# Camera poses, with ground height resolved from the generated heightfield.
# Framings chosen to sit against the Godot frames they are competing with.
import numpy as np, json, os
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "gen")
H = np.load(os.path.join(OUT, "main_h.npy"))
m = json.load(open(os.path.join(OUT, "valley.json")))["main"]
N, E = m["n"], m["extent"]

def g(x, y):
    px = int(np.clip((x/E + 0.5)*(N-1), 0, N-1)); py = int(np.clip((y/E + 0.5)*(N-1), 0, N-1))
    return float(H[py, px])

CAMS = [
    # name                       x     y    eye  yaw   pitch  fov   note
    ("u01_valley_open",        900, -150,  2.0, 180,   -1.0,  62,  "against v10_trailer_open"),
    ("u02_far_wall",           880, -420,  2.0,  95,    9.0,  46,  "town + trimline at ~1.1 km"),
    ("u03_ground",             905, -120,  1.6, 203,  -14.0,  64,  "against k05_route_behind"),
    ("u04_peaks",              900, -200,  2.0, 150,   13.0,  22,  "alpenglow, telephoto"),
    ("u05_headwall",           700, -100,  2.0,  14,    6.0,  52,  "up-valley to the terminus"),
    ("u06_both_walls",         620,  330,  2.4, 196,    1.0,  75,  "both walls, wide"),
]
out = []
for (nm, x, y, eye, yaw, pitch, fov, note) in CAMS:
    z = g(x, y)
    out.append(dict(name=nm, x=x, y=y, z=z+eye, yaw=yaw, pitch=pitch, fov=fov,
                    ground=z, note=note))
json.dump(out, open(os.path.join(OUT, "cams.json"), "w"), indent=1)
for c in out:
    print("%-18s ground %7.1f m" % (c["name"], c["ground"]))
