"""A beacon as the agent recorded it. Including the ones that lie."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class KnownBeacon:
    """Where the agent *thinks* a transponder is.

    An own beacon can only be recorded at the estimated position at the moment it was
    dropped, which is already wrong by whatever drift had accumulated. So a beacon
    chain anchors an agent to its own past belief, not to the world -- re-acquiring
    one collapses only the drift since the drop. The shaft is the single exception:
    it was survey-placed, so its recorded position is its true one, and it is the only
    thing in the match that can pull an agent back to reality.
    """
    beacon_id: str
    x: float
    y: float
    t_placed: float
    truth_anchor: bool = False
