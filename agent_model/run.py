"""Build, pose, and render an agent.

With the pip bpy module:     python -m agent_model.run [options]
With a Blender install:      blender -b -P agent_model/run.py -- [options]

Examples
  python -m agent_model.run --chassis surveyor --out renders/surveyor.png
  python -m agent_model.run --chassis hauler --move "stand 0.5; walk 3 0.4 25 walk" --anim renders/walk_ --frames 1,120,4
  python -m agent_model.run --chassis scout --modules top_f=optical,top_r=passive_acoustic --save scout.blend
"""
import argparse
import os
import sys

_here = os.path.dirname(os.path.abspath(__file__))
if os.path.dirname(_here) not in sys.path:
    sys.path.insert(0, os.path.dirname(_here))

import bpy  # noqa: E402
from agent_model import params as P  # noqa: E402
from agent_model.build import build_agent  # noqa: E402
from agent_model.motion import Mover, script  # noqa: E402
from agent_model import render as R  # noqa: E402

SKINS = {
    "team_a": P.Skin("team_a"),
    "team_b": P.Skin("team_b", base=(0.55, 0.30, 0.10), chassis=(0.06, 0.06, 0.06), accent=(0.85, 0.85, 0.8), light=(1.0, 0.55, 0.15)),
    "salvage": P.Skin("salvage", base=(0.35, 0.33, 0.28), accent=(0.5, 0.45, 0.3), light=(0.9, 0.2, 0.2), wear=0.85, grime=0.8),
    "fresh": P.Skin("fresh", base=(0.7, 0.68, 0.62), accent=(0.95, 0.5, 0.1), wear=0.05, grime=0.1),
}


def parse(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--chassis", default="surveyor", choices=list(P.CHASSIS))
    ap.add_argument("--modules", default=None, help="slot=module,slot=module (default: a sensible loadout)")
    ap.add_argument("--skin", default="team_a", choices=list(SKINS))
    ap.add_argument("--wear", type=float, default=None)
    ap.add_argument("--light", default=None, help="r,g,b for the running lights")
    ap.add_argument("--move", default="stand 0.2; look 1.4,-0.8,0.3 0.4 ride; walk 2.5 0.45 15 trot; stand 0.4",
                    help="motion script; see agent_model/motion.py")
    ap.add_argument("--pose-frame", type=int, default=None, help="frame to render the still at (default: mid-walk)")
    ap.add_argument("--out", default=None, help="still image path")
    ap.add_argument("--anim", default=None, help="animation path prefix (frames written as prefix####.png)")
    ap.add_argument("--frames", default=None, help="start,end,step for --anim / --video")
    ap.add_argument("--video", default=None, help="render the timeline to this .mp4")
    ap.add_argument("--samples", type=int, default=96)
    ap.add_argument("--res", default="1600x1000")
    ap.add_argument("--save", default=None, help="write a .blend to open on your machine")
    ap.add_argument("--export", default=None, help="write a .glb: armature, one skinned mesh, the motion baked to FK")
    ap.add_argument("--export-clip", default="clip", help="name of the animation in the .glb")
    ap.add_argument("--export-in-place", type=int, default=1, help="1 strips the world travel so the clip loops in place")
    ap.add_argument("--export-frames", default=None, help="first,last -- trim the clip to a whole number of gait cycles")
    ap.add_argument("--fps", type=int, default=24)
    ap.add_argument("--no-cave", action="store_true")
    ap.add_argument("--cam", default="-42,9,1.75", help="azimuth_deg,elevation_deg,distance")
    ap.add_argument("--chase", action="store_true", help="camera follows the body (default on for --video / --anim)")
    return ap.parse_args(argv)


def main(argv=None):
    if argv is None:
        argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    a = parse(argv)
    R.clear_scene()
    cfg = P.default_config(a.chassis)
    if a.modules:
        cfg.modules = dict(kv.split("=") for kv in a.modules.split(","))
    skin = SKINS[a.skin]
    if a.wear is not None:
        skin.wear = a.wear
    if a.light:
        skin.light = tuple(float(v) for v in a.light.split(","))
    cfg.skin = skin
    built = build_agent(cfg)
    mover = Mover(built, fps=a.fps)
    last = script(mover, a.move)
    # --export writes the model out and stops: there is nothing to render, and
    # the export mutates the rig (constraints baked away, meshes joined), so it
    # must not be followed by anything that expects the rig it was built with.
    if a.export:
        from agent_model.export_gltf import export_glb
        ef0, ef1 = 1, last
        if a.export_frames:
            ef0, ef1 = (int(v) for v in a.export_frames.split(","))
        st = export_glb(built, a.export, clip=a.export_clip, f0=ef0, f1=ef1,
                        in_place=bool(a.export_in_place), fps=a.fps)
        print("EXPORT " + repr(st))
        return
    if not a.no_cave:
        R.cave(path=mover.path)
    az, el, dist = (float(v) for v in a.cam.split(","))
    zc = float(built.arm["hull_center_z"])
    frame = a.pose_frame if a.pose_frame is not None else max(1, last // 2)
    chase = a.chase or bool(a.video or a.anim)
    cam = R.camera(built.arm, aim_offset=(0.12, 0, zc * 0.95), frame=1 if chase else frame,
                   dist=dist * (P.CHASSIS[a.chassis].hull[0] / 0.62) ** 0.8, azimuth_deg=az, elevation_deg=el, chase=chase)
    R.lights(target=tuple(built.arm.matrix_world.translation + __import__("mathutils").Vector((0.1, 0, zc))))
    w, h = (int(v) for v in a.res.split("x"))
    R.settings(samples=a.samples, res=(w, h))
    if a.save:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(a.save))
        print("saved", a.save)
    if a.out:
        R.render_still(os.path.abspath(a.out), frame=frame)
        print("rendered", a.out, "frame", frame)
    if a.video:
        s, e = 1, last
        if a.frames:
            s, e = (int(v) for v in a.frames.split(",")[:2])
        R.render_video(os.path.abspath(a.video), s, e)
        print("rendered video", a.video, s, e)
    if a.anim:
        s, e, st = (1, last, 1)
        if a.frames:
            s, e, st = (int(v) for v in a.frames.split(","))
        R.render_animation(os.path.abspath(a.anim), s, e, st)
        print("rendered frames", a.anim, s, e, st)


if __name__ == "__main__":
    main()
