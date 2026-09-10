# The vertical cave

What `docs/THE-ICE.md` §5 asked for, built. The cave had **under two metres** of floor range
and a `K_SHAFT` constant that nothing branched on; it now has **83.3 m**, four levels, nine
pitches, three media interleaved by depth, and a profile family that can express a hole.

Written 2026-09-10. Everything here is measured on this machine unless it says GUESS, and every
guess is collected in §11.

---

## 0. The one-page answer

| question | answer |
|---|---|
| Is the cave genuinely vertical? | **Yes.** 83.3 m of range against 8.4 m before (and under 2 m of *floor* range). Four levels stacked over the same plan, nine pitches between them, levels running in opposite directions so one lies under another |
| Did the existing cut survive? | **Yes, byte for byte, and it is asserted every run.** The flat cave is still the default; `seed 7 / 240 cells / 1 level` still hashes to `0xAD83E3ED`, and every run prints a PASS/FAIL against that constant |
| What is the new hash? | **`0xF1A66B36`** for `seed 7 / 240 / 4 levels` — schema v2. The two schemas are distinguishable by a machine from `topology hash v1` and `topology schema` on stdout, and from `topology_schema=` in `summary.txt` |
| Down cheap, up expensive? | **Yes, and it is measured, not asserted.** Reachable from the collar: **6924 of 6924 open cells (100%)**. Able to return to it: **5322 (76.9%)**. The 23% that cannot is the deepest level — the dry one, below the melt front, where the discoveries are |
| Can a machine know how deep it is? | **No, and it is worse than THE-ICE §6.2 claims.** It cannot see down a shaft, it cannot see up one, and it cannot even *record* that nothing came back. But the claim is currently **false in the built code**, because the cloud spike hands the belief layer its true Y. §9 |
| What did it cost? | Topology 6.6 → 42.7 ms, dressing 0.52 → 1.37 s, for **4× the cave**. GPU frame p50 3.6–4.4 ms → 4.9 ms. One 0.9 s stall at the foot of the first shaft |
| What broke? | The exposure contract (8 of 11 vertical frames outside it, all in the *dark* direction), one ceiling-invariant violation, and `ART-DIRECTION` §3.6's sightline statistics |

---

## 1. What must not break, and how it is held

`spikes/godot/cloud/` holds a byte copy of the pre-2026-09-10 `topology.gd`, generates the same
cave from seed 7 over 240 cells, and cuts its belief frames from **this cave's cameras** at a
measured 5 mm RMS. Four cave sequences and five belief sequences in the current trailer cut were
rendered against topology hash `0xAD83E3ED`. If seed 7 stops producing that cave, the cut breaks
silently — with a wrong picture, not an error.

**So the vertical work is behind a flag, and the flag defaults to off.**

```
--levels=1        (DEFAULT)  the flat cave, schema v1, hash 0xAD83E3ED
--levels=2..4                the layered cave, schema v2
--vertical                   alias for --levels=4
```

`generate(seed, length)` defaults to `p_levels = 1`, so even a byte copy of this file taken into
another project keeps producing the old cave from the old call site.

**Three things make that a guarantee rather than an intention.**

1. **The flat generation path is frozen.** `_legacy_drive()` and `_legacy_crosscuts()` are the
   pre-change rules R1–R4 verbatim. The vertical path is separate functions (`_build_levels`,
   `_build_level_drive`, `_build_level_crosscuts`). Nothing shared between them was edited except
   where a `levels == 1` clause makes the old rule the only rule — that happens in exactly three
   places, and each is commented: the rail rule, the discovery rule and the ground-support rule.
2. **The hash is versioned.** `content_hash()` on the flat path hashes the **sixteen station
   fields the old row had and nothing else** (`SCHEMA_V1_FIELDS = 16`), so the five new fields,
   the pitch rows and the new plan scalars are invisible to it. On the layered path it hashes
   everything.
3. **It is asserted every run.** Every launch generates the flat cave a second time from scratch
   and prints:

```
topology schema  : v1  (1 level)
topology hash    : 0xAD83E3ED
topology hash v1 : 0xAD83E3ED   (flat path, same seed and length)
v1 regression    : PASS   (recorded 0xAD83E3ED)
```

That costs 6 ms and it means nobody has to remember.

**And it was verified at the pixel, not only at the hash.** The twelve canonical shots were
re-rendered from this build and compared against the committed PNGs, then the same build was
rendered a second time and compared against itself:

| | worst channel diff, build vs committed | worst channel diff, build vs itself |
|---|---|---|
| `02_dense_mid` | 114 | 78 |
| `08_waterline` | 167 | 145 |
| `11_set_line` | 233 | 91 |
| `12_crown` | 82 | 70 |
| mean absolute diff, all frames | 0.0016 – 0.24 of 255 | 0.0019 – 0.05 |

**The build-to-build difference is the same size as the run-to-run difference**, which is the
GPU particle drips and FXAA, not the topology. The station rows and the raster were also compared
field by field against a copy of the original file: **zero differing fields, zero differing
cells.**

**Nothing outside `spikes/godot/cave/` was touched.** The cloud spike's copy of `topology.gd` is
still the pre-change file, byte for byte (`diff` says so), so it is unaffected either way — but
when somebody re-syncs it, the default keeps them safe.

**The shot log format is unchanged.** New output goes to new lines and new files; `summary.txt`
gains `topology_schema=` and `vertical_range_m=` lines *after* the existing ones and changes none
of them.

---

## 2. The seam, field by field

`docs/THE-ICE.md` §5.3 costed three options and recommended **B, levels**. That is what is built,
and its two properties survive: **the raster is still a set of 2D integer arrays** (one per level,
so `DETERMINISM.md`'s rules and a blake3 golden are untouched) and **dressing still works
per-chunk on a plane**. Everything below is integers in millimetres, no floats, no maps, no
dictionary iteration, and the counter-based `draw(purpose, a, b)` hash is unchanged.

### 2.1 The station row: 16 fields → 21

Fields 0–15 are unchanged in index, meaning and value.

| new field | type | what it is |
|---|---|---|
| `S_LEVEL` | 0..3 | which level. 0 is the shallowest. This is `CellPos.level` from THE-ICE §5.4 |
| `S_MEDIUM` | `MED_ROCK / MED_WORKED / MED_ICE / MED_ICE_OVER_ROCK` | THE-ICE §5.4 note 4's single `u8` enum, on the passage rather than per cell |
| `S_CEIL_MM` | i32 | ceiling **elevation**. NEW, and it fixes the hole THE-ICE §2.10 found: `PROCEDURAL-AND-GODOT` §1.6 asserts "chambers must be taller than the passages that reach them" against a field `Passage` did not have. It has one now and the assertion is counted (§7) |
| `S_PITCH_HEAD` | i32 | index into `pitches` whose **top** is at this station, else −1 |
| `S_PITCH_FOOT` | i32 | index into `pitches` whose **bottom** is at this station, else −1 |

**`S_FLOOR_MM` changed meaning and did not change type.** It was "floor height above datum" with
the datum implicitly at the shaft; it is now the **elevation measured from `datum_mm`, the valley
floor**, and it is negative going down. That is THE-ICE §5.4 note 6 taken as written: one zero
that the town's height and the cave's depth are both measured from.

**`depth_mm` is a function, not a field.** `depth_mm_of(st)` is `datum_mm - st[S_FLOOR_MM]`.
THE-ICE §5.4 note 1 says depth in metres is *additional to* `depth_band` and must never replace
it; making it derived rather than stored is the cheapest way to guarantee that, and `S_DEPTH`
(the BFS band) is still there and still has seven consumers.

**They correlate and are not identical**, which is note 1's post-condition. A pitch costs its own
drop in cells in the BFS, so level 3 starts 56 cells deep before a machine walks anywhere on it,
while a long crosscut at the top of level 2 can be graph-deeper than a short one at the top of
level 3.

### 2.2 The plan scalars

| new | type | what it is |
|---|---|---|
| `levels` | 1..4 | the level count. `extent` is `(w_cells, h_cells, levels)` |
| `datum_mm` | i32 | the valley floor, and the one zero. 0 in this spike |
| `melt_mm` | i32 | the melt front, an **elevation**. −60 000 |
| `level_water_mm[]` | i32 per level | the water surface on each level, or −1 000 000 for none |
| `collar_st` | i32 | the station the collar lands on. The BFS source |
| `reach_down`, `reach_up` | i32 | the two post-conditions, computed |
| `ceil_violations` | i32 | the invariant §2.1 made checkable |

`water_datum_mm` survives as the deepest wet level's surface, so the shader uniform and the kit
materials that read it still work.

### 2.3 The pitch row — 18 ints, a first-class record

THE-ICE §5.4 note 2: *"A drop is not a rule. It is a place the generator chose, a place the sim
must reason about, and a place the player will die at. It belongs beside `Passage`."*

| field | what it is |
|---|---|
| `P_FROM_ST`, `P_TO_ST` | the stations at the top and the bottom. `−1` at the top means the sky |
| `P_X`, `P_Y`, `P_TO_X`, `P_TO_Y` | the cells. A pitch may be inclined |
| `P_TOP_MM`, `P_BOT_MM`, `P_DROP_MM` | elevations and the drop. Positive is downward |
| `P_BORE_MM` | the clear diameter. **The width class of a vertical hole**, and deliberately a length rather than a class, because a bore is compared against a chassis width and not against a cell |
| `P_CLIMB` | `CL_WALK / CL_SCRAMBLE / CL_PITCH / CL_VERTICAL`. **On the link** |
| `P_KIND` | `collar / moulin / winze / aven / orepass / collapse / crevasse` |
| `P_MEDIUM` | as §2.1, at the top. A long pitch changes medium with elevation and the dressing follows the elevation, not this field |
| `P_WATER_MM` | the water surface inside it, or none |
| `P_FLOW` | 0..255 of meltwater running down it. **An acoustic object**, and it is zero below the melt front |
| `P_FLAGS` | `DAYLIGHT / MAIN / FIXED` decided, `DOWN / UP` **derived** |
| `P_FROM_LEVEL`, `P_TO_LEVEL` | |

**`climb` is on the link and `width_class` stayed on the cell**, which is THE-ICE §5.4 note 3
exactly. Width is a property of where you are standing; a pitch is a property of a transition.
`width_class_here` is untouched and the new belief signal it implies — `pitch_ahead`, derived
from returns, legal, and frequently wrong — is a different signal on a different object.

### 2.4 The link table, and why connectivity is now directed

`links` is rows of `(A, B, cost_cells, pitch_index)`. A passage link is bidirectional. A pitch
link carries its own permission bits, so the graph is directed and `A → B` can exist while
`B → A` does not. That is what makes THE-ICE §5.3's two separate assertions possible:

```
connectivity     : reachable 6924 of 6924 open cells   RETURNABLE 5322 (76.9%)
```

The first is a hard post-condition. **The second is allowed to fail by design** and does.

### 2.5 The chamber row: 5 ints → 7

`x, y, r_cells, is_plant, station_id` gains `level` and `running`. `running` is
`AncientSite.running` from THE-ICE §5.4: `floor_mm > melt_mm`. One field, derived from one plan
scalar, and if the designer rules "it never stopped" both it and `melt_mm` are deleted and nothing
else changes.

### 2.6 What did NOT change

The `draw(purpose, a, b)` hash. The FNV-1a form of `content_hash()`. The **17-flag works
bitfield** — not one bit added, exactly as THE-ICE §2.3 predicted. The four width classes and
their millimetres. `S_WORKED`'s meaning, `S_INTEG`, `S_FRACTURE`, `S_BEDDING`, `S_WET`,
`S_DISCOVERY`. The rasterise rule (an integer disc stamp, now per level). The 47-mesh kit (48 now
— one ring was added), the four shaders, the generated noise volumes, the placement rules.

**And a bug found on the way past that had nothing to do with the ice.** Adjacency lists built as
`Array[PackedInt32Array]` silently discard every append: a `Packed*` array is a value type in
GDScript, so `(adj[a] as PackedInt32Array).append(b)` appends to a copy. The first BFS returned
depth 0 for every station, which changed 199 stations' works and the hash, and it is the same
copy-on-write trap `dressing.gd`'s `MB` class already carries a note about. Untyped `Array` is
the fix and it is commented in place.

---

## 3. Pitches: the things that connect levels

### 3.1 The nine, at seed 7

```
  collar    L0->L0  drop   11.0 m  bore 2.60 m  scramble ice/rock down=Y up=Y flow=55
  moulin    L0->L1  drop   14.7 m  bore 2.20 m  pitch    ice      down=Y up=n flow=140
  winze     L1->L2  drop   22.7 m  bore 1.60 m  pitch    worked   down=Y up=n flow=60
  winze     L2->L3  drop   33.6 m  bore 1.84 m  pitch    worked   down=Y up=n flow=60
  collapse  L0->L1  drop   14.9 m  bore 3.94 m  scramble ice/rock down=Y up=Y flow=0
  collapse  L1->L2  drop   23.0 m  bore 3.45 m  scramble ice/rock down=Y up=Y flow=0
  orepass   L1->L2  drop   23.3 m  bore 0.97 m  vertical worked   down=n up=n flow=0
  aven      L2->L3  drop   33.7 m  bore 1.45 m  pitch    rock     down=Y up=n flow=0
  crevasse  L0->L1  drop   14.7 m  bore 0.74 m  vertical ice      down=n up=n flow=35
```

**The main descent is one object doing three jobs**, which is THE-ICE §5.2's first structural
claim taken literally: the collar is the ancients' shaft head, the moulin below it is the same
hole re-bored by meltwater, and the winzes below that are the ancients' own workings. The player
goes down the way the water went down, and the water went down the way the ancients went down.
The collar carries iron rings the water could not scour away, and the rings are still in the
moulin below it — that is the "workings cutting through both media" in one object.

**Each level's descent leaves near its far end** (88%, 88%, 85% along the drive), so a machine has
to cross a level to find the way down, and each level runs back the other way underneath the one
above it. That switchback is what puts a chamber over a chamber, and it is visible in
`shots/vertical/v10_section.png`.

### 3.2 The climb rule, and why down is cheap

`_climb_for(kind, drop, bore, medium, fixed)` is nine lines of integer comparison:

```
drop <= 400 mm                              -> WALK
drop <= 2200 and medium is not ice          -> SCRAMBLE
fixed (the ancients left steel) and <= 14 m -> SCRAMBLE
a COLLAPSE up to 30 m                       -> SCRAMBLE      (broken ground is a ramp)
drop <= 45 m and bore >= 1100 mm            -> PITCH
otherwise                                   -> VERTICAL
then: polished ice demotes SCRAMBLE to PITCH
      bore < 900 mm is VERTICAL whatever else it was
```

and the two permission bits fall out of it:

| class | down | up | what it means |
|---|---|---|---|
| `WALK` | free | free | a ramp |
| `SCRAMBLE` | free | costs, and a chassis class gates it | broken ground with something to push against |
| `PITCH` | **yes** | **no** | a controlled vertical descent. One way |
| `VERTICAL` | **no** | **no** | no purchase anywhere. A machine that enters it is falling, not descending |

**Three deliberate consequences.**

- **The polish demotion is the ice mechanic arriving as a number.** A 14.7 m moulin in ice is a
  `PITCH` where the same drop in rock would be a `PITCH` too — but a 2 m step in ice is a `PITCH`
  where in rock it is a `SCRAMBLE`. Ice takes away the way back, one class at a time.
- **A collapse is the exception, and it is the way home.** What fell is rock even where it fell
  through ice, so a collapse never gets the polish demotion. That is why the two `SCRAMBLE` links
  in the table are both collapses, and why they are the only routes back up.
- **There is no way back out of the deepest level.** By rule: an up-route is generated for every
  level pair *except* the last. Level 3 is below the melt front, dry, silent, and it holds
  discovery id 4. That is `DESIGN-PRINCIPLES` §2's *"any tuning that removes the possibility of
  not getting out removes the game"* made structural rather than statistical — and it composes
  with drift rather than replacing it, exactly as THE-ICE §5.1 argues. A machine that is lost
  *and* below a pitch it cannot climb is in a different kind of trouble.

### 3.3 The second profile family

THE-ICE §5.3: *"`_half_profile()` builds a floor, two legs and a crown, which a vertical shaft is
not. A moulin needs a **second profile family** beside the sweep, not a modification of it."*

Built as two genuinely different functions rather than one function with a flag:

| | passage | pitch |
|---|---|---|
| section | an **open half-section**, floor centre → crown, mirrored about a vertical | a **closed ring in the horizontal plane** |
| swept along | a horizontal spine, oriented by a tangent and a right vector | a vertical axis that is allowed to corkscrew |
| perimeter coordinate | arc length up from the floor | an angle |
| can it close over itself? | no | it is nothing but closed |

Six kinds share it and **each is a different radius function, not a different parameter**:

- **moulin / collar** — helical flutes, `1 + 0.13·sin(3θ + t·h·0.55)`, on an axis that corkscrews
  by up to a third of the bore. That is what falling water does to a hole, and it is the reason a
  moulin does not read as a passage stood on end.
- **winze / ore pass** — square-set: a superellipse of order 8, four timbered sides.
- **crevasse** — a slot. Bore wide one way, 4.2× that the other.
- **aven** — bells out upward, `0.72 + 0.55(1−t)`.
- **collapse** — broken, `0.80 + 0.34·sin(2θ + 5t)`, on a leaning axis.

**Two holes and a skirt.** A chamber with a pitch sunk from it builds its floor as an **annulus**
instead of a fan; a chamber a pitch lands in stops its dome at the ring whose nominal radius falls
under `bore/2 + 0.6 m`, leaving the apex open, and a short cone closes the join. Both ends of the
tube use a clean, noise-free radius so they meet those openings exactly. That is the whole cost of
"things below other things" in geometry: two skipped index ranges and one skirt.

### 3.4 What is inside a pitch

- **The ancients' rings** where they left steel, every 1.2 m, as a unit-radius kit mesh the pitch
  scales to its own bore. They are the only thing that gives a bore a rhythm when there is nothing
  else in frame but wall going past.
- **A beacon at the head and the foot of every pitch a machine can descend**, plus a chain every
  3.2 m down the main ones. `ART-DIRECTION` §6.3 calls a beacon chain receding down a drive the
  most beautiful image in the game; rotated ninety degrees it is also the **only thing that makes
  a shaft photograph at all**, because the lamp reaches about six metres on a floor and a shaft has
  no floor.
- **The meltwater**, as a ribbon clinging to the flutes rather than a column, and only above the
  melt front.
- **A cone of rubble at the bottom** — everything the hole has ever dropped.

---

## 4. The three media, interleaved by depth

`ART-DIRECTION` §3.7 and THE-ICE §5.2, compressed. **The interleave is the design, not the list.**

| band | elevation | what it is | at seed 7 |
|---|---|---|---|
| 0 — the fill | 0 to −15 m | dead ice and the meltwater conduits cut through it. Round, polished, smooth. No ancients except the collar itself | level 0 at −11 m, 266 stations |
| 1 — the karst | −15 to −38 m | bedrock re-cut by water that found the old joints. First marks, low item numbers | level 1 at −26 m, 242 stations |
| 2 — the workings | −38 to −72 m | the mine. Rail, sets, the Bus, the plant | level 2 at −49 m, 304 stations |
| 3 — the deep | below −72 m | past the melt front. Dry, silent, and it has not been touched since before the ice | level 3 at −83 m, 249 stations |

Measured mix: **rock 168, worked 535, ice 266, ice-over-rock 92** stations. Most of the cave is
the mine, the ice band is thin, and the karst is the transition — THE-ICE's ratios kept.

**The ice is a fill, not a layer.** Band 1 is not "no ice": it is ice where the drafts and the
drainage put it — near a pitch, in the low ground, and more of it the nearer the ice base. That is
one `draw_pct` against a depth-scaled threshold and it produces the 92 ice-over-rock stations.

**`worked` is now driven by elevation first and by along-drive distance second.** That is
`DESIGN-PRINCIPLES` §10's *"going deeper becomes literal"* in the one field that decides what a
frame contains. Band 0 runs 0–28, band 1 48–140, band 2 165–250, band 3 200–255.

**Deeper looks different, in three registers rather than two.** Shallow is pale, smooth, empty and
relatively bright; the middle is the wet mine the spike already knew how to draw; and the deepest
is the same mine **dry** — and the dryness is visible in the histogram, not only in the fiction
(§7).

### 4.1 The ice material

A **separate shader**, `ice.gdshader`, and the reason is written in `ART-DIRECTION` §3.1's own two
warnings: *"Everything in the rock family shares one voronoi and it shows… ice built from the same
function will join that family, which is exactly what it must not do"* and *"the fix is a second
pattern primitive — anisotropic, directional, flow-shaped — which nothing here has. That is the
one real new shader the ice costs."*

- **No cellular function is sampled.** `t_cel`, `t_agg` and `t_cid` are not bound. The only
  texture is the fbm volume, sampled with the coordinate **compressed 6:1 along the flow axis**.
- **The flow axis is recovered from the geometry.** `UV2.x` is the distance along the flow, so its
  world-space gradient is the flow direction; two `dFdx`/`dFdy` pairs give it and no tangent array
  has to be carried through the mesh builder. In a pitch `UV2.x` is the **elevation**, so the
  flutes run *down* the bore; in a passage it is the axial distance, so they run *along* it.
- **The scallops are explicit** — two registers at 0.22 m and 0.075 m, wrapped into a helix by the
  perimeter angle, and cut as hollows rather than lumps.
- **The blue is a path length, not a tint.** There is no blue constant anywhere in the file. There
  is an absorption coefficient in m⁻¹ and an `exp()`. `ART-DIRECTION` §3.1's four scalars —
  `clarity`, `polish`, `debris`, depth-of-medium — are all present, and `debris` is a **volume**
  mask that mixes toward the measured dark-rock band, which is what keeps ice inside the warm rock
  family: what is suspended in it is the cave.
- **`polish` is not only an art scalar.** An ice conduit's silhouette displacement is cut to 30%
  of the rock's and its bedding to zero, because THE-ICE §6.2's whole claim rests on a meltwater
  conduit having no features to lock a scan onto. A 0.5 m lumpy ice wall would hand the estimator
  exactly what the design says it cannot have.

**One shortcut, flagged.** The internal glow approximates the single carried lamp as a point
source at the camera (they are 0.26 m apart). It is why ice is the one specular-family material
that does not fail `ART-DIRECTION` §3.1's *"a pool reflects one hotspot and otherwise reflects
black"* test — it returns the lamp's own light from inside rather than a reflection of a black
room. **It will be wrong the first time two agents are in one chamber.** A real transmission term
needs a `light()` function or Godot's SSS.

**And three dressing rules the ice forced, all keyed on the one `medium` field:** no roof pendants
and no flowstone bosses in ice (both are limestone speleothems and take ten thousand years of
dripping); a much sparser and smaller breakdown field; and no ground-support mesh, because ground
support is the ancients' and there is none in dead ice. Before those three rules the ice band was
a limestone cave with ice paint on it.

---

## 5. What the client layer had to learn

| change | why |
|---|---|
| **`_chunk_key` is an 8 m cube** | it was XZ only. THE-ICE §2.3 named the consequence before there was any vertical geometry to suffer it: *"a vertical shaft puts an entire cave's worth of geometry into one chunk key."* The flat path keeps the old XZ partition so its frames are drawn by the same MeshInstances as before |
| **`VIS_PITCH = 96 m` on chunks holding pitch geometry** | THE-ICE §2.4 predicted this exactly: *"LOD comes back… a vertical sightline is what defeats them."* The cheap answer is a longer range on the shafts only; the real answer is LOD and this spike does not build it |
| **one rock and one ice material per level** | the water surface is per level now. `cave/PHOTOREAL.md` guess 4 already flagged the global datum — *"this treats the whole cave as having drowned once, to one level"* — and meltwater cutting downward is exactly the case where one horizontal datum is wrong. A chunk only ever belongs to one level, so this costs no extra draw calls |
| **`_place_water` walks every edge and reads each station's own surface** | same reason |
| **the camera path descends** | cross a level to its far end, drop, cross the next one back the other way. 495 m of path against 154 m |
| **cameras must stand on the drive centreline** | the chamber dome is a 5–7 m hemisphere with a 2.9 m tube running through it, so anywhere off the centreline by more than the tube's half width is *inside the tube's wall*. That is `NOTES.md` §7's chamber-interpenetration weakness, met head-on by a camera that wants to look down |

---

## 6. Frames

`shots/vertical/`, eleven at 1920×1080, `--levels=4 --shotset=vertical`.

| | what it is |
|---|---|
| `v0_collar_daylight` | the bottom of the collar. 12000 K skylight arriving through a smaller hole, and stopping |
| `v1_down_the_shaft` | the lip of the moulin from six metres back on the drive |
| `v2_up_from_the_bottom` | standing under the hole, looking up into it |
| `v3_chamber_below_chamber` | a chamber with the shaft that dropped into it open in its back |
| `v4_moulin_meltwater` | inside the bore, beside the water |
| `v5_ice_to_rock` | the transition, which happens **inside the shaft** at −15 m. Grey ice above, warm rock below, a beacon on the wall between them |
| `v6_ice_band` | a meltwater conduit in dead ice at walking height |
| `v7_melt_front` | the front, crossed inside the deepest winze. Nothing marks it |
| `v8_below_the_melt_front` | past it. Rails, sets, ballast, and no water anywhere |
| `v9_the_workings` | the mine, for the comparison |
| `v10_section` | the wide view, and it is a **schematic** |

**The section is a schematic on purpose**, and that is `ART-DIRECTION` §3.6's own rule rather than
a shortcut: *"the wide shot in Blindside is a schematic. The close shot is a photograph. There is
nothing in between."* A vertical cave has no place to stand that sees two levels at once, so the
frame that makes the structure legible is drawn from the plan — levels at their real section
height coloured by medium, pitches coloured by whether a machine can come back up them, the water
surfaces, the band boundaries and the melt front. Everything in it comes out of `topology.gd`.

**The honest report on the rest of them: three of the ten photographed frames are good, four are
correct and dark, and three are frames of a hole with nothing in it.** That is not entirely a
framing failure — it is the mechanic. A shaft has no floor for the lamp to find and a ceiling
opening is occluded from anywhere more than about two metres away, which is §9's subject arriving
in the viewfinder before it arrives in the sensor. But it does mean these are a first pass and
that a scouting run of the kind `CINEMA.md` describes — photograph the candidates, choose by
looking — has not been done for the vertical set.

---

## 7. What it costs, and what broke

**Measured on the machine described in `NOTES.md` §1, 1920×1080, seed 7. The machine throttles
hard (`cool.sh` documents a 2.7× SM clock throttle at 87 °C), so absolute frame rates are bracketed
rather than quoted.** No other Godot process was on the GPU for these runs; two were earlier and
those runs are discarded.

### Generation and scene

| | flat (1 level) | vertical (4 levels) |
|---|---|---|
| topology | **6.6 ms** | **42.7 ms** |
| dressing | 520 ms | 1369 ms |
| stations / edges / chambers / junctions | 351 / 8 / 4 / 7 | 1061 / 25 / 29 / 21 |
| pitches | 0 | 9 |
| open cells | 2 006 of 19 304 | 6 924 of 77 216 |
| shell triangles | 113 656 | 370 546 |
| prop instances | 19 015 in 946 multimeshes | 57 411 in 2 597 |
| chunks | 49 | 272 |
| video memory | 189 MB | 204 MB |
| walk length | 154 m | 495 m |

Topology is still linear and still trivial: 42.7 ms **in GDScript** for four levels of a 144 m
stretch. `NOTES.md` §8's advice stands — budget off the topology numbers and re-measure dressing
after the Rust port.

### Frame rate

Two flat runs bracket the session, because the second one is 40% slower than the first on
identical code:

| run | fps mean | p50 | p05 (worst 5%) | min | GPU p50 | GPU p95 | draws p50 |
|---|---|---|---|---|---|---|---|
| flat, cold | 262 | 238 | 142 | 141 | 3.55 ms | 4.76 ms | 306 |
| **vertical** | **174** | **168** | **133** | 11 | **4.91 ms** | **6.20 ms** | 268 |
| flat, hot | 155 | 141 | 106 | 102 | 4.39 ms | 6.58 ms | 305 |

**The vertical cave sits inside the flat cave's own run-to-run band.** The number that is not
noise is the GPU frame time: **3.55–4.39 ms → 4.91 ms**, about +20%, for four times the cave, four
times the geometry and a 96 m visibility range on nine shafts. Draw calls went *down*, because 3D
chunk keys cull better than XZ columns did.

**One real stall, and it is reproducible.** 62 frames of the 13 715-frame walk fall under 40 fps,
**all of them inside a 0.9-second window at elevation −20 to −30 m** — the moment the walk drops
out of the moulin and a whole level's chunks become resident at once. CPU max 108 ms against a p50
of 6.65 ms. It is chunk-entry pipeline compilation, which `NOTES.md` §5.2 already identifies and
which Godot's pipeline pre-compilation would remove. **It will get worse, not better**: the real
game enters a level by falling into it.

### What broke

1. **The exposure contract. 8 of 11 vertical frames fail, and every one fails for being too
   dark**, not too bright — the opposite of what THE-ICE §2.4 expected from daylight down a
   moulin. `v4`, `v8` and `v2` are 98–99.9% true black against a 70% floor.

   The cause is measured and is not the ice: it is **the wetness field**. `cave/PHOTOREAL.md`
   already found that *"'legible' going UP across the set while the floor albedo went DOWN is the
   wetness field — a wet surface returns a specular lobe where a dry one returned nothing"*. Below
   the melt front `wet` is 4–26 of 255 by rule, so the deep level returns almost no specular at
   all. **The melt front is legible in the histogram**, which is a good thing the fiction did not
   ask for and a broken contract at the same time.

   THE-ICE §6.1 proposes an exposure row of its own for the **ice** band because it is too bright.
   The measurement says the **dry** band needs one too, for the mirror-image reason. Both come out
   of the same field.

2. **The ceiling invariant, now that it can be checked, is violated once** at seed 7. Two adjacent
   chambers at different floor elevations: the lower one's neighbour is taller than it is. One in
   1061 stations, and it is a real generator bug rather than a measurement artefact. It is
   reported every run (`ceiling invariant: N violations`) and it is **not** fixed here, because
   fixing it means deciding whether a chamber grows or its neighbour shrinks and that is a
   generation-rule decision rather than a bug fix.

3. **`ART-DIRECTION` §3.6's sightline statistics are now wrong**, as THE-ICE §2.4 warned. The
   longest sightline in the flat cave was 49.8 m; the deepest winze is a 33.6 m straight line
   with a light at the top of it, and the collar-to-level-3 axis spans 83 m. The median almost
   certainly has not moved. **Nobody has re-run `docs/art/probes/sightlines.py` against a layered
   cave** and it should be re-run before any art budget is re-scoped.

4. **The trailer cut did not break**, but it is now pinned by a flag rather than by there being
   only one cave. The day the cut is re-shot, `--levels` should default to 4 and the frozen flat
   path in `topology.gd` should be deleted. It is marked in the file.

---

## 8. What was deliberately not built

- **Rope, winches, descent modules, a `ClimbClass` on a chassis.** THE-ICE §5.6 refuses the first
  three and flags the fourth as scope. The topology now *carries* what a chassis gate would need
  (`P_CLIMB`, `P_BORE_MM`), and nothing consumes it, because `CLAUDE.md` says do not add features.
- **Falling wrecks.** THE-ICE §5.1 raises it and defers it to the designer (§9 Q10).
- **Ice as an event** — a melting plug, a collapsing bridge. THE-ICE §6.6 refuses it and this
  build refuses it too. The melt front is a place. It does not move during a match.
- **Slip on ice.** THE-ICE §6.4 proposes it *with a measurement protocol attached* because the
  idea has been built and cut once already. It is a sim mechanic and there is no sim here.
- **True subsurface scattering.** §4.1.
- **LOD.** §5.

---

## 9. Can a machine know how deep it is?

**THE-ICE §6.2's claim is that it cannot. The claim holds, and the built sensor is worse than the
claim. But the claim is currently false in the built code, for a reason that has nothing to do
with the sensor.**

Read from `spikes/godot/cloud/` (read only; nothing there was touched).

### 9.1 The envelope, and the two blind cones

The cloud spike builds `DESIGN-PRINCIPLES` §8's recommendation exactly: **32 rings over −30.0° to
+12.0°**, uniform 1.355° spacing plus ±0.08° per-emitter calibration jitter, 1024 azimuth steps,
10 Hz, 0.55–40 m, 32 768 shots per revolution.

- **Nadir is never sampled.** There is a **60° cone of no data straight down**.
- **Zenith is never sampled.** There is a **78° cone of no data straight up**.

Both numbers against this cave's own geometry:

| | measured against the built cave |
|---|---|
| From the lip of the **moulin** (bore 2.20 m, r 1.10 m), the lowest thing a −30° beam can strike is the opposite wall at r/tan30° = **1.90 m** below the head | the drop is **14.7 m**. It reads as a 1.9 m step |
| From the lip of the **deepest winze** (bore 1.84 m) that figure is **1.59 m** | the drop is **33.6 m** |
| The **crevasse** is 0.74 m wide: the opposite wall is 0.64 m down | the drop is 14.7 m and the class is `VERTICAL`. A machine that walks into it is not descending |
| A **chamber crown** at 6.75 m needs h/tan12° = **31.8 m** of standoff to be sampled at all | the widest chamber is 14.4 m across and the range is 40 m. **Chamber ceilings are never in the beam pattern** |

**That last row is the one nobody has said out loud.** It is not only that a machine cannot see
*down* a pitch. **It cannot see the ceiling openings either** — the aven, the collapse, the hole
the shaft it fell down made in the back of the chamber it is standing in. `shots/vertical/v2` and
`v3` are pictures of a thing no machine in this game can perceive. **So a machine standing below
the one route it could climb out by cannot tell that the route is there.**

### 9.2 It cannot even record that nothing came back

The built scan discards a miss: `if r.is_empty(): continue`, and sub-minimum-range hits likewise.
The output arrays contain **hits only**, and `n_dropped` is a bare counter on the scan object
rather than a published signal.

**So free space and unmeasured space are indistinguishable in the data the belief layer receives.**
A machine that fires 4 300 beams into a hole and gets nothing back has, in its belief, exactly the
same record as a machine that never fired at all. It cannot represent "there is a hole here",
which is a stronger and more useful statement than "it cannot see down".

### 9.3 There is no other instrument

Exhaustive search of `spikes/godot/cloud/` and of `THE-SENSOR-AND-SLAM.md` for
`altimeter | barometer | IMU | inertial | gravity | accelerometer | gyro | inclinometer |
magnetometer | compass | pressure | wheel encoder`: **zero hits.** Localisation today is dead
reckoning plus fixes on beacons the machine dropped itself — *"it never compares what it is seeing
now against what it has seen before. There is no feature extraction, no data association, no scan
matching, no map optimisation."*

And a smooth ice bore is the case that would defeat scan matching if it existed:
**degenerate along its own axis and rotationally symmetric**, so there is no azimuthal lock either,
and ice-polished walls have no fracture features to extract in the first place. The dressing now
enforces the smoothness (§4.1) rather than assuming it.

**Which gives the sharpest formulation of the mechanic, and it is not in any document:**

> **A machine's depth error grows with distance walked, and a fall contributes no odometry at
> all. Falling is the only way down. So the vertical axis is the one dimension in which a machine's
> uncertainty jumps discontinuously — and it jumps at exactly the moment it commits.**

That is drift's vertical analogue and it is strictly worse than drift, because drift is gradual and
this is not.

### 9.4 But it is currently false in the built code, and this is a leak

`spikes/godot/cloud/lidar_root.gd` assigns the believed pose's vertical component **straight from
ground truth**:

```
bp.y = tpos.y                                        # :476, :479
var org := Vector3(bpos.x, s.out_org[i].y, bpos.z)   # :742-744
```

with the comment *"the y datum is measured, not dead-reckoned, so drift is planar (as in phase1)"*
— and `out_org` is declared *"true sensor origin, for stats only"*. `LIDAR.md` §9.4 records it as a
known limitation: *"Drift is planar. Height is measured, not dead-reckoned, as in phase1. Whether
Phase 3 agrees is a sim question."*

**On a plane that is a defensible simplification. On a vertical cave it is the invariant.**
`CLAUDE.md`: *"An agent's policy may never observe ground truth."* The height is asserted, not
sensed, and there is no instrument anywhere in the model that could sense it. Once depth is the
risk gradient, a belief pose whose Y comes from `World` hands the policy the one number the whole
design says it must not have.

**I have not touched it — it is outside this directory — and it is the single most important thing
in this document.** Whoever owns the cloud spike should be told before the vertical cave lands in
the sim, not after.

### 9.5 What it would take to make the blind cone deliberate

Five things, in the order they should be done.

1. **Delete the truth read.** Dead-reckon Y like X and Z, and let a fall contribute nothing. This
   is the whole mechanic and it is a two-line deletion plus whatever it breaks. It is also the only
   one of the five that is not optional.
2. **Publish the no-return.** Returns per sweep and *how much of the last sweep came back at all*
   are already in `BELIEF-CATALOGUE.md`; what is missing is that a miss is discarded before it can
   be counted. Publish it and "the map goes thin here" and "nothing came back downward" become
   learnable, through signals built for other reasons. **This is the difference between a machine
   that is blind and a machine that knows it is blind**, and only the second one is a game.
3. **Write the envelope down as an instrument property, not a constant.** `DESIGN-PRINCIPLES` §8
   already wants the sensor to be a gameplay object: *"a better sensor is a real advantage."* A
   downward-looking module that buys −30° → −75° is then a real upgrade with a real reason to
   exist, and the blind cone stops being an accident of the default and becomes the thing you pay
   to fix.
4. **Add `pitch_ahead` as a derived belief signal** — THE-ICE §5.4 note 3's own suggestion.
   Derived from returns, legal under §9's truth-leak test, and *frequently wrong*, which is the
   good kind of new signal. It is what lets a player author "do not walk off things" as a
   behaviour rather than as a prayer.
5. **Say it in the art direction.** `ART-DIRECTION` §8.2 already forbids drawing anything into a
   sensor shadow. The blind cone below a machine is the largest sensor shadow in the game and it is
   permanently attached to the machine. The spectator view should show it as a shadow, because a
   viewer who can see the cone understands the mechanic in one frame.

**My recommendation is THE-ICE §6.2's third option, without hesitation: make the blind cone the
mechanic.** A machine that walks into a winze because it physically cannot see down is
`DESIGN-PRINCIPLES` §8's own sentence — *"occlusion is the machine's ignorance made visible"* —
pointed at the floor. It costs nothing to build. It costs one deletion to stop cheating at.

---

## 10. Design problems found, which are not art problems

1. **The invariant leak in §9.4.** The most serious thing in this document.
2. **A machine cannot see the way out.** §9.1. The up-routes are ceiling openings and ceiling
   openings are outside the beam pattern at every standoff the range allows. If the designer wants
   the "I am not sure I can get back" tension to be *playable* rather than merely fatal, something
   has to make an up-route perceivable — a beacon dropped at the foot of one, a draught, the
   Assayer's sound arriving from the wrong direction. That is a content decision and it should be
   made deliberately rather than discovered.
3. **A pitch is a place a wreck comes to rest, and wrecks now fall.** `GLOSSARY`'s wreck *"persists
   for the match, holding its cargo and its policy"*. A wreck at the bottom of a `VERTICAL` pitch is
   cargo you can see and cannot have, which is exactly this game — and it is also a way to lose a
   policy permanently. THE-ICE §5.1 raises it; it still needs a ruling.
4. **The melt front is invisible to the exposure contract and visible in it at the same time.**
   §7. The art rule says *no boundary marker of any kind* — the front is legible because things
   stop. The histogram agrees so strongly that the frames fail CI. One of the two has to give.

---

## 11. Everything I guessed, in one list

Anything below is mine, not read out of a document. THE-ICE's own guesses are not repeated here.

1. **The whole depth stack, compressed.** THE-ICE §5.2 gives the bands as 0/−30/−80/−250 m and
   says *"the ratios matter more than the numbers"*. This spike uses **0 / −15 / −38 / −72 m**, a
   compression of about 2.2×, so the whole section renders and so a chamber one level down is
   inside the lamp's reach. The ratios are kept; the metres are not THE-ICE's.
2. **The four level datums** −11, −26, −49, −83 m, and **four** as the level count.
3. **The level lengths** — 760, 900, 1000, 700 per mille of the stretch, chosen so most of the
   cave is the mine and level 0 is the short one.
4. **The main descent leaves at 88 / 88 / 85 per cent along each level**, and levels alternate
   direction. That is a switchback mine; the design never says the cave is one.
5. **The melt front at −60 m**, and the whole reading of `melt_mm` that puts it there. THE-ICE
   §5.4 says *"above it running, below it dry, silent and older"* while §5.2 says band 2 is
   *"flooded to the tide mark, and rising"*. **Those are two different water surfaces and the
   document does not say which is which.** I took §5.4 literally: the front is the leading edge of
   water descending, everything above it is wet, everything below it has not been reached, and the
   ponded water sits on each wet level's own low ground. Under the other reading the deep level is
   drowned rather than dry and the strongest world object in §4.2 does not exist. **This needs a
   ruling and it changes what the deepest level is.**
6. **Every threshold in the climb rule** — 400 mm, 2200 mm, 14 m for a fixed ladderway, 30 m for a
   collapse, 45 m and 1100 mm bore for a pitch, 900 mm for "not a route at all".
7. **That polished ice demotes a climb class by one, and that a collapse is exempt.**
8. **That `down` means "under control" and `VERTICAL` means "entering it is a fall".** The brief
   says a link must be able to say down, up or neither; the four classes and which two bits each
   sets are mine.
9. **That there is an up-route for every level pair except the last.** This is the whole
   commitment gradient and it is a rule I invented.
10. **Every bore**: collar 2.6 m, moulin 2.2 m, winze 1.6–2.0 m, ore pass 0.95–1.08 m, aven
    1.3–1.8 m, collapse 2.8–4.2 m, crevasse 0.62–0.86 m.
11. **The nine-pitch set itself** — one collar, three on the main chain, two collapses, one ore
    pass, one aven, one crevasse — and that secondary pitches are found by scanning the level above
    for the station nearest a chosen one below, within 5 cells.
12. **Every radius function in the second profile family**, the corkscrew rate (`t·h·0.22` radians
    per metre at 0.32 bore of amplitude), and the ring spacing of 0.55 m.
13. **`worked` by band** — 0–28 / 48–140 / 165–250 / 200–255, and that the along-drive ramp only
    shades it.
14. **The medium rules**: ice above the ice base unless worked > 90; in the karst, ice-over-rock
    near a pitch or on a `draw_pct` under `48 − (ice_base − elev)/900`; no ice below the karst.
15. **The per-level water rule** (lowest floor + 950 mm, only above the front) and that the deep
    level is dry.
16. **Every ice scalar**: conduit ice polish 0.86 / clarity 0.78 / debris 0.16; dead ice
    0.30 / 0.26 / 0.52; a plug 0.55 / 0.66 / 0.40; and the per-kind values for pitches.
17. **Every number in `ice.gdshader`** — the absorption triple `(0.42, 0.20, 0.128)` per metre, the
    path length `mix(0.030, 0.55, clarity)`, scatter 0.26, the two scallop wavelengths (0.22 m and
    0.075 m) and their amplitudes, the 6:1 anisotropy, the roughness range 0.62 → 0.115, and the
    lamp approximation.
18. **That ice cuts the silhouette displacement to 30% and the bedding to zero.**
19. **`VIS_PITCH = 96 m`** and that it applies per chunk rather than per instance.
20. **The daylight at the collar** — one omni at 12000 K, energy 19, range 15 m, attenuation 2.6.
    `ART-DIRECTION` §2.1 gives the colour and THE-ICE §2.7 gives the reach in words; the Godot
    numbers are mine and were not derived against the §2.9 histogram.
21. **The beacon rules in a pitch** — head and foot of everything descendable, every 3.2 m on the
    main chain.
22. **The collar ring**: 16 tangential segments and four straps on a unit radius, every 1.2 m.
23. **The rubble cone** — `bore·0.62 + 0.45` m of radius, `26 + 14·bore` stones, one in nine a
    block.
24. **The chamber-hole geometry**: the dome stops below `bore/2 + 0.6 m` and a 0.34 m skirt closes
    the join. Some interpenetration remains and is visible from certain angles.
25. **Every camera in the vertical shot set.**
26. **The section's colours** and that a schematic is the right answer for the wide view.
27. **That `depth_mm` is derived rather than stored**, and that `S_FLOOR_MM` should change meaning
    rather than gain a sibling.
28. **That the chamber row should carry `level` and `running`** rather than those living on a
    separate `AncientSite` table this spike does not have.
