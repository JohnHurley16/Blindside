"""A demonstration: something chooses at every stop, and it is all written down."""
from __future__ import annotations

from typing import Callable

from .run_driver import RunDriver, assert_narrow
from .stop_view import StopView
from .trace import Trace
from .trace_step import TraceStep

Chooser = Callable[[StopView], str]


class Demonstration:
    """Runs a session with a chooser and records a Trace.

    The chooser may be a player at a window or a tree; either way it is handed a
    belief-only StopView and answers with an action id. Only the blocks the
    driver has enabled are evaluated and offered.

    A stop is written down only when the action actually moved the agent. A stop
    where the motor held is not a demonstration of anything: nothing happened, and
    recording it teaches the induction a rule the player never meant. The case that
    forces this is a run with one action -- the tutorial's first -- which ends
    standing somewhere that action cannot be used. See `match/session.py:choose`.
    """

    def __init__(self, driver: RunDriver, chooser: Chooser) -> None:
        assert_narrow(driver)
        self.driver: RunDriver = driver
        self.chooser: Chooser = chooser
        self.trace: Trace = Trace(seed=driver.seed,
                                  enabled_predicates=list(driver.enabled_predicates),
                                  enabled_actions=list(driver.enabled_actions),
                                  params={pid: dict(v) for pid, v in driver.params.items()
                                          if pid in driver.enabled_predicates})

    def run(self) -> Trace:
        while (view := self.driver.advance_to_stop()) is not None:
            action = self.chooser(view)
            if action not in self.driver.enabled_actions:
                raise ValueError(f"chooser picked an action that does not exist in this run: {action}")
            step = TraceStep(tick=view.tick, junction=view.junction,
                             predicates=dict(view.predicates),
                             raw=dict(view.raw), action=action)
            if self.driver.choose(action):
                self.trace.steps.append(step)
        self.trace.outcome = self.driver.outcome
        return self.trace
