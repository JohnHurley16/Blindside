"""Directional audio, driven entirely from Belief.

The spec is blunt that sound is not optional here: the game is about acoustics, and a
panned tone probably carries more tension than any visual. So a contact is audible,
it comes from a bearing, and it has a character -- a sharp transient, a low scrape, a
rising drone -- because those are properties of the signal the agent received.

What it deliberately does NOT do is distinguish an honest fix from a lie. Both play
the same two notes. The only tell is how far the estimate moved.
"""
from __future__ import annotations

import math
import threading

import numpy as np

from ..belief.belief import Belief
from ..sound_character import SoundCharacter
from .voice import SAMPLE_RATE, Voice
from .waveform import Waveform

MAX_VOICES: int = 24


class Mixer:
    """A numpy mixer behind a sounddevice callback. Runs silent if there is no device."""

    def __init__(self, blocksize: int = 1024) -> None:
        self.voices: list[Voice] = []
        self.lock: threading.Lock = threading.Lock()
        self.ok: bool = False
        self.stream: object | None = None
        try:
            import sounddevice as sd
            self.stream = sd.OutputStream(samplerate=SAMPLE_RATE, channels=2,
                                          blocksize=blocksize, dtype="float32",
                                          callback=self._callback)
            self.stream.start()          # type: ignore[union-attr]
            self.ok = True
        except Exception as exc:                       # noqa: BLE001 - any device failure
            print(f"audio: running silent ({exc})")

        # cursors into the Belief streams
        self._seen_contacts: dict[int, float] = {}
        self._n_own_pings: int = 0
        self._n_heard: int = 0
        self._n_fixes: int = 0
        self._n_log: int = 0
        self._next_signature_pulse: float = 0.0
        self._last_cargo: int = 0

    # ---- device ----------------------------------------------------------------------
    def _callback(self, out: np.ndarray, frames: int, time_info: object, status: object) -> None:
        buf = np.zeros((frames, 2), dtype=np.float64)
        with self.lock:
            for v in self.voices:
                v.render(buf)
            self.voices = [v for v in self.voices if not v.done]
        out[:] = np.clip(buf, -1.0, 1.0).astype(np.float32)

    def play(self, waveform: Waveform, f0: float, f1: float, duration: float,
             amplitude: float, pan: float, attack: float = 0.006,
             decay: float | None = None) -> None:
        if not self.ok:
            return
        with self.lock:
            if len(self.voices) < MAX_VOICES:
                self.voices.append(Voice(waveform, f0, f1, duration, amplitude, pan, attack, decay))

    def render_offline(self, seconds: float) -> np.ndarray:
        """Mix the queued voices to an array, for testing without a device."""
        buf = np.zeros((int(seconds * SAMPLE_RATE), 2))
        with self.lock:
            for v in self.voices:
                v.render(buf)
            self.voices = [v for v in self.voices if not v.done]
        return buf

    def close(self) -> None:
        if self.stream is not None:
            try:
                self.stream.stop()       # type: ignore[union-attr]
                self.stream.close()      # type: ignore[union-attr]
            except Exception:            # noqa: BLE001
                pass

    # ---- sound design -------------------------------------------------------------------
    @staticmethod
    def pan_for(bearing: float, camera_azimuth_deg: float) -> float:
        """Screen-relative pan, so what looks right sounds right as the camera orbits."""
        return math.cos(bearing + math.radians(camera_azimuth_deg))

    def own_ping(self) -> None:
        self.play(Waveform.SINE, 1500, 650, 0.55, 0.35, 0.0, decay=0.4)

    def heard_ping(self, bearing: float, quality: float, az: float) -> None:
        pan = self.pan_for(bearing, az)
        self.play(Waveform.SINE, 950, 520, 0.4, 0.4 * (0.25 + 0.75 * quality), pan, decay=0.3)
        self.play(Waveform.SINE, 1900, 1040, 0.2, 0.12 * quality, pan)

    def motion_contact(self, bearing: float, quality: float, az: float) -> None:
        pan = self.pan_for(bearing, az)
        self.play(Waveform.SAW, 140 + 90 * quality, 120 + 80 * quality, 0.16,
                  0.22 * (0.3 + 0.7 * quality), pan, decay=0.1)

    def crash(self, bearing: float, quality: float, az: float) -> None:
        pan = self.pan_for(bearing, az)
        self.play(Waveform.NOISE, 0, 0, 0.9, 0.5 * (0.4 + 0.6 * quality), pan, decay=0.7)
        self.play(Waveform.SINE, 90, 35, 1.2, 0.5 * (0.4 + 0.6 * quality), pan, decay=0.9)

    def signature_pulse(self, bearing: float, strength: float, az: float) -> None:
        """Pulses faster and rises in pitch as the machinery approaches lethal. That
        acceleration is the warning, and it is the reason the signature is legible
        before it is dangerous rather than merely present."""
        pan = self.pan_for(bearing, az)
        self.play(Waveform.SINE, 70 + 40 * strength, 55, 0.12, 0.45 * (0.3 + 0.7 * strength), pan, decay=0.08)
        self.play(Waveform.SQUARE, 220 + 300 * strength, 220 + 300 * strength, 0.05, 0.08 * strength, pan)

    def fix(self) -> None:
        self.play(Waveform.SINE, 660, 660, 0.1, 0.25, 0.0)
        self.play(Waveform.SINE, 990, 990, 0.14, 0.25, 0.0, attack=0.1)

    def recall_sent(self) -> None:
        for i in range(3):
            self.play(Waveform.SQUARE, 520, 520, 0.08, 0.15, 0.0, attack=0.001 + 0.12 * i)

    def recall_received(self) -> None:
        self.play(Waveform.SINE, 780, 780, 0.25, 0.3, 0.0)

    def cargo_changed(self) -> None:
        self.play(Waveform.SINE, 1200, 1200, 0.06, 0.2, 0.0)
        self.play(Waveform.SINE, 1600, 1600, 0.08, 0.2, 0.0, attack=0.08)

    # ---- per frame ---------------------------------------------------------------------
    def update(self, b: Belief, t: float, camera_azimuth: float = 0.0) -> None:
        for contact in b.contacts:
            key = id(contact)
            if self._seen_contacts.get(key) != contact.t_last:
                self._seen_contacts[key] = contact.t_last
                if contact.character is SoundCharacter.TONE:
                    self.motion_contact(contact.bearing, contact.quality, camera_azimuth)

        if len(b.own_pings) > self._n_own_pings:
            self._n_own_pings = len(b.own_pings)
            self.own_ping()

        while self._n_heard < len(b.heard):
            sound = b.heard[self._n_heard]
            self._n_heard += 1
            if sound.character is SoundCharacter.PING:
                self.heard_ping(sound.bearing, sound.quality, camera_azimuth)
            elif sound.character is SoundCharacter.CRASH:
                self.crash(sound.bearing, sound.quality, camera_azimuth)

        while self._n_fixes < len(b.fixes):
            self._n_fixes += 1
            self.fix()

        sig = b.signature
        if sig is not None and t - sig.t < 0.6 and t >= self._next_signature_pulse:
            self._next_signature_pulse = t + 1.0 / (1.2 + 7.0 * sig.quality)
            self.signature_pulse(sig.bearing, sig.quality, camera_azimuth)

        if b.cargo != self._last_cargo:
            self._last_cargo = b.cargo
            self.cargo_changed()

        while self._n_log < len(b.log):
            _, text = b.log[self._n_log]
            self._n_log += 1
            if text.startswith("RECALL received"):
                self.recall_received()
