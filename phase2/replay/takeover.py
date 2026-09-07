"""A run that has been wound forward to one stop and handed to a chooser.

The window pumps this one stop at a time, because the chooser is a person; a
scripted session pumps it in a loop. Either way the stops it records are the
suffix that `correction.promote` puts in place of the demonstration's.
"""
from __future__ import annotations

from ..demo.run_driver import RunDriver
from ..demo.stop_view import StopView
from ..demo.trace_step import TraceStep
from ..eval.run_outcome import RunOutcome


class Takeover:
    """Positioned at a stop, waiting to be told what to do there."""

    def __init__(self, driver: RunDriver, index: int) -> None:
        self.driver: RunDriver = driver
        self.index: int = index                     # the stop the takeover began at
        self.steps: list[TraceStep] = []
        self.stop: StopView | None = driver.advance_to_stop()

    @property
    def done(self) -> bool:
        return self.stop is None

    @property
    def outcome(self) -> RunOutcome | None:
        return self.driver.outcome

    def choose(self, action: str) -> None:
        """Record the choice at the stop we are at, and walk on to the next."""
        if self.stop is None:
            raise RuntimeError("the takeover is over")
        view = self.stop
        step = TraceStep(tick=view.tick, junction=view.junction,
                         predicates=dict(view.predicates), raw=dict(view.raw),
                         action=action)
        # Recorded only when it happened, exactly as a demonstration records it.
        if self.driver.choose(action):
            self.steps.append(step)
        self.stop = self.driver.advance_to_stop()
