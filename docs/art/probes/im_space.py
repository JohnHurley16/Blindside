"""How much surface is within reach of a lamp, and how big the spaces actually are.

The lighting answer depends on whether this cave is mostly narrow (a lamp always has a
wall to bounce off) or mostly open (it does not). Nothing in the repo measures that.
"""
import sys
from collections import deque
import numpy as np

sys.path.insert(0, r"C:/Users/jackh/documents/programming/Blindside")
from phase1.truth import cave as C
from phase1 import tuning as T

g = C.GRID if hasattr(C, "GRID") else None
if g is None:
    for nm in dir(C):
        v = getattr(C, nm)
        if isinstance(v, np.ndarray) and v.shape == (C.W, C.H) or (isinstance(v, np.ndarray) and v.ndim == 2):
            g = v
            print("grid found as", nm, v.shape)
            break
print("grid shape", g.shape, "values", np.unique(g))

open_mask = g > 0
dry = g == 1
flood = g == 2
print("open %d  dry %d  flooded %d  of %d  (%.1f%% open, %.1f%% of open is water)" %
      (open_mask.sum(), dry.sum(), flood.sum(), g.size,
       100 * open_mask.sum() / g.size, 100 * flood.sum() / max(1, open_mask.sum())))

# --- distance to nearest rock, per open cell (chebyshev BFS from rock) -------------
INF = 10 ** 9
dist = np.full(g.shape, INF, dtype=np.int32)
q = deque()
W, H = g.shape
for x in range(W):
    for y in range(H):
        if not open_mask[x, y]:
            dist[x, y] = 0
            q.append((x, y))
while q:
    x, y = q.popleft()
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            nx, ny = x + dx, y + dy
            if 0 <= nx < W and 0 <= ny < H and dist[nx, ny] > dist[x, y] + 1:
                dist[nx, ny] = dist[x, y] + 1
                q.append((nx, ny))
d = dist[open_mask]
print("\ndistance from any open cell to the nearest rock, in cells:")
for p in (10, 25, 50, 75, 90, 100):
    print("  p%-3d %5.1f cells = %4.1f m" % (p, np.percentile(d, p), np.percentile(d, p) * 0.6))
for k in (2, 3, 4, 5, 6, 8, 10):
    print("  within %2d cells (%4.1f m) of rock: %5.1f%%" % (k, k * 0.6, 100 * (d <= k).mean()))

# --- graph depth from the player shaft, and where the water is --------------------
sy, sx = (int(v) for v in reversed(C.SHAFTS["player"]))
depth = np.full(g.shape, -1, dtype=np.int32)
depth[sy, sx] = 0
q = deque([(sy, sx)])
while q:
    x, y = q.popleft()
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nx, ny = x + dx, y + dy
        if 0 <= nx < W and 0 <= ny < H and open_mask[nx, ny] and depth[nx, ny] < 0:
            depth[nx, ny] = depth[x, y] + 1
            q.append((nx, ny))
reach = depth >= 0
dv = depth[reach]
print("\nreachable open cells %d, graph depth 0..%d, median %d" % (reach.sum(), dv.max(), int(np.median(dv))))
print("chamber depths:")
for nm, (cx, cy, r) in C.CHAMBERS.items():
    print("   %-5s depth %4d  = %3d%%   radius %2d cells = %4.1f m across" %
          (nm, depth[cy, cx], round(100 * depth[cy, cx] / dv.max()), r, 2 * r * 0.6))

# where does the water sit, by depth quartile?
qs = np.percentile(dv, [25, 50, 75])
for i, (lo, hi) in enumerate(zip([0, qs[0], qs[1], qs[2]], [qs[0], qs[1], qs[2], dv.max() + 1])):
    sel = reach & (depth >= lo) & (depth < hi)
    if sel.sum() == 0:
        continue
    print("  depth quartile %d (%3d-%3d cells): %5d cells, %4.1f%% flooded, mean clearance %.1f cells" %
          (i + 1, lo, hi, sel.sum(), 100 * flood[sel].mean(), dist[sel].mean()))

# --- how much wall surface is there? (open cells adjacent to rock) ----------------
edge = open_mask & (dist == 1)
print("\nopen cells touching rock: %d (%.0f%% of open) -- that is the wall the lamp lights" %
      (edge.sum(), 100 * edge.sum() / open_mask.sum()))
