"""Angle helpers, copied from Phase 1. No state, no classes."""
from __future__ import annotations

import math

TAU: float = 2.0 * math.pi


def wrap(a: float) -> float:
    """Fold an angle into (-pi, pi]."""
    return (a + math.pi) % TAU - math.pi


def clamp(v: float, lo: float, hi: float) -> float:
    return lo if v < lo else (hi if v > hi else v)


def angle_between(a: float, b: float) -> float:
    """Smallest absolute angle between two headings."""
    return abs(wrap(a - b))
