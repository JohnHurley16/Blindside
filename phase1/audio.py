"""Directional audio from Belief. A tiny numpy mixer behind a sounddevice callback.

Pan is screen-relative: a bearing to the right of the screen is in the right ear.
Everything here is derived from Belief streams; it never sees World.
"""
import math
import threading
import numpy as np
from . import tuning as T

SR = 44100


class Voice:
    def __init__(self, kind, f0, f1, dur, amp, pan, attack=0.006, decay=None):
        self.kind, self.f0, self.f1, self.dur, self.amp = kind, f0, f1, dur, amp
        self.pan = max(-1.0, min(1.0, pan))
        self.attack = attack
        self.decay = decay if decay is not None else dur * 0.6
        self.pos = 0
        self.phase = 0.0
        self.done = False
        self.rng = np.random.default_rng(1)

    def render(self, buf):
        n = len(buf)
        tt = (np.arange(n) + self.pos) / SR
        if tt[0] >= self.dur:
            self.done = True
            return
        frac = np.clip(tt / self.dur, 0, 1)
        f = self.f0 + (self.f1 - self.f0) * frac
        if self.kind == "noise":
            sig = self.rng.uniform(-1, 1, n)
        else:
            ph = self.phase + 2 * np.pi * np.cumsum(f) / SR
            self.phase = ph[-1] % (2 * np.pi)
            if self.kind == "saw":
                sig = 2 * ((ph / (2 * np.pi)) % 1.0) - 1
            elif self.kind == "square":
                sig = np.sign(np.sin(ph))
            else:
                sig = np.sin(ph)
        env = np.clip(tt / self.attack, 0, 1) * np.clip((self.dur - tt) / self.decay, 0, 1)
        sig = sig * env * self.amp
        th = (self.pan + 1) * np.pi / 4
        buf[:, 0] += sig * np.cos(th)
        buf[:, 1] += sig * np.sin(th)
        self.pos += n


class Audio:
    def __init__(self):
        self.voices = []
        self.lock = threading.Lock()
        self.ok = False
        self.stream = None
        try:
            import sounddevice as sd
            self.stream = sd.OutputStream(samplerate=SR, channels=2, blocksize=1024, dtype="float32", callback=self._cb)
            self.stream.start()
            self.ok = True
        except Exception as e:
            print(f"audio: running silent ({e})")
        # stream cursors into Belief
        self.seen_contacts = {}
        self.n_own = 0; self.n_heard = 0; self.n_crash = 0; self.n_fix = 0; self.n_log = 0
        self.next_sig_pulse = 0.0
        self.last_cargo = 0
        self.dead_played = False

    def _cb(self, out, frames, time_info, status):
        buf = np.zeros((frames, 2), dtype=np.float64)
        with self.lock:
            for v in self.voices:
                v.render(buf)
            self.voices = [v for v in self.voices if not v.done]
        out[:] = np.clip(buf, -1, 1).astype(np.float32)

    def play(self, *a, **k):
        if not self.ok:
            return
        with self.lock:
            if len(self.voices) < 24:
                self.voices.append(Voice(*a, **k))

    def render_offline(self, seconds):
        """For testing without a device: mix the current voices to an array."""
        buf = np.zeros((int(seconds * SR), 2))
        with self.lock:
            for v in self.voices:
                v.render(buf)
            self.voices = [v for v in self.voices if not v.done]
        return buf

    # ---- sound design -------------------------------------------------------------------
    @staticmethod
    def _pan(bearing, cam_az_deg):
        # screen right = world +x rotated by the camera azimuth
        return math.cos(bearing + math.radians(cam_az_deg))

    def own_ping(self):
        self.play("sine", 1500, 650, 0.55, 0.35, 0.0, decay=0.4)

    def heard_ping(self, bearing, q, az):
        p = self._pan(bearing, az)
        self.play("sine", 950, 520, 0.4, 0.4 * (0.25 + 0.75 * q), p, decay=0.3)
        self.play("sine", 1900, 1040, 0.2, 0.12 * q, p)

    def motion_contact(self, bearing, q, az):
        p = self._pan(bearing, az)
        self.play("saw", 140 + 90 * q, 120 + 80 * q, 0.16, 0.22 * (0.3 + 0.7 * q), p, decay=0.1)

    def crash(self, bearing, q, az):
        p = self._pan(bearing, az)
        self.play("noise", 0, 0, 0.9, 0.5 * (0.4 + 0.6 * q), p, decay=0.7)
        self.play("sine", 90, 35, 1.2, 0.5 * (0.4 + 0.6 * q), p, decay=0.9)

    def signature_pulse(self, bearing, s, az):
        p = self._pan(bearing, az)
        self.play("sine", 70 + 40 * s, 55, 0.12, 0.45 * (0.3 + 0.7 * s), p, decay=0.08)
        self.play("square", 220 + 300 * s, 220 + 300 * s, 0.05, 0.08 * s, p)

    def fix(self, jump):
        # identical for an honest fix and a lie. The size of the jump is the only tell.
        self.play("sine", 660, 660, 0.1, 0.25, 0.0)
        self.play("sine", 990, 990, 0.14, 0.25, 0.0, attack=0.1)

    def recall_sent(self):
        for i in range(3):
            self.play("square", 520, 520, 0.08, 0.15, 0.0, attack=0.001 + 0.12 * i)

    def recall_received(self):
        self.play("sine", 780, 780, 0.25, 0.3, 0.0)

    def cargo(self):
        self.play("sine", 1200, 1200, 0.06, 0.2, 0.0); self.play("sine", 1600, 1600, 0.08, 0.2, 0.0, attack=0.08)

    def own_lost(self):
        self.play("saw", 300, 40, 1.6, 0.45, 0.0, decay=1.2)

    # ---- per frame ------------------------------------------------------------------------
    def update(self, b, t, cam_az=0.0):
        for c in b.contacts:
            key = id(c)
            last = self.seen_contacts.get(key)
            if last != c["t_last"]:
                self.seen_contacts[key] = c["t_last"]
                if c["kind"] == "tone":
                    self.motion_contact(c["bearing"], c["quality"], cam_az)
        if len(b.own_pings) > self.n_own:
            self.n_own = len(b.own_pings); self.own_ping()
        while self.n_heard < len(b.heard_pings):
            _, bw, q = b.heard_pings[self.n_heard]; self.n_heard += 1
            self.heard_ping(bw, q, cam_az)
        while self.n_crash < len(b.crashes):
            _, bw, q = b.crashes[self.n_crash]; self.n_crash += 1
            self.crash(bw, q, cam_az)
        while self.n_fix < len(b.fix_events):
            ev = b.fix_events[self.n_fix]; self.n_fix += 1
            self.fix(math.hypot(ev[3] - ev[1], ev[4] - ev[2]))
        sig = b.signature
        if sig and t - sig["t"] < 0.6 and t >= self.next_sig_pulse:
            s = sig["strength"]
            self.next_sig_pulse = t + 1.0 / (1.2 + 7.0 * s)
            self.signature_pulse(sig["bearing"], s, cam_az)
        if b.cargo != self.last_cargo:
            self.last_cargo = b.cargo; self.cargo()
        while self.n_log < len(b.log):
            _, txt = b.log[self.n_log]; self.n_log += 1
            if txt.startswith("RECALL received"):
                self.recall_received()

    def close(self):
        if self.stream:
            try:
                self.stream.stop(); self.stream.close()
            except Exception:
                pass
