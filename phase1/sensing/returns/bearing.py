"""Passive acoustic: a direction and nothing else."""
from __future__ import annotations

from dataclasses import dataclass

from ...sound_character import SoundCharacter


@dataclass(slots=True, frozen=True)
class BearingReturn:
    """A bearing in the body frame, with no range.

    The bearing points down the passage the sound arrived through, not at the
    source through rock. Two returns on different bearings may be one object heard
    by two routes, or two objects. Nothing here says which.
    """
    bearing_body: float
    quality: float
    character: SoundCharacter
