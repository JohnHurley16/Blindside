# Art direction

What the world looks like when it is rendered properly — Phase 5, Godot, the 3D client.
Not the spectator display: `SPECTATOR-DISPLAY.md` is a diagram of this world and has its
own visual language. §8 says where the two agree and where they must not.

This document is one direction assembled from four independent passes, with the parts that
did not survive measurement removed rather than softened. Where a number is measured, the
probe that measured it is named. Where it is a guess, it is in the guesses list at the end.
`CLAUDE.md` says ask rather than invent: the questions that actually block are in
**Needs a designer decision**, and the one I most want overruled is §11.

**Revised 2026-09-09 for the ice age.** `DESIGN-PRINCIPLES.md` §10 gave the world a period and a
shape: a society coming out of an ice age, living in a snowy valley under massive mountains with a
town built into them, digging into the pre-ice-age civilisation whose machinery is in the caves.
`docs/THE-ICE.md` is the reconciliation that decision asks for and it is this revision's
specification; where it made a recommendation about this file, this revision follows it or says
why not. **Every changed passage is dated and says what it replaces, and the full list is the
changelog at the end.** The world above the collar — which this document previously had almost
nothing to say about, because there was almost nothing above — is **§12**. It is numbered last
rather than placed after the cave because five documents cite this one by section number and
renumbering §4 through §11 would break nineteen references to §2.1 alone.

**Everything here about the cave is a parameter, a node graph, or generator geometry.** That is a
constraint, not a boast: the caves are generated per match, so they cannot be hand-modelled and
cannot be unwrapped. *(Corrected 2026-09-09. It read "Nothing in this document needs a modeller",
which was wrong in one direction and cost a stream of work before the designer caught it.
`DESIGN-PRINCIPLES.md` §5 scopes it: **machines, modules, the ancients' machinery and the
pit-head's fixed structures are authored, modelled assets**, exported and imported rather than
rebuilt in engine, and `agent_model/` is already that model. §9 carries the full ruling.)* The
agents are still parametric on top of an authored rig, and there is still no art team.

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

> **A cold white valley under peaks nobody can reach, and a machine lowered out of it into a
> drowned iron mine that the meltwater started again, photographed below the collar by one lamp
> somebody carried in: cut rock and black castings inside a pool that falls off ninety to one
> across the frame, nine-tenths of every frame true black, and the only bright surfaces down
> there are the ones something is still rubbing.**

**Rewritten 2026-09-09.** It replaces *"A drowned iron mine that never stopped working,
photographed by one lamp somebody carried in: cut rock and black castings inside a three-metre
pool that falls off ninety to one, nine-tenths of every frame true black, and the only bright
surfaces in the world are the ones something is still rubbing."* Four things moved and each is
load-bearing:

- **The valley is in it, and it is in it first**, because the picture the game makes is a descent
  and the sentence should be one. `DESIGN-PRINCIPLES.md` §10: *"monotonous and snowy and pretty."*
  The peaks nobody can reach are §2.1's new alpenglow row — the only warm light in the exterior
  and deliberately out of the player's reach (`THE-ICE.md` §2.7).
- **"never stopped working" → "that the meltwater started again."** `THE-ICE.md` §4 rules that it
  froze, stood in still water for the ice, and resumed when the melt reached it, and §4.4 asked
  this file for *"deliberately the weakest possible edit"* — *"still working"*. I have gone one
  clause further than it recommended and named the meltwater, because the sentence is the only
  place in the document where the water's *provenance* is stated, and *drowned by meltwater,
  restarted by meltwater* is one image rather than two facts. **The ruling itself is PROPOSED and
  not yet the designer's** (`THE-ICE.md` §9 Q1, default yes); if it comes back no, this clause
  reverts to *"that never stopped working"* and nothing else in the sentence moves.
- **"a three-metre pool that falls off ninety to one" → "a pool that falls off ninety to one
  across the frame."** The ninety is real and the three metres was not: measured, a physically
  correct lamp gives **≈ 7 : 1 across three metres** and **≈ 32 : 1 from near floor to far wall**,
  and ninety to one is what you get across 1.6 m → 12 m, which is a frame. See §2.2.
- **"the only bright surfaces in the world" → "down there."** There is now a bright world, and it
  is above. That is a repair the ice forced and the sentence is better for it.

The same sentence as a build contract, which is the form a shader author can start from on
Monday:

1. **Two material families below the collar — rock and ice — four scalars each, world-space
   mapped, no photographic texture anywhere.** Snow is the third, and it is §12.
2. **Six light sources, all diegetic. Below the collar, world background strength zero.** If a
   pixel is lit, name the fixture; above the collar the fixture is the sky and it is allowed to be.
3. **Wear is gravity, not noise.** Mud low, dust on horizontals, scuff on leading edges.
4. **Value carries meaning; hue does not — and where the setting supplies hue, saturation carries
   the rule instead.** One warm rock family. Ice and snow are the exception the setting bought,
   and they are governed by §8.4's saturation line rather than by a hue ban that a blue-white
   world cannot keep. No biome colour.
5. **Everything is ruined except what is still in use, and that is polished bright by the
   work itself** — and under `THE-ICE.md` §4's restart, *in use* means about forty years of it, not fourteen
   hundred. That is why there is a wear surface left to be bright (§5.2).

---

## 2. Light

### 2.1 The economy — six sources, and a seventh that needs a ruling

**Amended 2026-09-09: two rows added, none rewritten.** This is `THE-ICE.md` §2.7's
recommendation taken verbatim, and it is the largest single saving the ice-age decision produced.
The table below previously had four rows and ended at the shaft, and the decision looked at first
like it broke it — a game with a snowy exterior cannot have the shaft as its only daylight.
**The mountains reconcile it instead.** A valley floor in the shadow of an 1,800 m wall has no
direct sun on it at all and is lit by the sky alone, which is a clear-sky north window at the
scale of a landscape — on the order of 12000 K, `(0.60, 0.74, 1.00)`, which is exactly what the
shaft row already said. So nothing here is amended, and the sentence that replaces *"the only cold
light, and the only daylight"* is a better one than it:

> **The valley's light and the shaft's light are the same light, arriving by different routes.**
> The sky lights the floor; the sky lights the collar; the collar lights three metres of shaft and
> then stops. **The shaft is not the only daylight in the game. It is the last of it**, and the
> falloff down the collar is where daylight ends and the lamp economy begins.

That is one continuous physical story from the peaks to the sump, it runs down a single axis
(`THE-ICE.md` §5.4's `datum_mm`, the valley floor, from which the town's height and the cave's
depth are both measured), and it means everything below the collar is unchanged.

| source | who owns it | reach | colour | notes |
|---|---|---|---|---|
| **the work lamp** | any agent with `optical` | floor to ~6 m, walls to ~20 m | **white** `(1.00, 0.98, 0.95)` | 50° cone, tilted **8–10° down** so the pool lands inside the camera frustum |
| **running lights** | every agent | lights nothing past ~1.5 m | team, at **strength ≤ 3** | see §4.5 — these may not be lamps at all |
| **the machinery** | the world | rock legible to ~18 m | 1900 K → 2400 K, 4000 K at the strike | the 75-second cycle, §5.4 |
| **the shaft** | the world, two of them | its own chamber | 12000 K `(0.60, 0.74, 1.00)` | **the last of the daylight**, not the only daylight. See the falloff rule below |
| **the sky** *(new, 2026-09-09)* | the world | the valley floor, and three metres down the shaft | 12000 K `(0.60, 0.74, 1.00)` | the same light as the shaft's. The exterior has **no direct beam on the ground the player stands on** — the sun is on the ridge and the peaks. §12.2 |
| **alpenglow on the peaks** *(new, 2026-09-09)* | the world | nothing. It illuminates no surface the player can touch | ~2,000 K, on snow at 8–15 km | the only warm light in the exterior, present for minutes, and **deliberately unreachable**. It is `DESIGN-PRINCIPLES.md` §4's two-register collision handed over by the landscape rather than invented |
| *(contingency)* **the residual circuit** | the world | its own bay, ~5 m | 2100 K `(1.00, 0.72, 0.42)` | **§2.8. Needs a ruling before anything is modelled against it.** |

**The collar falloff, and it already exists.** `spikes/godot/surface/NOTES.md` §2.2 multiplies
every collar lining ring's instance colour by `1/(1 + (depth/2.2)^2)` — *"the inverse-square a
rectangular sky hole actually delivers. Three metres down it is 35%, at eight metres 7%: the shaft
reads as a hole rather than a lit box."* **That is the rule for where daylight stops**, it is one
line, it is built, and `THE-ICE.md` §5.2 points out that it is also exactly the falloff a shaft of
daylight down a moulin wants. Use it for both.

**World background strength is 0 below the collar.** *(Scope stated 2026-09-09; the sentence
below was written when there was no surface and read as an absolute.)* Above the collar the
illuminant **is** the sky, and a sky term there is a fixture in the fiction rather than light
arriving from infinity through solid rock. §9's first rules-out line carries the same scoping.
`agent_model/render.py:73` currently sets
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
into the client.**

**Corrected 2026-09-09 against measurement.** `spikes/godot/materials/NOTES.md` §5.2 built the
instrument this table always needed — a 30 m aggregate floor with a rock wall down one side, one
lamp on the camera, exposure fixed at 1.0, linearised luminance, reproducible with `-- --expo` —
and **two of the five numbers below were not reachable with a physically correct lamp, and not
reachable together.** The `measured` column is that probe at the shipped `LAMP_ENERGY` of 140 with
inverse-square decay. The table is not softened; the two wrong rows are struck through and
replaced.

| relationship | target | measured |
|---|---|---|
| floor 3 m ahead, grazing | ≈ 0.08 relative luminance (about half mid-grey) | **0.088** ✓ |
| near floor at 1.6 m | **blown, deliberately** | 0.264 ✓ |
| ~~brightest legible : dimmest legible, ≈ 90 : 1 across three metres~~ → **≈ 90 : 1 across the frame**, 1.6 m to 12 m | the frame's dynamic range | **7 : 1** across three metres; **32 : 1** near floor to far wall |
| ~~wall at 8 m ≈ 0.06~~ → **wall at 8 m is the edge of legible, ≈ 0.01–0.02** | the last thing that reads | **0.012** |
| wall at 25 m | black | **< 0.001** ✓ |

**Why the ninety moved rather than being deleted.** A point source is inverse-square: from 1.6 m
to 4.6 m that is 8.3 : 1 before anything else, and adding the cone falloff and the grazing cosine
gets 7–10 : 1 on a floor. *"To reach 90 : 1 across three metres you need falloff of about
d^-4.3, which is not a lamp."* The **ninety is right and the three metres was wrong**: 90 : 1 is
what a frame spans from 1.6 m to 12 m, so the figure was always describing the frame's dynamic
range and this document should have said which. It now does, here and in §1 and §2.3.

**Why the 8 m wall moved.** *"Floor at 3 m = 0.08 and wall at 8 m = 0.06 cannot both hold: they
are a ratio of 1.3 across a distance that inverse-square makes 7.1, even with the wall at normal
incidence and the floor grazing."* One of the two had to move, and it is the one that was never
measured. The **qualitative** claim survives and is the one that matters — 8 m is where the wall
stops reading — and it is now stated at a luminance a lamp can actually produce.

Pick the wattage that hits those on whatever renderer is in front of you, and re-derive it
after the aim fix rather than inheriting a number from a pass that measured a broken lamp.

**Ice does not obey this table, and should not be made to.** *(New 2026-09-09.)* Ice is
translucent: a beam entering it scatters within a few centimetres and the surface glows rather
than returning a hard pool, so an ice passage at the same power is **brighter, softer and flatter**
than a rock one. `THE-ICE.md` §6.1's recommendation is that the ice band gets its own row and a
softer falloff, and that this is a legitimate depth cue rather than a concession — **the shallow
band is the friendly one, and it is the one place in the cave where the darkness relents.** I have
taken it. The table above is a **rock contract**; §3.1's ice family and §2.9's ice band are where
the other one lives.

### 2.3 The falloff is the style, and the near wall is allowed to clip

**Do not compress the ramp.** No exposure compensation, no auto-exposure, no tone curve that
rescues the far end. A 90:1 falloff **across the frame** — 7:1 in the first three metres of it,
§2.2, corrected 2026-09-09 — is the one thing that says *carried light* rather than *lit level*,
and it is precisely the thing ambient cannot fake. Keep AgX with a shoulder; let the near wall
blow.

**And the same discipline is what the exterior needs, which is not obvious.** *(Added
2026-09-09.)* Sunlit snow on a peak against shadowed snow on the valley floor is somewhere in the
region of **thirty to sixty to one inside a single frame** — `THE-ICE.md` §2.7's arithmetic, and
it says so itself: its author's, not measured. That is the same problem this section already
loves, moved outdoors and made twenty times wider, and the answer transfers exactly: **do not
compress the ramp, let the peaks blow, and grade for the floor.** A frame in which the peaks are
correctly exposed is a frame in which the valley is black, and that is the wrong picture. §12.2.

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

**One contract cannot cover a world with a sky in it, and the fix is a second column, not a
looser first one.** *(Added 2026-09-09; `THE-ICE.md` §2.7 recommends it and the surface spike had
already discovered it independently.)* `spikes/godot/surface/CINEMA.md` §8.1 is blunt about what
happens if you try: *"'legible 3–20%' and 'true black ≥ 70%' describe a three-metre pool of
carried light in a black room. A yard under an overcast sky is legible over **55–72%** of frame by
construction… Applying the cave's floor to a daylight frame would fail every correct picture in
this directory."* It asserted only the 3% blown ceiling, and **0 of 27 frames breached it, worst
`t03_yard_drift` at 0.73%**.

So: **the scene declares which band it is in, and CI runs that one.** Three bands, and the
lamp-frame column above is untouched.

| band | `> 0.50` blown | `> 0.18` mid | `> 0.05` legible | `< 0.02` black | status |
|---|---|---|---|---|---|
| **lamp frame** (below the collar, no daylight, no machinery) | ≤ 3% | 1–25% | 3–20% | ≥ 70% | measured, unchanged |
| **ice band** (the shallow cave, §3.1) | ≤ 3% | 1–35% | **10–40%** | **≥ 40%** | **GUESS**, mine. `THE-ICE.md` §6.1 says only that ice will not hit the rock contract and should not be forced to; the numbers are mine and are chosen so the band reads as *relief* without reading as a lit level. **Provisional until an ice material exists to measure** |
| **daylight frame** (above the collar, §12) | **≤ 8%** — the peaks are allowed to be most of it | 25–60% | — | **≤ 12%** | **GUESS**, `THE-ICE.md` §2.7's, and it says so. The measured surface today runs p50 ≈ 0.33 with under 2% dead black on a *yard*, not a snowfield, so these move when snow exists |

**The important part is not the numbers; it is that an artist who lifts a cave frame to surface
levels still fails the build.** And the lamp-frame column is currently tighter than anything built
passes, in *both* directions, which is worth knowing before anybody treats a failure as a defect:
`spikes/godot/cave`'s `lumcheck.py` **passes 9 of 12 frames before and after the photoreal pass,
on different frames each time.** Today's three failures are `01_wide_passage` at **2.96% legible
against a 3.0% floor** — 0.04 points under, and it is the direction the whole pass moved as the
floor albedo came down (§3.1) — `05_two_registers` at **24.98% legible and 56.78% black**, and
`08_waterline` at **68.49% black**. The materials library's `09_falloff_lamp`, the only shot there
shaped like a real frame, lands at **0.6% blown / 29.7% legible / 62.1% true black**: slightly too
legible and not quite black enough, *"which is what you would expect from a 3.2 m wide corridor
with no ceiling and nothing to occlude."*

**Two things that move the bands and are not lighting**, both new and both measured, and they are
the reason the contract needs to say *where* it is measured:

- **The lens is an exposure control.** Same scene, same lamp, no lighting change: 21 mm gives
  5.56% legible, **35 mm gives 9.74%**, 50 mm gives 5.84% — **a 1.75× swing**. The reason is
  physical: the work lamp is a 54° cone, and the lens whose horizontal field matches it is
  **35.3 mm**. Anything wider is looking at rock the lamp is not lighting. **The focal length and
  the lamp cone are one decision, not two.**
- **The vignette can turn a passing frame into a failing one.** It costs about **7% of the frame
  mean and 0.4 points of legible fraction**, and with the full lens stack on, two more cinematic
  frames fall under the 3% floor. So **the contract has to say whether it is measured before or
  after the lens.** My answer, and it is a ruling this section did not previously need: **before.**
  The lens is a shot decision; the light economy is the thing being asserted, and a grade that
  fails a build is a grade nobody will use.

And **daylight arriving down a moulin (§3.7) invalidates the lamp-frame band for every frame it
reaches.** That is a re-measurement, not a relaxation.

### 2.10 Three things this document assumed the engine has, and it does not

**New 2026-09-09.** All three were measured in `spikes/godot/`, all three are cheap to write down
and expensive to discover, and the third one is a rule this document nearly got wrong on principle.

**1. Per-light contact shadows do not exist in Godot 4.** `spikes/godot/cave/PHOTOREAL.md` §2.9:
*"`Light3D` exposes `shadow_enabled`, `shadow_bias`, `shadow_normal_bias`,
`shadow_reverse_cull_face`, `shadow_transmittance_bias`, `shadow_opacity`, `shadow_blur` and
`shadow_caster_mask`, and nothing else; **the Godot 3 feature was removed.**"* The materials spike
found the same thing independently. **So no proposal may rest on them.** What does the job instead,
in order of how much it buys:

- **Offset the lamp from the eye.** The single most useful lighting finding in the spikes, and it
  is one vector: the cave's lamp sat at `(0.10, −0.16, 0)`, *"about 6° off the view axis at 1.5 m.
  That means N·L ≈ N·V for every surface in the frame, and a diffuse surface lit from exactly the
  direction it is seen from has almost no shading contrast: **a 30° bump changes the cosine by
  13%.** No normal map of any quality produces form under that condition."* It is now
  `(0.26, −0.22, 0.10)`. §0 is the same class of finding — a lamp pointing the wrong way — and
  this is its sibling.
- **Bury things.** Every stone sunk a quarter to three-quarters of its own radius, *"its own body
  draws the contact shadow that shadowless instances cannot cast for themselves."*
- **Material AO from the height field, with `AO_LIGHT_AFFECT = 1.0`**, so it darkens *direct*
  light. *"That pairing is what makes a wall read at all under a headlamp."*

The residue is honest and should be stated: *"a stone never casts a shadow on the stone beside
it."* Fixing that properly needs a parallax shadow march along the light vector, and **Godot does
not expose the light direction in `fragment()`**, so it means writing the whole BRDF. A day.

**2. SSAO does nothing in this world, and it is the most expensive thing in the frame.** It only
modulates *ambient*, and §2.1 sets ambient to zero. Measured in the cave: **4.35 ms of an 8.68 ms
GPU frame**, responsible for every 60 ms spike in the walk, for a **0.25% mean absolute pixel
difference**. Cut. (It is a different calculation above the collar, where there is a sky: the
surface spike measures SSAO at **4.2 ms of a 13.7 ms frame — 31%** — and says plainly that it is
*"what stops 84,864 props hovering above the ground"*, and that nobody gets to choose there
because it is measured. §12.4.)

**3. Screen-space reflections were measured and cut, and the reason is the interesting part.** The
first instinct is to ban SSR as ambient in a costume. That is wrong, and the spike argued it
correctly before measuring: *"SSR is not an ambient term in the sense §9 forbids. It has no source
at infinity; it is the reflection of actually lit geometry that is in this frame, and if the frame
goes black the reflection goes black with it. That is categorically different from a sky term,
which invents light where there is none."* **It was cut on cost, not on principle:**

> *"It did not earn its place here, and the honest reason is that **there is nothing to reflect.**
> Under one lamp with zero ambient, nine-tenths of the frame is black, so a mirror returns black.
> The measured difference between the two shots is **0.0049 vs 0.0058 at p90 — under 1%. SSR costs
> about 5 ms and buys almost nothing in this world. Leave it off.**"*

**So the rule is a costing, not a prohibition**, and it should be written that way because it
inverts above the collar: the surface spike ranks SSR its **number one remaining job** — *"a wet
yard that does not reflect the thing standing in it is the largest single remaining tell."* Same
technique, opposite verdict, and the variable is whether there is a lit world to return. **One
exception is already shipping and is correct**: the cave's water shader runs its own
Fresnel-weighted 14-step screen-space reflection, because §3.5's *"a mirror at grazing angle"*
cannot be had any other way and a reflection probe **would** be a light leak.

**And the consequence all three share, which is a design finding rather than an art one.** Both
cave documents and the materials library reach it independently: *"a lamp at the eye is a
photometric problem, not an art problem… **a second source — even §2.8's contingency circuit at its
low end — would do more for photorealism than any shader I could write. This is a design question,
not an art one."*** It is §2.8's ruling and §11's kill test, and three separate measurement passes
now want it. Recorded, not decided.

---

## 3. The cave

**Reframed 2026-09-09.** Everything in this section was written for a horizontal mine: a plan of
passages, one waterline, one material family, and a depth axis that was graph distance from the
shaft rather than a direction you could fall in. `DESIGN-PRINCIPLES.md` §10 replaced that:
*"The cave stops being a flat plan of passages and becomes a place with levels, drops, and things
below other things… going deeper becomes literal."* Three things follow and they are the frame for
everything below.

1. **The cave has a vertical axis, and it is the same axis the town is on.** `THE-ICE.md` §5.4's
   `datum_mm` is the valley floor: the town runs +90 to +520 m from it and the cave runs 0 to
   −250 m, so the game is one section about eight hundred metres long with the shaft in the middle.
   Depth is now a number in metres as well as a BFS band, and §7 carries both.
2. **There are three media, not one, and they interleave by depth.** Ice, rock, and the ancients'
   workings. §3.1 gains a second material family and §3.7 says how they are stacked.
3. **Down is cheap and up is not.** `THE-ICE.md` §5.1: *"A drop is free, fast, and one-way."* That
   is a gameplay consequence rather than an art one, but it decides what the art has to make
   legible — a pitch has to read as a pitch *before* a machine is standing at the lip of it, and
   §6.2's lidar cannot see down (`THE-ICE.md` §6.2). See §3.4.

**What survives untouched, and it is most of the section:** one rock family, world-space mapping,
the 1.2 m module, the scale rule, and every one of the eight axes. The ice is a **setting**, not a
biome, and nothing below turns into a palette swap.

### 3.1 Two material families, four scalars each, no hue axis

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

**Corrected 2026-09-09. The five triples below were about four times too bright, and two agents
found it independently.** They were stated as albedo — they are exactly the linear form of the hex
codes beside them — and `spikes/godot/materials/NOTES.md` §5.1 measured what that means:
*"**0.34 linear is a pale limestone or new plaster.** It is 4× the reflectance of the dark wet
rock the brief asks for and about 5× what an iron mine's walls measure."* And it named the damage:
*"I think it is the direct cause of what the designer was looking at: `spikes/godot/cave/rock.gdshader`
uses ART's numbers verbatim, and `spikes/godot/cave/shots/03_underfoot.png` is a peach-coloured
surface with blown highlights and no shadow in it. **A too-bright albedo is the fastest way to make
a surface look like painted plastic**, because the specular response stops being able to carry any
shape."* `THE-ICE.md` §2.10 lists the same conflict as open and says the ice **forces** the ruling,
because snow and ice are genuinely bright and the rock now has to be settled *against* them rather
than beside them.

**So the numbers below are the measured band, and the hue ratio is kept.** They are the materials
library's, not mine, and they are bands rather than points because a single value is the strongest
tell that a surface was authored rather than weathered.

| what | albedo, linear | was | note |
|---|---|---|---|
| dark rock, wet | **0.030 – 0.095** | 0.340 / 0.190 | the dark-rock band shifted down for a wet iron mine. ART's warm ratio (+22% R / −28% B) kept |
| rock, freshly broken | **0.045 – 0.140** | — | no patina: lighter and greyer than the weathered outside, and **the strongest readable difference between two rocks in the game** |
| rock, long weathered | **0.020 – 0.080** | — | iron patina darkens; the joints have opened and hold shadow |
| tide-mark crust | **0.090 – 0.240** | 0.520 | §3.5's ×1.7 off 0.06 is 0.10; the top of the band is a thick mineral crust. **The rule survives, the anchor moved** |
| silt / fines, dry | **0.070 – 0.175** | — | dry silt measures 0.15–0.25; iron-rich mine fines are darker |
| mud, saturated | **0.010 – 0.055** | — | water in the pores roughly halves it again |
| aggregate / ballast | **0.025 – 0.130** | — | the same rock, but each stone is a different stone: ±34% per voronoi cell |
| **scoured floor** (§5.3) | **0.190, 0.158, 0.122 dry; ×0.54 where soaked** | 0.420 / 0.360 / 0.280 | **the second, independent correction**, and it came from the other spike |

**Two agents found this separately, on different instruments, and that is why it should be taken as
settled.** The materials library measured the whole set with a calibration render — each material's
`ALBEDO` unlit, orthographic, tone mapper LINEAR at exposure 1.0, *"so the value in the PNG is the
number"*, read back and failed if it leaves plausible albedo — and the cave's photoreal pass
arrived at the scoured floor independently: *"That is a lit schematic value and it is far outside
anything measurable off a wet mine floor, which is muck at 0.05–0.12 linear… **This directly
contradicts a written number and needs a ruling.**"* It also reports the consequence in one line —
*"the floor albedo went from the schematic's 0.42 to a measured-plausible 0.19. Lamp energy
4.2 → 5.4"* — which is §2.2's point exactly: the ratios are the contract and the wattage is
derived.

**The two spikes do not fully agree with each other, and that is the open part.** The materials
library's measured `aggregate` mean is **0.0434**; the cave's dry scoured floor is **0.190**. They
are about 4.4× apart, and they are not measuring the same thing — one is a ballast stone, the other
is trammed bedrock the industry scoured clean (§5.3 says the scour has *no fines* and should be
*brighter* than what surrounds it). **Both corrections stand; the gap between them is a real
question about what a mine floor is**, and it is item 8 in **Needs a designer decision**.

**One measured effect that pulls the other way and should stop this reading as a pure darkening.**
The cave's exposure histograms got *more* legible across the set while the floor albedo went down,
and the pass diagnosed why: *"'Legible' going UP across the set while the floor albedo went DOWN is
the wetness field. A wet surface returns a specular lobe where a dry one returned nothing, so more
of the frame now carries information at the same lamp power. That is §2.7's argument — a wet
passage stays findable and a dry one does not — showing up in the histogram."* **§2.7 was right and
it is now measured.**

**The old triples are not deleted, they are demoted**, because one reading of them is still
defensible and somebody has to rule: `materials/NOTES.md` asks whether *"ART's triples were
intended as albedo or as the rendered value under the lamp,"* and notes that as rendered values
they are consistent with §2.2's *"floor 3 m ahead ≈ 0.08"* only at a much lower irradiance than
either spike uses. **My answer is that they were albedo and they were wrong** — the hexes beside
them are their exact sRGB encodings, which is what an albedo statement looks like — and a rendered
value has no business in a material table anyway. It is item 8 in **Needs a designer decision**.

`palette.py`'s `ROCK #15110D` / `ROCK_LIT #3A2E22` are the same pair at the schematic's
weights, and they are **unaffected** — they were always schematic weights rather than reflectances.
Use them as the shared anchor; that is where the two registers agree for free, and the correction
above moves the world side *toward* them rather than away.

**Rock type changes surface, never colour.** This is the single place where "biome = hue
swap" will be reached for, and it must be refused in writing now.

**And there is now a second family, and it is ice.** *(New 2026-09-09.)* `THE-ICE.md` §5.2 puts
ice in the shallow band and as plugs, floor ice and bridges further down, and none in the workings.
It is one shader with its own four scalars, and it is **a material and a place, never a biome**:

| scalar | drives | is really |
|---|---|---|
| `clarity` 0→1 | subsurface radius, the length of the path light takes before it comes back | bubble content. Glacier ice is white because it is full of air; meltwater-refrozen conduit ice is clear |
| `polish` 0→1 | roughness 0.55→0.03, and the normal-incidence specular flash | whether running water shaped it. It is also §3.5's footing axis and §6.2's sensor axis |
| `debris` 0→1 | entrained rock, gravel and silt frozen in — a volume mask, not a surface one | the ice is a *fill*, so it carries what it pushed into. This is the term that keeps ice inside the warm rock family, because what is suspended in it is the cave |
| `depth_of_medium` | the blue | see below |

**The blue is a path-length effect, not a tint, and that is what keeps the no-hue rule honest.**
`THE-ICE.md` §6.1: *"Thin ice is neutral; thick ice is blue because the light travelled far.
Implemented as depth-of-medium rather than as an albedo, it satisfies the no-hue-axis rule
honestly: the material has one colour and the distance is what is doing the work."* Take it as
written. A shader that reaches for a blue albedo has failed the rule; a shader that reaches for an
absorption coefficient has not, and it is the same instrument §5's mine-water absorption
(`0.85, 0.30, 0.18` per metre) already uses to make deep water read blue-green *with no blue
anywhere in the palette*.

**Ice is the only material in the game with a defensible subsurface-scattering term**, which §9's
old ice ban was implicitly forbidding and §9 now permits. Two consequences already noted elsewhere:
it is why an ice passage does not obey §2.2's ratio table, and it is why §2.9 gives the ice band
its own exposure row.

**And a third, which is the strongest argument for ice that nobody has made yet.** The materials
spike found the same failure twice, in two different materials, and stated it as a general law:
*"a wet surface is convincing because it reflects a world. Under one carried lamp with zero
ambient, a pool reflects one hotspot and otherwise reflects black"*, and *"a metal has no diffuse
term at all, so all it can show is a reflection of its surroundings, and its surroundings are
black."* Its verdict on both: *"the resolution is content, not code — put something lit near the
water."* **Ice is the one specular-family material that does not fail this way, because a
subsurface term returns the lamp's own light rather than a reflection of a black room.** An ice
wall lit by a carried lamp glows from inside; a water surface and a bare casting do not. So the
shallow band is not only the friendly band, it is **the one place where the one-lamp economy makes
a material better rather than worse** — and that is worth knowing before anybody proposes a second
light source to rescue the other two.

**Two warnings the same spike attaches, and both apply to ice directly.**

- **Do not build a smooth conduit out of the rock family's primitive.** *"The `lump` test mesh is a
  noise-displaced sphere and at high material frequency it reads as coral or dough rather than as
  broken rock… this material family on a rounded form looks wrong."* A water-polished ice bore is
  precisely a rounded form, and it needs the anisotropic, flow-shaped primitive the library says it
  does not have — *"the fix is a second pattern primitive — anisotropic, directional, flow-shaped —
  which nothing here has."* **That is the one real new shader the ice costs.**
- **Everything in the rock family shares one voronoi and it shows.** *"Rock joints, mud cracks,
  concrete cracks, aggregate stones and rotten-timber cubical rot are all the same cellular
  function at different frequencies, and at a glance they look related in a way real materials of
  those kinds do not."* Ice built from the same function will join that family, which is exactly
  what it must not do — it is the one material that is supposed to look like it came from somewhere
  else.

### 3.2 World-space mapping, and never a UV

`materials.py:141` binds `TexCoord → Object` into both noise nodes of `wet_rock`. On today's
single dome that happens to equal world space. The moment `blindside-gen` chunks a
120 × 72 m cave — which it must — every chunk gets its own origin and the noise breaks at
every seam. **Use `Geometry → Position`, triplanar.** One node, and it must land before the
shader touches a generated cave.

And the harder rule, **restated 2026-09-09 so that its intent survives its letter.** It used to
read: *"there is not one image texture, UV map or bitmap in this repo, and there must never be
one."* The first half is still true — the surface spike reports **zero imported assets** and the
only `Image` anywhere is three code-generated 128 × 128 decal masks. The second half was too wide,
and §9 now carries the amended version with its reason. The rule that actually matters is
unchanged and is the one to enforce:

> **A generated cave cannot be unwrapped. Nothing in this world may depend on a UV layout, and
> nothing may come from a photograph or a painted map.** World-space procedural is not an
> optimisation here, it is the only option — and it is why this direction can ship as numbers and
> node rules rather than as an asset library.

**What that permits and what it still forbids.** Generating a small 3D noise volume at load and
sampling it is *not* a bitmap asset: it is the same procedural function, evaluated once instead of
per fragment, and it reintroduces no art pipeline. `PROCEDURAL-AND-GODOT.md` §4.5 wants it for a
concrete measured reason — triplanar voronoi at `fracture` 3–14 is three sample sets in the
fragment stage and is ALU-heavy — and it is that document's **question 5**, whose recommended
answer is *yes, allowed*. `DESIGN-PRINCIPLES.md` §6 records the same conflict and treats the
intent as binding and the letter as amendable. **The default holds here.** What stays forbidden:
an authored bitmap, a photographic source, a UV unwrap of anything generated, and an asset library.

**Two node-level rules the spikes measured that belong with this one**, because they are what
world-space mapping actually costs if you get it wrong:

- **Gradient noise, not value noise, with rotated octaves.** *"Value noise on an axis-aligned
  lattice puts a visible square check into every mask built on it, and at ~1 m cell size on the
  hardstanding that check was the single most artificial thing in the underfoot frame"*
  (`surface/PHOTOREAL.md`). The cave spike hit the same thing and replaced its RNG with a 3-round
  integer bit-mix for it.
- **Normalise the fbm range.** Four octaves land in about **0.32–0.68**, so every `smoothstep`
  written against 0..1 operates on a third of its intended range: *"masks that should have covered
  15% of the concrete covered none, and albedo variation that should have been 3:1 was 1.3:1. This
  is the single most consequential line in the file."* It costs one clamp-and-scale and it is the
  difference between the four scalars in §3.1 doing anything and doing nothing.

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

**And there is now a second ruler, running the other way.** *(Added 2026-09-09.)* The 1.2 m module
is a horizontal ruler and it does nothing for a drop. A vertical cave needs a vertical one, and
`THE-ICE.md` supplies two that cost nothing:

- **Depth is in metres from the valley floor, and it is the same zero the town is measured from**
  (`datum_mm`, §5.4 there). A player who has stood in the valley has already calibrated it.
- **The collar's own lining is the ruler for the first ten metres of the descent.** The built
  surface lines the top **3 m** of the shaft in iron plate rings at **750 mm** and then goes to
  **2.5 m** rock rings — a change of pitch you can count, at exactly the height where the daylight
  falloff (§2.1) is doing its work. A moulin re-bored through the ancients' own shaft keeps those
  rings where the water could not scour them away (`THE-ICE.md` §5.2), so **the ruler and the
  fiction are the same object.**

**The anchor rule is unchanged and now has a vertical twin:** the agent fits between the rails, and
**a pitch is measured in agents.** A 4 m drop is five Surveyors stacked, and that is legible from
the lip if — and only if — something at the lip has known size. That is what the bolt line, the
collar rings and a rail end sticking out over the void are for.

### 3.4 Form, by how much the industry touched it — and, now, by which way it runs

Three registers; the generator interpolates on `worked`.

- **Natural.** CA blobs, rounded, no flat surface, no straight line, floor of breakdown and
  clay. Anything straight in a natural passage is a bug.
- **Worked — the horseshoe drive.** 2.4 m wide × 2.4 m high, vertical legs to 1.2 m and a
  semicircular arch above; flat trammed floor; a 300 × 90 mm drainage gutter down one side;
  shot-hole scars parallel to the direction of advance; rail on sleepers at 600 mm; timber-set
  sockets at 1.2 m; a bolt line at the springing.
- **Machine ground.** Stopes, the scour, bolt rings, the Bus conductor overhead, launders,
  collapsed sets, pump chambers with the pumps still under water.

**A fourth register, added 2026-09-09, and it is a second profile family rather than a fourth value
of `worked`.** This is the one place in §3 where the ice costs real geometry work, and
`THE-ICE.md` §2.3 found the exact reason: the built cave sweeps a shell profile that is *"a floor,
two legs and a crown"* along a spine, and **a vertical shaft cannot be expressed by that function
at all.** *"A moulin needs a second profile family beside the sweep, not a modification of it."*

- **The pitch — moulin, winze, aven, collar, stope, crevasse.** A bore rather than a passage:
  round or elliptical in section, its axis vertical, its wall shaped by what cut it. **Water-cut
  ice is smooth, round, polished and featureless** — that is the same surface `polish` scalar in
  §3.1, and it is why the sensor loses its grip in one (§3.5, and `THE-ICE.md` §6.2). **Water-cut
  rock keeps its joints** and is scalloped rather than smooth. **A worked shaft is neither**: it is
  a rectangle with iron rings in it, and it is the one pitch that has a ruler on the wall (§3.3).
- **Where the two profiles meet is the most valuable geometry in the cave**, because it is where
  the player commits. A lip. Whether the generator makes it legible from four metres back is a
  gate on the whole vertical axis, and it is not an art rule — §6.2's lidar physically cannot see
  down, so the *lamp* is the only thing that can show it, and the lamp is tilted 8–10° down for
  exactly that reason. **Nothing may be added to make a pitch legible that a machine could not
  sense.** A painted edge line is a lie the world does not get to tell.

### 3.5 The eight axes, each with one visual rule — and a ninth, which is the medium

**Amended 2026-09-09: one row added, one row rescoped.** The added row is `medium`
(`THE-ICE.md` §5.4 note 4 puts it on `Passage` and `Pitch` as a single `u8`-sized enum:
`Rock | Worked | Ice | IceOverRock`). It keys the material, the sensor response, the acoustic cost
and the footing all at once, and it is *"the only new axis the ice needs."* The rescoped row is
**depth**, whose *"not altitude"* was written when there was no altitude.

| axis | what changes | what must **not** change |
|---|---|---|
| **medium** *(new, 2026-09-09)* | which family §3.1 draws: rock, ice, or ice over rock with the rock legible through it. Ice adds translucency, a normal-incidence flash, and entrained debris; it does not add a hue | **never a biome.** Ice is a *place in the depth stack* (§3.7), not a season, not a region type, and not a palette. The rock family underneath it is unchanged, and what is frozen into the ice is the cave's own material |
| **flooding** | a **waterline** and everything one does: a **0.12 m mineral tide-mark crust** above it (albedo ×1.7, matte — one detail that says *the water moved*); below it albedo ×0.6, roughness 0.10, drips; the surface IOR 1.33, roughness 0.02, **a mirror at grazing angle** — which is exactly why `BLD-85` has lidar return it as a wall | not a blue tint. `WATER #16202E` is cool because water is cool, not because flooding is a colour |
| **passage width** | proportion, read against the 1.2 m module and the rail gauge. A crawl is where a Hauler's 0.32 m stops | never a fog or brightness change |
| **rock type** | roughness, fracture frequency, bedding contrast | **never a hue** |
| **sediment** | volumetric only, per-cell, 0.008 → 0.15 | not a surface effect |
| **magnetic character** | **nothing, ever.** If noisy rock glows, the magnetometer is redundant and the false-find mechanic dies. At most a *geological* tell present in noisy rock **and** in real deposits — a suggestion, never a confirmation | anything legible |
| **structural integrity** | geometry: fresh spall on the floor, open joints in the back, a fracture set that runs, **one timber set failed while its neighbours stand.** Static, so it is learnable *before* the sensor speaks | not a warning colour |
| **depth** | §7 | **not altitude *on the display*.** *(Rescoped 2026-09-09.)* `THE-ICE.md` §2.9's replacement, taken as written: *"On the display, depth is drawn as darkness. The display has no vertical axis and must not acquire one; a schematic that tries to show levels shows neither. In the rendered world, depth is altitude, because it is."* §8.4 carries the same scoping |
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

**Three of the numbers above are measured on a cave that no longer exists, and a vertical cave
reverses two of the conclusions.** *(Flagged 2026-09-09; `THE-ICE.md` §2.4 is the source and calls
this out as a warning to whoever re-runs the probes rather than as a correction, because nothing
has re-measured it yet.)*

1. **"There is no hundred metres" is the claim most at risk.** Every number above comes from
   sightlines cast across a *plan*. **A 40 m winze looked down is a single straight line longer
   than anything the cave currently contains**, and it is a line with a light at the top of it.
   Median sightline almost certainly does not move — most of the cave is still passage — but the
   tail does, and the tail is what the art budget was scoped against.
2. **"Spend no art budget past 15 m" survives horizontally and fails vertically.** The rule was
   always *"nothing is far enough away to need a decimated version"*, and
   `PROCEDURAL-AND-GODOT.md` §4.4 turned that into *"visibility ranges replace LOD entirely."*
   **LOD comes back.** The cave spike's own post-photoreal ablation prices it: turning visibility
   ranges off costs **≈ 45 ms (6.16 ms → 51.43 ms)**. The ranges are not insurance any more, they
   are the frame, **and a vertical sightline is exactly what defeats them.**
3. **§5.5's "the mast buys exactly zero extra cells of visibility" partially reverses**, and this
   is the constructive half. It was measured from ground level on a plane. **From a level above
   the Assayer's chamber, looking down into it, a 6.6 m mast with a winch head that emits during
   the wind is exactly the landmark §5.5 said it could not be.** That partially resolves this
   document's own design problem 6, which currently blocks one of the four gate questions. See
   §5.5.

**What does not change: the wide shot is still a schematic and the close shot is still a
photograph.** The vertical axis adds a third thing that is neither — *a light a long way below
you* — and it is a Contact in `GLOSSARY`'s exact sense: position without identification. Draw it
as one. Nothing about a distant light should resolve until you are near it.

### 3.7 The depth stack, and it is three media rather than one cave

**New 2026-09-09**, from `THE-ICE.md` §5.2. **The interleave is the design, not the list**, and
every depth below is that document's own GUESS, chosen to be legible rather than surveyed — *"the
ratios matter more than the numbers: the ice band is thin, the karst is the transition, and most
of the cave is the mine."*

| band | what it looks like | ancients | water | ice |
|---|---|---|---|---|
| **0 — the collar and the fill**, 0 to ~30 m | the valley's own glacial fill and the **dead ice** buried in it. Meltwater conduits cut through it: round, polished, steep and smooth. §3.1's `polish` at 1.0 | none — below their surface works, above their workings | running, seasonally | **most of it.** Ice walls, ice floor, ice ceiling |
| **1 — the karst**, ~30 to ~80 m | bedrock. Natural cave re-cut by meltwater that found the old joints. Shallow: natural karst with a bit of rail in it | first marks. Low item numbers, corroded, half-buried in flowstone **and now also in ice** | running, then ponded | plugs, floor ice, rime near the drafts |
| **2 — the workings**, ~80 to ~250 m | the mine as §3.4 already describes it. Drives, stopes, the Bus, the Haulage, the pump house | all of it | flooded to the tide mark, and rising | none. Below the freezing front, and always was |
| **3 — past the sump**, ~250 m+ | the deepest Assayer, the underwater scour, clear water | the highest numbers | fully submerged | none |

**Two rules that fall out of this and are worth more than the table.**

- **The ice is a *fill*, not a layer.** The glacier pushed into the openings it found, so band 1
  is not *"no ice"* — it is ice where the drafts and the drainage put it. An adit half-choked with
  a plug. **A stope with a floor of clear ice over a muck pile you can see and cannot reach.** A
  winze with an ice bridge over it. That is a placement rule against §3.1's `medium`, not a new
  geometry system, and the middle example is the best single image the ice produces: *value,
  visible, and behind a metre of the thing that is stopping you.*
- **The melt front is a place.** Somewhere in band 1 or the top of band 2 there is a boundary the
  water has not crossed, and past it the mine is dry, cold and silent with a machine standing in
  it that has not fired in fourteen hundred years (`THE-ICE.md` §5.2, §4.2). **Everything above it
  is running and everything below it is not**, so it is a line the world changes character across
  and it is drawn by one number in the plan. Art rule: **no boundary marker of any kind.** Like
  the scour (§5.3), it is legible because of what stops — no drip, no glow, no wind, dry rock
  where wet rock was — and drawing a line on it would be the same mistake as tinting the scour.
  **PROVISIONAL**: this whole depth stack is downstream of `THE-ICE.md` §9 questions 1, 2 and 8,
  none of which the designer has ruled on.

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
  distinctive than another ROV, and it keeps the locomotion honest. **And the ice hands it the job
  it was missing.** *(Added 2026-09-09.)* `THE-ICE.md` §5.6: meltwater is cold, moving and
  **vertical**, and *"a bottom-crawler in a flooded winze is a different animal from one in a
  flooded drive."* Its class does not change and its meaning does. Nothing above needs editing;
  the chassis simply acquired somewhere that is only reachable by it.

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

**The ice age is what makes all three of these survivable, and it is worth knowing which way the
argument runs.** *(Added 2026-09-09.)* `THE-ICE.md` §1.1 uses this section as **evidence for**
§4’s restart ruling rather than treating it as a casualty of it: *"Cold, anoxic, still fresh water
is the best iron-preserving environment that exists on land. A machine that spent 1,150 years
submerged in meltwater at 1-4 °C with no oxygen and no motion comes out graphitised and shaped,
which is exactly the material this section already specifies. **Under “it never stopped” the same
1,150 years are 480 million hammer blows and there is no brake band left.**"* The arithmetic:
under the restart the Assayer has run about **17 million cycles**, one thirty-fifth of what
continuous operation requires. **The bearing steel is bright because it has only been working for
forty years**, and *"a viewer reads it is still running off the shine on the bearing"* is a claim
about a wear surface that fourteen centuries of hammering would have turned into a hole. Nothing in
this section changes; it just acquired its reason.

**Two measured corrections to how the iron is built**, from `spikes/godot/cave/PHOTOREAL.md` §2.7,
because they contradict the numbers a naive reading of the three ages produces:

- **`METALLIC` is 0 or 1.** Cast iron was built at 0.55, *"which is not a material."* The one
  legitimate in-between is the rust transition, and it is a mask.
- **A metal’s albedo is its F0** - **0.56** for iron and steel, **0.91** for aluminium - not a
  diffuse colour. And the consequence caught the pass out: *"a rough bare metal under a co-located
  lamp has no diffuse term and returns almost nothing, so **every unrusted patch of cast iron went
  black.**"* There is now a floor under the corrosion coverage of anything ferrous, *"which is also
  simply true, since nothing ferrous in a drowned mine is bare."* **That is this section’s own rule
  arriving as a shader constraint**, and it is why "never orange rust" needs its companion: never
  *bare* iron either.

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

**Partially reversed 2026-09-09, and this is the constructive half of the vertical cave.** Every
number above was measured *from ground level on a plane*, which was the only cave that existed.
`THE-ICE.md` §2.4: *"From a level **above** the Assayer's chamber, looking down into it, a 6.6 m
mast with a winch head that emits during the wind is exactly the landmark §5.5 said it could not
be."* So:

- **The measurement stands and its scope is now stated.** At ground level, on the same level, the
  mast buys zero cells. That is still true and it is still why item 2 above is right.
- **What reverses is the design problem, not the measurement.** This document's own design problem 6
  — that `THE-MACHINERY.md` §2.1's *"you can see which way the boom is pointing from the next
  chamber"* is true of the schematic and false of a ground-level viewer — **is answered by a level
  above rather than by a chamber beside.** It currently blocks one of the four gate questions, and
  the vertical axis unblocks it for free.
- **Item 1's generator rule survives and gets easier.** A chamber that holds something worth seeing
  must be taller than the passages that reach it; `THE-ICE.md` §5.5 notes that this becomes
  *"trivially satisfiable when the generator thinks in elevations"* rather than being a
  post-condition somebody has to test for.

**And one thing that does not reverse and is worth saying loudly**: a machine standing above the
chamber still cannot *see down* into it, because the sensor's steepest downward beam is −30°
(`DESIGN-PRINCIPLES.md` §8, and `THE-ICE.md` §6.2's arithmetic). **The mast is a landmark for the
spectator and for the lamp, and it is not a landmark for a policy.** That is §8's rule applied to
the one case that most invites breaking it.

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
- **A chain going down a shaft is the same image rotated ninety degrees, and it is better.**
  *(Added 2026-09-09.)* `THE-ICE.md` §1.1 makes the point: a beacon chain descending a pitch is a
  vertical string of small lights receding, and the thing it is receding into is a drop the machine
  chose to make. **Same emissive, same rule, and the trail now reads as commitment rather than as
  distance.** Nothing in the beacon changes.
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

**Amended 2026-09-09: depth is now altitude in the world, and still darkness on the display.**
`SPECTATOR-DISPLAY.md` §6.7's rule was written for a schematic with no vertical dimension, and
`DESIGN-PRINCIPLES.md` §10 gave the cave one. `THE-ICE.md` §2.9's replacement scopes it rather
than deleting it, and I take it as written:

> *"On the display, depth is drawn as darkness. The display has no vertical axis and must not
> acquire one; a schematic that tries to show levels shows neither. **In the rendered world, depth
> is altitude, because it is.**"*

**Two fields, not one, and neither replaces the other.** `depth_band` — BFS graph distance from the
shaft — keeps all seven of its documented consumers, and `depth_mm` — metres below the valley
floor — arrives beside it. `THE-ICE.md` §5.4 note 1 is emphatic that substituting one for the other
*"breaks all seven for one `i32` of convenience"*, and that the generator's post-condition should
be that they **correlate but are not identical**, which is true of real mines and is the reason a
long horizontal drive at depth still reads as deep. The six cues below all run off `depth_band` and
are unchanged; **the seventh runs off `depth_mm` and is new.**

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

7. **The medium changes, and this is the seventh cue and the only one that is not a gradient.**
   *(New 2026-09-09, §3.7.)* Shallow is ice, middle is karst, deep is the workings. That is a
   **stack**, not a ramp: a player crossing from ice to rock knows they have crossed, because the
   light stops being soft (§2.2), the sensor stops dropping out (§8.2), and the floor stops being
   slippery. Where the six cues above are all *"a bit more of the same"*, this one is a door. **The
   melt front is the second door**, and it is deeper, drier and quieter than everything above it.

And the inversion this game wants, which falls out rather than being imposed: **deeper is
simultaneously darker (more water, no shaft, no daylight) and more lit (more machines, and
machines are the only world light).** The dangerous place is the visible place. That is the
correct feeling for an extraction game, and it is why depth does not collapse into mud.

**And the vertical axis adds a second inversion the ice supplies for free**: *(added 2026-09-09)*
**shallow is the bright, forgiving, low-contrast place and it is the one with nothing in it.** The
ice band relents (§2.2), the daylight still reaches part of it (§2.1), and it has no ancients, no
iron and no loot. Everything worth having is in the dark. `DESIGN-PRINCIPLES.md` §2's
*"the cool things are found by depth"* is now legible as a lighting gradient as well as a loot
table, and a player learns *value is where the light stops* without being told.

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

**Rewritten 2026-09-09**, after the designer looked at the first 3D build and said it looked
nothing like the point clouds from self-driving cars, then looked at a real simulated scanning
sensor and said it was far better. The previous text was written against a sparse range/bearing
sensor and specified oriented discs; that mechanism does not survive a scanning sensor, though
most of the intent does. What was measured is in `spikes/godot/cloud/LIDAR.md`.

It should look like **a survey, not a fog.**

- **The cloud has ring structure, and the ring structure is the point.** The sensor is a spinning
  array of emitters at fixed elevations, so returns lie on rings: concentric on the ground, banded
  on a wall, evenly pitched along each ring. Nothing in the presentation may destroy it - not a
  mark large enough to merge adjacent rings at working range, not randomised elevations, not a
  camera-facing sprite of fixed angular size, not additive accumulation. A regular pattern is the
  only thing whose misalignment a human reads instantly, and this is a game about a machine whose
  estimate drifts and then jumps. Measured: at close range two passes' bands interleave and
  visibly fail to line up, so sub-metre drift becomes legible where it previously needed metres.
- **A return is a point.** A hard-edged mark of near-constant screen size, floor about 1.5 px and
  cap about 4 px, opaque and depth-tested. The old 40-50 mm oriented disc was solving the problem
  that a few thousand sparse returns do not add up to a surface; twenty-odd thousand returns per
  revolution add up to a surface on their own. The 45 mm constant is deleted: it is not a length
  that exists, and a real footprint is range x 3 mrad, 3 mm at one metre and 120 mm at forty.
- **The cloud is opaque and depth-tested; a near return occludes a far one.** Belief still owns
  the frame and is drawn over truth at low exposure, but it is drawn as data, not as light. The
  additive treatment the first pass inferred is what made it read as mist.
- **Colour carries exactly one channel at a time** - intensity or height - with ring index as a
  diagnostic mode. The old sensed/walked split was an artefact of a simulation in which most of
  the map was near-field proximity hits; a scanning sensor has no such split. The "no third
  colour" discipline stands; the taxonomy does not.
- **Intensity, not confidence, owns the visible channel.** It is real, it is measured, and it is
  what anyone reading a scan looks at first. Confidence and age ride on brightness.
- **Age shows, and the map is not re-registered.** Unchanged, and doing real work. An old return
  is dimmer and stays where it was believed to be at the time: an old corridor and a new corridor
  for the same passage, both drawn, no annotation needed.
- **A sensor shadow is content.** Every object casts a clean wedge of *no data*, and those voids
  are as characteristic as the points. Nothing may ever be drawn into a sensor shadow - no fill,
  no interpolation, no decal, no smoothing.
- **Beacons, survey plates and the machines' own bands are retroreflective.** They clip the
  intensity channel and blaze from anywhere in range at any incidence, which makes the placed
  things the brightest things in the machine's own view, automatically, with no overlay and no
  art direction. It is physically true and it is the cheapest legibility win in this document.
- **A crop box is part of the vocabulary.** An accumulated cloud of a tunnel cannot be read from
  outside without one.
- **The floor decal is demoted** to an option for the widest replay camera. It was the only belief
  element with area; the ground rings are now a fabric with area of their own.
- **Ice is where the map goes thin, and that is content too.** *(Added 2026-09-09;
  `THE-ICE.md` §6.2, PROPOSED and not yet ruled — it is the material decision
  `THE-SENSOR-AND-SLAM.md` §1 explicitly did not make when it decided water returns a plane.)*
  Near-infrared is strongly absorbed by ice, so a clean ice wall gives **sparse, low-intensity,
  dropout-ridden returns** — not a mirror and not a hole. Wet ice at grazing incidence returns
  nothing and at normal incidence flashes, so **a machine walking a polished conduit sees a bright
  patch straight ahead and almost nothing at the walls: the returns collapse into a narrow forward
  cone.** This needs no new belief signals — returns per sweep and how much of the last sweep came
  back are already published — so **a player learns *the map goes thin here* by watching it
  happen.** It is the same intensity channel this section already gives the visible slot to, doing
  a second job for free.
- **Never smooth it into a mesh.** A mesh is a model, and the machine does not have one.

That last constraint produces the answer to the whole art problem:

> **The darkness is not empty. It is where belief lives.** The rendered world occupies the
> lit tenth of the frame; the believed world occupies the black nine-tenths. They never
> overlap in brightness and they never agree in shape.

And it now has a second, sharper meaning: some of that darkness is darkness the machine *knows
about*, because it is where its own sensor could not see.

**The height disagreement is preserved, because it is the game.** The shared datum is z = 0 on
both sides, and nothing on either side is drawn at a z that claims a measurement it does not have.

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
2. Depth is darkness **on the display**, and altitude in the world — the same BFS field on both
   sides, plus `depth_mm` on the world side only. *(Rescoped 2026-09-09, §7.)*
3. The same two rock anchors: `ROCK` / `ROCK_LIT` on the display, wet stone / dry dust in the
   render.
4. Player is `BONE`, rival is `EMBER`.
5. The machinery is the rock's own colour; only its field is magenta.
6. **Red is lethal and nothing else** — which binds the world too. The Assayer's winch is
   orange at ~1900 K and must stay clearly short of `KILL #FF3B30`.
7. The ambient-luminance ceiling. A lit massif that competes with a bone machine standing on
   it has undone the exercise.

**Must not:**

1. **Cyan is belief. No cyan in the world** — not a team, not a lamp, not an LED. **Restated as a
   saturation rule 2026-09-09, because a blue-white exterior cannot keep a literal no-blue rule and
   should not try.** `THE-ICE.md` §2.6's enforceable version: *"`SENSED #63D6F7` and
   `GHOST #9FE8FF` are **saturated and bright**. Skylit snow is high-value and low-saturation, and
   skylit shadow is low-value. **Nothing in the world may use belief's saturation at belief's
   brightness.**"* And one hard line that survives without any scoping at all: **no emissive in the
   world is ever cyan.** Not a status LED, not a window, not a vehicle light, not a screen seen
   from outside. **The ground may be the colour the sky makes it; nothing may *emit* belief's
   colour.** The reason the collision is survivable at all is that belief and the exterior almost
   never share a frame — belief is drawn underground, and on the surface it appears on a screen in
   the world, which is allowed to be cyan because it is a screen.
2. **The 2× glyph exaggeration does not transfer.** The display draws a 2.4-cell glyph over a
   0.6-cell footprint and argues for it at length; it is right for a diagram. **In the world
   things are their real size.**
3. **The invented 8-cell wall extrusion does not transfer.** §6.7 is explicit that it is a
   legibility device over a grid with no vertical dimension. **Phase 3 has real elevation.**
   *(Last clause replaced 2026-09-09; it read "a real heightfield", and `THE-ICE.md` §5.3 rules
   that out — a heightfield is single-valued in z and cannot hold a passage under a chamber. The
   recommended shape is a small stack of levels, 2–4 deep, each still a heightfield within itself.
   The rule this bullet states is unaffected either way.)*
4. **The display's fixed world light does not transfer.** Four compass face brightnesses is a
   *sun*, and it is correct for a diagram that needs to read as solid stone. **The rendered
   world below the collar has no sun and must never borrow one.** It gets its solidity from
   falloff, from silt extinction, and from the fact that the light moves with the machine.
   *(Scoped 2026-09-09.)* **Above the collar there is a sun and it is on the peaks**, and even
   there it is not on the ground the player is standing on (§2.1, §12.2) — so the display's
   four-face cheat does not transfer to the surface either, for a different reason: the exterior's
   illuminant is a sky, which lights every face, and what separates surfaces there is orientation
   against a *dome*, not against a compass.
5. **Signal colour is overlay vocabulary, not paint.** A diagram can guarantee that green
   means the objective; a rendered world cannot, because a green thing on a wall is just a
   green thing. **The world uses material; accents are for overlays only** — with two
   sanctioned exceptions where the fiction supplies the source: the shaft (naturally cold and
   bright) and the machinery's fire (naturally violent). **A third is added 2026-09-09 and it is
   the same exception as the first: the sky, and the alpenglow it does not reach.** Both are the
   fiction supplying a source, neither is a signal, and neither may ever be used to mean anything.

---

## 9. What this rules out

Short list, so that a later "while I was in there" has something to fail against.

**Seven lines were amended 2026-09-09 and seven were added, and every amendment carries its
reason.** Four of the seven the setting forced, two were already open questions
(`DESIGN-PRINCIPLES.md` §6 records both), and one was simply wrong. **None of them is weakened.** A
rules-out list that cannot survive a setting decision is a list somebody will quietly stop citing,
and a rule that is amended in the open with its intent restated is stronger than one that is
silently ignored. **Where a line has moved, what it used to say is quoted.**

- **No ambient light, ever, in any costume — below the collar.** No sky term, no fill, no rim, no
  bounce card, and no phosphorescent mineral. If a pixel is lit, a fixture in the frame or in the
  fiction is lighting it. **(Scoped 2026-09-09.)** It read as an absolute because there was nothing
  above the collar when it was written. Above it, the sky is the fixture — §2.1's fifth row — and a
  sky term there is not a costume, it is the source. The surface spike is explicit that without it
  *"the shadowed sides of every sample go to true black and the surface reads as a night scene with
  one hard sun, which is not overcast daylight"*, and it keeps ambient **off, hard, in both cave
  conditions.** The line between the two regimes is a physical one and it is drawn at
  `1/(1 + (depth/2.2)²)`, §2.1.
- **No world accumulation.** Lit ground goes black when the beam leaves. Memory belongs to
  belief, which is honest about being a memory. **One exception, and it is above the collar: snow
  records what walked on it** (§12.1). That is not the world remembering light; it is the world
  being deformed, it is truth rather than belief, and it is the single most valuable thing the ice
  age produces.
- **No hue axis on anything.** One warm rock family. Rock type, magnetic character, depth,
  structural integrity and biome all change *surface*, never colour. **PROVISIONAL, and it is the
  one line here I cannot repair on my own authority.** `DESIGN-PRINCIPLES.md` §6 records the
  conflict and leaves it open: *"Real rock varies in hue as well as value, and mineral staining in
  a wet iron mine is strongly coloured. Photorealism and the no-hue rule cannot both hold
  literally."* Both spikes then bent it in the same direction and both said so — mineral staining
  moving chroma by **±3.5%** off one low-frequency noise, iron ochre at `(0.115, 0.052, 0.018)`
  which is *"clearly orange, not a value change"* — and both preserved the intent with the same
  sentence: **hue is a material property keyed to *position*, never an axis, and *"it cannot be
  used as a legend."*** Snow and ice are the third party to that argument (`THE-ICE.md` §2.6) and
  they are governed by §8.4's saturation rule. **Until the designer rules, treat the intent as
  binding and the letter as amendable: one rock family, nothing signals by hue, no biome colour, no
  second hue axis.**
- **No crystal, no bioluminescence, no glowing ore. Ice is a material and a place, never a biome
  and never a hue axis**: it changes surface, translucency and sensor response, and the rock family
  underneath it is unchanged. **Nothing in this world glows because it is cold.** *(Replaced
  2026-09-09. It read "**No crystal, no ice, no bioluminescence, no glowing ore.** That is
  fantasy-cave vocabulary and it pulls the world toward hue-swap biomes, which is the exact failure
  this direction exists to prevent." The replacement is `THE-ICE.md` §2.5's, taken verbatim, and
  its argument is the one that matters: **the reason behind the old rule was to stop the season
  system becoming a palette swap, and ice arriving as a setting rather than as a biome does not
  threaten that.** The rest of the old line is untouched — crystal, bioluminescence and glowing ore
  are still fantasy-cave vocabulary and still banned, and §6.5's "there is no glowing item on the
  floor anywhere in this game" is unaffected.)*
- **No photographic texture, no authored bitmap, and nothing unwrapped.** A generated cave cannot be
  unwrapped, and nothing in this world may depend on a UV layout or come from a photograph or a
  painted map. **Generated noise, including noise baked to a generated texture at load, is not a
  bitmap asset and is allowed.** **(Amended 2026-09-09.)** It read "**No image texture, UV map or
  bitmap.** A generated cave cannot be unwrapped." The first sentence is the intent and it is
  unchanged; the letter forbade the generated noise textures that physically based materials need,
  which is `PROCEDURAL-AND-GODOT.md` **question 5**, recommendation **yes**, unruled, and
  `DESIGN-PRINCIPLES.md` §6 says photorealism *"depends on that default holding."* The cave's
  photoreal pass now depends on it outright — four seamless 64³ noise volumes generated at load
  from the cave seed, **786 KB of VRAM and ~130 ms**, turning a ~700-hash fragment into a ~30–60
  fetch one — and says what happens if the ruling goes the other way: *"If the answer comes back
  no, most of §2 goes with it."* The one UV anywhere is on a printed label, and a label is applied
  to a manufactured part in a factory. **This remains PROVISIONAL until Q5 is ruled on**, and it is
  item 9 in Needs a designer decision.
- **No hand-modelled *generated* content.** The cave is generated per match, so nothing in it may
  be hand-modelled and nothing in it may be unwrapped: if a proposal about the cave cannot be
  expressed as a parameter, a node graph, generator geometry or an instanced kit part, it does not
  ship. (Flowstone in named places on the Assayer was cut for exactly this reason: it is a
  displacement shader driven by a downward-flow and curvature mask, or it is nothing.)
  ***Authored* content is a different thing and this rule never applied to it.**
  **(Scoped 2026-09-09, and this one is a correction rather than a concession.)**
  `DESIGN-PRINCIPLES.md` §5 was
  amended by the designer on this exact point: *"This applies to GENERATED content, not to AUTHORED
  content, and the difference is not subtle… **Machines, modules, the ancients' machinery and the
  pit-head's fixed structures are modelled assets**, and `agent_model/` — a Blender rig with all
  four chassis, their legs, slots, modules, skins and a working gait — is the model. It gets
  exported and imported, not rebuilt in engine. Rebuilding an authored asset procedurally because a
  rule about caves said 'procedural' is a category error, and it cost a stream of work before the
  designer caught it."* **The header of this document says "nothing in this document needs a
  modeller" and that sentence is now wrong in one direction**: nothing in the *cave* needs a
  modeller, and the machines already have one. The intent — that a generated cave cannot be
  unwrapped — is exactly as strong as it was.
- **No visual for magnetic character.** If noisy rock is legible, the magnetometer is
  redundant and the false-find mechanic dies.
- **No tell on a spoofed beacon.** Not a flicker, not a hue shift, not a subtle one.
- **No second red.** No red strips, no red LEDs, no red-hot metal. `KILL` and `HURT` only.
- **No cyan anywhere in the world.**
- **No long shot *horizontally*.** Nothing may be required to be visible across a chamber, and no
  art budget is spent past 15 m of passage. **(Scoped 2026-09-09.)** **A vertical sightline is the
  exception and it is a real one**: a pitch looked down is a straight line longer than anything the
  horizontal cave contains, and `PROCEDURAL-AND-GODOT.md` §4.4's *"visibility ranges replace LOD
  entirely"* is downstream of a number that a winze breaks. Measured: turning visibility ranges off
  costs **≈ 45 ms**, so they are the frame rather than insurance. **LOD comes back for the vertical
  axis and for the exterior**, and §3.6 and §12.5 carry it. The horizontal rule is unchanged.
- **No permanent honest wayfinding grid.** Nothing in the world may act as a third Fix source
  and compete with the beacon.
- **No glowing item on the floor.** Deposits are worked faces, discoveries are transactions,
  wrecks are dark.
- **No world-readable inventory in the live player view** (§8's rule): glowing cargo segments
  and emptying beacon caps are spectator/replay vocabulary, because `Return::Optical` carries
  occupancy and not radiance.

**Added 2026-09-09, with the setting:**

- **No ice event.** No melting plug, no collapsing bridge, no roof that drops. `THE-ICE.md` §6.6:
  *"An ice hazard that acts converts the place into a haunted house."* The one exception is already
  in the fiction and is not an event: **the melt front is a place** (§3.7). It does not move during
  a match.
- **No marker on the melt front, the trimline or the snowline.** All three are lines the world
  draws by *changing*, and every one of them is one `smoothstep`. Drawing an edge on any of them is
  the same mistake as tinting the scour (§5.3).
- **No seasonal Assayer.** `THE-ICE.md` §4.5: more meltwater in summer and a faster cycle is
  obvious and it would delete the clock, the landmark and the learnable behaviour. **The tank fills
  in 75 seconds. It always has.**
- **No snowline that moves on its own.** It may only move as a deliberate published world event
  (`ROADMAP.md` Phase 9), never between matches and never during one. A world that visibly changes
  on its own is a weather system, and this world is one arithmetic, frozen.
- **No cave city.** The town is terraced and open to the sky. A society that lives *inside* rock
  puts the safe place underground and collapses `DESIGN-PRINCIPLES.md` §3's whole contrast. §12.3.
- **No person as a character.** People are visible in the town at distance and never nearer than
  the far side of a street: lit windows, moving vehicles, smoke, figures two pixels tall. And
  underground, `WHAT-HAPPENED-HERE.md`'s rule is *strengthened* by the ice rather than relaxed:
  **there are no remains, no bodies and no personal effects, ever, anywhere in this game**, and the
  ice will make somebody want to put a frozen person in a crevasse. Do not.
- **No blue snow shader.** Snow's diffuse term is achromatic; the blue lives in the shadow, which
  is the sky's colour, and in path length through ice, which is absorption (§3.1). A material that
  reaches for a blue albedo has failed the rule.

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
| 10 | **The point cloud as opaque depth-tested points with ring structure preserved** + the two-layer replay composition | 3 | ROADMAP says this screen gets the most polish. *(Reworded 2026-09-09 to match §8.2, which was rewritten the same day: the oriented disc and the 45 mm constant are deleted, and the floor decal is demoted to an option for the widest replay camera. The days are unchanged.)* |
| 11 | **Depth as one BFS field with six consumers** | 2 | |
| 12 | Module silhouette fixes — `passive_acoustic` vane, `structural_monitor` spike, beacon caps, cargo fill | 3 | |
| 13 | Damage rungs and the `damage` geometry exception | 2 | |
| 14 | Chassis gestures (Swimmer first — it has none) | 2 | Phase 5 is Surveyor-only; this is Phase 6 |

**What ships in the first week:** items 1, 3, 4 and 5 — about four days — and they change
every existing image in the project. That is the honest first pass, and item 1 is four
minutes of it.

**What needs no building at all:** any hand-authored *cave* asset. The cave is a shader, the
machinery is a spec in cells, and the found objects are poses and emissive states. *(Corrected
2026-09-09: the agents are parameters **on an authored rig**, per `DESIGN-PRINCIPLES.md` §5 and
§9 above.)*

**Not re-costed for the ice, deliberately.** *(Added 2026-09-09.)* The table above is a Phase 5
cost for one cave biome and one chassis, and every item in it still has to happen. What the ice
adds is scoped in `THE-ICE.md` §2's ranking table, which prices the *shape* of the setting in weeks
and its *look* in days, on the strength of a real observation about the built spikes: both have
already survived a total rebuild of the layer below the layout/dressing seam without moving their
content hash. **So: snow, ice, light and palette are a dressing change and cost nothing above the
line; a valley and a vertical cave are layout and topology changes and cost the plan, the hash, the
determinism tests and everything downstream.** Three art items are new and belong on this list
whenever it is re-costed, and I am naming rather than pricing them because two of them are
downstream of rulings nobody has made:

| new item | why it is not costed here |
|---|---|
| **the ice family** (§3.1) — one shader, one new anisotropic flow-shaped noise primitive, a subsurface term | needs `THE-ICE.md` §9 Q8 (is there ice in the cave at all) |
| **snow, and tracks in it** (§12.1) | it is the highest-value item in the whole ice decision and it does **not** depend on the valley, the town or the vertical cave. `THE-ICE.md` §11 puts it third in its own order and I agree |
| **the three lines on the wall** (§12.3) — trimline, town, snowline | two `smoothstep`s and a silhouette, and between them they put the entire setting on screen with no text. `THE-ICE.md` §11 puts it immediately after the snow |

**And one item on the list above got cheaper.** Item 7, the worked-passage geometry, is where
*"a place worth robbing"* gets built; the pitch profile family (§3.4) is new work beside it rather
than instead of it, and `THE-ICE.md` §2.3 reports that the built cave's topology layer is *"428
lines of pure integer code"* of which most rules survive verbatim — **it is the topology layer that
is rewritten, and it is the small file.** The expensive half is the dressing side's profile
function, which is one function.

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

**The ice age changes the shape of this risk twice, and the two changes pull in opposite
directions.** *(Added 2026-09-09.)*

**It gets better, in two ways that are real.**

- **There is now a bright place, and the player comes from it.** The fatigue argument was made
  against a game that was black from the title screen. `DESIGN-PRINCIPLES.md` §10's surface is
  *"monotonous and snowy and pretty… a valley under a large sky"*, and §3's structure is that the
  player leaves somewhere worth being. **A frame that is 90% black reads differently at minute six
  when minute one was white**, and the descent is now three legs long (§12.6) rather than a cage
  and a cut.
- **The shallow band relents.** §2.2 and §2.9 give the ice band a softer falloff and its own
  exposure row. The first minutes underground are the friendly ones by construction, which is the
  cheapest possible answer to *"after a minute, do you want the lights on?"* — for the first
  minute.

**It gets worse in one way, and it is the one that would actually kill it.** The failure mode was
never darkness, it was **fatigue**, and the ice does nothing about minute six. Worse: **§3.7 puts
everything worth having below the ice band**, so the friendly part of the cave is the part with no
reason to be in it, and every minute of the match that matters is still black. A player who is
relieved at 0–30 m and exhausted at 200 m has had the problem moved, not solved.

**So the kill test in this section is unchanged and gains one leg.** Render the sixty seconds as
specified, and render **a second clip that starts on the valley and goes down**, because what is
being tested is a contrast the old build could not produce. Same two questions, same encode-first
rule. If question 2 still comes back yes, the fallback is still §2.8.

---

## 12. The surface

**New 2026-09-09.** This document previously had almost nothing about the world above the collar,
because there was almost nothing above it: `DESIGN-PRINCIPLES.md` §3 gave the game a pit-head on
2026-09-08, and §10 gave it a valley, a town and an ice age the next day. **It is numbered 12 and
sits at the end so that §4 through §11 keep their numbers** — five documents cite this one by
section, nineteen times to §2.1 alone — and it should be read immediately after §3.

`docs/THE-ICE.md` §7 is the specification and every number below is its. **They are all GUESSes and
that document says so** — *"chosen so the frame reads rather than measured from anything, and they
are offered as a set because they only work together"* — so treat the ratios as the decision and
the values as provisional. `THE-ICE.md` §9 question 5 asks the designer to confirm them in order of
magnitude, and questions 3, 4, 19, 20, 21 and 22 decide the shape of the place.

**And one honest statement of what this section is.** Everything in `spikes/godot/surface/` is a
**wet brown industrial pit-head at 174 × 148 m under overcast**, tuned against one seed. There is
no snow, no ice, no valley, no mountain and no town anywhere in it. So §12 is **specifying, not
documenting**, and the reader should hold it to a lower standard of evidence than §2 or §3. Where a
built number exists it is cited, and it is usually cited as *the thing that has to change*.

### 12.1 Build this first, and it is not a picture

Before the town, before the valley, before the terrain: **snow records what walked on it.**

`DESIGN-PRINCIPLES.md` §3 puts teaching on the surface. §7's correction was that *"clear ground is
a feature — traffic lanes, turning circles, the apron in front of a bay and the ground a machine
walks are kept clear, and their emptiness reads as use."* Snow does that automatically, and it does
something concrete could not: **it keeps a record.** A training course in snow shows the machine's
own path, every run, as a physical mark on the ground — where it hesitated, where it turned, where
it went twice, where it went wrong.

> **The floor of the training course draws the policy.**

That is the highest-value object the ice-age decision produces and it is not an art win, it is a
teaching win. This project's own recorded lesson is to check every stream against *does this make
the player teach the agent sooner?* — and a course whose ground draws the answer is the only item
in this section that answers yes. **It does not need the valley, the town, or the vertical cave**,
and it should be built ahead of all three.

The instrument is a deformation or decal accumulation on the course ground. The built site already
bakes a **wear field on a 1 m grid, 183 × 157 cells, in about 90 ms**, from the walkway polylines
and the haul road — *"the site already knew where everything was"* — and a track record is that
field written at run time by one agent instead of at build time by a layout. **PROPOSED**, and it
is `THE-ICE.md` §7.1's, taken whole.

### 12.2 Light, and it is the same light as the shaft's

§2.1 carries the economy and its two new rows; this is what they mean on the ground.

- **There is no direct beam on the ground the player stands on.** The valley floor sits in the
  shadow of an 1,800 m wall for most of the day, so it is lit by the sky alone — a clear-sky north
  window at the scale of a landscape, on the order of **12000 K, `(0.60, 0.74, 1.00)`**. The sun is
  on the ridge and on the peaks and never on the floor.
- **Skylight in a shadowed valley is roughly a tenth to a seventh of full sun** (`THE-ICE.md`
  §2.6, its own arithmetic and it says so). Snow at 0.8 albedo under a tenth of the illumination is
  comparable in luminance to the built yard's 0.24 concrete under full overcast, **possibly
  darker.** So **the snow does not automatically dominate the frame by value**, which is what makes
  a blue-white exterior survivable next to a cyan belief layer at all.
- **The in-frame dynamic range goes up, not down**: sunlit peak against shadowed floor is roughly
  **thirty to sixty to one** inside one frame. §2.3's discipline transfers exactly — do not
  compress, let the peaks blow, grade for the floor.
- **Alpenglow is the only warm light and it is unreachable.** Minutes long, at 8–15 km, illuminating
  nothing the player can touch. It is the second register `DESIGN-PRINCIPLES.md` §4 demands, handed
  over by the landscape instead of invented. **The town's lit windows are the other warm element
  and they are at human scale.**

**What the built rig says, and what has to change.** `weather.gd` runs three states and no
time-of-day system: overcast at sun `(−46°, 132°)`, colour `(1.00, 0.985, 0.962)`, energy 1.50,
angular size 3.6°, ambient 1.30, `tonemap_exposure` **0.70**, fog density 0.0016. That sun is
**near-neutral on purpose**, and the reason is measured: the previous pass made the surface sun
*be* the shaft's light and the underfoot frame came back at **B/R = 1.30 — a monochrome blue
image**; with a neutral sun and a cold sky it measures **B/R = 1.01**.

> **`surface/PHOTOREAL.md` §3.4 asked for a ruling and §2.1 now answers it in its favour, without
> overruling it.** The sun stays near-neutral and correct. It simply is not on the ground the
> player is standing on. *"Real overcast diffuse is 6500–7500 K, not 12000 K; 12000 K is a
> clear-sky north window"* — and a shadowed valley floor under a clear sky **is** a clear-sky north
> window.

Everything else in that rig is re-derived rather than reused. **Every exposure number has to move**:
the yard's hardstanding is **0.24 linear** *"because the yard is meant to be a hellscape"*, fresh
snow is **0.7–0.9 linear**, and the photoreal pass's own image targets (p50 ≈ 0.33, under 2% dead
black) were fitted to a ground three times darker than the one this setting has. Two built numbers
worth keeping anyway: **the sky must be a shader, not `ProceduralSkyMaterial`, and it must run
`PROCESS_MODE_REALTIME`** — QUALITY re-bakes the radiance cubemap every frame and took the overcast
pass from 93 fps to **9**. And **the sky's lower hemisphere has to be about as bright as its
horizon**, because `fog_aerial_perspective` samples the sky in the pixel's view direction and a
dark ground colour paints every downward ray black.

### 12.3 The valley, the town, and the three lines that date the world

| quantity | proposal | why |
|---|---|---|
| valley floor, wall toe to wall toe | **1.2 km** | wide enough to separate town from pit-head; narrow enough that **both walls are in almost every frame**, which is what makes it a valley rather than a plain |
| valley length in view before it turns | **6–8 km** | one aerial-perspective ramp |
| wall height above the floor, to the ridge | **1,800 m** | the smallest number that reads as *massive* rather than as *hill* |
| the peaks behind | **2,600–3,200 m** | they carry the only sunlight |
| pit-head to the far wall | **~900 m** | deliberately close: the town must read as **buildings**, not as texture |
| to the nearest big peak | **4–6 km**; alpenglow peaks **8–15 km** | aerial perspective needs range |
| **the trimline** | **+310 m** | the ice's high-water mark |
| **the permanent snowline, today** | **+1,100 m** | above the whole town, well below the peaks, and it has moved up within living memory |
| the glacier's terminus | **~3 km up-valley** of the pit-head | far enough to be scenery, near enough to be the reason the pit-head exists |
| the town | foot **+90 m**, main body **+120 to +380 m**, oldest quarter **+520 m** | below |
| the cave | **0 to −250 m** | §3.7 |

**Which gives the game one vertical axis end to end: +520 m to −250 m, with the shaft in the
middle of it**, and `datum_mm` — the valley floor — is the single zero both halves are measured
from. A player standing on the floor can see both ends. **That is the strongest structural idea in
the setting and it costs one `i32`.**

**One correction to the obvious reason for wanting mountains, because it changes what gets built.**
A mountain does not make a machine read small. **A chain of known sizes does**, and one enormous
thing at 5 km with nothing between it and the machine reads as a backdrop. What delivers absolute
scale is the sequence *machine → bay → building → town on the wall → ridge → peak*, and the
load-bearing link is **the town**, because it is the only element whose size a viewer already
knows. **So the mountains are the thing you see and the town is the thing that does the work.**

**The town: terraces above a trimline, and it has been coming downhill for a thousand years.** The
constraint does the design. A glacier fills a valley from the bottom up, so the floor is the *last*
ground to come free. Above the trimline — the line the ice's own upper limit scours across both
walls — the rock was cold and exposed but never buried. **So the society survived the ice on the
walls, above the trimline, and has been walking downhill ever since.**

- **Terraces and galleries cut back into the wall, open to the sky.** Shelves quarried into rock,
  buildings standing on them, roads switching back between them, everything facing out across the
  valley. **Not tunnelled** — §9 bans the cave city, and the reason is that a society living inside
  rock puts the safe place underground and collapses `DESIGN-PRINCIPLES.md` §3's whole contrast.
- **It is oldest and highest.** The upper quarter at +520 m is the survival town: small, dense,
  weathered, built for a climate nobody now has to live in. The main body is modern and
  manufactured. The foot at +90 m is new construction on ground that was under ice.
- **So the town's stratigraphy runs downward and gets newer** — which is the mine's index running
  downward and getting newer (§7 cue 5), a thousand years apart, in one frame. **Two societies,
  both working downward, both getting better as they went, and the player stands in the second one
  looking at the first one's shaft.**

**And the ice age becomes visible without a word.** Three horizontal lines on the wall, all visible
from the floor, none explained, and no number, name or date anywhere:

| the line | at | what it says | how it is drawn |
|---|---|---|---|
| **the trimline** | +310 m | where the ice stood at its greatest. Weathered, jointed, lichened rock above; scoured, polished, freshly exposed rock below | **one `smoothstep` on world height** in the wall material |
| **the town** | +90 to +520 m | it straddles the trimline. Old and dense above, modern and manufactured below | silhouette and window light |
| **the snowline** | +1,100 m | where the ice is *now*. Not geological — current, and moving. The tell is a band below it that is bare, raw and colonised by nothing, because it came out from under the ice inside a lifetime | **one `smoothstep` on world height** |

> **The valley has a tide mark and it is three hundred metres high.**

That is the same instrument as §3.5's *"0.12 m mineral tide-mark crust above it — one detail that
says the water moved"*, at a thousand times the scale, and it obeys `WHAT-HAPPENED-HERE.md`'s
no-date, no-era, no-calendar rule absolutely. **A player who never thinks about it still sees that
the town straddles a line.**

### 12.4 Materials, and the pit-head is still a pit-head

**The pit-head survives the setting change, moves up the valley, and keeps its props.** That is the
finding that saves the built work (`THE-ICE.md` §7.4): the surface is now **three places** — the
town on the wall, the valley floor and its haul road, and a private pit-head at the retreat margin
— and everything in `spikes/godot/surface/` is the third one. Its ground material changes, its
lighting changes, its arrangements do not.

**`DESIGN-PRINCIPLES.md` §7's arrangement vocabulary is unchanged and is *more* correct in snow**,
because a swept bay in snow reads as use ten times more strongly than a swept bay on tarmac. The
twelve arrangements, the 1.2 m module the bays are cut on, the 0° / 90° yaw discipline, the ±2°
jitter that exists on exactly one object, the margins-only rule for debris and standing water, and
the numbered bay plate at the head of every stand — all of it stands. **The one thing snow adds is
that clear ground now has to be *cleared by somebody*, and the marks of the clearing are the
dressing.** A ploughed edge, a bank at the end of a lane, a swept apron with a rim: that is
`DESIGN-PRINCIPLES.md` §7's *"somebody swept this yard this week"* made literal.

**Snow is cheap as a material and expensive as a look**, and the split is worth stating exactly.

*Cheap.* A `"snow"` row in the material table is one line of ten numbers, no shader edit. The
`g_wet` global-uniform mechanism is exactly the pattern a `g_snow` copies, so snow accumulation as
a season lever costs one uniform. And **the slope term already exists**: the ground shader has
`smoothstep(0.86, 0.985, wnorm.y)` and the solid shader already drives its dirt term off
`clamp(wnorm.y, 0, 1)` — dust settling on up-facing surfaces. **Snow on up-facing surfaces is that
term with a different colour and a harder threshold.**

*Expensive.* Four things, none optional.

1. **Snow needs subsurface scattering to read, and nothing in any of the three material systems has
   a translucency term.** It is the same term §3.1's ice needs, which is the argument for building
   them together.
2. **Snow's silhouette is the known open weakness.** *"A flat plane with a heightfield on it is
   still a flat plane. POM gives apparent depth and it works well… but the silhouette is unchanged,
   so at grazing the ground shows a clean straight edge."* **Drifts, and snow banking against
   objects, are exactly the case parallax cannot do**, and they are the whole read of snow at
   ground level. That is instanced geometry, not a shader.
3. **`g_wet` and `g_snow` are not independent sliders.** Wet darkens albedo and drops roughness;
   snow does the opposite. They need one combined model rather than two knobs that fight.
4. **Snow will crawl unless it carries the same per-band Nyquist fades the aggregate does**, and
   the spike has already seen exactly this failure wearing exactly this costume: a 23 mm worley
   cell aliasing on a spoil tip *"came back as pale blotches crawling over the spoil tips that read
   exactly like snow."* The fade table is the reusable part. **The rule underneath it is §3.2's:
   fade bands by pixel footprint, and what a faded band turns into is roughness.**

*Also gone:* the puddles (ice now, or buried), the weeds in the margins, and the overcast rig.
*Also honest:* the ground shader is about 800 lines whose entire subject is weathered concrete —
slab joints, arris, lippage, spalling, repaired patches, hairline cracks, exposed aggregate, oil,
tracked mud, ruts, puddles. **It is the most expensive asset the photoreal pass produced and this
setting makes it the least visible.** That is a sunk cost rather than a new one, and the
consolation is §12.1.

**And one rule from below the collar inverts up here and must be allowed to.** SSAO does nothing in
a cave because it only modulates ambient and there is none (§2.10); on the surface it is *"what
stops 84,864 props hovering above the ground"* and it costs **4.2 ms of a 13.7 ms frame**. Both are
correct. **The variable is whether there is ambient, and the collar is where it changes.**

### 12.5 Scale, and what is ruled out up here

**The mountains are the cheapest large thing this game can add, and that is not intuitive.** At
4–15 km they are silhouette, aerial perspective and a snow line, and nothing else: no material
detail, no props, no shadow casting, no collision, and LOD that never has to be good. §3.6's
*"spend no art budget past 15 m"* is exactly the right rule inverted: **spend nothing past 500 m
except silhouette and air.**

**The inhabited wall at 900 m is where the money goes.** Close enough that buildings need edges,
roofs, glazing and a believable street logic; far enough that none of it can be instanced from the
yard kit at yard density. Pitched roofs, glazing and terracing do not exist in any built dressing
layer. **Budget the town, not the mountains.**

**And the valley saves something real: it is a room.** A valley floor is walled, so the *view* is
enormous and the *drawn extent* is bounded by two ridges at 900 m and a head wall at 6 km — a far
more tractable scene than an open snowfield with a true horizon in every direction. **Rooms are
what this project already knows how to build.**

**The one measured risk, and it is a hard number.** The built pit-head runs at **13.72 ms mean and
18.06 ms worst in overcast — a 40 fps worst case, not a 60 fps one** — and its own earlier claim
that *"it never drops below 60"* is false as built. **There is no headroom to spend on a town and a
mountain range.** So the mountains have to be free by construction, which they are, and the town
has to buy its own budget back, which it does not yet. Hold every estimate against that number, and
against the spike's own warning that the same build measured anywhere between **4.89 ms and
65.03 ms** on identical code depending on thermal state — *"a 13:1 spread"*. **Nothing under a 20%
difference between two measurements up here is real.**

**Ruled out on the surface** (and repeated in §9 so the list stays in one place): no cave city; no
person as a character; no snowline that moves on its own; no blue snow shader; no ice event; no
marker on any of the three lines. And one more that belongs only here: **no weather that acts.**
The exterior gets states, not events — the built rig already has three and switches between them —
because `WHAT-HAPPENED-HERE.md`'s thesis is that this world is one arithmetic, frozen, and a valley
at the foot of a retreating glacier is beautiful and provisional at once without anything needing
to happen in it.

### 12.6 The descent is three legs now, and each is colder than the last

| leg | how | register |
|---|---|---|
| the town to the floor | an inclined railway down the terraces — the players' technological register made obvious | warm → cold. You leave the last building |
| the floor to the pit-head | 3–5 km of haul road up the valley, walls on both sides, the glacier ahead | cold → empty. **The only leg where the whole vertical axis is in one frame** |
| the collar to the dark | the cage, about twenty seconds | empty → black |

`TRAILER.md` §1's reversal — *"you spend the first act being shown a machine you are preparing and
teaching, in daylight, with your hands on it. Then it goes down the shaft and you never touch it
again"* — now has two middles, and the picture runs **warm → white → black** across them.

**`GLOSSARY.md`'s Commit is unchanged and must stay unchanged.** It is *"the moment control leaves
the player, roughly 20 seconds after descent"*, and it is **the cable coming out of the charge port
at the collar** — not the town gate and not the road. Three legs of travel do not get three
commits; they get one, at the bottom.

**Where teaching happens, relocated rather than changed** (`DESIGN-PRINCIPLES.md` §3 is unchanged
in substance). **The course stays at the pit-head**, on the flat by the collar, now in snow — it is
outdoor, cold, and it is the last thing before the descent. **The bench and the tally board move to
the town**, where it is warm. And the beat that falls out of that: *(PROPOSED, `THE-ICE.md` §7.7)*
**the winding house keeps the *ancients'* tally board, empty and cast; the player's board is the one
in town; and the two are the same object a thousand years apart.**

**Still open and not answered here:** whether anything is at stake on the surface
(`DESIGN-PRINCIPLES.md` §3 leaves it open and the ice does not change it), and the vision board's
*"an open-topped daylight course cannot teach darkness"*, which is unchanged and still a real
problem.

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
- ~~**Rock albedo 0.30** as the light-end anchor. `wet_rock` currently ramps 0.015 → 0.11 (wet
  black basalt); this is a dust-covered dolomite. Both are physically real; I picked the
  brighter because the mine is dusty, and because below ~0.25 the bounce budget collapses and
  the machine is never lit by its own lamp.~~ **Wrong, and measured wrong twice.** §3.1 carries
  the correction and the two independent measurements. The reasoning quoted above is also where
  the error came from: *"below ~0.25 the bounce budget collapses"* is an argument about bounce
  light in a world that has none — §2.1 sets ambient to zero — so it was defending a brightness
  the lighting model cannot use. *(Struck 2026-09-09.)*
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

**Added with the ice, 2026-09-09.** Everything in this block is either mine or `THE-ICE.md`'s, and
the attribution says which. None of it is the designer's except where §10 of
`DESIGN-PRINCIPLES.md` is quoted directly.

- **The one sentence's "that the meltwater started again."** Mine. `THE-ICE.md` §4.4 recommended
  the weaker *"still working"*; I went one clause further and said why in §1. **The underlying
  ruling is PROPOSED and unmade.**
- **§3.1's four ice scalars** — `clarity`, `polish`, `debris`, `depth_of_medium`. Mine. `THE-ICE.md`
  §6.1 decides only that the blue is path length rather than tint; the parameterisation is my
  invention and it is the same shape as the rock family's on purpose.
- **§2.9's ice-band exposure row.** Mine, entirely. `THE-ICE.md` §6.1 says only that ice will not
  hit the rock contract; the four numbers are chosen so that *relief* does not become *lit level*
  and nothing has measured them.
- **§2.9's daylight band.** `THE-ICE.md` §2.7's, and it flags them as guesses. They were fitted
  against nothing; the built surface's own targets were fitted to a yard three times darker than
  snow.
- **§3.4's claim that the pitch lip is the most valuable geometry in the cave**, and that a lip has
  to be legible from four metres back. Mine, and it is an assertion about a gate that has not been
  played.
- **§3.7's depth stack and its 30 / 80 / 250 m boundaries.** `THE-ICE.md` §5.2's, marked GUESS
  there. *"The ratios matter more than the numbers."*
- **§7's seventh depth cue** — that the medium change is a door rather than a gradient. Mine.
- **§8.2's ice sensor behaviour.** `THE-ICE.md` §6.2's, PROPOSED. `THE-SENSOR-AND-SLAM.md` §1
  decided water and explicitly decided nothing else.
- **§12's entire valley table.** `THE-ICE.md` §7.2's, every value a GUESS, offered as a set.
- **That the society survived above the trimline and has been building downhill since**, and that
  the town's stratigraphy therefore rhymes with the mine's index. `THE-ICE.md` §7.3's, and it calls
  it *"the second-most load-bearing guess in the document."*
- **That the valley floor is in shadow most of the day and is lit at roughly a tenth of full sun**,
  and the thirty-to-sixty-to-one in-frame range that follows. `THE-ICE.md` §2.6/§2.7's arithmetic,
  which says plainly that it is arithmetic and not measurement. **§2.1's entire reconciliation rests
  on it.**
- **That scale comes from the chain and not from the mountain**, so the town is the element to build
  properly. `THE-ICE.md` §7.2's.
- **That the mountains are nearly free and the inhabited wall is not.** `THE-ICE.md` §7.5's, stated
  from the surface spike's numbers but not measured on anything that exists.
- **That ice is the one specular-family material that does not fail under one lamp**, because a
  subsurface term returns the lamp's own light. Mine, argued from the materials spike's measured
  failures of water and metal, and **not measured on ice, because no ice exists.**

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

**Added 2026-09-09.** Three of these were already open before the ice and the ice forces two of
them; the rest are the ice's own. `THE-ICE.md` §9 has twenty-four questions with defaults and this
list names only the ones that block *art*.

8. **Are §3.1's rock triples albedo, and were they wrong?** (§3.1) **This is now the highest
   blocker on the list, above metres-per-cell**, because it is measured, it is contradicted by two
   independent probes, and one of them names it as the direct cause of what the designer was
   looking at when he asked for photoreal. My answer: they were albedo and they were about four
   times too bright. The sub-question nobody can answer without a ruling is what a *scoured floor*
   is — the two spikes are 4.4× apart on it.
9. **Are generated noise textures allowed?** (§3.2, §9) `PROCEDURAL-AND-GODOT.md` question 5,
   recommendation yes, unruled. `DESIGN-PRINCIPLES.md` §6 says photorealism depends on the default
   holding, and the cave's photoreal pass now depends on it outright: *"If the answer comes back
   no, most of §2 goes with it."* My answer: yes.
10. **Is §9's "no hue axis" amended, and how?** (§9) `DESIGN-PRINCIPLES.md` §6 records that
    photorealism and the literal rule cannot both hold, and leaves it open. Both spikes have
    already bent it and both said so. My answer: hue is a material property keyed to position,
    never an axis, never a legend, chroma held to about ±3.5%.
11. **Did the machinery stop and restart?** (§1, §5.2) `THE-ICE.md` §9 Q1, default yes. It changes
    one clause of the one sentence and nothing else in this document; it is the difference between
    a bearing that has run 17 million cycles and one that has run 590 million.
12. **Is there ice inside the cave, or only snow outside it?** (§3.1, §3.7, §8.2) `THE-ICE.md` §9
    Q8, default *yes, in the shallow band only*. **Saying no deletes §3.1's second family, §3.7,
    §2.2's ice paragraph and §2.9's ice row**, and makes this a rock cave under a snowy surface.
13. **Are §12's valley numbers right in order of magnitude?** (§12.3) `THE-ICE.md` §9 Q5. The
    ratios are the decision, not the values, and vague scale delivers no scale at all.
14. **Does the surface get its own exposure band in CI, leaving the lamp-frame targets untouched?**
    (§2.9) `THE-ICE.md` §9 Q23. Without it, either the peaks fail the build or the cave stops being
    enforced.

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
3. **~~`blindside-gen` must make flooding rise monotonically with depth.~~ Closed 2026-09-09 by
   the vertical cave, and this is the cleanest thing the ice-age decision does to this list.**
   `THE-ICE.md` §5.5: when the generator thinks in elevations, *"G10 stops being a tested
   post-condition and becomes a consequence: water finds the lowest place."* The requirement below
   is still the requirement; what has changed is that it no longer needs a 1,000-seed test to
   enforce, because a plan with real elevation in it cannot violate it. Original text kept for the
   record:
   `THE-MACHINERY.md` §7 says *"the deepest ground is the wettest"*, and the whole deep-is-wet-is-dark-is-specular
   chain in §3, §5 and §7 rests on it. Measured on the Phase 1 cave, flooding by depth
   quartile is **0.0% / 17.1% / 30.8% / 0.0%** — the deepest quarter is bone dry. **This is
   not a bug**: `phase1/truth/cave.py` is a hand-authored dict of eleven chambers in a phase
   `CLAUDE.md` declares throwaway, and there is no generator yet to have a bug in. It is a
   requirement to carry into `blindside-gen`, and the art cannot fix it from outside.
4. **`blindside-gen` must make chambers taller than the passages that reach them.** (§5.5)
   Otherwise a 6.6 m mast does not fit under a 4.8 m ceiling, and nothing in a chamber is
   visible from outside it. *(2026-09-09: still required, and now trivially satisfiable —
   `THE-ICE.md` §5.5. Also worth recording that the invariant as currently written in
   `PROCEDURAL-AND-GODOT.md` §1.6 **cannot be checked**: it asserts a chamber is taller than every
   passage that reaches it, and `Passage` has no ceiling field. Found while reading for the ice,
   not caused by it.)*
5. **The Swimmer has no visual identity** while the design gives it the most distinctive job
   of the four chassis. (§4.6)
6. **`THE-MACHINERY.md` §2.1's "you can see which way the boom is pointing from the next
   chamber" is true of the schematic and false of a ground-level viewer.** (§5.5) Since *a
   hazard is identifiable before it fires* is a design requirement, this needs either an
   amendment to the doc or the generator rule in item 4 — and it currently blocks one of the
   four gate questions. **Partially resolved 2026-09-09 by the vertical cave**: from a level
   *above* the chamber it is true, which is a third answer neither of the two above anticipated.
   The residue is that it is true for a *viewer* and never for a *policy*, because the sensor
   cannot look down. §5.5.

7. **Three separate measurement passes now want a second light source, and nobody has ruled on
   it.** *(New 2026-09-09, and it is the loudest thing in the spikes.)* The cave's photoreal pass:
   *"A lamp at the eye is a photometric problem, not an art problem… a second source — even §2.8's
   contingency circuit at its low end — would do more for photorealism than any shader I could
   write. **This is a design question, not an art one.**"* Its cinema pass: *"A second source would
   do more for this than the whole post stack."* The materials library reaches it from the material
   side — wetness and bare metal both fail because there is nothing lit to return — and concludes
   *"the resolution is content, not code."* And the cave spike's own risk register says the quiet
   part: *"the frame currently survives because ~90% of it is black and the eye forgives what it
   cannot see… **The spike proves the pipeline at one lamp. It does not prove the look at two.**"*
   **This does not change my recommendation** — §2.8 stays a fallback and §11's kill test stays the
   thing that decides it — but the evidence has moved and the decision should be taken with the
   evidence in front of it rather than on the original argument.

8. **The built pit-head is a 40 fps worst case and the setting adds a town and a mountain range to
   it.** *(New 2026-09-09.)* 13.72 ms mean, 18.06 ms worst in overcast, with SSAO alone at 4.2 ms
   of it, and its own *"it never drops below 60"* claim now retracted. §12.5. The mountains are free
   by construction; **the town is not, and nothing has bought its budget back.**

---

## Changelog

Every revision to this document, what it touched and why. `§8.2` was rewritten earlier the same day
by a different pass and is listed for completeness.

### 2026-09-09 — the ice age

`DESIGN-PRINCIPLES.md` §10 gave the world a period, a valley, a town and a vertical cave.
`docs/THE-ICE.md` is the reconciliation and is this revision's specification. **Where it made a
recommendation about this file I followed it; the four places I went further or differently say so
in the text.**

| § | what changed | why |
|---|---|---|
| header | *"Nothing in this document needs a modeller"* corrected and scoped to the cave | `DESIGN-PRINCIPLES.md` §5 was amended by the designer on exactly this point; authored assets were never covered by the rule and treating them as if they were cost a stream of work |
| header | revision note added, pointing at `THE-ICE.md` and at §12 | somebody reading this cold has to know it moved |
| **1** | **the one sentence rewritten**, and the build contract's items 1, 2, 4 and 5 with it | the valley, the restart, the meltwater, and the falloff figure. The old sentence is quoted in full and each of the four moves is argued |
| 2.1 | **two rows added** (the sky, alpenglow); the shaft's row restated as *the last of the daylight*; world-background-zero scoped to below the collar; the collar falloff rule imported from the surface spike | `THE-ICE.md` §2.7 recommends adding rows rather than amending, and the mountains reconcile the light economy rather than breaking it. Its recommendation taken whole |
| 2.2 | **the ratio table corrected against measurement**, two rows struck and replaced; an ice paragraph added | 90:1 across three metres needs d^-4.3 falloff and measures 7:1; *"floor 3 m = 0.08"* and *"wall 8 m = 0.06"* cannot both hold. Both from `materials/NOTES.md` §5.2 |
| 2.3 | *"across three metres"* → *"across the frame"*; the exterior's dynamic-range paragraph added | consistency with 2.2, and the same discipline applies to the peaks |
| **2.9** | **a second and third exposure band added** (ice, daylight); the current cave failures corrected; **the lens and the vignette added as exposure controls**, with a ruling that the contract is measured *before* the lens | one contract cannot cover a world with a sky. `THE-ICE.md` §2.7's recommendation, and the surface spike had found it independently. The lens finding is the cave cinema pass's and was not in this document at all: same scene, same lamp, **a 1.75× swing in legible fraction from focal length alone** |
| **2.10** | **new.** Contact shadows do not exist in Godot 4; SSAO does nothing under zero ambient; SSR measured and cut on cost rather than on principle | three assumptions in this document that the engine does not support, all measured. The SSR reasoning is the part worth keeping: it inverts above the collar |
| 3 (intro) | **new.** The vertical axis, the three media, and down-is-cheap | the section assumed a horizontal mine throughout |
| **3.1** | **rock albedo corrected** (~4× too bright, found independently by two agents); the scoured floor corrected separately; **a second material family added for ice** | the strongest measured contradiction in the repo, and `THE-ICE.md` §2.10 says the ice forces the ruling. Ice as a family, not a biome |
| 3.2 | the no-bitmap absolute restated as its intent; generated noise permitted with its reason; two measured node-level rules added | `PROCEDURAL-AND-GODOT.md` Q5, and `DESIGN-PRINCIPLES.md` §6's *"intent binding, letter amendable"* |
| 3.3 | a vertical ruler added beside the 1.2 m module | the module is horizontal and does nothing for a drop |
| 3.4 | **a fourth register added: the pitch, as a second profile family** | a swept floor-legs-crown profile cannot express a shaft at all |
| 3.5 | **`medium` row added**; the depth row rescoped | one enum keys material, sensor, sound and footing. *"Not altitude"* was written when there was no altitude |
| 3.6 | the three measured reversals flagged; LOD comes back | every sightline number was cast across a plane |
| **3.7** | **new.** The depth stack: ice, karst, workings, past the sump — and the melt front as a place | `THE-ICE.md` §5.2 |
| 4.6 | one sentence on the Swimmer | the ice hands the weakest chassis identity a job |
| 5.2 | the restart as *evidence for* the three ages of iron; two measured metallic corrections | 17 million cycles against 590 million is why there is a wear surface left to be bright |
| 5.5 | **partially reversed** — the mast is a landmark from above | measured from ground level on a plane, which is no longer the cave |
| 6.3 | one bullet: a beacon chain down a shaft | the same image rotated, and better |
| **7** | depth is altitude in the world and darkness on the display; `depth_mm` beside `depth_band`; **a seventh cue**; a second inversion | `THE-ICE.md` §2.9's replacement taken as written. Neither field replaces the other |
| 8.2 | one bullet: ice is where the map goes thin | *(the section itself was rewritten earlier today for the scanning sensor; checked for consistency with §10's cost table, which still said "oriented discs" and no longer does)* |
| 8.4 | cyan restated as a saturation rule; three must-nots rescoped; the sky added as a sanctioned exception | a blue-white exterior cannot keep a literal no-blue rule, and pretending otherwise is how a rule stops being cited |
| **9** | **four lines amended, each with its reason and its old text quoted; seven added** | the ice ban, the bitmap ban, the hand-modelled ban and the ambient ban all needed care. The intent of every one of them is unchanged or stronger |
| 10 | item 10 reworded to match §8.2; the ice explicitly **not** re-costed, with the three new items named | re-costing Phase 5 is not this revision's job; naming what is missing is |
| 11 | the risk restated in both directions | the surface makes the contrast better and does nothing about minute six |
| **12** | **new: the surface.** Light, the valley, the town, the three lines, materials, scale, what is ruled out, the three descents | the document had almost nothing above the collar. Numbered 12 to protect ~120 cross-references from five documents |
| guesses | the old rock-albedo guess struck; sixteen new entries with attribution | |
| decisions | seven added; the rock albedo promoted above metres-per-cell | it is measured, contradicted twice, and named as the cause of what the designer was looking at |
| design problems | item 3 closed, items 4 and 6 partially resolved, **two added** | the vertical cave closes one for free and the spikes opened two |

**What was deliberately left alone.** §0 (the lamp aim finding), §2.4–§2.8, §4 apart from one
sentence in §4.6, §5.1, §5.3, §5.4, §5.6, §6.1, §6.2, §6.4, §6.5, §8.1, §8.3, and the probes
appendix. None of them is touched by the setting, and a revision that rewrites what it does not
have to is a revision nobody can review.

### Earlier

- **2026-09-09, §8.2 rewritten** for a real simulated scanning sensor, replacing text written
  against a sparse range/bearing model. `DESIGN-PRINCIPLES.md` §8; measurements in
  `spikes/godot/cloud/LIDAR.md`.
- **Original**, assembled from four independent passes, with the parts that did not survive
  measurement removed rather than softened.
