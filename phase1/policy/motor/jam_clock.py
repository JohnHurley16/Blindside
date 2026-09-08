"""Not moving, which is not the same as not arriving."""
from __future__ import annotations

from ... import tuning as T
from ...belief.belief import Belief


class JamClock:
    """When did the body last cover ground? Odometry alone; Belief knows this.

    One per body, not one per route. Measured: a machine pressed against rock reports
    zero forward motion, so belief freezes exactly as hard as truth and the only signal
    is the odometry integral standing still. The longest unbroken pin in a match was
    59.3 s, and the waypoint tracker cannot see it: "no closer to the waypoint" is also
    what a long detour looks like.

    Shared by every program the tree runs, because a clock that restarted with each
    program restarted the 0.5-cell quantisation of `note_motion` too, and against the
    same wall its jam fired three ticks before the old policy's did -- a 0.17-cell
    offset that never closed (seed 2, rival inert, 1:34.45).
    """

    def __init__(self, belief: Belief) -> None:
        self.b: Belief = belief
        self.since: float = 0.0
        self.mark: float = 0.0

    def note_motion(self, t: float) -> None:
        """Mark the last time it covered ground. Called once a tick, before the program."""
        if self.b.dist_total - self.mark > T.JAM_MOVE_CELLS:
            self.mark = self.b.dist_total
            self.since = t

    def still(self, t: float) -> None:
        """Standing still to load, to freeze or to dwell is not a jam."""
        self.since = t

    def jammed(self, t: float) -> bool:
        return t - self.since > T.JAM_SECONDS

    def reset(self, t: float) -> None:
        self.since = t
        self.mark = self.b.dist_total
