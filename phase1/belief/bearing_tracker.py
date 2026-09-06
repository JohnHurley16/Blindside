"""Turning a pile of bearings into a guess at where something is.

Passive sensing gives direction and no range, so one bearing tells you nothing about
distance. Two bearings taken from *different places* cross somewhere, and that
crossing is a position. DESIGN calls this out as the point of bearing-only tracking:
it is a skill involving deliberate movement, not a readout.

So this is the agent working something out, not being told it. If it has not moved
far enough between observations the lines are nearly parallel, the crossing is
garbage, and the honest answer is that it still does not know -- which is what
`estimate` returns.
"""
from __future__ import annotations

import math

import numpy as np

from .. import geometry as G
from .bearing_observation import BearingObservation
from .pose_correction import PoseCorrection

# Below this the bearings are so close to parallel that the crossing means nothing at
# all. Above it, poor conditioning does not hide the answer -- it widens it, because
# "somewhere vaguely over there" is real information and refusing to draw it is not.
MIN_CONDITION: float = 0.012
GOOD_CONDITION: float = 0.22
MAX_OBSERVATIONS: int = 60
# How fast the drawn centre chases a new solution. Bearings in a cave follow passages
# rather than pointing through rock, so raw solutions jump around; smoothing turns
# that into a zone that drifts, which is honest and readable, instead of one that
# teleports ninety cells between frames.
SMOOTHING: float = 0.12
BASE_UNCERTAINTY: float = 5.0
CONDITION_PENALTY: float = 42.0


class BearingTracker:
    """Least-squares intersection of bearing lines, weighted by return quality."""

    def __init__(self, memory_seconds: float) -> None:
        self.memory_seconds: float = memory_seconds
        self.observations: list[BearingObservation] = []
        self._estimate: tuple[float, float, float] | None = None
        self._smoothed: tuple[float, float] | None = None

    def add(self, x: float, y: float, bearing: float, quality: float, t: float) -> None:
        self.observations.append(BearingObservation(x, y, bearing, quality, t))
        if len(self.observations) > MAX_OBSERVATIONS:
            del self.observations[:-MAX_OBSERVATIONS]

    def forget_before(self, t: float) -> None:
        cutoff = t - self.memory_seconds
        if self.observations and self.observations[0].t < cutoff:
            self.observations = [o for o in self.observations if o.t >= cutoff]
            self._estimate = None

    def relax(self, correction: PoseCorrection) -> None:
        """A fix moves the map, so it moves where the agent thought it was standing
        when it heard something, and therefore moves the thing it heard."""
        if not self.observations:
            return
        xs = np.array([o.x for o in self.observations])
        ys = np.array([o.y for o in self.observations])
        ts = np.array([o.t for o in self.observations])
        nx, ny = correction.apply(xs, ys, ts)
        for obs, x, y, t in zip(self.observations, nx.tolist(), ny.tolist(), ts.tolist()):
            obs.x, obs.y = x, y
            obs.bearing = G.wrap(obs.bearing + correction.dtheta * correction.weight_at(t))
        self._estimate = None

    def estimate(self) -> tuple[float, float, float] | None:
        """(x, y, sigma) in the belief frame, or None while it is still guessing.

        sigma is the spread of each bearing line's closest approach to the solution:
        small when the lines agree, large when they do not.
        """
        # Count first: a stale cache outlived its observations and kept reporting a
        # position for something the agent had long since stopped hearing.
        if len(self.observations) < 2:
            return None
        if self._estimate is not None:
            return self._estimate
        a = np.zeros((2, 2))
        b = np.zeros(2)
        for o in self.observations:
            d = np.array([math.cos(o.bearing), math.sin(o.bearing)])
            p = np.array([o.x, o.y])
            w = max(o.quality, 0.05)
            m = np.eye(2) - np.outer(d, d)
            a += w * m
            b += w * (m @ p)
        # A near-singular system means every bearing pointed the same way, which
        # happens when the agent has not moved. It has learnt nothing about range.
        det = float(np.linalg.det(a))
        trace = float(np.trace(a))
        if trace <= 1e-9:
            return None
        condition = det / (trace * trace)
        if condition < MIN_CONDITION:
            return None
        try:
            point = np.linalg.solve(a, b)
        except np.linalg.LinAlgError:
            return None
        residuals: list[float] = []
        for o in self.observations:
            d = np.array([math.cos(o.bearing), math.sin(o.bearing)])
            v = point - np.array([o.x, o.y])
            residuals.append(abs(float(v[0] * d[1] - v[1] * d[0])))
        residual_rms = float(np.sqrt(np.mean(np.square(residuals)))) if residuals else 0.0
        vagueness = max(0.0, (GOOD_CONDITION - min(condition, GOOD_CONDITION)) / GOOD_CONDITION)
        sigma = residual_rms + BASE_UNCERTAINTY + CONDITION_PENALTY * vagueness ** 2

        if self._smoothed is None:
            self._smoothed = (float(point[0]), float(point[1]))
        else:
            sx, sy = self._smoothed
            self._smoothed = (sx + (float(point[0]) - sx) * SMOOTHING,
                              sy + (float(point[1]) - sy) * SMOOTHING)
        self._estimate = (self._smoothed[0], self._smoothed[1], sigma)
        return self._estimate

    def invalidate(self) -> None:
        self._estimate = None

    def forget_all(self) -> None:
        self.observations.clear()
        self._estimate = None
        self._smoothed = None
