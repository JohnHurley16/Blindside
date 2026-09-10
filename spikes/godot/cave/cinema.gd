# ---------------------------------------------------------------------------
# BLINDSIDE -- the cinematic camera rig.  TRAILER.md 8.
#
# A camera that clips a wall tells a viewer in one frame that this is a debug
# fly-through. So this camera has a body, a lens, and a validator that refuses
# a shot rather than quietly repairing it.
#
# THE SHOT FORMAT is a plain Dictionary, JSON-serialisable, so a shot list is
# data and not code. `shots_cinema.json` holds the trailer's cave shots.
#
#   {
#     "name":    "t16_lamp_comes_on",     # file stem for the sequence
#     "trailer": "16",                    # TRAILER.md 3 shot number, or ""
#     "len_s":   5.0,                     # duration, seconds
#     "lens_mm": 21.0,                    # focal length. Committed. Never zoomed.
#     "tstop":   2.8,                     # aperture, drives depth of field
#     "ease":    "inout",                 # in | out | inout   ("linear" is rejected)
#     "handheld_deg": 0.0,                # 0 = off. Peak sub-degree amplitude.
#     "height":  "eye",                   # floor | machine | eye | crane
#     "move":  {"from": ANCHOR, "to": ANCHOR, "via": ANCHOR?},
#     "look":  {"from": ANCHOR, "to": ANCHOR},
#     "focus": {"from": ANCHOR or number, "to": ANCHOR or number}
#   }
#
# An ANCHOR is either a world point [x, y, z], or a passage-frame offset from a
# station on the main drive:
#
#     {"st": 132, "r": 0.4, "u": 1.6, "f": -1.2}
#
# r = metres right of the centreline, u = metres above the FLOOR at that
# station, f = metres along the drive (+ is deeper). This is what makes a shot
# list portable across a re-generated cave: it names a place in the workings
# rather than a coordinate.
#
# WHAT THE VALIDATOR CHECKS, and it reports rather than repairs:
#   1  body       0.35 m sphere, swept from `from` to `to`, must not intersect
#   2  clearance  0.40 m of empty frustum ahead at every sampled instant
#   3  height     the declared height rule must match the floor under the camera
#   4  travel     a move is 0.15-2.5 m. A shot that must travel far is two shots
#   5  ease       no linear move; a camera has mass
#   6  speed      peak speed <= 1.2 m/s
#   7  lens       18-24 wide, 35-50 normal, 85+ long; nothing between, no zoom
# ---------------------------------------------------------------------------
extends RefCounted
class_name CameraRig

# The camera's body. TRAILER.md 8: a sphere of 0.35 m radius that sweeps
# against the same collision the machines use.
const BODY_R: float = 0.35
# Nothing clips the near plane. Keep 0.4 m of clearance in front at all times.
const NEAR_CLEAR: float = 0.40
# The shell mesh is the collision, but the rock shader parallax-maps up to
# 75 mm of aggregate DOWN from the polygon, so the visible floor sits below the
# collision floor. This margin buys that back and a little more.
const QUERY_MARGIN: float = 0.05
const MAX_TRAVEL: float = 2.5
const MIN_TRAVEL: float = 0.15
const MAX_SPEED: float = 1.2
const SAMPLES: int = 32

# A 16:9 crop of a full-frame sensor. 36.0 mm across is the number every focal
# length in TRAILER.md 8 is quoted against; the height follows from 16:9.
const SENSOR_W_MM: float = 36.0
const SENSOR_H_MM: float = 20.25
# The standard full-frame circle of confusion. Depth of field is derived from
# this and the T-stop rather than dialled by eye.
const COC_MM: float = 0.030

# Which heights are justifiable, and the band each one is allowed.
const HEIGHTS := {
	"floor":   [0.04, 0.40],
	"machine": [0.28, 0.56],
	"eye":     [1.38, 1.82],
	"crane":   [2.00, 9.00],
}

var world3d: World3D
var body: SphereShape3D
## The machine, so the shot's OWN machine is standing where the shot puts it
## while the camera is being tested against it. TRAILER 8 forbids passing
## through "not rock, not a prop, not a machine".
var fleet: CaveFleet
var topo: CaveTopology
var dress: CaveDressing
var static_root: StaticBody3D
var collision_tris: int = 0
var collision_props: int = 0
var build_ms: float = 0.0

# ---------------------------------------------------------------------------
# collision -- the layer a machine body would sweep against
# ---------------------------------------------------------------------------
# Kit that a body actually collides with. A 40 mm ballast chip is not an
# obstacle, and putting 19 000 collision shapes in the world to pretend it is
# would cost more than the whole post stack.
const OBSTACLES := ["set", "setfail", "arch", "pipe", "launder", "spoil",
	"pendant", "duct", "beacon", "pump", "tub", "mast", "drum", "case",
	"instrument", "block0", "block1", "block2", "bus"]

var shape_cache: Dictionary = {}
var kit_tris: Dictionary = {}

func build_collision(geo: Node3D, p_topo: CaveTopology, p_dress: CaveDressing,
					 world: Node3D) -> void:
	var t0: int = Time.get_ticks_usec()
	topo = p_topo
	dress = p_dress
	static_root = StaticBody3D.new()
	static_root.name = "CameraCollision"
	static_root.collision_layer = 1
	static_root.collision_mask = 0
	world.add_child(static_root)
	for chunk in geo.get_children():
		for g in chunk.get_children():
			if g is MeshInstance3D:
				var m: Mesh = (g as MeshInstance3D).mesh
				var faces: PackedVector3Array = m.get_faces()
				if faces.size() == 0:
					continue
				var sh := ConcavePolygonShape3D.new()
				sh.set_faces(faces)
				var cs := CollisionShape3D.new()
				cs.shape = sh
				static_root.add_child(cs)
				cs.global_transform = (g as MeshInstance3D).global_transform
				collision_tris += faces.size() / 3
			elif g is MultiMeshInstance3D:
				var nm: String = String(g.name)
				if not OBSTACLES.has(nm):
					continue
				var mm: MultiMesh = (g as MultiMeshInstance3D).multimesh
				# EXACT triangles, not the bounding box. The first version of
				# this used one BoxShape3D per instance on the mesh AABB and
				# every shot in the trailer was rejected, because a timber set
				# is a FRAME: its bounding box is the 2.4 x 2.4 m opening you
				# are supposed to walk through, so the box filled the drive.
				# The same is true of an arch, a duct ring and a mesh panel.
				# One shared ConcavePolygonShape3D per kit part, instanced.
				if not shape_cache.has(nm):
					var fc: PackedVector3Array = mm.mesh.get_faces()
					if fc.size() == 0:
						continue
					var csh := ConcavePolygonShape3D.new()
					csh.set_faces(fc)
					shape_cache[nm] = csh
					kit_tris[nm] = fc.size() / 3
				for i in range(mm.instance_count):
					var cs2 := CollisionShape3D.new()
					cs2.shape = shape_cache[nm]
					var xf: Transform3D = mm.get_instance_transform(i)
					static_root.add_child(cs2)
					cs2.transform = xf
					collision_props += 1
					collision_tris += int(kit_tris[nm])
	body = SphereShape3D.new()
	body.radius = BODY_R
	build_ms = float(Time.get_ticks_usec() - t0) / 1000.0

func ready_space(n: Node3D) -> void:
	# fetched fresh on every query: the space state handle is only valid inside
	# the physics step and Godot hands back null outside it.
	world3d = n.get_world_3d()

func _ss() -> PhysicsDirectSpaceState3D:
	return world3d.direct_space_state

# ---------------------------------------------------------------------------
# anchors
# ---------------------------------------------------------------------------
# The passage frame at a station on the main drive: origin on the floor at the
# centreline, +f down the drive, +r to its right, +u up.
func frame_at(st: int) -> Array:
	var ids: PackedInt32Array = topo.edges[0]
	var i: int = clampi(st, 0, ids.size() - 1)
	var p: Vector3 = dress._st_pos(ids[i])
	var j: int = clampi(i + 1, 0, ids.size() - 1)
	var k: int = clampi(i - 1, 0, ids.size() - 1)
	var fwd: Vector3 = (dress._st_pos(ids[j]) - dress._st_pos(ids[k]))
	fwd.y = 0.0
	if fwd.length() < 0.01:
		fwd = Vector3(0, 0, -1)
	fwd = fwd.normalized()
	var right: Vector3 = fwd.cross(Vector3.UP).normalized()
	return [p, right, Vector3.UP, fwd]

# `f` is ARC LENGTH along the drive, not a straight-line offset along the
# station's tangent. The first version used the tangent, and a look target 6 m
# "ahead" in a drive that bends landed inside the wall -- so the wide shot for
# trailer 16 came out pointed at a blown near face with the passage off to one
# side. A drive is a curve; a distance down it is measured along it.
# Returns [position on the centreline, right, up, forward] at that distance.
func drive_at(st: int, f: float) -> Array:
	var ids: PackedInt32Array = topo.edges[0]
	var i: int = clampi(st, 0, ids.size() - 1)
	var step: int = 1 if f >= 0.0 else -1
	var rem: float = absf(f)
	while rem > 0.0:
		var j: int = i + step
		if j < 0 or j >= ids.size():
			break
		var a: Vector3 = dress._st_pos(ids[i])
		var b: Vector3 = dress._st_pos(ids[j])
		var seg: float = Vector2(b.x - a.x, b.z - a.z).length()
		if seg < 1e-5:
			i = j
			continue
		if rem <= seg:
			var t: float = rem / seg
			var pos: Vector3 = a.lerp(b, t)
			var fwd: Vector3 = b - a
			fwd.y = 0.0
			if fwd.length() < 1e-4:
				fwd = Vector3(0, 0, -1)
			fwd = fwd.normalized()
			# forward always means DOWN the drive (increasing station index),
			# whichever way this walk went
			if step < 0:
				fwd = -fwd
			return [pos, fwd.cross(Vector3.UP).normalized(), Vector3.UP, fwd]
		rem -= seg
		i = j
	return frame_at(i)

func resolve(a) -> Vector3:
	if a is Array:
		return Vector3(float(a[0]), float(a[1]), float(a[2]))
	if a is Vector3:
		return a
	var st: int = int(a.get("st", 0))
	var fr: Array = drive_at(st, float(a.get("f", 0.0)))
	var p: Vector3 = (fr[0] as Vector3) + (fr[1] as Vector3) * float(a.get("r", 0.0))
	# `u` is height above the floor HERE, not above the floor at the station the
	# anchor names. A drive changes level as it runs, so a dolly that held a
	# constant world Y drifted out of its own height rule over 1.6 m -- which is
	# how the first pass of this rejected two of the four trailer shots.
	p.y = _ground_y(p, st) + float(a.get("u", 0.0))
	return p

# The floor an anchor is measured from is the one that is RENDERED, found with
# the same downward ray the validator uses. The station datum is only the
# design level: the swept shell is noise-displaced on top of it and carries
# breakdown, so the two differ by up to 0.3 m, and a shot authored against the
# datum lands outside its own height rule.
func _ground_y(q: Vector3, st: int) -> float:
	if world3d != null:
		var top: float = _floor_near(q, st) + 2.6
		var r := PhysicsRayQueryParameters3D.create(
			Vector3(q.x, top, q.z), Vector3(q.x, top - 9.0, q.z))
		r.collision_mask = 1
		var hit: Dictionary = _ss().intersect_ray(r)
		if not hit.is_empty():
			return float((hit["position"] as Vector3).y)
	return _floor_near(q, st)

# The floor of the nearest station on the main drive, searched in a window
# around the anchor's own station.
func _floor_near(q: Vector3, st: int) -> float:
	var ids: PackedInt32Array = topo.edges[0]
	var lo: int = maxi(0, st - 26)
	var hi: int = mini(ids.size() - 1, st + 26)
	var best: float = 1e18
	var by: float = 0.0
	for i in range(lo, hi + 1):
		var sp: Vector3 = dress._st_pos(ids[i])
		var d2: float = (sp.x - q.x) * (sp.x - q.x) + (sp.z - q.z) * (sp.z - q.z)
		if d2 < best:
			best = d2
			by = sp.y
	return by

# ---------------------------------------------------------------------------
# easing -- a camera has mass, so nothing starts or stops instantly
# ---------------------------------------------------------------------------
static func ease_u(kind: String, t: float) -> float:
	var x: float = clampf(t, 0.0, 1.0)
	match kind:
		"inout":
			# smootherstep: zero velocity AND zero acceleration at both ends.
			return x * x * x * (x * (x * 6.0 - 15.0) + 10.0)
		"in":
			return x * x * x
		"out":
			var y: float = 1.0 - x
			return 1.0 - y * y * y
		_:
			return x

# derivative of the easing, for the speed check
static func ease_dudt(kind: String, t: float) -> float:
	var h: float = 0.0005
	return (ease_u(kind, t + h) - ease_u(kind, t - h)) / (2.0 * h)

# ---------------------------------------------------------------------------
# handheld -- low frequency, sub-degree, off unless a shot asks for it
# ---------------------------------------------------------------------------
# Three octaves of value noise at 0.37 / 0.83 / 1.9 Hz. Nothing above 2 Hz: a
# real operator does not produce it, and anything faster reads as a shake
# effect rather than as a person holding a camera.
static func _h1(s: int, i: int) -> float:
	var n: int = (s * 374761393 + i * 668265263) & 0x7fffffff
	n = (n ^ (n >> 13)) * 1274126177
	return float(n & 0xffff) / 32767.5 - 1.0

static func _vnoise(seed_v: int, f: float, t: float) -> float:
	var x: float = t * f
	var i: int = int(floor(x))
	var u: float = x - float(i)
	u = u * u * (3.0 - 2.0 * u)
	return lerp(_h1(seed_v, i), _h1(seed_v, i + 1), u)

static func handheld(seed_v: int, t: float, deg: float) -> Vector3:
	if deg <= 0.0:
		return Vector3.ZERO
	var yaw: float = (_vnoise(seed_v, 0.37, t) * 0.60 + _vnoise(seed_v + 7, 0.83, t) * 0.28
		+ _vnoise(seed_v + 19, 1.90, t) * 0.12)
	var pit: float = (_vnoise(seed_v + 31, 0.41, t) * 0.60 + _vnoise(seed_v + 53, 0.77, t) * 0.28
		+ _vnoise(seed_v + 71, 1.70, t) * 0.12)
	var rol: float = (_vnoise(seed_v + 97, 0.29, t) * 0.75 + _vnoise(seed_v + 113, 0.61, t) * 0.25)
	return Vector3(deg_to_rad(pit * deg), deg_to_rad(yaw * deg), deg_to_rad(rol * deg * 0.55))

# ---------------------------------------------------------------------------
# lensing
# ---------------------------------------------------------------------------
# Godot's Camera3D.fov is the vertical field with the default KEEP_HEIGHT, so
# derive it from the sensor height. The rig sets keep_aspect explicitly so this
# does not depend on the project window shape.
static func fov_for(lens_mm: float) -> float:
	return rad_to_deg(2.0 * atan((SENSOR_H_MM * 0.5) / maxf(lens_mm, 4.0)))

# Depth of field from the lens, not from taste. Hyperfocal distance, then the
# near and far limits of acceptable sharpness at this focus distance.
static func dof_limits(lens_mm: float, tstop: float, focus_m: float) -> Array:
	var f: float = lens_mm
	var s: float = maxf(focus_m, 0.05) * 1000.0            # mm
	var H: float = (f * f) / (maxf(tstop, 0.7) * COC_MM) + f
	var near_mm: float = s * (H - f) / (H + s - 2.0 * f)
	var far_mm: float = 1.0e9
	if s < H:
		far_mm = s * (H - f) / (H - s)
	return [near_mm * 0.001, far_mm * 0.001, H * 0.001]

# ---------------------------------------------------------------------------
# the pose at a normalised time
# ---------------------------------------------------------------------------
func pose(shot: Dictionary, tn: float) -> Dictionary:
	var u: float = ease_u(String(shot.get("ease", "inout")), tn)
	var mv: Dictionary = shot["move"]
	var a: Vector3 = resolve(mv["from"])
	var b: Vector3 = resolve(mv["to"])
	var p: Vector3
	if mv.has("via"):
		var c: Vector3 = resolve(mv["via"])
		var iu: float = 1.0 - u
		p = a * (iu * iu) + c * (2.0 * iu * u) + b * (u * u)
	else:
		p = a.lerp(b, u)
	var lk: Dictionary = shot["look"]
	var tgt: Vector3 = resolve(lk["from"]).lerp(resolve(lk["to"]), u)
	var dir: Vector3 = tgt - p
	if dir.length() < 0.01:
		dir = Vector3(0, 0, -1)
	dir = dir.normalized()
	var yaw: float = atan2(-dir.x, -dir.z)
	var pitch: float = asin(clampf(dir.y, -1.0, 1.0))
	var hd: float = float(shot.get("handheld_deg", 0.0))
	var sd: int = int(shot.get("seed", 11))
	var hh: Vector3 = handheld(sd, tn * float(shot["len_s"]), hd)
	var basis := Basis.from_euler(Vector3(pitch + hh.x, yaw + hh.y, hh.z))
	# a handheld operator also translates, a few millimetres
	if hd > 0.0:
		var s2: float = hd * 0.006
		var tt: float = tn * float(shot["len_s"])
		p += basis.x * _vnoise(sd + 5, 0.44, tt) * s2
		p += basis.y * _vnoise(sd + 41, 0.51, tt) * s2
	var focus: float = p.distance_to(tgt)
	if shot.has("focus"):
		var fo: Dictionary = shot["focus"]
		focus = lerp(_focus_dist(fo.get("from"), p), _focus_dist(fo.get("to"), p), u)
	return {"pos": p, "basis": basis, "focus": focus, "lens": float(shot["lens_mm"]),
			"tstop": float(shot.get("tstop", 2.8))}

func _focus_dist(a, from: Vector3) -> float:
	if a is float or a is int:
		return float(a)
	return from.distance_to(resolve(a))

# ---------------------------------------------------------------------------
# validation
# ---------------------------------------------------------------------------
# THE GROUND IS NOT AN OBSTACLE.
#
# A 0.35 m sphere whose centre is at TRAILER 8's machine height of 0.40 m
# clears a perfectly flat floor by 50 mm, and this floor is not flat: it is
# noise-displaced, and it carries rail, sleepers and ballast. So the body
# sphere touches the ground in every low shot, and the first version of this
# rejected all of them.
#
# That is the two rules in section 8 colliding, and the resolution is in the
# section's own words: the camera "stands somewhere a body could stand". A rig
# resting on the floor is standing, not flying through. So a contact in the
# bottom of the sphere is permitted and the HEIGHT rule -- which is measured
# against the floor -- is what governs it. Everything else is a breach.
const GROUND_BAND: float = 0.18

## MASK 3, NOT 1, AND THE 2 IS THE MACHINE. Layer 1 is the cave shell and the
## kit; layer 2 is the hull proxy `fleet.gd` hangs off the machine. Every test
## that asks "is the camera inside something" asks about both. The tests that
## ask "where is the FLOOR" stay on mask 1, so a ray dropped under the rig can
## never land on the back of the machine.
const SOLID_MASK: int = 1 | CaveFleet.MACHINE_LAYER

## Layer 2 only, with no ground exemption: nothing on layer 2 is the floor.
func _in_machine(p: Vector3) -> bool:
	var q := PhysicsShapeQueryParameters3D.new()
	q.shape = body
	q.transform = Transform3D(Basis.IDENTITY, p)
	q.margin = QUERY_MARGIN
	q.collision_mask = CaveFleet.MACHINE_LAYER
	q.collide_with_areas = false
	return _ss().collide_shape(q, 2).size() > 0

func _overlaps(p: Vector3) -> bool:
	var q := PhysicsShapeQueryParameters3D.new()
	q.shape = body
	q.transform = Transform3D(Basis.IDENTITY, p)
	q.margin = QUERY_MARGIN
	q.collision_mask = SOLID_MASK
	q.collide_with_areas = false
	var pts: PackedVector3Array = _ss().collide_shape(q, 24)
	if pts.size() == 0:
		return false
	# collide_shape returns pairs; the odd entries are the points on the
	# collider, which is the surface the body would be pushed out of.
	for i in range(1, pts.size(), 2):
		if pts[i].y > p.y - GROUND_BAND:
			return true
	return false

func _sweep(a: Vector3, b: Vector3) -> float:
	# the safe fraction of the motion, 1.0 if wholly clear
	var q := PhysicsShapeQueryParameters3D.new()
	q.shape = body
	q.transform = Transform3D(Basis.IDENTITY, a)
	q.motion = b - a
	q.margin = QUERY_MARGIN
	q.collision_mask = SOLID_MASK
	q.collide_with_areas = false
	var r: PackedFloat32Array = _ss().cast_motion(q)
	if r.size() < 2:
		return 1.0
	return r[0]

# The near-plane corners plus the axis, at NEAR_CLEAR metres.
#
# Same exemption, same reason: a floor running up into the bottom of frame is
# a floor, and every low-angle dolly shot ever made has one inside 0.4 m. What
# section 8 forbids is "a wall dissolving into the lens". So a hit is only a
# breach if its surface is not up-facing ground below the camera.
func _frustum_clear(p: Vector3, bs: Basis, lens_mm: float) -> float:
	var vt: float = tan(deg_to_rad(fov_for(lens_mm)) * 0.5)
	var ht: float = vt * (SENSOR_W_MM / SENSOR_H_MM)
	var worst: float = NEAR_CLEAR
	for sx in [-1.0, 0.0, 1.0]:
		for sy in [-1.0, 0.0, 1.0]:
			var d: Vector3 = (-bs.z + bs.x * (ht * sx) + bs.y * (vt * sy)).normalized()
			var q := PhysicsRayQueryParameters3D.create(p, p + d * NEAR_CLEAR)
			q.collision_mask = SOLID_MASK
			var hit: Dictionary = _ss().intersect_ray(q)
			if hit.is_empty():
				continue
			var hp: Vector3 = hit["position"]
			var hn: Vector3 = hit["normal"]
			if hn.y > 0.60 and hp.y < p.y - 0.05:
				continue                       # ground, not a wall
			worst = minf(worst, p.distance_to(hp))
	return worst

# RULE 8, and it exists because the deliberate failure found the hole.
#
# The shell is a triangle soup, not a solid. A 0.35 m sphere sitting entirely
# INSIDE the rock touches no triangle, so the overlap test reports it clear --
# `xfail`'s end pose, 0.85 m into the wall, came back "overlaps=false". The
# swept test caught it on the way through, but a shot authored to START buried
# would have passed.
#
# So the camera must be able to see the passage it claims to be standing in:
# an unobstructed line from the camera to the centreline of its own station at
# its own height. Cheap, and it is the definition of being in the same room.
func sees_centreline(p: Vector3, st: int) -> bool:
	var c: Array = drive_at(st, 0.0)
	var tgt: Vector3 = (c[0] as Vector3)
	tgt.y = p.y
	if p.distance_to(tgt) < 0.05:
		return true
	var q := PhysicsRayQueryParameters3D.create(p, tgt)
	q.collision_mask = 1
	return _ss().intersect_ray(q).is_empty()

func floor_under(p: Vector3) -> float:
	var q := PhysicsRayQueryParameters3D.create(p + Vector3.UP * 0.05, p - Vector3.UP * 12.0)
	q.collision_mask = 1
	var hit: Dictionary = _ss().intersect_ray(q)
	if hit.is_empty():
		return -1.0
	return p.y - float((hit["position"] as Vector3).y)

func head_room(p: Vector3) -> float:
	var q := PhysicsRayQueryParameters3D.create(p, p + Vector3.UP * 12.0)
	q.collision_mask = 1
	var hit: Dictionary = _ss().intersect_ray(q)
	if hit.is_empty():
		return 99.0
	return float((hit["position"] as Vector3).y) - p.y

# Returns {ok, fail: [String], warn: [String], stats: {...}}
## THE MACHINE'S OWN RULE. The walk clips are baked IN PLACE and the stance
## feet slide backwards under the hull at exactly the gait's speed, so a node
## moved at any other speed skates (NOTES 5). A shot fixes the distance and the
## duration, so it has already fixed the speed, and the speed is checkable.
func skate_check(shot: Dictionary) -> Array[String]:
	var out: Array[String] = []
	var m: Dictionary = Hero.block(shot)
	if m.is_empty() or String(m.get("role", "")) != "hero":
		return out
	var cl: String = String(m.get("clip", "idle"))
	if cl != "walk" and cl != "trot":
		return out
	var at = m.get("at", null)
	if not (at is Dictionary) or not (at as Dictionary).has("from"):
		out.append("machine clip is '%s' but its `at` is a hold: a walking machine that does not travel skates on the spot" % cl)
		return out
	var d: float = resolve(at["from"]).distance_to(resolve(at["to"]))
	var v: float = Book.speed(String(m.get("chassis", "surveyor")), cl)
	var dur2: float = float(shot.get("len_s", 4.0))
	var want: float = v * dur2
	if absf(d - want) > 0.15:
		out.append(("machine travels %.2f m in %.1f s = %.2f m/s; the '%s' clip " +
			"is baked at %.2f m/s and needs %.2f m, so the feet would skate %.2f m")
			% [d, dur2, d / maxf(dur2, 0.01), cl, v, want, d - want])
	return out

func validate(shot: Dictionary) -> Dictionary:
	var fail: Array = []
	var warn: Array = []
	var nm: String = String(shot.get("name", "?"))

	# 0 -- CONTINUITY. TRAILER 11.1: the loadout and skin are part of the shot
	# definition and are validated in the same way the camera is, in the same
	# list, with the value that caused the rejection, and never corrected.
	for h in Hero.validate(shot):
		fail.append(h)
	for h2 in skate_check(shot):
		fail.append(h2)
	var ease: String = String(shot.get("ease", "inout"))
	var lens: float = float(shot["lens_mm"])
	var dur: float = float(shot["len_s"])

	# 5 -- ease
	if ease == "linear" or ease == "":
		fail.append("linear move: a camera has mass and must ease in and out")

	# 7 -- lens bands
	if not ((lens >= 18.0 and lens <= 24.0) or (lens >= 35.0 and lens <= 50.0) or lens >= 85.0):
		warn.append("lens %.0f mm is outside the committed bands (18-24 / 35-50 / 85+)" % lens)

	var pts: Array = []
	var mn_clear: float = 99.0
	var mn_clear_t: float = 0.0
	var worst_over: float = -1.0
	var h_lo: float = 99.0
	var h_hi: float = -99.0
	var head_lo: float = 99.0
	var mach_over: float = -1.0
	for i in range(SAMPLES + 1):
		var tn: float = float(i) / float(SAMPLES)
		# the machine first: it is one of the solids the camera may not enter
		if fleet != null:
			fleet.hero_pose(shot, tn, tn * float(shot.get("len_s", 4.0)))
		var ps: Dictionary = pose(shot, tn)
		pts.append(ps)
		var p: Vector3 = ps["pos"]
		if _overlaps(p) and worst_over < 0.0:
			worst_over = tn
		if mach_over < 0.0 and _in_machine(p):
			mach_over = tn
		var c: float = _frustum_clear(p, ps["basis"], lens)
		if c < mn_clear:
			mn_clear = c
			mn_clear_t = tn
		var fh: float = floor_under(p)
		if fh >= 0.0:
			h_lo = minf(h_lo, fh)
			h_hi = maxf(h_hi, fh)
		head_lo = minf(head_lo, head_room(p))

	# 8 -- in the same open space as the drive it is authored against
	var mv0 = (shot["move"] as Dictionary)["from"]
	if not (mv0 is Array):
		var st0: int = int(mv0.get("st", 0))
		var blind: float = -1.0
		for i in range(pts.size()):
			if not sees_centreline(pts[i]["pos"], st0):
				blind = float(i) / float(SAMPLES)
				break
		if blind >= 0.0:
			fail.append("no line of sight to the drive centreline at t=%.2f: the camera is not in the passage" % blind)

	# 1 -- body sweep, segment by segment along the sampled path
	var breach: float = -1.0
	for i in range(pts.size() - 1):
		var a: Vector3 = pts[i]["pos"]
		var b: Vector3 = pts[i + 1]["pos"]
		if a.distance_to(b) < 1e-5:
			continue
		if _sweep(a, b) < 0.999:
			breach = float(i) / float(SAMPLES)
			break
	# 1a -- the machine, NAMED. `_overlaps` would report this as "geometry",
	# which is true and useless: a camera that ends up inside the thing the
	# trailer is about is a different mistake from one that clips a set.
	if mach_over >= 0.0:
		fail.append("camera body enters the MACHINE at t=%.2f (the 0.35 m sphere is inside its hull)" % mach_over)
	if worst_over >= 0.0:
		fail.append("body intersects geometry at t=%.2f (the 0.35 m sphere overlaps)" % worst_over)
	elif breach >= 0.0:
		fail.append("swept body hits geometry at t=%.2f" % breach)

	# 2 -- near clearance
	if mn_clear < NEAR_CLEAR - 0.001:
		fail.append("frustum clearance falls to %.2f m at t=%.2f (needs %.2f)" % [
			mn_clear, mn_clear_t, NEAR_CLEAR])

	# 3 -- height rule
	var hr: String = String(shot.get("height", "eye"))
	if not HEIGHTS.has(hr):
		fail.append("unknown height rule '%s'" % hr)
	elif h_lo > 90.0:
		fail.append("no floor under the camera anywhere in the move")
	else:
		var band: Array = HEIGHTS[hr]
		if h_lo < float(band[0]) or h_hi > float(band[1]):
			fail.append("height '%s' wants %.2f-%.2f m; the move runs %.2f-%.2f m above the floor" % [
				hr, band[0], band[1], h_lo, h_hi])
		if hr == "crane" and head_lo < 0.5:
			fail.append("crane needs somewhere to hang from: only %.2f m of headroom" % head_lo)

	# 4 -- travel, 6 -- speed
	var travel: float = 0.0
	for i in range(pts.size() - 1):
		travel += (pts[i]["pos"] as Vector3).distance_to(pts[i + 1]["pos"])
	if travel > MAX_TRAVEL:
		fail.append("travels %.2f m; a shot that must go further is two shots (max %.1f)" % [
			travel, MAX_TRAVEL])
	var peak: float = 0.0
	for i in range(SAMPLES + 1):
		peak = maxf(peak, ease_dudt(ease, float(i) / float(SAMPLES)))
	var vmax: float = travel * peak / maxf(dur, 0.1)
	if vmax > MAX_SPEED:
		fail.append("peak speed %.2f m/s exceeds %.2f" % [vmax, MAX_SPEED])
	if travel < MIN_TRAVEL and travel > 0.001:
		warn.append("travels only %.2f m -- is this meant to be a HOLD?" % travel)

	return {"ok": fail.is_empty(), "fail": fail, "warn": warn, "name": nm,
		"stats": {"travel": travel, "vmax": vmax, "clear": mn_clear,
			"h_lo": h_lo, "h_hi": h_hi, "head": head_lo,
			"fov": fov_for(lens), "dof": dof_limits(lens, float(shot.get("tstop", 2.8)),
				float(pts[0]["focus"]))}}
