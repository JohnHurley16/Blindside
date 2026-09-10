"""Snow, as sound. Feet in it, wind over it, drift off a ridge, and air with it falling in it.

Sibling of `surface.py` and for the same reason (see that module's docstring): these take a
pan and a level, are not derived from a `Belief`, and cannot reach the cave, so they live
beside `Mixer` rather than on it. `surface.py` built a pit-head in the rain. The world is a
snowy valley under mountains now, and none of what is in there is snow.

THE ONE IDEA THIS FILE IS BUILT ON, and it is the difference between snow and everything
else in the package:

    **A footfall in deep snow is a COMPRESSION, not an impact.**

An impact is a discontinuity. A foot hits concrete, and all of the energy is in the first
millisecond; everything after it is a tail. Deep snow does not do that. The foot decelerates
over five to twenty centimetres while the pack densifies under it, and it goes on making
sound the whole way down -- in fact it makes MORE sound as it goes, because the pack stiffens
as it compacts and the individual crystal bonds that are failing get shorter and stiffer and
therefore higher pitched. So the energy is spread across a tenth of a second and the peak is
LATE, and the spectrum CLIMBS through the event. That is the whole recipe, and it is why
`Surface.footfall` -- a good thump with a plausible surface over it -- could never have been
retuned into a snow footfall. It is the wrong shape of event.

The squeak is a second mechanism on top of that one. Below about ten degrees of frost the
pressure of a foot no longer melts the crystals it is crushing, so instead of lubricating they
fracture and rub, which is stick-slip, which is a narrow band of noise whose centre rises as
the contact stiffens. Above about two degrees of frost it disappears entirely -- the crystals
melt under pressure and the foot slides on water. **`temperature_c` in this file is not
decoration: it is the one control that turns the recognisable half of the sound on and off**,
and the recipes below are written so that footfall at -1 C and footfall at -18 C are
different sounds rather than the same sound at two levels.

WHAT MADE ANY OF THIS BUILDABLE. `Voice._noise` used to take one moving-average width, chosen
at construction, so a corner could not move; `surface.py`'s own notes called the wind the
thinnest thing in the file for exactly that reason and said a squeak was out of reach. A width
may now be a PROFILE (see `Voice._noise`), which buys three things this file could not have
had: a low-pass whose corner climbs (the compression), a band-pass whose centre climbs (the
squeak), and wind whose brightness and level move together, because narrowing the window
raises the corner and raises the RMS at the same time, which is what a gust physically is.

AND THE DEADNESS IS NOT A SOUND. Air with snow falling in it is the most absorptive condition
you will ever stand in: the flakes scatter and the fresh layer underfoot removes the ground
reflection, so nothing comes back from anywhere. It cannot be added, only subtracted, so
`valley_call` renders the same event twice -- once with the valley answering and once with the
valley not answering -- because the effect only exists as a comparison.
"""
from __future__ import annotations

import numpy as np

from .envelope_shape import EnvelopeShape
from .mixer import Mixer
from .waveform import Waveform

# Moving-average widths as corner frequencies at 48 kHz (0.44 * rate / width).
LP_RUMBLE: int = 160       # ~132 Hz
LP_BODY: int = 44          # ~480 Hz
LP_GRAIN: int = 14         # ~1.5 kHz
LP_CRUNCH: int = 7         # ~3.0 kHz
LP_CRYSTAL: int = 4        # ~5.3 kHz
LP_DUST: int = 2           # ~10.6 kHz

SQUEAK_ONSET_C: float = -2.0     # warmer than this and pressure melting kills it outright
SQUEAK_FULL_C: float = -14.0     # colder than this and it is as loud as it gets


def squeak_strength(temperature_c: float) -> float:
    """How much of the crystal-fracture squeak survives at this temperature.

    The physics is a threshold, not a slope: a foot's pressure melts the crystal contacts it
    is loading when the snow is near freezing, so they slide instead of breaking and there is
    no squeak at all. Get ten or fifteen degrees below and nothing melts, everything fractures,
    and the squeak is the loudest part of the footfall. GUESS: the two temperatures. The shape
    -- off, then a ramp, then saturated -- is the part that is real.
    """
    if temperature_c >= SQUEAK_ONSET_C:
        return 0.0
    span = SQUEAK_ONSET_C - SQUEAK_FULL_C
    return float(min(1.0, (SQUEAK_ONSET_C - temperature_c) / span))


def corner_walk(rng: np.random.Generator, points: int, narrowest: float,
                widest: float, step: float = 0.35) -> np.ndarray:
    """A smoothed random walk between two moving-average widths, in log space.

    Log space because a corner is a frequency and a frequency is heard logarithmically: a
    walk that is linear in samples-per-window spends nearly all its time at the bright end.
    """
    out = np.empty(points, dtype=np.float64)
    lo, hi = np.log(narrowest), np.log(widest)
    value = (lo + hi) * 0.5
    for i in range(points):
        value += float(rng.normal(0.0, step)) + 0.10 * ((lo + hi) * 0.5 - value)
        out[i] = min(max(value, lo), hi)
    # one pass of smoothing, so a gust builds rather than switching
    kernel = np.array([0.25, 0.5, 0.25])
    out = np.convolve(out, kernel, "same")
    out[0], out[-1] = out[1], out[-2]
    return np.exp(out)


class Snow:
    """Recipes for a valley under snow. Every method queues voices on a `Mixer`."""

    def __init__(self, mixer: Mixer, seed: int = 1) -> None:
        self.mixer: Mixer = mixer
        self.rng: np.random.Generator = np.random.default_rng(seed)

    # ---- feet ---------------------------------------------------------------------------
    def footfall_deep(self, delay: float = 0.0, level: float = 0.30, pan: float = 0.0,
                      temperature_c: float = -14.0, depth: float = 1.0) -> None:
        """One foot into fresh, deep snow. A compression, and it should measure as one.

        Four things, and the first two are the sound:

        1. THE CRUSH. Band-limited noise over about 150 ms with a LINEAR envelope whose peak
           is at 60 per cent of its own length, not at the start. The corner climbs from
           530 Hz to 2.6 kHz across it, because the pack stiffens as it densifies and
           stiffer contacts fracture higher. The high-pass climbs with it, so the event does
           not merely get brighter, it gets THINNER: the low end of a footfall in snow is over
           almost as soon as it starts.
        2. THE SQUEAK. Stick-slip: a narrow band of noise that starts at 440-700 Hz and ends
           at 1.06-1.76 kHz, with a faint swept tone inside it because real stick-slip
           partially locks and is not pure noise. Level is set entirely by `temperature_c`,
           and at -1 C it is not here at all. It starts a third of the way into the crush,
           because there is nothing to fracture until there is load.
        3. THE THUD. Small. Snow is the most absorptive thing anybody walks on, so the mass
           of the machine is heard as almost nothing: one short low sweep at a fifth of the
           crush's level, and it is gone inside a tenth of a second.
        4. NOTHING AFTER IT. No reflection, no ring, no tail. That absence is a large part of
           what says snow rather than gravel, and it is the reason nothing here goes through
           `Placement`.

        `depth` scales how long the compression lasts: 1.0 is boot-deep fresh snow, 0.4 is a
        few centimetres over a hard layer.
        """
        span = 0.075 + 0.075 * depth
        rise = span * 0.60
        squeak = squeak_strength(temperature_c)

        # 1. the crush: the corner climbs, the floor climbs faster
        self.mixer.play(
            Waveform.NOISE, 0.0, 0.0, span, level * 0.95, pan,
            attack=rise, decay=span - rise, delay=delay,
            lowpass=np.array([40.0, 26.0, 15.0, 9.0, 8.0]),
            highpass=np.array([190.0, 150.0, 90.0, 52.0, 44.0]))
        # a second, drier layer a few milliseconds in: the crystals immediately under the foot
        self.mixer.play(
            Waveform.NOISE, 0.0, 0.0, span * 0.7, level * 0.42, pan * 0.8,
            attack=span * 0.42, decay=span * 0.3, delay=delay + span * 0.12,
            lowpass=np.array([16.0, 9.0, 5.0, 5.0]),
            highpass=np.array([70.0, 40.0, 22.0, 20.0]))

        # 2. the squeak
        if squeak > 0.0:
            start = delay + span * 0.30
            length = span * 0.62
            self.mixer.play(
                Waveform.NOISE, 0.0, 0.0, length, level * 0.95 * squeak, pan * 0.9,
                attack=length * 0.55, decay=length * 0.42, delay=start,
                lowpass=np.array([30.0, 22.0, 15.0, 12.0]),
                highpass=np.array([48.0, 36.0, 25.0, 20.0]))
            f0 = 760.0 * float(self.rng.uniform(0.88, 1.16))
            self.mixer.play(
                Waveform.SINE, f0, f0 * 2.15, length * 0.8, level * 0.20 * squeak, pan * 0.9,
                attack=length * 0.45, decay=length * 0.3, delay=start + length * 0.1,
                partials=((1.0, 1.0), (2.37, 0.30), (3.71, 0.12)))

        # 3. the thud, and there is not much of it
        self.mixer.play(
            Waveform.SINE, 74.0, 44.0, 0.075, level * 0.20, pan,
            attack=0.010, decay=0.026, delay=delay,
            shape=EnvelopeShape.EXPONENTIAL,
            partials=Mixer._struck((1.0, 1.94, 3.11), 0.35, tilt=2.4))

    def footfall_packed(self, delay: float = 0.0, level: float = 0.30, pan: float = 0.0,
                        temperature_c: float = -14.0) -> None:
        """One foot on packed snow -- a trail, a road, a cleared terrace, wind slab.

        The same materials arranged as an IMPACT, because that is what it is: the pack has
        already been compressed, so it does not yield, and the foot stops in a few
        milliseconds. Three differences from `footfall_deep`, all of them consequences of
        that one fact:

          the envelope is exponential and its peak is in the first two milliseconds;
          the crunch is broader and higher, because the grains are larger, rounded by
          repeated melt and refreeze, and they shear rather than crush;
          and there IS low end, about three times as much, because a compacted layer
          transmits into the ground under it instead of absorbing everything.

        The squeak survives -- packed cold snow squeaks under a boot as loudly as fresh does,
        and often more, because more crystals are being loaded at once -- but it is much
        shorter, so it reads as part of the crunch rather than as its own gesture.
        """
        squeak = squeak_strength(temperature_c)
        self.mixer.play(
            Waveform.NOISE, 0.0, 0.0, 0.075, level * 1.7, pan,
            attack=0.0018, decay=0.018, delay=delay, shape=EnvelopeShape.EXPONENTIAL,
            lowpass=np.array([9.0, 5.0, 3.0]),
            highpass=np.array([60.0, 34.0, 20.0]))
        if squeak > 0.0:
            self.mixer.play(
                Waveform.NOISE, 0.0, 0.0, 0.048, level * 0.85 * squeak, pan * 0.9,
                attack=0.005, decay=0.017, delay=delay + 0.004,
                shape=EnvelopeShape.EXPONENTIAL,
                lowpass=np.array([20.0, 13.0, 11.0]),
                highpass=np.array([34.0, 22.0, 18.0]))
        # The thud is a THIRD of what it would be on stone, and that is the balance the first
        # measurement got wrong: packed snow is still snow, and the first version measured 77%
        # of its power below 200 Hz against concrete's 90%, so it read as a thump with some
        # grit rather than as a crunch with a floor under it.
        self.mixer.play(
            Waveform.SINE, 88.0, 52.0, 0.11, level * 0.30, pan,
            attack=0.0016, decay=0.024, delay=delay,
            shape=EnvelopeShape.EXPONENTIAL,
            partials=Mixer._struck((1.0, 1.86, 2.94), 0.45, tilt=2.0))
        # the one thing packed snow has that deep snow does not: a floor under it
        self.mixer.play(
            Waveform.SINE, 176.0, 168.0, 0.16, level * 0.10, pan * 0.8,
            attack=0.003, decay=0.038, delay=delay + 0.006,
            shape=EnvelopeShape.EXPONENTIAL,
            partials=Mixer._struck((1.0, 2.42, 4.31), 0.4, tilt=1.6))

    def gait(self, seconds: float, delay: float = 0.0, level: float = 0.28,
             pan: float = 0.0, deep: bool = True, stride: float = 1.30,
             temperature_c: float = -14.0) -> None:
        """A four-legged machine walking. Four feet, and they are not evenly spaced.

        A symmetrical walk puts the four falls at fixed fractions of one stride, and in the
        LATERAL SEQUENCE a hind foot lands and its own fore foot follows it closely -- so the
        pattern is a pair, a gap, a pair, a gap, not four even beats. That unevenness is most
        of what makes a gait read as an animal rather than as a metronome, and it costs
        nothing here: it is four numbers.

        The fore feet are louder because a quadruped carries about sixty per cent of its
        weight on them, and left and right are panned apart, so the thing walks across the
        stereo field instead of standing in the middle of it.
        """
        # hind-left, fore-left, hind-right, fore-right, as fractions of one stride
        phases = (0.00, 0.22, 0.50, 0.72)
        weights = (0.86, 1.00, 0.84, 0.98)
        pans = (-0.34, -0.26, 0.34, 0.26)
        drop = self.footfall_deep if deep else self.footfall_packed
        t = 0.0
        while t < seconds:
            for phase, weight, side in zip(phases, weights, pans):
                at = t + stride * phase + float(self.rng.normal(0.0, 0.012))
                if at >= seconds:
                    continue
                drop(delay=delay + at,
                     level=level * weight * float(self.rng.uniform(0.86, 1.14)),
                     pan=float(np.clip(pan + side, -1.0, 1.0)),
                     temperature_c=temperature_c)
            t += stride * float(self.rng.uniform(0.96, 1.06))

    # ---- air ----------------------------------------------------------------------------
    def valley_wind(self, seconds: float, delay: float = 0.0, level: float = 0.13,
                    layers: int = 3, open_valley: bool = True) -> None:
        """Wind over 1.2 km of open snow, with a corner that moves.

        THIS IS THE FIX FOR THE THING `surface.py` CALLED THE THINNEST IN THE FILE. Its wind
        was overlapping fixed bands with long envelopes on them, which is a level change
        wearing a gust's clothes. A real gust is a filter sweeping: the sound gets brighter as
        it gets louder, and rougher as it finds an edge, and those are one event and not three.

        Each layer here is ONE voice whose moving-average width random-walks over the whole
        slot, so its corner walks with it -- and the level follows for free, because averaging
        w samples of white noise scales its RMS by one over root w, so narrowing the window
        from 200 samples to 60 raises the corner by a factor of three and the level by 5.2 dB
        at the same instant. Nothing modulates anything; it is one filter, moving.

        `open_valley` widens the walk. Over open snow there is nothing to break the flow, so
        the wind is steadier and darker in the lulls and much brighter in the gusts; in among
        buildings or a lattice it is choppier over a narrower range.
        """
        # The two widths bound the corner, and they were CHOSEN BY MEASUREMENT rather than
        # by taste. Real outdoor wind noise is dominated by its low end -- the first version
        # of this walked between widths 26 and 240 and put only 21% of its power under
        # 200 Hz, which is a hiss and not a valley. 50 to 400 puts 48% under 200 Hz with the
        # gust mechanism intact (corner against level +0.73). The high-pass sits eight times
        # wider than the low-pass so each layer is a broad sloping band rather than a narrow
        # one, which is also what a wind spectrum is.
        low, high = (400.0, 50.0) if open_valley else (280.0, 70.0)
        points = max(6, int(seconds / 0.30))
        # ONE walk, heard three times. The first version gave each layer an independent walk
        # and measured a corner-against-level correlation of about zero -- because when one
        # layer gusted another was in a lull and the sum flattened. That is also wrong as
        # physics: a gust is one body of air crossing a valley, not three winds. So the layers
        # share a master walk, offset by about a second each and scaled a little, which is a
        # gust arriving at three points across the floor at three times.
        master = corner_walk(self.rng, points + 3 * layers, high, low,
                             step=0.40 if open_valley else 0.55)
        for index in range(layers):
            width = master[index * 3:index * 3 + points] * (1.0, 1.18, 0.84)[index % 3]
            pan = (-0.72, 0.68, 0.0)[index % 3]
            share = (1.0, 0.85, 0.55)[index % 3]
            # The envelope is a flat top with short ramps ON PURPOSE, and this is the one
            # place the recipe was measurably wrong first time. A long triangular envelope
            # over the whole slot drives the level from the envelope, so the corner and the
            # level stopped being the same event: measured, brightness against level came out
            # at -0.41, brighter while quieter, which is the opposite of a gust. Flat, and
            # the filter is the only thing setting the level again.
            ramp = min(1.1, seconds * 0.16)
            self.mixer.play(
                Waveform.NOISE, 0.0, 0.0, seconds, level * share, pan,
                attack=ramp, decay=ramp, delay=delay + index * 0.23,
                lowpass=width, highpass=width * 8.0)
        # The ground layer: the part of a wind that is not a gust. It is low and it barely
        # moves, and it is kept small deliberately -- a loud fixed-corner bed under a moving
        # one puts the level back under something that is not the filter, which is the defect
        # the layers above were just fixed for.
        self.mixer.play(
            Waveform.NOISE, 0.0, 0.0, seconds, level * 0.20, 0.0,
            attack=min(1.6, seconds * 0.25), decay=min(1.6, seconds * 0.25), delay=delay,
            lowpass=master[:points] * 1.9)

    def spindrift(self, seconds: float = 3.0, delay: float = 0.0, level: float = 0.10,
                  pan: float = 0.4) -> None:
        """Loose snow lifting off a ridge and going over the edge.

        Two parts. The mass of it is a hiss an octave and a half above the wind, and its
        corner climbs INTO the gust and falls out of it, which is the difference between
        spindrift and a hi-hat. Over that, individual crystals: a few hundred grains a second
        at the peak, none at the ends, each one four milliseconds long. It is the only thing
        in this file that lives mostly above 4 kHz, and it is what a ridge line sounds like
        from below.
        """
        points = max(6, int(seconds / 0.18))
        ramp = np.concatenate((np.linspace(9.0, 2.6, points // 2),
                               np.linspace(2.6, 11.0, points - points // 2)))
        self.mixer.play(
            Waveform.NOISE, 0.0, 0.0, seconds, level, pan,
            attack=seconds * 0.40, decay=seconds * 0.36, delay=delay,
            lowpass=ramp, highpass=ramp * 6.0)
        grains = int(seconds * 150.0)
        for index in range(grains):
            u = (index + float(self.rng.random())) / max(grains, 1)
            weight = float(np.sin(np.pi * u)) ** 2          # none at the ends, dense at peak
            if float(self.rng.random()) > weight:
                continue
            self.mixer.play(
                Waveform.NOISE, 0.0, 0.0, 0.004,
                level * 0.5 * weight * float(self.rng.uniform(0.3, 1.0)),
                pan + float(self.rng.uniform(-0.25, 0.25)),
                attack=0.0004, decay=0.0011, delay=delay + u * seconds,
                shape=EnvelopeShape.EXPONENTIAL, lowpass=LP_DUST, highpass=LP_CRUNCH)

    def falling_snow(self, seconds: float, delay: float = 0.0, level: float = 0.035) -> None:
        """Snow actually falling, which is very nearly nothing, and that is the point.

        A flake weighs almost nothing and lands at a metre a second, so what you hear is not
        the snow: it is a very faint high tick where flakes land on something hard near you,
        and otherwise a silence with no floor in it. The recipe is deliberately thin. **The
        loud part of falling snow is what it does to everything else, and that is `deaden`.**
        """
        self.mixer.play(
            Waveform.NOISE, 0.0, 0.0, seconds, level, 0.0,
            attack=seconds * 0.3, decay=seconds * 0.45, delay=delay,
            lowpass=LP_CRYSTAL, highpass=LP_GRAIN)
        ticks = int(seconds * 9.0)
        for index in range(ticks):
            t = delay + seconds * (index + float(self.rng.random())) / max(ticks, 1)
            self.mixer.play(
                Waveform.NOISE, 0.0, 0.0, 0.005,
                level * float(self.rng.uniform(0.4, 1.5)),
                float(self.rng.uniform(-0.9, 0.9)),
                attack=0.0004, decay=0.0013, delay=t,
                shape=EnvelopeShape.EXPONENTIAL, lowpass=LP_DUST, highpass=LP_CRYSTAL)

    # ---- the deadness, which only exists as a comparison ---------------------------------
    def valley_call(self, delay: float = 0.0, level: float = 0.30, pan: float = -0.2,
                    still_air: bool = True) -> None:
        """One loud short event, and then the valley either answers it or does not.

        THE DEADNESS OF AIR WITH SNOW IN IT IS NOT A SOUND AND CANNOT BE ADDED. It is the
        opposite of reverb: falling snow scatters and absorbs across the whole path, and the
        fresh layer on the ground removes the one reflection that is always there outdoors, so
        nothing comes back from anywhere. The only way to render it is to render the same
        event twice and let the pair be the measurement.

        `still_air=True` is the valley answering: three discrete arrivals, from the near wall
        at 300 m (1.75 s there and back), the far wall at 900 m (5.24 s), and one late
        scattered return off the up-valley slope. Each is duller than the last, because air
        absorbs the top of a spectrum over half a kilometre whatever the weather, and they
        come from the sides because the walls are on the sides.

        `still_air=False` is the same event in falling snow. No returns at all, and the direct
        arrival itself loses its top, because the path from the source to the ear also has
        snow in it. It is roughly 2 dB quieter and markedly darker, and there is nothing after
        it -- which, out of doors, is a thing you will never otherwise hear.
        """
        bright = 0.85 if still_air else 0.42
        gain = 1.0 if still_air else 0.80
        self.mixer.play(
            Waveform.SINE, 186.0, 178.0, 0.9, level * gain, pan,
            attack=0.0022, decay=0.20, delay=delay,
            shape=EnvelopeShape.EXPONENTIAL,
            partials=Mixer._struck((1.0, 2.14, 3.77, 5.42), bright, tilt=1.3))
        self.mixer.play(
            Waveform.NOISE, 0.0, 0.0, 0.10, level * 0.35 * gain, pan,
            attack=0.0008, decay=0.020, delay=delay,
            shape=EnvelopeShape.EXPONENTIAL,
            lowpass=LP_CRUNCH if still_air else LP_BODY, highpass=LP_RUMBLE)
        if not still_air:
            return
        # (delay seconds, level, pan, brightness) -- near wall, far wall, up-valley
        for seconds, share, side, dull in ((1.75, 0.26, 0.62, 0.34),
                                           (5.24, 0.11, -0.70, 0.17),
                                           (7.10, 0.05, 0.30, 0.09)):
            self.mixer.play(
                Waveform.SINE, 186.0, 178.0, 1.4, level * share, side,
                attack=0.045, decay=0.34, delay=delay + seconds,
                shape=EnvelopeShape.EXPONENTIAL,
                partials=Mixer._struck((1.0, 2.14, 3.77, 5.42), dull, tilt=1.3))

    # ---- composed ------------------------------------------------------------------------
    def open_valley(self, seconds: float, delay: float = 0.0, level: float = 0.16) -> None:
        """The range, or the valley floor: wind, one drift off a ridge, and snow in the air.
        What movement 1 of the trailer stands on."""
        self.valley_wind(seconds, delay=delay, level=level * 0.9)
        self.falling_snow(seconds, delay=delay, level=level * 0.22)
        for index in range(max(1, int(seconds / 5.0))):
            self.spindrift(float(self.rng.uniform(2.2, 3.8)),
                           delay=delay + 1.0 + index * 4.6,
                           level=level * float(self.rng.uniform(0.4, 0.8)),
                           pan=float(self.rng.uniform(-0.8, 0.8)))

    def machine_crossing(self, seconds: float, delay: float = 0.0, level: float = 0.26,
                         deep: bool = True, temperature_c: float = -14.0) -> None:
        """The machine walking away across open snow, with the valley behind it. The shot the
        trailer's second movement is: one animal, small in frame, leaving a track."""
        self.valley_wind(seconds, delay=delay, level=level * 0.38)
        self.falling_snow(seconds, delay=delay, level=level * 0.10)
        self.gait(seconds - 0.4, delay=delay + 0.2, level=level, deep=deep,
                  temperature_c=temperature_c)
