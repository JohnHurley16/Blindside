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
## PHOTOREAL PASS (DESIGN-PRINCIPLES 6). Four changes, all of them about the
## last metre and a half:
##
## 1. THE GRID IS 0.5 m INSIDE THE COMPOUND, 1 m outside it. It was 1 m
##    everywhere, and a 1 m plane cannot hold a rut or a graded channel.
## 2. A DRESSING-SIDE RELIEF FIELD, `relief()`, sits on top of the layout's
##    height. It is ALWAYS >= 0 - never negative - so that every prop placed at
##    `L.ground_mm` ends up slightly BURIED rather than slightly hovering.
##    Hovering contact across 85 000 instances is the classic tell and this is
##    the cheapest possible fix for it: one addition, no per-prop work.
##    `scatter.gd` calls the same function so the underfoot layer follows it.
## 3. VERTEX COLOUR NOW CARRIES WHAT THE LAYOUT KNOWS. R hardstanding,
##    G mud, B **wear along the routes machines actually take** - the six
##    walkway polylines, the haul road and the four stations, straight out of
##    the plan - and A **pondability**, which is how much lower this point is
##    than the ground around it. The shader reads all four; the first pass
##    wrote them and then ignored them.
## 4. Normals are taken from the DISPLACED heights, so mesh and shader agree.

const RELIEF_MAX := 0.080   # metres. The most a prop can be buried.

## The amplitude of the shallow dish that puddles live in, metres.
##
## THIS IS THE NUMBER THAT MAKES PUDDLES POSSIBLE, and getting it wrong is why
## the first attempt had none. A puddle is a WATER LEVEL crossing a GROUND
## SURFACE. If the ground under the water is flat to a millimetre - which a
## graded concrete pad is - then no level produces a puddle edge: the whole pad
## is either dry or flooded, and both look identical to a uniform wet sheen.
##
## So the pad is given a real 16 mm dish at 8 m wavelength, in the mesh, and the
## same field is written into vertex colour A as "how far below the local pond
## plane this point is". The shader then only has to subtract its own micro
## height field from it, and the puddle edge falls out where the two cross -
## wrapping round the aggregate, filling the joints first, and growing when it
## rains without a single puddle shape being authored anywhere.
const POND_AMP := 0.024

## the shallow dish. 0 = the low ground that holds water, 1 = the high ground.
static func dish(x: float, z: float) -> float:
	return clampf(_vn(x * 0.130 + 41.0, z * 0.130 + 7.0) * 0.72
		+ _vn(x * 0.365 + 11.0, z * 0.365 + 63.0) * 0.28, 0.0, 1.0)

## The wear field, baked once at 1 m over the whole site box and then read by
## bilinear lookup. It is a grid rather than a per-call polyline query because
## every one of the 85 000 scattered props needs the SAME answer the ground mesh
## got - a prop that disagrees with the ground about where the rut is, hovers.
static var _wg := PackedFloat32Array()
static var _wx0 := -82.0
static var _wz0 := -78.0
static var _wnx := 0
static var _wnz := 0

static func wear_at(x: float, z: float) -> float:
	if _wnx == 0:
		return 0.0
	var fx := clampf(x - _wx0, 0.0, float(_wnx - 1) - 0.001)
	var fz := clampf(z - _wz0, 0.0, float(_wnz - 1) - 0.001)
	var ix := int(fx)
	var iz := int(fz)
	var tx := fx - float(ix)
	var tz := fz - float(iz)
	var a := _wg[iz * _wnx + ix]
	var b := _wg[iz * _wnx + ix + 1]
	var c := _wg[(iz + 1) * _wnx + ix]
	var d := _wg[(iz + 1) * _wnx + ix + 1]
	return lerpf(lerpf(a, b, tx), lerpf(c, d, tx), tz)

## The height every other dressing file must place against: the layout height
## plus the dressing relief. Anything that calls `L.ground_mm` directly and not
## this will float by up to 67 mm.
static func height(L: SurfaceLayout, x: float, z: float) -> float:
	var hard := 1.0 if L.on_pad(int(x * 1000.0), int(z * 1000.0)) else 0.0
	if hard < 0.5:
		hard = clampf(1.0 - _pad_dist(L, x, z) / 1.6, 0.0, 1.0) * 0.7
	var base := float(L.ground_mm(int(x * 1000.0), int(z * 1000.0))) / 1000.0
	return base + relief(x, z, hard, wear_at(x, z))

static func build(L: SurfaceLayout, parent: Node3D) -> Dictionary:
	var t0 := Time.get_ticks_usec()
	var site: Dictionary = L.plan["site"]
	var x0 := float(site["x0"]) / 1000.0
	var x1 := float(site["x1"]) / 1000.0
	var z0 := float(site["z0"]) / 1000.0
	var z1 := float(site["z1"]) / 1000.0

	# the compound - where a camera ever stands - gets twice the resolution
	var xs := _axis(x0, x1, 1.0, 420.0, -38.0, 42.0, 0.5)
	var zs := _axis(z0, z1, 1.0, 420.0, -32.0, 32.0, 0.5)
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

	# --- the routes, flattened once. Wear is read off these.
	var segs: Array = []
	for w in L.plan["walkways"]:
		segs.append([Vector2(float(w[0][0]) / 1000.0, float(w[0][1]) / 1000.0),
			Vector2(float(w[1][0]) / 1000.0, float(w[1][1]) / 1000.0),
			float(L.plan["walkway_w"]) / 2000.0 + 0.9])
	var rp: Array = L.plan["road"]
	for i in range(rp.size() - 1):
		segs.append([Vector2(float(rp[i][0]) / 1000.0, float(rp[i][1]) / 1000.0),
			Vector2(float(rp[i + 1][0]) / 1000.0, float(rp[i + 1][1]) / 1000.0),
			float(L.plan["road_w"]) / 2000.0])
	var spots: Array = [Vector2(0, 0)]
	for st in L.plan["stations"]:
		spots.append(Vector2(float(st["x"]) / 1000.0, float(st["z"]) / 1000.0))
	_bake_wear(segs, spots)

	var hcache := PackedFloat32Array()
	var wcache := PackedFloat32Array()
	var pcache := PackedFloat32Array()
	hcache.resize(nx * nz)
	wcache.resize(nx * nz)
	pcache.resize(nx * nz)
	for iz in nz:
		var zf: float = zs[iz]
		for ix in nx:
			var xf: float = xs[ix]
			var i := iz * nx + ix
			var hardv := 1.0 if L.on_pad(int(xf * 1000.0), int(zf * 1000.0)) else 0.0
			if hardv < 0.5:
				hardv = clampf(1.0 - _pad_dist(L, xf, zf) / 1.6, 0.0, 1.0) * 0.7
			var wr := wear_at(xf, zf)
			wcache[i] = wr
			pcache[i] = hardv
			hcache[i] = float(L.ground_mm(int(xf * 1000.0), int(zf * 1000.0))) / 1000.0 \
				+ relief(xf, zf, hardv, wr)

	for iz in nz:
		for ix in nx:
			var i := iz * nx + ix
			var x: float = xs[ix]
			var z: float = zs[iz]
			var h: float = hcache[i]
			verts[i] = Vector3(x, h, z)
			# normal from neighbours - of the DISPLACED height, so the shader's
			# form normal and the mesh's normal are the same surface
			var hl: float = hcache[i - (1 if ix > 0 else 0)]
			var hr: float = hcache[i + (1 if ix < nx - 1 else 0)]
			var hb: float = hcache[i - (nx if iz > 0 else 0)]
			var hf: float = hcache[i + (nx if iz < nz - 1 else 0)]
			var dx: float = xs[mini(ix + 1, nx - 1)] - xs[maxi(ix - 1, 0)]
			var dz: float = zs[mini(iz + 1, nz - 1)] - zs[maxi(iz - 1, 0)]
			norms[i] = Vector3(-(hr - hl) / maxf(dx, 0.01), 2.0, -(hf - hb) / maxf(dz, 0.01)).normalized()
			# --- surface facts
			var hard: float = pcache[i]
			var mud := clampf((h - 0.4) / 3.0, 0.0, 1.0) * 0.8
			mud = maxf(mud, clampf(1.0 - hard, 0.0, 1.0) * 0.35)
			# WEAR IS A PROPERTY OF THE GROUND, NOT OF THE PLAN POSITION. A walkway
			# runs from the collar to the course on z = 0 and a spoil tip has been
			# dumped across it; without this gate the wear field paints a worn
			# route six metres up the side of the tip, which reads as a pale band
			# of spilt something. Wear stops where the ground has been buried.
			var traffic: float = wcache[i] * clampf(1.0 - (h - 0.45) / 1.10, 0.0, 1.0)
			# pondability: how much lower this point is than the ground round it,
			# plus a broad noise so that flat concrete still puddles in patches
			# rather than uniformly. The SHADER decides the puddle's edge, off
			# its own height field; this only says where water may collect.
			var low := clampf(((hl + hr + hb + hf) * 0.25 - h) / 0.045, 0.0, 1.0)
			# A HEAP DRAINS. Off the pad, ponding is mostly the real local lowness
			# rather than the pad's dish, and it is switched off entirely as the
			# ground rises into the spoil - otherwise the shallow dish puts
			# standing water on top of a tip, which reads as snow.
			var pond := clampf(maxf(low, (1.0 - dish(x, z)) * (0.95 if hard > 0.5 else 0.42)), 0.0, 1.0)
			pond = maxf(pond, traffic * 0.55)     # ruts hold water
			pond *= clampf(1.0 - (h - 0.30) / 0.85, 0.0, 1.0)
			# ORDER PASS (DESIGN-PRINCIPLES 7): "standing water belongs in the
			# margins only". Ground the LAYOUT keeps clear is ground that is
			# driven, swept and drained, so it damps to a wet film rather than
			# holding pools. A lake across the apron in front of the service bay
			# says nobody has crossed it in a year.
			if L.swept(int(x * 1000.0), int(z * 1000.0)):
				pond *= 0.28
			if x < x0 or x > x1 or z < z0 or z > z1:
				traffic = 0.0
				hard = 0.0
				pond = 0.0
			cols[i] = Color(hard, mud, traffic, pond)

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

## RULE, and it is a contract with every other dressing file.
##
## The dressing-side micro relief on top of the layout's height, in metres.
## **It is never negative.** Layout says the ground is at h; the rendered ground
## is at h + relief(), which is between 0 and 67 mm above it. So a prop placed
## by any other file at the layout height is buried by up to 67 mm and is never
## left hovering above a surface that has moved down under it.
##
## Ruts subtract from the lump term, so the routes machines take are the lowest
## ground in the yard, which is where water goes.
static func relief(x: float, z: float, hard: float, wear: float) -> float:
	var lump := _vn(x * 0.45, z * 0.45)
	var lump2 := _vn(x * 1.4 + 31.0, z * 1.4 + 17.0)
	var d := dish(x, z)
	var open := 0.045 * lump + 0.022 * lump2 + POND_AMP * d
	var conc := POND_AMP * d + 0.009 * lump2 + 0.004 * lump
	var h: float = lerpf(open, conc, clampf(hard, 0.0, 1.0))
	h -= wear * (0.036 * (1.0 - hard) + 0.006 * hard)
	return maxf(h, 0.0)

static func _bake_wear(segs: Array, spots: Array) -> void:
	_wnx = 183
	_wnz = 157
	_wg = PackedFloat32Array()
	_wg.resize(_wnx * _wnz)
	for iz in _wnz:
		var z := _wz0 + float(iz)
		for ix in _wnx:
			_wg[iz * _wnx + ix] = _wear(segs, spots, _wx0 + float(ix), z)

## wear along the routes the plan says things take, 0..1
static func _wear(segs: Array, spots: Array, x: float, z: float) -> float:
	var pnt := Vector2(x, z)
	var best := 0.0
	for s in segs:
		var a: Vector2 = s[0]
		var b: Vector2 = s[1]
		var ab := b - a
		var t := clampf((pnt - a).dot(ab) / maxf(ab.length_squared(), 0.001), 0.0, 1.0)
		var d := (a + ab * t).distance_to(pnt)
		best = maxf(best, clampf(1.0 - d / float(s[2]), 0.0, 1.0))
	for p in spots:
		best = maxf(best, clampf(1.0 - pnt.distance_to(p) / 5.5, 0.0, 1.0) * 0.85)
	# the edge of a worn route is ragged, not a clean band
	return clampf(best * (0.80 + 0.40 * _vn(x * 0.9 + 3.0, z * 0.9 + 8.0)), 0.0, 1.0)

# ---- a small value noise, used only by the relief and pond fields. It has to
#      be cheap: it is evaluated once per vertex and there are ~70 000 of them.
static func _h2(ix: int, iz: int) -> float:
	var n := ix * 374761393 + iz * 668265263
	n = (n ^ (n >> 13)) * 1274126177
	return float((n ^ (n >> 16)) & 0xFFFF) / 65535.0

static func _vn(x: float, z: float) -> float:
	var ix := int(floor(x))
	var iz := int(floor(z))
	var fx := x - float(ix)
	var fz := z - float(iz)
	fx = fx * fx * (3.0 - 2.0 * fx)
	fz = fz * fz * (3.0 - 2.0 * fz)
	var a := _h2(ix, iz)
	var b := _h2(ix + 1, iz)
	var c := _h2(ix, iz + 1)
	var d := _h2(ix + 1, iz + 1)
	return lerpf(lerpf(a, b, fx), lerpf(c, d, fx), fz)

## a graded axis: `fine` metres between fa and fb, `step` metres over the rest of
## the site box, then a geometric skirt out to the horizon. One mesh, one call.
static func _axis(a: float, b: float, step: float, out_to: float,
		fa: float, fb: float, fine: float) -> PackedFloat32Array:
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
		if x >= fa - 0.001 and x < fb - 0.001:
			x += fine
		else:
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
