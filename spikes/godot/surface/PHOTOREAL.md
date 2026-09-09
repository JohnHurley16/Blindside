# The photoreal pass on the surface spike

`DESIGN-PRINCIPLES.md` §6, 2026-09-09:

> *"Yeah, I agree the materials and underfoot stuff sucks right now. Start working on that.
> It needs to look photoreal."*

`NOTES.md` §6 and §7.1 already said where the weakness was, in the previous pass's own words:

> *"at 0.4 m the concrete still reads smoother than it should, the chippings read as
> scattered plates rather than embedded aggregate, and there is no displaced geometry at
> all — the ground is a 1 m grid with a shader on it."*

This pass is about that. Nothing here changes `layout.gd`; the layout hash is unchanged at
**1889570882374975** for seed 20260908, which is the property that had to hold.

Measured on the **NVIDIA GeForce RTX 3080 Laptop GPU**, Vulkan 1.4.312, Forward+,
1920 × 1080, vsync off, MSAA 2×. Every number below is from that adapter; the `adapter :`
line in each `perf/photoreal/*.txt` is the proof. **§4 carries a large and unavoidable
caveat about contention — read it before quoting any absolute frame time.**

---

## 1. What changed, technique by technique, with what it cost

### 1.1 The ground is the whole task

| # | Technique | Where | What it bought | What it cost |
|---|---|---|---|---|
| 1 | **One height field, `ghf()`** — slab joints, joint arris, per-bay lippage, spalled patches, repaired patches, hairline cracks, half-exposed aggregate, a gravel bed, ruts along the routes, and 5 mm grain — at three LODs | `materials.gd` GROUND_SHADER | albedo, roughness, normal, occlusion and standing water are now all read off **the same** function, so they agree. A surface whose roughness does not follow its albedo reads as a decal on a plane. | it is the shader; see 1.2 for the part that was expensive |
| 2 | **Parallax occlusion mapping** on the hardstanding. 20 / 12 / 7 / 4 / 0 steps at 3 / 7 / 12 / 18 m, one linear refinement, stride clamped to 5 so a grazing view cannot walk half a metre per step, and off entirely on anything that is not flat | GROUND_SHADER | the joints, spalling and ruts have apparent depth instead of being drawn on. This is the single change the designer's note is most about. | **measured at ~1 ms of a 38 ms frame** — `--pom=0` moved the full-scene mean by less than run-to-run noise. The POM march uses the cheap LOD of the field (form only, no worley), which is why it is nearly free. |
| 3 | **Three normal scales** — form (0.4 m), detail (2-5 cm), micro (5 mm) — from that same field, each fading in at its own distance | GROUND_SHADER | a yard that has shape at 30 m, tooling at 8 m and grain at 1 m | **this was the expensive one and it had to be rewritten. See 1.2.** |
| 4 | **Ambient occlusion from the field's own cavity** (`AO`, `AO_LIGHT_AFFECT 0.28`) | GROUND_SHADER | joints, cracks and the lee of every stone darken. A crevice that does not darken is the cheapest tell there is. | free (one clamp) |
| 5 | **Finer tessellation: the ground mesh is 0.5 m inside the compound**, 1 m over the rest of the site box, geometric skirt beyond. 33 687 → **65 095 verts**, 66 608 → **129 072 tris**, still **one draw call** | `ground.gd` | a 1 m grid cannot hold a rut or a graded dish. This is what lets the mesh carry real form under the shader's micro relief. | +2 300 verts/ms of generation: ground build went **361 → ~900 ms** (GDScript, see §5) |
| 6 | **A dressing-side relief field, `Ground.relief()`, that is never negative** | `ground.gd`, used by `scatter.gd` | **the hovering-contact fix.** Layout says the ground is at *h*; the rendered ground is at *h + relief*, 0-80 mm above it. Every prop placed at the layout height is therefore slightly **buried** and never left hovering over a surface that moved down under it. One addition, no per-prop work, 85 000 instances. | ~0.4 ms per 1000 queries in GDScript; part of the scatter increase in §5 |
| 7 | **Puddles that follow real low spots.** The pad carries a real 24 mm dish at 8 m wavelength *in the mesh*, and the same field goes into vertex colour A. The shader subtracts its own micro relief from it and a `drain` term that rain lowers. | `ground.gd` + GROUND_SHADER | the puddle edge is where a **water level** crosses a **ground surface** — so it wraps round the aggregate, fills the joints first, and grows when it rains, with no puddle shape authored anywhere. The water surface normal is flattened to +Y, which is the detail that makes it read as water rather than as a dark stain. | free; it is one subtract and one smoothstep |
| 8 | **Worn tracks along the routes things actually take.** The six walkway polylines, the haul road and the four stations are baked to a 1 m wear grid and read by bilinear lookup, then written to vertex colour B. | `ground.gd` | wear is where the plan says machines walk, not where a noise field happens to be dark. Ruts subtract from the relief, so the routes are the lowest ground in the yard, which is where the water goes. | 28 700-cell bake, ~90 ms of generation |
| 9 | **Vertex colour is now read.** R hardstanding, G mud, B wear, A pondability. The first pass wrote all four and the shader ignored them. | both | the shader knows what the simulation knows | free |
| 10 | **Half-buried aggregate.** Loose stock and pad chippings are placed with their **centre below** the surface (−0.13 × size for gravel, −0.06 for chippings); fixings and litter bedded; weeds rooted 10% deep. | `scatter.gd` | a stone whose centre is above the surface is a stone lying on a picture of ground. A stone whose centre is below it is embedded, and its own body draws the contact shadow that 55 000 shadowless DETAIL instances cannot cast for themselves. | free |
| 11 | **Oil, tracked mud, kerb-edge mud, repaired bays** driven by the wear field and the pad rectangle | GROUND_SHADER | the pad is not one material | free |

### 1.2 The two performance disasters, because they will happen again

**`Sky.PROCESS_MODE_QUALITY` cost 100 ms a frame.** The new sky is a `ShaderMaterial`
rather than a `ProceduralSkyMaterial`, and QUALITY re-bakes the whole importance-sampled
radiance cubemap whenever the sky is marked dirty — which, with a ShaderMaterial sky, is
every frame. The overcast pass ran at **9.0 fps**. `PROCESS_MODE_REALTIME` took the same
frame from **110.6 ms to 37.9 ms** with no visible difference in a still, because the sky
does not animate. Godot's own documentation says QUALITY "should not be used if you plan on
changing the sky at runtime"; it turns out a shader sky counts as changing at runtime.

**Central differences at three separate scales cost 9.5 ms of a 27 ms frame, on the ground
alone.** Three scales × four taps = twelve full evaluations of a field containing three
worley cells each. Measured with `--nrm=0`: ground-only went **27.3 → 17.8 ms**. The
rewrite keeps the same three scales but rides the **sampling scale** on distance instead of
running three passes that each ride it:

```
under 7 m   : form + cracks + aggregate + grain, epsilon 11 mm
7 to 20 m   : form + cracks + aggregate,         epsilon 11 to 60 mm
beyond 20 m : form only,                         epsilon 75 mm
```

One evaluation and two forward differences, plus a separate 5 mm grain gradient inside
6.5 m. **Ground-only: 27.3 → 9.0 ms — faster than the baseline ground shader's 17.6 ms**,
which was doing 3D value-noise fbm. It is also more correct: the epsilon now tracks the
pixel footprint instead of being fixed.

The solid shader got the same treatment: the three scales collapse to one function sampled
at one epsilon, and the corrosion pit normal is taken **analytically** from the vector to
the nearest worley feature point (which the albedo needed anyway) instead of costing three
more worley evaluations in a finite difference.

### 1.3 A correctness fix that reads as a look fix: Nyquist

A 23 mm worley cell is four pixels at 10 m and two pixels at 20 m, and a two-pixel cell does
not average — it **aliases**. It came back as pale blotches crawling over the spoil tips
that read exactly like snow. Every frequency band in the ground shader now has its own
distance fade sized to when it reaches about two pixels:

| band | cell size | faded out over |
|---|---|---|
| exposed aggregate | 23 mm | 6 → 14 m |
| grain (fbm at 27/m) | 37 mm | 8 → 18 m |
| loose stones | 130 mm | 14 → 26 m |
| cracks, spalling, oil, tracked mud | 0.6 – 5 m | 22 → 38 m |

This is cheaper *and* it is the fix for the crawling. Both.

### 1.4 Materials

| # | Technique | What it bought | Cost |
|---|---|---|---|
| 12 | **Gradient noise with rotated octaves**, replacing value noise on an axis-aligned lattice, and a non-transcendental hash | value noise at ~1 m cell size put a visible square check into every mask built on it, and on the hardstanding that check was the most artificial thing in the underfoot frame | slightly cheaper (no `sin`) |
| 13 | **fbm range normalisation.** Four octaves of gradient noise land in about 0.32-0.68, so every `smoothstep` threshold written against 0..1 was operating on a third of its intended range | masks that should have covered 15% of the concrete covered none, and albedo variation that should have been 3:1 was 1.3:1. **This is the single most consequential line in the file.** | free |
| 14 | **Three normal scales on every solid**, form / detail / micro, from one triplanar height field with a hard axis pick (the kit is axis-aligned prisms, so a hard pick never blends and costs nothing) | flat-shaded blocks now have surface | see 1.2 |
| 15 | **Corrosion pitting as craters**, density modulated by a 0.7 m patch mask | a uniform pit density over a whole member reads as a printed dot screen, which is what the first attempt looked like | one worley, shared with the albedo |
| 16 | **Albedo in measured linear ranges, and every one of them varies.** Weathered concrete 0.24 base swinging 0.11-0.33 before wear; oil-soaked concrete 0.022; rusted steel 0.15 base over a 0.55-2.1 instance-colour range, i.e. 0.08-0.32; `bone` 0.887 → **0.620** (0.887 is fresh laboratory white, not a shell that has been in this yard a season) | the checklist's item 1 and item 6 | free |
| 17 | **Metallic is strictly 0 or 1.** `galv` was 0.72 and `alu` was 0.90 — those are not materials. Both are now metal, and their albedo is the metal's F0 (0.56 for galvanised steel, 0.91 for aluminium) rather than a diffuse colour | the bay frame and the handrails read as metal for the first time | free |
| 18 | **Roughness driven by the same field as albedo**, with a wide band on every entry, plus cavity roughening | a surface that is lighter because it is chalkier is also rougher | free |
| 19 | **Ambient occlusion per material** from the height field's cavity | contact | free |
| 20 | **Wet is a material state**: pooling on horizontals, run-off stretched vertically on verticals, darker albedo, lower roughness, higher specular. Gated so it costs nothing when dry or when the face is horizontal | rain changes the surfaces, not only the particles | ~1 fbm on wet vertical faces only |

### 1.5 Light, sky and exposure

| # | Technique | What it bought | Cost |
|---|---|---|---|
| 21 | **A generated sky shader**: gradient, a cloud deck raymarched onto a flat plane (so cloud stretches toward the horizon the way real cloud does), a horizon haze band and a sun glow. Same gradient noise as the ground; no bitmap. | a flat two-stop gradient is the strongest "this is a render" tell a daylight frame has, and the surface is the only place in the game with sky | free at `PROCESS_MODE_REALTIME`; **catastrophic at QUALITY, see 1.2** |
| 22 | **Exposure re-set for the new albedos.** Overcast went from `tonemap_exposure 0.50` to **0.80** with ambient 0.58 → **1.30** and sun 1.55 → **1.50**. The old exposure was compensating for a concrete albedo three times too dark. | the underfoot frame's tonal spread (p25→p75) went from **0.04 to 0.13** — the old frame was a flat grey card | free |
| 23 | **AgX kept**, plus `adjustment_contrast 1.15` / `adjustment_saturation 1.10` | AgX is the correct filmic shoulder for daylight and it is what the project already used, but it desaturates hard; the adjustment block puts the contrast back more cheaply and controllably than swapping to ACES and losing the highlight rolloff | free |
| 24 | **SSAO retuned from 0.7 m to 0.34 m radius**, intensity 1.05 → 1.5, `ssao_detail 1.0`, `ssao_sharpness 0.99` | 0.7 m is ten times the size of a chipping: it darkened whole regions and did nothing at the contact. 0.34 m is the scale of the objects that need it. | `--ssao=0` is available for measurement; it is not a new cost, the old build ran SSAO too |
| 25 | **A near-neutral sun with a cool sky.** See §3 — this is the art rule this pass bends hardest. | the underfoot frame went from **B/R = 1.30 to 1.01**: it was a monochrome blue image | free |

### 1.6 The two things `NOTES.md` §7 asked for

| # | Technique | Where |
|---|---|---|
| 26 | **Service bay rooflights.** Every fourth roof sheet on both slopes is a translucent panel rather than steel, with one shadowless daylight omni under each — what a real workshop does. `NOTES` §7.8: *"it wants a rooflight strip or one open bay."* | `props.gd` |
| 27 | **The two sceptic frames re-framed** lower and closer, onto the bench itself and down the charge row rather than onto the posts and the cable ramps. `09_sceptic_bench` and `10_sceptic_charge` in `shots/`. **Partly done only**: the bay frame is much better lit by 26 and now reads, but the three docked machines are at z + 1.1 m behind their pedestals and are still not what the charge frame is about. That is a placement problem in `props.gd`, not a camera one — the machines should stand *in front of* the pedestals they are plugged into. | `main.gd` |

---

## 2. Measurement switches built in

Every technique above can be priced separately, which is how the two disasters in 1.2 were
found. All of these are new:

```
--sky=realtime|incremental|quality    sky radiance process mode
--pom=0|1                             parallax occlusion mapping off / on
--nrm=0|1                             detail and micro ground normals off / on
--ssao=0|1                            screen-space ambient occlusion off / on
--mode=pshots --tag=NAME              capture the photoreal shot list to shots/photoreal/NAME/
--dbg=6                               ground shows vec3(water, pondability, water depth)
```

`--dbg=14` (ground only) and `--dbg=4` (hide the underfoot bucket) already existed and are
what isolate the ground shader from everything else.

---

## 3. Which art rules this bends

`DESIGN-PRINCIPLES.md` §6 already records that photorealism contradicts two rules in
`ART-DIRECTION.md` §9 and that neither is resolved. Here is exactly where it is spent.

### 3.1 "No hue axis on anything" — bent, deliberately, and this is the big one

§9 and §1.4 fix *one warm rock family, value carries meaning, hue does not*. The ground now
carries hue as a **material fact**: weathered concrete is warm-neutral (0.240 / 0.231 /
0.215), oil is a neutral near-black, tracked mud is a warm brown (0.086 / 0.062 / 0.040),
spoil is browner than the pad, the bed under standing water tints green-brown, and rust runs
from brown-black to orange-brown across one member. Without that, wet concrete and dry
concrete and mud and oil are four values of one grey and the frame reads as a greyscale
render, which is what it did.

**What is preserved is the intent**: it is one warm family, there is no biome colour, there
is no second hue axis, and nothing signals anything by hue. Amber and the transformer's
`ember` were both **desaturated** in this pass (0.72/0.46/0.16 → 0.48/0.30/0.11 and
0.62/0.19/0.04 → 0.30/0.15/0.06) specifically so this does not become garish.

### 3.2 "No image texture, UV map or bitmap" — not bent

Nothing is unwrapped, nothing is photographic, every value in both shaders comes from
generated gradient noise and worley cells evaluated in world space or by a hard triplanar
axis pick. The only `Image` in the project is the three decal masks the previous pass
already generated in code. `docs/spikes/PROCEDURAL-AND-GODOT.md` question 5's default —
generated noise is allowed — is what this depends on, and it holds.

### 3.3 "No ambient light, ever, in any costume" — bent, as it already was

§9 is written for the cave. The surface has sky, which `DESIGN-PRINCIPLES` §3 requires. The
previous pass already ran a sky ambient; this pass leans harder on it — overcast ambient
energy 0.58 → 1.30 — and adds a **warm downward hemisphere** to the sky so undersides pick
up a ground bounce. That is a real photographic effect and it is what stops every shadow in
the yard being the same blue.

### 3.4 `ART-DIRECTION` §2.1: "the shaft's 12000 K is the only cold light, and the only daylight" — bent, and I want this one ruled on

The previous pass made the surface's sun *be* the shaft's light, at
`SHAFT_LIGHT.lerp(white, 0.35)`. Combined with a 100%-sky ambient at the same colour, the
result is that **every surface in the frame comes back the same hue** — the underfoot frame
measured B/R = 1.30, i.e. a monochrome blue image, and no amount of material work fixes it
because there is nothing in the frame that is a different colour.

The sun is now near-neutral, `(1.00, 0.985, 0.962)`, and the **sky keeps the cool bias**.
The underfoot frame now measures B/R = 1.01.

The claim §2.1 is defending — that the shaft is the only cold light in the game — survives
in the ambient, which is where an overcast sky's colour actually lives. The direct beam does
not. Real overcast diffuse is 6500-7500 K, not 12000 K; 12000 K is a clear-sky north window.
**This is a design call and I have made it provisionally. If the answer is that the surface
must stay at 12000 K, the honest consequence is that the surface cannot look photoreal, and
that should be a decision rather than a side effect.**

### 3.5 One physical cheat, flagged

A puddle at 45° reflects about 2% of the sky (F0 for water is 0.02), which is why wet ground
photographs *dark*. The shader is honest about that. On top of it there is a **broad sheen
term**, `skyavg * (0.105 * water + 0.038 * sheen)`, which is larger than a rough water
film's true integral. Without it a wet yard at standing height reads as merely dark rather
than as wet. It is the one number in the ground shader that is a look rather than a
measurement, and it is the first thing to delete if screen-space reflections arrive.

---

## 4. The numbers, and a caveat that has to come first

### 4.1 The caveat

**Another agent session was running Godot on the same GPU for the whole of this
measurement window.** It is not speculation: two `Godot_v4.7.2` processes, and
`spikes/godot/cave/*.log` being written every few minutes throughout. `NOTES` §4.4 already
warns that this machine's run-to-run variance is real; under a second Godot it is
catastrophic. The **baseline build, unmodified, measured anywhere between 4.89 ms and
65.03 ms mean on the same 12-second pass** — a 13:1 spread on identical code.

So the absolute frame times below are not comparable to the 2026-09-08 table in `NOTES`
§4.1, and neither is any single run. What *is* usable is a **ratio taken from
back-to-back pairs**, because both halves of a pair see the same background load. Six
alternating pairs of the same 12 s overcast pass:

| pair | baseline | this build |
|---|---|---|
| 1 | 6.20 ms | 13.70 ms |
| 2 | 9.84 ms | 14.32 ms |
| 3 | 9.83 ms | (run failed) |
| 4 | 9.63 ms | 80.19 ms |
| 5 | 65.03 ms | (run failed) |
| 6 | 9.59 ms | 40.73 ms |
| **median of the usable pairs** | **9.7 ms** | **14.0 ms** |

**The ratio is about 1.4× — 1.45× on medians, 1.31× on the cleanest 40-second pair, and
2.2× if you take each build's single best run.** I would quote **1.4×** and say the
uncertainty is ±0.3.

### 4.2 The 40-second benchmark, all three conditions

Same 14-waypoint camera loop, 1920 × 1080, MSAA 2×. `before` is the recorded 2026-09-08
run in `perf/photoreal/before_bench_*.txt`, taken on a quiet machine. `after` is this build,
taken under the contention described above. **They are not directly comparable and the
"projected" column is what the ratio says the after number would be on a quiet machine.**

| overcast | before (quiet, 2026-09-08) | after (contended) | projected at 1.4× |
|---|---|---|---|
| mean frame | 5.01 ms — 199.7 fps | 15.86 ms — 63.0 fps | 7.0 ms — 143 fps |
| median | 4.63 ms — 215.8 fps | 16.38 ms — 61.1 fps | 6.5 ms — 154 fps |
| p99 | 8.69 ms — 115.1 fps | 19.23 ms — 52.0 fps | 12.2 ms — 82 fps |
| **worst frame** | **16.00 ms — 62.5 fps** | 20.12 ms — 49.7 fps | **22.4 ms — 44.6 fps** |
| draw calls max | 877 | 926 | |
| primitives max | 2 153 481 | 2 443 347 | |
| video memory | 255.9 MB | **251.3 MB** | |
| generation | 1 121 ms | 3 469 ms | |
| instances | 85 144 | 84 864 | |

| rain | before (quiet) | after (contended) | projected at 1.4× |
|---|---|---|---|
| mean frame | 7.97 ms — 125.5 fps | 19.16 ms — 52.2 fps | 11.2 ms — 90 fps |
| median | 7.58 ms — 132.0 fps | 20.00 ms — 50.0 fps | 10.6 ms — 94 fps |
| p99 | 12.50 ms — 80.0 fps | 24.47 ms — 40.9 fps | 17.5 ms — 57 fps |
| **worst frame** | **12.96 ms — 77.1 fps** | 26.84 ms — 37.3 fps | **18.1 ms — 55 fps** |
| draw calls max | 917 | 891 | |
| primitives max | 2 183 847 | 2 464 835 | |
| video memory | 287.9 MB | **283.5 MB** | |
| generation | 1 139 ms | 3 396 ms | |

| dusk | before (quiet) | after (contended) | projected at 1.4× |
|---|---|---|---|
| mean frame | 7.24 ms — 138.2 fps | 29.55 ms — 33.8 fps | 10.1 ms — 99 fps |
| median | 6.25 ms — 160.0 fps | 24.24 ms — 41.3 fps | 8.8 ms — 114 fps |
| p99 | 12.96 ms — 77.1 fps | 57.04 ms — 17.5 fps | 18.1 ms — 55 fps |
| **worst frame** | **15.14 ms — 66.1 fps** | 61.79 ms — 16.2 fps | **21.2 ms — 47 fps** |
| draw calls max | 1 140 | 1 112 | |
| primitives max | 2 258 251 | 2 545 837 | |
| video memory | 287.9 MB | **283.5 MB** | |
| generation | 1 166 ms | 3 529 ms | |

The dusk `after` run is the worst-contended of the nine and its p99 should be ignored; the
baseline itself measured 40.66 ms mean in the same window against its own recorded 7.24 ms.

### 4.3 Do we hold 60?

**The mean does, comfortably. The worst single frame probably does not, and I will not
claim otherwise.** Projecting the ratio onto the recorded quiet baselines puts the
worst frame of a 40-second pass at **45-57 fps in all three conditions**, where the
baseline was 62-79. The tail is the wide establishing view at each end of the loop, and it
is exactly the frame the ground shader is most exposed in.

`NOTES` §4.1's own headline — *"across every run and all three lighting conditions the
worst single frame of a 40-second pass is between 62 and 79 fps; it never drops below
60"* — **no longer holds, on the evidence I have.** It needs one clean measurement on a
quiet machine to settle, and I could not get one.

### 4.4 What each technique costs, measured back-to-back

Every one of these is a pair of adjacent runs of the same 12 s pass, so contention affects
both sides. The switches are in the build (§2).

| knob | measured | note |
|---|---|---|
| `Sky.PROCESS_MODE_QUALITY` vs `REALTIME` | **110.6 ms → 37.9 ms** | the biggest single find in this pass. §1.2. |
| ground normals: 12 field taps vs 3 (`--nrm`) | **27.3 → 17.8 ms**, ground only | §1.2 |
| ground shader after the rewrite | **27.3 → 9.0 ms**, ground only, vs 17.6 ms for the baseline ground shader | the new ground shader is *cheaper* than the one it replaced |
| parallax occlusion mapping (`--pom=0`) | **~0.2 ms** at 14/9/5 steps to 9 m; **5.4 ms** at 16/10/6/3 steps to 18 m | the 9-18 m band was 96% of the cost and 4% of the value |
| the solid shader's three normal scales (`--solid=0`) | **0.8 ms** | |
| SSAO (`--ssao=0`) | **4.4 ms** | unchanged from the baseline, which also runs it — this is not a regression, it is the knob to reach for if the tail needs buying back |
| INCREMENTAL vs REALTIME sky radiance | no measurable difference (18.5 vs 19.2 ms) | but INCREMENTAL's converged radiance is *brighter*, and re-tuning exposure for it is a separate job |

**If the 60 floor has to be met today, `--ssao=0` buys 4.4 ms and costs the contact
shading that half of §1's underfoot work depends on.** That is the trade and I would not
take it; I would spend a quiet machine on one clean measurement first.

## 5. Generation cost

Generation is GDScript looping over 85 000 instances and calling the height query ~150 000
times. `NOTES` §4.2 already says why that is not a number worth arguing about — in Rust
behind GDExtension it disappears — but it did roughly triple and the reason should be on
the record.

| | before | after | why |
|---|---|---|---|
| LAYOUT (integer, the part that has to port) | 0.8 – 2.6 ms | **unchanged, 0.9 – 2.0 ms** | nothing in this pass touches it |
| ground mesh | 361 ms (33 687 v / 66 608 t) | **900 – 1 700 ms (65 095 v / 129 072 t)** | twice the vertices in the compound, plus a `relief()` and a `wear_at()` per vertex |
| dressing — inherited | 63 ms | 74 ms | — |
| dressing — brought | 25 ms | 27 ms | rooflights |
| underfoot scatter and decals | 619 ms | **1 300 – 2 000 ms** | every scattered prop now asks `Ground.height()`, which is `ground_mm` + `on_pad` + `_pad_dist` + four value-noise taps + a bilinear wear lookup, 85 000 times |
| flush | 52 ms | 63 ms | — |
| **TOTAL** | **1 120 ms** | **2 400 – 3 900 ms** | |

The wear field is baked once to a 183 × 157 grid rather than queried per call, which is the
only reason this is 3 s and not 12. The obvious next saving is to cache `on_pad` and
`_pad_dist` the same way.

---

## 6. What is still not photoreal, and what it would take

Honestly, and in order of how much each one costs the frame:

1. **No screen-space reflections.** The ground's reflection is an *analytic sky* — it is
   the right gradient with the sun in the right place, and a puddle mirrors it correctly at
   grazing angles. What it cannot do is show the headframe, a machine, or a container in the
   water. A wet yard that does not reflect the thing standing in it is the largest single
   remaining tell. `Environment.ssr_enabled` plus dropping the ground's `specular_disabled`
   would do it; the ground would then need its roughness floor watched, because
   `specular_disabled` is there to stop grazing Fresnel washing the whole site to sky colour
   (`NOTES` §8).
2. **No edge wear on the kit.** Everything on the site is a flat-shaded prism with a
   zero-radius corner, so no edge in the frame catches light. Real steel has a bright, less
   rough line along every convex edge where the paint and the scale have been knocked off,
   and that single cue is most of what separates "manufactured metal" from "a shaded block".
   It needs either chamfered kit meshes (cheap — the `casebox` already exists) or a
   curvature estimate.
3. **No contact shadows.** Godot 4 has none, and the 55 000-instance DETAIL bucket casts no
   shadow by design (`NOTES` §3). Grounding is carried entirely by burying props in the
   relief field and by SSAO at 0.34 m. It works at 1.5 m and it does not work at 0.4 m.
4. **The ground is parallax, not displacement.** POM has no silhouette: run the camera down
   to 0.2 m and the joints flatten out at the edges of the frame, and a stone that should
   break the horizon does not. Real displacement in the last 6 m — a camera-following
   tessellated patch — is the fix and it is not cheap.
5. **Weeds are five untextured triangles with no translucency.** Real vegetation is backlit.
6. **No lens.** No bloom, no vignette, no chromatic aberration, no depth of field, no sensor
   noise, no motion blur. A photograph has all of those and their absence reads. Glow is off
   because `NOTES` §3 turned it off for cost; on this budget it could probably come back.
7. **The decal masks are 128 × 128.** At 1 m they are visibly soft blobs.
8. **Nothing moves.** `NOTES` §7.4 still stands and is still the cheapest big win available.
9. **One unresolved artifact.** A pale band sits on the flank of the large spoil tip in
   `03_yard_working`, about 25 m out. It is not the aggregate worley (fixed in 1.3), not the
   wear field painting a walkway up the side of the tip (fixed, and it did do that), and not
   the loose-stock albedo (tightened). It survives all three. It wants ten minutes with
   `--dbg=1` and `--dbg=4` and I ran out of them.
10. **Still one seed.** `NOTES` §7.6 stands: everything here was tuned against
    seed 20260908.

---

## 7. Every guess in this pass, in one list

These are on top of `NOTES` §9, which still stands. Strike them individually.

1. **The sun is near-neutral and only the sky is cold.** §3.4. The biggest one, and it
   contradicts `ART-DIRECTION` §2.1 as literally written.
2. **Weathered concrete is 0.24 linear** before wear, swinging 0.11-0.33. Real weathered
   concrete is 0.25-0.35; this sits at the bottom of the range because the yard is meant to
   be a hellscape.
3. **The hardstanding has a 24 mm dish at 8 m wavelength.** Invented, and it is the number
   that makes puddles possible at all. A real yard is graded to falls toward gullies; this
   is a noise field.
4. **`drain` is 20.8 mm dry and 12.2 mm wet.** i.e. rain raises the standing water by 8 mm.
   Tuned by eye against "the joints should fill first".
5. **The relief field is 0-80 mm and never negative.** The sign is the design (props bury
   rather than hover); the amplitude is a guess.
6. **`g_wet` in dry overcast dropped from 0.30 to 0.26.** Still never fully dry, per
   `NOTES` guess 18.
7. **`bone` is 0.620 linear rather than 0.887.** A machine that has been in this yard a
   season. Nothing says how new the players' kit is.
8. **Rooflights are every fourth roof sheet on both slopes.** Invented; `NOTES` §7.8 asked
   for "a rooflight strip or one open bay" and did not say which.
9. **Amber and the transformer orange were desaturated** by about a third to keep §3.1 from
   becoming garish. That is a taste call, not a measurement.
10. **The broad wet sheen term** (§3.5) is larger than physics. Flagged.
11. **Aggregate is exposed on about a third of the pad**, where a `worn` mask, a `spall`
    mask or the wear field says the float finish has gone. The proportion is by eye.
12. **The exposure numbers**: overcast 0.80, rain 1.95, dusk 1.45, with `adjustment_contrast`
    1.15 and `adjustment_saturation` 1.10. Set against measured image statistics (a target
    of p50 ≈ 0.33 and under 2% dead black) rather than against a reference photograph.

---

## 8. The before / after pairs

All 1920 × 1080, captured in code after `await RenderingServer.frame_post_draw`, from
**identical camera poses**. `before` was captured from the unmodified 2026-09-08 build with
only the capture mode added; `after` is this build.

```
GODOT=".../Godot_v4.7.2-stable_win64.exe"
$GODOT --path spikes/godot/surface --resolution 1920x1080 -- --mode=pshots --tag=after
```

`shots/photoreal/before/` and `shots/photoreal/after/`:

| file | pose | what to look at |
|---|---|---|
| `p01_underfoot_macro` | 0.38 m, the old `07_underfoot` pose | the macro. Before: a smooth blue-grey plane with black flakes on it. |
| `p02_underfoot_45` | **1.40 m looking down at 45°** — the frame the designer's standard names | the whole task. Joints, aggregate, broad staining, damp patches, embedded stones. |
| `p03_yard_working` | the yard at working distance | materials at 5-25 m, the sky, the spoil, the rooflights |
| `p04_hardstanding` | hardstanding with puddles and the transformer | the pad across its full depth |
| `p05_rain_underfoot` | the 45° pose again, in rain | **the same ground, wet.** Darker albedo, lower roughness, standing water, damp margins. |
| `p06_rain_collar` | rain at the collar | run-off on vertical faces, wet iron, particles |
| `p07_rusted_iron` | a headframe leg at 1.5 m | corrosion pitting, scale flaking, the galvanised handrail reading as metal |
| `p08_shaft_collar` / `p09_shaft_mouth` | the collar | the falloff into the shaft, unchanged and still the best image the surface has |
| `p10_site_wide` | the establishing shot | this is the worst frame in the benchmark |
| `p11_road_kerb` | the haul road and its kerbs | ruts and the wear field |
| `p12_dusk_yard` | the yard at dusk | the state that was not supposed to get better and did not get worse |

Measured image statistics for the `after` set (luminance percentiles, % clipped above 0.98,
% dead below 0.02). The point of the table is that **nothing clips and the tonal spread
opened up**: the before underfoot frame ran p25 → p75 across 0.04 of the range and was, in
the literal sense, a flat grey card.

| frame | p25 | p50 | p75 | clipped | dead |
|---|---|---|---|---|---|
| `p02_underfoot_45` **before** | 0.229 | 0.251 | 0.268 | 0.00% | 0.00% |
| `p02_underfoot_45` **after** | 0.163 | 0.216 | 0.280 | 0.00% | 1.06% |
| `p03_yard_working` before | 0.164 | 0.261 | 0.329 | 0.00% | 0.00% |
| `p03_yard_working` after | 0.199 | 0.318 | 0.478 | 0.00% | 1.00% |
| `p04_hardstanding` after | 0.218 | 0.350 | 0.429 | 0.00% | 1.42% |
| `p05_rain_underfoot` after | 0.188 | 0.231 | 0.273 | 0.00% | 1.93% |
| `p10_site_wide` after | 0.221 | 0.334 | 0.513 | 0.00% | 0.00% |
| `p12_dusk_yard` after | 0.021 | 0.040 | 0.127 | 0.01% | 23.2% |

And the colour cast, which is the measurement behind §3.4:

| frame | mean R / G / B | B:R |
|---|---|---|
| `p02_underfoot_45` **before** | 0.218 / 0.245 / 0.284 | **1.30** |
| `p02_underfoot_45` **after** | 0.222 / 0.221 / 0.224 | **1.01** |

The sixteen frames in `shots/` are regenerated from this build too, including the two
re-framed sceptic frames (§1.6).

---

## 9. Honest verdict on the underfoot frame

**No. It is much better and it would not pass.**

What it now has that it did not: real slab joints with depth, hairline cracks, spalled and
repaired bays, half-exposed aggregate, broad pour-scale mottling, oil that is dark *and*
smooth, tracked mud that is dragged in from the pad edge, weeds rooted rather than resting,
loose stock embedded rather than lying on top, standing water with a level and an edge, a
damp margin round it, occlusion in every crevice, and a tonal range instead of a grey card.

What it still does not have, in the order a photographer would notice: **the surface has no
silhouette** — POM stops at the edges of things, so nothing underfoot breaks the plane;
**nothing casts a contact shadow**, so a chipping is dark on its own but not on the ground
beside it; **every edge in the frame is a zero-radius corner**, so nothing catches a
highlight the way real steel and real concrete arrises do; and there is **no lens** —
no bloom, no vignette, no grain, no depth of field.

At 1.4 m and 45° it now reads as *a good render of an industrial yard*. It does not read as
a photograph, and the three things in §6 are what stand between.

---

## 10. What I would do next, in order

1. **Screen-space reflections and a tight bloom.** The single largest remaining tell is
   that a wet yard does not reflect anything standing in it. Everything else in the wet
   pipeline is already there and waiting for it.
2. **Edge wear on the kit.** A brighter, less rough line along every convex edge. The
   `casebox` chamfered mesh already exists and is used for the players' register only;
   putting a small chamfer on `box`, `ibeam`, `angle` and `channel` and letting the shader
   find it would change every frame at every distance for almost no cost.
3. **Real displacement and contact in the last six metres.** A camera-following tessellated
   patch under the POM, and shadow casting restored to the DETAIL bucket inside the first
   shadow split. Both cost frame time this build does not currently have, which is why they
   come after a clean measurement on a quiet machine.
