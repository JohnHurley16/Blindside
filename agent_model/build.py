"""Assemble one agent: meshes, materials, armature with IK legs and a tracking head.

Conventions (motion.py relies on these):
  - The armature object AGENT_RIG is the body. Its origin is on the ground under the
    hull centre. Root motion = keyframe the armature's location / rotation.
  - Foot IK targets are empties FOOT.<i> in world space. Pole targets are bones
    pole.<i>, children of the hip so the knee plane turns with the hip.
  - LOOK is a world-space empty; the neck tracks it.
  - arm["leg_neutral"] holds each foot's neutral position relative to the armature.
"""
import math
import bpy
from mathutils import Vector, Matrix, Euler
from . import geometry as G
from . import materials as M
from .params import AgentConfig, CHASSIS, MODULES, validate


def _bone(arm_data, name, head, tail, parent=None, roll=0.0):
    b = arm_data.edit_bones.new(name)
    b.head, b.tail = Vector(head), Vector(tail)
    b.roll = roll
    if parent:
        b.parent = arm_data.edit_bones[parent]
    return b


def _parent_to_bone(obj, arm, bone_name):
    """Parent a mesh to a bone and keep its current world placement."""
    obj.parent = arm
    obj.parent_type = "BONE"
    obj.parent_bone = bone_name
    bone = arm.data.bones[bone_name]
    pm = arm.matrix_world @ bone.matrix_local @ Matrix.Translation((0, bone.length, 0))
    obj.matrix_parent_inverse = pm.inverted()


def _empty(name, loc, size=0.04, kind="PLAIN_AXES"):
    e = bpy.data.objects.new(name, None)
    e.empty_display_type = kind
    e.empty_display_size = size
    e.location = loc
    bpy.context.scene.collection.objects.link(e)
    return e


class Built:
    def __init__(self):
        self.arm = None
        self.feet = []
        self.look = None
        self.parts = []
        self.head_parts = []
        self.lamp = None
        self.collection = None


def build_agent(cfg: AgentConfig, name="AGENT", at=(0, 0, 0)):
    ch = validate(cfg)
    skin = cfg.skin
    col = G.new_collection(name)
    out = Built()
    out.collection = col
    mats = {
        "paint": M.painted_metal(skin), "accent": M.accent(skin), "metal": M.bare_metal(),
        "dark": M.bare_metal("dark_metal", (0.12, 0.12, 0.13), 0.5), "rubber": M.rubber(),
        "light": M.emissive(skin), "eye": M.emissive(skin, "eye", skin.light_strength * 2.5), "lens": M.lens(),
    }
    L, W, H = ch.hull
    zc = ch.ride_height + H / 2                       # hull centre height
    parts_by_bone = {}                                # bone name -> [objects]; None -> body

    def add(obj, mat, bone=None):
        G.set_material(obj, mats[mat])
        parts_by_bone.setdefault(bone, []).append(obj)
        out.parts.append(obj)
        return obj

    # ---- hull -------------------------------------------------------------------------
    add(G.box("hull", (L, W, H), (0, 0, zc), bevel=ch.hull_bevel, col=col), "paint")
    add(G.box("hull_chin", (L * 0.25, W * 0.7, H * 0.45), (L * 0.42, 0, zc - H * 0.15), rot=(0, 0.35, 0), bevel=ch.hull_bevel * 0.6, col=col), "paint")
    add(G.box("hull_tail", (L * 0.18, W * 0.6, H * 0.5), (-L * 0.5, 0, zc + H * 0.05), rot=(0, -0.25, 0), bevel=ch.hull_bevel * 0.5, col=col), "dark")
    # side light strips: the honest silhouette includes running lights
    for side in (1, -1):
        add(G.box(f"strip.{side}", (L * 0.55, 0.006, H * 0.08), (0.02, side * (W / 2 + 0.002), zc + H * 0.05), col=col), "light")
        add(G.box(f"stripe.{side}", (L * 0.7, 0.012, H * 0.12), (0.0, side * (W / 2 - 0.004), zc + H * 0.42), col=col), "accent")
    if ch.spine_rail:
        add(G.box("spine_rail", (L * 0.86, W * 0.28, 0.02), (-0.02, 0, zc + H / 2 + 0.008), bevel=0.006, col=col), "dark")
        for s in ch.slots:
            if s.facing[2] > 0.5:
                add(G.box(f"pad.{s.name}", (W * 0.34, W * 0.34, 0.012), (s.pos[0], s.pos[1], zc + s.pos[2] + 0.006), bevel=0.004, col=col), "metal")
    # belly skid and rear connector block
    add(G.box("skid", (L * 0.6, W * 0.5, 0.02), (0.0, 0, zc - H / 2 - 0.008), bevel=0.006, col=col), "rubber")
    add(G.box("connector", (0.05, W * 0.35, H * 0.3), (-L / 2 - 0.02, 0, zc - H * 0.15), bevel=0.006, col=col), "metal")

    # ---- head -------------------------------------------------------------------------
    nx, ny, nz = ch.head_pos
    neck_root = Vector((L / 2 + nx - L / 2, ny, zc + nz))     # head_pos is body frame from hull centre
    neck_root = Vector((nx, ny, zc + nz))
    hr = ch.head_radius
    head_c = neck_root + Vector((ch.head_neck + hr * 0.6, 0, hr * 0.15))
    add(G.segment("neck", neck_root, head_c, hr * 0.45, hr * 0.35, col=col), "dark", "neck")
    add(G.torus("neck_ring", hr * 0.5, hr * 0.08, neck_root + Vector((0.02, 0, 0)), rot=(0, math.pi / 2, 0), col=col), "metal", "neck")
    hb = G.box("head", (hr * 2.0, hr * 1.9, hr * 1.5), head_c, bevel=hr * 0.5, col=col)
    add(hb, "paint", "neck")
    eye_c = head_c + Vector((hr * 1.0, 0, hr * 0.05))
    add(G.torus("eye_ring", hr * 0.55, hr * 0.09, eye_c, rot=(0, math.pi / 2, 0), col=col), "metal", "neck")
    add(G.cyl("eye_lens", hr * 0.5, hr * 0.5, hr * 0.06, eye_c + Vector((hr * 0.02, 0, 0)), rot=(0, math.pi / 2, 0), col=col), "lens", "neck")
    add(G.cyl("eye_glow", hr * 0.32, hr * 0.32, hr * 0.02, eye_c + Vector((hr * 0.04, 0, 0)), rot=(0, math.pi / 2, 0), col=col), "eye", "neck")
    for side in (1, -1):    # passive 'ears': flat vanes that read as a face
        add(G.box(f"ear.{side}", (hr * 0.9, hr * 0.06, hr * 1.1), head_c + Vector((-hr * 0.2, side * hr * 1.0, hr * 0.55)),
                  rot=(side * 0.35, -0.25, 0), bevel=hr * 0.02, col=col), "dark", "neck")
    add(G.cyl("antenna", 0.004, 0.002, hr * 1.6, head_c + Vector((-hr * 0.5, 0, hr * 1.4)), col=col), "metal", "neck")
    add(G.sphere("antenna_tip", 0.007, head_c + Vector((-hr * 0.5, 0, hr * 2.2)), col=col, seg=12), "light", "neck")
    out.head_center = head_c

    # ---- modules ------------------------------------------------------------------------
    u = W
    for slot in ch.slots:
        mod = cfg.modules.get(slot.name)
        if not mod:
            continue
        base = Vector((slot.pos[0], slot.pos[1], zc + slot.pos[2]))
        f = Vector(slot.facing).normalized()
        rot = f.to_track_quat("Z", "Y").to_euler()
        objs = _module(mod, slot.name, u, col)
        for o, mat in objs:
            # objects were built pointing +Z at the origin; rotate to the facing and place
            o.matrix_world = Matrix.Translation(base) @ rot.to_matrix().to_4x4() @ o.matrix_world
            add(o, mat)

    # ---- legs ---------------------------------------------------------------------------
    neutral = []
    leg_geom = []
    for i, leg in enumerate(ch.legs):
        s = leg.side
        Hp = Vector((leg.hip[0], leg.hip[1], zc + leg.hip[2]))
        C = Hp + Vector((0, s * leg.coxa, 0))
        kdir = Vector((leg.knee_back, s * leg.splay, leg.knee_rise)).normalized()
        K = C + kdir * leg.femur
        F = Vector((Hp.x + leg.foot_fwd, K.y + s * leg.foot_out, 0.0))
        neutral.append((F.x, F.y, F.z))
        leg_geom.append((Hp, C, K, F))
        r = W * 0.10
        add(G.sphere(f"hip.{i}", r * 1.25, Hp, col=col), "dark")
        add(G.segment(f"coxa.{i}", Hp, C, r * 0.9, r * 0.9, col=col), "metal", f"coxa.{i}")
        add(G.segment(f"femur.{i}", C, K, r * 1.1, r * 0.9, col=col, bevel=0.003), "paint", f"femur.{i}")
        add(G.segment(f"femur_rod.{i}", C + Vector((0, 0, -r * 1.2)), K + Vector((0, 0, -r * 1.4)), r * 0.3, r * 0.3, col=col), "metal", f"femur.{i}")
        add(G.cyl(f"knee.{i}", r * 1.15, r * 1.15, r * 2.2, K, rot=(math.pi / 2, 0, 0), col=col), "dark", f"femur.{i}")
        add(G.torus(f"knee_ring.{i}", r * 1.1, r * 0.15, K + Vector((0, s * r * 1.15, 0)), rot=(math.pi / 2, 0, 0), col=col), "accent", f"femur.{i}")
        add(G.segment(f"tibia.{i}", K, F + Vector((0, 0, 0.03)), r * 0.85, r * 0.55, col=col, bevel=0.003), "paint", f"tibia.{i}")
        mid = (K + F) / 2
        add(G.segment(f"tibia_rod.{i}", K + Vector((0.01, -s * r * 0.9, -0.01)), mid + Vector((0.01, -s * r * 0.7, 0)), r * 0.25, r * 0.25, col=col), "metal", f"tibia.{i}")
        add(G.sphere(f"ankle.{i}", r * 0.6, F + Vector((0, 0, 0.035)), col=col, seg=12), "dark", f"tibia.{i}")
        foot = G.sphere(f"foot.{i}", r * 0.9, F + Vector((0, 0, r * 0.7)), col=col, seg=16)
        foot.scale = (1.3, 1.1, 0.8)
        add(foot, "rubber", f"tibia.{i}")

    # ---- armature -----------------------------------------------------------------------
    arm_data = bpy.data.armatures.new("AGENT_RIG")
    arm = bpy.data.objects.new("AGENT_RIG", arm_data)
    col.objects.link(arm)
    arm.location = (0, 0, 0)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    _bone(arm_data, "neck", neck_root, head_c)
    _bone(arm_data, "head", head_c, eye_c + Vector((hr * 0.2, 0, 0)), parent="neck")
    for i, (Hp, C, K, F) in enumerate(leg_geom):
        _bone(arm_data, f"coxa.{i}", Hp, C)
        _bone(arm_data, f"femur.{i}", C, K, parent=f"coxa.{i}")
        _bone(arm_data, f"tibia.{i}", K, F, parent=f"femur.{i}")
        pole = K + (K - (C + F) / 2).normalized() * 0.25
        _bone(arm_data, f"pole.{i}", pole, pole + Vector((0, 0, 0.03)), parent=f"coxa.{i}")
    bpy.ops.object.mode_set(mode="OBJECT")
    arm.data.display_type = "STICK"

    # targets
    feet = []
    for i, (Hp, C, K, F) in enumerate(leg_geom):
        e = _empty(f"FOOT.{i}", F, size=0.05, kind="SPHERE")
        feet.append(e)
    look = _empty("LOOK", head_c + Vector((2.0, 0, 0)), size=0.08, kind="CUBE")
    out.feet, out.look, out.arm = feet, look, arm

    # constraints
    pb = arm.pose.bones
    for i in range(len(leg_geom)):
        c = pb[f"coxa.{i}"].constraints.new("LOCKED_TRACK")
        c.target = feet[i]; c.track_axis = "TRACK_Y"; c.lock_axis = "LOCK_Z"
        ik = pb[f"tibia.{i}"].constraints.new("IK")
        ik.target = feet[i]
        ik.pole_target = arm; ik.pole_subtarget = f"pole.{i}"
        ik.chain_count = 2
        ik.use_tail = True
    trk = pb["neck"].constraints.new("DAMPED_TRACK")
    trk.target = look; trk.track_axis = "TRACK_Y"
    lim = pb["neck"].constraints.new("LIMIT_ROTATION")
    lim.use_limit_x = lim.use_limit_z = True
    lim.min_x, lim.max_x = -0.7, 0.7
    lim.min_z, lim.max_z = -1.0, 1.0
    lim.owner_space = "LOCAL"

    # pick the pole angle that keeps the rest pose (IK with a pole can flip the chain)
    _settle_pole_angles(arm, leg_geom)

    # parenting
    for bone, objs in parts_by_bone.items():
        for o in objs:
            if bone is None:
                o.parent = arm
            else:
                _parent_to_bone(o, arm, bone)
    # the head lamp rides on the neck bone
    lamp_data = bpy.data.lights.new("HEAD_LAMP", "SPOT")
    lamp_data.energy = 60; lamp_data.spot_size = math.radians(55); lamp_data.spot_blend = 0.4
    lamp_data.color = (skin.light[0] * 0.6 + 0.4, skin.light[1] * 0.6 + 0.4, skin.light[2] * 0.6 + 0.4)
    lamp_data.shadow_soft_size = 0.05
    lamp = bpy.data.objects.new("HEAD_LAMP", lamp_data)
    col.objects.link(lamp)
    lamp.location = eye_c + Vector((hr * 0.1, 0, 0))
    lamp.rotation_euler = Euler((0, math.pi / 2, 0))
    _parent_to_bone(lamp, arm, "neck")
    out.lamp = lamp

    arm["leg_neutral"] = [list(n) for n in neutral]
    arm["chassis"] = ch.name
    arm["hull_center_z"] = zc
    arm["step_height"] = 0.35 * ch.ride_height
    # move the whole thing to `at`
    arm.location = Vector(at)
    for e in feet:
        e.location = Vector(e.location) + Vector(at)
    look.location = Vector(look.location) + Vector(at)
    return out


def _settle_pole_angles(arm, leg_geom):
    """Try pole angles and keep the one that leaves the knee where it was built."""
    dg = bpy.context.evaluated_depsgraph_get()
    for i, (Hp, C, K, F) in enumerate(leg_geom):
        ik = arm.pose.bones[f"tibia.{i}"].constraints[-1]
        best, best_err = 0.0, 1e9
        for deg in range(-180, 180, 15):
            ik.pole_angle = math.radians(deg)
            dg.update()
            bpy.context.view_layer.update()
            ev = arm.evaluated_get(dg)
            knee = ev.matrix_world @ ev.pose.bones[f"femur.{i}"].tail
            err = (knee - K).length
            if err < best_err:
                best, best_err = deg, err
        ik.pole_angle = math.radians(best)
    bpy.context.view_layer.update()


def _module(kind, slot, u, col):
    """Build a module at the origin pointing +Z. Returns [(object, material_key)]."""
    objs = []
    if kind == "active_sonar":
        objs.append((G.cyl(f"{slot}_sonar_base", u * 0.22, u * 0.2, u * 0.06, (0, 0, u * 0.03), col=col), "metal"))
        objs.append((G.hemisphere(f"{slot}_sonar_dome", u * 0.19, (0, 0, u * 0.06), col=col), "rubber"))
        objs.append((G.torus(f"{slot}_sonar_ring", u * 0.2, u * 0.012, (0, 0, u * 0.065), col=col), "light"))
    elif kind == "beacon_rack":
        objs.append((G.box(f"{slot}_rack", (u * 0.42, u * 0.3, u * 0.05), (0, 0, u * 0.025), bevel=0.004, col=col), "dark"))
        for k in range(4):
            x = -u * 0.15 + k * u * 0.1
            objs.append((G.cyl(f"{slot}_beacon{k}", u * 0.035, u * 0.035, u * 0.16, (x, 0, u * 0.13), verts=12, col=col), "metal"))
            objs.append((G.cyl(f"{slot}_beacon_cap{k}", u * 0.038, u * 0.03, u * 0.03, (x, 0, u * 0.22), verts=12, col=col), "accent"))
    elif kind == "magnetometer":
        objs.append((G.box(f"{slot}_mag_base", (u * 0.2, u * 0.2, u * 0.06), (0, 0, u * 0.03), bevel=0.004, col=col), "dark"))
        tip = Vector((-u * 0.9, 0, u * 0.8))
        objs.append((G.segment(f"{slot}_mag_boom", (0, 0, u * 0.05), tip, u * 0.025, u * 0.015, verts=12, col=col), "metal"))
        objs.append((G.sphere(f"{slot}_mag_head", u * 0.06, tip, col=col, seg=16), "accent"))
    elif kind == "passive_acoustic":
        objs.append((G.cyl(f"{slot}_pa_base", u * 0.1, u * 0.1, u * 0.05, (0, 0, u * 0.025), verts=16, col=col), "dark"))
        for k, ang in enumerate((-0.5, 0.0, 0.5)):
            v = G.box(f"{slot}_vane{k}", (u * 0.02, u * 0.16, u * 0.34), (0, 0, u * 0.2), rot=(0, 0, ang), bevel=0.002, col=col)
            objs.append((v, "metal"))
    elif kind == "optical":
        objs.append((G.cyl(f"{slot}_lamp_house", u * 0.09, u * 0.11, u * 0.12, (0, 0, u * 0.06), verts=20, col=col), "dark"))
        objs.append((G.cyl(f"{slot}_lamp_lens", u * 0.09, u * 0.09, u * 0.02, (0, 0, u * 0.125), verts=20, col=col), "eye"))
        objs.append((G.box(f"{slot}_camera", (u * 0.08, u * 0.06, u * 0.06), (u * 0.14, 0, u * 0.03), bevel=0.003, col=col), "metal"))
    elif kind == "cargo_bay":
        objs.append((G.box(f"{slot}_bay", (u * 1.1, u * 0.7, u * 0.28), (0, 0, u * 0.14), bevel=u * 0.05, col=col), "paint"))
        for side in (1, -1):
            objs.append((G.box(f"{slot}_rail{side}", (u * 1.0, u * 0.03, u * 0.05), (0, side * u * 0.36, u * 0.12), col=col), "accent"))
        objs.append((G.box(f"{slot}_hatch", (u * 0.6, u * 0.5, u * 0.02), (0, 0, u * 0.29), bevel=0.003, col=col), "dark"))
    elif kind == "structural_monitor":
        objs.append((G.box(f"{slot}_sm_box", (u * 0.16, u * 0.16, u * 0.06), (0, 0, u * 0.03), bevel=0.003, col=col), "dark"))
        for k in range(3):
            a = k * 2.1
            objs.append((G.segment(f"{slot}_spike{k}", (0, 0, u * 0.05), (math.cos(a) * u * 0.14, math.sin(a) * u * 0.14, u * 0.28), u * 0.012, u * 0.003, verts=8, col=col), "metal"))
    else:
        raise ValueError(f"unknown module {kind}")
    return objs
