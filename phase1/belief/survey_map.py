"""Prior intel: the previous industry's own map, handed to belief at launch.

Not sensed and not truth. The survey is what the agent was given before it went down:
the chambers by name, the dry passages between them with their straight-line lengths,
which chambers hold a deposit, which one holds the machinery, and which is its own
shaft. It is complete and honest for the hand-authored cave -- CAVE-BLOCKS.md guess 7 --
and it marks the machinery's chamber as ground the route planner keeps out of unless it
is the destination.

The planner, `deposit_remaining` and `interface_machinery` read this and nothing else
about the cave's layout. In Phase 3 a generated cave hands out no survey, and the
block that reads deposits off it becomes the corridor's exploration block again.
"""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class SurveyMap:
    """The list of places is in the survey's own order; a place's index in it is the
    `junction` a trace records, because the cave has no junctions of its own."""
    places: tuple[str, ...]
    positions: dict[str, tuple[float, float]]
    passages: tuple[tuple[str, str, float], ...]
    deposits: tuple[str, ...]
    machinery: str
    shaft: str
    avoided: frozenset[str]

    def neighbours(self, place: str) -> list[tuple[str, float]]:
        out: list[tuple[str, float]] = []
        for a, b, length in self.passages:
            if a == place:
                out.append((b, length))
            elif b == place:
                out.append((a, length))
        return out

    def nearest(self, x: float, y: float) -> str:
        return min(self.places, key=lambda n: math.hypot(self.positions[n][0] - x,
                                                          self.positions[n][1] - y))

    def nearest_index(self, x: float, y: float) -> int:
        return self.places.index(self.nearest(x, y))
