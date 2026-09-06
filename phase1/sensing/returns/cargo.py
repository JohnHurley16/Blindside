"""Self report: how much cargo is actually aboard."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class CargoReturn:
    """The load count after a load attempt.

    This is how an agent discovers that it spent thirty seconds loading at a place
    where there was no deposit: the number did not change.
    """
    count: int
