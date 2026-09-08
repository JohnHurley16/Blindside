# Agent probes — what was measured, including what failed

Produced for `docs/art/ART-DIRECTION.md`. Reproduce with:

```
./docs/art/agent/av_batch.sh
.venv/Scripts/python.exe docs/art/agent/av_measure.py
```

Blender 5.2.0 LTS, Cycles CPU, 960 × 600, 40 samples, AgX / Medium High Contrast, world
background strength 0. Every shot is lit only by sources the fiction supplies.

**All luminance figures are relative luminance with sRGB linearised first**, which is the
convention `palette.py:154-163` documents and requires. The last column of the exposure
table is the same statistic computed the wrong way, on gamma-encoded values, so the size of
the error is visible: a "5% legible" threshold on gamma-encoded values is **linear 0.0039**,
which is essentially black. Three of the four earlier probe passes
(`probes/im_lum.py`, `probes/lumstats.py`, `ruins/stats.py`) compute it the wrong way and
`probes/p2_stats.py` does not. No number from those three is comparable to any number here.

---

## 1. The head lamp fires backwards — confirmed by raycast

Not a render, a geometry query against the built rig.

```
AS BUILT   build.py:312  Euler((0, +pi/2, 0))
  lamp world origin : [+0.404, +0.000, +0.515]
  lamp -Z (beam dir): [-1.000, +0.000, +0.000]
  first hit         : 'eye_lens' at 0.014 m

PROPOSED                 Euler((0, -pi/2, 0))
  lamp -Z (beam dir): [+1.000, +0.000, +0.000]
  first hit         : nothing within 50 m
```

The spot's local `−Z` is its beam axis; `Ry(+90°)` sends it to world `−X`; the head's
forward is `+X`. **The lamp has never left the machine.**

Rendered, same shot, same 600 W, same everything, sign flipped:

| frame | mean | median | >0.5 | >0.18 | >0.05 | <0.02 |
|---|---|---|---|---|---|---|
| `av_01_lamp_asbuilt.png` | 0.0017 | 0.0000 | 0.12% | 0.24% | **0.36%** | 99.47% |
| `av_02_lamp_fixed.png` | 0.0115 | 0.0000 | 0.43% | 2.09% | **4.36%** | 93.49% |

**12× the legible fraction for one character.** This is the number that retires every "power
does nothing" table in the earlier passes: they were all measuring a light pointing into its
own lens.

---

## 2. Team identity — the value inversion is the best option tested and is still not enough

Mean CIELAB of the machine's own pixels (the brightest 10% at each downsample height, because
at nine pixels the machine *is* its brightest pixels). ΔE76 ≈ 2.3 is the just-noticeable
difference.

| scheme | 9 px | 24 px | 90 px | 300 px |
|---|---|---|---|---|
| **value inversion** — pale-over-graphite vs graphite-over-pale | **2.3** | **2.8** | **3.0** | **3.0** |
| value inversion, dust reduced 0.50 → 0.12 | 2.5 | 3.0 | 3.3 | 3.2 |
| **hue only** — same value, identity in the emissive, as built today | **0.6** | 0.6 | 0.8 | 0.9 |

Three readings, and the third is the one that matters:

1. **Hue alone does not work at any size.** 0.6–0.9 is a quarter of the JND. This reproduces
   the earlier pass's finding on a different scene, a different light rig and a corrected
   lamp, so it is not an artefact of either.
2. **Inverting the value is 3.5–4× better**, and it is the only channel tested that moves at
   all.
3. **It is still marginal in absolute terms** — 2.3 at nine pixels is exactly at the
   threshold. I tested and rejected the obvious explanation: dust in the rock's own colour
   settling on the horizontals was a plausible candidate for washing both teams toward the
   cave, but dropping dust from 0.50 to 0.12 moves ΔE by only 0.2–0.3. **Dust is not the
   limiter.**

The limiter is the metric as much as the design: a *mean* colour over the whole machine mixes
shell and chassis regardless of which one is pale, so inverting them is nearly invisible to an
average even when it is obvious to an eye. What a mean cannot see is **where** the pale is,
and that is what actually separates the two silhouettes.

**So the honest claim is narrower than "invert the value and it works":** value is the only
channel that survives at all, the inversion is necessary, and the remaining separation has to
come from *layout and rhythm* — which part is pale, and the blink pattern of the emissives —
neither of which this metric can score. **That needs a human A/B, not another render.**

---

## 3. Directional wear — it works, and the distribution is the proof

`av_03_wear_current.png` (isotropic noise ∪ inverted AO, as `materials.py` builds it today)
against `av_04_wear_directed.png` (three gravity masks, extended to the lower-leg materials),
same frame, same light, same `wear = 0.35`.

```
3.05% of pixels moved by more than 0.01 linear
the change occupies rows 89-512 -- that is the machine, 424 px tall
vertical centroid of the change: 0.505     (0.0 = machine's top, 1.0 = its feet)
  upper third : 39.4% of all changed pixels
  middle third: 24.0%
  lower third : 36.6%
```

**The bimodal distribution is the result, not the centroid.** A mask with no gravity in it
changes the machine uniformly. What three gravity-aware masks should produce is change
concentrated at *both ends* and less in the middle — dust settling on the top surfaces, mud
climbing the feet and tibias, and a comparatively clean waist. 39 / 24 / 37 is that signature.
A centroid of 0.505 looks like "no effect" and is actually two effects at opposite ends.

**Two cautions, both worth carrying into the build:**

- **The effect is modest at `wear = 0.35`** — 3% of frame at a raking inspection light. It is
  a real change and it is the cheapest one available, but the earlier passes' framing of it as
  transformative is not supported at this wear level.
- **It required a material change, not just a shader change.** `painted_metal` is bound only
  to `shell` and `chassis` (`build.py:95-101`); `tibia` is `carbon` and `foot` is `rubber`
  (`build.py:190-191`). A mud mask living inside `painted_metal` cannot reach the parts that
  touch mud. The probe reassigns the lower leg by hand. **Without that binding change the mud
  mask does nothing where mud actually goes**, which is what a previous attempt at this
  measured and correctly reported as a failure.

A third finding, from getting it wrong first: the leg material's `bare` colour must stay dark.
A muddy leg is mud *on* black, not paint worn *through* to bright metal. The first version of
this probe used the hull's bare-metal colour on the legs and made them lighter instead of
dirtier.

---

## 4. The backlit silhouette — framing matters more than the modules do

`av_08_sil_bare.png` (chassis plus `optical` only) against `av_09_sil_loaded.png` (full default
loadout), machine backlit by its own lamp pool.

| framing | pixels differing >0.01 | >0.05 |
|---|---|---|
| machine at the frame edge, pool beside it | 0.08% | 0.02% |
| **machine between camera and pool, outline on lit floor** | **0.71%** | **0.17%** |

**Nine times the read for a camera move.** The first framing put most of the machine's outline
against unlit rock, so the loadout was black-on-black and proved nothing. The claim that a
backlit machine is a loadout readout is true, but it is a claim about **where the camera is**,
not about the lamp: the silhouette only carries information where it falls on something lit.

That is a camera rule for the client, and it belongs with the light economy rather than with
the agent: **when the lamp is on, favour framing that puts the machine between the viewer and
its own pool.**

For scale, the four-studio-light hero framing moves 1.86% of frame between bare and loaded —
still more than backlighting, but it is a lighting rig that does not exist in a match.

---

## 5. The wreck — two failures, and they are the finding

The wreck is the one item in the art direction that a parameter could not express, and this is
the evidence for that rather than an assertion of it.

**Attempt 1 — ride height only** (`av_11_wreck_ridehonly.png`). `ChassisSpec.ride_height`
0.32 → 0.055, every emissive dead, wear 0.95, mud 1.0. **It reads as crouching, not dead.** A
dead quadruped is not a standing one lowered: the legs are still in a correct stance, evenly
spaced, weight plausibly on them.

**Attempt 2 — rig roll at 62°** (superseded). Rotating `AGENT_RIG` about X and moving the
`FOOT` empties produced a machine that read as **flipped and floating**: past roughly 45° the
pose stops meaning *fallen* and starts meaning *upside down*, and nothing in the rig knows the
hull can rest on the ground — only the feet have ground contact, so the body has to be dropped
onto the rock by hand.

**Attempt 3** — 40° roll, body lowered onto the rock, feet placed as a dropped machine's feet
land, one leg removed below the knee, the compute hatch deleted and a shed panel placed on the
floor beside it, found by a passing machine's lamp with nothing else in frame emitting.

The bounding-box aspect metric I wrote for this is **not usable** and I am reporting that
rather than quoting it: it measures the lit region of the frame, which is dominated by floor,
so it returns 2.09 against 2.13 for two obviously different images. Judge these two by eye.

**What `agent_model` would need**, which is the real output of this section:

| need | why the probe cannot fake it properly |
|---|---|
| `WreckSpec.collapse: float` driving **body roll plus a per-leg pose override** | roll alone floats the hull; the rig has ground contact only at the feet |
| `WreckSpec.shed: list[str]` | the probe deletes objects after build, which works once and is not a feature |
| `WreckSpec.emissive_scale: float` | currently a global walk over every material's emission node |
| `WreckSpec.spill: int` | there is no cargo geometry to spill |
| a hull ground-contact solve | so a collapsed body rests on the rock instead of hovering above it |

---

## 6. Exposure, all frames

| frame | mean | median | >0.5 blown | >0.18 mid | >0.05 legible | <0.02 black |
|---|---|---|---|---|---|---|
| `av_01_lamp_asbuilt` | 0.0017 | 0.0000 | 0.12% | 0.24% | 0.36% | 99.47% |
| `av_02_lamp_fixed` | 0.0115 | 0.0000 | 0.43% | 2.09% | 4.36% | 93.49% |
| `av_03_wear_current` | 0.0992 | 0.0557 | 0.61% | 22.08% | 53.01% | 37.02% |
| `av_04_wear_directed` | 0.0995 | 0.0561 | 0.60% | 22.14% | 53.21% | 35.91% |
| `av_05_team_player` | 0.0708 | 0.0220 | 1.30% | 14.01% | 39.02% | 47.68% |
| `av_06_team_rival` | 0.0672 | 0.0220 | 1.04% | 13.04% | 39.04% | 47.65% |
| `av_07_team_hue` | 0.0715 | 0.0220 | 1.37% | 14.19% | 39.12% | 47.85% |
| `av_08_sil_bare` | 0.0108 | 0.0000 | 0.19% | 1.76% | 4.74% | 91.76% |
| `av_09_sil_loaded` | 0.0108 | 0.0000 | 0.19% | 1.76% | 4.71% | 91.80% |
| `av_12/13_team_*_lowdust` | 0.067–0.071 | 0.0220 | 1.0–1.3% | 13–14% | 39% | 47.6% |

**Read against the contract in `ART-DIRECTION.md` §2.9** (blown ≤ 3%, legible 3–20% for a lamp
frame, black ≥ 70%):

- The two lamp-only frames (`av_02`, `av_08`, `av_09`) **pass all three** — 0.2–0.4% blown,
  4.4–4.7% legible, 92–93% black. That is the direction's own default look, and it sits at the
  bottom of the legible band.
- The wear inspection frames are deliberately outside it: they use a raking area light so that
  the *material* is what is being judged rather than the exposure. They are not target frames.
- The team frames sit at 39% legible and 47.7% black. They have a 420 W world source 1.5 m
  from the subject, which is a bulkhead fitting at close range — brighter than the direction's
  own default and useful only for comparing two paint schemes.

**Nothing here is a target frame for the world's look except `av_02`, `av_08` and `av_09`.**
The others are instrument readings and are lit for measurement, not for the game.
