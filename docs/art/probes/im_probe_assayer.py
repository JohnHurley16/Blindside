"""The Assayer, built to THE-MACHINERY.md 2.1 at 0.6 m/cell, with a surveyor at its foot.

Nothing here is invented geometry: every dimension in `SPEC` is section 2.1's number
times 0.6. What IS proposed is the DRESSING -- rust, the header tank, the winch, the
ladder, the wrecked service platform -- and the light.

  --lit  none | strike | fittings | both
         none      : agent lamp only. Does a 6.6 m machine read off a 70 W head spot?
         strike    : the hammer face incandescent, 0.15 s after the fall
         fittings  : two surviving bulkhead lamps on the old service circuit
"""
import sys, os, math, argparse
sys.path.insert(0, r"C:/Users/jackh/documents/programming/Blindside")
import bpy
from mathutils import Vector, Euler
from agent_model import params as P
from agent_model.build import build_agent
from agent_model.motion import Mover, script
from agent_model import render as R
from agent_model import geometry as G
from agent_model import materials as M
from agent_model.run import SKINS

MPC = 0.6                      # metres per cell -- the derived scale


def c(cells):
    return cells * MPC


ap = argparse.ArgumentParser()
ap.add_argument("--lit", default="fittings")
ap.add_argument("--hammer", type=float, default=0.0, help="0 rest .. 1 top of mast")
ap.add_argument("--aim", type=float, default=25.0, help="boom azimuth, degrees")
ap.add_argument("--agent", action="store_true")
ap.add_argument("--agent-lamp", type=float, default=70.0)
ap.add_argument("--cam", default="-46,7,9.0", help="azimuth,elevation,distance in metres")
ap.add_argument("--aimz", type=float, default=2.2)
ap.add_argument("--fog", type=float, default=0.010)
ap.add_argument("--fit", type=float, default=1.0, help="fitting energy multiplier")
ap.add_argument("--samples", type=int, default=64)
ap.add_argument("--res", default="1100x700")
ap.add_argument("--out", required=True)
a = ap.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:])

R.clear_scene()
col = G.new_collection("ASSAYER")

# ---- materials: three ages of iron, plus rock ---------------------------------------
def rusted(name, base=(0.075, 0.038, 0.021), rough=0.86, scale=3.0):
    """Cast iron that has been wet for a century: dark, matte, mottled, faintly
    ferrous-red where it has scaled, with a light bump so it is never flat."""
    m, nt, out = M._new(name)
    n = nt.nodes
    b = n.new("ShaderNodeBsdfPrincipled")
    b.inputs["Metallic"].default_value = 0.55
    coord = n.new("ShaderNodeTexCoord")
    tx = n.new("ShaderNodeTexNoise")
    tx.inputs["Scale"].default_value = scale
    tx.inputs["Detail"].default_value = 10
    fine = n.new("ShaderNodeTexNoise")
    fine.inputs["Scale"].default_value = scale * 14
    fine.inputs["Detail"].default_value = 6
    ramp = n.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.35
    ramp.color_ramp.elements[0].color = (base[0] * 0.45, base[1] * 0.45, base[2] * 0.5, 1)
    ramp.color_ramp.elements[1].position = 0.72
    ramp.color_ramp.elements[1].color = (base[0] * 1.9, base[1] * 1.6, base[2] * 1.3, 1)
    rgh = n.new("ShaderNodeMath")
    rgh.operation = "MULTIPLY_ADD"
    rgh.inputs[1].default_value = 0.14
    rgh.inputs[2].default_value = rough - 0.07
    bmp = n.new("ShaderNodeBump")
    bmp.inputs["Strength"].default_value = 0.35
    bmp2 = n.new("ShaderNodeBump")
    bmp2.inputs["Strength"].default_value = 0.15
    L = nt.links.new
    L(coord.outputs["Generated"], tx.inputs["Vector"])
    L(coord.outputs["Generated"], fine.inputs["Vector"])
    L(tx.outputs["Fac"], ramp.inputs["Fac"])
    L(ramp.outputs["Color"], b.inputs["Base Color"])
    L(tx.outputs["Fac"], rgh.inputs[0])
    L(rgh.outputs[0], b.inputs["Roughness"])
    L(fine.outputs["Fac"], bmp2.inputs["Height"])
    L(tx.outputs["Fac"], bmp.inputs["Height"])
    L(bmp2.outputs["Normal"], bmp.inputs["Normal"])
    L(bmp.outputs["Normal"], b.inputs["Normal"])
    L(b.outputs[0], out.inputs[0])
    return m


IRON = rusted("assayer_iron")
IRON_D = rusted("assayer_iron_dark", base=(0.045, 0.028, 0.018), rough=0.9, scale=5.0)
STEEL = M.bare_metal("polished_bearing", tint=(0.34, 0.30, 0.26), rough=0.30)
ROCK = M.wet_rock()
for n in ROCK.node_tree.nodes:
    if n.type == "VALTORGB" and len(n.color_ramp.elements) == 2 and n.color_ramp.elements[0].color[0] < 0.05:
        n.color_ramp.elements[0].color = (0.050, 0.043, 0.036, 1)
        n.color_ramp.elements[1].color = (0.30, 0.265, 0.215, 1)

# ---- the chamber: a stope, flat-floored, worked ---------------------------------------
floor = G.plane("floor", 46.0, (0, 0, 0), col=col, subdiv=90)
d = floor.modifiers.new("d", "DISPLACE")
t = bpy.data.textures.new("fl", "CLOUDS")
t.noise_scale = 2.4
t.noise_depth = 5
d.texture = t
d.strength = 0.30
d.mid_level = 0.62
floor.data.shade_smooth()
G.set_material(floor, ROCK)
bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=5, radius=16.0, location=(0, 0, 3.0))
dome = bpy.context.object
dome.name = "stope"
dome.scale = (1.0, 1.0, 0.52)
bpy.ops.object.transform_apply(scale=True)
d2 = dome.modifiers.new("d", "DISPLACE")
t2 = bpy.data.textures.new("wl", "CLOUDS")
t2.noise_scale = 3.2
t2.noise_depth = 6
d2.texture = t2
d2.strength = 3.2
dome.data.shade_smooth()
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.mesh.flip_normals()
bpy.ops.object.mode_set(mode="OBJECT")
G.set_material(dome, ROCK)
for cc in list(dome.users_collection):
    cc.objects.unlink(dome)
col.objects.link(dome)

# spoil: broken stock left where the survey said to dig (THE-MACHINERY 7)
import random
rng = random.Random(11)
for i in range(40):
    ang = rng.uniform(0, 6.283)
    dist = rng.uniform(4.5, 13.0)
    r = rng.uniform(0.10, 0.55)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=r,
                                          location=(math.cos(ang) * dist, math.sin(ang) * dist, r * 0.35))
    o = bpy.context.object
    o.name = "spoil.%d" % i
    o.scale = (rng.uniform(0.7, 1.6), rng.uniform(0.7, 1.6), rng.uniform(0.35, 0.7))
    o.rotation_euler = (rng.uniform(0, 3), rng.uniform(0, 3), rng.uniform(0, 3))
    mm = o.modifiers.new("d", "DISPLACE")
    tt = bpy.data.textures.new("sp%d" % i, "CLOUDS")
    tt.noise_scale = 0.22
    tt.noise_depth = 4
    mm.texture = tt
    mm.strength = r * 1.1
    o.data.shade_smooth()
    G.set_material(o, ROCK)
    for cc in list(o.users_collection):
        cc.objects.unlink(o)
    col.objects.link(o)

# ---- THE ASSAYER, section 2.1, times 0.6 ----------------------------------------------
AIM = math.radians(a.aim)
HUB_R, HUB_Z, FOOT_R = c(1.0), c(1.2), c(2.6)
MAST_F, MAST_TOP = c(1.6), c(11.0)
BOOM_L, BOOM_W, BOOM_Z = c(7.0), c(0.9), c(9.0)
RIB_S, RIB_ROOT, RIB_TIP = c(1.4), c(2.4), c(1.2)
CW = c(2.2)
HAM_R = c(2.0) / 2
BOLT_R = c(3.4)

# footing: three legs 120 deg apart, hub down to anchor pads
for k in range(3):
    th = AIM + k * 2.0944
    top = Vector((math.cos(th) * HUB_R, math.sin(th) * HUB_R, HUB_Z))
    bot = Vector((math.cos(th) * FOOT_R, math.sin(th) * FOOT_R, 0.05))
    lg = G.strut("foot_leg%d" % k, top, bot, 0.30, 0.34, 0.42, 0.30, col=col, bevel=0.02)
    G.set_material(lg, IRON)
    pad = G.box("pad%d" % k, (c(0.8), c(0.8), 0.10), (bot.x, bot.y, 0.05), rot=(0, 0, th), col=col, bevel=0.015)
    G.set_material(pad, IRON_D)
    for b in range(4):
        bo = G.cyl("padbolt%d_%d" % (k, b), 0.035, 0.035, 0.09,
                   (bot.x + math.cos(b * 1.57 + th) * c(0.28), bot.y + math.sin(b * 1.57 + th) * c(0.28), 0.12),
                   verts=8, col=col)
        G.set_material(bo, STEEL)
hub = G.cyl("hub", HUB_R * 1.05, HUB_R * 0.92, 0.55, (0, 0, HUB_Z), verts=6, col=col, bevel=0.02)
G.set_material(hub, IRON)

# mast: hex prism, 0.96 m across flats, 0.72 -> 6.6 m
mast = G.cyl("mast", MAST_F / 2 / math.cos(math.pi / 6), MAST_F / 2 / math.cos(math.pi / 6) * 0.86,
             MAST_TOP - HUB_Z, (0, 0, (MAST_TOP + HUB_Z) / 2), rot=(0, 0, math.pi / 6), verts=6, col=col, bevel=0.015)
G.set_material(mast, IRON)
# mast flange joints -- a mast this tall was shipped in sections and bolted
for z in (c(3.4), c(5.9), c(8.4)):
    fl = G.cyl("flange%d" % int(z * 100), MAST_F * 0.72, MAST_F * 0.72, 0.09, (0, 0, z), verts=6,
               rot=(0, 0, math.pi / 6), col=col, bevel=0.01)
    G.set_material(fl, IRON_D)
# ladder up the mast: someone had to service this
for i in range(int((MAST_TOP - HUB_Z) / 0.32)):
    z = HUB_Z + 0.25 + i * 0.32
    rg = G.cyl("rung%d" % i, 0.018, 0.018, 0.44, (MAST_F * 0.62, 0, z), rot=(math.pi / 2, 0, 0), verts=6, col=col)
    G.set_material(rg, STEEL)
for sd in (1, -1):
    st = G.box("stile%d" % sd, (0.035, 0.035, MAST_TOP - HUB_Z - 0.4),
               (MAST_F * 0.62, sd * 0.22, (MAST_TOP + HUB_Z) / 2), col=col)
    G.set_material(st, IRON_D)

# header tank: the fiction's power supply. Riveted plate, overflowing.
tank = G.cyl("header_tank", 0.85, 0.85, 1.5, (0, 0, c(9.9)), verts=20, col=col, bevel=0.02)
G.set_material(tank, IRON_D)
for i in range(20):
    th = i * 0.314
    rv = G.sphere("rivet%d" % i, 0.035, (math.cos(th) * 0.86, math.sin(th) * 0.86, c(9.9) + 0.55), col=col, seg=8)
    G.set_material(rv, STEEL)
band = G.torus("tank_band", 0.87, 0.05, (0, 0, c(9.9) - 0.3), col=col)
G.set_material(band, IRON)
# the launder that feeds it, running off into the dark
lau = G.box("launder", (7.0, 0.34, 0.28), (-3.6, 0, c(10.6)), rot=(0, -0.07, 0), col=col, bevel=0.01)
G.set_material(lau, IRON_D)

# boom at z = 5.4 m, swung to AIM
boom_root = Vector((0, 0, BOOM_Z))
bd = Vector((math.cos(AIM), math.sin(AIM), 0))
sd = Vector((-math.sin(AIM), math.cos(AIM), 0))
spine = G.strut("boom_spine", boom_root, boom_root + bd * BOOM_L, BOOM_W * 1.15, c(0.8), BOOM_W * 0.6, c(0.45),
                col=col, bevel=0.015)
G.set_material(spine, IRON)
for i in range(5):
    f = (i + 0.6) / 5.0
    hw = (RIB_ROOT + (RIB_TIP - RIB_ROOT) * f) / 2
    p = boom_root + bd * (f * BOOM_L)
    rb = G.strut("rib%d" % i, p - sd * hw, p + sd * hw, 0.10, 0.16, 0.10, 0.16, col=col, bevel=0.01)
    G.set_material(rb, IRON)
    for e in (1, -1):
        tp = G.cyl("ribtip%d_%d" % (i, e), 0.09, 0.055, 0.34, p + sd * hw * e, rot=(0, 0, 0), verts=10, col=col)
        G.set_material(tp, IRON_D)
# stay cables from the mast top to the boom: a 4.2 m arm needs them
for f in (0.55, 0.95):
    st = G.segment("stay%.2f" % f, Vector((0, 0, MAST_TOP - 0.35)), boom_root + bd * (f * BOOM_L), 0.028, 0.028,
                   verts=6, col=col)
    G.set_material(st, STEEL)
# counterweight
cwb = G.strut("cw", boom_root, boom_root - bd * CW, BOOM_W * 0.9, c(0.7), c(0.9), c(0.9), col=col, bevel=0.015)
G.set_material(cwb, IRON)
cwm = G.box("cw_mass", (c(0.9), c(1.6), c(1.1)), (boom_root - bd * CW).to_tuple(), rot=(0, 0, AIM), col=col, bevel=0.02)
G.set_material(cwm, IRON_D)

# the hammer: hex ring 1.2 m across riding the mast. hammer=0 rest, 1 at the top
ham_z = HUB_Z + 0.7 + a.hammer * (BOOM_Z - HUB_Z - 1.3)
hring = G.cyl("hammer", HAM_R, HAM_R, 0.62, (0, 0, ham_z), verts=6, rot=(0, 0, math.pi / 6), col=col, bevel=0.02)
G.set_material(hring, IRON)
hcap = G.cyl("hammer_face", HAM_R * 0.98, HAM_R * 0.8, 0.16, (0, 0, ham_z - 0.36), verts=6,
             rot=(0, 0, math.pi / 6), col=col, bevel=0.01)
G.set_material(hcap, STEEL)
# winch: drum on the mast, chain to the hammer
drum = G.cyl("winch_drum", 0.30, 0.30, 0.7, (MAST_F * 0.55, 0, c(2.6)), rot=(math.pi / 2, 0, 0), verts=18, col=col)
G.set_material(drum, IRON)
chain = G.segment("chain", Vector((MAST_F * 0.55, 0.30, c(2.6))), Vector((HAM_R * 0.8, 0.30, ham_z)), 0.022, 0.022,
                  verts=6, col=col)
G.set_material(chain, STEEL)

# bolt ring at r = 2.04 m: the old service platform, mostly gone
for i in range(8):
    th = i * 0.7854
    st = G.cyl("stanchion%d" % i, 0.06, 0.05, 1.1, (math.cos(th) * BOLT_R, math.sin(th) * BOLT_R, 0.55), verts=8, col=col)
    G.set_material(st, IRON_D)
for i in (0, 1, 2, 5):        # four bays of grating left of eight
    th0, th1 = i * 0.7854, (i + 1) * 0.7854
    gp = G.box("grate%d" % i, (BOLT_R * 0.62, 0.42, 0.05),
               (math.cos((th0 + th1) / 2) * BOLT_R, math.sin((th0 + th1) / 2) * BOLT_R, 1.06),
               rot=(0, 0, (th0 + th1) / 2 + 1.5708), col=col)
    G.set_material(gp, IRON_D)

# the scour: the ruined floor. A shallow, dark, dust-free annulus with no drawn boundary.
sc = G.plane("scour", 19.0, (0, 0, 0.012), col=col, subdiv=40)
d3 = sc.modifiers.new("d", "DISPLACE")
t3 = bpy.data.textures.new("sc", "CLOUDS")
t3.noise_scale = 1.1
t3.noise_depth = 6
d3.texture = t3
d3.strength = 0.16
d3.mid_level = 0.7
sc.data.shade_smooth()
scm = rusted("scoured_rock", base=(0.030, 0.026, 0.023), rough=0.95, scale=2.0)
G.set_material(sc, scm)

# ---- the agent, for scale ---------------------------------------------------------------
built = None
if a.agent:
    cfg = P.default_config("surveyor")
    cfg.skin = SKINS["team_a"]
    built = build_agent(cfg, at=(math.cos(AIM - 0.5) * 4.6, math.sin(AIM - 0.5) * 4.6, 0))
    mv = Mover(built)
    script(mv, "stand 0.6")
    if built.lamp is not None:
        built.lamp.data.energy = a.agent_lamp
        built.lamp.data.color = (1.0, 0.97, 0.92)
    built.arm.rotation_euler.z = AIM + 2.5

# ---- light --------------------------------------------------------------------------
w = bpy.data.worlds.new("World")
bpy.context.scene.world = w
w.use_nodes = True
_nt = w.node_tree
_bg = _nt.nodes.get("Background") or _nt.nodes.new("ShaderNodeBackground")
_bg.inputs["Color"].default_value = (0.0, 0.0, 0.0, 1)   # ZERO ambient: nothing is lit
_bg.inputs["Strength"].default_value = 0.0                # by anything not in the frame
_out = _nt.nodes.get("World Output") or _nt.nodes.new("ShaderNodeOutputWorld")
_nt.links.new(_bg.outputs[0], _out.inputs["Surface"])
_vol = _nt.nodes.new("ShaderNodeVolumeScatter")
_vol.inputs["Density"].default_value = a.fog
_vol.inputs["Anisotropy"].default_value = 0.4
_nt.links.new(_vol.outputs[0], _out.inputs["Volume"])


def fitting(name, loc, energy=9.0, color=(1.0, 0.72, 0.42)):
    """A surviving bulkhead lamp on the old service circuit. A real fixture: a cage,
    a glass, and a point source inside it, so it casts and can be seen."""
    body = G.cyl(name + "_body", 0.10, 0.10, 0.20, loc, rot=(0, math.pi / 2, 0), verts=12, col=col)
    G.set_material(body, IRON_D)
    gl, nt, out = M._new(name + "_glass")
    e = nt.nodes.new("ShaderNodeEmission")
    e.inputs["Color"].default_value = (*color, 1)
    e.inputs["Strength"].default_value = 22.0
    nt.links.new(e.outputs[0], out.inputs[0])
    glass = G.sphere(name + "_glass", 0.075, (loc[0] + 0.11, loc[1], loc[2]), col=col, seg=14)
    G.set_material(glass, gl)
    d = bpy.data.lights.new(name, "POINT")
    d.energy = energy
    d.color = color
    d.shadow_soft_size = 0.09
    o = bpy.data.objects.new(name, d)
    bpy.context.scene.collection.objects.link(o)
    o.location = (loc[0] + 0.11, loc[1], loc[2])


if a.lit in ("fittings", "both"):
    # A real cast bulkhead fitting is 150-400 W tungsten. Inverse square in a 14 m stope
    # means anything under ~100 W is a point in the dark and lights nothing -- measured.
    fitting("fit_a", (-5.6, 4.4, 2.6), energy=340.0 * a.fit)
    fitting("fit_b", (5.4, -5.2, 2.2), energy=180.0 * a.fit)
    fitting("fit_c", (-1.2, -8.4, 3.1), energy=120.0 * a.fit, color=(1.0, 0.66, 0.34))

if a.lit in ("strike", "both"):
    hm, nt, out = M._new("hot_face")
    e = nt.nodes.new("ShaderNodeEmission")
    e.inputs["Color"].default_value = (1.0, 0.30, 0.06, 1)
    e.inputs["Strength"].default_value = 60.0
    nt.links.new(e.outputs[0], out.inputs[0])
    G.set_material(hcap, hm)
    d = bpy.data.lights.new("STRIKE", "POINT")
    d.energy = 420
    d.color = (1.0, 0.42, 0.14)
    d.shadow_soft_size = 0.5
    o = bpy.data.objects.new("STRIKE", d)
    bpy.context.scene.collection.objects.link(o)
    o.location = (0, 0, 0.5)

# ---- camera -------------------------------------------------------------------------
az, el, dist = (float(v) for v in a.cam.split(","))
sc_ = bpy.context.scene
cd = bpy.data.cameras.new("CAM")
cd.lens = 42
cam = bpy.data.objects.new("CAM", cd)
sc_.collection.objects.link(cam)
azr, elr = math.radians(az), math.radians(el)
look = Vector((0, 0, a.aimz))
cam.location = look + Vector((math.cos(azr) * math.cos(elr), math.sin(azr) * math.cos(elr), math.sin(elr))) * dist
tgt = bpy.data.objects.new("CAM_aim", None)
sc_.collection.objects.link(tgt)
tgt.location = look
tr = cam.constraints.new("TRACK_TO")
tr.target = tgt
tr.track_axis = "TRACK_NEGATIVE_Z"
tr.up_axis = "UP_Y"
sc_.camera = cam
wpx, hpx = (int(v) for v in a.res.split("x"))
R.settings(samples=a.samples, res=(wpx, hpx))
R.render_still(os.path.abspath(a.out), frame=1)
print("rendered", a.out)
