# Phase 2 gate — session protocol

Twenty minutes, one non-engineer, no build needed. This is the test of whether a player who
*teaches* a machine cares what it does — the thing the failed Phase 1 session said was missing.
Score it on paper, during, not from memory afterwards.

## Before she sits down

- `python -m phase2` opens the window. Run it once yourself first so the first launch's warm-up
  is not her first impression.
- Have this sheet printed or on a second screen. You write; she plays.
- Do not explain the game. Do not explain the blocks. Do not say "drift".

## What you say — all of it

> "It's a machine in a tunnel. You can't drive it. When it stops, it'll ask you what to do —
> press 1 or 2. Teach it. After a few runs it'll tell you what it thinks the rule is."

Then nothing, unless she asks a question — and if she does, write the question down before you
answer it; the questions are data.

## The session, in order

The window runs six stages by itself. She presses `1` or `2` at each stop.

| Stage | What happens | What to write down |
|---|---|---|
| 1 — first blocks | No drift; only *a branch here* and *take a branch* exist | Does she notice there's only one real choice? |
| 2 — drift arrives | *lost* and *go back* appear | **Her first words when the bot gets lost.** Does she say anything before it does? |
| 3 — the full problem | All blocks | When does she stop reading the panel and start deciding fast? |
| 4, 5, 6 — three demonstrations | Same, three seeds; these are what the rule is induced from | Any moment she says *why* she chose — write the sentence. |
| The rule | It shows the tree and one sentence: *"If carrying, go back. Otherwise if lost…"* | **Read it to her? No — let her read it.** Does she say "yes, that's what I did"? Does she disagree? |
| `G` — ghost | Replays a run with the bot choosing by the rule; flags the first stop where it differs from her | See criterion 2 |
| arrows, `T`, `P` — correction | Scrub to a stop, take over, choose again, promote | See criterion 4 — **start a stopwatch when she says she wants to change something** |

## The four criteria, from `ROADMAP.md`

Tick them in the moment.

- [ ] **≥70% on unseen seeds.** The window prints the success rate after induction. Write the
      number: ____ %.
- [ ] **She reads the rule and predicts the next choice.** After the tree is shown, before the
      ghost runs, ask: *"At the next stop, what will it do?"* Right / wrong / wouldn't say.
- [ ] **On a failure she names the wrong rule UNPROMPTED.** When the ghost differs from her, or
      a run fails, say nothing. Wait ten seconds. Write down what she says. If she says nothing,
      *then* ask "why do you think it did that?" — and mark it prompted. **This is the one that
      matters.** The roadmap calls it "the real one": if a player cannot diagnose their own
      machine, the forensics layer does not work.
- [ ] **A correction takes under 60 seconds end to end.** From "I want to change that" to the
      re-induced rule on screen. Time: ____ s.

## The two questions that are not on the roadmap, and are why this session exists

Ask these at the end, verbatim, and write the answers verbatim.

1. *"Is that machine yours?"*
2. *"Would you want to watch it go into a cave for eight minutes now?"*

The Phase 1 tester said she had no connection to the bot because she'd put no work into it. These
two questions test whether twenty minutes of teaching changes that. They are the hinge of the
whole re-sequenced plan — if the answer to 2 is no, teaching is not the hook either.

## When she disengaged

If she does, write the stage and the clock. Bored during the tutorial is a tutorial problem; bored
after the rule is shown is a much worse one.

## Afterwards

Put the sheet, with her words, in `docs/phase2-playtests/YYYY-MM-DD-gate.md`. Score against the
four criteria and the two questions. Do not soften it — the last report was scored honestly and
it was the most useful document in the project.
