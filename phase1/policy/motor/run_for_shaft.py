"""Recall: abort straight to the believed shaft. The one live command, not a block."""
from __future__ import annotations

from ..waypoint import Waypoint
from .return_to_beacon import ReturnToBeacon


class RunForShaft(ReturnToBeacon):
    """Blunt on purpose.

    Not the beacon chain: the agent's own uncertainty return retraces the chain,
    which is the careful thing to do and which, once the pose estimate is corrupted,
    walks it into wall after wall without ever arriving. Recall drives straight at
    the shaft it believes in, and when the shaft is not there it starts searching --
    and the search is the only thing in the match that can undo a lie. That
    difference is what the player is actually buying.

    It is `return_to_beacon` with a one-waypoint route, and it is the deferred block
    CAVE-BLOCKS.md 6 calls `run_for_shaft`. Recall takes the tree out of the loop for
    the rest of the match (guess 5), so nothing here is the player's to teach yet.
    """

    def _route(self) -> list[Waypoint]:
        return [self._home()]
