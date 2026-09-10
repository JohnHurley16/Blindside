# THE MAP — the trailer's ending, and the lidar cuts that lead to it

2026-09-10. `spikes/godot/cloud/`, Godot 4.7.2, Forward+, Vulkan, RTX 3080 Laptop.
Spec: the designer, this morning, describing the whole new trailer.

> *"it wonders through the cave and than starts to uncover stuff and thats where it fades to
> black. work in the lidar views where it gets dark in the cave"*
>
> *"show a 3d map of the cave system somehow after the dog explored it"*

There are no text cards in the new trailer — the old ones read as a horror game — so the last
image has to carry the idea unaided. A machine wanders somewhere alone in the dark. It fades to
black. What comes up is **what it knew**: the cave rebuilt out of nothing but its own sensor
returns, turning in space.

```
<godot> --path spikes/godot/cloud --resolution 1920x1080 -- --map=probe
                                                            --map=stills
                                                            --map=reveal
                                                            --map=moments
                                                            --map=depth
                                                            --map=all
                                       --depth=gauge|beams|blind   the vertical belief, §6
                                       --voxel=0.07     metres; 0 keeps every return
                                       --levels=1..4    1 is the flat cave, and it is asserted
                                       --fixevery=40    metres of route between corrections
                                       --fast           half the revolutions, for iterating
                                       --mapshot=NAME   just one
                                       --mapframes=N    force a frame count
```

Everything is procedural and nothing is imported. Nothing outside `spikes/godot/cloud/` was
modified and nothing was committed.

---

## 0. The short version

| | |
|---|---|
| **Does the map read as architecture?** | **Yes, and it reads immediately.** Four levels as four ribbons stacked over the same plan, three shafts hanging between them as ribbed vertical tubes, and chambers as bulges in the ribbons. The machine's own trail is in there and is mostly *behind* the near wall — §3.5 and §8.3. `shots/map/01_the_map.png` and `02_section.png`. What makes it read is not the renderer: it is a **voxel downsample at source**, **height in the colour channel**, and a **section crop in Z instead of Y**. §3. |
| **How long should the reveal be?** | **Thirteen seconds, and it is a PULL-BACK rather than a push.** The first cut of it pushed in, which is a shot that explains itself in its first frame and then has twelve seconds to fill. It now opens where the audience has just been — at the foot of the deepest shaft, at the scale the lidar cuts are at — and goes away until the passage is a level, the levels are four, and the four are a cave. §4. |
| **Which lidar moments?** | Four, chosen by CONTENT rather than by clock: **the ice** (the map going thin), **the passage resolving**, **the lip of a pitch**, and **the workings being uncovered**. Each is a place on the route found by asking the topology a question, so none of them moves when the route does. They are 3.5 / 4.0 / 4.5 / 4.0 s and in that order they are also the journey: shallow ice, bedrock, a drop, the mine. §5. |
| **Is depth blindness visible?** | **In the map, unarguably. From inside the cave, only in motion.** A machine at the lip of a shaft cannot photograph the thing it is about to fall down — an absence 1.8 m across has no edge to sit against — but it can photograph **its own floor ending**, and over a second that reads. §6.2. The unanswerable version is a pair of stills on the same camera: the map before it committed and the map after. §6.3. |
| **The thing that should go in front of the designer** | **The depth gauge.** `lidar_root.gd` gives every chassis an instrument that reports its height to about half a metre, and `spikes/godot/cave/VERTICAL.md` §9.3 searched this project for an altimeter, a barometer, an inclinometer or a wheel encoder and found **zero**. With it, the map's vertical extent is right. Without it the map is a **pancake**: four levels superimposed at one elevation. It is one number and it decides whether the vertical axis is a mechanic or scenery. §6. |
| **The machine's own believed pose** | **Drawn, for the first time.** `CINEMA.md` §12.4 put it in front of the designer as an art proposal and did not build it. The map needs it — a cave with no route through it is a scatter of rooms — so it is built here and it obeys the register's rules. §3.5. |
| **Point counts / draw calls** | The accumulated map is **one draw call** at every count in this document. §7. |

---

## 1. The material changed overnight, twice

Two things happened between `CINEMA.md` being written and this pass starting, and both of them
change what a map IS.

**The cave gained a vertical axis.** `spikes/godot/cave/VERTICAL.md`: four levels over 83 m, nine
pitches including a moulin, levels running in opposite directions so one lies under another, and
a rule that down is cheap and up is not. A flat cave's map is a plan and a plan is a diagram. A
vertical cave's map is a **section**, and a section of a place with four floors in it is a
picture of a place rather than a picture of a corridor.

**The cave is becoming glacial ice rather than coal.** `docs/THE-ICE.md` §6.2 is the only
material-specific sensor ruling this project has beyond water, and it is not a reflectance, it is
an *angular response*: near-infrared is strongly absorbed by ice, so a clean ice wall gives
sparse, low-intensity, dropout-ridden returns — not a mirror and not a hole — and *"wet ice at
grazing incidence returns nothing and at normal incidence it flashes, so a machine walking a
polished conduit sees a bright patch straight ahead and almost nothing at the walls: the returns
collapse into a narrow forward cone."*

### 1.1 How the vertical cave was brought in without breaking the cut

`CINEMA.md` §12.5 ends on a warning: `topology.gd` here was a byte copy of the cave spike's, that
copy is what every frame in `shots/cinema/` was shot against, and the cave's working tree had
moved. **The vertical work is behind a flag and the flag defaults to off**, so the copy is now
safe to take: `generate(seed, length)` still defaults to one level, the flat path is frozen
verbatim, and `content_hash()` on it still hashes only the sixteen station fields the old row had.

So `topology.gd` here is a fresh byte copy of the cave's current file, and **every run asserts the
old hash**:

```
topology     : v2, 4 levels, 9 pitches, 72.3 m of vertical range
v1 regression: PASS  (flat path, seed 7 len 240 -> 0xAD83E3ED, recorded 0xAD83E3ED)
```

That costs 6 ms and it means the belief cut in `shots/cinema/seq/` is still the same passage it
was shot in. Nothing in `cinema.gd`, `cinema_run.gd` or `shots_cinema.json` was touched, and
`--cinema=*` still runs against `--levels=1`.

### 1.2 What had to be built to scan a vertical cave

`lidar_geo.gd` gains a **second profile family**, which is what THE-ICE §5.3 asked for in so many
words: *"`_half_profile()` builds a floor, two legs and a crown, which a vertical shaft is not. A
moulin needs a second profile family beside the sweep, not a modification of it."* So a pitch is a
genuinely different builder — a closed ring in the horizontal plane swept along an axis that is
allowed to corkscrew, with the perimeter coordinate an *angle* rather than an arc length up from a
floor — and each kind is a different radius function rather than a different parameter: helical
flutes on a moulin, a superellipse of order 8 on a timbered winze, a slot on a crevasse, a bell on
an aven, broken ground on a collapse.

**The holes are punched as a post-pass**, and that is worth stating because it is thirty lines
against three special cases. Every triangle whose centroid lies inside a bore between the pitch
floor and a little above its lip is deleted, *before* the tube is built. That is the floor of the
passage at the head and the ceiling of the passage at the foot, in one operation, without the
sweep, the chamber dome or the chamber floor fan knowing that pitches exist. At seed 7 over 240
cells it removes **6,134 triangles for nine bores**.

**And a laser must be able to get down them.** The rubble cone at the bottom of a bore, the
ancients' rings every 1.2 m where they left steel, and a **retroreflective beacon at the head and
the foot of every pitch a machine can descend plus a chain every 3.2 m down the main ones**, which
is `VERTICAL.md` §3.4's own content list. The beacons are the cheapest thing in this document and
the most valuable: a retroreflector clips the intensity channel and blazes from anywhere in range
at any incidence, so **the descent chain draws itself in the brightest marks the machine has**,
with no overlay and no art direction, and it is physically true.

### 1.3 Ice, as a sixth surface class

`SURF_ICE`, albedo 0.075, and then an angular response that is the whole of the ruling:

```gdscript
var cone:  float = pow(max(cos_i, 0.0), 2.6)          # near-IR is absorbed; grazing returns ~nothing
var flash: float = 0.62 * pow(max(cos_i, 0.0), 26.0)  # and at normal incidence it flashes
refl = alb * cone + flash * alb * 7.0
```

Both exponents are GUESSES. What they produce is measurable: against rock at the same range and
the same incidence the detection probability is roughly **twelve times lower** at eight metres, so
an ice passage arrives as a sparse dust with a bright patch straight ahead and no walls.
`shots/map/m1_into_the_dark.png` is that.

**And it gives the register a free inversion that is worth having.** THE-ICE §6.1 says the ice
band is the one place in the cave where the darkness relents — it is the *brightest* place in the
world register. In the machine's own view it is the **emptiest**. The same band, photographed two
ways, says two opposite things, and neither of them was authored.

---

## 2. The exploration

A map is the residue of a journey, so there is a journey. The route is the one the topology
already decided: along each level's main drive to the station the descent leaves from, down the
pitch, and on — which is THE-ICE §5.2's *"the player goes down the way the water went down, and
the water went down the way the ancients went down"*, walked.

| | |
|---|---|
| the cave | seed 7, 240 cells, **4 levels, 9 pitches**, topology hash `0xF1A66B36`; 1,061 stations, 485,566 triangles, 29 chambers |
| route | **503 m**, four levels, three drops |
| revolutions | **297**, one every 1.7 m of route |
| shots / returns | **9,732,096** fired, **8,193,906** came back (84%; 3.9% of the misses are detection dropouts rather than sky) |
| the map | **2,395,022 points** after a 70 mm voxel — 29% of the raw cloud |
| its extent | **155.5 × 77.6 × 27.6 m** against a cave whose true vertical range is 72.3 m |
| walk / descent speed | 1.45 / 0.85 m/s, GUESS |
| duration | **6.4 minutes** |
| the drops | moulin 14.7 m (bore 2.20), winze 22.7 m (1.60), winze 33.6 m (1.84) |
| corrections | **15 honest fixes**: every 40 m of route, and at every pitch mouth |

**The fixes are not a convenience and the number is doing real work.** phase1's dead-reckoning
model is 0.11° of heading bias per cell, and 503 m is 838 cells: with no corrections at all the
last passage is **ninety degrees** off the first and the map is a spiral rather than a cave. The
fiction already has the mechanism — *"dead reckoning plus fixes on beacons the machine dropped
itself"* — and the beacons are already in the geometry, so a correction lands at every pitch mouth
and otherwise every 40 m. **What is left over is the point:** between two fixes the machine still
drifts, and the corrections it then makes are real — the fifteen of them land as jumps of up to
**3.08 m** and heading changes of up to **7.98°**, printed with the bake. The map is bent by that
much at every seam. A map with no error in it would be a photograph.

---

## 3. Making a point cloud read as architecture

`LIDAR.md` §3 already found the hard case: *"an accumulated cloud of a tube cannot be read from
outside — it is a solid mass"*, and the answer there was a crop box in world Y that takes the
ceiling off. **A cave with four floors in it cannot be cropped in Y at all without deleting the
subject.** Four things replace it, in the order they matter.

### 3.1 The voxel downsample, and it is the biggest single lever

`LIDAR.md` §6 already says this has to happen and calls it a Phase 3 belief-map decision rather
than an art one: at 10 Hz the device makes ~230,000 returns a second and a whole match is ~110
million, so **the live sweep and the accumulated map cannot be the same object and the map has to
be reduced where it is made.** This is that decision, taken here for the first time, and the
reason it is in this section is that it is *also* what makes the map legible:

> A raw accumulation has a density gradient nobody wants: it is a solid fabric within three metres
> of wherever the machine stood and a scatter at twenty. Voxel it at 70 mm and the density becomes
> **uniform**, which is what lets the thing read as a surface at a hundred and eighty metres.

And the ring structure survives where it was legible in the first place. Ring pitch is
range × tan(1.355°): **236 mm at ten metres**, 71 mm at three. So a 70 mm voxel is far below the
ring pitch at working range and *at* it in the near field — it removes exactly the near-field
fabric that `CINEMA.md` §7 had to fix by halving the sweep rate, and touches nothing at six to
twenty metres where §8.2 says the rings have to be countable.

### 3.2 Height in the colour channel, and only height

`ART-DIRECTION` §8.2: *colour carries exactly one channel at a time*. For a map of a vertical cave
that channel is **height**, and it is not a close call — `06_intensity.png` is the same camera on
the intensity ramp and it is one flat pale cyan mass with retro flecks in it. Height puts the four
levels into four colours and the reading is instant.

Two details:

* **The ramp gets 18% of headroom below the cloud.** Its dark end is a near-black navy, so putting
  the deepest level exactly on it hides the deepest level — the one there is no way back up from.
* **Intensity is not lost**; it moved into *density*. The ice band is thin because the ice returns
  weakly, and that reads as clearly in a height-coloured map as a colour would.

### 3.3 The section, in Z

`ART-DIRECTION` §8.2's crop box, in the axis a vertical cave needs it in: a slab normal to Z, so
the levels and the pitches between them are in one cut. `lidar_point.gdshader` gains world X and Z
bounds and an **oriented slab** (`u_cut_n`, `u_cut_d0/d1`) beside the existing Y pair. It only ever
*removes* points, so it puts nothing into a sensor shadow and the §5 verdict in `CINEMA.md` is
untouched by it.

### 3.4 Scale, and why a solid shell is not a failure

The wide view of an accumulated cloud is opaque, because a tube seen from outside is a wall. That
is not a problem to solve: **a cave system seen from outside is a cast of itself**, which is a real
and beautiful object and exactly how a cave survey is drawn. What the reveal does is *use* it —
open on a passage, where the marks are individual measurements, and pull back until the object is
solid and sculptural. Both readings are true and the move is what puts them in one shot.

### 3.5 The machine's own believed pose, drawn

`CINEMA.md` §12.4 closes by putting this in front of the designer and not building it:

> *"the belief view should contain the machine's own believed pose as a mark: a scanner's map does
> hold 'and I think I am here', and that mark drifting off the truth is the game's whole subject.
> That is an art proposal and it is not built."*

The map is the shot that needs it, because a cave with no route through it is a scatter of rooms.
It is built here and it obeys the register: it is **belief** (the estimated pose, moved by whichever
correction has landed, never re-registered), it is a **single flat colour** so it carries no channel
of its own, and it is drawn as a constant-apparent-width ribbon rather than a GL line only because
a one-pixel line disappears at a hundred and eighty metres. It is **depth-tested like everything
else**, which means it is *hidden inside the passages and visible in the shafts and wherever the
section has taken the near wall off* — and that is correct rather than a limitation.

### 3.6 What is NOT done to make it read

No smoothing, no meshing, no interpolation, no fill, no decal, no depth cueing (ART §8.1: belief is
*falloff-free* emission), no additive blending, and **nothing is ever drawn into a sensor shadow**.
The holes in this map are holes. The only post effect is the vignette, which is the one of nine
`CINEMA.md` §5 found is multiplicative and ≤ 1.

---

## 4. THE REVEAL — the last shot of the trailer

**Thirteen seconds, 312 frames at 24 fps, one move, no cuts.** `shots/cinema/seq/map_reveal/`,
and `shots/map/_strip_map_reveal.png` is six of them on one sheet.

### 4.1 It is a pull-back, and that is the one structural decision in the file

The first version pushed *in*: it started on the whole system and ended on a passage. That is a
shot which explains itself in its first frame and then has twelve seconds to fill, and looking at
it, that is exactly what it did.

A reveal has to reveal. So it opens **where the audience has just been** — inside a passage, at the
scale the lidar cuts are at, close enough that the marks are individual measurements — and then
it goes away. Specifically it opens at
the **foot of the deepest winze**: the last place the exploration reached, on the level there is no
route back up from.

| | |
|---|---|
| 0.0 – 3.0 s | one passage, sectioned to 16 m, with the ribbed tube of the winze coming down into it. The register the cut arrives in, so nothing has to be established |
| 3.0 – 9.0 s | the pull-back. The section opens as the camera leaves, which is what lets the whole system arrive with nothing cropped out of it |
| 9.0 – 13.0 s | the object, whole, still turning, still going away. Fade |

Camera: **44 m to 187 m**, azimuth **58° to 124°** *through* broadside — the workings run along X,
so 90° is broadside and 0° is end on, where a hundred and twenty metres of cave collapse into
forty. Elevation 4° to 17°. Lens 40 mm to 34 mm.

**The move is eased at both ends and constant in the middle.** A smootherstep across thirteen
seconds is nearly still at both ends and hurries through the middle, which is the opposite of what
a slow turn wants; the profile is a trapezoid velocity with 22% ramps, integrated.

### 4.2 Why thirteen seconds and not four

`CINEMA.md` §12.2 measured what a four-second shot buys and the answer generalises: what four
seconds bought the fix was **the 2.25 seconds of established doubling in front of the correction**,
not the correction. The same arithmetic here: the *information* in this shot arrives in the last
four seconds, and everything before it exists to make that arrival mean something. Nine seconds of
travel is what turns "here is a diagram" into "that is where it was."

Thirteen is also the number that lets the move be slow. At 13 s the turn is 5.7°/s and the camera
recedes at 16 m/s of a 187 m throw; at 8 s both are fast enough to read as a camera move rather
than as an object turning, which is the wrong reading.

**If it has to be cut down, cut the head, not the tail.** The last four seconds are the shot.

---

## 5. THE LIDAR MOMENTS — inside the cave, where it gets dark

The designer asked for the belief view worked in *"where it gets dark"*, which is not one hard cut.
These are four instants along **one continuous journey** at which the picture becomes what the
machine sees. Each is a camera in the drive at about the machine's own height, scrubbed to the
moment it belongs to, and each is a different thing the sensor does.

| | length | what it is |
|---|---|---|
| `m1_into_the_dark` | 3.5 s | **the ice.** A polished meltwater conduit returns almost nothing at the walls and flashes where the beam meets it square. The passage is a tunnel of scattered light with no sides. §1.3 |
| `m2_passage_resolves` | 4.0 s | **the map being written.** Bedrock, so the returns come back. The camera moves 1.1 m and eleven metres of walk lands during the take: the passage ahead builds ring by ring and the far end stays black because nothing has been there |
| `m3_the_pitch` | 4.5 s | **the lip.** The floor stops. §6.2 |
| `m4_uncovered` | 4.0 s | **something is uncovered.** The workings: rail as two bright dotted lines down the floor, timber sets as a regular row of shadow slots, a beacon clipping the channel |

### 5.1 Two things were got wrong first, and both are worth recording

**The camera has to be ON THE ROUTE.** The first version put it `back` metres behind the machine
along its instantaneous heading and aimed it `ahead` metres along the same straight line. In a
drive that bends — which is every drive — that lands the camera inside the wall behind and the aim
inside the wall in front, and what it photographs is a flat rectangle of returns two metres away.
Both ends are now resolved **along the route**: a place the machine has already stood is guaranteed
to be inside the passage, and a place it is about to stand is guaranteed to be where the passage
goes. It also means that at a pitch the aim follows the route straight down the hole with nothing
to author.

**Every aim point has to be in BELIEF space, and getting this wrong cost an hour of frames that
looked like static.** `geo.pitch_m` holds where a shaft *is*. The cloud holds where the machine
*thought* it was when it measured it, and after two hundred metres of route those differ by metres.
A camera standing in the machine's map and aimed at a true-world coordinate is aimed into the rock
beside the thing it wants. The rule for this file is now the same rule `CLAUDE.md` states for the
sim: **nothing downstream of the sensor gets a world coordinate.** A place is named by where on the
route it is, and resolved through the belief.

### 5.2 The moments are found, not timed

A fraction of a six-minute walk is not a place, and it stops being one the moment anything about
the route changes. So each moment names the **content** it is about and the rig finds it: the first
clean-ice stretch past the collar that is wide enough to walk; the first bedrock station on a lower
level; the deepest winze; the first worked station carrying both rail and sets. `moments.txt`
prints the route distance each one resolved to.

**One of those choices is a finding rather than a convenience.** The pitch shot uses the *deepest*
winze, not the first, because `topology.gd` puts ice-over-rock *"in the karst, near a pitch"* — so
the floor at the first winze's lip is ice, an ice floor at grazing incidence returns almost nothing,
and the frame is a sparse dust with no floor in it and no lip. That is a true picture of that place
and a useless picture of a pitch. The deepest winze is below the melt front in the workings: rock,
timber, rail, dense returns on every side of a hole.

### 5.3 The local bake, and the split it forces

These shots cannot come from the map's cloud, and the reason is a real Phase 3 decision rather than
a rendering detail. The whole-route bake samples **one revolution every 1.7 m** because 503 m at
full rate is thirty-eight million returns. A 10 Hz head walking at 1.45 m/s lays a revolution every
**145 mm**. So a shot inside the cave gets its own bake over its own stretch of route at **one
revolution every 0.65 m** — forty times the map's density, and a quarter of the device's real rate.

0.65 rather than 0.30 for the reason `CINEMA.md` §7 already found and had to fix once: at full
local density everything within eleven metres is at the point-size cap and the frame is a solid
fabric with no countable rings and no legible shadows in it.

**Belief is integrated over the whole route either way.** The drift at a place is the drift the
walk earned getting there; only the sweeping is windowed. Same sensor, same route, same drift,
different sampling — which is exactly the live-sweep / accumulated-map split `LIDAR.md` §6 says
Phase 3 has to make anyway, arriving as a bake parameter.

### 5.4 The one exposure in the file, and why it exists

`m3` carries `gain: 1.5` and `m4` carries `2.3`, and they are the first hand-set gains in this
spike, against `LIDAR.md` §3's claim that the view is self-exposing and no frame has one. The
physics:

> A worked drive has a **flat** floor. A flat floor seen from a 0.90 m head at five metres is 80°
> off its own normal; `cos^0.75` of that is 0.27, so a 0.30-albedo rock floor returns **eight per
> cent** and lands on the dark end of the intensity ramp. The karst above it is rounded and rough,
> so its floor faces the beam in patches and reads two stops brighter.

That difference is real and worth keeping — *deeper looks different in the belief register too* —
but a frame in the workings needs exposing for what is in it. It is recorded rather than hidden and
a designer may well prefer the darker version.

---

## 6. DEPTH BLINDNESS

`VERTICAL.md` §9 is the sharpest thing anyone has written about this cave:

> *"A machine's depth error grows with distance walked, and a fall contributes no odometry at all.
> Falling is the only way down. So the vertical axis is the one dimension in which a machine's
> uncertainty jumps discontinuously — and it jumps at exactly the moment it commits."*

### 6.1 The envelope, and it is not a guess

The device is 32 rings over −30.0° … +12.0°. From the lip of a bore of radius *r* the steepest ring
strikes the **opposite wall** at r/tan30° and nothing below that is in the beam pattern at any
depth, for ever.

| pitch | bore | how far down the beams reach from the lip | the drop |
|---|---:|---:|---:|
| moulin | 2.20 m | **1.91 m** | 14.7 m |
| winze | 1.60 m | **1.39 m** | 22.7 m |
| winze | 1.84 m | **1.60 m** | 33.6 m |

**Everything a machine knows about the thirty-three metres under its feet is 1.6 m of tube.**

### 6.2 From inside the cave it reads only in motion, and that is the finding

`m3_the_pitch` is the moment that took the most work and the shape of the difficulty is the
finding. Depth blindness is an **absence**, and an absence is not an image on its own. Four
framings were tried before one read: 35 mm at five metres, 24 mm at ten, 21 mm at eight, and
finally 21 mm at three, aimed into the hole. The first three photograph a dust field with nothing
in it, because at those ranges and lenses the individual rings resolve and a 1.8 m void has no
edge to sit against.

**And it reads in motion where it does not read as a still.** `_strip_m3_the_pitch.png` is the
proof: the first frames are a floor, and over the last second a black hole opens in it with a
bright rim of returns round its lip and the retroreflective beacon blazing on the edge. What
carries it is not the hole, it is **the floor stopping**, and a stop is a thing that happens rather
than a thing that is. That is `CINEMA.md` §4's finding — *motion is the strongest carrier* —
arriving for a third time in a third register, and it is the reason this shot is 4.5 s rather than
the 3.5 s of the ice.

> **A machine at the lip of a shaft cannot photograph the thing it is about to fall down, because
> there is nothing there to photograph. It can only photograph its own floor ending.**

### 6.3 The pair that does read, and it needs no caption

`08_before_the_drop.png` and `09_after_the_drop.png` are the same camera on the same map with one
difference: the first is scrubbed to the instant the machine arrived at the lip of the first pitch,
the second to the end of the walk.

* **Before**: the drive ends. Below it there is a stub of bore and then nothing at all.
* **After**: the shaft is in the map — and it is in the map for one reason. **The machine went down
  it. A pitch is mapped by being fallen down.**

That is `VERTICAL.md` §9's sentence as a picture, and the picture needed nothing invented: it is
one uniform scrubbed to two values.

### 6.4 The three vertical belief models, and the number that should be ruled on

`--map=depth` renders the same exploration and the same camera three times.

| model | what it assumes | where it comes from |
|---|---|---|
| **`gauge`** (default) | a depth gauge on every chassis: true height plus a 0.42 m fixed bias and 0.08 m of per-reading noise | `lidar_root.gd`'s own constant, added to this spike on 2026-09-10 |
| **`beams`** | the machine estimates a drop from what its own beams reached: r/tan30° down from the lip and r/tan12° up from the foot | the envelope in §6.1. **Not a guess** |
| **`blind`** | a fall contributes nothing at all | `VERTICAL.md` §9.5 item 1, taken literally |

**Measured, one camera, one exploration, three beliefs:**

| model | the map's vertical extent | against a cave whose floors span 72.3 m | what the frame looks like |
|---|---:|---:|---|
| `gauge` | **77.6 m** | +5.3 m, and most of that is crowns and pit bottoms rather than error | four levels, three shafts, a survey |
| `beams` | **31.3 m** | **−41.1 m** | four levels still legible and **crushed into a stack a fifth as deep**, passages nearly touching |
| `blind` | **24.4 m** | **−47.9 m** | **a pancake.** On the same camera the entire cave has moved up into a single ribbon with a few stubs hanging under it. It is not wrong in a way a viewer could catch; it is a plausible flat cave |

The frames are `shots/map/07_depth_{gauge,beams,blind}.png`, and they share a camera so the
comparison is of the maps and not of three framings.

**And the third row is the one that should worry somebody.** `blind` does not look like an error.
It looks like a cave — a shallow one, with rather a lot of corridors in it, because four levels are
lying on top of each other. **A machine that does not know it went down draws a map nobody can tell
is wrong**, which is a much sharper problem than a map that is obviously broken.

**And the finding is about the first row rather than the other two.** `VERTICAL.md` §9.3 ran an
exhaustive search of this project and of `THE-SENSOR-AND-SLAM.md` for
`altimeter | barometer | IMU | inertial | gravity | accelerometer | gyro | inclinometer |
magnetometer | compass | pressure | wheel encoder` and found **zero hits**. The depth gauge is an
instrument no design document has agreed to exist, it has a fixed bias of 0.42 m over a range of
83 m, and **it is the only reason the map's vertical extent is right.**

> **The vertical cave makes the gauge visible. One number decides whether depth is a mechanic or
> scenery, and nobody has ruled on it.** With the gauge, the map is a survey. Without it, the map
> is a pancake: four correct level-maps stacked at the wrong spacing, or at no spacing at all.

I have not deleted it, because deleting it changes the shot the designer is being shown, and
because §6.5 says what should happen instead.

### 6.5 What I would recommend

**Make the blind cone the mechanic**, which is THE-ICE §6.2's third option and `VERTICAL.md` §9.5's
recommendation, and I agree with both. But add the one thing neither of them has, because the map
is what makes it obvious:

> **Publish the no-return.** The scan discards a miss — `if r.is_empty(): continue` — so free space
> and unmeasured space are indistinguishable in the data the belief layer receives. A machine that
> fires four thousand beams into a hole and gets nothing back has, in its belief, **exactly the same
> record as a machine that never fired at all.** That is the difference between a machine that is
> blind and a machine that knows it is blind, and only the second one is a game. It also happens to
> be the difference between a map with a hole in it and a map with a *question* in it, which is a
> better last image than the one this pass produced.

---

## 7. Measurements

**Safe at any time, and these are the numbers to quote:**

* **One draw call for the accumulated cloud at every point count in this document.** The trail is a
  second.
* The topology assertions: 1,061 stations, 29 chambers, hash `0xF1A66B36` at four levels, and the
  flat path still `0xAD83E3ED`.
* 9 pitches; the punch removes 6,134 triangles.
* The envelope arithmetic in §6.1, which is geometry and does not depend on a clock.
* The point counts and route distances in `shots/map/probe.txt`: **8,193,906 returns from
  9,732,096 shots in 297 revolutions**, reduced to **2,395,022 points** at a 70 mm voxel.
* The bake is not a frame cost. The whole-route sweep is GDScript raycasting against 485,566
  triangles and `LIDAR.md` §8 already records that this is the sim's job in Phase 3.

**Not measured, and deliberately.** No frame times and no GPU numbers are quoted anywhere in this
document. `tasklist` found **another agent's Godot process on this adapter during part of this
session**, and at one point two of my own — `CINEMA.md` §8 records exactly that mistake producing
negative leave-one-out deltas that looked like results. Nothing here needs a frame time. Re-measure
on a quiet machine before quoting a ceiling.

### 7.1 What is in `shots/`

| where | what |
|---|---|
| `shots/map/01..06` | the map read from six directions: three quarters, section, plan, end on, the descent chain close, and the same camera on the intensity ramp instead of height. **`04_end_on` is the surprise of the set** — sighted down the length of the workings the whole system stacks into one vertical object with the shafts threading it, and it is the single most compact statement of what the place is |
| `shots/map/08`, `09` | **the commitment pair.** §6.3 |
| `shots/map/07_depth_{gauge,beams,blind}` | the same camera under the three vertical belief models. §6.4 |
| `shots/map/_strip_*.png` | six frames of each sequence on one sheet |
| `shots/map/m1..m4.png` | one frame of each moment, at the instant of it that carries the shot — 0.62 of the take for three of them and **0.98 for the pitch**, because the hole is not open until the machine is standing over it |
| `shots/map/*.txt` | the machine-readable versions of §2, §5 and §6 |
| `shots/cinema/seq/map_reveal/000..311.png` | **the reveal**, 1920×1080, 24 fps |
| `shots/cinema/seq/m1..m4/` | the four lidar moments at their own lengths |

`shots/cinema/seq/` is **already gitignored** (repo `.gitignore` line 49), so the 632 MB of
sequences do not enter the tree. `shots/map/` is 15 MB and is not ignored, which is the same call
`LIDAR.md` §9.8 made for its ten: the frames are the evidence and hiding them from a clone seemed
worse than the bytes. Change it if you disagree.

---

## 8. What is still wrong

1. **The depth gauge.** §6.4. The most important thing in this document and it is a design question,
   not an art one.
2. **`m3_the_pitch` is weak.** §6.2. It is the honest picture of a thing that does not photograph,
   and if the trailer needs the pitch to *land* then it should land in the survey register
   (`08`/`09`) rather than from the drive.
3. **The trail is invisible in the wide shot.** It is depth-tested, and inside a passage the near
   wall is in front of it. That is correct and it means the trail earns its place only in the close
   third of the reveal and in the shafts. A designer who wants the route legible throughout is
   asking for it to be drawn over the data, which is a different rule.
4. **The whole-route map is sampled at one revolution per 1.7 m**, which is a twelfth of what the
   device really produces. §5.3. The map's shape is right; its *texture* is a sample of the texture.
5. **Nothing in the map is dimmed by age.** A map is not a live sweep, so `age_knee` is set past the
   run and every return is drawn at full value. `ART-DIRECTION` §8.2's *"an old return is dimmer"* is
   a rule about the live view and I have assumed it does not govern a finished map. That assumption
   should be checked: an age-graded map would show the *order* the cave was explored in, which might
   be a better last image than a uniform one and would cost nothing.
6. **Chambers are still cut out of the sweep and domed**, which the cave spike does not do — it
   sweeps a wide drive straight through. In the map that shows as round bulges. They read well and
   they are not what the other project builds.
7. **The pitch tubes interpenetrate the passages they join** in places, and at a grazing angle in the
   close third of the reveal that is visible as a doubled edge. The punch is a centroid test and a
   triangle straddling the bore wall survives it.
8. **The reveal has been looked at by one person who knows what it is.** `LIDAR.md` §4's caveat is
   unchanged and it is the same caveat: this has to go in front of somebody who has not read this
   file. The test is "does it read as a place that was explored, and is it beautiful", and I cannot
   answer the first half.

---

## 9. Every guess

Everything below is mine rather than read out of a document.

1. **The route**: that the exploration is the main descent chain, walked once, each level to its
   own descent head. The cave has crosscuts and side passages and this machine walks past them.
2. **Walk 1.45 m/s and descent 0.85 m/s.** `Book.CHASSIS` bakes the Surveyor's walk clip at
   0.50 m/s (`CINEMA.md` §12.4); a six-minute route at 0.5 m/s would be 180 m rather than 503.
   These are montage speeds and they are not the machine's.
3. **A fix every 40 m of route and at every pitch mouth.** §2. The mechanism is the fiction's; the
   interval is mine and it is the single number that decides how bent the map is.
4. **The 70 mm voxel**, and the argument in §3.1 that it is below the ring pitch at working range.
5. **One revolution every 1.7 m on the map bake and every 0.65 m on a local one.** §5.3.
6. **Ice**: albedo 0.075, `cos^2.6`, and the `0.62 × cos^26` flash term with its ×7 weight. THE-ICE
   §6.2 gives the behaviour in words and no numbers at all.
7. **That ice-over-rock means an ice FLOOR and rock walls.** THE-ICE §5.2's examples are floor ice,
   so this follows, but the document does not say it.
8. **Every radius function in the pitch profile family**, the corkscrew rate (0.22 rad/m at 0.30 of
   a bore), the ring spacing of 0.55 m, and the bore roughness (45 mm in ice, 160 mm elsewhere).
9. **The punch band**: from the pitch floor + 0.35 m to the lip + 0.60 m, and a bore radius
   multiplier of 1.02.
10. **The pitch furniture**: hoops every 1.2 m where the ancients left steel, a retro plate at the
    head and foot of everything descendable, and a chain every 3.2 m on the main descent. The rule is
    `VERTICAL.md` §3.4's; the sizes are mine.
11. **Chambers at 0.95 of the topology's radius rather than inflated.** The sensor test inflated the
    biggest one to 9.5 m so a standing scanner could lay a dozen ground rings; a map needs chambers
    the size the topology says or the plan is a lie about the place.
12. **The whole reveal**: thirteen seconds, the pull-back, 44 → 187 m, 58° → 124°, 4° → 17°, 40 → 34
    mm, the 22% trapezoid ramps, and the slab going 16 m → open. All chosen by looking.
13. **That the reveal should start at the foot of the deepest winze.** §4.1.
14. **The height ramp's 18% of headroom below the cloud.** §3.2.
15. **Every moment's framing, lens, window and recency curve**, and the two `gain: 1.5` exposures.
16. **The trail's width (1.7 px), colour (`GHOST`) and that it sits 0.85 m below the believed sensor
    origin** — i.e. on the believed floor.
17. **`beams` as a vertical belief model.** The envelope arithmetic is not a guess; the idea that a
    machine would estimate a drop that way, and that reach-from-the-top plus reach-from-the-bottom is
    the estimate, is mine.
18. **That the map should not be age-graded.** §8.5.
