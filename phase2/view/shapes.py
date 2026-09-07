"""Geometry helpers for the overlays. Functions only.

`ring` and `to_segments` are Phase 1's; `dashes` is new, because Phase 2's map has
to say "seen but not walked" and a dashed line is the way that reads.
"""
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


def ellipse(cx: float, cy: float, along: float, cross: float, angle: float,
            n: int = 64, z: float = 0.0) -> np.ndarray:
    """An error ellipse: `along` and `cross` are its semi-axes, `angle` the
    direction the along axis points."""
    a = np.linspace(0.0, 2 * math.pi, n)
    ex, ey = along * np.cos(a), cross * np.sin(a)
    c, s = math.cos(angle), math.sin(angle)
    return np.column_stack([cx + c * ex - s * ey, cy + s * ex + c * ey, np.full(n, z)])


def dashes(x0: float, y0: float, x1: float, y1: float, dash: float = 2.0,
           z: float = 0.0) -> list[np.ndarray]:
    """A dashed segment, as pairs of points for connect='segments'."""
    length = math.hypot(x1 - x0, y1 - y0)
    if length <= 1e-6:
        return []
    ux, uy = (x1 - x0) / length, (y1 - y0) / length
    out: list[np.ndarray] = []
    travelled = 0.0
    while travelled < length:
        end = min(travelled + dash, length)
        out.append(np.array([x0 + ux * travelled, y0 + uy * travelled, z]))
        out.append(np.array([x0 + ux * end, y0 + uy * end, z]))
        travelled = end + dash
    return out
