import sys, math, numpy as np
sys.path.insert(0, r"C:/Users/jackh/documents/programming/Blindside")
from phase1.truth import cave as C
from phase1 import tuning as T
G = C.GRID; H, W = G.shape
open_mask = G > 0; NOPEN = open_mask.sum()

def visible(px, py, R, heading=None, fov=360.0, step=0.4):
    seen = np.zeros_like(open_mask)
    nrays = int(max(180, 6*R*math.pi))
    a0 = 0.0 if heading is None else heading - math.radians(fov)/2
    span = 2*math.pi if heading is None else math.radians(fov)
    for i in range(nrays):
        a = a0 + span*i/nrays
        cx, cy = math.cos(a), math.sin(a); d = 0.0
        while d < R:
            d += step
            x, y = int(px + cx*d), int(py + cy*d)
            if not (0 <= x < W and 0 <= y < H): break
            if G[y, x] == 0: seen[y, x] = True; break
            seen[y, x] = True
    return seen

# walk the rival's long route, sampling every 2 cells of travel
route = ["S","C1","C2","C3","ANC","DB","C4","C3","C2","C1","S"]
pts = [(C.CHAMBERS[n][0], C.CHAMBERS[n][1]) for n in route]
path = []
for a, b in zip(pts, pts[1:]):
    n = int(math.hypot(b[0]-a[0], b[1]-a[1]) / 2.0)
    for i in range(n):
        t = i/max(n,1)
        path.append((a[0]+(b[0]-a[0])*t, a[1]+(b[1]-a[1])*t))
total_cells = sum(math.hypot(b[0]-a[0], b[1]-a[1]) for a,b in zip(pts, pts[1:]))
print(f"route {' -> '.join(route)}: {total_cells:.0f} cells, "
      f"{total_cells/T.AGENT_SPEED:.0f}s at {T.AGENT_SPEED} cells/s "
      f"({total_cells/T.AGENT_SPEED/T.MATCH_SECONDS*100:.0f}% of an 8-min match)")

for R, fov in ((10, 60.0), (10, 360.0), (20, 60.0)):
    acc = np.zeros_like(open_mask)
    for i,(px,py) in enumerate(path):
        nx, ny = path[min(i+1, len(path)-1)]
        h = math.atan2(ny-py, nx-px) if (nx,ny)!=(px,py) else 0.0
        acc |= visible(int(px), int(py), R, heading=(None if fov>=360 else h), fov=fov)
    print(f"cumulative over the whole route, R={R} fov={fov:.0f}: {acc.sum()} cells "
          f"= {acc.sum()/NOPEN*100:.1f}% of the open cave EVER lit")
