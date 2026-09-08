"""One action block, as listed in blocks.json."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class Action:
    """Something the agent can be told to do at a decision point. It hands off to a
    motor program that runs until the next one; see `motor/program.py`."""
    id: str
    label: str
    stage: int = 1
