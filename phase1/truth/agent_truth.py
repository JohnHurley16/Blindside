"""Where an agent actually is. Never visible to a policy."""
from __future__ import annotations

import math

import numpy as np

from .. import geometry as G
from .. import tuning as T
from . import cave


class AgentTruth:
    """The real pose, cargo and liveness of one agent.

    `last_true_delta` is the motion actually achieved this tick. The sensor layer
    corrupts it into odometry; the difference between the two is drift, and it is
    the only place drift is born.
    """

    def __init__(self, name: str, x: float, y: float, heading_deg: float, seed: int,
                 sensor: str = "sonar") -> None:
        self.name: str = name
        self.sensor: str = sensor          # the active sensor this chassis carries
        self.x: float = float(x)
        self.y: float = float(y)
        self.heading: float = math.radians(heading_deg)
        self.alive: bool = True
        self.extracted: bool = False
        self.audible_until: float = -1.0
        self.cargo: int = 0
        self.rng: np.random.Generator = np.random.default_rng(seed)
        # Each agent leans a different way, so the two maps do not smear identically.
        self.drift_sign_scale: float = 1.0 if self.rng.random() < 0.5 else -1.0
        self.drift_sign_heading: float = 1.0 if self.rng.random() < 0.5 else -1.0
        self.last_true_delta: tuple[float, float] = (0.0, 0.0)
        self.in_ancient: bool = False

    @property
    def active(self) -> bool:
        return self.alive and not self.extracted

    def move(self, desired_heading: float, speed: float, dt: float) -> None:
        """Turn toward a heading at a limited rate, then step with wall sliding."""
        if not self.active:
            self.last_true_delta = (0.0, 0.0)
            return
        delta = G.wrap(desired_heading - self.heading)
        max_turn = math.radians(T.AGENT_TURN_RATE) * dt
        turn = G.clamp(delta, -max_turn, max_turn)
        self.heading = G.wrap(self.heading + turn)
        step = speed * dt
        dx = math.cos(self.heading) * step
        dy = math.sin(self.heading) * step
        moved = 0.0
        for tx, ty in ((self.x + dx, self.y + dy), (self.x + dx, self.y), (self.x, self.y + dy)):
            if self._clear(tx, ty):
                moved = math.hypot(tx - self.x, ty - self.y)
                self.x, self.y = tx, ty
                break
        self.last_true_delta = (moved, turn)

    def _clear(self, x: float, y: float) -> bool:
        r = T.AGENT_RADIUS
        return all(cave.is_walkable(x + ox, y + oy)
                   for ox, oy in ((0.0, 0.0), (r, 0.0), (-r, 0.0), (0.0, r), (0.0, -r)))

    def __repr__(self) -> str:
        return f"<AgentTruth {self.name} ({self.x:.1f},{self.y:.1f}) cargo={self.cargo}>"
