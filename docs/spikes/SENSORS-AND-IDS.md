# BLD-63 — Sensor set, module list, content format and permanent IDs

**Status: proposal for designer sign-off. Nothing here is assigned until the designer
ticks it.** Written 2026-09-06. No code in the workspace is changed by this spike.

IDs are permanent (ARCHITECTURE rule 1, DETERMINISM rule 7). A number that ships in one
replay or one saved policy can never be reused. That is why this document exists before
BLD-68 writes a single content file, and why every number below is a recommendation with
its reason and its cost if wrong, not an assignment.

Every decision ends with a line the designer can answer in place:

    Designer: [ ] yes  [ ] no  — notes:

An unanswered line is an open question, not a default. Where a value below is a guess it
is marked **[guess]**; where it was measured it says where.

---

## 0. What this is built on

**Documents read.** CLAUDE.md, GLOSSARY, ARCHITECTURE, DETERMINISM, ROADMAP (Phase 3 and
Part 3), DESIGN-PRINCIPLES (wins over DESIGN.html), DESIGN.html, PHASE-1-OPEN-QUESTIONS
Part 4, PHASE-2-JUNCTION-TEST, PHASE-2-OPEN-QUESTIONS, PHASE-0-HARNESS, and the board
stories BLD-19/20/26/30 (Phase 0, in progress), BLD-61..66, BLD-68, BLD-71, BLD-74,
BLD-83..106, BLD-108, BLD-142, BLD-163, BLD-171, BLD-174, BLD-175, BLD-180/181, BLD-185.

**Code read.** `phase1/sensing/sensor_rig.py` (the complete Phase 1 sensor list),
`phase1/sensing/returns/*`, `phase1/tuning.py`, `phase1/belief/belief.py`,
`phase1/truth/*`, `phase1/match/sim.py`, and the Phase 0 branch `claude/phase-0-harness`
(read-only via `git show`): `crates/blindside-sim/src/ids.rs` already defines `SensorId`,
`PredicateId`, `ActionId`, `ModuleId`, `AncientKindId` as `u16` newtypes plus `AgentId(u32)`
and `Tick(u64)`; `crates/blindside-content/src/lib.rs` is a stub with `CONTENT_SCHEMA = 0`;
the harness `MatchRecord` is JSON; the lint's constrained set is sim/vm/gen and its
dependency allow-list is `[blindside-vm, blindside-content, fixed, blake3]`.

**Measured.** Two kinds of measurement were run for this spike; both scripts are in the
session scratchpad, not the repo.

1. *Phase 1 return census.* `python -m phase1 --headless` for both kits (`--player-sensor
   sonar|lidar`) on seeds 7, 8, 9, with the sensor rig's six methods wrapped to count calls,
   returns and wall time. Cave and beat sheet are fixed by `tuning.SEED`; the seed argument
   only changes agent noise, so three seeds is a noise check, not a scenario sweep.
2. *Content-format proof.* A scratch Rust binary (outside the workspace, floats allowed)
   using `fixed 1.31.0`, `blake3 1.8.7`, `serde 1.0.229`, `serde_json 1.0.151`, `toml 0.8`,
   proving the Fx-as-string parse path and the two hash semantics. Results in section 4.

### Phase 1 return census (seed 7; seeds 8 and 9 agree within noise)

| Sensor method | Kit | Calls / match | Returns / call | Returns / match | Wall per call |
|---|---|---|---|---|---|
| `_odometry` | both | 9,600 (every tick) | 1.0 | 9,600 | 3.2–3.7 µs |
| `_nearfield` | both | 2,400 (every 4 ticks) | 1.4–2.4 | 3,098–5,837 | 58–69 µs |
| `_passive` | both | 7,280–9,600 | 0.1 | 540–1,081 | 140–340 µs |
| `_sonar` | sonar, per ping | 14–18 (cautious) / 52–60 (aggressive) | 59.4–60.3 | 844–3,618 | 0.77–1.0 ms |
| `_lidar` | lidar, per sweep | 300–301 (every 1.5 s) | 75.6–77.0 | 22,760–23,091 | 1.18–1.27 ms |
| `_beacons` | both | 9,600 | 0.001–0.004 | 3–41 fixes | ~2 µs |
| cargo return | player only | 600 (a 30 s load dwell at 20 Hz) | 1.0 | 600 | — |

Three numbers from that table carry decisions below:

- **Near-field is most of the map for a sonar carrier.** Player, sonar kit, seed 7: 6,007
  map points, of which 5,110 (85%) are near-field, 867 sonar, 30 false. Seeds 8 and 9:
  87% and 81%. In the lidar kit it is 20% (5,837 of 28,597). Without near-field a cautious
  sonar agent's map is one-seventh the size.
- **An active sample is 60–77 returns, not 8.** ARCHITECTURE's `Sensor::sample` returns
  `SmallVec<[Return; 8]>`. Every sonar ping (60 rays + 2 false) and every lidar sweep (90
  rays, ~76 hits) spills that to the heap. This belongs to BLD-61/BLD-74; it is recorded
  here because the census is the evidence.
- **Lidar's silence is real and measurable.** The rival's passive sensor received 81–94
  `ping` bearings per match when the player carried sonar, and exactly 2 (the scripted
  echo) when the player carried lidar. That is the whole case for a typed emission
  channel (BLD-74) and for the lidar cluster tracker (BLD-89).

Passive acoustic dominates sensor cost (2.1–3.3 s of a 6.2–9.4 s match in Python, all in
`SoundField` Dijkstra builds). That is BLD-64's problem and is noted, not solved, here.

---

## 1. The Phase 3 sensor set

### 1.1 Reading "the six sensors"

ROADMAP says "the six sensors" and never lists them. DESIGN.html describes eight sensing
sources. ARCHITECTURE's `Return` has six variants. The reading that reconciles them:
"six" is the six kinds of *observation* in `Return` — Bearing (passive), RangeBearing
(sonar), Anomaly (magnetometer), Optical, Structural, Fix (beacon and terrain share it) —
with dead reckoning folded into `integrate_motion` and terrain-relative navigation sharing
`Fix` with beacons. That is eight DESIGN sources producing six return shapes. Phase 1 then
added two things DESIGN never named: lidar (a second active module) and the near-field
sense (PHASE-1-OPEN-QUESTIONS pushback 5, approved and built). BLD-61 has already flagged
that `Return` needs an odometry variant and a relative beacon-fix variant; BLD-92 requires
inventory to change only through a return, which needs a self-report variant.

So the honest count for Phase 3 is **eleven sensors producing eight return shapes**: six
that cost a slot and five that are part of any chassis. This is an interpretation of an
ambiguous phrase, not a fact; it is the first thing to say no to.

Reconciled 2026-09-06: nine return shapes became eight and the slotted/intrinsic split 7/4
became 6/5 — terrain-relative navigation is a module with no SensorId and no `Return` (it is
a `BeliefUpdater` stage, ARCHITECTURE-RECONCILIATION §5), `Fix` is not a return at all, and
the depth gauge takes the freed SensorId 7; see PHASE-3-OPEN-QUESTIONS.md §5 and §13.

**D1. Phase 3 ships the eleven sensors in table 1.2, no more and no fewer.**
Reason: every one is either in DESIGN, in ARCHITECTURE's `Return`, or built and measured in
Phase 1; nothing is invented. Cost if wrong: a sensor cut later leaves a retired
SensorId (cheap); a sensor added later after policies ship is a season block (also cheap).
The expensive mistake is a *shape* change to `Return`, which is BLD-61's, not this.

    Designer: [ ] yes  [ ] no  — notes:

### 1.2 The table

Columns: what the sensor returns (the `Return` variant it produces; variants marked † are
the additions BLD-61 has flagged, named here so the ID table can reference them), what it
emits (the typed `Emission` BLD-74 specifies: `None | Acoustic | Optical`), its cost
(slot / mass / power placeholders, all **[guess]**; compute cost is the Phase 1 measurement),
whether it is a slotted module or chassis-intrinsic, and the Phase 1 evidence.

| # | Sensor | Returns | Emits | Cost (slot/mass/power) | Module or intrinsic | Phase 1 evidence |
|---|---|---|---|---|---|---|
| 1 | **odometry** (IMU + leg encoders) | `Odometry { forward, turn }` † | None | 0 / 0 / 0 — part of the chassis | **intrinsic** | `_odometry`: true delta corrupted by scale bias 0.055, heading bias 0.11°/cell, small random walks. 9,600 returns/match, 3 µs each. Drift is born here and nowhere else. |
| 2 | **near-field** (own motion noise off walls within ~2.5 cells; on hardware: proximity/bump sensing) | `RangeBearing { range, angle, quality }` with `source = SensorId(2)` | None (it *listens*; the motion noise itself is the chassis's emission, registered by gait — BLD-83/100) | 0 / 0 / 0 | **intrinsic** | `_nearfield`: 8 rays, range 2.5, every 4 ticks, quality 0.28. Supplies 81–87% of a sonar carrier's map points (measured above). Approved in PHASE-1-OPEN-QUESTIONS pushback 5 as "what a real machine would have". |
| 3 | **passive acoustic** (hydrophone array) | `Bearing { angle, quality, character }` — character is `ping / tone / signature / crash`, a property of the signal, never an identity | None | 1 / 1 / 1 **[guess]** | **module** (`passive_array`) | `_passive`: path-length ranges 40/170/80/170 cells, bearing noise 4°→22°, deaf 1 s after own ping. 540–1,081 bearings/match. Hears rivals, the ancient signature, crashes, echoes. DESIGN mounts it on the flank as a module; BLD-98 lists it as a module. |
| 4 | **active sonar** | `RangeBearing` with `source = SensorId(4)`; includes the false returns | **Acoustic** — audible basin-wide for 3 s; every passive listener in range gets a `ping` bearing | 1 / 1 / 2 **[guess]**; compute 0.8–1.0 ms per ping | **module** (`sonar`) | `_sonar`: 120° arc, 60 rays, range 30, rays cross water (marched against `~FREE`), 2 false returns/ping. 59.4–60.3 returns per ping. Loadout alternative to lidar (Part 4 decision). |
| 5 | **lidar** | `RangeBearing` with `source = SensorId(5)` | **Optical** — a visible light; a tell only to an optical sensor with line of sight (BLD-85/95); registers no acoustic emitter | 1 / 1 / 1 **[guess]**; compute 1.2–1.3 ms per sweep | **module** (`lidar`) | `_lidar`: 360°, 90 rays, range 18, every 1.5 s, no false returns, stops at the waterline and returns it as a wall (designer's call, Part 4). 75.6–77 returns/sweep; builds ~4× the map of sonar without a sound. Rival heard 2 ping bearings vs 81–94 (measured). |
| 6 | **transponder interrogator** (hears every team's beacons in range, including the survey-placed shaft) | `Transponder { beacon, range, angle }` † — relative; Belief resolves own-team ids against its own `KnownBeacon` record, which is how a relocated beacon lies (BLD-86), and records foreign ids in `Belief.foreign_beacons` with no fix | None **[guess — see D5]** | 0 / 0 / 0 | **intrinsic** (the *rack* that drops beacons is a module — section 2) | `_beacons`: rising-edge fix on entering range 6 (shaft 10), noise 0.35; in Phase 1 only the owner's beacons answered; spoof reasserts every 8 s at range 18. 3–41 fixes/match. |
| 7 | **depth gauge** (pressure sensor) | `SelfReport { medium }` † — the medium the body is in | None | 0 / 0 / 0 | **intrinsic** | Not built. CHASSIS D8.1 asks for it: `SelfReport.medium` is what a later `submerged` predicate reads and what medium-dependent gait and noise switch on, and adding a field to a hashed type after a season ships is a schema migration. |
| 8 | **magnetometer** | `Anomaly { rough_direction, strength }` | None | 1 / 1 / 1 **[guess]** | **module** (`magnetometer`) | Not built. DESIGN: long range, no emission, coarse, false finds on noisy rock (BLD-91). |
| 9 | **optical** (camera + light) | `Optical { patch }` plus the identification path of BLD-95 | **Optical** — light on = visible with line of sight | 1 / 1 / 2 **[guess]** | **module** (`optical`) | Not built. DESIGN: identification not detection; silt destroys it. The only way a Contact becomes an identity (BLD-93/95). |
| 10 | **structural monitor** | `Structural { time_to_failure }` | None | 1 / 1 / 1 **[guess]** | **module** (`structural_monitor`) | Not built. DESIGN: warns of collapse seconds before; "costs a slot to survive". BLD-94. |
| 11 | **self-report** (cargo scale, power, damage, module health) | `SelfReport { cargo, power, damage, modules: ModuleHealth }` † | None | 0 / 0 / 0 | **intrinsic** | `CargoReturn`: 600/match during the load dwell; "how an agent discovers it spent thirty seconds loading where there was no deposit" (returns/cargo.py). BLD-92: inventory changes only through a return. |

Reconciled 2026-09-07: row 11's return field is `modules: ModuleHealth`, the name
ARCHITECTURE-RECONCILIATION §4 and PHASE-3-OPEN-QUESTIONS.md §11 carry, not `module_health`.

Ancient signatures, rival motion, crashes and echoes are not sensors: they are emitters
heard through #3. A wreck is not a sensor: sonar returns it as a `RangeBearing` and optical
identifies it (BLD-93).

Terrain-relative navigation is **not** in this table. Reconciled 2026-09-06: it is ModuleId 6
with no SensorId and no `Return` — a `BeliefUpdater` stage the module enables, because its
three inputs (this tick's range returns, the agent's own map, its pose estimate) are all in
Belief and none is in World; the depth gauge takes the freed SensorId 7, row 6's return is
renamed `Transponder`, and `FixSource::Beacon` stays on the Belief side. See
PHASE-3-OPEN-QUESTIONS.md §5, §10, §11 and §13.

### 1.3 The decisions inside the table

**D2. Lidar gets its own `SensorId` and `ModuleId` and shares `Return::RangeBearing` with
sonar; the return carries `source: SensorId`, and there is no `Lidar` return variant.**
Reason: a `Return` variant describes the *shape* of an observation (range and bearing);
which instrument produced it is the source id. Belief's map code then handles one shape
for sonar, lidar, near-field and any ranging sensor a season adds, and BLD-77's "every map
point carries source id" falls out. What differs between sonar and lidar — emission
channel, arc, range, the waterline rule, false-return count, sediment sensitivity — is all
content data and the `emits()` answer, not a type. Cost if wrong: if a future sensor needs
a field `RangeBearing` lacks, a new variant is added then; nothing retroactive. If instead
a `Lidar` variant were added now, every consumer branches on it forever.

    Designer: [ ] yes  [ ] no  — notes:

**D3. The near-field sense is chassis-intrinsic, not a module.**
Reason: it is the agent hearing its own footfalls off the wall beside it — there is no
hardware to unbolt, and on a real machine it is the proximity/bump layer every mobile
robot has. Measured: without it a sonar carrier's map loses 81–87% of its points and "a
corridor walked without pinging leaves no points at all" (tuning.py), which contradicts the
Phase 1 spec's "sparse where it has only passed through" and starves BLD-101's map-aware
steering. Making it a module would make "no near-field" a loadout that cannot steer.
Cost if wrong: if the designer wants it purchasable, a `ModuleId` is added later and the
chassis default loadout carries it; the SensorId does not change.

    Designer: [ ] yes  [ ] no  — notes:

**D4. Odometry and self-report are chassis-intrinsic.**
Reason: DESIGN calls dead reckoning "IMU and odometry" and puts "gait + power" on the
chassis; a body that cannot count its own steps or weigh its own hold is not a body.
Both are still `Sensor` impls with `SensorId`s so the hardware seam is uniform (a driver
answers "how far did I step" the same way it answers "what did the sonar hear") and so
BLD-82's "drift is born in the sensor layer" has a sensor to be born in. Cost if wrong:
none structural; an intrinsic sensor can be given a slot cost in data later.

    Designer: [ ] yes  [ ] no  — notes:

**D5. The transponder interrogator (hearing beacons) is chassis-intrinsic and emits
nothing; the beacon *rack* (deployables) is a module.**
Reason: every agent must be able to hear its shaft — the survey-placed beacon is the only
truth anchor (BLD-88) and Recall's spiral search ends only when "the real transponder
answers" (BLD-105). An agent without a rack still needs to get home. Emission is a guess
in the other direction: Phase 1 modelled no interrogation ping, and DESIGN describes
beacons as things you *drop*, not things you shout at. A rival finds a beacon because the
interrogator answers to every team's beacons in range and Belief records the foreign ids it
cannot fix on, which is the observable BLD-106 and BLD-174 read. Cost if wrong: if the
designer wants interrogation to be loud ("every fix announces you"), `emits()` for SensorId 6
becomes `Acoustic` in data with a small signature; no ID changes.

Reconciled 2026-09-06: this decision used to say the beacon itself is the emitter a rival
hears. Nothing else models that — ACOUSTIC-BUDGET §2.6's emitter load has no beacons — so the
sentence is replaced by the foreign-beacon return above; see PHASE-3-OPEN-QUESTIONS.md §10.

    Designer: [ ] yes  [ ] no  — notes:

**D6. Passive acoustic is a module (`passive_array`), not intrinsic.**
Reason: DESIGN mounts a "passive array" on the flank, its loadout-tension paragraph speaks
of an agent "heavy on passive sensing", and BLD-98 lists it as a module. The consequence
is stated so it is chosen and not discovered: an agent that drops the array to carry a
second cargo bay is deaf — no contacts, no ancient warning, no crash — and the "legible
before lethal" guarantee holds only for agents that can hear. That is the same trade DESIGN
already makes for the structural monitor ("costs a slot to survive things that would
otherwise simply kill you"). The Surveyor's stock loadout carries it (section 2). Cost if
wrong: if the designer wants hearing to be universal, the module is retired and SensorId 3
becomes intrinsic; a retired ModuleId is the only scar.

    Designer: [ ] yes  [ ] no  — notes:

**D7. Returns carry the producing `SensorId` and never a truth tag. Phase 1's
`PointSource.FALSE` does not port.**
Reason: Phase 1 tagged spurious sonar points `FALSE` and let that tag reach Belief
(point_source.py: "carried through into Belief and rendered exactly like SONAR, differing
only in confidence"). The renderer ignored it, but the tag *was* ground truth on the
belief side of the line, and a predicate could have read it. In Phase 3 a false sonar
return says `source = sonar` and a low quality, and nothing else. Same rule as
`FixSource` and the echo (BLD-80: no `is_echo`). Cost if wrong: none; this only removes a
leak.

    Designer: [ ] yes  [ ] no  — notes:

---

## 2. The module list

Every slotted thing, with slot / mass / power placeholders. **All three numbers in every
row are guesses**: DESIGN gives slot *counts* per chassis (Scout 3, Surveyor 6, Hauler 8,
Swimmer unstated) and never a mass or power figure; Phase 1 had no loadout. They are
integers so BLD-98's validator has something to reject; the designer replaces them.

| ModuleId | Module | Sensor it carries | Slot / mass / power **[guess]** | Ships in | Source |
|---|---|---|---|---|---|
| 1 | `passive_array` | SensorId 3 | 1 / 1 / 1 | Phase 3 | DESIGN "Flank · passive array"; BLD-83, BLD-98 |
| 2 | `sonar` | SensorId 4 | 1 / 1 / 2 | Phase 3 | DESIGN "Dorsal · active sonar"; Part 4; BLD-84 |
| 3 | `lidar` | SensorId 5 | 1 / 1 / 1 | Phase 3 | Part 4; BLD-85. An alternative to 2 on every chassis except the Swimmer, which may mount both (CHASSIS R4; BLD-85's rule is "lidar as its *only* active sensor") |
| 4 | `beacon_rack` | none (interrogator is intrinsic, D5) | 1 / 1 / 0; carries N beacons, N **[guess 6]** = Phase 1's ~530 cells of travel ÷ 45-cell drop interval ≈ 12 drops, halved so the rack runs out | Phase 3 | DESIGN "Belly · beacon rack"; BLD-86 "finite count per loadout" |
| 5 | `cargo_bay` | none | 1 / 1 / 0; `capacity` is content, default **1** unit per bay (CHASSIS D11) | Phase 3 | DESIGN "Belly · cargo bay"; BLD-92 |
| 6 | `terrain_nav` | none — the module enables a `BeliefUpdater` stage, not a sensor | 1 / 1 / 1 | Phase 3 | DESIGN; BLD-90 |
| 7 | `magnetometer` | SensorId 8 | 1 / 1 / 1 | Phase 3 | DESIGN "Flank · magnetometer"; BLD-91 |
| 8 | `optical` (camera + light) | SensorId 9 | 1 / 1 / 2 | Phase 3 | DESIGN "Head · optical + light"; BLD-95 |
| 9 | `structural_monitor` | SensorId 10 | 1 / 1 / 1 | Phase 3 | DESIGN; BLD-94 |
| 10 | `beacon_cloner` (the spoof module) | none | 1 / 1 / 1; finite count **[guess 2]** | Phase 3 | BLD-106: "content entry with slot/mass/power and a finite count" |
| 64 | `behaviour_reader` (recover a policy from a wreck) | none | reserved | Phase 6 | GLOSSARY *Wreck*; BLD-171 |
| 65 | `decoy_emitter` | none | reserved | Phase 6 if BLD-163 chooses it | DESIGN interference table; BLD-174 |
| 66 | `noise_flooder` | none | reserved | Phase 6 if chosen | BLD-175 |
| 67 | `silt_release` | none | reserved | Phase 6 if chosen | BLD-175 (uses BLD-96's cloud) |
| 68 | `collapse_charge` | none | reserved | Phase 6 if chosen | BLD-175 |

Beacon theft (BLD-174) needs no module: it is a pick-up action that returns the beacon to
the actor's rack. Following needs nothing. Gait is chassis data, not a module (BLD-100).

Reconciled 2026-09-06: row 3's flat "mutually exclusive" gains the Swimmer exception that
CHASSIS R4 needs and BLD-85's own wording implies, see PHASE-3-OPEN-QUESTIONS.md §43.
Reconciled 2026-09-06: row 5's "capacity 2" becomes a content field defaulting to one unit
per bay — Phase 1's capacity 2 is a Surveyor with two bays, not one bay holding two — see
PHASE-3-OPEN-QUESTIONS.md §43 and §45.
Reconciled 2026-09-06: row 6 carries no SensorId, per the note under table 1.2; see
PHASE-3-OPEN-QUESTIONS.md §5.

**D8. The module list above is the Phase 3 list, and rows 64–68 are reserved with those
numbers and no entries.**
Reason: every Phase 3 row is named by BLD-98 or BLD-106; every reserved row is named by
BLD-163/171/174/175, which say "ids reserved in the content ID table". Cost if wrong: a
cancelled reservation is marked cancelled and never reused; sixteen bits is cheap.

    Designer: [ ] yes  [ ] no  — notes:

**D9. The Surveyor's stock loadout (six slots) is: `passive_array`, `sonar` *or* `lidar`,
`beacon_rack`, `terrain_nav`, and two `cargo_bay`.** **[guess]**
Reason: it makes the choices DESIGN wants visible in the default — loud or quiet, and
"what do I give up for a third cargo bay". A player who drops `terrain_nav` for a bay
has no counter to a spoof; that is the design working. Cost if wrong: it is data in
`chassis.toml`; changing it changes the content hash and nothing else.

Reconciled 2026-09-06: the free slot becomes a second `cargo_bay`, because a bay now holds
one unit and Phase 1's capacity 2 has to come from somewhere; see
PHASE-3-OPEN-QUESTIONS.md §43 and §45.

    Designer: [ ] yes  [ ] no  — notes:

---

## 3. The ID tables

### 3.1 The numbering rule

**D10. One rule for every ID kind:**

- `0` is never assigned. A zeroed struct is invalid, and the loader rejects it.
- `1–63`: the set Phase 3 ships, assigned in this document.
- `64–127`: named reservations for Phases 4–7, listed here with their numbers so later
  stories (BLD-106, BLD-163, BLD-171, BLD-174, BLD-175, BLD-180, BLD-185, BLD-204/205) do
  not collide. A reservation has no content entry until its story lands.
- `128–255`: unnamed, kept free for the same phases' surprises. Assigned sequentially.
- `256–65534`: season blocks (DESIGN-PRINCIPLES 1: "a season ships blocks"), assigned
  sequentially in the order they ship. No per-season sub-ranges: a range would tempt
  someone to "fit" an entry, and the season is a field on the entry, not a property of its
  number.
- `65535` is a sentinel and never assigned.
- An ID's number carries **no meaning**. Ranges are a convention for reading the table,
  never something code derives from (DETERMINISM rule 7). Code looks IDs up; it never
  computes them.

Reason: contiguous shipped blocks read at a glance; reservations are visibly separate; the
rule is the same for all eight kinds so it can be checked by one test. Cost if wrong: none
that is irreversible — the ranges are documentation, and an entry that lands outside its
range is a review comment, not a desync.

    Designer: [ ] yes  [ ] no  — notes:

### 3.2 The retiring rule

**D11. Entries are never deleted. To retire one, add `retired = "YYYY-MM-DD"` to it (and,
for a predicate, `retired_value = true|false`); the entry stays in its file, its number
stays in this table marked retired, and `content/retired.toml` duplicates `(kind, id)` so
that a deleted entry is still caught.** The build fails on: a duplicate id within a kind; a
live entry whose id is in `retired.toml`; a retired predicate without `retired_value`; a
loadout for a new match that names a retired module (old replays still load: they are
pinned to their own pack by hash, section 4). A cancelled reservation is marked cancelled
and treated exactly like retired.

Reason: ARCHITECTURE rule 1 verbatim, made mechanical. Cost if wrong: none; this is the
cheapest possible enforcement of a rule everyone already agrees with.

    Designer: [ ] yes  [ ] no  — notes:

### 3.3 SensorId

| Id | Name | Kind | Return | Emits | Status |
|---|---|---|---|---|---|
| 1 | `odometry` | intrinsic | `Odometry` † | None | Phase 3 |
| 2 | `near_field` | intrinsic | `RangeBearing` | None | Phase 3 |
| 3 | `passive_acoustic` | module 1 | `Bearing` | None | Phase 3 |
| 4 | `sonar` | module 2 | `RangeBearing` | Acoustic | Phase 3 |
| 5 | `lidar` | module 3 | `RangeBearing` | Optical | Phase 3 |
| 6 | `transponder` | intrinsic | `Transponder` † | None (D5) | Phase 3 |
| 7 | `depth_gauge` | intrinsic | `SelfReport { medium }` † | None | Phase 3 |
| 8 | `magnetometer` | module 7 | `Anomaly` | None | Phase 3 |
| 9 | `optical` | module 8 | `Optical` | Optical | Phase 3 |
| 10 | `structural_monitor` | module 9 | `Structural` | None | Phase 3 |
| 11 | `self_report` | intrinsic | `SelfReport` † | None | Phase 3 |
| 64–127 | — | — | — | — | no named reservations; nothing on the board adds a sensor before a season |

Reconciled 2026-09-06: `terrain_nav` had SensorId 7 and a `Fix` return and has neither — it is
ModuleId 6 enabling a `BeliefUpdater` stage — and CHASSIS D8.1's depth gauge takes the freed
7, so this section no longer says no sensor reservation is needed. Row 6's return is renamed
`Transponder`. See PHASE-3-OPEN-QUESTIONS.md §5, §11 and §13.

### 3.4 ModuleId

As section 2: 1 `passive_array`, 2 `sonar`, 3 `lidar`, 4 `beacon_rack`, 5 `cargo_bay`,
6 `terrain_nav`, 7 `magnetometer`, 8 `optical`, 9 `structural_monitor`, 10
`beacon_cloner`; reserved 64 `behaviour_reader`, 65 `decoy_emitter`, 66 `noise_flooder`,
67 `silt_release`, 68 `collapse_charge`.

### 3.5 ChassisId — a new newtype

**D12. Add `ChassisId(u16)` to `ids.rs` beside the five ARCHITECTURE names, and keep
chassis and modules as two registries.**
Reason: ARCHITECTURE's extension table has one row "Chassis / modules — pure data", and
BLD-68 counts "seven registries" with chassis/modules as one. But a loadout is *one*
chassis plus *N* modules, the two have different fields (size class, gait set, pressure
limit, slot count versus slot cost), and BLD-65 asks for chassis IDs to be reserved. Two
tables keyed by two newtypes is the honest shape; folding them into one `ModuleId` space
would make "a Surveyor in a module slot" representable. This contradicts BLD-68's count
(seven becomes eight) and is said plainly. Cost if wrong: a newtype is twenty lines; if the
designer wants one registry, chassis take ModuleIds 32–47 instead and `ChassisId` is
deleted before anything ships.

    Designer: [ ] yes  [ ] no  — notes:

| Id | Chassis | Slots (DESIGN) | Status |
|---|---|---|---|
| 1 | `surveyor` | 6 | Phase 3, active season (BLD-98) |
| 2 | `scout` | 3 | Phase 3 pack, later season (BLD-65, CHASSIS D3/D10) |
| 3 | `hauler` | 8 | Phase 3 pack, later season (BLD-65, CHASSIS D3/D10) |
| 4 | `swimmer` | 5 **[guess]** | Phase 3 pack, later season (BLD-65, CHASSIS D3/D10); loadout rule "cannot carry lidar as its only active sensor" (Part 4, BLD-85) |

Reconciled 2026-09-06: Scout, Hauler and Swimmer take 2/3/4, not 64/65/66, because CHASSIS D3
puts all four records in the Phase 3 pack and D10's own rule puts anything in the pack in
1–63; the Swimmer's slot count is CHASSIS D11's guess of 5, not this spike's 4. See
PHASE-3-OPEN-QUESTIONS.md §7 and §44.

### 3.6 PredicateId

| Id | Predicate | Params | Status | Source |
|---|---|---|---|---|
| 1 | `unexplored_branch_exists` | — | Phase 3 | Phase 2 day-one block |
| 2 | `uncertainty_gt` | θ (Fx, fitted) | Phase 3 | Phase 2 day-one block |
| 3 | `carrying_cargo` | — | Phase 3 | Phase 2 day-one block |
| 4–n | whatever the Phase 2 gate report (BLD-59) adds | | assigned when that report exists | BLD-97: "plus any addition the Phase 2 report records" |
| n+1 | `signature_within` | window, q_min | Phase 3 | DRIVER §7; the cautious freeze and the investigate |
| n+2 | `at_unfinished_place` | kind, radius | Phase 3 | DRIVER §7; absorbs `at_shaft` as `at_unfinished_place(shaft, r)` |
| n+3 | `ping_ready` | cooldown | Phase 3 | DRIVER §7 |
| n+4 | `unmapped_ahead` | n | Phase 3 | DRIVER §7; Phase 1's cautious ping discipline |
| n+5 | `beacon_due` | cells | Phase 3 | DRIVER §7 |
| n+6 | `action_running` | id | Phase 3 | DRIVER §7 and D6; the latch a memoryless tree needs |
| 64 | `signature_quality_ge` | θ | **cancelled** — superseded by `signature_within` | Phase 1 candidate (BLD-97) — the cautious freeze |
| 65 | `fix_surprise_ge` | θ | reserved | Phase 1 candidate — the only belief-legal spoof tell |
| 66 | `contact_stationary` | window | reserved | Phase 1 candidate; the echo/decoy tell (BLD-89, BLD-174) |
| 67 | `ticks_since_ping_ge` | n | **cancelled** — superseded by `ping_ready` | Phase 1 candidate |
| 68 | `contact_heard_within` | ticks | **cancelled** — superseded by `signature_within` | Phase 1 candidate; Part 4: without one of 68/69 "do I ping" is a cooldown, not a decision |
| 69 | `best_contact_quality_ge` | θ | reserved | Phase 1 candidate |
| 70 | `being_followed` | window | reserved | BLD-163 candidate |

Reconciled 2026-09-06: the six blocks the reference policies need are assigned (numbered after
BLD-59's additions, hence `n+`), and 64, 67 and 68 are cancelled because the parameterised
`signature_within` and `ping_ready` supersede them; a cancelled reservation is treated exactly
like a retirement (D11). See PHASE-3-OPEN-QUESTIONS.md §8.

**D13. Phase 3 assigns the Phase 2 vocabulary (1–3 plus whatever BLD-59 records) *and* the
six blocks the reference policies need, as real content entries with stable ids. Reserved
predicates 64, 67 and 68 are cancelled; 65, 66, 69 and 70 stay reserved and unimplemented
until Phase 4 or a season adds them as data.**
Reason: DESIGN-PRINCIPLES §1 — nothing that consumes blocks is written over a fixed set by
name — and the Phase 3 reference policies are tree *data* over the registries (DRIVER D1,
D8), not Rust that can read Belief where no predicate exists. BLD-97's "do not expand it" and
BLD-102's "reproduce Phase 1's cautious and aggressive behaviours" cannot both hold, and the
cost of choosing BLD-97 was measured (DRIVER §2.3: the rival's death at the machinery falls
to path luck at 2/8 and the cautious agent cannot freeze). R5 is still answered by the Phase 2
gate: these are batch-coverage blocks, not the player's day-one vocabulary, and which of them
players hold on day one is a separate content call.

Reconciled 2026-09-06: this decision was "reserve, do not assign", written over hand-written
Rust reference policies; it flips to "assign" as a consequence of the driver decision, which
makes the reference policies tree data. See PHASE-3-OPEN-QUESTIONS.md §8 and §20.

    Designer: [ ] yes (assign the six)  [ ] no (reserve only; the reference policies lose the freeze and the investigate)  — notes:

### 3.7 ActionId

| Id | Action | Params | Status | Source |
|---|---|---|---|---|
| 1 | `take_branch` | — | Phase 3 | Phase 2 day-one block |
| 2 | `return_to_beacon` | — | Phase 3 | Phase 2 day-one block |
| 3 | `active_scan` | — | Phase 3 | BLD-99 names it `ping`; see D14 |
| 4 | `drop_beacon` | — | Phase 3 | BLD-99 |
| 5 | `load` | — | Phase 3 | BLD-99 |
| 6 | `abort_to_shaft` | — | Phase 3 | BLD-99; what the Recall command runs (BLD-105) |
| 7 | `interface` | — | Phase 3 | BLD-103: "an Interface action that consumes [yields()] as a timed, slowed, cargo-free dwell" |
| 8 | `set_gait` | gait index | Phase 3 (P2) | BLD-100 |
| 9 | `clone_beacon` | — | Phase 3 | BLD-106, the spoof action; unavailable without module 10 |
| 10 | `hold` | — | Phase 3 **[guess]** | Phase 1's cautious policy stops dead on a signature (`ANCIENT_HOLD_QUALITY`); nothing on the board names the action that does that. Also what the Phase 6 `Hold` command would run. DRIVER's `wait` folds into it. |
| 11 | `noop` | — | Phase 3 | DRIVER §4.3, D4: the optional-branch idiom, an ActionId in content rather than a new node kind |
| 12 | `investigate` | — | Phase 3 | DRIVER §7: walk toward a contact bearing; the aggressive reference policy |
| 64 | `salvage` | — | reserved | BLD-171; needs module 64 |
| 65 | `pick_up_beacon` | — | reserved | BLD-174 (beacon theft); needs module 4 |
| 66 | `deploy_decoy` | — | reserved | BLD-174; needs module 65 |
| 67 | `flood_noise` | — | reserved | BLD-175; needs module 66 |
| 68 | `release_silt` | — | reserved | BLD-175; needs module 67 |
| 69 | `induce_collapse` | — | reserved | BLD-175; needs module 68 |

Player commands (`Recall`, `Hold`, `Go quiet`, `Abort`) are **not** ActionIds. They are a
`Command` enum in `MatchRecord` with its own schema-versioned discriminants (BLD-30); each
maps to an action the policy driver runs (Recall → 6, Hold → 10). Keeping them apart means
a season can add an action without touching the replay format.

Reconciled 2026-09-06: `noop` (11) and `investigate` (12) are added because the reference
policies are tree data and need both as blocks; `wait` is folded into `hold` rather than given
a number. See PHASE-3-OPEN-QUESTIONS.md §8 and §27.

**D14. The active-sample action is named `active_scan`, not `ping`, and fires whichever
active module (2 or 3) the loadout carries.**
Reason: Phase 1's `cmd.ping` already drove both sonar and lidar; a lidar carrier that
"pings" is a name lying about an emission channel, in a game whose central question is
"do I ping". The action is the request; the module answers with sound or light. BLD-99's
`ping` is renamed, nothing else changes. Cost if wrong: a name is data; the number is what
is permanent.

    Designer: [ ] yes  [ ] no  — notes:

**D15. `hold` (ActionId 10) is added to Phase 3's action set.** **[guess]**
Reason: the cautious reference policy needs a way to stop and listen, and `MotorCmd` with
speed 0 is a motor request, not a block a tree can name. Without it the Phase 1 freeze
behaviour is only expressible outside the action registry. Cost if wrong: an unused
ActionId, retired.

    Designer: [ ] yes  [ ] no  — notes:

**Open, not decided here.** Phase 1's `TRAVEL` (follow a route of survey waypoints) and
Phase 2's `take_branch` (left-most unexplored passage at the current junction) are the
only navigation primitives named anywhere. A generated cave with chambers, sumps and dead
ends may need something between them for BLD-101/BLD-102 to reproduce Phase 1's routes.
Nothing is reserved for it; if BLD-61/62 decide one is needed it takes the next number in
1–63.

### 3.8 AncientKindId

| Id | Kind | Status | Source |
|---|---|---|---|
| 1 | `fixed_cycle` | Phase 3 | BLD-103; Phase 1 reference 75 s period, 9 s warning, 4 s lethal, radius 9 |
| 64 | *(Phase 7 system A)* | reserved, unnamed | BLD-180/181 |
| 65 | *(Phase 7 system B)* | reserved, unnamed | BLD-180/181 |

### 3.9 BiomeId

| Id | Biome | Status | Source |
|---|---|---|---|
| 1 | `reference` — mixed flooded and dry, moderate on every axis **[guess]** | Phase 3 | BLD-71 "one biome ships"; BLD-72 "mixed flooded and dry passages appear in every seed" |
| 64 | `dry_clear` — dry, clear, non-reflective | reserved; needed by BLD-108's R9 seed ("a dry clear cave is quiet") | BLD-108. Whether it is a second biome entry or an axis override on a harness fixture is BLD-71's; the number is held either way |

### 3.10 ModeId

| Id | Mode | Status | Source |
|---|---|---|---|
| 1 | `extraction` | Phase 3 | DESIGN-PRINCIPLES 2: the core mode; BLD-104 |
| 64 | `endurance` | reserved | Phase 7, BLD-185 |
| 65 | `survey` | reserved | BLD-204 |
| 66 | `race` | reserved | BLD-205 |

### 3.11 Things that are code enums, not content IDs

Kept out of the ID tables on purpose; listed so nobody reserves numbers for them:
`Emission { None, Acoustic, Optical }` (BLD-74); `SoundCharacter { Ping, Tone, Signature,
Crash }` (a property of a signal — if a Phase 7 ancient needs a fifth character it is a
schema bump on `Return`, which BLD-77's serialisation already versions);
`SurfaceCharacter { Rock, Water }` (the same, for an echo off water rather than rock);
`Medium { Dry, Submerged }`; `FixSource { Beacon(BeaconId), Terrain }`; `Command`. Runtime entity ids (`AgentId`, `BeaconId`,
`WreckId`, `DepositId`, `AncientId`) are BLD-69's and are per-match, never content.

Reconciled 2026-09-07: `SurfaceCharacter` and `Medium` were added to the hashed types on
2026-09-06 (ARCHITECTURE-RECONCILIATION §4, CHASSIS D8.2/D8.3) and were missing from this
list, which exists so nobody reserves numbers for them. See PHASE-3-OPEN-QUESTIONS.md §11
and §24.

---

## 4. Content file format, hashing and the constrained-crate question

### 4.1 What was proved in scratch

A scratch Rust binary (session scratchpad `fxproof/`, not in the workspace) did the
following, and the numbers below are its output:

1. **`I32F32::from_str` is a pure-integer path.** In `fixed 1.31.0` `src/from_str.rs`, the
   `FromStr` impl (line 1284) calls a `const fn from_str` built on `parse_bounds` (line
   1082), all integer arithmetic; the file's only `f64` uses are inside `#[cfg(test)] mod
   tests` from line 1307. For the eight Phase 1 constants tried (`0.055`, `0.11`, `0.0013`,
   `1.5`, `34`, `0.1`, `22.5`, `-0.38`) the string path and the `from_num(f64)` path gave
   identical bits — so the string path costs nothing in precision and removes the float.
2. **A float literal in a content file is rejected by the type.** With `Fx` deserialised
   only from a string or an integer, `range = 30.0` fails to load (`TOML parse error at
   line 14, column 9`). No `f64` reaches our code.
3. **Enabled-set hashing does what rule 5 needs; file-bytes hashing does not.** Two TOML
   packs with the same two enabled sensor entries but different formatting, different
   entry order, one extra `season = 2` entry and one `retired` entry: file-bytes BLAKE3
   hashes differ (`6e24d8ba…` vs `94f8ee3c…`); the enabled-set hash for season 1 is
   identical for both (`b3fe9366…`), and for season 2 it changes (`055874c2…`).
4. **JSON parses the same struct to the same bits** (`0x000000aa00000000` for `"170"` both
   ways), so the format choice is about people, not machines.
5. **A 300-entry pack parses in 1.9 ms.** Parse cost is not a factor.

### 4.2 Format

**D16. Content files are TOML, one file per kind under `content/`: `sensors.toml`,
`modules.toml`, `chassis.toml`, `predicates.toml`, `actions.toml`, `ancients.toml`,
`biomes.toml`, `modes.toml`, `retired.toml`, and `pack.toml` (schema version, active
season).**
Reason: content is written and read by a person, and this project's numbers come with
their measurements attached — `tuning.py` is one long argument for values that carry a
"Measured:" note beside them, and CLAUDE.md's definition of done requires guesses to be
listed. TOML has comments; JSON does not, and `_comment` fields are a hash-visible hack.
RON also has comments and native enums, but it is Rust-shaped, has one maintainer's worth
of tooling, and the designer is not a Rust programmer. TOML's weaknesses (verbose nesting,
strings for enums) do not bite flat tables of entries. Cost if wrong: the loader is one
crate (D20) and the typed structs do not care; switching format later costs a day and
changes no hash, because the hash is over the typed entries (D18), not the bytes.

    Designer: [ ] yes  [ ] no  — notes:

**D17. Every `Fx` in content is written as a decimal string or an integer, never a float
literal: `range = "30"`, `bias = "0.055"`, `capacity = 1`. The loader parses strings with
`fixed`'s `FromStr` and rejects TOML floats.**
Reason: proved above; it is the only way "no float enters through data" is a type check
rather than a code review. The quotes are the small ugliness that buys it. Cost if wrong:
none; if a nicer syntax is wanted later the parser is one function.

Reconciled 2026-09-07: the integer example was `capacity = 2`; a bay holds one unit by
default (§2 module 5), so the illustration uses 1. Cosmetic; the rule is unchanged. See
PHASE-3-OPEN-QUESTIONS.md §43.

    Designer: [ ] yes  [ ] no  — notes:

Example of the shape (illustrative; values are the Phase 1 numbers and are all guesses
until BLD-84 lands):

```toml
# content/sensors.toml
[[sensor]]
id = 4
name = "sonar"
module = 2                  # ModuleId that carries it; absent for intrinsic sensors
emission = "acoustic"
arc_deg = "120"
rays = 60
range = "30"                # cells. Measured 2026-09-06: lidar at 18 built ~4x the points
range_noise = "0.25"        # plus 2% of range
bearing_noise_deg = "1.2"
false_returns = 2
audible_s = "3"
self_deaf_s = "1"
season = 1                  # first season this entry is enabled

# content/retired.toml
[[retired]]
kind = "predicate"
id = 9
name = "example_that_never_existed"
retired = "2027-01-01"
retired_value = false
```

### 4.3 Hash coverage

**D18. `content_hash()` is BLAKE3 over the canonical serialisation of the *enabled set* —
every non-retired entry whose `season <= pack.active_season`, sorted by `(kind, id)`, each
field in declared order, `Fx` as `I32F32` bits little-endian, strings as bytes plus NUL —
prefixed by `CONTENT_SCHEMA` and `active_season`. Not over file bytes.**
Reason: ARCHITECTURE rule 5 says new content ships behind a season flag "so it does not
invalidate the live season", and rule 2 says the hash goes in every replay. If the hash
covers the file bytes, adding a flagged-off season-2 entry changes it, and every season-1
replay, benchmark listing (BLD-108 "versioned with the content hash") and market
verification is invalidated by content nobody can use yet — rule 5 becomes a lie. Enabled-
set hashing was proved above to survive reformatting, reordering and flagged-off additions
while still changing when the enabled set changes. Cost if wrong — and this is the one
place the cost is serious: a field left out of the canonical serialisation is a balance
change that goes unhashed, which is exactly the silent-replay-divergence DETERMINISM
fears. Mitigation is BLD-68's mutation test per field, made mandatory: every field of
every entry type has a test that changing it changes the hash. File-bytes hashing has the
opposite failure (it invalidates too much) and no silent mode; if the designer prefers
loud-and-wrong over quiet-and-tested, say no here.

Note for BLD-20/BLD-26: the Phase 0 branch's `content_hash()` lives in the harness and
hashes `CONTENT_SCHEMA` only; BLD-26's default is file bytes. This decision is the answer
BLD-20's question list is waiting for, and BLD-26 should land the enabled-set form in
`blindside-content` so the Phase 0 fixtures' hashes are not changed twice.

    Designer: [ ] yes (enabled set)  [ ] no (file bytes)  — notes:

**D19. A season is a monotone gate: each entry carries `season = N`, the first season in
which it is enabled; `pack.toml` carries `active_season`; entries are never disabled, only
retired (D11).**
Reason: DESIGN "Preserve the archive. Old behaviors stay usable"; DESIGN-PRINCIPLES 1 "a
season ships blocks". A per-season enable *list* would let a season remove a block, which
the archive rule forbids, and would make the enabled set a function of two files. Cost if
wrong: if a season must ever pull a block, that is a retirement with a date, and the
archive rule is the thing that changed, not the format.

    Designer: [ ] yes  [ ] no  — notes:

### 4.4 Is `blindside-content` a constrained crate?

**D20. Yes — with a split. `blindside-content` (typed registries, `Fx` fields, `content_hash`,
validation; dependencies `fixed`, `blake3` only) joins the lint's constrained set. The TOML
parser lives in a new small crate `blindside-content-loader` (unconstrained; `serde`,
`toml`) that produces the typed pack and is used by the harness, net and client — never by
sim, vm or gen.**
Reason: BLD-20 asks whether content joins the lint scope because it is in sim's dependency
tree but outside DETERMINISM's constrained set, and the lint's own doc says "`blindside-
content` is an allowed dependency of every constrained crate and is not itself in
`CONSTRAINED_CRATES`, so none of these rules are enforced there … the allow-list bounds
the blast radius; it does not close the hole." Floats can only enter through data, and
data enters through this crate. Constraining the typed crate closes the hole at the type
level (no `f32`/`f64` field can exist; the lint says so in CI), and moving the parser out
keeps `serde` and `toml` — which contain `f64` internally — out of the constrained
dependency tree, so ARCHITECTURE's "keeps determinism auditable by reading one dependency
tree" stays literally true. The alternative (one crate, `toml` added to the allow-list) is
a smaller diff and relies on D17's deserialiser to keep floats out; it works, and was
proved above, but it puts a parser with a float type inside the audited tree. Cost if
wrong: a tenth crate in ARCHITECTURE's layout (a doc edit) and one more `Cargo.toml`. The
lint's `ALLOWED_DEPENDENCIES` gains nothing; its `CONSTRAINED_CRATES` gains one path.
BLD-63 asks for this decision to be recorded in DETERMINISM.md; that file is the designer's
to edit and is not touched by this spike.

    Designer: [ ] yes (constrained + loader crate)  [ ] no (one crate, toml allow-listed)  — notes:

**D21. `MatchRecord` stays JSON (Phase 0's choice, BLD-30); content is TOML. Two formats,
on purpose.**
Reason: a record is written by a machine and read by a machine; a content file is written
by a person with a comment. Forcing one format on both costs the comments or the
compactness. Cost if wrong: the harness already depends on `serde_json`; adding `toml` to
the loader crate is one dependency. If the designer wants one format, JSON for both is the
only option that does not change Phase 0, and the "Measured:" notes move to a sibling
`content/NOTES.md`, which experience with `tuning.py` says will rot.

    Designer: [ ] yes  [ ] no  — notes:

---

## 5. Cross-check against the board

Where this proposal agrees with a story it says so; where it contradicts one it says so.

| Story | Agrees | Contradicts / changes |
|---|---|---|
| BLD-20 (Phase 0 question round) | hasher BLAKE3; MatchRecord JSON | answers its "content-hash coverage" and "content-crate lint scope" items: enabled set (D18), constrained + loader (D20) |
| BLD-26 (content hash) | location: `blindside-content`; 256-bit | built-so-far hashes `CONTENT_SCHEMA` only and defaults to file bytes; D18 picks the story's own alternative branch |
| BLD-30 (MatchRecord) | JSON stays (D21) | — |
| BLD-61 (core types) | `Return` gains `Odometry`, `Transponder` (relative), and here `SelfReport`; `SmallVec<[Return; 8]>` is too small (60–77 measured) | adds one variant (`SelfReport`) to BLD-61's list, from BLD-92's requirement; `Fix` leaves `Return` |
| BLD-65 (chassis) | Surveyor 1; Scout 2, Hauler 3, Swimmer 4, all four in the Phase 3 pack | — (D12 introduces `ChassisId`, which BLD-65 assumes exists) |
| BLD-68 (registries) | stable IDs, retired ledger, season flag, hash, Fx-or-int fields, "a test pins whether a flagged-off entry changes it" → it does not (D18) | **eight registries, not seven**: chassis and modules are separate (D12) |
| BLD-71 (biomes) | one biome, stable id | reserves 64 `dry_clear` for BLD-108's R9 seed |
| BLD-74 (sensor module) | typed `Emission`; source id on returns; RNG purpose includes sensor_id | — |
| BLD-83 (passive + near-field) | near-field has its own SensorId (2); own motion noise is a chassis emitter, not a sensor | near-field is intrinsic (D3), which BLD-83 left to this spike |
| BLD-84 (sonar) | ModuleId 2 + SensorId 4; loud | — |
| BLD-85 (lidar) | ModuleId 3 + SensorId 5; `Emission::Optical`; same `RangeBearing` (D2); Swimmer rule | — |
| BLD-86 (beacons) | rack finite count; relative fix; rising edge | interrogator intrinsic and silent (D5) — BLD-86 is silent on who can hear a beacon |
| BLD-89 (contact tracks) | `contact_stationary` reserved (66) | — |
| BLD-90 (terrain nav) | ModuleId 6, **no** SensorId; home is the `BeliefUpdater` (ARCH §5) | — |
| BLD-91 (magnetometer) | ModuleId 7 + SensorId 8; emits None | — |
| BLD-92 (deposits, inventory) | inventory via a return | names that return: `SelfReport` from SensorId 11 (D4) |
| BLD-93 (wrecks) | no sensor; sonar sees, optical identifies | — |
| BLD-94 (structural) | ModuleId 9 + SensorId 10 | — |
| BLD-95 (optical) | ModuleId 8 + SensorId 9; `Emission::Optical` | — |
| BLD-96 (silt) | no id; `silt_release` (67) reserved for BLD-175 on top of it | — |
| BLD-97 (predicates) | Phase 2's three | **expands the batch vocabulary**: six reference-policy predicates assigned (D13), candidates 64/67/68 cancelled, 65/66/69/70 still reserved |
| BLD-98 (Surveyor + modules) | module list; sonar/lidar alternatives except on the Swimmer; reserved ids for BLD-171/163 | near-field and odometry are **not** modules (D3, D4); stock loadout D9 is a guess BLD-98 did not have; four chassis records ship, not one |
| BLD-99 (actions) | take_branch, return_to_beacon, drop_beacon, load, abort_to_shaft | `ping` → `active_scan` (D14); adds `interface` (from BLD-103), `hold` (D15), `noop` and `investigate` (D13) |
| BLD-100 (gait) | `set_gait` ActionId 8; gait is chassis data | — |
| BLD-103 (ancients) | AncientKindId 1; `interface` action | — |
| BLD-104 (modes) | ModeId 1 `extraction` | — |
| BLD-106 (spoof) | ModuleId 10 + ActionId 9 | — |
| BLD-108 (benchmark) | biome 64 for R9 | — |
| BLD-163/174/175 (interference) | ModuleIds 65–68, ActionIds 65–69 reserved | — |
| BLD-171 (behaviour recovery) | ModuleId 64, ActionId 64 reserved | — |
| BLD-180/181 (two ancients) | AncientKindIds 64, 65 reserved | — |
| BLD-185, 204, 205 (modes) | ModeIds 64–66 reserved | — |

---

## 6. Everything guessed in this document

- All slot / mass / power numbers in section 2 and table 1.2.
- Beacon rack count 6; cloner count 2.
- The Surveyor stock loadout (D9).
- Swimmer slot count 5 (CHASSIS D11's guess; this spike guessed 4 — see §3.5).
- `hold` as an action (D15).
- `active_scan` as a name (the number is what matters).
- Transponder interrogation emits nothing (D5).
- Biome 1's axis weights ("moderate on every axis").
- That `dry_clear` is a biome entry rather than a fixture override.
- The reading of "six sensors" in 1.1.
- Reserved numbers 64+ for every named future entry: the *names* come from the board; the
  numbers are this document's.

Nothing in section 4 is a guess; every claim there was run.

---

## 7. What this spike leaves to others

- **BLD-61**: the exact shape of `Odometry`, `Transponder`, `SelfReport`; the `SmallVec`
  capacity; `World.wrecks`; tick rate. This document only names the variants so the ID table
  can point at them. (TRN's home is no longer open: it is a `BeliefUpdater` stage — see the
  note under table 1.2 and PHASE-3-OPEN-QUESTIONS.md §13.)
- **BLD-62**: answered. The reference policies are tree *data* over these registries, run by
  the interpreter in `blindside-vm` behind `VmHost` (AGENT-DRIVER D1), which is why D13
  assigns the six predicates rather than reserving them.
  Reconciled 2026-09-07: this line said the question was open and "D13 assumes Rust"; D13 was
  flipped to assign as a consequence of the driver decision. See
  PHASE-3-OPEN-QUESTIONS.md §8 and §20.
- **BLD-65**: which phase Scout, Hauler and Swimmer enter. Their numbers are held.
- **BLD-20**: the designer's answers on hasher, serialisation and lint scope; D18, D20 and
  D21 are the recommendations for the three of its questions that touch content.
- **DETERMINISM.md and ARCHITECTURE.md edits** (constrained set, tenth crate, eighth
  registry, `ChassisId`): the designer's, after sign-off; not made here.
- **`docs/CONTENT-IDS.md`**: BLD-63's done-when names it as the home of the signed-off
  table. This file is the proposal; the signed-off table should be copied there, or this
  file moved, once the boxes are ticked — the designer's call which.
