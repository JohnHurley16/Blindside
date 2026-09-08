"""Every chrome string on the screen, in four `Text` visuals instead of twenty-two.

SPECTATOR-DISPLAY.md 6.10, and it is the single largest saving available anywhere on
this display. The spike isolated the cost: three 3D viewboxes alone paint in 12.2 ms,
adding the panel grounds and images and lines and markers changes nothing measurable,
and adding the strings takes it to 27.3. **A `Text` visual costs about half a
millisecond a frame just to exist, whether or not anything ever touches it.** Measured:
34 separate = 24.2 ms, the same 34 in one visual = 10.0 ms, in four = 15.6 ms.

So the four type sizes of 6.2 are a performance rule as well as a design one, and this
module is where the two meet. A `Text` visual takes a *list* of strings and an array of
positions, one per string, and -- less obviously -- an (n, 4) array of colours, one per
string. What it does not take per string is a font, an anchor or a weight, so a group is
keyed by all three. Two things make four groups sufficient rather than twelve:

  * **weight follows size.** Display and Head are bold, Body and Micro are not. That is
    6.2's table, not a convenience, and it means (size, bold) has exactly four values.
  * **every chrome string is anchored left and vertically centred.** Anything that used
    to be right- or centre-anchored is given a left x by its caller. The two that were
    are a one-character compass tick and a static timeline label, so nothing is lost and
    a whole axis of grouping goes away.

**The one rule that must not be broken by a caller: no slot is assigned unconditionally
in `draw()`.** `Text.text` rebuilds the glyph atlas for the *whole group*, so an
unconditional assignment is worse here than it was with separate visuals, not better --
the spike priced unconditional assignment at 25.4 ms with one visual and 50.1 ms median
(p90 164) with thirty-four. `Slot.set` compares before it assigns and `flush` uploads at
most once per group per frame, so a caller who calls `set` every frame with the same
string costs nothing. That is the whole discipline: **compare, then assign.**
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from vispy.scene import visuals

from .. import tuning as T
from . import palette

Rgb = tuple[float, float, float]


@dataclass(frozen=True, slots=True)
class Role:
    """One of the four type sizes. Weight follows size; see 6.2."""

    key: str
    size: float
    bold: bool


DISPLAY: Role = Role("display", T.TYPE_DISPLAY_PT, True)
HEAD: Role = Role("head", T.TYPE_HEAD_PT, True)
BODY: Role = Role("body", T.TYPE_BODY_PT, False)
MICRO: Role = Role("micro", T.TYPE_MICRO_PT, False)
ROLES: tuple[Role, ...] = (DISPLAY, HEAD, BODY, MICRO)

# 6.2's floor, asserted at import. The status labels, the map key and the timeline's window
# label were all at 7.5 pt, and the gate tester watched a compressed H.264 video where
# 7.5 pt grey is not small -- it is absent. A fifth size would also be a fifth visual.
NINE_POINT_FLOOR: float = 9.0
assert min(role.size for role in ROLES) >= NINE_POINT_FLOOR, (
    "SPECTATOR-DISPLAY 6.2: nothing below nine points")
assert len({role.size for role in ROLES}) == len(ROLES), "one size per role"

# A hidden slot holds a space rather than an empty string. An empty one is handled
# correctly by vispy -- it contributes no glyphs and the position and colour arrays stay
# consistent -- but a group whose strings are *all* empty is a degenerate case that only
# shows up when something else has already gone wrong, and a space costs one invisible
# quad to be sure of never meeting it.
BLANK: str = " "


class Slot:
    """One string inside a group. A handle, not a visual: it owns an index."""

    __slots__ = ("_group", "_index")

    def __init__(self, group: TextGroup, index: int) -> None:
        self._group: TextGroup = group
        self._index: int = index

    @property
    def index(self) -> int:
        return self._index

    def set(self, text: str) -> None:
        """Compare, then assign. Safe to call every frame with the same string."""
        self._group._set_text(self._index, text)

    def hide(self) -> None:
        self._group._set_text(self._index, BLANK)

    def at(self, x: float, y: float) -> None:
        self._group._set_pos(self._index, x, y)

    def tint(self, rgb: Rgb, alpha: float = 1.0) -> None:
        self._group._set_colour(self._index, rgb, alpha)


class TextGroup:
    """Four `Text` visuals, and every chrome string on the screen inside them."""

    def __init__(self, parent: object, order: int = 0) -> None:
        self._visuals: dict[str, object] = {}
        self._texts: dict[str, list[str]] = {}
        self._pos: dict[str, np.ndarray] = {}
        self._colours: dict[str, np.ndarray] = {}
        self._dirty: dict[str, tuple[bool, bool, bool]] = {}
        self._pending: list[tuple[Role, str, float, float, Rgb, float]] = []
        self._role_of: list[Role] = []
        self._built: bool = False
        self._parent: object = parent
        self._order: int = order
        self._local: list[tuple[str, int]] = []
        self._saved: dict[int, str] = {}
        self._keep: set[int] | None = None

    # ---- construction ----------------------------------------------------------------
    def slot(self, role: Role, text: str = BLANK, x: float = 0.0, y: float = 0.0,
             rgb: Rgb = palette.SECONDARY, alpha: float = 1.0) -> Slot:
        """Register a string. Every slot must exist before `build()`.

        Slots are fixed at construction because adding one later would change a group's
        string count, and vispy rebuilds the whole group's vertex buffer when the list
        changes shape. A display with a fixed set of strings never pays that after the
        warm-up.
        """
        assert not self._built, "every slot must be registered before build()"
        index = len(self._pending)
        self._pending.append((role, text, x, y, rgb, alpha))
        self._role_of.append(role)
        return Slot(self, index)

    def build(self) -> None:
        """Create the four visuals. Called once, inside the warm-up."""
        assert not self._built
        for role in ROLES:
            mine = [i for i, r in enumerate(self._role_of) if r is role]
            if not mine:
                continue
            self._texts[role.key] = [self._pending[i][1] for i in mine]
            self._pos[role.key] = np.array(
                [[self._pending[i][2], self._pending[i][3]] for i in mine], dtype=np.float32)
            self._colours[role.key] = np.array(
                [[*self._pending[i][4], self._pending[i][5]] for i in mine], dtype=np.float32)
            visual = visuals.Text(list(self._texts[role.key]), parent=self._parent,
                                  pos=self._pos[role.key].copy(),
                                  color=self._colours[role.key].copy(),
                                  font_size=role.size, bold=role.bold,
                                  anchor_x="left", anchor_y="center")
            # The chrome sits over the cold open's scrim and over three ViewBoxes, and
            # vispy's "translucent" preset leaves depth testing on -- an overlay that
            # does not switch it off is discarded without a word.
            visual.set_gl_state("translucent", depth_test=False)
            visual.order = self._order
            self._visuals[role.key] = visual
            self._dirty[role.key] = (False, False, False)
        # index -> (role key, position within that role's list)
        counts: dict[str, int] = {}
        for role in self._role_of:
            n = counts.get(role.key, 0)
            self._local.append((role.key, n))
            counts[role.key] = n + 1
        self._built = True

    # ---- one frame -------------------------------------------------------------------
    def _pre_build(self, index: int, text: str | None = None,
                   pos: tuple[float, float] | None = None,
                   colour: tuple[Rgb, float] | None = None) -> None:
        """A caller may position or fill a slot before `build()` -- a panel's `move()`
        runs from its own constructor as often as from the layout -- so the pending
        record is editable until the visuals exist."""
        role, was_text, x, y, rgb, alpha = self._pending[index]
        if text is not None:
            was_text = text
        if pos is not None:
            x, y = pos
        if colour is not None:
            rgb, alpha = colour
        self._pending[index] = (role, was_text, x, y, rgb, alpha)

    def _set_text(self, index: int, text: str) -> None:
        if not self._built:
            self._pre_build(index, text=text)
            return
        if self._keep is not None and index not in self._keep:
            # Muted. Remember what the caller wanted rather than dropping it: the caller
            # is a draw() that runs every frame whether or not the cold open is up, and a
            # mute that a later call in the same frame could undo would not be a mute.
            self._saved[index] = text
            return
        self._write(index, text)

    def _write(self, index: int, text: str) -> None:
        key, i = self._local[index]
        if self._texts[key][i] == text:
            return
        self._texts[key][i] = text
        t, p, c = self._dirty[key]
        self._dirty[key] = (True, p, c)

    def _set_pos(self, index: int, x: float, y: float) -> None:
        if not self._built:
            self._pre_build(index, pos=(x, y))
            return
        key, i = self._local[index]
        row = self._pos[key][i]
        # Compared in float32, which is what the row holds. Comparing a float32 against
        # the float64 that produced it is False for almost every value -- 0.949 does not
        # survive the round trip -- so the naive check never matches and every call marks
        # the group dirty. That turns "compare, then assign" into "assign", which is the
        # one thing this module exists to avoid.
        want = np.array([x, y], dtype=np.float32)
        if np.array_equal(row, want):
            return
        row[:] = want
        t, p, c = self._dirty[key]
        self._dirty[key] = (t, True, c)

    def _set_colour(self, index: int, rgb: Rgb, alpha: float) -> None:
        if not self._built:
            self._pre_build(index, colour=(rgb, alpha))
            return
        key, i = self._local[index]
        row = self._colours[key][i]
        want = np.array([rgb[0], rgb[1], rgb[2], alpha], dtype=np.float32)
        if np.array_equal(row, want):        # in float32; see `_set_pos`
            return
        row[:] = want
        t, p, c = self._dirty[key]
        self._dirty[key] = (t, p, True)

    def flush(self) -> None:
        """Upload whatever changed, at most once per group per frame."""
        for key in tuple(self._dirty):
            text, pos, colour = self._dirty[key]
            if not (text or pos or colour):
                continue
            visual = self._visuals[key]
            if text:
                # Assigning `.text` drops the vertex buffer and re-promotes position and
                # colour from `self._pos` / `self._color` on the next draw, so a group
                # whose strings changed does not also need its other two arrays pushed --
                # but it does need them to be *current*, which is why `_set_pos` and
                # `_set_colour` write into the local arrays whether or not they upload.
                visual.text = list(self._texts[key])          # type: ignore[attr-defined]
                visual.pos = self._pos[key].copy()            # type: ignore[attr-defined]
                visual.color = self._colours[key].copy()      # type: ignore[attr-defined]
                self._dirty[key] = (False, False, False)
                continue
            if pos:
                visual.pos = self._pos[key].copy()            # type: ignore[attr-defined]
            if colour:
                visual.color = self._colours[key].copy()      # type: ignore[attr-defined]
            self._dirty[key] = (False, False, False)

    # ---- the cold open, and nothing else ----------------------------------------------
    def mute(self, exempt: tuple[Slot, ...]) -> None:
        """Blank every string except these, remembering what was there.

        The cold open is a title card and the rail behind it reads `0` and `0`, which is
        the first thing a stranger would try to interpret and which means nothing yet.
        Hiding the *visuals* is not an option -- the card's own lines live in the same four
        groups -- so it is done a string at a time, twice a match.
        """
        self._keep = {slot.index for slot in exempt}
        self._saved = {i: self._texts[k][j] for i, (k, j) in enumerate(self._local)
                       if i not in self._keep}
        for index in self._saved:
            self._write(index, BLANK)

    def unmute(self) -> None:
        """Put back what `mute` blanked. Static strings need this -- a title set once at
        construction is never re-set, so nothing else would ever restore it. Dynamic ones
        are restored too and then immediately overwritten by the frame's own value, which
        costs one comparison and keeps this from needing to know which is which."""
        saved = self._saved
        self._keep = None
        self._saved = {}
        for index, text in saved.items():
            self._write(index, text)

    @property
    def visual_count(self) -> int:
        return len(self._visuals)
