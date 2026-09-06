"""A beacon as it truly is. What it *claims* is a separate thing, held in Belief."""
from __future__ import annotations

from .. import tuning as T


class Beacon:
    """An acoustic transponder at a true position.

    Nothing here marks a beacon as honest or as a lie. A spoof is simply a beacon
    whose true position no longer matches the position the victim recorded for it,
    and the sensor layer cannot tell the difference. That is the point.
    """

    def __init__(self, beacon_id: str, x: float, y: float, owner: str,
                 truth_anchor: bool = False) -> None:
        self.id: str = beacon_id
        self.x: float = float(x)
        self.y: float = float(y)
        self.owner: str = owner
        self.truth_anchor: bool = truth_anchor
        self.range: float = T.SHAFT_BEACON_RANGE if truth_anchor else T.BEACON_RANGE
        # 0 means the transponder answers once as you enter its range. A spoof
        # broadcasts on a period instead, because it was placed to be heard.
        self.reassert_period: float = 0.0

    def move_to(self, x: float, y: float) -> None:
        """Relocate the transponder. Used by the scripted spoof: the id and the
        owner stay the same, so the victim keeps trusting it."""
        self.x = float(x)
        self.y = float(y)

    def __repr__(self) -> str:
        anchor = " anchor" if self.truth_anchor else ""
        return f"<Beacon {self.id} ({self.x:.1f},{self.y:.1f}) {self.owner}{anchor}>"
