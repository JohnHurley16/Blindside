# ---------------------------------------------------------------------------
# BLINDSIDE -- the cinematic camera rig, BELIEF SIDE.  TRAILER.md 8.
#
# This is a port of spikes/godot/cave/cinema.gd and it is deliberately kept
# recognisable next to it: the same shot format, the same anchor format, the
# same easing, the same handheld model, the same lens arithmetic, the same
# seven rules in the same order. Adopting that file rather than redesigning it
# is what makes a camera reproducible across the two projects at all.
#
# WHAT IS DIFFERENT HERE, and every difference is forced by the register:
#
#   1. A SHOT DECLARES ITS FRAME.  "world" or "survey".
#
#        world   the camera is standing in the mine. It has a 0.35 m body, it
#                sweeps against the TRUTH geometry, and it obeys every rule
#                the cave rig obeys. This is the register the belief cuts are
#                in, because a belief cut is cut FROM a cave shot and the two
#                cameras must pass or fail together.
#
#        survey  the camera is the replay's map view: thirty metres over the
#                workings looking down at an accumulated cloud. There is no
#                body because there is no place -- the camera is not in the
#                mine, it is over the drawing. It collides with NOTHING, and
#                the price of that exemption is the next rule.
#
#   2. A SURVEY CAMERA MAY NEVER DRAW TRUTH.  That is the whole of the
#      collision argument in one line:
#
#          A camera that draws the world has a body. A camera that draws only
#          the drawing does not need one -- and it may then never draw the
#          world.
#
#      The moment truth is in frame the camera is claiming to stand somewhere,
#      and a camera that claims to stand somewhere can be caught standing
#      inside a wall by the next cut. So `truth: true` on a survey shot is a
#      validation FAILURE, not a warning.
#
#   3. A SURVEY CAMERA MUST NOT ENTER ITS OWN SUBJECT.  Flying a camera into
#      an accumulated point cloud is the survey register's version of flying
#      through a wall: the data closes over the lens and the frame becomes
#      noise. Rule 9 is the cloud's bounding box plus a margin.
#
#   4. THE SCRUB IS PART OF THE SHOT.  `t_from` / `t_to` move belief time
#      across the shot, so drift accumulates, a fix closes and a lie tears
#      DURING the take. TRAILER 6 forbids a still pretending to be footage and
#      LIDAR.md 4 found that the fix reads as a pair of frames and not as one:
#      the answer to both is that these are shots.
#
# Everything else -- ANCHOR = {st, r, u, f}, ease is smootherstep, linear is a
# failure, travel 0.15-2.5 m, no zoom, 36 x 20.25 mm sensor, 0.030 mm circle
# of confusion -- is the cave's, unchanged, because a shot list that means two
# different things in two projects is not a shared shot list.
# ---------------------------------------------------------------------------
extends RefCounted
class_name CloudRig

const BODY_R: float = 0.35
const NEAR_CLEAR: float = 0.40
const QUERY_MARGIN: float = 0.05
const MAX_TRAVEL: float = 2.5
const MIN_TRAVEL: float = 0.15
const MAX_SPEED: float = 1.2
const SAMPLES: int = 32
const GROUND_BAND: float = 0.18

const SENSOR_W_MM: float = 36.0
const SENSOR_H_MM: float = 20.25
const COC_MM: float = 0.030

# `survey` is the one addition. It has no floor rule because it has no floor:
# the camera is over the workings, not in them, and rule 10 says so out loud
# rather than letting an unchecked height slide through.
const HEIGHTS := {
	"floor":   [0.04, 0.40],
	"machine": [0.28, 0.56],
	"eye":     [1.38, 1.82],
	"crane":   [2.00, 9.00],
	"survey":  [-1.0e9, 1.0e9],
}

var world3d: World3D
var body: SphereShape3D
var geo                                  # LidarGeo
var cloud_lo: Vector3 = Vector3.ZERO
var cloud_hi: Vector3 = Vector3.ZERO
var have_cloud: bool = false

func setup(p_geo, n: Node3D) -> void:
	geo = p_geo
	body = SphereShape3D.new()
	body.radius = BODY_R
	world3d = n.get_world_3d()

func ready_space(n: Node3D) -> void:
	world3d = n.get_world_3d()

func set_cloud_bounds(lo: Vector3, hi: Vector3) -> void:
	cloud_lo = lo
	cloud_hi = hi
	have_cloud = true

func _ss() -> PhysicsDirectSpaceState3D:
	return world3d.direct_space_state

# ---------------------------------------------------------------------------
# anchors -- IDENTICAL arithmetic to the cave rig, on the same topology
# ---------------------------------------------------------------------------
func frame_at(st: int) -> Array:
	var ids: PackedInt32Array = geo.topo.edges[0]
	var i: int = clampi(st, 0, ids.size() - 1)
	var p: Vector3 = geo._st_pos(ids[i])
	var j: int = clampi(i + 1, 0, ids.size() - 1)
	var k: int = clampi(i - 1, 0, ids.size() - 1)
	var fwd: Vector3 = (geo._st_pos(ids[j]) - geo._st_pos(ids[k]))
	fwd.y = 0.0
	if fwd.length() < 0.01:
		fwd = Vector3(0, 0, -1)
	fwd = fwd.normalized()
	return [p, fwd.cross(Vector3.UP).normalized(), Vector3.UP, fwd]

# `f` is arc length along the drive, not a straight-line tangent offset. Same
# reason as the cave: a drive is a curve and a distance down it is measured
# along it, or a look target six metres "ahead" lands in the wall.
func drive_at(st: int, f: float) -> Array:
	var ids: PackedInt32Array = geo.topo.edges[0]
	var i: int = clampi(st, 0, ids.size() - 1)
	var step: int = 1 if f >= 0.0 else -1
	var rem: float = absf(f)
	while rem > 0.0:
		var j: int = i + step
		if j < 0 or j >= ids.size():
			break
		var a: Vector3 = geo._st_pos(ids[i])
		var b: Vector3 = geo._st_pos(ids[j])
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
			if step < 0:
				fwd = -fwd
			return [pos, fwd.cross(Vector3.UP).normalized(), Vector3.UP, fwd]
		rem -= seg
		i = j
	return frame_at(i)

# `ground_bias` is the one channel that does not survive the crossing between
# the two projects, and CINEMA.md 2 is the argument. `u` is metres above the
# floor HERE; the floor here is whatever the dressing put there; the cave's
# dressing is drawn from an ordered RNG stream and this spike's from a
# stateless hash, so the two never agree about what the camera is standing on.
# A matched shot therefore carries the owning project's own ground as a number
# and the rig adds it instead of guessing.
#
# It is applied to the MOVE anchors only, and that is deliberate. The exported
# number means "the height the other project's raycast found UNDER ITS CAMERA",
# which is a statement about one square metre of floor. Pushing it out to the
# look target three metres down the drive would move the aim by five degrees on
# the strength of a measurement taken somewhere else. Look and focus resolve
# locally; the residual is measured in shots/cinema/match.txt.
func resolve(a, ground_ov: float = NAN) -> Vector3:
	if a is Array:
		return Vector3(float(a[0]), float(a[1]), float(a[2]))
	if a is Vector3:
		return a
	var st: int = int(a.get("st", 0))
	var fr: Array = drive_at(st, float(a.get("f", 0.0)))
	var p: Vector3 = (fr[0] as Vector3) + (fr[1] as Vector3) * float(a.get("r", 0.0))
	var g: float = ground_ov if not is_nan(ground_ov) else _ground_y(p, st)
	p.y = g + float(a.get("u", 0.0))
	return p

func _ground_y(q: Vector3, st: int) -> float:
	if world3d != null:
		var top: float = _floor_near(q, st) + 2.6
		var r := PhysicsRayQueryParameters3D.create(
			Vector3(q.x, top, q.z), Vector3(q.x, top - 9.0, q.z))
		r.collision_mask = 2
		var hit: Dictionary = _ss().intersect_ray(r)
		if not hit.is_empty():
			return float((hit["position"] as Vector3).y)
	return _floor_near(q, st)

func _floor_near(q: Vector3, st: int) -> float:
	var ids: PackedInt32Array = geo.topo.edges[0]
	var lo: int = maxi(0, st - 26)
	var hi: int = mini(ids.size() - 1, st + 26)
	var best: float = 1e18
	var by: float = 0.0
	for i in range(lo, hi + 1):
		var sp: Vector3 = geo._st_pos(ids[i])
		var d2: float = (sp.x - q.x) * (sp.x - q.x) + (sp.z - q.z) * (sp.z - q.z)
		if d2 < best:
			best = d2
			by = sp.y
	return by

# ---------------------------------------------------------------------------
# easing, handheld, lensing -- the cave's, unchanged
# ---------------------------------------------------------------------------
static func ease_u(kind: String, t: float) -> float:
	var x: float = clampf(t, 0.0, 1.0)
	match kind:
		"inout":
			return x * x * x * (x * (x * 6.0 - 15.0) + 10.0)
		"in":
			return x * x * x
		"out":
			var y: float = 1.0 - x
			return 1.0 - y * y * y
		_:
			return x

static func ease_dudt(kind: String, t: float) -> float:
	var h: float = 0.0005
	return (ease_u(kind, t + h) - ease_u(kind, t - h)) / (2.0 * h)

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

static func fov_for(lens_mm: float) -> float:
	return rad_to_deg(2.0 * atan((SENSOR_H_MM * 0.5) / maxf(lens_mm, 4.0)))

static func dof_limits(lens_mm: float, tstop: float, focus_m: float) -> Array:
	var f: float = lens_mm
	var s: float = maxf(focus_m, 0.05) * 1000.0
	var H: float = (f * f) / (maxf(tstop, 0.7) * COC_MM) + f
	var near_mm: float = s * (H - f) / (H + s - 2.0 * f)
	var far_mm: float = 1.0e9
	if s < H:
		far_mm = s * (H - f) / (H - s)
	return [near_mm * 0.001, far_mm * 0.001, H * 0.001]

# ---------------------------------------------------------------------------
# the pose at a normalised time -- byte-for-byte the cave's, so that a shot
# with the same anchors, ease, seed and lens produces the same frustum
# ---------------------------------------------------------------------------
func pose(shot: Dictionary, tn: float) -> Dictionary:
	var u: float = ease_u(String(shot.get("ease", "inout")), tn)
	var gov: float = NAN
	if shot.has("ground_from"):
		gov = lerp(float(shot["ground_from"]), float(shot["ground_to"]), u)
	var mv: Dictionary = shot["move"]
	var a: Vector3 = resolve(mv["from"], gov)
	var b: Vector3 = resolve(mv["to"], gov)
	var p: Vector3
	if mv.has("via"):
		var c: Vector3 = resolve(mv["via"], gov)
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
			"tstop": float(shot.get("tstop", 2.8)), "look": tgt}

func _focus_dist(a, from: Vector3) -> float:
	if a is float or a is int:
		return float(a)
	return from.distance_to(resolve(a))

# The belief scrub at a normalised shot time. A shot without one is a HOLD in
# belief time and still moves the camera; a shot with one is the only way
# drift, a fix or a lie can be a SHOT rather than a pair of stills.
func scrub(shot: Dictionary, tn: float, t_end: float) -> float:
	if not shot.has("t_from"):
		return t_end
	# A value <= 0 is relative to the END of the run, which is how a shot that
	# has to catch a correction is authored: the fix lands at t_end - 1.2 and
	# the shot wants to be sitting on it. A value > 0 is an absolute time.
	#
	# This started as "< 0 is relative" and it cost an hour: `t_to: 1.0` on the
	# fold meant "one second past the end" to me and "one second past the
	# START" to the rig, so the shot scrubbed BACKWARDS through fifty-eight
	# seconds of the run and the last frame was an empty map. It rendered
	# without an error and it looked like the fold had thrown the whole cloud
	# out of frame.
	var a: float = float(shot["t_from"])
	var b: float = float(shot.get("t_to", a))
	if a <= 0.0:
		a = t_end + a
	if b <= 0.0:
		b = t_end + b
	return lerp(a, b, tn)

# ---------------------------------------------------------------------------
# validation. Nothing is repaired. Every failure carries the number.
# ---------------------------------------------------------------------------
func _overlaps(p: Vector3) -> bool:
	var q := PhysicsShapeQueryParameters3D.new()
	q.shape = body
	q.transform = Transform3D(Basis.IDENTITY, p)
	q.margin = QUERY_MARGIN
	q.collision_mask = 2
	q.collide_with_areas = false
	var pts: PackedVector3Array = _ss().collide_shape(q, 24)
	if pts.size() == 0:
		return false
	for i in range(1, pts.size(), 2):
		if pts[i].y > p.y - GROUND_BAND:
			return true
	return false

# what the body is actually touching, for the report. A rejection that only
# says "the sphere overlaps" cannot be acted on.
func overlap_points(p: Vector3) -> PackedVector3Array:
	var q := PhysicsShapeQueryParameters3D.new()
	q.shape = body
	q.transform = Transform3D(Basis.IDENTITY, p)
	q.margin = QUERY_MARGIN
	q.collision_mask = 2
	q.collide_with_areas = false
	var pts: PackedVector3Array = _ss().collide_shape(q, 24)
	var out := PackedVector3Array()
	for i in range(1, pts.size(), 2):
		if pts[i].y > p.y - GROUND_BAND:
			out.push_back(pts[i])
	return out

func overlap_who(p: Vector3) -> String:
	var q := PhysicsShapeQueryParameters3D.new()
	q.shape = body
	q.transform = Transform3D(Basis.IDENTITY, p)
	q.margin = QUERY_MARGIN
	q.collision_mask = 2
	q.collide_with_areas = false
	var hits: Array = _ss().intersect_shape(q, 16)
	var names: Array = []
	for h in hits:
		var c = (h as Dictionary).get("collider")
		if c != null and not names.has(String(c.name)):
			names.append(String(c.name))
	return ", ".join(names)

func _sweep(a: Vector3, b: Vector3) -> float:
	var q := PhysicsShapeQueryParameters3D.new()
	q.shape = body
	q.transform = Transform3D(Basis.IDENTITY, a)
	q.motion = b - a
	q.margin = QUERY_MARGIN
	q.collision_mask = 2
	q.collide_with_areas = false
	var r: PackedFloat32Array = _ss().cast_motion(q)
	if r.size() < 2:
		return 1.0
	return r[0]

func _frustum_clear(p: Vector3, bs: Basis, lens_mm: float) -> float:
	var vt: float = tan(deg_to_rad(fov_for(lens_mm)) * 0.5)
	var ht: float = vt * (SENSOR_W_MM / SENSOR_H_MM)
	var worst: float = NEAR_CLEAR
	for sx in [-1.0, 0.0, 1.0]:
		for sy in [-1.0, 0.0, 1.0]:
			var d: Vector3 = (-bs.z + bs.x * (ht * sx) + bs.y * (vt * sy)).normalized()
			var q := PhysicsRayQueryParameters3D.create(p, p + d * NEAR_CLEAR)
			q.collision_mask = 2
			var hit: Dictionary = _ss().intersect_ray(q)
			if hit.is_empty():
				continue
			var hp: Vector3 = hit["position"]
			var hn: Vector3 = hit["normal"]
			if hn.y > 0.60 and hp.y < p.y - 0.05:
				continue
			worst = minf(worst, p.distance_to(hp))
	return worst

func sees_centreline(p: Vector3, st: int) -> bool:
	var c: Array = drive_at(st, 0.0)
	var tgt: Vector3 = (c[0] as Vector3)
	tgt.y = p.y
	if p.distance_to(tgt) < 0.05:
		return true
	var q := PhysicsRayQueryParameters3D.create(p, tgt)
	q.collision_mask = 2
	return _ss().intersect_ray(q).is_empty()

func floor_under(p: Vector3) -> float:
	var q := PhysicsRayQueryParameters3D.create(p + Vector3.UP * 0.05, p - Vector3.UP * 12.0)
	q.collision_mask = 2
	var hit: Dictionary = _ss().intersect_ray(q)
	if hit.is_empty():
		return -1.0
	return p.y - float((hit["position"] as Vector3).y)

func head_room(p: Vector3) -> float:
	var q := PhysicsRayQueryParameters3D.create(p, p + Vector3.UP * 12.0)
	q.collision_mask = 2
	var hit: Dictionary = _ss().intersect_ray(q)
	if hit.is_empty():
		return 99.0
	return float((hit["position"] as Vector3).y) - p.y

# how far inside the cloud's own bounding box a point sits; negative is outside
func _into_cloud(p: Vector3, margin: float) -> float:
	if not have_cloud:
		return -1.0
	var lo: Vector3 = cloud_lo - Vector3.ONE * margin
	var hi: Vector3 = cloud_hi + Vector3.ONE * margin
	return minf(minf(minf(p.x - lo.x, hi.x - p.x), minf(p.y - lo.y, hi.y - p.y)),
				minf(p.z - lo.z, hi.z - p.z))

func validate(shot: Dictionary) -> Dictionary:
	var fail: Array = []
	var warn: Array = []
	var nm: String = String(shot.get("name", "?"))

	# 0 -- CONTINUITY, and it runs before any camera rule for the same reason
	# the cave rig puts it first: TRAILER 11.1 says the loadout and the skin are
	# part of the shot definition and are validated "in the same way the camera
	# is". Hero lives in res://machines/, which is a junction to the shared
	# machine layer, so this project and the cave are checking against ONE
	# declaration rather than against two copies of a convention. Nothing here
	# is ever repaired -- a validator that repairs its input teaches nobody
	# anything, and that rule is the cave's and is inherited on purpose.
	for h in Hero.validate(shot):
		fail.append(h)
	var ease: String = String(shot.get("ease", "inout"))
	var lens: float = float(shot["lens_mm"])
	var dur: float = float(shot["len_s"])
	var frame: String = String(shot.get("frame", "world"))
	var draws_truth: bool = bool(shot.get("truth", false))

	if frame != "world" and frame != "survey":
		fail.append("unknown frame '%s': a shot is in the world or over it" % frame)

	# 5 -- ease
	if ease == "linear" or ease == "":
		fail.append("linear move: a camera has mass and must ease in and out")

	# 7 -- lens bands
	if not ((lens >= 18.0 and lens <= 24.0) or (lens >= 35.0 and lens <= 50.0) or lens >= 85.0):
		warn.append("lens %.0f mm is outside the committed bands (18-24 / 35-50 / 85+)" % lens)

	# 11 -- a survey camera may never draw truth. This is the price of not
	# having a body: the moment the world is in frame the camera is claiming a
	# place, and a claimed place can be caught inside a wall by the next cut.
	if frame == "survey" and draws_truth:
		fail.append("a survey camera has no body and may not draw truth: "
			+ "truth in frame means the camera claims a place it has not proved")

	var pts: Array = []
	var mn_clear: float = 99.0
	var mn_clear_t: float = 0.0
	var worst_over: float = -1.0
	var h_lo: float = 99.0
	var h_hi: float = -99.0
	var head_lo: float = 99.0
	var worst_in_cloud: float = -1.0e9
	var worst_in_cloud_t: float = 0.0
	for i in range(SAMPLES + 1):
		var tn: float = float(i) / float(SAMPLES)
		var ps: Dictionary = pose(shot, tn)
		pts.append(ps)
		var p: Vector3 = ps["pos"]
		if frame == "world":
			if _overlaps(p) and worst_over < 0.0:
				worst_over = tn
			var c: float = _frustum_clear(p, ps["basis"], lens)
			if c < mn_clear:
				mn_clear = c
				mn_clear_t = tn
			var fh: float = floor_under(p)
			if fh >= 0.0:
				h_lo = minf(h_lo, fh)
				h_hi = maxf(h_hi, fh)
			head_lo = minf(head_lo, head_room(p))
		else:
			var d: float = _into_cloud(p, 0.75)
			if d > worst_in_cloud:
				worst_in_cloud = d
				worst_in_cloud_t = tn

	if frame == "world":
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

		# 1 -- body sweep
		var breach: float = -1.0
		for i in range(pts.size() - 1):
			var a: Vector3 = pts[i]["pos"]
			var b: Vector3 = pts[i + 1]["pos"]
			if a.distance_to(b) < 1e-5:
				continue
			if _sweep(a, b) < 0.999:
				breach = float(i) / float(SAMPLES)
				break
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
		elif hr == "survey":
			fail.append("height 'survey' is only legal in the survey frame")
		elif shot.has("ground_from"):
			# RULE 3 IS MEASURED WHERE THE SHOT WAS AUTHORED.
			#
			# A matched shot carries the owning project's own raycast -- "the
			# floor under this camera is at y = 0.14" -- and `u` is 0.42 above
			# it by construction. Re-measuring that against THIS project's
			# geometry does not check the shot, it checks the model, and this
			# project's model of the same cave is missing the breakdown block
			# the cave's camera is standing on. Measured: the local floor is
			# 0.27 m lower at the head of shot 18's move and identical at its
			# tail, and rule 3 duly rejected a camera that the cave had already
			# stood on solid ground.
			#
			# So the exported measurement governs, the local one is reported
			# next to it, and NOTHING else is relaxed: rules 1, 2 and 8 -- the
			# body, the near plane and the line of sight -- still run against
			# the geometry that is actually here, because those are questions
			# about whether the camera hits something, and a camera that hits
			# something here would hit it there.
			var band2: Array = HEIGHTS[hr]
			var mv2: Dictionary = shot["move"]
			var ua: float = float((mv2["from"] as Dictionary).get("u", 0.0))
			var ub: float = float((mv2["to"] as Dictionary).get("u", 0.0))
			if minf(ua, ub) < float(band2[0]) or maxf(ua, ub) > float(band2[1]):
				fail.append("height '%s' wants %.2f-%.2f m; the shot declares %.2f-%.2f m" % [
					hr, band2[0], band2[1], minf(ua, ub), maxf(ua, ub)])
			warn.append(("height is the exported one: %.2f m above the floor the CAVE rig "
				+ "found. Against this project's own floor the same camera runs %.2f-%.2f m, "
				+ "a disagreement of %.2f m -- see CINEMA.md 2.") % [
				ua, h_lo, h_hi, absf(h_hi - ub)])
		elif h_lo > 90.0:
			fail.append("no floor under the camera anywhere in the move")
		else:
			var band: Array = HEIGHTS[hr]
			if h_lo < float(band[0]) or h_hi > float(band[1]):
				fail.append("height '%s' wants %.2f-%.2f m; the move runs %.2f-%.2f m above the floor" % [
					hr, band[0], band[1], h_lo, h_hi])
			if hr == "crane" and head_lo < 0.5:
				fail.append("crane needs somewhere to hang from: only %.2f m of headroom" % head_lo)
	else:
		# 9 -- a survey camera must not enter its own subject. Flying into an
		# accumulated cloud is this register's version of flying through a
		# wall: the data closes over the lens and there is no picture left.
		if worst_in_cloud > 0.0:
			fail.append("camera is %.2f m inside the cloud's own extent at t=%.2f: "
				% [worst_in_cloud, worst_in_cloud_t]
				+ "a survey camera may not enter its subject")
		# 10 -- and it must still declare a height, so that nothing hovers by
		# accident. The declared height for a survey camera is metres above the
		# workings and it is checked against the cloud rather than the floor.
		if String(shot.get("height", "")) != "survey":
			fail.append("a survey shot must declare height 'survey'")

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
			"h_lo": h_lo, "h_hi": h_hi, "head": head_lo, "frame": frame,
			"in_cloud": worst_in_cloud,
			"fov": fov_for(lens), "dof": dof_limits(lens, float(shot.get("tstop", 2.8)),
				float(pts[0]["focus"]))}}
