"""Where a map point came from.

Note that FALSE is carried through into Belief and rendered exactly like SONAR,
differing only in confidence. A marginal return that announced itself as false
would not be a marginal return.
"""
from __future__ import annotations

from enum import StrEnum


class PointSource(StrEnum):
    SONAR = "sonar"   # an active ping return
    LIDAR = "lidar"   # an active light return: precise, silent, stops at water
    NEAR = "near"     # near-field: the agent's own motion noise off close walls
    FALSE = "false"   # a return from nothing at all
