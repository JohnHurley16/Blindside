"""The sensor layer.

**This is the only module in the project that reads both World and Belief's inputs.**
It takes ground truth and produces returns: noisy, sometimes ambiguous, sometimes
false. Everything downstream sees returns only.

It is one class in one file so it can be audited by reading it.
"""
from __future__ import annotations

import math

import numpy as np

from .. import geometry as G
from .. import tuning as T
from ..motor_command import MotorCommand
from ..point_source import PointSource
from ..sound_character import SoundCharacter
from ..truth import cave
from ..truth.agent_truth import AgentTruth
from ..truth.world import World
from .raycast import march
from .returns import (
    BearingReturn,
    BeaconFixReturn,
    CargoReturn,
    OdometryReturn,
    RangeBearingReturn,
    Return,
)
from .sound_field import SoundField


class SensorRig:
    """Per-agent sensor state. Holds no belief and no policy."""

    def __init__(self, name: str, seed: int) -> None:
        self.name: str = name
        self.rng: np.random.Generator = np.random.default_rng(seed)
        self.beacons_in_range: set[str] = set()
        self._last_beacon_fix: dict[str, float] = {}
        self.deaf_until: float = -1.0
        self.next_motion_listen: float = 0.0
        self.tick: int = 0
        self._ping_fields: dict[str, tuple[SoundField, float]] = {}
        self._ancient_field: SoundField | None = None

    # ---- the one entry point ---------------------------------------------------------
    def sample(self, world: World, me: AgentTruth, cmd: MotorCommand, t: float) -> list[Return]:
        self.tick += 1
        out: list[Return] = [self._odometry(me)]
        if cmd.ping:
            if me.sensor == "lidar":
                # Light, not sound: nothing in the basin hears this, and the agent
                # is not deafened by its own transmission. The cost is elsewhere.
                out.extend(self._lidar(me))
            else:
                out.extend(self._sonar(me))
                me.audible_until = t + T.SONAR_AUDIBLE_S
                self.deaf_until = t + T.SELF_DEAF_AFTER_PING_S
        if self.tick % T.NEARFIELD_PERIOD_TICKS == 0:
            out.extend(self._nearfield(me))
        if t >= self.deaf_until:
            out.extend(self._passive(world, me, t))
        out.extend(self._beacons(world, me, t))
        if cmd.load:
            out.append(CargoReturn(me.cargo))
        return out

    # ---- dead reckoning ---------------------------------------------------------------
    def _odometry(self, me: AgentTruth) -> OdometryReturn:
        """The true displacement, corrupted by bias and noise.

        Bias dominates noise on purpose: a bias makes the map lean consistently and
        ghost, a random walk only makes it fuzzy.
        """
        forward, turn = me.last_true_delta
        scale = 1.0 + T.DR_SCALE_BIAS * me.drift_sign_scale
        root = math.sqrt(max(forward, 1e-9))
        measured = forward * scale + self.rng.normal(0.0, T.DR_POS_NOISE_PER_CELL * root)
        heading_bias = math.radians(T.DR_HEADING_BIAS_DEG_PER_CELL) * me.drift_sign_heading * forward
        heading_noise = self.rng.normal(0.0, math.radians(T.DR_HEADING_NOISE_DEG_PER_CELL) * root)
        return OdometryReturn(measured, turn + heading_bias + heading_noise)

    # ---- active sonar -----------------------------------------------------------------
    def _sonar(self, me: AgentTruth) -> list[Return]:
        out: list[Return] = []
        half = math.radians(T.SONAR_ARC_DEG) / 2.0
        for i in range(T.SONAR_RAYS):
            b = -half + 2.0 * half * i / (T.SONAR_RAYS - 1)
            r = march(me.x, me.y, me.heading + b, T.SONAR_RANGE, ~cave.FREE)
            if r is None:
                continue
            quality = 1.0 - 0.7 * r / T.SONAR_RANGE
            noisy_r = r + self.rng.normal(0.0, T.SONAR_RANGE_NOISE + 0.02 * r)
            noisy_b = b + self.rng.normal(0.0, math.radians(T.SONAR_BEARING_NOISE_DEG))
            out.append(RangeBearingReturn(max(0.2, noisy_r), noisy_b, quality, PointSource.SONAR))
        for _ in range(T.SONAR_FALSE_RETURNS):
            out.append(RangeBearingReturn(
                float(self.rng.uniform(3.0, T.SONAR_RANGE)),
                float(self.rng.uniform(-half, half)),
                float(self.rng.uniform(*T.SONAR_FALSE_QUALITY)),
                PointSource.FALSE))
        return out

    # ---- lidar --------------------------------------------------------------------------
    def _lidar(self, me: AgentTruth) -> list[Return]:
        """A full silent sweep, precise and short, that stops dead at water.

        Sonar rays march against ~FREE, so sound crosses a flooded sump and maps the
        far wall. Lidar marches against ~WALKABLE, so the water surface ends the ray
        -- and returns it. A sump seen from the dry side is a wall over a mirror: the
        agent maps the waterline as solid, steers round it like any other wall, and
        never learns what is on the other side. That is the honest cost of carrying
        the quiet sensor, and the other side is where the machinery is. (Designer's
        call over the alternative, where water returned nothing and read as open
        space -- which would have sent it in.)
        """
        out: list[Return] = []
        if not cave.is_walkable(me.x, me.y):
            return out                    # standing in water: it sees nothing at all
        half = math.radians(T.LIDAR_ARC_DEG) / 2.0
        for i in range(T.LIDAR_RAYS):
            b = -half + 2.0 * half * i / T.LIDAR_RAYS
            r = march(me.x, me.y, me.heading + b, T.LIDAR_RANGE, ~cave.WALKABLE, step=0.25)
            if r is None:
                continue
            quality = 1.0 - 0.3 * r / T.LIDAR_RANGE
            noisy_r = r + self.rng.normal(0.0, T.LIDAR_RANGE_NOISE)
            noisy_b = b + self.rng.normal(0.0, math.radians(T.LIDAR_BEARING_NOISE_DEG))
            out.append(RangeBearingReturn(max(0.2, noisy_r), noisy_b, quality, PointSource.LIDAR))
        for _ in range(T.LIDAR_FALSE_RETURNS):
            out.append(RangeBearingReturn(
                float(self.rng.uniform(2.0, T.LIDAR_RANGE)), float(self.rng.uniform(-half, half)),
                float(self.rng.uniform(0.1, 0.3)), PointSource.FALSE))
        return out

    # ---- near field -------------------------------------------------------------------
    def _nearfield(self, me: AgentTruth) -> list[Return]:
        """The agent's own motion noise reflecting off walls a step or two away.

        Without this a corridor walked without pinging leaves no points at all, and
        a cautious agent's map is empty rather than sparse.
        """
        out: list[Return] = []
        for i in range(T.NEARFIELD_RAYS):
            b = 2.0 * math.pi * i / T.NEARFIELD_RAYS + float(self.rng.uniform(-0.2, 0.2))
            r = march(me.x, me.y, me.heading + b, T.NEARFIELD_RANGE, ~cave.WALKABLE, step=0.2)
            if r is not None:
                out.append(RangeBearingReturn(r + float(self.rng.normal(0.0, 0.15)), b,
                                              T.NEARFIELD_QUALITY, PointSource.NEAR))
        return out

    # ---- passive acoustic --------------------------------------------------------------
    def _bearing_return(self, me: AgentTruth, d: float, world_bearing: float,
                        max_range: float, character: SoundCharacter,
                        strength: float = 1.0) -> BearingReturn:
        quality = max(0.0, 1.0 - d / max_range)
        spread = T.BEARING_NOISE_NEAR_DEG + (T.BEARING_NOISE_FAR_DEG - T.BEARING_NOISE_NEAR_DEG) * (1.0 - quality)
        noisy = world_bearing - me.heading + float(self.rng.normal(0.0, math.radians(spread)))
        return BearingReturn(G.wrap(noisy), quality * strength, character)

    def _passive(self, world: World, me: AgentTruth, t: float) -> list[Return]:
        out: list[Return] = []
        for other in world.agents.values():
            if other is me or not other.active:
                continue
            if t < other.audible_until:
                cached = self._ping_fields.get(other.name)
                if cached is None or cached[1] != other.audible_until:
                    cached = (SoundField(other.x, other.y, T.HEAR_PING_RANGE), other.audible_until)
                    self._ping_fields[other.name] = cached
                hit = cached[0].arrival(me.x, me.y)
                if hit is not None and self.tick % 10 == 0:
                    out.append(self._bearing_return(me, hit[0], hit[1], T.HEAR_PING_RANGE,
                                                    SoundCharacter.PING))
            if t >= self.next_motion_listen and other.last_true_delta[0] > 0.0:
                self.next_motion_listen = t + T.MOTION_LISTEN_PERIOD
                if math.hypot(other.x - me.x, other.y - me.y) < T.HEAR_MOTION_RANGE:
                    field = SoundField(other.x, other.y, T.HEAR_MOTION_RANGE)
                    hit = field.arrival(me.x, me.y)
                    if hit is not None:
                        out.append(self._bearing_return(me, hit[0], hit[1], T.HEAR_MOTION_RANGE,
                                                        SoundCharacter.TONE))
        strength = world.ancient.signature_strength(t)
        if strength > 0.0 and self.tick % 5 == 0:
            if self._ancient_field is None:
                self._ancient_field = SoundField(world.ancient.x, world.ancient.y, T.HEAR_ANCIENT_RANGE)
            hit = self._ancient_field.arrival(me.x, me.y)
            if hit is not None:
                out.append(self._bearing_return(me, hit[0], hit[1], T.HEAR_ANCIENT_RANGE,
                                                SoundCharacter.SIGNATURE, strength))
        for sound in world.pending_sounds:
            if abs(sound.t - t) < T.DT / 2.0:
                field = SoundField(sound.x, sound.y, T.HEAR_CRASH_RANGE)
                hit = field.arrival(me.x, me.y)
                if hit is not None:
                    out.append(self._bearing_return(me, hit[0], hit[1], T.HEAR_CRASH_RANGE,
                                                    sound.character))
        return out

    # ---- beacons -----------------------------------------------------------------------
    def _beacons(self, world: World, me: AgentTruth, t: float) -> list[Return]:
        """Fixes fire on the rising edge of entering a transponder's range.

        Rising edge rather than continuously, so that walking past your own chain
        gives you a fix each time you pass rather than pinning you to it. The shaft
        is no different -- it just happens to be the one beacon whose recorded
        position is its true one.

        A transponder with a reassert period broadcasts instead of answering, and so
        keeps re-fixing you while you are inside its range. Nothing here knows why
        one beacon behaves that way and another does not.
        """
        out: list[Return] = []
        now: set[str] = set()
        for bid, beacon in world.beacons.items():
            if beacon.owner != me.name:
                continue
            d = math.hypot(beacon.x - me.x, beacon.y - me.y)
            if d >= beacon.range:
                continue
            now.add(bid)
            rising = bid not in self.beacons_in_range
            reasserting = (beacon.reassert_period > 0.0
                           and t - self._last_beacon_fix.get(bid, -1e9) >= beacon.reassert_period)
            if not (rising or reasserting):
                continue
            self._last_beacon_fix[bid] = t
            world_bearing = math.atan2(beacon.y - me.y, beacon.x - me.x)
            noisy_r = d + float(self.rng.normal(0.0, T.BEACON_FIX_NOISE))
            noisy_b = G.wrap(world_bearing - me.heading + float(self.rng.normal(0.0, math.radians(2.0))))
            out.append(BeaconFixReturn(bid, max(0.0, noisy_r), noisy_b))
        self.beacons_in_range = now
        return out
