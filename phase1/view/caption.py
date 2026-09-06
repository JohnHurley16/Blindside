"""One thing worth saying, on screen, for a few seconds."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class Caption:
    """A short line of plain English describing something that just happened.

    Deliberately not telemetry. A viewer watching a cloud of dots cannot also parse
    eight point font in a corner, so the few moments that matter have to interrupt.
    """
    t: float
    text: str
    detail: str = ""
    weight: float = 1.0        # 1.0 ordinary, 2.0 the moments the test is built around

    def alpha(self, now: float, hold: float, fade: float) -> float:
        age = now - self.t
        if age < 0.0 or age > hold + fade:
            return 0.0
        if age <= hold:
            return 1.0
        return 1.0 - (age - hold) / fade
