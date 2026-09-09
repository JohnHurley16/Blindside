"""The teaching space: the pit-head as a place where machines are taught, and the cave stop.

Vision-board probe for docs/art/vision/teaching/. Run with a Blender install:

  blender -b -P docs/art/vision/teaching/teaching_probe.py -- --shot g1_junction_ots --out <ABS>.png

Nothing here is production art. It is a procedural stand-in for a surface the repo does not
draw, built from the same castings language as the ruins probes (wet cast iron, no paint,
the 1.2 m module) and the agent_model walker, so the designer can see the teaching act in
a place rather than read about it.

What it builds (all parametric, all guesses -- NOTES.md lists them):
  terrain      a spoil flat with rough ground and heaps beyond the works
  collar       the shaft mouth: a rectangular timbered shaft, cast-iron collar frame, a fence
  headframe    a four-legged A-frame with a sheave and backstays, 9 m, the one bright bearing
  winding_house roofless stone walls with the dead engine's drum and flywheel inside
  winch        the small modern winch the teams rigged, and the kibble on its cable
  lean_to      the yard: roof, bench, terminal, rack, crates, a charge cable
  course       Phase 2's Corridor(seed) extruded as 1.2 m hoarding walls at 0.6 m/cell
  mannequin    a person, for scale and for the act (no face; a hood)
  pendant      the wired teaching pendant: screen, block keys, scrub wheel, cable
  terminal     the bench terminal: screen and a rail of block keys
  post         the listening post at the collar: cable drum, hydrophone cable, small screen

Rigs: DAYLIGHT = uniform overcast sky in the shaft's own colour (0.60, 0.74, 1.00) plus one
soft cloud break; no sun by default (--sky sun adds one for comparison). CLEAR = neutral grey
studio world plus one 45-degree key, for product shots. In-situ frames use the same sky at
dusk / night strengths, and the only emissives are the screens.

Every agent gets the three fixes ART-DIRECTION.md 0 / 2.5 / 4.3 ask for: lamp re-aimed
Euler((0,-pi/2,0)) and tilted down, lamp white, emissives <= 3 in BONE / EMBER, no cyan.
"""
import argparse
import json
import math
import os
import random
import sys

ROOT = r"C:/Users/jackh/documents/programming/Blindside"
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "docs/art/probes"))

import bpy  # noqa: E402
from mathutils import Vector, Euler, Matrix  # noqa: E402

from agent_model import params as P  # noqa: E402
from agent_model import geometry as G  # noqa: E402
from agent_model import materials as M  # noqa: E402
from agent_model.build import build_agent  # noqa: E402
from agent_model.motion import Mover  # noqa: E402
import p2_env as E  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))

ap = argparse.ArgumentParser()
ap.add_argument("--shot", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--samples", type=int, default=40)
ap.add_argument("--res", default="960x600")
ap.add_argument("--seed", type=int, default=104, help="corridor seed (phase2 DEMONSTRATION_SEEDS[0])")
ap.add_argument("--sky", default=None, help="override the sky rig: overcast|drizzle|dusk|night|sun|clear")
ap.add_argument("--pendant-img", default=os.path.join(HERE, "g2_02_pendant-screen-mock.png"))
ap.add_argument("--terminal-img", default=os.path.join(HERE, "g2_06_terminal-screen-mock.png"))
ap.add_argument("--replay-img", default=os.path.join(HERE, "_screens", "terminal_replay.png"))
ap.add_argument("--post-img", default=os.path.join(HERE, "_screens", "post_belief.png"))
ap.add_argument("--cave-img", default=os.path.join(HERE, "_screens", "pendant_cave.png"))
ap.add_argument("--exposure", type=float, default=0.0)
ap.add_argument("--yard-lamp", type=float, default=0.0,
                help="watts of a work light hung under the lean-to roof (a proposal; 0 = none)")
ap.add_argument("--meta", default=None, help="write shot metadata (camera, junction) as JSON here")
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
A = ap.parse_args(argv)
RES = tuple(int(v) for v in A.res.split("x"))
CELL = 0.6

# ---------------------------------------------------------------------------------------
# palette (ART-DIRECTION 3.1, 5.2; phase1/view/palette.py)
# ---------------------------------------------------------------------------------------
BONE = (0.949, 0.902, 0.824)
EMBER = (1.000, 0.478, 0.184)
SKY = (0.60, 0.74, 1.00)                     # the shaft's own 12000 K
WET_IRON = (0.075, 0.038, 0.021)
BEARING = (0.52, 0.50, 0.48)
SPOIL_DRY = (0.340, 0.260, 0.175)            # #9E8B74
PALE_SHELL, GRAPHITE = (0.66, 0.63, 0.57), (0.050, 0.052, 0.058)
RIVAL_SHELL, RIVAL_CHASSIS = (0.070, 0.062, 0.055), (0.40, 0.36, 0.32)
LAMP_WHITE = (1.00, 0.98, 0.95)

META = {}


# ---------------------------------------------------------------------------------------
# materials
# ---------------------------------------------------------------------------------------
def _principled(name):
    m, nt, out = M._new(name)
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(b.outputs[0], out.inputs[0])
    return m, nt, b


def _world_noise(nt, scale, detail=6.0, rough=0.6, coord="Position"):
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    tex = nt.nodes.new("ShaderNodeTexNoise")
    tex.inputs["Scale"].default_value = scale
    tex.inputs["Detail"].default_value = detail
    tex.inputs["Roughness"].default_value = rough
    nt.links.new(geo.outputs[coord], tex.inputs["Vector"])
    return tex


def spoil_mat(wet=0.7, name="spoil"):
    """The spoil flat: the rock's own buff, darkened and glossed by rain, gravel bump."""
    m, nt, b = _principled(name)
    n, L = nt.nodes, nt.links.new
    tex = _world_noise(nt, 0.35, detail=8.0)
    fine = _world_noise(nt, 9.0, detail=6.0)
    k = 1.0 - 0.45 * wet
    lo = tuple(c * k * 0.55 for c in SPOIL_DRY)
    hi = tuple(c * k * 1.15 for c in SPOIL_DRY)
    ramp = n.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.35
    ramp.color_ramp.elements[0].color = (*lo, 1)
    ramp.color_ramp.elements[1].position = 0.70
    ramp.color_ramp.elements[1].color = (*hi, 1)
    L(tex.outputs["Fac"], ramp.inputs["Fac"])
    L(ramp.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.92 - 0.45 * wet
    b.inputs["Specular IOR Level"].default_value = 0.4
    bump = n.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.5
    L(fine.outputs["Fac"], bump.inputs["Height"])
    L(bump.outputs["Normal"], b.inputs["Normal"])
    return m


def hardstanding_mat(wet=0.7, name="hardstanding"):
    """Setts / slab in front of the winding house, puddled where it is worn."""
    m, nt, b = _principled(name)
    n, L = nt.nodes, nt.links.new
    geo = n.new("ShaderNodeNewGeometry")
    vor = n.new("ShaderNodeTexVoronoi")
    vor.inputs["Scale"].default_value = 1.6
    vor.feature = "DISTANCE_TO_EDGE"
    L(geo.outputs["Position"], vor.inputs["Vector"])
    joint = n.new("ShaderNodeMapRange")
    joint.inputs["From Min"].default_value = 0.0
    joint.inputs["From Max"].default_value = 0.05
    joint.clamp = True
    L(vor.outputs["Distance"], joint.inputs["Value"])
    mottle = _world_noise(nt, 2.5, detail=5.0)
    base = n.new("ShaderNodeMix")
    base.data_type = "RGBA"
    base.inputs["A"].default_value = (0.11, 0.10, 0.09, 1)
    base.inputs["B"].default_value = (0.20, 0.185, 0.165, 1)
    L(mottle.outputs["Fac"], base.inputs["Factor"])
    col = n.new("ShaderNodeMix")
    col.data_type = "RGBA"
    col.inputs["A"].default_value = (0.04, 0.035, 0.03, 1)      # the joint, dark and wet
    L(base.outputs["Result"], col.inputs["B"])
    L(joint.outputs["Result"], col.inputs["Factor"])
    # puddles: a low-frequency noise threshold, driven by wet
    pud = _world_noise(nt, 0.22, detail=3.0)
    pudm = n.new("ShaderNodeMapRange")
    pudm.inputs["From Min"].default_value = 0.62 - 0.14 * wet
    pudm.inputs["From Max"].default_value = 0.66 - 0.14 * wet
    pudm.clamp = True
    L(pud.outputs["Fac"], pudm.inputs["Value"])
    dark = n.new("ShaderNodeMix")
    dark.data_type = "RGBA"
    dark.inputs["B"].default_value = (0.03, 0.03, 0.03, 1)
    L(col.outputs["Result"], dark.inputs["A"])
    L(pudm.outputs["Result"], dark.inputs["Factor"])
    L(dark.outputs["Result"], b.inputs["Base Color"])
    rough = n.new("ShaderNodeMix")
    rough.data_type = "FLOAT"
    rough.inputs["A"].default_value = 0.75 - 0.35 * wet
    rough.inputs["B"].default_value = 0.03
    L(pudm.outputs["Result"], rough.inputs["Factor"])
    L(rough.outputs["Result"], b.inputs["Roughness"])
    b.inputs["Specular IOR Level"].default_value = 0.5
    bump = n.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.6
    L(joint.outputs["Result"], bump.inputs["Height"])
    L(bump.outputs["Normal"], b.inputs["Normal"])
    return m


def iron_mat(name="wet_iron"):
    """Cast iron wet a century: ART-DIRECTION 5.2. Near-black, ferrous, matte, scaled. Not orange."""
    m, nt, b = _principled(name)
    n, L = nt.nodes, nt.links.new
    tex = _world_noise(nt, 5.0, detail=9.0)
    ramp = n.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.30
    ramp.color_ramp.elements[0].color = (0.020, 0.016, 0.013, 1)
    ramp.color_ramp.elements[1].position = 0.75
    ramp.color_ramp.elements[1].color = (*WET_IRON, 1)
    L(tex.outputs["Fac"], ramp.inputs["Fac"])
    L(ramp.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Metallic"].default_value = 0.0
    r = n.new("ShaderNodeMath")
    r.operation = "MULTIPLY_ADD"
    r.inputs[1].default_value = -0.18
    r.inputs[2].default_value = 0.94
    L(tex.outputs["Fac"], r.inputs[0])
    L(r.outputs[0], b.inputs["Roughness"])
    fine = _world_noise(nt, 40.0, detail=6.0)
    bump = n.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.3
    L(fine.outputs["Fac"], bump.inputs["Height"])
    L(bump.outputs["Normal"], b.inputs["Normal"])
    return m


def bearing_mat(name="bearing_steel"):
    """Still in use, polished bright by the work itself: the sheave groove, the new cable."""
    return M.bare_metal(name, BEARING, 0.30)


def galv_mat(name="galvanised"):
    """The modern teams' kit in steel: fence, kibble, winch frame. Grey, cheap, temporary."""
    m, nt, b = _principled(name)
    b.inputs["Base Color"].default_value = (0.42, 0.43, 0.44, 1)
    b.inputs["Metallic"].default_value = 0.85
    b.inputs["Roughness"].default_value = 0.48
    return m


def timber_mat(name="timber"):
    m, nt, b = _principled(name)
    n, L = nt.nodes, nt.links.new
    tex = _world_noise(nt, 3.0, detail=7.0, coord="Position")
    ramp = n.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.35
    ramp.color_ramp.elements[0].color = (0.06, 0.045, 0.03, 1)
    ramp.color_ramp.elements[1].position = 0.7
    ramp.color_ramp.elements[1].color = (0.16, 0.115, 0.07, 1)
    L(tex.outputs["Fac"], ramp.inputs["Fac"])
    L(ramp.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.8
    return m


def sheet_mat(name="hoarding"):
    """Corrugated sheet, rusted: the course walls and the lean-to roof. Bands in object X."""
    m, nt, b = _principled(name)
    n, L = nt.nodes, nt.links.new
    tc = n.new("ShaderNodeTexCoord")
    wave = n.new("ShaderNodeTexWave")
    wave.wave_type = "BANDS"
    wave.bands_direction = "X"
    wave.inputs["Scale"].default_value = 13.0        # 77 mm pitch
    wave.inputs["Distortion"].default_value = 0.0
    L(tc.outputs["Object"], wave.inputs["Vector"])
    tex = _world_noise(nt, 2.2, detail=8.0)
    ramp = n.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.32
    ramp.color_ramp.elements[0].color = (0.018, 0.016, 0.014, 1)
    ramp.color_ramp.elements[1].position = 0.72
    ramp.color_ramp.elements[1].color = (0.085, 0.048, 0.026, 1)
    L(tex.outputs["Fac"], ramp.inputs["Fac"])
    L(ramp.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Metallic"].default_value = 0.3
    r = n.new("ShaderNodeMath")
    r.operation = "MULTIPLY_ADD"
    r.inputs[1].default_value = -0.25
    r.inputs[2].default_value = 0.82
    L(tex.outputs["Fac"], r.inputs[0])
    L(r.outputs[0], b.inputs["Roughness"])
    bump = n.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.85
    bump.inputs["Distance"].default_value = 0.02
    L(wave.outputs["Fac"], bump.inputs["Height"])
    L(bump.outputs["Normal"], b.inputs["Normal"])
    return m


def kit_mat(rgb, rough=0.5, name="kit", coat=0.2):
    """The modern kit: pale enamel or dark polymer. Clean because it is new, not because it shines."""
    m, nt, b = _principled(name)
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Coat Weight"].default_value = coat
    b.inputs["Coat Roughness"].default_value = 0.2
    return m


def jacket_mat(name="jacket"):
    m, nt, b = _principled(name)
    b.inputs["Base Color"].default_value = (0.045, 0.055, 0.05, 1)
    b.inputs["Roughness"].default_value = 0.55
    b.inputs["Specular IOR Level"].default_value = 0.45
    return m


def screen_mat(image_path, strength=1.5, name="screen"):
    """An emissive screen with the picture on it. The one bitmap in the probe, and it is
    a picture OF a screen, not a world material: see NOTES.md."""
    m, nt, out = M._new(name)
    n, L = nt.nodes, nt.links.new
    em = n.new("ShaderNodeEmission")
    em.inputs["Strength"].default_value = strength
    if image_path and os.path.exists(image_path):
        img = bpy.data.images.load(image_path)
        tex = n.new("ShaderNodeTexImage")
        tex.image = img
        tex.interpolation = "Cubic"
        L(tex.outputs["Color"], em.inputs["Color"])
    else:
        em.inputs["Color"].default_value = (0.05, 0.07, 0.10, 1)
        print(f"WARNING screen image missing: {image_path}")
    gl = n.new("ShaderNodeBsdfGlossy")
    gl.inputs["Roughness"].default_value = 0.08
    gl.inputs["Color"].default_value = (1, 1, 1, 1)
    mix = n.new("ShaderNodeMixShader")
    mix.inputs["Fac"].default_value = 0.06
    L(em.outputs[0], mix.inputs[1])
    L(gl.outputs[0], mix.inputs[2])
    L(mix.outputs[0], out.inputs[0])
    return m


def dark_rock_mat(name="shaft_rock"):
    return E.rock(name, albedo_lo=0.02, albedo_hi=0.16, warm=1.0, wet=0.8, bed_scale=1.4, fracture_scale=7.0)


MATS = {}


def mats():
    """Every material the surface uses, built once per scene; keys already present are kept."""
    makers = dict(
        spoil=lambda: spoil_mat(), hard=lambda: hardstanding_mat(), iron=iron_mat, bearing=bearing_mat,
        galv=galv_mat, timber=timber_mat, sheet=sheet_mat,
        stone=lambda: E.rock("stone", albedo_lo=0.09, albedo_hi=0.34, warm=0.75, wet=0.55, bed_scale=2.2, fracture_scale=5.0),
        pale=lambda: kit_mat((0.62, 0.60, 0.55), 0.45, "kit_pale"),
        dark=lambda: kit_mat((0.11, 0.115, 0.12), 0.5, "kit_dark"),
        key=lambda: kit_mat((0.85, 0.82, 0.76), 0.35, "kit_key", coat=0.4),
        jacket=jacket_mat, cable=lambda: M.rubber("cable"), shaft=dark_rock_mat,
        pilot=lambda: glow_mat((0.478, 0.400, 0.314), 2.5, "pilot_warm_dim"),
    )
    for k, mk in makers.items():
        if k not in MATS:
            MATS[k] = mk()
    return MATS


def glow_mat(rgb, strength, name="glow"):
    m, nt, out = M._new(name)
    e = nt.nodes.new("ShaderNodeEmission")
    e.inputs["Color"].default_value = (*rgb, 1)
    e.inputs["Strength"].default_value = strength
    nt.links.new(e.outputs[0], out.inputs[0])
    return m


# ---------------------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------------------
def col_new(name):
    return G.new_collection(name)


def put(o, mat, col=None):
    if mat is not None:
        G.set_material(o, mat)
    if col is not None:
        for c in list(o.users_collection):
            c.objects.unlink(o)
        col.objects.link(o)
    return o


def xform(objs, at=(0, 0, 0), yaw=0.0, pitch=0.0):
    """Apply a placement matrix (translate, yaw about Z, pitch about Y) to objects built at the origin."""
    Mx = Matrix.Translation(Vector(at)) @ Matrix.Rotation(yaw, 4, "Z") @ Matrix.Rotation(pitch, 4, "Y")
    for o in objs:
        o.matrix_world = Mx @ o.matrix_world
    return Mx


def screen_plane(name, w, h, loc, rot, mat, col):
    bpy.ops.mesh.primitive_plane_add(size=1.0, location=(0, 0, 0))
    o = bpy.context.object
    o.name = name
    o.scale = (w, h, 1.0)
    bpy.ops.object.transform_apply(scale=True)
    o.rotation_euler = Euler(rot)
    o.location = Vector(loc)
    bpy.context.view_layer.update()
    o.matrix_world = o.matrix_world.copy()
    return put(o, mat, col)


# ---------------------------------------------------------------------------------------
# the surface
# ---------------------------------------------------------------------------------------
def terrain(col, works_rect=((-30, -22), (95, 40)), size=300, wet=0.7):
    """A spoil flat: flat inside works_rect, rising rough ground outside, heaps at the edges."""
    m = mats()
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=150, y_subdivisions=150, size=size, location=(20, 0, 0))
    g = bpy.context.object
    g.name = "terrain"
    vg = g.vertex_groups.new(name="rough")
    (x0, y0), (x1, y1) = works_rect
    for v in g.data.vertices:
        wx, wy = v.co.x + 20, v.co.y
        dx = max(x0 - wx, 0, wx - x1)
        dy = max(y0 - wy, 0, wy - y1)
        d = math.hypot(dx, dy)
        w = min(max((d - 3.0) / 14.0, 0.0), 1.0)
        vg.add([v.index], w, "REPLACE")
    t = bpy.data.textures.new("terrain_noise", "CLOUDS")
    t.noise_scale = 14.0
    t.noise_depth = 4
    d = g.modifiers.new("disp", "DISPLACE")
    d.texture = t
    d.strength = 3.0
    d.mid_level = 0.45
    d.vertex_group = "rough"
    t2 = bpy.data.textures.new("terrain_fine", "CLOUDS")
    t2.noise_scale = 1.4
    t2.noise_depth = 3
    d2 = g.modifiers.new("disp2", "DISPLACE")
    d2.texture = t2
    d2.strength = 0.10
    d2.mid_level = 0.5
    g.data.shade_smooth()
    put(g, m["spoil"], col)
    # spoil heaps beyond the course and the works
    rng = random.Random(3)
    for i, (hx, hy, r, h) in enumerate([(120, 30, 26, 9), (105, -40, 22, 7), (-45, 30, 20, 6),
                                        (60, 62, 24, 8), (-40, -42, 18, 5), (150, -5, 30, 11)]):
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=4, radius=r, location=(hx, hy, -r * 0.55 + h * 0.5))
        o = bpy.context.object
        o.name = f"heap.{i}"
        o.scale = (1.0 + 0.3 * rng.random(), 1.0 + 0.3 * rng.random(), (h / r) * 1.1)
        bpy.ops.object.transform_apply(scale=True)
        E._displace(o, 6.0, r * 0.25, depth=4)
        o.data.shade_smooth()
        put(o, m["spoil"], col)
    return g


def hardstanding(col, centre=(-6, -4), size=(30, 22)):
    m = mats()
    slab = G.box("hardstanding", (size[0], size[1], 0.12), (centre[0], centre[1], 0.0), col=col)
    put(slab, m["hard"], col)
    return slab


def collar(col, at=(0, 0), hole=(2.4, 2.0), depth=32.0):
    """The shaft mouth: hole through the hardstanding, cast-iron collar frame on a stone kerb,
    timber/iron lining down the shaft, guide rails, and a fence with a gap on the -y side."""
    m = mats()
    x, y = at
    hx, hy = hole
    # the hole: cut the slab, then line it with an inverted box of dark rock going down
    cutter = G.box("shaft_cutter", (hx, hy, 4.0), (x, y, 0.0), col=col)
    cutter.hide_render = True
    cutter.display_type = "WIRE"
    slab = bpy.data.objects.get("hardstanding")
    if slab:
        b = slab.modifiers.new("hole", "BOOLEAN")
        b.operation = "DIFFERENCE"
        b.object = cutter
        b.solver = "EXACT"
    lining = G.box("shaft_lining", (hx + 0.02, hy + 0.02, depth), (x, y, -depth / 2 + 0.06), col=col)
    bpy.context.view_layer.objects.active = lining
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.flip_normals()
    bpy.ops.object.mode_set(mode="OBJECT")
    put(lining, m["shaft"], col)
    # timber sets down the top 6 m of the shaft, at the 1.2 m module
    z = -0.5
    k = 0
    while z > -7.0:
        for sx in (-1, 1):
            put(G.box(f"set_x{k}{sx}", (0.18, hy + 0.02, 0.18), (x + sx * (hx / 2 - 0.09), y, z), col=col), m["timber"], col)
        for sy in (-1, 1):
            put(G.box(f"set_y{k}{sy}", (hx - 0.3, 0.18, 0.18), (x, y + sy * (hy / 2 - 0.09), z), col=col), m["timber"], col)
        z -= 1.2
        k += 1
    # guide rails (iron channels) on the long sides, the cage runs on them
    for sy in (-1, 1):
        put(G.box(f"guide{sy}", (0.12, 0.08, depth - 1.0), (x, y + sy * (hy / 2 - 0.20), -depth / 2 + 0.5), col=col), m["iron"], col)
    # the collar frame: four cast beams on a stone kerb, bolt heads along them
    kz = 0.06
    for sx in (-1, 1):
        put(G.box(f"kerb_x{sx}", (0.5, hy + 1.0, 0.22), (x + sx * (hx / 2 + 0.25), y, kz + 0.11), col=col), m["stone"], col)
        put(G.box(f"collar_x{sx}", (0.28, hy + 0.6, 0.16), (x + sx * (hx / 2 + 0.14), y, kz + 0.30), bevel=0.02, col=col), m["iron"], col)
    for sy in (-1, 1):
        put(G.box(f"kerb_y{sy}", (hx + 1.0, 0.5, 0.22), (x, y + sy * (hy / 2 + 0.25), kz + 0.11), col=col), m["stone"], col)
        put(G.box(f"collar_y{sy}", (hx + 0.6, 0.28, 0.16), (x, y + sy * (hy / 2 + 0.14), kz + 0.30), bevel=0.02, col=col), m["iron"], col)
    for i in range(6):
        for sy in (-1, 1):
            put(G.cyl(f"bolt{i}{sy}", 0.035, 0.03, 0.03, (x - hx / 2 + 0.2 + i * (hx - 0.4) / 5, y + sy * (hy / 2 + 0.14), kz + 0.395), verts=8, col=col), m["iron"], col)
    # the fence: modern galvanised tube, 1.1 m, gap on the -y side
    fz = 1.1
    pts = []
    half = 3.0
    for i in range(6):
        pts.append((x - half + i * 1.2, y + half))
    for i in range(6):
        pts.append((x + half, y + half - i * 1.2))
    for i in range(6):
        pts.append((x + half - i * 1.2, y - half))
    for i in range(6):
        pts.append((x - half, y - half + i * 1.2))
    pts.append(pts[0])
    for i, (px, py) in enumerate(pts[:-1]):
        gap = (abs(py - (y - half)) < 0.01 and abs(px - x) < 1.0)
        if gap and abs(px - x) < 0.7:
            continue
        put(G.cyl(f"fpost{i}", 0.025, 0.025, fz, (px, py, fz / 2 + 0.06), verts=8, col=col), m["galv"], col)
        nx, ny = pts[i + 1]
        if abs(py - (y - half)) < 0.01 and min(px, nx) < x + 0.9 and max(px, nx) > x - 0.9:
            continue          # the gate gap
        for zz in (0.55, 1.05):
            put(G.segment(f"frail{i}_{zz}", (px, py, zz + 0.06), (nx, ny, zz + 0.06), 0.017, 0.017, verts=8, col=col), m["galv"], col)
    return cutter


def headframe(col, at=(0, 0), height=9.0):
    """A cast-iron A-frame over the shaft with the sheave on top and backstays to -x.
    Twice the Assayer's mast in the same casting language. The sheave groove and the
    new cable are the only bright metal on the surface."""
    m = mats()
    x, y = at
    top_z = height
    legs = [((x + sx * 2.6, y + sy * 2.1, 0.06), (x + sx * 0.45, y + sy * 1.45, top_z)) for sx in (-1, 1) for sy in (-1, 1)]
    for i, (a, b) in enumerate(legs):
        put(G.strut(f"hf_leg{i}", Vector(a), Vector(b), 0.34, 0.30, 0.22, 0.20, col=col, bevel=0.01), m["iron"], col)
        put(G.box(f"hf_pad{i}", (0.9, 0.9, 0.14), (a[0], a[1], 0.10), bevel=0.01, col=col), m["iron"], col)
    # horizontal ties at the 1.2 m module (every 2.4 m) across y, and diagonals across x
    for k, z in enumerate((2.4, 4.8, 7.2)):
        t = z / top_z
        for sx in (-1, 1):
            ax = x + sx * (2.6 + (0.45 - 2.6) * t)
            ay = 2.1 + (1.45 - 2.1) * t
            put(G.segment(f"hf_tie{k}{sx}", (ax, y - ay, z), (ax, y + ay, z), 0.07, 0.07, verts=8, col=col), m["iron"], col)
        for sy in (-1, 1):
            ay = y + sy * (2.1 + (1.45 - 2.1) * t)
            ax = 2.6 + (0.45 - 2.6) * t
            put(G.segment(f"hf_tiex{k}{sy}", (x - ax, ay, z), (x + ax, ay, z), 0.07, 0.07, verts=8, col=col), m["iron"], col)
    for sy in (-1, 1):
        put(G.segment(f"hf_diag{sy}", (x - 2.6, y + sy * 2.1, 0.2), (x + 0.45, y + sy * 1.45, top_z - 0.1), 0.06, 0.06, verts=8, col=col), m["iron"], col)
    # head: cross beam and the sheave, axis along y
    put(G.box("hf_head", (1.4, 3.4, 0.36), (x, y, top_z + 0.18), bevel=0.02, col=col), m["iron"], col)
    for sy in (-1, 1):
        put(G.box(f"hf_bearing{sy}", (0.5, 0.24, 0.5), (x, y + sy * 0.55, top_z + 0.62), bevel=0.02, col=col), m["iron"], col)
    put(G.torus("hf_sheave", 1.05, 0.075, (x, y, top_z + 0.86), rot=(math.pi / 2, 0, 0), col=col), m["iron"], col)
    put(G.torus("hf_sheave_groove", 1.08, 0.028, (x, y, top_z + 0.86), rot=(math.pi / 2, 0, 0), col=col), m["bearing"], col)
    put(G.cyl("hf_axle", 0.09, 0.09, 1.5, (x, y, top_z + 0.86), rot=(math.pi / 2, 0, 0), verts=12, col=col), m["bearing"], col)
    for k in range(8):
        a = math.radians(k * 45)
        put(G.segment(f"hf_spoke{k}", (x, y, top_z + 0.86), (x + math.cos(a) * 1.0, y, top_z + 0.86 + math.sin(a) * 1.0), 0.03, 0.03, verts=6, col=col), m["iron"], col)
    # backstays to -x, to the winch side
    for sy in (-1, 1):
        put(G.strut(f"hf_stay{sy}", Vector((x - 0.45, y + sy * 1.45, top_z)), Vector((x - 9.0, y + sy * 2.3, 0.06)), 0.26, 0.22, 0.18, 0.16, col=col, bevel=0.01), m["iron"], col)
        put(G.box(f"hf_staypad{sy}", (0.8, 0.8, 0.14), (x - 9.0, y + sy * 2.3, 0.10), bevel=0.01, col=col), m["iron"], col)
    # a small iron plate with a raised mark on the head: a casting has a foundry mark, no date
    put(G.box("hf_plate", (0.02, 0.5, 0.3), (x + 0.71, y, top_z + 0.2), bevel=0.004, col=col), m["iron"], col)
    return top_z + 0.86


def winch_and_cable(col, sheave_z, shaft_at=(0, 0), kibble_z=None, winch_at=(-7.5, -3.2)):
    """The modern winch on a skid, the new cable up to the sheave and down the shaft, and the
    kibble hanging at kibble_z (None: no kibble)."""
    m = mats()
    x, y = shaft_at
    wx, wy = winch_at
    put(G.box("winch_skid", (1.4, 1.0, 0.12), (wx, wy, 0.12), bevel=0.01, col=col), m["galv"], col)
    put(G.box("winch_body", (0.9, 0.7, 0.55), (wx + 0.15, wy, 0.46), bevel=0.02, col=col), m["pale"], col)
    put(G.cyl("winch_drum", 0.26, 0.26, 0.6, (wx - 0.35, wy, 0.55), rot=(math.pi / 2, 0, 0), verts=20, col=col), m["bearing"], col)
    for sy in (-1, 1):
        put(G.box(f"winch_cheek{sy}", (0.12, 0.05, 0.75), (wx - 0.35, wy + sy * 0.34, 0.50), col=col), m["galv"], col)
    # the rope: drum -> sheave rim (over the top) -> down the shaft
    r = 0.013
    put(G.segment("rope_up", (wx - 0.35, wy, 0.80), (x - 1.05, y, sheave_z + 0.05), r, r, verts=8, col=col), m["bearing"], col)
    pts = [Vector((x - 1.05, y, sheave_z + 0.05)), Vector((x - 0.75, y, sheave_z + 0.85)),
           Vector((x, y, sheave_z + 1.12)), Vector((x + 0.75, y, sheave_z + 0.85)), Vector((x + 1.05, y, sheave_z + 0.05))]
    put(G.tube_along("rope_over", pts, r, verts=8, col=col), m["bearing"], col)
    bottom = kibble_z + 1.35 if kibble_z is not None else -30.0
    put(G.segment("rope_down", (x + 1.05, y, sheave_z + 0.05), (x + 1.05, y, bottom), r, r, verts=8, col=col), m["bearing"], col)
    if kibble_z is not None:
        kx, ky = x + 1.05, y
        kib = []
        kib.append(put(G.cyl("kibble", 0.52, 0.46, 0.85, (kx, ky, kibble_z + 0.425), verts=24, col=col), m["galv"], col))
        kib.append(put(G.cyl("kibble_bore", 0.49, 0.43, 0.84, (kx, ky, kibble_z + 0.44), verts=24, col=col), m["dark"], col))
        # bail: an arch from rim to rim up to the hook
        arc = [Vector((kx + 0.5 * math.cos(a), ky, kibble_z + 0.8 + 0.6 * math.sin(a))) for a in [math.radians(t) for t in range(0, 181, 20)]]
        kib.append(put(G.tube_along("kibble_bail", arc, 0.022, verts=8, col=col), m["galv"], col))
        kib.append(put(G.cyl("kibble_hook", 0.05, 0.05, 0.12, (kx, ky, kibble_z + 1.35), verts=10, col=col), m["bearing"], col))
        return kib
    return []


def winding_house(col, centre=(-16.0, 0.0), size=(9.0, 7.0), wall_h=4.2):
    """Roofless stone walls, the dead engine's drum and flywheel inside, a doorway facing the shaft."""
    m = mats()
    cx, cy = centre
    sx, sy = size
    t = 0.6
    # walls: +x wall has a doorway (two pieces), others solid; gable on -x end
    put(G.box("wh_wall_-x", (t, sy, wall_h + 1.6), (cx - sx / 2, cy, (wall_h + 1.6) / 2), col=col), m["stone"], col)
    for s in (-1, 1):
        put(G.box(f"wh_wall_y{s}", (sx, t, wall_h), (cx, cy + s * sy / 2, wall_h / 2), col=col), m["stone"], col)
    door_w = 2.4
    seg = (sy - door_w) / 2
    for s in (-1, 1):
        put(G.box(f"wh_wall_+x{s}", (t, seg, wall_h), (cx + sx / 2, cy + s * (door_w / 2 + seg / 2), wall_h / 2), col=col), m["stone"], col)
    put(G.box("wh_lintel", (t + 0.1, door_w + 0.4, 0.5), (cx + sx / 2, cy, wall_h - 0.25), col=col), m["iron"], col)
    # the engine: a big drum on pedestals, a flywheel, all dead iron
    put(G.cyl("wh_drum", 1.25, 1.25, 2.4, (cx - 0.5, cy, 1.7), rot=(math.pi / 2, 0, 0), verts=28, col=col), m["iron"], col)
    for s in (-1, 1):
        put(G.box(f"wh_ped{s}", (1.6, 0.6, 1.2), (cx - 0.5, cy + s * 1.5, 0.6), bevel=0.02, col=col), m["iron"], col)
    put(G.torus("wh_flywheel", 1.9, 0.14, (cx + 1.6, cy - 2.2, 2.0), rot=(0, math.pi / 2, 0), col=col), m["iron"], col)
    put(G.cyl("wh_shaft", 0.14, 0.14, 4.8, (cx + 0.9, cy - 0.4, 2.0), rot=(math.pi / 2, 0, 0), verts=12, col=col), m["iron"], col)
    put(G.box("wh_bed", (3.2, 5.0, 0.4), (cx, cy, 0.2), col=col), m["iron"], col)


def lean_to(col, at=(-13.5, -6.2), with_terminal=True, terminal_img=None, terminal_strength=1.5,
            machines=2, crates=True):
    """The yard: a corrugated roof off the winding house's south wall on timber posts; the bench;
    the terminal; the rack with chassis on it; module crates; a machine on charge."""
    m = mats()
    x, y = at
    objs = []
    W, D = 7.5, 3.6        # roof plan, along x and away from the wall (-y)
    # roof: sheet sloping down away from the wall, on three timber posts
    roof = G.box("lt_roof", (W, D + 0.3, 0.04), (x, y - D / 2, 0), col=col)
    roof.rotation_euler = Euler((math.radians(-11), 0, 0))
    roof.location = Vector((x, y - D / 2, 3.05 - 0.35))
    put(roof, m["sheet"], col)
    for k in range(3):
        px = x - W / 2 + 0.3 + k * (W - 0.6) / 2
        put(G.cyl(f"lt_post{k}", 0.07, 0.07, 2.45, (px, y - D + 0.2, 1.25), verts=10, col=col), m["timber"], col)
    put(G.box("lt_beam", (W, 0.12, 0.16), (x, y - D + 0.2, 2.44), col=col), m["timber"], col)
    for k in range(6):
        px = x - W / 2 + 0.6 + k * (W - 1.2) / 5
        r = G.box(f"lt_rafter{k}", (0.08, D + 0.2, 0.14), (px, y - D / 2, 0), col=col)
        r.rotation_euler = Euler((math.radians(-11), 0, 0))
        r.location = Vector((px, y - D / 2, 3.05 - 0.35 - 0.10))
        put(r, m["timber"], col)
    # the bench along the wall
    bx, by = x - 0.8, y - 0.75
    put(G.box("bench_top", (3.4, 0.85, 0.06), (bx, by, 0.86), bevel=0.006, col=col), m["timber"], col)
    for sx in (-1, 1):
        for sy in (-1, 1):
            put(G.box(f"bench_leg{sx}{sy}", (0.08, 0.08, 0.83), (bx + sx * 1.6, by + sy * 0.36, 0.415), col=col), m["timber"], col)
    put(G.box("bench_shelf", (3.3, 0.7, 0.03), (bx, by, 0.25), col=col), m["timber"], col)
    if with_terminal:
        terminal(col, at=(bx + 0.9, by + 0.05, 0.89), yaw=math.radians(-90), img=terminal_img, strength=terminal_strength)
    # crates of modules, pale, stencilled only by their shape
    if crates:
        for k, (cx_, cy_, w, d, h) in enumerate([(bx - 1.2, by + 0.1, 0.42, 0.32, 0.22), (bx - 0.7, by + 0.15, 0.36, 0.28, 0.18),
                                                 (x + 2.6, y - 2.6, 0.6, 0.45, 0.35), (x + 2.6, y - 2.6, 0.6, 0.45, 0.35)]):
            zz = 0.89 + h / 2 if k < 2 else 0.12 + h / 2 + (0.36 if k == 3 else 0)
            put(G.box(f"crate{k}", (w, d, h), (cx_, cy_, zz), bevel=0.01, col=col), m["pale"], col)
            put(G.box(f"crate_lid{k}", (w + 0.02, d + 0.02, 0.02), (cx_, cy_, zz + h / 2 + 0.01), col=col), m["dark"], col)
        # loose modules on the bench: a beacon rack, a magnetometer boom, a sonar bar
        from agent_model.build import _module
        skin_mats = {"dark": m["dark"], "metal": M.bare_metal("loose_metal"), "accent": m["key"], "carbon": m["dark"],
                     "rubber": m["cable"], "light": glow_mat(BONE, 0.0, "loose_light"), "eye": glow_mat(BONE, 0.0, "loose_eye"),
                     "lens": M.lens("loose_lens"), "glass": M.bare_metal("loose_glass", (0.02, 0.03, 0.04), 0.08),
                     "chassis": m["dark"]}
        for k, (kind, px, py, yaw) in enumerate([("beacon_rack", bx + 0.05, by - 0.15, 0.3), ("magnetometer", bx - 0.35, by + 0.25, -1.2),
                                                 ("active_sonar", bx + 0.35, by + 0.25, 0.8)]):
            parts = _module(kind, f"loose{k}", 0.21, col)
            for o, key in parts:
                put(o, skin_mats[key], col)
                o.matrix_world = Matrix.Translation(Vector((px, py, 0.89))) @ Matrix.Rotation(yaw, 4, "Z") @ o.matrix_world
    # the rack: two shelves of galvanised angle, chassis parked on it
    rx, ry = x + 2.2, y - 0.75
    for zz in (0.35, 1.05):
        put(G.box(f"rack_shelf{zz}", (2.4, 0.8, 0.03), (rx, ry, zz), col=col), m["galv"], col)
    for sx in (-1, 1):
        for sy in (-1, 1):
            put(G.box(f"rack_up{sx}{sy}", (0.05, 0.05, 1.5), (rx + sx * 1.18, ry + sy * 0.38, 0.75), col=col), m["galv"], col)
    # charge point on the wall: a box with a cable to the machine below
    put(G.box("charge_box", (0.3, 0.12, 0.4), (x + 0.6, y - 0.07, 1.5), bevel=0.01, col=col), m["dark"], col)
    return objs, (rx, ry)


def yard_lamp(col, watts, at=(-13.2, -8.3, 2.32)):
    """PROPOSAL: the yard's one work light -- a caged bulkhead fitting hung under a rafter of the
    lean-to, the modern teams' kit (a yard with an electric winch and a charge point has a work
    light). Neutral-warm, ~3500 K. Off by default; the night frames render it both ways so the
    'the terminal is the surface's one emissive' proposal and this one can be compared."""
    if watts <= 0:
        return None
    m = mats()
    x, y, z = at
    put(G.cyl("yard_lamp_body", 0.065, 0.075, 0.12, (x, y, z + 0.06), verts=14, col=col), m["dark"], col)
    put(G.cyl("yard_lamp_glass", 0.055, 0.055, 0.03, (x, y, z - 0.005), verts=14, col=col), glow_mat((1.0, 0.86, 0.68), 6.0, "yard_lamp_glow"), col)
    for k in range(6):
        a = math.radians(60 * k)
        put(G.cyl(f"yard_lamp_cage{k}", 0.003, 0.003, 0.11, (x + 0.06 * math.cos(a), y + 0.06 * math.sin(a), z + 0.02), verts=6, col=col), m["dark"], col)
    put(G.cyl("yard_lamp_flex", 0.005, 0.005, 0.30, (x, y, z + 0.27), verts=6, col=col), m["cable"], col)
    return E.add_light("yard_lamp", "POINT", (x, y, z - 0.03), watts, (1.0, 0.86, 0.68), size=0.06)


def terminal(col, at, yaw=0.0, img=None, strength=1.5):
    """The bench terminal: a screen on a stand and a rail of block keys in front. Built facing +x
    in its own frame, then yawed. The screen shows `img`."""
    m = mats()
    objs = []
    objs.append(G.box("term_stand", (0.22, 0.30, 0.02), (0, 0, 0.01), bevel=0.004, col=col))
    put(objs[-1], m["dark"], col)
    objs.append(G.box("term_neck", (0.06, 0.12, 0.18), (-0.06, 0, 0.10), bevel=0.004, col=col))
    put(objs[-1], m["dark"], col)
    body = G.box("term_body", (0.045, 0.62, 0.40), (0, 0, 0.36), bevel=0.006, col=col)
    body.rotation_euler = Euler((0, math.radians(-10), 0))
    put(body, m["dark"], col)
    objs.append(body)
    scr = screen_plane("term_screen", 0.57, 0.35, (0.024, 0, 0.36), (math.pi / 2, 0, math.pi / 2),
                       screen_mat(img, strength, "term_screen_mat"), col)
    scr.rotation_euler = Euler((math.pi / 2, 0, math.pi / 2))
    Mtilt = Matrix.Translation(Vector((0, 0, 0.36))) @ Matrix.Rotation(math.radians(-10), 4, "Y") @ Matrix.Translation(Vector((0.024, 0, 0)))
    scr.matrix_world = Mtilt @ Matrix.Rotation(math.pi / 2, 4, "Z") @ Matrix.Rotation(math.pi / 2, 4, "X")
    objs.append(scr)
    # the block-key rail: one key per block, pale, a scrub wheel at the end
    rail = G.box("term_rail", (0.16, 0.56, 0.025), (0.30, 0, 0.0125), bevel=0.004, col=col)
    put(rail, m["dark"], col)
    objs.append(rail)
    for k in range(9):
        key = G.box(f"term_key{k}", (0.05, 0.048, 0.012), (0.27, -0.24 + k * 0.06, 0.03), bevel=0.003, col=col)
        put(key, m["key"], col)
        objs.append(key)
    wheel = G.cyl("term_wheel", 0.03, 0.03, 0.02, (0.34, 0.24, 0.035), rot=(0, 0, 0), verts=20, col=col)
    put(wheel, m["key"], col)
    objs.append(wheel)
    xform(objs, at, yaw)
    return objs


def pendant(col, img=None, strength=1.5, name="pendant"):
    """The wired pendant, built flat at the origin (screen normal +Z, cable exit -X):
    a 220 x 140 mm slab, a 2:1 screen, a row of five block keys, a scrub wheel, a strap."""
    m = mats()
    objs = []
    body = G.box(f"{name}_body", (0.22, 0.14, 0.032), (0, 0, 0), bevel=0.008, col=col)
    put(body, m["dark"], col)
    objs.append(body)
    bez = G.box(f"{name}_bezel", (0.19, 0.10, 0.004), (0, 0.012, 0.017), bevel=0.002, col=col)
    put(bez, m["pale"], col)
    objs.append(bez)
    scr = screen_plane(f"{name}_screen", 0.17, 0.085, (0, 0.012, 0.0195), (0, 0, 0),
                       screen_mat(img, strength, f"{name}_screen_mat"), col)
    objs.append(scr)
    for k in range(5):
        key = G.box(f"{name}_key{k}", (0.026, 0.016, 0.006), (-0.07 + k * 0.035, -0.052, 0.018), bevel=0.0015, col=col)
        put(key, m["key"], col)
        objs.append(key)
    wheel = G.cyl(f"{name}_wheel", 0.014, 0.014, 0.012, (0.1, -0.052, 0.012), rot=(0, math.pi / 2, 0), verts=16, col=col)
    put(wheel, m["key"], col)
    objs.append(wheel)
    gland = G.cyl(f"{name}_gland", 0.012, 0.010, 0.03, (-0.12, 0.0, 0.0), rot=(0, math.pi / 2, 0), verts=10, col=col)
    put(gland, m["cable"], col)
    objs.append(gland)
    return objs


def cable(col, pts, r=0.006, name="cable"):
    m = mats()
    return put(G.tube_along(name, [Vector(p) for p in pts], r, verts=8, col=col), m["cable"], col)


def mannequin(col, at, yaw=0.0, pose="hold", lean=0.0, name="person"):
    """A person, 1.75 m, no face, hooded. For scale and for the act. Built facing +x."""
    m = mats()
    objs = []
    J, B = m["jacket"], m["cable"]
    for s in (-1, 1):
        objs.append(put(G.box(f"{name}_boot{s}", (0.29, 0.12, 0.11), (0.04, s * 0.11, 0.055), bevel=0.02, col=col), B, col))
        objs.append(put(G.cyl(f"{name}_leg{s}", 0.085, 0.075, 0.82, (0, s * 0.11, 0.52), verts=12, col=col), J, col))
    torso = [put(G.box(f"{name}_pelvis", (0.26, 0.36, 0.22), (0, 0, 1.00), bevel=0.05, col=col), J, col)]
    torso.append(put(G.box(f"{name}_torso", (0.28, 0.44, 0.56), (0.0, 0, 1.36), bevel=0.07, col=col), J, col))
    torso.append(put(G.sphere(f"{name}_head", 0.115, (0.03, 0, 1.68), col=col, seg=20), J, col))
    torso.append(put(G.sphere(f"{name}_hood", 0.135, (-0.03, 0, 1.70), col=col, seg=20), J, col))
    sh = 1.55
    if pose == "hold":
        hands = [(0.36, 0.10, 1.20), (0.36, -0.10, 1.20)]
    elif pose == "reach":
        hands = [(0.55, 0.15, 0.55), (0.30, -0.18, 1.10)]
    else:  # arms down
        hands = [(0.05, 0.28, 0.85), (0.05, -0.28, 0.85)]
    for s, h in zip((1, -1), hands):
        elbow = (0.12, s * 0.27, 1.25) if pose != "reach" or s < 0 else (0.30, s * 0.25, 0.95)
        torso.append(put(G.segment(f"{name}_uarm{s}", (0, s * 0.24, sh), elbow, 0.055, 0.05, verts=10, col=col), J, col))
        torso.append(put(G.segment(f"{name}_farm{s}", elbow, h, 0.05, 0.04, verts=10, col=col), J, col))
        torso.append(put(G.sphere(f"{name}_hand{s}", 0.045, h, col=col, seg=12), B, col))
    # lean: pitch the upper body forward about the hips
    if lean:
        Ml = Matrix.Translation(Vector((0, 0, 0.9))) @ Matrix.Rotation(lean, 4, "Y") @ Matrix.Translation(Vector((0, 0, -0.9)))
        for o in torso:
            o.matrix_world = Ml @ o.matrix_world
    objs += torso
    Mx = xform(objs, at, yaw)
    Ml = Matrix.Identity(4)
    if lean:
        Ml = Matrix.Translation(Vector((0, 0, 0.9))) @ Matrix.Rotation(lean, 4, "Y") @ Matrix.Translation(Vector((0, 0, -0.9)))
    both = Mx @ Ml @ Vector(((hands[0][0] + hands[1][0]) / 2, 0, hands[0][2]))
    each = [Mx @ Ml @ Vector(h) for h in hands]
    return objs, (both if pose == "hold" else each[1])


def listening_post(col, at=(4.6, -4.2), shaft_at=(0, 0), img=None, strength=1.5):
    """The surface end of the acoustic link: a cable drum on an A-frame stand, the hydrophone
    cable over the collar and down the shaft, and a small screen on a tripod showing belief."""
    m = mats()
    x, y = at
    sx, sy = shaft_at
    put(G.cyl("post_drum", 0.34, 0.34, 0.42, (x, y, 0.55), rot=(0, math.pi / 2, 0), verts=24, col=col), m["dark"], col)
    put(G.cyl("post_drum_core", 0.36, 0.36, 0.06, (x - 0.22, y, 0.55), rot=(0, math.pi / 2, 0), verts=24, col=col), m["pale"], col)
    put(G.cyl("post_drum_core2", 0.36, 0.36, 0.06, (x + 0.22, y, 0.55), rot=(0, math.pi / 2, 0), verts=24, col=col), m["pale"], col)
    for s in (-1, 1):
        put(G.segment(f"post_a{s}a", (x + s * 0.30, y - 0.35, 0.06), (x + s * 0.30, y, 0.60), 0.02, 0.02, verts=8, col=col), m["galv"], col)
        put(G.segment(f"post_a{s}b", (x + s * 0.30, y + 0.35, 0.06), (x + s * 0.30, y, 0.60), 0.02, 0.02, verts=8, col=col), m["galv"], col)
    # the cable: off the drum, along the ground, over the collar beam, down the shaft
    pts = [(x, y + 0.34, 0.55), (x - 0.6, y + 0.4, 0.12), (sx + 0.4, sy - 3.6, 0.12), (sx + 0.9, sy - 2.2, 0.12),
           (sx + 1.1, sy - 1.5, 0.12), (sx + 1.12, sy - 1.3, 0.42), (sx + 1.12, sy - 1.0, 0.44), (sx + 1.1, sy - 0.85, 0.1),
           (sx + 1.1, sy - 0.85, -8.0)]
    cable(col, pts, r=0.009, name="hydrophone_cable")
    # the post itself: a pale box on a tripod, its screen facing -y (the player stands south of it)
    tx, ty = x + 1.3, y + 0.2
    for k in range(3):
        a = math.radians(90 + 120 * k)
        put(G.segment(f"post_tri{k}", (tx + math.cos(a) * 0.45, ty + math.sin(a) * 0.45, 0.06), (tx, ty, 1.05), 0.016, 0.014, verts=8, col=col), m["galv"], col)
    objs = [put(G.box("post_box", (0.34, 0.06, 0.24), (0, 0, 1.18), bevel=0.006, col=col), m["pale"], col)]
    scr = screen_plane("post_screen", 0.28, 0.16, (0, -0.031, 1.18), (0, 0, 0), screen_mat(img, strength, "post_screen_mat"), col)
    scr.matrix_world = Matrix.Translation(Vector((0, -0.031, 1.18))) @ Matrix.Rotation(math.pi / 2, 4, "X")
    objs.append(scr)
    objs.append(put(G.box("post_hood", (0.38, 0.12, 0.03), (0, -0.05, 1.32), bevel=0.004, col=col), m["dark"], col))
    xform(objs, (tx, ty, 0), 0.0)
    return (tx, ty)


# ---------------------------------------------------------------------------------------
# the course: Phase 2's corridor, made physical
# ---------------------------------------------------------------------------------------
def load_corridor(seed):
    from phase2.truth.corridor import Corridor
    return Corridor(seed)


def course_layout(C, root=(14.0, 4.0), cell=CELL):
    """Node positions in metres, the tree rotated so it runs away from the works toward +x."""
    raw = {i: (x * cell, y * cell) for i, (x, y) in C.layout().items()}
    cx = sum(p[0] for p in raw.values()) / len(raw)
    cy = sum(p[1] for p in raw.values()) / len(raw)
    ang = math.atan2(cy - raw[0][1], cx - raw[0][0])
    rot = -ang
    pos = {}
    for i, (x, y) in raw.items():
        dx, dy = x - raw[0][0], y - raw[0][1]
        pos[i] = (root[0] + dx * math.cos(rot) - dy * math.sin(rot), root[1] + dx * math.sin(rot) + dy * math.cos(rot))
    return pos


def course(col, C, pos, wall_h=1.2, width=1.8, post_every=1.2, roofed=()):
    """Extrude the corridor as hoarding walls on timber posts. Junction squares open, dead ends capped,
    the root post at the shaft node, the deposit leaf gets a crate and a heap of broken stock."""
    m = mats()
    clear = width / 2 + 0.45
    for pid, p in C.passages.items():
        a, b = Vector((*pos[p.near], 0)), Vector((*pos[p.far], 0))
        d = (b - a)
        L = d.length
        d.normalize()
        n = Vector((-d.y, d.x, 0))
        far_node = C.nodes[p.far]
        trim_b = clear if far_node.onward else 0.02
        yaw = math.atan2(d.y, d.x)
        seg_len = L - clear - trim_b
        if seg_len <= 0.5:
            continue
        mid = a + d * (clear + seg_len / 2)
        for s in (-1, 1):
            c = mid + n * s * width / 2
            w = G.box(f"wall{pid}{s}", (seg_len, 0.035, wall_h), (0, 0, 0), col=col)
            w.rotation_euler = Euler((0, 0, yaw))
            w.location = Vector((c.x, c.y, wall_h / 2 + 0.02))
            put(w, m["sheet"], col)
            k = 0
            t = clear + 0.1
            while t < L - trim_b:
                q = a + d * t + n * s * (width / 2 + 0.05)
                put(G.cyl(f"post{pid}{s}_{k}", 0.05, 0.045, wall_h + 0.2, (q.x, q.y, (wall_h + 0.2) / 2), verts=8, col=col), m["timber"], col)
                t += post_every
                k += 1
        if not far_node.onward:
            cap = G.box(f"cap{pid}", (0.035, width + 0.1, wall_h), (0, 0, 0), col=col)
            cap.rotation_euler = Euler((0, 0, yaw))
            cap.location = Vector((b.x, b.y, wall_h / 2 + 0.02))
            put(cap, m["sheet"], col)
        if pid in roofed:
            rf = G.box(f"roof{pid}", (seg_len + 0.4, width + 0.5, 0.04), (0, 0, 0), col=col)
            rf.rotation_euler = Euler((0, 0, yaw))
            rf.location = Vector((mid.x, mid.y, wall_h + 0.42))
            put(rf, m["sheet"], col)
            for s in (-1, 1):
                up = G.box(f"roofwall{pid}{s}", (seg_len, 0.035, 0.42), (0, 0, 0), col=col)
                up.rotation_euler = Euler((0, 0, yaw))
                c = mid + n * s * width / 2
                up.location = Vector((c.x, c.y, wall_h + 0.21))
                put(up, m["sheet"], col)
    # the root: a pale post with a warm pilot -- the shaft beacon of the corridor, made physical
    rx, ry = pos[C.shaft]
    put(G.cyl("root_post", 0.06, 0.05, 1.5, (rx, ry, 0.75), verts=10, col=col), m["pale"], col)
    put(G.cyl("root_pilot", 0.035, 0.035, 0.05, (rx, ry, 1.53), verts=12, col=col), m["pilot"], col)
    # the deposit leaf: a crate of broken stock at the dead end
    dx, dy = pos[C.deposit]
    par = C.passages[C.nodes[C.deposit].parent]
    a = Vector((*pos[par.near], 0))
    d = (Vector((dx, dy, 0)) - a).normalized()
    cpos = Vector((dx, dy, 0)) - d * 0.55
    put(G.box("cargo_crate", (0.5, 0.42, 0.3), (cpos.x, cpos.y, 0.17), bevel=0.01, col=col), m["pale"], col)
    rng = random.Random(9)
    for i in range(14):
        r = rng.uniform(0.05, 0.14)
        q = cpos - d * rng.uniform(0.3, 1.2) + Vector((-d.y, d.x, 0)) * rng.uniform(-0.55, 0.55)
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=r, location=(q.x, q.y, r * 0.5))
        o = bpy.context.object
        o.name = f"stock{i}"
        o.scale = (rng.uniform(0.7, 1.5), rng.uniform(0.7, 1.5), rng.uniform(0.4, 0.8))
        put(o, m["spoil"], col)
    return pos


def first_junction(C, pos):
    """The first real junction (parent and onward passages), its incoming direction and its
    onward mouths' bearings -- where the over-the-shoulder shot is staged."""
    first = C.passages[0]
    j = C.nodes[first.far]
    a, b = Vector((*pos[first.near], 0)), Vector((*pos[j.id], 0))
    inc = (b - a).normalized()
    mouths = []
    for pid in j.onward:
        q = Vector((*pos[C.passages[pid].far], 0))
        mouths.append((q - b).normalized())
    return j, b, inc, mouths


# ---------------------------------------------------------------------------------------
# agents
# ---------------------------------------------------------------------------------------
ROCK_DUST = (0.30, 0.265, 0.215)
MUD = (0.085, 0.062, 0.040)


def worn_metal(base, bare, wear=0.35, grime=0.4, mud=0.0, dust=0.0, scuff=0.0, foot_z=0.0, name="worn"):
    """av_probe.worn_metal, trimmed: the three gravity masks over painted_metal's isotropic term."""
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


def dress(built, team="player", wear=0.35, mud=0.5, dust=0.35, scuff=0.4, foot_z=0.0, emissive=3.0, tag="a"):
    """The three fixes plus the directed wear, applied to one built agent only."""
    shell, chas = (PALE_SHELL, GRAPHITE) if team == "player" else (RIVAL_SHELL, RIVAL_CHASSIS)
    colour = BONE if team == "player" else EMBER
    bare = (0.45, 0.45, 0.47)
    m_shell = worn_metal(shell, bare, wear, 0.4, mud, dust, scuff, foot_z, f"tp_shell_{tag}")
    m_chas = worn_metal(chas, bare, wear, 0.5, mud, dust, scuff, foot_z, f"tp_chassis_{tag}")
    m_leg = worn_metal((0.040, 0.040, 0.045), (0.075, 0.072, 0.070), wear * 0.35, 0.6, mud, dust * 0.4, scuff * 0.5, foot_z, f"tp_leg_{tag}")
    m_light = glow_mat(colour, emissive, f"tp_light_{tag}")
    m_eye = glow_mat(colour, emissive, f"tp_eye_{tag}")
    m_estop = M.bare_metal(f"tp_estop_{tag}", (0.6, 0.04, 0.03), 0.45)      # painted, never emissive
    leg_parts = ("tibia", "tibia_knuckle", "foot", "belt_cover")
    for o in built.parts:
        if o.type != "MESH" or not o.data.materials or o.data.materials[0] is None:
            continue
        nm = o.data.materials[0].name
        base = o.name.split(".")[0]
        if nm.startswith("shell_paint"):
            o.data.materials[0] = m_shell
        elif nm.startswith("chassis_paint"):
            o.data.materials[0] = m_chas
        elif base in leg_parts:
            o.data.materials[0] = m_leg
        elif nm.startswith("light_strip"):
            o.data.materials[0] = m_light
        elif nm.startswith("eye"):
            o.data.materials[0] = m_eye
        elif nm.startswith("estop_red"):
            o.data.materials[0] = m_estop
    if built.lamp:
        built.lamp.data.energy = 0.0
        built.lamp.data.color = LAMP_WHITE


def fix_lamp(built, energy=600.0, aim_down_deg=10.0):
    if not built.lamp:
        return
    built.lamp.rotation_euler = Euler((0, -math.pi / 2 + math.radians(aim_down_deg), 0))
    built.lamp.data.energy = energy
    built.lamp.data.color = LAMP_WHITE


def place_agent(chassis="surveyor", at=(0, 0, 0), yaw=0.0, look=None, modules=None, team="player",
                wear=0.35, mud=0.5, dust=0.35, scuff=0.4, name="AGENT", lamp=0.0, tag="a", crouch=0.0):
    cfg = P.default_config(chassis)
    if modules is not None:
        cfg.modules = modules
    built = build_agent(cfg, name=name, at=at)
    # yaw the whole machine: the rig and its world-space foot targets
    R = Matrix.Rotation(yaw, 4, "Z")
    o = Vector(at)
    built.arm.rotation_euler = Euler((0, 0, yaw))
    for f in built.feet:
        f.location = o + R @ (Vector(f.location) - o)
    built.look.location = o + R @ (Vector(built.look.location) - o)
    bpy.context.view_layer.update()
    mv = Mover(built)
    mv.stand(0.2)
    if crouch:
        mv.crouch(crouch, over=0.3)
    if look is not None:
        mv.look_at(Vector(look), over=0.4)
    mv.stand(0.1)
    mv.finish()
    bpy.context.scene.frame_set(mv.frame)
    dress(built, team=team, wear=wear, mud=mud, dust=dust, scuff=scuff, foot_z=at[2], tag=tag)
    if lamp > 0:
        fix_lamp(built, energy=lamp)
    return built


def agent_port(built, at, yaw):
    """World position of the charge port (build.py:236): the rear face, right of centre, low."""
    ch = P.CHASSIS[built.arm["chassis"]]
    L, W, H = ch.hull
    zc = ch.ride_height + H / 2
    local = Vector((-L / 2 - 0.006, -W * 0.15, zc - H * 0.15))
    return Vector(at) + Matrix.Rotation(yaw, 3, "Z") @ local


# ---------------------------------------------------------------------------------------
# skies and cameras
# ---------------------------------------------------------------------------------------
def sky(kind="overcast"):
    w = bpy.context.scene.world or bpy.data.worlds.new("World")
    bpy.context.scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    nt.links.new(bg.outputs[0], out.inputs["Surface"])
    fog = 0.0
    if kind == "overcast":
        bg.inputs["Color"].default_value = (*SKY, 1)
        bg.inputs["Strength"].default_value = 0.32
        E.add_light("cloud_break", "AREA", (18, -26, 34), 12000.0, (0.95, 0.95, 1.0), size=14.0, aim=(10, 0, 0))
    elif kind == "sun":
        bg.inputs["Color"].default_value = (*SKY, 1)
        bg.inputs["Strength"].default_value = 0.35
        d = bpy.data.lights.new("SUN", "SUN")
        d.energy = 1.6
        d.angle = math.radians(1.5)
        d.color = (1.0, 0.94, 0.86)
        o = bpy.data.objects.new("SUN", d)
        bpy.context.scene.collection.objects.link(o)
        o.rotation_euler = Euler((math.radians(58), 0, math.radians(-35)))
    elif kind == "drizzle":
        bg.inputs["Color"].default_value = (0.50, 0.60, 0.78, 1)
        bg.inputs["Strength"].default_value = 0.30
        E.add_light("cloud_break", "AREA", (18, -26, 34), 9000.0, (0.85, 0.88, 1.0), size=16.0, aim=(10, 0, 0))
        fog = 0.006
    elif kind == "dusk":
        bg.inputs["Color"].default_value = (0.36, 0.44, 0.66, 1)
        bg.inputs["Strength"].default_value = 0.07       # first pass 0.035: no roof-line at all
        fog = 0.003
    elif kind == "night":
        bg.inputs["Color"].default_value = (0.30, 0.38, 0.60, 1)
        bg.inputs["Strength"].default_value = 0.004      # first pass used 0.0015: a black frame
    elif kind == "clear":
        bg.inputs["Color"].default_value = (0.42, 0.42, 0.42, 1)
        bg.inputs["Strength"].default_value = 1.0
    elif kind == "cave":
        bg.inputs["Color"].default_value = (0, 0, 0, 1)
        bg.inputs["Strength"].default_value = 0.0
        fog = 0.02
    if fog > 0:
        vol = nt.nodes.new("ShaderNodeVolumeScatter")
        vol.inputs["Density"].default_value = fog
        vol.inputs["Anisotropy"].default_value = 0.55
        vol.inputs["Color"].default_value = (0.85, 0.86, 0.9, 1)
        nt.links.new(vol.outputs[0], out.inputs["Volume"])
    return w


def clear_stage(size=6.0):
    """The CLEAR rig: a grey ground, a 45-degree key, the world at 1.0. For product shots."""
    m = kit_mat((0.36, 0.36, 0.36), 0.7, "studio_floor", coat=0.0)
    put(G.plane("studio_floor", size, (0, 0, 0)), m)
    E.add_light("key", "AREA", (2.2, -2.2, 3.1), 1000.0, (1.0, 0.98, 0.95), size=3.0, aim=(0, 0, 0.3))
    E.add_light("fill", "AREA", (-2.5, 1.5, 1.8), 220.0, (0.9, 0.93, 1.0), size=3.0, aim=(0, 0, 0.3))


def cam(loc, aim, focal=40.0, fstop=None, sensor=36.0):
    cd = bpy.data.cameras.new("CAM")
    cd.lens = focal
    cd.sensor_width = sensor
    cd.clip_end = 2000.0
    if fstop:
        cd.dof.use_dof = True
        cd.dof.aperture_fstop = fstop
        cd.dof.focus_distance = (Vector(loc) - Vector(aim)).length
    c = bpy.data.objects.new("CAM", cd)
    bpy.context.scene.collection.objects.link(c)
    c.location = Vector(loc)
    t = bpy.data.objects.new("CAM_aim", None)
    bpy.context.scene.collection.objects.link(t)
    t.location = Vector(aim)
    k = c.constraints.new("TRACK_TO")
    k.track_axis = "TRACK_NEGATIVE_Z"
    k.up_axis = "UP_Y"
    k.target = t
    bpy.context.scene.camera = c
    META["camera"] = {"loc": list(loc), "aim": list(aim), "focal": focal}
    return c


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    MATS.clear()


# ---------------------------------------------------------------------------------------
# the surface, assembled
# ---------------------------------------------------------------------------------------
def build_surface(kind="overcast", kibble_z=None, terminal_img=None, terminal_strength=1.5,
                  post_img=None, post_strength=1.5, with_course=True, roofed=(), course_seed=None):
    reset()
    sky(A.sky or kind)
    wet = 0.75 if kind in ("drizzle", "dusk", "night") else 0.55
    MATS.clear()
    MATS.update({"spoil": spoil_mat(wet), "hard": hardstanding_mat(wet)})
    mats()
    col = col_new("SURFACE")
    terrain(col)
    hardstanding(col)
    collar(col)
    sheave_z = headframe(col)
    winch_and_cable(col, sheave_z, kibble_z=kibble_z)
    winding_house(col)
    _, rack_xy = lean_to(col, terminal_img=terminal_img, terminal_strength=terminal_strength)
    post_xy = listening_post(col, img=post_img, strength=post_strength)
    yard_lamp(col, A.yard_lamp)
    out = {"post": post_xy, "sheave_z": sheave_z, "col": col, "rack": rack_xy}
    if with_course:
        C = load_corridor(course_seed or A.seed)
        pos = course_layout(C)
        course(col_new("COURSE"), C, pos, roofed=roofed)
        out.update({"C": C, "pos": pos})
        j, b, inc, mouths = first_junction(C, pos)
        out.update({"junction": j, "jpos": b, "jinc": inc, "jmouths": mouths})
        META["junction"] = {"id": j.id, "pos": [b.x, b.y], "incoming": [inc.x, inc.y],
                            "mouths": [[v.x, v.y] for v in mouths]}
    return out


def parked_machines(col, rack_xy):
    """Chassis on the rack in the lean-to: a Scout on the top shelf, a Swimmer on the bottom."""
    rx, ry = rack_xy
    a = place_agent("scout", at=(rx - 0.5, ry, 1.065), yaw=math.radians(90), name="RACK_SCOUT", tag="rs", wear=0.2, mud=0.1, dust=0.2)
    b = place_agent("swimmer", at=(rx + 0.5, ry, 0.365), yaw=math.radians(90), name="RACK_SWIM", tag="rw", wear=0.5, mud=0.7, dust=0.3)
    return a, b


def finish(exposure=None):
    E.settings(samples=A.samples, res=RES, look="AgX - Medium High Contrast",
               exposure=A.exposure if exposure is None else exposure)
    sc = bpy.context.scene
    sc.cycles.volume_max_steps = 48
    sc.render.filepath = A.out
    bpy.ops.render.render(write_still=True)
    if A.meta:
        with open(A.meta, "w") as f:
            json.dump(META, f, indent=1)
    print(f"WROTE {A.out}")


# ---------------------------------------------------------------------------------------
# shots
# ---------------------------------------------------------------------------------------
S = A.shot


def stage_junction(sv, kind, pendant_img, pendant_strength=1.6, lean=0.22, machine_look="mouth"):
    """The act: machine stopped at the first junction, player over the wall with the pendant,
    the cable between them. Returns (machine, player hand position, machine position, yaw)."""
    b, inc, mouths = sv["jpos"], sv["jinc"], sv["jmouths"]
    myaw = math.atan2(inc.y, inc.x)
    mpos = b - inc * 0.4
    look = (b + mouths[0] * 2.5 + Vector((0, 0, 0.25))) if machine_look == "mouth" else (mpos + inc * 0.5 + Vector((0, 0, -0.1)))
    mach = place_agent("surveyor", at=(mpos.x, mpos.y, 0.02), yaw=myaw, look=look, name="MACHINE", tag="m")
    # the player stands outside the wall on the side away from the first mouth
    side = Vector((-inc.y, inc.x, 0))
    if side.dot(mouths[0]) > 0:
        side = -side
    ppos = b - inc * 2.1 + side * (0.9 + 0.55)
    pyaw = math.atan2(-side.y, -side.x) + math.radians(25)
    col = col_new("PLAYER")
    _, hand = mannequin(col, (ppos.x, ppos.y, 0.02), pyaw, pose="hold", lean=lean)
    pend = pendant(col, img=pendant_img, strength=pendant_strength)
    tilt = Matrix.Rotation(math.radians(-38), 4, "Y")   # screen faces up and back toward the face
    Mp = (Matrix.Translation(hand + Vector((0, 0, 0.03))) @ Matrix.Rotation(pyaw, 4, "Z") @ tilt
          @ Matrix.Rotation(-math.pi / 2, 4, "Z"))          # landscape in the hands: u runs left-right
    for o in pend:
        o.matrix_world = Mp @ o.matrix_world
    exit_pt = Mp @ Vector((-0.13, 0, 0))
    port = agent_port(mach, (mpos.x, mpos.y, 0.02), myaw)
    mid1 = Vector(exit_pt) + Vector((0, 0, -0.35)) - inc * 0.2
    over = b - inc * 2.1 + side * 0.9 + Vector((0, 0, 1.28))
    mid2 = over - side * 0.6 + Vector((0, 0, -0.5))
    cable(col, [exit_pt, mid1, over + side * 0.15, over, mid2, port + Vector((-0.1, 0, 0.05)), port], r=0.006, name="pendant_cable")
    return mach, hand, mpos, myaw, ppos, pyaw


if S == "g1_course_oblique":
    sv = build_surface("overcast", kibble_z=0.6, terminal_img=A.terminal_img, post_img=A.post_img)
    stage_junction(sv, "overcast", A.pendant_img)
    xs = [p[0] for p in sv["pos"].values()]
    ys = [p[1] for p in sv["pos"].values()]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    ext = max(max(xs) - min(xs), max(ys) - min(ys))
    cam((cx - 0.55 * ext - 12, cy - 0.95 * ext, 0.62 * ext + 14), (cx, cy, 0.0), focal=32)
    finish()

elif S == "g1_junction_ots":
    sv = build_surface("overcast", terminal_img=A.terminal_img, post_img=A.post_img)
    mach, hand, mpos, myaw, ppos, pyaw = stage_junction(sv, "overcast", A.pendant_img)
    back = Vector((math.cos(pyaw), math.sin(pyaw), 0))
    side = Vector((-back.y, back.x, 0))
    c = Vector((ppos.x, ppos.y, 0)) - back * 1.2 - side * 0.55 + Vector((0, 0, 2.1))
    aim = (Vector((mpos.x, mpos.y, 0.3)) * 0.45 + Vector(hand) * 0.55)
    cam(c, aim, focal=30, fstop=5.6)
    finish()

elif S == "g1_junction_ots_pendant":
    # the act over the OTHER shoulder, steeper, so the pendant screen in the hands is in frame with
    # the machine below the wall: the belief picture and the thing it is a belief about, in one frame.
    sv = build_surface("overcast", terminal_img=A.terminal_img, post_img=A.post_img)
    mach, hand, mpos, myaw, ppos, pyaw = stage_junction(sv, "overcast", A.pendant_img, pendant_strength=2.2)
    back = Vector((math.cos(pyaw), math.sin(pyaw), 0))
    side = Vector((-back.y, back.x, 0))
    c = Vector((ppos.x, ppos.y, 0)) - back * 0.85 + side * 0.80 + Vector((0, 0, 2.15))
    aim = (Vector((mpos.x, mpos.y, 0.3)) * 0.4 + Vector(hand) * 0.6)
    cam(c, aim, focal=28, fstop=5.6)
    finish()

elif S == "g1_junction_machine_eye":
    sv = build_surface("overcast", terminal_img=A.terminal_img, post_img=A.post_img)
    mach, hand, mpos, myaw, ppos, pyaw = stage_junction(sv, "overcast", A.pendant_img)
    inc = sv["jinc"]
    b = sv["jpos"]
    c = Vector((mpos.x, mpos.y, 0.45)) - inc * 1.4
    cam(c, Vector((b.x, b.y, 0.45)) + sv["jmouths"][0] * 1.0, focal=24)   # first pass: tuple + Vector, crashed
    finish()

elif S == "g1_scale_lineup":
    reset()
    sky("clear")
    clear_stage(size=14.0)
    m = mats()
    col = col_new("LINEUP")
    # the wall: a 3.6 m run at 1.2 m with posts at the module
    w = G.box("wall", (3.6, 0.035, 1.2), (0.6, 1.0, 0.62), col=col)
    put(w, m["sheet"], col)
    for k in range(4):
        put(G.cyl(f"post{k}", 0.05, 0.045, 1.4, (-1.2 + k * 1.2 + 0.6, 1.05, 0.7), verts=8, col=col), m["timber"], col)
    mannequin(col, (-1.4, 0.0, 0.0), math.radians(-90), pose="hold")
    mach = place_agent("surveyor", at=(0.4, 0.0, 0.0), yaw=math.radians(-90), name="MACHINE", tag="m", look=(0.4, -3, 0.3))
    # the rail gauge on the floor: two rails 0.6 m apart, cast, with a 1.2 m ruler beside
    for s in (-1, 1):
        put(G.box(f"rail{s}", (0.05, 3.2, 0.06), (1.9 + s * 0.3, 0.0, 0.03), col=col), m["bearing"], col)
    for k in range(5):
        put(G.box(f"sleeper{k}", (1.0, 0.16, 0.05), (1.9, -1.2 + k * 0.6, 0.025), col=col), m["timber"], col)
    put(G.box("ruler", (1.2, 0.03, 0.01), (0.2, -0.9, 0.005), col=col), m["key"], col)
    cam((0.6, -6.2, 1.55), (0.4, 0.0, 0.62), focal=50)
    finish()

elif S == "g1_junction_drizzle":
    sv = build_surface("drizzle", terminal_img=A.terminal_img, post_img=A.post_img, terminal_strength=2.5, post_strength=2.5)
    mach, hand, mpos, myaw, ppos, pyaw = stage_junction(sv, "drizzle", A.pendant_img, pendant_strength=3.0)
    back = Vector((math.cos(pyaw), math.sin(pyaw), 0))
    side = Vector((-back.y, back.x, 0))
    c = Vector((ppos.x, ppos.y, 0)) - back * 2.4 - side * 1.9 + Vector((0, 0, 1.45))
    cam(c, (mpos.x, mpos.y, 0.5), focal=40, fstop=4.0)
    finish()

elif S == "g1_deadend":
    sv = build_surface("overcast", terminal_img=A.terminal_img, post_img=A.post_img)
    C, pos = sv["C"], sv["pos"]
    # a leaf near the root: shortest path leaf
    leaves = sorted(C.leaves(), key=lambda i: C.nodes[i].depth)
    leaf = leaves[0]
    par = C.passages[C.nodes[leaf].parent]
    a, b = Vector((*pos[par.near], 0)), Vector((*pos[leaf], 0))
    d = (b - a).normalized()
    mpos = b - d * 1.1
    myaw = math.atan2(-d.y, -d.x) + math.radians(35)   # already turning back
    mach = place_agent("surveyor", at=(mpos.x, mpos.y, 0.02), yaw=myaw, look=(mpos - d * 3 + Vector((0, 0, 0.3))), name="MACHINE", tag="m")
    n = Vector((-d.y, d.x, 0))
    ppos = b - d * 3.2 + n * 1.5
    col = col_new("PLAYER")
    mannequin(col, (ppos.x, ppos.y, 0.02), math.atan2(d.y, d.x), pose="down")
    # first pass: from outside the wall the machine was 30 px behind hoarding. From above the
    # wall line, down the passage: the machine turning, the cap, the person over the wall to the side.
    c = b - d * 4.6 + n * 0.35 + Vector((0, 0, 1.85))
    cam(c, (mpos.x, mpos.y, 0.28), focal=38, fstop=5.6)
    finish()

elif S == "g1_roofed":
    # the proposal for design problem 3: a roofed, dark stretch of the course, lamp on
    sv = build_surface("overcast", terminal_img=A.terminal_img, post_img=A.post_img, roofed=(0,))
    C, pos = sv["C"], sv["pos"]
    p0 = C.passages[0]
    a, b = Vector((*pos[p0.near], 0)), Vector((*pos[p0.far], 0))
    d = (b - a).normalized()
    L = (b - a).length
    mpos = a + d * (L * 0.45)
    myaw = math.atan2(d.y, d.x)
    mach = place_agent("surveyor", at=(mpos.x, mpos.y, 0.02), yaw=myaw, look=(mpos + d * 3 + Vector((0, 0, 0.1))), name="MACHINE", tag="m", lamp=600.0)
    c = mpos - d * 3.2 + Vector((0.0, 0.0, 0.55))
    cam(c, mpos + d * 3.0 + Vector((0, 0, 0.1)), focal=32)
    finish()

elif S == "g2_pendant_clear":
    reset()
    sky("clear")
    clear_stage(size=3.0)
    m = mats()
    col = col_new("PRODUCT")
    pend = pendant(col, img=A.pendant_img, strength=1.2)
    Mp = Matrix.Translation(Vector((0, 0, 0.075))) @ Matrix.Rotation(math.radians(34), 4, "Z") @ Matrix.Rotation(math.radians(35), 4, "X")
    for o in pend:
        o.matrix_world = Mp @ o.matrix_world
    # a wedge under it, and the cable coiled away
    put(G.box("wedge", (0.20, 0.10, 0.05), (0.0, 0.03, 0.025), rot=(0, 0, math.radians(34)), bevel=0.005, col=col), m["dark"], col)
    exit_pt = Mp @ Vector((-0.13, 0, 0))
    cable(col, [exit_pt, exit_pt + Vector((-0.05, 0, -0.03)), (-0.2, 0.05, 0.006), (-0.3, 0.2, 0.006), (-0.15, 0.35, 0.006), (0.1, 0.3, 0.006)], r=0.006)
    # scale reference: a beacon tube, 230 x 60 mm (ART-DIRECTION 6.3), the thing the machine drops
    put(G.cyl("beacon", 0.03, 0.03, 0.23, (0.26, -0.08, 0.115), verts=16, col=col), m["iron"], col)
    put(G.cyl("beacon_base", 0.045, 0.03, 0.03, (0.26, -0.08, 0.015), verts=16, col=col), m["iron"], col)
    put(G.cyl("beacon_pilot", 0.012, 0.012, 0.01, (0.26, -0.08, 0.235), verts=12, col=col), m["pilot"], col)
    put(G.cyl("beacon_band", 0.031, 0.031, 0.02, (0.26, -0.08, 0.17), verts=16, col=col), m["key"], col)
    cam((0.42, -0.62, 0.42), (0.02, 0.0, 0.08), focal=60, fstop=8.0)
    finish()

elif S == "g2_terminal_clear":
    reset()
    sky("clear")
    clear_stage(size=4.0)
    m = mats()
    col = col_new("PRODUCT")
    put(G.box("bench_top", (2.0, 0.85, 0.06), (0, 0, -0.03), bevel=0.006, col=col), m["timber"], col)
    terminal(col, at=(-0.25, 0, 0.0), yaw=math.radians(0), img=A.terminal_img, strength=1.2)
    pend = pendant(col, img=A.pendant_img, strength=1.0)
    Mp = Matrix.Translation(Vector((0.25, -0.3, 0.017))) @ Matrix.Rotation(math.radians(25), 4, "Z")
    for o in pend:
        o.matrix_world = Mp @ o.matrix_world
    cable(col, [Mp @ Vector((-0.13, 0, 0)), (0.05, -0.2, 0.006), (-0.2, -0.35, 0.006), (-0.5, -0.3, 0.006), (-0.6, 0.0, 0.006), (-0.45, 0.0, 0.05)], r=0.006)
    cam((1.45, -1.05, 0.72), (-0.05, -0.05, 0.22), focal=45, fstop=5.6)
    finish()

elif S == "g2_pendant_collar":
    # with_course=False: the first pass had the course's first arm between the camera and the
    # collar, and the frame was all hoarding
    sv = build_surface("overcast", kibble_z=0.6, terminal_img=A.terminal_img, post_img=A.post_img, with_course=False)
    # the machine at the collar with the pendant plugged in; the player kneeling beside it
    mpos, myaw = Vector((0.0, -4.4, 0.06)), math.radians(90)
    mach = place_agent("surveyor", at=tuple(mpos), yaw=myaw, look=(0.0, -1.0, 0.3), name="MACHINE", tag="m")
    col = col_new("PLAYER")
    _, hand = mannequin(col, (0.95, -5.55, 0.06), math.radians(150), pose="reach", lean=0.35)
    pend = pendant(col, img=A.pendant_img, strength=1.6)
    Mp = (Matrix.Translation(hand + Vector((0, 0, 0.02))) @ Matrix.Rotation(math.radians(150), 4, "Z")
          @ Matrix.Rotation(math.radians(-40), 4, "Y") @ Matrix.Rotation(-math.pi / 2, 4, "Z"))
    for o in pend:
        o.matrix_world = Mp @ o.matrix_world
    port = agent_port(mach, tuple(mpos), myaw)
    exit_pt = Mp @ Vector((-0.13, 0, 0))
    cable(col, [exit_pt, exit_pt + Vector((0, 0, -0.3)), (0.5, -5.3, 0.1), port + Vector((0, -0.2, 0.02)), port], r=0.006, name="pendant_cable")
    cam((3.7, -7.2, 1.75), (0.3, -4.6, 0.45), focal=35, fstop=5.6)
    finish()

elif S == "g2_terminal_dusk":
    # first pass: strength 4, exposure 0 -> a black frame with a screen. The screen is the only
    # source that reaches a face here, so it is the key light: strength 14, and +1.2 stops so the
    # dusk sky still draws the roof-line. Not photometry: what made the frame read.
    sv = build_surface("dusk", terminal_img=A.replay_img, terminal_strength=24.0, post_img=A.post_img, post_strength=3.0)
    col = col_new("PLAYER")
    # the player at the bench, watching the replay
    mannequin(col, (-14.15, -8.15, 0.06), math.radians(90), pose="down", lean=0.12)
    cam((-12.55, -9.35, 1.42), (-13.55, -7.15, 1.05), focal=35, fstop=2.8)
    finish(exposure=1.8)

elif S == "g3_cable_in":
    reset()
    sky("clear")
    clear_stage(size=4.0)
    col = col_new("PRODUCT")
    mpos, myaw = Vector((0, 0, 0)), math.radians(0)
    mach = place_agent("surveyor", at=(0, 0, 0), yaw=0.0, name="MACHINE", tag="m", look=(3, 0, 0.3))
    port = agent_port(mach, (0, 0, 0), 0.0)
    plug = put(G.box("plug", (0.05, 0.028, 0.02), port + Vector((-0.028, 0, 0)), bevel=0.003, col=col), mats()["dark"], col)
    put(G.box("plug_latch", (0.02, 0.012, 0.006), port + Vector((-0.03, 0, 0.013)), bevel=0.002, col=col), mats()["key"], col)
    cable(col, [port + Vector((-0.05, 0, 0)), port + Vector((-0.25, 0.05, -0.05)), port + Vector((-0.5, 0.2, -0.2)), (-0.9, 0.5, 0.006)], r=0.006)
    cam((-0.62, -0.42, 0.30), port + Vector((-0.02, 0, 0.0)), focal=85, fstop=4.0)
    finish()

elif S == "g3_cable_out":
    reset()
    sky("clear")
    clear_stage(size=4.0)
    col = col_new("PRODUCT")
    mach = place_agent("surveyor", at=(0, 0, 0), yaw=0.0, name="MACHINE", tag="m", look=(3, 0, 0.3))
    port = agent_port(mach, (0, 0, 0), 0.0)
    # the plug pulled: hanging from the hand, 12 cm off the port, the port face open
    plug = put(G.box("plug", (0.05, 0.028, 0.02), port + Vector((-0.16, 0.02, -0.03)), rot=(0.2, 0.5, 0.1), bevel=0.003, col=col), mats()["dark"], col)
    cable(col, [port + Vector((-0.18, 0.02, -0.035)), port + Vector((-0.3, 0.1, -0.1)), port + Vector((-0.5, 0.25, -0.2)), (-0.9, 0.5, 0.006)], r=0.006)
    _, hand = mannequin(col, (-0.9, 0.55, 0.0), math.radians(-40), pose="reach", lean=0.4)
    cam((-0.62, -0.42, 0.30), port + Vector((-0.06, 0, 0.0)), focal=85, fstop=4.0)
    finish()

elif S == "g3_commit_wide":
    sv = build_surface("drizzle", kibble_z=None, terminal_img=A.terminal_img, post_img=A.post_img, post_strength=3.0)
    m = mats()
    col = col_new("PLAYER")
    # the cable coiled on the collar kerb, the plug lying loose; the kibble is gone
    for k in range(4):
        r = 0.16 + k * 0.012
        ring = [Vector((0.9 + r * math.cos(a), -2.0 + r * math.sin(a), 0.075 + k * 0.013)) for a in [math.radians(t) for t in range(0, 361, 20)]]
        cable(col, ring, r=0.006, name=f"coil{k}")
    put(G.box("plug", (0.05, 0.028, 0.02), (1.15, -2.2, 0.075), rot=(0, 0, 0.6), bevel=0.003, col=col), m["dark"], col)
    px, py = sv["post"]
    mannequin(col, (px - 0.15, py - 1.0, 0.06), math.radians(90), pose="down", lean=0.1)
    cam((6.2, -7.6, 2.0), (0.8, -1.8, 0.7), focal=38, fstop=5.6)
    finish(exposure=0.7)

elif S == "g3_descent":
    # looking down into the collar: the kibble a metre down, the machine's pale shell the last pale thing
    # first pass: camera at (0.2,-2.6,2.6) was too oblique and the collar frame hid the kibble;
    # from nearly overhead the kibble and the pale shell are the last lit things before the black
    sv = build_surface("overcast", kibble_z=-1.6, terminal_img=A.terminal_img, post_img=A.post_img, with_course=False)
    mach = place_agent("surveyor", at=(1.05, 0.0, -1.6 + 0.03), yaw=math.radians(90), name="MACHINE", tag="m", look=(1.05, 0, 30))
    cam((0.55, -1.35, 3.4), (1.0, 0.05, -1.7), focal=28, fstop=5.6)
    finish(exposure=0.5)

elif S == "g4_cave_stop":
    # underground: the same stop. A P2 passage, the machine halted at a narrowing, head down.
    reset()
    sky("cave")
    rk = E.rock("cave_rock", albedo_lo=0.045, albedo_hi=0.30, warm=1.0, wet=0.35)
    E.passage(width=3.4, height=4.6, length=22.0, mat=rk, seed=5, rubble=14)
    mach = place_agent("surveyor", at=(0, 0, 0), yaw=0.0, name="MACHINE", tag="m", look=(0.9, 0.3, -0.25), lamp=600.0, mud=0.85, dust=0.55)
    fix_lamp(mach, energy=600.0, aim_down_deg=22.0)
    cam((-2.3, -1.6, 1.1), (1.2, 0.1, 0.25), focal=36, fstop=5.6)
    finish()

elif S == "g4_cave_stop_above":
    reset()
    sky("cave")
    rk = E.rock("cave_rock", albedo_lo=0.045, albedo_hi=0.30, warm=1.0, wet=0.35)
    E.passage(width=3.4, height=4.6, length=22.0, mat=rk, seed=5, rubble=14)
    mach = place_agent("surveyor", at=(0, 0, 0), yaw=0.0, name="MACHINE", tag="m", look=(0.9, 0.3, -0.25), lamp=600.0, mud=0.85, dust=0.55)
    fix_lamp(mach, energy=600.0, aim_down_deg=22.0)
    cam((-1.6, -3.4, 3.6), (0.8, 0.0, 0.1), focal=35)
    finish(exposure=3.0)      # first pass at 0: a pool and nothing else; +1.5 was still a pool. Board exposure, not the game's.

elif S == "g5_leanto_night":
    # first pass: strength 6 -> black. A 0.57 x 0.35 m screen at strength 40 is roughly a 60 W
    # monitor at arm's length; at +1 stop it lights the bench, the hands and the underside of the roof.
    sv = build_surface("night", terminal_img=A.replay_img, terminal_strength=40.0, post_img=None, post_strength=0.0, with_course=False)
    col = col_new("PLAYER")
    mannequin(col, (-14.15, -8.15, 0.06), math.radians(90), pose="down", lean=0.12)
    cam((-12.55, -9.35, 1.42), (-13.55, -7.15, 1.05), focal=35, fstop=2.8)
    finish(exposure=1.0)

elif S == "g5_leanto_night_light":
    # the same night frame as g5_leanto_night with the yard work light on (--yard-lamp, default
    # 180 W here): the bench, the rack, the roof and the person, so the board shows the place;
    # the screen stays the only cool thing in it.
    if A.yard_lamp <= 0:
        A.yard_lamp = 180.0
    sv = build_surface("night", terminal_img=A.replay_img, terminal_strength=40.0, post_img=None, post_strength=0.0, with_course=False)
    col = col_new("PLAYER")
    mannequin(col, (-14.15, -8.15, 0.06), math.radians(90), pose="down", lean=0.12)
    cam((-11.9, -10.1, 1.55), (-13.6, -7.2, 1.0), focal=30, fstop=2.8)
    finish(exposure=0.6)

elif S == "g5_leanto_night_wide":
    # first pass: sky 0.0015, +1 stop -> a black frame with a 12 px screen. Sky 0.004 at +2.5 stops
    # puts the headframe against a sky just short of black; the screen is still the only warm thing.
    sv = build_surface("night", terminal_img=A.replay_img, terminal_strength=40.0, post_img=None, post_strength=0.0, with_course=False)
    col = col_new("PLAYER")
    mannequin(col, (-14.15, -8.15, 0.06), math.radians(90), pose="down", lean=0.12)
    cam((4.0, -22.0, 2.0), (-7.0, -3.5, 4.0), focal=32)
    finish(exposure=2.5)

elif S == "a_yard_wide":
    # the establishing wide of the whole place from the yard: lean-to, headframe, course, sky
    sv = build_surface("overcast", kibble_z=0.6, terminal_img=A.terminal_img, post_img=A.post_img)
    parked_machines(sv["col"], sv["rack"])
    mach = place_agent("surveyor", at=(-9.5, -5.0, 0.06), yaw=math.radians(20), name="MACHINE", tag="m", look=(0, 0, 0.5))
    col = col_new("PLAYER")
    mannequin(col, (-8.2, -6.2, 0.06), math.radians(60), pose="down")
    stage_junction(sv, "overcast", A.pendant_img)
    cam((-24.0, -19.0, 3.2), (-2.0, -1.0, 2.2), focal=28)
    finish()

elif S == "a_yard_bench":
    sv = build_surface("overcast", kibble_z=0.6, terminal_img=A.terminal_img, post_img=A.post_img, with_course=False)
    parked_machines(sv["col"], sv["rack"])
    mach = place_agent("surveyor", at=(-10.2, -5.1, 0.06), yaw=math.radians(180), name="MACHINE", tag="m", look=(-13, -5.1, 0.3))
    port = agent_port(mach, (-10.2, -5.1, 0.06), math.radians(180))
    cable(sv["col"], [(-12.9, -6.3, 1.3), (-12.4, -6.0, 0.6), (-11.0, -5.3, 0.1), port + Vector((0.2, 0, 0.02)), port], r=0.006, name="charge_cable")
    cam((-7.6, -10.6, 1.7), (-12.0, -6.4, 0.9), focal=35, fstop=5.6)
    finish()

elif S == "g4_cave_stop_plus3":
    # the SAME frame as g4_cave_stop at +3 stops: what is actually in front of the machine. Not the game.
    reset()
    sky("cave")
    rk = E.rock("cave_rock", albedo_lo=0.045, albedo_hi=0.30, warm=1.0, wet=0.35)
    E.passage(width=3.4, height=4.6, length=22.0, mat=rk, seed=5, rubble=14)
    mach = place_agent("surveyor", at=(0, 0, 0), yaw=0.0, name="MACHINE", tag="m", look=(0.9, 0.3, -0.25), lamp=600.0, mud=0.85, dust=0.55)
    fix_lamp(mach, energy=600.0, aim_down_deg=22.0)
    cam((-2.3, -1.6, 1.1), (1.2, 0.1, 0.25), focal=36, fstop=5.6)
    finish(exposure=3.0)

elif S == "g1_junction_plan":
    # the staged junction from straight above, 9.5 m up: the plan the pendant draws, as a photograph.
    # The machine, the three mouths, the way back, the person at the wall, the cable.
    sv = build_surface("overcast", terminal_img=A.terminal_img, post_img=A.post_img)
    mach, hand, mpos, myaw, ppos, pyaw = stage_junction(sv, "overcast", A.pendant_img)
    b = sv["jpos"]
    cam((b.x + 0.01, b.y - 0.6, 9.5), (b.x, b.y, 0.0), focal=30)
    finish()

elif S == "g3_commit_post":
    # after the commit: the player at the listening post, the belief map on its small screen,
    # the collar and the rope behind; drizzle. The surface end of the link.
    sv = build_surface("drizzle", kibble_z=None, terminal_img=A.terminal_img, post_img=A.post_img, post_strength=4.0)
    col = col_new("PLAYER")
    px, py = sv["post"]
    mannequin(col, (px - 0.15, py - 1.0, 0.06), math.radians(90), pose="down", lean=0.1)
    cam((px + 2.6, py - 2.9, 1.55), (px - 0.1, py - 0.2, 0.9), focal=40, fstop=4.0)
    finish(exposure=0.5)

else:
    raise SystemExit(f"unknown shot {S}")
