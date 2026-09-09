"""Vision-board probe for THE ANCIENT MACHINERY: the Assayer in every state, its two
siblings (the Haulage, the Bus), the download pose, and a spent machine.

Run with a Blender install (5.2 is what everything here was rendered on):

  "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b -P \
      docs/art/vision/machinery/machinery_probe.py -- --shot dormant_elevation --out <ABS>.png

`--out` must be ABSOLUTE. `--list` prints every shot name.

Two lighting rigs, so that a concept is shown before its mood:

  CLEAR    neutral grey world at strength 1 + one soft area key 45 deg high, AgX Base
           Contrast, a grey ground plane with the 1.2 m industrial module ruled on it.
           Not the game. A concept-artist's studio, so the thing can be SEEN.
  IN-SITU  world background 0, fog 0.010-0.014, and only the four sources the fiction
           supplies: the visiting machine's white work lamp (re-aimed, 8-10 deg down),
           running lights at strength <= 3 in BONE, the Assayer's winch head and anvil
           at 1900 K -> 2400 K -> 4000 K, and nothing else.

Geometry is THE-MACHINERY.md 2.1 at 0.6 m/cell; materials are ART-DIRECTION.md 5.2
(cast iron wet a century / bearing steel still working / graphitised below the
waterline). Everything that is not in either of those documents is a PROPOSAL and is
listed in NOTES.md beside the images. Nothing here modifies agent_model.
"""
import argparse
import math
import os
import random
import sys

ROOT = r"C:/Users/jackh/documents/programming/Blindside"
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "docs/art/probes"))

import bpy  # noqa: E402
import bmesh  # noqa: E402
from mathutils import Vector, Euler, Matrix  # noqa: E402

from agent_model import params as P  # noqa: E402
from agent_model import geometry as G  # noqa: E402
from agent_model import materials as M  # noqa: E402
from agent_model.build import build_agent  # noqa: E402
from agent_model.motion import Mover, script  # noqa: E402
import p2_env as E  # noqa: E402

CELL = 0.6

# palette.py values, linearised from their sRGB hexes (the display works in sRGB; a
# Cycles emission wants linear)
def _lin(c):
    return tuple((v / 12.92) if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in c)


BONE = _lin((0.949, 0.902, 0.824))       # #F2E6D2 player
EMBER = _lin((1.000, 0.478, 0.184))      # #FF7A2F rival
WARM_DIM = _lin((0.478, 0.400, 0.314))   # #7A6650 beacon pilot
LAMP_WHITE = (1.00, 0.98, 0.95)

# ART-DIRECTION 5.2: three ages of iron
CAST_IRON_RGB = (0.075, 0.038, 0.021)
BEARING_STEEL_RGB = (0.52, 0.50, 0.48)
GRAPHITISED_RGB = (0.010, 0.0095, 0.009)
PALE_SHELL, GRAPHITE = (0.66, 0.63, 0.57), (0.050, 0.052, 0.058)


def blackbody(T):
    """Planckian locus (Kim et al. 2002) -> linear sRGB, normalised to max 1.
    Used for LIGHTS; materials use Blender's own Blackbody node. Values, for the notes:
      1900 K (1.00, 0.25, 0.01)  2100 K (1.00, 0.29, 0.02)  2400 K (1.00, 0.35, 0.05)
      4000 K (1.00, 0.65, 0.38)"""
    T = float(T)
    if T <= 4000:
        x = -0.2661239e9 / T ** 3 - 0.2343589e6 / T ** 2 + 0.8776956e3 / T + 0.179910
    else:
        x = -3.0258469e9 / T ** 3 + 2.1070379e6 / T ** 2 + 0.2226347e3 / T + 0.240390
    if T <= 2222:
        y = -1.1063814 * x ** 3 - 1.34811020 * x ** 2 + 2.18555832 * x - 0.20219683
    elif T <= 4000:
        y = -0.9549476 * x ** 3 - 1.37418593 * x ** 2 + 2.09137015 * x - 0.16748867
    else:
        y = 3.0817580 * x ** 3 - 5.87338670 * x ** 2 + 3.75112997 * x - 0.37001483
    X, Y, Z = x / y, 1.0, (1 - x - y) / y
    r = 3.2406 * X - 1.5372 * Y - 0.4986 * Z
    g = -0.9689 * X + 1.8758 * Y + 0.0415 * Z
    b = 0.0557 * X - 0.2040 * Y + 1.0570 * Z
    m = max(r, g, b)
    return (max(r, 0) / m, max(g, 0) / m, max(b, 0) / m)


# ---------------------------------------------------------------------------------------
# materials
# ---------------------------------------------------------------------------------------
def _mix_rgb(nt):
    """ShaderNodeMix in RGBA mode. Sockets by INDEX: p2_env links `inputs["A"]`, which is
    the float A on a Mix node and is silently ignored in colour mode."""
    n = nt.nodes.new("ShaderNodeMix")
    n.data_type = "RGBA"
    return n, n.inputs[0], n.inputs[6], n.inputs[7]


def _mix_f(nt):
    n = nt.nodes.new("ShaderNodeMix")
    n.data_type = "FLOAT"
    return n, n.inputs[0], n.inputs[2], n.inputs[3]


def cast_iron(name="cast_iron", waterline=None, tone=1.0, rough=0.86, scale=1.6):
    """Cast iron, wet a century: (0.075, 0.038, 0.021), roughness 0.86, metallic 0.
    Mottled on a low-frequency world-space noise, bump on two scales. Never orange.
    With a `waterline`: graphitised below it (black, velvety, roughness 0.98, intact in
    silhouette and dead in surface) and a 0.12 m mineral crust just above it."""
    m, nt, out = M._new(name)
    n, L = nt.nodes, nt.links.new
    b = n.new("ShaderNodeBsdfPrincipled")
    b.inputs["Metallic"].default_value = 0.0
    b.inputs["Specular IOR Level"].default_value = 0.32
    geo = n.new("ShaderNodeNewGeometry")
    big = n.new("ShaderNodeTexNoise")
    big.inputs["Scale"].default_value = scale
    big.inputs["Detail"].default_value = 9.0
    big.inputs["Roughness"].default_value = 0.6
    fine = n.new("ShaderNodeTexNoise")
    fine.inputs["Scale"].default_value = scale * 22
    fine.inputs["Detail"].default_value = 5.0
    L(geo.outputs["Position"], big.inputs["Vector"])
    L(geo.outputs["Position"], fine.inputs["Vector"])
    ramp = n.new("ShaderNodeValToRGB")
    c = CAST_IRON_RGB
    # the mottle runs from a near-black scale to the spec colour at its brightest, and
    # the bright end is pulled a third of the way toward neutral: wet iron, not rust
    ramp.color_ramp.elements[0].position = 0.30
    ramp.color_ramp.elements[0].color = (c[0] * 0.40 * tone, c[1] * 0.48 * tone, c[2] * 0.60 * tone, 1)
    ramp.color_ramp.elements[1].position = 0.76
    ramp.color_ramp.elements[1].color = ((c[0] * 1.15 * 0.7 + 0.055 * 0.3) * tone, (c[1] * 1.15 * 0.7 + 0.050 * 0.3) * tone,
                                         (c[2] * 1.15 * 0.7 + 0.046 * 0.3) * tone, 1)
    L(big.outputs["Fac"], ramp.inputs["Fac"])
    colour = ramp.outputs["Color"]
    rgh = n.new("ShaderNodeMath")
    rgh.operation = "MULTIPLY_ADD"
    rgh.inputs[1].default_value = 0.12
    rgh.inputs[2].default_value = rough - 0.06
    L(big.outputs["Fac"], rgh.inputs[0])
    roughness = rgh.outputs[0]
    bmp2 = n.new("ShaderNodeBump")
    bmp2.inputs["Strength"].default_value = 0.12
    bmp2.inputs["Distance"].default_value = 0.01
    L(fine.outputs["Fac"], bmp2.inputs["Height"])
    bmp = n.new("ShaderNodeBump")
    bmp.inputs["Strength"].default_value = 0.30
    bmp.inputs["Distance"].default_value = 0.02
    L(big.outputs["Fac"], bmp.inputs["Height"])
    L(bmp2.outputs["Normal"], bmp.inputs["Normal"])
    normal = bmp.outputs["Normal"]

    if waterline is not None:
        sep = n.new("ShaderNodeSeparateXYZ")
        L(geo.outputs["Position"], sep.inputs["Vector"])
        sub = n.new("ShaderNodeMapRange")
        sub.inputs["From Min"].default_value = waterline + 0.02
        sub.inputs["From Max"].default_value = waterline - 0.02
        sub.inputs["To Min"].default_value = 0.0
        sub.inputs["To Max"].default_value = 1.0
        sub.clamp = True
        L(sep.outputs["Z"], sub.inputs["Value"])
        tide = n.new("ShaderNodeMapRange")
        tide.inputs["From Min"].default_value = waterline + 0.14
        tide.inputs["From Max"].default_value = waterline + 0.01
        tide.inputs["To Min"].default_value = 0.0
        tide.inputs["To Max"].default_value = 0.8
        tide.clamp = True
        L(sep.outputs["Z"], tide.inputs["Value"])
        crust, cf, ca, cb = _mix_rgb(nt)
        cb.default_value = (0.36, 0.33, 0.29, 1)
        L(tide.outputs["Result"], cf)
        L(colour, ca)
        graph, gf, ga, gb = _mix_rgb(nt)
        gb.default_value = (*GRAPHITISED_RGB, 1)
        L(sub.outputs["Result"], gf)
        L(crust.outputs[2], ga)
        colour = graph.outputs[2]
        rmix, rf, ra, rb = _mix_f(nt)
        rb.default_value = 0.98
        L(sub.outputs["Result"], rf)
        L(roughness, ra)
        roughness = rmix.outputs[0]
        # graphitised iron is velvety: a sheen where the noise bump was
        sh = n.new("ShaderNodeMath")
        sh.operation = "MULTIPLY"
        sh.inputs[1].default_value = 0.6
        L(sub.outputs["Result"], sh.inputs[0])
        L(sh.outputs[0], b.inputs["Sheen Weight"])
    L(colour, b.inputs["Base Color"])
    L(roughness, b.inputs["Roughness"])
    L(normal, b.inputs["Normal"])
    L(b.outputs[0], out.inputs[0])
    return m


def bearing_steel(name="bearing_steel", rough=0.30, tint=BEARING_STEEL_RGB):
    """The one clean thing on the object: what is still rubbing. Metallic 1, rough 0.30."""
    m, nt, out = M._new(name)
    n, L = nt.nodes, nt.links.new
    b = n.new("ShaderNodeBsdfPrincipled")
    b.inputs["Base Color"].default_value = (*tint, 1)
    b.inputs["Metallic"].default_value = 1.0
    geo = n.new("ShaderNodeNewGeometry")
    tex = n.new("ShaderNodeTexNoise")
    tex.inputs["Scale"].default_value = 60
    L(geo.outputs["Position"], tex.inputs["Vector"])
    r = n.new("ShaderNodeMath")
    r.operation = "MULTIPLY_ADD"
    r.inputs[1].default_value = 0.10
    r.inputs[2].default_value = rough - 0.05
    L(tex.outputs["Fac"], r.inputs[0])
    L(r.outputs[0], b.inputs["Roughness"])
    L(b.outputs[0], out.inputs[0])
    return m


def graphitised(name="graphitised"):
    m, nt, out = M._new(name)
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    b.inputs["Base Color"].default_value = (*GRAPHITISED_RGB, 1)
    b.inputs["Roughness"].default_value = 0.98
    b.inputs["Metallic"].default_value = 0.0
    b.inputs["Sheen Weight"].default_value = 0.6
    b.inputs["Specular IOR Level"].default_value = 0.2
    nt.links.new(b.outputs[0], out.inputs[0])
    return m


def porcelain(name="porcelain"):
    """Glazed white: the only clean, white, undamaged material in the game."""
    m, nt, out = M._new(name)
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    b.inputs["Base Color"].default_value = (0.86, 0.86, 0.82, 1)
    b.inputs["Roughness"].default_value = 0.12
    b.inputs["Coat Weight"].default_value = 1.0
    b.inputs["Coat Roughness"].default_value = 0.04
    nt.links.new(b.outputs[0], out.inputs[0])
    return m


def grease(name="grease"):
    m, nt, out = M._new(name)
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    b.inputs["Base Color"].default_value = (0.030, 0.024, 0.018, 1)
    b.inputs["Roughness"].default_value = 0.18
    b.inputs["Coat Weight"].default_value = 0.7
    b.inputs["Coat Roughness"].default_value = 0.1
    nt.links.new(b.outputs[0], out.inputs[0])
    return m


def hot(name, kelvin, strength):
    """An emissive surface at a colour temperature. Blender's Blackbody node, not a hand RGB."""
    m, nt, out = M._new(name)
    e = nt.nodes.new("ShaderNodeEmission")
    bb = nt.nodes.new("ShaderNodeBlackbody")
    bb.inputs["Temperature"].default_value = kelvin
    nt.links.new(bb.outputs["Color"], e.inputs["Color"])
    e.inputs["Strength"].default_value = strength
    nt.links.new(e.outputs[0], out.inputs[0])
    return m


def emissive_rgb(name, rgb, strength):
    m, nt, out = M._new(name)
    e = nt.nodes.new("ShaderNodeEmission")
    e.inputs["Color"].default_value = (*rgb, 1)
    e.inputs["Strength"].default_value = strength
    nt.links.new(e.outputs[0], out.inputs[0])
    return m


def water(name="water", corona_k=None, corona=0.0):
    """The sump surface: IOR 1.33, roughness 0.02 -- a mirror at grazing angle. With
    `corona`, the Bus is live: the WATER glows faintly, the conductor never does."""
    m, nt, out = M._new(name)
    n, L = nt.nodes, nt.links.new
    g = n.new("ShaderNodeBsdfGlass")
    g.inputs["IOR"].default_value = 1.33
    g.inputs["Roughness"].default_value = 0.02
    g.inputs["Color"].default_value = (0.92, 0.94, 0.95, 1)
    shader = g.outputs[0]
    if corona > 0:
        e = n.new("ShaderNodeEmission")
        bb = n.new("ShaderNodeBlackbody")
        bb.inputs["Temperature"].default_value = corona_k or 2100
        L(bb.outputs["Color"], e.inputs["Color"])
        # the corona sits in the water, strongest near the conductor's line (y = 0)
        geo = n.new("ShaderNodeNewGeometry")
        sep = n.new("ShaderNodeSeparateXYZ")
        L(geo.outputs["Position"], sep.inputs["Vector"])
        ab = n.new("ShaderNodeMath")
        ab.operation = "ABSOLUTE"
        L(sep.outputs["Y"], ab.inputs[0])
        fall = n.new("ShaderNodeMapRange")
        fall.inputs["From Min"].default_value = 0.0
        fall.inputs["From Max"].default_value = 1.1
        fall.inputs["To Min"].default_value = corona
        fall.inputs["To Max"].default_value = corona * 0.15
        fall.clamp = True
        L(ab.outputs[0], fall.inputs["Value"])
        nz = n.new("ShaderNodeTexNoise")
        nz.inputs["Scale"].default_value = 3.0
        L(geo.outputs["Position"], nz.inputs["Vector"])
        mul = n.new("ShaderNodeMath")
        mul.operation = "MULTIPLY_ADD"
        mul.inputs[1].default_value = 0.8
        mul.inputs[2].default_value = 0.6
        L(nz.outputs["Fac"], mul.inputs[0])
        st = n.new("ShaderNodeMath")
        st.operation = "MULTIPLY"
        L(fall.outputs["Result"], st.inputs[0])
        L(mul.outputs[0], st.inputs[1])
        L(st.outputs[0], e.inputs["Strength"])
        add = n.new("ShaderNodeAddShader")
        L(g.outputs[0], add.inputs[0])
        L(e.outputs[0], add.inputs[1])
        shader = add.outputs[0]
    L(shader, out.inputs[0])
    return m


def grey_ground(name="clear_ground", albedo=0.34, module=1.2, gauge=0.6):
    """The CLEAR rig's floor: neutral grey with the 1.2 m module ruled on it and the
    0.6 m rail gauge as a pair of finer lines. A scale reference in every studio frame."""
    m, nt, out = M._new(name)
    n, L = nt.nodes, nt.links.new
    b = n.new("ShaderNodeBsdfPrincipled")
    b.inputs["Roughness"].default_value = 0.85
    b.inputs["Specular IOR Level"].default_value = 0.2
    geo = n.new("ShaderNodeNewGeometry")
    sep = n.new("ShaderNodeSeparateXYZ")
    L(geo.outputs["Position"], sep.inputs["Vector"])

    def lines(src, period, width):
        d = n.new("ShaderNodeMath")
        d.operation = "DIVIDE"
        d.inputs[1].default_value = period
        L(src, d.inputs[0])
        f = n.new("ShaderNodeMath")
        f.operation = "FRACT"
        L(d.outputs[0], f.inputs[0])
        s = n.new("ShaderNodeMath")
        s.operation = "SUBTRACT"
        s.inputs[1].default_value = 0.5
        L(f.outputs[0], s.inputs[0])
        a = n.new("ShaderNodeMath")
        a.operation = "ABSOLUTE"
        L(s.outputs[0], a.inputs[0])
        g = n.new("ShaderNodeMath")
        g.operation = "GREATER_THAN"
        g.inputs[1].default_value = 0.5 - width / period
        L(a.outputs[0], g.inputs[0])
        return g.outputs[0]

    lx = lines(sep.outputs["X"], module, 0.012)
    ly = lines(sep.outputs["Y"], module, 0.012)
    mx = n.new("ShaderNodeMath")
    mx.operation = "MAXIMUM"
    L(lx, mx.inputs[0])
    L(ly, mx.inputs[1])
    # the gauge: two fine lines at y = +-0.3 around y = 0, along X
    gy = n.new("ShaderNodeMath")
    gy.operation = "ABSOLUTE"
    L(sep.outputs["Y"], gy.inputs[0])
    g1 = n.new("ShaderNodeMath")
    g1.operation = "SUBTRACT"
    g1.inputs[1].default_value = gauge / 2
    L(gy.outputs[0], g1.inputs[0])
    g2 = n.new("ShaderNodeMath")
    g2.operation = "ABSOLUTE"
    L(g1.outputs[0], g2.inputs[0])
    g3 = n.new("ShaderNodeMath")
    g3.operation = "LESS_THAN"
    g3.inputs[1].default_value = 0.006
    L(g2.outputs[0], g3.inputs[0])
    g4 = n.new("ShaderNodeMath")
    g4.operation = "MULTIPLY"
    g4.inputs[1].default_value = 0.6
    L(g3.outputs[0], g4.inputs[0])
    allm = n.new("ShaderNodeMath")
    allm.operation = "MAXIMUM"
    L(mx.outputs[0], allm.inputs[0])
    L(g4.outputs[0], allm.inputs[1])
    mix, mf, ma, mb = _mix_rgb(nt)
    ma.default_value = (albedo, albedo, albedo, 1)
    mb.default_value = (albedo * 0.35, albedo * 0.35, albedo * 0.35, 1)
    L(allm.outputs[0], mf)
    L(mix.outputs[2], b.inputs["Base Color"])
    L(b.outputs[0], out.inputs[0])
    return m


def scour_rock(name="scour_rock", centre=(0, 0), r_scour=5.4, blend=1.6, warm=1.0):
    """The scour, as material: within ~9 cells of the footing the floor has no fines --
    bare, angular, fresh-fractured bedrock (albedo up to 0.42, fracture x3, rough) --
    surrounded by a floor of silt and rounded rubble. No boundary is drawn: one radial
    blend over `blend` metres. Display tints the scour; the world de-silts it."""
    m, nt, out = M._new(name)
    n, L = nt.nodes, nt.links.new
    b = n.new("ShaderNodeBsdfPrincipled")
    b.inputs["Specular IOR Level"].default_value = 0.3
    geo = n.new("ShaderNodeNewGeometry")

    def tone(v):
        return (v * (1.0 + 0.22 * warm), v * (1.0 - 0.02 * warm), v * (1.0 - 0.28 * warm), 1.0)

    # radial factor: 0 inside the scour, 1 outside
    dist = n.new("ShaderNodeVectorMath")
    dist.operation = "DISTANCE"
    dist.inputs[1].default_value = (centre[0], centre[1], 0.0)
    L(geo.outputs["Position"], dist.inputs[0])
    edge = n.new("ShaderNodeTexNoise")
    edge.inputs["Scale"].default_value = 0.7
    L(geo.outputs["Position"], edge.inputs["Vector"])
    wob = n.new("ShaderNodeMath")
    wob.operation = "MULTIPLY_ADD"
    wob.inputs[1].default_value = 1.6
    wob.inputs[2].default_value = -0.8
    L(edge.outputs["Fac"], wob.inputs[0])
    dw = n.new("ShaderNodeMath")
    dw.operation = "ADD"
    L(dist.outputs["Value"], dw.inputs[0])
    L(wob.outputs[0], dw.inputs[1])
    f = n.new("ShaderNodeMapRange")
    f.inputs["From Min"].default_value = r_scour - blend / 2
    f.inputs["From Max"].default_value = r_scour + blend / 2
    f.interpolation_type = "SMOOTHSTEP"
    f.clamp = True
    L(dw.outputs[0], f.inputs["Value"])
    fac = f.outputs["Result"]

    # inside: fresh fracture, angular, pale
    vor = n.new("ShaderNodeTexVoronoi")
    vor.inputs["Scale"].default_value = 18.0
    vor.inputs["Randomness"].default_value = 0.85
    L(geo.outputs["Position"], vor.inputs["Vector"])
    vramp = n.new("ShaderNodeValToRGB")
    vramp.color_ramp.elements[0].position = 0.05
    vramp.color_ramp.elements[0].color = tone(0.20)
    vramp.color_ramp.elements[1].position = 0.75
    vramp.color_ramp.elements[1].color = tone(0.42)
    L(vor.outputs["Distance"], vramp.inputs["Fac"])
    # outside: silt, bedded, darker, smoother
    bed = n.new("ShaderNodeTexNoise")
    bed.inputs["Scale"].default_value = 0.9
    bed.inputs["Detail"].default_value = 10.0
    L(geo.outputs["Position"], bed.inputs["Vector"])
    bramp = n.new("ShaderNodeValToRGB")
    bramp.color_ramp.elements[0].position = 0.3
    bramp.color_ramp.elements[0].color = tone(0.05)
    bramp.color_ramp.elements[1].position = 0.8
    bramp.color_ramp.elements[1].color = tone(0.28)
    L(bed.outputs["Fac"], bramp.inputs["Fac"])
    cmix, cf, ca, cb = _mix_rgb(nt)
    L(fac, cf)
    L(vramp.outputs["Color"], ca)
    L(bramp.outputs["Color"], cb)
    L(cmix.outputs[2], b.inputs["Base Color"])
    rmix, rf, ra, rb = _mix_f(nt)
    ra.default_value = 0.88
    rb.default_value = 0.72
    L(fac, rf)
    L(rmix.outputs[0], b.inputs["Roughness"])
    # bump: crisp voronoi facets inside, soft bedding outside
    bin_ = n.new("ShaderNodeBump")
    bin_.inputs["Strength"].default_value = 0.9
    bin_.inputs["Distance"].default_value = 0.05
    L(vor.outputs["Distance"], bin_.inputs["Height"])
    bout = n.new("ShaderNodeBump")
    bout.inputs["Strength"].default_value = 0.35
    bout.inputs["Distance"].default_value = 0.05
    L(bed.outputs["Fac"], bout.inputs["Height"])
    nmix = n.new("ShaderNodeMix")
    nmix.data_type = "VECTOR"
    L(fac, nmix.inputs[0])
    L(bin_.outputs["Normal"], nmix.inputs[4])
    L(bout.outputs["Normal"], nmix.inputs[5])
    L(nmix.outputs[1], b.inputs["Normal"])
    L(b.outputs[0], out.inputs[0])
    return m


def dust_puff(name="dust"):
    m, nt, out = M._new(name)
    n, L = nt.nodes, nt.links.new
    t = n.new("ShaderNodeBsdfTranslucent")
    t.inputs["Color"].default_value = (0.55, 0.50, 0.42, 1)
    tr = n.new("ShaderNodeBsdfTransparent")
    mx = n.new("ShaderNodeMixShader")
    mx.inputs[0].default_value = 0.78
    L(tr.outputs[0], mx.inputs[1])
    L(t.outputs[0], mx.inputs[2])
    L(mx.outputs[0], out.inputs[0])
    return m


# ---------------------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------------------
def _link(o, col):
    for c in list(o.users_collection):
        c.objects.unlink(o)
    col.objects.link(o)
    return o


def _text(name, body, size, loc, rot, extrude, col, mat):
    bpy.ops.object.text_add(location=loc, rotation=rot)
    t = bpy.context.object
    t.data.body = body
    t.data.size = size
    t.data.extrude = extrude
    t.data.align_x = "CENTER"
    t.data.align_y = "CENTER"
    bpy.ops.object.convert(target="MESH")
    o = bpy.context.object
    o.name = name
    G.set_material(o, mat)
    return _link(o, col)


def spin_z(v, deg):
    r = math.radians(deg)
    return Vector((v.x * math.cos(r) - v.y * math.sin(r), v.x * math.sin(r) + v.y * math.cos(r), v.z))


def move_collection(col, offset, yaw_deg=0.0):
    R = Matrix.Rotation(math.radians(yaw_deg), 4, "Z")
    T = Matrix.Translation(Vector(offset))
    for o in col.all_objects:
        if o.parent is None:
            o.matrix_world = T @ R @ o.matrix_world


# ---------------------------------------------------------------------------------------
# THE ASSAYER
# ---------------------------------------------------------------------------------------
def assayer(at=(0, 0, 0), aim_deg=0.0, hammer_frac=0.0, tank_fill=1.0, drip=True,
            hot_k=None, hot_s=0.0, waterline=None, name="ASSAYER", cans=True,
            boom_pivot=None):
    """THE-MACHINERY.md 2.1 at 0.6 m/cell, dressed per ART-DIRECTION.md 5.2.

      footing   3 legs 120 deg, hub r 0.60 m at z 0.72 -> pads at r 1.56 m
      anvil     the hub IS the anvil: a hex block the hammer lands on, strike face steel
      mast      hex, 0.96 across flats, z 1.05 -> 6.60, 2 deg draft, three flanges
      boom      4.20 m at z 5.40 on a slew ring; five ribs, ten transducer cans
      hammer    hex ring 1.20 across, 0.60 deep, riding the mast: rest z ~1.35, top ~4.75
      bolt ring 8 stanchions at r 2.04 (the old service platform, four bays of grating)
      tank      header tank on a bracket, with a SIGHT GLASS (proposal) showing the level
      winch     drum + brake band at the mast head on the +Y side, chain over a sheave
      hot       `hot_k`/`hot_s`: colour temperature and strength of the winch band and
                the anvil face (the two hot points). None = dormant, emits nothing.

    `hammer_frac` 0 = on the anvil, 1 = wound to the top of its travel.
    `boom_pivot`  if given, everything above the slew ring is parented to this empty so a
                  shot can animate the slew (motion blur)."""
    col = G.new_collection(name)
    base = Vector(at)
    iron = cast_iron(name + "_iron", waterline=waterline)
    iron_d = cast_iron(name + "_iron_dark", waterline=waterline, tone=0.7, scale=3.0)
    steel = bearing_steel(name + "_steel")
    steel_dull = bearing_steel(name + "_steel_dull", rough=0.42, tint=(0.36, 0.34, 0.32))
    out = {"col": col}

    def put(o, m, parent=None):
        o.location = Vector(o.location) + base
        G.set_material(o, m)
        _link(o, col)
        if parent is not None:
            o.parent = parent
            o.matrix_parent_inverse = parent.matrix_world.inverted()
        return o

    def fillet_strip(nm, a, b, w, m):
        """a rib/web along a member: the casting language, cheaply."""
        return put(G.strut(nm, Vector(a), Vector(b), w, w * 0.45, w, w * 0.45, bevel=0.004), m)

    HUB_R, HUB_Z, PAD_R = 0.60, 0.75, 1.56
    ANVIL_Z0, ANVIL_Z1 = 0.55, 1.05
    MAST_R = 0.48 / math.cos(math.radians(30))
    MAST_Z0, MAST_Z1 = ANVIL_Z1, 6.60
    BOOM_Z = 5.40
    HEX = math.radians(30)

    # ---- footing: three splayed box-section legs, anchor pads, tie rods -------------------
    for k in range(3):
        a = math.radians(90 + 120 * k)
        top = Vector((math.cos(a) * HUB_R, math.sin(a) * HUB_R, HUB_Z))
        foot = Vector((math.cos(a) * PAD_R, math.sin(a) * PAD_R, 0.10))
        put(G.strut(f"leg{k}", top, foot, 0.22, 0.30, 0.26, 0.18, bevel=0.012), iron)
        # a web rib on the top face of each leg: a casting has ribs on every flat plane
        fillet_strip(f"leg_rib{k}", top + Vector((0, 0, 0.02)), foot + Vector((0, 0, 0.02)), 0.05, iron_d)
        pad = put(G.box(f"pad{k}", (0.50, 0.50, 0.12), (foot.x, foot.y, 0.06), rot=(0, 0, a), bevel=0.012), iron_d)
        for bb_ in range(4):
            ang = a + bb_ * math.pi / 2 + math.pi / 4
            put(G.cyl(f"padbolt{k}{bb_}", 0.032, 0.032, 0.08,
                      (foot.x + math.cos(ang) * 0.19, foot.y + math.sin(ang) * 0.19, 0.14), verts=8), steel_dull)
        a2 = math.radians(90 + 120 * ((k + 1) % 3))
        put(G.segment(f"tie{k}", Vector((math.cos(a) * PAD_R * 0.85, math.sin(a) * PAD_R * 0.85, 0.22)),
                      Vector((math.cos(a2) * PAD_R * 0.85, math.sin(a2) * PAD_R * 0.85, 0.22)), 0.03, 0.03, verts=8), iron_d)
    # ---- the anvil block (hub): hex, parting line, raised part number, strike face -----
    anvil = put(G.cyl("anvil", 0.80, 0.74, ANVIL_Z1 - ANVIL_Z0, (0, 0, (ANVIL_Z0 + ANVIL_Z1) / 2),
                      rot=(0, 0, HEX), verts=6, bevel=0.015), iron)
    put(G.cyl("anvil_parting", 0.805, 0.805, 0.012, (0, 0, ANVIL_Z0 + 0.20), rot=(0, 0, HEX), verts=6), iron_d)
    put(G.cyl("anvil_face", 0.70, 0.70, 0.03, (0, 0, ANVIL_Z1 + 0.012), rot=(0, 0, HEX), verts=6), steel)
    # raised index number and the foundry mark on one flat of the anvil
    # on the -30 deg flat, which leg 2 also meets: the number sits in the band above the
    # leg's top and ON the flat (apothem + 4 mm), the mark lower and to the left of the leg
    def apothem(z):
        return (0.80 - 0.06 * (z - ANVIL_Z0) / (ANVIL_Z1 - ANVIL_Z0)) * math.cos(math.radians(30))
    NUM_Z = 0.965
    ap = apothem(NUM_Z) + 0.004
    fx, fy = ap * math.cos(math.radians(-30)), ap * math.sin(math.radians(-30))
    _text("anvil_number", "K 14", 0.11, (base.x + fx, base.y + fy, base.z + NUM_Z),
          (math.pi / 2, 0, math.radians(60)), 0.006, col, iron_d)
    dm = apothem(0.63) / math.cos(math.radians(20)) + 0.007
    mx, my = dm * math.cos(math.radians(-50)), dm * math.sin(math.radians(-50))
    put(G.cyl("foundry_mark", 0.05, 0.05, 0.012, (mx, my, 0.63), rot=(math.pi / 2, 0, math.radians(60)), verts=16), iron_d)
    put(G.box("foundry_bar", (0.012, 0.075, 0.014), (mx * 1.008, my * 1.008, 0.63), rot=(0, 0, math.radians(60))), iron_d)
    out["anvil_top"] = base + Vector((0, 0, ANVIL_Z1 + 0.03))

    # ---- mast: hex prism with draft, flanges, the pawl track, ladder ----------------------
    put(G.cyl("mast", MAST_R, MAST_R * 0.90, MAST_Z1 - MAST_Z0, (0, 0, (MAST_Z0 + MAST_Z1) / 2),
              rot=(0, 0, HEX), verts=6, bevel=0.012), iron)
    for z in (2.35, 3.95, 5.55):
        put(G.cyl(f"flange{int(z * 100)}", MAST_R * 1.12, MAST_R * 1.12, 0.10, (0, 0, z), rot=(0, 0, HEX), verts=6, bevel=0.01), iron_d)
        for k in range(6):
            a = math.radians(60 * k)
            put(G.cyl(f"flangebolt{int(z * 100)}_{k}", 0.028, 0.028, 0.05,
                      (math.cos(a) * MAST_R * 1.03, math.sin(a) * MAST_R * 1.03, z), rot=(0, math.pi / 2, a), verts=8), steel_dull)
    # the ratchet track: bearing steel, the pawl has bitten it a century. On the +X flat.
    track_x = MAST_R * math.cos(math.radians(30)) * 0.94
    put(G.box("track", (0.05, 0.16, MAST_Z1 - MAST_Z0 - 0.5), (track_x + 0.02, 0, (MAST_Z0 + MAST_Z1) / 2 - 0.1)), steel)
    z = MAST_Z0 + 0.45
    i = 0
    while z < MAST_Z1 - 0.6:
        put(G.box(f"tooth{i}", (0.03, 0.14, 0.035), (track_x + 0.055, 0, z), rot=(0, math.radians(-25), 0)), steel)
        z += 0.18
        i += 1
    # ladder on the -X flat: someone had to service this
    lx = -(MAST_R * math.cos(math.radians(30))) - 0.16
    for sd in (1, -1):
        put(G.box(f"stile{sd}", (0.035, 0.035, MAST_Z1 - MAST_Z0 - 0.3), (lx, sd * 0.20, (MAST_Z0 + MAST_Z1) / 2)), iron_d)
    for i in range(int((MAST_Z1 - MAST_Z0 - 0.4) / 0.30)):
        put(G.cyl(f"rung{i}", 0.014, 0.014, 0.40, (lx, 0, MAST_Z0 + 0.3 + i * 0.30), rot=(math.pi / 2, 0, 0), verts=8), steel_dull)
    # mast head cap and the sheave (on the +X flat, above the ratchet track and the chain)
    put(G.cyl("mast_cap", MAST_R * 1.0, MAST_R * 0.8, 0.30, (0, 0, MAST_Z1 + 0.15), rot=(0, 0, HEX), verts=6, bevel=0.01), iron)
    sx = MAST_R * math.cos(math.radians(30))
    sheave_p = Vector((sx + 0.12, 0, MAST_Z1 + 0.12))
    put(G.cyl("sheave", 0.17, 0.17, 0.06, sheave_p, rot=(math.pi / 2, 0, 0), verts=20), steel)
    put(G.box("sheave_bracket", (0.26, 0.06, 0.24), (sx + 0.02, 0, MAST_Z1 + 0.05), bevel=0.006), iron_d)

    # ---- the winch: drum and brake band on the +X side of the mast head -----------------
    drum_p = Vector((sx + 0.34, 0, MAST_Z1 - 0.62))
    put(G.box("winch_bracket", (0.34, 0.30, 0.16), (sx + 0.15, 0, MAST_Z1 - 0.62), bevel=0.008), iron_d)
    put(G.cyl("winch_drum", 0.26, 0.26, 0.46, drum_p, rot=(math.pi / 2, 0, 0), verts=22), iron)
    put(G.cyl("winch_drum_face", 0.20, 0.20, 0.47, drum_p, rot=(math.pi / 2, 0, 0), verts=22), steel)
    band_m = hot(name + "_winch_hot", hot_k, hot_s) if (hot_k and hot_s > 0) else iron_d
    put(G.torus("winch_band", 0.27, 0.035, drum_p, rot=(math.pi / 2, 0, 0)), band_m)
    out["winch"] = base + drum_p
    # the water motor that turns it: a small turbine casing on the same bracket
    put(G.cyl("water_motor", 0.16, 0.16, 0.22, drum_p + Vector((0, 0.36, 0)), rot=(math.pi / 2, 0, 0), verts=18), iron_d)
    # anvil hot ring: the friction is at the foot when the pawl holds the load
    if hot_k and hot_s > 0:
        put(G.torus("anvil_hot", 0.60, 0.02, (0, 0, ANVIL_Z1 + 0.03), col=None), hot(name + "_anvil_hot", hot_k, hot_s / 3.0))

    # ---- the boom on its slew ring, everything above it rotates ----------------------------
    pivot = boom_pivot
    if pivot is None:
        pivot = bpy.data.objects.new(name + "_PIVOT", None)
        col.objects.link(pivot)
        pivot.location = base + Vector((0, 0, BOOM_Z))
    pivot.rotation_euler = Euler((0, 0, math.radians(aim_deg)))
    bpy.context.view_layer.update()
    ring = put(G.cyl("slew_ring", MAST_R * 1.45, MAST_R * 1.30, 0.34, (0, 0, BOOM_Z - 0.02), rot=(0, 0, HEX), verts=12, bevel=0.01), iron)
    put(G.torus("slew_race", MAST_R * 1.44, 0.028, (0, 0, BOOM_Z + 0.15)), steel)
    root, tip = Vector((0.35, 0, BOOM_Z + 0.32)), Vector((4.20, 0, BOOM_Z + 0.32))
    put(G.strut("boom", root, tip, 0.54, 0.34, 0.30, 0.18, bevel=0.008), iron, pivot)
    put(G.cyl("boom_root", MAST_R * 1.25, MAST_R * 1.1, 0.42, (0, 0, BOOM_Z + 0.34), rot=(0, 0, HEX), verts=6, bevel=0.01), iron, pivot)
    for k in range(5):
        t = (k + 0.6) / 5.0
        halfw = (1.44 - (1.44 - 0.72) * t) / 2
        x = 0.6 + 0.84 * k
        put(G.segment(f"rib{k}", Vector((x, -halfw, BOOM_Z + 0.32)), Vector((x, halfw, BOOM_Z + 0.32)), 0.06, 0.06, verts=8), iron, pivot)
        if cans:
            for s in (-1, 1):
                put(G.cyl(f"can{k}{s}", 0.10, 0.10, 0.20, (x, s * halfw * 0.92, BOOM_Z + 0.14), verts=10), iron_d, pivot)
    for f in (0.55, 0.95):
        put(G.segment(f"stay{int(f * 100)}", Vector((0, 0, MAST_Z1 + 0.28)), root.lerp(tip, f) + Vector((0, 0, 0.1)), 0.018, 0.018, verts=6), steel_dull, pivot)
    put(G.strut("cwt_arm", Vector((-0.3, 0, BOOM_Z + 0.32)), Vector((-1.32, 0, BOOM_Z + 0.32)), 0.42, 0.30, 0.36, 0.28, bevel=0.008), iron, pivot)
    put(G.box("cwt", (0.54, 0.96, 0.54), (-1.32, 0, BOOM_Z + 0.32), bevel=0.02), iron_d, pivot)
    out["pivot"] = pivot

    # ---- the hammer: hex ring 1.2 across, 0.6 deep, strike face steel, pawl housing -----
    ham_r = 0.60 / math.cos(math.radians(30))
    z_rest = ANVIL_Z1 + 0.03 + 0.30
    z_top = BOOM_Z - 0.02 - 0.17 - 0.32
    ham_z = z_rest + hammer_frac * (z_top - z_rest)
    out["hammer_travel"] = z_top - z_rest
    put(G.cyl("hammer", ham_r, ham_r, 0.60, (0, 0, ham_z), rot=(0, 0, HEX), verts=6, bevel=0.02), iron)
    put(G.cyl("hammer_face", ham_r * 0.96, ham_r * 0.90, 0.05, (0, 0, ham_z - 0.30), rot=(0, 0, HEX), verts=6), steel)
    put(G.cyl("hammer_parting", ham_r * 1.005, ham_r * 1.005, 0.01, (0, 0, ham_z + 0.05), rot=(0, 0, HEX), verts=6), iron_d)
    put(G.box("pawl_housing", (0.18, 0.26, 0.30), (ham_r * 0.87 + 0.06, 0, ham_z + 0.05), bevel=0.008), iron_d)
    _text("hammer_number", "K 14 · 2", 0.09, (base.x + ham_r * math.cos(math.radians(-30)) * 0.87 + 0.0, base.y + ham_r * math.sin(math.radians(-30)) * 0.87, base.z + ham_z),
          (math.pi / 2, 0, math.radians(60)), 0.005, col, iron_d)
    # chain from the drum over the sheave down to the hammer's pawl housing
    put(G.segment("chain_up", drum_p + Vector((0.26, 0, 0)), sheave_p + Vector((0.17, 0, 0)), 0.016, 0.016, verts=6), steel)
    put(G.segment("chain_down", sheave_p + Vector((0.17, 0, 0)), Vector((sx + 0.29, 0, ham_z + 0.22)), 0.016, 0.016, verts=6), steel)
    put(G.box("chain_lug", (0.10, 0.10, 0.10), (sx + 0.29, 0, ham_z + 0.20)), iron_d)
    out["hammer_z"] = ham_z

    # ---- header tank on a bracket (-Y), sight glass, pipes, the drip ----------------------
    TANK = Vector((0, -1.25, 3.05))
    put(G.box("tank_bracket", (0.6, 0.9, 0.12), (0, -0.85, 2.48), bevel=0.008), iron_d)
    put(G.strut("tank_brace", Vector((0, -0.40, 1.7)), Vector((0, -1.15, 2.42)), 0.08, 0.08, 0.08, 0.08, bevel=0.004), iron_d)
    put(G.cyl("tank", 0.52, 0.52, 1.00, TANK, verts=20, bevel=0.015), iron)
    put(G.cyl("tank_lid", 0.55, 0.50, 0.06, TANK + Vector((0, 0, 0.52)), verts=20), iron_d)
    put(G.torus("tank_band_a", 0.53, 0.02, TANK + Vector((0, 0, 0.30))), iron_d)
    put(G.torus("tank_band_b", 0.53, 0.02, TANK + Vector((0, 0, -0.30))), iron_d)
    for i in range(16):
        a = i * math.pi / 8
        put(G.sphere(f"rivet{i}", 0.02, TANK + Vector((math.cos(a) * 0.53, math.sin(a) * 0.53, 0.42)), seg=8), steel_dull)
    # PROPOSAL: a sight glass on the +X face so the tank's level reads from the floor
    glass_m = M.lens(name + "_sightglass")
    gp = TANK + Vector((0.58, 0, 0))
    put(G.cyl("sight_glass", 0.035, 0.035, 0.84, gp, verts=12), glass_m)
    put(G.cyl("sight_top", 0.05, 0.05, 0.05, gp + Vector((0, 0, 0.44)), verts=10), steel_dull)
    put(G.cyl("sight_bot", 0.05, 0.05, 0.05, gp + Vector((0, 0, -0.44)), verts=10), steel_dull)
    if tank_fill > 0.02:
        wcol = M.bare_metal(name + "_tankwater", (0.10, 0.12, 0.13), 0.05)
        h = 0.80 * tank_fill
        put(G.cyl("sight_water", 0.028, 0.028, h, gp + Vector((0, 0, -0.40 + h / 2)), verts=10), wcol)
    # feed from the roof (the water that drowned the mine comes down a rising main from
    # the workings above -- it goes up into the dark), and the downpipe to the motor
    put(G.tube_along("feed_pipe", [TANK + Vector((0, -0.2, 0.55)), TANK + Vector((0, -0.2, 1.2)),
                                   Vector((0, -1.75, 6.0)), Vector((0, -1.85, 10.4))], 0.045, verts=8), iron_d)
    for zz in (4.6, 7.2):
        put(G.cyl(f"feed_flange{int(zz * 10)}", 0.075, 0.075, 0.06, (0, -1.75 - (zz - 6.0) * 0.023, zz), verts=10), iron)
    put(G.tube_along("down_pipe", [TANK + Vector((0.2, 0.3, -0.50)), Vector((0.25, -0.62, 1.95)),
                                   Vector((0.32, -0.55, 1.62)), Vector((0.56, -0.20, 1.55))], 0.04, verts=8), iron_d)
    put(G.tube_along("motor_pipe", [Vector((0.45, -0.85, 3.4)), Vector((0.95, -0.85, 3.4)), Vector((0.95, 0.55, 5.6)),
                                    drum_p + Vector((0.0, 0.36, -0.2))], 0.03, verts=8), iron_d)
    joint = Vector((0.32, -0.55, 1.62))
    put(G.cyl("pipe_joint", 0.07, 0.07, 0.09, joint, verts=10), iron)
    if drip:
        # one drip every two seconds onto the anvil: the entire dormant performance
        drop_m = M.lens(name + "_drop")
        put(G.sphere("drop", 0.012, (joint.x + 0.02, joint.y, joint.z - 0.30), seg=8), drop_m)
        put(G.torus("ripple", 0.05, 0.004, (joint.x + 0.02, joint.y, ANVIL_Z1 + 0.032)), drop_m)
        put(G.torus("ripple2", 0.11, 0.003, (joint.x + 0.02, joint.y, ANVIL_Z1 + 0.031)), drop_m)
        # a wet patch on the strike face where the drip lands
        wet_m = bearing_steel(name + "_wetface", rough=0.08)
        put(G.cyl("wet_patch", 0.16, 0.16, 0.004, (joint.x + 0.02, joint.y, ANVIL_Z1 + 0.03), verts=16), wet_m)

    # ---- the bolt ring: the old service platform, mostly gone ------------------------------
    for i in range(8):
        a = i * math.pi / 4 + 0.3
        put(G.cyl(f"stanchion{i}", 0.05, 0.04, 1.05, (math.cos(a) * 2.04, math.sin(a) * 2.04, 0.52), verts=8), iron_d)
        put(G.cyl(f"stanchion_base{i}", 0.09, 0.07, 0.06, (math.cos(a) * 2.04, math.sin(a) * 2.04, 0.03), verts=8), iron_d)
    for i in (0, 1, 2, 5):
        a = (i + 0.5) * math.pi / 4 + 0.3
        put(G.box(f"grate{i}", (1.30, 0.40, 0.04), (math.cos(a) * 2.04, math.sin(a) * 2.04, 1.03), rot=(0, 0, a + math.pi / 2)), iron_d)
    return out


# ---------------------------------------------------------------------------------------
# the chamber and the scour floor
# ---------------------------------------------------------------------------------------
def chamber(radius=10.5, height=11.5, waterline=None, rubble=True, seed=11, scour_r=5.4):
    """A stope tall enough to hold a 6.6 m mast: ART-DIRECTION 5.5's rule that a chamber
    holding something worth seeing must be taller than the passages that reach it."""
    rock = E.rock("wall_rock", albedo_lo=0.035, albedo_hi=0.30, warm=1.0, wet=0.40, waterline=waterline)
    col = E.chamber(radius=radius, height=height, mat=rock, seed=seed, aven=False, rubble=0)
    floor = bpy.data.objects["floor"]
    floor.modifiers["disp"].strength = 0.10
    G.set_material(floor, scour_rock("scour", r_scour=scour_r))
    if rubble:
        rng = random.Random(seed + 3)
        for i in range(34):
            ang = rng.uniform(0, 6.283)
            d = rng.uniform(scour_r + 0.6, radius * 0.9)
            r = rng.uniform(0.10, 0.50)
            bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=r, location=(math.cos(ang) * d, math.sin(ang) * d, r * 0.35))
            rk = bpy.context.object
            rk.name = f"rubble.{i}"
            rk.scale = (rng.uniform(0.8, 1.7), rng.uniform(0.8, 1.7), rng.uniform(0.3, 0.7))
            rk.rotation_euler = (rng.uniform(0, 3), rng.uniform(0, 3), rng.uniform(0, 3))
            E._displace(rk, 0.25, r * 1.1, depth=4)
            rk.data.shade_smooth()
            _link(rk, col)
            G.set_material(rk, rock)
        # fresh spall INSIDE the scour: angular, small, few -- what the shock shook down
        for i in range(9):
            ang = rng.uniform(0, 6.283)
            d = rng.uniform(1.9, scour_r - 0.4)
            r = rng.uniform(0.04, 0.11)
            bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=r, location=(math.cos(ang) * d, math.sin(ang) * d, r * 0.5))
            sp = bpy.context.object
            sp.name = f"spall.{i}"
            sp.scale = (rng.uniform(0.7, 1.5), rng.uniform(0.7, 1.5), rng.uniform(0.4, 0.8))
            sp.rotation_euler = (rng.uniform(0, 3), rng.uniform(0, 3), rng.uniform(0, 3))
            _link(sp, col)
            G.set_material(sp, rock)
    return col


def clear_near(pos, r=1.4):
    """Remove loose rubble within r of a point: the camera must not sit behind a rock."""
    pos = Vector(pos)
    for o in list(bpy.data.objects):
        if (o.name.startswith("rubble.") or o.name.startswith("spall.")) and (Vector(o.location) - pos).length < r:
            bpy.data.objects.remove(o, do_unlink=True)


def lobe_decal(aim_deg, r0=1.9, r1=5.4, half_deg=40, at=(0, 0)):
    """The lethal lobe of the LAST firing, in the silt only: a wedge of floor that is
    fractionally paler because the fines were shaken off it. A decal, not a glow."""
    bm = bmesh.new()
    inner, outer = [], []
    n = 24
    for i in range(n + 1):
        a = math.radians(aim_deg - half_deg + 2 * half_deg * i / n)
        inner.append(bm.verts.new((at[0] + math.cos(a) * r0, at[1] + math.sin(a) * r0, 0.0)))
        outer.append(bm.verts.new((at[0] + math.cos(a) * r1, at[1] + math.sin(a) * r1, 0.0)))
    for i in range(n):
        bm.faces.new((inner[i], inner[i + 1], outer[i + 1], outer[i]))
    o = G._mesh_object("lobe_decal", bm, smooth=True)
    o.location.z = 0.006
    sw = o.modifiers.new("wrap", "SHRINKWRAP")
    sw.target = bpy.data.objects["floor"]
    sw.offset = 0.01
    m, nt, out = M._new("lobe_decal")
    nn, L = nt.nodes, nt.links.new
    d = nn.new("ShaderNodeBsdfDiffuse")
    d.inputs["Color"].default_value = (0.55, 0.50, 0.42, 1)
    tr = nn.new("ShaderNodeBsdfTransparent")
    geo = nn.new("ShaderNodeNewGeometry")
    dist = nn.new("ShaderNodeVectorMath")
    dist.operation = "DISTANCE"
    dist.inputs[1].default_value = (at[0], at[1], 0)
    L(geo.outputs["Position"], dist.inputs[0])
    fade = nn.new("ShaderNodeMapRange")
    fade.inputs["From Min"].default_value = r0 + 0.3
    fade.inputs["From Max"].default_value = r1
    fade.inputs["To Min"].default_value = 0.45
    fade.inputs["To Max"].default_value = 0.0
    fade.clamp = True
    L(dist.outputs["Value"], fade.inputs["Value"])
    nz = nn.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 2.5
    L(geo.outputs["Position"], nz.inputs["Vector"])
    mul = nn.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    L(fade.outputs["Result"], mul.inputs[0])
    L(nz.outputs["Fac"], mul.inputs[1])
    mx = nn.new("ShaderNodeMixShader")
    L(mul.outputs[0], mx.inputs[0])
    L(tr.outputs[0], mx.inputs[1])
    L(d.outputs[0], mx.inputs[2])
    L(mx.outputs[0], out.inputs[0])
    G.set_material(o, m)
    return o


def axis_line(aim_deg, r0=1.7, r1=6.5, at=(0, 0), width=0.03, z=0.004):
    """CLEAR rig only: the boom axis marked on the floor (a studio annotation)."""
    a = math.radians(aim_deg)
    mid = ((r0 + r1) / 2)
    o = G.box("axis_line", (r1 - r0, width, 0.004), (at[0] + math.cos(a) * mid, at[1] + math.sin(a) * mid, z), rot=(0, 0, a))
    G.set_material(o, M.bare_metal("axis_ink", (0.02, 0.02, 0.02), 0.9))
    return o


def dust_ring(r0=0.9, r1=1.7, n=40, seed=4, z=0.12):
    """The one thing the strike throws into the air: a low ring of fines off the anvil."""
    rng = random.Random(seed)
    m = dust_puff()
    for i in range(n):
        a = rng.uniform(0, 6.283)
        d = rng.uniform(r0, r1)
        r = rng.uniform(0.05, 0.13)
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=r, location=(math.cos(a) * d, math.sin(a) * d, z + rng.uniform(-0.05, 0.22)))
        o = bpy.context.object
        o.name = f"dust.{i}"
        o.scale = (rng.uniform(0.8, 1.6), rng.uniform(0.8, 1.6), rng.uniform(0.5, 0.9))
        o.data.shade_smooth()
        G.set_material(o, m)


# ---------------------------------------------------------------------------------------
# THE WORKED DRIVE along a path (for the Haulage and the Bus)
# ---------------------------------------------------------------------------------------
def horseshoe(hw=1.20, leg=1.20, nl=8, na=26):
    pts = [(hw, leg * k / nl) for k in range(nl + 1)]
    pts += [(hw * math.cos(math.pi * k / na), leg + hw * math.sin(math.pi * k / na)) for k in range(1, na)]
    pts += [(-hw, leg * (nl - k) / nl) for k in range(nl + 1)]
    return pts


def make_path(straight_in=8.0, arc_r=11.0, arc_deg=38.0, straight_out=8.0, step=0.4):
    """A polyline in XY: straight along +X, a left-hand arc, straight again."""
    pts = []
    x = -straight_in
    while x < 0:
        pts.append(Vector((x, 0.0)))
        x += step
    n = max(2, int(arc_r * math.radians(arc_deg) / step))
    for i in range(n + 1):
        a = math.radians(arc_deg) * i / n
        pts.append(Vector((arc_r * math.sin(a), arc_r * (1 - math.cos(a)))))
    end = pts[-1]
    t = Vector((math.cos(math.radians(arc_deg)), math.sin(math.radians(arc_deg))))
    s = step
    while s <= straight_out:
        pts.append(end + t * s)
        s += step
    return pts


class Path:
    def __init__(self, pts):
        self.pts = pts
        self.s = [0.0]
        for a, b in zip(pts, pts[1:]):
            self.s.append(self.s[-1] + (b - a).length)
        self.length = self.s[-1]

    def at(self, s):
        s = max(0.0, min(self.length, s))
        for i in range(len(self.pts) - 1):
            if self.s[i + 1] >= s:
                t = (s - self.s[i]) / max(1e-9, self.s[i + 1] - self.s[i])
                p = self.pts[i].lerp(self.pts[i + 1], t)
                d = (self.pts[i + 1] - self.pts[i]).normalized()
                return p, d
        return self.pts[-1], (self.pts[-1] - self.pts[-2]).normalized()


def sweep(name, path, prof, seg=0.28, closed=False, col=None, mat=None, inside=False,
          scallop=0.0, round_m=1.6, seed=5, z_of_s=None):
    """Sweep a 2D profile [(y, z), ...] along a Path. `scallop` > 0 adds the half-barrel
    drill scars, parallel to the direction of advance, one pattern per round."""
    rng = random.Random(seed)
    s_arc, norms = [0.0], []
    for i in range(1, len(prof)):
        s_arc.append(s_arc[-1] + math.dist(prof[i], prof[i - 1]))
    for i in range(len(prof)):
        a, b = prof[max(0, i - 1)], prof[min(len(prof) - 1, i + 1)]
        t = Vector((b[0] - a[0], b[1] - a[1])).normalized()
        norms.append(Vector((t.y, -t.x)))
    hole = 0.34
    nseg = int(path.length / seg)
    phases = {}
    bm = bmesh.new()
    rings = []
    for j in range(nseg + 1):
        s = path.length * j / nseg
        p, d = path.at(s)
        right = Vector((d.y, -d.x))
        rnd = int(s / round_m)
        ph = phases.setdefault(rnd, rng.random())
        zoff = z_of_s(s) if z_of_s else 0.0
        ring = []
        for i, (py, pz) in enumerate(prof):
            dd = 0.0
            if scallop > 0:
                k = 1.0 - abs(math.sin(math.pi * s_arc[i] / hole + ph * 6.28))
                dd = scallop * k + 0.018 * math.sin(s * 3.1 + s_arc[i] * 2.2 + ph * 9) + rng.uniform(-0.008, 0.008)
            n = norms[i]
            yy = py + n.x * dd
            zz = pz + n.y * dd
            w = p - right * yy
            ring.append(bm.verts.new((w.x, w.y, max(-2.0, zz + zoff) if not closed else zz + zoff)))
        rings.append(ring)
    npts = len(prof)
    for j in range(nseg):
        rng_i = range(npts) if closed else range(npts - 1)
        for i in rng_i:
            i2 = (i + 1) % npts
            bm.faces.new((rings[j][i], rings[j][i2], rings[j + 1][i2], rings[j + 1][i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    o = G._mesh_object(name, bm, col=col, smooth=True)
    if inside:
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.mesh.normals_make_consistent(inside=True)
        bpy.ops.object.mode_set(mode="OBJECT")
    if mat is not None:
        G.set_material(o, mat)
    return o


def drive(path, hw=1.20, leg=1.20, col=None, rock=None, z_of_s=None, gutter=True, rails=True,
          sleepers=True, seed=5):
    """The horseshoe drive 2.4 x 2.4 m along `path`: walls with shot-hole scallops, a flat
    trammed floor with the 300 x 90 mm gutter, rail on sleepers at 600 mm, timber-set
    sockets at 1.2 m, a bolt line at the springing. Rail HEADS are bearing steel: polished
    mirror-bright by use, the only truly specular thing in the cave."""
    col = col or G.new_collection("DRIVE")
    rock = rock or E.rock("drive_rock", albedo_lo=0.035, albedo_hi=0.30, warm=1.0, wet=0.45)
    sweep("drive_walls", path, horseshoe(hw, leg), col=col, mat=rock, inside=True, scallop=0.055, seed=seed, z_of_s=z_of_s)
    # floor: a strip with the gutter cut down the left side
    fl = []
    ny = 26
    for j in range(ny + 1):
        y = -hw + 2 * hw * j / ny
        z = 0.01 * math.sin(y * 7.0)
        if gutter and y < -hw + 0.30:
            z -= 0.09 * math.sin(math.pi * min(1.0, (y + hw) / 0.30)) ** 0.6
        fl.append((y, z))
    sweep("drive_floor", path, fl, seg=0.22, col=col, mat=rock, z_of_s=z_of_s)
    iron = cast_iron("rail_iron", tone=0.9, scale=4.0)
    head = bearing_steel("rail_head", rough=0.16, tint=(0.60, 0.58, 0.55))
    dark = cast_iron("socket_dark", tone=0.6, scale=5.0)
    gauge = 0.60
    if rails:
        for side in (1, -1):
            y0 = 0.10 + side * gauge / 2
            web = [(y0 - 0.02, 0.035), (y0 + 0.02, 0.035), (y0 + 0.02, 0.085), (y0 - 0.02, 0.085)]
            sweep(f"rail{side}", path, web, seg=0.5, closed=True, col=col, mat=iron, z_of_s=z_of_s)
            top = [(y0 - 0.024, 0.085), (y0 + 0.024, 0.085), (y0 + 0.024, 0.097), (y0 - 0.024, 0.097)]
            sweep(f"railhead{side}", path, top, seg=0.5, closed=True, col=col, mat=head, z_of_s=z_of_s)
    if sleepers:
        s = 0.3
        k = 0
        while s < path.length:
            p, d = path.at(s)
            yaw = math.atan2(d.y, d.x)
            zoff = z_of_s(s) if z_of_s else 0.0
            right = Vector((d.y, -d.x))
            c = p - right * 0.10
            o = G.box(f"sleeper.{k}", (0.11, gauge + 0.34, 0.05), (c.x, c.y, 0.025 + zoff), rot=(0, 0, yaw), col=col)
            G.set_material(o, dark)
            s += 0.60
            k += 1
    # sockets at 1.2 m, the bolt line at the springing
    s = 0.6
    k = 0
    while s < path.length:
        p, d = path.at(s)
        yaw = math.atan2(d.y, d.x)
        right = Vector((d.y, -d.x))
        zoff = z_of_s(s) if z_of_s else 0.0
        for side in (1, -1):
            c = p - right * (side * (hw - 0.03))
            o = G.box(f"socket.{k}.{side}", (0.16, 0.10, 0.20), (c.x, c.y, leg + 0.10 + zoff), rot=(0, 0, yaw), col=col)
            G.set_material(o, dark)
            o = G.cyl(f"bolt.{k}.{side}", 0.024, 0.024, 0.06, (c.x, c.y, leg - 0.35 + zoff), rot=(math.pi / 2, 0, yaw), verts=8, col=col)
            G.set_material(o, iron)
        s += 1.2
        k += 1
    return col, rock


def bus(path, col, live=False, z_crown=2.32, spacing=2.4, box_at=None, rock=None):
    """THE BUS: a bare conductor the length of the workings on glazed white porcelain
    insulators at the crown. It never glows. A junction box on the wall is one of the
    prior industry's control surfaces -- a STATION (ART-DIRECTION 6.4)."""
    porc = porcelain()
    cond_m = M.bare_metal("conductor", (0.06, 0.05, 0.045), 0.55)
    iron_d = cast_iron("bus_iron", tone=0.7, scale=4.0)
    pts = []
    s = 0.0
    while s <= path.length:
        p, d = path.at(s)
        pts.append(Vector((p.x, p.y, z_crown - 0.22)))
        s += 0.5
    o = G.tube_along("conductor", pts, 0.011, verts=8, col=col)
    G.set_material(o, cond_m)
    s = 0.8
    k = 0
    while s < path.length:
        p, d = path.at(s)
        yaw = math.atan2(d.y, d.x)
        base = Vector((p.x, p.y, z_crown + 0.05))
        b = G.box(f"ins_bracket.{k}", (0.14, 0.20, 0.06), base, rot=(0, 0, yaw), col=col)
        G.set_material(b, iron_d)
        pin = G.cyl(f"ins_pin.{k}", 0.014, 0.014, 0.16, base + Vector((0, 0, -0.10)), verts=8, col=col)
        G.set_material(pin, iron_d)
        for i, (r, dz) in enumerate(((0.065, -0.10), (0.055, -0.14), (0.045, -0.18))):
            sh = G.cyl(f"ins_shed.{k}.{i}", r, r * 0.8, 0.028, base + Vector((0, 0, dz)), verts=16, col=col)
            G.set_material(sh, porc)
        s += spacing
        k += 1
    if box_at is not None:
        s_box, side = box_at
        p, d = path.at(s_box)
        yaw = math.atan2(d.y, d.x)
        right = Vector((d.y, -d.x))
        c = p - right * (side * (1.20 - 0.12))
        box = G.box("junction_box", (0.42, 0.20, 0.52), (c.x, c.y, 1.25), rot=(0, 0, yaw), bevel=0.01, col=col)
        G.set_material(box, iron_d)
        lid = G.box("junction_lid", (0.34, 0.03, 0.42), (c.x + right.x * side * 0.10, c.y + right.y * side * 0.10, 1.25), rot=(0, 0, yaw), bevel=0.006, col=col)
        G.set_material(lid, cast_iron("lid_iron", tone=0.85, scale=6.0))
        lever = G.segment("junction_lever", Vector((c.x + right.x * side * 0.12, c.y + right.y * side * 0.12, 1.10)),
                          Vector((c.x + right.x * side * 0.30, c.y + right.y * side * 0.30, 1.32)), 0.014, 0.010, verts=8, col=col)
        G.set_material(lever, bearing_steel("lever_steel", rough=0.35))
        cond = G.tube_along("junction_conduit", [Vector((c.x, c.y, 1.52)), Vector((c.x, c.y, z_crown - 0.30)),
                                                  Vector((p.x, p.y, z_crown - 0.24))], 0.02, verts=8, col=col)
        G.set_material(cond, iron_d)
        return Vector((c.x, c.y, 1.25)), yaw
    return None, None


def sump(path, s0, s1, z_water, live=False, corona=0.0, col=None):
    """Standing water in the drive between s0 and s1 along the path."""
    ring = [(-1.3, 0.0), (1.3, 0.0)]
    sub = Path([path.at(s0 + (s1 - s0) * i / 20)[0] for i in range(21)])
    o = sweep("sump", sub, ring, seg=0.5, col=col)
    o.location.z = z_water
    G.set_material(o, water("sump_water", corona_k=2100, corona=corona if live else 0.0))
    return o


# ---------------------------------------------------------------------------------------
# THE HAULAGE
# ---------------------------------------------------------------------------------------
def haulage(path, s_loco, col=None, lamp_k=2400, lamp_w=0.0, tubs=3, ore_in=(1,), rider=None, direction=1):
    """An ore train still hauling on its circuit. The same castings as the Assayer but
    GREASED: bearings wet, the rail heads it runs on mirror-bright. PROPOSED form: a
    water-motor locomotive (a Pelton casing on the side, no chimney) and 1.2 x 0.6 m tubs
    -- one module long, one gauge wide -- so the agent can ride one. It carries one lamp."""
    col = col or G.new_collection("HAULAGE")
    iron = cast_iron("haul_iron", tone=0.95, scale=2.5)
    iron_d = cast_iron("haul_iron_dark", tone=0.65, scale=4.0)
    gr = grease()
    steel = bearing_steel("haul_steel", rough=0.28)
    tread = bearing_steel("haul_tread", rough=0.20, tint=(0.55, 0.53, 0.50))
    out = {"col": col}

    flip = 0.0 if direction > 0 else math.pi

    def place(o, s, dy=0.0, dz=0.0, yaw_extra=0.0):
        p, d = path.at(s)
        yaw = math.atan2(d.y, d.x) + flip
        right = Vector((d.y, -d.x))
        c = p - right * (0.10 + dy)
        o.matrix_world = Matrix.Translation((c.x, c.y, dz)) @ Matrix.Rotation(yaw + yaw_extra, 4, "Z") @ o.matrix_world
        _link(o, col)
        return o

    def wheels(prefix, s, xs, r=0.16):
        for xi, dx in enumerate(xs):
            for side in (1, -1):
                w = G.cyl(f"{prefix}_wheel{xi}{side}", r, r, 0.06, (dx, side * 0.30, r), rot=(math.pi / 2, 0, 0), verts=24)
                G.set_material(w, tread)
                place(w, s)
                f = G.cyl(f"{prefix}_flange{xi}{side}", r + 0.025, r + 0.025, 0.012, (dx, side * 0.335, r), rot=(math.pi / 2, 0, 0), verts=24)
                G.set_material(f, iron_d)
                place(f, s)
                ab = G.box(f"{prefix}_axlebox{xi}{side}", (0.14, 0.08, 0.12), (dx, side * 0.36, r + 0.06), bevel=0.006)
                G.set_material(ab, gr)
                place(ab, s)
            ax = G.cyl(f"{prefix}_axle{xi}", 0.03, 0.03, 0.74, (dx, 0, r), rot=(math.pi / 2, 0, 0), verts=10)
            G.set_material(ax, steel)
            place(ax, s)

    # ---- locomotive --------------------------------------------------------------------
    s = s_loco
    frame = G.box("loco_frame", (1.40, 0.62, 0.16), (0, 0, 0.36), bevel=0.01)
    G.set_material(frame, iron)
    place(frame, s)
    body = G.box("loco_body", (1.00, 0.54, 0.34), (-0.10, 0, 0.61), bevel=0.02)
    G.set_material(body, iron)
    place(body, s)
    drum = G.cyl("loco_drum", 0.22, 0.22, 0.90, (0.05, 0, 0.90), rot=(0, math.pi / 2, 0), verts=22, bevel=0.01)
    G.set_material(drum, iron)
    place(drum, s)
    for x in (-0.25, 0.05, 0.35):
        bd = G.torus(f"loco_band{int(x * 100)}", 0.225, 0.015, (x, 0, 0.90), rot=(0, math.pi / 2, 0))
        G.set_material(bd, iron_d)
        place(bd, s)
    pel = G.cyl("loco_pelton", 0.30, 0.30, 0.14, (-0.15, -0.36, 0.72), rot=(math.pi / 2, 0, 0), verts=28, bevel=0.01)
    G.set_material(pel, iron_d)
    place(pel, s)
    hub = G.cyl("loco_pelton_hub", 0.08, 0.08, 0.05, (-0.15, -0.45, 0.72), rot=(math.pi / 2, 0, 0), verts=16)
    G.set_material(hub, steel)
    place(hub, s)
    inlet = G.tube_along("loco_inlet", [Vector((-0.15, -0.36, 1.0)), Vector((-0.15, -0.36, 1.12)), Vector((0.3, -0.05, 1.13))], 0.035, verts=8)
    G.set_material(inlet, iron_d)
    place(inlet, s)
    buf = G.box("loco_buffer", (0.10, 0.30, 0.10), (0.75, 0, 0.36))
    G.set_material(buf, iron_d)
    place(buf, s)
    wheels("loco", s, (0.42, -0.42), r=0.17)
    # its lamp: a cast housing on the nose, one glass, a warm source inside
    lp = G.cyl("loco_lamp", 0.10, 0.11, 0.14, (0.62, 0, 0.72), rot=(0, math.pi / 2, 0), verts=16)
    G.set_material(lp, iron_d)
    place(lp, s)
    glass = G.cyl("loco_lamp_glass", 0.085, 0.085, 0.012, (0.70, 0, 0.72), rot=(0, math.pi / 2, 0), verts=16)
    G.set_material(glass, hot("loco_lamp_hot", lamp_k, 12.0 if lamp_w > 0 else 0.0) if lamp_w > 0 else M.bare_metal("dead_glass", (0.02, 0.03, 0.04), 0.08))
    place(glass, s)
    p, d = path.at(s)
    d = d * direction
    right = Vector((d.y, -d.x)) * direction
    c = p - right * 0.10
    out["lamp_pos"] = Vector((c.x + d.x * 0.72, c.y + d.y * 0.72, 0.72))
    out["lamp_dir"] = Vector((d.x, d.y, -0.12))
    if lamp_w > 0:
        E.add_light("HAUL_LAMP", "SPOT", out["lamp_pos"], lamp_w, blackbody(lamp_k), size=0.08, spot_deg=62, blend=0.6,
                    aim=out["lamp_pos"] + out["lamp_dir"] * 6.0)
    # ---- tubs --------------------------------------------------------------------------
    out["tubs"] = []
    for t in range(tubs):
        st = s - direction * (1.55 + t * 1.45)
        pfx = f"tub{t}"
        up = G.box(f"{pfx}_body", (1.20, 0.64, 0.30), (0, 0, 0.62), bevel=0.02)
        G.set_material(up, iron)
        place(up, st)
        lo = G.box(f"{pfx}_hopper", (1.00, 0.44, 0.24), (0, 0, 0.36), bevel=0.02)
        G.set_material(lo, iron_d)
        place(lo, st)
        for x in (-0.5, 0.5):
            e = G.box(f"{pfx}_end{int(x * 10)}", (0.04, 0.68, 0.34), (x, 0, 0.62))
            G.set_material(e, iron_d)
            place(e, st)
        wheels(pfx, st, (0.38, -0.38), r=0.13)
        cp = G.segment(f"{pfx}_coupling", Vector((0.60, 0, 0.36)), Vector((0.88, 0, 0.36)), 0.02, 0.02, verts=8)
        G.set_material(cp, steel)
        place(cp, st)
        p, d = path.at(st)
        right = Vector((d.y, -d.x))
        c = p - right * 0.10
        out["tubs"].append((Vector((c.x, c.y, 0.77)), math.atan2(d.y, d.x) + flip))
        if t in ore_in:
            rng = random.Random(20 + t)
            for i in range(14):
                r = rng.uniform(0.05, 0.12)
                bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=r, location=(rng.uniform(-0.45, 0.45), rng.uniform(-0.2, 0.2), 0.74 + rng.uniform(0, 0.08)))
                o = bpy.context.object
                o.name = f"{pfx}_ore{i}"
                o.scale = (rng.uniform(0.7, 1.4), rng.uniform(0.7, 1.4), rng.uniform(0.5, 0.9))
                o.rotation_euler = (rng.uniform(0, 3), rng.uniform(0, 3), rng.uniform(0, 3))
                G.set_material(o, E.rock("ore_rock", albedo_lo=0.05, albedo_hi=0.22, warm=1.4, wet=0.6))
                place(o, st)
    return out


# ---------------------------------------------------------------------------------------
# beacons
# ---------------------------------------------------------------------------------------
def beacon(at, name="beacon", pilot=True, tilt=0.0):
    """230 x 60 mm cast tube, self-righting weighted base, one warm pilot at the top
    (WARM_DIM, never team-coloured), a retroreflective band. A spoofed one is identical."""
    col = G.new_collection(name)
    iron = cast_iron(name + "_iron", tone=0.9, scale=8.0)
    steel = bearing_steel(name + "_band", rough=0.25, tint=(0.62, 0.60, 0.56))
    at = Vector(at)
    parts = [G.cyl(name + "_tube", 0.030, 0.030, 0.19, (0, 0, 0.135), verts=16, bevel=0.004),
             G.cyl(name + "_base", 0.045, 0.030, 0.045, (0, 0, 0.0225), verts=16, bevel=0.004),
             G.cyl(name + "_cap", 0.028, 0.020, 0.02, (0, 0, 0.24), verts=16)]
    for o in parts:
        G.set_material(o, iron)
    band = G.cyl(name + "_retro", 0.031, 0.031, 0.025, (0, 0, 0.19), verts=16)
    G.set_material(band, steel)
    pil = G.sphere(name + "_pilot", 0.009, (0, 0, 0.252), seg=10)
    G.set_material(pil, emissive_rgb(name + "_pilot_m", WARM_DIM, 6.0 if pilot else 0.0))
    for o in parts + [band, pil]:
        o.matrix_world = Matrix.Translation(at) @ Matrix.Rotation(tilt, 4, "Y") @ o.matrix_world
        _link(o, col)
    return col


# ---------------------------------------------------------------------------------------
# the visiting machine
# ---------------------------------------------------------------------------------------
def surveyor(at=(0, 0, 0), yaw_deg=0.0, move="stand 0.5", lamp=600.0, lamp_down=10.0, look=None,
             quiet_sonar=True, wear=0.45, name="AGENT"):
    """A Surveyor dressed for the direction: pale shell over graphite, BONE emissives at
    strength 3, WHITE lamp re-aimed +X and tilted down (the build.py:312 fix, applied in
    the probe), sonar bar dark because it is not pinging."""
    skin = P.Skin(name, base=PALE_SHELL, chassis=GRAPHITE, accent=(0.55, 0.35, 0.12), light=BONE,
                  light_strength=3.0, wear=wear, grime=0.5)
    cfg = P.default_config("surveyor")
    cfg.skin = skin
    built = build_agent(cfg, name=name, at=at)
    yaw = math.radians(yaw_deg)
    R = Matrix.Rotation(yaw, 4, "Z")
    at = Vector(at)
    built.arm.rotation_euler = Euler((0, 0, yaw))
    for e in built.feet:
        e.location = at + R @ (Vector(e.location) - at)
    built.look.location = at + R @ (Vector(built.look.location) - at)
    mv = Mover(built)
    if look is not None:
        mv.look_at(look, over=0.3)
    last = script(mv, move)
    if built.lamp is not None:
        built.lamp.rotation_euler = Euler((0, -math.pi / 2 + math.radians(lamp_down), 0))
        built.lamp.data.energy = lamp
        built.lamp.data.color = LAMP_WHITE
        built.lamp.data.spot_size = math.radians(50)
        built.lamp.data.shadow_soft_size = 0.04
    for m in bpy.data.materials:
        if not m.use_nodes:
            continue
        if m.name.startswith("light_strip") or m.name.startswith("eye"):
            for nd in m.node_tree.nodes:
                if nd.type == "EMISSION":
                    nd.inputs["Strength"].default_value = 3.0
                    nd.inputs["Color"].default_value = (*BONE, 1)
    if quiet_sonar:
        # the sonar elements share the strip material; give them their own, dark
        dark = M.bare_metal("sonar_dark", (0.06, 0.06, 0.065), 0.4)
        for o in bpy.data.objects:
            if "_sonar_el" in o.name:
                G.set_material(o, dark)
    bpy.context.scene.frame_set(last)
    return built, mv, last


def download_pose(built, mv, last, pitch_deg=24.0, drop=0.16, ahead=0.42):
    """THE-MACHINERY 6: 'it walks up, stops, and puts its transducer on the rock -- sensor
    head down, hard against the floor -- and holds still.' Body lowered and pitched nose
    down, tilt limit relaxed, look target on the floor ahead of the head. Lamp off: it is
    listening, and nothing on it glows but its running lights."""
    arm = built.arm
    sc = bpy.context.scene
    sc.frame_set(last)
    yaw = arm.rotation_euler.z
    fwd = Vector((math.cos(yaw), math.sin(yaw), 0))
    for pb in arm.pose.bones["tilt"].constraints:
        if pb.type == "LIMIT_ROTATION":
            pb.min_x, pb.max_x = -1.5, 1.5
    arm.location = Vector(arm.location) - Vector((0, 0, drop)) + fwd * 0.02
    arm.rotation_euler = Euler((0, math.radians(pitch_deg), yaw))
    arm.keyframe_insert("location", frame=last)
    arm.keyframe_insert("rotation_euler", frame=last)
    look = Vector(arm.location) + fwd * ahead + Vector((0, 0, -0.30))
    built.look.location = look
    built.look.keyframe_insert("location", frame=last)
    if built.lamp is not None:
        built.lamp.data.energy = 0.0
    sc.frame_set(last)
    bpy.context.view_layer.update()


# ---------------------------------------------------------------------------------------
# rigs and camera
# ---------------------------------------------------------------------------------------
def world_grey(strength=1.0, grey=0.30, fog=0.0):
    w = bpy.context.scene.world or bpy.data.worlds.new("World")
    bpy.context.scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.inputs["Color"].default_value = (grey, grey, grey, 1)
    bg.inputs["Strength"].default_value = strength
    nt.links.new(bg.outputs[0], out.inputs["Surface"])
    if fog > 0:
        vol = nt.nodes.new("ShaderNodeVolumeScatter")
        vol.inputs["Density"].default_value = fog
        vol.inputs["Anisotropy"].default_value = 0.55
        nt.links.new(vol.outputs[0], out.inputs["Volume"])


def rig_clear(target, dist, az_deg=-40, el_deg=45, ground=True, ground_size=60, key_scale=1.0):
    """CLEAR: grey world at 1.0, one soft area key 45 deg high whose power scales with the
    square of its distance so every studio frame sits at the same exposure, a grey ground
    ruled at the 1.2 m module. Not the game."""
    world_grey(1.0, 0.30)
    t = Vector(target)
    a, e = math.radians(az_deg), math.radians(el_deg)
    loc = t + Vector((math.cos(a) * math.cos(e), math.sin(a) * math.cos(e), math.sin(e))) * dist
    E.add_light("KEY", "AREA", loc, 110.0 * (dist / 2.5) ** 2 * key_scale, (1.0, 0.97, 0.93), size=max(2.0, 0.45 * dist), aim=t)
    if ground:
        g = G.plane("clear_ground", ground_size, (0, 0, -0.002))
        G.set_material(g, grey_ground())


def rig_interior(points, energy=180.0, size=1.6, colour=(1.0, 0.97, 0.93)):
    """CLEAR for an enclosed drive: neutral area lights hung at the crown. A studio
    inside a tunnel, so the furniture can be seen. Not the game."""
    world_grey(0.0, 0.0)
    for i, p in enumerate(points):
        E.add_light(f"CROWN{i}", "AREA", p, energy, colour, size=size, aim=(p[0], p[1], 0.0))


def rig_insitu(fog=0.012):
    E.world(fog=fog, ambient=0.0)


def hot_points(kelvin, winch_w, at=(0, 0, 0), winch_pos=None, anvil_z=1.10):
    """The two hot points (ART-DIRECTION 5.4): the winch head is a BEACON, seen from the
    next chamber and lighting little floor; the anvil block at the foot is a third the
    output and lights the ground the agents stand on."""
    rgb = blackbody(kelvin)
    at = Vector(at)
    wp = winch_pos if winch_pos is not None else at + Vector((0.85, 0, 5.98))
    E.add_light("WINCH", "POINT", wp + Vector((0.32, 0, 0)), winch_w, rgb, size=0.30)
    for k in range(3):
        a = math.radians(120 * k + 30)
        E.add_light(f"ANVIL{k}", "POINT", at + Vector((math.cos(a) * 0.95, math.sin(a) * 0.95, anvil_z + 0.12)), winch_w / 9.0, rgb, size=0.45)


def camera(loc, target, focal=40.0, ortho=None, clip_start=0.05, dof=None, res=None):
    cd = bpy.data.cameras.new("CAM")
    cd.lens = focal
    cd.clip_start = clip_start
    cd.clip_end = 400
    if ortho is not None:
        cd.type = "ORTHO"
        cd.ortho_scale = ortho
    cam = bpy.data.objects.new("CAM", cd)
    bpy.context.scene.collection.objects.link(cam)
    cam.location = Vector(loc)
    t = bpy.data.objects.new("CAM_aim", None)
    bpy.context.scene.collection.objects.link(t)
    t.location = Vector(target)
    c = cam.constraints.new("TRACK_TO")
    c.track_axis = "TRACK_NEGATIVE_Z"
    c.up_axis = "UP_Y"
    c.target = t
    if dof:
        cd.dof.use_dof = True
        cd.dof.aperture_fstop = dof
        cd.dof.focus_object = t
    bpy.context.scene.camera = cam
    return cam


# ---------------------------------------------------------------------------------------
# shots
# ---------------------------------------------------------------------------------------
ap = argparse.ArgumentParser()
ap.add_argument("--shot", default=None)
ap.add_argument("--out", default=None)
ap.add_argument("--samples", type=int, default=40)
ap.add_argument("--res", default=None, help="WxH; each shot has its own default")
ap.add_argument("--exposure", type=float, default=None)
ap.add_argument("--list", action="store_true")
ap.add_argument("--quick", action="store_true", help="8 spp at half size, for framing")
A = ap.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:])

SHOTS = {}


def shot(name, res=(960, 600), look="AgX - Medium High Contrast", exposure=0.0):
    def deco(fn):
        SHOTS[name] = (fn, res, look, exposure)
        return fn
    return deco


CLEAR = "AgX - Base Contrast"


def click(n):
    """Colour temperature and relative output at ratchet click n of 9 (0 = dormant)."""
    if n <= 0:
        return None, 0.0
    return 1900 + (2400 - 1900) * n / 9.0, n / 9.0


# The visiting machine is built FIRST in every shot: build_agent settles its IK pole angles
# with ~100 depsgraph updates, and each one re-evaluates every modifier in the scene.

# ---- C1: dormant ---------------------------------------------------------------------------
@shot("dormant_elevation", res=(960, 1200), look=CLEAR)
def _():
    surveyor(at=(1.9, -1.2, 0), yaw_deg=150, lamp=0.0, look=(0.2, 0.0, 0.9))
    assayer(aim_deg=35, hammer_frac=0.0)
    rig_clear((0, 0, 3.3), 14)
    camera((7.5, -10.5, 3.6), (0.1, -0.2, 3.25), focal=42)


@shot("dormant_plan", res=(960, 960), look=CLEAR)
def _():
    surveyor(at=(1.9, -1.2, 0), yaw_deg=150, lamp=0.0)
    assayer(aim_deg=35, hammer_frac=0.0)
    rig_clear((0, 0, 0), 12, el_deg=60)
    camera((0.001, 0, 40), (0, 0, 0), ortho=11.5)


@shot("dormant_footing", look=CLEAR)
def _():
    surveyor(at=(1.6, -1.5, 0), yaw_deg=140, lamp=0.0, look=(0.2, 0.0, 0.9))
    assayer(aim_deg=35, hammer_frac=0.0)
    rig_clear((0, 0, 0.8), 6, el_deg=40)
    camera((2.9, -3.3, 1.35), (0.15, -0.35, 0.75), focal=42)


@shot("dormant_bearing", look=CLEAR)
def _():
    assayer(aim_deg=35, hammer_frac=0.0)
    rig_clear((0, 0, 5.5), 7, el_deg=35)
    camera((3.4, -4.0, 6.4), (0.3, 0.2, 5.5), focal=45)


@shot("dormant_tank", look=CLEAR)
def _():
    assayer(aim_deg=35, hammer_frac=0.0)
    rig_clear((0, -0.9, 3.0), 6, az_deg=-110, el_deg=40)
    camera((3.3, -4.3, 3.2), (0.2, -0.9, 3.0), focal=45)


@shot("dormant_insitu_lamp", res=(1200, 750), exposure=0.7)
def _():
    # the visitor 4.5 m off the footing, lamp 1000 W (power and exposure are the same knob:
    # ART-DIRECTION 2.2), the camera low behind it so its silhouette lands on its own pool
    surveyor(at=(4.8, -2.0, 0), yaw_deg=158, lamp=1000, lamp_down=0.0, look=(0.0, 0.0, 2.4))
    chamber()
    assayer(aim_deg=35, hammer_frac=0.0)
    rig_insitu(0.012)
    clear_near((6.6, -3.3, 0.7), 1.8)
    camera((6.6, -3.3, 0.7), (0.4, -0.3, 2.3), focal=30)


@shot("dormant_insitu_drip")
def _():
    surveyor(at=(2.7, -2.1, 0), yaw_deg=140, lamp=600, lamp_down=6.0, look=(0.3, -0.5, 1.05))
    chamber()
    assayer(aim_deg=35, hammer_frac=0.0)
    rig_insitu(0.010)
    clear_near((2.1, -2.9, 0.75), 1.2)
    camera((2.1, -2.9, 0.75), (0.25, -0.55, 1.05), focal=50, dof=4.0)


# ---- C2: winding ---------------------------------------------------------------------------
def _wind_clear(n, aim=35):
    k, s = click(n)
    assayer(aim_deg=aim, hammer_frac=n / 9.0, tank_fill=1.0 - n / 9.0 * 0.9, hot_k=k, hot_s=10.0 * s)
    rig_clear((0, 0, 3.3), 14)
    if s > 0:
        hot_points(k, 900.0 * s)


@shot("wind_click6_clear", res=(1400, 900), look=CLEAR)
def _():
    surveyor(at=(2.6, -1.4, 0), yaw_deg=150, lamp=0.0, look=(0.2, 0.0, 0.9))
    _wind_clear(6)
    camera((9.0, -9.5, 3.2), (0.2, -0.3, 3.2), focal=36)


for _n in (1, 5, 9):
    def _mk(n):
        @shot(f"wind_click{n}_clear", res=(800, 1200), look=CLEAR)
        def _():
            _wind_clear(n)
            camera((7.0, -10.0, 3.4), (0.1, -0.2, 3.25), focal=42)
    _mk(_n)


def _wind_insitu(n, aim=35):
    k, s = click(n)
    chamber()
    assayer(aim_deg=aim, hammer_frac=n / 9.0, tank_fill=1.0 - n / 9.0 * 0.9, hot_k=k, hot_s=14.0 * s)
    rig_insitu(0.011)
    if s > 0:
        hot_points(k, 1100.0 * s)


for _n in (1, 5, 9):
    def _mk2(n):
        @shot(f"wind_click{n}_insitu", res=(800, 1200))
        def _():
            surveyor(at=(4.6, -1.3, 0), yaw_deg=165, lamp=0.0, look=(0.0, 0.0, 1.2))
            _wind_insitu(n)
            clear_near((7.2, -3.4, 0.7), 1.6)
            camera((7.2, -3.4, 0.7), (0.0, 0.0, 3.0), focal=26)
    _mk2(_n)


@shot("wind_insitu_wide", res=(1200, 750))
def _():
    surveyor(at=(4.6, -1.3, 0), yaw_deg=165, lamp=0.0, look=(0.0, 0.0, 1.2))
    _wind_insitu(8)
    clear_near((7.2, -4.2, 0.85), 1.6)
    camera((7.2, -4.2, 0.85), (0.0, 0.0, 2.9), focal=28)


@shot("wind_next_chamber", res=(960, 600))
def _():
    surveyor(at=(6.0, -3.2, 0), yaw_deg=150, lamp=0.0, look=(3.0, -1.8, 1.0))
    _wind_insitu(9)
    # a rock buttress on the line from the camera to the mast: the mast and both hot points
    # are hidden, the light on the far walls and the crown is not. Vertical landmark
    # presence is bought with light, not with geometry.
    wall = E.rock("buttress_rock", albedo_lo=0.035, albedo_hi=0.30, warm=1.0, wet=0.4)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=4, radius=1.4, location=(4.2, -2.5, 1.4))
    o = bpy.context.object
    o.name = "buttress"
    o.scale = (1.0, 1.1, 2.9)
    E._displace(o, 1.2, 0.5, depth=5)
    o.data.shade_smooth()
    G.set_material(o, wall)
    clear_near((7.6, -4.6, 0.9), 1.6)
    camera((7.6, -4.6, 0.9), (0.0, 0.0, 3.2), focal=24)


# ---- C3: firing ------------------------------------------------------------------------------
@shot("fire_strike_clear", res=(1400, 900), look=CLEAR)
def _():
    surveyor(at=(3.2, -1.6, 0), yaw_deg=150, lamp=0.0, look=(0.2, 0.0, 0.9))
    assayer(aim_deg=35, hammer_frac=0.0, tank_fill=0.1, hot_k=4000, hot_s=40.0, drip=False)
    dust_ring()
    hot_points(4000, 3600.0)
    rig_clear((0, 0, 3.3), 14)
    camera((9.0, -9.5, 3.2), (0.2, -0.3, 3.2), focal=36)


def _on_axis(aim, r):
    a = math.radians(aim)
    return a, Vector((math.cos(a) * r, math.sin(a) * r, 0))


@shot("fire_strike_machine_height", res=(1200, 750))
def _():
    aim = 35
    a, p = _on_axis(aim, 5.4)
    surveyor(at=(p.x, p.y, 0), yaw_deg=aim + 180, lamp=0.0, look=(0, 0, 1.2))
    chamber()
    assayer(aim_deg=aim, hammer_frac=0.0, tank_fill=0.1, hot_k=4000, hot_s=60.0, drip=False)
    dust_ring()
    hot_points(4000, 4400.0)
    rig_insitu(0.012)
    back = p + Vector((math.cos(a) * 2.4, math.sin(a) * 2.4, 0.62)) + Vector((-math.sin(a) * 0.9, math.cos(a) * 0.9, 0))
    clear_near(back, 1.6)
    camera(back, (0, 0, 2.6), focal=28)


@shot("fire_decay_2s", res=(1200, 750))
def _():
    aim = 35
    a, p = _on_axis(aim, 5.4)
    surveyor(at=(p.x, p.y, 0), yaw_deg=aim + 180, lamp=600, lamp_down=10, look=(0, 0, 0.6))
    chamber()
    assayer(aim_deg=aim, hammer_frac=0.0, tank_fill=0.1, hot_k=2400, hot_s=4.0, drip=False)
    lobe_decal(aim)
    hot_points(2400, 420.0)
    rig_insitu(0.012)
    back = p + Vector((math.cos(a) * 2.4, math.sin(a) * 2.4, 0.62)) + Vector((-math.sin(a) * 0.9, math.cos(a) * 0.9, 0))
    clear_near(back, 1.6)
    camera(back, (0, 0, 1.8), focal=28)


@shot("fire_strike_wide", res=(1200, 750))
def _():
    surveyor(at=(5.0, -3.6, 0), yaw_deg=145, lamp=0.0, look=(0, 0, 1.2))
    chamber()
    assayer(aim_deg=35, hammer_frac=0.0, tank_fill=0.1, hot_k=4000, hot_s=60.0, drip=False)
    dust_ring()
    hot_points(4000, 4400.0)
    rig_insitu(0.012)
    clear_near((-7.8, -3.0, 0.9), 1.6)
    camera((-7.8, -3.0, 0.9), (0.2, 0.1, 3.0), focal=30)


# ---- C4: the scour --------------------------------------------------------------------------
@shot("scour_topdown", res=(960, 960), look=CLEAR)
def _():
    surveyor(at=(4.2, 3.0, 0), yaw_deg=-120, lamp=0.0)
    chamber()
    assayer(aim_deg=35, hammer_frac=0.0)
    # the chamber roof would hide a plan view: lift the camera INSIDE and light from within
    world_grey(0.0, 0.0)
    E.add_light("TOP", "AREA", (0, 0, 8.9), 4200.0, (1.0, 0.97, 0.93), size=8.0, aim=(0, 0, 0))
    E.add_light("SIDE", "AREA", (6, -5, 6.0), 1200.0, (1.0, 0.97, 0.93), size=4.0, aim=(0, 0, 0))
    camera((0.001, 0, 8.6), (0, 0, 0), ortho=15.0, clip_start=0.1)


@shot("scour_oblique", res=(1400, 800), look=CLEAR)
def _():
    surveyor(at=(5.9, 1.4, 0), yaw_deg=-160, lamp=0.0, look=(2.0, 0.5, 0.4))
    chamber()
    assayer(aim_deg=35, hammer_frac=0.0)
    world_grey(0.0, 0.0)
    E.add_light("TOP", "AREA", (2, 2, 8.8), 4200.0, (1.0, 0.97, 0.93), size=8.0, aim=(2, 1, 0))
    E.add_light("RAKE", "AREA", (8, -4, 2.2), 900.0, (1.0, 0.97, 0.93), size=3.0, aim=(4, 0, 0))
    clear_near((8.0, -3.4, 1.6), 1.6)
    camera((8.0, -3.4, 1.6), (3.0, 0.4, 0.4), focal=35)


@shot("scour_insitu_lamp", res=(1400, 800))
def _():
    surveyor(at=(7.6, 0.6, 0), yaw_deg=185, lamp=600, lamp_down=12, look=(3.5, 0.2, 0.0))
    chamber()
    assayer(aim_deg=35, hammer_frac=0.0)
    rig_insitu(0.011)
    clear_near((8.3, -1.0, 0.8), 1.6)
    camera((8.3, -1.0, 0.8), (3.5, 0.3, 0.3), focal=32)


# ---- C5: three ages of iron -----------------------------------------------------------------
def _bracket(name, at, mat):
    """A cast knee bracket: two flats, a fillet web, a boss with a bolt hole, a parting
    line and a raised number. The casting language on one part."""
    at = Vector(at)
    objs = [G.box(name + "_base", (0.60, 0.40, 0.06), at + Vector((0, 0, 0.03)), bevel=0.008),
            G.box(name + "_upright", (0.06, 0.40, 0.50), at + Vector((-0.27, 0, 0.28)), bevel=0.008),
            G.strut(name + "_web", at + Vector((-0.24, 0, 0.50)), at + Vector((0.27, 0, 0.06)), 0.05, 0.04, 0.05, 0.04, bevel=0.004),
            G.cyl(name + "_boss", 0.07, 0.065, 0.10, at + Vector((0.12, 0.10, 0.08)), verts=16, bevel=0.005),
            G.cyl(name + "_parting", 0.30, 0.30, 0.004, at + Vector((-0.27, 0, 0.28)), rot=(0, math.pi / 2, 0), verts=4)]
    for o in objs:
        G.set_material(o, mat)
    return objs


@shot("iron_three_ages", res=(1500, 640), look=CLEAR)
def _():
    cast = cast_iron("cast_a")
    steel = bearing_steel("steel_b")
    graph = graphitised("graph_c")
    _bracket("cast", (-1.1, 0, 0), cast)
    _bracket("steel", (0.0, 0, 0), steel)
    _bracket("graph", (1.1, 0, 0), graph)
    for i, (nm, mat) in enumerate((("cast", cast), ("steel", steel), ("graph", graph))):
        G.set_material(G.sphere(f"{nm}_sphere", 0.16, ((i - 1) * 1.1, 0.42, 0.16)), mat)
    rig_clear((0, 0.1, 0.25), 3.0, az_deg=-60, el_deg=50)
    camera((0.0, -3.1, 1.55), (0, 0.15, 0.25), focal=36, dof=8.0)


@shot("iron_casting_macro", res=(1200, 800), look=CLEAR)
def _():
    assayer(aim_deg=35, hammer_frac=0.0)
    rig_clear((0.6, -0.4, 0.8), 3.0, az_deg=-70, el_deg=35)
    camera((1.9, -1.3, 1.05), (0.62, -0.42, 0.80), focal=60, dof=5.6)


@shot("iron_bearing_shine")
def _():
    surveyor(at=(3.4, -2.2, 0), yaw_deg=150, lamp=600, lamp_down=-38.0, look=(0.0, 0.0, 5.4))
    chamber()
    assayer(aim_deg=35, hammer_frac=0.0)
    rig_insitu(0.011)
    clear_near((3.9, -3.5, 0.55), 1.2)
    camera((3.9, -3.5, 0.55), (0.1, 0.0, 5.3), focal=35)


@shot("iron_waterline", res=(1200, 750), look=CLEAR)
def _():
    wl = 0.42
    iron = cast_iron("wl_iron", waterline=wl)
    top = Vector((0.4, 0, 1.55))
    foot = Vector((-0.9, 0, 0.10))
    G.set_material(G.strut("wl_leg", top, foot, 0.22, 0.30, 0.26, 0.18, bevel=0.012), iron)
    G.set_material(G.box("wl_pad", (0.50, 0.50, 0.12), (foot.x, foot.y, 0.06), bevel=0.012), iron)
    G.set_material(G.cyl("wl_hub", 0.5, 0.46, 0.5, (0.75, 0, 1.6), rot=(0, 0, math.radians(30)), verts=6, bevel=0.015), iron)
    for k in range(4):
        a = k * math.pi / 2 + math.pi / 4
        G.set_material(G.cyl(f"wl_bolt{k}", 0.032, 0.032, 0.08, (foot.x + math.cos(a) * 0.19, foot.y + math.sin(a) * 0.19, 0.14), verts=8), bearing_steel("wl_bolt", rough=0.42, tint=(0.36, 0.34, 0.32)))
    rock = E.rock("wl_rock", albedo_lo=0.035, albedo_hi=0.30, warm=1.0, wet=0.4, waterline=wl)
    fl = G.plane("wl_floor", 14, (0, 0, 0), subdiv=40)
    E._displace(fl, 0.7, 0.12, depth=5, mid=0.55)
    fl.data.shade_smooth()
    G.set_material(fl, rock)
    w = G.plane("wl_water", 14, (0, 0, wl))
    G.set_material(w, water("wl_water"))
    world_grey(1.0, 0.30)
    E.add_light("KEY", "AREA", (2.5, -3.5, 3.2), 520.0, (1.0, 0.97, 0.93), size=2.4, aim=(-0.2, 0, 0.7))
    camera((1.5, -2.4, 1.9), (-0.3, 0.0, 0.45), focal=42, dof=5.6)


# ---- C6: the Haulage ------------------------------------------------------------------------
def _rails_only():
    """Rails and sleepers on the studio floor: the drive without its rock."""
    path = Path([Vector((-6, 0)), Vector((6, 0))])
    col = G.new_collection("RAILS")
    drive(path, col=col, rock=grey_ground("gg"), rails=True, sleepers=True)
    bpy.data.objects.remove(bpy.data.objects["drive_walls"], do_unlink=True)
    bpy.data.objects.remove(bpy.data.objects["drive_floor"], do_unlink=True)
    for o in list(bpy.data.objects):
        if o.name.startswith("socket.") or o.name.startswith("bolt."):
            bpy.data.objects.remove(o, do_unlink=True)
    return path


@shot("haulage_side_elevation", res=(1600, 560), look=CLEAR)
def _():
    surveyor(at=(4.6, -1.05, 0), yaw_deg=0, lamp=0.0)
    path = _rails_only()
    haulage(path, s_loco=9.0, lamp_w=0.0)
    rig_clear((1.0, 0, 0.5), 8, az_deg=-90, el_deg=42)
    camera((1.0, -14.0, 0.75), (1.0, 0, 0.55), ortho=8.2)


@shot("haulage_threequarter", res=(1400, 850), look=CLEAR)
def _():
    surveyor(at=(4.5, -1.1, 0), yaw_deg=25, lamp=0.0, look=(3.2, 0.2, 0.6))
    path = _rails_only()
    haulage(path, s_loco=9.0, lamp_w=0.0)
    rig_clear((1.5, 0, 0.5), 7, az_deg=-60, el_deg=42)
    camera((6.8, -5.2, 2.0), (1.2, 0.0, 0.5), focal=40)


@shot("haulage_bearing_detail", res=(1200, 800), look=CLEAR)
def _():
    path = _rails_only()
    haulage(path, s_loco=9.0, lamp_w=0.0)
    rig_clear((3.4, -0.3, 0.2), 2.4, az_deg=-50, el_deg=40)
    camera((4.2, -1.35, 0.42), (3.42, -0.26, 0.20), focal=60, dof=5.6)


def _curve_scene():
    path = Path(make_path())
    col, rock = drive(path, col=G.new_collection("DRIVE"))
    return path, col, rock


@shot("haulage_round_the_curve", res=(1200, 750))
def _():
    # the train is coming TOWARD the camera round the bend: its lamp arrives before it does
    path, col, rock = _curve_scene()
    rig_insitu(0.016)
    haulage(path, s_loco=path.length - 8.5, lamp_w=900.0, lamp_k=2400, direction=-1)
    p, d = path.at(4.5)
    q = path.at(12.0)[0]
    camera((p.x, p.y - 0.62, 0.62), (q.x, q.y, 0.75), focal=32)


@shot("haulage_riding", res=(1200, 750))
def _():
    path = Path(make_path())
    s_loco = path.length - 5.5
    st = s_loco - 3.0                      # the second tub
    p, d = path.at(st)
    right = Vector((d.y, -d.x))
    tp = p - right * 0.10
    surveyor(at=(tp.x, tp.y, 0.62), yaw_deg=math.degrees(math.atan2(d.y, d.x)), lamp=0.0, move="stand 0.3")
    col, rock = drive(path, col=G.new_collection("DRIVE"))
    rig_insitu(0.014)
    haulage(path, s_loco=s_loco, lamp_w=900.0, lamp_k=2400, ore_in=(0, 2))
    p2, d2 = path.at(path.length - 8.6)
    right2 = Vector((d2.y, -d2.x))
    c = p2 - right2 * 0.10 - right2 * 0.95
    camera((c.x - d2.x * 1.6, c.y - d2.y * 1.6, 0.95), (tp.x, tp.y, 0.80), focal=35)


@shot("rails_return_lamp", res=(1200, 750))
def _():
    path = Path(make_path())
    p, d = path.at(4.0)
    surveyor(at=(p.x, p.y, 0), yaw_deg=0, lamp=600, lamp_down=9, look=(p.x + 5.0, 0.0, 0.05))
    drive(path, col=G.new_collection("DRIVE"))
    rig_insitu(0.012)
    camera((p.x - 1.9, p.y - 0.35, 0.36), (p.x + 6.0, 0.6, 0.1), focal=38)


# ---- C7: the Bus, live -----------------------------------------------------------------------
def _sump_scene(live, corona=0.6, waterline=0.0):
    path = Path([Vector((-4, 0)), Vector((18, 0))])

    def z_of_s(s):
        x = s - 4.0
        return 0.0 if x < 2.0 else -min(0.55, (x - 2.0) * 0.14)

    col, rock = drive(path, col=G.new_collection("DRIVE"), z_of_s=z_of_s)
    box_pos, box_yaw = bus(path, col, live=live, box_at=(2.2, 1))
    sump(path, 5.2, 22.0, waterline - 0.02, live=live, corona=corona, col=col)
    return path, col, rock, box_pos


@shot("bus_dead_clear", res=(960, 720), look=CLEAR)
def _():
    _sump_scene(live=False)
    rig_interior([(0.5, 0, 2.3), (4.5, 0, 2.3), (8.5, 0, 2.3), (12.5, 0, 2.2)], energy=150.0, size=1.4)
    camera((-2.6, -0.55, 1.35), (7.0, 0.05, 0.25), focal=32)


@shot("bus_live_clear", res=(960, 720), look=CLEAR)
def _():
    _sump_scene(live=True, corona=0.28)
    rig_interior([(0.5, 0, 2.3), (4.5, 0, 2.3), (8.5, 0, 2.3), (12.5, 0, 2.2)], energy=150.0, size=1.4)
    camera((-2.6, -0.55, 1.35), (7.0, 0.05, 0.25), focal=32)


@shot("bus_insulator_detail", res=(1200, 800), look=CLEAR)
def _():
    _sump_scene(live=False)
    rig_interior([(0.5, 0.6, 2.2), (2.5, -0.6, 2.2)], energy=90.0, size=1.0)
    camera((0.2, -1.3, 1.5), (0.8, 0.0, 2.15), focal=60, dof=5.6)


@shot("bus_corona_from_bank", res=(1200, 750))
def _():
    surveyor(at=(0.4, -0.5, 0), yaw_deg=0, lamp=0.0, look=(9.0, 0.0, 0.0))
    _sump_scene(live=True, corona=0.45)
    rig_insitu(0.012)
    E.add_light("CORONA", "POINT", (10.0, 0, 0.35), 40.0, blackbody(2100), size=2.5)
    camera((-1.9, -0.7, 0.75), (8.0, 0.0, 0.0), focal=32)


@shot("bus_beacon_in_sump", res=(1200, 750))
def _():
    surveyor(at=(1.6, -0.35, 0), yaw_deg=0, lamp=600, lamp_down=10, look=(6.0, 0.2, 0.0))
    _sump_scene(live=True, corona=0.45)
    rig_insitu(0.012)
    E.add_light("CORONA", "POINT", (10.0, 0, 0.35), 40.0, blackbody(2100), size=2.5)
    beacon((6.9, 0.55, -0.25), name="beacon_wet", tilt=0.12)     # in the live water: it lies
    beacon((3.9, -0.62, 0.0), name="beacon_dry")                 # on the bank: honest. Identical.
    camera((0.3, -1.0, 0.62), (6.2, 0.2, 0.05), focal=40)


# ---- C8: the download --------------------------------------------------------------------------
@shot("download_pose_clear", res=(1400, 850), look=CLEAR)
def _():
    aim = 35
    a, p = _on_axis(aim, 2.9)
    b, mv, last = surveyor(at=(p.x, p.y, 0), yaw_deg=aim + 180, lamp=0.0)
    download_pose(b, mv, last)
    assayer(aim_deg=aim, hammer_frac=0.35, hot_k=2050, hot_s=3.0)
    axis_line(aim)
    rig_clear((1.4, 0.9, 0.5), 6, az_deg=-30, el_deg=42)
    camera((4.9, -0.9, 0.85), (1.1, 0.95, 0.45), focal=42)


@shot("download_pose_macro", res=(1200, 800), look=CLEAR)
def _():
    a, p = _on_axis(35, 3.4)
    b, mv, last = surveyor(at=(p.x, p.y, 0), yaw_deg=215, lamp=0.0)
    download_pose(b, mv, last)
    assayer(aim_deg=35, hammer_frac=0.35)
    rig_clear((p.x - 0.3, p.y - 0.2, 0.2), 2.6, az_deg=-20, el_deg=35)
    camera((p.x + 0.9, p.y - 1.4, 0.45), (p.x - 0.35, p.y - 0.25, 0.12), focal=60, dof=4.0)


@shot("download_junction_box_clear", res=(1200, 800), look=CLEAR)
def _():
    b, mv, last = surveyor(at=(-1.8, 0.40, 0), yaw_deg=90, lamp=0.0)
    download_pose(b, mv, last)
    _sump_scene(live=False)
    rig_interior([(-3.5, 0, 2.3), (-0.5, 0, 2.3), (2.5, 0, 2.3)], energy=120.0, size=1.3)
    camera((0.9, -1.0, 1.05), (-1.8, 0.75, 0.65), focal=40)


@shot("download_insitu_wind", res=(1200, 750))
def _():
    aim = 35
    a, p = _on_axis(aim, 5.6)
    b, mv, last = surveyor(at=(p.x, p.y, 0), yaw_deg=aim + 180, lamp=0.0)
    download_pose(b, mv, last)
    k, s = click(5)
    chamber()
    assayer(aim_deg=aim, hammer_frac=5 / 9, tank_fill=0.5, hot_k=k, hot_s=14.0 * s)
    hot_points(k, 1500.0 * s)
    rig_insitu(0.013)
    side = Vector((-math.sin(a), math.cos(a), 0))
    c = p + side * 2.6 + Vector((math.cos(a), math.sin(a), 0)) * 0.6 + Vector((0, 0, 0.55))
    clear_near(c, 1.6)
    camera(c, (p.x - math.cos(a) * 1.4, p.y - math.sin(a) * 1.4, 0.9), focal=35)


@shot("download_insitu_anvil_glow", res=(1200, 750))
def _():
    aim = 35
    a, p = _on_axis(aim, 4.2)
    b, mv, last = surveyor(at=(p.x, p.y, 0), yaw_deg=aim + 180, lamp=0.0)
    download_pose(b, mv, last)
    k, s = click(8)
    chamber()
    assayer(aim_deg=aim, hammer_frac=8 / 9, tank_fill=0.2, hot_k=k, hot_s=14.0 * s)
    hot_points(k, 1500.0 * s)
    rig_insitu(0.013)
    side = Vector((-math.sin(a), math.cos(a), 0))
    c = p + side * 1.6 - Vector((math.cos(a), math.sin(a), 0)) * 1.1 + Vector((0, 0, 0.35))
    clear_near(c, 1.2)
    camera(c, (p.x - math.cos(a) * 0.2, p.y - math.sin(a) * 0.2, 0.25), focal=45, dof=4.0)


@shot("download_step_out", res=(1200, 750))
def _():
    aim = 35
    a, p = _on_axis(aim, 5.6)
    b, mv, last = surveyor(at=(p.x, p.y, 0), yaw_deg=aim + 90, lamp=600, lamp_down=10,
                           move="stand 0.2; walk 1.6 0.55 0 trot; stand 0.1")
    bpy.context.scene.frame_set(int(last * 0.55))
    k, s = click(8)
    chamber()
    assayer(aim_deg=aim, hammer_frac=8 / 9, tank_fill=0.2, hot_k=k, hot_s=14.0 * s)
    hot_points(k, 1500.0 * s)
    rig_insitu(0.013)
    side = Vector((-math.sin(a), math.cos(a), 0))
    c = p - Vector((math.cos(a), math.sin(a), 0)) * 2.4 - side * 1.4 + Vector((0, 0, 0.55))
    clear_near(c, 1.6)
    camera(c, (p.x + side.x * 0.9, p.y + side.y * 0.9, 0.5), focal=32)


# ---- C9: spent ----------------------------------------------------------------------------------
@shot("spent_working_clear", res=(960, 1250), look=CLEAR)
def _():
    assayer(aim_deg=35, hammer_frac=0.72, tank_fill=0.85, hot_k=2100, hot_s=4.0)
    hot_points(2100, 250.0)
    rig_clear((0, 0, 3.3), 14)
    camera((7.5, -10.5, 3.6), (0.1, -0.2, 3.25), focal=42)


@shot("spent_spent_clear", res=(960, 1250), look=CLEAR)
def _():
    # boom parked on the last bearing, hammer at the bottom, tank drained, anvil dry
    assayer(aim_deg=323, hammer_frac=0.0, tank_fill=0.0, drip=False)
    rig_clear((0, 0, 3.3), 14)
    camera((7.5, -10.5, 3.6), (0.1, -0.2, 3.25), focal=42)


@shot("spent_insitu_lamp", res=(1200, 750), exposure=0.7)
def _():
    surveyor(at=(4.8, -2.0, 0), yaw_deg=158, lamp=1000, lamp_down=0.0, look=(0.0, 0.0, 2.4))
    chamber()
    assayer(aim_deg=323, hammer_frac=0.0, tank_fill=0.0, drip=False)
    rig_insitu(0.012)
    clear_near((6.6, -3.3, 0.7), 1.8)
    camera((6.6, -3.3, 0.7), (0.4, -0.3, 2.3), focal=30)


# ---- extras: the slew, the chamber rule ---------------------------------------------------------
@shot("slew_index_plan", res=(960, 960), look=CLEAR)
def _():
    # two bearings 36 deg apart in plan: composited by machinery_sheets.py with the
    # `slew_index_plan_b` frame into one image
    assayer(aim_deg=41.5, hammer_frac=0.0)
    rig_clear((0, 0, 0), 12, el_deg=60)
    camera((0.001, 0, 40), (0, 0, 0), ortho=11.5)


@shot("slew_index_plan_b", res=(960, 960), look=CLEAR)
def _():
    assayer(aim_deg=5.5, hammer_frac=0.0)
    rig_clear((0, 0, 0), 12, el_deg=60)
    camera((0.001, 0, 40), (0, 0, 0), ortho=11.5)


@shot("slew_insitu_blur", res=(1200, 750))
def _():
    surveyor(at=(5.6, -2.8, 0), yaw_deg=150, lamp=600, lamp_down=-30.0, look=(0.0, 0.0, 5.4))
    chamber()
    piv = bpy.data.objects.new("SLEW_PIVOT", None)
    bpy.context.scene.collection.objects.link(piv)
    piv.location = (0, 0, 5.40)
    assayer(aim_deg=41.5, hammer_frac=0.0, boom_pivot=piv)
    sc = bpy.context.scene
    # exaggerated: 36 deg over one frame with a full shutter, so the arm reads as MOVING
    # in a still. In the game it is 36 deg over 3 s and the bearing race is the tell.
    piv.rotation_euler = Euler((0, 0, math.radians(41.5)))
    piv.keyframe_insert("rotation_euler", frame=1)
    piv.rotation_euler = Euler((0, 0, math.radians(41.5 - 36.0)))
    piv.keyframe_insert("rotation_euler", frame=3)
    sc.render.use_motion_blur = True
    sc.render.motion_blur_shutter = 1.0
    rig_insitu(0.012)
    clear_near((7.4, -4.6, 0.9), 1.6)
    camera((7.4, -4.6, 0.9), (0.2, -0.2, 4.6), focal=30)
    sc.frame_set(2)


@shot("chamber_rule_cutaway", res=(1400, 800), look=CLEAR)
def _():
    surveyor(at=(3.6, -1.6, 0), yaw_deg=150, lamp=0.0)
    chamber(radius=10.5, height=11.5)
    assayer(aim_deg=35, hammer_frac=0.0)
    # a 2.4 x 2.4 m drive mouth poking through the far wall, for the height comparison
    E.passage(width=2.4, height=2.4, length=12.0, mat=E.rock("pass_rock", albedo_lo=0.035, albedo_hi=0.30), seed=3, rubble=0)
    for o in list(bpy.data.objects):
        if o.name == "passage":
            o.location = Vector(o.location) + Vector((-20.0, 2.5, 0))
        elif o.name.startswith("floor") and o.name != "floor":
            bpy.data.objects.remove(o, do_unlink=True)
    world_grey(1.0, 0.30)
    E.add_light("TOP", "AREA", (0, 0, 8.9), 5200.0, (1.0, 0.97, 0.93), size=8.0, aim=(0, 0, 0))
    E.add_light("KEY", "AREA", (14, -12, 8), 9000.0, (1.0, 0.97, 0.93), size=6.0, aim=(0, 0, 3))
    # the cutaway: the camera's near clip removes the chamber wall between it and the machine
    camera((20.0, -12.0, 3.4), (-1.0, 0.5, 3.2), focal=32, clip_start=14.3)


# ---------------------------------------------------------------------------------------
if A.list:
    for k in SHOTS:
        print(k)
    raise SystemExit(0)
if not A.shot or not A.out:
    raise SystemExit("--shot and --out are required (or --list)")
fn, res, look, exposure = SHOTS[A.shot]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.unit_settings.system = "METRIC"
fn()
if A.res:
    res = tuple(int(v) for v in A.res.split("x"))
samples = A.samples
if A.quick:
    res = (res[0] // 2, res[1] // 2)
    samples = 8
E.settings(samples=samples, res=res, look=look, exposure=A.exposure if A.exposure is not None else exposure)
cy = bpy.context.scene.cycles
cy.max_bounces = 5
cy.diffuse_bounces = 3
cy.glossy_bounces = 3
cy.transmission_bounces = 4
cy.transparent_max_bounces = 8
bpy.context.scene.render.filepath = os.path.abspath(A.out)
bpy.ops.render.render(write_still=True)
print("RENDERED", A.out)
