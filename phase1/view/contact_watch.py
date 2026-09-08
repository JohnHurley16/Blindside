"""What the feed last said about one kind of sound, so it can tell news from a repeat.

The old feed keyed a twelve-second cooldown on the sentence alone. The bearing lived
in the detail and was not part of the key, so "the same standing contact, still there"
and "a new contact ninety degrees away" were the same event to it, and it admitted
whichever arrived first after the clock ran down. Measured on seed 7: 481 sounds passed
the quality gate, 447 were dropped by that clock, and what came out was one sentence
every 16.0 s to a tenth of a second for eight minutes.

This holds the state that lets the feed answer a different question -- has anything
changed since I last spoke -- which is the only question worth printing an answer to.
"""
from __future__ import annotations

import math

from .. import geometry as G
from .. import tuning as T


class ContactWatch:
    """One heard character, smoothed, plus what was last said about it."""

    def __init__(self, bearing: float, quality: float, t: float) -> None:
        self.bearing: float = bearing        # smoothed world bearing, belief frame
        self.quality: float = quality
        self.t_last: float = t
        self.said_bearing: float = bearing
        self.said_quality: float = quality
        self.said_t: float = t

    def hear(self, bearing: float, quality: float, t: float) -> str | None:
        """Fold one more return in and say what, if anything, is news.

        "new" | "moved" | "closer" | None. Bearings are smoothed the same way
        Contact.absorb smooths them, because a return at the quality gate carries
        about fourteen degrees of noise and an unsmoothed one would announce that a
        motionless contact had moved several times a match.
        """
        gone = t - self.t_last > T.FEED_CONTACT_FORGET_S
        self.t_last = t
        if gone:
            self.bearing, self.quality = bearing, quality
            return "new"
        self.bearing = G.wrap(self.bearing
                              + T.FEED_CONTACT_SMOOTH * G.wrap(bearing - self.bearing))
        self.quality += T.FEED_CONTACT_SMOOTH * (quality - self.quality)
        if t - self.said_t < T.FEED_CONTACT_HOLD_S:
            return None
        if G.angle_between(self.bearing, self.said_bearing) > math.radians(T.FEED_CONTACT_TURN_DEG):
            return "moved"
        if self.quality - self.said_quality > T.FEED_CLOSER_QUALITY:
            return "closer"
        return None

    def said(self, t: float) -> None:
        """Commit: from here on, news means changed from this."""
        self.said_bearing = self.bearing
        self.said_quality = self.quality
        self.said_t = t
