"""A one-shot loud event scheduled to be heard at an exact time."""
from __future__ import annotations

from dataclasses import dataclass

from ..sound_character import SoundCharacter


@dataclass(slots=True)
class PendingSound:
    """Emitted from a fixed point at a fixed instant.

    Used for two things: an agent dying, and the scripted echo -- a ping that
    arrives a second time from a reflective chamber, on a different bearing,
    because it came by a different passage.
    """
    t: float
    x: float
    y: float
    character: SoundCharacter
