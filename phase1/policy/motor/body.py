"""The one body every program drives: its belief, its loadout, its shaft, its jam clock."""
from __future__ import annotations

from ...belief.belief import Belief
from ..loadout import Loadout
from .jam_clock import JamClock


class Body:
    """What a program is handed. Programs come and go with the tree's decisions; the
    body and the things that are true of it between programs -- whether it has moved
    lately -- do not."""

    def __init__(self, belief: Belief, loadout: Loadout, shaft_beacon_id: str) -> None:
        self.belief: Belief = belief
        self.loadout: Loadout = loadout
        self.shaft_beacon_id: str = shaft_beacon_id
        self.jam: JamClock = JamClock(belief)
