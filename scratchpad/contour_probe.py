"""Which contour definition, and how well does the drawn table hold it?

The reference is the same closed form `Ancient.coupling_at` computes, vectorised over a
0.002-cell scan (ten times finer than the drawn table) and checked against coupling_at
itself point by point first, so it is the model and not a second approximation.
"""
import math, sys
sys.path.insert(0, r"C:/Users/jackh/documents/programming/Blindside")
import numpy as np
from phase1 import tuning as T
from phase1.match.sim import Sim
from phase1.view.shock_lobe import BEARINGS, ShockLobe

sim = Sim(7, stage=True)
a = sim._world.ancient
F = a.factor
RS = np.arange(0.01, 40.0, 0.002)


def ref(theta, aim, level, outermost):
    g = T.ANCIENT_LOBE_FLOOR + (1 - T.ANCIENT_LOBE_FLOOR) * math.cos(theta - math.radians(aim)) ** 2
    need = T.ANCIENT_RADIUS * math.sqrt(g / level)
    xs = np.clip((a.x + math.cos(theta) * RS).astype(np.int32), 0, 199)
    ys = np.clip((a.y + math.sin(theta) * RS).astype(np.int32), 0, 119)
    coupled = RS * F[ys, xs]
    ins = coupled < need
    if not ins.any():
        return 0.0
    if outermost:
        i = len(RS) - 1 - int(np.argmax(ins[::-1]))
        return 40.0 if i == len(RS) - 1 else float(RS[i])
    out = ~ins
    return 40.0 if not out.any() else float(RS[int(np.argmax(out))])


# prove the vectorised reference is coupling_at
for theta in (0.3, 1.7, 2.6, 4.4):
    for r in (3.0, 9.5, 18.2, 26.7):
        px, py = a.x + math.cos(theta) * r, a.y + math.sin(theta) * r
        g = T.ANCIENT_LOBE_FLOOR + (1 - T.ANCIENT_LOBE_FLOOR) * math.cos(theta - math.radians(256.0)) ** 2
        mine = g * (T.ANCIENT_RADIUS / (r * F[int(py), int(px)])) ** 2
        assert abs(mine - a.coupling_at(px, py, 341.0)) < 1e-12, (mine, r, theta)
print("vectorised reference == coupling_at to 1e-12 at 16 probe points\n")

for outermost in (True, False):
    print(f"--- drawn = current code, reference = {'OUTERMOST' if outermost else 'FIRST'} crossing")
    for firing_t in (41.0, 116.0, 191.0, 266.0, 341.0, 416.0):
        while sim.t < firing_t and not sim.over:
            sim.step()
        frame = sim.stage()
        lobe = ShockLobe(None, frame.ancient, frame.grid)
        aim = frame.ancient.bearing_deg
        line = f"  aim {aim:6.1f}"
        for level, name in ((1.0, "lethal"), (T.ANCIENT_FELT_COUPLING, "felt")):
            drawn = lobe._contour(level, aim)
            e36 = e180 = 0.0
            n = 0
            for k in range(BEARINGS):
                w = ref(2 * math.pi * k / BEARINGS, aim, level, outermost)
                e = abs(float(drawn[k]) - w)
                if e > 0.05:
                    n += 1
                e180 = max(e180, e)
                if k % 5 == 0:
                    e36 = max(e36, e)
            line += f" | {name}: 36-max {e36:.5f}  180-max {e180:.5f}  bad rays {n}"
        print(line)
    sim = Sim(7, stage=True)
    a = sim._world.ancient
    F = a.factor
