# Sound design

2026-09-09. The game's sound, as a design document rather than an asset list. Written against
what `phase1/audio/` actually does — about 1,100 lines of synthesis with real decisions in it —
and against `CLAUDE.md`'s invariant, `DESIGN-PRINCIPLES.md` §8 and §9, `THE-MACHINERY.md`,
`docs/spikes/ACOUSTIC-BUDGET.md` and `ART-DIRECTION.md`.

`ART-DIRECTION.md` is 1,346 lines and contains no audio section. This is the other half of it.
Where the two overlap, the parallel is stated explicitly, because the visual layer has already
solved several of these problems and the answers transfer.

**Marking convention, used on every claim in this document.**

| mark | means |
|---|---|
| **[BUILT]** | it exists and runs in `phase1/` today. File and constant named. |
| **[DESIGNED]** | a repo document specifies it and no code implements it. |
| **[PROPOSED]** | mine. Nothing in the repo says it. |
| **[GUESS]** | a number or a fact I could not check. Every one is repeated in §10. |

Costs: the sim runs at 20 Hz and is deterministic; **audio is entirely client-side**, so nothing
here is bound by `DETERMINISM.md`. What binds it is a frame. Numbers are given per sound.

---

## 1. Whose ears is the player using

### 1.1 The answer

**The machine's. Always, in the live view, with no toggle and no exception except the machine's
own body.** The player hears what their machine's sensors received and their machine's estimator
placed. Not what happened.

This is not a proposal. It is what the code does and it is already a stated invariant:

- `phase1/audio/__init__.py`: *"Directional audio. Reads Belief only."*
- `phase1/audio/mixer.py`: *"Directional audio, driven entirely from Belief."*
- `Mixer.update(b, t, camera_azimuth)` takes a `Belief` and a float. There is no other input.
- `SPECTATOR-DISPLAY.md` §4.2 rule 3 makes it a tripwire with a stated reason: *"`view` and
  `audio` may not import `truth`. `audio` is on the list deliberately: a room tone or hazard drone
  driven from truth would tell a player how close the machinery really is, through a channel that
  scanning `view` alone would never inspect."*

What has never been written down is what follows from it. Four things follow, and they are the
most valuable things this design has.

### 1.2 The four consequences

**(a) The player's stereo field is wrong, and it gets wronger.** `HeardSound.bearing` is *"world
bearing in the belief frame."* The belief frame's heading drifts — `phase1/tuning.py:54`,
`HEADING_FIX_GAIN = 0.0`, with the note *"Heading drift is now uncorrected for the whole match,
which is the honest consequence: the map fans open and nothing straightens it."* So every bearing
the player hears is rotated by an error that accumulates all match and is never corrected. **The
stereo image slowly rotates away from the world over eight minutes, and neither the player nor the
machine can tell.** [BUILT, and undocumented until now.]

The corollary is important and cuts the other way: **a fix does not rotate the stereo field today**,
because `HEADING_FIX_GAIN` is zero, so `Contact.rotate()` is a no-op and a spoof is a pure
translation of the map. A translation changes no bearing. When heading correction returns — terrain
matching, or the SLAM module `THE-SENSOR-AND-SLAM.md` §3 discusses — a fix *will* swing the whole
acoustic world at once, and that will be the most dramatic thing this game's audio ever does. It is
not available yet and this document should not pretend it is.

**(b) When the machine is spoofed, the player is spoofed — and the tell is that there is no tell.**
`mixer.py`, opening docstring: *"What it deliberately does NOT do is distinguish an honest fix from
a lie. Both play the same two notes. The only tell is how far the estimate moved."* The lie at
seed 7's 2:21.4 plays `Mixer.fix()` — 660 Hz then 990 Hz, dry, centred, 0.042 amplitude — which is
the same chime as every honest correction in the match. **The most violent event in a Phase 1 match
sounds exactly like routine housekeeping.** [BUILT]

That is the exact audio counterpart of `ART-DIRECTION.md` §6.3: *"A spoofed beacon is
pixel-identical to an honest one. No tell. Not a subtle one. … The renderer must not leak what the
types refuse to."* **The mixer must not leak what the types refuse to** is the same rule and it
should be written in `mixer.py` in those words.

**(c) A sound the machine's sensors missed does not exist for the player.** Three mechanisms, all
built:

- `SELF_DEAF_AFTER_PING_S = 1.0`. The machine is deaf for a second after its own transmission
  (`sensor_rig.py:61`), so is the player. A rival who pings inside that second was never there.
- Range. Motion at 40 path-cells, machinery at 80, pings and crashes at 170 — **path length through
  passages, not line of sight.** Past that, silence.
- The loadout. `SENSORS-AND-IDS.md` D6: passive acoustic is a **module** (`passive_array`), not
  intrinsic. *"An agent that drops the array to carry a second cargo bay is deaf — no contacts, no
  ancient warning, no crash."* **The player buys their own ears at the loadout screen, and can
  choose not to.** [DESIGNED, Phase 3.]

**(d) The spectator can see truth and cannot hear it.** `phase1/view/truth_panel.py` draws the cave
as it really is. `phase1/view/view.py:357` feeds the mixer `self.b` — the player's belief — and
`self.view.camera.azimuth`, which is the **belief** camera, not the truth camera
(`SPECTATOR-DISPLAY.md` §11 note 6 records that decision and its reason). So on the same screen,
at the same instant, the picture is truth and the sound is belief, and **the disagreement between
them is the subject of the game.**

Note the asymmetry with the visual layer, because it is not a small one. `ART-DIRECTION.md` §8.3
gives three modes — truth only, belief only, both — and *"Truth is rendered. Belief is drawn."*
**Audio has one register and it is belief. There has never been a truth register and nobody has
designed one.** §1.4 is about whether that is right.

### 1.3 Why it is right, tested by reversing it

Three things break if the mixer is fed World, and the first is fatal.

**1. The player and the machine stop looking at the same instrument, and teaching dies.**
`machinery_audible` is a day-one base block (`phase1/blocks.json`, stage 3) whose raw value is *the
signature's quality*, and quality is `(1 − path/80) × strength` — path length, not distance. A
truth-driven mixer would place the machinery at its **true** distance. The player would then hear
the hazard at nine metres, teach a threshold against that impression, and the machine would evaluate
a completely different number. The player's evidence and the machine's evidence must be the same
evidence or the whole authoring loop is built on a mismatch. **This is the argument. The other two
are decoration.**

**2. The spoof, the drift and the whole belief layer become visual-only.** Every acoustic
consequence of a wrong estimate — the rotating field in §1.2(a), the frame swing in §1.2(a) when
heading correction returns, the identical chime in §1.2(b) — exists only because sound comes through
the estimator. Feed the mixer truth and the estimator stops being audible at all.

**3. It creates a second, unaudited door out of `World`.** `SPECTATOR-DISPLAY.md` §4.2 already says
so and gives the mechanism: a drone driven from truth leaks the hazard's real distance through a
channel nobody inspects when they audit the renderer.

### 1.4 The cost of being right, stated plainly

**The mixer is an instrument readout with a stereo field. It cannot render a place.** A drip thirty
cells away that nothing sensed is not in `Belief`, so it cannot be in the mix. That is why
`mixer.py` says *"No ambience is added anywhere — a bored viewer is not fixed by a drone."* The
statement is correct and the reason given for it is the wrong reason: ambience is not absent because
drones are boring, it is absent because **there is no legal source for it.** §4.6 proposes the one
legal source there is.

### 1.5 The one exception, and its guard rail

**The machine's own body is not a world observation.** It is known by construction: a real machine
knows what its own motors did without sensing them. `MotorCmd` and `SelfReport` are both belief-side.
So:

> **The client may sound anything the machine itself did, and nothing the machine did not sense.**

That is exactly the split `own_ping()` and `heard_ping()` already make. It should be written down as
the rule instead of surviving as an accident, because the next person to touch this file will either
delete the body sounds as a leak or use the exception to smuggle in a room tone.

**The guard rail.** Own-body sound is **dry, centred, and never placed in the room** — no
`Placement`, no reflections, no pan. The moment somebody wants the footfall to be occluded by real
geometry or to reverberate off the real chamber, they need `World`, and the exception has become the
leak. Dryness is not an aesthetic choice here; it is the enforcement mechanism. It also happens to be
right: a dry centred sound reads as *inside the hull*, which is where the player is. [BUILT for the
panel — `AUDIO_PANEL_AMP = 0.042`, no `Placement` call in `fix`, `recall_sent`, `recall_received`,
`cargo_changed`. PROPOSED for feet, servos, gait and damage.]

### 1.6 Live, replay, spectator — three views, three answers

| view | what it hears | why |
|---|---|---|
| **live player** | one machine's belief. No toggle. | The player's only live input is Recall. Truth audio would be information they cannot act on, arriving through a channel that makes their teaching wrong. |
| **replay** | belief by default; a labelled, non-default **difference** layer. **[PROPOSED]** | See below. |
| **public spectator** (Phase 6) | one chosen machine's belief, switchable between machines, never a mixed god-ear. **[PROPOSED]** | The drama is a point of view. A spectator hearing every machine at once hears a crowd and learns nothing. |

**The replay proposal, and why it is not simply "add a truth track".** Phase 5's gate is *"Replay
with both layers drawn together — this is the most important screen in the game"* (`ROADMAP.md`),
and the forensics layer's job is *why did it die*. Half of those answers are **"it never heard the
thing"** — and you cannot demonstrate an absence with an absence.

So the replay's second layer is not a full truth mix. It is a **difference mix: only the arrivals
`World` generated that `Belief` never received.** The rival ping that landed in the deaf second. The
motion at 44 cells against a 40-cell range. Everything, if the loadout had no array. Played in a
distinct register (§5.9), on a track the viewer switches on deliberately, labelled as what it is.

Then the thing the machine missed **is a sound**, and the player can hear their loadout being wrong.

Cost: the sim must record culled arrivals, which is a `MatchRecord` change, not a client one. It is
cheap — an arrival is a bearing, a quality, a character and a tick — but it is not free and it is
sim-side. [PROPOSED]

---

## 2. Sound is a sensor channel, not atmosphere

### 2.1 The arithmetic, and it is not close

At `ART-DIRECTION.md`'s 0.6 m/cell — which that document flags as a **[GUESS]** and as designer
question 2, so every metre below inherits it:

| | reach | turns corners |
|---|---|---|
| work lamp, floor | ~6 m / 10 cells | no |
| work lamp, walls | ~20 m / 33 cells | no |
| **median sightline in the whole cave** | **3.6 m / 6 cells** | — |
| longest sightline anywhere in the cave | 49.8 m / 83 cells | — |
| lidar | 18 cells, stops dead at water | no |
| sonar | 30 cells | no |
| hearing: a rival walking | **40 path-cells** | **yes** |
| hearing: the machinery | **80 path-cells** | **yes** |
| hearing: a ping, a death | **170 path-cells** | **yes** |

`ART-DIRECTION.md` §3.6 measured that 90.8% of all directions in the cave are blocked under 12 m and
concluded *"Spend no art budget past 15 m"* and *"The wide shot is a schematic. The close shot is a
photograph. There is nothing in between."*

**Sound is the in-between.** A ping reaches twice the longest straight line that exists anywhere in
the cave, and twenty-eight times the median one, and it does it round corners. On the numbers, this
is not a game with an audio layer. **It is a game played almost entirely by ear, with a torch.**

One correction to `ART-DIRECTION.md` line 771, which is the only cross-channel claim in that
document: *"sound is faster than sight, so the glow arrives after the noise."* Sound is not faster
than light. What is true, and is the stronger claim, is that **sound arrives from places light
cannot reach at all** — round the bend, past the fall, up the flooded drive. The haulage's noise
precedes its glow because the noise comes round the corner and the glow does not.

### 2.2 What a machine can learn only by listening

1. **That it is not alone.** `contact_heard` is the *first* found block in the game
   (`WHAT-HAPPENED-HERE.md` §4.2, depth band 1, the hoist signal box): *"the first thing this world
   tells you is that you are not alone in it."*
2. **Where the machinery is, long before it can see it.** `THE-MACHINERY.md` §4.4: *"audible at 80
   cells, felt at 45, killed at 9. You can hear it from nearly nine times further than it can kill
   you."*
3. **That somebody died.** 170 cells, and in an extraction game a crash means a wreck holding cargo
   and a policy.
4. **That the machinery has fired, and therefore the phase of a 75-second clock it will keep for the
   whole match.**
5. **Where a passage runs.** This is the underused one. `sound_field.py`: the arrival bearing is
   taken by walking five cells back along the shortest path, *"so it points down the passage rather
   than at the source through rock."* **A sound bearing is a passage bearing.** A ping heard from
   210° where the believed map says wall is direct evidence of an opening the machine has not
   mapped. Nothing in the game currently uses this and it is the single richest unexploited signal
   in the design. [PROPOSED as a belief signal; the geometry is [BUILT].]

### 2.3 What it announces by being heard

| emission | range | duration | who hears it |
|---|---|---|---|
| **sonar ping** | 170 cells | `SONAR_AUDIBLE_S = 3.0` | every passive listener in range |
| lidar sweep | — | — | nobody; optical only, a line-of-sight tell |
| **motion noise** | 20 / 40 / 100 by chassis; **more in water** | continuous | everything within range, always |
| **interfacing / download** | `HEAR_ANCIENT_RANGE` (80) | the whole 80 s dwell | *"the whole cave hears you take it"* |
| **dying** | 170 cells | once | everything |
| beacons | none | — | nobody (`PHASE-3-OPEN-QUESTIONS.md` §10) |

Three of these deserve saying out loud.

**Sonar is not a sensor with a cost. It is a transmitter that happens to return a map.** It reaches
170 cells and maps 30. The instrument you carry to see 30 cells announces you to 170.

**Motion noise cannot be switched off.** `CHASSIS-TIMING.md`: 20 cells for a Scout, 100 for a
Hauler — *"audible across half the cave"* — and gaits scale it (BLD-100). And D8: *"Sound in water
is louder, not quieter. A Swimmer moving in flooded passage is heard further than a walker at the
same emitter range. 'Unmatched below the waterline' is about access, not stealth."*

**The reward channel is a broadcast.** `WHAT-HAPPENED-HERE.md` §4.3: *"Coupling is the download rate
and coupling is the dose. The reward channel is a broadcast at `HEAR_ANCIENT_RANGE` and the whole
cave hears you take it."* `ART-DIRECTION.md` §6.2 says the same of salvaging a wreck: *"Recovery is a
machine standing over a corpse with its head down, doing nothing visible, for a long time, while the
whole cave can hear it. Do not put a glowing brain in it."* **The art direction has already assigned
the two most valuable acts in the game to the audio layer, and the audio layer has no sound for
either.** [DESIGNED, unbuilt.]

### 2.4 Making the exposure audible — two changes, both cheap

**(a) Your own ping's tail should last exactly as long as you are audible.** `own_ping()` builds a
0.30 s transmission plus four wash voices of 0.55 s at delays out to 0.75 s — about 1.3 s of tail
against `SONAR_AUDIBLE_S = 3.0` of actual exposure. Extend the wash to cover the full three seconds
and decay it to nothing exactly as the exposure ends. The player then **feels their exposure window**
before they can read it, and `ticks_since_emit` becomes a block that names something they already
know. Cost: four voices' duration; no new machinery. **Change `AUDIO_OWN_WASH_S` and
`AUDIO_OWN_WASH_DELAYS` in `tuning.py`.** [PROPOSED]

**(b) The body sound is the exposure meter.** Gait scales motion-noise range. If the machine's own
body is audible to the player and scales with gait, then slow-and-quiet versus fast-and-loud is a
thing the player hears every second of every raid, one-to-one with a real mechanic, with no UI.
[PROPOSED; needs §1.5's exception and its guard rail.]

### 2.5 The acoustic picture as data, and one thing that is wrong

`BELIEF-CATALOGUE.md` family G already catalogues this properly. Two rows matter to the mixer:

- `signature_closing` — *"is it getting louder because it fired, or because I am walking into it."*
  The catalogue records that its absence has a measured body count: `CAVE-BLOCKS.md` §8, *"the
  cautious tree freezes where it stands"*, three deaths in eight seeds, because `machinery_audible`
  is a level and *loud and getting louder because I am approaching* is a different fact.
- `signature_period` — three cycles and the machine knows the clock the player learned in hour two.

**The thing that is wrong.** `phase1/audio/tracker.py` maintains the mixer's **own** bearing-cluster
list, with its own merge gate (`AUDIO_TRACK_MERGE_DEG = 40°`) separate from `Belief`'s
(`CONTACT_MERGE_DEG = 18°`). The docstring defends this — *"Belief already has `Contact` for that,
on its own merge rules, for the display. This is the mixer's own, coarser bookkeeping"* — and for
Phase 1 that is fine. **For Phase 3 it is a defect**, because the player and the policy would then
cluster bearings by two different laws, and §1.3's argument is that the player's evidence and the
machine's evidence have to be the same evidence. The player hears two contacts where the tree sees
one.

The fix is already specified elsewhere: `ARCHITECTURE-RECONCILIATION.md` §9 gives
`ContactTrack { id, origin, arrivals, character, estimate, stationary, last }`, where `arrivals` is
*"capped (Phase 1: 60); merged by bearing but never dropped inside the window."* The mixer derives
its gesture-suppression from those arrivals and keeps no track list of its own. **Retire
`tracker.py` and `acoustic_track.py` at Phase 3.** [PROPOSED]

---

## 3. The asymmetry that is the game

> **The player hears the danger and cannot tell the machine, because they never taught it that.**

This is the single most dramatic thing sound can do in this design and it costs nothing, because it
is a consequence of the architecture rather than a feature added to it. It has never been named.

### 3.1 It is two things, and they must not be confused

**(a) The machine sensed it and has no block that reads it.** The signature is on `Belief`, the
mixer sounds it, the tree has no `machinery_audible` guard — or has one with the wrong θ. The player
hears nine seconds of accelerating metal and watches the machine walk on. **This is teachable.** The
correct feeling is frustration that converts into a change made between raids.

**(b) The machine did not sense it and could not have.** No `passive_array`. Deaf for the second
after its own ping. Out of range. **Here the player hears nothing either**, so the drama is
retrospective and belongs to the replay (§1.6). **This is a loadout lesson, not a teaching lesson.**

**The design rule that keeps them apart: (a) must be audible and (b) must never be.** The live mix
must contain nothing the machine did not receive, or (b) collapses into (a) and the player learns
the wrong lesson — that their rule was wrong, when in fact their loadout was.

### 3.2 When (a) should happen: on a schedule, and the schedule already exists

`WHAT-HAPPENED-HERE.md` §4.2 puts `contact_heard` at depth band 1 and `shock_imminent` at depth band
3. So a new player's first raids have the wind-up in their ears and **no block that names it.** That
is not a gap to close. It is the ladder working: the sound arrives, the player has no word for it,
and the word is down there.

**So it needs one rule, and it is the important one in this section:**

> **Every base block that reads a sound ships its sound at least one depth band before the block is
> findable.** A block that arrives before its sound is a rule about nothing.

This is checkable. It is also currently satisfied by accident and will stop being satisfied the first
time a block is added faster than a sound is.

### 3.3 Three rules for designing into the asymmetry

**1. Never resolve the ambiguity in the mix.** A `Contact` is not an identification. Today the mixer
branches on `SoundCharacter` (PING / TONE / SIGNATURE / CRASH), which is legal because those are
*properties of the received signal*. It would be very tempting, and illegal, to make a rival's ping
sound different from the scripted echo, a team-mate different from an enemy, a Hauler different from
a Scout. Write it as a rule:

> **The mixer may branch on `SoundCharacter` and on numbers `Belief` publishes, and on nothing
> else.**

**2. Separate what Recall can answer from what it cannot.** Recall is the player's one live input,
and their hand goes to it whether or not pressing it helps. Recall cannot answer a wind-up: the
warning is nine seconds and a recall spiral is not. Recall *can* answer *the machine is lost* and
*something is closing.* **The separator should be rate, not level:** the things Recall answers are
slow, persistent and recur (you have time); the things it cannot answer are fast and once
(the wind-up, the hammer, a death). That is roughly true today by accident and should be a rule.
[PROPOSED]

**3. A sound that the machine can act on and a sound only the player can act on must be
distinguishable.** Today they are not, and there is a shipped example: the **approach event**. The
mixer computes closing from two arrivals (`AcousticTrack.closing()`, `AUDIO_APPROACH_STEP_Q =
0.055`) and answers the transmission with a second note a fifth higher, 0.22 s later. **The player
can hear a contact closing. No predicate in `blocks.json` can read closing.** `contact_closing` is in
the catalogue, reserved as PredicateId 70, and unbuilt. That is §3.1(a) in its purest possible
form, it is already in the game, and nobody wrote it down. [BUILT, and it is the best example in the
repo.]

---

## 4. What the place sounds like

### 4.1 The seam: two numbers cross it

`PHASE-3-OPEN-QUESTIONS.md` §37 already decides the sim-side model, and it is exact: a
range-bounded cell Dijkstra ("A-lazy"), integer costs in 1/1024-cell units, flooded cells at
563/1024, resumed lazily per listener, cached per emission, budget **10 µs per tick mean**. Measured
on a 400×240 passage cave with four agents: **8.2–9.5 µs per tick, 79–91 ms per match, 1.2 ms worst
tick, ~7.4 MB.**

**What crosses the seam per arrival is `(path length in cells, arrival bearing)` and nothing
else.** No amplitude. No spectrum. No delay. The whole of §4 is the client turning two numbers into
a place.

### 4.2 Propagation delay — none, anywhere, deliberately

The sim has none: a sound is audible over a fixed tick window regardless of path length, and the
20-tick echo offset in the spike is a scripted schedule, not a travel time.

**Recommendation: keep it, and do not add a client-side one either.** [PROPOSED, and it is
deliberately the physically dishonest answer.]

The reason is §1.3's reason. At 20 Hz a tick is 50 ms. A 170-cell path at 0.6 m/cell and 340 m/s is
0.3 s — six ticks, the same order as the sampling cadence. A propagation delay would put the
**sound the player hears out of step with the number the predicate reads**, and a machine whose
warning fires six ticks before the player's warning is a machine the player cannot teach. Physical
honesty is worth less than that.

The one delay that stays is not propagation: `Reflection.delay`, 35–85 ms, client-side, second
arrival. That is the room, and it is right.

### 4.3 Reverb — discrete arrivals, and the existing argument is correct

`reflection.py`: *"Not a reverb: the cave is passages, and a passage delivers a discrete copy at a
discrete delay from a discrete direction. Three of these cost three voices and no filter, which is
the whole reason this is affordable."* [BUILT]

Keep it into Phase 3, for two reasons that survive the change of engine:

- **It is the distance cue that carries.** `placement.py`: *"close to a source you hear the source,
  far from it you hear the cave, because the reverberant field barely falls off while the direct
  sound falls off hard."* `AUDIO_REFLECT_NEAR_FRAC` 0.10 → `AUDIO_REFLECT_FAR_FRAC` 0.55.
- **It costs voices, not DSP.** No filter state, no convolution, no send bus, no impulse response.

**The one place I would spend, and it is legal.** The room's *parameters* can come from the
machine's **believed** local geometry. `point_cloud.clearance()` is already computed every tick for
steering (`driver.py:191–227`) and is belief-derived, so a policy could read it. Feed it to
`Placement`: reflection delay from believed clearance, reflection count from how enclosed the machine
believes it is, decay from believed passage width.

A machine in a believed hall sounds like a hall. A machine in a believed crawl sounds like a crawl.
**A machine that believes it is in a hall and is actually in a crawl sounds wrong — and that is
correct, because being wrong is the subject.** The visual layer cannot make this joke; it draws
belief unlit and truth lit and the two never occupy the same channel. Audio has one channel and
therefore gets the joke for free.

Cost: one scalar per frame, already computed. Two constants on `Placement`. No new voices.
[PROPOSED]

### 4.4 Occlusion — total, binary, and it must stay that way

The sim never expands a rock cell. A sound arrives down a passage or does not arrive.

**There must be no muffled-through-rock arrival**, because the moment there is one, the arrival
bearing stops being the passage bearing, and the passage bearing is the entire reason a cave contact
is ambiguous. What reads to the ear as occlusion is *the path being long*: same source, two corners,
longer path, therefore quieter, duller, smeared and mostly room. `Placement` does occlusion with four
cues and no filter, and it is right.

**One consequence, and do not fix it.** Quality is path length and nothing else, so a near source
round three corners is indistinguishable from a far source in a straight line. That is honest — the
machine cannot tell either — and it is the mechanism behind the next section.

### 4.5 Does sound travel through rock? No. Does the danger? Yes.

This is the best single fact in the sound design and it is already in the build, undocumented.

- **The Assayer's warning** propagates through `SoundField`, over **free cells only**, at
  `HEAR_ANCIENT_RANGE = 80` path-cells, `FLOODED_COST = 0.55`.
- **The Assayer's blow** propagates through `truth/ancient.py`'s Dijkstra, in which *"Rock is
  passable, at cost 1.0. That is not an oversight: the shock travels in the massif, the caves are
  not in its path, and four cells of stone between you and the machine buys exactly nothing."* Water
  costs 0.35. Lethal at 9.00 cells on the axis, 5.32 at the flank.

> **The warning comes to you down the passage. The blow comes to you through the wall.**

So a machine can stand six cells from the anvil through solid rock, take a lethal dose, and have
heard the wind-up faintly, from a bearing sixty cells round the workings, that does not point at the
danger. `machinery_audible` reads a level; the level is measuring **the wrong distance**.
`THE-MACHINERY.md` §4.2 says the same thing from the other side — *"This deliberately inverts the
acoustic layer, where passages, corners and shadow zones are everything"* — and `CAVE-BLOCKS.md` §8
has the body count.

**Two consequences for the mix.**

**(a) The wind-up must not be mixed as though loud means close, and today it is not.**
`phase1/audio/ratchet.py` drives progress off the **ratio** of current signature quality to quality
at the cycle's start, which cancels the distance term entirely (`SIGNATURE_RATIO_AT_LETHAL = 3.33`
is one over the 0.3 strength floor). *"A machine two chambers away now winds up as legibly as one in
the room, at its own honest distance and level."* **This is the one place in the mixer where the
design already refuses to conflate level with danger, and it is the model for everything else.**
[BUILT]

**(b) The hazard needs a cue that reports the shock's geometry, not the sound's, and there is
one.** The shock is *felt*, not heard. A sub-lethal dose is already a number on the truth side
(`damage += 0.5·coupling^1.5`), and `ART-DIRECTION.md` §4.4 gives the module: `structural_monitor`,
whose fix is *"a deployable 180 mm geophone spike, carried on the deck and planted in the floor while
monitoring."*

> **[PROPOSED] A sub-lethal dose makes a sound: the hull ringing once, dry, centred, in the own-body
> register.**

It is legal under §1.5 — the machine's own body reporting its own state. It is the only cue in the
game that measures the shock's true geometry rather than the sound's. It converts a silent damage
number into the clearest teaching moment the game has: *that was close, and the sound did not tell
you.* Cost: one voice.

### 4.6 Water — three facts in the sim, none of them audible

**1. Water is a shortcut.** `FLOODED_COST` 0.55 acoustic, `ANCIENT_WATER_COST` 0.35 for the shock.
A flooded passage is acoustically *shorter* than it is long. The mixer cannot know: `quality` has
already collapsed path and medium into one number.

> **[PROPOSED] An arrival carries a wet fraction — what proportion of its path was flooded.**

Legal (it is a property of the received signal: a wet path really does sound different), cheap (one
accumulator in the same Dijkstra loop, one `u8` per arrival, no extra cells reached), and exactly
what `DESIGN-PRINCIPLES.md` §9 means by refusing to discard. It buys the mixer one honest cue —
**a wet arrival is brighter and longer-tailed than its distance says, because water carried it** —
and it buys a policy one predicate: *the thing I can hear is on the other side of water.*

**2. A Swimmer in water is louder than a walker.** [DESIGNED, `CHASSIS-TIMING.md` D8.]

**3. Water is a wall to lidar and open to sonar.** [BUILT.] So a sump sounds like a passage and
looks like a wall, which is the same joke as §4.3 arriving from a different direction.

**And the drips.** `ART-DIRECTION.md` §5.4 already specifies one, and it is the best detail in that
document: *"The header tank is full and the pipe joint drips — one drip every two seconds onto the
anvil is the entire dormant performance, and a machine that emits nothing while water runs off it
reads as finished rather than menacing."* But a drip thirty cells away is not in `Belief` and cannot
be in the mix (§1.4).

**The only legal source of local ambience is the near-field sense.** `_nearfield` is a real sensor:
8 rays, 2.5 cells, every 4 ticks, quality 0.28. So —

> **[PROPOSED] Ambience exists only within near-field range, is placed from near-field returns, and
> stops when the near field stops. Sound has a lamp radius.**

That is a strange constraint and it produces a genuinely new result: the cave's ambience follows the
machine the way the lamp does, and a machine standing still in a wet chamber has a small, close,
private acoustic world with nothing beyond it. It is the acoustic form of `ART-DIRECTION.md` §2.7's
*"the world does not accumulate"*, and I think it is right.

**[GUESS]** that 8 rays at quality 0.28 are a sufficient basis for saying *that is dripping wet rock
1.8 cells to port* rather than merely *that is rock*. This is designer question 6.

### 4.7 The second arrival — two mechanisms at two timescales, deliberately

- **35–85 ms** — `Placement.reflections`, up to three delayed copies from alternating sides. **This
  is the room.**
- **~1 s** — a genuinely separate `HeardSound` with its own bearing. In Phase 1 the scripted echo at
  (48, 101), an empty labelled dead end fifty cells from anything. In the Phase 3 spike, a whole
  second emitter at a random walkable cell, twenty ticks after the ping (`sim.rs`), which everyone
  including the original pinger can hear. **This is another machine that is not there.**

`tracker.py` already keeps them apart correctly: an arrival inside the merge window is absorbed
*unless* it is more than `AUDIO_PING_SEPARATE_DEG = 45°` off the last gesture, *"which is a genuinely
separate arrival and must survive: that is what the scripted echo is."* [BUILT]

Nothing in the documents distinguishes these two mechanisms and somebody will eventually collapse
them into one reverb. Written down here so they cannot.

### 4.8 What it costs, client-side

Measured from the Phase 1 build:

| sound | voices |
|---|---|
| panel tone | 1–3 |
| ratchet notch | 4 |
| own ping | 5 |
| heard ping | up to 4, or 8 with the approach event |
| motion contact | 4 |
| hammer | 10 |
| **crash** | **14** |

`AUDIO_MAX_VOICES = 48`, raised from 24 *"because a crash is fourteen voices and a wind-up…"*.

The number that matters is not the count, it is **where the synthesis happens**. `Voice` builds its
entire waveform at construction, on the game thread: *"a 2.4 s four-partial tail fell from 8.5 ms to
2.1 ms"* after the float32 change. **2.1 ms is 12% of a 60 fps frame, for one voice**, and it is
spent inside the frame that queued it.

That trick does not survive the move to Godot and should not try to. **[PROPOSED] In Phase 3
synthesis moves off the game thread — a generator feeding a small ring buffer — and the reason is
this measurement, not tidiness.** What *does* survive is every design decision above it: fixed pan,
no filter state, additive partials for brightness, discrete delayed copies for the room. All four are
cheap on any backend, which is the point of having chosen them.

---

## 5. The vocabulary

Eight families. For each: what it is, what it is made of, what it must never do.

There is a ninth thing that is not a family, because it is not a sensor channel and obeys different
rules: **music.** It is out of scope here and settled in §6.5 for the game and §8.1 for the trailer.
The one rule that belongs in this section: **music never occupies 400 Hz – 3 kHz**, which is the
register `tuning.py` reserves for everything that has to be *identified*.

### 5.1 The machine's own body

Dry, centred, no room, no reflections, no `Placement`. **The register that means *inside the
hull*.** [BUILT: the four panel recipes at `AUDIO_PANEL_AMP = 0.042`, the quietest things in the
game.] [PROPOSED: footfall, servo, gait, load, the hull ring of §4.5(b).] Rule and guard rail in
§1.5. Mechanic attached in §2.4(b).

### 5.2 Other machines

Only ever `PING` and `TONE`, only ever a bearing and a quality, never an identity. [BUILT:
`heard_ping` — falling sweep, panned, already reverberant on arrival; `motion_contact` — three grains
of band-limited noise, *"the only unpitched sound in the game that is not a catastrophe, so it cannot
be taken for a quiet beep."*]

The mixer separates *mine* from *theirs* on three orthogonal cues rather than on level: **the own
ping is the only rising sweep, the only hard-centred world sound, and the only one the room answers
afterwards — which is what a sonar transmission physically is.** That is the audio form of
`ART-DIRECTION.md` §4.3's finding about team identity: *"value is necessary and not sufficient. The
rest of the separation has to come from layout and rhythm."*

**Must never do:** resolve. Not rival from echo, not team-mate from enemy, not chassis from chassis.
The one legal difference is that a Hauler is *heard further* (100 cells against a Scout's 20), which
arrives free as quality and is a level difference, not a timbre one. See question 11.

### 5.3 The ancients' machinery

The most developed family, and the one with a live contradiction in it.

| phase | seconds | sound |
|---|---|---|
| listening | 54 | **nothing** [BUILT — silence]; a drip on the anvil every 2 s [DESIGNED, unbuilt] |
| **the slew** | 3 | **a low three-second grind** [DESIGNED, unbuilt] |
| locked | 5 | nothing |
| **the wind** | 9 | the ratchet [BUILT, and it disagrees with the fiction] |
| the fire | 0.15 | the hammer [BUILT] |
| lethal | 4 | nothing but a crash from whatever died |

**The click-count contradiction, measured.** `THE-MACHINERY.md` §3, §5, §6, §9 and §10 all say
**nine clicks at one per second**, and give the argument: *"a policy that hears click seven knows
more than one that hears click two, because the rate is fixed and the ramp is monotone."*
`TRAILER.md` shot 24 says nine. `WHAT-HAPPENED-HERE.md` §7 plants nine at 0:03 as the trailer's
payoff. `ART-DIRECTION.md` §5 lights nine. The Godot spike uses `CLICKS = 9`.

`phase1/audio/ratchet.py` plays a **geometric accelerando**: `interval = RATCHET_SLOW_S ·
(RATCHET_FAST_S/RATCHET_SLOW_S)^progress`, 1.05 s down to 0.115 s. `tuning.py:881` claims *"~24
countable notches over 9 s."* **I integrated the actual schedule: it is 31**, with the ring climbing
940 Hz → 2103 Hz. So the number of clicks in the game is nine, or twenty-four, or thirty-one,
depending which artefact you consult, and it is none of them by accident. See question 4.

**The slew is the biggest hole in the game's audio.** Three seconds of grind, **seventeen seconds
before anything is lethal**, and it says *which sector* — `THE-MACHINERY.md` §5: *"A policy that
stores the bearing of the last grind knows the sector before the warning… Safe becomes a place —
behind it — rather than a distance a machine has to estimate, which is the strongest legibility
property in the design."* It has no sound at all. §10.2 cut it from Phase 1 for a stated and correct
reason (a real `Tone` emitter would add contacts to both tuned policies' logs and change behaviour
the phase was not testing). **That reason expires at Phase 3.** See question 9.

Missing and undesigned anywhere: the recoil, the mast ring-down, the boom locking, the header tank
filling for seventy-five seconds, and — the strangest omission — **the machine listening to the
return, which is the entire purpose of the cycle.**

### 5.4 Water

§4.6. Three facts in the sim, one legal ambience source, one proposed signal.

### 5.5 Rock

**Rock is not a sound. Rock is what happens to other sounds.** That is why there is no rock family
in the mixer and there should not be. Distance is rock: `AUDIO_BRIGHT_CURVE`, the partial stack, the
attack softening, the reflection ratio. All four are the rock, expressed as what it did to something
else.

The exception is rock *moving*: debris in the crash [BUILT — five noise grains, `CRASH_DEBRIS_HP =
110`, *"rock hitting rock clatters, it does not thump"*] and the fines the strike shakes off every
surface. `THE-SENSOR-AND-SLAM.md` §2 makes those fines a **sensor failure** — haze, then occlusion,
then blindness.

> **[PROPOSED] The dust that blinds the sensor is audible for exactly the seconds it is blinding.**

It is the only cue for a failure mode that is otherwise a silent, invisible degradation, and it gives
the player a reason for why the map stopped growing.

### 5.6 The cave itself

Heard as what it does to other sounds (§4.3, §4.4), plus a near-field ambience with a lamp-sized
radius (§4.6). **No bed, no drone, no room tone.** [BUILT — the absence is deliberate; §1.4 corrects
the reason given for it.]

### 5.7 The surface

`DESIGN-PRINCIPLES.md` §3. The only place with sky, the only place that is safe and lit — and, the
point:

> **The surface is the only place in the game where the player hears the world directly, because
> there is no machine between them and it.**

On the surface the player is *present*. Underground they are listening through an instrument. That is
the strongest structural idea available to this game's audio and it costs nothing, because it is
already the fiction.

| | surface | cave |
|---|---|---|
| source | the world | one machine's belief |
| bandwidth | full | band-limited (`AUDIO_NOISE_LP_DULL` ≈ 265 Hz at distance) |
| density | continuous | event-driven, ~1.3 events/second |
| space | wide, wet, mechanical, weather | narrow, discrete arrivals, mostly nothing |
| the player | present | listening |

The descent is the transition, and it is the loudest structural moment in the game — not because it
is loud but because **everything the player has been hearing goes away and is replaced by a
readout.** `TRAILER.md` §5 Act III has half of this already.

[DESIGNED as a place; **entirely unbuilt as sound** — `phase1/audio/` contains no rain, no steel, no
servo, no footfall, no yard.]

### 5.8 The interface

[BUILT.] `fix`, `recall_sent`, `recall_received`, `cargo_changed`. Dry, centred, small.

**Must never do: grow.** The interface is the only family that competes with the world for the
player's attention and has none of the information. `AUDIO_PANEL_AMP = 0.042` against
`CRASH_AMP = 0.70` is a 24 dB gap and it should stay one.

### 5.9 The difference layer (replay only)

§1.6's proposed truth-difference track. It needs a register that cannot be confused with anything
above: **[PROPOSED]** unplaced, uncoloured by distance, and *inverted* — a sound that fades **in**
rather than out. The player should never mistake it for something the machine heard. `EnvelopeShape`
already has the mechanism; this would be a third shape.

### 5.10 Synthesised or sampled

**Stay synthesised.** Not a purity argument — three concrete reasons and one honest cost.

1. **Every distance cue is a parameter of the synthesis.** Brightness is the height of a partial
   stack (`Mixer._partials`); attack is a field on `Envelope`; the room is three extra voices. With
   samples, brightness is a filter with per-voice per-block state, attack is a fade you cannot fake,
   and the room is a send bus. **The four-cue distance model exists because the sounds are
   generated.**
2. **The cave is generated per match.** `DESIGN-PRINCIPLES.md` §5 splits generation into a
   deterministic layer and a client-side dressing layer from the same seed. Audio dressing is the
   same problem with the same answer, and `ART-DIRECTION.md` has already committed the whole visual
   direction to it: *"Nothing in this document needs a modeller."*
3. **A bug report is reproducible.** The mix is a function of `Belief` plus a seed.

**The cost, honestly.** Nothing here will have the grain of a recording — the incidental,
unrepeatable detail that makes a sound feel like a thing that happened once rather than a thing that
happens. `RATCHET_PARTIALS = (1.0, 2.76, 5.4)` is a struck bar; a real pawl on a real ratchet is a
hundred milliseconds of chaos. This is the same wall `DESIGN-PRINCIPLES.md` §6 hit visually — *"it
needs to look photoreal"* — and audio will hit it in the same place: the ancients' machinery, which
must feel *made* rather than *generated*.

**[PROPOSED] Leave one seam and do not build it.** `Voice` takes a `Waveform` enum. A
`Waveform::GRAIN(id)` variant that plays a short pre-rendered grain through the identical envelope,
pan, delay and reflection path would let exactly one family go to recorded material without changing
anything else in the mixer. Same posture as `CLAUDE.md`'s hardware backend: not building it, not
foreclosing it.

---

## 6. The mix, and silence

### 6.1 The visual is nine-tenths darkness. The acoustic is not nine-tenths silence.

`ART-DIRECTION.md` §2.9 asserts ≥70% true black per frame, measures 93.5% on the target frame, and
§11 names the risk: *"That a player will accept a frame that is 85–95% true black for six to ten
minutes, and that the belief overlay is enough company in the dark."*

**Audio's real job in this game is being the company in the dark**, and it cannot do that by also
being empty. A Phase 1 match has 587–636 audible events over eight minutes — roughly 1.2 to 1.3 per second —
and that is roughly right.

The correct analogy is not darkness. **It is the lamp:** a small, near, continuous thing you always
have, surrounded by a large emptiness that occasionally speaks.

> **Continuous near, sparse far.** The machine's own body is always there and always small. The
> world is rare and always means something.

Today the first half of that is missing entirely — there is no body — which is why eight minutes of
Phase 1 audio is a sequence of events with nothing between them.

### 6.2 When it is quiet

- The **54 listening seconds** of every 75.
- Every stretch with no contact in range.
- **`RATCHET_BREATH_S = 0.75`** before the hammer — and this one is *enforced*, not assumed. The
  build measured that it previously was not: *"over seed 7's four cycles, the loudest thing inside
  the breath window reached 0.30, 0.27, 0.00 and 0.15 against hammer peaks of 0.30, 0.31, 0.73 and
  0.41 — in two of four the silence was as loud as the hit."* Now the ratchet's `holding` state
  ducks everything sounding to 0.10 and forbids any routine gesture from starting. [BUILT]
- **`CRASH_SUPPRESS_S = 1.30`** after a death, same mechanism.

### 6.3 What makes quiet frightening rather than empty

**It has to be quiet *from* something.** Empty quiet is fifty-four seconds with nothing in it.
Frightening quiet is fifty-four seconds *after nine clicks and a hammer*, when you know the tank is
filling.

> **Silence is only frightening when it is a phase of a cycle the player has learned.**

That is the entire argument for §7, and it is why the Assayer is the most important sound in the
game: it is the thing that teaches the player to hear an absence as a phase. `THE-MACHINERY.md` §5
puts it better than I can — *"the only thing down there that is regular, loud and not lying…
working out that the most dangerous object in the cave is also the only honest one is the good kind
of discovery."*

Second mechanism, already built and worth naming: the crash and the breath both **duck what is
already sounding**. That is not a mix trick. It is the difference between *quiet* and *gone quiet*.
**A silence that arrives is an event.**

Third, [PROPOSED] and it is a refusal rather than a feature: **as the machine gets more lost, the mix
should get quieter, and it already will** — a machine that stops pinging stops being answered and
stops hearing its own returns. Do not add a fear stinger. **Let the loss of information be the loss
of sound.**

### 6.4 The loudest moment in a match

Today, measured: `CRASH_AMP = 0.70` against `HAMMER_AMP = 0.65`. That is 0.6 dB, which is not a
decision, it is a coincidence. Both are gain-floored (`HAZARD_GAIN_FLOOR = 0.78`) so a distant one
still arrives above every routine sound, at the deliberate cost of keeping only 1.7 dB of level
across the whole distance range.

**[PROPOSED] The loudest moment should be your own machine dying, then the hammer that killed it,
then anything else.** The hammer happens six times a match whatever anyone does. A death happens once
and it is what the raid was about. Make the gap deliberate and put it at 3–4 dB.

**And a third candidate nobody has considered: getting out.** `DESIGN-PRINCIPLES.md` §2 is that this
is an extraction game, and in an extraction game surviving is the payoff. **Nothing in the build
makes a sound when the machine comes up the shaft.** It is the only unambiguously good news the game
has and it is currently silent. See question 13.

### 6.5 Does the game have music? One rule, and it falls out of §5.7

Asked because the trailer question was asked (§8.1), and it is the larger of the two.

> **Music everywhere the player is present. No music anywhere the player is listening through a
> machine.**

**The argument against a score in the run phase is §1.3's argument, arriving in a costume.** Music is
allowed to editorialise — that is what it is *for*, and in a trailer it is a feature (§8.1). In a
match it is a truth leak with better manners. The moment a cue swells because a rival is closing, the
player has been told something their machine does not know, through a channel nobody audits, and the
player's evidence and the machine's evidence have stopped being the same evidence. That is precisely
the failure `SPECTATOR-DISPLAY.md` §4.2 rule 3 already names — *"a room tone or hazard drone driven
from truth"* — and **a dramatic score is a hazard drone that went to school.** It belongs in the same
prohibition, in the same words.

The rule has teeth even for a score driven honestly from `Belief`, and this is the part that is easy
to miss: a cue that swells on *believed* threat is legal under the invariant and still wrong, because
it duplicates in music a judgement the player is supposed to be making from evidence. **Belief-legal
is not the same as design-legal here.** The mixer may sound what the machine received; it may not
tell the player how to feel about it.

**And the run phase does not need one, because it already has a score and the score is diegetic.**
The Assayer is a 75-second period carrying a nine-figure ostinato, a held breath, a downbeat and
fifty-four seconds of rest. That is a composition, and §6.3 is a musical claim about it: silence
frightens only when it is a phase of a cycle the player has learned. `THE-MACHINERY.md` §5 says the
same thing without the word — *"the only thing down there that is regular, loud and not lying."*
**Music on top would compete with the one rhythm the game needs the player to internalise**, and
would compete with it for the same slot: a slow pulse, in the low-mid, that means *time is passing
and something is coming.*

**Where music is legal, and it is not nowhere.**

| place | music? | why |
|---|---|---|
| **the surface** — pit-head, yard, bench, teaching | **yes** | No machine between the player and the world (§5.7). No belief, nothing to leak. And it makes the descent a *musical* cut every single raid, which is the trailer's best beat given away free, forever. It stops at the shaft collar. |
| **menu, loadout, lobby** | yes | Same reason. |
| **the run phase** | **never** | Above. This is a rule, not a preference. |
| **replay playback / scrubbing** | **no** | The forensics layer is where the player diagnoses. A score colours a diagnosis, and `ROADMAP.md` Phase 5 makes this the most important screen in the game. |
| **post-match summary** | yes | It is over. Nothing left to leak, and it is the one moment the game is allowed to have an opinion about what happened. |
| **the difference layer** (§1.6, §5.9) | no | It is evidence. |

That single rule is worth more than it looks. It means **the descent is scored by subtraction in the
game exactly as it is in the trailer**, it means the surface can be warm without the cave having to
be, and it means nobody ever has to argue about whether a tension cue is cheating — because there
are no tension cues. See questions 16 and 17.

---

## 7. What the player learns to hear, in order

Ten hours. Each: what it is, and what it lets them predict.

| # | when | sound | what it predicts | state |
|---|---|---|---|---|
| 1 | minute 1 | **your own ping** — the only rising sweep, hard-centred, dry, and then the room answers | *I am now audible, for about three seconds* | [BUILT]; tail should cover the full 3 s (§2.4a) |
| 2 | minute 1–5 | **somebody else's ping** — falling, panned, already wet on arrival | *another machine, roughly that way, not close* | [BUILT] |
| 3 | hour 1 | **near against far** — not level: dull, smeared, wide, mostly room | *how much time I have* | [BUILT]; the cue the pre-rework mixer lacked entirely |
| 4 | hour 1 | **the wind-up** — a countable train of metal that climbs | *something hits in about nine seconds* | [BUILT]; count disputed (§5.3) |
| 5 | hour 1 | **the silence in front of the hammer, then the hammer** | *the cycle ended; I have about seventy seconds* | [BUILT]; the silence is the tell, not the hit |
| 6 | hour 2–3 | **the 75-second period** — not a sound, a rhythm, learned from three of 4 and 5 | *when it is next safe to cross* | emergent; the block that closes the gap (`signature_period`) is catalogued and unbuilt |
| 7 | hour 2–5 | **the approach event** — two notes a fifth apart, 0.22 s | *that contact is nearer than last time it spoke* | [BUILT]; **no predicate can read this** (§3.3) |
| 8 | hour 3–10 | **a crash that is not yours** | *somebody lost a raid; there is a wreck with cargo and a policy, that way* | [BUILT]; the best sound an extraction game can have |
| 9 | hour 5+ | **the slew** — three seconds of grind, seventeen seconds out, and it says which sector | *where safe is* — safe as a place, not a distance | [DESIGNED], unbuilt (§5.3) |
| 10 | hour 10+ | **the second arrival** — same character, wrong bearing, a second late | *there is a passage there I have not mapped* | [BUILT]; the hardest and the best |

Note that 6 is the first thing the player knows that their machine does not, and 7 is a thing the
player can hear that no block can express. **Two of the ten rungs on this ladder are §3's asymmetry,
and they are already shipped.**

**What the player must never learn to hear, because it does not exist:**

- **Front from back.** Stereo has one axis; `Placement.pan_for` folds north onto south exactly.
  There *was* a fake — a screen-y tilt on level and brightness — and it was measured at 1.74 dB
  against the 20 dB distance owns on the same channel and deleted, because *"it could not be heard as
  direction and it could be heard as distance."* [BUILT, as an absence, with the measurement.]
- **A lie from an honest fix.** §1.2(b).
- **A rival from an echo.** §3.3 rule 1.
- **A Hauler from a Scout**, except as range.

---

## 8. The trailer

### 8.1 Does the trailer need a backing track? Yes, and §5's own rule proves it

The designer asked directly. **I agree it needs one**, and the argument that settles it is the one
the designer's challenge exposes, which is a contradiction *internal to* `TRAILER.md` §5:

> §5 states the rule — *"every loud moment is followed by a longer quiet one"* — and builds the
> emotional centre of the cut on it: the descent, where *"surface noise recedes over five seconds
> until there is nothing but the machine, then a held silence under card 3."*
>
> **But silence only reads as silence if something stopped, and §5 removes the thing that would
> stop.** If the whole two minutes is quiet, the descent is not a change of register — it is more of
> the same, at a slightly lower level. **You cannot drop out of nothing.**

That is decisive on its own. Two supporting arguments, both real but neither load-bearing: two
minutes is long to hold with no musical structure (the famously quiet trailers are usually shorter,
or are carrying an audience that already knows the game); and a score-free announcement at a loud
show risks reading as *unfinished* rather than as bold, which is the exact opposite of what an
in-development announcement needs.

**One correction to the concession, because it went one step further than the evidence.** §5 makes
two claims and the challenge only breaks the first:

- *"There is no score."* — **wrong**, per above.
- *"The trailer is built from the game's own audio, which already exists in `phase1/audio/`."* —
  also wrong, and separately. `phase1/audio/` contains **ten recipes** and none of them is rain,
  steel, a pipe, a servo, a footfall or a yard. Acts I, II, III and VI need sound that **does not
  exist in this repository in any form.**

So the trailer does not have a *silence* problem. **It has a density problem**, and there are two
ways to fix it: build the missing diegetic material, or add a score. It probably wants both. If it
gets one, it should be the score — because a rain-on-steel that sounds wrong is worse than no rain,
whereas a sparse tonal bed that is merely adequate still works. Either way, the gap belongs in §7's
honestly-missing table, where it currently is not.

#### The argument that actually justifies a score here, rather than merely permitting one

**Music is the only channel in this trailer that is allowed to be wrong without lying.**

The trailer's whole fifth card is *"And it can be lied to."* But the diegetic layer is forbidden from
telling the viewer that: `ART-DIRECTION.md` §6.3's anti-tell rule, and §3.3 rule 1 here, both say the
lie must be indistinguishable from the truth — and in the shipped game it is, because a spoofed fix
plays the same 660/990 chime as every honest one (§1.2b). **Sound design cannot editorialise. Music
is not a sensor and is not bound by that rule.** So the lie is the one place in the film where a
score earns its existence rather than decorating: the diegetic layer plays routine housekeeping, and
underneath it the tonal centre moves and does not come home. The viewer hears that something is
wrong and cannot point at what — which is exactly the machine's situation, rendered in the one
channel that can render it.

#### What it is made of

The designer's instinct — *out of the world rather than laid over it* — is right, with one
correction. A score made **only** of struck iron and water is not a score; it is sound design with a
tempo, and it will not fix the "reads as unfinished" problem, because what reads as finished to a
general audience is **pitch material that moves**. Texture alone will not do it.

So: the world's *timbres*, carrying a real tonal argument.

| layer | material | source in the build |
|---|---|---|
| **the bed** | sustained inharmonic metal — long, low, struck rather than bowed | `Voice` + `Mixer._struck(ratios, brightness, tilt)`, `EnvelopeShape.EXPONENTIAL`. **This already exists.** |
| **the room** | every score voice sent through the cave's own reflections, so it arrives with the tails of a passage | `Mixer._room()` at low quality. **Already exists**, and it is precisely *"the mine is a resonator"* — the score and the sound design are the same material because they go through the same code. |
| **the pulse** | 1 Hz | **The ratchet.** Nine clicks at one per second is **60 BPM**, supplied by the fiction. |
| **the form** | one and a half breaths | **The 75-second cycle.** It is too slow to be felt as tempo — nothing at 75 s is a pulse — but it is exactly right as large-scale structure, and it is the reason the cut is 2:00. |
| **harmony** | **two events in two minutes, and no more** | authored |

**An interaction the designer needs to see before answering question 4.** The tempo device above
depends on the ratchet's rate. §9 question 4 recommends **nine fixed clicks at 1 Hz**, retiring the
shipped accelerando, for gameplay reasons — a fixed rate makes the count *information*. If that
recommendation is taken, **the trailer loses the free stringendo into the strike** and has to get its
acceleration from harmonic rhythm and the edit instead. If the accelerando is kept, the trailer gets
a built-in accelerating pulse and the game keeps a wind-up that cannot be counted. **These are one
question, not two, and I would not want my gameplay recommendation to quietly break the trailer's
tempo without saying so.** My position stands — take the nine clicks, and let the score accelerate
by other means — but it is a real cost and it is stated.

#### The two harmonic events

1. **0:50–1:04, the descent.** The bed drops a register and loses its top. Same pitch centre. This
   mirrors, in music, exactly what §5.7 says the mix does at the shaft: wide → narrow, full-band →
   band-limited, world → readout.
2. **1:45–1:47, the fold.** The centre moves a semitone and **does not resolve**, and never resolves
   for the remaining thirteen seconds of the film. Act VI ends on it, under rain. The trailer's
   argument is that nothing down there comes home, and this is that argument in the one channel that
   can make it without a word.

That is the entire harmonic content. Two events. Anything more is a film score, and this is not one.

#### The descent — exactly what the score does at 0:50–1:04

This is where the whole cut turns, and **the obvious scoring is wrong.**

The obvious move is to fade the score out with the surface. Do not. If the score leaves when the
world leaves, then the held silence at 1:01 has nothing carrying it and card 3 lands in a hole; and a
score that exits and re-enters at 1:04 reads as an edit rather than as a place.

> **The score is the one thing that survives the descent.**

Everything diegetic goes over five seconds — rain, yard, weather, footfall on concrete, the hoist.
The score does not go. It **narrows**: same pitch, same pulse, top gone, tails long, register
dropped. So the descent is not *sound stops.* It is **the world stops and the music is left alone in
it** — which is more frightening, and which is the literal statement of §5.7: on the surface you hear
the world; underground you hear an instrument. **The score becomes the instrument.**

And *then*, at **1:01**, under card 3, the score itself stops. Three seconds of true nothing.

That is the answer to *you cannot drop out of nothing*: **you drop out of the score**, fifty seconds
after it was established, one beat after it has just survived the loss of everything else. It is the
single loudest structural moment available in the film and it costs no signal at all.

#### Where it drops out, and nowhere else

Three holes. A fourth is refused.

1. **1:01–1:04** — card 3, in the black. The designed hole, above.
2. **1:13–1:13.5** — the first belief cut. §5 already asks for half a second of silence there and
   gives the right reason: *"sound is what tells the viewer they have changed register, not a
   whoosh."* The score goes too, or it is only a diegetic cut.
3. **1:43–1:45** — after the strike, and **by the game's own mechanism rather than by a fader.** The
   mixer already ducks everything sounding to 0.10 on a crash and holds it (`CRASH_DUCK`,
   `CRASH_SUPPRESS_S = 1.30`); `RATCHET_BREATH_DUCK` does the same in front of the hammer. Put the
   score on a bus the strike ducks, and the trailer inherits the game's dynamics instead of an
   editor's taste. §5's own "every loud moment is followed by a longer quiet one" is then not a
   trailer convention at all — it is `mixer.py` running.

**Refused: the fold at 1:45 must not be silent.** §5 says *"The fold at 1:45 gets no sound at all,
which is worse."* With a score present that is strictly worse than the alternative: the diegetic
layer plays the ordinary fix chime (true to the build — §8.2 item 3) and **the score does the fold.**
Silence there wastes the one moment music is indispensable.

#### Act by act

| act | t | what the score does |
|---|---|---|
| **I — the place** | 0:00–0:26 | **Enters at 0:05, not 0:00.** The first five seconds — black, water, the unexplained ratchet — stay naked, or the payoff at 1:39 becomes a musical callback instead of a narrative one. Then the bed: one low struck-metal centre, 60 BPM implied and never stated. |
| **II — the teaching** | 0:26–0:50 | Warmest and densest. **The only place the score is allowed to be pleasant**, because it is the only warm act in the film. One upper voice added. Still one centre. |
| **III — the commit** | 0:50–1:04 | The turn. Diegetic world recedes over five seconds; the score narrows but survives. **Stops dead at 1:01** for card 3. |
| **IV — the dark** | 1:04–1:36 | Returns at 1:04 with the lamp, thinner than before. Long tails, wide spacing, almost no event — this act belongs to the sensor. Half-second hole at the 1:13 belief cut. |
| **V — what is down there** | 1:36–1:54 | From 1:39 the score's pulse and the machine's pulse are **the same pulse**. Ducked by the strike at 1:43. **At 1:45 the centre moves and does not resolve.** |
| **VI — title** | 1:54–2:00 | The moved centre, unresolved, under rain. It never comes home. That is the film's argument. |

#### How it relates to the diegetic layer rather than fighting it

Four rules, and all four are mechanisms that already exist:

1. **Same room.** Score voices go through `Mixer._room()`, so they arrive with the same reflection
   pattern as everything else. They are in the cave, not over it.
2. **Separate bus, one-way ducking.** The world ducks the score. **The score never ducks the world.**
3. **The score never occupies the ping band.** `AUDIO_HEARD_PING_F0 = 760`, own ping 620→2100 Hz,
   the ratchet's ring 940→2103 Hz. The score's business is below 400 Hz and above 4 kHz, and the
   400 Hz–3 kHz window stays clear — which is the same register rule `tuning.py` already enforces on
   everything that has to be *identified*.
4. **The score is never a cue for an event.** It has two harmonic events in two minutes and neither
   is synchronised to a sound; both are synchronised to a *card*. Music comments on the film's
   argument, never on the world's contents. That is also the rule that keeps §6.5 honest.

### 8.2 The rest of the critique of `TRAILER.md` §5

**1. The material gap.** See §8.1: `phase1/audio/` covers Acts IV and V and nothing else, and §7's
honestly-missing table does not say so.

**2. The nine clicks are not what the mixer plays.** §5 Act V: *"the ratchet, nine clicks, rising in
pitch and level."* Shot 24: nine. `WHAT-HAPPENED-HERE.md` §7 beat 1 plants nine at 0:03 as the
payoff: *"A viewer who counts has been handed the machine's entire cycle before the game has
started."* The shipped ratchet plays **thirty-one accelerating notches** (§5.3). **A viewer who
counts at 0:03 and counts again at 1:39 gets a different number both times and neither is nine, so
the trailer's best planted payoff does not currently work.** Either the audio changes or the trailer
stops promising a count. Question 4.

**3. "The fold at 1:45 gets no sound at all, which is worse" — and the game does something better
than silence.** In the game a spoofed fix plays `Mixer.fix()`: 660 Hz, then 990 Hz, dry, centred,
0.042 — **exactly the same chime as every honest correction in the match.** That is stronger than
silence and it is also *true*, which silence is not: the machine did correct, and it is pleased with
itself. **Recommendation: the fold gets the ordinary sound.** The lie sounds like housekeeping.

I checked the more dramatic option and it is not available: a fix does not rotate the stereo field
today, because `HEADING_FIX_GAIN = 0.0` (§1.2a). Do not promise it.

**4. Act III is the trailer's best instinct and is under-specified.** *"The descent is the whole
sound design of the trailer… surface noise recedes over five seconds until there is nothing but the
machine."* That is exactly §5.7, arrived at independently. But **a fade alone reads as a volume
ramp.** The *register* has to change: wide to narrow, full-band to band-limited, continuous to
event-driven, world to readout. Name it, or an editor will do it with a fader.

**5. The belief cut at 1:13 — "silent for its first half second, then the sweep comes in. Sound is
what tells the viewer they have changed register, not a whoosh." That rule belongs in the game, not
only in the trailer.** Every surface/cave transition and every entry into enter-agent-perception mode
(Phase 5) should use it.

**6. "Every loud moment is followed by a longer quiet one" is not a trailer convention here — it is
the mixer's actual behaviour**, enforced by `CRASH_SUPPRESS_S = 1.30` and `RATCHET_BREATH_S = 0.75`
with ducking. Worth saying so, because it means the trailer inherits the game's dynamics rather than
imposing an edit style on them.

**7. The first sound in the trailer is the hardest sound in the trailer, and §5 does not say so.**
Shot 1 asks for *"one distant metallic ratchet, unexplained."* A distant notch in the shipped mixer
is dull, smeared, and mostly room — `RATCHET_RING_BRIGHT_FLOOR = 0.55` exists precisely because the
wind-up stopped being countable at range. **Countable and distant are in tension and that tension is
undocumented.**

**8. The download shot has no sound and it is the loudest act in the game.** §10 adds *"the machine
puts its head to the floor and downloads… the belief view fills with something that is not a scan,"*
and calls it the best value in the trailer. §5 gives it nothing. Interfacing broadcasts a continuous
`TONE` at 80 cells for the whole dwell and *"the whole cave hears you take it."* **A silent download
misrepresents the mechanic in the one shot that sells the mystery.**

**9. Shot 24 asks for twelve seconds of machine in a four-second shot.** Shot 24 is `1:39 | 4s` and
its content is *"The Assayer's boom slews. The hammer ratchets: nine clicks."* The slew is **3 s**
and nine clicks at 1 Hz is **9 s**. It does not fit, and the shot is the trailer's whole Act V
payoff. **Fix, and it is better filmmaking anyway: start the wind under shot 23.** The mast comes out
of the dark at 1:36 with the clicks already running, and the count has nine seconds to be a count.
Act V is 18 s and can afford it if the mast reveal carries the wind's audio rather than preceding it.
This also matters to §8.1: **a pulse that is on screen for four seconds is not a tempo.**

**10. The trailer promises a cycle and delivers a count.** `WHAT-HAPPENED-HERE.md` §7: *"A viewer who
counts has been handed the machine's entire cycle before the game has started."* Counting gives the
click count. It gives the **period** only if two firings are 75 seconds apart on screen — and the
opening ratchet is at 0:03 against the strike at 1:43, which is 100 s. **Moving the opening ratchet
to 0:28 makes the period literally true**, for free, and puts the mine's clock ticking underneath the
warm teaching act, which is a good intrusion. Against it: 0:03 is a stronger place for the first
sound in the film, and *"black, water dripping, one distant ratchet"* is an excellent opening. I do
not think this is clear-cut; I think it is worth knowing that the claim in §7 is currently
unearned.

### 8.3 What is buildable in `phase1/audio` today, what needs code, what needs a composer

**Buildable now, with zero new code.**

- `Voice` already takes a waveform, an `f0 → f1` sweep, duration, amplitude, pan, attack, decay,
  delay, envelope shape, **an arbitrary partial stack**, and noise band limits. `Mixer._struck()`
  builds inharmonic struck-bar stacks. So **a tonal bed is a set of long `SINE` voices on inharmonic
  ratios with exponential envelopes, and a harmonic move is a second set of `f0`s.** The entire pitch
  layer of §8.1 exists today.
- **The pulse** is `play(..., delay=n * 1.0)`.
- **The room** is `Mixer._room()` at low quality — long, dull, passage-shaped tails, free.
- **The render** is already there: `Mixer(offline=True)` plus `render_offline()`, and
  `view/recorder.py` already pulls the mix frame by frame into a WAV and muxes it with ffmpeg. **A
  procedural score can be rendered to a stem this week and cut in an editor.**

**Needs new code, and it is small.** Roughly 200 lines total.

1. **A transport.** There is no bar/beat clock; everything schedules off match seconds. A `Score`
   class owning a tempo and a section list, emitting voices on beats — the same shape of object as
   `ratchet.py`, and it belongs beside it. ~150 lines.
2. **Two buses.** `Mixer.duck()` currently hits every voice. `Voice` needs a `bus` field and `duck()`
   a bus filter, so the world can duck the score one-way (§8.1). ~15 lines.
3. **Amplitude automation upward.** `Voice.duck()` is the only level change and it only ramps down. A
   crescendo needs its mirror. ~20 lines.
4. **A streaming voice — for the game, not the trailer.** `Voice` builds its whole waveform at
   construction: a 30-second bed is 5.3 MB and, at the measured 2.1 ms per 2.4 s, about **26 ms to
   build inside one frame.** Irrelevant to an offline trailer render; fatal live. This is the same
   finding as §4.8 and the same fix.

**Genuinely needs a composer.**

- **The pitch material.** Which notes, and which semitone the fold moves to. `_struck(ratios)` supplies
  a mechanism; it does not supply a tune, and a wrong tune is worse than no tune. This is the one
  place in the whole document where I would not trust a default.
- **Anything with a performance in it.** Synthesis gets a sustained inharmonic tone with an envelope;
  the gap between that and something a person played is the same wall §5.10 names for the machinery.

**Recommendation: build the procedural score in `phase1/audio` first, cut the trailer with it, and
hand it to a composer as the brief rather than as the deliverable.** It answers the structural
questions cheaply and in exactly the right material — where it drops out, what the descent does, what
the fold does, what register it must stay out of — and those are precisely the questions a composer
would otherwise have to guess at from a text document. See question 15.

---

## 9. Open questions for the designer

Yes/no, with a recommended default each.

**1. Does the player always hear only what their machine heard, in the live view — no truth channel,
no toggle?** Default: **yes.** (§1. If no, the argument in §1.3.1 says teaching breaks, and that is
the whole game.)

**2. Does the replay get a labelled, non-default layer that plays only what the machine *failed* to
hear?** Default: **yes.** Cost is a `MatchRecord` change to keep culled arrivals. (§1.6)

**3. May the client sound the machine's own body — feet, servos, load, gait, damage — from
`MotorCmd` and `SelfReport`, dry and centred, never placed in the room?** Default: **yes.** This is
the one exception to belief-only and it must be explicit, or it will be either forbidden as a leak or
abused as a loophole. (§1.5)

**4. The wind-up: nine fixed clicks at 1 Hz, or the shipped accelerando?** Default: **nine fixed
clicks; retire the accelerando.** Five artefacts say nine and the design argument is real — a fixed
rate makes the count *information* (*"a policy that hears click seven knows more than one that hears
click two"*), while an accelerando is only a feeling. **The honest cost: nine one-second clicks are a
far less urgent sound than thirty-one accelerating ones, and the wind-up is the game's alarm.** If
both are wanted, the answer is nine clicks whose **pitch** climbs — `Ratchet.climb()` already does
14 semitones — rather than whose rate does. Changes `phase1/audio/ratchet.py` (`interval()` becomes
constant) and retires `RATCHET_SLOW_S` / `RATCHET_FAST_S`. (§5.3)

**5. Does an arrival carry a wet fraction — how much of its path was flooded?** Default: **yes.** One
accumulator in the propagation loop, one `u8` per arrival, buys a real cue and a real predicate.
(§4.6)

**6. Is there local ambience, restricted to near-field range, so that sound has a lamp radius?**
Default: **yes to both.** Depends on the [GUESS] that near-field returns can carry it. (§4.6)

**7. Is there propagation delay anywhere, sim-side or client-side?** Default: **no.** Stated
explicitly because it is the physically honest answer and I am recommending against it: a delay puts
the player's warning out of step with the predicate's. (§4.2)

**8. Does a sub-lethal shock dose make a sound — the hull ringing once, in the own-body register?**
Default: **yes.** It is the only cue that reports the shock's true geometry rather than the sound's,
and it fixes a measured failure. (§4.5b)

**9. Does the slew get a sound in Phase 3?** Default: **yes.** It is the earliest, cheapest and most
teachable warning in the whole design, and the reason it was cut from Phase 1 expires when Phase 1
does. (§5.3)

**10. Does the room's character come from the machine's *believed* local geometry — so a machine
that believes it is in a hall sounds like it is in a hall even when it is not?** Default: **yes.**
`clearance()` is already computed and already belief-side. (§4.3)

**11. Does a chassis have an audible timbre — does a Hauler sound heavier than a Scout — or only a
longer range?** Default: **no timbre, range only.** A bearing-only hydrophone with 4–22° of noise has
no business resolving mass, and a timbre difference is an identification. (§5.2)

**12. Is the loudest moment in a match your own machine dying, ahead of the hammer?** Default:
**yes**, with the gap made deliberate at 3–4 dB rather than the current accidental 0.6. (§6.4)

**13. Does extraction make a sound?** Default: **yes.** It is the only unambiguously good news in the
game and it is currently silent. (§6.4)

**14. Does the mixer stop keeping its own bearing tracks at Phase 3 and read `ContactTrack`
instead?** Default: **yes.** The player and the policy must cluster bearings by the same law or §1.3's
argument fails in the small. Retires `tracker.py` and `acoustic_track.py`. (§2.5)

**15. Does the trailer get a backing track?** Default: **yes** — sparse, tonal, built from the world's
timbres through the game's own room, two harmonic events in two minutes, surviving the descent and
stopping under card 3. Built procedurally in `phase1/audio` first and handed to a composer as the
brief. **`TRAILER.md` §5 needs rewriting either way**, because its material claim is false
independently of the score question. (§8.1, §8.3)

**16. Does the run phase have any non-diegetic music, ever?** Default: **no**, as a rule sitting
beside "audio may not import truth", and for the same reason: a score that has an opinion about the
machine's situation is telling the player something their machine does not know. Note this bites even
on a belief-driven score. (§6.5)

**17. Does the surface have music?** Default: **yes**, stopping at the shaft collar — which makes the
descent a musical event every raid, not just once in a trailer. Menu and loadout yes; replay playback
no; post-match summary yes. (§6.5)

**A note on question 4, restated because it now has two owners.** Nine fixed clicks versus the
accelerando is a gameplay question *and* the trailer's tempo question. Taking the nine costs the
trailer a free stringendo into the strike. My recommendation is unchanged — take the nine — but it
should be decided knowing both bills. (§5.3, §8.1)

---

## 10. Every guess, in one place

1. **0.6 m/cell.** Inherited from `ART-DIRECTION.md`, which flags it as its own guess and as designer
   question 2. Every metre figure in §2.1 is downstream of it. The *ratios* are not.
2. **That near-field returns (8 rays, 2.5 cells, every 4 ticks, quality 0.28) are a sufficient basis
   for local ambience.** They may only support *rock at 1.8 cells*, not *dripping wet rock at 1.8
   cells*. Question 6.
3. **That a wet-fraction accumulator is free in the Dijkstra loop.** By analogy with
   `ACOUSTIC-BUDGET.md` §11's own assumption that rock absorption is a per-cell cost multiplier and
   *"changes nothing in the loop"* — which that document also marks as assumed, not measured.
4. **That 3–4 dB is the right gap between a death and a hammer.** Nothing has been measured; the
   current 0.6 dB is definitely not a decision.
5. **That moving synthesis off the game thread is the right Phase 3 answer.** The 2.1 ms measurement
   is real; the remedy is mine and untested on Godot.
6. **That a difference-mix that fades in reads as "you did not hear this."** Untested. It is the only
   part of §1.6 that is an aesthetic claim rather than an architectural one.
7. **That the player can learn a 75-second period by ear in two to three hours** (§7 row 6). The one
   evidence point cuts against it: `2026-09-08-cold-read.md` records that *"nobody registered the
   hazard's seventy-five-second heartbeat as a rhythm"* — though that rehearsal had **no sound at
   all**, which is exactly what it could not test.
8. **The ten-hour ordering in §7.** It is an argument from what each sound predicts, not an
   observation. No playtest in this repo has ever been run with the current mixer audible.
9. **That a two-minute unscored trailer reads as unfinished at a loud show** (§8.1). This is a claim
   about an audience, from a designer's instinct that I agree with, and neither of us has tested it.
   It is the weakest of the three arguments for a score and it is not the one the case rests on — the
   *"you cannot drop out of nothing"* contradiction is internal to `TRAILER.md` §5 and needs no
   audience research at all.
10. **That texture without moving pitch will not read as finished** (§8.1). Same class of claim.
11. **That ~200 lines covers the transport, the buses and the upward automation.** Estimated from the
    shape of `ratchet.py`, not from writing it.
12. **That the surface has enough of an identity to be scored.** `ART-DIRECTION.md` has no surface
    section at all — no rendered exterior, no sky, no location — so §6.5's warmest claim rests on
    `DESIGN-PRINCIPLES.md` §3 and the Godot spike, not on an art direction.

**And one thing that is not a guess and should be said before anything in this document is acted
on:** `docs/phase1-playtests/2026-09-08-cold-read.md` §6 — *"It cannot tell us whether the sound
works. P1X-20 is entirely untested here, and P1X-20 was the largest single change in the build."*
**The mixer rework has never been heard by a tester.** Everything in §5, §6 and §7 is a design
argument standing on measurements of signals, not on anybody's reaction to them.
