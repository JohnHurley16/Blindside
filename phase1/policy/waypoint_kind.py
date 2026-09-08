"""What sort of place a waypoint is, which decides how close counts as arrived."""
from __future__ import annotations

from enum import StrEnum


class WaypointKind(StrEnum):
    PLACE = "place"      # a survey chamber: WAYPOINT_REACHED
    BEACON = "beacon"    # one of its own chain, retraced: RECALL_BEACON_REACHED
    SHAFT = "shaft"      # home: HOME_REACHED, or HOME_FINAL once the shaft has answered
