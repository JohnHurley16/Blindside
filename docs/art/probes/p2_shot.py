"""Driver for the second-pass probes. Run with a Blender install:

  blender -b -P docs/art/probes/p2_shot.py -- --mode bounce --albedo 0.30 --out x.png

Modes
  bounce   agent in a 3 m passage, its own head lamp and nothing else. --albedo sweeps
           rock reflectance. The question: does a carried lamp light the machine by
           bounce off the passage it is standing in?
  beam     same, camera 90 deg to the side. The question: is the BEAM the picture?
  rim      no head lamp. The running lights promoted from emissive geometry to real
           area emitters. The question: can a quiet loadout be rendered at all?
  assayer  the Assayer in a chamber, agent at its foot for scale, lit by the machine
  shaft    a chamber with an aven, one cold overhead source
  wreck    a collapsed agent, emissives dead, lit by a passing agent's lamp
"""
import argparse
import math
import os
import sys

sys.path.insert(0, r"C:/Users/jackh/documents/programming/Blindside")

import bpy  # noqa: E402
from mathutils import Vector, Euler  # noqa: E402

from agent_model import params as P  # noqa: E402
from agent_model import render as R  # noqa: E402
from agent_model import geometry as G  # noqa: E402
from agent_model import materials as M  # noqa: E402
from agent_model.build import build_agent  # noqa: E402
from agent_model.motion import Mover, script  # noqa: E402
from agent_model.run import SKINS  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import p2_env as E  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--mode", default="bounce")
ap.add_argument("--chassis", default="surveyor")
ap.add_argument("--modules", default=None)
ap.add_argument("--skin", default="team_a")
ap.add_argument("--wear", type=float, default=None)
ap.add_argument("--light", default=None)
ap.add_argument("--albedo", type=float, default=0.30, help="rock albedo at the light end of the ramp")
ap.add_argument("--albedo-lo", type=float, default=None)
ap.add_argument("--warm", type=float, default=1.0)
ap.add_argument("--wet", type=float, default=0.35)
ap.add_argument("--waterline", type=float, default=None)
ap.add_argument("--fog", type=float, default=0.0)
ap.add_argument("--ambient", type=float, default=0.0)
ap.add_argument("--lamp", type=float, default=70.0)
ap.add_argument("--lamp-deg", type=float, default=50.0)
ap.add_argument("--lamp-white", action="store_true", help="lamp colour 1,1,1 instead of team-tinted")
ap.add_argument("--rim", type=float, default=0.0, help="watts per running-light strip, as a real area emitter")
ap.add_argument("--strip-strength", type=float, default=None, help="emission strength on the strip geometry")
ap.add_argument("--width", type=float, default=3.6)
ap.add_argument("--height", type=float, default=4.8)
ap.add_argument("--cam", default=None, help="cx,cy,cz,tx,ty,tz explicit camera")
ap.add_argument("--focal", type=float, default=35.0)
ap.add_argument("--exposure", type=float, default=0.0)
ap.add_argument("--samples", type=int, default=64)
ap.add_argument("--res", default="1100x700")
ap.add_argument("--aim", type=float, default=28.0, help="assayer boom bearing, degrees")
ap.add_argument("--hammer", type=float, default=0.0, help="assayer hammer height 0..1")
ap.add_argument("--assayer-w", type=float, default=0.0, help="watts of light from the machine")
ap.add_argument("--out", required=True)
a = ap.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:])

R.clear_scene()

# ---- agent --------------------------------------------------------------------------------
cfg = P.default_config(a.chassis)
if a.modules is not None:
    cfg.modules = dict(kv.split("=") for kv in a.modules.split(",")) if a.modules else {}
skin = SKINS[a.skin]
if a.wear is not None:
    skin.wear = a.wear
if a.light:
    skin.light = tuple(float(v) for v in a.light.split(","))
cfg.skin = skin
built = build_agent(cfg)
mover = Mover(built)
last = script(mover, "stand 0.2; look 2.5,0.0,0.1 0.4 ride; walk 2.0 0.45 0 trot; stand 0.3")
frame = max(1, last // 2)
bpy.context.scene.frame_set(frame)
zc = float(built.arm["hull_center_z"])
body = Vector(built.arm.matrix_world.translation)

# ---- rock and environment ------------------------------------------------------------------
lo = a.albedo_lo if a.albedo_lo is not None else a.albedo * 0.11
rock = E.rock("cave_rock", albedo_lo=lo, albedo_hi=a.albedo, warm=a.warm, wet=a.wet,
              waterline=a.waterline)
E.world(fog=a.fog, ambient=a.ambient)

if a.mode in ("assayer", "shaft"):
    E.chamber(radius=7.0, height=9.6, mat=rock, aven=(a.mode == "shaft"))
else:
    E.passage(width=a.width, height=a.height, length=20.0, mat=rock)

# ---- lamp ------------------------------------------------------------------------------------
# BUG, found by raycast and corrected here rather than in the repo:
# build.py:311 sets `lamp.rotation_euler = Euler((0, +pi/2, 0))`, which takes the spot's
# local -Z to -X. Parented to the tilt bone, the head lamp therefore points BACKWARDS --
# measured world direction (-0.983, 0, +0.184), first hit the agent's own head at 0.117 m.
# Every "the lamp does nothing" render in this repo is this line. The fix is -pi/2.
if built.lamp is not None:
    built.lamp.rotation_euler = Euler((0, -math.pi / 2, 0))
    built.lamp.data.energy = a.lamp
    built.lamp.data.spot_size = math.radians(a.lamp_deg)
    if a.lamp_white:
        built.lamp.data.color = (1.0, 1.0, 1.0)

if a.strip_strength is not None:
    for m in bpy.data.materials:
        if m.name.startswith("light_strip") or m.name == "eye":
            for n in m.node_tree.nodes:
                if n.type == "EMISSION":
                    n.inputs["Strength"].default_value = a.strip_strength

# running lights promoted to real emitters, parented to the body
if a.rim > 0:
    L, W, H = P.CHASSIS[a.chassis].hull
    for side in (1, -1):
        o = E.add_light(f"RUN.{side}", "AREA",
                        body + Vector((0.04, side * (W / 2 + 0.004), zc - H * 0.06)),
                        a.rim, tuple(skin.light), size=L * 0.32)
        o.rotation_euler = Euler((0, math.radians(90 * side), 0))
        o.parent = built.arm
        o.matrix_parent_inverse = built.arm.matrix_world.inverted()

# ---- mode-specific -----------------------------------------------------------------------------
cam_loc, cam_tgt = None, body + Vector((0.12, 0, zc * 0.95))

if a.mode == "bounce":
    cam_loc = body + Vector((-1.15, -0.80, 0.58))
elif a.mode == "wide":
    # over the shoulder, looking the way the lamp looks: the shot that contains the pool
    cam_loc = body + Vector((-2.45, -0.30, 1.30))
    cam_tgt = body + Vector((3.6, 0.05, -0.15))
elif a.mode == "ahead":
    # what a RIVAL sees: the lit machine coming at you, its own beam in your face
    cam_loc = body + Vector((5.4, 0.55, 0.85))
    cam_tgt = body + Vector((0.0, 0.0, 0.32))
elif a.mode == "beam":
    cam_loc = body + Vector((0.10, -1.35, 0.80))
    cam_tgt = body + Vector((2.4, 0, 0.30))
elif a.mode == "rim":
    if built.lamp is not None:
        built.lamp.data.energy = 0.0
    cam_loc = body + Vector((-1.00, -0.72, 0.50))

elif a.mode == "shaft":
    if built.lamp is not None:
        built.lamp.data.energy = 0.0
    E.add_light("SHAFT", "AREA", (0.6, 0.4, 7.6), 1400, (0.60, 0.74, 1.0), size=2.6,
                aim=(0.6, 0.4, 0))
    built.arm.location = Vector((0.9, 0.2, 0))
    bpy.context.view_layer.update()
    body = Vector(built.arm.matrix_world.translation)
    cam_loc = body + Vector((-2.2, -2.4, 1.35))
    cam_tgt = body + Vector((0, 0, zc))

elif a.mode == "assayer":
    ir = M.bare_metal("assayer_iron", (0.24, 0.19, 0.14), 0.62)
    dk = M.bare_metal("assayer_dark", (0.10, 0.085, 0.07), 0.72)
    E.assayer(at=(0, 0, 0), aim_deg=a.aim, hammer_frac=a.hammer, mat_iron=ir, mat_dark=dk)
    built.arm.location = Vector((3.3, -2.4, 0))
    for f in built.feet:
        f.location = f.location + Vector((3.3, -2.4, 0))
    built.look.location = Vector((0.0, 0.0, 2.2))    # aim the head, and the lamp, at the machine
    bpy.context.view_layer.update()
    body = Vector(built.arm.matrix_world.translation)
    if a.assayer_w > 0:
        # the winch under load: a hot point at the head of the mast, and the
        # anvil glow at its foot. Both are the machine doing its job.
        # outside the mast, not inside it: a 0.96 m hex prism occludes a point at its axis
        E.add_light("WINCH", "POINT", (0.0, 0.80, 5.15), a.assayer_w, (1.0, 0.55, 0.22), size=0.30)
        E.add_light("ANVIL", "POINT", (0.0, 1.05, 0.40), a.assayer_w * 0.35, (1.0, 0.42, 0.14), size=0.35)
    cam_loc = Vector((3.5, -3.5, 1.45))
    cam_tgt = Vector((0.2, -0.5, 3.4))

elif a.mode == "wreck":
    # collapse: roll it onto its right side, drop it, splay the feet, kill the emissives
    built.arm.rotation_euler = Euler((math.radians(-74), math.radians(6), math.radians(0.35)))
    built.arm.location = Vector((0, 0, -0.20))
    for i, f in enumerate(built.feet):
        f.location = Vector(f.location) + Vector((0.03 * (i - 1.5), -0.16 - 0.05 * i, -0.22))
    for m in bpy.data.materials:
        if m.name.startswith("light_strip") or m.name == "eye":
            for n in m.node_tree.nodes:
                if n.type == "EMISSION":
                    n.inputs["Strength"].default_value = 0.0
    if built.lamp is not None:
        built.lamp.data.energy = 0.0
    bpy.context.view_layer.update()
    body = Vector(built.arm.matrix_world.translation)
    # the light that finds it: another machine's lamp, off camera, from the left and low
    E.add_light("FINDER", "SPOT", body + Vector((-1.5, 2.2, 0.50)), 600, (1.0, 0.98, 0.95),
                size=0.05, spot_deg=50, blend=0.5, aim=(body.x + 0.05, body.y, 0.05))
    cam_loc = body + Vector((1.15, -1.05, 0.48))
    cam_tgt = body + Vector((0.0, 0.05, 0.02))

if a.cam:
    v = [float(x) for x in a.cam.split(",")]
    cam_loc, cam_tgt = Vector(v[:3]), Vector(v[3:6])

# ---- camera ------------------------------------------------------------------------------------
cd = bpy.data.cameras.new("CAM")
cd.lens = a.focal
cd.dof.use_dof = False
cd.dof.aperture_fstop = 3.2
cd.dof.focus_distance = (cam_loc - cam_tgt).length
cam = bpy.data.objects.new("CAM", cd)
bpy.context.scene.collection.objects.link(cam)
cam.location = cam_loc
t = bpy.data.objects.new("CAM_aim", None)
bpy.context.scene.collection.objects.link(t)
t.location = cam_tgt
c = cam.constraints.new("TRACK_TO")
c.target = t
c.track_axis = "TRACK_NEGATIVE_Z"
c.up_axis = "UP_Y"
bpy.context.scene.camera = cam

w, h = (int(v) for v in a.res.split("x"))
E.settings(samples=a.samples, res=(w, h), exposure=a.exposure)
bpy.context.scene.render.filepath = os.path.abspath(a.out)
bpy.ops.render.render(write_still=True)
print("RENDERED", a.out)
