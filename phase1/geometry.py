"""Angle and vector helpers. No state, no classes, imported everywhere."""
from __future__ import annotations

import math

TAU: float = 2.0 * math.pi


def wrap(a: float) -> float:
    """Fold an angle into (-pi, pi]."""
    return (a + math.pi) % TAU - math.pi


def bearing(from_x: float, from_y: float, to_x: float, to_y: float) -> float:
    return math.atan2(to_y - from_y, to_x - from_x)


def dist(ax: float, ay: float, bx: float, by: float) -> float:
    return math.hypot(bx - ax, by - ay)


def clamp(v: float, lo: float, hi: float) -> float:
    return lo if v < lo else (hi if v > hi else v)


def angle_between(a: float, b: float) -> float:
    """Smallest absolute angle between two headings."""
    return abs(wrap(a - b))
