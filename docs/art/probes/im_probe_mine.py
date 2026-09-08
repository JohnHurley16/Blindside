"""Industrial-archaeology probes.

Tests four claims the first pass could not separate:
  --albedo   raise the rock ramp from 0.015-0.11 (wet black basalt) to mine values
             (dust-covered dolomite). If a lamp-only frame becomes readable, the
             darkness is a MATERIAL problem, not a light problem.
  --flood    add a low wide work lamp on the hull aimed forward-and-down, in
             addition to the 50 deg head spot. Tests whether the head spot's real
             failure is that it points away from every surface the camera sees.
  --wear-dir add gravity to the wear mask: a mud line by world Z, dust on
             upward normals. Tests whether wear can carry history instead of noise.
  --worked   replace the blob cave with a driven tunnel: flat floor, sprung arch,
             a bolt line, drill scars, a rail.
"""
import sys, os, math, argparse
sys.path.insert(0, r"C:/Users/jackh/documents/programming/Blindside")
import bpy
from mathutils import Vector
from agent_model import params as P
from agent_model.build import build_agent
from agent_model.motion import Mover, script
from agent_model import render as R
from agent_model import geometry as G
from agent_model import materials as M
from agent_model.run import SKINS

ap = argparse.ArgumentParser()
ap.add_argument("--chassis", default="surveyor")
ap.add_argument("--modules", default=None)
ap.add_argument("--skin", default="team_a")
ap.add_argument("--wear", type=float, default=None)
ap.add_argument("--albedo", default=None, help="lo_r,lo_g,lo_b,hi_r,hi_g,hi_b")
ap.add_argument("--lamp-energy", type=float, default=70.0)
ap.add_argument("--lamp-white", action="store_true")
ap.add_argument("--flood", type=float, default=0.0, help="watts for the wide work lamp")
ap.add_argument("--flood-deg", type=float, default=110.0)
ap.add_argument("--flood-tilt", type=float, default=32.0, help="degrees below horizontal")
ap.add_argument("--wear-dir", action="store_true")
ap.add_argument("--worked", action="store_true")
ap.add_argument("--shaft", type=float, default=0.0)
ap.add_argument("--assayer-glow", type=float, default=0.0)
ap.add_argument("--fog", type=float, default=None)
ap.add_argument("--cam", default="-42,9,1.75")
ap.add_argument("--samples", type=int, default=64)
ap.add_argument("--res", default="1100x700")
ap.add_argument("--out", required=True)
a = ap.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:])

R.clear_scene()
cfg = P.default_config(a.chassis)
if a.modules is not None:
    cfg.modules = dict(kv.split("=") for kv in a.modules.split(",")) if a.modules else {}
skin = SKINS[a.skin]
if a.wear is not None:
    skin.wear = a.wear
cfg.skin = skin
built = build_agent(cfg)
mover = Mover(built)
last = script(mover, "stand 0.2; look 1.4,-0.3,0.2 0.4 ride; walk 2.2 0.45 10 trot; stand 0.3")
R.cave(path=mover.path)

# ---- 1. rock albedo -----------------------------------------------------------------
if a.albedo:
    v = [float(x) for x in a.albedo.split(",")]
    for mat in bpy.data.materials:
        if not mat.name.startswith("wet_rock"):
            continue
        for n in mat.node_tree.nodes:
            if n.type == "VALTORGB" and len(n.color_ramp.elements) == 2:
                e = n.color_ramp.elements
                if e[0].color[0] < 0.05:          # the albedo ramp, not the wetness ramp
                    e[0].color = (v[0], v[1], v[2], 1)
                    e[1].color = (v[3], v[4], v[5], 1)

# ---- 2. directional wear ------------------------------------------------------------
if a.wear_dir:
    for mat in bpy.data.materials:
        if "paint" not in mat.name:
            continue
        nt = mat.node_tree
        n = nt.nodes
        L = nt.links.new
        bsdf = next(x for x in n if x.type == "BSDF_PRINCIPLED")
        if not bsdf.inputs["Base Color"].links or not bsdf.inputs["Roughness"].links:
            continue
        src = bsdf.inputs["Base Color"].links[0].from_socket
        geo = n.new("ShaderNodeNewGeometry")
        sep = n.new("ShaderNodeSeparateXYZ")
        L(geo.outputs["Position"], sep.inputs["Vector"])
        # mud line: everything under ~0.20 m of world Z takes splash
        mud = n.new("ShaderNodeMapRange")
        mud.inputs["From Min"].default_value = 0.20
        mud.inputs["From Max"].default_value = 0.05
        L(sep.outputs["Z"], mud.inputs["Value"])
        mudn = n.new("ShaderNodeTexNoise")
        mudn.inputs["Scale"].default_value = 22.0
        mudmul = n.new("ShaderNodeMath")
        mudmul.operation = "MULTIPLY"
        L(mud.outputs["Result"], mudmul.inputs[0])
        L(mudn.outputs["Fac"], mudmul.inputs[1])
        mudmix = n.new("ShaderNodeMix")
        mudmix.data_type = "RGBA"
        mudmix.inputs["B"].default_value = (0.055, 0.042, 0.030, 1)     # wet ore mud
        L(src, mudmix.inputs["A"])
        L(mudmul.outputs[0], mudmix.inputs["Factor"])
        # dust on horizontals: upward-facing normals only
        nsep = n.new("ShaderNodeSeparateXYZ")
        L(geo.outputs["Normal"], nsep.inputs["Vector"])
        up = n.new("ShaderNodeMapRange")
        up.inputs["From Min"].default_value = 0.35
        up.inputs["From Max"].default_value = 0.95
        L(nsep.outputs["Z"], up.inputs["Value"])
        dn = n.new("ShaderNodeTexNoise")
        dn.inputs["Scale"].default_value = 9.0
        dmul = n.new("ShaderNodeMath")
        dmul.operation = "MULTIPLY"
        dmul.inputs[1].default_value = 0.55
        dmul2 = n.new("ShaderNodeMath")
        dmul2.operation = "MULTIPLY"
        L(up.outputs["Result"], dmul.inputs[0])
        L(dmul.outputs[0], dmul2.inputs[0])
        L(dn.outputs["Fac"], dmul2.inputs[1])
        dmix = n.new("ShaderNodeMix")
        dmix.data_type = "RGBA"
        dmix.inputs["B"].default_value = (0.30, 0.265, 0.215, 1)        # pale rock dust
        L(mudmix.outputs["Result"], dmix.inputs["A"])
        L(dmul2.outputs[0], dmix.inputs["Factor"])
        L(dmix.outputs["Result"], bsdf.inputs["Base Color"])
        # wet below the mud line: roughness drops
        rl = bsdf.inputs["Roughness"].links[0].from_socket
        rmix = n.new("ShaderNodeMix")
        rmix.data_type = "FLOAT"
        rmix.inputs["B"].default_value = 0.18
        L(rl, rmix.inputs["A"])
        L(mud.outputs["Result"], rmix.inputs["Factor"])
        L(rmix.outputs["Result"], bsdf.inputs["Roughness"])

# ---- 3. a driven tunnel instead of a blob ------------------------------------------
if a.worked:
    for o in list(bpy.data.objects):
        if o.name.startswith(("cave_walls", "rock.")):
            bpy.data.objects.remove(o, do_unlink=True)
    rock = bpy.data.materials["wet_rock"]
    col = bpy.data.collections["CAVE"]
    W2, SPR, CR = 1.45, 1.5, 2.6          # half-width, springing line, crown
    for side in (1, -1):
        w = G.box("rib_wall%d" % side, (14.0, 0.5, SPR), (0, side * (W2 + 0.25), SPR / 2), col=col)
        G.set_material(w, rock)
    ar = CR - SPR + W2 * 0.15
    arch = G.cyl("arch", ar, ar, 14.0, (0, 0, SPR), rot=(0, math.pi / 2, 0), verts=28, col=col)
    arch.scale = (1.0, W2 / ar, 1.0)
    bpy.ops.object.transform_apply(scale=True)
    d = arch.modifiers.new("d", "DISPLACE")
    t = bpy.data.textures.new("scar", "CLOUDS")
    t.noise_scale = 0.35
    t.noise_depth = 5
    d.texture = t
    d.strength = 0.16
    d.mid_level = 0.5
    arch.data.shade_smooth()
    bpy.ops.object.select_all(action="DESELECT")
    arch.select_set(True)
    bpy.context.view_layer.objects.active = arch
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.flip_normals()
    bpy.ops.object.mode_set(mode="OBJECT")
    G.set_material(arch, rock)
    steel = M.bare_metal("bolt_steel", tint=(0.42, 0.38, 0.33), rough=0.62)
    for i in range(-5, 7):
        for side in (1, -1):
            y = side * (W2 * 0.92)
            z = SPR + (CR - SPR) * 0.55
            p = G.box("plate%d_%d" % (i, side), (0.15, 0.02, 0.15), (i * 1.2, y, z), col=col)
            G.set_material(p, steel)
            b = G.cyl("bolt%d_%d" % (i, side), 0.022, 0.022, 0.09, (i * 1.2, y - side * 0.05, z),
                      rot=(math.pi / 2, 0, 0), verts=8, col=col)
            G.set_material(b, steel)
    for side in (1, -1):
        r = G.box("rail%d" % side, (14.0, 0.055, 0.07), (0, side * 0.36, 0.02), col=col)
        G.set_material(r, M.bare_metal("rail_steel%d" % side, tint=(0.30, 0.22, 0.16), rough=0.75))
    for i in range(-9, 10):
        s = G.box("sleeper%d" % i, (0.14, 1.0, 0.05), (i * 0.7, 0, 0.005), col=col)
        G.set_material(s, rock)

# ---- 4. lights that exist in the fiction --------------------------------------------
if a.fog is not None:
    for n in bpy.context.scene.world.node_tree.nodes:
        if n.type == "VOLUME_SCATTER":
            n.inputs["Density"].default_value = a.fog

if built.lamp is not None:
    built.lamp.data.energy = a.lamp_energy
    if a.lamp_white:
        built.lamp.data.color = (1.0, 0.97, 0.92)

if a.flood > 0:
    d = bpy.data.lights.new("WORK_FLOOD", "SPOT")
    d.energy = a.flood
    d.spot_size = math.radians(a.flood_deg)
    d.spot_blend = 0.75
    d.color = (1.0, 0.96, 0.90)
    d.shadow_soft_size = 0.06
    o = bpy.data.objects.new("WORK_FLOOD", d)
    bpy.context.scene.collection.objects.link(o)
    ch = P.CHASSIS[a.chassis]
    zc = float(built.arm["hull_center_z"])
    # a spot points along local -Z. R_y(theta) . (0,0,-1) = (-sin, 0, -cos), so +X and
    # tilted `flood_tilt` below horizontal needs theta = -(90 - tilt).
    o.location = Vector((ch.hull[0] * 0.46, 0, zc + ch.hull[2] * 0.45))
    o.rotation_euler = (0, -math.radians(90 - a.flood_tilt), 0)
    o.parent = built.arm            # it is bolted to the machine, so it walks with it

if a.shaft > 0:
    d = bpy.data.lights.new("SHAFT", "AREA")
    d.energy = a.shaft
    d.color = (0.62, 0.76, 1.0)
    d.size = 1.1
    o = bpy.data.objects.new("SHAFT", d)
    bpy.context.scene.collection.objects.link(o)
    o.location = Vector(built.arm.matrix_world.translation) + Vector((0.4, 0.6, 3.2))

if a.assayer_glow > 0:
    d = bpy.data.lights.new("ASSAYER", "POINT")
    d.energy = a.assayer_glow
    d.color = (1.0, 0.55, 0.22)
    d.shadow_soft_size = 0.35
    o = bpy.data.objects.new("ASSAYER", d)
    bpy.context.scene.collection.objects.link(o)
    o.location = Vector(built.arm.matrix_world.translation) + Vector((3.2, 1.8, 1.1))

az, el, dist = (float(v) for v in a.cam.split(","))
zc = float(built.arm["hull_center_z"])
frame = max(1, last // 2)
R.camera(built.arm, aim_offset=(0.12, 0, zc * 0.95), frame=frame,
         dist=dist * (P.CHASSIS[a.chassis].hull[0] / 0.62) ** 0.8, azimuth_deg=az, elevation_deg=el)
w, h = (int(v) for v in a.res.split("x"))
R.settings(samples=a.samples, res=(w, h))
R.render_still(os.path.abspath(a.out), frame=frame)
print("rendered", a.out)
