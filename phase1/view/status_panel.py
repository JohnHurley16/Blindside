"""Label-and-value rows, in the shared text group. What is true of the machine, in words.

Four rows, down from six. The two that went were the two the readout above it made
redundant or that only an engineer could use -- `IT THINKS IT KNOWS WHERE IT IS TO` is
`IT THINKS IT IS WRONG BY` said again at a third of the size, and `MAP IT HAS BUILT
3900 points, 12 pings` is a number a stranger cannot do anything with. What is left is
what it is CARRYING, what STATE it is in, when it was last corrected, and the one thing
the viewer can do.

**The overprint is fixed here.** `ROW_HEIGHT = 30` with a value at `row_y + 14` and the
next label at `row_y + 30` meant the value struck through the label below it, which is
visible in every render of the display the gate failed on. The rows are taller and the
type is bigger: 7.5 pt is not small in an h264 encode, it is absent, and the gate tester
watched a video.

One row may also carry a bar, and exactly one does: CONDITION, the machine's own damage.
THE-MACHINERY.md 4.7 argues the meter belongs in the rail rather than in the world -- a
1.6-cell world-space bar is 50 px at CLOSE and 9 px at WIDE, and WIDE is where the
director sits for most of the match -- and that the number wants a bar beside it because
"hurt 51%" is a fact and a half-empty bar is a picture of one. The mark that has to work
at WIDE is on the glyph instead, which is `glyph.machine()`'s `damage`.
"""
from __future__ import annotations

import numpy as np
from vispy.scene import visuals

from .. import tuning as T
from . import palette
from .text_group import BODY, HEAD, Slot, TextGroup

Rgb = tuple[float, float, float]


class StatusPanel:
    def __init__(self, group: TextGroup, labels: tuple[str, ...],
                 bar_rows: tuple[int, ...] = (), parent: object | None = None,
                 order: int = 0) -> None:
        self.x: float = 0.0
        self.y: float = 0.0
        self.width: float = T.RAIL_W - 2.0 * T.MARGIN
        self.labels: tuple[str, ...] = labels
        self.bar_rows: tuple[int, ...] = bar_rows
        self.label_slots: list[Slot] = [
            group.slot(BODY, label, rgb=palette.SECONDARY) for label in labels]
        self.value_slots: list[Slot] = [
            group.slot(HEAD, " ", rgb=palette.PRIMARY) for _ in labels]

        # One Line for every bar on the panel, track and fill together, so a row's meter
        # costs one visual and one `set_data` on the frames where it changes.
        self.bars: object = visuals.Line(parent=parent, connect="segments",
                                         width=T.STATUS_BAR_H)
        # vispy's "translucent" preset leaves depth testing ON, and the rail panel behind
        # this is a Rectangle at the same z -- so without this the bar is drawn and then
        # discarded, with no error. The same trap is documented in view.py.
        self.bars.set_gl_state("translucent", depth_test=False)
        self.bars.order = order
        self.bars.visible = False
        self._fractions: tuple[object, ...] = ()
        self._drawn: bool = False

    # ---- geometry -----------------------------------------------------------------------
    def _offset(self, index: int) -> float:
        """Rows are stacked, and a row that carries a bar is taller than one that does
        not -- so the CONDITION row can sit anywhere in the rail rather than being pushed
        to the bottom where the thing the designer asked for is below the fold."""
        return sum(T.STATUS_ROW_H + (T.STATUS_BAR_ROW_EXTRA if k in self.bar_rows else 0.0)
                   for k in range(index))

    def move(self, x: float, y: float) -> None:
        """Reposition, without touching any string. The layout is derived from the live
        canvas size, and the live and recorded canvases are different sizes."""
        self.x, self.y = x, y
        for index in range(len(self.labels)):
            row_y = y + self._offset(index)
            self.label_slots[index].at(x, row_y)
            self.value_slots[index].at(x, row_y + T.STATUS_VALUE_DROP)
        self._fractions = ()                    # the bars are in canvas pixels: redraw

    # ---- one frame ----------------------------------------------------------------------
    def set(self, values: tuple[str, ...], colours: tuple[Rgb | None, ...] | None = None) -> None:
        """`Slot.set` compares before it assigns, so calling this every frame with the
        same strings costs four comparisons and no upload."""
        for index, value in enumerate(values):
            if index >= len(self.value_slots):
                break
            self.value_slots[index].set(value)
            if colours is not None and colours[index] is not None:
                self.value_slots[index].tint(colours[index])    # type: ignore[arg-type]

    def set_bars(self, fractions: tuple[float, ...],
                 colours: tuple[Rgb, ...]) -> None:
        """One 0..1 fraction and one colour per entry in `bar_rows`, in that order.

        Cached on the colours as well as the fractions: the meter goes from tertiary to
        the damage colour at a threshold, and a cache that only watched the number would
        hold the old colour until the number happened to move again.
        """
        if (fractions, colours) != self._fractions:
            self._fractions = (fractions, colours)
            points: list[list[float]] = []
            rgba: list[tuple[float, float, float, float]] = []
            left = self.x
            right = self.x + self.width
            for row, fraction, rgb in zip(self.bar_rows, fractions, colours):
                bar_y = self.y + self._offset(row) + T.STATUS_ROW_H + 6.0
                points += [[left, bar_y], [right, bar_y]]
                rgba += [(*palette.RULE, 0.95)] * 2
                end = left + (right - left) * min(max(fraction, 0.0), 1.0)
                if end > left + 1.0:
                    points += [[left, bar_y], [end, bar_y]]
                    rgba += [(*rgb, 0.95)] * 2
            if points:
                self.bars.set_data(np.array(points, dtype=np.float32),  # type: ignore[attr-defined]
                                   color=np.array(rgba, dtype=np.float32))
            self._drawn = bool(points)
        # Outside the cache, deliberately. Something else on the screen may have hidden
        # this -- the cold open's curtain does -- and a visibility that is only written
        # when the *number* changes never comes back, because the number does not change
        # just because the bar went away.
        if self.bars.visible is not self._drawn:     # type: ignore[attr-defined]
            self.bars.visible = self._drawn          # type: ignore[attr-defined]

    @property
    def height(self) -> float:
        return self._offset(len(self.labels))
