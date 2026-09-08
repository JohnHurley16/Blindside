"""One decision point: what the tree saw, the path it walked, what it chose."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class Decision:
    """A stop, as a trace step records one (crates/blindside-induct/FORMAT.md) plus the
    two things this side keeps for itself: `path`, for the decision graph, and `ran`,
    which says whether the chosen action actually did anything -- a no-op is not a
    demonstration (CAVE-BLOCKS.md 2.2, rule 2) and a trace writer leaves it out.

    `reason` is the optional trace field CAVE-BLOCKS.md 5 adds: `start`,
    `ended:<action id>`, `rose:<predicate id>`, or `waited` after a no-op.
    """
    t: float
    tick: int
    reason: str
    junction: int
    predicates: dict[str, bool]
    raw: dict[str, float]
    path: tuple[tuple[str, bool], ...]
    action: str
    ran: bool
