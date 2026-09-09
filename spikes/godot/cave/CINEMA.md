# The cinematic layer — the camera rig and the post stack

2026-09-09. `spikes/godot/cave/`, Godot 4.7.2, Forward+, Vulkan, RTX 3080 Laptop.
Spec: `docs/TRAILER.md` §8 (the camera) and §9 (the lens and the grade).
Nothing outside `spikes/godot/cave/` was modified. Nothing was committed.

> "make sure the camera doesnt fly through shit... make it look cinimatic, people should
> really want to play to figure out what is going on... Maybe postprocessing layer in
> godot is also needed to get the game play looking amazing"

---

## 0. The short version

| | |
|---|---|
| **Does the camera fly through anything?** | No. It has a 0.35 m body swept against the world, and it **rejects** a shot rather than repairing it. `--cinema=validate`. |
| **Do the trailer's cave shots execute?** | Yes: **16, 17, 18, 20 and 27**, all five, through the shot format rather than hand-flown. Two entries in the list are rejected and both rejections are correct — one is the deliberate failure, one is a real authoring attempt. §7. |
| **Biggest thing found in the camera** | TRAILER §8's own two rules contradict each other: a 0.35 m sphere at machine height 0.40 m cannot clear a mine floor. §4.2. And **legal is not the same as photographable** — the rig can make a shot correct and cannot make it good. §7.3. |
| **Biggest thing found in the post** | The colour grade was taking **14.3% off the mean of the whole frame** through a half-texel LUT error — an exposure cut wearing a grade's costume, which is precisely what ART-DIRECTION §2.9 exists to catch. §6.9. |
| **Effects that survived** | **9 of the 10** in §9's table, all measured on their own. |
| **Effects cut** | One: lens dirt/streak, cut on the spec's own words at zero cost. Bloom is **kept but idle** — it changes 0.06% of the frame because nothing in this cave is above threshold, and its subjects do not exist yet. §6.2. |
| **Cost of the whole stack** | ~5.7 ms of a 12.2 ms frame **on a GPU throttled to 780 MHz of 2100** with other applications on it. Do not read that as an absolute. §8. |
| **Per-object motion blur** | Answered with a measurement, not an opinion. §6.4. |

---

## 1. What Godot 4.7 actually gives you

Established by probing `ClassDB` in 4.7.2 rather than assumed. The probe is
`--headless --script`; the results:

| what | where it lives in 4.7.2 |
|---|---|
| tonemap, exposure | `Environment.tonemap_*`. **4.7 added `tonemap_agx_white` (default 16.29) and `tonemap_agx_contrast` (1.25)**; AgX no longer reads `tonemap_white`, which this spike still sets to 6.0. That line is now inert — see §10. |
| bloom / glare | `Environment.glow_*`, seven mip levels, HDR threshold |
| colour grade | `Environment.adjustment_*` — brightness, contrast, saturation, and a `Texture2D`/`Texture3D` LUT |
| depth of field | `CameraAttributesPractical` — near/far distance and transition, and an amount. Not on `Environment`. |
| SSR, SSAO, SSIL, SDFGI, fog, volumetric fog | `Environment` |
| **motion blur** | **nowhere.** Godot 4.7 has no motion blur of any kind, camera or per-object. |
| **vignette, chromatic aberration, film grain, lens distortion** | **nowhere.** |

So those five are a `CompositorEffect`. `Compositor`, `CompositorEffect`,
`RenderSceneBuffersRD`, `RenderSceneData` and `UniformSetCacheRD` all exist and
`Camera3D` has both `attributes` and `compositor`, so the seam is there.

**Two things that are not in the documentation and cost time:**

1. **`RenderSceneDataRD` exposes no methods.** The camera transform and the view
   projection are on its base class `RenderSceneData` (`get_cam_transform()`,
   `get_view_projection(view)`). Looking at the RD subclass finds nothing.
2. **Godot's scene colour buffer is not created with `CAN_COPY_TO`**, so the result
   of a compositor pass cannot be blitted back into it with `texture_copy` — it
   fails with an error per frame and the frame renders untouched. The effect
   therefore runs as two dispatches: the work into a scratch target the effect
   allocates through `RenderSceneBuffersRD.create_texture`, then a 1:1 compute
   store back into the colour buffer.

---

## 2. Where the stack sits, and why that is not a convenience

The whole lens/sensor pass runs at `EFFECT_CALLBACK_TYPE_POST_TRANSPARENT`, which
means **on the HDR linear colour buffer, before tonemapping.** That is where these
things physically happen:

```
   the lens         distortion, chromatic aberration, vignetting   on radiance
   the shutter      motion blur                                    integration
   the sensor       shot noise + read noise                        on electrons
   -------------------------------------------------------------- then AgX
```

Two things fall out for free that a post-tonemap filter has to fake:

* **Grain lands in the shadows and nowhere else**, because AgX's slope is steep in
  the toe and flat in the shoulder. No shadow mask is written anywhere in this
  code; §6.5's table is the tone curve doing it.
* **Vignetting rolls a deliberately-blown near wall down into the shoulder**
  instead of multiplying an already-clipped value.

The one ordering compromise: Godot's depth of field runs *after* the compositor,
so grain in a defocused region gets slightly blurred. TRAILER §9 asks for "almost
nothing in the wide cave shots", so the affected area is small; it is recorded
rather than fixed.

---

## 3. The shot format

A shot is a plain `Dictionary`, JSON-serialisable, and the list lives in
`shots_cinema.json`. That is the point: the trailer's shot list is **data the rig
executes**, not a camera path somebody flew.

```json
{
  "name":    "t16_lamp_comes_on",
  "trailer": "16",
  "len_s":   5.0,
  "lens_mm": 21.0,
  "tstop":   2.8,
  "ease":    "inout",
  "handheld_deg": 0.0,
  "height":  "eye",
  "seed":    16,
  "move":  {"from": ANCHOR, "to": ANCHOR, "via": ANCHOR },
  "look":  {"from": ANCHOR, "to": ANCHOR },
  "focus": {"from": ANCHOR or metres, "to": ANCHOR or metres }
}
```

**An ANCHOR** is either a world point `[x, y, z]` or, far more usefully, a place in
the workings:

```json
{"st": 116, "r": 0.10, "u": 0.42, "f": 1.60}
```

`st` is a station on the main drive. `r` is metres right of the centreline, `u` is
metres above the floor **there**, and `f` is **arc length along the drive**, which
is what makes the format portable: it names a place in a mine rather than a
coordinate in a scene.

**What the format cannot express, deliberately:**

* **A zoom.** There is one `lens_mm` per shot and no way to write two. TRAILER §8
  says pick a focal length and commit; the format enforces it by being unable to
  represent the alternative.
* **A linear move.** `"ease": "linear"` is a validation *failure*, not an option.
  `inout` is smootherstep — zero velocity *and* zero acceleration at both ends,
  which is the "camera is a physical object with mass" rule as arithmetic.
* **A long travel.** Over 2.5 m is a failure with the message *"a shot that must go
  further is two shots"*.

**Focus** is pulled, not snapped: it interpolates on the same eased `u` as the
move, so it accelerates and settles with the camera. It can be given as a distance
or as an anchor, in which case the distance is recomputed every frame and the pull
tracks a place in the world.

**Handheld** is off unless a shot asks for it: three octaves of value noise at
0.37 / 0.83 / 1.90 Hz, peak amplitude in degrees, plus a few millimetres of body
translation. Nothing above 2 Hz — a real operator does not produce it and anything
faster reads as a shake effect rather than as a person holding a camera.

### Running it

```
--cinema=validate   validate every shot and report          shots/cinema/validation.txt
--cinema=scout      --shot=NAME: sweep the drive for places that shot could stand
--cinema=seq        render the executing shots as image sequences
--cinema=pairs      before/after for every effect, cumulative, one pose
--cinema=stack      whole stack on/off, three frames
--cinema=tune       bloom threshold sweep, motion blur and DoF showcases
--cinema=fail       the deliberate failure and the frames it would have shipped
--cinema=cost       leave-one-out timing, interleaved
--cinema=locations  --shot=NAME --stations=a,b,c: photograph a shot from each
--cinema=mvcost     what asking Godot for motion vectors costs
--cinema=veldbg     one frame that proves the reprojection's Y is the right way up
--fx=a+b+c          any subset of the stack, or `all` / `none`
```

---

## 4. The camera rig

### 4.1 The body and the collision

A `SphereShape3D` of 0.35 m, swept with `cast_motion` against a `StaticBody3D`
built from the same geometry that is drawn:

* every chunk's shell mesh as a `ConcavePolygonShape3D` — **113 656 triangles**;
* the obstacle kit as one shared `ConcavePolygonShape3D` per part, instanced —
  **951 instances, 61 368 triangles**;
* **175 024 triangles total, built in ~330 ms** at scene load.

**The first version used a `BoxShape3D` per instance on the kit mesh's AABB and
rejected every single shot in the trailer.** A timber set is a *frame*: its
bounding box is the 2.4 × 2.4 m opening you are supposed to walk through, so the
box filled the drive. The same is true of an arch, a duct ring and a mesh panel.
Exact triangles cost about 25 ms more to build and are the only correct answer.

Loose scatter — stones, ballast, grit, spall, litter — is deliberately **not**
collision. A 40 mm chip is not an obstacle, and 19 015 collision shapes to pretend
it is would cost more than the entire post stack.

### 4.2 TRAILER §8's two rules contradict each other, and this is the resolution

> "The camera has a body. A sphere of 0.35 m radius…"
> "…machine height 0.4 m…"
> "Nothing clips the near plane. Keep 0.4 m of clearance in front at all times."

A 0.35 m sphere whose centre is at 0.40 m clears a *perfectly flat* floor by 50 mm.
This floor is not flat: it is noise-displaced, and it carries rail, sleepers and
ballast. So the body touches the ground in every low shot, and the first version of
the validator rejected all of them. The same applies to the frustum: every
low-angle dolly shot ever made has floor inside 0.4 m at the bottom of frame.

**The resolution is in the section's own words** — the camera "stands somewhere a
body could stand". A rig resting on the ground is standing, not flying through. So:

* a body contact **in the bottom 0.18 m of the sphere** is the rig standing on the
  floor and is permitted; every other contact is a breach;
* a frustum hit is only a breach if the surface is **not up-facing ground below the
  camera** (`normal.y > 0.60`). What §8 forbids is "a wall dissolving into the
  lens", and a floor running up into the bottom of frame is a floor.

The height rule is what governs the ground, and it is measured with a raycast
against the same collision.

**This is an interpretation, and it is the one I would most want overruled.**

### 4.3 What the validator checks

Every failure is reported with the number that caused it. Nothing is repaired.

| # | rule | threshold |
|---|---|---|
| 1 | swept body | 0.35 m sphere, 0.05 m query margin, non-ground contacts only |
| 2 | near clearance | 0.40 m of empty frustum, 9 rays, ground exempt |
| 3 | height | floor 0.04–0.40 · machine 0.28–0.56 · eye 1.38–1.82 · crane ≥ 2.00 with ≥ 0.5 m of headroom to hang from |
| 4 | travel | 0.15–2.50 m |
| 5 | ease | linear is a failure |
| 6 | speed | peak ≤ 1.2 m/s |
| 7 | lens | 18–24 / 35–50 / 85+; anything between is a warning |

### 4.4 Lensing, derived rather than dialled

Focal length → field of view assumes a **16:9 crop of a full-frame sensor,
36.0 × 20.25 mm**, which is the frame every number in TRAILER §8 is quoted
against. Depth of field is computed from the hyperfocal distance with the standard
full-frame **circle of confusion of 0.030 mm**, and the near and far limits of
acceptable sharpness are handed straight to `CameraAttributesPractical`. So a
21 mm at T2.8 focused at 3 m is sharp from 1.78 m to 5.46 m because that is what
the arithmetic says, not because it looked right.

### 4.5 The scout

`--cinema=scout --shot=NAME` sweeps the main drive with a shot as a template and
reports the stations where the rig would accept it, with the sightline from each.
It is a **location scout, not a repair**: it says where a shot *could* stand, the
shot list is then written by hand against the answer, and the validator still
governs what ships.

Its first result is worth recording on its own:

> **Only 16 of ~170 candidate stations on the main drive will accept a
> machine-height 1.6 m dolly.** At eye height, 48 will. The cave is a much harder
> place to put a low camera than a standing one, because that is the height at
> which rail, sleepers, spall and breakdown live.

And, on sightline: the longest view from any station that also accepts an
eye-height drift is **23.8 m**, at station 60, against a median sightline of
3.6 m measured in `ART-DIRECTION.md` §3.6. That is what "wide, small in frame"
needs — and station 60 still makes a bad frame, because a sightline says the
camera *can* see a long way and says nothing about what is in the first two
metres. §7.3.

`--cinema=locations --shot=NAME --stations=a,b,c` photographs the same shot from
each candidate so the choice can be made by looking. `shots/cinema/loc/` holds
both sweeps.

---

## 5. The pictures

Everything is 1920×1080, in `shots/cinema/`.

| where | what |
|---|---|
| `pairs/NN_<effect>_{off,on}.png` | the nine before/after pairs, **cumulative in TRAILER §9's order**, all from one identical camera: `t16_lamp_comes_on` at t = 0.55 |
| `stack/<shot>_{off,on}.png` | the whole stack on and off at three different frames. "off" is AgX and nothing else — the spike as it stood |
| `seq/<shot>/NNN.png` | the executing trailer shots as image sequences |
| `tune/bloom_t*.png` | the bloom threshold sweep |
| `tune/mblur_*`, `tune/dof_t20_*` | the two effects a slow static pose cannot show |
| `fail/*.png` | the rejected shot, and the frames it would have shipped |
| `diag/veldbg_dolly_in.png` | the reprojection sanity frame |
| `loc/<shot>_stNNN.png` | the same shot photographed from each candidate station, for choosing one |
| `contract_{off,on}/` | the frames `lumcheck.py` measures, AgX-only and full stack |

---

## 6. The post stack, effect by effect

TRAILER §9's table, in the order given. Every cost is a **leave-one-out delta from
the full stack**, interleaved A/B/A/B/A/B, 56 frames a block, median of medians,
at `t16_lamp_comes_on` t = 0.55, 1920×1080. **Read §8 before reading any of them.**

### 6.1 Tonemap and exposure — kept, unchanged, 0.61 ms

AgX, exposure 1.0, ambient disabled, background strength 0 — as the photoreal
pass left it, and not touched. ART-DIRECTION §2.3 forbids a curve that rescues
the far end and §2.9 measures the histogram on this one.

`CameraAttributesPractical` is now on the camera for depth of field, and it
arrives with an exposure multiplier and an auto-exposure. Both are pinned:
`auto_exposure_enabled = false`, `exposure_multiplier = 1.0`. **The only exposure
control in this project is the lamp.**

The 0.61 ms is AgX measured against Godot's LINEAR tonemapper, which is not
something anybody would ship; it is in the table for completeness, not as a
choice.

### 6.2 Bloom / glare — kept, idle, 0.31 ms

Retuned for a tight glare: weight on the two tightest mip levels
(`glow_levels/1 = 1.0`, `/2 = 0.55`, `/3 = 0.12`, the rest zero), normalized,
additive, `glow_bloom = 0`, intensity 0.55. Threshold chosen by measurement at a
pose with a beacon pilot in frame (`tune/bloom_t*.png`):

| threshold | pixels changed | max delta |
|---|---|---|
| 0.8 | 0.099% | 154/255 |
| **1.6** | **0.059%** | **106/255** |
| 2.6 | 0.024% | 21/255 |
| 4.0 | 0.009% | 16/255 |

**It is doing almost nothing, and that is a fact about the scene rather than
about the setting.** The subjects §9 names for bloom — the lamp seen directly,
the winch head at 2400 K, retroreflectors — are *none of them in this spike*.
The only emissive in the whole cave is a beacon pilot.

This is the SSR situation with one important difference. SSR had nothing to
reflect and never will under one lamp with no ambient; bloom has nothing to bloom
**yet**. So it is kept at 1.6, costing 0.31 ms, and **it must be re-measured the
day the Assayer's winch head exists.** Cutting it now would be cutting it against
a scene that does not contain its subject.

### 6.3 Depth of field — kept, 2.88 ms, the most expensive thing in the stack

`CameraAttributesPractical`, driven from the hyperfocal arithmetic in §4.4 rather
than dialled by eye. Bokeh shape changed from Godot's default hexagon to a
**circle**: a hexagon reads as a six-blade stills lens, a cinema prime stops down
round.

It earns it. On `t20_sensor_shadow` — 35 mm at T2.0 focused at 1.9 m, the
shallowest shot in the list — it changes **12.7% of pixels**, and in
`seq/t16_lamp_comes_on/` the near timber post goes soft as the focus pulls from
2.6 m to 5.3 m. That pull is the single most photographed-looking thing in any of
these frames.

`dof_blur_amount` is the one number here that is not physical: Godot's amount is
a blur radius, not an f-number. It is derived from the entrance pupil (f/N) and
normalised so a 50 mm at T2.8 sits at 0.06, clamped at 0.14 — TRAILER §9's "never
so shallow it looks like a miniature", as a clamp.

### 6.4 Motion blur — kept, camera only. 0.06 ms static, 0.24 ms moving

Godot 4.7 has none, so this is a `CompositorEffect`: reconstruct world position
from depth and the inverse view-projection, reproject through the previous
frame's view-projection, and integrate 9 taps along the resulting screen velocity
at a 180° shutter, which is half a frame interval.

**Two things that would have silently produced a wrong picture.**

1. **The previous frame is not the previously rendered frame.** Offline capture
   renders each shot frame eight times over to let the volumetric fog and the
   shadow atlas settle, so "last frame" is the same pose and the blur is exactly
   zero. The rig therefore hands the effect the previous **shot** frame's camera
   transform explicitly, computed at the true 1/60 s spacing regardless of how
   the sequence is decimated for disk. The sequences here are 24 frames and the
   blur in them is the blur the finished 60 fps shot will have.
2. **The reprojection's Y sense.** A sign error there smears every frame along
   the wrong diagonal, and it is invisible on a pan or a tilt because centred
   taps make the blur symmetric. `diag/veldbg_dolly_in.png` is a one-frame proof:
   a dolly in must produce velocity pointing outward from the axis, so the top
   half of the frame must read `vel.y < 0` (drawn red) and the bottom half blue.
   It does.

**Is per-object motion blur affordable? Measured, not asserted.** Godot only
produces a velocity buffer when something asks for one. Setting
`needs_motion_vectors = true` on the effect and changing nothing else:

```
needs_motion_vectors = false    11.60 ms
needs_motion_vectors = true     12.91 ms
                                ---------
the velocity pass alone          1.31 ms   before a single blur tap is taken
```

**That is four times the cost of the camera blur it would replace, for a scene in
which nothing but the camera moves.** The cave is static geometry and one lamp,
so camera reprojection is exact for every pixel of it. The two exceptions are the
drip and mote particles, which get the camera's velocity instead of their own — a
few dozen pixels a frame, already smeared by their own alpha.

**Verdict: per-object motion blur is not affordable and is not needed in the
cave. It becomes a real question the moment a machine walks through frame**, and
the number to beat then is 1.31 ms of prerequisite before any blur at all.

### 6.5 Film grain — kept, 1.42 ms

Not a grain texture and not a shadow mask. A sensor:

```
sigma = sqrt(signal / full_well) + read_noise
```

Shot noise is Poisson, so the signal-to-noise ratio is worst in the near-black —
which is nine-tenths of this game — and best in the lamp pool. Applied to the
linear signal before AgX, which is where a sensor's noise actually happens.

Measured on the pair, by tonal band, as the standard deviation of (on − off) in
output code values:

| band | share of frame | sigma | relative to signal |
|---|---|---|---|
| near-black 0–4 | 49.4% | 0.85/255 | ~40% |
| toe 4–20 | 26.0% | 2.04/255 | ~17% |
| mid 20–80 | 20.9% | 2.48/255 | ~5% |
| high 80+ | 3.7% | 1.11/255 | <1% |

**TRAILER §9's "grain in the shadows, not in the highlights" falls out of the
tone curve, not out of a mask** — there is no luminance mask anywhere in the
shader. And 0.85/255 in the near-black is about one LSB, which is the textbook
dither amplitude for breaking 8-bit banding, the other job §9 gave grain.

1.42 ms is more than it should be: four hash evaluations plus a `log` and a `cos`
per pixel for a Box–Muller Gaussian. A precomputed noise volume would make it
nearly free and is the first optimisation I would do.

### 6.6 Vignette — kept, 0.06 ms

**There is no amount knob.** The falloff is the cos⁴ law evaluated from the
shot's own focal length against the 36 × 20.25 mm frame, so a 21 mm darkens its
corners and a 100 mm does not, which is what a lens does. The one free parameter
is `vig_k = 0.55` — how much of the theoretical cos⁴ survives a real lens design.
A pinhole would be 1.0.

It costs about **7% of the frame's mean luminance** and takes the corner-to-centre
ratio from 0.107 to 0.077 at 21 mm. §9 asked for "optical amount only", which
this is, but see §9 below: in this cave it is expensive in a currency other than
milliseconds.

### 6.7 Chromatic aberration — kept, 0.06 ms

Lateral dispersion: red images larger than blue, zero on the axis, growing with
radius, 1.9 px at the corner of a 21 mm and scaled down with focal length. It is
carried *into* the motion-blur tap loop rather than applied after it, because a
lens disperses before a sensor integrates — so with blur running it costs three
texture fetches per tap instead of one, which is where the moving-frame number
comes from.

### 6.8 Lens distortion — kept, 0.06 ms

Barrel, `r' = r(1 + k·r²)`, with an overscan of `1/(1+k)` so the corner maps to
the corner and no black wedge appears. `k = −0.009` at 21 mm falling to zero by
32 mm — 0.9% at the corner, sub-percent as §9 asks, and honestly close to
invisible. It is the effect I would cut first if the budget got tight, and it is
kept only because it is free.

### 6.9 Colour grade — kept, 0.03 ms, after finding the bug

A 32³ LUT generated at runtime. There is not one imported asset in this project
and a LUT was not going to be the first. It does two things:

* the deepest shadows lose chroma, because both a sensor and a print do — and
  because it is what stops §6.5's chroma noise from turning the black into
  confetti;
* the top two stops warm by about 2%, toward the iron and the lamp.

**There is no cool shadow lift.** ART-DIRECTION §9 forbids cyan anywhere in the
world, and cooling the shadows is how every other game arrives at cyan.

**The bug, and it is the most important thing in this document.** Godot samples a
3-D colour-correction LUT with `texture()`, so a colour `v` lands at texel
position `v·N − 0.5`. Building the table on `i/(N−1)` — the obvious way — returns
`f(v − 0.5/N)` for every pixel. At v = 0.1 with N = 24 that is a **17% drop**.

Measured over the whole frame, the grade was taking **14.3% off the mean**.

It did not look like a bug. It looked like a moody grade. It was an exposure cut
wearing a grade's costume, which is exactly the failure ART-DIRECTION §2.9 was
written to catch — and it was caught by *measuring* the before/after pairs, not
by looking at them. Built on `(i + 0.5)/N` at N = 32, the grade now moves the
frame mean by **+1.1%**.

### 6.10 Lens dirt / streak — CUT, on the spec's own words, at zero cost

> "Only on the surface, only in rain, only on the strongest sources. Easy to
> overdo; cut first if in doubt."

There is no rain 140 m down a drowned mine and nothing is spraying the lens. It
was not built, and it costs nothing. If it appears anywhere it belongs in
`spikes/godot/surface`.

---

## 7. Which trailer shots execute

`shots/cinema/validation.txt` is the machine-readable version.

| # | shot | lens | executes | note |
|---|---|---|---|---|
| **16** | the lamp comes on | 21 mm T2.8 | **yes** | 1.30 m push in, 5 s, eye height 1.60 m, focus pulled 2.6 → 5.3 m. Handheld off. |
| **17** | following the machine | 35 mm T2.8 | **yes** | 1.60 m follow, 4 s, machine height 0.42 m, handheld 0.22°. **There is no machine**, so this executes as the plate: the move is right, the subject is missing. |
| **18** | the first belief cut | 35 mm T2.8 | **yes** | "Hard cut, same passage, SAME CAMERA" — so it is shot 17's move run again, identical anchors, ease and seed, so the two cut frame on frame. Not re-rendered here because it would be byte-identical; the cloud side belongs to the lidar spike. |
| **20** | the sensor shadow | 35 mm T2.0 | **yes** | 0.29 m drift, 4 s, sensor height 0.40 m, handheld 0.30°. A HOLD that is not a still: TRAILER §6 forbids that. |
| **27** | the wrong direction | 21 mm T4.0 | **yes** | 0.80 m lateral drift, 3 s, eye height 1.55 m, sharp from 2.6 m to infinity. |
| 18′ | the continuation reading | 35 mm | **REJECTED** | see below |
| — | `xfail_through_the_wall` | 21 mm | **REJECTED**, deliberately | see §7.2 |

Shots 22–25 were not attempted: 22 needs a machine and a deposit face, 23–25 need
the Assayer, which TRAILER §7 already records as unbuilt.

### 7.1 The one real trailer shot that is rejected

`x18_continuation_at_116`. TRAILER §3 gives shot 18 as a hard cut on the same
camera; the other reading is that the camera keeps moving through the cut. Run as
a continuation from the end of shot 17's move **at station 116** — the station the
first draft of shot 17 used — it is rejected:

```
FAIL: body intersects geometry at t=0.13 (the 0.35 m sphere overlaps)
FAIL: frustum clearance falls to 0.00 m at t=0.44 (needs 0.40)
```

0.96 m further down that drive the body finds geometry and the frustum finds the
near wall. It is kept in the list pinned to 116 as the record of an authoring
attempt that failed, rather than quietly moved until it passed. At station 68,
where shot 17 now stands, the same continuation is legal — which is the point:
**whether a camera move is possible is a property of the place, not of the move.**

### 7.2 The deliberate failure

`xfail_through_the_wall` is authored to fail: a 2.3 m push that leaves the
centreline for the wall, which is exactly the move a hand-flown camera makes when
nobody is checking.

```
xfail_through_the_wall  REJECTED
  FAIL: no line of sight to the drive centreline at t=0.53: the camera is not in the passage
  FAIL: body intersects geometry at t=0.41 (the 0.35 m sphere overlaps)
  FAIL: frustum clearance falls to 0.01 m at t=0.50 (needs 0.40)
last legal t = 0.391, first rejected t = 0.406
```

`shots/cinema/fail/` holds four frames: the legal start, the last legal position,
the first rejected one, and the end — 0.85 m inside the rock, looking at the back
face of a rib from behind it. **That last frame is the tell.** It is what would
have shipped.

**And it found a hole in the rig, which is why it is in the list.** At the end
pose the body reported `overlaps = false`: the shell is a triangle *soup*, not a
solid, so a 0.35 m sphere sitting entirely inside the rock touches no triangle.
The swept test caught it on the way through, but a shot authored to *start* buried
would have passed every check. That is now rule 8 in §4.3: the camera must have an
unobstructed line to the centreline of the station it is authored against — the
arithmetic definition of being in the same room.

### 7.3 Two things the rig cannot do, found by using it

**Legal is not the same as photographable.** Shot 17 went through three stations.
116 passes every rule in TRAILER §8 and ends with a blown near face filling frame.
196 has the longest machine-height sightline in the cave, 8.9 m, and renders
**0.00% of the frame legible against a 3% floor** — a long look down an unlit
drive is a long look at nothing. 68 was picked by photographing the candidates.
Neither the rule set nor the sightline could have found it.

So `--cinema=locations` exists, and the honest description of the workflow is:
the rig says where a camera *may* stand, the sightline says whether it can see,
and a person still has to look at the frame.

**Only 10% of the drive will take a low camera.** The scout accepts a
machine-height 1.6 m dolly at 16 of ~170 candidate stations, and an eye-height one
at 48. That is a fact about the cave generator, not about the rig: 0.4 m is the
height at which rail, sleepers, spall and breakdown live. If sensor-height shots
matter — and they do, because that is the machine's own eyeline and the belief
cut has to be cut from it — the generator needs to leave more clear ground at
0.4 m, or the shots have to be authored where it already does.

---

## 8. The measurements, and what they are worth

**The machine was not quiet and I am not going to pretend it was.** `tasklist`
found no other Godot process, but `nvidia-smi` reported the GPU at **80–85 °C,
clocked at 780 MHz against a 2100 MHz maximum — a 2.7× throttle — with 38–42%
utilisation from Brave and the Epic launcher** throughout. `PHOTOREAL.md` §4.0
already records that two runs of the same build on this laptop differ by more
than anything being measured.

So: **every number in §6 is a delta between two interleaved blocks taken seconds
apart, and none of it is an absolute frame rate.** The relative ordering is
trustworthy; the milliseconds are inflated by roughly the throttle factor.

```
stack off  6.32 ms   (repeat 6.69 ms -- 6% drift across the run)
stack on  12.18 ms
                     whole stack: 5.68 ms
sum of the individual leave-one-out deltas: 5.49 ms
```

The parts add up to the whole to within 3%, which is the main reason to believe
the table at all.

**I am not quoting a frame rate.** `summary.txt` records the clean baseline at
206 fps mean / 130 p05 after the photoreal pass; a stack costing ~5.7 ms on a
throttled GPU would be roughly 2 ms un-throttled, and the honest statement is
that **this needs re-measuring on a quiet machine before anyone budgets against
it.** Depth of field and grain are half of it, and grain is the one that is
cheaply fixable (§6.5).

### 8.1 The exposure contract

`lumcheck.py` now takes a directory. Three runs:

**The twelve canonical frames, unchanged by this work** — reproduces
`PHOTOREAL.md` §4.3 exactly, 9 of 12 pass, `01`/`05`/`08` fail. The cinematic
layer did not touch the base scene.

**The cinematic frames** — the four executing shots at t = 0.15, 0.50 and 0.85,
rendered twice: AgX only, and with the full stack.

| | AgX only | full stack |
|---|---|---|
| frames outside the contract | **3 of 12** | **5 of 12** |
| the failures | `t16@0.15`, `t17@0.85`, `t27@0.50` — all *too dark* | those three, plus `t20@0.50` and `t20@0.85` |

**The stack pushes two more frames below the 3% legible floor**, and it does it by
about 0.4 percentage points:

| frame | AgX only | full stack |
|---|---|---|
| `t20_sensor_shadow` @ 0.50 | 3.28% legible | **2.84%** |
| `t20_sensor_shadow` @ 0.85 | 3.84% | **2.92%** |
| `t16_lamp_comes_on` @ 0.50 | 5.64% | 5.09% |
| `t27_wrong_direction` @ 0.85 | 4.38% | 3.39% |

Every one of those deltas is the vignette; the grade now contributes +1.1% and
grain +0.5%, and neither moves a band.

**The finding, and it is the one to take to the designer:**

> **The vignette is not free in the currency the contract is denominated in.** It
> costs about 7% of the frame mean and 0.4 points of legible fraction, and this
> cave already sits on the floor — `01_wide_passage` has been at 2.96% against a
> 3.0% floor since the photoreal pass. So the lens can turn a passing frame into
> a failing one without a single lighting change.
>
> It is a real optical effect, it is derived from the focal length rather than
> dialled, and it is applied to radiance before the tone curve, which is where a
> lens applies it. **What needs a ruling is whether ART-DIRECTION §2.9's 3% floor
> is measured before or after the lens.** If after, either the lamp goes up
> (which §2.2 explicitly permits, since power and exposure are the same knob) or
> `vig_k` comes down. If before, nothing changes and the contract is a check on
> the lighting rather than on the picture.
>
> I did not brighten anything to make this go away, which is the whole point of
> §2.9.

### 8.2 Focal length is an exposure control here, and nobody has said so

The work lamp is a 54° cone (`spot_angle = 27`). A lens whose horizontal field
matches it is 18 / tan(27°) = **35.3 mm**. Anything wider is looking at rock the
lamp is not lighting. Measured at one pose, `tune/lens_*.png`:

| lens | legible >0.05 | true black <0.02 |
|---|---|---|
| 21 mm | 5.56% | 87.23% |
| 28 mm | 7.67% | 82.99% |
| **35 mm** | **9.74%** | **79.76%** |
| 50 mm | 5.84% | 82.70% |

**Changing the lens moves the legible fraction by 1.75× with no change to the
lighting at all.** At 21 mm about a quarter of the frame is structurally black
because it is outside the lamp cone. At 50 mm the field lands on unlit near wall
and it falls again.

That is not a defect — TRAILER §8 wants wide for the chamber, and in a game
whose contract demands ≥70% true black, a wide lens *buys* black. But it means
**the focal length and the lamp cone are one decision, not two**, and the 18–24 /
35–50 / 85+ bands in §8 were written for a world with more than one light in it.
In the cave the honest bands are: 21 mm when the dark is the subject, 35 mm when
the rock is.

---
## 9. Does the frame read as photographed?

My honest judgement, from reading the frames rather than from having written
them.

**Sometimes, and it is the shots rather than the stack that decide it.**

`seq/t20_sensor_shadow/` is the one that convinces. A low camera among the rails
with a tipped tub, sleepers, spall and a wet floor; the operator is breathing;
the near timber falls off into a soft edge and the far wall is soft the other
way; there is grain in the black and none in the pool. Nothing in that frame says
"engine viewport". `seq/t16_lamp_comes_on/` is second: the focus pull off the
rail underfoot and out down the drive is the most photographic single event in
this directory, because it is the one thing in the frame that only a lens does.

**What still says "rendered", in the order I would fix it:**

1. **There is exactly one light and it is on the camera.** This is
   `PHOTOREAL.md` §6.3 unchanged and it now dominates everything I could do in
   post. N·L ≈ N·V means the shading contrast is nearly flat, and a lens stack
   cannot manufacture form that the lighting never produced. Every frame here has
   a single hot ellipse with black around it — which is *true*, and it is also
   why the frames read as a torch demo rather than as photography. **A second
   source would do more for this than the whole post stack**, and ART-DIRECTION
   §2.8 already has one costed and waiting for a ruling.
2. **The kit meshes.** A timber set is six boxes; a launder is a slatted panel
   that renders as bright painted plaster; a tub is a box with two discs. At
   1–2 m from a 21 mm lens these are the largest objects in frame, and no lens
   effect survives being pointed at a box. `PHOTOREAL.md` §6.6 said this and it is
   now the single most visible thing.
3. **The near wall's macro form.** Same as `PHOTOREAL.md` §6.2. The rock has
   relief and no *shape* — no spalled slab, no overbreak lip, no bed that has
   parted and dropped. In a 21 mm frame at 1.5 m that is most of the picture.

**Is the grade a lens or a filter?** A lens. The test I would apply is whether an
effect can be turned off and the frame still reads as the same photograph, and
every one of these can: nothing here is carrying the image. The vignette is the
only one with a visible signature and it is derived from the focal length rather
than chosen. The grade moves the frame mean by 1.1% and I would defend cutting it
entirely — it survives on the chroma-rolloff argument (§6.9), not on the look.

**Is anything blown or crushed?** Blown: no. The worst frame in the set is 0.23%
of pixels above 0.50 against a 3% ceiling, and the deliberately-blown near wall
of ART-DIRECTION §2.2 does not appear at these poses. Crushed: yes, and on
purpose — 70–94% of every frame is true black. Two of the twelve contract frames
are *under* the legible floor with the stack on, and §8.1 is the argument about
whose fault that is.

**Does anything clip, or hover?** No clipping: `t16` at t = 0.55 with a timber
post at 0.6 m holds 0.40 m of frustum clearance, and the sequences were rendered
only after the validator passed them. No hovering: every height in the list is a
declared rule checked against a raycast to the floor, and there is no shot in
`shots_cinema.json` at an unjustifiable height because the format cannot express
one without naming it.

**Is the motion eased?** Measurably. `sequences.txt` prints the per-frame step in
millimetres:

```
t16   0.0  1.0  6.5  16.0  28.3  42.0 ... 105.9 (peak) ... 42.0  28.3  16.0  6.5  1.0
```

Symmetric, zero at both ends, no discontinuity. And the focus pull runs 2.61 →
5.30 m on the same curve, so it accelerates and settles with the camera rather
than sliding under it.

---

## 10. Everything I guessed

Everything below is mine rather than read out of a document.

1. **The ground exemption in §4.2** — that a body contact in the bottom 0.18 m of
   the sphere is the rig standing rather than the camera clipping, and that a
   frustum hit on up-facing ground below the camera is not a near-plane breach.
   This is an interpretation of TRAILER §8, it is load-bearing for every low
   shot in the trailer, and it is the one I most want overruled.
2. **The height bands.** floor 0.04–0.40, machine 0.28–0.56, eye 1.38–1.82,
   crane ≥ 2.00 with ≥ 0.5 m of headroom. §8 gives three numbers and no
   tolerances.
3. **Travel 0.15–2.50 m and peak speed 1.2 m/s.** §8 says "a metre or two" and
   "short and slow" and gives no figures.
4. **The sensor: 36.0 × 20.25 mm**, a 16:9 crop of full frame, and the standard
   **0.030 mm circle of confusion**. Every focal length and every depth-of-field
   figure in this document depends on both.
5. **`dof_blur_amount`** — the mapping from f/N to Godot's blur radius, and the
   0.14 clamp.
6. **The handheld model**: three octaves at 0.37 / 0.83 / 1.90 Hz, the 0.6/0.28/0.12
   weights, roll at 0.55 of yaw, and 6 mm of body translation per degree.
7. **That a focus pull shares the move's easing.** A real puller has their own
   timing and can start late or run faster than the dolly. The format cannot
   express that.
8. **`vig_k = 0.55`** — how much of the cos⁴ law survives a real lens design.
9. **The sensor numbers**: full well 9000 e⁻ at signal 1.0, read noise 0.00085 in
   signal units, grain cell 1.6 px, and the 0.7 weighting of chroma noise against
   luma.
10. **CA 1.9 px at the corner of a 21 mm**, and that it scales with focal length
    the way it does.
11. **Barrel `k = −0.009` at 21 mm**, falling to zero at 32 mm.
12. **The whole grade**: the 0.12 chroma-rolloff threshold, the 0.30 residual
    chroma at black, the 2% highlight warm and the 0.55 threshold it starts at.
13. **Bloom at threshold 1.6, intensity 0.55, levels 1.0 / 0.55 / 0.12.** The
    threshold is measured; the level weights and the intensity are taste.
14. **9 motion-blur taps and a 40 px clamp**, and the 0.35 px floor below which
    the blur is skipped.
15. **The obstacle list** — which 19 of the 47 kit parts a camera body collides
    with, and that loose scatter does not.
16. **The 0.05 m physics query margin**, chosen to cover the rock shader's 75 mm
    of downward parallax.
17. **That `f` should be arc length along the drive** rather than a straight-line
    offset. It is a better format; it is also a decision nobody asked for.
18. **Rule 8's formulation** — line of sight to the station centreline as the
    test for "in the passage". It is a proxy and it would misjudge a shot
    authored inside a chamber that the drive centreline cannot see.
19. **Every station index in `shots_cinema.json`.** They are seed-7 specific.
    Change the seed and the shot list needs re-scouting, which is a real
    limitation of a format that names stations.
20. **That the trailer's shot 18 is shot 17's camera run again** rather than a
    continuation. §3 says "same camera"; both readings are available and I picked
    one, and recorded the other as a rejection (§7.1).

### One thing I did not guess, and should be corrected in the code

`cave_root.gd` sets `env.tonemap_white = 6.0` with a comment describing it as the
AgX white point. **Godot 4.7 gave AgX its own parameters** — `tonemap_agx_white`
(default 16.29) and `tonemap_agx_contrast` (1.25) — and `tonemap_white` is read
by the other tonemappers, not by AgX. So that line has been inert for the whole
photoreal pass; the frames were graded against the 4.7 defaults. Nothing about
the pictures changes, but the comment claims something that is not true, and the
next person to tune exposure will turn that knob and watch nothing happen.

I did not change it: it is outside the cinematic layer and it changes the look of
every existing frame in `shots/`.

---

## 11. What I would do next, in order

1. **A second light source.** Not a post effect. ART-DIRECTION §2.8's residual
   circuit at its low end, or anything at all that is not bolted to the camera.
   Every frame in this directory is flat-shaded by a lamp at the eye, and that is
   now the limit on how photographed any of them can look. It needs a designer
   ruling, not an engineer.
2. **Kit meshes with a silhouette.** A sawn baulk with a split end, a launder
   with real boards, a tub with a rolled lip. The lens stack is now better than
   the things it is pointed at.
3. **Precompute the grain.** 1.42 ms for a Box–Muller Gaussian per pixel is a
   quarter of the whole stack for the cheapest effect in it. A tiled 3-D noise
   volume, sampled with a per-frame offset, makes it nearly free — and the
   photoreal pass already proved that trick pays (`PHOTOREAL.md` §2.1).

And one thing for the cave generator rather than the camera: **leave clear ground
at 0.4 m.** Only 16 of ~170 stations will take a machine-height dolly, and the
belief cut has to be cut from that eyeline.
