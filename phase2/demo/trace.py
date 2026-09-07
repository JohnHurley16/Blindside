"""One demonstration: the contract's trace.json, in memory."""
from __future__ import annotations

from dataclasses import dataclass, field

from ..eval.run_outcome import RunOutcome
from .trace_step import TraceStep


@dataclass(slots=True)
class Trace:
    """Everything the induction consumes about one run."""
    seed: int
    enabled_predicates: list[str]
    enabled_actions: list[str]
    params: dict[str, dict[str, float]]
    steps: list[TraceStep] = field(default_factory=list)
    outcome: RunOutcome | None = None
