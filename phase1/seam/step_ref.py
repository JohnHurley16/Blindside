"""One stop, named the way the induction names it."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class StepRef:
    """A trace path and an index into its steps."""
    trace: str
    index: int

    @classmethod
    def parse(cls, data: dict[str, object]) -> StepRef:
        return cls(trace=str(data["trace"]), index=int(data["index"]))   # type: ignore[arg-type]
