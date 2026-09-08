"""Fetch from a deposit: route to the nearest untried one, drive, load, retry, mark tried."""
from __future__ import annotations

import math

from ... import tuning as T
from ...motor_command import MotorCommand
from ..decision_node import DecisionNode
from .body import Body
from ..waypoint import Waypoint
from .driver import Driver
from .program import Program
from .route_planner import RoutePlanner


class GoToDeposit(Program):
    """The corridor's `take_branch` with a destination instead of a mouth.

    Ends when the load ended: cargo arrived, the deposit was given up on after the
    retries, or it was unreachable (skipped after four escapes at its own waypoint).
    Whichever way, the deposit is marked tried, so `a deposit left to try` moves on.
    The load itself is folded in: nobody has ever arrived at a deposit and chosen not
    to load (CAVE-BLOCKS.md 2.2).
    """

    def __init__(self, body: Body, t: float) -> None:
        super().__init__(body, t)
        belief = body.belief
        self.driver: Driver = Driver(body)
        self.deposit: str | None = None
        self.loading: bool = False
        self.load_until: float = 0.0
        self.cargo_at_load: int = 0
        self.load_attempts: int = 0
        planner = RoutePlanner(belief.survey)
        best: tuple[str, float] | None = None
        for place in belief.survey.deposits:
            if place in belief.tried_deposits:
                continue
            cost = planner.cost(belief.x, belief.y, place)
            if cost is not None and (best is None or cost < best[1]):
                best = (place, cost)
        if best is None:
            self.noop = True
            return
        self.deposit = best[0]
        route = planner.route(belief.x, belief.y, self.deposit)
        assert route is not None
        self.driver.set_route(route, t)

    def resume(self, t: float) -> None:
        self.driver.resume(t)
        if self.loading:
            # World's loading progress reset the tick this stopped asking to load, so
            # the dwell starts over; tuning.py says why that is the honest cost.
            self.load_until = t + T.LOAD_SECONDS

    def ending(self, t: float) -> str | None:
        # The deposit's own waypoint was skipped: it cannot be reached from here.
        return "unreachable" if (not self.loading and self.driver.finished) else None

    def step(self, t: float) -> MotorCommand | None:
        b, d = self.b, self.driver
        if self.loading:
            cmd = self.idle()
            cmd.load = True
            d.still_on_purpose(t)
            if t >= self.load_until:
                self._after_load(t)
            return cmd
        why = self.ending(t)
        if why is not None:
            assert self.deposit is not None
            b.note_deposit_tried(self.deposit, t, why)
            self._end(t, why)
            return None
        if d.arrived():
            wp = d.target()
            assert wp is not None
            if wp.label == self.deposit:
                b.log.append((t, f"at {wp.label}, loading"))
                self.cargo_at_load = b.cargo
                self.loading = True
                self.load_until = t + T.LOAD_SECONDS
            else:
                d.advance(t)
            return self.idle()
        return d.drive(t, drop=True)

    def _after_load(self, t: float) -> None:
        """Discover through the cargo return whether the load actually happened."""
        b = self.b
        wp = self.driver.target()
        assert wp is not None and self.deposit is not None
        if b.cargo > self.cargo_at_load:
            self.load_attempts = 0
            b.note_deposit_tried(self.deposit, t, "loaded")
            self._end(t, "loaded")
            return
        self.load_attempts += 1
        if self.load_attempts <= T.LOAD_RETRIES:
            b.log.append((t, f"nothing loaded at {wp.label}; it is not where I think it is"))
            angle = float(b.rng.uniform(0.0, 2.0 * math.pi))
            wp.nudge(math.cos(angle) * T.LOAD_SEARCH_STEP, math.sin(angle) * T.LOAD_SEARCH_STEP)
            self.loading = False
            self.driver.reset_progress(t)
            return
        b.log.append((t, f"giving up on {wp.label}"))
        self.load_attempts = 0
        b.note_deposit_tried(self.deposit, t, "given up")
        self._end(t, "given up")

    def nodes(self, t: float) -> list[DecisionNode]:
        if self.loading:
            left = max(0.0, self.load_until - t)
            return [DecisionNode("act.load", "LOAD CARGO", "action", active=True, fired=True),
                    DecisionNode("act.load.wait", "filling up", "sub",
                                 detail=f"{left:.0f}s left",
                                 fill=1.0 - left / max(T.LOAD_SECONDS, 1e-6), active=True)]
        return self.driver.nodes(t, drop=True)

    def target(self) -> Waypoint | None:
        return self.driver.target()
