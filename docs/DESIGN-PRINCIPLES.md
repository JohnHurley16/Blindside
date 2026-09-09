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
