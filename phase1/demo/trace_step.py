"""One stop of a demonstration, as the contract's trace.json records it."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True, frozen=True)
class TraceStep:
    """(predicate values, raw numbers, choice) at one decision point.

    `junction` is the index of the believed nearest survey place -- the cave has no
    junctions, and this is the *where* the induction's query prints. `reason` is the
    optional field CAVE-BLOCKS.md 5 adds: why the bot stopped. The induction ignores
    it; a replay uses it to say *it stopped because...*.
    """
    tick: int
    junction: int
    predicates: dict[str, bool]
    raw: dict[str, float] = field(default_factory=dict)
    action: str = ""
    reason: str = ""
