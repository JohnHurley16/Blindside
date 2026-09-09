# ---------------------------------------------------------------------------
# BLINDSIDE assayer spike -- a chamber to stand it in.
#
# MINIMAL AND DELIBERATELY SO. This is not the cave generator; it is enough
# rock to hold a 6.6 m machine, take its light, and give it one passage to be
# seen from. The rock material is the cave spike's, copied with the scour added
# (chamber.gdshader), so what these frames measure is the machine and not a
# second rock look.
#
# THE CHAMBER RULE, ART-DIRECTION 5.5: "a chamber that holds something worth
# seeing must be taller than the passages that reach it", and separately "a
# 6.6 m mast does not fit under a 4.8 m ceiling -- the Assayer's chamber needs
# >= 8 m". Concept proposal 11 asks for radius 10.5 m and a crown at ~11.5 m.
# Both are honoured: the crown is 11.4 m, the drive mouth is 2.4 x 2.4 m, and
# the ratio between them is the free depth cue that section asks for.
#
# THE ONE DECISION THIS FILE MAKES ALONE: the water datum sits at -0.30 m, so
# nothing in the chamber is submerged but everything below about 1.2 m is damp,
# and the parts of the machine below 0.34 m are built in the GRAPHITISED iron
# (ART-DIRECTION 5.2's third age) with a mineral crust band above them. That
# says "the water was here and it has gone down", which is what a drained
# working looks like, without putting a water plane under the machine that
# would contradict the scour's "no puddles".
# ---------------------------------------------------------------------------
class_name Chamber
extends Node3D

const R: float = 10.50
const CROWN: float = 11.40
const DRIVE_W: float = 2.40
const DRIVE_H: float = 2.40
const MOUTH_TH: float = deg_to_rad(196.0)   # the drive leaves on this bearing
const WATER_Y: float = -0.30

# the stope profile: near-vertical walls to 5 m, then it arches over. A dome
# reads as a bubble; a mine chamber is a room somebody drove upward into.
const PROFILE := [
	Vector2(10.50, 0.00), Vector2(10.66, 1.20), Vector2(10.62, 2.30),
	Vector2(10.74, 3.10),
	Vector2(10.10, 5.30), Vector2(8.90, 7.40), Vector2(6.95, 9.30),
	Vector2(4.35, 10.75), Vector2(1.70, 11.30), Vector2(0.00, CROWN),
]

var mats: AssayerMaterials
var noise: FastNoiseLite
var noise_lo: FastNoiseLite
var stat_tris: int = 0
var drive_pts: PackedVector3Array = PackedVector3Array()
var shell_mi: MeshInstance3D

const SEG: int = 68


func build(m: AssayerMaterials, sd: int) -> void:
	mats = m
	noise = FastNoiseLite.new()
	noise.seed = sd
	noise.noise_type = FastNoiseLite.TYPE_SIMPLEX_SMOOTH
	noise.frequency = 0.55
	noise.fractal_octaves = 4
	noise_lo = FastNoiseLite.new()
	noise_lo.seed = sd + 977
	noise_lo.noise_type = FastNoiseLite.TYPE_SIMPLEX_SMOOTH
	noise_lo.frequency = 0.11
	noise_lo.fractal_octaves = 2

	var mb := MeshKit.MB.new()
	_shell(mb)
	_floor(mb)
	_drive(mb)
	var mi := MeshInstance3D.new()
	mi.mesh = mb.commit()
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_DOUBLE_SIDED
	shell_mi = mi
	add_child(mi)
	stat_tris += mb.tri_count()

	_scatter(sd)


# the four scalars the rock material reads, per vertex
func _col(wet: float, worked: float) -> Color:
	return Color(wet, worked, 0.30, 0.05)


func _packed() -> float:
	# FRACTURE 0.12 of the 3..14 range, so the joint set sits at about 1.4 m --
	# a competent, massive ironstone. This was 0.52 and it was wrong: there the
	# cellular joint is at 0.7 m, and a 10 m wall lit by ONE point source 6 m
	# away came back reading as BRICKWORK, because the pattern tiles and a
	# point source shows the whole tile at once. In the cave spike the same
	# number is right, because nothing there is ever lit at that range by
	# anything but a 27-degree spot. BEDDING 0.34. UV2.y packs both.
	return floor(0.12 * 31.0) * 32.0 + floor(0.34 * 31.0)


# MEASURED, and it was a bug rather than a matter of taste: the first gains
# summed to +-2.54 before the 0.62 amplitude, so the shell wandered by up to
# 1.57 m on a 10.5 m chamber -- enough to swing solid rock across a 2.4 m drive
# mouth and plug it. That is why the passage frame came back 100% black twice.
# The gains now sum to +-1.41 before amplitude, and `fade` takes the
# displacement to zero across the mouth so an aperture stays an aperture.
func _disp(p: Vector3, outv: Vector3, amt: float, fade: float = 1.0) -> Vector3:
	var a: float = noise_lo.get_noise_3d(p.x, p.y * 1.4, p.z)
	var b: float = noise.get_noise_3d(p.x * 2.0, p.y * 2.0, p.z * 2.0)
	var c: float = noise.get_noise_3d(p.x * 5.5, p.y * 5.5, p.z * 5.5)
	return p + outv * (a * 0.85 + b * 0.40 + c * 0.16) * amt * fade


# --- the shell -------------------------------------------------------------
# One aperture is cut in it, by simply not emitting the quads the drive mouth
# occupies. That is the whole technique: a hole in a generated shell is a
# missing quad, and the drive's own tube covers the gap.
func _shell(mb: MeshKit.MB) -> void:
	var pk: float = _packed()
	var half: float = atan(DRIVE_W * 0.62 / R)
	var rows: Array = []
	for a in range(PROFILE.size()):
		var row: Array = []
		for b in range(SEG):
			var th: float = TAU * float(b) / float(SEG)
			var rr: float = PROFILE[a].x
			var yy: float = PROFILE[a].y
			var p := Vector3(cos(th) * rr, yy, sin(th) * rr)
			var outv := Vector3(cos(th) * 0.86, 0.5 if a >= PROFILE.size() - 3 else 0.10, sin(th) * 0.86).normalized()
			var dth0: float = absf(atan2(sin(th - MOUTH_TH), cos(th - MOUTH_TH)))
			var fade: float = smoothstep(half * 1.05, half * 3.2, dth0)
			if a > 0:
				p = _disp(p, outv, 0.62, fade)
			row.append(p)
		rows.append(row)
	for a in range(PROFILE.size() - 1):
		for b in range(SEG):
			var b2: int = (b + 1) % SEG
			var th: float = TAU * (float(b) + 0.5) / float(SEG)
			# the mouth: skip the quads it occupies
			var dth: float = absf(atan2(sin(th - MOUTH_TH), cos(th - MOUTH_TH)))
			if dth < half and PROFILE[a].y < DRIVE_H - 0.09:
				continue
			var q0: Vector3 = rows[a][b]
			var q1: Vector3 = rows[a][b2]
			var q2: Vector3 = rows[a + 1][b]
			var q3: Vector3 = rows[a + 1][b2]
			_quad(mb, q0, q1, q2, q3, Vector3(0, PROFILE[a].y + 1.0, 0), pk,
				_col(0.55 - PROFILE[a].y * 0.030, 0.30))


# --- the floor -------------------------------------------------------------
# A tessellated disc with a shallow dish, so the parallax field in the rock
# material has something to sit on and the scour has somewhere to be. UV2.x is
# the signed lateral offset the material reads for tram ruts; the chamber has
# no track, so it is parked far enough out that the rut term is exactly zero.
func _floor(mb: MeshKit.MB) -> void:
	var pk: float = _packed()
	var N: int = 44
	var step: float = (R * 2.04) / float(N)
	var v := PackedVector3Array()
	var n := PackedVector3Array()
	var c := PackedColorArray()
	var u := PackedVector2Array()
	var u2 := PackedVector2Array()
	var idx := PackedInt32Array()
	for i in range(N + 1):
		for j in range(N + 1):
			var x: float = -R * 1.02 + step * float(i)
			var z: float = -R * 1.02 + step * float(j)
			var d: float = sqrt(x * x + z * z)
			# A shallow dish. It does NOT rise to meet the wall any more, and
			# that rise is the single most expensive bug in this spike: a
			# 22 x 22 m plate lifted 0.55 m outside r = 11.1 m put a step of
			# rock across the drive mouth and roofed the passage over. The
			# machinery's light then reached the drive at 0.00000 mean
			# luminance and it read as a shadow-bias problem for four sweeps,
			# because the plate only blocks when shadows are on. The shell's
			# own row 0 is undisplaced at exactly r = R, y = 0, so the floor
			# meets the wall by construction and needs no ramp at all.
			var y: float = -0.055 * (1.0 - clampf(d / R, 0.0, 1.0))
			y += noise_lo.get_noise_3d(x * 0.7, 40.0, z * 0.7) * 0.16
			v.push_back(Vector3(x, y, z))
			n.push_back(Vector3.UP)
			c.push_back(_col(0.52, 0.22))
			u.push_back(Vector2(x, 0.0))
			u2.push_back(Vector2(6.0, pk))
	for i in range(N):
		for j in range(N):
			var a: int = i * (N + 1) + j
			var b: int = a + 1
			var c2: int = a + (N + 1)
			var d2: int = c2 + 1
			# and the plate stops AT the wall: no quad any of whose corners is
			# outside the chamber is emitted at all.
			var out: bool = false
			for q in [a, b, c2, d2]:
				var pv: Vector3 = v[q]
				if pv.x * pv.x + pv.z * pv.z > R * R * 1.004:
					out = true
			if out:
				continue
			idx.append_array([a, b, c2, b, d2, c2])
	# the naive winding above points the cross product UP, and Godot's front
	# face wants it pointing the other way (see mb.gd), so flip.
	for k in range(0, idx.size(), 3):
		var t: int = idx[k + 1]
		idx[k + 1] = idx[k + 2]
		idx[k + 2] = t
	mb.add_arrays(mats.rock, v, n, c, u, u2, idx, Transform3D.IDENTITY)


# --- the drive -------------------------------------------------------------
# A horseshoe section swept along a dog-leg, so there is a corner for the
# machine's light to come round without the mast being visible (the frame
# ART-DIRECTION 5.5 says is the ONLY way vertical landmark presence is bought).
func _drive(mb: MeshKit.MB) -> void:
	var pk: float = _packed()
	# THE DRIVE STARTS AT THE WALL, and this took three black frames to find.
	# The first build began the tube 2.4 m INSIDE the chamber so that it would
	# certainly cover the aperture. What that actually does is put an opaque
	# barrel between the machine and the mouth: every ray from the winch head
	# toward the drive lands on the OUTSIDE of the tube, and the only way in is
	# the tube's own open end, which faces along the axis, so what little light
	# enters does so at grazing incidence and the passage renders at literally
	# 0.00000 mean luminance. A tunnel mouth has to BE the hole in the wall.
	var dirv := Vector3(cos(MOUTH_TH), 0, sin(MOUTH_TH))
	var start: Vector3 = dirv * R
	# MEASURED. The winch head is 6.30 m up and the mouth is 2.40 m tall at
	# 10.5 m, so the ray from the head through the top of the mouth meets the
	# drive floor about 6 m past it and there is nothing lit beyond that. The
	# first pass put the bend 6.2 m out AND started the drive 1.6 m inside the
	# chamber, so the corner sat 15.9 m from the machine in the dark and the
	# frame ART-DIRECTION 5.5 exists to prove came back 100% black. The bend
	# goes where the light lands: 3.4 m out, and it turns 62 degrees so that
	# three metres past it the mast is behind solid rock.
	# and the bend goes 5.4 m out: far enough that three metres past it the
	# 6.6 m mast is behind solid rock (the sight line through a 2.4 m arch from
	# an eye at 0.42 m clears the mast top only inside about 5 m of the mouth),
	# and near enough to sit inside the winch head's own throw, which reaches
	# about 6.5 m past the mouth before its ray meets the floor.
	var bend: Vector3 = start + dirv * 5.40
	var d2: Vector3 = dirv.rotated(Vector3.UP, deg_to_rad(62.0))
	var end: Vector3 = bend + d2 * 11.20
	# a rounded corner, because a drive is driven in rounds and turned in arcs
	drive_pts = PackedVector3Array()
	drive_pts.push_back(start - dirv * 0.55)
	var nseg: int = 46
	for i in range(nseg + 1):
		var t: float = float(i) / float(nseg)
		var p: Vector3
		if t < 0.26:
			p = start.lerp(bend - dirv * 1.5, t / 0.26)
		elif t < 0.42:
			var u: float = (t - 0.26) / 0.16
			var a: Vector3 = bend - dirv * 1.5
			var b: Vector3 = bend
			var c3: Vector3 = bend + d2 * 1.5
			p = a.lerp(b, u).lerp(b.lerp(c3, u), u)
		else:
			p = (bend + d2 * 1.5).lerp(end, (t - 0.42) / 0.58)
		drive_pts.push_back(p)
	# the horseshoe: a flat floor, two walls, an arch
	var prof: Array = []
	var NP: int = 15
	for k in range(NP):
		var f: float = float(k) / float(NP - 1)
		var lat: float
		var hh: float
		if f < 0.14:
			lat = lerp(-DRIVE_W * 0.5, -DRIVE_W * 0.5, f / 0.14)
			hh = lerp(0.0, 1.20, f / 0.14)
		elif f < 0.86:
			var a2: float = PI * (1.0 - (f - 0.14) / 0.72)
			lat = cos(a2) * DRIVE_W * 0.5
			hh = 1.20 + sin(a2) * (DRIVE_H - 1.20)
		else:
			lat = DRIVE_W * 0.5
			hh = lerp(1.20, 0.0, (f - 0.86) / 0.14)
		prof.append(Vector2(lat, hh))
	var rows: Array = []
	for i in range(drive_pts.size()):
		var p: Vector3 = drive_pts[i]
		var j: int = mini(i + 1, drive_pts.size() - 1)
		var k2: int = maxi(i - 1, 0)
		var tan: Vector3 = (drive_pts[j] - drive_pts[k2]).normalized()
		var right: Vector3 = tan.cross(Vector3.UP).normalized()
		var row: Array = []
		for q in prof:
			var pp: Vector3 = p + right * q.x + Vector3.UP * q.y
			var outv: Vector3 = (right * q.x + Vector3.UP * (q.y - 0.6)).normalized()
			row.append(_disp(pp, outv, 0.20))
		rows.append(row)
	for i in range(rows.size() - 1):
		for k in range(prof.size() - 1):
			var ctr: Vector3 = drive_pts[i] + Vector3.UP * 1.0
			_quad(mb, rows[i][k], rows[i][k + 1], rows[i + 1][k], rows[i + 1][k + 1],
				ctr, pk, _col(0.62, 0.62))
	# the drive floor, a strip between the two toes
	for i in range(rows.size() - 1):
		var a: Vector3 = rows[i][0]
		var b: Vector3 = rows[i][prof.size() - 1]
		var c3: Vector3 = rows[i + 1][0]
		var d3: Vector3 = rows[i + 1][prof.size() - 1]
		_quad(mb, a, b, c3, d3, (a + b) * 0.5 + Vector3.UP * 2.0, pk, _col(0.48, 0.55))


# one inward-facing quad, normals recomputed and pointed at `ctr`
func _quad(mb: MeshKit.MB, q0: Vector3, q1: Vector3, q2: Vector3, q3: Vector3,
		   ctr: Vector3, pk: float, col: Color) -> void:
	var v := PackedVector3Array([q0, q1, q2, q3])
	var idx := PackedInt32Array([0, 2, 1, 1, 2, 3])
	var n: PackedVector3Array = MeshKit.recalc_normals(v, idx)
	for w in range(4):
		if n[w].dot(ctr - v[w]) < 0.0:
			n[w] = -n[w]
	var c := PackedColorArray()
	var u := PackedVector2Array()
	var u2 := PackedVector2Array()
	for w in range(4):
		c.push_back(col)
		u.push_back(Vector2(v[w].x + v[w].z, 0.5))
		u2.push_back(Vector2(6.0, pk))
	mb.add_arrays(mats.rock, v, n, c, u, u2, idx, Transform3D.IDENTITY)


# --- what is loose on the floor --------------------------------------------
# DESIGN-PRINCIPLES 7: every object answers who put it there and why. There are
# exactly three answers in this room and no fourth:
#   1. ANGULAR SPALL inside the scour -- the machine shook it off the walls.
#   2. ROUNDED RUBBLE outside it -- everything that has fallen in a century and
#      then been rounded by water and silt.
#   3. ONE MUCK PILE against the far wall -- broken stock left where the survey
#      said to dig (THE-MACHINERY 7), in a heap because a heap is what a mucking
#      shovel leaves. It is the only ordered thing in the room and it is ordered.
func _scatter(sd: int) -> void:
	var lr := RandomNumberGenerator.new()
	lr.seed = sd * 7717 + 13
	var meshes: Array = []
	for i in range(5):
		meshes.append(_stone(101 + i + sd * 13, 0.055 + i * 0.048, 0.62))
	var xf_by_mesh: Array = [[], [], [], [], []]
	for i in range(360):
		var th: float = lr.randf() * TAU
		var rr: float = sqrt(lr.randf()) * (R - 0.6)
		var p := Vector3(cos(th) * rr, 0.0, sin(th) * rr)
		# the scour: nothing settles inside 9 cells except what the machine
		# itself has just broken off, so the count falls and the size falls
		var inside: bool = rr < 5.40 + (lr.randf() - 0.5) * 1.4
		if inside and lr.randf() > 0.24:
			continue
		if rr < 2.4:
			continue
		var k: int = lr.randi_range(0, 1) if inside else lr.randi_range(0, 4)
		var s: float = (0.45 + lr.randf() * 0.45) if inside else (0.5 + lr.randf() * 1.25)
		xf_by_mesh[k].append(Transform3D(
			Basis.from_euler(Vector3(lr.randf() * 0.5 - 0.25, lr.randf() * TAU,
				lr.randf() * 0.5 - 0.25)).scaled(Vector3(s, s * 0.8, s)),
			p + Vector3(0, -0.02, 0)))
	# the muck pile: a heap, not a scatter
	var pile := Vector3(cos(2.55) * 8.10, 0.0, sin(2.55) * 8.10)
	for i in range(170):
		var a: float = lr.randf() * TAU
		var rr2: float = sqrt(lr.randf()) * 2.10
		var h: float = (1.0 - rr2 / 2.10) * 0.92
		var k2: int = lr.randi_range(1, 4)
		var s2: float = 0.7 + lr.randf() * 0.7
		xf_by_mesh[k2].append(Transform3D(
			Basis.from_euler(Vector3(lr.randf() * TAU, lr.randf() * TAU, lr.randf() * TAU))
				.scaled(Vector3(s2, s2, s2)),
			pile + Vector3(cos(a) * rr2, h * lr.randf(), sin(a) * rr2)))
	for k3 in range(meshes.size()):
		var arr: Array = xf_by_mesh[k3]
		if arr.is_empty():
			continue
		var mm := MultiMesh.new()
		mm.transform_format = MultiMesh.TRANSFORM_3D
		mm.mesh = meshes[k3]
		mm.instance_count = arr.size()
		for i2 in range(arr.size()):
			mm.set_instance_transform(i2, arr[i2])
		var mi := MultiMeshInstance3D.new()
		mi.multimesh = mm
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
		add_child(mi)
		stat_tris += (meshes[k3] as ArrayMesh).surface_get_array_index_len(0) / 3 * arr.size()


# an angular stone: a sphere whose directions are quantised so it has flats.
# Copied from the cave spike's `_stone_mesh`, including its outward-normal fix.
func _stone(sd: int, r: float, flat: float) -> ArrayMesh:
	var lr := RandomNumberGenerator.new()
	lr.seed = sd
	var s: SphereMesh = MeshKit.sph(r, 7)
	var a: Array = s.get_mesh_arrays()
	var v: PackedVector3Array = a[Mesh.ARRAY_VERTEX]
	for i in range(v.size()):
		var d: Vector3 = v[i].normalized()
		var q := Vector3(round(d.x * 2.0) / 2.0, round(d.y * 2.0) / 2.0, round(d.z * 2.0) / 2.0)
		d = d.lerp(q.normalized() if q.length() > 0.01 else d, 0.55)
		var k: float = r * (0.62 + lr.randf() * 0.55)
		v[i] = Vector3(d.x * k, d.y * k * flat, d.z * k)
	var sn: PackedVector3Array = MeshKit.recalc_normals(v, a[Mesh.ARRAY_INDEX])
	for i in range(sn.size()):
		if sn[i].dot(v[i]) < 0.0:
			sn[i] = -sn[i]
	var col := PackedColorArray()
	col.resize(v.size())
	col.fill(AssayerMaterials.C_STONE)
	var am := ArrayMesh.new()
	var arr := []
	arr.resize(Mesh.ARRAY_MAX)
	arr[Mesh.ARRAY_VERTEX] = v
	arr[Mesh.ARRAY_NORMAL] = sn
	arr[Mesh.ARRAY_COLOR] = col
	arr[Mesh.ARRAY_INDEX] = a[Mesh.ARRAY_INDEX]
	am.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arr)
	am.surface_set_material(0, mats.stone)
	return am
