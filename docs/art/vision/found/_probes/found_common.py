"""Shared pieces for the 'found' vision-board probes (deposit, wreck, beacon, discovery,
cloud, gap, perception). Imported by found_probe.py and cloud_scene.py inside Blender.

The three agent_model fixes ART-DIRECTION.md §0/§2.5/§4.3 asks for are re-applied here
at runtime, exactly as docs/art/agent/av_probe.py does, because agent_model belongs to
another workflow: the lamp is re-aimed to +X and tilted down, the lamp is white, and the
emissives are retinted BONE / EMBER at strength <= 3. Nothing in agent_model is modified.

Two lighting rigs, so every concept has a CLEAR view and an IN-SITU view:

  clear_rig()   a studio: neutral grey world at strength 1.0, one 3 m area key from 45 deg
                high at ~1000 W, AgX Base. The thing can be SEEN. Not the game.
  insitu()      world background 0. If a pixel is lit, a fixture in frame is lighting it.
"""
import math
import os
import sys

ROOT = r"C:/Users/jackh/documents/programming/Blindside"
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "docs/art/probes"))

import bpy  # noqa: E402
from mathutils import Vector, Euler  # noqa: E402

from agent_model import params as P  # noqa: E402
from agent_model import geometry as G  # noqa: E402
from agent_model import materials as M  # noqa: E402
from agent_model.build import build_agent  # noqa: E402
import p2_env as E  # noqa: E402

# ---- palette (palette.py, ART-DIRECTION 3.1 / 5.2 / 6.3) ----------------------------------
BONE = (0.949, 0.902, 0.824)
EMBER = (1.000, 0.478, 0.184)
WARM_DIM = (0.478, 0.400, 0.314)         # #7A6650 the beacon pilot. Never team-coloured.
SENSED = (0.388, 0.839, 0.969)           # #63D6F7
WALKED = (0.180, 0.282, 0.329)           # #2E4854
GHOST = (0.624, 0.910, 1.000)            # #9FE8FF
COOL_DIM = (0.227, 0.322, 0.376)
LIE = (1.000, 0.824, 0.247)
LAMP_WHITE = (1.00, 0.98, 0.95)
PLAYER_SHELL, PLAYER_CHASSIS = (0.66, 0.63, 0.57), (0.050, 0.052, 0.058)   # pale over graphite
RIVAL_SHELL, RIVAL_CHASSIS = (0.070, 0.062, 0.055), (0.40, 0.36, 0.32)     # graphite over pale
CAST_IRON = (0.075, 0.038, 0.021)        # wet a century, rough 0.86, metallic 0
BEARING_STEEL = (0.52, 0.50, 0.48)       # still working, rough 0.30, metallic 1
ROCK_DUST = (0.30, 0.265, 0.215)
MUD = (0.085, 0.062, 0.040)
CELL = 0.6


# ---- materials ------------------------------------------------------------------------------
def _new(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for nd in list(nt.nodes):
        nt.nodes.remove(nd)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    return m, nt, out


def flat(name, rgb, rough=0.5, metallic=0.0, coat=0.0, spec=0.5):
    m, nt, out = _new(name)
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metallic
    b.inputs["Coat Weight"].default_value = coat
    b.inputs["Specular IOR Level"].default_value = spec
    nt.links.new(b.outputs[0], out.inputs[0])
    return m


def emission(name, rgb, strength):
    m, nt, out = _new(name)
    e = nt.nodes.new("ShaderNodeEmission")
    e.inputs["Color"].default_value = (*rgb, 1)
    e.inputs["Strength"].default_value = strength
    nt.links.new(e.outputs[0], out.inputs[0])
    return m


def cast_iron(name="cast_iron"):
    """ART-DIRECTION 5.2: wet a century. Near-black, faintly ferrous, matte, scaled. Never
    orange. Mottled on a low-frequency noise, bump on two scales. Reads as a piece of the
    cave that has corners."""
    m, nt, out = _new(name)
    n, L = nt.nodes, nt.links.new
    b = n.new("ShaderNodeBsdfPrincipled")
    b.inputs["Metallic"].default_value = 0.0
    b.inputs["Specular IOR Level"].default_value = 0.35
    geo = n.new("ShaderNodeNewGeometry")
    t1 = n.new("ShaderNodeTexNoise")
    t1.inputs["Scale"].default_value = 3.0
    t1.inputs["Detail"].default_value = 6.0
    t2 = n.new("ShaderNodeTexNoise")
    t2.inputs["Scale"].default_value = 40.0
    t2.inputs["Detail"].default_value = 8.0
    L(geo.outputs["Position"], t1.inputs["Vector"])
    L(geo.outputs["Position"], t2.inputs["Vector"])
    ramp = n.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.35
    ramp.color_ramp.elements[0].color = (0.030, 0.020, 0.014, 1)
    ramp.color_ramp.elements[1].position = 0.75
    ramp.color_ramp.elements[1].color = (*CAST_IRON, 1)
    L(t1.outputs["Fac"], ramp.inputs["Fac"])
    L(ramp.outputs["Color"], b.inputs["Base Color"])
    rg = n.new("ShaderNodeMath")
    rg.operation = "MULTIPLY_ADD"
    rg.inputs[1].default_value = 0.12
    rg.inputs[2].default_value = 0.80
    L(t2.outputs["Fac"], rg.inputs[0])
    L(rg.outputs[0], b.inputs["Roughness"])
    bp1 = n.new("ShaderNodeBump")
    bp1.inputs["Strength"].default_value = 0.25
    L(t2.outputs["Fac"], bp1.inputs["Height"])
    bp2 = n.new("ShaderNodeBump")
    bp2.inputs["Strength"].default_value = 0.5
    L(t1.outputs["Fac"], bp2.inputs["Height"])
    L(bp1.outputs["Normal"], bp2.inputs["Normal"])
    L(bp2.outputs["Normal"], b.inputs["Normal"])
    L(b.outputs[0], out.inputs[0])
    return m


def bearing_steel(name="bearing_steel"):
    return flat(name, BEARING_STEEL, rough=0.30, metallic=1.0)


def porcelain(name="porcelain"):
    """The Bus's insulators: the only clean white dielectric in the game."""
    return flat(name, (0.86, 0.85, 0.80), rough=0.12, coat=0.6, spec=0.6)


def retro_band(name="retro_band"):
    """Retroreflective sheeting, approximated. Cycles has no true retroreflector; a very
    glossy pale coat returns a lamp that is near the camera axis, which is the case that
    matters (the lamp is on the head that is looking)."""
    return flat(name, (0.80, 0.78, 0.72), rough=0.08, metallic=0.6, coat=1.0)


def ore_rock(name="ore", lit_spec=True):
    """Ore: the same rock family, redder, denser, glassier, more specular -- ONLY when
    lit. A tighter voronoi (denser) with a low roughness and a slightly redder ramp."""
    m = E.rock(name, albedo_lo=0.05, albedo_hi=0.30, warm=1.0, wet=0.35,
               fracture_scale=14.0, bed_scale=1.6, bump=0.6)
    nt = m.node_tree
    for nd in nt.nodes:
        if nd.type == "VALTORGB":
            e0, e1 = nd.color_ramp.elements[0], nd.color_ramp.elements[1]
            e0.color = (0.055, 0.030, 0.022, 1)
            e1.color = (0.30, 0.19, 0.13, 1)     # redder, same warm family
        if nd.type == "BSDF_PRINCIPLED":
            nd.inputs["Specular IOR Level"].default_value = 0.55 if lit_spec else 0.35
            nd.inputs["Coat Weight"].default_value = 0.08 if lit_spec else 0.0
            nd.inputs["Coat Roughness"].default_value = 0.12
    # roughness: glassy
    for nd in nt.nodes:
        if nd.type == "MATH" and nd.operation == "MULTIPLY_ADD" and abs(nd.inputs[1].default_value + 0.25) < 1e-6:
            nd.inputs[2].default_value = 0.52
    return m


def worn_metal(base, bare, wear=0.35, grime=0.4, mud=0.0, dust=0.0, scuff=0.0,
               foot_z=0.0, name="worn"):
    """av_probe.worn_metal, verbatim in intent: painted metal plus three gravity masks
    (mud: world Z at the feet; dust: upward normals in the rock's colour; scuff: +X faces)."""
    m, nt, out = _new(name)
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


# ---- the agent, with the three fixes ------------------------------------------------------------
def fix_lamp(built, energy=600.0, aim_down_deg=9.0, white=True, spot_deg=50.0):
    """build.py:312 aims the spot at -X, into eye_lens at 14 mm. Re-aim to +X, tilt down."""
    if not built.lamp:
        return
    built.lamp.rotation_euler = Euler((0, -math.pi / 2 + math.radians(aim_down_deg), 0))
    built.lamp.data.energy = energy
    built.lamp.data.spot_size = math.radians(spot_deg)
    if white:
        built.lamp.data.color = LAMP_WHITE


def retint(col, shell, chassis, wear=0.35, mud=0.0, dust=0.0, scuff=0.0, legs_too=True,
           foot_z=0.0, bare=(0.45, 0.45, 0.47), tag="a"):
    """Reassign hull materials of every mesh in `col` (one agent's collection)."""
    m_shell = worn_metal(shell, bare, wear, 0.4, mud, dust, scuff, foot_z, f"fd_shell_{tag}")
    m_chas = worn_metal(chassis, bare, wear, 0.5, mud, dust, scuff, foot_z, f"fd_chassis_{tag}")
    m_leg = worn_metal((0.040, 0.040, 0.045), (0.075, 0.072, 0.070), wear * 0.35, 0.6,
                       mud, dust * 0.4, scuff * 0.5, foot_z, f"fd_leg_{tag}")
    leg_parts = ("tibia", "tibia_knuckle", "foot", "belt_cover")
    for o in col.all_objects:
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


def emissives(col, strength, colour=None):
    """Strength <= 3 for identity emissives (ART-DIRECTION 4.3). 0 kills them (a wreck)."""
    seen = set()
    for o in col.all_objects:
        if o.type != "MESH":
            continue
        for m in o.data.materials:
            if m is None or not m.use_nodes or m.name in seen:
                continue
            seen.add(m.name)
            for nd in m.node_tree.nodes:
                if nd.type == "EMISSION":
                    nd.inputs["Strength"].default_value = strength
                    if colour is not None:
                        nd.inputs["Color"].default_value = (*colour, 1)


def agent(team="player", chassis="surveyor", modules=None, at=(0, 0, 0), yaw_deg=0.0,
          wear=0.35, mud=0.6, dust=0.45, scuff=0.45, lamp=600.0, aim_down=9.0, name="AGENT",
          emissive=3.0):
    """Build one machine with the fixes applied. Returns the Built handle. `modules=None`
    is the default Surveyor loadout; pass {} for a bare chassis."""
    cfg = P.default_config(chassis)
    if modules is not None:
        cfg.modules = dict(modules)
    built = build_agent(cfg, name=name, at=at)
    col = built.collection
    if team == "player":
        retint(col, PLAYER_SHELL, PLAYER_CHASSIS, wear, mud, dust, scuff, True, at[2], tag=name)
        emissives(col, emissive, BONE)
    elif team == "rival":
        retint(col, RIVAL_SHELL, RIVAL_CHASSIS, wear, mud, dust, scuff, True, at[2], tag=name)
        emissives(col, emissive, EMBER)
    else:  # a wreck: dead grey-amber paint, every emissive dead
        retint(col, (0.30, 0.28, 0.25), (0.045, 0.045, 0.050), 0.95, 1.0, 0.8, 0.9, True, at[2], tag=name)
        emissives(col, 0.0)
    if built.lamp:
        if lamp > 0:
            fix_lamp(built, energy=lamp, aim_down_deg=aim_down)
        else:
            built.lamp.data.energy = 0.0
    built.arm.rotation_euler = Euler((0, 0, math.radians(yaw_deg)))
    if abs(yaw_deg) > 1e-6:
        # feet and look are world-space empties: rotate them about the body origin too
        c, s = math.cos(math.radians(yaw_deg)), math.sin(math.radians(yaw_deg))
        o = Vector(at)
        for e in built.feet + [built.look]:
            p = Vector(e.location) - o
            e.location = o + Vector((p.x * c - p.y * s, p.x * s + p.y * c, p.z))
    return built


def find(col, name):
    """An object of one agent's collection by its build name, whatever suffix Blender added
    when a second agent was built with the same part names."""
    for o in col.all_objects:
        if o.name == name or o.name.startswith(name + "."):
            return o
    return None


def open_hatch(col, name="belly_hatch", deg=70.0):
    """Spring the cargo hatch: rotate it about its own long edge."""
    h = find(col, name)
    if h is None:
        return None
    from mathutils import Matrix
    dims = h.dimensions
    edge = h.matrix_world @ Vector((0, dims.y * 0.5 / max(h.scale.y, 1e-6), 0))
    axis = (h.matrix_world.to_3x3() @ Vector((1, 0, 0))).normalized()
    R = Matrix.Translation(edge) @ Matrix.Rotation(math.radians(deg), 4, axis) @ Matrix.Translation(-edge)
    h.matrix_world = R @ h.matrix_world
    return h


def ore_lumps(name, at, n=12, r=(0.018, 0.05), radius=0.35, seed=9, mat=None, z0=0.0):
    import random
    rng = random.Random(seed)
    col = G.new_collection(name)
    for i in range(n):
        rr = rng.uniform(*r)
        d = rng.uniform(0, radius) ** 0.7 * radius ** 0.3
        ang = rng.uniform(0, 6.283)
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=rr,
                                              location=(at[0] + math.cos(ang) * d, at[1] + math.sin(ang) * d, z0 + rr * 0.6))
        o = bpy.context.object
        o.name = f"{name}.{i}"
        o.scale = (rng.uniform(0.7, 1.4), rng.uniform(0.7, 1.4), rng.uniform(0.5, 0.9))
        o.rotation_euler = (rng.uniform(0, 3), rng.uniform(0, 3), rng.uniform(0, 3))
        E._displace(o, 0.08, rr * 1.2, depth=3)
        for c in list(o.users_collection):
            c.objects.unlink(o)
        col.objects.link(o)
        G.set_material(o, mat)
    return col


def pose_wreck(built, roll_deg=40.0, yaw_deg=-12.0, missing_leg=3, shed_hatch=True, at=(0, 0, 0)):
    """av_probe's third attempt, the one that read as fallen: roll 40 deg, body dropped onto the
    rock, feet where a dropped machine's feet land, one tibia gone, the compute hatch shed."""
    arm = built.arm
    arm.rotation_euler = Euler((math.radians(roll_deg), 0, math.radians(yaw_deg)))
    arm.location = Vector(at) + Vector((0, 0, -0.012))
    splay = {0: (0.34, 0.24, 0.02), 1: (0.24, -0.14, 0.20), 2: (-0.20, 0.30, 0.02), 3: (-0.32, -0.06, 0.16)}
    for i, p in splay.items():
        e = built.feet[i] if i < len(built.feet) else None
        if e:
            e.location = Vector(at) + Vector(p)
    col = built.collection
    if missing_leg is not None:
        for nm in (f"tibia.{missing_leg}", f"tibia_knuckle.{missing_leg}", f"foot.{missing_leg}"):
            o = find(col, nm)
            if o:
                bpy.data.objects.remove(o, do_unlink=True)
    shed = None
    if shed_hatch:
        o = find(col, "hatch_compute")
        if o:
            bpy.data.objects.remove(o, do_unlink=True)
        shed = G.box("shed_panel", (0.16, 0.10, 0.004), Vector(at) + Vector((0.20, -0.26, 0.003)), bevel=0.002)
        shed.rotation_euler = Euler((0, 0.05, 0.8))
        shed.data.materials.append(worn_metal((0.30, 0.28, 0.25), (0.20, 0.19, 0.18), 0.95, 0.6, 1.0, 0.8, 0.9, 0.0, "fd_panel"))
    bpy.context.view_layer.update()
    return shed


def head_down(built, at=(0, 0, 0), dz=0.14):
    """The download / recovery pose: head folded down toward the floor in front of the prow,
    body crouched. THE-MACHINERY 6: 'sensor head down, hard against the floor'. The tilt bone
    is limited to +-0.6 rad, so the head cannot touch the rock as built -- flagged."""
    from agent_model.motion import Mover
    m = Mover(built)
    m.stand(0.2)
    m.crouch(dz, over=0.4)
    m.look_at((0.40, 0.0, 0.0), over=0.4, ride=True)      # body frame: 0.4 m ahead, on the floor
    m.stand(0.2)
    m.finish()
    bpy.context.scene.frame_set(m.frame)
    bpy.context.view_layer.update()
    return m


def clear_near(pos, r, prefixes=("rubble", "talus_lump", "spoil_lump")):
    """Delete loose rubble within r of a point -- a camera position. A lump on the lens is a
    black frame, and a probe that renders black has measured nothing. (Two first-pass frames
    were exactly this.)"""
    p = Vector(pos)
    gone = 0
    for o in list(bpy.data.objects):
        if o.type == "MESH" and any(o.name.startswith(x) for x in prefixes):
            if (Vector(o.location) - p).length < r:
                bpy.data.objects.remove(o, do_unlink=True)
                gone += 1
    print(f"clear_near: removed {gone} lumps within {r} m of {tuple(round(v, 2) for v in p)}")
    return gone


# ---- rigs ------------------------------------------------------------------------------------
def clear_rig(key_w=1000.0, bg=0.18, key_size=3.0, key_from=(2.5, -3.0, 3.5), aim=(0, 0, 0.3),
              fill_w=120.0):
    """The studio: a grey world and one big soft key at 45 deg. Not the game."""
    w = bpy.context.scene.world or bpy.data.worlds.new("World")
    bpy.context.scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    for nd in list(nt.nodes):
        nt.nodes.remove(nd)
    out = nt.nodes.new("ShaderNodeOutputWorld")
    b = nt.nodes.new("ShaderNodeBackground")
    b.inputs["Color"].default_value = (bg, bg, bg, 1)
    b.inputs["Strength"].default_value = 1.0
    nt.links.new(b.outputs[0], out.inputs["Surface"])
    E.add_light("KEY", "AREA", key_from, key_w, (1.0, 0.98, 0.95), size=key_size, aim=aim)
    if fill_w > 0:
        E.add_light("FILL", "AREA", (-3.0, 2.5, 2.0), fill_w, (0.95, 0.97, 1.0), size=4.0, aim=aim)


def insitu(fog=0.012):
    """World background 0. Resting cave volume 0.008-0.012 (ART-DIRECTION 2.6)."""
    E.world(fog=fog, ambient=0.0)


def ground(size=14.0, albedo=0.30, waterline=None, seed=3, disp=0.06, name="ground", rock=None):
    """A displaced rock floor at z = 0."""
    rk = rock or E.rock("ground_rock", albedo_lo=0.045, albedo_hi=albedo, warm=1.0, wet=0.35, waterline=waterline)
    fl = G.plane(name, size, (0, 0, 0), subdiv=60)
    E._displace(fl, 0.7, disp, depth=5, mid=0.5)
    fl.data.shade_smooth()
    G.set_material(fl, rk)
    return fl


def gauge_lines(x0=-3.0, x1=3.0, y=0.0, z=0.004, mat=None, gauge=0.60):
    """Two thin bars 0.60 m apart: the rail gauge as a scale reference, painted not built."""
    mat = mat or flat("gauge_paint", (0.80, 0.78, 0.70), rough=0.6)
    for s in (1, -1):
        b = G.box(f"gauge.{s}", (x1 - x0, 0.02, 0.006), ((x0 + x1) / 2, y + s * gauge / 2, z))
        G.set_material(b, mat)


def camera(loc, aim, focal=50.0, fstop=None, ortho=None):
    cd = bpy.data.cameras.new("CAM")
    cd.lens = focal
    if ortho is not None:
        cd.type = "ORTHO"
        cd.ortho_scale = ortho
    if fstop:
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
    if fstop:
        cd.dof.focus_object = t
    bpy.context.scene.camera = cam
    return cam


def render(out, samples=40, res=(960, 600), look="AgX - Medium High Contrast", exposure=0.0):
    E.settings(samples=samples, res=res, look=look, exposure=exposure)
    sc = bpy.context.scene
    sc.cycles.volume_bounces = 1
    os.makedirs(os.path.dirname(out), exist_ok=True)
    sc.render.filepath = out
    bpy.ops.render.render(write_still=True)
    print(f"WROTE {out}")


def fresh():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.unit_settings.system = "METRIC"


# ---- found objects -------------------------------------------------------------------------
def beacon(name, at, pilot=1.0, mat_body=None, mat_band=None, tilt=(0, 0, 0), halo=0.0):
    """ART-DIRECTION 6.3: a 230 x 60 mm cast tube, self-righting on a weighted base, one warm
    pilot at the top, a retroreflective band. Pilot WARM_DIM, never team-coloured. A spoofed
    one is built by this same function with the same arguments: pixel-identical by construction."""
    at = Vector(at)
    body = mat_body or cast_iron("beacon_iron")
    band = mat_band or retro_band("beacon_band")
    col = G.new_collection(name)
    parts = []
    parts.append(G.cyl(f"{name}_base", 0.040, 0.030, 0.035, at + Vector((0, 0, 0.0175)), verts=20, col=col, bevel=0.003))
    parts.append(G.cyl(f"{name}_tube", 0.030, 0.030, 0.170, at + Vector((0, 0, 0.035 + 0.085)), verts=20, col=col))
    parts.append(G.cyl(f"{name}_cap", 0.032, 0.022, 0.022, at + Vector((0, 0, 0.205 + 0.011)), verts=20, col=col, bevel=0.002))
    for p in parts:
        G.set_material(p, body)
    b = G.cyl(f"{name}_band", 0.0308, 0.0308, 0.028, at + Vector((0, 0, 0.16)), verts=20, col=col)
    G.set_material(b, band)
    pil = G.sphere(f"{name}_pilot", 0.007, at + Vector((0, 0, 0.230)), col=col, seg=12)
    G.set_material(pil, emission(f"{name}_pilot_m", WARM_DIM, pilot * 6.0))
    if halo > 0:
        # a bloom stand-in for the board: a 35 mm soft glow round the pilot, emissive at the
        # centre and transparent at the rim. Cycles has no bloom; the client would. A licence.
        h = G.sphere(f"{name}_halo", 0.035, at + Vector((0, 0, 0.230)), col=col, seg=16)
        m, nt, out = _new(f"{name}_halo_m")
        n, L = nt.nodes, nt.links.new
        lw = n.new("ShaderNodeLayerWeight")
        lw.inputs["Blend"].default_value = 0.35
        em = n.new("ShaderNodeEmission")
        em.inputs["Color"].default_value = (*WARM_DIM, 1)
        em.inputs["Strength"].default_value = 0.9 * halo
        tr = n.new("ShaderNodeBsdfTransparent")
        mx = n.new("ShaderNodeMixShader")
        L(lw.outputs["Facing"], mx.inputs["Fac"])
        L(em.outputs[0], mx.inputs[1])
        L(tr.outputs[0], mx.inputs[2])
        L(mx.outputs[0], out.inputs[0])
        m.blend_method = "BLEND"
        G.set_material(h, m)
        h.visible_shadow = False
        h.visible_diffuse = False
        h.visible_glossy = False
    if pilot > 0:
        d = bpy.data.lights.new(f"{name}_L", "POINT")
        d.energy = 0.35 * pilot                       # a pilot lights nothing; it is a point you can see
        d.color = WARM_DIM
        d.shadow_soft_size = 0.01
        o = bpy.data.objects.new(f"{name}_L", d)
        col.objects.link(o)
        o.location = at + Vector((0, 0, 0.232))
    for p in parts + [b, pil]:
        p.rotation_euler = Euler(tilt)
    return col


def rubble_cone(name, at, radius=3.6, height=1.1, n=180, seed=4, mat=None, r_lo=0.05, r_hi=0.22,
                spread=1.0, col=None):
    """A talus cone at the angle of repose: a displaced cone body plus loose lumps on it."""
    import random
    rng = random.Random(seed)
    col = col or G.new_collection(name)
    bpy.ops.mesh.primitive_cone_add(vertices=48, radius1=radius, radius2=0.25, depth=height,
                                    location=(at[0], at[1], at[2] + height / 2))
    cone = bpy.context.object
    cone.name = f"{name}_body"
    sub = cone.modifiers.new("subsurf", "SUBSURF")
    sub.levels = sub.render_levels = 2
    E._displace(cone, 0.6, 0.35, depth=5)
    cone.data.shade_smooth()
    for c in list(cone.users_collection):
        c.objects.unlink(cone)
    col.objects.link(cone)
    G.set_material(cone, mat)
    for i in range(n):
        r = rng.uniform(r_lo, r_hi)
        d = rng.uniform(0, radius * spread) ** 0.8 * radius ** 0.2
        ang = rng.uniform(0, 6.283)
        x, y = at[0] + math.cos(ang) * d, at[1] + math.sin(ang) * d
        z = at[2] + max(0.0, height * (1 - d / radius)) * 0.92 + r * 0.3
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=r, location=(x, y, z))
        rk = bpy.context.object
        rk.name = f"{name}_lump.{i}"
        rk.scale = (rng.uniform(0.7, 1.5), rng.uniform(0.7, 1.5), rng.uniform(0.4, 0.9))
        rk.rotation_euler = (rng.uniform(0, 3), rng.uniform(0, 3), rng.uniform(0, 3))
        E._displace(rk, 0.12, r * 1.3, depth=3)
        for c in list(rk.users_collection):
            c.objects.unlink(rk)
        col.objects.link(rk)
        G.set_material(rk, mat)
    return col


def working_face(name, at, width=7.0, height=4.4, yaw_deg=0.0, holes=True, scar=None, mat=None,
                 mat_ore=None, seed=2, col=None):
    """A fresh-cut working face: a near-vertical displaced slab with a row of drill holes,
    some charged. `scar` = (u, z, radius) of a freshly loaded bite, brighter and sharper."""
    import random
    rng = random.Random(seed)
    col = col or G.new_collection(name)
    a = math.radians(yaw_deg)
    fwd = Vector((math.cos(a), math.sin(a), 0))     # face normal, pointing into the chamber
    right = Vector((-math.sin(a), math.cos(a), 0))
    bpy.ops.mesh.primitive_plane_add(size=1.0, location=(0, 0, 0))
    pl = bpy.context.object
    pl.name = f"{name}_slab"
    pl.scale = (width, height, 1.0)
    bpy.ops.object.transform_apply(scale=True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.subdivide(number_cuts=60)
    bpy.ops.object.mode_set(mode="OBJECT")
    E._displace(pl, 1.3, 0.55, depth=5, mid=0.5)
    E._displace(pl, 0.30, 0.14, depth=4, mid=0.5)
    pl.data.shade_smooth()
    pl.rotation_euler = Euler((math.pi / 2, 0, a + math.pi / 2))
    pl.location = Vector(at) + Vector((0, 0, height / 2 - 0.2))
    for c in list(pl.users_collection):
        c.objects.unlink(pl)
    col.objects.link(pl)
    G.set_material(pl, mat)
    if holes:
        for k in range(9):
            u = -width * 0.42 + k * width * 0.105
            z = 0.9 + 0.35 * math.sin(k * 1.3) + rng.uniform(-0.1, 0.1)
            p = Vector(at) + right * u + fwd * 0.05 + Vector((0, 0, z))
            h = G.cyl(f"{name}_hole{k}", 0.028, 0.028, 0.30, p, verts=12, col=col)
            h.rotation_euler = fwd.to_track_quat("Z", "Y").to_euler()
            G.set_material(h, flat(f"{name}_hole_m", (0.004, 0.004, 0.004), rough=0.95))
            if k % 3 == 1:   # charged: a wire out of it, hanging
                w = G.tube_along(f"{name}_wire{k}", [p + fwd * 0.05, p + fwd * 0.12 + Vector((0, 0, -0.25)),
                                                       p + fwd * 0.10 + Vector((0, 0, -0.6))], 0.004, verts=6, col=col)
                G.set_material(w, flat(f"{name}_wire_m", (0.05, 0.04, 0.03), rough=0.7))
    if scar is not None:
        # the bite: a flattened patch of fresh-fractured rock, un-silted, brighter, sharper,
        # sitting in the face where the stock was taken (a recess would need a boolean; this
        # is the cheapest thing that reads as 'somebody cut here')
        su, sz, sr = scar
        p = Vector(at) + right * su + fwd * 0.03 + Vector((0, 0, sz))
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=sr, location=p)
        s = bpy.context.object
        s.name = f"{name}_scar"
        s.rotation_euler = fwd.to_track_quat("Z", "Y").to_euler()
        s.scale = (1.15, 0.85, 0.22)
        E._displace(s, 0.18, sr * 0.5, depth=4)
        s.data.shade_smooth()
        for c in list(s.users_collection):
            c.objects.unlink(s)
        col.objects.link(s)
        G.set_material(s, E.rock(f"{name}_scar_rock", albedo_lo=0.10, albedo_hi=0.42, warm=1.0, wet=0.1,
                                 fracture_scale=18.0, bump=0.7))
    return col
