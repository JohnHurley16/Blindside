"""Say how the agent moves; the gait generator and IK do the rest.

    m = Mover(built)            # from build_agent()
    m.stand(0.5)
    m.walk(3.0, speed=0.5, turn=20, gait="trot")     # seconds, m/s, deg/s
    m.look_at((1.5, 1.0, 0.3), over=0.4)
    m.crouch(0.06, over=0.5)
    m.finish()                  # sets the scene frame range

Every call appends to the timeline. Feet are keyed as world-space empties, the body
as the armature's transform. Blender's IK constraints solve the legs at eval time.
"""
import math
import bpy
from mathutils import Vector, Matrix, Euler

GAITS = {
    # phases per leg in build order: front-left, front-right, (mid-left, mid-right,) rear-left, rear-right
    "trot":   {"duty": 0.55, "phase4": [0.0, 0.5, 0.5, 0.0], "phase6": [0.0, 0.5, 0.5, 0.0, 0.0, 0.5]},
    "walk":   {"duty": 0.78, "phase4": [0.0, 0.5, 0.75, 0.25], "phase6": [0.0, 0.5, 0.33, 0.83, 0.67, 0.17]},
    "creep":  {"duty": 0.88, "phase4": [0.0, 0.5, 0.75, 0.25], "phase6": [0.0, 0.5, 0.33, 0.83, 0.67, 0.17]},
    "bound":  {"duty": 0.5, "phase4": [0.0, 0.0, 0.5, 0.5], "phase6": [0.0, 0.0, 0.5, 0.5, 0.0, 0.0]},
}


def _fcurves(ob):
    """F-curves of an object's action, across the legacy and the layered action API."""
    ad = ob.animation_data
    if not ad or not ad.action:
        return []
    act = ad.action
    if hasattr(act, "fcurves"):
        return list(act.fcurves)
    out = []
    for layer in act.layers:
        for strip in layer.strips:
            for cb in strip.channelbags:
                out.extend(cb.fcurves)
    return out


def _smooth(s):
    return s * s * (3 - 2 * s)


class Mover:
    def __init__(self, built, fps=24, start_frame=1):
        self.arm = built.arm
        self.feet = built.feet
        self.look = built.look
        self.fps = fps
        self.frame = start_frame
        self.neutral = [Vector(v) for v in self.arm["leg_neutral"]]
        self.step_height = float(self.arm["step_height"])
        self.pos = Vector(self.arm.location)
        self.yaw = float(self.arm.rotation_euler.z)
        self.z_rest = self.pos.z
        self.crouch_dz = 0.0
        self.foot_pos = [Vector(e.location) for e in self.feet]
        self.look_pos = Vector(self.look.location)
        self.look_rel = None      # if set, look target rides with the body (body frame)
        self.path = []            # body positions at every keyed frame, for scene keep-out
        self._key_all()

    # ---- helpers ------------------------------------------------------------------------
    def _R(self, yaw=None):
        return Matrix.Rotation(self.yaw if yaw is None else yaw, 3, "Z")

    def _key_all(self, bob=0.0, pitch=0.0, roll=0.0):
        f = self.frame
        self.path.append((self.pos.x, self.pos.y))
        self.arm.location = (self.pos.x, self.pos.y, self.z_rest - self.crouch_dz + bob)
        self.arm.rotation_euler = Euler((roll, pitch, self.yaw))
        self.arm.keyframe_insert("location", frame=f)
        self.arm.keyframe_insert("rotation_euler", frame=f)
        for e, p in zip(self.feet, self.foot_pos):
            e.location = p
            e.keyframe_insert("location", frame=f)
        if self.look_rel is not None:
            self.look_pos = self.pos + self._R() @ self.look_rel
        self.look.location = self.look_pos
        self.look.keyframe_insert("location", frame=f)

    def _frames(self, seconds):
        return max(1, int(round(seconds * self.fps)))

    # ---- verbs ------------------------------------------------------------------------------
    def stand(self, seconds=1.0, sway=0.0):
        for k in range(self._frames(seconds)):
            self.frame += 1
            t = k / self.fps
            self._key_all(bob=sway * math.sin(t * 2.0))

    def look_at(self, point, over=0.4, ride=False):
        """Turn the head to a world point (or a body-frame point if ride=True)."""
        start = Vector(self.look_pos)
        target = Vector(point)
        n = self._frames(over)
        for k in range(1, n + 1):
            self.frame += 1
            s = _smooth(k / n)
            if ride:
                self.look_rel = start_rel = None
                self.look_pos = start.lerp(self.pos + self._R() @ target, s)
            else:
                self.look_rel = None
                self.look_pos = start.lerp(target, s)
            self._key_all()
        if ride:
            self.look_rel = Vector(point)

    def look_ahead(self, distance=2.0, height=0.0):
        self.look_rel = Vector((distance, 0, float(self.arm["hull_center_z"]) + height))

    def crouch(self, dz, over=0.5):
        start = self.crouch_dz
        n = self._frames(over)
        for k in range(1, n + 1):
            self.frame += 1
            self.crouch_dz = start + (dz - start) * _smooth(k / n)
            self._key_all()

    def walk(self, seconds, speed=0.5, turn=0.0, gait="trot", stride=None, bob=None):
        """Walk for `seconds` at `speed` m/s while turning `turn` deg/s.
        Feet plant and stay planted; swings aim at where the body will be at touchdown."""
        g = GAITS[gait]
        n_legs = len(self.feet)
        phases = g["phase4"] if n_legs == 4 else g["phase6"]
        duty = g["duty"]
        speed = max(speed, 0.02)
        stride = stride if stride is not None else min(0.32, 0.12 + 0.36 * speed)
        T = stride / speed                         # cycle period
        w = math.radians(turn)
        bob = bob if bob is not None else 0.01 + 0.02 * speed
        n = self._frames(seconds)
        p0, y0 = Vector(self.pos), self.yaw

        def pose_at(t):
            yaw = y0 + w * t
            if abs(w) < 1e-6:
                return p0 + Vector((math.cos(y0), math.sin(y0), 0)) * speed * t, yaw
            r = speed / w
            return p0 + Vector((r * (math.sin(yaw) - math.sin(y0)), -r * (math.cos(yaw) - math.cos(y0)), 0)), yaw

        swing = [None] * n_legs                     # (lift_pos, target_pos)
        stance_travel = duty * T * speed
        for k in range(1, n + 1):
            t = k / self.fps
            self.pos, self.yaw = pose_at(t)
            for i in range(n_legs):
                c = (t / T + phases[i]) % 1.0
                if c < duty:
                    swing[i] = None                 # planted: leave the foot alone
                    continue
                s = (c - duty) / (1 - duty)
                if swing[i] is None:
                    t_td = t + (1 - s) * (1 - duty) * T
                    ptd, ytd = pose_at(t_td)
                    fwd = Vector((math.cos(ytd), math.sin(ytd), 0))
                    target = ptd + Matrix.Rotation(ytd, 3, "Z") @ self.neutral[i] + fwd * (stance_travel / 2)
                    target.z = 0.0
                    swing[i] = (Vector(self.foot_pos[i]), target)
                a, b = swing[i]
                p = a.lerp(b, _smooth(s))
                p.z = self.step_height * math.sin(math.pi * s)
                self.foot_pos[i] = p
            self.frame += 1
            self._key_all(bob=bob * math.sin(4 * math.pi * t / T), pitch=-0.03 * speed * math.sin(4 * math.pi * t / T),
                          roll=0.02 * math.sin(2 * math.pi * t / T) * (1 if gait == "walk" else 0))
        # settle: bring swinging feet down
        for i in range(n_legs):
            if self.foot_pos[i].z > 1e-4:
                self.foot_pos[i].z = 0.0
        self.frame += 1
        self._key_all()

    def finish(self):
        sc = bpy.context.scene
        sc.frame_start = 1
        sc.frame_end = self.frame
        sc.render.fps = self.fps
        for ob in [self.arm, self.look] + self.feet:
            for fc in _fcurves(ob):
                for kp in fc.keyframe_points:
                    kp.interpolation = "LINEAR"
        return self.frame


def script(mover, text):
    """Tiny DSL for the CLI:  'stand 0.5; walk 3 0.5 20 trot; look 1.5,1,0.3; crouch 0.05; walk 2 0.3 -40 walk'"""
    for cmd in text.split(";"):
        parts = cmd.strip().split()
        if not parts:
            continue
        op, args = parts[0], parts[1:]
        if op == "stand":
            mover.stand(float(args[0]) if args else 1.0)
        elif op == "walk":
            secs = float(args[0]); speed = float(args[1]) if len(args) > 1 else 0.5
            turn = float(args[2]) if len(args) > 2 else 0.0; gait = args[3] if len(args) > 3 else "trot"
            mover.walk(secs, speed=speed, turn=turn, gait=gait)
        elif op == "look":
            x, y, z = (float(v) for v in args[0].split(","))
            mover.look_at((x, y, z), over=float(args[1]) if len(args) > 1 else 0.4, ride=("ride" in args))
        elif op == "ahead":
            mover.look_ahead()
        elif op == "crouch":
            mover.crouch(float(args[0]), over=float(args[1]) if len(args) > 1 else 0.5)
        else:
            raise ValueError(f"unknown motion verb {op}")
    return mover.finish()
