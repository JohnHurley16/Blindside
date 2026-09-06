# Phase 2 — open questions before code

`ROADMAP.md` names the pieces of the Junction Test and is silent on the things that
change every later decision. Phase 1's questions were never answered inline and the code
chose instead; this time each one is answered here first. Each carries the recommendation
and the reason, so the answer can be a yes or a no.

Phase 2 exists to answer three risks: R2 (demonstration cannot produce a legible policy),
R3 (players cannot diagnose their own failures) and R5 (the predicate vocabulary is the
wrong size). Every recommendation below is chosen to keep the test pointed at those three
and nothing else.

---

## (a) What is a demonstration made of?

**Options.** Junction-level: the agent travels the corridor by itself, stops at each
junction it believes it has reached, and waits for the player to say `take_branch` or
`return_to_beacon`. Continuous: the player steers the agent the whole way, as DESIGN's
"drive it in its body" reads.

**Recommendation: junction-level.** The trace becomes a list of (belief at this junction,
choice made) pairs, which is exactly what the induction consumes. Continuous steering turns
changepoint segmentation into the hard problem, and segmentation is not one of the three
risks — it becomes real in Phase 4 when there is a VM to segment for. The feel DESIGN
describes survives: the player sees only belief, waits, and decides. The correction loop's
"enter the body and drive" becomes "scrub to a junction and choose differently", which is
also the thing criterion 4 (a correction in under sixty seconds) is measured on.

**Consequence.** The demonstration and correction stories get simpler; the segmentation
story goes away; the ghost replay is a diff of choices at junctions rather than of paths.

**Decision (designer, 2026-09-06): junction-level, and the blocks are discovered
progressively.** The designer's framing, recorded because it is a principle for the whole
game and not only for this phase:

> Think of the base blocks the same as Minecraft items. As the game grows, devs add more,
> so building behaviours can get more complex. But the equivalent of the wooden sword,
> shovel, pickaxe and crafting table are built on day one.

The three predicates and two actions are the day-one items. The tutorial introduces them
the way a first night introduces a pickaxe: run one has no drift and only *unexplored
branch* and *take branch* exist; run two brings drift, and *lost* and *go back* appear
because now they can matter; run three is the full problem. Every later block — from a
later phase, from a season, or downloaded from the machinery — arrives the same way.

What this binds in Phase 2, throwaway or not: the induction, the tree render and the
sentence render are written over a *list* of predicates and actions, never over the three
by name, so that adding a fourth is a data change. That is the shape Phase 2 is testing.
The gate's "three demonstrations" are three full runs after the two tutorial runs; the
tutorial runs still count as induction evidence (a run in which *lost* is always false is
evidence), but the success rate is measured only from the three full ones. No editing the
tree by hand in this phase: R2 asks whether demonstration alone produces a legible tree,
and a node editor would hide the answer.

## (b) Where does uncertainty come from?

**Options.** Reuse Phase 1's odometry: heading-bias drift, position sigma growing with
distance, the shaft beacon as the only fix. Or a scalar that grows per cell travelled.

**Recommendation: reuse Phase 1's, cut down to position sigma only.** `uncertainty > θ` has
to mean the thing it says. A per-cell counter makes θ a step budget in disguise, and the
player learns "turn back after four junctions" rather than "turn back when lost" — which
is a different rule and not the one the game is about. Phase 1's drift is built and
measured. Belief in Phase 2 is a pose with a sigma and a believed junction graph, nothing
more.

## (c) How far does `unexplored_branch_exists` see, and what does `take_branch` take?

**Recommendation: the current junction only; `take_branch` takes the left-most unexplored
branch here and has no parameter.** Three predicates is the deliberate size of the
vocabulary, and R5 is the question of whether that size is right. A predicate that
searches the whole believed graph is doing the policy's job inside the predicate, which
hides the answer. A fixed, legible branch order keeps the induced rule sayable in one
sentence: *"if there is an unexplored branch here and I am not too lost, take it."*

## (d) What counts as success, and how long does a run get?

**Recommendation, as one sentence the evaluator implements verbatim:** *a run succeeds when
the agent is within the shaft beacon's range carrying cargo before the tick budget ends;
the budget is twice the ticks a full depth-first walk of that seed's corridor needs.* A
correct depth-first policy always fits; a policy that loops or dithers does not. Seeds
for the ≥70% criterion are ones the player never demonstrated on.

## (e) Can the agent see branches before it is standing at them?

**Recommendation: only at the junction it occupies**, from the near-field sense — no sonar
or lidar choice in Phase 2. If branches further along were in belief, "unexplored branch
exists" would be ambiguous about *where*, and (c) would have to grow a parameter to fix it.

## (f) What does promotion do to the demonstration set?

**Options.** Append the corrected run as a fourth demonstration, or replace the corrected
run's suffix from the scrub point.

**Recommendation: replace.** The correction means "the rule I taught was wrong from here."
Appending leaves the wrong choice in the evidence, and with three demonstrations a single
contradiction is enough to make no consistent separator exist — which fires the
active-learning query on the player's own mistake. The promoted demonstration is the
original trace up to the scrub point plus the player's choices after it.

## (g) Does drift need teeth?

**Recommendation: yes, deliberately.** If `return_to_beacon` cannot fail, `uncertainty > θ`
never matters, the induced rule is always "explore", and criterion 3 — the player names
the wrong rule unprompted — has nothing to name. Tune so that a depth-first policy that
ignores uncertainty fails on roughly a third of unseen seeds and one that turns back at the
right θ succeeds on at least nine in ten. That guarantees a ≥70% policy exists and that
there are failures worth a replay.

## (h) What does the player look at during a demonstration?

**Recommendation: Phase 1's view, reduced.** The believed junction graph, the agent's
believed position with its ellipse, the shaft beacon, cargo state. No point cloud — the
corridor is the map. Belief only, as always.

## (i) Three demonstrations on what?

**Recommendation: three different seeds**, then twenty unseen ones for the success rate.
Three runs of one seed teach the induction that seed's shape, not a rule.

## (j) What does the active-learning query ask?

**Implementer's call, recorded here.** When no separator is consistent with the
demonstrations, show the two junction moments that contradict each other side by side —
same predicates true, different choice made — and ask which one the player would do
differently. That is the smallest question that resolves the conflict, and it is a
question about the player's own decisions, which is the forensics layer in miniature.

---

## What is not asked

The ROADMAP's list is taken as given: eight junctions, one deposit at a random leaf,
three predicates, two actions, a behaviour-tree render and a one-sentence render, ghost
replay, correction loop. The estimate of four to six weekends is not revisited here; the
board carries the working-day figure.
