"""The machine glyph. Functions only, like `shapes.py`.

SPECTATOR-DISPLAY.md section 6.4: a plan-view vehicle in world coordinates -- a hull,
two tracks, a sensor head that rotates slowly, and a cargo pip per load aboard, about
seventeen line segments lying flat on the floor plane.

It stays 2.4 cells long against a true radius of 0.6, and that 2x exaggeration is the
largest scale licence in the design. The third dimension created pressure to make it
bigger and picture-in-picture removed it: a larger glyph destroys the two beats the
glyph exists for -- the near miss at 9.038 cells against a 9.000 radius, and the pass
at 0.41 cells. The camera is the free variable; the glyph is not.

Solid is the thing, hollow is a belief about the thing: a true machine gets its hull
hatched and its tracks drawn, and the ghost gets the same outline with neither.
"""
from __future__ import annotations

import math

from .. import tuning as T

Segment = tuple[float, float, float, float]


def machine(x: float, y: float, heading: float, length: float, *,
            filled: bool = True, alive: bool = True, cargo: int = 0,
            head: float = 0.0, damage: float = 0.0) -> list[Segment]:
    """Segments as (x0, y0, x1, y1) pairs in world cells.

    `head` is the sensor head's angle relative to the hull; it turns slowly whether or
    not the machine is doing anything, because a still machine that is still *looking*
    reads differently from a dead one.

    `damage` is ground shock taken, 0 to 1, and it drops the hull hatching front to back
    (THE-MACHINERY.md 4.7). The hatching is what makes a line drawing read as a solid, so
    losing it is the glyph walking toward the wreck cross it becomes at 1.0 -- and it is
    the only damage display in the design that survives CAMERA_WIDE_CELLS, where a glyph
    is nine pixels and nothing written anywhere on screen can be read.
    """
    half = length * 0.5
    beam = length * 0.23
    local: list[Segment] = []

    if alive:
        hull = ((half, 0.0), (half * 0.4, beam), (-half, beam),
                (-half, -beam), (half * 0.4, -beam))
    else:
        # A wreck: the hull collapses to a cross inside its own footprint, and stays
        # for the rest of the match. Something died there and the place is marked.
        hull = ((half, beam), (-half, -beam))
        local += [(half, -beam, -half, beam)]
    for index in range(len(hull) - (0 if alive else 1)):
        ax, ay = hull[index]
        bx, by = hull[(index + 1) % len(hull)]
        local.append((ax, ay, bx, by))

    if not alive:
        return _place(local, x, y, heading)

    if filled:
        # two tracks, outboard of the hull
        for side in (1.0, -1.0):
            outer, inner = beam * 1.55 * side, beam * 1.02 * side
            fore, aft = half * 0.62, -half * 0.92
            local += [(aft, inner, fore, inner), (fore, inner, fore, outer),
                      (fore, outer, aft, outer), (aft, outer, aft, inner)]
        # hatching, which is what makes a line drawing read as a solid
        strokes = 3 if damage < T.DAMAGE_HATCH_1 else (2 if damage < T.DAMAGE_HATCH_2 else 1)
        for f in (-0.55, -0.15, 0.25)[:strokes]:
            local.append((half * f, -beam * 0.82, half * f, beam * 0.82))
        for pip in range(cargo):
            px = -half * 0.72 + pip * length * 0.16
            local.append((px, -beam * 0.45, px, beam * 0.45))

    # the sensor head
    hx, hy = half * 0.06, 0.0
    reach = length * 0.34
    local.append((hx, hy, hx + math.cos(head) * reach, hy + math.sin(head) * reach))
    local.append((hx + math.cos(head + 1.05) * reach * 0.55,
                  hy + math.sin(head + 1.05) * reach * 0.55,
                  hx + math.cos(head - 1.05) * reach * 0.55,
                  hy + math.sin(head - 1.05) * reach * 0.55))
    return _place(local, x, y, heading)


def _place(local: list[Segment], x: float, y: float, heading: float) -> list[Segment]:
    c, s = math.cos(heading), math.sin(heading)
    return [(x + ax * c - ay * s, y + ax * s + ay * c,
             x + bx * c - by * s, y + bx * s + by * c)
            for ax, ay, bx, by in local]
