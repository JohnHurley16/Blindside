extends RefCounted
class_name Scatter
##
## DRESSING LAYER - UNDERFOOT (0 to 1.5 m).
##
## The scale the designer's note is really about: "way more detail". Everything
## here is in the DETAIL bucket, which means chunked at 16 m, no shadow casting,
## and culled past 55 m. That is what makes tens of thousands of objects free at
## distance and dense at the feet.
##
## Decals carry what geometry cannot: oil, tracked mud, tyre and foot tracks,
## rust runs under the iron. Their textures are generated here, in code - there
## is no imported image anywhere in this spike.

var L: SurfaceLayout
var B: Batcher
var r: RandomNumberGenerator
var decals: Array = []

func _init(p_L: SurfaceLayout, p_B: Batcher) -> void:
	L = p_L
	B = p_B
	r = RandomNumberGenerator.new()
	r.seed = L.seed_v * 2654435761 + 999

## The surface, INCLUDING the dressing relief. Every underfoot prop has to agree
## with the ground mesh about where the ground is, or the whole layer floats.
func gh(x: float, z: float) -> float:
	return Ground.height(L, x, z)

func on_pad(x: float, z: float) -> bool:
	return L.on_pad(int(x * 1000.0), int(z * 1000.0))

func kcol(lo: float = 0.7, hi: float = 1.5) -> Color:
	var v := r.randf_range(lo, hi)
	return Color(v, v * r.randf_range(0.94, 1.0), v * r.randf_range(0.86, 0.98))

func build(parent: Node3D) -> void:
	_gravel()
	_pad_chippings()
	_weeds()
	_fixings()
	_litter()
	_ground_cables()
	_build_decals(parent)

# ================================================================== gravel
## RULE. Loose stock over every unpaved square metre inside 74 m of the collar,
## at 1.1 per m^2, sized 30-140 mm, flattened, random yaw, colour drawn from the
## rock family. Suppressed on the pads. This is what a machine stands on.
func _gravel() -> void:
	var rad := 74.0
	var n := int(PI * rad * rad * 2.2)
	for i in n:
		var a := r.randf() * TAU
		var d := sqrt(r.randf()) * rad
		var x := cos(a) * d
		var z := sin(a) * d
		if on_pad(x, z):
			continue
		var s := r.randf_range(0.03, 0.16)
		var mesh: String = ["chip", "chip", "rock", "rock2", "rock3"][r.randi() % 5]
		# HALF BURIED. A stone whose centre sits above the surface is a stone
		# lying on a picture of ground; a stone whose centre sits below it is
		# embedded in the ground, and its own body draws the contact shadow that
		# 55 000 shadowless DETAIL instances cannot cast for themselves.
		# VALUE, and it is the reason the spoil tips read as snow at 30 m: a
		# scattered stone whose albedo is four times the ground it lies on stops
		# being a stone and becomes a speckle, and at distance the speckle
		# aggregates into pale patches. Loose stock is drawn from the same value
		# range as the ground it is loose on.
		B.detail(mesh, "gravel", Batcher.xf(Vector3(x, gh(x, z) - s * 0.13, z),
			Vector3(s, s * r.randf_range(0.35, 0.7), s * r.randf_range(0.7, 1.4)),
			r.randf() * TAU, r.randf_range(-0.25, 0.25), r.randf_range(-0.25, 0.25)), kcol(0.50, 1.05))

## RULE. On the hardstanding: chippings tracked in, at 0.35 per m^2, plus a dense
## band 1.2 m either side of every slab joint where the sweeper never reaches.
func _pad_chippings() -> void:
	var p: Dictionary = L.plan["pads"][0]
	var x0 := float(p["x0"]) / 1000.0
	var z0 := float(p["z0"]) / 1000.0
	var x1 := float(p["x1"]) / 1000.0
	var z1 := float(p["z1"]) / 1000.0
	var n := int((x1 - x0) * (z1 - z0) * 9.0)
	for i in n:
		var x := r.randf_range(x0, x1)
		var z := r.randf_range(z0, z1)
		var s := r.randf_range(0.025, 0.105)
		var m2: String = ["chip", "chip", "rock", "rock2", "rock3"][r.randi() % 5]
		B.detail(m2, "gravel", Batcher.xf(Vector3(x, gh(x, z) - s * 0.06, z),
			Vector3(s, s * r.randf_range(0.55, 0.95), s * r.randf_range(0.7, 1.3)),
			r.randf() * TAU, r.randf_range(-0.3, 0.3), r.randf_range(-0.3, 0.3)), kcol(0.7, 1.5))
	# joint lines, on the 3.6 m module (the same module the shader draws)
	var mod := float(L.plan["slab_module"]) / 1000.0
	var jx := ceilf(x0 / mod) * mod
	while jx < x1:
		var m := int((z1 - z0) * 2.4)
		for k in m:
			var z2 := r.randf_range(z0, z1)
			var off := r.randf_range(-0.35, 0.35)
			var s2 := r.randf_range(0.02, 0.075)
			B.detail("chip", "gravel", Batcher.xf(Vector3(jx + off, gh(jx + off, z2) - 0.004, z2),
				Vector3(s2, s2 * 0.35, s2), r.randf() * TAU), kcol(0.5, 1.0))
		jx += mod
	var jz := ceilf(z0 / mod) * mod
	while jz < z1:
		var m2 := int((x1 - x0) * 2.4)
		for k2 in m2:
			var x3 := r.randf_range(x0, x1)
			var off2 := r.randf_range(-0.35, 0.35)
			var s3 := r.randf_range(0.02, 0.075)
			B.detail("chip", "gravel", Batcher.xf(Vector3(x3, gh(x3, jz + off2) - 0.004, jz + off2),
				Vector3(s3, s3 * 0.35, s3), r.randf() * TAU), kcol(0.5, 1.0))
		jz += mod

# =================================================================== weeds
## RULE. Weeds grow where nothing drives: in the slab joints, at the foot of
## every wall and fence, and over the unpaved ground at 0.22 per m^2, thinning
## toward the collar because that ground is worked daily.
func _weeds() -> void:
	var p: Dictionary = L.plan["pads"][0]
	var x0 := float(p["x0"]) / 1000.0
	var z0 := float(p["z0"]) / 1000.0
	var x1 := float(p["x1"]) / 1000.0
	var z1 := float(p["z1"]) / 1000.0
	var mod := float(L.plan["slab_module"]) / 1000.0
	# in the joints
	var jx := ceilf(x0 / mod) * mod
	while jx < x1:
		var m := int((z1 - z0) * 2.2)
		for k in m:
			if r.randf() < 0.25:
				continue
			var z := r.randf_range(z0, z1)
			var s := r.randf_range(0.10, 0.34)
			var jjx := jx + r.randf_range(-0.06, 0.06)
			B.detail("weed", "weed", Batcher.xf(Vector3(jjx, gh(jjx, z) + s * 0.36, z),
				Vector3(s * 1.4, s, s * 1.4), r.randf() * TAU), kcol(0.55, 1.25))
		jx += mod
	var jz := ceilf(z0 / mod) * mod
	while jz < z1:
		var m2 := int((x1 - x0) * 2.2)
		for k2 in m2:
			if r.randf() < 0.45:
				continue
			var x2 := r.randf_range(x0, x1)
			var s2 := r.randf_range(0.10, 0.34)
			var jjz := jz + r.randf_range(-0.06, 0.06)
			B.detail("weed", "weed", Batcher.xf(Vector3(x2, gh(x2, jjz) + s2 * 0.36, jjz),
				Vector3(s2 * 1.4, s2, s2 * 1.4), r.randf() * TAU), kcol(0.55, 1.25))
		jz += mod
	# open ground
	var rad := 70.0
	var n := int(PI * rad * rad * 0.22)
	for i in n:
		var a := r.randf() * TAU
		var d := sqrt(r.randf()) * rad
		var x3 := cos(a) * d
		var z3 := sin(a) * d
		if on_pad(x3, z3):
			continue
		if d < 14.0 and r.randf() < 0.75:
			continue
		var s3 := r.randf_range(0.14, 0.55)
		B.detail("weed", "weed", Batcher.xf(Vector3(x3, gh(x3, z3) + s3 * 0.36, z3),
			Vector3(s3 * 1.3, s3, s3 * 1.3), r.randf() * TAU), kcol(0.5, 1.3))
	# at the foot of the perimeter fence: an unbroken line of it
	var pts: Array = L.plan["fence"]
	for i in range(pts.size() - 1):
		var a2 := Vector2(float(pts[i][0]) / 1000.0, float(pts[i][1]) / 1000.0)
		var b2 := Vector2(float(pts[i + 1][0]) / 1000.0, float(pts[i + 1][1]) / 1000.0)
		var n2 := int(a2.distance_to(b2) * 2.2)
		for k3 in n2:
			var t := (float(k3) + 0.5) / float(n2)
			var pp: Vector2 = a2.lerp(b2, t)
			var s4 := r.randf_range(0.16, 0.5)
			var ox := r.randf_range(-0.5, 0.5)
			var oz := r.randf_range(-0.5, 0.5)
			B.detail("weed", "weed", Batcher.xf(Vector3(pp.x + ox, gh(pp.x + ox, pp.y + oz) + s4 * 0.36, pp.y + oz),
				Vector3(s4 * 1.3, s4, s4 * 1.3), r.randf() * TAU), kcol(0.5, 1.25))

# ================================================================= fixings
## RULE. Where something was bolted, something was dropped. Nuts, washers,
## offcuts and packing shims within 4 m of every structural foot.
func _fixings() -> void:
	var spots: Array = []
	var H: Dictionary = L.plan["headframe"]
	var sx := float(H["spread_x"]) / 2000.0
	var sz := float(H["spread_z"]) / 2000.0
	for s in [[-sx, -sz], [sx, -sz], [sx, sz], [-sx, sz]]:
		spots.append(Vector2(s[0], s[1]))
	for c in L.plan["columns"]:
		spots.append(Vector2(float(c["x"]) / 1000.0, float(c["z"]) / 1000.0))
	for st in L.plan["stations"]:
		spots.append(Vector2(float(st["x"]) / 1000.0, float(st["z"]) / 1000.0))
	spots.append(Vector2(-19.0, -3.0))
	spots.append(Vector2(-22.0, -1.5))
	spots.append(Vector2(0.0, 0.0))
	for s2 in spots:
		var n := r.randi_range(26, 60)
		for i in n:
			var a := r.randf() * TAU
			var d := sqrt(r.randf()) * 4.0
			var x: float = s2.x + cos(a) * d
			var z: float = s2.y + sin(a) * d
			var y := gh(x, z)
			var kind := r.randi() % 5
			match kind:
				0: B.detail("hex", "steel", Batcher.xf(Vector3(x, y + 0.007, z), Vector3(0.028, 0.02, 0.028), r.randf() * TAU), kcol(0.5, 1.0))
				1: B.detail("ring", "steel", Batcher.xf(Vector3(x, y + 0.001, z), Vector3(0.045, 0.006, 0.045), r.randf() * TAU), kcol(0.5, 1.0))
				2: B.detail("cyl6", "steel", Batcher.xf(Vector3(x, y + 0.006, z), Vector3(0.018, 0.11, 0.018), r.randf() * TAU, PI * 0.5, r.randf() * TAU), kcol(0.5, 1.0))
				3: B.detail("box", "timber", Batcher.xf(Vector3(x, y + 0.009, z), Vector3(0.09, 0.025, 0.22), r.randf() * TAU), kcol(0.5, 1.1))
				4: B.detail("chip", "iron", Batcher.xf(Vector3(x, y + 0.003, z), Vector3(0.07, 0.02, 0.05), r.randf() * TAU), kcol(0.5, 1.2))

# ================================================================== litter
## RULE. Cable ties, tape, offcut plastic, glove, sheet, banding strap: 0.05 per
## m^2 over the pad and double that in the lee of anything that stops the wind.
func _litter() -> void:
	var p: Dictionary = L.plan["pads"][0]
	var x0 := float(p["x0"]) / 1000.0
	var z0 := float(p["z0"]) / 1000.0
	var x1 := float(p["x1"]) / 1000.0
	var z1 := float(p["z1"]) / 1000.0
	var n := int((x1 - x0) * (z1 - z0) * 0.16)
	for i in n:
		var x := r.randf_range(x0, x1)
		var z := r.randf_range(z0, z1)
		var y := gh(x, z)
		var kind := r.randi() % 6
		match kind:
			0: B.detail("cyl6", "plastic", Batcher.xf(Vector3(x, y + 0.004, z), Vector3(0.006, 0.16, 0.006), r.randf() * TAU, PI * 0.5, r.randf() * TAU), Color(1.4, 1.4, 1.4))
			1: B.detail("ring", "plastic", Batcher.xf(Vector3(x, y + 0.004, z), Vector3(0.07, 0.008, 0.07), r.randf() * TAU), Color(1.2, 1.2, 1.2))
			2: B.detail("box", "litter", Batcher.xf(Vector3(x, y + 0.004, z), Vector3(r.randf_range(0.08, 0.3), 0.004, r.randf_range(0.08, 0.24)), r.randf() * TAU, r.randf_range(-0.2, 0.2), r.randf_range(-0.2, 0.2)), Color(1.1, 1.1, 1.05))
			3: B.detail("box", "amber", Batcher.xf(Vector3(x, y + 0.006, z), Vector3(0.03, 0.008, 0.5), r.randf() * TAU), Color(0.9, 0.9, 0.9))
			4: B.detail("box", "timber", Batcher.xf(Vector3(x, y + 0.02, z), Vector3(0.11, 0.035, r.randf_range(0.3, 0.9)), r.randf() * TAU), kcol(0.5, 1.1))
			5: B.detail("chip", "litter", Batcher.xf(Vector3(x, y + 0.005, z), Vector3(0.14, 0.006, 0.11), r.randf() * TAU), Color(0.9, 0.9, 0.85))

## RULE. Temporary power and data does not go in a trench: it snakes across the
## pad in a straight-ish line from a source to a load, held down by sandbags.
func _ground_cables() -> void:
	var runs := [[Vector2(-24.0, 4.0), Vector2(-4.0, 2.0)], [Vector2(-12.0, 1.0), Vector2(-1.0, -2.5)],
		[Vector2(-6.0, -20.0), Vector2(-6.0, -2.0)], [Vector2(14.0, 8.0), Vector2(3.0, 3.0)],
		[Vector2(-20.0, -6.0), Vector2(-20.0, 8.0)], [Vector2(0.0, 3.0), Vector2(30.0, 1.0)]]
	for run in runs:
		var a: Vector2 = run[0]
		var b: Vector2 = run[1]
		var n := int(a.distance_to(b) / 0.8)
		var prev := Vector3(a.x, gh(a.x, a.y) + 0.03, a.y)
		for i in range(1, n + 1):
			var t := float(i) / float(n)
			var pp: Vector2 = a.lerp(b, t) + Vector2(sin(t * 9.0) * 0.5, cos(t * 7.0) * 0.5)
			var q := Vector3(pp.x, gh(pp.x, pp.y) + 0.03, pp.y)
			B.detail("cyl6", "rubber", Batcher.beam_xf(prev, q, 0.032, 0.032), Color(0.9, 0.9, 0.9))
			if i % 5 == 0:
				B.detail("box", "litter", Batcher.xf(q + Vector3(0, -0.01, 0), Vector3(0.34, 0.10, 0.22), r.randf() * TAU), Color(0.55, 0.5, 0.42))
			prev = q

# =================================================================== decals
## RULE. Three generated textures - a stain, a track pair, a run - placed by
## rule: stains where machines stand and where drums are, tracks along the haul
## road and the collar approach, runs under every iron edge that sheds water.
func _build_decals(parent: Node3D) -> void:
	var stain := _tex_stain()
	var track := _tex_track()
	var pool := Node3D.new()
	pool.name = "Decals"
	parent.add_child(pool)
	var made := 0
	# oil and drip stains: the yard, the bay, the drum store, the charge row
	var clusters := [Vector3(-19.0, 0, -3.0), Vector3(-22.0, 0, -1.5), Vector3(-20.0, 0, 7.0),
		Vector3(-17.0, 0, 20.0), Vector3(0.0, 0, 0.0), Vector3(11.5, 0, -15.0),
		Vector3(-4.0, 0, -20.0), Vector3(-26.0, 0, -17.0), Vector3(15.0, 0, 10.0)]
	for c in clusters:
		for i in r.randi_range(4, 9):
			var x: float = c.x + r.randf_range(-3.5, 3.5)
			var z: float = c.z + r.randf_range(-3.5, 3.5)
			var d := Decal.new()
			d.texture_albedo = stain
			var s := r.randf_range(0.9, 3.4)
			d.size = Vector3(s, 2.0, s * r.randf_range(0.7, 1.3))
			d.position = Vector3(x, gh(x, z) + 0.6, z)
			d.rotation.y = r.randf() * TAU
			d.modulate = Color(0.10, 0.09, 0.085, 1.0)
			d.albedo_mix = r.randf_range(0.55, 0.95)
			d.distance_fade_enabled = true
			d.distance_fade_begin = 40.0
			d.distance_fade_length = 12.0
			pool.add_child(d)
			made += 1
	# tyre and machine tracks along the haul road and into the collar
	var lines := [[Vector2(-70.0, 4.0), Vector2(-33.0, -2.0)], [Vector2(-33.0, -2.0), Vector2(-6.0, -1.0)],
		[Vector2(-6.0, -1.0), Vector2(-1.0, 2.0)], [Vector2(-24.0, 6.0), Vector2(-8.0, 3.0)],
		[Vector2(4.0, 2.0), Vector2(30.0, 0.5)]]
	for ln in lines:
		var a: Vector2 = ln[0]
		var b: Vector2 = ln[1]
		var n := int(a.distance_to(b) / 3.0)
		for i in n:
			var t := (float(i) + 0.5) / float(n)
			var pp: Vector2 = a.lerp(b, t)
			var d2 := Decal.new()
			d2.texture_albedo = track
			d2.size = Vector3(2.6, 1.6, 3.2)
			d2.position = Vector3(pp.x, gh(pp.x, pp.y) + 0.5, pp.y)
			d2.rotation.y = atan2((b - a).y, (b - a).x) + PI * 0.5
			d2.modulate = Color(0.14, 0.115, 0.085, 1.0)
			d2.albedo_mix = r.randf_range(0.35, 0.7)
			d2.distance_fade_enabled = true
			d2.distance_fade_begin = 35.0
			d2.distance_fade_length = 12.0
			pool.add_child(d2)
			made += 1
	decals.append(made)

func _tex_stain() -> ImageTexture:
	var n := 128
	var img := Image.create(n, n, false, Image.FORMAT_RGBA8)
	var rr := RandomNumberGenerator.new()
	rr.seed = 4242
	for y in n:
		for x in n:
			var u := (float(x) / float(n) - 0.5) * 2.0
			var v := (float(y) / float(n) - 0.5) * 2.0
			var d := sqrt(u * u + v * v)
			var lobe := 0.0
			for k in 5:
				var ax := sin(float(k) * 2.1) * 0.45
				var az := cos(float(k) * 3.7) * 0.45
				var rad := 0.30 + 0.22 * sin(float(k) * 5.3)
				var dd := sqrt((u - ax) * (u - ax) + (v - az) * (v - az))
				lobe = maxf(lobe, 1.0 - dd / rad)
			var a := clampf(lobe, 0.0, 1.0)
			a *= 0.55 + 0.45 * rr.randf()
			a = clampf(a * 1.5 - 0.15, 0.0, 1.0)
			a *= clampf(1.2 - d, 0.0, 1.0)
			img.set_pixel(x, y, Color(1, 1, 1, a))
	return ImageTexture.create_from_image(img)

func _tex_track() -> ImageTexture:
	var n := 128
	var img := Image.create(n, n, false, Image.FORMAT_RGBA8)
	var rr := RandomNumberGenerator.new()
	rr.seed = 909
	for y in n:
		for x in n:
			var u := float(x) / float(n)
			var v := float(y) / float(n)
			var a := 0.0
			for band in [0.28, 0.72]:
				var w := absf(u - band)
				if w < 0.10:
					var tread := 0.55 + 0.45 * sin(v * 42.0 + band * 30.0)
					a = maxf(a, (1.0 - w / 0.10) * tread)
			a *= 0.5 + 0.5 * rr.randf()
			a *= smoothstep(0.0, 0.12, v) * smoothstep(0.0, 0.12, 1.0 - v)
			img.set_pixel(x, y, Color(1, 1, 1, clampf(a, 0.0, 1.0)))
	return ImageTexture.create_from_image(img)
