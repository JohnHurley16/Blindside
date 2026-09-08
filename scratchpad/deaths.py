"""Deaths, closest approaches and final damage across seeds 1-8.

Two closest-approach numbers, because the hazard is not a circle:
  * `min cells` -- the least euclidean distance to the machine at any time, which is
    what the old disc measured and what the camera's zone flag still uses;
  * `margin`    -- the least (distance - lethal contour radius on that agent's own
    bearing) over the ticks when the hazard was actually lethal. Negative is dead.
    This is the number the 5:41 beat is about: 0.038 cells.
"""
import math
import sys

sys.path.insert(0, r"C:/Users/jackh/documents/programming/Blindside")

from phase1 import tuning as T
from phase1.match.sim import Sim


def fmt(t):
    return f"{int(t) // 60}:{t % 60:04.1f}"


def run(seed):
    sim = Sim(seed)
    a = sim._world.ancient
    near = {n: float("inf") for n in sim._world.agents}
    margin = {n: float("inf") for n in sim._world.agents}
    peak = {n: 0.0 for n in sim._world.agents}
    while not sim.over:
        sim.step()
        lethal = a.is_lethal(sim.t)
        for n, ag in sim._world.agents.items():
            if not ag.alive:
                continue
            d = math.hypot(ag.x - a.x, ag.y - a.y)
            near[n] = min(near[n], d)
            if not lethal:
                continue
            c = a.coupling_at(ag.x, ag.y, sim.t)
            peak[n] = max(peak[n], c)
            # the lethal radius on this bearing: coupling = 1 at d * sqrt(c)
            margin[n] = min(margin[n], d - d * math.sqrt(c))
    # A death is recorded inside the same tick that flips `alive`, so the fatal instant
    # is never seen by the loop above. Fold it back in from the event.
    deaths = [(e.t, e.data["agent"], e.data.get("cause")) for e in sim._world.events
              if e.kind == "death"]
    for e in sim._world.events:
        if e.kind != "death":
            continue
        n, x, y = e.data["agent"], e.data["x"], e.data["y"]
        d = math.hypot(x - a.x, y - a.y)
        c = a.coupling_at(x, y, e.t)
        near[n] = min(near[n], d)
        peak[n] = max(peak[n], c)
        margin[n] = min(margin[n], d - d * math.sqrt(c))
    return sim, deaths, near, margin, peak


print(f"{'seed':<5}{"result":<17}{'deaths':<26}{'min cells P/R':<16}"
      f"{'margin P/R':<18}{'peak coupling P/R':<20}{'damage P/R'}")
for s in range(1, 9):
    sim, deaths, near, margin, peak = run(s)
    d = "; ".join(f"{n[0].upper()}@{fmt(t)}" for t, n, _ in deaths) or "-"
    res = str(sim.result).split(" (")[0]
    def pr(m, w=6, p=2):
        return (f"{m['player']:{w}.{p}f}/{m['rival']:{w}.{p}f}"
                .replace("   inf", "    --"))
    print(f"{s:<5}{res:<17}{d:<26}{pr(near):<16}{pr(margin):<18}"
          f"{pr(peak, 6, 3):<20}"
          f"{sim._world.agents['player'].damage:.3f}/{sim._world.agents['rival'].damage:.3f}")
