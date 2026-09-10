"""Render the trailer's score offline to a WAV, in the game's own mixer.

    python -m phase1.audio.score_render                       the whole two minutes
    python -m phase1.audio.score_render --from 45 --to 70     the descent, on its own
    python -m phase1.audio.score_render --plan                the schedule, no audio
    python -m phase1.audio.score_render --score OTHER.json    a different piece

This is `view/recorder.py`'s method with the pictures taken out: `Mixer(offline=True)`, the
clock owned by the caller, one block pulled at a time with `render_offline`, and the whole
thing concatenated and written as PCM. Because the clock is the caller's, the render is
deterministic and exact -- an event at 57.0 s lands on sample 2 736 000 and not near it.

WHY IT DOES NOT CALL `Mixer._room()`, having been told to. `_room` sets `attack=place.attack`
and that is correct for everything it was written for: attack is a distance cue, a transient
that crossed a hundred cells arrives smeared, and no world sound gets a say in it. A score
pad's four-second swell is not a distance cue, it is the gesture. So this replicates `_room`'s
body with one change -- the attack is `max(the line's, the placement's)`, so a pad swells and
the pulse still gets its distance smear for free -- and takes the reflections themselves
straight from `Placement.for_sound`, unchanged, which is what makes the score share the room
rather than sit on top of it. `Mixer.ratchet_notch` sets the precedent: it builds its own
direct voices and loops `place.reflections` for the same kind of reason.

The stop at 1:01 is `Mixer.duck(0.0, ramp)` -- the crash's own mechanism, aimed at the score.
"""
from __future__ import annotations

import argparse
import math
import wave
from pathlib import Path

import numpy as np

from .. import geometry as G
from . import voice as voice_module
from .envelope_shape import EnvelopeShape
from .placement import Placement
from .score import Score
from .score_event import ScoreEvent
from .score_spec import ScoreSpec
from .waveform import Waveform

_REPO: Path = Path(__file__).resolve().parents[2]
DEFAULT_SCORE: Path = _REPO / "spikes" / "score" / "trailer.json"
DEFAULT_OUT: Path = _REPO / "spikes" / "score" / "trailer-score.wav"

_REFLECT_ATTACK_FLOOR: float = 0.02      # as Mixer._room: another wall's worth of smear
_FULL_SCALE_24: float = 8388607.0


class ScoreRender:
    """One offline render of one `ScoreSpec`. Not reusable: it consumes the schedule."""

    def __init__(self, spec: ScoreSpec, verbose: bool = True) -> None:
        voice_module.set_sample_rate(spec.sample_rate)
        from .mixer import Mixer                     # after the rate, never before
        self.spec: ScoreSpec = spec
        self.score: Score = Score(spec)
        self.mixer = Mixer(offline=True)
        self.verbose: bool = verbose
        self.peak_voices: int = 0
        self.queued: int = 0
        self.struck: int = 0

    # ---- one event ---------------------------------------------------------------------
    def _place(self, event: ScoreEvent) -> Placement:
        """The same `Placement` every world sound gets, asked for at the score's distance.

        Pan goes in as a bearing because that is the only way in: `Placement.pan_for` is
        `cos(bearing + camera)`, so a pan of -0.30 is a bearing of acos(-0.30) with the
        camera at zero. Round trip is exact.
        """
        bearing = math.acos(G.clamp(event.pan, -1.0, 1.0))
        return Placement.for_sound(bearing, event.quality, 0.0,
                                   max_reflections=max(event.max_reflections, 1))

    def _queue(self, event: ScoreEvent, delay: float) -> None:
        place = self._place(event)
        attack = max(event.attack, place.attack)
        amp = event.amplitude * place.gain
        stack = (self.mixer._struck(event.ratios, place.brightness, event.tilt)
                 if event.tonal else ((1.0, 1.0),))
        wave_form = Waveform.SINE if event.tonal else Waveform.NOISE
        self.mixer.play(wave_form, event.f0, event.f1, event.duration, amp, event.pan,
                        attack=attack, decay=event.decay, delay=delay,
                        shape=EnvelopeShape.EXPONENTIAL, partials=stack,
                        lowpass=1 if event.tonal else event.noise_lowpass)
        self.queued += 1
        # The cave answering, exactly as Mixer._room does it: longer, duller, from the side.
        grown = min(event.duration * 1.9, event.duration + 0.45)
        scale = grown / max(event.duration, 1e-6)
        for reflection in place.reflections[:event.max_reflections]:
            echo = (self.mixer._struck(event.ratios, reflection.brightness, event.tilt)
                    if event.tonal else ((1.0, 1.0),))
            self.mixer.play(wave_form, event.f0, event.f1, grown,
                            amp * reflection.gain, reflection.pan,
                            attack=max(attack, _REFLECT_ATTACK_FLOOR),
                            decay=event.decay * scale, delay=delay + reflection.delay,
                            shape=EnvelopeShape.EXPONENTIAL, partials=echo,
                            lowpass=1 if event.tonal else int(event.noise_lowpass * 1.4))
            self.queued += 1

    # ---- the whole piece ------------------------------------------------------------------
    def run(self) -> np.ndarray:
        rate = self.spec.sample_rate
        block = self.spec.block_samples
        blocks = int(round(self.spec.length_s * rate)) // block
        chunks: list[np.ndarray] = []
        for index in range(blocks):
            t0 = index * block / rate
            t1 = (index + 1) * block / rate
            for event in self.score.due(t0, t1):
                self._queue(event, delay=event.t - t0)
                self.struck += 1
            if self.score.stops_in(t0, t1):
                # Sample-exact because the cut lands on a block boundary by construction:
                # 61.000 s at 48 kHz in 480-sample blocks is block 6100 and no remainder.
                self.mixer.duck(0.0, self.spec.stop_ramp_s)
                if self.verbose:
                    print(f"  stop at {self.spec.stop_s:.3f}s: "
                          f"{len(self.mixer.voices)} voices muted over "
                          f"{self.spec.stop_ramp_s * 1000:.0f} ms")
            chunks.append(self.mixer.render_offline(block / rate).astype(np.float32))
            self.peak_voices = max(self.peak_voices, len(self.mixer.voices))
            if self.verbose and index % (rate // block * 15) == 0:
                print(f"  {t0:6.1f}s  voices {len(self.mixer.voices):3d}  "
                      f"struck {self.struck:4d}")
        mix = np.concatenate(chunks, axis=0)
        want = int(round(self.spec.length_s * rate))
        if mix.shape[0] < want:                       # a length that is not a whole block
            mix = np.vstack([mix, np.zeros((want - mix.shape[0], 2), dtype=np.float32)])
        return mix[:want]


# ---- output -------------------------------------------------------------------------------
def write_wav(path: Path, mix: np.ndarray, rate: int) -> float:
    """24-bit PCM, and only ever attenuated -- never normalised up.

    A stem that has been made louder is a stem whose level is a fact about this script rather
    than about the score, and the assembler needs the second thing. If this prints a
    reduction, the fix is a smaller `amp` in the JSON and not a bigger number here.
    """
    peak = float(np.max(np.abs(mix))) if mix.size else 0.0
    if peak > 1.0:
        print(f"  WARNING: peak {peak:.3f} over full scale; attenuating. Lower `amp` "
              f"in the score instead.")
        mix = mix / peak
    ints = np.round(np.clip(mix, -1.0, 1.0) * _FULL_SCALE_24).astype("<i4")
    packed = np.frombuffer(ints.tobytes(), dtype=np.uint8).reshape(-1, 4)[:, :3]
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(2)
        handle.setsampwidth(3)
        handle.setframerate(rate)
        handle.writeframes(packed.tobytes())
    return peak


def print_plan(score: Score) -> None:
    events = score.plan()
    print(f"{len(events)} events")
    print(f"{'t':>8}  {'line':<22} {'Hz':>16} {'dur':>6} {'atk':>6} {'amp':>6} "
          f"{'pan':>6} {'q':>5}")
    for event in events:
        print(f"{event.t:8.3f}  {event.line:<22} {event.hz():>16} {event.duration:6.2f} "
              f"{event.attack:6.2f} {event.amplitude:6.3f} {event.pan:6.2f} "
              f"{event.quality:5.2f}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="phase1.audio.score_render")
    parser.add_argument("--score", default=str(DEFAULT_SCORE))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--from", dest="start", type=float, default=None,
                        help="seconds; the excerpt is cut from the full render, so tails "
                             "struck before the window are still in it")
    parser.add_argument("--to", dest="end", type=float, default=None)
    parser.add_argument("--plan", action="store_true", help="print the schedule and exit")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    spec = ScoreSpec.load(args.score)
    if args.plan:
        print_plan(Score(spec))
        return

    problems = Score(spec).band_report()
    for problem in problems:
        print(f"  BAND: {problem}")
    print(f"{spec.name}: {spec.length_s:.3f}s at {spec.sample_rate} Hz, "
          f"{len(spec.sections)} sections, "
          f"stop at {spec.stop_s:.3f}s, "
          f"{'clear' if not problems else str(len(problems)) + ' hits'} of 400-3000 Hz")

    render = ScoreRender(spec, verbose=not args.quiet)
    mix = render.run()
    rate = spec.sample_rate
    if args.start is not None or args.end is not None:
        a = int(round((args.start or 0.0) * rate))
        b = int(round((args.end if args.end is not None else spec.length_s) * rate))
        mix = mix[a:b]
    peak = write_wav(Path(args.out), mix, rate)
    seconds = mix.shape[0] / rate
    print(f"  {render.struck} strikes -> {render.queued} voices, "
          f"peak concurrent {render.peak_voices} of 48")
    if render.peak_voices >= 48:
        print("  WARNING: hit AUDIO_MAX_VOICES; the mixer will have dropped strikes.")
    print(f"  wrote {args.out}  {seconds:.3f}s  peak {peak:.3f} "
          f"({20 * math.log10(max(peak, 1e-9)):.1f} dBFS)")


if __name__ == "__main__":
    main()
