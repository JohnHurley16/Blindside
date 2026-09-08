"""Two numbers under near-identical labels. The whole game, in four words and two integers.

SPECTATOR-DISPLAY.md 3 and 6.9.1:

    IT IS                        IT THINKS IT IS
    WRONG BY                     WRONG BY
    34                           1
    cells                        cell

-- one above the other in a 300 px rail, not side by side.

The left number is the truth channel's `error_cells`. The right is the machine's own
`sigma_pos()` -- what it believes its uncertainty to be. Nothing else on the screen states
the same fact in both frames at the same size, and it needs no vocabulary: the labels are
as close to identical as the meaning allows, so **the difference between the numbers is
what the eye lands on**, not the difference between the words.

It lives in the top block of the rail, immediately right of the inset, because the small
picture of the machine's belief and the small claim that belief makes should be one
saccade apart rather than six hundred pixels. It does not move when the two scenes trade
slots: a readout that moves is a readout the viewer has to find again, and its meaning
does not depend on which picture is big.

**Three states, and the second and third are the design's whole thesis.**

*They disagree*, which is most of the match. The left number takes the ramp -- tertiary
under three cells, primary to twelve, lie to thirty, kill past it -- and the right one is
GHOST cyan, always. The machine's calm is the joke; it is never coloured to look alarmed,
because it is not.

*They agree*, `round(error) == round(sigma)`. Then the left number is drawn in GHOST too,
so the two are literally identical marks and the block reads as one fact stated twice.
This is the only time the ramp is overridden, and it is what makes disagreement -- rather
than largeness -- the thing that shows. Under the ramp alone, `2 / 2` and `2 / 34` would
both open with a tertiary left number, and the first of those is the machine being right.

*A fix lands.* Both numbers are underlined in LIE for `READOUT_FIX_HOLD_S`, and then the
numbers do the talking. At 1:44 an honest correction fires the mark and both numbers fall
together, which teaches the rule. At 2:21.4 the same mark fires, the right number collapses
to 1 -- and the left leaps from 4 to 34 and turns red. One mark, two opposite outcomes,
thirty-seven seconds apart, and no legend anywhere.
"""
from __future__ import annotations

import numpy as np
from vispy.scene import visuals

from .. import tuning as T
from . import palette
from .text_group import BODY, DISPLAY, MICRO, Slot, TextGroup

# Two lines each, and they break at the same word on purpose. `IT THINKS IT IS WRONG BY`
# set on one line at 11 pt measures about 269 px against 268 px of usable rail, which is a
# clipped label waiting for a machine with slightly different metrics -- but the wrap is
# not a workaround, it is the better drawing. Broken here, both labels end with `WRONG BY`
# on its own line directly above its own number, so the shared words are literally aligned
# and the only thing that differs between the two blocks is the integer underneath.
LEFT_LABEL: tuple[str, str] = ("IT IS", "WRONG BY")
RIGHT_LABEL: tuple[str, str] = ("IT THINKS IT IS", "WRONG BY")
LABEL_LINE_H: float = 18.0       # px between a label's two lines at 11 pt
UNDERLINE_INSET: float = 2.0     # px, so the rule sits under the digits and not the label


class Readout:
    """The rail's top block. Six strings in the shared group, plus one `Line`."""

    def __init__(self, group: TextGroup, parent: object, order: int = 0) -> None:
        self.left_label: tuple[Slot, ...] = tuple(
            group.slot(BODY, line, rgb=palette.SECONDARY) for line in LEFT_LABEL)
        self.left_value: Slot = group.slot(DISPLAY, "0", rgb=palette.TERTIARY)
        self.left_unit: Slot = group.slot(MICRO, "cells", rgb=palette.SECONDARY)
        self.right_label: tuple[Slot, ...] = tuple(
            group.slot(BODY, line, rgb=palette.SECONDARY) for line in RIGHT_LABEL)
        self.right_value: Slot = group.slot(DISPLAY, "0", rgb=palette.GHOST)
        self.right_unit: Slot = group.slot(MICRO, "cells", rgb=palette.SECONDARY)

        # A Line, not a Rectangle: setting any property on a Rectangle regenerates its
        # geometry and forces a synchronous repaint, and this one changes twice a minute.
        self.underline = visuals.Line(parent=parent, connect="segments", width=2.0)
        self.underline.set_gl_state("translucent", depth_test=False)
        self.underline.order = order
        self.underline.visible = False

        self.x: float = 0.0
        self.y: float = 0.0
        self._rule_points: np.ndarray = np.zeros((4, 2), dtype=np.float32)
        self._held: bool = False

    # ---- geometry --------------------------------------------------------------------
    def move(self, x: float, y: float) -> None:
        """Reposition, without touching any string. The layout is derived from the live
        canvas size, and the live and recorded canvases are different sizes."""
        self.x, self.y = x, y
        second = y + self.block_height + T.READOUT_BLOCK_GAP
        number = LABEL_LINE_H + T.READOUT_LABEL_GAP
        for top, label, value, unit in ((y, self.left_label, self.left_value, self.left_unit),
                                        (second, self.right_label, self.right_value,
                                         self.right_unit)):
            for index, slot in enumerate(label):
                slot.at(x, top + index * LABEL_LINE_H)
            value.at(x, top + number)
            unit.at(x, top + number + T.READOUT_UNIT_GAP)

        left_y = y + number + T.READOUT_UNDERLINE_DROP
        right_y = second + number + T.READOUT_UNDERLINE_DROP
        self._rule_points = np.array(
            [[x + UNDERLINE_INSET, left_y], [x + UNDERLINE_INSET + T.READOUT_UNDERLINE_LEN, left_y],
             [x + UNDERLINE_INSET, right_y], [x + UNDERLINE_INSET + T.READOUT_UNDERLINE_LEN, right_y]],
            dtype=np.float32)
        self.underline.set_data(self._rule_points, color=(*palette.LIE, 0.95))

    @property
    def block_height(self) -> float:
        return LABEL_LINE_H + T.READOUT_LABEL_GAP + T.READOUT_UNIT_GAP

    @property
    def height(self) -> float:
        return 2.0 * self.block_height + T.READOUT_BLOCK_GAP

    # ---- one frame -------------------------------------------------------------------
    def update(self, error_cells: float, sigma_cells: float, t: float,
               last_fix_t: float | None) -> None:
        """Both numbers are gated on their integer value, so each is assigned about once
        a second rather than sixty times -- 6.10's rule, and the reason the whole chrome
        can live in four `Text` visuals."""
        wrong = int(round(error_cells))
        thinks = int(round(sigma_cells))
        agree = wrong == thinks

        self.left_value.set(str(wrong))
        self.right_value.set(str(thinks))
        self.left_unit.set("cell" if wrong == 1 else "cells")
        self.right_unit.set("cell" if thinks == 1 else "cells")
        # Agreement is drawn as sameness: the same colour, so the two are one mark twice.
        self.left_value.tint(palette.GHOST if agree else palette.ramp(error_cells))

        # Derived from the fix's own timestamp rather than from a first-sight rule, so a
        # `--snap` that lands the display at 5:41 with a fix ninety seconds behind it does
        # not draw that fix as though it had just arrived. Snapshots are how this gets
        # iterated, so a mark that is only correct under a 60 Hz clock is not correct.
        age = 1e9 if last_fix_t is None else t - last_fix_t
        held = 0.0 <= age < T.READOUT_FIX_HOLD_S
        if held is not self._held:
            # It does not fade in or out: a mark that fades is a mark whose ends the eye
            # can miss, and this one exists to say *look here, now*. It arrives at full
            # and it stops. Two booleans a minute, so nothing here is in a per-frame path.
            self._held = held
            self.underline.visible = held
