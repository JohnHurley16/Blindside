"""Sound as it actually spreads through the cave: along passages, not through rock."""
from __future__ import annotations

import heapq
import math

import numpy as np

from .. import tuning as T
from ..truth import cave


class SoundField:
    """Path distance from one emitter to every reachable cell.

    Built with Dijkstra over open cells, so the distance to a listener is the length
    of the passage between them and the arrival bearing is the direction the sound
    came *in* from. That is what makes a bearing ambiguous in a cave, and it is what
    gives an echo a mechanism rather than a script: the same ping reaching a listener
    by two routes arrives on two different bearings.

    Flooded cells cost less: water carries.
    """

    _NEIGHBOURS: tuple[tuple[int, int, float], ...] = (
        (-1, 0, 1.0), (1, 0, 1.0), (0, -1, 1.0), (0, 1, 1.0),
        (-1, -1, 1.4142), (1, -1, 1.4142), (-1, 1, 1.4142), (1, 1, 1.4142),
    )

    def __init__(self, source_x: float, source_y: float, max_range: float) -> None:
        self.source_x: float = float(source_x)
        self.source_y: float = float(source_y)
        self.max_range: float = float(max_range)
        self.dist: np.ndarray = np.full((cave.H, cave.W), np.inf)
        self.pred: np.ndarray = np.full((cave.H, cave.W), -1, dtype=np.int32)
        self._build()

    def _build(self) -> None:
        sx, sy = int(self.source_x), int(self.source_y)
        if not (0 <= sx < cave.W and 0 <= sy < cave.H) or not cave.FREE[sy, sx]:
            return
        free = cave.FREE
        grid = cave.GRID
        self.dist[sy, sx] = 0.0
        heap: list[tuple[float, int, int]] = [(0.0, sx, sy)]
        while heap:
            d, x, y = heapq.heappop(heap)
            if d > self.dist[y, x]:
                continue
            for dx, dy, step in self._NEIGHBOURS:
                nx, ny = x + dx, y + dy
                if not free[ny, nx]:
                    continue
                cost = step * (T.FLOODED_COST if grid[ny, nx] == 2 else 1.0)
                nd = d + cost
                if nd < self.dist[ny, nx] and nd <= self.max_range:
                    self.dist[ny, nx] = nd
                    self.pred[ny, nx] = y * cave.W + x
                    heapq.heappush(heap, (nd, nx, ny))

    def arrival(self, listener_x: float, listener_y: float) -> tuple[float, float] | None:
        """(path_distance, arrival_bearing_world), or None if inaudible.

        The bearing is taken by walking a few steps back along the shortest path, so
        it points down the passage rather than at the source through rock.
        """
        xi, yi = int(listener_x), int(listener_y)
        if not (0 <= xi < cave.W and 0 <= yi < cave.H):
            return None
        d = float(self.dist[yi, xi])
        if not math.isfinite(d) or d > self.max_range:
            return None
        cx, cy = xi, yi
        for _ in range(5):
            p = int(self.pred[cy, cx])
            if p < 0:
                break
            cx, cy = p % cave.W, p // cave.W
        if (cx, cy) == (xi, yi):
            return d, 0.0
        return d, math.atan2(cy + 0.5 - listener_y, cx + 0.5 - listener_x)
