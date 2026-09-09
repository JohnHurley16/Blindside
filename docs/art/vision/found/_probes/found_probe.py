"""Vision-board probes for WHAT IS FOUND: deposits, wrecks, beacons, discoveries.

  blender -b -P docs/art/vision/found/_probes/found_probe.py -- --shot <name> --out <abs>.png

Every concept gets a CLEAR view (studio rig: the thing can be seen) and an IN-SITU view
(world background 0, diegetic light only). Shots are listed in SHOTS at the foot.

Nothing here modifies agent_model, phase1 or the other probes; the three agent fixes
(lamp aim, lamp colour, emissive strength/colour) are applied at runtime in found_common.
"""
import argparse
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import bpy  # noqa: E402
from mathutils import Vector, Euler  # noqa: E402

import found_common as F  # noqa: E402
from found_common import G, E, P  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--shot", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--samples", type=int, default=40)
ap.add_argument("--res", default="960x600")
A = ap.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
RES = tuple(int(v) for v in A.res.split("x"))
S = A.shot
LOOK = "AgX - Medium High Contrast"
EXPO = 0.0


def clear_floor(size=16.0, gauge=True):
    fl = F.ground(size=size, albedo=0.34, disp=0.03, name="studio_floor")
    if gauge:
        F.gauge_lines(-size * 0.4, size * 0.4)
    return fl


# =====================================================================================
# E1  DEPOSIT -- a worked face and the muck pile under it (ART-DIRECTION 6.1)
# =====================================================================================
def deposit_set(clear, scar=False, spoil=False, face_x=4.6):
    """The face along +X, the talus cone at its foot spread toward the camera."""
    rock = E.rock("country", albedo_lo=0.045, albedo_hi=0.30, warm=1.0, wet=0.35)
    ore = F.ore_rock("ore")
    if clear:
        F.clear_rig(key_from=(-4.0, -8.0, 7.0), aim=(2.0, 0, 1.0), key_w=2600.0, key_size=5.0, fill_w=300.0)
        F.ground(size=30.0, albedo=0.30, disp=0.10, rock=rock)
    else:
        F.insitu(fog=0.012)
        E.chamber(radius=7.5, height=7.0, mat=rock, seed=11, rubble=14)
    F.working_face("face", (face_x, 0, 0), width=8.5, height=4.6, yaw_deg=180.0, mat=rock, mat_ore=ore,
                   scar=(1.4, 1.5, 0.75) if scar else None)
    F.rubble_cone("talus", (face_x - 1.6, 0.2, 0), radius=3.6, height=1.15, n=220, mat=ore, seed=4)
    if spoil:
        # what loading leaves: a fresh pile of fines and small stock beside the cone, in the
        # scar's own un-silted rock, so it reads NEWER than the heap it came from
        fresh = E.rock("spoil_rock", albedo_lo=0.10, albedo_hi=0.42, warm=1.0, wet=0.1, fracture_scale=18.0, bump=0.7)
        F.rubble_cone("spoil", (face_x - 2.3, -2.7, 0), radius=1.0, height=0.36, n=70, mat=fresh, seed=8,
                      r_lo=0.02, r_hi=0.09)
    return rock, ore


if S == "dep_clear_face":
    # CLEAR: the face, the drill holes (three charged), the talus cone, a Surveyor loading
    # at its foot with the belly bay open. Not the game: the thing can be seen.
    F.fresh()
    deposit_set(clear=True)
    b = F.agent("player", at=(-0.4, -2.9, 0), yaw_deg=40.0, lamp=0.0)
    F.open_hatch(b.collection, deg=65.0)
    F.ore_lumps("held", (-0.45, -2.9, 0), n=8, radius=0.22, mat=F.ore_rock("ore2"), z0=0.0)
    F.camera((-6.0, -8.0, 3.0), (1.8, -0.6, 1.1), focal=40)

elif S == "dep_clear_after":
    # CLEAR: the same face after loading: a fresh scar on the face (brighter, sharper,
    # un-silted) and a new spoil pile under it. A rival can see this has been worked.
    F.fresh()
    deposit_set(clear=True, scar=True, spoil=True)
    F.camera((-4.5, -6.5, 2.6), (3.0, -0.6, 1.2), focal=42)

elif S in ("dep_clear_swatch_lit", "dep_clear_swatch_unlit"):
    # Two slabs: country rock (left), ore (right). ONLY when a lamp is on them is the ore
    # redder, glassier, more specular. Unlit under the studio's flat grey they are the same
    # rock family -- which is the rule: you find it by shining a light at it.
    F.fresh()
    rock = E.rock("country", albedo_lo=0.045, albedo_hi=0.30, warm=1.0, wet=0.35)
    ore = F.ore_rock("ore")
    F.clear_rig(key_w=0.0 if S.endswith("lit") else 0.0, bg=0.22, fill_w=0.0)
    F.ground(size=6.0, albedo=0.20, disp=0.0, name="bench")
    for i, (m, x) in enumerate(((rock, -0.55), (ore, 0.55))):
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=(x, 0, 0.22))
        s = bpy.context.object
        s.name = f"slab{i}"
        s.scale = (0.9, 0.7, 0.44)
        bpy.ops.object.transform_apply(scale=True)
        sub = s.modifiers.new("subsurf", "SUBSURF")
        sub.levels = sub.render_levels = 3
        E._displace(s, 0.35, 0.12, depth=5)
        s.data.shade_smooth()
        G.set_material(s, m)
    if S.endswith("_lit"):
        E.add_light("lamp", "SPOT", (-1.6, -2.4, 1.1), 260.0, F.LAMP_WHITE, size=0.05, spot_deg=55, blend=0.4, aim=(0, 0, 0.3))
    F.camera((0.1, -2.9, 1.25), (0, 0, 0.25), focal=50)

elif S == "dep_clear_plan":
    # CLEAR plan: the face and the cone from above, orthographic, with the 1.2 m module drawn
    # on the floor so the 7.2 m DEPOSIT_RADIUS reads as a heap, not a point.
    F.fresh()
    deposit_set(clear=True, scar=False)
    gm = F.flat("grid_paint", (0.75, 0.72, 0.62), rough=0.7)
    for k in range(-6, 7):
        G.set_material(G.box(f"gx{k}", (14.0, 0.02, 0.004), (0.0, k * 1.2, 0.006)), gm)
        G.set_material(G.box(f"gy{k}", (0.02, 14.0, 0.004), (k * 1.2, 0.0, 0.006)), gm)
    F.agent("player", at=(0.2, -2.6, 0), yaw_deg=40.0, lamp=0.0)
    F.camera((-0.2, 0.02, 16.0), (-0.2, 0.0, 0.0), focal=50, ortho=13.0)

elif S == "dep_situ_find":
    # IN-SITU: the lamp finds the pile. Camera behind and low; the machine between the
    # viewer and its own pool (the 2.4 camera rule); the ore glints where nothing else does.
    F.fresh()
    deposit_set(clear=False)
    b = F.agent("player", at=(-2.2, -0.3, 0), yaw_deg=8.0, lamp=600.0, aim_down=8.0)
    F.camera((-4.6, -1.6, 0.62), (0.6, 0.0, 0.45), focal=38)

elif S == "dep_situ_loading":
    # IN-SITU: loading. The machine in profile at the foot of the cone, bay sprung, stock on
    # the floor under it, its lamp on the pile 1.7 m ahead: the thirty seconds during which
    # the whole cave can hear it. The pile bounces the pool back onto the open belly.
    # (The first version put the camera inside a chamber rubble lump: a black frame.)
    F.fresh()
    deposit_set(clear=False)
    b = F.agent("player", at=(-1.3, -0.9, 0), yaw_deg=18.0, lamp=600.0, aim_down=15.0)
    F.open_hatch(b.collection, deg=70.0)
    F.ore_lumps("held", (-1.35, -0.9, 0), n=9, radius=0.24, mat=F.ore_rock("ore2"), z0=0.0)
    F.clear_near((-0.9, -3.4, 0.55), 1.6)
    F.camera((-0.9, -3.4, 0.55), (-0.4, -0.5, 0.35), focal=38, fstop=8.0)

elif S == "dep_situ_worked":
    # IN-SITU: the rival arrives later. Its lamp finds the scar and the spoil pile: the
    # deposit has been worked, told entirely by art, with no UI.
    F.fresh()
    deposit_set(clear=False, scar=True, spoil=True)
    b = F.agent("rival", at=(-1.0, -1.7, 0), yaw_deg=8.0, lamp=600.0, aim_down=1.0)
    F.camera((-2.7, -3.0, 0.7), (3.0, -1.4, 1.0), focal=38)

# =====================================================================================
# E2  WRECK (ART-DIRECTION 6.2)
# =====================================================================================
def wreck_set(clear, at=(0, 0, 0), spill=True):
    if clear:
        F.clear_rig(key_from=(2.0, -3.5, 3.2), aim=(0, 0, 0.15), key_w=900.0)
        clear_floor(size=10.0)
    else:
        F.insitu(fog=0.03)
        rk = E.rock("cave_rock", albedo_lo=0.045, albedo_hi=0.30, warm=1.0, wet=0.35)
        E.passage(width=3.6, height=4.8, length=22.0, mat=rk, seed=5, rubble=12)
    ch = P.CHASSIS["surveyor"]
    old = ch.ride_height
    ch.ride_height = 0.055                 # belly on the rock, as av_probe: built low, then posed
    w = F.agent("wreck", at=at, lamp=0.0, name="WRECK")
    # the pose override drops the body by hand exactly as av_probe does; WreckSpec is the
    # missing parameter (roll AND per-leg pose, a hull ground-contact solve, shed, spill).
    F.pose_wreck(w, at=at)
    F.open_hatch(w.collection, deg=80.0)
    if spill:
        F.ore_lumps("spill", (at[0] + 0.05, at[1] + 0.40, at[2]), n=14, radius=0.30, mat=F.ore_rock("ore"), z0=at[2])
    ch.ride_height = old
    return w


if S == "wreck_clear_front":
    # CLEAR: av_10's pose, front three-quarter, studio: belly on the rock, rolled 40 deg so
    # the underside shows, one leg gone below the knee, the compute hatch on the floor, the
    # cargo hatch sprung and ore spilled, every emissive dead. The gauge for scale.
    F.fresh()
    wreck_set(clear=True)
    F.camera((-1.35, -1.55, 0.70), (0.0, -0.05, 0.10), focal=50, fstop=8.0)

elif S == "wreck_clear_back":
    # CLEAR: the reverse three-quarter, from the rolled-up side: the underside, the
    # missing tibia, the splayed feet.
    F.fresh()
    wreck_set(clear=True)
    F.camera((1.45, 1.30, 0.75), (0.0, 0.0, 0.10), focal=50, fstop=8.0)

elif S == "wreck_clear_handle":
    # CLEAR macro: the recovery handle is the only clean thing on it.
    F.fresh()
    wreck_set(clear=True, spill=False)
    F.camera((-0.30, -0.62, 0.52), (0.02, -0.02, 0.30), focal=90, fstop=4.0)

elif S == "wreck_situ_found":
    # IN-SITU: a passing machine's lamp finds it at 1.7 m (av_10, with the spill). Nothing
    # else in frame emits. A hole where a light should be.
    F.fresh()
    w = wreck_set(clear=False)
    E.add_light("passing", "SPOT", (-1.75, -1.35, 0.55), 600.0, F.LAMP_WHITE, size=0.05, spot_deg=54, blend=0.5, aim=(0.05, 0, 0.04))
    F.camera((-1.15, -1.30, 0.30), (0.02, 0, 0.07), focal=48, fstop=5.0)

elif S == "wreck_situ_6m":
    # IN-SITU: a rival's lamp finds it at 6 m. The rival is a silhouette at the frame edge;
    # the wreck is a low shape in the far half of the pool. Retroreflective bands would make
    # it APPEAR all at once here (decision 1); rendered with the strips dead, as built.
    F.fresh()
    w = wreck_set(clear=False, at=(4.6, 0.2, 0))
    r = F.agent("rival", at=(-1.4, -0.5, 0), yaw_deg=6.0, lamp=600.0, aim_down=3.0, name="RIVAL")
    F.camera((-2.6, -1.9, 0.75), (2.6, 0.0, 0.25), focal=40)

elif S == "wreck_situ_pair":
    # IN-SITU: a healthy machine and a wreck side by side, backlit by a third machine's lamp
    # from behind them, for the nine-pixel ladder: a flat thing where a tall thing should be.
    F.fresh()
    w = wreck_set(clear=False, at=(0.0, -0.9, 0), spill=True)
    h = F.agent("player", at=(0.0, 0.9, 0), yaw_deg=0.0, lamp=0.0, name="HEALTHY")
    E.add_light("behind", "SPOT", (3.2, 0.0, 0.55), 700.0, F.LAMP_WHITE, size=0.05, spot_deg=60, blend=0.5, aim=(-1.2, 0.0, 0.05))
    F.camera((-3.4, 0.0, 0.55), (0.6, 0.0, 0.22), focal=40)

elif S == "wreck_situ_recovery":
    # IN-SITU: the recovery. A machine standing over the wreck, head down, doing nothing
    # visible for a long time while the whole cave can hear it. Its own lamp lights the
    # corpse under its chin. Do not put a glowing brain in it.
    F.fresh()
    w = wreck_set(clear=False, at=(0.0, 0.0, 0))
    b = F.agent("player", at=(-0.72, -0.05, 0), yaw_deg=0.0, lamp=600.0, aim_down=38.0, name="RECOVER")
    F.head_down(b, at=(-0.72, -0.05, 0), dz=0.12)
    F.camera((-1.5, -1.7, 0.75), (-0.2, 0.0, 0.18), focal=45, fstop=6.0)

# =====================================================================================
# E3  BEACON (ART-DIRECTION 6.3)
# =====================================================================================
if S == "bcn_clear_product":
    # CLEAR product shot: a 230 x 60 mm cast tube on a weighted self-righting base, one warm
    # pilot at the top, a retroreflective band. A 24 mm coin and a 100 mm bar for scale.
    F.fresh()
    F.clear_rig(key_from=(0.5, -0.8, 0.9), aim=(0, 0, 0.11), key_w=60.0, key_size=0.8, fill_w=8.0)
    bench = G.plane("bench", 2.0, (0, 0, 0))
    G.set_material(bench, F.flat("bench_m", (0.28, 0.27, 0.25), rough=0.6))
    F.beacon("B", (0, 0, 0), pilot=1.0)
    coin = G.cyl("coin", 0.012, 0.012, 0.002, (0.11, -0.07, 0.001), verts=32)
    G.set_material(coin, F.bearing_steel("coin_m"))
    bar = G.box("bar", (0.100, 0.006, 0.002), (-0.03, -0.12, 0.001))
    G.set_material(bar, F.flat("bar_m", (0.85, 0.83, 0.78), rough=0.5))
    # far enough back that the whole object, the coin and the bar are in frame (the first
    # version filled the frame with 120 mm of tube and nothing else)
    F.camera((0.55, -0.70, 0.34), (0.02, -0.03, 0.10), focal=45, fstop=5.6)

elif S == "bcn_clear_rack":
    # CLEAR macro: the beacon rack as agent_model builds it -- four deck tubes and caps and
    # the chute at the tail. The caps are the inventory readout (they go dark one at a time).
    F.fresh()
    F.clear_rig(key_from=(-1.2, -1.4, 1.5), aim=(-0.22, 0, 0.5), key_w=260.0, key_size=1.2, fill_w=40.0)
    clear_floor(size=6.0, gauge=False)
    b = F.agent("player", at=(0, 0, 0), lamp=0.0)
    F.camera((-0.72, -0.48, 0.66), (-0.20, 0.0, 0.46), focal=85, fstop=5.6)

elif S == "bcn_clear_drop":
    # CLEAR: the moment of a drop. One beacon mid-fall behind the chute, one already down and
    # righted 1.4 m back, the machine walking on. Beacon positions are taken from where the
    # body IS at the rendered frame, not where the walk ends.
    F.fresh()
    F.clear_rig(key_from=(1.5, -3.5, 3.0), aim=(0, 0, 0.3), key_w=900.0)
    clear_floor(size=10.0)
    b = F.agent("player", at=(0, 0, 0), lamp=0.0)
    from agent_model.motion import Mover
    m = Mover(b)
    m.stand(0.2)
    m.walk(1.2, speed=0.45, gait="trot")
    m.finish()
    bpy.context.scene.frame_set(int(m.frame * 0.75))
    bpy.context.view_layer.update()
    px = float(b.arm.matrix_world.translation.x)
    print(f"drop: body at x={px:.2f} at frame {int(m.frame * 0.75)} of {m.frame}")
    F.beacon("Bfall", (px - 0.40, 0.02, 0.15), pilot=1.0, tilt=(0.45, 0.25, 0.0))
    F.beacon("Bdown", (px - 1.45, 0.08, 0.0), pilot=1.0)
    F.camera((px - 0.75, -2.3, 0.55), (px - 0.55, 0.0, 0.22), focal=40, fstop=8.0)

elif S == "bcn_situ_chain":
    # IN-SITU: the most beautiful image the game has. The machine 9 m ahead, walking away,
    # a silhouette against its own pool (the 2.4 camera rule); the chain it dropped between
    # it and the lens, nearest pilot 1.4 m away, four warm points receding. One of them may
    # be lying. WARM_DIM pilots, never team-coloured. (The first version looked the other
    # way, at a machine whose pool was out of frame: a black frame with five dots in it.)
    F.fresh()
    F.insitu(fog=0.012)
    rk = E.rock("cave_rock", albedo_lo=0.045, albedo_hi=0.30, warm=1.0, wet=0.4)
    E.passage(width=3.4, height=4.6, length=40.0, mat=rk, seed=5, rubble=16)
    # pilots: strength 3 with a bloom stand-in (F.beacon halo), and a 1.4 W point each so a
    # cap and a band show within 0.3 m of every pilot -- both board licences, flagged
    b = F.agent("player", at=(7.0, 0.1, 0), yaw_deg=0.0, lamp=600.0, aim_down=9.0)
    for i, (x, y) in enumerate(((1.3, -0.45), (2.9, 0.40), (4.5, -0.35), (6.1, 0.45))):
        F.beacon(f"B{i}", (x, y, 0.0), pilot=4.0, halo=1.0)
    F.clear_near((0.0, 0.0, 0.34), 1.4)
    F.camera((0.0, 0.0, 0.34), (5.0, 0.0, 0.25), focal=30)

elif S == "bcn_situ_range":
    # IN-SITU: useful to 3.6 m, visible to 20 m. The near beacon stands in the pool and its
    # body and band read; the far one is a pilot and nothing else.
    F.fresh()
    F.insitu(fog=0.012)
    rk = E.rock("cave_rock", albedo_lo=0.045, albedo_hi=0.30, warm=1.0, wet=0.4)
    E.passage(width=3.4, height=4.6, length=44.0, mat=rk, seed=6, rubble=16)
    b = F.agent("player", at=(0.0, 0.0, 0), yaw_deg=0.0, lamp=600.0, aim_down=8.0)
    F.beacon("near", (2.6, -0.5, 0.0), pilot=1.3)
    F.beacon("far", (20.0, 0.35, 0.0), pilot=1.3)
    F.clear_near((-0.9, -1.15, 0.5), 1.0)
    F.camera((-0.9, -1.15, 0.50), (3.2, -0.25, 0.25), focal=32)

elif S == "bcn_situ_twins":
    # IN-SITU: an honest beacon and a spoofed one, side by side in the lamp. Pixel-identical:
    # the same function, the same arguments. No tell. Not a subtle one.
    F.fresh()
    F.insitu(fog=0.012)
    rk = E.rock("cave_rock", albedo_lo=0.045, albedo_hi=0.30, warm=1.0, wet=0.4)
    E.passage(width=3.4, height=4.6, length=22.0, mat=rk, seed=7, rubble=10)
    b = F.agent("player", at=(-1.8, 0.0, 0), yaw_deg=0.0, lamp=600.0, aim_down=12.0)
    F.beacon("honest", (1.1, 0.32, 0.0), pilot=1.0)
    F.beacon("spoof", (1.1, -0.32, 0.0), pilot=1.0)
    F.camera((-0.55, -0.85, 0.42), (1.1, 0.0, 0.14), focal=55, fstop=6.0)

elif S == "bcn_situ_sump":
    # IN-SITU: a beacon left in a live sump (THE BUS, ART-DIRECTION 5.6 / 6.3). A shallow
    # flooded section: the beacon stands in it, base and band under the water, pilot dry and
    # lit; the bare conductor on white porcelain along the haunch above is the tell that this
    # water is live; the water goes from a mirror to faintly self-lit (a corona, 2100 K at
    # 0.03 linear: a proposal). It comes back wrong rather than dead, and keeps lying.
    # The lamp is 56 deg here (wider than the direction's 50) to hold the Bus and the sump
    # in one frame -- a board licence.
    F.fresh()
    F.insitu(fog=0.012)
    wl = -0.02
    rk = E.rock("cave_rock", albedo_lo=0.045, albedo_hi=0.30, warm=1.0, wet=0.5, waterline=wl)
    E.passage(width=3.6, height=4.6, length=22.0, mat=rk, seed=9, rubble=6)
    fl = bpy.data.objects.get("floor")
    if fl:
        for v in fl.data.vertices:
            if v.co.x > 0.6:
                v.co.z -= 0.15 * min(1.0, (v.co.x - 0.6) / 1.0)
    F.clear_near((1.9, 0.1, 0.0), 2.0)
    water = G.plane("water", 30.0, (15.6, 0, wl))
    m, nt, out = F._new("water_m")
    n, L = nt.nodes, nt.links.new
    g = n.new("ShaderNodeBsdfGlass")
    g.inputs["IOR"].default_value = 1.33
    g.inputs["Roughness"].default_value = 0.02
    bb = n.new("ShaderNodeBlackbody")
    bb.inputs["Temperature"].default_value = 2100.0
    em = n.new("ShaderNodeEmission")
    # faint: 0.008 linear, broken up by a slow noise so it reads as a shimmer on water and
    # not as an orange floor (0.03 flat did exactly that in the first version)
    nz = n.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 0.9
    nz.inputs["Detail"].default_value = 4.0
    mr = n.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = 0.35
    mr.inputs["From Max"].default_value = 0.75
    mr.inputs["To Min"].default_value = 0.002
    mr.inputs["To Max"].default_value = 0.012
    mr.clamp = True
    L(nz.outputs["Fac"], mr.inputs["Value"])
    L(mr.outputs["Result"], em.inputs["Strength"])
    L(bb.outputs[0], em.inputs["Color"])
    add = n.new("ShaderNodeAddShader")
    L(g.outputs[0], add.inputs[0])
    L(em.outputs[0], add.inputs[1])
    L(add.outputs[0], out.inputs[0])
    G.set_material(water, m)
    # the Bus along the haunch: brackets off the wall, a white insulator on each, the bare
    # conductor resting on them
    # low on the haunch (1.7 m: this is a natural passage, not a 2.4 m drive) so one 56 deg
    # lamp aimed at the beacon holds the insulators in its upper edge
    cond = G.box("bus", (20.0, 0.03, 0.05), (5.0, 1.30, 1.74))
    G.set_material(cond, F.cast_iron("bus_iron"))
    for k in range(8):
        x = -3.0 + k * 2.4
        br = G.box(f"br{k}", (0.06, 0.60, 0.06), (x, 1.58, 1.55))
        G.set_material(br, F.cast_iron(f"br_iron{k}"))
        ins = G.cyl(f"ins{k}", 0.05, 0.05, 0.14, (x, 1.30, 1.65), verts=14)
        G.set_material(ins, F.porcelain(f"por{k}"))
    F.beacon("inwater", (1.9, 0.10, wl - 0.14), pilot=1.6, halo=0.6)
    b = F.agent("player", at=(-0.7, -0.35, 0), yaw_deg=8.0, lamp=600.0, aim_down=3.0)
    if b.lamp:
        b.lamp.data.spot_size = math.radians(56)
    F.camera((-0.25, -1.35, 0.72), (1.9, 0.45, 0.55), focal=30, fstop=8.0)

elif S == "bcn_situ_spoof":
    # IN-SITU: the spoof as an act, not a tell. A rival machine (EMBER strips) walks the
    # player's chain and drops one of its own among them -- mid-fall at its chute -- with its
    # pool on the player's next beacon. Every beacon in frame is the same object with the
    # same arguments; the display may go LIE-yellow after the fact, the world never may.
    F.fresh()
    F.insitu(fog=0.012)
    rk = E.rock("cave_rock", albedo_lo=0.045, albedo_hi=0.30, warm=1.0, wet=0.4)
    E.passage(width=3.4, height=4.6, length=30.0, mat=rk, seed=4, rubble=12)
    for i, x in enumerate((-0.4, 2.4, 5.2)):
        F.beacon(f"P{i}", (x, -0.5 + 0.4 * math.sin(i * 2.0), 0.0), pilot=1.3)
    r = F.agent("rival", at=(0.9, 0.35, 0), yaw_deg=0.0, lamp=600.0, aim_down=10.0, name="RIVAL")
    F.beacon("lie", (0.50, 0.38, 0.15), pilot=1.3, tilt=(0.4, 0.3, 0.0))
    F.clear_near((-1.6, -1.2, 0.5), 1.2)
    F.camera((-1.6, -1.2, 0.5), (2.2, 0.0, 0.25), focal=35)

# =====================================================================================
# E4  DISCOVERY -- the station, the pose, the mark that it is spent (ART-DIRECTION 6.4)
# =====================================================================================
def station_footing(at):
    """The Assayer's footing hub only: three splayed legs to anchor pads, a hex hub. The
    mast belongs to group C; the hub is the surface the transducer touches."""
    c = F.CELL
    col = G.new_collection("footing")
    iron = F.cast_iron("footing_iron")
    hub_r, hub_z, pad_r = 1.0 * c, 1.2 * c, 2.6 * c
    base = Vector(at)
    for k in range(3):
        a = math.radians(90 + 120 * k)
        top = base + Vector((math.cos(a) * hub_r, math.sin(a) * hub_r, hub_z))
        foot = base + Vector((math.cos(a) * pad_r, math.sin(a) * pad_r, 0.02))
        G.set_material(G.strut(f"leg{k}", top, foot, 0.34 * c, 0.30 * c, 0.46 * c, 0.22 * c, col=col, bevel=0.01), iron)
        G.set_material(G.box(f"pad{k}", (0.8 * c, 0.8 * c, 0.16 * c), foot + Vector((0, 0, 0.04)), bevel=0.01, col=col), iron)
    G.set_material(G.cyl("hub", hub_r * 1.15, hub_r * 0.95, 0.5 * c, base + Vector((0, 0, hub_z + 0.1 * c)), verts=6, bevel=0.01, col=col), iron)
    mast = G.cyl("mast_stub", 0.55, 0.50, 1.6, base + Vector((0, 0, hub_z + 0.35 * c + 0.8)), verts=6, col=col)
    G.set_material(mast, iron)
    return col


def station_junction(at, yaw_deg=0.0, spent=False):
    """A junction box on the Bus: a cast box on a wall bracket, the bare conductor entering
    on two white insulators, a hinged cover plate with a raised part number, one bright
    bearing-steel latch. SPENT (proposal): the cover hangs open on its hinge."""
    col = G.new_collection("junction")
    iron = F.cast_iron("jb_iron")
    a = math.radians(yaw_deg)
    R = Euler((0, 0, a))
    base = Vector(at)

    def put(o, m):
        o.rotation_euler = (R.to_matrix() @ o.rotation_euler.to_matrix()).to_euler()
        o.location = base + (R.to_matrix() @ (Vector(o.location) - base))
        G.set_material(o, m)
        return o
    box = put(G.box("jb_body", (0.22, 0.46, 0.60), base + Vector((0, 0, 1.30)), bevel=0.012, col=col), iron)
    for s in (1, -1):
        put(G.box(f"jb_rib{s}", (0.24, 0.03, 0.56), base + Vector((0, s * 0.19, 1.30)), col=col), iron)
    put(G.box("jb_bracket", (0.10, 0.30, 0.06), base + Vector((-0.12, 0, 1.02)), col=col), iron)
    for s in (1, -1):
        put(G.cyl(f"jb_ins{s}", 0.045, 0.045, 0.16, base + Vector((0.0, s * 0.12, 1.68)), verts=14, col=col), F.porcelain(f"jb_por{s}"))
    put(G.box("jb_cond", (0.03, 0.04, 6.0), base + Vector((0.0, 0.12, 4.7)), col=col), iron)
    put(G.box("jb_cond2", (0.03, 0.04, 6.0), base + Vector((0.0, -0.12, 4.7)), col=col), iron)
    put(G.cyl("jb_latch", 0.02, 0.02, 0.05, base + Vector((0.13, 0.17, 1.30)), rot=(0, math.pi / 2, 0), verts=12, col=col), F.bearing_steel("jb_steel"))
    # cover: hinged on the -Y edge
    if spent:
        cov = G.box("jb_cover", (0.02, 0.40, 0.50), base + Vector((0.16, -0.36, 1.10)), bevel=0.006, col=col)
        cov.rotation_euler = Euler((0.35, 0.0, a - 1.35))
        G.set_material(cov, iron)
    else:
        put(G.box("jb_cover", (0.02, 0.40, 0.50), base + Vector((0.12, 0, 1.30)), bevel=0.006, col=col), iron)
        # raised part number: three small plates
        for k in range(3):
            put(G.box(f"jb_num{k}", (0.006, 0.05, 0.08), base + Vector((0.135, -0.09 + k * 0.09, 1.42)), col=col), iron)
    return col


def station_switch(at, yaw_deg=0.0):
    """A rail switch: lever frame, counterweight, a throw rod to a stub of two rails at
    600 mm gauge on sleepers. The lever's pivot is the bright part."""
    col = G.new_collection("switch")
    iron = F.cast_iron("sw_iron")
    base = Vector(at)
    for k in range(4):
        G.set_material(G.box(f"sw_sleeper{k}", (0.11, 0.90, 0.055), base + Vector((-0.9 + k * 0.6, 0.6, 0.03)), col=col), iron)
    for s in (1, -1):
        G.set_material(G.box(f"sw_rail{s}", (2.6, 0.035, 0.055), base + Vector((0, 0.6 + s * 0.30, 0.085)), col=col), iron)
    G.set_material(G.box("sw_frame", (0.30, 0.20, 0.12), base + Vector((0, 0, 0.06)), bevel=0.01, col=col), iron)
    G.set_material(G.cyl("sw_pivot", 0.04, 0.04, 0.26, base + Vector((0, 0, 0.14)), rot=(math.pi / 2, 0, 0), verts=16, col=col), F.bearing_steel("sw_steel"))
    lever = G.strut("sw_lever", base + Vector((0, 0, 0.14)), base + Vector((-0.55, 0, 0.95)), 0.05, 0.06, 0.035, 0.04, col=col)
    G.set_material(lever, iron)
    G.set_material(G.sphere("sw_weight", 0.11, base + Vector((-0.55, 0, 0.95)), col=col, seg=16), iron)
    G.set_material(G.segment("sw_rod", base + Vector((0.12, 0, 0.10)), base + Vector((0.12, 0.30, 0.10)), 0.015, 0.015, col=col), iron)
    return col


def station_pump(at, yaw_deg=0.0):
    """A pump: a cast volute on a plinth, a flanged pipe up and away, a motor drum, a bright
    coupling. The pumps stopped when the industry left; this one is above the line."""
    col = G.new_collection("pump")
    iron = F.cast_iron("pump_iron")
    base = Vector(at)
    G.set_material(G.box("pm_plinth", (1.1, 0.7, 0.18), base + Vector((0, 0, 0.09)), bevel=0.01, col=col), iron)
    G.set_material(G.cyl("pm_volute", 0.34, 0.34, 0.30, base + Vector((0.2, 0, 0.48)), rot=(math.pi / 2, 0, 0), verts=24, bevel=0.01, col=col), iron)
    G.set_material(G.cyl("pm_motor", 0.20, 0.20, 0.55, base + Vector((-0.35, 0, 0.48)), rot=(0, math.pi / 2, 0), verts=20, bevel=0.01, col=col), iron)
    G.set_material(G.cyl("pm_coupling", 0.09, 0.09, 0.08, base + Vector((-0.02, 0, 0.48)), rot=(0, math.pi / 2, 0), verts=16, col=col), F.bearing_steel("pm_steel"))
    G.set_material(G.tube_along("pm_pipe", [base + Vector((0.2, 0, 0.82)), base + Vector((0.2, 0, 1.5)), base + Vector((0.2, 0.9, 2.1)), base + Vector((0.2, 2.0, 2.3))], 0.075, verts=12, col=col), iron)
    for k, z in enumerate((0.85, 1.45)):
        G.set_material(G.cyl(f"pm_flange{k}", 0.12, 0.12, 0.03, base + Vector((0.2, 0, z)), verts=16, col=col), iron)
    for k in range(4):
        a = k * math.pi / 2 + 0.4
        G.set_material(G.cyl(f"pm_bolt{k}", 0.014, 0.014, 0.05, base + Vector((0.2 + math.cos(a) * 0.4, math.sin(a) * 0.25, 0.20)), verts=8, col=col), iron)
    return col


if S == "disc_clear_stations":
    # CLEAR sheet: four stations in the casting language, left to right -- a Bus junction
    # box, a rail switch, a pump, the Assayer's footing -- with a Surveyor for scale. All one
    # idea: the prior industry's control surfaces. A discovery is not an object; these are
    # where the transaction happens.
    F.fresh()
    F.clear_rig(key_from=(-2.0, -9.0, 8.0), aim=(0.6, 0, 0.9), key_w=4200.0, key_size=6.0, fill_w=500.0)
    clear_floor(size=26.0)
    wall = G.box("wall", (0.4, 9.0, 4.4), (-4.6, 0.0, 2.2))
    G.set_material(wall, E.rock("wall_rock", albedo_lo=0.045, albedo_hi=0.30, warm=1.0, wet=0.3))
    station_junction((-4.4, 3.2, 0.0))
    station_switch((-2.6, 0.9, 0.0))
    station_pump((-1.2, -1.3, 0.0))
    station_footing((2.5, 0.0, 0.0))
    F.agent("player", at=(-0.4, -3.6, 0), yaw_deg=160.0, lamp=0.0)
    F.camera((3.2, -12.0, 4.0), (-0.6, 0.3, 1.0), focal=40)

elif S == "disc_clear_pose":
    # CLEAR: the pose at a junction box. Head down on the rock, still, for 80 s. The same
    # gesture as salvaging a wreck: I am listening to something that is not alive.
    F.fresh()
    F.clear_rig(key_from=(1.0, -3.5, 3.2), aim=(-0.4, 0, 0.5), key_w=900.0)
    clear_floor(size=10.0)
    wall = G.box("wall", (0.4, 6.0, 4.0), (-1.05, 0.0, 2.0))
    G.set_material(wall, E.rock("wall_rock", albedo_lo=0.045, albedo_hi=0.30, warm=1.0, wet=0.3))
    station_junction((-0.85, 0.0, 0.0))
    b = F.agent("player", at=(-0.05, 0.0, 0), yaw_deg=180.0, lamp=0.0)
    F.head_down(b, at=(-0.05, 0.0, 0), dz=0.13)
    F.camera((1.6, -1.9, 0.9), (-0.4, 0.0, 0.45), focal=50, fstop=8.0)

elif S == "disc_situ_pose":
    # IN-SITU: the same pose in its own lamp, which is aimed at the rock under its chin; the
    # near wall bounces enough back to show the machine; the box above it is at the edge of
    # the beam; the TONE it is broadcasting is a sound, and draws nothing.
    F.fresh()
    F.insitu(fog=0.015)
    rk = E.rock("cave_rock", albedo_lo=0.045, albedo_hi=0.30, warm=1.0, wet=0.4)
    E.passage(width=3.0, height=4.6, length=22.0, mat=rk, seed=5, rubble=10)
    station_junction((0.6, 1.25, 0.0), yaw_deg=-90.0)
    b = F.agent("player", at=(0.6, 0.38, 0), yaw_deg=90.0, lamp=600.0, aim_down=26.0)
    F.head_down(b, at=(0.6, 0.38, 0), dz=0.13)
    F.clear_near((-0.95, -0.55, 0.78), 1.3)
    F.camera((-0.95, -0.55, 0.78), (0.55, 0.75, 0.55), focal=35, fstop=6.0)

elif S == "disc_situ_spent":
    # IN-SITU, PROPOSAL: the mark that a small station is spent. Two junction boxes in one
    # lamp: the near one intact, the far one with its cover hanging open on the hinge --
    # somebody knocked here and took the report. Readable from across the passage,
    # permanently, the way a stopped Assayer is.
    F.fresh()
    F.insitu(fog=0.012)
    rk = E.rock("cave_rock", albedo_lo=0.045, albedo_hi=0.30, warm=1.0, wet=0.4)
    E.passage(width=3.0, height=4.6, length=22.0, mat=rk, seed=8, rubble=10)
    station_junction((1.0, 0.98, 0.0), yaw_deg=-90.0)
    j2 = station_junction((3.6, 0.98, 0.0), yaw_deg=-90.0, spent=True)
    b = F.agent("player", at=(-1.2, -0.4, 0), yaw_deg=20.0, lamp=600.0, aim_down=-4.0)
    F.camera((-2.2, -1.3, 0.9), (2.4, 0.9, 1.2), focal=40)

elif S == "disc_situ_rival":
    # IN-SITU: what a rival sees of a download: a machine head-down at the footing hub, still,
    # in the rival's lamp from 5 m. Its own lamp is on the floor under its chin. It is the
    # most committed, least deniable thing a machine can do.
    F.fresh()
    F.insitu(fog=0.015)
    rk = E.rock("cave_rock", albedo_lo=0.045, albedo_hi=0.30, warm=1.0, wet=0.4)
    E.chamber(radius=7.5, height=8.0, mat=rk, seed=12, rubble=12)
    station_footing((2.4, 0.0, 0.0))
    b = F.agent("player", at=(0.55, -0.9, 0), yaw_deg=25.0, lamp=600.0, aim_down=42.0, name="DL")
    F.head_down(b, at=(0.55, -0.9, 0), dz=0.13)
    r = F.agent("rival", at=(-4.6, -1.4, 0), yaw_deg=8.0, lamp=600.0, aim_down=2.0, name="RIVAL")
    F.camera((-5.6, -2.6, 0.7), (0.8, -0.6, 0.5), focal=40)

if bpy.context.scene.camera is None:
    raise SystemExit(f"unknown shot {S}")

F.render(A.out, samples=A.samples, res=RES, look=LOOK, exposure=EXPO)

SHOTS = [
    "dep_clear_face", "dep_clear_after", "dep_clear_swatch_lit", "dep_clear_swatch_unlit", "dep_clear_plan",
    "dep_situ_find", "dep_situ_loading", "dep_situ_worked",
    "wreck_clear_front", "wreck_clear_back", "wreck_clear_handle",
    "wreck_situ_found", "wreck_situ_6m", "wreck_situ_pair", "wreck_situ_recovery",
    "bcn_clear_product", "bcn_clear_rack", "bcn_clear_drop",
    "bcn_situ_chain", "bcn_situ_range", "bcn_situ_twins", "bcn_situ_sump", "bcn_situ_spoof",
    "disc_clear_stations", "disc_clear_pose", "disc_situ_pose", "disc_situ_spent", "disc_situ_rival",
]
