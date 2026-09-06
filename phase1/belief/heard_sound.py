"""A sound that arrived, kept for the display and the audio mixer."""
from __future__ import annotations

from dataclasses import dataclass

from ..sound_character import SoundCharacter


@dataclass(slots=True, frozen=True)
class HeardSound:
    t: float
    bearing: float        # world bearing in the belief frame
    quality: float
    character: SoundCharacter
