# Spike — the surface, generated procedurally, running in Godot 4

A Godot 4.7.2 project that builds a pit-head from one integer seed, entirely in code,
with **no imported meshes, no imported textures, no UV maps and nothing hand-placed**,
and flies a camera through it in daylight, rain and dusk.

This exists to answer one question the designer asked on 2026-09-08:

> *"this is a very solid start, but in the real game its going to need way more detail…
> dont do that in blender though. we need to figure out how we are going to do all this
> procedurley and than have it playable in godot"*

**A second pass ran on 2026-09-09 against `DESIGN-PRINCIPLES` §6 ("it needs to look
photoreal"), and it rewrote both shaders, the ground mesh and the lighting. Read
`PHOTOREAL.md` alongside this: where the two disagree on a material number, a shader, an
exposure or a frame time, PHOTOREAL is the current one.** §6 and §7 below are the
weaknesses that pass was aimed at.

**A third pass ran the same day against `DESIGN-PRINCIPLES` §7 ("density is order, not
scatter"), after the designer said the yard read as an abandoned scrap yard. It deleted
33 247 props and replaced weighted random scatter with a vocabulary of aligned
arrangements placed against new LAYOUT fields. Read `ORDER.md`: where it disagrees with
anything below about how an object gets its POSITION - §2.2's yard fill, §2.4's underfoot
rules, §2.3's charge row, and the layout/dressing table in §1 - ORDER is the current one.**

Everything below is a **pipeline**, not a picture. The Blender vision board under
`docs/art/vision/surface/` is the target; nothing from it ships and nothing from it is
imported here.

---

## 0. How to run it

```
GODOT=".../Godot_v4.7.2-stable_win64.exe"
$GODOT --path spikes/godot/surface --resolution 1920x1080 -- --mode=free
$GODOT --path spikes/godot/surface --resolution 1920x1080 -- --mode=shots
$GODOT --path spikes/godot/surface --resolution 1920x1080 -- --mode=bench --secs=40 --light=dusk
```

`--seed=N`, `--light=overcast|rain|dusk`, `--shot=<name>`, `--dbg=N` (see §8).
In `--mode=free`: mouse to look, WASD/QE to fly, shift to sprint, **1/2/3** switch the
lighting condition live, **F2** saves a screenshot and prints the camera position so a
new shot can be added to the list in one paste.

Measured on the **NVIDIA GeForce RTX 3080 Laptop GPU** (Vulkan 1.4.312, Forward+).
Godot picks device #0 and prints it; the log line `adapter :` in `perf/*.txt` is the
proof, and it is the NVIDIA part, not the Intel UHD.

---

## 1. The seam, which is the part that matters

`DESIGN-PRINCIPLES.md` §5 splits generation in two. This spike splits it in two **files**
so the split is auditable by reading, exactly as `CLAUDE.md` asks of the sensor layer.

### `scripts/layout.gd` — what the simulation would agree on

This is what `blindside-gen` owns. In this file:

- every number is an **integer, in millimetres** (or cells). There is no float literal
  and no float operation anywhere in it.
- there is **no square root**: the spoil-tip profile and the pad feather are both written
  against *squared* distance, so the rule ports to Rust as integer arithmetic with no
  `isqrt` and no fixed-point division.
- **no Dictionary is ever iterated.** The plan is a Dictionary only because GDScript has
  no structs; every field is an ordered `Array` and every loop is over an Array. In Rust
  it is a `SitePlan { … }` of `Vec<…>` and the field order is the declaration order.
- the RNG is a plain integer LCG (`s = (s*1103515245 + 12345) & 0x7FFFFFFF`) split into
  independent **streams** by purpose — stream 1 headframe, 2 course, 3 spoil, 4 columns —
  so adding a call to one stream cannot move another. In Rust this becomes
  `DeterministicRng::draw(tick, entity, purpose)` from `ARCHITECTURE.md`; the stream id is
  the `purpose`.
- the plan carries a **64-bit hash of itself** (`plan["hash"]`), printed on every run.
  That is the number that goes in the replay. Two clients that disagree on it are not
  playing the same match. Nothing in the dressing layer may change it — that is the
  property to write a test against.

### `scripts/dressing.gd`, `props.gd`, `scatter.gd`, `ground.gd`, `materials.gd`, `weather.gd`

Client side. Floats everywhere, seeded from the same site seed so two clients agree
visually, but **nothing here is allowed to feed back**. Each of these files takes the
layout as an input and only ever *reads* it.

### Where the line sits, precisely

The test is one sentence: **could you delete this object and have a machine walk a
different route, or a rule score differently?** If yes it is layout. If no it is dressing.

| Layout owns | Dressing owns |
|---|---|
| the shaft rectangle, collar height, lined depth, total depth | the collar castings, the rivets, the bunton sets, the guide rails, the cage |
| headframe foot spread, deck height, total height, sheave radius | how many bays, which bay gets which diagonal, the ladder, the rope sag, the rust value of each member |
| building footprints and their eaves height, and whether they are roofed | the ruined parapet profile, the openings, the coping, the rubble at the foot, the missing roof sheets |
| the hardstanding rectangles and the 3600 mm slab module | slab joints, cracks, oil, tracked mud, puddles, aggregate, weeds in the joints |
| the ground height field, in integer mm | the terrain mesh resolution, the normals, the horizon skirt |
| the course graph — nodes, edges, leaves, which leaf holds the cargo, passage width, wall height | the hoarding panels, the corrugation, the posts, the number plates, the pilot on the root post |
| zone rectangles and what each zone is *for* | which of the twenty-two cluster generators fires in a zone, and every object inside it |
| fence polyline, gate span, fence height | hoarding vs palisade, which 6% of panels are missing or leaning, the barbed arms |
| lighting column positions and heights | the fitting, the number of heads, the lumens, whether it casts a shadow |
| pole positions, mast positions and heights | crossarms, insulators, catenary sag, dishes, the obstruction pilot |
| the station list — bench, cradle, listening post, course root — as points a machine plugs into | everything on the bench, the tool board, the cases, the cable reels |
| the **walkways**: six polylines at 3400 mm between the gate, the collar, the bay, the charge row, the containers and the course | nothing. Dressing is forbidden to place a cluster inside one, which is why the yard has routes through it rather than being a scrapyard |
| the gantry rail line and height | the crab, the hoist block, the lifting frame, the chain |

**What crosses the line, and in which direction only:** layout → dressing, once, at build
time. `Dressing.new(L, B)` takes the layout by reference and writes instances into a
`Batcher`. There is no path back. The two things dressing reads most are
`L.ground_mm(x, z)` (integer in, integer out — the height a foot stands on) and
`L.on_pad(x, z)`. Both are layout queries, and the ground shader gets the pad rectangle
as a `vec4` uniform straight out of the plan so the concrete stops **exactly** where the
simulation says it stops rather than where a noise field happens to fade.

**One deliberate exception, flagged:** the ground shader derives "is this spoil" from
world **height** (`smoothstep(0.55, 3.2, wpos.y)`) rather than from a layout field. That
is dressing reading a layout-derived quantity, which is fine, but if the sim ever needs to
know "is this cell spoil" it must come from the plan, not from the shader's threshold.

---

## 2. Every generation rule, in enough detail to port

Rules are stated in the order they run. Layout rules are integer; dressing rules are the
comment above each function in the source, and the source is the authority.

### 2.1 Layout (integer, mm)

1. **Site box** fixed at x ∈ [−78, 96] m, z ∈ [−74, 74] m. The seed does not move it.
2. **Shaft** at the origin: 2400 × 2000 collar, 400 mm stone plinth, 150 mm collar proud,
   iron-lined for the top 3000 mm, 40 m deep.
3. **Headframe**: height seeded in [11600, 13400]; deck at height − 1400; foot spread
   seeded in [6800, 7800] × [6000, 7000]; deck rectangle fixed 2600 × 2400; sheave radius
   1100, sheave gap 1500.
4. **Hardstanding**: one main pad −32…30 × −26…26 m at +150 mm, one course apron
   30…38 × −10…10 m at +120 mm. Slab module **3600 mm** = 3 × the industry's 1.2 m module
   from `ART-DIRECTION` §3.3.
5. **Buildings**: five fixed footprints, each tagged `old` or `new`. Old = the prior
   industry's dead works (winding house, boiler house, fan house). New = the players'
   (service bay, store). The tag is what selects the whole material and geometry register
   downstream; it is the single most load-bearing field in the plan.
6. **Zones**: nine rectangles, each with a `kind`. A zone is layout because a full one is
   not walkable. The kinds are `charge_row`, `container_row`, `tank_farm`, `spares`,
   `drums`, `scrap`, `pallets`, `transformer`, `muster`.
7. **Course**: a corridor tree grown from the root on a 2400 mm cell. Pick a frontier node
   at random; if its depth > 6 retire it; roll 1 or 2 branches (3-in-5 for 2); each branch
   takes a direction from `[(1,0),(1,1),(1,−1),(0,1),(0,−1),(1,0)]` — east is drawn twice
   so the course grows away from the yard — and a length in [3,7] cells; reject if it
   leaves the box (x ∈ [0,24], z ∈ [−13,13]) or lands within Manhattan 2 of an existing
   node; stop at 26 nodes. Leaves are degree-1 nodes; one leaf, chosen from the same
   stream, holds the cargo. Passage half-width 900, wall height 1200.
8. **Spoil tips**: fourteen fixed ring positions, each jittered ±3500 mm, radius seeded in
   [9000, 22000], height in [3200, 10500].
9. **Height field**, integer in and out, and this is the one query the whole build leans on:
   two octaves of integer value noise (period 17000 amp 900, period 6100 amp 260) plus, for
   each tip, `h += tip_h · t² / 10⁶` where `t = (r² − d²)·1000 / r²`; then the pads are
   graded flat with a squared-distance feather over 4 m:
   `k = ((4000² − d²)·1000)/4000²`, `k = k²/1000`, `h += (pad_h − h)·k/1000`.
10. **Haul road** polyline from the west gate to the collar apron, 7000 wide.
11. **Fence** rectangle −34…92 × −34…34 m at 2400 high, enclosing the yard **and** the
    course, with a 7 m gate span in the west run.
12. **Lighting columns**: twelve seeded positions ±800 mm, height in [8000, 11000], one or
    two heads.
13. **Poles** every 22 m from x = −76 to the transformer pen; **masts**: one comms mast
    21 m, one vent stack 17 m.
14. **Stations**: listening post, bench, cradle, course root — points with a yaw, because
    a machine stands at them.
15. **Gantry**: rail line over the service bay at 4600, 6000 gauge.
16. **Walkways**: six polylines at 3400 mm wide — gate→collar, collar→bay, collar→course,
    bay→charge row, along the charge row, collar→containers. Circulation is layout because
    it is the route a machine takes, and because dressing must be forbidden from blocking
    it. Adding this rule changed the layout hash, which is exactly the behaviour wanted.

### 2.2 Dressing — the inherited (`dressing.gd`)

- **Headframe.** Four battered legs foot→deck as I-sections. Bays every ~1.9 m; per bay
  per face one horizontal tie (angle) and one diagonal, alternating direction by bay
  parity. A rivet line at 550 mm along every tie. Deck is a 7 × 7 grid of grating panels
  with a perimeter I-beam. Handrail on three sides: stanchion every ¼ of the run, top rail
  and knee rail. Two sheaves, axis along Z, at the head: the one the rope runs on is
  **bearing steel**, its neighbour is the same rust as the legs — `ART-DIRECTION` §5.2,
  *"still in use is polished bright by the work itself"*. Rope = 10 segments with 3.5% sag
  from sheave to winch and from sheave down the shaft. One caged ladder up a leg. The hoist
  beam under the deck is **THE BROUGHT**: grey, chamfered, bolted onto the old frame.
- **Collar and shaft.** Plinth = 26 dressed blocks forming a frame round the opening. Four
  cast collar castings with bolts on the 0.6 m module. Lining: rings of 750 mm iron plate
  for the top 3 m, then 2.5 m rings of rock, and **every ring's instance colour is
  multiplied by `1/(1 + (depth/2.2)²)`** — the inverse-square a rectangular sky hole
  actually delivers. Three metres down it is 35%, at eight metres 7%: the shaft reads as a
  hole rather than a lit box. Timber bunton sets every other ring. Guide rails both long
  sides. Handrail on three sides, the yard side left open so a machine can walk in. The
  surface end of the acoustic link is a cable drum on the plinth with the hydrophone cable
  running to the lip and over it.
- **Cage** one metre into the collar: open grating floor (so a machine reads against the
  sky from below), four corner angles, three rails per side, a four-rope bridle to one rope.
- **Winch**: skid on a cast pad, drum with 22 wraps of rope, control cabinet, fairlead
  bollard, and a cable tray running to the service bay.
- **Ruined masonry**: each wall is built as 600 mm piers whose top height is
  `h · (0.62 + 0.38·(0.5 + 0.5·sin(frac·9 + wall·2.3 + seed%17)))` × [0.94, 1.06] — so the
  parapet is broken and the break is seeded, not noisy. Openings punched on a 4-pier
  rhythm with a sagging timber lintel; 70% of piers get a coping stone at a random small
  yaw; three rubble lumps at the foot of every pier. If the building is roofed: trusses
  every 2.4 m, corrugated sheets every 0.9 m with **22% missing**.
- **Winding gear**: stone bed, 4.6 m flywheel, drum, connecting rod, and a pipe run that
  random-walks out of the bed and through the wall.
- **Stack**: 1.2 m lifts of tapering brick with a slight rotation per lift, iron banding
  every third lift, a cracked cap, a lightning conductor.
- **Fence**: angle posts at 3 m, four 0.75 m hoarding sheets per bay each with four
  corrugation ribs, three rails, two wires above, a raked barbed arm per post; 6% of bays
  missing and 10% leaning. The gate hangs open.
- **Poles**: timber pole, two crossarms, two braces, four porcelain insulators, and a
  catenary of 8 segments at 4.5% sag to the previous pole. The catenary is the only curve
  in the frame, which is why it reads.
- **Spoil dressing**: one lump per 6 m² over each tip, biased to the toe by
  `d = sqrt(rand)·r`, plus thrown-out timber and iron at 0.7 per metre of radius.
- **Course**: per edge, cut back 1.3 m at each node, then two hoarding walls at ±900 mm
  built from 1.2 m panels with five corrugation ribs each, a timber post per panel and a
  top rail. Node furniture: a numbered plate on a post at every junction; the root gets a
  galvanised post with a `WARM_DIM` pilot (the course's "shaft" beacon); the cargo leaf
  gets a pale crate and seven stones.
- **Lighting columns**: cast base, tapered column, a door and a duct stub, one or two flood
  heads on a raked bracket, four holding-down bolts.
- **Road furniture**: kerbs at 0.9 m both sides, a gully grating every third kerb on the
  low side, a bollard line at the apron.

### 2.3 Dressing — the brought (`props.gd`)

The register is deliberate and mechanical: **chamfered** boxes (a `casebox` mesh with a
0.10 chamfer), pale bone / light grey / galvanised / aluminium, labelled panels, and small
warm pilots at emission ≤ 3. Everything in it is small enough to be dwarfed by the iron it
is bolted to, which is `DESIGN-PRINCIPLES` §4's *"the new bolted onto and dwarfed by the
old"* expressed as a size rule rather than a mood.

- **Service bay**: portal frames every 3.5 m with base plates and four bolts each, purlins,
  roof sheets, corrugated back cladding; then on a 1.2 m module inside it: a 4.8 m bench,
  under-bench drawers, **the seven modules laid out as parts on the bench** with a pilot
  strip each, fourteen hand tools, a tool board with 22 tools on it, a rugged terminal with
  a lit screen, a three-bay parts rack with binned shelves, seven labelled flight cases,
  three cable reels, a cable tray with seven cables into the roof, and three work lights.
- **Gantry**: two rails on legs with knee braces, reaching 4 m out of the bay over the
  yard; a crab, a hoist block on a chain, and a **lifting frame that fits a machine**,
  hanging just above one.
- **Charge row**: five pedestals on the 2.4 m module, each a chamfered post with a bone
  head, an amber pilot, a labelled plate, a coiled cable on a hook and a painted stand box;
  a trunking run behind, cable ramps across the walkway, and a battery skid with a fin bank
  and two fans.
- **Containers**: 6.06 × 2.44 × 2.59 on the 2.44 module, stacked to two every third row,
  20 corrugation ribs per side, eight corner castings, doors with four bars, a label panel.
  Alternating rows are the players' grey and the mine's rust — the two registers stacked
  literally on top of each other.
- **Tanks**: three on a bunded slab, banded every 1.2 m with a bolt each side, conical top,
  vent, caged ladder, a valve manifold with a handwheel and a label, and a two-pipe bridge
  out of the farm.
- **Transformer pen**: palisade at 140 mm pitch, two transformers with 14-fin radiator
  banks and three porcelain bushings each, four switch cabinets, a chequer-plate trench lid.
- **Comms mast**: three-leg lattice on a cast pad, 1.2 m bays with horizontals and
  diagonals, guys at two levels to three anchors, two dishes, three panel antennas, a cable
  ladder with six cables, an amber obstruction pilot at the top.
- **Yard fill** — *the rule that carries walking distance*. The pad is swept on a **2.35 m
  lattice**; each cell that is not inside a building, a stocked zone, the collar apron, the
  gate approach or within 1.6 m of a lighting column rolls once at **p = 0.78** against a
  table of **twenty-two cluster generators**: bottles, stillage, toolchest, barrow, cones,
  barrier, bin, hosereel, planks, tyres, cans, ladder, tarp, genset, crates, sandbags,
  jersey barrier, steel plate, duckboard, tripod, welding set, cable spool. A cluster is
  4–30 instances. A second sweep at 3.4 m and p = 0.40 fills the unpaved strip between the
  pad edge and the fence with the heavy half of the table only.
- **Machines**: a parametric quadruped, ~0.77 m long, 34 instances — chamfered hull, a
  graphite chassis slab under a pale shell (`ART-DIRECTION` §4.3's value inversion), two
  flank strips at emission ≤ 3 sized by **area not intensity**, three deck modules, a
  four-tube beacon rack, the rubber-coated **recovery handle**, neck, head, a sensor bar,
  a lamp disc, and four three-segment legs with rubber feet. Pose is a parameter:
  `stand`, `dock` (legs spread on a charge plate, cable to the pedestal), `cradle`,
  `wreck`. Twelve machines are placed: three on charge, one on the service cradle under
  the hoist, one at the collar, one walking in from the course, one on the course, four on
  the muster square, one wreck on a trestle by the bench.
- **Wreck**: rolled 24°, belly down, one leg gone below the knee, a shed hull panel on the
  ground beside it, every emissive dark, mud colour throughout, and the recovery handle
  left bright — the one clean thing on it, per `ART-DIRECTION` §6.2.
- **Signage**: eight posts with a pale plate, an amber band and two grey text bars, placed
  where one register meets another.

### 2.4 Dressing — underfoot (`scatter.gd`)

Everything here goes in the DETAIL bucket: chunked at 16 m, **shadow casting off**, culled
past 55 m.

- **Gravel**: 2.2 lumps per m² over every unpaved square metre inside 74 m of the collar,
  30–140 mm, flattened, random yaw and a little pitch/roll, colour drawn from the rock
  family.
- **Pad chippings**: 9 per m² over the hardstanding at 25–105 mm, plus a dense band within
  ±350 mm of every slab joint on the 3.6 m module — the line the sweeper never reaches.
- **Weeds**: a 5-blade tapered-triangle tuft (no alpha, no transparency): in the slab
  joints at 2.2 per metre of joint, over open ground at 0.22 per m² thinning to a quarter
  within 14 m of the collar because that ground is worked daily, and an unbroken line at
  the foot of the perimeter fence.
- **Fixings**: 26–60 nuts, washers, bolts, shims and offcuts within 4 m of every structural
  foot, every lighting column and every station. *Where something was bolted, something was
  dropped.*
- **Litter**: 0.16 per m² over the pad — cable ties, tape rings, offcut plastic, banding
  strap, a board, a torn sheet.
- **Ground cables**: six runs that snake across the pad from a source to a load with a
  sandbag every fifth segment.
- **Decals**: three textures generated as `Image` in code (a lobed stain, a tyre track
  pair, and the track re-used for machine tracks). ~98 decals: stain clusters where
  machines stand and where drums are, track lines along the haul road and the collar
  approach.

---

## 3. Technique, and why

| Decision | Why, and what it cost |
|---|---|
| **One MultiMesh per (mesh, material, chunk)** | The whole site is 24 unit meshes under transforms. 84 000 instances land in ~1 400 MultiMeshes; a typical frame draws 180–900 of them. This is the single decision that makes the density affordable — without it the same site is 84 000 draw calls. |
| **`MultiMesh.buffer` written as one `PackedFloat32Array`** | Per-instance `set_instance_transform` is an FFI call each; writing the 16-float buffer in one go put the whole flush at ~50 ms. |
| **Three buckets: SITE / PROP / DETAIL** | SITE always resident and shadow-casting. PROP chunked at 32 m, shadow-casting, culled past 140 m. DETAIL chunked at 16 m, **no shadows**, culled past 55 m. Shadow casting is the expensive half of a daylight scene; the rule *"if it is smaller than a boot it does not cast"* is worth more than any other single setting here. |
| **`visibility_range_end` per chunk instead of mesh LOD** | `MultiMeshInstance3D` inherits `GeometryInstance3D`, so a chunk is one `visibility_range_end` away from being LOD. No LOD meshes were generated at all; the underfoot band simply stops existing at 55 m, where a 40 mm chipping is a quarter of a pixel. |
| **Kit of parts, assembled by rule — not noise fields** | An industrial site is a *catalogue*, not a fractal. The mesh library is box, chamfered box, I-beam, angle, channel, cylinder (6/10/12), hex bolt, three rock blobs, an angular chipping, a spoked wheel, a flat ring, a cone, a quad, a grating, a ladder, a weed tuft, a dish, a ribbed drum, a pallet, a bollard. Everything on the site is one of those under a transform. |
| **Flat shading everywhere** | Faceted reads as machined, costs nothing, and removes the need for smoothing groups or tangents. |
| **Per-instance colour → albedo multiply** | One material covers a whole family. Corroded iron varies enormously in value and *that variation is the material*; it comes from the instance colour, not from twelve materials. |
| **Two shaders total, world-space procedural, zero textures** | `ART-DIRECTION` §3.2: a generated site cannot be unwrapped, so world-space procedural is not an optimisation, it is the only option. The solid shader takes eleven uniforms (albedo, roughness band, metallic, grain, vertical streak, streak colour, noise scale, dirt, dirt colour, wet response, emission). The ground shader derives hardstanding, spoil, traffic and flatness from world position and the pad rectangle. |
| **`global uniform float g_wet`** | One number, set by the weather preset, darkens and polishes every material and floods the joints. Rain is a global, not a material edit. |
| **A procedural bump on the ground, three noise taps** | Without it the hardstanding is a smooth plane at 0.4 m and the aggregate never reads. |
| **Decals for staining and tracks** | ~98 `Decal` nodes with generated textures, distance-faded from 35–40 m. They are what geometry cannot do: oil that soaks in, mud dragged out of a gate. |
| **`OccluderInstance3D` boxes, in code** | Three boxes on the winding house, the container row and the service bay. Baking an occluder needs the editor; `BoxOccluder3D` does not, so it is available to a generated world. |
| **CSG: rejected** | Considered and not used. CSG is a blocking tool for a level designer; it does not survive being generated per match, and everything it would have done here is cheaper as a kit part. |
| **Rain as one `GPUParticles3D`** | 14 000 particles, a box emitter that follows the camera, `BILLBOARD_FIXED_Y` quads. Cheap; see the measurement table for what it actually costs. |

### Daylight, which is the cost centre

The cave has one lamp; the surface has a directional light over 170 × 148 m. What was done:

- `directional_shadow_max_distance = 95`, 4 splits at 0.06 / 0.17 / 0.45, `blend_splits`
  off, fade start 0.85.
- `shadow_bias = 0.11`, `shadow_normal_bias = 3.2`. At the Godot defaults (0.04 / 1.4) the
  far splits acne so badly that the ground beyond ~40 m goes uniformly dark. That looked
  exactly like a lighting bug for an hour and was not one.
- Every DETAIL MultiMesh has `cast_shadow = OFF`. That is ~55 000 of the 84 000 instances
  not in the shadow pass.
- `light_angular_distance = 4.5` in overcast: soft edges without a second shadow pass.
- SSAO on at radius 0.7 / intensity 1.05; SDFGI **off** (it is a per-match generated world
  and SDFGI's build cost is not affordable); glow off; volumetric fog off.

---

## 4. Measurements

**NVIDIA GeForce RTX 3080 Laptop GPU**, Vulkan 1.4.312, Forward+, 1920 × 1080, vsync off,
MSAA 2×, directional shadow atlas 4096, positional shadow atlas 4096.
`--mode=bench --secs=40`: the camera flies a fixed 14-waypoint loop that passes through the
yard, the bay, the collar, the course, the container row and back out to a wide view, so
every density regime is in the sample. Raw per-sample CSVs in `perf/frames_*.csv`, logs in
`perf/bench_*.txt`.

### 4.1 Sustained, camera moving

| | overcast | rain | dusk |
|---|---|---|---|
| frames sampled over 40 s | 4 574 | 4 894 | 5 390 |
| **mean frame** | **8.53 ms — 117.3 fps** | **7.97 ms — 125.5 fps** | **7.24 ms — 138.2 fps** |
| median frame | 9.09 ms — 110.0 fps | 7.58 ms — 132.0 fps | 6.25 ms — 160.0 fps |
| p95 frame | 11.90 ms — 84.0 fps | 11.11 ms — 90.0 fps | 11.90 ms — 84.0 fps |
| p99 frame | 12.50 ms — 80.0 fps | 12.50 ms — 80.0 fps | 12.96 ms — 77.1 fps |
| **worst single frame** | **12.60 ms — 79.4 fps** | **12.96 ms — 77.1 fps** | **15.14 ms — 66.1 fps** |
| draw calls, max in frame | 911 | 917 | 1 140 |
| primitives, max in frame | 2 154 355 | 2 183 847 | 2 258 251 |
| render objects, max in frame | 911 | 917 | 1 140 |
| video memory | 255.9 MB | 287.9 MB | 287.9 MB |

A fourth run of the same overcast pass, taken last with the machine cool, came in at
**5.01 ms mean (199.7 fps), p99 8.69 ms, worst single frame 16.00 ms (62.5 fps)**. So the
mean is worth somewhere between 117 and 200 fps depending on how hot the laptop is, and
that spread is the honest number.

**What does not move is the tail: across every run and all three lighting conditions the
worst single frame of a 40-second pass is between 62 and 79 fps.** It never drops below 60.
The tail is the wide establishing view at each end of the loop, where the whole site is in
frame and ~900 MultiMeshes are submitted.

### 4.2 Generation, per site, one seed

| | ms |
|---|---|
| **LAYOUT** (the whole integer plan: course grower, spoil, walkways, hash) | **0.8 – 2.6** |
| ground mesh (33 687 verts, 66 608 tris, one draw call) | 300 – 340 |
| dressing — the inherited | 60 – 80 |
| dressing — the brought | 90 – 120 |
| dressing — underfoot scatter and decals | 670 – 710 |
| flush to MultiMeshes | 54 – 56 |
| **TOTAL** | **1 140 – 1 300** |

Layout — the part that has to be deterministic and portable — is **under 3 ms**. The other
1.2 s is GDScript looping over 85 000 instances and calling the height query ~100 000 times;
in Rust behind GDExtension it is not a number worth discussing. It is, however, the reason
you would generate the surface at match start and not during one.

### 4.3 What is in the site

| | |
|---|---|
| prop instances alive | **85 144** (85 381 before the walkway rule cleared the routes) |
| of which underfoot (DETAIL, no shadow, culled at 55 m) | ~55 000 |
| MultiMeshInstance3D nodes | 1 479 |
| triangles across all MultiMeshes | 3 367 704 |
| ground mesh | 66 608 tris, 1 draw call |
| decals | 89 |
| unique meshes | 24 |
| unique materials | 22 (two shaders) |
| imported assets of any kind | **0** |

### 4.4 A caveat about the numbers

Run-to-run variance on a laptop is real and I hit it. Three benchmarks run back to back
produced an overcast pass with **mean 27.75 ms and p95 117 ms** — bimodal, median still
6.67 ms, so it was stalls rather than load. Run in isolation the same build gives the table
above. Every number quoted is from an isolated run; if you reproduce this, do not run the
three lighting conditions back to back and quote the second one.

One measured fix is in the build: two shadow-casting column floods at dusk put a **142 ms**
spike in the frame time when they entered the frame together with the bay omnis. Turning
their shadows off (only the shaft flood casts) and distance-fading every positional light
took dusk from *mean 13.23 ms / worst 142.68 ms* to *mean 7.24 ms / worst 15.14 ms*. That is
the single largest performance change in the spike and it is a lighting decision, not a
geometry one.

### 4.5 Determinism check

Four headless runs, `--headless --quit-after 2`:

```
seed 20260908  layout hash 1889570882374975  85144 instances
seed 20260908  layout hash 1889570882374975  85144 instances
seed 4242      layout hash 1102492564206557  84707 instances
seed 7         layout hash  524974411657025  84881 instances
```

Same seed reproduces the hash exactly; different seeds produce different plans and
materially different sites. That is the property that has to hold when this becomes
`blindside-gen`, and it is one assertion away from being a test.

---

## 4.6 The pictures

All at 1920 × 1080, captured in code after `await RenderingServer.frame_post_draw`, in
`shots/`.

| file | what it is for |
|---|---|
| `01_site_wide.png` | establishing: the whole compound from the south-west |
| `02_headframe_sky.png` | the headframe against sky, through the gantry's hoist and lifting frame |
| `03_yard_working.png` | the yard at working distance with the machines' kit in it |
| `04_service_bay.png` | inside the service bay |
| `09_sceptic_bench.png` | **the bench**: seven modules laid out, tool board, binned rack, terminal |
| `10_sceptic_charge.png` | **the charge row**: five pedestals, docked machines, cable ramps |
| `05_course.png` / `15_course_high.png` | the training course at machine height and from above |
| `06_shaft_mouth.png` | the collar looking down the shaft |
| `16_collar_close.png` | the collar from the yard, the acoustic-link drum on the plinth |
| `07_underfoot.png` | 0.4 m off the deck |
| `08_dusk_yard.png`, `13_dusk_wide.png` | the second lighting condition |
| `11_rain_collar.png` | the third: rain, which is canon |
| `12_yard_deep.png`, `14_gate_road.png` | depth into the yard, and the haul road at the gate |

**The two frames for a sceptic** are `09_sceptic_bench` and `10_sceptic_charge`: a bench
with the loadout laid out on it as parts, a tool board, a rack of bins, a terminal; and a
row of charge pedestals with machines docked on them, cables coiled on hooks, ramps over
the walkway and a battery skid at the end. Add `02_headframe_sky` — a modern hoist and a
lifting frame bolted to a century-old headframe — and that is the argument that somebody
here builds and services these machines.

---

## 5. Lighting: what the game should use

**Recommend overcast daylight as the default.** Three reasons, in order of weight:

1. **It is the only reading of the sky that agrees with `ART-DIRECTION` §2.1.** The shaft's
   12000 K `(0.60, 0.74, 1.00)` is *"the only cold light, and the only daylight"* in the
   game. If the surface has its own sun the direction has two daylights and the shaft stops
   being special. Making the surface's light **be** the shaft's light — a uniform overcast
   in that colour, no disc, no hard shadow edge — keeps that claim true, and it is what the
   vision board proposed (guess 4). This spike uses a soft directional at
   `angular_distance 4.5°` in that colour rather than a true dome, which is a cheat that
   buys contact shadows; a fully diffuse sky reads flat.
2. **The contrast that matters is surface-versus-cave, not morning-versus-evening.**
   `DESIGN-PRINCIPLES` §3: *"the surface is safe and lit; the cave is not… the art should
   make the descent feel like leaving somewhere."* A bright, flat, legible yard against a
   black hole is that sentence. Dusk halves the contrast for nothing.
3. **It is the honest exposure for a shaft mouth.** `21_shaft_hole` on the vision board is
   the correct picture: daylight goes black three metres down. Under overcast the falloff
   into the collar is the strongest single image the surface has, and it is free.

**Ship dusk as a state, not a default.** It is the better *picture* — the dusk wide frame
is the best frame in this spike — but it is better because it hides two thirds of the yard,
and hiding the yard defeats the reason the yard exists. Use it for the end of a raid
window, for a season, or for the moment after a machine is lost.

**Rain is canon and is a global.** `THE-MACHINERY.md` §1: the Assayer *"runs for as long as
it rains"*. `g_wet` is already the whole implementation: one float that darkens albedo,
drops roughness, fills the slab joints and turns the puddle field on. If rain is the season
lever, the surface's version of it costs one uniform.

---

## 6. Did it hit the density bar?

Honestly, per scale:

| Scale | Verdict |
|---|---|
| **Silhouette** | **Yes.** Headframe, sheaves, winding house and boiler house shells, the stack, the comms mast, the container row, tanks, twelve lighting columns, the pole line and its catenaries, the perimeter, the spoil ring, the course. The skyline reads as a working site from 55 m and from 15 m up. |
| **Walking distance (2–15 m)** | **Yes, in the yard; thin in two places.** The 2.35 m lattice × 22 cluster generators fills the pad convincingly, and the service bay, charge row, container row, tank farm and transformer pen each read as a *function* rather than as clutter. The two thin places are called out in §7. |
| **Underfoot (0–1.5 m)** | **Partly.** Slab joints, cracks, oil, tracked mud, standing water, aggregate at 9/m², weeds in the joints, dropped fixings, litter, cable runs and tracks are all there and all generated. But at 0.4 m the concrete still reads smoother than it should, the chippings read as scattered plates rather than embedded aggregate, and there is no displaced geometry at all — the ground is a 1 m grid with a shader on it. This is the weakest of the three scales and I would not claim it clears the bar yet. |
| **The two registers** | **Yes, and this is the part I am most confident in.** The inherited is riveted, corroded, timbered, broken-parapeted, and it is *big*. The brought is chamfered, pale, labelled, bolted onto it, and it is *small*. The container row stacks one literally on the other. The frames that argue it to a sceptic are `09_sceptic_bench` (bench, seven modules laid out, tool board, binned rack, terminal), `10_sceptic_charge` (five charge pedestals, machines docked, cables, battery skid) and `04_service_bay` (the gantry and the lifting frame over a machine on a cradle). |

---

## 7. What I could not do, and what is weak

1. **The ground is a 1 m heightfield.** No displacement, no ruts, no wheel tracks in
   geometry, no kerb-and-channel cross-section. The tracked-mud and tyre decals paper over
   this and they do not fully succeed at 2 m.
2. **The machines are placeholders.** They are 34-instance dolls at the right size with the
   right silhouette gestures and the right value inversion, but they are not
   `agent_model`'s walker and they do not move. Anything read off them about identity or
   loadout legibility is not evidence.
3. **The yard fill can still put a 1.2 m tyre stack in front of a camera.** The walkway
   rule fixed the routes, but a first-person camera standing anywhere else in the yard can
   end up inside a cluster. A real version wants either a small clearance query the camera
   respects, or clusters that know their own footprint.
4. **Nothing moves at all.** No wind on the weeds, no rotating sheave, no swinging hoist
   block, no smoke. A still yard reads as abandoned; two or three moving things would
   change the frame more than another 20 000 props would.
5. **No sound, no collision, no navmesh.** Layout produces the rectangles a collider would
   be built from; none is built.
6. **Only one seed was examined properly.** The generator runs on any seed and the layout
   hash changes, but I have looked hard at one site. A second seed could easily put a
   spoil tip through the course.
7. **The course is my own corridor grower, not `phase2.truth.corridor`.** Phase 2's graph
   is the one the sim actually walks; this one has the same shape and is not the same
   graph. Porting means taking the graph from `blindside-gen`, not from here.
8. **The service bay still reads dark inside.** It is roofed and the frames that argue the
   case hardest live in it. The bay's three work lights are now on in *every* lighting
   condition rather than only after dark — a roofed workshop is dark at noon — and it is
   still the dimmest of the sceptic frames. It wants a rooflight strip or one open bay,
   and that is a layout decision, not a dressing one.
9. **Underfoot at 0.4 m** — see §6.
10. **Generation is ~1.1 s of GDScript** and about 60% of it is the terrain height query and
   the scatter loops. In Rust behind GDExtension this is not a concern; in GDScript it is
   the reason you would not regenerate mid-match.
11. **The `Decal` count was never stress-tested.** ~90 is comfortable; the number at which
    Godot's clustered decal pass falls over on this GPU is not measured.
12. **The hardstanding reads paler than a hellscape wants.** Concrete at 0.086 linear
    albedo under a bright overcast sky lands around 0.45 sRGB and no amount of oil and
    tracked mud in the shader has pulled it down far enough. Either the pad is not
    concrete, or the sky is dimmer than I have it, and that is a design call.

---

## 8. Debug views built into the spike

`--dbg=N` on the ground shader / scene, which is how the two real bugs were found:

| N | What |
|---|---|
| 1 | ground shows `vec3(hard, mud, traffic)` |
| 2, 3 | flat albedo 0.4 (3 also disables the sun's shadow) |
| 4, 8 | hide the DETAIL bucket |
| 12 / 13 | hide the PROP / SITE bucket |
| 14 | hide everything except the ground |
| 15 | force an unshaded red `StandardMaterial3D` on the ground, print its AABB |
| 16 | enumerate scene children by class |
| 9, 10 | print layout probes / the largest MultiMesh bins |

### The two bugs, because they will happen again

- **`Basis.scaled()` scales the basis ROWS**, i.e. it applies the scale in the *parent*
  frame. Every rotated instance was being stretched along world axes instead of its own,
  so a 4.8 × 0.07 m bench became a 4.8 m post and the whole site was a forest of vertical
  bars. The fix is `Basis.from_euler(...) * Basis.from_scale(size)` — multiply on the
  **right** to scale local axes. `Batcher.xf()` carries the note.
- **Godot's front faces are CLOCKWISE.** The terrain grid was wound counter-clockwise, so
  every flat triangle was back-face culled while the spoil tips still rendered — because on
  a dome you see the inside of the far slope, which looks like a solid dome. The symptom
  was "the ground is washed out and none of my shader changes do anything", and it survived
  six wrong diagnoses (shadow acne, aerial perspective, gravel coverage, grazing Fresnel,
  vertex-colour gamma, specular IBL). `ground.gd` carries the note.

Two real findings came out of the wrong diagnoses and are worth keeping:

- **`fog_aerial_perspective` samples the sky in the pixel's view direction**, so a dark
  `ground_bottom_color` on the procedural sky paints every downward-looking ray black. The
  sky's ground half has to be about as bright as its horizon, because mist lit from above
  is not dark.
- **Grazing-angle Fresnel off a full-hemisphere sky turns a rough ground plane into a
  mirror.** A first-person camera near the ground sees it at 75–88° of incidence and
  Schlick's F → 1 whatever F0 is. The ground shader is `specular_disabled` and the one
  thing that should be shiny — standing water — gets a hand-written sheen instead.

---

## 9. Every guess, in one list

Things this spike decided that the design has not. Strike them individually.

1. **Site scale.** Hardstanding 62 × 52 m, compound 126 × 68 m inside the fence, site box
   174 × 148 m. The vision board guessed 32 × 28 m; that is too small to hold the yard the
   density bar asks for, so I made it twice the size.
2. **The slab module is 3600 mm**, three times the industry's 1.2 m. Invented here.
3. **Headframe height 11.6–13.4 m**, seeded. The vision board guessed 9.4 m to the deck.
4. **Shaft depth 40 m** in the visible geometry. The board notes three different numbers
   for this in the repo and none is decided.
5. **The pit-head is fenced, with one gated haul road from the west.** Nothing says it is.
6. **The training course is inside the perimeter fence**, adjacent to the yard on the east
   flat. The board put it outside.
7. **The course is my corridor grower**, 26 nodes, not `Corridor(54)`.
8. **Surface iron is brown-black rust, not the cave's near-black submerged iron.**
   `ART-DIRECTION` §5.2 forbids orange rust for *drowned* iron; the surface is above the
   waterline and reads dead without a brown. This is a deliberate deviation and the most
   likely thing in here to be wrong.
9. **The players' register is `BONE` + light grey + galvanised + aluminium, with amber
   (never red, never cyan) for pilots and hazard.** Amber is not in `palette.py`.
10. **Twelve machines are visible in the yard at once**, including one wreck on a trestle.
    Nothing says how many machines a team keeps.
11. **Charge is by pedestal-and-cable, five bays.** Inherited from the board's guess 8.
12. **The gantry and lifting frame exist**, i.e. machines are handled by a hoist rather than
    carried. Invented here to make servicing plausible.
13. **A battery skid, a genset, tanks, a transformer pen and a comms mast** — the site has
    its own power and its own uplink. Invented.
14. **Overcast is the default and dusk is a state.** §5 argues it; it is still a proposal.
15. **The sky is a soft directional at 4.5° angular size in the shaft's colour, plus a
    procedural sky**, not a physically diffuse dome. A cheat that buys contact shadows.
16. **Rain is 14 000 GPU particles following the camera** — a look, not a simulation.
17. **The spoil tip profile is quadratic in squared distance**, which makes domes rather
    than the cones a real tip makes. Cheaper, and wrong.
18. **`g_wet` is 0.30 even in "dry" overcast.** It never fully dries here.
19. **Twenty-two yard cluster kinds at p = 0.78 on a 2.35 m lattice** — the density
    numbers are tuned by eye against the designer's note, not against anything.
20. **Nothing is at stake on the surface and no rival is present**, following the board's
    guess 3. If the pit-head is shared, the layout changes shape.
21. **Circulation is six hand-written polylines.** A real generator would derive walkways
    from the station list and the gate, not list them.
22. **The site has a perimeter fence at all**, and it is corrugated hoarding rather than
    mesh. Invented here, and it is doing a lot of work in the silhouette.
