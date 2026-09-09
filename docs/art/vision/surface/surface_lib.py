"""The pit-head: every surface concept on the vision board, as one procedural Blender scene.

Nothing in the repo drew a surface before this. DESIGN-PRINCIPLES.md 3 binds only: the
pit-head is where the shaft comes up, machines are kept / prepared / taught / sent down
there, it is the only place with sky, it is safe and lit. Everything else in this file is a
PROPOSAL and is listed as a guess in NOTES.md.

Layout (metres, +X east, +Y north, Z up, shaft collar centre at the origin):
  collar + headframe      at (0, 0); headframe apex over y = 0.9
  modern winch            at (0, 9.5) on a concrete pad
  winding house (dead)    9 x 7 m, roofless, centred (0, 17)
  yard lean-to            on the winding house's west wall, centred (-8, 16)
  listening post          (-3.2, -2.8), cable drum beside it
  hardstanding            32 x 28 m centred (0, 4)
  the course              phase2 seed-54 corridor at 0.6 m/cell, root at (28, -6), rotated east
  spoil heaps             around the compound; the flat to the east is the course

Run through surface.py. Imports the repo's own probes read-only (p2_env for rock, agent_model
for the walker) and does not modify them. Blender 5.2, Cycles CPU.
"""
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
from agent_model.build import build_agent, _module  # noqa: E402
from agent_model.motion import Mover, script  # noqa: E402
import agent_model.build as _B  # noqa: E402
import p2_env as E  # noqa: E402

# ---------------------------------------------------------------------------------------
# build.py's _settle_pole_angles runs 24 depsgraph updates per leg (96 per machine, ~30 s in a
# big scene) to find the knee plane, and the answer depends only on the chassis geometry.
# Cache it on disk across Blender processes. A runtime patch of this probe, not a change to
# agent_model.
# ---------------------------------------------------------------------------------------
_POLE_CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_pole_cache.json")
_orig_settle = _B._settle_pole_angles


def _settle_cached(arm, leg_geom):
    import json
    key = "|".join(f"{v.x:.3f},{v.y:.3f},{v.z:.3f}" for lg in leg_geom for v in lg)
    try:
        cache = json.load(open(_POLE_CACHE))
    except Exception:
        cache = {}
    if key in cache:
        for i, deg in enumerate(cache[key]):
            arm.pose.bones[f"tibia.{i}"].constraints[-1].pole_angle = math.radians(deg)
        bpy.context.view_layer.update()
        return
    _orig_settle(arm, leg_geom)
    cache[key] = [round(math.degrees(arm.pose.bones[f"tibia.{i}"].constraints[-1].pole_angle), 3) for i in range(len(leg_geom))]
    try:
        json.dump(cache, open(_POLE_CACHE, "w"))
    except Exception:
        pass


_B._settle_pole_angles = _settle_cached

CELL = 0.6
SKY = (0.60, 0.74, 1.00)            # ART-DIRECTION 2.1: the shaft's 12000 K. Proposal: the surface's light IS this.
BONE = (0.949, 0.902, 0.824)
EMBER = (1.000, 0.478, 0.184)
WARM_DIM = (0.478, 0.400, 0.314)    # #7A6650, beacon pilot
PLAYER_SHELL, PLAYER_CHASSIS = (0.66, 0.63, 0.57), (0.050, 0.052, 0.058)
RIVAL_SHELL, RIVAL_CHASSIS = (0.070, 0.062, 0.055), (0.40, 0.36, 0.32)
ROCK_DUST = (0.30, 0.265, 0.215)
MUD = (0.085, 0.062, 0.040)

COL = None
_MATS = {}
WET = 0.0     # set by the scene before materials are made: 1.0 in rain, so iron goes wet-black and glossy
EXPOSURE = 0.0  # a shot may lift this for a CLEAR frame (never for an in-situ one); surface.py passes it to render()


def col(name="SURFACE"):
    global COL
    if COL is None:
        COL = G.new_collection(name)
    return COL


def _punch_faces(obj, cx, cy, hw, hd, zmin=-1e9):
    """Delete the faces of a mesh whose centre lies inside the footprint |x-cx|<hw, |y-cy|<hd and
    above zmin. Runs on the mesh data, so modifiers (displacement) still apply afterwards. This is
    how the shaft becomes a hole: the first pass capped it with the terrain, the hardstanding and
    the chamber roof, and every frame below the collar rendered black."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    # world space: a G.plane's origin is its centre, not the world origin
    mw = Matrix.Translation(obj.location) @ obj.rotation_euler.to_matrix().to_4x4() @ Matrix.Diagonal(obj.scale).to_4x4()
    kill = []
    for f in bm.faces:
        c = mw @ f.calc_center_median()
        if abs(c.x - cx) < hw and abs(c.y - cy) < hd and c.z > zmin:
            kill.append(f)
    bmesh.ops.delete(bm, geom=kill, context="FACES")
    bm.to_mesh(obj.data)
    bm.free()
    return len(kill)


def _frame_slab(name, size, at, hole_half, thick, zc, mat, hole_at=(0.0, 0.0)):
    """A slab with a rectangular hole: four boxes around it, so the shaft passes through."""
    x0, x1 = at[0] - size[0] / 2, at[0] + size[0] / 2
    y0, y1 = at[1] - size[1] / 2, at[1] + size[1] / 2
    hx, hy = hole_at
    hw, hd = hole_half
    parts = [((x0, hx - hw), (y0, y1)), ((hx + hw, x1), (y0, y1)),
             ((hx - hw, hx + hw), (y0, hy - hd)), ((hx - hw, hx + hw), (hy + hd, y1))]
    out = []
    for k, ((ax, bx), (ay, by)) in enumerate(parts):
        if bx - ax <= 0.01 or by - ay <= 0.01:
            continue
        o = G.box(f"{name}.{k}", (bx - ax, by - ay, thick), ((ax + bx) / 2, (ay + by) / 2, zc), col=col())
        G.set_material(o, mat)
        out.append(o)
    return out


def _link(o, c=None):
    c = c or col()
    for cc in list(o.users_collection):
        cc.objects.unlink(o)
    c.objects.link(o)
    return o


# =====================================================================================
# materials -- the direction's language: one warm rock family, three ages of iron, and the
# teams' kit as the only pale, clean, temporary thing
# =====================================================================================
def _noise(nt, scale, detail=6.0, coords=None):
    n = nt.nodes.new("ShaderNodeTexNoise")
    n.inputs["Scale"].default_value = scale
    n.inputs["Detail"].default_value = detail
    if coords is not None:
        nt.links.new(coords, n.inputs["Vector"])
    return n


def cast_iron(name="cast_iron"):
    """ART-DIRECTION 5.2: (0.075,0.038,0.021), roughness 0.86, metallic 0, mottled on a
    low-frequency noise, bump on two scales. Never orange. A piece of the cave with corners."""
    if name in _MATS:
        return _MATS[name]
    m, nt, out = M._new(name)
    n, L = nt.nodes, nt.links.new
    b = n.new("ShaderNodeBsdfPrincipled")
    b.inputs["Metallic"].default_value = 0.0
    geo = n.new("ShaderNodeNewGeometry")
    n1 = _noise(nt, 2.5, 7.0, geo.outputs["Position"])
    ramp = n.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.35
    k = 1.0 - 0.45 * WET
    ramp.color_ramp.elements[0].color = (0.040 * k, 0.022 * k, 0.014 * k, 1)
    ramp.color_ramp.elements[1].position = 0.75
    ramp.color_ramp.elements[1].color = (0.110 * k, 0.056 * k, 0.032 * k, 1)
    L(n1.outputs["Fac"], ramp.inputs["Fac"])
    L(ramp.outputs["Color"], b.inputs["Base Color"])
    r = n.new("ShaderNodeMath"); r.operation = "MULTIPLY_ADD"
    r.inputs[1].default_value = -0.12; r.inputs[2].default_value = 0.92 - 0.45 * WET
    L(n1.outputs["Fac"], r.inputs[0]); L(r.outputs[0], b.inputs["Roughness"])
    n2 = _noise(nt, 45.0, 4.0, geo.outputs["Position"])
    bp2 = n.new("ShaderNodeBump"); bp2.inputs["Strength"].default_value = 0.25
    L(n2.outputs["Fac"], bp2.inputs["Height"])
    bp1 = n.new("ShaderNodeBump"); bp1.inputs["Strength"].default_value = 0.45
    L(n1.outputs["Fac"], bp1.inputs["Height"]); L(bp2.outputs["Normal"], bp1.inputs["Normal"])
    L(bp1.outputs["Normal"], b.inputs["Normal"])
    L(b.outputs[0], out.inputs[0])
    _MATS[name] = m
    return m


def bearing_steel(name="bearing_steel"):
    """ART-DIRECTION 5.2: the one clean thing on the object. (0.52,0.50,0.48) rough 0.30 metallic 1."""
    if name in _MATS:
        return _MATS[name]
    m = M.bare_metal(name, (0.52, 0.50, 0.48), 0.30)
    _MATS[name] = m
    return m


def galv(name="galv"):
    """The teams' own steel: galvanised, clean, pale, temporary. Not the mine's."""
    if name in _MATS:
        return _MATS[name]
    m = M.bare_metal(name, (0.50, 0.52, 0.52), 0.48)
    _MATS[name] = m
    return m


def simple(name, rgb, rough=0.8, metallic=0.0, noise_scale=None, noise_amp=0.0):
    if name in _MATS:
        return _MATS[name]
    m, nt, out = M._new(name)
    n, L = nt.nodes, nt.links.new
    b = n.new("ShaderNodeBsdfPrincipled")
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metallic
    if noise_scale:
        geo = n.new("ShaderNodeNewGeometry")
        nz = _noise(nt, noise_scale, 5.0, geo.outputs["Position"])
        mixc = n.new("ShaderNodeMix"); mixc.data_type = "RGBA"
        mixc.inputs["A"].default_value = (*rgb, 1)
        mixc.inputs["B"].default_value = (*(v * 0.55 for v in rgb), 1)
        fac = n.new("ShaderNodeMath"); fac.operation = "MULTIPLY"; fac.inputs[1].default_value = noise_amp
        L(nz.outputs["Fac"], fac.inputs[0]); L(fac.outputs[0], mixc.inputs["Factor"])
        L(mixc.outputs["Result"], b.inputs["Base Color"])
        bp = n.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.2
        L(nz.outputs["Fac"], bp.inputs["Height"]); L(bp.outputs["Normal"], b.inputs["Normal"])
    L(b.outputs[0], out.inputs[0])
    _MATS[name] = m
    return m


def concrete():
    return simple("concrete", (0.30, 0.29, 0.27), 0.95, noise_scale=3.0, noise_amp=0.5)


def timber():
    return simple("timber", (0.15, 0.105, 0.065), 0.85, noise_scale=8.0, noise_amp=0.6)


def pale_kit():
    """The teams' cases and crates: the pale shell's own colour, matte. Temporary."""
    return simple("pale_kit", (0.66, 0.63, 0.57), 0.65, noise_scale=6.0, noise_amp=0.15)


def dark_kit():
    return simple("dark_kit", (0.06, 0.062, 0.066), 0.7)


def rubber_black():
    return simple("rubber_black", (0.02, 0.02, 0.02), 0.85)


def hoarding(name="hoarding"):
    """Corrugated galvanised sheet, weathered: the course's walls. Corrugations are a wave in
    OBJECT space along each panel's length, so every panel gets them whichever way it faces."""
    if name in _MATS:
        return _MATS[name]
    m, nt, out = M._new(name)
    n, L = nt.nodes, nt.links.new
    b = n.new("ShaderNodeBsdfPrincipled")
    b.inputs["Base Color"].default_value = (0.36, 0.36, 0.35, 1)
    b.inputs["Metallic"].default_value = 0.7
    b.inputs["Roughness"].default_value = 0.55
    tc = n.new("ShaderNodeTexCoord")
    wave = n.new("ShaderNodeTexWave")
    wave.inputs["Scale"].default_value = 13.0
    wave.bands_direction = "X"
    L(tc.outputs["Object"], wave.inputs["Vector"])
    bp = n.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.5
    L(wave.outputs["Fac"], bp.inputs["Height"]); L(bp.outputs["Normal"], b.inputs["Normal"])
    geo = n.new("ShaderNodeNewGeometry")
    nz = _noise(nt, 4.0, 5.0, geo.outputs["Position"])
    mixc = n.new("ShaderNodeMix"); mixc.data_type = "RGBA"
    mixc.inputs["A"].default_value = (0.36, 0.36, 0.35, 1)
    mixc.inputs["B"].default_value = (0.14, 0.09, 0.06, 1)   # rust streaks, dry-ish: it is up here in the weather
    fac = n.new("ShaderNodeMath"); fac.operation = "MULTIPLY"; fac.inputs[1].default_value = 0.45
    L(nz.outputs["Fac"], fac.inputs[0]); L(fac.outputs[0], mixc.inputs["Factor"])
    L(mixc.outputs["Result"], b.inputs["Base Color"])
    L(b.outputs[0], out.inputs[0])
    _MATS[name] = m
    return m


def water(name="water"):
    """ART-DIRECTION 3.5: IOR 1.33, roughness 0.02 -- a mirror at grazing angle."""
    if name in _MATS:
        return _MATS[name]
    m, nt, out = M._new(name)
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    b.inputs["Base Color"].default_value = (0.85, 0.88, 0.85, 1)
    b.inputs["Roughness"].default_value = 0.02
    b.inputs["Transmission Weight"].default_value = 1.0
    b.inputs["IOR"].default_value = 1.33
    nt.links.new(b.outputs[0], out.inputs[0])
    _MATS[name] = m
    return m


def emissive(name, rgb, strength):
    m, nt, out = M._new(name)
    e = nt.nodes.new("ShaderNodeEmission")
    e.inputs["Color"].default_value = (*rgb, 1)
    e.inputs["Strength"].default_value = strength
    nt.links.new(e.outputs[0], out.inputs[0])
    return m


def screen(name, image_path=None, strength=1.0, fallback=(0.02, 0.035, 0.045)):
    """A display. The one place an image is allowed: a screen is a thing that shows pictures."""
    m, nt, out = M._new(name)
    n, L = nt.nodes, nt.links.new
    e = n.new("ShaderNodeEmission")
    e.inputs["Strength"].default_value = strength
    if image_path and os.path.exists(image_path):
        img = bpy.data.images.load(image_path)
        tex = n.new("ShaderNodeTexImage"); tex.image = img
        tc = n.new("ShaderNodeTexCoord")
        L(tc.outputs["UV"], tex.inputs["Vector"])
        L(tex.outputs["Color"], e.inputs["Color"])
    else:
        e.inputs["Color"].default_value = (*fallback, 1)
    L(e.outputs[0], out.inputs[0])
    return m


def spoil_rock(wet=0.5):
    """The mine's own rock, broken and tipped: the same one-material family as the cave."""
    return E.rock("spoil", albedo_lo=0.04, albedo_hi=0.30, warm=1.0, wet=wet, bed_scale=0.7, fracture_scale=9.0, bump=0.7)


def sett_rock(wet=0.6):
    """Hardstanding: stone setts / rammed spoil. Same family, less bedding, more fracture, less warm."""
    return E.rock("setts", albedo_lo=0.05, albedo_hi=0.20, warm=0.45, wet=wet, bed_scale=2.5, fracture_scale=18.0, bump=0.5)


def wall_rock(wet=0.5):
    return E.rock("wall_stone", albedo_lo=0.05, albedo_hi=0.26, warm=0.8, wet=wet, bed_scale=2.2, fracture_scale=6.0, bump=0.6)


def cave_rock(wet=0.35):
    return E.rock("cave_rock", albedo_lo=0.04, albedo_hi=0.30, warm=1.0, wet=wet)


# =====================================================================================
# sky -- DAYLIGHT rig (proposal). Overcast, no sun disc, the shaft's own colour.
# =====================================================================================
def sky(kind="overcast", fog=None):
    """kind: overcast | drizzle | rain | dusk | night | sun
    The default is uniform overcast at the shaft's 12000 K (0.60,0.74,1.00), strength 1.0, plus a
    soft 'cloud break' (a SUN lamp with a 25 deg angle: directional but discless). GUESS: overcast
    always, no sun ever, so the surface light and the shaft light are one thing and the world's
    'no sun' rule survives in a surface-legal form. `sun` is the alternative, for the designer."""
    w = bpy.context.scene.world or bpy.data.worlds.new("World")
    bpy.context.scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    for nd in list(nt.nodes):
        nt.nodes.remove(nd)
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    spec = {
        "overcast": dict(col=SKY, s=1.0, fog=0.0004, sun=1.3, ang=25, el=38, az=215),
        "drizzle": dict(col=(0.56, 0.66, 0.86), s=0.55, fog=0.0035, sun=0.45, ang=40, el=35, az=215),
        "rain": dict(col=(0.50, 0.58, 0.74), s=0.32, fog=0.009, sun=0.0, ang=40, el=35, az=215),
        "dusk": dict(col=(0.42, 0.50, 0.74), s=0.22, fog=0.0025, sun=0.08, ang=40, el=12, az=260),
        "night": dict(col=(0.30, 0.36, 0.55), s=0.02, fog=0.0015, sun=0.0, ang=40, el=10, az=260),
        "sun": dict(col=(0.42, 0.60, 1.00), s=0.55, fog=0.0005, sun=4.0, ang=0.6, el=22, az=225),
    }[kind]
    bg.inputs["Color"].default_value = (*spec["col"], 1)
    bg.inputs["Strength"].default_value = spec["s"]
    nt.links.new(bg.outputs[0], out.inputs["Surface"])
    f = spec["fog"] if fog is None else fog
    if f > 0:
        # NOT a world volume: in Cycles a world volume sits between every surface and a background
        # at infinity, so the sky is extinguished and the frame goes black. A bounded box instead.
        fog_box(f)
    if spec["sun"] > 0:
        d = bpy.data.lights.new("SUN", "SUN")
        d.energy = spec["sun"]
        d.angle = math.radians(spec["ang"])
        d.color = (0.92, 0.94, 1.0) if kind != "sun" else (1.0, 0.93, 0.82)
        o = bpy.data.objects.new("SUN", d)
        bpy.context.scene.collection.objects.link(o)
        el, az = math.radians(spec["el"]), math.radians(spec["az"])
        o.rotation_euler = Euler((math.pi / 2 - el, 0, az))
    return w


def fog_box(density, size=500.0, height=60.0):
    """Aerial perspective / drizzle as a bounded scattering volume the sky can shine through."""
    m, nt, out = M._new("fog")
    vol = nt.nodes.new("ShaderNodeVolumeScatter")
    vol.inputs["Density"].default_value = density
    vol.inputs["Anisotropy"].default_value = 0.5
    vol.inputs["Color"].default_value = (0.85, 0.86, 0.90, 1)
    nt.links.new(vol.outputs[0], out.inputs["Volume"])
    b = G.box("fog_box", (size, size, height), (10, 5, height / 2 - 2.0), col=col())
    G.set_material(b, m)
    b.visible_shadow = False
    return b


def yard_light(energy=320.0):
    """PROPOSAL. The teams' own work light under the lean-to roof: a white LED floodlight, the
    lamp's (1.00,0.98,0.95). DESIGN-PRINCIPLES 3 says the surface is 'safe and lit'; this is what
    lit means after dark up here, and it is the one light the cave never has: free."""
    cx, cy = YARD
    G.set_material(G.box("yard_fitting", (0.36, 0.12, 0.08), (cx - 1.2, cy, 2.78), bevel=0.01, col=col()), galv())
    return E.add_light("YARD_WORK", "AREA", (cx - 1.2, cy, 2.72), energy, (1.00, 0.98, 0.95), size=0.5, aim=(cx - 1.2, cy, 0.0))


def dark_world():
    """Underground: world strength 0 (ART-DIRECTION 2.1). Nothing is lit unless a fixture lights it."""
    return E.world(fog=0.012, ambient=0.0)


# =====================================================================================
# terrain, spoil, hardstanding, puddles
# =====================================================================================
def terrain(size=280.0, rock=None, seed=3, heaps=True):
    rock = rock or spoil_rock()
    t = G.plane("terrain", size, (10, 5, -0.06), col=col(), subdiv=90)
    _punch_faces(t, 0.0, 0.0, 5.0, 5.0)        # under the hardstanding: the shaft passes through here
    E._displace(t, 7.0, 0.5, depth=4, mid=0.5)
    E._displace(t, 0.9, 0.10, depth=3, mid=0.5)
    t.data.shade_smooth()
    G.set_material(t, rock)
    if heaps:
        for i, (x, y, sx, sy, sz, rz) in enumerate([
            (-34, -22, 14, 6, 4.0, 0.3), (-44, 10, 12, 7, 5.0, 1.2), (-28, 38, 16, 6, 4.5, 0.1),
            (16, 44, 18, 7, 5.5, -0.2), (-14, -44, 20, 8, 6.0, 0.4), (60, 78, 22, 8, 6.5, 0.9),
            (-70, -30, 24, 9, 7.0, -0.5), (36, -62, 20, 8, 6.0, 1.4), (150, 20, 30, 10, 8.0, 0.2),
            (95, -70, 26, 9, 7.0, 0.8), (130, 100, 28, 10, 8.0, 0.0),
        ]):
            bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=4, radius=1.0, location=(x, y, -0.4))
            h = bpy.context.object
            h.name = f"heap.{i}"
            h.scale = (sx, sy, sz)
            h.rotation_euler = (0, 0, rz)
            bpy.ops.object.transform_apply(scale=True, rotation=True)
            E._displace(h, 5.0, 1.6, depth=4)
            E._displace(h, 0.8, 0.25, depth=3)
            h.data.shade_smooth()
            G.set_material(h, rock)
            _link(h)
    return t


def hardstanding(size=(32.0, 28.0), at=(0.0, 4.0), puddles=True, wet=0.6):
    m = sett_rock(wet)
    s = _frame_slab("hardstanding", size, at, (SHAFT_W / 2 + 0.075, SHAFT_D / 2 + 0.075), 0.4, -0.2, m)
    if puddles:
        w = water()
        rng = random.Random(9)
        for i, (x, y, rx, ry) in enumerate([(-6, 8, 2.6, 1.4), (5, -4, 1.9, 1.1), (7, 10, 1.4, 0.9),
                                            (-11, 2, 3.2, 1.6), (2, 13, 1.2, 0.8), (-4, -6, 2.2, 1.0),
                                            (10, 3, 1.6, 1.2)]):
            p = G.cyl(f"puddle.{i}", 1.0, 1.0, 0.006, (x, y, 0.004), verts=28, col=col())
            p.scale = (rx, ry, 1.0)
            p.rotation_euler = (0, 0, rng.uniform(0, 3))
            G.set_material(p, w)
    return s


# =====================================================================================
# the shaft: collar, plinth, guide rails, the hole, fence, cage
# =====================================================================================
SHAFT_W, SHAFT_D = 2.4, 2.0          # opening, X by Y. GUESS.
COLLAR_Z = 0.55                      # top of the collar iron


def _tube(name, w, d, z0, z1, at=(0, 0), mat=None, inward=True):
    """An open rectangular tube (four walls, no caps) with normals pointing INTO the hole."""
    bm = bmesh.new()
    cx, cy = at
    pts = [(cx - w / 2, cy - d / 2), (cx + w / 2, cy - d / 2), (cx + w / 2, cy + d / 2), (cx - w / 2, cy + d / 2)]
    lo = [bm.verts.new((x, y, z0)) for x, y in pts]
    hi = [bm.verts.new((x, y, z1)) for x, y in pts]
    for i in range(4):
        j = (i + 1) % 4
        if inward:
            bm.faces.new((lo[i], hi[i], hi[j], lo[j]))
        else:
            bm.faces.new((lo[i], lo[j], hi[j], hi[i]))
    o = G._mesh_object(name, bm, col=col(), smooth=False)
    if mat:
        G.set_material(o, mat)
    return o


def shaft(depth=40.0, rock=None, lined=3.0):
    """The hole. GUESS: 2.4 x 2.0 m, iron-lined for the top 3 m, bare rock below, ending in black."""
    rock = rock or cave_rock(0.6)
    iron = cast_iron()
    stone = wall_rock(0.6)
    # plinth and collar
    _frame_slab("plinth", (SHAFT_W + 2.0, SHAFT_D + 2.0), (0, 0), (SHAFT_W / 2, SHAFT_D / 2), 0.40, 0.20, stone)
    for k, (x, y, sx, sy) in enumerate([(0, -(SHAFT_D / 2 + 0.15), SHAFT_W + 0.6, 0.30), (0, SHAFT_D / 2 + 0.15, SHAFT_W + 0.6, 0.30),
                                        (-(SHAFT_W / 2 + 0.15), 0, 0.30, SHAFT_D), (SHAFT_W / 2 + 0.15, 0, 0.30, SHAFT_D)]):
        G.set_material(G.box(f"collar.{k}", (sx, sy, 0.15), (x, y, 0.40 + 0.075), bevel=0.012, col=col()), iron)
    # collar bolts: raised, cast, in the 1.2 m module
    for k in range(4):
        for s in (-1, 1):
            G.set_material(G.cyl(f"collar_bolt.{k}.{s}", 0.03, 0.03, 0.03, (-0.9 + 0.6 * k, s * (SHAFT_D / 2 + 0.15), COLLAR_Z + 0.015), verts=8, col=col()), iron)
    # the hole itself: iron plates for the top metres, rock below, open at the bottom into black
    _tube("shaft_lining", SHAFT_W, SHAFT_D, COLLAR_Z - lined, COLLAR_Z, mat=iron)
    _tube("shaft_rock", SHAFT_W + 0.15, SHAFT_D + 0.15, COLLAR_Z - depth, COLLAR_Z - lined, mat=rock)
    # black floor far below so nothing shows through
    G.set_material(G.box("shaft_bottom", (SHAFT_W + 1, SHAFT_D + 1, 0.2), (0, 0, COLLAR_Z - depth - 0.1), col=col()), simple("void", (0.0, 0.0, 0.0), 1.0))
    # guide rails: two channels the cage runs on
    for s in (-1, 1):
        G.set_material(G.box(f"guide.{s}", (0.12, 0.08, depth + 0.6), (s * (SHAFT_W / 2 - 0.08), 0, COLLAR_Z - depth / 2 + 0.3), col=col()), bearing_steel())
    # fence, open on the west (yard) side
    fm = galv()
    posts = [(3.2, -3.0), (3.2, 0), (3.2, 3.0), (0, 3.0), (-3.2, 3.0), (0, -3.0), (-3.2, -3.0)]
    for k, (x, y) in enumerate(posts):
        G.set_material(G.cyl(f"fence_post.{k}", 0.03, 0.03, 1.15, (x, y, 0.55), verts=8, col=col()), fm)
    rails = [((3.2, -3.0), (3.2, 3.0)), ((3.2, 3.0), (-3.2, 3.0)), ((3.2, -3.0), (-3.2, -3.0))]
    for k, (a, b) in enumerate(rails):
        for z in (0.55, 1.05):
            G.set_material(G.segment(f"fence_rail.{k}.{z}", (a[0], a[1], z), (b[0], b[1], z), 0.018, 0.018, verts=8, col=col()), fm)
    return iron


def cage(z=COLLAR_Z):
    """The kibble / cage the teams lower machines in. Modern, galvanised, open. GUESS.
    z is the cage floor height. Returns the bridle apex so the cable can end there."""
    fm = galv()
    W, D, H = 1.7, 1.4, 1.8
    parts = []
    # floor: an open grating, not a plate, so from below a machine in the cage reads against the sky
    for sy in (-1, 1):
        parts.append(G.box(f"cage_floor_edge.y{sy}", (W, 0.05, 0.05), (0, sy * (D / 2 - 0.025), z + 0.025), col=col()))
    for sx in (-1, 1):
        parts.append(G.box(f"cage_floor_edge.x{sx}", (0.05, D, 0.05), (sx * (W / 2 - 0.025), 0, z + 0.025), col=col()))
    for k in range(1, 11):
        parts.append(G.box(f"cage_bar.x{k}", (0.025, D - 0.1, 0.04), (-W / 2 + W * k / 11, 0, z + 0.03), col=col()))
    for k in range(1, 9):
        parts.append(G.box(f"cage_bar.y{k}", (W - 0.1, 0.02, 0.03), (0, -D / 2 + D * k / 9, z + 0.02), col=col()))
    for sx in (-1, 1):
        for sy in (-1, 1):
            parts.append(G.box(f"cage_post.{sx}.{sy}", (0.06, 0.06, H), (sx * (W / 2 - 0.03), sy * (D / 2 - 0.03), z + H / 2), col=col()))
    for sy in (-1, 1):
        parts.append(G.box(f"cage_top.{sy}", (W, 0.05, 0.05), (0, sy * (D / 2 - 0.03), z + H), col=col()))
        for zz in (0.55, 1.05):
            parts.append(G.box(f"cage_rail.{sy}.{zz}", (W - 0.1, 0.03, 0.03), (0, sy * (D / 2 - 0.03), z + zz), col=col()))
    for sx in (-1, 1):
        parts.append(G.box(f"cage_top_x.{sx}", (0.05, D, 0.05), (sx * (W / 2 - 0.03), 0, z + H), col=col()))
    # bridle to a single cable above
    apex = Vector((0, 0, z + H + 1.3))
    for sx in (-1, 1):
        for sy in (-1, 1):
            parts.append(G.segment(f"bridle.{sx}.{sy}", (sx * (W / 2 - 0.03), sy * (D / 2 - 0.03), z + H), apex, 0.012, 0.012, verts=6, col=col()))
    for p in parts:
        G.set_material(p, fm)
    # cage runners on the guide rails
    for sx in (-1, 1):
        r = G.box(f"runner.{sx}", (0.16, 0.14, 0.5), (sx * (SHAFT_W / 2 - 0.08), 0, z + 0.9), col=col())
        G.set_material(r, dark_kit())
    return apex


# =====================================================================================
# headframe, winch, winding house
# =====================================================================================
HF_APEX_Z = 9.4
SHEAVE_R = 0.9
SHEAVE_C = (0.5, 0.9, HF_APEX_Z + 0.95)      # the LIVE sheave (x=+0.5); the dead one at x=-0.5


def headframe(flood=True):
    """Cast-iron A-frame over the shaft, two sheaves, the dead one rusted, the live one bright
    where the cable runs. GUESS: ~10 m to the sheave axis, in the Assayer's casting language."""
    iron = cast_iron()
    dark = simple("iron_dark", (0.03, 0.026, 0.022), 0.9)
    legs = [((-2.7, -2.6, 0), (-0.7, 0.4, HF_APEX_Z)), ((2.7, -2.6, 0), (0.7, 0.4, HF_APEX_Z)),
            ((-2.5, 7.2, 0), (-0.7, 1.6, HF_APEX_Z)), ((2.5, 7.2, 0), (0.7, 1.6, HF_APEX_Z))]
    for k, (a, b) in enumerate(legs):
        G.set_material(G.strut(f"hf_leg.{k}", a, b, 0.42, 0.34, 0.26, 0.22, col=col(), bevel=0.01), iron)
        G.set_material(G.box(f"hf_pad.{k}", (1.2, 1.2, 0.35), (a[0], a[1], 0.17), bevel=0.02, col=col()), wall_rock(0.5))

    def leg_pt(k, t):
        a, b = Vector(legs[k][0]), Vector(legs[k][1])
        return a.lerp(b, t)
    for t in (0.33, 0.66):
        for (i, j) in ((0, 1), (2, 3), (0, 2), (1, 3)):
            G.set_material(G.segment(f"hf_tie.{i}{j}.{t}", leg_pt(i, t), leg_pt(j, t), 0.09, 0.09, verts=8, col=col()), iron)
    for (i, j) in ((0, 2), (1, 3)):
        G.set_material(G.segment(f"hf_diag.{i}{j}a", leg_pt(i, 0.33), leg_pt(j, 0.66), 0.06, 0.06, verts=8, col=col()), iron)
        G.set_material(G.segment(f"hf_diag.{i}{j}b", leg_pt(j, 0.33), leg_pt(i, 0.66), 0.06, 0.06, verts=8, col=col()), iron)
    # sheave deck
    G.set_material(G.box("hf_deck", (2.6, 2.2, 0.35), (0, 1.0, HF_APEX_Z + 0.17), bevel=0.02, col=col()), iron)
    for sx in (-1, 1):
        G.set_material(G.box(f"hf_bearing_ped.{sx}", (0.5, 0.6, 0.7), (sx * 1.0, SHEAVE_C[1], HF_APEX_Z + 0.35 + 0.35), bevel=0.02, col=col()), iron)
    # sheaves: rim + spokes + hub, axis X
    for sx, live in ((1, True), (-1, False)):
        c = (sx * 0.5, SHEAVE_C[1], SHEAVE_C[2])
        rim = G.torus(f"sheave_rim.{sx}", SHEAVE_R, 0.075, c, rot=(0, math.pi / 2, 0), col=col())
        G.set_material(rim, bearing_steel() if live else iron)
        for k in range(8):
            a = math.pi * 2 * k / 8
            p0 = Vector((c[0], c[1] + 0.12 * math.cos(a), c[2] + 0.12 * math.sin(a)))
            p1 = Vector((c[0], c[1] + (SHEAVE_R - 0.06) * math.cos(a), c[2] + (SHEAVE_R - 0.06) * math.sin(a)))
            G.set_material(G.segment(f"spoke.{sx}.{k}", p0, p1, 0.035, 0.03, verts=8, col=col()), iron)
        G.set_material(G.cyl(f"sheave_hub.{sx}", 0.16, 0.16, 0.22, c, rot=(0, math.pi / 2, 0), verts=16, col=col()), bearing_steel() if live else dark)
    G.set_material(G.cyl("sheave_axle", 0.06, 0.06, 2.6, (0, SHEAVE_C[1], SHEAVE_C[2]), rot=(0, math.pi / 2, 0), verts=12, col=col()), bearing_steel())
    # a foundry mark plate on the deck face: raised, unreadable, no date
    G.set_material(G.box("hf_plate", (0.5, 0.02, 0.22), (0.0, -0.11, HF_APEX_Z + 0.17), bevel=0.004, col=col()), iron)
    if flood:
        # PROPOSAL: the teams' floodlight under the deck, aimed down the shaft. It is what makes the
        # shaft chamber's 'daylight' bright enough to render -- see NOTES: sky through 14+ m of
        # shaft is physically black at the bottom.
        G.set_material(G.box("flood_body", (0.32, 0.22, 0.12), (0.0, -0.15, HF_APEX_Z - 0.10), bevel=0.01, col=col()), galv())
        G.set_material(G.box("flood_glass", (0.28, 0.18, 0.01), (0.0, -0.15, HF_APEX_Z - 0.165), col=col()), simple("flood_glass", (0.7, 0.75, 0.8), 0.1, 0.0))
    return iron


def flood_light(energy=2500.0):
    """The floodlight's light. Cold, the shaft's colour."""
    return E.add_light("FLOOD", "SPOT", (0.0, -0.15, HF_APEX_Z - 0.2), energy, SKY, size=0.2, spot_deg=34, blend=0.3, aim=(0, 0, -30))


def cable(cage_apex=None, down_to=None):
    """The live cable: bright steel, from the live sheave's front tangent straight down the shaft, and
    back over the top to the modern winch drum."""
    st = bearing_steel()
    x = SHEAVE_C[0]
    top = Vector((x, SHEAVE_C[1], SHEAVE_C[2] + SHEAVE_R))
    front = Vector((x, SHEAVE_C[1] - SHEAVE_R, SHEAVE_C[2]))
    end = Vector(cage_apex) if cage_apex is not None else Vector((x, SHEAVE_C[1] - SHEAVE_R, down_to if down_to is not None else -30.0))
    G.set_material(G.segment("cable_down", front, Vector((end.x, end.y, end.z)), 0.014, 0.014, verts=8, col=col()), st)
    drum = Vector((0.0, 9.5, 0.95))
    G.set_material(G.tube_along("cable_back", [front + Vector((0, 0.15, SHEAVE_R * 0.9)), top, top.lerp(drum, 0.5), drum], 0.014, verts=8, col=col()), st)


def winch():
    """The small modern electric winch the teams rigged to the old frame. Clean, galvanised. GUESS."""
    fm, dk = galv(), dark_kit()
    G.set_material(G.box("winch_pad", (1.8, 1.4, 0.15), (0, 9.5, 0.075), col=col()), concrete())
    for sx in (-1, 1):
        G.set_material(G.strut(f"winch_frame.{sx}", (sx * 0.55, 9.5, 0.15), (sx * 0.4, 9.5, 0.95), 0.08, 0.08, 0.06, 0.06, col=col(), bevel=0.004), fm)
        G.set_material(G.strut(f"winch_frame_b.{sx}", (sx * 0.55, 10.1, 0.15), (sx * 0.4, 9.55, 0.95), 0.06, 0.06, 0.05, 0.05, col=col(), bevel=0.004), fm)
    G.set_material(G.cyl("winch_drum", 0.28, 0.28, 0.6, (0, 9.5, 0.95), rot=(0, math.pi / 2, 0), verts=20, col=col()), dk)
    G.set_material(G.cyl("winch_drum_cable", 0.30, 0.30, 0.34, (0, 9.5, 0.95), rot=(0, math.pi / 2, 0), verts=20, col=col()), bearing_steel())
    G.set_material(G.box("winch_motor", (0.32, 0.30, 0.30), (0.62, 9.5, 0.95), bevel=0.01, col=col()), dk)
    G.set_material(G.box("winch_control", (0.30, 0.20, 0.40), (-0.9, 10.2, 0.55), bevel=0.01, col=col()), pale_kit())
    G.set_material(G.tube_along("winch_cable_run", [Vector((0.62, 9.6, 0.8)), Vector((0.9, 11.5, 0.05)), Vector((0, 13.6, 0.05))], 0.02, verts=6, col=col()), rubber_black())


def winding_house(at=(0.0, 17.0)):
    """The dead winding house: roofless stone walls, the old engine's flywheel inside. GUESS."""
    stone = wall_rock(0.55)
    iron = cast_iron()
    cx, cy = at
    W, D, H, T = 9.0, 7.0, 4.5, 0.6
    G.set_material(G.box("wh_s_a", ((W - 2.6) / 2, T, H), (cx - (W / 4 + 0.65), cy - D / 2, H / 2), col=col()), stone)
    G.set_material(G.box("wh_s_b", ((W - 2.6) / 2, T, H), (cx + (W / 4 + 0.65), cy - D / 2, H / 2), col=col()), stone)
    G.set_material(G.box("wh_s_lintel", (2.8, T, 1.2), (cx, cy - D / 2, H - 0.6), col=col()), stone)
    G.set_material(G.box("wh_n", (W, T, H * 0.8), (cx, cy + D / 2, H * 0.4), col=col()), stone)
    for sx in (-1, 1):
        G.set_material(G.box(f"wh_side.{sx}", (T, D, H * (0.92 if sx > 0 else 1.0)), (cx + sx * W / 2, cy, H * (0.46 if sx > 0 else 0.5)), col=col()), stone)
    for sx in (-1, 1):
        G.set_material(G.box(f"wh_window.{sx}", (0.05, 1.2, 1.8), (cx + sx * (W / 2 + 0.3), cy + 0.8, 2.4), col=col()), simple("void2", (0.0, 0.0, 0.0), 1.0))
    fc = (cx, cy + 0.5, 2.3)
    G.set_material(G.torus("flywheel", 2.2, 0.16, fc, rot=(0, math.pi / 2, 0), col=col()), iron)
    for k in range(8):
        a = math.pi * 2 * k / 8
        G.set_material(G.segment(f"fw_spoke.{k}", (fc[0], fc[1] + 0.25 * math.cos(a), fc[2] + 0.25 * math.sin(a)),
                                 (fc[0], fc[1] + 2.05 * math.cos(a), fc[2] + 2.05 * math.sin(a)), 0.07, 0.06, verts=8, col=col()), iron)
    G.set_material(G.cyl("fw_hub", 0.35, 0.35, 0.6, fc, rot=(0, math.pi / 2, 0), verts=16, col=col()), iron)
    G.set_material(G.box("engine_bed", (2.4, 1.6, 0.8), (cx - 2.4, cy + 1.6, 0.4), bevel=0.02, col=col()), iron)
    G.set_material(G.cyl("engine_cyl", 0.55, 0.55, 2.2, (cx - 2.4, cy + 1.6, 1.9), verts=16, bevel=0.02, col=col()), iron)
    rng = random.Random(4)
    for i in range(10):
        r = rng.uniform(0.25, 0.6)
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=r, location=(cx + rng.uniform(-3.5, 3.5), cy + rng.uniform(-2.5, 2.5), r * 0.4))
        o = bpy.context.object; o.name = f"roof_rubble.{i}"
        o.scale = (rng.uniform(0.8, 1.6), rng.uniform(0.8, 1.6), rng.uniform(0.3, 0.6))
        G.set_material(o, stone)
        _link(o)


# =====================================================================================
# the yard lean-to: bench, rack, crates, charge cable, terminal
# =====================================================================================
YARD = (-8.0, 16.0)
BENCH = (-9.0, 14.3, 0.90)       # bench top centre, z is the top surface


def yard(terminal_img=None):
    cx, cy = YARD
    tm, fm, pk, dk = timber(), galv(), pale_kit(), dark_kit()
    roof = G.box("yard_roof", (7.0, 5.2, 0.06), (cx, cy, 3.0), col=col())
    roof.rotation_euler = (0, math.radians(-7), 0)
    G.set_material(roof, hoarding())
    for k, (x, y) in enumerate([(cx - 3.3, cy - 2.4), (cx - 3.3, cy + 2.4), (cx - 0.2, cy - 2.4), (cx - 0.2, cy + 2.4)]):
        G.set_material(G.cyl(f"yard_post.{k}", 0.06, 0.06, 2.65 + (0.4 if x > cx - 1 else 0.0), (x, y, 1.3 + (0.2 if x > cx - 1 else 0.0)), verts=10, col=col()), tm)
    G.set_material(G.box("yard_purlin.0", (7.0, 0.08, 0.14), (cx, cy - 2.4, 2.6), col=col()), tm)
    G.set_material(G.box("yard_purlin.1", (7.0, 0.08, 0.14), (cx, cy + 2.4, 2.6), col=col()), tm)
    G.set_material(G.box("yard_slab", (7.5, 6.0, 0.12), (cx, cy, 0.06), col=col()), concrete())
    bx, by, bz = BENCH
    G.set_material(G.box("bench_top", (3.0, 0.8, 0.06), (bx, by, bz - 0.03), bevel=0.005, col=col()), tm)
    for sx in (-1, 1):
        G.set_material(G.strut(f"bench_leg.{sx}a", (bx + sx * 1.3, by - 0.35, 0.12), (bx + sx * 1.3, by, bz - 0.06), 0.05, 0.05, 0.05, 0.05, col=col()), fm)
        G.set_material(G.strut(f"bench_leg.{sx}b", (bx + sx * 1.3, by + 0.35, 0.12), (bx + sx * 1.3, by, bz - 0.06), 0.05, 0.05, 0.05, 0.05, col=col()), fm)
    rx, ry = cx - 1.5, cy + 2.0
    for k, (x, y) in enumerate([(rx - 1.2, ry - 0.35), (rx - 1.2, ry + 0.35), (rx + 1.2, ry - 0.35), (rx + 1.2, ry + 0.35)]):
        G.set_material(G.box(f"rack_up.{k}", (0.05, 0.05, 1.9), (x, y, 0.95 + 0.12), col=col()), fm)
    for z in (0.35, 1.05, 1.75):
        G.set_material(G.box(f"rack_shelf.{z}", (2.5, 0.75, 0.03), (rx, ry, z + 0.12), col=col()), fm)
    rng = random.Random(5)
    for k in range(9):
        z = (0.35, 1.05, 1.75)[k // 3] + 0.12 + 0.015
        x = rx - 0.8 + (k % 3) * 0.8 + rng.uniform(-0.05, 0.05)
        sz = (0.55, 0.42, rng.uniform(0.22, 0.34))
        G.set_material(G.box(f"case.{k}", sz, (x, ry, z + sz[2] / 2), bevel=0.012, col=col()), pk if k % 4 else dk)
    for k, (x, y, z) in enumerate([(cx + 1.8, cy + 1.4, 0.12), (cx + 1.8, cy + 1.4, 0.52), (cx + 2.4, cy + 0.7, 0.12)]):
        G.set_material(G.box(f"crate.{k}", (0.62, 0.62, 0.40), (x, y, z + 0.2), bevel=0.01, col=col()), pk)
    G.set_material(G.box("charge_box", (0.12, 0.28, 0.36), (cx + 3.45, cy - 0.6, 1.3), bevel=0.01, col=col()), pk)
    tcx, tcy = bx + 0.75, by
    G.set_material(G.box("term_case", (0.62, 0.48, 0.14), (tcx, tcy + 0.02, bz + 0.07), bevel=0.012, col=col()), pk)
    lid = G.box("term_lid", (0.62, 0.03, 0.42), (tcx, tcy + 0.24, bz + 0.14 + 0.19), bevel=0.01, col=col())
    lid.rotation_euler = (math.radians(-18), 0, 0)
    G.set_material(lid, pk)
    scr = G.plane("term_screen", 1.0, (0, 0, 0), col=col())
    scr.scale = (0.54, 0.34, 1.0)
    scr.rotation_euler = (math.radians(90 - 18), 0, 0)
    scr.location = (tcx, tcy + 0.24 - 0.02, bz + 0.14 + 0.19)
    G.set_material(scr, screen("term_screen_mat", terminal_img, 1.4, (0.02, 0.03, 0.04)))
    G.set_material(G.box("term_keys", (0.5, 0.18, 0.02), (tcx, tcy - 0.08, bz + 0.15), bevel=0.004, col=col()), dk)
    return (bx, by, bz)


def modules_on_bench(at, mats=None):
    """The seven modules laid out as physical parts, in a row. Built with agent_model's own
    `_module()` unattached: the loadout as things on a table."""
    mats = mats or {
        "glass": M.bare_metal("m_glass", (0.02, 0.03, 0.04), 0.08), "light": emissive("m_light", BONE, 0.6),
        "dark": M.bare_metal("m_dark", (0.09, 0.09, 0.10), 0.5), "eye": emissive("m_eye", BONE, 0.6),
        "lens": M.lens("m_lens"), "carbon": M.bare_metal("m_carbon", (0.04, 0.04, 0.045), 0.35),
        "rubber": M.rubber("m_rubber"), "metal": M.bare_metal("m_metal"), "accent": simple("m_accent", (0.85, 0.45, 0.10), 0.55, 0.3),
        "chassis": simple("m_chassis", PLAYER_CHASSIS, 0.45, 0.3),
    }
    u = 0.21
    x0, y0, z0 = at
    for k, kind in enumerate(["active_sonar", "optical", "passive_acoustic", "beacon_rack", "magnetometer", "cargo_bay", "structural_monitor"]):
        base = Vector((x0 - 1.2 + k * 0.38, y0, z0 + 0.002))
        for o, key in _module(kind, f"b{k}", u, col()):
            o.matrix_world = Matrix.Translation(base) @ o.matrix_world
            G.set_material(o, mats[key])


# =====================================================================================
# listening post -- the surface end of the acoustic link (PROPOSAL, A8)
# =====================================================================================
POST = (-3.2, -2.8)


def listening_post(screen_img=None, with_cable=True):
    px, py = POST
    fm, dk, pk = galv(), dark_kit(), pale_kit()
    top = Vector((px, py, 1.05))
    for k in range(3):
        a = math.radians(90 + 120 * k)
        G.set_material(G.segment(f"post_leg.{k}", top, (px + 0.55 * math.cos(a), py + 0.55 * math.sin(a), 0.0), 0.02, 0.02, verts=8, col=col()), fm)
    G.set_material(G.box("post_head", (0.34, 0.06, 0.24), (px, py, 1.22), bevel=0.01, col=col()), pk)
    scr = G.plane("post_screen", 1.0, (0, 0, 0), col=col())
    scr.scale = (0.28, 0.17, 1.0)
    scr.rotation_euler = (math.radians(78), 0, 0)
    scr.location = (px, py - 0.035, 1.23)
    G.set_material(scr, screen("post_screen_mat", screen_img, 1.4))
    dx, dy = px - 0.3, py - 0.9
    G.set_material(G.cyl("drum", 0.32, 0.32, 0.30, (dx, dy, 0.42), rot=(math.pi / 2, 0, 0), verts=20, col=col()), dk)
    G.set_material(G.cyl("drum_cable", 0.30, 0.30, 0.26, (dx, dy, 0.42), rot=(math.pi / 2, 0, 0), verts=20, col=col()), rubber_black())
    for sy in (-1, 1):
        G.set_material(G.strut(f"drum_leg.{sy}", (dx - 0.3, dy + sy * 0.25, 0.0), (dx, dy + sy * 0.2, 0.42), 0.04, 0.04, 0.03, 0.03, col=col()), fm)
        G.set_material(G.strut(f"drum_leg2.{sy}", (dx + 0.3, dy + sy * 0.25, 0.0), (dx, dy + sy * 0.2, 0.42), 0.04, 0.04, 0.03, 0.03, col=col()), fm)
    if with_cable:
        pts = [Vector((dx, dy, 0.74)), Vector((dx + 0.6, dy + 0.9, 0.35)), Vector((-1.6, -0.6, 0.05)), Vector((-1.35, -0.4, 0.56)),
               Vector((-1.15, -0.35, 0.58)), Vector((-0.95, 0.5, 0.2)), Vector((-0.95, 0.5, -30.0))]
        G.set_material(G.tube_along("hydrophone_cable", pts, 0.012, verts=6, col=col()), rubber_black())
        G.set_material(G.tube_along("post_cable", [Vector((px, py, 1.1)), Vector((px - 0.15, py - 0.5, 0.2)), Vector((dx, dy, 0.6))], 0.006, verts=6, col=col()), rubber_black())


# =====================================================================================
# the course: phase2's corridor, made physical (PROPOSAL, A4)
# =====================================================================================
COURSE_SEED = 54
COURSE_ORIGIN = (28.0, -6.0)
COURSE_W = 1.8          # passage width in metres (3 cells). GUESS.
WALL_H = 1.2            # above the 0.57 m machine, below a human's eye. GUESS.


def course_layout(seed=COURSE_SEED, origin=COURSE_ORIGIN):
    """Node positions in metres, rotated so the tree spreads east of the root. Read-only import."""
    from phase2.truth.corridor import Corridor
    C = Corridor(seed)
    L = C.layout()
    xs = [v[0] for v in L.values()]; ys = [v[1] for v in L.values()]
    cx, cy = sum(xs) / len(xs), sum(ys) / len(ys)
    rot = -math.atan2(cy, cx)
    pos = {}
    for k, (x, y) in L.items():
        xr = x * math.cos(rot) - y * math.sin(rot)
        yr = x * math.sin(rot) + y * math.cos(rot)
        pos[k] = (origin[0] + xr * CELL, origin[1] + yr * CELL)
    return C, pos


class _Panels:
    """All the course's panels in one bmesh and all its posts in another: one object each, because
    six hundred operator-built boxes take minutes to create and seconds to render."""

    def __init__(self):
        self.bm_p = bmesh.new()
        self.bm_q = bmesh.new()

    def _box(self, bm, centre, size, yaw, tilt=(0.0, 0.0)):
        R = Euler((tilt[0], tilt[1], yaw)).to_matrix()
        sx, sy, sz = size
        vs = []
        for dx in (-0.5, 0.5):
            for dy in (-0.5, 0.5):
                for dz in (-0.5, 0.5):
                    vs.append(bm.verts.new(Vector(centre) + R @ Vector((dx * sx, dy * sy, dz * sz))))
        # faces of a cube from the 8 verts indexed by (dx,dy,dz) bits: i = 4*ix + 2*iy + iz
        f = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
        for q in f:
            bm.faces.new([vs[i] for i in q])

    def _post(self, bm, centre, r, h, verts=8):
        cx, cy, cz = centre
        lo = [bm.verts.new((cx + r * math.cos(2 * math.pi * k / verts), cy + r * math.sin(2 * math.pi * k / verts), cz - h / 2)) for k in range(verts)]
        hi = [bm.verts.new((cx + r * math.cos(2 * math.pi * k / verts), cy + r * math.sin(2 * math.pi * k / verts), cz + h / 2)) for k in range(verts)]
        for k in range(verts):
            bm.faces.new((lo[k], lo[(k + 1) % verts], hi[(k + 1) % verts], hi[k]))
        bm.faces.new(list(reversed(hi)))

    def run(self, a, b, h, rng, post_every=2.4):
        a, b = Vector((a[0], a[1], 0)), Vector((b[0], b[1], 0))
        d = b - a
        L = d.length
        if L < 0.15:
            return
        yaw = math.atan2(d.y, d.x)
        n = max(1, int(math.ceil(L / post_every)))
        for i in range(n):
            c = a + d * ((i + 0.5) / n)
            hh = h + rng.uniform(-0.05, 0.05)
            self._box(self.bm_p, (c.x, c.y, hh / 2 - 0.05), (L / n - 0.03, 0.035, hh + 0.1), yaw,
                      (rng.uniform(-0.02, 0.02), rng.uniform(-0.03, 0.03)))
        for i in range(n + 1):
            c = a + d * (i / n)
            self._post(self.bm_q, (c.x, c.y, h / 2 - 0.1), 0.045, h + 0.5)

    def finish(self, mat_p, mat_q):
        for bm in (self.bm_p, self.bm_q):
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        p = G._mesh_object("course_panels", self.bm_p, col=col(), smooth=False)
        q = G._mesh_object("course_posts", self.bm_q, col=col(), smooth=True)
        G.set_material(p, mat_p)
        G.set_material(q, mat_q)
        return p, q


def course(seed=COURSE_SEED, origin=COURSE_ORIGIN, w=COURSE_W, h=WALL_H, roofed=None):
    """Walls along every passage, cut back at each node, and connecting panels between the
    mouths in angular order (a leaf gets its end cap that way; the root gets a closed bay).
    Returns (Corridor, node positions m, mouths)."""
    C, pos = course_layout(seed, origin)
    hp, tm = hoarding(), timber()
    rng = random.Random(seed)
    cut = 1.3
    pan = _Panels()
    mouths = {k: [] for k in pos}      # node -> list of (bearing, left_end, right_end)
    for pid, p in C.passages.items():
        a, b = Vector(pos[p.near]), Vector(pos[p.far])
        d = (b - a)
        L = d.length
        u = d / L
        left = Vector((-u.y, u.x))
        a2, b2 = a + u * cut, b - u * cut
        pan.run(a2 + left * (w / 2), b2 + left * (w / 2), h, rng)
        pan.run(a2 - left * (w / 2), b2 - left * (w / 2), h, rng)
        mouths[p.near].append((math.atan2(u.y, u.x), a2 + left * (w / 2), a2 - left * (w / 2)))
        mouths[p.far].append((math.atan2(-u.y, -u.x), b2 - left * (w / 2), b2 + left * (w / 2)))
    for k, ms in mouths.items():
        ms.sort(key=lambda t: t[0])
        n = len(ms)
        for i in range(n):
            _, left_end, _ = ms[i]
            _, _, right_end = ms[(i + 1) % n]
            pan.run(left_end, right_end, h, rng)
    pan.finish(hp, tm)
    rx, ry = pos[C.shaft]
    G.set_material(G.cyl("root_post", 0.05, 0.045, 1.5, (rx, ry, 0.7), verts=10, col=col()), galv())
    G.set_material(G.cyl("root_pilot", 0.035, 0.035, 0.05, (rx, ry, 1.47), verts=10, col=col()), emissive("pilot", WARM_DIM, 2.0))
    dx, dy = pos[C.deposit]
    G.set_material(G.box("cargo_crate", (0.5, 0.4, 0.34), (dx, dy, 0.17), bevel=0.01, col=col()), pale_kit())
    for i in range(6):
        r = rng.uniform(0.06, 0.14)
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=r, location=(dx + rng.uniform(-0.5, 0.5), dy + rng.uniform(-0.4, 0.4), r * 0.5))
        o = bpy.context.object; o.name = f"stock.{i}"
        G.set_material(o, spoil_rock()); _link(o)
    if roofed is not None:
        # ALTERNATIVE (design problem 3): a roofed, dark stretch so lamp / silt / ping blocks can
        # be taught up here. `roofed` is a passage id list.
        for pid in roofed:
            p = C.passages[pid]
            a, b = Vector(pos[p.near]), Vector(pos[p.far])
            c = (a + b) / 2; d = b - a
            yaw = math.atan2(d.y, d.x)
            rf = G.box(f"roof.{pid}", (d.length - 2 * cut + 0.6, w + 0.5, 0.05), (c.x, c.y, h + 0.05), col=col())
            rf.rotation_euler = (0, 0, yaw)
            G.set_material(rf, hoarding())
    return C, pos, mouths


def junctions(C, pos):
    """(node id, position, list of onward bearings) for every proper junction."""
    out = []
    for k in C.junction_ids():
        out.append((k, pos[k], [C.bearing(pid) for pid in C.children(k)]))
    return out


# =====================================================================================
# machines -- agent_model, with av_probe's three fixes re-applied every time
# =====================================================================================
def worn_metal(base, bare, accent, wear=0.35, grime=0.4, mud=0.0, dust=0.0, scuff=0.0, foot_z=0.0, name="worn"):
    """av_probe.worn_metal, copied verbatim: painted_metal plus three gravity-aware masks."""
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
    sep_n = n.new("ShaderNodeSeparateXYZ"); sep_p = n.new("ShaderNodeSeparateXYZ")
    L(geo.outputs["Normal"], sep_n.inputs["Vector"]); L(geo.outputs["Position"], sep_p.inputs["Vector"])
    tex = n.new("ShaderNodeTexNoise"); tex.inputs["Scale"].default_value = 70.0; tex.inputs["Detail"].default_value = 8.0; tex.inputs["Roughness"].default_value = 0.7
    ramp = n.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.70 - 0.22 * wear; ramp.color_ramp.elements[1].position = 0.80 - 0.22 * wear
    L(tex.outputs["Fac"], ramp.inputs["Fac"])
    ao = n.new("ShaderNodeAmbientOcclusion"); ao.inputs["Distance"].default_value = 0.02; ao.inside = True
    invao = n.new("ShaderNodeMath"); invao.operation = "SUBTRACT"; invao.inputs[0].default_value = 1.0
    L(ao.outputs["AO"], invao.inputs[1])
    edge = n.new("ShaderNodeMath"); edge.operation = "MULTIPLY"; edge.inputs[1].default_value = 4.0 * wear
    L(invao.outputs[0], edge.inputs[0])
    wearmix = n.new("ShaderNodeMath"); wearmix.operation = "MAXIMUM"
    L(ramp.outputs["Color"], wearmix.inputs[0]); L(edge.outputs[0], wearmix.inputs[1])
    fwd = n.new("ShaderNodeMath"); fwd.operation = "MAXIMUM"; fwd.inputs[1].default_value = 0.0
    L(sep_n.outputs["X"], fwd.inputs[0])
    scuffm = n.new("ShaderNodeMath"); scuffm.operation = "MULTIPLY"
    L(fwd.outputs[0], scuffm.inputs[0]); L(invao.outputs[0], scuffm.inputs[1])
    scuffg = n.new("ShaderNodeMath"); scuffg.operation = "MULTIPLY"; scuffg.inputs[1].default_value = 3.0 * scuff
    L(scuffm.outputs[0], scuffg.inputs[0])
    allwear = n.new("ShaderNodeMath"); allwear.operation = "MAXIMUM"
    L(wearmix.outputs[0], allwear.inputs[0]); L(scuffg.outputs[0], allwear.inputs[1])
    base_n = n.new("ShaderNodeRGB"); base_n.outputs[0].default_value = (*base, 1)
    bare_n = n.new("ShaderNodeRGB"); bare_n.outputs[0].default_value = (*bare, 1)
    mix = n.new("ShaderNodeMix"); mix.data_type = "RGBA"
    L(allwear.outputs[0], mix.inputs["Factor"]); L(base_n.outputs[0], mix.inputs["A"]); L(bare_n.outputs[0], mix.inputs["B"])
    up = n.new("ShaderNodeMath"); up.operation = "MAXIMUM"; up.inputs[1].default_value = 0.0
    L(sep_n.outputs["Z"], up.inputs[0])
    up3 = n.new("ShaderNodeMath"); up3.operation = "POWER"; up3.inputs[1].default_value = 3.0
    L(up.outputs[0], up3.inputs[0])
    dustn = n.new("ShaderNodeTexNoise"); dustn.inputs["Scale"].default_value = 22.0
    dustv = n.new("ShaderNodeMath"); dustv.operation = "MULTIPLY_ADD"; dustv.inputs[1].default_value = 0.5; dustv.inputs[2].default_value = 0.6
    L(dustn.outputs["Fac"], dustv.inputs[0])
    dustf = n.new("ShaderNodeMath"); dustf.operation = "MULTIPLY"
    L(up3.outputs[0], dustf.inputs[0]); L(dustv.outputs[0], dustf.inputs[1])
    dustg = n.new("ShaderNodeMath"); dustg.operation = "MULTIPLY"; dustg.inputs[1].default_value = dust
    L(dustf.outputs[0], dustg.inputs[0])
    dustmix = n.new("ShaderNodeMix"); dustmix.data_type = "RGBA"; dustmix.inputs["B"].default_value = (*ROCK_DUST, 1)
    L(mix.outputs["Result"], dustmix.inputs["A"]); L(dustg.outputs[0], dustmix.inputs["Factor"])
    mudr = n.new("ShaderNodeMapRange")
    mudr.inputs["From Min"].default_value = foot_z + 0.22; mudr.inputs["From Max"].default_value = foot_z + 0.05
    mudr.inputs["To Min"].default_value = 0.0; mudr.inputs["To Max"].default_value = 1.0; mudr.clamp = True
    L(sep_p.outputs["Z"], mudr.inputs["Value"])
    mudn = n.new("ShaderNodeTexNoise"); mudn.inputs["Scale"].default_value = 30.0
    mudv = n.new("ShaderNodeMath"); mudv.operation = "MULTIPLY_ADD"; mudv.inputs[1].default_value = 0.45; mudv.inputs[2].default_value = 0.65
    L(mudn.outputs["Fac"], mudv.inputs[0])
    mudf = n.new("ShaderNodeMath"); mudf.operation = "MULTIPLY"
    L(mudr.outputs["Result"], mudf.inputs[0]); L(mudv.outputs[0], mudf.inputs[1])
    mudg = n.new("ShaderNodeMath"); mudg.operation = "MULTIPLY"; mudg.inputs[1].default_value = mud
    L(mudf.outputs[0], mudg.inputs[0])
    mudmix = n.new("ShaderNodeMix"); mudmix.data_type = "RGBA"; mudmix.inputs["B"].default_value = (*MUD, 1)
    L(dustmix.outputs["Result"], mudmix.inputs["A"]); L(mudg.outputs[0], mudmix.inputs["Factor"])
    gr = n.new("ShaderNodeTexNoise"); gr.inputs["Scale"].default_value = 4.0; gr.inputs["Detail"].default_value = 8.0
    grr = n.new("ShaderNodeValToRGB"); grr.color_ramp.elements[0].position = 0.45; grr.color_ramp.elements[1].position = 0.7
    grf = n.new("ShaderNodeMath"); grf.operation = "MULTIPLY"; grf.inputs[1].default_value = grime
    grm = n.new("ShaderNodeMix"); grm.data_type = "RGBA"; grm.inputs["B"].default_value = (0.02, 0.018, 0.015, 1)
    L(gr.outputs["Fac"], grr.inputs["Fac"]); L(grr.outputs["Color"], grf.inputs[0]); L(grf.outputs[0], grm.inputs["Factor"])
    L(mudmix.outputs["Result"], grm.inputs["A"]); L(grm.outputs["Result"], b.inputs["Base Color"])
    rgh = n.new("ShaderNodeMath"); rgh.operation = "MULTIPLY_ADD"; rgh.inputs[1].default_value = 0.3; rgh.inputs[2].default_value = 0.35
    L(gr.outputs["Fac"], rgh.inputs[0])
    rgh2 = n.new("ShaderNodeMath"); rgh2.operation = "MAXIMUM"
    L(rgh.outputs[0], rgh2.inputs[0]); L(mudg.outputs[0], rgh2.inputs[1]); L(rgh2.outputs[0], b.inputs["Roughness"])
    bump = n.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.08
    L(tex.outputs["Fac"], bump.inputs["Height"]); L(bump.outputs["Normal"], b.inputs["Normal"])
    L(b.outputs[0], out.inputs[0])
    return m


def _retint(built, shell, chassis, wear=0.35, mud=0.0, dust=0.0, scuff=0.0, legs_too=True, foot_z=0.0,
            accent=(0.85, 0.45, 0.10), bare=(0.45, 0.45, 0.47), tag="a"):
    """av_probe._retint restricted to ONE built machine (its parts), so several machines in one
    scene can differ. Legs get a wear-capable material too, or mud never reaches the feet."""
    m_shell = worn_metal(shell, bare, accent, wear, 0.4, mud, dust, scuff, foot_z, f"sv_shell_{tag}")
    m_chas = worn_metal(chassis, bare, accent, wear, 0.5, mud, dust, scuff, foot_z, f"sv_chassis_{tag}")
    m_leg = worn_metal((0.040, 0.040, 0.045), (0.075, 0.072, 0.070), accent, wear * 0.35, 0.6, mud, dust * 0.4, scuff * 0.5, foot_z, f"sv_leg_{tag}")
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
        elif legs_too and base in leg_parts:
            o.data.materials[0] = m_leg


def _emissives(built, strength, colour=None):
    seen = set()
    for o in built.parts:
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


def _fix_lamp(built, energy=0.0, aim_down_deg=9.0):
    """build.py:312 aims the lamp backwards; re-aim +X (ART-DIRECTION 0), white, tilted down."""
    if not built.lamp:
        return
    built.lamp.rotation_euler = Euler((0, -math.pi / 2 + math.radians(aim_down_deg), 0))
    built.lamp.data.energy = energy
    built.lamp.data.color = (1.00, 0.98, 0.95)


def machine(at=(0, 0, 0), yaw=0.0, chassis="surveyor", modules=None, team="player", wear=0.35, mud=0.3,
            dust=0.25, scuff=0.2, lamp=0.0, emis=None, walk=None, look=None, crouch=0.0, tag=None, name="AGENT"):
    """Build one machine with every fix applied. `walk` = seconds of trot toward its heading (the
    scene is then rendered mid-walk); `look` = a world point for the head."""
    tag = tag or f"{name}_{abs(hash(at)) % 10000}"
    cfg = P.default_config(chassis) if modules is None else P.AgentConfig(chassis=chassis, modules=modules)
    built = build_agent(cfg, name=name, at=at)
    if team == "player":
        _retint(built, PLAYER_SHELL, PLAYER_CHASSIS, wear, mud, dust, scuff, True, at[2], tag=tag)
        _emissives(built, 2.5 if emis is None else emis, BONE)
    elif team == "rival":
        _retint(built, RIVAL_SHELL, RIVAL_CHASSIS, wear, mud, dust, scuff, True, at[2], tag=tag)
        _emissives(built, 2.5 if emis is None else emis, EMBER)
    else:  # fresh, unpainted-by-the-cave
        _retint(built, (0.70, 0.68, 0.62), PLAYER_CHASSIS, wear, mud, dust, scuff, True, at[2], tag=tag)
        _emissives(built, 2.5 if emis is None else emis, BONE)
    _fix_lamp(built, lamp)
    arm = built.arm
    arm.rotation_euler = Euler((0, 0, yaw))
    R = Matrix.Rotation(yaw, 3, "Z")
    for e, nb in zip(built.feet, arm["leg_neutral"]):
        e.location = Vector(at) + R @ Vector(nb)
    if look is not None:
        built.look.location = Vector(look)
    else:
        built.look.location = Vector(at) + R @ Vector((2.0, 0, 0.35))
    if walk:
        mv = Mover(built)
        last = script(mv, f"stand 0.2; walk {walk} 0.45 0 trot; stand 0.2")
        bpy.context.scene.frame_set(max(1, last // 2))
    if crouch:
        arm.location = Vector(arm.location) - Vector((0, 0, crouch))
    bpy.context.view_layer.update()
    return built


def wreck(at=(0, 0, 0), yaw=0.0, tag="wreck"):
    """av_probe's wreck pose, the one that read as fallen: ride height 0, 40 deg roll, feet placed
    by hand, one tibia gone, the compute hatch shed. Emissives dead; the handle the only clean thing."""
    ch = P.CHASSIS["surveyor"]
    old = ch.ride_height
    ch.ride_height = 0.055
    cfg = P.default_config("surveyor")
    built = build_agent(cfg, name="WRECK", at=at)
    ch.ride_height = old
    _retint(built, (0.30, 0.28, 0.25), (0.045, 0.045, 0.050), 0.95, 1.0, 0.8, 0.9, True, at[2], tag=tag)
    _emissives(built, 0.0)
    _fix_lamp(built, 0.0)
    arm = built.arm
    arm.rotation_euler = Euler((math.radians(40), 0, yaw + math.radians(-12)))
    arm.location = Vector(at) + Vector((0, 0, -0.012))
    R = Matrix.Rotation(yaw, 3, "Z")
    splay = {0: (0.34, 0.24, 0.02), 1: (0.24, -0.14, 0.20), 2: (-0.20, 0.30, 0.02), 3: (-0.32, -0.06, 0.16)}
    for i, p in splay.items():
        if i < len(built.feet):
            built.feet[i].location = Vector(at) + R @ Vector(p)
    for o in list(built.parts):
        base = o.name.split(".")[0]
        idx = o.name.split(".")[1] if "." in o.name else ""
        if base in ("tibia", "tibia_knuckle", "foot") and idx.startswith("3"):
            built.parts.remove(o); bpy.data.objects.remove(o, do_unlink=True)
        elif base == "hatch_compute":
            built.parts.remove(o); bpy.data.objects.remove(o, do_unlink=True)
    pan = G.box("shed_panel", (0.16, 0.10, 0.004), Vector(at) + R @ Vector((0.20, -0.26, 0.003)), bevel=0.002, col=col())
    pan.rotation_euler = Euler((0, 0.05, 0.8 + yaw))
    pan.data.materials.append(worn_metal((0.30, 0.28, 0.25), (0.20, 0.19, 0.18), (0.85, 0.45, 0.10), 0.95, 0.6, 1.0, 0.8, 0.9, at[2], "sv_panel"))
    bpy.context.view_layer.update()
    return built


# =====================================================================================
# the player: a mannequin for scale only, and the pendant / cable (PROPOSAL, G1-G3)
# =====================================================================================
def mannequin(at=(0, 0, 0), yaw=0.0, pose="pendant", name="PLAYER"):
    """1.75 m, faceless, a matte dark rain jacket. Scale and gesture only: nobody has designed a
    person for this game and this is not that design."""
    jacket = simple("jacket", (0.10, 0.105, 0.11), 0.8)
    skin = simple("skin_m", (0.40, 0.30, 0.24), 0.6)
    R = Matrix.Rotation(yaw, 4, "Z")
    T = Matrix.Translation(Vector(at))
    parts = []

    def put(o):
        o.matrix_world = T @ R @ o.matrix_world
        parts.append(o)
        return o
    for sy in (-1, 1):
        put(G.cyl(f"{name}_leg.{sy}", 0.075, 0.07, 0.95, (0, sy * 0.11, 0.525), verts=12, col=col()))
    put(G.box(f"{name}_hips", (0.26, 0.38, 0.22), (0, 0, 1.06), bevel=0.05, col=col()))
    put(G.box(f"{name}_torso", (0.28, 0.44, 0.52), (0.0, 0, 1.40), bevel=0.06, col=col()))
    put(G.sphere(f"{name}_head", 0.11, (0.04, 0, 1.73), col=col(), seg=20))
    put(G.sphere(f"{name}_hood", 0.125, (-0.02, 0, 1.75), col=col(), seg=20))
    if pose == "pendant":
        for sy in (-1, 1):
            sh = Vector((0.0, sy * 0.25, 1.58)); el = Vector((0.06, sy * 0.28, 1.28)); hd = Vector((0.32, sy * 0.10, 1.20))
            put(G.segment(f"{name}_uarm.{sy}", sh, el, 0.05, 0.045, verts=10, col=col()))
            put(G.segment(f"{name}_farm.{sy}", el, hd, 0.045, 0.04, verts=10, col=col()))
            put(G.sphere(f"{name}_hand.{sy}", 0.045, hd, col=col(), seg=12))
    else:
        for sy in (-1, 1):
            sh = Vector((0.0, sy * 0.25, 1.58)); el = Vector((0.0, sy * 0.28, 1.28)); hd = Vector((0.04, sy * 0.27, 0.98))
            put(G.segment(f"{name}_uarm.{sy}", sh, el, 0.05, 0.045, verts=10, col=col()))
            put(G.segment(f"{name}_farm.{sy}", el, hd, 0.045, 0.04, verts=10, col=col()))
            put(G.sphere(f"{name}_hand.{sy}", 0.045, hd, col=col(), seg=12))
    for o in parts:
        G.set_material(o, skin if o.name.endswith("_head") or "_hand" in o.name else jacket)
    hand_c = T @ R @ Vector((0.34, 0, 1.20))
    return hand_c


def pendant(at, rot=(0, 0, 0), screen_img=None, cable_to=None, cable_coiled=False, name="PENDANT"):
    """The wired pendant: a screen, a row of six block keys, a scrub wheel, a cable. Built
    face-up at the origin then placed. PROPOSAL Q2: the demonstration interface is wired."""
    pk, dk = pale_kit(), dark_kit()
    R = Euler(rot).to_matrix().to_4x4()
    T = Matrix.Translation(Vector(at))
    parts = []

    def put(o, m):
        o.matrix_world = T @ R @ o.matrix_world
        G.set_material(o, m)
        parts.append(o)
        return o
    put(G.box(f"{name}_body", (0.20, 0.135, 0.032), (0, 0, 0), bevel=0.006, col=col()), pk)
    scr = G.plane(f"{name}_screen", 1.0, (0, 0.024, 0.0165), col=col())
    scr.scale = (0.165, 0.075, 1.0)
    bpy.context.view_layer.update()
    put(scr, screen(f"{name}_scr", screen_img, 1.6))
    for k in range(6):
        put(G.box(f"{name}_key.{k}", (0.022, 0.014, 0.006), (-0.0625 + k * 0.025, -0.045, 0.018), bevel=0.001, col=col()), dk)
    put(G.cyl(f"{name}_wheel", 0.022, 0.022, 0.012, (0.108, -0.02, 0.0), rot=(0, math.pi / 2, 0), verts=16, col=col()), dk)
    put(G.box(f"{name}_grip.-1", (0.012, 0.13, 0.036), (-0.106, 0, 0), bevel=0.004, col=col()), rubber_black())
    put(G.box(f"{name}_grip.1", (0.012, 0.13, 0.036), (0.106, 0, 0), bevel=0.004, col=col()), rubber_black())
    origin = T @ R @ Vector((0, -0.07, 0))
    if cable_to is not None:
        end = Vector(cable_to)
        drop = T @ R @ Vector((0, -0.25, -0.05))
        mid = (origin + end) / 2
        pts = [origin, drop, Vector((mid.x, mid.y, min(origin.z, end.z) * 0.15 + 0.03)), end + Vector((-0.06, 0, 0.0)), end]
        G.set_material(G.tube_along(f"{name}_cable", pts, 0.006, verts=6, col=col()), rubber_black())
    elif cable_coiled:
        pts = []
        for i in range(60):
            a = i / 60 * math.pi * 2 * 3.5
            pts.append(origin + Vector((0.12 * math.cos(a), 0.12 * math.sin(a) - 0.16, -0.015 * i / 60)))
        G.set_material(G.tube_along(f"{name}_coil", pts, 0.006, verts=6, col=col()), rubber_black())
    return parts


def charge_port_world(built):
    """World position of a built machine's charge port (build.py: rear, -W*0.15, below the seam)."""
    for o in built.parts:
        if o.name.split(".")[0] == "charge_port":
            bpy.context.view_layer.update()
            return Vector(o.matrix_world.translation)
    return Vector(built.arm.matrix_world.translation)


def plug(at, direction, name="PLUG"):
    """A connector body sitting in the charge port, its cable leaving along `direction`."""
    d = Vector(direction).normalized()
    a = Vector(at)
    G.set_material(G.segment(f"{name}_body", a, a + d * 0.035, 0.012, 0.012, verts=10, col=col()), dark_kit())
    G.set_material(G.segment(f"{name}_boot", a + d * 0.035, a + d * 0.06, 0.008, 0.007, verts=8, col=col()), rubber_black())
    return a + d * 0.06


# =====================================================================================
# rain (an experiment): a streak card in front of the camera
# =====================================================================================
def rain_card(cam_loc, aim, dist=0.9, density=0.955):
    """Streaks as a procedural card 0.9 m in front of the camera. Not a particle system, not
    a volume; a cheap trick for a board frame and marked as such in NOTES."""
    cam_loc, aim = Vector(cam_loc), Vector(aim)
    fwd = (aim - cam_loc).normalized()
    m, nt, out = M._new("rain_card")
    n, L = nt.nodes, nt.links.new
    tc = n.new("ShaderNodeTexCoord")
    mp = n.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (140.0, 1.6, 1.0)
    L(tc.outputs["Object"], mp.inputs["Vector"])
    nz = n.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 1.0; nz.inputs["Detail"].default_value = 2.0
    L(mp.outputs["Vector"], nz.inputs["Vector"])
    ramp = n.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = density; ramp.color_ramp.elements[1].position = min(0.999, density + 0.03)
    L(nz.outputs["Fac"], ramp.inputs["Fac"])
    tr = n.new("ShaderNodeBsdfTransparent")
    em = n.new("ShaderNodeEmission"); em.inputs["Color"].default_value = (0.7, 0.75, 0.85, 1); em.inputs["Strength"].default_value = 0.35
    mix = n.new("ShaderNodeMixShader")
    L(ramp.outputs["Color"], mix.inputs["Fac"]); L(tr.outputs[0], mix.inputs[1]); L(em.outputs[0], mix.inputs[2])
    L(mix.outputs[0], out.inputs[0])
    card = G.plane("rain_card", 1.0, (0, 0, 0), col=col())
    card.scale = (1.9, 1.3, 1.0)
    q = fwd.to_track_quat("-Z", "Y")
    card.rotation_euler = q.to_euler()
    card.location = cam_loc + fwd * dist
    G.set_material(card, m)
    card.visible_shadow = False
    card.visible_diffuse = False
    card.visible_glossy = False
    return card


# =====================================================================================
# underground end: the shaft chamber, for the descent strip
# =====================================================================================
def underground(flood_w=2500.0, tube_top=24.0):
    """A P2 chamber with the shaft entering through its roof as a rectangular rock tube. The light
    at the top is the pit-head floodlight (SKY colour) plus a camera-visible sky card, because
    real sky through a shaft this deep is black on the floor (see NOTES)."""
    rk = cave_rock(0.45)
    E.chamber(radius=7.0, height=9.6, mat=rk, aven=False, rubble=14)
    dome = bpy.data.objects["chamber"]
    _punch_faces(dome, 0.6, 0.4, SHAFT_W / 2 + 0.25, SHAFT_D / 2 + 0.25, 5.0)   # the roof opening the tube enters through
    _tube("shaft_from_below", SHAFT_W + 0.2, SHAFT_D + 0.2, 7.0, tube_top, at=(0.6, 0.4), mat=rk)
    sky_card = G.plane("sky_card", 1.0, (0.6, 0.4, tube_top + 0.02), col=col())
    sky_card.scale = (SHAFT_W + 0.4, SHAFT_D + 0.4, 1.0)
    G.set_material(sky_card, emissive("sky_card_m", SKY, 1.0))
    sky_card.visible_diffuse = False; sky_card.visible_glossy = False; sky_card.visible_shadow = False
    E.add_light("FLOOD_BELOW", "SPOT", (0.6, 0.4, tube_top - 0.5), flood_w, SKY, size=0.25, spot_deg=30, blend=0.3, aim=(0.6, 0.4, 0))
    return rk


# =====================================================================================
# camera and output
# =====================================================================================
def camera(loc, aim, focal=35.0, fstop=None, clip_start=0.05, sensor=36.0):
    cd = bpy.data.cameras.new("CAM")
    cd.lens = focal
    cd.sensor_width = sensor
    cd.clip_start = clip_start
    cd.clip_end = 2000.0
    if fstop:
        cd.dof.use_dof = True
        cd.dof.aperture_fstop = fstop
        cd.dof.focus_distance = (Vector(loc) - Vector(aim)).length
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
    bpy.context.scene.camera = cam
    return cam


def render(path, samples=40, res=(960, 600), exposure=0.0, look="AgX - Medium High Contrast"):
    E.settings(samples=samples, res=res, look=look, exposure=exposure)
    sc = bpy.context.scene
    sc.cycles.max_bounces = 5
    sc.cycles.diffuse_bounces = 3
    sc.cycles.glossy_bounces = 3
    sc.cycles.transmission_bounces = 4
    sc.cycles.transparent_max_bounces = 8
    sc.cycles.volume_bounces = 1
    sc.cycles.volume_step_rate = 2.0
    sc.cycles.volume_max_steps = 128
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("WROTE", path)


def project(points):
    """Screen-space (0..1, y up) positions of world points through the scene camera, for PIL overlays."""
    from bpy_extras.object_utils import world_to_camera_view
    sc = bpy.context.scene
    bpy.context.view_layer.update()
    return [tuple(world_to_camera_view(sc, sc.camera, Vector(p))) for p in points]
