"""The policy drawn as a graph: boxes for tests and actions, wired together.

Flow runs down the column. Each test that answers "no" passes control to the one
below it; the test that answers "yes", or the action at the bottom, is the branch
that fired. The connector into the live branch is drawn bright, so the path taken
this tick is a line you can follow rather than a fact you have to read.
"""
from __future__ import annotations

import numpy as np
from vispy.scene import visuals

from ..policy.decision_node import DecisionNode
from . import palette
from .node_box import NodeBox

MAX_NODES: int = 10
ACTION_H: float = 30.0
TEST_H: float = 52.0
SUB_H: float = 32.0
GAP: float = 13.0
SUB_GAP: float = 4.0
SUB_INDENT: float = 14.0


class DecisionGraphView:
    def __init__(self, parent: object, x: float, y: float, width: float) -> None:
        self.x: float = x
        self.y: float = y
        self.width: float = width
        self.edges = visuals.Line(parent=parent, connect="segments", width=1.5)
        self.edges.set_gl_state("translucent", depth_test=False)
        self.arrows = visuals.Markers(parent=parent)
        self.arrows.set_gl_state("translucent", depth_test=False)
        self.boxes: list[NodeBox] = [NodeBox(parent) for _ in range(MAX_NODES)]
        # Every bar in the graph, as two line visuals: one set_data a frame instead
        # of twenty rectangle regenerations, each of which forced a repaint.
        self.bar_tracks = visuals.Line(parent=parent, connect="segments", width=5,
                                       color=palette.BAR_TRACK)
        self.bar_fills = visuals.Line(parent=parent, connect="segments", width=5)
        for v in (self.bar_tracks, self.bar_fills):
            v.set_gl_state("translucent", depth_test=False)
        self._bottom: float = y
        self._edge_key: tuple = ()

    @staticmethod
    def _height_for(node: DecisionNode) -> float:
        if node.kind == "action":
            return ACTION_H
        if node.kind == "sub":
            return SUB_H
        return TEST_H

    def update(self, nodes: list[DecisionNode]) -> None:
        segments: list[list[float]] = []
        colours: list[tuple[float, float, float, float]] = []
        arrow_pos: list[list[float]] = []
        arrow_col: list[tuple[float, float, float, float]] = []

        cursor = self.y
        previous_bottom: float | None = None
        previous_fired: bool = True

        for index, node in enumerate(nodes):
            if index >= MAX_NODES:
                break
            box = self.boxes[index]
            height = self._height_for(node)
            is_sub = node.kind == "sub"
            box_x = self.x + (SUB_INDENT if is_sub else 0.0)
            box_w = self.width - (SUB_INDENT if is_sub else 0.0)

            if previous_bottom is not None:
                cursor = previous_bottom + (SUB_GAP if is_sub else GAP)

            box.place(box_x, cursor, box_w, height)
            box.show(node)

            if previous_bottom is not None and not is_sub:
                # the edge into this node: bright when control actually flowed here
                live = previous_fired or node.active
                colour = palette.EDGE_LIVE if live else palette.EDGE_IDLE
                mid_x = self.x + self.width / 2
                segments += [[mid_x, previous_bottom, 0.0], [mid_x, cursor, 0.0]]
                colours += [colour] * 2
                arrow_pos.append([mid_x, cursor - 1.0, 0.0])
                arrow_col.append(colour)
            elif previous_bottom is not None and is_sub:
                # subs hang off the action above on a short elbow
                left_x = self.x + SUB_INDENT / 2
                segments += [[left_x, previous_bottom, 0.0], [left_x, cursor + height / 2, 0.0]]
                colours += [palette.EDGE_IDLE] * 2
                segments += [[left_x, cursor + height / 2, 0.0],
                             [box_x, cursor + height / 2, 0.0]]
                colours += [palette.EDGE_IDLE] * 2

            previous_bottom = cursor + height
            if not is_sub:
                previous_fired = node.fired

        for spare in range(len(nodes), MAX_NODES):
            self.boxes[spare].set_visible(False)

        tracks: list[list[float]] = []
        fills: list[list[float]] = []
        fill_colours: list[tuple[float, float, float, float]] = []
        for box in self.boxes[:len(nodes)]:
            if box.bar is None:
                continue
            bx, by, track_w, fill_w, hot = box.bar
            tracks += [[bx, by, 0.0], [bx + track_w, by, 0.0]]
            fills += [[bx, by, 0.0], [bx + max(fill_w, 1.0), by, 0.0]]
            fill_colours += [palette.BAR_HOT if hot else palette.BAR_FILL] * 2
        if tracks:
            self.bar_tracks.set_data(np.array(tracks))
            self.bar_fills.set_data(np.array(fills), color=np.array(fill_colours))
            self.bar_tracks.visible = True
            self.bar_fills.visible = True
        else:
            self.bar_tracks.visible = False
            self.bar_fills.visible = False

        edge_key = tuple((n.node_id, n.fired, n.active, n.kind) for n in nodes[:MAX_NODES])
        if edge_key != self._edge_key:
            self._edge_key = edge_key
            if segments:
                self.edges.set_data(np.array(segments), color=np.array(colours))
                self.edges.visible = True
            else:
                self.edges.visible = False
            if arrow_pos:
                self.arrows.set_data(np.array(arrow_pos), face_color=np.array(arrow_col),
                                     size=8, symbol="triangle_down", edge_width=0)
                self.arrows.visible = True
            else:
                self.arrows.visible = False
        self._bottom = previous_bottom or self.y

    @property
    def bottom(self) -> float:
        return self._bottom
