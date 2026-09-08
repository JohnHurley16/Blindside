import sys, time
sys.path.insert(0, r"C:/Users/jackh/documents/programming/Blindside")
import numpy as np
from phase1 import tuning as T
from phase1.match.sim import Sim
from phase1.view.shock_lobe import ShockLobe

sim = Sim(7, stage=True)
while sim.t < 341.0 and not sim.over:
    sim.step()
frame = sim.stage()
lobe = ShockLobe(None, frame.ancient, frame.grid)
aim = frame.ancient.bearing_deg

t0 = time.perf_counter()
n = 200
for i in range(n):
    lobe._curves.clear()
    lobe._contour(1.0, aim + i * 1e-6)
print(f"_contour, cold (20 bisections over 180 rays): {(time.perf_counter()-t0)/n*1000:.3f} ms")

lobe._curves.clear()
lobe._contour(1.0, aim)
t0 = time.perf_counter()
for _ in range(n):
    lobe._contour(1.0, aim)
print(f"_contour, cached:                              {(time.perf_counter()-t0)/n*1000:.4f} ms")

t0 = time.perf_counter()
for _ in range(50):
    ShockLobe(None, frame.ancient, frame.grid)
print(f"ShockLobe.__init__ (once a match):              {(time.perf_counter()-t0)/50*1000:.2f} ms")
