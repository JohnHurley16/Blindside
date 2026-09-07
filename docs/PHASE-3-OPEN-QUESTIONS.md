# Phase 3 — open questions before code

## Read this first

Three decisions carry the rest; the other 49 sections can wait until Phase 3 code starts.

- **[§3](#3-the-content-hash-covers-the-season-enabled-set-not-file-bytes)** — the content hash covers the season-enabled set, not file bytes: the only wrong
  answer here that fails silently, months later, as a replay that no longer reproduces.
- **[§11](#11-return-odometry-in-fix-out-transponder-returns-are-relative-sources-are-ids-no-truth-tags) + [§13](#13-terrain-relative-navigation-is-a-beliefupdater-stage-a-beacon-fix-changes-heading-by-exactly-zero) + [§14](#14-beliefmap-is-a-timestamped-point-set-with-derived-occupancy-bins)** — a relative `Transponder` return and no `Fix`, terrain
  matching in the belief updater, a timestamped point-set map: the spoof and the snap are the
  game's two core mechanisms and neither is expressible under ARCHITECTURE's types.
- **[§20](#20-the-policy-driver-a-memoryless-tree-interpreter-in-blindside-vm-behind-vmhost) + [§8](#8-phase-3s-predicate-and-action-ids-include-the-reference-policy-blocks)** — Phase 3 agents run tree data in `blindside-vm` behind `VmHost` with
  the reference-policy blocks registered: the only driver under which the 1,000-match gate
  proves determinism of the artifact Phase 4 will run.

Five spikes ran on 2026-09-06: BLD-61 (`spikes/ARCHITECTURE-RECONCILIATION.md`),
BLD-62 (`spikes/AGENT-DRIVER.md`), BLD-63 (`spikes/SENSORS-AND-IDS.md`), BLD-64
(`spikes/ACOUSTIC-BUDGET.md`) and BLD-65 (`spikes/CHASSIS-TIMING.md`). They read Phase 1 at
different commits as they ran — `66ebb20`, `7fcbe87` and `d19579b`, none of which changes a
sim number, since `7fcbe87` fixed a crash in the decision report and `d19579b` added a doc —
and each spike cites the one it read. Between them they put 77 yes/no lines to the designer,
and in nine places they answer the same question two ways.
This file is the one list: every decision Phase 3 code waits on, once, ordered by how much a
wrong answer costs, with the recommendation, the reason, the evidence and a line to answer on.
Where two spikes disagreed, the section says which one changes and how. Those sixteen edits
were applied to the spike files on 2026-09-06 and a further fourteen on 2026-09-07, each
carrying a `Reconciled <date>:` line that names the section here. After the second pass a
check found no remaining disagreement between the six files except the three decisions in
§50–§52, which no edit can settle.

**How to answer.** Tick yes or no in place. A no means say what instead, or "ask again with
options". A section with two lines has two independent answers. Anything marked **[guess]**
was chosen by a spike author without a measurement and is listed again at the end.

**Ordering.** Part A cannot be undone once a replay or a saved policy carries the number.
Part B is a hashed or serialised schema, or the invariant itself: wrong means a migration
under a live season or a rewrite. Part C is a refactor. Part D is data: wrong changes the
content hash and nothing else. Board stories are cited by key; `DEV-PLAN.md` is the board.

**Evidence.** Numbers below are the spikes' measurements (Phase 1 headless, 8 seeds unless
stated; scratch Rust for the acoustic and content-format work) plus one measurement made for
this file (§10). Re-run commands are in each spike's last section.

---

## Index

| # | Decision | From | Unblocks |
|---|---|---|---|
| 1 | ID numbering rule | SENSORS D10 | BLD-68 |
| 2 | Retire by date, never delete | SENSORS D11 | BLD-68 |
| 3 | Content hash covers the season-enabled set | SENSORS D18; BLD-20, BLD-26 | BLD-26, BLD-68 |
| 4 | A season is a monotone gate; no `enabled` flag | SENSORS D19; CHASSIS D3 | BLD-68, BLD-98 |
| 5 | The eleven Phase 3 sensors and their SensorIds | SENSORS D1, §3.3; ARCH §5; CHASSIS D8 | BLD-74, BLD-82–95 |
| 6 | Which sensors are chassis-intrinsic | SENSORS D3–D6 | BLD-83, BLD-86, BLD-98 |
| 7 | ModuleIds, `ChassisId`, the rest of the table | SENSORS D8, D12; CHASSIS D2 | BLD-68, BLD-98 |
| 8 | Phase 3 predicate and action ids, including the reference-policy blocks | SENSORS D13–D15; DRIVER D8 | BLD-97, BLD-99, BLD-102 |
| 9 | `Sensor::sample` sees `SensorEnv`, never `&World` | ARCH §1, §2 | BLD-74, BLD-75, BLD-111 |
| 10 | Who hears a beacon | new; SENSORS D5; BLD-106 | BLD-86, BLD-106 |
| 11 | `Return`: odometry in, `Fix` out, relative transponder returns, source ids | ARCH §4; SENSORS D2, D7 | BLD-74, BLD-82, BLD-86, BLD-87 |
| 12 | `Emission` is a typed channel | ARCH §3, §15 | BLD-74, BLD-84, BLD-85, BLD-95 |
| 13 | Terrain-relative navigation lives in the `BeliefUpdater`; a beacon fix never touches heading | ARCH §5 | BLD-87, BLD-90 |
| 14 | `Belief.map` is a point set with derived bins | ARCH §6 | BLD-77, BLD-87, BLD-101 |
| 15 | `PoseEstimate` is three sigmas and an epoch | ARCH §7 | BLD-77 |
| 16 | The rest of `Belief` | ARCH §8; DRIVER D6; CHASSIS D8 | BLD-77 |
| 17 | `ContactTrack` keeps every arrival; ranged tracks for lidar | ARCH §9 | BLD-89 |
| 18 | World collections, record-assigned ids, `Tick`/`AgentId` widths | ARCH §10, §11, §17; BLD-20 | BLD-69, BLD-70 |
| 19 | 20 Hz, and no seconds inside the sim | ARCH §17 | every tunable |
| 20 | The policy driver: tree data in `blindside-vm` behind `VmHost` | DRIVER D1, D2; ARCH §13 | BLD-62, BLD-75, BLD-102 |
| 21 | `Action`, `Intent`, `Actuator`, and where action state lives | ARCH §12; DRIVER §4.2 | BLD-78, BLD-99, BLD-101 |
| 22 | Chassis classes are in the game | CHASSIS D1 | BLD-73, BLD-78, BLD-98 |
| 23 | All four chassis records ship in Phase 3, season-gated; locomotion reads them | CHASSIS D3, D4 | BLD-71, BLD-78, BLD-98 |
| 24 | Schema room for the Swimmer | CHASSIS D8 | BLD-77, BLD-85, BLD-101 |
| 25 | Four width classes, terrain speed factors, locks only with keys | CHASSIS D5–D7 | BLD-71, BLD-72, BLD-73 |
| 26 | Tree semantics | DRIVER D3 | BLD-102 |
| 27 | Two channels per tick and `noop` | DRIVER D4 | BLD-102 |
| 28 | Recall overrides the tree | DRIVER D5 | BLD-105 |
| 29 | `self_report.current_action` and `action_running` | DRIVER D6 | BLD-97, BLD-102 |
| 30 | Budget unit, default, exhaustion | DRIVER D7; BLD-116 | BLD-102, BLD-120 |
| 31 | `MatchMode` | ARCH §14 | BLD-104 |
| 32 | `WorldView` | ARCH §15 | BLD-103 |
| 33 | `yields()`, `BlockId`, discoveries by depth, risk R9 | ARCH §16, §21 | BLD-72, BLD-103, BLD-108 |
| 34 | RNG purpose space | ARCH §18 | BLD-24, BLD-67, BLD-74 |
| 35 | Trig from a pinned pure-integer crate | ARCH §19 | BLD-67 |
| 36 | Phased tick order | ARCH §20; DRIVER §3.2 | BLD-107 |
| 37 | Acoustic model and budget | ACOUSTIC Q1, Q2 | BLD-79, BLD-81 |
| 38 | The benchmark cave and what the generator is | ACOUSTIC Q3, Q8; CHASSIS D5 | BLD-72, BLD-108 |
| 39 | Arrival bearing definition | ACOUSTIC Q6 | BLD-79 |
| 40 | Content is TOML with `Fx` as strings; `MatchRecord` stays JSON | SENSORS D16, D17, D21 | BLD-30, BLD-68 |
| 41 | `blindside-content` is lint-constrained, with a separate loader crate | SENSORS D20 | BLD-19, BLD-22, BLD-68 |
| 42 | Acoustic tunables | ACOUSTIC Q4, Q5, Q7, R4 | BLD-79, BLD-80, BLD-83 |
| 43 | Loadout validator rules, sonar/lidar exclusivity, bay capacity | CHASSIS D9; SENSORS §2 | BLD-92, BLD-98 |
| 44 | When each chassis ships; the harness flag; the numbers | CHASSIS D10–D12 | BLD-98, new BLD-208/209 |
| 45 | The Surveyor's stock loadout | SENSORS D9 | BLD-98 |
| 46 | Plan consequences of the driver decision | DRIVER D9–D11 | BLD-102, BLD-124, Phase 2 |
| 47 | BLD-87's beacon-fix criterion is restated | ARCH design problem 1 | BLD-87, BLD-88 |
| 48 | BLD-105's Recall criterion is re-based | ARCH design problem 2 | BLD-101, BLD-105 |
| 49 | GLOSSARY entries these decisions make wrong | consolidation; §6, §14, §20, §33, §42, §47 | GLOSSARY |

---

## Part A — Permanent: numbers, hashes and formats that can never change

### 1. One numbering rule for every ID kind

**Recommendation.** For SensorId, ModuleId, ChassisId, PredicateId, ActionId, AncientKindId,
BiomeId and ModeId alike: 0 is never assigned; 1–63 is the set present in the Phase 3 pack;
64–127 are named reservations for Phases 4–7; 128–255 are free; 256+ are season blocks in
shipping order; 65535 is a sentinel. A number carries no meaning and code never computes
one (DETERMINISM rule 7).

**Reason.** Contiguous shipped blocks read at a glance and one test checks all eight kinds.

**Evidence.** `spikes/SENSORS-AND-IDS.md` D10. ARCHITECTURE rule 1 and DETERMINISM rule 7
make every number permanent once a replay or saved policy carries it.

**If wrong.** Nothing irreversible: the ranges are documentation; an entry outside its range
is a review comment. The permanent part is the table in §5–§8, not the rule.

Designer: [ ] yes [ ] no

### 2. Retire by date, never delete

**Recommendation.** An entry is retired by adding `retired = "YYYY-MM-DD"` (and
`retired_value` for a predicate); it stays in its file, and `content/retired.toml`
duplicates `(kind, id)` so a deleted entry is still caught. Build fails on a duplicate id, a
live id in the ledger, a retired predicate without a value, and a new-match loadout naming a
retired module. A cancelled reservation is treated as retired.

**Reason.** ARCHITECTURE rule 1 made mechanical; a policy authored in season 1 must parse in
season 6.

**Evidence.** `spikes/SENSORS-AND-IDS.md` D11; BLD-68's build-fail list.

**If wrong.** None; this is the cheapest enforcement of a rule already agreed.

Designer: [ ] yes [ ] no

### 3. The content hash covers the season-enabled set, not file bytes

**Recommendation.** `content_hash()` is BLAKE3 over the canonical serialisation of every
non-retired entry with `season <= pack.active_season`, sorted by `(kind, id)`, fields in
declared order, `Fx` as `I32F32` bits little-endian, prefixed by `CONTENT_SCHEMA` and
`active_season`. Every field of every entry type gets a mutation test (changing it changes the
hash). This answers BLD-20's open item and BLD-26 lands this form, not file bytes.

**Reason.** Rule 5 says new content ships behind a season flag so it does not invalidate the
live season; rule 2 puts the hash in every replay. File-bytes hashing makes rule 5 a lie: a
flagged-off season-2 entry invalidates every season-1 replay, benchmark listing and market
verification.

**Evidence.** `spikes/SENSORS-AND-IDS.md` §4.1 item 3, D18: two packs with the same enabled
entries but different formatting, order, one `season = 2` entry and one retired entry hash
differently by bytes (`6e24d8ba…` vs `94f8ee3c…`) and identically by enabled set
(`b3fe9366…`); the enabled-set hash changes for season 2 (`055874c2…`). The Phase 0 branch
currently hashes `CONTENT_SCHEMA` only (BLD-26 built-so-far).

**If wrong.** This is the one place the cost is serious in both directions. A field left out
of the canonical serialisation is an unhashed balance change, which is the silent replay
divergence DETERMINISM fears; the mutation tests are the mitigation. File bytes fail loudly
but invalidate too much.

Designer: [ ] yes (enabled set) [ ] no (file bytes)

### 4. A season is a monotone gate; nothing carries an `enabled` flag

**Recommendation.** Each entry carries `season = N`, the first season it is enabled;
`pack.toml` carries `active_season`; entries are never disabled, only retired (§2). This
applies to chassis too: `spikes/CHASSIS-TIMING.md` D3's `enabled: bool` becomes a `season`
field (Surveyor at the active season; Scout, Hauler and Swimmer at a later one), and its D12
harness flag reads "run an entry whose season is later than the active one". Scout and
Hauler enter before launch (§44), which is a pre-season edit of their `season` field — legal
because no live season exists yet.

**Reason.** DESIGN: old behaviours stay usable; DESIGN-PRINCIPLES §1: a season ships
blocks. A per-season enable list could remove a block, and the enabled set would depend on
two files. One mechanism for all eight kinds keeps §3's hash a function of one thing.

**Evidence.** `spikes/SENSORS-AND-IDS.md` D19; `spikes/CHASSIS-TIMING.md` D3, D12 (the
conflict).

**If wrong.** If a season must ever pull a block, that is a dated retirement and the archive
rule changed, not the format.

Designer: [ ] yes [ ] no

### 5. The Phase 3 sensor set: eleven sensors, eight return shapes

**Recommendation.** Ship exactly: odometry (1), near-field (2), passive acoustic (3), sonar
(4), lidar (5), transponder interrogator (6), magnetometer (8), optical (9), structural
monitor (10), self-report (11), and — per §24 — a depth gauge, taking SensorId 7 **[guess:
the number]**. Terrain-relative navigation is a module (ModuleId 6) that enables a
`BeliefUpdater` stage (§13) and has **no SensorId and no `Return`**; SENSORS §1.2 row 7 and
§3.3 change accordingly, and its "nine return shapes" becomes eight (`Fix` is not a return,
§11). Lidar shares `Return::RangeBearing` with sonar and near-field, distinguished by
`source: SensorId`; there is no `Lidar` variant.

**Reason.** "The six sensors" (ROADMAP) is never enumerated; the reading that reconciles
ROADMAP, DESIGN's eight sources, ARCHITECTURE's `Return` and Phase 1's two additions (lidar,
near-field) is the table in SENSORS §1.2. A `Return` variant is a shape, not an instrument.

**Evidence.** `spikes/SENSORS-AND-IDS.md` §0 census (seed 7): sonar 59.4–60.3 returns per
ping, lidar 75.6–77 per sweep, near-field 3,098–5,837 per match; the rival heard 81–94 ping
bearings when the player carried sonar and 2 when it carried lidar. `spikes/ARCHITECTURE-RECONCILIATION.md`
§5 (TRN needs only Belief). `spikes/CHASSIS-TIMING.md` D8.1 asks for the depth-gauge id
that SENSORS §3.3 said nothing on the board needed.

**If wrong.** A sensor cut later is a retired id (cheap); a sensor added is a season block
(cheap). The expensive mistake is a shape change to `Return`, which is §11.

Designer: [ ] yes [ ] no

### 6. Which sensors are chassis-intrinsic

**Recommendation.** Odometry, near-field, the transponder interrogator and self-report are
part of every chassis (still `Sensor` impls with ids, so the hardware seam is uniform); the
passive array is a module, and an agent that drops it is deaf. The interrogator emits
nothing; the beacon *rack* is the module.

**Reason.** A body that cannot count its steps or weigh its hold is not a body; every agent
must hear its shaft (the only truth anchor, BLD-88, and how Recall's spiral ends); DESIGN
mounts the passive array on the flank as a module and BLD-98 lists it so.

**Evidence.** `spikes/SENSORS-AND-IDS.md` D3–D6: near-field supplies 81–87% of a sonar
carrier's map points (5,110 of 6,007 on seed 7); a near-field module would make "no
near-field" a loadout that cannot steer (BLD-101). PHASE-1-OPEN-QUESTIONS pushback 5 approved
near-field as "what a real machine would have".

**If wrong.** An intrinsic sensor can be given a slot cost in data later; making hearing
universal retires one ModuleId. Neither changes a SensorId.

Designer (near-field intrinsic): [ ] yes [ ] no
Designer (odometry and self-report intrinsic): [ ] yes [ ] no
Designer (interrogator intrinsic and silent; rack is the module): [ ] yes [ ] no
Designer (passive array is a module): [ ] yes [ ] no

### 7. ModuleIds, `ChassisId`, and the rest of the table

**Recommendation.** ModuleIds 1–10: `passive_array`, `sonar`, `lidar`, `beacon_rack`,
`cargo_bay`, `terrain_nav`, `magnetometer`, `optical`, `structural_monitor`,
`beacon_cloner`; reserved 64 `behaviour_reader`, 65 `decoy_emitter`, 66 `noise_flooder`,
67 `silt_release`, 68 `collapse_charge`. A new `ChassisId(u16)` newtype and an eighth
registry (BLD-68 says seven): Surveyor 1, Scout 2, Hauler 3, Swimmer 4 — the low numbers,
because §23 puts all four records in the Phase 3 pack and §1's rule puts anything in the
pack in 1–63; SENSORS §3.5 (64–66) changes to match. AncientKindId 1 `fixed_cycle`, 64–65
reserved for Phase 7; BiomeId 1 `reference`, 64 `dry_clear` (BLD-108's R9 seed); ModeId 1
`extraction`, 64 `endurance`, 65 `survey`, 66 `race`.

**Reason.** A loadout is one chassis plus N modules with different fields; one id space would
make "a Surveyor in a module slot" representable. Every reserved name comes from a board
story (BLD-106, 163, 171, 174, 175, 180, 181, 185, 204, 205).

**Evidence.** `spikes/SENSORS-AND-IDS.md` D8, D12, §3.4–§3.10; `spikes/CHASSIS-TIMING.md`
D2 (the numbering conflict: 2/3/4 vs 64/65/66).

**If wrong.** A cancelled reservation is marked and never reused; sixteen bits is cheap. If
one registry is wanted, chassis take ModuleIds 32–47 and `ChassisId` is deleted before
anything ships.

Designer (module list and reservations): [ ] yes [ ] no
Designer (`ChassisId`, eighth registry, Surveyor 1 / Scout 2 / Hauler 3 / Swimmer 4): [ ] yes [ ] no

### 8. Phase 3's predicate and action ids include the reference-policy blocks

**Recommendation.** PredicateIds 1–3 are Phase 2's (`unexplored_branch_exists`,
`uncertainty_gt(θ)`, `carrying_cargo`), then whatever BLD-59 records, then the six the
reference policies need, numbered after BLD-59's additions in this order:
`signature_within(window, q_min)`, `at_unfinished_place(kind, radius)`,
`ping_ready(cooldown)`, `unmapped_ahead(n)`, `beacon_due(cells)`, `action_running(id)`
(`at_shaft` folds into `at_unfinished_place(shaft)`). ActionIds 1–10 as SENSORS §3.7 with
`ping` renamed `active_scan` (3) and `hold` (10), plus `noop` (11) and `investigate` (12)
(`wait` folds into `hold`); reserved 64–69 unchanged. SENSORS's reserved predicates 64
(`signature_quality_ge`), 67 (`ticks_since_ping_ge`) and 68 (`contact_heard_within`) are
superseded by the parameterised `signature_within` and `ping_ready` and marked cancelled;
65, 66, 69, 70 stay reserved. **This flips SENSORS D13** (which assumed hand-written Rust
policies reading Belief by name) to "assign", as a consequence of §20. Whether players get
these blocks on day one or find them by depth is a separate content call (not asked here).

**Reason.** DESIGN-PRINCIPLES §1: nothing that consumes blocks is written over a fixed set by
name; a Rust policy that reads `Belief` directly where no predicate exists is exactly that.
BLD-97's "do not expand" and BLD-102's "reproduce Phase 1's cautious and aggressive
behaviours" cannot both hold, and the cost of choosing BLD-97 was measured. R5 (vocabulary
size) is still answered by the Phase 2 gate; these are batch-coverage blocks, not the
player's day-one vocabulary.

**Evidence.** `spikes/AGENT-DRIVER.md` §2.3, §7, D8: restricted to Phase 2's 3 + 2, the
rival's death at the machinery drops from 3/8 to 2/8 (path luck, matching tuning.py's
pre-investigate note) and the cautious agent cannot freeze; with the blocks, spoof 8/8,
cargo on the identical tick 8/8, rival dies 3/8 vs hand-written 4/8. §2.4: the latch
`action_running` is needed on 1 of 6 seeds at Phase 1's numbers and on every return under
Phase 3's 45-cell chain. `spikes/SENSORS-AND-IDS.md` D13–D15.

**If wrong (no).** The beat-sheet seed in BLD-108 must come from a reflex hidden inside an
action, which PHASE-2-OPEN-QUESTIONS (c) warned against, and BLD-130's requirement that the
baseline read a contact predicate has nowhere to go.

Designer (register the six predicates and `noop`, `investigate`): [ ] yes [ ] no
Designer (`ping` is named `active_scan` and fires whichever active module is fitted): [ ] yes [ ] no
Designer (`hold` is an action): [ ] yes [ ] no

---

## Part B — Expensive: the invariant and the hashed, serialised schemas

### 9. `Sensor::sample` sees a `SensorEnv`, never `&World`; returns go into `&mut Vec<Return>`

**Recommendation.**

```rust
pub trait SensorEnv {
    fn own_true_delta(&self) -> MotionDelta;
    fn own_pose(&self) -> Pose;
    fn own_state(&self) -> SelfState;
    fn medium_at(&self, pos: Vec2Fx) -> Medium;
    fn raycast(&self, from: Pose, angle: Fx, max_range: Fx, blocks: Blocks) -> Option<Fx>;
    fn arrivals_at(&self, pos: Vec2Fx, out: &mut Vec<Arrival>);
    fn transponders_in_range(&self, pos: Vec2Fx, out: &mut Vec<TransponderHit>);   // see §10: all teams' beacons
    fn terrain_patch(&self, pos: Vec2Fx, radius: Fx) -> OccupancyPatch;
    fn structural_warning_at(&self, pos: Vec2Fx) -> Option<Ticks>;
}
pub trait Sensor {
    fn id(&self) -> SensorId;
    fn cost(&self) -> SlotCost;
    fn emits(&self) -> Emission;
    fn sample(&self, env: &dyn SensorEnv, ctx: &SensorCtx, fired: bool,
              rng: &DeterministicRng, out: &mut Vec<Return>);
}
```

Implemented once over `(&World, AgentId)` inside `sensing/mod.rs`, the only module that names
both `World` and `Belief`.

**Reason.** ARCHITECTURE's `sample(&World, …)` and its hardware section ("no sensor may
query arbitrary world state") contradict each other; the trait is the rule the compiler
holds. The nine requests are what a robot's drivers answer.

**Evidence.** `spikes/ARCHITECTURE-RECONCILIATION.md` §1: of Phase 1's seven sensors, two
walk whole `World` collections (`sensor_rig.py:166`, `:218`). §2: returns per agent per tick
peak at 63–67 (sonar) and 91–96 (lidar), so `SmallVec<[Return; 8]>` spills on every ping
and sweep. `spikes/SENSORS-AND-IDS.md` §0 agrees (60–77 per active sample).

**If wrong.** A missing request is one method. `&World` leaves BLD-74, BLD-75 and BLD-111
with nothing to test.

Designer: [ ] yes [ ] no

### 10. Who hears a beacon

The spikes leave a hole. SENSORS D5 says "the beacon itself is the emitter, audible at
short range, which is what lets a rival find and clone or steal it"; ACOUSTIC's emitter load
(§2.6) has no beacons at all; ARCH §1's `transponders_in_range(pos, owner)` filters to the
listener's own team; BLD-86 says unknown beacon ids are ignored by Belief; and BLD-106's
arming rule needs "a foreign beacon within reach" that the rival can observe.

**Recommendation.** Beacons are not acoustic emitters (the passive array never hears them;
the acoustic budget in §37 stands). The interrogator returns every beacon in its range from
any team as `Return::Transponder { beacon, range, angle }`; Belief resolves own-team ids it
has a record of into fixes, records foreign ids in `Belief.foreign_beacons` (id, believed
position, tick) with no fix, and drops own-team ids it never recorded (BLD-86 unchanged for
fixes). BLD-106's arming predicate reads `foreign_beacons`. **[guess: the shape; the
behaviour is the smallest one that gives BLD-106 an observable.]**

**Reason.** Without a foreign-beacon observable the spoof cannot be a Belief-side action, and
BLD-106 is the beat the whole Phase 1 gate was watched on. Making beacons acoustic emitters
would add 40–80 continuous emitters to a budget measured without them.

**Evidence.** Measured for this file (Phase 1 at `d19579b`, seeds 1–8, sonar, truth
distances): the rival is within 18 cells (Phase 1's spoof range) of a foreign non-anchor
beacon on **8/8 seeds**, first at 140.8–155.7 s — the same window as Phase 1's scripted
spoof at 140 s — and within 6 cells (honest beacon range) on 5/8 (seeds 2, 6, 7 never;
closest 9.9–16.5 cells). So an arming rule of the form "foreign beacon within 18 cells" fires
on every seed at about the scripted time, and "within 6" does not. Script:
session scratchpad `foreign_beacons.py`, `PYTHONPATH=. .venv/Scripts/python.exe … 1 2 3 4 5 6 7 8`.

**If wrong.** If beacons should be audible (a `Tone` the passive array hears), ACOUSTIC's
budget must be re-measured with ~60 emitters of range ~6, and SoundCharacter gains an arm.
If foreign beacons should be invisible, BLD-106 needs a different observable and the
designer should say which.

Designer: [ ] yes [ ] no

### 11. `Return`: odometry in, `Fix` out, transponder returns are relative, sources are ids, no truth tags

**Recommendation.**

```rust
pub enum Return {
    Odometry     { forward: Fx, turn: Fx },                                   // already corrupted
    RangeBearing { range: Fx, angle: Fx, quality: Fx, source: SensorId,
                   character: SurfaceCharacter },                             // §24: Rock | Water
    Bearing      { angle: Fx, quality: Fx, character: SoundCharacter },
    Transponder  { beacon: BeaconId, range: Fx, angle: Fx },                  // Belief resolves it
    Anomaly      { rough_direction: Fx, strength: Fx },
    Optical      { patch: OccupancyPatch },
    Structural   { time_to_failure: Option<Ticks> },
    SelfReport   { cargo: u8, power: Fx, damage: Fx, modules: ModuleHealth, medium: Medium },
}
```

`Fix` leaves `Return`; a fix is what Belief does with a `Transponder` return or a terrain
match, recorded as `FixRecord { source: FixSource::Beacon(BeaconId) | Terrain }` on the
Belief side (the variant name `Beacon` is ARCHITECTURE's; SENSORS's `BeaconFix` is renamed
`Transponder`). Phase 1's `PointSource.FALSE` does not port: a false return carries the id of
the sensor that hallucinated it and a low quality, nothing else.

**Reason.** Drift must be born in the sensor layer from the true achieved motion, which
needs a variant; the spoof must run through the identical code as an honest fix, which
needs the return to be relative to a beacon the agent has its own record of. An absolute
`Fix { position }` cannot lie through belief. The `FALSE` tag was ground truth on the belief
side of the line.

**Evidence.** `spikes/ARCHITECTURE-RECONCILIATION.md` §4: the spoof produces a 33.6–35.8
cell jump at 11–12 σ on all 16 runs through `belief.py:165–173`; honest fixes through the
same function never exceed 13.8 σ. `spikes/SENSORS-AND-IDS.md` D2, D7. `spikes/CHASSIS-TIMING.md`
D8.3 needs the character field (§24).

**If wrong.** With `Fix { position }` the shaft still works but spoofing has to be
special-cased, and that special case is the lie marker the comment says must not exist.

Designer: [ ] yes [ ] no

### 12. `Emission` is a typed channel; a presence can carry more than one

**Recommendation.**

```rust
pub enum Emission { None, Acoustic { signature: AcousticSignature, audible_for: Ticks }, Optical { light: LightSignature } }
```

`Sensor::emits()` is the static property (loadout screen, validation, silhouette); the
sensing module registers the emitter when `sample` runs with `fired == true`: acoustic to
`World.acoustics`, optical to a line-of-sight list consumed by BLD-95. ARCH §15's
`Presence.emitting: Emission` becomes a pair of `Option`s (acoustic, optical), because a
sonar carrier with a camera lamp, or a Swimmer with both sonar and lidar (§43), emits on
both channels in one tick.

**Reason.** Sonar and lidar differ in who can notice, not in loudness; `None` for lidar makes
it a silent sonar, which the Part 4 decision says it is not.

**Evidence.** `spikes/ARCHITECTURE-RECONCILIATION.md` §3; `spikes/SENSORS-AND-IDS.md` §0:
the rival heard 81–94 `ping` bearings against a sonar player and 2 against a lidar player.

**If wrong.** A third channel is a third arm; dropping the optical tell leaves an unused arm.

Designer: [ ] yes [ ] no

### 13. Terrain-relative navigation is a `BeliefUpdater` stage; a beacon fix changes heading by exactly zero

**Recommendation.**

```rust
pub trait BeliefUpdater {
    fn integrate(&mut self, b: &mut Belief, r: &Return);                   // Odometry only; never the MotorCmd
    fn fuse(&mut self, b: &mut Belief, returns: &[Return], tick: Tick);
}
// inside fuse: odometry -> place RangeBearing points -> Transponder returns into position-only
// fixes -> terrain match if ModuleId 6 is fitted (scan-match this tick's points against
// Belief.map over a small pose window; may correct heading, bounded by content) -> contacts
```

**Reason.** TRN needs this tick's range returns, the agent's own map and its pose estimate —
all in Belief, none in World. A robot's scan matcher runs on the robot over its own map. The
question "sensor variant or updater path" dissolves once TRN is placed where its inputs are.
`integrate_motion(cmd)` goes: Belief integrates the odometry return, never the command.

**Evidence.** `spikes/ARCHITECTURE-RECONCILIATION.md` §5: `HEADING_FIX_GAIN = 0` because
inferring heading from a beacon fix made half of honest loop closures worse; heading error at
8:00 is −33° to −50° (player) and +27° to +63° (rival) on every seed, and the spoof's 34-cell
position lie becomes a 90-cell one by 6:30 on seed 7 because heading is wrong too.

**If wrong.** If TRN needs denser scans than the fitted sensor gives, the fix is a
higher-rate `RangeBearing` sensor through `SensorEnv`; the trait does not change.

Designer: [ ] yes [ ] no

### 14. `Belief.map` is a timestamped point set with derived occupancy bins

**Recommendation.**

```rust
pub struct MapPoint { pub pos: Vec2Fx, pub placed: Tick, pub odo: Fx, pub source: SensorId,
                      pub character: SurfaceCharacter, pub confidence: Fx }
pub struct BeliefMap { pub points: Vec<MapPoint> /* cap: content, guess 32_768 */, bins: OccupancyBins /* derived, not hashed */ }
impl BeliefMap {
    pub fn relax(&mut self, c: &PoseCorrection);
    pub fn blocked(&self, pos: Vec2Fx, viability: &TerrainViability) -> bool;               // §24: chassis-aware
    pub fn clearance(&self, from: Vec2Fx, heading: Fx, max_range: Fx, viability: &TerrainViability) -> Fx;
}
```

Separately: weight the relax by odometry distance since the epoch (`odo`), not by seconds.

**Reason.** An occupancy grid has no timestamp and no source, so a fix can stop the smear but
cannot move the ghost corridor back; the snap is the most important visual in the game and is
impossible over a grid. The bins are the grid, rebuilt from the points, for steering.

**Evidence.** `spikes/ARCHITECTURE-RECONCILIATION.md` §6: 13–56 relaxes per match moving up
to 3.8k (sonar) or 9.8k (lidar) points; map size at match end 5–7k points (sonar) vs
27–29k (lidar); 5–18% of points are placed while stationary, which time-weighting moves too
far. BLD-101: the spoofed agent "held a 26,000-point map and used none of it".

**If wrong.** A grid loses the snap; points without bins lose map-aware steering. Keeping
time-weighting breaks nothing; stationary points relax a little too far.

Designer (point set + derived bins): [ ] yes [ ] no
Designer (relax weighted by odometry distance, not time): [ ] yes [ ] no

### 15. `PoseEstimate` is three sigmas and an epoch, not a covariance

**Recommendation.**

```rust
pub struct PoseEstimate { pub mean: Pose, pub sigma_along: Fx, pub sigma_cross: Fx, pub sigma_heading: Fx, pub epoch: Epoch }
pub struct Epoch { pub tick: Tick, pub pose: Pose, pub odo: Fx }
```

**Reason [guess].** The ellipse is a gameplay object whose parameters are content and whose
honesty is a tuning choice ("kept slightly under the truth so a fix that jumps further than
the ellipse promised is the tell"). A 3×3 EKF needs a Jacobian per sensor in fixed point and
buys nothing a player sees; three sigmas are a diagonal covariance in the travel frame.

**Evidence.** `spikes/ARCHITECTURE-RECONCILIATION.md` §7: Phase 1 never built a covariance;
`belief.py:84–97` is the three-parameter model.

**If wrong.** Predicates over `sigma_pos()` do not care which representation is underneath;
a later covariance is an internal change.

Designer: [ ] yes [ ] no

### 16. The rest of `Belief`

**Recommendation.**

```rust
pub struct Belief {
    pub pose: PoseEstimate, pub map: BeliefMap, pub trail: Vec<TrailPoint>,
    pub contacts: Vec<ContactTrack>,
    pub beacons: BTreeMap<BeaconId, KnownBeacon>, pub chain: Vec<BeaconId>,     // own drops in order
    pub foreign_beacons: Vec<ForeignBeacon>,                                    // §10
    pub fixes: Vec<FixRecord>,                                                  // the only belief-legal spoof tell
    pub inventory: Inventory,                                                   // cargo, and blocks (§33)
    pub self_report: SelfReport,      // cargo, power, damage, modules, medium (§24), current_action + since (§29)
    pub loadout: LoadoutRef,
    pub ticks_since_fix: Ticks, pub ticks_since_emit: Ticks,
}
```

`Belief.self_report` is the union of what the `SelfReport` return carries, the depth gauge,
and the runner's own report; ARCH §8's `nav: NavState` is **not** a Belief field (§21). No
`known_places`: generated caves have no prior survey; the shaft arrives as
`KnownBeacon { truth_anchor: true }`.

**Reason.** Every field is something a Phase 1 policy or predicate read. `beacons` must be a
map with a separate order because relax skips the fixing beacon and truth anchors by id.

**Evidence.** `spikes/ARCHITECTURE-RECONCILIATION.md` §8: over 318 honest own-beacon fixes,
53% increased true position error, and the error after such a fix equals the error at that
beacon's drop within 1.8–3.5 cells — the chain re-anchors to past belief (BLD-88), which
`KnownBeacon.truth_anchor` encodes.

**If wrong.** A missing field is a schema bump when a predicate needs it.

Designer: [ ] yes [ ] no

### 17. `ContactTrack` retains every arrival; a moving range cluster opens a ranged track

**Recommendation.** `ContactTrack { id, origin: Acoustic | Ranged { range }, arrivals:
Vec<Arrival> (capped, Phase 1: 60), character, estimate: Option<(Vec2Fx, Fx)>, stationary: Fx,
last }`, each `Arrival` keeping its tick, bearing, quality, character and the believed pose it
was heard from. The cluster tracker is an updater stage: a `RangeBearing` group that persists
across sweeps and is not in the bins opens a `Ranged` track. No `is_echo` anywhere.

**Reason.** A contact is evidence, not a verdict; retaining arrivals is what makes a second
arrival inside the merge window a Belief-visible event without a flag. A lidar carrier
otherwise cannot notice a rival at all.

**Evidence.** `spikes/ARCHITECTURE-RECONCILIATION.md` §9: the scripted echo at 2:15 merged
into the rival's standing contact and never appeared as its own event; the lidar player logs
contacts only from the rival's sonar pings.

**If wrong.** Cap arrivals lower; the cluster tracker can ship later because `origin` exists.

Designer: [ ] yes [ ] no

### 18. World collections are `BTreeMap` keyed by record-assigned ids; `Tick(u64)`, `AgentId(u32)`

**Recommendation.** No `SlotMap` anywhere (its key is insertion order under another name,
rule 7 broken by the type). `AgentId` from `MatchRecord.loadouts` (team, slot);
`BeaconId { owner: AgentId, seq: u16 }`; `WreckId(AgentId)`; `DepositId`, `AncientId`,
`DiscoveryId` from the generator by a seed-determined rule. `World { tick, cave, agents,
beacons, wrecks, deposits, discoveries, ancients, acoustics, optical }`, every collection a
`BTreeMap`; no `rng` field. Phase 1's `next_beacon_id`, `spoof_done`, `pending_sounds`,
`events`, `load_progress` do not port. **Widths: keep the Phase 0 branch's `Tick(u64)` and
`AgentId(u32)`** rather than ARCH §17's `u32` / §10's `u16`; this is BLD-20's Tick question
answered once, and it avoids re-goldening Phase 0 fixtures for no gain.

**Reason.** `BTreeMap` makes rule 6 a property of the container. `BeaconId { owner, seq }`
makes an agent's ids independent of step order, which is what BLD-69 is for. At tens of
entries the lookup cost is not measurable.

**Evidence.** `spikes/ARCHITECTURE-RECONCILIATION.md` §10, §11: Phase 1's `world.py:51`
numbers beacons from a World counter, so the id an agent's third beacon gets depends on
whether the rival dropped first — the rule 7 violation. Populations: 14–21 beacons, 2 agents.
`claude/phase-0-harness:crates/blindside-sim/src/ids.rs` has `Tick(u64)`, `AgentId(u32)`.

**If wrong.** An entity type reaching thousands swaps one map for a sorted `Vec`; nothing
downstream names the container. DETERMINISM rule 2's "or `SlotMap`" is deleted.

Designer (BTreeMap, record-assigned ids, no SlotMap, the World field list): [ ] yes [ ] no
Designer (`Tick(u64)`, `AgentId(u32)` as Phase 0 built them): [ ] yes [ ] no

### 19. 20 Hz, and no seconds inside the constrained crates

**Recommendation.** `TICK_HZ = 20`; `Tick` and `Ticks` only; speeds in cells per tick,
periods and latencies in `Ticks`. Content may state seconds; the loader converts once and
errors on a non-integer tick count. Gate arithmetic: 1,000 × 9,600 ticks in 600 s is
62.5 µs per tick single-threaded, ~500 µs with eight matches in parallel.

**Reason.** Every Phase 1 measurement and fifteen calibrated constants are at 20 Hz; a sim that
accumulates seconds from `DT` drifts from its own clock.

**Evidence.** `spikes/ARCHITECTURE-RECONCILIATION.md` §17: `1/20` in I32F32 is
`0x0CCCCCCC` = 0.0499999998; `20 × DT` = 0.9999999963. Python tick mean 0.37–0.88 ms, worst
24–34 ms (every worst tick a whole-cave Dijkstra).

**If wrong.** 10 Hz halves every tick-denominated constant in content; the type does not
change. Letting seconds in makes `DT`'s bit pattern part of the content hash.

Designer: [ ] yes [ ] no

### 20. The policy driver: a memoryless tree interpreter in `blindside-vm` behind `VmHost`

**Recommendation.** Phase 3 agents run `CompiledPolicy { schema, program: FlatTree, budget:
VmBudget, policy_hash }` through `blindside_vm::run_tick(&CompiledPolicy, &mut VmState, &mut
impl VmHost) -> TickReport`, with `VmHost { eval_predicate(id, params) -> bool,
run_action(id, params) -> ActionStatus }`. The sim's entry point and BLD-75's compile-fail
target is `blindside_sim::policy::PolicyRunner::evaluate(&mut self, b: &Belief, tick: Tick)
-> Intent`. `Policy` with `BtNode` stays in Phase 4's `blindside-behavior`. Both reference
policies are tree *data* over the registries, loaded by the harness and referenced by
`policy_hash`. Not hand-written Rust (option A), not a bytecode VM pulled forward (B).
Names are unified here: DRIVER's `VmHost`, `CompiledPolicy`, `PolicyRunner` replace ARCH
§13's `Host`, `Program` and free `evaluate`; ARCH §12's `Intent` replaces DRIVER's
`ActuatorRequests`.

**Reason.** It is the artifact Phase 2 emits and Phase 4 compiles from; Phase 3 is the only
phase in which that artifact would not exist under A or B. Under A the 1,000-match replays
are of closures the VM cannot re-run, and BLD-130's baseline is something the node editor
cannot express. The host trait breaks the sim/vm dependency cycle without moving Belief.

**Evidence.** `spikes/AGENT-DRIVER.md` §2: a throwaway tree interpreter over the unchanged
Phase 1 sim, 8 seeds — spoof 8/8 under both drivers within 2.2 s, cargo on the identical
tick 8/8, rival dies at the machinery 3/8 (tree) vs 4/8 (hand), player 1/8 both, byte-identical
reruns; 33/32-node trees, 18.4 node visits per tick mean, 24 peak, 7.4 predicate evaluations
per tick, the chosen leaf changes 4–12 times per match. §10: 3.5 d, +1.5 d over BLD-102's
estimate, roughly −1 d net over Phases 3 and 4 **[guess]**.

**If wrong.** 1.5 d over BLD-102 and a ~150-line interpreter Phase 4 would have written
anyway as BLD-125's oracle.

Designer (tree interpreter in `blindside-vm`, reference policies as data): [ ] yes [ ] no
Designer (placement and names as above; `PolicyRunner::evaluate` is BLD-75's target): [ ] yes [ ] no

### 21. `Action`, `Intent`, the actuator seam, and where multi-tick action state lives

**Recommendation.**

```rust
pub struct Intent { pub motor: MotorCmd, pub requests: SmallVec<[Request; 4]>, pub report: RunnerReport }
pub struct MotorCmd { pub heading: Fx, pub speed: Fx, pub gait: GaitId }
pub enum Request { Emit(SensorId), DropBeacon, Load, Interface, AbortToShaft, CloneBeacon { target: BeaconId, offset: Vec2Fx } }
pub trait Action { fn id(&self) -> ActionId;
                   fn run(&self, b: &Belief, nav: &mut NavState, params: &[Fx], out: &mut Intent) -> ActionStatus; }
pub trait Actuator { fn apply(&mut self, agent: &mut AgentTruth, cave: &Cave, cmd: &MotorCmd, dt: Ticks); }
```

`NavState` (DRIVER's `ActionRuntime`) is owned by the `PolicyRunner` *beside* Belief, not
inside it: hashed, serialised with the agent's belief-side state, reset per action on entry,
never read by predicates. Durable facts an action wants a predicate to see (running action
and its start tick, plan progress, a place's done/given-up status) travel in
`Intent.report` and are fused into `Belief.self_report` in the fuse phase, like any other
return **[guess: the channel]**. This resolves ARCH §8/§12 (which listed `nav` inside Belief
yet passed `&mut NavState` separately) and DRIVER §4.2/§4.4 (which kept the runtime outside
Belief yet said durable facts "live in Belief" without saying how they get there).

**Reason.** `evaluate` takes `&Belief` (BLD-102's criterion and BLD-75's test), so nothing
inside evaluation can hold `&mut Belief`; an action that reads `&Belief` and writes only
`NavState` cannot corrupt pose, map or contacts. `Intent` is Phase 1's `MotorCommand` with
the booleans made a list so a new module is a new `Request` arm. The actuator takes truth
because it is truth-side; the hardware seam is the shape of `MotorCmd`.

**Evidence.** `spikes/ARCHITECTURE-RECONCILIATION.md` §12 (`policy.py:20–54` carries about
twenty fields of multi-tick state); `spikes/AGENT-DRIVER.md` §4.2, §4.4.

**If wrong.** If Phase 4 wants stateless one-shot actions, `NavState` stays where it is and
actions become `run(&Belief, params) -> Intent` with the VM owning `Running`: a trait change
on a registry of about twelve.

Designer: [ ] yes [ ] no

### 22. Chassis classes are in the game

**Recommendation.** Confirm Scout, Hauler and Swimmer are player-selectable chassis in the
shipped game, so the width and flooding locks the board already builds (BLD-71, 73, 78, 85,
98) have keys.

**Reason.** Every document but the board assumes it; DESIGN-PRINCIPLES §2 needs depth tiers
with keys; DESIGN's prep phase is a chassis decision plus a module decision.

**Evidence.** `spikes/CHASSIS-TIMING.md` §1: eight board mechanics that only mean something
if a second chassis exists, and no epic ever builds one.

**If wrong (no).** Delete BLD-73's constriction/flooded-lock criterion and BLD-78's
per-chassis width class so the generator does not place value nobody can take; §23–§25 and
§44 are skipped.

Designer: [ ] yes [ ] no

### 23. All four chassis ship in Phase 3 as content records, season-gated; locomotion reads the record

**Recommendation.** BLD-98 writes four records (data only): id, name, season (§4),
body_diameter, enter_width_class, turn_width_class, slots, mass and power budgets,
max_cargo_bays, base_speed, `terrain { dry, flooded }` speed factors, motion_noise_range,
pressure_limit_depth, gaits, intrinsic_sensors. Only the Surveyor is in the active season;
the validator, the hash and the tests know all four. BLD-78's "Surveyor is blocked below its
width class" becomes "an agent is blocked below its chassis's enter class, cannot turn below
its turn class, and moves at base_speed × terrain factor × gait"; BLD-71's classifier takes
the chassis's viability as an argument. No Surveyor constant exists in locomotion.

**Reason.** It is the cheapest moment to make the shape right; the data is a few dozen lines;
it is what makes §44's later stories "flip a season, make a model" rather than "design a
chassis system". Same code either way; only where the number lives differs.

**Evidence.** `spikes/CHASSIS-TIMING.md` D3, D4; cost 1.5 d in Phase 3 (§4).

**If wrong.** About one day of records and tests nobody plays.

Designer: [ ] yes [ ] no

### 24. Schema room for the Swimmer, in Phase 3

**Recommendation.** Four small things in hashed, serialised types: a depth-gauge SensorId
(§5) producing the medium the body is in; `SelfReport.medium: Dry | Submerged` (§16); a
`SurfaceCharacter { Rock, Water }` on `RangeBearing` and `MapPoint` (§11, §14) so the
water surface lidar returns as a wall is a door on a Swimmer's map; and `blocked()` /
`clearance()` taking the agent's own terrain viability from `Belief.loadout` (§14).

**Reason.** Adding a field to a hashed type later is a schema bump under a live season, which
BLD-203 forbids; reserving them now is a quarter-day each.

**Evidence.** `spikes/CHASSIS-TIMING.md` D8; `spikes/ARCHITECTURE-RECONCILIATION.md` §4, §6
lacked the character field and the viability argument.

**If wrong.** Half a day of fields that stay `Dry` and `Rock` forever.

Designer: [ ] yes [ ] no

### 25. Cells carry four width classes; terrain is a speed factor; the generator locks value only where a key exists

**Recommendation.** Per-cell width class crawl (0) / narrow (1) / passage (2) / hall (3),
widths **[guess]** 2–3 / 3–4 / 4–5 / ≥5 cells; BLD-72 emits all four in every seed with the
proportion per class a biome weight. Chassis name the class they enter and the class they can
turn in (Scout crawl/crawl, Surveyor narrow/passage, Hauler hall/hall, Swimmer narrow/passage).
`terrain { dry, flooded }` per chassis is a speed factor, 0 meaning wall; the Swimmer is
amphibious (dry 0.4 **[guess]**), not immobile. BLD-73 places a crawl-only or flooded-only
deposit only if a chassis in the active season holds that key; with the Phase 3 pack that
means no locks and an honest parity test.

**Reason.** With Phase 1's widths nothing under 3.6 cells is distinguishable, so the width
axis only differentiates chassis if the generator emits classes deliberately. No Phase 1
shaft touches water, so a pure swimmer cannot leave its shaft chamber. As written BLD-73
places value in Phases 3–5 that no chassis can reach and counts it in parity.

**Evidence.** `spikes/CHASSIS-TIMING.md` §2.1: eroding the Phase 1 grid, a 4.0-cell body
loses deposit A and a 5.0 body cannot leave the shaft; passages are 4–6 wide. §2.2: 12% of
free cells flooded; the sump is a 7-cell shortcut to the machinery for an amphibious body and
a detour for a slow walker.

**If wrong.** Class boundaries are content and can move; the number of classes is cave
schema and should not. A pure swimmer needs a guaranteed flooded route from a shaft (a day in
BLD-72 and a fairness question). If unreachable deposits are wanted as a tease, exclude them
from the parity sum instead.

Designer (four width classes, chassis enter/turn class): [ ] yes [ ] no
Designer (terrain speed factors; Swimmer walks badly rather than not at all): [ ] yes [ ] no
Designer (locks only where an enabled chassis holds the key): [ ] yes [ ] no

---

## Part C — A refactor if wrong: traits, order, models

### 26. Tree semantics: memoryless, evaluated from the root every tick, pre-emptible

**Recommendation.** Leaves return Running / Success / Failure; Sequence stops at the first
non-Success, Selector at the first non-Failure; Guard runs its child if the predicate holds.
A changed leaf pre-empts the running action at once; an action's private state resets on
entry; anything that must survive de-selection is a fact in Belief (§21).

**Reason.** It is Phase 2's `decide(belief) -> action` plus the minimum to run continuously.

**Evidence.** `spikes/AGENT-DRIVER.md` §4.1, D3: leaf changes 4–12 per match, so per-tick
evaluation costs nothing and a per-tick trace compresses to almost nothing.

**If wrong.** Phase 2 trees replayed in Phase 3 may turn back mid-passage where the
demonstration turned at the next junction; the fix is an "uninterruptible until done" flag on
`take_branch`, action-side, no schema change.

Designer: [ ] yes [ ] no

### 27. Two channels per tick, and `noop` is an ActionId

**Recommendation.** A tick may carry any number of instant module actions (`active_scan`,
`drop_beacon`: Success at once) and at most one locomotion action (Running); a second
locomotion leaf in the same tick returns Failure. Optional branches end in `noop`, an
ActionId in content, not a node kind, so ARCHITECTURE's `BtNode` set is unchanged.

**Reason.** Lets "ping then keep driving" be written without a new node kind.

**Evidence.** `spikes/AGENT-DRIVER.md` §4.3, D4: the tree's emission channel kept sweeping
during a 30 s load dwell (320 sweeps vs 301), a real small difference from Phase 1's `LOAD`
mode.

**If wrong.** Phase 4 adds a decorator node and the compiler folds `noop` away.

Designer: [ ] yes [ ] no

### 28. Recall is a terminal driver-level override, never a tree node

**Recommendation.** On delivery the runner stops evaluating the tree for the rest of the
match and runs `abort_to_shaft` directly. Player commands are a `Command` enum in
`MatchRecord`, not ActionIds.

**Reason.** The player's one command cannot depend on the policy author's goodwill; a market
policy that ignored Recall is a griefing vector; BLD-105 requires terminal.

**Evidence.** `spikes/AGENT-DRIVER.md` §4.5, D5; `spikes/SENSORS-AND-IDS.md` §3.7.

**If wrong.** If policies should react to Recall (drop cargo first), a `recalled` predicate is
added and the override becomes a default: a day.

Designer: [ ] yes [ ] no

### 29. `Belief.self_report` carries the running action and its start tick; `action_running(id)` is a predicate

**Recommendation.** As §16 and §21: the runner reports it through `Intent.report`.

**Reason.** The only latch a memoryless tree has; both reference policies need it ("once
lost, stay on the way home"; "interface for 80 s").

**Evidence.** `spikes/AGENT-DRIVER.md` §2.4, D6: without the guard the agent flipped back
to surveying on 1 of 6 seeds at Phase 1's numbers, and would on every return under Phase 3's
45-cell honest chain, which collapses sigma below θ on the way home.

**If wrong.** The cautious agent oscillates home/survey; the alternative is VM registers,
which is BLD-116's question and not available in Phase 3.

Designer: [ ] yes [ ] no

### 30. Budget unit is node visits, default 256 per tick, exhaustion stops the agent for that tick

**Recommendation.** One budget unit per node visit; default 256 **[guess]** on the loadout as
content; on exhaustion the runner emits no locomotion request, the actuator holds heading at
speed zero, and `TickReport.exhausted` goes into the trace. Phase 4 re-expresses the budget
in ops — a content change and a content-hash change, loud by construction.

**Reason.** Stopping is legible in a replay (the machine froze because its policy was over
budget) and cannot walk an agent into rock. This deviates from BLD-116's recommendation that
"the last MotorCmd holds"; neither reference tree ever exhausts, so Phase 3 replays are the
same whichever Phase 4 settles on.

**Evidence.** `spikes/AGENT-DRIVER.md` §2.2, §4.6, D7: reference trees peak at 24 visits;
a Phase 2-size tree is 5.

**If wrong.** A one-line change with no effect on Phase 3 replays.

Designer: [ ] yes (stop) [ ] no (last command holds, per BLD-116)

### 31. `MatchMode`

**Recommendation.** `trait MatchMode { id() -> ModeId; setup(&mut World, &MatchRecord);
step(&mut World, Tick) -> Option<MatchEnd>; score(&World) -> BTreeMap<TeamId, Score> }` with
`MatchParams { length, commit_at, extraction_opens }` in ticks per mode (Phase 1: 9600, 400,
7800). Scoring reads truth inside the sim and emits numbers only.

**Reason.** Survey mode scores map accuracy against truth, so `score(&World)` is right for all
four modes; `step` owns the window so the tick loop does not know which mode it runs.

**Evidence.** `spikes/ARCHITECTURE-RECONCILIATION.md` §14; `sim.py:162–186`.

**If wrong.** A mode needing per-agent hooks adds a method.

Designer: [ ] yes [ ] no

### 32. `WorldView`

**Recommendation.** `WorldView { tick, cave: &Cave, presences: &[Presence { agent, pos,
chassis, acoustic: Option<..>, optical: Option<..> }], acoustics: &AcousticField, me:
&AncientPlacement }`. No beacons, beliefs, deposits or other ancients' state **[guess: the
field list; Phase 1's ancient read nothing]**.

**Reason.** Ancients are truth-side and may read truth; narrowing is for auditability and
for keeping the borrow small. Everything a "signature before lethal, provocable by a loud
ping" system needs is there.

**Evidence.** `spikes/ARCHITECTURE-RECONCILIATION.md` §15.

**If wrong.** A field is one line; `&World` makes ancients a second unaudited reader.

Designer: [ ] yes [ ] no

### 33. `yields()`, `BlockId`, discoveries placed by depth, and risk R9

**Recommendation.** `enum BlockId { Predicate(PredicateId), Action(ActionId) }`;
`AncientSystem::yields(&AncientState) -> Option<Yield { block, dwell }>`; a completed
`Request::Interface` dwell adds the block to `AgentTruth.inventory.blocks`, which reaches
Belief through the next `SelfReport`. `blindside-gen` places `Discovery { block, pos, depth }`
by path-length bands from a content `DepthLootTable`, reusing the acoustic Dijkstra for depth.
R9: an empty emitter list for a whole match is a legal state the harness reports, never tunes
away.

**Reason.** DESIGN-PRINCIPLES §2: the cool things are new blocks, found by depth; the seam
needs an id type for "a block" before anything refers to one, and a block is already a
predicate or an action with a stable id.

**Evidence.** `spikes/ARCHITECTURE-RECONCILIATION.md` §16, §21: the aggressive rival's
80 s interface dwell at the machinery killed it 4/8 (sonar); "there is no cargo return for a
download in Phase 1, only the time spent".

**If wrong.** If yields become subtrees or modules, `BlockId` grows an arm; the
placement-by-depth seam is unchanged.

Designer: [ ] yes [ ] no

### 34. RNG purpose space

**Recommendation.** `Purpose { sensor: SensorId, kind: u8, index: u16 }` packed to u32;
`unit(tick, entity, p) -> [0,1)`, `normal(tick, entity, p)` (Irwin–Hall over 12 uniforms
**[guess]**), `sign(entity, p)` tick-free for the per-agent drift lean. `&self` everywhere;
no RNG field on `World`.

**Reason.** Stateless by construction means the phased order (§36) cannot change a noise
value. Every Phase 1 noise model is Gaussian and the tunings were measured against that.

**Evidence.** `spikes/ARCHITECTURE-RECONCILIATION.md` §18: Phase 1 used stateful streams
whose call order changes results; draw counts per event are 126 per ping, 180 per sweep.

**If wrong.** A different normal approximation changes the tails slightly; nothing
structural. DETERMINISM rule 4's example signature is updated.

Designer: [ ] yes [ ] no

### 35. Trig from `cordic =0.1.5` over `fixed =1.31.0`, behind one `fxmath.rs`

**Recommendation.** Pin both; `fxmath.rs` is the only file that names either; golden tables
on three platforms (BLD-67). If BLD-109's profile puts trig on the critical path, replace the
bodies with a 4,096-entry LUT in that file and bump the content hash. The Phase 0 lint's
dependency allow-list gains `cordic`.

**Reason.** A pure-integer crate with a one-crate dependency tree is auditable by reading it;
wrapping it makes the LUT swap invisible to callers.

**Evidence.** `spikes/ARCHITECTURE-RECONCILIATION.md` §19: every `f64` in `cordic`'s source
is under `#[cfg(test)]`; max abs error atan2 6.9e-10, sin/cos 1.6e-9, sqrt 2.1e-10; 679 ns
per (atan2 + sin + cos), so a ping tick is ~120 µs of trig against the 62.5 µs single-core
budget — amortised 7–14 µs per agent-tick **[guess: call counts estimated, not measured in Rust]**.

**If wrong.** Vendor the 300 lines, or the LUT path is a day.

Designer: [ ] yes [ ] no

### 36. Per-tick order is phased over all agents, not interleaved per agent

**Recommendation.** 1 deliver commands `(tick, team, seq)`; 2 `PolicyRunner::evaluate` for
every agent by id; 3 actuators apply, requests take effect; 4 world: ancients, hazards,
wrecks, emitter expiry, mode step; 5 sensors sample every agent against the one `&World`;
6 belief updaters fuse; 7 state hash. DRIVER §3.2's per-agent order ("as Phase 1 had it")
changes to this.

**Reason.** In phase 5 the world is borrowed immutably once and no agent sees a half-updated
tick; Phase 1's interleaving meant the lower id always sampled stale rivals.

**Evidence.** `spikes/ARCHITECTURE-RECONCILIATION.md` §20 (`sim.py:96–133`).

**If wrong.** A subsystem needing interleaving moves into phase 3; the hash position is fixed
either way.

Designer: [ ] yes [ ] no

### 37. The acoustic field is an exact range-bounded cell Dijkstra, resumed lazily and cached per emission; budget 10 µs per tick

**Recommendation.** Model "A-lazy": integer costs in 1/1024-cell units, flooded cells ×563/1024,
heap ordered by `(cost, cell id)`, resumed to the farthest listener that asks, cached for the
emission's life, Euclidean prefilter. Not the precomputed passage graph. Budget: 10 µs per
tick mean (100 ms per 9,600-tick match, 16% of the single-core tick), 2 ms worst tick, 8 MB,
0.1 ms per collapse. Emitters are hashed state in a `BTreeMap` keyed by a record-assigned
emission id; fields, heaps and touched lists are derived and excluded (BLD-81).

**Reason.** It computes what Phase 1 computed and what the spectator gate was watched on;
no precomputed structure, so collapses, echoes and absorption are each one line in the same
loop; cold and warm caches answer identically by construction; and it fits the budget at the
agent count Phase 3 implies (one per team).

**Evidence.** `spikes/ACOUSTIC-BUDGET.md` §4–§6: on a 400×240 passage cave with four agents,
9.5 µs per tick mean, 91 ms per match, 1.2 ms worst tick; with eight agents 26.6 µs (fits only
under the 8-wide parallel batch). ~48 ns per cell reached; a 170-cell ping costs 320–360 µs
regardless of cave size. The graph model is 0.1–0.3 µs per tick but hears 10–20% fewer
audible pairs (path 4–12 cells longer, hard cut-off), its bearings differ by 25° mean / ~60°
p90 — larger than Phase 1's whole 4–22° noise model — and a collapse costs a 6 ms (400×240)
to 28 ms (800×480) graph rebuild versus 0.02 ms. Python Phase 1: 12.9 ms per field, ~70×.

**If wrong.** If the cave is open-field or eight agents run on one core, acoustics is
25–90 µs per tick and the gate misses by up to 2×; the fallback is model B (prototyped,
~700 lines) at the fidelity cost above, about BLD-79's size to port. Too tight a budget fails
BLD-81 on a legitimate model; too loose and BLD-109 finds acoustics ate terrain matching.

Designer (model A-lazy): [ ] yes [ ] no
Designer (budget 10 µs mean / 2 ms worst / 8 MB / 0.1 ms per collapse): [ ] yes [ ] no

### 38. The benchmark cave is 400×240, passage-shaped, four agents; the generator is CA chambers joined by carved passages

**Recommendation.** BLD-72 and BLD-108's target: 400×240 cells, ~17% free, chambers of
radius 5–12 joined by passages, four agents (one per team), with the four width classes of
§25 in the biome's proportions. BLD-72 is written as "cellular-automata chambers joined by
carved passages", not "cellular automata with connectivity repair"; ROADMAP's "cellular
automata caves" reads the same way.

**Reason.** Four teams with rough parity of worth per region reads as one Phase-1-sized region
per team. The CA step alone cannot produce a passage cave.

**Evidence.** `spikes/ACOUSTIC-BUDGET.md` §2.4, §2.5, R5, Q8: DESIGN's demo fill (0.45–0.47)
gives an open field 52–61% free; fill 0.52 collapses the largest component to a few thousand
cells (0.50 → 29.7% / 12.2% free; 0.52 → 5.0% / 3.9%; 0.54 → 0.9%) — a percolation cliff
with no fill giving Phase 1's 16% free and 4–6-wide passages. The open field costs 3–4× the
passage cave acoustically. The size is a **[guess]**; 200×120 and 800×480 were measured so
a different answer is readable without re-running.

**If wrong.** Larger is cheaper acoustically (agents spread out) and linear in memory; more
open, see §37's fallback. Without the carving wording someone spends BLD-72's four days on
the fill parameter.

Designer (400×240, passage-shaped, four agents): [ ] yes [ ] no
Designer (BLD-72 is chambers plus carved passages): [ ] yes [ ] no

### 39. The arrival bearing keeps Phase 1's definition, and BLD-79's fixture criterion names it

**Recommendation.** Bearing = direction of the shortest path five cells back from the
listener (Phase 1's), accepting a ±20–40° swing with the listener's lateral position in
passages wider than ~3 cells and at bends. BLD-79's "on an L-shaped fixture the bearing
points down the passage" is rewritten to name this definition and a tolerance, because as
written it fails on a 5-wide L.

**Reason.** It is what the spectator gate was watched on, with 4–22° of noise on top;
neither definition is physically privileged.

**Evidence.** `spikes/ACOUSTIC-BUDGET.md` §4.4: on an 80×60 fixture the same source heard
from the same passage 40 cells down the leg gets bearing 0°, −22° or −39° depending on which
side of the passage the listener stands; identical to the passage-axis bearing on a straight
passage with the source on the axis.

**If wrong (no).** BLD-79 adds a skeleton-derived passage-axis bearing as a direction-only
side structure (8 bytes per cell, 6 ms per cave, staleness-tolerant after a collapse) and the
fixture becomes its acceptance test.

Designer: [ ] yes [ ] no

### 40. Content is TOML with every `Fx` as a decimal string or integer; `MatchRecord` stays JSON

**Recommendation.** One file per kind under `content/` plus `retired.toml` and `pack.toml`.
`range = "30"`, `bias = "0.055"`, `capacity = 1`; the loader parses strings with `fixed`'s
`FromStr` and rejects TOML floats. Records are machine-written JSON (Phase 0's choice).

**Reason.** Content is written by a person and carries its "Measured:" notes (tuning.py is one
long argument for that); TOML has comments, JSON does not. The string path is the only way
"no float enters through data" is a type check rather than a review.

**Evidence.** `spikes/SENSORS-AND-IDS.md` §4.1: `I32F32::from_str` is a pure-integer path
(its `f64` uses are all under `#[cfg(test)]`); the string and `from_num(f64)` paths give
identical bits for eight Phase 1 constants; `range = 30.0` fails to load; a 300-entry pack
parses in 1.9 ms.

**If wrong.** Switching format later costs a day and changes no hash (§3 hashes entries, not
bytes).

Designer (TOML, `Fx` as strings): [ ] yes [ ] no
Designer (`MatchRecord` stays JSON): [ ] yes [ ] no

### 41. `blindside-content` joins the constrained set; the TOML parser is a separate `blindside-content-loader` crate

**Recommendation.** The typed crate (registries, `Fx` fields, `content_hash`, validation;
dependencies `fixed`, `blake3`) is lint-constrained; the loader (`serde`, `toml`) is
unconstrained and used by harness, net and client, never by sim, vm or gen. ARCHITECTURE's
crate list gains the tenth crate; DETERMINISM's scope line gains `blindside-content`.

**Reason.** Floats can only enter through data and data enters through this crate; the
lint's own doc says the allow-list "does not close the hole". Keeping `toml` (which contains
`f64`) out of the constrained tree keeps "auditable by reading one dependency tree" literally
true.

**Evidence.** `spikes/SENSORS-AND-IDS.md` D20; BLD-20's lint-scope question.

**If wrong.** One crate with `toml` allow-listed works (proved) and relies on §40's
deserialiser; the cost is a parser with a float type inside the audited tree.

Designer: [ ] yes (constrained + loader crate) [ ] no (one crate, `toml` allow-listed)

---

## Part D — Data: changes the content hash and nothing else

### 42. Acoustic tunables

**Recommendation.** Motion-noise fields reused for 20 ticks, not 10 (−20% cost; source
displacement ≤1.4 cells, a 2° bearing shift against a 4° noise floor). Ping range stays 170
cells, so a ping reaches ~40% of a 400×240 cave, not the whole basin (DESIGN's "every
listener in the basin" was literally true only on Phase 1's cave). BLD-80 echoes are budgeted
at one extra emission per ping. Binary heap, not the bucket queue (8–20% faster but pops
equal-cost cells in push order, contradicting BLD-79's `(cost, cell id)` criterion).

**Evidence.** `spikes/ACOUSTIC-BUDGET.md` §4.5: 8 → 4 agents −64%; reuse −20%; range 120
−17%; one echo per ping +53%. §3: 170 cells is basin-wide at 200×120.

**If wrong.** Each is one constant; the budget still holds at four agents without the reuse.

Designer (motion reuse 20 ticks): [ ] yes [ ] no
Designer (ping range 170, ~40% of the benchmark cave): [ ] yes [ ] no
Designer (one echo per ping): [ ] yes [ ] no
Designer (binary heap): [ ] yes [ ] no

### 43. Loadout validator rules, sonar/lidar exclusivity, and what a cargo bay holds

**Recommendation.** R1 exactly one chassis, in the active season; R2 slots, mass, power;
R3 bays ≤ `max_cargo_bays`; R4 a Swimmer with lidar and no sonar is rejected, lidar plus
sonar on a Swimmer is accepted; R5 sonar and lidar are alternatives on every other chassis
**[guess]** — SENSORS §2's flat "mutually exclusive" gains the Swimmer exception, which
BLD-85's wording ("lidar as its *only* active sensor") already implies; R6 beacon drop
interval ≫ acquisition range per chassis; R7 nothing Hauler-specific. **Bay capacity:**
`cargo_bay.capacity` is content, default one unit per bay **[guess]**, so the silhouette shows
capacity (GLOSSARY: silhouette is always honest); SENSORS §2's "capacity 2" per bay and
CHASSIS's "one unit per bay" are reconciled this way, and Phase 1's capacity 2 is a Surveyor
with two bays (§45). Deposit yield per visit (BLD-92) is not capped at 2.

**Evidence.** `spikes/CHASSIS-TIMING.md` D9, §3.11 (the Hauler's arithmetic: A-and-home at
0.7 cells/s plus four loads is 323 s, inside the 390 s window, for four units); `spikes/SENSORS-AND-IDS.md`
§2 module 5. A general "every enterable terrain has a working mapping sensor" rule was
considered and rejected: it would reject the passive-only Surveyor DESIGN allows.

**If wrong.** Data.

Designer (R1–R7 with the Swimmer exception): [ ] yes [ ] no
Designer (one unit per bay, capacity in content): [ ] yes [ ] no

### 44. When each chassis ships, the harness flag, and the proposed numbers

**Recommendation.** Scout and Hauler: Phase 6, one new story (proposed BLD-208) after BLD-167
and before BLD-176; Hauler slides to Phase 8 if Phase 6 runs long. Swimmer: Phase 9, season
one, "the water rose" (proposed BLD-209 on BLD-203). `harness run --allow-future-season`
bypasses R1 only, in the harness crate, so Phase 6 starts from a seed-to-outcome table.
Numbers for the records, all **[guess]** except Phase 1's: body 0.8 / 1.2 / 4.0 / 1.2 cells;
slots 3 / 6 / 8 / 5; bays 1 / 2 / 4 / 2; dry speed 1.4 / 1.1 / 0.7 / 0.4, flooded 0 / 0 / 0 / 1.0;
motion-noise path range 20 / 40 / 100 / 40-in-water; pressure limit 0.5 / 0.8 / 0.8 / 1.0 of
biome max depth. Cost about 3.25 d in Phase 3, 10.5 in Phase 6, 11.5 in Phase 9 (art ≈ 14 d
of it, guessed).

**Reason.** Their trades are relative to rivals and to the prep decision, which first exist in
Phase 6; the Swimmer's worth is a generator weight, which is a season's lever.

**Evidence.** `spikes/CHASSIS-TIMING.md` §2.3–§2.5, D10–D12: "audible across half the
cave" is a motion path range of 80–100 cells (36–89% of free cells) against the Surveyor's
40 (9–37%); the S→A→B→S route is 576 cells, unreachable in 480 s below ~1.5 cells/s; the
two-deposit arc is lost at every speed 0.7–1.7 (28/30) and a one-deposit raid extracts at
every speed (17/18), so a Hauler's reason to exist is bays, not deposits; the spoof lands at
141 s (1.1) vs 176 (0.9) vs 203–206 (0.7/1.4/1.7), so BLD-108's beat sheet is per chassis;
water carries further, so a submerged agent is louder, not hidden.

**If wrong.** Too early: ~8 d of art a Phase 6 playtest might change; too late: a shipped
prep phase with no chassis decision. The numbers are tuning for the enabling story.

Designer (Scout Phase 6): [ ] yes [ ] no
Designer (Hauler Phase 6, fallback Phase 8): [ ] yes [ ] no
Designer (Swimmer Phase 9 season one): [ ] yes [ ] no
Designer (harness flag): [ ] yes [ ] no
Designer (the numbers as the Phase 3 records' starting values): [ ] yes [ ] no

### 45. The Surveyor's stock loadout

**Recommendation [guess].** Six slots: `passive_array`, `sonar` or `lidar`, `beacon_rack`,
`terrain_nav`, and two `cargo_bay` (one unit each, §43) — Phase 1's capacity 2 reproduced,
and "what do I give up for a third bay" is the visible trade. Rack count 6, cloner count 2
**[guess]**.

**Evidence.** `spikes/SENSORS-AND-IDS.md` D9 (proposed one bay and one free slot; the change
follows from §43).

**If wrong.** Data in `chassis.toml`.

Designer: [ ] yes [ ] no

### 46. Plan consequences of the driver decision

**Recommendation.** Phase 3's MatchRecords are re-run under the Phase 4 VM in BLD-124 with
identical final hashes as the pass criterion; BLD-102 is re-costed at 3.5 d (+1.5) with the
offsets noted on BLD-117, BLD-123, BLD-125 and BLD-130; Phase 2's tree render also writes the
induced tree as a node list with block names so the Phase 3 harness can load it.

**Evidence.** `spikes/AGENT-DRIVER.md` §6, §8–§10, D9–D11.

**If wrong.** A mismatch is found late instead of on the first VM commit; 1.5 d; half a day
of reconstruction in BLD-136.

Designer (re-run under the VM, identical hashes): [ ] yes [ ] no
Designer (BLD-102 re-costed): [ ] yes [ ] no
Designer (Phase 2 dumps the node list): [ ] yes [ ] no

### 47. BLD-87's criterion "no honest beacon fix increases true position error" is restated

**Recommendation.** Replace with: no honest *truth-anchor* fix increases true error, and an
own-beacon fix leaves true error within fix noise of the error at that beacon's drop.

**Reason.** The criterion as written is unachievable by design; it is BLD-88's finding
("the beacon chain buys confidence, not accuracy") working as intended.

**Evidence.** Re-measured independently on 2026-09-07 over seeds 1–8 at `d19579b`: 100 of
153 honest own-beacon fixes (65%) increased true position error, median +0.32 cells, mean
+0.33, worst +7.50 — the same conclusion as the spike's, from a different fix classification,
and the magnitudes say the mechanism is sound and only the criterion is wrong. The spike's own
figure: `spikes/ARCHITECTURE-RECONCILIATION.md` design problem 1: 170 of 318 honest
own-beacon fixes (53%) increased true position error; post-fix error equals drop-time error
within 1.8–3.5 cells.

Designer: [ ] yes [ ] no

### 48. BLD-105's Recall criterion is re-based on BLD-101, not on `b43ba0b`

**Recommendation.** BLD-105's "at least one Recall timing extracts" is kept as the goal but
its evidence line changes: it cites `b43ba0b`, which predates the `31a4646` steering change,
and is false on the committed code. It becomes a criterion BLD-101 (map-aware steering, the
28 s give-up) must restore, and BLD-108's beat sheet is re-verified after BLD-101 lands.

**Reason.** The player sits at one true position for 150 s cycling wall-escape 1–4 because
`policy.py:364–365` resets the escape counter instead of abandoning the waypoint; the
believed shaft is behind solid rock from where it truly stands, so the spiral — the only
mechanism that undoes a spoof — never runs.

**Evidence, corrected 2026-09-07.** The spike's claim was "Recall never extracts at the
committed tuning", from 0 of 31 runs at timings from 3:00 onward (seed 7 at seven timings;
seeds 1–8 at 4:00, 5:30, 7:00), with `spikes/AGENT-DRIVER.md` §2.1 agreeing at 5:00. That is
right about the timings tested and wrong as a general claim: **Recall at 2:30 on seed 7 does
extract** — SEARCH is entered at 7:13, the report reads "widening the circle · 4 cells out",
the match extracts at 7:35. Re-run on 2026-09-07 at `d19579b`.

So the window exists and closes before 3:00 of an 8-minute match. That is the finding worth a
decision, and it cuts both ways: `tuning.py` says outright that "a recall sent late genuinely
cannot get home, and that is the decision", so a window is intended — but a window that shuts
a third of the way in makes Recall a stopwatch rather than a judgement, and the spectator
tension the Phase 1 gate is scored on lives in the second half of the match. The wall-escape
loop the spike found (`policy.py:364–365` resets the escape counter instead of abandoning the
waypoint) is what closes it early, and is a real bug independent of where the window should
end.

Designer: [ ] yes [ ] no

### 49. Six GLOSSARY entries these decisions make wrong

**Recommendation.** GLOSSARY is the designer's file and is the first thing CLAUDE.md tells a
reader to read, so the entries the sections above contradict are listed here rather than left
to be discovered. *Policy* — "compiled to VM bytecode": Phase 3's artifact is a flat tree and
bytecode is Phase 4 (§20). *Fix* — "collapses drift": an own-beacon fix collapses believed
uncertainty, not true error (§47, BLD-88). *Belief* — "occupancy map": a timestamped point set
with derived bins (§14). *Passive/active* — BLD-6's wording, plus the finding that a 170-cell
ping reaches ~40% of a 400×240 cave rather than "every listener in the basin" (§42). *Ancient
system* — gains a `yields()` seam (§33). *Module* — four sensors are chassis-intrinsic and
cost no slot (§6).

**Reason.** A glossary that contradicts the types is where the next reader's wrong model comes
from; the vocabulary is the one thing this project asks to be read first.

**Evidence.** The sections cited; no new measurement.

**If wrong.** Wording only: a no leaves the entries as they stand and the sections above are
unaffected.

Designer: [ ] yes [ ] no

---

### 50. `GaitId` has no home in the ID scheme

**Recommendation.** A gait is an index into the chassis record's own `gaits` list, not a ninth
permanent registry.

**Reason.** `MotorCmd { heading, speed, gait }` (§25) needs to name a gait, and §6's ID scheme
has exactly eight permanent kinds, none of them gait. Two ways out: a ninth registry under the
rule in §6, so gait 3 means the same thing on every chassis forever; or a per-chassis index, so
a Hauler's gait 1 and a Scout's gait 1 are different things and only the chassis record says
what either means. The per-chassis form is the smaller commitment and matches how the chassis
record already carries `gaits: [ { name, speed_factor, noise_factor } ]` (`spikes/CHASSIS-TIMING.md`
§3.3). The cost of being wrong: a saved policy that says "use gait 2" means something different
after a chassis rebalance, so the index must be part of what the content hash covers (§3).

**Lands on** BLD-100.

Designer: [ ] yes [ ] no

### 51. `Return::SelfReport` cannot have two shapes

**Recommendation.** One `SelfReport` variant carrying every field, with the depth gauge filling
`medium` and the self-report sensor filling the rest; a sensor that does not produce a field
leaves it at its previous value rather than the variant splitting.

**Reason.** `spikes/SENSORS-AND-IDS.md` gives SensorId 7 (depth gauge) the return
`SelfReport { medium }` and SensorId 11 `SelfReport { cargo, power, damage, modules }`, but §5
fixes the count at eight return shapes and §11 declares one five-field variant. Three ways out:
one variant with every field (recommended); a ninth return shape, which breaks §5's count; or
folding `medium` into SensorId 11 and deleting the depth gauge as a separate sensor, which
`spikes/CHASSIS-TIMING.md` D8 wants kept because a Swimmer needs to know it is submerged. This
is a hashed, serialised type, so it is a Phase 3 decision and not a Phase 4 one.

**Lands on** BLD-63, BLD-92.

Designer: [ ] yes [ ] no

### 52. The sonar's reach: "basin-wide" or 40% of the cave

**Recommendation.** Keep the 170-cell ping range and change the prose, not the number.

**Reason.** `spikes/SENSORS-AND-IDS.md` describes the sonar as "audible basin-wide for 3 s",
which is Phase 1's language and was true of Phase 1's 200×120 hand-authored cave. Measured on a
400×240 cave, a 170-cell ping reaches about 40% of it (`spikes/ACOUSTIC-BUDGET.md` §3;
reproduced independently on 2026-09-07). Restoring literal basin-wide audibility needs roughly
300 cells, which triples the acoustic cost per ping and removes the thing that makes pinging a
judgement — that a ping tells *some* of the basin where you are, not all of it. This section
and §42's ping-range line are the same decision; answer one.

**Lands on** BLD-79, BLD-84, and the GLOSSARY *Passive/active* entry in §49.

Designer: [ ] yes [ ] no

## What is not asked

Taken as given from ROADMAP, ARCHITECTURE, DETERMINISM, CLAUDE.md and DESIGN-PRINCIPLES,
and not revisited here:

- The invariant: a policy never observes ground truth; `World` is `pub(crate)`; the sensor
  layer is one audited module; a compile-fail test guards `PolicyRunner::evaluate` and
  `Predicate::eval`; the one deliberate relaxation is BLD-76's harness-only `ReplayFrame`.
- The crate layout and `blindside-sim` depending only on `blindside-vm` and
  `blindside-content` (plus the loader crate of §41 outside that tree).
- DETERMINISM's hard rules: no `f32`/`f64`, no `HashMap` iteration, no `std::time`, no
  `rand`, no threading inside a tick, stable-id iteration, `unsafe` with justification, the
  canary on three platforms, the content hash and schema version in every record.
- Registries keyed by stable id, defined in data, validated at build time; rules 1–5 on
  retirement, hashes, schema versions, Belief-only predicates and season flags.
- ARCHITECTURE's `BtNode` set (Sequence, Selector, Guard, Act, Subtree) and `VmBudget`;
  `Predicate::eval(&Belief, &[Fx]) -> bool`.
- The Phase 3 gate: 1,000 headless matches in under 10 minutes on a laptop, bit-identical
  across Linux, macOS and Windows; parallelism only across matches; the Surveyor only.
- Extraction is the core mode; the match is a raid; wrecks hold cargo and policy; blocks are
  a list and are found by depth (DESIGN-PRINCIPLES §1–2). Phase 2's three predicates and two
  actions are the day-one items.
- Hardware-readiness: sensor and actuator seams designed so a driver is a second
  implementation; nothing built for hardware.
- The eight world axes and their names (BLD-71 confirms the list with the designer
  separately); one biome ships; one ancient system; `provocable_by` empty until Phase 7.
- Spoofing deals no damage; no action in the registry damages another agent.
- Phase 1's tunings as the starting content values, each cited with its measurement, and
  sensor-noise fairness as an untested known-weak area (BLD-112).
- Which of §8's extra blocks players hold on day one versus find by depth or behind a season
  flag: deferred to BLD-112 and Phase 4 content, not decided here.
- Board estimates and the phase totals; velocity is the board's.

## Guesses

Every value or choice a spike author marked as a guess, consolidated; where two spikes
guessed different values, the one this file carries is named.

**Architecture reconciliation.** `BeliefMap` point cap 32,768 per agent. Relax weighted by
odometry distance rather than time. Three-sigma `PoseEstimate` instead of a covariance.
Irwin–Hall normal in the RNG. `WorldView` field list. `Ticks` for every duration, including
`Structural::time_to_failure`. Amortised trig load of 10–20 calls per agent per tick. (Its
`AgentId` layout `team * 16 + slot` in a u16 is superseded by §18's `AgentId(u32)`.)

**Agent driver.** Default budget 256 node visits; depth cap 64; params `[Fx; 4]` (from
ARCHITECTURE); exhaustion = stop; `noop` as an action rather than a node kind; the day
estimates (option B 6–8 d, option C 3.5 d, net −1 d over Phases 3 and 4); `hold` and `wait`
as separate actions (this file folds `wait` into `hold`).

**Sensors and ids.** Every slot / mass / power value; beacon rack count 6; cloner count 2;
the Surveyor stock loadout (amended in §45); `hold` as an action; `active_scan` as a name;
the transponder interrogator emits nothing; biome 1 "moderate on every axis"; `dry_clear` as
a biome entry rather than a fixture override; the reading of "six sensors"; the reserved
numbers 64+ (names from the board, numbers from the spike). Swimmer slots 4 — superseded by
CHASSIS's 5.

**Chassis timing.** Width class boundaries (crawl 2–3, narrow 3–4, passage 4–5, hall ≥5)
and the "body + 1" passing rule, measured on Phase 1's raster and unverified on a heightfield;
body diameters Scout 0.8, Hauler 4.0, Swimmer 1.2; turn class one above enter class for
Surveyor and Swimmer; Swimmer slots 5; max bays 1 / 2 / 4 / 2 with one unit per bay; speeds
1.4 / 0.7 / 0.4 dry and 1.0 flooded (1.1 and 1.4 are Phase 1's); motion-noise ranges 20 /
100 / 40-in-water (40 dry is Phase 1's); pressure limits 0.5 / 0.8 / 0.8 / 1.0; the Swimmer
walks at 0.4× rather than not at all; R5 (sonar and lidar are alternatives on non-Swimmers);
all art estimates; the Scout as the courier for machinery yields; that the flooding weight,
not a stat, makes the Swimmer worth picking (one cave); story keys BLD-208 and BLD-209.

**Acoustic budget.** Target cave 400×240 with four agents; agents never stop and random-walk
uniformly; the ancient signature audible 13 s of every 75 s, two ancients, four crashes per
match; flooding 12% of free cells in blobs of radius 6–14; CA fills 0.47 and 0.50 and the
tree generator's chamber density, radii, passage widths and 30% extra loops (Phase 1's or the
DESIGN demo's, scaled); Phase 1's sampling cadences carried into Phase 3; the Euclidean
prefilter applied to every emission kind (exact; changes cost only); a 4-cell collapse radius
that invalidates every live field; rock absorption as a per-cell cost multiplier.

**This file.** The shape of the foreign-beacon observable (§10); the `Intent.report` channel
for durable action facts (§21); SensorId 7 for the depth gauge (§5); `cargo_bay.capacity`
defaulting to one unit (§43); keeping Phase 0's `Tick(u64)` and `AgentId(u32)` (§18); the
Surveyor's stock loadout with two bays (§45); `SurfaceCharacter` as the name of the
rock/water character (§11, §24).
