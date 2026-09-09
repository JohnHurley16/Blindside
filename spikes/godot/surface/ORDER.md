# Order pass — placement rebuilt as arrangements, 2026-09-09

The third pass over this spike. `NOTES.md` is the pipeline, `PHOTOREAL.md` is the material
and lighting pass, **this is the placement pass**, and where it disagrees with either of the
other two about how an object gets its position, this one is current.

It exists because of one sentence, said looking at the yard:

> *"idk what you are doing... the random shit thrown all over on the surface looks like an
> abandond scrap yard and that is not the vibe at all"*

The verdict is right and the fault was in the brief, not in the execution.
`DESIGN-PRINCIPLES` §4 asked for detail at three scales without saying detail **of what**,
and weighted random scatter is the fastest way to fill a frame. It is also exactly how you
draw abandonment. §7, written the same day, is the correction and is the spec this pass
implements.

Before/after pairs: `shots/order/before/` and `shots/order/after/`, seven identical camera
poses, 1920 × 1080, `--mode=oshots --tag=before|after`.

---

## 1. What was actually making it read as abandoned

Read off `shots/order/before/*.png` and then traced to the rule that produced it. Every one
of these is a *placement* fault; not one of them is a material, a mesh or a lighting fault.

| What the frame shows | The rule that produced it |
|---|---|
| Objects at unrelated angles, each on its own little mat | `_cluster(kind, o, r.randf() * TAU)` — every cluster got a uniform random yaw, and several kinds drew a base plate under themselves |
| Nothing aligned to anything else | position was `x + randf(-0.9, 0.9)` on a 2.35 m lattice — the lattice was never visible because the jitter was 77% of the pitch |
| No two objects that belong to the same task | the kind was `YARD_KINDS[randi() % 22]` **per cell**, so a genset, a tyre stack and a gas rack could land within 3 m of each other with no relation |
| Loose chippings evenly over the whole site, including the ground machines walk on | `_pad_chippings` seeded `62 × 52 × 9 = 29 016` stones uniformly over the hardstanding — 34% of every prop on the site was one stone lying on the concrete |
| Weeds growing through the middle of the working apron | `_weeds` seeded 2.2 tufts per metre of **every** slab joint on the pad, plus 0.22/m² over open ground, with no notion of a route |
| Cables snaking across the middle of open concrete | `_ground_cables` ran six sine-perturbed runs corner to corner across the pad |
| Litter spread thinly everywhere | `_litter` at 0.16/m² over the whole pad |
| Standing water in front of the service bay | `pond` in `ground.gd` was a pure lowness field with no idea which ground is driven |
| **The charge row: grey posts on orange mats with no machines in them** | five pedestals in `kitgrey` (0.198 albedo) each with a separate 1.5 × 1.4 `amber` ground box offset 0.9 m sideways, and only 3 of 5 machines placed, at a scale that lost them in the clutter |
| **The service bay's contents invisible** | fully roofed, every fourth sheet a rooflight, and the only machines were 6 m east of the bench so no frame held both |
| Signs at random angles | `yaw = r.randf_range(-0.5, 0.5)` per sign |

Two things I would add to the designer's list:

- **The clusters were fine; the placement was not.** Twenty-two of the twenty-two cluster
  generators drew a sensible object. A gas-bottle cage is a good object. A gas-bottle cage
  at 47° in the middle of a lane is litter. The vocabulary was never the problem.
- **The site already knew where everything was.** The plan carries the pads, the buildings,
  the zones, the course, the fence and six walkways. Dressing was only using that list to
  say *no* (don't block a walkway). It was never using it to say *yes*.

---

## 2. The rules this pass implements

Straight out of `DESIGN-PRINCIPLES` §7, restated as things a generator can do.

1. **Every object answers who put it there and why.** No object is placed because a
   probability said so. Randomness picks which *arrangement* fills a stand and what that
   arrangement holds; it never picks the position or the angle of an individual object.
2. **Placement is arrangements, not scatter.** Twelve arrangements, each with a footprint,
   an internal pitch, an alignment and one kind of contents. §3.
3. **Align to the site's own grid.** Every stand's yaw is 0° or 90° to the site box. The
   only jitter anywhere is ±2° on a pallet, and it is deliberate.
4. **Clear ground is a feature.** The layout now declares *keep-clear* ground — the collar
   turning circle, the service-bay apron, the charge frontage, the muster square, the course
   apron — and nothing, prop or chipping or weed, may be placed on it or on a walkway.
5. **Weeds, debris and standing water in the margins only.** Off the concrete, in the outer
   2.6 m of the pad, at the fence foot and behind the buildings. Nowhere else.
6. **Repetition reads as manufactured.** Five identical charge pedestals on one plinth on an
   exact 2.4 m pitch, four of them with a machine standing in a numbered painted bay.
7. **The pit-head is live.** Somebody swept this yard this week: lanes and the turning circle
   are painted, and the swept ground is swept.

---

## 3. The arrangement vocabulary

Twelve arrangements in four classes. A **stand** (§4) is a rectangle with a yaw and a class;
dressing rolls one arrangement of that class and fills it. Sizes are in metres. The stand's
own frame is `u` along the run and `v` across the depth; every item is positioned as a
multiple of a pitch in that frame, never as a random offset.

| # | arrangement | class | footprint | internal pitch | alignment | contents |
|---|---|---|---|---|---|---|
| 1 | `rack_run` | stores | the stand, 3.6–8.4 × 3.0–4.5 | uprights 2.4 m, shelves at 0.52 / 1.52 / 2.52 | square, no jitter | **one** kind for the whole rack: three totes per bay, one palletised load per bay, or five lengths of pipe per bay |
| 2 | `stillage_block` | stores | the stand | 1.35 × 1.15 grid | square, no jitter | mesh stillages, all one way up, back row stacked two high |
| 3 | `pallet_row` | stores | the stand | 1.35 along, 1.30 across | square ± 2° per stack | identical banded loads, one height for the whole stand, 2–4 high |
| 4 | `pipe_laydown` | lay-down | the stand | three transverse bearers at ¼ of the run | square | 5/4/3 pipes in a pyramid, all parallel, ends flush, chocked both ends |
| 5 | `section_laydown` | lay-down | the stand | as above | square | rolled sections instead of pipe |
| 6 | `plate_laydown` | lay-down | the stand | packers at 0.35 of the run | square | 3–6 plates flat, every edge flush, corner marked with a post |
| 7 | `bunded_drums` | consumables | the stand, kerbed on four sides | 0.78 m grid | square | drums, upright, one material, placards on the front row, spill kit at the head |
| 8 | `bottle_rack` | consumables | the stand | cages at 1.9 m | square | identical gas cages, six bottles each, chained by a top rail |
| 9 | `reel_stand` | consumables | the stand | stands at 2.6 m | square | two cable reels per stand on a common shaft, all axes parallel |
| 10 | `marked_bay` | marshalling | the stand, painted outline | — | square | one thing parked squarely, **or nothing at all** (40%) |
| 11 | `trolley_queue` | marshalling | the stand, painted outline | trolleys at 1.7 m | square | identical trolleys nose to tail, all facing the head of the bay |
| 12 | `skip_bay` | marshalling | the stand, painted, kerbed | — | square | one skip. **The only object on the site whose contents may take a random angle**, because the honest answer to "who put it there" is "somebody threw it away" |

Plus four fixed arrangements attached to named site features rather than to a stand:

| arrangement | where | rule |
|---|---|---|
| `dock_line` | the `charge_row` zone | one cast plinth 11 × 1.3 m; five identical pedestals on an exact 2.4 m pitch; a painted, numbered, chevroned 2.1 × 2.2 m dock bay in front of each; four machines standing in them, one bay left empty with its cable coiled on the hook; one straight trunking run behind; the battery skid square to the head of the line |
| `muster_rank` | the `muster` zone | four painted bays on one pitch, four machines, one yaw ± 1° |
| `pallet_yard` | the `pallets` zone | rows on 1.35 × 1.30 with a 2.4 m aisle down the middle; one load and one height per row |
| `spares_rack` | the `spares` zone | uprights on 2.4 m, three levels, **one kind of stock per bay** |

Every arrangement also gets a **bay plate** — a numbered plate on a galvanised post at its
head. It is four instances and it is the object that says a person numbered this bay.

**Markings** are their own rule and the cheapest thing in the pass: a dashed edge line
(1.2 m mark, 0.9 m gap, 0.17 m wide) each side of all six walkways, clipped at the turning
circle so six lanes do not converge into a starburst, plus a 40-chord painted circle at
r = 10.4 m round the collar. About 150 instances for the whole site.

---

## 4. Where the layout/dressing line now sits

The test in `NOTES.md` §1 is unchanged: *could you delete this object and have a machine walk
a different route, or a rule score differently?* Arrangements straddle it, so the line is
drawn inside the arrangement:

> **LAYOUT decides where a stand is, how big it is and which way it faces.**
> **DRESSING decides what stands in it.**

A stand is occupied ground — a machine cannot walk through a rack — so a stand is exactly as
much layout as a zone is, and it is decided by integer arithmetic in `scripts/layout.gd`
with no floats and no dictionary iteration:

| New in LAYOUT (`layout.gd`) | New in DRESSING (`props.gd`, `scatter.gd`, `ground.gd`) |
|---|---|
| `ranks` — ten hand-listed strips of ground, each `[x, z, run, depth, axis, class]` | — |
| `stands` — the bays cut out of those ranks by `_stands()`: a seeded length on the 1200 mm module, a seeded gap, rejected if it fouls a building, a zone, a walkway or a swept apron | which of the three arrangements of the stand's class fills it, and everything inside it |
| `clear_r` / `clear_rects` — the turning circle and the four swept aprons | the paint that makes them legible |
| `swept(x, z)` — is this ground a lane, a circle or a working apron | asks it before dropping a chipping, a weed, a bolt or a piece of litter, and before letting the ground pond |
| `in_stand(x, z)` — does an arrangement occupy this ground | asks it before dropping anything underfoot |

Randomness in `layout.gd` (stream 5, the new one) sets bay lengths and the gaps between them
and **nothing finer**. It never sets the position or angle of an object. The class of a bay
comes from its rank, which is hand-listed; the arrangement comes from the dressing RNG.

`_stand_ok()` is integer throughout. The walkway test walks the centreline in ~300 mm steps
and asks whether each point is inside the bay grown by the walkway half-width, which needs no
square root and no signed division. `swept()` does need a point-segment projection, so it
uses `num/den` integer division on the dot products — deterministic, and the only division in
the file that is not by a constant.

**The plan hash still prints on every run and now covers the new fields.** `_hash()`'s key
list gained `clear_r`, `clear_rects`, `ranks` and `stands`, so a client that disagrees about
where the racks are disagrees about the hash. Four headless runs on the final build:

```
seed 20260908  layout hash 190631341776686   51617 instances
seed 20260908  layout hash 190631341776686   51617 instances
seed 4242      layout hash 1776353373005951  50969 instances
seed 7         layout hash 1628025862058806  51149 instances
```

The hash moved from `1889570882374975` because the plan gained fields. That is the correct
behaviour and it is the same event as the walkway rule in `NOTES.md` §2.1.16.

---

## 5. What was deleted, and why

Measured, not estimated: the running instance count was logged at each build stage on both
builds from the same camera-less headless run.

| | before | after | delta |
|---|---|---|---|
| **prop instances** | **84 864** | **51 617** | **−33 247 (−39%)** |
| of which `dressing.gd` — the inherited iron | 9 379 | 9 379 | 0 (untouched) |
| of which `props.gd` — the brought | 3 959 | 3 247 | −712 |
| of which `scatter.gd` — underfoot | 71 526 | 38 991 | **−32 535** |
| MultiMeshInstance3D nodes | 1 464 | 1 347 | −117 |
| triangles across all MultiMeshes | 3 351 932 | 1 912 470 | −43% |
| draw calls, max in the bench loop | 923–930 | 697–699 | −25% |
| primitives, max in the bench loop | 2.44 M | 1.27 M | −48% |

What went, rule by rule:

| Deleted | Count | Why |
|---|---|---|
| **Uniform pad chippings, 9/m² over 3 224 m² of hardstanding** | **29 016** | Even cover over the ground a machine walks is the single strongest tell of abandonment. Replaced by three rules that each have a reason: the slab joints the sweeper never reaches, a 0.8 m lee band outside each arrangement, and the outer 2.6 m margin of the pad. Nothing on swept ground. |
| **Weeds in every slab joint across the whole pad** | ~3 800 | "Growing through the middle of a working apron says nobody has walked there in a year." Weeds now only in the pad's outer margin, off the concrete, at the fence foot, and behind the buildings. |
| **The 22-kind, p = 0.78, 2.35 m-lattice yard fill** | ~2 400 | This is the object of the complaint. Every cluster it placed had a random position, a random yaw and no relation to its neighbour. Replaced by 9–11 stands of aligned arrangements. |
| **`_yard_fill_open`, the p = 0.40 heavy-cluster sweep over the unpaved strip** | ~600 | Stock does not live on spoil. Replaced by three hand-placed margin tips, all of them behind something. |
| **Litter at 0.16/m² over the pad** | ~500 | Moved to the fence lee and the backs of the buildings. |
| **Four of the six snaking ground-cable runs** | ~180 | A cable somebody laid is straight and runs along a lane, not across it. |
| **Two thirds of the dropped fixings** | ~600 | Kept the rule ("where something was bolted, something was dropped") but halved the radius, cut the count, and suppressed it on swept ground. |
| Gravel on the unpaved ground | 0 | Untouched. That is a real gravel surface and it is outside the yard. |

Added, for scale: about 1 900 instances of arrangements, 150 of paint, and 5 more machines.
**The pass removes roughly twenty objects for every one it adds.**

---

## 6. The before/after pairs

`shots/order/`, 1920 × 1080, identical camera poses, overcast, seed 20260908.

| pair | what to look at |
|---|---|
| `o01_yard_working` | Before: machines wading through weeds and litter, a rack of unrelated stock, junk boxes on rusted posts at every angle. After: painted machine bays, a racked store with one kind of stock in it, the dock line at the end of the view, swept concrete. |
| `o02_site_wide` | The whole argument in one frame. Before: a field of small dark objects at uniform density across the pad. After: two drum bunds in a grid, a rack, palletised stock in rows, pipe on bearers, and large deliberate empty aprons. |
| `o03_underfoot_45` | Before: chippings at 9/m² and weeds through the joints, on ground a machine is standing on. After: swept concrete, a painted bay, the machine standing in it. This is where "deleting props is the point" is most visible. |
| `o04_service_bay` | Before: a roofed shed with an empty weed-grown floor. After: the last 4 m of roof removed, rooflights on every third sheet, two machines on work stands in front of the bench, one parked square on a painted bay by the door, the wreck on a trestle at the back. |
| `o05_charge_line` | **The frame the complaint was about.** Before: grey posts on orange mats, no machines, weeds and standing water across the apron. After: five identical pale pedestals on one plinth on an exact pitch, four machines docked, numbered painted bays with chevrons, one bay deliberately empty, clear swept ground in front. |
| `o06_lane_clear` | Before: steel offcuts at every angle strewn across the ground the lane runs on. After: the lane, painted, empty, with a machine walking up it and the scrap in a kerbed bay to one side. |
| `o07_margins` | Where the weeds and debris went: behind the boiler house, against the fence, off the concrete. Nothing in this frame is on a route. |

---

## 7. Frame rate

Measured on the same **RTX 3080 Laptop**, 1920 × 1080, `--mode=bench --secs=40 --light=overcast`,
the fixed 14-waypoint camera path. **Interleaved A/B/A/B**, because this machine's run-to-run
drift on an identical build is larger than the change: the before build was stashed back to
HEAD between runs and restored after, so both halves ran under the same thermal conditions.
Raw log: `perf/order_bench.txt`.

**Condition, stated because it matters:** no stray Godot processes (checked before every run;
the "1" in the log is the previous run's process still exiting), but the GPU was **68–88%
utilised by other applications** for the whole session, at 780 MHz against a 2100 MHz maximum
and 80–82 °C. Absolute numbers here are therefore not comparable to `PHOTOREAL.md`'s
clean-machine table (13.72 ms mean overcast); only the paired ratios are.

| run | mean | median | p95 | worst | draws | prims |
|---|---|---|---|---|---|---|
| AFTER  | 16.69 ms — 59.9 fps | 16.67 | 20.83 | 37.83 | 687 | 1.23 M |
| BEFORE | 17.66 ms — 56.6 fps | 18.06 | 22.22 | 24.87 | 924 | 2.44 M |
| AFTER  | 16.54 ms — 60.4 fps | 16.67 | 20.00 | 50.70 | 685 | 1.23 M |
| BEFORE | 17.75 ms — 56.3 fps | 18.06 | 22.22 | 54.36 | 922 | 2.44 M |
| AFTER  | 16.60 ms — 60.2 fps | 16.67 | 20.37 | 21.88 | 699 | 1.27 M |
| BEFORE | 17.75 ms — 56.3 fps | 18.06 | 22.22 | 24.61 | 923 | 2.44 M |
| AFTER  | 16.54 ms — 60.5 fps | 16.67 | 20.37 | 30.43 | 697 | 1.27 M |
| BEFORE | **14.30 ms — 69.9 fps** | 14.13 | 18.33 | 56.26 | 930 | 2.44 M |

Also measured on the after build: rain **20.76 ms mean / 38.91 worst**, dusk **21.42 ms mean
/ 52.98 worst**, both under the same contention.

**The honest reading.** Three of the four before runs sit tightly at 17.66–17.75 ms and all
four after runs sit tightly at 16.54–16.69 ms, which is a **1.1 ms / 6.5% mean improvement**.
The fourth before run came in at 14.30 ms — faster than any after run — on the one occasion
the GPU was at 78% rather than 81–85%. A 3.5 ms swing on an identical build is larger than a
1.1 ms delta, so **I will not claim the frame-time improvement.**

What is outside the noise, because it is counted rather than timed:

- **submitted geometry roughly halved**: 2.44 M → 1.27 M primitives, 3.35 M → 1.91 M triangles
- **draw calls down a quarter**: ~925 → ~698 max in frame
- **prop instances down 39%**, MultiMeshes down 117

One number that is clean, because it is CPU-side and not contended: **generation time fell
from ~3 300 ms to ~2 470 ms**, almost all of it in the scatter pass (1 750 ms -> 970 ms),
because the deleted rules are the ones that called the height query most.

**Conclusion:** the pass does not cost frame rate and removes about half the work the GPU was
being handed, but on this machine it does not on its own restore the 60 fps floor. That is
still the decision `PHOTOREAL.md` leaves open — screen-space ambient occlusion at 4.2 ms of a
13.7 ms clean frame — and it is unchanged by this pass. Deleting props helped; it is not the
lever.

---

## 8. What is still weak

1. **The ranks are ten hand-written strips.** Same criticism as `NOTES.md` guess 21 about the
   walkways: a real generator would derive stores runs from the buildings, the pad edges and
   the circulation graph rather than list them. Two of the ten had to be nudged by hand after
   the first run because the rejection test threw away every bay in them, which is exactly the
   symptom of a rule that should be derived rather than listed.
2. **`_stand_ok` only rejects; it never relaxes.** A rank whose bays all foul something
   produces nothing, silently. On seed 20260908 that lost the whole marshalling class until
   the rank was split either side of the haul road. A real version wants the rule to shorten a
   bay rather than discard it.
3. **The arrangement footprints are not checked against their contents.** A `rack_run` in a
   3.0 m-deep stand and one in a 4.5 m-deep stand hold the same tote clamped to 1.05 m deep;
   the deep one has a metre of empty shelf. Nothing looks wrong yet, but nothing stops it.
4. **The machines are still the placeholder dolls** (`NOTES.md` §7.2) and still do not move.
   `NOTES.md` §7.4 stands and is now the biggest remaining thing between this yard and one
   that looks staffed: nothing on this site moves at all.
5. **Underfoot on the swept apron is now shader-only.** Removing the loose stock from the
   working ground is right, but it means the last metre and a half of a lane is carried
   entirely by the ground shader's parallax and aggregate. `PHOTOREAL.md` §7.3 already says
   that is the weakest scale; this pass makes the swept parts of the site lean on it harder.
6. **Only one seed was looked at hard.** Seeds 4242 and 7 produce different hashes and 8–11
   stands, but I have not looked at either yard.
7. **The paint is one flat colour with a dirt term.** Real line marking is worn where the
   wheels run and intact between them, which the ground shader's `traffic` field already
   knows about and the paint does not read.
8. **Two lanes run straight through the service bay**, because two of the six layout walkways
   cross its footprint. It reads as a drive-through bay, which is defensible, but nobody
   decided it.

---

## 9. Every guess in this pass, in one list

Additions to `NOTES.md` §9; strike them individually.

1. **The layout/dressing line runs through the middle of an arrangement**: layout owns the
   rectangle, the yaw and the class; dressing owns the contents. Invented here, and it is the
   most consequential decision in the pass.
2. **A stand is not walkable.** Declared, not verified — nothing in this spike builds
   colliders, so "occupied ground" is an assertion about a future navmesh.
3. **Ten rank lines, hand-placed**, with classes assigned by hand. A different set of ten
   would produce a different yard.
4. **Bay lengths 3.6–8.4 m on the 1200 mm module, gaps 1.2–3.6 m, 700 mm clearance to
   everything.** Tuned by eye.
5. **Twelve arrangements in four classes.** The set is invented; there is no reason it is
   twelve rather than eight or twenty.
6. **The turning circle is 11 m radius** and the four swept aprons are the sizes listed in
   `layout.gd`. Invented.
7. **The yard is line-painted at all**, in a worn yellow-white. Nothing in the design says the
   players' register paints the ground, and it is doing a great deal of work in the frame.
8. **A `paint` material was added** — the twenty-third material and the first new one since
   the photoreal pass. Linear albedo 0.500 → 0.690 after the first pass read brown at
   distance.
9. **Four of five dock bays are occupied and the fifth is empty on purpose.** The empty bay is
   a storytelling decision, not a simulation one.
10. **The service bay's last 4 m of roof is open** and rooflights went from every fourth sheet
    to every third. `NOTES.md` §7.8 called this a layout decision; it is still implemented in
    dressing, because the plan's `roof` flag is a boolean and nobody has decided what a
    partially roofed building is in the plan.
11. **The wreck moved inside the service bay.** Previously it lay in the open yard. A lost
    machine being recovered to the bay is a fiction decision about what happens after a raid.
12. **Weeds are allowed within 2.6 m of the pad edge.** The margin width is invented.
13. **Ponding is damped to 28% on swept ground.** A number, chosen because a lake across the
    service-bay apron read as neglect.
14. **The skip is the only object allowed random angles.** Stated as a rule so that the next
    person to add a generator has one place to put "somebody threw this away".
15. **Machine count rose from 12 to 15** and their poses are hand-placed against named site
    features rather than seeded.
