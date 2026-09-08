import sys, math, numpy as np
sys.path.insert(0, r"C:/Users/jackh/documents/programming/Blindside")
from phase1.truth import cave as C
from phase1 import tuning as T

G = C.GRID
H, W = G.shape
open_mask = G > 0
dry = (G == 1); wet = (G == 2)
print(f"grid {W}x{H} = {W*H} cells; open {open_mask.sum()} ({open_mask.mean()*100:.1f}%), "
      f"dry {dry.sum()} ({dry.mean()*100:.1f}%), flooded {wet.sum()} ({wet.mean()*100:.1f}%)")

def visible(px, py, R, heading=None, fov=360.0, step=0.4):
    """Cells with unoccluded line of sight within R and inside the cone."""
    seen = np.zeros_like(open_mask)
    nrays = int(max(180, 6*R*math.pi))
    a0 = 0.0 if heading is None else heading - math.radians(fov)/2
    span = 2*math.pi if heading is None else math.radians(fov)
    for i in range(nrays):
        a = a0 + span*i/nrays
        cx, cy = math.cos(a), math.sin(a)
        d = 0.0
        while d < R:
            d += step
            x, y = int(px + cx*d), int(py + cy*d)
            if not (0 <= x < W and 0 <= y < H): break
            if G[y, x] == 0:
                seen[y, x] = True   # you see the wall face you light
                break
            seen[y, x] = True
    return seen

# sample positions: chamber centres + points along passages, all walkable
rng = np.random.default_rng(7)
ys, xs = np.nonzero(dry)
idx = rng.choice(len(xs), 400, replace=False)
samples = list(zip(xs[idx], ys[idx]))

for R in (6, 10, 12, 20, 30):
    fracs_omni, fracs_cone = [], []
    for (px, py) in samples[:120]:
        s = visible(px, py, R)
        fracs_omni.append(s.sum())
        h = rng.uniform(0, 2*math.pi)
        s2 = visible(px, py, R, heading=h, fov=60.0)
        fracs_cone.append(s2.sum())
    o = np.mean(fracs_omni); c = np.mean(fracs_cone)
    print(f"R={R:>2} cells | omni: {o:7.1f} cells lit = {o/open_mask.sum()*100:5.2f}% of open, "
          f"{o/(W*H)*100:5.3f}% of grid | 60-deg cone: {c:6.1f} = {c/open_mask.sum()*100:5.2f}% of open")

# how much of the cave does one 30-cell sonar ping see, for comparison
s = visible(82, 68, 30, heading=0.0, fov=T.SONAR_ARC_DEG)
print(f"one sonar ping from C2 centre (30 cells, {T.SONAR_ARC_DEG} deg): {s.sum()} cells "
      f"= {s.sum()/open_mask.sum()*100:.2f}% of open")

# route length: how far does an agent walk in a match
print(f"match {T.MATCH_SECONDS}s at {T.AGENT_SPEED} cells/s = {T.MATCH_SECONDS*T.AGENT_SPEED:.0f} cells travelled")
