# Phase 1 — The Spectator Test

**Language:** Python. **Deliberately throwaway.** **Estimated: 2–3 weekends.**

Answers the largest risk in the project: *is the run phase interesting when the player
has almost no control?* If the answer is no, the entire design is wrong and no later work
repairs it.

**Do not engineer this.** No abstraction layers, no config system, no plugin architecture,
no test suite beyond what you need to iterate. It will be deleted.

---

## What is being tested

Not visuals. **Information under ambiguity.** The tension is supposed to come from:

- A bearing with no range, which might be a rival, an ancient system, or an echo
- An uncertainty ellipse growing while the player decides whether to spend their one command
- Watching belief diverge from reality with no ability to intervene

Art does not make any of that clearer. Ugly is fine. **Illegible is not** — most grey-box
prototypes fail because state is unreadable, not because they are plain.

---

## Build

**World.** One hand-authored cave. Roughly 200×120 grid, passages and chambers, a
waterline. Does not need to be generated — Phase 3 does generation. Two deposits.

**Agents.** Two, one per team. Both run hand-written scripted policies — no authoring in
this phase. Policies should be simple and slightly different: one cautious (pings rarely,
returns on high uncertainty), one aggressive (pings often, pushes deeper).

**Sensors.** Three only:
- Passive acoustic — returns bearing plus a quality value, no range
- Active sonar — returns range and bearing over an arc; sets an `audible` flag for N ticks
- Dead reckoning — pose estimate with drift proportional to distance travelled

**Beacons.** The player's agent drops beacons automatically at intervals. One beacon,
partway through the match, is a **spoof placed by the rival** and returns a wrong fix.
This is scripted, not emergent. It is the moment the test is built around.

**Belief.** Maintained separately from world state, exactly as the real architecture will.
Do not shortcut this even in Python — it is the thing being tested.

**Ancient system.** One. A hazard on a fixed cycle with an acoustic signature emitted
several seconds before it becomes dangerous. Kills an agent that ignores it.

---

## Display

The **operator** view — what a player sees while playing — is belief only, and ground truth
is never rendered in it. The **spectator** view draws truth beside belief, because the gate asks
a stranger to follow a match she is not playing, and a viewer who is as lost as the machine has
no way to feel the machine being wrong. (Amended 2026-09-07 by the designer, after the first
gate failed: `docs/phase1-playtests/2026-09-06-gate.md`. `DESIGN.html` line 238 already leaned
this way — "truth for spectators, belief for players". The invariant is untouched: a policy
still never observes ground truth, and the truth channel is one-way to the screen.)

Primary view is a **sparse 3D point cloud** of accumulated sensor returns, orbitable.
Dense where the agent has pinged, sparse where it has only passed through, empty where it
has never sensed. Empty space must read as *absence*, not as fog.

Point cloud accumulates **in the agent's estimated frame**, so drift causes visible
smearing — a corridor ghosting into a doubled version of itself. A fix snaps it back into
alignment. This is the single most important visual in the test.

Overlay:
- Own ping propagating outward as a visible wavefront
- Other agents' pings arriving as wavefronts from a bearing
- Ancient system signature emissions, visually distinct
- Contact bearing lines with angular uncertainty wedges
- Pose uncertainty ellipse
- Per-point confidence — a marginal return must not look identical to a confident one

**Sound is not optional in this phase.** The game is about acoustics. A contact should be
audible, directional, and have character. Stereo pan plus a few tones is an afternoon of
work and probably carries more tension than any visual. Build it.

---

## Player input

Exactly one: **Recall**. Single use. Returns the agent toward the nearest shaft.

Nothing else. No steering, no camera-in-world, no pause.

Match length: **eight minutes**, compressed for testing. Needs at least one contact, one
ambiguous detection that turns out to be an echo, the spoofed beacon, and an extraction
deadline.

---

## Acceptance criteria

Build is ready for the gate when:

- [ ] Eight-minute match runs start to finish without intervention
- [ ] Point cloud visibly smears under drift and snaps on a fix
- [ ] The spoofed beacon fires and the agent acts on the wrong fix
- [ ] Contacts are audible and directional
- [ ] Rival pings appear as wavefronts from a bearing
- [ ] Recall works, once

## Gate — human playtest, not automated

Watch a player for eight minutes with no explanation beyond "you cannot drive it".

**Pass:** they talk to the screen, guess at contacts, form a wrong theory and correct it,
and report tension at the Recall decision.

**Fail:** they are bored. **Stop. Do not proceed to Phase 2.** Report when they
disengaged — engagement for four minutes then drift is a pacing problem; never engaging
is a design problem, and they are fixed differently.

Test it alone first. You will know within twenty minutes whether you are leaning forward.
