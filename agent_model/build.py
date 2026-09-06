"""Assemble one agent: meshes, materials, armature with IK legs and a pan-tilt head.

Design references: real quadruped robots (legs dominate, actuators visible at the hips,
broad upper leg housing the knee drive, thin lower leg, rubber ball feet, knees back)
and film droids (one silhouette, one dominant eye, two-tone panels with one accent,
every detail a mechanism, a head on a real joint).

Every part has a job:
  lower chassis     sealed body: batteries, computer, IMU (dead reckoning lives here)
  top shell         removable cover with hatches; the deck rail and handle are hardpoints
  handle            recovery / carry hook: wrecks get salvaged
  hip stacks        abduction motor on the body corner, flexion + knee motors at the femur top
  femur blade       houses the knee belt drive; tibia is a thin strut with a rubber ball foot
  head              pan-tilt yoke carrying the sonar transducer strip and the lamp / camera
  hydrophones       line array along each flank: bearing from a line of elements
  beacon rack       rear dispenser, drops behind the machine
  magnetometer      pod on a tail boom, away from the actuators' magnetic noise
  structural        geophone collars at the ankles, where the machine touches rock
  comms mast        thin acoustic link to the surface
  running lights    readable in the dark from its own light

Rig conventions (motion.py relies on these):
  - AGENT_RIG (armature object) is the body. Origin on the ground under the hull centre.
  - FOOT.<i> empties are the IK targets in world space. pole.<i> bones are children of
    the abduction bone so the knee plane rolls with the hip.
  - coxa.<i> is the hip abduction joint: it rolls about X to keep the leg plane on the
    foot. femur/tibia are a 2-bone IK chain inside that plane.
  - LOOK empty: the head pans (yaw) then tilts (pitch) to track it.
  - arm["leg_neutral"] holds each foot's neutral position relative to the armature.
"""
import math
import bpy
from mathutils import Vector, Matrix, Euler
from . import geometry as G
from . import materials as M
from .params import AgentConfig, CHASSIS, MODULES, validate


def _bone(arm_data, name, head, tail, parent=None, roll=0.0, connect=False):
    b = arm_data.edit_bones.new(name)
    b.head, b.tail = Vector(head), Vector(tail)
    b.roll = roll
    if parent:
        b.parent = arm_data.edit_bones[parent]
        b.use_connect = connect
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


class Built:
    def __init__(self):
        self.arm = None
        self.feet = []
        self.look = None
        self.parts = []
        self.lamp = None
        self.collection = None
        self.head_center = None


def _octagon(w, h, zc, chamfer=0.3, deck=0.78, belly=0.7):
    return [(-w / 2 * deck, zc + h / 2), (-w / 2, zc + h / 2 * (1 - 2 * chamfer)), (-w / 2, zc - h / 2 * (1 - 2 * chamfer)),
            (-w / 2 * belly, zc - h / 2), (w / 2 * belly, zc - h / 2), (w / 2, zc - h / 2 * (1 - 2 * chamfer)),
            (w / 2, zc + h / 2 * (1 - 2 * chamfer)), (w / 2 * deck, zc + h / 2)]


def _cap(w, z_seam, z_top, chamfer):
    return [(-w / 2, z_seam), (-w / 2, z_top - chamfer), (-w / 2 + chamfer * 1.2, z_top),
            (w / 2 - chamfer * 1.2, z_top), (w / 2, z_top - chamfer), (w / 2, z_seam)]


def build_agent(cfg: AgentConfig, name="AGENT", at=(0, 0, 0)):
    ch = validate(cfg)
    skin = cfg.skin
    col = G.new_collection(name)
    out = Built()
    out.collection = col
    mats = {
        "shell": M.painted_metal(skin, "shell_paint"),
        "chassis": M.painted_metal(skin.__class__(name="chassis", base=skin.chassis, accent=skin.accent, bare=skin.bare,
                                                   light=skin.light, wear=skin.wear * 0.6, grime=skin.grime), "chassis_paint"),
        "accent": M.accent(skin), "metal": M.bare_metal(),
        "dark": M.bare_metal("dark_metal", (0.09, 0.09, 0.10), 0.5), "carbon": M.bare_metal("carbon", (0.04, 0.04, 0.045), 0.35),
        "rubber": M.rubber(), "light": M.emissive(skin), "eye": M.emissive(skin, "eye", skin.light_strength * 2.5),
        "lens": M.lens(), "glass": M.bare_metal("dark_glass", (0.02, 0.03, 0.04), 0.08),
        "estop": M.bare_metal("estop_red", (0.6, 0.04, 0.03), 0.45),
    }
    L, W, H = ch.hull
    zc = ch.ride_height + H / 2
    parts_by_bone = {}

    def add(obj, mat, bone=None):
        G.set_material(obj, mats[mat])
        parts_by_bone.setdefault(bone, []).append(obj)
        out.parts.append(obj)
        return obj

    # ---- chassis: faceted lower body, pale top shell, seam between -------------------------
    def width_at(u):                      # u: 0 tail .. 1 nose
        return W * (0.9 + 0.1 * math.sin(math.pi * u)) * (1.0 - 0.18 * max(0.0, u - 0.75) / 0.25)
    xs = [-L / 2, -L * 0.3, 0.0, L * 0.3, L * 0.42, L / 2]
    lower = [(x, _octagon(width_at((x + L / 2) / L), H, zc)) for x in xs]
    add(G.loft("chassis", lower, col=col, subsurf=0), "chassis")
    bev = bpy.data.objects["chassis"].modifiers.new("bevel", "BEVEL"); bev.width = 0.006; bev.segments = 2; bev.limit_method = "ANGLE"
    z_seam = zc + H * 0.05
    z_top = zc + H / 2 + 0.012
    shell = [(x, _cap(width_at((x + L / 2) / L) + 0.014, z_seam, z_top + (0.012 if abs(x) < L * 0.35 else 0.0), 0.02)) for x in xs]
    shell[0] = (xs[0] + 0.01, shell[0][1]); shell[-1] = (xs[-1] - 0.02, shell[-1][1])
    add(G.loft("shell", shell, col=col, subsurf=0), "shell")
    bev = bpy.data.objects["shell"].modifiers.new("bevel", "BEVEL"); bev.width = 0.008; bev.segments = 3; bev.limit_method = "ANGLE"
    # hatches on the shell: battery (mid) and computer (rear). Proud by 1.5 mm, so they read as panels
    add(G.box("hatch_battery", (L * 0.26, W * 0.5, 0.004), (0.02, 0, z_top + 0.0125), bevel=0.002, col=col), "shell")
    add(G.box("hatch_compute", (L * 0.14, W * 0.4, 0.004), (-L * 0.28, 0, z_top + 0.0005), bevel=0.002, col=col), "shell")
    for side in (1, -1):
        add(G.box(f"latch.{side}", (0.012, 0.006, 0.004), (0.02 + L * 0.13 * side, side * W * 0.27, z_top + 0.0145), col=col), "dark")
    # deck rail and hardpoint pads
    add(G.box("rail", (L * 0.62, 0.012, 0.014), (-0.04, 0, z_top + 0.012 + 0.006), bevel=0.003, col=col), "carbon")
    # recovery handle: a bar on two posts
    hx = 0.02
    for dx in (-0.05, 0.05):
        add(G.cyl(f"handle_post{dx:+.2f}", 0.005, 0.005, 0.03, (hx + dx, 0, z_top + 0.03), verts=8, col=col), "metal")
    add(G.cyl("handle_bar", 0.007, 0.007, 0.13, (hx, 0, z_top + 0.045), rot=(0, math.pi / 2, 0), verts=10, col=col), "rubber")
    # running lights: a slit each side just under the seam. Status light at the tail
    for side in (1, -1):
        add(G.box(f"strip.{side}", (L * 0.32, 0.004, 0.006), (0.04, side * (width_at(0.55) / 2 + 0.001), z_seam - 0.012), col=col), "light")
    add(G.box("hatch_service", (0.006, W * 0.4, H * 0.5), (-L / 2 - 0.002, 0, zc), bevel=0.003, col=col), "dark")
    add(G.sphere("status_light", 0.006, (-L / 2 - 0.004, W * 0.15, zc + H * 0.3), col=col, seg=10), "light")
    # front face: a recessed dark sensor bay the yoke sits on; vents on the flanks near the hips
    add(G.box("front_bay", (0.02, W * 0.6, H * 0.55), (L / 2 - 0.005, 0, zc - H * 0.05), bevel=0.004, col=col), "dark")

    # ---- legs -----------------------------------------------------------------------------
    # Joint chain as on a real quadruped: abduction drum (axis X) on the chassis corner;
    # the flexion/knee motor stack (axis Y) bolts to its outboard face; the femur blade
    # bolts to the stack's outboard face on a round knuckle; the tibia sits BESIDE the
    # femur on a through-axle at the knee. Nothing passes through anything.
    neutral, leg_geom = [], []
    rh = H * 0.34                                       # hip motor radius
    bw = rh * 0.9                                       # femur blade thickness (Y)
    tw = rh * 0.5                                       # tibia thickness (Y)
    abd_len, stack_len, gap = 0.05, 0.06, 0.003
    for i, leg in enumerate(ch.legs):
        s = leg.side
        wx = width_at((leg.hip[0] + L / 2) / L) / 2
        Hp = Vector((leg.hip[0], s * wx, zc + leg.hip[2]))                  # abduction axis meets the chassis face
        y_face = Hp.y + s * abd_len                                          # abduction drum outboard face
        y_stack = y_face + s * stack_len / 2                                 # stack centre
        y_f = y_face + s * (stack_len + gap + bw / 2)                        # femur blade plane
        y_t = y_f + s * (bw / 2 + gap + tw / 2)                              # tibia plane
        P = Vector((Hp.x, y_f, Hp.z))                                        # femur pivot (flexion axis, in the blade plane)
        kdir = Vector((leg.knee_back, 0, leg.knee_rise)).normalized()
        Kf = P + kdir * leg.femur                                            # knee in the femur plane
        Kt = Vector((Kf.x, y_t, Kf.z))                                       # knee in the tibia plane
        F = Vector((leg.hip[0] + leg.foot_fwd, y_t, 0.0))
        neutral.append((F.x, F.y, F.z)); leg_geom.append((Hp, P, Kf, Kt, F))
        # abduction drum on the chassis corner, output flange on its outboard face
        add(G.cyl(f"abd_motor.{i}", rh, rh, abd_len, Hp + Vector((0, s * abd_len / 2, 0)), rot=(math.pi / 2, 0, 0), verts=28, col=col), "dark")
        add(G.cyl(f"abd_flange.{i}", rh * 0.85, rh * 0.85, 0.006, Vector((Hp.x, y_face + s * 0.003, Hp.z)), rot=(math.pi / 2, 0, 0), verts=28, col=col), "metal", f"coxa.{i}")
        # flexion + knee motor stack, axis Y, bolted to the flange
        add(G.cyl(f"hip_stack.{i}", rh * 0.95, rh * 0.95, stack_len - 0.006, Vector((Hp.x, y_stack, Hp.z)), rot=(math.pi / 2, 0, 0), verts=28, col=col), "dark", f"coxa.{i}")
        add(G.torus(f"stack_seam.{i}", rh * 0.95, 0.002, Vector((Hp.x, y_stack, Hp.z)), rot=(math.pi / 2, 0, 0), col=col), "carbon", f"coxa.{i}")
        add(G.cyl(f"stack_cap.{i}", rh * 0.55, rh * 0.55, 0.006, Vector((Hp.x, y_face + s * (stack_len - 0.003), Hp.z)), rot=(math.pi / 2, 0, 0), verts=28, col=col), "accent", f"coxa.{i}")
        # femur: round knuckle on the stack face, blade down to the knee knuckle, belt cover outboard
        add(G.cyl(f"femur_knuckle.{i}", rh * 0.78, rh * 0.78, bw, P, rot=(math.pi / 2, 0, 0), verts=28, col=col), "shell", f"femur.{i}")
        add(G.strut(f"femur.{i}", P, Kf, bw, rh * 1.5, bw, rh * 1.0, col=col, bevel=0.004), "shell", f"femur.{i}")
        add(G.cyl(f"knee_knuckle.{i}", rh * 0.5, rh * 0.5, bw, Kf, rot=(math.pi / 2, 0, 0), verts=24, col=col), "shell", f"femur.{i}")
        cov_y = s * (bw / 2 + 0.003)
        add(G.strut(f"belt_cover.{i}", P + Vector((0, cov_y, 0)), Kf + Vector((0, cov_y, 0)), 0.006, rh * 0.7, 0.006, rh * 0.45, col=col, bevel=0.002), "carbon", f"femur.{i}")
        # knee axle through femur knuckle and tibia knuckle, cap outboard
        ax0 = Vector((Kf.x, y_f - s * (bw / 2 + 0.004), Kf.z)); ax1 = Vector((Kf.x, y_t + s * (tw / 2 + 0.006), Kf.z))
        add(G.segment(f"knee_axle.{i}", ax0, ax1, rh * 0.16, rh * 0.16, verts=12, col=col), "metal", f"femur.{i}")
        add(G.cyl(f"knee_cap.{i}", rh * 0.24, rh * 0.24, 0.005, ax1, rot=(math.pi / 2, 0, 0), verts=12, col=col), "accent", f"tibia.{i}")
        # tibia beside the femur: knuckle, tapered strut, ankle, rubber ball foot
        add(G.cyl(f"tibia_knuckle.{i}", rh * 0.42, rh * 0.42, tw, Kt, rot=(math.pi / 2, 0, 0), verts=24, col=col), "carbon", f"tibia.{i}")
        add(G.strut(f"tibia.{i}", Kt, F + Vector((0, 0, 0.02)), tw, rh * 0.7, tw * 0.7, rh * 0.32, col=col, bevel=0.002), "carbon", f"tibia.{i}")
        add(G.sphere(f"foot.{i}", 0.022, F + Vector((0, 0, 0.018)), col=col, seg=16), "rubber", f"tibia.{i}")
        if "structural_monitor" in cfg.modules.values():
            add(G.cyl(f"geophone.{i}", rh * 0.4, rh * 0.4, 0.012, F + Vector((0, 0, 0.055)), verts=12, col=col), "accent", f"tibia.{i}")
        # power and signal cable: chassis -> abduction drum -> stack, with slack for travel
        c0 = Vector((Hp.x - rh * 0.6, Hp.y + s * 0.002, Hp.z - rh * 1.0)); c1 = Vector((Hp.x - rh * 0.9, y_stack, Hp.z - rh * 0.95))
        add(G.tube_along(f"cable.{i}", [c0, (c0 + c1) / 2 + Vector((-0.01, 0, -0.015)), c1], 0.0035, verts=6, col=col), "rubber", f"coxa.{i}")

    # ---- head: pan-tilt unit on a chassis prow bracket -------------------------------------
    # Mounted on structure, not on the removable shell. The payload block is centred on the
    # tilt axis so the tilt motor carries no static moment; the unit can look down at its
    # own footing.
    hr = ch.head_radius
    prow_z = zc + H / 2 - 0.012
    add(G.box("prow_bracket", (0.09, W * 0.55, 0.022), (L / 2 + 0.02, 0, prow_z), bevel=0.004, col=col), "chassis")
    for s in (1, -1):
        add(G.box(f"prow_gusset.{s}", (0.05, 0.006, 0.05), (L / 2 + 0.005, s * W * 0.2, prow_z - 0.035), rot=(0, -0.5, 0), col=col), "chassis")
    B = Vector((L / 2 + 0.035, 0, prow_z + 0.011))                          # pan axis base
    add(G.cyl("pan_motor", hr * 0.62, hr * 0.62, 0.028, B + Vector((0, 0, 0.014)), verts=28, col=col), "dark")
    add(G.torus("pan_ring", hr * 0.6, 0.003, B + Vector((0, 0, 0.0285)), col=col), "carbon")
    add(G.cyl("pan_plate", hr * 0.58, hr * 0.5, 0.012, B + Vector((0, 0, 0.034)), verts=28, col=col), "dark", "pan")
    T = B + Vector((0.01, 0, 0.04 + hr * 0.7))                              # tilt axis centre
    yw = hr * 0.95
    for s in (1, -1):
        a0 = B + Vector((-0.01, s * yw * 0.55, 0.04)); a1 = T + Vector((0, s * yw, 0))
        add(G.strut(f"yoke.{s}", a0, a1, 0.018, 0.04, 0.018, 0.03, col=col, bevel=0.003), "dark", "pan")
        add(G.box(f"yoke_foot.{s}", (0.05, 0.02, 0.01), a0 + Vector((0, 0, 0.005)), bevel=0.002, col=col), "dark", "pan")
    # tilt motor lives on the right arm; the left arm carries the bearing
    add(G.cyl("tilt_motor", hr * 0.38, hr * 0.38, 0.026, T + Vector((0, -(yw + 0.02), 0)), rot=(math.pi / 2, 0, 0), verts=24, col=col), "dark", "pan")
    add(G.cyl("tilt_motor_cap", hr * 0.25, hr * 0.25, 0.006, T + Vector((0, -(yw + 0.036), 0)), rot=(math.pi / 2, 0, 0), verts=24, col=col), "accent", "pan")
    add(G.cyl("tilt_bearing", hr * 0.3, hr * 0.3, 0.012, T + Vector((0, yw + 0.012, 0)), rot=(math.pi / 2, 0, 0), verts=24, col=col), "accent", "pan")
    Hc = T
    head = G.box("head", (hr * 1.5, yw * 2 - 0.012, hr * 0.95), Hc, bevel=hr * 0.16, col=col)
    add(head, "shell", "tilt")
    face_x = Hc.x + hr * 0.75
    add(G.box("face_plate", (0.006, yw * 2 - 0.03, hr * 0.8), (face_x, 0, Hc.z), bevel=0.003, col=col), "dark", "tilt")
    add(G.box("head_hood", (hr * 0.45, yw * 2 + 0.004, 0.005), (face_x - hr * 0.1, 0, Hc.z + hr * 0.5), bevel=0.002, col=col), "dark", "tilt")
    add(G.box("head_vent", (hr * 0.5, yw * 2 - 0.02, 0.004), Hc + Vector((-hr * 0.3, 0, hr * 0.48)), col=col), "dark", "tilt")
    # cable loop from the chassis into the head: slack for the pan/tilt travel
    add(G.tube_along("head_cable", [Vector((L / 2 - 0.02, W * 0.18, z_top - 0.01)), B + Vector((-0.02, yw * 0.9, 0.02)),
                                     T + Vector((-hr * 0.5, yw * 0.9, -hr * 0.2))], 0.004, verts=6, col=col), "rubber")
    eye_c = Vector((face_x, 0, Hc.z))
    out.head_center = Hc
    # rear: E-stop, charge port, flank cooling grilles
    add(G.cyl("estop_collar", 0.016, 0.016, 0.008, (-L * 0.35, W * 0.3, z_top + 0.004), verts=20, col=col), "accent")
    add(G.cyl("estop", 0.012, 0.011, 0.012, (-L * 0.35, W * 0.3, z_top + 0.014), verts=20, col=col), "estop")
    add(G.box("charge_port", (0.004, 0.03, 0.02), (-L / 2 - 0.006, -W * 0.15, zc - H * 0.15), bevel=0.002, col=col), "accent")
    for side in (1, -1):
        for k in range(5):
            add(G.box(f"vent.{side}.{k}", (0.004, 0.004, H * 0.38), (-0.024 + k * 0.012, side * (width_at(0.5) / 2 + 0.001), zc - H * 0.08), col=col), "carbon")

    # ---- modules ------------------------------------------------------------------------
    u = W
    for slot in ch.slots:
        mod = cfg.modules.get(slot.name)
        if not mod:
            continue
        if slot.name == "face":
            base = Vector((face_x, 0, Hc.z + hr * 0.22)); f = Vector((1, 0, 0)); bone = "tilt"; u_ = hr * 2.4
        elif slot.name == "eye":
            base = Vector((face_x, 0, Hc.z - hr * 0.16)); f = Vector((1, 0, 0)); bone = "tilt"; u_ = hr * 2.0
        else:
            base = Vector((slot.pos[0], slot.pos[1], zc + slot.pos[2])); f = Vector(slot.facing).normalized(); bone = None; u_ = u
        rot = f.to_track_quat("Z", "Y").to_euler()
        for o, mat in _module(mod, slot.name, u_, col):
            o.matrix_world = Matrix.Translation(base) @ rot.to_matrix().to_4x4() @ o.matrix_world
            add(o, mat, bone)
    mast = Vector((-L * 0.42, -W * 0.25, z_top + 0.012))
    add(G.cyl("comms_mast", 0.006, 0.005, hr * 1.0, mast + Vector((0, 0, hr * 0.5)), verts=8, col=col), "metal")
    add(G.cyl("comms_head", 0.011, 0.011, 0.02, mast + Vector((0, 0, hr * 1.0)), verts=12, col=col), "dark")

    # ---- armature -----------------------------------------------------------------------
    arm_data = bpy.data.armatures.new("AGENT_RIG")
    arm = bpy.data.objects.new("AGENT_RIG", arm_data)
    col.objects.link(arm)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    _bone(arm_data, "pan", B + Vector((0, 0, 0.028)), B + Vector((0.05, 0, 0.028)))
    _bone(arm_data, "tilt", T, T + Vector((0.06, 0, 0)), parent="pan")
    for i, (Hp, P, Kf, Kt, F) in enumerate(leg_geom):
        _bone(arm_data, f"coxa.{i}", Hp, Hp + Vector((0, 0, -0.04)))         # abduction: rolls about X
        _bone(arm_data, f"femur.{i}", P, Kf, parent=f"coxa.{i}")
        _bone(arm_data, f"tibia.{i}", Kt, F, parent=f"femur.{i}")           # beside the femur, on the axle
        pole = Kf + (Kf - (P + F) / 2).normalized() * 0.3
        _bone(arm_data, f"pole.{i}", pole, pole + Vector((0, 0, 0.03)), parent=f"coxa.{i}")
    bpy.ops.object.mode_set(mode="OBJECT")
    arm.data.display_type = "STICK"

    feet = [_empty(f"FOOT.{i}", F, size=0.05, kind="SPHERE") for i, (Hp, P, Kf, Kt, F) in enumerate(leg_geom)]
    look = _empty("LOOK", Hc + Vector((2.0, 0, 0)), size=0.08, kind="CUBE")
    out.feet, out.look, out.arm = feet, look, arm

    pb = arm.pose.bones
    for i in range(len(leg_geom)):
        c = pb[f"coxa.{i}"].constraints.new("LOCKED_TRACK")
        c.target = feet[i]; c.track_axis = "TRACK_Y"; c.lock_axis = "LOCK_X"
        ik = pb[f"tibia.{i}"].constraints.new("IK")
        ik.target = feet[i]; ik.pole_target = arm; ik.pole_subtarget = f"pole.{i}"
        ik.chain_count = 2; ik.use_tail = True
    pan = pb["pan"].constraints.new("LOCKED_TRACK"); pan.target = look; pan.track_axis = "TRACK_Y"; pan.lock_axis = "LOCK_Z"
    tilt = pb["tilt"].constraints.new("DAMPED_TRACK"); tilt.target = look; tilt.track_axis = "TRACK_Y"
    lim = pb["tilt"].constraints.new("LIMIT_ROTATION")
    lim.use_limit_x = True; lim.min_x, lim.max_x = -0.6, 0.6
    lim.use_limit_z = True; lim.min_z, lim.max_z = -0.2, 0.2
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
        lamp.location = eye_c + Vector((0.02, 0, -hr * 0.15))
        lamp.rotation_euler = Euler((0, math.pi / 2, 0))
        _parent_to_bone(lamp, arm, "tilt")
        out.lamp = lamp

    arm["leg_neutral"] = [list(n) for n in neutral]
    arm["chassis"] = ch.name
    arm["hull_center_z"] = zc
    arm["step_height"] = 0.3 * ch.ride_height
    arm.location = Vector(at)
    for e in feet:
        e.location = Vector(e.location) + Vector(at)
    look.location = Vector(look.location) + Vector(at)
    return out


def _settle_pole_angles(arm, leg_geom):
    dg = bpy.context.evaluated_depsgraph_get()
    for i, (Hp, P, K, Kt, F) in enumerate(leg_geom):
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


def _module(kind, slot, u, col):
    """Build a module at the origin pointing +Z. Returns [(object, material_key)]."""
    objs = []
    if kind == "active_sonar":
        objs.append((G.box(f"{slot}_sonar_window", (u * 0.6, u * 0.12, u * 0.03), (0, 0, u * 0.012), bevel=0.003, col=col), "glass"))
        for k in range(7):
            objs.append((G.box(f"{slot}_sonar_el{k}", (u * 0.055, u * 0.075, u * 0.02), (-u * 0.235 + k * u * 0.078, 0, u * 0.022), col=col), "light"))
    elif kind == "optical":
        objs.append((G.cyl(f"{slot}_reflector", u * 0.14, u * 0.11, u * 0.05, (0, 0, u * 0.0), verts=24, col=col), "dark"))
        objs.append((G.cyl(f"{slot}_lamp", u * 0.11, u * 0.11, u * 0.012, (0, 0, u * 0.03), verts=24, col=col), "eye"))
        objs.append((G.cyl(f"{slot}_lens", u * 0.12, u * 0.12, u * 0.008, (0, 0, u * 0.04), verts=24, col=col), "lens"))
        objs.append((G.cyl(f"{slot}_camera", u * 0.04, u * 0.04, u * 0.05, (0, u * 0.22, u * 0.0), verts=16, col=col), "dark"))
        objs.append((G.cyl(f"{slot}_camera_lens", u * 0.03, u * 0.03, u * 0.008, (0, u * 0.22, u * 0.03), verts=16, col=col), "glass"))
    elif kind == "passive_acoustic":
        objs.append((G.box(f"{slot}_rail", (u * 0.8, u * 0.07, u * 0.02), (0, 0, u * 0.01), bevel=0.003, col=col), "carbon"))
        for k in range(5):
            objs.append((G.hemisphere(f"{slot}_hydrophone{k}", u * 0.03, (-u * 0.32 + k * u * 0.16, 0, u * 0.02), col=col), "rubber"))
    elif kind == "beacon_rack":
        objs.append((G.box(f"{slot}_magazine", (u * 0.34, u * 0.26, u * 0.06), (0, 0, u * 0.03), bevel=0.004, col=col), "dark"))
        for k in range(4):
            x = -u * 0.12 + k * u * 0.08
            objs.append((G.cyl(f"{slot}_beacon{k}", u * 0.028, u * 0.028, u * 0.11, (x, 0, u * 0.1), verts=10, col=col), "metal"))
            objs.append((G.cyl(f"{slot}_beacon_cap{k}", u * 0.03, u * 0.022, u * 0.022, (x, 0, u * 0.165), verts=10, col=col), "accent"))
        objs.append((G.box(f"{slot}_chute", (u * 0.1, u * 0.1, u * 0.05), (-u * 0.22, 0, u * 0.02), rot=(0, 0.6, 0), bevel=0.003, col=col), "carbon"))
    elif kind == "magnetometer":
        # folding boom: motorised root hinge on a wide base, box-section arm, a brace
        # strut triangulating the first segment, elbow joint, sensor pod at the tip.
        # The pod has to sit clear of the hip actuators' magnetic noise, hence the reach.
        objs.append((G.box(f"{slot}_mag_base", (u * 0.22, u * 0.2, u * 0.04), (0, 0, u * 0.02), bevel=0.004, col=col), "dark"))
        for sd in (1, -1):
            objs.append((G.box(f"{slot}_mag_ear{sd}", (u * 0.08, u * 0.02, u * 0.09), (u * 0.02, sd * u * 0.075, u * 0.08), bevel=0.003, col=col), "dark"))
        objs.append((G.cyl(f"{slot}_mag_hinge", u * 0.045, u * 0.045, u * 0.19, (u * 0.02, 0, u * 0.09), rot=(math.pi / 2, 0, 0), verts=16, col=col), "metal"))
        objs.append((G.cyl(f"{slot}_mag_motor", u * 0.05, u * 0.05, u * 0.05, (u * 0.02, u * 0.12, u * 0.09), rot=(math.pi / 2, 0, 0), verts=16, col=col), "dark"))
        objs.append((G.cyl(f"{slot}_mag_motor_cap", u * 0.035, u * 0.035, u * 0.008, (u * 0.02, u * 0.148, u * 0.09), rot=(math.pi / 2, 0, 0), verts=16, col=col), "accent"))
        root = Vector((u * 0.02, 0, u * 0.09)); elbow = Vector((-u * 0.55, 0, u * 0.42)); tip = Vector((-u * 0.95, 0, u * 0.55))
        objs.append((G.strut(f"{slot}_boom1", root, elbow, u * 0.07, u * 0.09, u * 0.05, u * 0.06, col=col, bevel=0.003), "carbon"))
        objs.append((G.strut(f"{slot}_brace", Vector((-u * 0.18, 0, u * 0.02)), root.lerp(elbow, 0.55), u * 0.03, u * 0.03, u * 0.025, u * 0.025, col=col, bevel=0.002), "metal"))
        objs.append((G.cyl(f"{slot}_mag_elbow", u * 0.04, u * 0.04, u * 0.1, elbow, rot=(math.pi / 2, 0, 0), verts=16, col=col), "dark"))
        objs.append((G.cyl(f"{slot}_mag_elbow_cap", u * 0.028, u * 0.028, u * 0.008, elbow + Vector((0, u * 0.054, 0)), rot=(math.pi / 2, 0, 0), verts=16, col=col), "accent"))
        objs.append((G.strut(f"{slot}_boom2", elbow, tip, u * 0.04, u * 0.05, u * 0.03, u * 0.035, col=col, bevel=0.002), "carbon"))
        objs.append((G.cyl(f"{slot}_pod", u * 0.04, u * 0.04, u * 0.11, tip + Vector((-u * 0.03, 0, u * 0.01)), rot=(0, -0.5, 0), verts=16, col=col), "accent"))
        objs.append((G.tube_along(f"{slot}_mag_cable", [root + Vector((0, u * 0.06, u * 0.03)), root.lerp(elbow, 0.5) + Vector((0, u * 0.05, -u * 0.02)), elbow + Vector((0, u * 0.05, 0))], 0.003, verts=6, col=col), "rubber"))
    elif kind == "cargo_bay":
        objs.append((G.box(f"{slot}_bay", (u * 0.95, u * 0.6, u * 0.2), (0, 0, u * 0.1), bevel=u * 0.035, col=col), "chassis"))
        objs.append((G.box(f"{slot}_hatch", (u * 0.5, u * 0.42, u * 0.012), (0, 0, u * 0.205), bevel=0.003, col=col), "dark"))
        for side in (1, -1):
            objs.append((G.box(f"{slot}_latch{side}", (u * 0.07, u * 0.035, u * 0.03), (u * 0.18 * side, u * 0.27, u * 0.18), col=col), "accent"))
    elif kind == "structural_monitor":
        objs.append((G.box(f"{slot}_sm_box", (u * 0.12, u * 0.1, u * 0.035), (0, 0, u * 0.017), bevel=0.003, col=col), "dark"))
    else:
        raise ValueError(f"unknown module {kind}")
    return objs
