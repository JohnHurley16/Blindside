"""Vision-board shots for the surface. Run with a Blender install:

  "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b -P docs/art/vision/surface/surface.py -- \
      --shot pithead_wide --out <ABSOLUTE>.png [--samples 40 --res 960x600 --screen <png> --term <png>]

Every shot names its concept and whether it is a CLEAR view (lit to be seen) or an IN-SITU view
(the game's own light) in NOTES.md. `--list` prints the shot names.
"""
import argparse
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

import surface_lib as S  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--shot", default="pithead_wide")
ap.add_argument("--out", default=None)
ap.add_argument("--samples", type=int, default=40)
ap.add_argument("--res", default="960x600")
ap.add_argument("--screen", default=None, help="belief-map PNG for the pendant / post screens")
ap.add_argument("--term", default=None, help="tree+sentence PNG for the bench terminal")
ap.add_argument("--list", action="store_true")
A = ap.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
RES = tuple(int(v) for v in A.res.split("x"))
SHOTS = {}


def shot(fn):
    SHOTS[fn.__name__] = fn
    return fn


def fresh():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    S.COL = None
    S._MATS.clear()
    bpy.context.scene.unit_settings.system = "METRIC"


def compound(kind="overcast", course=True, cage_z=S.COLLAR_Z, cage=True, flood=False, post=True,
             yard=True, wh=True, puddles=True, roofed=None):
    """The whole pit-head. Everything hangs on this."""
    S.WET = {"overcast": 0.35, "sun": 0.0, "night": 0.6}.get(kind, 1.0)
    S.sky(kind)
    wet = {"overcast": 0.5, "sun": 0.2}.get(kind, 0.8)
    S.terrain(rock=S.spoil_rock(wet))
    S.hardstanding(puddles=puddles, wet=wet + 0.1)
    S.shaft()
    S.headframe()
    apex = S.cage(cage_z) if cage else None
    S.cable(cage_apex=apex, down_to=None if cage else -30.0)
    S.winch()
    if wh:
        S.winding_house()
    if yard:
        S.yard(A.term)
    if post:
        S.listening_post(A.screen)
    if flood:
        S.flood_light()
    out = None
    if course:
        out = S.course(roofed=roofed)
    return out


# =====================================================================================
# A1 the pit-head as a place
# =====================================================================================
@shot
def pithead_wide():
    """CLEAR. DAYLIGHT establishing from the south-west: headframe, winding house, yard, collar, course beyond."""
    compound("overcast")
    S.machine(at=(-4.0, -1.0, 0), yaw=0.0, walk=1.6)
    S.machine(at=(-7.5, 15.5, 0), yaw=-1.2, tag="yard1")
    S.camera((-30, -24, 8.5), (2.0, 8.0, 3.2), focal=30)


@shot
def pithead_high():
    """CLEAR. High oblique of the whole compound with the course on the spoil flat to the east."""
    compound("overcast")
    S.camera((-30, -95, 70), (30, 10, 0), focal=32)


@shot
def pithead_insitu():
    """IN-SITU. Drizzle at match start: one machine walking to the collar; the four teams never share a pit-head."""
    compound("drizzle", flood=True)
    S.machine(at=(-6.0, 0.4, 0), yaw=0.0, walk=1.6, lamp=300.0)
    S.camera((-13.5, 6.5, 1.7), (-1.0, 0.5, 1.6), focal=35)


@shot
def pithead_from_course():
    """IN-SITU. The compound seen from the course: what the player walks back from with a taught machine."""
    compound("overcast")
    S.machine(at=(22.0, -4.5, 0), yaw=math.pi, walk=1.6)
    S.camera((34, -12, 1.7), (0, 4, 4), focal=40)


# =====================================================================================
# A2 the headframe and winding gear
# =====================================================================================
@shot
def headframe_elevation():
    """CLEAR. Side elevation of the frame with a Surveyor at its foot for scale. The live sheave is bright, the dead one is not."""
    compound("overcast", course=False, post=False)
    S.machine(at=(-4.2, 1.0, 0), yaw=math.pi / 2)
    S.camera((-26, 1.0, 5.2), (0, 1.0, 5.2), focal=50)


@shot
def headframe_threequarter():
    """CLEAR. Three-quarter of the headframe, winch and cable from the south-west."""
    compound("overcast", course=False, post=False)
    S.machine(at=(-3.6, -2.0, 0), yaw=0.3)
    S.camera((-15, -13, 6.5), (0, 1.0, 5.0), focal=42)


@shot
def headframe_sheave():
    """CLEAR. The sheaves: the one still in use polished bright by the cable, the other rusted. 'Still in use is polished bright.'"""
    compound("overcast", course=False, post=False, yard=False)
    S.camera((-3.4, -2.6, 10.6), (0.35, 0.9, 10.3), focal=55)


@shot
def headframe_insitu():
    """IN-SITU. The frame against the overcast from the yard, cable running, cage descending."""
    compound("drizzle", cage_z=-1.4, flood=True)
    S.camera((-9.5, 12.0, 1.6), (0.0, 0.5, 5.5), focal=30)


# =====================================================================================
# A3 the yard
# =====================================================================================
def yard_machines(wreck=True):
    b = S.machine(at=(-7.2, 16.4, 0.0), yaw=-1.3, tag="charge")
    for k, ch in enumerate(("scout", "surveyor", "hauler", "swimmer")):
        S.machine(at=(-10.6 + k * 1.05, 17.9, 0.0), yaw=-math.pi / 2, chassis=ch, tag=f"rack{k}", wear=0.15, mud=0.1, dust=0.1)
    S.modules_on_bench((-9.1, 14.3, 0.90))
    if wreck:
        S.wreck(at=(-9.9, 14.35, 0.90), yaw=0.3)
    # charge cable from the wall box to the machine's port
    port = S.charge_port_world(b)
    end = S.plug(port, (-0.3, 0.9, 0.0))
    S.G.set_material(S.G.tube_along("charge_cable", [Vector((-4.55, 15.4, 1.15)), Vector((-5.4, 15.6, 0.05)), Vector((-6.6, 16.6, 0.03)), end], 0.008, verts=6, col=S.col()), S.rubber_black())
    return b


@shot
def yard_bench():
    """CLEAR. DAYLIGHT bench: four chassis on the floor, the seven modules on the bench, a recovered wreck being read, a machine on charge."""
    compound("overcast", course=False, post=False)
    yard_machines()
    S.camera((-13.0, 11.2, 1.75), (-8.6, 15.6, 0.7), focal=30)


@shot
def yard_overhead():
    """CLEAR. Overhead of the yard so the layout is settled once."""
    compound("overcast", course=False, post=False)
    yard_machines()
    S.camera((-8.0, 16.0, 16.0), (-8.0, 16.05, 0.0), focal=35)


@shot
def yard_modules():
    """CLEAR. The loadout as physical parts: sonar bar, lamp, hydrophone rail, beacon rack, magnetometer boom, cargo bay, monitor box."""
    compound("overcast", course=False, post=False, wh=True)
    yard_machines(wreck=False)
    S.camera((-9.1, 12.9, 1.45), (-9.1, 14.4, 0.95), focal=45)


@shot
def yard_wreck():
    """CLEAR. A recovered wreck on the bench: the visible loss of the extraction loop; the handle the only clean thing."""
    compound("overcast", course=False, post=False)
    yard_machines()
    S.camera((-10.9, 13.2, 1.35), (-9.9, 14.35, 0.98), focal=50, fstop=4.0)


@shot
def yard_insitu():
    """IN-SITU. Dusk-grey drizzle: a machine being loaded under the lean-to, the shaft and headframe beyond."""
    compound("dusk", course=False, flood=True)
    yard_machines(wreck=False)
    S.yard_light()
    S.EXPOSURE = 0.5
    S.camera((-11.5, 20.5, 1.5), (-4.0, 8.0, 1.2), focal=32)


# =====================================================================================
# A4 the course
# =====================================================================================
def course_scene(kind="overcast", roofed=None):
    C, pos, mouths = compound(kind, course=True, roofed=roofed)
    J = S.junctions(C, pos)
    return C, pos, J


def pick_junction(C, pos, J, want=2):
    """A junction close to the root with `want` onward passages, for the ground-level shots."""
    best = None
    for k, p, bearings in J:
        d = C.depth_of(k)
        if len(bearings) == want and (best is None or d < best[0]):
            best = (d, k, p, bearings)
    if best is None:
        _, k, p, bearings = 0, J[0][0], J[0][1], J[0][2]
    else:
        _, k, p, bearings = best
    return k, p, bearings


@shot
def course_oblique():
    """CLEAR. High oblique of the whole course so a human reads the maze: phase2 seed 54 at 0.6 m/cell, 110 x 130 m."""
    C, pos, J = course_scene()
    xs = [v[0] for v in pos.values()]; ys = [v[1] for v in pos.values()]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    S.camera((cx - 40, cy - 130, 95), (cx, cy, 0), focal=35)
    with open(os.path.join(HERE, "_course_proj.json"), "w") as f:
        json.dump({"nodes": {str(k): S.project([(p[0], p[1], 0.0)])[0][:2] for k, p in pos.items()},
                   "passages": [(p.near, p.far) for p in C.passages.values()], "shaft": C.shaft, "deposit": C.deposit}, f)


@shot
def course_ground():
    """CLEAR. What the machine sees at a junction: blind walls at head height, two ways on."""
    C, pos, J = course_scene()
    k, p, bearings = pick_junction(C, pos, J, 2)
    b0 = bearings[0]
    S.machine(at=(p[0] - 1.6 * math.cos(b0), p[1] - 1.6 * math.sin(b0), 0), yaw=b0)
    back = -0.5 * (Vector((math.cos(bearings[0]), math.sin(bearings[0]))) + Vector((math.cos(bearings[1]), math.sin(bearings[1]))))
    back.normalize()
    S.camera((p[0] + back.x * 3.2, p[1] + back.y * 3.2, 0.42), (p[0], p[1], 0.45), focal=28)


@shot
def course_human():
    """CLEAR. The same junction from a standing person's eye: the surface inverts the cave -- full information, and the walls are only 1.2 m."""
    C, pos, J = course_scene()
    k, p, bearings = pick_junction(C, pos, J, 2)
    b0 = bearings[0]
    S.machine(at=(p[0] - 1.6 * math.cos(b0), p[1] - 1.6 * math.sin(b0), 0), yaw=b0)
    back = -0.5 * (Vector((math.cos(bearings[0]), math.sin(bearings[0]))) + Vector((math.cos(bearings[1]), math.sin(bearings[1]))))
    back.normalize()
    S.camera((p[0] + back.x * 3.2, p[1] + back.y * 3.2, 1.7), (p[0], p[1], 0.3), focal=28)


@shot
def course_root():
    """CLEAR. The root bay: the 'shaft' beacon post and the machine set down at the start of a demonstration."""
    C, pos, J = course_scene()
    r = pos[C.shaft]
    first = C.passages[C.children(C.shaft)[0]]
    b = first.bearing
    S.machine(at=(r[0] + 0.3 * math.cos(b), r[1] + 0.3 * math.sin(b), 0), yaw=b)
    S.mannequin(at=(r[0] - 2.4 * math.cos(b) + 1.2 * math.sin(b), r[1] - 2.4 * math.sin(b) - 1.2 * math.cos(b), 0), yaw=b, pose="stand")
    S.camera((r[0] - 5.5 * math.cos(b) - 2.5 * math.sin(b), r[1] - 5.5 * math.sin(b) + 2.5 * math.cos(b), 2.1), (r[0], r[1], 0.6), focal=35)


@shot
def course_roofed():
    """ALTERNATIVE (design problem 3). A roofed, dark stretch of the course, the machine's lamp on inside it: where lamp / silt / ping blocks could be taught up here."""
    C, pos, J = course_scene(roofed=None)
    k, p, bearings = pick_junction(C, pos, J, 2)
    pid = C.children(k)[0]
    P_ = C.passages[pid]
    a, b = Vector(pos[P_.near]), Vector(pos[P_.far])
    d = b - a; L = d.length; u = d / L
    # roof this passage and its neighbours by hand
    for q in [pid] + C.children(P_.far):
        pp = C.passages[q]
        aa, bb = Vector(pos[pp.near]), Vector(pos[pp.far])
        c = (aa + bb) / 2; dd = bb - aa
        rf = S.G.box(f"roof.{q}", (dd.length - 2.0, S.COURSE_W + 0.6, 0.05), (c.x, c.y, S.WALL_H + 0.06), col=S.col())
        rf.rotation_euler = (0, 0, math.atan2(dd.y, dd.x))
        S.G.set_material(rf, S.hoarding())
    m = a + u * (L * 0.45)
    S.machine(at=(m.x, m.y, 0), yaw=math.atan2(u.y, u.x), lamp=400.0)
    cam = a + u * (L * 0.45) - u * 2.6
    S.camera((cam.x - u.y * 0.35, cam.y + u.x * 0.35, 0.45), (m.x + u.x * 2.0, m.y + u.y * 2.0, 0.2), focal=28)


# =====================================================================================
# A5 the shaft mouth
# =====================================================================================
@shot
def shaft_lookdown():
    """CLEAR. Looking down into the collar with the cage at the top and a machine in it. GUESS: the kibble on the modern winch, ~20 s down."""
    compound("overcast", course=False, post=False, yard=False, wh=False)
    S.machine(at=(0.0, 0.0, S.COLLAR_Z + 0.05), yaw=math.pi / 2, tag="incage")
    S.camera((1.2, -4.6, 4.6), (0.0, 0.0, 0.3), focal=35)


@shot
def shaft_collar():
    """CLEAR. The collar: cast ring on a stone plinth, guide rails, the fence, the hydrophone cable going over the edge, the hole."""
    compound("overcast", course=False, cage=False, yard=False, wh=False)
    S.camera((-4.6, -3.8, 1.75), (0.0, 0.0, 0.35), focal=40)


@shot
def shaft_hole():
    """CLEAR. Straight down the shaft from the collar: iron lining, then rock, then black. The flood is off; this is what daylight alone does."""
    compound("overcast", course=False, cage=False, yard=False, wh=False, post=False)
    S.camera((0.0, -0.3, 3.6), (0.0, 0.0, -30.0), focal=24)


@shot
def shaft_insitu():
    """IN-SITU. From the yard side: the cage three metres down, the machine's pale shell the last thing visible."""
    compound("drizzle", course=False, cage_z=-3.0, flood=True, yard=False, wh=False)
    S.machine(at=(0.0, 0.0, -3.0 + 0.05), yaw=math.pi / 2, tag="incage", emis=2.5)
    S.camera((-2.4, -3.6, 2.4), (0.0, 0.0, -1.2), focal=32)


@shot
def shaft_recovery():
    """CLEAR (A3/A5). A recovered wreck coming up in the cage: the loss of the extraction loop made visible at the surface, the next machine and the player waiting at the fence."""
    compound("overcast", course=False, yard=False, wh=False)
    S.wreck(at=(0.15, -0.05, S.COLLAR_Z + 0.06), yaw=0.5)
    S.machine(at=(-3.6, -1.4, 0), yaw=0.35, wear=0.45, mud=0.5, dust=0.3, scuff=0.3)
    S.mannequin(at=(-3.3, 2.2, 0), yaw=-0.55, pose="stand")
    S.camera((-4.4, -4.2, 2.0), (0.0, 0.0, 0.7), focal=40)


# =====================================================================================
# A6 the descent
# =====================================================================================
@shot
def descent_1_collar():
    """CLEAR strip 1/4. The cage at the collar, everything lit by sky, full authority."""
    compound("overcast", course=False, yard=False, wh=False, post=False, flood=True)
    S.machine(at=(0.0, 0.0, S.COLLAR_Z + 0.05), yaw=math.pi / 2, tag="incage")
    S.camera((-3.0, -1.6, 1.4), (0.0, 0.0, 0.9), focal=40)


@shot
def descent_2_halfway():
    """CLEAR strip 2/4. Camera inside the shaft: the cage passing, rock walls, the cold light from above."""
    compound("overcast", course=False, cage_z=-9.0, yard=False, wh=False, post=False, flood=True)
    S.machine(at=(0.0, 0.0, -9.0 + 0.05), yaw=math.pi / 2, tag="incage", emis=2.5)
    S.EXPOSURE = 2.0
    # in the gap between the cage rail and the wall (the cage posts are at +-0.82, +-0.67), looking
    # down over the rail at the machine on the grating. Light from straight above lights the
    # grating and the machine, not the walls, which are parallel to it: that is what a shaft is.
    S.camera((-0.25, -0.86, -7.15), (0.15, 0.1, -8.45), focal=22, clip_start=0.02)


@shot
def descent_3_lookup():
    """CLEAR strip 3/4. From inside the cage, looking straight up: the sky as a shrinking rectangle, the sheave deck in it, the bridle converging on the cable."""
    compound("overcast", course=False, cage_z=-7.0, yard=False, wh=False, post=False, flood=True)
    S.machine(at=(0.0, 0.0, -7.0 + 0.05), yaw=math.pi / 2, tag="incage", emis=2.5)
    S.EXPOSURE = 1.0
    S.camera((0.4, -0.45, -6.45), (0.05, 0.0, 12.0), focal=20, clip_start=0.02)


@shot
def descent_4_chamber():
    """CLEAR strip 4/4 (underground). Standing in the pool under the shaft: the one moment the machine is lit from above."""
    S.dark_world()
    S.underground(flood_w=4000.0, tube_top=24.0)
    S.machine(at=(0.9, 0.2, 0), yaw=0.4, tag="landed", emis=2.5)
    S.EXPOSURE = 1.0
    S.camera((-2.2, -2.6, 1.5), (0.7, 0.3, 0.6), focal=32)


@shot
def descent_insitu_lookup():
    """IN-SITU (underground). From the chamber floor looking up the shaft: the cage with the machine centred in the 12000 K rectangle, everything else black."""
    S.dark_world()
    S.underground(flood_w=4000.0, tube_top=24.0)
    apex = S.cage(12.0)
    for o in bpy.data.objects:
        if o.name.startswith(("cage", "bridle", "runner")):
            o.location = Vector(o.location) + Vector((0.6, 0.4, 0))
    S.machine(at=(0.6, 0.4, 12.05), yaw=math.pi / 2, tag="incage", emis=2.5)
    S.camera((0.6, 0.4, 0.5), (0.6, 0.4, 30.0), focal=28)


@shot
def descent_insitu_leaving():
    """IN-SITU (underground). The 'leaving somewhere' image: the machine walking out of the pool of daylight into black, lamp on."""
    S.dark_world()
    S.underground(flood_w=4000.0, tube_top=24.0)
    S.machine(at=(1.6, 0.6, 0), yaw=0.15, walk=1.8, lamp=600.0, emis=2.5)
    S.camera((-1.6, -2.8, 1.1), (2.6, 0.9, 0.35), focal=35)


# =====================================================================================
# A7 sky, weather, time of day
# =====================================================================================
def _sky_frame(kind):
    compound(kind, course=False, yard=True, wh=True, flood=(kind in ("dusk", "night", "rain")))
    if kind in ("dusk", "night"):
        S.yard_light()
        S.EXPOSURE = {"dusk": 0.5, "night": 1.5}[kind]
    S.machine(at=(-3.4, -0.3, 0), yaw=0.0)
    loc, aim = (-17.0, -9.5, 2.2), (0.0, 1.0, 5.6)
    S.camera(loc, aim, focal=28)
    if kind == "rain":
        S.rain_card(loc, aim)


@shot
def sky_overcast():
    """A7. Flat overcast, the default: the surface's light is the shaft's 12000 K."""
    _sky_frame("overcast")


@shot
def sky_drizzle():
    """A7. Drizzle: everything wet, the sky lower."""
    _sky_frame("drizzle")


@shot
def sky_rain():
    """A7. Heavy rain, the flooding season's tell; streaks are a card in front of the lens, an experiment."""
    _sky_frame("rain")


@shot
def sky_dusk():
    """A7. Dusk: the flood on, the sky nearly gone."""
    _sky_frame("dusk")


@shot
def sky_sun():
    """A7 ALTERNATIVE. Low sun for comparison. The direction says the rendered world has no sun; this frame is what breaking that costs."""
    _sky_frame("sun")


@shot
def sky_night():
    """A7 / G5. Night: the yard work light, the shaft flood and the terminal are the only light on the surface -- and the surface is allowed them."""
    _sky_frame("night")


@shot
def rain_shell():
    """A7 IN-SITU. Rain on a machine's shell at the collar: the wet pale shell, the hole behind."""
    compound("rain", course=False, yard=False, wh=False, flood=True)
    S.machine(at=(-3.0, 0.0, 0), yaw=0.0, wear=0.5, mud=0.6, dust=0.3, scuff=0.4)
    loc, aim = (-4.4, -1.5, 0.75), (-2.9, 0.0, 0.35)
    S.camera(loc, aim, focal=50, fstop=4.0)
    S.rain_card(loc, aim, dist=0.7, density=0.965)


# =====================================================================================
# A8 the surface end of the acoustic link
# =====================================================================================
@shot
def link_post():
    """CLEAR. The listening post: cable drum, the hydrophone going over the collar, the belief map on the post's screen."""
    compound("overcast", course=False, yard=False, wh=False)
    S.camera((-6.4, -6.2, 1.6), (-2.9, -2.6, 0.9), focal=40)


@shot
def link_insitu():
    """IN-SITU. The player at the post in rain, the map the only picture, the shaft black."""
    compound("rain", course=False, cage=False, yard=False, wh=False, flood=True)
    S.mannequin(at=(-3.2, -3.7, 0), yaw=math.pi / 2, pose="stand")
    loc, aim = (-7.2, -1.0, 1.55), (-3.2, -2.8, 1.05)
    S.camera(loc, aim, focal=35)
    S.rain_card(loc, aim)


# =====================================================================================
# D10 / A9 a machine in daylight
# =====================================================================================
@shot
def machine_daylight():
    """CLEAR. DAYLIGHT catalogue three-quarter of the Surveyor on the hardstanding: emissives vanish, the reflector is a dark disc, wear reads plainly."""
    compound("overcast", course=False, yard=False, wh=False, post=False, cage=False)
    S.machine(at=(-6.0, -4.0, 0), yaw=0.35, wear=0.45, mud=0.5, dust=0.35, scuff=0.35)
    S.camera((-4.35, -5.55, 0.62), (-6.0, -4.0, 0.30), focal=50, fstop=5.6)


@shot
def machine_fresh_veteran():
    """CLEAR. A fresh machine and a veteran side by side in daylight: history, not damage."""
    compound("overcast", course=False, yard=False, wh=False, post=False, cage=False)
    S.machine(at=(-6.0, -3.5, 0), yaw=0.35, team="fresh", wear=0.03, mud=0.0, dust=0.0, scuff=0.0, tag="fresh")
    S.machine(at=(-6.0, -4.6, 0), yaw=0.35, wear=0.85, mud=0.9, dust=0.7, scuff=0.7, tag="vet")
    S.camera((-4.2, -5.7, 0.75), (-6.0, -4.05, 0.28), focal=45, fstop=5.6)


@shot
def machine_lineup():
    """CLEAR. The four chassis abreast under DAYLIGHT on the hardstanding: Scout, Surveyor, Hauler, Swimmer (cross-ref D1)."""
    compound("overcast", course=False, yard=False, wh=False, post=False, cage=False)
    for k, ch in enumerate(("scout", "surveyor", "hauler", "swimmer")):
        S.machine(at=(-7.5 + k * 1.15, -6.0, 0), yaw=0.0, chassis=ch, tag=f"line{k}")
    S.camera((-5.8, -10.2, 1.1), (-5.8, -6.0, 0.28), focal=45)


@shot
def machine_rival_daylight():
    """CLEAR. Player and rival in daylight: the value inversion is all that is left when the emissives vanish."""
    compound("overcast", course=False, yard=False, wh=False, post=False, cage=False)
    S.machine(at=(-6.0, -3.5, 0), yaw=0.35, team="player", tag="pl")
    S.machine(at=(-6.0, -4.6, 0), yaw=0.35, team="rival", tag="rv")
    S.camera((-4.2, -5.7, 0.75), (-6.0, -4.05, 0.28), focal=45, fstop=5.6)


@shot
def machine_collar():
    """IN-SITU. The machine at the collar in drizzle, the shaft black behind it: the last image before commit."""
    compound("drizzle", course=False, cage=False, yard=False, wh=False, flood=False)
    S.machine(at=(-2.9, 0.0, 0), yaw=0.0, wear=0.5, mud=0.6, dust=0.3, scuff=0.4, lamp=300.0)
    S.camera((-5.2, -1.3, 0.55), (-1.4, 0.0, 0.25), focal=40, fstop=5.6)


# =====================================================================================
# G1 teaching at the course
# =====================================================================================
def teach_scene(kind="overcast", dead_end=False):
    C, pos, J = course_scene(kind)
    k, p, bearings = pick_junction(C, pos, J, 2)
    b_in = C.passages[C.nodes[k].parent].bearing
    # the machine stopped at the junction, head turned toward the passage it believes is there
    mp = (p[0] - 0.9 * math.cos(b_in), p[1] - 0.9 * math.sin(b_in))
    look_b = bearings[0]
    if dead_end:
        leaf = None
        for pid in C.children(k):
            if C.nodes[C.passages[pid].far].is_leaf:
                leaf = pid
        pid = leaf if leaf is not None else C.children(k)[0]
        P_ = C.passages[pid]
        e = Vector(pos[P_.far]); a = Vector(pos[P_.near]); u = (e - a).normalized()
        mp = (e.x - u.x * 1.7, e.y - u.y * 1.7)
        yaw = math.atan2(u.y, u.x)
        m = S.machine(at=(mp[0], mp[1], 0), yaw=yaw, look=(mp[0] - u.x * 2.0, mp[1] - u.y * 2.0, 0.3))
        left = Vector((-u.y, u.x))
        hp = Vector((mp[0], mp[1])) + left * (S.COURSE_W / 2 + 0.55) + u * 0.4
        hand = S.mannequin(at=(hp.x, hp.y, 0), yaw=math.atan2(-left.y, -left.x), pose="pendant")
        return C, pos, k, (mp[0], mp[1]), yaw, m, hand, u, left
    yaw = b_in
    m = S.machine(at=(mp[0], mp[1], 0), yaw=yaw, look=(p[0] + 2.0 * math.cos(look_b), p[1] + 2.0 * math.sin(look_b), 0.3))
    u = Vector((math.cos(b_in), math.sin(b_in)))
    left = Vector((-u.y, u.x))
    hp = Vector(mp) + left * (S.COURSE_W / 2 + 0.6) - u * 0.2
    hand = S.mannequin(at=(hp.x, hp.y, 0), yaw=math.atan2(-left.y, -left.x), pose="pendant")
    return C, pos, k, mp, yaw, m, hand, u, left


@shot
def teach_overshoulder():
    """CLEAR (G1). Over the player's shoulder at the wall: the machine stopped at a junction below, the pendant showing belief only. The stop is a question."""
    C, pos, k, mp, yaw, m, hand, u, left = teach_scene()
    port = S.charge_port_world(m)
    S.pendant(hand + Vector((0, 0, 0.02)), rot=(math.radians(50), 0, math.atan2(-left.y, -left.x) + math.pi / 2), screen_img=A.screen,
              cable_to=S.plug(port, (-0.6, 0.0, 0.2)))
    cam = Vector((hand.x, hand.y)) + left * 0.55 - u * 0.75
    S.camera((cam.x, cam.y, 2.05), (mp[0] + u.x * 0.2, mp[1] + u.y * 0.2, 0.55), focal=30)


@shot
def teach_wide():
    """CLEAR (G1). A wide of the demonstration: the player over the wall, the machine below, the course around them."""
    C, pos, k, mp, yaw, m, hand, u, left = teach_scene()
    port = S.charge_port_world(m)
    S.pendant(hand + Vector((0, 0, 0.02)), rot=(math.radians(50), 0, math.atan2(-left.y, -left.x) + math.pi / 2), screen_img=A.screen,
              cable_to=S.plug(port, (-0.6, 0.0, 0.2)))
    cam = Vector(mp) + left * 5.5 - u * 6.5
    S.camera((cam.x, cam.y, 4.2), (mp[0], mp[1], 0.6), focal=35)
    with open(os.path.join(HERE, "_teach_proj.json"), "w") as f:
        json.dump({"nodes": {str(kk): S.project([(pp[0], pp[1], 0.0)])[0][:2] for kk, pp in pos.items()},
                   "passages": [(p.near, p.far) for p in C.passages.values()], "shaft": C.shaft, "stop": k}, f)


@shot
def teach_insitu():
    """IN-SITU (G1). The same act in drizzle, late: the machine at a dead end turning back, the player following along the wall."""
    C, pos, k, mp, yaw, m, hand, u, left = teach_scene("drizzle", dead_end=True)
    port = S.charge_port_world(m)
    S.pendant(hand + Vector((0, 0, 0.02)), rot=(math.radians(50), 0, math.atan2(-left.y, -left.x) + math.pi / 2), screen_img=A.screen,
              cable_to=S.plug(port, (-0.6, 0.0, 0.2)))
    cam = Vector(mp) - u * 4.5 + left * 1.6
    S.camera((cam.x, cam.y, 1.5), (mp[0] + u.x * 1.2, mp[1] + u.y * 1.2, 0.45), focal=35)


# =====================================================================================
# G2 the interface in the world
# =====================================================================================
@shot
def pendant_product():
    """CLEAR (G2). The pendant on the bench, hand scale: screen, six block keys, scrub wheel, coiled cable. PROPOSAL."""
    compound("overcast", course=False, post=False)
    S.pendant((-8.55, 14.25, 0.916), rot=(0, 0, 0.25), screen_img=A.screen, cable_coiled=True)
    S.machine(at=(-9.9, 14.3, 0.90), yaw=-0.3, tag="onbench", wear=0.4, mud=0.4)
    S.camera((-8.35, 13.55, 1.32), (-8.55, 14.25, 0.92), focal=60, fstop=4.0)


@shot
def terminal_bench():
    """CLEAR (G2). The bench terminal: a rugged case with the tree, the sentence and the replay on its screen. PROPOSAL."""
    compound("overcast", course=False, post=False)
    S.pendant((-8.95, 14.15, 0.916), rot=(0, 0, 0.9), screen_img=A.screen, cable_coiled=True)
    S.camera((-7.6, 13.0, 1.45), (-8.25, 14.35, 1.05), focal=45, fstop=4.0)


@shot
def interface_collar():
    """IN-SITU (G2). The pendant plugged into the machine at the collar, the player crouched beside it: the last conversation before commit."""
    compound("drizzle", course=False, yard=False, wh=False, flood=True)
    m = S.machine(at=(-2.9, 0.0, 0), yaw=0.0, wear=0.5, mud=0.6, dust=0.3, scuff=0.4)
    hand = S.mannequin(at=(-3.4, -1.6, 0), yaw=math.pi / 2 + 0.3, pose="pendant")
    port = S.charge_port_world(m)
    S.pendant(hand + Vector((0, 0, 0.02)), rot=(math.radians(50), 0, math.pi / 2 + 0.3 + math.pi / 2), screen_img=A.screen,
              cable_to=S.plug(port, (-0.7, -0.3, 0.2)))
    S.camera((-6.2, -3.4, 1.5), (-3.0, -0.4, 0.6), focal=40)


@shot
def interface_terminal_dusk():
    """IN-SITU (G2 / G5). The terminal lit in the lean-to at dusk with a replay on it: the surface's one emissive."""
    compound("dusk", course=False, post=False, flood=True)
    yard_machines(wreck=False)
    S.E.add_light("SCREENGLOW", "AREA", (-8.25, 14.6, 1.3), 25.0, (0.55, 0.7, 0.9), size=0.5, aim=(-8.25, 13.5, 0.9))
    S.camera((-7.2, 12.4, 1.5), (-8.3, 14.4, 1.0), focal=40, fstop=4.0)


# =====================================================================================
# G3 the commit
# =====================================================================================
@shot
def commit_in():
    """CLEAR (G3). Macro: the pendant cable in the machine's charge port at the collar. Control is still a wire."""
    compound("overcast", course=False, yard=False, wh=False, post=False)
    m = S.machine(at=(-2.9, 0.0, 0), yaw=0.0, wear=0.5, mud=0.6, dust=0.3, scuff=0.4)
    port = S.charge_port_world(m)
    end = S.plug(port, (-0.75, -0.3, 0.1))
    S.G.set_material(S.G.tube_along("commit_cable", [end, end + Vector((-0.25, -0.1, -0.05)), end + Vector((-0.5, -0.35, -0.25)), Vector((-3.9, -1.2, 0.02))], 0.006, verts=6, col=S.col()), S.rubber_black())
    S.camera((-3.75, -0.55, 0.42), (port.x - 0.02, port.y, port.z), focal=70, fstop=3.5)


@shot
def commit_out():
    """CLEAR (G3). Macro: the cable out, the port empty, the cable coiled on the collar. The moment control leaves."""
    compound("overcast", course=False, yard=False, wh=False, post=False)
    m = S.machine(at=(-2.9, 0.0, 0), yaw=0.0, wear=0.5, mud=0.6, dust=0.3, scuff=0.4)
    port = S.charge_port_world(m)
    S.pendant((-3.45, -0.75, 0.02), rot=(0, 0, 0.6), screen_img=A.screen, cable_coiled=True)
    S.camera((-3.75, -0.55, 0.42), (port.x - 0.02, port.y, port.z), focal=70, fstop=3.5)


@shot
def commit_wide():
    """IN-SITU (G3). Cable coiled on the collar, cage gone, the player at the listening post, the shaft black."""
    compound("drizzle", course=False, cage=False, yard=False, wh=False, flood=False)
    S.pendant((-1.9, -0.2, 0.42), rot=(0, 0, 0.6), screen_img=A.screen, cable_coiled=True)
    S.mannequin(at=(-3.2, -3.7, 0), yaw=math.pi / 2, pose="stand")
    S.camera((-8.5, 3.5, 1.6), (-1.5, -1.5, 0.7), focal=35)


# =====================================================================================
# G4 the same stop underground (a truth half; the belief half is the P1 snap)
# =====================================================================================
@shot
def teach_cave_truth():
    """CLEAR (G4). The rendered truth of an underground stop: the machine halted at a junction of passage, lamp on, clock stopped. Next to it the player gets only the belief snap."""
    S.dark_world()
    rk = S.cave_rock(0.4)
    S.E.passage(width=3.4, height=4.6, length=22.0, mat=rk, seed=5, rubble=12)
    S.machine(at=(0, 0, 0), yaw=0.0, lamp=600.0, emis=2.5, look=(3.0, 1.2, 0.2))
    S.camera((-2.6, -1.7, 1.2), (1.6, 0.2, 0.3), focal=38)


# =====================================================================================
if A.list:
    for k, fn in SHOTS.items():
        print(f"{k:28s} {fn.__doc__}")
    raise SystemExit
if A.shot not in SHOTS:
    raise SystemExit(f"unknown shot {A.shot}; --list for names")
fresh()
SHOTS[A.shot]()
S.render(A.out or os.path.join(HERE, f"_{A.shot}.png"), samples=A.samples, res=RES, exposure=S.EXPOSURE)
