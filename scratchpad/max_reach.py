import math, sys
sys.path.insert(0, r"C:/Users/jackh/documents/programming/Blindside")
import numpy as np
from phase1 import tuning as T
from phase1.match.sim import Sim

sim = Sim(7, stage=True)
a = sim._world.ancient
worst = 0.0
for aim in range(0, 360, 4):
    for k in range(180):
        th = 2 * math.pi * k / 180
        need = T.ANCIENT_RADIUS * math.sqrt(
            (T.ANCIENT_LOBE_FLOOR + (1 - T.ANCIENT_LOBE_FLOOR)
             * math.cos(th - math.radians(aim)) ** 2) / T.ANCIENT_FELT_COUPLING)
        rs = np.arange(0.05, 60.0, 0.05)
        xs = np.clip((a.x + np.cos(th) * rs).astype(int), 0, 199)
        ys = np.clip((a.y + np.sin(th) * rs).astype(int), 0, 119)
        coupled = rs * a.factor[ys, xs]
        ins = coupled < need
        if ins.any():
            worst = max(worst, float(rs[len(rs) - 1 - int(np.argmax(ins[::-1]))]))
print(f"max outermost felt reach over 90 aims x 180 bearings: {worst:.3f} cells")
