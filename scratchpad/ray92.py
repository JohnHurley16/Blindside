import math, sys
sys.path.insert(0, r"C:/Users/jackh/documents/programming/Blindside")
import numpy as np
from phase1 import tuning as T
from phase1.match.sim import Sim
from phase1.view.shock_lobe import BEARINGS, ShockLobe, _gain

sim = Sim(7, stage=True)
while sim.t < 191.0 and not sim.over:
    sim.step()
frame = sim.stage()
lobe = ShockLobe(None, frame.ancient, frame.grid)
a = sim._world.ancient
t, aim, level = sim.t, frame.ancient.bearing_deg, T.ANCIENT_FELT_COUPLING
k = 92
th = 2 * math.pi * k / BEARINGS
need = T.ANCIENT_RADIUS * math.sqrt(float(_gain(np.array([th]), aim)[0]) / level)
print(f"ray {k}, theta {math.degrees(th)} deg, need coupled = {need:.6f}")
print(f"{'r':>8} {'view coupled':>14} {'truth coupled':>14} {'truth coupling':>15} {'view says':>10}")
for r in np.arange(17.75, 18.80, 0.125):
    v = float(lobe._coupled(np.full(BEARINGS, r))[k])
    px, py = a.x + math.cos(th) * r, a.y + math.sin(th) * r
    f = float(a.factor[min(max(int(py), 0), 119), min(max(int(px), 0), 199)])
    print(f"{r:8.3f} {v:14.6f} {r*f:14.6f} {a.coupling_at(px, py, t):15.6f} "
          f"{'OUT' if v >= need else 'in':>10}")
