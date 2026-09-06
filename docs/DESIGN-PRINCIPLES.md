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
