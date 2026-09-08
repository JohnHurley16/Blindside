"""Second lighting pass: test the proposed LIGHT ECONOMY rather than more wattage.

The first pass (probe_dark.py) proved that 5.7x the lamp buys nothing, because rock
albedo is 0.015-0.11 and a head-mounted spot points away from every surface the camera
can see. This probe tests the fixes that follow from that, one at a time.

  --albedo LO,HI    rock base-colour ramp (shipped value is 0.015,0.11)
  --lampcol white|team
  --mode            lamp | econ | econ_nolamp | wear
  --wearmode        current | directional   (patches painted_metal with gravity)

Modes:
  lamp        agent lamp only, at whatever albedo is set. Isolates the bounce budget.
  econ        the proposal: one distant warm world source (an Assayer at ~6 m), a WHITE
              agent lamp, raised low-end albedo, silt at 3x.
  econ_nolamp the same world source with the agent lamp OFF -- the quiet loadout under
              the proposed economy. The frame that decides whether quiet is playable.
  wear        shaft-lit (the readable reference frame) so a material change is visible.
"""
import sys, os, argparse
sys.path.insert(0, r"C:/Users/jackh/documents/programming/Blindside")
import bpy
from mathutils import Vector

ap = argparse.ArgumentParser()
ap.add_argument("--mode", default="econ")
ap.add_argument("--chassis", default="surveyor")
ap.add_argument("--modules", default=None)
ap.add_argument("--skin", default="team_a")
ap.add_argument("--wear", type=float, default=None)
ap.add_argument("--wearmode", default="current")
ap.add_argument("--albedo", default="0.015,0.11")
ap.add_argument("--lampcol", default="team")
ap.add_argument("--lamp-energy", type=float, default=70.0)
ap.add_argument("--cam", default="-42,9,1.75")
ap.add_argument("--samples", type=int, default=64)
ap.add_argument("--res", default="1100x700")
ap.add_argument("--fog", type=float, default=None)
ap.add_argument("--bounces", type=int, default=None)
ap.add_argument("--assayer-w", type=float, default=220.0)
ap.add_argument("--assayer-at", default="2.6,1.4,0.9",
                help="offset from the body. The probe cave dome is only ~5.4 x 4.25 x 2.7 m, "
                     "so anything past ~3 m is buried in rock and contributes nothing.")
ap.add_argument("--out", required=True)
a = ap.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:])

LO, HI = (float(v) for v in a.albedo.split(","))

from agent_model import materials as M
from agent_model import params as P

# ---- patch 1: rock albedo. One ramp, two stops. The whole bounce budget. -------------
_orig_wet_rock = M.wet_rock


def wet_rock(name="wet_rock"):
    m = _orig_wet_rock(name)
    for n in m.node_tree.nodes:
        if n.type == "VALTORGB":
            c0 = tuple(round(v, 4) for v in n.color_ramp.elements[0].color)[:3]
            if c0 == (0.015, 0.014, 0.013):
                n.color_ramp.elements[0].color = (LO, LO * 0.93, LO * 0.87, 1)
                n.color_ramp.elements[1].color = (HI, HI * 0.91, HI * 0.82, 1)
    return m


M.wet_rock = wet_rock

# ---- patch 2: wear that knows which way is down -------------------------------------
# Three world-space masks folded into the existing procedural wear:
#   mud    world z below MUD_TOP, strongest at the feet -> toward a wet dark ochre
#   dust   upward-facing normals only                   -> toward a pale dry grey
# Both are cheap: a Geometry node, two ramps, two noises.
_orig_painted = M.painted_metal


def painted_metal_directional(skin, name="hull_paint"):
    m = _orig_painted(skin, name)
    nt = m.node_tree
    n = nt.nodes
    L = nt.links.new
    bsdf = next(x for x in n if x.type == "BSDF_PRINCIPLED")
    src = bsdf.inputs["Base Color"].links[0].from_socket
    geo = n.new("ShaderNodeNewGeometry")
    sep = n.new("ShaderNodeSeparateXYZ")
    L(geo.outputs["Position"], sep.inputs["Vector"])
    MUD_TOP = 0.20
    mudramp = n.new("ShaderNodeValToRGB")
    mudramp.color_ramp.elements[0].position = 0.0
    mudramp.color_ramp.elements[0].color = (1, 1, 1, 1)
    mudramp.color_ramp.elements[1].position = MUD_TOP
    mudramp.color_ramp.elements[1].color = (0, 0, 0, 1)
    L(sep.outputs["Z"], mudramp.inputs["Fac"])
    mudnoise = n.new("ShaderNodeTexNoise")
    mudnoise.inputs["Scale"].default_value = 24.0
    mudmul = n.new("ShaderNodeMath")
    mudmul.operation = "MULTIPLY"
    L(mudramp.outputs["Color"], mudmul.inputs[0])
    L(mudnoise.outputs["Fac"], mudmul.inputs[1])
    mudgain = n.new("ShaderNodeMath")
    mudgain.operation = "MULTIPLY"
    mudgain.inputs[1].default_value = 2.6 * max(skin.grime, 0.25)
    L(mudmul.outputs[0], mudgain.inputs[0])
    mudmix = n.new("ShaderNodeMix")
    mudmix.data_type = "RGBA"
    mudmix.inputs["B"].default_value = (0.035, 0.026, 0.018, 1)
    L(src, mudmix.inputs["A"])
    L(mudgain.outputs[0], mudmix.inputs["Factor"])
    nsep = n.new("ShaderNodeSeparateXYZ")
    L(geo.outputs["Normal"], nsep.inputs["Vector"])
    upramp = n.new("ShaderNodeValToRGB")
    upramp.color_ramp.elements[0].position = 0.45
    upramp.color_ramp.elements[1].position = 0.95
    L(nsep.outputs["Z"], upramp.inputs["Fac"])
    dustnoise = n.new("ShaderNodeTexNoise")
    dustnoise.inputs["Scale"].default_value = 9.0
    dmul = n.new("ShaderNodeMath")
    dmul.operation = "MULTIPLY"
    L(upramp.outputs["Color"], dmul.inputs[0])
    L(dustnoise.outputs["Fac"], dmul.inputs[1])
    dgain = n.new("ShaderNodeMath")
    dgain.operation = "MULTIPLY"
    dgain.inputs[1].default_value = 0.85 * max(skin.grime, 0.2)
    L(dmul.outputs[0], dgain.inputs[0])
    dustmix = n.new("ShaderNodeMix")
    dustmix.data_type = "RGBA"
    dustmix.inputs["B"].default_value = (0.16, 0.145, 0.12, 1)
    L(mudmix.outputs["Result"], dustmix.inputs["A"])
    L(dgain.outputs[0], dustmix.inputs["Factor"])
    L(dustmix.outputs["Result"], bsdf.inputs["Base Color"])
    rsrc = bsdf.inputs["Roughness"].links[0].from_socket
    rmix = n.new("ShaderNodeMath")
    rmix.operation = "MAXIMUM"
    L(rsrc, rmix.inputs[0])
    L(dgain.outputs[0], rmix.inputs[1])
    L(rmix.outputs[0], bsdf.inputs["Roughness"])
    return m


if a.wearmode == "directional":
    M.painted_metal = painted_metal_directional

from agent_model.build import build_agent
from agent_model.motion import Mover, script
from agent_model import render as R
from agent_model.run import SKINS

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

fog = a.fog
if a.mode in ("econ", "econ_nolamp") and fog is None:
    fog = 0.018
if fog is not None:
    for n in bpy.context.scene.world.node_tree.nodes:
        if n.type == "VOLUME_SCATTER":
            n.inputs["Density"].default_value = fog

if built.lamp is not None:
    built.lamp.data.energy = a.lamp_energy
    if a.lampcol == "white":
        built.lamp.data.color = (1.0, 0.97, 0.92)

body = Vector(built.arm.matrix_world.translation)
ASSAYER_AT = tuple(float(v) for v in a.assayer_at.split(","))


def point(name, offset, energy, color, soft=0.3):
    d = bpy.data.lights.new(name, "POINT")
    d.energy = energy
    d.color = color
    d.shadow_soft_size = soft
    o = bpy.data.objects.new(name, d)
    bpy.context.scene.collection.objects.link(o)
    o.location = body + Vector(offset)
    return o


if a.mode == "econ":
    point("ASSAYER", ASSAYER_AT, a.assayer_w, (1.0, 0.58, 0.26), soft=0.5)
elif a.mode == "econ_nolamp":
    if built.lamp is not None:
        built.lamp.data.energy = 0.0
    point("ASSAYER", ASSAYER_AT, a.assayer_w, (1.0, 0.58, 0.26), soft=0.5)
elif a.mode == "wear":
    if built.lamp is not None:
        built.lamp.data.energy = 0.0
    d = bpy.data.lights.new("SHAFT", "AREA")
    d.energy = 260
    d.color = (0.62, 0.76, 1.0)
    d.size = 1.1
    o = bpy.data.objects.new("SHAFT", d)
    bpy.context.scene.collection.objects.link(o)
    o.location = body + Vector((0.4, 0.6, 3.2))

az, el, dist = (float(v) for v in a.cam.split(","))
zc = float(built.arm["hull_center_z"])
frame = max(1, last // 2)
R.camera(built.arm, aim_offset=(0.12, 0, zc * 0.95), frame=frame,
         dist=dist * (P.CHASSIS[a.chassis].hull[0] / 0.62) ** 0.8, azimuth_deg=az, elevation_deg=el)
w, h = (int(v) for v in a.res.split("x"))
R.settings(samples=a.samples, res=(w, h))
if a.bounces is not None:
    bpy.context.scene.cycles.max_bounces = a.bounces
R.render_still(os.path.abspath(a.out), frame=frame)
print("rendered", a.out)
