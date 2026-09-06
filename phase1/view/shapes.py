"""Geometry helpers for the overlays. Functions only."""
from __future__ import annotations

import math

import numpy as np


def ring(cx: float, cy: float, r: float, n: int = 72, a0: float = 0.0,
         a1: float = 2 * math.pi, z: float = 0.0) -> np.ndarray:
    a = np.linspace(a0, a1, n)
    return np.column_stack([cx + r * np.cos(a), cy + r * np.sin(a), np.full(n, z)])


def to_segments(polyline: np.ndarray) -> np.ndarray:
    """A connected polyline as disjoint segment pairs, for connect='segments'."""
    return np.repeat(polyline, 2, axis=0)[1:-1]


def wedge(x: float, y: float, bearing: float, half_angle: float, length: float,
          z: float = 0.15) -> list[np.ndarray]:
    """Three rays from a point: the bearing and its uncertainty bounds.

    The wedge is the honest picture of a bearing-only contact -- a direction with an
    angular error, and no range at all.
    """
    origin = np.array([x, y, z])
    out: list[np.ndarray] = []
    for a in (bearing - half_angle, bearing, bearing + half_angle):
        out += [origin, origin + np.array([math.cos(a) * length, math.sin(a) * length, 0.0])]
    return out
