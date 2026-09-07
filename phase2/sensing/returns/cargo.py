"""Self report: how much cargo is aboard."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class CargoReturn:
    """The load count, reported at every stop."""
    count: int
