"""What a chooser -- a player or a tree -- is shown at a stop."""
from __future__ import annotations

from dataclasses import dataclass

from ..belief.belief import Belief


@dataclass(slots=True, frozen=True)
class StopView:
    """The belief-only view of one stop.

    `predicates` holds the booleans of every predicate that exists in this run;
    `raw` the number behind each parametric one. `belief` is there for a window
    to draw; it is the same object the predicates were evaluated on.
    """
    tick: int
    junction: int
    predicates: dict[str, bool]
    raw: dict[str, float]
    belief: Belief
