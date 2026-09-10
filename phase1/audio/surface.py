"""The surface, as sound. Wind, water, iron, a servo, a footfall, a yard.

`SOUND-DESIGN.md` section 5.7 has the surface [DESIGNED as a place; entirely unbuilt as
sound], and section 8.1 says why that is the trailer's other problem and not a small one:
`phase1/audio/` has ten recipes and none of them is rain, steel, a pipe, a servo, a footfall
or a yard, so Acts I and II have almost no diegetic material to be built from. This is the
attempt, and the honest verdict on each recipe is in its own docstring under THIN.

**WHY IT IS NOT ON `Mixer` AND SHOULD NOT BE.** Every recipe on `Mixer` is driven from
`Belief` and placed by `Placement`, because underground the player is listening through a
machine and the four distance cues are what a received signal did on its way. Section 5.7's
whole point is that the surface is the one place where there is no machine in between:

    | | surface | cave |
    | source | the world | one machine's belief |
    | the player | present | listening |

So these take a pan and a level and no quality, they are not derived from a `Belief`, and
nothing here is allowed to reach the cave. Putting them on `Mixer` would put un-sensed
material in the object whose entire contract is that everything in it came through a sensor.
They live beside it instead, and that separation is the design, not tidiness.

WHAT THEY ARE ALL MADE OF, since there are no samples: band-limited noise for anything with
air or water in it, a swept oscillator for anything with a motor in it, and the inharmonic
struck stack for anything made of metal. `Voice` supports exactly one linear sweep per voice,
so a gesture with three parts -- a servo accelerating, holding and stopping -- is three
voices in a row, which is also how `Mixer.hammer` builds a strike out of four.
"""
from __future__ import annotations

import numpy as np

from .envelope_shape import EnvelopeShape
from .mixer import Mixer
from .waveform import Waveform

# Moving-average widths, as corner frequencies at 48 kHz (0.44 * rate / width).
LP_RUMBLE: int = 120       # ~176 Hz
LP_MOAN: int = 46          # ~460 Hz
LP_AIR: int = 12           # ~1.8 kHz
LP_HISS: int = 5           # ~4.2 kHz
LP_SPRAY: int = 3          # ~7 kHz


class Surface:
    """Recipes for the one place the player hears the world directly.

    Every method queues voices on a `Mixer` and returns nothing, exactly as the mixer's own
    recipes do. `delay` is seconds from now, so a whole yard can be scheduled in one pass and
    rendered offline.
    """

    def __init__(self, mixer: Mixer, seed: int = 1) -> None:
        self.mixer: Mixer = mixer
        self.rng: np.random.Generator = np.random.default_rng(seed)

    # ---- weather -----------------------------------------------------------------------
    def wind(self, seconds: float, delay: float = 0.0, level: float = 0.11,
             gusts: int = 5) -> None:
        """Wind over a yard: overlapping band-limited moans at different widths and pans.

        THIN, and this is the thinnest thing in the file. Real wind is a filter whose corner
        moves -- a gust is not a level change, it is the sound getting brighter as it gets
        louder, and then rougher as it finds an edge. `Voice` low-passes once, at
        construction, and cannot sweep a corner. So a gust here is a long envelope on a fixed
        band, and stacking three bands at different levels only approximates the colour
        change. It will pass under a wide shot with something else on top of it. It will not
        survive being the only thing in a frame.
        """
        for index in range(gusts):
            start = delay + seconds * index / (gusts + 1.0)
            length = seconds * float(self.rng.uniform(0.45, 0.8))
            pan = float(self.rng.uniform(-0.85, 0.85))
            for width, share in ((LP_RUMBLE, 1.0), (LP_MOAN, 0.55), (LP_AIR, 0.16)):
                self.mixer.play(Waveform.NOISE, 0.0, 0.0, length,
                                level * share * float(self.rng.uniform(0.6, 1.0)),
                                pan * (1.0 if width == LP_RUMBLE else 0.75),
                                attack=length * 0.42, decay=length * 0.45,
                                delay=start, lowpass=width)

    def rain_on_steel(self, seconds: float, delay: float = 0.0, level: float = 0.085,
                      drops_per_second: float = 26.0) -> None:
        """A continuous hiss with individual strikes on plate over it.

        Two layers, because rain on a roof is two sounds: the mass of it, which is a hiss
        with no events in it, and the ones that hit metal near you, which are events. The
        strikes get a struck-plate stack so the metal is in the timbre rather than in the
        listener's imagination.

        THIN in one specific way: real rain's grains are not identically shaped, and every
        grain here is the same envelope with a different seed and level. It reads as rain at
        a distance and as a shaker up close. The fix is not more code, it is `Waveform.GRAIN`
        from section 5.10 -- the one seam that document proposes leaving open.
        """
        for index, (width, share, pan) in enumerate(
                ((LP_HISS, 1.0, -0.5), (LP_SPRAY, 0.62, 0.55), (LP_AIR, 0.35, 0.0))):
            self.mixer.play(Waveform.NOISE, 0.0, 0.0, seconds, level * share, pan,
                            attack=1.4, decay=seconds * 0.35, delay=delay + index * 0.11,
                            lowpass=width, highpass=LP_RUMBLE)
        count = int(seconds * drops_per_second)
        for index in range(count):
            t = delay + seconds * (index + float(self.rng.random())) / max(count, 1)
            hit = level * float(self.rng.uniform(0.25, 1.05))
            pan = float(self.rng.uniform(-0.95, 0.95))
            self.mixer.play(Waveform.NOISE, 0.0, 0.0, 0.035, hit * 0.9, pan,
                            attack=0.0008, decay=0.006, delay=t,
                            shape=EnvelopeShape.EXPONENTIAL, lowpass=LP_SPRAY, highpass=26)
            if index % 3 == 0:                       # only some of them find plate
                f0 = float(self.rng.uniform(1400.0, 2600.0))
                self.mixer.play(Waveform.SINE, f0, f0 * 0.995, 0.09, hit * 0.30, pan,
                                attack=0.0006, decay=0.019, delay=t,
                                shape=EnvelopeShape.EXPONENTIAL,
                                partials=Mixer._struck((1.0, 2.31, 4.02), 0.8, tilt=1.1))

    def drip(self, delay: float = 0.0, level: float = 0.16, pan: float = 0.0,
             pipe_hz: float = 236.0) -> None:
        """One drop into standing water, in a pipe or a sump.

        The rising sweep is the whole thing and it is physics rather than taste: the cavity
        the drop leaves behind closes as it fills, so its resonance climbs over about forty
        milliseconds. That is why a drip is recognisable at any level, and it is why this is
        the least thin recipe in the file.

        `pipe_hz` is the pipe ringing after it -- lower it for a bigger pipe.
        """
        self.mixer.play(Waveform.NOISE, 0.0, 0.0, 0.012, level * 0.5, pan,
                        attack=0.0004, decay=0.003, delay=delay,
                        shape=EnvelopeShape.EXPONENTIAL, lowpass=4, highpass=20)
        f0 = pipe_hz * 2.6
        self.mixer.play(Waveform.SINE, f0, f0 * 1.75, 0.055, level, pan,
                        attack=0.0009, decay=0.016, delay=delay + 0.002,
                        shape=EnvelopeShape.EXPONENTIAL)
        self.mixer.play(Waveform.SINE, pipe_hz, pipe_hz * 0.985, 0.42, level * 0.22, pan,
                        attack=0.004, decay=0.11, delay=delay + 0.004,
                        shape=EnvelopeShape.EXPONENTIAL,
                        partials=Mixer._struck((1.0, 2.04, 3.11), 0.55))

    def water_in_pipe(self, seconds: float, delay: float = 0.0, level: float = 0.06,
                      pan: float = -0.3, every: float = 1.9) -> None:
        """A header tank filling and a joint dripping onto it. `ART-DIRECTION.md` section 5.4
        asks for one drip every two seconds and calls it the entire dormant performance."""
        self.mixer.play(Waveform.NOISE, 0.0, 0.0, seconds, level, pan,
                        attack=0.9, decay=seconds * 0.4, delay=delay,
                        lowpass=LP_AIR, highpass=LP_MOAN)
        t = 0.35
        while t < seconds:
            self.drip(delay=delay + t, level=level * 2.4,
                      pan=pan + float(self.rng.uniform(-0.12, 0.12)))
            t += every * float(self.rng.uniform(0.86, 1.14))

    # ---- the machine, on the bench ---------------------------------------------------------
    def footfall(self, delay: float = 0.0, level: float = 0.30, pan: float = 0.0,
                 concrete: bool = True) -> None:
        """One foot down. Three voices: the weight, the surface, and the leg settling.

        THIN: a footfall's character is mostly in what happens in the twenty milliseconds
        after contact -- grit, a slight roll, the shoe or the pad flexing -- and none of that
        is a shape `Envelope` has. This is a good thump and a plausible surface and it will
        read as a machine putting a foot down. It will not read as a particular machine on a
        particular floor.
        """
        self.mixer.play(Waveform.SINE, 96.0, 54.0, 0.16, level, pan,
                        attack=0.0016, decay=0.036, delay=delay,
                        shape=EnvelopeShape.EXPONENTIAL,
                        partials=Mixer._struck((1.0, 1.71, 2.44), 0.5, tilt=1.6))
        self.mixer.play(Waveform.NOISE, 0.0, 0.0, 0.075, level * 0.55, pan,
                        attack=0.0008, decay=0.014, delay=delay,
                        shape=EnvelopeShape.EXPONENTIAL,
                        lowpass=6 if concrete else 22, highpass=LP_RUMBLE)
        self.mixer.play(Waveform.SINE, 208.0, 196.0, 0.30, level * 0.16, pan * 0.8,
                        attack=0.004, decay=0.07, delay=delay + 0.020,
                        shape=EnvelopeShape.EXPONENTIAL,
                        partials=Mixer._struck((1.0, 2.76, 5.4), 0.45))

    def servo(self, seconds: float = 0.55, delay: float = 0.0, level: float = 0.16,
              pan: float = 0.0, hz: float = 128.0, load: float = 1.0) -> None:
        """A joint moving: engage, run, stop. Four voices and a click at each end.

        The pitch envelope is the whole recipe. A geared actuator does not run at a constant
        speed -- it accelerates into the move and decelerates out of it -- and a constant tone
        with a fade on it sounds like a fan rather than a joint. `Voice` sweeps linearly once,
        so this is three sweeps butted together, which is exactly how `Mixer.hammer` gets four
        different physical events out of four voices.

        THIN, and honestly: it is a decent robot noise and it is not a decent SERVO noise. A
        real one has a gear mesh -- a set of partials at multiples of the tooth rate that move
        WITH the speed and stay in ratio -- which is buildable here (`partials` on a swept
        voice does exactly that) and a cogging ripple, which is amplitude modulation at the
        same rate, and is not. The ripple is the part the ear uses.
        """
        run = max(seconds - 0.22, 0.06)
        top = hz * (1.0 + 0.55 * load)
        stack = ((1.0, 1.0), (2.0, 0.42), (3.0, 0.20), (4.6, 0.11))
        self.mixer.play(Waveform.SAW, hz * 0.55, top, 0.11, level * 0.8, pan,
                        attack=0.006, decay=0.09, delay=delay, partials=stack)
        self.mixer.play(Waveform.SAW, top, top * 0.97, run, level, pan,
                        attack=0.012, decay=run * 0.9, delay=delay + 0.11, partials=stack)
        self.mixer.play(Waveform.SAW, top * 0.97, hz * 0.4, 0.13, level * 0.7, pan,
                        attack=0.008, decay=0.1, delay=delay + 0.11 + run, partials=stack)
        self.mixer.play(Waveform.NOISE, 0.0, 0.0, seconds, level * 0.22, pan,
                        attack=0.02, decay=seconds * 0.7, delay=delay,
                        lowpass=LP_AIR, highpass=LP_MOAN)
        for tick in (delay, delay + 0.11 + run + 0.13):
            self.mixer.play(Waveform.NOISE, 0.0, 0.0, 0.02, level * 0.5, pan,
                            attack=0.0005, decay=0.004, delay=tick,
                            shape=EnvelopeShape.EXPONENTIAL, lowpass=4, highpass=40)

    def iron_under_load(self, seconds: float = 3.2, delay: float = 0.0, level: float = 0.24,
                        pan: float = 0.0, hz: float = 52.0, creaks: int = 7) -> None:
        """A structure taking weight: the headframe, a rack, a plate bridge under a machine.

        Two things at once. The body is a low struck stack that BENDS -- the sweep is downward
        because a loaded member's modes drop as it deflects, and that fall is what says
        'taking weight' rather than 'ringing'. Over it, stick-slip: irregular short grains
        that accelerate and then stop, which is what a joint under increasing load does.

        The best of the six, because both halves of it are things this engine is actually good
        at: a slow sweep on an inharmonic stack, and a train of events with irregular spacing.
        The stick-slip grains are a real mechanism and not a texture.
        """
        self.mixer.play(Waveform.SINE, hz, hz * 0.88, seconds, level, pan,
                        attack=seconds * 0.22, decay=seconds * 0.5, delay=delay,
                        shape=EnvelopeShape.EXPONENTIAL,
                        partials=Mixer._struck((1.0, 2.09, 3.42, 5.61), 0.75, tilt=1.1))
        t = seconds * 0.28
        gap = seconds * 0.16
        for index in range(creaks):
            f0 = 340.0 * (1.0 + 0.16 * index) * float(self.rng.uniform(0.92, 1.1))
            self.mixer.play(Waveform.SINE, f0, f0 * 1.06,
                            float(self.rng.uniform(0.035, 0.08)),
                            level * 0.30 * float(self.rng.uniform(0.5, 1.0)),
                            pan + float(self.rng.uniform(-0.2, 0.2)),
                            attack=0.002, decay=0.018, delay=delay + t,
                            shape=EnvelopeShape.EXPONENTIAL,
                            partials=Mixer._struck((1.0, 1.63, 2.87), 0.85, tilt=0.9))
            t += gap * float(self.rng.uniform(0.5, 1.2))
            gap *= 0.82                                   # it accelerates, then it holds

    # ---- the place ---------------------------------------------------------------------------
    def yard_hum(self, seconds: float, delay: float = 0.0, level: float = 0.05) -> None:
        """Somewhere people work: a plant hum, its fifth, and a slow beat between two of them.

        THIN by construction and deliberately so. A yard is a hundred small sources and this
        is four. What it does is stop Act I being a hole between events, which is section 6.1's
        'continuous near, sparse far' applied to the one place that is allowed a bed at all --
        the cave is forbidden one (section 5.6) and the surface is not.
        """
        for hz, pan, share in ((49.0, -0.4, 1.0), (49.35, 0.45, 0.85),
                               (73.5, 0.2, 0.4), (147.0, -0.25, 0.14)):
            self.mixer.play(Waveform.SINE, hz, hz, seconds, level * share, pan,
                            attack=2.5, decay=seconds * 0.45, delay=delay,
                            partials=((1.0, 1.0), (2.0, 0.18), (3.0, 0.07)))
        self.mixer.play(Waveform.NOISE, 0.0, 0.0, seconds, level * 0.5, 0.0,
                        attack=3.0, decay=seconds * 0.4, delay=delay,
                        lowpass=LP_RUMBLE)

    def headframe(self, seconds: float, delay: float = 0.0, level: float = 0.16) -> None:
        """Act I shot 2: the headframe against an overcast sky. Wind through a lattice, iron
        taking the weather, and one drip off it. A composed shot rather than a recipe, and it
        is here because that is the shot the trailer opens on."""
        self.wind(seconds, delay=delay, level=level * 0.85, gusts=4)
        self.iron_under_load(seconds * 0.42, delay=delay + seconds * 0.30,
                             level=level * 0.55, pan=-0.25, hz=44.0, creaks=5)
        self.yard_hum(seconds, delay=delay, level=level * 0.30)
        for index in range(int(seconds / 2.4)):
            self.drip(delay=delay + 0.8 + index * 2.4 * float(self.rng.uniform(0.9, 1.1)),
                      level=level * 0.5, pan=float(self.rng.uniform(-0.5, 0.5)),
                      pipe_hz=180.0)

    def bench(self, seconds: float, delay: float = 0.0, level: float = 0.24) -> None:
        """Act II: close and dry. A machine on the bench being prepared -- servos, a foot
        down, the frame taking its weight -- with the yard a long way behind it."""
        self.yard_hum(seconds, delay=delay, level=level * 0.16)
        t = 0.4
        index = 0
        while t < seconds - 0.8:
            if index % 3 == 2:
                self.footfall(delay=delay + t, level=level * 0.8,
                              pan=float(self.rng.uniform(-0.3, 0.3)))
                t += float(self.rng.uniform(0.7, 1.1))
            else:
                span = float(self.rng.uniform(0.35, 0.8))
                self.servo(span, delay=delay + t, level=level * 0.55,
                           pan=float(self.rng.uniform(-0.55, 0.55)),
                           hz=float(self.rng.uniform(104.0, 168.0)),
                           load=float(self.rng.uniform(0.4, 1.3)))
                t += span + float(self.rng.uniform(0.25, 0.7))
            index += 1
        self.iron_under_load(1.6, delay=delay + seconds * 0.62, level=level * 0.4,
                             pan=0.3, hz=61.0, creaks=4)

