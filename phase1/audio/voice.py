"""One sounding note, rendered into a stereo buffer."""
from __future__ import annotations

import sys

import numpy as np

from .envelope import Envelope
from .envelope_shape import EnvelopeShape
from .waveform import Waveform

SAMPLE_RATE: int = 44100
_PARTIAL_FLOOR: float = 0.02   # below this a partial is inaudible and only costs a transcendental


def set_sample_rate(rate: int) -> None:
    """Rebind the engine's rate. Call before any `Voice` exists; the game never calls it.

    The game runs at 44.1 kHz because that is the rate the device is opened at. Video wants
    48 kHz, and the trailer's score stem is rendered offline for an editor -- so it is
    synthesised at 48 rather than resampled to it, which is a conversion no code here would
    have to be trusted to do. Nothing about the sound changes: every frequency in this
    package is in Hz and every duration is in seconds. The one thing that does change is the
    corner of `_noise`'s moving average, which is a fraction of the rate (0.44 * rate /
    width) and therefore moves up with it; `Score.band_report` computes that corner at the
    score's own rate rather than assuming 44.1.

    Every consumer reads the module global at call time, except the two that imported the
    constant by name, so those are rebound here. Written as one function rather than left to
    a caller poking module attributes, because a rate change that is invisible in this
    package is a rate change nobody will find. See `spikes/score/NOTES.md`.
    """
    global SAMPLE_RATE
    SAMPLE_RATE = int(rate)
    for name in ("phase1.audio.mixer", "phase1.view.recorder"):
        module = sys.modules.get(name)
        if module is not None:
            module.SAMPLE_RATE = SAMPLE_RATE


class Voice:
    """A swept oscillator with a partial stack, an envelope, a delay and a constant pan.

    Pan is equal-power, so a contact swinging across the stereo field does not dip in the
    middle. Everything a voice knows came from Belief, which is why a contact can be heard
    from a bearing that is wrong.

    Two things were added when the sound stopped being only beeps.

    `partials` is the brightness channel. A far sound is a fundamental; a near one carries
    its harmonics. Doing it additively rather than with a filter is the reason a spectral
    distance cue costs nothing here -- no filter state, no convolution, no dependency
    beyond numpy.

    `delay` is the room. A cave delivers a sound twice, down two passages, at two delays
    from two directions, and three delayed voices are a truer cave than any reverb this
    phase could afford.

    The whole waveform is built once, at construction, into a mono float32 array; `render`
    is then a slice and two multiply-adds. That trades a bounded one-off cost for having no
    per-block oscillator, filter or envelope state at all, which is what makes the delay
    and the noise band exact rather than approximate across block boundaries.
    """

    def __init__(self, waveform: Waveform, f0: float, f1: float, duration: float,
                 amplitude: float, pan: float, attack: float = 0.006,
                 decay: float | None = None, seed: int = 1,
                 delay: float = 0.0, shape: EnvelopeShape = EnvelopeShape.LINEAR,
                 partials: tuple[tuple[float, float], ...] = ((1.0, 1.0),),
                 lowpass: int = 1, highpass: int = 0) -> None:
        self.waveform: Waveform = waveform
        self.duration: float = duration
        self.amplitude: float = amplitude
        self.pan: float = max(-1.0, min(1.0, pan))
        self.offset: int = max(0, int(delay * SAMPLE_RATE))
        self.pos: int = 0
        self.done: bool = False
        self.rng: np.random.Generator = np.random.default_rng(seed)

        n = max(1, int(duration * SAMPLE_RATE))
        t = (np.arange(n, dtype=np.float32) / SAMPLE_RATE)
        if waveform is Waveform.NOISE:
            sig = self._noise(n, lowpass, highpass)
        else:
            sig = self._tonal(waveform, f0, f1, n, partials)
        decay_s = decay if decay is not None else duration * 0.6
        env = Envelope(attack, decay_s, shape).curve(t, duration)
        angle = (self.pan + 1.0) * np.pi / 4.0
        self.sig: np.ndarray = sig * env * np.float32(amplitude)
        self.gl: float = float(np.cos(angle))
        self.gr: float = float(np.sin(angle))

    # ---- synthesis ---------------------------------------------------------------------
    @staticmethod
    def _tonal(waveform: Waveform, f0: float, f1: float, n: int,
               partials: tuple[tuple[float, float], ...]) -> np.ndarray:
        """A linear sweep has a closed-form phase, so there is no cumulative sum and no
        per-block oscillator state:

            phase(i) = 2*pi/SR * (f0*i + (f1 - f0) * i^2 / (2 * (n-1)))

        Accumulated in float64 -- i^2 reaches 1e10 and would lose every significant digit
        in float32 -- and then dropped to float32 for the transcendental, which is where
        all the time goes and which is twice as fast at single precision. Measured: a
        2.4 s four-partial tail fell from 8.5 ms to 2.1 ms, and that matters because these
        are built on the game thread, inside a frame.
        """
        i = np.arange(n, dtype=np.float64)
        k = 2.0 * np.pi / SAMPLE_RATE
        phase = (k * f0) * i + (k * (f1 - f0) / (2.0 * max(n - 1, 1))) * (i * i)
        base = phase.astype(np.float32)
        out = np.zeros(n, dtype=np.float32)
        for ratio, gain in partials:
            if gain < _PARTIAL_FLOOR:
                continue
            p = base * np.float32(ratio)
            if waveform is Waveform.SAW:
                out += np.float32(gain) * (2.0 * ((p / np.float32(2.0 * np.pi)) % 1.0) - 1.0)
            elif waveform is Waveform.SQUARE:
                out += np.float32(gain) * np.sign(np.sin(p))
            else:
                out += np.float32(gain) * np.sin(p)
        return out

    def _noise(self, n: int, lowpass: int, highpass: int) -> np.ndarray:
        """Band-limited noise by moving average, which is a real low-pass and costs one
        cumulative sum. Width w cuts at roughly 0.44 * SAMPLE_RATE / w, so w=3 is a crack
        and w=74 is a rumble. Subtracting a wider average is a crude high-pass, which is
        what keeps a scrape out of the machinery's register."""
        span = max(lowpass, highpass) + 1
        raw = self.rng.random(n + span, dtype=np.float32) * np.float32(2.0) - np.float32(1.0)
        band = self._smooth(raw, lowpass, n)
        if highpass > 1:
            band = band - self._smooth(raw, highpass, n)
        peak = float(np.max(np.abs(band))) if band.size else 0.0
        return band / np.float32(peak) if peak > 0.0 else band

    @staticmethod
    def _smooth(raw: np.ndarray, width: int, n: int) -> np.ndarray:
        if width <= 1:
            return raw[:n].copy()
        c = np.concatenate((np.zeros(1, dtype=np.float32), np.cumsum(raw, dtype=np.float32)))
        return (c[width:width + n] - c[:n]) / np.float32(width)

    # ---- playback ----------------------------------------------------------------------
    def render(self, buf: np.ndarray) -> None:
        n = len(buf)
        start = self.pos
        self.pos += n
        if start + n <= self.offset:
            return                                   # still on its way down the passage
        if start >= self.offset + len(self.sig):
            self.done = True
            return
        lo = max(0, self.offset - start)
        src = max(0, start - self.offset)
        count = min(n - lo, len(self.sig) - src)
        seg = self.sig[src:src + count]
        buf[lo:lo + count, 0] += seg * self.gl
        buf[lo:lo + count, 1] += seg * self.gr
        if src + count >= len(self.sig):
            self.done = True

    def duck(self, target: float, ramp: float) -> None:
        """Pull the rest of this voice down. A near hull failure masks what is under it,
        so a crash says so rather than merely being 3 dB louder than a beep."""
        i = max(0, self.pos - self.offset)
        if i >= len(self.sig):
            return
        k = min(max(1, int(ramp * SAMPLE_RATE)), len(self.sig) - i)
        self.sig[i:i + k] *= np.linspace(1.0, target, k, dtype=np.float32)
        self.sig[i + k:] *= target
