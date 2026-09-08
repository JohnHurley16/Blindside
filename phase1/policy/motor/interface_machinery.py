"""Go to the machinery and download."""
from __future__ import annotations

from ... import tuning as T
from ...motor_command import MotorCommand
from ..decision_node import DecisionNode
from .body import Body
from ..waypoint import Waypoint
from .driver import Driver
from .program import Program
from .route_planner import RoutePlanner


class InterfaceMachinery(Program):
    """Head for the machinery by the survey map's position for it; while the
    signature is heard, steer along its bearing instead (the old policy's
    *investigate*, kept for INVESTIGATE_HOLD_S after the last hearing); at
    INTERFACE_QUALITY stop walking, creep at INTERFACE_SPEED along the bearing and
    dwell INTERFACE_S. Arriving at the survey's position for it dwells the same
    length standing still. Ends when the dwell ended, or the machinery was
    unreachable.

    Designer's reasoning, carried over: the machinery is where an agent can download
    new behaviours, so investigating is rational, not reckless. It stays longer than
    one cycle, so the next cycle finds it there -- which is how the cautious one,
    holding still a chamber away, comes to hear something break. The investigate /
    interface split is one action on purpose (CAVE-BLOCKS.md 2.2): the motor decides
    when the sound is loud enough to stop walking and start downloading.
    """

    def __init__(self, body: Body, t: float) -> None:
        super().__init__(body, t)
        belief = body.belief
        self.driver: Driver = Driver(body)
        self.investigate_bearing: float | None = None
        self.investigate_until: float = -1.0
        self.interfacing_until: float = -1.0
        self.dwell_until: float | None = None
        route = RoutePlanner(belief.survey).route(belief.x, belief.y, belief.survey.machinery)
        if route is None:
            self.noop = True
            return
        self.driver.set_route(route, t)

    def resume(self, t: float) -> None:
        self.driver.resume(t)

    def ending(self, t: float) -> str | None:
        if self.dwell_until is not None:
            return None                       # the dwell ends on a tick it still acts in
        if self.interfacing_until > 0.0 and t >= self.interfacing_until:
            return "downloaded"
        if self.driver.finished:
            return "unreachable"
        return None

    def step(self, t: float) -> MotorCommand | None:
        b, d = self.b, self.driver
        if self.dwell_until is not None:
            d.still_on_purpose(t)
            if t >= self.dwell_until:
                b.log.append((t, "done at the machinery; moving on"))
                self._end(t, "downloaded")
            return self.idle()
        why = self.ending(t)
        if why is not None:
            if why == "downloaded":
                b.log.append((t, "done at the machinery; moving on"))
            self._end(t, why)
            return None

        sig = b.signature
        if (sig is not None and t - sig.t < T.SIGNATURE_STALE_S
                and sig.quality >= T.INVESTIGATE_QUALITY):
            if self.investigate_bearing is None or t >= self.investigate_until:
                b.log.append((t, "heard machinery; going to look"))
            self.investigate_bearing = sig.bearing
            self.investigate_until = t + T.INVESTIGATE_HOLD_S
            # Close enough that it is loud: stop travelling and interface with it. It
            # creeps the last few cells along the bearing and stays through the next
            # cycle -- that is what "downloading" costs.
            if sig.quality >= T.INTERFACE_QUALITY and self.interfacing_until < 0.0:
                b.log.append((t, "interfacing with the machinery"))
                self.interfacing_until = t + T.INTERFACE_S
        interfacing = self.interfacing_until > 0.0 and t < self.interfacing_until
        investigating = self.investigate_bearing is not None and (
            t < self.investigate_until or interfacing)

        if d.arrived():
            wp = d.target()
            assert wp is not None
            if wp.label == b.survey.machinery:
                b.log.append((t, "at the machinery; interfacing"))
                self.dwell_until = t + T.INTERFACE_S
            else:
                d.advance(t)
            return self.idle()
        return d.drive(t,
                       goal_override=self.investigate_bearing if investigating else None,
                       break_jams=not investigating,
                       speed=T.INTERFACE_SPEED if interfacing else None,
                       drop=True)

    def nodes(self, t: float) -> list[DecisionNode]:
        until = self.dwell_until if self.dwell_until is not None else (
            self.interfacing_until if self.interfacing_until > 0.0 else None)
        if until is not None:
            left = max(0.0, until - t)
            return [DecisionNode("act.interface", "INTERFACING", "action", active=True, fired=True),
                    DecisionNode("act.interface.wait", "downloading", "sub",
                                 detail=f"{left:.0f}s left",
                                 fill=1.0 - left / max(T.INTERFACE_S, 1e-6), active=True)]
        target = None
        if self.investigate_bearing is not None and t < self.investigate_until:
            target = "the sound"
        return self.driver.nodes(t, drop=True, target=target)

    def target(self) -> Waypoint | None:
        return self.driver.target()
