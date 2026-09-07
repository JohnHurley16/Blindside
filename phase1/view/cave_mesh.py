"""The cave, extruded into rock. Built once, uploaded once, never touched again.

SPECTATOR-DISPLAY.md sections 3.2 and 6.4, marks 1 and 2. One quad per rock face that
is exposed to open space, plus a cap over every rock cell: 43,202 triangles, about
5 ms of CPU and one upload. Orbiting it is free, because an orbit needs no re-upload.

Mesh, not points, and the reason is measured: the capped mesh reads as a cave -- a
solid massif with chambers and passages carved into it -- and the point version reads
as glowing dust along the edge of a flat map, which is the same picture the belief
scene already draws, in a different colour. Cost was not the discriminator.

The lighting is a fixed **world** light, not a camera one: four face brightnesses
attached to the four compass directions, with the wall foot darkened. As the viewer
orbits, the lit faces move to the back and the shadowed ones come round to the front.
That is why it reads as stone rather than as a texture.

Height means exactly one bit here -- rock or not rock. The sim's cave has no vertical
dimension at all, so the eight cells of wall are invented, and a varying height would
be a lie: it would read as terrain the machine has to climb, and there is no terrain.
The one real scalar, graph distance from the shaft, stays in the floor as brightness.
"""
from __future__ import annotations

from collections import deque

import numpy as np
from vispy.scene import visuals
from vispy.visuals.transforms import STTransform

from .. import tuning as T
from . import palette


class CaveMesh:
    """The rock as a mesh and the floor as an image, in the truth scene."""

    def __init__(self, parent: object, grid: np.ndarray,
                 origin: tuple[float, float]) -> None:
        height = T.CAVE_WALL_HEIGHT_CELLS
        vertices, faces, colours = _build(grid, height)
        self.triangles: int = len(faces)
        self.mesh = visuals.Mesh(vertices=vertices, faces=faces, vertex_colors=colours,
                                 parent=parent)
        self.mesh.set_gl_state("opaque", depth_test=True, cull_face=False)
        self.mesh.order = 0

        # Transparent under rock, so the cap carries the rock colour and the two
        # surfaces are never coplanar. That, with fov=0, is the z-fighting fix: at a
        # 2.6-cell wall under perspective the whole cave came back barred with black
        # stripes, and at 8 cells it degraded to a horizon line but did not go away.
        self.floor = visuals.Image(_floor_image(grid, origin), parent=parent,
                                   interpolation="nearest")
        self.floor.set_gl_state("translucent", depth_test=True)
        self.floor.order = 0
        self.floor.transform = STTransform(translate=(0.0, 0.0, -0.02))


# ---- the mesh ----------------------------------------------------------------------------
def _build(grid: np.ndarray, height: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    rock = grid == 0
    free = ~rock
    padded = np.pad(free, 1, constant_values=False)
    lit = np.asarray(palette.ROCK_LIT, dtype=np.float32)

    quads: list[np.ndarray] = []
    colours: list[np.ndarray] = []

    # caps, over every rock cell, at the top
    ys, xs = np.nonzero(rock)
    cap = np.empty((len(ys), 4, 3), dtype=np.float32)
    for index, (ox, oy) in enumerate(((0, 0), (1, 0), (1, 1), (0, 1))):
        cap[:, index, 0] = xs + ox
        cap[:, index, 1] = ys + oy
        cap[:, index, 2] = height
    quads.append(cap)
    colours.append(np.tile(lit * T.CAVE_CAP_SHADE, (len(ys), 4, 1)))

    # walls, one per rock face that an open cell can see
    exposures = (
        ("+x", rock & padded[1:-1, 2:], T.CAVE_FACE_SHADES[0],
         ((1, 0, 0.0), (1, 1, 0.0), (1, 1, 1.0), (1, 0, 1.0))),
        ("+y", rock & padded[2:, 1:-1], T.CAVE_FACE_SHADES[1],
         ((0, 1, 0.0), (1, 1, 0.0), (1, 1, 1.0), (0, 1, 1.0))),
        ("-x", rock & padded[1:-1, :-2], T.CAVE_FACE_SHADES[2],
         ((0, 0, 0.0), (0, 1, 0.0), (0, 1, 1.0), (0, 0, 1.0))),
        ("-y", rock & padded[:-2, 1:-1], T.CAVE_FACE_SHADES[3],
         ((0, 0, 0.0), (1, 0, 0.0), (1, 0, 1.0), (0, 0, 1.0))),
    )
    for _, mask, shade, corners in exposures:
        ys, xs = np.nonzero(mask)
        if not len(ys):
            continue
        quad = np.empty((len(ys), 4, 3), dtype=np.float32)
        colour = np.empty((len(ys), 4, 3), dtype=np.float32)
        for index, (ox, oy, oz) in enumerate(corners):
            quad[:, index, 0] = xs + ox
            quad[:, index, 1] = ys + oy
            quad[:, index, 2] = oz * height
            # a vertical gradient, so a wall has a visible foot as well as a top
            colour[:, index] = lit * shade * (T.CAVE_BASE_SHADE if oz == 0.0 else 1.0)
        quads.append(quad)
        colours.append(colour)

    vertices = np.concatenate(quads).reshape(-1, 3)
    vertex_colours = np.concatenate(colours).reshape(-1, 3)
    count = len(vertices) // 4
    base = np.arange(count, dtype=np.uint32)[:, None] * 4
    faces = np.concatenate([base + np.array([0, 1, 2], dtype=np.uint32),
                            base + np.array([0, 2, 3], dtype=np.uint32)])
    return vertices, faces, np.column_stack([vertex_colours,
                                             np.ones(len(vertices), dtype=np.float32)])


# ---- the floor ----------------------------------------------------------------------------
def _floor_image(grid: np.ndarray, origin: tuple[float, float]) -> np.ndarray:
    """Dry passage and water only, darkened by walking distance from the shaft.

    DESIGN-PRINCIPLES section 2 -- "further in is where the blocks you do not have
    are" -- as a gradient, for free. Depth is drawn as darkness, never as altitude.
    """
    image = np.zeros((*grid.shape, 4), dtype=np.float32)
    depth = _graph_depth(grid, origin)
    tint = 1.0 - (1.0 - T.DEPTH_TINT_FLOOR) * depth
    dry = grid == 1
    image[dry, :3] = np.asarray(palette.FLOOR, dtype=np.float32) * tint[dry, None]
    image[dry, 3] = 1.0
    wet = grid == 2
    image[wet, :3] = np.asarray(palette.WATER, dtype=np.float32) * tint[wet, None]
    image[wet, 3] = 1.0
    return image


def _graph_depth(grid: np.ndarray, origin: tuple[float, float]) -> np.ndarray:
    """0 at the shaft, 1 at the furthest reachable cell. A flood fill, not a ray:
    the far end of the cave is far by the passages, not by the crow."""
    passable = grid > 0
    height, width = grid.shape
    dist = np.full(grid.shape, -1, dtype=np.int32)
    start = (min(max(int(origin[1]), 0), height - 1),
             min(max(int(origin[0]), 0), width - 1))
    if not passable[start]:
        return np.zeros(grid.shape, dtype=np.float32)
    dist[start] = 0
    queue: deque[tuple[int, int]] = deque([start])
    while queue:
        y, x = queue.popleft()
        for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
            if 0 <= ny < height and 0 <= nx < width and passable[ny, nx] and dist[ny, nx] < 0:
                dist[ny, nx] = dist[y, x] + 1
                queue.append((ny, nx))
    furthest = float(dist.max())
    if furthest <= 0.0:
        return np.zeros(grid.shape, dtype=np.float32)
    return np.clip(dist / furthest, 0.0, 1.0).astype(np.float32)
