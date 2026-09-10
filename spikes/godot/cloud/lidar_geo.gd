# ---------------------------------------------------------------------------
# BLINDSIDE -- geometry for the scanning-sensor spike.
#
# This is NOT an art pass. It exists so that a laser has something real to hit,
# so that occlusion shadows fall where a viewer can check them, and so that a
# return can carry a surface class. `topology.gd` is copied verbatim from
# spikes/godot/cave/ (the deterministic layer); the shell sweep below is a
# stripped version of that spike's `dressing.gd` with every shader channel
# removed and the props reduced to the ones that cast a legible shadow.
#
# Everything is procedural. Nothing is imported.
#
# Output: one ArrayMesh and one StaticBody3D PER SURFACE CLASS, so a raycast
# can tell rock from steel from a retroreflector by asking the collider.
# ---------------------------------------------------------------------------
class_name LidarGeo
extends RefCounted

const CELL := 0.6
const RING_VERTS := 30
const HALF_RING := 15
const SUBSTEPS := 4

# --- surface classes. index -> (name, albedo, retro) -----------------------
# Lidar "intensity" is a reflectivity, not a radiance: it is what fraction of
# the emitted pulse came back. These are 905 nm diffuse reflectances, which is
# not the same as what the surface looks like to an eye -- wet rock is the
# extreme case and is why a puddle is a hole in a real scan.
const SURF_ROCK := 0
const SURF_WET := 1
const SURF_TIMBER := 2
const SURF_METAL := 3
const SURF_RETRO := 4
# ICE, added 2026-09-10 with the vertical cave. docs/THE-ICE.md 6.2 is the only
# material ruling the sensor has been given beyond water, and it is a different
# KIND of ruling: not a reflectance but an angular response. Near-infrared is
# strongly absorbed by ice, so a clean ice wall gives sparse, low-intensity,
# dropout-ridden returns -- not a mirror and not a hole -- and at grazing
# incidence it returns nothing at all while at normal incidence it flashes.
# The albedo below is only half the model; the rest is in lidar_scan.gd.
const SURF_ICE := 5
const N_SURF := 6
const SURF_NAME := ["rock", "wet rock", "timber", "steel", "retro", "ice"]
# GUESS. Ordered from published 905 nm reflectance tables (dry rock 0.2-0.4,
# wet surfaces near nothing, bare steel 0.4-0.6, engineering-grade retro tape
# 200-1000% of a Lambertian white). The retro value is deliberately > 1 so it
# clips the intensity channel, which is what a retroreflector does to a real
# unit and is the most recognisable single feature of a road scan.
const SURF_ALBEDO := [0.30, 0.045, 0.38, 0.55, 6.0, 0.075]
const SURF_RETRO_F := [0.0, 0.0, 0.0, 0.15, 1.0, 0.0]

var topo: CaveTopology
var noise: FastNoiseLite
var noise_lo: FastNoiseLite

var up_ranges: Array = []  # N_SURF of PackedInt32Array pairs: vertices whose
                           # normal must face up whatever the winding says. The
                           # chamber floor is one flat fan and getting its
                           # winding to agree with both the renderer and the
                           # physics server is not worth a day; state the
                           # normal instead.
var verts: Array = []      # N_SURF of PackedVector3Array
var idxs: Array = []       # N_SURF of PackedInt32Array
var meshes: Array = []     # N_SURF of ArrayMesh or null
var bodies: Array = []     # N_SURF of StaticBody3D or null

# chamber records, metres: cx, cz, radius, floor_y, station index
var chamber_m: Array = []
var big_chamber: int = 0
var machine_pos: Vector3 = Vector3.ZERO   # a landmark to point a camera at
# the main-drive centreline in metres, floor height included
var centre: PackedVector3Array = PackedVector3Array()

var tri_total := 0


# CAVE-MATCH MODE. Set before build() when the geometry has to be the same
# passage the cave spike renders, which is what a matched cut requires.
#
# Two things in this file were built for the sensor test and are wrong for a
# matched cut, and both are switched off here rather than deleted, because the
# sensor test still needs them:
#
#   * the biggest chamber is inflated to >= 9.5 m so a standing scanner lays a
#     dozen ground rings. The cave spike has no such chamber -- a chamber there
#     is just a wider length of the same swept drive -- so an inflated one is a
#     room that does not exist in the other project.
#   * chambers are cut out of the sweep and replaced with a dome and a floor
#     fan. The cave sweeps straight through.
#
# With cave_match on, a chamber is a wide bit of drive, exactly as it is in
# spikes/godot/cave/dressing.gd. See CINEMA.md 2.
var cave_match: bool = false

# VERTICAL, 2026-09-10. `levels > 1` switches topology.gd to its layered path
# (schema v2) and turns on the pitch geometry below. `levels == 1` is the
# frozen flat cave and reproduces hash 0xAD83E3ED, which is what every frame in
# shots/cinema/ was shot against; the default keeps that.
var levels: int = 1
var vertical: bool = false
# pitch records in metres: [axis_x, axis_z, top_y, bot_y, bore_r, kind, pitch_i]
var pitch_m: Array = []


func build(seed_v: int, length_cells: int) -> void:
	topo = CaveTopology.new()
	topo.generate(seed_v, length_cells, levels)
	vertical = topo.levels > 1

	noise = FastNoiseLite.new()
	noise.seed = seed_v
	noise.noise_type = FastNoiseLite.TYPE_SIMPLEX_SMOOTH
	noise.frequency = 0.9
	noise_lo = FastNoiseLite.new()
	noise_lo.seed = seed_v ^ 0x5bf03635
	noise_lo.noise_type = FastNoiseLite.TYPE_SIMPLEX_SMOOTH
	noise_lo.frequency = 0.14

	verts = []
	idxs = []
	up_ranges = []
	for i in range(N_SURF):
		verts.append(PackedVector3Array())
		idxs.append(PackedInt32Array())
		up_ranges.append(PackedInt32Array())

	_collect_chambers()
	_collect_pitches()
	_sweep_edges()
	if not cave_match:
		_build_chambers()
	if vertical:
		# ORDER MATTERS. The punch deletes floor and ceiling triangles that lie
		# inside a bore; the tube is built afterwards so it is not eaten by its
		# own hole. Doing it as a post-pass over finished triangles rather than
		# threading a hole through the sweep, the dome and the floor fan is
		# three separate special cases avoided for about thirty lines.
		_punch_pitches()
		_build_pitch_tubes()
	_place_props()
	if vertical:
		_place_pitch_props()
	_build_centreline()
	_commit()


# ---------------------------------------------------------------------------
# accumulators
# ---------------------------------------------------------------------------
# A SECOND collision body, for the CAMERA rather than for the laser, and the
# difference between them is the whole of spikes/godot/cave/cinema.gd 4.1:
#
#   "Loose scatter -- stones, ballast, grit, spall, litter -- is deliberately
#    NOT collision. A 40 mm chip is not an obstacle."
#
# The laser must see every chip, because a chip casts a return and a shadow.
# The camera must not, because a rig stands on the floor and a 0.3 m stone is
# something you step over. Merging the two is how the matched cut got rejected
# the first time this ran: the cave's camera walked straight down a drive that
# this spike had strewn with boulders the cave does not have.
#
# surf_* bodies are on layer 1 and the sensor masks to 1. cam_body is layer 2
# and the rig masks to 2.
var loose_mode: bool = false
var cam_v := PackedVector3Array()
var cam_i := PackedInt32Array()
var cam_body: StaticBody3D = null
var cam_tris: int = 0

func _add(cls: int, v: PackedVector3Array, ix: PackedInt32Array) -> void:
	if not loose_mode:
		var cb: int = cam_v.size()
		for p2 in v:
			cam_v.push_back(p2)
		for k2 in ix:
			cam_i.push_back(cb + k2)
	var base: int = (verts[cls] as PackedVector3Array).size()
	var vv: PackedVector3Array = verts[cls]
	for p in v:
		vv.push_back(p)
	verts[cls] = vv
	var ii: PackedInt32Array = idxs[cls]
	for k in ix:
		ii.push_back(base + k)
	idxs[cls] = ii


func _add_prim(cls: int, pm: PrimitiveMesh, xf: Transform3D) -> void:
	var arr: Array = pm.get_mesh_arrays()
	var v: PackedVector3Array = arr[Mesh.ARRAY_VERTEX]
	var ix: PackedInt32Array = arr[Mesh.ARRAY_INDEX]
	var out := PackedVector3Array()
	out.resize(v.size())
	for i in range(v.size()):
		out[i] = xf * v[i]
	_add(cls, out, ix)


func _box(cls: int, size: Vector3, xf: Transform3D) -> void:
	var b := BoxMesh.new()
	b.size = size
	_add_prim(cls, b, xf)


func _cyl(cls: int, r: float, h: float, xf: Transform3D, seg: int = 12) -> void:
	var c := CylinderMesh.new()
	c.top_radius = r
	c.bottom_radius = r
	c.height = h
	c.radial_segments = seg
	c.rings = 1
	_add_prim(cls, c, xf)


func _rock_lump(cls: int, centre_p: Vector3, r: float, sd: int, squash: float = 1.0) -> void:
	# a boulder: an icosphere-ish UV sphere pushed about by the noise field, so
	# its silhouette is not a circle and its shadow is not a wedge with a
	# smooth edge.
	var nu := 14
	var nv := 9
	var v := PackedVector3Array()
	var ix := PackedInt32Array()
	for j in range(nv + 1):
		var pv: float = float(j) / float(nv) * PI
		for i in range(nu):
			var pu: float = float(i) / float(nu) * TAU
			var d := Vector3(sin(pv) * cos(pu), cos(pv), sin(pv) * sin(pu))
			var n: float = noise.get_noise_3d(d.x * 3.0 + float(sd), d.y * 3.0, d.z * 3.0)
			var rr: float = r * (1.0 + 0.30 * n)
			var p: Vector3 = centre_p + Vector3(d.x * rr, d.y * rr * squash, d.z * rr)
			v.push_back(p)
	for j in range(nv):
		for i in range(nu):
			var a: int = j * nu + i
			var b: int = j * nu + (i + 1) % nu
			var c: int = (j + 1) * nu + i
			var d2: int = (j + 1) * nu + (i + 1) % nu
			ix.push_back(a); ix.push_back(c); ix.push_back(b)
			ix.push_back(b); ix.push_back(c); ix.push_back(d2)
	_add(cls, v, ix)


func _commit() -> void:
	meshes = []
	bodies = []
	tri_total = 0
	for cls in range(N_SURF):
		var v: PackedVector3Array = verts[cls]
		var ix: PackedInt32Array = idxs[cls]
		if v.size() == 0 or ix.size() == 0:
			meshes.append(null)
			bodies.append(null)
			continue
		var n: PackedVector3Array = _normals(v, ix)
		var ur2: PackedInt32Array = up_ranges[cls]
		for k in range(ur2.size() / 2):
			for i in range(ur2[k * 2], ur2[k * 2 + 1]):
				n[i] = Vector3(n[i].x, absf(n[i].y), n[i].z).normalized()
		var arr: Array = []
		arr.resize(Mesh.ARRAY_MAX)
		arr[Mesh.ARRAY_VERTEX] = v
		arr[Mesh.ARRAY_NORMAL] = n
		arr[Mesh.ARRAY_INDEX] = ix
		var am := ArrayMesh.new()
		am.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arr)
		meshes.append(am)
		tri_total += ix.size() / 3
		var body := StaticBody3D.new()
		body.name = "surf_" + SURF_NAME[cls].replace(" ", "_")
		body.set_meta("surf", cls)
		var cs := CollisionShape3D.new()
		var sh: ConcavePolygonShape3D = am.create_trimesh_shape()
		# A laser does not care which way a triangle was wound. Without this,
		# whether a surface answers a ray depends on the winding the mesh
		# builder happened to choose, which is a silent 20% swing in the return
		# count and has nothing to do with the sensor.
		sh.backface_collision = true
		cs.shape = sh
		body.add_child(cs)
		bodies.append(body)
	# the camera's body: everything except loose scatter, on its own layer so
	# the sensor never sees it twice
	if cam_v.size() > 0:
		var cam_arr: Array = []
		cam_arr.resize(Mesh.ARRAY_MAX)
		cam_arr[Mesh.ARRAY_VERTEX] = cam_v
		cam_arr[Mesh.ARRAY_INDEX] = cam_i
		var cam_mesh := ArrayMesh.new()
		cam_mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, cam_arr)
		cam_body = StaticBody3D.new()
		cam_body.name = "camera_collision"
		cam_body.collision_layer = 2
		cam_body.collision_mask = 0
		var ccs := CollisionShape3D.new()
		ccs.shape = cam_mesh.create_trimesh_shape()
		cam_body.add_child(ccs)
		cam_tris = cam_i.size() / 3


func _normals(v: PackedVector3Array, ix: PackedInt32Array) -> PackedVector3Array:
	var n := PackedVector3Array()
	n.resize(v.size())
	for i in range(v.size()):
		n[i] = Vector3.ZERO
	var t: int = ix.size() / 3
	for f in range(t):
		var a: int = ix[f * 3]
		var b: int = ix[f * 3 + 1]
		var c: int = ix[f * 3 + 2]
		var fn: Vector3 = (v[b] - v[a]).cross(v[c] - v[a])
		n[a] += fn
		n[b] += fn
		n[c] += fn
	for i in range(n.size()):
		n[i] = n[i].normalized() if n[i].length_squared() > 1e-12 else Vector3.UP
	return n


# ---------------------------------------------------------------------------
# the shell
# ---------------------------------------------------------------------------
func _st(i: int) -> PackedInt32Array:
	return topo.stations[i]


func _st_pos(i: int) -> Vector3:
	var s: PackedInt32Array = topo.stations[i]
	return Vector3(float(s[CaveTopology.S_X]) * CELL,
				   float(s[CaveTopology.S_FLOOR_MM]) * 0.001,
				   float(s[CaveTopology.S_Y]) * CELL)


func _hw(s: PackedInt32Array) -> float:
	var base: float = float(CaveTopology.WC_HALFWIDTH_MM[s[CaveTopology.S_WIDTH]]) * 0.001
	if s[CaveTopology.S_KIND] == CaveTopology.K_CHAMBER:
		base *= 1.5
	return base


func _ht(s: PackedInt32Array) -> float:
	var base: float = float(CaveTopology.WC_HEIGHT_MM[s[CaveTopology.S_WIDTH]]) * 0.001
	if s[CaveTopology.S_KIND] == CaveTopology.K_CHAMBER:
		base *= 1.35
	return base


# The profile, from the cave spike. Two registers interpolated on `worked`:
# natural rounded, and the horseshoe drive with vertical legs and a flat floor.
func _half_profile(s: float, worked: float, hw: float, ht: float, side: float) -> Vector2:
	var nu: float
	var nv: float
	if s < 0.22:
		nu = (s / 0.22) * hw * 0.92
		nv = 0.0
	else:
		var a: float = ((s - 0.22) / 0.78) * (PI * 0.5)
		var bulge: float = 1.0 + 0.22 * sin(a * 2.0)
		nu = hw * 0.92 * cos(a) * bulge
		nv = ht * sin(a) * (0.92 + 0.10 * cos(a * 3.0))
	var R: float = minf(hw, ht * 0.62)
	var leg: float = maxf(0.18, ht - R)
	var wu: float
	var wv: float
	if s < 0.28:
		wu = (s / 0.28) * hw
		wv = 0.0
	elif s < 0.55:
		wu = hw
		wv = ((s - 0.28) / 0.27) * leg
	else:
		var a2: float = ((s - 0.55) / 0.45) * (PI * 0.5)
		wu = R * cos(a2) + (hw - R)
		wv = leg + R * sin(a2)
	return Vector2(lerp(nu, wu, worked) * side, lerp(nv, wv, worked))


func _catmull(p0: Vector3, p1: Vector3, p2: Vector3, p3: Vector3, t: float) -> Vector3:
	var t2: float = t * t
	var t3: float = t2 * t
	return 0.5 * ((2.0 * p1) + (-p0 + p2) * t + (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * t2
		+ (-p0 + 3.0 * p1 - 3.0 * p2 + p3) * t3)


func _in_chamber(p: Vector3, k: float) -> bool:
	if cave_match:
		return false
	for c in chamber_m:
		var cc: Array = c
		# LEVEL AWARENESS, and without it the vertical cave is nonsense: a
		# chamber on level 2 is directly under a drive on level 0, and a plan
		# test alone cuts a hole in a passage 38 m above the room. The levels
		# are 13-34 m apart so a 5 m band is unambiguous.
		if absf(p.y - float(cc[3])) > 5.0:
			continue
		var d: float = Vector2(p.x - cc[0], p.z - cc[1]).length()
		if d < float(cc[2]) * k:
			return true
	return false


func _in_big_chamber(p: Vector3, k: float) -> bool:
	var c: Array = chamber_m[big_chamber]
	return Vector2(p.x - float(c[0]), p.z - float(c[1])).length() < float(c[2]) * k


func _collect_chambers() -> void:
	chamber_m = []
	var CR: int = CaveTopology.CH_ROW
	var nrow: int = topo.chambers.size() / CR
	# The biggest chamber in the stretch is inflated so that a sensor standing
	# in it lays more than a dozen complete ground rings; a 5 m room cannot
	# show the feature this spike exists to test. The others keep the cave
	# spike's own size, or they eat the drive and there is no corridor left to
	# walk twice. GUESS, both multipliers.
	var big := 0
	for ci in range(nrow):
		if topo.chambers[ci * CR + CaveTopology.CH_R] > topo.chambers[big * CR + CaveTopology.CH_R]:
			big = ci
	for ci in range(nrow):
		var sx: int = topo.chambers[ci * CR + CaveTopology.CH_X]
		var sy: int = topo.chambers[ci * CR + CaveTopology.CH_Y]
		var rc: int = topo.chambers[ci * CR + CaveTopology.CH_R]
		var sid: int = topo.chambers[ci * CR + CaveTopology.CH_SID]
		var st: PackedInt32Array = _st(sid)
		# In cave-match mode a chamber is not a room: it is the same swept
		# drive at HALL width, which is what the other spike renders. The
		# record is kept only so the walk planner can still ask where the wide
		# parts are; nothing is cut out and nothing is inflated.
		var r_m: float = _hw(st) * 1.5
		if not cave_match:
			if vertical:
				# NOT inflated. The sensor test needed one 9.5 m room so a
				# standing scanner could lay a dozen complete ground rings; a
				# MAP needs chambers that are the size the topology says, or
				# the plan is a lie about the place. GUESS: 0.95 of the
				# topology's radius in cells, floored at 3.0 m.
				r_m = maxf(3.0, float(rc) * 0.95)
			else:
				r_m = maxf(9.5, float(rc) * 1.5) if ci == big else maxf(3.4, float(rc) * 0.70)
		big_chamber = big
		chamber_m.append([float(sx) * CELL, float(sy) * CELL, r_m,
						  float(st[CaveTopology.S_FLOOR_MM]) * 0.001, sid])


func _sweep_edges() -> void:
	for e in range(topo.edges.size()):
		_sweep_edge(topo.edges[e])


func _sweep_edge(ids: PackedInt32Array) -> void:
	var n: int = ids.size()
	if n < 2:
		return
	var prev_ring := PackedVector3Array()
	var prev_ok := false
	for i in range(n):
		for sub in range(SUBSTEPS):
			var t: float = float(sub) / float(SUBSTEPS)
			var i0: int = maxi(0, i - 1)
			var i1: int = i
			var i2: int = mini(n - 1, i + 1)
			var i3: int = mini(n - 1, i + 2)
			var p: Vector3 = _catmull(_st_pos(ids[i0]), _st_pos(ids[i1]), _st_pos(ids[i2]), _st_pos(ids[i3]), t)
			var pn: Vector3 = _catmull(_st_pos(ids[i0]), _st_pos(ids[i1]), _st_pos(ids[i2]), _st_pos(ids[i3]), t + 0.02)
			var tangent: Vector3 = (pn - p).normalized()
			if tangent.length() < 0.5:
				tangent = Vector3(1, 0, 0)
			var right: Vector3 = tangent.cross(Vector3.UP).normalized()
			if right.length() < 0.5:
				right = Vector3(0, 0, 1)
			var sa: PackedInt32Array = _st(ids[i1])
			var sb: PackedInt32Array = _st(ids[i2])
			var med: int = sa[CaveTopology.S_MEDIUM] if vertical else CaveTopology.MED_ROCK
			var hw: float = lerp(_hw(sa), _hw(sb), t)
			var ht: float = lerp(_ht(sa), _ht(sb), t)
			var worked: float = lerp(float(sa[CaveTopology.S_WORKED]), float(sb[CaveTopology.S_WORKED]), t) / 255.0

			if _in_chamber(p, 1.0):
				prev_ok = false
				continue

			var ring := PackedVector3Array()
			for k in range(RING_VERTS):
				var side: float = 1.0
				var s01: float
				if k <= HALF_RING:
					s01 = float(k) / float(HALF_RING)
				else:
					side = -1.0
					s01 = float(RING_VERTS - k) / float(HALF_RING)
				var uv: Vector2 = _half_profile(s01, worked, hw, ht, side)
				var lp: Vector3 = p + right * uv.x + Vector3.UP * uv.y
				var outward: Vector3 = (right * uv.x + Vector3.UP * (uv.y - ht * 0.42)).normalized()
				var floor_mask: float = clampf(uv.y / 0.35, 0.0, 1.0)
				var big: float = noise_lo.get_noise_3d(lp.x, lp.y, lp.z)
				var fine: float = noise.get_noise_3d(lp.x * 2.2, lp.y * 2.2, lp.z * 2.2)
				var amp: float = lerp(0.52, 0.155, worked) * floor_mask
				lp += outward * (big * amp + fine * amp * 0.45)
				if uv.y < 0.02:
					lp.y += noise.get_noise_3d(lp.x * 3.1, 7.0, lp.z * 3.1) * lerp(0.10, 0.022, worked)
				ring.push_back(lp)
			if prev_ok:
				if med == CaveTopology.MED_ICE:
					_band(SURF_ICE, prev_ring, ring)
				elif med == CaveTopology.MED_ICE_OVER_ROCK:
					# THE-ICE 5.2: "the ice is a FILL, not a layer" -- it is
					# where the drainage put it, which is the low ground. So the
					# floor of the section is ice and the walls above it are the
					# rock the ice is lying in.
					_band_sel(SURF_ICE, prev_ring, ring, _floor_sel(true))
					_band_sel(SURF_ROCK, prev_ring, ring, _floor_sel(false))
				else:
					_band(SURF_ROCK, prev_ring, ring)
			prev_ring = ring
			prev_ok = true


func _band(cls: int, r0: PackedVector3Array, r1: PackedVector3Array) -> void:
	var v := PackedVector3Array()
	var ix := PackedInt32Array()
	for k in range(RING_VERTS):
		v.push_back(r0[k])
	for k in range(RING_VERTS):
		v.push_back(r1[k])
	for k in range(RING_VERTS):
		var k2: int = (k + 1) % RING_VERTS
		# inward-facing winding: the sensor is inside the tube
		ix.push_back(k); ix.push_back(RING_VERTS + k); ix.push_back(k2)
		ix.push_back(k2); ix.push_back(RING_VERTS + k); ix.push_back(RING_VERTS + k2)
	_add(cls, v, ix)


# Emit only the quads a selector asks for. The verts are pushed whole so the
# indices stay simple; a handful of unreferenced vertices costs nothing and a
# per-quad class does not have to duplicate the ring.
func _band_sel(cls: int, r0: PackedVector3Array, r1: PackedVector3Array, sel: PackedByteArray) -> void:
	var any := false
	for k in range(RING_VERTS):
		if sel[k] != 0:
			any = true
			break
	if not any:
		return
	var v := PackedVector3Array()
	var ix := PackedInt32Array()
	for k in range(RING_VERTS):
		v.push_back(r0[k])
	for k in range(RING_VERTS):
		v.push_back(r1[k])
	for k in range(RING_VERTS):
		if sel[k] == 0:
			continue
		var k2: int = (k + 1) % RING_VERTS
		ix.push_back(k); ix.push_back(RING_VERTS + k); ix.push_back(k2)
		ix.push_back(k2); ix.push_back(RING_VERTS + k); ix.push_back(RING_VERTS + k2)
	_add(cls, v, ix)


# The floor half of a section, by arc-length index. k = 0 is the floor centre;
# the profile reaches |u| = 0.92*hw at s = 0.22, which is k = 3 of 15.
var _sel_floor: PackedByteArray = PackedByteArray()
var _sel_wall: PackedByteArray = PackedByteArray()

func _floor_sel(want_floor: bool) -> PackedByteArray:
	if _sel_floor.is_empty():
		_sel_floor.resize(RING_VERTS)
		_sel_wall.resize(RING_VERTS)
		for k in range(RING_VERTS):
			var s01: float = float(k) / float(HALF_RING) if k <= HALF_RING 				else float(RING_VERTS - k) / float(HALF_RING)
			var f: bool = s01 < 0.30
			_sel_floor[k] = 1 if f else 0
			_sel_wall[k] = 0 if f else 1
	return _sel_floor if want_floor else _sel_wall


# ---------------------------------------------------------------------------
# chambers: a cylindrical wall under a noise-displaced dome, with a passage
# mouth punched east and west so a ray can escape down a drive and return
# nothing. That black wedge is one of the things this spike is testing.
# ---------------------------------------------------------------------------
func _build_chambers() -> void:
	for ci in range(chamber_m.size()):
		var c: Array = chamber_m[ci]
		var cx: float = c[0]
		var cz: float = c[1]
		var r_m: float = c[2]
		var fy: float = c[3]
		var wall_h: float = 2.6
		var dome_h: float = maxf(2.4, r_m * 0.42)
		var nu := 72
		var nv := 20
		var v := PackedVector3Array()
		var ix := PackedInt32Array()
		for j in range(nv + 1):
			var s: float = float(j) / float(nv)
			var rr: float
			var yy: float
			if s < 0.42:
				rr = r_m * (1.0 + 0.05 * sin(s * 7.0))
				yy = (s / 0.42) * wall_h
			else:
				var a: float = ((s - 0.42) / 0.58) * (PI * 0.5)
				rr = r_m * cos(a)
				yy = wall_h + dome_h * sin(a)
			for i in range(nu):
				var th: float = float(i) / float(nu) * TAU
				var px: float = cx + cos(th) * rr
				var pz: float = cz + sin(th) * rr
				var py: float = fy + yy
				var nrm: float = noise_lo.get_noise_3d(px, py * 1.4, pz)
				var fine: float = noise.get_noise_3d(px * 1.9, py * 1.9, pz * 1.9)
				var amp: float = 0.42 * clampf(yy / 0.6, 0.0, 1.0)
				var outw := Vector3(cos(th), 0.35, sin(th)).normalized()
				v.push_back(Vector3(px, py, pz) + outw * (nrm * amp + fine * amp * 0.4))
		for j in range(nv):
			for i in range(nu):
				var th2: float = float(i) / float(nu) * TAU
				# punch the two passage mouths: +X and -X, below the springing
				if float(j) / float(nv) < 0.40:
					var dx: float = cos(th2)
					if absf(dx) > cos(deg_to_rad(13.0)):
						continue
				var a0: int = j * nu + i
				var b0: int = j * nu + (i + 1) % nu
				var c0: int = (j + 1) * nu + i
				var d0: int = (j + 1) * nu + (i + 1) % nu
				ix.push_back(a0); ix.push_back(c0); ix.push_back(b0)
				ix.push_back(b0); ix.push_back(c0); ix.push_back(d0)
		_add(SURF_ROCK, v, ix)

		# the floor: a fan of rings, gently undulating, so the ground rings a
		# scanner lays on it are not perfect circles.
		var fv := PackedVector3Array()
		var fi := PackedInt32Array()
		var nr := 26
		fv.push_back(Vector3(cx, fy + _cfloor(cx, cz), cz))
		for j in range(1, nr + 1):
			var rad: float = r_m * float(j) / float(nr)
			for i in range(nu):
				var th3: float = float(i) / float(nu) * TAU
				var fx: float = cx + cos(th3) * rad
				var fz: float = cz + sin(th3) * rad
				fv.push_back(Vector3(fx, fy + _cfloor(fx, fz), fz))
		for i in range(nu):
			fi.push_back(0); fi.push_back(1 + (i + 1) % nu); fi.push_back(1 + i)
		for j in range(1, nr):
			for i in range(nu):
				var a1: int = 1 + (j - 1) * nu + i
				var b1: int = 1 + (j - 1) * nu + (i + 1) % nu
				var c1: int = 1 + j * nu + i
				var d1: int = 1 + j * nu + (i + 1) % nu
				fi.push_back(a1); fi.push_back(b1); fi.push_back(c1)
				fi.push_back(b1); fi.push_back(d1); fi.push_back(c1)
		var base_v: int = (verts[SURF_ROCK] as PackedVector3Array).size()
		_add(SURF_ROCK, fv, fi)
		var ur: PackedInt32Array = up_ranges[SURF_ROCK]
		ur.push_back(base_v)
		ur.push_back(base_v + fv.size())
		up_ranges[SURF_ROCK] = ur


func _cfloor(x: float, z: float) -> float:
	# GUESS: 90 mm of low-frequency relief plus 25 mm of fine. Enough that a
	# ground ring wobbles the way a real one does on a mine floor and not so
	# much that the ring structure is destroyed.
	return noise_lo.get_noise_3d(x * 1.6, 3.0, z * 1.6) * 0.09 \
		 + noise.get_noise_3d(x * 2.4, 11.0, z * 2.4) * 0.025


# ---------------------------------------------------------------------------
# props. Chosen for one reason only: each one casts a shadow a viewer can
# check against the thing that cast it.
# ---------------------------------------------------------------------------
func _place_props() -> void:
	# --- chamber furniture -------------------------------------------------
	# Skipped in cave-match mode: there is no chamber room to furnish, and a
	# pillar and a charging mast standing in the middle of a wide drive are
	# objects the other spike does not have.
	for ci in range(0 if cave_match else chamber_m.size()):
		var c: Array = chamber_m[ci]
		var cx: float = c[0]
		var cz: float = c[1]
		var r_m: float = c[2]
		var fy: float = c[3]
		var h: int = topo.draw(700, ci, 0)
		# five boulders on a ring, so their shadows fan out and do not overlap
		for k in range(5):
			var th: float = float(k) / 5.0 * TAU + float(h % 100) * 0.01
			var rad: float = r_m * (0.32 + 0.06 * float((h >> (k * 3)) & 7))
			var br: float = 0.42 + 0.13 * float((h >> (k * 2)) & 7)
			var bx: float = cx + cos(th) * rad
			var bz: float = cz + sin(th) * rad
			_rock_lump(SURF_ROCK, Vector3(bx, fy + _cfloor(bx, bz) + br * 0.55, bz), br, ci * 17 + k, 0.72)
		# a standing pillar: the cleanest possible shadow test, a full-height
		# cylinder whose shadow is a straight-sided corridor of no data.
		var pth: float = float(h % 360) * 0.0174
		var prad: float = r_m * 0.5
		_cyl(SURF_ROCK, 0.55, 5.2, Transform3D(Basis.IDENTITY,
			Vector3(cx + cos(pth) * prad, fy + 2.4, cz + sin(pth) * prad)), 18)
		# a stack of brought crates and a charging mast: steel, so they read
		# brighter than the rock at the same range.
		var kx: float = cx + cos(pth + 2.1) * r_m * 0.55
		var kz: float = cz + sin(pth + 2.1) * r_m * 0.55
		var ky: float = fy + _cfloor(kx, kz)
		_box(SURF_METAL, Vector3(1.1, 0.72, 0.86), Transform3D(Basis(Vector3.UP, 0.4), Vector3(kx, ky + 0.36, kz)))
		_box(SURF_METAL, Vector3(0.9, 0.62, 0.72), Transform3D(Basis(Vector3.UP, 0.9), Vector3(kx + 0.15, ky + 1.03, kz - 0.1)))
		_cyl(SURF_METAL, 0.05, 2.6, Transform3D(Basis.IDENTITY, Vector3(kx + 0.9, ky + 1.3, kz + 0.5)), 8)
		# a survey index plate on the mast: retroreflective, and it will clip
		# the intensity channel from anywhere in the chamber.
		_box(SURF_RETRO, Vector3(0.30, 0.30, 0.02),
			Transform3D(Basis(Vector3.UP, 0.0), Vector3(kx + 0.9, ky + 2.3, kz + 0.56)))
		# a machine standing on the floor: chassis, two wheels, a reflective
		# band. It is the thing a viewer will point at when asked what made
		# the shadow.
		var mx: float = cx + cos(pth + 3.9) * r_m * 0.45
		var mz: float = cz + sin(pth + 3.9) * r_m * 0.45
		var my: float = fy + _cfloor(mx, mz)
		var mb := Basis(Vector3.UP, pth + 0.7)
		if ci == big_chamber:
			machine_pos = Vector3(mx, my + 0.8, mz)
		_box(SURF_METAL, Vector3(1.6, 0.85, 0.95), Transform3D(mb, Vector3(mx, my + 0.75, mz)))
		_cyl(SURF_METAL, 0.34, 0.22, Transform3D(mb * Basis(Vector3(1, 0, 0), PI * 0.5), Vector3(mx, my + 0.36, mz) + mb * Vector3(0.55, 0.0, 0.52)), 14)
		_cyl(SURF_METAL, 0.34, 0.22, Transform3D(mb * Basis(Vector3(1, 0, 0), PI * 0.5), Vector3(mx, my + 0.36, mz) + mb * Vector3(0.55, 0.0, -0.52)), 14)
		_box(SURF_RETRO, Vector3(1.62, 0.14, 0.97), Transform3D(mb, Vector3(mx, my + 1.16, mz)))
		# a spoil heap against the wall: a low broad lump that shadows a long
		# shallow wedge of floor.
		var sx: float = cx + cos(pth + 5.2) * r_m * 0.74
		var sz: float = cz + sin(pth + 5.2) * r_m * 0.74
		_rock_lump(SURF_ROCK, Vector3(sx, fy + 0.35, sz), 1.7, ci + 400, 0.42)
		# standing water: a flat disc, and in a real scan it is a hole.
		var wx: float = cx + cos(pth + 1.2) * r_m * 0.66
		var wz: float = cz + sin(pth + 1.2) * r_m * 0.66
		_disc(SURF_WET, Vector3(wx, fy + _cfloor(wx, wz) + 0.012, wz), 1.5)

	# --- corridor furniture ------------------------------------------------
	for si in range(topo.stations.size()):
		var st: PackedInt32Array = _st(si)
		var p: Vector3 = _st_pos(si)
		if _in_chamber(p, 1.12):
			continue
		var hw: float = _hw(st)
		var ht: float = _ht(st)
		var wks: int = st[CaveTopology.S_WORKS]
		var along: int = st[CaveTopology.S_DEPTH]
		# timber sets on the 1.2 m module: two posts and a cap. The single most
		# useful prop here -- a regular row of posts down a drive produces a
		# regular row of shadow slots on the wall behind them.
		if (wks & CaveTopology.WK_SETS) != 0:
			# Sized to the CAVE SPIKE's own set, which is a 1.95 m post and a
			# 2.02 m cap scaled by (hw - 0.12)/1.18 across and (ht - 0.25)/2.02
			# up. The first version here stood 1.98 m posts under a cap at
			# 0.64 of the height, which put a beam across the drive at 2.05 m
			# -- half a metre below where the other project puts it. That is
			# not only a content difference: the rig finds the floor by casting
			# DOWN from 2.6 m above the station datum, so a cap at 2.05 m is a
			# floor, and every eye-height shot in this drive came out two
			# metres in the air.
			var psc: float = clampf((hw - 0.12) / 1.18, 0.55, 2.4)
			var psy: float = clampf((ht - 0.25) / 2.02, 0.5, 2.2)
			for side in [-1.0, 1.0]:
				_box(SURF_TIMBER, Vector3(0.18 * psc, 1.95 * psy, 0.16),
					Transform3D(Basis.IDENTITY, p + Vector3(0.0, 0.97 * psy, side * 1.18 * psc)))
			_box(SURF_TIMBER, Vector3(0.17, 0.20 * psy, 2.62 * psc),
				Transform3D(Basis.IDENTITY, p + Vector3(0.0, 2.02 * psy, 0.0)))
		# rail: two steel lines down the floor. In a scan these are two bright
		# parallel dotted lines and they are the clearest intensity feature in
		# a corridor.
		if (wks & CaveTopology.WK_RAIL) != 0:
			for side2 in [-1.0, 1.0]:
				_box(SURF_METAL, Vector3(0.62, 0.09, 0.055),
					Transform3D(Basis.IDENTITY, p + Vector3(0.0, 0.05, side2 * 0.36)))
		# a pipe run on the haunch
		if (wks & CaveTopology.WK_PIPE) != 0:
			_cyl(SURF_METAL, 0.09, 0.62,
				Transform3D(Basis(Vector3(1, 0, 0), PI * 0.5), p + Vector3(0.0, ht * 0.55, hw - 0.22)), 8)
		# beacon: the retroreflective marker the fiction already has
		if (wks & CaveTopology.WK_BEACON) != 0:
			_box(SURF_RETRO, Vector3(0.02, 0.22, 0.22),
				Transform3D(Basis.IDENTITY, p + Vector3(0.0, 1.05, -(hw - 0.06))))
		# A SPOIL HEAP against one wall where the topology says there is one.
		# The cave spike draws this from the same WK_SPOIL bit and the sensor
		# spike did not, which mattered: trailer shot 20 is "the clean wedge of
		# no data behind a fallen block" and a 0.3 m stone does not cast one.
		# Placed on the side the parent's index parity chooses, as the cave
		# does, so the two spikes agree about which wall it is against.
		if (wks & CaveTopology.WK_SPOIL) != 0:
			var sgn: float = 1.0 if (si % 2 == 0) else -1.0
			var hs: int = topo.draw(702, si, 0)
			var sc: float = 0.80 + 0.35 * float(hs % 100) / 100.0
			# Against the wall and it stays there. The first version was a
			# 1.4 m lump at 0.72 of the half-width, which reached 0.45 m PAST
			# the centreline and filled the drive.
			_rock_lump(SURF_ROCK, p + Vector3(0.0, 0.20 * sc, sgn * hw * 0.86),
				0.66 * sc, si + 5000, 0.52)
		# loose rock on the floor every few cells. NOT camera collision -- see
		# the note on cam_body above.
		if along % 3 == 1:
			var hh: int = topo.draw(701, si, 0)
			var off: float = (float(hh % 200) / 100.0 - 1.0) * hw * 0.7
			var rr2: float = 0.16 + 0.20 * float((hh >> 9) % 100) / 100.0
			loose_mode = true
			_rock_lump(SURF_ROCK, p + Vector3(0.0, rr2 * 0.5, off), rr2, si, 0.7)
			loose_mode = false


func _disc(cls: int, c: Vector3, r: float) -> void:
	var nu := 24
	var v := PackedVector3Array()
	var ix := PackedInt32Array()
	v.push_back(c)
	for i in range(nu):
		var th: float = float(i) / float(nu) * TAU
		v.push_back(c + Vector3(cos(th) * r, 0.0, sin(th) * r))
	for i in range(nu):
		ix.push_back(0); ix.push_back(1 + (i + 1) % nu); ix.push_back(1 + i)
	_add(cls, v, ix)



# ===========================================================================
# PITCHES -- the vertical axis, 2026-09-10
#
# docs/THE-ICE.md 5.3: "_half_profile() builds a floor, two legs and a crown,
# which a vertical shaft is not. A moulin needs a SECOND PROFILE FAMILY beside
# the sweep, not a modification of it." So this is a genuinely different
# builder: a closed ring in the horizontal plane, swept along an axis that is
# allowed to corkscrew, with the perimeter coordinate an ANGLE rather than an
# arc length up from a floor.
#
# The sensor consequence is the point of it. From the lip of a bore of radius r
# the steepest ring the device has (-30 deg) strikes the OPPOSITE WALL at
# r/tan30 = 1.73r below the head, and nothing below that is in the beam pattern
# at all. So a 14.7 m moulin returns about 1.9 m of tube and then nothing, at
# any depth, for ever. That is not a rendering decision; it is the envelope.
# ===========================================================================
func _collect_pitches() -> void:
	pitch_m = []
	if not vertical:
		return
	for i in range(topo.pitches.size()):
		var pr: PackedInt32Array = topo.pitch(i)
		pitch_m.append({
			"i": i,
			"x0": float(pr[CaveTopology.P_X]) * CELL,
			"z0": float(pr[CaveTopology.P_Y]) * CELL,
			"x1": float(pr[CaveTopology.P_TO_X]) * CELL,
			"z1": float(pr[CaveTopology.P_TO_Y]) * CELL,
			"top": float(pr[CaveTopology.P_TOP_MM]) * 0.001,
			"bot": float(pr[CaveTopology.P_BOT_MM]) * 0.001,
			"r": float(pr[CaveTopology.P_BORE_MM]) * 0.0005,
			"kind": pr[CaveTopology.P_KIND],
			"climb": pr[CaveTopology.P_CLIMB],
			"flags": pr[CaveTopology.P_FLAGS],
			"med": pr[CaveTopology.P_MEDIUM],
			"from_st": pr[CaveTopology.P_FROM_ST],
			"to_st": pr[CaveTopology.P_TO_ST],
		})


# The axis at a normalised depth. Moulins and collars corkscrew, because that
# is what falling water does to a hole and it is the reason a moulin does not
# read as a passage stood on end. GUESS: 0.22 rad per metre at 0.30 of a bore.
func _pitch_axis(pm: Dictionary, t: float) -> Vector3:
	var y: float = lerp(float(pm["top"]), float(pm["bot"]), t)
	var x: float = lerp(float(pm["x0"]), float(pm["x1"]), t)
	var z: float = lerp(float(pm["z0"]), float(pm["z1"]), t)
	var k: int = int(pm["kind"])
	var h: float = float(pm["top"]) - float(pm["bot"])
	if k == CaveTopology.PK_MOULIN or k == CaveTopology.PK_COLLAR:
		var a: float = t * h * 0.22 + float(int(pm["i"])) * 1.7
		var amp: float = float(pm["r"]) * 0.30
		x += cos(a) * amp
		z += sin(a) * amp
	elif k == CaveTopology.PK_COLLAPSE:
		x += t * float(pm["r"]) * 0.55
	return Vector3(x, y, z)


# A different RADIUS FUNCTION per kind, not a different parameter.
func _pitch_radius(pm: Dictionary, t: float, th: float) -> float:
	var r: float = float(pm["r"])
	var k: int = int(pm["kind"])
	var h: float = float(pm["top"]) - float(pm["bot"])
	match k:
		CaveTopology.PK_MOULIN, CaveTopology.PK_COLLAR:
			return r * (1.0 + 0.13 * sin(3.0 * th + t * h * 0.55))
		CaveTopology.PK_WINZE, CaveTopology.PK_ORE_PASS:
			# square-set: a superellipse of order 8, four timbered sides
			var c: float = absf(cos(th))
			var sn: float = absf(sin(th))
			return r / pow(pow(c, 8.0) + pow(sn, 8.0), 0.125)
		CaveTopology.PK_CREVASSE:
			# a slot: bore wide one way, 4.2x that the other
			var c2: float = cos(th)
			var s2: float = sin(th)
			return r / sqrt(c2 * c2 + (s2 * s2) / (4.2 * 4.2))
		CaveTopology.PK_AVEN:
			return r * (0.72 + 0.55 * (1.0 - t))
		CaveTopology.PK_COLLAPSE:
			return r * (0.80 + 0.34 * sin(2.0 * th + 5.0 * t))
	return r


func _pitch_surf(pm: Dictionary, y: float) -> int:
	var k: int = int(pm["kind"])
	if y > float(CaveTopology.BAND_ICE_BASE_MM) * 0.001:
		return SURF_ICE
	if k == CaveTopology.PK_WINZE or k == CaveTopology.PK_ORE_PASS:
		return SURF_TIMBER
	return SURF_ROCK


func _build_pitch_tubes() -> void:
	var seg := 26
	for pm_ in pitch_m:
		var pm: Dictionary = pm_
		var h: float = float(pm["top"]) - float(pm["bot"])
		if h < 0.6:
			continue
		var nv: int = maxi(4, int(round(h / 0.55)))
		var prev := PackedVector3Array()
		var prev_ok := false
		for j in range(nv + 1):
			var t: float = float(j) / float(nv)
			var axis: Vector3 = _pitch_axis(pm, t)
			var ring := PackedVector3Array()
			for i in range(seg):
				var th: float = float(i) / float(seg) * TAU
				var rr: float = _pitch_radius(pm, t, th)
				var px: float = axis.x + cos(th) * rr
				var pz: float = axis.z + sin(th) * rr
				# a bore is not smooth except where the ice polished it
				var rough: float = 0.045 if int(pm["med"]) == CaveTopology.MED_ICE else 0.16
				var nrm: float = noise_lo.get_noise_3d(px * 1.3, axis.y * 1.3, pz * 1.3)
				var fine: float = noise.get_noise_3d(px * 2.6, axis.y * 2.6, pz * 2.6)
				var outw := Vector3(cos(th), 0.0, sin(th))
				ring.push_back(Vector3(px, axis.y, pz) + outw * (nrm * rough + fine * rough * 0.4))
			if prev_ok:
				_ring_band(_pitch_surf(pm, axis.y), prev, ring, seg)
			prev = ring
			prev_ok = true
		# a cone of rubble at the bottom: everything the hole has ever dropped
		var bx: float = float(pm["x1"])
		var bz: float = float(pm["z1"])
		var by: float = float(pm["bot"])
		var nst: int = 14 + int(10.0 * float(pm["r"]))
		for q in range(nst):
			var hq: int = topo.draw(760, int(pm["i"]), q)
			var ta: float = float(hq % 1000) / 1000.0 * TAU
			var tr: float = float((hq >> 10) % 1000) / 1000.0 * (float(pm["r"]) * 1.5 + 0.5)
			var sr: float = 0.13 + 0.16 * float((hq >> 20) % 100) / 100.0
			_rock_lump(SURF_ROCK, Vector3(bx + cos(ta) * tr, by + sr * 0.55, bz + sin(ta) * tr),
				sr, 7700 + int(pm["i"]) * 41 + q, 0.7)


# an open band between two closed rings; the sensor is INSIDE the tube, so the
# winding faces in. `backface_collision` is on for the laser anyway.
func _ring_band(cls: int, r0: PackedVector3Array, r1: PackedVector3Array, seg: int) -> void:
	var v := PackedVector3Array()
	var ix := PackedInt32Array()
	for k in range(seg):
		v.push_back(r0[k])
	for k in range(seg):
		v.push_back(r1[k])
	for k in range(seg):
		var k2: int = (k + 1) % seg
		ix.push_back(k); ix.push_back(seg + k); ix.push_back(k2)
		ix.push_back(k2); ix.push_back(seg + k); ix.push_back(seg + k2)
	_add(cls, v, ix)


# Delete every triangle whose centroid lies inside a bore between the pitch
# floor and a little above its lip. That is the floor of the passage at the
# head and the ceiling of the passage at the foot, in one pass, without the
# sweep, the dome or the floor fan knowing anything about pitches.
func _punch_pitches() -> void:
	if pitch_m.is_empty():
		return
	var removed := 0
	for cls in range(N_SURF):
		var v: PackedVector3Array = verts[cls]
		var ix: PackedInt32Array = idxs[cls]
		if ix.is_empty():
			continue
		var keep := PackedInt32Array()
		for f in range(ix.size() / 3):
			var a: Vector3 = v[ix[f * 3]]
			var b: Vector3 = v[ix[f * 3 + 1]]
			var c: Vector3 = v[ix[f * 3 + 2]]
			var cen: Vector3 = (a + b + c) / 3.0
			var kill := false
			for pm_ in pitch_m:
				var pm: Dictionary = pm_
				if cen.y < float(pm["bot"]) + 0.35 or cen.y > float(pm["top"]) + 0.60:
					continue
				var span: float = maxf(float(pm["top"]) - float(pm["bot"]), 0.0001)
				var t: float = clampf((float(pm["top"]) - cen.y) / span, 0.0, 1.0)
				var ax: Vector3 = _pitch_axis(pm, t)
				if Vector2(cen.x - ax.x, cen.z - ax.z).length() < float(pm["r"]) * 1.02:
					kill = true
					break
			if kill:
				removed += 1
				continue
			keep.push_back(ix[f * 3]); keep.push_back(ix[f * 3 + 1]); keep.push_back(ix[f * 3 + 2])
		idxs[cls] = keep
	print("pitches: %d bores punched %d triangles out of the floors and crowns" % [pitch_m.size(), removed])


# What is inside a pitch, and it is the one thing that makes a shaft legible to
# a sensor at all. VERTICAL.md 3.4: the ancients' rings where they left steel,
# and a beacon at the head and the foot of everything a machine can descend
# plus a chain every 3.2 m down the main ones. A beacon is RETROREFLECTIVE
# (ART-DIRECTION 8.2), so it clips the intensity channel and blazes from
# anywhere in range -- which means the descent chain draws itself in the
# brightest marks in the machine's own map, with no overlay and no art
# direction. It is the cheapest legibility win available to this shot.
func _place_pitch_props() -> void:
	for pm_ in pitch_m:
		var pm: Dictionary = pm_
		var h: float = float(pm["top"]) - float(pm["bot"])
		if h < 0.6:
			continue
		var k: int = int(pm["kind"])
		var fixed: bool = (int(pm["flags"]) & CaveTopology.PF_FIXED) != 0 \
			or k == CaveTopology.PK_COLLAR or k == CaveTopology.PK_WINZE \
			or k == CaveTopology.PK_ORE_PASS
		var descendable: bool = (int(pm["flags"]) & CaveTopology.PF_DOWN) != 0
		var main: bool = (int(pm["flags"]) & CaveTopology.PF_MAIN) != 0
		if fixed:
			var n_r: int = int(h / 1.2)
			for j in range(1, n_r):
				var t: float = float(j) * 1.2 / h
				var ax: Vector3 = _pitch_axis(pm, t)
				var rr: float = _pitch_radius(pm, t, 0.0) * 0.97
				_ring_hoop(SURF_METAL, Vector3(ax.x, ax.y, ax.z), rr, 0.09, 16)
		if descendable:
			for tb in [0.02, 0.98]:
				var ax2: Vector3 = _pitch_axis(pm, float(tb))
				var rr2: float = _pitch_radius(pm, float(tb), 0.0) * 0.90
				_box(SURF_RETRO, Vector3(0.05, 0.26, 0.26),
					Transform3D(Basis.IDENTITY, Vector3(ax2.x + rr2, ax2.y, ax2.z)))
		if main and descendable:
			var n_b: int = int(h / 3.2)
			for j in range(1, n_b):
				var t3: float = float(j) * 3.2 / h
				var ax3: Vector3 = _pitch_axis(pm, t3)
				var rr3: float = _pitch_radius(pm, t3, PI * 0.5) * 0.90
				_box(SURF_RETRO, Vector3(0.22, 0.22, 0.05),
					Transform3D(Basis.IDENTITY, Vector3(ax3.x, ax3.y, ax3.z + rr3)))


# an open hoop: a short cylindrical band, NOT a CylinderMesh -- a capped
# cylinder of bore radius is a plate across the shaft and the laser would stop
# at the first one.
func _ring_hoop(cls: int, c: Vector3, r: float, hh: float, seg: int) -> void:
	var r0 := PackedVector3Array()
	var r1 := PackedVector3Array()
	for i in range(seg):
		var th: float = float(i) / float(seg) * TAU
		r0.push_back(c + Vector3(cos(th) * r, -hh * 0.5, sin(th) * r))
		r1.push_back(c + Vector3(cos(th) * r, hh * 0.5, sin(th) * r))
	_ring_band(cls, r0, r1, seg)


# ---------------------------------------------------------------------------
func _build_centreline() -> void:
	centre = PackedVector3Array()
	var ids: PackedInt32Array = topo.edges[0]
	for i in range(ids.size()):
		var p: Vector3 = _st_pos(ids[i])
		centre.push_back(Vector3(p.x, p.y, p.z))


func attach(root: Node3D) -> void:
	for cls in range(N_SURF):
		if bodies[cls] != null:
			root.add_child(bodies[cls])
	if cam_body != null:
		root.add_child(cam_body)
