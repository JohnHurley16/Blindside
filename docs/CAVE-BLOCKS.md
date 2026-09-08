# The cave's blocks and decision points

**This is the designer's to change.** It is the day-one item set for the real game, written
down before any code so that it can be argued with as a list rather than dug out of a build.
Every id, label, threshold and rule below is a proposal; the ones that are guesses rather
than readings of the existing code are marked **[guess]** where they occur and collected in
§7. Change a block here and in `phase1/blocks.json`; nothing else in the build names one.

What it is for, in the designer's words: *"The whole point is that the player teaches the
agent. We have done none of that."* Phase 2 proved the teaching loop on a toy corridor — the
bot stops where it believes a junction is, shows what it believes, waits, and three runs
later the induction hands back the rule as a tree and a sentence. This document is the same
loop reaching the cave. Phase 1's hand-written policy becomes a decision tree over the
cave's own blocks, evaluated at decision points; between decision points the motor layer
drives, unchanged. The engine is the game's; the tree is the player's.

Files: `phase1/blocks.json` (the list, in `crates/blindside-induct/FORMAT.md`'s shape),
`phase1/reference/cautious.json` and `phase1/reference/aggressive.json` (the two
temperaments as trees). All three have been run through the `induct` binary.

---

## 1. What the hand-written policy decides today

Read from `phase1/policy/policy.py`. Everything it reads is on `Belief`; it never imports
truth, and `python -m phase1 --invariant` proves it. The table separates the *decisions*
— places where two different answers were possible and the temperament or a number picked
one — from the *motor* behaviour that carries a decision out, because that is the line the
rest of this document is drawn along.

### 1.1 The decisions

| # | Decision (the report's words where it has them) | Where | Belief fields read | Motor behaviour selected | Cautious | Aggressive |
|---|---|---|---|---|---|---|
| D1 | *Where next?* — first leg of the survey | `_plan`, stage 1 | nothing: a route list | `set_route` → DRIVE TO each waypoint | `out_A`: C1, DA | `out`: C4 C3 C2 C3 ANC DB ANC C3 C2 C1 DA |
| D2 | *Push on or go home?* after the first deposit | `_plan`, stage 2 | `sigma_pos()`, `cargo` | DRIVE TO (route `A_to_B`) or DRIVE TO (route `home_from_A`) | push on if σ < 16 and cargo < capacity, else home | never asked: the route already goes everywhere |
| D3 | *Am I getting lost?* | `step`, every tick while travelling | `sigma_pos()` against `CAUTIOUS_RETURN_SIGMA` | TURNING BACK: retrace the believed beacon chain, then the shaft | yes, at σ > 16 | never |
| D4 | *Can I hear machinery?* → what to do about it | `step`, every tick | `signature` (character, quality, age) | FREEZE UNTIL IT PASSES (speed 0, no ping) | quality ≥ 0.45, heard within 1 s | — |
| D5 | same question, other temperament | `step`, every tick | `signature.bearing`, `.quality` | investigate: steer at the bearing for 14 s after the last hearing; at quality ≥ 0.60, interface: creep at 0.4 cells/s and dwell 80 s | — | quality ≥ 0.30 |
| D6 | *Have I got there yet?* → at a deposit | `_arrived`, waypoint label DA/DB | believed distance to the waypoint | LOAD CARGO for 30 s | both | both |
| D7 | *Have I got there yet?* → at the machinery | `_arrived`, waypoint label ANC | as above | interface: dwell 80 s | never routed there | dwells |
| D8 | *Did the load happen?* | `_after_load` | `cargo` against `cargo_at_load` | resume; or nudge 9 cells and retry, twice; then give up | both | both |
| D9 | *Have I got there yet?* → at the shaft | `_arrived`, label HOME/S | `fixes[-4:]` for the shaft's id | WAIT TO BE COLLECTED if it answered, else SEARCH FOR THE SHAFT | both | both |
| D10 | *Where next?* when the route runs out | `_plan`, stage ≥ 2 / `_advance` | stage counter | cautious: `home_from_B`; aggressive: the beacon chain home; recalled: search | | |
| D11 | Recall — the one live command | `recall` | — | make straight for the believed shaft; search if it is not there | player | — |

D1, D2 and D10 are the survey routes. They are prior intel — the previous industry's own
maps, handed to belief as `known_places` — and the two temperaments differ mostly in
*which list they were given*. That is the hand-written policy leaking into what should be
the engine: a player cannot teach "go to B after A" if B-after-A is a constant. §2 turns
the routes into a consequence of decisions over one intel map.

D3, D4 and D5 are the temperaments proper, and each is a threshold on one belief number
(σ, signature quality). D6–D9 are arrivals: the policy always loads at a deposit, always
waits at an answering shaft, always searches at a silent one. Nobody has ever chosen
otherwise, so those are not decisions, they are what the actions *do* — with one exception
kept in §2.4.

### 1.2 The motor behaviour it runs between decisions

| Behaviour | Where | Reads |
|---|---|---|
| Steering: a heading from the near-field feeler and the map's clearance, with hysteresis | `_steer`, `_clearance`, `_near_hits` | `recent_near`, `cloud.clearance` |
| Wall escape: the longest open line on the map when no progress for 5 s; remembered failed headings; skip the waypoint after four | `_track_progress`, `_escape_heading`, `_blame_escape` | distance to waypoint, `cloud`, `dist_total` |
| Jam: not moving is a different failure from not arriving; re-pick the heading after 2.5 s of zero odometry | `_note_motion`, `_jammed`, `_break_jam` | `dist_total` |
| Beacon drop cadence: every 45 cells, only while running the survey | `step` | `dist_since_drop` |
| Ping cadence: 24 s cautious / 8 s aggressive, only into unmapped ground for the cautious one, never while frozen; lidar sweeps every 1.5 s regardless | `_wants_ping` | `ticks_since_ping`, `points_ahead()`, `sensor` |
| Arrival radii: 5 cells for a waypoint, 3 for a chain beacon, 6 for the shaft (2 once it has answered) | `_reach_radius` | |
| The search spiral: an Archimedean spiral around the *believed* shaft, advancing with ground covered, until the survey transponder answers | `_search`, `_begin_search` | `fixes`, `dist_total`, `known_places["HOME"]` |
| The load dwell and the retry nudge | `_after_load` | `cargo`, `rng` |
| The interface creep and dwell | `step` | `signature` |

---

## 2. The block list

Predicates are boolean tests over `Belief` and nothing else. Actions hand off to a motor
program and run until the next decision point. Ids are the contract with the induction;
labels are content and the designer may reword any of them without telling anyone.

The rules, carried over from the corridor: blocks are a list. Nothing downstream —
registry aside — names one by id; the tree interpreter, the demonstration, the trace writer,
the block panel and the induction are written over the list. Adding a block is one line in
`blocks.json` and one evaluator or motor file. The induction refuses more than eight
predicates (`tuning.rs`); the design's vocabulary is three growing to about six. This list
is six and four.

### 2.1 Predicates

| id | label (what the player reads) | parametric? | raw value the induction fits against | Belief fields | stage |
|---|---|---|---|---|---|
| `deposit_remaining` | *a deposit left to try* | no | — | the survey map's deposits, minus those the load program has marked *tried* (loaded from, given up on after the retries, or unreachable) | 1 |
| `carrying_cargo` | *carrying* | no | — | `cargo > 0` — the corridor's block, same id, same meaning | 1 |
| `time_elapsed_exceeds` | *late* | `seconds` | match seconds elapsed, from the agent's own clock **[guess: the clock goes on Belief]** | a new `Belief.t` | 1 |
| `uncertainty_exceeds` | *lost* | `theta` | `sigma_pos()`, in cells — the corridor's block, same id, same estimator | `sigma_pos()` | 2 |
| `fix_jump_exceeds` | *the last fix was a jump* | `cells` | the largest fix jump in the last `FIX_JUMP_MEMORY_S` seconds, 0 when none **[guess: 45 s, one beacon interval of walking]** | `fixes[*].jump` | 2 |
| `machinery_audible` | *the machinery is loud* | `level` | the signature's quality if heard within `SIGNATURE_STALE_S` (the policy's 1.5 s), else 0 | `signature` | 3 |

Why each one is here, and what it costs:

- **`deposit_remaining`** is the cave's *somewhere worth going*. The corridor's version is
  `unexplored_branch_exists`; the cave has no junction graph in belief but it does have the
  survey's deposits, so the same question is asked of intel rather than of exploration. It
  is what lets the cautious temperament say *push on to B* and both say *go home when there
  is nothing left*. Capacity is two and there are two deposits, so *hold full* and *no
  deposit remaining* coincide in this cave; a separate `hold_full` block is deferred until
  they do not (§6). **Phase 3 note:** a generated cave with no survey intel makes this
  block the corridor's again — exploration, not a list. The id says *deposit* on purpose so
  that the change is visible when it comes.
- **`carrying_cargo`** is used by neither reference tree. It is here because the designer
  said it is the game: *I have something, I am getting lost, do I go one junction further?*
  (`DESIGN-PRINCIPLES.md` §2). A player who teaches *carrying and lost → go back; not
  carrying and lost → push on anyway* needs it, and a Phase 3 that inherits one list should
  inherit this id from both worlds.
- **`time_elapsed_exceeds`** is used by neither hand-written policy, and it is the first
  thing a player will want to teach after watching a machine stay out past the window. The
  raid has a deadline (`EXTRACT_WINDOW_OPENS` 6:30, match end 8:00) and a stateless tree has
  no other way to know it. Raw is elapsed rather than remaining because the induction tests
  `raw > value`; the label reads *late (seconds = 330)?*.
- **`uncertainty_exceeds`** is the cautious temperament's defining rule and the corridor's
  θ block unchanged.
- **`fix_jump_exceeds`** is the spoof, made visible to the tree. Phase 1's whole test was
  built around the beacon lie, and a set that cannot react to it would leave the game's
  centrepiece unteachable. It is legal: `FixRecord.jump` is belief-derived and the rail
  already prints it as the tell. It is honest that it is weak: on seed 7 the lie jumped
  33.8 cells and the honest chain fixes 0.5–8.8, but `tuning.py` records honest fixes of
  8–69 cells for beacons over three minutes old, so no threshold separates them everywhere.
  A wrong θ here fires on an honest fix — which is *sensor noise that feels fair*, one of
  the areas `CLAUDE.md` names as known-weak, and R5 evidence either way. Memory rather than
  *the most recent fix* because the spoof reasserts every 8 s and a small honest fix would
  otherwise erase the big one before the next stop.
- **`machinery_audible`** is both temperaments' other rule, with different thresholds
  (0.45 to freeze, 0.30 to investigate). One parametric block, θ fitted, and the induced
  tree says which the player meant. Quality already carries the aim (THE-MACHINERY §9: the
  agent about to be hit hears it loudest), so no second block is needed for direction.

### 2.2 Actions

| id | label | motor program it hands to | ends when |
|---|---|---|---|
| `go_to_deposit` | *fetch from a deposit* | route over the survey map to the nearest deposit not yet tried (path length from the believed position); drive it with steering, escape and jam handling; drop beacons on the way; on arrival LOAD for 30 s; nudge and retry twice on a failed load; mark the deposit tried | the load ended: cargo arrived, or the deposit was given up on, or it was unreachable (four escapes at the deposit's own waypoint) |
| `return_to_beacon` | *go back* | retrace the believed beacon chain in reverse, then the believed shaft; at the believed shaft with nothing answering, the search spiral; when the shaft answers, go to it and WAIT TO BE COLLECTED | arrival at the shaft with the shaft answering (fires once; the wait that follows runs to the end of the match unless a rising edge interrupts it) |
| `hold` | *freeze until it passes* | stop, silent (no ping), until the signature has not been heard for `HOLD_RELEASE_S` **[guess: 1.5 s, the policy's staleness window]** | silence |
| `interface_machinery` | *go to the machinery and download* | head for the machinery by the survey map's position for it; while the signature is heard, steer along its bearing instead (the policy's *investigate*); at `INTERFACE_QUALITY` (0.60) stop walking, creep at `INTERFACE_SPEED`, dwell `INTERFACE_S` (80 s) | the dwell ended, or the machinery was unreachable |

Two of the four keep the corridor's ids. `return_to_beacon` means what it meant there —
walk the believed route back to the shaft — with the cave's route being the beacon chain
and the cave's ending being the search. `go_to_deposit` is the corridor's `take_branch`
with a destination instead of a mouth: it does not share the id because it does not do the
same thing.

**What is folded into the actions and is not a block.** The load itself (D6, D8): nobody
has ever arrived at a deposit and chosen not to load, so *fetch* includes it and the load
program's retry is the motor's. The search (D9): at a believed shaft that does not answer
there is nothing else sane to do, so *go back* includes it; see §4 for what that costs.
The investigate/interface split (D5): one action, and the motor decides when the sound is
loud enough to stop walking and start downloading; a player who wants *go and look but do
not download* has no way to say it, and that is deliberate for day one (§6 has the
alternative).

**Three rules the interpreter obeys.**

1. *The same action continues.* If the tree picks the action already running, the motor
   carries on where it was; nothing restarts. So *fetch* interrupted by a machinery stop and
   told *fetch* again keeps its route and its retry count.
2. *A no-op is not a demonstration.* `go_to_deposit` with nothing left to try, `hold` with
   nothing audible: the corridor's rule applies — the stop is not recorded, because a stop
   where nothing happened teaches the induction a rule nobody meant. In a demonstration the
   block panel greys those choices out. In a run, a tree that picks one waits
   `NOOP_WAIT_S` **[guess: 10 s]** and decides again, so a wrong tree stalls visibly rather
   than silently doing something else.
3. *Recall survives, and it is still not the tree's.* The one live command stays as Phase 1
   built it: it takes the tree out of the loop for the rest of the match and makes straight
   for the believed shaft. **[guess]** It is orthogonal to teaching; it is kept because the
   Phase 1 gate is still owed a Recall decision.

### 2.3 The two temperaments as trees

Both were written by hand under `phase1/reference/` and rendered by `induct render`. The
thresholds are the policy's own constants.

**Cautious** (`phase1/reference/cautious.json`; `CAUTIOUS_RETURN_SIGMA` 16, `ANCIENT_HOLD_QUALITY` 0.45):

```
the machinery is loud (level = 0.45)?
  yes: freeze until it passes
  no: lost (theta = 16)?
    yes: go back
    no: a deposit left to try?
      yes: fetch from a deposit
      no: go back
```

> If the machinery is loud, freeze until it passes. Otherwise if lost, go back. Otherwise
> if a deposit left to try, fetch from a deposit. Otherwise go back.

That is the corridor's `theta_aware` tree with the freeze on top. D3, D4, D2 and D10 are
all in it; the survey order (A then B) falls out of *nearest untried deposit* from the
player's shaft.

**Aggressive** (`phase1/reference/aggressive.json`; `INVESTIGATE_QUALITY` 0.30):

```
the machinery is loud (level = 0.3)?
  yes: go to the machinery and download
  no: a deposit left to try?
    yes: fetch from a deposit
    no: go back
```

> If the machinery is loud, go to the machinery and download. Otherwise if a deposit left
> to try, fetch from a deposit. Otherwise go back.

That is the corridor's `dfs_ignores_theta` with the interface on top. From the rival's
shaft the nearest deposit is B, then A across the whole cave through C3, where the
signature is loud enough at full strength (quality ≈ 0.40 at 48 path-cells) to pull it
into the machinery's chamber — which is the story the Phase 1 route was written to tell.

The two are distinguishable by the induction on any stop where the machinery is audible
(different actions) and on any stop where σ passed 16 (a test one tree has and the other
does not). Fed one synthetic cautious demonstration with a stop of each kind, `induct`
returns the cautious shape and fits θ between the recorded sigmas (checked; the
`deposit_remaining` test is dropped as unneeded when no stop ever showed it false, which
is the minimality guarantee working).

### 2.4 What the set cannot say, and why that is accepted

- **Home for good.** Phase 1's cautious policy, once it has turned for home, stays turned:
  `PolicyMode.HOME` is sticky. A stateless tree over Belief has no mode. Under this set an
  agent that goes back because it is lost gets a fix at the shaft, is no longer lost, and —
  if a deposit remains and it is not late — goes out again. That is exactly the corridor's
  θ-aware explorer, and it is the behaviour the corridor's gate is built on. The sticky
  version was a spectator device so that Recall had something to buy, not a temperament,
  and *late* gives a player the way to say *and then stay*.
- **The exact routes.** The rival's `C4 C3 C2 C3 ANC DB ANC C3 C2 C1 DA` was authored for
  beats (it doubles back through C3 to be heard). Trees reproduce the decisions, not the
  path, so the measured beats — the 5:41 near miss, the 6:56 kill — are not preserved and
  must be re-found on the new paths. This is the cost of the build and it is stated here
  rather than discovered.
- **Do I ping?** The glossary calls it the central decision of a match; in Phase 1 it is a
  cooldown, and the design panel already found that no policy reads contacts. It stays a
  loadout number (§4) and the day-one set cannot teach it. §6 says what would.
- **Investigate without downloading**, and **go straight for the shaft** (Recall's blunt
  line, as opposed to the chain) — both are one more action each and are deferred (§6).

---

## 3. Decision points

The corridor stops at junction arrival because that is where its belief changes. The cave's
belief changes continuously, so the stops have to be chosen, and the choice is a trade:
too many and a demonstration is a click every twenty seconds; too few and the tree cannot
express a *reaction* — and both temperaments are reactions (to σ, to a sound).

**A decision point is when the action ended, or when something the tree can see became
true.** Precisely:

| | Fires when | Why it is in | Why it is enough |
|---|---|---|---|
| **DP0** start | the match begins, at the shaft | the corridor's first stop; the first choice is a real one (fetch, or download first) | — |
| **DP1** the action ended | as defined per action in §2.2: the load ended, the shaft answered and was reached, the silence fell, the dwell ended; or the action failed (unreachable, given up) | an action that has finished needs a new one; this is the only stop the corridor has | every *what now?* in §1.1 (D2, D6–D10) is one of these |
| **DP2** a predicate became true | any enabled predicate goes false → true, re-armed `PREDICATE_REARM_S` **[guess: 5 s]** after its last rising edge, so a flicker across θ is one event | D3, D4 and D5 all fire *mid-passage*, on a number crossing a threshold; without this stop the tree can hold a rule about σ or the machinery and never get to apply it | a rising edge is news. A falling edge is the absence of news: *no longer loud* is `hold` ending (DP1), *no longer a deposit left* is a load ending (DP1), *no longer lost* is a fix — and the fix reaches the tree as `fix_jump_exceeds` rising, if it was big enough to matter |

Three candidates were considered and are **not** decision points:

- **Every waypoint arrival.** C1, C2, C3, C4 are the route planner's business now. Stopping
  at each would make the corridor's mistake in reverse — the route as a sequence of choices
  nobody is choosing — and would triple the count for stops that always say *carry on*.
- **Every fix.** Considered as its own event (*the map snapped; everything the tree reads
  changed*). Measured on seed 7 it is 38 fixes, most of them under two cells, because a
  spoofed agent loitering between anchors gets a fix every eight seconds; at a 20 s re-arm
  that is still eleven stops at which the block readout shows nothing and the player says
  *carry on*. A fix only matters to the tree if a predicate can see it, so it is a
  predicate (`fix_jump_exceeds`) and DP2 covers it.
- **The extraction window opening, the machinery becoming audible.** Both are DP2 already —
  `time_elapsed_exceeds` and `machinery_audible` rising — and neither needs a second name.

**A consequence to know about.** DP2 fires on the *provisional* threshold a demonstration
runs with (Phase 2's `DEMONSTRATION_THETA` arrangement), so a player cannot teach a threshold
lower than the provisional one: the bot never stops there to ask. The provisional values
should therefore sit low — the bot asks early, the player says *carry on* until they mean
it, and the induction fits the boundary between the carry-ons and the reactions. Proposed
provisional values **[guess]**: `level` 0.25, `theta` 10, `seconds` 270, `cells` 8. Lower
still buys more stops per match; the machinery at 0.15 is audible from most of the middle
cave and would ask every cycle.

### 3.1 How many stops an eight-minute match has

Measured rather than estimated, on the existing policy's own path (seeds 1, 3, 5, 7,
`python -m phase1 --headless`, a scratchpad script reading Belief and applying the rules
above; the new trees will walk different paths, so this is the shape of the number, not the
number). Several triggers on one tick are one stop — the load ending and *carrying* rising
land together.

| seed | start | action ended (the deposit given up) | *carrying* rose | *the machinery is loud* rose, at level 0.30 / 0.45 | *late* rose | *the last fix was a jump* rose, at cells = 8 | *lost* rose | **stops** |
|---|---|---|---|---|---|---|---|---|
| 7 | 1 | 1 | (with the load) | 4 / 2 | 1 | 2 | 0 | **9–10** |
| 1 | 1 | 1 | — | 4 / 2 | 1 | 1 | 0 | **8–9** |
| 3 | 1 | 1 | — | 4 / 2 | 1 | ≥ 1 (the spoof; the rest not counted) | 0 | **8–9** |
| 5 | 1 | 1 | — | 4 / 2 | 1 | ≥ 1 (the spoof; the rest not counted) | 0 | **8–9** |

**About ten stops in eight minutes, one every forty-five to fifty seconds.** The corridor's
runs record eight to twenty junction stops, so a cave demonstration is the same size as
one the corridor's gate was written for. An unspoofed run that reaches both deposits and
gets home would be much the same: start, two loads, three or four machinery cycles in
earshot, the clock, arrival — nine.

Two readings from the same measurement worth more than the count:

- **What was rejected would have doubled it.** Counting every fix as a stop adds 9–13 per
  seed even at a 20 s re-arm (40 raw fixes on seed 7), and every one of them shows a block
  readout that says nothing. Counting the route's waypoint skips adds four more.
- **`lost` never rose on any of the four seeds, at θ = 16 or at the provisional 10.** The
  spoof lands at 2:23 and collapses σ, and a jammed agent stops accumulating distance, so
  as Phase 1 is tuned the cautious temperament's defining rule cannot be met in play before
  the lie. `tuning.py` says this is the design (*the spoof silently disarms the agent's own
  self-preservation*). It means the tutorial's drift run has to run with the spoof off, as
  the corridor stages drift in before the full problem, or the block a player is meant to
  meet before composing it never fires.

---

## 4. What stays in the motor layer, and is not the player's to teach

Everything in §1.2, unchanged, plus what the new actions need:

| Motor | Why it is not a block |
|---|---|
| Steering, the near-field feeler, the map's clearance, hysteresis | Runs at 20 Hz on continuous belief. A tree evaluated at decision points cannot steer, and a player asked to would be teaching robotics, not behaviour. |
| Wall escape, the escape memory, jam breaking, skip-after-four | The same, and it is measured to the second (`tuning.py` 442–474): the difference between a lost agent and a looping one is how fast it gives up on a wall, which is a number nobody should have to demonstrate. |
| The search spiral | The only behaviour that can undo a lie, and there is no alternative to it worth choosing at a silent shaft. It is the tail of `return_to_beacon`. What is lost: the player cannot teach *search from here* versus *search from where home should be*; `_begin_search` already decided that from measurement (centre on believed home, always). |
| Beacon drop cadence, 45 cells, outbound only | The chain is what `return_to_beacon` walks; a player who thinned it would be sabotaging their own action. It moves to a loadout number (beacon rack size, later). |
| Ping cadence | A loadout number **[guess]**: `ping_cooldown` and `speed` go on the chassis with `sensor`, since `RIVAL_SPEED` is already justified as *a lighter chassis*. The design calls *do I ping?* the central decision; this build cannot teach it and says so (§2.4, §6). |
| Route planning over the survey map | New. Shortest path over the survey's chambers and dry passages from the believed nearest chamber. **[guess]** The survey marks the machinery's chamber as dangerous ground and the planner avoids it except as a destination — without that rule the shortest intel path from C3 to deposit B runs *through* the Assayer's chamber (88 cells via ANC against 108 via C4), and the cautious tree would walk the player into the machine on day one. |
| Arrival radii, the load dwell, the retry nudge, the interface creep speed and dwell length, the hold release | Numbers that describe the body and the world, all already in `tuning.py`. |

The line, stated once: **the tree answers *what am I trying to do*; the motor answers *how
do I do it from here*.** A block is something two players would defensibly choose
differently; a motor constant is something one of them would be wrong about.

Two things sit *on* the line and are flagged rather than settled. The ping cadence is the
first; the second is that `interface_machinery` decides for itself when it is close enough
to stop walking (`INTERFACE_QUALITY` 0.60) — THE-MACHINERY §6 makes *how close to stand*
the download's whole decision (closer is faster and costs hull), and on day one the motor
makes it.

---

## 5. The trace, in FORMAT.md's shape

`blocks.json` is FORMAT's shape exactly (ids, labels, `param`, `stage`). The trace is
FORMAT's shape with one optional field, added as the contract allows and recorded here:

- `junction` (required, integer): the cave has none. It carries **the index of the believed
  nearest known place** on the survey map's list (S = 0, C1 = 1, … in the survey's order)
  **[guess]** — a *where*, which is what the corridor's junction id was, and what the
  induction's query prints: *stop 4 of trace-1 (junction 5, tick 2400)*.
- `reason` (**optional**, string): why the bot stopped — `start`, `ended:<action id>`,
  `rose:<predicate id>`. The induction ignores it (serde accepts unknown fields; checked
  with a trace carrying it). The window uses it to say *it stopped because…* at a scrub
  point, and the Phase 3 trace format should keep it.
- `outcome`: `success` = extracted with cargo ≥ 1; `lost` = alive and in the cave at the
  end; destroyed is neither **[guess]**.

A stop is recorded when the chosen action ran — started, or continued as the same action —
and not when it was a no-op (§2.2, rule 2). The validator is the corridor's with the
optional field admitted.

---

## 6. Not day one — the next blocks, by depth

Listed so that the day-one line is visibly a line and not an omission. Each would arrive
the way the design says blocks arrive: met in play, then composable.

| block | what it is | why not yet |
|---|---|---|
| `hold_full` | *the hold is full* | coincides with *no deposit remaining* in this cave |
| `downloaded` | *already downloaded from the machinery* | needs `yields()`; without it the aggressive tree re-interfaces every cycle it hears the machine, which is what the Phase 1 rival does too |
| `contact_heard` (`level`) | *something on a bearing* — a rival's ping or motion | no policy reads contacts today; it is the whole passive/active game and deserves its own tutorial run |
| `hurt` (`theta`) | *damaged* — over the self-report | THE-MACHINERY §4.8's two-block tree; needs `SelfReport`, a Phase 3 sensor |
| `slew_heard` | *the array just swung* — the counter | the slew is view-side only in Phase 1 (THE-MACHINERY §10.2) |
| `run_for_shaft` (action) | Recall's blunt line as a teachable choice against the chain | day one has one way home; this is the second, and it is the one that recovers from a lie |
| `investigate` (action) | go and look without downloading | folded into `interface_machinery` |
| ping as an action parameter | *do I ping?* | needs `Act { params }` (ARCHITECTURE), which the induction contract does not carry yet |

---

## 7. Every guess, in one place

1. The clock is on Belief (`time_elapsed_exceeds` reads the agent's own clock).
2. `fix_jump_exceeds` remembers the largest jump for 45 s; raw is the jump in cells, not
   the sigma-relative surprise, because the surprise does not separate the lie from an
   honest fix on seed 7 (11.4× against 0.2–10.9×) while the jump nearly does.
3. `hold` releases after 1.5 s of silence; no-op waits 10 s; predicates re-arm after 5 s.
4. Provisional demonstration thresholds: `level` 0.25, `theta` 10, `seconds` 270, `cells` 8.
5. Recall survives unchanged and overrides the tree.
6. Ping cooldown and speed move to the loadout with the sensor; both trees run with their
   temperament's Phase 1 numbers there.
7. The survey map is complete and honest (all chambers, dry passages, both deposits, the
   machinery's position), and marks the machinery's chamber as ground the planner avoids.
8. `junction` in the trace is the believed nearest known place's index; `reason` is added
   as an optional field; `outcome.success` is extracted-with-cargo.
9. Stages: 1 = deposits, carrying, the clock, fetch, go back; 2 = lost and the fix jump;
   3 = the machinery, freeze, download. The tutorial's shape is the corridor's (no drift,
   then drift and the spoof, then the full problem).
10. The two reference trees reproduce the temperaments' *decisions*; the hand-authored
    routes and the beats measured on them are not preserved.
11. `deposit_remaining` is intel-based and becomes the corridor's exploration block when
    the survey goes away in Phase 3.

---

## 8. As built — 2026-09-08

The tree policy is in `phase1/policy/` (registry, tree interpreter, one evaluator per
file under `predicates/`, one program per action under `motor/`); the sim loads
`reference/cautious.json` for the player and `reference/aggressive.json` for the rival,
and `--tree PATH` drives the player with any tree. Where the build settled a guess above
differently, or found something, it is here.

- **Guess 3, one number instead of two.** `SIGNATURE_STALE_S` = 1.0 s is both the block's
  staleness and the hold's release. With the block at 1.5 s and the hold at 1.0 s the block
  stayed true for half a second after the hold let go, the tree froze the machine again on
  nothing, and every freeze ended in a ten-second no-op stall (measured, all seeds). 1.0 is
  the old hold's window, so the freeze starts and ends on the ticks it always did. No-op
  wait 10 s and re-arm 5 s as guessed.
- **Guess 1, the clock.** `Belief.t` is advanced at the top of every tick, before the
  policy runs, so a predicate reading it and a program reading the tick's `t` agree on how
  old a sound is.
- **Guess 7, plus one.** The planner joins the survey graph at the believed nearest chamber,
  or at a neighbour whose passage runs within `PASSAGE_JOIN_CELLS` (10) of the believed
  position when that is shorter; never at the machinery's chamber unless it is the goal or
  the agent is standing in it. Measured with every chamber allowed as a join, the first route
  after deposit A was one waypoint — deposit B, through eighty cells of rock; with every
  neighbour allowed, a route from C3 joined at the Assayer's chamber. **[guess 12]**
- **Rule 1, as built.** One program is suspended at a time — the one the tree displaced —
  and it resumes only if the tree picks it again straight after; otherwise it is dropped
  and the action starts fresh. A load interrupted by a stop starts its dwell over on resume,
  because World's loading progress resets the tick the machine stops asking to load.
- **The wait.** `return_to_beacon` chosen while standing at an answering shaft is the wait
  to be collected, runs to the end of the match unless a rising edge interrupts it, and is
  recorded as a stop that ran.
- **Guess 5.** Recall is `motor/run_for_shaft.py`, `return_to_beacon` with a one-waypoint
  route, constructed by the policy and not in the block list.
- **Which predicates exist in a match.** Only the ones the tree reads, the corridor
  evaluator's rule, so `late`, `carrying` and `the last fix was a jump` never stop either
  reference tree; a demonstration will enable by stage.
- **Two things the old policy did that the motor layer does not reproduce**, both
  per-route state it never reset at `set_route`: its stall tracker ran through a freeze, so
  a hold longer than five seconds ended in a wall escape in a direction chosen while frozen
  (seed 1, rival inert, 3:15.9); and its escape-heading cache survived across routes and was
  blamed at the next window's first escalation, so a heading tried at 0:42 on the way to A
  was ruled out at 2:48 on the way to C2 (seed 5, rival inert). With the rival held still so
  the player's sensor stream is the same in both builds, the player's true path is identical
  to the cell until the first of those two moments on every seed (3:16–5:51), and the load
  and the spoof land at the same tenth of a second on all eight.
- **Finding: the rival dies at 1:56 on eight seeds of eight.** From R the nearest deposit is
  B, 38 cells away and 37 from the machine, and it is loading there when the first cycle
  winds up at 0:32; at 0.30 it goes to look, at 0.60 it creeps, and the second firing kills
  it. §2.3's *then A across the whole cave through C3* never happens: it never leaves B's
  side of the cave. The hand-authored route went the long way round first and doubled back,
  which is why its death was 5:41 and only three seeds in eight; the 5:41 near miss and kill
  are gone with it, and the two agents never come within a hundred cells of each other. This
  is the temperament plus the survey planner, not a constant; the designer decides whether
  the aggressive tree's level, the rival's survey, or the beat is what gives.
- **Finding: the cautious tree freezes where it stands.** A spoofed player whose route
  runs into the Assayer's chamber freezes there when the machine winds up, inside the lethal
  contour: three deaths in eight (seeds 1, 4, 6) against none with the hand-written policy,
  whose spoofed wanderings crossed the same ground between firings on four seeds of eight.
  Same rule, different timing luck; a `run_for_shaft` block, or *lost → go back* meaning the
  blunt line, is the day-two answer.

## 9. As built — the teaching loop, 2026-09-08

The corridor's loop reaches the cave. `python -m phase1 --teach` is the demonstration:
the window is belief only, the bot stops at each decision point, the rail shows every
enabled predicate with its value and raw number and the actions as numbered keys, the
match clock is stopped for the whole of the asking, and the trace is written in
`FORMAT.md`'s shape. `--teach-scripted TREE` is the same with a tree choosing and no
window; `--enabled ID,ID` restricts the blocks a run has; `--induce DIR` calls the induct
binary over every trace in `DIR/traces` and prints the tree and the sentence, or the two
contradicting stops; `--tree DIR/tree.json` runs the match on the rule with the full
spectator display, the rail showing the rule and lighting the path it took at each stop;
`--ghost DIR` replays each demonstration's seed on the induced tree and names the first
stop where it chose differently; `--correct DIR --trace N --stop K --with TREE` is the
correction loop scripted -- scrub, take over, promote by replacing the suffix, re-induce.
Where the build settled something, or found something, it is here.

- **How a stop pauses the match.** The policy is asked at the top of every tick, before
  the world moves, whether a decision is due (`Policy.poll`); with a tree it answers
  itself, without one the sim does not tick until `answer` is called. So a match paused
  for a person has not moved at all, and a scripted demonstration in which the reference
  tree chooses is the same match, to the tick, as that tree running by itself (checked:
  identical decisions and final truth on seed 7; the tree-driven headless timelines are
  byte-identical to the build before this on seeds 1, 3, 7 and the aggressive tree). The
  three programs that could end *before acting* (`hold`, `go_to_deposit`,
  `interface_machinery`) say so through `Program.ending(t)`, so that stop is found before
  the tick too rather than after an idle one.
- **Guess 4, moved.** The provisional thresholds are `tuning.DEMONSTRATION_PARAMS`, keyed
  by *parameter name* (level, theta, seconds, cells), not on `blocks.json`: the induct
  crate refuses a block list with a field it does not know. Two predicates sharing a
  parameter name would share a value.
- **Guess 8, the `reason` field, and a crate finding.** The trace on disk carries `reason`
  per step as designed. The crate as built refuses it too (`strict.rs`: every type denies
  unknown fields; §5 above believed serde would ignore it -- it does not), so the client
  hands the binary a copy of each trace holding the contract's fields only, under the
  same file name in `seam/contract/`. The conflict query names those copies. A one-line
  change in the crate (accept `reason` as optional) would remove the copy; the crate is
  another workflow's this week and was not touched.
- **Which stops are recorded.** Only stops whose chosen action ran, as the corridor does.
  The teach window refuses the key for an action that would be a no-op here (fetch with
  nothing left, freeze in silence) rather than record nothing, because a replay answers
  the recorded choices at the recorded stops and a stop that was never written down
  cannot be replayed through.
- **The demonstration is belief only** (PHASE-2-OPEN-QUESTIONS (h)): the teach window is
  the spectator display's belief inset given the main rectangle, the truth channel never
  switched on. The spectator display, truth beside belief, is for watching the taught
  machine run. **[guess]**
- **Finding: the fitted threshold lands near the provisional one, not the temperament's.**
  Three scripted cautious demonstrations with every block enabled induce *if loud freeze;
  otherwise if lost go back; otherwise fetch* with level 0.3 and theta 12 against the
  reference's 0.45 and 16, and decide identically to the reference at all 29 recorded
  stops. In play they do not run the same match: the load and the spoof land at the same
  tenth of a second on seeds 1, 3 and 7, but the freeze fires at 0.3 -- earlier, and on
  cycles the reference never heard as loud -- so the paths part around 3:05 and the
  outcomes differ on seeds 1 (reference destroyed 6:30, induced lost) and 7 (the
  reverse). The evidence a demonstration can give brackets `level` as (0.3, 0.45): the
  bot stops at the provisional 0.25 and the player says *carry on*, it stops again where
  the reference reacts, and nothing is recorded between, so the crate's roundest number
  in the band is 0.3. A threshold cannot be taught more precisely than the bot stops to
  ask about it, which §3's consequence predicted; the lever is the provisional value.
- **Finding: three runs never showed a deposit exhausted**, so the induced rule has no
  *a deposit left to try* test -- minimality dropping an unneeded predicate -- and on a
  seed where the fetch runs out (seed 3, 6:08) the taught machine stalls in ten-second
  no-op waits to the end, visibly. That is the rule working: the player never taught it
  what to do then.
- **The correction, scripted.** Scrubbing seed 7's demonstration to stop 4 reproduces
  the recorded stop exactly (tick 5216, place 5); the aggressive tree taking over replaces
  nine steps with three; re-induction is consistent and takes 4.1 s of wall clock end to
  end. The re-induced rule separates the old freezes from the new downloads by *late*,
  because that is what the evidence says. The window's form of the loop -- scrub with the
  arrow keys, take over, promote -- is not built; the pieces (`replay/`) are the
  corridor's and port cleanly, and the session state machine that binds them to keys is
  the remaining work.
