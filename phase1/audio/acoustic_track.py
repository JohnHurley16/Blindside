"""One direction that has been heard from more than once.

Not a contact and not an identification -- Belief already has `Contact` for that, on its
own merge rules, for the display. This is the mixer's own, coarser bookkeeping, and it
exists to answer exactly two questions: has this direction already sounded recently (so
one transmission is one gesture instead of six beeps), and is it markedly nearer than the
last time it spoke.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class AcousticTrack:
    bearing: float
    quality: float
    t_last: float
    t_last_gesture: float
    quality_last_gesture: float
    gestures: int = 0

    def closing(self) -> float:
        """How much nearer than the last time this direction sounded. Positive is toward."""
        return self.quality - self.quality_last_gesture

    def sounded(self, t: float) -> None:
        self.t_last_gesture = t
        self.quality_last_gesture = self.quality
        self.gestures += 1
