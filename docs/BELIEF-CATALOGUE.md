# The belief catalogue

Everything a machine's own estimator could publish to a policy, what each one costs, and what
technique each one makes possible that the six predicates in `phase1/blocks.json` cannot express.

Written 2026-09-09 against `DESIGN-PRINCIPLES.md` §9, which is the specification:

> We also need to make as much data available (in the vehicle belief) as possible so players can
> experiment with different techniques that utilize different data inputs.

§9 also states why this is safe and what it costs, and neither is repeated here. What is repeated,
because everything below depends on it: **a policy may never read `World`; `Belief` is by
construction not `World`; so nothing in this document can break the invariant.** One proposal in
here breaks it anyway, for a reason worth knowing about — C11 — and it is refused.

This is a catalogue, not a plan. It is organised so the designer can strike rows and a programmer
can implement the ones that survive. Nothing here is assigned.

---

## 0. What is actually true today

Six statements, each checked against the code rather than against the design documents. They
change where the work is, so they come first.

**0.1 `Belief` is not thin. The predicate surface is.** §9 says the estimator "exposes a pose, an
uncertainty scalar and a point cloud, and throws away most of what it computed on the way." The
first half is not right, and the correction matters. `phase1/belief/belief.py` already carries
about thirty-five fields and six query methods — the fix history, the contact list, the beacon
records and their drop order, the trail, two bearing trackers, four distance integrals, three
sensor-event streams, a log. The six predicates under `phase1/policy/predicates/` read **seven of
those forty-one things**: `cargo`, `survey.deposits`, `tried_deposits`, `t`, `sigma_pos()`,
`fixes`, `signature`.

So the first tranche of this catalogue is not new sensing, and mostly not even new computation.
It is naming.

**0.2 The motor layer already reads three times what the tree can, and everything it reads is
legal.** `phase1/policy/motor/driver.py` steers on `recent_near` and `cloud.clearance()`
(`driver.py:191–227`), gives up on a waypoint by a stall clock and an escape count
(`driver.py:36–43`, `:165–188`), scans thirty-six headings for the longest open line
(`driver.py:229–261`), and decides whether to ping from `points_ahead()` and `ticks_since_ping`
(`driver.py:272–283`). `JamClock` (`jam_clock.py:23–43`) knows to the tick how long the body has
failed to cover ground. None of it reaches a predicate. All of it is belief-derived, so all of it
is publishable at the cost of moving a field.

**0.3 What genuinely is discarded lives upstream and downstream of `Belief`, not inside it.** The
sensor rig knows it is deafened by its own transmission (`sensor_rig.py:43`, `:61`) and never says
so. It knows how many rays it fired and how many came back, and forms no count. The motor layer
knows the stall clock and the escape count and holds them in a `Driver` that is thrown away when
the tree picks a different action. Publishing these is plumbing in two directions, not a new
estimator.

**0.4 The most expensive line in this document is one word in `point_cloud.py`.** The occupancy
grid is `occupied: bool` over 170×130 two-cell bins (`point_cloud.py:17–20`, `:46–49`). It has two
states, and "not occupied" conflates *observed and free* with *never looked at*. `clearance()`
(`point_cloud.py:108–129`) therefore reads unobserved space as open — which is right for steering
and useless for exploration. **Frontiers, free area, staleness and coverage all need a third cell
state, and a third state means marking every cell a beam passed through, not only the one it
stopped in.** That is the single largest new cost in this catalogue, it is shared by four signals
in family C, and it is not optional: `CAVE-BLOCKS.md` §7 guess 11 already commits that
`deposit_remaining` becomes an exploration block in Phase 3, when a generated cave hands out no
survey. Something has to answer *is there anywhere left to go*, and only free space can.

**0.5 A damage effect is currently invisible to belief, and the code says so in its own words.**
`sensor_rig.py:98–107`:

> `reach` is the nominal range times `me.sensor_range_multiplier` — 30.0 cells unhurt, 22.6 at the
> 0.493 dose the 5:41 near miss delivers. The far returns stop arriving; the ones that still
> arrive are scored for quality against the NOMINAL range … So the map stops growing ahead of the
> machine and **no number anywhere on the belief side changes to explain why**.

Two free counters — how many returns came back this sweep, and how far the furthest one was — make
that visible. They are the cheapest signals in the catalogue and they close a hole the build
already knows it has.

**0.6 The induction refuses more than eight predicates.**
`crates/blindside-induct/src/tuning.rs:30` sets `MAX_PREDICATES = 8`, and `induce.rs:90` rejects a
block *list* longer than that — the list, not the enabled subset. This is the hard constraint on
§5's day-one recommendation, and it is also the structural argument for §9's two layers: **the
block list can never be the vocabulary, because the thing that learns from demonstrations cannot
search one.** The substrate has to be reached another way. §6 asks that as a question with a
default.

---

## 1. How to read the catalogue

**A signal is a number or a small tuple published on `Belief`. A block is a named threshold test
over one signal.** That distinction is §9's two layers made mechanical: the substrate publishes
values, the curated layer names tests. `uncertainty_exceeds` is a block; `sigma_pos` is the signal
under it; and `sigma_along`, `sigma_cross` and `sigma_heading` are three more signals under
nothing at all.

### 1.1 Columns

| column | values |
|---|---|
| **origin** | `kept` — computed today, then discarded or never published to a policy. `derived` — O(1) or O(small) from state already stored. `new` — genuinely new work: a new accumulator, a new grid channel, or a new pass. |
| **fx** | `y` — fixed-point safe as written. `y*` — safe with a precision or overflow caveat, stated in the family's determinism note. `!` — flagged; see §7. |
| **cost** | `free` / `cheap` / `real` / `heavy` / `refused`, defined in 1.2. |
| **layer** | `D1` — recommended as a day-one base block. `L` — a later block, arriving the way `DESIGN-PRINCIPLES.md` §1 says blocks arrive. `S` — substrate only: published and readable, never named as a block unless someone asks. |

The last column, *what it unlocks*, is the one that matters. A signal that enables no technique the
current six predicates cannot already express has not earned a row, and the ones that failed that
test are named in §4 rather than quietly left out.

### 1.2 The cost model, and its arithmetic

`PHASE-3-OPEN-QUESTIONS.md` §19 fixes 20 Hz and gives the batch gate as 1,000 matches × 9,600 ticks
in 600 s = **62.5 µs per tick, single-threaded, for the whole match**. §37 spends 10 µs of that on
acoustics. §38 puts four agents in the benchmark cave. So one agent's entire share — sensors,
belief, policy, actuator — is about **13 µs per tick**.

**My working envelope for everything this catalogue adds is 2 µs per agent per tick**, roughly
2,000 integer operations. That number is mine and it is the most consequential guess in the
document (guess 1). Against it:

| tier | meaning | ops | verdict |
|---|---|---|---|
| `free` | a counter, a comparison or a running max folded into a loop that already runs | < 20 | hundreds of these fit |
| `cheap` | O(returns this tick), or O(a fixed set ≤ 64) | 50–500 | a handful fit |
| `real` | O(local bins), a trig call, or a route plan | 500–5,000 | one or two, cached or on a cadence |
| `heavy` | O(map points) or O(whole grid) | ≥ 20,000 | **illegal every tick.** Incremental or rolling only |
| `refused` | unbounded, or needs something belief does not have | — | not published |

Two multipliers make these numbers unstable, and both are unsettled:

- **The return rate.** Phase 1's lidar returns 76 per sweep every 30 ticks. A real scanning sensor
  at `DESIGN-PRINCIPLES.md` §8's parameters returns ~23,000 per revolution at 10 Hz — about 11,500
  per 20 Hz tick, 150× more. `spikes/godot/cloud/LIDAR.md` §6 says the accumulated map must be
  voxel-downsampled at source and calls the factor "a `Belief` design question … that should be
  settled before anything depends on the point count." **It still is not settled**, so every
  per-return cost below is quoted per 100 returns and the multiplier is somebody else's decision.
- **The grid.** 170×130 = 22,100 bins in Phase 1; the Phase 3 benchmark cave is 400×240 (§38), so
  ~24,000 bins at the same 2-cell binning. One whole-grid sweep is twelve times the envelope.
  **No whole-grid aggregate may be computed every tick.** It is maintained incrementally by the
  writes, or swept on a rolling schedule — 1/16th per tick is 0.8 s of lag — and the lag has to be
  stated wherever it changes what the signal means.

### 1.3 Four rules every published signal obeys

1. **Fixed point, ticks, no seconds.** `DETERMINISM.md` rules 1 and 3;
   `PHASE-3-OPEN-QUESTIONS.md` §19 forbids seconds inside the constrained crates. Everything the
   catalogue calls "how long" is `Ticks`.
2. **Hashed, or recomputed from hashed state.** A published signal is state a policy reads, so it
   is either in the state hash or derived on demand from something that is. A cached aggregate
   that is neither is a desync waiting for month fourteen. §14 already excludes the occupancy bins
   as derived; the same discipline applies to every accumulator here.
3. **No iteration-order dependence; ties break by stable id.** `DETERMINISM.md` rules 2 and 6.
   This bites hardest in family D, where every signal is a nearest-neighbour query and a tie
   between two equidistant map points must not be settled by which bin was visited first.
4. **Any sampling uses the counter-based RNG.** `DETERMINISM.md` rule 4. Two signals below are
   only affordable computed over a sample of the returns; a sample drawn from a stateful stream
   desyncs the moment call order changes, and `draw(seed, tick, entity, purpose)` cannot.

---

### 1.4 What is in here

One hundred signals in ten families. By origin:

| origin | count | |
|---|---:|---|
| `kept` | 41 | of which **35 are computed today and read by no policy**; six are what the current six predicates already read |
| `derived` | 36 | O(1) or O(small) from state already stored |
| `reserved` | 8 | already in the Phase 3 schema (`PHASE-3-OPEN-QUESTIONS.md` §16, §24, §29, §33) and read by nothing |
| **`new`** | **14** | genuinely new work — a new accumulator, a new grid channel, or a new pass |
| `refused` | 1 | C11, and the reason is worth reading |

**So eighty-five of a hundred cost no new sensing and almost no new computation.** §9's central
claim holds and then some: the expensive part of this is not measuring more, it is refusing to
discard, and then naming what survives. The fourteen `new` signals are where the argument is.

By layer: 10 signals carry a `D1` mark, 2 more are day-one candidates, 47 are later blocks and 40
are substrate only. Ten `D1` signals make **eight** day-one predicates in §5, because
`last_fix_jump` and `max_fix_jump_window` are two readings of one block, and `deposits_tried` and
`frontier_count` are the same block on either side of the Phase 3 survey going away. ‡ marks the
one signal I would have made a day-one block and could not — see §5.2.

---

## 2. The catalogue

### A — Pose and its uncertainty

Today the estimator computes three sigmas and publishes one. `belief.py:93–106`:

```
sigma_along  = 0.5 + 0.038·d
sigma_theta  = 0.02 + 0.0013·d
sigma_cross  = 0.5 + 0.5·d·sigma_theta   =  0.5 + 0.010·d + 0.00065·d²
sigma_pos    = hypot(along, cross)
```

where `d` is `dist_since_fix`. `uncertainty_exceeds` reads `sigma_pos()` and nothing else reads
anything. **The two axes grow differently and they cross:**

| cells since a fix | σ along | σ cross | which dominates |
|---:|---:|---:|---|
| 20 | 1.26 | 0.96 | along-track |
| 43 | 2.13 | 2.13 | **they cross** |
| 100 | 4.30 | 8.00 | cross-track, ~2× |
| 200 | 8.10 | 28.5 | cross-track, ~3.5× |

Below about forty-three cells a machine is mostly wrong about *how far it has come*; above it,
mostly wrong about *which side of the passage it is on*. Collapsing that into one scalar throws
away the distinction, and it is the distinction that decides what a machine should do about it —
you fix along-track error by counting things, and cross-track error by touching a wall.

| signal | what it means to the player | origin | type / units | fx | cost | layer | what it unlocks |
|---|---|---|---|---|---|---|---|
| `pose` | where it thinks it is | kept | `Vec2Fx` cells, belief frame | y | free | S | Nothing new by itself, and it invites brittle policies — see §4. Published because everything else is relative to it. |
| `heading` | which way it thinks it is pointing | kept | `Fx` rad | y | free | S | as above |
| `sigma_along` | how wrong it could be about how far it has come | kept (`belief.py:93`) | `Fx` cells | y | free | S | *Count junctions, do not measure distance.* A machine that stops trusting odometry before it stops trusting its lateral position navigates by landmarks instead of by dead reckoning — a different animal from one that reads `sigma_pos`. |
| `sigma_cross` | how wrong it could be about which passage it is in | kept (`belief.py:96`) | `Fx` cells | y | free | S | *Hug a wall when cross-track error passes half a passage width.* The error that puts a machine down the wrong branch, made separately visible. |
| `sigma_heading` | how wrong it could be about which way it is facing | kept (`belief.py:57`, grown `:150`) | `Fx` rad | y | free | **L** | **The error a fix never corrects.** `HEADING_FIX_GAIN = 0.0` (`tuning.py:54`) and §13 confirms a beacon fix changes heading by exactly zero, so heading error is monotone for the whole match. A machine that turns back on heading is turning back on the only quantity that never improves — and it is unreachable today. |
| `sigma_pos` | how lost it thinks it is | kept, published | `Fx` cells | y | free | **D1** | the existing `uncertainty_exceeds` |
| `sigma_shape` | is my error a cigar or a circle | derived | `Fx` ratio | y | free | S | Corridor degeneracy, felt from the inside. A long straight drive produces a cigar; a chamber crossing does not. `THE-SENSOR-AND-SLAM.md` §3.2 makes degeneracy the generator's lever against SLAM; this is the machine noticing it without SLAM. |
| `error_axis` | which way the error points | kept (`belief.py:102–106`) | `Fx` rad | y* | free | S | *Approach a beacon across the long axis of the ellipse, not along it.* Turns re-acquisition into a geometry problem instead of a distance problem. |
| `epoch_age` | how long the current ellipse has been growing | kept (`epoch_t`) | `Ticks` | y | free | S | see E1, which is the same clock and the one to block on |
| `sigma_growth` | am I getting lost faster than I usually do | derived | `Fx` cells/100 cells | y | cheap | S | Detects a chassis that is slipping or limping before self-report says so; pairs with B8. |

**Determinism.** All safe. `error_axis` is `atan2` from `fxmath.rs` (§35) and therefore costs a
trig call, not a subtraction — that is why it is `y*` and not free-with-no-caveat. Nothing here
needs a covariance matrix; §15 already settled that three sigmas and an epoch is the
representation, and a 3×3 EKF in fixed point is refused there for reasons this document agrees
with.

**What the family makes possible that the six cannot.** Today there is exactly one way to be lost.
With the axes split there are four different machines: one that turns back on total error, one
that turns back when it can no longer trust *distance*, one that turns back when it can no longer
trust *heading* — the error that never gets fixed — and one that reads the shape of the error and
changes how it navigates rather than whether it continues.

---

### B — Odometry and motion

| signal | what it means to the player | origin | type / units | fx | cost | layer | what it unlocks |
|---|---|---|---|---|---|---|---|
| `dist_since_fix` | how far it has walked since anything told it where it was | kept (`belief.py:54`) | `Fx` cells | y | free | S | The legible twin of `sigma_along` — and today an exact affine reparametrisation of it, so blocking both is one block twice. See §4. They separate the moment terrain-relative navigation lands or the sigma model gains a second term. |
| `dist_total` | how far it has walked at all | kept (`belief.py:56`) | `Fx` cells | y | free | S | a denominator for B11, and the odometer a power model would bill against |
| `dist_since_drop` | how far since it last put a beacon down | kept (`belief.py:75`) | `Fx` cells | y | free | **L** | **Moves a motor constant into the player's hands.** The 45-cell drop cadence is `tuning.py:139` and `CAVE-BLOCKS.md` §4 explicitly keeps it out of the block set. With this signal and a `drop_beacon` action, chain density becomes a taught trade against a finite rack (`SENSORS-AND-IDS.md` module 4, six beacons) — thin chain and deep, or dense chain and shallow. |
| `speed_measured` | how fast it is actually going | derived | `Fx` cells/tick | y | free | S | |
| `turn_rate` | how hard it is turning | derived | `Fx` rad/tick | y | free | S | |
| `moving` | is it actually covering ground | kept (`jam_clock.py:30`) | bool | y | free | S | the boolean under B6 |
| `ticks_stuck` | how long since it last covered ground | kept (`jam_clock.py:26`) | `Ticks` | y | free | **L** | **The second motor constant to become a decision.** `STUCK_SECONDS 5` + `ESCAPE_SECONDS 9` × 4 (`tuning.py:447–449`) is 28 s before a waypoint is abandoned, and `CAVE-BLOCKS.md` §4 says nobody should have to demonstrate it. That was right for *how to escape a wall*; it is wrong for *when to stop trying and go home*, which is a temperament. |
| `slip` | it is asking to move and not moving | **new** | `Fx` ratio 0–1 | y | free | S | Needs the commanded speed on the belief side; §21's `Intent.report` is the channel and no new sensing is involved. Distinguishes *wedged* from *walking slowly through water* from *dragging a full hold* — and on real hardware it is the classic sign of a lost wheel, which is why it belongs in the interface now rather than later. |
| `escapes_this_leg` | how many times it has had to back out of something | kept (`driver.py:39`) | `u16` | y | free | **L** | *This route is wrong; stop working the problem.* The skip-after-four rule (`driver.py:174`) becomes a taught number, and a machine that gives up on a route after two escapes is a genuinely different animal from one that grinds. |
| `escapes_total` | how much of the match has been spent stuck | kept | `u16` | y | free | S | |
| `wander_ratio` | walked a long way, got nowhere | derived (`dist_since_fix` ÷ straight-line from epoch) | `Fx` ratio | y | free | **L** | **Loop detection with no SLAM and no map lookup.** Eighty cells walked, six cells moved, is circling — the exact behaviour a spoofed machine shows while loitering between anchors. Two integrals and a divide. Cheapest genuinely new capability in the catalogue. |

**Determinism.** All safe. `wander_ratio` divides by a displacement that can be near zero; clamp
the denominator at one cell and publish the ratio saturated, rather than letting a divide blow up
near the epoch.

**What it makes possible.** Three things the current set cannot say at all: *give up on a route*,
*notice you are going in circles*, and *drop beacons on a rule of your own*. All three are things
the motor layer currently decides on the player's behalf.

---

### C — The map itself

Read 0.4 first. The signals split cleanly into ones the two-state grid can already answer and ones
that need a third state.

| signal | what it means to the player | origin | type / units | fx | cost | layer | what it unlocks |
|---|---|---|---|---|---|---|---|
| `map_points` | how much it has mapped | kept (`cloud.n`) | `u32` | y | free | S | a denominator; also the *"my map has stopped growing"* tell when read as a rate |
| `points_ahead(r)` | is there anything on the map in front of me | kept, motor-only (`belief.py:268`, used `driver.py:282`) | `u32` | y | cheap | **L** ‡ | **Makes *do I ping?* teachable.** The glossary calls it the central decision of a match; `CAVE-BLOCKS.md` §4 concedes it is a cooldown today. Reserved as `unmapped_ahead` (`SENSORS-AND-IDS.md` PredicateId n+4). With an `active_scan` action beside it, the loud/quiet trade becomes a rule a player writes instead of a loadout number. |
| `clearance(heading)` | how far the map is open that way | kept, motor-only (`point_cloud.py:108`) | `Fx` cells | y | real | S | the first signal that reads *shape* rather than *quantity*; the substrate under C4 and C5 |
| `passage_width` | how wide it is where I am standing | derived (two opposed `clearance` rays) | `Fx` cells | y | real | **L** | **Makes the chassis width classes a belief property.** §25 gives cells four width classes and each chassis an enter class and a turn class. Without this the classes are truth the machine obeys silently; with it, a Hauler can be taught to refuse a passage it cannot turn in, and to notice *before* it is wedged rather than after. |
| `best_open_heading` | which way looks most open | kept (`driver.py:229–261`, 36 rays) | `Fx` rad | y | real | S | already computed once per escape; publishing it costs the cache, not the scan |
| `open_heading_count` | how many ways out of here | derived from the same scan | `u8` | y | real | **L** | *Am I at a junction?* This is the closest a generated cave gets to Phase 2's junction concept without a graph, and it is what a demonstration's decision points could fire on. |
| `free_cells` | how much ground it knows is walkable | **new** (third cell state) | `u32` | y | heavy → incremental | S | the denominator every coverage signal needs, and the thing that makes C8–C10 possible at all |
| `frontier_count` | how many places it knows about and has not looked at | **new** | `u16` | y | heavy → rolling | **D1** | **This is the Phase 3 replacement for `deposit_remaining`.** `CAVE-BLOCKS.md` §7 guess 11 already commits to it: a generated cave has no survey, so *somewhere worth going* has to be asked of exploration. Nothing else in this catalogue is load-bearing for an existing commitment. |
| `nearest_frontier` | where the nearest unlooked-at place is | **new** | `(Fx bearing, Fx range)` | y* | heavy → rolling | **L** | *Go to the nearest unexplored thing* as a taught destination rather than a route the planner picked. This is the cave's `take_branch`. |
| `staleness_here` | how long since I last looked at where I am standing | **new** (per-cell last-seen tick) | `Ticks` | y | real (a grid write per beam) | **L** | *Re-scan ground I have not seen for a minute.* A machine that maintains its map rather than accumulating it — and the natural home for the "old returns are dimmer" rule in `ART-DIRECTION.md` §8.2, on the policy side rather than the render side. |
| `stale_fraction` | how much of what I think I know is old | **new** | `Fx` 0–1 | y | heavy → rolling, 0.8 s lag | S | *My map is mostly memory.* Distinct from uncertainty: a machine can be perfectly localised on a map it built ten minutes ago. Nothing today can express that. |
| `explored_fraction` | how much of the cave I have seen | — | — | — | **refused** | — | **The denominator is ground truth.** There is no legal way for a machine to know how big the cave is. This is the one place §9's "enriching belief cannot break the invariant" has an edge, and it is worth stating loudly: a quantity derived from belief *and one truth-side constant* is a truth leak wearing a belief costume. Publish `free_cells` and let the player decide what "enough" means. |
| `surface_ahead` | is the thing in front of me rock or water | derived (§24 reserves `SurfaceCharacter` on `RangeBearing` and `MapPoint`) | enum | y | cheap | **L** | A Swimmer that chooses the sump and a walker that refuses it, from the same block. Lidar already returns the waterline as a wall (`sensor_rig.py:129–145`); the character field is what stops that being a lie to every chassis that could swim it. |

**Determinism.** The third cell state is the whole risk, and it is a budget risk rather than a
correctness one. Marking cells along a beam is a Bresenham walk per return — roughly 10 cells per
beam at Phase 1 ranges, so ~800 cell writes per 76-return sweep, which is affordable once every
30 ticks and is not affordable at 11,500 returns per tick. **Whether free-space marking survives
the real sensor depends entirely on the downsample factor that `LIDAR.md` §6 leaves open.** If the
downsample lands near 1 in 100, this family is cheap; at 1 in 4 it is the dominant cost in the
sim. That dependency should be stated in whichever story settles the map representation.

**What it makes possible.** Exploration as a taught behaviour rather than a route list; *do I
ping* as a rule; the chassis width classes as something the machine can reason about; and a
machine that distinguishes *I do not know* from *I knew, a while ago*.

---

### D — Map self-consistency

This is the family §9 singles out as expensive, and it is also the one with the largest single
payoff, so it is worth being precise about both.

**What it is.** For a point placed now, find the nearest older point from a different epoch and
measure the offset. Where the machine has walked over its own ground twice, that offset is the
drift between the two passes. `LIDAR.md` §4 is the picture: "the same five boulders, the same row
of timber sets, the same fan of occlusion shadows, the same chamber outline — twice, at a 7° angle
to each other," and after the lie, "the map torn into two overlapping copies of everything."

**Why it is worth the cost.** `THE-SENSOR-AND-SLAM.md` §3.3 lists the predicates a found SLAM
module would bring: *I have been here before*, *my map disagrees with itself*, *my last correction
was large*. **The second of those does not need SLAM.** A machine can measure that its map
disagrees with itself without being able to do anything about it — and that is a strictly better
game object than SLAM, because §3.1's risk is that a working SLAM deletes drift and drift is the
game. This makes drift *legible* while leaving it *uncorrected*. The machine knows it is lost in a
way it currently cannot express, and the fix is still the player's problem.

It is also a second, independent spoof tell. `fix_jump_exceeds` is admitted-weak in
`CAVE-BLOCKS.md` §2.1 — "no threshold separates them everywhere," because an honest fix on a
three-minute-old beacon jumps as far as the lie. A tear in the map does not have that problem: an
honest fix *reduces* disagreement by construction (it drags the recent map onto the old one,
`pose_correction.py`), and a lie *increases* it. The sign is the tell, and the sign does not need
a threshold.

| signal | what it means to the player | origin | type / units | fx | cost | layer | what it unlocks |
|---|---|---|---|---|---|---|---|
| `disagreement` | how far my map disagrees with itself where I am walking | **new** | `Fx` cells | y* | **heavy → sampled** | **L** | the SLAM predicate without SLAM; the drift a machine can feel rather than model |
| `disagreement_trend` | is it getting worse | derived from the above | `Fx` cells/100 cells | y | free once D1 exists | S | separates *steady drift* from *something just happened* |
| `tear_at_last_fix` | did the last correction pull my map apart or together | derived (D1 sampled either side of a fix) | `Fx` signed cells | y | free once D1 exists | **L** | **The spoof tell that needs no threshold.** Honest fix: negative. Lie: positive. Independent of fix size, so it survives the case `fix_jump_exceeds` fails on. |
| `epochs_here` | how many separate passes have mapped this spot | **new** | `u8` | y | real (local bins) | S | *my map claims two things about this place.* Note carefully what it is not: it is not recognition. The machine is counting its own records, not identifying a room. |
| `trail_revisits` | how many times my own path crosses near here | derived from `belief.trail` | `u8` | y | real | S | the cheap cousin of `epochs_here`; complements B11's `wander_ratio` with a *where* |

**Cost, honestly.** With the occupancy bins as a spatial index, one nearest-older-point query is
O(points in the local bins) — call it 20–60 comparisons. At Phase 1's rate (76 returns per sweep,
one sweep in 30 ticks) that is ~150 ops per tick amortised: **cheap.** At a real scanning
sensor's rate it is 11,500 queries per tick, ~500,000 comparisons: **250× over the whole
per-agent budget, and it is not close.**

**So the recommendation is a sample.** Draw K returns per tick with
`draw(seed, tick, agent, purpose)` — K = 32 is my guess (guess 6) — and maintain a running mean.
That costs ~1,000 comparisons per tick, fits the envelope, and buys a signal that lags by a second
or so and is noisy at the metre scale. For *the map is tearing*, that is enough. For *this
specific wall moved 8 cm*, it is not, and nothing in the design asks for that.

**Determinism.** Two real traps, both solvable and both easy to get wrong:

1. **The sample must come from the counter-based RNG.** A stateful draw makes the signal a
   function of call order, which is exactly `DETERMINISM.md` rule 4's reason for existing.
2. **Nearest-neighbour ties must break by stable point id, never by bin traversal order.**
   `DETERMINISM.md` rules 2 and 6. Two points equidistant from a query is not a rare case in a
   grid-quantised map; it is what happens on every flat wall.

Marked `y*` rather than `y` for a third reason: the offset is a difference of two nearby
coordinates, so it is a subtraction of similar magnitudes in `I32F32`. That is fine at cell scale
(2⁻³² resolution against distances of tens of cells) but it is the place in the catalogue where
precision is thinnest, and any threshold on it should sit well above a centimetre.

---

### E — Fixes and beacons

The fix record already carries everything here (`fix_record.py`); one field is computed
specifically as a tell and then deliberately not used.

| signal | what it means to the player | origin | type / units | fx | cost | layer | what it unlocks |
|---|---|---|---|---|---|---|---|
| `ticks_since_fix` | how long since anything recognised where it was | kept (`belief.py:55`) | `Ticks` | y | free | **D1** | **One of the three animals §9 names.** *"A machine that turns back on how long since it last recognised anything"* — this is that machine, and it is one field already on `Belief` and already in `ARCHITECTURE.md`'s struct. Distinct from `sigma_pos` in play: sigma is a model whose constants are content and which a spoof collapses; this is a clock a lie cannot argue with, except by lying again. |
| `last_fix_jump` | how far the last correction moved it | kept (`fix_record.py:26`) | `Fx` cells | y | free | **D1** | the existing `fix_jump_exceeds` |
| `last_fix_surprise` | how many sigma that correction was | kept (`fix_record.py:30`) | `Fx` ratio | y | free | S | Computed *as* the spoof tell and then rejected as a block, with the measurement attached: on seed 7 surprise gives 11.4× against an honest 0.2–10.9×, while the raw jump nearly separates (`CAVE-BLOCKS.md` §7 guess 2). Publish it as substrate with that note; someone will find a use for the ratio that the threshold search could not. |
| `last_fix_source` | was that the shaft, my own beacon, or somebody's | derived (`KnownBeacon.truth_anchor`) | enum | y | free | **L** | **Reads a measured asymmetry nothing today can see.** §47 re-measured it: 65% of honest own-beacon fixes *increase* true position error, because the chain re-anchors to past belief. Only the survey-placed shaft is a truth anchor. A machine that counts anchor fixes and ignores chain fixes is right about something the design has proved, and it is unreachable with the current six. |
| `ticks_since_anchor_fix` | how long since the *shaft* answered | derived | `Ticks` | y | free | S | the honest version of E1 for a machine that has learned not to trust its own chain |
| `fix_count` | how many times it has been told where it is | kept | `u16` | y | free | S | |
| `fix_jump_trend` | are the corrections getting bigger | derived over `fixes` | `Fx` cells/fix | y | cheap | **L** | **A better spoof tell than the block that exists.** The spoof reasserts every 8 s (`tuning.py`, `sensor_rig.py:232–243`), so it produces a *sequence* of corrections, and a rising sequence is a signature an honest chain does not produce. `CLAUDE.md` names "sensor noise that feels fair" as a known-weak area; this is a tell that does not require a threshold to separate the lie from an unlucky honest fix. |
| `max_fix_jump_window` | biggest jump in the last 45 s | kept, published (`fix_jump_exceeds.py:23`) | `Fx` cells | y | cheap | **D1** | the raw under the existing block |
| `sigma_before_fix` | how confident it was just before being corrected | kept (`fix_record.py:23`) | `Fx` cells | y | free | S | |
| `chain_length` | how many of its own beacons it has out | kept (`beacon_order`) | `u8` | y | free | S | |
| `beacons_remaining` | how many it has left to drop | derived (loadout rack, §2 module 4) | `u8` | y | free | **L** | *Do not spend the last beacon this shallow.* Pairs with B3 to make the rack a real resource rather than an invisible ceiling. |
| `dist_to_nearest_beacon` | how far to something that could fix me | derived | `Fx` cells | y | cheap | S | *Go and re-acquire before you go deeper* as a rule, not a route. |
| `foreign_beacons_seen` | somebody else's beacon is here | kept-by-design (§10, §16 reserve `Belief.foreign_beacons`) | `Vec` | y | free | **L** | **A contact without a sound.** The one piece of evidence a fully passive, never-pinging machine can gather about a rival. Already reserved in the Phase 3 schema and read by nothing. |

**Determinism.** All safe. `fix_jump_trend` iterates `fixes`, which is a `Vec` in drop order —
stable — and is capped by the number of fixes in a match (3–41 measured,
`SENSORS-AND-IDS.md` §0). Cap it explicitly anyway; an unbounded `Vec` in a per-tick loop is how a
`free` signal becomes a `heavy` one in month nine.

---

### F — Sensor health

Every signal in this family is a counter formed in a loop that already runs. It is the cheapest
family in the catalogue and it contains one of the three machines §9 asks for by name.

| signal | what it means to the player | origin | type / units | fx | cost | layer | what it unlocks |
|---|---|---|---|---|---|---|---|
| `returns_last_sweep` | how much came back | **new**, free | `u16` | y | free | S | |
| `expected_returns` | how much should have | derived (content: rays × rings) | `u16` | y | free | S | |
| `return_ratio` | is my sensor working | derived | `Fx` 0–1 | y | free | **D1** | **The second animal §9 names: the machine that turns back on sensor health.** It also makes a damage effect visible that the code says is currently invisible (0.5). And it is the direct read-out of `THE-SENSOR-AND-SLAM.md` §2's stage 2 (occlusion — "the far returns thin out and then stop"). Free, named by the designer, fixes a stated hole. |
| `max_range_seen` | how far away the furthest thing was | **new**, free | `Fx` cells | y | free | **L** | **Two numbers separate two situations one number cannot.** Low ratio + low max range = blind. High ratio + low max range = a small room. A machine that can tell *the passage ended* from *I stopped being able to see* is doing something no single signal permits. |
| `near_fraction` | how much of what came back was right in front of my face | **new**, free | `Fx` 0–1 | y | free | **L** | **The dust signal.** `THE-SENSOR-AND-SLAM.md` §2 stage 1: "sparse false points floating in the passage at short range, in front of the true walls." §2 also makes dust partly self-inflicted — "a machine that hurries blinds itself" — so this is the block that turns that fiction into a taught behaviour: *slow down when the near field fills up*. Nothing else in the catalogue closes a design loop that cleanly. |
| `blinded` | I cannot see anything but my own dust | derived (F5 high and F4 collapsed) | bool | y | free | **L** | stage 3. A compound, and a good example of why compounds should be substrate-derived blocks rather than new sensing. |
| `quality_mean` | how good the returns were | kept (`RangeBearingReturn.quality`, stored per point as `cloud.confidence` and never aggregated) | `Fx` 0–1 | y | free | S | |
| `ticks_since_return` | how long since the sensor said anything | **new**, free | `Ticks` | y | free | S | the failure case F3 cannot express: a module that has stopped answering at all |
| `deaf` | I am currently deafened by my own transmission | kept, sensor-side only (`sensor_rig.py:43`, `:61`) | bool | y | free | **L** | **Makes the passive/active trade a rule.** *Do not ping while I am listening for the machinery* is not expressible today. A machine pings, goes deaf for a second (`SELF_DEAF_AFTER_PING_S`), and cannot know it — which means it cannot be taught to time its pings around the thing that kills it. |
| `module_ok(id)` | is that part still working | reserved (§16 `self_report.modules`) | bitset | y | free | **L** | `hurt`-style blocks per module rather than one damage scalar; `CAVE-BLOCKS.md` §6 defers `hurt` for want of `SelfReport`, which §16 now has. |

**Determinism.** All safe, all `free`. The one caveat is definitional rather than numerical:
`expected_returns` must come from the sensor's *content record*, never from the world — a sensor
that asks the cave how many returns it should have got is reading truth. It is the content number
(rays, rings, azimuth steps) and the ratio is honestly wrong when the machine is in a large open
chamber, which is fine: that is what F4 is for.

**What it makes possible.** An entire temperament the current six predicates cannot express at
all. Two machines with identical trees, one reading uncertainty and one reading sensor health,
behave completely differently in a dust cloud: the first walks on confidently because its ellipse
is small, and the second stops. §9 says the difference between techniques "lives in what they
read, not in how the tree is shaped." This family is the clearest instance of that in the game.

---

### G — Contacts, acoustics, and what it has broadcast

Two things in this family are already computed in full and read by nobody: the bearing trackers'
position estimates (`bearing_tracker.py:72–122`) and the conditioning number that says how much to
trust them (`bearing_tracker.py:99`).

| signal | what it means to the player | origin | type / units | fx | cost | layer | what it unlocks |
|---|---|---|---|---|---|---|---|
| `contact_count` | how many things it can hear | kept (`belief.contacts`) | `u8` | y | free | S | |
| `best_contact_quality` | how loud the loudest is | kept | `Fx` 0–1 | y | free | **L** | reserved as PredicateId 69 |
| `contact_bearing(i)` | which way each is | kept | `Fx` rad | y | free | S | |
| `ticks_since_heard(character)` | how long since I heard one of those | derived (`HeardSound.t`) | `Ticks` | y | free | **L** | reserved as `signature_within`; the parametric form the two reference temperaments both want |
| `signature_level` | how loud the machinery is | kept, published | `Fx` 0–1 | y | free | **D1** | the existing `machinery_audible` |
| `signature_bearing` | which way the machinery is | kept, motor-only (`belief.signature.bearing`, used by `interface_machinery`) | `Fx` rad | y | free | **L** | **Makes *avoid* expressible.** Today a tree can freeze or approach and nothing else; the direction is read by the motor layer and never by the tree. A machine that walks the reciprocal bearing is a third temperament the block set cannot currently write down. |
| `signature_closing` | is it getting louder because it fired, or because I am walking into it | derived (quality trend over the last N ticks) | `Fx` signed | y | cheap | **L** | **Fixes a measured death.** `CAVE-BLOCKS.md` §8: *"the cautious tree freezes where it stands"* — a spoofed player whose route runs into the Assayer's chamber freezes inside the lethal contour, three deaths in eight seeds against none for the hand-written policy. It froze because *loud* is all it can read, and *loud and getting louder because I am approaching* is a different fact. One derivative separates them. |
| `signature_period` | the machine has a rhythm and I have heard three of them | **new** (interval between rising edges) | `Ticks` | y | cheap | **L** | **Times the walk past the machine.** `AncientKindId 1` is `fixed_cycle` (75 s period, 9 s warning, 4 s lethal). A machine that has heard three cycles knows the period, and *cross the chamber just after it fires* becomes teachable. `GLOSSARY.md` promises ancients have "a behavior, an exploit, and a counter"; this is the first signal that lets a policy hold the exploit. |
| `contact_closing` | that thing is getting nearer | derived (bearing rate + quality trend) | `Fx` signed | y | cheap | **L** | *Being followed*, reserved as PredicateId 70, without needing a track solution |
| `contact_stationary` | it has not moved | derived | `Ticks` | y | cheap | **L** | reserved as PredicateId 66; the echo and decoy tell |
| `hazard_estimate` | where I have worked out the machinery is | **kept and thrown away** (`bearing_tracker.estimate()`) | `(Vec2Fx, Fx sigma)` | ! | real | **L** | **The strongest unlock in this family, and it already exists in code.** Bearings crossed over time give a position for a thing the machine has never seen. *Keep thirty cells from where I think the machine is* is currently impossible; with this it is one guard. Computed today for the display and read by no predicate. |
| `rival_estimate` | where I have worked out the other machine is | **kept and thrown away** (`rival_track`) | `(Vec2Fx, Fx sigma)` | ! | real | **L** | the same, for a rival — and the reason to ping or not to |
| `track_condition` | do I actually know where it is yet | **kept and thrown away** (`bearing_tracker.py:99`) | 3-state band | ! | free once the track runs | **L** | **Turns a stated design intent into something teachable.** `bearing_tracker.py:5–6`: bearing-only tracking "is a skill involving deliberate movement, not a readout." Today nothing can act on *I have not moved enough to know*. With this, *step sideways twenty cells, then decide* is a rule a player can write, and deliberate baseline-building becomes a technique rather than an accident. |
| `ticks_since_emit` | how long since I made a noise | reserved (§16) | `Ticks` | y | free | **D1 candidate** | the other half of *do I ping?*, with C2 |
| `emissions_count` | how many times I have announced myself | derived | `u16` | y | free | S | a match-long exposure budget; the accounting a quiet loadout wants |
| `answered_last_emit` | did anything come back when I pinged | derived | bool | y | free | S | *ping once; if nothing answers, go quiet* — the cheapest possible active/passive discipline |

**Determinism — the one real flag in the catalogue.** The bearing trackers are marked `!`, and the
reason is worth stating carefully, because it is not the reason it looks like.

The tracker solves a weighted 2×2 least-squares system and then divides `det(A)` by `trace(A)²`
(`bearing_tracker.py:95–101`) to decide whether the crossing means anything. In fixed point that
computation is perfectly **deterministic** — it will produce identical bits on all three
platforms, which is what the canary tests. What it will not be is **meaningful** near the singular
case: `det` is a difference of products of similar magnitude, so when the bearings are nearly
parallel it is dominated by the last bits of `I32F32`, and a threshold placed on it will flap on
quantisation noise rather than on geometry.

So the flag is not "this cannot be made deterministic." It is: **a deterministic signal can still
be a bad signal, and this one is the catalogue's example.** The fix is cheap and it is a
recommendation, not a caveat: publish `track_condition` as three named states — *no crossing*,
*vague*, *good* — with the band edges set far from the noise floor (`MIN_CONDITION 0.012`,
`GOOD_CONDITION 0.22` are the Phase 1 values), and publish `hazard_estimate` as `None` below the
lower band rather than as a number nobody should use. Never expose the raw ratio.

The position estimates themselves inherit that: they are `!` because they are only as good as the
conditioning, not because the arithmetic is unsound.

---

### H — Self, cargo, and what it has put down

| signal | what it means to the player | origin | type / units | fx | cost | layer | what it unlocks |
|---|---|---|---|---|---|---|---|
| `cargo` | am I carrying anything | kept, published | `u8` | y | free | **D1** | the existing `carrying_cargo` |
| `hold_full` | am I full | derived (cargo vs bay capacity) | bool | y | free | **L** | `CAVE-BLOCKS.md` §6 defers it because it coincides with *no deposit remaining* in the Phase 1 cave. In a generated cave with more deposits than bays they diverge, and the divergence is the whole *one more junction* decision. |
| `blocks_carried` | am I carrying something I have never brought home | reserved (§33 `inventory.blocks`) | `Vec<BlockId>` | y | free | **L** | **`DESIGN-PRINCIPLES.md` §2's sentence, with the thing itself in the predicate.** *I have something, I am getting lost, do I go one junction further?* — today `cargo` stands in for "something." With this, the machine can weigh *a block I do not have a copy of* differently from ore, which is exactly what the extraction loop says is at stake. |
| `power` | how much I have left | reserved (§16) | `Fx` | y | free | **L** | turns the extraction deadline from a wall clock into a resource, and makes a fourth kind of turn-back machine |
| `damage` | how hurt I am | reserved (§16) | `Fx` 0–1 | y | free | **L** | `CAVE-BLOCKS.md` §6's deferred `hurt`; `THE-MACHINERY.md` §4.8's two-block tree |
| `medium` | am I in water | reserved (§24, depth gauge SensorId 7) | enum | y | free | **L** | the Swimmer's whole vocabulary, and a walker that knows it has waded in |
| `current_action` / `ticks_in_action` | what I am doing and for how long | reserved (§29) | `(ActionId, Ticks)` | y | free | **D1 candidate** | **The only latch a memoryless tree has.** §29's evidence: without it the agent flipped back to surveying on 1 of 6 seeds, and would on every return under Phase 3's honest chain. *Once turned for home, stay turned* is unwritable without it — which is the exact limitation `CAVE-BLOCKS.md` §2.4 records and accepts. |
| `known_beacons` | where I think I put my beacons | kept (`belief.beacons`) | `BTreeMap` | y | free | S | note honestly what these are: recorded at the *estimated* position at drop time, so the chain anchors to past belief, not to the world (`known_beacon.py:9–17`) |
| `wrecks_known` | where I think a dead machine is | **new** (needs optical identification, BLD-93/95) | `Vec` | y | free | **L** | *Go and salvage* / *avoid where things die* as taught behaviour. The wreck is already load-bearing in §2; nothing can currently reason about one. |
| `deposits_tried` | places I have been and finished with | kept, published (`belief.tried_deposits`) | set | y | free | **D1** | the existing `deposit_remaining`; becomes exploration in Phase 3 (see C8) |

**Determinism.** All safe; all of it arrives through `SelfReport` or `Intent.report`, which are
already hashed types. The one discipline: `known_beacons` is a `BTreeMap` keyed by id (§16), never
a `HashMap`, and `chain` is the separate order vector — `DETERMINISM.md` rule 2, and §16 gives the
reason (relax skips the fixing beacon and truth anchors by id).

---

### I — The clock and the plan

| signal | what it means to the player | origin | type / units | fx | cost | layer | what it unlocks |
|---|---|---|---|---|---|---|---|
| `elapsed` | what time it thinks it is | kept, published (`belief.t`) | `Ticks` | y | free | **D1** | the existing `time_elapsed_exceeds` |
| `window_open` | can I extract yet | derived (elapsed vs a content constant) | bool | y | free | **L** | Legal but worth flagging as *prior knowledge*, like the survey: the machine was told the schedule before it went down. That is defensible; it should be a stated content fact, not a silent one. |
| `ticks_to_close` | how long until the door shuts | derived | `Ticks` | y | free | **L** | |
| `dist_to_shaft` | how far home, as the crow flies | derived | `Fx` cells | y | free | **L** | the cheap version of I5 |
| `route_cost_home` | how far home, by a route I believe exists | derived (the route planner already computes it, `route_planner.py`) | `Fx` cells | y | real, cache it | **L** | |
| `ticks_home_estimate` | how long it would take me to get back | derived (I5 ÷ measured speed, B4) | `Ticks` | y | free once I5 exists | **L** | |
| `margin` | how much slack I have | derived (I3 − I6) | `Ticks` signed | y | free | **L** | **The signal that makes extraction a decision instead of a timer.** *Leave when the walk home is longer than the time left* is a genuinely different machine from *leave at 5:30*, and it degrades correctly: as drift grows, `route_cost_home` is computed on a wrong map and the margin becomes optimistic, so a lost machine cuts it fine by exactly the amount it is lost. That is the game's central tension expressed in one number, and it is honestly wrong in the right direction. |
| `destination` / `plan_progress` | where I mean to go and how far through | reserved (§21 `Intent.report`) | `(PlaceRef, Fx)` | y | free | S | |
| `places_visited` | how many places I have been | derived | `u8` | y | free | S | |

**Determinism.** `route_cost_home` is the only `real` item and it is a Dijkstra over the believed
graph. Cache it and recompute on a cadence — every 20 ticks is my guess (guess 7) — and state the
staleness, because a route cost that is one second old is fine and one that is silently thirty
seconds old is a lie the player cannot see. Everything else is arithmetic on `Ticks`.

---

### J — Terrain and body fit

Small, but it is the family that makes chassis choice mean something a policy can reason about.

| signal | what it means to the player | origin | type / units | fx | cost | layer | what it unlocks |
|---|---|---|---|---|---|---|---|
| `width_class_here` | how tight it is where I am | derived (C4 against the chassis record, §25) | enum 0–3 | y | free once C4 exists | **L** | *A Hauler that refuses to enter what it cannot turn in.* Today the width classes are truth the body obeys silently. |
| `can_turn_here` | could I turn round if I had to | derived | bool | y | free | **L** | the difference between a cautious Hauler and a stuck one |
| `flooded_ahead` | is that water | derived (C13) | bool | y | free | **L** | the Swimmer's shortcut and the walker's detour, from one block |

---

## 3. The three that unlock the most

Asked to pick three, and picking honestly rather than picking the cheap ones:

**1. `disagreement` — the map disagreeing with itself (D).** It is the only signal in the
catalogue that lets a machine doubt its own map. It delivers the SLAM predicate
`THE-SENSOR-AND-SLAM.md` §3.3 promises *without* delivering SLAM, so it makes drift legible while
leaving it uncorrected — which is the only way to have that predicate without §3.1's risk of
deleting the game. It is also a second, independent spoof tell whose *sign* carries the answer, so
it works where `fix_jump_exceeds` is admitted not to. It is the most expensive thing here and it
is worth it.

**2. `return_ratio` and `max_range_seen` — sensor health (F).** Free, both of them, formed in a
loop that already runs. They are the second of the three machines §9 names by name; they make a
damage effect visible that `sensor_rig.py:98–107` says in its own words is currently invisible;
and together they separate *the passage ended* from *I stopped being able to see*, which is a
distinction no single number can carry. Best ratio of technique to cost in the document by a
wide margin.

**3. `signature_closing` and `signature_bearing` — the machinery, as a direction and a
derivative (G).** The current set can freeze or approach. It cannot flee, and it cannot tell
*loud because it fired* from *loud because I am walking into it*. That second gap is not
hypothetical: `CAVE-BLOCKS.md` §8 measured the cautious tree freezing inside the lethal contour on
three of eight seeds for exactly that reason. One derivative and one field already on `Belief`
turn a measured failure into a teachable distinction and add a whole temperament.

**Runner-up, because it is already written:** `hazard_estimate` and `track_condition` (G). The
bearing trackers compute a position and a confidence for a thing the machine has never seen, and
no predicate reads either. Navigating relative to something you have only heard is the most
distinctive thing this game's machines can do, and it is sitting in `bearing_tracker.py` unread.

---

## 4. What I would cut first

A catalogue that recommends everything recommends nothing. In the order I would strike them:

1. **`pose` and `heading` as *block* material.** They stay as substrate because everything is
   relative to them, but a threshold on a believed coordinate is a policy that only works in one
   cave, and Phase 3 generates a cave per match. Publishing them invites exactly that. If a block
   over absolute position is ever wanted, it should be over a *named place* the machine knows, not
   over a number.
2. **`dist_since_fix` as a block, given `sigma_along`.** Under today's model
   `sigma_along = 0.5 + 0.038·d` — the two are the same test in different units, and blocking both
   spends two of the eight induction slots on one idea. Publish both as substrate, block one.
   They separate the moment terrain-relative navigation lands; until then, one.
3. **`speed_measured`, `turn_rate`, `places_visited`, `emissions_count`, `fix_count`,
   `map_points`.** Free, honest, and I cannot name a technique any of them enables that a
   neighbouring signal does not enable better. Keep them as substrate on the grounds that they
   cost nothing; strike them the moment "cost nothing" stops being true.
4. **`trail_revisits` (D5).** It is the cheap cousin of `epochs_here` and `wander_ratio` and it is
   worse than both — the trail is a sampled path (`belief.py:151`, one point per half cell), so
   the count is an artefact of the sampling as much as of the behaviour.
5. **`stale_fraction` (C11).** Genuinely interesting, genuinely expensive, and it is a whole-map
   aggregate on a rolling schedule, so it lags by a second and means less than `staleness_here`
   for most decisions. Cut it and keep the local one.
6. **`sigma_growth` (A10).** The technique it enables — noticing a limping chassis — is better
   served by `slip` (B8), which is free and direct rather than inferred.
7. **`explored_fraction` — already refused**, and it is listed here too because it is the one
   people will keep asking for. There is no legal denominator.

The families I would not cut anything from are F (everything in it is free) and D (there is only
one idea in it and it either lands or it does not).

---

## 5. The recommended day-one block list

A revision of `phase1/blocks.json`, in the same shape, written so it can be diffed. **The
constraint that shapes it is `MAX_PREDICATES = 8`** (`crates/blindside-induct/src/tuning.rs:30`,
enforced `induce.rs:90` over the whole list, not the enabled subset). Eight is what there is.

```json
{
  "predicates": [
    {"id": "frontier_exists",       "label": "somewhere left to look",                                          "stage": 1},
    {"id": "carrying_cargo",        "label": "carrying",                                                        "stage": 1},
    {"id": "time_elapsed_exceeds",  "label": "late",              "param": "seconds", "provisional": 270.0,     "stage": 1},
    {"id": "uncertainty_exceeds",   "label": "lost",              "param": "theta",   "provisional": 10.0,      "stage": 2},
    {"id": "time_since_fix_exceeds","label": "adrift",            "param": "seconds", "provisional": 40.0,      "stage": 2},
    {"id": "fix_jump_exceeds",      "label": "the last fix was a jump", "param": "cells", "provisional": 8.0,   "stage": 2},
    {"id": "sensor_degraded",       "label": "half blind",        "param": "ratio",   "provisional": 0.75,      "stage": 3},
    {"id": "machinery_audible",     "label": "the machinery is loud", "param": "level", "provisional": 0.25,    "stage": 3}
  ],
  "actions": [
    {"id": "go_to_deposit",       "label": "fetch from a deposit",                  "stage": 1},
    {"id": "return_to_beacon",    "label": "go back",                               "stage": 1},
    {"id": "run_for_shaft",       "label": "make straight for the shaft",           "stage": 2},
    {"id": "active_scan",         "label": "look around",                           "stage": 2},
    {"id": "drop_beacon",         "label": "leave a marker",                        "stage": 2},
    {"id": "hold",                "label": "freeze until it passes",                "stage": 3},
    {"id": "interface_machinery", "label": "go to the machinery and download",      "stage": 3}
  ]
}
```

### 5.1 What changed and why

**Replaced.** `deposit_remaining` → `frontier_exists`. Not a preference: `CAVE-BLOCKS.md` §7
guess 11 already commits that the intel-based block becomes an exploration block when the survey
goes away in Phase 3, and `frontier_exists` is what that block is. Keep `deposit_remaining` under
its own id for as long as a survey exists — they are different questions and should not share an
id — but the day-one *list* for a generated cave carries the exploration one. This is the row that
makes C7/C8's free-space channel non-optional.

**Added — `time_since_fix_exceeds` ("adrift").** §9 names the machine that "turns back on how long
since it last recognised anything." One field already on `Belief` (`belief.py:55`), already in
`ARCHITECTURE.md`'s struct, free. It is not a duplicate of *lost*: `CAVE-BLOCKS.md` §3.1 measured
that *lost* **never rose on any of four seeds** at θ = 16 or at the provisional 10, because the
spoof collapses σ and a jammed agent stops accumulating distance. A clock is harder to argue with
than a model.

**Added — `sensor_degraded` ("half blind").** §9's second named machine, free, and it makes a
damage effect visible that the code says is invisible (0.5). Stage 3 because it needs a run in
which the sensor is degraded for the player to meet it, which is the machinery's dose or a dust
event.

**Kept, with a note — `fix_jump_exceeds`.** Weak, and `CAVE-BLOCKS.md` §2.1 says so. Kept because
it is the only spoof tell that costs nothing and the spoof is the centrepiece. It should be
*superseded* by `tear_at_last_fix` (D3) the moment family D exists, not supplemented — the
supersession is the point, and it is exactly how `DESIGN-PRINCIPLES.md` §1 says a season should
replace an item.

**Kept — `carrying_cargo`.** Used by neither reference tree and mandated by §2. `blocks_carried`
(H3) is the sharper version and should arrive as a later block, not replace this one.

**Actions, +3.** `run_for_shaft` is `CAVE-BLOCKS.md` §6's next action and §8's stated day-two
answer to the cautious tree freezing in the lethal contour. `active_scan` and `drop_beacon` are
`SENSORS-AND-IDS.md` ActionIds 3 and 4, and they are what make C2, G13 and B3 mean anything — a
signal about pinging with no way to ping is furniture.

**This contradicts `CAVE-BLOCKS.md` §4 twice and the contradictions are deliberate.** §4 puts ping
cadence and the beacon drop cadence in the motor layer as loadout numbers. Adding `active_scan`
and `drop_beacon` moves both to the player. §4's own test — "a block is something two players
would defensibly choose differently" — passes for both: *do I ping?* is called the central
decision of a match in `GLOSSARY.md`, and a thin-chain-deep versus dense-chain-shallow trade
against a six-beacon rack is a real disagreement. §4 should be amended rather than quietly
overridden, and this is that flag.

### 5.2 What did not make it, and what it would take

`points_ahead` / `unmapped_ahead` and `signature_closing` are the ninth and tenth, and I think
both are better than `fix_jump_exceeds`. The eight-cap is the only reason they are not in the
list. See question 1.

---

## 6. Open questions for the designer

Each is yes/no with a default. An unanswered line is an open question, not a default taken.

**Q1. Is the substrate reachable in the node editor as a numeric source, and out of reach of the
induction?** §9 leaves this open explicitly. *Default: yes — the editor reaches the substrate
through comparison nodes; demonstrations teach over named blocks only.* Reason: the induction
fits a threshold over a *named* block, and a demonstration cannot express which of ninety numbers
a player meant by one click. This split also dissolves `MAX_PREDICATES = 8`: the cap binds the
demonstration path, which should be small, and not the editor path, which should be wide. It is
the cleanest reading of §9's two layers I can find.
`[ ] yes  [ ] no — notes:`

**Q2. If the day-one block list exceeds eight predicates, does the client hand `induce` a filtered
block list containing only the blocks that run was enabled with?** *Default: yes, filter.* The
client already writes contract-shaped copies of traces into `seam/contract/`
(`CAVE-BLOCKS.md` §9), so filtering a second file is the same mechanism. The cost is that
minimality is then computed against a smaller list, so a predicate absent from a run can never be
dropped as unneeded — which is arguably more honest anyway.
`[ ] yes  [ ] no (keep the list at eight) — notes:`

**Q3. Does the free-space channel get built — the third cell state, marked along every beam?**
*Default: yes.* It is the only way to answer *is there anywhere left to go* in a cave with no
survey, which `CAVE-BLOCKS.md` §7 guess 11 has already committed to. Saying no here means
`deposit_remaining` needs a different Phase 3 successor, and there is no other candidate.
`[ ] yes  [ ] no — notes:`

**Q4. Is map self-disagreement (family D) built, sampled at K returns per tick?** *Default: yes,
sampled.* It is the most expensive family and the largest single unlock. Saying no costs the
SLAM-without-SLAM predicate and the threshold-free spoof tell; saying yes costs a running
nearest-neighbour query and a stated lag.
`[ ] yes  [ ] no — notes:`

**Q5. Do `active_scan` and `drop_beacon` become actions, moving ping cadence and beacon cadence
out of the motor layer?** *Default: yes*, and `CAVE-BLOCKS.md` §4 is amended to say so.
`[ ] yes  [ ] no — notes:`

**Q6. Is `frontier_exists` the Phase 3 successor to `deposit_remaining`, with both ids live while
a survey exists?** *Default: yes.*
`[ ] yes  [ ] no — notes:`

**Q7. Is the machinery's cycle period (G8) something a machine may learn?** *Default: yes.* It is
derived from what it heard, so it is legal; the question is whether the designer wants the
ancients' rhythm to be exploitable by a policy rather than only by a player.
`[ ] yes  [ ] no — notes:`

**Q8. Does `window_open` (I2) count as prior knowledge the machine was given, like the survey?**
*Default: yes, and it is stated content rather than a silent constant.*
`[ ] yes  [ ] no — notes:`

**Q9. Is the per-agent budget for everything in this catalogue 2 µs per tick?** *Default: yes.*
Every cost tier in §1.2 is calibrated to it; halving it strikes families C and D, doubling it
buys the unsampled version of D.
`[ ] yes  [ ] no — notes:`

---

## 7. Every guess, in one place

1. **The 2 µs per agent per tick envelope**, derived from §19's 62.5 µs gate less §37's 10 µs of
   acoustics over §38's four agents. The division is mine; nothing states a belief-layer budget.
2. **The ops-per-tier numbers** in §1.2 (< 20 / 50–500 / 500–5,000 / ≥ 20,000) and the ~1 op/ns
   assumption behind them. Order-of-magnitude reasoning, not measurement.
3. **The along/cross crossover at ~43 cells** is arithmetic on `tuning.py:50–53` and is not a
   guess; the *reading* of it — that below it a machine is mostly wrong about distance and above
   it mostly wrong about lateral position — is mine.
4. **The Bresenham estimate of ~10 cells marked per beam** at Phase 1 ranges, and therefore the
   whole cost of the free-space channel.
5. **That publishing `return_ratio` makes the damage effect legible.** Reasoned from
   `sensor_rig.py:110` (`reach` scales with the damage multiplier, so far rays return nothing);
   not measured. It should be measured before the block ships — a run at the 0.493 dose, counting
   returns per sweep before and after.
6. **K = 32 sampled returns per tick** for family D, and the claim that the resulting signal is
   good enough for *the map is tearing* and not for anything finer.
7. **A 20-tick cadence for `route_cost_home`.**
8. **The provisional thresholds** for the two new blocks in §5: `seconds = 40` for *adrift* and
   `ratio = 0.75` for *half blind*. Both follow `CAVE-BLOCKS.md` §3's rule that a provisional
   value should sit low so the bot asks early; neither is measured.
9. **That `tear_at_last_fix` has the sign I claim** — negative for an honest fix, positive for a
   lie. It follows from `pose_correction.py` dragging the recent map onto the older map, and from
   `LIDAR.md` §4's description of the lie tearing the map into two copies. It has not been run.
10. **The three-state banding of `track_condition`** and the recommendation never to expose the
    raw conditioning ratio. The band edges borrow Phase 1's `MIN_CONDITION 0.012` and
    `GOOD_CONDITION 0.22`; whether those are far enough from the fixed-point noise floor has not
    been checked.
11. **That `wander_ratio` spikes under a spoof.** Reasoned from the spoofed machine loitering
    between anchors; not measured.
12. **The claim that `signature_closing` would have prevented the three deaths in
    `CAVE-BLOCKS.md` §8.** It addresses the stated cause; it has not been run against those seeds.
13. **Labels.** Every player-facing string in §5 is content and the designer may reword any of
    them without telling anyone. *Adrift*, *half blind* and *somewhere left to look* are mine.
14. **The signal names.** Ids are a contract in Phase 3; nothing here should be treated as
    assigned until it is in `content/predicates.toml` with a number.

---

## 8. What this document does not settle

- **The downsample factor for a real scanning sensor's returns.** `LIDAR.md` §6 raised it, called
  it a `Belief` design question, and it is still open. Every per-return cost in this catalogue is
  a function of it, and family D is affordable or impossible depending on where it lands.
- **Whether the substrate is versioned.** If a policy in the node editor reads a substrate signal
  by name, that name is a contract with the same permanence as a `PredicateId`
  (`ARCHITECTURE.md` rule 1). Nothing in this document assigns ids, and nothing decides whether
  substrate signals need them. They probably do.
- **What the substrate looks like in the editor.** Ninety numbers in a list is not discoverable;
  §9 says so. Grouping them by family is the obvious first answer and it is not a design.
- **Whether any of this reaches the spectator display.** A published signal is legal to render by
  construction, and several of these — sensor health, map disagreement, the margin — are better
  television than the numbers currently on the rail. That is `SPECTATOR-DISPLAY.md`'s question,
  not this one.
