# Art direction

What the world looks like when it is rendered properly — Phase 5, Godot, the 3D client.
Not the spectator display: `SPECTATOR-DISPLAY.md` is a diagram of this world and has its
own visual language. §8 says where the two agree and where they must not.

This document is one direction assembled from four independent passes, with the parts that
did not survive measurement removed rather than softened. Where a number is measured, the
probe that measured it is named. Where it is a guess, it is in the guesses list at the end.
`CLAUDE.md` says ask rather than invent: the six questions that actually block are in
**Needs a designer decision**, and the one I most want overruled is §11.

**Everything here is a parameter, a node graph, or generator geometry.** Nothing in this
document needs a modeller. That is a constraint, not a boast: the caves are generated, the
agents are parametric, and there is no art team.

---

## 0. The finding that reorders everything, and it is two characters

Three of the four passes into this problem concluded that a carried lamp cannot light a
scene, and two of them then spent new fiction buying a second light source to fix it. All
three were measuring the same bug.

`agent_model/build.py:312`:

```python
lamp.rotation_euler = Euler((0, math.pi / 2, 0))
```

`Ry(+90°)` takes the spot's local `−Z` to world `−X`. The head's forward is `+X`. Verified
by raycast against the built rig in Blender 5.2 (`docs/art/agent/av_probe.py` re-aims it;
the raycast itself is quoted below):

```
AS BUILT  Euler((0, +pi/2, 0))
  lamp -Z (beam dir): [-1.000, +0.000, +0.000]
  first hit         : 'eye_lens' at 0.014 m

PROPOSED  Euler((0, -pi/2, 0))
  lamp -Z (beam dir): [+1.000, +0.000, +0.000]
  first hit         : nothing within 50 m
```

**The head lamp has never left the machine. It fires into its own eye lens at 14 mm.**

Two renders, same shot, same 600 W, same everything — the only difference is the sign:

| render | mean | >0.05 legible | <0.02 black | |
|---|---|---|---|---|
| `docs/art/agent/av_01_lamp_asbuilt.png` | 0.0017 | **0.36%** | 99.47% | a black frame with a smear on the machine's own head |
| `docs/art/agent/av_02_lamp_fixed.png` | 0.0115 | **4.36%** | 93.49% | a lit passage, rubble throwing hard shadows toward camera, the machine a black silhouette |

**Twelve times the legible fraction, for one character.**

**What this retires.** Every "power does nothing" table in the earlier passes — 5.7× the
wattage moving the legible fraction by 0.00 percentage points, 3.3× albedo moving it 0.5
points, a lamp changing 0.97% of frame inside a box on the machine's own head. Those are
all measurements of a light pointing backwards. They must not be cited again. The
*qualitative* claim survives and matters (a head-mounted forward spot does not light the
machine it is bolted to — §2.4 makes that a virtue); the *quantitative* claim that no
amount of power produces a picture is false.

**What this costs to fix:** one character. It is item 1 in §10 and it blocks every other
lighting judgement, because until it lands, every dark render in this repo is graded
against a broken rig.

I did not make the change: `agent_model/` belongs to another workflow. The probe re-aims
the lamp at runtime in `_fix_lamp()`.

---

## 1. The one sentence

> **A drowned iron mine that never stopped working, photographed by one lamp somebody
> carried in: cut rock and black castings inside a three-metre pool that falls off ninety
> to one, nine-tenths of every frame true black, and the only bright surfaces in the world
> are the ones something is still rubbing.**

The same sentence as a build contract, which is the form a shader author can start from on
Monday:

1. **One rock material, four scalars, world-space mapped, no image texture anywhere.**
2. **Four light sources, all diegetic, world background strength zero.** If a pixel is lit,
   name the fixture.
3. **Wear is gravity, not noise.** Mud low, dust on horizontals, scuff on leading edges.
4. **Value carries meaning; hue does not.** One warm rock family. No biome colour.
5. **Everything is ruined except what is still in use, and that is polished bright by the
   work itself.**

---

## 2. Light

### 2.1 The economy — four sources, and a fifth that needs a ruling

| source | who owns it | reach | colour | notes |
|---|---|---|---|---|
| **the work lamp** | any agent with `optical` | floor to ~6 m, walls to ~20 m | **white** `(1.00, 0.98, 0.95)` | 50° cone, tilted **8–10° down** so the pool lands inside the camera frustum |
| **running lights** | every agent | lights nothing past ~1.5 m | team, at **strength ≤ 3** | see §4.5 — these may not be lamps at all |
| **the machinery** | the world | rock legible to ~18 m | 1900 K → 2400 K, 4000 K at the strike | the 75-second cycle, §5.4 |
| **the shaft** | the world, two of them | its own chamber | 12000 K `(0.60, 0.74, 1.00)` | the only cold light, and the only daylight |
| *(contingency)* **the residual circuit** | the world | its own bay, ~5 m | 2100 K `(1.00, 0.72, 0.42)` | **§2.8. Needs a ruling before anything is modelled against it.** |

**World background strength is 0.** `agent_model/render.py:73` currently sets
`(0.004, 0.006, 0.010)` at strength 1.0. In a cave that is light arriving from infinity
through solid rock, and it is *cool*, which is the worst possible colour to leak into a
world whose cool half means belief. It contributes almost nothing photometrically, which is
exactly why keeping it is a habit that grows. Delete it.

**`render.lights()`'s four studio lights do not exist in the match.** A 320 W cold rim, a
warm key, a fill and an under-bounce, all `TRACK_TO` the agent. Keep them in `agent_model`
for catalogue and marketing renders — those are not the game — and never in a match scene.
They are also the direct cause of the team-identity failure in §4.3.

### 2.2 Denominate in ratios, not watts

The earlier passes argued 70 W against 600 W. Under zero ambient with a single source and a
fixed tone curve, **lamp power and camera exposure are the same knob**: 70 W at +3 stops is
the same image as 600 W. A number in Blender watts also does not survive the move to
Godot, whose light units differ.

**So the durable part of this section is the ratios, and they should be what gets written
into the client:**

| relationship | target |
|---|---|
| floor 3 m ahead, grazing | ≈ 0.08 relative luminance (about half mid-grey) |
| near wall at 1.6 m | **blown, deliberately** |
| brightest legible : dimmest legible, within one frame | **≈ 90 : 1 across three metres** |
| wall at 8 m | ≈ 0.06 — the last thing that reads |
| wall at 25 m | black |

Pick the wattage that hits those on whatever renderer is in front of you, and re-derive it
after the aim fix rather than inheriting a number from a pass that measured a broken lamp.

### 2.3 The falloff is the style, and the near wall is allowed to clip

**Do not compress the ramp.** No exposure compensation, no auto-exposure, no tone curve that
rescues the far end. A 90:1 falloff across three metres is the one thing that says *carried
light* rather than *lit level*, and it is precisely the thing ambient cannot fake. Keep AgX
with a shoulder; let the near wall blow.

### 2.4 Backlight the agent by default — the honest silhouette pays for itself

A head-mounted forward lamp lights the ground in front of the machine, not the machine.
Once the lamp is aimed correctly this stops being a defect and becomes the best free thing
in the direction, because `DESIGN.html` already requires:

> *"chassis class and mounted modules determine the outline, and that outline is always honest"*

**A backlit machine is a loadout readout — but it is a claim about the camera, not about the
lamp.** Measured both ways (§4.4): with the machine at the frame edge and its pool beside it,
bare and loaded differ by **0.08% of frame**, because most of the outline falls on unlit rock
and is black-on-black. With the machine **between the camera and its own pool**, so its
outline lands on lit floor, the same comparison is **0.71%** — nine times the read for a
camera move and no lighting work at all.

> **Camera rule: when the lamp is on, favour framing that puts the machine between the
> viewer and its own pool.** The silhouette only carries information where it falls on
> something lit.

The corollary is the identity split, and it resolves a conflict the earlier passes had:
**the outline says what it is; the emissives say whose it is.** Two channels, no
competition.

### 2.5 Kill the team-tinted lamp

`build.py:307`:

```python
lamp_data.color = tuple(0.6 * v + 0.4 for v in skin.light)
```

For team A, whose `skin.light` is `(0.2, 0.9, 1.0)`, that evaluates to **`(0.52, 0.94, 1.00)`
— a cyan work lamp.** Every surface team A lights comes back cyan, in a game whose display
palette reserves cyan for belief (`SENSED #63D6F7`, `GHOST #9FE8FF`), in the one screen —
the replay — that draws both layers in a single frame.

- **Work lamps are white, `(1.00, 0.98, 0.95)`, for every team.** Real work lights are
  white, and a tinted one destroys material read.
- **Nothing in the world is ever cyan.** Not a lamp, not a strip, not a status LED. Cyan
  means belief, in both registers, and the world side is the cheap one to change.
- **`SKINS["salvage"].light = (0.9, 0.2, 0.2)` also goes.** Red is lethal and nothing else.
  A healthy salvaged machine glowing red says "dying" in both registers. Use a dead
  grey-amber `(0.85, 0.72, 0.55)`: old bulbs, not a casualty.

All four passes reached these independently. Treat them as settled.

### 2.6 What the darkness is made of — nothing, except where the fiction supplies silt

The temptation is to fill the black with atmosphere so it looks moody. Refuse it: the black
is the subject, and it is where belief lives (§8).

- **Resting cave volume scatter 0.008–0.012**, anisotropy 0.55 (forward-scattering, like
  real silt and water), colour `(0.85, 0.86, 0.90)` so it does not blue-shift.
- **Silt is the only thing that raises it.** `BLD-96` already models silt as transient,
  movement-raised and mass-scaled. Local density to ~0.05 behind a moving agent, decaying
  over 10–20 s; 0.15 is self-blinding.
- The consequence is the best free effect available: **the beam is only visible when the
  agent has stirred silt.** It appears when you move and fades when you stop. Movement makes
  you visible in two senses at once, which is what the whole game is about.
- **Below the waterline the medium changes:** scatter 0.35, absorption weighted off red,
  anisotropy 0.8. Light dies in 4–6 m instead of 20.

### 2.7 The world does not accumulate

One pass proposed that lit ground stays faintly lit after the beam leaves. That is ambient
light with no source wearing a costume, and per `CLAUDE.md` it is exactly the kind of damage
that is invisible for months.

**The world goes black.** What survives the beam leaving is two things, both honest:

- **specular, on wet surfaces only.** Wet rock at roughness 0.10 returns a hard glint to any
  source at any angle; dry rock at 0.96 returns nothing. A wet passage stays findable and a
  dry one does not — which promotes the flooding axis from decoration to navigation.
- **the belief cloud**, which is the game's actual memory, is already built, and is *honest
  about being a memory* because it is cool, sparse, and frequently wrong.

### 2.8 The contingency: the residual lighting circuit

`THE-MACHINERY.md` §8 establishes **THE BUS**: *"a conductor running the length of the
workings, energised on a duty cycle to drive haulage that no longer exists."* If the Bus is
live, a lighting circuit hung on it is live too. That is an inference from a claim the
fiction has already paid for, not a new claim — which is what makes it the only legitimate
second source anyone proposed.

**But it is no longer forced, and that changes its status.** The pass that proposed it
concluded *"there is no third answer that is not an ambient cheat."* There is: aim the lamp.
So the circuit is not the key light this direction needs to be legible. It is a content
decision with two real benefits and one real cost:

| for | against |
|---|---|
| light becomes the tell that the Bus hazard is live near here | it erodes *"the only light is what a machine brings"*, which is the premise |
| a lit fitting separates worked ground from natural cave for free, which is the depth gauge (§7) | 8–14% of fittings alight across the workings is a lot of standing world light |
| a landmark both teams can see and neither owns | it makes the dark less frightening, which is the whole point of the dark |

**Recommendation: hold it as the named fallback for §11's kill test, and ship it only on an
explicit ruling, at the low end** — 8% alight, output low enough that a fitting lights its
own bay and dies before the passage does. The form is two meshes and a point light on a
bolt line the generator is already drawing: a cast bulkhead lamp, wire cage, one glass,
bolted to the haunch at 2.2–2.6 m — above an agent's head, below the crown. Placement by
*workedness*, not depth: natural cave 0, driven passage 1 per 12 m, chamber with plant 3–6,
then a survival roll.

### 2.9 The exposure contract, and it must be asserted in CI

`palette.py` asserts its own hierarchy at import time (`_check_hierarchy`). The world side
deserves the same, on a fixed camera set, rendered at low samples, histogrammed, asserted.
An artist who quietly lifts the ambient to "make it readable" then fails at build time
rather than in month six.

**The arithmetic matters more than the thresholds.** `palette.py:154-163` documents the
correct method and names the alternative:

> *"Doing this on the gamma-encoded values instead — which is the easy mistake — puts
> WARM_DIM at 0.41 and the assertion below fails on a palette that is in fact correctly
> ordered, because gamma encoding compresses the dark end."*

Three of the four earlier passes' measurement scripts (`im_lum.py`, `lumstats.py`,
`ruins/stats.py`) compute relative luminance on gamma-encoded values. **A gamma-encoded
threshold of 0.05 is linear 0.0039 — essentially black.** So every "% of pixels legible"
figure in three of the four documents is far weaker than it reads, and none of them is
comparable to any figure in the fourth. `docs/art/agent/av_measure.py` linearises, and
prints both columns side by side so the size of the error is visible.

Targets, **linearised**, per frame on the canonical set:

| band | target | why |
|---|---|---|
| `> 0.50` blown | **≤ 3%** | above that it is a lit level, not a mine |
| `> 0.18` mid or better | 1–25% | material lives here |
| `> 0.05` legible | **3–20%** for a lamp frame; up to 50% for a shaft or a strike | below 3% is unplayable; above 20% something is unsourced |
| `< 0.02` true black | **≥ 70%** for a lamp frame | the dark is the material |

---

## 3. The cave

### 3.1 One rock material, four scalars, no hue axis

Eight world axes × naive material variation is a combinatorial content problem that will be
solved with hue, and hue will make the season system a palette swap. **No axis gets its own
hue.** Everything is one shader driven by four numbers plus a waterline.

| scalar | drives | is really |
|---|---|---|
| `wet` 0→1 | roughness 0.96→0.10, albedo ×0.6, a film normal, drips below overhangs | the flooding axis, and the legibility axis |
| `fracture` 3→14 | voronoi frequency, bump 0.15→0.9 | **rock type**: absorbent = friable, tight, spalled; reflective = dense, planar, blocky. Sonar quality, expressed as surface |
| `bedding` 0.4→3.5 | contrast of a world-Z banded gradient, beds at 0.25–0.6 m | one of the two scale cues |
| `worked` 0→1 | natural surface → half-barrel drill scars; as geometry, a flat floor, a sprung arch, a bolt line | the prior industry, and the depth gauge |

Three rock values in the entire game, all desaturated, all one warm buff family
(≈ +22% R / −28% B off neutral):

```
dry, lit            (0.340, 0.260, 0.175)   #9E8B74
wet, above the line (0.190, 0.150, 0.105)   #796C5B
submerged           (0.090, 0.075, 0.062)   #554D46
tide-mark crust     (0.520, 0.470, 0.400)   #BFB6AA
scoured floor       (0.420, 0.360, 0.280)   #ADA290
```

`palette.py`'s `ROCK #15110D` / `ROCK_LIT #3A2E22` are the same pair at the schematic's
weights. Use them as the shared anchor — that is where the two registers agree for free.

**Rock type changes surface, never colour.** This is the single place where "biome = hue
swap" will be reached for, and it must be refused in writing now.

### 3.2 World-space mapping, and never a UV

`materials.py:141` binds `TexCoord → Object` into both noise nodes of `wet_rock`. On today's
single dome that happens to equal world space. The moment `blindside-gen` chunks a
120 × 72 m cave — which it must — every chunk gets its own origin and the noise breaks at
every seam. **Use `Geometry → Position`, triplanar.** One node, and it must land before the
shader touches a generated cave.

And the harder rule: **there is not one image texture, UV map or bitmap in this repo, and
there must never be one.** A generated cave cannot be unwrapped. World-space procedural is
not an optimisation here, it is the only option — and it is why this direction can ship as
numbers and node rules rather than as an asset library.

### 3.3 The scale rule, and it is the most valuable rule in this document

Bedding frequency is a scale cue only for a viewer who has been taught it. The prior
industry supplies a better one, because it built to a module:

> **The industry built on a 1.2 m module.** Timber sets at 1.2 m, roof bolts at 1.2 m, rail
> gauge 0.6 m, drives 2.4 × 2.4 m, shot holes at 340 mm in 1.6 m rounds with each round's
> pattern phase-offset from the last, so you can count how many blasts made the passage.

Every worked surface then carries a ruler, and a passage's size is legible with no agent in
frame. And the anchor a viewer learns in one shot and never forgets:

> **The agent fits between the rails.** A Surveyor is 0.21 m wide, a Hauler 0.32 m, in a
> 0.60 m gauge.

This is carved geometry and surface marks — exactly what a procedural generator is best at
— and it is the difference between a cave system and *a place worth robbing*.

### 3.4 Form, by how much the industry touched it

Three registers; the generator interpolates on `worked`.

- **Natural.** CA blobs, rounded, no flat surface, no straight line, floor of breakdown and
  clay. Anything straight in a natural passage is a bug.
- **Worked — the horseshoe drive.** 2.4 m wide × 2.4 m high, vertical legs to 1.2 m and a
  semicircular arch above; flat trammed floor; a 300 × 90 mm drainage gutter down one side;
  shot-hole scars parallel to the direction of advance; rail on sleepers at 600 mm; timber-set
  sockets at 1.2 m; a bolt line at the springing.
- **Machine ground.** Stopes, the scour, bolt rings, the Bus conductor overhead, launders,
  collapsed sets, pump chambers with the pumps still under water.

### 3.5 The eight axes, each with one visual rule

| axis | what changes | what must **not** change |
|---|---|---|
| **flooding** | a **waterline** and everything one does: a **0.12 m mineral tide-mark crust** above it (albedo ×1.7, matte — one detail that says *the water moved*); below it albedo ×0.6, roughness 0.10, drips; the surface IOR 1.33, roughness 0.02, **a mirror at grazing angle** — which is exactly why `BLD-85` has lidar return it as a wall | not a blue tint. `WATER #16202E` is cool because water is cool, not because flooding is a colour |
| **passage width** | proportion, read against the 1.2 m module and the rail gauge. A crawl is where a Hauler's 0.32 m stops | never a fog or brightness change |
| **rock type** | roughness, fracture frequency, bedding contrast | **never a hue** |
| **sediment** | volumetric only, per-cell, 0.008 → 0.15 | not a surface effect |
| **magnetic character** | **nothing, ever.** If noisy rock glows, the magnetometer is redundant and the false-find mechanic dies. At most a *geological* tell present in noisy rock **and** in real deposits — a suggestion, never a confirmation | anything legible |
| **structural integrity** | geometry: fresh spall on the floor, open joints in the back, a fracture set that runs, **one timber set failed while its neighbours stand.** Static, so it is learnable *before* the sensor speaks | not a warning colour |
| **depth** | §7 | not altitude |
| **thermal layering** | the **cause, never the effect**: a 0.3 m haze band at the layer height that a beam flares crossing; condensation on the wall above it and not below; a thermocline shimmer in flooded sections | never draw the shadow zone. Draw the layer; let the player infer |

### 3.6 At ten metres, and at a hundred

**There is no hundred metres.** Measured on the real 200 × 120 grid
(`docs/art/probes/sightlines.py`, reproduced this pass):

```
sightline length, all directions from 900 random open cells
  p50    6.0 cells   3.6 m
  p90   19.0 cells  11.4 m
  p99   41.0 cells  24.6 m
  p100  83.0 cells  49.8 m      <- the longest sightline anywhere in the cave
under 20 cells (12 m): 90.8% of all directions
```

**Median sightline is 3.6 m and the longest view in the entire cave is 49.8 m.** The
hundred-metre register does not exist in the rendered world — only as 156 m of graph depth.
So:

> **The wide shot in Blindside is a schematic. The close shot is a photograph. There is
> nothing in between.**

That is the split `SPECTATOR-DISPLAY.md` and ROADMAP Phase 5 already describe, arrived at
from geometry rather than from taste. Two rules fall out:

- **Spend no art budget past 15 m.** At 10 m you read the rock — bedding, fracture, sheen,
  shot-hole scallops, a bolt head, rails going away, the machine's own tracks in the mud.
  All the detail budget lives there.
- **The only things ever seen at distance are the four things that emit.** Everything else
  is silhouette and extinction. That is aerial perspective with a physical cause, and it is
  `GLOSSARY`'s definition of a **Contact** drawn: position without identification.

And one level-design consequence, also measured: **no landmark may be required to be visible
across a chamber.** The largest chamber in the cave is 14.4 m across, which is about one
lamp wide.

---

## 4. The agents

Do not redesign the walker. It is good, it is parametric, and it is the project's biggest
art asset. Dress it. Everything below is additive parameters on `params.py`.

### 4.1 Directional wear — real, cheap, and more modest than the earlier passes claimed

Measured: `07_scout_fresh` (wear 0.0) and `01_scout_default` (wear 0.35) differ by
**0.003 mean luminance.** The bottom half of the wear axis does not exist, and wear 1.0
reads as camouflage rather than as history. The cause is in `materials.py:18-64`:
`painted_metal()` is isotropic noise MAX'd with an inverted AO edge term. **There is no
gravity and no direction in it.**

Three masks, two or three nodes each:

| mask | rule | says |
|---|---|---|
| **`mud`** | world-Z, saturated at the feet, gone above the hull seam, toward `(0.055, 0.042, 0.030)`, roughness → 0.18 | *it walked here* |
| **`dust`** | `max(0, N.z)³` toward `(0.30, 0.265, 0.215)` — **the rock's own dust colour**, so a machine wears the cave it has been in | *it has been down a while* |
| **`scuff`** | `max(0, dot(N, +X)) × edge_AO` — paint off leading faces only | *it hit things* |

**The correction, and it is why an earlier prototype of this half-failed.** A previous pass
built these masks, measured 0.62% of frame changed and **0.00% in the bottom third**, and
correctly diagnosed it as a negative result. I confirmed the structural cause:

```
build.py:95-101   painted_metal is bound to exactly two slots: "shell" and "chassis"
build.py:190      tibia   -> "carbon"   (bare_metal)
build.py:191      foot    -> "rubber"
```

**A mud mask living inside `painted_metal` cannot reach the parts that touch mud.** So the
change is two things, not one:

1. add the three masks, and
2. **extend a wear-capable material to the lower leg** — tibia, tibia knuckle, foot, belt
   cover — or the mud mask does nothing where mud actually goes.

Measured: `av_03_wear_current.png` (isotropic, as today) against `av_04_wear_directed.png`
(three masks, extended to the leg materials), same frame, same light, same `wear = 0.35`.
**3.05% of pixels move by more than 0.01 linear, and the distribution is the actual result:**

```
vertical centroid of the change: 0.505   (0.0 = machine's top, 1.0 = its feet)
  upper third : 39.4% of all changed pixels
  middle third: 24.0%
  lower third : 36.6%
```

**The bimodality is the proof, not the centroid.** A mask with no gravity in it changes the
machine uniformly. Three gravity-aware masks should concentrate change at *both* ends and
leave a comparatively clean waist — dust settling on the top surfaces, mud climbing the feet
and tibias. 39 / 24 / 37 is that signature, and a centroid of 0.505 is two effects at
opposite ends rather than no effect.

**Two honest cautions.** The effect is **modest at `wear = 0.35`** — 3% of frame under a
raking inspection light. It is real, and it is the cheapest change available, but the earlier
passes' framing of it as transformative is not supported at this wear level; it needs the
wear axis pushed, or it needs to be read at a distance where the *pattern* rather than the
*contrast* is doing the work. And a third finding, from getting it wrong first: **the leg
material's `bare` colour must stay dark.** A muddy leg is mud *on* black, not paint worn
*through* to bright metal — the first version of this probe used the hull's bare-metal colour
on the legs and made them lighter instead of dirtier.

The masks are also free information the sim already has: `mud` from time in flooded cells,
`dust` from distance travelled, `scuff` from collisions and `JAM_SECONDS`. **A wreck then
arrives carrying a legible history of where it went.**

New on `Skin`: `mud`, `dust`, `scuff`, `wet` — floats, defaults 0.30 / 0.25 / 0.20 / 0.0.

### 4.2 Damage is state; wear is history; they must never share a channel

Three hard separations:

1. **Wear is history, damage is state.** Paint wear never uses `HURT`/`KILL`; damage never
   uses the wear mask. A `salvage` machine at wear 0.85 must read as a veteran, not a
   casualty — which is exactly what `08_wreck_salvage.png` gets wrong today.
2. **`HURT #E06F60` for hurt-and-alive, `KILL #FF3B30` for dying, and no second red anywhere
   in the world.** No red warning strips, no red status LEDs, no red-hot metal. The 8 mm
   painted E-stop is fine — every real machine has one — provided it is never emissive.
3. **Damage must read at nine pixels.** Losing emissive elements does. A dent does not.

`THE-MACHINERY.md` §4.1 is precise about what arrives: a ground-borne shock that *"shakes
the machine hard enough to break the parts of it that are precise."* So damage shows as
**the sensors failing, not the body denting**:

| damage | what changes | expressible today? |
|---|---|---|
| 0.20 | the sonar bar loses elements — 7 lit, then 4, then 2. Countable, and it names the module that broke | needs a per-element emissive index |
| 0.30 | one hip actuator sheds its cover; the gait acquires a hitch | `motion.py` already has per-leg timing |
| 0.50 | a hull panel is simply not built; the graphite underneath is already a material | needs `shed: list[str]` |
| 0.75 | the head stops tracking and jitters, the boom hangs, **ride height drops 25%** | ride height is already a `ChassisSpec` field |
| 1.00 | the wreck (§6.2) | — |

**Losing ride height is the cheapest damage read there is**, and the whole IK already
follows that one number.

**`damage` is the one parameter allowed to touch geometry**, and that exception must be
written down explicitly, because `Skin` is denied it. The reason is that damage is *truth* —
it is information about the machine's actual state, which is what the honest-silhouette rule
exists to protect — whereas livery is not.

### 4.3 Team identity is value and rhythm, not hue

This is the measurement that most changed my mind, and it was produced by a pass that
overturned its own earlier assertion to get it. Rendered player and rival separate at
**ΔE76 ≈ 1.2 at nine pixels and ΔE76 ≈ 1.2 at ninety** — below the ~2.3 just-noticeable
difference at *every* size. Team identity currently never works at all. Two causes, both
fixable:

- **`render.lights()`'s 14.5 : 1 cold-rim-to-warm-key ratio** lands every machine at
  a\* −1.7 to −3.2 — the same blue-grey, whatever colour it is painted.
- **Emission strength 8 clips every team colour to white through AgX.** Cyan and amber both
  arrive as the same white dot.

Three rules:

1. **Player `BONE #F2E6D2`, rival `EMBER #FF7A2F`.** Already true in `palette.py` and in the
   renders; make it a rule so both registers agree.
2. **Identity-bearing emissives to strength ≤ 3 at ≥ 4× area.** The flank strip goes from
   `0.32L × 4 mm` to about `0.32L × 16 mm`. **Area over intensity** — the same rule
   `SPECTATOR-DISPLAY` §6.3 already applies to the diagram: *make the mark bigger, not
   brighter.*
3. **Invert the value, which is the only channel that survives at all.** Player = pale shell
   over graphite chassis; rival = graphite shell over pale chassis.

**Measured, and the result is narrower than "invert the value and it works":**

| scheme | 9 px | 24 px | 90 px | 300 px |
|---|---|---|---|---|
| **value inversion** | **2.3** | **2.8** | **3.0** | **3.0** |
| value inversion, dust 0.50 → 0.12 | 2.5 | 3.0 | 3.3 | 3.2 |
| **hue only, as built today** | **0.6** | 0.6 | 0.8 | 0.9 |

Hue alone is a quarter of the JND at every size — that reproduces on a different scene, a
different light rig and a corrected lamp, so it is not an artefact. **The inversion is 3.5–4×
better and is still only just at threshold.** I tested and rejected the obvious culprit: dust
in the rock's own colour settling on the horizontals was a plausible reason for both teams
converging toward the cave, and dropping it moves ΔE by 0.2–0.3. Dust is not the limiter.

The limiter is partly the metric: a *mean* colour over the machine mixes shell and chassis
whichever one is pale, so the inversion is nearly invisible to an average even when it is
obvious to an eye. What a mean cannot see is **where** the pale is.

> **So: value is necessary and not sufficient. The rest of the separation has to come from
> layout and rhythm — which parts are pale, and the blink pattern of the emissives — and that
> needs a human A/B rather than another render.** Do not treat team identity as solved by
> item 5 in §10; treat it as a thing to test on a person.

Renders: `av_05_team_player.png` / `av_06_team_rival.png` (inversion), `av_07_team_hue.png`
(today), `av_12/13_team_*_lowdust.png` (the dust control). Numbers and method in
`docs/art/agent/MEASUREMENTS.md`.

### 4.4 The loadout in silhouette, and two modules fail

The honesty is real at hero framing (bare vs loaded differ by 1.86% of frame, unmistakable)
but the honest features are 1–3 px at gameplay range: boom tubes 8–15 mm, beacon tubes
6 mm ⌀, hydrophone bumps 6 mm.

> **Rule: every module owns one silhouette gesture ≥ 0.15 × body length, and one emissive
> state. At range the emissives are the only read.**

| module | gesture | emissive state | verdict |
|---|---|---|---|
| `active_sonar` | face bar | 7 elements, lit **while pinging, dark while passive** | ✓ — but see the design problem below |
| `optical` | lamp housing | it *is* a light source; reflector goes visibly dark when off | ✓ |
| `magnetometer` | boom, 26% of body length | none | ✓ best read in the game |
| `beacon_rack` | 4 deck tubes | **caps go dark one at a time as beacons drop** | fix — a live inventory readout in the silhouette, nearly free |
| `cargo_bay` | belly slab | **hatch window; 0/1/2 loads = 0/1/2 lit segments** | fix — but see §8 on who may see this |
| `passive_acoustic` | ✗ five 6 mm rubber bumps, invisible past 2 m | **none, ever** | **fails.** Make it a **vane** — a line array standing 0.06 m proud of the flank on two stalks, 0.7 L long. A listening machine should look *wider*. Silent is correct: this is the sensor that must not glow |
| `structural_monitor` | ✗ a deck box and ankle collars nobody can see | one amber pilot, pulsing while hearing rock | **fails.** Give it a **deployable 180 mm geophone spike**, carried on the deck and planted in the floor while monitoring — a silhouette that changes with *state*, not just loadout |

That produces one rule a player learns in a match: **passive sensors are dark, active
sensors emit** — mechanically honest, because `BLD-95` already makes light a line-of-sight
tell.

Measured backlit: `av_08_sil_bare.png` against `av_09_sil_loaded.png` — **0.71% of frame,
against 0.08% for the same pair framed badly** (§2.4), and against 1.86% under the
four-studio-light hero rig that does not exist in a match. So the loadout does read from
its silhouette alone, at less than half the strength a studio rig gives it, and the framing
matters more than the modules do.

### 4.5 The running lights — resolve this before anything else in §4

`build.py:142-144` gives every machine an always-on emissive flank strip plus a tail status
sphere at strength 8. The sim registers no emission for them. `BLD-95` makes light a
line-of-sight tell. `DESIGN.html` says going quiet costs you your senses. **An always-on
lamp on every machine contradicts the central tradeoff**, and all four passes flagged it
independently.

**Recommended answer: the running lights are not lamps, they are retroreflective markings.**
They return light that hits them, and afterglow for a few seconds. A quiet agent is then
genuinely dark *until a rival's lamp finds it*, at which point it lights up like a road
sign. That is a far better mechanic than a permanent tell, it preserves the going-quiet
tradeoff exactly, and it is free in the sim — because *"is it inside someone's lamp cone"*
is a question `BLD-95` has to answer anyway.

**Fallback if rejected:** strip strength 8 → 1.5, delete the status sphere, and register an
emission of 0.1 in the sim so the tell is real and costed.

This is a design question, not an art one, and it is the load-bearing input to §2.4, §4.3
and §6.2. It should be answered first.

### 4.6 Chassis identity at a glance

Measured: only the Hauler is unmistakable. Scout, Surveyor and Swimmer are three pale slabs
on four legs and the read is carried entirely by the loadout. One hull gesture each, no new
systems:

- **Scout — *the head is the machine.*** `head_radius` 0.045 → 0.055, `head_neck` 0.07 →
  0.13, hull height 0.085 → 0.070. Small flat body, big head, long neck: *all sensor, no
  body*, which is honest, because its job is to look.
- **Surveyor — unchanged.** It is the reference, and it is the only chassis in Phase 5, so
  it gets the polish.
- **Hauler — already unmistakable.** Push it toward *truck*: the deck is a flat bed, the
  four `top_*` slots sit in a visible row, the spine rail becomes a real load rail, and the
  hull reads as a frame around a hole.
- **Swimmer — the weakest identity in the project, and the design gives it the most
  distinctive job** (*"useless on dry rock; unmatched below the waterline"*). Proposal: **a
  sealed lozenge that walks on the bottom.** `hull_bevel` 0.07 → 0.16 so it stops being a
  box; a **chine** running the full length, breaking the profile into a top and a bottom the
  way every submersible does; a **ballast band**, a bare-metal cylindrical section 0.3 L at
  mid-body — the one element that says *this displaces water*; `leg_stow` so its rest pose
  folds the legs flat, because a swimmer does not stand; flat plate feet instead of ball
  feet. **No fins, no thrusters.** Keep the walk: a bottom-crawler in a flooded mine is more
  distinctive than another ROV, and it keeps the locomotion honest.

New on `ChassisSpec`: `class_gesture`, `leg_stow`, `chine`, `ballast`. Numbers, not
modelling.

### 4.7 The head slot count disagrees with the design

`DESIGN.html` says 3/6/8 slots; the model builds 4/7/9, because `face` and `eye` are two
slots at the same point. That is why every loaded head reads as a lit bar over a lamp disc —
a good read. **Keep two slots and fix the doc**, before `BLD-71` freezes content IDs: a head
that can carry sonar *or* optics but not both is a better loadout decision than one that
cannot.

---

## 5. The ancient machinery

Follow `THE-MACHINERY.md` §1–2 exactly. What follows is dressing, not redesign.

### 5.1 Scale, at 0.6 m/cell

| part | cells | metres | against a 0.77 m Surveyor |
|---|---|---|---|
| mast, hex, 1.6 across flats | 1.2 → 11.0 | 0.96 × **6.60 m** | **11.6× its standing height** |
| boom at z = 9.0 | 7.0 × 0.9 | **4.20 m** long | 5.5× its length |
| footing, anchor pads | r = 2.6 | **3.12 m** across | the dog stands to the top of the footing hub |
| hammer ring | 2.0 across | **1.20 m** | 1.6× its length |
| bolt ring (old service platform) | r = 3.4 | 4.08 m ⌀ | — |
| lethal contour, on axis | 9.0 | **5.40 m** | seven body lengths |

The fiction's own numbers already work: a 1.2 m hex ring, 100 mm wall, 600 mm deep, in grey
cast iron is about 1.6 t, and it falls 5.04 m — **≈ 81 kJ into the rock**, squarely inside
the range of a real truck-mounted seismic weight drop. Nothing needs inflating.

### 5.2 Three ages of iron, and no paint

This is the whole material idea, and it is the strongest single rule any pass produced:

> **Everything is ruined except the surfaces still in use, and those are polished bright by
> the work itself.**

- **Cast iron, wet, a century in.** `(0.075, 0.038, 0.021)`, roughness 0.86, **metallic 0.0**
  — rusted iron is not a mirror. Mottled on a low-frequency noise, bump on two scales.
  **Never orange rust: orange rust is dry rust.** This is submerged-and-emerged iron —
  near-black, faintly ferrous, matte, scaled. Same warm hue family as the rock. It should not
  read as *metal*; it should read as **a piece of the cave that has corners.**
- **Bearing steel, still working.** The one clean thing on the object: slew ring, hammer
  face, winch drum contact face, the mast track where the pawl bites, chain. Roughness 0.30,
  `(0.52, 0.50, 0.48)`, metallic 1.0. **A viewer reads *it is still running* off the shine on
  the bearing before anything moves**, and it is one AO-inverse mask restricted to the moving
  parts.
- **Graphitised, below the waterline.** Real metallurgy: cast iron underwater loses its iron
  and leaves a soft graphite shell that keeps the shape. Black, non-metallic, velvety,
  roughness 0.98. **Intact in silhouette and dead in surface** is precisely what *"dead iron
  bolted into stone"* means, and it is one material swap on a Z threshold.

`palette.py` has already decided the colour relationship and the world should obey it:
`ASSAYER_MAST/IRON/HAMMER` are `ROCK_LIT × 2.3 / 2.6 / 3.2` — one material at three weights,
drawn in the rock's own colour and **never in `HAZARD`**. Only the *field* is magenta, and
the field is an overlay, not a material. If the 3D client draws the lobe at all, it draws it
as a **decal in the silt on the floor**, not a coloured glow in the air.

**Every part is a casting**, and that is a geometry rule a generator can execute: fillets at
every junction, webs and ribs on every flat plane, 2° draft, a visible mould parting line,
and **raised part numbers and a foundry mark — legible as an index system, unreadable as
language, and with no dates.** That last rule is what keeps this a works and not a temple.

### 5.3 The scour — de-silt it, do not tint it

`THE-MACHINERY.md` §2.1 asks for the floor *"tinted toward HAZARD, alpha 0.10."* A tint is
the only tool a schematic has. A rendered world has material, which is both stronger and
more honest:

> **Within ~9 cells the floor has no fines.** Everything that could be shaken loose has been.
> Bare, angular, freshly-fractured bedrock — albedo up to 0.42, roughness up, fracture
> frequency ×3 — surrounded by a floor of silt and rounded rubble. No dust, no spoil, no
> puddles, **no boundary drawn anywhere.**

A player reads *nothing settles here* and finds out why forty seconds later. The rock is
visibly *newer* than everything around it while the machine is visibly older, and that
inversion is the whole story of the object in one frame. **Display tints the scour; the
world de-silts it.**

### 5.4 The 75-second cycle is a lighting cue nobody has claimed

**Dormant (54 s of 75).** It emits nothing. 6.6 m of black shape resolving out of your own
beam, taller than your beam is wide, lit only by whoever walks up to it. The header tank is
full and the pipe joint drips — **one drip every two seconds onto the anvil is the entire
dormant performance**, and a machine that emits nothing while water runs off it reads as
*finished* rather than menacing, which is what §2.1 demands.

| p | state | light |
|---|---|---|
| 0–54 | listening | nothing |
| 54–57 | **the slew** | nothing. The arm moves; the bearing race is bright metal and catches whatever is present. Horizontal rotation is elevation-invariant, so this is the right tell |
| 57–62 | locked | nothing |
| **62–71** | **the wind, nine clicks** | **a source at the winch head ramping 0 → full in nine discrete one-second steps**, 1900 K → 2400 K. The warning *is* the light, the light *is* the countdown, and the countdown is nine countable steps. **And the tank draws down one ninth per click**, so the countdown is a falling water level as well as a rising hammer |
| 71.0–71.15 | **the fire** | one frame at ~4× the wind's output, 4000 K. **The only white light in the game** |
| 71–75 | lethal | decay over 8 s as the brake cools |

**Two hot points, not one, and this is measured.** A source at the mast head 6.05 m up
raises 20.6% of the frame but only 6.8% of the floor half, and lifts the floor's mean
luminance from 0.0407 to only 0.0442. So the winch head is a **beacon** — visible from the
next chamber, which is its job — and it does not light the ground the agents fight on. Add
a second source at **the anvil block at the mast foot**, at about a third the output, which
is where the friction actually is and which is at the height that lights a floor.

### 5.5 The mast does not do what the doc hopes, in this register

`THE-MACHINERY.md` §2.1 says *"the boom rides above the wall line, so you can see which way
it is pointing from the next chamber."* **That is true of the schematic and false of a
ground-level viewer**, and the distinction is worth writing down rather than treating as an
error. The display uses a `TurntableCamera(elevation=72)`, where 3 cells of extra height is
106 px of screen lift. A machine standing on the floor of a cave with a uniform 4.8 m wall
line sees no such thing. Measured (`docs/art/probes/skyline.py`, reproduced this pass):

```
footing  (ground LOS)  visible from 693 cells = 18.1% of the cave
the boom  z=9          visible from 693 cells = 18.1%
mast top  z=11         visible from 693 cells = 18.1%
cells that can see the MAST but not the machine's body: 0 = 0.0%
by chamber: 1 of 11 (ANC, the machine's own chamber) has line of sight at all
```

**The mast buys exactly zero extra cells of visibility at ground level.** Two consequences,
both constructive:

1. **`blindside-gen` gets a rule: a chamber that holds something worth seeing must be taller
   than the passages that reach it.** That also resolves the separate problem that a 6.6 m
   mast does not fit under a 4.8 m ceiling — the Assayer's chamber needs ≥ 8 m, and giving
   the machinery its own architecture is a free depth cue.
2. **Vertical landmark presence is bought with light, not with geometry**, because light
   goes round corners and a mast does not. That is what §5.4's winch-head beacon is for.

### 5.6 The siblings, each getting a material rather than a palette

- **THE HAULAGE.** The same castings, but *greased*: bearings wet, and **rail heads polished
  mirror-bright by use.** Two bright lines in the floor — the only truly specular thing in
  the cave, returning your own lamp straight back at you along their length. **A landmark
  that survives darkness because it is a mirror**, which solves the no-long-shot problem
  exactly once, for the one object that needs it. It is also the only *moving* light in the
  world besides agents, and sound is faster than sight, so the glow arrives after the noise.
- **THE BUS.** A bare conductor on **glazed white porcelain insulators** — the only clean,
  white, undamaged-looking material in the game, which is how you find it. Its tell is being
  the one clean thing in a wet place. **It should never glow; the water below it should.** A
  live flooded section gets a faint corona and its surface goes from mirror to faintly
  self-lit. Its casualties come back *wrong rather than dead*, so **a beacon left in a live
  sump keeps its pilot light and lies** — a lie that still glows.

---

## 6. What is found

### 6.1 Deposits — a worked face and the muck pile under it

`DESIGN.html` deliberately refuses to name the substance, and that refusal is defensible.
`THE-MACHINERY.md` §7 already answered the *shape* and nobody noticed:

> *"what lies on a chamber floor is broken stock and spoil left where the survey said to dig
> — value is in loose, gatherable piles rather than locked in a wall."*

So a deposit is **a face that was being worked, and the talus at its foot**:

- one wall of the chamber is a **fresh-cut working face**, drill holes still in it, some
  charged and some not;
- a **talus cone** of broken stock at its base, at the angle of repose, spread over
  `DEPOSIT_RADIUS = 12` cells = 7.2 m — which is what a muck pile *is*, and why a heap is
  big and diffuse rather than a point;
- the ore distinguished **only** by being redder, denser, glassier and more specular, and
  only when lit. **You find it by shining a light at it**, which is a thing only `optical`
  does and which gives the module a reason the design does not currently give it;
- the agent visibly **filling its bay** over the 30 s, and what it leaves is **a fresh scar
  on the face and a pile of spoil under it, permanently.** A rival arriving later can see the
  deposit has been worked — a real information channel produced entirely by art.

That answers the brief without naming a substance, ages well, and is one procedural rule: a
flat face, a cone, and an albedo-plus-specular tweak.

### 6.2 Wrecks — the best asset in the game, and it does not exist

`08_wreck_salvage.png` is worn paint on a standing machine. It reads as a veteran, not a
corpse. A wreck must read as (a) a machine like yours, (b) dead, (c) holding something worth
taking, (d) at nine pixels.

- **The pose is the whole read.** Belly on the rock (ride height → 0), rolled so **the
  underside shows** — you never see a working machine's underside, and seeing it is instantly
  wrong. Legs folded under and splayed, at least one **missing below the knee**, one **shed
  shell panel lying separately** — the single clearest mark of *destroyed*, not *parked*.
  Silhouette height drops 0.57 m → ~0.20 m. At nine pixels that is *a flat thing where a tall
  thing should be*, which is exactly what the display's `X` glyph means.
- **Dead is the emissives, and that is the read at range.** Every other machine in the cave
  carries two glowing strips. **A wreck is the only machine-shaped thing that is dark — a
  hole where a light should be.** It is also the strongest argument for retroreflective
  running lights (§4.5): a rival's lamp finding a wreck makes it *appear*, silently, all at
  once.
- **Holding something is visible.** Sprung cargo hatch, ore spilled on the floor beside it.
  *"Worth taking"*, at distance, with no UI, decided before you commit.
- **The recovery handle is the only clean thing on it.** `build.py:227` already models it,
  rubber-coated, on two posts. On a wreck it is the only unbent, unmuddied thing in frame, at
  maximum material contrast against the ruin around it. It is the part designed to survive
  this, it is literally what the next machine grabs, and it says *this machine was built to
  be recovered, and nobody came.* That one detail does more for the fiction than any amount
  of damage modelling.
- **What you are actually stealing is invisible.** The policy is in the computer under the
  hatch. Recovery is a machine standing over a corpse with its head down, doing nothing
  visible, for a long time, while the whole cave can hear it. **Do not put a glowing brain in
  it.**

**This is the one item in the document that a parameter could not express, and I have the
evidence rather than the assertion.** Three attempts:

1. **Ride height only** (`av_11_wreck_ridehonly.png`) — `ride_height` 0.32 → 0.055, emissives
   dead, wear 0.95, mud 1.0. **It reads as crouching, not dead.** A dead quadruped is not a
   standing one lowered: the legs are still evenly spaced in a correct stance with the weight
   plausibly on them.
2. **Rig roll at 62°** (superseded) — read as **flipped and floating.** Past about 45° the
   pose stops meaning *fallen* and starts meaning *upside down*; and nothing in the rig knows
   the hull can rest on the ground, because only the feet have ground contact, so the body
   hovers.
3. **40° roll, body dropped onto the rock by hand, feet placed where a dropped machine's feet
   land, one leg gone below the knee, the compute hatch shed onto the floor beside it**
   (`av_10_wreck.png`). This reads as fallen. It is also visibly hand-posed, which is the
   point.

**Needs in `agent_model`**, and note that the first one is not the float the earlier passes
proposed:

| parameter | why |
|---|---|
| `WreckSpec.collapse: float` driving **body roll *and* a per-leg pose override** | roll alone floats the hull; ride height alone reads as a crouch |
| a **hull ground-contact solve** | so a collapsed body rests on rock instead of hovering above it |
| `WreckSpec.shed: list[str]` | the probe deletes objects after build, which works once and is not a feature |
| `WreckSpec.emissive_scale: float` | currently a global walk over every material's emission node |
| `WreckSpec.spill: int` | there is no cargo geometry to spill |

This is why the wreck is the one line in §10 costed as needing an artist's eye rather than a
number.

### 6.3 Beacons — and the hard rule

The only thing the player *makes*. A 230 × 60 mm cast tube, self-righting on a weighted
base, one small warm pilot at the top, a retroreflective band. `BEACON_RANGE = 6` cells =
3.6 m of usefulness, but a point source is visible far past where it illuminates — call it
20 m. **Legible from further than it works, so a chain reads as a trail of small lights
receding into black, going back the way you came, one of which is lying to you.** That is
the most beautiful image the game has and it costs one emissive.

Two rules:

- **Beacons are `WARM_DIM #7A6650`, not team-coloured.** The display already decided this.
  If colour identified the owner, spoofing would be detectable by colour.
- **A spoofed beacon is pixel-identical to an honest one. No tell. Not a subtle one.**
  `ARCHITECTURE.md`: *"Nothing in the type system distinguishes a lie. That is the point."*
  The renderer must not leak what the types refuse to, and the temptation to add "just a
  slight flicker" will be enormous. The display may go `LIE`-yellow after the fact; the world
  never may.

### 6.4 Discoveries — a discovery has no world object

`DESIGN-PRINCIPLES.md` §1 makes base blocks Minecraft items: added by data, forever, so the
look must be a template that scales to hundreds. `THE-MACHINERY.md` §6 already answers it: a
discovery is *the plant's own control software*, obtained by putting a transducer on the
rock. **A discovery is not an object, it is a transaction.**

So what art must make is three things, none of them a pickup:

- **the station, not the loot** — a piece of plant with a surface worth knocking on: the
  Assayer's footing, a pump house, a junction box on the Bus, a rail switch. All one idea:
  *the prior industry's control surfaces.*
- **the pose** — head down on the rock, still, not turning, for 80 s while broadcasting. §6
  already specifies it and it is the right read. It is also the same gesture as salvaging a
  policy from a wreck: *I am listening to something that is not alive.*
- **the mark that it is spent.** `yields()` returns `None` once taken. **So a spent Assayer
  is a machine that has stopped.** Boom parked on the bearing it last worked, hammer at the
  bottom, tank drained, no glow, ever again. A player who finds a stopped machine knows
  someone beat them to it, from across the chamber, permanently.

**The template that scales to hundreds is therefore a family of prior-industry machines, not
a family of items.** Each new block ships with an ancient system that yields it; ancient
systems are parametric (mast, boom, footing, hammer, cycle, channel of harm) exactly the way
the agent is. §8's two siblings already started the family. The item's own representation
belongs in the policy editor as a block icon — Minecraft items are icons, not world models.

### 6.5 Survey marks — keep the object, refuse the network

An earlier pass proposed 63 self-luminous cast index plates at 4.8 m spacing, measuring a
mean of 8.8 in line of sight from any random open cell and 99.3% of positions seeing at
least one. **Keep the plates and delete the glow**, for a reason that is not an art reason:

A permanent, honest, immovable, unspoofable wayfinding grid is a third **Fix** source
(`GLOSSARY`: *"an external position observation that collapses drift"*) in a game whose
tension is drift and whose only player-made object is a beacon that can lie. It devalues the
beacon, blunts drift, and makes *"further in is where you get lost"* scenically false.

So: **cast plates on the wall at 1.40 m, raised numbers, no emission, readable only with a
lamp on them at close range, and deliberately not a fix source.** They say *this passage was
worked* — which is the `worked` axis and the depth gauge (§7) — and they say nothing about
where you are.

**There is no glowing item on the floor anywhere in this game.** That is a feature.

---

## 7. Depth

`SPECTATOR-DISPLAY.md` §6.7 already rules: *"Depth is drawn as darkness, not as altitude."*
The world consumes the same BFS field and adds six things darkness cannot carry. Measured:
graph distance from the player shaft runs **0 → 262 cells, median 158**, with the eleven
chambers at 0 / 18 / 37 / 39 / 58 / 58 / 63 / 77 / 78 / 92 / 95%.

1. **The cave stops being a cave.** `worked` climbs with depth: shallow is natural karst with
   a bit of rail in it; middle is a cut drive with sets, a gutter and a bolt line; deep is
   machine ground. **Straight lines increase with depth.** The strongest cue and the cheapest
   — a mask on the generator's carve step, not a material.
2. **How much iron is in frame.** Shallow ground has none; deep ground has bolt lines, rails,
   trays, pipework, then machines. This is the gauge a player reads without being taught.
3. **Water.** Wet walls → tide mark → standing water → sump. Deeper is wetter, so deeper has
   *highlights*: a wet cave photographs completely differently. **Depth is where the specular
   is.**
4. **Darkness.** Rock base × `(1 − 0.55 · depth)`, the same field the display uses, and it
   works because deep rock is wet and wet rock is much darker.
5. **The marks get younger.** Shallow survey plates are corroded and half-buried in
   flowstone; the deep ones are clean and sharp, because the mine **worked downward and got
   better as it went** — `THE-MACHINERY.md` §7's own chronology. **The deeper you go, the
   more competent the industry looks**, which is far more unsettling than ruin-gets-worse,
   and it is the same scalar.
6. **The beacon chain thins out.** `BEACON_DROP_EVERY_CELLS = 45`. In shallow ground a viewer
   sees three or four of the player's own beacons in one frame; past the machinery, none, and
   the last one is behind them. *"Past where the beacon chain still holds"* is the design's
   own phrase, and it becomes a thing you can literally see.

And the inversion this game wants, which falls out rather than being imposed: **deeper is
simultaneously darker (more water, no shaft, no daylight) and more lit (more machines, and
machines are the only world light).** The dangerous place is the visible place. That is the
correct feeling for an extraction game, and it is why depth does not collapse into mud.

---

## 8. The spectator problem

**The structural fact, and it is the strongest thing the art has been handed.**
`ARCHITECTURE.md`: `World` is never passed downstream of the sensor layer, and even
`Return::Optical { patch: OccupancyPatch }` returns *geometry*, not a picture. **There is no
photograph anywhere inside the game's information model.** So the beautiful, lit, material
world *is* what was actually there, and the player only ever gets to see it afterwards. That
is not a limitation to work around; it is the emotional structure of the game.

**One rule follows immediately and it should be enforced on every proposal, including the
ones in this document:** any sentence of the form *"and then the agent can see X in the
world"* must be checked against what the sensor actually returns. `Return::Optical` carries
occupancy, not radiance. A thing that is only distinguishable by *glowing* is invisible to a
policy. So glow may carry information to a **spectator** and never to an **agent**, unless
the sensor layer gains a photometric channel — which is a sim change, not an art one.

### 8.1 The rule that separates the layers in three dimensions

The display's rule is *warm and filled is real; cool and sparse is believed*, and it works
because both sides are diagrams. A rendered client has a stronger axis available that
composes with it rather than replacing it:

> **Truth is rendered. Belief is drawn.** Truth is lit, has shadows, has specular, has
> falloff, has depth of field. **Belief is unlit, unshaded, shadowless, falloff-free
> emission.** Nothing in the belief layer is ever touched by a scene light. A viewer
> separates them in one glance, at any camera angle, in any lighting, forever.

### 8.2 What the point cloud should look like

It should look like **a survey, not a fog.**

- **Points are hits, not dots.** Each is a ~40–50 mm **world-space oriented disc, facing back
  along the ray the return came from** — never a camera-facing sprite of fixed angular size.
  A range/bearing return has no normal, but it does have a sensor→hit direction, and using it
  is honest: it encodes *what the sensor saw from where it stood*. Two consequences, both
  free: a bank of returns reads as a **surface** rather than as fuzz, from any angle, with no
  mesh; and a wall mapped twice under drift draws as **two sheets at a slight angle to each
  other** — the doubling artifact made visible as a shape the eye catches.
  *(This resolves a silent disagreement between the earlier passes, one of which specified
  fixed-angular-size screen-facing sprites. The two produce opposite images — a uniform fog
  versus a readable surface — and only one can ship. Phase 5's replay is the screen ROADMAP
  says gets the most polish, so it needs deciding before it is built.)*
- **Two classes and nothing else** — sensed (at its scattered z) and walked (at z = 0).
  `SPECTATOR-DISPLAY` already collapsed four channels to one; do not re-expand.
- **One confidence channel: alpha**, with size as a weak second. No third colour.
- **Age shows, and the map is not re-registered.** An old return is dimmer and stays *where
  it was believed to be at the time*. That is what drift looks like in three dimensions: an
  old corridor and a new corridor for the same passage, 8 cells apart, both drawn, no
  annotation needed.
- **The mapped silhouette becomes a floor decal at z = 0** — a dark-cyan wash where
  `count > 0`, under everything. The only belief element with area, and what makes drift read
  as a *shape* drifting rather than as scatter moving.
- **The cloud is dimmer than the lamp's darkest legible surface** — emission ~0.03–0.06
  linear against a blown near wall. `palette.py`'s `AMBIENT_MAX_LUMINANCE = 0.35` applied to
  the world register.
- **Never smooth it into a mesh.** A mesh is a model, and the machine does not have one.

That last constraint produces the answer to the whole art problem:

> **The darkness is not empty. It is where belief lives.** The rendered world occupies the
> lit tenth of the frame; the believed world occupies the black nine-tenths. They never
> overlap in brightness and they never agree in shape.

**And the height disagreement is preserved, because it is the game.** `SPECTATOR-DISPLAY`
§6.7: the truth side is an 8-cell canyon, the belief side a 2.2-cell scatter, *"its map is a
tracing, not a model."* In 3D, truth is a real cave with a real ceiling and belief is a
~1.3 m fringe of discs at ankle-to-knee height. **The believed cave is a rug on the floor of
the real one.** Say it exactly like that to whoever builds it. The shared datum is z = 0 on
both sides, and nothing on either side is drawn at a z that claims a measurement it does not
have.

### 8.3 Three modes, and truth is the layer that gets turned down

- **Truth only** — the photographic register, full exposure, real scale.
- **Belief only** — the cloud on black. **This is the default live view**, because it is what
  the player is legally allowed to see.
- **Both** — truth at 30–40% exposure, desaturated toward its own rock colours, cloud
  additive over it. Truth becomes the *ground*, belief the *drawing on it*. **Never the
  reverse:** the belief layer must never be dimmed to let truth read, because belief is the
  subject.

`DESIGN.html`'s enter-agent-perception mode is the same rules from inside: first person at
0.5 m eye height, the cloud and a lamp pool and nothing else.

### 8.4 Where the registers agree, and where they must not

**Agree — write these down as shared rules:**

1. Warm/filled is real; cool/sparse is believed.
2. Depth is darkness, not altitude — the same BFS field on both sides.
3. The same two rock anchors: `ROCK` / `ROCK_LIT` on the display, wet stone / dry dust in the
   render.
4. Player is `BONE`, rival is `EMBER`.
5. The machinery is the rock's own colour; only its field is magenta.
6. **Red is lethal and nothing else** — which binds the world too. The Assayer's winch is
   orange at ~1900 K and must stay clearly short of `KILL #FF3B30`.
7. The ambient-luminance ceiling. A lit massif that competes with a bone machine standing on
   it has undone the exercise.

**Must not:**

1. **Cyan is belief. No cyan in the world** — not a team, not a lamp, not an LED.
2. **The 2× glyph exaggeration does not transfer.** The display draws a 2.4-cell glyph over a
   0.6-cell footprint and argues for it at length; it is right for a diagram. **In the world
   things are their real size.**
3. **The invented 8-cell wall extrusion does not transfer.** §6.7 is explicit that it is a
   legibility device over a grid with no vertical dimension. Phase 3 has a real heightfield.
4. **The display's fixed world light does not transfer.** Four compass face brightnesses is a
   *sun*, and it is correct for a diagram that needs to read as solid stone. **The rendered
   world has no sun and must never borrow one.** It gets its solidity from falloff, from
   silt extinction, and from the fact that the light moves with the machine.
5. **Signal colour is overlay vocabulary, not paint.** A diagram can guarantee that green
   means the objective; a rendered world cannot, because a green thing on a wall is just a
   green thing. **The world uses material; accents are for overlays only** — with two
   sanctioned exceptions where the fiction supplies the source: the shaft (naturally cold and
   bright) and the machinery's fire (naturally violent).

---

## 9. What this rules out

Short list, so that a later "while I was in there" has something to fail against.

- **No ambient light, ever, in any costume.** No sky term, no fill, no rim, no bounce card,
  and no phosphorescent mineral. If a pixel is lit, a fixture in the frame or in the fiction
  is lighting it.
- **No world accumulation.** Lit ground goes black when the beam leaves. Memory belongs to
  belief, which is honest about being a memory.
- **No hue axis on anything.** One warm rock family. Rock type, magnetic character, depth,
  structural integrity and biome all change *surface*, never colour.
- **No crystal, no ice, no bioluminescence, no glowing ore.** That is fantasy-cave vocabulary
  and it pulls the world toward hue-swap biomes, which is the exact failure this direction
  exists to prevent.
- **No image texture, UV map or bitmap.** A generated cave cannot be unwrapped.
- **No hand-modelled asset.** If a proposal cannot be expressed as a parameter, a node graph
  or generator geometry, it does not ship. (Flowstone in named places on the Assayer was cut
  for exactly this reason: it is a displacement shader driven by a downward-flow and curvature
  mask, or it is nothing.)
- **No visual for magnetic character.** If noisy rock is legible, the magnetometer is
  redundant and the false-find mechanic dies.
- **No tell on a spoofed beacon.** Not a flicker, not a hue shift, not a subtle one.
- **No second red.** No red strips, no red LEDs, no red-hot metal. `KILL` and `HURT` only.
- **No cyan anywhere in the world.**
- **No long shot.** Nothing may be required to be visible across a chamber, and no art budget
  is spent past 15 m.
- **No permanent honest wayfinding grid.** Nothing in the world may act as a third Fix source
  and compete with the beacon.
- **No glowing item on the floor.** Deposits are worked faces, discoveries are transactions,
  wrecks are dark.
- **No world-readable inventory in the live player view** (§8's rule): glowing cargo segments
  and emptying beacon caps are spectator/replay vocabulary, because `Return::Optical` carries
  occupancy and not radiance.

---

## 10. What it costs — the first pass, in days

Phase 5's own scope is *"one cave biome, Surveyor chassis only"*, so the first pass is one
rock material, one chassis, one machine, four found objects. Ordered the way `CLAUDE.md`
orders phases: by how much damage a wrong answer does, weighted by uncertainty.

| # | work | days | why here |
|---|---|---|---|
| 1 | **Fix `build.py:312`** — one character | **0.05** | Every dark render in the repo is graded against a broken rig until this lands. Nothing below is measurable first |
| 2 | **The light economy and the luminance contract** — world background to 0, delete the studio lights from match scenes, the four sources, exposure targets, the CI assertion using *linearised* luminance | 2 | Unmeasurable without it; every asset built before it is graded against the wrong exposure |
| 3 | **The lamp** — white, both teams, tilted 8–10° down, ratios re-derived after item 1; the beam-in-silt volumetric | 1 | Changes every render in the repo |
| 4 | **The three directional wear masks**, *and* extending a wear-capable material to the lower leg | 2 | Nine nodes plus the material binding that makes them work. Measured at 3% of frame with the right bimodal distribution — real and cheap, not transformative |
| 5 | **Team identity** — emissives to strength ≤ 3 at ≥ 4× area, the value inversion, kill the cyan and the salvage red | 1 | Hue is measured at a quarter of the JND; the inversion is 3.5–4× better and still at threshold. **Budget an afternoon of human A/B on layout and rhythm after this lands** — the render metric cannot score it |
| 6 | **One rock material, four scalars, world-space triplanar** | 4 | It is the entire cave. Item: fix `materials.py:141` first |
| 7 | **The worked-passage geometry** — horseshoe profile, shot-hole rounds, gutter, rail at 600 mm, sets and bolts at 1.2 m, plates at 4.8 m | 4 | Where "a place worth robbing" gets built, and it is all carved geometry |
| 8 | **The wreck** — `WreckSpec` with roll *and* per-leg pose, a hull ground-contact solve, `shed`, dead emissives, spilled cargo, the clean handle | 4 | Highest narrative value on the list, and **the only item here that needs an artist's eye rather than a number** — measured: ride height alone reads as crouching, roll alone floats (§6.2) |
| 9 | **The Assayer, dressed** — three ages of iron, the nine-click ramp, two hot points, the de-silted scour | 4 | The geometry is already fully specified in cells; this is material and cycle |
| 10 | **The point cloud as oriented discs** + the floor silhouette + the two-layer replay composition | 3 | ROADMAP says this screen gets the most polish |
| 11 | **Depth as one BFS field with six consumers** | 2 | |
| 12 | Module silhouette fixes — `passive_acoustic` vane, `structural_monitor` spike, beacon caps, cargo fill | 3 | |
| 13 | Damage rungs and the `damage` geometry exception | 2 | |
| 14 | Chassis gestures (Swimmer first — it has none) | 2 | Phase 5 is Surveyor-only; this is Phase 6 |

**What ships in the first week:** items 1, 3, 4 and 5 — about four days — and they change
every existing image in the project. That is the honest first pass, and item 1 is four
minutes of it.

**What needs no building at all:** any hand-authored asset. The cave is a shader, the agents
are parameters, the machinery is a spec in cells, and the found objects are poses and
emissive states.

---

## 11. The single riskiest assumption

Not metres-per-cell — that is merely unstated, and it is one number. Not the lighting model
— that is now measured.

> **That a player will accept a frame that is 85–95% true black for six to ten minutes, and
> that the belief overlay is enough company in the dark.**

Everything above is downstream of it. The failure mode is not darkness, it is **fatigue**,
and screenshots will not catch it: `av_02_lamp_fixed.png` is a good image and a good image
is two seconds, not eight minutes.

**There is real evidence on both sides and it should be read before this is decided.**
Phase 1's gate playtest failed, and it failed on exactly this axis — a non-engineer watching
eight minutes said *"it was hard to understand"*, *"all that changes is things kinda beep and
nothing really is obvious"*, and disengaged in the middle. That was a *bright schematic*, so
it is not evidence that darkness causes the problem — but it is evidence that this game's
legibility budget is already spent, and a direction that removes 90% of the frame is
spending a budget that was measured to be overdrawn. Her own suggested fix was *"it would be
easier to understand in 3D vs the 2D demo"*, which makes this register the thing the designer
is already hoping will rescue comprehension. **A dark 3D client is being asked to fix a
comprehension failure by showing less.** That is the risk, stated as plainly as I can.

**How to kill it cheaply, and it should run before item 6 on the cost list.** It is testable
in Phase 1 with no 3D client: render sixty seconds of the seed-7 route under this light
economy — a walk down a passage, a chamber, the machinery through a full 75-second cycle —
with no HUD, **encode it to h264** (because `SPECTATOR-DISPLAY` already records that small
dark grey does not survive an encode, so the histogram must be measured *after* encoding,
not before), and show it to somebody who has never seen the game. Two questions:

1. *Where is the machine and what is it standing on?* If they cannot answer in two seconds,
   the exposure is wrong and it is a two-number fix.
2. *After a minute, do you want the lights on?* If yes, the light economy needs a second
   persistent world source.

**And unlike the passes this document is assembled from, there is a fallback, which is why
§2.8 exists.** If question 2 comes back yes, the residual lighting circuit is the answer —
it is already derived from a claim the fiction has made, it costs two meshes and a point
light, and it buys the Bus tell and the worked-ground depth gauge on the way past. It should
be ruled on then, on evidence, rather than bought now on an argument.

---

## Probes, and how to re-run them

Everything new this pass is under `docs/art/agent/`. It writes nothing outside that
directory and does not modify `agent_model`.

| file | what |
|---|---|
| `av_probe.py` | ten shots. Lit only by sources the fiction supplies; world background 0; re-aims the head lamp at runtime in `_fix_lamp()` |
| `av_batch.sh` | renders all ten at 960 × 600, 40 samples, Cycles CPU |
| `av_measure.py` | exposure histograms (sRGB **linearised**, the `palette.py` convention) and team separation in CIELAB at 9 / 24 / 90 / 300 px |
| `MEASUREMENTS.md` | the numbers those two produced, and what they mean |

```
blender -b -P docs/art/agent/av_probe.py -- --shot lamp_fixed --out <abs path>.png
.venv/Scripts/python.exe docs/art/agent/av_measure.py
```

Renders, and the claim each one carries:

| render | claim |
|---|---|
| `av_01_lamp_asbuilt.png` | §0 — the lamp fires into its own eye lens. 0.36% legible |
| `av_02_lamp_fixed.png` | §0, §2.3, §2.4 — same power, one character, a picture. 4.36% legible, 93.5% black; **a target frame** |
| `av_03_wear_current.png` | §4.1 — isotropic wear, as `materials.py` builds it today |
| `av_04_wear_directed.png` | §4.1 — three gravity masks, extended to the lower-leg materials |
| `av_05_team_player.png` | §4.3 — pale shell over graphite chassis |
| `av_06_team_rival.png` | §4.3 — the value inversion |
| `av_07_team_hue.png` | §4.3 — today's scheme: identity by emissive hue at strength 8 |
| `av_12/13_team_*_lowdust.png` | §4.3 — the dust control, which ruled out the obvious explanation |
| `av_08_sil_bare.png` | §4.4 — the backlit silhouette, bare. **A target frame** |
| `av_09_sil_loaded.png` | §4.4 — the backlit silhouette is the loadout readout. **A target frame** |
| `av_11_wreck_ridehonly.png` | §6.2 — ride height alone: reads as crouching, not dead |
| `av_10_wreck.png` | §6.2 — roll, per-leg pose, shed panel, one leg gone, dead emissives |

**Only `av_02`, `av_08` and `av_09` are target frames for the world's look.** The wear and
team frames are instrument readings, lit with a raking area light or a close 420 W world
source so that the *material* is what is being judged rather than the exposure. Do not treat
them as a reference for how the game looks.

**Reproduced from the earlier passes rather than inherited** (`docs/art/probes/`):
`sightlines.py` (median sightline 3.6 m, longest 49.8 m, world sources reach 36.1%),
`skyline.py` (the mast buys 0 cells), and a BFS over `phase1/truth/cave.py` for depth and
flooding.

### What could not be rendered, and what `agent_model` would need

| claim | why not | parameter needed |
|---|---|---|
| the mud mask reaching the feet | `painted_metal` is bound only to `shell`/`chassis`; tibia is `carbon`, foot is `rubber`. The probe reassigns them by hand to prove the read | a wear-capable material bound to the lower leg, plus `mud`/`dust`/`scuff` on `Skin` |
| a wreck's collapsed pose | ride height is a `ChassisSpec` field the probe mutates globally; the roll and per-leg pose are hand-placed; shed parts are deleted after build. **Two attempts failed before one worked** — see §6.2 | `WreckSpec`: `collapse` driving roll *and* per-leg pose, a hull ground-contact solve, `shed`, `emissive_scale`, `spill` |
| team identity actually separating | measurable to ΔE 3.0, which is at threshold. The remaining channel is *layout and rhythm*, which a mean-colour metric cannot score | nothing in `agent_model` — it needs a human A/B |
| damage rungs 0.2–0.75 | there is no `damage` parameter and no per-element emissive index on the sonar bar | `damage: float` on `AgentConfig`, and the sonar bar as an indexable strip |
| module state (beacon count, cargo fill, sonar pulsing) | modules are static geometry with no state input | a per-module `state: float` consumed by the emissive |
| chassis gestures, the Swimmer's chine and ballast | no hull-gesture parameters exist | `class_gesture`, `chine`, `ballast`, `leg_stow` on `ChassisSpec` |
| retroreflective running lights | Cycles can render this, but it needs a real second light to react to, which is a scene question rather than a model one | nothing in `agent_model`; a material swap from emission to a retroreflective BSDF |

---

## Things I guessed

- **0.6 m per cell.** Inherited from the earlier passes and **stated nowhere in the repo** —
  I checked (`m/cell`, `cell_size`, `CELL_METRES` all absent from `docs/` and `phase1/`).
  `AGENT_RADIUS = 0.6` is a collision radius in cells, not a scale statement. Every scale
  number in §3, §5 and §6 is downstream of this. At 1.0 m/cell the existing agent model is
  about 36% too small.
- **The lamp's 8–10° downward tilt**, and the ratios in §2.2. Derived from a 0.01 legibility
  floor at albedo 0.30, re-derived after the aim fix, but not validated in a real cave mesh.
- **Rock albedo 0.30** as the light-end anchor. `wet_rock` currently ramps 0.015 → 0.11 (wet
  black basalt); this is a dust-covered dolomite. Both are physically real; I picked the
  brighter because the mine is dusty, and because below ~0.25 the bounce budget collapses and
  the machine is never lit by its own lamp.
- **The 1.2 m industrial module**, 600 mm rail gauge, 2.4 × 2.4 m drive, 340 mm shot-hole
  spacing, 1.6 m rounds. Chosen to be legible against a 0.77 m agent, not from a source.
- **The Assayer emits light only while winching and at the strike.** `THE-MACHINERY.md`
  describes a winch under load but never says it glows. The anvil-block second source is my
  addition, forced by the measurement in §5.4.
- **The Assayer's chamber needs a ceiling ≥ 8 m.** Follows from a 6.6 m mast against a 4.8 m
  wall line, but it is a generator requirement nobody has agreed to.
- **Cast iron rather than steel**, graphitisation below the waterline, and the
  "one-to-four-centuries and you cannot tell which" age rule.
- Every colour hex here that is not already in `palette.py`.

## Needs a designer decision

Ordered by how much they block.

1. **Do the running lights emit?** (§4.5) This is above metres-per-cell, because it decides
   whether a quiet loadout is renderable at all, and it is the load-bearing input to §2.4,
   §4.3 and §6.2. My answer: retroreflective, not emissive.
2. **Metres per cell.** (§ everywhere) Blocks every scale number in the document.
3. **Is the residual lighting circuit canon?** (§2.8, §11) Not needed for legibility any
   more. Needed as the fallback if §11's kill test fails. Rule on it *after* the test, not
   before.
4. **What shape is a deposit?** (§6.1) A worked face plus the muck pile under it. Needs a yes
   or a different answer; the art cannot start without the shape even though the substance is
   deliberately unnamed.
5. **Is a discovery an object at all?** (§6.4) I say no — it is a transaction, and the mark
   is a *stopped machine*. That decides the content template for every future block.
6. **`face` + `eye`: one head slot or two?** (§4.7) Fixes the 3/6/8 vs built 4/7/9 mismatch
   before `BLD-71` freezes content IDs.
7. **May `damage` touch geometry when `Skin` may not?** (§4.2) I say yes, and the reason is
   that damage is truth rather than livery.

## Design problems found, not art problems

Per `CLAUDE.md`: these are things the design does not survive, said plainly rather than built
around.

1. **The running lights contradict the central tradeoff.** Every machine carries an always-on
   emissive; the sim registers no emission; `BLD-95` makes light a line-of-sight tell; and
   `DESIGN.html` says going quiet costs you your senses. Four independent passes reached this
   conclusion. It is item 1 above.
2. **The active sonar bar is lit continuously.** *Do I ping?* is stated to be the central
   decision of a match, and the model asserts the opposite by having the transducer glowing
   all the time. One line to change, real design meaning.
3. **`blindside-gen` must make flooding rise monotonically with depth.** `THE-MACHINERY.md`
   §7 says *"the deepest ground is the wettest"*, and the whole deep-is-wet-is-dark-is-specular
   chain in §3, §5 and §7 rests on it. Measured on the Phase 1 cave, flooding by depth
   quartile is **0.0% / 17.1% / 30.8% / 0.0%** — the deepest quarter is bone dry. **This is
   not a bug**: `phase1/truth/cave.py` is a hand-authored dict of eleven chambers in a phase
   `CLAUDE.md` declares throwaway, and there is no generator yet to have a bug in. It is a
   requirement to carry into `blindside-gen`, and the art cannot fix it from outside.
4. **`blindside-gen` must make chambers taller than the passages that reach them.** (§5.5)
   Otherwise a 6.6 m mast does not fit under a 4.8 m ceiling, and nothing in a chamber is
   visible from outside it.
5. **The Swimmer has no visual identity** while the design gives it the most distinctive job
   of the four chassis. (§4.6)
6. **`THE-MACHINERY.md` §2.1's "you can see which way the boom is pointing from the next
   chamber" is true of the schematic and false of a ground-level viewer.** (§5.5) Since *a
   hazard is identifiable before it fires* is a design requirement, this needs either an
   amendment to the doc or the generator rule in item 4 — and it currently blocks one of the
   four gate questions.
