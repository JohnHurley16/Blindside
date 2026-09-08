# The cave induction, measured before anyone teaches it

2026-09-08. Five measurements of the cave teaching loop (`python -m phase1 --teach` /
`--induce` / `--tree`), made on the build at 53b61cf (the sim, demonstration and induct paths unchanged through 8441966) with no file under `phase1/`,
`phase2/` or `crates/` changed, so that when a person sits down to teach the cave bot
(`docs/phase2-playtests/PROTOCOL-CAVE.md`) her result can be read against numbers rather
than against hope. Two gates depend on them: ROADMAP's Phase 2 criterion, *three
demonstrations → at least 70% success on unseen seeds*, and risk R2, *demonstration
cannot produce legible policies*. Nothing here says ready or not ready. It says what the
numbers are and what a person should expect to see.

**Scope, added after verification.** The specific shapes below — which clause is missing,
how many words the rule is, how often the query fires — are seed-specific: a second run on
seeds 11/13/17 and 201–220 reproduced every gate-level number (0 of 20 either way, ten stops at
46–47 s, 72–73% *carry on*) and none of the specific sentences. Read the numbers as the shape
of what to expect, not as what she will see.

**And the finding that outranks the rest, measured on 2026-09-08 after this document was
written: the cave cannot be won by the rule being taught.** With the spoof switched off entirely
the cautious reference rule extracts 4 of 20; moving the extraction window earlier changes
nothing. So the gate's *≥70% on unseen seeds* is unreachable in the cave by any teaching, because
the cave was tuned for a spectator beat sheet in which the player is doomed, and never for a
game someone can win by teaching well — the corridor got that tuning pass (`PHASE-2-OPEN-QUESTIONS`
decision (g)) and the cave did not. The options are in `docs/CAVE-WINNABLE.md`; the choice is
the designer's.

The one-paragraph version. **Both reference trees score 0 of 20 on the gate's own
measure**, so the induced tree cannot be read against the tree it was taught from — it
has to be read against what the day-one blocks can reach at all, which is 70–80%, at
thresholds (*lost* at 6–7 cells; *late* at 3:00 or earlier) that neither reference holds
and that the bot never stops to ask about. Three clean demonstrations induce a rule of
two tests and nineteen words that reads as the temperament, but with thresholds fitted
where the stops happened to fall, not where the reference's are, and without the
*deposit left to try* clause, so the taught machine stalls in ten-second waits on a
fifth to a half of unseen seeds. The fitted number is the crate's round number nearest
the middle of the gap between the last stop that said *carry on* and the first that
reacted, so a threshold can land two minutes from where the person reacted when the
bot did not stop in between. One different choice in three runs makes the contradiction
query fire four to seven times in ten; when a rule comes out anyway it is twice as long.
With one or two runs in evidence the rule can name the wrong reason for a right action
(*late* for a turn that was made because the machine was lost). Two different choices:
the query, ten times in ten on seeds 1/3/7 — and two and four times in five on seeds 11/13/17, so often but not always. A demonstration is ten stops, forty-six seconds apart, seven of which
are *carry on* — the size the corridor's gate was written for, exactly as the protocol
says — but the bot asks about the machinery at 0.25 and about being lost at 10 cells,
and once a predicate is true it is not asked again, so a person who wants to freeze at
0.45 or turn back at 16 is only ever asked at a stop that lands there by luck.

Every script is under the session scratchpad,
`C:/Users/jackh/AppData/Local/Temp/claude/C--Users-jackh-documents-programming-Blindside/366e9734-eca3-41e8-a507-d6b36028c05e/scratchpad/cavelab/`
— `lab.py` the harness; `m1.py`, `m1b.py`, `m1c.py`, `m2.py`, `m3.py`, `m4.py`, `m5.py`
one per table below; results as `results/m*.md` and `results/m*.json` beside them; the
traces, induced trees and seam files under `work/`. They are throwaway and are not in
the repository.

---

## 0. Method

**What was run, and through what.** Every match, demonstration, induction, render,
decision and ghost goes through the build's own code, in-process, with a pool of ten
workers so that the 1,021 matches on trees, 120 demonstrations and 80 ghost runs behind
these tables take minutes rather than hours:

- *a match on a tree* is `phase1.match.headless.run_headless(seed, tree)` — what
  `--headless --tree` runs — and its `MatchResult` is the whole of what is read off it;
- *a scripted demonstration* is `Demonstration` + `TreeChooser` + `TraceWriter` over
  `RunFactory`, the classes `run_scripted_demo` in `phase1/__main__.py` uses — checked
  byte-identical to `--teach-scripted`'s own trace on seed 7 with every block enabled;
- *the induction, the render, `decide` and `diff`* are `InductClient` over the
  `induct.exe` the client already points at (`crates/blindside-induct/target/release`);
- *the ghost* is `phase1.replay.ghost.Ghost`, what `--ghost` runs.

Nothing reads `World`. The three things taken off a match are its `result`, the player
policy's `decisions` (the record the trace is written from, plus the no-ops the trace
leaves out) and the trace file.

**Success** is what `--headless` reports and nothing else: `MatchResult.extracted` with
`cargo ≥ 1`, which the sim grants only to an agent standing within six cells of its own
shaft after the extraction window opens at 6:30, alive. A machine home at 4:00 waits
there; a machine home at 8:01 is *lost in the cave*. Outcomes in the tables are the
sim's three words — **extracted**, **destroyed**, **lost in the cave** — and *cargo home*
is the sim's cargo, counted only when extracted. An agent extracted with nothing aboard
is not a success and is noted where it happens.

**Seeds** [guess — no document fixes them]. Teaching seeds are the three CAVE-BLOCKS 9
taught on, **1, 3, 7**, then 2, 4, 5, 6, 8 for the count sweep, in that order. Unseen
seeds are **101–120**, twenty seeds no document has run. The rival always runs the
aggressive tree; the spoof and the scripted echo are on, as the build is. Nothing
sends Recall. Wherever a tree is run on the unseen seeds it is run once per seed; the
sim is deterministic per seed, so there is no variance to report within a cell.

**Two kinds of demonstration, because they are not the same match.** Where a bot stops
is decided by the run's thresholds (`RunSpec`), and the two ways of making a
demonstration set them differently:

| variant | what it is | the bot stops when | who chooses |
|---|---|---|---|
| **scripted** | `--teach-scripted TREE --enabled <all ten blocks>` | an enabled predicate rises at the **tree's own** threshold (level 0.45, theta 16 for the cautious tree), or an action ends | the tree, with its own numbers |
| **provisional** | what `--teach` gives a person: `RunSpec.for_demonstration`, every block, the block list's `provisional` values (level 0.25, theta 10, seconds 270, cells 8) | an enabled predicate rises at the **provisional** threshold, or an action ends | the reference tree, with its own numbers — a person who is exactly the cautious temperament and never hesitates |

The second is the one her session will produce, and it does not walk the reference's
path. A stop is a rising edge: at the provisional value the bot stops when the
machinery reaches 0.25, the cautious chooser says *carry on* (0.25 < 0.45), the
predicate then stays true, and there is no second edge at 0.45 — the bot is not asked
again until something else stops it. On seed 7 the reference's freeze at tick 5216
(level 0.46) never happens in the provisional run; the first freeze is at tick 5401,
because *late* happened to stop the bot with the machine at 0.89. The same for *lost*:
it rises at 10, the chooser says no, σ passes 16 unasked. CAVE-BLOCKS 3 states the half
of this it saw — *a player cannot teach a threshold lower than the provisional one*;
the other half is that **a player cannot react at a threshold above the provisional
one either**, except at stops that land there by chance. So the provisional rows below
are not "the reference, badly taught": they are the best any person at the window can
do with the bot asking where it asks. Both variants are in every table.

**The induced tree's unseen runs** are `--headless --tree induced.json`: only the
predicates the tree reads exist in the run, at the tree's fitted thresholds — the
corridor evaluator's rule, and what `--tree SOMEWHERE/tree.json` does in Part two of the
protocol.

**Disagreement between two trees** is measured two ways, both on the reference's own
decision points on the twenty unseen seeds (its scripted demonstration there, every block
enabled):

- *offline*: `induct decide` with the induced tree at every recorded stop, against the
  action the reference recorded — the share of stops at which the two rules read the
  same belief differently;
- *online*: `--ghost`, the induced tree re-running the demonstration's seed over the
  demonstration's blocks and thresholds, and `induct diff`'s first differing stop — where
  the paths part.

---

## 1. Reference versus induced

Three scripted demonstrations on seeds 1, 3, 7; induce; reference and induced headless
on seeds 101–120. (`m1.py`; `results/m1.md`.)

### 1.1 Cautious

| tree | unseen success | destroyed | lost in the cave | cargo home | rule (the render's sentence) | fitted | differs at the reference's stops (offline) | ghost parts on |
|---|---|---|---|---|---|---|---|---|
| **cautious reference** | **0/20** | 4 | 16 | 0 | If the machinery is loud, freeze until it passes. Otherwise if lost, go back. Otherwise if a deposit left to try, fetch from a deposit. Otherwise go back. | level 0.45, theta 16 | — | — |
| induced, scripted | 0/20 | 2 | 17 (+1 extracted empty, seed 113) | 0 | If the machinery is loud, freeze until it passes. Otherwise if lost, go back. Otherwise fetch from a deposit. | level 0.3, theta 12 | 27 of 179 stops (15%) | 14 of 20 seeds, at stop 4–11 |
| induced, provisional | 0/20 | 3 | 17 | 0 | (the same sentence) | level 0.6, theta 15 | 53 of 179 stops (30%) | 20 of 20 seeds, at stop 3–5 |

The demonstrations themselves: scripted, seeds 1/3/7 ended destroyed / lost / lost with
6, 10 and 13 stops; provisional, lost / destroyed / lost with 9, 8, 12 stops; 29 stops
of evidence either way. Both inductions were consistent. The reference's own scripted
demonstration and its headless match ended identically on 20 of 20 unseen seeds.

**Where the induced tree reads a stop differently.** Scripted: at *fetch ended* 11 of
31, *late rose* 7 of 19, *the last fix was a jump rose* 5 of 26, *freeze ended* 4 of 27;
never at *the machinery is loud rose* (0 of 31) or *lost rose* (0 of 7). Those are the
two places the tree has no *a deposit left to try* test — it says *fetch* where the
reference says *go back* with both deposits tried — and the four cells between theta 12
and 16. Provisional: **31 of 31** *the machinery is loud rose* stops — the reference
stops at 0.45 rising and freezes; the tree fitted at 0.6 walks on — plus 11 of 31 *fetch
ended*, 5 of 26 jumps, 4 of 19 *late*, 2 of 27 *freeze ended*.

**Why the sentence is not the reference's.** Three runs never showed a deposit
exhausted, so minimality drops the test (CAVE-BLOCKS 9 found the same). On the unseen
seeds the consequence is visible: the scripted-taught tree spent 25 stops in no-op
waits across 4 matches (9 in one of them), the provisional-taught tree 91 across 9
matches (14 in one) — a machine standing still, asking every ten seconds, with nothing
it has been taught to do. The reference never stalls.

**The fitted level is where the stops fell.** Scripted evidence brackets *loud* between
the loudest carry-on and the quietest freeze (the freezes are at 0.45–0.46; the
carry-ons that other stops caught are quieter), and the crate's fit in that band is 0.3:
a machine that freezes on cycles the reference never heard as loud. Provisional evidence brackets it between the 0.25 stops
(carry on) and the freezes that other stops happened to catch (0.79, 0.89, …), and the
roundest number is 0.6: a machine that walks through what the reference freezes at.
Neither is the temperament; both are exactly what the demonstrations said.

**Why the reference scores zero** (`m1b.py`; its last stop on each unseen seed is in
`results/m1b.md`). Every block enabled, the reference tree choosing, on 19 of 20 seeds
*late* stopped it at 4:30 and it chose *fetch* (13 seeds) or *freeze* (6) — never *go
back*, because nothing in it reads the clock. It did choose *go back* on 17 of 20 seeds,
at *lost*, and on 4 of those, home and no longer lost with a deposit still untried, it
went out again (CAVE-BLOCKS 2.4 predicted this: *home for good* is not in the set). Its
last stop was between 4:19 and 7:59 — *go back* on 13 seeds, on its way home or
searching when the clock ran out; *fetch* on 3; *freeze* on 4, standing at believed
place 5 when it was destroyed (the four deaths; CAVE-BLOCKS 8's finding). The 16 lost are a machine that
turned for home after the spoof, walked a chain that lies, and did not finish the search
before 8:00.

### 1.2 Aggressive

| tree | unseen success | destroyed | lost in the cave | cargo home | rule | fitted | differs at the reference's stops (offline) | ghost parts on |
|---|---|---|---|---|---|---|---|---|
| **aggressive reference** | **0/20** | 4 | 16 | 0 | If the machinery is loud, go to the machinery and download. Otherwise if a deposit left to try, fetch from a deposit. Otherwise go back. | level 0.3 | — | — |
| induced, scripted | 0/20 | 4 | 16 | 0 | If the machinery is loud, go to the machinery and download. Otherwise fetch from a deposit. | level 0.3 | 0 of 178 | 0 of 20 |
| induced, provisional | 0/20 | 4 | 16 | 0 | If a deposit left to try and the machinery is loud, go to the machinery and download. Otherwise if a deposit left to try, fetch from a deposit. Otherwise go back. | level 0.3 | 0 of 178 | 0 of 20 |

Scripted demonstrations on 1/3/7: lost, lost, lost (23 stops); provisional: destroyed,
destroyed, lost (26 stops). The aggressive temperament induces back exactly: both taught
trees decide every one of the reference's 178 unseen stops as it did and part from it on
no seed, and their twenty matches end as the reference's do. Its level fits at 0.3 from either
variant because the download it chooses at 0.3 is loud enough, often enough, for other
stops to bracket it. The 0/20 is the temperament: it interfaces on every cycle it hears
and never goes home.

Two smaller things from this table. The reference's scripted demonstration (every
block enabled, its own thresholds) ended differently from its headless match on **2 of
20** unseen seeds — the extra stops (*late*, *carrying*, *the last fix was a jump*
rising) let the tree re-read a belief whose own edge had been swallowed by the 5 s
re-arm, so CAVE-BLOCKS 9's *same match to the tick* holds for a demonstration over the
tree's own blocks and not quite for one over all ten. And the provisional variant of the
aggressive tree ends differently from the match on **9 of 20** seeds (§5): its 0.3 cue
is above the 0.25 the bot asks at, so the rival's temperament, taught by a person, is
not the rival.

### 1.3 What the blocks can reach — a threshold sweep the gate needs (`m1c.py`)

Not reference trees, not a proposal: scratchpad trees, run headless on the twenty unseen
seeds, to find out whether 70% is reachable by any rule over the day-one blocks.

**The cautious tree with *late → go back* under the freeze**, by the second it turns at:

| late (seconds =) | unseen success | destroyed | lost in the cave | cargo home | extracted between |
|---|---|---|---|---|---|
| 150 (2:30) | **16/20 (80%)** | 0 | 4 | 16 | 6:30–7:30 |
| 180 (3:00) | 13/20 (65%) | 0 | 7 | 13 | 6:30–7:40 |
| 210 (3:30) | 5/20 (25%) | 0 | 15 | 5 | 6:30–7:23 |
| 240 (4:00) | 8/20 (40%) | 0 | 12 | 8 | 6:30–7:54 |
| 255 (4:15) | 3/20 (15%) | 0 | 17 | 3 | 6:42–7:13 |
| **270 (4:30) — the provisional value, where the bot stops to ask** | **0/20** | 1 | 19 | 0 | — |
| 285 (4:45) | 0/20 | 2 | 18 | 0 | — |

**The cautious tree (level 0.45) at other values of *lost*:**

| theta | unseen success | destroyed | lost in the cave | extracted empty | seeds that succeed |
|---|---|---|---|---|---|
| 4 | 0/20 | 0 | 12 | 8 | — |
| 5 | 0/20 | 0 | 8 | 12 | — |
| **6** | **15/20 (75%)** | 0 | 5 | 0 | 101 102 104 105 106 107 109 110 111 112 114 115 116 117 120 |
| **7** | **14/20 (70%)** | 0 | 6 | 0 | 101 102 103 104 105 107 108 109 110 111 112 115 117 118 |
| 8 | 0/20 | 3 | 17 | 0 | — |
| 9 | 0/20 | 1 | 19 | 0 | — |
| **10 — the provisional value** | **0/20** | 3 | 16 | 0 | — |
| 12 — what three scripted demonstrations fit | 0/20 | 5 | 14 | 0 | — |
| 16 — the reference | 0/20 | 4 | 16 | 0 | — |

Every success in both sweeps carries one unit: the machine loads at A, turns for home
before the spoof lands (at 2:20 and 34 cells past its last beacon), reaches a shaft its
chain still tells the truth about, and waits three minutes to be collected. Theta 4 and
5 turn back before A and come home empty. Theta 8 and up, and *late* past 3:00, turn
back after the lie and search until the clock. The cliff is one cell of σ (7 → 8) and
about half a minute of clock (3:00 → 3:30, and the middle of that sweep is not
monotonic: 4:00 does better than 3:30 because of where the spoof catches each seed).

**The loop she would go through if she taught the obvious thing.** A chooser that is
the cautious tree plus *go back* at the *late* stop (270 s), three demonstrations on
1/3/7, induce, run on the unseen seeds:

| variant | teach outcomes (stops) | induced rule | fitted | unseen success | destroyed | lost |
|---|---|---|---|---|---|---|
| scripted | lost, lost, lost (5, 5, 12) | If the machinery is loud, freeze until it passes. Otherwise if late, go back. Otherwise fetch from a deposit. | level 0.3, **seconds 204** | **11/20 (55%)** | 0 | 9 |
| provisional | lost, lost, lost (6, 7, 12) | (the same sentence) | level 0.6, **seconds 264** | 3/20 (15%) | 1 | 16 |

Neither rule has a *lost* test, and rightly: in the three scripted runs σ never passed 6.9 at
a stop, so nothing was ever taught about being lost. The number is the thing to read.
The chooser turned back at 4:30 on every run, but the bot had not stopped since the
spoof's fix jump at 2:21–2:27 (seeds 1, 3) or the freeze at 4:20 (seed 7), so the
evidence brackets *late* as anywhere in (146.7, 260.8) seconds, and the crate's fit —
the round number nearest the middle of the widest band, checked here on three numbers:
204 in that band, 264 in the provisional variant's (257.6, 270.05), 0.3 in (0.22, 0.46)
— puts it at **204 seconds, 3:24**. That is a minute and six seconds before the person
turned, and by the sweep above a much better time to turn, which is why this taught
tree is the best-scoring thing in this document: **it scores 55% because of where the
bot did not stop.** The provisional variant, whose bot stopped at 4:17 (the machinery
at 0.25 on seed 7), is bracketed tightly and turns at 4:24: 3/20.

---

## 2. How many demonstrations

Cautious, 1 / 2 / 3 / 5 / 8 demonstrations (seeds 1; 1 3; 1 3 7; +2 4; +5 6 8), both
variants, induce, twenty unseen seeds. (`m2.py`; `results/m2.md`.)

| demos | variant | stops in evidence | internal nodes | predicates the rule tests | fitted level (ref 0.45) | fitted theta (ref 16) | words | unseen success | destroyed | lost | sentence |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | scripted | 6 | 1 | loud | 0.3 | — | 14 | 0/20 | 1 | 19 | If the machinery is loud, freeze until it passes. Otherwise fetch from a deposit. |
| 2 | scripted | 16 | 2 | loud, late | 0.3 | — | 19 | 0/20 | 2 | 18 | If the machinery is loud, freeze until it passes. Otherwise if late, go back. Otherwise fetch from a deposit. |
| 3 | scripted | 29 | 2 | loud, lost | 0.3 | 12 | 19 | 0/20 | 2 | 17 | If the machinery is loud, freeze until it passes. Otherwise if lost, go back. Otherwise fetch from a deposit. |
| 5 | scripted | 44 | 3 | deposit, loud, lost | 0.4 | 12 | 40 | 0/20 | 6 | 13 | If a deposit left to try and the machinery is loud, freeze until it passes. Otherwise if a deposit left to try and lost, go back. Otherwise if a deposit left to try, fetch from a deposit. Otherwise go back. |
| 8 | scripted | 74 | 3 | deposit, loud, lost | **0.45** | **14** | 40 | 0/20 | 5 | 15 | (the same) |
| 1 | provisional | 9 | 1 | late | — | — | 9 | 0/20 | 5 | 15 | If late, go back. Otherwise fetch from a deposit. |
| 2 | provisional | 17 | 2 | loud, late | 0.6 | — | 19 | 0/20 | 3 | 17 | If the machinery is loud, freeze until it passes. Otherwise if late, go back. Otherwise fetch from a deposit. |
| 3 | provisional | 29 | 2 | loud, lost | 0.6 | 15 | 19 | 0/20 | 3 | 17 | If the machinery is loud, freeze until it passes. Otherwise if lost, go back. Otherwise fetch from a deposit. |
| 5 | provisional | 48 | 3 | deposit, loud, lost | 0.6 | 13 | 40 | 0/20 | 3 | 16 | (the four-clause rule above) |
| 8 | provisional | 80 | 3 | deposit, loud, lost | **0.46** | **14** | 40 | 0/20 | 6 | 14 | (the same) |

Every induction was consistent. Where it plateaus: the **shape** of the rule is right at
three (the two reactions, in the right order) and complete at five (a deposit runs out
on seed 2 or 4 and the *go back when nothing is left* clause appears); the
**thresholds** are not settled at three — 0.3 or 0.6 against 0.45, 12 or 15 against 16 —
and converge at eight, to 0.45 / 0.46 and 14 from either variant. So three is enough for
the sentence a person reads and not for the numbers the machine runs on, and §1.3 says
the numbers are what decide the match.

Two things to know about the rule at one and two demonstrations. The single provisional
demonstration (seed 1) induces *If late, go back* from a run in which the chooser went
back because it was **lost**: with one *go back* recorded at a stop where *late* and
*lost* had both risen, either predicate explains it with one node, and the crate's
lexical tie-break picks `time_elapsed_exceeds` over `uncertainty_exceeds`. It is a
sentence, and it is the wrong sentence, and nothing in the evidence could say so. At two
demonstrations both variants say *late* for the same reason — seed 3's two lost-turns in the scripted runs (the provisional seed-3 run has no go-back at all; its *late* clause comes from seed 1 alone)
are at 6:38 and 7:00, with *late* true as well, and the tie goes to the clock. At three,
seed 7 *fetches* at 4:30 with the clock past 270 and turns back at σ 16.01 at 5:27,
which rules *late* out and leaves *lost*: it took a run in which the machine kept
working after 4:30 to show that the clock was not the reason.

The four-clause rule at five and eight is the cautious reference's shape rooted on *a
deposit left to try* instead of *the machinery is loud*: three internal nodes either
way, three predicates either way, and `deposit_remaining` sorts before
`machinery_audible`. Same decisions, forty words instead of twenty-eight, and every
clause begins *if a deposit left to try and …*.

---

## 3. Noisy teaching — R2 measured

Three cautious demonstrations on seeds 1, 3, 7 (29 stops). Flip *k* recorded choices at
random to a different action the window would have offered at that stop, re-induce; ten
flip sets per *k*; for every consistent result, twenty unseen seeds. The availability
rule is reconstructed from the stop's record [guess, §7]: *freeze* only when the
machinery was audible, *fetch* only with a deposit left, *go back* and *download* always.
(`m3.py`; `results/m3.md`, and every flip, rule and threshold in `results/m3.json`.)

**Scripted evidence:**

| k flipped | the query fires | a rule comes out | internal nodes, mean / max | predicates tested, mean / max | words, mean / max | unseen success, mean / best | distinct rules | same rule as k = 0 |
|---|---|---|---|---|---|---|---|---|
| 0 | — | 1 of 1 | 2 | 2 | 19 | 0/20 | 1 | — |
| 1 | **4 of 10** | 6 of 10 | 3.3 / 5 | 3.0 / 4 | **36 / 60** | 2.5 / **14** | 6 | 0 of 6 |
| 2 | **10 of 10** | 0 | — | — | — | — | — | — |
| 3 | 8 of 10 | 2 of 10 | 4.5 / 5 | 3.5 / 4 | 47 / 58 | 0 / 0 | 2 | 0 of 2 |
| 5 | 10 of 10 | 0 | — | — | — | — | — | — |

**Provisional evidence:**

| k flipped | the query fires | a rule comes out | internal nodes, mean / max | predicates tested, mean / max | words, mean / max | unseen success, mean / best | distinct rules | same rule as k = 0 |
|---|---|---|---|---|---|---|---|---|
| 0 | — | 1 of 1 | 2 | 2 | 19 | 0/20 | 1 | — |
| 1 | **7 of 10** | 3 of 10 | 3.3 / 4 | 3.3 / 4 | **33 / 42** | 0 / 0 | 3 | 0 of 3 |
| 2 | 10 of 10 | 0 | — | — | — | — | — | — |
| 3 | 10 of 10 | 0 | — | — | — | — | — | — |
| 5 | 10 of 10 | 0 | — | — | — | — | — | — |

What the rules look like when one comes out of one flip (scripted; each seen once unless
marked):

- twice: *If the machinery is loud, freeze until it passes. Otherwise if lost, go back.
  Otherwise fetch from a deposit.* — the k = 0 sentence with a different number in it.
  Flipping seed 3's stop 8 (a freeze) to *go back* refits level 0.453, theta 7.5: 1/20.
  Flipping seed 3's stop 6 (a *fetch* after a freeze, at 5:46 with σ 7.49) to *go back*
  refits **theta 7.0**: **14/20**, no deaths — the §1.3 window, reached by a mistake.
- *If the machinery is loud and the last fix was a jump, freeze until it passes.
  Otherwise if the machinery is loud and late and lost, freeze until it passes.
  Otherwise if the machinery is loud and late, go back. Otherwise if the machinery is
  loud, freeze until it passes. Otherwise if lost, go back. Otherwise fetch from a
  deposit.* — sixty words, five tests, from one freeze flipped to *go back*.
- *If the machinery is loud, freeze until it passes. Otherwise if lost and late, go
  back. Otherwise if lost, go to the machinery and download. Otherwise fetch from a
  deposit.* — one *go back* flipped to *download*, and the rule now sends a lost
  machine to the machinery before 5:31.
- *If the machinery is loud, freeze until it passes. Otherwise if the last fix was a
  jump, fetch from a deposit. Otherwise if late and lost, go back. Otherwise if late, go
  to the machinery and download. Otherwise fetch from a deposit.*
- *If the machinery is loud and late, freeze until it passes. Otherwise if the machinery
  is loud and lost, fetch from a deposit. Otherwise if the machinery is loud, freeze
  until it passes. Otherwise if lost, go back. Otherwise fetch from a deposit.*

At k = 3 the two survivors are 58 and 36 words with *late* at 412 seconds (6:52) and,
in one, *If the last fix was a jump, go to the machinery and download* at the top.

**The query, when it fires**, is the corridor's: the two stops side by side, every
block's label with its value and raw number, *you chose: go back* / *you chose: fetch
from a deposit*, *Which one would you do differently?* The pair it picks is readable —
in the k = 1 example it is the two runs' first stops, identical in every belief. One
thing to expect on screen: it names each stop by the **full path** of the seam's
contract copy (`…/SOMEWHERE/seam/contract/trace-seed-1.json`), which on her machine will
be most of a line.

**R2, in these numbers.** A person who is consistent gets a sentence of nineteen words
that reads as her temperament. A person who changes her mind **once** in three runs —
one stop in twenty-nine — gets the contradiction query 4 to 7 times in 10, and otherwise
a rule twice as long that may attribute a right action to a wrong belief, or send a lost
machine to the machinery. A person who changes her mind **twice** gets the query every
time. The rule stops being a sentence a person would read at exactly one inconsistency,
and the loop's answer to that is the query and the correction, not the rule.

---

## 4. Staged teaching

Demonstrations with a subset of blocks enabled, mixed with full ones. The stage sets are
the block list's `stage` fields: stage 1 = *a deposit left to try*, *carrying*, *late* +
*fetch*, *go back*; stage 2 adds *lost* and *the last fix was a jump*; full adds *the
machinery is loud*, *freeze*, *download*. The chooser for a staged run is the cautious
tree restricted to the blocks that exist [guess, §7]: stage 1 *deposit left? fetch :
go back*; stage 2 *lost (16)? go back : (deposit left? fetch : go back)*. The spoof
cannot be turned off without editing the build, so the drift run has it, unlike the
tutorial CAVE-BLOCKS 3.1 asks for. (`m4.py`; `results/m4.md`.)

**The demonstrations** (scripted variant; the provisional ones differ by one or two
stops and are in the results file):

| chooser | seed | stops | outcome | actions recorded |
|---|---|---|---|---|
| stage 1 | 1 | 5 | lost in the cave | fetch, go back |
| stage 1 | 3 | 4 | destroyed | fetch |
| stage 1 | 7 | 5 | lost in the cave | fetch, go back |
| stage 2 | 1 | 6 | lost in the cave | fetch, go back |
| stage 2 | 3 | 5 | destroyed | fetch |
| stage 2 | 7 | 7 | lost in the cave | fetch, go back |
| full | 1 | 6 | destroyed | fetch, freeze |
| full | 3 | 10 | lost in the cave | fetch, freeze, go back |
| full | 7 | 13 | lost in the cave | fetch, freeze, go back |

A stage-1 or stage-2 machine cannot hear the machinery and walks into it on seed 3.

**The inductions** — every set was consistent; the crate reads an absent block as false
and the mixed evidence never contradicts itself:

| set | variant | stops | rule | fitted | unseen success | destroyed | lost |
|---|---|---|---|---|---|---|---|
| tutorial: stage 1 @1, stage 2 @3, full @7 | scripted | 23 | If a deposit left to try and the machinery is loud, freeze until it passes. Otherwise if a deposit left to try and lost, go back. Otherwise if a deposit left to try, fetch from a deposit. Otherwise go back. | **level 0.2**, theta 11 | 0/20 | 2 | 18 |
| tutorial + full @2, @4 | scripted | 38 | (the same) | level 0.4, theta 11 | 0/20 | 4 | 15 |
| stages only: stage 1 @1, stage 2 @3 | scripted | 10 | If a deposit left to try, fetch from a deposit. Otherwise go back. | — | 0/20 | 4 | 16 |
| stage 1 ×3 | scripted | 14 | If a deposit left to try, fetch from a deposit. Otherwise go back. | — | 0/20 | 4 | 16 |
| stage 2 ×3 | scripted | 18 | If lost, go back. Otherwise fetch from a deposit. | theta 12 | 0/20 | 2 | 17 |
| three full (§1) | scripted | 29 | If the machinery is loud, freeze until it passes. Otherwise if lost, go back. Otherwise fetch from a deposit. | level 0.3, theta 12 | 0/20 | 2 | 17 |
| tutorial | provisional | 22 | (the four-clause rule) | level 0.6, theta 15 | 0/20 | 3 | 17 |
| tutorial + full @2, @4 | provisional | 41 | (the four-clause rule) | level 0.7, theta 13 | 0/20 | 2 | 17 |
| stages only | provisional | 10 | If a deposit left to try, fetch from a deposit. Otherwise go back. | — | 0/20 | 4 | 16 |
| stage 1 ×3 | provisional | 14 | (the same) | — | 0/20 | 4 | 16 |
| stage 2 ×3 | provisional | 19 | **If a deposit left to try, fetch from a deposit. Otherwise go back.** | — | 0/20 | 4 | 16 |
| three full (§1) | provisional | 29 | If the machinery is loud, freeze until it passes. Otherwise if lost, go back. Otherwise fetch from a deposit. | level 0.6, theta 15 | 0/20 | 3 | 17 |

The mixed sets do what the corridor's design promised: a tutorial run with fewer blocks
is evidence, not a contradiction, and the rule that comes out of the tutorial-shaped set
is the cautious temperament's — with two differences a person will see. It is rooted on
*a deposit left to try* (the stage-1 runs recorded *go back* with nothing left, so the
clause is present, and the tie-break puts it first: 40 words, four clauses, every one
beginning *if a deposit left to try and …*). And its level is **0.2** — below the 0.25
the bot even asks at — because the only stops with a loud reading come from one full run
and the band below the quietest freeze reaches down to silence; the machine so taught
freezes at anything it can hear. Two more full runs bring it to 0.4.

Three stage-2 runs at the provisional theta (10) induce no *lost* clause at all: the
chooser (theta 16) said *carry on* at every σ-10 stop, was never asked at 16, and the
only *go back* it recorded was with the deposits gone. The block a stage-2 run exists to
teach is the one that run cannot show.

---

## 5. The decision-point count, for real

On the reference trees' own paths, twenty unseen seeds, three run specs: *match* is
`--headless --tree` (only the tree's predicates exist); *scripted* is every block at the
tree's thresholds; *provisional* is every block at the provisional thresholds, the
reference choosing — the demonstration a person makes. A no-op stop is one the trace
leaves out (fetch with nothing left, freeze in silence); a carry-on stop is one at
which the chosen action is the one already running. (`m5.py`; `results/m5.md`.)

| tree | run spec | stops per match, mean | min | max | seconds of match per stop | no-op stops | carry-on stops | triggers, most frequent first (over 20 matches) |
|---|---|---|---|---|---|---|---|---|
| cautious | match | 5.8 | 3 | 9 | 91 | 0 | — | the machinery is loud rose 32 · fetch ended 30 · freeze ended 28 · start 20 · lost rose 7 |
| cautious | scripted | 8.9 | 5 | 13 | 55 | 0 | 81 of 179 | fetch ended 31 · loud rose 31 · freeze ended 27 · the last fix was a jump rose 26 · start 20 · late rose 19 · carrying rose 18 · lost rose 7 |
| **cautious** | **provisional** | **10.2** | **6** | **13** | **46** | 0 | **147 of 205 (72%)** | **loud rose 74** · fetch ended 28 · jump rose 27 · start 20 · late rose 19 · carrying rose 18 · lost rose 10 · **freeze ended 9** |
| aggressive | match | 5.5 | 3 | 8 | 88 | 0 | — | loud rose 61 · start 20 · fetch ended 20 · download ended 8 |
| aggressive | scripted | 8.9 | 5 | 12 | 53 | 0 | 103 of 178 | loud rose 61 · jump rose 26 · start 20 · fetch ended 20 · late rose 19 · carrying rose 18 · download ended 8 · lost rose 6 |
| aggressive | provisional | 9.8 | 6 | 12 | 46 | 0 | 131 of 196 (67%) | loud rose 75 · jump rose 30 · fetch ended 27 · start 20 · carrying rose 18 · late rose 18 · lost rose 8 |

Per seed, the demonstration a person makes on the cautious path: 10 12 11 12 9 10 9 11
11 6 13 9 10 9 11 10 11 13 9 9 stops.

**Ten stops in eight minutes, one every forty-six seconds** — CAVE-BLOCKS 3.1's estimate
(9–10, one every 45–50 s) and the protocol's *about ten stops per run, one every
forty-five seconds or so* are both right, and the size is the corridor's. What the
estimate did not have: **seven in ten of those stops are *carry on***, and the one that
fires most — 3.7 times a match — is *the machinery is loud* at 0.25, at which the
cautious answer is *carry on* every time. The freeze the cautious temperament is built
on happened 28 times in 20 matches when the tree ran alone and **9 times** when the bot
asked at 0.25 instead of 0.45: the provisional demonstration applies the temperament's
own rule a third as often as the temperament does, and (§1.2) the aggressive path
diverges from its match on 9 of 20 seeds for the same reason. *Lost* stopped the bot 10
times in 20 matches at the provisional 10 and 7 times at the reference's 16; the fix
jump 27 times; *late* once a match, on cue. No stop was ever a no-op
on either reference path.

---

## 6. What this means for the gate, plainly

**The 70%.** On the gate's own measure the cautious reference scores 0 of 20 and so does
the aggressive, so *three demonstrations → 70%* cannot be read as *the taught tree gets
most of what the reference gets*. The day-one blocks can reach the number — 75% with
*lost* at 6, 70% at 7, 80% with *late* at 2:30, 65% at 3:00 — by one shape of rule: load
once, turn for home before the spoof lands, wait. Nothing else in the sweeps scores
above 55%, and the induced trees from clean teaching score 0. The window is narrow (θ
6–7; *late* ≤ 3:00), it is below where the bot stops to ask (θ 10, 4:30), and where the
fit lands inside the bracket the stops leave is not the person's to choose. What she
should expect from Part two: the machine loads at A, walks on toward B, freezes when
the machine winds up, turns back when it is lost, walks a chain that lies, searches,
and the clock runs out — *lost in the cave* on about 17 seeds in 20, *destroyed* on 2 to
6, extracted on 0. If it stalls, standing still and asking every ten seconds late in the
match, that is the *deposit left to try* clause three runs could not teach. If instead
it goes home early with one unit and sits there for three minutes, the fit landed in the
window and it will score in the sixties or seventies; the one time that happened in
this document it was a flip at a stop with σ 7.5 that did it.

**R2.** Consistent teaching produces a legible rule — two tests, nineteen words, the
temperament in the right order — with thresholds that are not the temperament's and one
clause missing. One inconsistency in three runs is enough for the query to fire more
often than not, and the rules that survive it are twice as long, to sixty words and five
tests. A clean rule can be wrong about *why* while right about *what* — *late*
explaining a lost-turn with one or two runs in evidence — and its numbers are the
middle of the gaps between stops: *late* at 3:24 from a person who turned at 4:30. Two
inconsistencies and there is no rule, only the query. The staged tutorial induces
cleanly and yields a longer sentence than the flat one, rooted on the deposit by
tie-break, with a freeze level of 0.2 until two more full runs are added. So: expect the
sentence when she is consistent, expect the query when she is not, and expect the
sentence to say something slightly other than what she did — a number she never chose,
a clause she never had the chance to teach, a reason picked by alphabetical order.

**The stops.** Ten a run, forty-six seconds apart, seven of them *carry on*: the size
the corridor's gate was written for, not a click every twenty seconds. The trade in
CAVE-BLOCKS 3 was too many stops against too few; the number measured here is the one
it wanted. The cost is elsewhere: the bot asks about the machinery at 0.25 and about
being lost at 10, once, and a person who means 0.45 or 16 is asked at those values only
when another stop happens to land there. The fitted threshold then sits between the
loudest *carry on* and the quietest reaction, and on twenty seeds that gap is the
difference between a machine that freezes at everything (0.2, 0.3) and one that walks
through what the reference freezes at (0.6, 0.7).

---

## 7. Every guess, in one place

1. **Seeds.** Teaching on 1, 3, 7 (CAVE-BLOCKS 9's) then 2, 4, 5, 6, 8; unseen 101–120.
   No document fixes either set. The provisional-variant demonstration reproduces her
   session's stop rule but not her seeds: the protocol runs `--teach` without `--seed`,
   which is seed 7 three times.
2. **The provisional variant** is `RunSpec.for_demonstration` with the reference tree as
   chooser, built in `lab.demo(..., provisional=True)`; it is not a CLI mode. It is what a
   person who never hesitates and is exactly the temperament would record.
3. **Availability for flips (§3)**: *freeze* offered iff the stop's raw level > 0 (the
   `Hold` program's no-op rule), *fetch* iff *a deposit left to try* was true, *go back*
   and *download* always (`InterfaceMachinery` is a no-op only with no route to the
   machinery, and the survey map always has one). The trace does not record the panel's
   greying, so this is reconstructed. Flips are uniform over stops and over the other
   offered actions, `random.Random(1000 + 100k + i)`.
4. **Stage trees (§4)** are the cautious tree restricted to each stage's blocks, written
   to the scratchpad; the spoof stays on in the drift run because turning it off means
   editing `tuning.py`.
5. **The *late* and *theta* trees (§1.3)** are scratchpad files, not references and not
   proposals; the *late* test sits under the freeze so a loud machine still stops it
   first.
6. **Everything ran in-process** through the same classes the CLI uses, not through
   `python -m phase1` per run; the one-off check that this is the same thing is the
   byte-identical seed-7 trace in §0.
7. **"Place N"** in §1.1 is the trace's `junction` — the believed nearest survey place —
   reported as the sim wrote it; that place 5 is the machine's chamber is CAVE-BLOCKS 8
   and 9's reading of the same index, not something measured here.
8. **Words** are the render's `sentence` split on whitespace.
9. **Carry-on stops (§5)** are counted as *same action as the previous recorded stop*,
   which over-counts by one wherever an action ended and the same action was chosen
   fresh (a second *fetch* after the first deposit's load).
