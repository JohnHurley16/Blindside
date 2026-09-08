import sys, numpy as np, collections
sys.path.insert(0, r"C:/Users/jackh/documents/programming/Blindside")
from phase1.truth import cave as C
G = C.GRID; H, W = G.shape
walk = (G == 1)
sx, sy = (int(v) for v in C.SHAFTS["player"])
dist = -np.ones((H, W), int); dist[sy, sx] = 0
q = collections.deque([(sx, sy)])
while q:
    x, y = q.popleft()
    for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)):
        nx, ny = x+dx, y+dy
        if 0 <= nx < W and 0 <= ny < H and walk[ny,nx] and dist[ny,nx] < 0:
            dist[ny,nx] = dist[y,x]+1; q.append((nx,ny))
d = dist[dist >= 0]
print(f"walkable reached from the player shaft: {d.size} cells")
print(f"graph depth: min {d.min()}  median {int(np.median(d))}  max {d.max()} cells")
for name,(cx,cy,r) in C.CHAMBERS.items():
    v = dist[cy,cx]
    print(f"  {name:5s} r={r:2d}  depth {v:4d} cells  ({v/d.max()*100:5.1f}% of the deepest)")
# how far is each deposit / the machinery
print("\npassage widths in PASSAGES:", sorted({w for _,_,w,_ in C.PASSAGES}))
print("chamber radii:", sorted({r for _,_,r in C.CHAMBERS.values()}))
