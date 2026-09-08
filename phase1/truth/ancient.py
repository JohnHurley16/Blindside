"""The Assayer: a survey machine of the prior industry, still running its program.

THE-MACHINERY.md sections 1, 3 and 4. Every seventy-five seconds it swings a ribbed
array onto a new bearing, ratchets a hammer up its mast and drops it, driving a shock
through the bedrock so it can listen to what comes back. It is not a guardian and not
a trap: it harms as a side effect of doing its job, and what it breaks is the
instruments of anything standing on the rock it is hitting.

Two facts about the harm decide the whole shape of this file:

  * it is DIRECTIONAL, so the lethal contour is 9.00 cells along the axis and 5.32 at
    the flank, and safe is a place rather than a distance; and
  * it arrives THROUGH THE ROCK, so a wall is not cover -- only water changes the
    reach, because a flooded working is a continuous column that carries the shock
    much further than stone does.
"""
from __future__ import annotations

import heapq
import math

import numpy as np

from .. import tuning as T
from ..ancient_phase import AncientPhase
from . import cave

# The cycle's boundaries, derived so that the established constants stay the only
# authority on when anything happens. THE-MACHINERY section 3's table, in seconds of
# phase: 0 listening, 54 slew, 57 locked, 62 wind, 71 fire, 71.15 lethal, 75.
_LETHAL_AT: float = T.ANCIENT_PERIOD_S - T.ANCIENT_LETHAL_S
_WIND_AT: float = _LETHAL_AT - T.ANCIENT_WARNING_S
_LOCK_AT: float = _WIND_AT - T.ANCIENT_LOCK_S
_SLEW_AT: float = _LOCK_AT - T.ANCIENT_SLEW_S

_factor_cache: np.ndarray | None = None
_base_cache: np.ndarray | None = None
_bearing_cache: np.ndarray | None = None


def _dijkstra(cost: np.ndarray) -> np.ndarray:
    """Cheapest path from the machine to every cell, eight-connected.

    Rock is passable, at cost 1.0. That is not an oversight: the shock travels in the
    massif, the caves are not in its path, and four cells of stone between you and the
    machine buys exactly nothing.
    """
    height, width = cost.shape
    dist = np.full((height, width), np.inf, dtype=np.float64)
    ax, ay = cave.ANCIENT_POS
    start = (int(ay), int(ax))
    dist[start] = 0.0
    queue: list[tuple[float, int, int]] = [(0.0, start[0], start[1])]
    diag = math.sqrt(2.0)
    steps = ((-1, 0, 1.0), (1, 0, 1.0), (0, -1, 1.0), (0, 1, 1.0),
             (-1, -1, diag), (-1, 1, diag), (1, -1, diag), (1, 1, diag))
    while queue:
        d, y, x = heapq.heappop(queue)
        if d > dist[y, x]:
            continue
        for dy, dx, length in steps:
            ny, nx = y + dy, x + dx
            if not (0 <= ny < height and 0 <= nx < width):
                continue
            nd = d + length * float(cost[ny, nx])
            if nd < dist[ny, nx]:
                dist[ny, nx] = nd
                heapq.heappush(queue, (nd, ny, nx))
    return dist


def medium_factor() -> np.ndarray:
    """How much shorter the shock's path to each cell is than an ordinary one.

    A ratio of two Dijkstras from the machine -- one where a flooded cell costs
    ANCIENT_WATER_COST and one where every cell costs the same -- so it is
    dimensionless, and the coupled distance is euclidean * factor.

    A ratio rather than a grid distance on purpose. This project's best beat is a
    0.038-cell margin, and an eight-connected Dijkstra distance carries up to 8%
    metric error plus a cell of quantisation, which would convert that near miss into
    a death. As a ratio the field is exactly 1.000 on every one of the 529 walkable
    cells within 20 cells of the machine (measured), so the beat survives to the third
    decimal, and the only thing water changes is the drawn tongue running 33.6 cells
    up the flooded ANC->SUMP passage against 17.9 on a dry bearing.

    Built once. The cave does not move in Phase 1.
    """
    global _factor_cache
    if _factor_cache is None:
        wet = _dijkstra(np.where(cave.GRID == 2, T.ANCIENT_WATER_COST, 1.0))
        dry = _dijkstra(np.ones(cave.GRID.shape, dtype=np.float64))
        factor = np.divide(wet, dry, out=np.ones_like(wet), where=dry > 0.0)
        _factor_cache = np.where(np.isfinite(factor), factor, 1.0)
    return _factor_cache


def _range_term() -> np.ndarray:
    """(radius / coupled distance)^2 at every cell centre: coupling with gain removed.

    The aim only multiplies this, so the expensive half of the field is built once and
    a new bearing costs three numpy operations.
    """
    global _base_cache
    if _base_cache is None:
        ax, ay = cave.ANCIENT_POS
        yy, xx = np.mgrid[0:cave.H, 0:cave.W]
        coupled = np.hypot(xx + 0.5 - ax, yy + 0.5 - ay) * medium_factor()
        _base_cache = (T.ANCIENT_RADIUS / np.maximum(coupled, 1e-6)) ** 2
    return _base_cache


def _cell_bearing() -> np.ndarray:
    """The world bearing from the machine to every cell centre, in radians."""
    global _bearing_cache
    if _bearing_cache is None:
        ax, ay = cave.ANCIENT_POS
        yy, xx = np.mgrid[0:cave.H, 0:cave.W]
        _bearing_cache = np.arctan2(yy + 0.5 - ay, xx + 0.5 - ax)
    return _bearing_cache


class Ancient:
    """Deterministic hazard on a fixed period, pointing somewhere.

    The signature ramps up over ANCIENT_WARNING_S and then the hazard is lethal for
    ANCIENT_LETHAL_S. An agent that listens has time to leave; an agent that is off
    the axis takes a third of the dose; an agent that is neither is killed. It is not
    a random hazard and it is not a trap -- the warning is always there to be heard,
    and the slew that says WHERE runs three seconds before the warning starts.
    """

    def __init__(self) -> None:
        self.x: float
        self.y: float
        self.x, self.y = cave.ANCIENT_POS
        self.factor: np.ndarray = medium_factor()

    # ---- the cycle -------------------------------------------------------------------
    def phase(self, t: float) -> float:
        return (t + T.ANCIENT_PHASE_S) % T.ANCIENT_PERIOD_S

    def firing_index(self, t: float) -> int:
        """Which firing the cycle now running will end with. 0 is the one at 0:41."""
        return int(math.floor((t + T.ANCIENT_PHASE_S) / T.ANCIENT_PERIOD_S))

    def aim_deg(self, index: int) -> float:
        """The survey azimuth of firing `index`. A survey covers ground, so the aim
        indexes the same way every cycle and ten firings is one revolution."""
        return (T.ANCIENT_AIM_0_DEG + T.ANCIENT_AIM_STEP_DEG * index) % 360.0

    def bearing_deg(self, t: float) -> float:
        """Where the array is pointing right now, swinging through the slew.

        Before the slew it still holds the last firing's bearing -- the machine does
        not commit to what it is about to do any earlier than a watcher can see it.
        """
        index = self.firing_index(t)
        p = self.phase(t)
        if p >= _LOCK_AT:
            return self.aim_deg(index)
        previous = self.aim_deg(index - 1)
        if p < _SLEW_AT:
            return previous
        swung = T.ANCIENT_AIM_STEP_DEG * (p - _SLEW_AT) / T.ANCIENT_SLEW_S
        return (previous + swung) % 360.0

    def is_slewing(self, t: float) -> bool:
        return _SLEW_AT <= self.phase(t) < _LOCK_AT

    def state(self, t: float) -> AncientPhase:
        p = self.phase(t)
        if p < _SLEW_AT:
            return AncientPhase.LISTENING
        if p < _LOCK_AT:
            return AncientPhase.SLEW
        if p < _WIND_AT:
            return AncientPhase.LOCKED
        if p < _LETHAL_AT:
            return AncientPhase.WIND
        if p < _LETHAL_AT + T.ANCIENT_FIRE_S:
            return AncientPhase.FIRING
        return AncientPhase.LETHAL

    def state_progress(self, t: float) -> float:
        """0..1 through whichever phase it is in.

        Across the wind this is the winch taking load: nine clicks at 1 Hz is twenty
        recorded frames each, which is countable rather than a strobe, and a policy
        that hears click seven knows more than one that hears click two.
        """
        p = self.phase(t)
        spans = ((_SLEW_AT, 0.0), (_LOCK_AT, _SLEW_AT), (_WIND_AT, _LOCK_AT),
                 (_LETHAL_AT, _WIND_AT), (_LETHAL_AT + T.ANCIENT_FIRE_S, _LETHAL_AT),
                 (T.ANCIENT_PERIOD_S, _LETHAL_AT + T.ANCIENT_FIRE_S))
        for end, start in spans:
            if p < end:
                return (p - start) / (end - start)
        return 1.0

    def signature_strength(self, t: float) -> float:
        """0 while quiet, ramping 0.3 -> 1.0 across the warning, 1.0 while lethal."""
        p = self.phase(t)
        if p < _WIND_AT:
            return 0.0
        if p < _LETHAL_AT:
            return 0.3 + 0.7 * (p - _WIND_AT) / T.ANCIENT_WARNING_S
        return 1.0

    def is_lethal(self, t: float) -> bool:
        return self.phase(t) >= _LETHAL_AT

    def is_firing_tick(self, t: float) -> bool:
        """The instant the hammer lands. The blow is an instant, so this is the one
        tick in the cycle on which a dose is taken."""
        return self.is_lethal(t) and not self.is_lethal(t - T.DT)

    def seconds_until_lethal(self, t: float) -> float:
        """Only ever used by truth-side logging and the spectator screen, never by a
        policy."""
        p = self.phase(t)
        return (_LETHAL_AT - p) if p <= _LETHAL_AT else (T.ANCIENT_PERIOD_S - p + _LETHAL_AT)

    # ---- the pointing hazard -----------------------------------------------------------
    def in_zone(self, x: float, y: float) -> bool:
        """The plain nine-cell disc, kept for the zone flag the director and the truth
        log read.

        Deliberately NOT the hazard any more: Appendix B keeps ANCIENT_RADIUS as a
        camera constant so the shot behaves exactly as it does today, while what
        actually hurts you is coupling_at. Change what 9 means; do not change 9.
        """
        return (x - self.x) ** 2 + (y - self.y) ** 2 < T.ANCIENT_RADIUS ** 2

    def coupling_at(self, x: float, y: float, t: float) -> float:
        """How much of the blow arrives here. One scalar, and it is the whole model.

            gain(theta) = 0.35 + 0.65 * cos^2(theta - aim)
            coupling    = gain(theta) * (9 / d)^2,   d = coupled distance in cells

        Lethal is coupling >= 1.0: 9.00 cells on the axis, 5.32 at the flank. There is
        no second radius and no threshold anywhere in the damage -- the same line that
        grades a near miss decides the kill.
        """
        dx, dy = x - self.x, y - self.y
        euclid = math.hypot(dx, dy)
        if euclid < 1e-6:
            return float("inf")
        xi = min(max(int(x), 0), cave.W - 1)
        yi = min(max(int(y), 0), cave.H - 1)
        coupled = euclid * float(self.factor[yi, xi])
        offset = math.atan2(dy, dx) - math.radians(self.bearing_deg(t))
        gain = T.ANCIENT_LOBE_FLOOR + (1.0 - T.ANCIENT_LOBE_FLOOR) * math.cos(offset) ** 2
        return gain * (T.ANCIENT_RADIUS / coupled) ** 2

    def coupling_field(self, t: float) -> np.ndarray:
        """The same number at every cell centre, for the spectator screen to draw.

        The drawn footprint is visibly lopsided toward the water every cycle and the
        shape is the explanation: there is a boundary, it is drawn, and it is not a
        circle.
        """
        offset = _cell_bearing() - math.radians(self.bearing_deg(t))
        gain = T.ANCIENT_LOBE_FLOOR + (1.0 - T.ANCIENT_LOBE_FLOOR) * np.cos(offset) ** 2
        return gain * _range_term()
