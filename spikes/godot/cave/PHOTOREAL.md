# Photoreal pass on the cave spike — 2026-09-09

**What this answers.** DESIGN-PRINCIPLES §6, recorded today after the designer walked the
previous build:

> *"yeah, j agree the materials and underfoot stuff sucks right now. start working on that.
> it needs to look photoreal"*

Nothing outside `spikes/godot/cave/` was modified. Nothing was committed.

**GPU.** `RenderingServer.get_video_adapter_name()` reports **NVIDIA GeForce RTX 3080 Laptop
GPU**, Vulkan, Forward+, and every number below is from that adapter, at a true 1920×1080
`SubViewport`, seed 7, 240 cells = 144 m of cave. Read §4.0 before reading any of the numbers:
this machine throttles from 2100 MHz to 780 MHz as it heats, and that is larger than most of
what is being measured.

---

## 0. The short version

| | |
|---|---|
| **Does it hold 60?** | Yes, with more headroom than the build it replaces. §4.1. |
| **Is the underfoot frame photoreal?** | No. It is now a wet mine floor rather than a pile of cut-outs on an invisible plane, and it fails for reasons that are one pass away rather than five. §6. |
| **Biggest single win** | Not a technique. Every loose stone in the spike had been lit by an **inverted normal** since the first build. §1.1. |
| **Second biggest** | Baking the noise into 3-D volumes. It made the rock shader ~2× cheaper *and* paid for everything else in §2. |
| **Cut after measuring** | SSAO. 4.35 ms of an 8.68 ms frame for a 0.25% pixel difference. §2.9, §5.3. |
| **Art rules bent** | Three, in §5, none silently. One of them contradicts a written number and needs a ruling. |

---

## 1. What was actually wrong, before any technique

Three of these are bugs, not art. They mattered more than anything I added.

### 1.1 Every loose stone was lit by an inverted normal

`_stone_mesh()` builds its meshes by distorting a `SphereMesh` and recomputing normals with
`_recalc_normals()`. That function's cross product has **the opposite sign to Godot's
front-face winding**, so every stone, ballast chip, spall flake and breakdown block in the
cave — the entire underfoot scale — carried normals pointing *into* itself.

Under one lamp and zero ambient that means no diffuse term and no specular term: they
rendered as **flat black cut-outs lying on the floor**. In
`shots/photoreal/before/p1_underfoot_macro.png` the black polygons are not shadows and not
holes in the mesh. They are the stones.

It survived three passes because the two obvious diagnostics both point away from the cause: a
forced-albedo debug render *still comes out black* when the normal is inverted, and so does a
shadows-off render. It took an emission tag, which bypasses lighting entirely, to find it.

Fixed in `dressing.gd::_stone_mesh()` by orienting each normal outward from the mesh origin — a
stone is star-shaped about its own centre, so `dot(n, v) > 0` is the correct test. It is the
same trick `_emit_band()` already used for the shell, and nobody carried it across.

### 1.2 The "puddles" were black holes cut in the floor

`WK_STANDWATER` placed an instanced disc with `albedo (0.020, 0.028, 0.032)`, `roughness 0.03`
and `metallic 0.15` — a value no material has. A flat mirror under a lamp that sits **at the
eye** returns nothing toward the camera, so each one read as a hole punched in the ground.
Deleted. The rock shader now grows puddles out of its own parallax height field, which is what
the discs were faking.

### 1.3 The lamp was effectively co-located with the sensor

`lamp.position` was `(0.10, −0.16, 0)` — about 6° off the view axis at 1.5 m. That means
**N·L ≈ N·V for every surface in the frame**, and a diffuse surface lit from exactly the
direction it is seen from has almost no shading contrast: a 30° bump changes the cosine by 13%.
No normal map of any quality produces form under that condition.

This is the most useful thing I learned in this pass and it drove three later decisions (§2.3,
§2.7, §6.3). The lamp is now `(0.26, −0.22, 0.10)`.

---

## 2. Technique by technique

### 2.1 Generated 3-D noise volumes replace the integer-hash noise — *this paid for everything else*

The old rock shader evaluated a 27-cell warped voronoi (81 integer hashes) plus six octaves of
value noise (8 hashes each) inside `rock_h()`, called `rock_h()` four times for central
differences, then evaluated the voronoi twice more in the albedo. That is **roughly 700
integer bit-mix hashes per fragment**, which is why the old `ablation.txt` found the empty
corridor *slower* than the dense one: the frame was fragment-bound on the wall material.

Four seamless 64³ `ImageTexture3D` volumes are now generated at load by `FastNoiseLite` and
sampled instead:

| volume | content | what it is for |
|---|---|---|
| `t_fbm` | 5-octave simplex fbm | form / detail / micro relief, staining, drip runs, ripples |
| `t_cel` | cellular `DISTANCE2_SUB` (F2−F1) | the joint set — the lines between blocks |
| `t_agg` | cellular `DISTANCE` (F1) | the bevel and the gap between aggregate stones |
| `t_cid` | cellular `CELL_VALUE` | **one value per stone**: its height and its albedo |

786 KB of VRAM, about 130 ms of load time, and a ~700-hash fragment becomes a ~30–60 fetch
one. Nothing is imported, nothing is unwrapped, nothing is photographic; all four are pure
functions of the cave seed. **`PROCEDURAL-AND-GODOT.md` Q5, default yes** — and this pass now
depends on that default holding (§5.1).

The fourth volume is the one that mattered visually. Taking an aggregate stone's height from
the *distance* field gives a cone, and a field of cones is the "cauliflower" that three
iterations of this floor could not shake off. Taking it from the *cell value* — constant over
the cell, stepping at the cell wall — gives a flat-topped angular block with a hard arris,
which is what blasted rock walked on for a century looks like. The distance field is then used
only to bevel that arris and open the gap.

### 2.2 Parallax occlusion mapping on the floor

The floor of the swept shell is four vertices per side. It is now 75 mm of packed aggregate,
fines, wheel ruts and puddles.

* Linear march plus **five binary-refine halvings**, which beats forty more linear steps.
* Step count falls with distance **and with view angle**: looking straight down, the parallax
  offset is zero, so `slant = |V.xz| / max(−V.y, 0.20)` scales the count. The 45° underfoot
  frame costs about half a grazing one.
* Off past `pom_far` = 4 m; the same height field then drives a plain bump out to 12 m, so
  there is no distance at which the floor becomes a plane.
* **Two texture fetches inside the loop.** Everything that does not change measurably over a
  75 mm offset — the broad relief, how far the fines have buried the stone, the ruts — is
  hoisted out of the march and passed in.

### 2.3 Three normal scales from one field, each with its own distance fade

`h_form` (metres: bedding, the joint set, shot-hole barrels), `h_det` (centimetres: spall
scars), `h_mic` (millimetres: grain). Amplitude fades, not frequency fades — a faded-out octave
costs nothing and cannot shimmer. Micro is gone by 2.6 m, detail by 13 m.

**With a clamp, and the clamp is not a nicety.** `g` is dh/dx in metres per metre, and a noise
volume sampled below its own Nyquist returns slopes of 3 or 4; `n − g·k` then tips the normal
past 90° and the surface faces away from the only light in the world. `bumped()` clamps the
tangential gradient to `atan(1.2) ≈ 50°`. Without it, props went black — the same failure mode
as §1.1 and just as invisible to a forced-albedo debug render.

Because §1.3 means the cosine term barely moves, the relief is carried as much by **cavity
occlusion and crevice dirt from the same height field** as by the normal. `AO` comes from
`h_det` with `AO_LIGHT_AFFECT = 1.0`, and the albedo is darkened by the same term. That pairing
is what makes a wall read at all under a headlamp.

### 2.4 A wetness field, not a wetness scalar

This is a drowned mine, so this is the strongest cue available, and it had been one number per
station. It is now composed from:

* **height above the water datum** — which became a shader uniform, so the tide-mark crust and
  the wetness gradient are continuous across the whole cave instead of existing only inside
  stations flagged flooded;
* **surface orientation** — water lies on top and runs off a vertical face;
* **concavity** — the parallax height field, so hollows are wetter;
* **drip runs** — noise stretched hard in world Y, gated on the face being steep enough for a
  run to exist at all;
* **a floor term**, because everything that runs down a wall ends up on the floor and nothing
  dries.

It drives albedo (×0.54 where soaked), roughness (0.88 → 0.24) and specular together, which is
what a wet surface does.

### 2.5 Puddles that follow the height field, with a flat normal

A low-frequency puddle-level field, gated on wetness, compared against the marched height. The
water sits in the real low spots and the aggregate breaks its surface. **The normal is
flattened inside the pool** — leaving the rock normal under a roughness-0.04 surface is what
makes a "wet" shader sparkle like glitter instead of reading as water. There is a pale mineral
rim at the wet/dry boundary, which is the detail that says the water level *moved*.

### 2.6 Standing water is a real surface

`water.gdshader`: two scrolling ripple scales; screen-space refraction of what is under it;
Beer-Lambert absorption weighted off red, so shallow water is the floor slightly darkened and
deep water is nearly black; and a **Fresnel-weighted 14-step screen-space reflection**, which
is the only way to get ART-DIRECTION §3.5's *"a mirror at grazing angle"* without a reflection
probe (which would be a light leak). No blue tint — §3.5 is explicit — so the colour is what is
under the water and what is reflected in it.

Godot 4.7 exposes neither `PROJECTION_MATRIX` nor `INV_PROJECTION_MATRIX` to the fragment
stage, so the four terms of it the reflection needs are carried across as a `flat` varying.

### 2.7 Physically plausible PBR on the kit

* **`METALLIC` is 0 or 1.** Cast iron was `0.55`, which is not a material. The one legitimate
  in-between is the rust transition, and it is a mask, not a constant.
* **A metal's albedo is its F0** (0.56 iron and steel, 0.91 aluminium), not its diffuse colour.
  The mesh's vertex colour now modulates how rubbed or how filthy the metal is, which is what
  it was really encoding.
* Making metallic binary immediately exposed a real consequence: **a rough bare metal under a
  co-located lamp has no diffuse term and returns almost nothing**, so every unrusted patch of
  cast iron went black. There is now a floor under the corrosion coverage of anything ferrous —
  which is also simply true, since nothing ferrous in a drowned mine is bare.
* Roughness varies over every surface from the same field as the albedo: casting skin, rubbed
  edges, rust bloom, water film. Two ages of rust, orange bloom over black scale.
* Two normal scales, model-space so they travel with the instance.
* Wetness from the water datum and face orientation, not a per-material constant.

### 2.8 Half-buried props, and fewer of them

Every stone, chip and flake is sunk between a quarter and three-quarters of its own radius into
the ground and follows the shell's own floor displacement. Counts are roughly halved
(33,470 → 19,015 instances) because the shader now parallax-maps the aggregate itself and the
props only have to break its silhouette; fifty loose stones per 0.6 m cell hid the floor
completely.

**This is the one place I spent the budget the brief said I had, in reverse.** The
justification is in the frames: half of what was there was hiding the thing that now does the
work. The budget went instead into shell triangles (§2.10), which is where geometry helps.

### 2.9 SSAO — measured, then cut

**Godot 4.7 has no per-light contact shadows.** `Light3D` exposes `shadow_enabled`,
`shadow_bias`, `shadow_normal_bias`, `shadow_reverse_cull_face`, `shadow_transmittance_bias`,
`shadow_opacity`, `shadow_blur` and `shadow_caster_mask`, and nothing else; the Godot 3 feature
was removed. So the checklist item cannot be satisfied as written, and contact darkening comes
from three other places: the lamp's real shadow map now that it is offset from the eye (§1.3),
geometric burial (§2.8), and the material AO computed from the parallax height field (§2.3).

SSAO was tried as the fourth. It cost **4.35 ms of an 8.68 ms GPU frame**, it was responsible
for every 60 ms+ spike in the walk (the runs with it off were the only stall-free ones), and
the underfoot frame with and without differs by **0.25% mean absolute pixel value** —
`shots/photoreal/cmp_ssao.png`, SSAO on top, off bottom. **Cut.** `--ssao` turns it back on.

The rule it was testing is written up in §5.3, because the ruling is worth having regardless.

### 2.10 Bedding as geometry, and a finer shell

A lamp at the eye returns almost no shading contrast from a normal map, so the beds have to be
real ledges in the silhouette or they do not read. Ring resolution 30 → 40 vertices, substeps
3 → 4 (0.15 m ring spacing), worked-ground displacement amplitude 0.085 → 0.155 m, and a banded
ledge term keyed to the same 0.25–0.60 m bed period the shader uses. Shell triangles
64,676 → 113,656 — which the ablation says is free, and this is the one thing the spike can
spend freely.

### 2.11 Tracks, and a repurposed vertex attribute

`UV2.x` carried "height above the local waterline". The waterline became a uniform, which freed
it, and it now carries the **signed lateral offset from the passage centreline in metres**.
That gives the floor shader a passage-local (axial, lateral) frame, which is what wheel ruts
need: two worn bands at the 0.60 m gauge with a wandering centre-line, a shallow trammed dish
between them, gated on `worked`. The ruts are also polished — roughness 0.44 against 0.88 —
because everything that ran over them rubbed them.

### 2.12 Exposure, re-derived rather than inherited

Tonemap was already AgX, white 6.0, ambient disabled, world background strength 0. That was
right and is unchanged. What changed is the lamp: ART-DIRECTION §2.2 is explicit that the
wattage is renderer-specific and must be re-derived against the *ratios* whenever the materials
move, and they moved a long way — the floor albedo went from the schematic's 0.42 to a
measured-plausible 0.19. Lamp energy 4.2 → 5.4; shadow bias 0.035 → 0.020 and normal bias
0.6 → 1.10, because a large bias detaches a small prop's shadow from its own base, which is the
classic hovering tell and the whole reason for moving the lamp off the eye.

`lumcheck.py` results in §4.3.

---

## 3. A note on the tooling, because it cost an hour

`check.sh` is headless and **never compiles a shader**. A GLSL type error therefore falls the
material back to white and the frame still renders — which is exactly what happened: one line
(`vec3 wof = <float expression>`) broke the rock shader and I spent an hour judging screenshots
of a fallback material, including one where I concluded a floor was "flat and white" and went
looking for the geometry that was wrong.

`shadercheck.sh` is a windowed compile gate that greps for `SHADER ERROR` and exits non-zero.
Run it before believing any frame. `cool.sh` is the thermal gate described in §4.0.

---

## 4. Measurements

### 4.0 Read this first: the machine is the largest variable

Measured mid-session with `nvidia-smi`: this RTX 3080 Laptop, at 87 °C, runs its SM clock at
**780 MHz against a 2100 MHz maximum — a 2.7× throttle** — and it does not come back below
about 75 °C in any useful time at idle, because the fan curve does not spin up for an idle GPU.
Two runs of the same build differ by more than anything in this directory does. Two concrete
examples from this session:

* the same build measured **gpu p50 3.63 ms and 25.02 ms** in two runs an hour apart;
* an ablation baseline row measured **4.72 ms** three times in a row and then **10.48 ms** two
  rows later.

I also found **two stray Godot processes from earlier timed-out runs holding the GPU at 99%**,
which silently corrupted every measurement taken before I noticed. `NOTES.md` §5.2 already
recorded an 85–114 fps band on this laptop; the real band is wider than that.

Everything below therefore either (a) alternates the two builds back to back, or (b) prints the
thermal state next to each row. `ablate.sh` now runs a baseline row before *and* after every
variant for the same reason.

### 4.1 Before and after, alternating

Three pairs, alternating, each pair with the two builds started within a minute of each other
and the GPU at the same reported temperature (75-76 C). The "before" column is the HEAD version
of this directory, checked out into a scratch project and run with the same harness. Figures
are the mean of the three runs; the fps minimum is the worst of the three.

| 1.7 m/s walk, 144 m, 1920x1080 | before (HEAD) | after | change |
|---|---|---|---|
| **fps mean** | 93.6 | **206.0** | **2.20x** |
| **fps p50** | 92.7 | **191.3** | 2.06x |
| **fps p05 (worst 5%)** | 70.7 | **130.3** | 1.84x |
| **fps minimum** | 63 | **87** | +38% |
| **GPU ms p50** | 9.90 | **4.28** | **2.31x cheaper** |
| GPU ms p95 | 13.82 | 6.65 | 2.08x cheaper |
| CPU ms p50 | 11.85 | 5.74 | 2.06x cheaper |
| draw calls p50 | 323 | 300 | -7% |
| primitives p50 | 315,891 | 224,645 | -29% |
| video memory | 178.0 MB | 188.7 MB | +10.7 MB |
| shell triangles | 64,676 | 113,656 | +76% |
| prop instances | 33,470 | 19,015 | -43% |
| generation, topology | 4.64 ms | 3.90 ms | - |
| generation, dressing | 523 ms | 651 ms | +128 ms (the noise volumes) |

**The topology is untouched.** Both builds report content hash `0xAD83E3ED`, 2,006 open cells,
351 stations, 8 edges, 4 chambers, 7 junctions. Everything in this pass is downstream of the
blob, which is the seam `DESIGN-PRINCIPLES` §5 asks for doing its job: a complete rebuild of
the material layer moved not one bit of what the simulation would play on.

**It holds 60 with more room than the build it replaces**: the worst single frame of a 154 m
walk is 87 fps, against 63 before, and the median frame is twice as fast. That is not a
tuning result, it is §2.1 -- roughly 700 integer hashes per rock fragment became roughly 30-60
texture fetches, and the parallax, the three normal scales, the wetness field and the water
surface were all bought out of the change.

The 76% more shell triangles and 29% fewer primitives in the same table are the trade in §2.8
and §2.10: geometry moved off the floor scatter and into the shell, where it buys silhouette.

For context, the figure recorded in `summary.txt` before this pass was fps mean 107.3 /
p50 105 / gpu 8.75 ms, measured on a different day. Today the same code measures 93.6 / 92.7 /
9.90. That gap is the machine, not the build -- see §4.0.

### 4.2 Technique ablation

Two tables, because they were taken differently and only one of them is trustworthy at the
sub-millisecond level.

**(a) The photoreal techniques**, measured back to back on the same walk at 5.0 m/s within
three minutes of each other, GPU at 77-79 C throughout. The settled baseline over three
interleaved runs was 4.45 / 4.44 / 4.51 ms, so the baseline noise here is about +-0.04 ms and
these deltas mean something.

| technique | frame with it | frame without | **cost** |
|---|---|---|---|
| parallax occlusion on the floor (§2.2) | 4.47 ms | 4.20 ms | **0.27 ms** |
| three normal scales (§2.3) | 4.45 ms | 4.29 ms | **0.16 ms** |
| SSAO (§2.9) | 7.01 ms | 4.29 ms | **2.72 ms — CUT** |

A separate clean A/B an hour earlier put SSAO at 8.68 ms against 4.33 ms, i.e. **4.35 ms**. So
its cost is somewhere between 60% and 100% of the entire rest of the frame, depending on
thermal state, and it is the only thing in this pass that was ever close to expensive. The two
techniques that actually do the work cost 0.43 ms together.

The generated noise volumes (§2.1) cannot be ablated with a switch, because without them the
shader has no noise at all. Their cost is the whole before/after column in §4.1.

**(b) The original spike's ablation rows**, re-run for comparability with the numbers in
`NOTES.md` §5.3. These were taken across a 20-minute interleaved sequence during which the GPU
clock drifted between 210 and 1245 MHz, so **treat anything under 1 ms as noise**. Full log in
`ablation.txt`, with the thermal state printed against every row.

| build | GPU p50 | nearest baselines | apparent cost | draws | primitives |
|---|---|---|---|---|---|
| **no visibility ranges** | **51.43 ms** | 6.16 ms | **≈ 45 ms** | 599 | 535,060 |
| no props (shell only) | 4.59 ms | 5.54 ms | 0.95 ms | 24 | 61,478 |
| no lamp shadows | 4.20 ms | 4.54 ms | 0.33 ms | 146 | 117,038 |
| no volumetric fog | 3.67 ms | 4.38 ms | 0.71 ms | 307 | 230,632 |
| no standing water | 5.11 ms | (drifted) | below noise | 309 | 250,682 |

**Two findings worth carrying forward.**

1. **Visibility ranges are no longer insurance, they are the frame.** `NOTES.md` §5.3 measured
   them at about 3 fps at this cave length. They are now worth 45 ms — the difference between
   6 ms and 51 ms — because the shell is 76% more triangles at a finer ring spacing and every
   one of its pixels costs more. This is the single most important performance fact in the
   directory and `OccluderInstance3D`, still unused, is the obvious next lever.
2. **The original spike's headline finding has reversed.** It measured the empty corridor as
   *slower* than the dense one (63 fps against 85) because the frame was fragment-bound on the
   rock shader and the props were occluding it. With the shader ~2.3x cheaper that is no longer
   true: hiding the props is now 0.95 ms *faster*, not slower. **The budget statement "there is
   room for considerably more stuff" was true of the old shader and should not be inherited
   without re-measuring.** There is still room, but it is now ordinary room, and it is bounded
   by the draw-call and shadow-pass cost of the stuff rather than being free.

### 4.3 The exposure contract

`lumcheck.py`, ART-DIRECTION §2.9, on linearised luminance, over the twelve canonical frames in
`shots/`.

| frame | blown >0.50 | mid >0.18 | legible >0.05 | true black <0.02 | verdict |
|---|---|---|---|---|---|
| 01_wide_passage | 0.01% | 0.04% | 2.96% | 89.20% | **too dark** (3% floor) |
| 02_dense_mid | 0.02% | 0.45% | 9.35% | 81.48% | ok |
| 03_underfoot | 0.06% | 4.17% | 13.66% | 81.21% | ok |
| 04_chamber | 0.00% | 0.27% | 4.50% | 88.91% | ok |
| 05_two_registers | 0.17% | 5.43% | 24.98% | 56.78% | **over on legible and black** |
| 06_falloff_to_black | 0.01% | 5.07% | 14.44% | 80.41% | ok |
| 07_junction | 0.08% | 1.73% | 10.37% | 79.37% | ok |
| 08_waterline | 1.43% | 7.02% | 19.62% | 68.49% | **not enough black** |
| 09_machine_ground | 0.27% | 5.80% | 12.52% | 82.42% | ok |
| 10_natural_shallow | 0.06% | 3.79% | 13.70% | 80.58% | ok |
| 11_set_line | 0.00% | 1.07% | 12.04% | 74.72% | ok |
| 12_crown | 0.00% | 0.93% | 4.02% | 83.24% | ok |

**Nine of twelve pass, which is the same score as before this pass, on different frames.**
Before: `08`, `11`, `12` failed. Now: `01`, `05`, `08`.

* `12_crown` was the previous pass's one genuine near-field blow-out — 32% legible against a
  20% ceiling, looking up into a crown 1.5 m away. It now passes at 4.02%. `11_set_line`
  recovered too.
* `01_wide_passage` is newly marginal at 2.96% against a 3.0% floor. That is §5.2's floor
  albedo: a passage seen end-on is mostly floor, and the floor now returns about half what the
  schematic value returned. It is 0.04 percentage points under, which is a rounding error, not
  a different kind of frame — but it is the direction the whole pass moved and it is worth
  watching.
* `05` and `08` both have a beacon pilot and a lot of near wall in them. `08_waterline` failed
  the true-black floor before this pass as well; the previous notes argued the contract's floor
  is the thing that is wrong for a wet frame, and this pass makes wet frames wetter.
* **"Legible" going UP across the set while the floor albedo went DOWN is the wetness field.**
  A wet surface returns a specular lobe where a dry one returned nothing, so more of the frame
  now carries information at the same lamp power. That is ART-DIRECTION §2.7's argument
  ("a wet passage stays findable and a dry one does not") showing up in the histogram.

* **Nothing here is a leak.** Ambient is disabled, world background strength is 0, and no
  screen-space indirect lighting was shipped (§5.3).

---

## 5. Art rules bent, and how far

DESIGN-PRINCIPLES §6 says two of these contradictions are unresolved and that until a designer
rules, the spikes treat the *intent* as binding and the *letter* as amendable. Here is exactly
what I did with each.

### 5.1 "No image texture, UV map or bitmap" (§9, §3.2) — **bent, on an existing default**

Four 64³ noise volumes are generated at load and sampled as `sampler3D`. Nothing imported,
nothing unwrapped, nothing photographic, every volume a pure function of the cave seed, 786 KB
in total. This is `PROCEDURAL-AND-GODOT.md` question 5, whose recommendation is already **yes**
— but it has never been ruled on, and this pass now *depends* on it: without it the shader
budget for parallax and three normal scales does not exist. **If the answer comes back no, most
of §2 goes with it.**

### 5.2 "One rock material, four scalars, no hue axis" (§3.1, §9) — **bent twice, one of them a written number**

1. **Mineral staining moves chroma by ±3.5%** on the red and blue channels, from one
   low-frequency noise. It is a value modulation with a slight warm/cool swing, not a hue axis:
   one rock family, no biome colour, nothing in the frame is a different *colour* of rock. It
   is the smallest amount of chroma I could find that stops a large lit wall reading as a
   single flat swatch. Rust staining off ferrous kit is the other chroma source and it was
   pulled back twice during this pass because it was turning the deep drive orange.
2. **The "scoured floor" value is no longer §3.1's `(0.420, 0.360, 0.280)`.** That is a lit
   schematic value and it is far outside anything measurable off a wet mine floor, which is
   muck at 0.05–0.12 linear. It is now `(0.190, 0.158, 0.122)` dry, ×0.54 where soaked. The
   other four rock values — dry, wet, submerged, tide-mark crust — are unchanged from the
   document. **This directly contradicts a written number and needs a ruling.** The consequence
   is visible in §4.3: the floor genuinely returns less light, and the frames that are mostly
   floor moved down the histogram accordingly.

### 5.3 "No ambient light, ever, in any costume" (§9) — **tested, then cut**

I turned SSAO onto direct light, flagged it as a rule I was testing rather than assuming, and
measured it. §2.9 and §4.2: 4.35 ms of an 8.68 ms frame, every large frame spike in the walk,
and a 0.25% mean absolute pixel difference. **Cut.**

The argument is still worth a ruling for its own sake: occlusion of direct light *removes*
light from creases and cannot make a pixel lit that no fixture is lighting, so it is not an
ambient term in a costume. But it is not worth its price in this engine on this scene, and the
material AO computed from the parallax height field does the same job from real geometry
rather than from a depth buffer.

I did **not** try SSIL, which genuinely would add light. Ambient light source stays
`AMBIENT_SOURCE_DISABLED`, background strength stays 0, no sky term and no reflection probe was
added, and every lit pixel in every frame in `shots/photoreal/after/` traces to the lamp or to
a beacon pilot.

---

## 6. What is still not photoreal

Judged off the frames in `shots/photoreal/after/`, in the order I would fix them.

1. **The aggregate still reads slightly melted.** The blocks have flat tops and hard arrises in
   the height field, but linear filtering of a 64³ volume smooths the cell wall over about one
   texel — roughly 9 mm at the working scale — so the arris is a 9 mm fillet rather than a
   fracture. A 128³ volume, or storing the cell id in a nearest-filtered channel and the bevel
   in a linear one, would fix it. **Top of the list.**
2. **The worked wall is still the weakest surface in the game**, which is what the previous
   pass's §7 said, but it is now weak for a different reason. It has relief, drip runs, joints
   and crevice dirt; what it lacks is *macro* form — spalled slabs, an overbreak lip above a
   set, one bed that has parted and dropped 100 mm. That is geometry, and §2.10 only started
   it.
3. **A lamp at the eye is a photometric problem, not an art problem.** N·L ≈ N·V means the
   cosine term barely moves, so nearly all of the surface read has to come from cavity
   occlusion, albedo variation and specular. Real mine photographs are lit off-camera. The
   0.26 m offset is the cheapest change in this pass; a second source — even ART-DIRECTION
   §2.8's contingency circuit at its low end — would do more for photorealism than any shader I
   could write. **This is a design question, not an art one, and I would put it to the
   designer.**
4. **No parallax on the walls.** Only the floor has it. Bedded and jointed faces would take it
   well and the code is written to be reused; the reason it is not there is time.
5. **No decals, and no tracks that record a specific event.** The wheel ruts are a rule keyed to
   the rail gauge, not a machine's actual path. "The machine's own tracks in the mud" is on
   ART-DIRECTION §3.6's short list of what should read at 10 m and it still does not exist.
6. **The kit meshes are now the limiting factor, not the kit shader.** A timber set is six
   boxes. No shader makes a box into a sawn baulk with a split end and a crushed bearing, and
   the frames where a prop is within a metre of the lens are the frames that look worst.
7. **The chambers still interpenetrate the swept passage.** Unchanged from the previous pass.
8. **Nothing is dirty in a *specific* way.** Every stain is a noise field. Real mines have
   spills, scorch, a place where something leaked for thirty years — which is exactly what
   `PROCEDURAL-AND-GODOT.md` §4.5 reserves the decal channel for.

---

## 7. Everything I guessed, in one list

The previous pass's twenty still stand. These are additional, and everything here is mine
rather than read out of a document.

1. **Every number in `rock.gdshader`.** The three tile sizes (3.70 m form, 0.470 m detail,
   0.0615 m micro), every amplitude, every smoothstep threshold, both cellular scales (0.60 m
   coarse aggregate, 0.155 m fine), and the 75 mm parallax depth.
2. **That the aggregate is 100 mm blocks with a 25 mm grade between them.** Nothing in the docs
   says what a mine floor's grading is.
3. **The whole composition of the wetness field**, including that the datum's influence reaches
   1.5 m above the line and that a floor gets a wetness term a wall does not.
4. **That the water datum is global.** ART-DIRECTION gives a waterline per axis; this treats the
   whole cave as having drowned once, to one level, which is why the tide-mark crust is now
   continuous rather than confined to flooded stations. It is a claim about the fiction and it
   is mine.
5. **Puddle level as a low-frequency field gated on wetness**, and the mineral rim at the
   wet/dry boundary.
6. **Wheel ruts at ±0.30 m, 42 mm deep, polished to roughness 0.44**, with a wandering
   centre-line, gated on `worked` between 0.25 and 0.70.
7. **The water shader's absorption coefficients** `(2.30, 1.45, 1.20)` per metre, and that 14
   SSR steps is the right number.
8. **Which parts are metal at all.** The F0 values themselves are standard measured figures;
   the assignment — iron, steel and aluminium `METALLIC 1`, timber, composite, porcelain and
   cable 0 — is mine.
9. **The corrosion floor on ferrous kit**: that nothing ferrous in a drowned mine is bare,
   expressed as `corr >= rust · (0.42 + 0.30·w_datum) · (0.55 + 0.45·lowness)`.
10. **The lamp offset `(0.26, −0.22, 0.10)` m** from the sensor, and the energy of 5.4. The
    offset is a claim about where a lamp sits on a machine that has no model yet.
11. **`bumped()`'s clamp at `atan(1.2) ≈ 50°`.**
12. **The prop counts after the cut** — `8 + 17(1 − 0.62·worked) + 12(1 − integ)` stones, 9
    grit, 15 ballast — and the burial fractions: 0.25–0.72 of a radius for stones, 0.15–0.60
    for ballast.
13. **Ring resolution 40, four substeps, and the 0.155 m worked displacement amplitude.**
14. **The bedding ledge amplitudes** in the vertex displacement: 30 mm swell, 45 mm parting.
15. **That `UV2.x` should be re-allocated to the lateral offset.** The waterline it replaced is
    now a uniform; this is a decision about a vertex attribute, not a fact.
16. **`pom_far` 4 m, `floor_bump_far` 12 m, `detail_far` 13 m, `micro_far` 2.6 m** — the four
    distances at which the surface stops getting more detailed.
17. **The stone tint `(0.80, 0.775, 0.74)` and wetness 0.55** applied over the ART-DIRECTION
    stone value, which is a 20% darkening of a documented number.

---

## 8. The pictures

`shots/photoreal/before/` and `shots/photoreal/after/`, identical camera poses, 1920×1080.

| pair | what it is for |
|---|---|
| `p1_underfoot_macro` | **the frame the designer named**: 1.2 m above the floor, looking down at 45° |
| `p2_wet_floor_water` | the drive approaching the sump: wet floor, ballast, rails |
| `p3_wall_lamp_dist` | a rock wall across the passage, at lamp distance |
| `p4_bedded_face` | a natural, low-`worked`, high-`bedding` face close up |
| `p5_iron_prop` | iron and timber against rock: sets, pipe run, mesh, wet floor |
| `p6_wide_passage` | the wide shot down a driven passage |
| `p7_ballast_gauge` | down among the rails: sleepers, ballast, spall |
| `p8_junction_wet` | a crosscut leaving the drive |

`shots/photoreal/cmp_ssao.png` is the SSAO on/off pair from §2.9 (on top, off bottom).
`shots/` holds the twelve canonical frames, re-rendered, which is what §4.3 measures.
