"""What sort of thing happened, for colouring it on the timeline."""
from __future__ import annotations

from enum import StrEnum


class EventKind(StrEnum):
    FIX = "fix"              # an ordinary position correction
    DISAGREE = "disagree"    # a correction far larger than the estimator allowed
    CONTACT = "contact"      # something heard
    HAZARD = "hazard"        # machinery winding up
    CARGO = "cargo"
    COMMAND = "command"      # the player's one input
    PHASE = "phase"          # extraction opening, the match ending
    TROUBLE = "trouble"      # stuck, lost, nothing where it expected
