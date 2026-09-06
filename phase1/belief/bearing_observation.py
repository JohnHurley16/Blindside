"""One bearing, remembered along with where the agent thought it was standing."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class BearingObservation:
    """A direction to something, taken from a believed position.

    Both the position and the bearing are in the belief frame, so a fix drags them
    along with the rest of the map. That matters: an agent whose pose estimate is
    wrong will place the thing it heard in the wrong place too, confidently.
    """
    x: float
    y: float
    bearing: float
    quality: float
    t: float
