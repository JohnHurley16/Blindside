# The ice cave

The designer, 2026-09-10: *"make the cave liok better (why js it still a coal mine)"*,
*"it wonders through the cave and than starts to uncover stuff"*, *"really show off the cave
system"* — and, later the same morning, *"is the assayer the big ancient robot in the cave? it
should end with the dog finding something massive and bright and scary in there."*

They were right, and it was not an art problem that had become a fiction problem. It was a
**fiction problem that had become an art problem**: the cave was modelled when the setting was a
drowned iron mine, `DESIGN-PRINCIPLES.md` §10 turned the world into a valley coming out of an ice
age, `VERTICAL.md` gave the cave four levels and three media — and the *material* never moved.

Written 2026-09-10. Everything measured on this machine unless it says GUESS, and every guess is
collected in §10.

---

## 0. The one-page answer

| question | answer |
|---|---|
| What read as a mine? | Timber sets, rail, sleepers, ballast, tubs, iron props and lagging **on the first frame a viewer sees**, plus a `worked` ramp that put the industry 15 m under the snow. And the ice was **grey** — §1 |
| Why was the ice grey? | Three numbers, all arithmetic rather than taste. The absorption path was 3 cm where it needed to be metres, the red:blue ratio was 3.3:1 where ice is about 17:1, and the scattering albedo was one constant where it has to be two. §2 |
| Does the ice carry the light now? | **Yes, and it is the single biggest change in the pass.** The lamp is a real spot with a position and a cone, and the internal scattering is computed against a cone **62°** wide where the lamp's own is **27°** — so the light bleeds past the edge of its own beam. That does not happen on rock. §3 |
| Is it a glacial cave rather than a mine? | Yes in bands 0 and 1. Icicles, fringes, columns, frozen falls, pool lids with air under them, ice blocks, scallops in the silhouette, a meltwater channel cut down the floor. The mine is still there and it starts abruptly at −38 m, which is the point. §4, §5 |
| Were the workings reduced? | Hard, and by depth, on the layered path only. Band 1 went from carrying rail + sets + gutter + bolt line + ground support to carrying **one cast index plate**. §6 |
| Does it end with the Assayer? | Yes. `spikes/godot/assayer/` is brought in unmodified, stood in the ice at −11 m with its footing frozen in, and found across a ten-frame stills set plus a 32-frame approach. §7 |
| Did the seam survive? | **Yes, and it is asserted every run.** `seed 7 / 240 cells / 1 level` still hashes to `0xAD83E3ED`; the flat cave's prop count is still 19 015 in 946 multimeshes. Two changes tried to break it and were caught — §8 |
| What did it cost? | (§9) |
| Would a viewer want to go there? | **Bands 0 and 1: yes.** The ice reads, the light reads, and the moulin frames are no longer holes with nothing in them. Honest failures are in §9 and §11. |

---

## 1. What read as a mine, and why

I looked at `shots/01_wide_passage.png`, `shots/03_underfoot.png`, `shots/11_set_line.png` and the
eleven frames in `shots/vertical/` before touching anything. Five separate things:

**1. The objects are a Victorian coal mine, and they are in the first frame.**
`01_wide_passage` is timber sets on a 1.2 m module, a rail line with sleepers and ballast, two
tubs, an iron prop, lagging behind the legs and a wall plate — all inside six metres of the lens.
`11_set_line` is the same list with a bus insulator. `03_underfoot` is rails and ballast and
nothing else. Not one frame in the canonical twelve contains ice, water that is frozen, or a
natural surface that has not been blasted.

**2. The palette is coal-mine brown.** `rock.gdshader`'s `rock_dry` is (0.325, 0.250, 0.170) and
the kit's cast iron is (0.058, 0.030, 0.017) against a 5.4 W tungsten lamp at 3200 K. Every
surface in the cave is on the same warm axis, which is correct for the *workings* and is the
reason a viewer reads "mine" in about 200 ms.

**3. The `worked` ramp put the industry fifteen metres under the snow.** `topology.gd` band 1 —
THE-ICE §5.2's karst, *"first marks, low item numbers, corroded, half-buried in flowstone and now
also in ice"* — runs `worked` 48–140, and the works thresholds were written for a cave that was
all mine: rail at >90, sets at >55, gutter at >100, bolt line at >120, ground support at
integ<115. So the karst came out carrying a **fully equipped drive**. That is not first marks.

**4. THE ICE WAS GREY, and this is the real finding.** `shots/vertical/v6_ice_band.png` is the
frame that was supposed to prove the new medium and it is a photograph of a **concrete culvert**:
a smooth grey-white tube with a grey rubble floor and a grey box in it. `ice.gdshader` existed,
was well argued, sampled no cellular function, had scallops and an absorption coefficient — and
produced a material indistinguishable from wet concrete. §2 is why.

**5. Three of the ten vertical frames were, in VERTICAL.md's own words, "a hole with nothing in
it".** `v1_down_the_shaft` is a grey wall and a heap of pale rubble; `v2_up_from_the_bottom` is
98.4% true black; `v4_moulin_meltwater` is a brown void with one beacon in it. The moulins are the
best structural idea in the project and they did not photograph.

---

## 2. Why the ice was grey: three numbers

This is the part worth keeping, because the shader was not *wrong* in shape. It was wrong in
magnitude, three times, and each error cancels the visual effect of the rule it implements.

### 2.1 The path was centimetres

> `float path = mix(0.030, 0.55, clarity) * (...)`
> `vec3 transmit = exp(-ice_absorb * path);`

`ART-DIRECTION` §3.1 and THE-ICE §6.1 both say **the blue is a path length, not a tint**, and the
shader implemented that honestly with a Beer-Lambert `exp()`. But the path was 3 cm to 55 cm.
Against the file's own absorption of (0.42, 0.20, 0.128) m⁻¹, the *clearest* ice in the cave
returned `transmit = (0.79, 0.90, 0.93)` — **a four per cent blue bias.** Four per cent is
invisible.

The physical mistake is treating the path as the *thickness of the ice*. It is not: it is the
distance light **walks** inside before it comes back out. In bubbly ice the mean free path is
centimetres, but the random walk between entry and exit is long, and in clear ice it is metres.
That is why a serac is blue and a bathroom window is not. Now `mix(0.35, 5.2)` m.

### 2.2 The absorption ratio was 3.3 : 1

(0.42, 0.20, 0.128) is red:blue = 3.3:1. Real ice absorbs red roughly **fifteen to twenty times**
as strongly as blue. At 3.3:1 **no path length produces a blue** — it produces a warm grey that
gets darker. Now (0.355, 0.082, 0.021), a ratio of 17:1.

### 2.3 The scattering albedo was one constant, and it has to be two

`ice_scatter = 0.26`, fixed. But `clarity` is supposed to do opposite things at the two ends:

- **bubbly ice is white** — the air turns light round in centimetres and most of it comes back;
- **clear ice is dark and blue** — light goes deep, and what returns has been filtered.

One number cannot be both, so the shader had a single dark grey for every kind of ice in the cave.
It is now two coupled numbers with opposite signs: `path = mix(0.35, 5.2, clarity)` and
`scat = mix(0.60, 0.30, clarity)`.

### 2.4 And then the surface and the body had to be separated

Fixing 2.1–2.3 produced a uniform petrol-teal wall with no white in it anywhere — right hue,
wrong picture. The fix is that **there are two paths, not one**:

| | path | what it is | where it shows |
|---|---|---|---|
| **short** → `ALBEDO` | 3–34 cm | the first-scatter rind. Bright, nearly neutral | where the lamp lands |
| **long** → `EMISSION` | 0.35–5.2 m | the body of the ice | in the shadows, round the beam, in thick lenses |

So a beam entering ice makes **a white patch with a blue halo**, which is what a torch in an ice
cave actually does and is the exact opposite of what it does on rock.

### 2.5 The albedo was then measured down twice

First-scatter albedo went 0.26 → 0.66 → **0.34 for clear conduit ice** (0.60 for bubbly). 0.66 is
about 3.5× the rock family's 0.19 and it put a six-metre ice dome above the legibility ceiling end
to end — ten of fourteen frames came back *"not enough black"*, and in the Assayer's chamber it
**erased the machine**: cast iron at albedo 0.058 in front of a wall at 0.66 is a silhouette, and
the whole point of that machine is that it is the brightest thing in the cave. THE-ICE §6.1 asks
for *"brighter, softer and flatter than a rock one at the same power"*, which is a ratio of about
**1.5**, not 3.5.

---

## 3. The light, which is the biggest single change

`ART-DIRECTION` §2's economy is one lamp and no ambient. On rock that gives a hard pool and a
black room. **Ice does not behave that way, and the difference is the whole opportunity.** Three
mechanisms, in order of how much they buy:

### 3.1 The lamp is now a real lamp

The first shader approximated the carried lamp as *a point source at the camera*, flagged in
`VERTICAL.md` §4.1 as a shortcut. It is worse than a shortcut: a point at the eye has **no shape**,
so the glow it produces is a vignette. `cave_root.gd` now writes the true spot position, axis, cone
angle, energy and range into every ice material every frame (`_ice_lamp()`), including inside the
screenshot loop, because that loop sets `busy` and `_process` returns early.

### 3.2 The halo is built explicitly, and it is the signature

```glsl
float hard = cone(L, lamp_cos);        // the lamp's own 27 degrees
float soft = cone(L, lamp_cos_wide);   // 62 degrees
float halo = clamp(soft - hard, 0.0, 1.0);
float inflow = lamp_energy * att * (hard * 0.40 + halo * 0.95) * wrap;
```

`halo` is the annulus *between* the beam and the cone the scattering fills, and it carries most of
the weight. Inverse square with no linear term, so it dies inside two metres. **A rock wall's lit
area ends where the cone ends. An ice wall's does not**, and that one term is the difference
between "a lamp in a mine" and "a lamp in an ice passage". It is `i02_beam_in_ice`.

### 3.3 `SSS_STRENGTH`, so every other light diffuses too

Godot's screen-space subsurface pass is enabled in `project.godot` and driven by
`SSS_STRENGTH = 0.42 · (1−debris) · (0.45 + 0.55·clarity)`. It puts *every* light in the scene —
the lamp, a beacon pilot, the 12000 K daylight down the collar, the Assayer's own two hot points —
through the surface instead of stopping it there, which is the correct general mechanism and costs
one pass the renderer already has.

**One measured trap.** The default scale of 0.30 is a blur radius wide enough to bleed a curtain's
silhouette halfway across the frame; the first ice frames had a translucent veil in them that was
not an object. 0.10 diffuses light across a scallop and stops at the edge.

### 3.4 Bubble trains, marched into the surface

Three taps along the refracted view vector, layered vertically, brightened white (air scatters
without absorbing, so a bubble train is the one part of an ice wall that is **not** blue). It is
the cheapest possible cue that what you can see is *below* the surface, and it is what stops
polished ice reading as painted plastic. It is also what makes a frozen pool lid read as a lid.

---

## 4. What the ice is made of now

### 4.1 Scallops, in the silhouette — and one Nyquist lesson

The first pass put scallops in the **normal map only**. This file already records why that cannot
work: *"a lamp that sits at the eye returns almost no shading contrast from a normal map, because
N·L equals N·V"* — the finding that made bedding real geometry on the rock family. The same
finding applies to the other family and had not been applied.

So the **low register of the scallop pattern is now real geometry**, in phase with the shader's
high register.

**And the first attempt at that was a Nyquist failure worth writing down.** It used the shader's
own 0.42 m period and its 1.6 helix constant, which shifts the phase by **4.2 m around a ring that
has 40 vertices in it** — four vertices per cycle around the perimeter and 2.8 along the sweep. The
mesh could not carry the pattern and folded it into a set of **curtains hanging down the passage
that were not objects** and that survived `--noprops`. I spent three renders looking for a prop.
The geometry now carries 0.70 m axially against a 0.15 m ring pitch (4.7 samples) with a helix slow
enough for ~17 vertices per cycle round the ring; the 0.22 m and 0.075 m registers stay in the
shader, where a **footprint fade** can filter them properly:

```glsl
float fw = (length(dpx) + length(dpy)) * 0.5;      // the pixel's world footprint, metres
float f22  = clamp(0.22  / max(fw * 5.0, 1e-5) - 0.55, 0.0, 1.0);
float f075 = clamp(0.075 / max(fw * 5.0, 1e-5) - 0.55, 0.0, 1.0);
```

A register switches itself off the moment it is smaller than a pixel, rather than at some
hand-chosen distance. Before this, the inside of the collar at a grazing angle rendered as a
**checkerboard** — a moiré so strong it looked like a tiled floor.

**And it does not break the sensor argument.** THE-ICE §6.2 needs a conduit to have nothing to
*lock onto* along its own axis. A strictly periodic form is the degenerate case, not the exception:
every scallop looks like every other scallop, so it supplies no landmark and no axial constraint.
Lumps would have. This is 100 mm of crescent hollow that reads at three metres and tells an
estimator nothing.

### 4.2 The ice kit — one generator, seven parameter sets

`_revolve()` sweeps a profile about the local Y with a helical flute on it, because that is what
water freezing while it runs actually makes. It writes the ice vertex contract properly: UV2.x is
the distance along the object's own axis, so **the flutes run down an icicle**.

| mesh | rule |
|---|---|
| `icicle0/1/2`, `icefringe0/1` | the crown drips and the drips froze. Placed on the crown **by the section's own ellipse**, so they hang from where the roof actually is. A fringe is seven spikes whose lengths are drawn on a power law, because uniform lengths read as a comb |
| `iceboss0/1` | what landed under a fringe and built back up. Bubbly, so it is **white** — the contrast against the blue wall is the point |
| `icecolumn` | a fringe that reached its boss. Generated **only where the two would actually have met**, which makes it rare, and rare is what makes it worth photographing |
| `icefall` | a wall seep that ran and froze — seven fused lobes that all reach the floor. The single most recognisable object in an ice cave and there was nothing like it here |
| `icelid` | a still pool that froze over. What sells it is not the slab; it is that the shader marches bubble trains **into** it |
| `iceblock0/1/2` | what a roof or a bridge dropped. Two thirds of the loose stone in an ice passage is now ice |
| `icerib` | a flute for the inside of a bore: the rhythm the ancients' rings give a worked shaft, in the medium that has no rings |

Density is driven by **one topology field, `wet`** — a drip is water, and the field that says how
much water is here is the field that says how many icicles there are. Nothing new crosses the seam.

### 4.3 The apron: ice as a fill, not a layer

THE-ICE §5.2's second structural claim is *"the ice is a **fill**, not a layer… a stope with a
floor of clear ice over a muck pile you can see and cannot reach"*. So a `MED_ICE_OVER_ROCK`
station is a **rock** passage with a body of ice lying in the bottom of it, not an ice passage. It
is built as a second, inner surface over the lower fifteen vertices of the same ring
(`_apron_ring` + `_emit_strip`): the rock is still there, still drawn, and now under something.

### 4.4 Water, because a glacier is water

- **A meltwater channel cut down the floor.** `_sweep_edge` cuts a 0.9 m wide, 130–260 mm deep
  notch in the profile of any running conduit, and `_place_water` puts a narrow ribbon in the
  bottom of it. It sits **below** the floor either side, which is the difference between a stream
  and a puddle, and it is the thing that gives an ice passage a direction to look along.
- **Pool lids.** Still water below freezing does not stay water: it freezes from the top and traps
  its own air. The water surface stays — you can see it — and a slab of ice sits 45 mm above it.
- **The frozen waterfall** down one side of the moulin, and on chamber walls.
- **The drip**, which was already there, and the Assayer's own.

### 4.5 The moulins, which were the best thing and did not photograph

`VERTICAL.md` diagnosed the three empty frames as *the mechanic* — a shaft has no floor for the
lamp to find. Half of that is true and half of it was a **missing object**. A shaft in ice is not
empty:

- **a fringe round the lip**, which is what makes the *edge* of the hole read from above;
- **ribs down the bore**, every 1.6 m, standing off the wall into it;
- **a frozen waterfall the length of the moulin**, on the side the meltwater ribbon runs;
- **broken ice in the cone at the foot** — half of what a hole in ice drops is the hole.

And the walls now light themselves, which is the other half.

---

## 5. Where the ice is, and where it is not

Unchanged from `VERTICAL.md` §4 and THE-ICE §5.2, because the interleave was already right:

| band | elevation | medium | what a machine meets |
|---|---|---|---|
| 0 — the fill | 0 to −15 m | **ice**, 266 stations | dead ice and meltwater conduits. Scalloped, blue, fringed, running. No ancients |
| 1 — the karst | −15 to −38 m | rock + 92 ice-over-rock | bedrock re-cut by water. **One cast index plate**, and nothing else |
| 2 — the workings | −38 to −72 m | worked | the mine, and it starts abruptly |
| 3 — the deep | below −72 m | worked, dry | past the melt front |

**A machine now meets ice for about 160 m of drive and 26 m of vertical before it meets iron**, and
the first iron it meets is one 160 × 100 mm plate bolted to a natural wall with a number on it.

---

## 6. The workings, reduced and re-cast

All of this is on the **layered path only**, guarded by `levels > 1`, because `S_WORKS` is field 7
and is inside `SCHEMA_V1_FIELDS`. The `flat` arm of every line below is the pre-change rule verbatim.

| works | flat (unchanged) | layered |
|---|---|---|
| rail | worked > 90 | **> 168** |
| timber sets | > 55, every 2nd station | **> 132, every 4th** |
| bolt line | > 120 | **> 182** |
| gutter | > 100 | **> 175** |
| pipe run | > 140 | **> 196** |
| the Bus | > 205 | **> 224** |
| ground support | integ < 115 | **integ < 95 and worked > 150** |
| spoil | > 70 | **> 150** |
| ventilation duct | > 150 | **> 200** |
| brought kit (crates, chargers) | any | **worked ≥ 46** — nothing brought above the karst either |
| **cast index plate** | > 110, every 12th | **> 58, every 17th** ← *down, not up* |

The plate moves the other way on purpose. **The plate is the first iron.** THE-ICE §5.2's *"low
item numbers"* is a thing you read off an object, so the object has to be there before anything
else is.

Beacons are untouched. They are the players' and they are the light.

---

## 7. The Assayer, found

The designer, mid-task: *"it should end with the dog finding something massive and bright and
scary in there."*

### 7.1 It is brought in, not rebuilt

`assayer.gd`, `materials.gd`, `mb.gd` and `chamber.gdshader` were copied **verbatim** from
`spikes/godot/assayer/` and nothing inside them was edited. The cycle, the mechanism, the two hot
points, the blackbody fit and the 75-second clock are that spike's and stay that spike's. 20 336
triangles, one clock, `set_phase()`.

Two things had to be set from outside, and both are that spike's own methodology rather than
exceptions to it:

1. **`hot_energy` 72 → 34.** `assayer/NOTES.md` §4: *"It is a **ratio**, not a wattage, and
   ART-DIRECTION 2.2 is explicit that it does not survive a change of renderer."* It does not
   survive a change of **room** either. 72 was calibrated against a chamber of rock at albedo
   0.19–0.32; this machine stands in a tube of ice at 0.34–0.60, so the same output comes back
   about twice as strong. Uncorrected, the whole discovery sequence measured **0.1–3.6% true black**
   against a 70% floor and the strike read as a flood rather than a flash.
2. **The anvil ring's `omni_range` 12 → 6 m.** The assayer spike's chamber was the entire world, so
   nothing was ever *outside* it. Here the chamber is a 6.4 m dome with eighty metres of passage
   round it, and six **shadowless** omnis at the mast foot light the dome's shell from inside and
   make it glow like a paper lantern from any camera in the drive. The first `a9_the_room` is a
   photograph of exactly that: a lit egg in a black void.
   **The fix is not shadows.** I tried that and the machine went dark, which is `assayer/NOTES.md`
   §4.1's first bug arriving on schedule: the ring sits at r = 0.62, *inside the anvil's own
   chamfer*, so a shadowed source there is a source sealed in a casting. The range comes down
   instead, and the cameras stay in the room.

### 7.2 Where it stands, and the fiction cost

**It stands in the ice, in the largest chamber on level 0, at −11 m.** THE-ICE §5.2's band table
says band 0 has *"none… this band is below the ancients' surface works and above their workings"*,
so this contradicts a table. It is done on the designer's instruction, and it is flagged rather
than smuggled.

**But there is a reading in THE-ICE itself that makes it consistent**, and it is the second
structural claim of the same section: *"the ice is a **fill**, not a layer. The glacier pushed into
the openings it found."* So the machine was here first and the ice came into the chamber around it.
Its footing is frozen in, there is a floor of clear ice over the muck it stands on, and the
meltwater running off it is the same meltwater that turns its wheel — which is THE-ICE §4's *"it
started again"* with the mechanism visible in the same frame as the machine.

**What still needs a ruling** (§11): whether the *whole* ancients' works move up, or whether this
one Assayer is a high outlier that the ice reached first.

### 7.3 The site is dressed as ice, not as a plinth

`_dress_assayer_site()`: five overlapping pool lids under the anchor pads; fourteen ice bosses
grown **up** the footing; twenty-two broken blocks the roof shed onto it; four frozen falls on the
chamber wall so the machine is silhouetted against ice rather than against black; a fringe of
sixteen round the crown over it.

### 7.4 The sequence, and the three findings obeyed rather than rediscovered

`shots/ice/assayer/` — ten stills at 1920 × 1080 plus a 32-frame approach at 1280 × 720.

| frame | phase | what it is |
|---|---|---|
| `a1_edge_of_the_lamp` | 22 | dormant. It can only be found by the visitor's own beam |
| `a2_closer` | 30 | it is *made* |
| `a3_footing_frozen` | 38 | it has been here longer than the ice |
| `a4_the_scale` | 46 | look up |
| `a5_the_slew` | 55.6 | **it moves** |
| `a6_click_one` | 62.4 | it is counting |
| `a7_click_nine` | 70.6 | and it is nearly done |
| `a8_the_strike` | 71.05 | 4000 K, the only white light in the game |
| `a9_the_room` | 71.05 | what it has been standing in, seen because the machine lit it |
| `a10_the_decay` | 74.2 | and it goes back to waiting |
| `seq_000..031` | 58 → 72.5 | a dolly from 6.1 m to 3.0 m while the slew, all nine clicks and the strike happen — the machine does not wait for the visitor to arrive |

The three findings from the Assayer spike were taken as given: **a dormant Assayer emits nothing**,
so the approach starts close enough for the visitor's lamp to reach it; **the slew is only visible
if the camera looks at the bearing race**, so `a5` is aimed at the race and not at the boom; **the
wind cannot fit in four seconds**, so the ratchet starts before the sequence does.

### 7.5 And one finding of my own, which cost six renders

**A camera in this cave must stand on the drive centreline, and `back` is measured in stations.**
The first `_asy_pose()` walked back along *one* tangent — the tangent at the chamber, which is not
the tangent anywhere else, because the drive wanders a cell every four stations. At seven metres
out the camera was a metre and a half off the line and **inside the tube's wall**. Every frame of
the first discovery sequence is a photograph of the inside of a wall.

And the second half of the same lesson: `VERTICAL.md` §5 already says *"the chamber dome is a 5–7 m
hemisphere with a 2.9 m tube running through it, so anywhere off the centreline by more than the
tube's half width is inside the tube's wall."* Every lateral offset in this set is now zero, and
the "room" a viewer sees is the **drive** — 5.9 m wide and 6.75 m tall at a chamber station. A
6.6 m machine in a 6.75 m drive is arguably a better scale reveal than a dome would have been,
because it nearly touches the roof.

---

## 8. What must not break, and how it was caught breaking

`spikes/godot/cloud/` cuts its belief frames from this cave's cameras, and four cave sequences in
the current trailer cut were rendered against topology hash `0xAD83E3ED`. The flat path is still
the default and is still asserted every run:

```
topology hash v1 : 0xAD83E3ED   (flat path, same seed and length)
v1 regression    : PASS   (recorded 0xAD83E3ED)
prop instances   : 19015  in 946 multimeshes
```

**Two changes in this pass tried to break it and were caught by a number rather than by a hash.**

1. The brought-kit rule was written `worked > (0 if flat else 45)`, which is not the old rule on
   the flat path — the old rule was unconditional, and `worked == 0` stations lost their crate. The
   hash held (the `draw_pct` stream did not move) but **the flat cave's prop count went 19 015 →
   19 033**, which is what said it. It is `worked >= (0 if flat else 46)` now.
2. `const APRON_KS` is a `PackedInt32Array` and GDScript will not accept one as a constant
   expression; it is a `static var`. Caught by `check.sh` in three seconds, which is the argument
   for `check.sh`.

**The auto-memory note applies literally here**: *"a `check | head && git commit` chain merged a
file that did not compile."* Every edit in this pass went through `./check.sh` before a render, and
two of them failed it.

`topology.gd` is unchanged in discipline: integers only, millimetres, no floats, no dictionary
iteration, the counter-based `draw()` untouched. The only edits are threshold expressions inside
`_assign_works`, each with a `flat` arm that is the old constant.

**Nothing outside `spikes/godot/cave/` was touched.** The four Assayer files were *copied in*.

---

## 9. What it costs

Measured on the machine in `NOTES.md` §1 (RTX 3080 Laptop, Godot 4.7.2, Forward+), 1920 × 1080
render target, seed 7, 240 cells, walking at 3.4 m/s. **`tasklist` reported zero other Godot
processes for both runs**, so these are absolute rather than relative — but the machine throttles
(see `cool.sh`) and the run-to-run band on this spike has been measured at 85–114 fps p50 for the
same build, so treat the *ratio* as the number.

| | flat cave `--levels=1` | **the ice cave** `--levels=4` | the same 4-level cave *before* this pass (`VERTICAL.md` §7, at 1.7 m/s) |
|---|---|---|---|
| fps mean / p50 | **193 / 196** | **140 / 134** | 174 / 168 |
| fps p05 (worst 5%) / min | 128 / 121 | **42 / 9** | 133 / 11 |
| GPU ms p50 / p95 / max | 4.19 / 6.54 / 7.8 | **5.72 / 14.97 / 158** | 4.91 / 6.20 / — |
| draw calls p50 / max | 301 / 447 | 309 / 847 | 268 / — |
| primitives p50 / p95 / max | 225 k / 291 k / 314 k | **272 k / 1.09 M / 2.49 M** | — |
| shell triangles | 113 656 | 380 766 | 370 546 |
| prop instances | 19 015 in 946 mm | 56 256 in 2 771 mm | 57 411 in 2 597 mm |
| chunks | 49 | 274 | 272 |
| video memory | 189 MB | **250 MB** | 204 MB |
| generation: topology / dressing | 6.8 ms / 724 ms | 45.8 ms / **1 875 ms** | 42.7 ms / 1 369 ms |

**The honest reading, against the cave this pass started from:** GPU frame time **+16%**
(4.91 → 5.72 ms p50), video memory **+23%** (204 → 250 MB), dressing **+37%** (1 369 → 1 875 ms),
and the mean frame rate **−20%**. Shell triangles are almost unchanged (+2.8%) and prop instances
went *down* slightly; the cost is in what those props are and in the second material family being
on screen more of the time.

**And one number is a real regression, not noise: the worst 5% went 128 → 42 fps.** The flat cave
measured at the *same* 3.4 m/s holds 128, so this is the ice cave specifically. Two causes, and the
split is visible in the table: `primitives max` is 2.49 M against 314 k on the flat path (the ice
kit arriving all at once when a wet chamber becomes resident), and `GPU max` is 158 ms in a single
frame, which is chunk-entry pipeline compilation — the stall `NOTES.md` §5.2 and `VERTICAL.md` §7
both already name, made worse because there are now more distinct materials to compile per chunk.
Pipeline pre-compilation would remove the second; the first is a density decision and there is
room to halve the fringe counts.

The brief's clean baseline of **206 mean / 87 worst** is close to the 193 / 128 measured here for
the same flat cave, which is inside the documented run-to-run band.

**Where the new cost is.** Three places, and none of them is the shader's arithmetic:

1. **The ice kit is a lot of small instanced meshes.** A wet ice station can carry five fringes,
   five bosses, a column, a rib and a lid. Frames in the ice band render 0.8–1.1 M triangles
   against 0.2–0.3 M in the flat cave. They are instanced and they are cheap per instance, but the
   count is real.
2. **`SSS_STRENGTH` adds Godot's subsurface pass** whenever an ice pixel is on screen.
3. **The Assayer** is 20 336 triangles, eight lights (one shadowed) and a particle emitter.

`shots/ice/` GPU times at 1080p ranged 2.6–12 ms per frame with the heaviest being the
icicle-and-column frames.

---

## 10. Everything I guessed

1. **`ice_absorb = (0.355, 0.082, 0.021)` m⁻¹.** The 17:1 ratio is from the physics; the absolute
   scale is chosen so 0.4 m of ice is visually neutral and 5 m is the colour of a crevasse.
2. **`path_bubbly 0.35 m`, `path_clear 5.2 m`.** The random-walk distance. Nothing in the docs
   gives a number.
3. **`scat_bubbly 0.60`, `scat_clear 0.30`, first-scatter 0.60 / 0.34.** Calibrated by measuring
   `lumcheck.py`, not by reference.
4. **The 62° scattering cone against a 27° lamp.** Chosen so the halo is obviously wider than the
   beam and obviously not the whole room. It is the one number in the pass I would most like a
   designer to look at, because it *is* the effect.
5. **`SSS` scale 0.10, strength 0.42.** Measured down from a visible artefact, not derived.
6. **The geometric scallop: 0.70 m period, 100 mm amplitude, helix constant 0.25.** Period and
   helix are Nyquist against the mesh; the amplitude is taste.
7. **Every threshold in §6.** They are chosen to produce "band 1 carries one plate", which is a
   reading of THE-ICE §5.2's prose, not a number anyone wrote down.
8. **The reveal rule** — one ice station in nineteen, from an integer hash of the station id. It is
   a **client** rule, not a topology one, because `S_WORKS` is inside the v1 hashed fields.
9. **All ice prop scalars** (clarity/polish/debris/wet per material) and all the site dressing
   counts.
10. **`hot_energy = 34`.** Halved by measurement against the exposure bands, not swept the way the
    original 72 was. A proper six-point sweep in the ice would be an hour.
11. **The Assayer's chamber choice**: biggest chamber on level 0's main drive, no pitch in it, at
    least four stations from either end. Deterministic, and arbitrary.
12. **The exposure row for ice.** THE-ICE §6.1 proposes that the ice band gets its own row and does
    not write one. I have not written one either — §11.

---

## 11. What is honestly still wrong

**1. The exposure contract fails across the ice set, and I did not fix it — I moved it.**
`python lumcheck.py shots/ice` puts **11 of 14** frames outside `ART-DIRECTION` §2.9, and almost
every failure is *"not enough black"*: 16–63% true black against a 70% floor. Nothing is blown any
more (the worst is 1.2%), and the "unsourced light" flag is a **false positive** — ambient is
disabled and the world background strength is zero, so every lit pixel is still traceable to the
lamp, a beacon pilot, the collar daylight or the Assayer. The checker reads a bright frame as
unsourced; on ice, a bright frame is what one lamp produces. THE-ICE §6.1 predicts
exactly this and says the ice band should get its own row — *"softer falloff, and it is the one
place in the cave where the darkness relents"* — but **nobody has written that row**, so the
contract now reports failures that may be correct behaviour. Somebody has to decide what the ice
band's floor is before this can be a gate again. Until then the number is not a verdict.

**2. The framing needed five passes and would take a sixth.** Four separate frames were
photographs of the inside of a wall, one was rendered a metre from the Assayer's ladder in a shot
whose entire job is to contain no iron, and one put a blown lamp pool across a quarter of the
frame. All six are fixed, and the fact that there were six says the scouting run `CINEMA.md`
describes — photograph the candidates, choose by looking — has not been done for this set.
`i07_frozen_pool` and `i13_uncovered` are still the weakest two: both are bright and have little
black in them, and neither points at its subject as clearly as `i12_first_iron` now does.

**3. The Assayer's scale reveal does not have room to be a reveal.** `_make_chamber` widens only
±2 stations, so the room a 6.6 m machine stands in is 3 m long. From outside it the drive is
3.2 m tall and the mast is simply not visible; from inside it, the crown is between the camera and
the mast head. `a4_the_scale` is the weakest frame in the set for that reason. **This is a
generator problem, not a camera problem**: a chamber that has to hold the Assayer needs a
`min_crown` and a longer widening, and `WHAT-HAPPENED-HERE.md` §6.7's G4 (*"the Assayer chamber
≥ 8 m crown"*) is a rule the client currently satisfies by accident and the plan does not carry.

**4. The chamber/tube interpenetration is now load-bearing and it is not fixed.** `NOTES.md` §7
lists it as a weakness; this pass hit it four separate times (every early Assayer frame, the
`a9_the_room` lantern, the `i10` slab, the first `_asy_pose`). A dome and a tube that both draw
their full surface where they overlap means **there is no safe camera off the centreline in any
chamber in this cave.** It should be fixed before any more cinematography is attempted, and the
fix is to cut the tube where the dome owns the space.

**5. The ice hue is a decision nobody has ratified.** It is cyan-blue, which is what the physics
gives, and it sits next to `BELIEF-CATALOGUE`'s cyan. `ART-DIRECTION` §9's no-hue-axis rule is
satisfied *honestly* — the material has one colour and the distance does the work — but THE-ICE
§2.6 already flags that the snow is close to the colour of belief, and now the ice is too.

**6. The ancients in band 0.** §7.2. It is on instruction and it contradicts a published table.

**7. `--levels=1` is still the default**, so none of this is what a `--path spikes/godot/cave` with
no arguments renders. That is deliberate (§8) and it is also a trap: the flat cave **is** the coal
mine, and it is what anybody who runs this spike without reading sees first. The day the trailer
cut is re-shot, the default should move to 4 and the frozen flat path should be deleted.

---

## 12. How to run it

```sh
G="C:/Users/jackh/Downloads/Godot_v4.7.2-stable_win64.exe/Godot_v4.7.2-stable_win64.exe"

# THE ICE SET -- 14 frames at 1920x1080 into shots/ice/
"$G" --path spikes/godot/cave --resolution 1280x720 -- \
    --levels=4 --shotset=ice --shotdir=ice --shotsonly

# THE ASSAYER -- 10 stills plus a 32-frame approach into shots/ice/assayer/
"$G" --path spikes/godot/cave --resolution 1280x720 -- \
    --levels=4 --shotset=assayer --shotdir=ice/assayer --shotsonly

# watch the Assayer's cycle run live, in the ice
"$G" --path spikes/godot/cave --resolution 1280x720 -- --levels=4 --stay

./check.sh                    # GDScript parse gate. RUN IT BEFORE EVERY RENDER.
./shadercheck.sh              # shader compile gate -- check.sh never compiles one
python lumcheck.py shots/ice  # the exposure contract, linearised
```

New flags: `--p=N` parks the Assayer's clock at phase N; `--noassayer` leaves it out.

| file | what changed |
|---|---|
| `ice.gdshader` | rewritten. Two paths, a real lamp, a halo, bubble trains, footprint fades, `SSS_STRENGTH`, prop overrides |
| `dressing.gd` | the ice kit (`_revolve`, `_make_ice_kit`), `_dress_ice`, the apron, the meltwater channel, `_place_reveals`, `_dress_assayer_site` |
| `topology.gd` | `_assign_works` thresholds, `levels > 1` arm only. Nothing else |
| `cave_root.gd` | `_ice_lamp()`, `_build_ice_shots()`, `_build_assayer_shots()`, `_assayer_sequence()`, the Assayer's construction and clock |
| `project.godot` | subsurface scattering enabled, scale 0.10 |
| `assayer.gd`, `materials.gd`, `mb.gd`, `chamber.gdshader` | **copied in verbatim from `spikes/godot/assayer/`. Not edited.** |
