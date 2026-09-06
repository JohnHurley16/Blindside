# Deadwater — development roadmap and architecture

Ordering principle: **build in order of how much damage a wrong answer does, weighted by how uncertain the answer is.** Every phase has a gate with a stated kill criterion. If a gate fails, the phase after it does not start.

Two phases are deliberately throwaway Python. Do not try to make them permanent — their only job is to answer a question before you commit a year of engineering to it.

---

## Part 1 — Risk register

| # | Risk | If wrong | Confidence now | Tested in |
|---|------|----------|----------------|-----------|
| R1 | The run phase is boring | Whole design collapses; unfixable later | Low | Phase 1 |
| R2 | Demonstration can't produce legible policies | Ladder breaks; game becomes an IDE | Low | Phase 2 |
| R3 | Players can't diagnose their own failures | Forensics layer dead; no learning loop | Low | Phase 2 |
| R4 | Cross-platform determinism unachievable | No replays, no market verification, no server authority | Medium | Phase 3 |
| R5 | Predicate vocabulary wrong size | Policies unexpressive or overfit | Low | Phase 2 |
| R6 | Onboarding the belief/truth concept | High bounce; niche within a niche | Low | Phase 7 |
| R7 | Not enough authors to sustain a market | Ghost-town store, looks dead | Low | Phase 9 |
| R8 | Server cost per match exceeds unit economics | Business model broken | Medium | Phase 6 |

R1 through R3 are cheap to test and catastrophic if wrong. They come first, before any real engineering.

---

## Part 2 — Phases

### Phase 0 — Harness (before any game code)
**~1 weekend. Rust.**

Not a game. The tooling that makes everything after it survivable.

- `deadwater-harness`: headless runner, batch executor, state hash per tick
- Desync canary: two sim instances, identical inputs, hash comparison, panic on divergence
- Replay format: seed + input log, load and re-run
- Determinism lint: CI rejects `std::time`, `rand`, `HashMap` iteration, `f32`/`f64` in the sim crate

**Gate:** an empty sim runs 10,000 ticks on two instances with identical hashes. Trivial now, impossible to retrofit later.

---

### Phase 1 — The Spectator Test
**~2–3 weekends. Python, throwaway.**

Answers R1, the biggest risk in the project. No demonstration, no authoring, no art.

- 2D top-down cave, hardcoded
- Two agents running hand-written scripted policies
- Passive acoustic contacts with bearing only, plus active ping
- Belief-space display only: what your agent thinks the map is, uncertainty ellipse, contact bearings
- Player has exactly one input: `Recall`

Put someone in front of it for eight minutes with no controls but Recall.

**Gate — kill criterion:**
- The player talks to the screen, guesses at contacts, leans in
- They can articulate a wrong theory about what a contact was, then correct it
- They report tension at the moment they decide whether to recall

If they're bored, **stop and redesign the run phase.** Do not proceed to Phase 2. This is the one failure that no later work repairs.

---

### Phase 2 — The Junction Test
**~4–6 weekends. Python, throwaway.**

Answers R2, R3, R5.

- Branching corridor, 8 junctions, one deposit at a random leaf
- 3 predicates: `unexplored_branch_exists`, `uncertainty > θ`, `carrying_cargo`
- 2 actions: `take_branch`, `return_to_beacon`
- Record belief + input traces during player-driven demonstration
- Changepoint segmentation, minimal-separator predicate induction, threshold fitting
- Render the inferred policy as a behavior tree and as one plain sentence
- Ghost replay: inferred policy runs alongside the demonstration
- Correction loop: scrub, enter body, drive correction, promote
- Active-learning query when no consistent separator is found

**Gate — kill criterion:**
- 3 demonstrations → ≥70% success on unseen seeds
- Player reads the inferred rule and correctly predicts the next junction choice
- On failure, player names the wrong rule **unprompted** from the replay
- A correction takes under 60 seconds end to end

Criterion 3 is the real one. If players can't self-diagnose, the forensics layer — the emotional core of the game — does not work.

---

### Phase 3 — Sim core, for real
**~3–5 months. Rust.**

Now you build the thing. Everything in Part 3 below lands here.

- `deadwater-sim` with the truth/belief boundary enforced at the crate level
- Fixed-point math throughout, deterministic locomotion over a heightfield
- Sensor trait + the six sensors, all returning `Return` values, never truth
- `BeliefUpdater` fusion stack: dead reckoning, terrain-relative fixes, beacon fixes, contact tracking
- Seeded noise per `(tick, entity_id, sensor_id, purpose)`
- `deadwater-gen`: cellular automata caves, connectivity guarantees, value parity, the 8 world axes
- Acoustic field: propagation, absorption by rock type, thermal shadow zones

**Gate:** 1,000 matches run headless in under 10 minutes, bit-identical across Linux/macOS/Windows. R4 answered here — if it fails, you find out before the client exists.

---

### Phase 4 — VM and node editor
**~3–4 months.**

- `deadwater-vm`: ~30 opcodes, fixed register file, hard instruction budget per tick
- `deadwater-behavior`: behavior tree representation, direct compilation to bytecode (no text intermediate)
- Node editor in Godot: build, collapse, expand, subtree extraction
- Execution trace capture — which nodes fired, in what order, on what predicate values
- Port Phase 2's induction to produce these trees

**Gate:** a policy authored entirely in nodes beats a hand-written one on the benchmark set. Graph diff works on two versions of the same tree.

---

### Phase 5 — Client and replay
**~3–4 months. Godot + GDExtension.**

- 3D renderer, one cave biome, Surveyor chassis only
- Operator view: belief-space telemetry, map as the agent built it, contact list
- **Replay with both layers drawn together** — this is the most important screen in the game and should get the most polish
- Enter-agent-perception mode
- Failure attribution heuristics: identify and present the causal chain

**Gate:** Phase 1's spectator test, re-run in the real client, scores better than the Python version did.

---

### Phase 6 — Networked match
**~3–4 months.**

- Server-authoritative sim, clients receive belief-space state only
- 4 teams, extraction mode, wrecks and salvage, behavior recovery from wrecks
- Command channel: latency by depth, blocked in acoustic shadow
- Lobby, seeds, published post-match

**Gate:** answers R8 — measured server cost per match against a plausible price point.

---

### Phase 7 — Onboarding and fiction
**~2–3 months.**

- Two ancient systems only, with signature/behavior/exploit/counter each
- Teach belief-versus-truth without a lecture: the first failure should be a beacon lie the player watches happen
- Named persistent fleet, service history, wall of the lost
- Endurance mode

**Gate:** answers R6. New players, no explanation, watched to see whether the concept lands in ten minutes.

---

### Phase 8 — Ship something
**~2 months.**

Early access, or the standalone forensic game carved out of Phases 2 and 5. Either way: a thing people can buy, an audience, and feedback that isn't from friends.

---

### Phase 9 — Market and seasons
**Post-launch.**

- In-game currency only — no real payouts until there is a company
- Benchmark auto-evaluation of listings, replays attached
- Seed with your own behaviors, labelled honestly as first-party
- Season one: shift generation weights, change an ancient system's state, publish the transition as an event

**Gate:** answers R7. If ≥1% of active players publish a behavior anyone adopts, the economy works.

---

**Total to Phase 8: roughly 18–24 months of nights and weekends.** Treat that as a floor. The estimate is honest about the work and dishonest about life.

---

## Part 3 — Architecture

### Crate layout

```
deadwater-sim        deterministic core. no I/O, no time, no float, no std::rand
deadwater-vm         bytecode interpreter, instruction budget
deadwater-behavior   node graph, compiler → bytecode, graph diff
deadwater-induct     demonstration traces → behavior trees
deadwater-gen        cave and world generation
deadwater-content    data-driven definitions: sensors, modules, chassis, ancients
deadwater-net        server, lobby, match orchestration
deadwater-harness    headless runner, canary, batch eval, replay tooling
deadwater-client     Godot GDExtension bindings
```

`deadwater-sim` depends on nothing but `deadwater-vm` and `deadwater-content`. That constraint is load-bearing — it's what keeps determinism auditable.

---

### The boundary that matters most

```rust
// deadwater-sim/src/world.rs — ground truth. pub(crate) ONLY.
pub(crate) struct World {
    tick: Tick,
    cave: Cave,
    agents: SlotMap<AgentId, AgentTruth>,
    beacons: SlotMap<BeaconId, Beacon>,
    wrecks: Vec<Wreck>,
    deposits: SlotMap<DepositId, Deposit>,
    ancients: SlotMap<AncientId, AncientInstance>,
    acoustics: AcousticField,
    rng: DeterministicRng,
}

// deadwater-sim/src/belief.rs — what an agent thinks. PUBLIC.
pub struct Belief {
    pub pose: PoseEstimate,          // mean + covariance, drifts
    pub map: OccupancyMap,           // only what it has sensed
    pub contacts: Vec<ContactTrack>, // bearings over time, unresolved
    pub beacons: Vec<KnownBeacon>,   // including ones that lie
    pub inventory: Inventory,
    pub ticks_since_fix: u32,
    pub self_report: SelfReport,     // power, damage, module health
}
```

**`World` is never passed to anything downstream of the sensor layer.** Not to predicates, not to the VM, not to the client, not to the renderer. The sensor layer is the only code in the project that touches both, and it lives in one file so it can be audited by reading it.

Write a compile-time test that asserts `Policy::evaluate` cannot reach `World`. When someone eventually adds a "just for debugging" accessor, that test is what catches it.

---

### Core types

```rust
// ---- identity: stable, explicit, never derived from registration order ----
pub struct SensorId(pub u16);
pub struct PredicateId(pub u16);
pub struct ActionId(pub u16);
pub struct ModuleId(pub u16);
pub struct AncientKindId(pub u16);
// IDs are assigned in content data files and NEVER reused after retirement.
// Deriving these from a name hash or a Vec index will desync you across versions.

// ---- sensors ----
pub trait Sensor {
    fn id(&self) -> SensorId;
    fn cost(&self) -> SlotCost;
    fn emits(&self) -> Option<AcousticSignature>;   // Some => you are audible
    fn sample(&self, w: &World, a: &AgentTruth, rng: &mut DeterministicRng)
        -> SmallVec<[Return; 8]>;
}

pub enum Return {
    Bearing   { angle: Fx, quality: Fx },                 // passive acoustic
    RangeBearing { range: Fx, angle: Fx, quality: Fx },   // active sonar
    Anomaly   { rough_direction: Fx, strength: Fx },      // magnetometer
    Optical   { patch: OccupancyPatch },
    Structural{ time_to_failure: Option<Fx> },
    Fix       { position: Vec2Fx, source: FixSource },    // beacon or terrain match
}
// FixSource::Beacon(BeaconId) — a spoofed beacon returns a Fix that is simply wrong.
// Nothing in the type system distinguishes a lie. That is the point.

// ---- belief update ----
pub trait BeliefUpdater {
    fn integrate_motion(&mut self, b: &mut Belief, cmd: &MotorCmd, dt: Fx);
    fn fuse(&mut self, b: &mut Belief, returns: &[Return], tick: Tick);
}

// ---- policy ----
pub trait Predicate {
    fn id(&self) -> PredicateId;
    fn eval(&self, b: &Belief, params: &[Fx]) -> bool;   // &Belief. never &World.
}

pub struct Policy {
    pub schema: u16,
    pub root: NodeId,
    pub nodes: Vec<BtNode>,
    pub bytecode: Vec<Op>,
    pub author: AuthorRef,
    pub provenance: Vec<AuthorRef>,   // attribution chain for salvaged behaviors
}

pub enum BtNode {
    Sequence(Vec<NodeId>),
    Selector(Vec<NodeId>),
    Guard { pred: PredicateId, params: SmallVec<[Fx; 4]>, child: NodeId },
    Act   { action: ActionId, params: SmallVec<[Fx; 4]> },
    Subtree { source: PolicyRef },     // the unit of sale
}

pub struct VmBudget { pub ops_per_tick: u32 }   // also a balance lever

// ---- ancient systems ----
pub trait AncientSystem {
    fn kind(&self) -> AncientKindId;
    fn signature(&self, s: &AncientState) -> Option<AcousticSignature>;  // legible BEFORE lethal
    fn step(&self, s: &mut AncientState, w: &WorldView, rng: &mut DeterministicRng);
    fn hazard(&self, s: &AncientState) -> Option<HazardVolume>;
    fn provocable_by(&self) -> &[ProvocationKind];  // how a player can trigger it deliberately
}

// ---- determinism ----
pub struct DeterministicRng { /* counter-based: hash(seed, tick, entity, purpose) */ }
impl DeterministicRng {
    pub fn draw(&self, tick: Tick, entity: u32, purpose: u16) -> Fx { /* stateless */ }
}
// Counter-based, not stateful. Order of calls cannot affect results, which removes
// the single most common source of desync in a simulation with many actors.

pub type Fx = fixed::types::I32F32;   // no f32/f64 anywhere in deadwater-sim

// ---- recording ----
pub struct MatchRecord {
    pub seed: u64,
    pub schema: u16,
    pub content_hash: [u8; 32],       // which content pack — replays break silently without this
    pub loadouts: Vec<Loadout>,
    pub policies: Vec<PolicyRef>,
    pub commands: Vec<(Tick, TeamId, Command)>,   // the only live input
}
// Kilobytes. Re-runs the whole match. Makes the market verifiable and clips shareable.
```

---

## Part 4 — Extension points

These are the things that will grow. Each is a registry keyed by stable ID, defined in data, validated at build time.

| Extends | How | Growth |
|---|---|---|
| Sensors | `impl Sensor` + content entry | 6 → 20+ |
| Predicates | `impl Predicate` + vocabulary entry | 3 → 20 → 40 |
| Actions | `impl Action` + entry | 2 → 15 |
| Ancient systems | `impl AncientSystem` + entry | 2 → many |
| Chassis / modules | pure data | 1 → 4 classes |
| Cave biomes | generator params | 1 → per-season |
| Modes | `impl MatchMode` | 1 → 4 |

**Rules that keep this from rotting:**

1. **Never reuse a retired ID.** A policy authored in season 1 must still parse in season 6. Retired predicates become `Deprecated`, evaluate to a fixed value, and are flagged in the editor.
2. **Content pack hash goes in every replay.** Otherwise replays silently produce different results after a balance change and you will not notice for months.
3. **Schema-version every serialized policy** with a migration path. You will change the node format.
4. **Predicates read `&Belief` only** — enforced by module privacy, not by discipline.
5. **New content ships behind a season flag**, so adding it doesn't invalidate the current competitive season.

---

## Part 5 — Determinism rules

Print these and put them above the desk.

- No `f32`/`f64` in `deadwater-sim`. Fixed-point only.
- No `HashMap`/`HashSet` iteration in sim logic. `BTreeMap` or `SlotMap` with explicit ordering.
- No `SystemTime`, `Instant`, thread IDs, or address-derived values.
- No `rayon` or thread pools inside a tick unless the reduction is order-independent and proven.
- RNG is counter-based and stateless: `hash(seed, tick, entity, purpose)`.
- Entity iteration order is by stable ID, always.
- The canary runs in CI on every commit, across all three platforms.
- Any `unsafe` in the sim crate requires a written justification in the PR.

**The failure mode to fear:** a desync introduced in month 4, discovered in month 14, in a networked match you cannot reproduce. The canary is not optional tooling — it's the reason the project survives.

---

## Part 6 — Deliberately deferred

Not forgotten. Deferred, with the reason.

| Deferred | Until | Why |
|---|---|---|
| Real-money payouts | There is a company | Regulatory and moderation load will consume a solo dev |
| Multiple agents per player | Post Phase 6 | Inter-agent comms is a large design surface; needs a stable base |
| Multi-human teams | Post Phase 6 | Changes the run phase fundamentally; test the solo version first |
| Matchmaking / ranked | Post Phase 8 | Meaningless without a playerbase |
| Skins and cosmetics | Post Phase 8 | Requires a locked chassis silhouette, which requires final art |
| Anti-griefing systems | Phase 6 playtests | Design the response to observed griefing, not imagined griefing |
| More than 2 ancient systems | Phase 7 feedback | Let the good ones tell you what the others should be |
| Moderation tooling | Phase 9 | Scales with the market, which doesn't exist yet |

---

## The single most important thing on this page

**Phase 1 comes before everything.** It is three weekends of throwaway Python, it costs nothing, and it answers the one question that no amount of later engineering can fix. If watching a blind machine work is not tense, the entire design is wrong and you want to know that now — not after eighteen months of Rust.
