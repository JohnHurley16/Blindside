"""The ruins, dressed, lit only by sources that exist in the fiction.

Builds a WORKED DRIVE (cut passage: horseshoe profile, half-barrel shot-hole scars,
gutter, rail, timber sockets, bolt line, self-luminous survey marks) or THE ASSAYER
at true scale, and stands the agent in it.

Light sources, all diegetic, selectable:
  --afterglow S   the ore's own phosphorescence, emission added to the rock  (0 = off)
  --marks 0|1     the prior industry's self-luminous survey marks
  --lamp E        the agent's optical work lamp, watts (0 = quiet loadout)
  --winch E       the Assayer's winch and bearing, hot under load, watts

Run:
  blender.exe -b -P docs/art/ruins/ruins_probe.py -- --scene drive --out x.png
"""
import sys, os, math, random, argparse
sys.path.insert(0, r"C:/Users/jackh/documents/programming/Blindside")
import bpy, bmesh
from mathutils import Vector
from agent_model import params as P, geometry as GEO, materials as M, render as R
from agent_model.build import build_agent
from agent_model.motion import Mover, script
from agent_model.run import SKINS

MPC = 0.6                                   # metres per cell (derived)
AFTERGLOW_RGB = (1.00, 0.72, 0.42)          # the ore's phosphorescence: warm, never cool
MARK_RGB      = (1.00, 0.80, 0.55)          # same phosphor, painted on a plate
WINCH_RGB     = (1.00, 0.42, 0.13)          # iron hot under load


# ---- materials ---------------------------------------------------------------------
def _out(m):
    nt = m.node_tree
    return nt, next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")


def ruin_rock(afterglow=0.0, name="ruin_rock"):
    """wet_rock plus the ore's afterglow: a patchy emission, warm, very low."""
    m = M.wet_rock(name)
    if afterglow <= 0:
        return m
    nt, out = _out(m)
    n = nt.nodes
    principled = next(x for x in n if x.type == "BSDF_PRINCIPLED")
    patch = n.new("ShaderNodeTexNoise"); patch.inputs["Scale"].default_value = 5.5
    patch.inputs["Detail"].default_value = 7.0
    ramp = n.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.40
    ramp.color_ramp.elements[1].position = 0.70
    # the charge lives where a passing lamp put it: low on the walls, not on the roof
    geo = n.new("ShaderNodeNewGeometry")
    sep = n.new("ShaderNodeSeparateXYZ")
    hgt = n.new("ShaderNodeMapRange")
    hgt.inputs["From Min"].default_value = 2.3
    hgt.inputs["From Max"].default_value = 0.4
    hgt.inputs["To Min"].default_value = 0.12
    hgt.inputs["To Max"].default_value = 1.0
    hmul = n.new("ShaderNodeMath"); hmul.operation = "MULTIPLY"
    em = n.new("ShaderNodeEmission"); em.inputs["Color"].default_value = (*AFTERGLOW_RGB, 1)
    mul = n.new("ShaderNodeMath"); mul.operation = "MULTIPLY"
    mul.inputs[1].default_value = afterglow
    add = n.new("ShaderNodeAddShader")
    L = nt.links.new
    L(patch.outputs["Fac"], ramp.inputs["Fac"])
    L(geo.outputs["Position"], sep.inputs["Vector"])
    L(sep.outputs["Z"], hgt.inputs["Value"])
    L(ramp.outputs["Color"], hmul.inputs[0])
    L(hgt.outputs["Result"], hmul.inputs[1])
    L(hmul.outputs[0], mul.inputs[0])
    L(mul.outputs[0], em.inputs["Strength"])
    L(principled.outputs[0], add.inputs[0])
    L(em.outputs[0], add.inputs[1])
    L(add.outputs[0], out.inputs["Surface"])
    return m


def cast_iron(name="cast_iron", rust=0.55):
    """Graphitised cast iron: black, soft-surfaced, orange bloom where water runs."""
    m, nt, out = M._new(name)
    n = nt.nodes
    b = n.new("ShaderNodeBsdfPrincipled")
    b.inputs["Metallic"].default_value = 0.25
    tex = n.new("ShaderNodeTexNoise"); tex.inputs["Scale"].default_value = 6.0
    tex.inputs["Detail"].default_value = 9.0
    ramp = n.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.022, 0.021, 0.020, 1)
    ramp.color_ramp.elements[0].position = 0.34
    ramp.color_ramp.elements[1].color = (0.17, 0.075, 0.028, 1)
    ramp.color_ramp.elements[1].position = 0.34 + 0.5 * (1 - rust)
    rough = n.new("ShaderNodeMath"); rough.operation = "MULTIPLY_ADD"
    rough.inputs[1].default_value = -0.18
    rough.inputs[2].default_value = 0.94
    bump = n.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.35
    L = nt.links.new
    L(tex.outputs["Fac"], ramp.inputs["Fac"]); L(ramp.outputs["Color"], b.inputs["Base Color"])
    L(tex.outputs["Fac"], rough.inputs[0]); L(rough.outputs[0], b.inputs["Roughness"])
    L(tex.outputs["Fac"], bump.inputs["Height"]); L(bump.outputs["Normal"], b.inputs["Normal"])
    L(b.outputs[0], out.inputs[0])
    return m


def flowstone(name="flowstone"):
    """Iron-stained calcite: the age clock. Ochre, wet, slightly translucent."""
    m, nt, out = M._new(name)
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    b.inputs["Base Color"].default_value = (0.28, 0.145, 0.055, 1)
    b.inputs["Roughness"].default_value = 0.22
    try:
        b.inputs["Subsurface Weight"].default_value = 0.25
    except KeyError:
        pass
    nt.links.new(b.outputs[0], out.inputs[0])
    return m


def glow(rgb, strength, name="glow"):
    m, nt, out = M._new(name)
    e = nt.nodes.new("ShaderNodeEmission")
    e.inputs["Color"].default_value = (*rgb, 1)
    e.inputs["Strength"].default_value = strength
    nt.links.new(e.outputs[0], out.inputs[0])
    return m


# ---- the worked drive --------------------------------------------------------------
def profile(hw=1.20, leg=1.20, nl=8, na=26):
    """Horseshoe: vertical legs to `leg`, semicircular arch of radius `hw` above.
    2.4 m wide by 2.4 m high = 4 cells by 4 cells."""
    pts = [(hw, leg * k / nl) for k in range(nl + 1)]
    pts += [(hw * math.cos(math.pi * k / na), leg + hw * math.sin(math.pi * k / na))
            for k in range(1, na)]
    pts += [(-hw, leg * (nl - k) / nl) for k in range(nl + 1)]
    return pts


def drive(length=20.0, hw=1.20, leg=1.20, scallop=0.055, round_m=1.6, col=None,
          seed=5, mat=None):
    """One cut drive. The half-barrels left by the drill are the scale cue: a row of
    grooves at the drill spacing, all parallel to the direction of advance."""
    rng = random.Random(seed)
    pts = profile(hw, leg)
    s, norms = [0.0], []
    for i in range(1, len(pts)):
        s.append(s[-1] + math.dist(pts[i], pts[i - 1]))
    for i in range(len(pts)):
        a = pts[max(0, i - 1)]
        b = pts[min(len(pts) - 1, i + 1)]
        t = Vector((b[0] - a[0], b[1] - a[1]))
        t.normalize()
        norms.append(Vector((t.y, -t.x)))          # points into the rock
    hole = 0.34                                    # drill spacing on the perimeter
    nseg = int(length / 0.28)
    phases = {}
    bm = bmesh.new()
    rings = []
    for j in range(nseg + 1):
        x = -length / 2 + length * j / nseg
        rnd = int((x + length / 2) / round_m)       # each round of blasting has its own pattern
        ph = phases.setdefault(rnd, rng.random())
        ring = []
        for i, (py, pz) in enumerate(pts):
            k = 1.0 - abs(math.sin(math.pi * s[i] / hole + ph * 6.28))
            d = (scallop * k
                 + 0.018 * math.sin(x * 3.1 + s[i] * 2.2 + ph * 9)
                 + rng.uniform(-0.008, 0.008))
            n = norms[i]
            ring.append(bm.verts.new((x, py + n.x * d, max(0.005, pz + n.y * d))))
        rings.append(ring)
    for j in range(nseg):
        for i in range(len(pts) - 1):
            bm.faces.new((rings[j][i], rings[j][i + 1], rings[j + 1][i + 1], rings[j + 1][i]))
    o = GEO._mesh_object("drive_walls", bm, col=col, smooth=True)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.normals_make_consistent(inside=True)
    bpy.ops.object.mode_set(mode="OBJECT")
    GEO.set_material(o, mat)
    return o


def drive_floor(length=20.0, hw=1.20, col=None, mat=None, seed=6):
    """Flat trammed floor with the drainage gutter cut down one side."""
    rng = random.Random(seed)
    nx, ny = int(length / 0.18), 26
    bm = bmesh.new()
    grid = []
    for j in range(ny + 1):
        row = []
        y = -hw + 2 * hw * j / ny
        for i in range(nx + 1):
            x = -length / 2 + length * i / nx
            z = rng.uniform(-0.012, 0.012) + 0.02 * math.sin(x * 1.7 + y * 3.0)
            if y < -hw + 0.30:                      # gutter: 300 mm wide, 90 mm deep
                z -= 0.09 * math.sin(math.pi * min(1.0, (y + hw) / 0.30)) ** 0.6
            row.append(bm.verts.new((x, y, z)))
        grid.append(row)
    for j in range(ny):
        for i in range(nx):
            bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
    o = GEO._mesh_object("drive_floor", bm, col=col, smooth=True)
    GEO.set_material(o, mat)
    return o


def drive_furniture(length=20.0, hw=1.20, leg=1.20, col=None, marks=True,
                    mark_strength=6.0, seed=7):
    """Everything the industry bolted in: rail on sleepers at 600 mm gauge, timber
    sockets at 1.2 m, a bolt line at the springing, and the survey marks."""
    rng = random.Random(seed)
    iron = cast_iron("rail_iron", rust=0.75)
    dark = M.bare_metal("socket_dark", tint=(0.04, 0.035, 0.03), rough=0.9)
    stone = flowstone()
    markm = glow(MARK_RGB, mark_strength, "survey_mark")
    gauge = 0.60                                    # 1 cell. The agent walks between the rails
    made = []
    for k in range(int(length / 0.60)):
        x = -length / 2 + 0.3 + k * 0.60
        made.append(GEO.box("sleeper.%d" % k, (0.11, gauge + 0.30, 0.055),
                            loc=(x, 0.15, 0.02), col=col))
    for side in (1, -1):
        made.append(GEO.box("rail.%d" % side, (length - 0.4, 0.035, 0.055),
                            loc=(0, 0.15 + side * gauge / 2, 0.06), col=col))
    for o in made:
        GEO.set_material(o, iron)
    for k in range(int(length / 1.2)):
        x = -length / 2 + 0.6 + k * 1.2
        for side in (1, -1):
            GEO.set_material(GEO.box("socket.%d.%d" % (k, side), (0.16, 0.10, 0.20),
                                     loc=(x, side * (hw - 0.02), leg + 0.10), col=col), dark)
            GEO.set_material(GEO.cyl("bolt.%d.%d" % (k, side), 0.022, 0.022, 0.06,
                                     loc=(x, side * (hw - 0.03), leg - 0.35),
                                     rot=(0, math.pi / 2, 0), verts=8, col=col), iron)
    for k in range(6):
        x = rng.uniform(-length / 2 + 1, length / 2 - 1)
        side = rng.choice((1, -1))
        GEO.set_material(GEO.cyl("flow.%d" % k, 0.02, 0.16, leg + 0.9,
                                 loc=(x, side * (hw - 0.05), (leg + 0.9) / 2),
                                 verts=10, col=col), stone)
    if marks:
        for k in range(int(length / 4.8) + 1):      # every 8 cells: measured, 8.8 in sight
            x = -length / 2 + 1.0 + k * 4.8
            GEO.set_material(GEO.box("mark.%d" % k, (0.012, 0.14, 0.09),
                                     loc=(x, hw - 0.03, 1.40), col=col), markm)
    return col


# ---- the Assayer --------------------------------------------------------------------
def assayer(col=None, aim_deg=35.0, hammer_frac=0.55, winch_w=0.0, at=(0, 0, 0)):
    """THE-MACHINERY.md 2.1, in metres at 0.6 m/cell. Mast 6.6 m, boom 4.2 m,
    hammer ring 1.2 m across, footing 3.1 m across, hub 0.72 m over the floor."""
    iron = cast_iron("assayer_iron", rust=0.45)
    hot = glow(WINCH_RGB, max(0.001, winch_w / 12.0), "winch_hot")
    root = bpy.data.objects.new("ASSAYER", None)
    col.objects.link(root)
    root.location = at
    MAST_H, MAST_F = 11.0 * MPC, 1.6 * MPC
    HUB_Z, HUB_R, FOOT_R = 1.2 * MPC, 1.0 * MPC, 2.6 * MPC
    BOOM_L, BOOM_W, BOOM_Z = 7.0 * MPC, 0.9 * MPC, 9.0 * MPC
    parts = []
    for i in range(3):
        a = math.radians(90 + 120 * i)
        parts.append(GEO.segment("foot.%d" % i,
                                 (math.cos(a) * HUB_R, math.sin(a) * HUB_R, HUB_Z),
                                 (math.cos(a) * FOOT_R, math.sin(a) * FOOT_R, 0.0),
                                 0.075, 0.16, col=col))
        parts.append(GEO.box("pad.%d" % i, (0.48, 0.48, 0.10),
                             loc=(math.cos(a) * FOOT_R, math.sin(a) * FOOT_R, 0.05), col=col))
    parts.append(GEO.cyl("hub", HUB_R * 0.9, HUB_R * 0.75, 0.34,
                         loc=(0, 0, HUB_Z), verts=6, col=col))
    parts.append(GEO.cyl("mast", MAST_F / 2, MAST_F / 2 * 0.86, MAST_H - HUB_Z,
                         loc=(0, 0, HUB_Z + (MAST_H - HUB_Z) / 2), verts=6, col=col))
    for k in range(7):
        parts.append(GEO.cyl("mastrib.%d" % k, MAST_F / 2 * 1.07, MAST_F / 2 * 1.07, 0.05,
                             loc=(0, 0, HUB_Z + 0.35 + k * 0.78), verts=6, col=col))
    a = math.radians(aim_deg)
    ca, sa = math.cos(a), math.sin(a)
    parts.append(GEO.box("boom", (BOOM_L, BOOM_W, 0.22),
                         loc=(ca * BOOM_L / 2, sa * BOOM_L / 2, BOOM_Z), rot=(0, 0, a), col=col))
    for k in range(5):
        f = 0.12 + 0.22 * k
        wdt = (2.4 - 1.2 * f) * MPC
        parts.append(GEO.box("rib.%d" % k, (0.10, wdt, 0.30),
                             loc=(ca * BOOM_L * f, sa * BOOM_L * f, BOOM_Z),
                             rot=(0, 0, a), col=col))
    parts.append(GEO.box("cwt", (2.2 * MPC, 0.7 * MPC, 0.5 * MPC),
                         loc=(-ca * 1.1 * MPC, -sa * 1.1 * MPC, BOOM_Z), rot=(0, 0, a), col=col))
    hz = HUB_Z + 0.4 + hammer_frac * (BOOM_Z - HUB_Z - 1.0)
    parts.append(GEO.cyl("hammer", 1.15 * MPC, 1.15 * MPC, 0.62,
                         loc=(0, 0, hz), verts=6, col=col))
    for i in range(8):
        b = math.radians(45 * i)
        parts.append(GEO.cyl("ring.%d" % i, 0.05, 0.04, 0.16,
                             loc=(math.cos(b) * 3.4 * MPC, math.sin(b) * 3.4 * MPC, 0.08),
                             verts=8, col=col))
    for p in parts:
        GEO.set_material(p, iron)
        p.parent = root
    w = GEO.cyl("winch", MAST_F * 0.62, MAST_F * 0.62, 0.42,
                loc=(0, 0, MAST_H - 0.55), verts=6, col=col)
    GEO.set_material(w, iron)
    w.parent = root
    band = GEO.cyl("winch_band", MAST_F * 0.64, MAST_F * 0.64, 0.10,
                   loc=(0, 0, MAST_H - 0.55), verts=6, col=col)
    GEO.set_material(band, hot)
    band.parent = root
    if winch_w > 0:
        d = bpy.data.lights.new("WINCH", "POINT")
        d.energy = winch_w
        d.color = WINCH_RGB
        d.shadow_soft_size = 0.35
        o = bpy.data.objects.new("WINCH", d)
        col.objects.link(o)
        o.location = (at[0], at[1], at[2] + MAST_H - 0.55)
    return root


# ---- scene ---------------------------------------------------------------------------
ap = argparse.ArgumentParser()
ap.add_argument("--scene", default="drive", choices=("drive", "assayer"))
ap.add_argument("--chassis", default="surveyor")
ap.add_argument("--modules", default=None)
ap.add_argument("--skin", default="team_a")
ap.add_argument("--light", default=None)
ap.add_argument("--afterglow", type=float, default=0.06)
ap.add_argument("--marks", type=int, default=1)
ap.add_argument("--mark-strength", type=float, default=6.0)
ap.add_argument("--lamp", type=float, default=0.0)
ap.add_argument("--winch", type=float, default=0.0)
ap.add_argument("--fog", type=float, default=0.004)
ap.add_argument("--cam", default="168,10,3.4")
ap.add_argument("--move", default="stand 0.2; look 3.0,0.0,0.30 0.4 ride; walk 2.0 0.45 0 trot; stand 0.3")
ap.add_argument("--focal", type=float, default=50.0)
ap.add_argument("--aim-z", type=float, default=None)
ap.add_argument("--samples", type=int, default=64)
ap.add_argument("--res", default="1200x760")
ap.add_argument("--out", required=True)
a = ap.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:])

R.clear_scene()
cfg = P.default_config(a.chassis)
if a.modules is not None:
    cfg.modules = dict(kv.split("=") for kv in a.modules.split(",")) if a.modules else {}
skin = SKINS[a.skin]
if a.light:
    skin.light = tuple(float(v) for v in a.light.split(","))
cfg.skin = skin
built = build_agent(cfg)
mover = Mover(built)
last = script(mover, a.move)

col = GEO.new_collection("RUINS")
rock = ruin_rock(a.afterglow)
if a.scene == "drive":
    drive(length=22.0, col=col, mat=rock)
    drive_floor(length=22.0, col=col, mat=rock)
    drive_furniture(length=22.0, col=col, marks=bool(a.marks), mark_strength=a.mark_strength)
else:
    fl = GEO.plane("stope_floor", 34.0, (0, 0, 0), col=col, subdiv=90)
    d = fl.modifiers.new("disp", "DISPLACE")
    t = bpy.data.textures.new("stope", "CLOUDS")
    t.noise_scale = 2.2
    t.noise_depth = 5
    d.texture = t
    d.strength = 0.34
    d.mid_level = 0.62
    fl.data.shade_smooth()
    GEO.set_material(fl, rock)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=5, radius=13.0, location=(0, 0, 4.0))
    dome = bpy.context.object
    dome.name = "stope_walls"
    dome.scale = (1.0, 1.0, 0.62)
    bpy.ops.object.transform_apply(scale=True)
    dd = dome.modifiers.new("disp", "DISPLACE")
    t2 = bpy.data.textures.new("stope_w", "CLOUDS")
    t2.noise_scale = 2.6
    t2.noise_depth = 6
    dd.texture = t2
    dd.strength = 3.2
    dome.data.shade_smooth()
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.flip_normals()
    bpy.ops.object.mode_set(mode="OBJECT")
    GEO.set_material(dome, rock)
    for c in list(dome.users_collection):
        c.objects.unlink(dome)
    col.objects.link(dome)
    assayer(col=col, aim_deg=205.0, hammer_frac=0.62, winch_w=a.winch, at=(2.9, 1.7, 0.0))

# world: no ambient. The background is the dark itself.
w = bpy.context.scene.world or bpy.data.worlds.new("World")
bpy.context.scene.world = w
w.use_nodes = True
nt = w.node_tree
bg = nt.nodes.get("Background") or nt.nodes.new("ShaderNodeBackground")
bg.inputs["Color"].default_value = (0.0, 0.0, 0.0, 1)
bg.inputs["Strength"].default_value = 0.0
wout = nt.nodes.get("World Output") or nt.nodes.new("ShaderNodeOutputWorld")
nt.links.new(bg.outputs[0], wout.inputs["Surface"])
vol = nt.nodes.new("ShaderNodeVolumeScatter")
vol.inputs["Density"].default_value = a.fog
vol.inputs["Anisotropy"].default_value = 0.45
vol.inputs["Color"].default_value = (0.9, 0.82, 0.7, 1)
nt.links.new(vol.outputs[0], wout.inputs["Volume"])

if built.lamp is not None:
    built.lamp.data.energy = a.lamp
    built.lamp.data.color = (1.0, 0.97, 0.92)      # white. A work lamp is not a team colour

az, el, dist = (float(v) for v in a.cam.split(","))
zc = float(built.arm["hull_center_z"])
frame = max(1, last // 2)
R.camera(built.arm, aim_offset=(0.12, 0, a.aim_z if a.aim_z is not None else zc * 0.95),
         frame=frame, dist=dist * (P.CHASSIS[a.chassis].hull[0] / 0.62) ** 0.8,
         azimuth_deg=az, elevation_deg=el, focal=a.focal)
wpx, hpx = (int(v) for v in a.res.split("x"))
R.settings(samples=a.samples, res=(wpx, hpx))
cy = bpy.context.scene.cycles
cy.volume_step_rate = 8.0
cy.volume_max_steps = 48
cy.max_bounces = 4
R.render_still(os.path.abspath(a.out), frame=frame)
print("rendered", a.out)
