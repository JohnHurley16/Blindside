"""What the body is, as far as the motor layer needs to know."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class Loadout:
    """The chassis numbers that used to be the temperament's.

    CAVE-BLOCKS.md guess 6: the ping cadence and the walking speed move to the
    loadout with the sensor, because the design already justifies `RIVAL_SPEED` as
    a lighter chassis and the day-one block list cannot teach *do I ping?*. Both
    trees run with their temperament's Phase 1 numbers here.
    """
    speed: float                        # cells/s
    ping_cooldown_s: float
    ping_only_if_unmapped_ahead: bool   # the cautious discipline: ping into unmapped ground only
