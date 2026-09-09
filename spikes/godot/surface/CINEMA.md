# The cinematic layer on the pit-head — the camera rig and the post stack

2026-09-09. `spikes/godot/surface/`, Godot 4.7.2, Forward+, Vulkan, RTX 3080 Laptop.
A port of `spikes/godot/cave/CINEMA.md` and the four files it describes.
Spec: `docs/TRAILER.md` §3 (shots 2–7, 12–14, 28), §8 (the camera), §9 (the lens and the grade).
Nothing outside `spikes/godot/surface/` was modified. Nothing was committed.

---

## 0. The short version

| | |
|---|---|
| **What is the site anchor?** | A **named place in the site plan** plus an offset in that place's own frame: `{"at": "collar", "a": 6.0, "o": -2.0, "u": 1.60}`. `a` is metres along the place's axis, `o` metres right of it, `u` metres above the ground there. The cave names a station on a drive; a pit-head has no drive, it has a collar, five buildings, nine zones, six walkways, a haul road, four stations, twelve columns and a 26-node course, and `layout.gd` already knows where all of them are. §2. |
| **Do the pit-head's trailer shots execute?** | **Nine of the ten: 2, 3, 4, 5, 6, 7, 12, 13 and 28.** Shot **14** (descending the shaft) is rejected, correctly, on four rules at once — and its rejection is the most interesting result in this document, because the frames it would have shipped are *right*. §7.2. |
| **Biggest thing found in the camera** | **The cave's swept test rejects 100% of low shots on a site.** `cast_motion` returns 0 whenever the shape starts in contact, and every floor- and machine-height camera on hardstanding starts in contact. §4.3. And **the site's own weakest scale is where the camera cannot stand**: at floor height, 0 of 121 sampled positions on the muster square accept a camera body. §7.4. |
| **Biggest thing found in the post** | **Godot's glow high-pass never fires on this site at the cave's settings, and the reason is not the threshold.** `glow_hdr_scale` is a *width*, 2.00 by default, and the HDR probe says the pit-head's entire scene radiance is 0.03–0.9. The knee was wider than the range. §6.2. |
| **The grade bug** | **Not inherited, and proved by reproducing it.** `--cinema=lutbug` renders the same frame with the correct `(i+0.5)/N` table and with the cave's `i/(N−1)` bug: −1.13% versus −2.59%. §6.9. |
| **Effects that survived** | **9 of the 10** in §9's table. |
| **Effects cut** | One: **lens dirt**, built here because the cave explicitly handed it to the surface, measured, and cut on the spec's own words. §6.10. |
| **Cost of the whole stack** | ~4.8 ms of a 23.6 ms frame **on a GPU throttled to 780 MHz of 2100 with 64% external utilisation.** Do not read that as an absolute. §8. |
| **Does the exposure contract hold?** | Yes, and emphatically: **0 of 27 frames over the 3% blown ceiling, and every single frame's mean goes DOWN.** Nothing was brightened to make it read. §8.1. |

---

## 1. What was ported, and what it cost to port it

Four files came across from `spikes/godot/cave/`:

| cave | pit-head | verdict |
|---|---|---|
| `cinema.gd` | `scripts/cinema.gd` | rules unchanged; the **anchor**, the **ground query**, the **swept test**, the **crane rule**, **rule 8** and the **collision build** all rewritten. §2–§4. |
| `postfx.gd` | `scripts/postfx.gd` | structure unchanged; the **grade owns only the LUT**, `tonemap_exposure` is never written, and bloom/CA are retuned. §5, §6. |
| `lens.gd` | `scripts/lens.gd` | verbatim plus two floats for the dirt and one flag for the HDR probe. |
| `lens.glsl` | `lens.glsl` | optics verbatim; dirt and HDR probe added. |
| `shots_cinema.json` | `shots_cinema.json` | rewritten in the site anchor. |
| `lumcheck.py` | `lumcheck.py`, `paircheck.py` | rewritten: §8.1 explains why the cave's thresholds cannot be applied to a daylight frame. |

**Everything in TRAILER §8 that is a RULE came over unchanged and was not renegotiated**: the
0.35 m body sphere, 0.40 m of near-plane clearance, the four height bands, the 0.15–2.50 m
travel window, the 1.2 m/s peak, smootherstep easing, one `lens_mm` per shot with no way to
write two, `"ease": "linear"` as a validation failure, and the principle that a failure is
**reported with the number that caused it and never repaired**.

### 1.1 One process note that cost a measurement

`run.sh` exists because **a Godot game run does not reimport `.glsl`** — it loads the cached
SPIR-V from `.godot/imported/`. An edit to `lens.glsl` is therefore silently ignored until the
editor has been run over the project once, and any measurement taken in between is a
measurement of the *previous* shader. That produced one entirely bogus HDR probe table before
it was caught (the numbers were 16× too high and self-consistent, which is the worst kind of
wrong). Every run in this document went through `run.sh`, which compares mtimes and reimports.

---

## 2. The site anchor, which is the design question this port had to answer

### 2.1 What the cave's anchor is, and why it does not survive the move

```json
{"st": 116, "r": 0.10, "u": 0.42, "f": 1.60}
```

`st` is a station index on the main drive, `f` is **arc length along it**, `r` is metres right
of the centreline and `u` is metres above the floor *there*. It works because **a drive is
one-dimensional**: there is exactly one thing to be "along", and the whole cave is that thing
plus branches.

A pit-head is not one-dimensional and it has no drive. `layout.gd` — the integer half of the
generator, the half that becomes `blindside-gen` — describes it as a **plan**: a shaft
rectangle at the origin, a headframe over it, five building footprints each tagged `old` or
`new`, nine functional zones each with a `kind`, two hardstanding rectangles, six walkway
polylines, a haul road, a fence with a gate, twelve lighting columns, two masts, a gantry, ten
stores ranks, four **stations** (points a machine plugs into, each with a yaw) and a 26-node
course graph.

### 2.2 The site anchor

```json
{"at": "z:charge_row", "a": 7.50, "o": 3.20, "u": 1.60}
```

* **`at`** names a **place in the plan**.
* **`a`** is metres **along that place's own axis** — the cave's `f`.
* **`o`** is metres **right of that axis** — the cave's `r`.
* **`u`** is metres **above the ground at that point** — the cave's `u`, unchanged and for the
  cave's reason: the yard is graded flat and everything outside the pad is not.

A place's **axis** is the direction the thing is laid out in, which is the only choice that
makes `a` mean the same thing for a 16 × 17 m container row and a 12 × 4 m charge row:

| place | origin | axis |
|---|---|---|
| `collar`, `headframe` | the shaft, at the world origin | +X, along the 2400 mm side of the collar |
| `gantry` | mid-span of the rail over the service bay | +X |
| `gate` | the gate span in the west fence | +X, into the site |
| `b:<kind>` | a building footprint's centre — `winding_house` `boiler_house` `fan_house` `service_bay` `store` | its **long** side |
| `z:<kind>` | a zone rectangle's centre — `charge_row` `container_row` `tank_farm` `spares` `drums` `scrap` `pallets` `transformer` `muster` | its long side |
| `s:<kind>` | a station — `listening_post` `bench` `cradle` `course_root` | **the station's own yaw**, because these are the only places in the plan that carry a facing, and it is the facing a machine adopts |
| `road@<t>` | fraction `t` of **arc length** along the haul road | along the road |
| `walk<i>@<t>` | the same, on walkway `i` | along the walkway |
| `course:<n>` | course node `n` | along its edge to its parent |
| `col<i>`, `mast:<kind>`, `spoil<i>` | a lighting column, a mast, a spoil tip | +X |

`road@t` and `walk<i>@t` are the one idea that came straight across: the cave measures `f` as
arc length because "a drive is a curve; a distance down it is measured along it", and that is
equally true of a haul road that bends round the collar apron. The only change is that a
**fraction** is a better handle than an index when the polyline has four points instead of two
hundred.

An anchor may still be a plain world point `[x, y, z]`, as in the cave. Exactly one shot uses
that, and it is the one that fails: §7.2.

### 2.3 Why this is more portable than the cave's, not less

The cave's own §10 lists as a limitation: *"Every station index in `shots_cinema.json` … They
are seed-7 specific. Change the seed and the shot list needs re-scouting."*

Change the seed here and **the collar is still the collar, the service bay is still the service
bay, and the charge row is still the charge row**, because those are plan *fields* rather than
indices into a generated polyline. The seed moves the headframe's spread, the spoil tips, the
column positions and the course graph; it does not rename a zone.

Three place kinds are seed-fragile and are marked as such in the source: `course:<n>`,
`col<i>` and `spoil<i>` name an index into a generated list. Two of the ten shots use
`course:<n>`. That is the honest residue.

### 2.4 The vocabulary is dumpable, which is how the shots were authored

`--cinema=places` resolves every place and every anchor in the shot list and prints origin,
axis and ground height (`shots/cinema/places.txt`). Authoring against that rather than against a
guess is the difference between one iteration and six.

---

## 3. Running it

```
./run.sh --cinema=validate     validate every shot            shots/cinema/validation.txt
./run.sh --cinema=places       the anchor vocabulary, resolved
./run.sh --cinema=scout  --shot=NAME   sweep the shot's own frame for places it could stand
./run.sh --cinema=scoutf --shot=NAME   the same, 0.4 m grid
./run.sh --cinema=probe  --shot=NAME   what, by name, is in the way
./run.sh --cinema=seq          the executing shots as image sequences
./run.sh --cinema=pairs  --shot=NAME   before/after for every effect, cumulative, one pose
./run.sh --cinema=stack        the whole stack on and off, three frames
./run.sh --cinema=tune  --shot=NAME    the bloom, vignette and dirt sweeps
./run.sh --cinema=hdr          the scene-radiance probe
./run.sh --cinema=lutbug       the grade LUT, built right and built wrong
./run.sh --cinema=fail         the rejected shots and the frames they would have shipped
./run.sh --cinema=contract     the frames lumcheck.py measures, AgX-only and full stack
./run.sh --cinema=cost         leave-one-out timing, interleaved
--fx=a+b+c                     any subset of the stack, or `all` / `none`
```

`--cinema=scout` is the surface's version of the cave's station sweep, and the cave's warning
applies unchanged: **it is a location scout, not a repair.** It shifts the whole *move* by
`(da, do)` in the place's own axes, leaves the *look* where it is, and prints one letter per
offset — `.` accepts, `b` body, `c` clearance, `h` height, `u` buried, `m` no crane mount, `t`
travel, `s` speed. The shot list is still written by hand against the answer and the validator
still governs what ships.

`--cinema=probe` is new and it earned its place three times: it prints the contact points of
the body query and **names the MultiMeshInstance3D bin each one came from**. "Something is in
the way at 0.51 m" is a fact you cannot act on; "`box_stone_s`, `casebox_kitgrey_s` and
`channel_alu_p-1_0` are in the way, with contacts at y = 0.50–0.62" is a fact you can, and it
took two of the three re-framings from guesswork to one edit. It also named the obstruction that
rejected `t28` — `angle_iron_s`, with body contacts at 2.40–2.46 m out over the collar.

---

## 4. The camera rig, and the four things that had to change

### 4.1 Collision — the buckets already draw the line the cave drew by hand

The cave lists 19 kit parts a camera body collides with and excludes loose scatter, because
"a 40 mm ballast chip is not an obstacle, and 19 015 collision shapes to pretend it is would
cost more than the entire post stack."

The surface already has that split made for it, by the renderer. `Batcher` bins every instance
into **SITE** (silhouette structures), **PROP** (walking-distance objects) and **DETAIL**
(underfoot: gravel, chippings, weeds, dropped fixings, litter — no shadow, culled at 55 m). So
the rule needs no list: **SITE and PROP collide, DETAIL does not.**

```
129 072 ground triangles + 4 486 instances / 114 222 triangles, built in 569 ms
```

**One thing had to change and it is a Godot fact worth writing down.** The cave gives every kit
instance its own `CollisionShape3D` sharing a cached shape — 951 nodes, fine at 951. Doing that
here produces tens of thousands of children on one `StaticBody3D` and **the physics server is
quadratic in that**: the first attempt had not finished building after five minutes. The fix is
to transform the triangles on the CPU and bake **one `ConcavePolygonShape3D` per
MultiMeshInstance3D** — ~700 shapes instead of ~20 000 nodes, identical geometry to the query,
and `Transform3D * PackedVector3Array` does the transform natively rather than a vertex at a
time in GDScript. 569 ms.

### 4.2 The ground query — the raycast is wrong on a site, and visibly so

The cave finds the floor an anchor is measured from with a downward raycast, because the swept
shell is noise-displaced on top of the station datum. On a site that method is wrong, and the
first `--cinema=places` dump said so in one column:

| place | what the cave's raycast returns as "ground" | what it actually hit |
|---|---|---|
| `collar` | **11.18 m** | the sheave deck, eleven metres up |
| `b:service_bay`, `gantry`, `s:bench` | **6.27 m** | the bay roof |
| `s:cradle` | **6.09 m** | the same roof |
| `s:course_root` | **2.25 m** | the top of the course's root post |
| `b:fan_house` | **10.67 m** | a catenary |

`u` would then mean "metres above whatever happens to be standing here", which is not a height
rule, it is a hazard — and it is a hazard that exists *only* on a site, because a drive's back
is a metre and a half over your head everywhere and a pit-head has a headframe.

The pit-head does not need the raycast because it already has the answer.
`Ground.height(L, x, z)` is the site's own contract — *"the height every other dressing file
must place against: the layout height plus the dressing relief. Anything that calls
`L.ground_mm` directly and not this will float by up to 67 mm"* — and it is exactly the surface
the ground mesh is built from. **An anchor's `u` is measured from the ground, and the ground
means the ground.**

The raycast survives where it belongs: `floor_under()` still measures the **height rule**
against what is rendered, so a camera authored on top of a crate fails its height band instead
of quietly standing on the crate.

*(One residue, and it cost one rejection: the analytic surface and the 0.5 m triangulation of
it differ by up to ~20 mm in concave spots, so an anchor authored at exactly 0.40 m — the top
of the floor band — can measure 0.402 m and fail. Author inside the band, not on it.)*

### 4.3 The swept test — `cast_motion` rejects every low shot on a site

This is the change that would have silently killed the whole low-camera half of the trailer.

The cave sweeps the body with `cast_motion`, which returns the safe fraction of the motion.
**`cast_motion` returns 0 whenever the shape starts in contact.** On a site every floor- and
machine-height camera starts in contact: a 0.35 m sphere plus a 0.05 m query margin, centred
0.36 m above hardstanding, is 40 mm into the ground before it moves. So the cave's swept test
rejects 100% of low surface shots, with the message *"swept body hits geometry at t=0.00"*, and
it rejects them **for standing on the floor**.

That is the same collision between TRAILER §8's two rules that the cave's §4.2 resolves for the
*overlap* test, and the resolution has to apply here too: a contact in the bottom 0.18 m of the
sphere is the rig standing, not the camera flying through. `cast_motion` cannot express that,
because it has no way to ask whether the blocking contact was ground.

So the sweep walks the path with **the same overlap test that already carries the ground
exemption**, at 40 mm steps against a 700 mm sphere. It cannot miss anything, it costs about 60
extra queries for a 2.5 m move, and it is exact rather than approximate. **This is a
correctness fix to the cave's rig as well as a port change**, and it should go back.

### 4.4 The crane rule — there is no ceiling under a sky

The cave's crane rule is "≥ 2.00 m with at least 0.5 m of headroom to hang from", measured with
an upward raycast. On a site under open sky an upward ray hits nothing, so that rule **passes a
camera hovering nine metres over an empty yard** — precisely what §8 forbids ("Nothing hovers at
2.5 m in a passage for no reason").

The surface version asks the plan instead: a crane shot must have a **structure whose top is at
or above the lens, within `CRANE_REACH` = 12 m horizontally**. The headframe, the gantry, a
lighting column, a mast, a pole and a building gable are all things a rig hangs off, and they
are all in the plan. The validator prints which one:

```
t13_collar_above    crane hangs off the headframe at 6.5 m
t12_course_alone    crane hangs off a lighting column at 9.1 m
t28_extraction_window  crane hangs off the headframe at 6.7 m
```

12 m is a guess (§10).

### 4.5 Rule 8 — "am I inside a solid", asked directly instead of by proxy

The cave's rule 8 is "the camera must have an unobstructed line to the centreline of the drive
it is authored against", and it exists because a triangle **soup** is not a solid: a sphere
sitting entirely inside the rock touches no triangle, so the overlap test reports it clear. That
hazard is identical here — every mesh in the kit is an open shell.

But there is no centreline on a pit-head, and the cave's own §10 flags the formulation as *"a
proxy [that] would misjudge a shot authored inside a chamber that the drive centreline cannot
see"*. A site is all chamber.

So the test is made direct: fire six axis rays 2 m and ask whether the camera is looking at the
**back** of a face in every direction. A camera in the open yard sees the ground's front face
below it and nothing else; a camera under the service bay roof sees one back face above it; a
camera authored inside a container sees six. Five of six is the threshold. Nothing about a
passage or a room is assumed.

**It is not good enough, and the deliberate failure proved it.** A camera standing inside a
*roofless* ruin — which four of the five buildings on this site are — escapes upward to the sky
and finds at most two back faces. §7.1. The rule catches a container and misses a winding house.
The fix the pit-head can afford and the cave could not is a containment query against the
building rectangles the plan already holds; I have not written it.

Also worth stating plainly, because it is the reason rule 8 exists at all and it reproduces
here: **the shell is a triangle soup and a body entirely inside a solid reports clear.**
`fail.txt` now says so out loud when it happens.

### 4.6 What the validator checks

| # | rule | threshold | changed from the cave? |
|---|---|---|---|
| 1 | swept body | 0.35 m sphere, 0.05 m margin, 40 mm path step, ground band 0.18 m | **method**, §4.3 |
| 2 | near clearance | 0.40 m of empty frustum, 9 rays, ground exempt | no |
| 3 | height | floor 0.04–0.40 · machine 0.28–0.56 · eye 1.38–1.82 · crane 2.00–30.00 | **crane**, §4.4 |
| 4 | travel | 0.15–2.50 m | no |
| 5 | ease | linear is a failure | no |
| 6 | speed | peak ≤ 1.2 m/s | no |
| 7 | lens | 18–24 / 35–50 / 85+; anything between is a warning | no |
| 8 | not buried | ≥ 5 of 6 axis rays hitting a back face is a failure | **method**, §4.5 |
| — | *(new warning)* | a shot with zero travel warns, because TRAILER §7 requires a move on **every** surface shot: nothing on this site moves, and a static wide would say so | new |

Lensing and depth of field are unchanged: a 16:9 crop of a 36.0 × 20.25 mm full-frame sensor,
a 0.030 mm circle of confusion, and near/far limits derived from the hyperfocal distance.

---

## 5. The pictures

Everything is 1920 × 1080, in `shots/cinema/`.

| where | what |
|---|---|
| `seq/<shot>/NNN.png` | the nine executing trailer shots, 24 frames each |
| `pairs/<shot>/NN_<effect>_{off,on}.png` | before/after for every effect, **cumulative in TRAILER §9's order**, from one identical camera, for an overcast pose (`t02`, `t05`) and a rain pose (`t28`) |
| `stack/<shot>_{off,on}.png` | the whole stack on and off at three frames in three registers: iron against sky, the brought kit at working distance, and rain |
| `tune/bloom_t*_s*.png` | the bloom threshold × soft-knee sweep |
| `tune/vig_k*.png`, `tune/dirt_*.png`, `tune/mblur_*` | the vignette, dirt and motion-blur sweeps |
| `hdr/<shot>.png` | the scene-radiance probe, one per shot |
| `lutbug/grade_{off,on_correct,on_halftexel_bug}.png` | §6.9 |
| `fail/*.png` | the two rejected shots: start, last legal, first rejected, end |
| `contract_{off,on}/` | the 27 frames `lumcheck.py` measures |
| `places.txt`, `scout_*.txt`, `probe_*.txt`, `validation.txt`, `cost.txt`, `sequences.txt` | the machine-readable versions |

---

## 6. The post stack, effect by effect

TRAILER §9's table, in the order given. Costs are **leave-one-out deltas from the full stack**,
interleaved, 56 frames a block, 3 blocks, median of medians, at `t05_charge_line` t = 0.55,
1920 × 1080. **Read §8 before reading any of them.**

### 6.0 The measurement that made the rest of this section possible

Bloom's threshold and the dirt's "strongest sources" gate are both quoted in units of **scene
radiance**, and the cave's numbers were measured against one 54° lamp in a black room. Nobody
had ever measured what range the pit-head's radiance occupies. `--cinema=hdr` writes
`luminance / 16` through the LINEAR tonemapper so it can be read straight off the PNG:

| shot | light | max | p99.9 | p99 | p90 | median |
|---|---|---|---|---|---|---|
| `t02_headframe_sky` | overcast | **9.19** | 0.97 | 0.33 | 0.28 | 0.209 |
| `t03_yard_drift` | overcast | 2.50 | 1.14 | 0.58 | 0.33 | 0.109 |
| `t05_charge_line` | overcast | 0.60 | 0.46 | 0.38 | 0.35 | 0.118 |
| `t06_bench_machine` | overcast | 0.81 | 0.51 | 0.46 | 0.33 | 0.092 |
| `t07_course_posts` | overcast | 0.84 | 0.38 | 0.37 | 0.33 | 0.062 |
| `t12_course_alone` | overcast | 0.46 | 0.40 | 0.40 | 0.37 | 0.092 |
| `t13_collar_above` | overcast | 0.31 | 0.28 | 0.25 | 0.18 | 0.035 |
| `t04_rain_macro` | rain | 0.11 | 0.08 | 0.07 | 0.06 | 0.041 |
| `t28_extraction_window` | rain | 0.18 | 0.11 | 0.09 | 0.04 | 0.007 |

**The whole site lives between 0.03 and 0.9, the overcast sky sits at 0.33, and the only thing
above 1.0 anywhere is the sun glow through cloud.** Every number in §6.2 and §6.10 falls out of
that table.

### 6.1 Tonemap and exposure — kept, unchanged, and deliberately not touched

AgX, as `weather.gd` left it after the photoreal pass. **`tonemap_exposure` is never written by
this layer.** It belongs to the lighting preset — 0.70 overcast, 1.45 rain, 1.45 dusk — and the
cave's `postfx.gd` pins it to 1.0. Doing that here would have been a two-stop exposure change
wearing a port's costume, which is exactly the shape of the LUT bug and exactly what
ART-DIRECTION §2.9 exists to catch.

`CameraAttributesPractical` arrives with an exposure multiplier and an auto-exposure. Both are
pinned: `auto_exposure_enabled = false`, `exposure_multiplier = 1.0`.

### 6.2 Bloom / glare — **kept, retuned by 4× and 13×, and it has a real subject here.** 1.05 ms

The cave kept bloom at threshold 1.60 with Godot's default `glow_hdr_scale` of 2.00 and measured
it changing 0.06% of the frame, "because nothing in this cave is above threshold". Ported
unchanged to the pit-head it changed **0.000%** of every overcast frame — max delta 0 code
values — at every threshold from 0.8 to 6.0.

The threshold was not the whole problem. **`glow_hdr_scale` is a width, not a ratio**: Godot's
high-pass is `smoothstep(threshold, threshold + scale, luminance)`, so a 2.00-wide knee on a
scene whose entire radiance range is 0.03–0.9 means *nothing ever reaches full weight*. The
sweep, at `t05_charge_line`, intensity 0.90:

| threshold | knee | pixels changed | changed > 2 codes | max delta | mean |
|---|---|---|---|---|---|
| 0.30 | 0.15 | 3.72% | 0.93% | 22 | +0.22% |
| 0.30 | 0.35 | 2.03% | 0.01% | 7 | +0.04% |
| 0.30 | **2.00** | **0.09%** | 0.00% | **1** | +0.00% |
| **0.40** | **0.15** | **0.00%** | 0.00% | **0** | +0.00% |
| 0.55 | any | 0.00% | 0.00% | 0 | +0.00% |

and at `t02_headframe_sky`, whose frame contains the polished sheave and the caged ladder:

| threshold | knee | pixels changed | changed > 2 codes | max delta | mean |
|---|---|---|---|---|---|
| 0.30 | 0.15 | 1.75% | 0.92% | 182 | +0.57% |
| **0.40** | **0.15** | **1.34%** | **0.56%** | **180** | **+0.31%** |
| 0.40 | 2.00 | 0.42% | 0.08% | 72 | +0.02% |
| 0.55 | 0.15 | 0.85% | 0.30% | 176 | +0.15% |

**Shipped: threshold 0.40, knee 0.15, intensity 0.70.** At those numbers the sky at 0.33 and the
concrete are untouched, and the only thing that blooms in the whole set is a 2 717-pixel region
around the **bearing-steel sheave and the caged ladder rail** — ART-DIRECTION §5.2's *"still in
use is polished bright by the work itself"*, which is the one class of surface the direction
says should be the brightest thing in the world. `tune/bloom_t0.40_s0.15.png`.

That is TRAILER §9's discipline satisfied on its own terms: *"Real glare is tight and bright,
not a soft haze over everything. If bloom is visible on rock, it is too strong."* Every setting
low enough to catch the sky produced the haze; the setting that spares the sky produced the
glare.

**It is idle in seven of the nine shots**, costs 1.05 ms — the second most expensive thing in
the stack — and it is the effect I would make a per-shot switch rather than a global. The mask
already supports that (`--fx=`).

### 6.3 Depth of field — kept, 2.77 ms, the most expensive thing in the stack

Unchanged arithmetic: hyperfocal from the focal length and the T-stop, near and far limits of
acceptable sharpness handed to `CameraAttributesPractical`, round iris rather than Godot's
default hexagon, `dof_blur_amount` derived from the entrance pupil and clamped at 0.14.

**The daylight hazard is TRAILER §9's own discipline line and it is worth stating why the
arithmetic already prevents it.** A far-field blur on a wide site shot *is* tilt-shift, and
tilt-shift on an industrial yard is the most recognisable "this is a model" cue there is. A
21 mm at T2.8 has a hyperfocal of 5.27 m, so every wide shot focused past that gets
`far = infinity` and the far blur switches itself off. Five of the nine shots are in that state
by arithmetic, not by taste; the validator prints it (`sharp 2.28 m to inf`).

It earns its keep on the close shots: `t06_bench_machine` at 50 mm T2.8 focused 2.45 m is sharp
from 2.27 to 2.66 m, so the machine on the work stand is sharp and the bench behind it is not.
On `t05` it changes 28.98% of pixels.

### 6.4 Motion blur — kept, camera only, 0.03 ms

Unchanged: reconstruct world position from depth, reproject through the previous frame's
view-projection, integrate 9 taps at a 180° shutter. The rig hands the effect the previous
**shot** frame's transform at the true 1/60 s spacing, so the blur in a 24-frame sequence is the
blur the finished 60 fps shot will have.

Per-object motion blur is still not built and the cave's reason survives the move and then some:
it measured the velocity pass at 1.31 ms before a single blur tap, for a scene in which nothing
but the camera moves — and `NOTES.md` §7.4 for this spike is *"Nothing moves at all."* The only
moving things on the pit-head are the rain particles, which get the camera's velocity instead of
their own and are already smeared by their own alpha.

It changes 18–47% of pixels depending on the shot. On `t28`, a 3-second shot, it is 47.45%.

### 6.5 Film grain — kept, 0.17 ms, and daylight makes it *more* interesting, not less

Unchanged sensor model: `sigma = sqrt(signal / full_well) + read_noise`, applied to the linear
signal before AgX. Measured as the standard deviation of (on − off) by output tonal band:

**`t05_charge_line`, overcast, `tonemap_exposure` 0.70**

| band | share of frame | sigma | relative to signal |
|---|---|---|---|
| near-black 0–4 | 1.1% | 1.90/255 | 96% |
| toe 4–20 | 9.4% | 2.48/255 | 22% |
| mid 20–80 | 43.4% | 1.68/255 | 3.5% |
| high 80+ | 46.1% | 1.27/255 | 1.1% |

**`t28_extraction_window`, rain, `tonemap_exposure` 1.45**

| band | share of frame | sigma | relative to signal |
|---|---|---|---|
| near-black 0–4 | 25.6% | 2.15/255 | 215% |
| toe 4–20 | 17.1% | 4.07/255 | 38% |
| mid 20–80 | 43.5% | 3.55/255 | 7.8% |
| high 80+ | 13.7% | 3.47/255 | 3.5% |

Two things fall out, and neither is in the code:

* **TRAILER §9's "grain in the shadows, not in the highlights" is the tone curve, not a mask.**
  There is no luminance mask anywhere in the shader and the toe carries twenty times the
  relative noise of the highlights.
* **The rain preset is a pushed sensor and it looks like one.** Its exposure is 1.45 against
  overcast's 0.70, and its grain is correspondingly about 1.6× coarser in every band. That is
  what opening up two thirds of a stop does to a real camera, and it arrived for free.

**One thing to be careful of, found by looking at 1:1 crops.** The white speckle on the
headframe's ironwork is **not grain** — it is present in `04_grain_off.png`. It is specular
aliasing on 1–2 pixel lattice members at MSAA 2×. That matters for §6.7.

### 6.6 Vignette — kept at `vig_k = 0.55`, 0.13 ms, and it is the entire exposure story

**There is still no amount knob.** The falloff is the cos⁴ law evaluated from the shot's own
focal length against the 36 × 20.25 mm frame, so a 21 mm darkens its corners and a 50 mm barely
does. The one free parameter is how much of the theoretical cos⁴ survives a real lens design.
The sweep at `t02` (21 mm):

| `vig_k` | pixels changed | changed > 2 codes | max delta | frame mean |
|---|---|---|---|---|
| 0.35 | 91.7% | 54.8% | 20 | **−8.44%** |
| **0.55** | 94.1% | 68.6% | 34 | **−13.27%** |
| 0.80 | 95.6% | 76.8% | 57 | **−19.28%** |

**It is by a wide margin the largest single change the stack makes to the frame**, and it is a
function of focal length and nothing else, which the contract measurement confirms exactly:
the stack costs **−6.3%** of the mean on the 50 mm shot and **−18 to −20%** on the three 21 mm
shots. §8.1.

The cave's finding — *"the vignette is not free in the currency the contract is denominated
in"* — reproduces here at two to three times the magnitude, because the surface uses more wide
lenses. **And the surface can afford it, which the cave could not**: a daylight frame is legible
over 55–72% of its area against a floor of 3%, so losing 0.4 to 5 points of legible fraction
changes nothing. The cave's request for a ruling stands; the pit-head is not where it bites.

### 6.7 Chromatic aberration — kept, **halved**, 0.46 ms

Unchanged physics — lateral dispersion, zero on the axis, growing with radius, scaled down with
focal length — but the corner figure comes down from the cave's **1.9 px to 1.0 px** at a 21 mm.

Not because the optics changed. Because the **subject** did. The cave points a 21 mm at rock,
which is low-frequency. The pit-head points it at a headframe, which is a lattice of 1–2 pixel
members against a bright sky and is the highest-frequency thing in the game. Those members
already carry specular aliasing (§6.5), and **a 1.9 px colour split applied to a 1 px aliased
edge does not read as a lens, it reads as chroma noise** — visible as red/blue confetti in the
middle third of `pairs/t02_headframe_sky/06_ca_on.png` at the old value. At 1.0 px the fringe is
still there at the frame edge and stops being confetti in the middle. TRAILER §9's "a pixel or
two" is satisfied either way; this is the half that survives being pointed at ironwork.

The real fix is more samples, and that is a frame-budget decision outside this layer.

### 6.8 Lens distortion — kept, 0.26 ms, and still the first thing I would cut

Barrel, `r' = r(1 + k·r²)`, overscanned so the corner maps to the corner. `k = −0.009` at 21 mm
falling to zero by 32 mm. At 35 mm and 50 mm it changes **0.00% of the frame with a max delta of
1**, which is correct and is also the argument for cutting it: two thirds of the shot list is at
a focal length where it does nothing at all. At 21 mm it changes 46% of pixels with a max delta
of 199 — but that is a one-pixel resample on a high-contrast edge, not a visible barrel.

### 6.9 Colour grade — kept, ~0.00 ms, **and the bug was not inherited**

A 32³ LUT generated at runtime; not one imported asset in this project.

**The port's first obligation was to prove it did not inherit the cave's 14.3% exposure cut, and
"it looks fine" is not a proof — the cave's own words are that the bug "did not look like a bug,
it looked like a moody grade".** So `--cinema=lutbug` renders the same frame three times, with
the LUT built correctly on `(i + 0.5)/N` and with it built the cave's wrong way on `i/(N − 1)`:

```
grade OFF                mean 0.09962
grade ON, (i+0.5)/N      mean 0.09849    -1.13%   <- the port
grade ON, i/(N-1)  BUG   mean 0.09704    -2.59%   <- the cave's bug, reproduced
```

Two conclusions:

1. **The port is clean.** −1.13%, in line with the cave's post-fix +1.1%, and not −14.3%.
2. **Daylight would have hidden it.** The same bug costs 1.5 percentage points here against
   14.3 in the cave, because the half-texel offset is a fixed shift *down the input axis* and
   its proportional cost is largest where the signal is smallest — and nine-tenths of a cave
   frame is near-black. **The cave was the right place to find that bug and the surface would
   have shipped it.** That is worth remembering the next time a check is skipped because a
   daylight frame looks fine.

**What the grade does, and one number that did not come across.** The deepest shadows lose
chroma, as a sensor and a print both do — same threshold as the cave. But the cave also warms
*the top two stops* by 2%, and in the cave the top two stops are the lamp pool on iron. **On the
surface the top two stops are the sky**, and ART-DIRECTION §2.1 gives the sky's colour to the
shaft — 12000 K, *"the only cold light, and the only daylight"*. Warming the highlights here
warms the one thing in the game that is not allowed to be warm, and it would undo the photoreal
pass's fight to get the frame's B:R from 1.30 to 1.01.

So the warm is masked off the top: it runs over the upper **midtones** (0.42–0.78, smoothstepped)
and falls back to nothing as the value approaches the sky. Measured on the pairs, the grade moves
B:R by 1.085 → 1.079 on the yard frame — *toward* neutral, not away.

There is still no cool shadow lift. ART-DIRECTION §9 forbids cyan anywhere in the world, and
cooling the shadows is how every other game arrives at cyan.

### 6.10 Lens dirt / streak — **built, measured, and CUT**

The cave cut this without building it, on the spec's own words, and wrote: *"If it appears
anywhere it belongs in `spikes/godot/surface`."* Two of the ten pit-head shots are rain shots,
so this pass had to answer it rather than defer it.

It was built: a screen-space field (because a mark on the glass does not move when the camera
does, which is the one thing that distinguishes dirt from anything in the world), stretched 4:1
vertically because a drop on a vertical front element runs down, gated on the maximum radiance
in a five-tap neighbourhood so it only fires near a strong source, and gated again on `g_wet`
so it is literally switched by whether it is raining rather than by a per-shot flag somebody can
forget.

**Then it was measured, and there is nothing for it to do.** At `t28_extraction_window` in rain,
across every threshold from 0.10 to 1.00 and every gain from 0.04 to 0.30:

| | pixels changed | max delta |
|---|---|---|
| all eight settings | 2.34 – 2.45% | 21 – 27 |

— which is **indistinguishable from the frame-to-frame jitter of the rain particles themselves**
(the same 2.4% appears between two identical captures). The reason is in the HDR table: the two
rain shots' entire radiance range tops out at **0.18 and 0.11**. TRAILER §9 says "only on the
strongest sources", and in a rain frame on this site *there are no strong sources* — the yard
floods are on at 0.55 energy in the rain preset, and neither of the trailer's two rain shots
contains one. Every gate low enough to make the dirt visible smears the whole frame, which is
the "easy to overdo" the spec warns about.

**Cut, on TRAILER §9's own last clause: "cut first if in doubt."** `dirt_gain` ships at 0.0, the
bit stays in the mask so `--fx=dirt` still works, and the sweep frames are in
`tune/dirt_*.png` as the evidence. **The frame that would justify it is a rain shot with a
flood in it, and the trailer does not have one.** It should be re-measured the day one exists,
and at dusk, where fourteen column floods and every amber pilot on the site are the brightest
things in frame.

---

## 7. Which trailer shots execute

`shots/cinema/validation.txt` is the machine-readable version.

| # | shot | lens | executes | note |
|---|---|---|---|---|
| **2** | the headframe against the sky | 21 mm T2.8 | **yes** | 1.25 m push in from machine height 0.42 m, 5 s, looking up at 41°. The head against sky with the pole-line catenary crossing it. |
| **3** | the yard, wide, lateral drift | 21 mm T4.0 | **yes** | 1.60 m lateral, 4 s, eye 1.72 m. Portal frames and rooflights, machines on painted bays, spoil tips behind. |
| **4** | rain on hardstanding, macro | 50 mm T4.0 | **yes** | 0.33 m creep, 4 s, floor 0.33 m, handheld 0.18°. **The weakest of the nine and the reason is the site, not the camera.** §7.4. |
| **5** | the charge line | 35 mm T2.8 | **yes** | 1.24 m push down the row, 4 s, eye 1.60 m. Five pedestals, amber pilots, machines docked, cables. |
| **6** | a machine on the bench | 50 mm T2.8 | **yes** | 0.72 m push, 4 s, handheld 0.24°. **Height rule changed from `machine` to `eye`, and that is a finding.** §7.3. |
| **7** | the training course | 35 mm T2.8 | **yes** | 1.40 m dolly down the corridor, 4 s, machine height 0.45 m, handheld 0.22°. Posts, a gate, the numbered plate, the machine. |
| **12** | the machine walks it alone | 21 mm T4.0 | **yes** | 1.30 m lateral, 4 s, crane 5.5 m off lighting column 8. |
| **13** | the collar from above | 21 mm T4.0 | **yes** | 1.14 m drift, 4 s, crane 4.6 m off the headframe. The collar and the cage seen through the headframe's own bracing. |
| **14** | descending the shaft | 21 mm T2.8 | **REJECTED** | **§7.2, and it is the most interesting result here.** |
| **28** | the extraction window | 21 mm T4.0 | **yes** | 1.13 m drift, 3 s, crane 3.2 m off the headframe, in rain. |
| — | `xfail_through_the_shed` | 21 mm | **REJECTED**, deliberately | §7.1 |

Shots 8–11 are the Phase 1 teaching view and are not this spike's.

### 7.1 The deliberate failure

`xfail_through_the_shed` is authored to fail: a 2.2 m push straight into the winding house's
west wall, which is the move a hand-flown camera makes when nobody is checking.

```
FAIL: body intersects geometry at t=0.28 (the 0.35 m sphere overlaps)
FAIL: frustum clearance falls to 0.01 m at t=0.47 (needs 0.40)
last legal t = 0.250, first rejected t = 0.281
   (and it reports CLEAR again after that: the shell is a triangle soup,
    so a camera fully inside a solid touches nothing)
```

`fail/xfail_through_the_shed_end.png` is what would have shipped: the camera standing inside the
winding house, in the middle of the 4.6 m flywheel and its stone bed, with the ruined parapet at
eye level all round it. It is a good-looking frame and it is a camera that has walked through a
masonry wall.

**And it found the same hole the cave's xfail found, in the surface's own rule 8.** At the end
pose the overlap test reports clear — a triangle soup is not a solid, so a sphere entirely
inside a building touches nothing — **and so does the buried test**, because the winding house
is *roofless*: the up-ray escapes to the sky, the down-ray hits the ground's front face, and
the piers are 600 mm wide with 4-pier openings punched through them, so at most two of the six
axis rays find a back face against a threshold of five. **§4.5's rule does not catch a camera
standing inside a ruin.** What caught this shot is the swept path, exactly as in the cave. If a
shot were authored to *start* inside a roofless building it would pass, and the surface's
version of rule 8 needs a better test than six rays — probably a containment query against the
building rectangles the plan already holds, which is a check the cave could not have written
and the pit-head can.

### 7.2 Shot 14 is rejected, the rejection is correct, and the frames are right anyway

This is the finding to take to the designer.

TRAILER §3 shot 14: *"Descending. Daylight climbing away up the shaft, the walls going past, the
12000 K disc shrinking."* Authored as written — the camera rides the cage from 0.8 m below the
collar to 8.8 m down — it is rejected on **four rules at once**:

```
FAIL: body intersects geometry at t=0.00 (the 0.35 m sphere overlaps)
FAIL: frustum clearance falls to 0.01 m at t=0.19 (needs 0.40)
FAIL: height 'machine' wants 0.28-0.56 m; the move runs 0.05-1.33 m above the ground
FAIL: travels 8.00 m; a shot that must go further is two shots (max 2.5)
FAIL: peak speed 3.00 m/s exceeds 1.20
```

**Every one of those is the rig working correctly, and every one of them is wrong about this
shot.** `fail/t14_descending_start.png` and `fail/t14_descending_end.png` are the proof: the
first is the headframe seen from inside the collar against the sky, and the second is nine
metres down the lined shaft with the cage a small lit rectangle far above. **That is the shot
the trailer describes, and the geometry to make it already exists in this spike.**

The rig cannot express it because **a shot's move is stated in world coordinates**, and TRAILER
§8's rules were written for a camera on a dolly on the ground:

* *"a shot that must go further is two shots"* is a rule about a camera **travelling**. A camera
  bolted to a descending cage travels 0 m in its own frame; the world moves past it.
* the **height rule** measures the lens above the ground. There is no ground inside a shaft.
* the **near-plane clearance** rule wants 0.4 m of empty frustum. A shaft is 2.4 × 2.0 m and the
  camera is looking up the middle of it at a wall 1.0 m away.
* the **speed cap** is 1.2 m/s. A cage does 3 m/s and that is what makes the descent read.

**What needs a ruling.** Either (a) the shot format gains a **mount** — a shot may declare that
it is carried by a moving thing, and travel, speed and height are then measured in the mount's
frame, which is also what shots 17 and 22 will need the day a machine walks; or (b) shot 14 is
accepted as an exception with its own rules, written down. I have not implemented either.
Nothing was moved until it passed: shot 14 sits in `shots_cinema.json` rejected, with its four
frames beside it, as the record of an authoring attempt that the rules refuse.

### 7.3 A machine on a work stand cannot be photographed from any justifiable height

Shot 6's first authoring was at `machine` height, 0.50 m, which is the machine's own eyeline and
the thematically obvious choice. The frame is `seq` frame 012 of that pass and it is a
rust-brown slab filling 60% of the picture: **the lens was under the top of the work stand.**

`props.gd` puts a machine being serviced on a cradle at 0.72 m above the pad, so its body sits
at about 0.9–1.1 m. TRAILER §8's four justifiable heights are floor (0.04–0.40), machine
(0.28–0.56), eye (1.38–1.82) and crane (≥ 2.00). **There is no band between 0.56 and 1.38 m**,
so a machine on a stand can only be seen from eye height, looking down at it.

Which is right, and it is right for a reason that is better than the rule: **a machine on a
bench is at a person's working height, and a person is who is looking at it.** Shot 6 is now an
eye-height 50 mm at 2.45 m, the machine is whole and sharp and the bench behind it is not, and
it is the frame the trailer asks for ("First time we see one whole"). The band gap is worth
recording anyway, because the next person to author a bench shot will hit it.

### 7.4 The pit-head's version of "only 10% of the drive will take a low camera"

The cave's scout found that only 16 of ~170 stations would accept a machine-height dolly, and
called that "a fact about the cave generator, not about the rig". The surface has the same fact
in a sharper form.

`--cinema=scout` on `t04_rain_macro`, a floor-height (0.36 m) shot, over an 11 × 11 grid at 1 m
spacing centred on the muster square:

```
0 of 121 offsets accept this shot
```

Every single one failed on the body, and the probe put the contacts at x ≈ −5.72, z ≈ 3.70–3.78,
y = 0.44–0.62 — which is one of the **four machines parked on painted bays on the muster
square**, whose centres `props.gd` puts at x = −9.10, −7.37, −5.63, −3.90 on z = 4.0. Moved to the collar→bay walkway —
swept clear ground that `layout.gd` explicitly forbids dressing to occupy — it was **still
0 of 121**, this time against `box_stone_s`, `casebox_kitgrey_s` and `channel_alu_p-1_0`, a
cable tray, with contacts at 0.50 m. The scout maps show that one as a hard east–west line: at
`t02`, every offset at `o ≤ 0.4` fails and every offset at `o ≥ 0.8` passes. Shots 2 and 4 both
had to be moved 1.0–1.4 m sideways to clear it. *(I did not chase which individual instance in
those bins it is; the bin name was enough to move the camera, which is the point of the tool.)*

**The honest statement is the cave's, inverted.** In the cave, 0.4 m is the height at which
rail, sleepers, spall and breakdown live. On the pit-head, 0.4 m is the height at which cable
trays, kerbs, trunking, cable ramps, dropped stock and — on the muster square — four parked
machines live. The yard is *denser* at 0.4 m than the cave is, and `NOTES.md` §7.3 predicted it:
*"The yard fill can still put a 1.2 m tyre stack in front of a camera … A real version wants
either a small clearance query the camera respects, or clusters that know their own
footprint."* It does; the camera now has that query, and the answer is mostly no.

That is also why shot 4 is the weakest of the nine. It is the trailer's only underfoot shot, and
`PHOTOREAL.md` §7.3 and `ORDER.md` §8.5 both already say that underfoot on swept hardstanding is
the weakest scale in this spike and is carried entirely by the ground shader. The shot now has a
painted bay edge, a slab joint and a machine's front feet in it, which is the best that framing
can do; what it does not have is standing water reading as water, visible rain, or aggregate
that reads as embedded rather than tiled. **No camera choice fixes that.**

### 7.5 Legal is not the same as photographable — again, and worse

The cave's §7.3 is the single most useful thing in it and it needed no adaptation. Four of the
nine shots were re-framed *after* they had passed every rule:

* **t03** passed with a stores rack one metre off the left edge whose shelved drums read as
  floating. Legal, and the first third of the frame was unusable.
* **t06** passed with the lens under a work stand (§7.3).
* **t12** passed with a lighting column running straight up the middle of the frame — because
  the crane rule had *correctly* told it to hang off that column, and the obvious place to hang
  off a column is directly above it.
* **t13** passed with a headframe leg 1.9 m from the lens taking a third of the frame.

The rig can make a shot correct. It cannot make it good, and on a site it is *more* likely to
produce a legal-and-bad frame than in a drive, because a drive has two walls and a pit-head has
eighty-five thousand objects. The workflow that actually works is the cave's:
**`--cinema=places` to author against numbers, `--cinema=scout` to find where a body fits,
`--cinema=probe` to name what is in the way, and then a person looks at the frame.**

---

## 8. The measurements, and what they are worth

**The machine was not quiet and I am not going to pretend it was.** `tasklist` found no other
Godot process at the start of the timing run, but `nvidia-smi` reported the GPU at **80 °C,
clocked at 780 MHz against a 2100 MHz maximum — a 2.7× throttle — with 64% utilisation from
other applications.** `PHOTOREAL.md` §4.4 and `ORDER.md` §7 both already record that this
laptop's run-to-run drift on an identical build is larger than anything being measured.

So: **every number below is a delta between interleaved blocks taken seconds apart, and none of
it is an absolute frame rate.** The site's clean baseline is `perf/`: 73 fps mean, 55 fps worst
in overcast after the photoreal pass, with ambient occlusion costing 4.2 ms of a 13.7 ms frame.

```
full stack      23.61 ms
tonemap only    18.79 ms
                --------
whole stack      4.82 ms
```

| effect | leave-one-out cost | survived? |
|---|---|---|
| depth of field | **2.77 ms** | yes — and it is the single most photographic thing in the set |
| bloom | **1.05 ms** | yes, retuned 4× / 13×; **idle in 7 of 9 shots**; §6.2 |
| chromatic aberration | 0.46 ms | yes, halved; §6.7 |
| lens distortion | 0.26 ms | yes, and it is the first thing I would cut; §6.8 |
| film grain | 0.17 ms | yes; §6.5 |
| vignette | 0.13 ms | yes, and it dominates the exposure; §6.6 |
| motion blur | 0.03 ms | yes |
| colour grade | ~0.00 ms | yes, and the bug is not in it; §6.9 |
| lens dirt | (0.10 ms, untrustworthy block) | **CUT**; §6.10 |
| **sum of the parts** | **4.97 ms** | vs 4.82 ms for the whole stack — **3%**, which is the main reason to believe the table |

**Two numbers I do not believe and am recording rather than hiding.** The grain measured
**0.17 ms** here against the cave's **1.42 ms** for the same shader doing the same work — an 8×
discrepancy that is more likely to be measurement conditions than physics, and needs a quiet
machine. And the dirt block ran at 55.9 ms against every other block's 24 ms, i.e. the machine
had a contention event during it; the 0.10 ms delta from that block means nothing.

### 8.1 The exposure contract

**First, the thing the cave checked and this pass owes too: the base scene is untouched.**
`--mode=shots --shot=01_site_wide` rendered from this build and from HEAD's build with the
cinematic layer's two source edits stashed is **byte-identical, 0.0000% of pixels differing,
max delta 0**. (Two runs of the same build are also byte-identical, so that is a real result
and not a coincidence of noise.) The cinematic layer adds files and one recording variable in
`weather.gd`; it does not move a pixel of the spike as the photoreal and order passes left it.


`lumcheck.py` compares `contract_off/` (AgX and the scene's own grade, i.e. the spike as the
photoreal and order passes left it) against `contract_on/` (the full stack), on all nine
executing shots at t = 0.15, 0.50 and 0.85 — 27 frames.

**ART-DIRECTION §2.9's thresholds are for a lamp frame and not one frame here is a lamp frame.**
"legible 3–20%" and "true black ≥ 70%" describe a three-metre pool of carried light in a black
room. A yard under an overcast sky is legible over 55–72% of frame *by construction*, and that
is the contrast the whole design rests on — `DESIGN-PRINCIPLES` §3, *"the surface is safe and
lit; the cave is not… the art should make the descent feel like leaving somewhere."* Applying
the cave's floor to a daylight frame would fail every correct picture in this directory.

So the **blown ceiling** is asserted, because it is the one line of §2.9 that is about the sky
as much as the lamp, and the rest is measured as a **delta** — which is what §2.9's actual
sentence, *"No shot is brightened to make it read"*, is about.

**The result:**

> **0 of 27 frames over the 3% blown ceiling** — the worst is `t03_yard_drift` at **0.73%**.
>
> **Every single frame's mean goes DOWN.** The largest change is **−20.25%** and the smallest is
> **−6.32%**. Nothing in this layer brightened anything.

And the shape of it is entirely the vignette and entirely a function of focal length:

| shot | lens | stack's effect on frame mean |
|---|---|---|
| `t04_rain_macro` | 50 mm | **−6.3 to −6.8%** |
| `t06_bench_machine` | 50 mm | −7.3 to −7.8% |
| `t07_course_posts` | 35 mm | −7.2 to −9.7% |
| `t05_charge_line` | 35 mm | −9.0 to −9.3% |
| `t02`, `t03` | 21 mm | −13.6 to −14.8% |
| `t28_extraction_window` | 21 mm | −17.4 to −18.7% |
| `t12`, `t13` | 21 mm | **−17.8 to −20.3%** |

Nothing else in the stack moves the mean by more than 1.3%. The vignette is derived from the
focal length rather than dialled, and the contract measurement is an independent confirmation
that it is: **a 21 mm costs three times what a 50 mm costs, in exactly the ratio cos⁴ predicts.**

The one band that moves structurally is `> 0.18` on the sky shots: at `t02` it falls from
19.6% to 7.0%, because the overcast sky sits within a few percent of the 0.18 threshold and the
vignette pushes most of it under. It is still inside §2.9's 1–25% window, so it passes; it is
worth knowing that on a daylight frame that band is a knife edge.

### 8.2 The motion is eased, and it is measurable

`sequences.txt` prints the per-frame step in millimetres. `t02_headframe_sky`:

```
1.0  6.2  15.4  27.2  40.4  54.0  67.0  78.7  88.4  95.7  100.2  101.8
     100.2  95.7  88.4  78.7  67.0  54.0  40.4  27.2  15.4  6.2  1.0
```

Symmetric, zero at both ends, no discontinuity, and the same shape on all nine. Focus is pulled
on the same eased curve, so it accelerates and settles with the camera rather than sliding under
it — `t06_bench_machine` pulls 2.45 → 1.95 m across the push.

---

## 9. Does the frame read as photographed?

My honest judgement, from reading the frames rather than from having written them.

**More often than in the cave, and for the opposite reason.** The cave's verdict was that the
lens stack had become better than the things it was pointed at, and that one lamp at the eye was
the limit on how photographed anything could look. The pit-head has a sky, a directional source
at 4.5° angular size, ambient from a generated radiance map, real shadows, wet materials and
eighty-five thousand objects. **The lighting is not the limit here. The geometry is.**

**The three that convince.**

1. **`t13_collar_above`.** A crane at 4.6 m looking down through the headframe's own bracing at
   the collar, the cage grating, and a machine standing on the pad waiting to be sent down. The
   ironwork frames it as foreground, the pale machine reads against the concrete, the shadows
   are long and soft. Nothing in that frame says engine viewport. It is also the frame that
   proves the crane rule was worth writing: it is *hung*, and you can see what it is hung from.
2. **`t02_headframe_sky`.** The head against an overcast sky from 0.42 m, with the pole-line
   catenary crossing the frame and the polished sheave carrying the only glare in the picture.
   The catenary is the only curve in the frame, which `NOTES.md` §2.2 already knew, and it is
   what makes the composition.
3. **`t06_bench_machine`.** The machine whole on its work stand at 50 mm T2.8, sharp from 2.27
   to 2.66 m, with the bench and the second stand soft behind it. The depth of field is doing
   exactly what §9 says it should: *"reads as a camera rather than an eye."*

**What still says "rendered", in the order I would fix it.**

1. **Specular aliasing on the ironwork.** At MSAA 2× the headframe's 1–2 pixel lattice members
   crawl with white speckle, and it is present with every post effect off. It is the single most
   damaging thing in the two frames that open the trailer, it is what forced the CA down (§6.7),
   and it is a render-settings decision, not a lens one.
2. **Things that read as floating.** A stores rack whose shelved drums have no visible support;
   signage panels that hang without posts at some angles. This forced one re-frame and it will
   force more. It is a dressing problem (`ORDER.md` §8.3 is the nearest existing note) and it is
   the most expensive kind, because the camera cannot avoid the whole yard.
3. **Underfoot.** §7.4. The trailer asks for a macro of wet hardstanding and the spike's own
   documentation says three times that this is its weakest scale.
4. **Nothing moves.** `NOTES.md` §7.4, unchanged and now the loudest thing in the set. Every one
   of these nine shots is a camera move over a still yard, which is exactly the workaround
   TRAILER §7 prescribes, and it works — but a hoist that ran, a sheave that turned, or one weed
   in the wind would do more for these frames than another effect in the stack.

**Is the grade a lens or a filter?** A lens, and the test is the cave's: can every effect be
turned off and the frame still read as the same photograph? Every one can. The grade moves the
frame mean by 1.2% and pulls B:R *toward* neutral. The only effect with a visible signature is
the vignette, and it is derived from the focal length rather than chosen — which the contract
measurement confirms independently by showing it cost three times as much on the 21 mm shots as
on the 50 mm ones.

**Is anything blown or crushed?** Blown: **no** — 0 of 27 frames over the 3% ceiling, worst
0.73%. Crushed: not on the overcast shots. The two rain shots run 60–69% true black and
`t12_course_alone` loses half its legible fraction to the vignette (10.4% → 5.5%); both are
still well clear of anything unplayable, and both are dark on purpose.

**Does anything clip, or hover?** No clipping: the sequences were rendered only after the
validator passed them, and all nine report `near clear 0.40` — which is the measurement's
ceiling, i.e. **nothing is inside the 0.40 m frustum at any sampled instant of any shot**, not
that they are pressed against the limit. No hovering: every height in the list is a declared rule checked against a raycast to
the rendered ground, every crane names the structure it hangs from and its distance, and the
format cannot express an unjustifiable height without naming it.

**Is the motion eased?** Measurably, §8.2.

---

## 10. Everything I guessed

Everything below is mine rather than read out of a document. The cave's §10 list is inherited in
full where the code is inherited — the sensor size, the circle of confusion, `dof_blur_amount`,
the handheld model, the sensor's full-well and read-noise numbers, the barrel coefficient, the
9 motion-blur taps, the 0.05 m query margin, `vig_k = 0.55` and the LUT's chroma-rolloff
threshold are all still guesses and are all still the cave's. New ones:

1. **The site anchor's whole vocabulary** — which places exist, that a rectangle's axis is its
   long side, that a station's axis is its own yaw, and that walkways and the haul road are
   addressed by fraction of arc length. Nobody asked for this format.
2. **`CRANE_REACH = 12 m`** — how far a rig can hang out from the thing it is hung on. §4.4.
3. **The crane band's ceiling of 30 m.** The cave uses 9.
4. **The buried test's shape**: six axis rays at 2.0 m, five back-face hits out of six. §4.5.
   It is a guess and it is a *wrong* one for roofless buildings; §7.1 shows it missing.
5. **40 mm as the swept-path step.** §4.3.
6. **That SITE and PROP collide and DETAIL does not.** It matches the cave's intent exactly and
   it is still a decision this pass made.
7. **Bloom threshold 0.40, knee 0.15, intensity 0.70.** The threshold and the knee are measured
   against the HDR probe; the intensity is taste.
8. **Chromatic aberration at 1.0 px** rather than the cave's 1.9. Argued from the subject
   (§6.7), not measured against anything.
9. **The grade's warm mask**: 0.42–0.78 smoothstepped, falling to zero at the top. The argument
   (do not warm the sky, because the sky is the shaft's colour) is from ART-DIRECTION §2.1; the
   numbers are mine.
10. **The dirt model entirely** — two noise populations, 4:1 vertical stretch, a five-tap
    neighbourhood gate, and gating on `g_wet > 0.55`. It is cut, so none of it ships, but the
    measurement that cut it depends on the model being reasonable.
11. **That `u` is measured from `Ground.height` rather than from a raycast.** §4.2. It is
    right, and it is a deviation from the cave that nobody asked for.
12. **Which nine places in the yard the ten shots stand in**, and every focal length,
    T-stop, duration and handheld amplitude in `shots_cinema.json`. TRAILER §3 gives a sentence
    and a length per shot and nothing else.
13. **That shot 6 is an eye-height shot.** §7.3. TRAILER says "low, close" and I read "low" as
    relative to the headframe shots rather than as a height band.
14. **That shot 13 should be wide (21 mm) rather than normal.** A crane over a collar sees the
    headframe's legs whatever it does, and a 35 mm framed the pad instead of the shaft.
15. **That shot 3's "racks in rows" can be satisfied in the mid-ground rather than the
    foreground.** The first framing put a rack in the near field and it read as floating.
16. **The `--cinema=hdr` probe's 1/16 scale factor** and the assumption that dividing out the
    preset's `tonemap_exposure` recovers scene radiance. It is right for Godot's LINEAR
    tonemapper; it is an assumption about Godot.
17. **That the ten pit-head shots are 2, 3, 4, 5, 6, 7, 12, 13, 14 and 28.** That was given.
    What was not given is that shot 14 is mine to attempt at all, since §3 sources it "S / C".

---

## 11. What I would do next, in order

1. **Rule on shot 14.** §7.2. The trailer's third act opens on a descent and the rig refuses it
   for four reasons, none of which is about the picture. The general form — *a shot may declare
   that it is carried by a moving thing* — is also what shots 17 and 22 need the day a machine
   walks, so it is not a special case, it is a missing feature of the format.
2. **Raise MSAA, or add a specular anti-aliasing term.** §9. The two frames that open the
   trailer are of a lattice against a bright sky, which is the worst possible case, and it is
   currently the most render-looking thing in the set.
3. **Replace rule 8 with a containment query against the building rectangles.** §4.5 and
   §7.1. It is about fifteen lines, the plan already holds the rectangles, and the current
   six-ray test demonstrably passes a camera standing inside the winding house.
4. **Take the swept-test fix back to the cave.** §4.3. `cast_motion` returning 0 on initial
   contact is not a surface problem; it is a latent one in the cave's rig that its floor happens
   not to trigger.
5. **Give the yard fill a footprint check, or the camera a clearance query it can author
   against.** §7.4. 0 of 121 offsets at floor height is a fact about the generator, and
   `NOTES.md` §7.3 predicted it before this pass existed.
6. **Re-measure the whole stack on a quiet machine.** §8. Two numbers in the cost table are not
   trustworthy and the grain figure disagrees with the cave's by 8×.
7. **Make bloom a per-shot switch.** It costs 1.05 ms and is idle in seven of nine shots; the
   mask already supports it and the shot format does not.
