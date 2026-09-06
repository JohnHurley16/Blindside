"""A truth-side log entry. Headless tuning only; never rendered during a run."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class WorldEvent:
    t: float
    kind: str
    data: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        return f"{self.kind} {self.data}"
