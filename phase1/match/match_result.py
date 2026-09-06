"""How a match ended."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class MatchResult:
    why: str
    player_outcome: str        # extracted | destroyed | lost in the cave
    cargo: int
    recall_used: bool
    ended_at: float

    def __str__(self) -> str:
        return (f"{self.player_outcome} (cargo {self.cargo}, "
                f"recall {'used' if self.recall_used else 'unused'}) "
                f"after {int(self.ended_at) // 60}:{self.ended_at % 60:04.1f} -- {self.why}")
