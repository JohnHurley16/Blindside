"""What the corridor actually was, once the run cannot be changed by knowing it."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True, frozen=True)
class TruthSnapshot:
    """Plain numbers only: no World, no Corridor, nothing with behaviour on it.

    Positions are in the true frame, which is the same frame the shaft is surveyed
    at, so the believed map and this can be drawn over each other and the gap
    between them is the drift.
    """
    seed: int
    nodes: list[tuple[float, float]]
    passages: list[tuple[float, float, float, float]]
    deposit: tuple[float, float]
    agent: tuple[float, float]
    trail: list[tuple[float, float]] = field(default_factory=list)
    misturns: int = 0
