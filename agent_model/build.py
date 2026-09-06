"""Assemble one agent: meshes, materials, armature with IK legs and a tracking head.

Every part has a job. Nothing is decoration:
  hull            sealed pressure body; the top rail is the module mount
  head            the sensor mast; it turns. Sonar transducer strip and lamp live here
  hydrophones     passive acoustic: a line array along each flank gives a bearing
  beacon rack     rear dispenser; beacons are dropped behind you
  magnetometer    on a tail boom, away from the actuators' magnetic noise
  structural      contact geophone pucks at the ankles, where the machine touches rock
  comms mast      the thin acoustic link to the surface
  conduits        power to the leg actuators
  running lights  so the machine is readable in the dark from its own light

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


def _smoothstep(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


class Built:
    def __init__(self):
        self.arm = None
        self.feet = []
        self.look = None
        self.parts = []
        self.lamp = None
        self.collection = None
        self.head_center = None


def build_agent(cfg: AgentConfig, name="AGENT", at=(0, 0, 0)):
    ch = validate(cfg)
    skin = cfg.skin
    col = G.new_collection(name)
    out = Built()
    out.collection = col
    mats = {
        "paint": M.painted_metal(skin), "accent": M.accent(skin), "metal": M.bare_metal(),
        "dark": M.bare_metal("dark_metal", (0.10, 0.10, 0.11), 0.55), "carbon": M.bare_metal("carbon", (0.05, 0.05, 0.055), 0.4),
        "rubber": M.rubber(), "light": M.emissive(skin), "eye": M.emissive(skin, "eye", skin.light_strength * 2.5),
        "lens": M.lens(), "glass": M.bare_metal("dark_glass", (0.02, 0.03, 0.04), 0.08),
    }
    L, W, H = ch.hull
    zc = ch.ride_height + H / 2
    parts_by_bone = {}

    def add(obj, mat, bone=None):
        G.set_material(obj, mats[mat])
        parts_by_bone.setdefault(bone, []).append(obj)
        out.parts.append(obj)
        return obj

    # ---- hull: a lofted, tapered body -------------------------------------------------
    stations = []
    N = 9
    for k in range(N):
        u = k / (N - 1)                                   # 0 tail .. 1 nose
        x = -L / 2 + u * L
        wf = 0.55 + 0.45 * math.sin(math.pi * (0.15 + 0.85 * u) ** 0.8) if u < 0.999 else 0.42
        wf = min(1.0, max(0.42, wf))
        hf = 0.5 + 0.5 * math.sin(math.pi * (0.1 + 0.9 * u) ** 0.9)
        hf = min(1.0, max(0.45, hf))
        drop = -H * 0.10 * _smoothstep(0.55, 1.0, u)      # nose dips a little
        prof = [(y, z + zc + drop) for (y, z) in G.hull_profile(W * wf, H * hf)]
        stations.append((x, prof))
    add(G.loft("hull", stations, col=col, crease=0.55, subsurf=2), "paint")
    # canopy seam: dark inset band where the top shell meets the lower body
    seam_pts = [(-L / 2 + u * L, 0, 0) for u in (0.08, 0.3, 0.55, 0.8, 0.95)]
    for side in (1, -1):
        pts = []
        for (x, prof) in stations[1:-1]:
            y = prof[1][0] if side < 0 else prof[6][0]
            z = (prof[1][1] + prof[0][1]) / 2
            pts.append(Vector((x, y * 1.005, z)))
        add(G.tube_along(f"seam.{side}", pts, 0.004, verts=6, col=col), "carbon")
        # running light: a short strip low on the flank, purposeful and dim
        lp = [Vector((p.x, p.y, p.z - H * 0.33)) for p in pts[1:-2]]
        add(G.tube_along(f"strip.{side}", lp, 0.004, verts=6, col=col), "light")
    # deck rail: the module mount
    if ch.spine_rail:
        add(G.box("rail", (L * 0.7, W * 0.22, 0.014), (-0.02, 0, zc + H / 2 + 0.004), bevel=0.004, col=col), "carbon")
        for s in ch.slots:
            if s.facing[2] > 0.5:
                add(G.box(f"pad.{s.name}", (W * 0.26, W * 0.3, 0.01), (s.pos[0], s.pos[1], zc + s.pos[2] + 0.005), bevel=0.003, col=col), "dark")
    # rear: service hatch and a status light
    add(G.box("hatch", (0.03, W * 0.3, H * 0.35), (-L / 2 + 0.02, 0, zc - H * 0.05), bevel=0.005, col=col), "dark")
    add(G.sphere("status_light", 0.008, (-L / 2 + 0.005, 0, zc + H * 0.2), col=col, seg=12), "light")

    # ---- head: sensor mast on a neck ------------------------------------------------------
    nx, ny, nz = ch.head_pos
    neck_root = Vector((nx, ny, zc + nz))
    hr = ch.head_radius
    head_c = neck_root + Vector((ch.head_neck + hr * 0.7, 0, hr * 0.1))
    add(G.segment("neck", neck_root, head_c - Vector((hr * 0.5, 0, 0)), hr * 0.42, hr * 0.36, verts=8, col=col), "dark", "neck")
    add(G.torus("neck_ring", hr * 0.46, hr * 0.06, neck_root + Vector((0.015, 0, 0)), rot=(0, math.pi / 2, 0), col=col), "metal", "neck")
    hs = []
    for k in range(6):
        u = k / 5
        x = head_c.x - hr * 0.8 + u * hr * 1.7
        wf = 1.0 - 0.45 * u ** 2
        hf = 1.0 - 0.35 * u ** 2
        prof = [(y, z + head_c.z) for (y, z) in G.hull_profile(hr * 1.9 * wf, hr * 1.35 * hf, chamfer=0.4, belly=0.65, deck=0.75)]
        hs.append((x, prof))
    add(G.loft("head", hs, col=col, crease=0.5, subsurf=2), "paint", "neck")
    face_x = head_c.x + hr * 0.9
    out.head_center = head_c
    eye_c = Vector((face_x, 0, head_c.z))

    # ---- modules ------------------------------------------------------------------------
    u = W
    for slot in ch.slots:
        mod = cfg.modules.get(slot.name)
        if not mod:
            continue
        if slot.name == "face":
            base = Vector((face_x - hr * 0.05, 0, head_c.z + hr * 0.28)); f = Vector((1, 0, 0)); bone = "neck"; u_ = hr * 2
        elif slot.name == "eye":
            base = Vector((face_x - hr * 0.1, 0, head_c.z - hr * 0.15)); f = Vector((1, 0, 0)); bone = "neck"; u_ = hr * 2
        else:
            base = Vector((slot.pos[0], slot.pos[1], zc + slot.pos[2])); f = Vector(slot.facing).normalized(); bone = None; u_ = u
        rot = f.to_track_quat("Z", "Y").to_euler()
        for o, mat in _module(mod, slot.name, u_, col, hull=(L, W, H, zc)):
            o.matrix_world = Matrix.Translation(base) @ rot.to_matrix().to_4x4() @ o.matrix_world
            add(o, mat, bone)
    # comms mast: acoustic modem to the surface. Short, stiff, at the tail
    mast_base = Vector((-L * 0.38, 0, zc + H / 2))
    add(G.cyl("comms_mast", 0.006, 0.004, hr * 1.4, mast_base + Vector((0, 0, hr * 0.7)), verts=8, col=col), "metal")
    add(G.cyl("comms_head", 0.012, 0.012, 0.02, mast_base + Vector((0, 0, hr * 1.4)), verts=12, col=col), "dark")

    # ---- legs ---------------------------------------------------------------------------
    neutral, leg_geom = [], []
    for i, leg in enumerate(ch.legs):
        s = leg.side
        Hp = Vector((leg.hip[0], leg.hip[1], zc + leg.hip[2]))
        C = Hp + Vector((0, s * leg.coxa, 0))
        kdir = Vector((leg.knee_back, s * leg.splay, leg.knee_rise)).normalized()
        K = C + kdir * leg.femur
        F = Vector((Hp.x + leg.foot_fwd, K.y + s * leg.foot_out, 0.0))
        neutral.append((F.x, F.y, F.z))
        leg_geom.append((Hp, C, K, F))
        r = W * 0.085
        # hip: a hinge housing that yaws (coxa) and a pitch actuator inside it
        add(G.cyl(f"hip.{i}", r * 1.3, r * 1.3, r * 1.6, Hp, rot=(0, math.pi / 2, 0), verts=12, col=col), "dark")
        add(G.cyl(f"coxa.{i}", r * 0.9, r * 0.9, leg.coxa + r, (Hp + C) / 2, rot=(math.pi / 2, 0, 0), verts=12, col=col), "metal", f"coxa.{i}")
        add(G.torus(f"hip_ring.{i}", r * 1.05, r * 0.12, C, rot=(math.pi / 2, 0, 0), col=col), "accent", f"coxa.{i}")
        # femur: tapered strut plus a linear actuator on its outer face
        add(G.strut(f"femur.{i}", C, K, r * 2.0, r * 1.6, r * 1.5, r * 1.2, col=col), "paint", f"femur.{i}")
        fa, fb = C.lerp(K, 0.15), C.lerp(K, 0.85)
        off = Vector((0, s * r * 1.15, 0))
        add(G.segment(f"femur_cyl.{i}", fa + off, fa.lerp(fb, 0.55) + off, r * 0.42, r * 0.42, verts=10, col=col), "dark", f"femur.{i}")
        add(G.segment(f"femur_rod.{i}", fa.lerp(fb, 0.5) + off, fb + off, r * 0.2, r * 0.2, verts=8, col=col), "metal", f"femur.{i}")
        # knee: hinge with a bolt head each side
        add(G.cyl(f"knee.{i}", r * 1.05, r * 1.05, r * 2.6, K, rot=(math.pi / 2, 0, 0), verts=16, col=col), "dark", f"femur.{i}")
        add(G.cyl(f"knee_bolt.{i}", r * 0.5, r * 0.5, r * 0.3, K + Vector((0, s * r * 1.4, 0)), rot=(math.pi / 2, 0, 0), verts=6, col=col), "accent", f"femur.{i}")
        # tibia: slimmer strut, actuator rod down its back, ankle, rubber pad
        add(G.strut(f"tibia.{i}", K, F + Vector((0, 0, 0.03)), r * 1.5, r * 1.3, r * 0.9, r * 0.8, col=col), "carbon", f"tibia.{i}")
        ta, tb = K.lerp(F, 0.12), K.lerp(F, 0.72)
        back = Vector((-r * 0.9, 0, 0))
        add(G.segment(f"tibia_cyl.{i}", ta + back, ta.lerp(tb, 0.5) + back, r * 0.35, r * 0.35, verts=10, col=col), "dark", f"tibia.{i}")
        add(G.segment(f"tibia_rod.{i}", ta.lerp(tb, 0.45) + back, tb + back, r * 0.16, r * 0.16, verts=8, col=col), "metal", f"tibia.{i}")
        add(G.sphere(f"ankle.{i}", r * 0.7, F + Vector((0, 0, 0.035)), col=col, seg=12), "dark", f"tibia.{i}")
        foot = G.sphere(f"foot.{i}", r * 0.95, F + Vector((0, 0, r * 0.55)), col=col, seg=16)
        foot.scale = (1.4, 1.15, 0.6)
        add(foot, "rubber", f"tibia.{i}")
        if "structural_monitor" in cfg.modules.values():
            add(G.torus(f"geophone.{i}", r * 0.85, r * 0.22, F + Vector((0, 0, 0.045)), col=col), "accent", f"tibia.{i}")
        # power conduit from the hull to the hip actuator
        p0 = Vector((Hp.x, s * (W * 0.42), zc - H * 0.1))
        p1 = Hp + Vector((0, s * r * 0.4, r * 1.2))
        mid = (p0 + p1) / 2 + Vector((0, s * 0.01, 0.02))
        add(G.tube_along(f"conduit.{i}", [p0, mid, p1], 0.005, verts=6, col=col), "rubber")

    # ---- armature -----------------------------------------------------------------------
    arm_data = bpy.data.armatures.new("AGENT_RIG")
    arm = bpy.data.objects.new("AGENT_RIG", arm_data)
    col.objects.link(arm)
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

    feet = [_empty(f"FOOT.{i}", F, size=0.05, kind="SPHERE") for i, (Hp, C, K, F) in enumerate(leg_geom)]
    look = _empty("LOOK", head_c + Vector((2.0, 0, 0)), size=0.08, kind="CUBE")
    out.feet, out.look, out.arm = feet, look, arm

    pb = arm.pose.bones
    for i in range(len(leg_geom)):
        c = pb[f"coxa.{i}"].constraints.new("LOCKED_TRACK")
        c.target = feet[i]; c.track_axis = "TRACK_Y"; c.lock_axis = "LOCK_Z"
        ik = pb[f"tibia.{i}"].constraints.new("IK")
        ik.target = feet[i]; ik.pole_target = arm; ik.pole_subtarget = f"pole.{i}"
        ik.chain_count = 2; ik.use_tail = True
    trk = pb["neck"].constraints.new("DAMPED_TRACK")
    trk.target = look; trk.track_axis = "TRACK_Y"
    lim = pb["neck"].constraints.new("LIMIT_ROTATION")
    lim.use_limit_x = lim.use_limit_z = True
    lim.min_x, lim.max_x = -0.7, 0.7
    lim.min_z, lim.max_z = -1.0, 1.0
    lim.owner_space = "LOCAL"
    _settle_pole_angles(arm, leg_geom)

    for bone, objs in parts_by_bone.items():
        for o in objs:
            if bone is None:
                o.parent = arm
            else:
                _parent_to_bone(o, arm, bone)

    if "optical" in cfg.modules.values():
        lamp_data = bpy.data.lights.new("HEAD_LAMP", "SPOT")
        lamp_data.energy = 70; lamp_data.spot_size = math.radians(50); lamp_data.spot_blend = 0.5
        lamp_data.color = tuple(0.6 * v + 0.4 for v in skin.light)
        lamp_data.shadow_soft_size = 0.04
        lamp = bpy.data.objects.new("HEAD_LAMP", lamp_data)
        col.objects.link(lamp)
        lamp.location = eye_c + Vector((hr * 0.15, 0, -hr * 0.15))
        lamp.rotation_euler = Euler((0, math.pi / 2, 0))
        _parent_to_bone(lamp, arm, "neck")
        out.lamp = lamp

    arm["leg_neutral"] = [list(n) for n in neutral]
    arm["chassis"] = ch.name
    arm["hull_center_z"] = zc
    arm["step_height"] = 0.35 * ch.ride_height
    arm.location = Vector(at)
    for e in feet:
        e.location = Vector(e.location) + Vector(at)
    look.location = Vector(look.location) + Vector(at)
    return out


def _settle_pole_angles(arm, leg_geom):
    dg = bpy.context.evaluated_depsgraph_get()
    for i, (Hp, C, K, F) in enumerate(leg_geom):
        ik = arm.pose.bones[f"tibia.{i}"].constraints[-1]
        best, best_err = 0.0, 1e9
        for deg in range(-180, 180, 15):
            ik.pole_angle = math.radians(deg)
            dg.update(); bpy.context.view_layer.update()
            ev = arm.evaluated_get(dg)
            knee = ev.matrix_world @ ev.pose.bones[f"femur.{i}"].tail
            err = (knee - K).length
            if err < best_err:
                best, best_err = deg, err
        ik.pole_angle = math.radians(best)
    bpy.context.view_layer.update()


def _module(kind, slot, u, col, hull):
    """Build a module at the origin pointing +Z. Returns [(object, material_key)]."""
    L, W, H, zc = hull
    objs = []
    if kind == "active_sonar":
        # forward-looking transducer array: a wide flat strip of elements behind a dark window
        objs.append((G.box(f"{slot}_sonar_window", (u * 0.62, u * 0.11, u * 0.03), (0, 0, u * 0.012), bevel=0.003, col=col), "glass"))
        for k in range(7):
            objs.append((G.box(f"{slot}_sonar_el{k}", (u * 0.06, u * 0.07, u * 0.02), (-u * 0.24 + k * u * 0.08, 0, u * 0.02), col=col), "light"))
    elif kind == "optical":
        # lamp reflector with lens, and a camera beside it
        objs.append((G.cyl(f"{slot}_reflector", u * 0.16, u * 0.13, u * 0.06, (0, 0, u * 0.0), verts=24, col=col), "dark"))
        objs.append((G.cyl(f"{slot}_lamp", u * 0.13, u * 0.13, u * 0.015, (0, 0, u * 0.035), verts=24, col=col), "eye"))
        objs.append((G.cyl(f"{slot}_lens", u * 0.14, u * 0.14, u * 0.01, (0, 0, u * 0.045), verts=24, col=col), "lens"))
        objs.append((G.cyl(f"{slot}_camera", u * 0.045, u * 0.045, u * 0.06, (0, u * 0.24, u * 0.0), verts=16, col=col), "dark"))
        objs.append((G.cyl(f"{slot}_camera_lens", u * 0.035, u * 0.035, u * 0.01, (0, u * 0.24, u * 0.035), verts=16, col=col), "glass"))
    elif kind == "passive_acoustic":
        # hydrophone line array: a rail of small domes along the flank
        n = 5
        objs.append((G.box(f"{slot}_rail", (u * 0.9, u * 0.06, u * 0.025), (0, 0, u * 0.012), bevel=0.003, col=col), "carbon"))
        for k in range(n):
            x = -u * 0.36 + k * u * 0.18
            objs.append((G.hemisphere(f"{slot}_hydrophone{k}", u * 0.035, (x, 0, u * 0.025), col=col), "rubber"))
    elif kind == "beacon_rack":
        # dispenser: magazine of beacon tubes angled to drop behind the machine
        objs.append((G.box(f"{slot}_magazine", (u * 0.36, u * 0.26, u * 0.07), (0, 0, u * 0.035), bevel=0.004, col=col), "dark"))
        for k in range(4):
            x = -u * 0.135 + k * u * 0.09
            objs.append((G.cyl(f"{slot}_beacon{k}", u * 0.03, u * 0.03, u * 0.12, (x, 0, u * 0.11), verts=10, col=col), "metal"))
            objs.append((G.cyl(f"{slot}_beacon_cap{k}", u * 0.032, u * 0.024, u * 0.025, (x, 0, u * 0.18), verts=10, col=col), "accent"))
        objs.append((G.box(f"{slot}_chute", (u * 0.12, u * 0.1, u * 0.05), (-u * 0.24, 0, u * 0.02), rot=(0, 0.6, 0), bevel=0.003, col=col), "carbon"))
    elif kind == "magnetometer":
        # sensor pod on a boom, as far from the actuators as the hull allows
        objs.append((G.box(f"{slot}_mag_base", (u * 0.14, u * 0.14, u * 0.04), (0, 0, u * 0.02), bevel=0.003, col=col), "dark"))
        tip = Vector((-u * 1.0, 0, u * 0.55))
        objs.append((G.segment(f"{slot}_boom", (0, 0, u * 0.03), tip, u * 0.018, u * 0.012, verts=8, col=col), "carbon"))
        objs.append((G.cyl(f"{slot}_pod", u * 0.04, u * 0.04, u * 0.1, tip, rot=(0, -0.5, 0), verts=12, col=col), "accent"))
    elif kind == "cargo_bay":
        objs.append((G.box(f"{slot}_bay", (u * 1.0, u * 0.62, u * 0.22), (0, 0, u * 0.11), bevel=u * 0.04, col=col), "paint"))
        objs.append((G.box(f"{slot}_hatch", (u * 0.55, u * 0.45, u * 0.015), (0, 0, u * 0.225), bevel=0.003, col=col), "dark"))
        for side in (1, -1):
            objs.append((G.box(f"{slot}_latch{side}", (u * 0.08, u * 0.04, u * 0.03), (u * 0.2 * side, u * 0.28, u * 0.2), col=col), "accent"))
    elif kind == "structural_monitor":
        # the geophones are at the ankles (see legs); this is the signal conditioner
        objs.append((G.box(f"{slot}_sm_box", (u * 0.14, u * 0.12, u * 0.04), (0, 0, u * 0.02), bevel=0.003, col=col), "dark"))
    else:
        raise ValueError(f"unknown module {kind}")
    return objs
