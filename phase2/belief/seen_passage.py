"""A passage mouth the agent has seen at a believed junction."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class SeenPassage:
    """One onward passage at a believed junction.

    `bearing` is the believed world bearing recorded when the junction was first
    seen; it is never refreshed, so the drift accrued since then is carried into
    every later use of it. `far` is the believed node at the other end once the
    passage has been walked.
    """
    index: int
    bearing: float
    walked: bool = False
    far: int | None = None
