"""Lighting probe: build the agent, build the cave, and light the scene ONLY with
sources that exist in the fiction. No key, no rim, no fill.

  --mode lamp     the agent's own head lamp only (optical module fitted)
  --mode quiet    no lamp at all: running lights + emissive strips only
  --mode assayer  no agent lamp; one warm point where the ancient machine stands
  --mode shaft    a cold shaft of daylight from above, agent lit only by that
"""
import sys, os, math, argparse
sys.path.insert(0, r"C:/Users/jackh/documents/programming/Blindside")
import bpy
from mathutils import Vector
from agent_model import params as P
from agent_model.build import build_agent
from agent_model.motion import Mover, script
from agent_model import render as R
from agent_model.run import SKINS

ap = argparse.ArgumentParser()
ap.add_argument("--mode", default="lamp")
ap.add_argument("--chassis", default="surveyor")
ap.add_argument("--modules", default=None)
ap.add_argument("--skin", default="team_a")
ap.add_argument("--wear", type=float, default=None)
ap.add_argument("--lamp-energy", type=float, default=70.0)
ap.add_argument("--cam", default="-42,9,1.75")
ap.add_argument("--samples", type=int, default=64)
ap.add_argument("--res", default="1100x700")
ap.add_argument("--fog", type=float, default=None)
ap.add_argument("--out", required=True)
a = ap.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else sys.argv[1:])

R.clear_scene()
cfg = P.default_config(a.chassis)
if a.modules is not None:
    cfg.modules = dict(kv.split("=") for kv in a.modules.split(",")) if a.modules else {}
skin = SKINS[a.skin]
if a.wear is not None: skin.wear = a.wear
cfg.skin = skin
built = build_agent(cfg)
mover = Mover(built)
last = script(mover, "stand 0.2; look 1.4,-0.3,0.2 0.4 ride; walk 2.2 0.45 10 trot; stand 0.3")
R.cave(path=mover.path)

# ---- the fiction's own light sources, and nothing else -------------------------------
if a.fog is not None:
    nt = bpy.context.scene.world.node_tree
    for n in nt.nodes:
        if n.type == "VOLUME_SCATTER":
            n.inputs["Density"].default_value = a.fog

if built.lamp is not None:
    built.lamp.data.energy = a.lamp_energy
if a.mode == "quiet" and built.lamp is not None:
    built.lamp.data.energy = 0.0

if a.mode == "assayer":
    if built.lamp is not None: built.lamp.data.energy = 0.0
    d = bpy.data.lights.new("ASSAYER", "POINT"); d.energy = 60; d.color = (1.0, 0.62, 0.30); d.shadow_soft_size = 0.3
    o = bpy.data.objects.new("ASSAYER", d); bpy.context.scene.collection.objects.link(o)
    o.location = Vector(built.arm.matrix_world.translation) + Vector((2.6, 1.4, 0.9))

if a.mode == "shaft":
    if built.lamp is not None: built.lamp.data.energy = 0.0
    d = bpy.data.lights.new("SHAFT", "AREA"); d.energy = 260; d.color = (0.62, 0.76, 1.0); d.size = 1.1
    o = bpy.data.objects.new("SHAFT", d); bpy.context.scene.collection.objects.link(o)
    o.location = Vector(built.arm.matrix_world.translation) + Vector((0.4, 0.6, 3.2))
    o.rotation_euler = (0, 0, 0)

az, el, dist = (float(v) for v in a.cam.split(","))
zc = float(built.arm["hull_center_z"])
frame = max(1, last // 2)
R.camera(built.arm, aim_offset=(0.12, 0, zc*0.95), frame=frame,
         dist=dist * (P.CHASSIS[a.chassis].hull[0]/0.62) ** 0.8, azimuth_deg=az, elevation_deg=el)
w, h = (int(v) for v in a.res.split("x"))
R.settings(samples=a.samples, res=(w, h))
R.render_still(os.path.abspath(a.out), frame=frame)
print("rendered", a.out)
