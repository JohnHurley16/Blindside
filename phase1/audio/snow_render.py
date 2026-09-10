"""Render the snow set to one auditionable contact sheet, with a cue sheet beside it.

    python -m phase1.audio.snow_render
    python -m phase1.audio.snow_render --only one_deep_cold,one_packed --out X.wav

Every slot gets silence around it and a line in the printed cue sheet, and the same table is
written next to the WAV as `snow-cues.json` so `spikes/score/measure2.py snow` can find each
slot without anybody typing timecodes twice.

FOUR OF THE SLOTS ARE CONTROLS AND THEY ARE THE POINT, not padding:

  one_concrete    `Surface.footfall`, unchanged, on concrete. This is what an IMPACT measures
                  like, and the snow recipes are only interesting if they measure differently.
  one_deep_mild   the same deep-snow footfall at one degree of frost instead of fourteen.
                  If `temperature_c` is doing anything, these two are different sounds.
  wind_fixed      the wind built the way `Surface.wind` used to build it -- three fixed bands
                  at different levels with long envelopes -- so the swept-corner version has
                  something to be measured against.
  call_snow       the same event as `call_still`, in falling snow. The deadness only exists
                  as this pair.

Same machinery as `surface_render`, and the same two reasons for it: a fresh `Mixer` per slot,
because `Voice.render` only retires a voice once the clock has passed its delay and a hundred
seconds queued in one pass would hit the cap by scheduling rather than by sound; and the cap
itself raised, explicitly and only here, because `AUDIO_MAX_VOICES` is a live frame budget and
an offline render has no frames. The number that matters for the live question is printed
separately: how many voices were ever SOUNDING at once.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from . import voice as voice_module
from .score_render import DEFAULT_SCORE, write_wav

RATE: int = 48000
BLOCK: int = 480
GAP_S: float = 1.2
OFFLINE_VOICE_CAP: int = 1024
COLD_C: float = -14.0
MILD_C: float = -1.0
DEFAULT_OUT: Path = DEFAULT_SCORE.parents[0] / "snow-contact-sheet.wav"


def slot_table() -> dict[str, tuple[float, str, object]]:
    """name -> (seconds, kind, a function that queues that slot on a fresh Snow).

    `kind` is what the measurement should do with it: "event" is one isolated onset whose
    shape is the question, "wind" is a bed whose corner is the question, "slot" is everything
    else and only gets the spectral table.
    """

    def ones(temperature: float, deep: bool):
        def queue(snow) -> None:
            drop = snow.footfall_deep if deep else snow.footfall_packed
            drop(delay=0.25, level=0.34, pan=0.0, temperature_c=temperature)
        return queue

    def concrete(snow) -> None:
        from .surface import Surface
        Surface(snow.mixer, seed=5).footfall(delay=0.25, level=0.34, pan=0.0, concrete=True)

    def many(temperature: float, deep: bool, count: int = 6):
        def queue(snow) -> None:
            drop = snow.footfall_deep if deep else snow.footfall_packed
            for index in range(count):
                drop(delay=0.30 + index * 0.62, level=0.30,
                     pan=-0.45 + 0.18 * index, temperature_c=temperature)
        return queue

    def wind_fixed(snow) -> None:
        """`Surface.wind` as it was before the corner could move: three fixed bands, long
        envelopes, different pans. Kept here verbatim as the control."""
        from .waveform import Waveform
        rng = snow.rng
        seconds, level, gusts = 10.0, 0.13, 5
        for index in range(gusts):
            start = 0.3 + seconds * index / (gusts + 1.0)
            length = seconds * float(rng.uniform(0.45, 0.8))
            pan = float(rng.uniform(-0.85, 0.85))
            for width, share in ((120, 1.0), (46, 0.55), (12, 0.16)):
                snow.mixer.play(Waveform.NOISE, 0.0, 0.0, length,
                                level * share * float(rng.uniform(0.6, 1.0)),
                                pan * (1.0 if width == 120 else 0.75),
                                attack=length * 0.42, decay=length * 0.45,
                                delay=start, lowpass=width)

    return {
        "one_deep_cold": (0.9, "event", ones(COLD_C, True)),
        "one_deep_mild": (0.9, "event", ones(MILD_C, True)),
        "one_packed": (0.9, "event", ones(COLD_C, False)),
        "one_concrete": (0.9, "event", concrete),
        "deep_cold": (4.6, "slot", many(COLD_C, True)),
        "deep_mild": (4.6, "slot", many(MILD_C, True)),
        "packed_cold": (4.6, "slot", many(COLD_C, False)),
        "gait_deep": (8.0, "slot", lambda s: s.gait(7.4, delay=0.3, level=0.28, deep=True)),
        "gait_packed": (8.0, "slot",
                        lambda s: s.gait(7.4, delay=0.3, level=0.26, deep=False)),
        "wind_open": (11.0, "wind",
                      lambda s: s.valley_wind(10.0, delay=0.3, level=0.13)),
        "wind_fixed": (11.0, "wind", wind_fixed),
        "spindrift": (5.5, "slot",
                      lambda s: s.spindrift(4.4, delay=0.3, level=0.11, pan=0.35)),
        "falling_snow": (8.0, "slot",
                         lambda s: s.falling_snow(7.4, delay=0.3, level=0.045)),
        "call_still": (9.5, "slot",
                       lambda s: s.valley_call(delay=0.3, level=0.34, still_air=True)),
        "call_snow": (9.5, "slot",
                      lambda s: s.valley_call(delay=0.3, level=0.34, still_air=False)),
        "open_valley": (12.0, "slot",
                        lambda s: s.open_valley(11.0, delay=0.3, level=0.16)),
        "machine_crossing": (10.0, "slot",
                             lambda s: s.machine_crossing(9.4, delay=0.3, level=0.26)),
    }


def render_slot(queue, seconds: float, seed: int) -> tuple[np.ndarray, int, int]:
    from .mixer import Mixer
    from .snow import Snow

    mixer = Mixer(offline=True)
    queue(Snow(mixer, seed=seed))
    peak_queued = len(mixer.voices)
    chunks: list[np.ndarray] = []
    peak_sounding = 0
    for _ in range(int(seconds * RATE) // BLOCK):
        chunks.append(mixer.render_offline(BLOCK / RATE).astype(np.float32))
        peak_sounding = max(peak_sounding, sum(
            1 for v in mixer.voices if v.offset <= v.pos <= v.offset + len(v.sig)))
    return np.concatenate(chunks, axis=0), peak_queued, peak_sounding


def main() -> None:
    parser = argparse.ArgumentParser(prog="phase1.audio.snow_render")
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--only", default=None)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()

    voice_module.set_sample_rate(RATE)
    from . import mixer as mixer_module
    mixer_module.MAX_VOICES = OFFLINE_VOICE_CAP          # see the module docstring

    table = slot_table()
    names = args.only.split(",") if args.only else list(table)
    gap = np.zeros((int(GAP_S * RATE), 2), dtype=np.float32)

    pieces: list[np.ndarray] = []
    cues: dict[str, list[dict]] = {"slots": [], "events": [], "winds": []}
    print(f"{'t':>8}  {'queued':>6} {'sounding':>8}  cue")
    at = 0.0
    worst_sounding = 0
    for name in names:
        if name not in table:
            raise SystemExit(f"unknown slot {name!r}; have {sorted(table)}")
        seconds, kind, queue = table[name]
        buffer, queued, sounding = render_slot(queue, seconds, args.seed)
        worst_sounding = max(worst_sounding, sounding)
        length = buffer.shape[0] / RATE
        print(f"{at:8.2f}  {queued:6d} {sounding:8d}  {name}")
        cues["slots"].append({"name": name, "at": round(at, 4), "len": round(length, 4)})
        if kind == "event":
            # 0.30 s from just before the onset: long enough to contain the whole compression
            # and its silence, short enough that the window is the event and not the slot.
            cues["events"].append({"name": name, "at": round(at + 0.24, 4), "len": 0.30})
        if kind == "wind":
            cues["winds"].append({"name": name, "at": round(at + 1.0, 4),
                                  "len": round(length - 2.0, 4)})
        pieces.extend((buffer, gap))
        at += length + GAP_S

    mix = np.concatenate(pieces, axis=0)
    out = Path(args.out)
    peak = write_wav(out, mix, RATE)
    cue_path = out.with_name("snow-cues.json")
    cue_path.write_text(json.dumps(cues, indent=2), encoding="utf-8")
    print(f"{at:8.2f}  {'':6} {'':8}  end")
    print(f"\n  peak SOUNDING voices {worst_sounding} of the live cap 48 "
          f"({'inside' if worst_sounding < 48 else 'OVER'} the live budget)")
    print(f"  wrote {out}  {mix.shape[0] / RATE:.3f}s  peak {peak:.3f}")
    print(f"  wrote {cue_path}")


if __name__ == "__main__":
    main()
