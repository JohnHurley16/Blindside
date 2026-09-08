"""One delayed arrival of a sound that came by a second passage.

Not a reverb: the cave is passages, and a passage delivers a discrete copy at a discrete
delay from a discrete direction. Three of these cost three voices and no filter, which is
the whole reason this is affordable in Phase 1.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Reflection:
    delay: float        # seconds after the direct arrival
    gain: float         # fraction of the direct level
    pan: float
    brightness: float   # always below the direct: another wall's worth of rock
