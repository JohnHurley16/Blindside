"""The eleven names, so the cave is a place instead of a shape.

SPECTATOR-DISPLAY.md section 6.4, truth mark 3. The names themselves exist nowhere but
here -- `truth/cave.py` calls these rooms S, C1, DA, C2, ECHO, C3, ANC, SUMP, DB, C4
and R, which is a rasteriser's vocabulary and not a spectator's.

The coordinates are a hand copy of that module's chamber centres, because `view` may
not import `truth` and the truth channel's frame carries the whole 200 x 120 grid but
not a list of rooms. Nothing new reaches the renderer through this file: it already
draws every cell of the cave from `StageFrame.grid`, so a chamber centre is something
it could compute. If the cave is ever re-authored these have to be moved by hand, and
they will be visibly wrong on the first frame if they are not.

Three rooms are called JUNCTION on purpose. They are junctions; naming them C1, C2 and
C3 would teach a stranger a vocabulary in order to tell her something she can see.
"""
from __future__ import annotations

from typing import Final

Label = tuple[str, float, float]

CHAMBER_LABELS: Final[tuple[Label, ...]] = (
    ("YOUR SHAFT", 14.0, 60.0),
    ("JUNCTION", 44.0, 42.0),
    ("DEPOSIT A", 66.0, 16.0),
    ("THE BIG HALL", 82.0, 68.0),
    ("THE ECHO CHAMBER", 48.0, 98.0),
    ("JUNCTION", 122.0, 42.0),
    ("THE MACHINERY", 140.0, 86.0),
    ("THE SUMP", 108.0, 104.0),
    ("DEPOSIT B", 176.0, 96.0),
    ("JUNCTION", 166.0, 34.0),
    ("THEIR SHAFT", 188.0, 60.0),
)
