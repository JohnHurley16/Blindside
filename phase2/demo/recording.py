"""One finished demonstration: the stage it came from, the trace, the file."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .stage import Stage
from .trace import Trace


@dataclass(slots=True, frozen=True)
class Recording:
    """The trace is what the induction reads; the stage is what a replay needs to
    reopen the same run (its seed, its blocks, whether drift was on)."""
    stage: Stage
    trace: Trace
    path: Path

    def choices(self) -> list[str]:
        return [step.action for step in self.trace.steps]
