"""The drawn contour against the model's own, at every aim the match uses.

The drawn curve comes out of `ShockLobe._contour`, which is the renderer's only source
for it. The reference is `Ancient.coupling_at`'s own closed form -- checked point by
point against `coupling_at` itself first, so it is the model rather than a second
approximation of it -- scanned at 0.002 cells, ten times finer than the drawn table,
and then bisected to 1e-9 so the reported error is not limited by the reference.

Both take the OUTERMOST crossing. Coupling is not monotone in radius: the medium factor
is a per-cell lookup, so a ray grazing the flooded passage leaves the field and re-enters
it. Measured here, taking the FIRST crossing instead disagrees with the outermost on 7 to
14 of 180 bearings by up to 12.5 cells -- it clips the tongue up the water, which is the
one thing the felt curve exists to show.

36 bearings is what was asked for; all 180 drawn rays are also checked, because 36 of 180
could miss a bearing that crosses water.
"""
import math
import sys

sys.path.insert(0, r"C:/Users/jackh/documents/programming/Blindside")

import numpy as np

from phase1 import tuning as T
from phase1.match.sim import Sim
from phase1.view.shock_lobe import BEARINGS, ShockLobe

STEP = 0.002


def make_ref(ancient):
    F = ancient.factor
    rs = np.arange(0.01, 40.0, STEP)
    rows, cols = F.shape

    def coupled(theta, r):
        x = min(max(int(ancient.x + math.cos(theta) * r), 0), cols - 1)
        y = min(max(int(ancient.y + math.sin(theta) * r), 0), rows - 1)
        return r * float(F[y, x])

    def ref(theta, aim, level):
        g = (T.ANCIENT_LOBE_FLOOR + (1 - T.ANCIENT_LOBE_FLOOR)
             * math.cos(theta - math.radians(aim)) ** 2)
        need = T.ANCIENT_RADIUS * math.sqrt(g / level)
        xs = np.clip((ancient.x + math.cos(theta) * rs).astype(np.int32), 0, cols - 1)
        ys = np.clip((ancient.y + math.sin(theta) * rs).astype(np.int32), 0, rows - 1)
        ins = rs * F[ys, xs] < need
        if not ins.any():
            return 0.0
        i = len(rs) - 1 - int(np.argmax(ins[::-1]))
        if i == len(rs) - 1:
            return 40.0
        lo, hi = float(rs[i]), float(rs[i + 1])
        for _ in range(50):
            mid = 0.5 * (lo + hi)
            lo, hi = (mid, hi) if coupled(theta, mid) < need else (lo, mid)
        return 0.5 * (lo + hi)

    return ref


sim = Sim(7, stage=True)
ancient = sim._world.ancient
ref = make_ref(ancient)

for theta in (0.3, 1.7, 2.6, 4.4):
    for r in (3.0, 9.5, 18.2, 26.7):
        px, py = ancient.x + math.cos(theta) * r, ancient.y + math.sin(theta) * r
        g = (T.ANCIENT_LOBE_FLOOR + (1 - T.ANCIENT_LOBE_FLOOR)
             * math.cos(theta - math.radians(256.0)) ** 2)
        mine = g * (T.ANCIENT_RADIUS / (r * ancient.factor[int(py), int(px)])) ** 2
        assert abs(mine - ancient.coupling_at(px, py, 341.0)) < 1e-12
print("the reference is coupling_at, to 1e-12, at 16 probe points\n")
print(f"{'firing':>8} {'aim':>7}   {'curve':<7} {'max err, 36 bearings':>21} "
      f"{'max err, all 180':>18}  rays over 0.05")

axis_flank = {}
for firing_t in (41.0, 116.0, 191.0, 266.0, 341.0, 416.0):
    while sim.t < firing_t and not sim.over:
        sim.step()
    frame = sim.stage()
    lobe = ShockLobe(None, frame.ancient, frame.grid)
    aim = frame.ancient.bearing_deg
    for level, name in ((1.0, "lethal"), (T.ANCIENT_FELT_COUPLING, "felt")):
        drawn = lobe._contour(level, aim)
        e36 = e180 = 0.0
        bad = []
        for k in range(BEARINGS):
            err = abs(float(drawn[k]) - ref(2 * math.pi * k / BEARINGS, aim, level))
            e180 = max(e180, err)
            if err > 0.05:
                bad.append((k, round(err, 3)))
            if k % 5 == 0:
                e36 = max(e36, err)
        print(f"{firing_t:8.0f} {aim:7.1f}   {name:<7} {e36:21.5f} {e180:18.5f}"
              f"  {bad if bad else 'none'}")
        axis = int(round((aim % 360.0) / 360.0 * BEARINGS)) % BEARINGS
        axis_flank.setdefault(name, []).append(
            (float(drawn[axis]), float(drawn[(axis + BEARINGS // 4) % BEARINGS])))

print()
for name, rows in axis_flank.items():
    print(f"  {name:<7} drawn on-axis {[f'{a:.4f}' for a, _ in rows]}")
    print(f"  {name:<7} drawn flank   {[f'{b:.4f}' for _, b in rows]}")
