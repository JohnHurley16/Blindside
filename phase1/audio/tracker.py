"""One transmission, one gesture.

The measured failure this class exists to fix: a single rival ping stays audible for
SONAR_AUDIBLE_S and the rig samples it every tenth tick, so ONE event arrived at the ear
as six identical beeps, 0.5 s apart, on an 8 s cooldown. Eight minutes of that is a
metronome, and a listener hearing six identical beeps has no reason to believe that is one
event and every reason to believe the world is full of beeping.

So arrivals on a direction that has already spoken inside the merge window are absorbed
rather than sounded -- unless they arrive from a clearly different direction, which is a
genuinely separate arrival and must survive: that is what the scripted echo is.

The bearing gate is wide because it has to be. Bearing noise runs to 22 degrees of sigma
at range, so two samples of the same burst can be forty degrees apart, and a tight gate
would split one transmission back into several.
"""
from __future__ import annotations

import math

from .. import geometry as G
from .. import tuning as T
from .acoustic_track import AcousticTrack


class Tracker:
    """Bearing clusters for the mixer. Holds no identity and resolves nothing."""

    def __init__(self) -> None:
        self.tracks: list[AcousticTrack] = []
        self._last_gesture_bearing: float = 0.0

    def observe(self, bearing: float, quality: float, t: float) -> AcousticTrack:
        self.tracks = [k for k in self.tracks if t - k.t_last < T.AUDIO_TRACK_MEMORY_S]
        gate = math.radians(T.AUDIO_TRACK_MERGE_DEG)
        for track in self.tracks:
            if G.angle_between(track.bearing, bearing) < gate:
                # follow, the way Contact.absorb does: a track that cannot move loses the
                # rival exactly when it is close and its bearing is swinging fastest
                track.bearing = G.wrap(track.bearing + 0.5 * G.wrap(bearing - track.bearing))
                track.quality = max(track.quality * 0.85, quality)
                track.t_last = t
                return track
        track = AcousticTrack(bearing=bearing, quality=quality, t_last=t,
                              t_last_gesture=-1e9, quality_last_gesture=0.0)
        self.tracks.append(track)
        return track

    def should_sound(self, track: AcousticTrack, bearing: float, t: float) -> bool:
        if t - track.t_last_gesture >= T.AUDIO_PING_MERGE_S:
            return True
        return (G.angle_between(bearing, self._last_gesture_bearing)
                >= math.radians(T.AUDIO_PING_SEPARATE_DEG))

    def note_gesture(self, track: AcousticTrack, bearing: float, t: float) -> None:
        track.sounded(t)
        self._last_gesture_bearing = bearing
