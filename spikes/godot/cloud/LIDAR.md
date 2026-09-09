# The belief cloud as SENSOR DATA

Second pass on `spikes/godot/cloud/`. The designer looked at the first one and said:

> look at the point clouds from lidar in self driving cars and other systems... this looks
> nothing like that

They were right, and the reason is not tuning. The first pass rendered **5,663 points
exported from a real phase1 match** as soft additive discs. Two separate things made it a
nebula, and only one of them was the renderer:

1. **The sensor.** phase1's lidar fires 90 rays in ONE horizontal plane every 1.5 s to
   10.8 m. Over an entire eight-minute match that is **8,640 returns**. A scanning sensor
   produces more than that in **one tenth of a second**. There is no rendering technique
   that turns 8,640 samples into something a lidar engineer recognises, because the thing
   they recognise is a *structure* the toy sensor does not have.
2. **The blending.** Additive, depth-disabled discs sized by beam width. Additive
   accumulation is a fog operator: it is what you reach for when you have too few samples
   and want them to add up to a surface. It destroys exactly the feature that makes a scan
   readable.

This pass replaces the sensor and the mark. It keeps the data path.

    <godot> --path spikes/godot/cloud --resolution 1920x1080
    <godot> --path spikes/godot/cloud --resolution 1920x1080 -- --shotsonly
    <godot> --path spikes/godot/cloud --resolution 1920x1080 -- --stats
    <godot> --path spikes/godot/cloud --resolution 1920x1080 -- --old     # the first pass

Drag to orbit, wheel to zoom, `space` play, arrows scrub, `1..6` colour channel
(intensity / conventional intensity / height / ring index / epoch / range), `t` truth
overlay, `l` trail, `h` readout, `s` square dots, `f` beam-footprint sizing, `+/-` point
size floor, `q w e r y` rebake scene (chamber ×1, chamber ×4, walk, lie, toy).

Nothing is imported. `topology.gd` is copied verbatim from `spikes/godot/cave/`; the shell
sweep in `lidar_geo.gd` is a stripped version of that spike's `dressing.gd`. No file outside
`spikes/godot/cloud/` was modified.

---

## 1. What was kept, and the one thing that proves the invariant

**Kept, unchanged from the first pass** — this is not a rewrite of the renderer, it is a
rewrite of what the points *are*:

- One `MultiMeshInstance3D`, `TRANSFORM_3D` + custom data, **16 floats / 64 bytes a point**,
  uploaded once. The instance packing is byte-identical to `cloud_body.gdshaderinc`:
  column 0 = `p1 - p0`, column 1 = `n0`, column 2 = `n1`, origin = `p0`, custom =
  (intensity, `t_placed`, `t_fix`, ring + 64·surface class).
- **A belief point is moved by at most one fix, ever**, so the whole of drift, the fix and
  the lie is one `mix()` in the vertex shader and scrubbing is a single float uniform at any
  point count. That property came out of `phase1`; it survives the sensor change unchanged
  and it is still the reason this is cheap.
- **The cloud is one draw call** at any size (1,530,334 points in the walk scene, one draw).
  The trail is a second; the truth overlay adds five more when it is on.
- Belief and truth are separate node trees.

**The invariant.** `lidar_scan.gd` is the only file that reads the true world. `sweep()`
returns `out_local` — range/bearing/elevation **in the sensor's own frame** — plus a
timestamp, an intensity and a ring index. Every world coordinate downstream is produced by
`_place()` from a *believed* pose. There is no code path from the geometry to the cloud that
does not go through `sweep()`, and that is a fact about the function signature rather than
about anyone's discipline.

---

## 2. The sensor model

A spinning head carrying a fixed vertical array of emitters. Each emitter sits at a fixed
elevation, so as the head turns each one traces a **ring**. That is not drawn on; it is what
the device is.

| parameter | value | why |
|---|---|---|
| rings (emitters) | **32** | enough that rings are countable at working range and each still has an identity |
| elevation span | **−30.0° … +12.0°**, uniform | GUESS. A car unit (HDL-64: −24.8…+2.0) is wrong underground: in a 2.2–5 m drive you need the floor *close in* and the crown, not the horizon |
| elevation step | 1.355° | derived |
| azimuth steps / rev | **1024** (0.352°) | VLP-16 at 10 Hz is 0.2°; 0.35° keeps a ring a legible dotted line rather than a solid one |
| spin | **10 Hz** | ⇒ 327,680 shots/s, ~230,000 returns/s |
| range | **0.55 – 40 m** | the min is the hole at the origin; 40 m is a guess for a dusty heading |
| range noise | σ **20 mm**, Gaussian | VLP-16 is ±30 mm |
| per-emitter calibration | elevation ±0.08°, range ±15 mm, deterministic | real units ship a table of these; it is why rings on a flat floor are visibly *unevenly* spaced |
| beam divergence | 3 mrad full angle | ⇒ a footprint of 3 mm at 1 m, 120 mm at 40 m |
| head height | 0.90 m | GUESS |

**Intensity** is a reflectivity, not a radiance. `refl = albedo · cos(incidence)^0.75`, with
retroreflectors substituting a wide-angle response that does not fall off until ~70°.
Surface classes and their 905 nm reflectances (all GUESSES, ordered from published tables):

| class | albedo | in the fiction |
|---|---|---|
| rock | 0.30 | the cave |
| **wet rock / standing water** | **0.045** | a puddle is a **hole** in a real scan. It is here. |
| timber | 0.38 | the sets |
| steel | 0.55 | rail, pipe, crates, the machine |
| **retroreflector** | **6.0** | beacons, survey index plates, the machine's band — **clips the channel and blazes from anywhere** |

Rock albedo is **mottled** by a hash of the hit point at ~75 mm — real intensity images of
a rock face are visibly speckled, and the mottle is hashed off the *hit* rather than the
shot so that two passes over the same wall agree about its brightness. If they did not,
drift would be masked by noise instead of shown by it.

**Detection** is a link budget: `snr = refl · (12 m / r)²`, and a shot below threshold is a
dropout. This is what produces the 1/r² *thinning* on top of the 1/r² geometric density
falloff, and it is why the far half of a chamber is a scatter and the near half is a fabric.
Measured dropout: 28% standing in a chamber, 2% in a corridor.

**Occlusion is not modelled, it is raycast.** Every shot is a
`PhysicsDirectSpaceState3D.intersect_ray` against the real generated cave (seed 7: 251
stations, **75,932 triangles**, 4 chambers, topology hash `0x97de7a55`), with
`backface_collision = true` because a laser does not care which way a triangle was wound.
Shadows fall where they fall. Throughput: **~8.8 µs a ray** against that mesh from GDScript
(2.3 µs against a bare 20k-triangle plane), so a 32,768-shot revolution costs ~0.29 s to
bake and the 55-revolution walk costs ~19 s. It is a bake, not a per-frame cost.

The **skew is real too**: the head spins while the machine moves, so each azimuth column is
fired from its own interpolated pose and carries its own timestamp. That is free here and it
is one of the things that makes a moving-vehicle cloud look the way it does.

---

## 3. The mark: what makes it read as a scan

`lidar_point.gdshader`. Three changes, in the order they matter.

1. **Opaque, depth-tested, depth-writing.** A near return hides a far one. Every point-cloud
   viewer anyone actually works in does this; the first pass's additive x-ray does not. This
   is the single biggest cause of the "glowing mist" and the single cheapest fix. It also
   deletes two hacks: no sorting is needed (the depth buffer does it) and the **1/√N
   brightness compensation is gone** — there is no accumulation to blow out, so the view is
   self-exposing at any density and no frame in `shots/lidar/` has a hand-set gain.
2. **Small and sharp.** A hard-edged round dot, sized in *screen* space:
   `px = clamp(0.020 m · pixels_per_metre, 1.6, 3.6)`. Constant-ish, with a floor so a
   40 m return never vanishes and a cap so a 1 m return never becomes a blob. Structure
   comes from **where** the points are, not from how much they overlap. The oriented disc is
   still in the file (`f`) as a comparison and it is not the default.
3. **Coloured by a channel, not by a class.** Intensity (in the belief palette, and in the
   conventional blue→green→yellow→white ramp for comparison), height, ring index, epoch,
   range. One channel at a time.

Two additions that are not decoration:

- **A crop box** (`u_clip_lo/u_clip_hi`, world Y). An accumulated cloud of a *tube* cannot
  be read from outside — it is a solid mass. Every real tool has a crop box and the art
  vocabulary needs one. Shots 10 / 11 / 13 / 14 / 17 / 18 all use it to take the ceiling off.
- **Age still dims**, and retroreflectors are exempt from dimming. That is ART §8.2's "an
  old return is dimmer and stays where it was believed to be" surviving intact.

Tonemapping is **linear**, not AgX. The filmic roll-off existed to stop a million additive
discs summing past white; opaque points never accumulate, so the intensity ramp should
arrive on screen as it was authored.

---

## 4. Does ring structure make the fix legible in a still?

This is the question that matters most, and the first pass's honest answer was *no* — the
doubling as a single still was not legible to a cold viewer, because **two parallel banks of
returns is also what one passage looks like**, since a passage has two walls.

**The answer now: yes, and not for the reason I expected.**

Look at `13_fix_before.png` and `14_fix_after.png` — same camera, plan view of a corridor
with the ceiling cropped, **intensity colouring, no annotation of any kind**. Before: two
corridors. After: one. The pair is unarguable. But the *single* "before" frame is now
legible on its own, and the thing that carries it is not the rings:

> **The two records contain the same objects, in the same order, and both terminate at the
> same chamber mouth.** The same five boulders, the same row of timber sets, the same fan of
> occlusion shadows, the same chamber outline — twice, at a 7° angle to each other. A
> junction does not do that. That reading only exists at scanning density: it is *recognisable
> repeated content*, and 8,640 returns cannot carry recognisable content.

Ring structure does something different and also valuable, and `12_drift_close.png` is the
proof. At close range the two passes' ring bands **interleave** on the same wall — outbound
cyan, return gold — and you can see at a glance that the gold rings do not sit where the
cyan ones do. Misregistration of a regular pattern is visible at a fraction of the ring
pitch, so **rings make small drift visible where the previous representation needed metres.**

So the honest split:

- **Rings solve the small-drift and diagnostic problem.** Sub-metre disagreement is now
  visible, and `11_drift_two_passes.png` (epoch-coloured plan view) is a figure you could
  put in a paper.
- **Density solves the doubling problem.** The reason `13` reads without a caption is that
  the map now has *features*, not that it has rings.
- Both come from the same sensor change, so the recommendation is the same either way.

**The caveat I owe you:** I am not a cold viewer, and neither is anyone who has read this
document. `13` vs `14` should be put in front of someone who has not been told what the game
is. The first pass's conclusion — that *motion* is still the strongest carrier and a
two-second clip beats any still — has not been overturned; it has been made unnecessary
rather than wrong. The eased 0.7 s fix animation is still in the shader and still costs
nothing.

**The lie** (`17`/`18`) is a different and easier problem: an 11.0 m / +26° correction hinged
about an epoch anchor 40 m away tears the map into two overlapping copies of *everything*,
including the retroreflective plates, which duplicate as pairs of bright rectangles. It does
not need to be legible as "a lie"; it needs to be legible as "that was violent", and it is.

---

## 5. What is in `shots/lidar/`

Twenty frames, 1920×1080, ~10 MB. All belief-only except `03`.

| file | what |
|---|---|
| `01_single_sweep` | **one revolution** from a standing machine. Ground rings, wall bands, the hole at the origin, the machine's retro band clipping white. |
| `02_occlusion_shadows` | the same sweep from above. Every dark radial wedge is a shadow; count them against the objects. |
| `03_occlusion_with_truth` | the same, with the truth geometry under it, so a shadow can be checked against the thing that cast it. |
| `04_rings_countable` | 6 m from the sensor, coloured **by ring index**. Individual rings countable, constant azimuth pitch visible, rings climbing over a boulder. |
| `05_rings_plan` | plan view of one sweep. The textbook picture: concentric rings, nonlinear spacing, shadow wedges, minimum-range hole. |
| `06_intensity` | four revolutions, intensity in the belief palette. |
| `07_intensity_conventional` | the same data on the conventional scan ramp, for comparison. |
| `08_height` | the same data coloured by height. |
| `09_first_person` | 5.5 m from the machine at eye height — the `enter-agent-perception` register. |
| `10_accumulated_walk` | 40.9 m out and back, 55 revolutions, **1,530,334 returns**, ceiling cropped, height-coloured. |
| `11_drift_two_passes` | **the drift figure.** Outbound cyan, return gold, plan view. One corridor, two records, 7° apart. |
| `12_drift_close` | the same at 9 m, perspective. The two passes' **ring bands interleave and do not line up**. |
| `13_fix_before` / `14_fix_after` | **the fix pair, no annotation.** Two corridors, then one. |
| `15`/`16_fix_*_perspective` | the same moment from inside the corridor. |
| `17_lie_before` / `18_lie_after` | the rival's lie: 11.0 m, +26°, the map torn into two copies. |
| `19_toy_sensor_whole_walk` | the phase1 sensor's **entire 54.5-second traverse**: 3,882 dots. |
| `20_real_sensor_whole_walk` | the same walk, same camera, a real scanner. |

---

## 6. What the sensor decision is worth

`--stats` prints this. Both sensors go through the same raycaster against the same cave and
the same walk, so the only variable is the device.

| scene | sensor | returns | over | returns/s |
|---|---|---:|---:|---:|
| `toy_walk` | phase1 lidar: 1 plane, 90 rays/rev, 10.8 m, 1.5 s + near-field | **3,882** | 54.5 s | 71 |
| `walk` | 32 rings, 1024 az, sampled 1 rev/s | **1,530,334** | 54.5 s | 28,088 |
| `real_short` | the same, four consecutive revolutions | **114,997** | 0.4 s | 287,493 |
| `toy_stand` | phase1 lidar, standing, a **whole 8-minute match** | **8,640** | 480 s | 18 |
| `chamber1` | 32 rings, **one revolution** | **23,397** | 0.1 s | 233,970 |

Read the last two rows together:

> **One revolution of a real scanning sensor — one tenth of a second — returns 2.7× what the
> toy simulation's lidar returns in an entire eight-minute match.**

`19` and `20` are that comparison as pictures, same camera, same ground. The first pass
concluded "the renderer is not the constraint, the sensor is". This makes it concrete: the
renderer draws 1.53 M points in one draw call; the toy sensor cannot supply 4,000.

**The consequence nobody has costed yet.** At 10 Hz the real sensor produces ~230,000
returns *per second*, i.e. **~110 million over an eight-minute match**. That cannot be kept
and it does not need to be: the walk scene above is already a *sampled* cloud (one
revolution per second, not ten). So the sensor decision forces a **belief-map representation
decision** in Phase 3:

- the **live sweep** — one revolution, ~23,000 points — is what the machine "sees now";
- the **accumulated map** must be voxel-downsampled at source. At a 30 mm voxel, the 40 m
  drive above is ~500,000 points rather than 1.5 M, and a whole match is single-digit
  millions.

That is a `Belief` design question, not an art one, and it should be settled before anything
depends on the point count.

---

## 7. What ART-DIRECTION §8.2 should now say

§8.2 was written against a sparse range/bearing sensor. Most of its *intent* survives; three
of its *mechanisms* do not, and it is missing the one rule that turns out to matter most. My
recommendation, in the form of what to change:

**Add, at the top, the rule the section does not have:**

> **The cloud has ring structure, and the ring structure is the point.** The sensor is a
> spinning array of emitters at fixed elevations, so the returns lie on rings: concentric on
> the ground, banded on a wall, evenly pitched along each ring. Nothing in the presentation
> may destroy it — not a mark large enough to merge adjacent rings at working range, not
> randomised elevations, not a camera-facing sprite of fixed angular size, not additive
> accumulation. **A regular pattern is the only thing whose misalignment a human reads
> instantly, and this is a game about a machine whose estimate drifts and then jumps.**

**Replace "points are hits, not dots" with "a return is a point."** The intent — *encode
what the sensor saw from where it stood* — was right and is now carried by the ring geometry
instead of by the shape of each mark. The 40–50 mm oriented disc was solving the problem
that 5,663 sparse returns do not add up to a surface; 23,000 returns per revolution add up
to a surface on their own. Specify instead: **a hard-edged mark of near-constant screen size,
with a floor around 1.5 px and a cap around 4 px, opaque and depth-tested.** Delete the 45 mm
constant; it is not a length that exists. (A real footprint is range × 3 mrad: 3 mm at 1 m,
120 mm at 40 m. Neither the constant nor the first pass's 0.2–0.7 m ray-spacing footprint is
what should be drawn.)

**Reverse the blending rule.** §8.3's "belief must never be dimmed to let truth read" is
right and is untouched; but the *additive x-ray* the first pass inferred from it is wrong at
scanning density. State it directly: **the cloud is opaque and depth-tested; a near return
occludes a far one.** Belief still owns the frame — it is drawn over truth at low exposure —
but it is drawn as data, not as light.

**Retire "two classes and nothing else."** Sensed-versus-walked was an artefact of a sim in
which 82% of the map was near-field proximity hits. A scanning sensor has no such split.
Replace with: **colour carries exactly one channel at a time — intensity or height — with
ring index as a diagnostic mode.** The "no third colour" discipline survives; the taxonomy
does not.

**Retire "one confidence channel: alpha."** Alpha is unavailable once points are opaque, and
intensity is a better use of the channel than confidence: it is real, it is measured, and it
is what a lidar reader looks at first. Confidence and age ride on brightness. **Keep** "age
shows and the map is never re-registered" exactly as written — it is doing real work.

**Add: a sensor shadow is content.** Every object casts a clean wedge of *no data*, and the
voids are as characteristic as the points. **Nothing may ever be drawn into a sensor shadow**
— no fill, no interpolation, no decal, no "smoothing". §8.2's closing line gets a second and
sharper meaning: the darkness is not empty, and some of it is darkness the machine *knows
about*.

**Add: a crop box is part of the vocabulary.** An accumulated cloud of a tunnel is unreadable
from outside without one.

**Demote the floor decal.** It was "the only belief element with area". It no longer is — the
ground rings are a fabric with area of their own. Keep it as an option for the widest replay
camera; it is not load-bearing.

**Add a note on retroreflectors, because it is free world-building.** Beacons, survey index
plates and the machines' own bands should be retroreflective. They then clip the intensity
channel and blaze from anywhere in range, at any incidence — which means **the placed things
are the brightest things in the machine's own view of the world**, automatically, with no art
direction and no overlay. `01`, `05` and `18` all show it. This is the cheapest legibility
win in the document and it is physically true.

**Drop "emission ~0.03–0.06 linear"** as a rule. It was a density-compensation number for
additive overlap. Opaque points are drawn at their authored value and the frame is
self-exposing. Keep the *principle* (belief is dimmer than the lamp's darkest legible
surface) as an exposure target for the "both" mode, not as a per-point number.

**Unchanged and still right:** never smooth it into a mesh; the believed cave is a rug on the
floor of the real one; the shared datum is z = 0; truth is rendered and belief is drawn;
truth is the layer that gets turned down.

---

## 8. The cost of the change

- **~2,000 lines of new GDScript and GLSL** in this directory: `lidar_geo.gd` 630 (geometry
  and props, ~180 of which is the cave-spike sweep), `lidar_root.gd` 1,009 (run, drift, fix,
  camera, shots), `lidar_scan.gd` 203 (the sensor — this is the file that matters),
  `lidar_point.gdshader` 156, `boot.gd` 15. Plus `topology.gd` copied verbatim, 428.
- **The renderer change is the shader alone, 156 lines**, and it *removed* two mechanisms
  (the 1/√N gain and the 1/√N beam width). The MultiMesh path, the buffer layout and the
  scrub are untouched.
- **Bake, not frame cost.** One revolution ≈ 0.29 s of GDScript raycasting; the 55-revolution
  walk ≈ 19 s plus ~5 s to place 1.5 M points. Both are one-off. In Phase 3 this is a
  GDExtension or the sim's own job and neither is in GDScript.
- **No new data files.** The first pass shipped a ~230 MB `data/` directory of exported
  buffers; this one generates everything at load.
- **Performance was not measured and the numbers from the first pass should not be assumed
  to transfer.** Another agent had a Godot process on this GPU during part of this session
  (`tasklist` found one mid-session; the final capture ran with none), so no frame
  time in this document. What *is* safe to say: 1,530,334 opaque points render in **one draw
  call**, and the first pass's finding that the ceiling is **fill rate, not instances** now
  cuts the other way — a 2 px opaque dot covers ~3 px² where a 0.2–0.9 m additive disc
  covered hundreds, so the fill bill should be far smaller. **Re-measure on a quiet machine
  before quoting a ceiling.**

---

## 9. What is still wrong

1. **The chamber floor's normals had to be forced up by hand.** `lidar_geo.up_ranges` states
   the normal for the chamber floor fan rather than deriving it from the winding, because
   getting one flat fan's winding to satisfy the renderer, the physics server and my own
   normal accumulator at once cost more than it was worth in a spike. It is a wart.
2. **The truth overlay carries a small self-emission** (0.42 × exposure) so that a surface
   the two survey directionals do not reach still reads. Without it a lit-shading gap in the
   *truth* layer looks like a *sensor* void, which is the one confusion this overlay exists
   to prevent. It is a diagnostic hack, not an art proposal.
3. **The walk is sampled at 1 revolution per second, not 10.** At full rate a 40 m traverse
   is 15 M returns. See §6 — this is a real Phase 3 decision, not a spike shortcut, but the
   spike does not model what full-rate accumulation looks like (the ground rings would smear
   into a continuous fabric and the wall bands would stay).
4. **Drift is planar.** Height is measured, not dead-reckoned, as in phase1. Whether Phase 3
   agrees is a sim question.
5. **No multi-return, no dust, no rain.** Real units report 2–3 returns per shot and airborne
   particulate produces a characteristic near-field haze. Underground, in a place the fiction
   describes as silty, that is not a detail — **a dust cloud that returns the beam is a
   sensor failure mode with gameplay in it** and it is not modelled here.
6. **No second machine.** "Two machines that disagree about where the same wall is" is still
   the picture nobody has drawn, and it is now much easier than it was.
7. **The `--old` path still needs `data/`**, which is gitignored and must be rebuilt with
   `export_belief.py` / `build_buffers.py` before that flag works.
8. **`shots/lidar/` is ~10 MB and is not gitignored**, unlike the first pass's frames. That
   is a deliberate non-decision: they are the evidence for this pass and hiding them from a
   clone seemed worse than the bytes. Change it if you disagree.

---

## 10. Every guess, in one place

1. **32 rings over −30.0° … +12.0°.** The count, the span and the uniform spacing are all
   mine. Real units are non-uniform (VLP-32C packs beams near the horizon). Reasoned from
   "underground you need the near floor and the crown, not the horizon"; no source.
2. **1024 azimuth steps and 10 Hz.** Bracketed by real units (VLP-16 is 1800 at 10 Hz;
   HDL-64 is ~2000) but chosen because 0.35° keeps a ring a *dotted* line on screen.
3. **Range 0.55 – 40 m, σ 20 mm, 3 mrad divergence.** The minimum is what makes the hole at
   the origin; 40 m is a guess for a dusty heading.
4. **Per-emitter calibration ±0.08° and ±15 mm.** Real, in kind; the magnitudes are mine.
5. **Sensor head at 0.90 m.** The first pass guessed 0.45 m. Raised because a higher head
   lays more visible ground rings, which is also why cars put the unit on the roof.
6. **Every reflectance in the surface table**, and the retro value of 6.0 in particular — it
   is deliberately > 1 so that it clips the channel.
7. **The link budget** `snr = refl · (12 m / r)²` with a 0.55 threshold. The 12 m reference
   range was tuned by eye against the frames until a far chamber wall thinned the way a real
   one does.
8. **Rock reflectance mottling**, 0.52–1.44 × albedo, hashed at 75 mm.
9. **Receiver noise ±9% on intensity.**
10. **Screen-space point sizing**: 0.020 m at range, floored at 1.6 px, capped at 3.6 px.
    Chosen by eye against the frames.
11. **All five colour ramps**, including the decision to make the default intensity ramp
    palette-legal (dark teal → SENSED → white) and to keep the conventional
    blue→green→yellow→white only as a comparison mode.
12. **Age ramps to 0.42 over 90 s**, and retroreflectors floor at 0.85. §8.2 gives the
    principle, not the curve. Every drift/fix/lie frame here sets `age_floor = 1.0` — i.e.
    **the doubling in `13` is carried by shape alone, not by the age difference**, which is
    what the first pass had to lean on.
13. **The walk is 40.9 m each way at 1.5 m/s, sampled one revolution per second.**
14. **The fix schedule**: one honest correction at the turn (which is what makes the outbound
    and return legs different epochs, and therefore what makes a later fix able to close the
    doubling at all — see NOTES §5), one at the end. The lie is 11.0 m at +26°; phase1's own
    `SPOOF_LIE_CELLS` is 34 cells (20.4 m), so this is conservative.
15. **The dead-reckoning model is phase1's** (`DR_HEADING_BIAS_DEG_PER_CELL = 0.11` etc.,
    quoted in `lidar_root.gd`) — *not* a guess — but the honest fix residual (0.10 m, 0.4°)
    and the choice to hinge a correction about the previous epoch's believed position are
    mine, following `pose_correction.py`.
16. **Chamber sizing**: the largest chamber in the stretch is inflated to ≥ 9.5 m radius so a
    standing sensor lays more than a dozen complete ground rings; the others are shrunk to
    the cave spike's own size so the drive is not swallowed. Both multipliers are mine and
    both exist to make the test possible, not because the cave should look like that.
17. **Chamber floor relief**: 90 mm low-frequency + 25 mm fine. Enough that a ground ring
    wobbles like a real one and not so much that ring structure dies.
18. **The prop set** (5 boulders, a pillar, crates, a charging mast, a machine, a spoil heap,
    a water disc per chamber; timber sets, rail, pipe and beacon plates in the corridor) was
    chosen for one reason: each casts a shadow a viewer can check against the thing that cast
    it. It is not an art proposal.
19. **The truth overlay's survey fill** — two shadowless directionals at 1.6 and 0.5 scaled
    by exposure, plus the self-emission in §9.2. `PROCEDURAL-AND-GODOT` §5.4(a) asks for a
    shadowless desaturated fill; the numbers are mine.
20. **`length_cells = 170`, seed 7.** Long enough that the longest chamber-free run supports a
    64-cell out-and-back.
