"""What a chooser -- a player at the window, or a tree -- is shown at a decision point."""
from __future__ import annotations

from dataclasses import dataclass, field

from ..belief.belief import Belief


@dataclass(slots=True, frozen=True)
class StopView:
    """The belief-only view of one stop; the corridor's `StopView` with the cave's
    two extra facts.

    `predicates` holds the booleans of every predicate enabled in this run and
    `raw` the number behind each parametric one -- exactly what the trace records.
    `reason` is why the bot stopped (`start`, `ended:<action id>`, `rose:<predicate
    id>`, `waited`), the optional trace field CAVE-BLOCKS.md 5 adds. `available`
    says, per enabled action, whether choosing it here would do anything: a no-op
    (fetch with no deposit left, freeze in silence) is not a demonstration and the
    block panel greys it out. `belief` is the same object the predicates were read
    from, for a window to draw.
    """
    t: float
    tick: int
    reason: str
    junction: int
    predicates: dict[str, bool]
    raw: dict[str, float]
    belief: Belief
    available: dict[str, bool] = field(default_factory=dict)
