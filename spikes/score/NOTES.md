# The trailer's score, procedurally, in the game's own mixer

2026-09-09. Built to `TRAILER.md` §5 as revised, with `SOUND-DESIGN.md` §8 as the buildability
argument. Nothing is sampled and nothing was added to the dependency list: every sound in both
WAVs is `phase1/audio/` synthesising it.

**Nothing here is committed.** Two `.wav` files, an `.svg` and this note are new on disk; `*.wav`
is already gitignored.

---

## 1. What is here

| file | what it is |
|---|---|
| `spikes/score/trailer.json` | **the score.** Every pitch, level, entry and room setting. Hand-editable. |
| `spikes/score/trailer-score.wav` | the full two minutes, 48 kHz, 24-bit, stereo, 120.000 s |
| `spikes/score/trailer-score-descent.wav` | 0:45–1:10 on its own, 25.000 s, cut from the same render |
| `spikes/score/surface-ambience.wav` | the diegetic recipes, one per slot, with a cue sheet |
| `spikes/score/trailer-score.svg` | RMS and F50/F85 against the structure |
| `spikes/score/measure.py` | the analysis. Reads a WAV, no dependencies beyond numpy |
| `phase1/audio/score_spec.py` | the JSON grammar, and only that |
| `phase1/audio/score.py` | the transport. A state machine over time, in `ratchet.py`'s shape |
| `phase1/audio/score_event.py` | what the transport emits: data, no engine |
| `phase1/audio/score_render.py` | the offline render and the CLI |
| `phase1/audio/surface.py` | wind, rain on steel, water in a pipe, a drip, a footfall, a servo, iron under load, a yard hum, and two composed shots |
| `phase1/audio/surface_render.py` | the ambience render and its CLI |

**One existing file changed**, minimally, and §4 says why: `phase1/audio/voice.py` gains
`set_sample_rate()`, ten lines and a docstring. Nothing else in `phase1/` is touched. The game
still runs unchanged — `python -m phase1 --headless` completes and the engine is still at 44.1 kHz
at import, because the function is inert unless a caller asks for a different rate.

### The commands

```
python -m phase1.audio.score_render                                   # the whole two minutes
python -m phase1.audio.score_render --from 45 --to 70 --out X.wav     # the descent alone
python -m phase1.audio.score_render --plan                            # the schedule, no audio
python -m phase1.audio.surface_render                                 # the ambience contact sheet
python spikes/score/measure.py spikes/score/trailer-score.wav --envelope --harmony --svg OUT.svg
```

Both renders are a few seconds. The render is deterministic: block-synchronous, no wall clock,
no device.

---

## 2. How the score is defined, and how to change a note

The score is **data**. `trailer.json` holds it; `score.py` holds the grammar and nothing else.

The grammar is one idea repeated. A **section** is a span of the trailer. A **line** is one voice
of the score inside a section: a timbre, a pitch, a level, a room, and how often it strikes. A pad
is a line that strikes every nine seconds and rings for fifteen. The pulse is the same line
striking every second and ringing for a third of one. **There is no pad type and no pulse type**,
which is why the transport is 150 lines and not 500.

**To change a note**, do one of three things and nothing else:

1. **Change a line's pitch.** `"pitch": "A2"` → `"pitch": "E2"`, or `"pitch": 96.5` for a literal
   frequency. Names resolve through the `pitches` block at the top.
2. **Change the tuning.** Edit a number in `pitches` and every line using that name moves. The
   whole piece is in D; retuning it is eight numbers.
3. **Add or delete a line.** Copy a line object into a section's `lines` array. It needs `id`,
   `timbre`, `pitch`, `amp`, `duration_s`; everything else has a default.

Other knobs, all per line: `pan`, `quality` (the room — low is far, duller, wetter, longer tails),
`attack_s` (a long attack **is** the crescendo; see §4), `decay_s`, `every_s`, `at_s`, `until_s`,
`accent_every`/`accent_amp`, `glide_to`, `detune_cents`, `max_reflections`. `amp_to` and
`quality_to` interpolate across the section, which is the only automation there is.

**Unknown keys are an error, not a shrug.** A misspelt `duration_s` is a note that does not sound
with no way to find out why, so the loader names the offending key and refuses.

**`Score.band_report()` runs before every render** and checks, structurally, that no audible partial
of any line lands in 400 Hz–3 kHz. A partial is `ratio × f0` and that is knowable from the document,
so a wrong note is caught before it is heard. It currently reports clear.

### What the score actually is

| | | |
|---|---|---|
| **centre** | D | struck bar on `HAMMER_ANVIL_PARTIALS` (1, 2.09, 3.42) |
| **the chord** | D–A–E, stacked fifths | open, warm, and committed to neither major nor minor |
| **tempo** | 60 BPM | from the fiction. Nine ratchet clicks at 1 Hz. Every pulse strike is on an integer second and the accent falls every ninth |
| **0:00–0:05** | nothing | the ratchet at 0:03 stays naked or the payoff at 1:39 becomes a musical callback |
| **0:05–0:26** | Act I. D2, A2, D1. No pulse. Attacks of 3.6–5.0 s | the score does not begin, it is found to have been there |
| **0:26–0:50** | Act II. Adds A3 and E4, and the pulse at 0:28 | the only warm act, the only place it is allowed to be pleasant |
| **0:50–0:57** | **harmonic event 1.** D2/A2 → D1/A1, the top deleted, the room opened | drops a register and loses its top |
| **0:57–1:01** | **harmonic event 2.** The centre moves D1 → E♭1 over a held A1 | a tritone. It never resolves |
| **1:00** | the pulse stops a beat early | `RATCHET_BREATH_S` in miniature: the held breath before the event, except the event is the silence |
| **1:01.000** | **the stop.** Everything muted over 8 ms | |
| **1:01–2:00** | exactly zero | 59 seconds of digital silence, in the file, on purpose |

---

## 3. The one place I did not do what I was told, and it is a contradiction in the spec

`TRAILER.md` §5 says both of these, four paragraphs apart:

> **It does not come back.** Not for the machinery, not for the lie, not under the title.

> …it is why the fold at 1:45 gets no silence: the diegetic layer plays its ordinary, cheerful
> housekeeping chime, and **the score does the fold.**

The score cannot do the fold at 1:45 if it stopped at 1:01 and never comes back. `SOUND-DESIGN.md`
§8.1's act-by-act table is the older reading (*"Returns at 1:04 with the lamp"*), and `TRAILER.md`
§5's revision — which is the newer document and the one I was given as the specification —
supersedes it everywhere except in that one sentence, which reads as a leftover.

**I took "it never comes back" as load-bearing**: it is stated three times, once with the lie named
explicitly, and it is the structural claim the whole cut rests on. So the second harmonic event is
at **0:57**, inside the score's surviving span, and the score's last sounding chord is the moved,
unresolved centre. It then never resolves for the remaining 59 seconds and the film ends. That is a
relocation, not a removal: the specified musical function — *the centre moves a semitone and never
resolves* — is delivered literally, and arguably harder, because the unresolved chord is the last
thing you hear before the hole.

**If the designer wants it back at 1:45 instead, it is one edit and no code.** Change `stop.t_s` to
`105.0` and add a `fold` section from 105 to 120 with the same lines. I have not done it because
doing both would be a feature and doing only that would contradict the section three times over.
**This is the first thing to put in front of the designer.**

---

## 4. What was already in the engine, and what I added

`SOUND-DESIGN.md` §8.3 claims the whole pitch layer needs zero new code. **Verified, with two
corrections.**

**True as stated.** `Voice` already takes a waveform, an f0→f1 sweep, duration, amplitude, pan,
attack, decay, delay, envelope shape, an arbitrary partial stack and noise band limits.
`Mixer._struck()` builds the inharmonic struck-bar stacks. `Placement.for_sound()` builds the
room. `Mixer.render_offline()` plus the method in `view/recorder.py` gets it to a WAV. Every
timbre, every note and every tail in this score is those four things and nothing else.

**Correction 1: the pitch layer does not go through `Mixer._room()`, and should not.** `_room`
sets `attack=place.attack`, which is right for everything it was written for — attack is a distance
cue, a transient that crossed a hundred cells arrives smeared, and no world sound gets a say in it.
A four-second swell is not a distance cue, it is the gesture. So `score_render._queue` replicates
`_room`'s body with exactly one change, `attack = max(the line's, the placement's)`, and takes the
reflections themselves straight from `Placement.for_sound` unchanged. The score is in the same
room, on the same reflection pattern, at the same delays and dullings as every world sound.
`Mixer.ratchet_notch` sets the precedent: it builds its own direct voices and loops
`place.reflections` for the same kind of reason.

**Correction 2: two of §8.3's four "needs new code" items were not needed.**

- *"Two buses, so the world can duck the score one-way."* Not needed for a **stem**. The score is
  rendered alone, so everything `Mixer.duck` can reach *is* the score, and `duck` already does
  one-way ducking by being pointed at a mixer that only has score in it. A bus field becomes
  necessary the day the score and the world are mixed in one process, which is the game and not the
  trailer.
- *"Amplitude automation upward, ~20 lines."* Not needed. A crescendo is successive strikes at
  rising amplitude, which is `amp_to` in the data. A swell inside one strike is the envelope's own
  attack: `Envelope.curve` ramps `clip(t/attack, 0, 1)` linearly from zero, so `attack_s: 5.0` is a
  five-second linear fade-in and Act I's entrance is three of them. **`Voice` has had an upward
  amplitude ramp all along; it is called `attack`.**

So the new code is the transport, the grammar, the renderer and the analysis. The estimate of
~200 lines for transport-plus-buses-plus-automation was about right for the part that was needed.

**The one edit to an existing file.** `voice.py` gains `set_sample_rate(rate)`. The game opens its
device at 44.1 kHz; the assembler wants 48. Synthesising at 48 is better than resampling, because
every frequency in this package is in Hz and every duration in seconds, so **nothing about the
sound changes** — it is the same score, sampled more often. The one thing that does move is
`Voice._noise`'s moving-average corner, which is `0.44 × rate / width` and therefore rises with the
rate; `Score.band_report` computes that corner at the score's own rate rather than assuming 44.1.
Two modules import the constant by name (`mixer`, `view/recorder`) so the function rebinds those
too. It is a function in the audio package rather than a caller poking module attributes because a
rate change that is invisible in this package is a rate change nobody will find.

**The stop is `mixer.py` running, not a fader.** `Mixer.duck(0.0, 0.008)` is the crash's own
mechanism — `CRASH_DUCK` and `RATCHET_BREATH_DUCK` already pull everything sounding down and hold
it — aimed at the score. §6.3's distinction between *quiet* and *gone quiet* is the whole point:
**a silence that arrives is an event.** It lands sample-exact because 61.000 s at 48 kHz in
480-sample blocks is block 6100 with no remainder.

---

## 5. The measurements, and what each is a proxy for

**I cannot hear any of this.** Every number below is a deliberate substitute for a listen, and the
substitution is named each time. `spikes/score/measure.py` reproduces all of it.

| measurement | what it stands in for | what it cannot say |
|---|---|---|
| **RMS envelope**, 100 ms windows and 2.5 s blocks | Does the shape match §5's table — enter at 0:05, tighten, narrow at 0:50, stop at 1:01? A structure right on paper and flat in the render is the likeliest failure and the easiest to miss | whether the build feels like a build or like a slow volume knob |
| **F50 / F85** — the frequencies below which half and 85% of the power lies | register, and "loses its top". A one-octave drop should roughly halve F50 | whether the drop reads as *going down a shaft* or merely as *bass* |
| **power-weighted centroid** | kept because it is the standard number | see the box below |
| **400 Hz – 3 kHz occupancy**, as a fraction and as an absolute level | not a proxy — it is the rule. `tuning.py` reserves that window for everything that must be *identified* | nothing. This one is a fact |
| **300 Hz / 12 dB-per-octave RMS** | a laptop. The mixer's own model, from `Mixer.hammer`'s docstring, where a hammer was measured losing 14.6 dB through it | how loud a real laptop is in a real room |
| **peak component list** per passage | evidence for the two harmonic events: which frequencies are actually present | whether D→E♭ is the right semitone |
| **amplitude-modulation rate** in the fold | the beating that makes a low tritone sour rather than merely low | whether sour is what a viewer feels |
| **the 5 ms grid across 61.000 s** | whether the stop is a stop | — |

> **A measurement I threw away, because it was lying.** A magnitude-weighted spectral centroid read
> **1400 Hz** during Act II in a window where **99.5% of the power was below 400 Hz**. There are two
> thousand FFT bins above 400 Hz and eighteen below it, so summing magnitudes counts *bins* rather
> than energy, and the statistic was reporting the width of the noise floor. F50 replaced it. This
> is worth writing down because a centroid is the obvious first thing to reach for and on this
> material — a handful of very low partials against a wide empty spectrum — it is the wrong tool.

### The structure, measured

```
passage                            t  RMS dB  peak dB   F50   F85  400-3k  in-band dB  laptop dB
naked                           0-5s  -240.0   -240.0     0     0  0.000%      -240.0     -240.0
I  the place                   5-26s   -35.6    -30.2    90   109  0.000%      -116.4      -52.7
II  the teaching              26-50s   -26.0    -20.0    77   100  0.009%       -51.4      -42.8
III descent                   50-57s   -29.6    -25.7    53    82  0.008%       -57.3      -48.7
III fold                      57-61s   -27.7    -23.8    46    58  0.001%       -67.9      -52.7
IV-VI  gone                  61-120s  -100.7    -45.3     0     0  0.001%      -106.8     -154.4
```

- **The build is 9.6 dB**, Act I to Act II, and it is monotone in the 2.5 s table: −39.7 at 0:05,
  −34 through Act I, −27.9 at 0:25 as Act II arrives, up to −22.5 at 0:42.
- **The reserved band is clear.** Worst case anywhere in the piece is **0.363% of power, −51.4
  dBFS** — thirty-three decibels under a routine heard ping. It is not zero, and the reason is
  named in the JSON: `Voice._noise` low-passes by moving average, which is a real filter with a poor
  stopband, so the pulse's `knock` leaks a little. Widening it from 66 to 96 took the worst case
  from −48.4 to −51.4 dBFS. Anything below that costs the beat its definition.
- **The peak is −14.0 dBFS.** Deliberately conservative; a stem's level is the assembler's call and
  a stem that has been normalised up is a stem whose level is a fact about my script. The renderer
  only ever attenuates, and says so loudly if it has to.
- **L/R correlation +0.887.** The field is narrow, and most of that is honest — the piece is mostly
  below 120 Hz, where stereo width is largely notional — but see §7.

### The descent

```
III  the descent  (51.0–56.0s)      36.6 +0.0   54.9 −1.0   73.4 −8.7   76.7 −10.4  110.0 −6.8  125.6 −15.8  251.4 −20.0
II   the teaching (42.0–48.0s)      36.7 −22.0  73.4 +0.0  110.0 −15.0  153.4 −19.3  220.0 −20.0  251.1 −18.8
```

**The register drop is real and it is visible in the components, not just in a statistic.** Act II
is built on D2 = 73.4 as its loudest thing with A2 = 110 fifteen decibels under it. The descent is
built on D1 = 36.6 and A1 = 54.9 within a decibel of each other, with D2 present only as the pulse,
8.7 dB down. F50 falls **77 → 46 Hz across 0:50–1:01**, which is 0.74 of an octave rather than a
full one, and the reason is deliberate and in the JSON: *the pulse does not drop with the bed*. At
36.7 Hz a beat is a movement of air rather than a beat, and the pulse is the only thing left for a
viewer to hold on to. It moves away instead — quality 0.55 → 0.30, the same object further off,
wetter and duller.

**F85 falls 100 → 58 Hz**, which is "loses its top" measured: A3 = 220 and E4 = 329.6 are simply not
in the descent section, and Act II's tails decay across it rather than being chopped, which is what
the picture is doing at the same moment.

**And a real problem the measurement found.** The score lives below 400 Hz by rule, so it is the
thing in this build most exposed to a small speaker, and the descent makes that worse by design. The
first render measured the fold at **29 dB below** its true RMS through the 300 Hz laptop model — the
descent would have been nearly inaudible on the machine most people will watch a trailer on. The
cause was specific and would not have been guessable: the `deep` timbre carries a fourth ratio at
6.85 precisely so that something lands at 250–380 Hz when the fundamentals are at 37 and 55, and at
`tilt: 1.5` that partial's gain fell **under `Voice._PARTIAL_FLOOR` of 0.02 and was never
synthesised at all.** The partial that existed to survive a laptop was the first thing thrown away.
Tilt is now 0.85 and the quality floor on those lines is 0.24; the gap is now 23–25 dB, in line with
the rest of the piece. **This is still the score's biggest playback risk and it needs a human ear on
a bad speaker.**

### The stop

```
    t      RMS dB (5 ms)          window     RMS dB
60.900          -29.1          58.0-58.5      -26.3
60.980          -31.5          58.5-59.0      -26.8
60.995          -29.7          59.0-59.5      -27.3
61.000          -33.1  <- cut  59.5-60.0      -27.8
61.005          -51.7          60.0-60.5      -28.4
61.010         -240.0          60.5-61.0      -29.1
```

**It is a stop and not a fade, on three separate tests.**

1. **The level is not already falling.** −1.22 dB/s over the three seconds before the cut, and the
   0.5 s table shows −26.3 → −29.1: **2.8 dB across three seconds.** That is struck metal decaying,
   which is what struck metal does. A fade would be tens of decibels.
2. **The cut takes 8.0 ms.** Last non-zero sample at 61.0080 s. Eight milliseconds is roughly four
   cycles of the lowest note in the piece — below the threshold at which a level change is heard as
   a gesture rather than as an edit. It is there so the cut does not click, and nothing else.
3. **What follows is nothing, exactly.** From 61.008 s to 120.000 s every sample is a hard zero.
   Not a room tone, not a noise floor, not a reverb tail. 58.99 seconds of it.

The cut drops from −29.1 dBFS to digital silence: about **60 dB of instantaneous discontinuity**, out
of a level 3 dB below the score's own busiest passage. Whether that *lands* is a human question. The
measurement can only say it is not a fade, and it is not.

### The fold

```
III  the fold (57.5–60.5s)   36.6 −3.5   38.8 +0.0   54.9 −0.6   76.7 −22.1   81.3 −21.1   125.6 −20.2   132.9 −24.8
fold beat rates: 16.09 Hz under 120 Hz (the partials), 2.11 Hz under 45 Hz (the fundamentals)
```

E♭1 = 38.8 arrives as the loudest component with **D1 = 36.6 still ringing 3.5 dB under it** and
A1 = 54.9 held level with both. The old centre is not replaced, it is still there — so the fold is a
semitone *cluster*, not a move, which is the sound of something not resolving rather than something
going somewhere. The two predicted beats are both present: 2.11 Hz between the fundamentals (a slow
swell; 2.18 predicted) and 16.09 Hz between their upper partials (132.9 against 115.0 is 17.9 Hz;
125.6 against 110.0 is 15.6 Hz), which is inside the roughness band and is why a low tritone here
sounds sour instead of merely muddy.

---

## 6. The ambience — what got built, and which of it is thin

Done second, on the document's own judgement that if only one thing gets made it should be the
score. `phase1/audio/surface.py`, rendered by `surface_render` to a contact sheet with a cue sheet.

**Why it is not on `Mixer`, and should not be.** Every recipe on `Mixer` is driven from `Belief` and
placed by `Placement`, because underground the player is listening *through a machine*. §5.7's whole
point is that the surface is the one place with no machine in between. These take a pan and a level,
are not derived from a `Belief`, and cannot reach the cave. Putting them on `Mixer` would put
un-sensed material inside the object whose entire contract is that everything in it came through a
sensor.

| recipe | verdict |
|---|---|
| **drip** | **The best thing in the file, and not thin.** The rising sweep is physics, not taste: the cavity a drop leaves closes as it fills, so its resonance climbs over about forty milliseconds. That is why a drip is recognisable at any level, and `Voice`'s one linear sweep is exactly the right shape for it. |
| **iron under load** | **Good.** Both halves are things this engine is genuinely good at — a slow downward sweep on an inharmonic stack (a loaded member's modes drop as it deflects, and that fall is what says *taking weight* rather than *ringing*), and a train of stick-slip grains with accelerating, irregular spacing. Real mechanism, not texture. |
| **footfall** | **Thin.** A good thump and a plausible surface. A footfall's character is mostly in the twenty milliseconds *after* contact — grit, a roll, a pad flexing — and none of that is a shape `Envelope` has. Reads as *a machine putting a foot down*, not as *this machine on this floor*. |
| **servo** | **Thin, and I can say exactly where.** The three-part pitch envelope (engage, run, stop) is right and is what stops it sounding like a fan. What is missing is the **cogging ripple** — amplitude modulation at the gear-mesh rate — and that is the part the ear uses to say *geared actuator*. The mesh partials are buildable here and are in it; the ripple needs per-sample amplitude modulation, which `Voice` cannot do because the envelope is one curve applied once. |
| **rain on steel** | **Thin in one specific way.** The two-layer structure is right — the mass of it is a hiss with no events in it, the ones that hit metal near you are events with a struck-plate stack. But every grain is the same envelope with a different seed and level. It reads as rain at a distance and as a shaker up close. The fix is not more code, it is `Waveform::GRAIN` — the one seam §5.10 proposes leaving open, and this is the family that wants it first. |
| **wind** | **The thinnest thing here.** Real wind is a filter whose corner moves: a gust is not a level change, it is the sound getting *brighter* as it gets louder and then rougher as it finds an edge. `Voice` low-passes once, at construction, and cannot sweep a corner. Stacking three fixed bands at different levels only approximates the colour change. It will pass under a wide shot with something on top of it. **It will not survive being the only thing in a frame** — which is exactly what shot 2 asks of it. |
| **water in a pipe** | Adequate. It is the drip carrying it. |
| **yard hum** | Thin by construction and deliberately. A yard is a hundred small sources and this is four. What it does is stop Act I being a hole between events. |
| **headframe** (shot 2) | Composed. Wind + iron + hum + drips. Holds, but it is the wind carrying the width and the wind is the weak one. |
| **bench** (shot 6) | Composed. Servos, footfalls, the frame settling, the yard behind. The strongest composed shot, because it is made of events rather than of bed. |

Measured per slot: F50 ranges from 27 Hz (iron) to 2166 Hz (rain), so the recipes are at least
occupying different registers from each other and from the score. **Peak simultaneously *sounding*
voices across the whole sheet is 21 of the live cap of 48**, so none of this is unaffordable live —
the offline render raises `AUDIO_MAX_VOICES` only because it lays a whole shot out in one call, and
that is stated in the module.

---

## 7. What needs a composer rather than a programmer

Honest list, and §8.3 already named the first one as the place it would not trust a default.

1. **The notes.** D, D–A–E, and D→E♭ are my choices and they are the least defensible thing in this
   note. `_struck(ratios)` supplies a mechanism; it does not supply a tune. The structural
   questions — where it drops out, what the descent does, which register is forbidden, how long the
   hole is — are now answered *in the right material*, which is what makes this a brief rather than
   a deliverable.
2. **Whether E♭ is the right semitone.** Up against a held fifth gives a tritone, which is the
   strongest available statement of *does not resolve*; down to C♯ against A resolves to a
   first-inversion A major and would be actively wrong. That is the whole of my reasoning, and it is
   a rule of thumb rather than a musical decision.
3. **Anything with a performance in it.** Every strike here is on an exact integer second or an
   exact multiple of 8. A player would not be. There is no rubato, no variation of touch and no
   asymmetry anywhere in this piece, and that is the wall §5.10 names for the machinery arriving in
   the music.
4. **The Act I entrance.** Three overlapping five-second attacks is a mechanism for entering
   unnoticed. Whether it enters *well* — whether 0:05 to 0:14 is patient or merely empty at
   −35 dBFS — is the single most likely thing to be wrong and no measurement I have touches it.
5. **The stereo image.** +0.887 correlation. A composer or a mixer would decide whether this piece
   wants to be that narrow. My reflections are the only width in it and they come from
   `Placement`, which was built for locating a contact, not for making a score wide.
6. **Whether the pulse should be there at all in the descent.** I kept it and moved it away.
   Deleting it at 0:50 and leaving only the bed is the other reading of *narrows*, and it is one
   line in the JSON.

---

## 8. Every guess, in one list

1. **That "it never comes back" beats "the score does the fold at 1:45"** where `TRAILER.md` §5 says
   both. §3. **This is a designer question and it is the important one.**
2. **The notes themselves.** D as the centre; D–A–E stacked fifths for Act II; E♭ up a semitone for
   the fold; D1/A1 for the descent. §7.1, §7.2.
3. **That the second harmonic event at 0:57 with four seconds to sit before the cut is enough time
   for it to register.** It could be too short to be heard as a move rather than as a new note.
4. **The section boundaries at 0:05, 0:26, 0:50, 0:57 and 1:01.** The first four are `TRAILER.md`'s
   shot times; 0:57 is mine and comes out of guess 1.
5. **That the pulse stopping at 1:00, one beat before the cut, reads as a held breath and not as an
   accident.** It is `RATCHET_BREATH_S`'s logic transplanted, and that mechanism has never been
   heard by a tester either (§10 of `SOUND-DESIGN.md`, last item).
6. **That 8 ms is short enough to read as a cut and long enough to not click.** Standard practice;
   not measured against an ear here. The click, if there is one, would be at the very bottom of the
   spectrum where the fundamentals are.
7. **That an all-zero stem is what an assembler wants** for 1:01–2:00, rather than a shorter file.
   It is what makes the score's not-coming-back a property of the file rather than something an
   editor has to remember.
8. **Levels.** −14.0 dBFS peak, −26 dBFS RMS at the loudest passage, a 9.6 dB build across Acts I
   and II. All chosen so the shape reads; the absolute values are the assembler's to set.
9. **That the 300 Hz / 12 dB-per-octave model is a fair stand-in for a laptop.** Inherited from
   `Mixer.hammer`'s docstring, where it was already used to make a decision; neither there nor here
   has it been checked against a real speaker.
10. **That 0.363% of power at −51.4 dBFS in 400 Hz–3 kHz counts as "stays out of the band".** The
    rule does not give a threshold. It is 33 dB under a routine ping.
11. **That the descent keeping the pulse at D2 is right**, at the cost of the register drop
    measuring 0.74 of an octave instead of one. §5.
12. **That `deep`'s fourth ratio at 6.85 is the right way to keep the descent on a small speaker.**
    The problem is measured; the remedy is mine and it is a compromise with "loses its top".
13. **That rendering at 48 kHz rather than resampling is worth a ten-line change to `voice.py`.**
14. **That the ambience recipes belong beside `Mixer` rather than on it.** §6. It follows from §5.7
    but §5.7 does not say it.
15. **That `bench` and `headframe` are the right two shots to compose.** Chosen because they are the
    two the shot list holds longest, not from a cut.

---

## 9. What I would do next, in order

1. **Ask the designer about §3.** Everything else is tuning; that is a structural decision I made on
   a reading of a contradiction.
2. **Play the descent WAV on a laptop speaker and on something with a woofer.** The gap between
   those two is the score's biggest risk and it is measured at 23–25 dB.
3. **Audition the whole two minutes against picture**, because every level in it was chosen to make
   a shape legible in a table and none of it has been heard against a cut.
4. **Then hand `trailer.json` to a composer as the brief**, with §7 as the list of what to replace.
   The structural questions are answered in the right material; the notes are not.
