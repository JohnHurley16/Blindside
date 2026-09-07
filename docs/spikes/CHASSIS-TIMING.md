# Chassis timing — when Scout, Hauler and Swimmer ship, and what Phase 3 reserves for them

BLD-65 spike. Written 2026-09-06 against HEAD `d19579b`. This is a recommendation, not a
decision: every numbered item in §3 ends in a line for the designer. No chassis data has
been written and no board story has been edited. IDs here are *proposed*; BLD-63's table
assigns them.

The designer's instruction for tonight was to measure rather than assert, so this spike
ran the Phase 1 build against every question it could put a number on. What was measured
is in §2. Everything guessed is marked **(guess)** where it appears and listed again in §6.

---

## 0. The decisions in one table

| # | Question | Recommendation |
|---|---|---|
| D1 | Are chassis classes in the game at all? | Yes. If no, the width and flooding locks in BLD-73 and BLD-78 should go too. |
| D2 | ID space | A separate `ChassisId(u16)`. Surveyor 1, Scout 2, Hauler 3, Swimmer 4. Reserved now. |
| D3 | What Phase 3 ships | All four chassis as content records. The Surveyor's `season` is the active one; the other three carry a later `season`, so the validator, the content hash and the tests know them. |
| D4 | Where the mechanics read from | Locomotion and the cell classifier read width class and terrain viability from the chassis record, never from Surveyor constants. |
| D5 | Passage width | A per-cell width class (crawl / narrow / passage / hall). Each chassis names the class it can enter and the class it can turn in. |
| D6 | Flooding | Terrain viability is a speed factor per terrain (0 = cannot enter). The Swimmer is amphibious with a heavy dry penalty, not immobile on dry rock. |
| D7 | Generator locks | A deposit goes behind a lock (crawl, flooded) only if an enabled chassis holds the key. |
| D8 | Schema room for the Swimmer | A depth-gauge SensorId (SENSORS §3.3 ships it as SensorId 7, on every chassis); `SelfReport.medium`; `SurfaceCharacter { Rock, Water }` on the range return and the map point; chassis-aware `blocked()`. All Phase 3, all small. Reconciled 2026-09-07: the depth gauge is assigned, not reserved, and water is a *character* on a return whose `source` is a SensorId, not a map-point source of its own. See PHASE-3-OPEN-QUESTIONS.md §5, §11, §14 and §24. |
| D9 | Loadout rules | Seven validator rules, §3.9. |
| D10 | When each ships | Scout and Hauler: Phase 6, one new story after BLD-167 and before BLD-176. Swimmer: Phase 9, as season one's world change, on BLD-203. |
| D11 | Numbers | Proposed per-chassis values, §3.11, all marked. |
| D12 | Harness override | The headless harness may run an entry whose season is later than the active one behind an explicit flag, so Phase 6 enablement is tuning, not discovery. |

Cost: about 3.25 working days in Phase 3, about 10.5 in Phase 6, about 11.5 in Phase 9
(§4). Today the board spends 0 days on three of the four classes, ever.

---

## 1. What the documents say, and where the board contradicts them

**DESIGN.html** (background) lists four classes with their trades — Scout "small, quiet,
fast, three module slots; fits anywhere; almost no carry capacity; fragile"; Surveyor
"mid-size, six slots; the default"; Hauler "large, heavy carry, eight slots, loud; blocked
by constrictions; audible across half the cave"; Swimmer "flooded passage specialist;
useless on dry rock; unmatched below the waterline". Its prep phase is "chassis selection,
module loadout, behavior assignment". Its seasons section says a season changes "which
chassis classes and modules are viable, as a downstream consequence" and adds "a new module
or chassis class, occasionally".

**ARCHITECTURE.md** makes chassis "pure data", growth "1 → 4 classes", with permanent IDs
that are never reused (rule 1; DETERMINISM rule 7).

**GLOSSARY.md** names all four classes under *Chassis*. BLD-6 adds that "a Swimmer can only
sensibly carry sonar".

**DESIGN-PRINCIPLES.md §2** (wins over DESIGN): it is an extraction game; the cool things
are found by depth — "past the sump, past the machinery, past where the beacon chain still
holds". A chassis that can go where the others cannot is a key to a depth tier.

**The board** builds mechanics for all of this and then never builds the classes:

| Mechanic on the board | Story | Only meaningful if |
|---|---|---|
| Width class per cell; "Surveyor is blocked below its width class"; turning impossible below a class | BLD-71, BLD-78 | Some chassis fits where the Surveyor does not, or vice versa |
| Detection range scales with passage width | BLD-79 | — (world variety; stands alone) |
| Flooded cells impassable to walkers; "every entry reaches every deposit region by some chassis-passable route" | BLD-71, BLD-72 | Some chassis passes water |
| "At least one deposit per seed is reachable only through a constriction or a flooded cell" | BLD-73 | Some chassis has the key |
| "Loadout validation rejects a Swimmer with lidar as its only active sensor" | BLD-85 | The Swimmer exists |
| Pressure-limit depth per chassis | BLD-98 | More than one chassis |
| "Scout, Hauler and Swimmer are not built here — reserve IDs only if the designer asks" | BLD-98 | — |
| Surveyor only | Phase 5 (BLD-149), Phases 6–9 | — |

So the board has locks with no keys. Either the keys get a phase, or the locks are world
variety (speed, sound) and BLD-73's criterion is wrong as written. D1 is that question.

---

## 2. What was measured

All on the Phase 1 build at `d19579b`: one hand-authored 200×120 cave, seed 7, scripted
beats. Scripts are throwaway and live in the session scratchpad, not the repo. Numbers
carry over to Phase 3 as ratios and shapes, not as values.

### 2.1 Body size against the cave

The Phase 1 cave's passages are 4, 5 and 6 cells wide (diameter). The Phase 1 agent has
radius 0.6 (`AGENT_RADIUS`), so a body 1.2 cells across. Eroding the dry grid by a disc
of radius *r* and running Dijkstra from the player's shaft gives what a body of that size
can reach:

| body radius | diameter | dry cells left | % of dry | reaches from S |
|---|---|---|---|---|
| 0.6 (Phase 1) | 1.2 | 3371 | 100 | everything dry |
| 1.0 | 2.0 | 2489 | 74 | everything dry |
| 1.5 | 3.0 | 2109 | 63 | everything dry |
| 1.8 | 3.6 | 2109 | 63 | everything dry |
| 2.0 | 4.0 | 1615 | 48 | loses deposit A (behind a width-4 passage); deposit B by a 247-cell route instead of 203 |
| 2.5 | 5.0 | 1252 | 37 | nothing beyond the shaft chamber |
| 3.0 | 6.0 | 872 | 26 | nothing beyond the shaft chamber |

Reading: on this grid a body passes a passage when the width is at least one cell more
than the body (a 4.0 body is blocked by width 4, passes width 5). Every Phase 1 passage is
the same class for anything under 3.6 cells across, so the Phase 1 cave cannot tell a
Scout from a Surveyor; it can only tell a Hauler from both — and a 4-cell Hauler reaches
neither deposit. The width axis only differentiates chassis if the generator emits at least
four classes deliberately (D5) and the biome sets their proportions.

### 2.2 Water

The flooded region is 460 of 3831 free cells (12%): the sump chamber and two flooded
passages, C2→SUMP→ANC.

- **No shaft touches water.** A chassis that is literally "useless on dry rock" cannot
  leave either shaft chamber in this cave. Either the generator guarantees a flooded route
  from a shaft whenever a Swimmer is in the match, or the Swimmer can walk badly (D6).
- **The sump is a detour here, not a door.** Path lengths from S, body 1.2:

  | to | dry only | amphibious | Swimmer (dry cells cost 2.5×) |
  |---|---|---|---|
  | C2 (big hall) | 83 | 83 | 207 |
  | SUMP | — | 129 | 268 |
  | ANC (machinery) | 166 | 159 | 316 |
  | DB (deposit B) | 203 | 197 | 410 |

  An amphibious body saves 7 cells to the machinery via the sump. A Swimmer that walks at
  0.4× is slower to everything. The Swimmer's whole value is set by whether water is *the*
  way somewhere, which is a generator weight — the flooding axis — and not a chassis stat.

### 2.3 The route budget

The Phase 1 player route S→A→B→S is 576 cells of dry path. Match 480 s; the extraction
window opens at 390 s; each load is 30 s.

| speed (cells/s) | route time | plus two loads | fits before the window closes? |
|---|---|---|---|
| 0.7 | 823 s | 883 s | no; A-and-home (142 cells, 203 s + 30 s) does |
| 1.1 (Surveyor, Phase 1) | 523 s | 583 s | no — and Phase 1 knew it: the cautious policy pushes to B only while sigma is low |
| 1.4 (Phase 1's rival, "a lighter chassis") | 411 s | 471 s | barely |
| 1.7 | 339 s | 399 s | yes |

### 2.4 How far a body is heard

Phase 1's sound travels along passages (Dijkstra, flooded cells cost 0.55). Percentage of
free cells that hear an emitter at a chamber, by path range:

| emitter at | r=20 | r=40 (Phase 1 motion) | r=60 | r=80 | r=100 | r=170 (Phase 1 ping) |
|---|---|---|---|---|---|---|
| S (shaft) | 5% | 9% | 15% | 23% | 36% | 81% |
| C1 | 10% | 20% | 32% | 44% | 62% | 99% |
| C2 (big hall) | 16% | 33% | 61% | 74% | 88% | 100% |
| C3 | 10% | 17% | 48% | 70% | 89% | 100% |
| SUMP (in water) | 13% | 37% | 50% | 70% | 85% | 100% |
| ANC | 15% | 31% | 56% | 72% | 86% | 100% |
| C4 | 8% | 16% | 28% | 39% | 60% | 96% |

Reading: DESIGN's "audible across half the cave" for the Hauler is a motion-noise path
range of 80–100 cells in a cave this size. A Scout at 20 is heard over a twentieth to a
sixth of it. Water carries: the same range from the sump covers more than from a dry hall
of similar size, so a Swimmer moving in water is *louder* to the basin than a walker,
range for range.

### 2.5 Speed against the Phase 1 match

`AGENT_SPEED` swept with the scripted spoof and the ancient in place, Recall sent at
various times or not at all. Capacity 2 is the Phase 1 policy (load A, push on to B if
sigma is low); capacity 1 makes it load A and go home — a one-deposit raid.

Capacity 2, Recall at none / 180 / 240 / 300 / 360 / 420 s (six runs per speed):

| speed | loaded A at | spoof lands | own uncertainty return | extracted | max true error over the match |
|---|---|---|---|---|---|
| 0.7 | 122 s | 203 s | never | 1 of 6 (Recall 180, which landed before the spoof; 1 unit at 390 s) | 34–39 cells |
| 0.9 | 113 s | 176 s | never | 0 of 6 | 37–61 |
| 1.1 (Surveyor) | 89 s | 141 s | 392 s | 0 of 6 | 36–91 |
| 1.4 | 79 s | 205 s | never | 0 of 6 | 20–44 |
| 1.7 | 67 s | 204 s | 165 s | 1 of 6 (Recall 240; 1 unit at 390 s) | 23–28 |

Capacity 1 — load A and go home — same Recall times:

| speed | loaded A at | extracted |
|---|---|---|
| 1.1 | 89 s | 5 of 6 (Recall at 360 s lost it); unrecalled, home at 422 s |
| 1.4 | 79 s | 6 of 6, all waiting at the shaft when the window opened at 390 s |
| 1.7 | 67 s | 6 of 6, same |

Reading:

- **The greedy arc is lost at every speed** (28 of 30), the Surveyor's own 1.1 included.
  This build's Recall arc is itself under retune (BLD-8, BLD-9; BLD-105 makes "at least
  one Recall timing extracts" a Phase 3 criterion), so the absolute rates say little. What
  carries is that speed neither rescues the second leg nor makes it worse.
- **A one-deposit raid extracts at any speed** (17 of 18). The second leg is what loses
  the agent — Principle §2's "one junction further" — and no chassis stat changes that.
  A Hauler's reason to exist has to be more cargo per deposit (bays), not more deposits.
- **Speed moves the beats.** The spoof arms on displacement from the last beacon, so it
  lands where the drops fell, not at a time: 141 s at 1.1, 176 s at 0.9, 203–206 s at
  0.7, 1.4 and 1.7. The cautious policy's own uncertainty return fires at 165 s at 1.7
  (sigma grows per cell and a fast body covers the cells sooner), at 392 s at 1.1, and
  never at the other three. BLD-108's benchmark seeds are per chassis, the same way the
  ANCIENT_PHASE retune was forced by the steering change.
- **Less distance, less drift; neither gets home.** Max true error falls from 91 cells at
  1.1 to 34–39 at 0.7 (it never got far) and 23–28 at 1.7 (it turned for home early on
  its own). Drift is per cell and the window is per second: a chassis's speed buys or
  costs time, not safety.

Caveat on all of §2: one cave, one seed, scripted beats, a policy that was tuned for the
Surveyor. These numbers say what shape the problem has, not what the values are.

---

## 3. Recommendations

Each: what, why, what it costs if wrong, and a line for the designer.

### 3.1 D1 — Chassis classes are in the game

**What.** Confirm that Scout, Hauler and Swimmer are player-selectable chassis in the
shipped game, so that the width and flooding locks the board already builds have keys.

**Why.** Every document but the board assumes it (§1). Principle §2 needs depth tiers with
keys. The prep phase (DESIGN; BLD-167) is a chassis decision plus a module decision; with
one chassis it is a module picker.

**If wrong.** If the answer is no, this spike costs nothing further, and BLD-73's
constriction/flooded lock criterion and BLD-78's per-chassis width class should be deleted
so the generator does not place value nobody can take. If the answer is yes but nothing in
D3/D4/D8 is done in Phase 3, enabling a class later is a Belief schema change, a locomotion
retrofit and a content-hash bump under a live season.

Designer: [ ] yes [ ] no

### 3.2 D2 — A `ChassisId` space, four IDs reserved now

**What.** Add `pub struct ChassisId(pub u16);` beside the other identity newtypes in
ARCHITECTURE (it lists Sensor, Predicate, Action, Module, AncientKind, but a loadout is a
chassis plus modules and a chassis is not a module). Reserve in BLD-63's table: Surveyor 1,
Scout 2, Hauler 3, Swimmer 4. Never reused.

**Why.** IDs are permanent (ARCHITECTURE rule 1, DETERMINISM rule 7); reserving costs
nothing and forgetting costs a migration. A separate space keeps `Loadout` honest and lets
`MatchRecord.loadouts` name a chassis by a stable number.

**If wrong.** A u16 space with four entries used; the waste is four numbers.

Designer: [ ] yes [ ] no

### 3.3 D3 — Phase 3 ships all four chassis as content records; three are season-gated

**What.** BLD-98 writes four records, not one. The record (data only, no trait impls):

```
chassis:
  id: ChassisId                # permanent (D2)
  name
  season: u16                  # first season this record is enabled (SENSORS D19). Surveyor:
                               # the active season; Scout, Hauler, Swimmer: a later one
  body_diameter: Fx            # cells; documentation and the art silhouette
  enter_width_class: 0..3      # D5: crawl 0, narrow 1, passage 2, hall 3
  turn_width_class:  0..3      # >= enter_width_class
  slots: u8
  mass_budget: Fx
  power_budget: Fx
  max_cargo_bays: u8
  base_speed: Fx               # cells/s at the default gait
  terrain: { dry: Fx, flooded: Fx }   # D6: speed factor, 0 = cannot enter
  motion_noise_range: Fx       # cells of path range at the default gait; gaits scale it (BLD-100)
  pressure_limit_depth: Fx     # BLD-98 already requires this
  gaits: [ { name, speed_factor, noise_factor } ]      # BLD-100
  intrinsic_sensors: [SensorId]                        # odometry (1), near-field (2), transponder
                                                       # interrogator (6), depth gauge (7),
                                                       # self-report (11) — SENSORS §3.3
```

The loadout validator rejects a loadout whose chassis's season is later than the pack's
active season. Tests exercise every rule in §3.9 using the not-yet-enabled records, so the
rules exist and are proven before any class is playable. The content hash covers the
season-enabled set (SENSORS D18), so bringing a chassis into the active season changes the
hash, which is the season semantics BLD-203 wants.

Reconciled 2026-09-06: the record carried `enabled: bool`, which contradicts SENSORS D19 —
a season is a monotone gate and entries are never disabled, only retired — so the flag becomes
a `season` field. Bringing the Scout and the Hauler in before launch (D10) is a pre-season
edit of that field, legal because no live season exists yet. See
PHASE-3-OPEN-QUESTIONS.md §4.

Reference policies, the benchmark set and the 1,000-match gate run the Surveyor only.

**Why.** This is the cheapest moment to make the *shape* right: registries keyed by
stable ID, defined in data, validated at build time (ARCHITECTURE extension rules). The
data itself is a few dozen lines. Doing it here is what makes D10's later stories
"flip a flag, make a model" rather than "design a chassis system".

**If wrong.** About one working day of records and tests nobody plays. If D1 is no, skip.

Designer: [ ] yes [ ] no

### 3.4 D4 — Locomotion and the cell classifier read the chassis record

**What.** BLD-78's "Surveyor is blocked below its width class and by flooded cells"
becomes "an agent is blocked below its chassis's `enter_width_class`, cannot turn below
its `turn_width_class`, and moves at `base_speed × terrain[cell class] × gait`". BLD-71's
single classification query takes the chassis's terrain viability as an argument (or the
chassis id) rather than assuming a walker. No Surveyor constant exists anywhere in
locomotion.

**Why.** It is the same amount of code either way; the only difference is where the number
lives. Written as data now, the Phase 6 and Phase 9 stories are content and art. Written
as constants, they are a refactor of the one function locomotion, acoustics and sensors
all share (BLD-71 makes duplicate classification logic a test failure, so the refactor
touches all three).

**If wrong.** Half a day of parameter plumbing on a system that only ever runs one chassis.

Designer: [ ] yes [ ] no

### 3.5 D5 — Passage width is a per-cell class with four values

**What.** BLD-71's "width class" per cell gets four values: crawl (0), narrow (1),
passage (2), hall (3). Widths per class in cells **(guess, from §2.1's "body + 1"
rule)**: crawl 2–3, narrow 3–4, passage 4–5, hall 5 and up. BLD-72 must emit all four in
every seed (add to its "mixed" criterion), with the proportion per class a biome weight —
that is the passage-width axis, "cathedral to crawl". Chassis name the class they enter
and the class they can turn in:

| chassis | enters | turns in | body diameter (cells) |
|---|---|---|---|
| Scout | crawl | crawl | 0.8 **(guess)** |
| Surveyor | narrow | passage | 1.2 (Phase 1 `AGENT_RADIUS` 0.6) |
| Hauler | hall | hall | 4.0 **(guess; the erosion table says 4.0 is the first size the Phase 1 cave blocks)** |
| Swimmer | narrow | passage | 1.2 **(guess)** |

**Why.** §2.1: with only Phase 1's widths, nothing under 3.6 cells is distinguishable. A
crawl class is what makes the Scout a key; a hall class is what makes the Hauler blocked.
Turning is BLD-78's own criterion ("turning around is impossible below a content width
class") and needs a class one step above entering for the Surveyor or it never fires.

**If wrong.** The class boundaries are content and can move; the number of classes is a
schema for the cave and should not. Four is the smallest that gives every chassis a
different answer.

Designer: [ ] yes [ ] no

### 3.6 D6 — Terrain viability is a speed factor per terrain; the Swimmer walks badly

**What.** `terrain: { dry, flooded }` per chassis, each a speed factor, 0 meaning the
cell class is a wall to that chassis. Walkers: dry 1.0, flooded 0. Swimmer: flooded 1.0,
dry 0.4 **(guess)**. "Useless on dry rock" is read as *slow and loud on dry rock*, not
*cannot enter*.

**Why.** §2.2: no Phase 1 shaft touches water; a Swimmer that cannot walk cannot enter the
cave unless the generator floods a route from a shaft. Making it amphibious keeps BLD-72's
connectivity guarantee ("every entry reaches every deposit region by some chassis-passable
route") satisfiable without a Swimmer-specific carve, and makes the flooding weight, not a
hard rule, decide how good the Swimmer is in a given season.

**If wrong.** If the designer wants a pure swimmer, D7's generator rule must also
guarantee a flooded route from at least one shaft whenever the Swimmer is enabled, which
is a carving constraint (BLD-72, about a day) and a stronger fairness question (which
shaft?).

Designer: [ ] yes [ ] no

### 3.7 D7 — Locks only where an enabled chassis holds the key

**What.** BLD-73's "at least one deposit per seed is reachable only through a constriction
or a flooded cell" becomes: the generator reads the enabled chassis set; a crawl-only
deposit is placed only if a chassis with `enter_width_class = crawl` is enabled; a
flooded-only deposit only if a chassis with `terrain.flooded > 0` is enabled; the test
asserts one such lock per seed *among the locks that have keys*. With the Phase 3 pack
(Surveyor only) that means: no locks, and the parity test is honest.

**Why.** As written, BLD-73 places value in Phases 3–5 that no chassis can take, and
counts it in per-region value parity, so parity is false on the day it is measured. When
the Scout ships (Phase 6) crawl locks appear; when the Swimmer ships (Phase 9) flooded
locks appear — the cave changes, which is how DESIGN says seasons should feel.

**If wrong.** The designer may *want* visible, unreachable deposits as a tease for the
chassis to come. Then keep BLD-73 as written and exclude locked deposits from the parity
sum instead (a smaller change), and accept that a sonar carrier will map value it cannot
reach. Say which.

Designer: [ ] yes [ ] no

### 3.8 D8 — Schema room for the Swimmer, in Phase 3

**What.** Four small things, so that enabling the Swimmer in Phase 9 is content and art,
not a Belief schema migration under a live season:

1. **A depth-gauge SensorId**, assigned in BLD-63's table beside odometry and the
   near-field sense (chassis-intrinsic, as they are). Hardware-honest: a pressure sensor.
   It produces one return: the medium the body is in.
2. **`SelfReport.medium: Dry | Submerged`** in BLD-77's Belief, fused from that return.
   A later predicate (`submerged`) reads it; gait and noise switch on it.
3. **A water *character* on the range return and the map point** — `SurfaceCharacter
   { Rock, Water }` on `Return::RangeBearing` and on `MapPoint`, beside the point's
   `source: SensorId`. BLD-85's lidar returns the water surface as a wall; on a Swimmer's
   belief map that "wall" is a door. Like Phase 1's sound characters it is a property of
   the signal (a specular return off water looks different from rock), not an
   identification. No World read.

Reconciled 2026-09-07: item 1 said "reserved" — SENSORS §3.3 ships the depth gauge as
SensorId 7, status Phase 3, intrinsic to every chassis. Item 3 said "a `Waterline`
map-point source"; a point's `source` is the SensorId that produced it and water is a
`SurfaceCharacter`, so there is no `Waterline` source. See PHASE-3-OPEN-QUESTIONS.md §5,
§11, §14 and §24.
4. **Chassis-aware `blocked(x, y)`** in BLD-101: the belief-map clearance query takes the
   agent's own terrain viability from its loadout (it knows its own body; not a truth
   leak) so a Swimmer steers into water and a walker steers round it from the same map.

**Why.** Items 2 and 3 are fields in serialized, hashed types. Adding them later changes
the state hash and every replay's schema; BLD-203 forbids editing existing content in a
season and a schema bump is worse than a content bump. Reserving them now is a quarter-day
each. Item 4 is where the "one classification function" rule (BLD-71) meets Belief: a
walker and a swimmer must disagree about the same map point, and the place they disagree
is the chassis record, not a second classifier.

**If wrong.** Half a day of fields that stay `Dry` and `Rock` forever.

Designer: [ ] yes [ ] no

### 3.9 D9 — The loadout rules the validator enforces

Stated so BLD-98 can write a test per line:

| # | Rule | Source |
|---|---|---|
| R1 | Exactly one chassis per loadout, and its `season` is at or before the pack's active season. | D3 |
| R2 | Module slots used ≤ `slots`; mass ≤ `mass_budget`; power ≤ `power_budget`. | BLD-98 already |
| R3 | Cargo bays mounted ≤ `max_cargo_bays`. | DESIGN "almost no carry" / "heavy carry" |
| R4 | A Swimmer with lidar and no sonar is rejected. Lidar plus sonar on a Swimmer is accepted (lidar for the dry approach, sonar under water). | PHASE-1-OPEN-QUESTIONS Part 4; BLD-85 |
| R5 | Sonar and lidar are alternatives, not a pair, on every chassis except the Swimmer — **(guess)**; the Part 4 decision says "the player picks" and never says both. Say if both is allowed everywhere; then R4 is the only chassis-specific sensor rule. | Part 4 |
| R6 | The beacon drop interval is much larger than beacon acquisition range for every chassis — BLD-98's existing invariant, checked per chassis if either becomes chassis-dependent. | tuning.py |
| R7 | No rule for the Hauler beyond R2/R3: "blocked by constrictions" is the world (D5), not the validator. | — |

A more general form of R4 was considered — *for every terrain a chassis can enter, at
least one mounted mapping sensor works there* — and rejected: it would reject a passive-
only Surveyor, which DESIGN explicitly allows ("a quiet agent heavy on passive sensing").

Designer: [ ] yes [ ] no

### 3.10 D10 — When each chassis becomes playable

**Scout and Hauler: Phase 6.** One new story in epic BLD-160 — proposed key BLD-208,
"Enable the Scout and the Hauler" — depending on BLD-167 (lobby and prep: the first chassis
picker), BLD-149 (the model pipeline), BLD-142 (walkers vs pods), BLD-100 (gaits), and
required by BLD-176 (the networked playtest).

- *Why there.* Their trades are relative to rivals — quiet against loud, fits against
  blocked, fast against slow — and to the prep decision, and Phase 6 is where both first
  exist. BLD-176 is the only multi-human playtest before the ship decision (BLD-179) and
  it should see a chassis choice. Their sim mechanics are Surveyor mechanics with other
  numbers (§2.1, §2.5). Their art rides the pipeline BLD-149 builds.
- *Why not Phase 5.* Phase 5's gate is Phase 1's spectator test re-run; more chassis
  there is more variables in a test that must compare like with like.
- *Why not Phase 8.* Phase 8 builds only what the cut list names (BLD-188) and has no
  playtest of its own before strangers.
- *If wrong, too early:* about 8 working days of art on two bodies that a Phase 6
  playtest might change. *Too late:* a shipped prep phase with no chassis decision, and
  DESIGN's prep line false; the crawl lock never seen by a human before early access.
- *Fallback.* If Phase 6 runs long, the Hauler slides to BLD-189 (Phase 8 content) and
  the Scout stays: it is cheaper (three mounts, one bay) and it is the one that tests the
  lock.

**Swimmer: Phase 9, season one.** One new story in epic BLD-195 — proposed key BLD-209,
"Enable the Swimmer as season one's world change" — depending on BLD-203 (season config)
and BLD-149.

- *Why there.* DESIGN's own example of a season is "a season of deeply flooded, thermally
  stratified systems", its example of a transition event is "a flood", and it says a
  season adds "a new module or chassis class, occasionally — but the world change should
  do most of the work". §2.2 says the Swimmer's value *is* the flooding weight: in a
  Phase-1-like cave water is a detour and no shaft touches it. A chassis whose worth is
  set by a generator weight is a season's chassis. It is also the most expensive of the
  three (swimming locomotion is a new animation set; belief needs D8), and BLD-179 may
  choose the forensic product for Phase 8, in which case no chassis matters at ship.
- *The reading of Principle §2.* "Past the sump" on a walker's route means deeper than
  the sump as a landmark; the Swimmer turns the landmark into a door. Season one is
  "the water rose, and there is a machine that swims" — a shared event and a new key at
  once.
- *If wrong, too late:* if the sump is meant to be a depth key at ship, the shipped loot
  ladder is missing its middle rung; move BLD-209 into Phase 6 at the same cost there.
  *Too early:* about 11 days in Phase 6 on a chassis whose value depends on flooding
  weights nobody has tuned yet.

Designer (Scout Phase 6): [ ] yes [ ] no
Designer (Hauler Phase 6, fallback Phase 8): [ ] yes [ ] no
Designer (Swimmer Phase 9 season one): [ ] yes [ ] no

### 3.11 D11 — Proposed numbers, for the Phase 3 records

All **(guess)** except where a Phase 1 value is cited. They exist so BLD-98 has something
to write and D12 has something to run; tuning is the enabling story's job.

| field | Scout | Surveyor | Hauler | Swimmer |
|---|---|---|---|---|
| id | 2 | 1 | 3 | 4 |
| season (Phase 3 pack) | later | active | later | later |
| body diameter (cells) | 0.8 | 1.2 (Phase 1) | 4.0 | 1.2 |
| enters / turns in | crawl / crawl | narrow / passage | hall / hall | narrow / passage |
| slots | 3 (DESIGN) | 6 (DESIGN) | 8 (DESIGN) | 5 |
| max cargo bays | 1 | 2 (Phase 1 capacity 2, one unit per bay) | 4 | 2 |
| base speed dry (cells/s) | 1.4 (Phase 1's rival: "a lighter chassis") | 1.1 (Phase 1) | 0.7 | 0.4 |
| base speed flooded | 0 | 0 | 0 | 1.0 |
| motion noise range (path cells) | 20 (§2.4: 5–16% of the cave) | 40 (Phase 1; 9–37%) | 100 (36–89%, DESIGN's "half the cave") | 40, in water (37% from the sump) |
| pressure limit (fraction of biome max depth) | 0.5 | 0.8 | 0.8 | 1.0 |
| mass / power budgets | not proposed: no module has a mass or power yet (BLD-98 assigns) | | | |

A note on the Hauler's arithmetic from §2.3 and §2.5: at 0.7 cells/s it cannot do two
deposits in a Phase 1 match, but A-and-home is 203 s of walking plus 4 bays × 30 s of
loading = 323 s, inside the 390 s window, for four units against the Surveyor's two. That
is the trade DESIGN describes — heavy carry against slow and loud — and it only works if
a deposit yields more than two units to a body that can hold them. Deposit yield per
visit is BLD-92's content; it should not be capped at 2.

A note on the Scout: with one bay it is the courier for the things that weigh nothing —
a behaviour downloaded from the machinery (BLD-103's `yields()` seam) — and the key to
crawl-locked deposits. That gives "almost no carry capacity" a job in an extraction game.
Proposal, not in any document.

Designer: [ ] yes [ ] no

### 3.12 D12 — The harness may run a later-season chassis behind a flag

**What.** `harness run --allow-future-season` — run an entry whose season is later than the
active one — bypasses R1 only. Nothing else in the workspace can. Phase 3's batch gate does
not use it.

Reconciled 2026-09-06: the flag was `--allow-disabled-content`, which named a `bool` that no
longer exists; it reads against the season gate instead. See PHASE-3-OPEN-QUESTIONS.md §4
and §44.

**Why.** With D3, D4 and D11 in place, a Scout or Hauler match runs headless in Phase 3
for a quarter-day of flag plumbing. That means Phase 6's enabling story starts from a
seed-to-outcome table rather than from the first-ever run, and BLD-108's beat-sheet drift
per chassis (§2.5) is known before it matters. The Swimmer is excluded: without D8's
steering it cannot use water anyway.

**If wrong.** It is an addition CLAUDE.md would normally refuse. A quarter-day, and a
door that the compile-fail tests must keep shut (the flag lives in the harness crate, not
in `blindside-sim`).

Designer: [ ] yes [ ] no

---

## 4. Cost in working days

| Phase | Story | Work | Days |
|---|---|---|---|
| 3 | BLD-63 | `ChassisId`; four ids; depth-gauge SensorId assigned (7) | 0.25 |
| 3 | BLD-98 | Four records; `season`; rules R1–R7; tests against the later-season records | 1.0 |
| 3 | BLD-78 | Enter/turn class and terrain factors read from the chassis record | 0.5 |
| 3 | BLD-71, BLD-72 | Four width classes; every seed emits all four; class proportion as a biome weight | 0.5 |
| 3 | BLD-73 | Lock-only-with-key rule | 0.25 |
| 3 | BLD-77, BLD-85, BLD-101 | `SelfReport.medium`; `SurfaceCharacter` on the range return and the map point; chassis-aware `blocked()` | 0.5 |
| 3 | BLD-38 / harness | `--allow-future-season` | 0.25 |
| **3** | | | **3.25** |
| 6 | BLD-208 (new) | Content flip; cautious-Scout and greedy-Hauler reference policy variants | 1.0 |
| 6 | BLD-208 | Benchmark seeds: a crawl-locked deposit; a hall-only Hauler route | 1.0 |
| 6 | BLD-208 | Scout model: three mounts, one bay, walker rig from BLD-149 | 3.5 |
| 6 | BLD-208 | Hauler model: eight mounts, four bay meshes | 4.5 |
| 6 | BLD-208 / BLD-167 | Chassis picker showing more than one; silhouette read at distance | 0.5 |
| **6** | | human-gated on art, about two round trips | **10.5** |
| 9 | BLD-209 (new) | Flooded locomotion on the heightfield; medium-dependent gait and noise | 1.5 |
| 9 | BLD-209 | Swimmer steering through water via D8's `blocked()`; sonar maps water as open | 1.0 |
| 9 | BLD-209 | Generator: flooded locks switch on; flooded route from a shaft if D6 is "pure swimmer" | 1.0 |
| 9 | BLD-209 | Reference policy; flooded benchmark seeds | 1.5 |
| 9 | BLD-209 | Model and swimming locomotion set | 6.0 |
| 9 | BLD-203 | Season config: enable flag, flooding weight, "the water rose" transition event | 0.5 |
| **9** | | human-gated on art and the season note | **11.5** |
| | | **Total** | **25.25** |

Art days are the least certain numbers here **(guess)**: BLD-149 estimates 8 days for the
Surveyor including the pipeline; each further body is assumed to cost about half plus its
module meshes, and the Swimmer's locomotion is assumed to be a new set rather than a
retarget.

---

## 5. Board changes this implies (not made; the board is the designer's)

- BLD-63 "done when": add `ChassisId` and the depth-gauge SensorId (7, intrinsic) to the
  table.
- BLD-98: replace "Scout, Hauler and Swimmer are not built here — reserve IDs only if the
  designer asks" with "present as records carrying a later `season`; rules R1–R7; tests use
  them".
- BLD-73: lock criterion conditional on enabled keys (D7), or locked value excluded from
  parity (the alternative).
- BLD-72: "every seed emits all four width classes" alongside "mixed flooded and dry".
- BLD-77: `SelfReport.medium`; `MapPoint` carries `character: SurfaceCharacter { Rock,
  Water }` beside its `source: SensorId`.
- BLD-85: the water-surface return is a `RangeBearing` with `source = lidar` and
  `character = Water`.

Reconciled 2026-09-07: both lines said the water surface is a map-point *source*; source is
the SensorId that produced the point and water is a character on it. See
PHASE-3-OPEN-QUESTIONS.md §11, §14 and §24.
- BLD-101: `blocked()` takes the agent's terrain viability.
- BLD-108: "beat-sheet seeds are re-verified per enabled chassis".
- New BLD-208 in epic BLD-160, between BLD-167 and BLD-176.
- New BLD-209 in epic BLD-195, on BLD-203.
- BLD-149: note that it is the pipeline story and later bodies are estimated against it.
- GLOSSARY *Chassis* entry: unchanged; it already names all four.

---

## 6. Guesses

Everything below was chosen by this spike, not given by a document or a measurement.

- Width class boundaries in cells (crawl 2–3, narrow 3–4, passage 4–5, hall ≥5); the
  "body + 1" passing rule is measured on the Phase 1 raster and may not hold on the
  Phase 3 heightfield.
- Body diameters: Scout 0.8, Hauler 4.0, Swimmer 1.2.
- Turn class one above enter class for the Surveyor and Swimmer.
- Swimmer slots 5; max cargo bays 1/2/4/2; one unit per bay.
- Speeds 1.4 / 0.7 / 0.4 dry and 1.0 flooded (1.1 and the rival's 1.4 are Phase 1 values).
- Motion noise ranges 20 / 100 / 40-in-water (40 dry is Phase 1).
- Pressure limits 0.5 / 0.8 / 0.8 / 1.0 of biome max depth.
- The Swimmer walks at 0.4× rather than not at all (D6).
- R5: sonar and lidar are alternatives on non-Swimmers.
- All art estimates in §4.
- The Scout as the courier for machinery yields (§3.11).
- That the flooding weight, not a stat, is what makes the Swimmer worth picking — inferred
  from one cave (§2.2).
- Proposed story keys BLD-208 and BLD-209 (the board assigns keys; these are the next two
  after BLD-207).

---

## 7. Design problems found on the way

1. **Locks without keys (BLD-73).** As written, Phases 3–5 place at least one deposit per
   seed that no chassis can reach and count it in value parity. D7.
2. **"Useless on dry rock" strands the Swimmer.** In the Phase 1 cave no shaft touches
   water. Either the Swimmer walks (D6) or the generator floods a route from a shaft
   whenever it is enabled — which is a fairness question, because it is one shaft's route.
3. **"Fragile" has nothing to bind to.** The sim has death and no damage model (collapse
   and the ancient kill outright; `SelfReport.damage` exists as a field). The Scout's
   fragility here is a shallower pressure limit and nothing else. If fragility should mean
   more, that is a damage model, which no story builds and this spike does not propose.
4. **The Hauler needs halls that do not exist yet.** In a cave with Phase 1's widths a
   4-cell body reaches neither deposit (§2.1). The hall fraction per biome is the Hauler's
   balance lever and no story parameterises it; D5 adds it.
5. **Speed buys time, not safety (§2.5).** Drift is per cell, the window is per second;
   a slow chassis loses on the clock and a fast one drifts sooner. Neither survives the
   greedy leg in this build. The Hauler's justification is bays, and deposit yield per
   visit (BLD-92) must exceed two units for that to be real. Match length (DESIGN guesses
   ten minutes; Phase 1 tuned eight; BLD-161 decides) moves this directly.
6. **The beat sheet is chassis-dependent (§2.5).** The spoof lands 60 s later at 0.7
   than at 1.1. Every enabled chassis is another re-verification of BLD-108's seeds.
7. **What a Scout is for in an extraction game.** DESIGN gives it "almost no carry
   capacity". Principle §2 says the cool things are blocks, and blocks weigh nothing.
   The Scout as the crawl key and the yield courier is a proposal (§3.11) that makes the
   class coherent; without something like it the Scout is a Survey-mode chassis in an
   Extraction-mode game, and Survey mode is Phase 9 (BLD-204).
8. **Sound in water is louder, not quieter (§2.4).** A Swimmer moving in flooded passage
   is heard further than a walker at the same emitter range. "Unmatched below the
   waterline" is about access, not stealth; the reference policy and the design notes
   should not assume a submerged agent is hidden.
