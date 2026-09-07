# BLD-62 — What drives agents in Phase 3

Spike, 2026-09-06. One working day. Nothing in `blindside-sim` was written; a throwaway
Python prototype was run against the Phase 1 sim to get numbers. Every recommendation
below ends in a `Designer:` line. Anything guessed is marked **[guess]**.

**Recommendation in one sentence:** drive Phase 3 agents with a data-driven behaviour
tree interpreter living in `blindside-vm`, behind the same host seam the Phase 4 bytecode
VM will sit behind, and write both reference policies as tree *data* over the predicate
and action registries — not as Rust code, and not with a bytecode VM pulled forward.

---

## 1. The question and the three options

The Phase 3 gate runs 1,000 headless matches (BLD-109/110). Something must choose each
agent's action every tick, and `blindside-vm` / `blindside-behavior` are Phase 4.
ARCHITECTURE fixes two constraints: `blindside-sim` depends only on `blindside-vm` and
`blindside-content`, and the sim executes a *compiled artifact plus `VmBudget`*, never a
`Policy` holding `BtNode`.

| Option | What runs the agent | Cost in Phase 3 | What it leaves for Phase 4 |
|---|---|---|---|
| A. Hand-written Rust | Two Rust structs implementing a driver trait over the Predicate/Action traits | BLD-102 as costed, 2 d | Everything: host seam, artifact, budget, baseline. The 1,000-match replays are of closures the VM cannot re-run. |
| B. Minimal VM pulled forward | A register bytecode interpreter plus a hand compiler | 6–8 d **[guess]**: the BLD-116 ISA spike (designer round-trips), BLD-119, BLD-120, a compiler subset | Little, but it decides the ISA before the spike meant to ask the designer about it |
| **C. Tree interpreter in `blindside-vm`** | A flat, memoryless behaviour tree over predicate ids and action ids, one budget unit per node visit | ~3.5 d, +1.5 d over BLD-102 | Replaces only the interpreter body; keeps the seam, the artifact envelope, the budget, the reference policies, and becomes BLD-125's test oracle |

C is what Phase 2 already produces ("a tree over predicates with actions at the leaves,
`decide(belief) -> action`") and what Phase 4 compiles from. Phase 3 is the only phase in
which the same artifact would *not* exist under A or B.

## 2. What was measured

A prototype (`treeproto/`, ~600 lines of throwaway Python in the session scratchpad;
see §12) replaced `phase1.policy.Policy` with a tree interpreter plus an action runtime,
with the sim, sensors and belief untouched. The interpreter has exactly ARCHITECTURE's
node kinds (Sequence, Selector, Guard, Act), no memory, and is evaluated from the root
every tick. Phase 1's steering, stuck detection, wall escape, load retry and shaft search
were ported verbatim into the actions. The cautious and aggressive policies were then
written as tree data and run on the same eight seeds as the hand-written policy.

### 2.1 The beats, hand-written vs tree, 8 seeds, no Recall

| seed | driver | spoof | cargo | uncertainty return | rival interfaces | rival dies | player dies |
|---|---|---|---|---|---|---|---|
| 1 | hand | 2:20.8 | 1:29.6 | – | 6:52.6 | – | – |
| 1 | tree | 2:21.1 | 1:29.6 | 7:41.9 | 5:37.3 | 5:41.0 | – |
| 2 | hand | 2:21.9 | 1:28.9 | – | 3:09.3 | 4:26.0 | – |
| 2 | tree | 2:23.2 | 1:28.9 | 7:07.5 | 5:37.3 | 5:41.0 | – |
| 3 | hand | 2:22.0 | 1:29.6 | – | – | – | 6:56.0 |
| 3 | tree | 2:21.6 | 1:29.6 | – | – | – | – |
| 4 | hand | 2:21.0 | 1:29.1 | – | 4:21.8 | 4:26.0 | – |
| 4 | tree | 2:23.0 | 1:29.1 | 6:24.2 | 5:37.3 | 5:41.0 | – |
| 5 | hand | 2:22.2 | 1:29.3 | – | – | – | – |
| 5 | tree | 2:22.7 | 1:29.3 | – | 3:10.8 | – | 4:26.0 |
| 6 | hand | 2:20.8 | 1:29.5 | – | 3:09.3 | 4:26.0 | – |
| 6 | tree | 2:23.0 | 1:29.5 | 6:21.7 | 3:13.8 | – | – |
| 7 | hand | 2:21.4 | 1:28.9 | 6:31.5 | 5:37.3 | 6:56.0 | – |
| 7 | tree | 2:21.0 | 1:28.9 | 7:44.2 | – | – | – |
| 8 | hand | 2:21.4 | 1:29.0 | 6:09.7 | – | – | – |
| 8 | tree | 2:22.7 | 1:29.0 | 5:19.1 | 3:14.3 | – | – |

- Spoof fires 8/8 under both, within 2.2 s of each other (it is armed by the victim's
  own beacon geometry, which the tree reproduces).
- Cargo lands on the identical tick on 8/8 seeds.
- Rival dies at the machinery 3/8 (tree) vs 4/8 (hand); player dies 1/8 under both.
- The cautious uncertainty return fires 6/8 (tree) vs 2/8 (hand). Post-spoof paths
  diverge because the tree's `investigate` is its own leaf while Phase 1's is a heading
  override inside route-following, and once paths diverge the sigma trajectories do too.
  Not investigated further; it is a porting choice, not a driver limitation.
- All 16 matches end "lost in the cave" or "destroyed", same as the hand-written ones.
- With Recall at 300 s: 0/8 extract under both (also the case for the hand-written
  policy; BLD-105's timing sweep is the story that owns that).
- Lidar loadout (`--player-sensor lidar`, seed 7): cargo at 1:27.8 and spoof at 2:20.0
  under both. 320 sweeps vs 301: the tree's emission channel keeps sweeping during the
  30 s load dwell, the hand-written `LOAD` mode returns early and does not. A real, small
  semantic difference of the two-channel tree (§4.3).
- Two runs of the same seed produce byte-identical timelines.

### 2.2 Cost of the tree per tick

Over 32 tree-driven matches (8 seeds × {no Recall, Recall 300 s} × 2 agents):

| | cautious tree | aggressive tree |
|---|---|---|
| nodes | 33 | 32 |
| node visits per tick, mean | 18.4 (13.5–22.1 across runs) | |
| node visits per tick, max in any tick | **24** | |
| predicate evaluations per tick, mean | 7.4 | |
| locomotion leaf changes per match | 4–12 (mean 6.8; about one per 70 s) | |
| interpreter time, Python | 0.15 ms per agent-tick (Phase 1's whole tick is 0.76 ms) | |

So: a policy of this size needs a budget of a few dozen node visits; the chosen leaf
changes about once a minute, so evaluating every tick is cheap and a per-tick trace
(BLD-128) compresses to almost nothing.

### 2.3 What exactly Phase 2's vocabulary can express

Both policies were rewritten using **only** Phase 2's three predicates and two actions
(`carrying_cargo` given the capacity as its threshold; `take_branch` standing in as
`survey_auto` with ping, beacon-drop and load folded inside it, because there is no
other place for them):

| seed | spoof | cargo | rival dies | player dies |
|---|---|---|---|---|
| 1–8 | 8/8, same times | 8/8, same ticks | **2/8** (seeds 5, 7 at 4:26) | 1/8 (seed 3) |

The rival cannot hear the machinery as a decision, so it never investigates or
interfaces; its death becomes path luck at 2-in-8 — which is exactly the number
`tuning.py` records from before the investigate/interface behaviour was added ("a 2-in-8
event across seeds ... path luck, not a beat"). The cautious agent cannot freeze. Trees
shrink to 8 and 4 nodes, 5 and 3 visits per tick.

### 2.4 The latch

The cautious rule "once lost, go home and stay home" is a latch; a memoryless tree has
none. The prototype expresses it as a self-report predicate `action_running(return_chain)`
(§4.4). With that guard removed, on the six seeds where a return fired the agent flipped
back to surveying once on one seed and never on the other five — because Phase 1's
return fires late and a spoofed agent seldom regains a fix on the way home. The latch is
still needed: Phase 3's honest beacon fixes every 45 cells will collapse sigma below θ on
every return. Phase 1's numbers simply do not stress it.

## 3. The recommendation: placement and the trait the sim calls

### 3.1 `blindside-vm` (Phase 3 contents; a constrained crate under DETERMINISM.md)

```rust
pub struct VmBudget { pub ops_per_tick: u32 }            // ARCHITECTURE, unchanged

pub struct CompiledPolicy {                               // the artifact the sim executes
    pub schema: u16,
    pub program: FlatTree,                                // Phase 4: Vec<Op> behind the same field
    pub budget: VmBudget,
    pub policy_hash: [u8; 32],                            // hash of program bytes + schema
}

pub struct FlatTree { pub root: u16, pub nodes: Vec<FlatNode>, pub children: Vec<u16> }
pub enum FlatNode {                                       // ARCHITECTURE's BtNode, flattened; Subtree inlined before this
    Sequence { first_child: u16, child_count: u8 },
    Selector { first_child: u16, child_count: u8 },
    Guard    { pred: PredicateId, params: [Fx; 4], n_params: u8, child: u16 },
    Act      { action: ActionId,  params: [Fx; 4], n_params: u8 },
}

pub struct VmState {}                                     // Phase 3: empty. Phase 4: registers, pc. Hashed either way.

pub enum ActionStatus { Running, Success, Failure }

pub trait VmHost {                                        // the seam. Phase 4 keeps it (BLD-123). Hardware implements it later.
    fn eval_predicate(&mut self, id: PredicateId, params: &[Fx]) -> bool;
    fn run_action(&mut self, id: ActionId, params: &[Fx]) -> ActionStatus;
}

pub struct TickReport { pub ops_used: u32, pub exhausted: bool, pub root: ActionStatus }

pub fn run_tick(p: &CompiledPolicy, s: &mut VmState, host: &mut impl VmHost) -> TickReport;
```

`run_tick` walks the tree with an explicit fixed-size stack (depth cap 64 **[guess]**,
validated at load), allocates nothing, charges one budget unit per node visit, and stops
with `exhausted = true` when the budget is spent. Malformed trees (bad child index,
unknown id, over-depth) are rejected at load, never at run. Ids are validated against the
content registries at load (BLD-123's rule, adopted now). Serialization reuses the Phase 0
record format with `Fx` as raw bits.

### 3.2 `blindside-sim` — the entry point BLD-75 targets

```rust
// blindside-sim/src/policy.rs — a module that cannot name world.rs (module privacy + trybuild)
pub struct PolicyRunner {
    compiled: CompiledPolicy,
    vm: VmState,
    actions: ActionRuntime,          // motor-program state; hashed; belief-side, never truth
    overriding: Option<ActionId>,    // Recall: terminal, see §4.5
}

impl PolicyRunner {
    /// The one place a policy is evaluated. Takes &Belief. Never &World.
    pub fn evaluate(&mut self, b: &Belief, tick: Tick) -> Intent;
}
```

`evaluate` builds a host over `&Belief`, the predicate registry (BLD-97) and the action
runtime (BLD-99), calls `blindside_vm::run_tick`, and returns the `Intent` — motor command,
requests, and the runner's report — that the actuator, the modules and the fuse phase consume.

Reconciled 2026-09-06: the return type is ARCHITECTURE-RECONCILIATION §12's `Intent`, not a
separate `ActuatorRequests`, and `ActionRuntime` is that document's `NavState`, owned here
beside Belief rather than inside it. See PHASE-3-OPEN-QUESTIONS.md §20 and §21.

This is the concrete target for BLD-75's compile-fail tests:
`PolicyRunner::evaluate` and `Predicate::eval` accept `&Belief` and no type from
`world.rs`. ARCHITECTURE's `Policy::evaluate` should be renamed to this in BLD-61/BLD-112;
`Policy` (with `BtNode`) stays in `blindside-behavior`, Phase 4, and never enters the sim.

Per-tick order, phased over *every* agent by id before the next phase begins (BLD-107):
deliver commands → `PolicyRunner::evaluate(&belief)` for every agent → actuators apply and
requests take effect → world (ancients, hazards, wrecks, emitter expiry, mode step) → sensors
sample every agent against the one `&World` of this tick → belief updaters fuse → state hash.

Reconciled 2026-09-06: this said "for one agent, as Phase 1 had it" — the interleaved order,
under which the lower id always samples rivals at their stale positions and the sensing module
must hold `&World` and `&mut World` alternately. It becomes the phased order of
ARCHITECTURE-RECONCILIATION §20; see PHASE-3-OPEN-QUESTIONS.md §36.

### 3.3 Where the policies come from in Phase 3

The two reference policies are tree files (data), loaded by the harness, hashed, and
referenced from `MatchRecord.policies` by `policy_hash`. The harness refuses a record
whose resolved bytes do not hash to the ref (BLD-117's rule, adopted now). No Rust names
a predicate or action: adding a block is a data change, per DESIGN-PRINCIPLES §1.

## 4. Semantics that have to be decided now

### 4.1 Memoryless, evaluated every tick, pre-emptible

The tree is a pure function `Belief -> requests`, re-evaluated from the root every tick.
Leaves return Running / Success / Failure; Sequence stops at the first non-Success,
Selector at the first non-Failure; Guard runs its child if the predicate holds, else
Failure. A changed leaf pre-empts the running action immediately. An action's private
state (route index, escape timer, dwell clock) is reset when the action is entered;
anything that must survive de-selection is a fact in Belief (plan progress, which
believed places are finished, what the agent is currently doing).

This is Phase 2's `decide(belief) -> action` with two additions: evaluation every tick
rather than only at junction stops, and leaves that may finish instantly (§4.3). A
Phase 2 tree run this way makes the same choice at every junction; the one behavioural
difference is that `uncertainty > θ` flipping mid-passage turns the agent back at once
instead of at the next junction.

### 4.2 Actions are re-entrant motor programs in the sim

Steering, stuck detection, give-up timing (BLD-101), load retries, the shaft search: all
live inside actions, as they did in Phase 1 and as Phase 2's BLD-46 "motor programs" do.
`ActionRuntime` is per agent, belief-side, and part of the state hash because it affects
future ticks. Predicates cannot read it; what a policy may reasonably decide on (the
running action, since when) is mirrored into `Belief.self_report` (§4.4).

### 4.3 Two channels per tick

A tick may carry any number of instant module actions (ping, drop_beacon: Success at
once) and at most one locomotion action (Running). A second locomotion leaf in the same
tick returns Failure. Optional branches use a `noop` action that returns Success:

```
Selector
  Sequence
    Guard ping_ready(24 s)
      Guard unmapped_ahead(40 points)
        Act active_scan
  Act noop
```

Reconciled 2026-09-07: this example said `Act ping`; the action is `active_scan`, as §5's
trees and SENSORS D14 / §3.7 (ActionId 3) have it. See PHASE-3-OPEN-QUESTIONS.md §8.

`noop` is an ActionId in content, not a node kind, so ARCHITECTURE's `BtNode` set is
unchanged. Never exercised as a conflict in the reference trees (they are ordered to
avoid it), so nothing depends on the tie rule yet.

### 4.4 Memory lives in Belief, not in the tree

Phase 1's policy has timers and mode flags. Every one of them ported to a fact in Belief
plus a predicate with a window or threshold parameter:

| Phase 1 state | Tree form |
|---|---|
| `mode is HOME` latch | `Belief.self_report.current_action` + predicate `action_running(id)` |
| `investigate_until = t + 14` | `signature_within(window = 14 s, q ≥ 0.30)` over heard-sound history |
| `interfacing_until = t + 80` | the `interface` action's own dwell, plus `action_running(interface)` |
| `stage`, route index | `plan_progress` in Belief; `plan_remaining` predicate |
| `load_attempts`, nudged waypoint | inside the `load` action; place status ("done", "given up") in Belief |

How a fact gets there: the runner puts it in `Intent.report` and the fuse phase writes it
into `Belief.self_report`, like any other return. `ActionRuntime` itself (route index, escape
timer, dwell clock) stays outside Belief, owned by the runner, hashed with it, and unreadable
by predicates.

Reconciled 2026-09-06: this section said durable facts "live in Belief" without saying how
they get there, while `ActionRuntime` sits outside it; `Intent.report` **[guess: the channel]**
is the path, and ARCHITECTURE-RECONCILIATION §8 drops `nav` from Belief to match. See
PHASE-3-OPEN-QUESTIONS.md §21 and §29.

Consequence for BLD-116: neither reference policy needs VM-side registers if predicates
may read windows over Belief history and Belief self-reports the running action. That is
evidence for the ISA spike, not a decision of it.

### 4.5 Recall is the driver's, not the tree's

The player's one command must work whatever a policy author wrote — a market policy
that ignored Recall is a griefing vector, and DESIGN says the player "cannot drive", not
"can ask". On delivery the runner stops evaluating the tree for the rest of the match and
runs `abort_to_shaft` directly (Phase 1's blunt drive-then-spiral, BLD-105). The tree is
never consulted again: terminal, as BLD-105 requires.

### 4.6 Budget unit and exhaustion

Phase 3's unit is one node visit; the reference trees peak at 24. Default budget 256
node visits per tick **[guess]**, on the loadout as content data (BLD-98/BLD-120), so a
Phase 2-size tree (5 visits) and a reference tree (24) both fit with room for a market
policy several times larger. Exhaustion: the runner emits no locomotion request; the
actuator holds heading and sets speed to zero for that tick, and `TickReport.exhausted`
goes into the trace. BLD-116 suggested instead that "the last MotorCmd holds"; stopping
is chosen here because it is legible in a replay (the machine froze because its policy
was over budget) and cannot walk an agent into rock. Neither reference tree ever
exhausts, so Phase 3 replays are unaffected whichever Phase 4 settles on. Phase 4 will
re-express the budget in bytecode ops; that is a content change and changes the content
hash, which is the loud failure BLD-26 wants.

## 5. How the Phase 1 policies are expressed

Rendered from the prototype. Parameters are Phase 1's tuning values.

**Cautious (the Phase 1 player):**
```
Sequence
  Selector                                   # emission channel
    Sequence
      Guard ping_ready(24.0)
        Guard unmapped_ahead(40)
          Act active_scan
    Act noop
  Selector                                   # locomotion channel
    Guard at_unfinished_place(shaft, r)
      Act hold
    Guard signature_within(1.0 s, q>=0.45)
      Act hold                               # freeze while the machinery is loud
    Guard at_unfinished_place(deposit, 12 cells)
      Act load
    Sequence                                 # once lost, stay on the way home
      Selector
        Guard uncertainty_gt(16.0)  -> Act noop
        Guard action_running(return_chain) -> Act noop
      Act return_chain
    Sequence
      Guard cargo_lt(2)           -> Act noop
      Guard plan_remaining(7)     -> Act noop
      Selector
        Sequence
          Guard beacon_due(45 cells)
            Act drop_beacon
        Act noop
      Act survey                             # stands in for take_branch on Phase 1's a-priori routes
    Act return_chain
```
For a lidar loadout the emission channel is `Guard ping_ready(1.5 s) -> Act active_scan`
(silent sweep on a period); the rest is identical.

Reconciled 2026-09-06: both trees say `active_scan`, not `ping` — the action is the request
and the fitted module answers with sound or light (SENSORS D14) — and `wait` is written `hold`,
since it folds into `hold` rather than taking an ActionId of its own. See
PHASE-3-OPEN-QUESTIONS.md §8.

**Aggressive (the Phase 1 rival):**
```
Sequence
  Selector
    Sequence
      Guard ping_ready(8.0)
        Act active_scan
    Act noop
  Selector
    Guard at_unfinished_place(shaft, r)
      Act hold
    Sequence                                 # arrive, or hear it loud, then stay 80 s
      Selector
        Guard at_unfinished_place(machinery, 5 cells) -> Act noop
        Guard signature_within(1.5 s, q>=0.60)        -> Act noop
        Guard action_running(interface)               -> Act noop
      Act interface
    Guard signature_within(14 s, q>=0.30)
      Act investigate                        # walk toward the bearing
    Guard at_unfinished_place(deposit, 12 cells)
      Act load
    Sequence
      Guard plan_remaining(11) -> Act noop
      Selector
        Sequence
          Guard beacon_due(45 cells)
            Act drop_beacon
        Act noop
      Act survey
    Act return_chain
```

`survey` walks Phase 1's hand-authored route list; in Phase 3's generated caves it is
`take_branch` (Phase 2's left-most unexplored passage) and `plan_remaining` is
`unexplored_branch_exists`. `cargo_lt(n)` is Phase 2's `carrying_cargo` (PredicateId 3) with
the bay capacity as its threshold, guarding the not-yet-full branch as §2.3 uses it, and
`return_chain` is `return_to_beacon` (ActionId 2), which retraces `Belief.chain`. Nothing
else in either tree is Phase 1-specific.

Reconciled 2026-09-07: both trees guarded on `at_shaft`, which §7 folds into
`at_unfinished_place(shaft, r)` and which has no id of its own in SENSORS §3.6; and
`cargo_lt` and `return_chain` are mapped to their registry blocks here, as `survey` and
`plan_remaining` already were. See PHASE-3-OPEN-QUESTIONS.md §8.

## 6. How Phase 2's induced trees are expressed

Phase 2 induces a minimal separator over its block list with a fitted θ. As a FlatTree:

```
Selector
  Guard carrying_cargo             -> Act return_to_beacon
  Guard uncertainty_gt(θ)          -> Act return_to_beacon
  Guard unexplored_branch_exists   -> Act take_branch
  Act return_to_beacon
```

Five nodes, five visits per tick. The Phase 2 Python renders the tree already; the only
addition needed is to also dump it as a node list with block names, which the Phase 3
harness maps to `PredicateId`/`ActionId` through the registries. Phase 4's
`blindside-induct` (BLD-137) then emits the same artifact natively.

## 7. The vocabulary the reference policies need

BLD-97 says the Phase 3 predicate vocabulary is Phase 2's and "do not expand it"; BLD-99
lists take_branch, return_to_beacon, ping, drop_beacon, load, abort_to_shaft (+interface
from BLD-103, spoof from BLD-106, gait from BLD-100). BLD-102 asks the same phase for
reference policies that freeze on the signature, investigate it, ping on a rule and load.
Those two stories cannot both be satisfied; §2.3 measures what giving up the second costs.

Extra blocks the trees above use, beyond Phase 2's:

| Predicate | Reads | Where it comes from |
|---|---|---|
| `signature_within(window, q_min)` | heard-sound history (BLD-89 retains arrivals) | BLD-97's candidates "signature quality ≥ θ" and "heard within N s", merged |
| `at_unfinished_place(kind, radius)` | believed places and their belief-side status | new; needed to choose `load`/`interface` at all |
| `ping_ready(cooldown)` | `ticks_since_ping` | BLD-97 candidate |
| `unmapped_ahead(n)` | map point count ahead | Phase 1's cautious ping discipline |
| `beacon_due(cells)` | distance since last drop | new |
| `at_shaft` | self-report | folded into `at_unfinished_place(shaft, r)`; not a block of its own |
| `action_running(id)` | `self_report.current_action` | new; the latch (§4.4) |

| Action | Notes |
|---|---|
| `hold` | freeze in place; could later be `gait(stop)` (BLD-100 is P2) |
| `investigate` (approach a contact bearing) | generic "walk toward a bearing" |
| `wait` | folded into `hold`; the trace text is not worth an ActionId |
| `noop` | the optional-branch idiom (§4.3) |

Six predicates and three actions, so the Phase 3 reference vocabulary is about nine
predicates and twelve actions (SENSORS §3.6, §3.7), not 3 + 2. They are ordinary blocks with
stable ids; whether players see them on day one or behind a season flag (ARCHITECTURE rule 5)
is the designer's call and does not affect the batch. R5 (vocabulary size) is still answered
by Phase 2's gate, not by this.

Reconciled 2026-09-06: seven predicates became six (`at_shaft` folds into
`at_unfinished_place`) and the actions are `hold`, `investigate` and `noop` (`wait` folds into
`hold`); SENSORS D13 flips from "reserve" to "assign" and gives them numbers after BLD-59's
additions. See PHASE-3-OPEN-QUESTIONS.md §8.

## 8. The representativeness risk, and how C bounds it

The risk BLD-62 names: policies that drive the Phase 3 gate are not the policies the VM
will run, so the gate proves determinism of the wrong thing and the replays die at Phase 4.

Under C the reference policies *are* the artifact the VM will run: the same node kinds,
ids, params, budget and host calls. Phase 4 swaps the interpreter body for bytecode and
proves, by BLD-125's differential test on the same trees, that the bytecode makes the same
decision as the tree-walker — which is the Phase 3 interpreter, kept as the oracle. Then
the Phase 3 MatchRecords are re-run under the VM (BLD-124's "re-run the Phase 3 gate
mechanism with the VM in the loop") with a concrete pass criterion: identical final
hashes. A mismatch is a VM bug or a deliberate content-hash bump, never a silent drift.

What C does not cover:
- Budget accounting changes unit (visits → ops). Loud by construction (content hash).
- VM registers (if BLD-116 adds them) are unused by Phase 3 trees; Phase 4 policies that
  use them have no Phase 3 form, which is fine in that direction.
- Subtree inlining and provenance are not exercised until Phase 4.
- Phase 3's per-tick trace is node visits; Phase 4's is BLD-128's fuller shape.

Under A none of this holds: the references would be Rust closures with arbitrary memory,
BLD-130's baseline would be something the node editor cannot express, and a challenger
losing the Phase 4 gate could not be told apart from an unfair baseline — the exact
misattribution BLD-113's kill criterion warns about.

## 9. What Phase 4 replaces, what it keeps

| Keeps | Replaces |
|---|---|
| `VmHost`, `CompiledPolicy` envelope (schema, budget, policy_hash), `run_tick` signature, `TickReport` | `run_tick`'s body: tree walk → bytecode interpreter (BLD-119) |
| `PolicyRunner::evaluate` in `blindside-sim`, `ActionRuntime`, registries, the Recall override | `VmState` grows registers/pc and joins the hash (BLD-124) |
| The two reference trees, now BLD-130's "hand-written" baseline by definition | Budget unit and the content entries that carry it (BLD-120) |
| The tree-walker, moved to test-only as BLD-125's oracle | `FlatTree` becomes the compiler's output from `Policy`/`BtNode` (BLD-121/125), gaining `Subtree` |
| Harness policy loading and the policy_hash refusal rule (BLD-117) | Trace shape (BLD-128) |

## 10. Cost relative to BLD-102

BLD-102 is costed at 2 d for "policy driver + two reference policies + VM stub".

| Work | Days |
|---|---|
| `blindside-vm`: FlatTree, `run_tick` with fixed stack and budget, `VmHost`, load-time validation, serialization, golden tests on three platforms | 1.5 |
| `blindside-sim`: `PolicyRunner`, host over Belief + registries, `ActionRuntime` state and hashing, Recall override, exhaustion behaviour | 1.0 |
| Reference trees as data, harness loader, policy_hash check | 0.5 |
| BLD-102's last criterion: two-policy match bit-identical on three platforms | 0.5 |
| **Total** | **3.5 d, +1.5 d** |

Offsets later: BLD-123 (3 d) mostly done; BLD-125 (4 d) starts with its oracle; BLD-117
(1 d) is largely this decision; BLD-130's "what counts as hand-written" round-trip is
gone. Net over Phases 3 and 4 about −1 d **[guess]**. Action implementations (BLD-99,
BLD-101, BLD-103's interface) and predicate implementations (BLD-97) are their own
stories under any option and are not in this table.

## 11. Decisions

**D1. Phase 3 agents are driven by a data-driven tree interpreter in `blindside-vm`,
behind the `VmHost` seam; not hand-written Rust, not a bytecode VM pulled forward.**
Reason: §2 shows the two Phase 1 temperaments port to tree data with the beats intact,
at ≤24 node visits per tick; it is the artifact Phase 2 emits and Phase 4 compiles. Cost
if wrong: 1.5 d over BLD-102, and Phase 4 throws away a ~150-line interpreter it would
have written anyway as a test oracle.
Designer: [ ] yes [ ] no

**D2. Placement as §3: `CompiledPolicy`/`FlatTree`/`VmHost`/`run_tick` in `blindside-vm`;
`PolicyRunner::evaluate(&Belief)` in `blindside-sim/src/policy.rs` is the BLD-75 target;
`Policy` with `BtNode` stays in Phase 4's `blindside-behavior`.** Reason: keeps
`blindside-sim`'s dependency list at vm + content and gives BLD-75 a concrete symbol. Cost
if wrong: a rename in ARCHITECTURE and one trybuild case.
Designer: [ ] yes [ ] no

**D3. Tree semantics as §4.1: memoryless, evaluated from the root every tick, leaves
return Running/Success/Failure, a changed leaf pre-empts at once, action state resets on
entry, durable facts live in Belief.** Reason: it is Phase 2's decision tree plus the
minimum needed to run continuously; measured leaf changes are once a minute, so per-tick
evaluation costs nothing. Cost if wrong: Phase 2 trees replayed in Phase 3 may turn back
mid-passage where the demonstration turned at the next junction; the fix is an
"uninterruptible until done" flag on `take_branch`, action-side, no schema change.
Designer: [ ] yes [ ] no

**D4. Two channels per tick and `noop` as an ActionId (§4.3).** Reason: lets "ping then
keep driving" be written without a new node kind. Cost if wrong: Phase 4 adds a decorator
node and the compiler folds `noop` away; the reference trees gain nothing and lose
nothing.
Designer: [ ] yes [ ] no

**D5. Recall is a terminal driver-level override, never a tree node (§4.5).** Reason:
the player's one command cannot depend on the policy author's goodwill. Cost if wrong: if
the designer wants policies to *react* to Recall (e.g. drop cargo first), a `recalled`
predicate is added and the override becomes a default rather than a rule — a day.
Designer: [ ] yes [ ] no

**D6. `Belief.self_report` carries the running action id and its start tick, and
`action_running(id)` is a predicate.** Reason: the only latch a memoryless tree has;
needed by both reference policies (§2.4, §4.4). Cost if wrong: without it the cautious
agent oscillates home/survey whenever a beacon fix collapses sigma on the way home
(measured rare on Phase 1, certain on Phase 3's chain); the alternative is VM registers,
which is BLD-116's question and not available in Phase 3.
Designer: [ ] yes [ ] no

**D7. Budget unit is node visits, default 256 per tick on the loadout as content data;
exhaustion stops the agent for that tick and is reported in the trace (§4.6).** Reason:
measured peak of 24 for the reference trees; stopping is legible and safe. Cost if wrong:
Phase 4 changes the unit anyway; if the designer prefers BLD-116's "last command holds",
it is a one-line change with no effect on Phase 3 replays.
Designer: [ ] yes [ ] no

**D8. The six predicates and three actions in §7 are registered as real
blocks with stable ids for BLD-102's reference policies, as an explicit expansion of
BLD-97's "do not expand" for Phase 3's batch coverage; whether players get them on day
one or behind a season flag is a separate content call.** Reason: §2.3 measures the
alternative: the rival's machinery death becomes path luck at 2/8 and the cautious agent
cannot freeze, so the batch stops exercising the signature-to-decision path by policy.
Cost if wrong (designer says no): the beat-sheet seed in BLD-108 must be produced by a
reflex hidden inside an action, which PHASE-2-OPEN-QUESTIONS (c) warned against, and
BLD-130's requirement that the baseline read a contact predicate has nowhere to go.
Designer: [ ] yes [ ] no

**D9. Phase 3's MatchRecords are re-run under the Phase 4 VM as part of BLD-124, with
identical final hashes as the pass criterion (§8).** Reason: this is the sentence that
turns "representativeness risk" into a test. Cost if wrong: none in Phase 3; in Phase 4
a mismatch is found late instead of on the first VM commit.
Designer: [ ] yes [ ] no

**D10. BLD-102 is re-costed at 3.5 d (+1.5 d) with the offsets in §10 noted on BLD-117,
BLD-123, BLD-125 and BLD-130.** Reason: honest accounting; the plan's velocity figures
are what the designer steers by. Cost if wrong: 1.5 d.
Designer: [ ] yes [ ] no

**D11. Phase 2's tree render also writes the induced tree as a node list with block
names (a few lines in the Phase 2 Python), so Phase 3's harness can load it.** Reason:
§6; it makes "Phase 2's trees run in Phase 3" a file copy rather than a reconstruction.
Cost if wrong: BLD-136 reconstructs from the Phase 2 report; half a day, later.
Designer: [ ] yes [ ] no

Ready-to-paste text for the ROADMAP Phase 4 notes and ARCHITECTURE, once D1 is a yes
(neither file was edited by this spike):

> Phase 3 drove its 1,000-match gate with a memoryless behaviour-tree interpreter in
> `blindside-vm` behind the `VmHost` seam, executing `CompiledPolicy { FlatTree,
> VmBudget }` via `blindside_sim::policy::PolicyRunner::evaluate(&Belief)`. Both
> reference policies are tree data over the registries (docs/spikes/AGENT-DRIVER.md §5).
> Representativeness risk: the Phase 4 bytecode VM must make the same decisions as that
> interpreter on the same trees (BLD-125 differential test, the interpreter kept as
> oracle), and Phase 3's MatchRecords must re-run to identical final hashes under it
> (BLD-124). Budget unit changes from node visits to ops in Phase 4; that is a content
> change and changes the content hash.

## 12. Guesses, limits, and how to re-run

**Guessed:** default budget 256 visits; depth cap 64; params `[Fx; 4]` (taken from
ARCHITECTURE); exhaustion = stop; `noop` as an action rather than a node kind; the cost
figures in §1 and §10; that `hold` is an action rather than a gait (§7 folds `wait` into
`hold`, which takes no ActionId of its own).

Reconciled 2026-09-07: the guess was "that `hold`/`wait` stay separate actions rather than a
gait"; §7 and SENSORS §3.7 fold `wait` into `hold` (ActionId 10) and give `wait` no number.
See PHASE-3-OPEN-QUESTIONS.md §8.

**Limits of the evidence:** Phase 1's cave is hand-authored with a-priori routes, so
`survey` stands in for `take_branch`; eight seeds; Python floats; the belief-side facts
(`plan_progress`, place status, `current_action`, last-loud timestamps) were attached to
Phase 1's `Belief` object rather than designed into it; the hand-written and tree paths
diverge after the first heard signature because `investigate` is a separate leaf in the
tree, so per-seed outcomes beyond the first three minutes should be read as "same
distribution", not "same match".

**Prototype:** session scratchpad, `treeproto/` (`tree.py` interpreter, `predicates.py`,
`actions.py` — Phase 1's motor programs ported verbatim —, `treepolicy.py` the two trees
as data, `run.py`, `compare.py`). It is throwaway and is not committed; say the word and
it goes under `spikes/agent-driver/`. Re-run from the repo root:

```
.venv/Scripts/python.exe <scratchpad>/treeproto/run.py --seed 7 --show-trees
.venv/Scripts/python.exe <scratchpad>/treeproto/run.py --seed 7 --recall 300
TREE_MINIMAL=1  ...  (Phase 2 vocabulary only)      TREE_NO_LATCH=1 ... (no action_running guard)
.venv/Scripts/python.exe <scratchpad>/treeproto/compare.py norecall
```

Baselines came from `python -m phase1 --headless --seed N [--recall 300]
[--player-sensor lidar]` on tuning.py as committed at HEAD (66ebb20), whose "Measured:" notes the board
cites.
