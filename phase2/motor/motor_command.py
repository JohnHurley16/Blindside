"""What an action asks the body to do at a stop."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class MotorCommand:
    """A turn relative to the heading the agent believes it has, then go.

    Note what is absent: there is no way to ask for a passage, a node or a
    position. The body turns and walks into whatever is in front of it.
    """
    turn: float
    go: bool

    @classmethod
    def hold(cls) -> MotorCommand:
        return cls(0.0, False)
