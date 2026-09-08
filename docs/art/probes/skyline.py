"""Can you see the machine coming?

THE-MACHINERY 2.1 claims the mast is the one thing that breaks the skyline: 11 cells
against CAVE_WALL_HEIGHT_CELLS = 8, "so you can see which way it is pointing from the
next chamber". That claim has never been checked against the actual cave, and the whole
"a hazard is identifiable before it fires" requirement rests on it.

This does the 2.5D version of the line-of-sight test: rock cells are opaque slabs 8 cells
tall, the viewer's eye is at 0.6 cells (an agent's head), and the target is a point at
height h on the Assayer. A cell can see the target if the straight line clears every
intervening slab top.

Reported for h = 11.0 (mast top), 9.0 (the boom, the part that points), and 1.2 (the
footing -- i.e. plain ground-level line of sight, the control).
"""
import sys
import numpy as np

sys.path.insert(0, r"C:/Users/jackh/documents/programming/Blindside")
from phase1.truth import cave as C
from phase1 import tuning as T

MPC = 0.6
WALL = T.CAVE_WALL_HEIGHT_CELLS          # 8.0
EYE = 0.6
G = [v for k, v in vars(C).items() if isinstance(v, np.ndarray) and v.shape == (C.H, C.W)][0]
OPEN = G > 0
AX, AY = C.ANCIENT_POS
print(f"wall height {WALL} cells ({WALL*MPC:.1f} m)   mast {T.ANCIENT_MAST_CELLS} cells "
      f"({T.ANCIENT_MAST_CELLS*MPC:.1f} m)   boom z {9.0} cells ({9.0*MPC:.1f} m)")
print(f"open cells {OPEN.sum()}\n")


def sees(px, py, h_target, h_eye=EYE):
    dx, dy = AX - px, AY - py
    d = float(np.hypot(dx, dy))
    if d < 1e-6:
        return True, 0.0
    n = max(int(d * 2), 2)
    t = np.linspace(0.0, 1.0, n)[1:-1]
    xs = (px + dx * t).astype(int)
    ys = (py + dy * t).astype(int)
    rock = ~OPEN[ys, xs]
    if not rock.any():
        return True, d
    # ray height at each sample, in cells
    zs = h_eye + (h_target - h_eye) * t
    return bool((zs[rock] > WALL).all()), d


for h, label in ((1.2, "footing  (ground LOS)"), (9.0, "the boom  z=9"), (11.0, "mast top  z=11")):
    seen, dists = 0, []
    for (y, x) in np.argwhere(OPEN):
        ok, d = sees(x + 0.5, y + 0.5, h)
        if ok:
            seen += 1
            dists.append(d)
    dists = np.array(dists) if dists else np.array([0.0])
    print(f"{label:<24} visible from {seen:5d} cells = {seen/OPEN.sum():5.1%} of the cave"
          f"   median range {np.median(dists):5.1f} cells ({np.median(dists)*MPC:4.1f} m)"
          f"   max {dists.max():5.1f} cells ({dists.max()*MPC:4.1f} m)")

# how much does the skyline buy over ground LOS?
g = set()
m = set()
for (y, x) in np.argwhere(OPEN):
    if sees(x + 0.5, y + 0.5, 1.2)[0]:
        g.add((x, y))
    if sees(x + 0.5, y + 0.5, 11.0)[0]:
        m.add((x, y))
extra = m - g
print(f"\ncells that can see the MAST but not the machine's body: {len(extra)}"
      f" = {len(extra)/max(len(OPEN.nonzero()[0]),1):.1%} of the cave")
if extra:
    ds = np.array([np.hypot(x + .5 - AX, y + .5 - AY) for (x, y) in extra])
    print(f"  their range to it: median {np.median(ds):.1f} cells ({np.median(ds)*MPC:.1f} m), "
          f"max {ds.max():.1f} cells ({ds.max()*MPC:.1f} m)")
    print(f"  the lethal radius is {T.ANCIENT_RADIUS} cells ({T.ANCIENT_RADIUS*MPC:.1f} m); "
          f"{(ds > T.ANCIENT_RADIUS).mean():.0%} of them are outside it -- i.e. warned in time")

# Chamber-by-chamber: which named rooms get the warning
print("\nby chamber:")
for nm, (cx, cy, r) in C.CHAMBERS.items():
    body = sees(cx + .5, cy + .5, 1.2)[0]
    mast = sees(cx + .5, cy + .5, 11.0)[0]
    d = np.hypot(cx - AX, cy - AY)
    print(f"  {nm:<6} {d*MPC:6.1f} m   body {'Y' if body else '.'}   mast {'Y' if mast else '.'}")
