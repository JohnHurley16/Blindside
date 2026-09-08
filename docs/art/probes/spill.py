"""Light goes round corners; silhouettes do not.

skyline.py showed the Assayer's body is visible from 18.1% of the cave and its 6.6 m mast
buys exactly zero extra cells, because a uniform 4.8 m wall occludes everything behind it
from a ground-level viewer. So a hazard cannot be seen coming. Can it be *lit* coming?

This measures the spill: cells with no line of sight to the source, but within N cells
(along the open graph) of a cell that does have one -- i.e. ground that is lit by bounce
off a lit wall, which is what a viewer coming down a passage actually sees first.
"""
import sys
from collections import deque
import numpy as np
sys.path.insert(0, r"C:/Users/jackh/documents/programming/Blindside")
from phase1.truth import cave as C
from phase1 import tuning as T

MPC = 0.6
G = [v for k, v in vars(C).items() if isinstance(v, np.ndarray) and v.shape == (C.H, C.W)][0]
OPEN = G > 0

def los_set(px, py):
    s = np.zeros_like(OPEN)
    for (y, x) in np.argwhere(OPEN):
        dx, dy = x + .5 - px, y + .5 - py
        d = np.hypot(dx, dy)
        n = max(int(d * 2), 2)
        t = np.linspace(0, 1, n)
        if OPEN[(py + dy * t).astype(int), (px + dx * t).astype(int)].all():
            s[y, x] = True
    return s

for name, (px, py) in (("the Assayer", C.ANCIENT_POS),
                       ("player shaft", C.SHAFTS["player"]),
                       ("rival shaft", C.SHAFTS["rival"])):
    seed = los_set(px, py)
    dist = np.where(seed, 0, -1).astype(np.int32)
    q = deque((int(x), int(y)) for (y, x) in np.argwhere(seed))
    while q:
        x, y = q.popleft()
        for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)):
            nx, ny = x+dx, y+dy
            if 0 <= nx < C.W and 0 <= ny < C.H and OPEN[ny,nx] and dist[ny,nx] < 0:
                dist[ny,nx] = dist[y,x] + 1
                q.append((nx,ny))
    print(f"\n{name}: direct LOS {seed.sum()} cells = {seed.sum()/OPEN.sum():.1%}")
    for n in (3, 6, 10, 16, 25):
        v = ((dist >= 0) & (dist <= n)).sum()
        print(f"  within {n:>2} cells ({n*MPC:4.1f} m) of lit ground: {v:5d} = {v/OPEN.sum():5.1%} of the cave")
