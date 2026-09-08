"""How far can you actually SEE in this cave?

An art direction that says "at a hundred metres the cave looks like X" is worthless if
no sightline in the cave is a hundred metres long. This measures the real distribution
of unobstructed sightlines on phase1's grid, in cells and at the derived 0.6 m/cell, and
the sky factor of every open cell (how much of the hemisphere is rock).

Also measures the two things the depth axis needs: graph distance from the player shaft,
and how much of the cave is within sight of the two shafts and the Assayer -- i.e. how
much of the cave is ever lit by a world source rather than by a machine.
"""
import os
import sys
import numpy as np

sys.path.insert(0, r"C:/Users/jackh/documents/programming/Blindside")
from phase1.truth import cave as C
from phase1 import tuning as T

MPC = 0.6                      # metres per cell, derived; see the evidence pass
G = C.GRID if hasattr(C, "GRID") else None
if G is None:
    G = [v for k, v in vars(C).items() if isinstance(v, np.ndarray) and v.shape == (C.H, C.W)][0]

OPEN = G > 0
WALK = G == 1
FLOOD = G == 2
print(f"grid {C.W}x{C.H}  open {OPEN.sum()} ({OPEN.mean():.1%})  dry {WALK.sum()}  flooded {FLOOD.sum()}")


def ray(x, y, dx, dy, limit=400.0):
    """March until rock. Returns distance in cells."""
    d = 0.0
    while d < limit:
        d += 0.5
        ix, iy = int(x + dx * d), int(y + dy * d)
        if ix < 0 or iy < 0 or ix >= C.W or iy >= C.H or not OPEN[iy, ix]:
            return d
    return limit


rng = np.random.default_rng(11)
cells = np.argwhere(OPEN)
pick = cells[rng.choice(len(cells), 900, replace=False)]
NDIR = 64
ang = np.arange(NDIR) * 2 * np.pi / NDIR

dists = []
skyish = []
for (y, x) in pick:
    ds = [ray(x + 0.5, y + 0.5, np.cos(t), np.sin(t)) for t in ang]
    dists.extend(ds)
    skyish.append(max(ds))
dists = np.array(dists)
skyish = np.array(skyish)

print("\n--- sightline length, all directions from 900 random open cells ---")
for p in (50, 75, 90, 95, 99, 100):
    v = np.percentile(dists, p)
    print(f"  p{p:<4} {v:7.1f} cells   {v*MPC:6.1f} m")
print(f"  mean  {dists.mean():7.1f} cells   {dists.mean()*MPC:6.1f} m")

print("\n--- the LONGEST view available from each cell (best direction) ---")
for p in (10, 50, 90, 99, 100):
    v = np.percentile(skyish, p)
    print(f"  p{p:<4} {v:7.1f} cells   {v*MPC:6.1f} m")

print("\n--- how much of the frame is rock: sightlines under N cells ---")
for n in (5, 10, 20, 30, 50):
    print(f"  under {n:>3} cells ({n*MPC:4.1f} m): {(dists < n).mean():5.1%} of all directions")

# ---- what a world source can reach: line of sight from the fixed furniture -----------
def visible_from(px, py, limit=400.0):
    seen = np.zeros_like(OPEN)
    for (y, x) in np.argwhere(OPEN):
        dx, dy = x + 0.5 - px, y + 0.5 - py
        d = np.hypot(dx, dy)
        if d > limit:
            continue
        n = int(d * 2)
        t = np.linspace(0, 1, max(n, 2))
        xs = (px + dx * t).astype(int)
        ys = (py + dy * t).astype(int)
        if OPEN[ys, xs].all():
            seen[y, x] = True
    return seen


srcs = {
    "player shaft": C.SHAFTS["player"],
    "rival shaft": C.SHAFTS["rival"],
    "the Assayer": C.ANCIENT_POS,
}
print("\n--- line of sight from the fixed world sources (no range limit) ---")
tot = np.zeros_like(OPEN)
for name, (px, py) in srcs.items():
    v = visible_from(px, py)
    tot |= v
    print(f"  {name:<14} sees {v.sum():5d} open cells = {v.sum()/OPEN.sum():5.1%} of the cave")
print(f"  {'union':<14} sees {tot.sum():5d} open cells = {tot.sum()/OPEN.sum():5.1%} of the cave")
print("  -> everything else is lit only by whatever a machine carries in.")

# ---- depth: graph distance from the player shaft ------------------------------------
from collections import deque
sx, sy = (int(v) for v in C.SHAFTS["player"])
dist = -np.ones((C.H, C.W), np.int32)
dist[sy, sx] = 0
q = deque([(sx, sy)])
while q:
    x, y = q.popleft()
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nx, ny = x + dx, y + dy
        if 0 <= nx < C.W and 0 <= ny < C.H and OPEN[ny, nx] and dist[ny, nx] < 0:
            dist[ny, nx] = dist[y, x] + 1
            q.append((nx, ny))
r = dist[dist >= 0]
print(f"\n--- depth (BFS cells from the player shaft) ---")
print(f"  reached {len(r)}  min {r.min()}  median {int(np.median(r))}  max {r.max()}"
      f"   = {r.max()*MPC:.0f} m of graph depth")
for nm, (cx, cy, _) in C.CHAMBERS.items():
    print(f"  {nm:<6}{dist[int(cy), int(cx)]:>5} cells  {dist[int(cy), int(cx)]/r.max():>6.0%} deep"
          f"   {dist[int(cy), int(cx)]*MPC:>6.0f} m")
