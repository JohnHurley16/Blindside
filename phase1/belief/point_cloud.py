"""The accumulated map: sensor returns placed in the agent's estimated frame.

Each point is stamped with the time it was placed, which is what lets a fix drag
the recent ones back into line. See `pose_correction.PoseCorrection`.
"""
from __future__ import annotations

import numpy as np

from ..point_source import PointSource
from .pose_correction import PoseCorrection


# The occupancy grid covers belief space, which can drift well outside the cave, so it
# is larger than the cave and offset. Two-cell bins: coarse enough to be cheap, fine
# enough that a four-cell passage still reads as open.
GRID_CELL: float = 2.0
GRID_OFFSET: float = 60.0
GRID_W: int = 170
GRID_H: int = 130

_SOURCE_CODE: dict[PointSource, int] = {
    PointSource.SONAR: 0,
    PointSource.NEAR: 1,
    PointSource.FALSE: 2,
    PointSource.LIDAR: 3,
}


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
        # Which sense produced each point, so the display can tell a wall the agent
        # pinged from ground it merely walked through. Drawing them identically is
        # what makes an accumulated map read as noise.
        self.source: np.ndarray = np.zeros(capacity, dtype=np.uint8)
        self.n: int = 0
        # Which bins hold at least one sensed point. This is the map the policy can
        # actually steer by: globally wrong by whatever the drift is, but the agent is
        # wrong by the same amount, so locally it is right.
        self.occupied: np.ndarray = np.zeros((GRID_W, GRID_H), dtype=bool)

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
        self.source[i] = _SOURCE_CODE[source]
        self.n += 1
        ix, iy = self._bin(x, y)
        if 0 <= ix < GRID_W and 0 <= iy < GRID_H:
            self.occupied[ix, iy] = True

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
        self._rebuild_grid()

    @staticmethod
    def _bin(x: float, y: float) -> tuple[int, int]:
        return int((x + GRID_OFFSET) / GRID_CELL), int((y + GRID_OFFSET) / GRID_CELL)

    def _rebuild_grid(self) -> None:
        """After a fix moves the points, the bins they sat in are stale."""
        n = self.n
        self.occupied[:] = False
        if n == 0:
            return
        ix = ((self.x[:n] + GRID_OFFSET) / GRID_CELL).astype(int)
        iy = ((self.y[:n] + GRID_OFFSET) / GRID_CELL).astype(int)
        ok = (ix >= 0) & (ix < GRID_W) & (iy >= 0) & (iy < GRID_H)
        self.occupied[ix[ok], iy[ok]] = True

    def blocked(self, x: float, y: float) -> bool:
        ix, iy = self._bin(x, y)
        if not (0 <= ix < GRID_W and 0 <= iy < GRID_H):
            return False
        return bool(self.occupied[ix, iy])

    def clearance(self, x: float, y: float, angle: float, max_range: float,
                  step: float = 0.7) -> float:
        """How far the believed map is open along a heading, up to max_range."""
        r = 0.0
        cos_a, sin_a = np.cos(angle), np.sin(angle)
        while r < max_range:
            r += step
            if self.blocked(x + cos_a * r, y + sin_a * r):
                return r
        return max_range

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
