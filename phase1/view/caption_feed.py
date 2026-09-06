"""Turns Belief's event streams into plain-English captions.

Everything here is derived from Belief, so it tells the viewer only what the agent
itself could know. It never says "you have been spoofed" -- it says the estimate
jumped thirty-two cells when the agent expected four, which is the same fact stated
honestly, and leaves the conclusion to the person watching.
"""
from __future__ import annotations

import math

from .. import tuning as T
from ..belief.belief import Belief
from ..sound_character import SoundCharacter
from .caption import Caption

# A fix this many times larger than the ellipse promised is worth interrupting for.
SURPRISE_THRESHOLD: float = 2.5
BIG_JUMP_CELLS: float = 8.0
CONTACT_QUALITY_THRESHOLD: float = 0.45
# Seconds before the same ordinary caption may be said again.
ROUTINE_COOLDOWN: float = 9.0


class CaptionFeed:
    def __init__(self, belief: Belief) -> None:
        self.b: Belief = belief
        self.captions: list[Caption] = []
        self._n_fixes: int = 0
        self._n_log: int = 0
        self._n_heard: int = 0
        self._last_cargo: int = 0
        self._signature_until: float = -1.0
        self._extract_announced: bool = False
        self._last_said: dict[str, float] = {}

    def _add(self, t: float, text: str, detail: str = "", weight: float = 1.0) -> None:
        # Routine chatter repeats -- a rival pings every eight seconds all match. Without
        # a cooldown it floods the feed and pushes the moments that matter off screen.
        if weight < 2.0:
            last = self._last_said.get(text)
            if last is not None and t - last < ROUTINE_COOLDOWN:
                return
        self._last_said[text] = t
        self.captions.append(Caption(t, text, detail, weight))
        if len(self.captions) > 40:
            del self.captions[:-40]

    def update(self, t: float) -> None:
        b = self.b

        # Fixes: the size of the correction relative to what the estimator promised is
        # the only thing separating an honest beacon from one that has been moved.
        while self._n_fixes < len(b.fixes):
            record = b.fixes[self._n_fixes]
            self._n_fixes += 1
            if record.surprise >= SURPRISE_THRESHOLD and record.jump >= BIG_JUMP_CELLS:
                self._add(record.t, "POSITION FIX DISAGREES",
                          f"estimate moved {record.jump:.0f} cells - it expected "
                          f"under {record.jump / max(record.surprise, 1e-6):.0f}",
                          weight=2.0)
            elif record.jump >= 3.0:
                self._add(record.t, "position fix",
                          f"estimate corrected {record.jump:.0f} cells")

        while self._n_heard < len(b.heard):
            sound = b.heard[self._n_heard]
            self._n_heard += 1
            if sound.quality < CONTACT_QUALITY_THRESHOLD:
                continue
            compass = f"bearing {int(math.degrees(sound.bearing)) % 360:03d}"
            if sound.character is SoundCharacter.CRASH:
                self._add(sound.t, "SOMETHING BROKE", compass, weight=2.0)
            elif sound.character is SoundCharacter.PING:
                self._add(sound.t, "someone else is pinging", compass)
            elif sound.character is SoundCharacter.TONE:
                self._add(sound.t, "something is moving", compass)

        sig = b.signature
        if sig is not None and t - sig.t < 1.0 and t > self._signature_until:
            self._signature_until = t + 20.0
            self._add(t, "MACHINERY SPINNING UP",
                      f"bearing {int(math.degrees(sig.bearing)) % 360:03d}", weight=2.0)

        if b.cargo != self._last_cargo:
            self._last_cargo = b.cargo
            self._add(t, "CARGO ABOARD", f"{b.cargo} of {T.CARGO_CAPACITY}")

        if not self._extract_announced and t >= T.EXTRACT_WINDOW_OPENS:
            self._extract_announced = True
            self._add(t, "EXTRACTION WINDOW OPEN",
                      "anything not back through the shaft is lost", weight=2.0)

        while self._n_log < len(b.log):
            log_t, text = b.log[self._n_log]
            self._n_log += 1
            self._from_log(log_t, text)

    def _from_log(self, t: float, text: str) -> None:
        if text.startswith("RECALL received"):
            self._add(t, "RECALL RECEIVED", "abandoning the survey, running for the shaft", 2.0)
        elif text.startswith("uncertainty"):
            self._add(t, "TOO UNCERTAIN TO CONTINUE", "turning for home on its own", 2.0)
        elif text.startswith("nothing loaded"):
            self._add(t, "NOTHING HERE", "the deposit is not where it thinks it is", 2.0)
        elif text.startswith("at the shaft, but nothing is answering"):
            self._add(t, "THE SHAFT IS NOT HERE", "searching for it", 2.0)
        elif text.startswith("shaft acquired"):
            self._add(t, "SHAFT FOUND", "", 2.0)
        elif text.startswith("cannot reach"):
            self._add(t, "cannot get there", text.split(";")[0].replace("cannot reach ", "blocked from "))
        elif text.startswith("at ") and ", loading" in text:
            self._add(t, "LOADING", "believes it has arrived at the deposit")
        elif text.startswith("giving up"):
            self._add(t, "GIVING UP ON IT", "moving on without the cargo")
        elif text.startswith("going home") or text.startswith("pushing on"):
            self._add(t, text.split(":")[-1].strip(), "")

    def active(self, t: float, hold: float, fade: float, limit: int = 3) -> list[tuple[Caption, float]]:
        """Live captions, the ones that matter first.

        Sorting by recency alone let two routine ping notices push
        "POSITION FIX DISAGREES" off the screen in the same second it fired -- the one
        line the whole test is built around, lost to chatter.
        """
        live = [(c, c.alpha(t, hold, fade)) for c in self.captions]
        live = [(c, a) for c, a in live if a > 0.0]
        live.sort(key=lambda pair: (pair[0].weight, pair[0].t), reverse=True)
        chosen = live[:limit]
        chosen.sort(key=lambda pair: pair[0].t, reverse=True)
        return chosen
