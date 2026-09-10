# Act I, re-authored against the valley — 2026-09-10

`spikes/godot/surface/`, Godot 4.7.2, Forward+, Vulkan, RTX 3080 Laptop.
Ten trailer shots — **2, 3, 4, 5, 6, 7, 12, 13, 14, 28** — re-authored, re-framed and
re-rendered at full duration against the world `VALLEY.md` built.

Read `CINEMA.md` first: the camera rig, the site anchor, the post stack and the reasons are all
there and none of them changed. This document is what the *shots* became. Where the two disagree
about a framing, a lens or a light, **this one is current**; where they disagree about a rule,
`CINEMA.md` is still the rule.

Nothing outside `spikes/godot/surface/` was modified. Nothing was committed.

---

## 0. The short version

| | |
|---|---|
| **Does the trailer still open on the headframe?** | **No. It opens on the valley**, and it should. `shots/cinema/seq/t02_valley_first_light/000.png` is the first frame of the trailer: alpenglow on the ridge, the town lit on the far wall at 900 m, the floor in shadow, the works 170 m away and 90 px tall. §2. |
| **How many execute?** | **All ten**, including shot 14. Ten of fourteen; the four `xfail`s still fail, correctly and for their own reasons. |
| **Is the descent solved?** | **Yes, and it is the largest thing in this pass.** A shot may now declare that it is **carried**, and travel, speed and height are measured in the carrier's frame while every physical rule still runs in world space. The cage genuinely moves. §6. |
| **Does shot 6 land?** | **Yes.** Machine height, 50 mm at T4, on open snow, five seconds, and its head comes round to the lens over the last two. The contrast reverses exactly as `machines/NOTES.md` §15 predicted it would: dark legs and graphite chassis against white. §4. |
| **Is it the same machine everywhere?** | Yes, and it is measured rather than asserted: `hero_boxes.json` has its screen rectangle in four shots, `Hero.validate` runs inside the rig's validate, and shot 28 says `role: "none"` out loud. §5. |
| **Render time for the act** | **807.7 s of shot time for 1 008 frames — 0.80 s a frame**, 13 min 43 s wall for the ten-shot pass including the 40 s scene build. §7. |
| **Frame rate, quiet machine** | **15.97 ms mean — 62.6 fps; 27.64 ms worst — 36.2 fps.** §7.1. |
| **New tooling** | `--cinema=look`: three frames a shot instead of a hundred and twenty. It is the reason this pass could iterate five times. §7.2. |
| **The honest verdict** | Six of the ten are frames I would put in a trailer. Shot 4 is not, and the reason is not the camera. §8. |

---

## 1. What changed, and what did not

`CINEMA.md` §0 and §10 hold in full. The 0.35 m body, the 0.40 m near-plane clearance, the four
height bands, the 0.15–2.50 m travel window, the 1.2 m/s cap, smootherstep easing, one `lens_mm`
per shot, the site anchor's whole vocabulary, and the principle that a failure is **reported with
the number that caused it and never repaired** — all unchanged and all still governing.

What changed is the world the shots point at, and therefore every framing. The pit-head did not
move: the collar is still at the origin, `z:charge_row` is still the charge row, `course:3` is
still course node 3. **That is why this was a day and not a week** — the anchor vocabulary
survived the ice exactly as `THE-ICE.md` §7.4 said the pit-head would.

Six source files were touched, all of them inside this spike:

| file | what |
|---|---|
| `shots_cinema.json` | rewritten: ten shots re-authored, four `xfail`s kept verbatim |
| `scripts/cinema.gd` | the **mount frame** (§6), the carrier collision exemption, and one new ease kind |
| `scripts/batcher.gd` | a **carrier tag**, so a group of instances can be its own MultiMesh and can therefore move |
| `scripts/dressing.gd` | two lines: the cage is tagged as a carrier |
| `scripts/fleet.gd` | `hero_pose` places the machine in the mount's frame when there is one |
| `scripts/shoot.gd` | `--cinema=look`, mount reporting in the validation record, and one honesty fix in `--cinema=hero` |
| `scripts/main.gd` | one line, wiring `--cinema=look` |

---

## 2. Shot 2 is the valley, and that is the biggest single change to the act

`docs/THE-ICE.md` §8.1 rewrote this shot the day the world changed, and it argues for itself
better than I can:

> *"Today: 'the headframe against an overcast sky, slow push in from low.' Under snow and
> mountains: **the valley at first light** — the peaks lit and the floor still in shadow, walls on
> both sides, the town a line of small warm windows on the far wall at 900 m, and everything else
> white and silent. That is §10's 'monotonous and snowy and pretty' in a single frame; it
> establishes the society before it establishes the machine; and it is the one shot in the trailer
> that can carry absolute scale, because the town is in it and a town is a size a viewer already
> knows."*

**I agree, and there is a fourth argument it does not make.** `TRAILER.md` §11.1's whole diagnosis
is that the first act as written is *a tour of a place* and that the card at 0:46 therefore has no
referent. A tour that opens on a headframe opens on a **thing**; a tour that opens on the valley
opens on a **world**, and it buys the act four seconds it does not have to spend explaining where
we are. The headframe is not lost — it becomes shot 3's foreground, where it now reads as old
**against** something new, which is `DESIGN-PRINCIPLES.md` §4's two-register collision in one
frame instead of two.

**The frame.** Eye height on the valley floor, 170 m up-valley of the works, 21 mm at T4, a 1.60 m
lateral drift over five seconds, `firstlight`. The camera is a person standing on the floor: there
is no structure within 12 m to hang a crane off out there and there should not be. `v10_trailer_open`
was shot at 6.8 m and this is at 1.66 m; the composition survives the drop because the thing
carrying it is the wall, not the floor.

**Would it stop a scroll?** Yes. It is the only frame in the set where a viewer does not know what
they are looking at for a second and a half, which is the correct amount of time.

**What is wrong with it** is `VALLEY.md` §8.1's own admission and not mine: the wall's ridged bands
are too regular in period, so the corrugation reads at this scale. And the town's lit windows
cluster into an orange sparkle that at 1.6 km reads very slightly like circuitry. Neither is a
camera problem.

---

## 3. What each shot became

| # | name | lens / light | what it is now, and why |
|---|---|---|---|
| **2** | `t02_valley_first_light` | 21 mm T4, `firstlight` | **The valley, not the headframe.** §2. Eye height on the floor 170 m up-valley, drifting 1.60 m across, the town lit on the far wall, the works small in the middle distance, alpenglow on the ridge. The whole act's establishing work in one frame. |
| **3** | `t03_yard_under_the_wall` | 21 mm T4, `day` | **The yard with the inhabited wall over it.** The old note said "racks in rows, painted bays, spoil tips behind. *Somewhere people work.*" The last three words are now the frame: the headframe's sheave and legs make the left foreground, the yard and its machines run along the bottom, and the town's terraces fill the middle distance at 900 m. `THE-ICE.md` §7.2's chain of known sizes — bay, building, yard, town, ridge — in one picture. |
| **4** | `t04_melt_macro` | 50 mm T4, `snowfall` | **The weakest of the ten and the only one where the world fought back.** §8.1. `THE-ICE.md` §8.2 asks for "meltwater running off ice, macro"; the braid plain that would supply it is buried (§8.1), so the shot is the hero's own parked neighbours' feet in compacted, tracked, wet snow at the bay edge, at floor height, in falling snow. It is the only shot in the act with anything **moving** in it. |
| **5** | `t05_charge_line` | 35 mm T2.8, `day` | **The row, and the way out.** Five pedestals, machines docked, one bay empty with its cable coiled — unchanged as a subject. A 35 mm cannot hold a 4 m row and a wall 300 m away, so the valley enters down its own axis: the camera stands ten metres back on the row's centreline and looks WNW straight out through the gate, and the haul road runs away down-valley toward the foot of the town's inclined railway. The row recedes on the right, the way out is down the middle. |
| **6** | `t06_meet_the_machine` | 50 mm T4, `day` | **The shot the machines spike specified and could not site.** §4. |
| **7** | `t07_course_posts` | 35 mm T2.8, `day` | **The course, in snow, pointing up-valley.** Camera and machine unchanged from the pit-head authoring — this is the one shot whose geometry the valley did not break — but the corridor now ends on three kilometres of white and a peak, and the near wall closes the left. The best-composed frame in the set and I did almost nothing to it. |
| **12** | `t12_course_alone` | 21 mm T4, `day` | **Small, alone, and out of the furniture.** The pit-head version hung a crane at 5.5 m and looked down at 29°, which fills the frame with ground; and re-sited across the course it put the machine *inside* a corridor it could not be seen in. This one hangs at 2.8 m off lighting column 8, sits on the corridor's own axis at its west end, and watches the machine walk **away**: 48 × 84 px of machine, a corridor of black panels on the right, an open snowfield on the left, and both walls above the horizon. The card lands over this. |
| **13** | `t13_collar_above` | 21 mm T4, `day` | **The pit-head's own crane, mirrored.** 4.6 m off the headframe, looking down through its bracing at the collar as the machine walks the last two metres to the plate with its lamp on. Mirrored to the south side so that what lies beyond the collar is the yard and the far wall rather than the near wall's black rock. §8.3 records why this is the frame I would re-scout next. |
| **14** | `t14_descending` | 21 mm T2.8, `day` | **Executes.** §6. The camera rides the cage, bolted, 0.45 m above its deck, 0.55 m off the centreline because a shaft has buntons and a cage runs in a compartment. The cage descends 8 m under constant acceleration and the daylight climbs away. |
| **28** | `t28_extraction_window` | 18 mm T4, `dusk` | **The empty shaft with home in the frame.** `THE-ICE.md` §8.5: *"an empty shaft is a fact; an empty shaft with somewhere to have come back to is a loss."* Crane at 2.6 m due east of the collar looking straight down the headframe's own axis, so the two near legs straddle the frame instead of splitting it and you see *through* to the collar. Dusk, the yard lights on, the town lit on the wall behind and above, drifted snow across the pad. `role: "none"`. |

### 3.1 Three decisions inside that table worth arguing

**Shot 4 keeps `snowfall` and it is not for the weather.** `snowfall` is the only preset with
falling particles, and `NOTES.md` §7.4's *"nothing moves at all"* is the loudest thing wrong with
every other frame in this act. One shot in ten with something physically moving in it is worth more
to the cut than one shot in ten with better contrast.

**Shot 28 is `dusk` and not `snowfall`.** `TRAILER.md` §3 says rain; `THE-ICE.md` §8.5 says melt
and says *home is in the frame*. Those pull apart: `snowfall` collapses visibility to a few hundred
metres and the town — the entire point of the addition — disappears. `VALLEY.md` §5.1 already calls
`dusk` *"shot 28's frame"*, and dusk is the only state in which the town reads as **occupied**
rather than as texture. Taken.

**Shot 2 is `firstlight` and shots 3–7 and 12–14 are `day`.** That is a continuity jump inside one
act. It is deliberate and `THE-ICE.md` §8.3 asks for it: the picture runs **warm → white → black**
across Acts I–IV, and the warm third has to come from somewhere. Flagged as guess 1.

---

## 4. Shot 6, which is the most important shot in the trailer

`machines/NOTES.md` §15 is a complete specification and it was handed over rather than shipped
because the bench moved. **Everything in it was built as written.** Five seconds at 24 fps, 50 mm
at T4, the lens at **0.45 m — the machine band, not eye** — a 0.36 m push (0.14 m/s at its peak,
the slowest move in the cut), 0.22° of handheld, focus pulled 3.01 → 2.65 m onto the head, the
`idle` clip because a machine that stands perfectly still is a prop, lamp off because a work lamp
in daylight is a lighting mistake, and the head aim ramping across the shot.

Its three non-numbers were the whole job:

1. **It is on the ground.** A thing on a table is a thing being worked on.
2. **The camera is at its eye level, which means on the floor.** You crouch to meet it.
3. **Nothing tall, dark and close behind it.**

**The third is the one the valley answers, and answering it took four sitings.** The note predicted
this: *"In the valley this is free and it is better than anything the pit-head could offer: snow. A
pale machine against a white valley under a large sky is the version of this shot that the ice age
makes possible, and the contrast reverses."*

It is free in the sense that the material exists and expensive in the sense that almost nowhere on
this site points at it. The compound is 126 × 68 m inside a fence, the course fills its eastern
half with black panels, the yard fills its western half with black iron, and the near wall — 1,800 m
of rock at 300 m — is dead ahead of anything pointing south or up-valley. The four sitings:

1. **East of the course apron, looking ESE.** Rejected by the rig: an iron and a timber course
   obstacle at x = 41.7, contacts at 0.40–0.68 m. The rig was right and `--cinema=probe` named the
   two bins in one run.
2. **On open ground at z = −14, looking ESE.** Legal, and the frame has 700 m of near wall filling
   its top third and the perimeter fence crossing its left. Legal is not photographable, again.
3. **Same, at z = −8, axis swung to due up-valley.** The fence's top edge now sits *behind the
   machine's own body* — the machine is 0.55 m tall at 2.6 m and the fence is 2.4 m tall at 49 m,
   and those subtend the same 2.3°, so the machine covers the only dark line in the frame. That is
   not a trick, it is what choosing a background means.
4. **The head aim, which is not arithmetic.** The end value is *"whatever aims the head at the
   camera from wherever the camera stands"*, and the arithmetic for that is
   `head_yaw = atan2(−lz, lx)` in the machine's own frame — which gives −35° for the pit-head
   authoring and reproduces its shipped −40° to within half a degree. **It was still wrong by eight
   degrees here**, and the reason is in `machine.gd`'s own comment: `look_at_local` is an offset
   **on top of the clip**, and the `idle` clip is a head *scan*. So the aim that lands is the aim
   you looked at. Shipped at +43°, measured off a 1:1 crop of frame 113.

**Does it make you care about it?** `shots/cinema/seq/t06_meet_the_machine/108.png` is the frame I
would put in front of the designer. The whole body, the feet in, dark legs and a graphite hull
against wind-carved snow, the head square to the lens with the sonar bar and the eye lens dead on,
three kilometres of pale valley behind it and nothing in the frame it could be mistaken for. It
reads as an animal that has stopped to look at you.

**What it still does not do** is `NOTES.md` §15's own honest gap and it is unchanged: it does not
read as one whose *fate* is at stake, because nothing in the shot is at stake. The head turn buys
the attachment; the shaft puts it at risk; only the cut can do both.

---

## 5. The hero machine, in every shot that should contain one

`machines/hero.gd` is the mechanism and it runs inside `CameraRig.validate()`, so a continuity
break is reported in the same list as a camera that would fly through a wall and **the shot is not
rendered**. Five shots name the hero, one names its absence, four leave it at home:

| shot | machine | |
|---|---|---|
| 2, 3, 4, 5 | no block | the hero is on the site, standing at home. Shot 5's `_why` is the interesting one: its dock bay is the empty one with the coiled cable, because at 0:18 it is already at the course |
| **6** | `hero`, `idle`, lamp off | 778 × 707 px |
| **7** | `hero`, `walk`, lamp off | 315 × 452 px, 2.00 m in 4.0 s = exactly the 0.50 m/s the clip was baked at |
| **12** | `hero`, `walk`, lamp off | 48 × 84 px — small in frame and still above the 34 px where the chassis class stops reading |
| **13** | `hero`, `walk`, **lamp on** | 119 × 137 px. The lamp comes on here and stays on: this is the frame where it stops being a thing in a yard |
| **14** | `hero`, `idle`, lamp on | **in the shot and not in the frame.** §5.1 |
| **28** | `role: "none"` | the most load-bearing line in the file. Without it the default puts a Surveyor in the yard behind the empty shaft and the ending answers its own question |

`--cinema=hero` writes `shots/cinema/hero_boxes.json`, which is the input to
`machines/contact_sheet.py`. Four rectangles, one machine.

### 5.1 A hero can be in the shot and not in the frame, and that needed saying in code

Shot 14 is the camera and the machine standing on the same descending cage deck, 0.9 m apart. The
camera is looking **up** a 2.4 × 2.0 m shaft at 84° of elevation; the machine beside it is at −20°.
A 21 mm covers 51.5° vertically. **No lens can hold both the daylight and the animal from inside a
two-metre box**, and the trailer asks for the daylight.

So the machine is declared, placed, lit and out of frame — which is the truth, and which
`--cinema=hero` was quietly turning into a garbage crop at (−161, 3530). It now reports
`IN THE SHOT, NOT IN THE FRAME` and leaves the shot out of the contact sheet, because a crop of an
off-screen rectangle is a comparison of nothing against the machine in every other shot.

---

## 6. The descent, and the mount frame

`CINEMA.md` §7.2 is the finding this pass had to answer:

> *"Every one of those is the rig working correctly, and every one of them is wrong about this
> shot… The rig cannot express it because **a shot's move is stated in world coordinates**, and
> TRAILER §8's rules were written for a camera on a dolly on the ground… Either (a) the shot format
> gains a **mount**… or (b) shot 14 is accepted as an exception with its own rules, written down. I
> have not implemented either."*

**(a) is implemented.** A shot may carry:

```json
"mount": { "what": "the cage",
           "from": [0.0, -0.70, 0.0], "to": [0.0, -8.70, 0.0], "ease": "accel" }
```

and then:

* **`move` and `look` are offsets in the mount's frame**, written as plain `[x, y, z]` in metres. A
  mount frame is axis-aligned with the world, because a cage hangs on a rope and does not rotate,
  and inventing a facing nobody asked for is how a format acquires a bug. The site anchor's
  vocabulary is **refused** inside a mount rather than quietly reinterpreted: there is no ground in
  a shaft to measure a `u` against and no axis to measure an `a` along.
* **Travel and speed are measured relative to the mount.** A bolted camera scores 0.00 m and
  0.00 m/s, which is the truth. The `MIN_TRAVEL` warning and TRAILER §7's no-move warning are both
  suppressed for a mounted shot, because the frame moves even though the camera does not.
* **Height is measured above the mount's own origin, which is its deck.** The four bands are
  untouched: `machine` still means 0.28–0.56 m and still means *as high off the floor as the thing
  being photographed*.
* **The mount's own speed is reported and not capped.** 1.2 m/s is how fast a person pushes a
  dolly. It is not how fast a hoist runs, and the speed of the hoist is not the camera department's
  decision. The validation record prints it: `MOUNTED on the cage: it moves 8.00 m at up to
  4.50 m/s and the camera is bolted to it`.
* **Every physical rule is unchanged and still runs in world space.** The swept body, the
  near-plane clearance and the buried test are facts about where the lens actually is, and a mount
  is not a licence to fly through a wall. Shot 14 passes all three on its merits:
  `near clear 0.40 m`, no overlap at any of 33 sampled instants, 0 of 6 axis rays buried.

### 6.1 The carrier has to actually move, and that is what makes the exemption honest

The one genuine exemption is that **the camera does not collide with the thing it is bolted to**.
That is only sound if the thing moves with it, and in this spike everything is baked into shared
MultiMeshes, so the cage did not.

`Batcher` gained a `tag`, `_cage()` sets it, and the cage's twenty-odd instances now land in bins of
their own. A `MultiMeshInstance3D` is a node, so moving the node moves every instance in it —
`CameraRig.carry()` does exactly that, once per frame, and `build_collision` leaves carrier-tagged
bins out of the bake. The cage descends; the camera descends with it; their relative position never
changes; no query between them could ever mean anything. **Two lines in `dressing.gd` and one
`continue` in the collision bake.**

Without this the shot is a camera falling through a stationary cage floor at t = 0.06, and the
right answer to that is a rejection, not an exemption.

### 6.2 Two numbers that are not round, and why

**z = −0.55, not 0.** A shaft has **buntons** — timber sets across it on the 1.2 m module that
divide it into compartments — and a cage runs in a compartment, not down the middle. On the
centreline the 0.35 m body clips every bunton it passes. At −0.55 it clears the bunton's face by
0.05 m and the shaft lining by 0.05 m. That is a 0.10 m window and it is the entire reason this
number has two decimal places. *(The cage as modelled straddles the bunton at y = +0.65 in its
parked state, which is a pre-existing inconsistency in `dressing.gd` and not something this pass
introduced. It is never in frame: the camera looks up.)*

**A new ease kind, `accel` = x², offered to mounts and not to cameras.** The first render used
`in` (x³) and it was wrong by a lot: more than half of an 8 m descent lands in the last quarter of
the shot, so three of the five seconds are a hold and the last one is a lurch. A hoist leaves the
collar under a constant pull. x² over 8 m in 5 s is 0.64 m/s² and 3.2 m/s at the cut, which is what
a small winder does. It is **not** offered to a camera move: TRAILER §8's easing rule is about a
body with mass being pushed by a person, and a person does not accelerate all the way to the cut.

### 6.3 What the mount does not yet do

* **Only translation.** A mount that rotates — a camera on a machine's back, which is what shots 17
  and 22 will want — needs the offsets expressed in a rotating basis and needs the carrier's yaw.
  The format has room for it; the code does not have it.
* **One carrier, addressed by tag, moved as a rigid body.** There is no notion of a carrier's own
  collision *against the world* — the cage passes through the bunton at y = −0.85 on its way down
  and nothing complains, because carriers are out of the bake entirely. For a cage in a shaft that
  is invisible; for a machine walking a corridor it would not be.
* **`--cinema=fail` still renders the mount's frames the old way.** It was not re-pointed at the
  mount frame because shot 14 no longer fails.

---

## 7. Measurements

**The machine was quiet for every number here and I checked.** `tasklist` at the start and at the
end of the pass: **no other Godot process**, no browser, no game client, no capture tool. What is
resident is Razer Synapse, four `msedgewebview2` helpers, the NVIDIA overlay and OneDrive — all
idle, none of them holding the GPU. This is the first measurement in this spike's history taken on
a genuinely quiet machine and it shows: `CINEMA.md` §8's timing block was taken with the GPU
throttled to 780 MHz of 2100 with 64% external utilisation, and its absolute numbers should still
not be trusted.

### 7.1 Frame rate

45-second, 14-waypoint free-flight path, 1920 × 1080, MSAA 2×, `day`, no cinematic post stack:

| | this pass | `VALLEY.md` §7 |
|---|---|---|
| **mean frame** | **15.97 ms — 62.6 fps** | 17.52 ms — 57.1 fps |
| median | 15.28 ms — 65.5 fps | 17.26 ms — 57.9 fps |
| p95 | 24.24 ms — 41.3 fps | 24.07 ms — 41.5 fps |
| p99 | 25.00 ms — 40.0 fps | 25.00 ms — 40.0 fps |
| **worst frame** | **27.64 ms — 36.2 fps** | 26.23 ms — 38.1 fps |
| draw calls max | 741 | 735 |

**The act cost the scene nothing.** The mean is 9% better and the worst 5% worse, which is inside
the ±3 ms run-to-run drift this laptop is documented three times over as having. The only geometry
change in the whole pass is the cage becoming its own two MultiMeshes: **1 474 → 1 476**, same
56 425 instances, same layout hash `701635322695612`. Ambient occlusion is still the whole of the
frame budget and this pass did not touch it.

### 7.2 Render time, per shot, at full duration

`--cinema=seq`, full post stack, 1920 × 1080, 24 fps cut rate, 72 render passes to settle the first
frame of each shot and 8 for every frame after it.

| shot | frames | seconds | s/frame |
|---|---|---|---|
| `t02_valley_first_light` | 120 | 82.0 | 0.68 |
| `t03_yard_under_the_wall` | 96 | 82.3 | 0.86 |
| `t04_melt_macro` | 96 | 80.1 | 0.83 |
| `t05_charge_line` | 96 | 74.7 | 0.78 |
| `t06_meet_the_machine` | 120 | 87.5 | 0.73 |
| `t07_course_posts` | 96 | 76.8 | 0.80 |
| `t12_course_alone` | 96 | 88.1 | 0.92 |
| `t13_collar_above` | 96 | 78.3 | 0.82 |
| `t14_descending` | 120 | 89.6 | 0.75 |
| `t28_extraction_window` | 72 | 68.3 | 0.95 |
| **total** | **1 008** | **807.7** | **0.80** |

**13 min 43 s of wall clock** for the ten-shot pass, including the 40 s scene build and the
601 ms collision bake. The measured budget was 0.6 s a frame; the truth is 0.80, a third over,
and the difference is the PNG encode rather than the render — `t28` at 0.95 s/frame is the
*cheapest* frame in the set to draw and the most expensive to write, because a dusk frame with
falling grain compresses badly.

`t14_descending` was rendered twice: 91.8 s on the `in` ease, discarded (§6.2), and 89.6 s on
`accel`, shipped. The act's total above uses the shipped one.

### 7.3 `--cinema=look`, and it paid for itself four times over

Three frames a shot — t = 0.06, 0.50, 0.94 — full stack, rejected shots included and labelled.
**2.4–3.5 s a shot, about 40 s for all ten including the scene build.** A full sequence pass is
13 minutes and answers the same framing question.

`CINEMA.md` §7.5's workflow was *places → scout → probe → **a person looks at the frame***, and the
last step was the one with no cheap tool behind it. This pass ran five look passes and one sequence
pass; on the old tooling it would have been six sequence passes and eighty minutes of GPU. It also
renders **rejected** shots deliberately, because a rejection is usually a framing problem wearing a
rule's costume — shot 6's first two sitings were both.

---

## 8. What is weak, and three things this pass found

### 8.1 The braid plain is buried, and `THE-ICE.md` §8.2's shot cannot be taken

`THE-ICE.md` §8.2 turns shot 4 into *"meltwater running off ice, macro"* and calls it a beat working
better than it did, because it makes the first and last images of the trailer both water and makes
the first one water **coming out of ice**. `valley.gd` builds exactly that object: a braided
meltwater plain 58 m wide at z = −150, cut 2.6–4.0 m into the floor, with a three-state material of
washed gravel, shore ice and dark threads.

**It is invisible.** The pit-head's own ground mesh is a single `ArrayMesh` spanning the site box
plus a skirt to **420 m in every direction**, it is drawn on top of the valley mesh by
construction (`Valley.SINK` = 0.25 m), and it knows nothing about the landform. So from the collar
out to 420 m the valley's floor detail — the braid plain, the near lateral moraine's trough, the
roches moutonnées — is under a flat lid. The only reason the moraine *crest* is visible in `v01` is
that it is 26 m high and pokes through.

That is not a shot-list problem, it is a seam: **two graded surfaces, one drawn over the other,
with no agreement about which owns the ground between 80 m and 420 m.** It is worth a paragraph in
`VALLEY.md` §8 and it is the reason shot 4 is what it is.

### 8.2 Drifts read as ghosts on open ground

`scatter.gd::_drift` instances a `rock` mesh with the `snow` material, and the snow material is
shaded from **world position**. So a drift's own crust, sastrugi and wind grain line up exactly
with the ground's underneath it, and on open snow — where there is no silhouette against anything —
the result reads as a **translucent faceted sheet lying on the ground** rather than as a bank of
snow. It is clearly visible in the first siting of shot 6 and in the lower middle of shot 12, and
it is in `v14_course_snow` too, so it predates this pass.

Banked against a fence or a container it reads correctly, which is exactly `VALLEY.md` §4.3's claim
and also exactly why it was not caught: every frame that pass judged drifts on had something for
them to bank against. **The fix is a per-instance offset into the noise field, not a new mesh.**

### 8.3 Shot 13 is the frame I would re-scout next

It executes, it is the pit-head's own praised crane geometry mirrored to the better side, the
machine is unmistakably the hero and its lamp is on. It is also **dark, and the machine is 119 px
in a frame whose middle third is black ironwork**, and at 4.6 m looking down at 27° nothing above
the horizon is in it — which in this world is half the picture. I could not find a position that
holds the collar, the machine and the far wall at once with any lens in the committed bands: the
collar needs a steep look-down and the town needs a shallow one, and 4.6 m of crane is not enough
lever arm to separate them. It wants either a 6–8 m crane off the headframe (legal — the band goes
to 30 m and the headframe is 12 m) or acceptance that shot 13 is an iron shot and shot 28 is the
one that carries home.

### 8.4 Unchanged and still true

* **Specular aliasing on the ironwork.** `CINEMA.md` §9's first item, unfixed, and shots 3, 13, 14
  and 28 are all lattice-against-sky. At MSAA 2× the 1–2 px members crawl.
* **Nothing moves** except shot 4's falling snow. Ten camera moves over a still yard.
* **The snow does not record what walked on it.** `THE-ICE.md` §7.1 calls this *"the single most
  valuable object the ice decision produces, and it is not an art win, it is a teaching win"* — a
  course whose floor draws the policy. Shot 7 is a machine walking a course in snow and **the snow
  behind it is untouched.** It is the only place in this act where the frame actively contradicts
  the design, and it is `VALLEY.md` §8.6's own top item.
* **One seed.** Everything here is seed 20260908.

---

## 9. Every guess in this pass, in one list

Things this pass decided that neither the designer, `TRAILER.md`, `THE-ICE.md` nor
`machines/NOTES.md` decided. Strike them individually.

1. **That shot 2 is `firstlight` and shots 3–7, 12–14 are `day`**, which is a continuity jump inside
   one act. `THE-ICE.md` §8.3's warm → white → black asks for it and does not say where the seam is.
2. **That shot 28 is `dusk` rather than `snowfall`**, trading the falling snow and `THE-ICE.md`
   §8.5's "melt running into the collar" for a town that reads as occupied. §3.1.
3. **That shot 4 keeps `snowfall`** for its particles rather than taking `day` for its contrast. §3.1.
4. **Every camera position, aim, focal length, T-stop, focus pull and handheld amplitude in the ten
   shots.** `TRAILER.md` §3 gives a sentence and a length; `THE-ICE.md` §8 gives an intent for four
   of them; the rest is mine. In particular: 170 m up-valley for shot 2, ten metres back down the
   row's axis for shot 5, z = −8 on the open snowfield for shot 6, the corridor axis for shot 12,
   and due east down the headframe's own axis for shot 28.
5. **Shot 28 at 18 mm.** It is inside TRAILER §8's wide band and it is 3 mm wider than everything
   else in the act, chosen because it is `v10`/`v08`'s own angle of view and because at 21 mm the
   near headframe leg splits the frame.
6. **The mount frame's whole design**: that a mount is axis-aligned and does not rotate; that its
   anchors are plain `[x, y, z]`; that travel and speed are measured in its frame; that height is
   measured above its origin; that its own speed is reported and not capped; and that a carrier is
   exempt from the camera's collision. §6.
7. **`accel` = x² as an ease kind, and that it is for mounts only.** §6.2.
8. **8.00 m in 5.0 s for the cage** — 0.64 m/s², 3.2 m/s at the cut. `TRAILER.md` §3 says
   "descending" and nothing else.
9. **z = −0.55 in the shaft.** Derived from the bunton and lining geometry, but the 0.05 m
   clearance either side is a judgement about how tight is tight enough. §6.2.
10. **That the hero rides the cage in shot 14 and is out of frame.** The alternative reading is that
    the camera goes down first and the machine follows, which would let shot 14 say `role: "none"`
    and would be a different beat. I took the one that keeps `TRAILER.md` §11.1's *one machine* rule
    literal.
11. **Shot 6's head aim ending at +43°**, measured off a crop rather than computed, because the
    `idle` clip's own head scan is an unknown offset at 4.7 s. §4.
12. **Shot 6's node yaw of 134.1°**, which puts the camera 35° off the machine's nose. `NOTES.md`
    §15 asks for a head turn "about 30° away" at the start and does not fix the body's angle.
13. **That shot 12's machine walks *away* from the camera** rather than across it. "Alone" reads
    better going away; nothing says so.
14. **The carrier tag as a mechanism** — that a named group of instances gets its own MultiMesh, that
    the name is a string on the `Batcher`, and that the only user is the cage.
15. **That `--cinema=look` should exist**, and its three sample times (0.06, 0.50, 0.94).
16. **That an off-frame hero is reported and skipped rather than written into `hero_boxes.json`.** §5.1.

---

## 10. What I would do next, in order

1. **Give the ground mesh and the valley mesh one agreement about the floor**, so the braid plain,
   the moraine trough and the roches moutonnées exist inside 420 m. §8.1. It unblocks
   `THE-ICE.md` §8.2's shot 4 and it is the difference between a valley you stand on and a valley
   you stand in front of.
2. **Accumulate the machine's actual path in the snow.** §8.4. It is a teaching win before it is an
   art win and shot 7 currently argues against the design.
3. **Offset each drift's noise phase.** §8.2. One `hash(instance)` into the world-position lookup.
4. **Re-scout shot 13 at a 7 m crane**, or rule that it is an iron shot. §8.3.
5. **Raise MSAA or add a specular anti-aliasing term.** Four of the ten shots are lattice against
   bright sky.
6. **Extend the mount to rotation**, which is what shots 17 and 22 need the day the camera follows a
   walking machine. §6.3.
