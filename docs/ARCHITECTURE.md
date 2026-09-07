# Architecture

Applies from Phase 3 onward. Phases 1 and 2 are throwaway Python and ignore all of this.

---

## Crate layout

```
blindside-sim         deterministic core. no I/O, no time, no float, no rand
blindside-vm          bytecode interpreter, instruction budget
blindside-behavior    node graph, compiler -> bytecode, graph diff
blindside-induct      demonstration traces -> behavior trees
blindside-gen         cave and world generation
blindside-content     data-driven definitions: sensors, modules, chassis, ancients
blindside-net         server, lobby, match orchestration
blindside-harness     headless runner, canary, batch eval, replay tooling
blindside-client      Godot GDExtension bindings
```

`blindside-sim` depends only on `blindside-vm` and `blindside-content`. That constraint
is load-bearing — it keeps determinism auditable by reading one dependency tree.

---

## The boundary that matters most

```rust
// blindside-sim/src/world.rs — ground truth. pub(crate) ONLY.
pub(crate) struct World {
    tick: Tick,
    cave: Cave,
    agents: SlotMap<AgentId, AgentTruth>,
    beacons: SlotMap<BeaconId, Beacon>,
    wrecks: Vec<Wreck>,
    deposits: SlotMap<DepositId, Deposit>,
    ancients: SlotMap<AncientId, AncientInstance>,
    acoustics: AcousticField,
}

// blindside-sim/src/belief.rs — what an agent thinks. PUBLIC.
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

`World` is never passed downstream of the sensor layer. Not to predicates, not to the VM,
not to the client, not to the renderer.

**Write a compile-time test asserting `Policy::evaluate` cannot reach `World`.** It exists
to catch the "just for debugging" accessor someone adds in year two.

---

## Core types

```rust
// ---- identity: stable, explicit, never derived from registration order ----
pub struct SensorId(pub u16);
pub struct PredicateId(pub u16);
pub struct ActionId(pub u16);
pub struct ModuleId(pub u16);
pub struct AncientKindId(pub u16);
// Assigned in content data files. NEVER reused after retirement.
// Deriving these from a name hash or Vec index will desync across versions.

// ---- sensors ----
pub trait Sensor {
    fn id(&self) -> SensorId;
    fn cost(&self) -> SlotCost;
    fn emits(&self) -> Option<AcousticSignature>;   // Some => you are audible
    fn sample(&self, w: &World, a: &AgentTruth, rng: &DeterministicRng)
        -> SmallVec<[Return; 8]>;
}

pub enum Return {
    Bearing      { angle: Fx, quality: Fx },
    RangeBearing { range: Fx, angle: Fx, quality: Fx },
    Anomaly      { rough_direction: Fx, strength: Fx },
    Optical      { patch: OccupancyPatch },
    Structural   { time_to_failure: Option<Fx> },
    Fix          { position: Vec2Fx, source: FixSource },
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
    Guard   { pred: PredicateId, params: SmallVec<[Fx; 4]>, child: NodeId },
    Act     { action: ActionId, params: SmallVec<[Fx; 4]> },
    Subtree { source: PolicyRef },     // the unit of sale
}

pub struct VmBudget { pub ops_per_tick: u32 }   // also a balance lever

// ---- ancient systems ----
pub trait AncientSystem {
    fn kind(&self) -> AncientKindId;
    fn signature(&self, s: &AncientState) -> Option<AcousticSignature>; // legible BEFORE lethal
    fn step(&self, s: &mut AncientState, w: &WorldView, rng: &DeterministicRng);
    fn hazard(&self, s: &AncientState) -> Option<HazardVolume>;
    fn provocable_by(&self) -> &[ProvocationKind];  // deliberate triggering by players
}

// ---- determinism ----
pub struct DeterministicRng { seed: u64 }
impl DeterministicRng {
    // Counter-based and stateless. Call order cannot affect results.
    pub fn draw(&self, tick: Tick, entity: u32, purpose: u16) -> Fx { /* hash */ }
}

pub type Fx = fixed::types::I32F32;   // no f32/f64 anywhere in blindside-sim

// ---- recording ----
pub struct MatchRecord {
    pub seed: u64,
    pub schema: u16,
    pub content_hash: [u8; 32],       // replays break silently without this
    pub loadouts: Vec<Loadout>,
    pub policies: Vec<PolicyRef>,
    pub commands: Vec<(Tick, TeamId, Command)>,   // the only live input
    pub ticks: u64,                   // length: "run to completion" needs one
    pub final_hash: [u8; 32],         // what `verify` compares against
}
```

**DEFAULT (awaiting designer): `ticks` and `final_hash` were added to `MatchRecord` --
the acceptance criteria cannot be expressed without them.** The last two fields were not
in this struct originally. Phase 0 added them because running a replay "to completion"
needs a length, and verifying that "the final state hash matches the recorded one" needs a
recorded hash; putting both in the record keeps a replay one self-describing file. The
designer has not confirmed this. It is question 6 of `HARNESS.md` §1, which is written as
a yes/no so it can be answered in one pass, and the marker in
`crates/blindside-sim/src/record.rs` comes out when it is.

Commands are stored sorted by `(tick, team, sequence)`; a record in any other order is a
typed error, not a silent re-sort.

`blindside_sim::diagnostics` is the one sanctioned exception to "make it awkward to pass
ground truth": a `String`-only window onto `World` for the desync canary and bisect,
compiled only under a cargo feature that no client, policy, VM or renderer crate may
enable. `HARNESS.md` §7 covers why the feature alone is not a boundary and what enforces
it.

---

## Extension points

Each is a registry keyed by stable ID, defined in data, validated at build time.

| Extends | How | Expected growth |
|---|---|---|
| Sensors | `impl Sensor` + content entry | 6 → 20+ |
| Predicates | `impl Predicate` + vocabulary entry | 3 → 20 → 40 |
| Actions | `impl Action` + entry | 2 → 15 |
| Ancient systems | `impl AncientSystem` + entry | 2 → many |
| Chassis / modules | pure data | 1 → 4 classes |
| Cave biomes | generator params | 1 → per-season |
| Match modes | `impl MatchMode` | 1 → 4 |

**Rules that keep this from rotting:**

1. Never reuse a retired ID. Retired predicates become `Deprecated`, evaluate to a fixed
   value, and are flagged in the editor. A policy authored in season 1 must parse in
   season 6.
2. Content pack hash goes in every replay.
3. Schema-version every serialized policy, with a migration path.
4. Predicates read `&Belief` only — enforced by module privacy, not discipline.
5. New content ships behind a season flag so it does not invalidate the live season.

---

## Hardware-readiness

The behavior layer is intended to eventually run on physical hardware. `Sensor` and the
actuator interface should be designed so a hardware backend is a second implementation of
the same traits, not a rewrite. Do not build it. Do not foreclose it.

Concretely: no sensor implementation should assume it can query arbitrary world state; it
should express what it needs as a request the sim happens to answer from `World` and
hardware would answer from a driver.

---

## Client

Godot 4 via GDExtension with Rust bindings for the sim. GDScript for UI and glue — do not
write the whole client in Rust, it costs the iteration speed that is the reason to use
Godot.

The FFI boundary is a feature: it enforces that the client can only see what is
deliberately handed across. Make it awkward to pass ground truth.

Primary run-phase view is a sparse 3D point cloud of accumulated returns in the agent's
estimated frame, so drift renders as visible smearing and a fix snaps it into alignment.
See `PHASE-1-SPECTATOR-TEST.md` for the display spec being validated.
