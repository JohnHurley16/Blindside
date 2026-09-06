"""The ancient system: a fixed cycle that is legible before it is lethal."""
from __future__ import annotations

from .. import tuning as T
from . import cave


class Ancient:
    """Deterministic hazard on a fixed period.

    The signature ramps up over ANCIENT_WARNING_S and then the hazard is lethal for
    ANCIENT_LETHAL_S. An agent that listens has time to leave; an agent that does not
    is killed. It is not a random hazard, and it is not a trap -- the warning is
    always there to be heard.
    """

    def __init__(self) -> None:
        self.x: float
        self.y: float
        self.x, self.y = cave.ANCIENT_POS

    def phase(self, t: float) -> float:
        return (t + T.ANCIENT_PHASE_S) % T.ANCIENT_PERIOD_S

    def signature_strength(self, t: float) -> float:
        """0 while quiet, ramping 0.3 -> 1.0 across the warning, 1.0 while lethal."""
        p = self.phase(t)
        start = T.ANCIENT_PERIOD_S - T.ANCIENT_WARNING_S - T.ANCIENT_LETHAL_S
        if p < start:
            return 0.0
        if p < start + T.ANCIENT_WARNING_S:
            return 0.3 + 0.7 * (p - start) / T.ANCIENT_WARNING_S
        return 1.0

    def is_lethal(self, t: float) -> bool:
        return self.phase(t) >= T.ANCIENT_PERIOD_S - T.ANCIENT_LETHAL_S

    def seconds_until_lethal(self, t: float) -> float:
        """Only ever used by truth-side logging, never by a policy."""
        p = self.phase(t)
        lethal_at = T.ANCIENT_PERIOD_S - T.ANCIENT_LETHAL_S
        return (lethal_at - p) if p <= lethal_at else (T.ANCIENT_PERIOD_S - p + lethal_at)

    def covers(self, x: float, y: float) -> bool:
        return (x - self.x) ** 2 + (y - self.y) ** 2 < T.ANCIENT_RADIUS ** 2
