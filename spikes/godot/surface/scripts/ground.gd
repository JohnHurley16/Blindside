extends RefCounted
class_name Ground
##
## DRESSING LAYER - the ground surface.
##
## One indexed ArrayMesh for the whole site, in one draw call. Heights come from
## LAYOUT (integer millimetres); everything else - grain, slab joints, cracks,
## oil, tracked mud, standing water - is generated in the fragment shader from
## world position, because a generated site cannot be UV unwrapped.
##
## Vertex colour carries the four surface facts the shader needs:
##   R hardstanding   G mud/spoil   B traffic (oil, rubber, tracked mud)   A lowness (water pools)
##
## The grid is 1 m inside the site box and grows geometrically outside it, so a
## horizon exists without a second mesh or a second draw call.

static func build(L: SurfaceLayout, parent: Node3D) -> Dictionary:
	var t0 := Time.get_ticks_usec()
	var site: Dictionary = L.plan["site"]
	var x0 := float(site["x0"]) / 1000.0
	var x1 := float(site["x1"]) / 1000.0
	var z0 := float(site["z0"]) / 1000.0
	var z1 := float(site["z1"]) / 1000.0

	var xs := _axis(x0, x1, 1.0, 420.0)
	var zs := _axis(z0, z1, 1.0, 420.0)
	var nx := xs.size()
	var nz := zs.size()

	var verts := PackedVector3Array()
	var norms := PackedVector3Array()
	var cols := PackedColorArray()
	verts.resize(nx * nz)
	norms.resize(nx * nz)
	cols.resize(nx * nz)

	var shaft: Dictionary = L.plan["shaft"]
	var sw := float(shaft["w"]) / 2000.0 + 0.15
	var sd := float(shaft["d"]) / 2000.0 + 0.15

	var hcache := PackedFloat32Array()
	hcache.resize(nx * nz)
	for iz in nz:
		for ix in nx:
			hcache[iz * nx + ix] = float(L.ground_mm(int(xs[ix] * 1000.0), int(zs[iz] * 1000.0))) / 1000.0

	for iz in nz:
		for ix in nx:
			var i := iz * nx + ix
			var x: float = xs[ix]
			var z: float = zs[iz]
			var h: float = hcache[i]
			verts[i] = Vector3(x, h, z)
			# normal from neighbours
			var hl: float = hcache[i - (1 if ix > 0 else 0)]
			var hr: float = hcache[i + (1 if ix < nx - 1 else 0)]
			var hb: float = hcache[i - (nx if iz > 0 else 0)]
			var hf: float = hcache[i + (nx if iz < nz - 1 else 0)]
			var dx: float = xs[mini(ix + 1, nx - 1)] - xs[maxi(ix - 1, 0)]
			var dz: float = zs[mini(iz + 1, nz - 1)] - zs[maxi(iz - 1, 0)]
			norms[i] = Vector3(-(hr - hl) / maxf(dx, 0.01), 2.0, -(hf - hb) / maxf(dz, 0.01)).normalized()
			# --- surface facts
			var hard := 1.0 if L.on_pad(int(x * 1000.0), int(z * 1000.0)) else 0.0
			if hard < 0.5:
				# feather the concrete edge so the pad does not stop on a line
				var dpad := _pad_dist(L, x, z)
				hard = clampf(1.0 - dpad / 1.6, 0.0, 1.0) * 0.7
			var mud := clampf((h - 0.4) / 3.0, 0.0, 1.0) * 0.8
			mud = maxf(mud, clampf(1.0 - hard, 0.0, 1.0) * 0.35)
			var traffic := 0.0
			traffic = maxf(traffic, clampf(1.0 - Vector2(x, z).length() / 16.0, 0.0, 1.0))
			traffic = maxf(traffic, clampf(1.0 - Vector2(x + 19.0, z + 2.0).length() / 13.0, 0.0, 1.0))
			traffic = maxf(traffic, _road_traffic(L, x, z))
			var low := clampf((h * 0.5 - (hl + hr + hb + hf) * 0.125) * -3.0 + 0.30, 0.0, 1.0)
			# outside the site box the grid stretches geometrically, so the
			# finite-difference "lowness" is meaningless there - and a wrong
			# lowness paints a black wet band across the horizon.
			if x < x0 or x > x1 or z < z0 or z > z1:
				low = 0.0
				traffic = 0.0
				hard = 0.0
			cols[i] = Color(hard, mud, clampf(traffic * hard + traffic * 0.35, 0.0, 1.0), low)

	var idx := PackedInt32Array()
	for iz in nz - 1:
		for ix in nx - 1:
			var a := iz * nx + ix
			var b := a + 1
			var c := a + nx
			var d := c + 1
			# punch the shaft
			var mx := (xs[ix] + xs[ix + 1]) * 0.5
			var mz := (zs[iz] + zs[iz + 1]) * 0.5
			if absf(mx) < sw + 0.6 and absf(mz) < sd + 0.6:
				continue
			# Godot's front faces are CLOCKWISE. Get this backwards and the whole
			# flat ground is back-face culled while the spoil tips still read,
			# because on a dome you see the inside of the far slope. It looks
			# exactly like "the ground is washed out", and it is not.
			idx.append(a); idx.append(b); idx.append(c)
			idx.append(b); idx.append(d); idx.append(c)

	var arr := []
	arr.resize(Mesh.ARRAY_MAX)
	arr[Mesh.ARRAY_VERTEX] = verts
	arr[Mesh.ARRAY_NORMAL] = norms
	arr[Mesh.ARRAY_COLOR] = cols
	arr[Mesh.ARRAY_INDEX] = idx
	var am := ArrayMesh.new()
	am.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arr)

	var mi := MeshInstance3D.new()
	mi.name = "Ground"
	mi.mesh = am
	mi.material_override = Mats.ground_material(L)
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
	parent.add_child(mi)

	return {"verts": verts.size(), "tris": idx.size() / 3,
		"ms": float(Time.get_ticks_usec() - t0) / 1000.0}

static func _axis(a: float, b: float, step: float, out_to: float) -> PackedFloat32Array:
	var v := PackedFloat32Array()
	var e := a - 2.0
	var g := 2.0
	var pre := PackedFloat32Array()
	while e > -out_to:
		pre.append(e)
		e -= g
		g *= 1.55
	pre.reverse()
	v.append_array(pre)
	var x := a
	while x <= b + 0.001:
		v.append(x)
		x += step
	e = b + 2.0
	g = 2.0
	while e < out_to:
		v.append(e)
		e += g
		g *= 1.55
	return v

static func _pad_dist(L: SurfaceLayout, x: float, z: float) -> float:
	var best := 999.0
	for p in L.plan["pads"]:
		var px0 := float(p["x0"]) / 1000.0
		var pz0 := float(p["z0"]) / 1000.0
		var px1 := float(p["x1"]) / 1000.0
		var pz1 := float(p["z1"]) / 1000.0
		var dx := maxf(maxf(px0 - x, 0.0), x - px1)
		var dz := maxf(maxf(pz0 - z, 0.0), z - pz1)
		best = minf(best, sqrt(dx * dx + dz * dz))
	return best

static func _road_traffic(L: SurfaceLayout, x: float, z: float) -> float:
	var pts: Array = L.plan["road"]
	var w := float(L.plan["road_w"]) / 1000.0
	var best := 999.0
	for i in range(pts.size() - 1):
		var a := Vector2(float(pts[i][0]) / 1000.0, float(pts[i][1]) / 1000.0)
		var b := Vector2(float(pts[i + 1][0]) / 1000.0, float(pts[i + 1][1]) / 1000.0)
		var ab := b - a
		var t := clampf((Vector2(x, z) - a).dot(ab) / maxf(ab.length_squared(), 0.001), 0.0, 1.0)
		best = minf(best, (a + ab * t - Vector2(x, z)).length())
	return clampf(1.0 - best / (w * 0.5), 0.0, 1.0)
