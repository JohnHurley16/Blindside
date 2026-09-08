"""Second-pass lighting probes: the cave as it actually is, not as a studio dome.

The first pass lit the agent inside `render.cave()` -- an ico-sphere dome 3.4 m across
with the agent in the middle. That is the wrong test environment for a carried lamp:
a forward spot in an open room has nothing to hit inside its range, so of course it
returns nothing. The real cave is a warren -- 16.0% open, passages 2.4-3.6 m wide at
0.6 m/cell -- and a forward spot in a 3 m passage hits a wall at 3-6 m.

This module builds:
  * `passage()`   a straight-ish corridor of given width/height/length, displaced rock
  * `chamber()`   a dome of given radius/height, with an aven above if asked
  * `rock()`      the wet_rock material with albedo, warmth, wetness and waterline
                  exposed as parameters, mapped in WORLD space (not object space)
  * `assayer()`   THE-MACHINERY.md 2.1, built to metres at 0.6 m/cell
  * `stats()`     luminance histogram of a rendered PNG

Nothing here is production code. It exists to turn art-direction opinions into numbers.
"""
import math
import random

import bpy
from mathutils import Vector

from agent_model import geometry as G


# ---------------------------------------------------------------------------------------
# rock, parameterised
# ---------------------------------------------------------------------------------------
def rock(name="rock", albedo_lo=0.035, albedo_hi=0.30, warm=1.0, wet=0.35,
         waterline=None, bed_scale=0.9, fracture_scale=6.0, bump=0.9):
    """One rock material, four scalars, world-space mapped.

    albedo_lo/hi   diffuse reflectance at the dark and light end of the bedding ramp
    warm           1.0 = the buff/ochre of a wet limestone; 0.0 = neutral grey
    wet            0..1 global wetness -> roughness down, spec up
    waterline      world z of the water surface, or None. Below it: wet, darker, glossy.
                   Just above it: a tide mark 0.12 m tall, lighter and matte (mineral crust)
    """
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    n = nt.nodes
    L = nt.links.new
    out = n.new("ShaderNodeOutputMaterial")
    b = n.new("ShaderNodeBsdfPrincipled")
    L(b.outputs[0], out.inputs[0])

    # world-space coordinates. `Object` on a mesh with applied transforms at the origin is
    # world space; the point of the probe is that this is what a 120 m cave needs and what
    # materials.wet_rock() does NOT do (it uses per-object coords, which swim and tile).
    geo = n.new("ShaderNodeNewGeometry")

    bed = n.new("ShaderNodeTexNoise")
    bed.inputs["Scale"].default_value = bed_scale
    bed.inputs["Detail"].default_value = 12.0
    bed.inputs["Roughness"].default_value = 0.62
    L(geo.outputs["Position"], bed.inputs["Vector"])

    frac = n.new("ShaderNodeTexVoronoi")
    frac.inputs["Scale"].default_value = fracture_scale
    L(geo.outputs["Position"], frac.inputs["Vector"])

    # colour: a two-stop ramp between albedo_lo and albedo_hi, hue pushed warm
    def tone(v):
        return (v * (1.0 + 0.22 * warm), v * (1.0 - 0.02 * warm), v * (1.0 - 0.28 * warm), 1.0)

    ramp = n.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.28
    ramp.color_ramp.elements[0].color = tone(albedo_lo)
    ramp.color_ramp.elements[1].position = 0.78
    ramp.color_ramp.elements[1].color = tone(albedo_hi)
    L(bed.outputs["Fac"], ramp.inputs["Fac"])

    colour = ramp.outputs["Color"]
    rough_base = n.new("ShaderNodeMath")
    rough_base.operation = "MULTIPLY_ADD"
    rough_base.inputs[1].default_value = -0.25
    rough_base.inputs[2].default_value = 0.96 - 0.45 * wet
    L(bed.outputs["Fac"], rough_base.inputs[0])
    rough = rough_base.outputs[0]

    if waterline is not None:
        sep = n.new("ShaderNodeSeparateXYZ")
        L(geo.outputs["Position"], sep.inputs["Vector"])
        # submerged mask: 1 below the waterline, 0 above, 4 cm of blend
        sub = n.new("ShaderNodeMapRange")
        sub.inputs["From Min"].default_value = waterline
        sub.inputs["From Max"].default_value = waterline - 0.04
        sub.inputs["To Min"].default_value = 0.0
        sub.inputs["To Max"].default_value = 1.0
        sub.clamp = True
        L(sep.outputs["Z"], sub.inputs["Value"])
        # tide mark: a band from waterline to waterline+0.12, mineral crust
        tide = n.new("ShaderNodeMapRange")
        tide.inputs["From Min"].default_value = waterline + 0.14
        tide.inputs["From Max"].default_value = waterline + 0.005
        tide.inputs["To Min"].default_value = 0.0
        tide.inputs["To Max"].default_value = 1.0
        tide.clamp = True
        L(sep.outputs["Z"], tide.inputs["Value"])

        wetc = n.new("ShaderNodeMix")
        wetc.data_type = "RGBA"
        wetc.inputs["B"].default_value = tone(albedo_lo * 0.6)   # submerged: darker
        L(sub.outputs["Result"], wetc.inputs["Factor"])
        L(colour, wetc.inputs["A"])

        crust = n.new("ShaderNodeMix")
        crust.data_type = "RGBA"
        crust.inputs["B"].default_value = tone(min(albedo_hi * 1.7, 0.72))  # crust: pale
        L(tide.outputs["Result"], crust.inputs["Factor"])
        L(wetc.outputs["Result"], crust.inputs["A"])
        colour = crust.outputs["Result"]

        wr = n.new("ShaderNodeMix")
        wr.data_type = "FLOAT"
        wr.inputs["B"].default_value = 0.10        # submerged rock is glossy
        L(sub.outputs["Result"], wr.inputs["Factor"])
        L(rough, wr.inputs["A"])
        rough = wr.outputs["Result"]

    L(colour, b.inputs["Base Color"])
    L(rough, b.inputs["Roughness"])
    b.inputs["Specular IOR Level"].default_value = 0.35

    bmp2 = n.new("ShaderNodeBump")
    bmp2.inputs["Strength"].default_value = 0.35
    L(frac.outputs["Distance"], bmp2.inputs["Height"])
    bmp = n.new("ShaderNodeBump")
    bmp.inputs["Strength"].default_value = bump
    L(bed.outputs["Fac"], bmp.inputs["Height"])
    L(bmp2.outputs["Normal"], bmp.inputs["Normal"])
    L(bmp.outputs["Normal"], b.inputs["Normal"])
    return m


# ---------------------------------------------------------------------------------------
# environments
# ---------------------------------------------------------------------------------------
def _displace(obj, scale, strength, depth=5, mid=0.5):
    t = bpy.data.textures.new(f"{obj.name}_noise", "CLOUDS")
    t.noise_scale = scale
    t.noise_depth = depth
    d = obj.modifiers.new("disp", "DISPLACE")
    d.texture = t
    d.strength = strength
    d.mid_level = mid
    return obj


def passage(width=3.0, height=4.8, length=18.0, mat=None, seed=5, rubble=10, col=None):
    """A corridor along +X, centred on the origin at x=0, floor at z=0.

    Built as a stretched, inverted, displaced cylinder: a real passage cross-section is
    closer to a lens than a box, and the displacement makes it read as rock rather
    than as a tube.
    """
    col = col or G.new_collection("CAVE")
    # Build unrotated (length along local Z), scale, APPLY, then rotate. Scaling a
    # rotated object scales along its rotated local axes, which is how the first
    # version of this ended up 48 m long and 2 m tall with its floor above the agent.
    bpy.ops.mesh.primitive_cylinder_add(vertices=40, radius=1.0, depth=length, location=(0, 0, 0))
    o = bpy.context.object
    o.name = "passage"
    o.scale = (height / 2.0, width / 2.0, 1.0)   # Ry(90) sends local X to world -Z
    bpy.ops.object.transform_apply(scale=True)
    o.rotation_euler = (0, math.pi / 2, 0)
    bpy.ops.object.transform_apply(rotation=True)
    o.location = (length * 0.35, 0, height / 2.0 + 0.55)   # keep the tube floor clear of z=0
    bpy.ops.object.transform_apply(location=True)
    for c in list(o.users_collection):
        c.objects.unlink(o)
    col.objects.link(o)
    sub = o.modifiers.new("subsurf", "SUBSURF")
    sub.levels = sub.render_levels = 1
    _displace(o, 1.1, width * 0.16, depth=6)
    _displace(o, 0.28, width * 0.055, depth=5)
    o.data.shade_smooth()
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.flip_normals()
    bpy.ops.object.mode_set(mode="OBJECT")
    G.set_material(o, mat)

    floor = G.plane("floor", length * 1.6, (length * 0.35, 0, 0.0), col=col, subdiv=44)
    _displace(floor, 0.7, 0.16, depth=5, mid=0.55)
    floor.data.shade_smooth()
    G.set_material(floor, mat)

    rng = random.Random(seed)
    for i in range(rubble):
        r = rng.uniform(0.06, 0.30)
        x = rng.uniform(-2.0, length * 0.8)
        y = rng.uniform(-width / 2 + 0.3, width / 2 - 0.3)
        if abs(x) < 1.0 and abs(y) < 0.6:
            continue
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=r, location=(x, y, r * 0.4))
        rk = bpy.context.object
        rk.name = f"rubble.{i}"
        rk.scale = (rng.uniform(0.8, 1.6), rng.uniform(0.8, 1.6), rng.uniform(0.35, 0.8))
        rk.rotation_euler = (rng.uniform(0, 3), rng.uniform(0, 3), rng.uniform(0, 3))
        _displace(rk, 0.2, r * 1.1, depth=4)
        rk.data.shade_smooth()
        for c in list(rk.users_collection):
            c.objects.unlink(rk)
        col.objects.link(rk)
        G.set_material(rk, mat)
    return col


def chamber(radius=7.0, height=9.0, mat=None, seed=11, aven=False, col=None, rubble=16):
    col = col or G.new_collection("CAVE")
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=5, radius=radius, location=(0, 0, height * 0.30))
    o = bpy.context.object
    o.name = "chamber"
    o.scale = (1.0, 1.0, height / (radius * 1.55))
    bpy.ops.object.transform_apply(scale=True)
    for c in list(o.users_collection):
        c.objects.unlink(o)
    col.objects.link(o)
    _displace(o, 1.5, radius * 0.16, depth=6)
    _displace(o, 0.35, radius * 0.045, depth=5)
    o.data.shade_smooth()
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.flip_normals()
    bpy.ops.object.mode_set(mode="OBJECT")
    G.set_material(o, mat)

    floor = G.plane("floor", radius * 4, (0, 0, 0), col=col, subdiv=50)
    _displace(floor, 0.8, 0.22, depth=5, mid=0.55)
    floor.data.shade_smooth()
    G.set_material(floor, mat)

    if aven:
        bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=2.1, depth=14.0,
                                            location=(0.6, 0.4, height + 5.0))
        a = bpy.context.object
        a.name = "aven"
        for c in list(a.users_collection):
            c.objects.unlink(a)
        col.objects.link(a)
        _displace(a, 1.4, 0.9, depth=5)
        a.data.shade_smooth()
        bpy.context.view_layer.objects.active = a
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.mesh.flip_normals()
        bpy.ops.object.mode_set(mode="OBJECT")
        G.set_material(a, mat)

    rng = random.Random(seed)
    for i in range(rubble):
        r = rng.uniform(0.10, 0.55)
        ang = rng.uniform(0, 6.283)
        d = rng.uniform(1.6, radius * 0.85)
        x, y = math.cos(ang) * d, math.sin(ang) * d
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=r, location=(x, y, r * 0.4))
        rk = bpy.context.object
        rk.name = f"rubble.{i}"
        rk.scale = (rng.uniform(0.8, 1.7), rng.uniform(0.8, 1.7), rng.uniform(0.3, 0.75))
        rk.rotation_euler = (rng.uniform(0, 3), rng.uniform(0, 3), rng.uniform(0, 3))
        _displace(rk, 0.25, r * 1.2, depth=4)
        rk.data.shade_smooth()
        for c in list(rk.users_collection):
            c.objects.unlink(rk)
        col.objects.link(rk)
        G.set_material(rk, mat)
    return col


def world(fog=0.012, ambient=0.0):
    """The world background. `ambient` is the unsourced sky term -- the thing this
    project should not have. Default 0: the dark is actually dark."""
    w = bpy.context.scene.world or bpy.data.worlds.new("World")
    bpy.context.scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.inputs["Color"].default_value = (0.35, 0.42, 0.55, 1)
    bg.inputs["Strength"].default_value = ambient
    nt.links.new(bg.outputs[0], out.inputs["Surface"])
    if fog > 0:
        vol = nt.nodes.new("ShaderNodeVolumeScatter")
        vol.inputs["Density"].default_value = fog
        vol.inputs["Anisotropy"].default_value = 0.55
        vol.inputs["Color"].default_value = (0.85, 0.86, 0.9, 1)
        nt.links.new(vol.outputs[0], out.inputs["Volume"])
    return w


# ---------------------------------------------------------------------------------------
# THE ASSAYER -- THE-MACHINERY.md 2.1, at 0.6 m per cell
# ---------------------------------------------------------------------------------------
CELL = 0.6


def assayer(at=(0, 0, 0), aim_deg=0.0, hammer_frac=0.0, mat_iron=None, mat_dark=None, col=None):
    """Cells from THE-MACHINERY.md 2.1, converted at 0.6 m/cell.

      footing  3 legs 120 deg, hub r=1.0c @ z=1.2c  ->  r=2.6c @ z=0
      mast     hex prism, 1.6c across flats, z = 1.2c -> 11.0c        (0.96 m x 6.60 m)
      boom     7.0c x 0.9c at z = 9.0c, 5 cross-ribs at 1.4c spacing,
               2.4c wide at root tapering to 1.2c at tip              (4.20 m at 5.40 m)
      cwt      2.2c stub opposite the boom with one 1.6c rib
      hammer   hex ring 2.0c across riding the mast; z is the variable
      bolts    8 markers at r = 3.4c -- the old service platform

    `hammer_frac` 0 = at the foot of the mast (just fallen); 1 = at the top (wound).
    """
    c = CELL
    col = col or G.new_collection("ASSAYER")
    base = Vector(at)
    objs = []

    def put(o, m):
        o.location = o.location + base
        G.set_material(o, m)
        for cc in list(o.users_collection):
            cc.objects.unlink(o)
        col.objects.link(o)
        objs.append(o)
        return o

    hub_r, hub_z, pad_r = 1.0 * c, 1.2 * c, 2.6 * c
    # footing: three splayed legs, box-section, from the hub down and out to anchor pads
    for k in range(3):
        a = math.radians(90 + 120 * k)
        top = Vector((math.cos(a) * hub_r, math.sin(a) * hub_r, hub_z))
        foot = Vector((math.cos(a) * pad_r, math.sin(a) * pad_r, 0.02))
        put(G.strut(f"as_leg{k}", top, foot, 0.34 * c, 0.30 * c, 0.46 * c, 0.22 * c, bevel=0.01), mat_iron)
        put(G.box(f"as_pad{k}", (0.8 * c, 0.8 * c, 0.16 * c),
                  (math.cos(a) * pad_r, math.sin(a) * pad_r, 0.06), bevel=0.01), mat_iron)
        # a diagonal tie between legs: this is what makes a footing read as engineered
        a2 = math.radians(90 + 120 * ((k + 1) % 3))
        put(G.segment(f"as_tie{k}",
                      Vector((math.cos(a) * pad_r * 0.82, math.sin(a) * pad_r * 0.82, 0.30 * c)),
                      Vector((math.cos(a2) * pad_r * 0.82, math.sin(a2) * pad_r * 0.82, 0.30 * c)),
                      0.05 * c, 0.05 * c, verts=8), mat_dark)
    put(G.cyl("as_hub", hub_r * 1.15, hub_r * 0.95, 0.5 * c, (0, 0, hub_z + 0.1 * c), verts=6, bevel=0.01), mat_iron)

    # mast: hexagonal prism 1.6c across flats. r = flats/2 / cos(30)
    mast_r = (1.6 * c / 2) / math.cos(math.radians(30))
    mast_z0, mast_z1 = 1.2 * c, 11.0 * c
    put(G.cyl("as_mast", mast_r, mast_r * 0.86, mast_z1 - mast_z0,
              (0, 0, (mast_z0 + mast_z1) / 2), verts=6), mat_iron)
    # mast lacing: the rungs the hammer ratchets against, every 0.5 c
    z = mast_z0 + 0.4 * c
    i = 0
    while z < mast_z1 - 0.3 * c:
        put(G.cyl(f"as_rung{i}", mast_r * 1.12, mast_r * 1.12, 0.05 * c, (0, 0, z), verts=6), mat_dark)
        z += 0.5 * c
        i += 1

    # everything above the bearing rotates: build it, then rotate about Z
    rot = math.radians(aim_deg)

    def spin(v):
        return Vector((v.x * math.cos(rot) - v.y * math.sin(rot),
                       v.x * math.sin(rot) + v.y * math.cos(rot), v.z))

    boom_z = 9.0 * c
    put(G.cyl("as_bearing", mast_r * 1.9, mast_r * 1.7, 0.7 * c, (0, 0, boom_z - 0.1 * c), verts=12), mat_dark)
    # boom spine: root at the mast, tip 7.0c out
    root = spin(Vector((0.5 * c, 0, boom_z)))
    tip = spin(Vector((7.0 * c, 0, boom_z)))
    put(G.strut("as_boom", root, tip, 0.9 * c, 0.55 * c, 0.5 * c, 0.30 * c, bevel=0.008), mat_iron)
    # five cross-ribs, 1.4c spacing, 2.4c at the root tapering to 1.2c at the tip
    for k in range(5):
        t = (k + 0.6) / 5.0
        halfw = (2.4 * c - (2.4 - 1.2) * c * t) / 2
        x = 1.0 * c + 1.4 * c * k
        a = spin(Vector((x, -halfw, boom_z)))
        b = spin(Vector((x, halfw, boom_z)))
        put(G.segment(f"as_rib{k}", a, b, 0.10 * c, 0.10 * c, verts=8), mat_iron)
        # the transducer cans hanging under each rib tip: this is the "array"
        for s in (-1, 1):
            p = spin(Vector((x, s * halfw * 0.92, boom_z - 0.22 * c)))
            put(G.cyl(f"as_can{k}{s}", 0.16 * c, 0.16 * c, 0.30 * c, p, verts=10), mat_dark)
    # counterweight: 2.2c stub opposite with one 1.6c rib
    cw = spin(Vector((-2.2 * c, 0, boom_z)))
    put(G.strut("as_cwt_arm", spin(Vector((-0.5 * c, 0, boom_z))), cw, 0.7 * c, 0.5 * c, 0.6 * c, 0.45 * c, bevel=0.008), mat_iron)
    put(G.box("as_cwt", (0.9 * c, 1.6 * c, 0.9 * c), cw, bevel=0.02), mat_dark)

    # hammer: hex ring 2.0c across, riding the mast
    ham_z = mast_z0 + 0.9 * c + hammer_frac * (boom_z - mast_z0 - 2.4 * c)
    put(G.cyl("as_hammer", 2.0 * c / 2 / math.cos(math.radians(30)), 2.0 * c / 2 / math.cos(math.radians(30)),
              0.85 * c, (0, 0, ham_z), verts=6, bevel=0.012), mat_iron)
    put(G.cyl("as_hammer_bore", mast_r * 1.2, mast_r * 1.2, 0.9 * c, (0, 0, ham_z), verts=6), mat_dark)
    # anvil: what the hammer lands on, at the foot of the mast
    put(G.cyl("as_anvil", 1.3 * c, 1.6 * c, 0.55 * c, (0, 0, 0.27 * c), verts=12, bevel=0.01), mat_iron)

    # bolt ring: 8 markers at r = 3.4c, the old service platform
    for k in range(8):
        a = math.radians(45 * k + 22)
        put(G.cyl(f"as_bolt{k}", 0.09 * c, 0.07 * c, 0.34 * c,
                  (math.cos(a) * 3.4 * c, math.sin(a) * 3.4 * c, 0.17 * c), verts=8), mat_dark)

    # header tank and the pipe that feeds it: THE-MACHINERY.md 1. Water winds the hammer.
    put(G.cyl("as_tank", 0.95 * c, 0.95 * c, 1.5 * c, (0, -2.3 * c, 3.4 * c), verts=16, bevel=0.02), mat_iron)
    put(G.cyl("as_tank_band", 1.02 * c, 1.02 * c, 0.10 * c, (0, -2.3 * c, 3.9 * c), verts=16), mat_dark)
    put(G.tube_along("as_pipe", [Vector((0, -2.3 * c, 2.6 * c)), Vector((0, -2.3 * c, 1.4 * c)),
                                 Vector((0, -1.0 * c, 0.9 * c)), Vector((0, -0.2 * c, 1.3 * c))],
                     0.11 * c, verts=10), mat_dark)
    return col, objs


# ---------------------------------------------------------------------------------------
# light rigs -- all diegetic
# ---------------------------------------------------------------------------------------
def add_light(name, kind, loc, energy, colour, size=0.1, spot_deg=None, blend=0.4, aim=None):
    d = bpy.data.lights.new(name, kind)
    d.energy = energy
    d.color = colour
    if kind == "SPOT":
        d.spot_size = math.radians(spot_deg or 50)
        d.spot_blend = blend
        d.shadow_soft_size = size
    elif kind == "AREA":
        d.size = size
    else:
        d.shadow_soft_size = size
    o = bpy.data.objects.new(name, d)
    bpy.context.scene.collection.objects.link(o)
    o.location = Vector(loc)
    if aim is not None:
        t = bpy.data.objects.new(name + "_aim", None)
        bpy.context.scene.collection.objects.link(t)
        t.location = Vector(aim)
        c = o.constraints.new("TRACK_TO")
        c.track_axis = "TRACK_NEGATIVE_Z"
        c.up_axis = "UP_Y"
        c.target = t
    return o


def settings(samples=64, res=(1100, 700), look="AgX - Medium High Contrast", exposure=0.0):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"
    cy = sc.cycles
    cy.device = "CPU"
    cy.samples = samples
    cy.use_denoising = True
    cy.max_bounces = 4
    cy.diffuse_bounces = 3
    cy.glossy_bounces = 2
    cy.transmission_bounces = 2
    cy.volume_bounces = 0
    cy.volume_step_rate = 6.0
    cy.volume_max_steps = 64
    cy.use_adaptive_sampling = True
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.look = look
    sc.view_settings.exposure = exposure
    sc.render.film_transparent = False
