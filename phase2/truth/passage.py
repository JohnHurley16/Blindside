"""One passage of the corridor, as it actually is."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class Passage:
    """A straight run of cave between two nodes.

    `near` is the shaft-ward node and `far` the deeper one. `bearing` is the
    direction of travel from near to far, in world radians; the bearing of the
    way back is the same plus pi.
    """
    id: int
    near: int
    far: int
    bearing: float
    length: int
