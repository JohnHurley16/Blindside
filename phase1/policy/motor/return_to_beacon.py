"""Go back: retrace the believed beacon chain, then the shaft; search if it is silent."""
from __future__ import annotations

from ... import geometry as G
from ...motor_command import MotorCommand
from ..decision_node import DecisionNode
from .body import Body
from ..waypoint import Waypoint
from ..waypoint_kind import WaypointKind
from .driver import Driver
from .program import Program
from .search_spiral import SearchSpiral


class ReturnToBeacon(Program):
    """The corridor's action, with the cave's route being the beacon chain and the
    cave's ending being the search.

    Ends on arrival at the shaft with the shaft answering -- once. Chosen again while
    standing there, it is the wait to be collected, which runs to the end of the
    match unless a rising edge interrupts it. At a believed shaft that does not
    answer, or when the shaft's own waypoint had to be given up on, it searches: the
    spiral is the only thing in the match that can undo a lie, and there is nothing
    else sane to do there.
    """

    def __init__(self, body: Body, t: float) -> None:
        super().__init__(body, t)
        belief = body.belief
        self.driver: Driver = Driver(body)
        self.search: SearchSpiral | None = None
        self.waiting: bool = False
        home = self._home()
        if (self.driver.heard_shaft()
                and G.dist(belief.x, belief.y, home.x, home.y) < self.driver.reach_radius(home)):
            self.waiting = True
            return
        self.driver.set_route(self._route(), t)

    def _home(self) -> Waypoint:
        sx, sy = self.b.known_places["HOME"]
        return Waypoint(sx, sy, "HOME", WaypointKind.SHAFT)

    def _route(self) -> list[Waypoint]:
        """The believed beacon chain in reverse, then the believed shaft."""
        b = self.b
        route = [Waypoint(b.beacons[bid].x, b.beacons[bid].y, bid, WaypointKind.BEACON)
                 for bid in reversed(b.beacon_order)]
        route.append(self._home())
        return route

    def resume(self, t: float) -> None:
        self.driver.resume(t)

    def step(self, t: float) -> MotorCommand | None:
        b, d = self.b, self.driver
        if self.waiting:
            d.still_on_purpose(t)
            return self.idle()
        if self.search is not None:
            if d.heard_shaft():
                b.log.append((t, "shaft acquired"))
                d.set_route([self._home()], t)
                d.escapes = 0
                self.search = None
                return self.idle()
            return self.search.step(t)
        if d.finished:
            self.search = SearchSpiral(b, d, t)
            return self.idle()
        if d.arrived():
            wp = d.target()
            assert wp is not None
            if wp.kind is WaypointKind.SHAFT:
                if d.heard_shaft():
                    b.log.append((t, "at the shaft"))
                    self.waiting = True
                    self._end(t, "arrived")
                else:
                    self.search = SearchSpiral(b, d, t)
            else:
                d.advance(t)
            return self.idle()
        return d.drive(t, drop=False)

    def nodes(self, t: float) -> list[DecisionNode]:
        if self.waiting:
            return [DecisionNode("act.done", "WAIT TO BE COLLECTED", "action",
                                 active=True, fired=True)]
        if self.search is not None:
            return self.search.nodes()
        return self.driver.nodes(t, drop=False)

    def target(self) -> Waypoint | None:
        return None if self.waiting else self.driver.target()
