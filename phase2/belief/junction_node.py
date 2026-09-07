"""A node of the believed junction graph."""
from __future__ import annotations

from dataclasses import dataclass, field

from .seen_passage import SeenPassage


@dataclass(slots=True)
class JunctionNode:
    """A place the agent believes it has stood.

    `passages` are the onward mouths in left-most-first order as seen on the
    first arrival. `back_bearing` is the believed world bearing of the way it
    came in, reversed -- the next step of the route back. The shaft has none.
    """
    id: int
    parent: int | None
    depth: int
    back_bearing: float | None
    x: float
    y: float
    passages: list[SeenPassage] = field(default_factory=list)
