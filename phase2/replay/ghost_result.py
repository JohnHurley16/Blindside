"""What the ghost found."""
from __future__ import annotations

from dataclasses import dataclass, field

from ..demo.trace_step import TraceStep
from ..eval.run_outcome import RunOutcome
from ..seam.choice_diff import ChoiceDiff


@dataclass(slots=True, frozen=True)
class GhostResult:
    """The induced tree's run beside the demonstration's, and where they parted.

    `diff` is `induct diff`'s answer over the two choice lists; `first_difference`
    is the stop the window flags. `steps` are the ghost's own stops, so a panel can
    light the tree's path at each of them.
    """
    seed: int
    demonstrated: list[str]
    ghosted: list[str]
    diff: ChoiceDiff
    outcome: RunOutcome | None
    steps: list[TraceStep] = field(default_factory=list)

    @property
    def first_difference(self) -> int | None:
        return self.diff.index

    def summary(self) -> str:
        if self.diff.index is None:
            return f"the tree chose exactly what you did, all {len(self.demonstrated)} stops"
        return (f"first difference at stop {self.diff.index}: "
                f"you {self.diff.a or '(ran out)'}, the tree {self.diff.b or '(ran out)'}")
