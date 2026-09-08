import math, sys
sys.path.insert(0, r"C:/Users/jackh/documents/programming/Blindside")
import numpy as np
from phase1 import tuning as T
from phase1.match.sim import Sim
from phase1.view.shock_lobe import BEARINGS, ShockLobe

sim = Sim(7, stage=True)
while sim.t < 191.0 and not sim.over:
    sim.step()
frame = sim.stage()
lobe = ShockLobe(None, frame.ancient, frame.grid)
a = sim._world.ancient
t, aim, level = sim.t, frame.ancient.bearing_deg, T.ANCIENT_FELT_COUPLING
drawn = lobe._contour(level, aim)

def c(theta, r):
    return a.coupling_at(a.x + math.cos(theta)*r, a.y + math.sin(theta)*r, t)

bad = []
for k in range(BEARINGS):
    th = 2*math.pi*k/BEARINGS
    rs = np.arange(0.05, 60.0, 0.02)
    vals = np.array([c(th, r) for r in rs])
    inside = vals >= level
    first_out = rs[np.argmax(~inside)] if (~inside).any() else 60.0
    last_in = rs[len(rs)-1-np.argmax(inside[::-1])] if inside.any() else 0.0
    err = abs(float(drawn[k]) - first_out)
    if err > 0.05:
        bad.append((k, math.degrees(th), float(drawn[k]), first_out, last_in,
                    int(inside.sum())))
print(f"aim {aim} deg, level {level}: {len(bad)} of {BEARINGS} bearings disagree by >0.05")
for k, deg, dr, fo, li, n in bad:
    print(f"  ray {k:3d} ({deg:6.1f} deg): drawn {dr:8.4f}  first-out {fo:8.4f}  "
          f"last-in {li:8.4f}  inside samples {n}")
