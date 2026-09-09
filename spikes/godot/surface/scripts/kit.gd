extends RefCounted
class_name Kit
##
## DRESSING LAYER - the kit of parts.
##
## A dozen unit meshes, built once in code, flat shaded. Everything on the site
## is one of these under a transform, which is the whole reason the site fits in
## a handful of draw calls: one MultiMesh per (mesh, material) pair.
##
## Every mesh is unit sized and centred on its own origin unless the comment says
## otherwise, so an instance transform is (position, basis = size * rotation).

static var _cache: Dictionary = {}

static func get_mesh(id: String) -> ArrayMesh:
	if _cache.has(id):
		return _cache[id]
	var m: ArrayMesh = _build(id)
	_cache[id] = m
	return m

static func _build(id: String) -> ArrayMesh:
	match id:
		"box": return _box()
		"casebox": return _casebox(0.10)
		"ibeam": return _ibeam()
		"angle": return _angle()
		"channel": return _channel()
		"cyl": return _cyl(12, true)
		"cyl6": return _cyl(6, true)
		"tube": return _cyl(10, false)
		"hex": return _hex()
		"rock": return _rock(0)
		"rock2": return _rock(7)
		"rock3": return _rock(19)
		"chip": return _chip()
		"wheel": return _wheel()
		"ring": return _ring(0.42, 12)
		"cone": return _cone(10)
		"quad": return _quad()
		"grate": return _grate(9)
		"ladder": return _ladder(7)
		"weed": return _weed(5)
		"dish": return _dish(12)
		"drum": return _drum()
		"pallet": return _pallet()
		"bollard": return _bollard()
		"tri": return _tri()
	push_error("Kit: unknown mesh " + id)
	return _box()

# ------------------------------------------------------------------ builder
class B extends RefCounted:
	var v := PackedVector3Array()
	var n := PackedVector3Array()
	var uv := PackedVector2Array()
	func tri(a: Vector3, b: Vector3, c: Vector3) -> void:
		var nm := (b - a).cross(c - a)
		if nm.length_squared() < 1e-16:
			return
		nm = nm.normalized()
		v.push_back(a); v.push_back(b); v.push_back(c)
		n.push_back(nm); n.push_back(nm); n.push_back(nm)
		uv.push_back(Vector2(a.x + a.z, -a.y))
		uv.push_back(Vector2(b.x + b.z, -b.y))
		uv.push_back(Vector2(c.x + c.z, -c.y))
	func quad(a: Vector3, b: Vector3, c: Vector3, d: Vector3) -> void:
		tri(a, b, c); tri(a, c, d)
	## a prism: polygon `poly` in XZ, extruded along Y from y0 to y1
	func prism(poly: PackedVector2Array, y0: float, y1: float, caps: bool = true) -> void:
		var cnt := poly.size()
		for i in cnt:
			var p := poly[i]
			var q := poly[(i + 1) % cnt]
			quad(Vector3(p.x, y0, p.y), Vector3(q.x, y0, q.y),
				Vector3(q.x, y1, q.y), Vector3(p.x, y1, p.y))
		if caps:
			for i in range(1, cnt - 1):
				tri(Vector3(poly[0].x, y1, poly[0].y), Vector3(poly[i].x, y1, poly[i].y),
					Vector3(poly[i + 1].x, y1, poly[i + 1].y))
				tri(Vector3(poly[0].x, y0, poly[0].y), Vector3(poly[i + 1].x, y0, poly[i + 1].y),
					Vector3(poly[i].x, y0, poly[i].y))
	func mesh() -> ArrayMesh:
		var arr := []
		arr.resize(Mesh.ARRAY_MAX)
		arr[Mesh.ARRAY_VERTEX] = v
		arr[Mesh.ARRAY_NORMAL] = n
		arr[Mesh.ARRAY_TEX_UV] = uv
		var am := ArrayMesh.new()
		am.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arr)
		return am

static func _b() -> B:
	return B.new()

# ------------------------------------------------------------------ parts
static func _box() -> ArrayMesh:
	var b := _b()
	var p := PackedVector2Array([Vector2(-0.5, -0.5), Vector2(0.5, -0.5),
		Vector2(0.5, 0.5), Vector2(-0.5, 0.5)])
	b.prism(p, -0.5, 0.5)
	return b.mesh()

## chamfered box - the BROUGHT register's signature. Clean edges catch light.
static func _casebox(c: float) -> ArrayMesh:
	var b := _b()
	var h := 0.5
	var i := h - c
	var pts := PackedVector2Array([
		Vector2(-i, -h), Vector2(i, -h), Vector2(h, -i), Vector2(h, i),
		Vector2(i, h), Vector2(-i, h), Vector2(-h, i), Vector2(-h, -i)])
	b.prism(pts, -i, i, false)
	# top and bottom chamfered caps
	for s in [1.0, -1.0]:
		var y0: float = i * s
		var y1: float = h * s
		var cnt := pts.size()
		for k in cnt:
			var p0 := pts[k]
			var p1 := pts[(k + 1) % cnt]
			var q0 := p0 * (1.0 - c * 2.0)
			var q1 := p1 * (1.0 - c * 2.0)
			if s > 0.0:
				b.quad(Vector3(p0.x, y0, p0.y), Vector3(p1.x, y0, p1.y),
					Vector3(q1.x, y1, q1.y), Vector3(q0.x, y1, q0.y))
			else:
				b.quad(Vector3(q0.x, y1, q0.y), Vector3(q1.x, y1, q1.y),
					Vector3(p1.x, y0, p1.y), Vector3(p0.x, y0, p0.y))
		var inner := PackedVector2Array()
		for k in cnt:
			inner.push_back(pts[k] * (1.0 - c * 2.0))
		if s > 0.0:
			for k in range(1, cnt - 1):
				b.tri(Vector3(inner[0].x, y1, inner[0].y), Vector3(inner[k].x, y1, inner[k].y),
					Vector3(inner[k + 1].x, y1, inner[k + 1].y))
		else:
			for k in range(1, cnt - 1):
				b.tri(Vector3(inner[0].x, y1, inner[0].y), Vector3(inner[k + 1].x, y1, inner[k + 1].y),
					Vector3(inner[k].x, y1, inner[k].y))
	return b.mesh()

## I-section, 1 x 1 x 1, web along Y. Reads as structure instead of a stick.
static func _ibeam() -> ArrayMesh:
	var b := _b()
	var fw := 0.5      # half flange width  (X)
	var ft := 0.11     # flange thickness   (Z)
	var wt := 0.09     # half web thickness (X)
	var d := 0.5       # half depth         (Z)
	var p := PackedVector2Array([
		Vector2(-fw, -d), Vector2(fw, -d), Vector2(fw, -d + ft), Vector2(wt, -d + ft),
		Vector2(wt, d - ft), Vector2(fw, d - ft), Vector2(fw, d), Vector2(-fw, d),
		Vector2(-fw, d - ft), Vector2(-wt, d - ft), Vector2(-wt, -d + ft), Vector2(-fw, -d + ft)])
	b.prism(p, -0.5, 0.5)
	return b.mesh()

static func _angle() -> ArrayMesh:
	var b := _b()
	var t := 0.16
	var p := PackedVector2Array([
		Vector2(-0.5, -0.5), Vector2(0.5, -0.5), Vector2(0.5, -0.5 + t),
		Vector2(-0.5 + t, -0.5 + t), Vector2(-0.5 + t, 0.5), Vector2(-0.5, 0.5)])
	b.prism(p, -0.5, 0.5)
	return b.mesh()

static func _channel() -> ArrayMesh:
	var b := _b()
	var t := 0.14
	var p := PackedVector2Array([
		Vector2(-0.5, -0.5), Vector2(0.5, -0.5), Vector2(0.5, 0.5), Vector2(0.5 - t, 0.5),
		Vector2(0.5 - t, -0.5 + t), Vector2(-0.5 + t, -0.5 + t), Vector2(-0.5 + t, 0.5),
		Vector2(-0.5, 0.5)])
	b.prism(p, -0.5, 0.5)
	return b.mesh()

static func _poly_circle(n: int, r: float, phase: float = 0.0) -> PackedVector2Array:
	var p := PackedVector2Array()
	for i in n:
		var a := TAU * (float(i) / float(n)) + phase
		p.push_back(Vector2(cos(a) * r, sin(a) * r))
	return p

static func _cyl(n: int, caps: bool) -> ArrayMesh:
	var b := _b()
	b.prism(_poly_circle(n, 0.5), -0.5, 0.5, caps)
	return b.mesh()

static func _hex() -> ArrayMesh:
	var b := _b()
	b.prism(_poly_circle(6, 0.5), -0.5, 0.35)
	# a shallow dome on top, so a bolt head is not a flat disc at 0.3 m
	var p := _poly_circle(6, 0.5)
	for i in 6:
		b.tri(Vector3(p[i].x, 0.35, p[i].y), Vector3(p[(i + 1) % 6].x, 0.35, p[(i + 1) % 6].y),
			Vector3(0, 0.5, 0))
	return b.mesh()

static func _bollard() -> ArrayMesh:
	var b := _b()
	b.prism(_poly_circle(8, 0.5), -0.5, 0.42)
	var p := _poly_circle(8, 0.5)
	var q := _poly_circle(8, 0.34)
	for i in 8:
		b.quad(Vector3(p[i].x, 0.42, p[i].y), Vector3(p[(i + 1) % 8].x, 0.42, p[(i + 1) % 8].y),
			Vector3(q[(i + 1) % 8].x, 0.5, q[(i + 1) % 8].y), Vector3(q[i].x, 0.5, q[i].y))
	for i in range(1, 7):
		b.tri(Vector3(q[0].x, 0.5, q[0].y), Vector3(q[i].x, 0.5, q[i].y), Vector3(q[i + 1].x, 0.5, q[i + 1].y))
	return b.mesh()

## a 205 litre drum: ribbed, which is the read at 3 m
static func _drum() -> ArrayMesh:
	var b := _b()
	var n := 10
	var ys := [-0.5, -0.44, -0.16, -0.10, 0.10, 0.16, 0.44, 0.5]
	var rs := [0.46, 0.50, 0.50, 0.46, 0.46, 0.50, 0.50, 0.46]
	for k in range(ys.size() - 1):
		var p0 := _poly_circle(n, rs[k])
		var p1 := _poly_circle(n, rs[k + 1])
		for i in n:
			b.quad(Vector3(p0[i].x, ys[k], p0[i].y), Vector3(p0[(i + 1) % n].x, ys[k], p0[(i + 1) % n].y),
				Vector3(p1[(i + 1) % n].x, ys[k + 1], p1[(i + 1) % n].y), Vector3(p1[i].x, ys[k + 1], p1[i].y))
	var cap := _poly_circle(n, 0.46)
	for i in range(1, n - 1):
		b.tri(Vector3(cap[0].x, 0.5, cap[0].y), Vector3(cap[i].x, 0.5, cap[i].y), Vector3(cap[i + 1].x, 0.5, cap[i + 1].y))
		b.tri(Vector3(cap[0].x, -0.5, cap[0].y), Vector3(cap[i + 1].x, -0.5, cap[i + 1].y), Vector3(cap[i].x, -0.5, cap[i].y))
	return b.mesh()

static func _pallet() -> ArrayMesh:
	var b := _b()
	for i in 3:
		var x := -0.5 + 0.5 * float(i)
		_slab(b, Vector3(x + 0.0833, -0.25, 0.0), Vector3(0.166, 0.5, 1.0))
	for i in 5:
		var z := -0.5 + 0.25 * float(i)
		_slab(b, Vector3(0.0, 0.4, z + 0.05), Vector3(1.0, 0.2, 0.10))
	return b.mesh()

static func _slab(b: B, c: Vector3, s: Vector3) -> void:
	var p := PackedVector2Array([
		Vector2(c.x - s.x * 0.5, c.z - s.z * 0.5), Vector2(c.x + s.x * 0.5, c.z - s.z * 0.5),
		Vector2(c.x + s.x * 0.5, c.z + s.z * 0.5), Vector2(c.x - s.x * 0.5, c.z + s.z * 0.5)])
	b.prism(p, c.y - s.y * 0.5, c.y + s.y * 0.5)

## sheave / flywheel / cable drum: rim, spokes, hub. Axis is Z.
static func _wheel() -> ArrayMesh:
	var b := _b()
	var n := 16
	var t := 0.07
	var outer := _poly_circle(n, 0.5)
	var inner := _poly_circle(n, 0.40)
	for i in n:
		var j := (i + 1) % n
		# rim outer face, grooved
		b.quad(Vector3(outer[i].x, outer[i].y, -t), Vector3(outer[j].x, outer[j].y, -t),
			Vector3(outer[j].x * 0.94, outer[j].y * 0.94, 0.0), Vector3(outer[i].x * 0.94, outer[i].y * 0.94, 0.0))
		b.quad(Vector3(outer[i].x * 0.94, outer[i].y * 0.94, 0.0), Vector3(outer[j].x * 0.94, outer[j].y * 0.94, 0.0),
			Vector3(outer[j].x, outer[j].y, t), Vector3(outer[i].x, outer[i].y, t))
		for s in [-t, t]:
			b.quad(Vector3(outer[i].x, outer[i].y, s), Vector3(inner[i].x, inner[i].y, s),
				Vector3(inner[j].x, inner[j].y, s), Vector3(outer[j].x, outer[j].y, s))
		b.quad(Vector3(inner[j].x, inner[j].y, -t), Vector3(inner[i].x, inner[i].y, -t),
			Vector3(inner[i].x, inner[i].y, t), Vector3(inner[j].x, inner[j].y, t))
	for k in 6:
		var a := TAU * float(k) / 6.0
		var dx := cos(a)
		var dy := sin(a)
		var w := 0.035
		var px := -dy * w
		var py := dx * w
		for s2 in [-0.035, 0.035]:
			b.quad(Vector3(dx * 0.10 + px, dy * 0.10 + py, s2), Vector3(dx * 0.42 + px, dy * 0.42 + py, s2),
				Vector3(dx * 0.42 - px, dy * 0.42 - py, s2), Vector3(dx * 0.10 - px, dy * 0.10 - py, s2))
	var hub := _poly_circle(10, 0.12)
	for i in 10:
		var j2 := (i + 1) % 10
		b.quad(Vector3(hub[i].x, hub[i].y, -0.10), Vector3(hub[j2].x, hub[j2].y, -0.10),
			Vector3(hub[j2].x, hub[j2].y, 0.10), Vector3(hub[i].x, hub[i].y, 0.10))
	return b.mesh()

## flat ring in XZ - the collar casting, manhole rings, tank bands
static func _ring(inner_r: float, n: int) -> ArrayMesh:
	var b := _b()
	var o := _poly_circle(n, 0.5)
	var i2 := _poly_circle(n, inner_r)
	for i in n:
		var j := (i + 1) % n
		b.quad(Vector3(o[i].x, 0.5, o[i].y), Vector3(o[j].x, 0.5, o[j].y),
			Vector3(i2[j].x, 0.5, i2[j].y), Vector3(i2[i].x, 0.5, i2[i].y))
		b.quad(Vector3(i2[i].x, -0.5, i2[i].y), Vector3(i2[j].x, -0.5, i2[j].y),
			Vector3(o[j].x, -0.5, o[j].y), Vector3(o[i].x, -0.5, o[i].y))
		b.quad(Vector3(o[i].x, -0.5, o[i].y), Vector3(o[j].x, -0.5, o[j].y),
			Vector3(o[j].x, 0.5, o[j].y), Vector3(o[i].x, 0.5, o[i].y))
		b.quad(Vector3(i2[j].x, -0.5, i2[j].y), Vector3(i2[i].x, -0.5, i2[i].y),
			Vector3(i2[i].x, 0.5, i2[i].y), Vector3(i2[j].x, 0.5, i2[j].y))
	return b.mesh()

static func _cone(n: int) -> ArrayMesh:
	var b := _b()
	var p := _poly_circle(n, 0.5)
	for i in n:
		var j := (i + 1) % n
		b.tri(Vector3(p[i].x, -0.5, p[i].y), Vector3(p[j].x, -0.5, p[j].y), Vector3(0, 0.5, 0))
		if i > 0 and i < n - 1:
			b.tri(Vector3(p[0].x, -0.5, p[0].y), Vector3(p[i + 1].x, -0.5, p[i + 1].y), Vector3(p[i].x, -0.5, p[i].y))
	return b.mesh()

static func _quad() -> ArrayMesh:
	var b := _b()
	b.quad(Vector3(-0.5, 0, -0.5), Vector3(0.5, 0, -0.5), Vector3(0.5, 0, 0.5), Vector3(-0.5, 0, 0.5))
	return b.mesh()

static func _tri() -> ArrayMesh:
	var b := _b()
	b.tri(Vector3(-0.5, 0, -0.5), Vector3(0.5, 0, -0.5), Vector3(0.0, 0, 0.5))
	return b.mesh()

## open-mesh walkway grating, 1 x 1 in XZ. Bars, not a plate: it silhouettes.
static func _grate(n: int) -> ArrayMesh:
	var b := _b()
	_slab(b, Vector3(0, 0, -0.48), Vector3(1.0, 0.10, 0.04))
	_slab(b, Vector3(0, 0, 0.48), Vector3(1.0, 0.10, 0.04))
	for i in n:
		var x := -0.5 + (float(i) + 0.5) / float(n)
		_slab(b, Vector3(x, 0, 0), Vector3(0.028, 0.09, 0.94))
	for i in 3:
		var z := -0.4 + 0.4 * float(i)
		_slab(b, Vector3(0, -0.02, z), Vector3(0.98, 0.02, 0.02))
	return b.mesh()

static func _ladder(rungs: int) -> ArrayMesh:
	var b := _b()
	_slab(b, Vector3(-0.45, 0, 0), Vector3(0.08, 1.0, 0.05))
	_slab(b, Vector3(0.45, 0, 0), Vector3(0.08, 1.0, 0.05))
	for i in rungs:
		var y := -0.5 + (float(i) + 0.5) / float(rungs)
		_slab(b, Vector3(0, y, 0), Vector3(0.9, 0.035, 0.035))
	return b.mesh()

## a tuft of blades. No alpha, no transparency - solid tapered triangles.
static func _weed(blades: int) -> ArrayMesh:
	var b := _b()
	for i in blades:
		var a := TAU * (float(i) / float(blades)) + 0.7
		var lean := 0.30 + 0.22 * float((i * 7) % 5) / 5.0
		var hgt := 0.55 + 0.45 * float((i * 3) % 4) / 4.0
		var dx := cos(a)
		var dz := sin(a)
		var w := 0.045
		var base := Vector3(dx * 0.02, -0.5, dz * 0.02)
		var mid := Vector3(dx * lean * 0.5, -0.5 + hgt * 0.6, dz * lean * 0.5)
		var tip := Vector3(dx * lean, -0.5 + hgt, dz * lean)
		var px := -dz * w
		var pz := dx * w
		b.tri(base + Vector3(px, 0, pz), base - Vector3(px, 0, pz), mid + Vector3(px * 0.6, 0, pz * 0.6))
		b.tri(base - Vector3(px, 0, pz), mid - Vector3(px * 0.6, 0, pz * 0.6), mid + Vector3(px * 0.6, 0, pz * 0.6))
		b.tri(mid + Vector3(px * 0.6, 0, pz * 0.6), mid - Vector3(px * 0.6, 0, pz * 0.6), tip)
	return b.mesh()

static func _dish(n: int) -> ArrayMesh:
	var b := _b()
	for ring in 4:
		var r0 := 0.5 * float(ring) / 4.0
		var r1 := 0.5 * float(ring + 1) / 4.0
		var y0 := -0.5 + r0 * r0 * 1.4
		var y1 := -0.5 + r1 * r1 * 1.4
		var p0 := _poly_circle(n, r0)
		var p1 := _poly_circle(n, r1)
		for i in n:
			var j := (i + 1) % n
			if ring == 0:
				b.tri(Vector3(0, y0, 0), Vector3(p1[j].x, y1, p1[j].y), Vector3(p1[i].x, y1, p1[i].y))
			else:
				b.quad(Vector3(p0[i].x, y0, p0[i].y), Vector3(p1[i].x, y1, p1[i].y),
					Vector3(p1[j].x, y1, p1[j].y), Vector3(p0[j].x, y0, p0[j].y))
	return b.mesh()

## irregular blobs for gravel, spoil lumps and chippings
static func _rock(salt: int) -> ArrayMesh:
	var b := _b()
	var n := 8
	var rows := 4
	var pts: Array = []
	for r in range(rows + 1):
		var row := PackedVector3Array()
		var phi := PI * float(r) / float(rows)
		for i in n:
			var th := TAU * float(i) / float(n)
			var k := (i * 7 + r * 13 + salt * 31) % 17
			var rad := 0.34 + 0.16 * float(k) / 17.0
			row.push_back(Vector3(sin(phi) * cos(th) * rad, cos(phi) * rad * 0.72, sin(phi) * sin(th) * rad))
		pts.append(row)
	for r in range(rows):
		var a: PackedVector3Array = pts[r]
		var c: PackedVector3Array = pts[r + 1]
		for i in n:
			var j := (i + 1) % n
			b.quad(a[i], a[j], c[j], c[i])
	return b.mesh()

## a flat angular chipping - the thing underfoot on a haul road
static func _chip() -> ArrayMesh:
	var b := _b()
	var p := PackedVector2Array([Vector2(-0.5, -0.2), Vector2(-0.1, -0.5),
		Vector2(0.45, -0.25), Vector2(0.5, 0.2), Vector2(0.0, 0.5), Vector2(-0.4, 0.3)])
	b.prism(p, -0.12, 0.12)
	return b.mesh()
