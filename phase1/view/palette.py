"""Colours. Grey-box on purpose -- ugly is fine, illegible is not."""
from __future__ import annotations

import numpy as np

from ..sound_character import SoundCharacter

Rgb = tuple[float, float, float]

BACKGROUND: tuple[float, float, float] = (0.015, 0.015, 0.025)

# Point confidence runs from dim slate to near white. A marginal return must not look
# identical to a confident one, so confidence drives colour, size and alpha together.
POINT_LOW: np.ndarray = np.array([0.22, 0.32, 0.45])
POINT_HIGH: np.ndarray = np.array([0.80, 0.97, 1.00])

CONTACT: dict[SoundCharacter, Rgb] = {
    SoundCharacter.TONE: (1.00, 0.72, 0.25),      # something moving
    SoundCharacter.PING: (0.85, 0.95, 1.00),      # a ping heard, or its echo
    SoundCharacter.CRASH: (1.00, 0.30, 0.25),     # something broke
}
SIGNATURE: Rgb = (0.95, 0.30, 0.95)               # machinery winding up

AGENT: tuple[float, float, float, float] = (0.40, 1.00, 0.60, 1.00)
ELLIPSE: tuple[float, float, float, float] = (0.30, 1.00, 0.50, 0.90)
TRAIL: tuple[float, float, float, float] = (0.50, 0.60, 0.70, 0.35)
BEACON: tuple[float, float, float, float] = (0.60, 0.80, 1.00, 0.90)
FIX_FLASH: Rgb = (1.00, 0.95, 0.30)

# Truth, drawn only after the match is over.
TRUTH_WALL: tuple[float, float, float, float] = (0.90, 0.25, 0.20, 0.35)
TRUTH_FLOOD: tuple[float, float, float, float] = (0.20, 0.40, 0.90, 0.25)
TRUTH_TRAIL_PLAYER: tuple[float, float, float, float] = (1.00, 0.30, 0.20, 0.90)
TRUTH_TRAIL_RIVAL: tuple[float, float, float, float] = (1.00, 0.60, 0.20, 0.60)
TRUTH_BEACON: tuple[float, float, float, float] = (1.00, 0.50, 0.30, 0.90)
TRUTH_DEPOSIT: tuple[float, float, float, float] = (1.00, 0.90, 0.30, 0.90)

HUD: Rgb = (0.85, 0.90, 0.95)
BANNER: Rgb = (1.00, 0.85, 0.40)
LEGEND: Rgb = (0.50, 0.55, 0.60)
