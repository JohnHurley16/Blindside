"""Where a sound is, expressed as everything the ear uses to tell where a sound is.

This is the whole distance argument in one class. The sensor already hands Belief a
quality, and quality is a distance proxy -- `q = 1 - path_length / range` -- so one number
drives four cues at once:

  level        a far thing is quiet                       (the only cue the old mixer had)
  brightness   a far thing has had its top eaten by rock
  attack       a far thing has had its transient smeared
  the room     a far thing is mostly reverberation, a near thing is mostly itself

Any one of them alone reads as "the same event, quieter". Together they read as distance,
because together they are what distance actually does to a sound. The fourth is the one
that carries most: close to a source you hear the source, far from it you hear the cave,
because the reverberant field barely falls off while the direct sound falls off hard.

WHAT THIS DOES NOT DO IS FRONT AND BACK. Pan is the screen-x component of the bearing;
stereo has one axis; cos() folds north onto south exactly, and nothing here separates
them. There used to be a screen-y tilt on level and brightness pretending to. It measured
1.74 dB against the 20 dB distance owns on the same channel, so a north contact at q=0.70
was matched within 0.1 dB by a south contact at q=0.60 -- it could not be heard as
direction and it could be heard as distance. It is gone, and distance is cleaner without
it. Front/back needs a channel of its own or it does not exist; it does not exist.

Nothing here knows what made the sound. It is handed a bearing and a quality out of
Belief, and both of those can be wrong.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from .. import geometry as G
from .. import tuning as T
from .reflection import Reflection


@dataclass(frozen=True, slots=True)
class Placement:
    pan: float
    gain: float                            # multiplies a recipe's nominal amplitude
    brightness: float                      # 0 = fundamental only, 1 = full partial stack
    attack: float                          # seconds
    reflections: tuple[Reflection, ...]

    @staticmethod
    def pan_for(bearing: float, camera_azimuth_deg: float) -> float:
        """Screen-relative pan, so what looks right sounds right as the camera orbits.

        This is the screen-x component of the bearing. Stereo has one axis, so screen-y is
        not in it and never can be -- north and south fold onto the same pan, and nothing
        else here separates them either.
        """
        return math.cos(bearing + math.radians(camera_azimuth_deg))

    @classmethod
    def for_sound(cls, bearing: float, quality: float, camera_azimuth_deg: float,
                  max_reflections: int = 3, gain_floor: float = 0.0) -> Placement:
        """`gain_floor` is for the two sounds that must arrive whatever the distance --
        the hammer and a death. It compresses the level cue for those and leaves the other
        three cues untouched; see HAZARD_GAIN_FLOOR."""
        q = G.clamp(quality, 0.0, 1.0)
        far = 1.0 - q
        pan = cls.pan_for(bearing, camera_azimuth_deg)

        gain = T.AUDIO_FAR_GAIN + (T.AUDIO_NEAR_GAIN - T.AUDIO_FAR_GAIN) * q ** T.AUDIO_GAIN_CURVE
        gain = gain_floor + (1.0 - gain_floor) * gain
        brightness = G.clamp(q ** T.AUDIO_BRIGHT_CURVE, 0.0, 1.0)
        attack = T.AUDIO_ATTACK_NEAR_S + (T.AUDIO_ATTACK_FAR_S - T.AUDIO_ATTACK_NEAR_S) * far

        frac = T.AUDIO_REFLECT_NEAR_FRAC + (T.AUDIO_REFLECT_FAR_FRAC - T.AUDIO_REFLECT_NEAR_FRAC) * far
        first = T.AUDIO_REFLECT_DELAY_NEAR_S + (T.AUDIO_REFLECT_DELAY_FAR_S - T.AUDIO_REFLECT_DELAY_NEAR_S) * far
        spread = T.AUDIO_REFLECT_SPREAD * (0.4 + 0.6 * far)
        sides = (1.0, -0.85, 0.5)          # the room answers from alternating sides
        out: list[Reflection] = []
        for i in range(min(max_reflections, len(T.AUDIO_REFLECT_SPACING))):
            level = frac * T.AUDIO_REFLECT_LEVELS[i]
            if level < T.AUDIO_REFLECT_FLOOR:
                break                       # so near sounds get one arrival and far ones three
            out.append(Reflection(
                delay=first * T.AUDIO_REFLECT_SPACING[i],
                gain=level,
                pan=G.clamp(pan * 0.55 + spread * sides[i], -1.0, 1.0),
                brightness=brightness * T.AUDIO_REFLECT_DULLING[i]))
        return cls(pan=pan, gain=gain, brightness=brightness, attack=attack,
                   reflections=tuple(out))
