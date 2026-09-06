"""The accumulated map: sensor returns placed in the agent's estimated frame.

Each point is stamped with the time it was placed, which is what lets a fix drag
the recent ones back into line. See `pose_correction.PoseCorrection`.
"""
from __future__ import annotations

import numpy as np

from ..point_source import PointSource
from .pose_correction import PoseCorrection


class PointCloud:
    """Flat preallocated arrays, because this is redrawn every frame."""

    def __init__(self, capacity: int, rng: np.random.Generator) -> None:
        self.capacity: int = capacity
        self.rng: np.random.Generator = rng
        self.x: np.ndarray = np.zeros(capacity)
        self.y: np.ndarray = np.zeros(capacity)
        self.z: np.ndarray = np.zeros(capacity)
        self.confidence: np.ndarray = np.zeros(capacity)
        self.t: np.ndarray = np.zeros(capacity)
        self.n: int = 0

    def add(self, x: float, y: float, confidence: float, t: float,
            source: PointSource, wall_height: float) -> None:
        if self.n >= self.capacity:
            return
        i = self.n
        self.x[i] = x
        self.y[i] = y
        # A 2D sim gives 2D returns; a flat sheet is nothing to orbit. Wall hits get a
        # short vertical scatter so passages read as curtains. Near-field hits sit on
        # the floor, so the walked trail reads as a distinct low band.
        self.z[i] = 0.0 if source is PointSource.NEAR else float(self.rng.uniform(0.0, wall_height))
        self.confidence[i] = confidence
        self.t[i] = t
        self.n += 1

    def relax(self, correction: PoseCorrection) -> None:
        """Slide everything placed since the last fix onto the corrected pose."""
        n = self.n
        if n == 0:
            return
        mask = self.t[:n] > correction.epoch_t
        if not mask.any():
            return
        nx, ny = correction.apply(self.x[:n][mask], self.y[:n][mask], self.t[:n][mask])
        xs = self.x[:n]
        ys = self.y[:n]
        xs[mask] = nx
        ys[mask] = ny
        self.x[:n] = xs
        self.y[:n] = ys

    def positions(self) -> np.ndarray:
        return np.column_stack([self.x[:self.n], self.y[:self.n], self.z[:self.n]])

    def count_ahead(self, x: float, y: float, cos_h: float, sin_h: float,
                    radius: float) -> int:
        n = self.n
        if n == 0:
            return 0
        dx = self.x[:n] - x
        dy = self.y[:n] - y
        forward = dx * cos_h + dy * sin_h
        return int(np.count_nonzero((forward > 0.0) & (dx * dx + dy * dy < radius * radius)))
