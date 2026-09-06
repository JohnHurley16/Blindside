# Glossary

Precise domain vocabulary. Used consistently across all specs and code. Where a word
here has a general English meaning, the definition below is the one that applies.

---

**Agent** — one autonomous machine. Owned by a team, built from a chassis plus modules,
running a policy. Small, roughly dog-sized. Expected to be lost routinely.

**Ancient system** — machinery in the ruins that is still operating. Deterministic, with
an acoustic signature that is detectable *before* it is dangerous, a behavior, an exploit,
and a counter. Not a random hazard.

**Belief** — an agent's model of the world, assembled from sensor returns. Contains a
pose estimate, an occupancy map, contact tracks, known beacons, and inventory. **This is
the only world representation a policy may read.** Frequently wrong.

**Chassis** — the agent's body. Determines size, slot count, locomotion, noise, and which
passages it can enter. Classes: Scout, Surveyor, Hauler, Swimmer.

**Commit** — the moment control leaves the player, roughly 20 seconds after descent.
Before it: full authority, no information. After it: full information, no authority.
The central beat of the design.

**Contact** — an unresolved detection of something that might be another agent, an
ancient system, or an echo. A contact is *not* an identification.

**Drift** — accumulated error in the pose estimate from integrating motion without an
external fix. Grows continuously. Not a penalty — it is what dead reckoning does.

**Fix** — an external position observation that collapses drift. Sources: a beacon, or
terrain-relative matching against already-mapped ground. A spoofed beacon produces a fix
that is simply wrong; nothing in the type system distinguishes it.

**Ground truth** — the actual state of the world. Held in `World`. Never visible to
policies, predicates, clients, or renderers. See the invariant in `CLAUDE.md`.

**Loadout** — chassis plus modules, locked at launch and unchangeable once contact is lost.

**Module** — a slotted component. Sensors, beacon racks, cargo bays, and similar. Costs
slots, mass, and power. Visible on the model — silhouette is always honest.

**Passive / active** — passive sensing emits nothing and yields bearing without range.
Active sensing yields range and bearing and announces your position to every listener in
range. *Do I ping?* is the central decision of a match.

**Policy** — the behavior an agent runs. A behavior tree over predicates and actions,
compiled to VM bytecode. Authored three ways: demonstration, node composition, or
recovered from a wreck. All three produce the same artifact.

**Predicate** — a boolean test over `Belief`. The vocabulary policies are built from.
Fixed library with stable IDs.

**Return** — one raw sensor observation. Noisy, sometimes ambiguous, sometimes false.
Returns are fused into belief; they are not truth.

**Run phase** — the six to ten minutes after commit. The player observes belief-space
telemetry and may send scarce, unreliable, low-bandwidth commands. They cannot drive.

**Shadow zone** — a region acoustically invisible from another region, caused by thermal
layering refracting sound. Positional advantage available to players who understand it.

**Spoofing** — placing a false beacon that corrupts a rival's pose estimate. Deals no
damage. The agent then acts correctly on a wrong premise.

**Wreck** — a destroyed agent. Persists for the match, holding its cargo and its policy.
Any agent may salvage one; recovering the policy requires the appropriate module.
