extends RefCounted

# ---------------------------------------------------------------------------
# The forms a material is judged on. A sphere is not enough: a sphere has one
# curvature, one silhouette and no flat area, so it hides exactly the two lies
# that matter -- a constant roughness, and a normal that does nothing.
#
#   bevel_box    flat faces plus a tight radius. Flat faces show a constant
#                roughness immediately; the radius shows the specular ramp.
#   lump         a rough natural form. Shows the field at form scale and shows
#                whether the material has any large-scale structure at all.
#   graze_plane  a flat plane laid nearly edge-on to the camera. Grazing angle
#                is where roughness lies show, because the specular lobe is
#                stretched and every error in it is magnified.
#
# All meshes carry normals and UVs. Tangents are deliberately NOT generated:
# the family must work without them, because a generated cave has none.
# ---------------------------------------------------------------------------

static func _finish(verts: PackedVector3Array, norms: PackedVector3Array,
		uvs: PackedVector2Array, idx: PackedInt32Array) -> ArrayMesh:
	var arr := []
	arr.resize(Mesh.ARRAY_MAX)
	arr[Mesh.ARRAY_VERTEX] = verts
	arr[Mesh.ARRAY_NORMAL] = norms
	arr[Mesh.ARRAY_TEX_UV] = uvs
	arr[Mesh.ARRAY_INDEX] = idx
	var m := ArrayMesh.new()
	m.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arr)
	return m


const _FACE_AXES := [
	[Vector3(1, 0, 0), Vector3(0, 1, 0), Vector3(0, 0, 1)],
	[Vector3(-1, 0, 0), Vector3(0, 1, 0), Vector3(0, 0, -1)],
	[Vector3(0, 1, 0), Vector3(0, 0, 1), Vector3(1, 0, 0)],
	[Vector3(0, -1, 0), Vector3(0, 0, -1), Vector3(1, 0, 0)],
	[Vector3(0, 0, 1), Vector3(0, 1, 0), Vector3(-1, 0, 0)],
	[Vector3(0, 0, -1), Vector3(0, 1, 0), Vector3(1, 0, 0)],
]


# A cube surface, N x N per face, in [-1,1]^3. Everything else is built on it.
static func _cube_shell(n: int) -> Array:
	var verts := PackedVector3Array()
	var uvs := PackedVector2Array()
	var idx := PackedInt32Array()
	for f in range(6):
		var nrm: Vector3 = _FACE_AXES[f][0]
		var uax: Vector3 = _FACE_AXES[f][1]
		var vax: Vector3 = _FACE_AXES[f][2]
		var base := verts.size()
		for j in range(n + 1):
			for i in range(n + 1):
				var a := float(i) / float(n) * 2.0 - 1.0
				var b := float(j) / float(n) * 2.0 - 1.0
				verts.push_back(nrm + uax * a + vax * b)
				uvs.push_back(Vector2(float(i) / float(n), float(j) / float(n)))
		for j in range(n):
			for i in range(n):
				var v0 := base + j * (n + 1) + i
				var v1 := v0 + 1
				var v2 := v0 + (n + 1)
				var v3 := v2 + 1
				idx.append_array([v0, v2, v1, v1, v2, v3])
	return [verts, uvs, idx]


# Godot uses CLOCKWISE winding for front faces, so the outward normal of a
# triangle (a, b, c) is the NEGATION of (b-a) x (c-a). Getting this backwards
# inverts every normal in the library, and an inverted normal is not a subtle
# artefact: every direct light lands on the far side of the surface and the
# whole testbed renders black while the albedo channel looks perfect. It cost
# an hour here.
static func _recompute_normals(verts: PackedVector3Array, idx: PackedInt32Array) -> PackedVector3Array:
	var norms := PackedVector3Array()
	norms.resize(verts.size())
	for i in range(norms.size()):
		norms[i] = Vector3.ZERO
	var t := 0
	while t < idx.size():
		var a := idx[t]
		var b := idx[t + 1]
		var c := idx[t + 2]
		var fn := (verts[c] - verts[a]).cross(verts[b] - verts[a])
		norms[a] += fn
		norms[b] += fn
		norms[c] += fn
		t += 3
	for i in range(norms.size()):
		norms[i] = norms[i].normalized() if norms[i].length() > 1e-9 else Vector3.UP
	return norms


# A block with a real radius on every edge. `radius` is in metres, `size` is the
# full extent. The radius is what a bevelled block is FOR: it is the only place
# a specular highlight sweeps continuously, and a material whose roughness is a
# constant is obvious there in one frame.
static func bevel_box(size: Vector3, radius: float, n: int = 22) -> ArrayMesh:
	var sh := _cube_shell(n)
	var verts: PackedVector3Array = sh[0]
	var uvs: PackedVector2Array = sh[1]
	var idx: PackedInt32Array = sh[2]
	var half := size * 0.5
	var inner := half - Vector3(radius, radius, radius)
	inner = Vector3(maxf(inner.x, 0.0), maxf(inner.y, 0.0), maxf(inner.z, 0.0))
	for i in range(verts.size()):
		var p: Vector3 = verts[i] * half
		var q := Vector3(clampf(p.x, -inner.x, inner.x), clampf(p.y, -inner.y, inner.y),
			clampf(p.z, -inner.z, inner.z))
		var d := p - q
		if d.length() > 1e-9:
			p = q + d.normalized() * radius
		verts[i] = p
	return _finish(verts, _recompute_normals(verts, idx), uvs, idx)


# A rough natural form: a sphere pushed around by three octaves of noise. Not
# a rock model -- a shape with no flat face and no straight line, which is what
# ART 3.4 says a natural surface is.
static func lump(radius: float, seed: int, n: int = 26) -> ArrayMesh:
	var sh := _cube_shell(n)
	var verts: PackedVector3Array = sh[0]
	var uvs: PackedVector2Array = sh[1]
	var idx: PackedInt32Array = sh[2]
	var noise := FastNoiseLite.new()
	noise.noise_type = FastNoiseLite.TYPE_SIMPLEX_SMOOTH
	noise.seed = seed
	noise.frequency = 0.85
	noise.fractal_octaves = 2
	for i in range(verts.size()):
		var d: Vector3 = (verts[i] as Vector3).normalized()
		var r := radius
		# Two low octaves only. Three made a cauliflower: a natural form is a
		# few large facets, not a field of bumps -- the bumps are the shader's
		# job and duplicating them in geometry reads as coral.
		r *= 1.0 + noise.get_noise_3d(d.x * 1.35, d.y * 1.35, d.z * 1.35) * 0.34
		r *= 1.0 + noise.get_noise_3d(d.x * 3.1 + 40.0, d.y * 3.1, d.z * 3.1) * 0.13
		verts[i] = d * r
	return _finish(verts, _recompute_normals(verts, idx), uvs, idx)


# A flat plane. `tilt_deg` is how far it is laid back from facing the camera:
# at 78 degrees the camera sees it at 12 degrees off the surface, which is the
# angle at which a GGX lobe is widest and a wrong roughness is loudest.
static func plane(w: float, h: float, n: int = 40) -> ArrayMesh:
	var verts := PackedVector3Array()
	var uvs := PackedVector2Array()
	var idx := PackedInt32Array()
	for j in range(n + 1):
		for i in range(n + 1):
			var u := float(i) / float(n)
			var v := float(j) / float(n)
			verts.push_back(Vector3((u - 0.5) * w, 0.0, (v - 0.5) * h))
			uvs.push_back(Vector2(u, v))
	for j in range(n):
		for i in range(n):
			var v0 := j * (n + 1) + i
			# clockwise, so the plane faces +Y
			idx.append_array([v0, v0 + 1, v0 + (n + 1),
				v0 + 1, v0 + (n + 1) + 1, v0 + (n + 1)])
	var norms := PackedVector3Array()
	norms.resize(verts.size())
	for i in range(norms.size()):
		norms[i] = Vector3.UP
	return _finish(verts, norms, uvs, idx)


static func sphere(radius: float, n: int = 24) -> ArrayMesh:
	var sh := _cube_shell(n)
	var verts: PackedVector3Array = sh[0]
	var uvs: PackedVector2Array = sh[1]
	var idx: PackedInt32Array = sh[2]
	for i in range(verts.size()):
		verts[i] = (verts[i] as Vector3).normalized() * radius
	return _finish(verts, _recompute_normals(verts, idx), uvs, idx)
