"""A beacon was heard. It may be lying."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class BeaconFixReturn:
    """Range and bearing to a transponder that answered to `beacon_id`.

    Belief turns this into a position by combining it with the position it
    recorded for that id. Nothing in this type distinguishes a beacon that has
    been moved from one that has not, and nothing downstream can. That is the
    whole mechanism of spoofing.
    """
    beacon_id: str
    range: float
    bearing_body: float
