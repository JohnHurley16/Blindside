"""A demonstration: something chooses at every decision point, and it is all written down."""
from __future__ import annotations

from ..match.match_view import MatchView
from .chooser import Chooser
from .trace import Trace
from .trace_writer import TraceWriter


class Demonstration:
    """Runs a match with a chooser and reads the Trace off it.

    The chooser may be a person at a window or a tree; either way it is handed a
    belief-only StopView and answers with an action id. Only the blocks the run's
    spec enables are evaluated and offered. The match is paused for the whole of
    the asking -- the sim does not tick with a question open -- so a demonstration
    is not timed.

    What is written down is the policy's own record of its decisions, filtered to
    the ones that ran (`TraceWriter.from_match`): a no-op is not a demonstration.
    """

    def __init__(self, match: MatchView, chooser: Chooser) -> None:
        self.match: MatchView = match
        self.chooser: Chooser = chooser

    def run(self) -> Trace:
        match = self.match
        while (stop := match.advance_to_stop()) is not None:
            action = self.chooser(stop)
            if action not in match.spec.enabled_actions:
                raise ValueError(f"chooser picked an action that does not exist in this run: {action}")
            match.answer(action)
        return TraceWriter.from_match(match)
