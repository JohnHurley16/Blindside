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

    `damage` is what the Assayer's shock has done to it, in [0, 1]. It costs the
    machine two things and only two: how far its active sensor reaches, and how fast
    it walks. A hurt machine maps less ground per sweep and covers less ground per
    minute, and nothing on the belief side tells it either. It is truth, and the
    policy never sees it.
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
        self.damage: float = 0.0

    @property
    def active(self) -> bool:
        return self.alive and not self.extracted

    @property
    def sensor_range_multiplier(self) -> float:
        """How far the active sensor still reaches, as a fraction of its nominal range.

        Frames survive shock; precision does not, so the transducer is the first thing
        to go, at DAMAGE_RANGE_FROM. Below that this is exactly 1.0 -- a machine that
        took a scratch at forty cells is not yet a machine with a broken part.

        **Nothing tells the agent this happened.** The far returns simply stop
        arriving, and the returns it does get are scored for quality against the
        nominal range, so a near wall looks exactly as good as it always did. What it
        loses is reach, and the only way it can find that out is by noticing that the
        map stopped growing ahead of it.

        There used to be a `drift_multiplier` here that scaled the truth-side dead
        reckoning coefficients instead. It was cut: THE-MACHINERY 11 pre-committed to
        an A/B on it, the A/B failed -- the damaged machine ended up LESS wrong than
        the healthy one, and the effect was not monotone in its own gain -- and the
        pre-commitment names speed and sensor range as the replacement.
        """
        if self.damage < T.DAMAGE_RANGE_FROM:
            return 1.0
        return 1.0 - T.DAMAGE_RANGE_LOSS * self.damage

    def take_shock(self, dose: float) -> None:
        """One firing's dose of ground shock. Monotone: nothing repairs in a match.

        Nothing tells the policy this number, and no predicate reads it. In Phase 3
        the agent learns it through `Return::SelfReport`, which is a sensor and so can
        be wrong, and at 0.85 damage the health monitor freezes and it stops knowing
        it is dying. Here it reaches the spectator screen and goes nowhere else.
        """
        if not self.alive:
            return
        self.damage = min(1.0, self.damage + dose)
        if self.damage >= 1.0:
            self.alive = False

    def move(self, desired_heading: float, speed: float, dt: float) -> None:
        """Turn toward a heading at a limited rate, then step with wall sliding."""
        if not self.active:
            self.last_true_delta = (0.0, 0.0)
            return
        delta = G.wrap(desired_heading - self.heading)
        max_turn = math.radians(T.AGENT_TURN_RATE) * dt
        turn = G.clamp(delta, -max_turn, max_turn)
        self.heading = G.wrap(self.heading + turn)
        # The drive breaks one rung after the transducer, because a chassis is the
        # sturdiest thing on the machine. The policy asks for a speed and gets less; it
        # finds that out through its own odometry, if it finds out at all. Below
        # DAMAGE_SPEED_FROM this line does nothing, so an undamaged machine walks
        # exactly the distance it always did and a scratch changes no path.
        step = speed * dt
        if self.damage >= T.DAMAGE_SPEED_FROM:
            step *= 1.0 - T.DAMAGE_SPEED_LOSS * self.damage
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
        return (f"<AgentTruth {self.name} ({self.x:.1f},{self.y:.1f}) "
                f"cargo={self.cargo} damage={self.damage:.2f}>")
