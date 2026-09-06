"""The hand-authored cave, rasterised once at import.

Ground truth. Only `truth` and `sensing` may import this module.

Grid values: 0 = rock, 1 = dry passage, 2 = flooded. Agents walk only on 1;
sound passes through 1 and 2, and travels further through 2.
"""
from __future__ import annotations

import math
from typing import Final

import numpy as np

from .. import tuning as T

W: Final[int] = 200
H: Final[int] = 120

Point = tuple[float, float]
Chamber = tuple[int, int, int]
Passage = tuple[str, str, int, bool]

# Chambers: name -> (x, y, radius). Coordinates are cells; y grows upward.
CHAMBERS: Final[dict[str, Chamber]] = {
    "S": (14, 60, 6),        # player's shaft
    "C1": (44, 42, 8),
    "DA": (66, 16, 6),       # deposit A
    "C2": (82, 68, 11),      # the big hall
    "ECHO": (48, 98, 5),     # reflective dead end
    "C3": (122, 42, 8),
    "ANC": (140, 86, 12),    # the ancient system's chamber
    "SUMP": (108, 104, 9),   # flooded
    "DB": (176, 96, 7),      # deposit B
    "C4": (166, 34, 7),
    "R": (188, 60, 5),       # rival's shaft
}

PASSAGES: Final[list[Passage]] = [
    ("S", "C1", 5, False), ("C1", "DA", 4, False), ("C1", "C2", 6, False),
    ("C2", "ECHO", 4, False), ("C2", "C3", 5, False), ("C3", "ANC", 5, False),
    ("ANC", "DB", 4, False), ("C3", "C4", 5, False), ("C4", "DB", 4, False),
    ("C2", "SUMP", 5, True), ("SUMP", "ANC", 4, True), ("R", "C4", 5, False),
    ("R", "DB", 5, False),
]

DEPOSITS: Final[dict[str, Point]] = {
    "A": (float(CHAMBERS["DA"][0]), float(CHAMBERS["DA"][1])),
    "B": (float(CHAMBERS["DB"][0]), float(CHAMBERS["DB"][1])),
}
ANCIENT_POS: Final[Point] = (float(CHAMBERS["ANC"][0]), float(CHAMBERS["ANC"][1]))
ECHO_POS: Final[Point] = (float(CHAMBERS["ECHO"][0]), float(CHAMBERS["ECHO"][1] + 3))
SHAFTS: Final[dict[str, Point]] = {
    "player": (float(CHAMBERS["S"][0]), float(CHAMBERS["S"][1])),
    "rival": (float(CHAMBERS["R"][0]), float(CHAMBERS["R"][1])),
}

# Survey routes: prior intel handed to the policies, as waypoints in the shaft frame.
ROUTES: Final[dict[str, list[str]]] = {
    "player_out_A": ["C1", "DA"],
    "player_A_to_B": ["C1", "C2", "C3", "C4", "DB"],
    "player_home_from_B": ["C4", "C3", "C2", "C1", "S"],
    "player_home_from_A": ["C1", "S"],
    "rival_out": ["C4", "C3", "C2", "C3", "ANC", "DB", "ANC", "C3", "C2", "C1", "DA"],
}


def _rasterise() -> np.ndarray:
    yy, xx = np.mgrid[0:H, 0:W]
    grid = np.zeros((H, W), dtype=np.uint8)
    rng = np.random.default_rng(T.SEED)
    for name, (cx, cy, r) in CHAMBERS.items():
        # slightly lumpy chambers so sonar returns are not perfect circles
        ang = np.arctan2(yy - cy, xx - cx)
        wob = (1.0
               + 0.12 * np.sin(3 * ang + rng.uniform(0, 6))
               + 0.08 * np.cos(5 * ang + rng.uniform(0, 6)))
        mask = (xx - cx) ** 2 + (yy - cy) ** 2 <= (r * wob) ** 2
        grid[mask] = 2 if name == "SUMP" else 1
    for a, b, width, flooded in PASSAGES:
        ax, ay, _ = CHAMBERS[a]
        bx, by, _ = CHAMBERS[b]
        # gentle bend so passages are not straight lines
        mx, my = (ax + bx) / 2.0, (ay + by) / 2.0
        nx, ny = -(by - ay), (bx - ax)
        nl = math.hypot(nx, ny) or 1.0
        bend = rng.uniform(-0.18, 0.18) * nl
        mx += nx / nl * bend
        my += ny / nl * bend
        for (x0, y0), (x1, y1) in (((ax, ay), (mx, my)), ((mx, my), (bx, by))):
            steps = int(math.hypot(x1 - x0, y1 - y0) * 2) + 1
            for i in range(steps + 1):
                f = i / steps
                px, py = x0 + (x1 - x0) * f, y0 + (y1 - y0) * f
                mask = (xx - px) ** 2 + (yy - py) ** 2 <= (width / 2.0) ** 2
                if flooded:
                    grid[mask & (grid == 0)] = 2
                else:
                    grid[mask] = 1
    grid[0, :] = 0
    grid[-1, :] = 0
    grid[:, 0] = 0
    grid[:, -1] = 0
    return grid


GRID: Final[np.ndarray] = _rasterise()
FREE: Final[np.ndarray] = GRID > 0        # sound passes
WALKABLE: Final[np.ndarray] = GRID == 1   # agents pass


def is_walkable(x: float, y: float) -> bool:
    xi, yi = int(x), int(y)
    return 0 <= xi < W and 0 <= yi < H and bool(WALKABLE[yi, xi])


def is_free(x: float, y: float) -> bool:
    xi, yi = int(x), int(y)
    return 0 <= xi < W and 0 <= yi < H and bool(FREE[yi, xi])


def wall_outline() -> np.ndarray:
    """Rock cells that touch open space: the true wall, for the post-match reveal."""
    pad = np.pad(FREE, 1)
    edge = (pad[:-2, 1:-1] | pad[2:, 1:-1] | pad[1:-1, :-2] | pad[1:-1, 2:]) & (GRID == 0)
    wy, wx = np.nonzero(edge)
    return np.column_stack([wx + 0.5, wy + 0.5])


def flooded_cells() -> np.ndarray:
    fy, fx = np.nonzero(GRID == 2)
    return np.column_stack([fx + 0.5, fy + 0.5])
