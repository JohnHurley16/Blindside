# ---------------------------------------------------------------------------
# BLINDSIDE -- the cinematic camera rig, PIT-HEAD.  TRAILER.md 8.
#
# Ported from spikes/godot/cave/cinema.gd. Everything that is a RULE came over
# unchanged: the 0.35 m body, the 0.40 m near-plane clearance, the height bands,
# the 0.15-2.5 m travel window, the 1.2 m/s speed cap, smootherstep easing, no
# zoom, no linear move, and the principle that a failure is REPORTED with the
# number that caused it and never repaired.
#
# ONE THING HAD TO BE REDESIGNED, and it is the whole difference between a
# tunnel and a site.
#
# THE CAVE'S ANCHOR names a station on the main drive:
#
#     {"st": 116, "r": 0.10, "u": 0.42, "f": 1.60}
#
# st is an index into a polyline, f is arc length along it. That works because a
# drive is one-dimensional: there is exactly one thing to be "along". A pit-head
# is not one-dimensional. It has no drive. It has a collar, a headframe, five
# buildings, nine zones, six walkways, a haul road, four stations a machine
# plugs into, twelve lighting columns, two masts and a 26-node course, and the
# layout already knows where every one of them is.
#
# THE SITE ANCHOR therefore names a PLACE and offsets inside that place's own
# frame:
#
#     {"at": "collar", "a": 6.0, "o": -2.0, "u": 1.60}
#
#   at  a place in the site plan (see PLACES below)
#   a   metres ALONG that place's own axis      (the cave's `f`)
#   o   metres to the right of that axis        (the cave's `r`)
#   u   metres above the GROUND AT THAT POINT   (the cave's `u`, unchanged)
#
# Every place derives its origin and its axis from `layout.gd`'s plan, which is
# the integer half of the generator -- the half that will become `blindside-gen`.
# So a shot names a place in a pit-head rather than a coordinate in a scene, in
# exactly the sense the cave's format meant it.
#
# And it is MORE portable than the cave's, not less. The cave's own CINEMA.md
# lists "every station index in shots_cinema.json is seed-7 specific" as a
# limitation: change the seed and the shot list needs re-scouting. Change the
# seed here and the collar is still the collar, the service bay is still the
# service bay, and the charge row is still the charge row -- because those are
# plan FIELDS, not indices into a generated polyline. The only place kinds that
# are seed-fragile are the ones that name an index into a generated list
# (`course:N`, `col<i>`, `spoil<i>`), and they are marked as such below.
#
# THE PLACES
#   collar              the shaft collar at the origin. Axis +X along the 2400 side.
#   headframe           same origin, axis +X. `u` is still above GROUND.
#   gantry              mid-span of the rail over the service bay, axis +X
#   gate                the gate span in the west fence, axis +X (into the site)
#   b:<kind>            a building: winding_house boiler_house fan_house
#                       service_bay store. Origin = footprint centre,
#                       axis = its long side.
#   z:<kind>            a zone: charge_row container_row tank_farm spares drums
#                       scrap pallets transformer muster. Same rule.
#   s:<kind>            a station a machine stands at: listening_post bench
#                       cradle course_root. Axis from the station's own yaw --
#                       these are the only places in the plan that carry a
#                       facing, and it is the facing a machine adopts.
#   road@<t>            fraction t of ARC LENGTH along the haul road, axis along
#                       the road. This is the closest thing on the site to the
#                       cave's drive, and it is measured the same way.
#   walk<i>@<t>         the same, on walkway i (0-5)
#   course:<n>          course node n, axis along its edge to its parent   [seeded]
#   col<i>              lighting column i                                  [seeded]
#   mast:<kind>         comms | stack
#   spoil<i>            spoil tip i, centre                                [seeded]
#
# An anchor may also be a plain world point [x, y, z], as in the cave.
# ---------------------------------------------------------------------------
extends RefCounted
class_name CameraRig

# ---- unchanged from the cave -----------------------------------------------
const BODY_R: float = 0.35
const NEAR_CLEAR: float = 0.40
const QUERY_MARGIN: float = 0.05
const MAX_TRAVEL: float = 2.5
const MIN_TRAVEL: float = 0.15
const MAX_SPEED: float = 1.2
const SAMPLES: int = 32
const SENSOR_W_MM: float = 36.0
const SENSOR_H_MM: float = 20.25
const COC_MM: float = 0.030
const GROUND_BAND: float = 0.18

const HEIGHTS := {
	"floor":   [0.04, 0.40],
	"machine": [0.28, 0.56],
	"eye":     [1.38, 1.82],
	"crane":   [2.00, 30.00],
}

# CHANGED FOR DAYLIGHT. The cave's crane rule is "at least 0.5 m of headroom to
# hang from", measured with an upward raycast -- in a tunnel there is always a
# back above you. On a site under open sky an upward ray hits nothing, so that
# rule passes a camera hovering 9 m over an empty yard, which is precisely what
# TRAILER 8 forbids ("Nothing hovers at 2.5 m for no reason").
#
# The surface version asks the site plan instead: a crane shot must have a
# STRUCTURE within reach whose top is at or above the lens. The headframe, the
# gantry, a lighting column, a mast, a pole or a building gable are all things a
# rig hangs off. CRANE_REACH is the jib, and it is a guess.
const CRANE_REACH: float = 12.0

var world3d: World3D
var body: SphereShape3D
var L: SurfaceLayout
## The machines, so that the shot's OWN machine is standing where the shot puts
## it while the camera is being tested against it. Without this a shot is
## validated against a machine parked somewhere else, which is worse than not
## testing at all because it reads as a pass.
var fleet: Fleet
var static_root: StaticBody3D
var collision_tris: int = 0
var collision_props: int = 0
var collision_ground_tris: int = 0
var build_ms: float = 0.0

## the MultiMeshInstance3Ds tagged as carriers, kept out of the collision bake
## and moved by `carry()`
var carriers: Array[MultiMeshInstance3D] = []

var _tri_cache: Dictionary = {}
## shape index -> the MultiMeshInstance3D it was baked from, so a rejection can
## name the object that caused it rather than a number
var shape_names: Array[String] = []

# ---------------------------------------------------------------------------
# collision -- the layer a machine body would sweep against
# ---------------------------------------------------------------------------
# The cave collides the shell mesh and 19 named kit parts, and deliberately does
# NOT collide loose scatter: "a 40 mm chip is not an obstacle, and 19 015
# collision shapes to pretend it is would cost more than the whole post stack."
#
# The surface has the same split already made for it, by the renderer rather
# than by a name list. `Batcher` bins every instance into SITE (silhouette
# structures), PROP (walking-distance objects) and DETAIL (underfoot: gravel,
# chippings, weeds, dropped fixings, litter -- 40 mm objects, culled at 55 m,
# no shadow). So the rule is exact and needs no list: SITE and PROP collide,
# DETAIL does not, and it is the same rule the cave applied by hand.
#
# Exact triangles, not bounding boxes, for the cave's reason: a portal frame, a
# gantry, a fence bay, a container door and a headframe leg are all FRAMES, and
# a frame's bounding box is the opening you are meant to see through.
func build_collision(root: Node3D, p_L: SurfaceLayout) -> void:
	var t0: int = Time.get_ticks_usec()
	L = p_L
	static_root = StaticBody3D.new()
	static_root.name = "CameraCollision"
	static_root.collision_layer = 1
	static_root.collision_mask = 0
	root.add_child(static_root)
	for c in root.get_children():
		if c is MeshInstance3D and String(c.name) == "Ground":
			var faces: PackedVector3Array = (c as MeshInstance3D).mesh.get_faces()
			if faces.size() > 0:
				shape_names.append("Ground")
				_add_shape(faces, (c as MeshInstance3D).global_transform)
				collision_ground_tris = faces.size() / 3
		elif c is MultiMeshInstance3D:
			var bucket: int = int(c.get_meta("bucket", Batcher.DETAIL))
			if bucket == Batcher.DETAIL:
				continue
			# A CARRIER IS NOT AN OBSTACLE TO THE CAMERA IT CARRIES, and this is
			# the one exemption in the whole rig that is not about the ground.
			# The cage moves with the camera bolted to it, so their relative
			# position never changes and no query between them can ever mean
			# anything. Leaving it in the bake would reject shot 14 for the
			# camera being where it is standing -- the same mistake as the cave's
			# swept test rejecting a rig for resting on the floor.
			# It is only sound BECAUSE the carrier really moves: see `carry()`.
			if String(c.get_meta("carrier", "")) != "":
				carriers.append(c)
				continue
			var mm: MultiMesh = (c as MultiMeshInstance3D).multimesh
			if mm == null or mm.mesh == null or mm.instance_count == 0:
				continue
			var mid: int = mm.mesh.get_instance_id()
			if not _tri_cache.has(mid):
				_tri_cache[mid] = mm.mesh.get_faces()
			var base: PackedVector3Array = _tri_cache[mid]
			if base.size() == 0:
				continue
			# ONE BAKED SHAPE PER MULTIMESH, not one shape per instance.
			#
			# The cave gives every kit instance its own CollisionShape3D sharing
			# a cached ConcavePolygonShape3D -- 951 nodes, and that is fine at
			# 951. The pit-head has tens of thousands of SITE and PROP
			# instances, and adding that many CollisionShape3D children to one
			# StaticBody3D is quadratic in the physics server: the first attempt
			# at this had not finished building after five minutes.
			#
			# So the triangles are transformed on the CPU and baked, one
			# ConcavePolygonShape3D per MultiMeshInstance3D. That is ~700 shapes
			# instead of ~20 000 nodes, it is the same geometry to the query,
			# and `Transform3D * PackedVector3Array` does the transform natively
			# rather than a vertex at a time in GDScript.
			var mtx: Transform3D = (c as MultiMeshInstance3D).global_transform
			var out := PackedVector3Array()
			out.resize(base.size() * mm.instance_count)
			var w: int = 0
			for i in range(mm.instance_count):
				var xf: PackedVector3Array = (mtx * mm.get_instance_transform(i)) * base
				for k in range(xf.size()):
					out[w + k] = xf[k]
				w += xf.size()
			shape_names.append(String(c.name))
			_add_shape(out, Transform3D.IDENTITY)
			collision_props += mm.instance_count
			collision_tris += out.size() / 3
	body = SphereShape3D.new()
	body.radius = BODY_R
	build_ms = float(Time.get_ticks_usec() - t0) / 1000.0

func _add_shape(faces: PackedVector3Array, xf: Transform3D) -> void:
	var sh := ConcavePolygonShape3D.new()
	sh.set_faces(faces)
	var cs := CollisionShape3D.new()
	cs.shape = sh
	static_root.add_child(cs)
	cs.global_transform = xf

func ready_space(n: Node3D) -> void:
	# fetched fresh on every query: the space state handle is only valid inside
	# the physics step and Godot hands back null outside it.
	world3d = n.get_world_3d()

func _ss() -> PhysicsDirectSpaceState3D:
	return world3d.direct_space_state

# ---------------------------------------------------------------------------
# places -- the site anchor's frame
# ---------------------------------------------------------------------------
# Returns [origin, right, up, forward]. Same shape as the cave's frame_at().
func place(id: String) -> Array:
	var P: Dictionary = L.plan
	if id == "collar" or id == "shaft" or id == "headframe":
		var S: Dictionary = P["shaft"]
		return _fr(Vector3(_m(S["cx"]), 0.0, _m(S["cz"])), Vector3(1, 0, 0))
	if id == "gantry":
		var G: Dictionary = P["gantry"]
		return _fr(Vector3(_m((int(G["x0"]) + int(G["x1"])) / 2), 0.0, _m(G["z"])),
			Vector3(1, 0, 0))
	# THE BRAID PLAIN, and it is the only anchor in this file that is not on the
	# pit-head. THE-ICE 8.2 turns shot 4 into "meltwater running off ice, macro"
	# and the object it asks for is two hundred metres south of the collar, out
	# on the valley floor. ACT-ONE 8.1 could not take that shot because the
	# pit-head's ground mesh was a flat lid over it; it is not any more, so the
	# shot has an anchor.
	#
	# It FINDS the channel rather than being told where it is. `river_z` is
	# -150 m but the braid wanders 60 m either side of that, so the plan's
	# number names a band and not a place. Marching the mask and taking its
	# maximum is the only way to name the thread, and it costs 80 evaluations
	# once. `a` runs down-valley, `o` runs across the channel.
	if id == "braid":
		var bx := 8.0
		var bz := -150.0
		var best := -1.0
		for i in 81:
			var zz: float = -250.0 + float(i) * 2.5
			var v: float = Valley.floor_masks(bx, zz).x
			if v > best:
				best = v
				bz = zz
		return _fr(Vector3(bx, 0.0, bz), Vector3(1, 0, 0))
	if id == "gate":
		var GA: Dictionary = P["gate"]
		return _fr(Vector3(_m(GA["x"]), 0.0, _m((int(GA["z0"]) + int(GA["z1"])) / 2)),
			Vector3(1, 0, 0))
	if id.begins_with("b:"):
		for b in P["buildings"]:
			if String(b["kind"]) == id.substr(2):
				return _rect(b)
		push_error("CINEMA: no building '%s'" % id.substr(2))
	if id.begins_with("z:"):
		for z in P["zones"]:
			if String(z["kind"]) == id.substr(2):
				return _rect(z)
		push_error("CINEMA: no zone '%s'" % id.substr(2))
	if id.begins_with("s:"):
		for s in P["stations"]:
			if String(s["kind"]) == id.substr(2):
				# a station is the only place in the plan that carries a facing,
				# and it is the direction a machine stands in. yaw is in
				# milli-degrees, which is how layout.gd keeps an angle integral.
				var th: float = deg_to_rad(float(s["yaw"]) / 1000.0)
				return _fr(Vector3(_m(s["x"]), 0.0, _m(s["z"])),
					Vector3(cos(th), 0.0, sin(th)))
		push_error("CINEMA: no station '%s'" % id.substr(2))
	if id.begins_with("road@"):
		return _poly(_road_pts(), id.substr(5).to_float())
	if id.begins_with("walk"):
		var at: int = id.find("@")
		var wi: int = int(id.substr(4, at - 4))
		var ws: Array = P["walkways"]
		var w: Array = ws[clampi(wi, 0, ws.size() - 1)]
		var pts: Array = []
		for q in w:
			pts.append(Vector3(_m(q[0]), 0.0, _m(q[1])))
		return _poly(pts, id.substr(at + 1).to_float())
	if id.begins_with("course:"):
		var C: Dictionary = P["course"]
		var n: int = int(id.substr(7))
		var nodes: Array = C["nodes"]
		n = clampi(n, 0, nodes.size() - 1)
		var pitch: int = int(C["pitch"])
		var pn: Vector3 = Vector3(_m(int(C["ox"]) + int(nodes[n][0]) * pitch), 0.0,
			_m(int(C["oz"]) + int(nodes[n][1]) * pitch))
		# axis = along the edge back to this node's parent, so `a` runs down the
		# passage the way the cave's `f` runs down the drive
		var ax := Vector3(1, 0, 0)
		for e in C["edges"]:
			if int(e[1]) == n:
				var pp: Vector3 = Vector3(_m(int(C["ox"]) + int(nodes[e[0]][0]) * pitch), 0.0,
					_m(int(C["oz"]) + int(nodes[e[0]][1]) * pitch))
				var d: Vector3 = pn - pp
				if d.length() > 0.01:
					ax = d.normalized()
				break
		return _fr(pn, ax)
	if id.begins_with("col"):
		var cols: Array = P["columns"]
		var ci: int = clampi(int(id.substr(3)), 0, cols.size() - 1)
		return _fr(Vector3(_m(cols[ci]["x"]), 0.0, _m(cols[ci]["z"])), Vector3(1, 0, 0))
	if id.begins_with("mast:"):
		for m in P["masts"]:
			if String(m["kind"]) == id.substr(5):
				return _fr(Vector3(_m(m["x"]), 0.0, _m(m["z"])), Vector3(1, 0, 0))
		push_error("CINEMA: no mast '%s'" % id.substr(5))
	if id.begins_with("spoil"):
		var sp: Array = P["spoil"]
		var si: int = clampi(int(id.substr(5)), 0, sp.size() - 1)
		return _fr(Vector3(_m(sp[si]["cx"]), 0.0, _m(sp[si]["cz"])), Vector3(1, 0, 0))
	push_error("CINEMA: unknown place '%s'" % id)
	return _fr(Vector3.ZERO, Vector3(1, 0, 0))

static func _m(v) -> float:
	return float(int(v)) / 1000.0

static func _fr(o: Vector3, fwd: Vector3) -> Array:
	var f: Vector3 = fwd
	f.y = 0.0
	if f.length() < 1e-4:
		f = Vector3(1, 0, 0)
	f = f.normalized()
	return [o, f.cross(Vector3.UP).normalized(), Vector3.UP, f]

# A rectangle's axis is its LONG side. That is the only choice that makes `a`
# mean the same thing for a 16 x 17 m container row and a 12 x 4 m charge row:
# `a` runs the way the thing is laid out.
static func _rect(r: Dictionary) -> Array:
	var x0: float = _m(r["x0"])
	var z0: float = _m(r["z0"])
	var x1: float = _m(r["x1"])
	var z1: float = _m(r["z1"])
	var c := Vector3((x0 + x1) * 0.5, 0.0, (z0 + z1) * 0.5)
	var ax := Vector3(1, 0, 0) if absf(x1 - x0) >= absf(z1 - z0) else Vector3(0, 0, 1)
	return _fr(c, ax)

func _road_pts() -> Array:
	var pts: Array = []
	for q in L.plan["road"]:
		pts.append(Vector3(_m(q[0]), 0.0, _m(q[1])))
	return pts

# ARC LENGTH along a polyline, which is the one idea that came straight across
# from the cave. Its drive_at() walks the drive's stations accumulating segment
# length because "a drive is a curve; a distance down it is measured along it",
# and the same is true of a haul road that bends round the collar apron. The
# difference is only that a fraction is a better handle than a station index
# when the polyline has four points instead of two hundred.
static func _poly(pts: Array, t: float) -> Array:
	if pts.size() < 2:
		return _fr(pts[0] if pts.size() > 0 else Vector3.ZERO, Vector3(1, 0, 0))
	var total: float = 0.0
	for i in range(pts.size() - 1):
		total += (pts[i] as Vector3).distance_to(pts[i + 1])
	var want: float = clampf(t, 0.0, 1.0) * total
	var acc: float = 0.0
	for i in range(pts.size() - 1):
		var a: Vector3 = pts[i]
		var b: Vector3 = pts[i + 1]
		var seg: float = a.distance_to(b)
		if seg < 1e-5:
			continue
		if acc + seg >= want:
			var u: float = (want - acc) / seg
			return _fr(a.lerp(b, u), b - a)
		acc += seg
	return _fr(pts[pts.size() - 1], (pts[pts.size() - 1] as Vector3) - (pts[pts.size() - 2] as Vector3))

# ---------------------------------------------------------------------------
# resolving an anchor
# ---------------------------------------------------------------------------
func resolve(a) -> Vector3:
	if a is Array:
		return Vector3(float(a[0]), float(a[1]), float(a[2]))
	if a is Vector3:
		return a
	var fr: Array = place(String(a.get("at", "collar")))
	var p: Vector3 = (fr[0] as Vector3) \
		+ (fr[3] as Vector3) * float(a.get("a", 0.0)) \
		+ (fr[1] as Vector3) * float(a.get("o", 0.0))
	# `u` is height above the ground HERE, not above the ground at the place the
	# anchor names -- the cave's rule, and it matters more on a site than in a
	# drive because the yard is graded flat and everything outside the pad is
	# not: the haul road falls 150 mm off the apron and the spoil rises 10 m.
	p.y = ground_y(p) + float(a.get("u", 0.0))
	return p

# THE GROUND AN ANCHOR IS MEASURED FROM, and this is a real difference from the
# cave rather than a detail.
#
# The cave finds it with a downward raycast against the collision, because the
# swept shell is noise-displaced on top of the station datum and the two differ
# by up to 0.3 m. On a site that method is wrong, and it was wrong in a way that
# showed up in the first run: a ray dropped at the collar hits the SHEAVE DECK
# 11.18 m up, one dropped in the service bay hits the roof at 6.27 m, one at the
# cradle hits it at 6.09 m, and one at the course root hits the top of the root
# post at 2.25 m. `u` would then mean "metres above whatever happens to be
# standing here", which is not a height rule, it is a hazard -- and it is a
# hazard that only exists because a site has things ABOVE it and a drive's
# ceiling is a metre and a half over your head everywhere.
#
# The pit-head does not need the raycast, because it already has the answer.
# `Ground.height(L, x, z)` is the site's own contract -- "the height every other
# dressing file must place against: the layout height plus the dressing relief.
# Anything that calls L.ground_mm directly and not this will float by up to
# 67 mm" -- and it is exactly the surface the ground mesh is built from.
#
# The raycast survives where it belongs: `floor_under()` still measures the
# HEIGHT RULE against what is rendered, so a camera authored on top of a crate
# fails its height band rather than quietly standing on the crate.
func ground_y(q: Vector3) -> float:
	if L == null:
		return 0.0
	return Ground.height(L, q.x, q.z)

# ---------------------------------------------------------------------------
# easing, handheld, lensing -- verbatim from the cave, and deliberately so
# ---------------------------------------------------------------------------
static func ease_u(kind: String, t: float) -> float:
	var x: float = clampf(t, 0.0, 1.0)
	match kind:
		"inout":
			return x * x * x * (x * (x * 6.0 - 15.0) + 10.0)
		"in":
			return x * x * x
		# CONSTANT ACCELERATION FROM REST, and it exists for MOUNTS ONLY.
		# A hoist cage leaves the collar under a constant pull and is still
		# gaining when the shot cuts. `in` (x cubed) is the wrong curve for that
		# by a wide margin -- it puts more than half of an 8 m descent into the
		# last quarter of the shot, which reads as a lurch rather than as a
		# departure. x squared is what a cage actually does. It is NOT offered
		# to a camera move: TRAILER 8's easing rule is about a body with mass
		# being pushed by a person, and a person does not accelerate all the way
		# to the cut.
		"accel":
			return x * x
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
# THE MOUNT FRAME -- a shot may declare that it is CARRIED
# ---------------------------------------------------------------------------
# CINEMA.md 7.2 and TRAILER 11: shot 14 is a camera riding the cage down the
# shaft, and it was rejected on four rules at once, every one of them correct
# and every one of them wrong about this shot. The reason is one sentence: A
# SHOT'S MOVE IS STATED IN WORLD COORDINATES, and TRAILER 8's rules were written
# for a camera on a dolly on the ground.
#
#   "travels 8.00 m; a shot that must go further is two shots"  -- a rule about
#       a camera TRAVELLING. A camera bolted to a descending cage travels 0 m;
#       the world moves past it.
#   "height 'machine' wants 0.28-0.56 m above the ground"       -- there is no
#       ground inside a shaft. There is a DECK, and the lens is 0.45 m above it.
#   "peak speed 3.00 m/s exceeds 1.20"                          -- 1.2 m/s is
#       how fast a person pushes a dolly. It is not how fast a hoist runs, and
#       the speed of the hoist is not the camera department's decision.
#
# So a shot may carry a `mount`:
#
#     "mount": {"what": "cage",
#               "from": [0, -0.70, 0], "to": [0, -8.70, 0], "ease": "in"}
#
# and then:
#
#   * `move` and `look` are OFFSETS IN THE MOUNT'S FRAME, in metres, and are
#     written as plain [x, y, z]. A mount frame is axis-aligned with the world:
#     a cage hangs on a rope and does not rotate, and pretending otherwise would
#     invent a facing nobody asked for.
#   * TRAVEL and SPEED are measured on the camera's motion RELATIVE TO THE
#     MOUNT. A bolted camera scores zero on both, which is the truth.
#   * HEIGHT is measured above the MOUNT'S OWN ORIGIN, which is its deck. The
#     four bands are unchanged, so `machine` still means 0.28-0.56 m and still
#     means "as high off the floor as the thing being photographed".
#   * EVERY PHYSICAL RULE IS UNCHANGED AND STILL RUNS IN WORLD SPACE: the body
#     sweep, the near-plane clearance and the buried test are facts about where
#     the lens actually is, and a mount is not a licence to fly through a wall.
#   * the mount's OWN speed is reported and NOT capped. A cage does what a cage
#     does; the rule it has to satisfy is that a real thing could carry a camera
#     at that speed, and a winding cage is exactly such a thing.
#
# This is the general form CINEMA.md 11.1 asked for -- "a shot may declare that
# it is carried by a moving thing" -- and it is what shots 17 and 22 will need
# the day the camera follows a walking machine.
static func has_mount(shot: Dictionary) -> bool:
	return shot.has("mount") and (shot["mount"] is Dictionary)

## The carrier's own origin at normalised time `tn`, in world space.
func mount_at(shot: Dictionary, tn: float) -> Vector3:
	var M: Dictionary = shot["mount"]
	var mu: float = ease_u(String(M.get("ease", "inout")), tn)
	return resolve(M["from"]).lerp(resolve(M["to"]), mu)

## Move the carrier's instances so the thing the camera is riding actually
## rides. Without this the exemption in `build_collision` would be a lie.
func carry(shot: Dictionary, tn: float) -> void:
	if carriers.is_empty():
		return
	var d := Vector3.ZERO
	if has_mount(shot):
		d = mount_at(shot, tn) - mount_at(shot, 0.0)
	for c in carriers:
		c.position = d

## An offset in a mount's frame. Always a plain [x, y, z] in metres: a mount has
## no ground to measure `u` from and no axis to measure `a` along, so the site
## anchor's vocabulary does not apply inside one and is refused rather than
## quietly reinterpreted.
static func _local(a) -> Vector3:
	if a is Array:
		return Vector3(float(a[0]), float(a[1]), float(a[2]))
	push_error("CINEMA: a mounted shot's anchors are [x,y,z] offsets in the mount's frame")
	return Vector3.ZERO

# ---------------------------------------------------------------------------
# the pose at a normalised time
# ---------------------------------------------------------------------------
func pose(shot: Dictionary, tn: float) -> Dictionary:
	var u: float = ease_u(String(shot.get("ease", "inout")), tn)
	var mv: Dictionary = shot["move"]
	if has_mount(shot):
		return _pose_mounted(shot, tn, u)
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

## The same arithmetic as `pose`, with the mount's origin added to everything
## and the anchors read as local offsets. It is a separate function rather than
## a branch inside `pose` because every line of it means something different.
func _pose_mounted(shot: Dictionary, tn: float, u: float) -> Dictionary:
	var org: Vector3 = mount_at(shot, tn)
	var mv: Dictionary = shot["move"]
	var p: Vector3 = org + _local(mv["from"]).lerp(_local(mv["to"]), u)
	var lk: Dictionary = shot["look"]
	var tgt: Vector3 = org + _local(lk["from"]).lerp(_local(lk["to"]), u)
	var dir: Vector3 = tgt - p
	if dir.length() < 0.01:
		dir = Vector3(0, 0, -1)
	dir = dir.normalized()
	var basis := Basis.from_euler(Vector3(asin(clampf(dir.y, -1.0, 1.0)),
		atan2(-dir.x, -dir.z), 0.0))
	var hd: float = float(shot.get("handheld_deg", 0.0))
	if hd > 0.0:
		var hh: Vector3 = handheld(int(shot.get("seed", 11)), tn * float(shot["len_s"]), hd)
		basis = Basis.from_euler(Vector3(asin(clampf(dir.y, -1.0, 1.0)) + hh.x,
			atan2(-dir.x, -dir.z) + hh.y, hh.z))
	var focus: float = p.distance_to(tgt)
	if shot.has("focus"):
		var fo: Dictionary = shot["focus"]
		focus = lerp(float(fo.get("from", focus)), float(fo.get("to", focus)), u)
	return {"pos": p, "basis": basis, "focus": focus, "lens": float(shot["lens_mm"]),
			"tstop": float(shot.get("tstop", 2.8))}

# ---------------------------------------------------------------------------
# validation
# ---------------------------------------------------------------------------
## MASK 3, NOT 1, AND THE 2 IS THE MACHINES. TRAILER 8 forbids passing through
## "not rock, not a prop, not a machine, not the ground". While every machine on
## the site was a batched box it was in layer 1 with the rest of the props and
## the rule held by accident. The real chassis are skinned meshes with no body,
## so `fleet.gd` gives each one a hull proxy on layer 2 and every test that asks
## "is the camera inside something" asks about both layers. The tests that ask
## "where is the FLOOR" stay on mask 1, so a ray dropped under the rig can never
## land on the back of a machine.
const SOLID_MASK: int = 1 | Fleet.MACHINE_LAYER

## Layer 2 only, and no ground exemption: nothing on layer 2 is the floor.
func _in_machine(p: Vector3) -> bool:
	var q := PhysicsShapeQueryParameters3D.new()
	q.shape = body
	q.transform = Transform3D(Basis.IDENTITY, p)
	q.margin = QUERY_MARGIN
	q.collision_mask = Fleet.MACHINE_LAYER
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
	for i in range(1, pts.size(), 2):
		if pts[i].y > p.y - GROUND_BAND:
			return true
	return false

# THE SWEPT TEST, and it had to be rewritten -- this is the second real port
# change and it is the one that would have silently killed every low shot.
#
# The cave sweeps the body with `cast_motion`, which returns the safe fraction
# of the motion. `cast_motion` returns 0 whenever the shape STARTS in contact,
# and on a site every floor- and machine-height camera starts in contact: a
# 0.35 m sphere plus a 0.05 m query margin, centred 0.36 m above hardstanding,
# is 40 mm into the ground before it moves. So the cave's swept test rejected
# 100% of low surface shots with "swept body hits geometry at t=0.00", and it
# rejected them for standing on the floor.
#
# That is the same collision between TRAILER 8's two rules that CINEMA.md 4.2
# resolves for the overlap test, and the resolution has to apply here too: a
# contact in the bottom of the sphere is the rig standing, not the camera
# flying through. `cast_motion` cannot express that, because it has no way to
# ask "was the blocking contact ground?".
#
# So the sweep is done by walking the path with the SAME overlap test that
# already carries the ground exemption, at a spacing far finer than the body:
# 40 mm steps against a 700 mm sphere cannot miss anything. It costs about 60
# extra queries for a 2.5 m move and it is exact rather than approximate.
const SWEEP_STEP: float = 0.04

func _path_breach(pts: Array) -> float:
	for i in range(pts.size() - 1):
		var a: Vector3 = pts[i]["pos"]
		var b: Vector3 = pts[i + 1]["pos"]
		var d: float = a.distance_to(b)
		if d < SWEEP_STEP:
			continue
		var n: int = int(ceil(d / SWEEP_STEP))
		for k in range(1, n):
			if _overlaps(a.lerp(b, float(k) / float(n))):
				return (float(i) + float(k) / float(n)) / float(SAMPLES)
	return -1.0

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

# RULE 8, and it had to be re-derived for a site.
#
# The cave's version is "the camera must have an unobstructed line to the
# centreline of the drive it is authored against", and it exists because a
# triangle SOUP is not a solid: a 0.35 m sphere sitting entirely inside the rock
# touches no triangle, so the overlap test reports it clear. That hazard is
# identical here -- every mesh in the kit is an open shell.
#
# But there is no centreline on a pit-head, and the cave's own CINEMA.md flags
# the formulation as "a proxy [that] would misjudge a shot authored inside a
# chamber the drive centreline cannot see". A site is all chamber.
#
# So the test is made direct instead of proxied: fire six axis rays and ask
# whether the camera is looking at the BACK of a face in every direction. A
# camera in the open yard sees the ground's front face below it and nothing
# else; a camera under the service bay roof sees one back face above it; a
# camera authored inside a container sees six. Nothing about a passage, a
# centreline or a room is assumed.
const BURIED_RAY: float = 2.0

func buried(p: Vector3) -> int:
	var dirs := [Vector3(1, 0, 0), Vector3(-1, 0, 0), Vector3(0, 1, 0),
		Vector3(0, -1, 0), Vector3(0, 0, 1), Vector3(0, 0, -1)]
	var back: int = 0
	for d in dirs:
		var q := PhysicsRayQueryParameters3D.create(p, p + (d as Vector3) * BURIED_RAY)
		q.collision_mask = 1
		q.hit_back_faces = true
		var hit: Dictionary = _ss().intersect_ray(q)
		if hit.is_empty():
			continue
		if (hit["normal"] as Vector3).dot(d) > 0.0:
			back += 1
	return back

func floor_under(p: Vector3) -> float:
	var q := PhysicsRayQueryParameters3D.create(p + Vector3.UP * 0.05, p - Vector3.UP * 14.0)
	q.collision_mask = 1
	var hit: Dictionary = _ss().intersect_ray(q)
	if hit.is_empty():
		return -1.0
	return p.y - float((hit["position"] as Vector3).y)

# What a crane could hang off, out of the plan rather than out of a raycast.
# Returns [horizontal distance, name] of the nearest structure whose top is at
# or above `y`, or [-1, ""] if there is none.
func crane_mount(p: Vector3, y: float) -> Array:
	var best: float = 1e18
	var who: String = ""
	var P: Dictionary = L.plan
	var H: Dictionary = P["headframe"]
	var cands: Array = [
		[_m(H["cx"]), _m(H["cz"]), _m(H["height"]), "the headframe"],
		[_m((int(P["gantry"]["x0"]) + int(P["gantry"]["x1"])) / 2), _m(P["gantry"]["z"]),
			_m(P["gantry"]["h"]), "the gantry"]]
	for c in P["columns"]:
		cands.append([_m(c["x"]), _m(c["z"]), _m(c["h"]), "a lighting column"])
	for m in P["masts"]:
		cands.append([_m(m["x"]), _m(m["z"]), _m(m["h"]), "the %s mast" % m["kind"]])
	for po in P["poles"]:
		cands.append([_m(po["x"]), _m(po["z"]), _m(po["h"]), "a pole"])
	for b in P["buildings"]:
		cands.append([(_m(b["x0"]) + _m(b["x1"])) * 0.5, (_m(b["z0"]) + _m(b["z1"])) * 0.5,
			_m(b["h"]), "the %s" % b["kind"]])
	for c in cands:
		var gy: float = ground_y(Vector3(float(c[0]), 0.0, float(c[1])))
		if gy + float(c[2]) < y:
			continue
		var d: float = Vector2(float(c[0]) - p.x, float(c[1]) - p.z).length()
		if d < best:
			best = d
			who = String(c[3])
	if who == "":
		return [-1.0, ""]
	return [best, who]

## THE MACHINE'S OWN RULE, and it is as hard as any of the camera's.
##
## The walk clips are baked IN PLACE: `motion.py` plants the feet in world
## space and the exporter strips the body's travel, so the stance feet slide
## backwards under the hull at exactly the gait's speed. Move the node forward
## at that same speed and the feet are stationary on the ground. NOTES section
## 5: "any other speed and it skates."
##
## A shot says where the machine starts and where it ends and how long it
## lasts, so it has already fixed the speed, and the speed is checkable. This
## is the check. It is a FAIL and not a warning because a machine moonwalking
## across a trailer shot is the most legible possible tell that the walk is a
## texture rather than a gait.
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
	var want: float = v * float(shot.get("len_s", 4.0))
	if absf(d - want) > 0.15:
		out.append(("machine travels %.2f m in %.1f s = %.2f m/s; the '%s' clip " +
			"is baked at %.2f m/s and needs %.2f m, so the feet would skate %.2f m")
			% [d, float(shot.get("len_s", 4.0)), d / maxf(float(shot.get("len_s", 4.0)), 0.01),
				cl, v, want, d - want])
	return out


# Returns {ok, fail: [String], warn: [String], stats: {...}}
func validate(shot: Dictionary) -> Dictionary:
	var fail: Array = []
	var warn: Array = []
	var nm: String = String(shot.get("name", "?"))

	# 0 -- CONTINUITY. TRAILER 11.1: "the loadout and skin have to be part of the
	# shot definition and validated, in the same way the camera is". So it is in
	# the same list, it carries the value that caused it, and a shot that names
	# the wrong machine is REJECTED and not rendered -- exactly what happens to a
	# camera that would fly through a wall. Nothing here corrects the shot.
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

	var mounted: bool = has_mount(shot)
	var pts: Array = []
	var mn_clear: float = 99.0
	var mn_clear_t: float = 0.0
	var worst_over: float = -1.0
	var h_lo: float = 99.0
	var h_hi: float = -99.0
	var buried_t: float = -1.0
	var buried_n: int = 0
	var mach_over: float = -1.0
	for i in range(SAMPLES + 1):
		var tn: float = float(i) / float(SAMPLES)
		# the machine first: it is one of the solids the camera may not enter
		if fleet != null:
			fleet.hero_pose(shot, tn, tn * float(shot.get("len_s", 4.0)))
		carry(shot, tn)
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
		# THE HEIGHT A RULE IS MEASURED AGAINST. Normally the rendered ground
		# under the lens; inside a mount, the mount's own deck, because there is
		# no ground in a shaft and the lens is standing on something else.
		var fh: float = (p.y - mount_at(shot, tn).y) if mounted else floor_under(p)
		if fh >= 0.0:
			h_lo = minf(h_lo, fh)
			h_hi = maxf(h_hi, fh)
		if buried_t < 0.0:
			var bn: int = buried(p)
			if bn >= 5:
				buried_t = tn
				buried_n = bn

	# 8 -- not inside a solid
	if buried_t >= 0.0:
		fail.append("camera is inside solid geometry at t=%.2f (%d of 6 axis rays hit a back face)" % [
			buried_t, buried_n])

	# 1a -- the machine, named. `_overlaps` would report this as "geometry",
	# which is true and useless: a camera that ends up inside the thing the
	# trailer is about is a different mistake from one that clips a fence, and
	# the report should say which happened.
	if mach_over >= 0.0:
		fail.append("camera body enters the MACHINE at t=%.2f (the 0.35 m sphere is inside its hull)" % mach_over)

	# 1 -- body sweep
	var breach: float = _path_breach(pts)
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
	var mount: Array = [-1.0, ""]
	if not HEIGHTS.has(hr):
		fail.append("unknown height rule '%s'" % hr)
	elif h_lo > 90.0:
		fail.append("no ground under the camera anywhere in the move")
	else:
		var band: Array = HEIGHTS[hr]
		if h_lo < float(band[0]) or h_hi > float(band[1]):
			fail.append("height '%s' wants %.2f-%.2f m; the move runs %.2f-%.2f m above the ground" % [
				hr, band[0], band[1], h_lo, h_hi])
		if hr == "crane" and not mounted:
			mount = crane_mount((pts[0]["pos"] as Vector3), (pts[0]["pos"] as Vector3).y)
			if float(mount[0]) < 0.0:
				fail.append("crane at %.2f m has nothing on the site tall enough to hang from" % h_hi)
			elif float(mount[0]) > CRANE_REACH:
				fail.append("crane at %.2f m: the nearest thing tall enough to hang from is %s at %.1f m (reach %.1f)" % [
					h_hi, mount[1], mount[0], CRANE_REACH])

	# 4 -- travel, 6 -- speed. IN THE MOUNT'S FRAME when there is one: a camera
	# bolted to a descending cage travels 0 m and the world moves past it, and
	# measuring that motion as a dolly move is what rejected shot 14.
	var travel: float = 0.0
	var m_travel: float = 0.0
	var m_vmax: float = 0.0
	if mounted:
		var ma: Vector3 = _local(shot["move"]["from"])
		var mb: Vector3 = _local(shot["move"]["to"])
		travel = ma.distance_to(mb)
		var M: Dictionary = shot["mount"]
		m_travel = resolve(M["from"]).distance_to(resolve(M["to"]))
		var mpk: float = 0.0
		for i in range(SAMPLES + 1):
			mpk = maxf(mpk, ease_dudt(String(M.get("ease", "inout")), float(i) / float(SAMPLES)))
		m_vmax = m_travel * mpk / maxf(dur, 0.1)
	else:
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
	if travel < MIN_TRAVEL and travel > 0.001 and not mounted:
		warn.append("travels only %.2f m -- is this meant to be a HOLD?" % travel)
	# TRAILER 7: "Nothing on the surface moves ... every surface shot has a
	# camera move so the frame is not static". On the surface that is not a
	# style note, it is the only thing hiding a still yard, so a surface shot
	# with no move at all is a warning even inside the HOLD allowance.
	if travel < 0.001 and not mounted:
		warn.append("no camera move at all: TRAILER 7 requires one on every surface shot")

	return {"ok": fail.is_empty(), "fail": fail, "warn": warn, "name": nm,
		"stats": {"travel": travel, "vmax": vmax, "clear": mn_clear,
			"mounted": mounted, "m_travel": m_travel, "m_vmax": m_vmax,
			"m_what": String(shot.get("mount", {}).get("what", "")) if mounted else "",
			"h_lo": h_lo, "h_hi": h_hi, "mount": mount,
			"fov": fov_for(lens), "dof": dof_limits(lens, float(shot.get("tstop", 2.8)),
				float(pts[0]["focus"]))}}
