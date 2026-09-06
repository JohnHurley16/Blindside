"""Dead reckoning: the agent's own motion, as it measured it."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class OdometryReturn:
    """Forward distance and heading change since the last tick.

    Already corrupted by scale bias, heading bias and noise. The agent has no
    other source of motion, so this error is not recoverable -- it is integrated
    straight into the pose estimate and becomes drift.
    """
    forward: float
    turn: float
