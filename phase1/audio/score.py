"""The trailer's score, as a state machine over time.

Same shape as `ratchet.py`, and for the same reason: a thing that has to be right at a
particular second is easier to trust when it is a schedule you can print than when it is a
sequence of calls buried in a render loop. `Ratchet.tick(t)` returns what to play; `Score`
returns the same kind of answer -- a tuple of `ScoreEvent`, which is data -- and something
else decides what a struck bar is made of.

WHAT IT IS FOR. `TRAILER.md` section 5: the score is the sound of having control. It plays
on the surface, through Acts I and II, while the player's hands are on the machine. It is
the one thing that survives the descent at 0:50 -- every diegetic layer falls away and the
score narrows and is left alone in the dark. At 1:01, over black and under the card, it
stops. It never comes back.

SO THE TWO THINGS THIS CLASS HAS TO GET EXACTLY RIGHT are the events and the stop, and they
are not the same problem.

The events are a schedule and a schedule is easy. The STOP is not a schedule -- it is the
absence of one, and an absence cannot be built out of not queueing anything, because the
score is made of long metal that is still ringing. Sixteen seconds of struck bar are already
in flight at 1:01 and something has to take them away. `Mixer.duck(0.0, ramp)` is that
something, and it is already in the engine because a crash already does it: `CRASH_DUCK` and
`RATCHET_BREATH_DUCK` pull everything sounding down and hold it there, which is the
difference `SOUND-DESIGN.md` section 6.3 names between *quiet* and *gone quiet*. **A silence
that arrives is an event.** The trailer's largest structural moment is therefore the game's
own mixer running, not a fader in an editor, which is what section 8.1 asked for.

The ramp on that duck is eight milliseconds. That is not a fade -- a fade is a decision the
ear can follow, and 8 ms is four cycles of the lowest note in the piece. It is there so the
cut does not click, and `spikes/score/NOTES.md` measures what it actually does.

NOTHING HERE READS A CLOCK. `tick` is handed the block it is being asked about, exactly as
`Recorder` hands the mixer one frame's worth at a time, so the offline render and any future
live one see the same schedule.
"""
from __future__ import annotations

import math

from .score_event import ScoreEvent
from .score_spec import Line, ScoreSpec, Section

_PARTIAL_FLOOR: float = 0.02      # Voice drops a partial below this, so it is not "occupied"


def _hash(text: str, index: int, stream: int) -> int:
    """FNV-1a over the line's id, mixed with the strike index. Deterministic everywhere.

    Not `hash()`: Python randomises string hashing per process, so a score rendered twice
    would be two different performances and a bug report would not reproduce. Not `random`
    either, because a module-level generator is shared state and the schedule is walked
    block by block. A pure function of (line id, strike, stream) has neither problem.
    """
    h = 2166136261 ^ ((stream * 0x9E3779B1) & 0xFFFFFFFF)
    for ch in text:
        h = ((h ^ ord(ch)) * 16777619) & 0xFFFFFFFF
    h = (h ^ ((index * 0x85EBCA6B) & 0xFFFFFFFF)) & 0xFFFFFFFF
    h = ((h ^ (h >> 15)) * 0x2545F491) & 0xFFFFFFFF
    return (h ^ (h >> 13)) & 0xFFFFFFFF


def _wobble(text: str, index: int, stream: int) -> float:
    """-1..1, with a slow term under a fast one.

    White jitter is not rubato -- it is a badly quantised machine. A player pushes and drags
    across a phrase and varies the individual note inside that, so this is two thirds a
    value that only changes every third strike and one third a value that changes every
    strike. The result drifts rather than rattling.
    """
    fast = _hash(text, index, stream) / 2147483647.5 - 1.0
    slow = _hash(text, index // 3, stream + 7) / 2147483647.5 - 1.0
    return 0.34 * fast + 0.66 * slow


class Score:
    """A schedule over a `ScoreSpec`. Holds no buffers and builds no sound."""

    def __init__(self, spec: ScoreSpec) -> None:
        self.spec: ScoreSpec = spec
        self.stopped: bool = False
        self.events: int = 0

    # ---- the schedule ---------------------------------------------------------------------
    def due(self, t0: float, t1: float) -> tuple[ScoreEvent, ...]:
        """Everything that strikes in [t0, t1). Empty once the score has stopped.

        Half-open on purpose: a block asks for its own span and never for a neighbour's, so
        no event is emitted twice and none is dropped at a boundary.
        """
        if self.stopped or t0 >= self.spec.stop_s:
            return ()
        out: list[ScoreEvent] = []
        for section in self.spec.sections:
            if section.to_s <= t0 or section.from_s >= t1:
                continue
            for line in section.lines:
                out.extend(self._line_events(section, line, t0, t1))
        out.sort(key=lambda e: (e.t, e.line))
        self.events += len(out)
        return tuple(out)

    def stops_in(self, t0: float, t1: float) -> bool:
        """True for the one block the cut lands in. Latches, so it fires once."""
        if self.stopped or not math.isfinite(self.spec.stop_s):
            return False
        if t0 <= self.spec.stop_s < t1:
            self.stopped = True
            return True
        return False

    def _line_events(self, section: Section, line: Line,
                     t0: float, t1: float) -> list[ScoreEvent]:
        first = section.from_s + line.at_s
        last = min(section.to_s, section.from_s + line.until_s, self.spec.stop_s)
        out: list[ScoreEvent] = []
        if line.every_s <= 0.0:
            strikes = [(0, first)] if first < last else []
        else:
            # The window is widened by the humanising amount at BOTH ends and every
            # candidate is then tested against its own displaced time, so a strike that
            # drifts across a block boundary is emitted exactly once and by the block it
            # actually lands in. Widening only one end would drop it or double it.
            slack = line.humanize_s
            k0 = max(0, math.ceil((t0 - slack - first) / line.every_s))
            k1 = math.floor((t1 + slack - first) / line.every_s)
            strikes = []
            for k in range(k0, k1 + 1):
                t = first + k * line.every_s
                if slack > 0.0:
                    # Every strike moves, including the first one in a section. A gait does
                    # not reset its feet at a bar line, and the tread here is one gait spread
                    # across ten sections because the chord under it changes: exempting each
                    # section's first strike would have put a third of the piece's steps
                    # back on the grid, which is the defect this exists to remove.
                    t += slack * _wobble(line.id, k, 1)
                if t >= last:
                    break
                strikes.append((k, t))
        for index, t in strikes:
            if not (t0 <= t < t1) or t >= last:
                continue
            out.append(self._event(section, line, index, t))
        return out

    def _event(self, section: Section, line: Line, index: int, t: float) -> ScoreEvent:
        """One strike. Level and room are interpolated across the section, which is the
        score's only automation and the reason there is no automation code: a crescendo is
        successive strikes at rising amplitude, and a swell inside one strike is the
        envelope's own attack, which `Envelope.curve` already ramps linearly from zero."""
        p = min(max((t - section.from_s) / section.span, 0.0), 1.0)
        amp = line.amp + (line.amp_to - line.amp) * p
        if line.accent_every > 0 and index % line.accent_every == 0:
            amp *= line.accent_amp
        if line.touch > 0.0:
            amp *= max(0.05, 1.0 + line.touch * _wobble(line.id, index, 2))
        timbre = self.spec.timbres[line.timbre]
        return ScoreEvent(
            t=t, line=line.id, tonal=timbre.tonal, ratios=timbre.ratios, tilt=timbre.tilt,
            f0=line.pitch, f1=line.glide_to, duration=line.duration_s,
            attack=line.attack_s, decay=line.decay_s, amplitude=amp, pan=line.pan,
            quality=line.quality + (line.quality_to - line.quality) * p,
            max_reflections=line.max_reflections, noise_lowpass=timbre.noise_lowpass)

    # ---- what it can be asked about without rendering it ------------------------------------
    def plan(self) -> tuple[ScoreEvent, ...]:
        """Every event in the whole piece, in time order. A fresh `Score` is used so calling
        this does not consume the schedule the render is about to walk."""
        clone = Score(self.spec)
        out: list[ScoreEvent] = []
        step = 0.25
        t = 0.0
        while t < self.spec.length_s:
            out.extend(clone.due(t, min(t + step, self.spec.length_s)))
            t += step
        return tuple(out)

    def band_report(self, low: float = 400.0, high: float = 3000.0) -> list[str]:
        """Which partials of which lines land inside the reserved band, structurally.

        `tuning.py` keeps 400 Hz to 3 kHz for anything that has to be identified by ear --
        the heard ping at 760, the own ping sweeping to 2100, the ratchet's ring at 940 to
        2103 -- and section 8.1 rule 3 puts the score's business below and above it. The
        render is measured with an FFT, but a partial is `ratio * f0` and that is knowable
        from the document alone, which means a wrong note can be caught before it is heard.

        A partial `Voice` would drop as inaudible (gain below `_PARTIAL_FLOOR`) does not
        count as occupying anything, because it is never synthesised.
        """
        bad: list[str] = []
        for section in self.spec.sections:
            for line in section.lines:
                timbre = self.spec.timbres[line.timbre]
                if not timbre.tonal:
                    bad.extend(self._noise_band(section, line, timbre.noise_lowpass, low))
                    continue
                norm = 1.0 / sum(1.0 if i == 0 else 1.0 / (1.0 + timbre.tilt * i)
                                 for i in range(len(timbre.ratios)))
                bright = max(line.quality, line.quality_to) ** 1.25   # AUDIO_BRIGHT_CURVE
                for i, ratio in enumerate(timbre.ratios):
                    gain = norm if i == 0 else norm * bright / (1.0 + timbre.tilt * i)
                    if gain < _PARTIAL_FLOOR:
                        continue
                    for hz in {ratio * line.pitch, ratio * line.glide_to}:
                        if low <= hz <= high:
                            bad.append(f"{line.id}: partial {i} ({ratio}x) at {hz:.1f} Hz "
                                       f"gain {gain:.3f} is inside {low:.0f}-{high:.0f}")
        return bad

    @staticmethod
    def _noise_band(section: Section, line: Line, width: int, low: float) -> list[str]:
        """A band-limited stroke has no partials, it has a corner. `Voice._noise` moving-
        averages `width` samples, which cuts at about 0.44 * rate / width."""
        corner = 0.44 * 48000.0 / max(width, 1)
        if corner > low:
            return [f"{line.id}: noise lowpass width {width} corners at {corner:.0f} Hz, "
                    f"above {low:.0f}"]
        return []
