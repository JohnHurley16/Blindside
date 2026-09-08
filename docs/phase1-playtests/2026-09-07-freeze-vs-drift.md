# Finding — the frozen ending and the map snapping back are the same mechanism

**A design tension, deliberately not tuned away.** Fixing the thing that made the machine
stand against a wall for two and a half minutes also removed every mid-sized correction
from the match. One attempt was made to keep both; it recovered half, and the other half is
written down here rather than hidden behind a constant.

Measured over 88 runs per build — eight seeds crossed with no-recall and Recall at 2:00,
plus the 2:00–6:00 sweep — by an instrument that reads `World` directly and is never
imported by `phase1`. "In-cave stillness" is the longest unbroken stretch (< 0.005 cells per
tick) while the player is still alive and still in the cave; a destroyed agent lies where it
fell and is not counted as frozen.

---

## The two numbers, and that they move together

| build | in-cave stillness > 60 s | worst | 8–16 cell fixes, no recall | 8–16, recall 3:00 | rival deaths | kills at 6:56 |
|---|---|---|---|---|---|---|
| **base** (before this round) | 16 / 88 | 157.2 s | 7 | 6 | 49 / 88 | 8 |
| this round, before the attempt | 1 / 88 | 68.2 s | 0 | 1 | 33 / 88 | 1 |
| **this round, shipped** | **1 / 88** | **68.2 s** | **0** | 1 | **39 / 88** | **7** |
| this round, escape memory off | 7 / 88 | **173.0 s** | **12** | 0 | 37 / 88 | 7 |
| this round, jam breaker off | 8 / 88 | 78.5 s | 1 | 1 | **48 / 88** | 11 |

Single-variable isolation, one change at a time off the finished build. Read the last two
rows against the second:

- **The escape memory is the freeze fix, and it is also what emptied the 8–16 band.** Turn
  it off and twelve mid-sized fixes come back — more than base had — and the worst freeze
  goes to **173 s, worse than base.** Not a coincidence and not two effects: one cause.
- **The jam breaker is the deaths, and it is not the jump band.** Turn it off and the rival
  dies 48 times again, but the 8–16 band stays empty.

So there are two levers, not one, and only one of them is a trade.

---

## Why they are one mechanism

The 8–16 cell fixes in the base build are not drift being corrected. They are **a tug of war
between the lie and the honest chain**, and it only happens to a machine that is standing
still.

The cloned beacon has `SPOOF_RANGE = 18` and `SPOOF_REASSERT_S = 8`: it shouts every eight
seconds across eighteen cells. An honest beacon has range 6 and no reassert period at all —
it answers on the rising edge and then goes quiet forever. A machine walking through the
overlap gets the lie once, or the truth once, and moves on. A machine **loitering** in the
overlap gets both, alternately, for as long as it loiters, and each hand-over drags the
estimate by the distance the two anchors disagree — which is eight to eleven cells.

Base build, seed 1, no recall — five of that build's seven 8–16 jumps, in fifteen seconds:

```
373.80  player_5   11.3      <- the lie
378.55  player_13   8.3      <- an honest beacon takes it back
381.80  player_5    9.2      <- the lie again
383.35  player_11  10.7      <- back again
388.85  player_5    9.7
```

The agent producing that trace had been in wall-escape for the previous ninety seconds. It
is the map snapping because the machine is pinned between two anchors that disagree, not
because it has travelled far enough to have drifted.

**The escape memory stops the pinning.** Four remembered failed headings at 50° means the
machine cannot choose the same wall seven times running, so it leaves — and leaving is
exactly what ends the tug of war. Same change, both effects.

---

## The attempt that was made, and what it recovered

One attempt, on the lever that is *not* the trade: **the jam breaker no longer fires while
the aggressive agent is investigating the machinery.** The carve-out already existed for
`interfacing` — the last eighty seconds of that approach — and an agent that has heard the
machinery and turned toward a bearing has a decision in hand for the whole approach, not
just the end of it. Answering "briefly stopped" with "take the longest open line on the map"
throws that decision away.

It is freeze-neutral by construction: only the aggressive temperament investigates, and the
freeze is measured on the cautious one.

**It recovered the late-match kill and about a third of the missing deaths, and cost
nothing.**

| | before the attempt | after | base, for reference |
|---|---|---|---|
| rival deaths | 33 / 88 | **39 / 88** | 49 / 88 |
| kills at 6:56 — the only firing in the last two minutes | 1 / 88 | **7 / 88** | 8 / 88 |
| in-cave stillness > 60 s | 1 / 88 | **1 / 88** | 16 / 88 |
| worst in-cave stillness | 68.2 s | **68.2 s** | 157.2 s |
| player extractions | 19 / 88 | 19 / 88 | 17 / 88 |
| 8–16 cell fixes, no recall | 0 | **0** | 7 |

The last beat — a machine dying in the final ninety seconds, once, at 6:56 — is back on
seven of eighty-eight runs against base's eight, and the freeze numbers did not move by a
tenth of a second. The rival's route changes enough to alter what the player hears on 32 of
80 runs, and the player's stillness figures are still identical to the digit, which is the
evidence that this lever and the freeze lever are genuinely separate.

**It did not restore the jump band, and nothing on this lever could have.** The band is the
escape memory's doing, and that is the trade below.

---

## What is left, and what the designer should decide

**Nothing further was reverted.** The escape memory stays. The choice it presents is real:

1. **A machine that stops grinding walls stops being pinned between the lie and the truth,
   and the map stops snapping.** The drama of a fix that moves the estimate ten cells is a
   symptom of the machine being stuck, not of it being lost. Base was more watchable in that
   one respect *because it was failing*.
2. **The 34-cell fix survives either way.** The spoof's own correction — the moment the
   agent walks back into its shaft transponder's range at ~150 s and is moved 32.4–34.0
   cells — is present in every seed of every build. The beat that matters most is not what
   this trade costs.
3. **If mid-match corrections are wanted on their own merits, the lever is the beacon model,
   not the policy.** Honest beacons currently speak once, on the rising edge; the liar
   speaks every eight seconds. Giving honest beacons a reassert period would produce
   contested fixes from a machine that is *moving* — the tug of war without the pinning.
   That is a change to the central mechanic of the match and is not made here.

**Recommendation: do not restore it by loosening the escape memory.** The measurement above
shows that path costs a 173-second freeze, which is worse than the state this round was
asked to fix, and buys twelve fixes in a match nobody is watching by then.
