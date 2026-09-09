"""Vision-board probe: THE DESCENT AND THE CAVE (group B of the inventory).

One script, many shots. Every shot is either

  CLEAR    a concept-art reference: neutral grey world at strength 1.0, one 3 m area key
           from about 45 deg high, AgX base look, a scale reference in frame. Enclosed
           rock is cut away (bisected) so the light gets in. NOT the game.
  IN-SITU  the game's own light: world strength 0, only diegetic sources -- the head lamp
           (white, re-aimed +X, tilted down), the shaft's 12000 K sky, a beacon pilot, the
           Assayer's winch at a Blackbody temperature. AgX medium-high contrast.

Run one shot:
  "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b -P cave_probe.py -- \
      --shot b12_03_insitu_drive_lamp --out <abs>.png
Run many in one process (saves the 15 s start-up per frame):
  ... -- --shots b12_,b13_ --outdir <abs dir> [--skip-existing]

Reuses docs/art/probes/p2_env.py (passage, chamber, lights, settings) and copies the
worked drive from docs/art/ruins/ruins_probe.py (that file parses argv at import, so it
cannot be imported). agent_model is used read-only; its three known rig faults (lamp aimed
backwards, cyan strips, team-tinted lamp) are corrected here at runtime, as av_probe does.

Everything numeric that is not in ART-DIRECTION.md is a guess and is listed in NOTES.md.
"""
import argparse
import math
import os
import random
import sys
import time
import traceback

REPO = r"C:/Users/jackh/documents/programming/Blindside"
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "docs/art/probes"))

import bpy  # noqa: E402
import bmesh  # noqa: E402
from mathutils import Vector, Euler, Matrix  # noqa: E402

from agent_model import params as P  # noqa: E402
from agent_model import geometry as G  # noqa: E402
from agent_model.build import build_agent  # noqa: E402
from agent_model.motion import Mover, script  # noqa: E402
import p2_env as E  # noqa: E402

# ---------------------------------------------------------------------------------------
# palette (linear RGB unless marked)
# ---------------------------------------------------------------------------------------
def _lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def srgb(hexstr):
    h = hexstr.lstrip("#")
    return tuple(_lin(int(h[i:i + 2], 16) / 255.0) for i in (0, 2, 4))


LAMP_WHITE = (1.00, 0.98, 0.95)                 # ART-DIRECTION 2.1: every team's work lamp
SKY = (0.60, 0.74, 1.00)                         # 12000 K, the shaft, the only cold light
BONE = srgb("#F2E6D2")                           # player emissives
WARM_DIM = srgb("#7A6650")                       # beacon pilot, never team-coloured
PLAYER_SHELL, PLAYER_CHASSIS = (0.66, 0.63, 0.57), (0.050, 0.052, 0.058)
CAST_IRON = (0.075, 0.038, 0.021)                # wet a century, never orange
BEARING = (0.52, 0.50, 0.48)                     # still working
FOG = (0.85, 0.86, 0.90)                         # resting silt colour, so it never blue-shifts
CELL = 0.6


# ---------------------------------------------------------------------------------------
# materials
# ---------------------------------------------------------------------------------------
def _mat(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    return m, nt, nt.nodes.new("ShaderNodeOutputMaterial")


def rock(name="rock", albedo_lo=0.035, albedo_hi=0.30, warm=1.0, wet=0.35, wet_rough=0.10,
         waterline=None, bed_scale=0.9, fracture_scale=6.0, bump=0.9, dark=0.0,
         wet_above_z=None, grid=None, crack=0.0):
    """p2_env.rock() extended: `wet_rough` is the wet roughness target (0.10 per the
    direction), `dark` is the depth field (albedo x (1 - 0.55 dark)), `wet_above_z` puts
    condensation above a height and not below (thermal layer), `grid` draws a module
    grid on the surface for CLEAR views only. `crack` (0 = off, as p2_env) darkens the
    voronoi cell edges in the COLOUR and doubles the fracture bump: the direction makes
    fracture a bump-only term, and bump does not survive a soft studio key, so the
    rock-type frames need the cracks drawn to show what the scalar means."""
    m, nt, out = _mat(name)
    n, L = nt.nodes, nt.links.new
    b = n.new("ShaderNodeBsdfPrincipled")
    L(b.outputs[0], out.inputs[0])
    geo = n.new("ShaderNodeNewGeometry")
    sep = n.new("ShaderNodeSeparateXYZ")
    L(geo.outputs["Position"], sep.inputs["Vector"])

    bed = n.new("ShaderNodeTexNoise")
    bed.inputs["Scale"].default_value = bed_scale
    bed.inputs["Detail"].default_value = 12.0
    bed.inputs["Roughness"].default_value = 0.62
    L(geo.outputs["Position"], bed.inputs["Vector"])
    frac = n.new("ShaderNodeTexVoronoi")
    frac.inputs["Scale"].default_value = fracture_scale
    L(geo.outputs["Position"], frac.inputs["Vector"])

    k = 1.0 - 0.55 * dark

    def tone(v):
        v = v * k
        return (v * (1.0 + 0.22 * warm), v * (1.0 - 0.02 * warm), v * (1.0 - 0.28 * warm), 1.0)

    ramp = n.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.28
    ramp.color_ramp.elements[0].color = tone(albedo_lo)
    ramp.color_ramp.elements[1].position = 0.78
    ramp.color_ramp.elements[1].color = tone(albedo_hi)
    L(bed.outputs["Fac"], ramp.inputs["Fac"])
    colour = ramp.outputs["Color"]

    # wetness factor: a constant, or a height mask (condensation above the thermal layer)
    if wet_above_z is None:
        wv = n.new("ShaderNodeValue")
        wv.outputs[0].default_value = wet
        wetf = wv.outputs[0]
    else:
        mr = n.new("ShaderNodeMapRange")
        mr.inputs["From Min"].default_value = wet_above_z - 0.12
        mr.inputs["From Max"].default_value = wet_above_z + 0.12
        mr.inputs["To Min"].default_value = 0.05
        mr.inputs["To Max"].default_value = wet
        mr.clamp = True
        L(sep.outputs["Z"], mr.inputs["Value"])
        wetf = mr.outputs["Result"]

    dry_r = n.new("ShaderNodeMath")
    dry_r.operation = "MULTIPLY_ADD"
    dry_r.inputs[1].default_value = -0.25
    dry_r.inputs[2].default_value = 0.96
    L(bed.outputs["Fac"], dry_r.inputs[0])
    rmix = n.new("ShaderNodeMix")
    rmix.data_type = "FLOAT"
    rmix.inputs["B"].default_value = wet_rough
    L(wetf, rmix.inputs["Factor"])
    L(dry_r.outputs[0], rmix.inputs["A"])
    rough = rmix.outputs["Result"]

    # wet darkens: albedo x (1 - 0.4 wet)
    wf = n.new("ShaderNodeMath")
    wf.operation = "MULTIPLY"
    wf.inputs[1].default_value = 0.4
    L(wetf, wf.inputs[0])
    dk = n.new("ShaderNodeMix")
    dk.data_type = "RGBA"
    dk.blend_type = "MULTIPLY"
    dk.inputs["B"].default_value = (0, 0, 0, 1)
    L(wf.outputs[0], dk.inputs["Factor"])
    L(colour, dk.inputs["A"])
    colour = dk.outputs["Result"]

    if waterline is not None:
        sub = n.new("ShaderNodeMapRange")
        sub.inputs["From Min"].default_value = waterline
        sub.inputs["From Max"].default_value = waterline - 0.04
        sub.inputs["To Min"].default_value = 0.0
        sub.inputs["To Max"].default_value = 1.0
        sub.clamp = True
        L(sep.outputs["Z"], sub.inputs["Value"])
        tide = n.new("ShaderNodeMapRange")
        tide.inputs["From Min"].default_value = waterline + 0.14
        tide.inputs["From Max"].default_value = waterline + 0.005
        tide.inputs["To Min"].default_value = 0.0
        tide.inputs["To Max"].default_value = 1.0
        tide.clamp = True
        L(sep.outputs["Z"], tide.inputs["Value"])
        wetc = n.new("ShaderNodeMix")
        wetc.data_type = "RGBA"
        wetc.inputs["B"].default_value = tone(albedo_lo * 0.6)
        L(sub.outputs["Result"], wetc.inputs["Factor"])
        L(colour, wetc.inputs["A"])
        crust = n.new("ShaderNodeMix")
        crust.data_type = "RGBA"
        crust.inputs["B"].default_value = tone(min(albedo_hi * 1.7, 0.72))
        L(tide.outputs["Result"], crust.inputs["Factor"])
        L(wetc.outputs["Result"], crust.inputs["A"])
        colour = crust.outputs["Result"]
        wr = n.new("ShaderNodeMix")
        wr.data_type = "FLOAT"
        wr.inputs["B"].default_value = 0.10
        L(sub.outputs["Result"], wr.inputs["Factor"])
        L(rough, wr.inputs["A"])
        rough = wr.outputs["Result"]
        # the crust is matte
        cr = n.new("ShaderNodeMix")
        cr.data_type = "FLOAT"
        cr.inputs["B"].default_value = 0.92
        L(tide.outputs["Result"], cr.inputs["Factor"])
        L(rough, cr.inputs["A"])
        rough = cr.outputs["Result"]

    if crack > 0:
        edge = n.new("ShaderNodeTexVoronoi")
        edge.feature = "DISTANCE_TO_EDGE"
        edge.inputs["Scale"].default_value = fracture_scale
        L(geo.outputs["Position"], edge.inputs["Vector"])
        er = n.new("ShaderNodeMapRange")
        er.inputs["From Min"].default_value = 0.0
        er.inputs["From Max"].default_value = 0.07        # in the texture's scaled space: 7% of a cell
        er.inputs["To Min"].default_value = crack
        er.inputs["To Max"].default_value = 0.0
        er.clamp = True
        L(edge.outputs["Distance"], er.inputs["Value"])
        cm = n.new("ShaderNodeMix")
        cm.data_type = "RGBA"
        cm.inputs["B"].default_value = tone(albedo_lo * 0.35)
        L(er.outputs["Result"], cm.inputs["Factor"])
        L(colour, cm.inputs["A"])
        colour = cm.outputs["Result"]

    if grid:
        lines = None
        for axis in ("X", "Y"):
            w = n.new("ShaderNodeMath")
            w.operation = "WRAP"
            w.inputs[1].default_value = grid
            w.inputs[2].default_value = 0.0
            L(sep.outputs[axis], w.inputs[0])
            lt = n.new("ShaderNodeMath")
            lt.operation = "LESS_THAN"
            lt.inputs[1].default_value = 0.03
            L(w.outputs[0], lt.inputs[0])
            if lines is None:
                lines = lt.outputs[0]
            else:
                mx = n.new("ShaderNodeMath")
                mx.operation = "MAXIMUM"
                L(lines, mx.inputs[0])
                L(lt.outputs[0], mx.inputs[1])
                lines = mx.outputs[0]
        gm = n.new("ShaderNodeMix")
        gm.data_type = "RGBA"
        gm.inputs["B"].default_value = (0.02, 0.02, 0.02, 1)
        L(lines, gm.inputs["Factor"])
        L(colour, gm.inputs["A"])
        colour = gm.outputs["Result"]

    L(colour, b.inputs["Base Color"])
    L(rough, b.inputs["Roughness"])
    b.inputs["Specular IOR Level"].default_value = 0.35
    bmp2 = n.new("ShaderNodeBump")
    bmp2.inputs["Strength"].default_value = 0.35 + 0.5 * crack
    L(frac.outputs["Distance"], bmp2.inputs["Height"])
    bmp = n.new("ShaderNodeBump")
    bmp.inputs["Strength"].default_value = bump
    L(bed.outputs["Fac"], bmp.inputs["Height"])
    L(bmp2.outputs["Normal"], bmp.inputs["Normal"])
    L(bmp.outputs["Normal"], b.inputs["Normal"])
    return m


def cast_iron(name="cast_iron", base=CAST_IRON, rough=0.86, scale=2.5):
    """ART-DIRECTION 5.2: (0.075,0.038,0.021), roughness 0.86, metallic 0, mottled on a
    low-frequency noise, bump on two scales. A piece of the cave that has corners."""
    m, nt, out = _mat(name)
    n, L = nt.nodes, nt.links.new
    b = n.new("ShaderNodeBsdfPrincipled")
    b.inputs["Metallic"].default_value = 0.0
    b.inputs["Specular IOR Level"].default_value = 0.4
    geo = n.new("ShaderNodeNewGeometry")
    tx = n.new("ShaderNodeTexNoise")
    tx.inputs["Scale"].default_value = scale
    tx.inputs["Detail"].default_value = 9
    fine = n.new("ShaderNodeTexNoise")
    fine.inputs["Scale"].default_value = scale * 16
    fine.inputs["Detail"].default_value = 5
    L(geo.outputs["Position"], tx.inputs["Vector"])
    L(geo.outputs["Position"], fine.inputs["Vector"])
    ramp = n.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.35
    ramp.color_ramp.elements[0].color = (base[0] * 0.45, base[1] * 0.45, base[2] * 0.5, 1)
    ramp.color_ramp.elements[1].position = 0.72
    ramp.color_ramp.elements[1].color = (base[0] * 1.25, base[1] * 1.15, base[2] * 1.05, 1)
    L(tx.outputs["Fac"], ramp.inputs["Fac"])
    L(ramp.outputs["Color"], b.inputs["Base Color"])
    rg = n.new("ShaderNodeMath")
    rg.operation = "MULTIPLY_ADD"
    rg.inputs[1].default_value = 0.10
    rg.inputs[2].default_value = rough - 0.05
    L(tx.outputs["Fac"], rg.inputs[0])
    L(rg.outputs[0], b.inputs["Roughness"])
    b1 = n.new("ShaderNodeBump")
    b1.inputs["Strength"].default_value = 0.18
    L(fine.outputs["Fac"], b1.inputs["Height"])
    b2 = n.new("ShaderNodeBump")
    b2.inputs["Strength"].default_value = 0.30
    L(tx.outputs["Fac"], b2.inputs["Height"])
    L(b1.outputs["Normal"], b2.inputs["Normal"])
    L(b2.outputs["Normal"], b.inputs["Normal"])
    L(b.outputs[0], out.inputs[0])
    return m


def bearing_steel(name="bearing_steel", rough=0.30, tint=BEARING):
    m, nt, out = _mat(name)
    n, L = nt.nodes, nt.links.new
    b = n.new("ShaderNodeBsdfPrincipled")
    b.inputs["Base Color"].default_value = (*tint, 1)
    b.inputs["Metallic"].default_value = 1.0
    b.inputs["Roughness"].default_value = rough
    tx = n.new("ShaderNodeTexNoise")
    tx.inputs["Scale"].default_value = 60
    r = n.new("ShaderNodeMath")
    r.operation = "MULTIPLY_ADD"
    r.inputs[1].default_value = 0.12
    r.inputs[2].default_value = rough - 0.06
    L(tx.outputs["Fac"], r.inputs[0])
    L(r.outputs[0], b.inputs["Roughness"])
    L(b.outputs[0], out.inputs[0])
    return m


def graphitised(name="graphitised"):
    """Cast iron below the waterline: iron gone, graphite shell left. Black, velvety."""
    m, nt, out = _mat(name)
    n, L = nt.nodes, nt.links.new
    b = n.new("ShaderNodeBsdfPrincipled")
    b.inputs["Base Color"].default_value = (0.012, 0.011, 0.010, 1)
    b.inputs["Metallic"].default_value = 0.0
    b.inputs["Roughness"].default_value = 0.98
    b.inputs["Specular IOR Level"].default_value = 0.15
    L(b.outputs[0], out.inputs[0])
    return m


def porcelain(name="porcelain"):
    """Glazed white: the only clean, undamaged material in the game (the Bus insulators)."""
    m, nt, out = _mat(name)
    n, L = nt.nodes, nt.links.new
    b = n.new("ShaderNodeBsdfPrincipled")
    b.inputs["Base Color"].default_value = (0.86, 0.85, 0.80, 1)
    b.inputs["Roughness"].default_value = 0.10
    b.inputs["Coat Weight"].default_value = 1.0
    b.inputs["Coat Roughness"].default_value = 0.03
    L(b.outputs[0], out.inputs[0])
    return m


def timber(name="timber"):
    """Waterlogged set timber: near-black, matte, grain along X. A guess."""
    m, nt, out = _mat(name)
    n, L = nt.nodes, nt.links.new
    b = n.new("ShaderNodeBsdfPrincipled")
    b.inputs["Roughness"].default_value = 0.85
    b.inputs["Specular IOR Level"].default_value = 0.2
    geo = n.new("ShaderNodeNewGeometry")
    mp = n.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (1.0, 14.0, 14.0)
    L(geo.outputs["Position"], mp.inputs["Vector"])
    tx = n.new("ShaderNodeTexNoise")
    tx.inputs["Scale"].default_value = 3.0
    tx.inputs["Detail"].default_value = 8
    L(mp.outputs["Vector"], tx.inputs["Vector"])
    ramp = n.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.030, 0.022, 0.015, 1)
    ramp.color_ramp.elements[1].color = (0.085, 0.062, 0.040, 1)
    L(tx.outputs["Fac"], ramp.inputs["Fac"])
    L(ramp.outputs["Color"], b.inputs["Base Color"])
    bm = n.new("ShaderNodeBump")
    bm.inputs["Strength"].default_value = 0.5
    L(tx.outputs["Fac"], bm.inputs["Height"])
    L(bm.outputs["Normal"], b.inputs["Normal"])
    L(b.outputs[0], out.inputs[0])
    return m


def conductor(name="conductor"):
    """The Bus conductor: bare metal gone dark. Never glows. A guess at the alloy."""
    m, nt, out = _mat(name)
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    b.inputs["Base Color"].default_value = (0.16, 0.10, 0.06, 1)
    b.inputs["Metallic"].default_value = 0.7
    b.inputs["Roughness"].default_value = 0.45
    nt.links.new(b.outputs[0], out.inputs[0])
    return m


def water_surface(name="water_surface"):
    """IOR 1.33, roughness 0.02: a mirror at grazing angle (ART-DIRECTION 3.5)."""
    m, nt, out = _mat(name)
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    b.inputs["Base Color"].default_value = (1, 1, 1, 1)
    b.inputs["Transmission Weight"].default_value = 1.0
    b.inputs["Roughness"].default_value = 0.02
    b.inputs["IOR"].default_value = 1.33
    nt.links.new(b.outputs[0], out.inputs[0])
    return m


def emit(rgb, strength, name="emit"):
    m, nt, out = _mat(name)
    e = nt.nodes.new("ShaderNodeEmission")
    e.inputs["Color"].default_value = (*rgb, 1)
    e.inputs["Strength"].default_value = strength
    nt.links.new(e.outputs[0], out.inputs[0])
    return m


def flat(rgb, rough=0.6, name="flat"):
    m, nt, out = _mat(name)
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = rough
    nt.links.new(b.outputs[0], out.inputs[0])
    return m


def water_volume(name="water_volume", scatter=0.35, absorb=0.12, aniso=0.8):
    """Below the waterline: scatter 0.35, absorption weighted off red, anisotropy 0.8.
    Light dies in 4-6 m (ART-DIRECTION 2.6)."""
    m, nt, out = _mat(name)
    n, L = nt.nodes, nt.links.new
    s = n.new("ShaderNodeVolumeScatter")
    s.inputs["Density"].default_value = scatter
    s.inputs["Anisotropy"].default_value = aniso
    s.inputs["Color"].default_value = (0.80, 0.86, 0.90, 1)
    a = n.new("ShaderNodeVolumeAbsorption")
    a.inputs["Density"].default_value = absorb
    a.inputs["Color"].default_value = (0.45, 0.70, 0.82, 1)     # red dies first
    add = n.new("ShaderNodeAddShader")
    L(s.outputs[0], add.inputs[0])
    L(a.outputs[0], add.inputs[1])
    L(add.outputs[0], out.inputs["Volume"])
    return m


def silt_volume(density, name="silt"):
    """A local plume: density falls off spherically in the object's own space."""
    m, nt, out = _mat(name)
    n, L = nt.nodes, nt.links.new
    tc = n.new("ShaderNodeTexCoord")
    gr = n.new("ShaderNodeTexGradient")
    gr.gradient_type = "SPHERICAL"
    L(tc.outputs["Object"], gr.inputs["Vector"])
    nz = n.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 2.5
    L(tc.outputs["Object"], nz.inputs["Vector"])
    sh = n.new("ShaderNodeMath")
    sh.operation = "MULTIPLY_ADD"
    sh.inputs[1].default_value = 0.8
    sh.inputs[2].default_value = 0.6
    L(nz.outputs["Fac"], sh.inputs[0])
    pw = n.new("ShaderNodeMath")
    pw.operation = "POWER"
    pw.inputs[1].default_value = 1.6
    L(gr.outputs["Fac"], pw.inputs[0])
    mul = n.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    L(pw.outputs[0], mul.inputs[0])
    L(sh.outputs[0], mul.inputs[1])
    d = n.new("ShaderNodeMath")
    d.operation = "MULTIPLY"
    d.inputs[1].default_value = density * 2.2
    L(mul.outputs[0], d.inputs[0])
    s = n.new("ShaderNodeVolumeScatter")
    s.inputs["Anisotropy"].default_value = 0.55
    s.inputs["Color"].default_value = (*FOG, 1)
    L(d.outputs[0], s.inputs["Density"])
    L(s.outputs[0], out.inputs["Volume"])
    return m


def haze_volume(density=0.06, name="haze"):
    m, nt, out = _mat(name)
    s = nt.nodes.new("ShaderNodeVolumeScatter")
    s.inputs["Density"].default_value = density
    s.inputs["Anisotropy"].default_value = 0.6
    s.inputs["Color"].default_value = (*FOG, 1)
    nt.links.new(s.outputs[0], out.inputs["Volume"])
    return m


# ---------------------------------------------------------------------------------------
# mesh surgery
# ---------------------------------------------------------------------------------------
def _bm_edit(obj, fn):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    fn(bm)
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()


def delete_ngons(obj):
    """Tube caps (p2_env passages are capped cylinders)."""
    _bm_edit(obj, lambda bm: bmesh.ops.delete(bm, geom=[f for f in bm.faces if len(f.verts) > 4], context="FACES"))


def bisect(obj, co, no):
    """Cut at world plane (co, no); delete the side the normal points to. The cutaway."""
    inv = obj.matrix_world.inverted()
    co_l = inv @ Vector(co)
    no_l = (inv.to_3x3() @ Vector(no)).normalized()

    def f(bm):
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
        bmesh.ops.bisect_plane(bm, geom=geom, dist=1e-4, plane_co=co_l, plane_no=no_l, clear_outer=True)
    _bm_edit(obj, f)


def punch(obj, p0, axis, radius, forward_only=False):
    """Delete faces within `radius` of the world line (p0, axis): an opening for a mouth.
    `forward_only` keeps the faces behind p0 along the axis (one wall, not both)."""
    p0, ax = Vector(p0), Vector(axis).normalized()
    mw = obj.matrix_world

    def f(bm):
        kill = []
        for fc in bm.faces:
            c = mw @ fc.calc_center_median()
            d = c - p0
            if forward_only and d.dot(ax) < 0:
                continue
            if (d - ax * d.dot(ax)).length < radius:
                kill.append(fc)
        bmesh.ops.delete(bm, geom=kill, context="FACES")
    _bm_edit(obj, f)


def first(col, prefix):
    return next(o for o in col.objects if o.name.startswith(prefix))


def cull(col, y_lt, keep=("chamber", "floor", "passage", "drive", "water", "aven")):
    """After a cutaway at y = y_lt: remove the loose props that stood in the removed half,
    or they hang in the air in front of the camera."""
    for o in list(col.objects):
        if o.name.startswith(keep):
            continue
        if o.location.y < y_lt:
            bpy.data.objects.remove(o)


# ---------------------------------------------------------------------------------------
# props
# ---------------------------------------------------------------------------------------
def water_plane(z, size=40.0, center=(0, 0), col=None):
    p = G.plane("water", size, (center[0], center[1], z), col=col)
    G.set_material(p, water_surface())
    return p


def water_box(z_top, x0, x1, y0, y1, depth=3.0, col=None, **kw):
    """The underwater medium: a box of volume from the waterline down."""
    b = G.box("water_body", (x1 - x0, y1 - y0, depth), ((x0 + x1) / 2, (y0 + y1) / 2, z_top - depth / 2 - 0.001), col=col)
    G.set_material(b, water_volume(**kw))
    return b


def ruler(loc, length=1.2, yaw=0.0, col=None, step=0.3):
    """A black/white bar: the 1.2 m module made visible in CLEAR views."""
    dark, pale = flat((0.02, 0.02, 0.02), 0.5, "ruler_k"), flat((0.85, 0.85, 0.82), 0.5, "ruler_w")
    objs = []
    n = int(round(length / step))
    for i in range(n):
        x = -length / 2 + step * (i + 0.5)
        o = G.box(f"ruler.{i}", (step, 0.05, 0.05), (loc[0] + x * math.cos(yaw), loc[1] + x * math.sin(yaw), loc[2] + 0.025),
                  rot=(0, 0, yaw), col=col)
        G.set_material(o, dark if i % 2 else pale)
        objs.append(o)
    return objs


def gauge_lines(x0, x1, y=0.0, gauge=0.60, z=0.005, col=None):
    """Two pale strips 0.60 m apart on a natural floor: the rail gauge, painted."""
    m = flat((0.7, 0.68, 0.6), 0.7, "gauge_paint")
    for s in (1, -1):
        o = G.box(f"gauge.{s}", (x1 - x0, 0.02, 0.01), ((x0 + x1) / 2, y + s * gauge / 2, z), col=col)
        G.set_material(o, m)


def track(length, x0=0.0, y0=0.15, gauge=0.60, z=0.0, polished=True, col=None, seed=3):
    """Rail on timber sleepers at 600 mm gauge. Rusted web, and a rounded head that the
    work has polished bright (ART-DIRECTION 5.6): the only specular landmark in the cave."""
    iron = cast_iron("rail_iron", rough=0.9, scale=4.0)
    head = bearing_steel("rail_head", rough=0.16) if polished else iron
    wood = timber("sleeper")
    rng = random.Random(seed)
    for k in range(int(length / 0.60)):
        x = x0 - length / 2 + 0.3 + k * 0.60
        o = G.box(f"sleeper.{k}", (0.12, gauge + 0.34, 0.06), (x, y0 + rng.uniform(-0.01, 0.01), z + 0.03),
                  rot=(0, 0, rng.uniform(-0.02, 0.02)), col=col)
        G.set_material(o, wood)
    for s in (1, -1):
        y = y0 + s * gauge / 2
        G.set_material(G.box(f"rail_web.{s}", (length - 0.3, 0.018, 0.075), (x0, y, z + 0.095), col=col), iron)
        G.set_material(G.box(f"rail_foot.{s}", (length - 0.3, 0.075, 0.012), (x0, y, z + 0.063), col=col), iron)
        h = G.cyl(f"rail_head.{s}", 0.024, 0.024, length - 0.3, (x0, y, z + 0.135), rot=(0, math.pi / 2, 0), verts=14, col=col)
        G.set_material(h, head)


def beacon(loc, col=None, name="beacon", pilot=True, light=1.5):
    """ART-DIRECTION 6.3: 230 x 60 mm cast tube, weighted self-righting base, one warm
    pilot at the top (WARM_DIM), a retroreflective band. The pilot's point light is a
    guess (the pilot must light something, or it is a dot)."""
    x, y, z = loc
    G.set_material(G.cyl(f"{name}_base", 0.058, 0.036, 0.06, (x, y, z + 0.03), verts=16, col=col), graphitised(f"{name}_g"))
    G.set_material(G.cyl(f"{name}_body", 0.030, 0.030, 0.19, (x, y, z + 0.155), verts=16, col=col), cast_iron(f"{name}_i", scale=8.0))
    band = flat((0.55, 0.55, 0.52), 0.18, f"{name}_band")      # retroreflective approximated as gloss
    G.set_material(G.cyl(f"{name}_band", 0.0315, 0.0315, 0.025, (x, y, z + 0.19), verts=16, col=col), band)
    if pilot:
        G.set_material(G.sphere(f"{name}_pilot", 0.011, (x, y, z + 0.258), col=col, seg=12), emit(WARM_DIM, 12.0, f"{name}_p"))
        if light > 0:
            E.add_light(f"{name}_L", "POINT", (x, y, z + 0.27), light, WARM_DIM, size=0.02)


def timber_set(x, hw=1.20, leg=1.20, col=None, mat=None, failed=False, rock_mat=None, seed=4):
    """A timber set: two posts and a cap, in the 1.2 m module. `failed`: one post broken,
    the cap down at one end, spall on the floor under it."""
    mat = mat or timber("set_timber")
    h = leg + 0.72
    yp = hw - 0.14
    if not failed:
        for s in (1, -1):
            G.set_material(G.box(f"post{s}.{x:.1f}", (0.20, 0.18, h), (x, s * yp, h / 2), col=col), mat)
        G.set_material(G.box(f"cap.{x:.1f}", (0.20, 2 * yp + 0.18, 0.22), (x, 0, h + 0.11), col=col), mat)
        return
    rng = random.Random(seed)
    # the +Y post stands; the -Y post is broken at 0.55 m and its top lies on the floor
    G.set_material(G.box(f"post_ok.{x:.1f}", (0.20, 0.18, h), (x, yp, h / 2), col=col), mat)
    G.set_material(G.box(f"post_stub.{x:.1f}", (0.20, 0.18, 0.55), (x, -yp, 0.275), col=col), mat)
    G.set_material(G.box(f"post_fallen.{x:.1f}", (0.20, 0.18, h - 0.55), (x + 0.35, -yp + 0.9, 0.12),
                         rot=(math.radians(-80), math.radians(12), 0.35), col=col), mat)
    # cap: one end on the standing post, the other on the floor
    a = Vector((x, yp, h + 0.11))
    bpt = Vector((x + 0.25, -yp + 0.25, 0.15))
    d = bpt - a
    cap = G.box(f"cap_fallen.{x:.1f}", (0.20, d.length, 0.22), ((a + bpt) / 2), col=col)
    cap.rotation_euler = d.to_track_quat("Y", "Z").to_euler()
    G.set_material(cap, mat)
    # spall: the rock that came down, under it
    for i in range(9):
        r = rng.uniform(0.08, 0.30)
        px = x + rng.uniform(-0.8, 0.8)
        py = rng.uniform(-yp + 0.1, 0.4)
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=r, location=(px, py, r * 0.45))
        o = bpy.context.object
        o.name = f"spall.{x:.1f}.{i}"
        o.scale = (rng.uniform(0.8, 1.7), rng.uniform(0.8, 1.5), rng.uniform(0.35, 0.7))
        o.rotation_euler = (rng.uniform(0, 3), rng.uniform(0, 3), rng.uniform(0, 3))
        o.data.shade_flat()
        if col is not None:
            for c in list(o.users_collection):
                c.objects.unlink(o)
            col.objects.link(o)
        G.set_material(o, rock_mat or mat)


def joint(loc, length, yaw=0.0, tilt=0.0, col=None, width=0.03):
    """An open joint: a dark slot in the rock. A guess at how 'a fracture set that runs'
    reads -- geometry, not colour."""
    o = G.box("joint", (length, width, 0.05), loc, rot=(tilt, 0, yaw), col=col)
    G.set_material(o, flat((0.004, 0.004, 0.004), 0.95, "joint_dark"))
    return o


def plate(loc, yaw=0.0, text="K7-41", col=None, corroded=False, name="plate"):
    """ART-DIRECTION 6.5: a cast index plate at 1.40 m, raised numbers, no emission,
    legible only with a lamp on it. Faces -Y after `yaw` (so yaw=0 sits on the +Y wall)."""
    iron = cast_iron(f"{name}_iron", rough=0.92 if corroded else 0.82, scale=12.0)
    rot = (0, 0, yaw)
    R = Matrix.Rotation(yaw, 4, "Z")
    base = Vector(loc)

    def at(dx, dy, dz):
        return base + (R @ Vector((dx, dy, dz)))
    G.set_material(G.box(f"{name}_body", (0.16, 0.012, 0.10), at(0, 0, 0), rot=rot, bevel=0.003, col=col), iron)
    G.set_material(G.box(f"{name}_rim", (0.15, 0.004, 0.09), at(0, -0.007, 0), rot=rot, bevel=0.002, col=col), iron)
    for s in (1, -1):
        G.set_material(G.cyl(f"{name}_bolt{s}", 0.007, 0.006, 0.006, at(s * 0.068, -0.009, 0.037), rot=(math.pi / 2 + yaw * 0, 0, 0), verts=8, col=col),
                       bearing_steel(f"{name}_b{s}", rough=0.6, tint=(0.25, 0.22, 0.20)))
    # raised numerals: legible as an index, not as language
    bpy.ops.object.text_add(location=at(0, -0.010, -0.004), rotation=(math.pi / 2, 0, yaw))
    t = bpy.context.object
    t.data.body = text
    t.data.size = 0.052
    t.data.extrude = 0.0015 if corroded else 0.0028
    t.data.align_x = "CENTER"
    t.data.align_y = "CENTER"
    bpy.ops.object.convert(target="MESH")
    t = bpy.context.object
    t.name = f"{name}_num"
    G.set_material(t, iron)
    if col is not None:
        for c in list(t.users_collection):
            c.objects.unlink(t)
        col.objects.link(t)
    # foundry mark: a ring and a triangle, bottom right. No date.
    G.set_material(G.torus(f"{name}_mark", 0.010, 0.0022, at(0.058, -0.010, -0.036), rot=(math.pi / 2, 0, yaw), col=col), iron)
    G.set_material(G.cyl(f"{name}_mark_t", 0.005, 0.005, 0.004, at(0.058, -0.010, -0.036), rot=(math.pi / 2, 0, yaw), verts=3, col=col), iron)
    if corroded:
        # half-buried in flowstone: a calcite drip over the lower half
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=0.07, location=at(-0.02, -0.006, -0.05))
        o = bpy.context.object
        o.name = f"{name}_flow"
        o.scale = (1.4, 0.22, 1.3)
        o.rotation_euler = rot
        mm = o.modifiers.new("d", "DISPLACE")
        tt = bpy.data.textures.new(f"{name}_ft", "CLOUDS")
        tt.noise_scale = 0.05
        mm.texture = tt
        mm.strength = 0.03
        o.data.shade_smooth()
        fs, nt, out = _mat(f"{name}_flowstone")
        b = nt.nodes.new("ShaderNodeBsdfPrincipled")
        b.inputs["Base Color"].default_value = (0.30, 0.20, 0.10, 1)
        b.inputs["Roughness"].default_value = 0.25
        nt.links.new(b.outputs[0], out.inputs[0])
        G.set_material(o, fs)
        if col is not None:
            for c in list(o.users_collection):
                c.objects.unlink(o)
            col.objects.link(o)


def bus(length, z, x0=0.0, y=0.0, spacing=2.4, col=None, hang=0.32, pin_to=None):
    """THE BUS: a bare conductor on glazed white porcelain insulators, hung from the crown.
    It never glows. The insulator shape and the 2.4 m pitch are guesses."""
    cm = conductor()
    pm = porcelain()
    im = cast_iron("bus_iron", rough=0.9, scale=6.0)
    G.set_material(G.cyl("bus_conductor", 0.012, 0.012, length, (x0, y, z), rot=(0, math.pi / 2, 0), verts=10, col=col), cm)
    n = int(length / spacing)
    for k in range(n + 1):
        x = x0 - length / 2 + spacing * 0.5 + k * spacing
        if x > x0 + length / 2:
            break
        G.set_material(G.cyl(f"ins_top.{k}", 0.026, 0.020, 0.030, (x, y, z + 0.012), verts=18, col=col), pm)
        G.set_material(G.cyl(f"ins_body.{k}", 0.040, 0.044, 0.055, (x, y, z + 0.052), verts=18, col=col), pm)
        G.set_material(G.torus(f"ins_skirt.{k}", 0.046, 0.014, (x, y, z + 0.082), col=col), pm)
        G.set_material(G.cyl(f"ins_pin.{k}", 0.011, 0.011, hang, (x, y, z + 0.09 + hang / 2), verts=8, col=col), im)
        G.set_material(G.box(f"ins_plate.{k}", (0.10, 0.10, 0.02), (x, y, z + 0.09 + hang), col=col), im)


def agent(chassis="surveyor", at=(0, 0, 0), yaw=0.0, pose="stand 0.5", lamp_w=600.0, aim_down=10.0,
          modules=None, name="AGENT", frame=None, emissive=3.0, wear=0.35, spot_deg=50.0):
    """The walker as agent_model builds it, with the three rig faults corrected: lamp
    re-aimed +X and tilted down, lamp white for every team, emissives BONE at <= 3."""
    cfg = P.default_config(chassis)
    if modules is not None:
        cfg.modules = modules
    cfg.skin = P.Skin("player", base=PLAYER_SHELL, chassis=PLAYER_CHASSIS, light=BONE,
                      light_strength=emissive, wear=wear, grime=0.4)
    built = build_agent(cfg, name=name, at=at)
    if yaw:
        R = Matrix.Rotation(yaw, 3, "Z")
        o = Vector(at)
        for e in built.feet:
            e.location = o + R @ (Vector(e.location) - o)
        built.look.location = o + R @ (Vector(built.look.location) - o)
        built.arm.rotation_euler.z = yaw
    mover = Mover(built)
    last = script(mover, pose)
    bpy.context.scene.frame_set(frame if frame is not None else last)
    if built.lamp is not None:
        built.lamp.rotation_euler = Euler((0, -math.pi / 2 + math.radians(aim_down), 0))
        built.lamp.data.energy = lamp_w
        built.lamp.data.color = LAMP_WHITE
        built.lamp.data.spot_size = math.radians(spot_deg)
        built.lamp.data.spot_blend = 0.4
        built.lamp.data.shadow_soft_size = 0.05
    for m in bpy.data.materials:
        if m.name.startswith("light_strip") or m.name.startswith("eye"):
            for nd in m.node_tree.nodes:
                if nd.type == "EMISSION":
                    nd.inputs["Strength"].default_value = emissive
                    nd.inputs["Color"].default_value = (*BONE, 1)
    return built


# ---------------------------------------------------------------------------------------
# the worked drive, copied from docs/art/ruins/ruins_probe.py (which cannot be imported)
# ---------------------------------------------------------------------------------------
def profile(hw=1.20, leg=1.20, nl=8, na=26):
    pts = [(hw, leg * k / nl) for k in range(nl + 1)]
    pts += [(hw * math.cos(math.pi * k / na), leg + hw * math.sin(math.pi * k / na)) for k in range(1, na)]
    pts += [(-hw, leg * (nl - k) / nl) for k in range(nl + 1)]
    return pts


def drive(length=20.0, hw=1.20, leg=1.20, scallop=0.055, round_m=1.6, col=None, seed=5, mat=None, x0=0.0):
    """Horseshoe 2.4 x 2.4 m, half-barrel shot-hole scars at 340 mm parallel to the
    advance, each 1.6 m round's pattern phase-offset from the last."""
    rng = random.Random(seed)
    pts = profile(hw, leg)
    s, norms = [0.0], []
    for i in range(1, len(pts)):
        s.append(s[-1] + math.dist(pts[i], pts[i - 1]))
    for i in range(len(pts)):
        a = pts[max(0, i - 1)]
        b = pts[min(len(pts) - 1, i + 1)]
        t = Vector((b[0] - a[0], b[1] - a[1]))
        t.normalize()
        norms.append(Vector((t.y, -t.x)))
    hole = 0.34
    nseg = int(length / 0.28)
    phases = {}
    bm = bmesh.new()
    rings = []
    for j in range(nseg + 1):
        x = -length / 2 + length * j / nseg
        rnd = int((x + length / 2) / round_m)
        ph = phases.setdefault(rnd, rng.random())
        ring = []
        for i, (py, pz) in enumerate(pts):
            k = 1.0 - abs(math.sin(math.pi * s[i] / hole + ph * 6.28))
            d = scallop * k + 0.018 * math.sin(x * 3.1 + s[i] * 2.2 + ph * 9) + rng.uniform(-0.008, 0.008)
            n = norms[i]
            ring.append(bm.verts.new((x + x0, py + n.x * d, max(0.005, pz + n.y * d))))
        rings.append(ring)
    for j in range(nseg):
        for i in range(len(pts) - 1):
            bm.faces.new((rings[j][i], rings[j][i + 1], rings[j + 1][i + 1], rings[j + 1][i]))
    o = G._mesh_object("drive_walls", bm, col=col, smooth=True)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.normals_make_consistent(inside=True)
    bpy.ops.object.mode_set(mode="OBJECT")
    G.set_material(o, mat)
    return o


def drive_floor(length=20.0, hw=1.20, col=None, mat=None, seed=6, x0=0.0, z=0.0):
    """Flat trammed floor with the 300 x 90 mm gutter down the -Y side."""
    rng = random.Random(seed)
    nx, ny = int(length / 0.18), 26
    bm = bmesh.new()
    grid = []
    for j in range(ny + 1):
        row = []
        y = -hw + 2 * hw * j / ny
        for i in range(nx + 1):
            x = -length / 2 + length * i / nx
            zz = z + rng.uniform(-0.012, 0.012) + 0.02 * math.sin(x * 1.7 + y * 3.0)
            if y < -hw + 0.30:
                zz -= 0.09 * math.sin(math.pi * min(1.0, (y + hw) / 0.30)) ** 0.6
            row.append(bm.verts.new((x + x0, y, zz)))
        grid.append(row)
    for j in range(ny):
        for i in range(nx):
            bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
    o = G._mesh_object("drive_floor", bm, col=col, smooth=True)
    G.set_material(o, mat)
    return o


def drive_furniture(length=20.0, hw=1.20, leg=1.20, col=None, rails=True, sockets=True, bolts=True,
                    plates=True, plate_every=4.8, polished=True, x0=0.0, seed=7, plate_text=None):
    """Rail on sleepers at 600 mm, timber-set sockets at 1.2 m, a bolt line at the
    springing, cast index plates every 4.8 m -- dark (ART-DIRECTION 6.5 deletes the glow)."""
    rng = random.Random(seed)
    iron = cast_iron("furniture_iron", rough=0.9, scale=5.0)
    dark = graphitised("socket_dark")
    if rails:
        track(length, x0=x0, y0=0.15, polished=polished, col=col)
    for k in range(int(length / 1.2)):
        x = x0 - length / 2 + 0.6 + k * 1.2
        for side in (1, -1):
            if sockets:
                G.set_material(G.box(f"socket.{k}.{side}", (0.16, 0.10, 0.20), (x, side * (hw - 0.02), leg + 0.10), col=col), dark)
            if bolts:
                G.set_material(G.cyl(f"bolt.{k}.{side}", 0.022, 0.022, 0.06, (x, side * (hw - 0.03), leg - 0.35),
                                     rot=(0, math.pi / 2, 0), verts=8, col=col), iron)
                G.set_material(G.cyl(f"bolthead.{k}.{side}", 0.035, 0.030, 0.02, (x, side * (hw - 0.055), leg - 0.35),
                                     rot=(math.pi / 2, 0, 0), verts=8, col=col), iron)
    if plates:
        for k in range(int(length / plate_every) + 1):
            x = x0 - length / 2 + 1.0 + k * plate_every
            if x > x0 + length / 2 - 0.5:
                break
            txt = plate_text or f"K{7 + k}-{41 + 8 * k}"
            plate((x, hw - 0.03, 1.40), yaw=0.0, text=txt, col=col, name=f"plate{k}")


# ---------------------------------------------------------------------------------------
# rigs, camera, settings
# ---------------------------------------------------------------------------------------
LOOK_CLEAR = "None"
LOOK_GAME = "AgX - Medium High Contrast"
STATE = {"look": LOOK_GAME, "exposure": 0.0, "volume": False}


def world(colour=(0, 0, 0), strength=0.0, fog=0.0, aniso=0.55):
    w = bpy.data.worlds.new("World")
    bpy.context.scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.inputs["Color"].default_value = (*colour, 1)
    bg.inputs["Strength"].default_value = strength
    nt.links.new(bg.outputs[0], out.inputs["Surface"])
    if fog > 0:
        v = nt.nodes.new("ShaderNodeVolumeScatter")
        v.inputs["Density"].default_value = fog
        v.inputs["Anisotropy"].default_value = aniso
        v.inputs["Color"].default_value = (*FOG, 1)
        nt.links.new(v.outputs[0], out.inputs["Volume"])
        # the resting fog renders fine at p2_env's coarse stepping (6.0 / 64); only the
        # LOCAL volumes (silt plume, water body, haze band) set STATE["volume"] and buy
        # the fine stepping. With it on for every fog frame a frame costs 3x.
    return w


def rig_clear(key=(4, -6, 7), aim=(0, 0, 0.6), energy=1000.0, size=3.0, grey=0.45, strength=1.0, exposure=0.0):
    """CLEAR: neutral grey world at 1.0 + one 3 m area key from about 45 deg high."""
    world((grey, grey, grey), strength)
    E.add_light("KEY", "AREA", key, energy, (1.0, 1.0, 1.0), size=size, aim=aim)
    STATE["look"] = LOOK_CLEAR
    STATE["exposure"] = exposure


def rig_insitu(fog=0.010, exposure=0.0):
    """IN-SITU: world strength 0, resting silt 0.008-0.012, nothing else."""
    world((0, 0, 0), 0.0, fog=fog)
    STATE["look"] = LOOK_GAME
    STATE["exposure"] = exposure


def bb_light(name, kelvin, energy, loc, size=0.3, kind="POINT"):
    """A source whose colour comes from a Blackbody node, not a hand RGB."""
    d = bpy.data.lights.new(name, kind)
    d.energy = energy
    d.shadow_soft_size = size
    d.use_nodes = True
    nt = d.node_tree
    em = next(n for n in nt.nodes if n.type == "EMISSION")
    bb = nt.nodes.new("ShaderNodeBlackbody")
    bb.inputs["Temperature"].default_value = kelvin
    nt.links.new(bb.outputs["Color"], em.inputs["Color"])
    o = bpy.data.objects.new(name, d)
    bpy.context.scene.collection.objects.link(o)
    o.location = Vector(loc)
    return o


def cam(loc, aim, focal=50.0, fstop=None, ortho=None):
    cd = bpy.data.cameras.new("CAM")
    cd.lens = focal
    if ortho:
        cd.type = "ORTHO"
        cd.ortho_scale = ortho
    cd.dof.use_dof = fstop is not None
    if fstop:
        cd.dof.aperture_fstop = fstop
        cd.dof.focus_distance = (Vector(loc) - Vector(aim)).length
    c = bpy.data.objects.new("CAM", cd)
    bpy.context.scene.collection.objects.link(c)
    c.location = Vector(loc)
    t = bpy.data.objects.new("CAM_aim", None)
    bpy.context.scene.collection.objects.link(t)
    t.location = Vector(aim)
    k = c.constraints.new("TRACK_TO")
    k.target = t
    k.track_axis = "TRACK_NEGATIVE_Z"
    k.up_axis = "UP_Y"
    bpy.context.scene.camera = c
    return c


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.unit_settings.system = "METRIC"
    STATE.update(look=LOOK_GAME, exposure=0.0, volume=False)


def render(out, samples, res):
    E.settings(samples=samples, res=res, look=STATE["look"], exposure=STATE["exposure"])
    cy = bpy.context.scene.cycles
    if STATE["volume"]:
        cy.volume_step_rate = 2.0
        cy.volume_max_steps = 192
    bpy.context.scene.render.filepath = os.path.abspath(out)
    bpy.ops.render.render(write_still=True)


# ---------------------------------------------------------------------------------------
# scenes shared by several shots
# ---------------------------------------------------------------------------------------
def natural_passage(width=3.4, height=4.2, length=22.0, rk=None, seed=5, rubble=12, open_ends=True, sink=0.7):
    """p2_env.passage keeps its tube 0.55 m clear of z=0 and relies on displacement to
    close the gap, which only works above ~3 m wide. Build taller and sink it, so the
    walls of a crawl meet the floor."""
    col = E.passage(width=width, height=height + sink - 0.55, length=length, mat=rk, seed=seed, rubble=rubble)
    tube = first(col, "passage")
    tube.location.z -= sink
    if open_ends:
        delete_ngons(tube)
    return col, tube


def core(col, x_cut, half_w, x_max=None):
    """Trim a passage's floor and rubble to a core: nothing before x_cut, nothing beyond
    half_w to either side. The section then reads as a sample of rock, not a pipe on a plain."""
    fl = first(col, "floor")
    bisect(fl, (x_cut, 0, 0), (-1, 0, 0))
    bisect(fl, (0, -half_w, 0), (0, -1, 0))
    bisect(fl, (0, half_w, 0), (0, 1, 0))
    if x_max is not None:
        bisect(fl, (x_max, 0, 0), (1, 0, 0))
    for o in list(col.objects):
        if o.name.startswith("rubble") and (o.location.x < x_cut + 0.3 or abs(o.location.y) > half_w - 0.3):
            bpy.data.objects.remove(o)


def shaft_chamber(rk, radius=6.0, height=8.5, sky_w=2600.0, disc=True):
    """The chamber under the aven: the only cold light in the cave. The aven is an open
    tube punched through the roof; the sky is an emissive disc at its top plus an area
    light. Landing plate on the floor where the kibble comes down (a guess)."""
    col = E.chamber(radius=radius, height=height, mat=rk, seed=11, aven=False, rubble=12)
    ch = first(col, "chamber")
    ax, ay, ar = 0.6, 0.4, 1.7
    punch(ch, (ax, ay, 0), (0, 0, 1), ar + 0.35)
    # the chamber's roof is at ~0.30 h + 0.914 r (+/- displacement); start the tube just
    # under it so it meets the punched hole rather than hanging into the room
    roof = height * 0.30 + radius * (height / (radius * 1.55)) - 1.0
    bpy.ops.mesh.primitive_cylinder_add(vertices=36, radius=ar, depth=16.0, location=(ax, ay, roof + 8.0))
    av = bpy.context.object
    av.name = "aven"
    for c in list(av.users_collection):
        c.objects.unlink(av)
    col.objects.link(av)
    delete_ngons(av)
    E._displace(av, 1.2, 0.55, depth=5)
    av.data.shade_smooth()
    bpy.context.view_layer.objects.active = av
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.flip_normals()
    bpy.ops.object.mode_set(mode="OBJECT")
    G.set_material(av, rk)
    top = roof + 16.0
    if disc:
        d = G.cyl("sky_disc", ar * 1.4, ar * 1.4, 0.02, (ax, ay, top + 0.4), verts=36, col=col)
        G.set_material(d, emit(SKY, 9.0, "sky"))
    E.add_light("SKY", "AREA", (ax, ay, top), sky_w, SKY, size=ar * 1.8, aim=(ax, ay, 0))
    # the landing: a cast plate where the kibble sets down
    G.set_material(G.box("landing", (1.6, 1.6, 0.05), (ax, ay, 0.03), bevel=0.01, col=col), cast_iron("landing_iron"))
    return col, (ax, ay, top)


def worked_drive(length=22.0, rk=None, x0=0.0, polished=True, plates=True, sockets=True, sets=None, failed_at=None, bus_z=None):
    col = G.new_collection("DRIVE")
    walls = drive(length=length, col=col, mat=rk, x0=x0)
    drive_floor(length=length, col=col, mat=rk, x0=x0)
    drive_furniture(length=length, col=col, polished=polished, plates=plates, sockets=sockets, x0=x0)
    if sets:
        tm = timber("set_timber")
        for x in sets:
            timber_set(x, col=col, mat=tm, failed=(failed_at is not None and abs(x - failed_at) < 1e-6), rock_mat=rk)
    if bus_z is not None:
        bus(length - 1.0, bus_z, x0=x0, y=0.0, col=col, hang=2.36 - bus_z - 0.1)
    return col, walls


def machine_ground(rk, radius=6.0, height=6.5, water_z=0.45, mouth_deg=None, mouth_len=12.0):
    """Deep machine ground: a pump chamber with the pump still under water, pipework up to
    a launder, a bolt ring at the springing, the Bus across the crown, rails in, one
    collapsed set at the mouth. Every part a casting. All of it a guess at the dressing;
    the list of parts is ART-DIRECTION 3.4."""
    col = E.chamber(radius=radius, height=height, mat=rk, seed=13, aven=False, rubble=10)
    ch = first(col, "chamber")
    iron = cast_iron("plant_iron")
    dark = graphitised("plant_graphite")
    steel = bearing_steel("plant_steel")
    # the pump: horizontal barrel on a plinth, flange, flywheel, half under water
    px, py = 2.5, 2.1
    G.set_material(G.box("plinth", (2.2, 1.2, 0.5), (px, py, 0.25), bevel=0.02, col=col), dark)
    G.set_material(G.cyl("pump_body", 0.46, 0.46, 1.7, (px, py, 0.85), rot=(0, math.pi / 2, 0), verts=24, bevel=0.02, col=col), iron)
    for k, dx in enumerate((-0.75, 0.0, 0.75)):
        G.set_material(G.cyl(f"pump_rib{k}", 0.52, 0.52, 0.08, (px + dx, py, 0.85), rot=(0, math.pi / 2, 0), verts=24, col=col), iron)
    G.set_material(G.cyl("pump_flange", 0.56, 0.56, 0.12, (px + 0.9, py, 0.85), rot=(0, math.pi / 2, 0), verts=24, col=col), iron)
    G.set_material(G.torus("flywheel", 0.95, 0.07, (px - 1.05, py, 1.0), rot=(0, math.pi / 2, 0), col=col), iron)
    for k in range(6):
        a = k * math.pi / 3
        G.set_material(G.cyl(f"spoke{k}", 0.035, 0.035, 1.8, (px - 1.05, py, 1.0), rot=(a, 0, 0), verts=8, col=col), iron)
    G.set_material(G.cyl("crank_shaft", 0.09, 0.09, 0.5, (px - 1.05, py, 1.0), rot=(0, math.pi / 2, 0), verts=12, col=col), steel)
    # pipework: from the pump up and back to the launder (behind the pump, in the +Y half,
    # so a cutaway from -Y keeps it and its posts)
    ly = py + 1.5
    pipe = [Vector((px + 1.0, py, 0.85)), Vector((px + 1.6, py, 0.85)), Vector((px + 1.6, py, 2.6)),
            Vector((px + 1.6, ly - 0.3, 2.9)), Vector((px + 0.4, ly, 3.1))]
    G.set_material(G.tube_along("pipe", pipe, 0.11, verts=12, col=col), iron)
    for i, p in enumerate(pipe[1:-1]):
        G.set_material(G.cyl(f"pipe_flange{i}", 0.16, 0.16, 0.06, p, verts=12, col=col), iron)
    # the launder: an iron trough on posts, running off into the dark
    G.set_material(G.box("launder", (7.0, 0.36, 0.30), (-1.2, ly, 3.1), rot=(0, 0.03, -0.12), bevel=0.01, col=col), iron)
    for k, x in enumerate((-4.0, -1.0, 2.0)):
        G.set_material(G.cyl(f"launder_post{k}", 0.05, 0.06, 2.95, (x, ly - 0.12 * (x + 1.2), 1.48), verts=8, col=col), dark)
    # bolt ring at the springing, all round
    for k in range(18):
        a = k * 2 * math.pi / 18
        r = radius * 0.86
        G.set_material(G.cyl(f"ring_bolt{k}", 0.03, 0.03, 0.10, (math.cos(a) * r, math.sin(a) * r, 2.3),
                             rot=(0, math.pi / 2, a), verts=8, col=col), iron)
        G.set_material(G.box(f"ring_plate{k}", (0.06, 0.16, 0.16), (math.cos(a) * r, math.sin(a) * r, 2.3), rot=(0, 0, a), col=col), iron)
    # the Bus, across the crown
    bus(radius * 1.5, 4.6, x0=0.0, y=-0.6, spacing=2.4, col=col, hang=0.9)
    # rails in from the mouth, one collapsed set on them
    track(9.0, x0=-6.5, y0=-1.3, polished=True, col=col)
    timber_set(-4.6, hw=1.2, leg=1.2, col=col, mat=timber("mg_timber"), failed=True, rock_mat=rk)
    for o in list(col.objects):
        if o.name.startswith(("post", "cap", "spall")):
            o.location.y += -1.3
    water_plane(water_z, size=radius * 3.2, col=col)
    if mouth_deg is not None:
        a = math.radians(mouth_deg)
        d = Vector((math.cos(a), math.sin(a), 0))
        punch(ch, (0, 0, 1.6), d, 1.8)
        mcol = E.passage(width=3.2, height=3.4, length=mouth_len, mat=rk, seed=8, rubble=0)
        tube = first(mcol, "passage")
        delete_ngons(tube)
        bisect(tube, (0.8, 0, 0), (-1, 0, 0))                # trim what would sit inside the chamber
        fl = first(mcol, "floor")
        bpy.data.objects.remove(fl)                         # the chamber floor already covers it
        tube.location = d * (radius * 0.9)
        tube.rotation_euler = (0, 0, a)
        return col, (d, a)
    return col, None


# ---------------------------------------------------------------------------------------
# SHOTS
# ---------------------------------------------------------------------------------------
SHOTS = {}


def shot(name):
    def deco(fn):
        SHOTS[name] = fn
        return fn
    return deco


# ---- B1 the shaft chamber --------------------------------------------------------------
@shot("b1_01_clear_cutaway")
def _():
    rk = rock("rk", albedo_hi=0.30, wet=0.35)
    col, (ax, ay, top) = shaft_chamber(rk, sky_w=1800.0, disc=False)
    for o in list(col.objects):
        if o.name.startswith(("chamber", "aven")):
            bisect(o, (0, -1.2, 0), (0, -1, 0))
    agent(at=(ax, ay, 0), yaw=math.radians(-60), lamp_w=0.0)
    ruler((ax + 1.6, ay - 1.2, 0.05))
    rig_clear(key=(6, -16, 14), aim=(ax, ay, 3), energy=9000.0, size=5.0, exposure=0.3)
    cam((0.4, -20.0, 7.5), (ax, ay + 0.5, 4.2), focal=32)


@shot("b1_02_clear_aven_only")
def _():
    rk = rock("rk", albedo_hi=0.30, wet=0.35)
    col, (ax, ay, top) = shaft_chamber(rk, sky_w=2600.0)
    for o in list(col.objects):
        if o.name.startswith(("chamber", "aven")):
            bisect(o, (0, -1.2, 0), (0, -1, 0))
    agent(at=(ax, ay, 0), yaw=math.radians(-60), lamp_w=0.0)
    rig_insitu(fog=0.006, exposure=3.0)
    STATE["look"] = LOOK_CLEAR
    cam((0.4, -20.0, 7.5), (ax, ay + 0.5, 4.2), focal=32)


@shot("b1_03_insitu_pool")
def _():
    rk = rock("rk", albedo_hi=0.30, wet=0.35)
    col, (ax, ay, top) = shaft_chamber(rk, sky_w=2600.0)
    agent(at=(ax, ay, 0), yaw=math.radians(-50), lamp_w=0.0, pose="stand 0.3; look 2.0,1.5,0.3 0.4 ride; stand 0.2")
    rig_insitu(fog=0.012)
    cam((ax - 3.4, ay - 3.0, 1.35), (ax, ay, 0.45), focal=40)


@shot("b1_04_insitu_leaving")
def _():
    rk = rock("rk", albedo_hi=0.30, wet=0.35)
    col, (ax, ay, top) = shaft_chamber(rk, sky_w=2600.0)
    agent(at=(ax + 2.2, ay - 0.2, 0), yaw=0.0, lamp_w=600.0, pose="stand 0.2; walk 2.0 0.45 0 trot", frame=36)
    rig_insitu(fog=0.012)
    cam((ax - 1.4, ay - 1.6, 1.1), (ax + 4.5, ay - 0.3, 0.3), focal=35)


@shot("b1_05_insitu_lookup")
def _():
    rk = rock("rk", albedo_hi=0.30, wet=0.35)
    col, (ax, ay, top) = shaft_chamber(rk, sky_w=2600.0)
    agent(at=(ax, ay, 0), yaw=math.radians(90), lamp_w=0.0)
    rig_insitu(fog=0.010)
    # from the floor beside the machine with a very wide lens: the machine's top-lit
    # shell in the lower frame, the lit throat of the aven and the disc above it. A
    # 20 mm from 2.4 m aimed at z = 6.5 puts the machine below the bottom of the frame.
    cam((ax + 0.15, ay - 1.35, 0.12), (ax, ay + 0.15, 1.7), focal=13)


# ---- B2 passages by width class --------------------------------------------------------
WIDTHS = {"crawl": (1.5, 1.3), "narrow": (2.1, 2.2), "passage": (2.7, 3.2), "hall": (3.9, 5.0)}


def _section(cls, chassis="surveyor"):
    w, h = WIDTHS[cls]
    rk = rock("rk", albedo_hi=0.30, wet=0.35)
    col, tube = natural_passage(width=w, height=h, length=14.0, rk=rk, rubble=6)
    bisect(tube, (-0.9, 0, 0), (-1, 0, 0))
    core(col, -0.9, w / 2 + 0.9)
    agent(chassis=chassis, at=(0.3, 0, 0), yaw=0.0, lamp_w=0.0)
    gauge_lines(-0.8, 8.0, y=0.0)
    ruler((-0.6, 0.0, 0.02), yaw=math.pi / 2)
    rig_clear(key=(-4, -3.5, 5.5), aim=(0.5, 0, h * 0.4), energy=1200.0, size=3.0)
    d = 1.9 + 1.25 * h
    cam((-0.9 - d, 0.0, h * 0.45), (0.6, 0, h * 0.40), focal=32)


for _cls in WIDTHS:
    SHOTS[f"b2_01_clear_section_{_cls}"] = (lambda c: (lambda: _section(c)))(_cls)


@shot("b2_02_clear_scout_crawl")
def _():
    w, h = WIDTHS["crawl"]
    rk = rock("rk", albedo_hi=0.30, wet=0.35)
    col, tube = natural_passage(width=w, height=h, length=14.0, rk=rk, rubble=6)
    bisect(tube, (-0.9, 0, 0), (-1, 0, 0))
    core(col, -0.9, w / 2 + 0.9)
    agent(chassis="scout", at=(0.6, 0, 0), yaw=0.0, lamp_w=0.0)
    gauge_lines(-0.8, 8.0, y=0.0)
    rig_clear(key=(-4, -3.5, 5.5), aim=(0.5, 0, 0.5), energy=1200.0, size=3.0)
    cam((-3.4, -0.9, 0.95), (1.2, 0, 0.35), focal=35)


@shot("b2_03_clear_hauler_crawl")
def _():
    w, h = WIDTHS["crawl"]
    rk = rock("rk", albedo_hi=0.30, wet=0.35)
    col, tube = natural_passage(width=w, height=h, length=14.0, rk=rk, rubble=6)
    bisect(tube, (-0.9, 0, 0), (-1, 0, 0))
    core(col, -0.9, w / 2 + 0.9)
    agent(chassis="hauler", at=(0.6, 0, 0), yaw=0.0, lamp_w=0.0)
    gauge_lines(-0.8, 8.0, y=0.0)
    rig_clear(key=(-4, -3.5, 5.5), aim=(0.5, 0, 0.5), energy=1200.0, size=3.0)
    cam((-3.4, -0.9, 0.95), (1.2, 0, 0.35), focal=35)


@shot("b2_04_insitu_crawl_lamp")
def _():
    w, h = WIDTHS["crawl"]
    rk = rock("rk", albedo_hi=0.30, wet=0.35)
    natural_passage(width=w, height=h, length=18.0, rk=rk, rubble=8)
    agent(at=(0, 0, 0), yaw=0.0, lamp_w=600.0)
    rig_insitu(fog=0.010)
    cam((-1.9, -0.25, 0.60), (2.5, 0, 0.15), focal=26)


@shot("b2_05_insitu_hall_lamp")
def _():
    w, h = 4.4, 5.6
    rk = rock("rk", albedo_hi=0.30, wet=0.35)
    natural_passage(width=w, height=h, length=32.0, rk=rk, rubble=14)
    agent(at=(0, 0, 0), yaw=0.0, lamp_w=600.0)
    rig_insitu(fog=0.010)
    cam((-1.9, -0.25, 0.60), (2.5, 0, 0.15), focal=26)


# ---- B3 chambers ------------------------------------------------------------------------
@shot("b3_01_clear_cutaway")
def _():
    rk = rock("rk", albedo_hi=0.30, wet=0.35, grid=1.2)
    col = E.chamber(radius=7.2, height=8.0, mat=rk, seed=11, rubble=14)
    bisect(first(col, "chamber"), (0, -2.0, 0), (0, -1, 0))
    fl = first(col, "floor")
    bisect(fl, (0, -8.0, 0), (0, -1, 0))
    bisect(fl, (-8.5, 0, 0), (-1, 0, 0))
    bisect(fl, (8.5, 0, 0), (1, 0, 0))
    agent(at=(0, 0, 0), yaw=math.radians(-40), lamp_w=0.0)
    ruler((1.2, -1.2, 0.05))
    rig_clear(key=(6, -18, 15), aim=(0, 0, 3), energy=12000.0, size=6.0, exposure=0.3)
    cam((0.5, -23.0, 8.5), (0, 1.0, 3.2), focal=32)


@shot("b3_02_insitu_one_lamp")
def _():
    rk = rock("rk", albedo_hi=0.30, wet=0.35)
    E.chamber(radius=7.2, height=8.0, mat=rk, seed=11, rubble=14)
    agent(at=(-4.2, 0, 0), yaw=0.0, lamp_w=600.0)
    rig_insitu(fog=0.010)
    cam((-6.0, -1.1, 1.3), (0.0, 0.0, 0.5), focal=32)


@shot("b3_03_insitu_beacon_far")
def _():
    rk = rock("rk", albedo_hi=0.30, wet=0.35)
    E.chamber(radius=7.2, height=8.0, mat=rk, seed=11, rubble=14)
    agent(at=(-4.2, 0, 0), yaw=0.0, lamp_w=600.0)
    beacon((5.4, 1.1, 0.0))
    rig_insitu(fog=0.010)
    cam((-6.0, -1.1, 1.3), (0.0, 0.0, 0.5), focal=32)


# ---- B4 the waterline ------------------------------------------------------------------
def _flooded_passage(rk_kw=None, wl=0.20, tilt_deg=4.0):
    rk = rock("rk", albedo_hi=0.30, wet=0.6, waterline=wl, **(rk_kw or {}))
    col, tube = natural_passage(width=3.0, height=3.2, length=18.0, rk=rk, rubble=8, sink=1.0)
    fl = first(col, "floor")
    fl.rotation_euler.y = math.radians(tilt_deg)
    for o in list(col.objects):
        if o.name.startswith("rubble") and o.location.x > 3.0:
            o.location.z -= 0.25 + 0.04 * o.location.x
    wp = water_plane(wl, size=40.0, center=(6, 0), col=col)
    return col, tube, fl, wp


@shot("b4_01_clear_section")
def _():
    col, tube, fl, wp = _flooded_passage()
    for o in (tube, wp, fl):
        bisect(o, (0, -0.25, 0), (0, -1, 0))
    bisect(fl, (0, 2.6, 0), (0, 1, 0))
    for o in list(col.objects):
        if o.name.startswith("rubble") and o.location.y < 0.1:
            bpy.data.objects.remove(o)
    # the water: a volume whose -Y face is the cut plane, so the camera looks INTO it
    water_box(0.20, -3.0, 16.0, -0.25, 1.6, depth=1.6, col=col, scatter=0.03, absorb=0.05)
    STATE["volume"] = True
    # the bank: the 4 deg tilt puts the floor above the 0.20 m line for x < -3
    agent(at=(-4.6, 0.45, 0.30), yaw=0.0, lamp_w=0.0)
    ruler((-3.4, 0.9, 0.26))
    rig_clear(key=(0, -7, 5), aim=(1.5, 0.4, 0.3), energy=2400.0, size=3.5)
    # side-on and low: the profile of dry rock / crust / surface / submerged rock
    cam((1.2, -7.4, 0.95), (1.4, 0.4, 0.10), focal=35)


@shot("b4_02_clear_grazing")
def _():
    col, tube, fl, wp = _flooded_passage()
    rig_clear(key=(9, -1.0, 2.6), aim=(11, 0, 0.3), energy=900.0, size=2.0)
    cam((0.6, 0.15, 0.70), (12.0, 0.0, 0.15), focal=32)


@shot("b4_03_insitu_pool_returns")
def _():
    col, tube, fl, wp = _flooded_passage()
    # on the bank (floor above the 0.20 m line for x < -3), looking down the flooded
    # passage: the pool lands on the water 3-4 m ahead and the mirror throws it on up
    # the far wall and the roof -- light going where the machine did not point it
    agent(at=(-4.6, 0.3, 0.30), yaw=0.0, lamp_w=600.0, aim_down=9.0)
    rig_insitu(fog=0.010)
    cam((-6.4, -1.5, 1.05), (0.5, 0.2, 0.55), focal=30)


def _wet_floor(wet):
    rk = rock("rk", albedo_hi=0.30, wet=wet, wet_rough=0.10)
    natural_passage(width=3.2, height=3.8, length=20.0, rk=rk, rubble=8)
    agent(at=(0, 0, 0), yaw=0.0, lamp_w=600.0, aim_down=12.0)
    rig_insitu(fog=0.008)
    cam((5.6, 0.35, 0.32), (0.0, 0.0, 0.30), focal=40)


@shot("b4_04_insitu_wet_streak")
def _():
    _wet_floor(0.95)


@shot("b4_05_insitu_dry_same")
def _():
    _wet_floor(0.0)


# ---- B5 below the waterline -----------------------------------------------------------
def _flooded_drive(wl=1.1, length=22.0):
    rk = rock("rk", albedo_hi=0.30, wet=0.9, waterline=wl, dark=0.6)
    col, walls = worked_drive(length=length, rk=rk, plates=False)
    wp = water_plane(wl, size=length + 6, col=col)
    wb = water_box(wl, -length / 2 - 2, length / 2 + 2, -1.6, 1.6, depth=1.6, col=col)
    return col, wp, wb


@shot("b5_01a_clear_above")
def _():
    col, wp, wb = _flooded_drive()
    bpy.data.objects.remove(wb)
    rig_clear(key=(-5.0, -0.3, 2.2), aim=(3, 0, 1.0), energy=260.0, size=1.0, exposure=0.6)
    cam((-7.5, 0.25, 1.85), (6.0, 0.0, 1.15), focal=30)


@shot("b5_01b_clear_below")
def _():
    col, wp, wb = _flooded_drive()
    agent(chassis="swimmer", at=(-3.2, 0.1, 0), yaw=math.radians(150), lamp_w=0.0)
    rig_clear(key=(-5.0, -0.3, 2.2), aim=(3, 0, 0.5), energy=260.0, size=1.0, exposure=0.6)
    STATE["volume"] = True
    cam((-7.5, 0.25, 0.55), (6.0, 0.0, 0.45), focal=30)


@shot("b5_02_insitu_swimmer_lamp")
def _():
    col, wp, wb = _flooded_drive()
    agent(chassis="swimmer", at=(0, 0.1, 0), yaw=0.0, lamp_w=600.0, aim_down=8.0,
          modules={"face": "active_sonar", "eye": "optical", "side_l": "passive_acoustic", "side_r": "passive_acoustic",
                   "top_r": "beacon_rack", "belly": "cargo_bay"},
          pose="stand 0.2; walk 1.6 0.35 0 walk", frame=30)
    plume = G.sphere("plume", 1.0, (-0.5, 0.1, 0.35), seg=16)
    plume.scale = (1.6, 0.9, 0.6)
    G.set_material(plume, silt_volume(0.09, "silt_walk"))
    rig_insitu(fog=0.0, exposure=1.6)
    STATE["volume"] = True
    cam((-1.9, -0.9, 0.62), (2.6, 0.0, 0.25), focal=30)


@shot("b5_03_insitu_from_above")
def _():
    col, wp, wb = _flooded_drive()
    agent(chassis="swimmer", at=(1.0, 0.1, 0), yaw=math.radians(20), lamp_w=600.0, aim_down=8.0,
          modules={"face": "active_sonar", "eye": "optical", "side_l": "passive_acoustic", "side_r": "passive_acoustic",
                   "top_r": "beacon_rack", "belly": "cargo_bay"})
    rig_insitu(fog=0.006, exposure=0.8)
    STATE["volume"] = True
    cam((-3.8, -0.7, 1.95), (1.2, 0.2, 0.9), focal=32)


@shot("b5_04_clear_light_death")
def _():
    col, wp, wb = _flooded_drive()
    white = flat((0.8, 0.8, 0.8), 0.7, "white_ball")
    for k in range(1, 8):
        G.set_material(G.sphere(f"ball{k}", 0.14, (k * 1.0 - 0.5, 0.0, 0.55), seg=16), white)
    E.add_light("DIVE", "SPOT", (-1.6, 0.0, 0.62), 600.0, LAMP_WHITE, size=0.05, spot_deg=55, aim=(6, 0, 0.5))
    rig_insitu(fog=0.0, exposure=1.0)
    STATE["volume"] = True
    STATE["look"] = LOOK_CLEAR
    cam((-1.7, -0.55, 0.75), (4.0, 0.0, 0.5), focal=28)


# ---- B6 silt ----------------------------------------------------------------------------
def _silt(density, walking, cam_side=True, big=False):
    rk = rock("rk", albedo_hi=0.30, wet=0.35)
    col, tube = natural_passage(width=4.0, height=4.6, length=22.0, rk=rk, rubble=10)
    if cam_side:
        bisect(tube, (0, -1.3, 0), (0, -1, 0))     # the near wall is behind the camera anyway
    if walking:
        agent(at=(-0.4, 0, 0), yaw=0.0, lamp_w=600.0, pose="stand 0.2; walk 1.6 0.45 0 trot", frame=30)
    else:
        agent(at=(0, 0, 0), yaw=0.0, lamp_w=600.0)
    if density > 0:
        pl = G.sphere("plume", 1.0, (-0.55, 0.0, 0.40), seg=16)
        pl.scale = (2.6, 1.5, 1.15) if big else (2.0, 1.1, 0.85)
        G.set_material(pl, silt_volume(density, "silt"))
    rig_insitu(fog=0.008, exposure=0.4)
    STATE["volume"] = True
    if cam_side:
        cam((1.6, -3.6, 1.05), (1.6, 0.0, 0.35), focal=30)
    else:
        cam((-2.3, -0.55, 0.95), (3.0, 0.0, 0.15), focal=32)


SHOTS["b6_01a_insitu_stopped"] = lambda: _silt(0.0, False)
SHOTS["b6_01b_insitu_walking"] = lambda: _silt(0.05, True)
SHOTS["b6_01c_insitu_blinded"] = lambda: _silt(0.15, True, big=True)
SHOTS["b6_02_insitu_plume_behind"] = lambda: _silt(0.05, True, cam_side=False)


# ---- B7 rock types ---------------------------------------------------------------------
@shot("b7_01_clear_swatches")
def _():
    ground = G.plane("ground", 12, (0, 0, 0))
    G.set_material(ground, flat((0.35, 0.35, 0.35), 0.8, "ground"))
    fr = (3.0, 8.0, 14.0)
    bumps = (0.30, 0.6, 0.9)
    for row, (lo, hi) in enumerate(((0.12, 0.24), (0.03, 0.34))):
        for cidx, f in enumerate(fr):
            m = rock(f"rk_{row}_{cidx}", albedo_lo=lo, albedo_hi=hi, wet=0.35, fracture_scale=f, bump=bumps[cidx],
                     bed_scale=1.4, crack=0.35 + 0.25 * cidx)
            o = G.box(f"slab_{row}_{cidx}", (1.1, 0.14, 0.75), (-1.3 + cidx * 1.3, row * 0.9 - 0.2, 0.375 + row * 0.55), bevel=0.01)
            E._displace(o, 0.5, 0.05, depth=4)
            G.set_material(o, m)
    # a swatch wall wants a RAKING key: small, low, from the side, so the bump reads.
    # The 3 m soft key of the other CLEAR frames turns every rock into plaster.
    rig_clear(key=(-4.5, -1.2, 1.6), aim=(0, 0, 0.7), energy=700.0, size=0.5, grey=0.30, strength=0.6)
    cam((0.0, -5.0, 2.1), (0.0, 0.3, 0.75), focal=45)


@shot("b7_02_clear_three_values")
def _():
    ground = G.plane("ground", 12, (0, 0, 0))
    G.set_material(ground, flat((0.35, 0.35, 0.35), 0.8, "ground"))
    specs = [("dry", dict(albedo_lo=0.20, albedo_hi=0.42, wet=0.0)),
             ("wet", dict(albedo_lo=0.13, albedo_hi=0.30, wet=1.0, wet_rough=0.10)),
             ("submerged", dict(albedo_lo=0.07, albedo_hi=0.16, wet=1.0, wet_rough=0.10))]
    for i, (nm, kw) in enumerate(specs):
        o = G.box(f"slab_{nm}", (1.1, 0.14, 0.75), (-1.3 + i * 1.3, 0.0, 0.375), bevel=0.01)
        E._displace(o, 0.5, 0.05, depth=4)
        G.set_material(o, rock(f"rk_{nm}", bed_scale=1.4, crack=0.4, **kw))
    wb = G.box("sub_water", (1.3, 0.5, 0.85), (1.3, -0.05, 0.425))
    G.set_material(wb, water_surface("ws"))
    rig_clear(key=(-4.5, -1.5, 1.8), aim=(0, 0, 0.5), energy=800.0, size=0.6, grey=0.30, strength=0.6)
    cam((0.0, -4.4, 1.5), (0.0, 0.0, 0.42), focal=50)


def _rock_type(absorbent):
    if absorbent:
        rk = rock("rk", albedo_lo=0.05, albedo_hi=0.16, wet=0.15, fracture_scale=14.0, bump=0.95, bed_scale=1.6, crack=0.7)
    else:
        rk = rock("rk", albedo_lo=0.03, albedo_hi=0.34, wet=0.6, fracture_scale=3.0, bump=0.35, bed_scale=0.7, crack=0.4)
    natural_passage(width=3.2, height=4.0, length=22.0, rk=rk, rubble=10, seed=9)
    agent(at=(0, 0, 0), yaw=0.0, lamp_w=600.0)
    rig_insitu(fog=0.010)
    cam((-2.4, -0.8, 1.2), (2.4, 0.0, 0.3), focal=32)


SHOTS["b7_03_insitu_absorbent"] = lambda: _rock_type(True)
SHOTS["b7_04_insitu_reflective"] = lambda: _rock_type(False)


# ---- B8 magnetic rock: the negative concept --------------------------------------------
def _magnetic(seed):
    rk = rock("rk", albedo_hi=0.30, wet=0.35)
    natural_passage(width=3.2, height=4.0, length=20.0, rk=rk, rubble=9, seed=seed)
    agent(at=(0, 0, 0), yaw=math.radians(35), lamp_w=600.0, pose="stand 0.3; look 1.4,1.2,0.6 0.4 ride; stand 0.2")
    rig_insitu(fog=0.010)
    cam((-2.1, -0.85, 1.15), (1.2, 0.9, 0.55), focal=32)


SHOTS["b8_01a_insitu_noisy"] = lambda: _magnetic(21)
SHOTS["b8_01b_insitu_deposit"] = lambda: _magnetic(22)


# ---- B9 unstable ground ----------------------------------------------------------------
def _sets_drive():
    rk = rock("rk", albedo_hi=0.30, wet=0.5, dark=0.3)
    col, walls = worked_drive(length=16.0, rk=rk, sets=(-2.4, -1.2, 0.0, 1.2, 2.4), failed_at=0.0, plates=False)
    joint((0.3, 0.2, 2.36), 1.8, yaw=0.5, tilt=0.15, col=col)
    return col, walls


@shot("b9_01_clear_sets")
def _():
    col, walls = _sets_drive()
    bisect(walls, (0, -0.35, 0), (0, -1, 0))
    agent(at=(-3.2, 0.15, 0), yaw=0.0, lamp_w=0.0)
    rig_clear(key=(-2.5, -6.5, 6.5), aim=(0, 0, 1.2), energy=1700.0, size=3.0)
    cam((-1.6, -7.0, 2.4), (0.0, 0.0, 1.15), focal=40)


@shot("b9_02_insitu_failed_set")
def _():
    col, walls = _sets_drive()
    agent(at=(-3.6, 0.15, 0), yaw=0.0, lamp_w=600.0)
    rig_insitu(fog=0.010)
    cam((-5.6, -0.85, 1.15), (0.0, 0.0, 0.6), focal=36)


def _fracture_passage():
    rk = rock("rk", albedo_lo=0.04, albedo_hi=0.26, wet=0.3, fracture_scale=13.0, bump=0.9, bed_scale=2.2)
    col, tube = natural_passage(width=3.2, height=3.8, length=20.0, rk=rk, rubble=6, seed=17)
    for i, x in enumerate((1.0, 2.2, 3.4, 4.6)):
        joint((x, 1.15, 1.6 + 0.1 * i), 2.4, yaw=0.0, tilt=math.radians(62), col=col)
    rng = random.Random(3)
    for i in range(14):
        r = rng.uniform(0.06, 0.26)
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=r, location=(rng.uniform(0.5, 5.5), rng.uniform(0.2, 1.3), r * 0.45))
        o = bpy.context.object
        o.scale = (rng.uniform(0.8, 1.8), rng.uniform(0.7, 1.3), rng.uniform(0.3, 0.6))
        o.rotation_euler = (rng.uniform(0, 3), rng.uniform(0, 3), rng.uniform(0, 3))
        o.data.shade_flat()
        G.set_material(o, rk)
    return col, tube


@shot("b9_03_insitu_fracture_set")
def _():
    _fracture_passage()
    agent(at=(-1.6, -0.5, 0), yaw=math.radians(18), lamp_w=600.0, aim_down=4.0)
    rig_insitu(fog=0.010)
    cam((-3.6, -0.8, 1.15), (2.4, 0.6, 0.9), focal=32)


@shot("b9_04_clear_fracture_set")
def _():
    col, tube = _fracture_passage()
    bisect(tube, (0, -0.8, 0), (0, -1, 0))
    agent(at=(-1.0, -0.5, 0), yaw=math.radians(18), lamp_w=0.0)
    rig_clear(key=(0, -6, 6), aim=(2.5, 0.5, 1.2), energy=2600.0, size=3.0)
    cam((0.5, -7.5, 2.6), (2.5, 0.6, 1.2), focal=40)


# ---- B10 thermal layering --------------------------------------------------------------
def _thermal(clear, up=True, condensation=False):
    layer = 1.5
    rk = rock("rk", albedo_hi=0.30, wet=(0.9 if condensation else 0.35), wet_above_z=(layer if condensation else None))
    col, tube = natural_passage(width=4.0, height=3.8, length=20.0, rk=rk, rubble=8)
    if not condensation:
        bisect(tube, (0, -1.3, 0), (0, -1, 0))
        hz = G.box("haze", (20.0, 3.6, 0.30), (6.0, 0.0, layer))
        G.set_material(hz, haze_volume(0.16 if clear else 0.12, "haze"))
    if condensation:
        # the pool has to straddle the layer ON THE WALL: head turned to the wall at 1.5 m
        pose = "stand 0.3; look 3.0,1.3,1.5 0.4 ride; stand 0.2"
        aim_down = -4.0
    else:
        pose = "stand 0.3; look 3.0,0.0,1.9 0.4 ride; stand 0.2" if up else "stand 0.5"
        aim_down = -6.0 if up else 10.0
    agent(at=(0, 0, 0), yaw=0.0, lamp_w=600.0, aim_down=aim_down, pose=pose)
    if clear:
        # a dim studio, so the band reads as a band AND the beam still flares inside it
        rig_clear(key=(-1, -6, 5), aim=(2, 0, 1.3), energy=380.0, size=3.0, grey=0.22, strength=0.35)
        STATE["volume"] = True
    else:
        rig_insitu(fog=0.006)
        STATE["volume"] = True
    if condensation:
        # behind-left, near the lamp's line, so the wet upper wall returns its specular
        cam((-2.2, -0.5, 0.9), (3.0, 1.3, 1.5), focal=35)
    elif clear:
        # three-quarter from behind-left and low, along the passage: the beam leaves the
        # head, crosses the slab at ~2 m and is gone above it
        cam((-4.0, -5.0, 0.7), (2.5, 0.4, 1.35), focal=32)
    else:
        cam((1.8, -3.6, 1.3), (1.8, 0.0, 1.25), focal=32)


SHOTS["b10_01_clear_band"] = lambda: _thermal(True)
SHOTS["b10_02_insitu_lamp_up"] = lambda: _thermal(False)
SHOTS["b10_03_insitu_condensation"] = lambda: _thermal(False, up=False, condensation=True)


# ---- B11 depth: shallow / middle / deep ------------------------------------------------
CAM_INSITU = ((-2.6, -0.9, 1.2), (2.0, 0.0, 0.35), 32)
CAM_CLEAR = ((-1.5, -6.5, 3.0), (1.5, 0.0, 1.0), 40)


def _depth_shallow(clear):
    rk = rock("rk", albedo_hi=0.30, wet=0.25, dark=0.0)
    col, tube = natural_passage(width=3.4, height=4.2, length=22.0, rk=rk, rubble=12)
    agent(at=(0, 0, 0), yaw=0.0, lamp_w=(0.0 if clear else 600.0))
    for i, (x, y) in enumerate(((2.6, 0.7), (6.2, -0.5), (9.8, 0.6))):
        beacon((x, y, 0.0), name=f"beacon{i}", pilot=True)
    if clear:
        bisect(tube, (0, -0.9, 0), (0, -1, 0))
        rig_clear(key=(-1, -6, 6), aim=(1.5, 0, 1.0), energy=2600.0, size=3.0)
        cam(*CAM_CLEAR)
    else:
        rig_insitu(fog=0.010)
        cam(*CAM_INSITU)


def _depth_middle(clear):
    rk = rock("rk", albedo_hi=0.30, wet=0.6, dark=0.5)
    col, walls = worked_drive(length=22.0, rk=rk, sets=(-3.6, -2.4, 3.6, 4.8), plates=True)
    agent(at=(0, 0.15, 0), yaw=0.0, lamp_w=(0.0 if clear else 600.0))
    if clear:
        bisect(walls, (0, -0.35, 0), (0, -1, 0))
        rig_clear(key=(-1, -6, 6), aim=(1.5, 0, 1.0), energy=2600.0, size=3.0)
        cam(*CAM_CLEAR)
    else:
        rig_insitu(fog=0.010)
        cam(*CAM_INSITU)


def _depth_deep(clear):
    rk = rock("rk", albedo_hi=0.30, wet=0.9, dark=1.0)
    col, mouth = machine_ground(rk, radius=6.0, height=6.5, water_z=0.30, mouth_deg=25.0)
    # in-situ: turned toward the pump so the lamp lands on iron; the camera moved off the
    # line to the winch source (the first version had the flywheel exactly in front of it)
    agent(at=(0, 0, 0), yaw=(0.0 if clear else math.radians(35)), lamp_w=(0.0 if clear else 600.0))
    d, a = mouth
    if clear:
        # its own camera: the same 40 mm three-quarter as the other two, pulled back to
        # hold a 12 m room, the near half cut away and its loose iron culled
        bisect(first(col, "chamber"), (0, -3.6, 0), (0, -1, 0))
        cull(col, -3.4)
        rig_clear(key=(-2, -12, 9), aim=(1.5, 0.5, 1.5), energy=7000.0, size=4.0, exposure=0.2)
        cam((-2.5, -12.5, 4.6), (1.2, 0.6, 1.4), focal=40)
    else:
        rig_insitu(fog=0.010)
        bb_light("WINCH", 2400.0, 3000.0, d * 10.5 + Vector((-2.4 * d.y, 2.4 * d.x, 3.0)), size=0.8)
        cam((-2.0, -2.4, 1.2), (2.2, 1.0, 0.6), focal=32)


SHOTS["b11_01a_clear_shallow"] = lambda: _depth_shallow(True)
SHOTS["b11_01b_clear_middle"] = lambda: _depth_middle(True)
SHOTS["b11_01c_clear_deep"] = lambda: _depth_deep(True)
SHOTS["b11_02a_insitu_shallow"] = lambda: _depth_shallow(False)
SHOTS["b11_02b_insitu_middle"] = lambda: _depth_middle(False)
SHOTS["b11_02c_insitu_deep"] = lambda: _depth_deep(False)


# ---- B12 the worked drive --------------------------------------------------------------
def _drive_scene():
    rk = rock("rk", albedo_hi=0.30, wet=0.55, dark=0.45)
    return worked_drive(length=22.0, rk=rk, plates=True)


@shot("b12_01_clear_down_drive")
def _():
    col, walls = _drive_scene()
    agent(at=(0.0, 0.15, 0), yaw=0.0, lamp_w=0.0)
    ruler((-2.4, -0.55, 0.0))
    E.add_light("FILL", "AREA", (-5.0, 0.0, 2.25), 260.0, (1, 1, 1), size=1.2, aim=(2, 0, 0.2))
    rig_clear(key=(-9.0, -0.6, 2.2), aim=(0, 0, 0.6), energy=300.0, size=1.2, exposure=0.4)
    cam((-7.6, 0.3, 1.5), (4.0, 0.0, 0.7), focal=32)


@shot("b12_02_clear_section_endon")
def _():
    col, walls = _drive_scene()
    bisect(walls, (0.9, 0, 0), (-1, 0, 0))
    for o in list(col.objects):
        if o.name.startswith(("sleeper", "rail", "socket", "bolt", "plate")) and o.location.x < 0.9:
            bpy.data.objects.remove(o)
    agent(at=(2.4, 0.15, 0), yaw=0.0, lamp_w=0.0)
    ruler((1.2, -0.7, 0.0))
    rig_clear(key=(-3.5, -3.5, 5.0), aim=(2.0, 0, 1.0), energy=1600.0, size=3.0)
    cam((-4.4, 0.0, 1.35), (2.5, 0.0, 1.05), focal=32)


@shot("b12_03_insitu_drive_lamp")
def _():
    col, walls = _drive_scene()
    agent(at=(-4.0, 0.15, 0), yaw=0.0, lamp_w=600.0)
    rig_insitu(fog=0.010)
    cam((-6.3, -0.95, 1.15), (0.5, 0.15, 0.45), focal=36)


@shot("b12_04_insitu_machine_height")
def _():
    col, walls = _drive_scene()
    agent(at=(-3.8, 0.15, 0), yaw=0.0, lamp_w=600.0)
    rig_insitu(fog=0.010)
    cam((-5.6, 0.15, 0.42), (6.0, 0.15, 0.25), focal=30)


# ---- B13 rails polished by use ---------------------------------------------------------
@shot("b13_01_clear_railhead")
def _():
    col, walls = _drive_scene()
    # the drive is enclosed: a key outside its wall lights nothing (the first version was
    # a black frame). Cut the near wall away and rake the key across the rail from inside.
    bisect(walls, (0, -0.35, 0), (0, -1, 0))
    rig_clear(key=(-0.9, -1.9, 1.4), aim=(0.0, -0.15, 0.12), energy=260.0, size=0.8, exposure=0.3)
    cam((0.8, -1.05, 0.48), (0.0, -0.10, 0.11), focal=60)


def _rails_long(cam_z):
    rk = rock("rk", albedo_hi=0.30, wet=0.55, dark=0.45)
    worked_drive(length=34.0, rk=rk, plates=True)
    agent(at=(-11.0, 0.15, 0), yaw=0.0, lamp_w=600.0, aim_down=7.0)
    rig_insitu(fog=0.008)
    cam((-12.4, 0.15, cam_z), (4.0, 0.15, 0.15), focal=38)


SHOTS["b13_02_insitu_rails_long"] = lambda: _rails_long(0.95)
SHOTS["b13_03_insitu_machine_height"] = lambda: _rails_long(0.42)


@shot("b13_04_clear_gauge_topdown")
def _():
    col, walls = _drive_scene()
    bisect(walls, (0, 0, 2.05), (0, 0, 1))
    agent(at=(0.9, 0.15, 0), yaw=0.0, lamp_w=0.0)
    ruler((-1.4, -0.6, 0.0))
    rig_clear(key=(1, -2, 6), aim=(0, 0, 0), energy=1200.0, size=3.0)
    cam((0.0, 0.15, 6.0), (0.0, 0.15, 0.0), focal=50, ortho=3.4)


# ---- B14 the Bus as an object ----------------------------------------------------------
def _bus_drive(length=22.0):
    rk = rock("rk", albedo_hi=0.30, wet=0.7, dark=0.6)
    return worked_drive(length=length, rk=rk, plates=False, bus_z=2.02)


@shot("b14_01_clear_conductor")
def _():
    col, walls = _bus_drive()
    bisect(walls, (0, -0.35, 0), (0, -1, 0))
    agent(at=(-1.0, 0.15, 0), yaw=0.0, lamp_w=0.0)
    rig_clear(key=(-3, -6, 6.5), aim=(1, 0, 1.6), energy=2400.0, size=3.0)
    cam((-2.0, -6.0, 2.6), (1.5, 0.0, 1.5), focal=40)


@shot("b14_02_clear_insulator")
def _():
    col, walls = _bus_drive()
    bisect(walls, (0, -0.35, 0), (0, -1, 0))
    rig_clear(key=(0.6, -1.4, 3.0), aim=(0.0, 0.0, 2.05), energy=260.0, size=1.2)
    x = -11.0 + 1.2 + 4 * 2.4
    cam((x + 0.55, -0.75, 2.25), (x, 0.0, 2.06), focal=85)


@shot("b14_03_insitu_row")
def _():
    col, walls = _bus_drive(length=30.0)
    agent(at=(-6.0, 0.15, 0), yaw=0.0, lamp_w=600.0, aim_down=0.0, pose="stand 0.3; look 6.0,0.0,2.2 0.4 ride; stand 0.2")
    rig_insitu(fog=0.010)
    cam((-7.6, -0.75, 0.95), (1.0, 0.0, 1.85), focal=35)


# ---- B15 survey plates -----------------------------------------------------------------
def _plate_drive():
    rk = rock("rk", albedo_hi=0.30, wet=0.5, dark=0.4)
    col, walls = worked_drive(length=12.0, rk=rk, plates=False)
    return col, walls


@shot("b15_01_clear_plate_macro")
def _():
    col, walls = _plate_drive()
    plate((0.0, 1.17, 1.40), text="K7-41", col=col, name="p_deep")
    rig_clear(key=(0.5, 0.3, 2.3), aim=(0, 1.17, 1.4), energy=70.0, size=0.9)
    cam((0.22, 0.62, 1.44), (0.0, 1.17, 1.40), focal=85)


@shot("b15_02_clear_shallow_deep")
def _():
    col, walls = _plate_drive()
    plate((-0.30, 1.17, 1.40), text="K3-17", col=col, corroded=True, name="p_shallow")
    plate((0.30, 1.17, 1.40), text="K7-41", col=col, name="p_deep")
    rig_clear(key=(0.5, 0.2, 2.4), aim=(0, 1.17, 1.4), energy=90.0, size=1.0)
    cam((0.0, 0.25, 1.46), (0.0, 1.17, 1.40), focal=60)


@shot("b15_03_insitu_plate_1m")
def _():
    col, walls = _plate_drive()
    plate((0.0, 1.17, 1.40), text="K7-41", col=col, name="p_deep")
    agent(at=(-0.9, 0.15, 0), yaw=math.radians(30), lamp_w=600.0, aim_down=-8.0,
          pose="stand 0.3; look 0.0,1.17,1.35 0.4; stand 0.2")
    rig_insitu(fog=0.008)
    cam((-0.65, -0.55, 1.25), (0.0, 1.10, 1.36), focal=45)


@shot("b15_04_insitu_lamp_off_it")
def _():
    col, walls = _plate_drive()
    plate((0.0, 1.17, 1.40), text="K7-41", col=col, name="p_deep")
    agent(at=(-0.9, 0.15, 0), yaw=0.0, lamp_w=600.0, aim_down=10.0)
    rig_insitu(fog=0.008)
    cam((-0.65, -0.55, 1.25), (0.0, 1.10, 1.36), focal=45)


# ---- B16 deep machine ground -----------------------------------------------------------
@shot("b16_01_clear_pump_chamber")
def _():
    rk = rock("rk", albedo_hi=0.30, wet=0.9, dark=0.8)
    col, mouth = machine_ground(rk, radius=6.0, height=6.5, water_z=0.30, mouth_deg=25.0)
    bisect(first(col, "chamber"), (0, -2.6, 0), (0, -1, 0))
    cull(col, -2.4)
    agent(at=(-1.8, -1.9, 0), yaw=math.radians(30), lamp_w=0.0)
    rig_clear(key=(4, -14, 12), aim=(0.5, 0.5, 1.8), energy=11000.0, size=6.0, exposure=0.3)
    cam((0.2, -17.0, 6.2), (0.5, 0.5, 1.9), focal=35)


@shot("b16_02_insitu_one_lamp")
def _():
    rk = rock("rk", albedo_hi=0.30, wet=0.9, dark=0.8)
    col, mouth = machine_ground(rk, radius=6.0, height=6.5, water_z=0.30, mouth_deg=25.0)
    agent(at=(-3.0, -1.6, 0), yaw=math.radians(28), lamp_w=600.0, aim_down=6.0)
    rig_insitu(fog=0.010)
    cam((-4.4, -2.7, 1.45), (0.5, 0.6, 0.8), focal=30)


@shot("b16_03_insitu_winch_glow")
def _():
    rk = rock("rk", albedo_hi=0.30, wet=0.9, dark=0.8)
    col, mouth = machine_ground(rk, radius=6.0, height=6.5, water_z=0.30, mouth_deg=25.0)
    d, a = mouth
    agent(at=(-2.4, -2.2, 0), yaw=math.radians(-20), lamp_w=600.0, aim_down=10.0)
    rig_insitu(fog=0.012)
    bb_light("WINCH", 2400.0, 5000.0, d * 10.5 + Vector((-2.4 * d.y, 2.4 * d.x, 3.0)), size=0.5)
    cam((-4.4, -2.4, 1.5), (2.5, 1.2, 1.4), focal=28)


# ---- B17 a junction (the decision point, in rock) --------------------------------------
def _crosscut(clear):
    """A crosscut leaving a drive at right angles: the atom of every teaching stop."""
    rk = rock("rk", albedo_hi=0.30, wet=0.55, dark=0.45)
    colA, wallsA = worked_drive(length=22.0, rk=rk, plates=True)
    jx = 3.0
    colB = G.new_collection("CROSSCUT")
    wallsB = drive(length=12.0, col=colB, mat=rk, x0=6.6, seed=9)
    floorB = drive_floor(length=12.0, col=colB, mat=rk, x0=6.6, seed=10)
    for o in (wallsB, floorB):
        o.rotation_euler = (0, 0, math.pi / 2)
        o.location = (jx, 0, 0)
    bpy.context.view_layer.update()
    bisect(wallsB, (jx, 1.12, 0), (0, -1, 0))
    bisect(floorB, (jx, 1.12, 0), (0, -1, 0))
    punch(wallsA, (jx, 0, 1.2), (0, 1, 0), 1.24, forward_only=True)
    for o in list(colA.objects):
        if o.name.startswith(("socket", "bolt", "plate")) and abs(o.location.x - jx) < 1.4 and o.location.y > 0:
            bpy.data.objects.remove(o)
    if clear:
        bisect(wallsA, (0, -0.35, 0), (0, -1, 0))
        agent(at=(0.6, 0.15, 0), yaw=0.0, lamp_w=0.0)
        rig_clear(key=(0, -7, 7), aim=(jx, 0.5, 1.2), energy=2600.0, size=3.0)
        cam((1.2, -8.5, 4.2), (jx, 1.0, 0.9), focal=38)
    else:
        agent(at=(0.2, 0.15, 0), yaw=0.0, lamp_w=600.0, aim_down=6.0,
              pose="stand 0.3; look 2.6,1.6,0.3 0.4 ride; stand 0.2")
        rig_insitu(fog=0.010)
        cam((-2.2, -0.75, 1.15), (jx, 1.0, 0.5), focal=30)


SHOTS["b17_01_clear_crosscut"] = lambda: _crosscut(True)
SHOTS["b17_02_insitu_crosscut"] = lambda: _crosscut(False)


# ---------------------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shot", default=None)
    ap.add_argument("--shots", default=None, help="comma-separated prefixes, or 'all'")
    ap.add_argument("--out", default=None)
    ap.add_argument("--outdir", default=None)
    ap.add_argument("--samples", type=int, default=40)
    ap.add_argument("--res", default="960x600")
    ap.add_argument("--skip-existing", action="store_true")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    if a.list:
        for k in sorted(SHOTS):
            print(k)
        return
    res = tuple(int(v) for v in a.res.split("x"))
    if a.shot:
        names = [a.shot]
    else:
        pre = [p for p in a.shots.split(",") if p]
        names = sorted(k for k in SHOTS if a.shots == "all" or any(k.startswith(p) for p in pre))
    for name in names:
        out = a.out if (a.shot and a.out) else os.path.join(a.outdir, name + ".png")
        if a.skip_existing and os.path.exists(out):
            print("SKIP", name, flush=True)
            continue
        t0 = time.time()
        try:
            reset()
            SHOTS[name]()
            render(out, a.samples, res)
            print(f"OK {name} {time.time() - t0:.0f}s", flush=True)
        except Exception:
            traceback.print_exc()
            print(f"FAIL {name}", flush=True)


main()
