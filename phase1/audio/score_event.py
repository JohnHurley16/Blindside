"""One sounding gesture of the score, with no engine in it.

The transport emits these; `score_render` is the only thing that knows they become
`Mixer._room()` calls. Same split as `Ratchet`, which returns the string "notch" and lets
the mixer decide what a notch is made of -- so the score's structure can be reasoned about,
tabulated and diffed without a device, a buffer or numpy anywhere near it.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ScoreEvent:
    t: float                        # absolute seconds from the head of the trailer
    line: str                       # which line of which section emitted it, for the log
    tonal: bool                     # False is a band-limited noise stroke
    ratios: tuple[float, ...]       # inharmonic struck-object stack; (1.0,) is a pure sine
    tilt: float                     # how fast the stack rolls off; see Mixer._struck
    f0: float
    f1: float                       # equal to f0 unless the note glides
    duration: float
    attack: float                   # a long attack is the score's only crescendo (see NOTES)
    decay: float
    amplitude: float
    pan: float                      # -1 left, +1 right
    quality: float                  # the room: low is far, duller, wetter, longer tails
    max_reflections: int
    noise_lowpass: int              # moving-average width, tonal events ignore it

    def hz(self) -> str:
        return f"{self.f0:.2f}" if self.f0 == self.f1 else f"{self.f0:.2f}->{self.f1:.2f}"
