"""The shaft beacon answered."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class ShaftFixReturn:
    """Range and body bearing to the shaft, plus the agent's heading read against
    the shaft's survey marks.

    The shaft is the only truth anchor in Phase 2, and it is survey-placed, so it
    can answer heading as well as position. Phase 1's beacon could not; see
    tuning.SHAFT_HEADING_REF_NOISE_DEG for why this one does.
    """
    range: float
    bearing_body: float
    heading_ref: float
