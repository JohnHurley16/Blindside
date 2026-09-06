"""Ray marching against the true grid. Used only by the sensor layer."""
from __future__ import annotations

import math

import numpy as np

from ..truth import cave


def march(x: float, y: float, angle: float, max_range: float,
          blocked: np.ndarray, step: float = 0.3) -> float | None:
    """Distance to the first blocked cell along `angle`, or None if nothing is hit.

    `blocked` is a boolean grid: pass ~FREE for sonar (rock stops sound) or
    ~WALKABLE for the near-field sense (the waterline is a surface too).
    """
    r = 0.0
    while r < max_range:
        r += step
        px = x + math.cos(angle) * r
        py = y + math.sin(angle) * r
        xi, yi = int(px), int(py)
        if not (0 <= xi < cave.W and 0 <= yi < cave.H) or blocked[yi, xi]:
            return r
    return None
