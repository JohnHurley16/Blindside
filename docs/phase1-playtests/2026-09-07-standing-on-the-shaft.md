# Finding — the recalled machine stands on its own extraction point for three minutes and cannot tell

**Not a bug report and not a request for a fix.** This is behaviour nobody designed,
produced by the parts interacting, and it is the thesis of the whole game happening by
itself. It is written down before it gets tuned away by accident.

Measured on the Phase 1 build on `claude/phase1-pacing` (the pacing round: jam breaker,
escape memory, search spiral, clearance fix; no go-back-out branch). Eight seeds, Recall
sent at 2:00, no other input. Numbers come from an instrument that reads `World` directly
and lives outside the `phase1` package — never imported by it, and it changes nothing.

---

## What happens

Between **t = 200 s and t = 380 s** — three minutes, from 3:20 to 6:20 — the agent is
**within 8 true cells of its own shaft 100% of the time, in all eight seeds.**

| seed | median true distance to its shaft, 200–380 s | closest | furthest | longest stretch inside a 2-cell circle |
|---|---|---|---|---|
| 1 | 5.37 | 2.21 | 7.27 | **82.5 s** |
| 2 | 5.10 | 0.57 | 7.23 | 23.0 s |
| 3 | 4.87 | 0.81 | 7.08 | 15.8 s |
| 4 | 5.21 | 2.56 | 5.57 | **80.8 s** |
| 5 | 5.29 | 3.03 | 7.28 | 39.0 s |
| 6 | 5.20 | 0.29 | 7.15 | 36.0 s |
| 7 | 5.34 | 1.44 | 7.07 | **69.8 s** |
| 8 | 5.15 | 0.51 | 6.40 | **68.8 s** |

`EXTRACT_RADIUS` is 6.0 cells. For most of those three minutes the agent is *inside the
collection radius of the thing it is looking for*, shuffling in a circle two cells across.

**`Policy.heard_shaft()` is false at every one-second sample of that window, in all eight
seeds.** The machine is standing on the extraction point and its own test for "am I at the
extraction point" says no, continuously, for three minutes.

It does not merely fail to notice. **It believes it is somewhere else entirely.** At the end
of the match it believes it is at roughly (35–47, 40–45) while it is truly at (8.6–15.6,
56.6–64.8), and it believes HOME is at (14, 60) — which is exactly where the true shaft is.
So it thinks it has about twenty-eight cells still to walk while it is standing five cells
away, in the right place, with the right map, holding the right answer.

---

## Why — the mechanism, which is three correct parts

**1. An honest beacon speaks only on the rising edge.** `SensorRig._beacons` emits a fix
when a beacon enters range (`rising`) or when its `reassert_period` says to. The
survey-placed shaft transponder has no reassert period, so it answers exactly when the
agent crosses into its 10-cell range. Across all eight seeds the shaft transponder fixes
**twice in the whole match**: once at t = 0.05 (jump ~0.1 cells, leaving the shaft) and once
at **t = 150–155 s, with a jump of 32.4–34.0 cells** — the recalled agent walking back into
its own range and being violently corrected. After that it never leaves the 10-cell range
again, so the only truth anchor in the cave never speaks again either. It is not broken. It
already told the agent everything it had to say.

**2. The lie does not stop talking.** `SPOOF_REASSERT_S = 8.0`, `SPOOF_RANGE = 18.0`. The
cloned beacon `player_5` re-announces itself every eight seconds for the rest of the match:
**31 fixes per seed, from ~147 s to ~387 s, uninterrupted.**

**3. The test is a recency test, not a presence test.**

```python
def heard_shaft(self) -> bool:
    return any(f.beacon_id == self.shaft_beacon_id for f in self.b.fixes[-4:])
```

Four fixes deep. The liar produces one every eight seconds. From the moment the clone starts
reasserting, **the shaft can never be in the last four fixes again**, no matter where the
agent stands. The window is thirty-two seconds wide and the honest anchor is silent for two
hundred.

None of the three is wrong on its own. Together they build a machine that is standing in the
right place and is structurally incapable of finding out.

---

## The part that is worse than failing

**It extracts anyway. All eight seeds, one cargo, every time.**

At 6:30 the extraction window opens, `Sim._extraction` measures the *true* distance to the
shaft, finds the agent inside `EXTRACT_RADIUS`, and collects it. The match reports
`extracted, cargo 1` and the player is told they won.

The machine never agreed. Its own root node still reads `SEARCH FOR THE SHAFT`, its
believed position is twenty-eight cells off, and it was three minutes into a widening spiral
looking for something it was standing on. The score and the machine's own account of the
match disagree completely, and only the score is shown.

---

## Why this is the game

`GLOSSARY.md` and the design both say the point is a machine you cannot steer, whose model
of the world can be attacked. This is that, unscripted:

- The attack is not "make it walk into a wall". It is **"make it unable to recognise
  success"** — the beacon chain was the instrument it recognises home with, and one cloned
  beacon jams it for the remaining four minutes.
- The player watching the operator view sees a machine that failed. The spectator view sees
  it standing on the pad. **The gap between those two pictures is the whole product.** The
  spectator display is the only place this reads at all, which is an argument for that
  display existing, made by the sim rather than by a document.
- It is the most legible spoof consequence Phase 1 has produced, and it happens at **Recall
  2:00 — the one recall timing that extracts** — so it is on the path a player is most
  likely to take.

---

## What the designer has to decide (not decided here, and not touched)

1. **Is `heard_shaft()`'s four-fix window deliberate?** As an "instruments can be starved by
   a louder liar" vulnerability it is excellent and should be kept and made visible. As an
   accident it is a one-line fix (ask whether the shaft has *ever* answered near here, or
   keep a separate shaft-fix timestamp) and the whole three minutes disappears with it.
   These are opposite decisions and the code currently records no intent either way.
2. **Should extraction believe the world or the machine?** Being collected while lost is
   currently a silent win. If the point is that you are responsible for a machine you cannot
   steer, being collected by luck may deserve to read differently from arriving on purpose.
3. **Should the display say it?** Nothing on screen currently states "it is 5 cells from the
   shaft and does not know". Saying it in the operator view would break the invariant. Saying
   it in the spectator view is exactly what that view is for, and the number to draw is
   already in `StageFrame`.

## What was guessed

Nothing in the numbers. The 200–380 s window and the 2-cell circle are choices of how to
report, not results: 200 s is after the spoof has fully taken hold in every seed and 380 s is
before the extraction window opens, and 2 cells is the smallest circle that still contains a
recognisable "shuffling on the spot". The stated conclusion does not depend on either — the
figure that carries it is `heard_shaft()` being false at every sample while the true distance
never exceeds 7.3 cells.
