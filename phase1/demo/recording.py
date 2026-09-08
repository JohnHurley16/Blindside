"""One finished demonstration: the trace and the file it was written to."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .trace import Trace


@dataclass(slots=True, frozen=True)
class Recording:
    """The trace is what the induction reads; its `enabled_*` and `params` are what a
    replay needs to reopen the same run, so nothing else is kept."""
    trace: Trace
    path: Path

    def choices(self) -> list[str]:
        return self.trace.choices()
