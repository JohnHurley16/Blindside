"""The machine's own view, rendered: the point cloud as oriented discs, the truth cave it was
measured off, and the two drawn together (ART-DIRECTION 8.1-8.3; SPECTATOR-DISPLAY 6.4, 6.7).

  blender -b -P docs/art/vision/found/_probes/cloud_scene.py -- --data <npz> --shot <name> --out <abs>.png

Data comes from cloud_dump.py (phase1, seed 7). Two frames are drawn in ONE world:
  truth   the cave grid extruded to rock at 0.6 m/cell, 4.4 m to the crown, displaced, lit
          only by the real machine's lamp.                            "Truth is rendered."
  belief  every point of the agent's map as a 44 mm disc facing back along the ray it came
          from, emission only, shadowless, unlit, at the coordinates the agent BELIEVES.
          Plus the floor decal where count > 0, the hollow ghost at the believed pose, its
          2-sigma ellipse, the believed trail, the beacons it recorded.   "Belief is drawn."
The two never overlap in brightness and never agree in shape. The shared datum is z = 0.

Shots
  cloud_director    belief only, the display's 72 deg, orthographic, on black
  cloud_low         belief only, a low orbit: the discs read as banks, the rug as a rug
  cloud_macro       belief only, close: hits not dots, each disc facing its sensor
  cloud_drift       belief only, wide, late in the match: the map before and after fixes,
                    sheets that were never re-registered
  gap_clear         CLEAR-exposed truth with the cloud at full strength over it, the tether
  both              truth at ~35 %, cloud additive -- the replay's default
  belief_only       the same camera, the cloud on black -- the live default
  truth_only        the same camera, the photographic register
  reveal            the 8:00 reveal in 3D: the true wall outline (WARM_DIM) over the built map
  percep_truth      first person at 0.5 m, what is actually in front of it
  percep_both       first person: the pool, the rug of discs, black
  percep_belief     first person: the discs and nothing else
"""
import argparse
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import numpy as np  # noqa: E402
import bpy  # noqa: E402
import bmesh  # noqa: E402
from mathutils import Vector, Euler, Matrix  # noqa: E402

import found_common as F  # noqa: E402
from found_common import G, E  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--data", required=True)
ap.add_argument("--shot", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--samples", type=int, default=40)
ap.add_argument("--res", default="960x600")
ap.add_argument("--radius", type=float, default=16.0, help="metres of truth cave built around the machine")
ap.add_argument("--disc", type=float, default=0.022, help="disc radius, m (44 mm across)")
ap.add_argument("--cloud", type=float, default=1.0, help="cloud emission multiplier")
ap.add_argument("--truth-exposure", type=float, default=1.0, help="scale on every scene light (the 'both' mode dims TRUTH, never belief)")
ap.add_argument("--ortho", type=float, default=None, help="orthographic width, m, for the top-down / director shots")
ap.add_argument("--centre", default=None, help="cx,cy in CELLS: fixed camera centre for cloud_top / cloud_director")
ap.add_argument("--bg", type=float, default=0.0, help="world grey for a CLEAR variant of a belief-only shot (0 = black)")
ap.add_argument("--wall-h", type=float, default=4.4, help="truth wall height, m (a cut-away uses less)")
A = ap.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
RES = tuple(int(v) for v in A.res.split("x"))
S = A.shot
D = np.load(A.data)
CELL = float(D["grid_cell"])
WALL_H = A.wall_h
LOOK = "AgX - Medium High Contrast"

truth_pose = D["truth_pose"]
belief_pose = D["belief_pose"]
T_NOW = float(D["t"])


def m(v):
    """cells -> metres, (x, y) or (x, y, z)."""
    return tuple(float(c) * CELL for c in v)


def tp():
    return Vector((truth_pose[0] * CELL, truth_pose[1] * CELL, 0.0))


def bp():
    return Vector((belief_pose[0] * CELL, belief_pose[1] * CELL, 0.0))


# =====================================================================================
# TRUTH: the cave grid, extruded and displaced. Only cells within --radius of the machine.
# =====================================================================================
def build_truth(centre, radius, rock):
    grid = D["grid"]
    H, W = grid.shape
    cx, cy = centre.x / CELL, centre.y / CELL
    r = radius / CELL
    x0, x1 = max(0, int(cx - r)), min(W - 1, int(cx + r) + 1)
    y0, y1 = max(0, int(cy - r)), min(H - 1, int(cy + r) + 1)
    bm = bmesh.new()
    col = G.new_collection("TRUTH")

    def wall(ax, ay, bx, by):
        v = [bm.verts.new((ax * CELL, ay * CELL, 0.0)), bm.verts.new((bx * CELL, by * CELL, 0.0)),
             bm.verts.new((bx * CELL, by * CELL, WALL_H)), bm.verts.new((ax * CELL, ay * CELL, WALL_H))]
        bm.faces.new(v)

    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            if grid[y, x] == 0:
                continue
            if (x - cx) ** 2 + (y - cy) ** 2 > r * r:
                continue
            # a wall quad on every edge that meets rock (or the edge of the world)
            if x == 0 or grid[y, x - 1] == 0:
                wall(x, y, x, y + 1)
            if x == W - 1 or grid[y, x + 1] == 0:
                wall(x + 1, y + 1, x + 1, y)
            if y == 0 or grid[y - 1, x] == 0:
                wall(x + 1, y, x, y)
            if y == H - 1 or grid[y + 1, x] == 0:
                wall(x, y + 1, x + 1, y + 1)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    for f in bm.faces:
        f.smooth = True
    walls = G._mesh_object("truth_walls", bm, col=col, smooth=True)
    sub = walls.modifiers.new("sub", "SUBSURF")
    sub.subdivision_type = "SIMPLE"
    sub.levels = sub.render_levels = 3
    E._displace(walls, 1.1, 0.42, depth=6)
    E._displace(walls, 0.28, 0.12, depth=5)
    G.set_material(walls, rock)
    # floor and crown: one plane each, displaced, world-space rock so seams do not show
    fl = G.plane("truth_floor", radius * 2.4, (centre.x, centre.y, 0.0), col=col, subdiv=80)
    E._displace(fl, 0.7, 0.14, depth=5, mid=0.55)
    fl.data.shade_smooth()
    G.set_material(fl, rock)
    cr = G.plane("truth_crown", radius * 2.4, (centre.x, centre.y, WALL_H), col=col, subdiv=60)
    E._displace(cr, 1.0, 0.6, depth=5, mid=0.5)
    cr.data.shade_smooth()
    G.set_material(cr, rock)
    return col


def truth_outline(centre, radius, mat, z=0.02, r_tube=0.03):
    """The reveal's wall outline: thin emissive tubes along every truth wall edge at z = 0."""
    grid = D["grid"]
    H, W = grid.shape
    cx, cy = centre.x / CELL, centre.y / CELL
    r = radius / CELL
    col = G.new_collection("OUTLINE")
    bm = bmesh.new()
    segs = []
    for y in range(max(0, int(cy - r)), min(H - 1, int(cy + r) + 1) + 1):
        for x in range(max(0, int(cx - r)), min(W - 1, int(cx + r) + 1) + 1):
            if grid[y, x] == 0 or (x - cx) ** 2 + (y - cy) ** 2 > r * r:
                continue
            if x == 0 or grid[y, x - 1] == 0:
                segs.append(((x, y), (x, y + 1)))
            if x == W - 1 or grid[y, x + 1] == 0:
                segs.append(((x + 1, y), (x + 1, y + 1)))
            if y == 0 or grid[y - 1, x] == 0:
                segs.append(((x, y), (x + 1, y)))
            if y == H - 1 or grid[y + 1, x] == 0:
                segs.append(((x, y + 1), (x + 1, y + 1)))
    for (a, b) in segs:
        a3 = Vector((a[0] * CELL, a[1] * CELL, z))
        b3 = Vector((b[0] * CELL, b[1] * CELL, z))
        d = b3 - a3
        n1 = Vector((0, 0, 1)).cross(d).normalized() * r_tube
        n2 = Vector((0, 0, r_tube))
        vs = [bm.verts.new(a3 + n1), bm.verts.new(a3 - n1), bm.verts.new(b3 - n1), bm.verts.new(b3 + n1)]
        bm.faces.new(vs)
        vs2 = [bm.verts.new(a3 + n2), bm.verts.new(a3 - n2), bm.verts.new(b3 - n2), bm.verts.new(b3 + n2)]
        bm.faces.new(vs2)
    o = G._mesh_object("truth_outline", bm, col=col, smooth=False)
    G.set_material(o, mat)
    return col


# =====================================================================================
# BELIEF: discs, decal, ghost, ellipse, trail, beacons. Emission only. Never lit.
# =====================================================================================
def belief_material(name, strength):
    """Emission = per-corner colour attribute 'col' (class colour x alpha) x strength.
    Shadowless and unlit: an emission shader with no BSDF is exactly that in Cycles."""
    m, nt, out = F._new(name)
    n, L = nt.nodes, nt.links.new
    attr = n.new("ShaderNodeAttribute")
    attr.attribute_name = "col"
    em = n.new("ShaderNodeEmission")
    em.inputs["Strength"].default_value = strength
    L(attr.outputs["Color"], em.inputs["Color"])
    L(em.outputs[0], out.inputs[0])
    m.blend_method = "BLEND"
    return m


def build_cloud(centre=None, radius=None, strength=0.05, disc_r=0.022, age=True):
    """One mesh: an 8-gon per point, facing back along its return ray. Sensed at its
    scattered z (0 .. 2.2 cells = 1.32 m: ankle to knee); walked at z = 0, facing up.
    Alpha = confidence (SPECTATOR 6.4: 0.35 + 0.5 q sensed, 0.2 walked), times age."""
    xyz = D["cloud_xyz"]
    conf = D["cloud_conf"]
    src = D["cloud_source"]
    tt = D["cloud_t"]
    org = D["cloud_origin"]
    n = len(xyz)
    col = G.new_collection("CLOUD")
    bm = bmesh.new()
    layer = bm.loops.layers.color.new("col")
    keep = 0
    for i in range(n):
        p = Vector((xyz[i, 0] * CELL, xyz[i, 1] * CELL, xyz[i, 2] * CELL))
        if centre is not None and (p - centre).length > radius:
            continue
        walked = src[i] == 1
        if walked:
            normal = Vector((0, 0, 1))
            rgb = F.WALKED
            alpha = 0.55          # the display's 0.2 is invisible on a 960 px board; flagged
            rr = disc_r * 0.9
            p.z = 0.004
        else:
            o = Vector((org[i, 0] * CELL, org[i, 1] * CELL, 0.5))     # the sensor at 0.5 m
            normal = (o - p)
            if normal.length < 1e-3:
                normal = Vector((0, 0, 1))
            normal.normalize()
            rgb = F.SENSED
            alpha = 0.35 + 0.5 * float(conf[i])
            rr = disc_r * (0.8 + 0.4 * float(conf[i]))
        if age and T_NOW > 0:
            a = (T_NOW - float(tt[i])) / T_NOW
            alpha *= 0.35 + 0.65 * (1.0 - a)
        # an 8-gon in the plane perpendicular to `normal`
        u = normal.cross(Vector((0, 0, 1)) if abs(normal.z) < 0.9 else Vector((1, 0, 0))).normalized()
        v = normal.cross(u).normalized()
        verts = [bm.verts.new(p + (u * math.cos(k * math.pi / 4) + v * math.sin(k * math.pi / 4)) * rr) for k in range(8)]
        f = bm.faces.new(verts)
        for lp in f.loops:
            lp[layer] = (rgb[0] * alpha, rgb[1] * alpha, rgb[2] * alpha, 1.0)
        keep += 1
    o = G._mesh_object("cloud_discs", bm, col=col, smooth=False)
    G.set_material(o, belief_material("cloud_m", strength))
    print(f"cloud: {keep} of {n} discs")
    return col


def build_decal(centre=None, radius=None, strength=0.05):
    """The mapped silhouette: a dark-cyan wash on the floor where count > 0, in 2-cell bins."""
    occ = D["occupied"]
    off = float(D["grid_offset"][0])
    bin_c = float(D["grid_offset"][2])
    col = G.new_collection("DECAL")
    bm = bmesh.new()
    layer = bm.loops.layers.color.new("col")
    ix, iy = np.nonzero(occ)
    for bx, by in zip(ix, iy):
        x0 = (bx * bin_c - off) * CELL
        y0 = (by * bin_c - off) * CELL
        c = Vector((x0 + bin_c * CELL / 2, y0 + bin_c * CELL / 2, 0.0))
        if centre is not None and (c - centre).length > radius:
            continue
        s = bin_c * CELL * 1.0
        z = 0.002
        vs = [bm.verts.new((c.x - s / 2, c.y - s / 2, z)), bm.verts.new((c.x + s / 2, c.y - s / 2, z)),
              bm.verts.new((c.x + s / 2, c.y + s / 2, z)), bm.verts.new((c.x - s / 2, c.y + s / 2, z))]
        f = bm.faces.new(vs)
        for lp in f.loops:
            lp[layer] = (F.WALKED[0] * 0.6, F.WALKED[1] * 0.6, F.WALKED[2] * 0.6, 1.0)
    o = G._mesh_object("decal", bm, col=col, smooth=False)
    G.set_material(o, belief_material("decal_m", strength))
    return col


def tube(name, pts, r, mat, col):
    o = G.tube_along(name, pts, r, verts=6, col=col)
    G.set_material(o, mat)
    return o


def build_ghost(strength=0.6):
    """The hollow ghost at the believed pose, at the machine's REAL size (the display's 2x
    licence does not transfer): a wire outline of a 0.58 x 0.21 m hull with a nose, and its
    2-sigma ellipse on the floor. GHOST. Hollow is a belief about the thing."""
    col = G.new_collection("GHOST")
    gm = F.emission("ghost_m", F.GHOST, strength)
    x, y, th = belief_pose
    o = Vector((x * CELL, y * CELL, 0.0))
    R = Matrix.Rotation(float(th), 3, "Z")
    L, W = 0.58, 0.21
    pts = [(L / 2 + 0.06, 0), (L * 0.35, W / 2), (-L / 2, W / 2), (-L / 2, -W / 2), (L * 0.35, -W / 2), (L / 2 + 0.06, 0)]
    pts3 = [o + R @ Vector((px, py, 0.05)) for px, py in pts]
    tube("ghost_hull", pts3, 0.006, gm, col)
    # posts down to the floor at the corners, so it reads as a thing standing here
    for px, py in pts[1:5]:
        p = o + R @ Vector((px, py, 0))
        tube("ghost_post", [p + Vector((0, 0, 0.005)), p + Vector((0, 0, 0.05))], 0.004, gm, col)
    a, b, ang = D["belief_ellipse"]
    ell = [o + Vector((math.cos(ang) * 2 * a * CELL * math.cos(t) - math.sin(ang) * 2 * b * CELL * math.sin(t),
                       math.sin(ang) * 2 * a * CELL * math.cos(t) + math.cos(ang) * 2 * b * CELL * math.sin(t), 0.02))
           for t in np.linspace(0, 2 * math.pi, 64)]
    tube("ghost_ellipse", ell, 0.006, F.emission("ell_m", F.GHOST, strength * 0.5), col)
    return col


def build_trail(strength=0.15):
    col = G.new_collection("TRAIL")
    tr = D["belief_trail"]
    pts = [Vector((p[0] * CELL, p[1] * CELL, 0.012)) for p in tr]
    if len(pts) > 1:
        tube("belief_trail", pts, 0.005, F.emission("trail_m", F.COOL_DIM, strength), col)
    return col


def build_beacons(strength=0.6):
    """Ghost diamonds on 0.6 m stalks where the agent RECORDED its beacons."""
    col = G.new_collection("BEACONS_BELIEVED")
    gm = F.emission("bcn_ghost_m", F.GHOST, strength)
    for i, (x, y) in enumerate(D["beacons_believed"]):
        o = Vector((x * CELL, y * CELL, 0.0))
        tube(f"stalk{i}", [o, o + Vector((0, 0, 0.6))], 0.004, gm, col)
        top = o + Vector((0, 0, 0.6))
        d = 0.06
        for a, b in (((d, 0, 0), (0, 0, d)), ((0, 0, d), (-d, 0, 0)), ((-d, 0, 0), (0, 0, -d)), ((0, 0, -d), (d, 0, 0)),
                     ((0, d, 0), (0, 0, d)), ((0, 0, d), (0, -d, 0)), ((0, -d, 0), (0, 0, -d)), ((0, 0, -d), (0, d, 0))):
            tube(f"dia{i}", [top + Vector(a), top + Vector(b)], 0.004, gm, col)
    return col


def build_tether(strength=0.5):
    """A rope above the rock from the true machine to where it believes it is. Colour by
    how wrong (READOUT_RAMP_CELLS 3 / 12 / 30: tertiary, primary, LIE, KILL)."""
    col = G.new_collection("TETHER")
    err = (tp() - bp()).length / CELL
    rgb = (0.337, 0.384, 0.435) if err < 3 else ((0.949, 0.961, 0.976) if err < 12 else (F.LIE if err < 30 else (1.0, 0.231, 0.188)))
    a = tp() + Vector((0, 0, 0.45))
    b = bp() + Vector((0, 0, 0.45))
    mid = (a + b) / 2 + Vector((0, 0, 0.25))
    pts = [a.lerp(mid, t) * (1 - t) + mid.lerp(b, t) * t for t in np.linspace(0, 1, 16)]
    tube("tether", pts, 0.006, F.emission("tether_m", rgb, strength), col)
    return col


def cell_open(p):
    grid = D["grid"]
    H, W = grid.shape
    x, y = int(p.x / CELL), int(p.y / CELL)
    return 0 <= x < W and 0 <= y < H and grid[y, x] != 0


def open_cam(candidates, target, clearance=0.45):
    """The first candidate that stands in open truth cells (with clearance) and sees the
    target through open cells. A camera inside rock renders black -- the t=138 trio did."""
    for c in candidates:
        if not all(cell_open(c + Vector((dx, dy, 0))) for dx in (-clearance, 0, clearance)
                   for dy in (-clearance, 0, clearance)):
            continue
        d = target - c
        n = max(2, int(d.length / 0.25))
        if all(cell_open(c + d * (k / n)) for k in range(n + 1)):
            print("open_cam:", tuple(round(v, 2) for v in c))
            return c
    print("open_cam: no candidate is open; using the first")
    return candidates[0]


def grey_world(bg):
    """A CLEAR variant for a belief-only frame: the discs on a dark grey instead of black,
    so the geometry of the drawing can be seen. Not the game."""
    if bg <= 0:
        return
    w = bpy.context.scene.world
    for nd in w.node_tree.nodes:
        if nd.type == "BACKGROUND":
            nd.inputs["Color"].default_value = (bg, bg, bg, 1)
            nd.inputs["Strength"].default_value = 1.0


# =====================================================================================
# scene assembly
# =====================================================================================
def scale_lights(k):
    for o in bpy.data.objects:
        if o.type == "LIGHT":
            o.data.energy *= k


def real_machine(lamp=600.0):
    x, y, th = truth_pose
    b = F.agent("player", at=(float(x) * CELL, float(y) * CELL, 0.0), yaw_deg=math.degrees(float(th)),
                lamp=lamp, aim_down=9.0, name="TRUE")
    return b


def rock():
    return E.rock("truth_rock", albedo_lo=0.045, albedo_hi=0.30, warm=1.0, wet=0.35, fracture_scale=7.0)


F.fresh()
centre = tp()
heading = Vector((math.cos(float(truth_pose[2])), math.sin(float(truth_pose[2])), 0))
left = Vector((-heading.y, heading.x, 0))
cloud_k = A.cloud

if S == "cloud_director":
    # belief only, on black, from the display's own attitude (TurntableCamera elevation 72,
    # orthographic). SENSED and WALKED, two classes and nothing else; the floor decal under.
    F.insitu(fog=0.0)
    build_cloud(strength=2.2 * cloud_k)
    build_decal(strength=1.2 * cloud_k)
    build_ghost(1.0)
    build_trail(0.18)
    build_beacons(1.0)
    xyz = D["cloud_xyz"]
    src = D["cloud_source"]
    sens = xyz[src != 1]
    c = bp()
    if len(sens):
        cs = Vector((float(np.median(sens[:, 0])) * CELL, float(np.median(sens[:, 1])) * CELL, 0.0))
        c = (c + cs) / 2
    if A.centre:
        cx, cy = (float(v) for v in A.centre.split(","))
        c = Vector((cx * CELL, cy * CELL, 0.0))
    az = math.radians(-90)
    grey_world(A.bg)
    F.camera(c + Vector((math.cos(az) * 6, math.sin(az) * 6, 18.5)), c, ortho=A.ortho or 24.0)

elif S == "cloud_top":
    # belief only, straight down, orthographic, at a FIXED --centre / --ortho, so two times
    # of one match can be compared from the same camera: the drift pair.
    F.insitu(fog=0.0)
    build_cloud(strength=2.2 * cloud_k, disc_r=A.disc)
    build_decal(strength=1.0 * cloud_k)
    build_ghost(1.2)
    build_trail(0.3)
    build_beacons(1.2)
    cx, cy = (float(v) for v in A.centre.split(",")) if A.centre else (float(belief_pose[0]), float(belief_pose[1]))
    c = Vector((cx * CELL, cy * CELL, 0.0))
    grey_world(A.bg)
    F.camera(c + Vector((0.0, -0.01, 40.0)), c, ortho=A.ortho or 30.0)

elif S == "cloud_low":
    # belief only, a low orbit near the believed pose: banks of discs where the walls were
    # pinged, a rug of walked points on the floor, the ghost standing on it.
    F.insitu(fog=0.0)
    build_cloud(strength=2.2 * cloud_k)
    build_decal(strength=1.2 * cloud_k)
    build_ghost(1.0)
    build_trail(0.18)
    build_beacons(1.0)
    c = bp()
    F.camera(c - heading * 5.5 + left * 3.0 + Vector((0, 0, 2.2)), c + heading * 2.0 + Vector((0, 0, 0.3)), focal=35)

elif S == "cloud_macro":
    # belief only, close: a bank of returns is a SURFACE from any angle because each disc
    # faces the sensor that measured it. Hits, not dots. Never smoothed into a mesh. The
    # camera finds the densest sensed bank in the whole map and stands 1.4 m off it, on the
    # side the sensor stood; --bg puts a dark grey behind it so the discs' tilt can be read.
    F.insitu(fog=0.0)
    build_cloud(strength=2.2 * cloud_k, disc_r=A.disc, age=False)
    build_decal(strength=1.0 * cloud_k)
    build_ghost(1.0)
    build_trail(0.3)
    xyz = D["cloud_xyz"]
    src = D["cloud_source"]
    org = D["cloud_origin"]
    sel = src != 1
    pts = xyz[sel][:, :2] * CELL
    dd = np.hypot(pts[:, 0][:, None] - pts[:, 0][None, :], pts[:, 1][:, None] - pts[:, 1][None, :])
    k = int(np.argmax((dd < 0.9).sum(axis=1)))
    cl = dd[k] < 1.2
    tgt = Vector((float(pts[cl, 0].mean()), float(pts[cl, 1].mean()), float((xyz[sel][cl, 2] * CELL).mean())))
    o = org[sel][cl].mean(axis=0) * CELL
    side = Vector((float(o[0]), float(o[1]), 0.0)) - Vector((tgt.x, tgt.y, 0.0))
    side.normalize()
    grey_world(A.bg)
    F.camera(Vector((tgt.x, tgt.y, 0.0)) + side * 1.5 + Vector((0, 0, 0.75)), tgt, focal=45)

elif S == "cloud_drift":
    # belief only, wide, late: fixes moved everything since the epoch and nothing before it.
    # The old corridor and the new corridor for the same passage, both drawn, no annotation.
    F.insitu(fog=0.0)
    build_cloud(strength=2.2 * cloud_k, disc_r=A.disc)
    build_decal(strength=1.2 * cloud_k)
    build_ghost(1.0)
    build_trail(0.2)
    build_beacons(1.0)
    xyz = D["cloud_xyz"]
    lo = np.percentile(xyz[:, :2], 2, axis=0) * CELL
    hi = np.percentile(xyz[:, :2], 98, axis=0) * CELL
    c = Vector((float(lo[0] + hi[0]) / 2, float(lo[1] + hi[1]) / 2, 0.0))
    span = max(float(hi[0] - lo[0]), float(hi[1] - lo[1]) * 1.6) * 1.12
    F.camera(c + Vector((0.0, -0.01, 40.0)), c, ortho=max(30.0, span))

elif S == "gap_clear":
    # a teaching image: the truth passage at CLEAR exposure, the cloud over it at full
    # strength, the tether from the machine to its ghost. Two registers, one frame.
    F.clear_rig(key_from=(centre.x - 3.0, centre.y - 6.0, 7.0), aim=(centre.x, centre.y, 0.6), key_w=2800.0, key_size=5.0, fill_w=300.0)
    rk = rock()
    build_truth(centre, A.radius, rk)
    bpy.data.objects["truth_crown"].hide_render = True       # cut away for the studio view
    build_cloud(centre, A.radius, strength=1.6 * cloud_k)
    build_decal(centre, A.radius, strength=1.2 * cloud_k)
    build_ghost(2.0)
    build_trail(0.4)
    build_beacons(2.0)
    build_tether(2.0)
    real_machine(lamp=0.0)
    mid = (tp() + bp()) / 2
    # from above the (cut-down) walls, 50 deg down, so the canyon floor, the machine, the
    # ghost and the rope all read; the first version stood at wall height and saw a wall
    F.camera(mid - heading * 3.5 + left * 5.5 + Vector((0, 0, 8.0)), mid + heading * 0.6 + Vector((0, 0, 0.2)), focal=32)

elif S in ("both", "belief_only", "truth_only"):
    # the three modes from one camera behind the real machine, favouring the framing that
    # puts the machine between the viewer and its own pool.
    F.insitu(fog=0.012 if S != "belief_only" else 0.0)
    if S != "belief_only":
        build_truth(centre, A.radius, rock())
        real_machine(lamp=600.0)
        if S == "both":
            scale_lights(0.35)          # truth turned DOWN; belief never is
    else:
        real_machine(lamp=0.0)
        # a quiet machine is invisible on the belief side: only the ghost is drawn
        for o in bpy.data.collections["TRUE"].all_objects:
            o.hide_render = True
    if S != "truth_only":
        k = 2.2 if S == "belief_only" else 1.4
        build_cloud(centre, A.radius + 6, strength=k * cloud_k)
        build_decal(centre, A.radius + 6, strength=(0.5 if S == "belief_only" else 0.18) * k * cloud_k)
        build_ghost(1.0)
        build_trail(0.15)
        build_beacons(1.0)
        if S == "both":
            build_tether(0.8)
    tgt = centre + heading * 2.2 + Vector((0, 0, 0.2))
    cands = [centre - heading * 3.2 + left * k * 1.3 + Vector((0, 0, 1.25)) for k in (1, -1, 0.5, -0.5, 0)]
    cands += [centre - heading * 2.4 + left * k * 1.0 + Vector((0, 0, 1.1)) for k in (1, -1, 0)]
    cands += [centre - heading * 4.2 + left * k * 0.8 + Vector((0, 0, 1.4)) for k in (1, -1, 0)]
    F.camera(open_cam(cands, tgt), tgt, focal=32)

elif S == "reveal":
    # the 8:00 reveal in three dimensions: the true wall outline drawn in WARM_DIM over the
    # built map, from the director's attitude, wide. Truth is a line drawing here on
    # purpose -- the display draws it that way, and a rendered cave would drown the map.
    F.insitu(fog=0.0)
    xyz = D["cloud_xyz"]
    c = Vector((float(np.median(xyz[:, 0])) * CELL, float(np.median(xyz[:, 1])) * CELL, 0.0))
    c = (c + tp()) / 2
    truth_outline(c, 70.0, F.emission("outline_m", F.WARM_DIM, 1.2), z=0.03, r_tube=0.05)
    build_cloud(strength=2.2 * cloud_k, disc_r=A.disc)
    build_decal(strength=1.2 * cloud_k)
    build_ghost(1.2)
    build_trail(0.25)
    build_beacons(1.2)
    build_tether(1.2)
    b = F.agent("player", at=(float(truth_pose[0]) * CELL, float(truth_pose[1]) * CELL, 0.0),
                yaw_deg=math.degrees(float(truth_pose[2])), lamp=0.0, name="TRUE", emissive=6.0)
    span = max(float(np.ptp(xyz[:, 0])), abs(tp().x / CELL - float(np.median(xyz[:, 0]))) * 2.2) * CELL
    F.camera(c + Vector((0.0, -12.0, 60.0)), c, ortho=max(40.0, span * 1.2))

elif S in ("percep_truth", "percep_both", "percep_belief"):
    # enter-agent-perception: first person at 0.5 m eye height, the cloud, a lamp pool, and
    # nothing else. percep_truth is what is actually in front of it (not the game).
    F.insitu(fog=0.012 if S != "percep_belief" else 0.0)
    b = real_machine(lamp=600.0 if S != "percep_belief" else 0.0)
    if S != "percep_belief":
        build_truth(centre, A.radius, rock())
        if S == "percep_both":
            scale_lights(0.4)
    for o in bpy.data.collections["TRUE"].all_objects:
        o.hide_render = True          # the camera is inside the head
    if S != "percep_truth":
        k = 2.2 if S == "percep_belief" else 1.4
        build_cloud(centre, A.radius + 6, strength=k * cloud_k)
        build_decal(centre, A.radius + 6, strength=(0.5 if S == "percep_belief" else 0.18) * k * cloud_k)
        build_trail(0.15)
        build_beacons(1.0)
    eye = centre + heading * 0.36 + Vector((0, 0, 0.50))
    F.camera(eye, eye + heading * 3.0 + Vector((0, 0, -0.35)), focal=24)
    if b.lamp is not None and S != "percep_belief":
        # the lamp rides the head; the head is hidden, the lamp is not
        b.lamp.hide_render = False

if bpy.context.scene.camera is None:
    raise SystemExit(f"unknown shot {S}")

if A.truth_exposure != 1.0:
    scale_lights(A.truth_exposure)
F.render(A.out, samples=A.samples, res=RES, look=LOOK)
