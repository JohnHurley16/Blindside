"""What the truth camera is looking at, and how wide. One frame's worth of intent."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Shot:
    """`key` names the subject, so the director can tell a new shot from a held one.
    `major` marks a shot that may override the dwell: a death, a moved beacon or a
    sound with no source is by definition not the noise the dwell exists to suppress."""

    cx: float
    cy: float
    cells: float
    key: str
    major: bool = False
