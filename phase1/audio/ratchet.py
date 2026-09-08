"""The machinery's wind-up, as a state machine over the signature Belief can hear.

THE-MACHINERY.md: the Assayer ratchets a hammer up a mast and drops it. That is the sound
this drives -- a countable train of notches that accelerates and climbs the mast, a held
breath at the top, and the drop.

What the old version got backwards, measured over seed 7: the signature's strength ramps
across the nine-second warning and then HOLDS FLAT for the four lethal seconds, so the
pulse rate stopped accelerating at the exact instant the thing became dangerous. The ear
was given "it stopped getting faster", which is the opposite of an alarm. Worse, on a
distant cycle the whole wind-up came to +1.7 dB and +5 Hz over thirteen seconds -- below
the threshold at which a viewer notices that anything happened at all.

Both come from the same mistake: driving the sound off quality, which is
`(1 - distance/range) x strength` and therefore conflates how hard the machinery is
working with how far away it is. This class separates them the only way Belief allows --
as a RATIO. Distance barely moves across thirteen seconds, so the current quality divided
by the quality at the start of the cycle is very nearly strength divided by its floor.
Progress comes out of that, and a machine two chambers away now winds up as legibly as one
in the room, at its own honest distance and level.

The top of the wind-up is found the same way and also without a clock: the moment strength
stops rising is the moment the hazard becomes lethal, and a ramp that stops rising is
visible in its own slope. Nothing here reads truth, and nothing here knows the period, the
phase, or how long is left.

`observe` takes measurements and must only be fed a signature record it has not already
seen -- a stale sample fed repeatedly reads as a ramp that has stopped, which is exactly
the thing this looks for. `tick` runs the schedule and is safe to call every frame.
"""
from __future__ import annotations

from .. import geometry as G
from .. import tuning as T

NOTHING: str = ""
NOTCH: str = "notch"
HAMMER: str = "hammer"


class Ratchet:
    """One wind-up at a time. `tick` returns what to play, if anything."""

    def __init__(self) -> None:
        self.active: bool = False
        self.progress: float = 0.0
        self.notch: int = 0
        self.topped: bool = False
        self._t_start: float = 0.0
        self._t_seen: float = -1e9
        self._q_start: float = 0.0
        self._q_prev: float = 0.0
        self._slope: float = 0.0
        self._slope_peak: float = 0.0
        self._next_notch: float = 0.0
        self._hammer_at: float = 0.0
        self._struck: bool = False

    # ---- measurement ---------------------------------------------------------------------
    def observe(self, quality: float, t: float) -> None:
        """One fresh signature sample. Never call this twice for the same record."""
        if not self.active or t - self._t_seen > T.RATCHET_CYCLE_GAP_S:
            self._begin(quality, t)
            return
        dt = t - self._t_seen
        self._t_seen = t
        if dt > 0.0:
            raw = (quality - self._q_prev) / dt
            self._slope += 0.4 * (raw - self._slope)     # a light smoother, not a filter
            self._slope_peak = max(self._slope_peak, self._slope)
            self._q_prev = quality
        self.progress = G.clamp(
            (quality / self._q_start - 1.0) / max(T.SIGNATURE_RATIO_AT_LETHAL - 1.0, 1e-6),
            0.0, 1.0)
        if (not self.topped
                and t - self._t_start >= T.RATCHET_MIN_CYCLE_S
                and self._slope_peak > 0.0
                and self._slope < T.RATCHET_TOP_SLOPE_FRACTION * self._slope_peak):
            self.topped = True
            self._hammer_at = t + T.RATCHET_BREATH_S

    def _begin(self, quality: float, t: float) -> None:
        self.active = True
        self.topped = False
        self.progress = 0.0
        self.notch = 0
        self._t_start = t
        self._t_seen = t
        self._q_start = max(quality, 1e-4)
        self._q_prev = quality
        self._slope = 0.0
        self._slope_peak = 0.0
        self._next_notch = t
        self._struck = False

    # ---- schedule --------------------------------------------------------------------------
    @property
    def holding(self) -> bool:
        """The held breath: topped out, not yet struck.

        The mixer asks this so that nothing routine starts in the silence. Before it
        existed the silence was only a silence in the ratchet's own voice, and measured
        over seed 7's four cycles what was left sounding in front of the hammer was as
        loud as the hammer in two of them.
        """
        return self.active and self.topped and not self._struck

    def tick(self, t: float) -> str:
        if not self.active:
            return NOTHING
        if self.topped:
            if not self._struck and t >= self._hammer_at:
                self._struck = True
                return HAMMER
            if self._struck and t - self._t_seen > T.RATCHET_CYCLE_GAP_S:
                self.active = False
            return NOTHING                              # the held breath, then the ring-out
        if t - self._t_seen > T.RATCHET_CYCLE_GAP_S:
            self.active = False                         # it went quiet without topping out
            return NOTHING
        if t >= self._next_notch:
            self.notch += 1
            self._next_notch = t + self.interval()
            return NOTCH
        return NOTHING

    # ---- what a notch sounds like ------------------------------------------------------------
    def interval(self) -> float:
        """Geometric, not linear: a constant ratio between successive gaps is what the ear
        hears as accelerating, where a constant difference reads as merely fast."""
        return T.RATCHET_SLOW_S * (T.RATCHET_FAST_S / T.RATCHET_SLOW_S) ** self.progress

    def climb(self) -> float:
        """Frequency multiplier for this notch: the hammer going up the mast."""
        return 2.0 ** (T.RATCHET_CLIMB_SEMITONES * self.progress / 12.0)
