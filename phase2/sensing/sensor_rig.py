"""The sensor layer.

**This is the only module in the project that reads both World and the inputs to
Belief.** It takes ground truth and produces returns: noisy, sometimes wrong.
Everything downstream sees returns only.

It is one class in one file so it can be audited by reading it.
"""
from __future__ import annotations

import math

import numpy as np

from .. import geometry as G
from .. import tuning as T
from ..truth.agent_truth import AgentTruth
from ..truth.world import World
from .returns import CargoReturn, JunctionReturn, OdometryReturn, Return, ShaftFixReturn


class SensorRig:
    """Per-run sensor state. Holds no belief and no policy."""

    def __init__(self, seed: int, drift: bool = True) -> None:
        self.rng: np.random.Generator = np.random.default_rng([seed, 2])
        self.drift: bool = drift              # False for the tutorial's first run
        self._in_range: bool = False
        self._reported_stop: bool = False

    # ---- the one entry point ---------------------------------------------------------
    def sample(self, world: World) -> list[Return]:
        me = world.agent
        out: list[Return] = [self._odometry(me)]
        if me.stopped:
            if not self._reported_stop:
                self._reported_stop = True
                out.append(self._junction(world, me))
                out.append(CargoReturn(me.cargo))
        else:
            self._reported_stop = False
        fix = self._shaft(world, me)
        if fix is not None:
            out.append(fix)
        return out

    # ---- dead reckoning ---------------------------------------------------------------
    def _odometry(self, me: AgentTruth) -> OdometryReturn:
        """The true displacement, corrupted by bias and noise. Phase 1's model.

        Bias dominates noise on purpose: a bias makes the error lean consistently,
        a random walk only makes it fuzzy.
        """
        forward, turn = me.last_true_delta
        if not self.drift:
            return OdometryReturn(forward, turn)
        scale = 1.0 + T.DR_SCALE_BIAS * me.drift_sign_scale
        root = math.sqrt(max(forward, 1e-9))
        measured = forward * scale + float(self.rng.normal(0.0, T.DR_POS_NOISE_PER_CELL * root))
        heading_bias = math.radians(T.DR_HEADING_BIAS_DEG_PER_CELL) * me.drift_sign_heading * forward
        heading_noise = float(self.rng.normal(0.0, math.radians(T.DR_HEADING_NOISE_DEG_PER_CELL) * root))
        return OdometryReturn(measured, turn + heading_bias + heading_noise)

    # ---- the near-field sense at a stop -------------------------------------------------
    def _junction(self, world: World, me: AgentTruth) -> JunctionReturn:
        """Every passage mouth at the node, in body frame, each bearing jittered."""
        assert me.node is not None
        noise = math.radians(T.JUNCTION_BEARING_NOISE_DEG)
        bearings = tuple(
            G.wrap(bearing - me.heading + float(self.rng.normal(0.0, noise)))
            for _, bearing in world.corridor.passages_at(me.node)
        )
        return JunctionReturn(bearings)

    # ---- the shaft beacon -----------------------------------------------------------------
    def _shaft(self, world: World, me: AgentTruth) -> ShaftFixReturn | None:
        """A fix on the rising edge of entering the beacon's range, as in Phase 1:
        once as you arrive, not continuously, so the agent is not pinned to it."""
        in_range = world.in_shaft_range()
        rising = in_range and not self._in_range
        self._in_range = in_range
        if not rising:
            return None
        d = world.shaft_distance()
        # Down the shaft passage the beacon lies behind the agent when it is walking
        # home, ahead when it is walking out, and nowhere in particular at the shaft.
        first = world.corridor.passages[world.corridor.children(world.corridor.shaft)[0]]
        world_bearing = G.wrap(first.bearing + math.pi) if me.passage == first.id else me.heading
        noisy_r = max(0.0, d + float(self.rng.normal(0.0, T.SHAFT_FIX_RANGE_NOISE)))
        noisy_b = G.wrap(world_bearing - me.heading
                         + float(self.rng.normal(0.0, math.radians(T.SHAFT_FIX_BEARING_NOISE_DEG))))
        heading_ref = G.wrap(me.heading
                             + float(self.rng.normal(0.0, math.radians(T.SHAFT_HEADING_REF_NOISE_DEG))))
        return ShaftFixReturn(noisy_r, noisy_b, heading_ref)
