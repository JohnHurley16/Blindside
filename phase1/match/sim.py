"""The match loop. Owns World, the sensor rigs, the beliefs and the policies.

Order each tick: policy(Belief) -> world moves -> sensors sample -> belief fuses.
The renderer and the audio mixer are handed Belief objects only, through the
`MatchView` facade -- there is no `world` attribute on this object to reach.

Truth leaves here by exactly two doors, both one-way and both returning frozen plain
data: `reveal()`, guarded on the match being over, and `stage()`, the live spectator
export, guarded on the channel being switched on and on not being inside a tick.
SPECTATOR-DISPLAY.md section 4.
"""
from __future__ import annotations

import math

import numpy as np

from .. import geometry as G
from .. import tuning as T
from ..belief.belief import Belief
from ..policy.policy import Policy
from ..sensing.sensor_rig import SensorRig
from ..sound_character import SoundCharacter
from ..truth import cave
from ..truth.pending_sound import PendingSound
from ..truth.world import World
from .match_result import MatchResult
from .reveal import Reveal
from .stage_builder import StageBuilder
from .stage_frame import StageFrame


def snap_to_tick(t: float) -> float:
    return round(t / T.DT) * T.DT


class Sim:
    def __init__(self, seed: int = T.SEED, stage: bool = False) -> None:
        """`stage` switches the truth channel on. It is off by default, so --headless,
        --invariant and any future batch or training path never build a frame at all:
        the leak has to be deliberately enabled rather than merely not used."""
        self._world: World = World()
        self.t: float = 0.0
        self.tick: int = 0
        self.over: bool = False
        self.result: MatchResult | None = None
        self.recall_at: float | None = None
        self.recall_used: bool = False
        self.truth_trail: dict[str, list[tuple[float, float, float]]] = {
            name: [] for name in self._world.agents}

        rng = np.random.default_rng(seed)
        places: dict[str, tuple[float, float]] = {
            name: (float(c[0]), float(c[1])) for name, c in cave.CHAMBERS.items()}

        self.beliefs: dict[str, Belief] = {}
        self.rigs: dict[str, SensorRig] = {}
        self.policies: dict[str, Policy] = {}
        for name, agent in self._world.agents.items():
            known = dict(places)
            known["HOME"] = cave.SHAFTS[name]
            belief = Belief(name, agent.x, agent.y, agent.heading, known,
                            np.random.default_rng(int(rng.integers(1 << 30))),
                            sensor=agent.sensor)
            shaft_id = f"shaft_{name}"
            belief.note_surveyed_beacon(shaft_id, *cave.SHAFTS[name])
            self.beliefs[name] = belief
            self.rigs[name] = SensorRig(name, int(rng.integers(1 << 30)))

        self.policies["player"] = Policy(
            self.beliefs["player"],
            {"out_A": cave.ROUTES["player_out_A"],
             "A_to_B": cave.ROUTES["player_A_to_B"],
             "home_from_A": cave.ROUTES["player_home_from_A"],
             "home_from_B": cave.ROUTES["player_home_from_B"]},
            cautious=True, shaft_beacon_id="shaft_player")
        self.policies["rival"] = Policy(
            self.beliefs["rival"], {"out": cave.ROUTES["rival_out"]},
            cautious=False, shaft_beacon_id="shaft_rival")

        # The scripted echo: the same ping arriving a second time off a reflective
        # chamber, on a different bearing because it came by a different passage.
        for t_echo in (T.ECHO_TIMES):
            self._world.pending_sounds.append(
                PendingSound(snap_to_tick(t_echo), cave.ECHO_POS[0], cave.ECHO_POS[1],
                             SoundCharacter.PING))

        self._spoof_target: str | None = None
        self._spoof_arm_dist: float = 0.0

        # ---- the truth channel, off unless switched on ----
        self._stage_enabled: bool = stage
        self._in_tick: bool = False
        self._spoof_arm: float = 0.0
        self._error_history: list[tuple[float, float, float]] = []
        self._next_error_sample: float = 0.0

    # ---- the one player input ---------------------------------------------------------
    def recall(self) -> bool:
        if self.recall_used or self.over:
            return False
        self.recall_used = True
        depth = math.hypot(self._world.agents["player"].x - cave.SHAFTS["player"][0],
                           self._world.agents["player"].y - cave.SHAFTS["player"][1])
        self.recall_at = self.t + T.RECALL_DELAY_S + T.RECALL_LATENCY_PER_CELL * depth
        return True

    @property
    def recall_pending(self) -> bool:
        return self.recall_at is not None

    # ---- one tick ---------------------------------------------------------------------
    def step(self) -> None:
        if self.over:
            return
        # A runtime tripwire, not a style: no stage frame may be built from inside a
        # tick, so no sensor, belief or policy path can route through one by accident.
        self._in_tick = True
        try:
            self._tick()
        finally:
            self._in_tick = False

    def _tick(self) -> None:
        self.tick += 1
        self.t = self.tick * T.DT
        w = self._world
        w.t = self.t
        w.tick = self.tick

        if self.recall_at is not None and self.t >= self.recall_at:
            self.policies["player"].recall(self.t)
            self.recall_at = None

        self._script()

        for name, agent in w.agents.items():
            if not agent.active:
                continue
            belief = self.beliefs[name]
            policy = self.policies[name]
            rig = self.rigs[name]
            cmd = policy.step(self.t)
            agent.move(cmd.heading, cmd.speed, T.DT)
            if cmd.drop:
                bid = w.drop_beacon(name)
                belief.note_beacon_drop(bid, self.t)
                rig.beacons_in_range.add(bid)     # standing on it; no fix until you return
            if cmd.ping:
                belief.note_ping(self.t)
                w.log("ping", agent=name, x=agent.x, y=agent.y)
            w.step_loading(name, cmd.load)
            belief.fuse(rig.sample(w, agent, cmd, self.t), self.t)

        w.step_hazards()
        w.expire_sounds()
        self._extraction()
        if self._stage_enabled and self.t >= self._next_error_sample:
            self._next_error_sample = self.t + 1.0 / T.ERROR_SAMPLE_HZ
            agent, belief = w.agents["player"], self.beliefs["player"]
            self._error_history.append(
                (self.t, math.hypot(agent.x - belief.x, agent.y - belief.y),
                 belief.sigma_pos()))
        if self.t >= T.MATCH_SECONDS:
            self._finish("time")

    # ---- the scripted spoof -------------------------------------------------------------
    def _script(self) -> None:
        """After SPOOF_AFTER_S, pick the beacon the victim most recently dropped, then
        relocate it once the victim has walked far enough past it that the lie is
        worth telling.

        Deliberately not gated on the policy's mode. The earlier version required the
        victim to be in TRAVEL and to be exactly at a drop instant, and in a full run
        that window never opened: the uncertainty return fired first and the spoof
        could never happen at all.
        """
        w = self._world
        belief = self.beliefs["player"]
        if w.spoof_done or not w.agents["player"].alive or not belief.beacon_order:
            self._spoof_arm = 0.0
            return
        # Fire once the victim is SPOOF_LIE_CELLS *away from* its most recent beacon,
        # measured straight line in the belief frame, because that displacement is
        # what the lie will actually be. Using distance travelled instead gave a
        # 15.3-cell lie when the agent had doubled back on itself, and a 52.9-cell
        # one when it had not, against a tuned 34.
        target = belief.beacons[belief.beacon_order[-1]]
        gap = G.dist(belief.x, belief.y, target.x, target.y)
        threshold = T.SPOOF_LIE_CELLS - T.SPOOF_AHEAD_CELLS

        # The display's five seconds of held breath, for free. `_spoof_arm` is how
        # close that condition is to being met, as 0..1. Nothing in the sim reads it,
        # no branch changes and no event time moves -- the firing test below is the
        # one that was already here. SPECTATOR-DISPLAY.md section 8.
        self._spoof_arm = (
            G.clamp((gap - (threshold - T.SPOOF_ARM_CELLS)) / T.SPOOF_ARM_CELLS, 0.0, 1.0)
            if self.t >= T.SPOOF_AFTER_S - T.SPOOF_ARM_LEAD_S else 0.0)

        if self.t < T.SPOOF_AFTER_S:
            return
        if gap >= threshold:
            w.spoof("player", target.beacon_id)

    # ---- ending --------------------------------------------------------------------------
    def _extraction(self) -> None:
        w = self._world
        if self.t < T.EXTRACT_WINDOW_OPENS:
            return
        for name, agent in w.agents.items():
            sx, sy = cave.SHAFTS[name]
            if agent.active and math.hypot(agent.x - sx, agent.y - sy) < T.EXTRACT_RADIUS:
                agent.extracted = True
                w.log("extracted", agent=name, cargo=agent.cargo)
        if all(not a.active for a in w.agents.values()):
            self._finish("all resolved")

    def _finish(self, why: str) -> None:
        self.over = True
        p = self._world.agents["player"]
        outcome = "extracted" if p.extracted else ("destroyed" if not p.alive else "lost in the cave")
        self.result = MatchResult(why, outcome, p.cargo if p.extracted else 0,
                                  self.recall_used, self.t)
        self._world.log("end", why=why, player=outcome, cargo=self.result.cargo,
                       recall_used=self.recall_used)

    def record_truth_trail(self) -> None:
        for name, agent in self._world.agents.items():
            self.truth_trail[name].append((agent.x, agent.y, self.t))

    # ---- truth, live, one way, to the spectator screen ---------------------------------------
    def stage(self) -> StageFrame:
        """The live truth export for the spectator screen.

        A deliberate relaxation of reveal()'s `assert self.over`, and a category
        change: reveal fires once, this fires every frame. It is safe because what it
        returns is a frozen record of numbers with no route back to World; because
        stage_builder cannot see Belief or Policy; and because neither belief nor
        policy may import match, so neither can name StageFrame. match/invariant.py
        proves all three.
        """
        assert not self._in_tick, "a stage frame may not be built from inside a tick"
        assert self._stage_enabled, "the truth channel was not switched on"
        belief = self.beliefs["player"]
        return StageBuilder.of(self._world, self.truth_trail, self.t, self._spoof_arm,
                               (belief.x, belief.y, belief.theta), self._error_history)

    # ---- truth, only after the end ---------------------------------------------------------
    def reveal(self) -> Reveal:
        assert self.over, "truth is never rendered during the run"
        w = self._world
        walls, flooded = cave.wall_outline(), cave.flooded_cells()
        walls.flags.writeable = False
        flooded.flags.writeable = False
        return Reveal(
            walls=walls,
            flooded=flooded,
            agents={n: (a.x, a.y, a.alive, a.extracted) for n, a in w.agents.items()},
            beacons={bid: (b.x, b.y, b.owner) for bid, b in w.beacons.items()},
            ancient=(w.ancient.x, w.ancient.y, T.ANCIENT_RADIUS),
            deposits=dict(w.deposits),
            truth_trail={n: tuple(t) for n, t in self.truth_trail.items()},
        )
