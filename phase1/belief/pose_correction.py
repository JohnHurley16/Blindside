"""A fix, expressed as something that can be applied to the map behind you.

This is the single most important piece of Phase 1 and the easiest to get wrong.

A fix corrects the pose estimate *now*. Points already placed do not move on their
own, so the naive implementation leaves the ghost corridor sitting there forever and
the only thing that "snaps" is the agent marker. The doubled corridor collapsing
onto itself -- the visual the whole test is built around -- never happens.

So instead: every point carries the time it was placed, and a fix applies its
correction to everything placed since the previous fix, weighted by how far into
the drift interval each point was. Points from just after the last fix barely move;
points from just now move the whole way. The ghost slides onto the original.

That is one loop closure of a pose graph, done by hand. A spoofed fix runs exactly
this same code and drags the recent map somewhere wrong, tearing it away from the
older map. Nothing here knows the difference.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


@dataclass(slots=True)
class PoseCorrection:
    """Interpolated rigid correction over one drift interval."""

    epoch_t: float          # when the previous fix happened
    span: float             # seconds of drift being corrected
    origin_x: float         # the pose at the epoch: the anchored end
    origin_y: float
    dtheta: float           # heading correction at full weight
    dx: float               # translation correction at full weight
    dy: float

    def weights(self, ts: np.ndarray) -> np.ndarray:
        return np.clip((ts - self.epoch_t) / self.span, 0.0, 1.0)

    def apply(self, xs: np.ndarray, ys: np.ndarray,
              ts: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Rotate about the anchored end and translate, both scaled by weight."""
        w = self.weights(ts)
        a = w * self.dtheta
        ca, sa = np.cos(a), np.sin(a)
        ox, oy = self.origin_x, self.origin_y
        rx = ox + ca * (xs - ox) - sa * (ys - oy)
        ry = oy + sa * (xs - ox) + ca * (ys - oy)
        return rx + w * self.dx, ry + w * self.dy

    def apply_one(self, x: float, y: float, t: float) -> tuple[float, float]:
        nx, ny = self.apply(np.array([x]), np.array([y]), np.array([t]))
        return float(nx[0]), float(ny[0])

    def weight_at(self, t: float) -> float:
        return float(min(1.0, max(0.0, (t - self.epoch_t) / self.span)))

    @staticmethod
    def between(epoch_t: float, now: float, origin_x: float, origin_y: float,
                pre_x: float, pre_y: float, post_x: float, post_y: float,
                dtheta: float) -> "PoseCorrection":
        """Build the correction that takes the pre-fix pose to the post-fix pose."""
        span = max(now - epoch_t, 1e-6)
        c, s = math.cos(dtheta), math.sin(dtheta)
        rotated_x = origin_x + c * (pre_x - origin_x) - s * (pre_y - origin_y)
        rotated_y = origin_y + s * (pre_x - origin_x) + c * (pre_y - origin_y)
        return PoseCorrection(epoch_t, span, origin_x, origin_y, dtheta,
                              post_x - rotated_x, post_y - rotated_y)
