"""A small key in the corner of the map: swatch, then what it means.

Four words each. Someone who has never seen this before should be able to work out
what they are looking at without being told, and a colour with no label is just a
colour.
"""
from __future__ import annotations

import numpy as np
from vispy.scene import visuals

from . import palette

ROW_HEIGHT: float = 17.0

ENTRIES: tuple[tuple[tuple[float, float, float, float], str], ...] = (
    ((0.62, 0.93, 1.00, 0.95), "wall it has pinged"),
    ((0.26, 0.30, 0.38, 0.95), "ground it only walked"),
    (palette.AGENT, "where it thinks it is"),
    (palette.ELLIPSE, "how sure it is"),
    (palette.BEACON, "beacons it dropped"),
    (palette.BELIEVED_HAZARD, "where it thinks the machinery is"),
    (palette.BELIEVED_RIVAL, "where it thinks the other machine is"),
)


class MapKey:
    def __init__(self, parent: object, x: float, y: float) -> None:
        self.swatches = visuals.Markers(parent=parent)
        self.swatches.set_gl_state("translucent", depth_test=False)
        self.labels: list[object] = []
        self._colours = np.array([colour for colour, _ in ENTRIES])
        for colour, label in ENTRIES:
            self.labels.append(
                visuals.Text(label, parent=parent, pos=(x + 14, y),
                             anchor_x="left", anchor_y="center",
                             color=palette.LEGEND, font_size=7.5))
        self.move(x, y)

    def move(self, x: float, y: float) -> None:
        positions: list[list[float]] = []
        for index, label in enumerate(self.labels):
            row_y = y + index * ROW_HEIGHT
            positions.append([x, row_y, 0.0])
            label.pos = (x + 14, row_y)
        self.swatches.set_data(np.array(positions), face_color=self._colours,
                               size=8, symbol="disc", edge_width=0)

    @property
    def height(self) -> float:
        return len(ENTRIES) * ROW_HEIGHT
