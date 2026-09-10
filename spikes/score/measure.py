"""Measure a rendered score stem, because nobody here can hear it.

    python spikes/score/measure.py spikes/score/trailer-score.wav
    python spikes/score/measure.py FILE.wav --svg spikes/score/trailer-score.svg

Every number below is a PROXY and is named as one. None of them can tell you whether the
piece is any good; what they can do is catch the specific ways this piece could be wrong
without anyone noticing until it is in a cut:

  RMS envelope        Does the shape match TRAILER.md section 5's table -- enter at 0:05,
                      tighten through Act II, narrow at 0:50, stop at 1:01, nothing after?
                      A structure that is right on paper and flat in the render is the most
                      likely failure and the easiest one to miss.

  F50 and F85         Proxy for register and for "loses its top": the frequencies below
                      which half and 85% of the power lies. The descent is specified as a
                      drop of one octave and F50 should roughly halve.

                      THESE REPLACED A SPECTRAL CENTROID AND THE REASON MATTERS. A
                      magnitude-weighted centroid on this material measured 1400 Hz during
                      Act II, in a window where 99.5% of the power was under 400 Hz. There
                      are two thousand bins above 400 Hz and eighteen below it, so summing
                      magnitudes counts bins rather than energy and the statistic reported
                      the noise floor's width instead of the music's register. A power-
                      weighted centroid is kept below because it is the standard number and
                      is honest here, but F50 is the one to read.

  400 Hz - 3 kHz      Not a proxy. It is the rule. tuning.py reserves that window for
                      everything that has to be identified by ear, and the score is not
                      allowed to be in it. Reported as a fraction of total power and as an
                      absolute level, because a small fraction of a loud passage can still
                      be a loud sound.

  the stop            Whether 1:01 is a stop or a fade. Three separate questions: is the
                      level falling BEFORE the cut (a fade has already started), how many
                      milliseconds does the cut take, and is what follows actually nothing.

  small-speaker RMS   The mixer's own measurement, reused: a 300 Hz / 12 dB-per-octave
                      high-pass standing in for a laptop. This score lives below 400 Hz by
                      rule, so it is the piece most at risk from it in the whole build, and
                      the gap between the two RMS columns is the size of that risk.

WHAT NONE OF IT ANSWERS is in NOTES.md, under "what needs a human ear".
"""
from __future__ import annotations

import argparse
import math
import wave
from pathlib import Path

import numpy as np

WINDOW: int = 4096
HOP: int = 4800                  # 100 ms at 48 kHz
BAND_LOW: float = 400.0
BAND_HIGH: float = 3000.0
SPEAKER_CORNER: float = 300.0    # the model in mixer.hammer's docstring
SPEAKER_SLOPE_DB: float = 12.0   # per octave


def read_wav(path: Path) -> tuple[np.ndarray, int]:
    """24-bit or 16-bit PCM to float in [-1, 1]."""
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
        packed[:, 1:] = b                       # shift up so the sign bit lands in int32
        data = np.frombuffer(packed.tobytes(), dtype="<i4").astype(np.float64) / 2147483648.0
    else:
        raise ValueError(f"{path}: {width * 8}-bit PCM not handled")
    return data.reshape(-1, channels), rate


def db(x: float) -> float:
    return 20.0 * math.log10(max(x, 1e-12))


class Frames:
    """One row per 100 ms of everything below. Plain arrays; nothing clever."""

    def __init__(self, mono: np.ndarray, rate: int) -> None:
        window = np.hanning(WINDOW)
        freqs = np.fft.rfftfreq(WINDOW, 1.0 / rate)
        in_band = (freqs >= BAND_LOW) & (freqs <= BAND_HIGH)
        # 12 dB/octave below 300 Hz, flat above: 10^(slope * log2(f / corner) / 20)
        octaves = np.where(freqs > 0.0,
                           np.log2(np.maximum(freqs, 1e-9) / SPEAKER_CORNER), -12.0)
        speaker = np.where(octaves >= 0.0, 1.0, 10.0 ** (SPEAKER_SLOPE_DB * octaves / 20.0))
        norm = float(np.sum(window * window)) * WINDOW      # Parseval, so band RMS ~ RMS

        rows: list[tuple[float, ...]] = []
        for start in range(0, len(mono) - WINDOW + 1, HOP):
            chunk = mono[start:start + WINDOW]
            power = np.abs(np.fft.rfft(chunk * window)) ** 2
            total = float(power.sum())
            if total > 0.0:
                cumulative = np.cumsum(power) / total
                f50 = float(freqs[int(np.searchsorted(cumulative, 0.50))])
                f85 = float(freqs[int(np.searchsorted(cumulative, 0.85))])
                centroid = float((freqs * power).sum() / total)
                frac = float(power[in_band].sum() / total)
                band = math.sqrt(2.0 * float(power[in_band].sum()) / norm)
                laptop = math.sqrt(2.0 * float((power * speaker * speaker).sum()) / norm)
            else:
                f50 = f85 = centroid = frac = band = laptop = 0.0
            rows.append(((start + WINDOW / 2) / rate,
                         float(np.sqrt(np.mean(chunk * chunk))),
                         f50, f85, centroid, frac, band, laptop))
        table = np.array(rows)
        (self.t, self.rms, self.f50, self.f85, self.centroid,
         self.frac, self.band_rms, self.laptop) = (table[:, i] for i in range(8))

    def span(self, values: np.ndarray, a: float, b: float) -> np.ndarray:
        return values[(self.t >= a) & (self.t < b)]


def structure_table(f: Frames, marks: list[tuple[str, float, float]]) -> list[str]:
    out = [f"{'passage':<24} {'t':>11} {'RMS dB':>7} {'peak dB':>8} {'F50':>5} {'F85':>5} "
           f"{'cent':>5} {'400-3k':>7} {'in-band dB':>11} {'laptop dB':>10}",
           "-" * 100]
    for name, a, b in marks:
        r = f.span(f.rms, a, b)
        if r.size == 0:
            continue
        out.append(
            f"{name:<24} {f'{a:.0f}-{b:.0f}s':>11} {db(float(r.mean())):7.1f} "
            f"{db(float(r.max())):8.1f} {float(f.span(f.f50, a, b).mean()):5.0f} "
            f"{float(f.span(f.f85, a, b).mean()):5.0f} "
            f"{float(f.span(f.centroid, a, b).mean()):5.0f} "
            f"{float(f.span(f.frac, a, b).mean()) * 100:6.3f}% "
            f"{db(float(f.span(f.band_rms, a, b).max())):11.1f} "
            f"{db(float(f.span(f.laptop, a, b).mean())):10.1f}")
    return out


def envelope_table(mono: np.ndarray, rate: int, a: float, b: float, step: float) -> list[str]:
    """Straight RMS in fixed windows, no FFT and no averaging of averages -- so a window
    that straddles the cut reads as what it is rather than as a fade."""
    out = [f"{'window':>14} {'RMS dB':>8}"]
    t = a
    while t < b - 1e-9:
        chunk = mono[int(t * rate):int(min(t + step, b) * rate)]
        if chunk.size:
            value = db(float(np.sqrt(np.mean(chunk * chunk))))
            out.append(f"{f'{t:6.1f}-{min(t + step, b):5.1f}':>14} {value:8.1f}")
        t += step
    return out


def stop_report(mono: np.ndarray, rate: int, stop_s: float) -> list[str]:
    out: list[str] = []
    step = int(0.005 * rate)                            # 5 ms
    out.append(f"{'t':>9} {'RMS dB (5 ms)':>15}")
    for offset_ms in (-500, -200, -100, -50, -20, -10, -5, 0, 5, 10, 20, 50, 200, 1000):
        centre = int((stop_s + offset_ms / 1000.0) * rate)
        chunk = mono[centre:centre + step]
        if chunk.size == 0:
            continue
        value = float(np.sqrt(np.mean(chunk * chunk)))
        out.append(f"{stop_s + offset_ms / 1000.0:9.3f} {db(value):15.1f}"
                   + ("   <- the cut" if offset_ms == 0 else ""))

    after = mono[int(stop_s * rate):]
    nonzero = np.nonzero(np.abs(after) > 0.0)[0]
    if nonzero.size == 0:
        out.append(f"\nafter {stop_s:.3f}s: {after.size} samples, all exactly zero "
                   f"({after.size / rate:.3f}s of digital silence)")
    else:
        last = (int(stop_s * rate) + int(nonzero[-1])) / rate
        peak = float(np.max(np.abs(after)))
        out.append(f"\nafter {stop_s:.3f}s: last non-zero sample at {last:.4f}s, "
                   f"peak {db(peak):.1f} dBFS "
                   f"(cut takes {(last - stop_s) * 1000:.1f} ms)")
    return out


def peak_table(mono: np.ndarray, rate: int, a: float, b: float, limit: float = 500.0,
               count: int = 10) -> list[str]:
    """The strongest components in one passage, which is how a harmonic event is checked.

    A register drop and a semitone move are claims about which frequencies are present, and
    that is the one musical question a measurement can answer outright: the descent should
    show D1/A1 where Act II showed D2/A2, and the fold should show E flat 1 with D1 still
    ringing under it rather than replaced by it.
    """
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
    return [f"{a:.1f}-{b:.1f}s, strongest components under {limit:.0f} Hz:",
            "  " + "   ".join(f"{freqs[i]:6.1f} Hz {db(spectrum[i] / top):+5.1f}"
                              for i in picked)]


def roughness(mono: np.ndarray, rate: int, a: float, b: float,
              band: float = 120.0) -> tuple[float, float]:
    """Peak amplitude-modulation rate under `band` Hz, and under 45 Hz.

    Two beats are expected in the fold and they are different sizes: the fundamentals D1 and
    E flat 1 are 2.18 Hz apart, which is a slow swell, and their upper partials are 15 to 18
    Hz apart, which is the roughness that makes a low semitone sound wrong rather than merely
    low. Reported separately because the second one is the audible half.
    """
    out: list[float] = []
    for limit in (band, 45.0):
        chunk = mono[int(a * rate):int(b * rate)]
        low = np.fft.irfft(np.fft.rfft(chunk)
                           * (np.fft.rfftfreq(len(chunk), 1.0 / rate) < limit))
        envelope = np.convolve(np.abs(low), np.ones(480) / 480.0, "same")[240:-240]
        envelope = envelope - envelope.mean()
        spectrum = np.abs(np.fft.rfft(envelope * np.hanning(len(envelope))))
        freqs = np.fft.rfftfreq(len(envelope), 1.0 / rate)
        window = (freqs > 0.5) & (freqs < 25.0)
        out.append(float(freqs[window][int(np.argmax(spectrum[window]))]))
    return out[0], out[1]


def slope_before(f: Frames, a: float, b: float) -> float:
    """dB per second over [a, b). A score that is already fading has a strongly negative
    slope here and the 'stop' is then only the end of a fade that started earlier."""
    mask = (f.t >= a) & (f.t < b)
    if mask.sum() < 3:
        return 0.0
    return float(np.polyfit(f.t[mask], np.array([db(v) for v in f.rms[mask]]), 1)[0])


def write_svg(path: Path, f: Frames, marks: list[tuple[str, float, float]],
              length: float) -> None:
    """No matplotlib in this venv and no new dependency for one picture."""
    w, h, pad = 1180.0, 460.0, 58.0
    plot_w = w - 2 * pad
    plot_h = (h - 2 * pad) / 2.0 - 16.0
    top_a, top_b = pad + 6.0, pad + plot_h + 52.0

    def x_of(t: float) -> float:
        return pad + plot_w * t / length

    def y_rms(v: float) -> float:
        return top_a + plot_h * (1.0 - (max(db(v), -90.0) + 90.0) / 90.0)

    def y_hz(v: float) -> float:
        return top_b + plot_h * (1.0 - min(v, 400.0) / 400.0)

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:.0f}" height="{h:.0f}" '
             f'viewBox="0 0 {w:.0f} {h:.0f}" font-family="monospace" font-size="11">',
             f'<rect width="{w:.0f}" height="{h:.0f}" fill="#0d0f11"/>']
    for name, a, _ in marks:
        parts.append(f'<line x1="{x_of(a):.1f}" y1="{pad - 6:.1f}" x2="{x_of(a):.1f}" '
                     f'y2="{h - pad + 10:.1f}" stroke="#2f363d" stroke-width="1"/>')
        parts.append(f'<text x="{x_of(a) + 4:.1f}" y="{pad - 12:.1f}" fill="#7c8892">'
                     f'{name}</text>')
    parts.append(f'<text x="{pad:.1f}" y="{top_a - 4:.1f}" fill="#9aa5ae">'
                 f'RMS dBFS, 100 ms windows  (-90 at the floor, 0 at the top)</text>')
    parts.append(f'<text x="{pad:.1f}" y="{top_b - 6:.1f}" fill="#9aa5ae">'
                 f'F50 (solid) and F85 (faint), Hz  (0 .. 400) - where the power is</text>')
    sounding = f.rms > 1e-6
    for values, colour, width, y_of in ((f.rms, "#e0b95a", 1.5, y_rms),
                                        (f.f85, "#3d6f8e", 1.2, y_hz),
                                        (f.f50, "#5fa8d3", 1.6, y_hz)):
        points = " ".join(f"{x_of(t):.1f},{y_of(v):.1f}"
                          for t, v, on in zip(f.t, values, sounding)
                          if on or y_of is y_rms)
        parts.append(f'<polyline points="{points}" fill="none" stroke="{colour}" '
                     f'stroke-width="{width}"/>')
    for t in range(0, int(length) + 1, 10):
        parts.append(f'<text x="{x_of(t):.1f}" y="{h - pad + 26:.1f}" fill="#7c8892" '
                     f'text-anchor="middle">{t // 60}:{t % 60:02d}</text>')
    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("wav")
    parser.add_argument("--stop", type=float, default=61.0)
    parser.add_argument("--svg", default=None)
    parser.add_argument("--envelope", action="store_true",
                        help="RMS every 2.5 s across the sounding part of the piece")
    parser.add_argument("--harmony", action="store_true",
                        help="the components in each passage, and the fold's beat rates")
    args = parser.parse_args()

    path = Path(args.wav)
    stereo, rate = read_wav(path)
    mono = stereo.mean(axis=1)
    length = stereo.shape[0] / rate
    print(f"{path.name}: {stereo.shape[0]} frames, {stereo.shape[1]} ch, {rate} Hz, "
          f"{length:.3f}s, peak {db(float(np.max(np.abs(stereo)))):.1f} dBFS")
    correlation = (float(np.corrcoef(stereo[:, 0], stereo[:, 1])[0, 1])
                   if stereo.shape[0] > 1 else 1.0)
    print(f"  L/R correlation {correlation:+.3f} "
          f"(1.0 would mean the stereo field is doing nothing)")

    f = Frames(mono, rate)
    marks = [("naked", 0.0, 5.0), ("I  the place", 5.0, 26.0),
             ("II  the teaching", 26.0, 50.0), ("III descent", 50.0, 57.0),
             ("III fold", 57.0, 61.0), ("IV-VI  gone", 61.0, length)]
    marks = [(n, a, b) for n, a, b in marks if a < length]
    print()
    for line in structure_table(f, marks):
        print(line)

    print(f"\nwhole piece: 400-3000 Hz is {float(np.max(f.frac)) * 100:.3f}% of power at "
          f"worst, {db(float(np.max(f.band_rms))):.1f} dBFS at worst "
          f"(a routine heard ping is -18 dBFS)")

    if args.envelope:
        print()
        for line in envelope_table(mono, rate, 0.0, min(length, args.stop + 2.0), 2.5):
            print(line)

    if args.harmony:
        for name, a, b in (("II   the teaching", 42.0, 48.0),
                           ("III  the descent", 51.0, 56.0),
                           ("III  the fold", 57.5, 60.5)):
            if b > length:
                continue
            print()
            print(name)
            for line in peak_table(mono, rate, a, b):
                print("  " + line)
        if length > 61.0:
            wide, low = roughness(mono, rate, 57.2, 61.0)
            print(f"\nfold beat rates: {wide:.2f} Hz under 120 Hz (the partials, roughness), "
                  f"{low:.2f} Hz under 45 Hz (the fundamentals, a slow swell)")

    if args.stop < length:
        print(f"\nlevel slope over the three seconds before the cut: "
              f"{slope_before(f, args.stop - 3.0, args.stop):+.2f} dB/s "
              f"(a fade would be strongly negative)")
        print("\n" + "\n".join(envelope_table(mono, rate, args.stop - 3.0, args.stop, 0.5)))
        print()
        for line in stop_report(mono, rate, args.stop):
            print(line)

    if args.svg:
        write_svg(Path(args.svg), f, marks, length)
        print(f"\nwrote {args.svg}")


if __name__ == "__main__":
    main()
