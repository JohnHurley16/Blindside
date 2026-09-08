"""Freeze until it passes."""
from __future__ import annotations

from ... import tuning as T
from ...motor_command import MotorCommand
from ..decision_node import DecisionNode
from .body import Body
from .driver import Driver
from .program import Program


class Hold(Program):
    """Stop, and go silent, until the signature has not been heard for
    SIGNATURE_STALE_S. A lidar still sweeps: it is light, and nothing hears it.

    Ends with the silence, by returning `None` on the tick it lifts, so that tick
    belongs to the drive it interrupted -- exactly when the old policy started
    walking again. In silence from the start it is a no-op.
    """

    def __init__(self, body: Body, t: float) -> None:
        super().__init__(body, t)
        belief = body.belief
        self.driver: Driver = Driver(body)
        if not self._audible(t):
            self.noop = True

    def _audible(self, t: float) -> bool:
        sig = self.b.signature
        return sig is not None and t - sig.t < T.SIGNATURE_STALE_S

    def ending(self, t: float) -> str | None:
        return None if self._audible(t) else "silence"

    def step(self, t: float) -> MotorCommand | None:
        why = self.ending(t)
        if why is not None:
            self._end(t, why)
            return None
        cmd = self.idle()
        cmd.ping = self.driver.wants_ping(silent=True)
        return cmd

    def nodes(self, t: float) -> list[DecisionNode]:
        return [DecisionNode("act.hold", "FREEZE UNTIL IT PASSES", "action",
                             active=True, fired=True)]
