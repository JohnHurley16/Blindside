# The valley score, and snow — 2026-09-10

Written against `docs/TRAILER.md` as the designer rewrote it this morning: **one continuous
journey in seven movements, no acts, no text cards.** The score that was here yesterday was
built for six acts, five cards and a hard stop at 1:01 under a card, and none of those exist
any more.

`NOTES.md` is the previous pass and is left alone. So are `trailer.json`,
`trailer-score.wav`, `trailer-score-descent.wav` and `surface-ambience.wav`: nothing about the
old score was deleted, and it is one command away if any of this turns out worse.

**Nothing here is committed.** Everything is synthesised in `phase1/audio/`; no samples, and
no new dependency.

---

## 1. What is here

| file | what it is |
|---|---|
| `spikes/score/valley.json` | **the score.** Every pitch, level, entry and room setting, hand-editable |
| `spikes/score/valley-score.wav` | the whole piece: **108.000 s, 48 kHz, 24-bit stereo, peak −16.9 dBFS** |
| `spikes/score/valley-stairs-and-cave.wav` | 0:44–1:12 on its own, 28.000 s, cut from the same render. §6 says why this passage |
| `spikes/score/snow-contact-sheet.wav` | seventeen snow slots with a cue sheet, 130.270 s |
| `spikes/score/snow-cues.json` | where every slot is, written by the render so nobody types a timecode twice |
| `spikes/score/valley-score.svg` | RMS and F50/F85 against the seven movements |
| `spikes/score/measure2.py` | the analysis. numpy only |
| `phase1/audio/snow.py` | **new.** Feet, wind, spindrift, falling snow, and the deadness |
| `phase1/audio/snow_render.py` | **new.** The contact sheet and its CLI |

```
python -m phase1.audio.score_render --score spikes/score/valley.json \
       --out spikes/score/valley-score.wav
python -m phase1.audio.score_render --score spikes/score/valley.json --plan
python -m phase1.audio.snow_render
python spikes/score/measure2.py score spikes/score/valley-score.wav --svg OUT.svg --envelope
python spikes/score/measure2.py snow  spikes/score/snow-contact-sheet.wav
```

Both renders take a few seconds and are deterministic: block-synchronous, no wall clock, no
device, and the humanising is a hash rather than a random generator (§3.2).

**One thing I could not do and it needs doing by somebody who can.**
`spikes/godot/_assemble_cut.py` has `SCORE = spikes/score/trailer-score.wav` hardcoded, so the
assembler still lays the old score under the cut. That directory was off limits for this pass
(three agents are in it). **It is a one-line change and until it is made, the new score is not
in the video.** The assembler's `SHOTS` table is also still the old six-act order with five
cards in it, so it needs the same rewrite the treatment just had.

---

## 2. The structure, movement by movement

`TRAILER.md` §2's seven movements, taken literally as the score's boundaries. Total 107 s of
music in a 108.000 s file, which is about the "1:45" the treatment asks for; the last second is
the final tail dying rather than padding.

| | movement | t | chords | what the score does |
|---|---|---|---|---|
| 1 | The range | 0:00–0:20 | A5 · F · C | Enters out of nothing on an open fifth with **no third in it** — a mode would be an opinion about a mountain. The bass steps down a third to F, then to C, and the third arrives with the F. Attacks of 3–6.5 s: it is found to have been there |
| 2 | The machine | 0:20–0:30 | G · Am | **The tread enters at 0:21**, on the beat the camera arrives on the animal. Home for the first time at 0:25.5, and the minor third is stated in the middle of the chord rather than on top |
| 3 | The village | 0:30–0:45 | F · C · Dm · G | The only melody in the piece, four phrases over four chords, reaching E4 — the top of the film — and coming straight back down. Warmest and closest voicing |
| 4 | The stairs, and the hole | 0:45–0:55 | Am · G · F · Em | A bass walking **down by step**, which is the oldest descending figure there is and is here because the machine is going down stairs. The thirds thin at every step, the tread thins with them, and **the last footfall in the film is at 0:54.3**, at the edge |
| 5 | The cave | 0:55–1:25 | Fadd9 · Dm9 · B♭ · F/A | The room opens — quality falls to 0.26, three reflections instead of two — and **the tread is gone: there is no ground here.** The harmony goes one flat further out than it has been, the bed thins, and the frost above 3 kHz becomes a real layer instead of a dusting |
| 6 | Uncovering | 1:25–1:35 | C, and one struck iron | The loudest place in the film. C major in root position, and at 1:26.6 **the only note in 108 seconds with a hard attack** |
| 7 | The map | 1:35–1:48 | A across five octaves | About 14 dB under the cave. A1, E2, A3 and two A7s a cent apart. **The piece ends on the chord it opened on** |

**The chord chart is the section ids in `valley.json`.** One section per harmonic event, which
makes the document readable as a chart and is why the transport needed no new concept for it.

### What I kept from the old score, and why

- **The data/engine split.** `valley.json` holds the music; `score_spec.py` holds the grammar;
  `score.py` is a schedule; `score_render.py` is the render. That was the right call and it is
  the reason today could be spent on notes instead of on code.
- **The room.** The score still goes through `Placement.for_sound` and arrives with the same
  reflection pattern, delays and dullings as every world sound, and `score_render._queue`'s one
  deviation from `Mixer._room` — `attack = max(the line's, the placement's)` — is still exactly
  right and still the only one.
- **The 400 Hz – 3 kHz prohibition**, and it stopped being a constraint and became the idea. §4.
- **`Score.band_report` running before every render.** It is what the timbre ceilings in §3.1
  enforce, and a wrong note in the reserved band would be inaudible as a mistake. It reports
  clear for this score.
- **The measurement posture**: F50/F85 rather than a spectral centroid, and the 300 Hz laptop
  model. Both findings from yesterday and both still correct.

### What I threw away

- **The stop.** There is no `stop` block. The score thins rather than stopping, per §4 of the
  new treatment, and the 8 ms cut belonged to a card that no longer exists.
- **The tempo.** There isn't one. §3.2.
- **The iron.** §3.1.
- **The two-harmonic-events rule.** That was `SOUND-DESIGN.md` §8.1's, written for a film with
  five text cards doing the structural work. With no text, two events in two minutes is why the
  old one reads as sound design with a tempo. There are twenty chords now.
- **D as the centre.** A, because the piece has to come home and A minor's own relative-major
  neighbourhood (F, C, G, Dm) is the only chord set in common use that has no leading tone and
  no tritone in it anywhere. §5.

---

## 3. The three things the old score got wrong, and what each cost to fix

### 3.1 It was made of iron, and the world is made of ice

`bar` was `HAMMER_ANVIL_PARTIALS` — 1, 2.09, 3.42, a struck steel bar, the mast ringing after
the hit. Right for a mine.

The bed is now **1, 2.01, 3.05, 4.12: a slightly stretched harmonic series.** That is what a
large plate of ice or a thick pane does — nearly harmonic, so it is a pitch rather than a
clang, but stretched enough that its partials beat slowly against the note next to it, and
that slow beating is where the shimmer in the piece comes from and it is free. Three timbres
are the same material at three heights (`deep` ≤ 92 Hz, `body` ≤ 131, `reed` ≤ 198), because a
partial is ratio × pitch and the reserved band puts a ceiling on each.

**Iron appears exactly once**, at 1:26.6, on the old ratios, for the first iron the machine
finds in a cave of ice. Measured: of the 130 notes in the bed, **exactly one has an attack under
50 ms** and it is that one. Everything else swells, between 0.26 s and 6.50 s, median 2.00 s.
(The remaining 30 events are the tread, which is plucked.)

### 3.2 Nine strikes a second on integer seconds, and no touch

The old notes called this the least defensible thing in the piece and they were right.

There is no tempo now. The only pulse is **the machine's tread** — a plucked walking bass
alternating root and fifth, about one step every 1.15 s — and it exists only while the machine
is walking on the surface. It enters at 0:21 with the machine and its last step is at 0:54.3,
at the edge of the hole. **It never comes back**, because in the cave there is no ground.

**It is one gait walking through ten chords, not ten pairs of steps.** The `at_s` values are
chosen so the grid runs unbroken across every section boundary; the first version of this had
gaps of 0.23 s and 0.92 s where chords changed, which is a stumble.

**The code this needed**, and it is the second of two edits to existing files:
`score_spec.py` gains two keys and `score.py` gains about thirty lines.

- **`humanize_s`** displaces every strike by up to that much, and **`touch`** varies its level
  by up to that fraction.
- The displacement is **deterministic**: FNV-1a over the line's own id mixed with the strike
  index. Not `hash()` — Python randomises string hashing per process, so the same document
  would render two different performances and a bug report would not reproduce. Not `random` —
  a module-level generator is shared state and the schedule is walked block by block.
- **It is two thirds a value that only changes every third strike.** White jitter is not
  rubato, it is a badly quantised machine; a player pushes and drags across a phrase and varies
  the note inside that. The result drifts rather than rattling.
- `_line_events` widens its search window by the humanising amount **at both ends** and tests
  each candidate against its own displaced time, so a strike that drifts across a block
  boundary is emitted exactly once and by the block it actually lands in.

**Why a hash and not hand-written note times.** Composed timing belongs in `at_s` on a line of
its own, where a person chose it, and the whole bed is written that way — 130 individually
placed notes. A tread is not a performance, it is a **gait**, which is a stochastic process,
and a pseudo-random model is the right model for it. Splitting it that way is also why the
document is 900 lines and not 3,000.

Measured, over the whole gait: **30 steps, gap 1.147 ± 0.062 s, from 1.034 to 1.268 — 5.4 % of
the mean. Zero of the thirty land within 2 ms of an integer second. 10.9 dB between the
heaviest step and the lightest.**

### 3.3 Two harmonic events in two minutes

Twenty chords in 108 seconds, one per section, changing every 2.5 to 8 s. **And the tails were
shortened to make it audible**: the first render had chords ringing for 11–17 s under the two
that followed them, which is a cluster rather than a resonance. Durations are now 6–18 s with
decays of 2.0–8.0, so a chord is roughly 10 dB down by the time the next one arrives — present
as a tail, not competing as a harmony. That change also brought the voice count from **48 of
48, dropping strikes**, down to **42 of 48**, so the whole piece now fits inside the live
budget rather than needing an offline exemption.

---

## 4. The register rule stopped being a constraint

`tuning.py` reserves **400 Hz – 3 kHz** for everything that has to be identified by ear. That
leaves two windows: 20–400 Hz, and above 3 kHz.

So the piece is **a deep bed with a high frost over it and three empty octaves in between.**

That is not a compromise. It is what cold dense air with snow in it does to a sound, so the
rule and the world agree; and it is the answer to the problem the old score could not solve.
The old descent measured **29 dB below its own RMS through the 300 Hz laptop model** — nearly
inaudible on the machine most people will watch a trailer on — and the remedy was a partial at
6.85× dragged up into 250–380 Hz, which its own notes called a compromise with "loses its top".
**The frost sits at 3.1–5.6 kHz, where a small speaker is at its most efficient and loses
nothing.** No compromise, and it is also the coldest thing in the piece: ice, spindrift,
crystals in air.

Measured:

| | old score | this one |
|---|---|---|
| worst power in 400 Hz–3 kHz, while sounding | 0.363 % | **0.147 %** |
| worst absolute level in that band, anywhere | −51.4 dBFS | **−64.6 dBFS** |
| gap to the 300 Hz laptop model | 23–29 dB | **9–18 dB** |

Thirteen decibels further out of the reserved band, and six to fourteen decibels better on a
laptop.

---

## 5. The measurements, and what each is a proxy for

**I cannot hear any of this.** Every number is a deliberate substitute for a listen and the
substitution is named each time. `measure2.py` reproduces all of it.

### The shape

```
movement                 t  RMS dB  peak dB   F50   F85   400-3k  in-band dB     >3k   >3k dB  laptop dB
range                0-20s   -34.7    -30.6    60    96   0.131%       -69.3   0.16%    -63.3      -52.4
machine             20-30s   -31.1    -25.2    61   111   0.009%       -66.7   0.02%    -69.9      -47.9
village             30-45s   -30.3    -26.8    85   215   0.004%       -64.6   0.05%    -64.6      -39.4
stairs              45-55s   -31.2    -26.9    56   116   0.003%       -68.7   0.11%    -63.0      -47.9
cave                55-85s   -30.2    -25.0    59    89   0.001%       -71.0   0.40%    -56.0      -47.1
uncovering          85-92s   -29.5    -25.0    91   156   0.001%       -75.1   0.17%    -59.8      -42.4
to_black            92-95s   -35.5    -34.5    78   124   0.000%       -94.1   0.10%    -65.6      -49.6
map                95-107s   -42.9    -37.4    83   169   0.000%      -114.9   1.19%    -68.9      -55.8
```

- **The arc rises to the discovery and then falls off a cliff.** In 2.5 s windows: −43.3 at the
  head (arriving), −34 through the range, −30 through the machine and village, −27.4 in the
  window containing the iron strike, which is the loudest 2.5 s in the piece, and then −33.6,
  −35.6, −39.5, −41.7, −45.1, **−51.4** across the map. **The diminuendo into the map is 24 dB
  and it is written into the amplitudes rather than performed by a fader.**
- **F50 moves the way the picture does.** The village is the brightest low-register movement at
  85 Hz with F85 at 215 — warm, close, and it is the only movement with a melody in it. The
  stairs fall to 56 Hz, which is the descent measured. The cave sits at 59 and then climbs
  across its own thirty seconds — 49, 54, 68, 69 Hz over the four chords — because the bed
  thins and lifts as the frost takes over, which is the world becoming data as the light fails.
- **The frost is a real layer only where it is meant to be.** Above 3 kHz is 0.02 % of power in
  the machine movement and **0.69 % in the B♭ cave chord**, which is the flat-side lift and the
  most beautiful place in the piece; the map is 1.19 % because everything else has gone.

### Is it beautiful rather than ominous?

The only proxy I have, and it is a real one. Three specific things make music sound wrong and
all three are visible in the document: semitone and tritone verticalities between notes
actually sounding, two notes closer than a minor third in the bass, and beating in the 12–35 Hz
roughness band. The census evaluates `Envelope` at 0.25 s intervals and counts a note only
while it is within 20 dB of the loudest thing then sounding — comparing nominal amplitudes
credits a chord struck eleven seconds ago with forming an interval, and every piece ever
written contains a semitone if that is allowed.

- **No chord as written contains a tritone.** Twenty chords, checked by hand against the chart
  and reproduced by the tool: A5, F, C, G, Am, Dm, Em, Fadd9, Dm9, B♭, F/A, C5.
- **34 of 429 sounding instants contain one**, about eight seconds of the film, and every one
  of them is a decaying B against an arriving F across a G→F chord change on the stairs. That
  is what a chord change is. The worst is 6.00 semitones at 0:50.8, B2 dying against F3
  arriving.
- **The smallest vertical interval anywhere in 108 seconds is 1.00 semitones**, and it is two
  adjacent notes of the village melody overlapping — F4 into E4, which is legato.
- **The smallest interval below 200 Hz is also 1.00 semitones**, C3 into B2, the inner voice of
  the stairs stepping down. Same thing.
- **106 of 429 instants contain a minor second somewhere**, all of them voice leading of that
  kind; **225 contain a major second**, which is what a ninth is.
- **624 near-unisons**, and they are deliberate: the detuned pairs that make the width.
- One thing the measurement found and I fixed rather than reported: Em's fifth was at B1 =
  61.7 Hz, which made a tritone with the F1 still ringing under it **in the register where a
  tritone is muddiest.** It is at B2 now. Same interval class, an octave further apart, and the
  voicing E1–G2–B2 is better open anyway.

### Did anybody play it?

```
the gait: 30 steps from 21.04s to 54.32s
  gap 1.147 +/- 0.062 s (1.034 to 1.268), spread 5.4% of the mean
  steps landing within 2 ms of an integer second: 0 of 30
  touch: 10.9 dB between the heaviest step and the lightest, sd 31.2% of mean
  1.03 1.27 1.05 1.25 1.08 1.23 1.08 1.22 1.09 1.21 1.13 1.08 1.18 1.13 1.19 1.21
  1.15 1.15 1.13 1.15 1.11 1.18 1.07 1.23 1.09 1.16 1.19 1.13 1.11
```

Against the old score, where every strike was on an exact integer second and every one was the
same weight.

### Stereo

**L/R correlation +0.826** (old score: +0.887) and **side against mid −10.1 dB**. Correlation is
a whole-file average and side/mid is the honest number; both say the field is narrower than a
commercial mix and neither says whether that is wrong here.

The width that is there is bought where it is safe. **The root and the fifth of every chord are
panned apart and never detuned**, because two detuned copies of a fundamental cancel when
somebody plays the film in mono and the bass disappears at the null. The thirds and the upper
voices are split into hard-panned pairs four or five cents apart, which beat over several
seconds; the frost is always two different pitches at opposite edges. **A split pair at one
reflection each costs exactly what the single line at three reflections cost**, so the width was
free in voices.

This is still the thing about the piece I am least able to judge. §8.

---

## 6. The excerpt: 0:44–1:12, the stairs and the hole

`valley-stairs-and-cave.wav`. The strongest passage, and it is the hinge of the film rather
than the prettiest thirty seconds.

The bass walks down A–G–F–E while the thirds get quieter at every step and the tread thins with
them; the same four notes are stated two octaves up as pure sine; the last footfall in the film
lands at 0:54.3; the bass goes E→F, up a semitone, and the room opens underneath it. That
semitone is the door: the descending tetrachord's own semitone is F→E at 0:52.5 and the hole
answers it going back up. **They are the only two semitone moves in the piece and they are the
two halves of the same gesture.**

If any one passage is going to tell somebody whether this score works, it is this one, because
it contains the descent, the arrival, the disappearance of the pulse and the change of room
inside twenty-eight seconds.

---

## 7. The snow

`phase1/audio/snow.py`, rendered by `snow_render` to a seventeen-slot contact sheet. Four of
the slots are **controls and they are the point**, not padding.

### 7.1 The idea the whole file is built on

> **A footfall in deep snow is a compression, not an impact.**

An impact is a discontinuity: all the energy is in the first millisecond and everything after
it is a tail. Deep snow does not do that. The foot decelerates over 5–20 cm while the pack
densifies under it, and it goes on making sound the whole way down — in fact it makes *more* as
it goes, because the pack stiffens as it compacts and the crystal bonds that are failing get
shorter and stiffer and therefore higher pitched. **So the energy is spread over a tenth of a
second, the peak is late, and the spectrum climbs through the event.**

That is why `Surface.footfall` could not have been retuned into this. It is the wrong shape of
event, and the measurement says so:

```
event                   centroid  peak at  rise ms  to -20 dB ms  ring dB
one_deep_cold              0.334    0.341     88.0          46.2   -219.3
one_deep_mild              0.316    0.336     62.9          53.0   -214.5
one_packed                 0.076    0.041      1.5          47.2   -217.0
one_concrete               0.098    0.041      1.8          29.7    -39.5
```

`centroid` is the energy-weighted mean time as a fraction of a fixed 0.30 s window taken from
just before the onset; `rise` is 10 % to 90 % of peak; `ring` is what is left 200 ms after the
onset, against the peak.

- **The deep-snow footfall's energy centroid is 3.4× later than the concrete control's and its
  rise is 49× longer.** Its peak is 92 ms after contact. That is a compression and it measures
  as one.
- **The packed-snow footfall is an impact** — centroid 0.076, rise 1.5 ms, indistinguishable
  from concrete on those two numbers, which is correct, because a compacted pack does not yield.
  What separates it from concrete is the spectrum, below.
- **`ring_db` is the snow test and it is unambiguous.** Two hundred milliseconds after the
  onset, every snow footfall is at digital silence, −214 to −219 dB. The concrete control is at
  −39.5 dB and still going. Snow is the most absorptive thing anybody ever walks on and
  **nothing rings afterwards**; that absence is a large part of what says snow, and it is why
  nothing in this file goes through `Placement`.

### 7.2 Deep against packed, as spectrum

```
slot                RMS dB    F50    F85   <200  .2-1k   1-4k    >4k
one_deep_cold        -35.2   1380   3281   2.5%  28.3%  57.0%  12.2%
one_packed           -40.7   1239   3320  18.9%  24.7%  44.5%  11.8%
one_concrete         -36.2     89    114  90.4%   6.6%   2.0%   1.1%
```

Deep snow puts **2.5 %** of its power below 200 Hz. Concrete puts **90.4 %**. Packed snow puts
**18.9 %** — between them, and much nearer the snow, which is right: a packed layer transmits
into the ground under it instead of absorbing everything, but it is still snow.

**The first version of packed snow measured 77 % below 200 Hz** and read as a thump with some
grit on it rather than as a crunch with a floor under it. The thud is now a third of what it
was. That is a fix the measurement found and I would not have.

### 7.3 The squeak, and the temperature control

The squeak is the recognisable half of a snow footfall and it is a **threshold, not a slope**.
Near freezing, a foot's pressure melts the crystal contacts it is loading, so they slide
instead of breaking and there is no squeak at all; ten or fifteen degrees colder, nothing melts,
everything fractures, and the squeak is the loudest thing in the event. `squeak_strength()` is
that curve: zero at −2 °C, saturated at −14 °C.

It is built as **a band-pass whose centre climbs** — a swept low-pass minus a swept high-pass,
from 440–700 Hz to 1060–1760 Hz — with a faint swept tone inside it, because real
stick-slip partially locks and is not pure noise. It sits squarely in 400 Hz–3 kHz, and that is
correct: the reserved band exists *for* world sounds that must be identified by ear, and this
is one.

Measured, the same footfall at −14 °C and at −1 °C: **3.2 dB louder, rise 88 ms against 63 ms,
and 57.0 % of its power in 1–4 kHz against 43.1 %.** Different sounds rather than one sound at
two levels.

### 7.4 The wind — yes, it is fixable, and it is fixed

`surface.py`'s own note said why it could not be:

> *"Real wind is a filter whose corner moves — a gust is not a level change, it is the sound
> getting brighter as it gets louder, and then rougher as it finds an edge. `Voice` low-passes
> once, at construction, and cannot sweep a corner."*

**The first two sentences are right. The third has stopped being true.** `Voice._noise` now
takes a moving-average width that may be a *profile* rather than a number, resampled to one
width per sample, and the cumulative-sum trick generalises exactly: `(c[i + w(i)] − c[i]) / w(i)`
is the same identity with a varying window. It is about twenty lines and one gather. §9.

Two things fall out for free and both are physics rather than luck.

1. **A narrower window is brighter AND louder**, because averaging *w* samples of white noise
   scales its RMS by 1/√w. So a corner rising 200 → 60 samples raises the level 5.2 dB at the
   same instant. Nothing modulates anything: there is one filter and it is moving, which is
   what a gust is.
2. **A swept low-pass minus a swept high-pass is a band-pass whose centre moves**, which is
   what a squeak is.

```
slot                     min Hz   max Hz  octaves  corner v level
wind_open                   240     1107     2.20          +0.653
wind_fixed                  258      662     1.36          -0.155
```

`wind_fixed` is the old method kept in the render as the control: three fixed bands at
different levels with long envelopes. It moves through 1.36 octaves — because different gusts
happen to have different band mixes — and **its brightness and its level are uncorrelated**,
which is the defect stated as a number. The swept version moves through 2.20 octaves with the
two tracks correlated at **+0.65**.

**Two things had to be fixed before that number was true, and both were found by measuring.**
The first version measured **−0.41** — brighter while quieter, the exact opposite of a gust —
for two reasons. A long triangular envelope over the whole slot was driving the level from the
envelope rather than from the filter, so the corner and the level had stopped being the same
event; the envelope is a flat top with short ramps now. And each layer had its own independent
walk, so when one gusted another was in a lull and the sum flattened — which is also wrong as
physics, because **a gust is one body of air crossing a valley, not three winds.** The layers
now share a master walk, offset by about a second each, which is a gust arriving at three
points across the floor at three times.

The corner range was chosen by measurement too. Walking between widths 26 and 240 put only
21 % of the power below 200 Hz, which is a hiss and not a valley; 50 to 400 with the high-pass
eight times wider than the low-pass puts **47.5 %** below 200 Hz with the gust mechanism intact.

`Surface.wind` got the same treatment, and that is the only change to an existing recipe.

### 7.5 The deadness of air with falling snow in it

**It is not a sound and it cannot be added.** Falling snow scatters and absorbs across the whole
path, and the fresh layer on the ground removes the one reflection that is always there
outdoors, so nothing comes back from anywhere. It is the opposite of reverb, and the only
honest way to render it is to render the same event twice.

`valley_call` does that: one loud short event, and then the valley either answers it or does
not. In still air, three discrete arrivals — the near wall at 300 m (1.75 s there and back),
the far wall at 900 m (5.24 s), and one late scattered return off the up-valley slope, each
duller than the last. In falling snow, none of them, and the direct arrival itself loses its
top because the path from the source to the ear has snow in it too.

```
slot                    direct dB  after 1 s dB   gap dB  direct F85
call_still                  -27.3         -50.4     23.1         394
call_snow                   -29.9        -240.0    210.1         186
```

**In still air 23 dB of the event arrives late. In falling snow the file is exactly zero after
the direct sound**, and the direct sound's F85 has fallen from 394 Hz to 186 Hz. That pair is
the deliverable; neither half of it means anything alone.

`falling_snow` itself is deliberately almost nothing — a very faint high tick where flakes land
on something hard, and no floor under it. **The loud part of falling snow is what it does to
everything else.**

### 7.6 The gait

Four feet, and they are not evenly spaced. A symmetrical walk in the **lateral sequence** puts
a hind foot down and its own fore foot follows it closely, so the pattern is a pair, a gap, a
pair, a gap — 0.00, 0.22, 0.50, 0.72 of a stride — not four even beats. The fore feet are
louder because a quadruped carries about sixty per cent of its weight on them, and left and
right are panned apart so the thing walks across the field instead of standing in the middle of
it. It is four numbers and it is most of what makes a gait read as an animal.

`gait_deep` and `gait_packed` are the same walk on the two surfaces: **F50 1283 against 1351 Hz,
3.2 % against 18.6 % below 200 Hz, and 6.2 dB apart in level.** The same machine, two floors.

**Peak simultaneously sounding voices across the whole sheet is 15 of the live cap of 48**, so
none of this is unaffordable live.

---

## 8. What is thin, and what needs a human ear

Honest list. The first four are the ones I would look at first.

1. **The frost.** 3.1–5.6 kHz is the most sensitive part of the ear's range, and a tone up there
   is either shimmer or tinnitus with very little in between. Everything about it is
   defensive — level 30 dB under the bed, attacks of 2.2–4.5 s, never more than three at once,
   always consonant intervals of the chord standing — and I still cannot tell you which it is.
   **This is the single riskiest decision in the piece and it is also the one carrying the
   laptop.** If it whines, the fix is to drop every `frost` amp by half and accept a worse
   small-speaker number.
2. **Whether the melody reads as a voice or as a test tone.** Above 200 Hz nothing but a pure
   sine clears the reserved band, so the village melody is pure sines with a few cents of
   downward glide on each note. That glide is the only expression available inside one `Voice`.
   It may be enough and it may sound like a signal generator.
3. **The stereo image.** +0.826 correlation, −10.1 dB side against mid. A mixer would decide
   whether this piece wants to be that narrow. My reflections and my hard-panned detuned pairs
   are the only width in it, and `Placement` was built for locating a contact rather than for
   making a score wide.
4. **Whether the arrival at 0:20 is an arrival.** The range is three chords in twenty seconds
   and the tread enters at 0:21. If 0:00–0:20 is patient it works; if it is empty at −34.7 dBFS
   it is twenty seconds of nothing at the front of a trailer, and no measurement I have can
   tell the difference. This is the same risk the old score's Act I entrance had and I have not
   retired it.
5. **The tread's tempo.** 1.147 s a step is a decision, not a measurement. Faster reads as
   purposeful, slower as exhausted.
6. **Whether the map is too quiet.** 14 dB under the cave and a 24 dB diminuendo into it. It is
   meant to be a hush. It may be a mistake in a room with air conditioning in it.
7. **The squeak.** I have modelled the mechanism and I have never heard snow through this
   engine. Whether a listener hears "snow" or hears "a filter sweeping" is the whole question
   and it is not measurable.
8. **`falling_snow` and `spindrift` are thin by construction.** Both are one hiss and a grain
   train, and `surface.py`'s note about rain applies verbatim: every grain is the same envelope
   with a different seed, so it reads as texture at a distance and as a shaker up close. The
   fix is `Waveform::GRAIN` — the seam `SOUND-DESIGN.md` §5.10 proposes leaving open — and this
   is the third family to ask for it.
9. **Ice under stress is not built and it should be.** `THE-ICE.md` §6.3 names it: *"a real,
   loud, irregular, non-machine sound that is not an ancient system and does not lie… the only
   thing in the world that is loud and meaningless."* Movement 5 of the trailer is thirty
   seconds of ice cave. I did not build it because it is not in the brief and `CLAUDE.md` says
   not to add features, but it is the most obviously missing sound in this world.

---

## 9. The three edits to existing files, and why each is minimal

Nothing in `phase1/` was touched except these. `python -m phase1 --invariant` passes (8 rules),
`python -m phase1 --headless` completes a full 8:00 match, and **`trailer.json` — yesterday's
score — re-renders BIT-IDENTICALLY through all three edits**: 11,520,000 samples, every one
equal to the WAV that was on disk before any of this was written. That is the regression test
for all three changes at once, and it is why they can be called minimal rather than merely
small.

**1. `phase1/audio/voice.py` — a moving-average width may be a profile.** About twenty lines: a
`Width` type alias, `_width_profile` (returns `None` for a plain integer, so **every existing
caller stays on exactly the code path it was on** — no gather, no allocation), `_max_width`, and
one branch in `_smooth`. This is the change that makes the wind, the squeak and the compression
possible; without it all three are approximations of the wrong shape. It is not reflection and
it adds no import beyond `collections.abc.Sequence`.

**2 and 3. `phase1/audio/score_spec.py` and `score.py` — `humanize_s` and `touch`.** Two keys,
a hash, a wobble function, a widened search window in `_line_events` and one multiply in
`_event`. Defaults are 0.0, so the old `trailer.json` is unaffected.

**And one existing recipe changed**: `Surface.wind`, which is the method whose own docstring
said the wind could not be fixed. Same signature, same call sites, same three-layer idea; the
fixed bands became one walking corner. §7.4.

`voice.py`'s `set_sample_rate` was left exactly as yesterday's pass rewrote it after the
invariant checker rejected the `sys.modules` version. Nothing here reaches through a module
registry, and the checker agrees.

---

## 10. Every guess, in one list

1. **That the seven movements are 20/10/15/10/30/10/12 seconds**, taken literally from
   `TRAILER.md` §2's "~" figures. If the cut comes in at different lengths every boundary in
   `valley.json` moves, and it is twenty numbers rather than a rewrite.
2. **A as the tonal centre, and the chord set A–F–C–G–Dm–Em–B♭.** Mine. The argument is that it
   is the largest set in common use with no leading tone and no tritone in it, that it
   contains a real relative major for the discovery, and that ending where it began is what a
   map is. `_struck(ratios)` supplies a mechanism; it does not supply a tune.
3. **That the cave should go flat-ward.** B♭ at 1:11 is one flat outside A minor and it is the
   only chord in the piece that is outside the home key. It is the "beautiful before it is
   dangerous" moment and it is a taste decision.
4. **The lament tetrachord for the stairs.** A descending stepwise bass is literal — the machine
   is going down — and it is also a four-hundred-year-old figure for grief. Beautiful and sad
   are not the same as ominous, but the designer said beautiful and I chose sad.
5. **That the iron should be one strike and that it should be at 1:26.6**, 1.6 s into the
   discovery rather than on it.
6. **The frost's register and level.** §8.1.
7. **1.147 s a step**, and that the tread should stop at the hole and never return.
8. **That the map should be 14 dB down** rather than 6 or 25.
9. **That 108.000 s of stem with the tail dying inside it is what an assembler wants**, rather
   than a stem trimmed to the last note.
10. **Levels.** −16.9 dBFS peak, −30 dBFS RMS at the loudest passage. Chosen so the shape reads;
    the absolute values are the assembler's to set, and `write_wav` only ever attenuates.
11. **`SQUEAK_ONSET_C = -2` and `SQUEAK_FULL_C = -14`.** The shape — off, then a ramp, then
    saturated — is real physics. The two temperatures are mine.
12. **The compression's 150 ms and its 60 % peak position.** Real deep-snow footfalls are
    roughly this and I have not measured one.
13. **The valley's echo geometry**: 300 m to the near wall and 900 m to the far one, from
    `THE-ICE.md` §7.2's cross-section, giving 1.75 s and 5.24 s. The third return at 7.10 s is
    invented.
14. **That falling snow costs the direct arrival about 2 dB and half its F85.** The direction is
    certain and the magnitudes are mine.
15. **The lateral-sequence phases 0.00 / 0.22 / 0.50 / 0.72.** A real walk, not this machine's
    walk, and nobody has specified this machine's gait.
16. **That the 300 Hz / 12 dB-per-octave laptop model is a fair stand-in for a laptop.**
    Inherited from `Mixer.hammer`'s docstring and never checked against a real speaker, there or
    here.
17. **That −64.6 dBFS and 0.147 % of power counts as "stays out of 400 Hz–3 kHz".** The rule
    gives no threshold. It is 46 dB under a routine heard ping.
18. **That the interval census is a fair proxy for "beautiful rather than ominous".** It can
    only say the piece contains none of the specific things that reliably make music sound
    wrong. It cannot say it is beautiful, and that is the largest gap between what was asked
    for and what was measured.
