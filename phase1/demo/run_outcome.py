"""How one run ended, as the trace records it."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class RunOutcome:
    """The contract's three fields plus a reason for the printout.

    CAVE-BLOCKS.md guess 8: `success` is extracted with cargo of at least one;
    `lost` is alive and still in the cave when the match ended; destroyed is
    neither. `reason` is Python-side only and is not written to trace.json.
    """
    success: bool
    ticks: int
    lost: bool
    reason: str = ""
