"""Directional audio, driven entirely from Belief.

The spec is blunt that sound is not optional here: the game is about acoustics, and a
panned tone probably carries more tension than any visual. So a contact is audible, it
comes from a bearing, and it has a character -- a sharp transient, a low scrape, a rising
drone -- because those are properties of the signal the agent received.

What it deliberately does NOT do is distinguish an honest fix from a lie. Both play the
same two notes. The only tell is how far the estimate moved.

---

The gate failed on "all that changes is things kinda beep and nothing really is obvious",
and a tick-by-tick replay agreed: 587 audible events in a match, 80% of them one of two
recipes, all nine recipes built from the same 6 ms attack and linear fade, none filtered,
none modulated by anything but a volume multiplier. **Amplitude was the only channel in
use**, and amplitude alone cannot say far, near, closing, mine, theirs, winding up or
dead. The rest of this file is the argument that those are six different things and ought
to be six different sounds.

  DISTANCE   Five cues off one number. `Placement` owns four of them -- level,
             brightness, attack softening, and how much of what you hear is the cave
             rather than the thing -- and a heard ping's base pitch is the fifth. A far
             sound is dull, smeared, low, wide and mostly reverberation. It is not a near
             sound with the volume down.

  WHOSE      The own ping is the only RISING sweep in the game, the only hard-centred
             world sound, and the only one the room answers afterwards -- which is what a
             sonar transmission physically is. A heard ping falls, is panned, and arrives
             already reverberant. Three orthogonal cues, not a fifth and a pan.

  APPROACH   An EVENT, not a parameter. A contact that has closed materially since the
             last time that bearing spoke answers itself a fifth of a second later, a
             fifth higher and louder: one transmission, two notes, stepping up. It used
             to be a drift -- base pitch rising with proximity, a median of 0.20 semitones
             between consecutive transmissions, 0.057 semitones a second -- which is the
             same failure this rework diagnosed in the old mixer, moved to a better
             channel. Base pitch is still proximity; it is filed under DISTANCE, where it
             belongs, and it is not asked to carry approach on its own.

  THREAT     `Ratchet`. A countable train that accelerates and climbs, a held breath, then
             the hammer. See that file: the old pulse train stopped accelerating at the
             instant the hazard became lethal. The climb lives in the pawl's RING, not in
             its body, because the body is at 84-188 Hz and a laptop speaker does not have
             those notes.

  DEATH      A crash ducks everything sounding to a tenth and forbids any routine gesture
             from starting until it has spoken. It is the only sound with debris, the only
             downward saw, and by far the longest.

  SILENCE    One transmission is one gesture (see `Tracker`); before, one rival ping was
             six beeps. No ambience is added anywhere -- a bored viewer is not fixed by a
             drone -- and the loudest moment of the match has three quarters of a second of
             nothing in front of it, which `update` now enforces rather than assumes.

  REGISTER   Every sound that has to be identified carries its weight above 300 Hz,
             because the gate is a human watching a video on a laptop and a laptop speaker
             is a 300 Hz / 12 dB-per-octave high-pass. The first rework failed this on the
             two biggest sounds in the match and that is very probably what the gate
             heard: nothing. See the register rule in `tuning.py`.

  NOT HERE   FRONT AND BACK. Pan is one axis, north folds onto south, and the screen-y
             tilt that used to pretend otherwise measured 1.74 dB against the 20 dB
             distance owns on the same channel -- so it was inaudible as direction and
             audible as distance. Deleted, not weakened. Nothing in this file tells a
             due-north contact from a due-south one.
"""
from __future__ import annotations

import threading

import numpy as np

from .. import geometry as G
from .. import tuning as T
from ..belief.belief import Belief
from ..sound_character import SoundCharacter
from .envelope_shape import EnvelopeShape
from .placement import Placement
from .ratchet import HAMMER, NOTCH, Ratchet
from .tracker import Tracker
from . import voice as _voice
from .voice import Voice
from .waveform import Waveform

MAX_VOICES: int = T.AUDIO_MAX_VOICES


class Mixer:
    """A numpy mixer behind a sounddevice callback. Runs silent if there is no device."""

    def __init__(self, blocksize: int = 1024, offline: bool = False) -> None:
        """offline=True queues voices without opening a device, so a recording can pull
        the mix out frame by frame with `render_offline` and end up in sync.

        Both paths render the identical stereo buffer through `Voice.render`; the only
        difference is who owns the clock. Everything below -- pan, delayed reflections,
        ducking -- therefore behaves the same live as it does in the offline render the
        gate video was made from.
        """
        self.voices: list[Voice] = []
        self.lock: threading.Lock = threading.Lock()
        self.ok: bool = False
        self.offline: bool = offline
        self.stream: object | None = None

        # cursors into the Belief streams, set before any early return
        self._seen_contacts: dict[int, float] = {}
        self._n_own_pings: int = 0
        self._n_heard: int = 0
        self._n_fixes: int = 0
        self._n_log: int = 0
        self._last_cargo: int = 0
        self._seed: int = 1

        # what the sound design has to remember
        self._tracker: Tracker = Tracker()
        self._ratchet: Ratchet = Ratchet()
        self._last_signature_t: float = -1.0
        self._signature_bearing: float = 0.0
        self._signature_quality: float = 0.0
        self._quiet_until: float = -1.0        # nothing routine starts before this
        self._breathing: bool = False          # the ratchet is topped out and holding

        if offline:
            self.ok = True
            return
        try:
            import sounddevice as sd
            self.stream = sd.OutputStream(samplerate=_voice.SAMPLE_RATE, channels=2,
                                          blocksize=blocksize, dtype="float32",
                                          callback=self._callback)
            self.stream.start()          # type: ignore[union-attr]
            self.ok = True
        except Exception as exc:                       # noqa: BLE001 - any device failure
            print(f"audio: running silent ({exc})")

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
             decay: float | None = None, delay: float = 0.0,
             shape: EnvelopeShape = EnvelopeShape.LINEAR,
             partials: tuple[tuple[float, float], ...] = ((1.0, 1.0),),
             lowpass: int = 1, highpass: int = 0, priority: bool = False) -> None:
        """Queue one voice. Built outside the lock, because a voice is now synthesised at
        construction and the audio callback must never wait on that."""
        if not self.ok or duration <= 0.0 or amplitude <= 0.0005:
            return
        self._seed += 1
        voice = Voice(waveform, f0, f1, duration, amplitude, pan, attack, decay,
                      self._seed, delay, shape, partials, lowpass, highpass)
        with self.lock:
            if len(self.voices) >= MAX_VOICES:
                if not priority:
                    return
                self.voices.pop(0)         # a death may always take a slot from a beep
            self.voices.append(voice)

    def render_offline(self, seconds: float) -> np.ndarray:
        """Mix the queued voices to an array, for testing without a device."""
        buf = np.zeros((int(seconds * _voice.SAMPLE_RATE), 2))
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

    def duck(self, target: float, ramp: float) -> None:
        with self.lock:
            for v in self.voices:
                v.duck(target, ramp)

    # ---- the room -----------------------------------------------------------------------
    @staticmethod
    def pan_for(bearing: float, camera_azimuth_deg: float) -> float:
        """Kept as the mixer's public name for it; the argument is in `Placement`."""
        return Placement.pan_for(bearing, camera_azimuth_deg)

    @staticmethod
    def _partials(brightness: float) -> tuple[tuple[float, float], ...]:
        """The brightness channel: a far sound is a fundamental, a near one has edge."""
        return ((1.0, 1.0),
                (2.0, T.AUDIO_PARTIAL_2 * brightness),
                (3.0, T.AUDIO_PARTIAL_3 * brightness * brightness))

    @staticmethod
    def _struck(ratios: tuple[float, ...], brightness: float,
                tilt: float = 1.4) -> tuple[tuple[float, float], ...]:
        """An inharmonic stack for a struck object: a bar, a bell, a hull being torn.

        Distance thins the upper partials here exactly as it does a harmonic stack, so a
        far strike is a duller strike rather than a different object. The fundamental is
        never thinned, because the thing is still there.

        The stack is scaled so that at full brightness its partials sum to one. Without
        that, adding partials to a voice raised its PEAK by up to two thirds while adding
        nothing a listener would call level, and three struck voices landing together put
        the hammer at 2.4 of full scale -- which the offline render normalises away and
        the live callback hard-clips. The scale is a constant, not a function of
        brightness, so a dull strike stays quieter than a bright one and the level cue
        keeps its sign.
        """
        norm = 1.0 / sum(1.0 if i == 0 else 1.0 / (1.0 + tilt * i)
                         for i in range(len(ratios)))
        return tuple((r, norm if i == 0 else norm * brightness / (1.0 + tilt * i))
                     for i, r in enumerate(ratios))

    @staticmethod
    def _hazard_bright(brightness: float) -> float:
        """Distance still dulls a hammer or a death, but not into a sine: below
        HAZARD_BRIGHT_FLOOR the strike stops being recognisable as a strike, which is the
        same failure as making it inaudible."""
        return T.HAZARD_BRIGHT_FLOOR + (1.0 - T.HAZARD_BRIGHT_FLOOR) * brightness

    @staticmethod
    def _lowpass(brightness: float) -> int:
        span = T.AUDIO_NOISE_LP_BRIGHT - T.AUDIO_NOISE_LP_DULL
        return max(1, int(round(T.AUDIO_NOISE_LP_DULL + span * brightness)))

    def _room(self, waveform: Waveform, f0: float, f1: float, duration: float,
              amplitude: float, place: Placement, decay: float | None = None,
              shape: EnvelopeShape = EnvelopeShape.LINEAR, highpass: int = 0,
              priority: bool = False, delay: float = 0.0,
              ratios: tuple[float, ...] | None = None, tilt: float = 1.4,
              bright_floor: bool = False, max_reflections: int | None = None) -> None:
        """The direct arrival, then the cave answering it down its other passages.

        `ratios` swaps the harmonic stack for a struck object's inharmonic one, so a
        strike can go through the room and still be a strike.
        """
        tonal = waveform is not Waveform.NOISE

        def stack(brightness: float) -> tuple[tuple[float, float], ...]:
            if not tonal:
                return ((1.0, 1.0),)
            if ratios is None:
                return self._partials(brightness)
            return self._struck(
                ratios, self._hazard_bright(brightness) if bright_floor else brightness,
                tilt)

        self.play(waveform, f0, f1, duration, amplitude * place.gain, place.pan,
                  attack=place.attack, decay=decay, delay=delay, shape=shape,
                  partials=stack(place.brightness),
                  lowpass=1 if tonal else self._lowpass(place.brightness),
                  highpass=highpass, priority=priority)
        # A reflection is a sine even when the direct arrival was a saw: two more walls of
        # rock have taken the edge off it, which is the same reason it is dull and late.
        # It is also four times cheaper to build, which is what keeps a death inside a frame.
        echo = Waveform.SINE if waveform is not Waveform.NOISE else Waveform.NOISE
        grown = min(duration * (1.0 + T.AUDIO_REFLECT_STRETCH),
                    duration + T.AUDIO_REFLECT_MAX_TAIL_S)
        scale = grown / duration
        # `max_reflections` is a cost lever, not a design one: a long voice's third
        # reflection is a second and a half of three-partial sine built on the game
        # thread, and the two that carry the room cue are the first two.
        for r in (place.reflections if max_reflections is None
                  else place.reflections[:max_reflections]):
            self.play(echo, f0, f1, grown, amplitude * place.gain * r.gain, r.pan,
                      attack=max(place.attack, 0.02),
                      decay=None if decay is None else decay * scale,
                      delay=delay + r.delay, shape=shape,
                      partials=stack(r.brightness),
                      lowpass=1 if tonal else self._lowpass(r.brightness),
                      highpass=highpass, priority=priority)

    # ---- sound design: whose sensor it was ------------------------------------------------
    def own_ping(self, gain: float = 1.0) -> None:
        """Mine. Rising, hard centre, dry -- and then the room answers, because that is
        what a transmission does and nothing else in the game does it.

        `gain` is only ever the held breath pulling it down. The player's own transmission
        is a fact about their own instrument, so it is never dropped the way a world sound
        is -- but it is not allowed to be the thing filling the silence before a hammer.
        """
        self.play(Waveform.SINE, T.AUDIO_OWN_PING_F0, T.AUDIO_OWN_PING_F1,
                  T.AUDIO_OWN_PING_S, T.AUDIO_OWN_PING_AMP * gain, 0.0, attack=0.004,
                  decay=T.AUDIO_OWN_PING_S * 0.55,
                  partials=((1.0, 1.0), (2.0, 0.30), (3.0, 0.14)), priority=True)
        for i, delay in enumerate(T.AUDIO_OWN_WASH_DELAYS):
            f = T.AUDIO_OWN_WASH_F0 * 0.9 ** i
            self.play(Waveform.SINE, f, f * 0.72, T.AUDIO_OWN_WASH_S,
                      T.AUDIO_OWN_PING_AMP * T.AUDIO_OWN_WASH_LEVELS[i] * gain,
                      T.AUDIO_OWN_WASH_PANS[i], attack=0.025,
                      decay=T.AUDIO_OWN_WASH_S * 0.75, delay=delay)

    def heard_ping(self, bearing: float, quality: float, az: float,
                   closing: bool = False) -> None:
        """Somebody else's. Falling, panned, and already reverberant when it arrives.

        Base pitch is proximity, which makes pitch the fifth channel DISTANCE is carried
        on. It is not approach: measured across 62 gestures, consecutive transmissions
        differed by a median of 0.20 semitones, and a fifth of a semitone every few
        seconds is a drift only a spectrogram can see.

        `closing` is approach, and it is an EVENT: the transmission answers itself a fifth
        of a second later, a fifth higher and slightly louder. Two notes stepping up is a
        different gesture, not the same gesture slightly sharper, and both notes sit in the
        ping's own register where a small speaker can reproduce them.
        """
        place = Placement.for_sound(bearing, quality, az)
        semitones = T.AUDIO_DISTANCE_SEMITONES * (quality - T.AUDIO_DISTANCE_REFERENCE_Q)
        f0 = T.AUDIO_HEARD_PING_F0 * 2.0 ** (semitones / 12.0)
        self._room(Waveform.SINE, f0, f0 * T.AUDIO_HEARD_PING_FALL, T.AUDIO_HEARD_PING_S,
                   T.AUDIO_HEARD_PING_AMP, place, decay=T.AUDIO_HEARD_PING_S * 0.62)
        if not closing:
            return
        second = f0 * 2.0 ** (T.AUDIO_APPROACH_INTERVAL / 12.0)
        self._room(Waveform.SINE, second, second * T.AUDIO_HEARD_PING_FALL,
                   T.AUDIO_HEARD_PING_S,
                   T.AUDIO_HEARD_PING_AMP * T.AUDIO_APPROACH_SECOND_AMP, place,
                   decay=T.AUDIO_HEARD_PING_S * 0.62, delay=T.AUDIO_APPROACH_GAP_S)

    def motion_contact(self, bearing: float, quality: float, az: float) -> None:
        """Something moving. Grains of band-limited noise -- the only unpitched sound in
        the game that is not a catastrophe, so it cannot be taken for a quiet beep."""
        place = Placement.for_sound(bearing, quality, az, max_reflections=1)
        for i in range(T.AUDIO_SCRAPE_GRAINS):
            if i == 0:
                self._room(Waveform.NOISE, 0.0, 0.0, T.AUDIO_SCRAPE_S, T.AUDIO_SCRAPE_AMP,
                           place, decay=T.AUDIO_SCRAPE_S * 0.6,
                           highpass=T.AUDIO_SCRAPE_LP * 5)
                continue
            self.play(Waveform.NOISE, 0.0, 0.0, T.AUDIO_SCRAPE_S,
                      T.AUDIO_SCRAPE_AMP * place.gain * (1.0 - 0.22 * i),
                      G.clamp(place.pan + 0.12 * (i - 1), -1.0, 1.0),
                      attack=0.015, decay=T.AUDIO_SCRAPE_S * 0.6,
                      delay=i * T.AUDIO_SCRAPE_GAP_S,
                      lowpass=self._lowpass(place.brightness),
                      highpass=T.AUDIO_SCRAPE_LP * 5)

    # ---- sound design: the machinery ---------------------------------------------------------
    def ratchet_notch(self, bearing: float, quality: float, az: float) -> None:
        """One notch of the hammer going up the mast: a pawl, its ring, and its click.

        The ring is the point, and until this it was not doing the job it was written for.
        It sat 11 dB under the body, so what a listener actually heard climbing the mast
        was the BODY, going 84 Hz to 188 Hz across a cycle -- which a laptop speaker
        removes entirely. The wind-up was audible on the gate machine by accident. The
        ring is now the loud voice and the body is the weight under it, so the thing that
        climbs is the thing a small speaker has.
        """
        place = Placement.for_sound(bearing, quality, az, max_reflections=1)
        climb = self._ratchet.climb()
        amp = T.RATCHET_AMP * place.gain * (0.55 + 0.45 * self._ratchet.progress)
        body = T.RATCHET_F0 * climb
        self.play(Waveform.SINE, body, body * 0.82, 0.10, amp * T.RATCHET_BODY_LEVEL,
                  place.pan, attack=0.002, decay=0.030, shape=EnvelopeShape.EXPONENTIAL)
        metal = T.RATCHET_METAL_F0 * climb
        # A far pawl is duller but it is still a pawl: the ring's stack thins with
        # distance, its fundamental does not, or the wind-up vanishes at range again.
        bright = (T.RATCHET_RING_BRIGHT_FLOOR
                  + (1.0 - T.RATCHET_RING_BRIGHT_FLOOR) * place.brightness)
        self.play(Waveform.SINE, metal, metal * 0.97, 0.075,
                  amp * T.RATCHET_RING_LEVEL, place.pan * 0.85,
                  attack=0.001, decay=0.022, shape=EnvelopeShape.EXPONENTIAL,
                  partials=self._struck(T.RATCHET_PARTIALS, bright, tilt=1.0))
        self.play(Waveform.NOISE, 0.0, 0.0, 0.04, amp * 0.30, place.pan,
                  attack=0.001, decay=0.007, shape=EnvelopeShape.EXPONENTIAL,
                  lowpass=self._lowpass(place.brightness),
                  highpass=T.RATCHET_CLICK_HP)
        for r in place.reflections:
            self.play(Waveform.SINE, metal, metal * 0.97, 0.13,
                      amp * T.RATCHET_RING_LEVEL * 0.6 * r.gain, r.pan,
                      attack=0.02, decay=0.045, delay=r.delay,
                      shape=EnvelopeShape.EXPONENTIAL,
                      partials=self._struck(T.RATCHET_PARTIALS, r.brightness, tilt=1.0))

    def hammer(self, bearing: float, quality: float, az: float) -> None:
        """The drop. Everything above it has been silent for RATCHET_BREATH_S, which is the
        only reason it lands; a hit with no held breath in front of it is a thud.

        Four things happen at once and the order they are written in is the order they
        matter on the machine the gate is watched on. The crack and the STRIKE are steel
        arriving; the ANVIL is the mast ringing afterwards; the body and the rock ring are
        weight, and weight is what a laptop throws away. The previous hammer was 99.9%
        below 150 Hz, centroid 95 Hz, and lost up to 14.6 dB through a 300 Hz /
        12 dB-per-octave speaker model where a routine ping lost none of itself -- so on
        the machine the gate was watched on, the most violent event in the match arrived
        under a beep. The strike and the anvil are what fixes that, and they are honest: a
        hammer hitting rock does crack and does ring.

        The placement gain is floored (HAZARD_GAIN_FLOOR) so a distant hammer still
        arrives above every routine sound. That trade is deliberate and it is a real cost:
        the hammer keeps 1.7 dB of LEVEL across the whole distance range instead of 20,
        and says how far away it is with brightness, attack and the room instead. The four
        hammers of seed 7 land within 2.6 dB of each other on a laptop where their
        qualities span 0.20 to 0.87. A lethal strike that cannot be heard because it is
        two chambers away is the worse failure.
        """
        place = Placement.for_sound(bearing, quality, az, gain_floor=T.HAZARD_GAIN_FLOOR)
        self.duck(T.HAMMER_DUCK, 0.04)
        amp = T.HAMMER_AMP * place.gain
        self.play(Waveform.NOISE, 0.0, 0.0, T.HAMMER_CRACK_S, amp * 0.55, place.pan,
                  attack=0.001, decay=T.HAMMER_CRACK_DECAY_S,
                  shape=EnvelopeShape.EXPONENTIAL,
                  lowpass=self._lowpass(min(1.0, place.brightness + 0.2)),
                  highpass=T.HAMMER_CRACK_HP, priority=True)
        self.play(Waveform.SINE, T.HAMMER_STRIKE_F0, T.HAMMER_STRIKE_F1,
                  T.HAMMER_STRIKE_S, amp * T.HAMMER_STRIKE_LEVEL, place.pan,
                  attack=0.001, decay=T.HAMMER_STRIKE_DECAY_S,
                  shape=EnvelopeShape.EXPONENTIAL,
                  partials=self._struck(T.HAMMER_STRIKE_PARTIALS,
                                        self._hazard_bright(place.brightness)),
                  priority=True)
        self._room(Waveform.SINE, T.HAMMER_ANVIL_F0, T.HAMMER_ANVIL_F1, T.HAMMER_ANVIL_S,
                   T.HAMMER_AMP * T.HAMMER_ANVIL_LEVEL, place,
                   decay=T.HAMMER_ANVIL_DECAY_S, shape=EnvelopeShape.EXPONENTIAL,
                   ratios=T.HAMMER_ANVIL_PARTIALS, delay=T.HAMMER_ANVIL_DELAY_S,
                   bright_floor=True, max_reflections=2, priority=True)
        self._room(Waveform.SINE, T.HAMMER_BODY_F0, T.HAMMER_BODY_F1, T.HAMMER_BODY_S,
                   T.HAMMER_AMP * T.HAMMER_BODY_LEVEL, place, decay=0.30,
                   shape=EnvelopeShape.EXPONENTIAL, delay=T.HAMMER_BODY_DELAY_S,
                   priority=True)
        self.play(Waveform.SINE, T.HAMMER_RING_F0, T.HAMMER_RING_F0 * 0.94,
                  T.HAMMER_RING_S, amp * T.HAMMER_RING_LEVEL, place.pan * 0.5,
                  attack=0.01, decay=0.75, shape=EnvelopeShape.EXPONENTIAL,
                  delay=T.HAMMER_RING_DELAY_S,
                  partials=self._struck(T.HAMMER_RING_PARTIALS, place.brightness),
                  priority=True)

    # ---- sound design: death -------------------------------------------------------------------
    def crash(self, bearing: float, quality: float, az: float, t: float) -> None:
        """Something died. It takes the room.

        Measured before this: the one death in seed 7 was 3.3 dB above a routine beep, in
        the same speaker as the machinery pulsing over it, with the same 6 ms attack and
        the same linear fade as everything else. A death and a ping were the same envelope.

        Then it took the room and still could not be heard, because 96.4% of it was under
        150 Hz: full-range it came out 2.7 dB above the loudest routine ping, and through
        a laptop speaker 4.9 dB below it. The TEAR is the fix. A hull coming apart shrieks
        before it thuds, and the shriek is the half of the event a small speaker has. The
        snap and the debris are high-passed for the same reason -- rock hitting rock
        clatters, it does not thump.
        """
        place = Placement.for_sound(bearing, quality, az, gain_floor=T.HAZARD_GAIN_FLOOR)
        self.duck(T.CRASH_DUCK, T.CRASH_DUCK_S)
        self._quiet_until = t + T.CRASH_SUPPRESS_S
        amp = T.CRASH_AMP * place.gain
        self.play(Waveform.NOISE, 0.0, 0.0, T.CRASH_SNAP_S, amp * 0.70, place.pan,
                  attack=0.001, decay=T.CRASH_SNAP_DECAY_S,
                  shape=EnvelopeShape.EXPONENTIAL,
                  lowpass=self._lowpass(min(1.0, place.brightness + 0.25)),
                  highpass=T.CRASH_SNAP_HP, priority=True)
        self._room(Waveform.SINE, T.CRASH_TEAR_F0, T.CRASH_TEAR_F1, T.CRASH_TEAR_S,
                   T.CRASH_AMP * T.CRASH_TEAR_LEVEL, place, decay=T.CRASH_TEAR_DECAY_S,
                   shape=EnvelopeShape.EXPONENTIAL, ratios=T.CRASH_TEAR_PARTIALS,
                   tilt=0.9, delay=T.CRASH_TEAR_DELAY_S, bright_floor=True,
                   max_reflections=2, priority=True)
        self._room(Waveform.SAW, T.CRASH_COLLAPSE_F0, T.CRASH_COLLAPSE_F1,
                   T.CRASH_COLLAPSE_S, T.CRASH_AMP * 0.55, place, decay=0.20,
                   shape=EnvelopeShape.EXPONENTIAL, priority=True)
        self.play(Waveform.SINE, T.CRASH_HULL_F0, T.CRASH_HULL_F0 * 0.9, T.CRASH_HULL_S,
                  amp * T.CRASH_HULL_LEVEL, place.pan * 0.4, attack=0.006, decay=0.85,
                  shape=EnvelopeShape.EXPONENTIAL, delay=T.CRASH_HULL_DELAY_S,
                  partials=self._struck(T.CRASH_HULL_PARTIALS, place.brightness, tilt=1.3),
                  priority=True)
        for i in range(T.CRASH_DEBRIS):
            self.play(Waveform.NOISE, 0.0, 0.0, T.CRASH_DEBRIS_S,
                      amp * 0.30 * (1.0 - 0.13 * i),
                      G.clamp(place.pan * 0.3 + T.CRASH_DEBRIS_PANS[i], -1.0, 1.0),
                      attack=0.001, decay=T.CRASH_DEBRIS_DECAY_S,
                      delay=T.CRASH_DEBRIS_DELAYS[i],
                      shape=EnvelopeShape.EXPONENTIAL,
                      lowpass=self._lowpass(place.brightness * 0.8),
                      highpass=T.CRASH_DEBRIS_HP, priority=True)

    # ---- sound design: the agent's own panel ------------------------------------------------------
    def fix(self) -> None:
        """Dry, centred and small. These are the instrument, not the world."""
        self.play(Waveform.SINE, 660, 660, 0.09, T.AUDIO_PANEL_AMP, 0.0, decay=0.05)
        self.play(Waveform.SINE, 990, 990, 0.11, T.AUDIO_PANEL_AMP, 0.0, decay=0.06,
                  delay=0.07)

    def recall_sent(self) -> None:
        """Three, and all three are audible: the old version set attack >= duration on the
        second and third, so they never reached level and it was one click."""
        for i in range(3):
            self.play(Waveform.SQUARE, 520, 520, 0.07, T.AUDIO_PANEL_AMP * 0.9, 0.0,
                      attack=0.002, decay=0.04, delay=0.12 * i)

    def recall_received(self) -> None:
        self.play(Waveform.SINE, 780, 780, 0.22, T.AUDIO_PANEL_AMP * 1.2, 0.0, decay=0.14,
                  partials=((1.0, 1.0), (2.0, 0.2)))

    def cargo_changed(self) -> None:
        self.play(Waveform.SINE, 1200, 1200, 0.055, T.AUDIO_PANEL_AMP, 0.0, decay=0.03)
        self.play(Waveform.SINE, 1600, 1600, 0.07, T.AUDIO_PANEL_AMP, 0.0, decay=0.04,
                  delay=0.055)

    # ---- per frame ---------------------------------------------------------------------
    def update(self, b: Belief, t: float, camera_azimuth: float = 0.0) -> None:
        # The held breath. RATCHET_BREATH_S was written as the design's best idea and
        # nothing enforced it: `_quiet_until` was set by `crash` and by nothing else, so
        # the ratchet went quiet at the top of the mast while everything else carried on.
        # Measured over seed 7's four cycles, the loudest thing inside the breath window
        # reached 0.30, 0.27, 0.00 and 0.15 against hammer peaks of 0.30, 0.31, 0.73 and
        # 0.41 -- in two of four the silence was as loud as the hit. So the breath now
        # does what a crash does: what is already sounding is pulled down, and nothing
        # routine is allowed to start.
        breath = self._ratchet.holding
        if breath and not self._breathing:
            self.duck(T.RATCHET_BREATH_DUCK, T.RATCHET_BREATH_DUCK_S)
        self._breathing = breath
        routine = t >= self._quiet_until and not breath

        for contact in b.contacts:
            key = id(contact)
            if self._seen_contacts.get(key) != contact.t_last:
                self._seen_contacts[key] = contact.t_last
                if contact.character is SoundCharacter.TONE and routine:
                    self.motion_contact(contact.bearing, contact.quality, camera_azimuth)

        if len(b.own_pings) > self._n_own_pings:
            self._n_own_pings = len(b.own_pings)
            # never suppressed: whose sensor it was is the point. Ducked in the breath,
            # because the silence in front of the hammer belongs to the hammer.
            self.own_ping(T.RATCHET_BREATH_DUCK if breath else 1.0)

        while self._n_heard < len(b.heard):
            sound = b.heard[self._n_heard]
            self._n_heard += 1
            if sound.character is SoundCharacter.CRASH:
                self.crash(sound.bearing, sound.quality, camera_azimuth, t)
                routine = False
            elif sound.character is SoundCharacter.PING:
                track = self._tracker.observe(sound.bearing, sound.quality, sound.t)
                if not self._tracker.should_sound(track, sound.bearing, sound.t):
                    continue        # the same transmission, still audible: not a new event
                closing = track.gestures > 0 and track.closing() >= T.AUDIO_APPROACH_STEP_Q
                if routine:
                    # Only a transmission somebody HEARD counts as the reference the next
                    # one is compared against. Noting it before this gate meant a ping
                    # suppressed inside a held breath or the crash window still moved the
                    # mark, so the next audible ping's approach was measured against
                    # something nobody heard -- swallowing one approach event per match.
                    self._tracker.note_gesture(track, sound.bearing, sound.t)
                    self.heard_ping(sound.bearing, sound.quality, camera_azimuth, closing)

        while self._n_fixes < len(b.fixes):
            self._n_fixes += 1
            if routine:
                self.fix()

        sig = b.signature
        if sig is not None and sig.t != self._last_signature_t:
            self._last_signature_t = sig.t
            self._signature_bearing = sig.bearing
            self._signature_quality = sig.quality
            self._ratchet.observe(sig.quality, sig.t)
        action = self._ratchet.tick(t)
        if action == NOTCH and routine:
            self.ratchet_notch(self._signature_bearing, self._signature_quality,
                               camera_azimuth)
        elif action == HAMMER:
            self.hammer(self._signature_bearing, self._signature_quality, camera_azimuth)

        if b.cargo != self._last_cargo:
            self._last_cargo = b.cargo
            if routine:
                self.cargo_changed()

        while self._n_log < len(b.log):
            _, text = b.log[self._n_log]
            self._n_log += 1
            if text.startswith("RECALL received"):
                self.recall_received()
