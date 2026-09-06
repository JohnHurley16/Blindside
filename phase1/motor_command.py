"""What a policy asks the machine to do this tick.

Top-level vocabulary so the sensor layer can read a command without importing the
policy package.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class MotorCommand:
    """The whole of a policy's output. Note what is absent: there is no way to ask
    for a position, only for a heading and a speed."""
    heading: float
    speed: float = 0.0
    ping: bool = False
    drop: bool = False
    load: bool = False
