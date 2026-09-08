"""Agent-direction probes for ART-DIRECTION.md. Run with a Blender install:

  blender -b -P docs/art/agent/av_probe.py -- --shot lamp_fixed --out docs/art/agent/av_02.png

Every shot is lit ONLY by sources the fiction supplies. World background strength is 0.
The head lamp is re-aimed in this script (see `_fix_lamp`) because agent_model/build.py:312
aims it at -X, into the machine's own eye_lens at 14 mm. This probe does not modify
agent_model; another workflow owns that tree.

Shots
  lamp_asbuilt   the head lamp as agent_model builds it today
  lamp_fixed     identical frame, same power, lamp re-aimed +X. The two-character fix.
  wear_current   the isotropic noise-plus-AO wear mask that exists now
  wear_directed  three gravity-aware masks, extended to the lower-leg materials
  team_player    pale shell over graphite chassis
  team_rival     graphite shell over pale chassis  (the value inversion)
  team_hue       today's scheme: same value, team identity carried by emissive hue only
  sil_bare       bare chassis backlit by its own lamp pool
  sil_loaded     same frame, full loadout. The silhouette is the loadout readout.
  wreck          ride height 0, emissives dead, panels shed, one tibia gone
"""
import argparse
import math
import os
import sys

sys.path.insert(0, r"C:/Users/jackh/documents/programming/Blindside")

import bpy  # noqa: E402
from mathutils import Vector, Euler  # noqa: E402

from agent_model import params as P  # noqa: E402
from agent_model import geometry as G  # noqa: E402
from agent_model.build import build_agent  # noqa: E402

sys.path.insert(0, os.path.join(r"C:/Users/jackh/documents/programming/Blindside", "docs/art/probes"))
import p2_env as E  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--shot", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--samples", type=int, default=28)
ap.add_argument("--res", default="900x560")
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
A = ap.parse_args(argv)
RES = tuple(int(v) for v in A.res.split("x"))

# ---------------------------------------------------------------------------------------
# materials: directional wear
# ---------------------------------------------------------------------------------------
ROCK_DUST = (0.30, 0.265, 0.215)     # the cave's own dust: a machine wears the cave it walked
MUD = (0.085, 0.062, 0.040)          # wet mine mud. Lighter than graphite, so it READS on a
                                     # near-black leg -- the thing that matters is that it is
                                     # ochre and matte, not that it is dark.


def worn_metal(base, bare, accent, wear=0.35, grime=0.4, mud=0.0, dust=0.0, scuff=0.0,
               foot_z=0.0, name="worn"):
    """painted_metal plus three gravity-aware masks.

    mud    world-Z mask, saturated at the feet, gone above the hull seam.  'it walked here'
    dust   upward-normal mask, in the ROCK's colour, on every horizontal.  'it has been down a while'
    scuff  +X-facing normals x edge AO: paint off the leading faces only.  'it hit things'

    The existing mask is isotropic noise MAX inverted-AO: no gravity and no direction in it,
    which is why wear 0.0 and wear 0.35 differ by 0.003 mean luminance.
    """
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for nd in list(nt.nodes):
        nt.nodes.remove(nd)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    n, L = nt.nodes, nt.links.new
    b = n.new("ShaderNodeBsdfPrincipled")
    b.inputs["Metallic"].default_value = 0.3
    b.inputs["Coat Weight"].default_value = 0.35
    b.inputs["Coat Roughness"].default_value = 0.15

    geo = n.new("ShaderNodeNewGeometry")
    sep_n = n.new("ShaderNodeSeparateXYZ")
    sep_p = n.new("ShaderNodeSeparateXYZ")
    L(geo.outputs["Normal"], sep_n.inputs["Vector"])
    L(geo.outputs["Position"], sep_p.inputs["Vector"])

    # --- the existing isotropic term, unchanged, so this is additive not a replacement
    tex = n.new("ShaderNodeTexNoise")
    tex.inputs["Scale"].default_value = 70.0
    tex.inputs["Detail"].default_value = 8.0
    tex.inputs["Roughness"].default_value = 0.7
    ramp = n.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.70 - 0.22 * wear
    ramp.color_ramp.elements[1].position = 0.80 - 0.22 * wear
    L(tex.outputs["Fac"], ramp.inputs["Fac"])
    ao = n.new("ShaderNodeAmbientOcclusion")
    ao.inputs["Distance"].default_value = 0.02
    ao.inside = True
    invao = n.new("ShaderNodeMath")
    invao.operation = "SUBTRACT"
    invao.inputs[0].default_value = 1.0
    L(ao.outputs["AO"], invao.inputs[1])
    edge = n.new("ShaderNodeMath")
    edge.operation = "MULTIPLY"
    edge.inputs[1].default_value = 4.0 * wear
    L(invao.outputs[0], edge.inputs[0])
    wearmix = n.new("ShaderNodeMath")
    wearmix.operation = "MAXIMUM"
    L(ramp.outputs["Color"], wearmix.inputs[0])
    L(edge.outputs[0], wearmix.inputs[1])

    # --- scuff: +X normals only, times the edge term
    fwd = n.new("ShaderNodeMath")
    fwd.operation = "MAXIMUM"
    fwd.inputs[1].default_value = 0.0
    L(sep_n.outputs["X"], fwd.inputs[0])
    scuffm = n.new("ShaderNodeMath")
    scuffm.operation = "MULTIPLY"
    L(fwd.outputs[0], scuffm.inputs[0])
    L(invao.outputs[0], scuffm.inputs[1])
    scuffg = n.new("ShaderNodeMath")
    scuffg.operation = "MULTIPLY"
    scuffg.inputs[1].default_value = 3.0 * scuff
    L(scuffm.outputs[0], scuffg.inputs[0])
    allwear = n.new("ShaderNodeMath")
    allwear.operation = "MAXIMUM"
    L(wearmix.outputs[0], allwear.inputs[0])
    L(scuffg.outputs[0], allwear.inputs[1])

    base_n = n.new("ShaderNodeRGB")
    base_n.outputs[0].default_value = (*base, 1)
    bare_n = n.new("ShaderNodeRGB")
    bare_n.outputs[0].default_value = (*bare, 1)
    mix = n.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    L(allwear.outputs[0], mix.inputs["Factor"])
    L(base_n.outputs[0], mix.inputs["A"])
    L(bare_n.outputs[0], mix.inputs["B"])

    # --- dust: upward normals, in the rock's own colour
    up = n.new("ShaderNodeMath")
    up.operation = "MAXIMUM"
    up.inputs[1].default_value = 0.0
    L(sep_n.outputs["Z"], up.inputs[0])
    up3 = n.new("ShaderNodeMath")
    up3.operation = "POWER"
    up3.inputs[1].default_value = 3.0
    L(up.outputs[0], up3.inputs[0])
    dustn = n.new("ShaderNodeTexNoise")
    dustn.inputs["Scale"].default_value = 22.0
    dustv = n.new("ShaderNodeMath")
    dustv.operation = "MULTIPLY_ADD"
    dustv.inputs[1].default_value = 0.5
    dustv.inputs[2].default_value = 0.6
    L(dustn.outputs["Fac"], dustv.inputs[0])
    dustf = n.new("ShaderNodeMath")
    dustf.operation = "MULTIPLY"
    L(up3.outputs[0], dustf.inputs[0])
    L(dustv.outputs[0], dustf.inputs[1])
    dustg = n.new("ShaderNodeMath")
    dustg.operation = "MULTIPLY"
    dustg.inputs[1].default_value = dust
    L(dustf.outputs[0], dustg.inputs[0])
    dustmix = n.new("ShaderNodeMix")
    dustmix.data_type = "RGBA"
    dustmix.inputs["B"].default_value = (*ROCK_DUST, 1)
    L(mix.outputs["Result"], dustmix.inputs["A"])
    L(dustg.outputs[0], dustmix.inputs["Factor"])

    # --- mud: world Z, saturated at the feet. foot_z is the ground plane under this agent.
    mudr = n.new("ShaderNodeMapRange")
    mudr.inputs["From Min"].default_value = foot_z + 0.22
    mudr.inputs["From Max"].default_value = foot_z + 0.05
    mudr.inputs["To Min"].default_value = 0.0
    mudr.inputs["To Max"].default_value = 1.0
    mudr.clamp = True
    L(sep_p.outputs["Z"], mudr.inputs["Value"])
    mudn = n.new("ShaderNodeTexNoise")
    mudn.inputs["Scale"].default_value = 30.0
    mudv = n.new("ShaderNodeMath")
    mudv.operation = "MULTIPLY_ADD"
    mudv.inputs[1].default_value = 0.45
    mudv.inputs[2].default_value = 0.65
    L(mudn.outputs["Fac"], mudv.inputs[0])
    mudf = n.new("ShaderNodeMath")
    mudf.operation = "MULTIPLY"
    L(mudr.outputs["Result"], mudf.inputs[0])
    L(mudv.outputs[0], mudf.inputs[1])
    mudg = n.new("ShaderNodeMath")
    mudg.operation = "MULTIPLY"
    mudg.inputs[1].default_value = mud
    L(mudf.outputs[0], mudg.inputs[0])
    mudmix = n.new("ShaderNodeMix")
    mudmix.data_type = "RGBA"
    mudmix.inputs["B"].default_value = (*MUD, 1)
    L(dustmix.outputs["Result"], mudmix.inputs["A"])
    L(mudg.outputs[0], mudmix.inputs["Factor"])

    # --- grime in the crevices, as today
    gr = n.new("ShaderNodeTexNoise")
    gr.inputs["Scale"].default_value = 4.0
    gr.inputs["Detail"].default_value = 8.0
    grr = n.new("ShaderNodeValToRGB")
    grr.color_ramp.elements[0].position = 0.45
    grr.color_ramp.elements[1].position = 0.7
    grf = n.new("ShaderNodeMath")
    grf.operation = "MULTIPLY"
    grf.inputs[1].default_value = grime
    grm = n.new("ShaderNodeMix")
    grm.data_type = "RGBA"
    grm.inputs["B"].default_value = (0.02, 0.018, 0.015, 1)
    L(gr.outputs["Fac"], grr.inputs["Fac"])
    L(grr.outputs["Color"], grf.inputs[0])
    L(grf.outputs[0], grm.inputs["Factor"])
    L(mudmix.outputs["Result"], grm.inputs["A"])
    L(grm.outputs["Result"], b.inputs["Base Color"])

    # roughness: mud is matte, dust is matte
    rgh = n.new("ShaderNodeMath")
    rgh.operation = "MULTIPLY_ADD"
    rgh.inputs[1].default_value = 0.3
    rgh.inputs[2].default_value = 0.35
    L(gr.outputs["Fac"], rgh.inputs[0])
    rgh2 = n.new("ShaderNodeMath")
    rgh2.operation = "MAXIMUM"
    L(rgh.outputs[0], rgh2.inputs[0])
    L(mudg.outputs[0], rgh2.inputs[1])
    L(rgh2.outputs[0], b.inputs["Roughness"])

    bump = n.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.08
    L(tex.outputs["Fac"], bump.inputs["Height"])
    L(bump.outputs["Normal"], b.inputs["Normal"])
    L(b.outputs[0], out.inputs[0])
    return m


# ---------------------------------------------------------------------------------------
def _fix_lamp(built, energy=600.0, white=True, aim_down_deg=0.0):
    """Re-aim the head lamp. build.py:312 sets Euler((0, +pi/2, 0)), which takes the spot's
    local -Z to world -X: backwards, into eye_lens at 14 mm. Verified by raycast."""
    if not built.lamp:
        return
    built.lamp.rotation_euler = Euler((0, -math.pi / 2 + math.radians(aim_down_deg), 0))
    built.lamp.data.energy = energy
    if white:
        built.lamp.data.color = (1.00, 0.98, 0.95)


def _retint(shell, chassis, wear=0.35, mud=0.0, dust=0.0, scuff=0.0,
            legs_too=False, foot_z=0.0, accent=(0.85, 0.45, 0.10), bare=(0.45, 0.45, 0.47)):
    """Reassign hull materials. If legs_too, the lower leg gets a wear-capable material as
    well -- today tibia is 'carbon' and the foot is 'rubber', neither of which is
    painted_metal, so a mud mask inside painted_metal cannot reach the parts that touch mud."""
    m_shell = worn_metal(shell, bare, accent, wear, 0.4, mud, dust, scuff, foot_z, "av_shell")
    m_chas = worn_metal(chassis, bare, accent, wear, 0.5, mud, dust, scuff, foot_z, "av_chassis")
    # The leg stays graphite. Its wear term is low on purpose: a muddy leg is mud ON black,
    # not paint worn THROUGH to bright metal. Getting this wrong is how the first attempt at
    # this probe made the legs lighter instead of dirtier.
    m_leg = worn_metal((0.040, 0.040, 0.045), (0.075, 0.072, 0.070), accent, wear * 0.35, 0.6,
                       mud, dust * 0.4, scuff * 0.5, foot_z, "av_leg")
    leg_parts = ("tibia", "tibia_knuckle", "foot", "belt_cover")
    for o in bpy.data.objects:
        if o.type != "MESH" or not o.data.materials or o.data.materials[0] is None:
            continue
        nm = o.data.materials[0].name
        base = o.name.split(".")[0]
        if nm.startswith("shell_paint"):
            o.data.materials[0] = m_shell
        elif nm.startswith("chassis_paint"):
            o.data.materials[0] = m_chas
        elif legs_too and base in leg_parts:
            o.data.materials[0] = m_leg


def _emissive_strength(value, colour=None):
    for m in bpy.data.materials:
        if not m.use_nodes:
            continue
        for nd in m.node_tree.nodes:
            if nd.type == "EMISSION":
                nd.inputs["Strength"].default_value = value
                if colour is not None:
                    nd.inputs["Color"].default_value = (*colour, 1)


def _cam(loc, aim, focal=40.0, fstop=5.6):
    cd = bpy.data.cameras.new("CAM")
    cd.lens = focal
    cd.dof.use_dof = True
    cd.dof.aperture_fstop = fstop
    cam = bpy.data.objects.new("CAM", cd)
    bpy.context.scene.collection.objects.link(cam)
    cam.location = Vector(loc)
    t = bpy.data.objects.new("CAM_aim", None)
    bpy.context.scene.collection.objects.link(t)
    t.location = Vector(aim)
    c = cam.constraints.new("TRACK_TO")
    c.track_axis = "TRACK_NEGATIVE_Z"
    c.up_axis = "UP_Y"
    c.target = t
    cd.dof.focus_object = t
    bpy.context.scene.camera = cam
    return cam


def _stage(fog=0.02, albedo=0.30, width=3.6, height=4.8, length=22.0):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    E.world(fog=fog, ambient=0.0)          # ambient 0: the dark is actually dark
    rk = E.rock(albedo_lo=0.045, albedo_hi=albedo, warm=1.0, wet=0.35)
    E.passage(width=width, height=height, length=length, mat=rk, seed=5, rubble=12)
    return rk


PLAYER_SHELL, PLAYER_CHASSIS = (0.66, 0.63, 0.57), (0.050, 0.052, 0.058)   # pale over graphite
RIVAL_SHELL, RIVAL_CHASSIS = (0.070, 0.062, 0.055), (0.40, 0.36, 0.32)     # graphite over pale
BONE = (0.949, 0.902, 0.824)
EMBER = (1.000, 0.478, 0.184)

S = A.shot

# ---- 1/2. the lamp -------------------------------------------------------------------------
if S in ("lamp_asbuilt", "lamp_fixed"):
    _stage(fog=0.022)
    cfg = P.default_config("surveyor")
    built = build_agent(cfg, at=(0, 0, 0))
    _retint(PLAYER_SHELL, PLAYER_CHASSIS, wear=0.35)
    _emissive_strength(3.0, BONE)
    if S == "lamp_fixed":
        _fix_lamp(built, energy=600.0, white=True, aim_down_deg=10.0)
    else:
        built.lamp.data.energy = 600.0          # same power, so ONLY aim differs
        built.lamp.data.color = (1.00, 0.98, 0.95)
    _cam((-2.5, -1.5, 1.15), (1.6, 0, 0.30), focal=38)

# ---- 3/4. wear -----------------------------------------------------------------------------
elif S in ("wear_current", "wear_directed"):
    _stage(fog=0.012)
    cfg = P.default_config("surveyor")
    built = build_agent(cfg, at=(0, 0, 0))
    if S == "wear_directed":
        _retint(PLAYER_SHELL, PLAYER_CHASSIS, wear=0.35,
                mud=0.85, dust=0.55, scuff=0.6, legs_too=True, foot_z=0.0)
    else:
        _retint(PLAYER_SHELL, PLAYER_CHASSIS, wear=0.35)   # isotropic only, as today
    _emissive_strength(3.0, BONE)
    # a close raking source so the MATERIAL is what is judged, not the exposure
    E.add_light("insp", "AREA", (1.5, -1.9, 1.5), 90.0, (1.0, 0.95, 0.88), size=1.0, aim=(0, 0, 0.28))
    E.add_light("insp2", "AREA", (-1.4, 1.5, 0.55), 22.0, (1.0, 0.93, 0.85), size=0.8, aim=(0, 0, 0.20))
    _cam((1.55, -1.45, 0.52), (0.0, 0, 0.26), focal=52, fstop=4.0)

# ---- 5/6/7. team identity --------------------------------------------------------------------
elif S in ("team_player", "team_rival", "team_hue",
           "team_player_lowdust", "team_rival_lowdust"):
    _stage(fog=0.02)
    cfg = P.default_config("surveyor")
    built = build_agent(cfg, at=(0, 0, 0))
    # `_lowdust` variants test one hypothesis: dust in the ROCK's own colour settles on the
    # horizontals, which are the surfaces the value inversion is carried on -- so the two
    # teams may be converging toward the cave rather than staying apart.
    if S == "team_player":
        _retint(PLAYER_SHELL, PLAYER_CHASSIS, wear=0.35, mud=0.7, dust=0.5, scuff=0.5, legs_too=True)
        _emissive_strength(3.0, BONE)
    elif S == "team_rival":
        _retint(RIVAL_SHELL, RIVAL_CHASSIS, wear=0.5, mud=0.7, dust=0.5, scuff=0.6, legs_too=True)
        _emissive_strength(3.0, EMBER)
    elif S == "team_player_lowdust":
        _retint(PLAYER_SHELL, PLAYER_CHASSIS, wear=0.35, mud=0.7, dust=0.12, scuff=0.5, legs_too=True)
        _emissive_strength(3.0, BONE)
    elif S == "team_rival_lowdust":
        _retint(RIVAL_SHELL, RIVAL_CHASSIS, wear=0.5, mud=0.7, dust=0.12, scuff=0.6, legs_too=True)
        _emissive_strength(3.0, EMBER)
    else:   # today's scheme: identical value, identity carried by emissive hue at strength 8
        _retint(PLAYER_SHELL, PLAYER_CHASSIS, wear=0.35)
        _emissive_strength(8.0, (0.2, 0.9, 1.0))
    # Lit the way a machine is actually SEEN by something other than itself: standing in a
    # rival's lamp, or under a bulkhead fitting on the near haunch. The first version of this
    # shot put the source across the passage and produced two black frames -- which tests
    # nothing, because two machines you cannot see are trivially the same colour.
    E.add_light("fitting", "POINT", (1.35, -1.55, 2.05), 420.0, (1.0, 0.72, 0.42), size=0.10)
    _fix_lamp(built, energy=600.0, white=True, aim_down_deg=10.0)
    _cam((-1.55, -1.95, 0.72), (0.05, 0, 0.28), focal=55, fstop=5.6)

# ---- 8/9. the loadout in silhouette ----------------------------------------------------------
elif S in ("sil_bare", "sil_loaded"):
    _stage(fog=0.045)
    if S == "sil_bare":
        cfg = P.AgentConfig(chassis="surveyor", modules={"eye": "optical"})
    else:
        cfg = P.default_config("surveyor")
    built = build_agent(cfg, at=(0, 0, 0))
    _retint(PLAYER_SHELL, PLAYER_CHASSIS, wear=0.35, mud=0.7, dust=0.5, scuff=0.5, legs_too=True)
    _emissive_strength(3.0, BONE)
    _fix_lamp(built, energy=600.0, white=True, aim_down_deg=14.0)
    # Directly behind and LOW, so the machine sits between the camera and its own pool and
    # its outline falls on lit floor. The first version of this shot put the machine at the
    # frame edge with the pool beside it, which makes most of the silhouette black-on-black
    # and proves nothing: measured at 0.08% of frame changing between bare and loaded.
    _cam((-1.62, -0.10, 0.30), (2.6, 0.02, 0.06), focal=45, fstop=6.0)

# ---- 10. the wreck ----------------------------------------------------------------------------
elif S in ("wreck", "wreck_ridehonly"):
    _stage(fog=0.03)
    ch = P.CHASSIS["surveyor"]
    old_ride = ch.ride_height
    ch.ride_height = 0.055                      # belly on the rock
    cfg = P.default_config("surveyor")
    built = build_agent(cfg, at=(0, 0, 0))
    ch.ride_height = old_ride
    _retint((0.30, 0.28, 0.25), (0.045, 0.045, 0.050), wear=0.95,
            mud=1.0, dust=0.8, scuff=0.9, legs_too=True)
    _emissive_strength(0.0)                     # every emissive dead: the read at range

    if S == "wreck":
        # Ride height alone reads as CROUCHING, not dead -- measured, see MEASUREMENTS.md.
        # Three more things are needed and none of them is a material:
        #   1. roll, so the underside shows. You never see a working machine's underside.
        #   2. per-leg pose: folded under on one side, splayed out on the other.
        #   3. a part actually missing, and a part actually lying on the floor.
        arm = bpy.data.objects["AGENT_RIG"]
        # 40 deg, not 62: past about 45 it stops reading as FALLEN and starts reading as
        # FLIPPED, which is a different and less useful idea. And the body has to be dropped
        # onto the rock by hand, because nothing in the rig knows the hull can touch the
        # ground -- only the feet do. That is the core of why a WreckSpec is needed.
        arm.rotation_euler = Euler((math.radians(40), 0, math.radians(-12)))
        arm.location = Vector((0, 0, -0.012))
        # legs go where a dropped machine's legs go, not where a standing one's do
        splay = {0: (0.34, 0.24, 0.02), 1: (0.24, -0.14, 0.20),
                 2: (-0.20, 0.30, 0.02), 3: (-0.32, -0.06, 0.16)}
        for i, p in splay.items():
            e = bpy.data.objects.get(f"FOOT.{i}")
            if e:
                e.location = Vector(p)
        # one leg gone below the knee
        for nm in ("tibia.3", "tibia_knuckle.3", "foot.3"):
            o = bpy.data.objects.get(nm)
            if o:
                bpy.data.objects.remove(o, do_unlink=True)
        # the compute hatch, sprung off and lying on the rock: destroyed, not parked
        o = bpy.data.objects.get("hatch_compute")
        if o:
            bpy.data.objects.remove(o, do_unlink=True)
        pan = G.box("shed_panel", (0.16, 0.10, 0.004), (0.20, -0.26, 0.003), bevel=0.002)
        pan.rotation_euler = Euler((0, 0.05, 0.8))
        pan.data.materials.append(worn_metal((0.30, 0.28, 0.25), (0.20, 0.19, 0.18),
                                             (0.85, 0.45, 0.10), 0.95, 0.6, 1.0, 0.8, 0.9,
                                             0.0, "av_panel"))
    bpy.context.view_layer.update()
    # a passing machine's lamp finds it. Nothing else in frame emits.
    E.add_light("passing", "SPOT", (-1.75, -1.35, 0.55), 600.0, (1.00, 0.98, 0.95),
                size=0.05, spot_deg=54, blend=0.5, aim=(0.05, 0, 0.04))
    _cam((-1.15, -1.30, 0.30), (0.02, 0, 0.07), focal=48, fstop=5.0)

else:
    raise SystemExit(f"unknown shot {S}")

E.settings(samples=A.samples, res=RES, look="AgX - Medium High Contrast")
bpy.context.scene.render.filepath = A.out
bpy.ops.render.render(write_still=True)
print(f"WROTE {A.out}")
