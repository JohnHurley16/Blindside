"""What the blow does to the floor. THE-MACHINERY.md sections 2.3, 2.4 and 4.2.

The Assayer points, so the answer to *where is safe* is a place and not a distance, and
the only way a stranger reads a place is if the place is drawn. This draws three things
off the one field the sim hands over:

  * **the scour** -- permanent, built once, never touched. The ground around the machine
    is visibly ruined in roughly the shape of the union of every bearing it has ever
    worked, with no boundary anywhere. It is what replaces the dormant ring, and it is
    the single highest-value change in section 2: that ring was on screen for
    seventy-two per cent of the match, so for four minutes in five the only thing drawn
    *was* a disc. A viewer reads *nothing settles here* and finds out why forty seconds
    later.
  * **the lobe** -- an `Image` under the two contours, dark until the wind starts and
    then filling in nine countable steps from the axis outward to the flanks, so the
    first ground to light is the ground the array is pointing at and the lit region is
    always the dangerous one. This reverses THE-MACHINERY 2.4 deliberately; `_paint`
    says why.
  * **the contours** -- the lethal one solid at coupling 1.0, the felt one faint at
    0.25. Two closed curves, and neither is a circle: 9.00 cells on the axis against
    5.32 at the flank, and a tongue running better than thirty cells up the flooded
    passage against eighteen on a dry bearing. **The shape is the explanation.** Rock is
    not cover -- the curves cross walls without noticing them, because the shock is in
    the massif and the caves are not in its path -- and water is a highway.

**Where the field comes from, and why this file is not allowed to compute it.**
`StageAncient.coupling` is `gain(theta) * (9/d)^2` at every cell, already lopsided by
the medium factor, and it arrives frozen through the one-way channel. The range term
alone -- the field with the aim divided out -- is what the scour and the contour tables
need, and it is recovered here in one divide, because `gain` is a closed form of the
bearing this file is also given. Nothing is read from `truth`, and
`sensing.SoundField` is deliberately *not* reused: it imports `truth.cave`, which would
hand the renderer the real grid at module scope.
"""
from __future__ import annotations

import math

import numpy as np
from vispy.scene import visuals
from vispy.visuals.transforms import STTransform

from .. import tuning as T
from ..ancient_phase import AncientPhase
from ..match.stage_frame import StageAncient
from . import palette

_TAU: float = 2.0 * math.pi
BEARINGS: int = 180                  # 2 degrees a step: a contour at CLOSE framing is
                                     # 560 px around, so this is sub-pixel and it is one
                                     # 180x240 numpy compare a frame
RADII_STEP: float = 0.02             # only ever a BRACKET: the table finds which fiftieth
                                     # of a cell the crossing is in and the closed form is
                                     # bisected inside it (`_contour`). Fine because the
                                     # medium factor is a per-cell LOOKUP, so a ray that
                                     # clips the corner of a flooded cell puts a notch in
                                     # the field a tenth of a cell wide -- measured at 0.09
                                     # -- and a table that steps over one draws a curve
                                     # half a cell away from the model
RADII_MAX: float = 40.0              # the outermost felt reach over 90 aims x 180 bearings
                                     # is 33.75 cells (scratchpad/max_reach.py), so no
                                     # curve is ever clipped by the end of the table
BISECT_STEPS: int = 12               # 0.02 / 2^12 is five millionths of a cell
SCOUR_Z: float = -0.010              # over the floor image at -0.02, under everything
LOBE_Z: float = 0.050                # under the comets at 0.108 and the glyphs at 0.18
CONTOUR_Z: float = 0.140


class ShockLobe:
    """The coupling field on the floor plane, as one image and three line visuals."""

    def __init__(self, parent: object, ancient: StageAncient, grid: np.ndarray) -> None:
        self.x: float = ancient.x
        self.y: float = ancient.y
        rows, cols = grid.shape

        # The aim divided out. Constant for the match, so everything below is built on
        # it once: the polar table the contours read, and the scour.
        self._range: np.ndarray = np.asarray(ancient.coupling) / _gain(
            _cell_bearing(ancient.x, ancient.y, rows, cols), ancient.bearing_deg)

        # The medium factor, recovered from the frozen field in one more divide.
        # `_range` is (R / (d * factor))^2 at every cell CENTRE, so R / sqrt(range) is
        # the coupled distance and dividing that by the euclidean distance to the same
        # centre leaves the factor alone. It is wanted because the two curves have to be
        # drawn the way the model computes them: the factor is a property of a CELL and
        # the distance is continuous, exactly as `Ancient.coupling_at` does it truth-side.
        # Nothing new crosses the channel; this is arithmetic on what already arrived.
        yy, xx = np.mgrid[0:rows, 0:cols]
        centre = np.hypot(xx + 0.5 - self.x, yy + 0.5 - self.y)
        with np.errstate(divide="ignore", invalid="ignore"):
            coupled = T.ANCIENT_RADIUS / np.sqrt(self._range)
        self._factor: np.ndarray = np.where(centre > 1e-6, coupled / np.maximum(centre, 1e-9),
                                            1.0)
        self._rows: int = rows
        self._cols: int = cols

        self._angles: np.ndarray = np.linspace(0.0, _TAU, BEARINGS, endpoint=False)
        self._radii: np.ndarray = np.arange(RADII_STEP, RADII_MAX, RADII_STEP)
        self._ring: np.ndarray = np.column_stack([np.cos(self._angles),
                                                  np.sin(self._angles)])
        # The bracket table, in coupled distance rather than in coupling: the aim only
        # moves the threshold, so one table serves every bearing and every level.
        self._polar: np.ndarray = self._coupled(
            np.tile(self._radii, (BEARINGS, 1)))
        self._curves: dict[tuple[float, float], np.ndarray] = {}
        # The angular distance of every cell from the axis, folded into a quarter turn:
        # cos^2 is symmetric, so the back lobe is as strong as the front and the fill
        # opens from both noses at once.
        self._cell_bearing: np.ndarray = _cell_bearing(ancient.x, ancient.y, rows, cols)

        self.scour: object = visuals.Image(self._scour_image(grid), parent=parent,
                                           interpolation="nearest")
        self.scour.set_gl_state("translucent", depth_test=False)
        self.scour.order = T.SCOUR_DRAW_ORDER
        self.scour.transform = STTransform(translate=(0.0, 0.0, SCOUR_Z))

        self._blank: np.ndarray = np.zeros((rows, cols, 4), dtype=np.float32)
        self.lobe: object = visuals.Image(self._blank, parent=parent,
                                          interpolation="linear")
        self.lobe.set_gl_state("translucent", depth_test=False)
        self.lobe.order = T.LOBE_DRAW_ORDER
        self.lobe.transform = STTransform(translate=(0.0, 0.0, LOBE_Z))

        self.contours: object = visuals.Line(parent=parent, connect="segments", width=2.0)
        self.heave: object = visuals.Line(parent=parent, connect="segments", width=2.6)
        for index, visual in enumerate((self.contours, self.heave)):
            visual.set_gl_state("translucent", depth_test=False)   # type: ignore[attr-defined]
            visual.order = T.LOBE_DRAW_ORDER + 1 + index           # type: ignore[attr-defined]

        self._drawn: tuple[float, int, bool] = (float("nan"), -1, False)
        self.lobe.visible = False
        self.contours.visible = False
        self.heave.visible = False

    # ---- one frame -----------------------------------------------------------------------
    def update(self, ancient: StageAncient) -> None:
        armed = ancient.phase in (AncientPhase.WIND, AncientPhase.FIRING,
                                  AncientPhase.LETHAL)
        if not armed:
            # Nothing on the floor for fifty-four listening seconds, three of slew and
            # five of lock, except the scour that is always there. The warning has
            # somewhere to arrive.
            _show(self.lobe, False)
            _show(self.contours, False)
            _show(self.heave, False)
            self._drawn = (float("nan"), -1, False)
            return

        lethal = ancient.phase != AncientPhase.WIND
        clicks = (T.ANCIENT_CLICKS if lethal
                  else min(int(ancient.phase_progress * T.ANCIENT_CLICKS) + 1,
                           T.ANCIENT_CLICKS))
        key = (ancient.bearing_deg, clicks, lethal)
        if key != self._drawn:
            self._drawn = key
            self._paint(ancient, clicks, lethal)
            self._draw_contours(ancient, lethal)
        _show(self.lobe, True)
        _show(self.contours, True)
        self._draw_heave(ancient)

    # ---- the image -----------------------------------------------------------------------
    def _paint(self, ancient: StageAncient, clicks: int, lethal: bool) -> None:
        """Nine steps, from the nose outward to the tail.

        **This is the reverse of THE-MACHINERY 2.4, and 2.4 is wrong.** That section
        asks for the lobe to fill "from the tail round to the nose", so that "the last
        thing to light is the direction it is pointing" -- a nice idea about a shape
        closing on its own answer, and it inverts the only reading a stranger brings to
        a screen. Built that way, for eight of the nine warning seconds the lit,
        hazard-coloured ground is the ground that SURVIVES and the lethal axis is dark:
        anyone who reads brightness as danger reads the picture backwards for the whole
        warning and gets it right one second before the blow. The disagreement is
        written here rather than taken silently, because the document is the spec.

        So the axis lights first and the lit wedge widens outward as the clicks count
        up. The lit region is then always a superset of the dangerous region -- there is
        no instant at which lit ground is safer than dark ground -- and it GROWS toward
        anyone standing off the axis, which is the same information arriving as motion
        rather than as a legend. 2.4's other two marks are untouched: the boom still
        says where, seventeen seconds early, and the hammer still counts.
        """
        coupling = np.asarray(ancient.coupling)
        band = np.clip((coupling - T.ANCIENT_FELT_COUPLING)
                       / (1.0 - T.ANCIENT_FELT_COUPLING), 0.0, 1.0)
        core = np.clip((coupling - 1.0) * 0.8, 0.0, 1.0)
        offset = np.abs(_wrap(self._cell_bearing - math.radians(ancient.bearing_deg)))
        from_axis = np.minimum(offset, math.pi - offset)          # folded: cos^2 is even
        # Click 1 lights a ten-degree wedge on the axis; click 9 lights the whole quarter
        # turn out to the flank. Folded, so both noses fill together -- the back lobe is
        # as strong as the front and leaving it dark would be the same lie again.
        lit = from_axis <= (math.pi * 0.5) * (clicks / T.ANCIENT_CLICKS)

        image = self._blank.copy()
        # Red is drawn on exactly the ground that kills and nowhere else. That rule
        # already cost this project a beat once -- a verifier watching 5:43 read the red
        # tether as the danger and the red kill disc as scenery, two meanings sharing one
        # colour side by side -- so the halo stays magenta even while the core is red.
        image[:, :, :3] = palette.HAZARD
        if lethal:
            image[coupling >= 1.0, :3] = palette.KILL
        image[:, :, 3] = np.where(
            lit,
            T.ANCIENT_LOBE_ALPHA * (T.ANCIENT_LOBE_HALO * band ** T.ANCIENT_LOBE_FALLOFF
                                    + (1.0 - T.ANCIENT_LOBE_HALO) * core),
            0.0)
        self.lobe.set_data(image)                                  # type: ignore[attr-defined]

    # ---- the two curves ------------------------------------------------------------------
    def _coupled(self, radii: np.ndarray) -> np.ndarray:
        """Coupled distance at polar sample points: euclidean radius times the factor of
        the cell the point falls in. `radii` is either one radius per bearing or a table
        of them, and the cell lookup is the only quantised thing in it."""
        cos, sin = self._ring[:, 0], self._ring[:, 1]
        if radii.ndim == 2:
            cos, sin = cos[:, None], sin[:, None]
        xs = np.clip(self.x + cos * radii, 0.0, self._cols - 1e-6).astype(np.int32)
        ys = np.clip(self.y + sin * radii, 0.0, self._rows - 1e-6).astype(np.int32)
        return radii * self._factor[ys, xs]

    def _contour(self, level: float, aim_deg: float) -> np.ndarray:
        """How far `level` of coupling reaches on every bearing: the OUTERMOST radius at
        which the field crosses it.

        **Sub-cell, and it has to be.** The model's lethal contour is 9.00000 cells on
        the axis; a table sampled at integer cell indices on a quarter-cell radial grid
        drew it at 9.50, and at the 5:41 beat that put a survivor standing at 9.038
        nearly half a cell INSIDE the drawn kill boundary -- in the one frame this whole
        slice exists to produce. A picture that contradicts the rule it is illustrating
        is worse than no picture.

        So the table is a bracket and the closed form is bisected inside it, which is
        what `coupling_at` already does with a continuous distance and a cell-quantised
        medium factor. Rearranged, the crossing has no square roots in the loop:

            coupling = gain(theta) * (R / coupled)^2 = level
            <=>  coupled = R * sqrt(gain(theta) / level)

        and `gain` is constant along a bearing, so each of the 180 rays is one scalar
        solve. **Measured against `Ancient.coupling_at` itself, at all six aims a match
        uses and both levels: max error 0.00000 cells over the 36 bearings sampled, and
        0.00000 over all 180 drawn rays on the lethal curve** (`scratchpad/contour_error.py`).

        **Outermost, not first, and that is a real choice.** Coupling is not monotone in
        radius: the medium factor is a per-cell lookup, so a ray grazing the flooded
        passage leaves the field and re-enters it through notches a tenth to half a cell
        wide. A polar curve gets one radius per bearing, and for a *reach* the honest one
        is the far side of the last notch -- measured, taking the first crossing instead
        disagrees on 7 to 14 of 180 bearings by up to 12.5 cells, because it clips the
        tongue running 33.6 cells up the flooded ANC->SUMP bearing, which is the one
        thing the felt curve exists to show.

        What is left, and it is worth naming: on three of the six aims the felt curve
        misses an isolated inside sliver on ONE ray of 180 -- always a bearing into the
        sump, where the ray clips the corner of a flooded cell for less than the table's
        0.02 -- and draws 0.42, 0.50 and 7.04 cells short there. A finer table would find
        them and draw a one-ray spike off an otherwise smooth curve, which is a rendering
        of a measure-zero feature rather than information, so this is the better picture
        as well as the cheaper one. The lethal curve has no such rays at any aim: within
        20 cells of the machine every walkable cell has a medium factor of exactly 1.000,
        so the field there is smooth and the kill line is exact.
        """
        key = (level, aim_deg)
        cached = self._curves.get(key)
        if cached is not None:
            return cached
        need = T.ANCIENT_RADIUS * np.sqrt(_gain(self._angles, aim_deg) / level)
        inside = self._polar < need[:, None]
        reaches = inside.any(axis=1)
        columns = self._polar.shape[1]
        last = columns - 1 - np.argmax(inside[:, ::-1], axis=1)     # last sample inside
        lo = self._radii[last]
        hi = np.where(last + 1 < columns,
                      self._radii[np.minimum(last + 1, columns - 1)], RADII_MAX)
        for _ in range(BISECT_STEPS):
            mid = 0.5 * (lo + hi)
            still_in = self._coupled(mid) < need
            lo = np.where(still_in, mid, lo)
            hi = np.where(still_in, hi, mid)
        radius = 0.5 * (lo + hi)
        radius[~reaches] = 0.0                    # the level is met nowhere on this ray
        radius[last == columns - 1] = RADII_MAX   # still inside at the end of the table
        if len(self._curves) > 8:
            self._curves.clear()       # one aim is two curves; this never grows
        self._curves[key] = radius
        return radius

    def _draw_contours(self, ancient: StageAncient, lethal: bool) -> None:
        """The lethal curve solid, the felt one faint, and only the lethal one turns red.

        Two closed curves and neither is a circle. That is the answer to *where is safe*:
        there is a boundary, it is drawn, it points, and it runs a long way further up the
        flooded passage than it does anywhere dry.
        """
        points: list[np.ndarray] = []
        colours: list[np.ndarray] = []
        for level, alpha, rgb in ((1.0, 0.95, palette.KILL if lethal else palette.HAZARD),
                                  (T.ANCIENT_FELT_COUPLING, 0.30, palette.HAZARD)):
            radius = self._contour(level, ancient.bearing_deg)
            ring = self._ring * radius[:, None] + np.array([self.x, self.y])
            closed = np.vstack([ring, ring[:1]])
            pair = np.repeat(closed, 2, axis=0)[1:-1]
            points.append(np.column_stack([pair, np.full(len(pair), CONTOUR_Z)]))
            colours.append(np.tile(np.array([*rgb, alpha], dtype=np.float32),
                                   (len(pair), 1)))
        self.contours.set_data(np.concatenate(points).astype(np.float32),  # type: ignore[attr-defined]
                               color=np.concatenate(colours))

    # ---- the heave -----------------------------------------------------------------------
    def _draw_heave(self, ancient: StageAncient) -> None:
        """Three arcs crossing the floor at 24 cells a second, clipped to the lobe.

        This replaces the three flashes at 6 Hz. One hammer falling and a wave leaving
        it is more legible than a strobe, and the strobe was part of why the object read
        as a generic damage zone rather than as something that happened.

        Each arc is weighted along its own length by `gain`, so the wave is bright on the
        axis and almost gone at the flank. Without that it leaves the machine as a
        perfect circle for the first half-second -- which is the one shape this whole
        slice exists to stop drawing, arriving at the loudest moment in the match.
        """
        since = _since_blow(ancient)
        if since is None:
            _show(self.heave, False)
            return
        reach = self._contour(T.ANCIENT_FELT_COUPLING, ancient.bearing_deg)
        along = ((_gain(self._angles, ancient.bearing_deg) - T.ANCIENT_LOBE_FLOOR)
                 / (1.0 - T.ANCIENT_LOBE_FLOOR))
        points: list[np.ndarray] = []
        colours: list[np.ndarray] = []
        for arc in range(T.ANCIENT_HEAVE_ARCS):
            radius = T.ANCIENT_HEAVE_SPEED * (since - arc * T.ANCIENT_HEAVE_GAP_S)
            if radius <= 0.0:
                continue
            keep = (reach >= radius) & np.roll(reach >= radius, -1)
            if not keep.any():
                continue
            ring = self._ring * radius + np.array([self.x, self.y])
            starts, ends = ring[keep], np.roll(ring, -1, axis=0)[keep]
            pair = np.empty((2 * len(starts), 2), dtype=np.float64)
            pair[0::2], pair[1::2] = starts, ends
            fade = max(0.0, 1.0 - radius / float(reach.max())) * 0.9
            alpha = np.empty(2 * len(starts), dtype=np.float32)
            lit = fade * (0.10 + 0.90 * along[keep])
            alpha[0::2], alpha[1::2] = lit, lit
            rgba = np.tile(np.array([*palette.KILL, 1.0], dtype=np.float32),
                           (len(pair), 1))
            rgba[:, 3] = alpha
            points.append(np.column_stack([pair, np.full(len(pair), CONTOUR_Z)]))
            colours.append(rgba)
        if not points:
            _show(self.heave, False)
            return
        self.heave.set_data(np.concatenate(points).astype(np.float32),  # type: ignore[attr-defined]
                            color=np.concatenate(colours))
        _show(self.heave, True)

    # ---- built once ----------------------------------------------------------------------
    def _scour_image(self, grid: np.ndarray) -> np.ndarray:
        """alpha = 0.10 * min(1, 9/d), on ground only.

        The union of every bearing the array has ever worked is the range term with the
        gain at its maximum, which is exactly the field above -- so the ruined patch is
        already lopsided toward the water without anything being drawn twice. No
        boundary is drawn anywhere: a hard edge here would be a second ring, and a ring
        is what this is replacing.
        """
        image = np.zeros((*grid.shape, 4), dtype=np.float32)
        image[:, :, :3] = palette.HAZARD
        image[:, :, 3] = T.ANCIENT_SCOUR_ALPHA * np.minimum(1.0, np.sqrt(self._range))
        image[grid == 0, 3] = 0.0
        return image


# ---- the model, as three lines ------------------------------------------------------------------
def _gain(bearing: np.ndarray, aim_deg: float) -> np.ndarray:
    """0.35 + 0.65 * cos^2(theta - aim). The array is directional, which is the whole
    reason safe is a place: 9.00 cells of lethal reach on the axis, 5.32 at the flank."""
    return (T.ANCIENT_LOBE_FLOOR + (1.0 - T.ANCIENT_LOBE_FLOOR)
            * np.cos(bearing - math.radians(aim_deg)) ** 2)


def _cell_bearing(x: float, y: float, rows: int, cols: int) -> np.ndarray:
    yy, xx = np.mgrid[0:rows, 0:cols]
    return np.arctan2(yy + 0.5 - y, xx + 0.5 - x)


def _wrap(angle: np.ndarray) -> np.ndarray:
    return (angle + math.pi) % _TAU - math.pi


def _since_blow(ancient: StageAncient) -> float | None:
    if ancient.phase == AncientPhase.FIRING:
        return ancient.phase_progress * T.ANCIENT_FIRE_S
    if ancient.phase == AncientPhase.LETHAL:
        return T.ANCIENT_FIRE_S + ancient.phase_progress * T.ANCIENT_LETHAL_S
    return None


def _show(visual: object, wanted: bool) -> None:
    """`Node.visible` always calls `update()`, whether or not the value changed."""
    if visual.visible is not wanted:                    # type: ignore[attr-defined]
        visual.visible = wanted                         # type: ignore[attr-defined]
