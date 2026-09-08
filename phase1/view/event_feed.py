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
from .contact_watch import ContactWatch
from .event_kind import EventKind
from .match_event import MatchEvent

SURPRISE_THRESHOLD: float = 2.5
BIG_JUMP_CELLS: float = 8.0
CONTACT_QUALITY_THRESHOLD: float = 0.45

# What to say about a contact, by what kind of news it is. Distinct sentences per
# character, so that the feed reads as separate things being followed rather than one
# string repeating. There is no acceptance criterion for this anywhere in docs/ -- the
# measured outcome is that the contact lines fell from 61% of the feed to 37%, and that
# the largest single line is 20-42%, most of it "position fix". Written down rather than
# dressed up as a test that was never agreed and that this build would fail.
CONTACT_LINES: dict[SoundCharacter, dict[str, str]] = {
    SoundCharacter.PING: {
        "new": "a machine is pinging out there",
        "moved": "the pinging has swung round",
        "closer": "the pinging is closer",
    },
    SoundCharacter.TONE: {
        "new": "something is moving out there",
        "moved": "it has gone round",
        "closer": "it is closer than it was",
    },
}


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
        self._last_said: dict[tuple[str, str], float] = {}
        self._watch: dict[SoundCharacter, ContactWatch] = {}

    def _add(self, t: float, text: str, detail: str = "",
             kind: EventKind = EventKind.CONTACT, major: bool = False) -> None:
        """Keyed on the sentence AND its detail: the same words about a different
        bearing are a different fact, and were being thrown away as a repeat."""
        key = (text, detail)
        if not major:
            last = self._last_said.get(key)
            if last is not None and t - last < T.FEED_REPEAT_COOLDOWN:
                return
        self._last_said[key] = t
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
            elif record.jump >= T.FEED_FIX_CELLS:
                self._add(record.t, "position fix", f"corrected {record.jump:.0f} cells",
                          EventKind.FIX)

        while self._n_heard < len(b.heard):
            sound = b.heard[self._n_heard]
            self._n_heard += 1
            if sound.quality < CONTACT_QUALITY_THRESHOLD:
                continue
            if sound.character is SoundCharacter.CRASH:
                self._add(sound.t, "something broke", _compass(sound.bearing),
                          EventKind.TROUBLE, major=True)
                continue
            self._contact(sound.character, sound.bearing, sound.quality, sound.t)

        # DECIDED, and left as it is: this line IS a clock, and it is supposed to be.
        # The contact lines were made to speak only on news because a rival's ping
        # cooldown is an implementation detail that means nothing to a viewer -- a
        # sentence arriving every 16.0 s taught them to stop reading. The machinery is
        # the opposite case. THE-MACHINERY.md section 3 fixes the firings at 0:41,
        # 1:56, 3:11, 4:26, 5:41 and 6:56, and the glossary entry it proposes calls the
        # system "deterministic -- a fixed cycle ... a behavior a player can learn".
        # The repeat is the mechanic. Suppressing it until something "changed" would
        # delete exactly the evidence a player needs to work the period out, and the
        # thing that would then be missing is the one hazard in the match you can beat
        # by counting.
        #
        # And measured, the line did not get louder -- everything else got quieter. It
        # prints exactly 4 times a match in both builds, before and after the contact
        # work, on all eight seeds with no recall. What changed is its share of the
        # feed, 7-12% to 11-21%, because the two contact sentences that used to be
        # 45% of it stopped repeating. It is now the top line of one seed in eight
        # (21%) with no recall and four in eight (12-19%) at Recall 3:00, and that is
        # still inside the quarter-of-the-feed test the contact work set itself. If
        # the gate says four warnings is too many, the lever is HAZARD_REPEAT_S, not a
        # news test.
        sig = b.signature
        if sig is not None and t - sig.t < 1.0 and t > self._hazard_until:
            self._hazard_until = t + T.HAZARD_REPEAT_S
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
        elif text.startswith("cannot get to the shaft"):
            self._add(t, "it cannot get home", "searching from where it stands",
                      EventKind.TROUBLE, True)
        elif text.startswith("shaft acquired"):
            self._add(t, "found the shaft", "", EventKind.PHASE, True)
        elif text.startswith("cannot reach"):
            where = text[len("cannot reach "):].split(";")[0]
            self._add(t, "cannot get through", f"giving up on {where}", EventKind.TROUBLE)
        elif ", loading" in text:
            self._add(t, "loading", "", EventKind.CARGO)

    def _contact(self, character: SoundCharacter, bearing: float, quality: float,
                 t: float) -> None:
        """Print a contact only when something about it has changed.

        Three questions, in order: is this the first I have heard of it, has it swung
        round since I last spoke, is it louder than it was. A return that answers none
        of them is a repeat carrying no information, and the right length for it is
        nothing -- which is what lets a genuinely quiet stretch be quiet.
        """
        lines = CONTACT_LINES.get(character)
        if lines is None:
            return
        watch = self._watch.get(character)
        if watch is None:
            watch = ContactWatch(bearing, quality, t)
            self._watch[character] = watch
            news = "new"
        else:
            news = watch.hear(bearing, quality, t)
        if news is None:
            return
        detail = _compass(watch.bearing)
        if news == "moved":
            detail = f"{_compass(watch.said_bearing)} to {_compass(watch.bearing)}"
        # First contact and a closing one are worth an interruption; a contact merely
        # wandering across the arc is not.
        self._add(t, lines[news], detail, EventKind.CONTACT, major=news != "moved")
        watch.said(t)

    def latest(self, t: float, window: float = 6.0) -> MatchEvent | None:
        """The most recent event, for the one line printed beside the playhead."""
        for event in reversed(self.events):
            if t - event.t <= window:
                return event
        return None


def _compass(bearing: float) -> str:
    return f"bearing {int(math.degrees(bearing)) % 360:03d}"
