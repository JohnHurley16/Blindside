"""One fix, kept for the display.

The size of a fix is itself information the player can act on, and it is derived
entirely from belief: a fix that moves you forty cells when the ellipse promised six
is the tell that something lied to you. Rendering it is legal and it is the cheapest
way to give a player a chance of catching the spoof.
"""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class FixRecord:
    t: float
    beacon_id: str
    pre_x: float
    pre_y: float
    post_x: float
    post_y: float
    dtheta: float
    sigma_before: float

    @property
    def jump(self) -> float:
        return math.hypot(self.post_x - self.pre_x, self.post_y - self.pre_y)

    @property
    def surprise(self) -> float:
        """How many sigma the jump was. Large means the estimator was confident and
        wrong, which is exactly what a spoof looks like from the inside."""
        return self.jump / max(self.sigma_before, 1e-6)
