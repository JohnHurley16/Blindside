"""Label-and-value rows. What the agent believes about itself, in plain words.

One row may also carry a bar, and exactly one does: CONDITION, the machine's own damage.
THE-MACHINERY.md 4.7 argues the meter belongs in the rail rather than in the world --
a 1.6-cell world-space bar is 50 px at CLOSE and 9 px at WIDE, and WIDE is where the
director sits for most of the match -- and that the number wants a bar beside it because
"hurt 51%" is a fact and a half-empty bar is a picture of one. The mark that has to work
at WIDE is on the glyph instead, which is `glyph.machine()`'s `damage`.
"""
from __future__ import annotations

import numpy as np
from vispy.scene import visuals

from . import palette

ROW_HEIGHT: float = 30.0
BAR_ROW_EXTRA: float = 14.0      # a row with a bar is taller, so the bar never lands on
                                 # the next row's label
BAR_HEIGHT: float = 5.0
BAR_INSET: float = 12.0          # the value text's own left margin, so they line up


class StatusPanel:
    def __init__(self, parent: object, x: float, y: float, width: float,
                 labels: tuple[str, ...], bar_rows: tuple[int, ...] = ()) -> None:
        self.x: float = x
        self.y: float = y
        self.width: float = width
        self.labels: tuple[str, ...] = labels
        self.bar_rows: tuple[int, ...] = bar_rows
        self.label_visuals: list[object] = []
        self.value_visuals: list[object] = []
        self._cache: list[str] = [""] * len(labels)
        for index, label in enumerate(labels):
            row_y = y + self._offset(index)
            self.label_visuals.append(
                visuals.Text(label, parent=parent, pos=(x + BAR_INSET, row_y),
                             anchor_x="left", anchor_y="center",
                             color=palette.DIM, font_size=7.5))
            self.value_visuals.append(
                visuals.Text("", parent=parent, pos=(x + BAR_INSET, row_y + 14),
                             anchor_x="left", anchor_y="center",
                             color=palette.TITLE, font_size=10.5, bold=True))
        # One Line for every bar on the panel, track and fill together, so a row's
        # meter costs one visual and one `set_data` on the frames where it changes.
        self.bars: object = visuals.Line(parent=parent, connect="segments", width=BAR_HEIGHT)
        # vispy's "translucent" preset leaves depth testing ON, and the rail panel behind
        # this is a Rectangle at the same z -- so without this the bar is drawn and then
        # discarded, with no error. The same trap is documented in view.py.
        self.bars.set_gl_state("translucent", depth_test=False)
        self.bars.visible = False
        self._fractions: tuple[float, ...] = ()

    # ---- geometry -----------------------------------------------------------------------
    def _offset(self, index: int) -> float:
        """Rows are stacked, and a row that carries a bar is taller than one that does
        not -- so the CONDITION row can sit anywhere in the rail rather than being
        pushed to the bottom where the thing the designer asked for is below the fold."""
        return sum(ROW_HEIGHT + (BAR_ROW_EXTRA if k in self.bar_rows else 0.0)
                   for k in range(index))

    def move(self, x: float, y: float) -> None:
        """Reposition, without touching any `.text`. The layout is derived from the live
        canvas size, and the live and recorded canvases are different sizes."""
        self.x, self.y = x, y
        for index in range(len(self.labels)):
            row_y = y + self._offset(index)
            self.label_visuals[index].pos = (x + BAR_INSET, row_y)
            self.value_visuals[index].pos = (x + BAR_INSET, row_y + 14)
        self._fractions = ()                    # the bars are in canvas pixels: redraw

    # ---- one frame ----------------------------------------------------------------------
    def set(self, values: tuple[str, ...], colours: tuple[object, ...] | None = None) -> None:
        for index, value in enumerate(values):
            if index >= len(self.value_visuals):
                break
            if self._cache[index] != value:
                self._cache[index] = value
                self.value_visuals[index].text = value
            if colours is not None and colours[index] is not None:
                self.value_visuals[index].color = colours[index]

    def set_bars(self, fractions: tuple[float, ...],
                 colours: tuple[tuple[float, float, float], ...]) -> None:
        """One 0..1 fraction and one colour per entry in `bar_rows`, in that order."""
        if fractions == self._fractions:
            return
        self._fractions = fractions
        points: list[list[float]] = []
        rgba: list[tuple[float, float, float, float]] = []
        left = self.x + BAR_INSET
        right = self.x + self.width - BAR_INSET
        for row, fraction, rgb in zip(self.bar_rows, fractions, colours):
            bar_y = self.y + self._offset(row) + ROW_HEIGHT + 1.0
            points += [[left, bar_y], [right, bar_y]]
            rgba += [palette.BAR_TRACK] * 2
            end = left + (right - left) * min(max(fraction, 0.0), 1.0)
            if end > left + 1.0:
                points += [[left, bar_y], [end, bar_y]]
                rgba += [(*rgb, 0.95)] * 2
        if points:
            self.bars.set_data(np.array(points, dtype=np.float32),   # type: ignore[attr-defined]
                               color=np.array(rgba, dtype=np.float32))
        self.bars.visible = bool(points)            # type: ignore[attr-defined]

    @property
    def height(self) -> float:
        return self._offset(len(self.labels))
