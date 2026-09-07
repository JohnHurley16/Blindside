# Phase 2 — The Junction Test

**Python, throwaway.** Answers R2 (demonstration cannot produce a legible policy), R3
(players cannot diagnose their own failures), R5 (predicate vocabulary is the wrong size).
`ROADMAP.md` names the pieces; `PHASE-2-OPEN-QUESTIONS.md` records the decisions; this file
is the target. Where they disagree, the decisions win.

The one invariant holds here as everywhere: the policy reads Belief, never World. The
sensor layer is one module. `python -m phase2 --invariant` checks it the way Phase 1 did.

---

## What exists

**World.** A seeded branching corridor: a shaft at the root, eight junctions, each with
two or three onward passages, one deposit at a random leaf. Passages have lengths.
Nothing else — no sump, no rival, no machinery. Drift is the only adversary.

**Agent.** Walks passages by itself. Stops at every junction it *believes* it has reached
and waits for a decision. Carries one unit of cargo once it has stood at the deposit.

**Sensing.** Phase 1's odometry — biased heading drift, position sigma growing with
distance — is the uncertainty. The shaft is the only fix. At a junction the agent sees the
passages leaving it (count and bearings), nothing further. Cargo is self-reported.

**Belief.** Believed pose with sigma, the believed junction graph (junctions reached,
passages seen, which have been walked), the believed route back, cargo.

**Base blocks — the day-one items.**
Predicates over Belief: `unexplored_branch_exists` (at the current believed junction),
`uncertainty > θ` (position sigma; θ is fitted, not set), `carrying_cargo`.
Actions: `take_branch` (the left-most unexplored passage here), `return_to_beacon` (walk
the believed route back to the shaft).
Blocks are a *list*. Nothing downstream names the three.

**Drift with teeth.** At a junction the agent takes the passage whose true bearing best
matches the believed bearing of the one it meant to take. When heading error exceeds half
the angle between passages it takes the wrong one. So `return_to_beacon` can fail, and
does more often the further from the shaft it starts.

**Decision tree.** A policy is a tree over predicates with actions at the leaves.
`decide(belief) -> action`. Rendered two ways: as a tree, and as one plain sentence
assembled from the block names.

**Demonstration.** A session where the player makes the choice at each stop, on the
belief-only view. Recorded as (predicate values, sigma, choice) per stop. The tutorial is
staged: run one has no drift and only two blocks exist; run two has drift and the other
three appear; run three is the full problem. Three full runs follow on three seeds.

**Induction.** Minimal separator: the smallest tree over the block list consistent with
every recorded (predicate vector → choice), with θ fitted from the recorded sigmas. When no
consistent separator exists, the two contradicting stops are shown side by side and the
player is asked which one they would do differently.

**Ghost replay.** The induced tree runs on a demonstration's seed beside the demonstration
and the first stop where its choice differs is marked.

**Correction.** Scrub to a stop, take over, choose from there; promote replaces the run's
suffix from that stop; re-induce.

**Evaluation.** Twenty unseen seeds. *A run succeeds when the agent is within the shaft
beacon's range carrying cargo before the tick budget ends; the budget is twice the ticks a
full depth-first walk of that seed's corridor needs.*

---

## Acceptance criteria

Build is ready for the gate when:

- [ ] `python -m phase2 --invariant` passes
- [ ] Headless, on twenty seeds: a depth-first policy that ignores `uncertainty > θ` fails on
      roughly a third; one that turns back at the right θ succeeds on at least nine in ten
      (this is what makes the gate's 70% reachable and the failures worth a replay)
- [ ] Three synthetic demonstrations generated from a known tree induce that tree back,
      including θ within the gap between the nearest recorded sigmas
- [ ] Two demonstrations that contradict each other produce no separator and the query
      names the two contradicting stops
- [ ] The staged tutorial runs start to finish in the live window; the block readout at
      each stop shows only the blocks that exist in that run
- [ ] A correction — scrub, take over, promote, re-induce — completes in under sixty seconds
      of wall clock, timed

## Gate — human playtest, not automated

From `ROADMAP.md`:

- 3 demonstrations → ≥70% success on unseen seeds
- Player reads the inferred rule and correctly predicts the next junction choice
- On failure, player names the wrong rule **unprompted** from the replay
- A correction takes under 60 seconds end to end

Criterion 3 is the real one. If players cannot self-diagnose, the forensics layer does not
work. Report the build as ready for the gate; the designer calls it.
