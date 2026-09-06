"""An unresolved detection. Not an identification."""
from __future__ import annotations

import math
from dataclasses import dataclass

from .. import geometry as G
from ..sound_character import SoundCharacter


@dataclass(slots=True)
class Contact:
    """A bearing that has been heard one or more times.

    It might be a rival, an ancient system, or the same ping arriving twice by two
    different passages. The glossary is strict: a contact is not an identification,
    and nothing in this class resolves it. The player does that, or fails to.
    """

    bearing: float                 # world bearing in the *belief* frame
    quality: float
    character: SoundCharacter
    t_first: float
    t_last: float
    returns: int = 1

    @property
    def age(self) -> float:
        return self.t_last - self.t_first

    def matches(self, bearing: float, t: float, merge_deg: float, merge_s: float) -> bool:
        return (G.angle_between(self.bearing, bearing) < math.radians(merge_deg)
                and t - self.t_last < merge_s)

    def absorb(self, bearing: float, quality: float, character: SoundCharacter,
               t: float) -> None:
        self.bearing = G.wrap(self.bearing + 0.5 * G.wrap(bearing - self.bearing))
        self.quality = max(self.quality * 0.8, quality)
        self.t_last = t
        self.returns += 1
        # A transient overrides a scrape: the sharper signal is the more informative one.
        if character is not SoundCharacter.TONE:
            self.character = character

    def rotate(self, dtheta: float, weight: float) -> None:
        """A fix rotates the frame, so bearings recorded in it move too."""
        self.bearing = G.wrap(self.bearing + dtheta * weight)
