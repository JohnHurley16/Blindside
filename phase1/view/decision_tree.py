"""A live view of the policy deciding.

The point of the whole game is that you do not drive the machine, you gave it rules
and now you are watching them run. That is invisible if the screen only shows where
the machine ended up. So this draws the rules themselves, with whichever branch is
firing right now lit up.

It is also a preview of the real thing: Phase 4 captures an execution trace from the
behaviour-tree VM -- which nodes fired, in what order, on what predicate values -- and
this is the same idea against a hand-written policy.
"""
from __future__ import annotations

import numpy as np
from vispy.scene import visuals

from . import palette

# (node id, depth, label). Order is drawing order, top to bottom.
NODES: tuple[tuple[str, int, str], ...] = (
    ("root", 0, "WHAT IT IS DOING"),
    ("guard.uncertain", 1, "am I getting lost?"),
    ("hold", 1, "can I hear machinery?"),
    ("load", 1, "am I at a deposit?"),
    ("load.wait", 2, "sit still and fill up"),
    ("search", 1, "is the shaft missing?"),
    ("search.spiral", 2, "widen the circle until something answers"),
    ("done", 1, "home - wait to be collected"),
    ("drive", 1, "otherwise: keep going"),
    ("drive.steer", 2, "feel for walls, steer round them"),
    ("drive.escape", 2, "stuck - follow the wall out"),
    ("drive.beacon", 2, "drop a beacon behind me"),
    ("drive.ping", 2, "ping if I cannot see ahead"),
)

ROW_HEIGHT: float = 26.0
INDENT: float = 16.0


class DecisionTreeView:
    """Rows of text with the live branch highlighted."""

    def __init__(self, parent: object, x: float, y: float, width: float) -> None:
        self.x: float = x
        self.y: float = y
        self.width: float = width
        self.rows: list[object] = []
        self.marks: list[object] = []
        self._cache: dict[str, tuple[bool, str]] = {}

        self.highlight = visuals.Markers(parent=parent)
        self.highlight.set_gl_state("translucent", depth_test=False)
        self.connector = visuals.Line(parent=parent, connect="segments",
                                      color=(0.30, 0.36, 0.44, 0.55), width=1)
        self.connector.set_gl_state("translucent", depth_test=False)

        segments: list[list[float]] = []
        for index, (node_id, depth, label) in enumerate(NODES):
            row_y = y + index * ROW_HEIGHT
            text_x = x + 12 + depth * INDENT
            size = 11 if depth == 0 else (9.5 if depth == 1 else 8.5)
            row = visuals.Text(label, parent=parent, pos=(text_x, row_y),
                               anchor_x="left", anchor_y="center",
                               color=palette.TREE_IDLE, font_size=size,
                               bold=(depth == 0))
            self.rows.append(row)
            if depth > 0:
                left = x + 6 + (depth - 1) * INDENT + 4
                segments.append([left, row_y, 0.0])
                segments.append([text_x - 5, row_y, 0.0])
        if segments:
            self.connector.set_data(np.array(segments))

    def update(self, active: set[str], root_label: str) -> None:
        lit: list[list[float]] = []
        for index, (node_id, depth, label) in enumerate(NODES):
            row_y = self.y + index * ROW_HEIGHT
            is_live = node_id in active
            text = root_label if node_id == "root" else label
            cached = self._cache.get(node_id)
            if cached != (is_live, text):
                self._cache[node_id] = (is_live, text)
                row = self.rows[index]
                row.text = text
                if node_id == "root":
                    row.color = palette.TREE_ROOT
                else:
                    row.color = palette.TREE_LIVE if is_live else palette.TREE_IDLE
            if is_live and node_id != "root":
                lit.append([self.x + 6 + depth * INDENT - 6, row_y, 0.0])
        if lit:
            self.highlight.set_data(np.array(lit), face_color=palette.TREE_DOT,
                                    size=7, symbol="disc", edge_width=0)
            self.highlight.visible = True
        else:
            self.highlight.visible = False

    @property
    def height(self) -> float:
        return len(NODES) * ROW_HEIGHT
