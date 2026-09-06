"""Turns Belief's streams into events for the timeline.

Everything here is derived from Belief, so it marks only what the agent itself could
know. Nothing ever says "you have been spoofed" -- it records that the estimate moved
thirty-four cells when it expected three, which is the same fact stated honestly, and
leaves the conclusion to the person watching.
"""
from __future__ import annotations

import math

from .. import tuning as T
from ..belief.belief import Belief
from ..sound_character import SoundCharacter
from .event_kind import EventKind
from .match_event import MatchEvent

SURPRISE_THRESHOLD: float = 2.5
BIG_JUMP_CELLS: float = 8.0
CONTACT_QUALITY_THRESHOLD: float = 0.45
ROUTINE_COOLDOWN: float = 12.0


class EventFeed:
    def __init__(self, belief: Belief) -> None:
        self.b: Belief = belief
        self.events: list[MatchEvent] = []
        self._n_fixes: int = 0
        self._n_log: int = 0
        self._n_heard: int = 0
        self._last_cargo: int = 0
        self._hazard_until: float = -1.0
        self._extract_announced: bool = False
        self._last_said: dict[str, float] = {}

    def _add(self, t: float, text: str, detail: str = "",
             kind: EventKind = EventKind.CONTACT, major: bool = False) -> None:
        if not major:
            last = self._last_said.get(text)
            if last is not None and t - last < ROUTINE_COOLDOWN:
                return
        self._last_said[text] = t
        self.events.append(MatchEvent(t, text, detail, kind, major))

    def update(self, t: float) -> None:
        b = self.b

        while self._n_fixes < len(b.fixes):
            record = b.fixes[self._n_fixes]
            self._n_fixes += 1
            if record.surprise >= SURPRISE_THRESHOLD and record.jump >= BIG_JUMP_CELLS:
                self._add(record.t, "the fix disagrees",
                          f"moved it {record.jump:.0f} cells; it expected "
                          f"{record.jump / max(record.surprise, 1e-6):.0f}",
                          EventKind.DISAGREE, major=True)
            elif record.jump >= 2.0:
                self._add(record.t, "position fix", f"corrected {record.jump:.0f} cells",
                          EventKind.FIX)

        while self._n_heard < len(b.heard):
            sound = b.heard[self._n_heard]
            self._n_heard += 1
            if sound.quality < CONTACT_QUALITY_THRESHOLD:
                continue
            compass = f"bearing {int(math.degrees(sound.bearing)) % 360:03d}"
            if sound.character is SoundCharacter.CRASH:
                self._add(sound.t, "something broke", compass, EventKind.TROUBLE, major=True)
            elif sound.character is SoundCharacter.PING:
                self._add(sound.t, "another machine pinged", compass, EventKind.CONTACT)
            elif sound.character is SoundCharacter.TONE:
                self._add(sound.t, "something moving nearby", compass, EventKind.CONTACT)

        sig = b.signature
        if sig is not None and t - sig.t < 1.0 and t > self._hazard_until:
            self._hazard_until = t + 25.0
            self._add(t, "machinery spinning up",
                      f"bearing {int(math.degrees(sig.bearing)) % 360:03d}",
                      EventKind.HAZARD, major=True)

        if b.cargo != self._last_cargo:
            self._last_cargo = b.cargo
            self._add(t, "cargo aboard", f"{b.cargo} of {T.CARGO_CAPACITY}",
                      EventKind.CARGO, major=True)

        if not self._extract_announced and t >= T.EXTRACT_WINDOW_OPENS:
            self._extract_announced = True
            self._add(t, "extraction window open", "90 seconds to be back",
                      EventKind.PHASE, major=True)

        while self._n_log < len(b.log):
            log_t, text = b.log[self._n_log]
            self._n_log += 1
            self._from_log(log_t, text)

    def _from_log(self, t: float, text: str) -> None:
        if text.startswith("RECALL received"):
            self._add(t, "recall received", "running for the shaft", EventKind.COMMAND, True)
        elif text.startswith("uncertainty"):
            self._add(t, "too lost to continue", "turning back on its own", EventKind.TROUBLE, True)
        elif text.startswith("nothing loaded"):
            self._add(t, "nothing here", "the deposit is not where it thought", EventKind.TROUBLE, True)
        elif text.startswith("at the shaft, but nothing"):
            self._add(t, "the shaft is not here", "starting to search", EventKind.TROUBLE, True)
        elif text.startswith("shaft acquired"):
            self._add(t, "found the shaft", "", EventKind.PHASE, True)
        elif text.startswith("cannot reach"):
            self._add(t, "cannot get through", "", EventKind.TROUBLE)
        elif ", loading" in text:
            self._add(t, "loading", "", EventKind.CARGO)

    def latest(self, t: float, window: float = 6.0) -> MatchEvent | None:
        """The most recent event, for the one line printed beside the playhead."""
        for event in reversed(self.events):
            if t - event.t <= window:
                return event
        return None
