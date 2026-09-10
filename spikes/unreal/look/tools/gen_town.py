# Terraced town on the far (+Y) wall. THE-ICE 7.3: oldest and highest, walking downhill,
# straddling the trimline at +310 m. Emits transforms; Unreal instances boxes on them.
import numpy as np, json, os, math
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "gen")
H = np.load(os.path.join(OUT, "main_h.npy"))
meta = json.load(open(os.path.join(OUT, "valley.json")))
m = meta["main"]
N = m["n"]; EXT = m["extent"]; DS = m["ds"]

def hgt(x, y):
    """bilinear sample, world metres -> metres"""
    px = (x/EXT + 0.5)*(N-1); py = (y/EXT + 0.5)*(N-1)
    px = np.clip(px, 0, N-2); py = np.clip(py, 0, N-2)
    i = px.astype(int); j = py.astype(int)
    fx = px-i; fy = py-j
    return ((H[j,i]*(1-fx)+H[j,i+1]*fx)*(1-fy) + (H[j+1,i]*(1-fx)+H[j+1,i+1]*fx)*fy)

rng = np.random.default_rng(31)
buildings = []   # x,y,z,yaw,sx,sy,sz,age(0 new .. 1 old),lit
roads = []

# The town sits on the +Y wall, up-valley of the camera, so it reads at ~900 m.
X0, X1 = -700.0, 1000.0

def find_y(x, target_z, ylo=500.0, yhi=2400.0):
    ys = np.linspace(ylo, yhi, 900)
    zs = hgt(np.full_like(ys, x), ys)
    k = np.argmin(np.abs(zs - target_z))
    if abs(zs[k]-target_z) > 25.0: return None
    return float(ys[k])

TERRACES = 22
for ti in range(TERRACES):
    f = ti/(TERRACES-1.0)
    z = 90.0 + f*(520.0-90.0)                 # THE-ICE 7.2: foot +90, oldest quarter +520
    age = f                                   # higher is older
    # a terrace is a contour segment; older quarters are shorter and denser
    seg_len = 420.0*(1.0-0.55*age) + 90.0
    cx = X0 + (X1-X0)*(0.30 + 0.40*rng.random()) + 240.0*math.sin(ti*1.7)
    n_b = int(seg_len/ (11.0 + 5.0*age))
    step = seg_len/max(n_b,1)
    for bi in range(n_b):
        x = cx - seg_len*0.5 + bi*step + rng.normal(0, 0.8)
        y = find_y(x, z)
        if y is None: continue
        # local slope -> the plinth
        y2 = find_y(x, z+8.0)
        if y2 is None: continue
        # footprint: older = smaller, tighter, more varied
        sx = (6.0 + 8.0*(1.0-age))*(0.75+0.5*rng.random())
        sy = (6.0 + 5.0*(1.0-age))*(0.75+0.5*rng.random())
        sz = (5.0 + 9.0*(1.0-age))*(0.7+0.6*rng.random())
        plinth = sz*(0.32 + 0.20*rng.random())
        yaw = math.degrees(math.atan2(z+8.0-z, max(abs(y2-y),1e-3))) * 0.0
        # face out across the valley: -Y
        yaw = 180.0 + rng.normal(0, 5.0)
        buildings.append(dict(x=x, y=y, z=z-plinth, yaw=yaw, sx=sx, sy=sy,
                              sz=sz+plinth, age=float(age),
                              lit=float(rng.random() < (0.55 - 0.2*age))))
    # switchback road segment
    for k in range(14):
        t = k/13.0
        rx = cx - seg_len*0.62 + seg_len*1.24*t
        ry = find_y(rx, z-11.0)
        if ry is None: continue
        roads.append(dict(x=rx, y=ry, z=z-11.0, sx=seg_len*1.24/14.0*1.15, sy=9.0, sz=1.2,
                          yaw=0.0))

# one tower on the top terrace: a skyline needs a vertical (VALLEY.md guess 10)
ty = find_y(X0+ (X1-X0)*0.5, 520.0)
if ty:
    buildings.append(dict(x=X0+(X1-X0)*0.5, y=ty, z=520.0-6.0, yaw=180.0,
                          sx=9.0, sy=9.0, sz=58.0, age=1.0, lit=1.0))

json.dump(dict(buildings=buildings, roads=roads), open(os.path.join(OUT,"town.json"),"w"))
print("buildings %d  roads %d" % (len(buildings), len(roads)))
