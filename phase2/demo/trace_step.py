"""One stop of a demonstration, as the contract's trace.json records it."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True, frozen=True)
class TraceStep:
    """(predicate values, raw numbers, choice) at one believed junction."""
    tick: int
    junction: int
    predicates: dict[str, bool]
    raw: dict[str, float] = field(default_factory=dict)
    action: str = ""
