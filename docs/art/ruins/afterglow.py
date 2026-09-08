"""Does a decaying residual make a dark cave legible? And how many fixed marks
does a viewer see down a drive?

Two measurements, both against the real 200x120 grid in phase1/truth/cave.py.

  1. AFTERGLOW. The agent walks the long route with a lamp of range R and cone FOV.
     A lit cell charges to I = min(1, (2/d)^2) and then decays with time constant TAU.
     Report the fraction of open cells above a visibility floor, both over the whole
     cave and inside the CAMERA_CLOSE_CELLS = 40 frame the director actually parks on.

  2. MARKS. Self-luminous survey marks every SPACING cells along every passage
     centreline and round every chamber wall. From a random walkable cell, how many
     are in line of sight? That is what a long view down a drive is made of.

Run: "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" is not needed --
this is plain numpy.  python docs/art/ruins/afterglow.py
"""
import sys, math
import numpy as np
sys.path.insert(0, r"C:/Users/jackh/documents/programming/Blindside")
from phase1.truth import cave as C
from phase1 import tuning as T

G = C.GRID; H, W = G.shape
open_mask = G > 0
NOPEN = int(open_mask.sum())
MPC = 0.6   # metres per cell, derived; see the ground-truth pass


def cast(px, py, R, heading=None, fov=360.0, step=0.4):
    """Returns (cells, intensity) for one lamp position: 1/d^2 with occlusion."""
    inten = np.zeros(G.shape, dtype=np.float32)
    nrays = int(max(180, 6 * R * math.pi))
    a0 = 0.0 if heading is None else heading - math.radians(fov) / 2
    span = 2 * math.pi if heading is None else math.radians(fov)
    for i in range(nrays):
        a = a0 + span * i / nrays
        cx, cy = math.cos(a), math.sin(a)
        d = 0.0
        while d < R:
            d += step
            x, y = int(px + cx * d), int(py + cy * d)
            if not (0 <= x < W and 0 <= y < H):
                break
            v = min(1.0, (2.0 / max(d, 0.5)) ** 2)
            if v > inten[y, x]:
                inten[y, x] = v
            if G[y, x] == 0:
                break
    return inten


route = ["S", "C1", "C2", "C3", "ANC", "DB", "C4", "C3", "C2", "C1", "S"]
pts = [(C.CHAMBERS[n][0], C.CHAMBERS[n][1]) for n in route]
path = []
for a, b in zip(pts, pts[1:]):
    n = max(1, int(math.hypot(b[0] - a[0], b[1] - a[1]) / 2.0))
    for i in range(n):
        t = i / n
        path.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
DT = 2.0 / T.AGENT_SPEED          # 2 cells of travel per sample
print(f"route: {len(path)} samples, dt={DT:.2f}s, total {len(path)*DT:.0f}s "
      f"({len(path)*DT/T.MATCH_SECONDS*100:.0f}% of an 8-min match)\n")

FLOOR_FAINT, FLOOR_READ = 0.02, 0.10
HALF = T.CAMERA_CLOSE_CELLS / 2   # the close frame is 40 cells across

print("AFTERGLOW  lamp R=10 cells (6.0 m), 60 deg cone")
print(f"{'tau':>6} {'t=60s':>22} {'t=180s':>22} {'t=300s':>22} {'t=395s':>22}")
print(f"{'':>6} " + " ".join(f"{'cave% / frame%':>22}" for _ in range(4)))
for tau in (0.0, 30.0, 90.0, 240.0, 1e9):
    res = np.zeros(G.shape, dtype=np.float32)
    k = 0.0 if tau <= 0 else math.exp(-DT / tau)
    marks = {}
    for i, (px, py) in enumerate(path):
        nx, ny = path[min(i + 1, len(path) - 1)]
        h = math.atan2(ny - py, nx - px) if (nx, ny) != (px, py) else 0.0
        res *= k
        np.maximum(res, cast(int(px), int(py), 10.0, heading=h, fov=60.0), out=res)
        t = (i + 1) * DT
        for probe in (60, 180, 300, 395):
            if probe not in marks and t >= probe:
                x0, x1 = int(px - HALF), int(px + HALF)
                y0, y1 = int(py - HALF), int(py + HALF)
                x0, y0 = max(0, x0), max(0, y0)
                sub_o = open_mask[y0:y1, x0:x1]
                sub_r = res[y0:y1, x0:x1]
                n_sub = max(1, int(sub_o.sum()))
                marks[probe] = (
                    float((res[open_mask] >= FLOOR_FAINT).mean() * 100),
                    float(((sub_r >= FLOOR_FAINT) & sub_o).sum() / n_sub * 100),
                    float(((sub_r >= FLOOR_READ) & sub_o).sum() / n_sub * 100))
    label = "none" if tau <= 0 else ("inf" if tau > 1e8 else f"{tau:.0f}s")
    cells = " ".join(f"{marks[p][0]:8.1f} /{marks[p][1]:7.1f} " for p in (60, 180, 300, 395))
    print(f"{label:>6} {cells}")
print(f"\n  (left number: % of the whole open cave above {FLOOR_FAINT} residual;"
      f"\n   right number: % of the open cells inside the 40-cell close frame)\n")

# ---- 2. how many fixed marks are in sight ------------------------------------------
def los(ax, ay, bx, by, step=0.5):
    d = math.hypot(bx - ax, by - ay)
    n = int(d / step) + 1
    for i in range(1, n):
        f = i / n
        x, y = int(ax + (bx - ax) * f), int(ay + (by - ay) * f)
        if not (0 <= x < W and 0 <= y < H) or G[y, x] == 0:
            return False
    return d


for SPACING in (4, 8, 16):
    marks = []
    for a, b, width, flooded in C.PASSAGES:
        ax, ay, _ = C.CHAMBERS[a]; bx, by, _ = C.CHAMBERS[b]
        n = max(1, int(math.hypot(bx - ax, by - ay) / SPACING))
        for i in range(n + 1):
            f = i / n
            x, y = ax + (bx - ax) * f, ay + (by - ay) * f
            if 0 <= int(x) < W and 0 <= int(y) < H and G[int(y), int(x)] > 0:
                marks.append((x, y))
    rng = np.random.default_rng(11)
    ys, xs = np.nonzero(G == 1)
    idx = rng.choice(len(xs), 150, replace=False)
    counts, dists = [], []
    for j in idx:
        px, py = float(xs[j]), float(ys[j])
        c = 0
        for (mx, my) in marks:
            d = los(px, py, mx, my)
            if d:
                c += 1
                dists.append(d)
        counts.append(c)
    counts = np.array(counts)
    print(f"marks every {SPACING:>2} cells ({SPACING*MPC:.1f} m): {len(marks):3d} placed | "
          f"in sight from a random cell: mean {counts.mean():4.1f}, median {np.median(counts):3.0f}, "
          f"max {counts.max():3d}, none-in-sight {float((counts==0).mean())*100:4.1f}% | "
          f"furthest visible {max(dists):.0f} cells ({max(dists)*MPC:.0f} m)")
