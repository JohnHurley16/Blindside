"""Where the agent believed it was when it pinged."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class OwnPing:
    """The wavefront is drawn from the believed position, so a drifted estimate puts
    the agent's own ping in the wrong place too -- and the returns it produces land
    around that wrong place, which is how the ghost corridor is built."""
    t: float
    x: float
    y: float
    heading: float
