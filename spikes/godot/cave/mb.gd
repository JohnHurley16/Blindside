# ---------------------------------------------------------------------------
# BLINDSIDE assayer spike -- the mesh builder.
#
# Surf and MB are copied verbatim from spikes/godot/cave/dressing.gd, including
# the copy-on-write note, because that note is the difference between 40 ms and
# 1.3 s of generation. Everything after them is new, and every one of them is a
# CASTING rule from ART-DIRECTION 5.2: fillets at every junction, webs and ribs
# on every flat plane, 2 degrees of draft, a parting line, raised part numbers.
#
# Nothing here imports a mesh, opens an image, or unwraps a UV.
# ---------------------------------------------------------------------------
class_name MeshKit
extends RefCounted


class Surf:
	var v := PackedVector3Array()
	var n := PackedVector3Array()
	var c := PackedColorArray()
	var u := PackedVector2Array()
	var u2 := PackedVector2Array()
	var idx := PackedInt32Array()

	# NOTE: every Packed* here is a MEMBER, and is only ever mutated from
	# inside this class. GDScript Packed arrays are copy-on-write, so holding
	# one in a local while appending copies the whole array on every call.
	func append_geo(av: PackedVector3Array, an: PackedVector3Array,
					ac: PackedColorArray, au: PackedVector2Array,
					au2: PackedVector2Array, aidx: PackedInt32Array,
					xf: Transform3D, ident: bool) -> void:
		var base: int = v.size()
		if ident:
			for i in range(av.size()):
				v.push_back(av[i])
				n.push_back(an[i])
		else:
			var nb: Basis = xf.basis.inverse().transposed()
			for i in range(av.size()):
				v.push_back(xf * av[i])
				n.push_back((nb * an[i]).normalized())
		var nc: int = ac.size()
		var nu: int = au.size()
		var nu2: int = au2.size()
		for i in range(av.size()):
			c.push_back(ac[i] if i < nc else Color(1, 1, 1, 1))
			u.push_back(au[i] if i < nu else Vector2.ZERO)
			u2.push_back(au2[i] if i < nu2 else Vector2.ZERO)
		for i in range(aidx.size()):
			idx.push_back(aidx[i] + base)


class MB:
	var surf: Dictionary = {}
	var order: Array = []

	func _bucket(m: Material) -> Surf:
		if not surf.has(m):
			surf[m] = Surf.new()
			order.append(m)
		return surf[m]

	func add_arrays(m: Material, v: PackedVector3Array, n: PackedVector3Array,
					c: PackedColorArray, u: PackedVector2Array, u2: PackedVector2Array,
					idx: PackedInt32Array, xf: Transform3D) -> void:
		_bucket(m).append_geo(v, n, c, u, u2, idx, xf, xf == Transform3D.IDENTITY)

	func add_prim(m: Material, prim: PrimitiveMesh, xf: Transform3D, col: Color) -> void:
		var a: Array = prim.get_mesh_arrays()
		var v: PackedVector3Array = a[Mesh.ARRAY_VERTEX]
		var n: PackedVector3Array = a[Mesh.ARRAY_NORMAL]
		var idx: PackedInt32Array = a[Mesh.ARRAY_INDEX]
		var c := PackedColorArray()
		c.resize(v.size())
		c.fill(col)
		_bucket(m).append_geo(v, n, c, PackedVector2Array(), PackedVector2Array(), idx, xf, false)

	func tri_count() -> int:
		var t: int = 0
		for m in order:
			t += (surf[m] as Surf).idx.size() / 3
		return t

	func vert_count() -> int:
		var t: int = 0
		for m in order:
			t += (surf[m] as Surf).v.size()
		return t

	func is_empty() -> bool:
		return tri_count() == 0

	func commit() -> ArrayMesh:
		var am := ArrayMesh.new()
		for m in order:
			var b: Surf = surf[m]
			if b.idx.size() == 0:
				continue
			var arr := []
			arr.resize(Mesh.ARRAY_MAX)
			arr[Mesh.ARRAY_VERTEX] = b.v
			arr[Mesh.ARRAY_NORMAL] = b.n
			arr[Mesh.ARRAY_COLOR] = b.c
			arr[Mesh.ARRAY_TEX_UV] = b.u
			arr[Mesh.ARRAY_TEX_UV2] = b.u2
			arr[Mesh.ARRAY_INDEX] = b.idx
			am.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arr)
			am.surface_set_material(am.get_surface_count() - 1, m)
		return am


# ===========================================================================
# primitives
# ===========================================================================
static func box(sx: float, sy: float, sz: float) -> BoxMesh:
	var b := BoxMesh.new()
	b.size = Vector3(sx, sy, sz)
	return b


static func cyl(r: float, h: float, seg: int = 12) -> CylinderMesh:
	var c := CylinderMesh.new()
	c.top_radius = r
	c.bottom_radius = r
	c.height = h
	c.radial_segments = seg
	c.rings = 0
	return c


static func taper(rt: float, rb: float, h: float, seg: int = 12) -> CylinderMesh:
	var c := CylinderMesh.new()
	c.top_radius = rt
	c.bottom_radius = rb
	c.height = h
	c.radial_segments = seg
	c.rings = 0
	return c


static func sph(r: float, seg: int = 10) -> SphereMesh:
	var s := SphereMesh.new()
	s.radius = r
	s.height = r * 2.0
	s.radial_segments = seg
	s.rings = maxi(3, seg / 2)
	return s


static func xf(p: Vector3, rot: Vector3 = Vector3.ZERO, sc: Vector3 = Vector3.ONE) -> Transform3D:
	return Transform3D(Basis.from_euler(rot).scaled(sc), p)


# MEASURED, not assumed (see _windtest.gd): for a Godot BoxMesh face whose
# shading normal is +Z, cross(v1-v0, v2-v0) is -Z. So Godot's front face winds
# so that the naive cross product points INWARD, and a normal computed the
# naive way points into the solid. Under one light and no ambient that renders
# as a black cut-out, which is the bug the cave spike found in every underfoot
# frame it ever took. Every winding in this file obeys the measured rule and
# this function negates to match it.
static func recalc_normals(v: PackedVector3Array, idx: PackedInt32Array) -> PackedVector3Array:
	var n := PackedVector3Array()
	n.resize(v.size())
	for i in range(v.size()):
		n[i] = Vector3.ZERO
	var i2: int = 0
	while i2 < idx.size():
		var a: int = idx[i2]
		var b: int = idx[i2 + 1]
		var c: int = idx[i2 + 2]
		var fn: Vector3 = (v[b] - v[a]).cross(v[c] - v[a])
		n[a] += fn
		n[b] += fn
		n[c] += fn
		i2 += 3
	for i in range(n.size()):
		n[i] = -n[i].normalized() if n[i].length() > 0.0001 else Vector3.UP
	return n


# ===========================================================================
# the casting vocabulary
#
# Everything on this machine was poured, so everything on it obeys the same
# five rules. These are those five rules as functions; the machine is built by
# calling them, which is what makes it a rule-based mesh rather than a model.
# ===========================================================================

# A PRISM of `sides` sides about +Y, given the across-flats width, with DRAFT:
# the top is `draft` narrower than the bottom, because a casting has to come
# out of the mould. Two degrees over a 1.8 m section is 63 mm, which is what
# makes a 6 m column read as cast and not as extruded.
static func prism(mb: MB, mat: Material, col: Color, sides: int,
				  af_bot: float, af_top: float, y0: float, y1: float,
				  ctr := Vector3.ZERO, phase: float = 0.0,
				  cap_bot: bool = true, cap_top: bool = true) -> void:
	var rb: float = af_bot * 0.5 / cos(PI / float(sides))
	var rt: float = af_top * 0.5 / cos(PI / float(sides))
	var v := PackedVector3Array()
	var idx := PackedInt32Array()
	for i in range(sides):
		var a0: float = phase + TAU * float(i) / float(sides)
		var a1: float = phase + TAU * float(i + 1) / float(sides)
		var p0 := Vector3(cos(a0) * rb, y0, sin(a0) * rb) + ctr
		var p1 := Vector3(cos(a1) * rb, y0, sin(a1) * rb) + ctr
		var p2 := Vector3(cos(a0) * rt, y1, sin(a0) * rt) + ctr
		var p3 := Vector3(cos(a1) * rt, y1, sin(a1) * rt) + ctr
		var b: int = v.size()
		v.push_back(p0); v.push_back(p1); v.push_back(p2); v.push_back(p3)
		idx.append_array([b, b + 1, b + 2, b + 1, b + 3, b + 2])
	if cap_top:
		var b2: int = v.size()
		v.push_back(Vector3(0, y1, 0) + ctr)
		for i in range(sides + 1):
			var a: float = phase + TAU * float(i % sides) / float(sides)
			v.push_back(Vector3(cos(a) * rt, y1, sin(a) * rt) + ctr)
		for i in range(sides):
			idx.append_array([b2, b2 + 1 + i, b2 + 1 + ((i + 1) % sides)])
	if cap_bot:
		var b3: int = v.size()
		v.push_back(Vector3(0, y0, 0) + ctr)
		for i in range(sides + 1):
			var a2: float = phase + TAU * float(i % sides) / float(sides)
			v.push_back(Vector3(cos(a2) * rb, y0, sin(a2) * rb) + ctr)
		for i in range(sides):
			idx.append_array([b3, b3 + 1 + ((i + 1) % sides), b3 + 1 + i])
	var n: PackedVector3Array = recalc_normals(v, idx)
	var c := PackedColorArray()
	c.resize(v.size())
	c.fill(col)
	mb.add_arrays(mat, v, n, c, PackedVector2Array(), PackedVector2Array(), idx, Transform3D.IDENTITY)


# A hollow prism: the hammer, the flange rings, the slew race. Same draft rule.
static func prism_ring(mb: MB, mat: Material, col: Color, sides: int,
					   af_out: float, af_in: float, y0: float, y1: float,
					   ctr := Vector3.ZERO, phase: float = 0.0) -> void:
	var ro: float = af_out * 0.5 / cos(PI / float(sides))
	var ri: float = af_in * 0.5 / cos(PI / float(sides))
	var v := PackedVector3Array()
	var idx := PackedInt32Array()
	for i in range(sides):
		var a0: float = phase + TAU * float(i) / float(sides)
		var a1: float = phase + TAU * float(i + 1) / float(sides)
		for pair in [[ro, 1.0], [ri, -1.0]]:
			var r: float = pair[0]
			var s: float = pair[1]
			var b: int = v.size()
			v.push_back(Vector3(cos(a0) * r, y0, sin(a0) * r) + ctr)
			v.push_back(Vector3(cos(a1) * r, y0, sin(a1) * r) + ctr)
			v.push_back(Vector3(cos(a0) * r, y1, sin(a0) * r) + ctr)
			v.push_back(Vector3(cos(a1) * r, y1, sin(a1) * r) + ctr)
			if s > 0.0:
				idx.append_array([b, b + 1, b + 2, b + 1, b + 3, b + 2])
			else:
				idx.append_array([b, b + 2, b + 1, b + 1, b + 2, b + 3])
		# the two annular faces
		for pair2 in [[y1, 1.0], [y0, -1.0]]:
			var y: float = pair2[0]
			var s2: float = pair2[1]
			var b2: int = v.size()
			v.push_back(Vector3(cos(a0) * ro, y, sin(a0) * ro) + ctr)
			v.push_back(Vector3(cos(a1) * ro, y, sin(a1) * ro) + ctr)
			v.push_back(Vector3(cos(a0) * ri, y, sin(a0) * ri) + ctr)
			v.push_back(Vector3(cos(a1) * ri, y, sin(a1) * ri) + ctr)
			if s2 > 0.0:
				idx.append_array([b2, b2 + 1, b2 + 2, b2 + 1, b2 + 3, b2 + 2])
			else:
				idx.append_array([b2, b2 + 2, b2 + 1, b2 + 1, b2 + 2, b2 + 3])
	var n: PackedVector3Array = recalc_normals(v, idx)
	var c := PackedColorArray()
	c.resize(v.size())
	c.fill(col)
	mb.add_arrays(mat, v, n, c, PackedVector2Array(), PackedVector2Array(), idx, Transform3D.IDENTITY)


# A TAPERED BOX -- the universal cast member. Four corners at each end, so a
# leg that is 340 mm at the hub and 500 mm at the pad is one call. Local +Z is
# the length; the caller supplies the transform.
static func tbox(mb: MB, mat: Material, col: Color,
				 w0: float, h0: float, w1: float, h1: float, len: float,
				 t: Transform3D, off0 := Vector2.ZERO, off1 := Vector2.ZERO) -> void:
	var v := PackedVector3Array()
	for s in [[0.0, w0, h0, off0], [len, w1, h1, off1]]:
		var z: float = s[0]
		var w: float = s[1]
		var h: float = s[2]
		var o: Vector2 = s[3]
		v.push_back(Vector3(-w * 0.5 + o.x, -h * 0.5 + o.y, z))
		v.push_back(Vector3(w * 0.5 + o.x, -h * 0.5 + o.y, z))
		v.push_back(Vector3(w * 0.5 + o.x, h * 0.5 + o.y, z))
		v.push_back(Vector3(-w * 0.5 + o.x, h * 0.5 + o.y, z))
	var idx := PackedInt32Array([
		0, 1, 2, 0, 2, 3,        # near cap (reversed below)
		4, 6, 5, 4, 7, 6,        # far cap
		0, 4, 1, 1, 4, 5,        # bottom
		2, 6, 3, 3, 6, 7,        # top
		1, 5, 2, 2, 5, 6,        # +x
		3, 7, 0, 0, 7, 4,        # -x
	])
	# the near cap faces -Z, so it winds the other way round
	idx[0] = 0; idx[1] = 1; idx[2] = 2; idx[3] = 0; idx[4] = 2; idx[5] = 3
	var n: PackedVector3Array = recalc_normals(v, idx)
	var c := PackedColorArray()
	c.resize(v.size())
	c.fill(col)
	mb.add_arrays(mat, v, n, c, PackedVector2Array(), PackedVector2Array(), idx, t)


# A WEB RIB -- a triangular gusset in the local XY plane, extruded `t` thick.
# ART-DIRECTION 5.2: "webs and ribs on every flat plane". This is what stops a
# tapered box reading as a tapered box.
static func web(mb: MB, mat: Material, col: Color,
				a: Vector3, b: Vector3, c3: Vector3, t: float) -> void:
	var nrm: Vector3 = (b - a).cross(c3 - a).normalized()
	if nrm.length() < 0.001:
		return
	var o: Vector3 = nrm * (t * 0.5)
	var v := PackedVector3Array([a - o, b - o, c3 - o, a + o, b + o, c3 + o])
	var idx := PackedInt32Array([
		0, 1, 2, 3, 5, 4,
		0, 3, 1, 1, 3, 4,
		1, 4, 2, 2, 4, 5,
		2, 5, 0, 0, 5, 3,
	])
	var n: PackedVector3Array = recalc_normals(v, idx)
	var col2 := PackedColorArray()
	col2.resize(v.size())
	col2.fill(col)
	mb.add_arrays(mat, v, n, col2, PackedVector2Array(), PackedVector2Array(), idx, Transform3D.IDENTITY)


# A BOLT: a hex head on a washer, standing proud of the face it is in.
# Nothing on this machine is welded -- a mast this tall was shipped in sections
# and the bolt lines are the evidence. `dir` is the outward face normal.
static func bolt(mb: MB, mat: Material, col: Color, p: Vector3, dir: Vector3, r: float) -> void:
	var d: Vector3 = dir.normalized()
	# a cylinder's local axis is +Y, so build a basis whose +Y is `dir`
	var up: Vector3 = Vector3.UP if absf(d.dot(Vector3.UP)) < 0.95 else Vector3.FORWARD
	var xa: Vector3 = up.cross(d).normalized()
	var za: Vector3 = d.cross(xa).normalized()
	var b := Basis(xa, d, za)
	mb.add_prim(mat, cyl(r * 1.42, r * 0.30, 8), Transform3D(b, p + d * (r * 0.15)), col)
	mb.add_prim(mat, cyl(r, r * 0.80, 6), Transform3D(b, p + d * (r * 0.70)), col)


# a basis whose LOCAL +Z points along `dir`
static func _face(dir: Vector3) -> Basis:
	var d: Vector3 = dir.normalized()
	var up: Vector3 = Vector3.UP
	if absf(d.dot(up)) > 0.98:
		up = Vector3.FORWARD
	return Basis.looking_at(-d, up)


static func face(dir: Vector3) -> Basis:
	return _face(dir)


# A basis whose LOCAL +Y runs along `d`. Godot's CylinderMesh is built about
# +Y, so every rod, tie, stay, pipe and handrail on this machine is placed with
# this. `Basis.looking_at(d).rotated(Vector3.RIGHT, PI/2)` is the tempting
# one-liner and it is wrong: Basis.rotated rotates about a GLOBAL axis, so the
# result depends on where the member happens to be pointing.
static func along(d: Vector3) -> Basis:
	var y: Vector3 = d.normalized()
	var u: Vector3 = Vector3.UP if absf(y.dot(Vector3.UP)) < 0.95 else Vector3.FORWARD
	var x: Vector3 = u.cross(y).normalized()
	var z: Vector3 = y.cross(x).normalized()
	return Basis(x, y, z)


# A PIPE RUN through a list of points, with a cast elbow at every corner.
# The feed main, the downpipe and the motor line are all one call each.
static func pipe(mb: MB, mat: Material, col: Color, pts: PackedVector3Array,
				 r: float, seg: int = 8) -> void:
	for i in range(pts.size() - 1):
		var a: Vector3 = pts[i]
		var b: Vector3 = pts[i + 1]
		var d: Vector3 = b - a
		var l: float = d.length()
		if l < 0.001:
			continue
		mb.add_prim(mat, cyl(r, l, seg), Transform3D(along(d), (a + b) * 0.5), col)
		if i > 0:
			mb.add_prim(mat, sph(r * 1.22, 8), Transform3D(Basis.IDENTITY, a), col)
	# a socketed spigot at each end, because a pipe joins something
	for e in [pts[0], pts[pts.size() - 1]]:
		mb.add_prim(mat, cyl(r * 1.35, r * 1.1, seg), Transform3D(Basis.IDENTITY, e), col)


# RAISED LETTERING. Not a texture and not a decal: 12 mm proud, cast into the
# flat, on a seven-segment stroke grid. Legible as an index system, unreadable
# as language, and there are no dates anywhere on the machine.
#
# Each glyph is a set of strokes on a 3x5 unit cell; `t` places the plate with
# local +X across the text, +Y up it, +Z out of the face.
const _GLYPH := {
	"K": [[0, 0, 0, 5], [0, 2.4, 2.6, 5], [0, 2.4, 2.6, 0]],
	"1": [[1.4, 0, 1.4, 5], [0.2, 4.0, 1.4, 5]],
	"4": [[2.2, 0, 2.2, 5], [0.0, 1.7, 2.9, 1.7], [0.0, 1.7, 2.0, 5]],
	"2": [[0, 5, 2.8, 5], [2.8, 5, 2.8, 2.7], [2.8, 2.7, 0, 2.7], [0, 2.7, 0, 0], [0, 0, 2.9, 0]],
	"7": [[0, 5, 2.9, 5], [2.9, 5, 1.1, 0]],
	"3": [[0, 5, 2.8, 5], [2.8, 5, 2.8, 0], [2.8, 0, 0, 0], [0.6, 2.6, 2.8, 2.6]],
	".": [[1.2, 0, 1.55, 0]],
	" ": [],
}


static func lettering(mb: MB, mat: Material, col: Color, text: String,
					  t: Transform3D, h: float, proud: float, stroke: float) -> void:
	var u: float = h / 5.0
	var x: float = 0.0
	for i in range(text.length()):
		var ch: String = text[i]
		if not _GLYPH.has(ch):
			ch = " "
		for s in _GLYPH[ch]:
			var a := Vector2(x + s[0] * u, s[1] * u)
			var b := Vector2(x + s[2] * u, s[3] * u)
			var mid: Vector2 = (a + b) * 0.5
			var d: Vector2 = b - a
			var l: float = d.length() + stroke
			var ang: float = atan2(d.y, d.x)
			var lt := Transform3D(
				Basis.from_euler(Vector3(0, 0, ang)).scaled(Vector3(1, 1, 1)),
				Vector3(mid.x, mid.y, proud * 0.5))
			mb.add_prim(mat, box(l, stroke, proud), t * lt, col)
		x += 3.6 * u
