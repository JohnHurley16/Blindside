# The agent's own view, as a 3D point cloud

Godot 4.7.2, Forward+, NVIDIA GeForce RTX 3080 Laptop GPU (Vulkan 1.4.312). Every number
below was taken on that adapter with no other Godot process running; the thermal state is
quoted where it matters, because this machine throttles to 780–1275 MHz against a 2100 MHz
maximum and two runs of the same build differ by more than any change in this directory.

The data is one real `phase1` match, seed 7, player, exported by `export_belief.py`. Nothing
is mocked. 5,663 points, 12 fixes, one spoof at 2:21, `lost in the cave` at 8:00.

Run it:

    <godot> --path spikes/godot/cloud --resolution 1920x1080
    <godot> --path spikes/godot/cloud --resolution 1920x1080 -- --shotsonly
    <godot> --path spikes/godot/cloud --resolution 1920x1080 -- --bench

Drag to orbit, wheel to zoom, `space` to play, arrows to scrub, `1/2/3` belief / both /
truth, `b` additive vs solid, `p` multimesh vs points, `d` decal, `l` lines, `f` walked
discs flat, `o` orthographic, `+/-` disc size, `h` the readout.

Rebuild the data (needs the repo `.venv`; `data/` is gitignored and is ~230 MB):

    .venv/Scripts/python.exe spikes/godot/cloud/export_belief.py --seed 7
    .venv/Scripts/python.exe spikes/godot/cloud/build_buffers.py --seed 7

The two 4,000,000-point bench rows need one more file, deleted after measuring because it
is another 256 MB:

    .venv/Scripts/python.exe spikes/godot/cloud/build_buffers.py --seed 7 --dense 4000000

---

## 1. The finding that makes the whole thing cheap

**A phase1 belief point is moved by at most one fix, ever.** `PointCloud.relax()` moves
points with `t > correction.epoch_t`, and `epoch_t` is the *previous* fix's time; point
times are monotonic in index, so the moved set is always a contiguous suffix, and a point
placed between fix *k−1* and fix *k* is dragged by fix *k* and then frozen for good. That
is asserted, not assumed — `export_belief.py` fails if any point is touched twice, and on
seed 7 it holds for all 5,663 (5,353 moved once, 310 never moved).

That is exactly ART-DIRECTION §8.2's *"an old return is dimmer and stays where it was
believed to be at the time"*, and it means **a point needs two positions, two ray
directions and one timestamp, and the whole of drift, the fix and the spoof is a
per-vertex switch in the vertex shader.** Scrubbing costs nothing per frame at any point
count. No CPU rebuild, no re-upload, no reordering — the instance buffer is uploaded once
and the scrub time is a uniform.

This is worth carrying into Phase 3: it says the belief cloud is an *append-only* buffer
plus a per-point "which epoch am I in" tag, which is a very cheap thing for a GDExtension
to hand Godot.

## 2. Technique, and what it costs

**MultiMesh of quads with an oriented-disc vertex shader.** One `MultiMeshInstance3D`,
`TRANSFORM_3D` + custom data, 16 floats (64 bytes) per point, loaded as one `memcpy` from a
`.mmbuf` file. The instance transform is not a transform: its columns are free storage.

    column 0 = p1 - p0    what the fix did to this point, metres
    column 1 = n0         sensor -> hit before the fix, UNNORMALISED (length = range)
    column 2 = n1         the same after it
    origin   = p0         where it was believed to be when it was measured
    custom   = (confidence, t_placed, t_fix or -1, source)

The quad corner comes from `UV`, because `world_vertex_coords` hands `VERTEX` in already
multiplied by that basis and the basis is not a rotation.

Measured at 1920×1080, whole map in frame, 40 frames per row after a 60-frame settle,
GPU 80 °C at 780–1275 MHz against a 2100 MHz maximum — i.e. **throttled 1.6–2.7×**, so every
row here is pessimistic and a cold clock would be faster.

| buffer | technique | instances | GPU ms | CPU ms | draws | load ms |
|---|---|---|---:|---:|---:|---:|
| real match | multimesh quad | 5,663 | 0.63 | 0.19 | 3 | 1.4 |
| real match | PRIMITIVE_POINTS | 5,663 | 0.54 | 0.19 | 3 | 1.4 |
| dense | multimesh quad | 100,000 | 1.07 | 0.18 | 3 | 25 |
| dense | PRIMITIVE_POINTS | 100,000 | 1.04 | 0.22 | 3 | 13 |
| dense | multimesh quad | 500,000 | 3.43 | 0.23 | 3 | 67 |
| dense | multimesh quad | 1,000,000 | 7.99 | 0.23 | 3 | 146 |
| dense | multimesh, mix + depth write | 1,000,000 | 7.86 | 0.19 | 3 | 120 |
| dense | multimesh quad, no floor decal | 1,000,000 | 7.66 | 0.22 | 2 | 119 |
| dense | multimesh quad | 2,000,000 | 15.82 | 0.21 | 3 | 275 |
| dense | PRIMITIVE_POINTS | 2,000,000 | 8.51 | 0.21 | 3 | 236 |
| dense | **multimesh quad, sub-pixel discs** | 2,000,000 | **5.56** | 0.29 | 3 | 240 |
| dense | multimesh quad | 4,000,000 | 33.95 | 0.19 | 3 | 632 |
| dense | **multimesh quad, sub-pixel discs** | 4,000,000 | **9.23** | 0.21 | 3 | 626 |

The two bold rows are the same instance counts with the disc shrunk to nothing, so what is
left is the vertex and instance cost and no fill at all. **The ceiling is fill rate, not
instances.**

- Geometry: **~2.3 ms per million instances**, flat. 4M oriented, drift-switched,
  age-and-confidence-shaded quads cost 9.2 ms of vertex work and Godot never blinks.
- Fill: the other **~10 ms per million** at these disc sizes and this camera, and it scales
  with *projected disc area*, not with N. Halve the disc and you halve it; fly the camera
  into the cloud and it goes up.

So the honest statement of the ceiling is **not** a point count:

> **The belief view costs ~2.3 ms per million points plus whatever screen area the discs
> cover. At the footprint sizing in §3 and a whole-map camera, 1,000,000 points is 8.0 ms
> (comfortable), 2,000,000 is 15.8 ms (the entire 60 fps budget, and the practical
> ceiling as built), and 4,000,000 is 34 ms (30 fps).** Close-in cameras at 1M measured
> 6.2–11 ms depending on how much of the frame the cloud fills.

Two more things the table says. The floor decal is **0.33 ms** at 1M (3 draws vs 2). And
`blend_mix` + depth write is **not** meaningfully cheaper than additive here (7.86 vs 7.99;
an earlier run measured 6.72 vs 7.70, so the difference is inside the throttling noise) —
early-Z does not pay for itself when the discs are this small.

There is no 4M `PRIMITIVE_POINTS` row: that path needs a GDScript loop over every point to
build its mesh, is capped at 2.1M, and above the cap silently keeps the previous mesh. It
would have measured nothing. Which is itself the argument against it — the MultiMesh path
takes the same buffer the exporter writes, as one `memcpy`, with no per-point CPU work at
any size.

**Why not the other three techniques.**

- **`ArrayMesh` with `PRIMITIVE_POINTS`** is 1.9× cheaper at 2M (8.5 vs 15.8 ms) and is the
  thing ART §8.2 explicitly rules out: `POINT_SIZE` is screen-space, so it is a
  fixed-angular-size sprite, so a bank of returns is fog and a wall mapped twice is two
  patches of fog. It also cannot carry per-instance custom data (confidence, times and
  source have to be smuggled through `COLOR`, at 8-bit precision), and building it costs a
  GDScript loop per point. Kept as a baseline (`p`, shot 17) and rejected.
- **`GPUParticles3D`** would put the drift switch in a process shader and re-simulate every
  frame, to reproduce data that is static and already known. It buys nothing here and costs
  a compute dispatch per frame.
- **A compute-built vertex buffer** is what you would reach for if the cloud had to be
  *generated* on the GPU. It does not: the sim produces it, and §1 says the per-frame update
  is a single float uniform. The MultiMesh buffer is already the compute-friendly layout, so
  this is the upgrade path (frustum-cull or LOD-cull instances into an indirect draw) rather
  than a different design.

**Three draw calls** for the entire belief view at any point count: the cloud, the floor
decal (one more MultiMesh) and one `ImmediateMesh` for the trail, the beacons and the
ghost. CPU is 0.18–0.29 ms and does not move with the point count, because the scrub is a
uniform.

**Where the ceiling is.** At 1920×1080 on this adapter, additive oriented discs cost about
**7.7 ms per million** wide, and **6.2–11 ms per million** when the camera is inside the
cloud (shots 18 and 13). So:

- **1,000,000 points is comfortable** — 7.7 ms leaves half a 16.7 ms frame for everything
  else, and the belief-only view has nothing else in it.
- **2,000,000 points is the ceiling as built** — 15.5 ms is the whole frame. It renders,
  it is stable, it is not shippable next to a truth layer.
- Beyond that it is linear in instances and the buffer is the other wall: 64 bytes each,
  so 4M is a 256 MB upload and a 0.5 s load.

Points are unlit and emissive and this **is** cheap: 2M oriented world-space discs with
per-instance drift, age and confidence, in three draw calls, at 64 fps, on a throttled
laptop GPU. The claim in the brief holds.

## 3. Blending, sorting and overdraw

**No sorting is done and none is needed.** The cloud renders `blend_add,
depth_draw_never, depth_test_disabled`: addition is commutative, so draw order does not
matter, and depth-testing it against itself would throw away the accumulation that makes a
bank of returns read as a surface. It also means the cloud is never occluded by the truth
layer, which is what ART §8.3 wants — *"the belief layer must never be dimmed to let truth
read"*.

**Overdraw is real and it is handled by making each disc dimmer as the count rises.** A
million discs off the same surfaces overdraw the same pixels hundreds of times; at a flat
per-disc emission the whole map clips to white (this happened, and the first 2M frame was
a solid white ribbon). Two compensations, both automatic:

- **Emission ∝ 1/√N.** Straight 1/N is energy-correct and erases every isolated return;
  √ is the compromise that keeps a bank at roughly constant brightness while a lone hit
  stays visible. Guessed, tuned by eye against the frames.
- **Beam width ∝ 1/√N.** A denser sensor has a *narrower* beam: N returns off the same
  surfaces means the ray spacing fell by √(N₀/N), so the footprint falls with it. Below
  about 300k the footprint drops under §8.2's 45 mm and the constant takes over. This is
  the thing that stops a million points becoming a million 0.9 m blobs, and it is
  physically motivated rather than a fudge.

Even so, a close camera at 1M still needs a manual `gain` of 0.4–0.7 (shots 18, 20). The
right fix, not built: **compensate by measured screen coverage, not by point count** — the
overdraw at a given pixel depends on the camera, and √N cannot know that. A one-pixel
histogram pass, or simply scaling gain by the ratio of projected disc area to frame area,
would make it camera-independent.

`blend_mix` with depth write is also implemented (`b`, shot 16). It is marginally *cheaper*
(6.72 vs 7.70 ms at 1M — early-Z pays for itself) and it makes near banks opaque, but it
hides the map behind itself and produces order artefacts where discs are coplanar. The
additive x-ray is the right register for a survey; the solid one is worth keeping for the
first-person `enter-agent-perception` mode, where occlusion is the point.

## 4. Where ART-DIRECTION §8.2 was right, and the two places reality changed it

**Right, and it earned its keep:**

- **Hits, not dots.** Orienting each disc back along its return ray is the single biggest
  thing in these frames. A bank of returns reads as a *surface* from any angle with no mesh
  (shot 20 is the proof; shot 03 is the same camera on the sparse cloud). A camera-facing
  sprite of fixed angular size would have given fog.
- **Two classes, and only two.** `SENSED #63D6F7` at its scattered height and `WALKED
  #2E4854` at zero. The value gap between the two colours does all the work; do not give
  the walked class a separate dimming factor as well (I did, and it disappeared — 82% of
  seed 7's cloud is near-field/walked, so making it invisible removed most of the map).
- **Alpha carries confidence, size is the weak second.** Kept exactly.
- **Age shows, and old returns are never re-registered.** Kept, and the sim already
  enforces it (§1). The age curve is what separates two records of one passage in shot 08.
- **The floor decal.** ART is right that it is the element with area and the thing that
  makes drift read as a *shape* drifting — but see below.
- **Never meshed.** Nothing here is meshed and nothing needs to be.

**Changed 1 — the disc is the sensor footprint, not a constant 45 mm.** phase1's sonar
fires 60 rays over 120° (2.0° apart, 1.2° of bearing noise) to 30 cells; its lidar fires 90
over 360° (4.0°) to 18 cells. The patch of rock a return could have come off is therefore
**0.2–0.7 m across at working ranges — five to fifteen times 45 mm.** At a constant 45 mm
the cloud is invisible in any frame wider than a macro, which is what the Blender board hit
and worked around by drawing 70–100 mm discs "so a 960 px board can show them". Sizing by
`range × beamwidth` is not a legibility hack: it is *more* honest than the constant,
because the disc then states the uncertainty the beam actually has, and it is what makes
banks read as surfaces. **Recommendation: §8.2 should say the disc is the beam footprint,
with 40–50 mm as the floor for a fine lidar.** (`u_beam_rad = 0` restores the literal
constant; shot 90 is that, at 600 mm, so the shape of a bare oriented disc can be seen.)

**Changed 2 — a screen-space floor of ~1.6 px, in both axes.** A disc facing back along a
horizontal ray *is a vertical plane*, so from any camera above about 40° elevation it is
seen edge-on and the survey vanishes. That is visible in the Blender board's own director
frames (`docs/art/vision/found/cloud/01_clear_director.png`, `04`, `05`): the points there
are slivers one pixel wide and the image is carried entirely by the decal. The fix is to
widen the quad in *screen* space only, and only up to about a pixel, so the orientation
stays honest inside ~15 m and degrades to a dot beyond it. **This is a real limit and it
should be written down: the "hits not dots" rule buys a surface at conversational range
and buys nothing at map range, where the decal has to carry the picture — which is what
`SPECTATOR-DISPLAY` §6.4 already said.**

**Changed 3, smaller — the decal is a wash, not a mosaic.** One hard quad per occupied bin
reads as tiles and competes with the points (again, visible in the board's frames). Drawn
as overlapping soft blobs at 2.6× the bin pitch with a radial falloff, at 10% rather than
25%, it becomes the continuous dark-cyan ground §8.2 asks for and stops fighting the hits.

**Dropped — the beacon chain.** `belief_scene.py` joins recorded beacons in drop order.
In 3D that is a straight line right across the whole map and it is the brightest thing in
frame; it asserts structure the belief does not have. Not in §8.2, so it is gone.

## 5. The three things belief does that truth does not

All three are produced by the *same* mechanism and no special-casing: the vertex shader
picks `p0` or `p1` by whether the scrub time has passed `t_fix`, and eases across 0.7 s
because a fix lands in one sim tick and at 20 fps the ghost corridor slid onto the original
before the eye could start (`belief_scene.py` learned that first).

**DRIFT — `05_drift_smear.png`, t = 7:07.** 246 s of dead reckoning between the fixes at
3:03 and 7:08. Position error reaches 73 cells (44 m) at 5:28. The cloud does not "blur":
it *walks*, because every point is placed at the believed pose plus the measurement and the
believed pose is wrong by a growing amount. What you see is a map whose far end is bent
away from its near end.

**THE FIX — `06_fix_before.png` / `07_fix_after.png`, same camera, 7:07 and 7:13.** This is
the pair, and it is the clearest image in the set. Before: the machine walked out along one
passage at 3:03–6:21 and back along it at 6:21–7:08, and the two records of *one* passage
sit 5 cells apart — rigid alignment over the two epochs gives a median residual of 0.47
cells at a shift of (0.5, −5.0) — both drawn, with the believed trail running through each.
After: `player_6` answers, the estimate jumps 13.3 cells (4.3 σ), everything placed since
the 3:03 epoch swings about that epoch, and the two records collapse into one. That is
`pose_correction.py`'s docstring made visible — *"the ghost slides onto the original"*.

**And the doubling a fix does not close — `08_fix_two_corridors.png` / `18_..._dense.png`,
t = 8:00.** The second traverse (7:46–8:00) fell in a *later* epoch than the first
(6:21–7:08), so no correction will ever bring them together: they stay 17.4 cells (10.4 m)
apart for the rest of the match. Measured by rigid alignment over the two epochs: **median
residual 0.21 cells at a shift of (3.5, 17.0)** — the same shape, twice, in two places, with
no annotation. `age_knee` is set to 90 s in these two frames so the older copy sits at the
0.35 age floor and the newer one does not; that is §8.2's own "an old return is dimmer"
doing the separating, not a third colour.

**THE SPOOF — `09_spoof_before.png` / `10_spoof_after.png` (and `21`/`19` dense), 2:21 and
2:24.** The rival has cloned `player_3` and put the clone four cells ahead of the victim.
The next fix runs the same code as an honest one and drags the pose 33.3 cells — **11.1 σ**,
against 0.3–4.3 σ for every honest fix in the match. 441 points placed since 1:44 are
hinged about the 1:44 epoch and folded back across the map they already drew; their centroid
moves 18 cells and the recent end moves the full 33. In the pair you can watch a corridor
that ran away to the horizon collapse onto the near map. Rigid alignment says the folded
limb ends up as a 14.9-cell-shifted copy of the map it tore away from (residual 0.40 cells).

Note what is *not* on screen in any of these: nothing says "a fix happened", nothing is
yellow, nothing is annotated. The tear is the only evidence, which is the design.

### Is the fix frame legible without a caption? Honestly: the pair is, the still is not.

`06`/`07` is legible with no caption. Two traces of one passage, then one trace, same
camera, four seconds apart: the eye reads *that came together* immediately, and it reads it
without knowing anything about the game.

`08` and `18` — the doubling as a single still — are **not** legible to a cold viewer, and
I do not think they can be made so by tuning. The reason is structural: **two parallel
banks of returns is also what one passage looks like**, because a passage has two walls.
The frame contains everything it needs — the same shape twice, the older copy dimmer, the
believed trail running through both — and a viewer who has been told the machine walked one
corridor reads it correctly. A viewer who has not been told will read a junction. At 1M
points (`18`) it is close; at the toy sim's 5,663 (`08`) it is not.

What actually carries the reading, in order: **motion** (the swing at the fix is
unmistakable and instant, and it is 0.7 s of animation this renderer already does), then
**density**, then the age difference, then the doubled trail. A still image is the weakest
of the four, and this is the one place where I would push back on the brief: the single
most important image in the game may have to be a two-second clip.

## 6. Is the belief view the answer to the spectator legibility problem?

`PROCEDURAL-AND-GODOT` §5.4(a): ART §2.1's four-source light economy plus §9's "no ambient
light, ever" means a spectator camera looking into a chamber with no agent in it sees black,
and §8.3's "truth at 30–40% exposure" cannot help, because **exposure is not a light
source; you cannot expose black.**

**Tested, and the claim holds — with one qualification.**

- The belief layer in this spike is rendered with **zero lights in the scene**. The
  renderer prints the evidence on every run rather than claiming it in prose:

      belief layer: 0 Light3D in the scene; ambient source 1 (1 = AMBIENT_SOURCE_DISABLED);
      background BG_COLOR (0.0235, 0.0314, 0.0431, 1); no fog, no GI, no shadows;
      every cloud shader unshaded

  It is legible everywhere in the map, at every camera angle, at every scrub time, with no
  light source at all, because emission is not lit geometry.
  `15_truth_only.png` is the truth layer, and it only reads at all because I gave it the
  **non-diegetic survey fill** §5.4(a) recommends — two shadowless directionals. Without
  them that frame is black, exactly as predicted. `14_both_registers.png` puts them
  together at truth 35%.
- So: **the belief view removes the exposure problem for the live run view completely.**
  ART §8.3 already makes belief-only the default live view; this spike says that choice is
  also the one that makes the run view *possible*, not merely legal.

**The qualification, and it matters.** The belief view is legible but it is not
*self-locating*. `14_both_registers.png` is the honest picture: at 8:00 the cloud and the
true cave barely overlap, because the machine is 56 cells wrong. A spectator watching
belief-only has no idea where in the world anything is — that is the point of the game, but
it means the belief view solves *legibility* and does not solve *orientation*. Anything the
replay needs to show about the true world (a rival closing, the machinery, where the shaft
is) still needs the truth layer, and the truth layer still needs the survey light. **So:
belief-only answers the live view; it does not answer the replay, and §5.4(a)'s survey-light
recommendation should still be taken.**

One more thing that fell out and is worth saying: **the belief view is legible in
thumbnails and in motion in a way the lit truth view is not**, because there is no dynamic
range problem at all — nine-tenths of the frame is true black and the tenth that is not is
one hue at a known intensity.

## 7. What is still wrong

1. **The toy cloud is too sparse, and that is the real limit on the fix frame.** 5,663
   points in eight minutes, of which only **1,007 are wall returns**; 4,656 are near-field
   proximity hits at z = 0 and 34 are outright false. So the class ART §8.2 cares most
   about — a bank of returns off a wall — is 18% of the cloud, and 0.06 wall returns per
   free cell over the whole match. The doubling in `08` is marginal at that density and
   unmistakable at 1M (`18`). The renderer is not the problem. Either Phase 3's sensor
   returns far more, or the decal carries the map at wide angles, or both.
2. **Overdraw compensation is by point count, not by screen coverage** (§3). Dense
   close-ups still need a hand-set gain.
3. **`PointCloud` still stores no ray direction.** This spike captures the sensor origin by
   monkey-patching `Belief._add_point`; Phase 3's `Belief` needs one more array (or the
   believed pose at placement time) or "a disc facing back along its ray" is not drawable.
   Without it the honest fallback is a camera-facing sprite, which §8.2 explicitly rejects.
4. **The truth stand-in is an extruded grid**, 4.4 m crown, flat-shaded, no heightfield. It
   exists only so the two registers can be compared. Do not read anything into how it looks.
5. **No `walked` height information at all.** Near-field returns are placed at z = 0 by the
   sim, so the "rug" is genuinely flat. Whether that is right, or whether near returns should
   carry the same scattered height as wall hits, is a sim question.
6. **The believed trail, the ghost and the beacons are drawn 1 px wide** and get thin at
   distance; they want a real line shader with world-space width.
7. **MSAA 2× is on** and is the cheapest thing that stops an edge-on disc aliasing into a
   dotted line. Not measured against MSAA off; it should be.
8. **Age is a linear ramp to a floor.** §8.2 says age shows; it does not say how. The knee
   (150 s by default, 90 s in the doubling frames) is a guess and it is load-bearing for
   the most important image in the set.

## 8. Every guess, in one place

1. **The sensor head is 0.45 m above the floor.** Used to give the return ray a vertical
   component so discs are not all perfectly vertical. No source.
2. **The disc is `range × 2.0° / 2`, floored at 45 mm and capped at 0.9 m.** The 2.0° comes
   from `SONAR_RAYS`/`SONAR_ARC_DEG`; the cap and the choice of ray-spacing rather than
   bearing noise (1.2°) are mine.
3. **Beam width and per-disc emission both scale as 1/√N** for the dense ladder. The
   exponent is a compromise, not a derivation.
4. **Age ramps linearly to 0.35 over 150 s** (90 s in shots 08/18). §8.2 gives the floor,
   not the curve; the Blender board guessed "0.35 at the start of the match", i.e. 480 s.
5. **The fix ease is 0.7 s, cubic**, taken from `belief_scene.FIX_ANIM_SECONDS`.
6. **The screen-space floor is 1.6 px in both axes**, capped at 60× growth. Chosen by eye.
7. **The decal is 0.6 m bins, quads at 2.6× the pitch, radial falloff, 10% of `WALKED`.**
   §8.2 gives "a dark-cyan wash where count > 0"; the pitch and level are mine. The board
   used 2-cell bins at 25%.
8. **Walked discs are oriented along their ray like every other return**, not laid flat.
   `f` / shot 91 shows the flat variant. §8.2 says "walked at z = 0" and does not say which.
9. **The dense ladder is an upsample of the real cloud**: each return becomes K children
   scattered in its own disc plane (σ 0.42 m along the surface, 0.018 m along the normal,
   height jitter for sensed returns), inheriting the parent's fix displacement and times.
   Everything drift, the fix and the spoof do to the real cloud they do to the dense one.
   What it does **not** model is a denser sensor seeing surfaces the sparse one missed.
10. **The truth layer's survey light** is two shadowless directionals at energy 1.6 and 0.5,
    and "both" mode is truth at 35% with no desaturation step. §5.4(a) asks for a
    "shadowless fill, desaturated"; the numbers are mine.
11. **The truth cave is the phase1 grid extruded to 4.4 m**, from the Blender board.
12. **AgX tonemap, white 4.0.** Chosen so heavy additive overlap rolls off rather than
    clipping. Not specified anywhere.
13. **Belief-frame → world**: `(x·0.6, height·0.6, −y·0.6)` metres, so a plan camera looking
    down −Y with up = −Z reproduces phase1's own plan orientation.
14. **`SENSED` emission is 1.0 × the palette colour and `WALKED` is 1.0 ×** its (much
    darker) palette colour, i.e. the class difference is carried entirely by the palette.
    §8.2's "emission ~0.03–0.06 linear" is a *density* number and is met by the 1/√N gain
    at scale, not by the base value.

## 9. Two notes for Phase 3, neither of them art

1. **The export is split into a belief half and a truth half on purpose.** `seed7.json` +
   `seed7.bin` are all the live view opens; `seed7_truth.json` + `seed7_grid.bin` are opened
   only when the mode is `truth` or `both`. That is `PROCEDURAL-AND-GODOT` §2.1's rule made
   into a fact about which files are open rather than a fact about anyone's self-discipline,
   and it cost nothing. The real client should ship it as two transports.
2. **`Belief` needs the return direction** (guess 3 in §7). It is one array, and everything
   in §8.2 that makes this view work depends on it.

## 10. The three things that would most improve this next

1. **Make the fix a moment, not a frame.** The renderer already eases the correction across
   0.7 s and the scrub is a single uniform, so a two-second clip costs nothing to produce.
   It is the difference between "two corridors" and "*that* was one corridor". If the
   replay's key beat has to be still, then it needs the second copy marked, and the only
   legal marker left inside §8.2 is age — which is why `age_knee` is doing so much work in
   `08`/`18` and why it is guess 4.
2. **More returns.** Everything got better between 5,663 points and 1,000,000: banks became
   surfaces (`03` → `20`), the doubling became visible (`08` → `18`), the spoof's fold
   became a shape (`10` → `19`). The budget is there — 1M is 8 ms — and the constraint is
   the sensor, not the renderer. This is a Phase-3 sensor decision with a large art
   consequence and it should be made deliberately rather than inherited from the toy sim.
3. **Overdraw compensation by screen coverage, not by point count.** The 1/√N gain is
   camera-blind, so every close-in dense frame still needs a hand-set `gain` (0.4–0.7).
   Scaling by projected disc area over frame area, or one cheap histogram pass, makes the
   view self-exposing and removes the last hand-tuned number from the pipeline.

Three more, smaller, in order: a real world-space-width line shader for the trail and the
ghost; the enter-agent-perception mode, which is this renderer with the camera at 0.5 m and
`blend_mix` turned on (already implemented, never framed); and the second agent's cloud, so
that "two machines that disagree about where the same wall is" becomes a picture.

## 11. What is in `shots/`

| file | what |
|---|---|
| `01_early_sparse` | 1:40. How little it knows. Mostly walked, a few pinged walls. |
| `02_late_full_match` | 8:00, the whole believed map. |
| `03_low_orbit_surfaces` | 5:00, elevation 5°. Banks of discs as surfaces, sparse. |
| `04_macro_true_disc` | 1.8 m from the cloud at the direction's 45 mm floor. |
| `05_drift_smear` | 7:07. 246 s of dead reckoning. |
| `06_fix_before` | 7:07. One passage, drawn twice, 8 cells apart. |
| `07_fix_after` | 7:13, same camera. The fix has closed it. |
| `08_fix_two_corridors` | 8:00. The doubling a fix will never close: 17.4 cells. Sparse. |
| `09_spoof_before` | 2:21, one second before the lie. |
| `10_spoof_after` | 2:24, same camera. 33.3 cells, 11.1 σ, the map folded. |
| `11/12/13_dense_*` | 100k / 1M / 2M, same camera as `02`. |
| `14_both_registers` | Truth at 35% under the cloud. They never agree in shape. |
| `15_truth_only` | The truth layer alone — and it needs the non-diegetic survey light. |
| `16_solid_blend` | `blend_mix` + depth write, the rejected alternative. |
| `17_points_baseline` | `PRIMITIVE_POINTS`, the rejected alternative. |
| `18_fix_two_corridors_dense` | `08` at 1M. This is the frame that reads. |
| `19/21_spoof_*_dense` | The spoof pair at 1M. |
| `20_low_orbit_dense` | `03` at 1M. Banks of discs, unmistakably surfaces. |
| `90_probe_600mm_flat_disc` | Constant-size discs at 600 mm, no screen floor: the bare rule. |
| `91_probe_walked_flat` | Walked returns laid flat on the floor instead of along the ray. |
