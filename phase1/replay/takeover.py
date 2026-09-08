"""A match that has been wound forward to one stop and handed to a chooser.

The window pumps this one stop at a time, because the chooser is a person; a
scripted correction pumps it in a loop. Either way the stops it records are the
suffix that `correction.promote` puts in place of the demonstration's.
"""
from __future__ import annotations

from ..demo.trace_writer import TraceWriter
from ..match.match_view import MatchView
from ..policy.stop_view import StopView


class Takeover:
    """Positioned at a stop, waiting to be told what to do there."""

    def __init__(self, match: MatchView, index: int, before: int) -> None:
        self.match: MatchView = match
        self.index: int = index                     # the stop the takeover began at
        self.before: int = before                   # recorded decisions replayed to get here
        self.stop: StopView | None = match.stop

    @property
    def done(self) -> bool:
        return self.match.over

    def choose(self, action: str) -> None:
        """Answer the stop we are at, and walk on to the next."""
        if self.stop is None or self.match.over:
            raise RuntimeError("the takeover is over")
        self.match.answer(action)
        self.stop = self.match.advance_to_stop()

    def suffix(self) -> list:
        """The steps recorded since the takeover began: what replaces the old ones."""
        return TraceWriter.from_match(self.match).steps[self.index:]
