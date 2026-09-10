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

## LAYOUT queries. DESIGN-PRINCIPLES 7: the ground a machine walks is kept clear
## and swept, and its emptiness is what reads as use. `swept` is the lanes, the
## turning circle and the working aprons; `in_stand` is ground an arrangement
## occupies. Nothing in this file drops anything on either.
func swept(x: float, z: float) -> bool:
	return L.swept(int(x * 1000.0), int(z * 1000.0))

func in_stand(x: float, z: float) -> bool:
	return L.in_stand(int(x * 1000.0), int(z * 1000.0))

## MARGIN. Where debris, weeds and standing water are allowed: off the concrete,
## or within 2.6 m of the pad edge where the sweeper turns round.
func margin(x: float, z: float) -> bool:
	if not on_pad(x, z):
		return true
	var p: Dictionary = L.plan["pads"][0]
	var d := minf(minf(x - float(p["x0"]) / 1000.0, float(p["x1"]) / 1000.0 - x),
		minf(z - float(p["z0"]) / 1000.0, float(p["z1"]) / 1000.0 - z))
	return d < 2.6

func kcol(lo: float = 0.7, hi: float = 1.5) -> Color:
	var v := r.randf_range(lo, hi)
	return Color(v, v * r.randf_range(0.94, 1.0), v * r.randf_range(0.86, 0.98))

func build(parent: Node3D) -> void:
	_gravel()
	_pad_chippings()
	_drifts()
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

## RULE, REWRITTEN FOR DESIGN-PRINCIPLES 7. The old rule put 9 chippings per
## square metre over all 3 224 m2 of hardstanding - 29 000 of them - including
## the lanes, the turning circle and the apron a machine is walked across. Even
## cover is exactly how abandonment is drawn.
##
## Loose stock on concrete now collects in the three places a broom leaves it and
## nowhere else:
##   1. the slab joints, which no sweeper reaches;
##   2. the LEE of an arrangement, in a 0.8 m band outside the stand it hides
##      behind, because that is where the brush stops;
##   3. the margin, the outer 2.6 m of the pad where nothing turns.
## Swept ground gets none. That deletion is the single largest change in the pass
## and it is worth more than everything added.
func _pad_chippings() -> void:
	var p: Dictionary = L.plan["pads"][0]
	var x0 := float(p["x0"]) / 1000.0
	var z0 := float(p["z0"]) / 1000.0
	var x1 := float(p["x1"]) / 1000.0
	var z1 := float(p["z1"]) / 1000.0
	var mod := float(L.plan["slab_module"]) / 1000.0
	# 1. the joint lines, on the 3.6 m module the shader draws
	var jx := ceilf(x0 / mod) * mod
	while jx < x1:
		var m := int((z1 - z0) * 2.2)
		for k in m:
			var z2 := r.randf_range(z0, z1)
			var off := r.randf_range(-0.30, 0.30)
			if swept(jx + off, z2) or in_stand(jx + off, z2):
				continue
			var s2 := r.randf_range(0.02, 0.075)
			B.detail("chip", "gravel", Batcher.xf(Vector3(jx + off, gh(jx + off, z2) - 0.004, z2),
				Vector3(s2, s2 * 0.35, s2), r.randf() * TAU), kcol(0.5, 1.0))
		jx += mod
	var jz := ceilf(z0 / mod) * mod
	while jz < z1:
		var m2 := int((x1 - x0) * 2.2)
		for k2 in m2:
			var x3 := r.randf_range(x0, x1)
			var off2 := r.randf_range(-0.30, 0.30)
			if swept(x3, jz + off2) or in_stand(x3, jz + off2):
				continue
			var s3 := r.randf_range(0.02, 0.075)
			B.detail("chip", "gravel", Batcher.xf(Vector3(x3, gh(x3, jz + off2) - 0.004, jz + off2),
				Vector3(s3, s3 * 0.35, s3), r.randf() * TAU), kcol(0.5, 1.0))
		jz += mod
	# 2. the lee of every arrangement: a 0.8 m band outside the stand
	for st in L.plan["stands"]:
		var sx0 := float(st["x0"]) / 1000.0
		var sz0 := float(st["z0"]) / 1000.0
		var sx1 := float(st["x1"]) / 1000.0
		var sz1 := float(st["z1"]) / 1000.0
		var per := 2.0 * ((sx1 - sx0) + (sz1 - sz0))
		for k3 in int(per * 3.0):
			var t := r.randf() * per
			var e := r.randf_range(0.06, 0.8)
			var q := _perimeter(sx0, sz0, sx1, sz1, t, e)
			if swept(q.x, q.y) or in_stand(q.x, q.y):
				continue
			var s4 := r.randf_range(0.02, 0.09)
			B.detail(["chip", "chip", "rock"][r.randi() % 3], "gravel",
				Batcher.xf(Vector3(q.x, gh(q.x, q.y) - s4 * 0.06, q.y),
					Vector3(s4, s4 * r.randf_range(0.5, 0.9), s4 * r.randf_range(0.7, 1.3)),
					r.randf() * TAU, r.randf_range(-0.3, 0.3), r.randf_range(-0.3, 0.3)), kcol(0.6, 1.3))
	# 3. the margin, the outer band of the pad
	var nm := int((x1 - x0) * (z1 - z0) * 0.9)
	for i in nm:
		var x := r.randf_range(x0, x1)
		var z := r.randf_range(z0, z1)
		if not margin(x, z) or swept(x, z) or in_stand(x, z):
			continue
		var s5 := r.randf_range(0.025, 0.105)
		B.detail(["chip", "chip", "rock", "rock2", "rock3"][r.randi() % 5], "gravel",
			Batcher.xf(Vector3(x, gh(x, z) - s5 * 0.06, z),
				Vector3(s5, s5 * r.randf_range(0.55, 0.95), s5 * r.randf_range(0.7, 1.3)),
				r.randf() * TAU, r.randf_range(-0.3, 0.3), r.randf_range(-0.3, 0.3)), kcol(0.7, 1.5))

## a point at arc length t round a rectangle, pushed e metres outward
func _perimeter(x0: float, z0: float, x1: float, z1: float, t: float, e: float) -> Vector2:
	var w := x1 - x0
	var d := z1 - z0
	if t < w:
		return Vector2(x0 + t, z0 - e)
	t -= w
	if t < d:
		return Vector2(x1 + e, z0 + t)
	t -= d
	if t < w:
		return Vector2(x1 - t, z1 + e)
	t -= d
	return Vector2(x0 - e, clampf(z1 - t, z0, z1))

# =================================================================== drifts
## RULE, REWRITTEN AGAIN FOR THE ICE. The weeds are gone - THE-ICE 7.4: "also
## gone: the puddles (ice, or buried), the weeds in the margins, and the overcast
## lighting rig" - and what replaces them is the thing THE-ICE 7.4 names as the
## expensive half of snow:
##
##   "Snow's silhouette is the known open weakness - materials/NOTES.md 7.4: 'a
##    flat plane with a heightfield on it is still a flat plane. POM gives
##    apparent depth and it works well ... but the silhouette is unchanged, so at
##    grazing the ground shows a clean straight edge.' DRIFTS AND SNOW BANKING
##    AGAINST OBJECTS ARE EXACTLY THE CASE PARALLAX CANNOT DO."
##
## They are, so they are geometry. And the placement rule did not have to be
## invented: the weed rule already knew where the margins are - the fence line,
## behind the buildings, the outer band of the pad, the ground nothing crosses -
## because DESIGN-PRINCIPLES 7 taught it that. The same three placements now
## carry snow banks instead of grass, which is what "re-point it, do not
## re-invent it" means in practice.
##
## AND IT STILL OBEYS "DENSITY IS ORDER, NOT SCATTER", by a route the weeds
## never could. Every drift answers "who put it there and why" with ONE answer -
## THE WIND - so every drift on the site shares one axis, and that shared axis is
## read instantly as a cause. A field of randomly rotated snow lumps would be the
## scrapyard failure in white. Nothing here takes a random yaw.
const WIND := Vector2(0.94, 0.34)

func _drift(pos: Vector3, along: float, l: float, w: float, h: float, salt: int) -> void:
	var m: String = ["rock", "rock2", "rock3"][salt % 3]
	B.detail(m, "snow", Batcher.xf(pos + Vector3(0, h * 0.30, 0),
		Vector3(l, h, w), along), kcol(0.94, 1.06))

## the yaw whose local +X points along a world XZ direction
static func _yaw_of(d: Vector2) -> float:
	return -atan2(d.y, d.x)

func _drifts() -> void:
	var wy := _yaw_of(WIND.normalized())
	var p: Dictionary = L.plan["pads"][0]
	var x0 := float(p["x0"]) / 1000.0
	var z0 := float(p["z0"]) / 1000.0
	var x1 := float(p["x1"]) / 1000.0
	var z1 := float(p["z1"]) / 1000.0

	# --- 1. AT THE FOOT OF THE PERIMETER FENCE. A fence is a snow fence whether
	# anybody meant it to be or not: it stalls the wind and the load drops out
	# on the lee side in one continuous bank. This is the margin the frame is
	# meant to notice, and it is now a metre of white instead of a line of grass.
	var pts: Array = L.plan["fence"]
	for i2 in range(pts.size() - 1):
		var a2 := Vector2(float(pts[i2][0]) / 1000.0, float(pts[i2][1]) / 1000.0)
		var b2 := Vector2(float(pts[i2 + 1][0]) / 1000.0, float(pts[i2 + 1][1]) / 1000.0)
		var run := b2 - a2
		var rl := run.length()
		if rl < 0.5:
			continue
		var dir := run / rl
		var nrm := Vector2(-dir.y, dir.x)
		# the bank is on the lee side, and which side that is depends on the run
		var lee: float = 1.0 if nrm.dot(WIND) > 0.0 else -1.0
		var ryaw := _yaw_of(dir)
		var n2 := int(rl / 2.2)
		for k3 in n2:
			var t := (float(k3) + 0.5) / float(n2)
			var pp: Vector2 = a2.lerp(b2, t)
			var off := nrm * lee * r.randf_range(0.55, 1.5)
			var q := pp + off
			if swept(q.x, q.y):
				continue
			var hgt := r.randf_range(0.30, 0.95)
			_drift(Vector3(q.x, gh(q.x, q.y), q.y), ryaw,
				r.randf_range(2.4, 4.4), r.randf_range(1.4, 2.8), hgt, k3)

	# --- 2. AGAINST THE BUILDINGS. Same rule, and the walls are square to the
	# site grid, so the banks are too. A drift with a straight edge against a
	# wall and a feathered tail away from it is the whole shape.
	for b in L.plan["buildings"]:
		var bx0 := float(b["x0"]) / 1000.0
		var bz0 := float(b["z0"]) / 1000.0
		var bx1 := float(b["x1"]) / 1000.0
		var bz1 := float(b["z1"]) / 1000.0
		var per := 2.0 * ((bx1 - bx0) + (bz1 - bz0))
		for k4 in int(per * 0.55):
			var q2 := _perimeter(bx0, bz0, bx1, bz1, r.randf() * per, r.randf_range(0.35, 1.5))
			if swept(q2.x, q2.y) or in_stand(q2.x, q2.y):
				continue
			# square to the wall it is against, not to the wind: a wall wins
			var horiz := absf(q2.x - bx0) < 0.9 or absf(q2.x - bx1) < 0.9
			_drift(Vector3(q2.x, gh(q2.x, q2.y), q2.y), 0.0 if horiz else PI * 0.5,
				r.randf_range(1.8, 3.6), r.randf_range(1.1, 2.2),
				r.randf_range(0.25, 0.80), k4)

	# --- 3. THE OPEN MARGIN. Long, low, all one way, and the only thing that
	# varies is size. This is the one that makes a wide frame read as WIND.
	var rad := 74.0
	var n := int(PI * rad * rad * 0.020)
	for i in n:
		var a := r.randf() * TAU
		var d := sqrt(r.randf()) * rad
		var x3 := cos(a) * d
		var z3 := sin(a) * d
		if swept(x3, z3) or in_stand(x3, z3):
			continue
		# thinned hard over the swept ground near the collar, exactly as the
		# weeds were, and for exactly the same reason: that ground is worked
		if d < 15.0 and r.randf() < 0.86:
			continue
		if on_pad(x3, z3) and r.randf() < 0.72:
			continue
		var sc := r.randf_range(0.55, 1.9)
		_drift(Vector3(x3, gh(x3, z3), z3), wy + r.randf_range(-0.10, 0.10),
			sc * r.randf_range(3.2, 7.0), sc * r.randf_range(1.3, 2.4),
			sc * r.randf_range(0.16, 0.42), i)

	# --- 4. LAST YEAR'S STEMS, and this is a deliberate retention rather than a
	# leftover. THE-ICE says the weeds go, and green weeds in a working margin
	# do go. Dead stems standing out of a snow bank are a different object: they
	# are the only fine dark thing in a white margin, they are the cheapest scale
	# cue in the frame, and a perfectly clean snowfield is the thing that reads
	# as a render. Twelve per cent of the old count, at the fence line only.
	for i3 in range(pts.size() - 1):
		var a3 := Vector2(float(pts[i3][0]) / 1000.0, float(pts[i3][1]) / 1000.0)
		var b3 := Vector2(float(pts[i3 + 1][0]) / 1000.0, float(pts[i3 + 1][1]) / 1000.0)
		var n3 := int(a3.distance_to(b3) * 0.32)
		for k5 in n3:
			var t2 := (float(k5) + 0.5) / float(n3)
			var pp2: Vector2 = a3.lerp(b3, t2)
			var ox := r.randf_range(-0.9, 0.9)
			var oz := r.randf_range(-0.9, 0.9)
			if swept(pp2.x + ox, pp2.y + oz):
				continue
			var s4 := r.randf_range(0.22, 0.52)
			B.detail("weed", "timber", Batcher.xf(
				Vector3(pp2.x + ox, gh(pp2.x + ox, pp2.y + oz) + s4 * 0.20, pp2.y + oz),
				Vector3(s4 * 0.7, s4, s4 * 0.7), r.randf() * TAU), kcol(0.5, 0.9))

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
		var n := r.randi_range(10, 24)
		for i in n:
			var a := r.randf() * TAU
			var d := sqrt(r.randf()) * 2.4
			var x: float = s2.x + cos(a) * d
			var z: float = s2.y + sin(a) * d
			# a dropped bolt on a lane gets swept up with everything else
			if swept(x, z):
				continue
			var y := gh(x, z)
			var kind := r.randi() % 5
			match kind:
				0: B.detail("hex", "steel", Batcher.xf(Vector3(x, y + 0.007, z), Vector3(0.028, 0.02, 0.028), r.randf() * TAU), kcol(0.5, 1.0))
				1: B.detail("ring", "steel", Batcher.xf(Vector3(x, y + 0.001, z), Vector3(0.045, 0.006, 0.045), r.randf() * TAU), kcol(0.5, 1.0))
				2: B.detail("cyl6", "steel", Batcher.xf(Vector3(x, y + 0.006, z), Vector3(0.018, 0.11, 0.018), r.randf() * TAU, PI * 0.5, r.randf() * TAU), kcol(0.5, 1.0))
				3: B.detail("box", "timber", Batcher.xf(Vector3(x, y + 0.009, z), Vector3(0.09, 0.025, 0.22), r.randf() * TAU), kcol(0.5, 1.1))
				4: B.detail("chip", "iron", Batcher.xf(Vector3(x, y + 0.003, z), Vector3(0.07, 0.02, 0.05), r.randf() * TAU), kcol(0.5, 1.2))

# ================================================================== litter
## RULE, REWRITTEN FOR DESIGN-PRINCIPLES 7: "if the answer to who put it there
## is nobody, it is litter, and litter belongs only in the margins." It used to
## be spread at 0.16 per m2 over the whole pad. It now blows into the lee of the
## fence and the backs of the buildings, which is where wind actually puts it.
func _litter() -> void:
	var spots: Array = []
	var pts: Array = L.plan["fence"]
	for i in range(pts.size() - 1):
		var a2 := Vector2(float(pts[i][0]) / 1000.0, float(pts[i][1]) / 1000.0)
		var b2 := Vector2(float(pts[i + 1][0]) / 1000.0, float(pts[i + 1][1]) / 1000.0)
		var n2 := int(a2.distance_to(b2) * 0.55)
		for k in n2:
			var pp: Vector2 = a2.lerp(b2, (float(k) + 0.5) / float(maxi(n2, 1)))
			spots.append(pp + Vector2(r.randf_range(-1.1, 1.1), r.randf_range(-1.1, 1.1)))
	for b in L.plan["buildings"]:
		var bx0 := float(b["x0"]) / 1000.0
		var bz0 := float(b["z0"]) / 1000.0
		var bx1 := float(b["x1"]) / 1000.0
		var bz1 := float(b["z1"]) / 1000.0
		var per := 2.0 * ((bx1 - bx0) + (bz1 - bz0))
		for k2 in int(per * 0.5):
			spots.append(_perimeter(bx0, bz0, bx1, bz1, r.randf() * per, r.randf_range(0.2, 1.4)))
	for q in spots:
		var x: float = q.x
		var z: float = q.y
		if swept(x, z) or in_stand(x, z):
			continue
		var y := gh(x, z)
		match r.randi() % 6:
			0: B.detail("cyl6", "plastic", Batcher.xf(Vector3(x, y + 0.004, z), Vector3(0.006, 0.16, 0.006), r.randf() * TAU, PI * 0.5, r.randf() * TAU), Color(1.4, 1.4, 1.4))
			1: B.detail("ring", "plastic", Batcher.xf(Vector3(x, y + 0.004, z), Vector3(0.07, 0.008, 0.07), r.randf() * TAU), Color(1.2, 1.2, 1.2))
			2: B.detail("box", "litter", Batcher.xf(Vector3(x, y + 0.004, z), Vector3(r.randf_range(0.08, 0.3), 0.004, r.randf_range(0.08, 0.24)), r.randf() * TAU, r.randf_range(-0.2, 0.2), r.randf_range(-0.2, 0.2)), Color(1.1, 1.1, 1.05))
			3: B.detail("box", "amber", Batcher.xf(Vector3(x, y + 0.006, z), Vector3(0.03, 0.008, 0.5), r.randf() * TAU), Color(0.9, 0.9, 0.9))
			4: B.detail("box", "timber", Batcher.xf(Vector3(x, y + 0.02, z), Vector3(0.11, 0.035, r.randf_range(0.3, 0.9)), r.randf() * TAU), kcol(0.5, 1.1))
			5: B.detail("chip", "litter", Batcher.xf(Vector3(x, y + 0.005, z), Vector3(0.14, 0.006, 0.11), r.randf() * TAU), Color(0.9, 0.9, 0.85))

## RULE. Temporary power and data does not go in a trench: it snakes across the
## pad in a straight-ish line from a source to a load, held down by sandbags.
func _ground_cables() -> void:
	# ORDER PASS. Six runs snaking across the middle of the pad became two that go
	# where a person would run them: the transformer pen to the service bay, and
	# the bay to the charge line. Straight, along the edge of a lane rather than
	# across it, because a cable somebody laid is straight.
	var runs := [[Vector2(-4.0, -18.5), Vector2(-4.0, -9.0)], [Vector2(-28.6, 3.4), Vector2(-28.6, 6.2)]]
	for run in runs:
		var a: Vector2 = run[0]
		var b: Vector2 = run[1]
		var n := int(a.distance_to(b) / 0.8)
		var prev := Vector3(a.x, gh(a.x, a.y) + 0.03, a.y)
		for i in range(1, n + 1):
			var t := float(i) / float(n)
			var pp: Vector2 = a.lerp(b, t) + Vector2(sin(t * 5.0) * 0.10, cos(t * 4.0) * 0.10)
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
	# ORDER PASS. A stain says WORK HAPPENED HERE, so every cluster is now on a
	# thing that is worked: the bench, the service stand, the dock line, the
	# drum bund, the scrap bay, the muster square, the collar.
	var clusters := [Vector3(-20.4, 0, -7.2), Vector3(-13.6, 0, -1.5), Vector3(-10.8, 0, -2.1),
		Vector3(-21.0, 0, 7.0), Vector3(-6.5, 0, 4.0), Vector3(-17.0, 0, 20.0),
		Vector3(23.5, 0, -3.0), Vector3(0.0, 0, 0.0), Vector3(-4.0, 0, -20.0)]
	for c in clusters:
		for i in r.randi_range(3, 7):
			var x: float = c.x + r.randf_range(-2.4, 2.4)
			var z: float = c.z + r.randf_range(-2.4, 2.4)
			var d := Decal.new()
			d.texture_albedo = stain
			var s := r.randf_range(0.9, 3.4)
			d.size = Vector3(s, 2.0, s * r.randf_range(0.7, 1.3))
			d.position = Vector3(x, gh(x, z) + 0.6, z)
			d.rotation.y = r.randf() * TAU
			# UNDER SNOW A STAIN IS NOT BLACK. The yard's oil is still there and
			# it is still where the work is, but it is under a hand of snow, so
			# what shows is a grey bruise where the pad has been walked and the
			# cover is thin - not the 0.10 near-black that read as holes punched
			# in the snowfield. `g_snow` is not readable from GDScript in a game
			# build (the getter is editor-only), so this follows the preset the
			# same way `Weather.wet` does.
			d.modulate = Color(0.30, 0.30, 0.315, 1.0)
			d.albedo_mix = r.randf_range(0.22, 0.46)
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
			# A TRACK IN SNOW IS COMPACTED SNOW, which is DARKER AND BLUER than
			# the snow beside it because the light gets further into it before it
			# comes back out - the same path-length rule as everything else here,
			# used as evidence of traffic. It is not a mud smear.
			d2.modulate = Color(0.40, 0.435, 0.50, 1.0)
			d2.albedo_mix = r.randf_range(0.30, 0.55)
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
