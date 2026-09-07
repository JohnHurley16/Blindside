# The machinery

What the ancient system is, what it does to an agent that stands near it, and what
`phase1` builds. One answer, for the designer to accept, amend or reject.

The fiction was genuinely open: `GLOSSARY.md` had three lines, `DESIGN.html` has **zero**
occurrences of "ancient", "machinery" or "ruins" (checked), and `ROADMAP.md`'s references
are build tasks. So what is decided here becomes the fiction. Everything below that is a
number is a proposal; the load-bearing guesses are listed in §11, and the one I most want
overruled is §11's first paragraph.

Every measured number came from `python -m phase1 --headless` on seed 7 and from a script
over `truth/cave.py`'s grid. Where a number is derived rather than measured, it says so.

---

## 1. What it is

**The Assayer is a survey machine the last industry bolted into the bedrock to find out
what was in the rock: every seventy-five seconds it swings a ribbed array onto a new
bearing, ratchets a hammer up its mast, and drops it, driving a shock through the stone so
it can listen to what comes back.** It is still running because it never needed anybody —
the water that drowned the workings is the same water that fills its header tank and winds
the hammer, so it will keep surveying an exhausted claim for as long as it rains. What it
found is why the deposits are where they are and why the tunnels go where they go; what it
does now is shake apart the instruments of anything standing on the rock it is hitting.

The **kind** is *a machine of the prior industry still running its program, which harms as
a side effect of doing its job.* Not a guardian, not a trap, not a hazard someone placed.
That distinction is what lets the same object be the thing you download from: it is not
defending anything, and it will talk to you while it is working.

---

## 2. The form, and exactly what `phase1/view` draws

Nothing here needs an asset, a texture or a modeller. It is quads and line segments over
`shapes.py` and the quad builder `cave_mesh.py` already has.

**The governing constraint is the camera, and it is not the one three of the four proposals
assumed.** `view.py` uses a `TurntableCamera(elevation=72, fov=0)`, clamped 60–90°
(`tuning.py` 332–334). A world-z displacement projects up-screen at `cos(elevation)` —
**0.31× at the default and exactly zero at the top of the clamp.** So vertical motion is a
weak mark and horizontal rotation is a strong one. This design puts its warning on rotation
and on the floor plane, and uses height only for *silhouette*, where height does work.

### 2.1 The parts

| part | geometry | primitive | colour |
|---|---|---|---|
| **footing** | 3 legs 120° apart, hub `r=1.0` at `z=1.2` out to `r=2.6` at `z=0`; 3 anchor pads, 0.8-cell squares | 3 quads + 12 segments | `ROCK_LIT`, pads ×1.2 |
| **mast** | hexagonal prism, 1.6 across the flats, `z = 1.2 → 11.0` | 6 quads | `ROCK_LIT` ×0.9 |
| **boom (the array)** | 7.0 long × 0.9 wide at `z = 9.0`, five cross-ribs at 1.4-cell spacing, 2.4 wide at the root tapering to 1.2 at the tip | ~22 segments | `ROCK_LIT`; outer 20% of each rib `HAZARD` @ 0.25 |
| **counterweight** | a 2.2-cell stub opposite the boom with one 1.6-cell rib | 4 segments | `ROCK_LIT` ×0.8 |
| **drop line** | one vertical from the boom root to the floor, so the boom's ground position is never ambiguous | 1 segment | `WARM_DIM` @ 0.4 |
| **hammer** | hexagonal ring 2.0 across, riding the mast; its `z` is the animated variable | 6 quads | `ROCK_LIT` ×1.15 |
| **bolt ring** | 8 markers at `r = 3.4` — the old service platform | `Markers` | `WARM_DIM` @ 0.5 |
| **the scour** | permanent, baked into `cave_mesh._floor_image` at build time | — | floor tinted toward `HAZARD`, `alpha = 0.10 · min(1, (9/d)²)^0.5` |

About 21 quads and 40 line segments, against a cave mesh of 43,202 triangles. A static mesh
that is present and never touched measured ~1 ms; `Line.set_data` at 2000 segments sits at
the empty-canvas baseline. It is free.

**The machine is `ROCK_LIT` and `WARM_DIM`, not `HAZARD`.** It is dead iron bolted into
stone and it is part of the world; only the *field* is magenta. That is what stops the
object being a magenta blob, and it is why the dormant state has to read as *finished*
rather than as menacing — the current design's mistake is that the quiet state already
looks like a warning, so the warning has nowhere to go.

**The mast is 11 cells and `CAVE_WALL_HEIGHT_CELLS` is 8.** That is +3.4 cells of screen
lift at the default elevation — 106 px at `CAMERA_CLOSE_CELLS = 40` (31.3 px/cell) and 19 px
at `CAMERA_WIDE_CELLS = 225`. It is the only thing in the cave that breaks the skyline, and
**the boom rides above the wall line, so you can see which way it is pointing from the next
chamber.** That is what the height is for. It is not what the warning is for.

### 2.2 The one rule the animation must obey

Measured on this machine, 1600×900, shown canvas, against a 3.4 ms baseline:

| operation | cost |
|---|---|
| `Mesh.set_data(vertices, faces, vertex_colors)` on **96 triangles** | **21.2 ms** |
| assigning a **new** `MatrixTransform` each frame | **21.8 ms** |
| mutating an existing `MatrixTransform.matrix` in place | 3.25 ms |
| `STTransform.translate` | 3.18 ms |
| `Line.set_data`, 2000 segments | 3.15 ms |
| `Image.set_data`, 200×120 RGBA float32 | 3.72 ms |
| a second static 2000-triangle mesh, present, untouched | 4.28 ms |

`Mesh.set_data` is a **fixed** cost, not a geometry cost: 96 triangles and 2000 triangles
price the same. Against the 26.8 ms median frame that is 74% of the 60 ms ceiling consumed
by one small animated body. **So: a rigid body is a static `Mesh` under a transform whose
matrix is mutated in place. No `Mesh.set_data` in any per-frame path, ever.**

Concretely: the whole machine is one node whose `MatrixTransform` carries the aim rotation,
mutated in place; the hammer is a child with an `STTransform` whose `translate.z` moves; the
strike recoil is the parent's `translate.z`. Nothing rebuilds. This trap is not in
`SPECTATOR-DISPLAY.md` §6.10's table and it should be added there in the same commit.

### 2.3 Dormant — 54 of every 75 seconds

The array is still. One `HAZARD` band on the top 0.6 cells of the mast, alpha 0.08–0.14,
breathing at 0.1 Hz — the existing quiet-state breathe, moved off the floor and onto the
machine.

**And the dormant floor ring is deleted.** This is the highest value-per-hour change in the
document and it costs about a line. That ring is on screen for 72% of the match and it is
most of the reason the object reads as a circle: for four minutes out of five, the only
thing drawn *is* a disc. What replaces it is the permanent scour in the floor image — the
ground around the machine is visibly ruined, in roughly the shape of the union of every
bearing it has ever worked, **with no boundary drawn anywhere.** A viewer reads *nothing
settles here*, and finds out why forty seconds later. Built once with the floor image,
never updated.

### 2.4 Active

Three marks, in order of how much they carry:

1. **The boom slews and points.** Horizontal rotation is elevation-invariant: it survives
   the whole 60–90° clamp intact, which no vertical mark does. A 7-cell arm swinging 36° in
   3 s moves its tip 4.4 cells — 2.4 cells/s, 76 px/s at CLOSE, 13 px/s at WIDE. Both are
   above the 6–8 px/s threshold this project already measured and built comets to defeat.
2. **The lobe on the floor** — an `Image` plus two contour polylines (§4.2), filling in nine
   countable steps across the nine-second warning. Area and brightness on the floor plane
   read at every elevation in the clamp.
3. **The hammer climbs the mast.** 8.4 cells of z is 2.6 cells up-screen at the default and
   nothing at 90°. It is the redundant mark, deliberately. The proposals that made a rising
   mass the primary warning were betting on the axis this camera is worst at.

---

## 3. The 75-second cycle

`Ancient.phase()` is unchanged: `p = (t + ANCIENT_PHASE_S) % 75`, lethal for the last four
seconds, so firings land at `t ≡ 41 (mod 75)` — **0:41, 1:56, 3:11, 4:26, 5:41, 6:56**.
`ANCIENT_PERIOD_S`, `ANCIENT_WARNING_S`, `ANCIENT_LETHAL_S`, `ANCIENT_PHASE_S` and
`ANCIENT_RADIUS` are all untouched, which is why every measured beat in
`SPECTATOR-DISPLAY.md` survives this proposal.

| p | rel. firing | state | what a viewer sees | what an agent hears |
|---|---|---|---|---|
| 0 – 54 | −21 → −17 | **listening** | A still machine standing in a ruined patch of floor, one faint band breathing on the mast. Nothing else moves for fifty-four seconds | nothing |
| 54 – 57 | −17 → −14 | **the slew** | **The boom swings 36° and stops, pointing somewhere.** Movement is the loudest thing on a screen; the eye follows the arm and looks where it points before it knows why | a low three-second grind (Phase 3: `Tone`; Phase 1: mixer only — §10.2) |
| 57 – 62 | −14 → −9 | **locked** | Five seconds of stillness after a movement. This is the beat that turns "a machine" into "a machine that has decided something" | nothing |
| 62 – 71 | −9 → 0 | **the wind** | The hammer ratchets up the mast in **nine clicks, one per second**. On each click the lobe fills one ninth, from the tail round to the nose, so **the last thing to light is the direction it is pointing**. The mast band goes 0.12 → 0.95 | a rising drone, `SoundCharacter.SIGNATURE`, strength 0.3 → 1.0 — exactly what `ancient.signature_strength()` already returns, and now it is the winch taking load |
| 71.0 – 71.15 | 0 | **the fire** | The hammer falls the whole mast in three frames. The rig jolts down 0.4 cells and recoils over 0.5 s | one sub-40 Hz impulse and a noise burst |
| 71 – 75 | 0 → +4 | **lethal** | Three arcs of heave cross the floor at ~24 cells/s, clipped to the lobe, fading. The lobe flashes `HAZARD → KILL`. Anything killed collapses to the existing wreck cross, displaced 0.6 cells outward along the radial — a thing hit by a shock should have moved | `CRASH` from whatever died |

Nine clicks at 1 Hz is **20 recorded frames each** at `recorder.py`'s `fps = 20`, which is
the right grain for a captured video: countable, not a strobe. A policy that hears click
seven knows more than one that hears click two, because the rate is fixed and the ramp is
monotone.

**Delete the three-flashes-at-6-Hz.** One hammer falling is more legible than a strobe, and
the strobe is part of why the current object reads as a generic damage zone.

**Keep `LETHAL IN 0:07`, and treat it as an instrument, not as furniture.**
`HAZARD_COUNTDOWN_FROM_S = 15`, so the label appears at −15 s — two seconds *after* the boom
has swung and pointed. That two-second gap is the gate question: ask the tester what the
machine is about to do at −16 s, before the number exists. If they can say it, the label is
redundant and should go in Phase 3. If they cannot, requirement 4 has not been met and no
amount of drawing will fix it.

**One director change, worth 0.1 days.** Rule 1 cuts to the machinery on the signature, at
−9 s, so on the 5:41 beat the camera arrives at 5:32 and the slew at 5:24 happens
off-camera. Make the rule fire on *slewing or signature* and the shot runs 5:24 → 5:58.6 —
34 s, inside `CAMERA_MAX_HOLD_S = 45` — and the video gets the tell.

---

## 4. The mechanism of harm, and the damage model

### 4.1 What physically reaches the agent

**A mechanical shock, delivered through the ground.** Not heat, not current, not debris, not
blast. The Assayer's entire purpose is to put energy *into the rock*; the agent is standing
on the rock. What arrives is a ground-borne impulse that comes up through the feet and
shakes the machine hard enough to break the parts of it that are precise.

This is the only mechanism I found where **the thing you hear and the thing that hurts you
are one physical object at two amplitudes.** The glossary's "detectable *before* it is
dangerous" stops being a rule somebody wrote and becomes a fact about the machine.

### 4.2 Distance, rock, water, direction

Two terms, and the whole model is these two lines:

```
gain(θ)  = 0.35 + 0.65 · cos²(θ − aim)         # the array is directional
coupling = gain(θ) · (9 / d)²                   # d = coupled distance, in cells
```

Lethal is `coupling ≥ 1.0`: **9.0 cells on the axis, 5.32 cells at the flank.** There is no
hard edge anywhere else, no second radius, and no threshold in the damage.

**Rock does not shield you, and this is the rule the object exists to teach.** The wave
travels in the massif; the caves are not in its path, so a wall between you and the machine
is not cover, it is more of the same medium. Four cells of rock buys nothing. This
deliberately **inverts** the acoustic layer, where passages, corners and shadow zones are
everything — which is exactly why it is worth a player's attention. There are two ways to
survive the Assayer: be far, or be off the axis. Cover is not one of them.

**Water is a highway.** A flooded working is a continuous, nearly incompressible column
coupled to the rock on every side; the shock runs along it with much less loss. Model it as
**0.35 cost per flooded cell against 1.00 for everything else** on a Dijkstra from the
machine, and take the ratio against the same Dijkstra over uniform cost. That gives a
dimensionless **medium factor** per cell, and `d = |p − machine| × factor(p)`.

Doing it as a *factor* rather than as a grid distance is not fussiness. The project's best
beat is a **0.038-cell** margin, and an 8-connected Dijkstra distance carries up to 8% metric
error plus a cell of quantisation — enough to convert that near miss into a death. As a
factor the field is exactly **1.000 on all land** (measured), and the beat survives to the
third decimal.

Measured on the real cave, from the machine at (140, 86):

| | dry bearings | the flooded `ANC → SUMP` bearing (150°) |
|---|---|---|
| lethal contour (`coupling ≥ 1`, on-axis) | 9.00 cells | 9.00 cells |
| felt contour (`coupling = 0.25`) | 18.0 cells | **32.5 cells** |

**The drawn footprint is visibly lopsided toward the water, every cycle, and the shape is
the explanation.** Two contours are drawn: the lethal one solid, the felt one faint, with the
`Image` between them. That is also the answer to *where is safe* — there is a boundary, it is
drawn, and it is not a circle.

### 4.3 What it damages

Frames survive shock. Precision does not. In order of fragility:

| damage crosses | what breaks | mechanical effect |
|---|---|---|
| **0.20** | the heading reference | `DR_HEADING_BIAS_DEG_PER_CELL` and `DR_SCALE_BIAS` scale by `1 + 1.5·damage`. **`EST_SIGMA_*` does not change** |
| **0.45** | the transponder | `BEACON_RANGE` × `(1 − 0.5·damage)`: 6.0 → 4.5 cells. It starts walking past its own chain |
| **0.45** | the sensor head mount | a fixed **+2.5°** bearing offset on active returns, so the map builds *skewed* and every wall is drawn at an angle to where it is |
| **0.70** | the drive | speed × `(1 − 0.3·damage)` |
| **0.85** | the health monitor | `SelfReport.damage` freezes and never rises again — **the agent stops knowing it is dying.** *Named, not built* |
| **1.00** | the frame | wreck |

**The heading reference first, and that is the whole point.** A shaken agent drifts faster
and its ellipse does not widen to match: it becomes confidently wrong at an accelerating
rate, and nothing on the belief side announces it. The subject of the game arrives as a
**consequence of a physical event a viewer watched**, rather than as a rule. The damage
compounds rather than merely accumulating — drifting faster *and* correcting less often *and*
slower *and* with a skewed map — so what the meter measures is not health, it is lostness.

**Write this next to `HEADING_FIX_GAIN = 0.0`:** damage scales the *truth-side* drift
coefficients and never the estimator's own sigma model. If those two are ever wired together
the mechanic inverts into a warning system, and the loss will not be visible for months. It
belongs beside the existing note, for the same reason that note exists.

### 4.4 The near-miss gradient

Damage is applied **per firing, not per second.** The blow is an instant, so the unit of risk
is the *cycle*: loitering for three minutes is three firings — countable, legible, and it
makes an 80-second interface dwell cost exactly one firing.

```
coupling ≥ 1.0   →  destroyed, one event, no meter
otherwise        →  damage += 0.5 · coupling^1.5      # monotone; never repairs in a match
```

No threshold and no special case: `coupling ≥ 1` *is* `d ≤ 9` on the axis, so requirement 1
is preserved by the same formula that grades everything else.

| coupled distance, on-axis | coupling | damage per firing |
|---|---|---|
| 9.04 | 0.991 | **0.493** |
| 10.5 | 0.735 | 0.315 |
| 12 | 0.562 | 0.211 |
| 15 | 0.360 | 0.108 |
| 18 | 0.250 | 0.063 |
| 24 | 0.141 | 0.026 |
| 45 | 0.040 | 0.004 — the floor; beyond this, nothing |

Off the axis at 90°, multiply by 0.35: 5.3 cells is the kill edge and 9 cells costs 0.104.

**The ratio to defend if anything gets tuned: audible at 80 cells (`HEAR_ANCIENT_RANGE`),
felt at 45, killed at 9.** You can hear it from nearly nine times further than it can kill
you. That is the glossary's promise written as arithmetic.

### 4.5 The two reference beats, checked

Both were run and measured, not assumed. With `ANCIENT_AIM_0 = 41.5°` and a step of −36° per
firing (§5), the aim at the fifth firing (5:41) is 257.5° and at the sixth (6:56) is 221.5°.

| beat | today | under this model |
|---|---|---|
| **5:41** — player at **9.038** cells, bearing 255.5°, medium factor 1.000 | outside a 9.000 disc: **costs nothing** | 2.0° off the axis → gain 0.999, coupling **0.9906** → **survives by 0.038 cells and takes 0.493 damage.** Half the machine, its odometry gone, and it walks on |
| **5:41** — rival at 10.025 cells, bearing 6.6° | nothing | 109° off the axis → coupling 0.367 → **0.111 damage.** *Two bars drop in the same second, inside the one CLOSE frame the director is already parked on. Nothing has to be scripted to get that* |
| **6:56** — rival at **8.121** cells, bearing 221.5° | dies | on the axis → coupling **1.228** → **still dies**, at 89% hull, so the wreck it leaves is a damaged wreck |

The most-photographed frame in the project stops being a coin-flip that landed right and
becomes *the moment the machine was ruined without dying* — which explains the last two
minutes of the match with something the viewer watched happen.

### 4.6 What water does **not** do in Phase 1, and why that is still worth building

`cave.py:109` is `WALKABLE = GRID == 1`; flooded is 2. **No agent can enter water in Phase
1.** Measured: the nearest flooded cell is **10.79 cells** from the machine, there are zero
flooded cells inside 9, and — the number that settles it — **every walkable cell within 20
cells of the machine has a medium factor of exactly 1.000.**

So a receipt multiplier for a submerged agent is dead code this phase, and any claim that
"the sump is the most dangerous place in the cave" is false about the current build. What
water buys in Phase 1 is the **drawn** field: a tongue running 32 cells up the flooded
passage against 18 on dry bearings, every cycle. That teaches the rule before the rule can
bite, and the bite arrives in Phase 3 with the Swimmer on the same one line of cost table.
A rule a player learns by watching is cheaper than one they learn by dying.

### 4.7 The Phase 1 damage meter

**One float on `AgentTruth`: `damage ∈ [0, 1]`, monotone, applied on the firing tick only,
`alive = damage < 1.0`.** `World.step_hazards` already loops the agents and already knows
`is_lethal`; `covers()` becomes `coupling_at(x, y) >= 1.0`. Two multipliers are wired in
Phase 1 — the drift pair and speed — and nothing else.

Three marks, no new widget and no new `Text` in a per-frame path:

1. **The glyph degrades into the wreck it becomes.** `glyph.machine()` draws three hull hatch
   strokes at `f ∈ (−0.55, −0.15, 0.25)`. Drop them front-to-back: 3 above 0.34 damage, 2
   above 0.67, 1 beyond; lerp `BONE`/`EMBER` toward `KILL` above 0.30; halve
   `HEAD_TURN_DEG_S` (`truth_panel.py:37`) above 0.45 and stop it above 0.80. **This is the
   only damage display of the four proposed that reads at `CAMERA_WIDE_CELLS = 225`**, where
   the glyph is nine pixels and no text is legible: a machine that is visibly thinner, redder
   and has stopped looking is read instantly by a stranger with no legend. About ten lines.
2. **One rail row.** `STATUS_LABELS` gains `CONDITION` → `"unhurt"` → `"hurt 51% — odometry
   unreliable"` → `"limping, 22%"`, coloured `TITLE` / `BANNER` / `KILL`. It belongs in the
   rail and not in the world because **it is a belief number**: it arrived through a
   self-report and it can be wrong. Two `Text` visuals, about 0.9 ms.
3. **Nothing else.** The tether already lengthens and will now lengthen faster; that is the
   meter's second display and it was built two slices ago. One `EventKind.HAZARD` event per
   dosed firing gives the feed line and the timeline pip for free, because `timeline.update()`
   already reads the feed.

Prefer this to a world-space bar: a 1.6-cell bar is 50 px at CLOSE and 9 px at WIDE, and WIDE
is where the director sits for most of the match.

### 4.8 What the agent can know about its own damage

`Return::SelfReport { cargo, power, damage: Fx, modules: ModuleHealth, medium }` is already
specified (`PHASE-3-OPEN-QUESTIONS.md:396`). Damage arrives **through a sensor**, so it can
be wrong — that seam should be left open and not built.

- **`damage: Fx` is honest, and coarse.** It is a strain gauge in the frame, and dumb
  analogue things survive shock. A policy can trust *am I hurt*.
- **It supports the two-block tree a player would actually build:** a predicate `hurt(θ)`
  over `self_report.damage`, guarding the existing `return_to_beacon`. *If I am carrying and
  I am hurt, go home.* It is the first predicate in the game whose threshold is a **risk
  appetite rather than a fact** — two players will pick different θ and both are defensible,
  which is what `DESIGN-PRINCIPLES.md` §1 wants a base block to be. And the player meets it
  in play, by watching a machine limp, before composing it.
- **`ModuleHealth` cannot tell it how wrong it now is.** `imu < 1.0` says the dead reckoning
  is impaired; the bias itself is unobservable from inside, because a gyro cannot measure its
  own bias. So the only correct policy response is not "compensate" — that is impossible —
  but *stop trusting distance; get a fix or come home.* A real, transferable robotics lesson
  that falls out of the physics rather than being asserted.
- **The honest tell already exists.** `FixRecord.surprise` is computed today and printed in
  the rail (`view.py:536`: `surprise >= 2.5 and jump >= 8.0`). A machine whose fixes start
  jumping further than its own ellipse promised is a machine whose drift model has gone
  wrong. The counter-play to damaged odometry is already built and needs no new sensor.
- **Do not build a lying `ModuleHealth` yet.** A non-monotonic self-test, where the
  worst-damaged module reports the healthiest, has the right instinct — a self-test is run by
  the part that broke — but the consequence is that the correct policy is to never read the
  field, which forecloses the seam line 396 exists to open. The **freezing** health monitor at
  0.85 is the version to keep, because it removes information rather than inverting it, and it
  is named here and built later.

---

## 5. The behavior, the exploit and the counter

**The behavior.** A survey covers ground. Each cycle it slews the array, fires, and listens
to the return; **the aim advances by 36° per cycle, always the same direction.** That is
learnable from two slews — a player does not need to watch a full revolution to predict the
next bearing, they need to see the step twice — and it means the safe side of the chamber is
safe *for a while*, and then is not. A machine standing at 8.5 cells is outside the lethal
contour this cycle (reach 7.92 at 36° off-axis) and inside it next cycle. In Phase 3 it also
**seeks**: it is a prospecting machine and it aims at the strongest recent anomaly — anything
dense and stationary in the rock, or anything that made a large acoustic event. Phase 1 builds
only the fixed rotation, so what a Phase 1 viewer sees is a machine working its way round its
own claim.

**The exploit — you can point it.** Drop a beacon, and the next slew swings onto it. No new
module, no new action, no weapon: a beacon rack is standard kit and dropping one is already in
the game. Two things this buys, and they are different sizes:

- *At chamber scale, where it is real:* the aim decides **which crescent of the room is
  dangerous** and — because coupling is also the download rate (§6) — **which ground downloads
  fast.** Aiming the array at your own feet roughly triples your download rate at a given
  distance and quintuples your dose. On-axis at 12 cells is a 142-second dwell at 0.211 per
  firing; at the flank at 12 cells it is 406 seconds at 0.044.
- *At corridor scale, where it is not:* aiming down a passage at a rival 18 cells away
  delivers coupling 0.25 and a dose of 0.063 — **a scratch.** I am saying that plainly because
  the temptation to sell this as artillery is strong and the numbers do not support it. It is
  a lever on a room, not a gun.

A second exploit is free and arrives on day one: **the Assayer is a clock and a landmark.**
Nine clicks at 1 Hz every seventy-five seconds from a fixed point is the only thing down there
that is regular, loud and not lying. Working out that the most dangerous object in the cave is
also the only honest one is the good kind of discovery.

**The counter — three, escalating, none of them a weapon.**

1. **Hear the slew and take the flank.** The grind runs three seconds, seventeen seconds
   before anything is dangerous and *before the signature starts*. A policy that stores the
   bearing of the last grind knows the sector before the warning, and the flank is 5.32 cells
   of lethal reach against 9.0 and a third of the dose. **Safe becomes a place — behind it —
   rather than a distance a machine has to estimate**, which is the strongest legibility
   property in the design.
2. **Out-bid the anomaly.** The aim goes to the strongest, most recent anomaly, so a rival
   drops its own beacon and takes the aim back. A bidding war on a seventy-five-second clock,
   decided by proximity and recency, played with objects everybody already carries.
3. **Leave a body.** A wreck is a large permanent anomaly. An agent that dies in the wrong
   place re-aims the machine for the rest of the match, so the loser's corpse changes the map,
   and a player who understands that will occasionally spend an agent to move the machine's
   attention off their extraction route. `DESIGN.html` already makes wrecks load-bearing; this
   is the first mechanic that makes a wreck's *position* matter.

**None of this breaks the stated rule.** `PHASE-3-OPEN-QUESTIONS` is explicit that spoofing
deals no damage and no action in the registry damages another agent. Dropping a beacon damages
nobody; the machinery does, and it does what it always does. This exploit **fulfils** that rule
rather than routing around it — which is the test a mechanic that needs a designer ruling
before it can exist would fail.

**One clamp, written in `step()` and not in a comment:** a provoked cycle may never cut the
warning below **three seconds**. The glossary promises the signature is detectable *before* it
is dangerous, and a provocation that removes the warning voids the contract. This applies to
every provocable ancient, not just this one.

---

## 6. Interfacing, and why an agent risks it

**What it physically does.** It walks up, stops, and **puts its transducer on the rock** —
sensor head down, hard against the floor, and holds still. The Assayer talks in the ground;
that is the only channel it has ever had. It is still trying to file a survey report to an
office that is not there, and it answers anything that knocks back, because as far as it is
concerned you are the office. What comes back is that report: the plant's own control
software. That is why a recovered thing is a predicate or an action rather than a treasure,
and why deeper is better — the deepest machines are the newest, and they were doing the
hardest jobs.

**Interfacing is loud.** Knocking on rock hard enough for a machine to hear is an emission:
an interfacing agent broadcasts a continuous `TONE` at `HEAR_ANCIENT_RANGE`. It is the
loudest, most committed, least deniable thing a machine can do in this game — the reward
channel is a broadcast, which is what gives counter 2 its teeth and puts *do I ping?* at the
one object that hands out blocks.

**The design closes here, and this is the best thing in it: coupling is the download rate and
coupling is the damage. They are the same scalar.**

```
download rate  = min(coupling, 1.0)              # full rate at the lethal contour
damage/firing  = 0.5 · coupling^1.5
dwell required = INTERFACE_S = 80 s at full rate           (unchanged)
```

| station | rate | dwell | firings sat through | total damage | you leave with |
|---|---|---|---|---|---|
| 9.04 cells, on-axis | 0.99 | 81 s | 2 | 0.99 | dead, or nearly |
| 10.5, on-axis | 0.73 | 109 s | 2 | 0.63 | 37% hull, fast |
| 12, on-axis | 0.56 | 142 s | 2 | 0.42 | 58% hull |
| 15, on-axis | 0.36 | 222 s | 3 | 0.32 | 68% hull, and three minutes gone |
| 12, at the flank | 0.20 | 406 s | 6 | 0.26 | 74% hull, and the match is over |

**Closer is faster and costs hull; further is cheaper and costs match.** There is no dominant
answer, and the right one depends on how much clock is left and how much you already carry.
The risk is not incidental to the reward — **it is the same act.** You cannot download without
being coupled, and being coupled is how it hurts you.

Three things make that a decision rather than arithmetic:

- **`INTERFACE_S = 80` and the period is 75.** Even at the maximum possible rate you cannot
  complete a download without being present for a firing. That number was chosen for a
  spectator beat before any of this existed; the fiction now makes it the central puzzle.
- **The dwell is resumable** — it is a transfer with a cursor — so stepping out for the four
  lethal seconds costs only time. But the walk out and back is about twenty seconds a cycle,
  and **because the aim indexes 36°, the station that was fastest this cycle is not the
  fastest next cycle**, so a stepping-out agent must also move round. Stand and eat one
  firing: 81 s and half your hull. Step out each cycle: about 120 s and nothing. Neither
  dominates.
- **The report is finite.** `yields()` returns `None` once it has been taken, so one machine
  yields once per match. The machinery is contested rather than shared, a second team arriving
  late has something to have lost, and squatting the good ground is a real counter rather than
  a nuisance.

**What the screen shows.** The machine stops and **its sensor head folds down and stops
turning** — in `glyph.py` the head is the one mark that says *alive and still looking*, so
killing its rotation reads instantly as *doing something deliberate, and not watching*. A thin
`CARGO`-green line runs from the glyph to the floor and a progress arc fills around it in the
same green — because a block *is* the objective, and green touches the machinery nowhere else.
The emitted `TONE` draws as the existing sound rings, once a second, so the viewer sees the
whole cave being told. And the arc and the machine's own nine clicks are on screen together,
in the same 40-cell frame, both counting. Nothing needs saying.

---

## 7. What it explains about the world

- **Why the deposits are where they are.** The Assayers found the ore and said so; the crews
  followed the survey. What lies on a chamber floor is broken stock and spoil left where the
  survey said to dig — which is why value is in loose, gatherable piles rather than locked in
  a wall, why a cargo bay and thirty seconds is all it takes to load, and why
  `DEPOSIT_RADIUS = 12` is right: a heap is big and diffuse, not a point.
- **Why the richest ground is the worst ground.** You can only work below the water table
  where you can keep the water off, so the deepest ground is the wettest is the ground that
  needed the biggest machines. `DESIGN-PRINCIPLES.md` §2's loot-by-depth stops being an
  abstract gradient: **the best blocks sit next to the worst hazards because of a mining fact,
  not a game rule**, and the loot table becomes the survey's own chronology — it worked
  downward and got better as it went.
- **Why there are tunnels at all and why they go where they go.** Chambers are stopes,
  passages are drives driven along the survey lines, and `C3 → ANC` exists because crews had
  to reach the machine to service it. A cellular-automata cave acquires a reason to be
  chambers-joined-by-passages rather than blobs.
- **Why `ROUTES` exists.** The prior industry's own maps are the intel the modern teams launch
  with. The player's waypoints are somebody else's work.
- **Why the workings are flooded, and why the machine is still running.** The pumps stopped
  when the industry left. The water that drowned the mine is the water that fills the
  Assayer's header tank — **the mine's failure is the machine's power supply**, which is how a
  thing with no fuel and no store is still hammering after everybody went home. The
  seventy-five-second period is how long the tank takes to fill.
- **Why the rock is magnetically noisy and a compass is useless.** The workings follow an ore
  body, ore disturbs the magnetics, and the arrays are large magnetic installations sited *on*
  the ore — so false anomalies cluster exactly where the true ones are. **The reason to go in
  and the reason you get lost are the same rock.** That is the premise of the whole game
  explained by the object at the middle of it.
- **Why the ruins are here.** A works, not a temple. There is no lost civilisation to write:
  there is a mine that outlived its owners because it was built to run untended. Your agents
  are the same idea, worse.

It does not explain thermal layering or shadow zones, and should not try.

---

## 8. Two siblings, for Phase 7

The kind is *still executing a job, harming as a side effect*. Each sibling is a different
physical channel, hooked to a different world axis, with a different distance rule and a
different casualty part — one trait, no new machinery in the type system.

- **THE HAULAGE** — an ore train, still hauling, on a fixed rail circuit of several minutes.
  Its hazard is **a line, not a region**: the road. Approaching sound is the warning and you
  step off the rail. Its exploit is that it is a **ride** — an agent that mounts it covers real
  distance with **no odometry error, because it is not walking**, and makes no noise of its
  own, which is the only mechanic proposed anywhere that attacks the game's own currency
  rather than spending it. Its counter is that a rival who knows the route knows where you
  must get off, and the road runs past the Assayer.
- **THE BUS** — a conductor running the length of the workings, energised on a duty cycle to
  drive haulage that no longer exists. Its hazard is **current, carried by wet rock and
  standing water and by nothing else**, so a dry passage two cells from the conductor is safe
  and a flooded chamber forty cells away is not: the only hazard proposed whose entire reach
  *is* the flooding axis. What it damages is the estimator itself and any beacon left in the
  water, which come back **wrong rather than dead**.

Find an Assayer and there is a Bus under it and a Haulage between them. The generator can
place a *mine* rather than a scatter of traps.

---

## 9. The Phase 3 shape

```rust
// content: AncientKindId(1) — assayer.  §29 reserves id 1 as `fixed_cycle`; this is a rename
// of that slot, because the next two kinds are also fixed-cycle and the label carries nothing.
pub struct AssayerState {
    pub phase:   Ticks,                     // 0..1500 @ 20 Hz
    pub aim:     Fx,                        // the survey azimuth
    pub slew_to: Fx,                        // set at the slew tick; the tell
    pub clicks:  u8,                        // 0..9, the winch ratchet
    pub factor:  MediumFactorId,            // the cached medium field; rebuilt only when water moves
    pub dwell:   BTreeMap<AgentId, Ticks>,  // interface progress, resumable; BTreeMap for order
    pub spent:   bool,                      // the report is finite: one yield per match
}
```

**`kind()`** → `AncientKindId(1)`.

**`signature(&s)`** → `None` for the quiet fifty-four seconds. `Some(AcousticSignature {
character: Tone, level: 0.25, .. })` for the three-second slew — *this is the counter's whole
mechanism and it is `signature()`'s only genuinely new obligation.* `Some(Signature, level:
0.3 + 0.7·clicks/9)` across the wind and `1.0` while firing. The signature carries
`directivity: Option<Lobe { aim, floor }>` and the acoustic layer applies it, because the
emitter is directional and only the listener's bearing is known there. That one field means
**the agent about to be hit hears it loudest, and the existing thresholds already respond with
no new code**: `ANCIENT_HOLD_QUALITY = 0.45` (the cautious agent freezes) and
`INTERFACE_QUALITY = 0.60` (the aggressive one commits) are both thresholds on quality. The
aim reaches belief through a number that already exists.

**`step(&self, s, w, rng)`** → advances `phase`; at the slew tick sets `slew_to` (Phase 3:
`aim − 36°`; Phase 7: the strongest recent anomaly's bearing, else the rotation) and rebuilds
`factor` if the cave's water changed; pushes each ratchet click into `w.acoustics`; at the
firing tick opens the hazard window; credits `dwell` at `coupling` per tick for any agent whose
`current_action` is `Request::Interface`. The only world reads are `w.presences` and
`w.acoustics`, so §32's recommended `WorldView` is sufficient — a point in its favour. Phase
7's anomaly scan wants one narrow addition (`anomalies: &[Anomaly]`), **not** a widening to
`&World`. **`rng` is never drawn from.** A deterministic ancient that consumes RNG is a bug;
the parameter exists for kinds that scatter debris.

**`hazard()` — the one type change, and it is the reason the machinery is a disc today.**

```rust
fn hazard(&self, s: &AncientState) -> &[HazardVolume];      // was Option<HazardVolume>

pub struct HazardVolume { pub origin: Vec2Fx, pub field: HazardField, pub effect: HazardEffect }

pub enum HazardField {
    Radial    { radius: Fx },
    Conducted { reach: Fx, aim: Fx, lobe_floor: Fx, medium: MediumFactorId },
}
pub enum HazardEffect {
    Crush { lethal: bool },
    Shock { lethal_at: Fx, hull: Fx, curve: Fx, imu: Fx, active: Fx, drive: Fx },
}
```

During the four-second window it returns one volume — `Conducted { reach: 9, aim: s.aim,
lobe_floor: 0.35, medium }` → `Shock { lethal_at: 1.0, hull: 0.5, curve: 1.5, .. }` — and
otherwise an empty slice.

`Option<HazardVolume>` (`ARCHITECTURE.md:129`, `ROADMAP.md:301`,
`spikes/ARCHITECTURE-RECONCILIATION.md:905`) returns at most one region with one effect and can
only answer *inside or outside*. **That is the type-level reason a near miss costs nothing
today**, and it forecloses every one of the four questions the designer asked. All four
proposals hit this wall independently. Two constraints on the replacement: it must be **data,
not a closure** — a closure cannot be hashed for the desync canary and is hostile to the
fixed-point rule (`DETERMINISM.md`; Definition of Done item 3) — and it must carry a *graded*
effect rather than a boolean. **This is a Phase 3 open question that should be settled before
Phase 3 starts, and it is worth more than the choice between fictions.**

**`provocable_by()`** → `&[]` in Phase 3, exactly as §1362 plans; Phase 7 fills it with
`ProvocationKind::Anomaly { Beacon | Wreck | Cargo }` and `ProvocationKind::Emission(..)`. The
aim machinery is written in Phase 3 with the fixed rotation and the anomaly scan behind a
content flag, so Phase 7 is a data change and not a rewrite.

**`yields(&s)`** → `Some(Yield { block: BlockId::Predicate(SHOCK_IMMINENT), dwell: Ticks(1600) })`
while `!s.spent`, `None` after. `dwell` is the nominal dwell at rate 1.0; the variable-rate
accounting lives in `step()`, so §33 and §16 need no amendment. The first block it hands out
should be the one that teaches you about itself — a predicate over `Bearing.character ==
Signature && quality > θ`. **The first thing the ruins teach you is how to survive the ruins**,
and per `DESIGN-PRINCIPLES.md` §1 there is no better introduction to a block than surviving the
thing it protects you from.

**The truth channel.** The coupling field reaches the renderer as `coupling: np.ndarray` on
`StageAncient` — `match/invariant.py:63` lists `ndarray` in `PLAIN_TYPES`, so rule 7 permits it.
**Do not reuse `sensing.SoundField` from the view side to draw the footprint:** `sensing`
imports `truth.cave`, and that hands the renderer `cave.GRID` at module scope. That is exactly
the class of leak `CLAUDE.md`'s one invariant exists to stop, and the hole rule 4 was written
after. The field is aim-independent — `gain(θ)` is a per-cell multiply — so it is one Dijkstra
per match and six numpy multiplies.

---

## 10. What it costs, and what it does not solve

### 10.1 The build

| work | file | days |
|---|---|---|
| the form: footing, mast, boom, ribs, counterweight, hammer, drop line, bolt ring — **one static mesh under an in-place `MatrixTransform`**, hammer on an `STTransform` | `view/assayer.py` (new) | **1.25** |
| aim, slew, the nine-click wind, the fall, the recoil | same | 0.35 |
| the medium-factor Dijkstra, `coupling_at`, damage application; the kill test moved from `covers()` to `coupling ≥ 1`; `coupling` onto `StageAncient` | `truth/ancient.py`, `truth/world.py`, `match/stage_builder.py` | 0.6 |
| `damage` on `AgentTruth`; the drift pair and speed wired truth-side; damage onto `StageMachine` and into the rail | `truth/`, `sensing/`, `belief/` | 0.3 |
| the floor lobe as an `Image` plus the lethal and felt contours; **delete the dormant ring**; keep the countdown | `view/truth_panel.py` | 0.5 |
| the permanent scour in the floor image | `view/cave_mesh.py` | 0.1 |
| glyph degradation, colour lerp, head turn, the folded head while interfacing | `view/glyph.py`, `view/truth_panel.py` | 0.25 |
| the `CONDITION` rail row and the `SHOCK` feed event (the timeline pip comes free) | `view/view.py` | 0.15 |
| audio: the slew grind, the ratchet driving `signature_pulse`, the impulse | `audio/mixer.py` | 0.3 |
| the director cuts on slewing as well as on signature | `view/director.py` | 0.1 |
| **re-watch seed 7 and sweep `ANCIENT_AIM_0` across the eight tuning seeds** | — | **0.75** |
| | | **4.65** |

`mixer.signature_pulse` (`audio/mixer.py:119`) already pulses faster and rises in pitch with
`strength`. Driving the pulse from the ratchet rather than from an abstract ramp turns a siren
into a machine, and it is one argument changed.

### 10.2 What to build, and where to stop

`CLAUDE.md` is explicit that Phase 1 is throwaway and must not be engineered. **Build about 3.9
days of the above and stop.** Cut deliberately: `ModuleHealth` and the module ladder, the
transponder and sensor-head effects, the anomaly seeking, `provocable_by`, the rock-type
coefficient, the submerged receipt multiplier, and the resumable-dwell bookkeeping. Every one
of those needs either the Phase 3 generator, a second agent per side, or an authored policy
before it can be tested, and building them against a prototype is the engineering the phase
forbids. For the same reason the slew is **view-side audio and motion only** in Phase 1: making
it a real `Tone` emitter would add contacts to both tuned policies' logs and change behaviour
this phase is not testing.

What survives the cut is exactly what the designer asked for: a machine that visibly does
something, a warning that is a physical event, harm with a mechanism and a gradient, and a
meter.

If only two days exist: **the form, the nine-click wind, the damage float and the glyph mark.**
That answers both halves of the note and nothing else.

### 10.3 What it does not solve

- **The rival still cannot reliably reach the machinery.** This run logged `no progress toward
  ANC; wall escape` four times and `cannot reach ANC; skipping` at 6:04. `tuning.py` already
  records the rival reaching ANC on 5 of 8 seeds and blames the `C3 → ANC` passage. A better
  machine does not fix a navigation stack, and on three seeds in eight this is scenery.
  **Nothing here touches it, and it is the single biggest threat to the beat.** In its favour:
  coupling has no pedestal and no contact point, so *arriving* is no harder than it is today —
  the agent couples to the floor wherever it happens to stop.
- **The player's 79-second jam from 6:40 is untouched.** The worst dead air in the match is not
  a machinery problem.
- **The exploit and the counter cannot be played in Phase 1.** They need two agents on a side
  or an authored policy. Phase 1 ships the behavior and the price; §5 is designed here and
  exercised in Phase 7, and there is no way to shorten that gap.
- **The drift consequence is real but modest on this seed.** The player's only dose lands at
  5:41 with 139 seconds of match left. At 0.493 damage the heading bias goes 0.11 → 0.192
  °/cell, which over roughly 150 cells of remaining travel adds about **16 cells** of lateral
  error on top of an error already running 64 → 91. Measurable on the error trace; not
  spectacular. The mechanic wants a dose *early* in a match to really bite, and on seed 7 it
  does not get one. The glyph and the rail row are what carry it here.
- **Attribution is not solved**, and `ROADMAP.md` already lists it as known-weak. A machine
  extracting at 40% with a wrecked heading reference must be able to say *which firing* did it,
  or the meter reads as arbitrary and the player learns nothing. One timeline pip per dosed
  firing is the minimum answer and is probably not sufficient.
- **Six cycles is enough to teach the index; thirty seconds is not.** The rotation, the flank
  and the countable clicks all want two or three cycles. Fine for an eight-minute gate video,
  not fine for a trailer.

---

## 11. The riskiest assumption

> **Measured 2026-09-07, and it retires the first of these.** The worry below — that a pointing
> hazard silently deletes a death on a seed nobody swept — was answerable from the sim as it
> stands, with no implementation and no fitting, by recording every agent's closest approach
> during every lethal window across seeds 1–8 and asking what a cos² lobe would do at *every* aim
> origin. Result: there are **three deaths in eight seeds, all of them the rival**. Two (seed 1 at
> 3.38 cells, seed 5 at 3.80) are so deep inside that they die *at any angle* — the lobe cannot
> save them. Only seed 7's, at 8.12 cells, is angle-sensitive, and it dies anywhere within 32° of
> the axis. Over all 72 aim origins the lobe keeps a minimum of **2 of 3** deaths and never fewer;
> 26 of the 72 keep all three. So direction risks exactly one marginal kill at the rim, and the
> case it removes is the one where "it was on the flank" is the right answer rather than a loss.
> `ANCIENT_AIM_0` is chosen from the 26, not fitted to a beat. Script:
> `scratchpad/lobe_sweep2.py`, reproducible.


**The one I most want overruled, because it is the one that costs money: that direction should
be load-bearing in Phase 1 at all.** The lobe is what stops the object being a circle, it is
what makes *safe* a place rather than a distance, and it is the whole basis of the exploit and
the counter. It is also the only thing here that (a) needs a fitted constant —
`ANCIENT_AIM_0 = 41.5°` was chosen on seed 7 to put the fifth firing's axis on the player and
the sixth on the rival, which is fitting the world to the video, exactly as `ANCIENT_PHASE_S =
30` already was — and (b) can **delete a death on an unswept seed**, because an agent inside 9
cells but off the axis now lives where today it dies. In a video judged by a stranger, deleting
the only kill is a direct legibility loss, and it is the 0.75 days of sweeping.

The fallback is one constant and it is genuinely good: **`lobe_floor = 1.0` collapses the gain
to unity**, and what ships is a graded, water-distorted, visibly lopsided field with the lethal
contour at exactly 9 cells in every direction — today's disc, with a near miss that now costs
half a machine, zero fitting and zero seed risk. What is lost is the flank as a *place*, and
with it the counter and most of the exploit: the boom still slews and still points, but it
points at nothing. Say the word and I will build it that way, draw the lobe, and turn direction
on in Phase 3, where the sweep is a generator concern rather than a hand-authored cave.

**The riskiest assumption I cannot buy my way out of: that a stranger reads the degraded
odometry as a consequence at all.** Everything that makes this better than a health bar depends
on a viewer connecting *the machine took a shock at 5:41* to *its map fanned open faster
afterwards*. Drift already lengthens the tether for other reasons, and 16 cells on 91 is not a
large signal. The cheapest test is a one-off instrumented A/B — same seed, damage effects on and
off, the two error traces on one plot. If they are not obviously different by 7:00, the odometry
effect should be cut and damage should cost speed and sensor range instead: legible, much less
interesting, and honest.

Everything else I guessed at, listed because `CLAUDE.md` requires it: the 54/3/5/9/4 split of
the established seventy-five seconds; the 36° index step; the 0.35 lobe floor;
`0.5 · coupling^1.5` and every constant in the damage ladder; the 0.35 water cost, and that the
mechanism is shock through rock rather than anything radiated; that the heading reference goes
first and that the estimator's sigma model does not learn about it; that interfacing is contact
with the floor and that its rate is the coupling; that `hazard()` should return a slice of
graded volumes; that the day-one yield is `shock_imminent`; and that the report is finite, so
one machine yields once per match.

---

## Appendix A — the `GLOSSARY.md` replacement, ready to paste

> **Ancient system** — a machine of the prior industry, still running its program in the ruins.
> It harms as a side effect of doing its job rather than as a trap: it is not hunting you, you
> are standing in its work. Deterministic — a fixed cycle, an acoustic signature that is
> detectable *before* it is dangerous, a behavior a player can learn, an exploit and a counter.
> Harm is **graded and physical**: a named channel (ground shock, current, pressure, moving
> water), a falloff that the cave's own axes distort, and a part of the agent it damages first.
> Instruments break before frames, so a machine usually leaves an encounter ruined rather than
> dead — and a machine whose odometry is hurt drifts faster without knowing it. Interfacing with
> one is how new base blocks are recovered (`yields()`), and the interface sits **inside** the
> harm, so the reward and the risk are the same act. One system is one instance of a *kind*, and
> kinds have siblings, each on a different physical channel. Not a random hazard, and not a
> guardian.

## Appendix B — what changes in `tuning.py`

**Unchanged, deliberately:** `ANCIENT_PERIOD_S 75`, `ANCIENT_WARNING_S 9`, `ANCIENT_LETHAL_S 4`,
`ANCIENT_RADIUS 9`, `ANCIENT_PHASE_S 30`, `INTERFACE_S 80`, `INTERFACE_QUALITY 0.60`,
`ANCIENT_HOLD_QUALITY 0.45`, `HEAR_ANCIENT_RANGE 80`, `HAZARD_COUNTDOWN_FROM_S 15`, and every
`CAMERA_*` constant including `CAMERA_HAZARD_WATCH_CELLS 15`. **`ANCIENT_RADIUS` keeps its value
and changes its meaning:** it is the on-axis lethal contour and the drawn boundary, and the
`in_ancient` zone flag that the director and the log read stays a plain 9-cell disc, so the
camera behaves exactly as it does today. Change what 9 *means*; do not change 9.

**New:** `ANCIENT_AIM_0_DEG 41.5`, `ANCIENT_AIM_STEP_DEG −36.0`, `ANCIENT_SLEW_S 3.0`,
`ANCIENT_LOCK_S 5.0`, `ANCIENT_LOBE_FLOOR 0.35`, `ANCIENT_WATER_COST 0.35`, `ANCIENT_DOSE_K 0.5`,
`ANCIENT_DOSE_CURVE 1.5`, `DAMAGE_DRIFT_GAIN 1.5`, `DAMAGE_SPEED_LOSS 0.3`,
`ANCIENT_MAST_CELLS 11.0`, `ANCIENT_BOOM_CELLS 7.0`.
