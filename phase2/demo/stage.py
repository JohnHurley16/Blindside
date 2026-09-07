"""One run of the staged tutorial."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True, frozen=True)
class Stage:
    """A run and the conditions it happens under.

    `block_stage` selects the blocks that exist: every block whose own stage is at
    most this one. Which blocks those are is read from blocks.json, so this object
    names none of them. `drift` off is the tutorial's first run, where dead
    reckoning is exact and nothing can get lost. `demonstration` marks the runs the
    success rate is measured from -- the three full ones after the staging.
    """
    number: int
    title: str
    note: str
    seed: int
    drift: bool
    block_stage: int
    demonstration: bool
    params: dict[str, dict[str, float]] = field(default_factory=dict)
