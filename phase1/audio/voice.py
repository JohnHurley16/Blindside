"""One sounding note, rendered into a stereo buffer."""
from __future__ import annotations

import numpy as np

from .waveform import Waveform

SAMPLE_RATE: int = 44100


class Voice:
    """A swept oscillator with an envelope and a constant pan.

    Pan is equal-power, so a contact swinging across the stereo field does not dip in
    the middle. Everything a voice knows came from Belief, which is why a contact can
    be heard from a bearing that is wrong.
    """

    def __init__(self, waveform: Waveform, f0: float, f1: float, duration: float,
                 amplitude: float, pan: float, attack: float = 0.006,
                 decay: float | None = None, seed: int = 1) -> None:
        self.waveform: Waveform = waveform
        self.f0: float = f0
        self.f1: float = f1
        self.duration: float = duration
        self.amplitude: float = amplitude
        self.pan: float = max(-1.0, min(1.0, pan))
        self.attack: float = attack
        self.decay: float = decay if decay is not None else duration * 0.6
        self.pos: int = 0
        self.phase: float = 0.0
        self.done: bool = False
        self.rng: np.random.Generator = np.random.default_rng(seed)

    def render(self, buf: np.ndarray) -> None:
        n = len(buf)
        t = (np.arange(n) + self.pos) / SAMPLE_RATE
        if t[0] >= self.duration:
            self.done = True
            return
        frac = np.clip(t / self.duration, 0.0, 1.0)
        freq = self.f0 + (self.f1 - self.f0) * frac
        if self.waveform is Waveform.NOISE:
            sig = self.rng.uniform(-1.0, 1.0, n)
        else:
            phase = self.phase + 2 * np.pi * np.cumsum(freq) / SAMPLE_RATE
            self.phase = float(phase[-1] % (2 * np.pi))
            if self.waveform is Waveform.SAW:
                sig = 2.0 * ((phase / (2 * np.pi)) % 1.0) - 1.0
            elif self.waveform is Waveform.SQUARE:
                sig = np.sign(np.sin(phase))
            else:
                sig = np.sin(phase)
        env = np.clip(t / self.attack, 0.0, 1.0) * np.clip((self.duration - t) / self.decay, 0.0, 1.0)
        sig = sig * env * self.amplitude
        angle = (self.pan + 1.0) * np.pi / 4.0
        buf[:, 0] += sig * np.cos(angle)
        buf[:, 1] += sig * np.sin(angle)
        self.pos += n
