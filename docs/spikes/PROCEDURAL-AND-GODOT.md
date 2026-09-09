# Procedural, and playable in Godot

A spike, not code. It answers `DESIGN-PRINCIPLES.md` §5 — *"we need to figure out how we are
going to do all this procedurally and then have it playable in Godot"* — by making the seam in
that section precise, testing it against `DETERMINISM.md`, `ARCHITECTURE.md`, `art/ART-DIRECTION.md`
and `PHASE-3-OPEN-QUESTIONS.md`, and saying where it breaks.

**Nothing here is buildable yet and most of it should not be built yet.** §6 says so plainly.
Every number is either cited to a document that measured it or marked **[estimate]**.

**Repository state this was written against:** `crates/` contains `blindside-induct` only;
`tools/` contains `render_dev_plan.py` only. `tools/determinism-lint` is specified (BLD-21,
BLD-26) and does not exist. `blindside-gen` does not exist. Phase 1's cave is a hand-authored
dict of eleven chambers (`phase1/truth/cave.py`); there is no generator to have a bug in.

---

## 0. The four findings, before the detail

1. **The seam is a function, not a file.** `blindside-gen` is float-free, so the client can
   *link it and re-run it* rather than receive its output. The thing that crosses is a ~12 kB
   `CavePlan` **[estimate, arithmetic in §1.4]** and, in the limit, just a `u64` seed. This is
   the cheapest possible answer and it is available only because the crate is constrained.

2. **That is also the largest new leak in the project.** Pure generation plus a shared seed
   means *anyone holding the seed holds the entire true cave*, including every deposit, before
   the match starts. DESIGN gives every team the same seed. Nothing in the type system stops
   this; purity is the vulnerability. §2.1.

3. **Nine-tenths of the designer's ask is not a run-phase problem.** `ART-DIRECTION.md` §8.3:
   belief-only is *"the default live view, because it is what the player is legally allowed to
   see."* The dense, lit, dressed cave is a **replay and spectator asset**, and the dense yard
   is the **surface**, which is the same place every match and therefore not generated at all.
   Neither is a per-frame streaming problem in the run phase. §5.
   The corollary is uncomfortable and is stated in §5.4: **the one-lamp light economy and a
   free spectator camera cannot both be right**, and somebody has to rule.

4. **Density is affordable because the light economy makes 96–99% of the world unnecessary at
   any instant** **[estimate; measurable in an afternoon once BLD-72 exists]**. That is the
   whole performance argument, and §5 is the most important section here.

---

## 1. The two-layer split

### 1.1 Where the line is

`DESIGN-PRINCIPLES.md` §5 draws it: the deterministic layer decides *what is where*, the
dressing layer decides *what it looks like*. Made precise, `blindside-gen` exposes **three**
functions, not two, and the middle one is the part §5 did not name:

```rust
// blindside-gen — constrained crate. No f32/f64, no HashMap iteration, no std::time.
pub fn plan(seed: u64, biome: BiomeId, content: &ContentPack) -> CavePlan;   // ~12 kB, hashed
pub fn rasterise(plan: &CavePlan) -> Cave;                                   // ~1.2 MB, the grid
// client-side, unconstrained. floats allowed.
pub fn dress(plan: &CavePlan, cave: &Cave, chunk: ChunkId, kit: &DressingKit) -> ChunkGeometry;
```

`rasterise` is float-free and **shared**. The client does not build its mesh from its own
interpretation of the plan; it builds it from the same cell grid the sim locomotes over
(BLD-71's *"single cell-classification query"*). This is not tidiness. If the mesh and the
collision grid disagree, the replay shows an agent walking through a wall or standing in
one, and the replay is the screen ROADMAP Phase 5 calls the most important in the game.

So the split is:

| | decides | crate | floats | in the cave hash | reaches the client |
|---|---|---|---|---|---|
| **plan** | chambers, passages, water, deposits, ancients, discoveries, feature anchors | `blindside-gen` | no | **yes** | replay/spectator only (§2) |
| **rasterise** | per-cell classification + heightfield | `blindside-gen` | no | yes (derived) | replay/spectator only |
| **dress** | mesh, scatter, props, materials, decals, particles, LOD | `blindside-client` | yes | **no** | is the client |

### 1.2 The interface, field by field

```rust
// blindside-gen/src/plan.rs — the entire seam between the layers.
// Integers and Fx only. Every collection is an ordered Vec; ids are indices into it.
// DETERMINISM rule 2: no map is iterated anywhere in this file.

pub struct CavePlan {
    pub schema:       u16,          // bump on any field change; replays carry it
    pub seed:         u64,
    pub biome:        BiomeId,      // u16, permanent content id (P3-OQ §1)
    pub content_hash: [u8; 32],     // the season-enabled set (P3-OQ §3)
    pub extent:       (u16, u16),   // cells. benchmark: (400, 240)  [P3-OQ §38]
    pub cell_mm:      u32,          // millimetres per cell. ONE number. see Q1
    pub chambers:     Vec<Chamber>,
    pub passages:     Vec<Passage>,
    pub shafts:       Vec<Shaft>,
    pub deposits:     Vec<DepositSite>,
    pub ancients:     Vec<AncientSite>,
    pub discoveries:  Vec<DiscoverySite>,
    pub features:     Vec<Feature>,
}

pub struct Chamber {
    pub centre:       CellPos,      // (u16, u16)
    pub radius_cells: u8,           // 5..12  [P3-OQ §38]
    pub floor_mm:     i32,          // heightfield datum
    pub ceiling_mm:   i32,          // >= every passage that reaches it. see §1.6
    pub depth_band:   u8,           // 0..15, quantised BFS distance from the nearest shaft
    pub worked:       u8,           // 0..255, natural karst -> machine ground (ART §3.1)
    pub integrity:    u8,           // 0..255
    pub water_mm:     i32,          // waterline height; i32::MIN = dry
}

pub struct Passage {
    pub from:         NodeRef,      // Chamber(u16) | Shaft(u16) | Junction(u16)
    pub to:           NodeRef,
    pub spine:        Vec<CellPos>, // the carve path, ordered, ~1 point per 4 cells
    pub width_class:  WidthClass,   // Crawl | Narrow | Passage | Hall  [P3-OQ §25]
    pub worked:       u8,
    pub integrity:    u8,
    pub depth_band:   u8,
    pub water_mm:     i32,
    pub rock:         u8,           // absorbent (0) .. reflective (255). ART §3.1 `fracture`
    pub sediment:     u8,           // ART §3.5: volumetric only, never a surface effect
    pub thermal_mm:   i32,          // layer height; the 0.3 m haze band (ART §3.5)
    pub furniture:    u16,          // bitset: RAIL | GUTTER | BOLT_LINE | TIMBER_SETS |
                                    //   BUS_CONDUCTOR | LAUNDER | PIPEWORK | SLEEPERS
}

pub struct Shaft   { pub at: CellPos, pub team_slot: u8, pub chamber: u16, pub daylight: bool }
pub struct DepositSite   { pub at: CellPos, pub value: Fx, pub region: u8, pub face_facing: u8 }
pub struct AncientSite   { pub at: CellPos, pub kind: AncientKindId, pub aim: u8, pub chamber: u16 }
pub struct DiscoverySite { pub at: CellPos, pub block: BlockId, pub depth_band: u8 }  // P3-OQ §33

pub struct Feature {
    pub kind:       FeatureKindId,  // u16, permanent content id, in the retired ledger
    pub at:         CellPos,
    pub facing:     u8,             // 0..63; a 5.625-degree quantum
    pub span_cells: u8,             // runs use this; a point feature is 1
    pub variant:    u8,             // which of the kind's variants
    pub depth_band: u8,
}
```

**`Feature` is small on purpose, and that is the design decision that makes this affordable.**
A `Feature` records a *placement decision*: this survey plate, this collapsed timber set, this
muck pile, this pump chamber. Anything that repeats on a rule is **not** in the plan — a rail
run is one bit in `Passage.furniture`, and the dressing layer expands it into sleepers every
0.6 m and sets every 1.2 m (ART §3.3's module) by rule, with the per-round phase offset derived
from a hash of `(passage_index, spine_index)`. Recording every timber set individually would be
tens of thousands of entries for no decision content.

### 1.3 What is deliberately not in it

- **No geometry.** No vertices, no normals, no heights except `floor_mm` / `ceiling_mm` datums.
  The heightfield is `rasterise`'s output, derived, not carried.
- **No materials, no colours, no light.** Those are the dressing kit's (§3).
- **No runtime ids.** `DepositSite` is an index in this plan; the sim's `DepositId` is
  record-assigned (P3-OQ §18, BLD-69). Two different id spaces, deliberately.
- **No floats.** `Fx` is `I32F32` and serialises as its integer bits.

### 1.4 Size, and the two numbers that matter

Sized against the benchmark cave (400 × 240 cells, ~17% free, chambers r 5–12 joined by carved
passages — P3-OQ §38, itself marked **[guess]** there):

- 96,000 cells, **16,320 free**. Phase 1's 200 × 120 grid had 11 chambers; scaling by area gives
  **~44 chambers and ~70 passages** **[estimate]**.
- Chambers: 44 × 24 B ≈ **1.1 kB**.
- Passages: 70 × (28 B scalars + a ~10-point spine at 4 B) ≈ **4.8 kB**.
- Features: ~300 × 10 B ≈ **3.0 kB** **[estimate: 2 per chamber, 3 per passage, plus sites]**.
- Shafts, deposits, ancients, discoveries: **< 1 kB**.

**`CavePlan` ≈ 10–15 kB uncompressed [estimate]; ~4 kB zstd.** The rasterised grid, at ~12 B per
cell, is **~1.15 MB**. That is the ratio the split buys: two orders of magnitude.

Both are irrelevant to the wire, because **nothing is sent**. The plan is a pure function of
`(seed, biome, content_hash)`; a replay already carries all three in `MatchRecord`. The network
payload for the whole cave is the 8 bytes of seed that are already there — which is exactly the
problem in §2.1.

Hashing: blake3 over the plan's canonical byte encoding. BLD-72's *"cave hash golden in CI"*
should hash **the plan, not the raster** — it is 100× smaller, it is the thing a human can diff
when the golden moves, and the raster is a pure function of it, so a plan match implies a raster
match given the same build.

### 1.5 Must dressing be identical across clients?

**Reproducible, not bit-identical. And the competitive-fairness argument that appears to demand
bit-identity does not apply, because no player ever sees dressed truth during a match.**

The chain, each link citable:

1. `ART-DIRECTION.md` §8.3 — belief-only is *"the default live view, because it is what the
   player is legally allowed to see."*
2. BLD-144 — the live FFI exposes only named Belief-derived snapshot types; *"a test enumerates
   the FFI exports and fails the build if any type from `blindside-sim`'s `world.rs` (or any
   type carrying a true position) is reachable from the live-run host."*
3. BLD-148 — the cave mesh *"is a replay and reveal asset"*.

So dressing cannot hide a deposit from one player and show it to another during play: **neither
player is shown the cave at all.** Identity is therefore a *reproducibility* requirement — two
people discussing the same replay must be looking at the same picture, a bug report must
reproduce, a screenshot must be evidence — and not a fairness requirement.

What that buys, and what it still requires:

**Binding (the guarantee):**
- Every fact that exists is in the plan. **The dresser may not create, move, or delete anything
  the plan names.** It chooses subdivision, displacement amplitude, prop rotation, scatter
  jitter, LOD, particle counts, material response.
- **Decisions are made on integers; floats are only continuous outputs.** The dresser's
  randomness is counter-based and stateless, exactly as `DETERMINISM.md` rule 4 requires of the
  sim: `dress_draw(plan_hash, chunk_id, slot, purpose) -> u32`. A float may be *derived* from a
  draw (a rotation angle, an offset) but a float never *keys* a decision. This costs nothing and
  makes the dresser a pure function of `(plan_hash, chunk_id, kit_version)`.
- **Nothing that must be seen may be carried by dressing alone.** A deposit is a `DepositSite`
  with an index; the spectator UI labels it from the plan. If the dresser scatters a boulder in
  front of the muck pile, the label is still there. This is the rule that makes the fairness
  question moot even if the answer to Q2 below changes.

**Not required:** bit-identical float results across GPUs, drivers and Godot versions. Demanding
that would forbid floats, which is the entire point of having a second layer.

**The version that must travel:** the kit is content the artist edits without invalidating
replays (§3), so it is *not* in `content_hash` — but a replay watched with a different kit looks
different. The replay header carries `kit_version: u32`; a mismatch shows a banner, not a
refusal.

**The one condition that would flip this answer** is in Q2: if a live, truth-visible spectator
feed is ever available to a *participant* — a teammate on voice, a coach — then dressed truth is
back inside the competitive loop and legibility becomes a fairness property. That is a design
decision about who may watch, not an art decision.

### 1.6 Two documented design requirements the plan exists to satisfy

`ART-DIRECTION.md`'s "design problems found" list names two things `blindside-gen` must do that
nothing else can fix:

- **#3 — flooding must rise monotonically with depth.** Measured on Phase 1's hand-authored
  cave, flooding by depth quartile is **0.0% / 17.1% / 30.8% / 0.0%**; the deepest quarter is
  bone dry, and the whole deep-is-wet-is-dark-is-specular chain in ART §3, §5 and §7 rests on
  the opposite. `Passage.water_mm` and `Chamber.water_mm` are generated from `depth_band`, with a
  post-condition test over 1,000 seeds.
- **#4 — chambers must be taller than the passages that reach them.** Otherwise the Assayer's
  6.6 m mast does not fit and nothing in a chamber is visible from outside it. `Chamber.ceiling_mm`
  exists so this is a checkable invariant of the plan rather than an art complaint.

Neither is expressible in a raster. Both are one line in the plan and one assertion in a test.

### 1.7 A free by-product

`Passage.spine` is a passage skeleton. P3-OQ §39's fallback — *"BLD-79 adds a skeleton-derived
passage-axis bearing as a direction-only side structure"* — currently costs a separate 8-bytes-
per-cell structure and 6 ms per cave. If the generator is chambers-plus-carved-passages (§38),
the plan already holds that skeleton and the fallback is free. Worth telling BLD-79.

---

## 2. Where the invariant could leak

`CLAUDE.md`: an agent's policy may never observe ground truth. A player who sees truth is not,
strictly, a policy reading `World` — but the player is inside the control loop (the command
channel, BLD-105: Recall), so **player-visible truth is a truth path into agent behaviour
laundered through a human**, and ART §8.3's word for the belief-only live view is *legally*.
Both are treated as leaks below.

### 2.1 The generator itself — the new one, and the largest

**`plan()` is pure and takes the seed. DESIGN gives every team the same seed. Therefore any
client that can call it holds the entire true cave — every deposit, every ancient, every
discovery — before commit.** No amount of module privacy helps: the function is correct, it is
deterministic by design, and that is precisely what makes it a map generator for a cheater.

This leak does not exist today because there is no generator. It arrives with BLD-72 and it is
not covered by BLD-75 (compile-fail tests) or BLD-76 (the sanctioned truth export), both of which
guard *values*, not *the ability to recompute them*.

What stops it, in order of strength:

1. **The live client never receives the match seed.** This is the real fix and it is cheap,
   because on inspection the live client needs the seed for nothing: the run view is Belief, the
   surface is not generated (§5.5), and any presentation randomness can use an unrelated
   `presentation_seed`. **This must be written into BLD-162 (transport and protocol) now**, while
   it is a sentence, rather than discovered in Phase 6 when the wire format exists.
2. **`blindside-gen` is not in the live client's dependency graph.** Extend BLD-29's
   `cargo tree -e features` guard from *features* to *crates*: the live host binary must have no
   path to `blindside-gen`, `world.rs`, or `ReplayFrame`. A dependency-graph assertion is stronger
   than a grep and it is one CI line.
3. **Benchmark seeds are never used in live matches.** BLD-108 fixes a benchmark seed set and
   ROADMAP Phase 9 auto-evaluates listings against it; those seeds are public by construction.
4. **Honest limit.** Against a modified client that has the seed, this is unwinnable. So the
   requirement is (1), stated as an absolute.

### 2.2 The dressing layer feeding a sensor

The tempting version: lidar should hit the *dressed* mesh — the rails, the timber, the boulder —
because the cell grid is coarse. That puts float geometry into the sim and breaks determinism and
the invariant at once.

Stopped by: `SensorEnv` (BLD-74, P3-OQ §9) offers raycasts against the **cell classification**
only, and `blindside-sim` depends on `blindside-vm` and `blindside-content` and nothing else
(ARCHITECTURE). The dresser is not reachable from the sim by the dependency graph.

**The consequence is a design problem, not a bug: props are invisible to sensors, and they are
also not solid.** A rail is a thing you can see in the replay and cannot detect, walk into, or
hide behind. This is consistent with ART §8's rule — *"any sentence of the form 'and then the
agent can see X in the world' must be checked against what the sensor actually returns"* — but it
means **dressing may never be cover, obstruction, landmark or hazard.** If the designer wants a
prop to matter, it must be promoted into the plan and into the cell classification, which makes
it sim state, hashed, and paid for in the acoustic and locomotion budgets. Q7.

### 2.3 The replay host inside the live process — the GDScript hole

This is the one the Rust tests do not cover, and it is the direct descendant of what
`phase1/match/invariant.py` and `phase2/match/invariant.py` already document about Python.

GDExtension registers classes into Godot's global `ClassDB`. GDScript is dynamic. So in a single
process holding both hosts:

```gdscript
var h = ClassDB.instantiate("BlindsideReplayHost")   # never imported, never named at build time
```

reaches the truth host past every `trybuild` case in BLD-75. `phase2/match/invariant.py` says the
same thing about Python — *"the modules that hand out other modules (`importlib`, `builtins`,
`sys`, `inspect`, `ctypes`, `gc`) may not be imported at all, under any alias"* — and its
`MODULE_FETCHERS` / `FETCHER_NAMES` lists exist because a verifier defeated the by-name version
four ways.

**The Rust/Godot equivalent of `invariant.py` is three tools, not one.** Only the first is
already on the board:

| # | mechanism | catches | on the board |
|---|---|---|---|
| 1 | `trybuild` compile-fail cases | any Rust code naming `World`, `ReplayFrame`, or a truth type from the wrong module | **BLD-75**, exists |
| 2 | a `cargo metadata` assertion on the live host binary's dependency graph | `blindside-gen`, `blindside-sim::world`, the replay host, reachable at all | partly BLD-29; **needs extending** |
| 3 | an AST check over `.gd` and `.tscn`, plus a runtime registration assertion | `ClassDB.instantiate`, `load`, `ResourceLoader`, `Engine.get_singleton`, `get_node` on a constructed string, anywhere in the run-phase scene tree | **does not exist.** BLD-145 has a one-line grep; this is the real version |

Tool 3 should be `tools/invariant-gd/` and should port `invariant.py`'s actual lesson rather than
its rule list: **refuse the reflection machinery by shape, not the target by spelling.** Plus the
belt-and-braces version that Python could not have: **the run-phase build does not register the
replay classes at all** — a separate GDExtension library, or a feature-gated `register_class` and
a distinct export preset — with a `_ready()` assertion that `ClassDB.class_exists("BlindsideReplayHost")`
is false. That is a structural refusal, and `phase1/match/invariant.py`'s rule 8 ("structure, not
spelling") is the precedent.

### 2.4 The per-seed mesh cache on disk

BLD-148: *"Mesh build ... is cached per seed."* A cache written during a replay of seed X and
readable during a later live match of seed X is a truth file on the player's disk. Rule: the cache
key is the match id, not the seed; the cache is refused while a live match is running; it does not
survive the session. Cheap, and it must be said before BLD-148 is written.

### 2.5 Audio

The dresser naturally wants to place sound emitters in world space, at true positions. Phase 1 got
this right — the mixer was driven entirely from Belief, contacts panned by bearing — and BLD-151
carries it forward. Name it here because "the dressing layer" is exactly the component that would
undo it without noticing: **in the live client, an emitter's position is a believed bearing, never
a true position.**

### 2.6 The surface

`DESIGN-PRINCIPLES.md` §3 is new and every environment list is short by one place. The pit-head is
dressed from truth and there is no drift there, so truth and belief nearly coincide — but the
training course (Phase 2's corridor made physical) runs a policy on the surface, and that policy
reads `Belief` like every other. The surface is not an exception; it is a place where the invariant
is cheap to satisfy and therefore easy to forget.

### 2.7 Which P3-OQ decisions this section depends on

§9 (`Sensor::sample` sees `SensorEnv`, never `&World`), §18 (World collections and record-assigned
ids), §3 (the content hash covers the season-enabled set), §33 (`BlockId`, discoveries by depth).

---

## 3. How density is authored

The question that decides whether ART is reachable: **what does a person edit to make the world
denser, and is it Rust?** Answer: three files, none of them Rust, and they are in two different
formats for a reason.

### 3.1 Three tiers

| tier | file | edited by | changes | in `content_hash`? | invalidates replays? |
|---|---|---|---|---|---|
| 1. **Generation rules** | `content/biomes/*.toml`, `content/features/*.toml` | designer / technical artist | what the generator *decides*: chamber counts, width-class mix, depth loot table, feature kinds, placement constraints, weights | **yes** | **yes** |
| 2. **Dressing kit** | `client/dressing/*.tres` (Godot Resource) | artist, in the Godot inspector | which recipe each `FeatureKindId` draws, its parameters, scatter density per surface class, LOD and visibility distances | **no** | no |
| 3. **Materials** | one `rock.gdshader` + four scalars per cell (ART §3.1) | shader author | what stone looks like | no | no |

**The tier-1/tier-2 boundary is the same line as §1's plan/dress line, and the hash column is why
it must not move.** If scatter density were in `content_hash`, an artist raising the boulder count
would break every stored replay (P3-OQ §3). If chamber count were in a `.tres`, two clients would
disagree about the cave. The boundary is: **tier 1 changes what exists; tier 2 changes what it
looks like.**

Tier 1 is TOML with every `Fx` as a decimal string, per P3-OQ §40, loaded by the unconstrained
`blindside-content-loader` (§41). Tier 2 is a Godot `Resource` because the editor gives an artist
an inspector, live reload and no build step, and because ART says plainly *there is no art team* —
the person editing it is probably the designer, and a text format is a worse tool for them.

### 3.2 Tier 1: a feature kind is a constraint struct, not an expression language

```toml
[[feature]]
id        = 12                  # FeatureKindId. permanent, in retired.toml (P3-OQ §1, §2)
name      = "survey_plate"
scan      = "passage"           # cell | passage | chamber | junction | deposit
rate      = "0.021"             # expected count per 100 cells of the scan unit; Fx string
requires  = ["wall_adjacent", "above_waterline"]
forbids   = ["natural"]
worked    = { min = "0.4" }     # inclusive ranges over plan/cell attributes
depth_band = { min = 2 }
facing    = "wall_normal"       # wall_normal | spine | fixed | random
variants  = { weights = ["3", "2", "1"] }
```

**Recommend the constraint-struct form, not a predicate expression language.** A little language
over cell attributes is the obvious design, and `CLAUDE.md` says do not add features: a struct of
optional ranges plus two tag lists covers every placement in ART §3.4, §3.5 and §7, is total by
construction, cannot loop, needs no parser beyond serde, and is trivially deterministic. The
expression language is the growth path, and it should wait until a real placement cannot be
written in the struct.

Named tags (`wall_adjacent`, `on_spine`, `above_waterline`, `below_waterline`, `dead_end`,
`junction`, `natural`, `ceiling_above(n)`) are a fixed enum in `blindside-content`, not free text.
Adding one is a Rust change; adding a *feature* is not, which is the correct split.

Placement is a single ordered scan over the plan's own vectors with `dress_draw`-style stateless
draws keyed by `(scan_unit_index, feature_kind, slot)` — no shuffling, no accept/reject loop with
a mutable RNG, and therefore no ordering hazard (DETERMINISM rule 4).

### 3.3 Tier 2: weighted scatter by surface class

Surface classes are derived from the rasterised grid and the plan, not authored: `floor_dry`,
`floor_wet`, `floor_submerged`, `wall_below_tidemark`, `wall_above`, `ceiling`, `worked_floor`,
`muck`, `spall`. The kit gives each class a table:

```
[scatter.floor_dry]
density_per_m2 = 1.8
recipes        = [ {name="breakdown_block", weight=5, scale=[0.4,1.4], align="gravity"},
                   {name="clay_mound",      weight=2, scale=[0.6,1.1]},
                   {name="rail_spike",      weight=1, requires="furniture:RAIL"} ]
lod_end_m      = 15.0
```

**The single number that answers the designer's ask is `density_per_m2`.** Making the cave denser
is editing that field in the inspector and pressing play. That is the whole reachability argument,
and if it is not true, ART is not reachable.

### 3.4 The "no hand-modelled asset" rule, and where it breaks

ART §9 rules out *"no hand-modelled asset. If a proposal cannot be expressed as a parameter, a node
graph or generator geometry, it does not ship."* Taken literally, that forbids a kit-of-parts, and
the kit-of-parts is how density gets authored.

The escape is that a kit part is a **parametric recipe**, not a mesh file: a timber set is
`(width, height, timber_section, sag, broken)`; an insulator is `(shed_count, skirt_radius,
pin_length)`; a rail is an extrusion along a spine. The vision board's `works-bus/` and
`works-plates/` renders are already exactly this. So the rule survives, but only under a reading
nobody has written down. Q6.

**Where it does not survive is the surface.** A headframe, a winding house, a gantry, a bench, a
handling crane — `VISION-BOARD.md` §A1–A9 — are not parametric recipes in any honest sense, and
the pit-head is the one place in the game that is the same every match, so generating it buys
nothing. **ART §9's rule was written for the cave and should be scoped to the cave.** Q11.

---

## 4. The Godot side

Godot 4.7 shipped in June 2026 with HDR output, `AreaLight3D`, the low-level Vulkan plumbing for
ray tracing, and a `MeshLibrary` editor ([Phoronix](https://www.phoronix.com/news/Godot-4.7-Beta),
[release coverage](https://app.cinevva.com/news/2026-06-19-godot-4-7-released)) — **verify against
the official release notes before pinning; the press summaries are second-hand.** gdext supports
the 4.6 API level and has 4.7 preparation in its changelog ([gdext Changelog](https://github.com/godot-rust/gdext/blob/master/Changelog.md));
extensions load in any runtime ≥ their API level ([compatibility](https://godot-rust.github.io/book/toolchain/compatibility.html)).
**Which exact pair to pin is BLD-115's job and this document does not pre-empt it.**

Everything below marked **[verify]** is for the two running Godot proofs to settle; their
measurements win over anything here.

### 4.1 Mesh generation: Rust, not GDScript

`SurfaceTool` is the convenient path and the slow one — per-vertex method calls. The fast path is
`ArrayMesh.add_surface_from_arrays()` with pre-built `PackedVector3Array` / `PackedInt32Array`.

**Build the arrays in Rust and submit one `ArrayMesh` per chunk.** Reasons: it is the same code
that rasterises; it avoids per-vertex script calls entirely; and it is one FFI crossing per chunk
rather than tens of thousands. This does not violate ARCHITECTURE's *"do not write the whole client
in Rust"* — that rule is about UI and glue, and BLD-144's own criterion says *"all scenes, cameras,
overlays and panels are GDScript; Rust in the client is sim/replay hosting and FFI types only."*
Mesh construction from a truth grid is replay hosting. Say so in BLD-148 so the CI grep does not
fight it.

**[verify]** the cost of constructing a `PackedVector3Array` from a Rust slice across gdext — if
it copies element-by-element rather than memcpy, the chunk budget in §4.6 is wrong.

### 4.2 Chunking, and why it is not optional

Chunk = **32 × 32 cells = 19.2 × 19.2 m** at 0.6 m/cell. The benchmark cave is 13 × 8 = **104
chunks**.

Chunking is forced by the renderer, not chosen: Godot culls a `MultiMeshInstance3D` **as a whole**,
by its AABB. Per-instance frustum culling and per-instance mesh LOD for MultiMesh are an open
proposal ([godot-proposals #10669](https://github.com/godotengine/godot-proposals/issues/10669))
— **[verify] whether this landed in 4.6/4.7.** Until it does, one MultiMesh spanning the cave is
one all-or-nothing draw of every instance in the world. One MultiMesh per (chunk × material) is
the whole of the culling strategy.

### 4.3 MultiMeshInstance3D and the instance arithmetic

At 4 scatter instances per free cell across the whole cave: 16,320 × 4 ≈ **65,000 instances**,
≈ 630 per chunk **[estimate]**. Group by material rather than by recipe and use
`MultiMesh.use_custom_data` (a per-instance `Color`, readable as `INSTANCE_CUSTOM` in a spatial
shader) to select variant, and it is ~3 multimeshes per chunk instead of ~10: **~312
MultiMeshInstance3D nodes total, of which ~27 are visible** at the residency in §5. **[verify]**
that `INSTANCE_CUSTOM` is available to the fragment stage and survives the 4.7 shader changes.

Also: MultiMeshes, `GPUParticles3D` and CSG nodes **are not considered when baking occluders**
([occlusion culling docs](https://github.com/godotengine/godot-docs/blob/master/tutorials/3d/occlusion_culling.rst)).
Scatter can be occluded but can never occlude. In a cave that is fine, because the rock occludes.

### 4.4 LOD and visibility ranges

**Runtime mesh LOD effectively does not exist.** `SurfaceTool.generate_lod()` is deprecated and
loses normals and UVs; `ImporterMesh.generate_lods()` is the recommended path and is an
import-time/editor facility with reports of it not producing LODs when driven manually
([forum](https://forum.godotengine.org/t/unable-to-generate-lods-on-importermesh-automatically-or-manually/111326),
[proposal #6402](https://github.com/godotengine/godot-proposals/issues/6402)). A runtime-generated
`ArrayMesh` has no LOD chain and `ArrayMesh` has no `surface_get_lods()`
([proposal #6890](https://github.com/godotengine/godot-proposals/issues/6890)). **[verify] for
4.7.**

That is fine here, and the reason is measured: ART §3.6 puts the longest sightline anywhere in the
cave at **49.8 m**, p90 at **11.4 m**, and 90.8% of all directions under 12 m. Nothing is ever far
enough away to need a decimated version. **Visibility ranges replace LOD entirely.**

`GeometryInstance3D.visibility_range_begin` / `_end` plus margins and a fade mode work on
`MeshInstance3D`, `MultiMeshInstance3D`, `GPUParticles3D` and the rest
([visibility ranges](https://docs.godotengine.org/en/stable/tutorials/3d/visibility_ranges.html)),
which is exactly per-chunk granularity. Proposed settings, each derived from a cited number:

| layer | `visibility_range_end` | source |
|---|---|---|
| scatter, props, decals, particles | **15 m** | ART §3.6: *"spend no art budget past 15 m"* |
| rock shell chunks | **30 m** | ART §2.2: wall at 25 m is black |
| anything at all | **50 m** | ART §3.6: longest sightline in the cave is 49.8 m |

Margins ≈ 10% of the range, per the hysteresis note in the docs.

### 4.5 Occlusion culling, decals, particles, materials

- **Occlusion.** `OccluderInstance3D` with Embree, CPU-side, normally baked. Our geometry is
  runtime. **Do not derive occluders from the mesh — derive them from the rasteriser's solid map**:
  one box per fully-solid chunk region is accurate in a cave and costs nothing to build. **[verify]**
  whether an `ArrayOccluder3D` / `BoxOccluder3D` can be assigned at runtime without an editor bake
  step. A cave is close to the ideal case for occlusion culling, and it is the second-biggest
  performance lever after §5.
- **Decals.** Godot `Decal`s are clustered like lights; the practical visible budget is **[verify]**.
  But most of what wants a decal here should not be one: **anything that is a function of world
  position belongs in the shader, not in an instance.** The 0.12 m tide-mark crust (ART §3.5) is a
  `smoothstep` on world height around `water_mm`, costing zero instances. Reserve decals for things
  with no positional rule: a specific spill, a specific scorch.
- **GPU particles.** `GPUParticles3D` with an explicit `visibility_aabb` for the silt plume behind a
  moving agent (BLD-96, ART §2.6: local density to ~0.05, decaying over 10–20 s, 0.15 is
  self-blinding). Cosmetic only — the sim's silt is sim-side and the particles must not be what
  lidar hits (§2.2).
- **Volumetric fog** is what makes *"the beam is only visible when there is silt"* work. Froxel cost
  scales with view distance, and our view distance is 50 m, so this is cheap by accident. **[verify]**
  the cost at the resting scatter of 0.008–0.012.
- **Triplanar, no textures.** ART §3.2 forbids image textures and UV maps outright, and it is right
  that a generated cave cannot be unwrapped. But procedural voronoi at `fracture` 3–14, evaluated
  triplanar (three sample sets) in the fragment stage, is ALU-heavy. The likely fix is to **generate**
  a small 3D noise texture at load and sample it — which is not a bitmap *asset* and does not
  reintroduce an art pipeline, but it does contradict the letter of §3.2. Q5, and risk 4.

### 4.6 The per-match generation budget, in milliseconds

All **[estimate]**, with the arithmetic shown so a measurement can replace each line. Target from
BLD-148: *"Mesh build for a full-size generated cave completes under one second on the dev laptop."*

| step | work | estimate |
|---|---|---|
| `plan()` | ~44 chambers, ~70 passages, connectivity check, a whole-cave BFS for depth bands | **5–20 ms** |
| `rasterise()` | 96,000 cells, a few passes | **1–5 ms** |
| rock shell mesh, all 104 chunks | ~250k triangles total (below) | **100–300 ms** |
| scatter transforms | ~65,000 instances × 12 floats | **20–50 ms** |
| occluder boxes | per solid chunk region | **< 5 ms** |
| **total, cold** | | **130–380 ms** |

Triangle arithmetic, per chunk: 157 free cells average → floor + ceiling = 628 tris; walls at ~0.8
solid neighbours per free cell × ~7 vertical quads for a 4 m wall at 0.6 m subdivision ≈ 1,760 tris.
**≈ 2,400 tris/chunk, ≈ 250k tris for the whole cave, ≈ 5–15 MB of vertex data.**

Streaming budget: at 60 fps the frame is 16.6 ms, so **one chunk build per frame maximum**
(~1–3 ms), on a worker thread, with the `ArrayMesh` handed to the main thread for instancing.
**[verify]** Godot 4.7's rules for creating `Mesh` resources off the main thread.

---

## 5. The one lamp is a performance strategy

`ART-DIRECTION.md` §1: *"nine-tenths of every frame true black."* That is a look. It is also the
single largest performance lever available, and it is measured rather than assumed.

### 5.1 How much of the world need not exist

The numbers, all from ART §2.2 and §3.6, measured on the real Phase 1 grid:

- The lamp lights floor to ~6 m and walls to ~20 m. Wall at 25 m is black.
- Median sightline **3.6 m**; p90 **11.4 m**; 90.8% of directions under 12 m; longest anywhere
  **49.8 m**; largest chamber **14.4 m across** — *"about one lamp wide."*
- No landmark may be required to be visible across a chamber.

So the visible set from one lamp is bounded twice: by light (~20 m) and, much more tightly, by rock.

Arithmetic **[estimate]**: total free floor is 16,320 cells × 0.36 m² = **5,875 m²**. A 20 m disc is
1,257 m², i.e. **21%** of the cave — that is the light bound alone. Apply occlusion: a 20 m sight
down a 5-wide passage covers ~33 × 5 = 165 cells ≈ **1%** of free cells, plus whatever side branches
open. **Estimated visible set: 1–4% of the cave at any instant.**

**That is the argument that makes the designer's density affordable: the per-cell detail budget can
be 25–100× what a whole-cave budget would allow, for the same frame cost.** It is also the single
most important claim in this document and it is currently an estimate. It becomes a measurement the
day BLD-72 produces a cave: a BFS plus a visibility test over the plan, an afternoon.

### 5.2 How to exploit it

1. **Residency is keyed to the lamp, not the camera.** A 20 m radius touches at most 3 × 3 = **9
   chunks** of 104 — under 9% of the world resident in detail.
2. **Two tiers, and only the second streams.** Pre-build the **rock shell for the entire cave** in
   the background at match load: 250k triangles, 130–380 ms, once. Stream only **detail** (scatter,
   props, decals, particles) at 15 m. This costs one background job and buys immunity to §5.4(a).
3. **Nothing accumulates.** ART §9: *"No world accumulation. Lit ground goes black when the beam
   leaves."* No lightmaps, no baked GI, no per-chunk mutable state. Combined with §1.5's rule that
   the dresser is a pure function of `(plan_hash, chunk_id, kit_version)`, **eviction is free and
   re-entry is bit-identical.** This is the payoff for making the dresser deterministic even though
   it is allowed floats, and it is the reason streaming is safe here and is not safe in most games.
4. **Shadow cost is the light economy.** One shadow-casting `SpotLight3D` (the work lamp) plus a few
   non-shadow emissives is close to the cheapest possible 3D lighting setup, and it is exactly what
   ART §2.1 specifies. The art direction and the performance strategy are the same document.

### 5.3 What is genuinely cheap because of this

- **The map view is not rendered at all.** ART §3.6: *"the wide shot in Blindside is a schematic."*
  The schematic is drawn from the 12 kB plan — chambers, spines, shafts — not from geometry. **The
  plan is the map.** Cost ≈ 0, and it is another argument for the plan-as-seam design.
- **No LOD chain is needed** (§4.4), because nothing is ever 50 m away.
- **No streaming at all in the run phase**, because there is no truth geometry in the run phase
  (§0.3). Streaming is a replay/spectator problem only.

### 5.4 What breaks the trick

**(a) The spectator camera that can look anywhere.** A free camera can demand twenty chunks in a
frame; a camera that moves faster than the streamer is the cause of every hitch in every game that
has this problem. **Solved by 5.2(2): pre-build the whole shell.** Detail is then at most 9 chunks
behind the camera, ~10–30 ms worst case, one hitch, and pre-warm on drag removes it.

**But the camera breaks something the geometry budget cannot fix.** A free camera in an unlit chamber
sees *black*. ART §2.1's economy — four diegetic sources, world background strength **0** — and §9's
*"no ambient light, ever, in any costume"* mean the spectator view of a chamber with no agent in it
and no machinery in it is a black rectangle. ART §8.3 says the both-layers replay draws *"truth at
30–40% exposure"* — but **exposure is not a light source; you cannot expose black.** §8.3 presumes
truth is lit and §2 guarantees it is not.

**This is a genuine, unresolved conflict between two sections of the art direction, and it lands
squarely on the screen ROADMAP calls the most important in the game.** Recommended resolution
(Q4): the replay/spectator truth layer gets an explicitly **non-diegetic survey light** — a
shadowless fill, desaturated, marked as a diagram convention the way the belief layer is — and the
diegetic one-lamp economy governs *enter-agent-perception mode* (BLD-155) and every shot the game
presents as a photograph. That keeps ART's picture where it earns its keep, and makes the replay
legible. The alternative — a beautiful, faithful, unusable replay — should be rejected explicitly
rather than by drift.

**(b) The map view.** Not a problem: §5.3, it is drawn from the plan.

**(c) Several agents in different places at once.** P3-OQ §38 fixes the benchmark at **four agents,
one per team**. Worst case 4 × 9 = 36 chunks of detail resident, **35%** — survivable, and less in
practice because converging agents share chunks. If the design later puts two agents per team in the
cave, worst case is 72 of 104 and the trick collapses. Recommended rule (Q13): **the replay view
lights at most two agents at once**; the rest are shell-only silhouettes, which is also better
staging.

**(d) Replay scrubbing.** Two distinct problems.
   - *Camera teleport*: covered by the pre-built shell; ≤ 9 detail chunks to build.
   - *Truth geometry changes over time.* Collapses (BLD-94) mutate the cave. So a chunk cache keyed
     on `chunk_id` alone is wrong. **Rule: collapses are the only truth-geometry mutation; they are
     events in the ReplayFrame stream; the chunk cache key is `(chunk_id, collapse_epoch)` and the
     dresser takes the collapse list up to the scrub tick as an argument.** Rebuilding backwards is
     then exact and cheap, because collapses are few. If anything else ever mutates the cave — water
     level, silt as geometry, a deposit being worked out — it must join the same event list or
     scrubbing silently lies. Worth telling BLD-94 and BLD-146 now.

### 5.5 The surface is a different problem and a much easier one

Half the designer's ask is above ground, and it is not a procedural problem at all. The pit-head is
the **same place every match** (`DESIGN-PRINCIPLES.md` §3), so:

- It is authored once, not generated. No plan, no seam, no determinism constraint — nothing there
  is in `World`.
- The same tier-2 scatter machinery works, keyed to hand-painted surface classes instead of derived
  ones, so the density tooling is shared.
- It is the only place in the game with sky, with daylight, and with a player standing still — so it
  can carry far more detail per frame than the cave, and it is where §4's frame budget will actually
  be tested.
- It is also where ART §9's no-hand-modelled-asset rule breaks (§3.4, Q11).

**Recommendation: build the surface first when this work starts, not the cave.** It is the cheaper
half, it is where the "advanced robots must be plausible in the frame" requirement
(`DESIGN-PRINCIPLES.md` §4) is actually satisfied, and it needs none of §1's machinery.

---

## 6. What this costs and when it happens

Said plainly, as asked.

**The designer is asking a Phase 3 and Phase 5 question during Phase 2, and Phase 2's gate has not
been met.** `CLAUDE.md`: *"Do not start a phase whose predecessor's gate has not been met."* Phase 1's
gate playtest failed on comprehension (ART §11 quotes it), and the project's own recorded lesson is
that two days went into polishing a spectator video while the built teaching loop sat idle. The test
to apply to this work is that lesson's test: *does this make the player teach the agent sooner?* For
almost all of it, no.

**What can be answered now, for free:** this document. The seam (§1), the leak enumeration (§2), the
authoring surface (§3), the residency arithmetic (§5). None of it needs the sim, and §2.1 in
particular is worth having *before* BLD-162 is written, because it is a protocol requirement that is
a sentence now and a rewrite later.

**What genuinely needs the sim first — i.e. every number:**
- `cell_mm` is unanswered. ART's own guesses list: *"0.6 m per cell ... stated nowhere in the repo — I
  checked."* Every scale number in ART §3, §5 and §6 is downstream of it. Nothing can be modelled,
  scattered or sized until it is fixed. Q1.
- The cell model (BLD-71) and the generator (BLD-72) do not exist, and the plan in §1.2 is written
  against P3-OQ §38's *recommendation*, not a decision. If §38 comes back "CA with connectivity
  repair" rather than "chambers plus carved passages", **the plan has no chambers and no passages to
  record and the seam collapses to shipping the raster.** That is the single largest structural
  dependency in this document.
- The `FeatureKindId` list is permanent content ids (P3-OQ §1, §2). Guessing it now creates a retired
  ledger of guesses.
- Any dressing kit authored today is authored against Phase 1's hand-authored cave, which ART's own
  design-problem #3 proves is wrong on the deep-is-wet chain.

**What would be wasted work if done now, in order of waste:**
1. Any cave mesh, material or scatter work — it is graded against the wrong cave and the wrong scale.
2. Any Godot scene work beyond BLD-115's *"one GDScript call into Rust returns a value."*
3. A `FeatureKind` table, because its ids are permanent.
4. A dressing kit, because it has nothing to dress.
5. **Blender renders of any of it** — `DESIGN-PRINCIPLES.md` §5's first bullet: *"Blender renders are
   targets, not the pipeline. Nothing in it ships."*

**BLD-115, and the cost of pulling it forward.** BLD-115 (Godot + gdext bootstrap, 3 d) sits in Phase
4, is the only Phase 4 story with no sim dependency, and *"may be pulled into late Phase 3 solely with
the designer's explicit sign-off, recorded in BLD-114."* Pulling it into Phase 2 is a further step and
needs the same recorded sign-off. **It also is not three days: BLD-115 depends on BLD-37 (the
three-OS CI matrix), which is Phase 0 and is not built.** So the real price is Phase 0's CI matrix plus
three days plus the *"about 7 calendar days"* of toolchain latency BLD-115 already carries.
**Recommendation: do not pull it.** Q12.

### 6.1 Where this lands on the board, and what it reorders

| story | change |
|---|---|
| **BLD-71** (cell model, 3 d) | add `cell_mm` as an acceptance criterion; add the plan/raster split; add ART design-problem #3 (flooding rises with depth) and #4 (chamber ceilings) as plan post-conditions |
| **BLD-72** (generation, 4 d) | emits `CavePlan`; `rasterise` is a separate pure function; **the cave hash golden is over the plan, not the raster** |
| **BLD-73** (deposits) | `DepositSite` shape and `region` come from the plan; unchanged otherwise |
| **BLD-76** (truth export, 2 d) | **scope grows.** Add a per-match header (`seed`, `biome`, `content_hash`, `CavePlan`, `kit_version`) beside the per-tick frames — and, larger, record that **the generator function itself is part of the sanctioned-truth surface** (§2.1). BLD-76 currently guards values, not the ability to recompute them |
| **BLD-79** (acoustics) | may take its passage-axis skeleton from `Passage.spine` for free (P3-OQ §39 fallback) |
| **BLD-94** (collapse) | collapses become the only truth-geometry mutation and must appear in the frame stream as events (§5.4d) |
| **BLD-29** (feature-unification guard) | extend from *features* to *crates*: the live host must have no dependency path to `blindside-gen` |
| **BLD-145** (ReplayFrame on the client) | its one-line GDScript grep becomes tool 3 in §2.3 |
| **BLD-148** (cave truth layer, 6 d) | mesh from the shared rasteriser; 32×32 chunks; shell/detail split; the per-seed cache rule in §2.4; the 1 s bar is reachable by the §4.6 estimate |
| **BLD-162** (transport, 2 d) | **new requirement: the live client never receives the match seed** (§2.1) |
| new, Phase 3 | `FeatureKind` content table + placement constraints — **~2 d [estimate]**, next to BLD-71/73 |
| new, Phase 5 | dressing kit resource format + scatter — **~3 d [estimate]** |
| new, Phase 4/5 | `tools/invariant-gd` — **~2 d [estimate]**, beside BLD-145 |

**Estimated added cost: Phase 3 +3–5 d, Phase 5 +8–12 d [estimate].** Nothing is removed. No phase
order changes. Nothing starts now.

### 6.2 The P3-OQ decisions this work is blocked on

Answer these and the plan can be written; leave them and it cannot.

**§38** (400×240, chambers joined by carved passages) — structural, see above.
**§25** (four width classes, chassis enter/turn class) — `Passage.width_class` is exactly this.
**§33** (`BlockId`, discoveries placed by depth) — `DiscoverySite`.
**§40** (content is TOML with `Fx` as strings) — tier 1's format.
**§41** (`blindside-content` constrained, loader separate) — decides who may read the placement rules.
**§34** (RNG purpose space) — the dresser borrows the construction; the purpose space needs `gen` and
`dress` arms reserved now, because it is packed to a `u32` and permanent.
**§1, §2** (id numbering, retire by date) — `FeatureKindId` and `BiomeId` join the ledger.
**§3** (content hash covers the season-enabled set) — and, from §3.1 above, **the dressing kit must
stay out of it**.
**§18** (record-assigned ids) — plan indices are not runtime ids.
**§19** (20 Hz, no seconds) — `dwell`, decay and cycle numbers in the kit are seconds and must be
converted at load, like all content.

---

## 7. Risks and kill criteria

| # | risk | what would tell us early | kill criterion |
|---|---|---|---|
| **1** | **The seed is the cave** (§2.1). Pure generation plus a shared seed hands a modified client the full map before commit. | During BLD-162, write down exactly what the live client needs the seed for. | If the answer is not "nothing", generation moves server-side and the cave reaches the client only as belief-shaped fragments — a large Phase 6 change. If it is "nothing", the risk closes for one protocol sentence. |
| **2** | **Density the sim cannot see** (§2.2). Props are neither solid nor sensible, so more detail makes the drawn world and the simulated world diverge, and the replay shows agents walking through timber. | Dress one Phase-1-sized cave and count dressed instances intersecting cells the sim calls FREE. | If the count is high enough to read as a lie, either dressing gets a collision budget or props move into the plan — which multiplies the plan's size and makes them sim state. Measure before the kit is authored, not after. |
| **3** | **The one-lamp economy and the spectator camera are incompatible** (§5.4a). | ART §11's own kill test, run with the camera *detached* from the agent: sixty seconds of free-flying a lamp-lit cave, h264-encoded, shown to someone who has not seen the game. | If a viewer cannot say where they are in five seconds, the truth layer needs a non-diegetic light and ART §2.1/§9 need an amendment. Cheap, and it can run in Blender before Godot exists. |
| **4** | **Procedural materials are ALU-expensive** (§4.5). Voronoi + triplanar + zero textures at 1080p on a laptop. | Measure shader cost in the running Godot proof on a single dressed chunk. | > 4 ms/frame at 1080p → bake noise to a generated 3D texture and amend ART §3.2 (Q5). |
| **5** | **No runtime mesh LOD in Godot** (§4.4). If the 250k-triangle shell plus everything else misses frame rate, there is no automatic fallback. | Draw the pre-built shell alone, nothing else, in the Godot proof. | Shell-only > 3 ms → write a coarse second rasterisation (a 2× cell decimation), which is a day, or drop the pre-built shell and accept §5.4(a)'s hitching. |
| **6** | **The §5.1 residency estimate is wrong.** 1–4% is arithmetic, not a measurement. | A BFS + visibility pass over the first real generated cave (BLD-72). An afternoon. | If it is 15%+, the detail budget per cell drops by 5× and ART's *"way more detail"* becomes a per-frame fight rather than a free win. |
| **7** | **Fatigue** — ART §11's *"single riskiest assumption"*, unchanged by anything here. More detail may help or hurt and nobody knows. | ART §11's kill test, unmodified. | Out of scope for this document; named so it is not lost. |

---

## 8. Questions for the designer

Each is yes/no with a recommended default. Answering nothing leaves the defaults, and the defaults
are the recommendations.

**Answered so far.** 15 (yes, 2026-09-08). The other fourteen stand at their recommended defaults
until the designer says otherwise; 4 and 9 are the two that amend documents rather than settle
housekeeping, and should be answered deliberately rather than by default.

1. **`cell_mm = 600`** — 0.6 m per cell, recorded in `CavePlan` and in ARCHITECTURE, so every scale
   number in ART stops being downstream of a guess. **Recommend: yes.** (ART's #2 blocker.)
2. **The dressed cave is a replay and spectator asset only; the player never sees dressed truth
   during a match.** **Recommend: yes** — this is what ART §8.3 and BLD-144 already say, but it has
   never been stated as a decision, and everything in §1.5 and §5 depends on it.
3. **Dressing must be reproducible, not bit-identical**, under §1.5's binding rules. **Recommend: yes.**
4. **The replay/spectator truth layer gets a non-diegetic survey light**; the diegetic one-lamp
   economy governs enter-agent-perception mode and any shot presented as a photograph. This amends
   ART §2.1 and §9. **Recommend: yes.** (§5.4a — the sharpest conflict found.)
5. **Generated noise textures are allowed** even though bitmap art assets are not. Amends the letter
   of ART §3.2. **Recommend: yes.**
6. **Kit-of-parts props are parametric recipes, not modelled meshes**, and that satisfies ART §9's
   "no hand-modelled asset". **Recommend: yes.**
7. **Props never affect the sim** — not cover, not obstruction, not landmark, not hazard. Anything
   that must matter is promoted into the plan and the cell grid. **Recommend: yes, with an empty
   promotion list for Phase 5.**
8. **Feature placement is a constraint struct in TOML, not an expression language.** **Recommend: yes.**
9. **The live client never receives the match seed**, recorded now as a BLD-162 requirement.
   **Recommend: yes.** (§2.1 — the largest new leak.)
10. **Benchmark seeds are never used in live matches.** **Recommend: yes.**
11. **ART §9's "no hand-modelled asset" is scoped to the cave**, so the pit-head can be built.
    **Recommend: yes.** (§3.4, §5.5.)
12. **Do not pull BLD-115 forward.** **Recommend: yes, do not pull** — and note it is not 3 days,
    because BLD-37 is not built. (§6.)
13. **The replay view lights at most two agents at once**; others are shell-only. **Recommend: yes.**
14. **Detail budget ends at 15 m; nothing is required to be legible past 50 m.** **Recommend: yes**
    (this is ART §3.6 restated as a client setting).
15. **When this work starts, the surface is built before the cave.** **Recommend: yes.** (§5.5.)
    **ANSWERED YES, 2026-09-08, by the designer.** The pit-head is built first. It is where the
    players' technology lives, so it is the frame that has to make advanced machines plausible
    (`DESIGN-PRINCIPLES.md` §4), it is lit by daylight so the one-lamp conflict in §5.4a does not
    block it, and question 11 scopes ART §9 to the cave so it is not forbidden ground.

---

## Things this document guessed

Beyond every line marked **[estimate]** or **[verify]** above:

- **~44 chambers and ~70 passages** for a 400×240 cave, scaled from Phase 1's eleven on 200×120.
  Nothing measured this; the generator does not exist.
- **32 × 32 cells as the chunk size.** Chosen so a 20 m lamp radius touches 9 chunks. The Godot
  proofs should confirm it against draw-call and build-time cost.
- **~4 scatter instances per free cell** as the density that produces "way more detail". A number
  with no source, used only to make §4.3's arithmetic concrete.
- **0.8 solid neighbours per free cell** and a **4 m wall height**, used for the triangle count.
- **The `Feature` field set**, especially `facing` at a 5.625° quantum and `variant` as a `u8`.
- **The tag list** in §3.2 (`wall_adjacent`, `on_spine`, …). It covers the placements ART names; it
  has not been checked against anything else.
- **That `blindside-gen` can be linked by the replay host at all** without dragging `blindside-sim`
  in with it. The crate graph does not exist yet, so this is an assumption about a graph nobody has
  drawn.
