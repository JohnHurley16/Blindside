"""The amplitude curve of one voice.

Split out of `Voice` so the attack can be a distance cue. A transient that has crossed a
hundred cells of flooded passage arrives smeared -- the rock and the water have taken its
edge off long before they have taken its level off -- so `attack` is set by quality and
not by the recipe.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .envelope_shape import EnvelopeShape

_END_TAPER: float = 0.10        # fraction of duration spent easing an exponential tail to
                                # zero, so cutting the array off does not click


@dataclass(frozen=True, slots=True)
class Envelope:
    attack: float
    decay: float
    shape: EnvelopeShape = EnvelopeShape.LINEAR

    def curve(self, t: np.ndarray, duration: float) -> np.ndarray:
        """`t` is float32 and stays float32: these arrays are built on the game thread."""
        rise = np.clip(t / np.float32(max(self.attack, 1e-6)), 0.0, 1.0)
        if self.shape is EnvelopeShape.EXPONENTIAL:
            fall = np.exp(-t / np.float32(max(self.decay, 1e-6)))
            taper = np.float32(max(duration * _END_TAPER, 1e-6))
            fall = fall * np.clip((np.float32(duration) - t) / taper, 0.0, 1.0)
        else:
            fall = np.clip((np.float32(duration) - t) / np.float32(max(self.decay, 1e-6)),
                           0.0, 1.0)
        return rise * fall
