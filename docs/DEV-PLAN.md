# Blindside — development plan

This file is the board. Edit it directly. It was generated once from `docs/dev-plan.json`; that file is disposable.

**197 stories · 478.25 working days · ~47.8 months at ten working days a month**, plus the 19-story P1X epic the failed gate opened (12 more days). Solo, nights and weekends. `DESIGN.html` calls 18–24 months to Phase 8 a floor; treat any total under that as optimism.


> ## Where this actually stands, 2026-09-07
>
> **The Phase 1 gate failed.** A non-engineer watched the eight minutes and was bored
> (`docs/phase1-playtests/2026-09-06-gate.md`). That is R1, the risk the whole design rests on,
> and per `CLAUDE.md` Phase 2 does not start until it is met — so everything in the Phase 2 epic
> below is written but not startable, including the Phase 2 build that already exists.
>
> **What the failure produced, all of it new work not in the 197 stories:** a diagnosis measured
> from a tick-by-tick replay (the display's most dramatic moment — a machine standing 0.04 cells
> outside a lethal radius — was invisible; the last 79 s of the match are frozen; no map fix for
> the final 236 s; 34 of 50 events are two strings on a 16-second metronome; the rival is never
> drawn); a redesigned spectator display (`docs/SPECTATOR-DISPLAY.md`); an amendment to
> `PHASE-1-SPECTATOR-TEST.md` so the spectator view may draw truth while the operator view may
> not; slice one of that display built and running in 3D; and a decision on what the machinery is
> (`docs/THE-MACHINERY.md`, the Assayer).
>
> **The epic below that matters is P1X.** The 197 stories are still right about Phases 2–9; they
> are simply not what is being worked on, because a failed gate outranks a plan.

## Order of work

1. **BLD-1** — Phase 1 close-out: run the spectator gate and record what it proved *(Phase Phase 1 — Spectator Test, 8.75 d)* — starts when: Now. Phase 1 has no predecessor gate and the build exists (HEAD 7fcbe87, working tree clean). The Phase 0 harness epic may proceed in parallel because Phase 0 has no gate dependency on Phase 1 (BLD-20 puts that reading to the designer as a yes/no); the Phase 2 junction test must not start until BLD-16's report exists and does not record a fail, which BLD-42's depends_on encodes.
2. **BLD-18** — Phase 0 — Harness: headless runner, desync canary, replay, bisect, determinism lint, three-OS CI *(Phase Phase 0 — Harness, 17.5 d)* — starts when: Immediately. No document places a predecessor gate before Phase 0: CLAUDE.md's 'do immediately before 3' and PHASE-0's 'build immediately before Phase 3, not first' are read as priority statements (do not let the harness rot), not blockers — this is an interpretation that contradicts the literal spec text, so BLD-20 puts it to the designer as a yes/no on day one and records the dated answer in docs/HARNESS.md, and BLD-40 and BLD-66 assert that nothing crept into blindside-sim during the parallel window. It runs in parallel with the Phase 1 gate playtest and with Phase 2 (throwaway Python). Constraint that keeps the build order honest: blindside-sim gains no sensors, belief fusion, generation or any game logic until the Phase 2 gate report exists; Phase 3 remains blocked on gates 1, 2 and 0 and BLD-66 encodes that in depends_on. Stories BLD-19 and BLD-20 have no dependencies and start on day one; BLD-21 follows BLD-19.
3. **BLD-41** — Junction Test: demonstration → legible policy (throwaway Python) *(Phase Phase 2 — Junction Test, 20.5 d)* — starts when: The Phase 1 gate playtest has been run with a non-designer and its report classifies the player as engaged (talks to the screen, wrong theory corrected, tension at Recall) rather than bored — i.e. the Phase 1 group's final playtest-report story is done. Runs in parallel with the P0 harness epic; nothing here depends on P0 and nothing in P0 depends on this. Phase 3 stays blocked until this epic's gate report exists.
4. **BLD-60** — Phase 3 — Sim core in Rust *(Phase Phase 3 — Sim core, 116.25 d)* — starts when: BLD-66 is the gate-entry anchor and encodes CLAUDE.md's 'blocked on 1, 2, 0' in depends_on: the Phase 1 decision record (BLD-17, carrying the BLD-16 playtest report — the designer's read of the observations, never 'gate met'), the Phase 2 gate report (BLD-59) with all four criteria recorded, and the Phase 0 readiness report (BLD-40) with all five PHASE-0-HARNESS acceptance criteria green in CI. Every Phase 3 story that touches blindside-sim/gen/content/harness depends on BLD-66. Judgment call, flagged to the designer: spikes BLD-61 to BLD-64 and BLD-65 are question rounds and a scratch prototype outside the workspace, so they may run while Phase 2 is in progress; no game logic is committed to blindside-sim before BLD-66 confirms the reports and re-runs the empty-sim assertion.
5. **BLD-113** — VM, behavior trees, and the node editor *(Phase Phase 4 — VM and node editor, 67.75 d)* — starts when: BLD-114 is the gate-entry anchor: it links the BLD-110 readiness report with the designer's dated 'proceed' (1,000 headless matches under 10 minutes, bit-identical final hashes on Linux/macOS/Windows in CI, which itself required the Phase 0, 1 and 2 gates) and quotes the BLD-62 decision about what drove agents for that gate, because BLD-117 turns that seam into the real VM. Every Phase 4 story except BLD-115 depends on BLD-114. BLD-115 (Godot toolchain bootstrap) depends only on the three-OS CI (BLD-37); it may be pulled into late Phase 3 solely with the designer's explicit sign-off, recorded in BLD-114.
6. **BLD-141** — Client and replay — Godot 4 via GDExtension *(Phase Phase 5 — Client and replay, 75.5 d)* — starts when: The Phase 4 gate result has been produced and confirmed by the designer (a policy authored entirely in nodes beats a hand-written one on the benchmark set; graph diff works on two versions of the same tree), which implies the Phase 3 gate and the Phase 1 playtest record with its two-viewing rubric already exist; BLD-143 depends on BLD-139 to encode that. The walkers-vs-pods decision (BLD-142) should be raised during Phases 3-4 so it does not stall this phase.
7. **BLD-160** — Networked match *(Phase Phase 6 — Networked match, 60 d)* — starts when: The Phase 5 gate report (BLD-159) exists and the designer has read it as better than the Python record; BLD-164 depends on BLD-159 to encode that, and on BLD-104 (Extraction mode) which the server hosts. BLD-161, BLD-162 and BLD-163 are decisions and can be done during Phase 5.
8. **BLD-178** — Onboarding and fiction *(Phase Phase 7 — Onboarding and fiction, 34 d)* — starts when: The Phase 6 gate spike (BLD-177) has been answered — R8 measured and the designer has accepted the number; every Phase 7 build story depends on BLD-177 to encode that. BLD-179 and BLD-180 are decisions and can happen during Phase 6.
9. **BLD-187** — Ship something *(Phase Phase 8 — Ship something, 33 d)* — starts when: The Phase 7 gate report (BLD-186) exists and the designer accepts the result, and BLD-179 has named the product; BLD-188 depends on both.
10. **BLD-195** — Market and seasons *(Phase Phase 9 — Market and seasons, 45 d)* — starts when: Phase 8 has shipped and the first-month report (BLD-194) recommends proceeding; BLD-197 and BLD-198 depend on BLD-194 to encode that, and there is an active playerbase to be the denominator. BLD-196 can be decided during Phase 8.

## Board

Tick a story when it is done and move its `Status:` line. `Ready` means every dependency is done or there were none; the first epics in the order of work can start today.

### Ready now (10)

- [ ] **P1X-10** The readout row: the two numbers under near-identical labels *(P1X, P0, 0.5d)*
- [ ] **P1X-11** The palette pass: one meaning per colour, four type sizes, a 9pt floor *(P1X, P0, 1d)*
- [ ] **P1X-12** The cold open: the rules in twenty-two words before the clock starts *(P1X, P0, 0.5d)*
- [ ] **P1X-14** The last 79 s are frozen: the policy will not abandon a waypoint *(P1X, P0, 0.75d)*
- [ ] **P1X-15** No map fix for the final 236 s *(P1X, P0, 0.5d)*
- [ ] **P1X-16** The event feed is a metronome *(P1X, P0, 0.5d)*

> **Phase 1's gate failed on 2026-09-06** (`docs/phase1-playtests/2026-09-06-gate.md`). Per CLAUDE.md Phase 2 does not start, whatever its stories say below; the Phase 2 build that exists was made on the wrong reading and is not advanced by it. The next move is BLD-16b: re-run the gate on the live window with Recall in the player's hand, which is the cheapest experiment that separates "the display is illegible" from "the run phase is boring".

- [ ] **BLD-8** Spike: sweep Recall timings for both player sensors; find why lidar never reaches SEARCH *(BLD-1, P0, 0.75d)*
- [ ] **BLD-4** Pin the Phase 1 Python environment in requirements.txt *(BLD-1, P1, 0.25d)*
- [ ] **BLD-5** Write the spectator-test protocol and scoring rubric for Phase 1 and Phase 5 *(BLD-1, P0, 0.5d)*
- [ ] **BLD-6** Update GLOSSARY Passive/active for sonar and lidar as loadout modules *(BLD-1, P1, 0.25d)*
- [ ] **BLD-7** Record Phase 1's velocity data point and state the plan's estimate unit and total *(BLD-1, P1, 0.25d)*
- [ ] **BLD-20** Spike: put the harness's load-bearing unknowns to the designer in one written round *(BLD-18, P0, 0.5d)*

### Blocked on a dependency (175)

- [ ] **BLD-9** Apply the two-viewings gate decision: sonar is the gate configuration; retune so the Recall arc can succeed in it *(BLD-1, P0, 1.5d)* — after BLD-8
- [ ] **BLD-10** Reconcile tuning.py commentary with its values; write the measured beat sheet *(BLD-1, P1, 0.5d)* — after BLD-9
- [ ] **BLD-11** Spike: measure the contact mix the player actually hears; decide if ambiguity exists *(BLD-1, P1, 0.5d)* — after BLD-9
- [ ] **BLD-12** Answer or retire every PHASE-1-OPEN-QUESTIONS item against what was built *(BLD-1, P1, 0.5d)* — after BLD-9, BLD-11
- [ ] **BLD-13** Tick the six PHASE-1 acceptance boxes with seed, args and commit as evidence *(BLD-1, P0, 0.5d)* — after BLD-2, BLD-9, BLD-10, BLD-11
- [ ] **BLD-17** Write the Phase 1 decision record: what was proved, measured, and handed to Phase 3 *(BLD-1, P0, 1d)* — after BLD-16, BLD-12
- [ ] **BLD-21** Spike: choose the determinism-lint mechanism and prove it catches the known evasions *(BLD-18, P0, 0.5d)* — after BLD-19
- [ ] **BLD-25** Provide DeterministicRng-based test helpers and settle the dev-dependency lint policy *(BLD-18, P1, 0.5d)* — after BLD-24, BLD-21, BLD-22
- [ ] **BLD-29** Guard against Cargo feature unification exposing diagnostics or inject-desync outside the harness *(BLD-18, P0, 0.5d)* — after BLD-28, BLD-22
- [ ] **BLD-32** Scaffold the compile-fail test that nothing outside blindside-sim can reach World *(BLD-18, P1, 0.5d)* — after BLD-23, BLD-28
- [ ] **BLD-34** Add the unsafe policy and PR template for the non-lintable determinism rules *(BLD-18, P1, 0.5d)* — after BLD-19, BLD-22
- [ ] **BLD-39** Write docs/HARNESS.md and reconcile ARCHITECTURE's MatchRecord and ROADMAP's crate names *(BLD-18, P1, 0.5d)* — after BLD-20, BLD-21, BLD-36, BLD-37
- [ ] **BLD-40** Verify all five Phase 0 acceptance criteria on one commit and report ready for the gate *(BLD-18, P0, 0.5d)* — after BLD-34, BLD-35, BLD-36, BLD-37, BLD-38, BLD-32, BLD-39, BLD-29, BLD-25
- [ ] **BLD-42** Settle the load-bearing Phase 2 unknowns with the designer before writing code *(BLD-41, P0, 1d)* — after BLD-16
- [ ] **BLD-43** Build the seeded 8-junction branching corridor with a deposit at a random leaf *(BLD-41, P0, 1.5d)* — after BLD-42
- [ ] **BLD-44** Implement the corridor Belief: drifting pose, believed junction graph, cargo self-report *(BLD-41, P0, 1.5d)* — after BLD-42, BLD-43
- [ ] **BLD-45** Implement the three predicates over Belief with θ as a fitted parameter *(BLD-41, P0, 0.5d)* — after BLD-44
- [ ] **BLD-46** Implement take_branch and return_to_beacon as motor programs shared by demo and policy *(BLD-41, P0, 1d)* — after BLD-44
- [ ] **BLD-47** Build the unseen-seed batch evaluator and establish the success ceiling *(BLD-41, P0, 1d)* — after BLD-43, BLD-46
- [ ] **BLD-48** Build demonstration mode: player drives on a belief-only view and traces are recorded *(BLD-41, P0, 2d)* — after BLD-43, BLD-44, BLD-45, BLD-46
- [ ] **BLD-49** Segment demonstration traces at behavior changepoints *(BLD-41, P0, 1.5d)* — after BLD-48
- [ ] **BLD-50** Induce the minimal-separator rule over the 3 predicates and fit θ; report no-separator *(BLD-41, P0, 2d)* — after BLD-45, BLD-49
- [ ] **BLD-51** Render the inferred policy as a behavior tree and as one plain sentence *(BLD-41, P0, 1d)* — after BLD-50
- [ ] **BLD-52** Write the Phase 2 playtest protocol and scoring sheet before the session *(BLD-41, P0, 0.5d)* — after BLD-51
- [ ] **BLD-53** Run the inferred policy as a ghost beside the demonstration and mark the divergence *(BLD-41, P0, 1d)* — after BLD-48, BLD-50, BLD-51
- [ ] **BLD-54** Build the correction loop: scrub, enter body, drive correction, promote, re-induce *(BLD-41, P0, 1.5d)* — after BLD-53
- [ ] **BLD-55** Ask the player an active-learning query when no consistent separator exists *(BLD-41, P1, 1d)* — after BLD-50, BLD-51, BLD-48
- [ ] **BLD-56** Measure 3 demos → success rate on unseen seeds and record the number *(BLD-41, P0, 1d)* — after BLD-47, BLD-50, BLD-55
- [ ] **BLD-57** Record candidate predicates observed during demos without adding them *(BLD-41, P3, 0.5d)* — after BLD-56
- [ ] **BLD-58** Self-test the full loop end to end and fix blockers before the external playtest *(BLD-41, P0, 1d)* — after BLD-54, BLD-56, BLD-52
- [ ] **BLD-59** Run the Phase 2 gate playtest with a non-designer and write the readiness report *(BLD-41, P0, 1d)* — after BLD-58
- [ ] **BLD-61** Reconcile ARCHITECTURE core types with Phase 1 findings before writing sim code *(BLD-60, P0, 3d)* — after BLD-16
- [ ] **BLD-62** Decide what drives agents in Phase 3 before the Phase 4 VM exists *(BLD-60, P0, 1d)* — after BLD-61
- [ ] **BLD-63** Fix the Phase 3 sensor set, module list, content format and permanent content IDs *(BLD-60, P0, 2d)* — after BLD-61
- [ ] **BLD-64** Prototype range-bounded acoustic propagation and measure it at target cave size *(BLD-60, P0, 3d)* — after BLD-61
- [ ] **BLD-65** Decide when Scout, Hauler and Swimmer ship and reserve their chassis IDs *(BLD-60, P1, 0.5d)* — after BLD-63
- [ ] **BLD-66** Phase 3 gate-entry: confirm gates 1, 2 and 0 and that blindside-sim is still empty before the first sim commit *(BLD-60, P0, 0.25d)* — after BLD-17, BLD-59, BLD-40, BLD-61
- [ ] **BLD-67** Build the single fixed-point math module with cross-platform golden tests *(BLD-60, P0, 3d)* — after BLD-24, BLD-37, BLD-61, BLD-66
- [ ] **BLD-68** Build blindside-content registries with stable IDs, retired ledger, season flag and content hash *(BLD-60, P0, 3d)* — after BLD-63, BLD-66
- [ ] **BLD-69** Assign runtime entity IDs from record data and step-order-independent sequences, never from SlotMap slots *(BLD-60, P0, 1.5d)* — after BLD-61, BLD-27, BLD-66
- [ ] **BLD-70** Fill World with its documented fields and extend the state hash with mutation tests *(BLD-60, P0, 3d)* — after BLD-61, BLD-69, BLD-66
- [ ] **BLD-71** Define the cave cell model and the eight world axes as biome parameters in blindside-gen *(BLD-60, P0, 3d)* — after BLD-63, BLD-68, BLD-66
- [ ] **BLD-72** Generate connected caves by seeded cellular automata with perimeter entry shafts *(BLD-60, P0, 4d)* — after BLD-67, BLD-71, BLD-66
- [ ] **BLD-73** Place deposits with rough value parity per region but not accessibility parity *(BLD-60, P1, 2d)* — after BLD-72, BLD-66
- [ ] **BLD-74** Build the sensor module as the sole World/Belief crossing with a request-shaped SensorEnvironment *(BLD-60, P0, 3d)* — after BLD-61, BLD-63, BLD-67, BLD-70, BLD-66
- [ ] **BLD-75** Add compile-fail tests proving Policy::evaluate and Predicate::eval cannot reach World *(BLD-60, P0, 2d)* — after BLD-62, BLD-70, BLD-66
- [ ] **BLD-76** Design the sanctioned truth export for replay and spectator views as harness-only diagnostics *(BLD-60, P1, 2d)* — after BLD-70, BLD-75, BLD-66
- [ ] **BLD-77** Define Belief with a covariance pose model, fix history and a relaxable timestamped map *(BLD-60, P0, 3d)* — after BLD-61, BLD-67, BLD-70, BLD-66
- [ ] **BLD-78** Implement MotorCmd, the actuator trait and deterministic locomotion over the heightfield *(BLD-60, P0, 3d)* — after BLD-67, BLD-74, BLD-72, BLD-66
- [ ] **BLD-79** Build the AcousticField with range-bounded passage propagation, absorption and arrival bearings *(BLD-60, P0, 4d)* — after BLD-64, BLD-67, BLD-70, BLD-71, BLD-66
- [ ] **BLD-80** Add multi-path echoes and thermal shadow zones to the AcousticField *(BLD-60, P1, 2d)* — after BLD-79, BLD-66
- [ ] **BLD-81** Keep acoustic caches out of the state hash and prove the worst tick fits the budget *(BLD-60, P0, 2d)* — after BLD-70, BLD-79, BLD-66
- [ ] **BLD-82** Implement the odometry sensor so drift is born in the sensor layer, bias-dominated *(BLD-60, P0, 2d)* — after BLD-74, BLD-78, BLD-66
- [ ] **BLD-83** Implement passive acoustic returns with quality and character, plus the near-field sense *(BLD-60, P0, 2d)* — after BLD-74, BLD-79, BLD-66
- [ ] **BLD-84** Implement active sonar as a loudly emitting loadout module *(BLD-60, P0, 2d)* — after BLD-74, BLD-79, BLD-66
- [ ] **BLD-85** Implement lidar as the silent short-range alternative module, blind past the waterline *(BLD-60, P0, 2d)* — after BLD-71, BLD-84, BLD-66
- [ ] **BLD-86** Implement beacons in World, transponder fixes and spoofing as a real mechanism *(BLD-60, P0, 3d)* — after BLD-70, BLD-74, BLD-66
- [ ] **BLD-87** Implement the BeliefUpdater with back-propagating fixes and position-only beacon correction *(BLD-60, P0, 4d)* — after BLD-82, BLD-86, BLD-77, BLD-66
- [ ] **BLD-88** Record own beacons at the estimated drop pose and keep only survey-placed beacons as truth anchors *(BLD-60, P0, 1d)* — after BLD-87, BLD-66
- [ ] **BLD-89** Implement contact tracks and fixed-point bearing-only localisation over movement *(BLD-60, P0, 2.5d)* — after BLD-83, BLD-77, BLD-66
- [ ] **BLD-90** Implement terrain-relative navigation producing fixes that recover heading in surveyed ground *(BLD-60, P0, 4d)* — after BLD-83, BLD-77, BLD-87, BLD-61, BLD-66
- [ ] **BLD-91** Implement the magnetic anomaly sensor with false finds from magnetic character *(BLD-60, P1, 1.5d)* — after BLD-74, BLD-73, BLD-66
- [ ] **BLD-92** Implement deposits, cargo loading and inventory through self-report returns *(BLD-60, P0, 2d)* — after BLD-74, BLD-73, BLD-77, BLD-66
- [ ] **BLD-93** Implement wrecks per the container decision, holding cargo and policy for the rest of the match *(BLD-60, P1, 1d)* — after BLD-70, BLD-92, BLD-66
- [ ] **BLD-94** Implement collapse events from structural integrity and the structural monitor sensor *(BLD-60, P1, 2d)* — after BLD-72, BLD-79, BLD-93, BLD-66
- [ ] **BLD-95** Implement the optical sensor with a tiny sediment-limited radius and light as a line-of-sight tell *(BLD-60, P1, 2d)* — after BLD-85, BLD-89, BLD-66
- [ ] **BLD-96** Stir a transient silt cloud behind agents moving through silty passages *(BLD-60, P2, 1.5d)* — after BLD-71, BLD-78, BLD-85, BLD-95, BLD-66
- [ ] **BLD-97** Implement the Predicate trait in a World-blind module with the Phase 2 vocabulary and Deprecated *(BLD-60, P0, 2d)* — after BLD-68, BLD-75, BLD-77, BLD-66
- [ ] **BLD-98** Define the Surveyor chassis and Phase 3 modules as content data with loadout validation *(BLD-60, P0, 2d)* — after BLD-63, BLD-68, BLD-66
- [ ] **BLD-99** Implement the Action trait and the Phase 3 action set as actuator requests from Belief *(BLD-60, P0, 2d)* — after BLD-78, BLD-86, BLD-92, BLD-97, BLD-66
- [ ] **BLD-100** Model gait as an action parameter that sets speed and motion-noise signature *(BLD-60, P2, 1.5d)* — after BLD-78, BLD-83, BLD-99, BLD-98, BLD-66
- [ ] **BLD-101** Add a belief-map clearance query and map-aware steering with the Phase 1 give-up timing *(BLD-60, P0, 2.5d)* — after BLD-77, BLD-87, BLD-99, BLD-66
- [ ] **BLD-102** Ship the Phase 3 policy driver with cautious and aggressive reference policies and a VM stub *(BLD-60, P0, 2d)* — after BLD-62, BLD-97, BLD-99, BLD-66
- [ ] **BLD-103** Implement the AncientSystem trait, WorldView and one fixed-cycle instance that kills into a wreck *(BLD-60, P0, 3d)* — after BLD-68, BLD-79, BLD-93, BLD-66
- [ ] **BLD-104** Implement the MatchMode trait and Extraction mode with commit, run, extraction window and scoring *(BLD-60, P0, 2d)* — after BLD-68, BLD-70, BLD-92, BLD-66
- [ ] **BLD-105** Implement the command channel with Recall as a terminal abort-to-shaft with depth latency *(BLD-60, P0, 2d)* — after BLD-80, BLD-86, BLD-99, BLD-104, BLD-66
- [ ] **BLD-106** Implement the spoof module and a Belief-only clone/relocate-beacon action with an observable arming rule *(BLD-60, P0, 3d)* — after BLD-86, BLD-99, BLD-102, BLD-98, BLD-76, BLD-66
- [ ] **BLD-107** Fix and document the per-tick step order and enforce stable-ID iteration through it *(BLD-60, P0, 2d)* — after BLD-87, BLD-102, BLD-103, BLD-104, BLD-66
- [ ] **BLD-108** Build the benchmark seed set and reference match scenario for batch runs *(BLD-60, P1, 2d)* — after BLD-76, BLD-105, BLD-107, BLD-106, BLD-101, BLD-66
- [ ] **BLD-109** Profile the sim and reach 1,000 headless matches in under 10 minutes on a laptop *(BLD-60, P0, 3d)* — after BLD-81, BLD-108, BLD-66
- [ ] **BLD-110** Prove 1,000-match bit-identity across Linux, macOS and Windows in CI and report gate readiness *(BLD-60, P0, 2d)* — after BLD-37, BLD-38, BLD-109, BLD-66
- [ ] **BLD-111** Audit hardware-readiness of the Sensor and Actuator seams *(BLD-60, P1, 1d)* — after BLD-78, BLD-90, BLD-95, BLD-94, BLD-66
- [ ] **BLD-112** Fold Phase 1 findings and Phase 3 decisions back into the docs and list every guess *(BLD-60, P1, 1.5d)* — after BLD-110, BLD-66
- [ ] **BLD-114** Phase 4 gate-entry: confirm the Phase 3 gate result and the policy-driver decision before VM code *(BLD-113, P0, 0.25d)* — after BLD-110, BLD-112
- [ ] **BLD-115** Bootstrap Godot 4 + gdext: blindside-client builds a GDExtension on Windows and in CI *(BLD-113, P0, 3d)* — after BLD-37
- [ ] **BLD-116** Specify the VM ISA, register file, and per-tick evaluation model *(BLD-113, P0, 2d)* — after BLD-114
- [ ] **BLD-117** Decide where Policy lives and what compiled artifact the sim executes *(BLD-113, P0, 1d)* — after BLD-116, BLD-114
- [ ] **BLD-118** Record the designer's decision on rung three text authoring *(BLD-113, P3, 0.5d)* — after BLD-117, BLD-114
- [ ] **BLD-119** Implement the blindside-vm interpreter: opcodes, fixed Fx register file, golden tests *(BLD-113, P0, 4d)* — after BLD-116, BLD-114
- [ ] **BLD-120** Enforce VmBudget per tick, sourced from content data, and prove the sandbox *(BLD-113, P0, 2d)* — after BLD-119, BLD-114
- [ ] **BLD-121** blindside-behavior: BtNode, Policy, NodeId, PolicyRef, AuthorRef with schema and validation *(BLD-113, P0, 3d)* — after BLD-117, BLD-114
- [ ] **BLD-122** Define the benchmark set and add harness bench *(BLD-113, P0, 2d)* — after BLD-117, BLD-108, BLD-114
- [ ] **BLD-123** VM host interface: predicate and action call-outs over Belief only, compile-fail test *(BLD-113, P0, 3d)* — after BLD-117, BLD-119, BLD-114
- [ ] **BLD-124** Bring VM state under the state hash; injected VM non-determinism caught by the canary *(BLD-113, P0, 1.5d)* — after BLD-123, BLD-33, BLD-114
- [ ] **BLD-125** Compile behavior trees directly to bytecode with no text intermediate *(BLD-113, P0, 4d)* — after BLD-119, BLD-123, BLD-121, BLD-114
- [ ] **BLD-126** Policy schema migration chain with historical fixtures; Deprecated predicates load and run *(BLD-113, P1, 2d)* — after BLD-121, BLD-114
- [ ] **BLD-127** Graph diff of two versions of the same tree (gate criterion 2) *(BLD-113, P0, 3d)* — after BLD-121, BLD-114
- [ ] **BLD-128** Execution trace capture: nodes fired, order, predicate values vs thresholds *(BLD-113, P1, 3d)* — after BLD-123, BLD-125, BLD-114
- [ ] **BLD-129** Demonstration trace recorder: Belief-derived predicate values and actions per tick *(BLD-113, P1, 2d)* — after BLD-123, BLD-114
- [ ] **BLD-130** Score the hand-written reference policy on the benchmark and commit the baseline *(BLD-113, P0, 1.5d)* — after BLD-122, BLD-123, BLD-114
- [ ] **BLD-131** Editor FFI surface: vocabulary, policy load/save/validate/compile, diff, trace, bench *(BLD-113, P0, 3d)* — after BLD-115, BLD-121, BLD-125, BLD-127, BLD-128, BLD-114
- [ ] **BLD-132** Node editor: build trees from the vocabulary in Godot *(BLD-113, P0, 5d)* — after BLD-131, BLD-114
- [ ] **BLD-133** Collapse, expand, and subtree extraction into a Subtree policy *(BLD-113, P1, 3d)* — after BLD-132, BLD-114
- [ ] **BLD-134** Flag Deprecated predicates and render graph diffs in the editor *(BLD-113, P1, 2d)* — after BLD-132, BLD-126, BLD-127, BLD-114
- [ ] **BLD-135** Live trace readout in the editor: run on a benchmark seed, scrub, light the fired branch *(BLD-113, P1, 3d)* — after BLD-132, BLD-128, BLD-122, BLD-114
- [ ] **BLD-136** Design the induction port from Phase 2 findings; settle how demonstrations exist in Phase 4 *(BLD-113, P1, 2d)* — after BLD-121, BLD-114
- [ ] **BLD-137** blindside-induct: traces to Policy via segmentation, separator induction, threshold fitting *(BLD-113, P1, 5d)* — after BLD-136, BLD-129, BLD-114
- [ ] **BLD-138** Plain-sentence rendering of a tree and the active-learning query surface *(BLD-113, P2, 2d)* — after BLD-121, BLD-137, BLD-114
- [ ] **BLD-139** Author the node challenger in the editor and run the Phase 4 gate benchmark *(BLD-113, P0, 4d)* — after BLD-130, BLD-132, BLD-133, BLD-134, BLD-135, BLD-127, BLD-124, BLD-114
- [ ] **BLD-140** Record Phase 4 decisions and reconcile ARCHITECTURE with the code *(BLD-113, P1, 1d)* — after BLD-139, BLD-137, BLD-114
- [ ] **BLD-142** Record the walkers-vs-pods decision before chassis art starts *(BLD-141, P1, 0.5d)* — after BLD-100
- [ ] **BLD-143** Re-pin Godot 4 and gdext; audit what churned since the Phase 4 bootstrap *(BLD-141, P0, 2d)* — after BLD-115, BLD-139
- [ ] **BLD-144** Define the FFI surface as named Belief-derived snapshot types plus command submission *(BLD-141, P0, 4d)* — after BLD-143, BLD-74, BLD-75
- [ ] **BLD-145** Consume the sanctioned ReplayFrame export in the replay host only; keep the run-phase scene unable to import it *(BLD-141, P0, 2d)* — after BLD-144, BLD-76
- [ ] **BLD-146** Load, verify and scrub a MatchRecord in the client replay host *(BLD-141, P0, 4d)* — after BLD-145, BLD-31, BLD-30
- [ ] **BLD-147** Reproduce the Phase 1 beat sheet on the real sim as a MatchRecord fixture *(BLD-141, P0, 4d)* — after BLD-146, BLD-139, BLD-108, BLD-106
- [ ] **BLD-148** Render the one generated cave biome as a 3D truth layer for the replay *(BLD-141, P1, 6d)* — after BLD-145
- [ ] **BLD-149** Model and animate the Surveyor chassis with an honest silhouette and a sensor head *(BLD-141, P1, 8d)* — after BLD-142
- [ ] **BLD-150** Build the operator view point cloud in the estimated frame with smear, snap and overlays *(BLD-141, P0, 8d)* — after BLD-144
- [ ] **BLD-151** Drive directional audio from Belief with identical sound for honest and lying fixes *(BLD-141, P1, 3d)* — after BLD-144
- [ ] **BLD-152** Build the operator panels: live decision graph, timeline strip, belief-fact HUD *(BLD-141, P0, 5d)* — after BLD-150, BLD-128
- [ ] **BLD-153** Design failure-attribution heuristics against a harness-generated wreck corpus *(BLD-141, P1, 2d)* — after BLD-146
- [ ] **BLD-154** Build the replay screen with truth and belief drawn together on one scrubbable timeline *(BLD-141, P0, 10d)* — after BLD-146, BLD-148, BLD-149, BLD-150, BLD-152
- [ ] **BLD-155** Add enter-agent-perception mode from any replay tick *(BLD-141, P1, 4d)* — after BLD-154
- [ ] **BLD-156** Give each interference and hazard event a distinct replay signature *(BLD-141, P2, 3d)* — after BLD-154
- [ ] **BLD-157** Present the causal chain of each loss in the replay with evidence per link *(BLD-141, P1, 6d)* — after BLD-153, BLD-154
- [ ] **BLD-158** Hold the frame budget with a full-match point cloud; warm up shaders before play *(BLD-141, P2, 2d)* — after BLD-150, BLD-154
- [ ] **BLD-159** Re-run the Phase 1 spectator test in the real client and score it against the Python record *(BLD-141, P0, 2d)* — after BLD-150, BLD-152, BLD-151, BLD-154, BLD-155, BLD-147, BLD-158, BLD-14, BLD-5, BLD-16
- [ ] **BLD-161** Record the Phase 6 design decisions with the designer *(BLD-160, P0, 1d)* — after BLD-139
- [ ] **BLD-162** Choose transport, serialisation and snapshot cadence for blindside-net *(BLD-160, P0, 2d)* — after BLD-139
- [ ] **BLD-163** Decide which interference methods ship, in what order, and their replay signatures *(BLD-160, P1, 1d)* — after BLD-161
- [ ] **BLD-164** Create blindside-net with a belief-only wire protocol *(BLD-160, P0, 4d)* — after BLD-162, BLD-159, BLD-104
- [ ] **BLD-165** Run the sim server-authoritatively and build the MatchRecord live *(BLD-160, P0, 6d)* — after BLD-164, BLD-31, BLD-105
- [ ] **BLD-166** Connect the Godot client to a remote match *(BLD-160, P0, 5d)* — after BLD-164, BLD-165
- [ ] **BLD-167** Build the lobby and simultaneous prep phase *(BLD-160, P0, 5d)* — after BLD-161, BLD-165, BLD-166
- [ ] **BLD-168** Run N-team extraction matches on one shared seed *(BLD-160, P0, 4d)* — after BLD-167
- [ ] **BLD-169** Play the descent and blackout sequence *(BLD-160, P1, 3d)* — after BLD-165, BLD-166
- [ ] **BLD-170** Complete the command channel: Hold, Go quiet, Abort, per-match budget, shadow blocking end to end, lobby toggle *(BLD-160, P0, 3d)* — after BLD-161, BLD-165, BLD-105
- [ ] **BLD-171** Add wrecks, salvage and behaviour recovery with provenance *(BLD-160, P0, 5d)* — after BLD-168, BLD-93
- [ ] **BLD-172** Publish seed and replay after every match *(BLD-160, P1, 3d)* — after BLD-165, BLD-168
- [ ] **BLD-173** Serve a live spectator stream per the recorded truth-or-belief decision *(BLD-160, P2, 4d)* — after BLD-161, BLD-165, BLD-172
- [ ] **BLD-174** Implement beacon theft and the decoy emitter with their counters *(BLD-160, P1, 3d)* — after BLD-163, BLD-86, BLD-90, BLD-89, BLD-156
- [ ] **BLD-175** Implement noise flooding, silt clouding and induced collapse *(BLD-160, P2, 4d)* — after BLD-163, BLD-79, BLD-94, BLD-96, BLD-156
- [ ] **BLD-176** Playtest networked matches and log observed griefing *(BLD-160, P1, 3d)* — after BLD-170, BLD-171, BLD-172
- [ ] **BLD-177** Measure server cost per match against a plausible price point *(BLD-160, P0, 4d)* — after BLD-168, BLD-170, BLD-171, BLD-172
- [ ] **BLD-179** Decide which product Phase 8 ships before building onboarding *(BLD-178, P0, 1d)* — after BLD-159
- [ ] **BLD-180** Design the two ancient systems on paper with the designer *(BLD-178, P0, 2d)* — after BLD-159
- [ ] **BLD-181** Implement the two ancient systems with signature, behaviour, exploit, counter *(BLD-178, P0, 8d)* — after BLD-180, BLD-103, BLD-33, BLD-177
- [ ] **BLD-182** Build the first-failure scenario: a beacon lie the player watches happen *(BLD-178, P0, 6d)* — after BLD-179, BLD-177, BLD-108
- [ ] **BLD-183** Build the first-session flow on rung one only, with no lecture *(BLD-178, P0, 5d)* — after BLD-179, BLD-182, BLD-177
- [ ] **BLD-184** Add the named persistent fleet, service history and wall of the lost *(BLD-178, P1, 5d)* — after BLD-177, BLD-157
- [ ] **BLD-185** Implement Endurance mode *(BLD-178, P1, 4d)* — after BLD-177, BLD-104, BLD-179
- [ ] **BLD-186** Run the new-player ten-minute observation test *(BLD-178, P0, 3d)* — after BLD-181, BLD-182, BLD-183, BLD-184, BLD-185
- [ ] **BLD-188** Write the cut list for the shipping build *(BLD-187, P0, 2d)* — after BLD-179, BLD-186
- [ ] **BLD-189** Build out the product-specific content the cut list requires *(BLD-187, P0, 10d)* — after BLD-188
- [ ] **BLD-190** Produce release builds from CI whose replays verify *(BLD-187, P0, 4d)* — after BLD-188, BLD-37
- [ ] **BLD-191** Set up the store page and the commercial prerequisites *(BLD-187, P0, 5d)* — after BLD-188
- [ ] **BLD-192** Open a feedback channel that carries replays *(BLD-187, P1, 3d)* — after BLD-190
- [ ] **BLD-193** Run the stability soak and set the min-spec floor *(BLD-187, P1, 4d)* — after BLD-189, BLD-190
- [ ] **BLD-194** Launch, then write the first-month response report *(BLD-187, P1, 5d)* — after BLD-189, BLD-190, BLD-191, BLD-192, BLD-193
- [ ] **BLD-196** Record the market rules before writing market code *(BLD-195, P0, 2d)* — after BLD-186
- [ ] **BLD-197** Build the listing service for Subtree policies with provenance *(BLD-195, P0, 6d)* — after BLD-196, BLD-194
- [ ] **BLD-198** Add the in-game currency ledger with no real-money path *(BLD-195, P0, 4d)* — after BLD-196, BLD-194
- [ ] **BLD-199** Auto-evaluate every listing on the benchmark set with replays attached *(BLD-195, P0, 6d)* — after BLD-197, BLD-38, BLD-122
- [ ] **BLD-200** Seed the market with first-party behaviours, labelled honestly *(BLD-195, P1, 2d)* — after BLD-197, BLD-199
- [ ] **BLD-201** Build the market client: browse, verify, buy, slot as a component *(BLD-195, P0, 6d)* — after BLD-197, BLD-199, BLD-198
- [ ] **BLD-202** Instrument publish-and-adopt for the 1% gate *(BLD-195, P0, 3d)* — after BLD-201
- [ ] **BLD-203** Ship season one as a world change and a shared event *(BLD-195, P0, 6d)* — after BLD-197, BLD-199
- [ ] **BLD-204** Implement Survey mode scoring map accuracy against ground truth inside the sim *(BLD-195, P2, 3d)* — after BLD-196, BLD-104, BLD-76, BLD-194
- [ ] **BLD-205** Implement Race mode: first to reach a single generated anomaly *(BLD-195, P2, 2d)* — after BLD-196, BLD-73, BLD-91, BLD-104, BLD-194
- [ ] **BLD-206** Add moderation tooling sized to the observed market *(BLD-195, P2, 3d)* — after BLD-201
- [ ] **BLD-207** Evaluate the R7 gate over the stated window *(BLD-195, P0, 2d)* — after BLD-200, BLD-202, BLD-203

### In progress

- [ ] **P1X-9** Build the Assayer: geometry, cycle, pointing hazard, graded damage *(P1X, P0, 2d)*
- [ ] **BLD-16** Run the Phase 1 gate playtest with a non-engineer and write the readiness report *(BLD-1, P0, 0.5d)*
- [ ] **BLD-19** Create the Cargo workspace, pin the toolchain, and lock blindside-sim's dependency tree *(BLD-18, P0, 0.5d)*
- [ ] **BLD-22** Land the CI determinism lint and prove a PR adding f64 to blindside-sim goes red *(BLD-18, P0, 1d)*
- [ ] **BLD-23** Build the empty blindside-sim: Sim::new(&MatchRecord), step, tick, state_hash; World pub(crate) *(BLD-18, P0, 0.5d)*
- [ ] **BLD-24** Add Fx, the fixed-point math module home, and stateless DeterministicRng with golden tests *(BLD-18, P0, 1d)*
- [ ] **BLD-26** Compute the content pack hash in blindside-content and refuse mismatching replays *(BLD-18, P0, 0.5d)*
- [ ] **BLD-27** Implement the per-tick state hash with an explicit coverage list and mutation tests *(BLD-18, P0, 1d)*
- [ ] **BLD-28** Expose a feature-gated, string-only structural diff of two Sims for the canary *(BLD-18, P0, 0.5d)*
- [ ] **BLD-30** Define MatchRecord serialisation, schema version, migration hook, and recorded final hash *(BLD-18, P0, 1d)*
- [ ] **BLD-31** Build the blindside-harness binary: run, record and verify subcommands, hash log, throughput *(BLD-18, P0, 1d)*
- [ ] **BLD-33** Build the desync canary: two Sims in lockstep, hash compared every tick, panic with diff *(BLD-18, P0, 1d)*
- [ ] **BLD-35** Inject a HashMap-iteration non-determinism and prove the canary catches it in the tick *(BLD-18, P0, 1d)*
- [ ] **BLD-36** Build one-command bisect: first divergent tick, both hashes, and the state diff *(BLD-18, P0, 1.5d)*
- [ ] **BLD-37** Run build, lint, canary, golden replay and cross-OS hash compare on Linux/macOS/Windows CI *(BLD-18, P0, 2d)*
- [ ] **BLD-38** Add the batch executor: N seeds in parallel across matches with a seed-to-hash table *(BLD-18, P1, 1d)*
- [ ] **BLD-14** Render gate videos for both sensors from one seed and record their provenance *(BLD-1, P1, 0.5d)*

### Done

- [x] **P1X-1** Record the failed gate with the tester's words and the diagnosis *(P1X, P0, 0.25d)*
- [x] **P1X-2** Measure the dead air tick by tick *(P1X, P0, 0.5d)*
- [x] **P1X-3** Redesign the spectator display *(P1X, P0, 1d)*
- [x] **P1X-4** Amend the spec so the spectator view may draw truth *(P1X, P0, 0.1d)*
- [x] **P1X-5** Prove 3D fits the frame budget *(P1X, P0, 0.5d)*
- [x] **P1X-6** Slice one: the truth channel and the 3D picture-in-picture view *(P1X, P0, 2.5d)*
- [x] **P1X-7** Close the invariant against every route a verifier found *(P1X, P0, 0.5d)*
- [x] **P1X-8** Decide what the machinery is, how it harms, and the damage model *(P1X, P0, 1d)*
- [x] **BLD-15** Designer self-test: twenty minutes on the gate build before the external session *(BLD-1, P0, 0.25d)*
- [x] **BLD-2** Fix SEARCH-mode crash: decision_report reads undefined T.RECALL_SEARCH_RADIUS_RATE *(BLD-1, P0, 0.25d)*
- [x] **BLD-3** Verify and commit the in-progress Phase 1 retune, one commit per concern *(BLD-1, P0, 0.75d)*

## P1X — Answer R1: make eight minutes worth watching

**Phase 1, re-opened by the gate.** Everything here exists because a stranger was bored, and the
only thing that closes it is a stranger who is not. It is not in the original 197 stories because
the plan assumed the gate passed. Nothing in Phases 2–9 starts until this does.

- **Gate — pass:** a non-engineer, watching the LIVE window with Recall in her hand and one
  sentence of instruction, talks to the screen, guesses at what is happening, forms a wrong theory
  and corrects it, and feels the Recall decision. Run twice: truth on, then truth off.
- **Gate — kill:** she is bored again with a live decision in front of her and a display that
  shows her the world. Then R1 is real, the run phase does not carry a match, and Phases 2–9 are
  built on a premise that does not hold. Stop and report.
- **Estimate:** 12 working days of build, plus the designer's decisions and two playtest sessions.

| Key | Type | Summary | Pri | Days | Depends on | Status |
|---|---|---|---|---|---|---|
| P1X-1 | Task | Record the failed gate with the tester's words and the diagnosis | P0 | 0.25 | — | Done (`01e156e`) |
| P1X-2 | Spike | Measure the dead air tick by tick and name every stretch nothing changes | P0 | 0.5 | P1X-1 | Done |
| P1X-3 | Design | Redesign the spectator display; four proposals, three judges, one plan | P0 | 1 | P1X-2 | Done (`70ba674`) |
| P1X-4 | Decision | Amend the spec so the spectator view may draw truth | P0 | 0.1 | P1X-3 | Done (`0175f69`) |
| P1X-5 | Spike | Prove 3D fits the frame budget; measure both panels and the minimap | P0 | 0.5 | P1X-3 | Done — 26.8 ms median, cheaper than the 2D it replaces |
| P1X-6 | Story | Slice one: the truth channel and the 3D picture-in-picture view | P0 | 2.5 | P1X-4, P1X-5 | Done (`e2cfd46`) |
| P1X-7 | Bug | Close the invariant against every route a verifier found | P0 | 0.5 | P1X-6 | Done — 12 of 12 routes caught |
| P1X-8 | Design | Decide what the machinery is, how it harms, and the damage model | P0 | 1 | — | Done (`97563a1`, the Assayer) |
| P1X-9 | Story | Build the Assayer: geometry, cycle, pointing hazard, graded damage | P0 | 2 | P1X-8 | In progress |
| P1X-10 | Story | The readout row: the two numbers under near-identical labels | P0 | 0.5 | P1X-6 | Backlog |
| P1X-11 | Story | The palette pass: one meaning per colour, four type sizes, a 9pt floor | P0 | 1 | P1X-6 | Backlog |
| P1X-12 | Story | The cold open: the rules in twenty-two words before the clock starts | P0 | 0.5 | P1X-6 | Backlog |
| P1X-13 | Story | The release beat: a near miss needs an exhale, not just an alarm | P1 | 0.5 | P1X-9 | Backlog |
| P1X-14 | Bug | The last 79 s are frozen: the policy resets its escape counter instead of abandoning the waypoint | P0 | 0.75 | — | Backlog |
| P1X-15 | Bug | No map fix for the final 236 s, so the cloud never snaps in the second half | P0 | 0.5 | — | Backlog |
| P1X-16 | Bug | The event feed is a metronome: 34 of 50 events are two strings every 16 s | P0 | 0.5 | — | Backlog |
| P1X-17 | Decision | Should the player have a reason to go to the machinery? Today only the rival does, so only the rival is ever at risk | P0 | 0.25 | P1X-8 | **Designer** |
| P1X-18 | Task | Designer self-test on the live window before the next session | P0 | 0.25 | P1X-9..P1X-16 | Backlog |
| P1X-19 | Task | Re-run the gate live, truth on then truth off, and write the report | P0 | 0.5 | P1X-18 | Backlog |

### P1X-17 — Should the player have a reason to go to the machinery?

**Measured 2026-09-07, after a first attempt got it wrong** (the sweep set `T.SEED` after import,
but `Sim.__init__` binds that default at import time, so it re-ran one world eight times). With
the seed actually passed: across seeds 1–8 there are five deaths and **one is the player** —
seed 3 at 6:56, ending that match `destroyed`. Time spent inside the 9-cell radius is **28 s for
the player against 224 s for the rival**, because the rival *parks* there: `INTERFACE_S` is 80
seconds of standing still to download.

So the asymmetry is eight-to-one exposure, not immunity — the player is at real risk and dies on
one seed in eight. The question is still worth asking, but it is a question about frequency rather
than about whether the player is in the game at all: exposure follows motive, and
`docs/DESIGN-PRINCIPLES.md` §2 says the machinery is where new blocks come from, while in Phase 1
only the aggressive rival wants them.

Designer: [ ] yes, the player should want what the machinery has  [ ] no, leave it the rival's business

## BLD-1 — Phase 1 close-out: run the spectator gate and record what it proved

**Phase Phase 1 — Spectator Test.** Close Phase 1 honestly. Fix the two regressions on HEAD that would make an eight-minute playtest uninterpretable (the SEARCH-mode display crash and a Recall that cannot extract in the default lidar configuration), choose and document the gate configuration, run the human gate with a written, repeatable rubric, and leave a decision record plus preserved renders that Phase 3 can build from and Phase 5 can be scored against. Nothing new is built; this is throwaway Python and the code-quality rules of CLAUDE.md do not apply. The build never reports the gate as met, only ready. The gate configuration is the designer's recorded two-viewings decision (PHASE-1-OPEN-QUESTIONS Part 4, uncommitted: 'THE GATE IS TWO VIEWINGS, SONAR FIRST' — the sonar viewing is scored, the lidar viewing is logged for the sensor question), not a fresh choice; the estimates in this epic are calibrated against the one velocity data point the repo has (BLD-7). Human-gated stories in this epic: 7 of 16 (2 designer decisions or reviews, 3 playtests or self-tests, 2 art, toolchain, CI or commercial), carrying at least 26 calendar days of latency on top of 8.75 working days.

- **Gate — pass:** PHASE-1-SPECTATOR-TEST.md: Watch a player for eight minutes with no explanation beyond "you cannot drive it". Pass: they talk to the screen, guess at contacts, form a wrong theory and correct it, and report tension at the Recall decision. ROADMAP.md adds: they lean in, and can articulate a wrong theory about what a contact was, then correct it.
- **Gate — kill:** PHASE-1-SPECTATOR-TEST.md: Fail: they are bored. Stop. Do not proceed to Phase 2. Report when they disengaged — engagement for four minutes then drift is a pacing problem; never engaging is a design problem, and they are fixed differently. ROADMAP.md: if they're bored, stop and redesign the run phase; this is the one failure that no later work repairs (risk R1, confidence Low).
- **Can start when:** Now. Phase 1 has no predecessor gate and the build exists (HEAD 7fcbe87, working tree clean). The Phase 0 harness epic may proceed in parallel because Phase 0 has no gate dependency on Phase 1 (BLD-20 puts that reading to the designer as a yes/no); the Phase 2 junction test must not start until BLD-16's report exists and does not record a fail, which BLD-42's depends_on encodes.
- **Estimate:** 8.75 working days

| Key | Type | Summary | Pri | Days | Depends on | Risk |
|---|---|---|---|---|---|---|
| BLD-2 | Bug | Fix SEARCH-mode crash: decision_report reads undefined T.RECALL_SEARCH_RADIUS_RATE | P0 | 0.25 | — | R1 |
| BLD-3 | Task | Verify and commit the in-progress Phase 1 retune, one commit per concern | P0 | 0.75 | — | R1 |
| BLD-4 | Task | Pin the Phase 1 Python environment in requirements.txt | P1 | 0.25 | — | — |
| BLD-5 | Task | Write the spectator-test protocol and scoring rubric for Phase 1 and Phase 5 | P0 | 0.5 | — | R1 |
| BLD-6 | Task | Update GLOSSARY Passive/active for sonar and lidar as loadout modules | P1 | 0.25 | — | — |
| BLD-7 | Task | Record Phase 1's velocity data point and state the plan's estimate unit and total | P1 | 0.25 | — | — |
| BLD-8 | Spike | Spike: sweep Recall timings for both player sensors; find why lidar never reaches SEARCH | P0 | 0.75 | BLD-2, BLD-3 | R1 |
| BLD-9 | Story | Apply the two-viewings gate decision: sonar is the gate configuration; retune so the Recall arc can succeed in it | P0 | 1.5 | BLD-8 | R1 |
| BLD-10 | Task | Reconcile tuning.py commentary with its values; write the measured beat sheet | P1 | 0.5 | BLD-9 | R1 |
| BLD-11 | Spike | Spike: measure the contact mix the player actually hears; decide if ambiguity exists | P1 | 0.5 | BLD-9 | R1 |
| BLD-12 | Task | Answer or retire every PHASE-1-OPEN-QUESTIONS item against what was built | P1 | 0.5 | BLD-9, BLD-11 | — |
| BLD-13 | Task | Tick the six PHASE-1 acceptance boxes with seed, args and commit as evidence | P0 | 0.5 | BLD-2, BLD-9, BLD-10, BLD-11 | R1 |
| BLD-14 | Task | Render gate videos for both sensors from one seed and record their provenance | P1 | 0.5 | BLD-13 | R1 |
| BLD-15 | Task | Designer self-test: twenty minutes on the gate build before the external session | P0 | 0.25 | BLD-13, BLD-5 | R1 |
| BLD-16 | Story | Run the Phase 1 gate playtest with a non-engineer and write the readiness report | P0 | 0.5 | BLD-14, BLD-15 | R1 |
| BLD-17 | Task | Write the Phase 1 decision record: what was proved, measured, and handed to Phase 3 | P0 | 1 | BLD-16, BLD-12 | R1 |

### BLD-2 — Fix SEARCH-mode crash: decision_report reads undefined T.RECALL_SEARCH_RADIUS_RATE

**Status:** Done (7fcbe87)  ·  **Bug**  ·  P0  ·  0.25 d  ·  retires R1

phase1/policy/policy.py line 165 reads T.RECALL_SEARCH_RADIUS_RATE inside Policy.decision_report, but commit b43ba0b renamed that constant to RECALL_SEARCH_PITCH in phase1/tuning.py (line 233) and left RECALL_SEARCH_SWEEP marked unused. The view calls decision_report every frame, and the agent enters PolicyMode.SEARCH precisely when a recalled agent reaches its believed shaft and nothing answers, so the live window and the recorder die at the one moment the Recall beat pays off. Statically confirmed by grep; runtime reproduction was not possible in this session, so it is the first acceptance criterion. This is a Phase 1 spec item ('Recall works, once') and the bug would corrupt the gate result.

Done when:
- [x] A one-line Python check calling Policy.decision_report in each PolicyMode (TRAVEL, HOME, LOAD, SEARCH) returns without exception; the SEARCH branch derives the spiral's current radius from the same expression _search uses (4.0 + T.RECALL_SEARCH_PITCH * search_angle) rather than a new constant
- [x] A run at a timing that reaches 'at the shaft, but nothing is answering' (on HEAD: --player-sensor sonar --recall 180 --seed 7) continues through 'shaft acquired' to RESULT with the live window or --record still running
- [x] RECALL_SEARCH_SWEEP is deleted from tuning.py or its comment made true
- [x] python -m phase1 --invariant still passes
- [x] One commit; message states the crash and the moment it fires, not the files touched

**Resolution (2026-09-06, 7fcbe87):** reproduced with `--player-sensor sonar --recall 150 --seed 7`: SEARCH is entered at 7:13, the report reads "widening the circle / 4 cells out" derived from the spiral's own expression, and the match extracts at 7:35. RECALL_SEARCH_SWEEP deleted. `--invariant` still holds. Headless sweeps never build the report, which is why no sweep caught it.

### BLD-3 — Verify and commit the in-progress Phase 1 retune, one commit per concern

**Status:** Done (31a4646, 6ba476e)  ·  **Task**  ·  P0  ·  0.75 d  ·  retires R1

The working tree held +137/-30 uncommitted lines across five files — phase1/tuning.py, phase1/policy/policy.py, phase1/belief/point_cloud.py (occupancy bins, clearance()), phase1/sensing/sensor_rig.py (the sensor layer, the audited World/Belief crossing) and docs/PHASE-1-OPEN-QUESTIONS.md — carrying four separate concerns plus the gate-decision text: (1) map-aware steering (MAP_LOOKAHEAD 9 / MAP_ESCAPE_LOOKAHEAD 18; _steer and _escape_heading read clearance off the believed map) with the measurement that motivated it — with the 2.5-cell feeler alone the spoofed agent spent 2:24 to 8:00 inside one chamber with a 26,000-point map it never used; (2) lidar water-as-wall (sensor_rig.py: a ray reaching water now returns the surface; the 'hole' branch was deleted); (3) the echo moved from 2:15 to 2:35 with the merge-window measurement; (4) ANCIENT_PHASE_S 20 -> 30 'measured after map-aware steering moved every path'; (5) the two-viewings gate decision in Part 4. Steering moved every path, so every beat must be re-verified before this becomes the gate build. Per CLAUDE.md, small commits, one concern each.

Done when:
- [x] python -m phase1 --invariant passes with every change (this covers the sensor_rig.py change to the audited crossing)
- [ ] A no-recall headless run at seed 7 in the sonar viewing still shows the spoof fix landing near 2:20 with a jump of at least 30 cells and a surprise of at least 10x in the belief log
- [x] The post-spoof aftermath no longer shows the agent confined to a single chamber until 8:00 (headless truth lines show movement between chambers after the spoof)
- [x] In the sonar viewing the echo at 2:35 appears as its own contact event rather than merging into the rival's standing contact
- [ ] The rival dies at about 5:41 (sonar) / 5:45 (lidar) with ANCIENT_PHASE_S 30
- [x] A lidar run maps the sump as a wall and the agent steers round it; the doc paragraph that describes the decision commits with the tuning it describes
- [ ] One commit per concern (steering, lidar water, echo timing, ancient phase, gate-decision text), each message stating the measured problem and the fix; no working-tree changes remain

**Resolution (2026-09-06):** landed as two commits rather than five — 31a4646 carries steering, lidar water, echo timing, ancient phase and the gate text together; 6ba476e carries the rival's machinery behaviour. Measured over eight seeds on the final tuning: the spoof fires 8/8 (the surprise ratio was not re-measured), the player's longest post-spoof stall has a median of 88 s (sonar) / 96 s (lidar) with chamber changes after it, the echo is its own contact, and the rival dies 4/8 (sonar) and 2/8 (lidar) — not every seed, so the 5:41 above is one seed's number, not a property. The residual is the C3 → machinery passage, which is BLD-101's problem, not a Phase 1 one.

### BLD-4 — Pin the Phase 1 Python environment in requirements.txt

**Status:** Backlog  ·  **Task**  ·  P1  ·  0.25 d

No requirements file exists. The gate has to run on the designer's machine, and the Phase 5 gate ('scores better than the Python version did', ROADMAP Phase 5) re-runs this test against the Python baseline months from now. The .venv currently holds numpy 2.5.2, vispy 0.16.2, PyQt6 6.11.0 (Qt 6.11.2, sip 13.12.0), sounddevice 0.5.6, imageio 2.37.4, imageio-ffmpeg 0.6.0 on Python 3.13. PHASE-1-OPEN-QUESTIONS Part 3 fixes the library choices; this only pins them.

Done when:
- [ ] requirements.txt at the repo root pins numpy, vispy, PyQt6, sounddevice, imageio, imageio-ffmpeg to the exact versions in the current .venv, with a one-line header naming Python 3.13
- [ ] A fresh venv built from it runs python -m phase1 --headless --seed 7 to a RESULT line and python -m phase1 --invariant to 'invariant holds'
- [ ] No build system, lockfile tooling, or config system is added

### BLD-5 — Write the spectator-test protocol and scoring rubric for Phase 1 and Phase 5

**Status:** Backlog  ·  **Task**  ·  P0  ·  0.5 d  ·  retires R1

The Phase 5 gate is 'Phase 1's spectator test, re-run in the real client, scores better than the Python version did' (ROADMAP Phase 5). Without a written rubric and preserved session record there is nothing to compare against in a year. The protocol also has to make the spec's failure taxonomy scorable: talked to the screen, guessed at contacts, formed and corrected a wrong theory, reported tension at Recall, and the minute of disengagement if bored (four minutes then drift is pacing; never engaged is design). The protocol encodes the designer's two-viewings decision (Part 4): viewing one on sonar is the scored viewing; viewing two on lidar is logged separately, with the caveat written into the observer notes that a tester who has seen both worlds compares rather than reacts. One markdown file, no tooling.

Done when:
- [ ] docs/PHASE-1-PLAYTEST-PROTOCOL.md contains: setup (no explanation beyond 'you cannot drive it', R key only, audio on, truth hidden until the match ends), the observer checklist mapped one-to-one to the three pass criteria, a place to log the disengagement minute, and the designer's twenty-minute self-test check
- [ ] A scoring scale per criterion (e.g. 0 to 2 with anchors) so two sessions a year apart can be compared numerically
- [ ] A session-notes template with fields for player background, build commit, seed, sensor configuration, recall timing chosen and when, verbatim quotes, and the wrong theory and its correction
- [ ] The file states that the report says 'ready for gate' or records observations, and never 'gate met' (CLAUDE.md)
- [ ] The protocol specifies two viewings, sonar first: viewing one is scored against the three pass criteria; viewing two (lidar) is logged separately with the compare-versus-react caveat written into the observer notes, and the two are never pooled into one score

### BLD-6 — Update GLOSSARY Passive/active for sonar and lidar as loadout modules

**Status:** Backlog  ·  **Task**  ·  P1  ·  0.25 d

GLOSSARY.md still says active sensing 'announces your position to every listener in range' and that 'Do I ping?' is the central decision. PHASE-1-OPEN-QUESTIONS Part 4 records the designer's decision that sonar (loud, long range, works in water) and lidar (silent, short, precise, blind through water or silt, a line-of-sight light tell) are both loadout modules locked at launch, and explicitly leaves the vocabulary update to the designer 'since it is the one document that defines the vocabulary'. Logged open item; designer-owned. Human-gated (designer-owned glossary edit): expect about 3 calendar days and 1 round-trip(s) with the designer or testers beyond the 0.25 working days of work.

Done when:
- [ ] The Passive / active entry distinguishes acoustic-active (basin-wide announcement, works in water) from optical-active (silent, line-of-sight exposure, blind at the waterline and in silt)
- [ ] 'Do I ping?' is restated so it moves for a lidar carrier ('where do I dare to go') rather than disappearing
- [ ] The Module or Loadout entry notes that sonar and lidar are modules and that a Swimmer can only sensibly carry sonar
- [ ] Edited by the designer, or drafted by an agent and explicitly approved before commit

### BLD-7 — Record Phase 1's velocity data point and state the plan's estimate unit and total

**Status:** Backlog  ·  **Task**  ·  P1  ·  0.25 d

All sixteen Phase 1 commits (~4,700 lines: headless sim, belief, sensors, policies, view, audio, recorder, invariant checker) landed between 13:11 and 17:35 UTC on 2026-09-06 per git log, against PHASE-1-SPECTATOR-TEST's 'Estimated: 2-3 weekends'. Construction ran roughly twenty times faster than the plan's estimate unit, while the gate playtest and every designer decision still take calendar time, and the faults found after construction (Recall never extracting until b43ba0b, honest loop closures worsening error in 4909bcb, the SEARCH crash still at policy.py:165) show verification is where the hours go. This plan sums to 478.25 working days across ten epics, which at ten working days a month is 47.8 months, against ROADMAP.md's '18-24 months of nights and weekends... a floor' (line 175); per phase, P0 (17.5 d) is about 9x its '1 weekend', P3 (116.25 d) about 2.3-3.9x its '3-5 months', P4/P5/P6 about 1.5-2.5x. The plan tags every story agent-buildable or human-gated (labels) and gives human-gated stories a calendar estimate beside the working days; this task writes the arithmetic and the unit down so the designer decides on the number now rather than discovering it in month fourteen. Human-gated (designer decision on the ROADMAP floor): expect about 3 calendar days and 1 round-trip(s) with the designer or testers beyond the 0.25 working days of work.

Done when:
- [ ] The plan's totals section and docs/ROADMAP.md carry per-epic and total working days, the ten-days-a-month conversion, and the ratio to ROADMAP per phase and in total (P0 17.5 d vs ~1 weekend; P3 116.25 d vs 3-5 months; 478.25 d vs 18-24 months)
- [ ] Every story carries the label agent-buildable or human-gated (designer decision, playtest, three-OS CI debugging, art, Godot toolchain, commercial); human-gated stories carry an expected calendar duration and round-trip count beside working days
- [ ] Per epic, the number of designer decisions and human playtests on the critical path is listed in the epic goal
- [ ] The Phase 1 data point (spec 2-3 weekends; construction ~4.5 h wall-clock; gate not yet run) is recorded as the calibration baseline, and BLD-40's actual-versus-'1 weekend' figure is added when it exists
- [ ] ROADMAP.md's floor is either re-baselined in a one-line note or the designer records which epics or stories are cut to fit it

### BLD-8 — Spike: sweep Recall timings for both player sensors; find why lidar never reaches SEARCH

**Status:** Backlog  ·  **Spike**  ·  P0  ·  0.75 d  ·  depends on BLD-2, BLD-3  ·  retires R1

Commit b43ba0b measured three of twelve Recall timings extracting with cargo, but two later commits (HEADING_FIX_GAIN 0.7 to 0.0 in 4909bcb; lidar made the player default in 4e2cc17) were never re-swept. Reported measurements on HEAD at seed 7: lidar player extracts at 0 of 9 timings and never logs 'at the shaft, but nothing is answering', so the spiral search that tuning.py calls 'the only thing in the match that can undo a spoof' never runs; the sonar player extracts at 1 of 9. The measurements quoted here predate the uncommitted retune that moved every path and the two-viewings decision (sonar viewing scored, lidar viewing logged for the sensor question), so this spike re-measures on the fixed build (after BLD-2 and BLD-3), cites commit hashes, and finds the cause for lidar so that viewing two is a fair comparison. Candidate causes to test, not assume: HOME_REACHED (6 cells) never satisfied by a lidar-steered wall-follower; the lidar map's waterline holes routing the return; the uncertainty return interacting with the recall route.

Done when:
- [ ] A table of recall timings 3:00 to 7:00 at 30 s steps, for --player-sensor sonar (the gate viewing) and lidar (viewing two) at seed 7, giving RESULT outcome, cargo, and whether 'nothing is answering' and 'shaft acquired' logged, produced by the headless runner on a cited commit hash and saved in the story
- [ ] A one-paragraph diagnosis naming the mechanism that stops the lidar player reaching SEARCH, with the log lines that show it
- [ ] A recommendation for BLD-9: which single constants to change so the sonar viewing can extract and, separately, what the lidar viewing needs to reach SEARCH

### BLD-9 — Apply the two-viewings gate decision: sonar is the gate configuration; retune so the Recall arc can succeed in it

**Status:** Backlog  ·  **Story**  ·  P0  ·  1.5 d  ·  depends on BLD-8  ·  retires R1

PHASE-1-OPEN-QUESTIONS Part 4 (uncommitted) and phase1/tuning.py lines 89-102 already record the designer's decision: 'THE GATE IS TWO VIEWINGS, SONAR FIRST', PLAYER_SENSOR = "sonar". Viewing one (sonar) is scored against the three pass criteria; viewing two (lidar) answers the sensor question and is logged separately, because a tester who sees both worlds compares rather than reacts. This story applies that decision instead of re-opening it (the draft plan asked the designer to choose again; the answer exists). On HEAD in the sonar configuration 1 of 9 recall timings extract and the uncertainty return fires at 6:11, so the retune target is: Recall can extract, the cautious agent's defining rule fires in the sonar viewing, and the spoof still lands before the return. Tuning.py's own rule applies: every changed value carries the measurement that prompted it.

Done when:
- [ ] PLAYER_SENSOR = "sonar" is committed with the Part 4 reason beside it, and the Sensors paragraph of PHASE-1-SPECTATOR-TEST.md is amended in one line so spec and code agree (two viewings, sonar scored, lidar logged)
- [ ] In the sonar configuration a sweep of recall timings 3:00 to 7:00 at 30 s steps yields at least one RESULT of 'extracted' with cargo > 0, and success is not monotonic in send time (a late recall still fails)
- [ ] At least one timing logs 'at the shaft, but nothing is answering' followed by 'shaft acquired'
- [ ] A no-recall run in the sonar configuration logs 'uncertainty N > 16.0: heading home' after the spoof fix and before 6:30 (HEAD: 6:11), OR tuning.py records the designer's explicit acceptance that it does not fire and why
- [ ] The spoof still lands before the uncertainty return (tuning.py: at 4:00 the return fired first at 3:31 and made Recall worthless)
- [ ] The lidar viewing is re-swept with the same table so the sensor comparison in viewing two is measured, not assumed
- [ ] Every constant changed carries its measurement in tuning.py; the sweep table is written next to the changed values; no new mechanisms are added

### BLD-10 — Reconcile tuning.py commentary with its values; write the measured beat sheet

**Status:** Backlog  ·  **Task**  ·  P1  ·  0.5 d  ·  depends on BLD-9  ·  retires R1

tuning.py's SPOOF_AFTER_S comment argues that '3:20 with the trigger at 16 does both' while the value is 140.0 (2:20), and the same note says the 2:30 aftermath was 'one note held far too long'. PHASE-1-OPEN-QUESTIONS pushback 10 still carries the proposed timeline, not the measured one. The timeline quoted in the draft plan (echo 2:15 and 2:16.5, spoof fix 2:20.3 with jump 34.1 and surprise 11.4x, rival death 5:51) predates the uncommitted retune: the echo moved to 2:35 because at 2:15 it was absorbed into the rival's standing contact inside the 18-degree merge window, ANCIENT_PHASE_S moved to 30 because at 20 nobody died, and map-aware steering 'moved every path'. This story re-measures the beat sheet on the sonar viewing after BLD-3 and BLD-9, cites commit hashes, and writes down what is actually true so the playtest is run against a known beat sheet. Human-gated (designer viewing of the aftermath): expect about 3 calendar days and 1 round-trip(s) with the designer or testers beyond the 0.5 working days of work.

Done when:
- [ ] SPOOF_AFTER_S's comment and value agree and cite the measurement behind the final choice
- [ ] Pushback 10's proposed table in PHASE-1-OPEN-QUESTIONS.md is replaced by the measured timeline for the gate configuration, labelled with seed, CLI args and commit hash
- [ ] The designer has watched the post-spoof aftermath in the gate render and recorded in the same section whether it 'flattens into one note'
- [ ] At most one tuning constant changes in this story, with its measurement
- [ ] The measured table includes the echo at 2:35 with its merge reason, ANCIENT_PHASE_S 30 with the rival death time, and the spoof fix jump and surprise as re-measured, each against a commit hash

### BLD-11 — Spike: measure the contact mix the player actually hears; decide if ambiguity exists

**Status:** Backlog  ·  **Spike**  ·  P1  ·  0.5 d  ·  depends on BLD-9  ·  retires R1

Logged open item: all contacts are pings. The spec's tension is 'a bearing with no range, which might be a rival, an ancient system, or an echo'. In the gate configuration the player's passive returns are rival sonar pings (PING), the scripted echo (also PING, ECHO_TIMES 135 and 136.5 s), the ancient signature (SIGNATURE, a distinct rising drone), a CRASH on the rival's death, and rival motion (TONE) only within HEAR_MOTION_RANGE 40 cells, which the routes may never satisfy (open question L5 was never answered). If every ambiguous contact is a ping, the three-way ambiguity the phase claims to test may not be on screen. The uncommitted ECHO_TIMES note records that at 2:15 the echo arrived on bearing 23 while the rival's own pings were a standing contact on bearing 13, inside the 18-degree merge window, so it was absorbed and never appeared as its own event, and that lowering the merge angle does not help because both sounds enter the chamber down the same passage; the measurement must show whether the 2:35 echo appears as its own event. This spike measures rather than guesses, and does not add a sensor. Human-gated (designer decision on the contact mix): expect about 3 calendar days and 1 round-trip(s) with the designer or testers beyond the 0.5 working days of work.

Done when:
- [ ] A table from a no-recall headless run in the gate configuration counting Bearing returns reaching the player by SoundCharacter (PING, TONE, SIGNATURE, CRASH) and by true source (rival ping, echo, ancient, motion), with first-arrival times
- [ ] A written decision in PHASE-1-OPEN-QUESTIONS.md rows P1 and L5: either the mix is accepted for the gate with the reason, or one bounded retune (e.g. HEAR_MOTION_RANGE or the rival route so it passes within earshot once) is made with its measurement and the beat sheet from BLD-10 is re-verified
- [ ] No new sensor, sound character, or scripted event is added

### BLD-12 — Answer or retire every PHASE-1-OPEN-QUESTIONS item against what was built

**Status:** Backlog  ·  **Task**  ·  P1  ·  0.5 d  ·  depends on BLD-9, BLD-11

The doc promised no code until the numbers were answered inline; instead the implementation chose and tuning.py became the sheet, with only Part 4 recording a designer decision. Later phases will re-litigate settled things (waterline semantics, passage propagation, spoof mechanism, recall behaviour) unless each pushback and each numbered quantity points at where the code answered it. De facto answers include: pushback 1 yes (belief/pose_correction.py), 2 heading-bias dominated, 3 yes (known_beacon.py, only the shaft is truth_anchor), 4 ratio 34/6 with reassert, 5 option (a) near-field built, 6 2D sim with 3D scatter and flooded cells as the waterline, 7 path propagation via Dijkstra in sound_field.py, 8 both built, 9 rival has its own Belief, B4 rising-edge fix, B7 spoof clones a known beacon ID, R1 straight to believed shaft then spiral, R2 3 s + 0.02 s per cell. Doc-only. Human-gated (designer review of de-facto answers): expect about 5 calendar days and 1 round-trip(s) with the designer or testers beyond the 0.5 working days of work.

Done when:
- [ ] Every pushback 1 to 10 carries a '[built as: ...]' line naming the module or constant, or is marked still open
- [ ] Every numbered quantity T1 to R4 points at its tuning.py constant and value, or is marked unset
- [ ] Any answer the designer disagrees with becomes a named Phase 1 retune story rather than a silent code change
- [ ] No config system or tooling is added

### BLD-13 — Tick the six PHASE-1 acceptance boxes with seed, args and commit as evidence

**Status:** Backlog  ·  **Task**  ·  P0  ·  0.5 d  ·  depends on BLD-2, BLD-9, BLD-10, BLD-11  ·  retires R1

All six 'ready for the gate' boxes in PHASE-1-SPECTATOR-TEST.md are unchecked, and 'Recall works, once' is currently true only in the sense that the command is delivered. Each box gets evidence from the gate build so the build agent can report readiness without reporting the gate met (CLAUDE.md definition of done).

Done when:
- [ ] 'Eight-minute match runs start to finish without intervention': a headless and a live run at the gate seed reach RESULT with no exception, cited by commit hash
- [ ] 'Point cloud visibly smears under drift and snaps on a fix': a fix jump of at least 30 cells visible in the render, with the FixRecord surprise value quoted
- [ ] 'The spoofed beacon fires and the agent acts on the wrong fix': the spoof fix log line with surprise >= 10x followed by 'cannot reach ... skipping' entries
- [ ] 'Contacts are audible and directional' and 'Rival pings appear as wavefronts from a bearing': confirmed on the live build with audio on, noted with the sensor configuration
- [ ] 'Recall works, once': an 'extracted' RESULT with cargo > 0 at a stated recall timing in the gate configuration, not merely delivery
- [ ] python -m phase1 --invariant passes on the gate commit; the checklist in the spec is ticked with seed, CLI args and commit for each box

### BLD-14 — Render gate videos for both sensors from one seed and record their provenance

**Status:** In progress  ·  **Task**  ·  P1  ·  0.5 d  ·  depends on BLD-13  ·  retires R1

Four gitignored mp4s (about 175 MB) sit at the repo root with nothing recording which commit, seed, sensor or recall timing produced them; The current pair (phase1-sonar.mp4 8:12, phase1-lidar.mp4, both h264+aac 1600x1000, seed 7, no Recall) was rendered from 6ba476e, one commit before the BLD-2 fix; neither reaches SEARCH, so neither exercised the crash. A Recall render must come from 7fcbe87 or later. The recorder exists so the eight minutes can be replayed for the gate and, later, compared by the Phase 5 gate. Part 4 asks that both sensor versions be rendered from the same seed and compared.

Done when:
- [ ] phase1-lidar and phase1-sonar renders exist from the same seed and the same gate commit, each with the chosen recall timing, produced by python -m phase1 --record
- [ ] docs/phase1-playtests/RENDERS.md (or equivalent single file) lists each video's filename, commit hash, seed, CLI args, recall timing and duration; videos themselves stay out of git and are copied to durable storage named in that file
- [ ] The sonar render completes through the SEARCH beat without the recorder stopping
- [ ] The sonar render is the one labelled 'gate' (viewing one) in RENDERS.md; the lidar render is labelled 'viewing two / sensor comparison'

### BLD-15 — Designer self-test: twenty minutes on the gate build before the external session

**Status:** Done  ·  **Task**  ·  P0  ·  0.25 d  ·  depends on BLD-13, BLD-5  ·  retires R1

**Gate (2026-09-06):** designer self-test run on 2026-09-06 before the external session; reported green.

PHASE-1-SPECTATOR-TEST.md: 'Test it alone first. You will know within twenty minutes whether you are leaning forward.' The two earlier 'playtest feedback' commits were the designer watching renders, not a live session on the gate build. This is the go/no-go for spending someone else's evening. Human-gated (designer self-test): expect about 2 calendar days and 1 round-trip(s) with the designer or testers beyond the 0.25 working days of work.

Done when:
- [ ] The designer plays the gate build live (not a render) once in the sonar gate configuration with audio, spending Recall at a moment of their choosing
- [ ] Notes in the self-test section of the protocol: leaning forward or not, the minute anything became unreadable, and whether Recall's outcome was legible from belief alone
- [ ] An explicit go or no-go for BLD-16; a no-go names the fix as a Phase 1 retune story rather than starting Phase 2 work

### BLD-16 — Run the Phase 1 gate playtest with a non-engineer and write the readiness report

**Status:** Done (fail)  ·  **Story**  ·  P0  ·  0.5 d  ·  depends on BLD-14, BLD-15  ·  retires R1

**Gate (2026-09-06): FAIL.** The observations are in `docs/phase1-playtests/2026-09-06-gate.md`. She was silent until the end, bored in the middle, and reported that it was hard to understand and needed more action -- "all that changes is things kinda beep and nothing really is obvious". No moment of engagement to drift from, so on the spec's own split this reads as a design problem rather than pacing. One confound: she watched the video, not the live window, so the Recall criterion was structurally unavailable. R1 is live.

This is the Phase 1 gate and the one failure that no later work repairs (ROADMAP: risk R1, confidence Low). No commit or document records it having been run. The designer wants Rust to start as soon as this lands; the report is what unblocks the Phase 2 group and, transitively, Phase 3. The build agent cannot declare the gate met; it reports readiness and the observations (CLAUDE.md definition of done). Human-gated (external playtest with a non-engineer): expect about 7 calendar days and 1 round-trip(s) with the designer or testers beyond the 0.5 working days of work.

Done when:
- [ ] A player who is not the designer and not an engineer watches eight minutes of the gate build with no explanation beyond 'you cannot drive it' and only the R key available; the session follows docs/PHASE-1-PLAYTEST-PROTOCOL.md
- [ ] Session notes record, with quotes: whether they talked to the screen, their guesses at contacts, the wrong theory they formed and whether and when they corrected it, and what they said at the moment they decided whether to Recall
- [ ] If they disengaged, the minute is recorded and the result is classified as pacing (engaged then drifted) or design (never engaged)
- [ ] The report is filed under docs/phase1-playtests/ with build commit, seed, sensor configuration and the rubric scores, and states 'ready for gate' plus observations, never 'gate met'
- [ ] If the result is a fail, no Phase 2 story starts and the report says so; the Phase 0 harness group is unaffected either way
- [ ] The report scores viewing one (sonar) against the rubric and records viewing two's (lidar) observations separately, never pooled; the session record names which viewing each quote came from

### BLD-17 — Write the Phase 1 decision record: what was proved, measured, and handed to Phase 3

**Status:** Backlog  ·  **Task**  ·  P0  ·  1 d  ·  depends on BLD-16, BLD-12  ·  retires R1

Phase 1 is throwaway code, so its findings survive only if written down. Several change design or architecture text: a fix must back-propagate onto every point placed since the previous fix or the snap never happens (ARCHITECTURE's Belief.map: OccupancyMap cannot do this as written); a beacon fix corrects position only, HEADING_FIX_GAIN is 0.0 because half of honest loop closures made the agent more wrong, so heading drift is uncorrected until terrain-relative navigation exists; the beacon chain buys confidence not accuracy because own beacons anchor to past belief and only the shaft is a truth anchor (known_beacon.py); sound propagates along passages and the Dijkstra is the worst tick (33 ms vs 0.36 ms mean) which fixes 20 Hz and threatens larger caves; sonar and lidar are loadout modules and the lidar line-of-sight tell is noted, not built (tuning.py lines 95-96); spoof lie divided by beacon range is the key ratio and a spoof disarms the uncertainty return by design; Recall is terminal, drives straight at the believed shaft, then spirals; fix surprise is the only belief-legal spoof tell; ARCHITECTURE's Return enum lacks Odometry and a relative beacon Fix. Three more measured lessons from the uncommitted retune are findings in their own right: map-aware steering off the believed map is what finds the door after a spoof (the map is globally wrong by the drift and so is the agent, so locally it is right), with the 28 s give-up (STUCK 5 s + ESCAPE 9 s x 2) so a lost agent looks like it is failing to get somewhere rather than stuck in a loop; a same-passage echo merges into a standing contact inside the bearing merge window and no merge-angle change fixes it; and the spoof's Phase 1 arming rule was truth-side (displacement from the target beacon in the victim's belief frame) and does not port to a Belief-only rival. The record also closes the logged open items (all contacts are pings, spiral search never fires, beacon chain, lidar tell, glossary) with their outcomes, and includes the playtest result. It records questions for Phase 3; it does not answer them (CLAUDE.md: ask rather than invent).

Done when:
- [ ] docs/PHASE-1-DECISIONS.md exists with one entry per finding: what was measured (numbers, seed, commit), what it implies, and which downstream doc or crate it touches (ARCHITECTURE Return/Belief/BeliefUpdater, DETERMINISM tick rate, DESIGN beacon note, GLOSSARY)
- [ ] Each of the five logged open items has an entry with its outcome and the story that resolved or deferred it (BLD-11, BLD-8/BLD-9, known_beacon.py note, lidar tell deferred to Phase 3 optics, BLD-6)
- [ ] The Phase 1 tuning that becomes Phase 3's reference is tabulated: 20 Hz, 8-minute match, extraction at 6:30, beacon drop 45 / range 6 / shaft 10 (with the note that 'the gap between 6 and 45 is where the smear happens'), heading bias 0.11 deg per cell, spoof 34/6 with range 18 and reassert 8 s, ancient 75/9/4 s with phase offset 30 s, echo at 2:35 and its merge reason, MAP_LOOKAHEAD 9 / MAP_ESCAPE_LOOKAHEAD 18, give-up 28 s (STUCK 5 s + ESCAPE 9 s x 2), deposit radius 12, cautious return sigma 16, lidar water returns as a wall, and the gate as two viewings sonar first
- [ ] A short list of questions for the designer that Phase 3 must not guess at (Belief.map representation, Odometry and relative Fix in the Return enum, tick rate, whether the near-field sense is a module or intrinsic, lidar's place among the six sensors)
- [ ] The playtest report from BLD-16 is linked and its result stated verbatim; the record says the build was reported ready for the gate, not that the gate was met

## BLD-18 — Phase 0 — Harness: headless runner, desync canary, replay, bisect, determinism lint, three-OS CI

**Phase Phase 0 — Harness.** Build the Rust tooling that makes eighteen months of determinism work survivable, against an empty blindside-sim, before any game logic exists. Deliverables per docs/PHASE-0-HARNESS.md and docs/DETERMINISM.md: a headless runner over MatchRecord, a per-tick state hash with an explicit coverage list, a desync canary proven against an injected HashMap-iteration bug, a replay format carrying seed + input log + content pack hash + schema, one-command bisect-by-tick with a structural diff, a CI determinism lint over blindside-sim/vm/gen, and a Linux/macOS/Windows CI matrix with required status checks. The truth/belief boundary (World pub(crate), Belief pub) is laid down now so the harness is never the leak path. blindside-sim stays an empty skeleton throughout: Phase 3 is blocked on the Phase 1, 2 and 0 gates. Human-gated stories in this epic: 3 of 22 (2 designer decisions or reviews, 0 playtests or self-tests, 1 art, toolchain, CI or commercial), carrying at least 14 calendar days of latency on top of 17.5 working days.

- **Gate — pass:** PHASE-0-HARNESS.md acceptance criteria, verbatim: (1) An empty sim runs 10,000 ticks in two instances with identical hashes every tick. (2) A deliberately introduced non-determinism (e.g. a HashMap iteration) is caught by the canary within the tick it occurs. (3) The same replay produces identical final hashes on Linux, macOS, and Windows in CI. (4) Bisect tooling locates an injected divergence in one command. (5) CI lint rejects a PR adding f64 to blindside-sim. ROADMAP wording: an empty sim runs 10,000 ticks on two instances with identical hashes — trivial now, impossible to retrofit later.
- **Gate — kill:** PHASE-0-HARNESS.md: 'The second criterion matters most. A canary that does not catch a known bug is worse than no canary, because it is trusted.' If the injected HashMap iteration is not caught in the tick it occurs, or the same replay's final hash differs on any of the three OSes, Phase 3 does not start. CLAUDE.md: if a gate fails, stop and report; do not work around it. Never report this gate as met — report the build as ready for the gate with evidence links.
- **Can start when:** Immediately. No document places a predecessor gate before Phase 0: CLAUDE.md's 'do immediately before 3' and PHASE-0's 'build immediately before Phase 3, not first' are read as priority statements (do not let the harness rot), not blockers — this is an interpretation that contradicts the literal spec text, so BLD-20 puts it to the designer as a yes/no on day one and records the dated answer in docs/HARNESS.md, and BLD-40 and BLD-66 assert that nothing crept into blindside-sim during the parallel window. It runs in parallel with the Phase 1 gate playtest and with Phase 2 (throwaway Python). Constraint that keeps the build order honest: blindside-sim gains no sensors, belief fusion, generation or any game logic until the Phase 2 gate report exists; Phase 3 remains blocked on gates 1, 2 and 0 and BLD-66 encodes that in depends_on. Stories BLD-19 and BLD-20 have no dependencies and start on day one; BLD-21 follows BLD-19.
- **Estimate:** 17.5 working days

**Where it actually is (2026-09-06):** branch `claude/phase-0-harness` carries a working harness that meets all five PHASE-0-HARNESS acceptance criteria. CI run 34062222514 on commit `0051189` is green on ubuntu-24.04, macos-26-arm64 and windows-2025 with byte-identical 5,001-entry hash logs (sha256 `365f7d33…6513`, reproduced on the dev machine). The stories below were written before that branch existed and their Done-when lists are stricter than the spec's criteria, so none is ticked; each carries a *Built so far* line saying what exists and what its own criteria still want. Two things the branch did that the plan says not to: every BLD-20 unknown was defaulted rather than asked (the defaults are listed under BLD-20 so the designer can answer yes/no), and CI builds with `--workspace`, which BLD-29 forbids for hash-producing binaries. 

| Key | Type | Summary | Pri | Days | Depends on | Risk |
|---|---|---|---|---|---|---|
| BLD-19 | Task | Create the Cargo workspace, pin the toolchain, and lock blindside-sim's dependency tree | P0 | 0.5 | — | — |
| BLD-20 | Spike | Spike: put the harness's load-bearing unknowns to the designer in one written round | P0 | 0.5 | — | R4 |
| BLD-21 | Spike | Spike: choose the determinism-lint mechanism and prove it catches the known evasions | P0 | 0.5 | BLD-19 | — |
| BLD-22 | Story | Land the CI determinism lint and prove a PR adding f64 to blindside-sim goes red | P0 | 1 | BLD-19, BLD-21 | R4 |
| BLD-23 | Story | Build the empty blindside-sim: Sim::new(&MatchRecord), step, tick, state_hash; World pub(crate) | P0 | 0.5 | BLD-19, BLD-22 | — |
| BLD-24 | Story | Add Fx, the fixed-point math module home, and stateless DeterministicRng with golden tests | P0 | 1 | BLD-19, BLD-20, BLD-22 | R4 |
| BLD-25 | Task | Provide DeterministicRng-based test helpers and settle the dev-dependency lint policy | P1 | 0.5 | BLD-24, BLD-21, BLD-22 | R4 |
| BLD-26 | Story | Compute the content pack hash in blindside-content and refuse mismatching replays | P0 | 0.5 | BLD-19, BLD-20 | — |
| BLD-27 | Story | Implement the per-tick state hash with an explicit coverage list and mutation tests | P0 | 1 | BLD-20, BLD-23, BLD-24 | R4 |
| BLD-28 | Story | Expose a feature-gated, string-only structural diff of two Sims for the canary | P0 | 0.5 | BLD-20, BLD-23, BLD-27 | — |
| BLD-29 | Story | Guard against Cargo feature unification exposing diagnostics or inject-desync outside the harness | P0 | 0.5 | BLD-28, BLD-22 | — |
| BLD-30 | Story | Define MatchRecord serialisation, schema version, migration hook, and recorded final hash | P0 | 1 | BLD-20, BLD-23, BLD-27, BLD-26 | — |
| BLD-31 | Story | Build the blindside-harness binary: run, record and verify subcommands, hash log, throughput | P0 | 1 | BLD-23, BLD-27, BLD-30, BLD-26 | — |
| BLD-32 | Story | Scaffold the compile-fail test that nothing outside blindside-sim can reach World | P1 | 0.5 | BLD-23, BLD-28 | — |
| BLD-33 | Story | Build the desync canary: two Sims in lockstep, hash compared every tick, panic with diff | P0 | 1 | BLD-23, BLD-27, BLD-28, BLD-31 | R4 |
| BLD-34 | Task | Add the unsafe policy and PR template for the non-lintable determinism rules | P1 | 0.5 | BLD-19, BLD-22 | — |
| BLD-35 | Story | Inject a HashMap-iteration non-determinism and prove the canary catches it in the tick | P0 | 1 | BLD-33, BLD-21, BLD-22, BLD-29 | R4 |
| BLD-36 | Story | Build one-command bisect: first divergent tick, both hashes, and the state diff | P0 | 1.5 | BLD-20, BLD-28, BLD-31, BLD-35 | R4 |
| BLD-37 | Story | Run build, lint, canary, golden replay and cross-OS hash compare on Linux/macOS/Windows CI | P0 | 2 | BLD-33, BLD-31, BLD-30, BLD-22, BLD-35, BLD-29 | R4 |
| BLD-38 | Story | Add the batch executor: N seeds in parallel across matches with a seed-to-hash table | P1 | 1 | BLD-31, BLD-37 | R4 |
| BLD-39 | Task | Write docs/HARNESS.md and reconcile ARCHITECTURE's MatchRecord and ROADMAP's crate names | P1 | 0.5 | BLD-20, BLD-21, BLD-36, BLD-37 | — |
| BLD-40 | Task | Verify all five Phase 0 acceptance criteria on one commit and report ready for the gate | P0 | 0.5 | BLD-34, BLD-35, BLD-36, BLD-37, BLD-38, BLD-32, BLD-39, BLD-29, BLD-25 | R4 |

### BLD-19 — Create the Cargo workspace, pin the toolchain, and lock blindside-sim's dependency tree

**Status:** In progress  ·  **Task**  ·  P0  ·  0.5 d

**Built so far (2026-09-06, `claude/phase-0-harness`):** workspace of five crates; `rust-toolchain.toml` floats on `stable` rather than an exact version; `Cargo.lock` committed; blindside-sim depends on exactly `fixed` and `blake3`, enforced by the lint's `--check-all` allow-list rather than a `cargo metadata` test. Not yet: `=x.y.z` pins, `.gitattributes eol=lf` (every commit today warns LF→CRLF), per-crate descriptions.

ARCHITECTURE.md fixes the crate names (blindside-*, not ROADMAP's stale deadwater-*) and says 'blindside-sim depends only on blindside-vm and blindside-content. That constraint is load-bearing — it keeps determinism auditable by reading one dependency tree.' The repo has no Cargo.toml, rust-toolchain, .github or .gitattributes today. Phase 0 creates only the crates it needs — sim, vm (stub), content (stub), gen (stub, a lint target), harness — and none of behavior/induct/client/net. Line-ending normalisation lands here because Windows autocrlf checkouts would otherwise change fixture bytes and the content hash.

Done when:
- [ ] Root Cargo.toml workspace with blindside-sim, blindside-vm, blindside-content, blindside-gen, blindside-harness; `cargo build --workspace` and `cargo test --workspace` pass on the Windows dev machine
- [ ] rust-toolchain.toml pins an exact stable version; Cargo.lock is committed
- [ ] A test in blindside-harness (or a CI step over `cargo metadata`) fails if blindside-sim's dependencies include any workspace crate other than blindside-vm and blindside-content
- [ ] Every external dependency of sim/vm/gen is pinned `=x.y.z` and listed in an allowlist file; adding a dependency to those crates without editing the allowlist fails the same check; `rand` and any rand-family crate are absent
- [ ] `.gitattributes` sets `eol=lf` for `*.rs`, `*.toml`, `content/**` and `fixtures/**`; a fresh clone on Windows with autocrlf=true produces identical bytes (verified by `git ls-files --eol`)
- [ ] Each crate's Cargo.toml `description` is its one-line responsibility from ARCHITECTURE's crate layout block

### BLD-20 — Spike: put the harness's load-bearing unknowns to the designer in one written round

**Status:** Backlog  ·  **Spike**  ·  P0  ·  0.5 d  ·  retires R4

**Built so far (2026-09-06, `claude/phase-0-harness`):** not done, and it is the first thing to do. The builders defaulted every unknown this story exists to ask: hasher = BLAKE3 over a hand-written LE layout; serialisation = JSON; `Tick` = u64; arithmetic wraps (`wrapping_add`) with no overflow-checks decision; MatchRecord carries `final_hash` and `ticks`; bisect assumes a divergence never heals; RNG mix = SplitMix64 finaliser; content hash = BLAKE3 over `CONTENT_SCHEMA` alone (the empty pack). Put exactly that list to the designer as yes/no with the default as the recommendation.

CLAUDE.md: 'Ask rather than invent... A wrong guess that compiles is worse than a question.' The Phase 0 docs are silent on several things every later replay will hash: the state hasher and its width (256-bit to match content_hash [u8;32] vs 64-bit per tick), the MatchRecord serialisation format, Tick width, overflow-checks in the hash-producing profile (integer overflow panics in debug and wraps in release; the fixed crate follows suit — a profile-dependent desync the hard rules do not name), whether MatchRecord gains final_hash and ticks (ARCHITECTURE's struct has neither, yet the acceptance criteria require verifying a recorded final hash and running 'to completion'), what 'bisect by tick' compares (two live instances, a replay plus a foreign hash log, or two builds), the DeterministicRng mix function, whether blindside-content joins the lint scope (it is in sim's dependency tree but outside DETERMINISM's constrained set), and explicit blessing of the feature-gated diagnostics diff as the one sanctioned ground-truth window. Also record the tick rate (Phase 1 ran 20 Hz; its 33 ms worst tick rules out 60 Hz) though it does not block Phase 0 code. The output is a decisions section in docs/HARNESS.md (BLD-39), not code. Human-gated (designer question round): expect about 5 calendar days and 1 round-trip(s) with the designer or testers beyond the 0.5 working days of work.

Done when:
- [ ] One written question list is sent to the designer on day one covering: state hasher and width; serialisation format; Tick width; overflow-checks policy; MatchRecord final_hash/ticks; bisect semantics; RNG mix function; content-crate lint scope; diagnostics-diff exception; tick rate; content-hash coverage semantics (full-pack bytes vs season-enabled entries, so BLD-26 does not foreclose the BLD-63 decision); and 'Phase 0 starts now, before the Phase 1 report and in parallel with Phase 2 — yes/no'
- [ ] Every answer is recorded verbatim and dated in docs/HARNESS.md; any unanswered question is listed as open, never defaulted silently
- [ ] Stories that consume an answer (BLD-24 RNG mix and overflow, BLD-27 hasher, BLD-28 diff blessing, BLD-30 format and fields, BLD-26 hasher, BLD-36 semantics) do not check in golden values or freeze a format before their answer is recorded
- [ ] Each open question carries the recommendation the extraction made (e.g. overflow-checks=true in release; foreign-hash-log bisect as the minimum) so the designer can answer with a yes/no

### BLD-21 — Spike: choose the determinism-lint mechanism and prove it catches the known evasions

**Status:** Backlog  ·  **Spike**  ·  P0  ·  0.5 d  ·  depends on BLD-19

**Built so far (2026-09-06, `claude/phase-0-harness`):** a token-level lint exists (`tools/determinism-lint`, commit 8ca2e22): rejects f32/f64, HashMap/HashSet, std::time, threads, rand-family and rayon dependencies, unsafe, std's keyed hashers, the common raw-pointer routes, process/env reads, `include!` and `#[path]` leaving src/, `[lib]`/`[[bin]]` path and build scripts, `package = ..` renames; 41 tests, 25 of them one evasion each. Two adversarial rounds: the first found six evasions, all closed; the second found thirteen more, of which the six it targeted are confirmed closed and the rest are stated in `--help` under WHAT THIS CANNOT SEE rather than claimed — including that its hand-written Cargo.toml reader is blinded by a `\"` escape or a BOM. It guards against an honest author's accidents; a hostile author is what review is for. Not yet: this story's fixture crate and pass/fail table in docs/HARNESS.md, the inject-desync exemption decision.

DETERMINISM.md: 'CI lint rejects any of rules 1–4 appearing in the constrained crates. Add this before writing sim code, not after.' The mechanism is unspecified. A token grep false-positives on comments and misses `Fx::from_num(0.5)`, `use std::collections::*`, type aliases and `std::collections::hash_map::HashMap` full paths; clippy `disallowed_types`/`disallowed_methods` catch resolved paths but not float literals; cargo-deny catches the `rand` dependency. This spike finds the combination that passes a known-bad fixture set and records the result, including how the BLD-35 injection fixture is exempted without weakening the lint.

Done when:
- [ ] A fixture crate outside the workspace default members contains one file per evasion: `f64` field, `f32` literal, `Fx::from_num(0.5)`, `to_num::<f32>()`, `HashMap` via full path, via glob import, via type alias, `HashSet::iter`, `Instant::now`, `SystemTime`, a `rand` dependency, `libm`, `std::thread::spawn`, `rayon`, plus a comment mentioning `f64` that must NOT fire
- [ ] The chosen mechanism is run against every fixture and the pass/fail table is recorded in docs/HARNESS.md; every evasion is caught and the comment case is not
- [ ] Decision recorded on how BLD-35's gated HashMap injection is exempted: the exemption is scoped to items under `#[cfg(feature = "inject-desync")]`, never a whole module path, with BLD-29 proving the feature is absent from every non-canary build; the record says why this does not weaken the lint elsewhere
- [ ] Decision from BLD-20 on whether blindside-content is in scope is applied to the mechanism's crate list
- [ ] The decision on whether dev-dependencies are inside the lint's dependency check is recorded (recommendation: yes, so the rand ban stays simple); BLD-25 provides the DeterministicRng-based test helpers that make that possible

### BLD-22 — Land the CI determinism lint and prove a PR adding f64 to blindside-sim goes red

**Status:** In progress  ·  **Story**  ·  P0  ·  1 d  ·  depends on BLD-19, BLD-21  ·  retires R4

**Built so far (2026-09-06, `claude/phase-0-harness`):** CI job `lint-rejects-f64` appends `pub fn bad() -> f64 { 0.0 }` to a copy of blindside-sim and passes only if the lint fails — it did (`FAIL -- 2 finding(s)`). `--check-all` rejects rand-family, rayon and libm dependencies. Not yet: required status check on main; the throwaway-branch demonstration link; the `std::fs/io/net/env` cases are covered by rule text but see BLD-21 for what the lint cannot see.

PHASE-0-HARNESS.md criterion 5: 'CI lint rejects a PR adding f64 to blindside-sim.' Scope is blindside-sim, blindside-vm and blindside-gen per DETERMINISM.md (not just 'the sim crate' as ROADMAP says) and it does not apply to the harness, client or Python phases. CLAUDE.md's definition of done from Phase 3 onward relies on CI enforcing this, so it must be a required status check. ARCHITECTURE's 'no I/O' for blindside-sim is enforced here too (std::fs/io/net/env). This story creates the first workflow file; BLD-37 extends it to the three-OS matrix.

Done when:
- [ ] A CI job runs the BLD-21 mechanism over blindside-sim, blindside-vm, blindside-gen on every push and PR and is a required status check on main
- [ ] A self-test job runs the lint against the BLD-21 bad-fixture crate and passes only if the lint FAILS, so the lint cannot silently rot
- [ ] Demonstrated: a throwaway branch adding `let x: f64 = 1.0;` to blindside-sim gets a red check; the branch/PR link is recorded in docs/HARNESS.md
- [ ] The lint does not fire on the `fixed` crate's internals or any dependency — workspace source only
- [ ] `rand`, `rand_core`, `rand_chacha`, `libm` or `rayon` as a dependency of any constrained crate fails the check
- [ ] `std::fs`, `std::io`, `std::net`, `std::env` in blindside-sim fail the check

### BLD-23 — Build the empty blindside-sim: Sim::new(&MatchRecord), step, tick, state_hash; World pub(crate)

**Status:** In progress  ·  **Story**  ·  P0  ·  0.5 d  ·  depends on BLD-19, BLD-22

**Built so far (2026-09-06, `claude/phase-0-harness`):** `Sim::new(seed)`, `step()`, `tick()`, `state_hash()` are the public surface and the harness never names `World` (it is `pub(crate)`). Differs from this story: constructed from a seed not a `&MatchRecord`; `step()` takes no commands; `World` holds two random-walking agents, not `{ tick }` alone; no `Belief` type exists.

The canary needs a real Sim to step and hash; ARCHITECTURE.md fixes world.rs as `pub(crate) struct World` and belief.rs as `pub struct Belief`, and says 'World is never passed downstream of the sensor layer.' Laying the boundary down while the sim is empty prevents the harness from becoming the leak path. No game logic: World holds `tick` and nothing else (the injection fixture in BLD-35 adds one gated field); Phase 3 fills it after the Phase 2 gate. Sim is constructible only from a MatchRecord so the replay path is the only path from day one; the MatchRecord struct and its stub member types live here because blindside-sim may depend on nothing but vm and content.

Done when:
- [ ] `Sim::new(&MatchRecord) -> Sim`, `Sim::step(&mut self, commands: &[(TeamId, Command)])`, `Sim::tick(&self) -> Tick`, `Sim::state_hash(&self) -> StateHash` are the only public entry points blindside-harness calls; no ad-hoc constructor exists
- [ ] `pub(crate) struct World { tick: Tick }` in world.rs and an empty `pub struct Belief` in belief.rs exist; blindside-harness compiles without naming World
- [ ] `MatchRecord` matches ARCHITECTURE (seed, schema, content_hash, loadouts, policies, commands) with Loadout, PolicyRef and Command as empty stub types; `Tick` and `TeamId` are newtypes whose width follows the BLD-20 answer, or carry a `// PENDING BLD-20` marker with no golden hash checked in until resolved
- [ ] step() applies this tick's commands in (team, sequence) order; the rule is in the doc comment and a test asserts commands stamped with a different tick are rejected with a typed error
- [ ] The crate root carries `#![forbid(...)]`-free but documented rules: no f32/f64, HashMap, std::time, rand, std::fs/io/net/env; the BLD-22 lint (which lands first, per DETERMINISM: add the lint before writing sim code) passes on this crate from its first commit

### BLD-24 — Add Fx, the fixed-point math module home, and stateless DeterministicRng with golden tests

**Status:** In progress  ·  **Story**  ·  P0  ·  1 d  ·  depends on BLD-19, BLD-20, BLD-22  ·  retires R4

**Built so far (2026-09-06, `claude/phase-0-harness`):** `pub type Fx = fixed::types::I32F32` defined once; `DeterministicRng::draw(tick, entity, purpose) -> Fx` is stateless SplitMix64 with order-independence, unit-interval and two pinned known-answer tests. Not yet: `fxmath` module, the 32-row golden table, mean-of-draws check, `Purpose` enum (purpose is a bare `u16`), the overflow-checks decision.

DETERMINISM.md rule 1 (`type Fx = fixed::types::I32F32`), rule 4 (RNG is counter-based and stateless: `draw(seed, tick, entity_id, purpose_id) -> Fx`, so call order cannot affect results), and the practical note that trig and sqrt come from a single module, never platform math. ARCHITECTURE's signature is `draw(&self, tick, entity: u32, purpose: u16) -> Fx` on `DeterministicRng { seed: u64 }` — immutable, with no rng field in World; ROADMAP's older `&mut` form is superseded. Phase 0 establishes the alias, the module, the RNG and the overflow policy; sqrt/trig implementations are Phase 3 work. The golden tables are what will catch R4 on a third platform, so their expected values are checked in, not computed.

Done when:
- [ ] `pub type Fx = fixed::types::I32F32;` defined exactly once in blindside-sim and re-exported; `fixed` pinned `=x.y.z` with no feature that routes through floats
- [ ] `blindside_sim::fxmath` exists with a header comment naming it the only permitted home for sqrt/sin/cos/atan2; it contains no implementations yet, and the BLD-22 lint bans `libm` and platform float math everywhere in the constrained crates
- [ ] `DeterministicRng::draw(&self, tick, entity, purpose) -> Fx` is a pure function using the mix function decided in BLD-20, written as explicit little-endian integer arithmetic with no `std::hash::Hasher`, `RandomState` or interior mutability
- [ ] Property test: 1,000 draws made in an order shuffled by the BLD-25 DeterministicRng-based permutation helper equal the same draws made in sorted order (no rand-family crate, even as a dev-dependency)
- [ ] Golden test: a checked-in table of at least 32 (seed, tick, entity, purpose) → Fx raw-bits rows, asserted equal in CI on all three OSes via BLD-37
- [ ] Output range documented as [0, 1) in Fx; a sanity test accumulates the mean of 10,000 draws in Fx and asserts it is within 0.02 of 0.5
- [ ] Workspace `[profile.release]` sets `overflow-checks` per the BLD-20 decision and a test demonstrates the chosen behaviour (panic or wrap) for an overflowing Fx multiply; the choice is recorded in docs/HARNESS.md
- [ ] `purpose` is a `#[repr(u16)] enum Purpose` owned by blindside-sim with explicit stable discriminants, extended (never renumbered) by Phase 3; the golden table uses named variants (DETERMINISM: purpose IDs are an enum with explicit stable discriminants, never derived from names or ordering)

### BLD-25 — Provide DeterministicRng-based test helpers and settle the dev-dependency lint policy

**Status:** Backlog  ·  **Task**  ·  P1  ·  0.5 d  ·  depends on BLD-24, BLD-21, BLD-22  ·  retires R4

DETERMINISM.md bans `rand` and floats in blindside-sim/vm/gen, and BLD-22 bans rand-family crates as dependencies of those crates. Several planned tests need randomness or statistics inside them: BLD-24's shuffled-order draw test and mean-of-draws sanity check, BLD-67's fixed-point golden tables 'versus a reference', BLD-120's 10,000 random bytecode programs, BLD-125's differential test. Without a decision, the first of these will either pull proptest/rand in as a dev-dependency (weakening the lint) or compute a float reference in a sim-crate test (tripping it). The RNG itself is the right source: draw() is pure, so a permutation or a random program derived from it is reproducible across platforms.

Done when:
- [ ] BLD-21's decision record states whether dev-dependencies are inside the lint's dependency check; recommendation recorded as yes, so the ban stays simple
- [ ] A `testing` module in blindside-sim (cfg(test) or a feature that BLD-29 also guards) exposes shuffle/permutation and bounded-index draws built on DeterministicRng::draw; BLD-24 and BLD-120 use it and no rand-family crate appears in any constrained crate's dependency tree
- [ ] Statistical assertions in constrained-crate tests accumulate in Fx (the mean-of-draws check is written in Fx)
- [ ] Golden reference tables (Fx arithmetic, fxmath sin/cos/atan2/sqrt) are produced by `tools/gen_fx_golden.py` or a `blindside-harness golden` subcommand where floats are permitted, and checked in as raw i64 bits with the generating command in the file header

### BLD-26 — Compute the content pack hash in blindside-content and refuse mismatching replays

**Status:** In progress  ·  **Story**  ·  P0  ·  0.5 d  ·  depends on BLD-19, BLD-20

**Built so far (2026-09-06, `claude/phase-0-harness`):** `content_hash()` exists but in blindside-harness `record.rs`, not blindside-content, and hashes `CONTENT_SCHEMA` only; `verify` refuses a record with a foreign content hash (tested). Not yet: hash over `content/**` bytes, golden constant, one-byte-change test.

DETERMINISM.md: 'Replays carry a content pack hash. Without it, replays silently produce different results after a balance change and nobody notices for months.' ARCHITECTURE rule 2: 'Content pack hash goes in every replay.' The pack is empty in Phase 0 but the field must never be a placeholder: the function, its canonical byte order and the mismatch error exist from day one. Hash the canonical bytes of the data files in sorted-path order with LF endings (BLD-19 .gitattributes), not parsed structs, so a Windows checkout does not change the hash. Whether the hash covers the full pack or only the season-enabled set is a Phase 3 content-format decision; note it here, do not decide it.

Done when:
- [ ] `blindside_content::content_hash() -> [u8; 32]` uses the 256-bit hasher decided in BLD-20 over either the canonical bytes of `content/**` in sorted relative-path order with each path's bytes included, or canonical serialised entries sorted by stable ID if BLD-20 chose season-enabled-set semantics; the choice is made in BLD-20 before this lands so switching later does not change every Phase 0 fixture's content_hash
- [ ] The empty pack's hash is a documented constant and a golden test asserts it on all three OSes via BLD-37
- [ ] Adding a one-byte file under `content/` changes the hash; a test proves it
- [ ] MatchRecord load (BLD-30) errors with both hashes printed when `content_hash` mismatches; the harness exits non-zero
- [ ] A doc comment flags the open Phase 3 question (full pack vs season-enabled set) so it is decided before the content format is frozen

### BLD-27 — Implement the per-tick state hash with an explicit coverage list and mutation tests

**Status:** In progress  ·  **Story**  ·  P0  ·  1 d  ·  depends on BLD-20, BLD-23, BLD-24  ·  retires R4

**Built so far (2026-09-06, `claude/phase-0-harness`):** BLAKE3 over a hand-written little-endian layout with a `LAYOUT_VERSION`; `debug_fields` mirrors the same fields in the same order; agents hashed in `BTreeMap` key order; hash at tick 1000 pinned and asserted on three OSes. Not yet: per-field mutation tests, the hashed/excluded field list on `World`, per-tick hash cost print.

PHASE-0-HARNESS.md: 'Hash must cover everything that can affect future ticks and nothing that cannot — including RNG call counters if any state is kept, excluding caches and derived values. Getting the hash wrong in either direction wastes weeks.' The RNG is stateless, so there are no counters today; keep it that way. Belief will be hashed in Phase 3 because policies read it. The hasher must be fixed-key and endianness-explicit: std DefaultHasher and #[derive(Hash)] over usize pass a single-machine canary and fail cross-platform. Design for growth — a hierarchical hash (per-subsystem sub-hashes) lets the BLD-28 diff localise divergence cheaply.

Done when:
- [ ] `Sim::state_hash()` returns the width decided in BLD-20, computed by serialising every hashed field as explicit little-endian bytes into the decided fixed-key hasher; grep confirms no `DefaultHasher`, `RandomState` or `#[derive(Hash)]` in blindside-sim
- [ ] A `StateHash` trait is implemented per World field; the doc comment on `World` lists every hashed field and every excluded field with the reason for exclusion (this list is mirrored in docs/HARNESS.md by BLD-39)
- [ ] Mutation test: for each hashed field, mutating it changes the hash; a deliberately added excluded cache field does not
- [ ] Hashing iterates any keyed collection in stable-ID (sorted key) order; a test inserts the same entries in two orders and gets one hash
- [ ] Golden test: the empty-sim hash at ticks 0, 1 and 10,000 is checked in and asserted on all three OSes
- [ ] The runner (BLD-31) prints per-tick hash cost; on the empty sim it is under 1 µs/tick

### BLD-28 — Expose a feature-gated, string-only structural diff of two Sims for the canary

**Status:** In progress  ·  **Story**  ·  P0  ·  0.5 d  ·  depends on BLD-20, BLD-23, BLD-27

**Built so far (2026-09-06, `claude/phase-0-harness`):** `state_debug()` (field-path dump) and `perturb_for_test()` sit behind a `test-hooks` feature that only blindside-harness enables; the canary diffs two dumps in `canary.rs`. Differs: the feature is `test-hooks` not `diagnostics`, the diff lives in the harness not the sim, and nothing yet proves `&World` is unreachable through it (BLD-32).

The canary must print more than two hashes; DETERMINISM.md: 'panic on first divergence with the tick number and a state diff.' World is pub(crate), so the diff can only be produced inside blindside-sim and exported as text — this is the one sanctioned ground-truth window for tooling and exactly the 'just for debugging' accessor CLAUDE.md warns about. It is designed to be useless as a leak: behind a `diagnostics` cargo feature, string paths and values only, never a typed &World, with the designer's blessing recorded via BLD-20.

Done when:
- [ ] `blindside_sim::diagnostics::diff(&Sim, &Sim) -> DiffReport` compiles only under `--features diagnostics`; blindside-harness enables it, the default feature set does not
- [ ] DiffReport lists every differing field path with both values (e.g. `world.tick: 41 vs 42`); identical Sims yield an empty report; unit tests cover both cases
- [ ] The API exposes no type from world.rs; the BLD-32 compile-fail test proves `&World` cannot be obtained through it
- [ ] Output order is deterministic (field-declaration then stable-ID order) so two runs produce byte-identical reports
- [ ] `diagnostics::dump(&Sim) -> String` renders the same field paths for one Sim so a state at a tick can be saved on one machine and diffed against another (used by BLD-36)
- [ ] Module header comment states it is tooling-only, names the feature flag, and links the BLD-20 decision
- [ ] Cargo features are not a privacy boundary: BLD-29's CI check asserts `diagnostics` is absent from every non-harness build's resolved feature set, and the module header says so

### BLD-29 — Guard against Cargo feature unification exposing diagnostics or inject-desync outside the harness

**Status:** Backlog  ·  **Story**  ·  P0  ·  0.5 d  ·  depends on BLD-28, BLD-22

**Built so far (2026-09-06, `claude/phase-0-harness`):** not started — and CI currently builds every step with `--workspace`, which is what this story forbids for hash-producing binaries. Feature unification is the reason `test-hooks` is not a privacy boundary today.

BLD-28 gates the structural diff and state dump behind a `diagnostics` cargo feature and BLD-35 gates the HashMap injection behind `inject-desync`, treating both as boundaries. Cargo unifies features per package across a build invocation: `cargo build --workspace` with blindside-harness enabling `blindside-sim/diagnostics` enables it for blindside-sim in every dependent compiled in that build, including blindside-client and blindside-net when they exist, so the String dump of World becomes callable from the client at compile time and the injected HashMap path can be compiled into a shipped binary. ARCHITECTURE.md: 'Make it awkward to pass ground truth.' CLAUDE.md: a leak's damage 'will not be visible for months.' This story makes the feature gates real with a CI check and a build rule.

Done when:
- [ ] blindside-sim's Cargo.toml declares `diagnostics` and `inject-desync` with `default = []`; a test asserts the default feature set is empty
- [ ] A CI step runs `cargo tree -e features -p <crate>` for blindside-sim and for every non-harness binary crate as it is added (client in Phase 4, net in Phase 6) and fails if `diagnostics` or `inject-desync` appears in the resolved set; the crate list lives in one file that BLD-115 and BLD-164 must extend
- [ ] Every hash-producing or shippable build in CI (verify, batch, golden, later release) is built with `-p <crate>`, never `--workspace`; the workflow encodes this and docs/HARNESS.md states why
- [ ] The BLD-35 injection job is the only job that enables `inject-desync`, and BLD-35's lint exemption is scoped to `#[cfg(feature = "inject-desync")]` items, not a module path
- [ ] docs/HARNESS.md records that cargo features are not a privacy boundary and names this check as the enforcement

### BLD-30 — Define MatchRecord serialisation, schema version, migration hook, and recorded final hash

**Status:** In progress  ·  **Story**  ·  P0  ·  1 d  ·  depends on BLD-20, BLD-23, BLD-27, BLD-26

**Built so far (2026-09-06, `claude/phase-0-harness`):** JSON `MatchRecord` `{schema, seed, content_hash, loadouts, policies, commands, ticks, final_hash}`; schema checked on load with a typed error; content-hash mismatch is a hard error carrying both hashes. Not yet: `migrate()` chain, sorted-commands rule, checked-in fixture, PR-template rule.

PHASE-0-HARNESS.md: 'Replay format. Seed plus input log plus content pack hash. Load, re-run, verify the final state hash matches the recorded one.' ARCHITECTURE's MatchRecord has seed, schema, content_hash, loadouts, policies and commands ('the only live input') but no final hash and no length; both are needed to verify and to run 'to completion', and are added per the BLD-20 answer. DETERMINISM: 'Policies carry a schema version with a migration path' — the same pattern applies to the record from v1 so Phase 0 replays stay loadable a year on. Fx serialises as raw bits, never through a float. DESIGN/ROADMAP: a full match is kilobytes.

Done when:
- [ ] `MatchRecord` gains the BLD-20-approved `final_hash` and `ticks` fields (or the recorded decision not to, with the alternative end rule); Loadout, PolicyRef and Command remain empty stubs
- [ ] Serialisation uses the BLD-20 format; a round-trip test proves byte-identical re-serialisation, and a golden fixture's bytes are asserted identical on all three OSes via BLD-37
- [ ] `schema: u16` is checked on load; an unknown or newer schema is a typed error; `migrate()` exists as an identity chain for v1 and a test loads a checked-in v1 fixture through it
- [ ] Commands are stored sorted by (tick, team, sequence); loading an unsorted record is a typed error (decided and tested, not implicit)
- [ ] Loading a record whose `content_hash` differs from the loaded pack's (BLD-26) is a hard error carrying both hashes, not a warning
- [ ] `fixtures/phase0-empty-10k.record` and its expected final hash are checked in; the file is under 1 KB and the size is recorded in a doc comment
- [ ] PR template (BLD-34) gains the rule: any serialised-field change bumps `schema` in the same PR

### BLD-31 — Build the blindside-harness binary: run, record and verify subcommands, hash log, throughput

**Status:** In progress  ·  **Story**  ·  P0  ·  1 d  ·  depends on BLD-23, BLD-27, BLD-30, BLD-26

**Built so far (2026-09-06, `claude/phase-0-harness`):** `run`, `record`, `verify` exist; hash log is a JSON sidecar `<stem>.hashes.json` rather than plain `tick,hash` lines; throughput is printed by `batch` (23.8M matches/hour, release, empty sim). Not yet: `--hash-every`, `--dump-state-at`, the 10 ms step-cost measurement.

PHASE-0-HARNESS.md: 'Loads a MatchRecord (seed, content hash, loadouts, policies, command log) and runs a match to completion with no renderer. Must run thousands of matches per hour on a laptop.' The harness is tooling — DETERMINISM does not apply to it, so it may use std::time for throughput and threads across matches — but it touches the sim only through the BLD-23 public API and never names World. The per-tick hash log is the input bisect (BLD-36) needs and the cheapest cross-OS diagnostic; CI uploads it in BLD-37. Phase 1's phase1/match/headless.py is the precedent, not a port.

Done when:
- [ ] `blindside-harness run <record> [--hash-log <path>] [--hash-every N] [--dump-state-at <tick>]` runs to the record's tick count with no renderer and prints final tick, final hash, wall-clock, ticks/second and hash cost per tick
- [ ] `blindside-harness record --seed S --ticks N --out <path>` writes an empty-loadout MatchRecord using BLD-30's serialisation, with final_hash filled by running it
- [ ] `blindside-harness verify <record>` re-runs and compares the final state hash to the recorded one; exits 0 on match, 1 on mismatch with both hashes printed; refuses to run on a content-hash mismatch (BLD-26)
- [ ] `--hash-log` writes one plain-text `tick,hash` line per tick (or every N) so ordinary diff tools work; default on for verify/canary, off for batch
- [ ] `cargo tree -p blindside-harness` shows no GUI, renderer or audio dependency; grep confirms the crate never names `World`
- [ ] Empty sim: 10,000 ticks complete in under 1 s; the throughput line extrapolates matches/hour at 9,600 ticks/match so the Phase 3 budget (~0.6 s/match for 1,000 matches in 10 minutes) is visible from day one
- [ ] 10,000 step() calls on the empty sim complete in under 10 ms as measured by the harness with std::time (the measurement lives here because std::time is banned in blindside-sim; no per-tick I/O or allocation churn)

### BLD-32 — Scaffold the compile-fail test that nothing outside blindside-sim can reach World

**Status:** Backlog  ·  **Story**  ·  P1  ·  0.5 d  ·  depends on BLD-23, BLD-28

ARCHITECTURE.md: 'Write a compile-time test asserting Policy::evaluate cannot reach World. It exists to catch the "just for debugging" accessor someone adds in year two.' Policy does not exist until Phase 3/4, but the harness is the first code that wants ground truth (to hash and diff), so the scaffold lands now with the variant that matters today: no crate outside blindside-sim can obtain &World, including through the diagnostics API. Phase 1's phase1/match/invariant.py (an AST walk) is the Python precedent; in Rust the mechanism is module privacy plus trybuild, not a source lint.

Done when:
- [ ] A trybuild (or `compile_fail` doctest) test in blindside-sim/tests attempts to name `blindside_sim::World` and to call a World-returning function from outside the crate; both fail to compile and the expected error snippets are checked in
- [ ] A second case attempts to reach World through `diagnostics::diff`/`dump` return types and fails to compile
- [ ] The test runs in CI on every commit on all three OSes (BLD-37)
- [ ] A doc comment in the test names the Phase 3 follow-up — add the `Policy::evaluate` and `Predicate::eval` variants when those types exist — so it is not forgotten

### BLD-33 — Build the desync canary: two Sims in lockstep, hash compared every tick, panic with diff

**Status:** In progress  ·  **Story**  ·  P0  ·  1 d  ·  depends on BLD-23, BLD-27, BLD-28, BLD-31  ·  retires R4

**Built so far (2026-09-06, `claude/phase-0-harness`):** criterion 1 met: two Sims via `Sim::new`, hash compared after every step, 10,000 ticks clean on three OSes, non-zero exit with tick, both hashes and a field diff written to `divergence.json`. Differs: built from a seed, not the record fixture this story names.

PHASE-0-HARNESS.md: 'Two Sim instances in one process, constructed from identical inputs, stepped in lockstep. State hash computed every tick and compared. On divergence: panic with the tick number, both hashes, and a structural diff of the two states.' ROADMAP calls the canary the reason the project survives. Both instances must be built through Sim::new(&MatchRecord) — the same path the runner uses — so the canary tests what ships, and both must live in ONE process: std's RandomState is randomised per instance, which is what makes the HashMap injection in BLD-35 detectable. Comparison is every tick, not only at the end.

Done when:
- [ ] `blindside-harness canary --record <fixture>` constructs two Sim instances from the same MatchRecord via Sim::new only (no special constructor exists in the crate) and compares Sim::state_hash() after every step()
- [ ] The empty-sim fixture (fixtures/phase0-empty-10k.record from BLD-30) runs 10,000 ticks with identical hashes every tick and exits 0 — PHASE-0 criterion 1
- [ ] On the first divergent tick the process exits non-zero and the message contains the tick number, both hashes, and the BLD-28 structural diff; the diff is also written to a file whose path is printed
- [ ] The canary runs in the pinned hash-producing build profile decided in BLD-20 (the same profile CI uses in BLD-37)
- [ ] Wall-clock for the 10,000-tick canary on the empty sim is printed and is under 10 s on the dev laptop, so every-tick comparison stays viable for a 9,600-tick match (Phase 1: 20 Hz × 480 s)

### BLD-34 — Add the unsafe policy and PR template for the non-lintable determinism rules

**Status:** Backlog  ·  **Task**  ·  P1  ·  0.5 d  ·  depends on BLD-19, BLD-22

DETERMINISM.md rule 8 ('Any unsafe in these crates requires written justification in the PR'), rule 5 (no threading inside a tick unless the reduction is order-independent and proven), rule 7 (IDs assigned in content data, never derived, never reused), plus the schema-bump and golden-hash update procedures are process rules a solo developer will forget. Cheapest enforcement: `#![deny(unsafe_code)]` at the crate roots (deny, not forbid, so a justified exception stays possible), a CI check that any allow carries a SAFETY comment, and a PR template checklist. CLAUDE.md: do not add process beyond what the rules require.

Done when:
- [ ] `#![deny(unsafe_code)]` at the root of blindside-sim, blindside-vm, blindside-gen
- [ ] CI step fails if an `unsafe` block or `#[allow(unsafe_code)]` in those crates lacks a `// SAFETY:` comment on the preceding line; a fixture proves both the pass and fail cases
- [ ] `.github/PULL_REQUEST_TEMPLATE.md` has checkboxes for: unsafe justification written; threading-in-tick order-independence proof attached; new stable IDs assigned in content files and not reused; `schema` bumped if a serialised format changed; golden replay hash updated deliberately with the reason stated

### BLD-35 — Inject a HashMap-iteration non-determinism and prove the canary catches it in the tick

**Status:** In progress  ·  **Story**  ·  P0  ·  1 d  ·  depends on BLD-33, BLD-21, BLD-22, BLD-29  ·  retires R4

**Built so far (2026-09-06, `claude/phase-0-harness`):** `canary --inject` perturbs instance B at tick N using a real `std::collections::HashMap` iteration order and is caught in that tick (unit test covers N = 0, 1, 250, 1000). Weaker than this story in two ways the verifier flagged: it is a same-tick state mutation of one instance, not an order-dependent update of both, so the canary is proven against a state change rather than a real order bug; and CI has no injection job. Feature is `test-hooks`, not `inject-desync`.

PHASE-0-HARNESS.md criterion 2 and its kill line: 'A canary that does not catch a known bug is worse than no canary, because it is trusted.' The fixture must live where the lint exempts it (BLD-21 decision), must mutate HASHED state (otherwise the hash correctly ignores it and the test proves nothing), and must use a real HashMap iteration so the actual failure mode is exercised: two instances in one process see different RandomState keys and therefore different iteration orders. This is permanent CI, not a one-off demo — it is re-verified after every refactor.

Done when:
- [ ] Behind `--features inject-desync` (excluded from default features, never shipped), at tick N (default 5,000) the sim folds the iteration order of a freshly built `HashMap<u64, u64>` with at least 16 entries into a hashed World field
- [ ] CI job `canary-injection` runs the BLD-33 canary with the feature on and asserts: non-zero exit, reported tick == N, non-empty diff naming the mutated field; the job is red if the canary passes
- [ ] The same job runs the canary with the feature off and asserts exit 0 for 10,000 ticks
- [ ] The BLD-22 lint still passes on the workspace with the fixture present, via the exemption decided in BLD-21: scoped to `#[cfg(feature = "inject-desync")]` items only, never a module path; BLD-29's check proves the feature is absent from every non-canary build, and docs/HARNESS.md records this as the sole sanctioned HashMap in a constrained crate
- [ ] Run 20× locally: the injection fires every time; if a run ever passes, the entry count is widened and the reason recorded in docs/HARNESS.md

### BLD-36 — Build one-command bisect: first divergent tick, both hashes, and the state diff

**Status:** In progress  ·  **Story**  ·  P0  ·  1.5 d  ·  depends on BLD-20, BLD-28, BLD-31, BLD-35  ·  retires R4

**Built so far (2026-09-06, `claude/phase-0-harness`):** criterion 4 met: `bisect <record> <hashes>` binary-searches re-runs (15 for 5,000 ticks), falls back to a linear scan for a transient mismatch, prints both hashes and the changed fields with raw bits; `--from-divergence` reproduces a canary file exactly; exit codes 0/1/2. Not yet: `diff-dumps`, checkpoint-every-N mode, the `git bisect run` example.

PHASE-0-HARNESS.md: 'One command to re-run a divergent replay, bisect by tick, and dump the state diff at the divergence point. Build this now. Building it the first time you need it, at 1am in month nine, is how projects die.' The in-process canary already finds the tick linearly; bisect earns its keep against a hash log recorded elsewhere — another OS in CI, another commit — with the semantics fixed by BLD-20. Minimum reading: binary-search the foreign log against a local re-run to the first divergent checkpoint, then step linearly to the exact tick; for the cross-machine case, diff two diagnostics dumps (BLD-28). Exit codes are `git bisect run`-compatible so bisect-by-commit works with the canary as the test.

Done when:
- [ ] `blindside-harness bisect --record <r> --hash-log <foreign.log>` re-runs the record locally, finds the first tick whose local hash differs from the log, prints tick and both hashes, writes a diagnostics dump of the local state at that tick, and exits 1
- [ ] `blindside-harness bisect --record <r> --injected` (canary in bisect mode) locates the BLD-35 injected divergence at exactly tick N with a non-empty structural diff, in one command; a CI job asserts this — PHASE-0 criterion 4
- [ ] `blindside-harness diff-dumps <a.dump> <b.dump>` prints the field-level diff of two dumps from different machines; a test diffs the two OS dumps CI produced for the injected case
- [ ] With a log recorded every N ticks, bisect narrows to the checkpoint then steps linearly to the exact tick; a test with N=100 proves it
- [ ] Exit codes 0 (no divergence), 1 (divergence), 2 (usage/error) are documented with a `git bisect run` example in docs/HARNESS.md
- [ ] Runtime on a 10,000-tick empty record is under 5 s

### BLD-37 — Run build, lint, canary, golden replay and cross-OS hash compare on Linux/macOS/Windows CI

**Status:** In progress  ·  **Story**  ·  P0  ·  2 d  ·  depends on BLD-33, BLD-31, BLD-30, BLD-22, BLD-35, BLD-29  ·  retires R4

**Built so far (2026-09-06, `claude/phase-0-harness`):** three-OS matrix green on `0051189`: build, test, lint, 10k canary, 5k record, artifacts uploaded and `cmp`-compared byte-for-byte in a fourth job; lint self-test job. Not yet: required status checks on main, nightly variant, two consecutive green commits, `-p` instead of `--workspace` (BLD-29).

PHASE-0-HARNESS.md criterion 3: 'The same replay produces identical final hashes on Linux, macOS, and Windows in CI.' DETERMINISM.md: the canary 'runs on every commit across Linux, macOS, and Windows.' No CI exists; the dev machine is Windows. This is where the 'one weekend' estimate breaks — runner quirks, line endings and macOS minutes. Required status checks are what turn CLAUDE.md's Phase 3 definition of done ('the desync canary passes on all three platforms') from something remembered into something enforced. R4 is formally answered at the Phase 3 gate; this is where it is first probed. Human-gated (three-OS CI debugging): expect about 7 calendar days and 0 round-trip(s) with the designer or testers beyond the 2 working days of work.

Done when:
- [ ] GitHub Actions matrix over ubuntu-latest, macos-latest, windows-latest using the pinned toolchain and the pinned hash-producing profile runs: cargo build, cargo test (Fx/RNG/state-hash/content-hash/serialisation golden tests), the BLD-22 lint, the BLD-33 canary on fixtures/phase0-empty-10k.record, and `verify` against the record's final_hash
- [ ] Each OS job uploads its per-tick hash log as an artifact; a final job downloads all three, diffs them, and fails naming the first divergent tick if they differ
- [ ] All jobs above plus the BLD-35 injection job and the BLD-22 lint self-test are required status checks on main; a PR cannot merge with any red
- [ ] Per-commit wall-clock for the full matrix on the empty sim is under 10 minutes; a scheduled nightly variant exists so Phase 3 can move full-length canaries there without breaking the every-commit rule
- [ ] docs/HARNESS.md documents the golden-hash update procedure: changing the checked-in final hash requires a schema bump or content-hash change in the same PR and the BLD-34 checkbox
- [ ] CI has run green on all three OSes on at least two consecutive commits
- [ ] Every hash-producing CI build (verify, canary, batch, golden) is built with `-p <crate>` and never `--workspace`, so feature unification cannot enable `diagnostics` or `inject-desync` in a hash-producing binary (BLD-29)

### BLD-38 — Add the batch executor: N seeds in parallel across matches with a seed-to-hash table

**Status:** In progress  ·  **Story**  ·  P1  ·  1 d  ·  depends on BLD-31, BLD-37  ·  retires R4

**Built so far (2026-09-06, `claude/phase-0-harness`):** `batch --matches N --ticks T` runs seeds in parallel and reports matches/hour. Not yet: `seed,final_hash` table output, the J-independence test, the CI batch diff.

ROADMAP Phase 0 lists a batch executor alongside the headless runner. Phase 3's gate ('1,000 matches run headless in under 10 minutes, bit-identical across Linux/macOS/Windows') and Phase 9's market verification are measured with it, so building it against the empty sim gives a baseline and a dry run of the gate mechanism. DETERMINISM rule 5: parallelism only between matches, never inside a tick. Phase 1's numbers imply ~9,600 ticks per match, so the Phase 3 gate is roughly 16k ticks/s aggregate — the batch runner must not be the bottleneck.

Done when:
- [ ] `blindside-harness batch --seeds A..B [--ticks N] [--jobs J] --out <table>` runs one match per seed with at most J in parallel and writes a `seed,final_hash` table sorted by seed
- [ ] Output is byte-identical for any J; a test runs J=1 and J=8 and diffs the tables
- [ ] CI (BLD-37) runs a 100-seed batch on each OS and diffs the three tables; any difference fails the build
- [ ] The throughput line reports matches/hour and aggregate ticks/s and is appended to the CI job summary so the trend is visible (not a hard gate on the empty sim)
- [ ] Empty sim: 1,000 seeds × 9,600 ticks finishes in under 60 s on the dev laptop with J=8, showing harness overhead is well inside the ~0.6 s/match Phase 3 budget

### BLD-39 — Write docs/HARNESS.md and reconcile ARCHITECTURE's MatchRecord and ROADMAP's crate names

**Status:** Backlog  ·  **Task**  ·  P1  ·  0.5 d  ·  depends on BLD-20, BLD-21, BLD-36, BLD-37

**Built so far (2026-09-06, `claude/phase-0-harness`):** `docs/HARNESS.md` does not exist; `README-phase0.md` (commit 25b3ac8) is the harness document for now. Every command in it was executed and its output pasted, then a second agent re-ran every command verbatim and compared; the lint section mirrors `--help` including the gap list. Not yet: the BLD-20 decisions (none were asked), the state-hash coverage list, ARCHITECTURE/ROADMAP reconciliation, the dependency audit.

CLAUDE.md's definition of done: 'Anything you guessed at is listed explicitly in the summary.' The BLD-20 answers, the BLD-21 lint evasion table, the state-hash coverage list, bisect semantics and the golden-hash update procedure need one home. ARCHITECTURE.md's MatchRecord gains the approved fields; ROADMAP.md's deadwater-* names get a one-line note that ARCHITECTURE wins (CLAUDE.md: renaming is a git mv, do not spend time on it). A one-line determinism audit per pinned dependency (fixed rounding, smallvec spill, SlotMap iteration order when it arrives) belongs here so an upgrade is never silent.

Done when:
- [ ] docs/HARNESS.md exists with sections: decisions (from BLD-20, dated, verbatim); lint mechanism and evasion table (BLD-21); state-hash coverage list mirroring the World doc comment (BLD-27); bisect semantics with the `git bisect run` example (BLD-36); golden-hash update procedure (BLD-37); CLI reference for every harness subcommand
- [ ] ARCHITECTURE.md MatchRecord updated with `final_hash`/`ticks` — or the recorded decision not to — and the diagnostics feature named as the sanctioned tooling exception
- [ ] ROADMAP.md gets a one-line note under Phase 0 that crate names follow ARCHITECTURE.md (blindside-*)
- [ ] Dependency audit: for each pinned external crate of sim/vm/gen, one line on its determinism properties and which golden test would catch an upgrade changing them

### BLD-40 — Verify all five Phase 0 acceptance criteria on one commit and report ready for the gate

**Status:** Backlog  ·  **Task**  ·  P0  ·  0.5 d  ·  depends on BLD-34, BLD-35, BLD-36, BLD-37, BLD-38, BLD-32, BLD-39, BLD-29, BLD-25  ·  retires R4

**Built so far (2026-09-06, `claude/phase-0-harness`):** the adversarial verifier's report plus CI run 34062222514 cover the five-criteria half of this on one commit. Not yet: the guessed-values list (BLD-20 is that list), working days recorded against the spec's one-weekend estimate, the parallel-window assertion script.

CLAUDE.md: 'Do not report a phase gate as met... Report that the build is ready for the gate.' Walk the five PHASE-0-HARNESS.md checkboxes with evidence links (CI run URLs and commit hashes on the same HEAD), list every guess made per definition-of-done item 4, and state the constraint Phase 3 inherits: no game logic in blindside-sim until the Phase 2 gate report exists. This report, together with the Phase 1 and Phase 2 gate reports, is what the Phase 3 epic's can_start_when waits on. Human-gated (readiness report read by the designer): expect about 2 calendar days and 1 round-trip(s) with the designer or testers beyond the 0.5 working days of work.

Done when:
- [ ] Each of the five criteria has a linked CI run or commit demonstrating it, all on the same HEAD commit
- [ ] The kill criterion (injected non-determinism caught in-tick, BLD-35) is demonstrated by a CI run within the last 7 days, not a historical one
- [ ] The report lists every guessed value and every BLD-20 question still open
- [ ] The report says 'ready for the Phase 0 gate', never 'gate met'; PHASE-0-HARNESS.md checkboxes are ticked only with the evidence link beside each
- [ ] Actual working days and calendar span are recorded against the spec's '1 weekend' estimate so ROADMAP's floor estimates can be recalibrated before Phase 3 is scheduled
- [ ] At readiness a script asserts the parallel-window constraint held: World contains only `tick`, fxmath contains no implementations, Belief is empty, and blindside-sim/gen/content contain no sensor, belief or generation code; BLD-66 re-runs the same script before the first Phase 3 commit

## BLD-41 — Junction Test: demonstration → legible policy (throwaway Python)

**Phase Phase 2 — Junction Test.** Answer risks R2 (can demonstration produce a legible policy), R3 (can a player self-diagnose a failure from the replay) and R5 (is a 3-predicate vocabulary the right size) for the price of a few weekends of throwaway Python, before any Rust sim-core code is written. Scope is exactly ROADMAP.md Phase 2: branching corridor (8 junctions, deposit at a random leaf), 3 predicates, 2 actions, belief+input trace recording, changepoint segmentation, minimal-separator induction with threshold fitting, tree + one-sentence rendering, ghost replay, correction loop, active-learning query, and an unseen-seed evaluator. No abstraction layers, config systems or test suites beyond what the gate needs (CLAUDE.md). Human-gated stories in this epic: 8 of 18 (1 designer decisions or reviews, 7 playtests or self-tests, 0 art, toolchain, CI or commercial), carrying at least 22 calendar days of latency on top of 20.5 working days.

- **Gate — pass:** All four ROADMAP.md Phase 2 criteria observed and recorded: (1) 3 demonstrations → ≥70% success on unseen seeds, measured by the headless evaluator; (2) the player reads the inferred rule and correctly predicts the next junction choice on a fresh seed; (3) on a failure, the player names the wrong rule unprompted from the replay; (4) a correction (scrub, enter body, drive, promote) takes under 60 seconds end to end, wall-clock measured. Reported as 'ready for gate / observed', never 'gate met' (CLAUDE.md).
- **Gate — kill:** Criterion 3 is the real one. If the player cannot self-diagnose from the replay, the forensics layer — the emotional core of the game — does not work: stop, report, and do not start Phase 3 sim-core work (Phase 0 harness tooling may continue since it has no game logic). Also stop if honest designer demonstrations yield no consistent separator over the three predicates and the active-learning query cannot resolve it — that is R2/R5 failing, and it is to be flagged as a design problem, not worked around.
- **Can start when:** The Phase 1 gate playtest has been run with a non-designer and its report classifies the player as engaged (talks to the screen, wrong theory corrected, tension at Recall) rather than bored — i.e. the Phase 1 group's final playtest-report story is done. Runs in parallel with the P0 harness epic; nothing here depends on P0 and nothing in P0 depends on this. Phase 3 stays blocked until this epic's gate report exists.
- **Estimate:** 20.5 working days

| Key | Type | Summary | Pri | Days | Depends on | Risk |
|---|---|---|---|---|---|---|
| BLD-42 | Spike | Settle the load-bearing Phase 2 unknowns with the designer before writing code | P0 | 1 | BLD-16 | R2, R5 |
| BLD-43 | Story | Build the seeded 8-junction branching corridor with a deposit at a random leaf | P0 | 1.5 | BLD-42 | — |
| BLD-44 | Story | Implement the corridor Belief: drifting pose, believed junction graph, cargo self-report | P0 | 1.5 | BLD-42, BLD-43 | R3 |
| BLD-45 | Story | Implement the three predicates over Belief with θ as a fitted parameter | P0 | 0.5 | BLD-44 | R5 |
| BLD-46 | Story | Implement take_branch and return_to_beacon as motor programs shared by demo and policy | P0 | 1 | BLD-44 | — |
| BLD-47 | Story | Build the unseen-seed batch evaluator and establish the success ceiling | P0 | 1 | BLD-43, BLD-46 | R2 |
| BLD-48 | Story | Build demonstration mode: player drives on a belief-only view and traces are recorded | P0 | 2 | BLD-43, BLD-44, BLD-45, BLD-46 | R2 |
| BLD-49 | Story | Segment demonstration traces at behavior changepoints | P0 | 1.5 | BLD-48 | R2 |
| BLD-50 | Story | Induce the minimal-separator rule over the 3 predicates and fit θ; report no-separator | P0 | 2 | BLD-45, BLD-49 | R2, R5 |
| BLD-51 | Story | Render the inferred policy as a behavior tree and as one plain sentence | P0 | 1 | BLD-50 | R2 |
| BLD-52 | Task | Write the Phase 2 playtest protocol and scoring sheet before the session | P0 | 0.5 | BLD-51 | R3 |
| BLD-53 | Story | Run the inferred policy as a ghost beside the demonstration and mark the divergence | P0 | 1 | BLD-48, BLD-50, BLD-51 | R3 |
| BLD-54 | Story | Build the correction loop: scrub, enter body, drive correction, promote, re-induce | P0 | 1.5 | BLD-53 | R3 |
| BLD-55 | Story | Ask the player an active-learning query when no consistent separator exists | P1 | 1 | BLD-50, BLD-51, BLD-48 | R5 |
| BLD-56 | Story | Measure 3 demos → success rate on unseen seeds and record the number | P0 | 1 | BLD-47, BLD-50, BLD-55 | R2 |
| BLD-57 | Task | Record candidate predicates observed during demos without adding them | P3 | 0.5 | BLD-56 | R5 |
| BLD-58 | Task | Self-test the full loop end to end and fix blockers before the external playtest | P0 | 1 | BLD-54, BLD-56, BLD-52 | R2, R3 |
| BLD-59 | Story | Run the Phase 2 gate playtest with a non-designer and write the readiness report | P0 | 1 | BLD-58 | R2, R3, R5 |

### BLD-42 — Settle the load-bearing Phase 2 unknowns with the designer before writing code

**Status:** Backlog  ·  **Spike**  ·  P0  ·  1 d  ·  depends on BLD-16  ·  retires R2, R5

ROADMAP.md Phase 2 names the pieces but is silent on several things that change every later story, and CLAUDE.md says ask rather than invent. PHASE-1-OPEN-QUESTIONS.md was never answered inline and the code chose instead; do not repeat that — write a short docs/PHASE-2-OPEN-QUESTIONS.md and get inline answers before BLD-43 starts. This story depends on BLD-16 so the board cannot show Phase 2 as startable before the Phase 1 report exists (CLAUDE.md: Phase 2 is blocked on 1). Questions: (a) demonstration input granularity — junction-level choice (agent auto-travels, pauses at each believed junction and waits for take_branch/return_to_beacon) versus continuous steering as DESIGN's 'drive it in its body' implies; junction-level keeps traces discrete and induction tractable, continuous makes changepoint segmentation a real problem; (b) what produces uncertainty here — reuse Phase 1's heading-bias odometry drift and sigma_pos() with the shaft beacon as the only fix, or a scalar that grows per cell travelled; (c) scope of unexplored_branch_exists (current junction only vs anywhere in the believed graph) and the parameter of take_branch (nearest unexplored, left-most, index); (d) the success definition for the ≥70% criterion and the per-run tick budget; (e) whether branches are visible in belief before arrival (which Phase 1 sensor kit, if any) ; (f) whether promotion appends the corrected run as a fourth demonstration or replaces the failed run's suffix; (g) whether drift must be large enough that return_to_beacon can fail, so uncertainty > θ has teeth and there are failures to diagnose. Human-gated (designer question round): expect about 5 calendar days and 1 round-trip(s) with the designer or testers beyond the 1 working days of work.

Done when:
- [ ] docs/PHASE-2-OPEN-QUESTIONS.md exists with each question answered inline by the designer, or explicitly marked 'implementer's call' with the chosen default
- [ ] The input-granularity decision (a) is recorded with its consequence for BLD-48 and BLD-49 estimates
- [ ] The success definition (d) is written as one sentence that BLD-47 implements verbatim
- [ ] Anything left unanswered is listed as a guess in the story's closing note (CLAUDE.md definition of done)

### BLD-43 — Build the seeded 8-junction branching corridor with a deposit at a random leaf

**Status:** Backlog  ·  **Story**  ·  P0  ·  1.5 d  ·  depends on BLD-42

ROADMAP.md Phase 2: 'Branching corridor, 8 junctions, one deposit at a random leaf'. The induction test needs many unseen instances of the same structure, so unlike Phase 1's hand-authored cave this world is generated from a seed. Build a phase2/ package alongside phase1/ with a truth world (corridor tree rasterised to a small grid, or a pure graph if BLD-42 chose junction-level input), a Sim step loop borrowed from phase1/match/sim.py, and a headless CLI in the phase1/match/headless.py pattern. Extend phase1/match/invariant.py's AST walk to phase2's belief/ and policy/ packages so the truth/belief split is enforced from the first commit. Throwaway: no generator abstraction, no config file.

Done when:
- [ ] `python -m phase2 --seed N --headless` runs a corridor from seed N to the tick budget and prints the junction tree and which leaf holds the deposit
- [ ] Every seed in 0..999 yields exactly 8 junctions and a deposit reachable from the shaft beacon (checked by a one-line loop, not a test suite)
- [ ] Same seed produces the identical corridor and identical headless timeline on two runs
- [ ] `python -m phase2 --invariant` passes: phase2 belief/ and policy/ import nothing from truth/
- [ ] Runs in the pinned phase1 Python environment with no new dependencies

### BLD-44 — Implement the corridor Belief: drifting pose, believed junction graph, cargo self-report

**Status:** Backlog  ·  **Story**  ·  P0  ·  1.5 d  ·  depends on BLD-42, BLD-43  ·  retires R3

Policies, predicates and the display see Belief only (CLAUDE.md invariant). The corridor Belief needs exactly what the three predicates and two actions consume: a pose estimate whose uncertainty grows with travel and collapses on a shaft-beacon fix (per BLD-42 (b), reusing phase1/belief's sigma_pos() and odometry integration where cheap), a believed junction graph with per-branch explored flags built from sensor returns, and cargo learned through a self-report return as Phase 1 did (phase1/sensing/returns/cargo.py). Sensor layer is one module that reads both World and Belief and emits returns; nothing else reads World. Keep it small — this is not Phase 3's BeliefUpdater.

Done when:
- [ ] Belief exposes uncertainty (scalar), unexplored branch set, current believed junction and cargo count, all derived from returns only
- [ ] Uncertainty grows monotonically between fixes and drops on a shaft-beacon fix; headless timeline shows true position error and sigma side by side for tuning (truth lines never reach the display)
- [ ] With drift tuned per BLD-42 (g), a return_to_beacon started from the deepest leaf fails to reach the shaft on some seeds (records 'lost') — there are failures to diagnose
- [ ] Sensor module is the only phase2 module importing both truth and belief; invariant check still passes

### BLD-45 — Implement the three predicates over Belief with θ as a fitted parameter

**Status:** Backlog  ·  **Story**  ·  P0  ·  0.5 d  ·  depends on BLD-44  ·  retires R5

ROADMAP.md Phase 2: '3 predicates: unexplored_branch_exists, uncertainty > θ, carrying_cargo'. R5 asks whether this vocabulary is the right size, so exactly three are built — any further predicate the demos seem to need is written down as a candidate (BLD-57), not added. Each is a pure function of Belief plus a parameter list, mirroring ARCHITECTURE.md's Predicate::eval(&Belief, params) shape so the Phase 4 port is a translation. θ is a parameter supplied by induction (BLD-50), never a constant.

Done when:
- [ ] Three functions taking (Belief, params) and returning bool; uncertainty > θ reads θ from params
- [ ] `python -m phase2 --predicates --seed N` prints the three values per decision point for a scripted run, and the invariant check passes
- [ ] No predicate imports or receives anything from truth/
- [ ] Exactly three predicates exist in the module; a comment points to BLD-57 for candidates

### BLD-46 — Implement take_branch and return_to_beacon as motor programs shared by demo and policy

**Status:** Backlog  ·  **Story**  ·  P0  ·  1 d  ·  depends on BLD-44

ROADMAP.md Phase 2: '2 actions: take_branch, return_to_beacon'. Both the player's demonstration and the inferred policy must produce the same movement from the same action, or the ghost replay (BLD-53) compares different things. Each action is a motor program over Belief (drive along the believed corridor to the chosen branch / drive back toward the believed shaft beacon), issuing MotorCommands to the truth world exactly as phase1/policy/policy.py does. take_branch's parameter semantics follow BLD-42 (c).

Done when:
- [ ] A hand-written 'intended' policy (carrying_cargo → return; uncertainty > θ → return; unexplored_branch_exists → take_branch; else return) runs headless end to end using only the two actions
- [ ] return_to_beacon can be run from any junction and either reaches the shaft (fix, 'home') or logs 'lost' when drift exceeds the acquisition radius
- [ ] The same action called with the same Belief state produces the same MotorCommand sequence whether invoked by the player or by a policy
- [ ] Exactly two actions exist

### BLD-47 — Build the unseen-seed batch evaluator and establish the success ceiling

**Status:** Backlog  ·  **Story**  ·  P0  ·  1 d  ·  depends on BLD-43, BLD-46  ·  retires R2

Gate criterion 1 is quantitative ('3 demonstrations → ≥70% success on unseen seeds') and needs a headless runner over many seeds in the phase1/match/headless.py pattern. Success is the one-sentence definition from BLD-42 (d) (expected: reach the deposit, load, and return to the shaft beacon with cargo within the tick budget). Run the hand-written intended policy from BLD-46 and a random-branch baseline across the seed range first: if the intended policy cannot clear 70% the environment is unsolvable and the gate would measure the wrong thing.

Done when:
- [ ] `python -m phase2 eval --policy <file> --seeds 1000..1199` prints success rate, mean ticks, and a failure-reason histogram (lost / timeout / returned empty)
- [ ] The success definition is written in docs/PHASE-2-OPEN-QUESTIONS.md and implemented verbatim
- [ ] The hand-written intended policy scores ≥85% on 200 unseen seeds and the random-branch baseline scores well below 70%; both numbers recorded in the doc
- [ ] 200 seeds evaluate in under one minute on the dev laptop

### BLD-48 — Build demonstration mode: player drives on a belief-only view and traces are recorded

**Status:** Backlog  ·  **Story**  ·  P0  ·  2 d  ·  depends on BLD-43, BLD-44, BLD-45, BLD-46  ·  retires R2

ROADMAP.md Phase 2: 'Record belief + input traces during player-driven demonstration'. This is a new input surface — Phase 1 forbids driving — so it is a separate mode, not a change to phase1. The player sees Belief only (believed corridor, uncertainty, cargo, current junction); at each decision point (per BLD-42 (a)) they choose take_branch(k) or return_to_beacon. Every decision records a trace row: tick, the three predicate values, the raw belief features they came from (unexplored count, sigma, cargo), and the input. Traces are JSON files that a headless replay can re-run from the seed to the same outcome. The view can be a minimal 2D vispy scene; do not port phase1/view's panels wholesale. Human-gated (designer records the demonstrations): expect about 2 calendar days and 1 round-trip(s) with the designer or testers beyond the 2 working days of work.

Done when:
- [ ] `python -m phase2 demo --seed N` opens a window; the player completes a run and a trace JSON is written with one row per decision point containing tick, predicate values, raw features, action and parameter, and — whenever the corridor Belief takes a shaft-beacon fix — the fix jump and surprise (jump / sigma_before), the only belief-legal spoof tell from Phase 1, so BLD-57 has trace data to evaluate
- [ ] `python -m phase2 replay trace.json` re-runs the trace headless from its seed and reproduces the same decision sequence and outcome
- [ ] No ground truth is drawn during the demonstration; a post-run reveal of truth over belief is allowed (DESIGN: replay is one of the two places truth appears)
- [ ] Three demonstrations by the designer on three seeds take under 10 minutes total to record

### BLD-49 — Segment demonstration traces at behavior changepoints

**Status:** Backlog  ·  **Story**  ·  P0  ·  1.5 d  ·  depends on BLD-48  ·  retires R2

ROADMAP.md Phase 2: 'Changepoint segmentation, minimal-separator predicate induction, threshold fitting' — this is the first stage. A changepoint is where the player's behavior switched; with junction-level input (BLD-42 (a)) a segment is a maximal run of the same action and the boundary carries the belief at the switch, which is nearly trivial. If continuous steering was chosen, this becomes a real signal-segmentation problem (mode changes in heading relative to the believed goal) and should be re-scoped as a spike before building. CLAUDE.md names demonstration-to-policy induction a known-weak area: if honest demos produce boundaries that do not line up with anything in Belief, say so rather than force it.

Done when:
- [ ] `python -m phase2 segment trace.json` prints the segments with their start/end ticks, the action in each, and the predicate values at every boundary
- [ ] Boundaries are inspectable in the demo view as markers on the run's timeline
- [ ] On the designer's three demos, every boundary coincides with a decision point at which the action changed (junction-level), or the segmentation report explains each boundary (continuous)
- [ ] If continuous input was chosen, a written note on whether segmentation is reliable enough to feed induction, before BLD-50 starts

### BLD-50 — Induce the minimal-separator rule over the 3 predicates and fit θ; report no-separator

**Status:** Backlog  ·  **Story**  ·  P0  ·  2 d  ·  depends on BLD-45, BLD-49  ·  retires R2, R5

Second and third induction stages from ROADMAP.md Phase 2. For each action, find the smallest conjunction of literals over the three predicates that covers every decision point labeled with that action across all demonstrations and none labeled with the other; with three predicates this is a brute-force search over eight cells, so the interesting outcome is whether the demos are consistent with any rule at all. θ is fitted from the sorted uncertainty values at decision points: the midpoint of the largest gap that makes the labeling consistent, reported alongside the rule. When no consistent separator exists, return an explicit NoSeparator result listing the conflicting decision points (identical predicate values, different actions) — this feeds BLD-55. Output is an ordered decision list convertible to a Selector-of-Guards tree in ARCHITECTURE.md's BtNode shape.

Done when:
- [ ] `python -m phase2 induce demo1.json demo2.json demo3.json` prints the rule as an ordered list of (conjunction → action) and the fitted θ
- [ ] Induced from three intended-policy traces generated headless, the rule reproduces the intended policy exactly and θ lies between the demos' return and take_branch uncertainty values
- [ ] Given two demos that conflict on a cell, the output is NoSeparator with the conflicting rows listed, not a guessed rule
- [ ] Given demos that never visit a predicate cell, the rule states which cells are uncovered (input to BLD-55)
- [ ] Induction on three demos runs in under one second

### BLD-51 — Render the inferred policy as a behavior tree and as one plain sentence

**Status:** Backlog  ·  **Story**  ·  P0  ·  1 d  ·  depends on BLD-50  ·  retires R2

ROADMAP.md Phase 2: 'Render the inferred policy as a behavior tree and as one plain sentence'. Gate criterion 2 requires the player to read the rule and predict the next junction choice, so legibility is the whole point (R2). Phase 1's phase1/policy/decision_node.py DecisionNode and phase1/view/decision_graph.py (guards with fill bars toward their threshold) were built as a rehearsal for this and are the starting point: reuse them rather than designing a new tree widget. The sentence is generated from the same structure as the tree so they cannot disagree, e.g. 'Return to the beacon when carrying cargo or when uncertainty is above 14; otherwise take an unexplored branch.' Human-gated (designer prediction dry run): expect about 1 calendar days and 1 round-trip(s) with the designer or testers beyond the 1 working days of work.

Done when:
- [ ] The induced rule renders as a tree with one guard node per literal and one action leaf per branch, with live predicate values and the uncertainty fill bar against the fitted θ when attached to a running belief
- [ ] A single English sentence is generated from the same rule object and shown beside the tree; changing the rule changes both
- [ ] The designer, reading only the sentence, predicts the intended policy's choice at five junctions on a fresh seed with five correct (dry run of gate criterion 2)
- [ ] NoSeparator renders as a plain statement of which situations conflict, not as a partial tree

### BLD-52 — Write the Phase 2 playtest protocol and scoring sheet before the session

**Status:** Backlog  ·  **Task**  ·  P0  ·  0.5 d  ·  depends on BLD-51  ·  retires R3

Gate criteria 2–4 are observed, not computed, and criterion 3 requires the player to name the wrong rule unprompted — so the observer must know in advance what counts as a prompt. Write docs/PHASE-2-PLAYTEST.md: the script the player is told (the task, nothing about rules), the three-demonstration recording, the prediction test (player reads the sentence and tree, then predicts the choice at at least three junctions on a fresh seed; predicted vs actual logged), the failure replay (the evaluator supplies a seed where the induced rule fails; the ghost replay is shown with no commentary; verbatim record of what the player says and whether they name the wrong rule before any question is asked), and the timed correction. Include the scoring sheet and the Phase 1 lesson that reports state readiness, never 'gate met'.

Done when:
- [ ] docs/PHASE-2-PLAYTEST.md contains the player script, the observer script with an explicit definition of 'prompted', and a one-page scoring sheet for all four criteria
- [ ] The failure-replay step specifies how the failing seed is chosen (from BLD-47's failure list, not hand-picked to be obvious)
- [ ] The sheet has a field for the wall-clock correction time as logged by BLD-54, not estimated

### BLD-53 — Run the inferred policy as a ghost beside the demonstration and mark the divergence

**Status:** Backlog  ·  **Story**  ·  P0  ·  1 d  ·  depends on BLD-48, BLD-50, BLD-51  ·  retires R3

ROADMAP.md Phase 2: 'Ghost replay: inferred policy runs alongside the demonstration'. The ghost is the inferred policy run headless from the demonstration's seed; its path is drawn over the demonstration's path in the same belief-space view, with a scrubbable timeline. The first decision point where the ghost's action differs from the player's is the divergence and is marked on the timeline and the map. Because this is a replay, truth may be revealed underneath both paths after the run (DESIGN), which is what lets a player see where the rule went wrong relative to where the machine actually was. This is the screen gate criterion 3 is observed on.

Done when:
- [ ] `python -m phase2 ghost trace.json rule.json` shows demonstration and ghost paths in distinct colours with a scrubber; the tree from BLD-51 lights the fired branch as the scrubber moves
- [ ] The first divergent decision is marked on the timeline and the map; when the ghost never diverges the view says so
- [ ] Scrubbing to any tick shows the belief the ghost acted on at that tick (predicate values, uncertainty, cargo)
- [ ] Truth overlay is available only after the run has completed and is off by default

### BLD-54 — Build the correction loop: scrub, enter body, drive correction, promote, re-induce

**Status:** Backlog  ·  **Story**  ·  P0  ·  1.5 d  ·  depends on BLD-53  ·  retires R3

ROADMAP.md Phase 2: 'Correction loop: scrub, enter body, drive correction, promote'; gate criterion 4 requires the whole loop under 60 seconds end to end, and DESIGN describes rewinding and dropping into the body as the teaching mechanism. From the ghost replay the player scrubs to a decision point, takes control from the ghost's belief state at that tick, drives the remainder (or a few decisions), and promotes: the corrected run becomes a trace (appended as a fourth demonstration or replacing the failed suffix, per BLD-42 (f)), induction re-runs, and the updated tree and sentence render. The loop is timed from the first scrub input to the new rule being on screen and the time is written into the trace directory so the gate has a number, not an impression. Human-gated (designer timed correction): expect about 1 calendar days and 1 round-trip(s) with the designer or testers beyond the 1.5 working days of work.

Done when:
- [ ] From the ghost view, one key scrubs, one key enters the body at the current decision, the player drives with the same controls as BLD-48, and one key promotes
- [ ] Promotion writes the corrected trace, re-runs induction, and re-renders the tree and sentence without restarting the program
- [ ] Elapsed wall-clock from first scrub to updated rule is logged per correction and displayed after promotion
- [ ] The designer performs a correction on a seed where the induced rule fails and the logged time is under 60 seconds

### BLD-55 — Ask the player an active-learning query when no consistent separator exists

**Status:** Backlog  ·  **Story**  ·  P1  ·  1 d  ·  depends on BLD-50, BLD-51, BLD-48  ·  retires R5

ROADMAP.md Phase 2: 'Active-learning query when no consistent separator is found'. When BLD-50 returns NoSeparator (or reports uncovered predicate cells), the system constructs a belief situation in that cell — either by synthesising the belief directly and showing it in the demo view, or by finding a seed and decision point where the cell holds — and asks the player which of the two actions they would take. The answer becomes a labeled trace row and induction re-runs. This is the fallback that keeps three demonstrations sufficient; if honest demos routinely need many queries, that is R5 evidence to record.

Done when:
- [ ] After induction returns NoSeparator, the demo view presents the conflicting situation (predicate values, uncertainty, cargo, believed corridor) and a two-button question
- [ ] Answering writes a one-row trace tagged 'query' and triggers re-induction; the updated rule renders
- [ ] A deliberately ambiguous demo pair (same cell, different actions) is resolved to a consistent rule after one answer
- [ ] The number of queries needed for the designer's real three demos is recorded in the playtest notes

### BLD-56 — Measure 3 demos → success rate on unseen seeds and record the number

**Status:** Backlog  ·  **Story**  ·  P0  ·  1 d  ·  depends on BLD-47, BLD-50, BLD-55  ·  retires R2

Gate criterion 1 end to end: take the designer's three real demonstrations, induce (BLD-50), evaluate on unseen seeds (BLD-47), and write the number down. Also run a deliberately sloppy demo set (one inconsistent choice) to see how brittle the pipeline is, and a set recorded with a different θ in mind, so the gate playtest is not the first time robustness is observed. Do not tune the world to make the number pass; if the intended policy clears the ceiling (BLD-47) but induced rules do not, that is R2 information. Human-gated (designer's real demonstrations evaluated): expect about 2 calendar days and 1 round-trip(s) with the designer or testers beyond the 1 working days of work.

Done when:
- [ ] `python -m phase2 induce demos/*.json --eval 1000..1199` prints the induced rule, θ, and the success rate on 200 seeds not used in any demonstration
- [ ] Designer's three real demos yield a rule whose success rate is recorded in docs/PHASE-2-OPEN-QUESTIONS.md next to the intended-policy ceiling
- [ ] The sloppy demo set's outcome (NoSeparator, query needed, or degraded rate) is recorded
- [ ] No tuning constant is changed to reach 70%; any change to the world after this run is listed with its reason

### BLD-57 — Record candidate predicates observed during demos without adding them

**Status:** Backlog  ·  **Task**  ·  P3  ·  0.5 d  ·  depends on BLD-56  ·  retires R5

R5 asks whether three predicates is the right size; the honest evidence is which extra tests the player reached for while demonstrating (e.g. 'is this branch a dead end', 'how deep am I') and Phase 1's belief-legal spoof tell, fix surprise (jump / sigma_before, phase1/belief/fix_record.py), which tuning.py notes is a skill Phase 2 would be where it is learned. Write them into a short candidates section of docs/PHASE-2-OPEN-QUESTIONS.md with the situation that prompted each. Include the panel finding from PHASE-1-OPEN-QUESTIONS Part 4 that in Phase 1 'do I ping' is a cooldown rather than a decision because no policy reads contacts, so contact-reading predicates ('contact heard within N s', 'best contact quality >= theta') are candidates the Phase 3 vocabulary must consider. Nothing is implemented; the three-predicate gate stays as written. Human-gated (designer and tester wishes recorded): expect about 1 calendar days and 1 round-trip(s) with the designer or testers beyond the 0.5 working days of work.

Done when:
- [ ] A 'candidate vocabulary' section lists each predicate the designer or playtester wished for, with the demo and decision point that prompted it
- [ ] Fix surprise is listed with a one-paragraph note on whether it belongs in the Phase 3/4 predicate library
- [ ] The predicate module still contains exactly three predicates
- [ ] The contact-reading candidates ('contact heard within N s', 'best contact quality >= theta') are listed with the Part 4 note that without one of them pinging is a cooldown, not a decision, and the fix-surprise values recorded in the BLD-48 traces are cited

### BLD-58 — Self-test the full loop end to end and fix blockers before the external playtest

**Status:** Backlog  ·  **Task**  ·  P0  ·  1 d  ·  depends on BLD-54, BLD-56, BLD-52  ·  retires R2, R3

Phase 1's lesson (PHASE-1-SPECTATOR-TEST.md: 'test it alone first') applies. The designer runs the complete protocol from BLD-52 on themselves: record three demos, read the rule, predict five junctions, watch a failing seed's ghost replay, perform a timed correction, and answer any active-learning query. Fix anything that crashes or stalls (Phase 1's SEARCH-mode crash surfaced only at the one beat that mattered). Record the designer's own numbers so the external session has a baseline. Human-gated (designer self-test of the full loop): expect about 3 calendar days and 1 round-trip(s) with the designer or testers beyond the 1 working days of work.

Done when:
- [ ] The whole protocol runs start to finish on the current commit without a crash or manual intervention
- [ ] Designer's own results for all four criteria are recorded on a scoring sheet, including the induced success rate and the logged correction time
- [ ] Every blocker found is fixed in its own small commit before BLD-59 is scheduled
- [ ] A list of everything guessed at during Phase 2 is written up (CLAUDE.md definition of done)

### BLD-59 — Run the Phase 2 gate playtest with a non-designer and write the readiness report

**Status:** Backlog  ·  **Story**  ·  P0  ·  1 d  ·  depends on BLD-58  ·  retires R2, R3, R5

The gate involves a human and cannot be declared met by the build (CLAUDE.md). Put a non-designer through docs/PHASE-2-PLAYTEST.md: they record three demonstrations, the pipeline induces a rule, they predict junction choices from the rendered rule, they watch a failing seed's ghost replay with no commentary, and they perform a timed correction. The report records the four criteria with evidence (success rate from the evaluator, predictions logged vs actual, verbatim words at the failure replay and whether the wrong rule was named before any prompt, logged correction time), plus every guess made in this phase. If criterion 3 fails, the report says so plainly and Phase 3 sim-core work does not start; Phase 0 tooling may continue. Human-gated (external playtest with a non-designer): expect about 7 calendar days and 1 round-trip(s) with the designer or testers beyond the 1 working days of work.

Done when:
- [ ] A non-designer completed the protocol and a report in docs/ records evidence for each of the four criteria, including verbatim quotes at the failure replay
- [ ] The report states readiness ('ready for gate' / observed outcomes) and never 'gate met'
- [ ] If criterion 3 was not observed, the report classifies why (rule not legible, replay not legible, failure not attributable) and recommends stop/redesign rather than a workaround
- [ ] The report links the trace files, induced rule, evaluator output and correction timing log for that session, kept outside git if large
- [ ] The list of guesses from BLD-58 is included and any that the playtest contradicted are flagged for the designer

## BLD-60 — Phase 3 — Sim core in Rust

**Phase Phase 3 — Sim core.** Build blindside-sim, blindside-gen and blindside-content for real: World/Belief boundary enforced at the crate level with a compile-fail test, fixed-point math, stateless RNG, the request-shaped Sensor trait and every Phase 3 sensor returning Return values, the BeliefUpdater fusion stack carrying Phase 1's measured lessons (back-propagating fixes, position-only beacon fixes, terrain-relative heading recovery, bearing-only tracking), a range-bounded AcousticField, generated caves with the eight world axes, one ancient system, MatchRecord-driven Extraction matches, and hardware-ready sensor/actuator seams. Answer risk R4 by running 1,000 headless matches bit-identically on three platforms. ROADMAP estimates 3–5 months; the honest nights-and-weekends total below is larger and should be read as a floor. Four findings from the 2026-09-06 design panel are folded into existing stories rather than added as new ones: typed emission channels (BLD-74, BLD-85), a cluster tracker so lidar can see agents (BLD-89), ancients as a behaviour source with a yields() seam (BLD-103), and risk R9 (BLD-108). Seven stories were added after review: the gate-entry anchor (BLD-66), record-assigned entity IDs (BLD-69), the spoof module and Belief-only action (BLD-106), map-aware steering with the Phase 1 give-up timing (BLD-101), gait (BLD-100), transient silt (BLD-96) and the chassis-class decision (BLD-65). Human-gated stories in this epic: 14 of 52 (11 designer decisions or reviews, 0 playtests or self-tests, 3 art, toolchain, CI or commercial), carrying at least 70 calendar days of latency on top of 116.25 working days.

- **Gate — pass:** 1,000 matches run headless in under 10 minutes on a laptop, bit-identical (seed→final-hash table diff empty) across Linux, macOS and Windows in CI, with every task's canary green on all three platforms and every guessed value listed. Report 'ready for the Phase 3 gate'; the designer confirms.
- **Gate — kill:** R4 answered here. If final hashes differ across platforms after bisect-and-fix, or 1,000 matches cannot fit 10 minutes after profiling without threading inside a tick, stop and report: no replays, no market verification, no server authority — Phase 4 and the client do not start.
- **Can start when:** BLD-66 is the gate-entry anchor and encodes CLAUDE.md's 'blocked on 1, 2, 0' in depends_on: the Phase 1 decision record (BLD-17, carrying the BLD-16 playtest report — the designer's read of the observations, never 'gate met'), the Phase 2 gate report (BLD-59) with all four criteria recorded, and the Phase 0 readiness report (BLD-40) with all five PHASE-0-HARNESS acceptance criteria green in CI. Every Phase 3 story that touches blindside-sim/gen/content/harness depends on BLD-66. Judgment call, flagged to the designer: spikes BLD-61 to BLD-64 and BLD-65 are question rounds and a scratch prototype outside the workspace, so they may run while Phase 2 is in progress; no game logic is committed to blindside-sim before BLD-66 confirms the reports and re-runs the empty-sim assertion.
- **Estimate:** 116.25 working days

| Key | Type | Summary | Pri | Days | Depends on | Risk |
|---|---|---|---|---|---|---|
| BLD-61 | Spike | Reconcile ARCHITECTURE core types with Phase 1 findings before writing sim code | P0 | 3 | BLD-16 | R4 |
| BLD-62 | Spike | Decide what drives agents in Phase 3 before the Phase 4 VM exists | P0 | 1 | BLD-61 | — |
| BLD-63 | Spike | Fix the Phase 3 sensor set, module list, content format and permanent content IDs | P0 | 2 | BLD-61 | — |
| BLD-64 | Spike | Prototype range-bounded acoustic propagation and measure it at target cave size | P0 | 3 | BLD-61 | R4 |
| BLD-65 | Spike | Decide when Scout, Hauler and Swimmer ship and reserve their chassis IDs | P1 | 0.5 | BLD-63 | — |
| BLD-66 | Task | Phase 3 gate-entry: confirm gates 1, 2 and 0 and that blindside-sim is still empty before the first sim commit | P0 | 0.25 | BLD-17, BLD-59, BLD-40, BLD-61 | R1 |
| BLD-67 | Story | Build the single fixed-point math module with cross-platform golden tests | P0 | 3 | BLD-24, BLD-37, BLD-61, BLD-66 | R4 |
| BLD-68 | Story | Build blindside-content registries with stable IDs, retired ledger, season flag and content hash | P0 | 3 | BLD-63, BLD-66 | R4 |
| BLD-69 | Story | Assign runtime entity IDs from record data and step-order-independent sequences, never from SlotMap slots | P0 | 1.5 | BLD-61, BLD-27, BLD-66 | R4 |
| BLD-70 | Story | Fill World with its documented fields and extend the state hash with mutation tests | P0 | 3 | BLD-61, BLD-69, BLD-66 | R4 |
| BLD-71 | Story | Define the cave cell model and the eight world axes as biome parameters in blindside-gen | P0 | 3 | BLD-63, BLD-68, BLD-66 | — |
| BLD-72 | Story | Generate connected caves by seeded cellular automata with perimeter entry shafts | P0 | 4 | BLD-67, BLD-71, BLD-66 | R4 |
| BLD-73 | Story | Place deposits with rough value parity per region but not accessibility parity | P1 | 2 | BLD-72, BLD-66 | — |
| BLD-74 | Story | Build the sensor module as the sole World/Belief crossing with a request-shaped SensorEnvironment | P0 | 3 | BLD-61, BLD-63, BLD-67, BLD-70, BLD-66 | — |
| BLD-75 | Story | Add compile-fail tests proving Policy::evaluate and Predicate::eval cannot reach World | P0 | 2 | BLD-62, BLD-70, BLD-66 | — |
| BLD-76 | Story | Design the sanctioned truth export for replay and spectator views as harness-only diagnostics | P1 | 2 | BLD-70, BLD-75, BLD-66 | — |
| BLD-77 | Story | Define Belief with a covariance pose model, fix history and a relaxable timestamped map | P0 | 3 | BLD-61, BLD-67, BLD-70, BLD-66 | — |
| BLD-78 | Story | Implement MotorCmd, the actuator trait and deterministic locomotion over the heightfield | P0 | 3 | BLD-67, BLD-74, BLD-72, BLD-66 | R4 |
| BLD-79 | Story | Build the AcousticField with range-bounded passage propagation, absorption and arrival bearings | P0 | 4 | BLD-64, BLD-67, BLD-70, BLD-71, BLD-66 | R4 |
| BLD-80 | Story | Add multi-path echoes and thermal shadow zones to the AcousticField | P1 | 2 | BLD-79, BLD-66 | — |
| BLD-81 | Story | Keep acoustic caches out of the state hash and prove the worst tick fits the budget | P0 | 2 | BLD-70, BLD-79, BLD-66 | R4 |
| BLD-82 | Story | Implement the odometry sensor so drift is born in the sensor layer, bias-dominated | P0 | 2 | BLD-74, BLD-78, BLD-66 | — |
| BLD-83 | Story | Implement passive acoustic returns with quality and character, plus the near-field sense | P0 | 2 | BLD-74, BLD-79, BLD-66 | — |
| BLD-84 | Story | Implement active sonar as a loudly emitting loadout module | P0 | 2 | BLD-74, BLD-79, BLD-66 | — |
| BLD-85 | Story | Implement lidar as the silent short-range alternative module, blind past the waterline | P0 | 2 | BLD-71, BLD-84, BLD-66 | — |
| BLD-86 | Story | Implement beacons in World, transponder fixes and spoofing as a real mechanism | P0 | 3 | BLD-70, BLD-74, BLD-66 | R1 |
| BLD-87 | Story | Implement the BeliefUpdater with back-propagating fixes and position-only beacon correction | P0 | 4 | BLD-82, BLD-86, BLD-77, BLD-66 | — |
| BLD-88 | Story | Record own beacons at the estimated drop pose and keep only survey-placed beacons as truth anchors | P0 | 1 | BLD-87, BLD-66 | — |
| BLD-89 | Story | Implement contact tracks and fixed-point bearing-only localisation over movement | P0 | 2.5 | BLD-83, BLD-77, BLD-66 | — |
| BLD-90 | Story | Implement terrain-relative navigation producing fixes that recover heading in surveyed ground | P0 | 4 | BLD-83, BLD-77, BLD-87, BLD-61, BLD-66 | — |
| BLD-91 | Story | Implement the magnetic anomaly sensor with false finds from magnetic character | P1 | 1.5 | BLD-74, BLD-73, BLD-66 | — |
| BLD-92 | Story | Implement deposits, cargo loading and inventory through self-report returns | P0 | 2 | BLD-74, BLD-73, BLD-77, BLD-66 | — |
| BLD-93 | Story | Implement wrecks per the container decision, holding cargo and policy for the rest of the match | P1 | 1 | BLD-70, BLD-92, BLD-66 | — |
| BLD-94 | Story | Implement collapse events from structural integrity and the structural monitor sensor | P1 | 2 | BLD-72, BLD-79, BLD-93, BLD-66 | — |
| BLD-95 | Story | Implement the optical sensor with a tiny sediment-limited radius and light as a line-of-sight tell | P1 | 2 | BLD-85, BLD-89, BLD-66 | — |
| BLD-96 | Story | Stir a transient silt cloud behind agents moving through silty passages | P2 | 1.5 | BLD-71, BLD-78, BLD-85, BLD-95, BLD-66 | — |
| BLD-97 | Story | Implement the Predicate trait in a World-blind module with the Phase 2 vocabulary and Deprecated | P0 | 2 | BLD-68, BLD-75, BLD-77, BLD-66 | R5 |
| BLD-98 | Story | Define the Surveyor chassis and Phase 3 modules as content data with loadout validation | P0 | 2 | BLD-63, BLD-68, BLD-66 | — |
| BLD-99 | Story | Implement the Action trait and the Phase 3 action set as actuator requests from Belief | P0 | 2 | BLD-78, BLD-86, BLD-92, BLD-97, BLD-66 | — |
| BLD-100 | Story | Model gait as an action parameter that sets speed and motion-noise signature | P2 | 1.5 | BLD-78, BLD-83, BLD-99, BLD-98, BLD-66 | — |
| BLD-101 | Story | Add a belief-map clearance query and map-aware steering with the Phase 1 give-up timing | P0 | 2.5 | BLD-77, BLD-87, BLD-99, BLD-66 | R1 |
| BLD-102 | Story | Ship the Phase 3 policy driver with cautious and aggressive reference policies and a VM stub | P0 | 2 | BLD-62, BLD-97, BLD-99, BLD-66 | — |
| BLD-103 | Story | Implement the AncientSystem trait, WorldView and one fixed-cycle instance that kills into a wreck | P0 | 3 | BLD-68, BLD-79, BLD-93, BLD-66 | — |
| BLD-104 | Story | Implement the MatchMode trait and Extraction mode with commit, run, extraction window and scoring | P0 | 2 | BLD-68, BLD-70, BLD-92, BLD-66 | — |
| BLD-105 | Story | Implement the command channel with Recall as a terminal abort-to-shaft with depth latency | P0 | 2 | BLD-80, BLD-86, BLD-99, BLD-104, BLD-66 | R1 |
| BLD-106 | Story | Implement the spoof module and a Belief-only clone/relocate-beacon action with an observable arming rule | P0 | 3 | BLD-86, BLD-99, BLD-102, BLD-98, BLD-76, BLD-66 | R1 |
| BLD-107 | Story | Fix and document the per-tick step order and enforce stable-ID iteration through it | P0 | 2 | BLD-87, BLD-102, BLD-103, BLD-104, BLD-66 | R4 |
| BLD-108 | Story | Build the benchmark seed set and reference match scenario for batch runs | P1 | 2 | BLD-76, BLD-105, BLD-107, BLD-106, BLD-101, BLD-66 | R1 |
| BLD-109 | Story | Profile the sim and reach 1,000 headless matches in under 10 minutes on a laptop | P0 | 3 | BLD-81, BLD-108, BLD-66 | R4 |
| BLD-110 | Story | Prove 1,000-match bit-identity across Linux, macOS and Windows in CI and report gate readiness | P0 | 2 | BLD-37, BLD-38, BLD-109, BLD-66 | R4 |
| BLD-111 | Task | Audit hardware-readiness of the Sensor and Actuator seams | P1 | 1 | BLD-78, BLD-90, BLD-95, BLD-94, BLD-66 | — |
| BLD-112 | Task | Fold Phase 1 findings and Phase 3 decisions back into the docs and list every guess | P1 | 1.5 | BLD-110, BLD-66 | — |

### BLD-61 — Reconcile ARCHITECTURE core types with Phase 1 findings before writing sim code

**Status:** Backlog  ·  **Spike**  ·  P0  ·  3 d  ·  depends on BLD-16  ·  retires R4

ARCHITECTURE.md documents types that conflict with each other and with what Phase 1 measured: Sensor::sample takes &World while the hardware-readiness section forbids sensors querying arbitrary world state; World.wrecks is a Vec while DETERMINISM rule 6 forbids index iteration; Return has no odometry variant and Fix is an absolute position while Phase 1 needed a relative measurement to a known beacon ID for a relocated beacon to lie through belief; Belief.map: OccupancyMap cannot be relaxed by a fix, which Phase 1 proved is the whole snap. Also named but undefined: the Action trait, MatchMode trait, actuator interface, Policy::evaluate signature and owning crate, WorldView contents, and the tick rate (Phase 1 ran 20 Hz and measured 0.36 ms mean / 33 ms worst tick). CLAUDE.md says ask rather than invent; this spike is the question round, and its output is the designer's answers written into ARCHITECTURE.md. Human-gated (designer question round on core types): expect about 10 calendar days and 2 round-trip(s) with the designer or testers beyond the 3 working days of work.

Done when:
- [ ] ARCHITECTURE.md carries a designer-attributed answer for each of: Sensor::sample signature (request/answer environment vs &World), wrecks container, Return odometry variant and relative beacon fix, Belief.map representation, Action/MatchMode/actuator trait surfaces, Policy::evaluate signature and crate, WorldView contents, tick rate, terrain-relative navigation's home (Sensor::sample takes no &Belief, so TRN is either a Sensor variant with a Belief-reading request or a BeliefUpdater-side request path — BLD-90 waits on this), the fixed-point trig source (hand-written CORDIC/LUT vs a pinned pure-integer crate — BLD-67 waits on this), and the World collection types for record-assigned ids (BTreeMap keyed by id vs SlotMap plus a BTreeMap index — BLD-69 waits on this)
- [ ] Every answer cites the Phase 1 measurement or doc line that motivated the question
- [ ] Anything still undecided is listed with the Phase 3 story keys it blocks
- [ ] No code in blindside-sim is changed by this story

### BLD-62 — Decide what drives agents in Phase 3 before the Phase 4 VM exists

**Status:** Backlog  ·  **Spike**  ·  P0  ·  1 d  ·  depends on BLD-61

The Phase 3 gate runs 1,000 matches, but blindside-vm and blindside-behavior are Phase 4 deliverables (ROADMAP). Either hand-written Rust policies against the Predicate/Action traits or a minimal VM pulled forward must run the agents. ARCHITECTURE says blindside-sim depends only on vm and content, and Policy holds BtNode (behavior crate) plus Op (vm crate), so the sim must execute a compiled artifact plus VmBudget, never Policy itself. Ask the designer; record the decision; note the risk that hand-written policies may not represent VM-run policies. Human-gated (designer decision on the policy driver): expect about 3 calendar days and 1 round-trip(s) with the designer or testers beyond the 1 working days of work.

Done when:
- [ ] Decision recorded in ARCHITECTURE.md with the designer's name on it
- [ ] Shape of the blindside-vm stub agreed so the dependency constraint holds either way
- [ ] The Policy::evaluate entry point location is fixed so the compile-fail test (BLD-75) has a concrete target
- [ ] Representativeness risk of the chosen driver written into ROADMAP Phase 4 notes

### BLD-63 — Fix the Phase 3 sensor set, module list, content format and permanent content IDs

**Status:** Backlog  ·  **Spike**  ·  P0  ·  2 d  ·  depends on BLD-61

ROADMAP says 'the six sensors' but never enumerates them; DESIGN.html describes eight sensing sources; Phase 1 added lidar as a second active module and a near-field sense. ARCHITECTURE rule 1 and DETERMINISM rule 7 make every SensorId/ModuleId/PredicateId/ActionId/AncientKindId permanent, so a wrong early assignment can never be undone. Also unspecified: the content file format, whether the content hash covers the full pack or only the active season's enabled set (rule 5 interacts with rule 2), and whether blindside-content joins the constrained crate set since floats could enter through data. Settle all of it with the designer before BLD-68 assigns a single ID. Human-gated (designer sign-off on permanent IDs): expect about 7 calendar days and 2 round-trip(s) with the designer or testers beyond the 2 working days of work.

Done when:
- [ ] A signed-off ID table (in the content files or docs/CONTENT-IDS.md) lists every SensorId, ModuleId, PredicateId, ActionId, AncientKindId and biome/mode id Phase 3 ships
- [ ] Lidar's place (own SensorId and ModuleId, or a Return variant) and the near-field sense (module vs chassis-intrinsic) are decided
- [ ] Content file format decided; content hash coverage (full pack vs enabled set) decided and written in the blindside-content README
- [ ] Decision on whether blindside-content is lint-constrained recorded in DETERMINISM.md
- [ ] The ID table reserves entries for the spoof module and action (BLD-106), the behaviour-recovery module (BLD-171), the interference modules and actions BLD-163 may choose, and any chassis class BLD-65 gives a phase; reserved ids are listed as reserved, never reused

### BLD-64 — Prototype range-bounded acoustic propagation and measure it at target cave size

**Status:** Backlog  ·  **Spike**  ·  P0  ·  3 d  ·  depends on BLD-61  ·  retires R4

Phase 1's SoundField rebuilt a whole-cave Dijkstra per emission: 33 ms worst tick against a 0.36 ms mean at 200x120 in Python. It fits 20 Hz on one hand-authored cave but grows with cave size, and Phase 3 has four teams pinging plus ancient signatures, crashes and motion noise. ROADMAP lists 'Acoustic field: propagation, absorption by rock type, thermal shadow zones' for Phase 3, so the model must be chosen with a budget, not inherited. Prototype in scratch Rust outside the workspace (throwaway, floats allowed): range-bounded Dijkstra from the emitter over passage cells with a flooded cost multiplier, versus a precomputed passage graph with per-edge lengths and per-node bearings. Measure both at the Phase 3 cave size on the dev laptop. Human-gated (acoustic budget agreed with the designer): expect about 3 calendar days and 1 round-trip(s) with the designer or testers beyond the 3 working days of work.

Done when:
- [ ] Mean and worst-case cost per emission measured for at least two approaches at the target cave size with 8 concurrent emitters
- [ ] A per-tick acoustic budget in milliseconds at the chosen tick rate is written down and agreed with the designer
- [ ] Chosen approach keeps the worst tick under that budget in the prototype
- [ ] Cache and hash policy for derived propagation fields stated (excluded from state hash, or canonical) for BLD-81
- [ ] Prototype code is not merged into the workspace

### BLD-65 — Decide when Scout, Hauler and Swimmer ship and reserve their chassis IDs

**Status:** Backlog  ·  **Spike**  ·  P1  ·  0.5 d  ·  depends on BLD-63

DESIGN's chassis table lists four classes ('| Scout | Small, quiet, fast, three module slots | Fits anywhere; almost no carry capacity; fragile |', Hauler 'Blocked by constrictions; audible across half the cave', Swimmer 'Useless on dry rock; unmatched below the waterline') and ARCHITECTURE's extension table says 'Chassis / modules | pure data | 1 → 4 classes', but no epic in the draft plan ever went past the Surveyor: BLD-98 excludes the other three, Phase 5 renders Surveyor only, and Phases 6-9 never return to chassis. The passage-width axis, the flooding axis, value-parity-not-accessibility (BLD-73) and the Swimmer/sonar coupling from PHASE-1-OPEN-QUESTIONS Part 4 all exist to differentiate chassis that are never built. Because chassis and module IDs are permanent (ARCHITECTURE rule 1), the decision on which phase each class enters belongs beside the BLD-63 ID table. Ask the designer; write nothing but the decision. Human-gated (designer decision on chassis classes): expect about 3 calendar days and 1 round-trip(s) with the designer or testers beyond the 0.5 working days of work.

Done when:
- [ ] A designer-attributed decision names the phase (or the deferral reason) for each of Scout, Hauler and Swimmer, recorded in docs/CONTENT-IDS.md next to the BLD-63 table
- [ ] IDs are reserved in the table for any class given a phase, or explicitly left unassigned with the reason; no reserved ID is ever reused
- [ ] The named target epic gains a data-only story (chassis size class, slots, mass, noise signature, terrain viability, pressure limit) with the loadout rules the designer states, e.g. a Swimmer cannot carry lidar as its only active sensor
- [ ] No chassis data is written in this spike

### BLD-66 — Phase 3 gate-entry: confirm gates 1, 2 and 0 and that blindside-sim is still empty before the first sim commit

**Status:** Backlog  ·  **Task**  ·  P0  ·  0.25 d  ·  depends on BLD-17, BLD-59, BLD-40, BLD-61  ·  retires R1

CLAUDE.md: Phase 3 is 'blocked on 1, 2, 0' and 'do not start a phase whose predecessor's gate has not been met.' The draft plan's Phase 3 code stories chained only to BLD-33, so nothing in the dependency graph waited for the Phase 1 report, the Phase 2 report, or Phase 0 readiness, and tools/render_dev_plan.py reads only depends_on. This story is the single anchor every Phase 3 code story depends on. It also closes the parallel Phase 0/Phase 2 window by asserting nothing crept into blindside-sim while the designer's 'start the real thing' pressure was on. The build agent records the reports and the designer's read; it does not declare any gate met. Human-gated (designer 'proceed' on three reports): expect about 3 calendar days and 1 round-trip(s) with the designer or testers beyond the 0.25 working days of work.

Done when:
- [ ] Links to the BLD-16 playtest report (via BLD-17's decision record), the BLD-59 report and the BLD-40 readiness report, each with the designer's dated 'proceed' written beside it; no report is described as 'gate met'
- [ ] `git diff` of blindside-sim, blindside-gen and blindside-content between the BLD-40 commit and HEAD contains only comments and docs; World has only `tick`; fxmath has no implementations; Belief is empty (the BLD-40 script re-run)
- [ ] Every open question from BLD-61..BLD-64 is recorded in ARCHITECTURE.md as answered or listed with the Phase 3 story keys it blocks, and those stories are not started
- [ ] A one-line script over docs/dev-plan.json confirms every Phase 3 story that touches blindside-sim/gen/content/harness lists this story in depends_on

### BLD-67 — Build the single fixed-point math module with cross-platform golden tests

**Status:** Backlog  ·  **Story**  ·  P0  ·  3 d  ·  depends on BLD-24, BLD-37, BLD-61, BLD-66  ·  retires R4

DETERMINISM.md practical note: trig and sqrt are the usual desync culprits and must come from a single module, never platform math. Phase 0 established the module location and the lint; this story fills it with sin, cos, atan2, sqrt over Fx = I32F32, plus Vec2Fx (dot, length, rotate, angle wrap, distance). Whether to hand-write CORDIC/LUT or pin a pure-integer crate is undecided; ask before choosing.

Done when:
- [ ] sin, cos, atan2, sqrt over Fx exist only in the designated math module; a test greps/parses the constrained crates and fails on any other trig/sqrt call site
- [ ] A golden table of at least 100 inputs per function is checked in and asserted bit-identical on Linux, macOS and Windows CI
- [ ] Vec2Fx operations have unit tests and maximum error versus a reference generated by the BLD-25 golden tool (floats permitted there, never in the crate) is documented
- [ ] No f32/f64 anywhere (CI lint green); the fixed crate version is pinned exactly

### BLD-68 — Build blindside-content registries with stable IDs, retired ledger, season flag and content hash

**Status:** Backlog  ·  **Story**  ·  P0  ·  3 d  ·  depends on BLD-63, BLD-66  ·  retires R4

ARCHITECTURE extension points: each is a registry keyed by stable ID, defined in data, validated at build time, with rules 1 (never reuse a retired ID; Deprecated evaluates to a fixed value), 2 (content hash in every replay) and 5 (season flag). Seven registries: sensors, predicates, actions, ancients, chassis/modules, biomes, match modes. Values must arrive as Fx or integers so no float leaks in through data. Uses the ID table and format decisions from BLD-63.

Done when:
- [ ] Seven typed registries keyed by their ID newtype, stored in BTreeMap, iterated in ID order
- [ ] Build fails on: duplicate ID within a kind, reuse of an ID in the retired ledger, dangling cross-reference, unknown season flag, trait-backed entry with no matching impl
- [ ] content_hash() -> [u8;32] is identical across the three CI platforms for the same checkout and changes when an enabled entry changes; a test pins whether a flagged-off entry changes it, per the BLD-63 decision
- [ ] Numeric fields parse directly to Fx or integers; a test asserts no f32/f64 path exists in content loading
- [ ] A fixture policy referencing a retired PredicateId loads and its Guard evaluates to the recorded fixed value
- [ ] .gitattributes sets eol=lf for content and fixture files

### BLD-69 — Assign runtime entity IDs from record data and step-order-independent sequences, never from SlotMap slots

**Status:** Backlog  ·  **Story**  ·  P0  ·  1.5 d  ·  depends on BLD-61, BLD-27, BLD-66  ·  retires R4

DETERMINISM rule 6: 'Entity iteration is by stable ID, always. Never by insertion order or index.' Rule 7: stable IDs are 'never derived from name hashes, registration order, or vector indices.' ARCHITECTURE.md's World uses `SlotMap<AgentId, AgentTruth>`, `SlotMap<BeaconId, Beacon>`, `Vec<Wreck>`: a SlotMap key is (index, version) assigned by insertion, so iterating by key is iterating by insertion order, and an id that is the slot key is derived from registration order. BLD-70's test 'insert agents in two orders and get identical hashes' cannot pass while ids are slot keys. Runtime beacons and wrecks need ids that do not depend on the per-tick step order either, or two teams dropping beacons in the same tick get order-dependent ids. This changes documented World field types, so the designer answers through BLD-61. Human-gated (World field-type sign-off): expect about 3 calendar days and 1 round-trip(s) with the designer or testers beyond the 1.5 working days of work.

Done when:
- [ ] AgentId is derived from MatchRecord.loadouts (team, slot); BeaconId from (owner AgentId, per-owner drop sequence); WreckId from the dead agent's AgentId; DepositId and AncientId from the generator by a seed-determined, insertion-independent rule; each id type's doc comment states its assignment and that it is never a SlotMap key, Vec index or name hash
- [ ] World collections are BTreeMap<Id, T>, or SlotMap plus a BTreeMap<Id, key> index that every per-tick loop and the state hash iterate; the designer's sign-off on the amended field types is recorded in ARCHITECTURE.md
- [ ] A test constructs the same MatchRecord with loadouts listed in two orders and gets the same AgentIds and the same final state hash after a full match
- [ ] A test permutes the per-tick agent step order and gets the same BeaconIds for beacons dropped in the same tick
- [ ] clippy disallowed_methods rejects SlotMap::iter, keys, values and drain in the constrained crates (moved here from BLD-70)

### BLD-70 — Fill World with its documented fields and extend the state hash with mutation tests

**Status:** Backlog  ·  **Story**  ·  P0  ·  3 d  ·  depends on BLD-61, BLD-69, BLD-66  ·  retires R4

ARCHITECTURE: World is pub(crate) with tick, cave, agents, beacons, wrecks, deposits, ancients, acoustics and no rng field (RNG is stateless). DETERMINISM rule 6: entity iteration by stable ID, never insertion order; SlotMap's native iteration is slot order and a slot key is assigned by insertion, so ids and iteration follow BLD-69 (record-assigned ids; the raw SlotMap iterators are disallowed there). PHASE-0-HARNESS: the hash must cover everything that affects future ticks (including every agent's Belief, which policies read) and nothing else; getting it wrong in either direction wastes weeks. Applies the wrecks decision from BLD-61.

Done when:
- [ ] World has the documented fields with the wrecks container per the BLD-61 decision; no pub accessor returns World or any field of it outside the crate
- [ ] Collections and ids follow BLD-69 (record-assigned ids, never SlotMap keys); the by-stable-id iteration helper from BLD-69 is the only iteration path used by this story
- [ ] The state hash doc comment lists every hashed and every excluded field with the reason; a mutation test per hashed field changes the hash and per excluded field does not
- [ ] A test inserts agents in two different orders and asserts identical hashes
- [ ] Desync canary passes on all three platforms after the change

### BLD-71 — Define the cave cell model and the eight world axes as biome parameters in blindside-gen

**Status:** Backlog  ·  **Story**  ·  P0  ·  3 d  ·  depends on BLD-63, BLD-68, BLD-66

ROADMAP Phase 3: 'the 8 world axes'; DESIGN.html enumerates flooding, passage width, rock type, sediment, magnetic character, structural integrity, depth profile and thermal layering, but DESIGN is background not spec, so confirm the axis list with the designer before IDs are fixed. Cells carry rock/dry/flooded, width class, depth, integrity, rock absorption/reflectivity, sediment, magnetic noise and thermal layer, plus the heightfield the sim locomotes over. Phase 1 settled the waterline semantics: flooded cells are impassable to walkers, an acoustic conduit, and lidar-reflective (a lidar ray reaching water returns the surface as a wall — the designer's call in PHASE-1-OPEN-QUESTIONS Part 4, over water returning nothing); one classification function must serve locomotion, acoustics and sensors so they never disagree. Human-gated (axis list confirmed by the designer): expect about 3 calendar days and 1 round-trip(s) with the designer or testers beyond the 3 working days of work.

Done when:
- [ ] Cave type with per-cell fields, all Fx or integers, plus heightfield
- [ ] Biome is a content params struct with a stable id carrying the eight axis weights; one biome ships
- [ ] Axis list confirmed by the designer and recorded in ARCHITECTURE.md
- [ ] A single cell-classification query (rock/dry/flooded, walkable, free, lidar-reflective at the waterline) is the only one locomotion, acoustics and sensors call; a test asserts no duplicate classification logic
- [ ] Determinism lint green in blindside-gen

### BLD-72 — Generate connected caves by seeded cellular automata with perimeter entry shafts

**Status:** Backlog  ·  **Story**  ·  P0  ·  4 d  ·  depends on BLD-67, BLD-71, BLD-66  ·  retires R4

ROADMAP Phase 3: 'cellular automata caves, connectivity guarantees'. DESIGN: chambers connected by passages of varying width, generated by CA over a seeded noise field then carved into a connectivity graph, with entry shafts distributed around the perimeter and every team sharing the seed. Generation lives in blindside-gen (a constrained crate) and draws only from DeterministicRng. Connectivity: every entry reaches every deposit region by some chassis-passable route; repair or reject-and-reseed must itself be deterministic. Phase 1's hand-authored cave is not reused.

Done when:
- [ ] Same seed and biome produce a bit-identical cave on Linux, macOS and Windows (cave hash golden in CI)
- [ ] 1,000 seeds all pass the connectivity checker; team count is a parameter (default 4) with shafts on the perimeter
- [ ] Dead ends exist and are unmarked; mixed flooded and dry passages appear in every seed; a shaft chamber radius is defined for extraction
- [ ] Generation time per seed is measured and reported by the harness so BLD-109 can budget it
- [ ] No HashMap iteration, floats or std::time in blindside-gen (lint)
- [ ] Any heap or priority queue in generation (connectivity repair, region carving) orders entries by (cost, cell id) so equal-cost ties break by stable cell id; a symmetric fixture yields identical caves on two Sims and on all three OSes

### BLD-73 — Place deposits with rough value parity per region but not accessibility parity

**Status:** Backlog  ·  **Story**  ·  P1  ·  2 d  ·  depends on BLD-72, BLD-66

ROADMAP Phase 3 'value parity'; DESIGN: deposits are placed with guaranteed rough parity of total worth per region but not of accessibility — some behind a constriction, a flooded sump, or a failing ceiling. Value is deliberately abstract. Deposits are unknown to agents until sensed, so nothing here touches Belief.

Done when:
- [ ] Per-region value totals within the designer's stated tolerance across 1,000 seeds (tolerance recorded in content)
- [ ] At least one deposit per seed is reachable only through a constriction or a flooded cell (test)
- [ ] Deposit capture radius and load time are content tunables (Phase 1 reference: radius 12 because 6 was smaller than drift)
- [ ] Placement is deterministic across platforms (covered by the cave hash golden)

### BLD-74 — Build the sensor module as the sole World/Belief crossing with a request-shaped SensorEnvironment

**Status:** Backlog  ·  **Story**  ·  P0  ·  3 d  ·  depends on BLD-61, BLD-63, BLD-67, BLD-70, BLD-66

CLAUDE.md: the sensor layer is the only code permitted to read both World and Belief and lives in one module so it can be audited by reading it. ARCHITECTURE hardware-readiness: no sensor may assume it can query arbitrary world state; it expresses what it needs as a request the sim answers from World and hardware would answer from a driver. This story defines the Sensor trait (id, cost, emits, sample), the Return enum (six documented variants plus whatever BLD-61 added) with FixSource carrying no lie marker, and a SensorEnvironment trait (raycast over an arc against FREE or WALKABLE, audible emitters at a pose, field strength at a pose, transponders in range, terrain patch at a pose) implemented over World inside this module only. Sensor noise draws from DeterministicRng keyed by (tick, entity, sensor_id, purpose) per ROADMAP Phase 3.

Done when:
- [ ] Exactly one module names both World and Belief; a test parses the crate and fails if any other module does
- [ ] Sensor impls compile against SensorEnvironment only; a test asserts no sensor impl file names World or AgentTruth fields
- [ ] Return is serializable and a test proves a spoofed-beacon Fix and an honest Fix are structurally indistinguishable
- [ ] emits() returns a typed Emission — Acoustic { signature } or Optical { light } — not Option<AcousticSignature>; an acoustic emission registers an acoustic emitter for the tick, an optical one registers a line-of-sight emitter (consumed by BLD-95). Design panel 2026-09-06: lidar and lights are a second channel, not a silent sonar, and the Return enum should not have to grow a variant to say so
- [ ] RNG purpose space includes sensor_id; two Sims produce identical returns every tick
- [ ] Module header comment states it is the audited crossing and documents the hardware seam

### BLD-75 — Add compile-fail tests proving Policy::evaluate and Predicate::eval cannot reach World

**Status:** Backlog  ·  **Story**  ·  P0  ·  2 d  ·  depends on BLD-62, BLD-70, BLD-66

ARCHITECTURE: write a compile-time test asserting Policy::evaluate cannot reach World; it exists to catch the 'just for debugging' accessor someone adds in year two. Phase 1's phase1/match/invariant.py (AST walk) is the Python precedent; in Rust the mechanism is module privacy plus trybuild compile-fail cases. Targets the entry point fixed in BLD-62.

Done when:
- [ ] A trybuild case that names blindside_sim::World from outside the crate fails to compile with the expected error text
- [ ] A case that adds a &World accessor inside the predicate module fails (module privacy), and one that obtains &World from inside Policy::evaluate fails
- [ ] A signature test asserts Predicate::eval and Policy::evaluate accept &Belief and no type defined in world.rs
- [ ] Runs in CI on every commit on all three platforms and is named in CLAUDE.md's definition of done

### BLD-76 — Design the sanctioned truth export for replay and spectator views as harness-only diagnostics

**Status:** Backlog  ·  **Story**  ·  P1  ·  2 d  ·  depends on BLD-70, BLD-75, BLD-66

ARCHITECTURE says World goes to neither client nor renderer, but ROADMAP Phase 5 ('replay with both layers drawn together') and DESIGN ('ground truth appears in exactly two places: the post-match replay and the spectator view') require truth after the run. The reconciliation is a named ReplayFrame type produced by the harness behind the same diagnostics feature gate as Phase 0's structural diff, carrying truth poses alongside each agent's Belief for the same tick, never reachable from the live Sim API. CLAUDE.md says stop and ask when anything downstream wants &World; this is that ask, made deliberately in Phase 3 so Phase 5 does not improvise it. Human-gated (designer sign-off on the truth export): expect about 3 calendar days and 1 round-trip(s) with the designer or testers beyond the 2 working days of work.

Done when:
- [ ] Designer sign-off recorded in ARCHITECTURE.md naming this the one deliberate relaxation of the invariant
- [ ] ReplayFrame exists only behind the diagnostics feature; a compile-fail test proves Policy, Predicate, Action and BeliefUpdater cannot name it
- [ ] harness frames <record> dumps ReplayFrames for a replay; the live Sim public API exposes no path to it
- [ ] ReplayFrame is string/plain-data only, never a typed &World

### BLD-77 — Define Belief with a covariance pose model, fix history and a relaxable timestamped map

**Status:** Backlog  ·  **Story**  ·  P0  ·  3 d  ·  depends on BLD-61, BLD-67, BLD-70, BLD-66

ARCHITECTURE: Belief is public with pose (mean + covariance), map, contacts, beacons including ones that lie, inventory, ticks_since_fix, self_report. Phase 1 lessons: the covariance grows with distance and heading sigma (sigma_along 0.5+0.038d, sigma_cross 0.5+0.5d·sigma_theta, sigma_theta += 0.0013d), resets on a fix, and is kept slightly under truth so a fix that jumps further than the ellipse promised is the tell a player can catch; a FixRecord (jump, surprise = jump/sigma_before, pre/post pose) is the only belief-legal spoof tell; and the map must be a timestamped point set with source and confidence so a fix can relax it — the OccupancyMap named in ARCHITECTURE cannot, per the BLD-61 decision. Belief is hashed because policies read it.

Done when:
- [ ] Belief has the documented fields with the map representation decided in BLD-61; every map point carries placement tick, source id and confidence
- [ ] PoseEstimate covariance grows per the content model and resets on fix; fix history exposes jump, surprise and sigma_before
- [ ] belief.rs imports nothing from world.rs (test) and Belief round-trips through serialization without World
- [ ] Belief is covered by the state hash (mutation test)

### BLD-78 — Implement MotorCmd, the actuator trait and deterministic locomotion over the heightfield

**Status:** Backlog  ·  **Story**  ·  P0  ·  3 d  ·  depends on BLD-67, BLD-74, BLD-72, BLD-66  ·  retires R4

ROADMAP Phase 3: 'deterministic locomotion over a heightfield'. ARCHITECTURE hardware-readiness names the actuator interface as the second seam: a trait whose sim implementation applies MotorCmd to AgentTruth and a hardware driver could implement later. Phase 1 lessons: turn-rate limit and wall sliding are part of the true motion, and the true achieved delta must be recorded so the odometry sensor can corrupt it (drift is born in the sensor layer, not in integration). DESIGN: constrictions block larger chassis, wide passages are faster, walkers cannot enter flooded cells. Belief only ever sees the command and the odometry return, never the outcome.

Done when:
- [ ] Actuator trait per the BLD-61 decision with a sim implementation; the trait doc states what a hardware driver would implement
- [ ] Surveyor is blocked below its width class and by flooded cells; speed scales with passage width per content
- [ ] AgentTruth.last_true_delta is populated each tick and read only by the odometry sensor through SensorEnvironment (test)
- [ ] Same MotorCmd sequence produces a bit-identical traversal on three platforms (golden)
- [ ] No sensor or belief code reads AgentTruth.pose directly outside the sensor module
- [ ] Turning around is impossible below a content width class (DESIGN passage-width axis: 'whether you can turn around'); the actuator refuses the manoeuvre and Belief learns it only through the odometry return

### BLD-79 — Build the AcousticField with range-bounded passage propagation, absorption and arrival bearings

**Status:** Backlog  ·  **Story**  ·  P0  ·  4 d  ·  depends on BLD-64, BLD-67, BLD-70, BLD-71, BLD-66  ·  retires R4

ROADMAP Phase 3: 'Acoustic field: propagation, absorption by rock type'. Phase 1 established that sound must propagate along passages, not straight lines: range is path length, the arrival bearing is the direction the sound came in from (path direction a few steps back from the listener), flooded cells carry sound further (0.55 path cost in Phase 1), and this is what makes bearings ambiguous and gives echoes a mechanism. Implements the model chosen in BLD-64 so cost is bounded by emission range, not cave size. Emitters registered per tick from Sensor::emits, ancient signatures, chassis motion noise and crashes; only the sensor module reads the field.

Done when:
- [ ] On an L-shaped fixture the bearing at the listener points down the passage, not the straight line
- [ ] Flooded cells extend range and absorbent rock shortens it, per content values; an emission never expands past its max range in cells
- [ ] Two Sim instances produce identical fields every tick; Dijkstra heap entries are ordered by (cost, cell id) so equal-cost ties break by stable cell id, and a symmetric fixture yields identical fields on two Sims and on all three OSes
- [ ] Per-emission cost at the target cave size measured against the BLD-64 budget and recorded
- [ ] No threading inside the tick; lint green
- [ ] Detection and audible range scale with passage width per content (DESIGN passage-width axis: 'detection range')

### BLD-80 — Add multi-path echoes and thermal shadow zones to the AcousticField

**Status:** Backlog  ·  **Story**  ·  P1  ·  2 d  ·  depends on BLD-79, BLD-66

ROADMAP Phase 3 'thermal shadow zones'; DESIGN: reflective rock produces false echoes and thermal layering bends sound so some parts of the cave are acoustically invisible from others — the positional advantage, and what later blocks the command channel (Phase 6). Phase 1 scripted the echo as a second sound field from a second point; here it must emerge from the rock-type axis, with the tell being that an echo does not move and does not repeat. Nothing in Return or Belief may mark a bearing as an echo.

Done when:
- [ ] A fixture with a reflective chamber yields two bearings from one emission on different arrival passages
- [ ] No is_echo or equivalent flag exists anywhere in Return, Belief or ContactTrack (grep test)
- [ ] Shadow zones are stable for a seed, listed in a diagnostics dump, and passive returns are absent across them
- [ ] An in_shadow(pose) query exists and is called by nothing except the command channel (BLD-105)
- [ ] A same-passage fixture (echo and standing contact within the merge angle, as at Phase 1's 2:15 where the echo on bearing 23 was absorbed into the rival contact on bearing 13) has its expected Belief-side outcome stated: either the second arrival is a Belief-visible event through BLD-89's per-arrival record, or the design explicitly accepts that same-passage echoes are invisible and BLD-108 places echoes where bearings separate; no is_echo flag either way

### BLD-81 — Keep acoustic caches out of the state hash and prove the worst tick fits the budget

**Status:** Backlog  ·  **Story**  ·  P0  ·  2 d  ·  depends on BLD-70, BLD-79, BLD-66  ·  retires R4

Phase 1 cached a SoundField per emitter keyed by emission; the Rust equivalent is a derived value that PHASE-0-HARNESS says the hash must exclude, while emitter state must be included. This story pins that decision with mutation tests and measures the worst tick with four teams pinging, ancient signatures and a crash on a target-size generated cave, against the BLD-64 budget. CLAUDE.md's Phase 1 lesson: the field must not be a whole-cave Dijkstra per emission.

Done when:
- [ ] Mutation test: clearing or warming the propagation cache does not change the state hash; changing an emitter does
- [ ] A cold-start Sim and a warm-cache Sim stepped in lockstep produce identical hashes every tick
- [ ] Worst-tick acoustic cost on the target cave with 8 concurrent emitters is printed by the harness and is under the BLD-64 budget
- [ ] Measurement recorded in docs/HARNESS.md

### BLD-82 — Implement the odometry sensor so drift is born in the sensor layer, bias-dominated

**Status:** Backlog  ·  **Story**  ·  P0  ·  2 d  ·  depends on BLD-74, BLD-78, BLD-66

ROADMAP Phase 3 'dead reckoning' in the fusion stack; DESIGN calls drift the real clock of the game. Phase 1 lesson: drift must come from corrupting the true achieved delta into odometry inside the sensor layer, and it must be heading-bias dominated (0.11 deg/cell, scale bias 0.055, small random walks) or the map fuzzes instead of ghosting; at 0.035 deg/cell the error was invisible. Bias signs are drawn per agent from the seed so two agents do not share a lie. Uses the Return variant decided in BLD-61; the BeliefUpdater integrates this return, not the MotorCmd. Sensor-noise fairness is a CLAUDE.md known-weak area: all values are from one Phase 1 seed and must be listed as guesses.

Done when:
- [ ] Odometry return produced from AgentTruth.last_true_delta via SensorEnvironment only
- [ ] Over a 200-cell straight leg the integrated heading error is approximately the content-specified bias (Phase 1 reference about 22 degrees) and the random-walk term is an order of magnitude smaller
- [ ] Two agents on the same seed receive independent bias signs from DeterministicRng
- [ ] Identical returns every tick across two Sim instances; noise keyed by (tick, entity, sensor_id, purpose)
- [ ] Tunables in content with the Phase 1 measurement cited in a comment

### BLD-83 — Implement passive acoustic returns with quality and character, plus the near-field sense

**Status:** Backlog  ·  **Story**  ·  P0  ·  2 d  ·  depends on BLD-74, BLD-79, BLD-66

ARCHITECTURE Return::Bearing { angle, quality }; DESIGN: you hear something and know the direction, not the distance. Phase 1 added a sound character (ping, tone, signature, crash) as a property of the signal rather than an identification, quality falling with path length (1 - path/max_range), bearing noise widening from about 4 to 22 degrees at max range, and deafness for a second after the agent's own ping. Phase 1 also needed a fourth near-field sense (range about 2.5 cells, every 4 ticks, low quality) so a corridor walked without pinging registers as sparse points instead of nothing; whether it is a module or chassis-intrinsic was decided in BLD-63.

Done when:
- [ ] Return::Bearing carries quality and character and never a range
- [ ] Bearing noise widens with path length per content; the agent is deaf for the content-specified ticks after its own emission
- [ ] Near-field returns carry a distinct source id and an agent walking a corridor without pinging accumulates sparse map points
- [ ] Own motion noise registers as an emitter that rival passive sensors can hear (chassis noise signature from content)
- [ ] Deterministic across two Sims

### BLD-84 — Implement active sonar as a loudly emitting loadout module

**Status:** Backlog  ·  **Story**  ·  P0  ·  2 d  ·  depends on BLD-74, BLD-79, BLD-66

ARCHITECTURE Return::RangeBearing and emits() Some => audible; DESIGN: range and bearing, real map data, and you have just announced your position to every passive listener in the basin. Phase 1 reference: 120-degree arc, 60 rays, range 30, rays marched against FREE so they cross water and map the far wall of a sump, range/bearing noise, two false returns per ping, audible for 3 s, self-deaf 1 s. The post-Phase-1 decision makes sonar one of two mutually exclusive active modules (see BLD-85), loud, long, and the only one that works in water.

Done when:
- [ ] RangeBearing returns over the arc with content-specified noise and false-return count
- [ ] A ping registers an emitter for its audible duration and every passive listener in range receives a Bearing with character ping
- [ ] Sonar maps the far wall of a flooded sump on a fixture
- [ ] Content entry with ModuleId and SensorId; slot cost charged against the loadout
- [ ] Deterministic across two Sims
- [ ] RangeBearing noise and false-return count scale with rock reflectivity per the rock-type axis (DESIGN: 'Sonar return quality, false echoes, how far your own noise carries')

### BLD-85 — Implement lidar as the silent short-range alternative module, blind past the waterline

**Status:** Backlog  ·  **Story**  ·  P0  ·  2 d  ·  depends on BLD-71, BLD-84, BLD-66

Designer decision recorded in PHASE-1-OPEN-QUESTIONS Part 4: sonar and lidar are both loadout modules, the player picks, and the choice is locked at launch. Lidar is silent, short, precise, blind through water or silt, and its visible light is a line-of-sight tell rather than a basin-wide one; a Swimmer can only sensibly carry sonar. Phase 1 reference: 360 degrees, 90 rays, range 18, 1.5 s period, no false returns, rays marched against WALKABLE so they stop at the waterline; the designer's later decision (Part 4, sensor_rig.py uncommitted) makes the water surface return as a wall rather than a hole — 'a sump maps as a wall over a mirror: the agent steers round it and never learns what is beyond', chosen over the alternative where water returned nothing, read as open space, and would have sent the agent in; lidar built about four times the points of sonar without emitting. The LOS tell needs the optical sensor (BLD-95); this story registers the exposure so that sensor can see it.

Done when:
- [ ] On a sump fixture a lidar ray reaching water returns the surface as a wall at the waterline; the agent steers round the sump and never maps beyond it, while sonar maps the far wall (PHASE-1-OPEN-QUESTIONS Part 4: the rejected alternative, water returning nothing, would have sent the agent into the machinery)
- [ ] emits() is Emission::Optical, never Acoustic: a lidar sweep registers no acoustic emitter
- [ ] Sediment reduces lidar range per the biome axis
- [ ] A lidar-active agent is registered as an optical emitter visible only with line of sight (consumed by BLD-95)
- [ ] Loadout validation rejects a Swimmer with lidar as its only active sensor (or the designer's alternative rule) and sonar/lidar are selectable alternatives

### BLD-86 — Implement beacons in World, transponder fixes and spoofing as a real mechanism

**Status:** Backlog  ·  **Story**  ·  P0  ·  3 d  ·  depends on BLD-70, BLD-74, BLD-66  ·  retires R1

ARCHITECTURE: FixSource::Beacon(BeaconId) — a spoofed beacon returns a Fix that is simply wrong; nothing in the type system distinguishes a lie. GLOSSARY: spoofing deals no damage. Phase 1 lessons: fixes fire on the rising edge of entering a transponder's range (continuous fixing pins the agent to its chain); the fix is a relative measurement (beacon id, range, bearing) that Belief resolves against its own record of that beacon, which is why a relocated beacon lies through belief; the spoof clones a known beacon id ahead of the victim, is louder than an honest beacon (range 18 vs 6) and reasserts every 8 s; lie-distance over beacon range is the most important ratio (34/6; below 1 it self-heals; range 30 pinned the victim for five minutes). The survey-placed shaft transponder is the only truth anchor. Phase 1 scripted the spoof; here the beacon is a World entity, and the rival's spoof module, action and arming rule are BLD-106.

Done when:
- [ ] Beacon entities carry owner, id, true position, range and reassert period; the beacon rack has a finite count per loadout
- [ ] Transponder returns fire on the rising edge only: walking past an own chain yields one fix per pass (test)
- [ ] A relocated or cloned beacon produces a Fix through the identical function as an honest one (test calls the same path) and no field distinguishes it
- [ ] Spoof tunables (lie offset, range, reassert) are content data with the Phase 1 ratios recorded in comments
- [ ] Unknown beacon ids are ignored by Belief (nothing to resolve against)
- [ ] Deterministic across two Sims

### BLD-87 — Implement the BeliefUpdater with back-propagating fixes and position-only beacon correction

**Status:** Backlog  ·  **Story**  ·  P0  ·  4 d  ·  depends on BLD-82, BLD-86, BLD-77, BLD-66

ARCHITECTURE BeliefUpdater { integrate_motion, fuse }; ROADMAP Phase 3 fusion stack: dead reckoning, terrain-relative fixes, beacon fixes, contact tracking. Phase 1's most important finding: a naive fix only stops further smearing; the snap requires the correction to back-propagate over everything placed since the previous fix — map points, trail, beacons dropped since the epoch (except the fixing beacon and truth anchors), contact bearings and tracker observations — weighted by how far into the drift interval each was, rotating about the epoch pose and translating. Second finding: a beacon fix corrects position only, never heading (the heading gain was measured to make half of honest loop closures worse); heading is recovered only by terrain-relative fixes. A spoofed fix runs the identical code and visibly tears the recent map to the wrong place. Beacon fixes are relative measurements resolved against KnownBeacon (BLD-86). The updater sees &[Return] and &mut Belief only.

Done when:
- [ ] After an honest loop closure on a fixture the doubled corridor collapses: map RMS error to truth (measured in the test via diagnostics) drops by the designer's stated fraction
- [ ] A beacon fix changes the heading estimate by exactly zero (the terrain-fix half of this test lives in BLD-90, which depends on this story)
- [ ] A spoofed fix and an honest fix call the same function and a test asserts the spoof relocates the recent map by the lie offset
- [ ] On the benchmark seeds no honest beacon fix increases true position error (Phase 1 measurement reproduced)
- [ ] Returns are fused in a stable order; two Sims agree every tick; only Fx arithmetic
- [ ] Odometry integration grows covariance and increments ticks_since_fix; a fix resets both

### BLD-88 — Record own beacons at the estimated drop pose and keep only survey-placed beacons as truth anchors

**Status:** Backlog  ·  **Story**  ·  P0  ·  1 d  ·  depends on BLD-87, BLD-66

Phase 1 finding that changes the design text: a beacon only recorded where the agent believed it was at drop time, so re-acquiring it re-anchors the agent to its own past error — the beacon chain buys confidence, not accuracy. Only the survey-placed shaft is a truth anchor. This is the premise working as written (ARCHITECTURE Belief.beacons 'including ones that lie') and must not be 'fixed' by giving own beacons true positions. Fixes from beacon ids the agent never recorded are ignored.

Done when:
- [ ] KnownBeacon stores the estimated pose at drop and a truth_anchor flag set only for survey-placed beacons
- [ ] On a fixture an own-beacon fix collapses covariance while true position error is unchanged (test via diagnostics)
- [ ] Relaxation (BLD-87) never moves a truth anchor; a fix from an unrecorded id is dropped
- [ ] A design note stating 'beacon chain buys confidence, not accuracy' is added to ARCHITECTURE.md

### BLD-89 — Implement contact tracks and fixed-point bearing-only localisation over movement

**Status:** Backlog  ·  **Story**  ·  P0  ·  2.5 d  ·  depends on BLD-83, BLD-77, BLD-66

ARCHITECTURE Belief.contacts: bearings over time, unresolved. DESIGN: two bearings taken from different positions over time give a solution, so passive tracking is an active skill involving deliberate movement, not a readout; decoys and echoes do not move naturally. Phase 1 reference: merge bearings within 18 degrees and 8 s, fade after 14 s, transient overrides scrape; the BearingTracker crosses bearings by weighted least squares with conditioning thresholds (returns nothing while ill-conditioned), residual-based sigma, and smoothing because raw solutions jumped ninety cells between frames. Trackers are relaxed by fixes.

Done when:
- [ ] Two bearings from positions far apart yield an estimate within its sigma on a fixture; near-parallel bearings yield None
- [ ] Frame-to-frame estimate movement is bounded by the smoothing constant (test)
- [ ] ContactTrack exposes bearing history, character and a stationary-over-time measure that predicates can read
- [ ] Fixed-point least squares only; deterministic across two Sims
- [ ] Trackers are included in the relaxation set of BLD-87 (test)
- [ ] A moving cluster of lidar or optical returns — a range-and-bearing origin that persists across sweeps and is not on the believed map — opens a ContactTrack seeded with range, so a lidar agent can see a rival at close quarters without ever hearing it; a stationary cluster stays map. Design panel 2026-09-06: Phase 1's lidar player has no way to notice the rival at all, which makes the quiet loadout blind rather than stealthy
- [ ] Each arrival is retained on the ContactTrack with its tick and character even when merged by bearing, so a second arrival inside the merge window (Phase 1's 2:15 echo, absorbed into the rival's standing contact 10 degrees away) is a Belief-visible event

### BLD-90 — Implement terrain-relative navigation producing fixes that recover heading in surveyed ground

**Status:** Backlog  ·  **Story**  ·  P0  ·  4 d  ·  depends on BLD-83, BLD-77, BLD-87, BLD-61, BLD-66

ROADMAP Phase 3 lists terrain-relative fixes in the fusion stack; DESIGN calls it the only fix that collapses drift from what the agent has already mapped, working only in surveyed ground, and the counter to false beacons and beacon theft. Phase 1 lesson that makes it load-bearing: inferring heading from a beacon fix made half of all honest loop closures worse, so HEADING_FIX_GAIN is 0 and heading drift runs uncorrected for the whole match until this exists — the map fans open with nothing to straighten it. Implementation is fixed-point scan matching of current returns against the agent's own map over a small pose window; this is genuinely hard and the algorithm choice should be shown to the designer before it is tuned. TRN reads Belief and the environment, but Sensor::sample takes no &Belief, so its home (a Sensor variant with a Belief-reading request, or a BeliefUpdater-side request path) is the BLD-61 decision this story waits on; either way it lives in the audited sensor module. Human-gated (scan-matching algorithm shown to the designer): expect about 5 calendar days and 1 round-trip(s) with the designer or testers beyond the 4 working days of work.

Done when:
- [ ] Produces Fix { source: Terrain } with the heading correction form decided in BLD-61, and never fires in unmapped ground (test on a fresh corridor)
- [ ] On a loop-closure fixture, heading error after a TRN fix is below the designer's threshold and a benchmark-seed run shows no TRN fix increasing true heading error
- [ ] After a spoof on the fixture, a subsequent TRN fix moves the estimate back toward truth (the DESIGN counter works)
- [ ] Per-evaluation cost measured and within the tick budget; deterministic across two Sims
- [ ] Fixed-point only; correlation window and overlap threshold are content tunables
- [ ] A terrain fix changes the heading estimate (a beacon fix never does — BLD-87's half of this test); the heading correction is bounded by the content window

### BLD-91 — Implement the magnetic anomaly sensor with false finds from magnetic character

**Status:** Backlog  ·  **Story**  ·  P1  ·  1.5 d  ·  depends on BLD-74, BLD-73, BLD-66

ARCHITECTURE Return::Anomaly { rough_direction, strength }; DESIGN: long range, no emission, extremely coarse — tells you something is roughly over there without saying what or where — and noisy rock produces false finds so it never becomes a treasure pointer. False positive rate scales with the magnetic character axis from BLD-71.

Done when:
- [ ] Return::Anomaly with rough_direction quantized to the content-specified coarseness and no range
- [ ] False find rate scales with the region's magnetic axis (test across two biome settings)
- [ ] emits() is None; no emitter registered
- [ ] Deterministic across two Sims

### BLD-92 — Implement deposits, cargo loading and inventory through self-report returns

**Status:** Backlog  ·  **Story**  ·  P0  ·  2 d  ·  depends on BLD-74, BLD-73, BLD-77, BLD-66

ARCHITECTURE Belief.inventory and self_report (power, damage, module health). Phase 1 lesson: loading succeeds only if the agent is truly within the capture radius, and the radius must exceed drift (at 6 the agent sat 7.8 cells short and 'extracted with an empty hold and never knew why'; 12 works); 30 s per unit, capacity 2; the agent learns it loaded via a cargo return and can hunt a few cells if it did not. Nothing on the policy side sees deposit truth.

Done when:
- [ ] Inventory changes only through a return fused into Belief; a failed load is silent on the belief side (no truth leak)
- [ ] Capture radius, load time and capacity are content tunables with the Phase 1 values cited
- [ ] SelfReport carries the minimal power/damage/module-health fields and is hashed
- [ ] Deterministic across two Sims

### BLD-93 — Implement wrecks per the container decision, holding cargo and policy for the rest of the match

**Status:** Backlog  ·  **Story**  ·  P1  ·  1 d  ·  depends on BLD-70, BLD-92, BLD-66

GLOSSARY: a wreck persists for the match holding its cargo and its policy; any agent may salvage one (salvage itself is Phase 6). ARCHITECTURE lists wrecks: Vec<Wreck> and DETERMINISM rule 6 forbids index iteration, so the container follows the BLD-61 decision (SlotMap keyed by WreckId, or an explicitly append-only log never indexed as identity). A wreck is sensable: sonar returns it without identity, optical identifies it.

Done when:
- [ ] Agent death produces a Wreck at the true position with inventory and PolicyRef; wrecks are never removed during a match
- [ ] Wrecks are hashed and iterated by stable id
- [ ] A wreck appears as a RangeBearing to sonar and as an identity only through optical
- [ ] Deterministic across two Sims

### BLD-94 — Implement collapse events from structural integrity and the structural monitor sensor

**Status:** Backlog  ·  **Story**  ·  P1  ·  2 d  ·  depends on BLD-72, BLD-79, BLD-93, BLD-66

ARCHITECTURE Return::Structural { time_to_failure }; DESIGN: structural integrity is the main environmental kill vector, and the monitor warns of a collapse a few seconds before it happens — a slot spent to survive things that would otherwise kill without explanation in belief-space. Failing cells collapse on a deterministic schedule drawn from DeterministicRng per (tick, cell) after a warning lead; the volume becomes impassable; agents inside die and leave a wreck; the crash is heard basin-wide. Induced collapse (interference) is unscheduled and not built here.

Done when:
- [ ] Collapse changes cell passability, is hashed, and is identical across two Sims
- [ ] Agents inside the volume die and produce wrecks; a crash emitter is registered
- [ ] The monitor returns Some(time_to_failure) at least the content lead before the collapse; without the module nothing reaches Belief beforehand
- [ ] Collapse frequency is a biome parameter

### BLD-95 — Implement the optical sensor with a tiny sediment-limited radius and light as a line-of-sight tell

**Status:** Backlog  ·  **Story**  ·  P1  ·  2 d  ·  depends on BLD-85, BLD-89, BLD-66

ARCHITECTURE Return::Optical { patch }; DESIGN: high detail, tiny radius, needs illumination that gives you away in the dark — identification, not detection. It is the only way a Contact becomes an identity, and its light is the mechanism for lidar's line-of-sight tell (BLD-85). Silt clouding from the sediment axis destroys it entirely.

Done when:
- [ ] Patch returned only within radius and line of sight; radius shrinks with sediment to zero at silt-out
- [ ] An agent with its light on (optical or lidar active) is visible to a rival optical sensor with line of sight and invisible without it
- [ ] Identification of a ContactTrack reaches Belief only through a return, never by lookup
- [ ] Deterministic across two Sims

### BLD-96 — Stir a transient silt cloud behind agents moving through silty passages

**Status:** Backlog  ·  **Story**  ·  P2  ·  1.5 d  ·  depends on BLD-71, BLD-78, BLD-85, BLD-95, BLD-66

DESIGN's sediment axis row reads 'Sediment | Clear to silt-out | Optical range, and whether moving stirs up a cloud that blinds you behind you'. BLD-85 and BLD-95 reduce lidar and optical range by the static sediment value only; nothing makes movement raise a transient cloud that blinds the agent that stirred it and any follower. Cloud state lives in World, decays deterministically, and is read only through SensorEnvironment; it is also the substrate the silt-clouding interference method (BLD-175) would use, so building it here keeps that method a module plus an action later.

Done when:
- [ ] A per-cell transient sediment level is raised by agent movement, scaled by the biome sediment axis and chassis mass, and decays per tick by a content constant; static plus transient sediment is exposed through one SensorEnvironment query
- [ ] Lidar and optical range fall with the combined value; on a fixture an agent following another through a silty passage loses optical returns while a follower in a clear passage does not
- [ ] Cloud state is hashed (mutation test) and identical across two Sims; per-tick update cost is measured and within the BLD-64 budget
- [ ] Tunables in content with the values listed as guesses in the PR

### BLD-97 — Implement the Predicate trait in a World-blind module with the Phase 2 vocabulary and Deprecated

**Status:** Backlog  ·  **Story**  ·  P0  ·  2 d  ·  depends on BLD-68, BLD-75, BLD-77, BLD-66  ·  retires R5

ARCHITECTURE: trait Predicate { id, eval(&Belief, &[Fx]) -> bool } — &Belief, never &World, enforced by module privacy (rule 4). Initial vocabulary is whatever the Phase 2 gate settled (unexplored_branch_exists, uncertainty > theta, carrying_cargo, plus any addition the Phase 2 report records); do not expand it — R5 is about vocabulary size. Retired ids resolve to a Deprecated predicate evaluating to a fixed value (rule 1). Phase 1 candidates (signature quality >= theta, fix surprise >= theta, contact stationary, ticks_since_ping, contact heard within N s, best contact quality >= theta) are recorded as candidates in a doc, not implemented; the last two carry the PHASE-1-OPEN-QUESTIONS Part 4 panel finding that in Phase 1 'do I ping' is a cooldown rather than a decision because no policy reads contacts, so the Phase 4 gate could otherwise be won on ping cadence alone.

Done when:
- [ ] Predicate module cannot name World (covered by the BLD-75 compile-fail case)
- [ ] Phase 2's predicates have content entries with stable PredicateIds and unit tests over Belief fixtures
- [ ] A fixture policy referencing a retired id loads and evaluates to the ledger's fixed value
- [ ] docs/PREDICATE-CANDIDATES.md lists the Phase 1 candidates including 'contact heard within N s' and 'best contact quality >= theta' with the Part 4 note that without one of them pinging is a cooldown, not a decision; nothing else is added

### BLD-98 — Define the Surveyor chassis and Phase 3 modules as content data with loadout validation

**Status:** Backlog  ·  **Story**  ·  P0  ·  2 d  ·  depends on BLD-63, BLD-68, BLD-66

ARCHITECTURE: chassis and modules are pure data (1 -> 4 classes); GLOSSARY: loadout is chassis plus modules, locked at launch, and modules cost slots, mass and power. Phase 3 and Phase 5 ship the Surveyor only (six slots per DESIGN); Scout, Hauler and Swimmer are not built here — reserve IDs only if the designer asks. Modules: passive acoustic, sonar, lidar, beacon rack, cargo bay, terrain-relative nav, magnetometer, optical, structural monitor, the spoof module (BLD-106), and near-field/odometry per the BLD-63 decision, each with slot/mass/power and a SensorId reference. A VmBudget field lives on the loadout as data for Phase 4.

Done when:
- [ ] Loadout validator rejects over-slot, over-mass and over-power builds and any chassis/module combination the designer ruled out
- [ ] MatchRecord.loadouts round-trips and the loadout is immutable after match start
- [ ] Sonar and lidar are selectable alternatives; every module has a stable ModuleId from the BLD-63 table
- [ ] No trait impls exist for chassis or modules (data only)
- [ ] Chassis carry a pressure-limit depth honoured by locomotion (DESIGN depth-profile axis: 'pressure limits')
- [ ] A content validation invariant asserts the beacon drop interval is much larger than the beacon acquisition range (tuning.py: 'the gap between 6 and 45 is where the smear happens')
- [ ] The behaviour-recovery module (BLD-171) and the interference modules BLD-163 may choose have ids reserved in the BLD-63 table but no entries yet; the spoof module has its entry

### BLD-99 — Implement the Action trait and the Phase 3 action set as actuator requests from Belief

**Status:** Backlog  ·  **Story**  ·  P0  ·  2 d  ·  depends on BLD-78, BLD-86, BLD-92, BLD-97, BLD-66

ARCHITECTURE's extension table lists impl Action + entry (2 -> 15) but never gives the trait; BLD-61 settles the signature. Actions read &Belief plus params and emit actuator or module requests (MotorCmd, ping, drop beacon, load, abort to shaft) — the actuator side of hardware-readiness. Set: take_branch and return_to_beacon from Phase 2, plus ping, drop_beacon, load and abort_to_shaft (used by Recall); the spoof action is BLD-106 and gait selection is BLD-100, both registered through this trait. DESIGN: no direct combat — the registry may contain no damage-dealing action; every kill is a navigation or environmental failure.

Done when:
- [ ] Action impls produce requests only and cannot name World (compile-fail case added to BLD-75's set)
- [ ] A test enumerates the action registry and fails if any action can reduce another agent's health directly
- [ ] Each action has a content entry with a stable ActionId and a headless test
- [ ] take_branch and return_to_beacon match Phase 2's semantics as recorded in the Phase 2 report

### BLD-100 — Model gait as an action parameter that sets speed and motion-noise signature

**Status:** Backlog  ·  **Story**  ·  P2  ·  1.5 d  ·  depends on BLD-78, BLD-83, BLD-99, BLD-98, BLD-66

DESIGN chooses walkers over pods for 'noise that varies with gait so movement style becomes an acoustic decision'. BLD-78 integrates MotorCmd and BLD-83 registers own motion noise as an emitter, but no story lets a policy choose a gait, and BLD-142 refers to 'the gait set the sim models in Phase 3' that nothing modelled. The sim model is cheap regardless of the walker-vs-pod art decision: a per-gait speed factor and motion-noise signature in chassis content data, selected through the actuator request. Animation is Phase 5.

Done when:
- [ ] At least two gaits per chassis in content data, each with an Fx speed factor and a motion-noise signature; gait is part of the actuator request from BLD-78 and selectable by an action parameter
- [ ] On a fixture a rival passive listener hears the loud gait at a longer path length than the quiet one; own-noise emitter registration in BLD-83 uses the current gait's signature
- [ ] The cautious reference policy walks quietly and the aggressive one fast, so batch matches exercise both
- [ ] Current gait is part of AgentTruth and hashed; deterministic across two Sims

### BLD-101 — Add a belief-map clearance query and map-aware steering with the Phase 1 give-up timing

**Status:** Backlog  ·  **Story**  ·  P0  ·  2.5 d  ·  depends on BLD-77, BLD-87, BLD-99, BLD-66  ·  retires R1

tuning.py MAP_LOOKAHEAD note (uncommitted, 2026-09-06): with steering on the 2.5-cell near-field feeler alone, the spoofed agent spent 2:24 to 8:00 inside one chamber skipping every waypoint in turn, because each target was thirty cells off in truth and pointed into rock; it held a 26,000-point map and used none of it. Reading clearance off the believed map does not undo the lie but finds the door: the map is globally wrong by the drift and so is the agent, so locally it is right. The same change re-timed every beat (ANCIENT_PHASE_S had to move from 20 to 30 because at 20 nobody died). A second lesson rides with it: STUCK 5 s + ESCAPE 9 s x 2 escapes = 28 s before a waypoint is abandoned, down from 48, because 'a lost agent should look like it is failing to get somewhere, not like it is stuck in a loop'. BLD-77 defines the map as a timestamped point set and BLD-99 defines actions, but nothing gives Belief an occupancy/clearance query, rebuilds it after a BLD-87 relax, or gives actions map-aware steering and give-up tunables. Phase 1's point_cloud.py (2-cell bins over a belief-space extent larger than the cave, rebuilt after relax) is the reference.

Done when:
- [ ] Belief.map exposes blocked(x, y) and clearance(pose, heading, max_range) over a coarse occupancy binning that is rebuilt after every relax; fixed-point only; the bins are either excluded from the state hash as derived or canonical (mutation test)
- [ ] Action steering combines near-field clearance with map clearance at content lookahead values (Phase 1: 9 cells steering, 18 escaping); the escape heading prefers the longest open line with weak goal alignment, per the policy.py note that a strong pull toward the goal 'kept it grinding the same wall'
- [ ] Regression on the benchmark spoof seed: after the spoofed fix the agent leaves its current chamber within a content-specified time instead of remaining until match end
- [ ] Stuck, escape and escapes-before-skip are content tunables with the 28 s Phase 1 note; a test shows a waypoint pointing into rock is abandoned within that budget
- [ ] The BLD-108 beat sheet is re-run after this lands and any moved beat is re-tuned with its measurement recorded (the ANCIENT_PHASE lesson)

### BLD-102 — Ship the Phase 3 policy driver with cautious and aggressive reference policies and a VM stub

**Status:** Backlog  ·  **Story**  ·  P0  ·  2 d  ·  depends on BLD-62, BLD-97, BLD-99, BLD-66

Per the BLD-62 decision: either hand-written Rust policies against the Predicate/Action traits or a minimal VM pulled forward. Two reference policies reproduce Phase 1's cautious (lidar, uncertainty return, freezes on ancient signature) and aggressive (sonar, pings often, passes the ancient chamber) behaviours so batch matches exercise every system. ARCHITECTURE: the sim executes the compiled artifact plus VmBudget, never a Policy holding BtNode; blindside-vm remains a stub that satisfies the dependency constraint.

Done when:
- [ ] Both reference policies run a full match headless from a MatchRecord
- [ ] Policy::evaluate takes &Belief and is the target of the BLD-75 compile-fail test
- [ ] blindside-sim holds no BtNode type; the executable form and VmBudget are what the sim consumes
- [ ] A match with both policies is bit-identical on three platforms (golden hash)

### BLD-103 — Implement the AncientSystem trait, WorldView and one fixed-cycle instance that kills into a wreck

**Status:** Backlog  ·  **Story**  ·  P0  ·  3 d  ·  depends on BLD-68, BLD-79, BLD-93, BLD-66

ARCHITECTURE: trait AncientSystem { kind, signature (legible BEFORE lethal), step(&mut AncientState, &WorldView, &DeterministicRng), hazard, provocable_by }; GLOSSARY: deterministic machinery with a signature detectable before it is dangerous, not a random hazard. WorldView is the narrowed truth view decided in BLD-61. Phase 3 ships one instance to exercise the trait, tuned to Phase 1's reference (75 s period, 9 s warning with signature quality rising 0.3 to 1.0, 4 s lethal, radius 9, phase offset 30 s — tuning.py: at 20 nobody dies in either kit; at 30 the rival dies at 5:41 (sonar) / 5:45 (lidar), and several other phases kill the player instead, which is DESIGN's 'march into a trench' beat and worth a deliberate seed (BLD-108); a 42 s period killed the rival too early and silenced the map). Two full systems with exploit and counter are Phase 7; more are deferred.

Done when:
- [ ] Trait matches ARCHITECTURE; a generic test asserts for every impl that signature() is Some at least the warning lead before hazard() is Some
- [ ] The signature is registered as an acoustic emitter whose quality rises toward lethal (the acceleration is the warning)
- [ ] An agent inside the hazard volume dies, leaves a wreck, and a crash emitter is registered basin-wide
- [ ] AncientState is hashed; ancients are unreachable from any Belief-side module (compile-fail case)
- [ ] Cycle tunables are content data with the Phase 1 values cited; provocable_by is empty and documented as Phase 7
- [ ] The trait carries a yields() seam: what an agent that interfaces with the machinery brings back (DESIGN: the machinery is where behaviours come from; Phase 1's aggressive rival goes to look and stops to download). Phase 3 ships the seam and an Interface action that consumes it as a timed, slowed, cargo-free dwell inside the hazard radius — the risk is the price. What a yield unlocks is Phase 4+ and is deliberately not designed here

### BLD-104 — Implement the MatchMode trait and Extraction mode with commit, run, extraction window and scoring

**Status:** Backlog  ·  **Story**  ·  P0  ·  2 d  ·  depends on BLD-68, BLD-70, BLD-92, BLD-66

ARCHITECTURE extension table: impl MatchMode (1 -> 4), trait undefined until BLD-61. DESIGN match structure: descent and commit (~20 s of full telemetry), run, an extraction window in the last 90 s, and anything not back through a shaft is lost with its cargo; Extraction scores value recovered through a shaft. Match length is a content parameter (Phase 1 used 8 minutes at 20 Hz, so about 9,600 ticks; DESIGN's 10 minutes is a guess). PHASE-0-HARNESS requires a match to run to completion and verify a final hash, so MatchRecord carries the length/end rule and final hash per the Phase 0 decision. Scoring reads World inside the sim and emits only a score.

Done when:
- [ ] impl MatchMode for Extraction registered by stable id; the registry supports adding modes without touching the sim loop
- [ ] A match ends deterministically at the content length; agents outside a shaft when the window closes lose their cargo
- [ ] Score is computed inside blindside-sim from World and exposed only as a number; no policy path can reach the scorer inputs
- [ ] harness run completes a full Extraction match and prints score, tick count and final hash; MatchRecord round-trips with length and final hash

### BLD-105 — Implement the command channel with Recall as a terminal abort-to-shaft with depth latency

**Status:** Backlog  ·  **Story**  ·  P0  ·  2 d  ·  depends on BLD-80, BLD-86, BLD-99, BLD-104, BLD-66  ·  retires R1

ARCHITECTURE MatchRecord.commands is the only live input; DESIGN: a few bytes, latency proportional to depth, blocked in acoustic shadow (the shadow block is Phase 6 but the hook from BLD-80 is wired now). Phase 1 lesson: Recall is a blunt abort-to-shaft — it drives straight at the believed shaft rather than retracing the beacon chain (retracing a corrupted estimate walks into wall after wall), is terminal (running off the route must never re-plan a survey; that bug silently cancelled the command), then searches with an Archimedean spiral at walking pace pitched against the shaft's transponder range until the shaft answers; the search is the only thing in the match that can undo a spoof. Delivery delay is computed by the world from true depth, which is not an invariant leak because the policy never observes it. Phase 1's four Recall faults become regression tests.

Done when:
- [ ] Commands are applied at recorded tick plus latency in (tick, team, sequence) order; latency = base + k * true depth from content
- [ ] Recall never re-plans a survey after running off its route (regression test); arrival radius then extraction radius match the shaft chamber
- [ ] Spiral pitch is less than twice the shaft transponder range so the shaft cannot be skipped (test)
- [ ] On the benchmark scenario, a sweep of Recall timings from 3:00 to 7:00 in 30 s steps yields at least one timing that extracts with cargo and at least one later timing that does not (b43ba0b: success is not monotonic in send time; the honest mechanism that saves it is usually walking home past its own chain); the sweep table records which own beacons the returning agent re-acquired on each run
- [ ] Commands are dropped while in_shadow(pose) is true (unit test only; feature exercised in Phase 6)

### BLD-106 — Implement the spoof module and a Belief-only clone/relocate-beacon action with an observable arming rule

**Status:** Backlog  ·  **Story**  ·  P0  ·  3 d  ·  depends on BLD-86, BLD-99, BLD-102, BLD-98, BLD-76, BLD-66  ·  retires R1

DESIGN's interference toolkit opens with the false beacon: 'A false beacon does not damage anything. It convinces an agent that it is somewhere it is not — and the agent then acts, correctly and confidently, on a wrong premise.' BLD-86 builds beacons as World entities and says spoofing becomes 'an action rivals can take', but its acceptance criteria never add the action; BLD-99's action set omits it, the draft's module list had no spoof module, and BLD-108 and BLD-147 both assume 'the aggressive rival relocates a beacon (spoof)'. Phase 1 scripted the spoof from the truth side: after 140 s, when the victim was at least 30 cells from its last beacon measured in the victim's belief frame (fac388d moved arming from distance walked, which gave 15.3 or 52.9 cells depending on backtracking, to displacement from the target beacon), the rival's beacon id was cloned 4 cells ahead of the victim at range 18, reasserting every 8 s. A rival policy that reads only its own Belief cannot evaluate that condition, so the beat does not port as-is: this story adds a spoof module (content entry with slot/mass/power and a finite count), a clone-and-relocate action that reads &Belief only, and an arming rule the rival can actually observe. tuning.py's measured couplings must survive the port: lie over beacon range at 34/6 (below 1 it self-heals within a minute); spoof range 18 not 30 (at 30 the liar pinned the victim 'confidently wrong' for five minutes with sigma 0.9 against 80 cells of true error); the spoof lands before the victim's uncertainty return fires (at 4:00 the return fired first at 3:31 and made Recall worthless); and the spoofed fix collapses sigma and disarms that return, 'which is the design, not a bug'. Spoofing deals no damage (GLOSSARY). Human-gated (arming-rule sign-off): expect about 3 calendar days and 1 round-trip(s) with the designer or testers beyond the 3 working days of work.

Done when:
- [ ] Content entries with stable ModuleId and ActionId from the BLD-63 table; the action is unavailable without the module and loadout validation says so; the module has a finite count per loadout
- [ ] The action reads &Belief only (compile-fail case added to the BLD-75 set) and emits a module request; the sim places or relocates the beacon entity in World through BLD-86's beacon code; it deals no damage and BLD-99's no-attack registry test still passes
- [ ] The arming rule is expressed over the rival's Belief (a foreign beacon within reach whose owner has been heard moving away, or the designer's alternative), recorded with the designer's sign-off; no World read reproduces the Phase 1 truth-side condition
- [ ] A headless match with the aggressive reference policy carrying the module produces a Fix at the victim with surprise >= 10x through the identical Fix function an honest beacon uses; no field distinguishes it
- [ ] Spoof content carries lie offset, range and reassert period with the tuning.py ratios cited; a headless test shows lie/range below 1 self-heals within 60 s and 34/6 walks the victim off its chain; range 18 lets the victim leave range so drift resumes
- [ ] On the BLD-108 benchmark seed the spoof lands before the cautious policy's uncertainty predicate fires, and immediately after the spoofed fix uncertainty > theta evaluates false (regression test for 'the spoof disarms self-preservation by design')
- [ ] The scenario is verified through ReplayFrames (BLD-76), never from Belief; deterministic across two Sims and bit-identical in the three-platform batch
- [ ] BLD-108 and BLD-147 depend on this story and their spoof beat is produced by it, not by a script

### BLD-107 — Fix and document the per-tick step order and enforce stable-ID iteration through it

**Status:** Backlog  ·  **Story**  ·  P0  ·  2 d  ·  depends on BLD-87, BLD-102, BLD-103, BLD-104, BLD-66  ·  retires R4

DETERMINISM rules 5 and 6: no threading inside a tick, entity iteration by stable ID. Phase 1's order per tick was: deliver pending commands, then per agent (policy(Belief) -> actuator -> side effects -> sensors sample -> belief fuse), then ancients, then expire sounds, then mode step and end check. This story fixes the Rust order, writes it into ARCHITECTURE.md, and proves insertion order cannot change the result once every subsystem is integrated.

Done when:
- [ ] Step order documented in ARCHITECTURE.md and implemented in one function that every subsystem hangs off
- [ ] A test inserts agents, beacons and ancients in two different orders and asserts identical hashes over a full match
- [ ] clippy disallowed_types/methods reject rayon and std::thread in the constrained crates; any exception needs the PR-template proof
- [ ] Desync canary green on three platforms with all Phase 3 systems active

### BLD-108 — Build the benchmark seed set and reference match scenario for batch runs

**Status:** Backlog  ·  **Story**  ·  P1  ·  2 d  ·  depends on BLD-76, BLD-105, BLD-107, BLD-106, BLD-101, BLD-66  ·  retires R1

The Phase 3 gate is measured by the Phase 0 batch executor over seeded matches; Phase 4's gate and Phase 9's listing evaluation reuse a benchmark set. This story fixes a seed set and a reference scenario in which Phase 1's beat sheet emerges from mechanisms rather than scripts: the aggressive rival relocates a beacon through the BLD-106 action, reflective rock produces an echo, the ancient cycles, and a recorded Recall command fires. Verified through the BLD-76 diagnostics, never from Belief.

Done when:
- [ ] docs/BENCHMARK.md lists the seed set, loadouts, policies and command log used
- [ ] harness batch runs the set and reports per-seed score, cargo, deaths, fix count, spoof fixes and Recall outcome
- [ ] At least one seed reproduces the spoof -> wrong branch -> Recall -> spiral -> extraction arc, confirmed from ReplayFrames
- [ ] The set is versioned with the content hash so a balance change invalidates it loudly
- [ ] A second benchmark seed in which the spoofed player walks into the ancient hazard (tuning.py: 'the spoof walks it into the machinery's chamber', DESIGN's 'march into a trench'), recorded as the candidate first failure for BLD-182
- [ ] Risk R9, "a dry clear cave is quiet": one seed in a dry, clear, non-reflective biome where neither kit emits until the ancient's signature. If eight minutes pass with no contact, no fix and no beat, that is reported as a design finding for BLD-112 rather than tuned away (design panel 2026-09-06)
- [ ] The beat-sheet seeds are re-verified whenever steering, acoustics or drift content changes (the ANCIENT_PHASE lesson: a steering change moved every path and forced a retune)

### BLD-109 — Profile the sim and reach 1,000 headless matches in under 10 minutes on a laptop

**Status:** Backlog  ·  **Story**  ·  P0  ·  3 d  ·  depends on BLD-81, BLD-108, BLD-66  ·  retires R4

ROADMAP Phase 3 gate: 1,000 matches headless in under 10 minutes. That is roughly 0.6 s per match including cave generation and about 16k ticks per second aggregate; DETERMINISM rule 5 allows parallelism only across matches. Phase 1's Python baseline was 0.36 ms per tick mean with a 33 ms acoustic worst tick. Profile acoustics, terrain matching, sensors and generation; fix hot spots without changing semantics, and bump golden hashes only deliberately with a stated reason. Also the first real data point for R8 (server cost per match).

Done when:
- [ ] harness batch --seeds 1..1000 completes in under 10 minutes on the dev laptop with wall-clock and matches/hour printed
- [ ] A per-subsystem tick profile at target cave size is checked into docs/HARNESS.md
- [ ] No hash changes except deliberate bumps recorded with reason; no threading inside a tick
- [ ] Generation time per seed is within the share of the per-match budget recorded in BLD-72

### BLD-110 — Prove 1,000-match bit-identity across Linux, macOS and Windows in CI and report gate readiness

**Status:** Backlog  ·  **Story**  ·  P0  ·  2 d  ·  depends on BLD-37, BLD-38, BLD-109, BLD-66  ·  retires R4

ROADMAP: bit-identical across Linux/macOS/Windows — R4 answered here, and if it fails you find out before the client exists. Uses the Phase 0 three-platform CI matrix, batch hash tables, per-tick hash logs and bisect tooling; any divergence is bisected to a tick, fixed at the root (never by loosening the comparison), and pinned with a regression test. CLAUDE.md: do not report the gate as met; report that the build is ready for it. Human-gated (three-OS CI debugging of 1,000-match bit-identity): expect about 14 calendar days and 0 round-trip(s) with the designer or testers beyond the 2 working days of work.

Done when:
- [ ] A CI job runs the benchmark batch on every commit and the full 1,000 seeds nightly on all three OS and diffs the seed->final-hash tables: empty diff
- [ ] Every divergence found is bisected with the Phase 0 tooling, root-caused, fixed and covered by a regression test in the constrained crate
- [ ] docs/HARNESS.md documents the golden-hash update procedure (must cite a schema or content-hash change)
- [ ] A written report to the designer states 'ready for the Phase 3 gate' with wall-clock and hash-table evidence, plus the list of every guessed value

### BLD-111 — Audit hardware-readiness of the Sensor and Actuator seams

**Status:** Backlog  ·  **Task**  ·  P1  ·  1 d  ·  depends on BLD-78, BLD-90, BLD-95, BLD-94, BLD-66

CLAUDE.md: the behavior authoring layer is intended to run on real hardware; sensor and actuator interfaces should be designed as though a hardware backend will exist — a few days of care in Phase 3 is the difference between possible and impossible later. Audit every sensor impl against SensorEnvironment only and the actuator against its trait, document what a driver would implement for each request, and build nothing for hardware. Human-gated (designer review of the two seams): expect about 5 calendar days and 1 round-trip(s) with the designer or testers beyond the 1 working days of work.

Done when:
- [ ] An automated test asserts no sensor impl file imports world.rs or names World/AgentTruth fields (extends the BLD-74 test to all sensors)
- [ ] SensorEnvironment and Actuator docs list each request with what the sim answers from World and what hardware would answer from a driver
- [ ] Designer has reviewed the two seams and the review is recorded in ARCHITECTURE.md
- [ ] No hardware backend code exists in the workspace

### BLD-112 — Fold Phase 1 findings and Phase 3 decisions back into the docs and list every guess

**Status:** Backlog  ·  **Task**  ·  P1  ·  1.5 d  ·  depends on BLD-110, BLD-66

CLAUDE.md definition of done: anything guessed at is listed explicitly. Several Phase 1 findings change design text: the beacon chain buys confidence not accuracy; terrain-relative navigation is the anti-spoof counter; lidar's line-of-sight tell; 'Do I ping?' moves for a lidar carrier; Return gained an odometry variant and a relative beacon fix; Belief.map is a relaxable point set; tick rate is 20 Hz with the Phase 1 measurement; ROADMAP's deadwater-* names are stale (note only — CLAUDE.md says do not spend time on renaming). Three uncommitted-retune findings also belong in the text: map-aware steering off the believed map with the 28 s give-up, the same-passage echo merge, and the spoof's Belief-only arming rule replacing Phase 1's truth-side one. GLOSSARY's passive/active entry is the designer's to edit. Sensor-noise fairness (a CLAUDE.md known-weak area) has only ever been felt on one seed; say so. Human-gated (designer glossary edit): expect about 5 calendar days and 1 round-trip(s) with the designer or testers beyond the 1.5 working days of work.

Done when:
- [ ] ARCHITECTURE.md core types match the code, including Return, Belief, World.wrecks, Sensor::sample and the actuator and Action/MatchMode traits
- [ ] GLOSSARY passive/active entry updated by the designer or flagged as pending in the summary
- [ ] The Phase 3 summary carries a GUESSES section listing every value not given by a doc, with the Phase 1 constant or measurement it came from, and names sensor-noise fairness as untested across generated caves

## BLD-113 — VM, behavior trees, and the node editor

**Phase Phase 4 — VM and node editor.** Policies run as sandboxed fixed-point bytecode under a per-tick instruction budget; behavior trees compile directly to that bytecode with no text intermediate; a Godot node editor (built on a GDExtension that hands across Belief-derived data only) is the second authoring path; execution traces show which nodes fired on what predicate values; Phase 2's induction is re-implemented in Rust to emit the same Policy artifact; graph diff and schema migration keep policies readable across versions and seasons. Human-gated stories in this epic: 12 of 27 (6 designer decisions or reviews, 2 playtests or self-tests, 4 art, toolchain, CI or commercial), carrying at least 54 calendar days of latency on top of 67.75 working days.

- **Gate — pass:** A policy authored entirely in nodes beats a hand-written one on the benchmark set. Graph diff works on two versions of the same tree. (ROADMAP Phase 4, verbatim.)
- **Gate — kill:** ROADMAP states no separate kill criterion; the universal rule applies: if the node-authored challenger cannot beat the hand-written reference on the benchmark set, or the diff cannot identify the edits between two versions of the same tree, Phase 5 does not start. A challenger that loses because the predicate vocabulary or the editor cannot express what the hand-written policy does is R5/R2 evidence (composition rung unexpressive; the game becomes an IDE) and must be reported as such, not tuned away by changing the benchmark. Do not report the gate as met; report ready for the gate with numbers.
- **Can start when:** BLD-114 is the gate-entry anchor: it links the BLD-110 readiness report with the designer's dated 'proceed' (1,000 headless matches under 10 minutes, bit-identical final hashes on Linux/macOS/Windows in CI, which itself required the Phase 0, 1 and 2 gates) and quotes the BLD-62 decision about what drove agents for that gate, because BLD-117 turns that seam into the real VM. Every Phase 4 story except BLD-115 depends on BLD-114. BLD-115 (Godot toolchain bootstrap) depends only on the three-OS CI (BLD-37); it may be pulled into late Phase 3 solely with the designer's explicit sign-off, recorded in BLD-114.
- **Estimate:** 67.75 working days

| Key | Type | Summary | Pri | Days | Depends on | Risk |
|---|---|---|---|---|---|---|
| BLD-114 | Task | Phase 4 gate-entry: confirm the Phase 3 gate result and the policy-driver decision before VM code | P0 | 0.25 | BLD-110, BLD-112 | R4 |
| BLD-115 | Spike | Bootstrap Godot 4 + gdext: blindside-client builds a GDExtension on Windows and in CI | P0 | 3 | BLD-37 | — |
| BLD-116 | Spike | Specify the VM ISA, register file, and per-tick evaluation model | P0 | 2 | BLD-114 | R4 |
| BLD-117 | Spike | Decide where Policy lives and what compiled artifact the sim executes | P0 | 1 | BLD-116, BLD-114 | — |
| BLD-118 | Spike | Record the designer's decision on rung three text authoring | P3 | 0.5 | BLD-117, BLD-114 | R7 |
| BLD-119 | Story | Implement the blindside-vm interpreter: opcodes, fixed Fx register file, golden tests | P0 | 4 | BLD-116, BLD-114 | R4 |
| BLD-120 | Story | Enforce VmBudget per tick, sourced from content data, and prove the sandbox | P0 | 2 | BLD-119, BLD-114 | R4 |
| BLD-121 | Story | blindside-behavior: BtNode, Policy, NodeId, PolicyRef, AuthorRef with schema and validation | P0 | 3 | BLD-117, BLD-114 | — |
| BLD-122 | Story | Define the benchmark set and add harness bench | P0 | 2 | BLD-117, BLD-108, BLD-114 | R5 |
| BLD-123 | Story | VM host interface: predicate and action call-outs over Belief only, compile-fail test | P0 | 3 | BLD-117, BLD-119, BLD-114 | — |
| BLD-124 | Story | Bring VM state under the state hash; injected VM non-determinism caught by the canary | P0 | 1.5 | BLD-123, BLD-33, BLD-114 | R4 |
| BLD-125 | Story | Compile behavior trees directly to bytecode with no text intermediate | P0 | 4 | BLD-119, BLD-123, BLD-121, BLD-114 | R4 |
| BLD-126 | Story | Policy schema migration chain with historical fixtures; Deprecated predicates load and run | P1 | 2 | BLD-121, BLD-114 | — |
| BLD-127 | Story | Graph diff of two versions of the same tree (gate criterion 2) | P0 | 3 | BLD-121, BLD-114 | — |
| BLD-128 | Story | Execution trace capture: nodes fired, order, predicate values vs thresholds | P1 | 3 | BLD-123, BLD-125, BLD-114 | R3 |
| BLD-129 | Story | Demonstration trace recorder: Belief-derived predicate values and actions per tick | P1 | 2 | BLD-123, BLD-114 | R2 |
| BLD-130 | Story | Score the hand-written reference policy on the benchmark and commit the baseline | P0 | 1.5 | BLD-122, BLD-123, BLD-114 | R5 |
| BLD-131 | Story | Editor FFI surface: vocabulary, policy load/save/validate/compile, diff, trace, bench | P0 | 3 | BLD-115, BLD-121, BLD-125, BLD-127, BLD-128, BLD-114 | — |
| BLD-132 | Story | Node editor: build trees from the vocabulary in Godot | P0 | 5 | BLD-131, BLD-114 | R5 |
| BLD-133 | Story | Collapse, expand, and subtree extraction into a Subtree policy | P1 | 3 | BLD-132, BLD-114 | R7 |
| BLD-134 | Story | Flag Deprecated predicates and render graph diffs in the editor | P1 | 2 | BLD-132, BLD-126, BLD-127, BLD-114 | — |
| BLD-135 | Story | Live trace readout in the editor: run on a benchmark seed, scrub, light the fired branch | P1 | 3 | BLD-132, BLD-128, BLD-122, BLD-114 | R3 |
| BLD-136 | Spike | Design the induction port from Phase 2 findings; settle how demonstrations exist in Phase 4 | P1 | 2 | BLD-121, BLD-114 | R2 |
| BLD-137 | Story | blindside-induct: traces to Policy via segmentation, separator induction, threshold fitting | P1 | 5 | BLD-136, BLD-129, BLD-114 | R2 |
| BLD-138 | Story | Plain-sentence rendering of a tree and the active-learning query surface | P2 | 2 | BLD-121, BLD-137, BLD-114 | R2 |
| BLD-139 | Story | Author the node challenger in the editor and run the Phase 4 gate benchmark | P0 | 4 | BLD-130, BLD-132, BLD-133, BLD-134, BLD-135, BLD-127, BLD-124, BLD-114 | R5 |
| BLD-140 | Task | Record Phase 4 decisions and reconcile ARCHITECTURE with the code | P1 | 1 | BLD-139, BLD-137, BLD-114 | — |

### BLD-114 — Phase 4 gate-entry: confirm the Phase 3 gate result and the policy-driver decision before VM code

**Status:** Backlog  ·  **Task**  ·  P0  ·  0.25 d  ·  depends on BLD-110, BLD-112  ·  retires R4

CLAUDE.md: do not start a phase whose predecessor's gate has not been met. The Phase 4 epic's can_start_when names the Phase 3 gate, but in the draft plan BLD-119 (the blindside-vm interpreter, a constrained crate) depended only on BLD-116, a docs spike with no dependencies, so the graph allowed VM code before BLD-110. This story is the anchor. It also records what drove agents in Phase 3 (the BLD-62 decision), which BLD-117 turns into the real VM, so that Phase 3's recorded MatchRecords are not silently invalidated, and it is the place a designer sign-off to pull BLD-115 (Godot bootstrap) forward is recorded, if one is given. Human-gated (designer 'proceed' on the Phase 3 report): expect about 3 calendar days and 1 round-trip(s) with the designer or testers beyond the 0.25 working days of work.

Done when:
- [ ] Link to the BLD-110 readiness report with the designer's dated 'proceed'; the report is not described as 'gate met'
- [ ] BLD-112's reconciled ARCHITECTURE.md is the version BLD-116 and BLD-117 read from; the BLD-62 policy-driver decision is quoted here
- [ ] Any designer sign-off to start BLD-115 before this story is recorded here with its date; absent that, BLD-115 waits for this story
- [ ] A one-line script over docs/dev-plan.json confirms every Phase 4 story except BLD-115 lists this story in depends_on

### BLD-115 — Bootstrap Godot 4 + gdext: blindside-client builds a GDExtension on Windows and in CI

**Status:** Backlog  ·  **Spike**  ·  P0  ·  3 d  ·  depends on BLD-37

The node editor is 'in Godot' (ROADMAP Phase 4), one phase before the client, so blindside-client must exist now as a GDExtension built from Rust with GDScript for UI (ARCHITECTURE client section: do not write the whole client in Rust). Toolchain risk is real on a Windows primary dev machine: Godot 4 and gdext API churn, three-platform builds, and load-time failures that show nothing. This is the only Phase 4 story with no sim dependency; the designer may choose to pull it into late Phase 3 with explicit sign-off, recorded in BLD-114; without that recorded sign-off it does not start before BLD-114. It extends the BLD-29 crate list so feature unification cannot enable diagnostics in the client build. Human-gated (Godot toolchain bootstrap): expect about 7 calendar days and 0 round-trip(s) with the designer or testers beyond the 3 working days of work.

Done when:
- [ ] Godot 4.x and gdext versions are pinned and recorded; a rust-toolchain-compatible build is documented in docs/CLIENT-TOOLCHAIN.md
- [ ] blindside-client builds a shared library that a checked-in Godot project loads on Windows, and one GDScript call into Rust returns a value
- [ ] CI builds the extension on Linux, macOS, and Windows (load test on Windows at minimum)
- [ ] blindside-client is exempt from the determinism lint but a dependency check proves it has no path to blindside-sim's world module types

### BLD-116 — Specify the VM ISA, register file, and per-tick evaluation model

**Status:** Backlog  ·  **Spike**  ·  P0  ·  2 d  ·  depends on BLD-114  ·  retires R4

ROADMAP Phase 4 gives only '~30 opcodes, fixed register file, hard instruction budget per tick' and ARCHITECTURE gives VmBudget and BtNode; the opcode list, register count, whether registers persist across ticks (i.e. whether they are the policy's only memory), what happens when the budget runs out mid-evaluation, and how Sequence/Selector/Guard/Act map onto ops are all unspecified. CLAUDE.md says ask rather than invent, so this spike produces a one-page ISA doc with each of those answered by the designer, not guessed. Recommendation to bring to the designer: registers persist across ticks and are therefore hashed; each tick restarts at pc 0 with the budget reset; budget exhaustion means no new action this tick and the last MotorCmd holds. Bytecode is Fx-only per DETERMINISM.md because blindside-vm is a constrained crate. Human-gated (designer confirms the ISA): expect about 7 calendar days and 2 round-trip(s) with the designer or testers beyond the 2 working days of work.

Done when:
- [ ] docs/VM-ISA.md exists listing every opcode (target ~30, hard cap 32) with operand encoding and its cost in budget units
- [ ] Register file size, element type (Fx), and persistence-across-ticks are decided and recorded, with the consequence for the state hash stated
- [ ] Budget-exhaustion behaviour is decided and recorded (what the agent does that tick)
- [ ] Each BtNode kind (Sequence, Selector, Guard, Act, Subtree) is shown as the op sequence it compiles to
- [ ] Every decision in the doc is marked designer-confirmed or open; no interpreter code is written during the spike

### BLD-117 — Decide where Policy lives and what compiled artifact the sim executes

**Status:** Backlog  ·  **Spike**  ·  P0  ·  1 d  ·  depends on BLD-116, BLD-114

ARCHITECTURE's Policy holds both BtNode (behavior crate) and Op (vm crate), but blindside-sim may depend only on blindside-vm and blindside-content, so the sim cannot consume Policy; it must consume a compiled artifact. Phase 3 ran its 1,000-match gate on whatever the designer chose then (hand-written Rust policies or a minimal VM pulled forward); this spike records how that seam becomes the real VM without changing Phase 3's replays silently. It also fixes the owner and signature of Policy::evaluate, which ARCHITECTURE names in the compile-time test but never defines. Recommendation: CompiledPolicy { schema, bytecode, budget, policy_hash } in blindside-vm; Policy in blindside-behavior; Sim::new takes compiled artifacts resolved from PolicyRef by the harness/net. Human-gated (designer decision on Policy placement): expect about 3 calendar days and 1 round-trip(s) with the designer or testers beyond the 1 working days of work.

Done when:
- [ ] Written decision names the crate and shape of the compiled artifact the sim executes, and confirms blindside-sim's dependency list is unchanged (vm + content only)
- [ ] PolicyRef -> policy_hash verification rule is written: the harness refuses to run a MatchRecord whose resolved policy bytes do not hash to the recorded ref
- [ ] Policy::evaluate's owning crate and signature are recorded so the compile-fail test in BLD-123 has a concrete target
- [ ] A migration note states what happens to Phase 3's hand-written policies and their recorded MatchRecords (kept as a reference policy in BLD-130, or retired with reason)
- [ ] ARCHITECTURE.md updated or a decision note committed; every unresolved item listed as open

### BLD-118 — Record the designer's decision on rung three text authoring

**Status:** Backlog  ·  **Spike**  ·  P3  ·  0.5 d  ·  depends on BLD-117, BLD-114  ·  retires R7

DESIGN names a third authoring rung: 'Real text authoring, in a small purpose-built language, for the players who go deep. This is the redstone tier: used by a small fraction of players, responsible for most of what the game becomes famous for, and the source of nearly everything worth selling on the market.' ROADMAP Phase 4 says the tree compiles directly to bytecode with no text intermediate, and BLD-125 adds a test that no parser for policies exists on the compiler path, so without a recorded decision the plan forecloses rung three. Ask whether rung three is dead, deferred to a named phase, or a separate front-end that compiles to the same Policy artifact, and scope BLD-125's test accordingly. Human-gated (rung-three decision): expect about 3 calendar days and 1 round-trip(s) with the designer or testers beyond the 0.5 working days of work.

Done when:
- [ ] A decision recorded in docs with the designer's name: rung three is cut, deferred to a named phase, or planned as a front-end producing the same Policy schema with provenance
- [ ] If deferred, the constraint that it must never become the primary path and is unreachable in a first session (DESIGN onboarding rule) is written next to it
- [ ] BLD-125's no-parser test is scoped to the compiler and VM, or kept as-is if rung three is cut; the choice is stated in the test's doc comment
- [ ] Nothing is built

### BLD-119 — Implement the blindside-vm interpreter: opcodes, fixed Fx register file, golden tests

**Status:** Backlog  ·  **Story**  ·  P0  ·  4 d  ·  depends on BLD-116, BLD-114  ·  retires R4

Build the interpreter exactly as docs/VM-ISA.md specifies: an Op enum, a fixed register file of Fx, program counter and flags, and one run-tick entry point. DETERMINISM.md applies to blindside-vm, so no f32/f64, no HashMap iteration, no std::time, no rand, no unsafe, and no platform math. Every opcode gets a unit test, and golden execution vectors are checked in and compared across the three CI platforms so R4 is exercised inside the VM before any policy runs in a match.

Done when:
- [ ] Every opcode in docs/VM-ISA.md is implemented and no opcode outside it exists (test enumerates the Op enum against the doc)
- [ ] cargo test -p blindside-vm passes on Linux, macOS, and Windows; golden execution traces are bit-identical across the three
- [ ] Determinism lint passes on blindside-vm; #![deny(unsafe_code)] at the crate root
- [ ] The per-tick execution path performs no heap allocation (fixed arrays; verified by a counting-allocator test or by construction with a documented argument)
- [ ] Malformed bytecode (bad register index, jump out of range, unknown opcode) returns a typed error at load or step, never panics

### BLD-120 — Enforce VmBudget per tick, sourced from content data, and prove the sandbox

**Status:** Backlog  ·  **Story**  ·  P0  ·  2 d  ·  depends on BLD-119, BLD-114  ·  retires R4

ARCHITECTURE: VmBudget { ops_per_tick } is 'also a balance lever', so the number must come from loadout/content data and be covered by the content hash, not be a constant. DESIGN: user code cannot hang, crash, or escape; the instruction budget is what guarantees that. On exhaustion the interpreter halts deterministically with the behaviour decided in BLD-116, identical on every platform.

Done when:
- [ ] Infinite-loop bytecode terminates within ops_per_tick ops on every tick, and the agent's observable result on exhaustion matches the BLD-116 decision (golden test on all three platforms)
- [ ] ops_per_tick is read from a content entry (chassis or module — designer decides where) and appears in the MatchRecord loadout; changing it changes the content hash
- [ ] Property test: 10,000 random bytecode programs never panic, never exceed the budget, and never read or write outside the register file
- [ ] Budget accounting is per agent per tick and resets each tick; a test with two agents on different budgets shows each halting at its own limit

### BLD-121 — blindside-behavior: BtNode, Policy, NodeId, PolicyRef, AuthorRef with schema and validation

**Status:** Backlog  ·  **Story**  ·  P0  ·  3 d  ·  depends on BLD-117, BLD-114

Define the tree per ARCHITECTURE — Sequence, Selector, Guard { pred, params: SmallVec<[Fx; 4]>, child }, Act { action, params }, Subtree { source: PolicyRef } — and Policy { schema, root, nodes, bytecode, author, provenance }. Serialization reuses the format chosen in Phase 0 for MatchRecord with Fx written as raw bits, never through a float. A validator rejects malformed trees before they reach the compiler so every downstream error is a validation message at a node, not a panic.

Done when:
- [ ] Types compile in blindside-behavior and a fixture Policy serializes and deserializes byte-identically on all three platforms
- [ ] Validator rejects: cycles, dangling NodeIds, missing root, Guard param count not matching the predicate's vocabulary entry, unknown PredicateId/ActionId not in the registry or retired ledger, Subtree self-reference
- [ ] schema: u16 is written on save and checked on load; an unknown or future schema is a hard error, never silently accepted
- [ ] AuthorRef and provenance are populated on creation and provenance is append-only (a test shows salvage/extraction appends rather than replaces)

### BLD-122 — Define the benchmark set and add harness bench

**Status:** Backlog  ·  **Story**  ·  P0  ·  2 d  ·  depends on BLD-117, BLD-108, BLD-114  ·  retires R5

The gate compares two policies 'on the benchmark set', which no document defines, and Phase 9's listing auto-evaluation reuses it. Ask the designer for the size, biome, loadout, mode, and metric; recommendation: a fixed list of seeds (e.g. 100) in the single Phase 3 biome, the Surveyor loadout, extraction-mode score plus success rate. BLD-108 already created docs/BENCHMARK.md and a harness batch over the benchmark seed set; this story extends that one file and one runner (metric, version hash, `harness bench`) rather than creating a second. It runs through the Phase 0 batch executor, parallel across matches only, so results are bit-identical across platforms and cheap to repeat. Human-gated (benchmark definition confirmed): expect about 3 calendar days and 1 round-trip(s) with the designer or testers beyond the 2 working days of work.

Done when:
- [ ] docs/BENCHMARK.md lists the seeds, biome, loadout, mode, and metric, marked designer-confirmed
- [ ] harness bench <compiled-policy> runs the set and prints per-seed score, aggregate score, success rate, and final hashes
- [ ] Output is identical on Linux, macOS, and Windows in CI for the same policy
- [ ] The set carries a version hash so a changed benchmark cannot be compared to an old score without the mismatch being reported

### BLD-123 — VM host interface: predicate and action call-outs over Belief only, compile-fail test

**Status:** Backlog  ·  **Story**  ·  P0  ·  3 d  ·  depends on BLD-117, BLD-119, BLD-114

The VM must invoke predicates (Predicate::eval(&Belief, params) per ARCHITECTURE) and emit actions by stable PredicateId/ActionId resolved against the content registries; the host trait is implemented by the sim and is the seam a hardware runtime would implement later (ARCHITECTURE hardware-readiness section). blindside-vm must be unable to name World. This story also lands the Policy::evaluate variant of the compile-time test ARCHITECTURE asks for, now that the type exists per BLD-117.

Done when:
- [ ] A host trait (e.g. VmHost { eval_predicate(&self, PredicateId, &[Fx]) -> bool; emit_action(&mut self, ActionId, &[Fx]) }, or the designer-approved equivalent) is defined in blindside-vm and implemented in blindside-sim over &Belief and the registries
- [ ] Unknown PredicateId/ActionId is rejected at policy load/validation, never at runtime; retired IDs resolve to Deprecated evaluating to the ledger's fixed value (ARCHITECTURE rule 1)
- [ ] trybuild compile-fail tests prove that code inside blindside-vm and code on the Policy::evaluate path cannot obtain &World or any type from world.rs
- [ ] The desync canary passes on all three platforms with VM-driven agents in the loop
- [ ] Action emission produces the same actuator request type Phase 3's hand-written policies produced, so locomotion code is unchanged

### BLD-124 — Bring VM state under the state hash; injected VM non-determinism caught by the canary

**Status:** Backlog  ·  **Story**  ·  P0  ·  1.5 d  ·  depends on BLD-123, BLD-33, BLD-114  ·  retires R4

If registers persist across ticks (BLD-116) they affect future ticks, and PHASE-0-HARNESS.md says the hash must cover everything that does and nothing that does not. Add per-agent VM state to Sim::state_hash in stable AgentId order with a mutation test, and add a VM-specific injected non-determinism fixture so the canary is proven to catch a VM bug and not only a sim bug ('a canary that does not catch a known bug is worse than none'). Re-run the Phase 3 gate mechanism with the VM in the loop and record the throughput cost.

Done when:
- [ ] Mutating any agent's VM register or pc changes Sim::state_hash(); the hash coverage doc comment lists VM state as included
- [ ] A feature-gated fixture that makes one VM op depend on HashMap iteration order is caught by the canary within the tick it occurs (CI job expects failure)
- [ ] 1,000 VM-driven matches via harness batch produce identical final hashes on Linux/macOS/Windows
- [ ] Ticks/second with VM-driven agents measured and recorded next to the Phase 3 number; if 1,000 matches no longer fit in 10 minutes the regression is reported, not hidden

### BLD-125 — Compile behavior trees directly to bytecode with no text intermediate

**Status:** Backlog  ·  **Story**  ·  P0  ·  4 d  ·  depends on BLD-119, BLD-123, BLD-121, BLD-114  ·  retires R4

ROADMAP Phase 4: 'direct compilation to bytecode (no text intermediate)' — the compiler emits Op values; there is no assembler and no parser anywhere in the pipeline. Subtree { source } resolves the referenced Policy, inlines its bytecode, and appends its provenance chain; the compiled op count is reported against VmBudget so an author knows before a match whether the tree fits. A test-only tree-walking interpreter over the same BtNode types is the oracle: on randomized trees and Belief fixtures the VM must make the same decision as the walker.

Done when:
- [ ] compile(&Policy, &Registry) -> Result<CompiledPolicy, CompileError> exists and every BtNode kind compiles
- [ ] Differential test over at least 1,000 random trees x fixture beliefs: VM decision equals the tree-walker decision, on all three platforms
- [ ] Subtree inlining appends the referenced policy's provenance and the compiled policy_hash changes when the referenced policy changes
- [ ] Compiled op count is reported and compared against the loadout's VmBudget with a clear over-budget error
- [ ] A grep/test asserts the compiler and VM contain no text intermediate (no FromStr, parser or assembler on the tree-to-bytecode path); its scope follows the BLD-118 rung-three decision so a separate text front-end producing the same Policy schema is not foreclosed; a read-only disassembler for diagnostics is permitted and marked as such

### BLD-126 — Policy schema migration chain with historical fixtures; Deprecated predicates load and run

**Status:** Backlog  ·  **Story**  ·  P1  ·  2 d  ·  depends on BLD-121, BLD-114

ARCHITECTURE rule 3: schema-version every serialized policy with a migration path ('you will change the node format'); rule 1: retired predicates become Deprecated, evaluate to a fixed value, and a season-1 policy must parse in season 6. Keep one fixture per historical schema and prove each migrates to current, and prove a policy referencing a retired PredicateId still loads, compiles, and runs with the ledger's fixed value. Editor flagging lands in BLD-134.

Done when:
- [ ] migrate(policy) walks a chain v_n -> v_{n+1} -> current (identity for the first schema) and is exercised by a test
- [ ] A fixtures directory holds one Policy per historical schema; a test migrates each to current and compares to a checked-in expected result
- [ ] A fixture policy referencing a retired PredicateId loads, compiles, and its Guard evaluates to the value recorded in the retired-ID ledger
- [ ] The PR template gains a checkbox: schema bumped if serialized Policy fields changed, with a fixture added for the previous schema

### BLD-127 — Graph diff of two versions of the same tree (gate criterion 2)

**Status:** Backlog  ·  **Story**  ·  P0  ·  3 d  ·  depends on BLD-121, BLD-114

Second half of the Phase 4 gate. The diff must identify added, removed, moved, and changed nodes (param edits and Subtree source changes included) between two versions and print a readable delta; corrections and market versioning depend on it later. Node identity across edits is undecided in ARCHITECTURE — NodeId indexes nodes: Vec<BtNode>, and Vec indices shift on delete — so ask the designer; recommendation: NodeIds are stable handles never reused within a policy's lineage, mirroring the never-reuse-a-retired-ID rule, with structural matching as the fallback for freshly created subtrees. Human-gated (node-identity decision and designer read of a delta): expect about 5 calendar days and 1 round-trip(s) with the designer or testers beyond the 3 working days of work.

Done when:
- [ ] Node identity semantics decided with the designer and recorded in docs (and the editor in BLD-132 preserves them on save)
- [ ] diff(&Policy, &Policy) -> Delta lists added, removed, moved, and changed nodes with old and new values; the delta of a tree with itself is empty
- [ ] Patch round-trip: applying diff(a, b) to a reproduces b for at least 200 randomized edit sequences
- [ ] harness diff a.policy b.policy prints a human-readable delta
- [ ] The designer reads the delta of two saved challenger versions from BLD-139 and names the edits correctly without explanation

### BLD-128 — Execution trace capture: nodes fired, order, predicate values vs thresholds

**Status:** Backlog  ·  **Story**  ·  P1  ·  3 d  ·  depends on BLD-123, BLD-125, BLD-114  ·  retires R3

ROADMAP Phase 4: 'which nodes fired, in what order, on what predicate values'. Phase 1's Policy.decision_report is the rehearsal and proved the useful shape: per node an answer, the live value against its threshold as a fill ratio, active, and fired — a bar creeping toward its threshold shows what the machine is about to decide seconds before it does. The trace is derived from Belief and VM state only, is not part of the state hash, and is regenerated by re-running a MatchRecord rather than stored in it (replays stay kilobytes).

Done when:
- [ ] Per tick per agent the VM emits an ordered list of (NodeId, fired, predicate value(s), threshold param, ratio) for every node evaluated that tick
- [ ] Trace construction has no reference to World (module privacy plus a test), and enabling tracing changes neither the state hash nor the match outcome
- [ ] Re-running the same MatchRecord with tracing on yields a byte-identical trace on all three platforms
- [ ] harness trace <record> --agent <id> --tick <n> prints the trace; a whole-match trace can be written to a file
- [ ] Ticks/second measured with and without tracing and recorded

### BLD-129 — Demonstration trace recorder: Belief-derived predicate values and actions per tick

**Status:** Backlog  ·  **Story**  ·  P1  ·  2 d  ·  depends on BLD-123, BLD-114  ·  retires R2

Induction needs, per tick for one agent, the Belief-derived predicate values (or a Belief snapshot) and the action taken, whether the agent is driven by a policy (the Phase 4 teacher) or later by a human in the Phase 5 client. Belief only, per the invariant. The trace is a derived output regenerated from a MatchRecord, not stored inside it, so replays stay kilobytes.

Done when:
- [ ] harness demo-record <record> --agent <id> --out <trace> writes a schema-versioned trace
- [ ] The trace contains only Belief-derived fields, the action id, and params; a test asserts no World-derived field is present
- [ ] Re-running the same MatchRecord yields a byte-identical trace on all three platforms
- [ ] A trace for a full 9,600-tick match stays under a size stated in the format doc

### BLD-130 — Score the hand-written reference policy on the benchmark and commit the baseline

**Status:** Backlog  ·  **Story**  ·  P0  ·  1.5 d  ·  depends on BLD-122, BLD-123, BLD-114  ·  retires R5

Gate criterion 1 needs a baseline. 'Hand-written' is not defined in ROADMAP: it is most plausibly the policy that drove Phase 3's 1,000-match gate (hand-written Rust against the Predicate/Action traits) or a tree composed by hand in code; the designer confirms which counts. The score and MatchRecords are committed so the challenger's win is reproducible from a clean checkout. Human-gated (hand-written definition confirmed): expect about 2 calendar days and 1 round-trip(s) with the designer or testers beyond the 1.5 working days of work.

Done when:
- [ ] The designer's definition of hand-written is recorded in docs/BENCHMARK.md
- [ ] The reference policy runs via harness bench; per-seed results, aggregate score, and MatchRecords are committed under docs/benchmark/ (or the designated artifacts location)
- [ ] The reference score reproduces from a clean checkout on all three platforms
- [ ] The reference policy is not edited again during Phase 4 (its policy_hash is recorded)
- [ ] The reference policy's ping rule reads at least one contact predicate ('contact heard within N s' or 'best contact quality >= theta'), or docs/BENCHMARK.md records that the Phase 2 vocabulary forbids it and that R5 therefore stays open; without this the gate can be won on ping cadence alone (PHASE-1-OPEN-QUESTIONS Part 4 panel finding)

### BLD-131 — Editor FFI surface: vocabulary, policy load/save/validate/compile, diff, trace, bench

**Status:** Backlog  ·  **Story**  ·  P0  ·  3 d  ·  depends on BLD-115, BLD-121, BLD-125, BLD-127, BLD-128, BLD-114

ARCHITECTURE: 'the FFI boundary is a feature ... make it awkward to pass ground truth.' The editor needs only the predicate/action vocabulary (ids, names, param counts and ranges, Deprecated entries), Policy load/save/validate/compile, graph diff, trace retrieval, and a way to trigger a headless bench run. Every export is named and typed; nothing derived from World crosses, and a test enforces it so the year-two convenience accessor is caught.

Done when:
- [ ] All exported FFI functions are declared in one file with their argument and return types
- [ ] A test enumerates the exports and fails if any type from blindside-sim's world module (or any World-derived export) appears
- [ ] The vocabulary export includes Deprecated entries with their fixed value and a deprecated flag
- [ ] A Policy loaded in GDScript and saved unchanged is byte-identical; a changed one validates through the same validator as the harness
- [ ] bench and trace are invoked headless from GDScript and return plain data (scores, per-tick node records)

### BLD-132 — Node editor: build trees from the vocabulary in Godot

**Status:** Backlog  ·  **Story**  ·  P0  ·  5 d  ·  depends on BLD-131, BLD-114  ·  retires R5

ROADMAP Phase 4 'build'. DESIGN: behavior is built as a physical object, not typed, and nobody hits a text editor in their first session. GDScript UI (Godot's GraphEdit is a reasonable base) over the FFI: a palette from the vocabulary, placing Sequence/Selector/Guard/Act nodes, ordered child wiring, editing Fx params with units and ranges from the vocabulary entry, inline validation, save/load with schema, and a compile readout of op count against budget. Node identity on save follows the BLD-127 decision. Human-gated (authoring-surface decision and informal usability check): expect about 5 calendar days and 1 round-trip(s) with the designer or testers beyond the 5 working days of work.

Done when:
- [ ] A tree equivalent to the reference policy can be built with the mouse only, saved, and its compiled bytecode scores identically on the benchmark to the same tree compiled from a fixture
- [ ] Invalid trees show the validator's message at the offending node and cannot be compiled
- [ ] Params are edited and saved as Fx with no float round-trip in the saved file (byte-compare test)
- [ ] Load then save without edits preserves NodeIds and produces an empty diff
- [ ] A person who has not seen the editor builds a three-node tree without reading docs (informal check, outcome noted in the story)
- [ ] The designer's decision on in-world vs panel authoring (DESIGN: 'the assembly lives in the world rather than in a text buffer'; the named failure is 'an IDE with a viewport') is recorded before the scene is built; GraphEdit is acceptable only as the recorded choice

### BLD-133 — Collapse, expand, and subtree extraction into a Subtree policy

**Status:** Backlog  ·  **Story**  ·  P1  ·  3 d  ·  depends on BLD-132, BLD-114  ·  retires R7

ROADMAP Phase 4 lists collapse/expand and subtree extraction; the extracted Subtree { source: PolicyRef } is 'the unit of sale' (ARCHITECTURE) and is how a purchased behavior slots into a buyer's tree as a component (DESIGN). Extraction creates a new Policy with the current author and provenance, replaces the selection with a Subtree node, and the parent must still compile to bytecode that behaves identically.

Done when:
- [ ] Collapsing a subtree hides its children behind one node showing name, node count, and compiled op count; expand restores the exact structure (diff is empty)
- [ ] Extracting a selection saves a new Policy with author and appended provenance and replaces the selection with Subtree { source }
- [ ] The parent compiles before and after extraction to bytecode with identical benchmark scores
- [ ] A Subtree whose source is missing is visibly flagged and blocks compile with a message naming the missing PolicyRef

### BLD-134 — Flag Deprecated predicates and render graph diffs in the editor

**Status:** Backlog  ·  **Story**  ·  P1  ·  2 d  ·  depends on BLD-132, BLD-126, BLD-127, BLD-114

ARCHITECTURE rule 1: retired predicates are 'flagged in the editor'. Gate criterion 2 needs the diff to be usable, not only computable, and the correction loop and market versioning will need it visually later. Uses BLD-126's retired-ID fixture and BLD-127's delta.

Done when:
- [ ] The retired-ID fixture policy opens with its Deprecated node visibly marked and the fixed value it evaluates to shown
- [ ] The editor loads two versions of a policy and highlights added, removed, moved, and changed nodes from the BLD-127 delta
- [ ] The designer reads a highlighted diff of two challenger versions and names the change correctly without prompting

### BLD-135 — Live trace readout in the editor: run on a benchmark seed, scrub, light the fired branch

**Status:** Backlog  ·  **Story**  ·  P1  ·  3 d  ·  depends on BLD-132, BLD-128, BLD-122, BLD-114  ·  retires R3

To author a policy that beats the reference the author must see the policy think; Phase 1 showed the decision graph with live guard bars was what made the run readable. Minimal scope: run the current compiled policy on one benchmark seed headless via the FFI, scrub ticks, light the fired branch, and draw each guard's value-vs-threshold bar from BLD-128's trace. This is not the Phase 5 replay: no 3D, no truth layer, belief-derived trace only.

Done when:
- [ ] A run control executes the current compiled policy on a chosen benchmark seed headless and returns the trace to the editor
- [ ] A tick scrubber highlights fired nodes and shows guard value/threshold ratio bars, matching the harness trace output for the same tick
- [ ] Nothing rendered derives from World; the BLD-131 export test still passes
- [ ] A full-match trace (about 9,600 ticks at 20 Hz) loads and scrubs without stalling on the dev machine (under 2 s to load)

### BLD-136 — Design the induction port from Phase 2 findings; settle how demonstrations exist in Phase 4

**Status:** Backlog  ·  **Spike**  ·  P1  ·  2 d  ·  depends on BLD-121, BLD-114  ·  retires R2

ROADMAP Phase 4: 'port Phase 2's induction to produce these trees'; blindside-induct is 'demonstration traces -> behavior trees'. Phase 2 was throwaway Python, so this is a rewrite informed by its report, over the registered predicate vocabulary and Fx thresholds. Two things are unspecified and load-bearing: the demonstration trace format, and how a human demonstrates in Phase 4 when the client is Phase 5. Flag this gap to the designer with two options — (a) validate the port by teacher-policy recovery (synthetic demonstrations from a known tree) and defer human driving to Phase 5, or (b) a minimal drive mode in the Godot editor build — and record the choice. CLAUDE.md names demonstration-to-policy induction a known-weak area: report problems, do not force it. Human-gated (demonstration-source decision): expect about 5 calendar days and 1 round-trip(s) with the designer or testers beyond the 2 working days of work.

Done when:
- [ ] Written design covers trace format, changepoint segmentation, minimal-separator search over the vocabulary, threshold fitting over Fx, the active-learning query API, and output Policy provenance
- [ ] The demonstration-source decision (teacher recovery vs drive mode) is recorded with the designer's confirmation
- [ ] Every failure mode from the Phase 2 gate report is listed with how the port addresses it or that it remains open
- [ ] Designer decision recorded on whether blindside-induct joins the determinism lint scope; if not, BLD-137's cross-platform claim is reduced to 'Fx output, identical for identical traces on one platform'

### BLD-137 — blindside-induct: traces to Policy via segmentation, separator induction, threshold fitting

**Status:** Backlog  ·  **Story**  ·  P1  ·  5 d  ·  depends on BLD-136, BLD-129, BLD-114  ·  retires R2

Implement changepoint segmentation, minimal-separator predicate induction, and threshold fitting per BLD-136 over recorded (Belief-derived predicate values, action) traces, producing a Policy with a BtNode tree, author = demonstrator, and provenance. 'No consistent separator' is reported explicitly so the active-learning query can fire. Validation is teacher recovery: demonstrations generated by a known tree on benchmark seeds must yield a policy that matches the teacher on unseen seeds at the Phase 2 threshold; a shortfall is written up as R2 evidence rather than papered over.

Done when:
- [ ] induce(&[Trace], &Vocabulary) -> Result<Policy, NoSeparator> exists; NoSeparator carries the conflicting trace points
- [ ] 3 teacher demonstrations produce a policy that succeeds on at least 70% of unseen benchmark seeds (success per docs/BENCHMARK.md), or the shortfall and its cause are written up as a design problem
- [ ] The induced Policy validates, compiles, and runs through harness bench
- [ ] Fitted thresholds are Fx; they are asserted bit-identical across Linux/macOS/Windows only if BLD-136 put blindside-induct under the determinism lint, otherwise the assertion is identical output for identical traces on one platform (no unenforced cross-platform claim)
- [ ] blindside-induct has no path to World (dependency and grep test)

### BLD-138 — Plain-sentence rendering of a tree and the active-learning query surface

**Status:** Backlog  ·  **Story**  ·  P2  ·  2 d  ·  depends on BLD-121, BLD-137, BLD-114  ·  retires R2

Two Phase 2 requirements carried forward: the inferred policy rendered as one plain sentence, and an active-learning query when no consistent separator exists. The sentence generator lives in blindside-behavior so both the editor and induct can use it; the query surface constructs a situation from the conflicting trace points and asks which action, and in Phase 4 the asker is a harness CLI prompt (the client will host it later). Human-gated (designer reads the sentence): expect about 1 calendar days and 1 round-trip(s) with the designer or testers beyond the 2 working days of work.

Done when:
- [ ] sentence(&Policy, &Vocabulary) -> String yields one sentence for the three-predicate fixtures and for the challenger tree
- [ ] The designer reads the sentence for a policy and correctly predicts its next decision on a benchmark seed (checked against the trace)
- [ ] When induce returns NoSeparator, the harness prints the conflicting situations, accepts an answer that becomes an additional trace, and induce then succeeds on the fixture

### BLD-139 — Author the node challenger in the editor and run the Phase 4 gate benchmark

**Status:** Backlog  ·  **Story**  ·  P0  ·  4 d  ·  depends on BLD-130, BLD-132, BLD-133, BLD-134, BLD-135, BLD-127, BLD-124, BLD-114  ·  retires R5

The gate: a policy authored entirely in nodes beats the hand-written reference on the benchmark set, and graph diff works on two versions of the same tree. Author the challenger in the editor only (no hand-edited bytes), iterate using the trace readout, save at least two versions, diff them, and run both policies through harness bench on all three platforms. Report 'ready for gate' with the numbers and a list of every guessed value; do not report the gate as met (CLAUDE.md). If the challenger cannot win, say which vocabulary or editor limitation blocked it — that is R5 evidence — instead of changing the benchmark. Human-gated (gate challenger authored by the designer): expect about 10 calendar days and 1 round-trip(s) with the designer or testers beyond the 4 working days of work.

Done when:
- [ ] The challenger Policy was saved from the editor with author and provenance; its policy_hash matches an editor save and no manual byte edits exist
- [ ] harness bench shows the challenger's aggregate score above the reference on the full benchmark set, identical on Linux/macOS/Windows; MatchRecords for both are attached
- [ ] harness diff of two saved challenger versions lists exactly the edits made (compared against the editor's own change log)
- [ ] The Phase 4 report lists every guessed value and states readiness, not that the gate is met
- [ ] If the challenger loses, the report names the blocking vocabulary or editor limitation and the benchmark is unchanged

### BLD-140 — Record Phase 4 decisions and reconcile ARCHITECTURE with the code

**Status:** Backlog  ·  **Task**  ·  P1  ·  1 d  ·  depends on BLD-139, BLD-137, BLD-114

CLAUDE.md's definition of done requires anything guessed at to be listed explicitly. Fold the ISA, Policy placement, node identity semantics, budget-exhaustion semantics, execution and demonstration trace formats, and the benchmark definition into docs, and update ARCHITECTURE's Policy/BtNode section where the designer changed anything. ROADMAP's deadwater-* crate names are left alone; renaming is not work.

Done when:
- [ ] docs/VM-ISA.md, docs/BENCHMARK.md, and ARCHITECTURE.md agree with the code (spot-checked against the Op enum, Policy struct, and bench output)
- [ ] Every item marked open in BLD-116, BLD-117, BLD-127, and BLD-136 is either closed with the designer's answer or listed as open in the epic summary
- [ ] The epic summary lists every guessed value and reports readiness for the gate, not that the gate was met

## BLD-141 — Client and replay — Godot 4 via GDExtension

**Phase Phase 5 — Client and replay.** Build the real client on the Phase 3 sim and Phase 4 VM: a 3D renderer for one generated biome and the Surveyor chassis, a belief-only operator view that is the Phase 1 layout grown up (decision graph left, map centre, timeline bottom, fix eased over 0.7 s), the replay screen with truth and belief drawn together — ROADMAP calls it 'the most important screen in the game' — enter-agent-perception mode, and failure-attribution heuristics. The FFI is treated as the third enforcement point of the one invariant: only named Belief-derived types cross it, and ground truth reaches the client through exactly one sanctioned replay/spectator export (the ReplayFrame designed and signed off in BLD-76) that the live run-phase scene cannot import. Three things are flagged rather than built around: (1) ARCHITECTURE says World never reaches the renderer while ROADMAP/DESIGN require the replay to draw truth — BLD-76 recorded the designer's sign-off and BLD-145 only consumes it on the client side; (2) automatic failure attribution is a known-weak area per CLAUDE.md, so it is a spike before a story; (3) the Phase 1 gate configuration — the judged sonar viewing (player sonar, rival sonar), with the lidar viewing logged separately — must be reproduced exactly or the Phase 5 score is not comparable. Human-gated stories in this epic: 8 of 18 (1 designer decisions or reviews, 3 playtests or self-tests, 4 art, toolchain, CI or commercial), carrying at least 52 calendar days of latency on top of 75.5 working days.

- **Gate — pass:** Phase 1's spectator test, re-run in the real client with the preserved Phase 1 rubric and protocol (eight minutes, no explanation beyond 'you cannot drive it', Recall only, a player who has not seen the Python version), scores better than the Python version did. (ROADMAP Phase 5.)
- **Gate — kill:** ROADMAP states no kill line for Phase 5 beyond the universal rule: if the gate fails, Phase 6 does not start. Treat a score at or below the Phase 1 record as a kill — the client lost the tension the prototype had. Stop, diff the two views against the rubric item by item, and do not begin networking until the real client beats the Python record. Never report the gate as met; report the build ready for the gate.
- **Can start when:** The Phase 4 gate result has been produced and confirmed by the designer (a policy authored entirely in nodes beats a hand-written one on the benchmark set; graph diff works on two versions of the same tree), which implies the Phase 3 gate and the Phase 1 playtest record with its two-viewing rubric already exist; BLD-143 depends on BLD-139 to encode that. The walkers-vs-pods decision (BLD-142) should be raised during Phases 3-4 so it does not stall this phase.
- **Estimate:** 75.5 working days

| Key | Type | Summary | Pri | Days | Depends on | Risk |
|---|---|---|---|---|---|---|
| BLD-142 | Spike | Record the walkers-vs-pods decision before chassis art starts | P1 | 0.5 | BLD-100 | — |
| BLD-143 | Spike | Re-pin Godot 4 and gdext; audit what churned since the Phase 4 bootstrap | P0 | 2 | BLD-115, BLD-139 | — |
| BLD-144 | Story | Define the FFI surface as named Belief-derived snapshot types plus command submission | P0 | 4 | BLD-143, BLD-74, BLD-75 | — |
| BLD-145 | Story | Consume the sanctioned ReplayFrame export in the replay host only; keep the run-phase scene unable to import it | P0 | 2 | BLD-144, BLD-76 | — |
| BLD-146 | Story | Load, verify and scrub a MatchRecord in the client replay host | P0 | 4 | BLD-145, BLD-31, BLD-30 | — |
| BLD-147 | Story | Reproduce the Phase 1 beat sheet on the real sim as a MatchRecord fixture | P0 | 4 | BLD-146, BLD-139, BLD-108, BLD-106 | R1 |
| BLD-148 | Story | Render the one generated cave biome as a 3D truth layer for the replay | P1 | 6 | BLD-145 | — |
| BLD-149 | Story | Model and animate the Surveyor chassis with an honest silhouette and a sensor head | P1 | 8 | BLD-142 | — |
| BLD-150 | Story | Build the operator view point cloud in the estimated frame with smear, snap and overlays | P0 | 8 | BLD-144 | R1 |
| BLD-151 | Story | Drive directional audio from Belief with identical sound for honest and lying fixes | P1 | 3 | BLD-144 | R1 |
| BLD-152 | Story | Build the operator panels: live decision graph, timeline strip, belief-fact HUD | P0 | 5 | BLD-150, BLD-128 | R1 |
| BLD-153 | Spike | Design failure-attribution heuristics against a harness-generated wreck corpus | P1 | 2 | BLD-146 | R3 |
| BLD-154 | Story | Build the replay screen with truth and belief drawn together on one scrubbable timeline | P0 | 10 | BLD-146, BLD-148, BLD-149, BLD-150, BLD-152 | R3 |
| BLD-155 | Story | Add enter-agent-perception mode from any replay tick | P1 | 4 | BLD-154 | R3 |
| BLD-156 | Story | Give each interference and hazard event a distinct replay signature | P2 | 3 | BLD-154 | — |
| BLD-157 | Story | Present the causal chain of each loss in the replay with evidence per link | P1 | 6 | BLD-153, BLD-154 | R3 |
| BLD-158 | Task | Hold the frame budget with a full-match point cloud; warm up shaders before play | P2 | 2 | BLD-150, BLD-154 | — |
| BLD-159 | Story | Re-run the Phase 1 spectator test in the real client and score it against the Python record | P0 | 2 | BLD-150, BLD-152, BLD-151, BLD-154, BLD-155, BLD-147, BLD-158, BLD-14, BLD-5, BLD-16 | R1 |

### BLD-142 — Record the walkers-vs-pods decision before chassis art starts

**Status:** Backlog  ·  **Spike**  ·  P1  ·  0.5 d  ·  depends on BLD-100

DESIGN leaves 'Walkers versus hovering' open: walkers give gait-dependent noise, terrain interaction and skin value at real animation cost; a pod halves the art budget. GLOSSARY has already settled that modules are visible on the model and the silhouette is always honest, which roughly doubles module art either way. CLAUDE.md says ask rather than invent; this is the designer's call and it must be recorded before BLD-149 spends a week on a model that might be the wrong body. Ask during Phase 3 or 4 so it is settled by the time Phase 5 starts. Human-gated (walker-or-pod decision): expect about 3 calendar days and 1 round-trip(s) with the designer or testers beyond the 0.5 working days of work.

Done when:
- [ ] Designer's decision (walker or pod) recorded in DESIGN.html's open-decisions list or docs/ with the date
- [ ] If walker: the gait set the sim models (BLD-100) is listed so animation matches actual sim gaits
- [ ] If pod: the gait-noise mechanic in the Phase 3 sim is confirmed still meaningful or flagged as dead

### BLD-143 — Re-pin Godot 4 and gdext; audit what churned since the Phase 4 bootstrap

**Status:** Backlog  ·  **Spike**  ·  P0  ·  2 d  ·  depends on BLD-115, BLD-139

ARCHITECTURE fixes the client as 'Godot 4 via GDExtension with Rust bindings for the sim. GDScript for UI and glue'. The blindside-client crate was bootstrapped in Phase 4 for the node editor; by the time Phase 5 starts, a year of Godot and godot-rust API churn is likely (the risk register work flagged it). Before any client scene is written, re-pin exact Godot and gdext versions, rebuild the extension on all three platforms, and list every binding that broke. The output is a short note in the client crate README plus green CI, not new features. Human-gated (Godot toolchain re-pin): expect about 7 calendar days and 0 round-trip(s) with the designer or testers beyond the 2 working days of work.

Done when:
- [ ] Godot 4.x and gdext versions pinned exactly (engine version in project.godot, crate version with '=' in Cargo.toml) and recorded in blindside-client/README.md
- [ ] blindside-client builds and loads in the pinned Godot on Linux, macOS and Windows in CI; the Phase 4 node editor scene still opens
- [ ] A written list of every gdext/Godot API that changed since the Phase 4 bootstrap and how each was resolved
- [ ] Rust in blindside-client is confirmed limited to sim/replay hosting and FFI types; any rendering code found there is listed for removal in BLD-144

### BLD-144 — Define the FFI surface as named Belief-derived snapshot types plus command submission

**Status:** Backlog  ·  **Story**  ·  P0  ·  4 d  ·  depends on BLD-143, BLD-74, BLD-75

ARCHITECTURE: 'The FFI boundary is a feature: it enforces that the client can only see what is deliberately handed across. Make it awkward to pass ground truth.' This story makes that literal. The live sim host exposes only explicitly named snapshot types built from Belief (pose estimate with covariance, map points with placement tick and source, contact tracks, known beacons, inventory, self_report, ticks_since_fix, the fix history with jump and surprise that Phase 1 proved is the only belief-legal spoof tell) plus a per-tick Belief-derived event list for the timeline, and one input path: a command appended to MatchRecord as (Tick, TeamId, Command). There is no generic get-state accessor. A test enumerates the exported types and fails if anything from world.rs appears. Recall in Phase 5 is the only command; the rest of the command channel is Phase 6.

Done when:
- [ ] Every exported FFI type is defined in one module of blindside-client, built from Belief only, and documented with the Belief field it derives from
- [ ] A test enumerates the FFI exports and fails the build if any type from blindside-sim's world.rs (or any type carrying a true position) is reachable from the live-run host
- [ ] No function on the live-run host takes or returns &World, WorldView, ReplayFrame, or a whole Sim; the only truth path is the separate export in BLD-145
- [ ] Command submission accepts exactly (Tick, TeamId, Command), appends to the in-progress MatchRecord, and is the only client-to-sim input; a GDScript call with any other payload is a compile/load error, not a silent no-op
- [ ] Per-tick Belief event list (fix landed with jump and surprise, new contact, ping heard from bearing, cargo loaded, command delivered) is produced inside the sim from Belief transitions and crosses the FFI as data
- [ ] All scenes, cameras, overlays and panels are GDScript; Rust in the client is sim/replay hosting and FFI types only (grep test in CI)

### BLD-145 — Consume the sanctioned ReplayFrame export in the replay host only; keep the run-phase scene unable to import it

**Status:** Backlog  ·  **Story**  ·  P0  ·  2 d  ·  depends on BLD-144, BLD-76

BLD-76 designed the sanctioned truth export — ReplayFrame: true cave, true agent poses and trails, true beacon positions including the spoof, wrecks, ancient state, alongside each agent's Belief for the same tick — produced by the harness replay runner behind the diagnostics feature, and recorded the designer's sign-off on DESIGN's two-places reading ('Ground truth appears in exactly two places: the post-match replay ... and the spectator view'). This story does not re-decide any of that; it consumes the export on the client side so that the replay/spectator scene is the only importer, the live run-phase scene has no path to it, and the BLD-29 feature-unification guard covers blindside-client. Two stories owning the same invariant relaxation is how it gets improvised twice, so the sign-off and compile-fail criteria stay in BLD-76.

Done when:
- [ ] The client replay host consumes ReplayFrames from the BLD-76 harness runner (a MatchRecord re-run); the live-run host does not enable the diagnostics feature, and blindside-client is added to the BLD-29 crate list so `cargo tree -e features` proves it
- [ ] The run-phase Godot scene has no import path to ReplayFrame or the replay host; a CI grep over GDScript scenes fails if the run-phase scene references the replay host
- [ ] Belief and truth for one tick are drawn from one ReplayFrame, never from two runs; the replay scene reads the Belief half through the same BLD-144 snapshot types the live view uses
- [ ] No new sign-off or compile-fail test is added here; the story links BLD-76's recorded decision and its compile-fail cases

### BLD-146 — Load, verify and scrub a MatchRecord in the client replay host

**Status:** Backlog  ·  **Story**  ·  P0  ·  4 d  ·  depends on BLD-145, BLD-31, BLD-30

The replay is a re-run: MatchRecord is 'seed + input log + content pack hash' and 'Kilobytes. Re-runs the whole match' (ARCHITECTURE). The client replay host loads a record, refuses it on content_hash mismatch (PHASE-0-HARNESS: replays break silently without this), re-runs it through the sim, checks the final state hash against the recorded one, and yields a ReplayFrame per tick. Scrubbing to an arbitrary tick is re-run from the start or from periodic snapshots; at Phase 1's numbers (20 Hz, 8 minutes, ~9,600 ticks) a full re-run is well under a second in Rust, so snapshots are an optimisation to add only if measured necessary.

Done when:
- [ ] Loading a MatchRecord whose content_hash does not match the loaded content pack is a hard error shown in the client, not a warning
- [ ] A re-run whose final state hash differs from the recorded one is reported as a divergence with the tick, and the replay refuses to present itself as faithful
- [ ] Play, pause, step one tick, and seek to any tick; seek latency measured and recorded for a full-length match (Phase 1 sizing: ~9,600 ticks)
- [ ] The same MatchRecord fixture used by the harness verify command loads and scrubs in the client with identical per-tick hashes
- [ ] Seed and content hash are displayed on the replay screen and copyable (DESIGN: the seed is published after the match)

### BLD-147 — Reproduce the Phase 1 beat sheet on the real sim as a MatchRecord fixture

**Status:** Backlog  ·  **Story**  ·  P0  ·  4 d  ·  depends on BLD-146, BLD-139, BLD-108, BLD-106  ·  retires R1

The gate re-runs Phase 1's spectator test, so the real sim must reproduce the Phase 1 scenario: a cautious sonar player agent and an aggressive sonar rival — the judged viewing of the Phase 1 gate per PHASE-1-OPEN-QUESTIONS Part 4 ('two viewings, sonar first') — plus a lidar-player variant of the same seed for the sensor comparison (viewing two), at least one contact, an ambiguous detection that turns out to be an echo, a spoofed beacon placed by the rival through the BLD-106 action that the player's agent acts on, an ancient system that kills the rival on schedule, an eight-minute match with an extraction deadline, and Recall as the single command. Phase 1 scripted the echo and spoof; here they must come from real mechanisms (Phase 3 acoustic field, a rival beacon action) driven by Phase 4 node policies, so a seed search over the batch executor finds a seed in the one biome that yields all four beats in order. The chosen record is the gate fixture and the fixture for every replay story above.

Done when:
- [ ] Two node-authored policies (cautious, aggressive) reproduce the Phase 1 scripted behaviours over the Phase 3 predicate vocabulary, with the same sensor kit as the Phase 1 gate session: player sonar and rival sonar for the judged fixture, plus a player-lidar variant of the same seed for viewing two
- [ ] A harness batch search finds and records a seed in the shipped biome where a headless run logs contact, echo, spoof fix (surprise at least 10x), ancient kill and extraction deadline in that order within eight minutes
- [ ] Recall at at least one send time extracts with cargo, and at least one send time does not (Phase 1 lesson: success must be possible but not monotonic); the sweep table is checked in beside the fixture
- [ ] The fixture MatchRecord is committed with its expected final hash and verified by harness verify on all three CI platforms
- [ ] Live run of the fixture configuration in the client (not replay) produces the same beats at the same ticks

### BLD-148 — Render the one generated cave biome as a 3D truth layer for the replay

**Status:** Backlog  ·  **Story**  ·  P1  ·  6 d  ·  depends on BLD-145

ROADMAP Phase 5: '3D renderer, one cave biome, Surveyor chassis only.' Because truth is never rendered during the run, the cave mesh is a replay and reveal asset: it is built from ReplayFrame's true cave (heightfield cells with rock/dry/flooded semantics from Phase 3), with a water surface for flooded cells and stylised, dark materials — DESIGN says stylised rendering is enough. One biome only; no other biomes, no props, no foliage. The cave must read at the Phase 1 camera angle (58–62 degrees, not top-down) and the truth layer must be visually distinct from the belief point cloud drawn over it. Human-gated (cave art): expect about 10 calendar days and 1 round-trip(s) with the designer or testers beyond the 6 working days of work.

Done when:
- [ ] A mesh is generated from the true cave grid of any seed in the one shipped biome with no hand authoring; flooded cells render as a water surface
- [ ] Rock, dry passage, and flooded passage are distinguishable at the default replay camera; wall points from the belief layer read as a separate layer over it
- [ ] Mesh build for a full-size generated cave completes under one second on the dev laptop and is cached per seed
- [ ] No second biome, no hand-placed props; scope is written down in the scene file header

### BLD-149 — Model and animate the Surveyor chassis with an honest silhouette and a sensor head

**Status:** Backlog  ·  **Story**  ·  P1  ·  8 d  ·  depends on BLD-142

Surveyor is the only chassis in Phase 5. DESIGN: 'It needs something that functions as a face — a sensor head that turns to look at what it is attending to. This is the single detail that converts a machine into your machine.' GLOSSARY: modules are 'Visible on the model — silhouette is always honest.' The model carries visible meshes for the modules the loadout mounts (at minimum sonar, lidar, beacon rack, cargo bay), locomotion animation per the BLD-142 decision, and a head whose orientation is driven by a belief-space attention target (current contact, waypoint, or the fix just landed), never by anything true. The same model is drawn at the believed pose in the operator view and at the true pose in the replay. Human-gated (chassis art and animation): expect about 14 calendar days and 2 round-trip(s) with the designer or testers beyond the 8 working days of work.

Done when:
- [ ] Surveyor model with six slot mount points; each Phase 3 module has a mesh that reads at distance in the dark and is shown only when mounted
- [ ] Sensor head orientation is driven by a Belief-derived attention target supplied over the FFI; a test confirms the input type is one of the BLD-144 snapshot types
- [ ] Locomotion animation matches the sim's motion (turn-rate limits, walking pace); no foot sliding at the Phase 1 agent speed of ~1.1 cells/s
- [ ] Model renders at the believed pose in the operator view and at the true pose in the replay from the same asset
- [ ] Silhouette is documented as provisional; skins remain deferred post Phase 8 (ROADMAP Part 6)

### BLD-150 — Build the operator view point cloud in the estimated frame with smear, snap and overlays

**Status:** Backlog  ·  **Story**  ·  P0  ·  8 d  ·  depends on BLD-144  ·  retires R1

ARCHITECTURE: 'Primary run-phase view is a sparse 3D point cloud of accumulated returns in the agent's estimated frame, so drift renders as visible smearing and a fix snaps it into alignment.' PHASE-1-SPECTATOR-TEST calls the smear-and-snap 'the single most important visual'. The Phase 1 lessons carried here: the fix must be eased on screen over ~0.7 s while the model applies it instantly (a one-tick snap is invisible); walked near-field points, sonar points and lidar points must render distinctly or the map 'reads as noise'; empty space reads as absence, not fog; the camera starts at 58–62 degrees and orbits only. Overlays from the Phase 1 spec: own ping wavefront, rival pings as wavefronts from a bearing, ancient signature emissions, contact wedges, pose ellipse, per-point confidence, plus the fix-jump vector with surprise as a multiple of what the ellipse allowed. Belief only; Recall is the only input.

Done when:
- [ ] Points accumulate in the estimated frame with per-point confidence and source (walked / sonar / lidar) visibly distinct; a corridor walked without pinging is sparse, not empty
- [ ] A fix moves every point placed since the previous fix (the Phase 3 back-propagation) and the display eases the move over 0.7 s; a spoofed fix runs the identical display path
- [ ] Overlays present: own ping wavefront, rival ping wavefront from a bearing, ancient signature distinct from pings, contact bearing wedges kept short, pose uncertainty ellipse, fix-jump vector labelled with surprise
- [ ] Camera: orbit and zoom only, default elevation 58–62 degrees; no camera-in-world, no pause, no steering
- [ ] Pressing R sends Recall once through the BLD-144 command path; a second press does nothing and the HUD says so
- [ ] Scene has no reference to the replay host or ReplayFrame (CI grep from BLD-145)
- [ ] An intent line is drawn from the agent to its current believed waypoint so purposeful movement can be told apart from thrashing (b57a363)
- [ ] The believed beacon chain and the told-about shaft and deposit markers are drawn so there is somewhere to read the map against (ce9cb2c)

### BLD-151 — Drive directional audio from Belief with identical sound for honest and lying fixes

**Status:** Backlog  ·  **Story**  ·  P1  ·  3 d  ·  depends on BLD-144  ·  retires R1

PHASE-1-SPECTATOR-TEST: 'Sound is not optional in this phase. The game is about acoustics.' Phase 1's mixer was driven entirely from Belief: contacts panned by bearing relative to the camera azimuth, with a character (transient, scrape, drone); the ancient signature pulsing faster and higher as it approaches lethal so the acceleration is the warning; a crash loud and basin-wide; and, deliberately, the same two notes for an honest fix and a spoofed one — 'The only tell is how far the estimate moved.' Port that behaviour to Godot's audio, fed by the BLD-144 snapshots and event list.

Done when:
- [ ] Contacts are audible and panned by bearing relative to the current camera azimuth; character differs by sound kind
- [ ] Honest and spoofed fixes play the identical sound; a code review confirms no audio path branches on anything but Belief data
- [ ] Ancient signature audibly accelerates and rises through the warning window before the lethal window
- [ ] Rival pings and the crash are audible from a bearing; own ping deafens briefly as in the sim
- [ ] Audio is entirely Belief-driven: the audio script imports only BLD-144 snapshot types

### BLD-152 — Build the operator panels: live decision graph, timeline strip, belief-fact HUD

**Status:** Backlog  ·  **Story**  ·  P0  ·  5 d  ·  depends on BLD-150, BLD-128  ·  retires R1

The Phase 1 view is the prototype of this layout: 'the policy deciding on the left, the map it has built in the middle, and the shape of the match along the bottom. Words live in fixed places, so position carries meaning and only the one event happening now has to be read' (phase1/view/view.py). Phase 1 playtesting found the decision graph's fill bars were the thing that made the run readable: 'a bar creeping toward its threshold tells you what the machine is about to decide several seconds before it decides it.' In the real client the graph is driven by Phase 4's execution trace (which nodes fired, in what order, on what predicate values) rendered over the policy's BtNode tree, the timeline from the Belief event list, and the status HUD from plain-English labels stating belief facts ('moved 34 cells when it expected 3', never 'you were spoofed'). Human-gated (designer self-test): expect about 3 calendar days and 1 round-trip(s) with the designer or testers beyond the 5 working days of work.

Done when:
- [ ] Decision graph renders the running policy's tree with the fired branch lit and each Guard's predicate value drawn as a fill toward its threshold, from the Phase 4 execution trace
- [ ] Timeline strip marks every Belief event at its time; only the current event is spelled out in words
- [ ] Status HUD shows cargo, believed destination, last fix (as a multiple of what the ellipse allowed), map size, and the one command's state, using the Phase 1 plain-English labels as the starting copy
- [ ] Layout is three fixed regions (graph left, map centre, timeline bottom) and resizes without overlap at 1280x720 and 1920x1080
- [ ] All panel text is Belief-derived; a review of panel GDScript finds no reference to the replay host
- [ ] Designer's twenty-minute self-test (PHASE-1 spec: 'You will know within twenty minutes whether you are leaning forward') done on this build and its notes recorded
- [ ] Timeline captions carry a priority and a cooldown: important events sort first and routine notices cannot push them off screen (Phase 1: two routine ping notices were pushing POSITION FIX DISAGREES off screen)

### BLD-153 — Design failure-attribution heuristics against a harness-generated wreck corpus

**Status:** Backlog  ·  **Spike**  ·  P1  ·  2 d  ·  depends on BLD-146  ·  retires R3

ROADMAP Phase 5: 'Failure attribution heuristics: identify and present the causal chain.' CLAUDE.md names automatic failure attribution a known-weak area and says to flag design problems rather than build around them, so this is a spike before a story. Use the Phase 0 batch executor to generate a corpus of lost agents, then work out from execution traces and Belief events (fix surprise, uncertainty collapse after a fix, a contact that never moved, ticks_since_fix growth, an ignored hazard signature, a 'cannot reach' waypoint streak) which chains from trigger to decision to outcome can be stated with evidence, and which cannot. The spike ends with a written verdict: which chains are honest, which would overclaim, and whether the approach survives. Human-gated (designer labels the wreck corpus): expect about 5 calendar days and 1 round-trip(s) with the designer or testers beyond the 2 working days of work.

Done when:
- [ ] A corpus of at least 50 lost-agent MatchRecords generated with the harness batch executor across seeds in the one biome
- [ ] Candidate heuristics listed with, for each, the Belief events and trace nodes it rests on and the truth check (from ReplayFrame) used to score it
- [ ] The designer labels 20 corpus wrecks by hand; agreement between labels and each heuristic recorded — no target set in advance because the area is known-weak
- [ ] Written verdict recommending which chains to present, which to withhold as 'no cause identified', and any design problem found (e.g. spoof and honest loop-closure indistinguishable in belief)
- [ ] No heuristic runs inside the live sim or feeds anything back to Belief or policies

### BLD-154 — Build the replay screen with truth and belief drawn together on one scrubbable timeline

**Status:** Backlog  ·  **Story**  ·  P0  ·  10 d  ·  depends on BLD-146, BLD-148, BLD-149, BLD-150, BLD-152  ·  retires R3

ROADMAP Phase 5: 'Replay with both layers drawn together — this is the most important screen in the game and should get the most polish.' DESIGN: the replay is 'where you can finally see where your machine's picture came apart', where the learning happens and where the clip comes from. Truth (cave mesh, true trail, true beacon positions including the spoof, wrecks, ancient hazard volume) and belief (the point cloud, believed trail, believed beacons, ellipse) are drawn from the same ReplayFrame in two clearly separated palettes, with a tether between believed and true pose, the BLD-152 panels showing the execution trace at the scrubbed tick, and a camera tilt that separates the layers as Phase 1's reveal did. The run phase ends by transitioning into this screen at the final tick — that is the Phase 1 post-run reveal, where the player's wrong theory got corrected.

Done when:
- [ ] Both layers render from one ReplayFrame per tick; belief and truth palettes are distinguishable at a glance and in a screenshot
- [ ] A tether from believed pose to true pose is drawn and its length shown; the spoofed beacon's true and recorded positions are both visible
- [ ] Scrub, play, pause, step; the decision graph and timeline show the state at the scrubbed tick
- [ ] The run-phase scene transitions into the replay at match end without leaving the process; truth is not drawn before the end (PHASE-1: 'Ground truth is never rendered during the run')
- [ ] Seed and content hash visible and copyable
- [ ] The Phase 1 gate video's moments (first contact, echo, spoof landing, ancient kill, extraction) are each locatable within ten seconds of scrubbing on the BLD-147 fixture

### BLD-155 — Add enter-agent-perception mode from any replay tick

**Status:** Backlog  ·  **Story**  ·  P1  ·  4 d  ·  depends on BLD-154  ·  retires R3

DESIGN: 'When an agent fails, you do not read a stack trace. You enter its perception in the replay and watch the world through its degraded senses — the false echo it trusted, the beacon that lied to it, the moment its position estimate and its actual position parted company.' It calls this 'the best teaching mechanism in the design' and says it 'should be the most polished thing in the game.' From any replay tick the player drops into the operator view (BLD-150/BLD-152/BLD-151) rendered from that tick's Belief in the ReplayFrame, with the truth layer hidden, and returns to the two-layer view at the same tick. Reuses the operator scene; no separate renderer.

Done when:
- [ ] From any replay tick, one input switches to the operator view driven by that tick's Belief and plays forward from there; the truth layer is not drawn in this mode
- [ ] Returning to the two-layer view lands on the same tick the player left
- [ ] The operator scene instance used here is the same scene as the live run phase (no fork), fed by the Belief half of ReplayFrame through the same snapshot types
- [ ] Perception mode at the spoof tick on the BLD-147 fixture shows the fix landing, the surprise value, and the ellipse collapsing, with nothing on screen revealing the lie
- [ ] Audio plays in perception mode as it did live

### BLD-156 — Give each interference and hazard event a distinct replay signature

**Status:** Backlog  ·  **Story**  ·  P2  ·  3 d  ·  depends on BLD-154

DESIGN: 'Every interference method needs a distinct, obvious visual signature in the replay' — without attributable sabotage there is no clip. Scope is what the Phase 3 sim actually has by Phase 5: the spoofed beacon (recorded vs true position, the fix that tore the map), the echo (a second arrival on a different bearing that never moves or repeats), the ancient kill (signature ramp then hazard volume), and collapse if the structural axis shipped. Methods that do not exist in the sim yet get nothing; do not build signatures for imagined mechanics. Human-gated (three-person clip check): expect about 3 calendar days and 1 round-trip(s) with the designer or testers beyond the 3 working days of work.

Done when:
- [ ] Spoof, echo, ancient hazard, and (if present in the sim) collapse each have a unique replay glyph or animation at the tick they occur, visible in both the two-layer view and on the timeline
- [ ] A spectator shown a five-second clip of each on the BLD-147 fixture can name which happened (three-person informal check, results recorded)
- [ ] Signatures are drawn from ReplayFrame or trace data; none is drawn in the live operator view
- [ ] A list of interference methods still lacking a sim mechanic (DESIGN's noise flooding, decoy, silt clouding, induced collapse, beacon theft) is recorded and handed to BLD-163, which decides which ship and what signature each needs; nothing is built for them here

### BLD-157 — Present the causal chain of each loss in the replay with evidence per link

**Status:** Backlog  ·  **Story**  ·  P1  ·  6 d  ·  depends on BLD-153, BLD-154  ·  retires R3

Implements the heuristics the BLD-153 spike endorsed. DESIGN's promise is 'Every failure is legible', but the client must not overclaim: each link in the chain (e.g. fix from beacon B moved the estimate 34 cells at 11x what the ellipse allowed -> uncertainty collapsed and the return rule disarmed -> policy took the left branch on a wrong premise -> hazard signature ignored -> wreck) cites the tick and the Belief event or trace node it rests on, and clicking a link scrubs the replay there. Truth from ReplayFrame may confirm a link in the replay tool; the chain's wording stays in belief facts. When no chain meets the spike's bar the screen says so rather than guessing.

Done when:
- [ ] For each wreck in the replay, a chain panel lists links from trigger to decision to outcome, each with a tick and a cited Belief event or trace node; clicking a link seeks the replay to that tick
- [ ] When no endorsed heuristic matches, the panel states 'no cause identified' and nothing else
- [ ] Attribution runs only in the replay host (feature-gated with ReplayFrame); a compile-fail test proves it cannot be reached from the live-run host
- [ ] On the BLD-147 fixture the spoof-to-loss chain is produced and matches the designer's label; on the 20 labelled corpus wrecks the agreement rate from BLD-153 does not fall
- [ ] Chain text uses belief facts ('moved 34 cells when it expected 3'), never 'you were spoofed' (Phase 1 caption rule)

### BLD-158 — Hold the frame budget with a full-match point cloud; warm up shaders before play

**Status:** Backlog  ·  **Task**  ·  P2  ·  2 d  ·  depends on BLD-150, BLD-154

Phase 1 measured a live paint of 39 ms with a 16k-point lidar map, and a lidar run accumulating 26,825 points; vispy's first-paint shader compile froze the loop for 11 s and text reassignment rebuilt glyph atlases. Godot removes the vispy-specific traps but 'warm up before play' and 'cache strings, batch geometry' still apply. Measure the operator view and the replay screen at end-of-match point counts and fix what misses 60 fps on the dev laptop. Not a feature; a measurement with a budget.

Done when:
- [ ] Operator view holds 60 fps on the dev laptop at 30k accumulated points with all overlays and panels on
- [ ] Replay screen holds 60 fps with both layers at the final tick of the BLD-147 fixture
- [ ] First frame after scene load has no visible hitch: shaders and fonts are warmed before the match clock starts
- [ ] Frame-time numbers recorded in blindside-client/README.md next to the Phase 1 baseline

### BLD-159 — Re-run the Phase 1 spectator test in the real client and score it against the Python record

**Status:** Backlog  ·  **Story**  ·  P0  ·  2 d  ·  depends on BLD-150, BLD-152, BLD-151, BLD-154, BLD-155, BLD-147, BLD-158, BLD-14, BLD-5, BLD-16  ·  retires R1

This is the Phase 5 gate: 'Phase 1's spectator test, re-run in the real client, scores better than the Python version did.' The protocol must be identical to the recorded Phase 1 session or the comparison is meaningless: eight minutes, no explanation beyond 'you cannot drive it', Recall only, the same sensor configuration, the preserved rubric, and a player who has not seen the Python version. The observer records the same behaviours (talks to the screen, guesses at contacts, forms a wrong theory and corrects it, reports tension at the Recall decision, and the minute of disengagement if any), scores with the same rubric, and writes the comparison. CLAUDE.md: report readiness, never that the gate is met — a human decides. Human-gated (external playtest against the Phase 1 record): expect about 7 calendar days and 1 round-trip(s) with the designer or testers beyond the 2 working days of work.

Done when:
- [ ] An exported client build (no editor) runs the BLD-147 configuration live on the playtest machine start to finish without intervention
- [ ] Designer self-test done first: the twenty-minute leaning-forward check, noted
- [ ] Session with a non-designer who has not seen the Python version follows the two-viewing protocol from BLD-5: viewing one (sonar) is scored with the Phase 1 rubric and compared to Phase 1's viewing one (BLD-16) item by item; viewing two (lidar) is logged separately; observer notes capture quotes, the wrong theory and its correction, stated tension at Recall, and disengagement minute if any
- [ ] A written comparison against the Phase 1 session: rubric item by item, with the client's score and the Python score side by side, and which items moved
- [ ] If the score is not better: the report classifies what the client lost (legibility, pacing, sound) and Phase 6 is not started
- [ ] The report says 'ready for gate' or lists what blocks it; it does not say 'gate met'

## BLD-160 — Networked match

**Phase Phase 6 — Networked match.** Stand up blindside-net: a server-authoritative sim that sends each client only its team's belief-space state, runs four-team extraction matches with wrecks, salvage and behaviour recovery, a depth-latency command channel blocked in acoustic shadow, and a lobby that publishes seed and replay post-match (ROADMAP Phase 6, DESIGN netcode and match-structure sections). The phase exists to answer risk R8 with a measured number. It leans on Phase 3 systems that must already exist: the thermal shadow zones of the acoustic field, the depth-profile axis, Wreck data in World, and the Extraction MatchMode. Deferred on purpose: multiple agents per player, multi-human teams, matchmaking, and pre-built anti-griefing (ROADMAP Part 6). Added after review: an interference-method decision spike (BLD-163) and the two stories that build the chosen methods on Phase 3 substrate (BLD-174, BLD-175), so DESIGN's toolkit is held by a story rather than silently dropped. Human-gated stories in this epic: 4 of 17 (0 designer decisions or reviews, 1 playtests or self-tests, 3 art, toolchain, CI or commercial), carrying at least 29 calendar days of latency on top of 60 working days.

- **Gate — pass:** Answers R8: server cost per match is measured on real hosting (CPU, memory, bandwidth at the chosen team count and snapshot cadence) and written up against a plausible price point (ROADMAP Phase 6 gate).
- **Gate — kill:** R8: server cost per match exceeds unit economics — business model broken. The server-authoritative architecture is still required for replays and market verification, so the code is not wasted, but Phase 7 does not start until the designer has decided what to do about the number.
- **Can start when:** The Phase 5 gate report (BLD-159) exists and the designer has read it as better than the Python record; BLD-164 depends on BLD-159 to encode that, and on BLD-104 (Extraction mode) which the server hosts. BLD-161, BLD-162 and BLD-163 are decisions and can be done during Phase 5.
- **Estimate:** 60 working days

| Key | Type | Summary | Pri | Days | Depends on | Risk |
|---|---|---|---|---|---|---|
| BLD-161 | Task | Record the Phase 6 design decisions with the designer | P0 | 1 | BLD-139 | — |
| BLD-162 | Spike | Choose transport, serialisation and snapshot cadence for blindside-net | P0 | 2 | BLD-139 | R8 |
| BLD-163 | Spike | Decide which interference methods ship, in what order, and their replay signatures | P1 | 1 | BLD-161 | — |
| BLD-164 | Story | Create blindside-net with a belief-only wire protocol | P0 | 4 | BLD-162, BLD-159, BLD-104 | — |
| BLD-165 | Story | Run the sim server-authoritatively and build the MatchRecord live | P0 | 6 | BLD-164, BLD-31, BLD-105 | R4 |
| BLD-166 | Story | Connect the Godot client to a remote match | P0 | 5 | BLD-164, BLD-165 | — |
| BLD-167 | Story | Build the lobby and simultaneous prep phase | P0 | 5 | BLD-161, BLD-165, BLD-166 | — |
| BLD-168 | Story | Run N-team extraction matches on one shared seed | P0 | 4 | BLD-167 | R4 |
| BLD-169 | Story | Play the descent and blackout sequence | P1 | 3 | BLD-165, BLD-166 | — |
| BLD-170 | Story | Complete the command channel: Hold, Go quiet, Abort, per-match budget, shadow blocking end to end, lobby toggle | P0 | 3 | BLD-161, BLD-165, BLD-105 | — |
| BLD-171 | Story | Add wrecks, salvage and behaviour recovery with provenance | P0 | 5 | BLD-168, BLD-93 | R7 |
| BLD-172 | Story | Publish seed and replay after every match | P1 | 3 | BLD-165, BLD-168 | R4 |
| BLD-173 | Story | Serve a live spectator stream per the recorded truth-or-belief decision | P2 | 4 | BLD-161, BLD-165, BLD-172 | — |
| BLD-174 | Story | Implement beacon theft and the decoy emitter with their counters | P1 | 3 | BLD-163, BLD-86, BLD-90, BLD-89, BLD-156 | R4 |
| BLD-175 | Story | Implement noise flooding, silt clouding and induced collapse | P2 | 4 | BLD-163, BLD-79, BLD-94, BLD-96, BLD-156 | R4 |
| BLD-176 | Task | Playtest networked matches and log observed griefing | P1 | 3 | BLD-170, BLD-171, BLD-172 | — |
| BLD-177 | Spike | Measure server cost per match against a plausible price point | P0 | 4 | BLD-168, BLD-170, BLD-171, BLD-172 | R8 |

### BLD-161 — Record the Phase 6 design decisions with the designer

**Status:** Backlog  ·  **Task**  ·  P0  ·  1 d  ·  depends on BLD-139

DESIGN.html's open-decisions section leaves four things unresolved that change the shape of this phase: team count (two, four or eight; DESIGN defaults to four), whether live spectators see truth or belief (DESIGN leans truth for spectators, belief for players), whether the command channel exists at all or pure helplessness is tested too, and match length (DESIGN guesses ten minutes; Phase 1 tuned to eight). CLAUDE.md says ask rather than invent; this story is the asking, and the answers are written down before any net code depends on them. Human-gated (designer decisions): expect about 5 calendar days and 1 round-trip(s) with the designer or testers beyond the 1 working days of work.

Done when:
- [ ] A decision record in docs/ states team count (as a parameter with its default), spectator truth-or-belief, whether the pure-helplessness variant is to be playtested, and the match length to ship with, each with a one-line reason
- [ ] The wrecks container is not reopened: it was decided in BLD-61, given record-assigned ids in BLD-69 and built in BLD-93; the record says so
- [ ] Nothing in this story is code

### BLD-162 — Choose transport, serialisation and snapshot cadence for blindside-net

**Status:** Backlog  ·  **Spike**  ·  P0  ·  2 d  ·  depends on BLD-139  ·  retires R8

ARCHITECTURE names blindside-net (server, lobby, match orchestration) but says nothing about how bytes move. DESIGN's netcode row says the problem is small: no client prediction, no rollback, no lag compensation, sparse inputs and a filtered view. The unknowns are which transport and serialisation crates to pin, how often a Belief snapshot is sent (every tick at 20 Hz is likely wasteful; the point cloud is the large part), and whether snapshots are full or delta. The answer sets the bandwidth term of the R8 measurement, so it is a spike, not a guess.

Done when:
- [ ] A written note pins the transport and serialisation crates with exact versions and the reason for each
- [ ] Snapshot cadence and full-versus-delta strategy chosen, with a back-of-envelope bytes-per-client-per-match figure derived from Phase 5's belief snapshot types
- [ ] A throwaway prototype sends a Phase 5 belief snapshot from a server process to a client process on localhost and the client renders it
- [ ] Time-boxed to the estimate; open questions are listed, not resolved by guessing

### BLD-163 — Decide which interference methods ship, in what order, and their replay signatures

**Status:** Backlog  ·  **Spike**  ·  P1  ·  1 d  ·  depends on BLD-161

DESIGN's interference toolkit lists seven methods; the plan covers the false beacon (BLD-86 and BLD-106) and, implicitly, following. The other five — 'Noise flooding | Blinds passive listeners in a region', 'Decoy emitter | Fake contact draws agents toward nothing', 'Silt clouding | Destroys optical range in a passage', 'Induced collapse | Closes a route, possibly onto something', 'Beacon theft | Removes a rival's navigation network' — are recorded by BLD-156 as lacking a sim mechanic, and DESIGN says 'Sabotage must be visible and attributable ... without clips there is no growth engine.' Phase 6 is the first phase where rivals play each other, so the choice belongs here, made with the designer and informed by the BLD-176 griefing log where available. Also settles the counters for following: a being-followed predicate candidate (vocabulary growth is R5) and Go quiet (BLD-170). Human-gated (designer decision on interference methods): expect about 3 calendar days and 1 round-trip(s) with the designer or testers beyond the 1 working days of work.

Done when:
- [ ] A written decision per method: ship in Phase 6, defer to a named phase, or cut, each with the DESIGN counter it requires and the replay signature BLD-156 must add for it
- [ ] Each shipped method gets a ModuleId and ActionId reserved in the content ID table; none is derived or reused
- [ ] A being-followed predicate (persistent contact astern over time) is recorded in docs/PREDICATE-CANDIDATES.md as a candidate, not implemented
- [ ] No code in this spike

### BLD-164 — Create blindside-net with a belief-only wire protocol

**Status:** Backlog  ·  **Story**  ·  P0  ·  4 d  ·  depends on BLD-162, BLD-159, BLD-104

Create the blindside-net crate from ARCHITECTURE's layout and define the wire protocol: per-team belief snapshots built only from Belief-derived types (the same snapshot types Phase 5 hands across the FFI), command submission as (Tick, TeamId, Command), and lobby messages. The network boundary is the fourth enforcement point of the one invariant after module privacy, the compile-time test and the FFI surface: DESIGN says clients genuinely should not have ground truth and that cheating is structurally hard because of it. A test must prove the player protocol cannot carry anything from world.rs or from the sanctioned replay/spectator truth export.

Done when:
- [ ] blindside-net compiles in the workspace and depends on blindside-sim's public surface only; it never names World
- [ ] Every wire message type is enumerated in one module; a test fails if any type from blindside-sim's world module or the truth export is reachable from the player-client protocol
- [ ] Message schema is versioned; an unknown version is a hard error, not a silent accept
- [ ] Command messages carry exactly (Tick, TeamId, Command) and nothing else

### BLD-165 — Run the sim server-authoritatively and build the MatchRecord live

**Status:** Backlog  ·  **Story**  ·  P0  ·  6 d  ·  depends on BLD-164, BLD-31, BLD-105  ·  retires R4

The server owns the only running World. It constructs a Sim from a MatchRecord-in-progress (seed, content hash, loadouts, policies), steps it at the fixed tick rate, accepts client commands, stamps them with the server tick, appends them to the command log, and broadcasts each team's belief snapshot at the chosen cadence. At match end the accumulated MatchRecord is the replay and must re-verify through the Phase 0 harness — this is the server-authority dependent that DETERMINISM.md lists. Commands are the only live input (ARCHITECTURE MatchRecord).

Done when:
- [ ] A server process runs a full-length match with four connected clients and no renderer
- [ ] Every accepted command appears in the MatchRecord command log; commands that exceed the per-match budget, are malformed, or are out of tick order are rejected server-side and logged
- [ ] The MatchRecord the server writes at match end passes harness verify and reproduces the server's final state hash on a different platform in CI
- [ ] The server tick loop holds the fixed tick rate under four clients on the intended hosting; a dropped-tick counter is exposed for BLD-177

### BLD-166 — Connect the Godot client to a remote match

**Status:** Backlog  ·  **Story**  ·  P0  ·  5 d  ·  depends on BLD-164, BLD-165

The Phase 5 client hosts the sim in-process behind the GDExtension boundary. For networked play the operator view is fed from network belief snapshots instead, and the client runs no truth at all — there is nothing to leak. GDScript stays the UI and glue layer (ARCHITECTURE: do not write the whole client in Rust). The Recall, Hold, Go quiet and Abort inputs become command messages.

Done when:
- [ ] A client joins a server match, receives belief snapshots, and the Phase 5 operator view renders from them with no local sim of truth
- [ ] Player input during the run is limited to command messages; there is no code path that steers the agent
- [ ] Disconnect and reconnect mid-match resumes snapshots without affecting the server (the server is the only authority, so a client crash costs the player nothing but time)
- [ ] The client build contains no reference to the truth export types, checked by the same build-time test Phase 5 uses for the FFI surface

### BLD-167 — Build the lobby and simultaneous prep phase

**Status:** Backlog  ·  **Story**  ·  P0  ·  5 d  ·  depends on BLD-161, BLD-165, BLD-166

DESIGN's match timeline: prep is two to four minutes of chassis selection, module loadout and behaviour assignment, all teams prepping at once, each seeing its entry shaft and nothing else. The lobby forms a match of N teams (N from the BLD-161 decision, default four), the server picks the seed and keeps it hidden until match end, loadouts are validated against slots, mass and power and locked at launch (GLOSSARY: Loadout), and policies come from the player's library, purchases, or salvage. No matchmaking or ranking — ROADMAP defers both past Phase 8.

Done when:
- [ ] Lobby forms a match of N teams where N is a server parameter defaulting to the recorded decision
- [ ] Prep timer enforces the window; a team that has not confirmed by the deadline launches with its last valid loadout
- [ ] An over-slot, over-mass or over-power loadout is rejected by the same validator the sim uses, and the loadout is immutable after launch
- [ ] Each team's prep view shows only its own entry shaft; the seed is not present in any client message before match end

### BLD-168 — Run N-team extraction matches on one shared seed

**Status:** Backlog  ·  **Story**  ·  P0  ·  4 d  ·  depends on BLD-167  ·  retires R4

DESIGN: all four teams get the same seed and the same cave, with entry points distributed around the perimeter and deposit value roughly equal per region but not accessibility. Phase 3 shipped the Extraction MatchMode for the headless gate; this story extends generation and the mode to N teams — perimeter entry shafts, per-team scoring of value brought back through a shaft, the last-90-second extraction window after which anything still below is lost with its cargo. This is sim and gen crate work, so the determinism lint and the three-platform canary apply.

Done when:
- [ ] blindside-gen places N perimeter entry shafts and the connectivity guarantee holds from every shaft to every deposit region
- [ ] Extraction mode scores each team by value extracted through any shaft; agents not extracted when the window closes are lost with cargo
- [ ] 1,000 headless four-team matches remain bit-identical across Linux, macOS and Windows in CI, and the Phase 3 time budget is re-measured with four teams
- [ ] A team-count parameter of 2 and 8 also generates and runs, so the BLD-161 decision can be revisited from playtests

### BLD-169 — Play the descent and blackout sequence

**Status:** Backlog  ·  **Story**  ·  P1  ·  3 d  ·  depends on BLD-165, BLD-166

GLOSSARY: Commit is the moment control leaves the player, roughly 20 seconds after descent; before it full authority and no information, after it full information and no authority. DESIGN's timeline has descent with full telemetry, then blackout where comms degrade to an acoustic trickle and drift begins. The client shows the handoff; the server enforces it by rejecting control after commit. The telemetry fidelity schedule is tied to the depth-profile axis from Phase 3.

Done when:
- [ ] For roughly 20 s after launch the client receives full-fidelity telemetry; after commit it receives belief snapshots only and any control message is rejected by the server
- [ ] Telemetry fidelity drops on a schedule derived from the agent's depth, not from wall-clock
- [ ] The commit moment is legible in the client (Phase 1 lesson: illegible is the failure mode, not plain)

### BLD-170 — Complete the command channel: Hold, Go quiet, Abort, per-match budget, shadow blocking end to end, lobby toggle

**Status:** Backlog  ·  **Story**  ·  P0  ·  3 d  ·  depends on BLD-161, BLD-165, BLD-105

DESIGN: a handful of very low-bandwidth messages — Recall, Hold, Go quiet, Abort to nearest shaft — a few bytes each, delivered with latency proportional to depth and blocked entirely in acoustic shadow; a deliberate pressure valve, blunt on purpose. Recall with depth latency, terminal abort-to-shaft, the spiral search and the unit-tested shadow drop were built in BLD-105 and are not rebuilt here. This story adds Hold, Go quiet and Abort, the per-match command budget, exercises the shadow block end to end over the network (the BLD-80 zones), and adds the lobby option that disables the channel so the pure-helplessness variant can be playtested. Commands are the only live input in MatchRecord.

Done when:
- [ ] Hold, Go quiet and Abort to nearest shaft exist as actions and byte-sized command encodings; with Recall (BLD-105) that is the four DESIGN names, and a per-match budget is set in content data and enforced server-side
- [ ] A command sent while the agent is inside a shadow zone is not delivered, end to end over the network; the client shows it as unacknowledged rather than lost
- [ ] Recall is unchanged from BLD-105 (terminal, straight at the believed shaft, then the spiral search); its regression tests still pass with the other three commands present
- [ ] A lobby option disables the channel so the pure-helplessness variant can be playtested, per the DESIGN open decision and the BLD-161 record
- [ ] All delivered commands, with their delivery tick, are in the MatchRecord and the replay reproduces them

### BLD-171 — Add wrecks, salvage and behaviour recovery with provenance

**Status:** Backlog  ·  **Story**  ·  P0  ·  5 d  ·  depends on BLD-168, BLD-93  ·  retires R7

DESIGN Loss and salvage: when an agent dies it stays where it fell with everything it was carrying and running; wrecks persist for the match; any agent can salvage a wreck for its cargo and, with the module for it, its behaviour. GLOSSARY: recovering the policy requires the appropriate module. ARCHITECTURE's Policy carries a provenance chain for salvaged behaviours; DESIGN leans private-use-only with attribution for stolen behaviours, recorded in BLD-196. Phase 3 shipped the Wreck data; this adds the salvage action, the recovery module, and the library plumbing. Sim-crate work: canary and lint apply.

Done when:
- [ ] Agent death produces a Wreck at the true position holding inventory and PolicyRef; wrecks are sensable and persist to match end; iteration is by the record-assigned WreckId from BLD-69 as built in BLD-93
- [ ] A salvage action transfers cargo; with the behaviour-recovery module equipped it also yields a Policy whose provenance has the original author appended, never replaced
- [ ] A recovered policy appears in the recovering player's library for the next prep and is usable there; resale is disabled pending the BLD-196 decision
- [ ] Salvage of your own wreck and of a rival's wreck both work; the replay shows the salvage event as a distinct signature
- [ ] The behaviour-recovery module has a content entry with the stable ModuleId reserved in the BLD-63 table and a slot/mass/power cost validated by BLD-98's loadout validator; without it salvage yields cargo only (GLOSSARY: recovering the policy requires the appropriate module)

### BLD-172 — Publish seed and replay after every match

**Status:** Backlog  ·  **Story**  ·  P1  ·  3 d  ·  depends on BLD-165, BLD-168  ·  retires R4

DESIGN: the seed is published after the match; anyone can re-run a scenario, test a behaviour against a known cave, and share a seed that produced something remarkable. ROADMAP Phase 6 lists lobby, seeds, published post-match. The server writes the MatchRecord (seed, schema, content hash, loadouts, policies, commands) and publishes it; any client can download it and load it into the Phase 5 replay screen, and the Phase 0 harness verifies it. The content hash must travel with it or replays break silently after a balance change (ARCHITECTURE extension rule 2).

Done when:
- [ ] At match end the server publishes the MatchRecord and seed to all participants and to a fetchable location
- [ ] A downloaded record loads in the replay screen and re-runs to the same final hash the server recorded
- [ ] harness verify passes on the published record on all three CI platforms
- [ ] The seed is absent from every message sent before match end

### BLD-173 — Serve a live spectator stream per the recorded truth-or-belief decision

**Status:** Backlog  ·  **Story**  ·  P2  ·  4 d  ·  depends on BLD-161, BLD-165, BLD-172

DESIGN: ground truth appears in exactly two places, the post-match replay and the spectator view, and the designer leans truth for spectators because clips must be legible. ARCHITECTURE says World goes to neither client nor renderer; Phase 5 reconciled that with a sanctioned truth export produced by the replay runner. If BLD-161 chooses truth for spectators, the spectator stream is a second protocol built from that export on the server and sent only to spectator connections. Player clients must never be able to receive it.

Done when:
- [ ] Spectator connections are a distinct role at the lobby; a player connection cannot be upgraded to spectator during a match
- [ ] If truth-for-spectators was chosen: the spectator stream carries both layers for the same tick, built from the sanctioned export, and a test asserts the player protocol cannot deserialise it
- [ ] If belief-for-spectators was chosen: spectators receive every team's belief snapshots and nothing else
- [ ] Spectating a friend's match works end to end on the intended hosting

### BLD-174 — Implement beacon theft and the decoy emitter with their counters

**Status:** Backlog  ·  **Story**  ·  P1  ·  3 d  ·  depends on BLD-163, BLD-86, BLD-90, BLD-89, BLD-156  ·  retires R4

DESIGN: 'Beacon theft | Removes a rival's navigation network | Redundancy; terrain-relative fallback' and 'Decoy emitter | Fake contact draws agents toward nothing | Bearing-only tracking over time; decoys don't move naturally'. Both reuse Phase 3 machinery: theft is a pick-up action on any beacon entity (the victim's KnownBeacon stays in Belief and simply stops answering, so the lie is in belief, not in the type); a decoy is a deployable emitter with a chosen signature registered in the AcousticField, whose tell is a bearing that never moves, readable through ContactTrack's stationary-over-time measure (BLD-89). Built only if BLD-163 chose them. Sim-crate work: lint, canary and the three-platform hash apply.

Done when:
- [ ] A pick-up action removes any beacon entity from World and returns it to the actor's rack; the victim's KnownBeacon persists in Belief and yields no further fixes; terrain-relative navigation (BLD-90) still recovers on the fixture
- [ ] The decoy module deploys an emitter with a content-specified signature and duration; a rival's ContactTrack for it reports stationary over time and nothing in Return or Belief marks it a decoy (grep test)
- [ ] Both events have a distinct replay signature added to BLD-156's set and appear in the failure-attribution chain when they cause a loss
- [ ] No damage path exists (BLD-99 registry test); deterministic across two Sims; the 1,000-match batch stays bit-identical on three platforms

### BLD-175 — Implement noise flooding, silt clouding and induced collapse

**Status:** Backlog  ·  **Story**  ·  P2  ·  4 d  ·  depends on BLD-163, BLD-79, BLD-94, BLD-96, BLD-156  ·  retires R4

DESIGN: 'Noise flooding | Blinds passive listeners in a region | Blinds you too; also announces that someone is doing it', 'Silt clouding | Destroys optical range in a passage | Non-optical sensing; wait it out', 'Induced collapse | Closes a route, possibly onto something | Structural monitor; route diversity'. Each is a module plus an action over Phase 3 substrate: a regional noise floor in the AcousticField (BLD-79) that zeroes passive quality including the emitter's own and is itself a loud contact; a deliberate sediment release using the transient cloud state (BLD-96); a provocation on failing rock that triggers a collapse with the standard structural warning lead (BLD-94). Only the methods BLD-163 chose are built; induced collapse is the one method that can kill and must do so only through the collapse path.

Done when:
- [ ] Per chosen method: content entries with stable ModuleId and ActionId; the effect matches its DESIGN row on a fixture and the DESIGN counter works on the same fixture (non-optical sensing unaffected by silt; structural monitor gives its lead before an induced collapse; the flooding emitter is audible as a contact to everyone including itself)
- [ ] Induced collapse kills and wrecks agents inside the volume through BLD-94's collapse path; no action deals damage directly (BLD-99 registry test)
- [ ] Each method has a distinct replay signature (extends BLD-156) and is named by the failure-attribution chain when it causes a loss
- [ ] Deterministic across two Sims; the 1,000-match batch stays bit-identical on three platforms; every tunable is listed as a guess in the PR

### BLD-176 — Playtest networked matches and log observed griefing

**Status:** Backlog  ·  **Task**  ·  P1  ·  3 d  ·  depends on BLD-170, BLD-171, BLD-172

DESIGN milestone seven asks whether competition holds up. ROADMAP Part 6 defers anti-griefing systems to Phase 6 playtests so the response is designed to observed griefing rather than imagined. Run matches with friends across both command-channel variants (BLD-170), log what people do to each other and whether it was legible in the replay (DESIGN: sabotage must be visible and attributable), and write the griefing log without building any response yet. Human-gated (networked playtests with friends): expect about 14 calendar days and 2 round-trip(s) with the designer or testers beyond the 3 working days of work.

Done when:
- [ ] At least six four-team matches played over the network with observer notes per match
- [ ] Both the command-channel and pure-helplessness variants played, and the designer's preference recorded against the BLD-161 open decision
- [ ] A griefing log listing each observed behaviour, its replay legibility, and a proposed response — with no anti-griefing code written
- [ ] Match length reconsidered against DESIGN's ten-minute guess and Phase 1's eight, and the chosen value recorded

### BLD-177 — Measure server cost per match against a plausible price point

**Status:** Backlog  ·  **Spike**  ·  P0  ·  4 d  ·  depends on BLD-168, BLD-170, BLD-171, BLD-172  ·  retires R8

This is the Phase 6 gate and the reason the phase exists: ROADMAP Part 1 rates R8 (server cost per match exceeds unit economics) at medium confidence and says the answer is found here. Pick the hosting the game would actually run on, run K concurrent full-length four-team matches with real clients connected at the chosen snapshot cadence, and measure CPU-seconds, memory and egress per match. Compare to a price point the designer believes players would pay. Report the number; do not report the gate as met (CLAUDE.md). Human-gated (real hosting measurement and price point): expect about 7 calendar days and 1 round-trip(s) with the designer or testers beyond the 4 working days of work.

Done when:
- [ ] A written measurement: hosting provider and instance, matches per instance-hour at the shipped tick rate and cadence, memory per match, bytes per client per match, and the resulting cost per match in currency
- [ ] A stated plausible price point and the implied matches-per-player-per-month at which hosting breaks even
- [ ] The measurement is reproducible from a script in blindside-harness or blindside-net, not a one-off
- [ ] Findings list what would change the number most (cadence, delta snapshots, tick rate, team count) with a rough sensitivity for each

## BLD-178 — Onboarding and fiction

**Phase Phase 7 — Onboarding and fiction.** Teach belief-versus-truth without a lecture. Two ancient systems with signature, behaviour, exploit and counter; a first match whose first failure is a beacon lie the player watches happen; a named persistent fleet with service history and a wall of the lost; Endurance mode (ROADMAP Phase 7). The phase answers R6. DESIGN's onboarding rule: rung one (demonstration) must be a complete game on its own and nobody hits a text editor in their first session. Deferred: a third ancient system until this phase's feedback says what it should be (ROADMAP Part 6). Human-gated stories in this epic: 5 of 8 (0 designer decisions or reviews, 3 playtests or self-tests, 2 art, toolchain, CI or commercial), carrying at least 32 calendar days of latency on top of 34 working days.

- **Gate — pass:** Answers R6: new players with no explanation are watched for ten minutes and the belief/truth concept lands — they say, in their own words, that the machine's picture of the world is not the world (ROADMAP Phase 7 gate).
- **Gate — kill:** R6: onboarding the belief/truth concept fails — high bounce, niche within a niche. Stop and redesign the first session before Phase 8; do not ship a build whose first ten minutes lose the player.
- **Can start when:** The Phase 6 gate spike (BLD-177) has been answered — R8 measured and the designer has accepted the number; every Phase 7 build story depends on BLD-177 to encode that. BLD-179 and BLD-180 are decisions and can happen during Phase 6.
- **Estimate:** 34 working days

| Key | Type | Summary | Pri | Days | Depends on | Risk |
|---|---|---|---|---|---|---|
| BLD-179 | Task | Decide which product Phase 8 ships before building onboarding | P0 | 1 | BLD-159 | — |
| BLD-180 | Spike | Design the two ancient systems on paper with the designer | P0 | 2 | BLD-159 | — |
| BLD-181 | Story | Implement the two ancient systems with signature, behaviour, exploit, counter | P0 | 8 | BLD-180, BLD-103, BLD-33, BLD-177 | R4 |
| BLD-182 | Story | Build the first-failure scenario: a beacon lie the player watches happen | P0 | 6 | BLD-179, BLD-177, BLD-108 | R6 |
| BLD-183 | Story | Build the first-session flow on rung one only, with no lecture | P0 | 5 | BLD-179, BLD-182, BLD-177 | R6 |
| BLD-184 | Story | Add the named persistent fleet, service history and wall of the lost | P1 | 5 | BLD-177, BLD-157 | — |
| BLD-185 | Story | Implement Endurance mode | P1 | 4 | BLD-177, BLD-104, BLD-179 | R4 |
| BLD-186 | Task | Run the new-player ten-minute observation test | P0 | 3 | BLD-181, BLD-182, BLD-183, BLD-184, BLD-185 | R6 |

### BLD-179 — Decide which product Phase 8 ships before building onboarding

**Status:** Backlog  ·  **Task**  ·  P0  ·  1 d  ·  depends on BLD-159

ROADMAP Phase 8 offers a fork: early access of the competitive game, or the standalone forensic game carved out of Phases 2 and 5. DESIGN says milestone five is a product — a single-player forensic game about diagnosing why autonomous machines failed is small, novel and shippable by one person, and there is a strong case for shipping it first. The first session in this phase must be built for the product that ships, so the decision belongs before BLD-182, not at the start of Phase 8. Ask the designer; record the answer. Human-gated (product decision): expect about 5 calendar days and 1 round-trip(s) with the designer or testers beyond the 1 working days of work.

Done when:
- [ ] A decision record in docs/ names the Phase 8 product and the reason
- [ ] The record lists which Phase 6 systems the shipped build includes (networked matches, or none) so onboarding targets the right first session
- [ ] BLD-182 and BLD-183 descriptions are updated to match before they start

### BLD-180 — Design the two ancient systems on paper with the designer

**Status:** Backlog  ·  **Spike**  ·  P0  ·  2 d  ·  depends on BLD-159

GLOSSARY: an ancient system is deterministic machinery with an acoustic signature detectable before it is dangerous, a behaviour, an exploit and a counter — not a random hazard. ROADMAP Phase 7 ships exactly two; ARCHITECTURE's AncientSystem trait (signature before hazard, provocable_by) was defined in Phase 3 and exercised by one fixed-cycle hazard whose Phase 1 tuning was 75 s period, 9 s warning, 4 s lethal. Which two systems, what each one's exploit and counter are, and what provocation kinds exist are design questions, and CLAUDE.md says ask rather than invent. Human-gated (ancient-system designs signed off): expect about 7 calendar days and 2 round-trip(s) with the designer or testers beyond the 2 working days of work.

Done when:
- [ ] A one-page design per system: signature (what is heard and how long before lethal), behaviour cycle, hazard volume, exploit (how a player deliberately triggers it via provocable_by), counter
- [ ] Each design says what a spectator should be able to read in the replay when an agent dies to it
- [ ] Both signed off by the designer before BLD-181 starts

### BLD-181 — Implement the two ancient systems with signature, behaviour, exploit, counter

**Status:** Backlog  ·  **Story**  ·  P0  ·  8 d  ·  depends on BLD-180, BLD-103, BLD-33, BLD-177  ·  retires R4

Two impl AncientSystem plus content entries with stable AncientKindIds, per the BLD-180 designs and ARCHITECTURE's trait: signature(&AncientState) is Some strictly before hazard() is Some, step() runs against WorldView with the stateless DeterministicRng, provocable_by() lists the deliberate triggers. Phase 1's lesson on the hazard cycle: a longer period and a shorter kill make passing through survivable, so dying there is a decision that went wrong rather than a toll booth. Sim-crate work — lint, canary and the three-platform hash apply. No third system (ROADMAP Part 6).

Done when:
- [ ] Two AncientSystem implementations registered by AncientKindId in content; content validation passes
- [ ] A test per system asserts signature() becomes Some at least the designed lead before hazard() becomes Some, across a full cycle
- [ ] Each system's exploit is reachable by a policy through an action and each counter is expressible with the predicate vocabulary; both demonstrated in a headless match with a hand-written policy
- [ ] Death to either system produces a wreck, an audible crash, and a failure-attribution chain in the Phase 5 replay that names the system
- [ ] The 1,000-match batch remains bit-identical across three platforms with both systems active

### BLD-182 — Build the first-failure scenario: a beacon lie the player watches happen

**Status:** Backlog  ·  **Story**  ·  P0  ·  6 d  ·  depends on BLD-179, BLD-177, BLD-108  ·  retires R6

ROADMAP Phase 7: teach belief-versus-truth without a lecture; the first failure should be a beacon lie the player watches happen. Phase 1 already proved the beat on one seed: a spoofed fix moves the estimate far beyond what the ellipse allowed, the map tears, the agent walks confidently into walls, and the only in-belief tell is the fix surprise. This story reproduces that beat as a new player's first match on the real sim: a pre-built named agent, a rival that places a spoof through BLD-106 (BLD-108's second benchmark seed, where the spoofed player walks into the ancient hazard, is the candidate scenario), and a replay that opens in enter-perception mode at the moment the estimate and the truth parted. Captions state belief facts (moved 34 cells when it expected 3), never 'you were spoofed' (Phase 1 lesson). Human-gated (designer dry runs): expect about 3 calendar days and 1 round-trip(s) with the designer or testers beyond the 6 working days of work.

Done when:
- [ ] A scripted-seed first match in which the player's agent is spoofed before the extraction window and is lost or comes home wrong; the scenario is deterministic across platforms
- [ ] The post-match replay opens on both layers at the spoof tick with the fix-jump vector shown; enter-perception mode is one click away
- [ ] No text explains belief versus truth before or during the match; the only explanation is the replay
- [ ] Five designer-run dry runs from a fresh profile reach the replay without a crash or a missed beat

### BLD-183 — Build the first-session flow on rung one only, with no lecture

**Status:** Backlog  ·  **Story**  ·  P0  ·  5 d  ·  depends on BLD-179, BLD-182, BLD-177  ·  retires R6

DESIGN: rung one (demonstration) has to be complete on its own, a purchased behaviour is a component not a black box, and nobody should hit a text editor in their first session. The first session is: name an agent, prep with a pre-built loadout, watch the first match (BLD-182), read the replay, correct by demonstration through the Phase 4 induction port, go again. It must work for the product chosen in BLD-179. The audience is the Factorio and Kerbal adult (DESIGN), so the flow trusts the player to read and refuses to explain. Human-gated (designer dry run): expect about 3 calendar days and 1 round-trip(s) with the designer or testers beyond the 5 working days of work.

Done when:
- [ ] A fresh profile reaches prep, first match, replay, demonstration correction, second match, with no screen that is a tutorial page
- [ ] The node editor and any text authoring are not reachable from the first session's menus
- [ ] The correction step uses the real induction path and produces a schema-valid Policy with the player as author
- [ ] Time from launch to second match is under fifteen minutes in a designer-run dry run

### BLD-184 — Add the named persistent fleet, service history and wall of the lost

**Status:** Backlog  ·  **Story**  ·  P1  ·  5 d  ·  depends on BLD-177, BLD-157

DESIGN: agents are roughly dog-sized, you own several at once and expect to lose some; the emotional register is my drone, not my vehicle; progression is what you learned and built, not a level number. ROADMAP Phase 7: named persistent fleet, service history, wall of the lost. Each agent persists across sessions with a name, its matches, cargo returned, and how it was lost — the cause taken from the Phase 5 failure-attribution chain in belief terms. Lost agents move to the wall.

Done when:
- [ ] Agents have persistent names and a per-agent service record (matches, extractions, cargo, loss cause) stored locally and, for networked play, on the server profile
- [ ] The wall of the lost lists every lost agent with cause and a link that opens its final replay at the failure tick
- [ ] Loss causes use belief-space language from the attribution chain, never ground-truth language the player could not have known during the run
- [ ] No level, rank or XP number appears anywhere in the fleet UI

### BLD-185 — Implement Endurance mode

**Status:** Backlog  ·  **Story**  ·  P1  ·  4 d  ·  depends on BLD-177, BLD-104, BLD-179  ·  retires R4

DESIGN's modes table: Endurance has no opponents; how deep and how long before you lose everything; solo, meditative, unbounded; the mode people will play at 2am. ROADMAP Phase 7 lists it as the second MatchMode after Extraction. A single agent, no extraction deadline, score is depth reached and time survived; the match ends when the agent is lost. Sim-crate work under the determinism rules. This is also the second objective DESIGN's anti-calcification rule (objectives vary) needs; Survey and Race are scheduled as BLD-204 and BLD-205, not built here.

Done when:
- [ ] impl MatchMode for Endurance registered by stable ID; a headless batch of Endurance runs is bit-identical across three platforms
- [ ] Score is max depth reached and ticks survived; the match ends on agent loss and the replay shows the causal chain
- [ ] Playable from the client menus in single-player and, if BLD-179 chose the networked product, from the lobby as a solo mode
- [ ] Endurance results appear in the agent's service history and the wall of the lost

### BLD-186 — Run the new-player ten-minute observation test

**Status:** Backlog  ·  **Task**  ·  P0  ·  3 d  ·  depends on BLD-181, BLD-182, BLD-183, BLD-184, BLD-185  ·  retires R6

The Phase 7 gate: new players, no explanation, watched to see whether the concept lands in ten minutes (ROADMAP). This is a human playtest; CLAUDE.md says report that the build is ready for the gate, never that the gate is met. Use the Phase 1 rubric style — observable behaviours, when, how scored — and record the minute of disengagement so a pacing problem and a design problem can be told apart. Human-gated (five new-player sessions): expect about 14 calendar days and 1 round-trip(s) with the designer or testers beyond the 3 working days of work.

Done when:
- [ ] At least five players who have never seen the game, no explanation beyond how to start, each watched for ten minutes with observer notes
- [ ] For each: whether and when they said in their own words that the machine's picture is not the world; whether they opened the replay unprompted; the minute they disengaged if they did
- [ ] A written report in docs/ with the rubric, the per-player notes and a readiness statement; no claim that the gate is met
- [ ] If the concept does not land for most players, a one-page diagnosis of which step lost them before any Phase 8 work

## BLD-187 — Ship something

**Phase Phase 8 — Ship something.** Put a purchasable build in front of people who are not friends. ROADMAP Phase 8: early access, or the standalone forensic game carved out of Phases 2 and 5; either way a thing people can buy, an audience, and feedback that is not from friends. DESIGN: the failure mode for a project like this is never shipping, and milestone five is a product on its own. Deferred past this phase on purpose: matchmaking, ranked, skins and cosmetics (ROADMAP Part 6). Only one of the two products is built; the estimate assumes whichever is chosen. Human-gated stories in this epic: 5 of 7 (2 designer decisions or reviews, 0 playtests or self-tests, 3 art, toolchain, CI or commercial), carrying at least 73 calendar days of latency on top of 33 working days.

- **Gate — pass:** No gate is stated in ROADMAP. The outcome is: a build is purchasable on a store, a feedback channel exists, and feedback has arrived from people who are not friends.
- **Gate — kill:** None stated. DESIGN names the only failure: never shipping. Nine in ten multi-year solo projects die; the survivors shipped something small first.
- **Can start when:** The Phase 7 gate report (BLD-186) exists and the designer accepts the result, and BLD-179 has named the product; BLD-188 depends on both.
- **Estimate:** 33 working days

| Key | Type | Summary | Pri | Days | Depends on | Risk |
|---|---|---|---|---|---|---|
| BLD-188 | Task | Write the cut list for the shipping build | P0 | 2 | BLD-179, BLD-186 | — |
| BLD-189 | Story | Build out the product-specific content the cut list requires | P0 | 10 | BLD-188 | — |
| BLD-190 | Story | Produce release builds from CI whose replays verify | P0 | 4 | BLD-188, BLD-37 | R4 |
| BLD-191 | Task | Set up the store page and the commercial prerequisites | P0 | 5 | BLD-188 | — |
| BLD-192 | Story | Open a feedback channel that carries replays | P1 | 3 | BLD-190 | R7 |
| BLD-193 | Task | Run the stability soak and set the min-spec floor | P1 | 4 | BLD-189, BLD-190 | — |
| BLD-194 | Task | Launch, then write the first-month response report | P1 | 5 | BLD-189, BLD-190, BLD-191, BLD-192, BLD-193 | R6 |

### BLD-188 — Write the cut list for the shipping build

**Status:** Backlog  ·  **Task**  ·  P0  ·  2 d  ·  depends on BLD-179, BLD-186

From the BLD-179 decision, list exactly what ships and what does not. If early access: the Phase 6 networked match, onboarding, fleet, Endurance. If the standalone forensic game: single-player scenarios over generated caves, the demonstration rung, the replay and enter-perception screens, Endurance, with no networking. Either way: no matchmaking, no cosmetics, no market (ROADMAP Part 6). CLAUDE.md: do not add features; a cut list is how that rule survives a launch. Human-gated (cut-list sign-off): expect about 3 calendar days and 1 round-trip(s) with the designer or testers beyond the 2 working days of work.

Done when:
- [ ] A one-page cut list in docs/ with an in column and an out column, each item pointing at the phase story that built it
- [ ] Every out item carries the ROADMAP Part 6 reason or a one-line reason of its own
- [ ] The designer has signed the list; anything not on it is not worked on during Phase 8

### BLD-189 — Build out the product-specific content the cut list requires

**Status:** Backlog  ·  **Story**  ·  P0  ·  10 d  ·  depends on BLD-188

The two Phase 8 products need different finishing work. Early access needs the match loop to survive strangers: a lobby with no friends in it, server uptime, a first-match experience that works with three other new players. The standalone forensic game needs a run of generated scenarios that each end in a legible failure — the Phase 7 beacon lie first, then echoes, collapse, an ancient system — with the demonstration correction loop between them (DESIGN: debugging as a place you go). Only one branch is built. Human-gated (strangers weekend or forensic scenario content): expect about 14 calendar days and 1 round-trip(s) with the designer or testers beyond the 10 working days of work.

Done when:
- [ ] Early-access branch: a stranger can install, reach a lobby, play a four-team match with strangers, and open the published replay, with the server staying up for a weekend of continuous matches
- [ ] Forensic branch: at least eight generated scenarios in sequence, each with a distinct failure cause the attribution chain names, playable start to finish from a fresh profile without networking
- [ ] Either branch: everything on the cut list's in column is reachable from the shipped menus and nothing on the out column is

### BLD-190 — Produce release builds from CI whose replays verify

**Status:** Backlog  ·  **Story**  ·  P0  ·  4 d  ·  depends on BLD-188, BLD-37  ·  retires R4

DETERMINISM.md's four dependents all assume the shipped binary produces the same hashes as CI. Release builds must come from the pinned toolchain and the pinned build profile (the overflow-checks decision from Phase 0), on all three platforms the CI matrix already covers, with the content pack hash and version string surfaced in-game so a bug report can be matched to a build. A replay recorded on the shipped build must verify with the harness built from the same commit.

Done when:
- [ ] A tagged commit produces Windows, macOS and Linux release artefacts from CI with no manual build steps
- [ ] The in-game about screen shows version, commit and content pack hash
- [ ] A MatchRecord recorded on each shipped platform verifies with the harness from the same tag and reproduces the same final hash on the other two
- [ ] Crash reporting captures the version and attaches the current MatchRecord when one exists

### BLD-191 — Set up the store page and the commercial prerequisites

**Status:** Backlog  ·  **Task**  ·  P0  ·  5 d  ·  depends on BLD-188

A thing people can buy needs a store (Steam or itch), a page with honest early-access disclosure, a price, and the legal and tax entity that receives money. ROADMAP defers real-money payouts to players until there is a company, but selling the game at all requires an entity that can invoice a storefront; whether the designer has one is a question, not something to guess at. DESIGN's audience note: adults with money, the Factorio and Kerbal crowd, so the page speaks to them. Human-gated (store page and legal entity): expect about 21 calendar days and 2 round-trip(s) with the designer or testers beyond the 5 working days of work.

Done when:
- [ ] Store page live with build, screenshots and replay clips from real matches, and an early-access or scope disclosure the designer has approved
- [ ] Price set and recorded with a one-line reason
- [ ] Legal/tax entity question answered and recorded; the store account belongs to that entity
- [ ] Store build upload is scripted from the BLD-190 artefacts

### BLD-192 — Open a feedback channel that carries replays

**Status:** Backlog  ·  **Story**  ·  P1  ·  3 d  ·  depends on BLD-190  ·  retires R7

The point of shipping is feedback that is not from friends. Because a full replay is kilobytes (DESIGN: seed plus input log), a bug report or a story can carry the whole match; that is the single most useful thing a player can send. Minimal opt-in telemetry (matches played, losses, replay views, and later publish and adopt events) is needed here so Phase 9's 1% adoption metric has a denominator when it arrives.

Done when:
- [ ] In-game link to a feedback destination (forum, Discord or store hub) approved by the designer
- [ ] A one-click report attaches the current or last MatchRecord and the build version
- [ ] Opt-in telemetry with a written list of exactly which events are sent; nothing else is sent
- [ ] A received report replays locally through the Phase 5 replay screen from the attachment alone

### BLD-193 — Run the stability soak and set the min-spec floor

**Status:** Backlog  ·  **Task**  ·  P1  ·  4 d  ·  depends on BLD-189, BLD-190

Before strangers pay for it: hours of unattended headless batch matches and client sessions without a crash, a known-issues list, and a measured minimum machine on which the client holds its frame rate with the Phase 5 point cloud at full size (Phase 1 saw a 16k-point map cost 39 ms per paint in Python; Godot is faster, but the lesson is to measure rather than assume). Human-gated (soak and min-spec): expect about 5 calendar days and 0 round-trip(s) with the designer or testers beyond the 4 working days of work.

Done when:
- [ ] 24 hours of headless batch matches and 8 hours of client sessions on the release build with zero crashes, or a fixed root cause for each
- [ ] Min-spec machine named on the store page; the client holds its target frame rate at match end on it
- [ ] Known-issues list published with the build

### BLD-194 — Launch, then write the first-month response report

**Status:** Backlog  ·  **Task**  ·  P1  ·  5 d  ·  depends on BLD-189, BLD-190, BLD-191, BLD-192, BLD-193  ·  retires R6

Ship, then spend the first month reading what strangers say. ROADMAP wants feedback that is not from friends; DESIGN wants to know whether the forensics loop is the good part (milestone five) and, for early access, whether competition holds up (milestone seven). Separate what they did not understand from what broke, and decide with the designer whether Phase 9 proceeds or the first session gets another pass. Human-gated (launch and first month): expect about 30 calendar days and 1 round-trip(s) with the designer or testers beyond the 5 working days of work.

Done when:
- [ ] Build live on the store on a recorded date
- [ ] A first-month report: units, refunds, top ten feedback themes split into did-not-understand versus broke, and the replays that best show each
- [ ] A written decision on whether to proceed to Phase 9, iterate onboarding, or pause, with the designer's sign-off

## BLD-195 — Market and seasons

**Phase Phase 9 — Market and seasons.** Run the behaviour market on in-game currency, with every listing auto-evaluated on a rotating benchmark set and its replays attached, seeded honestly with first-party behaviours; then ship season one by shifting generation weights across the eight world axes, changing one ancient system's state, and publishing the transition as a shared event (ROADMAP Phase 9, DESIGN market and seasons sections). Answers R7. Deferred: real-money payouts until there is a company; moderation tooling sized to the market once it exists (ROADMAP Part 6). DESIGN's anti-calcification rule needs objectives to vary: Survey (BLD-204) and Race (BLD-205) are scheduled here at low priority so they are held by a story, and the designer may pull either earlier. Human-gated stories in this epic: 4 of 12 (2 designer decisions or reviews, 0 playtests or self-tests, 2 art, toolchain, CI or commercial), carrying at least 45 calendar days of latency on top of 45 working days.

- **Gate — pass:** Answers R7: over a stated window after season one, at least 1% of active players have published a behaviour that at least one other player adopted (ROADMAP Phase 9 gate).
- **Gate — kill:** R7: not enough authors to sustain a market — a ghost-town store that looks dead. If the metric is far below 1%, the response is to find where authoring stalls (rung one correction or rung two composition), not to add more first-party listings.
- **Can start when:** Phase 8 has shipped and the first-month report (BLD-194) recommends proceeding; BLD-197 and BLD-198 depend on BLD-194 to encode that, and there is an active playerbase to be the denominator. BLD-196 can be decided during Phase 8.
- **Estimate:** 45 working days

| Key | Type | Summary | Pri | Days | Depends on | Risk |
|---|---|---|---|---|---|---|
| BLD-196 | Task | Record the market rules before writing market code | P0 | 2 | BLD-186 | R7 |
| BLD-197 | Story | Build the listing service for Subtree policies with provenance | P0 | 6 | BLD-196, BLD-194 | R7 |
| BLD-198 | Story | Add the in-game currency ledger with no real-money path | P0 | 4 | BLD-196, BLD-194 | R7 |
| BLD-199 | Story | Auto-evaluate every listing on the benchmark set with replays attached | P0 | 6 | BLD-197, BLD-38, BLD-122 | R7 |
| BLD-200 | Task | Seed the market with first-party behaviours, labelled honestly | P1 | 2 | BLD-197, BLD-199 | R7 |
| BLD-201 | Story | Build the market client: browse, verify, buy, slot as a component | P0 | 6 | BLD-197, BLD-199, BLD-198 | R7 |
| BLD-202 | Story | Instrument publish-and-adopt for the 1% gate | P0 | 3 | BLD-201 | R7 |
| BLD-203 | Story | Ship season one as a world change and a shared event | P0 | 6 | BLD-197, BLD-199 | R7 |
| BLD-204 | Story | Implement Survey mode scoring map accuracy against ground truth inside the sim | P2 | 3 | BLD-196, BLD-104, BLD-76, BLD-194 | R7 |
| BLD-205 | Story | Implement Race mode: first to reach a single generated anomaly | P2 | 2 | BLD-196, BLD-73, BLD-91, BLD-104, BLD-194 | R7 |
| BLD-206 | Story | Add moderation tooling sized to the observed market | P2 | 3 | BLD-201 | — |
| BLD-207 | Task | Evaluate the R7 gate over the stated window | P0 | 2 | BLD-200, BLD-202, BLD-203 | R7 |

### BLD-196 — Record the market rules before writing market code

**Status:** Backlog  ·  **Task**  ·  P0  ·  2 d  ·  depends on BLD-186  ·  retires R7

DESIGN's open decisions and market section leave rules the code must embody: stolen behaviours resold or private-use-only with attribution (DESIGN leans private-use-only), listings are composable Subtrees and never whole agents, in-game currency only with no real payouts until there is a company, and what 'adopt' means for the gate metric (slotted into a tree and used in at least one match is the obvious reading, but it is the designer's call). CLAUDE.md: ask rather than invent. Each answer is recorded once and referenced by the stories below. Human-gated (market rules decided): expect about 5 calendar days and 1 round-trip(s) with the designer or testers beyond the 2 working days of work.

Done when:
- [ ] A decision record in docs/ answers: resale of salvaged policies, the listing unit, how currency is earned and what it can buy, the definition of adopt for the gate, and the season-one benchmark set size
- [ ] The record restates the content-hash-versus-season-flag semantics chosen in Phase 3 so season one does not change them by accident

### BLD-197 — Build the listing service for Subtree policies with provenance

**Status:** Backlog  ·  **Story**  ·  P0  ·  6 d  ·  depends on BLD-196, BLD-194  ·  retires R7

ARCHITECTURE: BtNode::Subtree { source: PolicyRef } is the unit of sale, and Policy carries schema, author and a provenance chain. A listing is a Subtree policy plus metadata; DESIGN: composable modules such as a search pattern, a threat response, a navigation stack, a fallback ladder, a sonar discipline policy — not whole agents. The service stores listings server-side, enforces the BLD-196 resale rule on policies whose provenance shows salvage, and tags each with the season content hash it was published under so old listings still parse in later seasons (ARCHITECTURE extension rules 1 and 3).

Done when:
- [ ] Publishing accepts only a Subtree-rooted Policy with a valid schema; whole-agent policies are rejected with a clear reason
- [ ] A salvaged policy is publishable or not exactly per the BLD-196 decision; either way the original author appears on the listing
- [ ] Listings carry the season content hash and schema; a season-one listing loads under a later schema through the migration chain in a test
- [ ] Listing storage survives server restart and is backed up

### BLD-198 — Add the in-game currency ledger with no real-money path

**Status:** Backlog  ·  **Story**  ·  P0  ·  4 d  ·  depends on BLD-196, BLD-194  ·  retires R7

ROADMAP Phase 9: in-game currency only, no real payouts until there is a company; DESIGN: real money is a decision, not a default, and Roblox's payout loop is a regulatory and moderation surface that will consume a solo developer. Currency is earned and spent per the BLD-196 record, held in a server-side ledger, and there is deliberately no code path that converts between it and money in either direction.

Done when:
- [ ] Server-side ledger with an append-only transaction log; balances are derivable from the log
- [ ] Earning sources and spend sinks match the BLD-196 record exactly
- [ ] A test asserts no purchase or payout endpoint accepts or emits a real-money amount or payment-provider token
- [ ] Ledger entries reference the match or listing that caused them so disputes can be traced

### BLD-199 — Auto-evaluate every listing on the benchmark set with replays attached

**Status:** Backlog  ·  **Story**  ·  P0  ·  6 d  ·  depends on BLD-197, BLD-38, BLD-122  ·  retires R7

DESIGN: a listing carries verified statistics, not seller claims; because the simulation is deterministic and seeds are published, every behaviour can be re-run automatically against a rotating benchmark set of caves, showing how it performed on which cave types with the replays attached. This is the market-verification dependent of DETERMINISM.md and the reason the Phase 0 batch executor exists. Wrap the listing's Subtree in a reference harness tree, run it across the season's benchmark seeds through blindside-harness, and attach score and MatchRecords.

Done when:
- [ ] On publish and on every season change, each listing is run over the season's benchmark seeds by the harness batch executor and its score per cave type is stored with the MatchRecords
- [ ] Any player can download an attached MatchRecord and reproduce its final hash locally with the harness
- [ ] Evaluation is queued and rate-limited so a publish storm does not stall the server; a failed evaluation leaves the listing unverified, never scored
- [ ] The benchmark seed set is versioned and referenced by the listing so old scores are attributable to the set that produced them

### BLD-200 — Seed the market with first-party behaviours, labelled honestly

**Status:** Backlog  ·  **Task**  ·  P1  ·  2 d  ·  depends on BLD-197, BLD-199  ·  retires R7

ROADMAP Phase 9: seed with your own behaviours, labelled honestly as first-party — the store must not look dead on day one and must not deceive players about who wrote what. Use the Phase 4 reference policies and the Phase 7 ancient-system counters, split into Subtrees, evaluated by BLD-199 like any other listing.

Done when:
- [ ] At least six first-party Subtree listings live at market launch, each with verified scores and replays
- [ ] Every first-party listing carries a distinct first-party flag visible in browse and on the node
- [ ] First-party listings receive no ranking preference in browse or counters

### BLD-201 — Build the market client: browse, verify, buy, slot as a component

**Status:** Backlog  ·  **Story**  ·  P0  ·  6 d  ·  depends on BLD-197, BLD-199, BLD-198  ·  retires R7

DESIGN: a purchased behaviour is a component, not a black box — you slot someone else's search pattern into your own architecture and it becomes part of a thing you built. The market screen in Godot lists Subtrees with their verified statistics and attached replays, lets a player buy with currency, and puts the purchase into the Phase 4 node editor as a Subtree node with its provenance visible. Anti-calcification: DESIGN wants counters to be profitable, so the screen surfaces counters to top sellers rather than only top sellers.

Done when:
- [ ] Browse and sort listings by verified score per cave type; open an attached replay in the replay screen from the listing
- [ ] Buying deducts currency through the ledger and the Subtree appears in the node editor palette with author and provenance shown on the node
- [ ] A purchased Subtree slots into an existing tree, compiles to bytecode, and runs in a match unchanged
- [ ] A counters section lists behaviours whose benchmark results beat the current top sellers on the same seeds

### BLD-202 — Instrument publish-and-adopt for the 1% gate

**Status:** Backlog  ·  **Story**  ·  P0  ·  3 d  ·  depends on BLD-201  ·  retires R7

The Phase 9 gate is quantitative: if at least 1% of active players publish a behaviour anyone adopts, the economy works (ROADMAP). Count active players over the window, count players who published at least one listing that at least one other player adopted per the BLD-196 definition, and report the ratio. Keep it to those events; DESIGN warns against over-tuning to telemetry, and the BLD-192 opt-in list is the only place events are added.

Done when:
- [ ] A report computes active players, publishers, publishers-with-an-adopter, and the ratio over a configurable window
- [ ] Adopt is measured exactly as the BLD-196 definition, and the events are added to the BLD-192 telemetry list
- [ ] The report runs from a script against the server data and its output is checked into docs/ per window

### BLD-203 — Ship season one as a world change and a shared event

**Status:** Backlog  ·  **Story**  ·  P0  ·  6 d  ·  depends on BLD-197, BLD-199  ·  retires R7

ROADMAP: season one shifts generation weights, changes an ancient system's state, and publishes the transition as an event. DESIGN Seasons: rebalancing that takes nothing away — the cave is different; a season changes generation weights across the eight world axes, the benchmark set listings are scored against, occasionally a module or chassis behind a season flag (ARCHITECTURE extension rule 5), never a direct stat edit; preserve the archive so old behaviours stay usable; run the transition as a shared visible event such as a flood, collapse or thermal shift. Season design notes must cite the solved policy being disrupted, not a difficulty target (DESIGN: don't over-tune to telemetry). Human-gated (season design note): expect about 7 calendar days and 1 round-trip(s) with the designer or testers beyond the 6 working days of work.

Done when:
- [ ] A season config holds the eight-axis generation weights, the benchmark seed set, the enabled season flags and one ancient system's state change; loading it changes generation and the content hash exactly as the Phase 3 semantics say it should
- [ ] No existing chassis or module stat is edited; any new content is behind the season flag and absent from the previous season's hash
- [ ] Every pre-season policy and listing still loads and runs (deprecated predicates evaluate to their fixed value); a test loads the full pre-season listing set under season one
- [ ] The transition is visible in every player's first match of the season and published as an event on the store and feedback channels
- [ ] A season-one design note names the solved policies the change targets, taken from BLD-202's data and the benchmark results

### BLD-204 — Implement Survey mode scoring map accuracy against ground truth inside the sim

**Status:** Backlog  ·  **Story**  ·  P2  ·  3 d  ·  depends on BLD-196, BLD-104, BLD-76, BLD-194  ·  retires R7

DESIGN: 'Survey | Most cave area accurately mapped — accuracy scored against ground truth | Fast, quiet, wide-ranging builds. Punishes drift directly and explicitly.' and 'Scoring map accuracy against ground truth makes the game's central idea into the literal win condition ... It is the purest expression of the design and it should exist even if it never becomes the popular mode.' ARCHITECTURE grows match modes 1 → 4; the plan ships Extraction (BLD-104) and Endurance (BLD-185) and without this story Survey had no phase. The scorer reads Belief.map and World.cave — a legitimate consumer of truth — so it lives inside blindside-sim beside the Extraction scorer and emits only a number; no policy path may reach its inputs. Placement in Phase 9 is a proposal (DESIGN's anti-calcification rule needs objectives to vary before the market and season one); the designer may pull it earlier. Human-gated (designer-defined accuracy metric): expect about 3 calendar days and 1 round-trip(s) with the designer or testers beyond the 3 working days of work.

Done when:
- [ ] impl MatchMode for Survey registered by stable ID; score is the designer-defined map-accuracy metric computed inside blindside-sim from Belief.map against World.cave and exposed only as a number
- [ ] A compile-fail case proves Predicate, Action, Policy and BeliefUpdater cannot reach the scorer's inputs; the scorer is not reachable from any FFI or net export
- [ ] Headless Survey batch is bit-identical on Linux, macOS and Windows; the BLD-199 benchmark set includes Survey seeds so listings are scored per mode
- [ ] Playable from the client menus and the lobby; results appear in the service history

### BLD-205 — Implement Race mode: first to reach a single generated anomaly

**Status:** Backlog  ·  **Story**  ·  P2  ·  2 d  ·  depends on BLD-196, BLD-73, BLD-91, BLD-104, BLD-194  ·  retires R7

DESIGN: 'Race | First to reach a single anomaly placed somewhere in the system | Long-range detection, aggressive commitment, high-risk routing.' The generator places one strong anomaly the magnetometer (BLD-91) detects at long range; the first agent truly within its capture radius wins. It is the second of the two modes DESIGN lists that ROADMAP never schedules, and it is needed for the anti-calcification rule that objectives vary across modes. Placement in Phase 9 is a proposal for the designer.

Done when:
- [ ] blindside-gen places one strong anomaly per seed reachable from every entry shaft; the magnetometer returns it at long range with false finds per the magnetic axis (BLD-91)
- [ ] impl MatchMode for Race registered by stable ID; the match ends deterministically when an agent is truly within the content capture radius, scored by tick; a no-finish match ends at the content length
- [ ] Headless Race batch is bit-identical on three platforms; the BLD-199 benchmark set includes Race seeds
- [ ] Playable from the client menus and the lobby

### BLD-206 — Add moderation tooling sized to the observed market

**Status:** Backlog  ·  **Story**  ·  P2  ·  3 d  ·  depends on BLD-201

ROADMAP Part 6 defers moderation tooling to Phase 9 because it scales with the market, which does not exist before this. Build the minimum the observed volume needs: a report flow on listings, a review queue, removal with refund through the ledger, and an author-facing reason. Do not build ahead of the volume; revisit after the first season.

Done when:
- [ ] Players can report a listing with a reason; reports land in a queue the designer can review
- [ ] Removal unpublishes the listing, refunds purchasers through the ledger log, and records the reason
- [ ] The queue size and turnaround are visible so the tooling can be resized from data

### BLD-207 — Evaluate the R7 gate over the stated window

**Status:** Backlog  ·  **Task**  ·  P0  ·  2 d  ·  depends on BLD-200, BLD-202, BLD-203  ·  retires R7

After season one has run for the window fixed in BLD-196, run the BLD-202 report and write up the result against the 1% criterion. CLAUDE.md: report readiness and the number, not that the gate is met; the designer decides. If the number is low, the write-up says which rung authors stalled at rather than proposing more first-party listings. Human-gated (window evaluation): expect about 30 calendar days and 1 round-trip(s) with the designer or testers beyond the 2 working days of work.

Done when:
- [ ] The BLD-202 report for the full window is checked into docs/ with the ratio and the raw counts
- [ ] A written comparison to the 1% criterion and, if below it, a diagnosis of where authoring stalls (rung one correction, rung two composition, or publishing itself)
- [ ] A recommendation for season two that follows DESIGN's rule: disrupt what players solved, do not tune a slider

## Reviewer verdicts on this plan

- {'lens': 'completeness against the documents', 'verdict': "Coverage of the five extracts is high: every ROADMAP phase deliverable, every PHASE-0-HARNESS and DETERMINISM enforcement item, every ARCHITECTURE core type, and every Phase 1 finding maps to at least one story, and the gate handling (report ready, never met; Phase 0 in parallel; Phase 3 blocked on 1, 2, 0) is respected throughout. The uncovered work is almost entirely DESIGN-only material that ROADMAP never scheduled and the draft therefore drops or merely acknowledges: five of seven interference methods, Survey and Race modes, the Scout/Hauler/Swimmer chassis classes, gait-dependent noise, movement-stirred silt, and rung-three text authoring. One gap is a real mechanism the plan's own later stories assume (P3-S41, P5-S16) but no story builds: the spoof module and place/relocate-beacon action. Two structural defects need fixing before the plan is rendered: the P5 epic's cross-epic depends_on keys point at the wrong stories in P0, P1, P3 and P4, and P5-S03 duplicates P3-S10. Not ready to render as-is; fix the P5 keys, add P3-S47, and add the decision spikes (P3-S46, P4-S26, P6-S15) so the unscheduled DESIGN systems are held by a story rather than silently lost, then it is.", 'disposition': 'Applied in full: P5 cross-epic keys corrected; BLD-145 scoped to client-side consumption of the BLD-76 export; spoof module+action, chassis decision spike, gait, transient silt, rung-three spike, interference decision spike and two interference stories, Survey and Race added; world-axis ACs added to locomotion, acoustics, sonar and loadout; behaviour-recovery module entry, fix surprise in Phase 2 traces, Purpose enum, and the in-world-authoring decision added.', 'note': "The verdict text is the reviewer's own words and cites the draft keys it reviewed (P<phase>-S<nn>); the disposition uses final BLD keys."}
- {'lens': 'constraints and ordering', 'verdict': "On constraints the plan is mostly sound: no story introduces f32/f64, HashMap iteration, std::time or rand into blindside-sim/vm/gen except the deliberate P0-S14 injection, and the World/Belief invariant is enforced by stories at every boundary (P0-S04/S18 module privacy and compile-fail scaffold, P3-S08 single sensor module, P3-S09 Policy::evaluate compile-fail, P3-S10 sanctioned ReplayFrame, P4-S05 VM host, P5-S02/S03 FFI surface, P6-S03 wire protocol). The residual constraint problems are real but bounded: cargo features are used as a privacy boundary and feature unification defeats that (P0-S21 needed); SlotMap keys as entity IDs violate DETERMINISM rules 6 and 7 and make P3-S07's own test unpassable (P3-S46 needed); a handful of test ACs need randomness, timing or float references inside constrained crates (P0-S22 needed, timing AC moved to the harness); the lint is not sequenced before the first sim code as DETERMINISM demands. On ordering the plan is not ready: gates live in can_start_when prose, but tools/render_dev_plan.py schedules from depends_on alone and marks empty-depends_on stories 'Ready now', so as rendered today P2-S01, P3-S01..S04, P4-S01, P4-S14, P7-S06, P7-S07 (sim work) and others appear startable, every P3 constrained-crate story chains only to P0-S01 rather than to the lint, the three-OS CI, Phase 0 readiness or the Phase 2 gate, and P5 cites four wrong cross-epic keys that render silently. Phase 0 starting now is defensible and matches the brief, but it contradicts the literal spec text and must be recorded as a designer decision with an empty-sim assertion at P0-S20 and P3-S00. Fix the depends_on chain (P2-S01 -> P1-S12; add P3-S00 and P4-S00 as anchors; P6-S03 -> P5-S18; P8-S01 -> P7-S08; P9-S02/S04 -> P8-S07; correct P5's keys; give P7-S07 predecessors), add the four missing stories, and the plan respects CLAUDE.md's build order while letting the harness start immediately.", 'disposition': 'Applied in full: gate-entry anchors added for Phase 3 and Phase 4 and wired into every code story; Phase 2, 6, 7, 8 and 9 gates encoded in depends_on; lint sequenced before the empty sim; feature-unification guard, deterministic test helpers and record-assigned entity IDs added; the Phase-0-now interpretation put to the designer in BLD-20 with empty-sim assertions at BLD-40 and the Phase 3 anchor; duplicate command-channel and wrecks questions removed; stable tie-break, TRN-home and CORDIC questions, induct lint scope and benchmark ownership fixed.', 'note': "The verdict text is the reviewer's own words and cites the draft keys it reviewed (P<phase>-S<nn>); the disposition uses final BLD keys."}
- {'lens': 'honesty of estimates and Phase 1 lessons', 'verdict': "Not ready as drafted. On estimates: the plan is internally consistent (every epic total sums correctly) but sums to 416 working days to Phase 8, which the repo's own renderer turns into 41.6 months against ROADMAP's 18-24 month floor, and it never says so; only the P3 goal admits any excess. The single velocity data point (all of Phase 1 built in about 4.5 hours of wall-clock today, gate still unrun) says the working-day unit is wrong in the other direction for construction and irrelevant for the ~22 designer decisions and five playtests that will actually set the calendar. Put the arithmetic and the unit in front of the designer now (P1-S16). On Phase 1 lessons: the draft was written against a stale tree. Five files carry an uncommitted retune with new designer decisions (gate is two viewings, sonar first; echo moved to 2:35 because it merged into the rival contact; lidar water returns as a wall; ancient phase 30; map-aware steering that moved every path). P1-S05 must apply the decision rather than re-ask it (blocker), P1-S02 must split and re-verify the beats, P3-S21 builds the rejected lidar-water alternative, and P5-S16 fixes the wrong configuration for the Phase 5 comparison. Three measured lessons have no Phase 3 story at all and will be rediscovered the hard way: the spoof as a Belief-only rival action (P3-S46; the Phase 1 arming rule is truth-side and does not port), map-aware steering off the belief map with the 28 s give-up (P3-S47), and the same-passage echo-merge failure (P3-S30/S16 ACs). The panel's finding that 'do I ping' is a cooldown because no predicate reads contacts is missing from the vocabulary stories and would let the Phase 4 gate pass without testing the game's central tension. Everything else measured in tuning.py, the commit bodies and PHASE-1-OPEN-QUESTIONS Parts 1 and 4 is carried, mostly as acceptance criteria in P3-S18/S19/S22/S23/S27/S28/S29/S30/S31/S35/S37 and P5-S08/S09/S10/S17; the remaining gaps are minor number and overlay omissions listed above.", 'disposition': 'Applied in full: every story labelled agent-buildable or human-gated with calendar latency and round-trips on the human-gated ones and per-epic counts in each goal; BLD-7 carries the velocity baseline and the ROADMAP-floor decision; BLD-9 applies the two-viewings decision, BLD-3 splits the retune per concern with re-verified beats, BLD-10/BLD-17 re-measure and extend the reference table; lidar water-as-wall, phase offset 30 s, non-monotonic Recall sweep, the trench seed, the echo-merge fixture, the Belief-only spoof story, map-aware steering, contact-reading predicate candidates and the display-overlay lessons are all in the plan; BLD-147/BLD-159 judge the sonar viewing.', 'note': "The verdict text is the reviewer's own words and cites the draft keys it reviewed (P<phase>-S<nn>); the disposition uses final BLD keys."}
