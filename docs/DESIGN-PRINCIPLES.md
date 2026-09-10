# Design principles

Decisions the designer has stated that are larger than any one phase. Each is dated, in
the designer's words, followed by what it binds. `DESIGN.html` is the full design and is
background; these are current and win where they disagree with it.

---

## 1. Base blocks are Minecraft items — 2026-09-06

> Think of the base blocks the same as Minecraft items. As the game grows, devs add more,
> so building behaviours can get more complex. But the equivalent of the wooden sword,
> shovel, pickaxe and crafting table are built on day one.

**What a base block is.** A predicate or an action — the things a behaviour tree is made
of. Phase 2's three predicates (`unexplored_branch_exists`, `uncertainty > θ`,
`carrying_cargo`) and two actions (`take_branch`, `return_to_beacon`) are the day-one
items.

**What it binds.**
- The player meets each block in play before composing it. The Phase 2 tutorial
  introduces them progressively: a run with no drift and two blocks; drift arrives and the
  other blocks appear because now they matter; then the full problem. Every later block
  arrives the same way.
- Nothing that consumes blocks — induction, tree render, sentence render, later the VM and
  the node editor — is written over a fixed set by name. Blocks are a list. Adding one is a
  data change. `ARCHITECTURE.md` already makes predicates and actions registries keyed by
  stable ID; this is why.
- Content growth is new blocks, not new modes. A season ships blocks.

## 2. It is an extraction game — 2026-09-06

> I'm basically looking at this game like Escape from Tarkov. You enter, try to get new
> cool things, and then get out. If you don't get out you lose stuff.

> They discover new things in the caves as they branch further into them.

**What it binds.**
- The match is a raid: commit a loadout, go in, get out before the window closes.
  Extraction mode (Phase 3) is the core mode, not one of several.
- Losing means losing things. A dead agent leaves a wreck holding its cargo and its
  policy, in the cave, for the rest of the match. That is already in the design (wrecks)
  and is load-bearing, not flavour.
- **The cool things are new blocks, and they are found by depth.** Further in is where
  the blocks you do not have yet are — past the sump, past the machinery, past where the
  beacon chain still holds. The cave has a loot table by depth. The machinery's `yields()`
  seam is one source; the Phase 3 cave generator must place discoveries by depth, not
  uniformly.
- Drift is what makes depth expensive. The tension of the game is *I have something, I am
  getting lost, do I go one junction further?* Phase 1's Recall decision was that in
  miniature; Phase 2's `carrying_cargo` against `uncertainty > θ` is the same thing with a
  block attached to the reward. Any tuning that removes the possibility of not getting
  out removes the game.

**What it does not change yet.** Phase 2 stages its tutorial by run, not by depth, because
that is controllable and the phase is testing induction, not discovery. Depth-gated
discovery is a Phase 3+ content question.

## 3. There is a surface, and you teach there — 2026-09-08

> The training stuff will happen on the surface as well.

**What it binds.**
- The game has a surface: the pit-head, where the shaft comes up. It is where machines are
  kept, prepared, taught, and sent down, and it is the only place in the game with sky. Every
  art concept, every environment list and every plan that assumed the whole game was underground
  is short by one place.
- Teaching is a physical act in the world, not only a panel. The corridor test (Phase 2) is, in
  the fiction, a training course on the surface; the cave demonstrations are the same act
  underground. Both are the player's, and both feed the same induction.
- The surface is safe and lit; the cave is not. That contrast is the game's structure — Tarkov's
  stash and raid (§2) — and the art should make the descent feel like leaving somewhere.

**What it does not settle.** What the surface looks like, what the teaching interface is in the
world, and whether anything is at stake up there. Proposed, marked as proposals, in the vision
board under `docs/art/vision/`.

## 4. Dense, and futuristic enough to justify the robots — 2026-09-08

> This is a very solid start, but in the real game it's going to need way more detail. It
> can't just look like an empty hellscape, it has to be kinda a hellscape, but also
> futuristic enough where they have advanced robots. Way more detail needed in both the
> cave and above ground.

**What it binds.**
- **Density is a requirement, not a finish pass.** Every environment carries detail at three
  scales at once: what reads in silhouette, what reads at lamp distance, and what reads when
  a machine is standing on it. An empty corridor with good lighting is a failure even if the
  lighting is right. This applies to the surface as much as the cave — the pit-head is a
  working yard, not a clearing with a headframe in it.
- **Two technological registers, and the world is the collision of them.** The mine and the
  ancients' works are the hellscape: cast iron, water power, riveted plate, drowned and
  still running. The machines, their instruments and the pit-head's working equipment are
  the future: the player's side is manufactured, modular, powered and clean-edged by
  contrast. Neither register alone is the look. A frame that shows only ancient iron reads
  as a period piece; a frame that shows only the players' kit reads as any science-fiction
  game. The image the game is after is the new bolted onto, lowered into and dwarfed by the
  old.
- **Advanced robots must be plausible in the frame.** If the world contains autonomous
  walkers, something in the world has to have built and serviced them. That evidence is the
  surface's job and it must be visible: the yard, the bench, the power, the handling gear.

**What it does not settle.** How far forward the players' register sits, and whether anyone
still lives here.

## 5. Procedural, and playable in Godot — 2026-09-08

> Don't do that in Blender though. We need to figure out how we are going to do all this
> procedurally and then have it playable in Godot.

**What it binds.**
- **Blender renders are targets, not the pipeline.** Everything in `docs/art/vision/` is
  concept art: a picture of what a frame should contain. Nothing in it ships. Any art
  decision is only real once a rule produces it procedurally at frame rate.
- **This applies to GENERATED content, not to AUTHORED content, and the difference is not
  subtle.** *(Scoped 2026-09-09, after I got it wrong.)* The cave is generated per match, so it
  cannot be hand-modelled and cannot be unwrapped, which is what `ART-DIRECTION.md` §9's "no
  hand-modelled asset" rule is actually about. A machine is not generated per match. It is
  authored once, shipped as content, and instanced. **Machines, modules, the ancients' machinery
  and the pit-head's fixed structures are modelled assets**, and `agent_model/` — a Blender rig
  with all four chassis, their legs, slots, modules, skins and a working gait — is the model. It
  gets exported and imported, not rebuilt in engine. Rebuilding an authored asset procedurally
  because a rule about caves said "procedural" is a category error, and it cost a stream of work
  before the designer caught it.
- **The density in §4 has to come from rules, not from modelling.** A hand-built cave cannot
  be generated per match, and the game generates a cave per match. So every piece of dressing
  named in §4 must be reachable as a placement rule, a material rule or an instanced kit
  part, and the art direction has to be written in those terms.
- **The target is Godot 4, at frame rate, on the dev machine.** `ARCHITECTURE.md` already
  fixes Godot 4 via GDExtension with Rust. A look is not approved until it has been seen
  running there.
- **The generation seam.** `blindside-gen` is a constrained crate: no floats, no `HashMap`
  iteration, and its output is hashed into the replay. So generation splits in two. The
  deterministic layer produces the cave the simulation plays on — which cells are open,
  width class, where the deposits, the machinery and the water are — and every client agrees
  on it bit for bit. The dressing layer turns that into geometry and props from the same
  seed, is allowed floats, and lives on the client side. Nothing the dressing layer decides
  may ever reach the simulation, and the invariant stands unchanged: dressing is drawn from
  world truth for a spectator, never handed to a policy.

## 6. It has to look photoreal — 2026-09-09

> Yeah, I agree the materials and underfoot stuff sucks right now. Start working on that. It
> needs to look photoreal.

Said after walking the first two Godot spikes, which held frame rate with tens of thousands
of props but whose surfaces read as flat shaded blocks.

**What it binds.**
- **Photoreal is a material and surface problem, not a geometry-count problem.** The spikes
  already proved the budget: the cave runs faster dense than empty. What is missing is what a
  surface does with light — layered roughness, real normals at several scales, apparent depth
  underfoot, and the wetness that a drowned mine should have everywhere.
- **Underfoot is the hardest scale and the one that decides it.** A ground plane with a shader
  on it reads as a plane however good the shader is. The last metre and a half needs apparent
  or real displacement, half-buried aggregate, and wear that responds to what happened there.
- **Still procedural.** §5 stands: no hand-modelled assets, no photographic textures. Detail
  comes from generated noise, layered material rules and instanced geometry. Whether generated
  noise textures count as bitmaps is question 5 in `docs/spikes/PROCEDURAL-AND-GODOT.md`, whose
  default is yes, allowed, and photorealism depends on that default holding.
- **Frame rate is a constraint, not an afterthought.** Every material change is measured
  against the recorded baselines in the spikes. A look that costs the 60 is not a look.

**Two rules in `ART-DIRECTION.md` that this contradicts, and neither is resolved here.**
1. §3.1 fixes *one rock material, four scalars, no hue axis* and §9 forbids any hue axis
   anywhere. Real rock varies in hue as well as value, and mineral staining in a wet iron mine
   is strongly coloured. Photorealism and the no-hue rule cannot both hold literally.
2. §9 forbids *no image texture, UV map or bitmap*. The intent was that a generated cave cannot
   be unwrapped, which remains true; the letter also forbids the generated noise textures that
   physically based materials need.
Both need a designer ruling. Until then the spikes treat the *intent* as binding — one rock
family, world-space mapping, nothing unwrapped, nothing photographic — and the letter as
amendable.

## 7. Density is order, not scatter — 2026-09-09

> I don't know what you are doing... the random shit thrown all over on the surface looks
> like an abandoned scrap yard and that is not the vibe at all.

Said looking at the pit-head after the density pass. The pass was mine and the fault is in how
I briefed it: §4 asked for detail at three scales without saying detail *of what*, and uniform
random scatter is the fastest way to fill a frame. It is also exactly how you draw abandonment.

**What it binds.**
- **Every object answers who put it there and why.** If that question has no answer, the object
  is litter, and a frame full of litter reads as a site nobody works at. Density comes from
  purpose: things in rows, in racks, in marked bays, on pallets, aligned to the site's own grid
  and to each other, because a person or a machine put them down deliberately.
- **The pit-head is a working facility, not a ruin.** The mine below is dead and drowned; the
  operation above it is live. That contrast is the whole point of having a surface (§3), and
  the art has to carry it. Somebody swept this yard this week.
- **Clear ground is a feature.** Traffic lanes, turning circles, the apron in front of a bay
  and the ground a machine walks are kept clear, and their emptiness reads as use. Uniform
  cover is the tell.
- **Weeds, debris and standing water belong in the margins only** — behind buildings, along
  fences, in corners nothing crosses. Growing through the middle of a working apron says
  nobody has walked there in a year.
- **Repetition reads as manufactured.** The players' register is modular and mass-produced, so
  identical units in an aligned row say "somebody built these" far more strongly than the same
  objects rotated randomly. This is also the cheapest possible fix for §4's complaint that
  advanced robots are not plausible in the frame.

**The instrument this changes.** Placement stops being weighted random scatter over a surface
class and becomes a small number of *arrangements* — a rack, a row, a bay, a stack, a lay-down
area, a queue — each with its own footprint, spacing and alignment, placed against the layout's
zones. Randomness sets which arrangement and what it holds, never the position of each object.

## 8. The sensor is simulated for real - 2026-09-09

> The real simulated lidar sensor is wayyyy better.

Said comparing the first belief render, which placed points from a sparse range/bearing model
and looked like glowing mist, against one that models a spinning array of emitters raycast
against the actual world.

**What it binds.**
- **Returns are produced by simulating the instrument, not by decorating a position.** A fixed
  set of beam elevations, a spin rate, a firing rate, a range envelope, and a ray that stops at
  the first thing it hits. Everything that makes the view read - ring structure, occlusion
  shadows, density falling off with range, intensity varying with incidence - is a consequence
  of that, and none of it can be faked convincingly on top of a cheaper model.
- **Occlusion is the machine's ignorance made visible.** A sensor shadow is a region the machine
  genuinely has no information about, which is this game's subject. `ART-DIRECTION.md` section
  8.2 now forbids drawing anything into one.
- **The sensor becomes a gameplay object.** If beam count, spin rate, range and noise are real
  parameters, then a better sensor is a real advantage, a damaged one is a real loss, and what a
  machine can perceive is something the player equips, upgrades and can be deprived of. That
  connects the instrument straight to the extraction loop in section 2.
- **It forces a data decision.** Ten hertz is on the order of a hundred million returns in a
  match. The live sweep and the accumulated map must be different objects, and the map has to be
  reduced at the source rather than stored raw.

**What it does not settle.** The parameters. The measured recommendation is 32 rings over -30 to
+12 degrees, 1024 azimuth steps per revolution, 10 Hz, and 0.55 to 40 m, pointing further down
than an automotive unit because underground you need the near floor and the crown. Also
unsettled: dust and water as multi-return failure modes, which underground is not a detail but a
sensor failure with gameplay in it.

## 9. Belief should be rich, so that technique can differ - 2026-09-09

> We also need to make as much data available (in the vehicle belief) as possible so players
> can experiment with different techniques that utilize different data inputs.

**Why this is safe, and it is the one place in this design where "more" costs nothing.** The
invariant is that a policy may never observe ground truth. Belief is by definition what the
machine's own sensors and estimator produced, so anything derived from it is already legal for a
policy to read. Enriching `World` would be a catastrophe; enriching `Belief` cannot break the
invariant at all. The only costs are determinism, budget and legibility.

**What it binds.**
- **The estimator publishes everything it already knows.** Today `Belief` exposes a pose, an
  uncertainty scalar and a point cloud, and throws away most of what it computed on the way:
  the full covariance rather than one sigma, the size and time of the last correction, returns
  per sweep, how much of the last sweep came back at all, how far it has walked since a fix, how
  long since it saw a given place. None of that is new sensing. It is refusing to discard.
- **Derived structure counts as belief.** Frontiers between mapped and unmapped, clearance at a
  point, passage width, whether the map disagrees with itself where two passes overlap, how long
  since a region was last observed. These are computed from belief and are therefore belief.
- **Two layers, not one.** The rich data is the substrate; the base blocks of §1 are curated,
  named views over it that arrive progressively. Both exist at once. A beginner composes the
  blocks they have been given; someone who wants to build a technique nobody has tried reaches
  past them into the substrate. Discovery introduces the block, not the data - the data was
  always there, which is what makes a discovery feel like a realisation rather than a permission.
- **Different inputs are how techniques differ.** A game where everyone reads the same three
  numbers has one solved strategy. A machine that turns back on uncertainty, one that turns back
  on sensor health, and one that turns back on how long since it last recognised anything are
  three different animals, and the difference lives in what they read, not in how the tree is
  shaped.
- **It changes what a module is worth.** §8 made the sensor a real instrument; this makes what
  the instrument produces legible to a policy. A better sensor is then not just a longer range,
  it is new signals to build on.

**What it costs, and none of it is optional.**
- **Determinism.** Everything published is hashed into the replay and must be fixed-point and
  iteration-order stable, per `DETERMINISM.md`. A signal that cannot be computed deterministically
  cannot be published.
- **Budget.** Every published signal is computed every tick for every agent, so each needs a cost.
  Some are free by-products; some, like map self-disagreement, are not.
- **Legibility.** A vocabulary of two hundred signals is not a richer game, it is an unusable one.
  The curated layer is what stops that, and the substrate needs to be discoverable by someone
  looking for it rather than dumped in front of someone who is not.

**The one edge on "enriching belief cannot break the invariant", found while cataloguing.** A
quantity derived from belief *plus one truth-side constant* is a truth leak wearing a belief
costume. The example that will keep being asked for is *how much of the cave have I explored*:
the numerator is belief, the denominator is the size of the cave, and the size of the cave is
ground truth. There is no legal way for a machine to know it. So the test for a proposed signal is
not "is it derived from belief" but **"could a machine compute this from what it has actually
sensed, with no constant it was never told"**. Publish the numerator and let the player decide what
enough means.

**What it does not settle.** Which signals exist, what each costs, which are base blocks on day
one, and whether the substrate is reachable in the node editor at all or only through blocks. The
catalogue is `docs/BELIEF-CATALOGUE.md`: 100 signals in ten families, of which 85 need no new
sensing, 35 are computed today and read by no policy, and one is refused outright.

## 10. It is a world coming out of an ice age - 2026-09-09

> It's a society that lives in a world that is coming out of an ice age and discovering the
> society that existed pre ice age. So it's all monotonous and snowy and pretty, they live in a
> valley in a somewhat futuristic town. That also explains why there are caves. That also opens
> it so the caves have depth and aren't just flat 2D caves.

**This is the largest single decision in the project and it reframes every other document.**
Everything before it treated the setting as an abandoned iron mine with a vague past. It now has a
period, a reason, and a shape.

**What it binds.**
- **The ancients are a pre-ice-age civilisation**, not a defunct company from a decade nobody
  named. They are separated from the player's society by an ice age, which is why nobody ever came
  back for the survey, why the index has no living register, and why a machine that a player finds
  in the dark is genuinely from another world rather than merely old.
- **The player's society is recovering, not declining.** They live in a valley in a somewhat
  futuristic town, and they are the ones with the advanced machines. That answers §4's demand that
  the world be futuristic enough for autonomous robots to belong in it, and it answers it better
  than the pit-head did: this is a society with real technology, deliberately going down into an
  older one.
- **The surface is snow, and it is beautiful.** Monotonous, white, quiet, a valley under a large
  sky. That is the strongest possible contrast with a black cave lit by one lamp, and it is a much
  better contrast than an industrial yard under overcast, because it is *pretty* — the player is
  leaving somewhere worth being.
- **The caves have depth, and vertical is now a real axis.** Glacial systems are vertical: shafts,
  moulins, crevasses, meltwater cutting downward. The cave stops being a flat plan of passages and
  becomes a place with levels, drops, and things below other things. `blindside-gen` has to carry
  height as a first-class dimension rather than as dressing, and going *deeper* becomes literal.
- **Ice explains the water.** The mine drowned because the ice melted, the sumps are meltwater, and
  the machinery runs because meltwater is abundant. The existing fiction's flooding and its
  water-powered machinery both survive this change and are strengthened by it.

**The reframe this opens, and it is the strongest beat available: the machinery did not never
stop. It started again.** The ancients built it, the ice came, it froze and stood silent for as
long as the ice lasted, and when the melt reached it the water turned the wheel and it resumed a
survey for a client who has been gone since before the ice. That is more frightening than a
machine that simply kept going, it explains why it is intact rather than worn to nothing, and it
gives the player's society a reason to be here *now*. **Proposed, not decided** - it changes
`THE-MACHINERY.md` §1 and `WHAT-HAPPENED-HERE.md` §1, both of which currently say it never stopped.

**What it costs.** The pit-head as built is a wet industrial yard under grey cloud, and the
recorded lighting recommendation is overcast. Snow changes the ground material, the light, the
palette, the weather states and the whole first act of the trailer. `ART-DIRECTION.md` §2.1 makes
the shaft's 12000 K the only daylight in the game, which snow-lit exteriors do not survive
unchanged. The reconciliation is `docs/THE-ICE.md`.

**What it does not settle.** How long the ice lasted, how far the melt has gone, whether the
player's society knows what it is digging into, and whether anyone alive remembers the ancients as
people rather than as a layer.
