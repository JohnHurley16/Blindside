# ARCHITECTURE reconciliation — BLD-61 question round

`ARCHITECTURE.md` was written before Phase 1 ran. Phase 1 is now evidence, and in a dozen
places the two disagree, or ARCHITECTURE names a thing it never defines. This document puts
each disagreement in front of the designer as one recommendation with a yes/no line.

It edits nothing. `ARCHITECTURE.md` is unchanged; the answers here get written into it by
BLD-112 (or sooner by the designer). No code in `blindside-sim` exists yet, and none is
proposed here.

**How to answer.** Each item ends with `Designer: [ ] yes [ ] no`. A yes means the Rust
signature shown is what Phase 3 builds. A no means say what instead, or say "ask again with
options". Items marked **guess** are places where Phase 1 gives no measurement and the
recommendation is judgment; they are still yes/no, but weigh them as opinions.

**What was measured, and how.** Every number below comes from running the committed Phase 1
code (`7fcbe87`) headless on this laptop, 8 seeds × 2 player sensors unless stated, with
read-only instrumentation (monkeypatched timers and counters, no changes to `phase1/`). The
scripts are in the session scratchpad, not the repo. The baseline command is
`python -m phase1 --headless --seed N [--player-sensor lidar] [--recall S]`.

---

## 0. The numbers this document leans on

| Quantity | Measured (8 seeds, sonar / lidar player) | Where it matters |
|---|---|---|
| Tick wall time, mean | 0.49–0.80 ms / 0.37–0.88 ms | §17 tick rate |
| Tick wall time, median | 0.27–0.37 ms / 0.20–0.33 ms | §17 |
| Tick wall time, p99 | 4.8–8.3 ms / 4.2–6.2 ms | §17 |
| Tick wall time, worst | 24.6–34.4 ms / 24.2–27.5 ms — every worst tick is a `SoundField` (Dijkstra) build | §17, BLD-64 |
| `SoundField` builds per match | 357–1006 / 219–1058; mean 4.3–5.8 ms each, worst 12.9–23.4 ms | §17, BLD-64 |
| Returns per agent per tick, max | 63–67 / 91–96 (mean 1.7–2.1 / 4.0–4.2) | §2 return container |
| Map points per agent at match end | player 4.9k–6.7k / 27.1k–29.3k; rival (sonar) 2.9k–9.5k | §6 map |
| Points placed while the agent was stationary | 5–16 % / 5–18 % of all points | §6 relax weighting |
| Relaxations (fixes that move the map) per match | 13–38 / 15–56; max points moved per relax 1.8k–3.8k / 5.0k–9.8k | §6 |
| Honest own-beacon fixes per match | 5–26 / 6–47 | §5, §8 |
| Honest own-beacon fixes that **increased** true position error | 66 of 121 (sonar), 104 of 197 (lidar): **53 %** | §8, BLD-87 criterion |
| True error after an honest own-beacon fix minus true error at that beacon's drop | mean 1.8–3.5 cells | §8: the chain re-anchors to past belief |
| Spoofed fix: jump / surprise | 33.6–35.8 cells / 11.0–12.0 σ on every seed | §4, §5 |
| Largest honest fix surprise | 3.4–13.8 σ | §5 predicate candidate |
| Heading error at match end (uncorrected, `HEADING_FIX_GAIN = 0`) | player −33° to −50°; rival +27° to +63° | §5 TRN home |
| Beacons dropped per agent / in World | 5–11 / 14–21 | §10 collections |
| New contacts logged per agent per match | 10–86 | §9 |
| Player extracted with cargo, no Recall | 0 of 16 | context |
| Player extracted after Recall sent at 4:00, 5:30 or 7:00, seeds 1–8, sonar | **0 of 24**; the believed shaft is never reached, so the spiral search never starts | Design problems, item 2 |
| `cordic 0.1.5` over `fixed::I32F32` (scratch Cargo project, release) | max abs error: atan2 6.9e-10, sin/cos 1.6e-9, sqrt 2.1e-10; **679 ns per (atan2 + sin + cos)** | §19 trig |
| `1/20` in I32F32 | `0x0CCCCCCC` = 0.0499999998; `20 × that` = 0.9999999963 | §17 ticks not seconds |

The Phase 1 board figure "0.36 ms mean / 33 ms worst" is reproduced within the spread above.

---

## 1. `Sensor::sample` takes `&World`

**ARCHITECTURE says**

```rust
fn sample(&self, w: &World, a: &AgentTruth, rng: &DeterministicRng)
    -> SmallVec<[Return; 8]>;
```

and, under Hardware-readiness: "no sensor implementation should assume it can query
arbitrary world state; it should express what it needs as a request the sim happens to
answer from `World` and hardware would answer from a driver."

These contradict each other. A `&World` parameter is exactly the arbitrary query.

**Phase 1 evidence.** `phase1/sensing/sensor_rig.py:50` has the same shape,
`def sample(self, world: World, me: AgentTruth, cmd: MotorCommand, t: float)`, and the
per-sensor methods show what a sensor actually needs from the world. The complete list,
from reading every method in that file:

| Sensor | What it reads (file:line) | As a request |
|---|---|---|
| odometry | `me.last_true_delta` (:78) plus per-agent bias signs | `own_true_delta()` |
| sonar | ray march from true pose against `~cave.FREE` (:87–:98) | `raycast(pose, angle, max_range, Blocks::Sound)` |
| lidar | ray march against `~cave.WALKABLE`; `cave.is_walkable(me.x, me.y)` (:108–:131) | `raycast(…, Blocks::Light)`, `medium_at(pose)` |
| near-field | ray march against `~cave.WALKABLE`, 2.5 cells (:140–:151) | `raycast(…, Blocks::Body)` |
| passive | **iterates every other agent** (`for other in world.agents.values()`, :166) reading `audible_until`, `last_true_delta`, `x`, `y`; the ancient's `signature_strength(t)`; `world.pending_sounds` | `arrivals_at(pose)` — the acoustic field's job |
| beacons | **iterates every beacon** (`for bid, beacon in world.beacons.items()`, :218) filtering by owner and range | `transponders_in_range(pose)` — every team's, see the note below |
| cargo | `me.cargo` after a load (:68) | `self_report()` |

Two of the seven walk whole World collections. That is the leak the hardware section is
about: a driver cannot iterate "all agents".

**Recommendation.**

```rust
// blindside-sim/src/sensing/mod.rs — the audited crossing. Only this module names both
// World and Belief. Sensor impls live in sensing/*.rs and see SensorEnv only.

pub struct SensorCtx { pub tick: Tick, pub agent: AgentId, pub sensor: SensorId }

pub trait SensorEnv {
    fn own_true_delta(&self) -> MotionDelta;                    // odometry only
    fn own_pose(&self) -> Pose;                                 // true pose, for raycasts
    fn own_state(&self) -> SelfState;                           // cargo, power, damage
    fn medium_at(&self, pos: Vec2Fx) -> Medium;                 // Dry | Submerged (§4); rock is raycast's answer
    fn raycast(&self, from: Pose, angle: Fx, max_range: Fx, blocks: Blocks) -> Option<Fx>;
    fn arrivals_at(&self, pos: Vec2Fx, out: &mut Vec<Arrival>); // acoustic field, by path
    fn transponders_in_range(&self, pos: Vec2Fx, out: &mut Vec<TransponderHit>);  // every team's
    fn terrain_patch(&self, pos: Vec2Fx, radius: Fx) -> OccupancyPatch;  // optical
    fn structural_warning_at(&self, pos: Vec2Fx) -> Option<Ticks>;       // monitor
}

pub trait Sensor {
    fn id(&self) -> SensorId;
    fn cost(&self) -> SlotCost;
    fn emits(&self) -> Emission;                                // see §3
    fn sample(&self, env: &dyn SensorEnv, ctx: &SensorCtx, fired: bool,
              rng: &DeterministicRng, out: &mut Vec<Return>);
}
```

`SensorEnv` is implemented once, inside `sensing/mod.rs`, over `(&World, AgentId)`. Sensor
impls compile against the trait and cannot name `World` (BLD-74's test). `fired` is
whether the policy asked this sensor to emit this tick (Phase 1's `cmd.ping`); active
sensors return nothing when it is false.

Reconciled 2026-09-06: `transponders_in_range` lost its `owner` filter and returns every
team's beacons in range. Belief resolves own-team ids into fixes and records foreign ids in
`Belief.foreign_beacons` (§8) with no fix; without that, BLD-106's arming rule has no
observable anywhere in the sim. See PHASE-3-OPEN-QUESTIONS.md §10.

Reconciled 2026-09-07: `medium_at`'s comment read `Dry | Flooded | Rock`; `Medium` is
`Dry | Submerged` (CHASSIS D8.2), the medium a *body* is in, and it is what `SelfReport`
carries. Whether a cell is rock is `raycast`'s answer through `Blocks`, not this one's. See
PHASE-3-OPEN-QUESTIONS.md §24.

**Reason.** The seven Phase 1 sensors need nine requests between them, all of which are
things a robot's drivers answer (encoders, a rangefinder, a hydrophone array, a transponder
interrogator, a camera, a strain gauge). Nothing needs the list of agents. Putting the trait
in the signature is the difference between a rule in a document and a rule the compiler
holds.

**If wrong.** If some Phase 3 sensor needs a request not on this list, add a method: the
list is the contract, not the trait shape. The cost of a missing method is one line; the
cost of `&World` is that BLD-74, BLD-75 and BLD-111 have nothing to test.

Designer: [ ] yes [ ] no

---

## 2. The return container `SmallVec<[Return; 8]>`

**ARCHITECTURE says** `-> SmallVec<[Return; 8]>`.

**Phase 1 evidence.** Measured returns handed to `Belief.fuse` per agent per tick: sonar
player max 63–67 (60 rays + 2 false + odometry + near-field + passive), lidar player max
91–96 (90 rays + the rest), p99 for the lidar player 80–87. Mean 1.7–4.2. An inline
capacity of 8 spills to the heap on every ping and every sweep.

**Recommendation.** The `out: &mut Vec<Return>` parameter in §1: one `Vec` per agent, owned
by the sensing module, cleared each tick, never reallocated after the first sweep.

**Reason.** The worst case is 12× the inline size. A per-agent scratch vector costs one
allocation per match and makes the sample count visible to the caller for free.

**If wrong.** Nothing breaks either way; this is a performance and honesty point. If a
hardware backend wants ownership semantics it can wrap the same call.

Designer: [ ] yes [ ] no

---

## 3. `emits()` is `Option<AcousticSignature>`

**ARCHITECTURE says** `fn emits(&self) -> Option<AcousticSignature>;   // Some => you are audible`.

**Phase 1 evidence.** Sonar sets `me.audible_until = t + T.SONAR_AUDIBLE_S`
(`sensor_rig.py:60`); lidar sets nothing ("Light, not sound: nothing in the basin hears
this", :55–:57); the design decision in `PHASE-1-OPEN-QUESTIONS.md` Part 4 is that a lidar
sweep "is a visible light in a dark cave, so it is a tell to anyone with *line of sight* —
local exposure, not basin-wide." Board: BLD-74 and BLD-85 already carry the panel's typed
channel.

**Recommendation.**

```rust
pub enum Emission {
    None,
    Acoustic { signature: AcousticSignature, audible_for: Ticks },   // sonar: 60 ticks
    Optical  { light: LightSignature },                             // lidar, camera lamp
}
```

`Sensor::emits()` is the static property (for the loadout screen, content validation such
as "a Swimmer cannot carry lidar as its only active sensor", and the silhouette rule). The
sensing module registers the emitter on `World` when `sample` runs with `fired == true`:
an acoustic emission goes to `World.acoustics` as `(agent, signature, until_tick)`; an
optical one to a line-of-sight emitter list consumed by BLD-95.

**Reason.** Sonar and lidar differ in *who can notice*, not in loudness. A second channel
is one enum arm; encoding it as `None` would make lidar a silent sonar, which the Part 4
decision says it is not.

**If wrong.** If the designer later wants a third channel (electromagnetic, for the
magnetometer to be spoofable) it is a third arm. If the optical tell is dropped, the arm is
unused and nothing else changes.

Designer: [ ] yes [ ] no

---

## 4. `Return` has no odometry variant, and `Fix` is an absolute position

**ARCHITECTURE says**

```rust
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
```

There is no way for drift to enter Belief through this enum: `BeliefUpdater::integrate_motion`
takes the *command*, so dead reckoning would integrate what the policy asked for, not what
the wheels did. And an absolute `Fix { position }` cannot lie through belief: a relocated
beacon can only lie if the return is *relative to a beacon the agent has its own record of*.

**Phase 1 evidence.** `phase1/sensing/returns/odometry.py:8–16`:

> "Forward distance and heading change since the last tick. Already corrupted by scale bias,
> heading bias and noise. The agent has no other source of motion, so this error is not
> recoverable — it is integrated straight into the pose estimate and becomes drift."

`phase1/sensing/returns/beacon_fix.py:8–18`:

> "Range and bearing to a transponder that answered to `beacon_id`. Belief turns this into a
> position by combining it with the position it recorded for that id. Nothing in this type
> distinguishes a beacon that has been moved from one that has not, and nothing downstream
> can. That is the whole mechanism of spoofing."

and the resolution in `phase1/belief/belief.py:165–173`:

```python
known = self.beacons.get(r.beacon_id)
if known is None:
    return                                   # a beacon we never recorded is not trusted
...
est_x = known.x - math.cos(self.theta + r.bearing_body) * r.range
```

Measured: the spoof produces a 33.6–35.8 cell jump at 11–12 σ on all 16 runs through that
one function; honest fixes through the same function never exceed 13.8 σ. Phase 1 also
needed a self-report return (`cargo.py`: "This is how an agent discovers that it spent
thirty seconds loading at a place where there was no deposit: the number did not change").

**Recommendation.**

```rust
pub enum Return {
    Odometry     { forward: Fx, turn: Fx },                              // already corrupted
    RangeBearing { range: Fx, angle: Fx, quality: Fx, source: SensorId,
                   character: SurfaceCharacter },                        // sonar, lidar, near-field, false
    Bearing      { angle: Fx, quality: Fx, character: SoundCharacter },  // passive; never a range
    Transponder  { beacon: BeaconId, range: Fx, angle: Fx },             // relative; Belief resolves it
    Anomaly      { rough_direction: Fx, strength: Fx },
    Optical      { patch: OccupancyPatch },
    Structural   { time_to_failure: Option<Ticks> },
    SelfReport   { cargo: u8, power: Fx, damage: Fx, modules: ModuleHealth, medium: Medium }, // Dry | Submerged
}
pub enum SoundCharacter   { Ping, Tone, Signature, Crash } // a property of the signal, not an identity
pub enum SurfaceCharacter { Rock, Water }                  // a property of the echo, not an identification
```

`Fix` leaves `Return`. A fix is something Belief *does* with a `Transponder` return (or a
terrain match, §5), recorded on the Belief side as a `FixRecord` (§8). `FixSource` moves
there too: `enum FixSource { Beacon(BeaconId), Terrain }`.

**Reason.** Drift must be born in the sensor layer from the true achieved motion
(`agent_truth.py:16`: "The sensor layer corrupts it into odometry; the difference between
the two is drift, and it is the only place drift is born") — that needs a variant. The
spoof must run through the identical code path as an honest fix — that needs the return to
be relative to a recorded beacon. `source: SensorId` on `RangeBearing` is what lets the map
draw a near-field floor point differently from a sonar wall point (`point_source.py:3`:
"FALSE is carried through into Belief and rendered exactly like SONAR, differing only in
confidence"); a false return carries the sensor id of the sensor that hallucinated it.

**If wrong.** If `Fix { position }` stays, the shaft beacon still works (its recorded
position is true) but spoofing has to be special-cased somewhere, and that special case is
the lie marker the comment says must not exist.

Reconciled 2026-09-06: `RangeBearing` gains `character: SurfaceCharacter { Rock, Water }` and
`SelfReport` gains `medium`, both of which CHASSIS D8.2/D8.3 need in Phase 3 and neither of
which can be added later without a schema migration under a live season: the water surface
lidar returns as a wall is a door on a Swimmer's map. Like `SoundCharacter` it is a property
of the signal, never an identification. See PHASE-3-OPEN-QUESTIONS.md §11 and §24.

Reconciled 2026-09-07: the fix source arm was `Transponder(BeaconId)`; it keeps
ARCHITECTURE's own name, `Beacon(BeaconId)` — only the *return* is renamed `Transponder`.
`SelfReport.medium` is `Medium { Dry, Submerged }` (CHASSIS D8.2), which is also what §1's
`medium_at` answers. See PHASE-3-OPEN-QUESTIONS.md §11 and §24.

Designer: [ ] yes [ ] no

---

## 5. Terrain-relative navigation has no home; a beacon fix must not touch heading

**ARCHITECTURE says** `Fix { position, source }   // beacon or terrain match` and the
board (BLD-61 done-when, BLD-90) asks: "Sensor::sample takes no &Belief, so TRN is either a
Sensor variant with a Belief-reading request or a BeliefUpdater-side request path".

**Phase 1 evidence.** `tuning.py:49–62`, `HEADING_FIX_GAIN = 0.0`:

> "The heading correction here was invented: it guessed rotation error by comparing the
> direction travelled since the last fix against the direction to the fixed position …
> Measured over a match, half of all honest loop closures left the agent MORE wrong than
> before they happened. At 0.0 none of them do. Heading drift is now uncorrected for the
> whole match, which is the honest consequence: the map fans open and nothing straightens
> it. DESIGN says the thing that recovers heading is terrain-relative matching against
> ground already surveyed, and that is a Phase 3 sensor, not something a lone beacon can do."

Re-measured tonight: heading error at 8:00 is −33° to −50° (player) and +27° to +63°
(rival) on every seed, and the spoof turns a 34-cell position lie into a 90-cell one by
6:30 on seed 7 because the heading is wrong too (`--headless` timeline, 6:30.0 line:
`pos err 89.9 hdg err -38.6`).

**Recommendation.** TRN is not a `Sensor`. It is a stage of the `BeliefUpdater` that is
enabled by a module in the loadout:

```rust
pub trait BeliefUpdater {
    fn integrate(&mut self, b: &mut Belief, r: &Return);              // Odometry only
    fn fuse(&mut self, b: &mut Belief, returns: &[Return], tick: Tick);
}
// Inside fuse, in this order, each a private fn of the belief module:
//   integrate odometry -> place RangeBearing points -> resolve Transponder returns into
//   position-only fixes -> terrain match (if the TRN module is fitted): scan-match this
//   tick's RangeBearing points against Belief.map over a small pose window, producing a
//   fix with a heading component -> contacts.
pub struct TerrainMatch { pub dpos: Vec2Fx, pub dtheta: Fx, pub overlap: Fx }   // internal to belief.rs
```

A transponder fix changes heading by exactly zero. A terrain fix may change heading, bounded
by a content window. Both are recorded as `FixRecord { source: Beacon(id) | Terrain }`.

Reconciled 2026-09-07: the arm was written `Transponder(id)` here and in §4; the return is
renamed `Transponder`, the *fix source* keeps ARCHITECTURE's `Beacon(BeaconId)`. See
PHASE-3-OPEN-QUESTIONS.md §11.

**Reason.** TRN needs three things: this tick's range returns, the agent's own map, and the
pose estimate. All three are already in Belief; none is in World. A real robot's scan
matcher runs on the robot over its own map, which is the belief side. So it never needed
`&World` or a Belief-reading request on the sensor trait; the question dissolves once TRN
is placed where its inputs are. `integrate_motion(cmd)` in ARCHITECTURE goes: Belief
integrates the odometry *return*, never the command (`belief.py:123–132`).

**If wrong.** If TRN needs something not in Belief (a denser scan than the fitted sensor
supplies), the fix is a higher-rate `RangeBearing` sensor, still through `SensorEnv`. The
trait above does not change. BLD-90 waits on this line and BLD-87's "a beacon fix changes
the heading estimate by exactly zero" is the test.

Designer: [ ] yes [ ] no

---

## 6. `Belief.map: OccupancyMap` cannot be relaxed by a fix

**ARCHITECTURE says** `pub map: OccupancyMap, // only what it has sensed` and, under
Client: "drift renders as visible smearing and a fix snaps it into alignment."

An occupancy grid is a set of cells. A cell has no timestamp and no source, so nothing can
say *which* cells were placed since the last fix or how far into the drift interval; a fix
can correct the pose and stop the smear but cannot move the ghost corridor back. That is
the "naive implementation" `PHASE-1-OPEN-QUESTIONS.md` §1 warned about.

**Phase 1 evidence.** `phase1/belief/pose_correction.py:1–22`:

> "A fix corrects the pose estimate *now*. Points already placed do not move on their own,
> so the naive implementation leaves the ghost corridor sitting there forever and the only
> thing that 'snaps' is the agent marker … So instead: every point carries the time it was
> placed, and a fix applies its correction to everything placed since the previous fix,
> weighted by how far into the drift interval each point was … That is one loop closure of
> a pose graph, done by hand. A spoofed fix runs exactly this same code and drags the recent
> map somewhere wrong, tearing it away from the older map."

`point_cloud.py:70–85` is the relax (`mask = self.t[:n] > correction.epoch_t`) and
`:91–100` rebuilds the coarse occupancy bins afterwards ("After a fix moves the points, the
bins they sat in are stale"). The bins are what steering reads (`clearance`, `:108`;
BLD-101). Measured: 13–56 relaxes per match, each moving up to 3.8k (sonar) or 9.8k (lidar)
points, 12–42 % of the cloud on average, in ≤ 0.71 ms of numpy. Map size at match end:
5–7k points per sonar agent, 27–29k per lidar agent; `MAX_POINTS = 250_000` was never
approached.

**Recommendation.**

```rust
pub struct MapPoint {
    pub pos: Vec2Fx,          // belief frame; moved by relax
    pub placed: Tick,         // for age and display
    pub odo: Fx,              // odometry integral at placement; the relax weight (see below)
    pub source: SensorId,     // sonar | lidar | near-field | ... (a false return carries its sensor's id)
    pub character: SurfaceCharacter,  // Rock | Water (§4); one agent's wall is another's door
    pub confidence: Fx,
}
pub struct BeliefMap {
    pub points: Vec<MapPoint>,          // capped by content (guess: 32_768 per agent)
    bins: OccupancyBins,                // derived: 2-cell bins over the belief extent, rebuilt after relax
}
impl BeliefMap {
    pub fn relax(&mut self, c: &PoseCorrection);                                  // rotate about epoch, translate, weighted
    pub fn blocked(&self, pos: Vec2Fx, viability: &TerrainViability) -> bool;     // viability from Belief.loadout
    pub fn clearance(&self, from: Vec2Fx, heading: Fx, max_range: Fx,
                     viability: &TerrainViability) -> Fx;                         // what steering reads
}
pub struct PoseCorrection { pub epoch_odo: Fx, pub span_odo: Fx, pub origin: Vec2Fx, pub dtheta: Fx, pub dpos: Vec2Fx }
```

`bins` are derived and excluded from the state hash; `points` are hashed (policies read the
map through `clearance`).

**Guess inside this item, separately answerable:** weight the relax by *odometry distance
since the epoch* (`odo`), not by seconds. Phase 1 weights by time
(`pose_correction.py:40`: `(ts - epoch_t) / span`). Drift is per cell travelled, not per
second: a point placed during a 30 s load dwell has the same drift as the point placed just
before the dwell, but time-weighting moves it further. Measured: 5–18 % of all points are
placed while the agent is stationary. Same code, different stamp.

**Reason.** The snap is the single most important visual in the game and it is impossible
over a grid. The point set is what Phase 1 built and what the client will draw; the bins
are the grid, rebuilt from it, for steering.

**If wrong.** A pure grid loses the snap; a point set without bins loses map-aware steering
(BLD-101: the spoofed agent "held a 26,000-point map and used none of it"). Both halves
are needed. If time-weighting is kept, nothing breaks; stationary points relax a little
too far.

Reconciled 2026-09-06: `MapPoint` gains `character` and both map queries take the agent's own
terrain viability, read from `Belief.loadout` — its own body, not a truth leak — so a walker
and a Swimmer disagree about the same point without a second classifier (CHASSIS D8.3, D8.4;
BLD-71's one-classification rule). See PHASE-3-OPEN-QUESTIONS.md §14 and §24.

Designer (point set + derived bins): [ ] yes [ ] no
Designer (weight relax by odometry distance, not time): [ ] yes [ ] no

---

## 7. `Belief.pose: PoseEstimate // mean + covariance`

**ARCHITECTURE says** mean plus covariance.

**Phase 1 evidence.** Phase 1 never built a covariance. `belief.py:84–97` is a
three-parameter model: `sigma_along = 0.5 + 0.038·d`, `sigma_cross = 0.5 + 0.5·d·sigma_theta`,
`sigma_theta += 0.0013·d`, all reset on a fix, where `d` is odometry distance since the
last fix. `tuning.py:42–44`: "The estimator's own model of its error … kept slightly under
the truth: a fix that jumps further than the ellipse promised is the tell a player can
actually catch." It is deliberately not the truth's covariance.

**Recommendation.**

```rust
pub struct PoseEstimate {
    pub mean: Pose,                       // x, y, heading in the belief frame
    pub sigma_along: Fx,                  // grows with odometry since epoch
    pub sigma_cross: Fx,
    pub sigma_heading: Fx,
    pub epoch: Epoch,                     // the anchored end of the current drift interval
}
pub struct Epoch { pub tick: Tick, pub pose: Pose, pub odo: Fx }
```

**Reason (guess).** The ellipse is a gameplay object whose parameters are content, and
whose honesty is a tuning choice. A 3×3 covariance with an EKF update needs a Jacobian per
sensor in fixed point and buys nothing a player sees. The three sigmas *are* a diagonal
covariance in the travel frame, so this is a restriction, not a departure; widen it later
if TRN or contact fusion needs cross terms.

**If wrong.** Predicates written over `sigma_pos()` (Phase 2's `uncertainty > θ`) do not
care which representation is underneath. A later covariance is an internal change.

Designer: [ ] yes [ ] no

---

## 8. The rest of `Belief`: what Phase 1 needed that ARCHITECTURE does not list

**ARCHITECTURE says** `pose, map, contacts, beacons, inventory, ticks_since_fix, self_report`.

**Phase 1 evidence.** `belief.py:29–81` holds, beyond those: the believed trail (`:59`;
Phase 2's `return_to_beacon` walks it), the fix history (`:80`, `FixRecord` with `jump`
and `surprise`, `fix_record.py:26–33`: "a fix that moves you forty cells when the ellipse
promised six is the tell that something lied to you"), the relax epoch (`:202`), which
sensor it carries (`:41`: "it knows this"), prior places (`:46`, the survey routes), and
two bearing trackers. `KnownBeacon` (`known_beacon.py`) carries `t_placed` and
`truth_anchor`. And the beacon chain finding, re-measured tonight over 318 honest
own-beacon fixes: **53 % increased true position error**, and the error after such a fix
equals the error the agent had when it dropped that beacon to within 1.8–3.5 cells on
average. The chain re-anchors the agent to its own past belief. This is not a bug and must
not be "fixed" (BLD-88).

**Recommendation.**

```rust
pub struct Belief {
    pub pose: PoseEstimate,                       // §7
    pub map: BeliefMap,                           // §6
    pub trail: Vec<TrailPoint>,                   // believed path; relaxed with the map
    pub contacts: Vec<ContactTrack>,              // §9
    pub beacons: BTreeMap<BeaconId, KnownBeacon>, // including ones that lie; insertion order kept in `chain`
    pub chain: Vec<BeaconId>,                     // own drops in order (return_to_beacon retraces it)
    pub foreign_beacons: Vec<ForeignBeacon>,      // other teams' transponders heard; no fix (§1)
    pub fixes: Vec<FixRecord>,                    // history; the only belief-legal spoof tell
    pub inventory: Inventory,                     // cargo, and blocks downloaded (§16)
    pub self_report: SelfReport,                  // the union: the SelfReport return, the depth
                                                  // gauge's medium, and the runner's report (§12)
    pub loadout: LoadoutRef,                      // it knows what it carries
    pub ticks_since_fix: Ticks,
    pub ticks_since_emit: Ticks,
}
pub struct KnownBeacon { pub id: BeaconId, pub pos: Vec2Fx, pub placed: Epoch, pub truth_anchor: bool }
pub struct FixRecord { pub tick: Tick, pub source: FixSource, pub pre: Pose, pub post: Pose, pub sigma_before: Fx }
impl FixRecord { pub fn jump(&self) -> Fx; pub fn surprise(&self) -> Fx; }
```

No `known_places`: generated caves have no prior survey; the only prior is the shaft, which
arrives as a `KnownBeacon { truth_anchor: true }`.

**Reason.** Every field above is something a Phase 1 policy or predicate read. `fixes` is
the source of the predicate candidate *fix surprise ≥ θ* (BLD-97); `chain` is what Phase
2's `return_to_beacon` needs; `loadout` is how a lidar carrier knows it is silent.

**If wrong.** Missing fields are added when a predicate needs them; the cost is a schema
bump. The one that is expensive to get wrong is `beacons` being a map with a separate
order, because relax must skip the fixing beacon and truth anchors by id
(`belief.py:218`).

Reconciled 2026-09-06: `nav` leaves Belief — `NavState` is owned by the `PolicyRunner` beside
Belief, hashed with it, never read by predicates — because this struct listed it inside Belief
while §12 and §13 passed it separately; see PHASE-3-OPEN-QUESTIONS.md §21.
Reconciled 2026-09-06: `foreign_beacons` added, per §1's unfiltered `transponders_in_range`;
see PHASE-3-OPEN-QUESTIONS.md §10.
Reconciled 2026-09-06: `self_report` is the union of what the `SelfReport` return carries, the
depth gauge's `medium` (CHASSIS D8.2) and the runner's `current_action` + start tick (DRIVER
D6); the return feeds a subset of the field. See PHASE-3-OPEN-QUESTIONS.md §16 and §29.

Designer: [ ] yes [ ] no

---

## 9. `contacts: Vec<ContactTrack>` — per-arrival retention and the lidar cluster tracker

**ARCHITECTURE says** `pub contacts: Vec<ContactTrack>, // bearings over time, unresolved`.

**Phase 1 evidence.** `contact.py:12–47`: a contact merges arrivals within 18° and 8 s
(`absorb`), fades after 14 s, rotates with a fix. The scripted echo at 2:15 merged into the
rival's standing contact and "never appeared as its own event" (`tuning.py:285–291`), which
is why BLD-89 asks each arrival to be retained. `bearing_tracker.py` keeps 60 observations
each with the believed position it was heard from, refuses to answer while ill-conditioned,
and is relaxed by fixes. The design panel (BLD-89) found that a lidar carrier cannot notice
a rival at all — measured tonight, the player with lidar logs contacts only from the
rival's *sonar* pings; a lidar rival would be invisible.

**Recommendation.**

```rust
pub struct Arrival { pub tick: Tick, pub bearing: Fx, pub quality: Fx, pub character: SoundCharacter,
                     pub from: Vec2Fx /* believed pose when heard; relaxed */ }
pub enum ContactOrigin { Acoustic, Ranged { range: Fx } }   // Ranged: a moving RangeBearing cluster not on the map
pub struct ContactTrack {
    pub id: ContactId,                    // per-agent sequence, step-order independent
    pub origin: ContactOrigin,
    pub arrivals: Vec<Arrival>,           // capped (Phase 1: 60); merged by bearing but never dropped inside the window
    pub character: SoundCharacter,
    pub estimate: Option<(Vec2Fx, Fx)>,   // bearing-only crossing, or None while ill-conditioned
    pub stationary: Fx,                   // how little the estimate has moved: the echo/decoy tell, readable by predicates
    pub last: Tick,
}
```

The cluster tracker is a `BeliefUpdater` stage after point placement: a group of
`RangeBearing` returns whose origin persists across sweeps and is not in `map.bins` opens a
`Ranged` track; a stationary group stays map. No `is_echo` anywhere (BLD-80).

**Reason.** A contact is not an identification; the type must hold evidence, not verdicts.
Retaining arrivals is what lets a second arrival inside the merge window be a
Belief-visible event without any flag saying what it was.

**If wrong.** If per-arrival retention is too much state, cap it lower; the cluster tracker
can ship later without changing the type because `origin` already exists.

Designer: [ ] yes [ ] no

---

## 10. `World.wrecks: Vec<Wreck>`, and every World collection

**ARCHITECTURE says** `wrecks: Vec<Wreck>,` beside four `SlotMap`s. DETERMINISM rule 6:
"Entity iteration is by stable ID, always. Never by insertion order or index." Rule 7: IDs
are "never derived from … registration order, or vector indices". BLD-69 asks: "BTreeMap
keyed by id vs SlotMap plus a BTreeMap index".

**Phase 1 evidence.** `world.py:36,51–52`: beacon ids come from a World counter
(`bid = f"{owner}_{self.next_beacon_id}"`), so the id an agent's third beacon gets depends
on whether the rival dropped one first in step order — exactly the rule 7 violation.
Agents are a dict keyed by name; death is `agent.alive = False` (`world.py:109`), no wreck
object. Measured population: 14–21 beacons and 2 agents; four teams would be roughly 40–80
beacons, a handful of ancients, at most one wreck per agent.

**Recommendation.**

```rust
pub struct AgentId(pub u32);      // from MatchRecord.loadouts (team, slot); the Phase 0 width
pub struct BeaconId { pub owner: AgentId, pub seq: u16 }   // per-agent sequence; shafts use owner = AgentId::SURVEY
pub struct WreckId(pub AgentId);  // an agent dies once
pub struct DepositId(pub u16);    // from the generator, in placement order for the seed
pub struct AncientId(pub u16);    // likewise

pub(crate) struct World {
    tick: Tick,
    cave: Cave,
    agents:      BTreeMap<AgentId, AgentTruth>,
    beacons:     BTreeMap<BeaconId, Beacon>,
    wrecks:      BTreeMap<WreckId, Wreck>,
    deposits:    BTreeMap<DepositId, Deposit>,
    discoveries: BTreeMap<DiscoveryId, Discovery>,   // §21
    ancients:    BTreeMap<AncientId, AncientInstance>,
    acoustics:   AcousticField,                      // emitters are state; propagation fields are cache (BLD-81)
    optical:     Vec<LightEmitter>,                  // rebuilt each tick; not hashed
}
```

`BTreeMap` everywhere, keyed by a record-assigned id. No `SlotMap`.

**Reason.** A `BTreeMap` iterates in key order, so rule 6 is a property of the container
rather than of every loop. A `SlotMap` key is a slot index plus generation, which is
insertion order under another name; using it as identity is rule 7 broken by the type, and
iterating it in id order needs the side index BLD-69 mentions anyway. At these sizes
(tens of entries) the O(log n) lookup is not measurable. `BeaconId { owner, seq }` makes an
agent's beacon ids independent of step order, which is what BLD-69 is for.

**If wrong.** If an entity type ever reaches thousands (it does not in this design; points
live in Belief, not World), swap that one map for a sorted `Vec`. Nothing downstream names
the container.

Reconciled 2026-09-06: `AgentId` is `u32`, not `u16`, matching `ids.rs` on the Phase 0 branch
rather than forcing a re-goldening of the Phase 0 fixtures for no gain; the `team * 16 + slot`
packing is superseded by a (team, slot) rule. See PHASE-3-OPEN-QUESTIONS.md §18.

Designer: [ ] yes [ ] no

---

## 11. Phase 1 `World` fields that must not port

Not a conflict with ARCHITECTURE, but a list the Phase 3 `World` (BLD-70) needs.

`world.py:36–42`: `next_beacon_id` (→ §10), `spoof_done` and `spoof()` (`:57–75`, the
scripted lie → BLD-106's action, no truth-side arming), `pending_sounds` (`:41`, the
scripted echo → BLD-80's reflective rock; a crash is an acoustic emitter with a one-tick
life), `events` (`:40`, the truth log → harness diagnostics behind BLD-76's gate),
`load_progress` (`:42` → a field of `AgentTruth`). `Ancient` (`ancient.py`) reads the
clock in seconds (`phase(t)`) → ticks (§17).

Designer: [ ] yes [ ] no

---

## 12. The `Action` trait, the actuator, and where multi-tick action state lives

**ARCHITECTURE says** only the table row `| Actions | impl Action + entry | 2 → 15 |` and,
under Hardware-readiness, "`Sensor` and the actuator interface should be designed so a
hardware backend is a second implementation of the same traits". Neither trait is written.

**Phase 1 evidence.** `motor_command.py:12–19` is the whole output of a policy:

```python
class MotorCommand:
    """... there is no way to ask for a position, only for a heading and a speed."""
    heading: float
    speed: float = 0.0
    ping: bool = False
    drop: bool = False
    load: bool = False
```

`agent_truth.py:43–61` applies it: turn-rate limited, wall sliding, and records
`last_true_delta` — the achieved motion the odometry sensor corrupts. The Phase 1 policy
(`policy.py:20–54`) carries about twenty fields of multi-tick state: route and index, load
timer, investigate bearing, escape heading, search spiral angle. In a behaviour tree
re-evaluated every tick that state has to live somewhere the tree can read it back.

**Recommendation.**

```rust
// what a policy asks for this tick; the whole of its output
pub struct Intent {
    pub motor: MotorCmd,
    pub requests: SmallVec<[Request; 4]>,
    pub report: RunnerReport,          // durable facts for Belief.self_report; fused like a return
}
pub struct MotorCmd { pub heading: Fx, pub speed: Fx, pub gait: GaitId }
pub enum Request { Emit(SensorId), DropBeacon, Load, Interface, AbortToShaft, CloneBeacon { target: BeaconId, offset: Vec2Fx } }

pub trait Action {
    fn id(&self) -> ActionId;
    fn run(&self, b: &Belief, nav: &mut NavState, params: &[Fx], out: &mut Intent) -> ActionStatus;
}
pub enum ActionStatus { Running, Success, Failure }

// the actuator seam: the sim's implementation moves AgentTruth over the heightfield and
// records the achieved delta; a hardware driver would drive motors and record nothing
// (its odometry sensor reads encoders instead)
pub trait Actuator {
    fn apply(&mut self, agent: &mut AgentTruth, cave: &Cave, cmd: &MotorCmd, dt: Ticks);
}
```

`NavState` (DRIVER's `ActionRuntime`) is the one thing an action may write: route, waypoint
index, stuck timers, search spiral, load timer. It is owned by the `PolicyRunner` *beside*
Belief, hashed and serialised with the agent's belief-side state, reset per action on entry,
and never read by a predicate. What a policy may reasonably decide on — the running action and
since when, plan progress, a place's done/given-up status — travels in `Intent.report` and is
fused into `Belief.self_report` in the fuse phase.

Reconciled 2026-09-06: `NavState` was listed inside `Belief` in §8 and passed separately here
and in §13, and DRIVER §4.4 said durable facts "live in Belief" with no path for them to get
there; `Intent.report` **[guess: the channel]** is that path. See
PHASE-3-OPEN-QUESTIONS.md §21.

Reconciled 2026-09-07: the request arm was `Spoof { target, offset }`; it is named for the
action that issues it, `clone_beacon` (ActionId 9, SENSORS §3.7), so the arm is
`CloneBeacon`. See PHASE-3-OPEN-QUESTIONS.md §21.

**Reason.** `Intent` is Phase 1's `MotorCommand` with the booleans made a list so a new
module (spoof, gait, interface) is a new `Request` arm, not a new field on every policy. An
action that reads `&Belief` and writes only `NavState` cannot corrupt the pose, map or
contacts, which is the invariant's belief-side cousin. The actuator trait takes truth
because it *is* truth-side; the hardware seam is the shape of `MotorCmd`, which a base
controller can consume as a heading setpoint and speed.

**If wrong.** If Phase 4's VM wants actions to be stateless one-shot ops, `NavState` stays
in Belief and actions become `run(&Belief, params) -> Intent` with the VM owning
`Running`. That is a trait change on a registry of six.

Designer: [ ] yes [ ] no

---

## 13. `Policy::evaluate`: signature and owning crate

**ARCHITECTURE says** "Write a compile-time test asserting `Policy::evaluate` cannot reach
`World`" but `Policy` holds `nodes: Vec<BtNode>` (behaviour crate) and `bytecode: Vec<Op>`
(vm crate), and "`blindside-sim` depends only on `blindside-vm` and `blindside-content`".
So `Policy` cannot be a sim type, `evaluate` cannot live on it inside the sim, and the VM
cannot take `&Belief` (it would need to depend on sim, which depends on it).

**Phase 1 evidence.** `policy.py:212–214`: `def step(self, t: float) -> MotorCommand` over
`self.b: Belief`; `phase1/match/invariant.py` walks the AST to prove `belief` and `policy`
never import `truth`. That is the target the compile-fail test needs.

**Recommendation.** Break the cycle with a host trait in the VM crate:

```rust
// blindside-vm: knows nothing of Belief
pub struct CompiledPolicy { pub schema: u16, pub program: FlatTree,
                            pub budget: VmBudget, pub policy_hash: [u8; 32] }
pub trait VmHost {
    fn eval_predicate(&mut self, id: PredicateId, params: &[Fx]) -> bool;
    fn run_action(&mut self, id: ActionId, params: &[Fx]) -> ActionStatus;
}
pub fn run_tick(p: &CompiledPolicy, s: &mut VmState, host: &mut impl VmHost) -> TickReport;

// blindside-sim/src/policy.rs: the entry point and the compile-fail target
impl PolicyRunner {
    pub fn evaluate(&mut self, b: &Belief, tick: Tick) -> Intent;
}
// implements VmHost over (b, &mut NavState, registry, &mut Intent) and calls run_tick
```

`Policy` (nodes + bytecode + provenance) lives in `blindside-behavior`; the sim consumes
`CompiledPolicy`. In Phase 3 that artifact is a flat tree run by the interpreter in
`blindside-vm` behind this seam, and both reference policies are tree data over the registries
(BLD-62's answer; BLD-102 builds it).

Reconciled 2026-09-06: names unified with AGENT-DRIVER — `Host` → `VmHost`, `Program` →
`CompiledPolicy`, the free `evaluate` → `PolicyRunner::evaluate` returning this document's
`Intent` — and "driven by hand-written Rust policies" is replaced by the tree interpreter,
which is what BLD-62 answered. See PHASE-3-OPEN-QUESTIONS.md §20 and §21.

**Reason.** The dependency rule is load-bearing for determinism auditing; a host trait is
the standard way to keep an interpreter blind to its host's types.
`blindside_sim::policy::PolicyRunner::evaluate` is one method in one file, which is what a
trybuild case can name.

**If wrong.** If the VM must read Belief directly for speed, Belief moves to a leaf crate
both depend on — a larger reorganisation, and the module-privacy argument for rule 4
weakens. Prefer the trait until profiling says otherwise.

Designer: [ ] yes [ ] no

---

## 14. The `MatchMode` trait

**ARCHITECTURE says** `| Match modes | impl MatchMode | 1 → 4 |`, nothing else.
`DESIGN-PRINCIPLES.md` §2: Extraction is the core mode.

**Phase 1 evidence.** `sim.py:162–186` (`_extraction`, `_finish`): the window opens at
`EXTRACT_WINDOW_OPENS = 6*60+30`, an active agent within `EXTRACT_RADIUS` of its shaft in
*truth* is extracted, the match ends at `MATCH_SECONDS` or when every agent is resolved,
and the result is cargo if extracted else zero. Scoring reads truth; the policy never does.

**Recommendation.**

```rust
pub struct ModeId(pub u16);
pub trait MatchMode {
    fn id(&self) -> ModeId;
    fn setup(&self, w: &mut World, rec: &MatchRecord);
    fn step(&self, w: &mut World, tick: Tick) -> Option<MatchEnd>;   // extraction window, resolution
    fn score(&self, w: &World) -> BTreeMap<TeamId, Score>;           // reads truth; emits numbers only
}
pub struct MatchParams { pub length: Ticks, pub commit_at: Ticks, pub extraction_opens: Ticks }   // content, per mode
```

Phase 1's values in ticks at 20 Hz: length 9600, extraction opens 7800, commit 400
(DESIGN's ~20 s descent; Phase 1 started at commit).

**Reason.** Survey mode scores map accuracy against ground truth, so `score(&World)` is
the right signature for all four modes, and it is inside the sim, which is the only place
allowed to read both. `step` owns the window and the end rule so the tick loop (BLD-107)
does not know which mode it is running.

**If wrong.** A mode needing per-agent hooks (Race's "first to reach") adds a method.
Low cost.

Designer: [ ] yes [ ] no

---

## 15. `WorldView` contents

**ARCHITECTURE says** `fn step(&self, s: &mut AncientState, w: &WorldView, rng: &DeterministicRng);`
and never defines `WorldView`.

**Phase 1 evidence.** `ancient.py` reads nothing from the world: a fixed cycle on the clock.
The kill is done by `World.step_hazards` (`world.py:99–112`) checking `ancient.covers(x, y)`
for each agent. Phase 7's provocable systems (`provocable_by`) will need to know who is
near and what is emitting.

**Recommendation.**

```rust
pub struct Presence { pub agent: AgentId, pub pos: Vec2Fx, pub chassis: ChassisId,
                      pub acoustic: Option<AcousticSignature>,
                      pub optical: Option<LightSignature> }
pub struct WorldView<'a> {
    pub tick: Tick,
    pub cave: &'a Cave,
    pub presences: &'a [Presence],        // every live agent, truth positions
    pub acoustics: &'a AcousticField,     // what is audible where
    pub me: &'a AncientPlacement,         // own position and hazard geometry
}
```

No beacons, no beliefs, no deposits, no other ancients' state.

**Reason.** Ancients are truth-side and may read truth; narrowing is for auditability
(what can an ancient react to?) and for keeping the borrow small while the tick loop mutates
the rest. Everything a "signature before lethal, provocable by a loud ping" system needs is
in the five fields.

**If wrong.** Adding a field to a view struct is one line. The cost of `&World` instead is
that ancients become a second unaudited reader of everything.

Reconciled 2026-09-06: `emitting: Emission` held one channel, but a sonar carrier with a
camera lamp — or a Swimmer carrying sonar and lidar (CHASSIS R4) — emits on both in one tick,
so it becomes a pair of `Option`s. See PHASE-3-OPEN-QUESTIONS.md §12 and §32.

Designer: [ ] yes [ ] no

---

## 16. `AncientSystem`: the `yields()` seam and `BlockId`

**ARCHITECTURE says** `kind, signature, step, hazard, provocable_by`. BLD-103 adds a
`yields()` seam per the panel; `DESIGN-PRINCIPLES.md` §1–2: base blocks are a list, the
cool things are new blocks, and "the machinery's `yields()` seam is one source".

**Phase 1 evidence.** `policy.py:455–456` and `:476`: the aggressive rival stops at
the machinery and interfaces for `INTERFACE_S = 80` s (longer than one 75 s cycle, so the
next cycle finds it there — measured 4/8 sonar deaths from that dwell), and "there is no
cargo return for a download in Phase 1, only the time spent." The dwell is the price; the
reward has no type yet.

**Recommendation.**

```rust
pub enum BlockId { Predicate(PredicateId), Action(ActionId) }   // a base block; blocks are a list
pub struct Yield { pub block: BlockId, pub dwell: Ticks }

pub trait AncientSystem {
    fn kind(&self) -> AncientKindId;
    fn signature(&self, s: &AncientState) -> Option<AcousticSignature>;
    fn step(&self, s: &mut AncientState, w: &WorldView, rng: &DeterministicRng);
    fn hazard(&self, s: &AncientState) -> Option<HazardVolume>;
    fn provocable_by(&self) -> &[ProvocationKind];
    fn yields(&self, s: &AncientState) -> Option<Yield>;     // what a completed Interface dwell brings back
}
```

`Request::Interface` (§12) starts a dwell; on completion the sim adds the block to
`AgentTruth.inventory.blocks`, which reaches Belief through the next `SelfReport` return
(so `Inventory { cargo: u8, blocks: Vec<BlockId> }`). What a block *unlocks* is Phase 4+.

**Reason.** The seam needs an id type for "a block" before anything else refers to one,
and DESIGN-PRINCIPLES already says a block is a predicate or an action with a stable id.
Two-arm enum, no new registry.

**If wrong.** If yields become subtrees (`PolicyRef`) or modules later, `BlockId` grows an
arm. `Option<Yield>` on the trait is free if Phase 3's one system returns `None`.

Designer: [ ] yes [ ] no

---

## 17. Tick rate, `Tick`, and no seconds inside the sim

**ARCHITECTURE says** nothing about the rate; `Tick` appears untyped. BLD-61 asks for it.

**Phase 1 evidence.** `tuning.py:14–15`: `TICK_HZ = 20`, `DT = 1/20`. Measured tonight:
tick mean 0.37–0.88 ms, p99 4–8 ms, worst 24–34 ms in Python, and every worst tick is a
whole-cave Dijkstra build (mean 4.3–5.8 ms, worst 12.9–23.4 ms; 219–1058 builds per
two-agent match). Fifteen Phase 1 constants are already in ticks or multiples of `DT`
(`NEARFIELD_PERIOD_TICKS = 4`, passive sampling every 10 ticks, the ancient every 5, deafness
20, audible 60, contact merge 160, fade 280). Scratch check: `1/20` in I32F32 is
`0x0CCCCCCC` = 0.0499999998 and `20 × DT` = 0.9999999963, so a sim that accumulates
seconds from `DT` drifts from its own clock.

Budget arithmetic for the Phase 3 gate: 1,000 matches × 9,600 ticks = 9.6 M ticks in
600 s = **62.5 µs per tick single-threaded**, or ~500 µs per tick with 8 cores running
matches in parallel (DETERMINISM rule 5 allows that). Rust at 50–100× Python puts the
Phase 1 mean at 5–15 µs; the acoustic worst case is BLD-64's problem and the reason it is a
spike.

**Recommendation.**

```rust
pub struct Tick(pub u64);      // 20 Hz; a 10-minute match is 12_000. u64, as Phase 0 built it
pub struct Ticks(pub u32);     // a duration
pub const TICK_HZ: u32 = 20;   // content constant; lives in blindside-content, quoted here
```

Inside the constrained crates there are no seconds: speeds are cells per tick, periods are
`Ticks`, latencies are `Ticks`. Content files may state seconds; the content loader
converts once, with an error if a value is not a whole number of ticks.

**Reason.** 20 Hz is what every Phase 1 measurement was made at, and the case for
changing it (halving the tick count) is weaker than the case for keeping fifteen
calibrated constants. Keeping seconds out of the sim removes `DT` and its rounding from the
determinism surface entirely.

**If wrong.** If 10 Hz turns out necessary for the gate, each tick-denominated constant is
halved in content; the type does not change. If seconds are allowed in, `DT` becomes a
canonical constant whose bit pattern is part of the content hash.

Reconciled 2026-09-06: `Tick` is `u64`, not `u32` — the Phase 0 branch's `ids.rs` already has
`Tick(u64)` and `AgentId(u32)` (§10), and this is BLD-20's open width question answered once.
See PHASE-3-OPEN-QUESTIONS.md §18.

Designer: [ ] yes [ ] no

---

## 18. `DeterministicRng::draw` and the purpose space

**ARCHITECTURE says** `pub fn draw(&self, tick: Tick, entity: u32, purpose: u16) -> Fx`.
ROADMAP Part 3 disagrees with itself: `rng: &mut DeterministicRng` in `sample` and a
`rng: DeterministicRng` field on `World`. BLD-74: purpose space must include `sensor_id`.

**Phase 1 evidence.** Phase 1 used stateful streams: one `np.random.default_rng(seed)` per
sensor rig (`sensor_rig.py:37`), per belief (`belief.py:45`, used for the map's z-scatter
and the load-search nudge), and per `AgentTruth` (`agent_truth.py:33`, the drift signs).
Call order changes results — the thing rule 4 forbids. Draw counts per event: sonar 60
rays × 2 noises + 2 false × 3 = 126 per ping; lidar 180 per sweep; odometry 2 per tick;
near-field ~10 per 4 ticks. Every draw in Phase 1 is Gaussian except the false-return
positions and the drift signs.

**Recommendation.**

```rust
pub struct Purpose { pub sensor: SensorId, pub kind: u8, pub index: u16 }   // packed to u32
impl DeterministicRng {
    pub fn unit(&self, tick: Tick, entity: EntityId, p: Purpose) -> Fx;      // [0, 1)
    pub fn normal(&self, tick: Tick, entity: EntityId, p: Purpose) -> Fx;    // ~N(0,1): sum of 12 units minus 6 (guess)
    pub fn sign(&self, entity: EntityId, p: Purpose) -> Fx;                  // ±1, tick-free: the per-agent drift lean
}
```

`&self` everywhere; no field on `World` except the seed. `index` is the ray or false-return
number so 180 draws in one tick are 180 different keys.

**Reason.** Stateless by construction means the phased tick order (§20) cannot change a
noise value, and two sims stepping different subsystems in different orders still agree.
The Gaussian is needed because every Phase 1 noise model is Gaussian and the tunings were
measured against that; Irwin–Hall over 12 uniforms is exact enough for noise whose sigma is
a content guess, and needs no log or sqrt in fixed point (BLD-67 may choose a ziggurat LUT
instead; the signature does not change).

**If wrong.** A different normal approximation changes the noise distribution's tails,
which changes false-return feel slightly. Nothing structural.

Designer: [ ] yes [ ] no

---

## 19. The fixed-point trig source (BLD-67 waits on this)

**DETERMINISM says** "Trig and `sqrt` are the usual culprits. Use fixed-point
implementations from a single module; never call platform math libraries from sim code."
BLD-61 asks: hand-written CORDIC/LUT, or a pinned pure-integer crate.

**Evidence (scratch Cargo project outside the repo, release build, this laptop).**
`fixed = 1.31.0` provides `sqrt` natively (`fixed/src/wrapping.rs:1007`). `cordic = 0.1.5`
(depends only on `fixed`) provides `sin`, `cos`, `atan2`, `sqrt`, `exp` over any `fixed`
type; its runtime path uses `U0F64` lookup tables and integer shifts only — every `f64` in
its source is under `#[cfg(test)]` (`cordic/src/lib.rs:238`). Over `I32F32`: max abs error
atan2 6.9e-10, sin/cos 1.6e-9, sqrt 2.1e-10 across the Phase 1 angle range; throughput
**679 ns per (atan2 + sin + cos)** — CORDIC iterates once per fractional bit, so it is
slow. Amortised Phase 1 trig load is small (a lidar sweep is 90 rays per 30 ticks, near-field
8 per 4 ticks), so per agent per tick roughly 10–20 calls ≈ 7–14 µs, against the 62.5 µs
single-thread gate budget in §17. A ping or sweep tick is ~120 µs of trig alone.

**Recommendation.** Pin `cordic = "=0.1.5"` and `fixed = "=1.31.0"` behind one module,
`blindside-sim/src/fxmath.rs`, which is the only file allowed to name either crate:

```rust
pub fn sin(a: Fx) -> Fx; pub fn cos(a: Fx) -> Fx; pub fn atan2(y: Fx, x: Fx) -> Fx;
pub fn sqrt(x: Fx) -> Fx; pub fn wrap(a: Fx) -> Fx;   // (-π, π]
```

with golden tests (BLD-67) over the exact bit patterns on three platforms. If the profile
in BLD-109 shows trig on the critical path, replace the bodies with a 4,096-entry LUT and
linear interpolation *in that file*, re-run the goldens, and bump the content hash.

**Reason.** A pure-integer crate with a one-crate dependency tree is auditable by reading
it, and its results are bit-identical anywhere `i128` multiplication is — which is every
target. Wrapping it means the swap to a LUT is invisible to callers.

**If wrong.** If `cordic` is abandoned, vendor the 300 lines. If its speed blocks the gate,
the LUT path above is a day.

Designer: [ ] yes [ ] no

---

## 20. Per-tick step order: phased, not interleaved per agent

BLD-107 owns the order, but the `Sensor::sample` borrow depends on it, so it is here.

**Phase 1 evidence.** `sim.py:96–133`: for each agent in turn — policy, move, drop, ping,
load, sample, fuse — then hazards, then expiry, then extraction. So the first agent samples
the world with the second agent still at its previous position, and the second samples the
first at its new one. Deterministic, but the lower id always sees stale rivals.

**Recommendation.** Phases, each over every agent by id before the next begins:

1. deliver commands whose delivery tick has arrived (`(tick, team, seq)` order)
2. `policy::evaluate` for every agent → `Intent` (reads `&Belief` only)
3. actuators apply every `MotorCmd`; requests take effect (drops, emissions registered)
4. world: ancients step, hazards resolve, wrecks form, acoustic emitters expire, mode step
5. sensors sample every agent against the one `&World` of this tick
6. belief updaters fuse
7. state hash

**Reason.** In phase 5 the whole world is borrowed immutably once and no agent sees a
half-updated tick; in Rust the interleaved form needs alternating `&mut World` and
`&World` per agent, which is legal but forces the sensing module to hold both. Fairness
falls out: no agent is sampled against a rival's stale position because of its id.

**If wrong.** A subsystem that needs per-agent interleaving (none in Phase 1) would move
into phase 3. The hash position is fixed either way.

Designer: [ ] yes [ ] no

---

## 21. Blocks are a list; discoveries are placed by depth; risk R9

`DESIGN-PRINCIPLES.md` §1: "Blocks are a list. Adding one is a data change." §2: "the Phase
3 cave generator must place discoveries by depth, not uniformly." BLD-108 adds R9, "a dry
clear cave is quiet".

**What this binds in the types.** `BtNode::Guard { pred: PredicateId }` and
`Act { action: ActionId }` already refer to blocks by id — that part of ARCHITECTURE holds.
What is missing is a place for a block to be *found*:

```rust
pub struct DiscoveryId(pub u16);
pub struct Discovery { pub block: BlockId, pub pos: Vec2Fx, pub depth: Fx /* path length from nearest shaft */ }
// blindside-gen: `place_discoveries(cave, seed, table: &DepthLootTable) -> BTreeMap<DiscoveryId, Discovery>`
// blindside-content: `DepthLootTable { bands: Vec<(Fx /* min depth */, Vec<(BlockId, weight)>)> }`
```

and the R9 consequence: nothing in `World` is scripted (§11), so an eight-minute match in
which no emitter ever registers is a legal state the harness must report, not tune away.
The `AcousticField` emitter list may be empty for a whole match.

**Reason.** Depth is path length, not straight line — Phase 1's `SoundField` already
computes it (`sound_field.py:13–20`), so the generator can reuse the same Dijkstra to band
the cave.

**If wrong.** If discoveries are not blocks (cargo variants, modules), `Discovery.block`
becomes an enum. The placement-by-depth seam is unchanged.

Designer: [ ] yes [ ] no

---

## Still undecided, and what each blocks

| Question | Blocks | Note |
|---|---|---|
| ~~Which driver runs agents in Phase 3~~ — answered: tree data in `blindside-vm` (BLD-62) | BLD-102, BLD-75 | §13 fixes the entry point; reconciled 2026-09-06, see PHASE-3-OPEN-QUESTIONS.md §20 |
| Normal-distribution method for `DeterministicRng::normal` | BLD-67 | §18 proposes Irwin–Hall; a ziggurat LUT is equivalent for callers |
| Point cap per agent (`BeliefMap.points`) | BLD-77 | Measured max 29.3k (lidar); 32,768 is the guess |
| Whether `Belief.map.points` is hashed every tick or only on canary runs | BLD-77, BLD-81 | 29k points × 4 agents per tick is the cost; canary-only is the likely answer |
| Acoustic model and budget | BLD-64, BLD-79, BLD-81 | Tonight's numbers: 219–1058 whole-cave builds per two-agent match, 4.3–5.8 ms each in Python |
| Sensor set and permanent IDs | BLD-63 | §4's `source: SensorId` needs near-field to have an id (module or chassis-intrinsic) |
| Chassis classes and when | BLD-65 | §3's Swimmer/lidar validation rule needs the class to exist |

## Design problems found on the way

1. **BLD-87's acceptance criterion "no honest beacon fix increases true position error" is
   unachievable by design.** Measured over 318 honest own-beacon fixes on 16 runs: 53 %
   increase true position error, and the error after the fix is the error the agent had at
   drop time (mean gap 1.8–3.5 cells). That is BLD-88's "the beacon chain buys confidence,
   not accuracy" working as intended. The criterion should read: no honest *truth-anchor*
   fix increases true error, and an own-beacon fix leaves true error within fix noise of the
   error at that beacon's drop.
2. **Recall never extracts at the committed tuning (`7fcbe87`).** Seed 7 at 3:00, 4:00,
   5:00, 5:30, 6:00, 6:30 and 7:00, and seeds 1–8 at 4:00, 5:30 and 7:00: 0 of 31 runs
   extract; "at the shaft, but nothing is answering" never appears, so the spiral search —
   the only mechanism that can undo a spoof — never runs. The trace on seed 7 (Recall at
   5:00) shows why: from 5:30 to 8:00 the player's true position does not change,
   `(121, 51)`, while it cycles "no progress toward HOME; wall escape 1…4" fourteen
   times, because `policy.py:364–365` ("Keep pushing for the shaft") resets the escape
   counter instead of abandoning the waypoint. Its believed position is `(89, 6)`, off the
   edge of the cave, so the believed shaft is behind solid rock from where it truly stands.
   BLD-105's done-when expects at least one timing to extract (it cites `b43ba0b`, which
   predates the map-aware steering in `31a4646`); that expectation is now false on the
   committed code. This is BLD-101's steering problem, not a type question, but the beat
   sheet (BLD-108) cannot be ported from Phase 1 as it stands.
3. **Lidar makes the map 4–5× larger** (27–29k vs 5–7k points) and moves ~5k points per
   relax. Fine in Rust; it is the number that sizes the point cap and the hash question.

## Guesses in this document

- `BeliefMap` point cap of 32,768 per agent (§6).
- Relax weighted by odometry distance rather than time (§6, separate yes/no).
- Three-sigma `PoseEstimate` instead of a covariance (§7).
- Irwin–Hall normal in the RNG (§18).
- `AgentId` layout: a (team, slot) rule (§10). The earlier `team * 16 + slot` packing in a
  u16 is superseded by Phase 0's `AgentId(u32)`.
- `Ticks(u32)` for every duration, including `Structural::time_to_failure` (§4, §17).
- `WorldView` field list (§15) — Phase 1's ancient read nothing, so this is the Phase 7
  need guessed forward.
- Amortised trig load of 10–20 calls per agent per tick (§19) is estimated from Phase 1
  ray counts and periods, not measured in Rust.
