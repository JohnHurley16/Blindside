"""Render the surface recipes to one auditionable WAV, with a cue sheet.

    python -m phase1.audio.surface_render
    python -m phase1.audio.surface_render --only headframe --out shot2.wav

Each recipe gets its own slot with silence around it, then the two composed shots the trailer
actually needs -- the headframe at 0:05 and the bench at 0:22 -- so the question "does this
hold a frame" can be asked of the thing that would hold the frame rather than of a recipe.

Same machinery as `score_render`: `Mixer(offline=True)` and the caller owning the clock. It is
a separate command because the score and the ambience are separate stems, and section 8.1's
judgement is that if only one of them gets made it should be the score.

TWO THINGS ABOUT THE VOICE BUDGET, because the first render hit the cap and dropped sound.

Each slot gets its own `Mixer` and its own buffer, and they are concatenated. That is not
tidiness: `Voice.render` only retires a voice once the clock has passed its delay, so a
hundred seconds queued in one pass keeps every voice in the list from the first block and
`AUDIO_MAX_VOICES` is reached by scheduling rather than by sound.

Even one slot exceeds 48, because `bench` lays out thirteen seconds of servos and footfalls in
a single call. `AUDIO_MAX_VOICES` is a live budget -- what a frame can afford to mix -- and an
offline render has no frames, so it is raised here, explicitly and only here. The number that
matters for the live question is printed separately: how many voices were ever SOUNDING at
once, which is the honest count and which stays well inside the real cap.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from . import voice as voice_module
from .score_render import DEFAULT_SCORE, write_wav

RATE: int = 48000
BLOCK: int = 480
GAP_S: float = 1.6
OFFLINE_VOICE_CAP: int = 512
DEFAULT_OUT: Path = DEFAULT_SCORE.parents[0] / "surface-ambience.wav"


def slot_table() -> dict[str, tuple[float, object]]:
    """name -> (seconds, a function that queues that slot on a fresh Surface)."""

    def drips(surface) -> None:
        for index, hz in enumerate((118.0, 236.0, 340.0, 512.0)):
            surface.drip(delay=0.3 + index * 1.1, level=0.20, pan=-0.6 + 0.4 * index,
                         pipe_hz=hz)

    def footfalls(surface) -> None:
        for index in range(6):
            surface.footfall(delay=0.3 + index * 0.62, level=0.32, pan=-0.4 + 0.16 * index,
                             concrete=index < 3)

    def servos(surface) -> None:
        for index, (span, load, hz) in enumerate(((0.35, 0.6, 152.0), (0.9, 1.0, 118.0),
                                                  (0.6, 1.5, 96.0), (0.45, 0.3, 176.0))):
            surface.servo(span, delay=0.3 + index * 1.4, level=0.18, pan=-0.5 + 0.33 * index,
                          hz=hz, load=load)

    def irons(surface) -> None:
        surface.iron_under_load(3.2, delay=0.3, level=0.26, pan=-0.2, hz=52.0)
        surface.iron_under_load(4.0, delay=4.5, level=0.22, pan=0.25, hz=38.0, creaks=9)

    return {
        "wind": (9.5, lambda s: s.wind(9.0, delay=0.3, level=0.13)),
        "rain": (10.5, lambda s: s.rain_on_steel(9.0, delay=0.3, level=0.09)),
        "pipe": (10.0, lambda s: s.water_in_pipe(9.0, delay=0.3, level=0.07)),
        "drip": (5.5, drips),
        "footfall": (4.8, footfalls),
        "servo": (6.6, servos),
        "iron": (9.5, irons),
        "yard": (10.0, lambda s: s.yard_hum(9.0, delay=0.3, level=0.07)),
        "headframe": (12.5, lambda s: s.headframe(11.0, delay=0.3, level=0.17)),
        "bench": (14.5, lambda s: s.bench(13.0, delay=0.3, level=0.26)),
    }


def render_slot(queue, seconds: float, seed: int) -> tuple[np.ndarray, int, int]:
    """One slot on its own mixer. Returns the buffer, the peak queued and the peak sounding."""
    from .mixer import Mixer
    from .surface import Surface

    mixer = Mixer(offline=True)
    queue(Surface(mixer, seed=seed))
    peak_queued = len(mixer.voices)
    chunks: list[np.ndarray] = []
    peak_sounding = 0
    for _ in range(int(seconds * RATE) // BLOCK):
        chunks.append(mixer.render_offline(BLOCK / RATE).astype(np.float32))
        peak_sounding = max(peak_sounding, sum(
            1 for v in mixer.voices if v.offset <= v.pos <= v.offset + len(v.sig)))
    return np.concatenate(chunks, axis=0), peak_queued, peak_sounding


def main() -> None:
    parser = argparse.ArgumentParser(prog="phase1.audio.surface_render")
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--only", default=None,
                        help="comma-separated: wind,rain,pipe,drip,footfall,servo,iron,"
                             "yard,headframe,bench")
    parser.add_argument("--seed", type=int, default=4)
    args = parser.parse_args()

    voice_module.set_sample_rate(RATE)
    from . import mixer as mixer_module
    mixer_module.MAX_VOICES = OFFLINE_VOICE_CAP          # see the module docstring

    table = slot_table()
    names = args.only.split(",") if args.only else list(table)
    gap = np.zeros((int(GAP_S * RATE), 2), dtype=np.float32)

    pieces: list[np.ndarray] = []
    print(f"{'t':>8}  {'queued':>6} {'sounding':>8}  cue")
    at = 0.0
    worst_sounding = 0
    for name in names:
        if name not in table:
            raise SystemExit(f"unknown slot {name!r}; have {sorted(table)}")
        seconds, queue = table[name]
        buffer, queued, sounding = render_slot(queue, seconds, args.seed)
        worst_sounding = max(worst_sounding, sounding)
        print(f"{at:8.2f}  {queued:6d} {sounding:8d}  {name}")
        pieces.extend((buffer, gap))
        at += buffer.shape[0] / RATE + GAP_S

    mix = np.concatenate(pieces, axis=0)
    peak = write_wav(Path(args.out), mix, RATE)
    print(f"{at:8.2f}  {'':6} {'':8}  end")
    print(f"\n  peak SOUNDING voices {worst_sounding} of the live cap 48 "
          f"({'inside' if worst_sounding < 48 else 'OVER'} the live budget)")
    print(f"  wrote {args.out}  {mix.shape[0] / RATE:.3f}s  peak {peak:.3f}")


if __name__ == "__main__":
    main()
