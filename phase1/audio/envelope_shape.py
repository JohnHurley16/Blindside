"""How a voice's amplitude leaves.

Two shapes, because the old mixer had one and that was the problem: every sound in the
game -- a ping ninety cells away, a machine dying -- rose in 6 ms and faded linearly, so
nothing sounded *struck* and nothing sounded *distant*. A linear fade is a signal being
turned off. An exponential one is energy leaving an object.
"""
from __future__ import annotations

from enum import StrEnum


class EnvelopeShape(StrEnum):
    LINEAR = "linear"            # a transmission: it stops when it stops
    EXPONENTIAL = "exponential"  # a struck thing: hammer, hull, pawl, rock
