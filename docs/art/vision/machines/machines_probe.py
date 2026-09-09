"""Vision-board renders for THE MACHINES (ART-DIRECTION.md 4, 6.2, 8; D1-D11 in the inventory).

  "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b -P docs/art/vision/machines/machines_probe.py \
      -- --shots lineup_clear,lineup_side --out-dir <ABSOLUTE docs/art/vision/machines> [--samples 40]

`--shots all` renders everything. Each shot writes <concept>/<NN_name>.png and a
<NN_name>.bbox.json sidecar with every agent's screen bounding box (for ladders.py).

Nothing here modifies agent_model. Three things av_probe.py established are re-applied to
every machine in every frame, because build.py still has them wrong:
  1. the head lamp is re-aimed +X (build.py:312 fires it into its own eye lens)
  2. the lamp is WHITE for every team (build.py:307 tints it toward the skin's cyan)
  3. no emissive is cyan; strips are BONE (player) / EMBER (rival) at strength <= 3
Directional wear (`worn_metal`) is copied from av_probe.py so the two agree.

Two reference rigs, both guesses, so the board's clear views agree with each other:
  CLEAR    neutral grey world 1.0 + one 3 m area key from 45 deg high, grey ground plane,
           the 0.60 m rail gauge painted on the floor and a 1 m banded rod for scale
  DAYLIGHT uniform overcast sky at the shaft's own 12000 K (0.60, 0.74, 1.00) -- the surface
           light IS the light that comes down the shaft -- no sun disc, one soft cloud-break
IN-SITU frames use the direction's own rig: world 0, diegetic sources only, p2_env passage.
"""
import argparse
import dataclasses
import json
import math
import os
import re
import sys

ROOT = r"C:/Users/jackh/documents/programming/Blindside"
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "docs/art/probes"))

import bpy  # noqa: E402
from mathutils import Vector, Euler, Matrix  # noqa: E402
from bpy_extras.object_utils import world_to_camera_view  # noqa: E402

from agent_model import params as P  # noqa: E402
from agent_model import geometry as G  # noqa: E402
from agent_model.build import build_agent  # noqa: E402
from agent_model import build as _B  # noqa: E402
import p2_env as E  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--shots", required=True)
ap.add_argument("--out-dir", required=True)
ap.add_argument("--samples", type=int, default=40)
ap.add_argument("--res", default="960x600")
ap.add_argument("--skip-existing", action="store_true")
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
A = ap.parse_args(argv)
RES = tuple(int(v) for v in A.res.split("x"))

# ---- pole-angle cache ---------------------------------------------------------------------
# build.py settles each leg's IK pole angle by trying 24 angles with a depsgraph update each:
# ~100 updates per machine, ~150 for a Hauler, and every update re-evaluates every rig in
# the scene. Measured: a four-machine lineup took 20 min to BUILD under load. The answer
# depends only on the chassis geometry (the armature is at the origin when it runs), so it
# is cached per (chassis, ride, legs) in _bbox/pole_cache.json and reused across shots.
_POLE_CACHE = os.path.join(A.out_dir, "_bbox", "pole_cache.json")
_settle_orig = _B._settle_pole_angles


def _pole_key(arm, leg_geom):
    # arm["chassis"] is set AFTER the settle in build.py, so the key is the leg geometry alone
    return repr([tuple(round(v, 5) for v in (Hp.x, Hp.y, Hp.z, P.x, P.y, P.z, K.x, K.y, K.z, Kt.x, Kt.y, Kt.z, F.x, F.y, F.z))
                 for (Hp, P, K, Kt, F) in leg_geom])


def _settle_cached(arm, leg_geom):
    key = _pole_key(arm, leg_geom)
    cache = {}
    try:
        with open(_POLE_CACHE) as f:
            cache = json.load(f)
    except (OSError, ValueError):
        pass
    if key in cache and len(cache[key]) == len(leg_geom):
        for i, deg in enumerate(cache[key]):
            arm.pose.bones[f"tibia.{i}"].constraints[-1].pole_angle = math.radians(deg)
        bpy.context.view_layer.update()
        return
    _settle_orig(arm, leg_geom)
    cache[key] = [round(math.degrees(arm.pose.bones[f"tibia.{i}"].constraints[-1].pole_angle), 3) for i in range(len(leg_geom))]
    try:
        os.makedirs(os.path.dirname(_POLE_CACHE), exist_ok=True)
        tmp = _POLE_CACHE + f".{os.getpid()}"
        with open(tmp, "w") as f:
            json.dump(cache, f)
        os.replace(tmp, _POLE_CACHE)
    except OSError:
        pass


_B._settle_pole_angles = _settle_cached


# ---- palette (av_probe's values, so the board matches av_02/08/09) -------------------------
BONE = (0.949, 0.902, 0.824)
EMBER = (1.000, 0.478, 0.184)
WHITE = (1.00, 0.98, 0.95)
WARM_DIM = (0.478, 0.400, 0.314)          # #7A6650 beacon pilot
PLAYER_SHELL, PLAYER_CHASSIS = (0.66, 0.63, 0.57), (0.050, 0.052, 0.058)   # pale over graphite
RIVAL_SHELL, RIVAL_CHASSIS = (0.070, 0.062, 0.055), (0.40, 0.36, 0.32)     # graphite over pale
ROCK_DUST = (0.30, 0.265, 0.215)
MUD = (0.085, 0.062, 0.040)
SKY = (0.60, 0.74, 1.00)                  # the shaft's 12000 K, ART-DIRECTION 2.1
CAST_IRON = (0.075, 0.038, 0.021)          # ART-DIRECTION 5.2


# =========================================================================================
# materials
# =========================================================================================
def _mat(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for nd in list(nt.nodes):
        nt.nodes.remove(nd)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    return m, nt, out


def flat(name, colour, rough=0.6, metallic=0.0, spec=0.5):
    m, nt, out = _mat(name)
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    b.inputs["Base Color"].default_value = (*colour, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metallic
    b.inputs["Specular IOR Level"].default_value = spec
    nt.links.new(b.outputs[0], out.inputs[0])
    return m


def emissive(name, colour, strength):
    m, nt, out = _mat(name)
    e = nt.nodes.new("ShaderNodeEmission")
    e.inputs["Color"].default_value = (*colour, 1)
    e.inputs["Strength"].default_value = strength
    nt.links.new(e.outputs[0], out.inputs[0])
    return m


def retro(name="retro_sheeting", tint=(0.80, 0.78, 0.72), rough=0.14):
    """Retroreflective sheeting, approximated. Cycles has no retroreflector BSDF; the shading
    normal is bent to face the viewer (Geometry.Incoming), so the glossy lobe returns light
    that comes from NEAR THE CAMERA and almost nothing else. Correct for the case that
    matters (a rival's lamp is next to the rival's eye); wrong for a lamp far off-axis, which
    a real prism sheet would still return. A little diffuse so it exists in daylight."""
    m, nt, out = _mat(name)
    n, L = nt.nodes, nt.links.new
    geo = n.new("ShaderNodeNewGeometry")
    g = n.new("ShaderNodeBsdfPrincipled")
    g.inputs["Base Color"].default_value = (*tint, 1)
    g.inputs["Metallic"].default_value = 1.0
    g.inputs["Roughness"].default_value = rough
    L(geo.outputs["Incoming"], g.inputs["Normal"])
    d = n.new("ShaderNodeBsdfDiffuse")
    d.inputs["Color"].default_value = (0.30, 0.29, 0.27, 1)
    mix = n.new("ShaderNodeMixShader")
    mix.inputs["Fac"].default_value = 0.85
    L(d.outputs[0], mix.inputs[1])
    L(g.outputs[0], mix.inputs[2])
    L(mix.outputs[0], out.inputs[0])
    return m


def cast_iron(name="cast_iron"):
    """ART-DIRECTION 5.2: wet a century, near-black, matte, mottled, never orange."""
    m, nt, out = _mat(name)
    n, L = nt.nodes, nt.links.new
    b = n.new("ShaderNodeBsdfPrincipled")
    b.inputs["Metallic"].default_value = 0.0
    geo = n.new("ShaderNodeNewGeometry")
    nz = n.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 2.5
    nz.inputs["Detail"].default_value = 9.0
    L(geo.outputs["Position"], nz.inputs["Vector"])
    ramp = n.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.35
    ramp.color_ramp.elements[0].color = (*[v * 0.6 for v in CAST_IRON], 1)
    ramp.color_ramp.elements[1].position = 0.75
    ramp.color_ramp.elements[1].color = (*[v * 1.5 for v in CAST_IRON], 1)
    L(nz.outputs["Fac"], ramp.inputs["Fac"])
    L(ramp.outputs["Color"], b.inputs["Base Color"])
    rg = n.new("ShaderNodeMath")
    rg.operation = "MULTIPLY_ADD"
    rg.inputs[1].default_value = 0.14
    rg.inputs[2].default_value = 0.78
    L(nz.outputs["Fac"], rg.inputs[0])
    L(rg.outputs[0], b.inputs["Roughness"])
    fine = n.new("ShaderNodeTexNoise")
    fine.inputs["Scale"].default_value = 40.0
    L(geo.outputs["Position"], fine.inputs["Vector"])
    bump = n.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.25
    L(fine.outputs["Fac"], bump.inputs["Height"])
    L(bump.outputs["Normal"], b.inputs["Normal"])
    L(b.outputs[0], out.inputs[0])
    return m


def hardstanding(name="hardstanding", wet=0.6):
    """Compacted spoil and old concrete, puddled. One noise picks the puddles: colour darkens,
    roughness drops to a mirror. Guess: what a pit-head floor is."""
    m, nt, out = _mat(name)
    n, L = nt.nodes, nt.links.new
    b = n.new("ShaderNodeBsdfPrincipled")
    geo = n.new("ShaderNodeNewGeometry")
    big = n.new("ShaderNodeTexNoise")
    big.inputs["Scale"].default_value = 0.35
    big.inputs["Detail"].default_value = 6.0
    L(geo.outputs["Position"], big.inputs["Vector"])
    pud = n.new("ShaderNodeMapRange")
    pud.inputs["From Min"].default_value = 0.56
    pud.inputs["From Max"].default_value = 0.60
    pud.clamp = True
    L(big.outputs["Fac"], pud.inputs["Value"])
    pudw = n.new("ShaderNodeMath")
    pudw.operation = "MULTIPLY"
    pudw.inputs[1].default_value = wet
    L(pud.outputs["Result"], pudw.inputs[0])
    grit = n.new("ShaderNodeTexNoise")
    grit.inputs["Scale"].default_value = 9.0
    grit.inputs["Detail"].default_value = 10.0
    L(geo.outputs["Position"], grit.inputs["Vector"])
    ramp = n.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.3
    ramp.color_ramp.elements[0].color = (0.07, 0.062, 0.054, 1)
    ramp.color_ramp.elements[1].position = 0.75
    ramp.color_ramp.elements[1].color = (0.17, 0.152, 0.130, 1)
    L(grit.outputs["Fac"], ramp.inputs["Fac"])
    col = n.new("ShaderNodeMix")
    col.data_type = "RGBA"
    col.inputs["B"].default_value = (0.05, 0.048, 0.045, 1)
    L(pudw.outputs[0], col.inputs["Factor"])
    L(ramp.outputs["Color"], col.inputs["A"])
    L(col.outputs["Result"], b.inputs["Base Color"])
    rgh = n.new("ShaderNodeMix")
    rgh.data_type = "FLOAT"
    rgh.inputs["A"].default_value = 0.55
    rgh.inputs["B"].default_value = 0.04
    L(pudw.outputs[0], rgh.inputs["Factor"])
    L(rgh.outputs["Result"], b.inputs["Roughness"])
    bump = n.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.3
    L(grit.outputs["Fac"], bump.inputs["Height"])
    L(bump.outputs["Normal"], b.inputs["Normal"])
    L(b.outputs[0], out.inputs[0])
    return m


def worn_metal(base, bare, accent, wear=0.35, grime=0.4, mud=0.0, dust=0.0, scuff=0.0,
               foot_z=0.0, name="worn"):
    """painted_metal plus three gravity-aware masks (av_probe.py, ART-DIRECTION 4.1):
    mud = world-Z at the feet; dust = upward normals in the rock's colour; scuff = +X faces."""
    m, nt, out = _mat(name)
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


# =========================================================================================
# agents: build, dress, pose, state
# =========================================================================================
AGENTS = []          # [(label, built)] for the bbox sidecar; reset per shot
_N = [0]


def _core(name):
    return re.sub(r"\.\d{3}$", "", name)


def parts(built, base):
    """Parts of ONE agent by build name, ignoring Blender's .001 suffixes: 'foot.3',
    'hatch_compute', ... Multi-agent scenes make build.py's global name lookups unsafe."""
    return [o for o in built.parts if _core(o.name) == base]


def parts_prefix(built, prefix):
    return [o for o in built.parts if _core(o.name).startswith(prefix)]


def make_agent(chassis="surveyor", modules=None, at=(0, 0, 0), yaw=0.0, label=None,
               ride=None, **overrides):
    """build_agent with the chassis spec temporarily replaced (ride height, head radius,
    hull ...). The spec is restored afterwards, so shots do not leak into each other."""
    spec0 = P.CHASSIS[chassis]
    kw = dict(overrides)
    if ride is not None:
        kw["ride_height"] = ride
    spec = dataclasses.replace(spec0, **kw) if kw else spec0
    P.CHASSIS[chassis] = spec
    _N[0] += 1
    try:
        mods = P.default_config(chassis).modules if modules is None else dict(modules)
        cfg = P.AgentConfig(chassis=chassis, modules=mods)
        built = build_agent(cfg, name=f"AGENT{_N[0]}", at=at)
    finally:
        P.CHASSIS[chassis] = spec0
    built.cfg, built.spec, built.at, built.yaw = cfg, spec, Vector(at), yaw
    if yaw:
        R = Matrix.Rotation(yaw, 3, "Z")
        built.arm.rotation_euler = Euler((0, 0, yaw))
        for e in built.feet:
            e.location = built.at + R @ (Vector(e.location) - built.at)
        built.look.location = built.at + R @ (Vector(built.look.location) - built.at)
    bpy.context.view_layer.update()
    AGENTS.append((label or chassis, built))
    return built


def fwd(built):
    return Vector((math.cos(built.yaw), math.sin(built.yaw), 0))


def dress(built, team="player", wear=0.35, mud=0.7, dust=0.5, scuff=0.5, legs_too=True,
          shell=None, chassis=None):
    """Reassign hull materials (and the lower leg, so mud can reach the feet)."""
    if shell is None:
        shell, chassis = (PLAYER_SHELL, PLAYER_CHASSIS) if team == "player" else (RIVAL_SHELL, RIVAL_CHASSIS)
    bare, accent, fz = (0.45, 0.45, 0.47), (0.85, 0.45, 0.10), built.at.z
    m_shell = worn_metal(shell, bare, accent, wear, 0.4, mud, dust, scuff, fz, "v_shell")
    m_chas = worn_metal(chassis, bare, accent, wear, 0.5, mud, dust, scuff, fz, "v_chassis")
    m_leg = worn_metal((0.040, 0.040, 0.045), (0.075, 0.072, 0.070), accent, wear * 0.35, 0.6,
                       mud, dust * 0.4, scuff * 0.5, fz, "v_leg")
    leg_parts = ("tibia", "tibia_knuckle", "foot", "belt_cover")
    for o in built.parts:
        if o.type != "MESH" or not o.data.materials or o.data.materials[0] is None:
            continue
        nm = o.data.materials[0].name
        base = _core(o.name).split(".")[0]
        if nm.startswith("shell_paint"):
            o.data.materials[0] = m_shell
        elif nm.startswith("chassis_paint"):
            o.data.materials[0] = m_chas
        elif legs_too and base in leg_parts:
            o.data.materials[0] = m_leg


def emissives(built, strength, colour=None, which=("light_strip", "eye")):
    seen = set()
    for o in built.parts:
        for m in o.data.materials:
            if m is None or m.name in seen or not m.use_nodes or _core(m.name) not in which:
                continue
            seen.add(m.name)
            for nd in m.node_tree.nodes:
                if nd.type == "EMISSION":
                    nd.inputs["Strength"].default_value = strength
                    if colour is not None:
                        nd.inputs["Color"].default_value = (*colour, 1)


SONAR_DARK = None


def sonar(built, lit=0, colour=BONE, strength=3.0):
    """Active sonar bar: `lit` of 7 elements emitting. 0 = passive, dark (the default here:
    ART-DIRECTION design problem 2 says a bar lit all the time asserts 'always pinging')."""
    global SONAR_DARK
    if SONAR_DARK is None:
        SONAR_DARK = flat("sonar_dark", (0.03, 0.03, 0.035), rough=0.3)
    on = emissive("sonar_lit", colour, strength) if lit else None
    for o in parts_prefix(built, "face_sonar_el"):
        k = int(_core(o.name).rsplit("el", 1)[1])
        o.data.materials[0] = on if k < lit else SONAR_DARK


def lamp(built, on=True, energy=600.0, down_deg=10.0):
    """build.py:312 aims the spot at -X. Re-aim +X, tilt down, make it white."""
    if not built.lamp:
        return
    if on:
        built.lamp.rotation_euler = Euler((0, -math.pi / 2 + math.radians(down_deg), 0))
        built.lamp.data.energy = energy
        built.lamp.data.color = WHITE
        emissives(built, 3.0, WHITE, which=("eye",))
    else:
        built.lamp.data.energy = 0.0
        emissives(built, 0.0, which=("eye",))


def strips(built, mode="emissive", strength=3.0, colour=BONE, wide=False, status=True):
    """Running lights. emissive = as today (strength <= 3 in BONE/EMBER). retro = the
    proposal (ART-DIRECTION 4.5). wide = the 4x area (16 mm) the direction asks for."""
    for o in parts(built, "strip.1") + parts(built, "strip.-1"):
        if wide:
            o.scale.z *= 2.67
        if mode == "retro":
            o.data.materials[0] = retro()
    if mode == "retro":
        for o in parts(built, "status_light"):
            bpy.data.objects.remove(o, do_unlink=True)
            built.parts.remove(o)
    else:
        emissives(built, strength, colour, which=("light_strip",))
        if not status:
            for o in parts(built, "status_light"):
                bpy.data.objects.remove(o, do_unlink=True)
                built.parts.remove(o)


def remove(built, *names):
    for nm in names:
        for o in parts(built, nm):
            bpy.data.objects.remove(o, do_unlink=True)
            built.parts.remove(o)


def add_part(built, obj, mat):
    """A mesh bolted on after build: parented to the body so it rides with it."""
    G.set_material(obj, mat)
    obj.parent = built.arm
    obj.matrix_parent_inverse = built.arm.matrix_world.inverted()
    built.parts.append(obj)
    return obj


def look(built, world_point):
    built.look.location = Vector(world_point)


def wreck_pose(built, shell=(0.30, 0.28, 0.25), chassis=(0.045, 0.045, 0.050), retro_strips=False):
    """av_probe's wreck (ART-DIRECTION 6.2): 40 deg roll, body dropped onto the rock, legs
    where a dropped machine's legs land, one gone below the knee, the compute hatch shed.
    Build with ride=0.055 first."""
    a = built.at
    dress(built, shell=shell, chassis=chassis, wear=0.95, mud=1.0, dust=0.8, scuff=0.9)
    emissives(built, 0.0)
    sonar(built, 0)
    if retro_strips:
        strips(built, "retro", wide=True)
    lamp(built, on=False)
    built.arm.rotation_euler = Euler((math.radians(40), 0, math.radians(-12) + built.yaw))
    built.arm.location = a + Vector((0, 0, -0.012))
    splay = {0: (0.34, 0.24, 0.02), 1: (0.24, -0.14, 0.20), 2: (-0.20, 0.30, 0.02), 3: (-0.32, -0.06, 0.16)}
    for i, p in splay.items():
        built.feet[i].location = a + Vector(p)
    remove(built, "tibia.3", "tibia_knuckle.3", "foot.3", "hatch_compute")
    # built at the origin, then placed: G.box bakes its location into the mesh, so a
    # rotation_euler set afterwards would swing the panel about world zero (measured: a
    # wreck at x = 5.8 put its panel at x = 4.4, under the floor)
    pan = G.box("shed_panel", (0.16, 0.10, 0.004), (0, 0, 0), bevel=0.002)
    pan.rotation_euler = Euler((0, 0.05, 0.8 + built.yaw))
    pan.location = a + Vector((0.20, -0.26, 0.003))
    G.set_material(pan, worn_metal(shell, (0.20, 0.19, 0.18), (0.85, 0.45, 0.10), 0.95, 0.6, 1.0, 0.8, 0.9, a.z, "v_panel"))
    built.parts.append(pan)
    bpy.context.view_layer.update()


def damage(built, level):
    """ART-DIRECTION 4.2's rungs, expressed with what the model has. Build the 0.75 rung with
    ride = 0.75 * ride_height (the rig follows that one number)."""
    if level >= 0.20:
        sonar(built, 4 if level < 0.5 else 2)
    else:
        sonar(built, 7)
    if level >= 0.30:
        remove(built, "belt_cover.1", "knee_cap.1")                  # a hip cover shed
        f = built.feet[1]
        f.location = Vector(f.location) + Vector((-0.06, 0.0, 0.05))  # the gait hitch, frozen
    if level >= 0.50:
        remove(built, "hatch_battery")                               # a hull panel not built
        L, W, H = built.spec.hull
        zc = built.spec.ride_height + H / 2
        hole = G.box("shed_recess", (L * 0.26, W * 0.5, 0.006), built.at + Vector((0.02, 0, zc + H / 2 + 0.006)))
        add_part(built, hole, flat("graphite_under", (0.035, 0.036, 0.040), rough=0.75))
    if level >= 0.75:
        # the head stops tracking and jitters: frozen off-axis and down
        look(built, built.at + Vector((0.7, -0.9, 0.05)))
        # the boom hangs: rotate every boom part about its root hinge
        L, W, H = built.spec.hull
        zc = built.spec.ride_height + H / 2
        u = W
        for s in built.spec.slots:
            if built.cfg.modules.get(s.name) == "magnetometer":
                hinge = built.at + Vector((s.pos[0] + u * 0.02, s.pos[1], zc + s.pos[2] + u * 0.09))
                boom = parts_prefix(built, f"{s.name}_boom") + parts_prefix(built, f"{s.name}_brace") + \
                    parts_prefix(built, f"{s.name}_mag_elbow") + parts_prefix(built, f"{s.name}_pod") + \
                    parts_prefix(built, f"{s.name}_mag_cable")
                pod = parts_prefix(built, f"{s.name}_pod")[0]
                # whichever sign LOWERS the pod is "hangs" (the sign depends on the boom's frame)
                z0 = (pod.matrix_world.translation).z
                for sign in (1, -1):
                    R = Matrix.Translation(hinge) @ Matrix.Rotation(math.radians(sign * 48), 4, "Y") @ Matrix.Translation(-hinge)
                    if (R @ pod.matrix_world).translation.z < z0:
                        break
                for o in boom:
                    o.matrix_world = R @ o.matrix_world
    bpy.context.view_layer.update()


# ---- module fixes (ART-DIRECTION 4.4 proposals) ----------------------------------------------
def fix_vane(built):
    """passive_acoustic -> a line array standing 0.06 m proud of each flank on two stalks,
    0.7 L long. 'A listening machine should look wider.' Passive: no emissive, ever."""
    L, W, H = built.spec.hull
    zc = built.spec.ride_height + H / 2
    for side, slot in ((1, "side_l"), (-1, "side_r")):
        if built.cfg.modules.get(slot) != "passive_acoustic":
            continue
        remove(built, f"{slot}_rail", *[f"{slot}_hydrophone{k}" for k in range(5)])
        sp = [s for s in built.spec.slots if s.name == slot][0]
        y0 = sp.pos[1]
        z = zc + sp.pos[2]
        y = y0 + side * 0.062
        add_part(built, G.box(f"{slot}_vane", (L * 0.70, 0.005, 0.046), built.at + Vector((sp.pos[0], y, z)), bevel=0.001),
                 flat("vane_dark", (0.05, 0.05, 0.055), rough=0.5))
        for x in (sp.pos[0] - L * 0.22, sp.pos[0] + L * 0.22):
            add_part(built, G.cyl(f"{slot}_vane_stalk", 0.004, 0.004, 0.062, built.at + Vector((x, y0 + side * 0.031, z)),
                                  rot=(math.pi / 2, 0, 0), verts=8), flat("stalk", (0.35, 0.35, 0.36), rough=0.4, metallic=1.0))


def fix_spike(built, planted=False):
    """structural_monitor -> a 180 mm geophone spike. Stowed: on the deck in a cradle.
    Planted: the machine crouches (ride 0.15) and the spike goes into the floor under the
    belly -- 180 mm cannot reach the floor from a 0.32 m ride height, so monitoring is a
    posture as well as a part (guess). Build the planted one with ride=0.15."""
    L, W, H = built.spec.hull
    zc = built.spec.ride_height + H / 2
    z_top = zc + H / 2 + 0.024
    steel = flat("spike_steel", (0.50, 0.49, 0.47), rough=0.30, metallic=1.0)
    for i in range(len(built.feet)):
        remove(built, f"geophone.{i}")
    if not planted:
        add_part(built, G.cyl("spike", 0.006, 0.0015, 0.18, built.at + Vector((-L * 0.30, -W * 0.30, z_top + 0.018)),
                              rot=(0, math.pi / 2, 0), verts=10), steel)
        for dx in (-0.06, 0.06):
            add_part(built, G.box("spike_cradle", (0.012, 0.024, 0.016), built.at + Vector((-L * 0.30 + dx, -W * 0.30, z_top + 0.008))),
                     flat("cradle", (0.06, 0.06, 0.065), rough=0.6))
    else:
        zb = built.spec.ride_height
        # 180 mm from just under the hull DOWN INTO the floor: the tip is 40 mm below z=0
        add_part(built, G.cyl("spike", 0.0015, 0.006, 0.18, built.at + Vector((-0.02, 0, zb - 0.05)), verts=10), steel)
        add_part(built, G.cyl("spike_collar", 0.018, 0.018, 0.024, built.at + Vector((-0.02, 0, zb - 0.008)), verts=12),
                 flat("cradle2", (0.06, 0.06, 0.065), rough=0.6))


def rack_state(built, remaining=4, lit=True):
    """beacon_rack: caps lit while a beacon is aboard, dark (and gone) once dropped. Spectator
    vocabulary only (ART-DIRECTION 9: no world-readable inventory in the live view)."""
    pilot = emissive("cap_pilot", WARM_DIM, 2.0)
    for slot in ("top_r", "top_m", "top_0", "top_1", "top_2", "top_3"):
        if built.cfg.modules.get(slot) != "beacon_rack":
            continue
        for k in range(4):
            if k >= remaining:
                remove(built, f"{slot}_beacon{k}", f"{slot}_beacon_cap{k}")
            elif lit:
                for o in parts(built, f"{slot}_beacon_cap{k}"):
                    o.data.materials[0] = pilot


def bay_state(built, loads=0):
    """cargo_bay: a two-segment window on the bay's flank, 0/1/2 lit."""
    if built.cfg.modules.get("belly") != "cargo_bay":
        return
    L, W, H = built.spec.hull
    zc = built.spec.ride_height + H / 2
    sp = [s for s in built.spec.slots if s.name == "belly"][0]
    u = W
    z = zc + sp.pos[2] - u * 0.10
    lit = emissive("bay_lit", BONE, 2.0)
    dark = flat("bay_dark", (0.02, 0.02, 0.025), rough=0.3)
    for side in (1, -1):
        for k, dx in enumerate((-0.05, 0.05)):
            add_part(built, G.box(f"bay_seg{k}", (0.08, 0.004, 0.02), built.at + Vector((sp.pos[0] + dx, side * (u * 0.30 + 0.002), z))),
                     lit if k < loads else dark)


# ---- chassis gestures (ART-DIRECTION 4.6 proposals) -------------------------------------------
def raise_head(built, dz):
    """Scout: a long neck. build.py never reads `head_neck`, so the pan/tilt bones are moved
    up in edit mode and a neck column fills the gap. The head's parts ride with the bones."""
    arm = built.arm
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    for nm in ("pan", "tilt"):
        eb = arm.data.edit_bones[nm]
        eb.head = eb.head + Vector((0, 0, dz))
        eb.tail = eb.tail + Vector((0, 0, dz))
    bpy.ops.object.mode_set(mode="OBJECT")
    pm = parts(built, "pan_motor")[0]
    c = pm.matrix_world.translation
    hr = built.spec.head_radius
    add_part(built, G.cyl("neck", hr * 0.42, hr * 0.42, dz + 0.02, Vector((c.x, c.y, c.z + 0.014 + dz / 2 + 0.005)), verts=16),
             flat("neck_dark", (0.09, 0.09, 0.10), rough=0.5))
    bpy.context.view_layer.update()


def swimmer_gesture(built, stow=False):
    """Swimmer: a sealed lozenge that walks on the bottom. Chine along the seam, a bare-metal
    ballast band 0.3 L at mid-body, flat plate feet. stow = legs folded (build with ride=0.12)."""
    L, W, H = built.spec.hull
    zc = built.spec.ride_height + H / 2
    z_seam = zc + H * 0.05
    a = built.at
    steel = flat("ballast_steel", (0.42, 0.41, 0.40), rough=0.32, metallic=1.0)
    add_part(built, G.cyl("ballast_band", H * 0.62, H * 0.62, L * 0.30, a + Vector((0.0, 0, zc)), rot=(0, math.pi / 2, 0), verts=32), steel)
    for side in (1, -1):
        add_part(built, G.box("chine", (L * 0.92, 0.022, 0.006), a + Vector((0, side * (W / 2 + 0.006), z_seam - 0.004)), bevel=0.002),
                 flat("chine_pale", PLAYER_SHELL, rough=0.45))
    for i in range(len(built.feet)):
        remove(built, f"foot.{i}")
        f = Vector(built.feet[i].location)
        add_part(built, G.cyl(f"plate_foot.{i}", 0.032, 0.026, 0.010, Vector((f.x, f.y, f.z + 0.006)), verts=16), flat("plate_rubber", (0.02, 0.02, 0.02), rough=0.8))
    if stow:
        for i, leg in enumerate(built.spec.legs):
            built.feet[i].location = a + Vector((leg.hip[0] - 0.02, leg.side * (W / 2 + 0.045), 0.0))
    bpy.context.view_layer.update()


def hauler_truck(built):
    """Hauler as truck: the deck is a flat bed with a load rail and tie-down cleats."""
    L, W, H = built.spec.hull
    zc = built.spec.ride_height + H / 2
    z_top = zc + H / 2 + 0.024
    a = built.at
    remove(built, "rail")
    add_part(built, G.box("bed", (L * 0.68, W * 0.92, 0.008), a + Vector((-0.06, 0, z_top + 0.004)), bevel=0.002),
             flat("bed_dark", (0.06, 0.06, 0.065), rough=0.7))
    for side in (1, -1):
        add_part(built, G.box("load_rail", (L * 0.66, 0.012, 0.03), a + Vector((-0.06, side * W * 0.40, z_top + 0.024)), bevel=0.003),
                 flat("rail_dark", (0.09, 0.09, 0.10), rough=0.5))
    for i in range(4):
        add_part(built, G.box(f"cleat{i}", (0.02, 0.05, 0.012), a + Vector((0.1 - 0.15 * i, 0, z_top + 0.014))),
                 flat("cleat", (0.35, 0.35, 0.36), rough=0.4, metallic=1.0))


# =========================================================================================
# stages
# =========================================================================================
PENDING = []       # environment builders, run at render time -- AFTER the agents are built.
                   # build_agent settles each leg's pole angle with ~96 depsgraph updates, and
                   # each update re-evaluates every displaced/subdivided mesh in the scene;
                   # measured: five tiny frames took 10 min with the environment built first.


def _later(fn):
    PENDING.append(fn)


def _reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    AGENTS.clear()
    PENDING.clear()
    global SONAR_DARK
    SONAR_DARK = None


def world_flat(colour, strength, fog=0.0):
    w = bpy.data.worlds.new("World")
    bpy.context.scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    for nd in list(nt.nodes):
        nt.nodes.remove(nd)
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.inputs["Color"].default_value = (*colour, 1)
    bg.inputs["Strength"].default_value = strength
    nt.links.new(bg.outputs[0], out.inputs["Surface"])
    if fog > 0:
        vol = nt.nodes.new("ShaderNodeVolumeScatter")
        vol.inputs["Density"].default_value = fog
        vol.inputs["Anisotropy"].default_value = 0.55
        vol.inputs["Color"].default_value = (0.85, 0.86, 0.9, 1)
        nt.links.new(vol.outputs[0], out.inputs["Volume"])
    return w


def rod(at, axis="z", length=1.0):
    """A 1 m rod in 0.1 m black/white bands. The scale reference every clear view carries."""
    n = int(round(length / 0.1))
    for k in range(n):
        c = (0.85, 0.85, 0.85) if k % 2 == 0 else (0.03, 0.03, 0.03)
        off = 0.05 + 0.1 * k
        loc = Vector(at) + (Vector((0, 0, off)) if axis == "z" else Vector((0, off, 0)))
        rot = (0, 0, 0) if axis == "z" else (math.pi / 2, 0, 0)
        G.set_material(G.cyl(f"rod{k}", 0.012, 0.012, 0.1, loc, rot=rot, verts=12), flat(f"rodm{k}", c, rough=0.5))


def gauge(y=0.0, length=8.0, x=0.0):
    """The 0.60 m rail gauge painted on the floor -- 'the agent fits between the rails'."""
    dark = flat("gauge_paint", (0.10, 0.10, 0.10), rough=0.7)
    for s in (-1, 1):
        G.set_material(G.box(f"gauge{s}", (length, 0.02, 0.002), (x, y + s * 0.30, 0.001)), dark)


def stage_clear(gauge_y=None, rod_at=None, rod_axis="z", size=30.0):
    _reset()
    world_flat((0.42, 0.42, 0.42), 1.0)
    E.add_light("key", "AREA", (3.2, -3.2, 4.4), 1000.0, (1.0, 1.0, 1.0), size=3.0, aim=(0, 0, 0.3))

    def env():
        g = G.plane("ground", size, (0, 0, 0))
        G.set_material(g, flat("ground_grey", (0.40, 0.40, 0.40), rough=0.7))
        if gauge_y is not None:
            gauge(gauge_y)
        if rod_at is not None:
            rod(rod_at, rod_axis)
    _later(env)


def stage_passage(fog=0.02, albedo=0.30, width=3.6, height=4.8, length=22.0, seed=5):
    """av_probe's in-situ stage: world 0, the p2_env passage, rock albedo 0.30."""
    _reset()
    E.world(fog=fog, ambient=0.0)

    def env():
        rk = E.rock(albedo_lo=0.045, albedo_hi=albedo, warm=1.0, wet=0.35)
        E.passage(width=width, height=height, length=length, mat=rk, seed=seed, rubble=12)
    _later(env)


def stage_yard(sun=False, collar=(-7.0, 5.0)):
    """The pit-head, minimal: hardstanding, the shaft collar, a cast-iron headframe with its
    sheave and cable, a roofless stone winding house, spoil heaps on the skyline. Overcast at
    the shaft's own colour; no sun unless asked. All of it is a guess (DESIGN-PRINCIPLES 3
    settles only that the surface exists, has sky, and is where teaching happens)."""
    _reset()
    world_flat(SKY, 1.0)
    E.add_light("cloud_break", "AREA", (6.0, -9.0, 14.0), 2600.0, (0.92, 0.94, 1.0), size=8.0, aim=(0, 0, 0))
    if sun:
        d = bpy.data.lights.new("SUN", "SUN")
        d.energy = 3.0
        d.angle = math.radians(1.5)
        d.color = (1.0, 0.86, 0.68)
        o = bpy.data.objects.new("SUN", d)
        bpy.context.scene.collection.objects.link(o)
        o.rotation_euler = Euler((math.radians(68), 0, math.radians(-135)))
    _later(lambda: _yard_set(collar))


def _yard_set(collar):
    g = G.plane("hardstanding", 160.0, (0, 0, 0), subdiv=90)
    E._displace(g, 3.0, 0.05, depth=4, mid=0.5)
    g.data.shade_smooth()
    G.set_material(g, hardstanding())
    iron = cast_iron()
    stone = E.rock("stone", albedo_lo=0.06, albedo_hi=0.30, warm=0.8, wet=0.45, bed_scale=1.4, fracture_scale=9.0)
    spoil = E.rock("spoil", albedo_lo=0.04, albedo_hi=0.22, warm=1.0, wet=0.4, bed_scale=0.6)
    cx, cy = collar
    # the collar: a stone plinth, a cast ring, and the hole
    G.set_material(G.cyl("plinth", 1.9, 1.75, 0.35, (cx, cy, 0.175), verts=24), stone)
    G.set_material(G.cyl("collar_ring", 1.30, 1.26, 0.28, (cx, cy, 0.49), verts=24, bevel=0.02), iron)
    G.set_material(G.cyl("collar_hole", 1.10, 1.10, 0.40, (cx, cy, 0.35), verts=24), flat("hole_black", (0.003, 0.003, 0.003), rough=1.0, spec=0.0))
    for k in range(4):
        a = math.radians(45 + 90 * k)
        G.set_material(G.cyl(f"guide{k}", 0.05, 0.05, 8.5, (cx + math.cos(a) * 0.95, cy + math.sin(a) * 0.95, 4.5), verts=8), iron)
    # the headframe: two A-frames over the collar, back braces to the engine side, sheave, cable
    for sy in (-1.6, 1.6):
        for sx in (-2.6, 2.6):
            G.set_material(G.strut(f"hf_leg", (cx + sx, cy + sy, 0.0), (cx, cy + sy, 9.0), 0.34, 0.30, 0.22, 0.20, bevel=0.01), iron)
        G.set_material(G.strut(f"hf_back", (cx - 7.5, cy + sy, 0.0), (cx - 0.2, cy + sy, 8.9), 0.30, 0.26, 0.20, 0.18, bevel=0.01), iron)
        for z in (3.0, 6.0):
            t = z / 9.0
            G.set_material(G.segment("hf_tie", (cx - 2.6 * (1 - t), cy + sy, z), (cx + 2.6 * (1 - t), cy + sy, z), 0.06, 0.06, verts=8), iron)
    G.set_material(G.segment("hf_cross", (cx, cy - 1.6, 9.0), (cx, cy + 1.6, 9.0), 0.16, 0.16, verts=10), iron)
    G.set_material(G.segment("hf_cross2", (cx - 1.2, cy - 1.6, 6.0), (cx - 1.2, cy + 1.6, 6.0), 0.10, 0.10, verts=8), iron)
    G.set_material(G.torus("sheave", 0.95, 0.075, (cx - 0.95, cy, 9.0), rot=(math.pi / 2, 0, 0)), iron)
    G.set_material(G.cyl("sheave_hub", 0.22, 0.22, 0.5, (cx - 0.95, cy, 9.0), rot=(math.pi / 2, 0, 0), verts=16),
                   flat("bearing_steel", (0.52, 0.50, 0.48), rough=0.30, metallic=1.0))
    for k in range(6):
        a = math.radians(30 * (2 * k + 1))
        G.set_material(G.segment(f"spoke{k}", (cx - 0.95, cy, 9.0), (cx - 0.95 + math.cos(a) * 0.9, cy, 9.0 + math.sin(a) * 0.9), 0.03, 0.03, verts=6), iron)
    G.set_material(G.segment("cable_down", (cx, cy, 9.0), (cx, cy, -0.4), 0.014, 0.014, verts=8), flat("cable", (0.30, 0.30, 0.31), rough=0.35, metallic=1.0))
    G.set_material(G.segment("cable_out", (cx - 0.95, cy, 9.95), (cx - 15.0, cy, 2.2), 0.014, 0.014, verts=8), flat("cable2", (0.30, 0.30, 0.31), rough=0.35, metallic=1.0))
    # winding house: roofless stone walls, engine side
    hx, hy = cx - 17.0, cy
    for (sx, sy, lx, ly) in ((0, -4.5, 8.0, 0.6), (0, 4.5, 8.0, 0.6), (-4.0, 0, 0.6, 9.6), (4.0, 0, 0.6, 9.6)):
        G.set_material(G.box("wh_wall", (lx, ly, 4.6), (hx + sx, hy + sy, 2.3)), stone)
    G.set_material(G.box("wh_gable", (0.6, 5.0, 1.6), (hx + 4.0, hy, 5.3)), stone)
    # spoil heaps on the skyline
    import random
    rng = random.Random(4)
    for k in range(7):
        a = math.radians(rng.uniform(100, 320))
        d = rng.uniform(26, 44)
        r = rng.uniform(9, 15)
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=4, radius=r, location=(math.cos(a) * d, math.sin(a) * d, -r * 0.55))
        h = bpy.context.object
        h.name = f"spoil{k}"
        h.scale = (rng.uniform(1.0, 1.8), rng.uniform(1.0, 1.6), 0.55)
        E._displace(h, 4.0, r * 0.25, depth=4)
        h.data.shade_smooth()
        G.set_material(h, spoil)
    return iron


# =========================================================================================
# camera and output
# =========================================================================================
def cam(loc, aim, focal=45.0, fstop=None, ortho=None, straight_down=False):
    cd = bpy.data.cameras.new("CAM")
    cd.lens = focal
    if ortho:
        cd.type = "ORTHO"
        cd.ortho_scale = ortho
    if fstop:
        cd.dof.use_dof = True
        cd.dof.aperture_fstop = fstop
    c = bpy.data.objects.new("CAM", cd)
    bpy.context.scene.collection.objects.link(c)
    c.location = Vector(loc)
    if straight_down:
        c.rotation_euler = Euler((0, 0, 0))
    else:
        t = bpy.data.objects.new("CAM_aim", None)
        bpy.context.scene.collection.objects.link(t)
        t.location = Vector(aim)
        k = c.constraints.new("TRACK_TO")
        k.track_axis = "TRACK_NEGATIVE_Z"
        k.up_axis = "UP_Y"
        k.target = t
        if fstop:
            cd.dof.focus_object = t
    bpy.context.scene.camera = c
    return c


def _bboxes():
    sc = bpy.context.scene
    c = sc.camera
    bpy.context.view_layer.update()
    W, H = sc.render.resolution_x, sc.render.resolution_y
    out = {}
    for label, built in AGENTS:
        xs, ys = [], []
        for o in built.parts:
            if o.type != "MESH":
                continue
            for corner in o.bound_box:
                v = world_to_camera_view(sc, c, o.matrix_world @ Vector(corner))
                xs.append(v.x * W)
                ys.append((1 - v.y) * H)
        if xs:
            out.setdefault(label, []).append([min(xs), min(ys), max(xs), max(ys)])
    return {k: [min(b[0] for b in v), min(b[1] for b in v), max(b[2] for b in v), max(b[3] for b in v)] for k, v in out.items()}


def render(folder, name, res=None, look="AgX - Medium High Contrast", exposure=0.0):
    res = res or RES
    for fn in PENDING:          # the environment, now that every agent is built and posed
        fn()
    PENDING.clear()
    try:
        E.settings(samples=A.samples, res=res, look=look, exposure=exposure)
    except TypeError:
        E.settings(samples=A.samples, res=res, look="AgX - Medium High Contrast", exposure=exposure)
    cy = bpy.context.scene.cycles
    cy.adaptive_threshold = 0.04          # the black nine-tenths converge at once; denoise does the rest
    cy.adaptive_min_samples = 8
    d = os.path.join(A.out_dir, folder)
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, name + ".png")
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    bd = os.path.join(A.out_dir, "_bbox")
    os.makedirs(bd, exist_ok=True)
    with open(os.path.join(bd, f"{folder}__{name}.bbox.json"), "w") as f:
        json.dump({"res": list(res), "agents": _bboxes()}, f)
    print(f"WROTE {path}")


CLEAR_LOOK = "AgX - Base Contrast"


# =========================================================================================
# shots
# =========================================================================================
SHOTS = {}


def shot(folder, name):
    def deco(fn):
        SHOTS[fn.__name__] = (folder, name, fn)
        return fn
    return deco


def clear_agent(chassis, at, modules=None, team="player", wear=0.35, label=None, **kw):
    b = make_agent(chassis, modules, at=at, label=label, **kw)
    dress(b, team, wear=wear, mud=0.35 * wear / 0.35 if wear else 0.0, dust=0.3, scuff=0.3)
    emissives(b, 3.0, BONE if team == "player" else EMBER, which=("light_strip",))
    emissives(b, 1.0, WHITE, which=("eye",))
    sonar(b, 0)
    if b.lamp:
        b.lamp.data.energy = 0.0
    return b


def insitu_agent(chassis, at, modules=None, team="player", yaw=0.0, lamp_on=True, down=10.0, label=None, **kw):
    b = make_agent(chassis, modules, at=at, yaw=yaw, label=label, **kw)
    dress(b, team, wear=0.35 if team == "player" else 0.5, mud=0.7, dust=0.5, scuff=0.5)
    emissives(b, 3.0, BONE if team == "player" else EMBER, which=("light_strip",))
    sonar(b, 0)
    lamp(b, on=lamp_on, down_deg=down)
    return b


LINEUP = [("scout", 1.35), ("surveyor", 0.45), ("hauler", -0.55), ("swimmer", -1.55)]
ROW = [("scout", 0.0), ("surveyor", 1.0), ("hauler", 2.35), ("swimmer", 3.7)]


def _swim_mods():
    m = dict(P.default_config("swimmer").modules)
    m["eye"] = "optical"
    return m


# ---- D1 chassis-lineup --------------------------------------------------------------------------
@shot("chassis-lineup", "01_clear_lineup_3q")
def lineup_clear():
    stage_clear(gauge_y=0.45, rod_at=(-0.3, 2.3, 0))
    for ch, y in LINEUP:
        clear_agent(ch, (0, y, 0), label=ch)
    cam((5.6, -4.6, 2.1), (0, -0.15, 0.24), focal=68, fstop=8.0)
    render("chassis-lineup", "01_clear_lineup_3q", look=CLEAR_LOOK)


@shot("chassis-lineup", "02_clear_side_ortho")
def lineup_side():
    stage_clear(rod_at=(-0.75, 0, 0))
    for ch, x in ROW:
        clear_agent(ch, (x, 0, 0), label=ch)
    cam((1.6, -9.0, 0.36), (1.6, 0, 0.36), ortho=5.4)
    render("chassis-lineup", "02_clear_side_ortho", res=(2000, 700), look=CLEAR_LOOK)


@shot("chassis-lineup", "03_clear_top_ortho")
def lineup_top():
    stage_clear(gauge_y=0.0, rod_at=(-0.75, -0.5, 0.02), rod_axis="y")
    for ch, x in ROW:
        clear_agent(ch, (x, 0, 0), label=ch)
    cam((1.6, 0, 10.0), None, ortho=5.4, straight_down=True)
    render("chassis-lineup", "03_clear_top_ortho", res=(2000, 700), look=CLEAR_LOOK)


@shot("chassis-lineup", "04_insitu_passage_staggered")
def lineup_passage():
    stage_passage(fog=0.035)
    for ch, at in (("scout", (0.0, 0.55, 0)), ("surveyor", (1.7, -0.5, 0)), ("hauler", (3.6, 0.5, 0)), ("swimmer", (5.4, -0.6, 0))):
        insitu_agent(ch, at, modules=_swim_mods() if ch == "swimmer" else None, label=ch, down=12.0)
    cam((-1.9, 0.05, 0.5), (3.2, 0, 0.1), focal=35, fstop=5.6)
    render("chassis-lineup", "04_insitu_passage_staggered")


# ---- D2 chassis-gestures ----------------------------------------------------------------------
@shot("chassis-gestures", "01_clear_scout_asbuilt_vs_proposed")
def scout_gesture():
    stage_clear(rod_at=(-0.55, 1.05, 0))
    clear_agent("scout", (0, 0.42, 0), label="scout_asbuilt")
    b = clear_agent("scout", (0, -0.42, 0), label="scout_proposed", head_radius=0.055, hull=(0.40, 0.15, 0.070))
    raise_head(b, 0.06)
    cam((2.1, -1.55, 0.85), (0, 0, 0.17), focal=50)
    render("chassis-gestures", "01_clear_scout_asbuilt_vs_proposed", look=CLEAR_LOOK)


@shot("chassis-gestures", "02_clear_swimmer_asbuilt_vs_proposed")
def swimmer_gesture_shot():
    stage_clear(rod_at=(-0.65, 1.2, 0))
    clear_agent("swimmer", (0, 0.5, 0), label="swimmer_asbuilt")
    b = clear_agent("swimmer", (0, -0.55, 0), label="swimmer_proposed", ride=0.12)
    swimmer_gesture(b, stow=True)
    cam((2.3, -1.9, 0.95), (0, 0, 0.16), focal=50)
    render("chassis-gestures", "02_clear_swimmer_asbuilt_vs_proposed", look=CLEAR_LOOK)


@shot("chassis-gestures", "03_clear_hauler_asbuilt_vs_truck")
def hauler_gesture():
    stage_clear(rod_at=(-0.8, 1.4, 0))
    clear_agent("hauler", (0, 0.62, 0), label="hauler_asbuilt")
    m = {"face": "active_sonar", "eye": "optical", "side_l": "passive_acoustic", "side_r": "passive_acoustic", "belly": "cargo_bay"}
    b = clear_agent("hauler", (0, -0.68, 0), modules=m, label="hauler_truck")
    hauler_truck(b)
    cam((2.7, -2.5, 1.35), (0, 0, 0.25), focal=45)
    render("chassis-gestures", "03_clear_hauler_asbuilt_vs_truck", look=CLEAR_LOOK)


@shot("chassis-gestures", "04_insitu_swimmer_proposed_backlit")
def swimmer_backlit():
    stage_passage(fog=0.045)
    b = insitu_agent("swimmer", (0, 0, 0), modules=_swim_mods(), label="swimmer_proposed", down=14.0)
    swimmer_gesture(b, stow=False)
    cam((-1.62, -0.10, 0.30), (2.6, 0.02, 0.06), focal=45, fstop=6.0)
    render("chassis-gestures", "04_insitu_swimmer_proposed_backlit")


# ---- D3 modules -------------------------------------------------------------------------------
CATALOGUE = [("bare", {}), ("active_sonar", {"face": "active_sonar"}), ("optical", {"eye": "optical"}),
             ("passive_acoustic", {"side_l": "passive_acoustic", "side_r": "passive_acoustic"}),
             ("beacon_rack", {"top_r": "beacon_rack"}), ("cargo_bay", {"belly": "cargo_bay"}),
             ("magnetometer", {"top_m": "magnetometer"}), ("structural_monitor", {"top_r": "structural_monitor"})]


def _catalogue_row():
    for k, (label, mods) in enumerate(CATALOGUE):
        clear_agent("surveyor", (k * 1.15, 0, 0), modules=mods, label=label)


@shot("modules", "01_clear_catalogue_side")
def catalogue_side():
    stage_clear(rod_at=(-0.75, 0, 0))
    _catalogue_row()
    cam((4.0, -10.0, 0.3), (4.0, 0, 0.3), ortho=9.8)
    render("modules", "01_clear_catalogue_side", res=(2400, 520), look=CLEAR_LOOK)


@shot("modules", "02_clear_catalogue_top")
def catalogue_top():
    stage_clear(gauge_y=0.0, rod_at=(-0.75, -0.5, 0.02), rod_axis="y")
    _catalogue_row()
    cam((4.0, 0, 10.0), None, ortho=9.8, straight_down=True)
    render("modules", "02_clear_catalogue_top", res=(2400, 520), look=CLEAR_LOOK)


@shot("modules", "03_clear_loaded_3q")
def loaded_3q():
    stage_clear(gauge_y=0.0, rod_at=(-0.5, 0.75, 0))
    clear_agent("surveyor", (0, 0, 0), label="loaded")
    cam((1.7, -1.35, 0.85), (0.02, 0, 0.24), focal=55)
    render("modules", "03_clear_loaded_3q", look=CLEAR_LOOK)


@shot("modules", "04_insitu_sil_bare")
def sil_bare():
    stage_passage(fog=0.045)
    insitu_agent("surveyor", (0, 0, 0), modules={"eye": "optical"}, label="bare", down=14.0)
    cam((-1.62, -0.10, 0.30), (2.6, 0.02, 0.06), focal=45, fstop=6.0)
    render("modules", "04_insitu_sil_bare")


@shot("modules", "05_insitu_sil_loaded")
def sil_loaded():
    stage_passage(fog=0.045)
    insitu_agent("surveyor", (0, 0, 0), label="loaded", down=14.0)
    cam((-1.62, -0.10, 0.30), (2.6, 0.02, 0.06), focal=45, fstop=6.0)
    render("modules", "05_insitu_sil_loaded")


def _rival_view(lit):
    stage_passage(fog=0.03)
    b = insitu_agent("surveyor", (0, 0, 0), label="loud" if lit else "quiet", lamp_on=False)
    sonar(b, 7 if lit else 0)
    E.add_light("rival_lamp", "SPOT", (4.4, 0.55, 0.62), 600.0, WHITE, size=0.05, spot_deg=50, blend=0.5, aim=(0.3, 0, 0.25))
    cam((4.6, 0.5, 0.7), (0, 0, 0.32), focal=50, fstop=5.6)


@shot("modules", "06_insitu_rival_view_pinging")
def rival_view_loud():
    _rival_view(True)
    render("modules", "06_insitu_rival_view_pinging")


@shot("modules", "07_insitu_rival_view_passive")
def rival_view_quiet():
    _rival_view(False)
    render("modules", "07_insitu_rival_view_passive")


# ---- D4 modules-fixes ------------------------------------------------------------------------
FLANK = {"eye": "optical", "side_l": "passive_acoustic", "side_r": "passive_acoustic"}


@shot("modules-fixes", "01_clear_bumps_vs_vane")
def fix_vane_shot():
    stage_clear(rod_at=(-1.05, 0.55, 0))
    clear_agent("surveyor", (0.44, 0, 0), modules=FLANK, label="bumps_asbuilt")
    b = clear_agent("surveyor", (-0.44, 0, 0), modules=FLANK, label="vane_proposed")
    fix_vane(b)
    # side-on and low, both flanks toward the camera: the stand-off and the stalks are the read
    cam((0.05, -2.45, 0.40), (0.05, 0.0, 0.30), focal=50, fstop=8.0)
    render("modules-fixes", "01_clear_bumps_vs_vane", look=CLEAR_LOOK)


SM = {"eye": "optical", "top_r": "structural_monitor"}


@shot("modules-fixes", "02_clear_collars_vs_spike")
def fix_spike_shot():
    stage_clear(rod_at=(-1.85, 0.4, 0))
    clear_agent("surveyor", (-1.1, 0, 0), modules=SM, label="collars_asbuilt")
    b = clear_agent("surveyor", (0.0, 0, 0), modules=SM, label="spike_stowed")
    fix_spike(b, planted=False)
    b = clear_agent("surveyor", (1.1, 0, 0), modules=SM, label="spike_planted", ride=0.15)
    fix_spike(b, planted=True)
    # side-on and low, so the ankle collars, the stowed spike in profile and the planted rod
    # under the belly all sit on the same line
    cam((0.0, -3.9, 0.32), (0.0, 0.0, 0.26), focal=45, fstop=8.0)
    render("modules-fixes", "02_clear_collars_vs_spike", look=CLEAR_LOOK)


RACK = {"eye": "optical", "top_r": "beacon_rack"}


@shot("modules-fixes", "03_clear_rack_full_vs_dropped")
def fix_rack_shot():
    stage_clear(rod_at=(0.5, 1.1, 0))
    b = clear_agent("surveyor", (0, 0.5, 0), modules=RACK, label="rack_full")
    rack_state(b, 4)
    b = clear_agent("surveyor", (0, -0.5, 0), modules=RACK, label="rack_two_dropped")
    rack_state(b, 2)
    cam((-1.7, -1.5, 1.15), (-0.1, 0, 0.3), focal=50)
    render("modules-fixes", "03_clear_rack_full_vs_dropped", look=CLEAR_LOOK)


BAY = {"eye": "optical", "belly": "cargo_bay"}


@shot("modules-fixes", "04_clear_bay_0_1_2")
def fix_bay_shot():
    stage_clear(rod_at=(-0.6, 1.4, 0))
    for x, n in ((-0.85, 0), (0.0, 1), (0.85, 2)):
        b = clear_agent("surveyor", (x, 0, 0), modules=BAY, label=f"bay_{n}")
        bay_state(b, n)
    # three on a line, side-on, camera at bay height: the window is on the bay's flank
    cam((0.0, -2.7, 0.22), (0.0, 0.0, 0.24), focal=40, fstop=8.0)
    render("modules-fixes", "04_clear_bay_0_1_2", look=CLEAR_LOOK)


@shot("modules-fixes", "05_insitu_vane_rival_lamp")
def fix_vane_backlit():
    """A rear silhouette cannot show a vane (edge-on, a 5 mm plate is a line); what makes a
    listening machine look wider is a rival's lamp raking its flank, so the plate throws a
    shadow band on the hull and the outline gains the stand-off."""
    stage_passage(fog=0.03)
    b = insitu_agent("surveyor", (0, 0, 0), modules=FLANK, label="vane", lamp_on=False, yaw=math.radians(20))
    fix_vane(b)
    E.add_light("rival_lamp", "SPOT", (1.6, -3.6, 0.6), 600.0, WHITE, size=0.05, spot_deg=50, blend=0.5, aim=(0.1, 0, 0.28))
    cam((1.3, -3.3, 0.55), (0.0, 0.0, 0.30), focal=55, fstop=5.6)
    render("modules-fixes", "05_insitu_vane_rival_lamp")


@shot("modules-fixes", "06_insitu_spike_planted_lamp")
def fix_spike_lamp():
    stage_passage(fog=0.02)
    b = insitu_agent("surveyor", (0, 0, 0), modules=SM, label="spike_planted", lamp_on=False, ride=0.15)
    fix_spike(b, planted=True)
    E.add_light("passing", "SPOT", (2.3, -1.9, 0.5), 600.0, WHITE, size=0.05, spot_deg=50, blend=0.5, aim=(0, 0, 0.1))
    # low, so the rod under the belly is seen against the lit floor behind it
    cam((1.45, -1.55, 0.12), (0, 0, 0.11), focal=50, fstop=5.6)
    render("modules-fixes", "06_insitu_spike_planted_lamp")


# ---- D5 team ---------------------------------------------------------------------------------
@shot("team", "01_clear_player_vs_rival")
def team_clear():
    stage_clear(rod_at=(-0.55, 1.1, 0))
    clear_agent("surveyor", (0, 0.52, 0), team="player", label="player")
    clear_agent("surveyor", (0, -0.52, 0), team="rival", wear=0.5, label="rival")
    cam((2.0, -1.75, 0.9), (0, 0, 0.22), focal=50)
    render("team", "01_clear_player_vs_rival", look=CLEAR_LOOK)


def _team_lamp(lit_team):
    stage_passage(fog=0.03)
    near, far = ("player", "rival") if lit_team == "player" else ("rival", "player")
    insitu_agent("surveyor", (0, 0, 0), team=near, label=near, lamp_on=True)
    insitu_agent("surveyor", (3.6, 0.3, 0), team=far, yaw=math.pi, label=far, lamp_on=False)
    cam((-1.4, -1.35, 0.78), (1.9, 0.1, 0.2), focal=40, fstop=5.6)


@shot("team", "03_insitu_rival_in_players_lamp")
def team_lamp_a():
    _team_lamp("player")
    render("team", "03_insitu_rival_in_players_lamp")


@shot("team", "04_insitu_player_in_rivals_lamp")
def team_lamp_b():
    _team_lamp("rival")
    render("team", "04_insitu_player_in_rivals_lamp")


# ---- D6 running-lights ---------------------------------------------------------------------------
@shot("running-lights", "01_clear_emissive_vs_retro")
def retro_clear():
    stage_clear(rod_at=(-0.55, 1.1, 0))
    b = clear_agent("surveyor", (0, 0.52, 0), label="emissive_fallback")
    strips(b, "emissive", strength=1.5, wide=True, status=False)
    b = clear_agent("surveyor", (0, -0.52, 0), label="retro")
    strips(b, "retro", wide=True)
    cam((1.9, -2.1, 0.85), (0, 0, 0.22), focal=50)
    render("running-lights", "01_clear_emissive_vs_retro", look=CLEAR_LOOK)


def _quiet_retro(found):
    # resting volume, not silt; and the "unfound" beam goes into the far wall short of the
    # machine, not past it down the passage -- a 50 deg cone pointed 'past' a machine 4.4 m
    # away still has it inside the cone, and the first version lit it plainly by bounce
    stage_passage(fog=0.012)
    b = insitu_agent("surveyor", (0, 0, 0), label="quiet", lamp_on=False)
    strips(b, "retro", wide=True)
    aim = (0, 0, 0.22) if found else (-1.6, -2.6, 0.5)
    E.add_light("rival_lamp", "SPOT", (-4.4, 1.0, 0.55), 600.0, WHITE, size=0.05, spot_deg=50, blend=0.5, aim=aim)
    cam((-4.2, 0.9, 0.62), (0.3, 0, 0.2), focal=40, fstop=5.6)


@shot("running-lights", "02_insitu_quiet_unfound")
def retro_dark():
    _quiet_retro(False)
    render("running-lights", "02_insitu_quiet_unfound")


@shot("running-lights", "03_insitu_quiet_found")
def retro_found():
    _quiet_retro(True)
    render("running-lights", "03_insitu_quiet_found")


@shot("running-lights", "04_insitu_wreck_found")
def retro_wreck():
    stage_passage(fog=0.03)
    b = make_agent("surveyor", at=(0, 0, 0), label="wreck", ride=0.055)
    wreck_pose(b, retro_strips=True)
    E.add_light("finder", "SPOT", (-1.5, -1.6, 0.42), 600.0, WHITE, size=0.05, spot_deg=54, blend=0.5, aim=(0.05, 0, 0.04))
    cam((-1.15, -1.30, 0.30), (0.02, 0, 0.07), focal=48, fstop=5.0)
    render("running-lights", "04_insitu_wreck_found")


@shot("running-lights", "05_insitu_fallback_strip_1p5")
def fallback_dark():
    stage_passage(fog=0.02)
    b = insitu_agent("surveyor", (0, 0, 0), label="quiet_fallback", lamp_on=False)
    strips(b, "emissive", strength=1.5, wide=True, status=False)
    cam((-1.7, -1.25, 0.6), (0, 0, 0.25), focal=45, fstop=5.6)
    render("running-lights", "05_insitu_fallback_strip_1p5")


# ---- D7 wear ------------------------------------------------------------------------------------
@shot("wear", "01_clear_fresh_035_085")
def wear_row():
    stage_clear(rod_at=(-0.6, 1.6, 0))
    for y, (w, mud, dust, scuff, label) in ((0.9, (0.0, 0.0, 0.0, 0.0, "fresh")), (0.0, (0.35, 0.5, 0.4, 0.4, "wear_035")), (-0.9, (0.85, 1.0, 0.8, 0.9, "wear_085"))):
        b = make_agent("surveyor", at=(0, y, 0), label=label)
        dress(b, "player", wear=w, mud=mud, dust=dust, scuff=scuff)
        emissives(b, 3.0, BONE, which=("light_strip",))
        emissives(b, 1.0, WHITE, which=("eye",))
        sonar(b, 0)
        b.lamp.data.energy = 0.0
    cam((2.1, -2.5, 1.0), (0, 0, 0.22), focal=45)
    render("wear", "01_clear_fresh_035_085", look=CLEAR_LOOK)


@shot("wear", "02_insitu_veteran_lamp")
def wear_lamp():
    stage_passage(fog=0.015)
    b = make_agent("surveyor", at=(0, 0, 0), label="veteran")
    dress(b, "player", wear=0.85, mud=1.0, dust=0.8, scuff=0.9)
    emissives(b, 3.0, BONE, which=("light_strip",))
    sonar(b, 0)
    lamp(b, on=True)
    E.add_light("passing", "SPOT", (2.3, -1.7, 0.55), 600.0, WHITE, size=0.05, spot_deg=50, blend=0.5, aim=(0, 0, 0.22))
    cam((1.6, -1.45, 0.5), (0, 0, 0.26), focal=50, fstop=4.5)
    render("wear", "02_insitu_veteran_lamp")


# ---- D8 damage ------------------------------------------------------------------------------------
RUNGS = [(0.0, 0.0), (1.1, 0.20), (2.2, 0.30), (3.3, 0.50), (4.5, 0.75), (5.8, 1.0)]


@shot("damage", "01_clear_ladder_side")
def damage_ladder():
    stage_clear(rod_at=(-0.75, 0, 0))
    for x, lv in RUNGS:
        if lv >= 1.0:
            b = make_agent("surveyor", at=(x, 0, 0), label="d100", ride=0.055)
            wreck_pose(b)
            continue
        ride = P.CHASSIS["surveyor"].ride_height * (0.75 if lv >= 0.75 else 1.0)
        b = make_agent("surveyor", at=(x, 0, 0), label=f"d{int(lv * 100):03d}", ride=ride)
        dress(b, "player", wear=0.35, mud=0.5, dust=0.4, scuff=0.4)
        emissives(b, 3.0, BONE, which=("light_strip",))
        emissives(b, 1.0, WHITE, which=("eye",))
        b.lamp.data.energy = 0.0
        damage(b, lv)
    cam((2.6, -9.0, 0.34), (2.6, 0, 0.34), ortho=7.4)
    render("damage", "01_clear_ladder_side", res=(2400, 600), look=CLEAR_LOOK)


@shot("damage", "02_insitu_075_own_lamp")
def damage_limp():
    stage_passage(fog=0.022)
    b = insitu_agent("surveyor", (0, 0, 0), label="d075", ride=P.CHASSIS["surveyor"].ride_height * 0.75)
    damage(b, 0.75)
    cam((-2.5, -1.5, 1.15), (1.6, 0, 0.30), focal=38, fstop=5.6)
    render("damage", "02_insitu_075_own_lamp")


@shot("damage", "04_clear_sonar_bar_7_4_2")
def damage_bar():
    """The 0.20 rung close enough to count: three heads face-on, 7 / 4 / 2 elements lit."""
    stage_clear(rod_at=(0.3, 0.75, 0))
    for y, n in ((0.34, 7), (0.0, 4), (-0.34, 2)):
        b = make_agent("surveyor", at=(0, y, 0), label=f"bar{n}")
        dress(b, "player", wear=0.35, mud=0.5, dust=0.4, scuff=0.4)
        emissives(b, 3.0, BONE, which=("light_strip",))
        emissives(b, 1.0, WHITE, which=("eye",))
        b.lamp.data.energy = 0.0
        sonar(b, n)
    cam((1.45, 0.0, 0.60), (0.33, 0.0, 0.50), focal=50, fstop=8.0)
    render("damage", "04_clear_sonar_bar_7_4_2", look=CLEAR_LOOK)


# ---- D9 own-lamp ------------------------------------------------------------------------------------
def _av02():
    stage_passage(fog=0.022)
    insitu_agent("surveyor", (0, 0, 0), label="surveyor")
    cam((-2.5, -1.5, 1.15), (1.6, 0, 0.30), focal=38, fstop=5.6)


@shot("own-lamp", "01_clear_same_frame_plus3stops")
def ownlamp_plus3():
    _av02()
    render("own-lamp", "01_clear_same_frame_plus3stops", exposure=3.0)


@shot("own-lamp", "02_insitu_own_lamp")
def ownlamp():
    _av02()
    render("own-lamp", "02_insitu_own_lamp")


@shot("own-lamp", "03_insitu_rival_view_beam_in_face")
def ownlamp_rival():
    # resting cave volume (ART-DIRECTION 2.6: 0.008-0.012), not stirred silt -- at 0.03 the
    # in-line scatter over 5 m washed the whole frame grey and the machine vanished
    stage_passage(fog=0.010)
    insitu_agent("surveyor", (0, 0, 0), label="surveyor")
    cam((5.2, 0.95, 0.72), (0, 0, 0.32), focal=40, fstop=5.6)
    render("own-lamp", "03_insitu_rival_view_beam_in_face")


@shot("own-lamp", "04_insitu_director_72deg")
def ownlamp_above():
    stage_passage(fog=0.02)
    insitu_agent("surveyor", (0, 0, 0), label="surveyor")
    # z = 5.0 was inside the displaced roof of a 4.8 m passage (a black frame); 3.6 m up at
    # ~65 deg is as high as the director's elevation can go in this passage
    cam((-0.7, -0.45, 3.6), (0.9, 0, 0.0), focal=32)
    render("own-lamp", "04_insitu_director_72deg")


# ---- D10 machine-daylight --------------------------------------------------------------------------
def day_agent(chassis, at, yaw=0.0, wear=0.35, mud=0.3, dust=0.2, scuff=0.3, label=None, modules=None, **kw):
    b = make_agent(chassis, modules, at=at, yaw=yaw, label=label, **kw)
    dress(b, "player", wear=wear, mud=mud, dust=dust, scuff=scuff)
    emissives(b, 3.0, BONE, which=("light_strip",))       # emissives vanish in daylight: left ON to show it
    sonar(b, 0)
    lamp(b, on=False)                                     # the reflector is a dark disc
    return b


@shot("machine-daylight", "01_clear_surveyor_daylight_3q")
def day_3q():
    stage_yard()
    day_agent("surveyor", (0, 0, 0), label="surveyor")
    cam((2.0, -1.65, 0.85), (0, 0, 0.25), focal=50, fstop=4.0)
    render("machine-daylight", "01_clear_surveyor_daylight_3q", look=CLEAR_LOOK)


@shot("machine-daylight", "02_clear_fresh_vs_veteran")
def day_fresh_vet():
    stage_yard()
    day_agent("surveyor", (0, 0.6, 0), wear=0.0, mud=0.0, dust=0.0, scuff=0.0, label="fresh")
    day_agent("surveyor", (0, -0.6, 0), wear=0.85, mud=1.0, dust=0.8, scuff=0.9, label="veteran")
    cam((2.3, -2.0, 1.0), (0, 0, 0.22), focal=45, fstop=4.0)
    render("machine-daylight", "02_clear_fresh_vs_veteran", look=CLEAR_LOOK)


def _collar_scene(sun=False):
    stage_yard(sun=sun)
    yaw = math.atan2(5.0 - 4.5, -7.0 + 4.9)
    day_agent("surveyor", (-4.9, 4.5, 0), yaw=yaw, label="surveyor")
    cam((-1.4, 2.6, 1.1), (-6.8, 5.0, 2.6), focal=28, fstop=5.6)


@shot("machine-daylight", "03_insitu_at_the_collar")
def day_collar():
    _collar_scene()
    render("machine-daylight", "03_insitu_at_the_collar")


@shot("machine-daylight", "04_insitu_four_in_the_yard")
def day_four():
    stage_yard()
    for ch, at, yaw in (("scout", (-2.0, 3.2, 0), 2.6), ("surveyor", (-3.0, 2.0, 0), 2.9), ("hauler", (-1.4, 1.2, 0), 2.4), ("swimmer", (-3.9, 3.4, 0), 3.1)):
        day_agent(ch, at, yaw=yaw, label=ch)
    cam((1.6, -1.2, 1.5), (-3.6, 3.4, 0.5), focal=35, fstop=5.6)
    render("machine-daylight", "04_insitu_four_in_the_yard")


@shot("machine-daylight", "05_variant_low_sun")
def day_sun():
    _collar_scene(sun=True)
    render("machine-daylight", "05_variant_low_sun")


@shot("machine-daylight", "06_insitu_veteran_in_the_yard")
def day_veteran():
    stage_yard()
    day_agent("surveyor", (-3.0, 3.0, 0), yaw=2.2, wear=0.85, mud=1.0, dust=0.8, scuff=0.9, label="veteran")
    cam((-1.7, 1.6, 0.55), (-3.1, 3.0, 0.26), focal=50, fstop=3.5)
    render("machine-daylight", "06_insitu_veteran_in_the_yard")


# ---- D11 nine-pixel: one frame, one camera, seven machines -----------------------------------------
def _single(label, fn):
    stage_passage(fog=0.045)
    fn()
    cam((-1.62, -0.10, 0.30), (2.6, 0.02, 0.06), focal=45, fstop=6.0)
    render("nine-pixel", label)


@shot("nine-pixel", "01_src_scout")
def single_scout():
    _single("01_src_scout", lambda: insitu_agent("scout", (0, 0, 0), label="scout", down=14.0))


@shot("nine-pixel", "02_src_surveyor")
def single_surveyor():
    _single("02_src_surveyor", lambda: insitu_agent("surveyor", (0, 0, 0), label="surveyor", down=14.0))


@shot("nine-pixel", "03_src_hauler")
def single_hauler():
    _single("03_src_hauler", lambda: insitu_agent("hauler", (0.55, 0, 0), label="hauler", down=14.0))


@shot("nine-pixel", "04_src_swimmer")
def single_swimmer():
    _single("04_src_swimmer", lambda: insitu_agent("swimmer", (0, 0, 0), modules=_swim_mods(), label="swimmer", down=14.0))


@shot("nine-pixel", "05_src_rival")
def single_rival():
    _single("05_src_rival", lambda: insitu_agent("surveyor", (0, 0, 0), team="rival", label="rival", down=14.0))


def _damaged():
    b = insitu_agent("surveyor", (0, 0, 0), label="damaged075", down=14.0, ride=P.CHASSIS["surveyor"].ride_height * 0.75)
    damage(b, 0.75)


@shot("nine-pixel", "06_src_damaged075")
def single_damaged():
    _single("06_src_damaged075", _damaged)


def _dead():
    b = make_agent("surveyor", at=(0, 0, 0), label="wreck", ride=0.055)
    wreck_pose(b)
    E.add_light("finder", "SPOT", (-1.7, -0.3, 0.45), 600.0, WHITE, size=0.05, spot_deg=54, blend=0.5, aim=(0.05, 0, 0.04))


@shot("nine-pixel", "07_src_wreck")
def single_wreck():
    _single("07_src_wreck", _dead)



# =========================================================================================
# extras the inventory missed but that belong to the machines: the head as the face, the
# hardpoints the surface uses, the gait, a human for scale, the underside
# =========================================================================================
from agent_model.motion import Mover  # noqa: E402


def mannequin(at, height=1.75):
    """A scale figure only: cylinders and a sphere, matte grey. Not a character."""
    grey = flat("mannequin", (0.32, 0.31, 0.30), rough=0.8)
    a = Vector(at)
    s = height / 1.75
    for side in (1, -1):
        G.set_material(G.cyl("mq_leg", 0.075 * s, 0.06 * s, 0.82 * s, a + Vector((0, side * 0.10 * s, 0.41 * s)), verts=12), grey)
        G.set_material(G.cyl("mq_arm", 0.045 * s, 0.04 * s, 0.62 * s, a + Vector((0, side * 0.26 * s, 1.10 * s)), verts=10), grey)
        G.set_material(G.sphere("mq_shoulder", 0.075 * s, a + Vector((0, side * 0.22 * s, 1.42 * s)), seg=12), grey)
    G.set_material(G.cyl("mq_hip", 0.17 * s, 0.17 * s, 0.16 * s, a + Vector((0, 0, 0.88 * s)), verts=14), grey)
    torso = G.cyl("mq_torso", 0.16 * s, 0.18 * s, 0.52 * s, a + Vector((0, 0, 1.20 * s)), verts=14)
    torso.scale = (0.72, 1.0, 1.0)
    G.set_material(torso, grey)
    G.set_material(G.cyl("mq_neck", 0.05 * s, 0.05 * s, 0.08 * s, a + Vector((0, 0, 1.50 * s)), verts=10), grey)
    G.set_material(G.sphere("mq_head", 0.11 * s, a + Vector((0, 0, 1.64 * s)), seg=16), grey)


HEAD_C = (0.335, 0.0, 0.525)     # the Surveyor's tilt-axis centre at ride 0.32 (build.py's B/T arithmetic)


@shot("head", "01_clear_head_macro")
def head_macro():
    stage_clear(rod_at=(0.1, 0.55, 0.0))
    b = clear_agent("surveyor", (0, 0, 0), label="surveyor")
    emissives(b, 0.0, which=("eye",))            # lamp off: the reflector is a dark disc
    cam((0.86, -0.42, 0.66), HEAD_C, focal=85, fstop=5.6)
    render("head", "01_clear_head_macro", look=CLEAR_LOOK)


@shot("head", "02_clear_reflector_off_vs_on")
def head_reflector():
    stage_clear(rod_at=(0.1, 0.9, 0.0))
    b = clear_agent("surveyor", (0, 0.30, 0), label="lamp_off")
    emissives(b, 0.0, which=("eye",))
    b = clear_agent("surveyor", (0, -0.30, 0), label="lamp_on")
    lamp(b, on=True, energy=40.0, down_deg=10.0)    # low, so the pool does not blow the frame
    emissives(b, 30.0, WHITE, which=("eye",))       # but the disc itself must read against a 1000 W key
    cam((2.1, -0.02, 0.62), (0.33, 0, 0.50), focal=60, fstop=8.0)
    render("head", "02_clear_reflector_off_vs_on", look=CLEAR_LOOK)


@shot("head", "03_insitu_head_in_rival_lamp")
def head_insitu():
    stage_passage(fog=0.025)
    b = insitu_agent("surveyor", (0, 0, 0), label="surveyor", lamp_on=False)
    look(b, (2.0, -1.2, 0.5))
    E.add_light("rival_lamp", "SPOT", (1.9, -1.1, 0.58), 600.0, WHITE, size=0.05, spot_deg=50, blend=0.5, aim=(0.3, 0, 0.45))
    cam((1.05, -0.62, 0.62), HEAD_C, focal=70, fstop=4.5)
    render("head", "03_insitu_head_in_rival_lamp")


@shot("hardpoints", "01_clear_deck_macro")
def hardpoints_macro():
    stage_clear(rod_at=(-0.55, 0.45, 0.0))
    b = clear_agent("surveyor", (0, 0, 0), label="surveyor")
    cam((-0.95, -0.62, 0.86), (-0.10, 0.0, 0.47), focal=70, fstop=5.6)
    render("hardpoints", "01_clear_deck_macro", look=CLEAR_LOOK)


@shot("hardpoints", "02_clear_tail_ports")
def hardpoints_tail():
    stage_clear(rod_at=(0.35, 0.45, 0.0))
    b = clear_agent("surveyor", (0, 0, 0), label="surveyor")
    cam((-0.88, -0.48, 0.42), (-0.28, -0.02, 0.37), focal=70, fstop=5.6)
    render("hardpoints", "02_clear_tail_ports", look=CLEAR_LOOK)


@shot("hardpoints", "03_insitu_underside")
def underside():
    stage_clear(gauge_y=0.0, rod_at=(0.6, 0.55, 0.0))
    clear_agent("surveyor", (0, 0, 0), label="surveyor")
    cam((0.95, -0.85, 0.04), (0.0, 0.0, 0.26), focal=40, fstop=5.6)
    render("hardpoints", "03_insitu_underside", look=CLEAR_LOOK)


def _walkers(rows, gait="trot", speed=0.5, delays=(0.0, 0.25, 0.5), team="player", lamp_on=False, seconds=2.0):
    """Several machines walking, each started a little later, so one frame shows the gait
    at three phases. Feet are keyed empties; the IK solves the legs at the render frame."""
    movers = []
    for (at, label), dly in zip(rows, delays):
        b = make_agent("surveyor", at=at, label=label)
        dress(b, team, wear=0.35, mud=0.5, dust=0.4, scuff=0.4)
        emissives(b, 3.0, BONE, which=("light_strip",))
        emissives(b, 1.0 if not lamp_on else 3.0, WHITE, which=("eye",))
        sonar(b, 0)
        if lamp_on:
            lamp(b, on=True, down_deg=12.0)
        else:
            b.lamp.data.energy = 0.0
        m = Mover(b)
        m.stand(0.2 + dly)
        m.walk(seconds, speed=speed, gait=gait)
        m.finish()
        movers.append(m)
    return movers


@shot("gait", "01_clear_trot_three_phases")
def gait_clear():
    stage_clear(gauge_y=None, rod_at=(-0.4, 1.7, 0.0))
    _walkers([((0, 1.0, 0), "phase_a"), ((0, 0.0, 0), "phase_b"), ((0, -1.0, 0), "phase_c")])
    bpy.context.scene.frame_set(1 + 24 + 8)
    cam((2.6, -2.4, 1.0), (0.45, 0, 0.22), focal=45)
    render("gait", "01_clear_trot_three_phases", look=CLEAR_LOOK)


@shot("gait", "02_clear_trot_side_ortho")
def gait_side():
    stage_clear(rod_at=(-0.5, 0, 0.0))
    _walkers([((0.0, 0, 0), "phase_a"), ((1.3, 0, 0), "phase_b"), ((2.6, 0, 0), "phase_c")])
    bpy.context.scene.frame_set(1 + 24 + 8)
    cam((1.7, -8.0, 0.3), (1.7, 0, 0.3), ortho=4.6)
    render("gait", "02_clear_trot_side_ortho", res=(1800, 600), look=CLEAR_LOOK)


@shot("gait", "03_insitu_walking_own_lamp")
def gait_insitu():
    stage_passage(fog=0.05)
    _walkers([((0, 0, 0), "walker")], delays=(0.0,), lamp_on=True, seconds=1.5)
    bpy.context.scene.frame_set(1 + 5 + 14)
    cam((-1.72, -0.10, 0.30), (2.6, 0.02, 0.06), focal=45, fstop=6.0)
    render("gait", "03_insitu_walking_own_lamp")


@shot("chassis-lineup", "05_clear_human_scale")
def human_scale():
    stage_clear(gauge_y=0.45, rod_at=None)
    for ch, y in LINEUP:
        clear_agent(ch, (0, y, 0), label=ch)
    _later(lambda: mannequin((-0.35, 2.45, 0)))
    cam((6.2, -4.2, 2.0), (0.0, 0.35, 0.6), focal=60, fstop=8.0)
    render("chassis-lineup", "05_clear_human_scale", look=CLEAR_LOOK)


# =========================================================================================
if __name__ == "__main__":
    names = list(SHOTS) if A.shots == "all" else [s.strip() for s in A.shots.split(",") if s.strip()]
    import time
    import traceback
    for nm in names:
        if nm not in SHOTS:
            raise SystemExit(f"unknown shot {nm}; known: {', '.join(SHOTS)}")
        folder, fname, fn = SHOTS[nm]
        if A.skip_existing and os.path.exists(os.path.join(A.out_dir, folder, fname + ".png")):
            print(f"=== skip {nm} (exists)")
            continue
        print(f"=== {nm} -> {folder}/{fname}")
        t0 = time.time()
        try:
            fn()
            print(f"=== ok {nm} {time.time() - t0:.0f} s")
        except Exception:
            traceback.print_exc()
            print(f"=== FAILED {nm}")
    print("MACHINES DONE")
