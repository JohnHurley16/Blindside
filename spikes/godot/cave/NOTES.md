# Spike — procedural cave, in Godot, at the density the designer asked for

**Question this spike exists to answer.** Not "can a cave be generated" — Phase 1 already
generates one. The question is the one in DESIGN-PRINCIPLES §4 and §5 together:

> can a rule-generated cave carry detail at three scales at once, in both technological
> registers, and still run at frame rate in Godot 4?

**Answer, honestly.** Yes for the performance, with a lot of headroom. Partly for the
density — the three scales are all present and all generated, but the *material* read at
lamp distance is the weakest part, and the two-register collision needs one more thing that
this spike does not have (see §7). Nothing here is a look that is approved; it is a pipeline
that is proved.

Nothing in this directory is imported by `phase1/` or `phase2/`, and nothing outside
`spikes/godot/cave/` was modified.

> **Superseded in part, 2026-09-09.** The materials and the underfoot scale were rebuilt for
> DESIGN-PRINCIPLES §6 ("it needs to look photoreal"). **`PHOTOREAL.md` is the current record
> for §4 (technique), §5 (measurements) and §7 (what did not hit the bar).** Everything in
> this file about the topology/dressing seam, the generation rules and the kit of parts still
> stands. Three findings in `PHOTOREAL.md` §1 are bugs that were in the build this document
> describes, so its screenshots and its §7 conclusions about the underfoot scale should be
> read as measuring those bugs rather than the design.

---

## 1. How to run it

```
GODOT="C:/Users/jackh/Downloads/Godot_v4.7.2-stable_win64.exe/Godot_v4.7.2-stable_win64.exe"

# the walk, the measurements, and the twelve screenshots  (~100 s)
"$GODOT" --path spikes/godot/cave --resolution 1280x720

# just the screenshots (~25 s)
"$GODOT" --path spikes/godot/cave --resolution 1280x720 -- --shotsonly

# other flags: --seed=N --len=CELLS --speed=M_PER_S --noshadow --nofog --noprops
#              --novis --walkonly --stay
./check.sh                 # GDScript parse gate, headless
./shadercheck.sh           # SHADER compile gate -- check.sh never compiles one
./ablate.sh                # the performance ablation table in §5.3
./scale.sh                 # the length-scaling table in §5.4
python lumcheck.py         # the ART-DIRECTION §2.9 exposure contract, linearised
```

**Resolution.** The desktop is a 1920×1080 panel at 125% Windows scaling, so a 1920×1080
*window* cannot exist in logical coordinates. The scene therefore renders into a
`SubViewport` fixed at exactly 1920×1080 inside a smaller window. Every number and every PNG
below is a true 1080p render; the window is only a way to look at it.

**GPU.** `RenderingServer.get_video_adapter_name()` reports
**NVIDIA GeForce RTX 3080 Laptop GPU**, Vulkan 1.4.312, Forward+, device #0. It is not the
Intel UHD. Every number below is on the NVIDIA.

| file | what it is |
|---|---|
| `topology.gd` | **the deterministic layer.** Integer only. This is `blindside-gen`. |
| `dressing.gd` | **the client layer.** Geometry, kit, scatter, materials. |
| `cave_root.gd` | scene, camera walk, lamp, metrics, screenshots |
| `rock.gdshader` | the one rock material, four scalars, world-space, no texture |
| `kit.gdshader` | one shader, six parameter sets: iron / steel / timber / porcelain / composite / aluminium |
| `stone.gdshader` | loose rock and spoil — the cheap shader, tens of thousands of instances |
| `lumcheck.py` | the exposure contract, computed on **linearised** luminance |
| `metrics.csv` | per-frame log of the walk |
| `summary.txt`, `ablation.txt`, `scaling.txt` | the numbers quoted in §5 |
| `shots/` | twelve 1920×1080 PNGs |

---

## 2. The seam, and exactly where it sits

`DESIGN-PRINCIPLES §5` requires generation to split in two. It does, into two files, and the
line is this:

> **Topology decides what is there. Dressing decides what it looks like. The interface is a
> blob of integers, and it only travels one way.**

### 2.1 What is above the line (`topology.gd`)

Obeys `DETERMINISM.md` as written for a constrained crate:

* **No float appears anywhere in the file.** Every length is an integer in **millimetres**;
  every probability is an integer percent; every ratio is integer arithmetic with the
  multiply before the divide.
* **No dictionary is iterated.** Every loop is `for i in range(...)` or over a
  `PackedInt32Array` in index order.
* **No engine RNG, no `Time`, no node lookups.** The only source of variety is
  `draw(purpose, a, b) -> u32`, a counter-based bit-mixing hash seeded on the cave seed.
  It is stateless, so **the order of calls cannot change any result** — which is
  `DETERMINISM.md` rule 4, and it is the property that makes the file portable to Rust
  without re-deriving anything.
* **The output is hashable.** `content_hash()` is FNV-1a over the whole grid and every
  integer field of every station, in index order. Seed 7 at 240 cells gives
  **`0xAD83E3ED`**, identically on every run. That is what would go into the replay.

Verified, not asserted:

```
seed 7     0xAD83E3ED   351 stations     seed 7   0xAD83E3ED   (again)
seed 7     0xAD83E3ED   (again)          seed 42  0xCFDD10D3   337 stations
                                         seed 1234 0x89A28771  336 stations
```

and an audit of the file for `float`, `randf`, `randi`, `Time.`, `sin`, `cos`, `sqrt` and
any decimal literal returns only comments and `1 << n` bit-shift constants.

### 2.2 What crosses the line

Exactly this, and nothing else:

```
w_cells, h_cells                 int
grid_state[]                     u8   per cell: 0 rock / 1 dry / 2 flooded
grid_station[]                   i32  per cell: owning station index, or -1
stations[]                       16 x i32 per station:
      x, y            cell coordinates
      floor_mm        signed mm above datum
      width           0 crawl / 1 narrow / 2 passage / 3 hall
      worked          0..255, how much the industry touched it
      state           dry / flooded
      water_mm        water surface, mm, or -1000000
      works           bitfield, 17 bits (rail, sets, bolt line, Bus, gutter, pipe,
                      tray, spoil, mesh, launder, duct, beacon, plate, failed set,
                      standing water, plant, kit)
      depth           cells from the shaft along the graph
      integ           structural integrity 0..255
      wet             0..255
      fracture        3..14
      bedding         4..35   (x10)
      kind            drive / chamber / junction / shaft
      edge            0 = main drive, 1.. = crosscuts
      discovery       0, or a discovery id
edges[]                          PackedInt32Array of station ids, one per passage
chambers[]                       rows of 5: x, y, r_cells, is_plant, station id
junctions[]                      station ids
water_datum_mm                   int
```

That is a JSON document. It is what would come back over a GDExtension boundary from Rust.

### 2.3 What never crosses back

Nothing. `dressing.gd` holds a reference to the `CaveTopology` object and **never assigns to
it**. Every float, every `FastNoiseLite` call, every mesh, every prop transform, every
material and every particle is downstream of the blob and invisible to it.

The two things that are *deliberately* topology and could naively have been dressing, because
the simulation needs them:

* **the works bitfield.** Whether a length of drive has rails, standing sets, a live Bus
  conductor or one of the player's beacons is not decoration — it is trammable ground, a
  pinched section, a hazard, and a Fix source. So it is decided above the line and hashed.
* **`floor_mm` and the water datum.** Where the sump is has to be identical on every client.
  One integer bowl in the floor profile decides it and nothing else does.

And the one thing that is deliberately dressing and could naively have been topology:

* **the exact position of every rock bolt, stone, drip and rust streak.** ~33,500 prop
  instances per 144 m stretch. None of them is in the hash. If a client rolls a stone
  differently it changes nothing that the simulation can observe.

**Where this spike is weaker than the real thing will need to be.** The visual shell is swept
from a *smoothed* (Catmull-Rom) centreline while the sim's collision would come from the
integer cell grid. They agree to within roughly a cell, not exactly. In the real build the
walkable surface has to be derived from the grid, or the grid from the mesh — see risk 1 in
§8.

---

## 3. Every generation rule, in enough detail to port

All of §3.1 is integer arithmetic on millimetres and percents. `n` is the stretch length in
cells; a cell is **600 mm** (inherited from `phase1`).

### 3.1 Topology

**R0 — randomness.** `draw(purpose, a, b)`: xor the seed with three odd-constant multiplies,
then three xorshift/multiply rounds, masked to 32 bits. `draw_range(p,a,b,lo,hi)` is
`lo + draw % (hi-lo+1)`. Each rule uses its own `purpose` constant so rules cannot alias.

**R1 — the spine.** Start at `y = h/2`. Every 4 cells step `y` by `draw ∈ {-1,0,+1}`, forced
back toward the centre when `|y - h/2| > 7`. Station `i` sits at cell `(i+7, y)`.

**R2 — the floor, and therefore the sump.** `floor_mm = -(2·i)`, plus one bowl:
centre at `i = 0.58n`, half-width `max(6, n/11)`, triangular, 1500 mm deep at the centre.
*Nothing else in the generator decides where water is.*

**R3 — width class runs.** A class is held for `draw ∈ [6,22]` cells, then re-rolled. The
mix depends on depth as a percentage of the stretch:

| depth | crawl | narrow | passage | hall |
|---|---|---|---|---|
| < 22 % | 16 % | 39 % | 45 % | — |
| 22–78 % | — | 20 % | 68 % | 12 % |
| > 78 % | — | — | 72 % | 28 % |

Half-width / height per class, mm: crawl 750/1300, narrow 1050/2200, passage 1350/3200,
hall 1950/5000. Rasterisation radius in cells: 1, 2, 2, 3.

**R4 — `worked`, the depth gauge.** As a function of `p = 1000·i/n`:
`p<130 → 0`; `130..300 → 0..195`; `300..640 → 195..230`; `640..1000 → 230..255`.
That is ART-DIRECTION §7's "worked climbs with depth": karst → cut drive → machine ground.

**R5 — the standard section.** `worked > 128` forces `width ≥ passage`. The industry drove
to a module (§3.3 of the art direction puts the horseshoe at 2.4 × 2.4 m), so a driven length
is never narrower than one. This single rule is what makes a driven passage read as *built*
rather than as a hole that happens to have rails in it, and it fixed most of the framing
problems in the first four passes.

**R6 — rock type.** `fracture` (3..14) and `bedding` (4..35, ×10) are drawn per **9-cell
block**, not per cell. Per-cell would make the wall boil along the passage.

**R7 — chambers.** At 17 %, 44 %, 71 % and 92 % of the stretch, ±3 cells. Radius `draw ∈
[5,9]` cells. Forced to `hall`; the two neighbours either side widened to hall, the next
to passage. The 92 % one is the plant chamber and gets `WK_PLANT`.
(ART-DIRECTION §5.5 requires a chamber holding plant to be taller than the passages reaching
it; forcing `hall` is how that is enforced here.)

**R8 — water and wetness.** `water_datum = lowest_floor + 950 mm`. A station with
`floor_mm < datum` is flooded, `wet = 255`. Otherwise
`wet = max(255 − above_mm/4, 25 + 95·depth/n)`, clamped — that is "wetter near the line, and
wetter with depth". `wet > 140` gives a 50 % chance of standing water on the floor.

**R9 — crosscuts.** Starting at cell 18, one every `draw ∈ [26,40]` cells, alternating side.
Length `draw ∈ [10,20]` cells, one width class narrower than the parent (and one narrower
again for the last two cells — a crosscut peters out), `worked` reduced by `draw ∈ [20,90]`,
floor wandering ±8 mm/cell. The parent station is marked a **junction**.

**R10 — the works.** Thresholds on `worked` (w), integrity (g), depth percent (d) and the
1.2 m module (`along % 2 == 0`):

| flag | rule | register |
|---|---|---|
| rail | `w>90`, dry, main drive only | inherited |
| sets | `w>55` and `along%2==0` (the 1.2 m module) | inherited |
| set failed | that set, `g<95`, 32 % | inherited |
| bolt line | `w>120` | inherited |
| gutter | `w>100` | inherited |
| pipe | `w>140`, 72 % | inherited |
| Bus | `w>205` | inherited |
| launder | `w>215`, 45 % | inherited |
| ground mesh | `g<115` | inherited |
| spoil heap | `w>70`, 24 % | inherited |
| survey plate | `w>110` and `along%12==3` | inherited |
| plant | chamber and `w>195` | inherited |
| **cable tray** | **requires a bolt line to clip to**, then `(58 − d/3) %` | **brought** |
| **ducting** | `w>150`, `(32 − d/5) %` | **brought** |
| **beacon** | every `13 + 27d/100` cells, and at junctions while `d<75` | **brought** |
| **loose kit** | `(17 − d/8) %` | **brought** |

Two things worth naming. The tray rule *depends on an inherited feature* — the composite tray
can only exist where there is already a rusted bracket line to clip it over. That is the
design principle "the new bolted onto the old" written as a placement rule rather than as an
instruction to an artist. And every brought probability **falls with depth**: the beacon chain
thins, the kit runs out, and the deep ground is all iron. That is ART-DIRECTION §7 as a
number.

**R11 — rasterise.** Integer disc stamp per station, exactly `phase1`'s rule: open if
`dx² + dy² ≤ r²`. Chamber radius +3.

**R12 — discoveries.** A chamber past 60 % depth carries a discovery id.
(DESIGN-PRINCIPLES §2: the cool things are found by depth.)

### 3.2 Dressing

**Shell.** For each edge, sample the station polyline with Catmull-Rom at 3 steps per station
(≈0.2 m), build a 30-vertex ring at each step, quad-strip between rings, normals flipped
inward toward the ring centre.

The ring profile is **two profiles interpolated on `worked`** (ART-DIRECTION §3.4):

* *natural* — floor from centre to `0.92·hw` for the first 22 % of the half-outline, then an
  elliptical quarter with a `1 + 0.22·sin(2a)` bulge to the crown. No straight line anywhere.
* *horseshoe* — floor to `hw` (with a 300 × 90 mm gutter dip on one side), vertical leg to
  `ht − R`, then a quarter arch of radius `R = min(hw, 0.62·ht)`.

Then every vertex is pushed along its outward normal by
`noise_lo(p) · amp + noise(2.2p) · 0.45 amp`, where `amp = lerp(0.42, 0.085, worked)` and is
masked to zero at the floor. That is the silhouette break: buttresses and spalled backs in
natural ground, a nearly-true wall in driven ground.

**The four scalars reach the shader as vertex attributes, not as textures:**

```
COLOR.rgba = wet, worked, dark(depth), iron-proximity
UV.xy      = axial distance along the passage (m), perimeter position (0..1)
UV2.x      = height above the local waterline (m)
UV2.y      = packed rock type: floor(fracture01*31)*32 + floor(bedding01*31)
```

`UV.x` and `UV.y` are not a texture parameterisation — nothing is sampled with them. They are
the two coordinates the *shot-hole scallops* need: 340 mm around the perimeter, in 1.6 m
rounds, each round's phase offset from the last, so a player can count how many blasts made
the passage (ART-DIRECTION §3.3).

**Chambers** are a separate noise-displaced hemisphere (26 × 9) with a floor fan, dropped over
the station and left to interpenetrate the sweep. In the dark the seam is never visible; in
daylight it would be. Flagged in §7.

**Kit of parts.** 47 meshes, all built in code from `BoxMesh` / `CylinderMesh` / `SphereMesh`
and a distorted, facet-quantised sphere for broken rock. Colour is baked per-part into vertex
colours, so one prop can be rusted web and mirror-bright rail head **inside a single draw
call**. Nothing is imported. There is no `.glb`, no `.obj`, no image file in this directory.

Inherited: rail, sleeper, ballast, timber set, failed set, steel arch, lagging, rock bolt and
plate, ground-support mesh panel, cast pipe with flanges, wall bracket, timber launder,
porcelain insulator, Bus conductor, cast survey plate, drum, chain coil, spoil heap, roof
pendant, flowstone boss, derailed mine tub, pump with flywheel and pipework, breakdown block,
loose stone (4 sizes), spall flake (3), grit (2), silt fan, litter, puddle.

Brought: composite cable tray with clip bracket and three cables, extruded ventilation duct
with printed hangers, the player's beacon (machined tripod, labelled body, one warm pilot),
a modular case, a printed bracket holding an instrument, a charging mast.

**Placement**, per station, all from the works bitfield and the four scalars. Underfoot:
`14 + 34(1 − 0.62·worked) + 24(1 − integ)` stones, 22 grit, 4–13 spall flakes where the
ground is bad, 3 silt fans where it is wet, litter where the industry went, 26 ballast stones
between the rails. Lamp distance: bolts at the springing on the 1.2 m module plus a crown
bolt in wide sections, mesh panels on bad ground, the pipe run on the haunch at 1.62 m, the
tray at 1.86 m with a bracket every third station, a survey plate at 1.40 m, puddles,
a 6-link catenary of sagging cable between consecutive bolt stations. Silhouette: sets or
steel arches on the module, lagging on one side of a set in bad ground, spoil heaps, breakdown
blocks, roof pendants and flowstone in natural ground, ducting on the crown, the Bus and its
insulators every 4 stations, the pump in the plant chamber.

**Chunking.** Everything is bucketed by an **8 m world grid** — 49 chunks for a 144 m stretch.
Each chunk gets one `MeshInstance3D` for its slice of shell and up to ~20
`MultiMeshInstance3D`, one per prop type present.

---

## 4. Technique, and why each one

**Swept profile, not marching cubes, not a kit of tunnel modules.**
The topology is a graph of passages with a width class, so a swept profile is the shape the
data already has. It buys three things marching cubes would not: the 1.2 m module and the
horseshoe section fall out of the profile function for free; the sweep hands the shader an
*axial* and a *perimeter* coordinate, which is what the drill rounds and the scallops need;
and the whole 144 m shell is **64,676 triangles**, which is nothing. A density field would
have needed its own resolution decision, would have lost the module, and would have given no
natural place to hang the works. A kit of pre-made tunnel modules was never on the table —
DESIGN-PRINCIPLES §5 rules out anything that needs a modeller.

**`MultiMeshInstance3D` for everything instanced, with the buffer written directly.**
33,470 instances live in 985 multimeshes and cost **~320 draw calls**. The transforms are
written as a flat `PackedFloat32Array` (12 floats per instance, row-major) straight into
`MultiMesh.buffer` rather than through `set_instance_transform`, which is roughly an order of
magnitude faster to build.

**No MultiMesh instance colours.** In Godot 4 an instance colour *replaces* the mesh's own
vertex colours. The first dense pass set them to near-white for per-instance variation and
flattened every kit part to white concrete. Per-instance variation now comes from the wear
shader sampling world position, which is better anyway: two identical timber sets 1.2 m apart
are no longer twins, and the variation follows gravity rather than an index.

**Procedural shaders, world-space, no UVs, no textures.**
ART-DIRECTION §3.2 is categorical: a generated cave cannot be unwrapped, so world-space
procedural is not an optimisation, it is the only option. The rock shader evaluates a warped
voronoi for the jointing and 6 octaves of value noise for the relief, and perturbs the normal
by central differences on that height field, with an LOD term that drops the expensive octaves
past ~6 m. There is not one image file in this spike.

**Tangent-free normals.** Generated meshes have no UVs and therefore no tangents, so
`NORMAL_MAP` is evaluated in a garbage basis — this produced a blocky light/dark mosaic over
every prop that survived three passes before I found it. All three shaders now perturb the
world normal directly by finite differences and convert with `VIEW_MATRIX`.

**One integer hash for all three shaders.** The `fract(sin(dot(...)))` family produced a
visible square lattice at high frequency. Replaced with a 3-round integer bit-mix on
`uvec3`.

**Visibility ranges, not mesh LODs, not occlusion culling.**
Because the game is *one lamp in the dark*, a hard cutoff is invisible: past the lamp there is
nothing to pop. Each family gets its own range — shell 44 m, silhouette props 30 m, lamp-scale
props 19 m, underfoot scatter 12 m — with fade **disabled**, because dithered fade would need
transparency and cost more than it saves. Godot's automatic mesh LOD is not used (these meshes
are already 40–400 triangles); `OccluderInstance3D` is not used either, and is the obvious
next lever (§7).

**Volumetric fog for the resting silt**, at density 0.011, anisotropy 0.55, albedo
(0.85, 0.86, 0.90) — ART-DIRECTION §2.6's numbers, entered directly.

**GPU particles for drips**: 22 emitters placed where `wet > 130`, each with a 14 m visibility
range so only the one you are standing under is simulating.

**Decals: not used.** Wheel and foot tracks are the one item on the designer's underfoot list
that this spike does not have. A Godot `Decal` needs a texture, and the honest way to do it
here is a procedurally-generated `ImageTexture` — cheap, but it was below the line on time.

**The lamp.** One `SpotLight3D`, white `(1.00, 0.98, 0.95)` (ART-DIRECTION §2.5 — never
team-tinted, never cyan), 54° cone, tilted 11° down, range 26 m, shadows on.
`spot_attenuation = 2.0`: Godot's attenuation parameter is the **decay exponent of a windowed
inverse square**, so the default 1.0 is `1/d` and lights the whole 26 m evenly. That one value
was the difference between a lit level and a carried lamp. World background strength is zero,
ambient light source is **disabled**, tonemap is **AgX**. The only other lights in the world
are the players' beacon pilots — 31 of them, warm amber, `omni_range` 2.6 m, no shadows,
distance-faded out at 16 m.

---

## 5. Measurements

All at **1920×1080**, NVIDIA GeForce RTX 3080 Laptop GPU, Godot 4.7.2 Forward+, seed 7,
240 cells = **144 m** of cave, camera walking the drive at **1.7 m/s** (a machine's pace) with
the lamp on and shadows and volumetric fog enabled. `metrics.csv` is the per-frame log.

### 5.1 The scene

| | |
|---|---|
| topology content hash | `0xAD83E3ED` (identical every run) |
| open cells | 1,954 of 19,304 |
| stations / edges / chambers / junctions | 351 / 8 / 4 / 7 |
| chunks | 49 |
| shell triangles | 64,676 |
| **prop instances** | **33,470** in 985 MultiMeshInstance3D, from 47 kit meshes |
| beacon pilot lights | 31 |
| path walked | 153.8 m |

### 5.2 Frame rate, sustained, while walking

| | |
|---|---|
| **fps mean / p50** | **107 / 105** |
| **fps worst 5 % (p05)** | **68** |
| **fps minimum over the whole walk** | **54** |
| GPU frame time p50 / p95 / max | **8.75 ms / 13.43 ms** / 94 ms |
| CPU process time p50 / p95 | 10.59 ms / 68.8 ms |
| draw calls p50 / p95 / max | **317 / 393 / 423** |
| primitives p50 / p95 / max | **312,062 / 424,702 / 448,088** |
| video memory | **178 MB** |
| generation, this stretch | topology **3.9 ms**, dressing **539 ms** |

**It hits 60 fps and stays there.** The median frame is 105 fps and the worst 5 % are still
68. There are a handful of single-frame hitches — the worst frame of the 154 m walk was
**54 fps**, and the CPU p95 of 68 ms against a p50 of 10.6 ms says those are a few outliers,
not a sustained cost. They are chunk-entry frames: the first time a chunk becomes visible its
pipelines compile. Godot's pipeline pre-compilation would remove them and this spike does not
do it.

**Run-to-run spread, stated plainly.** Across six runs of the same build the p50 ranged
**85–114 fps**. This is a laptop: the CPU sits at its 2.30 GHz base with no turbo
headroom reported, and the figure depends on how hot it already is. One run was discarded
entirely because another agent's Godot benchmark (`--mode=bench --secs=40`) was running on the
same GPU at the time and dragged the p05 to 13 fps. The table above is a clean run; treat 97
as the middle of a 85–114 band, not as a precise number.

### 5.3 Ablation — where the frame actually goes

Same walk, 5.0 m/s to keep each run short, so the absolute fps is lower than §5.2 across the
board. `ablation.txt`.

| build | fps p50 | GPU p50 | draw calls | primitives | VRAM |
|---|---|---|---|---|---|
| **baseline** | **85** | 10.27 ms | 328 | 326,510 | 178 MB |
| no visibility ranges | 82 | 10.60 ms | **753** | **1,064,228** | 181 MB |
| **no props at all** (shell only) | **63** | **14.73 ms** | 24 | 35,078 | 179 MB |
| no lamp shadows | 88 | 9.76 ms | 156 | 168,248 | 147 MB |
| no volumetric fog | 87 | 9.59 ms | 321 | 321,018 | 167 MB |
| neither shadows nor fog | 94 | 9.05 ms | 156 | 168,500 | 136 MB |

Three findings, and the first one is the important one:

1. **The empty corridor is more expensive than the dense one.** 63 fps with the props hidden
   against 85 fps with 33,470 of them. The frame is *fragment-bound on the rock shader*, and
   the props are nearly free because they are instanced **and because they occlude the
   expensive surface**. This is the single most useful number in the spike: at this density
   the budget is being spent on the wall material, not on the amount of stuff, so **there is
   room for considerably more stuff**.
2. **Shadows cost about 3 fps and 31 MB**, and they halve the draw calls when off because the
   shadow pass re-draws the geometry. Cheap for what they give — every prop in the pool casts.
3. **Visibility ranges buy 2.3× the draw calls and 3.3× the triangles for ~3 fps at 144 m.**
   At this length they are insurance rather than necessity. They become necessary at real cave
   size — see the next table, where they are the reason the frame cost does not grow.

### 5.4 Generation time, and how it scales

`scale.sh`, same seed, five lengths. Generation is measured once at load; fps is a short walk
at the same 1080p.

| stretch | stations | shell tris | prop instances | multimeshes | topology | dressing | fps p50 |
|---|---|---|---|---|---|---|---|
| 36 m (60 cells) | 80 | 16,256 | 7,696 | 253 | 1.6 ms | 425 ms | 73 |
| 72 m (120) | 165 | 31,436 | 15,883 | 514 | 2.8 ms | 591 ms | 66 |
| **144 m (240)** | 351 | 64,676 | 33,526 | 973 | **5.2 ms** | **694 ms** | 86 |
| 288 m (480) | 691 | 125,456 | 65,310 | 1,742 | 8.6 ms | 888 ms | 92 |
| 576 m (960) | 1,386 | 249,776 | 128,557 | 3,624 | 18.3 ms | 1,453 ms | 96 |

* **Topology is linear and trivially cheap: ~0.019 ms per cell, 0.032 ms per metre.** 576 m of
  cave costs 18 ms *in GDScript*. In Rust with fixed-point it is not a cost at all.
* **Dressing has a fixed cost of about 360 ms — building the 47 kit meshes — plus ~1.9 ms per
  metre of cave.** So the 144 m stretch is 531–694 ms depending on run, of which more than
  half is the kit. In a real build the kit is built once at load, not per match, which turns
  the per-match cost into ~1.9 ms/m: **half a second for a 250 m raid**.
* **Frame rate is flat with cave length** (73–96 fps from 36 m to 576 m). That is the chunking
  and the visibility ranges working: what is on screen does not depend on how much cave exists
  behind you. The 36 m and 72 m entries being *slower* is the §5.3 finding again — a shorter
  cave means more of the frame is bare wall.

A note on the 531 ms figure: the first implementation took **1,311 ms** for the same content.
The cause was GDScript's copy-on-write on `Packed*` arrays — holding one in a local variable
while appending copies the entire array on every call, which made the shell build quadratic.
Keeping the arrays as members of a small class and only ever mutating them from inside it
removed 60 % of generation time. Worth knowing before anyone writes the streaming version.

### 5.5 The exposure contract

`lumcheck.py` implements ART-DIRECTION §2.9 on **linearised** luminance (the doc is explicit
that three of the four earlier passes did this on gamma-encoded values and were wrong by a
large factor). Targets for a lamp frame: blown ≤ 3 %, legible 3–20 %, true black ≥ 70 %.

**Nine of the twelve frames pass** (`05_two_registers` now passes too). The three that do not:

* `08_waterline` and `11_set_line` — 64–70 % true black against a 70 % floor. Both are frames
  where the lamp is close to a wet floor that returns it; arguably the contract's floor is
  the thing that is wrong for a wet frame rather than the frame.
* `12_crown` — 32 % legible against a 20 % ceiling, looking up into a crown 1.5 m away. That
  one is a genuine near-field blow-out.

None of them is a leak: ambient is disabled and world background strength is 0, so every lit
pixel in every frame is traceable to the lamp or to a beacon pilot.

---

## 6. The screenshots

`spikes/godot/cave/shots/`, all 1920×1080, all captured in code from inside the running scene
after `await RenderingServer.frame_post_draw`.

| file | what it is for | draws / tris |
|---|---|---|
| `01_wide_passage.png` | a driven passage under the lamp: arch sets, lagging, pipe run, drum, spoil | 215 / 248,840 |
| `02_dense_mid.png` | the dense mid-distance: pipes on the haunch, sets receding, standing water, a beacon at range | 331 / 402,316 |
| `03_underfoot.png` | what a machine stands on: ballast, sleepers, grit, spall, fines | 103 / 206,734 |
| `04_chamber.png` | a chamber — the beam comes back with nothing | 344 / 378,694 |
| `05_two_registers.png` | **the frame that has to work**: the players' beacon, machined and lit, standing against timber lagging, a bolt line, a cast survey plate and sagging cable | 172 / 221,696 |
| `06_falloff_to_black.png` | the long view: falloff to black, nothing legible past ~12 m | 335 / 308,534 |
| `07_junction.png` | a crosscut leaving a drive — the atom of every teaching stop | 202 / 233,670 |
| `08_waterline.png` | the sump edge: tide-mark crust, standing water, wet iron | 289 / 383,224 |
| `09_machine_ground.png` | the deep register approaching the plant chamber | 384 / 392,806 |
| `10_natural_shallow.png` | shallow natural karst: pendants, breakdown, flowstone, no straight line | 122 / 244,240 |
| `11_set_line.png` | the 1.2 m module: sets on the module, pipe run, mesh, wet floor | 349 / 411,468 |
| `12_crown.png` | looking up: Bus, ducting, cable, bolts on the crown | 341 / 409,020 |

---

## 7. The density bar — what hit it and what did not

The bar was three scales in every frame, in two registers.

### Hit

* **Silhouette.** Timber sets and steel arches on the 1.2 m module, one failed set among
  standing ones, roof pendants, breakdown blocks, buttresses in the shell displacement, spoil
  heaps, a pipe run, ducting, the Bus on its insulators, a rail line, a derailed tub, the
  launder. `04`, `09`, `11` carry six or more of these at once.
* **Lamp distance.** Bolts and plates on the module, mesh panels, sagging cable in catenaries,
  survey plates, drums and chain coils, standing water and puddles, silt fans, the crust band
  at the waterline, rust runs from anything ferrous, drips.
* **Underfoot.** Between 40 and 90 discrete objects per 0.6 m cell — stone, grit, ballast,
  spall, fines, litter — plus sleepers and the gutter. `03` is the proof.
* **Instance count and cost.** 33,470 props at 320 draw calls and 97 fps, with the ablation
  showing the props are not what costs.
* **The topology/dressing split**, hashed, and portable.

### Did not hit, and I would not claim otherwise

* **The rock material at lamp distance is the weakest thing here.** It reads as a hard,
  slightly waxy stone with jointing, not as bedded, spalled, wet iron-ore country rock. The
  warped voronoi is much better than the unwarped "crazed pottery" it started as, but the
  bedding is still weak and the drill scars barely register at the scale they should. The
  ablation says there is fragment budget to spend here; what it needs is art time, not
  performance.
* **Wheel and foot tracks are missing.** They are on the designer's underfoot list. They need
  decals (procedural `ImageTexture`) or a world-space track mask in the floor shader.
* **The two registers collide, but not hard enough.** `05` does what was asked — clean
  machined beacon against rotten timber and old iron — and the tray-requires-a-bracket rule is
  the right mechanism. But the brought register is currently 5 objects out of 47, and none of
  them is *big*. The image the designer described ("a modern beacon standing in a Victorian
  drive... lowered into and dwarfed by the old") wants at least one large brought object per
  chamber — a lowered pallet, a mast, a charging rack — and the spike has only a small mast.
* **Chambers interpenetrate the swept passage** rather than being blended into it. Invisible
  in the dark, wrong the moment anything lights a chamber properly.
* **No occlusion culling.** `OccluderInstance3D` is the obvious next lever and would matter a
  lot at a junction, where two passages are in the frustum and one is behind a rib.
* **No streaming.** The whole stretch is built at load. 531 ms for 144 m is fine for a raid
  load screen; it is not fine for a 2 km cave, and the chunk structure is already the right
  unit to stream on.
* **Water is a flat translucent plane** with a low roughness. It gives the grazing-angle
  mirror ART-DIRECTION §3.5 wants, and nothing else — no thermocline, no refraction, no
  motion.
* **No silt plume behind a moving agent.** There is no agent. The resting fog is there and the
  beam is visible in it, which is arguably already too generous — §2.6 says the beam should
  appear only when something has stirred silt.
* **The `noprops` frame is slower than the full one**, which means the current density is not
  where the cost is. That is a good problem, but it also means this spike has *not* found the
  ceiling. I do not know what the ceiling is.

---

## 8. Top three risks for doing this for real

**1. The shell and the collision surface are two different things.**
The visual passage is swept from a smoothed centreline; the simulation would walk the integer
cell grid. They agree to about a cell. That is the classic source of "the machine is standing
in the wall" and of players seeing a wall the sim thinks is open — and because the sim is
authoritative and the client only ever sees `Belief`, the mismatch would show up as the
*agent* behaving impossibly. It has to be resolved before Phase 3 by one of: deriving the
walkable surface from the mesh, deriving the mesh strictly from the grid, or making the sweep
snap to cell centres. My recommendation is the last one — cheap and it keeps the module.

**2. GDScript is a stand-in, and the real build's cost split is not this one.**
Topology is 5 ms here and would be well under 1 ms in Rust with fixed point, so that half is
safe. Dressing at ~1.9 ms per metre in GDScript is the half that has to move to GDExtension or
be streamed, and mesh building in Rust behaves nothing like mesh building in GDScript — the
copy-on-write trap that cost 60 % of generation time here does not exist there, and other
things will. Anyone budgeting off these numbers should budget off the *topology* numbers and
re-measure dressing after the port.

**3. The look is one lamp away from being unreadable, and the density hides it.**
The frame currently survives because ~90 % of it is black and the eye forgives what it cannot
see. Change one thing — add the contingency lighting circuit of ART-DIRECTION §2.8, put a
second agent's lamp in the frame, light a chamber properly — and every weakness in §7 becomes
visible at once: the chamber interpenetration, the flat water, the soft rock. The spike proves
the *pipeline* at one lamp. It does not prove the look at two, and the first time the game
puts two agents in one chamber it will find out.

---

## 9. Everything I guessed, in one list

Anything below is mine, not read out of a document.

1. **Every metre dimension of the four width classes.** Half-widths 750/1050/1350/1950 mm and
   heights 1300/2200/3200/5000 mm are my reading of `docs/art/vision/cave/NOTES.md` B2, which
   itself calls its metres a guess. The cell-count classes they derive from are marked a guess
   in CHASSIS-TIMING.
2. **The whole floor profile.** −2 mm per cell general fall, one bowl at 58 % of the stretch,
   `max(6, n/11)` cells half-width, 1500 mm deep, water datum at lowest floor + 950 mm.
   Nothing in the docs says where a sump is or how deep.
3. **The `worked` ramp** — the three knees at 13 %, 30 % and 64 % of the stretch. §7 says
   worked climbs with depth; the shape of the climb is mine.
4. **Rule R5**, that `worked > 128` forces a passage-class section. Defensible from
   ART-DIRECTION §3.4 (the drive is a standard 2.4 × 2.4 m section) but it is an inference.
5. **Every number in the works table of §3.1 R10** — every threshold, every percentage, the
   1.2 m module spacing of the plate (`along % 12`), and the beacon spacing formula.
6. **The width-class run lengths and mix** (6–22 cells, and the three depth bands).
7. **The crosscut rules** — one every 26–40 cells, 10–20 long, one class narrower, and the
   idea that a crosscut peters out at its far end.
8. **Chamber placement at 17/44/71/92 %** and radius 5–9 cells, and that the deepest one holds
   the plant.
9. **`integ`**, structural integrity, as a per-5-cell random field. The docs call for "one
   timber set failed while its neighbours stand" but not for a field that decides it.
10. **The wetness formula**, `max(255 − above/4, 25 + 95·depth/n)`.
11. **The rock-type block size** (9 cells) and the ranges of `fracture` and `bedding` as
    integers (3–14 and 0.4–3.5 come from ART-DIRECTION §3.1; quantising them per block is
    mine).
12. **Every dimension of every one of the 47 kit meshes** — the tub, the pump, the launder,
    the insulator, the beacon, the case, the mast, the instrument, the tray, the duct. The
    docs describe several of them in words; none of them in millimetres.
13. **The colours of everything that is not rock.** Cast iron (0.058, 0.030, 0.017), timber
    (0.072, 0.053, 0.036), composite (0.185, 0.196, 0.180), aluminium, porcelain, rust
    (0.230, 0.098, 0.042). The three rock values and the crust are from ART-DIRECTION §3.1
    and are not guesses.
14. **The lamp's numbers in Godot units**: energy 4.2, 54° cone, 11° down-tilt, 26 m range,
    inverse-square decay, 4096 shadow atlas. §2.2 says explicitly to re-derive these per
    renderer against the ratios; I derived them against the §2.9 histogram and 9 of 12 frames
    pass.
15. **The beacon pilot** as a real point light (0.9 energy, 2.6 m range, amber). ART-DIRECTION
    lists running lights at strength ≤ 3 and does not say whether a dropped beacon lights
    anything. The cave board guessed 1.5 W; I guessed differently.
16. **Every visibility range** — 44 / 30 / 19 / 12 m. Derived from "spend no art budget past
    15 m" (§3.6), but the four numbers are mine.
17. **The 8 m chunk size** and the 0.2 m ring spacing and 30-vertex ring.
18. **The camera**: 1.15 m eye height, 46° vertical FOV, 1.7 m/s walk. There is no machine in
    the frame, so the eye height is a proxy for one and is not any chassis's actual sensor
    height.
19. **The silhouette displacement amplitudes** — 0.42 m natural, 0.085 m worked.
20. **That the composite tray requires a bolt line.** This is my reading of "the new bolted
    onto the old" as a placement rule. It is the rule I am most confident about and the one I
    would most like confirmed, because a lot follows from it.

---

## 10. One design problem found, which is not an art problem

**The brought register has no large object, and the design does not currently name one.**
DESIGN-PRINCIPLES §4 asks for "the new bolted onto, lowered into and dwarfed by the old". The
first two are placement rules and this spike implements them. The third — *dwarfed by* —
requires something of the players' that is physically large enough to be dwarfed, and the
inventory does not have one underground. Beacons, cases and instruments are all hand-sized;
the machines themselves are 0.2–0.9 m. Everything large in the cave belongs to the ancients.

The result is that a frame reads as "an old mine with some small new kit in it" rather than as
a collision of two registers. The fix is a content decision, not an art one: the players need
at least one piece of large deployed equipment underground — a lowered pallet or cradle, a
relay mast, a charging rack, a winch head — placed by the generator at chambers and junctions.
`DESIGN-PRINCIPLES §3` says the surface is where the handling gear lives; something of it has
to come down the shaft, or the second register will never be more than a garnish.
