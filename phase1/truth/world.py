"""Ground truth for the whole match.

Nothing downstream of the sensor layer may hold a reference to this object.
"""
from __future__ import annotations

import math
from typing import Any

from .. import tuning as T
from ..sound_character import SoundCharacter
from . import cave
from .agent_truth import AgentTruth
from .ancient import Ancient
from .beacon import Beacon
from .pending_sound import PendingSound
from .world_event import WorldEvent


class World:
    """Everything that is actually the case."""

    def __init__(self) -> None:
        self.t: float = 0.0
        self.tick: int = 0
        self.agents: dict[str, AgentTruth] = {}
        for index, (name, (sx, sy)) in enumerate(cave.SHAFTS.items()):
            heading = 0.0 if name == "player" else 180.0
            sensor = T.PLAYER_SENSOR if name == "player" else T.RIVAL_SENSOR
            self.agents[name] = AgentTruth(name, sx, sy, heading, T.SEED * 11 + index + 1,
                                           sensor=sensor)
        self.beacons: dict[str, Beacon] = {}
        for name, (sx, sy) in cave.SHAFTS.items():
            bid = f"shaft_{name}"
            self.beacons[bid] = Beacon(bid, sx, sy, name, truth_anchor=True)
        self.next_beacon_id: int = 1
        self.ancient: Ancient = Ancient()
        self.deposits: dict[str, tuple[float, float]] = dict(cave.DEPOSITS)
        self.spoof_done: bool = False
        self.events: list[WorldEvent] = []
        self.pending_sounds: list[PendingSound] = []
        self.load_progress: dict[str, float] = {name: 0.0 for name in self.agents}

    # ---- logging -------------------------------------------------------------------
    def log(self, kind: str, **data: Any) -> None:
        self.events.append(WorldEvent(self.t, kind, data))

    # ---- beacons -------------------------------------------------------------------
    def drop_beacon(self, owner: str) -> str:
        agent = self.agents[owner]
        bid = f"{owner}_{self.next_beacon_id}"
        self.next_beacon_id += 1
        self.beacons[bid] = Beacon(bid, agent.x, agent.y, owner)
        self.log("beacon_drop", owner=owner, id=bid, x=agent.x, y=agent.y)
        return bid

    def spoof(self, victim: str, cloned_id: str) -> float:
        """Scripted sabotage: the rival has cloned one of the victim's own beacons and
        placed the clone just ahead of it. Same id, same owner, wrong place.

        The victim's Belief still records the beacon where it was dropped, so the
        next fix drags its pose estimate back by roughly the distance it has walked
        since. Returns that lie distance, for the truth log only.
        """
        agent = self.agents[victim]
        beacon = self.beacons[cloned_id]
        was_x, was_y = beacon.x, beacon.y
        beacon.move_to(agent.x + math.cos(agent.heading) * T.SPOOF_AHEAD_CELLS,
                       agent.y + math.sin(agent.heading) * T.SPOOF_AHEAD_CELLS)
        beacon.range = T.SPOOF_RANGE
        beacon.reassert_period = T.SPOOF_REASSERT_S
        lie = math.hypot(beacon.x - was_x, beacon.y - was_y)
        self.spoof_done = True
        # was_x/was_y are logged so the spectator can draw the dashed line back to
        # where the victim still records the beacon. Nothing in the sim reads them.
        self.log("spoof", victim=victim, id=cloned_id, x=beacon.x, y=beacon.y,
                 was_x=was_x, was_y=was_y, lie_cells=round(lie, 1))
        return lie

    # ---- deposits ------------------------------------------------------------------
    def step_loading(self, name: str, loading: bool) -> None:
        """Cargo only arrives if the agent is actually standing at a deposit.

        An agent whose drift has put it short of the deposit will sit there for the
        full load time and get nothing. It finds that out through a cargo return,
        not by assumption.
        """
        agent = self.agents[name]
        if not loading:
            self.load_progress[name] = 0.0
            return
        near = any(math.hypot(agent.x - dx, agent.y - dy) < T.DEPOSIT_RADIUS
                   for dx, dy in self.deposits.values())
        if near and agent.cargo < T.CARGO_CAPACITY:
            self.load_progress[name] += T.DT
            if self.load_progress[name] >= T.LOAD_SECONDS - T.DT:
                agent.cargo += 1
                self.load_progress[name] = 0.0
                self.log("loaded", agent=name, cargo=agent.cargo)

    # ---- hazards -------------------------------------------------------------------
    def step_hazards(self) -> None:
        """The Assayer fires, and what a machine takes depends on where it is standing.

        THE-MACHINERY sections 4.4 and 4.7. Three things happen here and they are
        deliberately separate:

          * the zone flag stays a plain nine-cell disc, because the director and the
            truth log read it and the camera must behave exactly as it did before;
          * the KILL test runs on every lethal tick, as it always has, but the shape
            it tests is the lobe rather than a circle -- 9.00 cells on the axis and
            5.32 at the flank;
          * the DOSE lands on the firing tick only. The blow is an instant, so the
            unit of risk is the cycle: loitering for three minutes is three firings,
            countable and legible, and an 80-second interface dwell costs exactly one.

        An agent inside the lethal contour is destroyed and takes no dose -- one
        event, no meter. Everything outside it and above the floor is graded, with no
        threshold and no special case.
        """
        ancient = self.ancient
        for agent in self.agents.values():
            inside = agent.alive and ancient.in_zone(agent.x, agent.y)
            if inside != agent.in_ancient:
                agent.in_ancient = inside
                self.log("ancient_zone", agent=agent.name, inside=inside)
        if not ancient.is_lethal(self.t):
            return
        firing = ancient.is_firing_tick(self.t)
        for agent in self.agents.values():
            if not agent.alive:
                continue
            coupling = ancient.coupling_at(agent.x, agent.y, self.t)
            if coupling >= 1.0:
                self._destroy(agent, "ancient")
            elif firing and coupling >= T.ANCIENT_DOSE_FLOOR:
                dose = T.ANCIENT_DOSE_K * coupling ** T.ANCIENT_DOSE_CURVE
                agent.take_shock(dose)
                # Logged per dosed firing so a machine limping home at 40% can say
                # WHICH firing did it. THE-MACHINERY 10.3 is honest that one pip is
                # the minimum answer to attribution and probably not a sufficient one.
                self.log("shock", agent=agent.name, x=agent.x, y=agent.y,
                         coupling=round(coupling, 3), dose=round(dose, 3),
                         damage=round(agent.damage, 3))
                if not agent.alive:
                    self._destroy(agent, "damage")

    def _destroy(self, agent: AgentTruth, cause: str) -> None:
        agent.alive = False
        self.pending_sounds.append(
            PendingSound(self.t + T.DT, agent.x, agent.y, SoundCharacter.CRASH))
        self.log("death", agent=agent.name, x=agent.x, y=agent.y, cause=cause)

    def expire_sounds(self) -> None:
        self.pending_sounds = [s for s in self.pending_sounds if s.t > self.t - T.DT]
