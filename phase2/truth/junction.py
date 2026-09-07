"""One node of the corridor: the shaft, a junction, or a dead end."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class Junction:
    """A place the agent stops.

    The shaft has no parent passage and one onward passage; the eight junctions
    proper have two or three onward passages; a leaf has none. The agent stops at
    all of them, so they share a type.
    """
    id: int
    depth: int
    parent: int | None
    onward: list[int] = field(default_factory=list)
    x: float = 0.0
    y: float = 0.0

    @property
    def is_leaf(self) -> bool:
        return self.parent is not None and not self.onward
