"""Measure the rewritten score and the snow set, because nobody here can hear either.

    python spikes/score/measure2.py score spikes/score/valley-score.wav --svg OUT.svg
    python spikes/score/measure2.py snow  spikes/score/snow-contact-sheet.wav

`measure.py` is kept as it was: its passage table and its stop report are about a score that
had six acts and a hard cut at 1:01, and neither exists any more. What is reused here is its
method and two of its findings -- F50/F85 instead of a spectral centroid (a magnitude-weighted
centroid on this material counts empty bins and reports the noise floor's width), and the
300 Hz / 12 dB-per-octave laptop model out of `Mixer.hammer`'s docstring.

WHAT IS NEW HERE, and why each exists.

  movements           The structure is seven movements and no cards, so the passage table is
                      driven from the score document rather than hardcoded.

  above 3 kHz         The old score had nothing up there. This one puts its top layer above
                      the reserved band on purpose, and that layer is both the thing that
                      makes it cold and the thing that survives a laptop, so it is measured
                      as its own column rather than folded into "everything else".

  interval census     A PROXY FOR "BEAUTIFUL RATHER THAN OMINOUS", and the only one I have.
                      Ominous is mostly two things a measurement can see: semitone and
                      tritone verticalities, and beating in the roughness band (about 15-30
                      Hz between partials, which is what makes a low dissonance sour rather
                      than merely low). This walks the score document, finds every pair of
                      fundamentals that is sounding at the same time, and reports the
                      smallest interval and the fastest beat anywhere in the piece. It cannot
                      say the piece is beautiful. It can say it contains none of the specific
                      things that make music sound wrong.

  rubato census       A PROXY FOR "somebody played this". The old score's own notes said every
                      strike was on an exact integer second with no variation of touch. This
                      counts the inter-onset intervals of every repeating line and reports
                      their spread, and does the same for amplitude.

  attack census       How many events are struck and how many swell. The piece claims exactly
                      one hard attack in 108 seconds; this is the check.

The snow half is in its own subcommand and its measurements are described there.

WHAT NONE OF IT ANSWERS is in NOTES2.md, under "what needs a human ear".
"""
from __future__ import annotations

import argparse
import json
import math
import wave
from pathlib import Path

import numpy as np

WINDOW: int = 4096
HOP: int = 4800                  # 100 ms at 48 kHz
BAND_LOW: float = 400.0
BAND_HIGH: float = 3000.0
SPEAKER_CORNER: float = 300.0
SPEAKER_SLOPE_DB: float = 12.0


def read_wav(path: Path) -> tuple[np.ndarray, int]:
    with wave.open(str(path), "rb") as handle:
        rate = handle.getframerate()
        width = handle.getsampwidth()
        channels = handle.getnchannels()
        raw = handle.readframes(handle.getnframes())
    if width == 2:
        data = np.frombuffer(raw, dtype="<i2").astype(np.float64) / 32768.0
    elif width == 3:
        b = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3)
        packed = np.zeros((b.shape[0], 4), dtype=np.uint8)
        packed[:, 1:] = b
        data = np.frombuffer(packed.tobytes(), dtype="<i4").astype(np.float64) / 2147483648.0
    else:
        raise ValueError(f"{path}: {width * 8}-bit PCM not handled")
    return data.reshape(-1, channels), rate


def db(x: float) -> float:
    return 20.0 * math.log10(max(x, 1e-12))


# ---- the score ------------------------------------------------------------------------------
class Frames:
    """One row per 100 ms. Plain arrays; nothing clever."""

    def __init__(self, mono: np.ndarray, rate: int) -> None:
        window = np.hanning(WINDOW)
        freqs = np.fft.rfftfreq(WINDOW, 1.0 / rate)
        in_band = (freqs >= BAND_LOW) & (freqs <= BAND_HIGH)
        over = freqs > BAND_HIGH
        octaves = np.where(freqs > 0.0,
                           np.log2(np.maximum(freqs, 1e-9) / SPEAKER_CORNER), -12.0)
        speaker = np.where(octaves >= 0.0, 1.0, 10.0 ** (SPEAKER_SLOPE_DB * octaves / 20.0))
        norm = float(np.sum(window * window)) * WINDOW

        rows: list[tuple[float, ...]] = []
        for start in range(0, len(mono) - WINDOW + 1, HOP):
            chunk = mono[start:start + WINDOW]
            power = np.abs(np.fft.rfft(chunk * window)) ** 2
            total = float(power.sum())
            if total > 0.0:
                cumulative = np.cumsum(power) / total
                f50 = float(freqs[int(np.searchsorted(cumulative, 0.50))])
                f85 = float(freqs[int(np.searchsorted(cumulative, 0.85))])
                frac = float(power[in_band].sum() / total)
                high = float(power[over].sum() / total)
                band = math.sqrt(2.0 * float(power[in_band].sum()) / norm)
                top = math.sqrt(2.0 * float(power[over].sum()) / norm)
                laptop = math.sqrt(2.0 * float((power * speaker * speaker).sum()) / norm)
            else:
                f50 = f85 = frac = high = band = top = laptop = 0.0
            rows.append(((start + WINDOW / 2) / rate,
                         float(np.sqrt(np.mean(chunk * chunk))),
                         f50, f85, frac, high, band, top, laptop))
        table = np.array(rows)
        (self.t, self.rms, self.f50, self.f85, self.frac, self.high,
         self.band_rms, self.top_rms, self.laptop) = (table[:, i] for i in range(9))

    def span(self, values: np.ndarray, a: float, b: float) -> np.ndarray:
        return values[(self.t >= a) & (self.t < b)]


def movements(doc: dict) -> list[tuple[str, float, float]]:
    """Seven movements, from TRAILER.md as rewritten. Section boundaries are finer than
    these -- one section per chord -- so the sections are grouped by their id prefix."""
    groups: dict[str, list[float]] = {}
    order: list[str] = []
    for section in doc["sections"]:
        head = str(section["id"]).split("_")[0]
        if head not in groups:
            groups[head] = [float(section["from_s"]), float(section["to_s"])]
            order.append(head)
        else:
            groups[head][1] = max(groups[head][1], float(section["to_s"]))
    return [(name, groups[name][0], groups[name][1]) for name in order]


def structure_table(f: Frames, marks: list[tuple[str, float, float]]) -> list[str]:
    out = [f"{'movement':<14} {'t':>11} {'RMS dB':>7} {'peak dB':>8} {'F50':>5} {'F85':>5} "
           f"{'400-3k':>8} {'in-band dB':>11} {'>3k':>7} {'>3k dB':>8} {'laptop dB':>10}",
           "-" * 108]
    for name, a, b in marks:
        r = f.span(f.rms, a, b)
        if r.size == 0:
            continue
        out.append(
            f"{name:<14} {f'{a:.0f}-{b:.0f}s':>11} {db(float(r.mean())):7.1f} "
            f"{db(float(r.max())):8.1f} {float(f.span(f.f50, a, b).mean()):5.0f} "
            f"{float(f.span(f.f85, a, b).mean()):5.0f} "
            f"{float(f.span(f.frac, a, b).mean()) * 100:7.3f}% "
            f"{db(float(f.span(f.band_rms, a, b).max())):11.1f} "
            f"{float(f.span(f.high, a, b).mean()) * 100:6.2f}% "
            f"{db(float(f.span(f.top_rms, a, b).mean())):8.1f} "
            f"{db(float(f.span(f.laptop, a, b).mean())):10.1f}")
    return out


def envelope_table(mono: np.ndarray, rate: int, a: float, b: float, step: float) -> list[str]:
    out = [f"{'window':>14} {'RMS dB':>8}"]
    t = a
    while t < b - 1e-9:
        chunk = mono[int(t * rate):int(min(t + step, b) * rate)]
        if chunk.size:
            out.append(f"{f'{t:6.1f}-{min(t + step, b):5.1f}':>14} "
                       f"{db(float(np.sqrt(np.mean(chunk * chunk)))):8.1f}")
        t += step
    return out


def peak_table(mono: np.ndarray, rate: int, a: float, b: float, limit: float = 460.0,
               count: int = 9) -> str:
    chunk = mono[int(a * rate):int(b * rate)]
    size = 1 << (len(chunk) - 1).bit_length()
    spectrum = np.abs(np.fft.rfft(chunk * np.hanning(len(chunk)), size))
    freqs = np.fft.rfftfreq(size, 1.0 / rate)
    keep = freqs < limit
    spectrum, freqs = spectrum[keep], freqs[keep]
    picked: list[int] = []
    for i in np.argsort(spectrum)[::-1]:
        if all(abs(freqs[i] - freqs[j]) > 1.2 for j in picked):
            picked.append(int(i))
        if len(picked) >= count:
            break
    picked.sort(key=lambda i: freqs[i])
    top = float(spectrum.max())
    return "  ".join(f"{freqs[i]:6.1f} {db(spectrum[i] / top):+5.1f}" for i in picked)


# ---- what the document itself says ----------------------------------------------------------
_NAMES = ("C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B")


def _note_name(hz: float) -> str:
    midi = int(round(69 + 12 * math.log2(hz / 440.0)))
    return f"{_NAMES[midi % 12]}{midi // 12 - 1}"


def sounding_events(path: Path) -> list[dict]:
    """Every strike the transport will emit, with its pitch and its envelope, from the plan."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from phase1.audio.score import Score                       # noqa: PLC0415
    from phase1.audio.score_spec import ScoreSpec              # noqa: PLC0415

    spec = ScoreSpec.load(path)
    out: list[dict] = []
    for event in Score(spec).plan():
        if not event.tonal:
            continue
        out.append({"t": event.t, "hz": event.f0, "amp": event.amplitude,
                    "line": event.line, "attack": event.attack, "decay": event.decay,
                    "end": event.t + event.duration})
    return out


def level_at(e: dict, t: float) -> float:
    """What this note is actually doing at time t: `Envelope`, evaluated.

    This is the correction that makes the interval census mean anything. Comparing NOMINAL
    amplitudes credits a chord struck eleven seconds ago with forming an interval against the
    one standing now, and every piece ever written contains a semitone if that is allowed.
    What forms an interval is what is sounding.
    """
    if t < e["t"] or t >= e["end"]:
        return 0.0
    u = t - e["t"]
    return e["amp"] * min(u / max(e["attack"], 1e-6), 1.0) * math.exp(
        -u / max(e["decay"], 1e-6))


def interval_census(events: list[dict], floor_db: float = -20.0) -> list[str]:
    """The smallest vertical interval, the closest low pair, and the beating. A PROXY FOR
    "beautiful rather than ominous", and the only one available.

    Three specific things make music sound wrong, and all three are visible in a document:

      a semitone or a tritone between two notes that are actually sounding together;
      two notes closer than a minor third in the bass, where one critical band is wide
      enough that any interval at all beats rather than blends;
      and beating between 12 and 35 Hz, which is the roughness band and is the difference
      between a low chord that is warm and a low chord that is sour.

    Sampled every 0.25 s. Both notes must be within `floor_db` of the loudest thing sounding
    at that instant, so a dying tail is not credited with an interval nobody can hear.
    """
    if not events:
        return ["no events"]
    end = max(e["end"] for e in events)
    worst = (99.0, 0.0, "", "")
    worst_low = (99.0, 0.0, "", "")
    tritones: list[tuple[float, float, str, str]] = []
    clusters: list[tuple[float, float, str, str]] = []
    rough: list[tuple[float, float, str, str]] = []
    seconds: list[tuple[float, float, str, str]] = []
    unisons = 0
    samples = 0
    t = 0.0
    while t < end:
        live = [(level_at(e, t), e) for e in events]
        live = [(v, e) for v, e in live if v > 0.0]
        if live:
            gate = max(v for v, _ in live) * 10.0 ** (floor_db / 20.0)
            audible = [e for v, e in live if v >= gate]
            samples += 1
            for i, a in enumerate(audible):
                for b in audible[i + 1:]:
                    lo, hi = sorted((a["hz"], b["hz"]))
                    steps = 12.0 * math.log2(hi / lo)
                    # Under a fifth of a semitone is a UNISON, not an interval. The score is
                    # full of them on purpose -- the detuned pairs that make the width, and
                    # a chord holding a note the next chord also holds -- and counting them
                    # as dissonances made the first version of this report meaningless.
                    if steps < 0.20:
                        unisons += 1
                        continue
                    pair = (steps, t, a["line"], b["line"])
                    if steps < worst[0]:
                        worst = pair
                    if hi < 200.0 and steps < worst_low[0]:
                        worst_low = pair
                    if abs(abs(steps - 12.0 * round(steps / 12.0)) - 6.0) < 0.35:
                        tritones.append(pair)
                    if steps < 1.6:                 # a minor second: the ominous one
                        clusters.append(pair)
                    elif steps < 3.0:                # a major second: voice leading
                        seconds.append(pair)
                    # Roughness is register-relative: one critical band is about 100 Hz wide
                    # at 250 Hz and much wider proportionally lower down, so 12-35 Hz apart
                    # is inside a band down here and is merely a legato overlap up in the
                    # melody. Tested only where this piece keeps its power.
                    if 12.0 <= hi - lo <= 35.0 and steps < 5.0 and hi < 250.0:
                        rough.append((hi - lo, t, a["line"], b["line"]))
        t += 0.25
    def instants(group: list) -> int:
        return len({round(p[1], 2) for p in group})
    out = [f"sampled every 0.25 s over {samples} sounding instants; a note counts only while "
           f"it is within {floor_db:.0f} dB of the loudest thing then sounding",
           f"  smallest vertical interval anywhere: {worst[0]:.2f} semitones "
           f"({worst[2]} + {worst[3]} at {worst[1]:.1f}s)",
           f"  smallest interval with both notes under 200 Hz: {worst_low[0]:.2f} semitones "
           f"({worst_low[2]} + {worst_low[3]} at {worst_low[1]:.1f}s)",
           f"  instants containing a tritone: {instants(tritones)} of {samples}",
           f"  instants containing a MINOR SECOND: {instants(clusters)} of {samples}",
           f"  instants containing a major second: {instants(seconds)} of {samples}",
           f"  instants with 12-35 Hz beating between two notes under 250 Hz and under a "
           f"fourth apart: {instants(rough)} of {samples}",
           f"  deliberate unisons (detuned pairs, held common tones): {unisons} pairs seen"]
    for label, group in (("tritone", tritones), ("minor second", clusters),
                         ("major second", seconds)):
        if group:
            item = min(group, key=lambda p: abs(p[0] - 6.0) if label == "tritone" else p[0])
            item = min(group, key=lambda p: p[1]) if label == "major second" else item
            out.append(f"  worst {label}: {item[0]:.2f} semitones at {item[1]:.1f}s "
                       f"({item[2]} + {item[3]})")
    if rough:
        item = max(rough, key=lambda p: p[0])
        out.append(f"  worst roughness: {item[0]:.1f} Hz apart at {item[1]:.1f}s "
                   f"({item[2]} + {item[3]})")
    return out


def harmony_chart(path: Path) -> list[str]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    pitches = {k: float(v) for k, v in doc["pitches"].items()}
    out = [f"{'section':<16} {'t':>13}  chord as written"]
    for section in doc["sections"]:
        names = []
        for line in section.get("lines", []):
            value = line["pitch"]
            hz = pitches.get(value) if isinstance(value, str) else float(value)
            if hz is None or hz > 3000.0 or line["timbre"] == "air":
                continue
            name = _note_name(hz)
            if name not in names:
                names.append(name)
        window = f"{float(section['from_s']):.1f}-{float(section['to_s']):.1f}"
        out.append(f"{section['id']:<16} {window:>13}  {' '.join(names)}")
    return out


def rubato_census(events: list[dict]) -> list[str]:
    """The gait as one line, because it IS one line: it walks through ten chords, and
    splitting it by section would report ten pairs of steps and no rhythm."""
    steps = sorted((e["t"], e["amp"]) for e in events if "/tread" in e["line"])
    if not steps:
        return ["no repeating line in this score"]
    times = np.array([t for t, _ in steps])
    amps = np.array([a for _, a in steps])
    gaps = np.diff(times)
    exact = int(np.sum(np.abs(times - np.round(times)) < 0.002))
    return [f"the gait: {len(steps)} steps from {times[0]:.2f}s to {times[-1]:.2f}s",
            f"  gap {gaps.mean():.3f} +/- {gaps.std():.3f} s "
            f"({gaps.min():.3f} to {gaps.max():.3f}), spread {gaps.std() / gaps.mean() * 100:.1f}% "
            f"of the mean",
            f"  steps landing within 2 ms of an integer second: {exact} of {len(steps)}",
            f"  touch: {db(float(amps.max())) - db(float(amps.min())):.1f} dB between the "
            f"heaviest step and the lightest, sd {amps.std() / amps.mean() * 100:.1f}% of mean",
            "  the gaps, in order:",
            "    " + " ".join(f"{g:.2f}" for g in gaps)]


def attack_census(events: list[dict]) -> list[str]:
    """One hard attack in the bed. Everything else swells; the tread is plucked."""
    struck = [e for e in events if e["attack"] < 0.05 and "/tread" not in e["line"]]
    swelled = [e for e in events if e["attack"] >= 0.05]
    attacks = np.array([e["attack"] for e in swelled]) if swelled else np.zeros(1)
    return [f"attacks: {len(struck)} struck under 50 ms with the tread excluded, "
            f"{len(swelled)} swelled, "
            f"{len(events) - len(struck) - len(swelled)} tread",
            f"  the swells run {attacks.min():.2f} to {attacks.max():.2f} s, "
            f"median {float(np.median(attacks)):.2f} s",
            *(f"  struck: {e['line']:<24} {e['t']:7.3f}s  attack {e['attack'] * 1000:.0f} ms"
              for e in struck)]


def write_svg(path: Path, f: Frames, marks: list[tuple[str, float, float]],
              length: float) -> None:
    w, h, pad = 1180.0, 470.0, 58.0
    plot_w = w - 2 * pad
    plot_h = (h - 2 * pad) / 2.0 - 16.0
    top_a, top_b = pad + 6.0, pad + plot_h + 52.0

    def x_of(t: float) -> float:
        return pad + plot_w * t / length

    def y_rms(v: float) -> float:
        return top_a + plot_h * (1.0 - (max(db(v), -80.0) + 80.0) / 80.0)

    def y_hz(v: float) -> float:
        return top_b + plot_h * (1.0 - min(v, 300.0) / 300.0)

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:.0f}" height="{h:.0f}" '
             f'viewBox="0 0 {w:.0f} {h:.0f}" font-family="monospace" font-size="11">',
             f'<rect width="{w:.0f}" height="{h:.0f}" fill="#0d0f11"/>']
    for name, a, _ in marks:
        parts.append(f'<line x1="{x_of(a):.1f}" y1="{pad - 6:.1f}" x2="{x_of(a):.1f}" '
                     f'y2="{h - pad + 10:.1f}" stroke="#2f363d" stroke-width="1"/>')
        parts.append(f'<text x="{x_of(a) + 4:.1f}" y="{pad - 12:.1f}" fill="#7c8892">'
                     f'{name}</text>')
    parts.append(f'<text x="{pad:.1f}" y="{top_a - 4:.1f}" fill="#9aa5ae">'
                 f'RMS dBFS, 100 ms windows (-80 at the floor)</text>')
    parts.append(f'<text x="{pad:.1f}" y="{top_b - 6:.1f}" fill="#9aa5ae">'
                 f'F50 (solid) and F85 (faint), Hz, 0..300 - where the power is</text>')
    for values, colour, width, y_of in ((f.rms, "#e0b95a", 1.5, y_rms),
                                        (f.f85, "#3d6f8e", 1.2, y_hz),
                                        (f.f50, "#5fa8d3", 1.6, y_hz)):
        points = " ".join(f"{x_of(t):.1f},{y_of(v):.1f}" for t, v in zip(f.t, values))
        parts.append(f'<polyline points="{points}" fill="none" stroke="{colour}" '
                     f'stroke-width="{width}"/>')
    for t in range(0, int(length) + 1, 10):
        parts.append(f'<text x="{x_of(t):.1f}" y="{h - pad + 26:.1f}" fill="#7c8892" '
                     f'text-anchor="middle">{t // 60}:{t % 60:02d}</text>')
    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")


def run_score(args: argparse.Namespace) -> None:
    path = Path(args.wav)
    score_path = Path(args.score)
    doc = json.loads(score_path.read_text(encoding="utf-8"))
    stereo, rate = read_wav(path)
    mono = stereo.mean(axis=1)
    length = stereo.shape[0] / rate
    print(f"{path.name}: {stereo.shape[0]} frames, {stereo.shape[1]} ch, {rate} Hz, "
          f"{length:.3f}s, peak {db(float(np.max(np.abs(stereo)))):.1f} dBFS")
    correlation = float(np.corrcoef(stereo[:, 0], stereo[:, 1])[0, 1])
    mid = (stereo[:, 0] + stereo[:, 1]) / 2.0
    side = (stereo[:, 0] - stereo[:, 1]) / 2.0
    spread = db(float(np.sqrt(np.mean(side ** 2)))) - db(float(np.sqrt(np.mean(mid ** 2))))
    print(f"  L/R correlation {correlation:+.3f}, side against mid {spread:+.1f} dB "
          f"(correlation is a whole-file average; side/mid is the honest width number)")

    f = Frames(mono, rate)
    marks = movements(doc)
    print()
    for line in structure_table(f, marks):
        print(line)
    # A fraction of nothing is not a measurement: the last seconds of the map are 40 dB down
    # and every stray bin there is a large share of a tiny total. Gate on level.
    loud = f.rms > float(np.max(f.rms)) * 0.05
    print(f"\nwhole piece: 400-3000 Hz is {float(np.max(f.frac[loud])) * 100:.3f}% of power "
          f"at worst while the piece is sounding, {db(float(np.max(f.band_rms))):.1f} dBFS "
          f"at worst anywhere (a routine heard ping is -18 dBFS)")

    print("\nthe chord chart, as the document writes it")
    for line in harmony_chart(score_path):
        print("  " + line)

    print("\nsection by section: where the power sits, and whether it moves")
    print(f"  {'section':<16} {'t':>13} {'RMS dB':>7} {'F50':>5} {'F85':>5} {'>3k':>7} "
          f"{'laptop dB':>10}")
    for section in doc["sections"]:
        a, b = float(section["from_s"]), float(section["to_s"])
        r = f.span(f.rms, a, b)
        if r.size == 0:
            continue
        print(f"  {section['id']:<16} {f'{a:.1f}-{b:.1f}':>13} {db(float(r.mean())):7.1f} "
              f"{float(f.span(f.f50, a, b).mean()):5.0f} "
              f"{float(f.span(f.f85, a, b).mean()):5.0f} "
              f"{float(f.span(f.high, a, b).mean()) * 100:6.2f}% "
              f"{db(float(f.span(f.laptop, a, b).mean())):10.1f}")

    print("\nthe strongest components under 460 Hz, per movement")
    for name, a, b in marks:
        if b - a < 2.0 or b > length:
            continue
        print(f"  {name:<14} {peak_table(mono, rate, a + 1.0, min(b, a + 7.0))}")

    events = sounding_events(score_path)
    print("\nis it ominous? the interval census")
    for line in interval_census(events):
        print("  " + line)
    print("\ndid anybody play it? the rubato census")
    for line in rubato_census(events):
        print("  " + line)
    print()
    for line in attack_census(events):
        print("  " + line)

    if args.envelope:
        print()
        for line in envelope_table(mono, rate, 0.0, length, 2.5):
            print(line)
    if args.svg:
        write_svg(Path(args.svg), f, marks, length)
        print(f"\nwrote {args.svg}")


# ---- the snow -------------------------------------------------------------------------------
def energy_shape(x: np.ndarray, rate: int) -> tuple[float, float, float, float, float]:
    """Where in its own life an event keeps its energy. The whole snow question in four numbers.

    An IMPACT is a discontinuity: the energy is there in the first millisecond and everything
    after it is a tail. A COMPRESSION is not -- a foot going into deep snow decelerates over
    five to twenty centimetres while the pack densifies, so the energy is spread across the
    whole event and the peak is late, because the pack is stiffest just before it stops.

      centroid   the energy-weighted mean time, as a fraction of the event's length.
                 Under about 0.15 is an impact. Around 0.4 to 0.55 is a compression.
      peak_at    when the envelope peaks, same units.
      rise_ms    10% to 90% of peak. An impact is under a millisecond; a compression is tens.
      tail_ms    time from the peak to 10% of it. For a compression this is the second
                 half of the compression rather than a resonance, so it is reported but is
                 not the ring test.
      ring_db    what is left 200 ms after the onset, against the peak. THIS is the ring
                 test: snow is the most absorptive material a foot ever lands on and there
                 should be nothing there at all.
    """
    env = np.abs(x)
    kernel = max(1, int(0.0015 * rate))
    env = np.convolve(env, np.ones(kernel) / kernel, "same")
    if env.max() <= 0.0:
        return 0.0, 0.0, 0.0, 0.0
    power = env ** 2
    t = np.arange(len(env)) / rate
    centroid = float((t * power).sum() / power.sum()) / (len(env) / rate)
    peak = int(np.argmax(env))
    peak_at = peak / len(env)
    lo = np.nonzero(env[:peak + 1] >= 0.1 * env[peak])[0]
    hi = np.nonzero(env[:peak + 1] >= 0.9 * env[peak])[0]
    rise = (hi[0] - lo[0]) / rate * 1000.0 if lo.size and hi.size else 0.0
    after = np.nonzero(env[peak:] < 0.1 * env[peak])[0]
    tail = float(after[0]) / rate * 1000.0 if after.size else len(env[peak:]) / rate * 1000.0
    late = env[int(0.20 * rate):]
    ring = 20.0 * math.log10(max(float(late.max()) if late.size else 0.0, 1e-12)
                             / max(float(env[peak]), 1e-12))
    return centroid, peak_at, rise, tail, ring


def band_energy(x: np.ndarray, rate: int, edges: tuple[float, ...]) -> list[float]:
    spectrum = np.abs(np.fft.rfft(x * np.hanning(len(x)))) ** 2
    freqs = np.fft.rfftfreq(len(x), 1.0 / rate)
    total = float(spectrum.sum()) or 1.0
    out = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        out.append(float(spectrum[(freqs >= lo) & (freqs < hi)].sum()) / total * 100.0)
    return out


def corner_track(x: np.ndarray, rate: int, window: int = 8192,
                 hop: int = 2048) -> tuple[np.ndarray, np.ndarray]:
    """F85 and RMS over time. For a noise bed F85 IS the filter's corner.

    Two questions, and the second is the one that matters. Does the corner move at all, and
    does it move WITH THE LEVEL -- because that is what separates a gust from a fade. A real
    gust gets brighter as it gets louder; three fixed bands with envelopes on them get louder
    without getting brighter, and no amount of level automation will fix that. The correlation
    between these two tracks is the number.
    """
    corners, levels = [], []
    w = np.hanning(window)
    freqs = np.fft.rfftfreq(window, 1.0 / rate)
    for start in range(0, max(len(x) - window, 1), hop):
        chunk = x[start:start + window]
        power = np.abs(np.fft.rfft(chunk * w)) ** 2
        total = power.sum()
        if total <= 0.0:
            continue
        corners.append(freqs[int(np.searchsorted(np.cumsum(power) / total, 0.85))])
        levels.append(float(np.sqrt(np.mean(chunk * chunk))))
    return (np.array(corners) if corners else np.zeros(1),
            np.array(levels) if levels else np.zeros(1))


def run_snow(args: argparse.Namespace) -> None:
    stereo, rate = read_wav(Path(args.wav))
    mono = stereo.mean(axis=1)
    cues = json.loads(Path(args.cues).read_text(encoding="utf-8"))
    print(f"{Path(args.wav).name}: {stereo.shape[0] / rate:.3f}s, {rate} Hz, "
          f"peak {db(float(np.max(np.abs(stereo)))):.1f} dBFS")

    print(f"\n{'slot':<22} {'t':>7} {'len':>6} {'RMS dB':>7} {'F50':>6} {'F85':>6} "
          f"{'<200':>6} {'.2-1k':>6} {'1-4k':>6} {'>4k':>6}")
    print("-" * 92)
    for cue in cues["slots"]:
        a, b = float(cue["at"]), float(cue["at"]) + float(cue["len"])
        x = mono[int(a * rate):int(b * rate)]
        if x.size == 0:
            continue
        spectrum = np.abs(np.fft.rfft(x * np.hanning(len(x)))) ** 2
        freqs = np.fft.rfftfreq(len(x), 1.0 / rate)
        cumulative = np.cumsum(spectrum) / max(spectrum.sum(), 1e-30)
        bands = band_energy(x, rate, (0.0, 200.0, 1000.0, 4000.0, rate / 2.0))
        print(f"{cue['name']:<22} {a:7.2f} {b - a:6.2f} "
              f"{db(float(np.sqrt(np.mean(x * x)))):7.1f} "
              f"{freqs[int(np.searchsorted(cumulative, 0.5))]:6.0f} "
              f"{freqs[int(np.searchsorted(cumulative, 0.85))]:6.0f} "
              + " ".join(f"{v:5.1f}%" for v in bands))

    print("\nIMPACT OR COMPRESSION -- one event of each kind, aligned on its own onset")
    print(f"{'event':<22} {'centroid':>9} {'peak at':>8} {'rise ms':>8} {'to -20 dB ms':>13} "
          f"{'ring dB':>8}")
    print("-" * 76)
    for cue in cues["events"]:
        a, b = float(cue["at"]), float(cue["at"]) + float(cue["len"])
        x = mono[int(a * rate):int(b * rate)]
        if x.size == 0:
            continue
        centroid, peak_at, rise, tail, ring = energy_shape(x, rate)
        print(f"{cue['name']:<22} {centroid:9.3f} {peak_at:8.3f} {rise:8.1f} {tail:13.1f} "
              f"{ring:8.1f}")

    print("\nDOES THE FILTER CORNER MOVE, AND DOES IT MOVE WITH THE LEVEL")
    print(f"{'slot':<22} {'min Hz':>8} {'max Hz':>8} {'octaves':>8} {'corner v level':>15}")
    print("-" * 66)
    for cue in cues["winds"]:
        a, b = float(cue["at"]), float(cue["at"]) + float(cue["len"])
        corners, levels = corner_track(mono[int(a * rate):int(b * rate)], rate)
        lo, hi = float(corners.min()), float(corners.max())
        r = (float(np.corrcoef(np.log(np.maximum(corners, 1.0)),
                               np.log(np.maximum(levels, 1e-9)))[0, 1])
             if corners.size > 3 else 0.0)
        print(f"{cue['name']:<22} {lo:8.0f} {hi:8.0f} "
              f"{math.log2(hi / max(lo, 1e-6)):8.2f} {r:+15.3f}")
    print("  a gust is brighter BECAUSE it is louder, so the two tracks should rise together;")
    print("  fixed bands under envelopes get louder without getting brighter.")

    print("\nTHE DEADNESS -- does anything come back")
    print(f"{'slot':<22} {'direct dB':>10} {'after 1 s dB':>13} {'gap dB':>8} "
          f"{'direct F85':>11}")
    print("-" * 68)
    for cue in cues["slots"]:
        if not cue["name"].startswith("call_"):
            continue
        a = float(cue["at"])
        direct = mono[int((a + 0.25) * rate):int((a + 0.75) * rate)]
        tail = mono[int((a + 1.3) * rate):int((a + float(cue["len"])) * rate)]
        power = np.abs(np.fft.rfft(direct * np.hanning(len(direct)))) ** 2
        freqs = np.fft.rfftfreq(len(direct), 1.0 / rate)
        f85 = freqs[int(np.searchsorted(np.cumsum(power) / max(power.sum(), 1e-30), 0.85))]
        d = db(float(np.sqrt(np.mean(direct ** 2))))
        t = db(float(np.sqrt(np.mean(tail ** 2))))
        print(f"{cue['name']:<22} {d:10.1f} {t:13.1f} {d - t:8.1f} {f85:11.0f}")
    print("  reverb is measured as what arrives late. Deadness is the absence of that, and it")
    print("  is the one acoustic effect that can only be rendered as a pair.")


def main() -> None:
    parser = argparse.ArgumentParser(prog="measure2")
    subs = parser.add_subparsers(dest="mode", required=True)
    s = subs.add_parser("score")
    s.add_argument("wav")
    s.add_argument("--score", default=str(Path(__file__).with_name("valley.json")))
    s.add_argument("--svg", default=None)
    s.add_argument("--envelope", action="store_true")
    s.set_defaults(func=run_score)
    n = subs.add_parser("snow")
    n.add_argument("wav")
    n.add_argument("--cues", default=str(Path(__file__).with_name("snow-cues.json")))
    n.set_defaults(func=run_snow)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
