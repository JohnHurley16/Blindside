# The cave session — she teaches it, then watches it

> **Do not run this yet.** Measured 2026-09-08: the cave as tuned cannot be won by the rule she
> would teach — both reference rules extract 0 of 20 on unseen seeds, 4 of 20 with the spoof
> off. She would lose every time whatever she taught, which tests nothing and costs her
> goodwill. The options are in `docs/CAVE-WINNABLE.md` and the decision is P2X-11 on the board.
> Run the corridor session (`PROTOCOL.md`) now; run this one after the cave is winnable.

Run this **after** the corridor session (`PROTOCOL.md`), on the same day if she is willing. The
corridor asks whether teaching works. This asks the question the whole re-sequence rests on:
does she care about a machine she taught, when it goes somewhere she cannot follow.

## Before she sits down

- `python -m phase1 --teach --workdir SOMEWHERE` opens the teaching window. Run it once yourself.
  The clock stops at every stop; a demonstration is not timed.
- Three demonstrations, then `python -m phase1 --induce SOMEWHERE` prints the rule, then
  `python -m phase1 --tree SOMEWHERE/tree.json` runs the eight-minute match on it with the full
  spectator display. Have the three commands ready; do not make her wait on typing.
- Sheet printed. You write; she plays.

## What you say

> "Same machine, real cave now. When it stops, it'll tell you what it believes and ask what to
> do. Teach it. Then we'll watch it go in on its own."

Nothing else. If she asks what a word on the panel means — *lost*, *the last fix was a jump* —
write the question down first, then answer in one sentence.

## Part one — teaching, three runs

About ten stops per run, one every forty-five seconds or so. At each stop the panel shows six
beliefs in plain words and four things it can do; the impossible one is greyed and says why.

| Write down | Why |
|---|---|
| Her first words at the first stop | Does the panel make sense cold? |
| Any stop where she hesitates more than ten seconds, and what she says | That is a belief she cannot read, or a choice she cannot make |
| Every time she chooses **[4] go to the machinery and download** | This is the block that makes the rival dangerous. Does she want it for herself? |
| Every time she chooses **[3] freeze** | She has learnt the machinery is dangerous — from what? |
| Any sentence beginning "because" | The rule, in her words, before the induction says it |

## The rule

`--induce` prints the tree and one sentence. **Let her read it.** Then ask, verbatim:

> "Is that what you were doing?"

Yes / no / partly, and her words. If she disagrees, that is the most valuable sentence of the
session — write it exactly.

## Part two — watching, eight minutes

`--tree` runs the match on her rule. Truth on the left, the machine's own map inset, the two
numbers on the right. **This is the Phase 1 spectator gate, re-run on a machine she built.** Score
the four signals from `PHASE-1-SPECTATOR-TEST.md` as before — talks to the screen, guesses,
forms and corrects a wrong theory, tension at Recall — and write the clock beside each.

Add these, because they are what changed:

| Moment | Write down |
|---|---|
| The first time it does something she taught | Does she say so? ("There — that's the go-back.") |
| The first time it does something she did **not** expect | What she says, unprompted. Wait ten seconds before asking anything. |
| The spoof, about 2:20 — the big number leaps | Does she connect it to the other machine? |
| If it walks toward the machinery | Does she know why? Does she want to stop it? Does she reach for the key? |
| If it dies | Her words. Then, after a beat: *"What would you teach it differently?"* — and if she answers, `python -m phase1 --teach --resume WORKDIR --trace N --stop K` replays that demonstration to the stop she names and lets her choose differently by hand; the rule is re-induced and shown. Start the stopwatch. |
| Recall — `R`, once | When, if ever, and what she says before pressing it |

## Afterwards — the two questions

Verbatim, and write the answers verbatim.

1. *"Was that machine yours?"*
2. *"Do you want to teach it again and send it back in?"*

The second is the whole game — teach, run, diagnose, correct — asked as one question. If she says
yes, the loop closes and R1, R2 and R3 are all answered in one afternoon. If she says no, write
down what she says *instead*, because that is the design finding.

## Scoring

Write it up as `docs/phase2-playtests/YYYY-MM-DD-cave.md`: the corridor's four criteria, the
spectator's four signals, the two questions, and every sentence she said unprompted. Do not
soften it. The September report was scored honestly and it was the most useful document in the
project; this one decides whether the plan is right.
