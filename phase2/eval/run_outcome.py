"""How one run ended."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class RunOutcome:
    """The contract's three fields plus a reason for the table.

    `success`: within the shaft beacon's range carrying cargo before the budget
    ended. `lost`: the agent stood where it believed the shaft was and no fix
    came. `reason` is Python-side only and is not written to trace.json.
    """
    success: bool
    ticks: int
    lost: bool
    reason: str = ""
