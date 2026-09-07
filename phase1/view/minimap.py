"""Where the camera is looking, and where everything else is. The slice-1 stub.

SPECTATOR-DISPLAY.md section 3.3 asks for ten marks; slice 1 builds four of them --
the outline, the two true machines, and the camera footprint -- and slice 5 adds the
rest. What is here is the part that earns its place immediately: two of the three
pictures on screen can be spun and the big one moves on the beat, so exactly one thing
has to be the same way up, at the same scale, showing the same thing, every time she
looks at it.

Exactly 1.00 pixel per cell over the 200 x 120 grid, so the image is uploaded at its
native resolution into a viewport of exactly its own size and is never resampled --
which makes `interpolation="nearest"` pixel-exact rather than approximately so. It
never rotates and never zooms, which is also why it is 2D.
"""
from __future__ import annotations

import numpy as np
from vispy.scene import visuals

from ..match.stage_frame import StageFrame
from . import palette


class Minimap:
    def __init__(self, parent: object, grid: np.ndarray) -> None:
        self.rows: int = int(grid.shape[0])
        self.cols: int = int(grid.shape[1])
        image = np.zeros((*grid.shape, 4), dtype=np.float32)
        # Its own encoding, not the cave's: at one pixel per cell a 16% floor on an 8%
        # rock is two blacks, and the shape of the place is the whole reason it is here.
        image[grid == 0, :3] = tuple(c * 0.55 for c in palette.ROCK)
        image[grid == 1, :3] = tuple(c * 0.85 for c in palette.WARM_DIM)
        image[grid == 2, :3] = tuple(c * 1.9 for c in palette.WATER)
        image[:, :, 3] = 1.0
        self.image = visuals.Image(image, parent=parent, interpolation="nearest")
        # vispy's "translucent" preset leaves depth_test ON, and the cave mesh has
        # already written depth over every pixel this overlay sits on -- so a visual
        # that does not switch it off is silently discarded. That is what an empty
        # minimap over a full truth scene looks like, and it cost an afternoon.
        self.image.set_gl_state("translucent", depth_test=False)
        self.image.order = 0

        # A bone rectangle with a nose, showing where the truth camera is and which way
        # it is pointing. This is the minimap's primary job -- it answers the exact
        # question a director camera creates.
        self.footprint = visuals.Line(parent=parent, connect="segments", width=1,
                                      color=(*palette.BONE, 0.55))
        self.dots = visuals.Markers(parent=parent)
        for visual in (self.footprint, self.dots):
            visual.set_gl_state("translucent", depth_test=False)
        self.footprint.order = 1
        self.dots.order = 2

    def update(self, frame: StageFrame, cx: float, cy: float,
               cells: float, vertical_fraction: float) -> None:
        half_w = cells * 0.5
        half_h = cells * vertical_fraction * 0.5
        left, right = cx - half_w, cx + half_w
        bottom, top = cy - half_h, cy + half_h
        box = ((left, bottom), (right, bottom), (right, top), (left, top))
        segments: list[list[float]] = []
        for index in range(4):
            ax, ay = box[index]
            bx, by = box[(index + 1) % 4]
            segments += [[ax, ay, 0.0], [bx, by, 0.0]]
        segments += [[cx, top, 0.0], [cx, top + 4.0, 0.0]]      # the nose, north-up
        self.footprint.set_data(np.array(segments, dtype=np.float32))

        marks = np.array([[frame.player.x, frame.player.y, 0.0],
                          [frame.rival.x, frame.rival.y, 0.0]], dtype=np.float32)
        colours = np.array([(*palette.BONE, 1.0),
                            (*palette.EMBER, 1.0 if frame.rival.alive else 0.35)])
        self.dots.set_data(marks, face_color=colours, size=4, symbol="disc", edge_width=0)
