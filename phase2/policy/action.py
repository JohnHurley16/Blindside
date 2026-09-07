"""One action block, as listed in blocks.json."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class Action:
    """Something the agent can be told to do at a stop.

    `stage` is the tutorial run at which this block first exists; see `Predicate`.
    """
    id: str
    label: str
    stage: int = 1
