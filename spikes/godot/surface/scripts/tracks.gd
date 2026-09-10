extends RefCounted
class_name Tracks
##
## DRESSING LAYER - what walked on the snow, and where it went.
##
## THE-ICE 7.1, which is the reason this file exists and the reason it should
## have existed before the valley did:
##
##   "Before the town, before the valley, before the terrain: SNOW RECORDS WHAT
##    WALKED ON IT ... A training course in snow shows the machine's own path,
##    every run, as a physical mark on the ground - where it hesitated, where it
##    turned, where it went twice, where it went wrong. That is the single most
##    valuable object the ice decision produces, and it is not an art win, it is
##    a teaching win."
##
## VALLEY.md 8.6 and ACT-ONE.md 8.4 both name its absence as the top item left
## undone, and ACT-ONE is blunter: shot 7 is a machine walking a course in snow
## with UNTOUCHED SNOW BEHIND IT, which is the one frame in the act that
## actively contradicts the design. This is the fix.
##
## WHAT IT IS NOT. It is not the plan's static wear field. `ground.gd` bakes one
## of those from the six walkway polylines, the haul road and the four stations,
## and the snow read it - so a route was drawn if and only if the LAYOUT already
## knew about it. A machine that walks somewhere nobody planned left nothing,
## which is precisely the case the teaching loop is about. This accumulates.
##
## ---------------------------------------------------------------------------
## THE MECHANISM, AND WHY THIS ONE
##
## Four were on the table: a render target the feet write into, a growing
## instanced set of print meshes, a decal buffer, and a field the ground shader
## samples. The answer is the fourth, in TWO layers, and the split is forced by
## the density principle rather than chosen for convenience. DESIGN-PRINCIPLES 4
## asks every environment to carry detail at three scales at once, and a track
## has to read at all three:
##
##   a line across the yard, from sixty metres   -> a FIELD. 40 cm is plenty.
##   individual prints, from two metres          -> needs 1-2 cm of shape.
##   ground crossed a hundred times              -> a COUNTER, not an image.
##
## One buffer cannot serve the first and second at once without being enormous:
## a foot is 130 mm across, so drawing print SHAPE into a texture needs ~15 mm
## texels, and 15 mm over the site box is an 8192-square texture - 67 MB for a
## channel. So:
##
##   `_p` THE PRINT BUFFER, 1024 square over 208 m (203 mm a texel).
##       It does not store the print's picture. It stores the print's IDENTITY:
##       where its centre is to sub-texel precision, which way the foot was
##       pointing, and how deep it went. The GROUND SHADER reconstructs the
##       shape analytically from that, so a 203 mm texel yields a print with a
##       1 mm edge, a rim of displaced snow and a correct normal. One texel is
##       written per footfall - not a splat, one texel - and the newest print in
##       a texel wins, which is also what happens in snow.
##
##   `_k` THE PACK BUFFER, 512 square over 208 m (406 mm a texel).
##       Three saturating counters, splatted over ~0.6 m per footfall:
##         R  compaction - snow pressed to firn. ~24 machine passes to saturate.
##         G  refreeze   - packed, then thawed, then frozen again. ~65.
##         B  dirt       - grit dragged up out of the ground under it. ~89.
##       This is the layer that reads from sixty metres and the layer that says
##       "many times" rather than "once". A field, not a picture, so it costs
##       one bilinear tap.
##
## WHAT IT COSTS. 4 MB + 1 MB of VRAM, fixed, forever - it does not grow with
## the number of prints or the number of agents. Per footfall: one texel write
## and a 3x3 splat, about thirty byte operations, which is nothing. In the
## ground shader: one bilinear tap always, and nine texelFetches inside 16 m
## where individual prints can actually be resolved. See VALLEY.md for the
## measured numbers.
##
## DOES IT SURVIVE TWENTY AGENTS? The buffers are fixed-size and shared, so
## twenty agents cost exactly what one costs to STORE and to READ. What scales
## with agent count is the write path, and here it is a CPU write plus a whole
## texture upload on any frame a foot lands - 5 MB, which is fine for offline
## capture at 0.8 s a frame and is NOT fine at sixty. The production form of the
## same design writes the stamps on the GPU (one instanced quad per new footfall
## into a render target with clear-mode never), which is O(new footfalls) and
## uploads nothing. That is a different fifty lines, not a different design: the
## buffers, the encoding and the whole of the shader are unchanged. Flagged.

# ------------------------------------------------------------------ the window
## The site box is x -78..96, z -74..74. This is that plus ~30 m of margin, and
## it is a fixed window rather than one that follows the camera because the
## pit-head does not move and a scrolling window has a seam.
const SPAN := 208.0
const CX := 9.0
const CZ := 0.0
const OX := CX - SPAN * 0.5      # -95
const OZ := CZ - SPAN * 0.5      # -104
const PN := 1024                 # print buffer edge, texels. 203 mm a texel.
const KN := 512                  # pack buffer edge, texels. 406 mm a texel.

const PT := SPAN / float(PN)     # print texel, metres
const KT := SPAN / float(KN)     # pack texel, metres

## How far a splat reaches, metres, and the three counter rates.
##
## MEASURED AND THEN RE-DERIVED, because the first set was four times too hot
## and it destroyed the thing the file is for. At 0.15 a texel saturated in
## about seven crossings, so every route in the plan came back at 1.0 - which
## means the snow was cleared off ALL of them, which means there was nothing for
## a print to be in, and the yard went back to looking exactly as it did before.
## Saturating a counter throws away the only information it has.
##
## The arithmetic, and it was got wrong once by a factor of four. A texel on the
## line is inside the splat of every footfall within 620 mm of it, and a walking
## Surveyor lays 12.7 footfalls a metre - so that is about SIXTEEN footfalls a
## pass, not four, at a mean splat weight of ~0.35. A texel therefore gains
## ~5.5 x K a machine pass.
##
## At 0.0077 a walkway walked eighteen times reads 0.76, a course branch walked
## twelve reads 0.51 and a turn-back walked four reads 0.17 - which is the RANGE
## the picture needs, because "crossed a hundred times" only means anything next
## to "crossed twice". The first two attempts both saturated everything to 1.0
## and the yard came back looking exactly as it had before.
const SPLAT_R := 0.62
const K_PACK := 0.0077
const K_FREEZE := 0.0028
const K_DIRT := 0.0021

static var _p := PackedByteArray()
static var _k := PackedByteArray()
static var _ptex: ImageTexture = null
static var _ktex: ImageTexture = null
static var _dirty := true
static var n_print := 0
static var n_out := 0
static var stamp_us := 0
static var up_us := 0
static var up_n := 0


static var _dith := 0x2545F491

## round `v` to an integer, carrying the fraction as a probability. Deterministic
## per run - it is one xorshift, not `randf()` - so a seed still reproduces.
static func _q(v: float) -> int:
	var i := int(v)
	_dith ^= (_dith << 13) & 0x7FFFFFFF
	_dith ^= _dith >> 17
	_dith ^= (_dith << 5) & 0x7FFFFFFF
	if float(_dith & 0xFFFF) / 65536.0 < v - float(i):
		i += 1
	return i


static func reset() -> void:
	_p = PackedByteArray()
	_p.resize(PN * PN * 4)
	_p.fill(0)
	_k = PackedByteArray()
	_k.resize(KN * KN * 4)
	_k.fill(0)
	_ptex = null
	_ktex = null
	_dirty = true
	n_print = 0
	n_out = 0
	_dith = 0x2545F491
	stamp_us = 0
	up_us = 0
	up_n = 0


# ------------------------------------------------------------------ one footfall
## Mark the snow at (x, z) with a foot pointing along `yaw`, pressed `depth`
## metres in. This is the whole write API and everything else in the file is a
## way of calling it more times.
static func foot(x: float, z: float, yaw: float, depth: float) -> void:
	var fx := (x - OX) / PT
	var fz := (z - OZ) / PT
	if fx < 0.5 or fz < 0.5 or fx >= float(PN) - 0.5 or fz >= float(PN) - 0.5:
		n_out += 1
		return
	var ix := int(fx)
	var iz := int(fz)
	# THE SUB-TEXEL OFFSET IS THE WHOLE TRICK. The texel says "a print is near
	# here"; these two bytes say where, to 0.8 mm. The shader rebuilds the print
	# about that point, so the print's edge is analytic and the buffer's own
	# resolution never appears in the picture.
	var ox := fx - float(ix)
	var oz := fz - float(iz)
	var o := (iz * PN + ix) * 4
	_p[o] = int(clampf(ox, 0.0, 1.0) * 255.0)
	_p[o + 1] = int(clampf(oz, 0.0, 1.0) * 255.0)
	# yaw wrapped to 0..2pi. A ball foot is nearly round, so this only has to
	# carry which way the print was DRAGGED, and half a degree is ample.
	var yw := fposmod(yaw, TAU) / TAU
	_p[o + 2] = int(clampf(yw, 0.0, 0.999) * 255.0)
	_p[o + 3] = maxi(_p[o + 3] / 6, int(clampf(depth / 0.075, 0.06, 1.0) * 255.0))

	# --- the pack layer: three saturating counters over ~0.6 m
	var kx := (x - OX) / KT
	var kz := (z - OZ) / KT
	var r := SPLAT_R / KT
	var x0 := maxi(int(kx - r), 0)
	var x1 := mini(int(kx + r) + 1, KN - 1)
	var z0 := maxi(int(kz - r), 0)
	var z1 := mini(int(kz + r) + 1, KN - 1)
	for jz in range(z0, z1 + 1):
		var dz := (float(jz) + 0.5 - kz) / r
		for jx in range(x0, x1 + 1):
			var dx := (float(jx) + 0.5 - kx) / r
			var q := dx * dx + dz * dz
			if q >= 1.0:
				continue
			var w := (1.0 - q) * (1.0 - q)
			var b := (jz * KN + jx) * 4
			# DITHERED, and it has to be. A counter that rises 0.011 per pass is
			# 2.8 of 255, and the outer half of every splat is under 1 - so
			# truncating to an integer rounds the whole margin of every track to
			# zero and the field comes back as a hard-edged core with no
			# feathering, which is the one thing a footpath in snow does not
			# have. Carrying the fraction as a probability puts the expectation
			# back where it belongs and costs one xorshift.
			_k[b] = mini(255, _k[b] + _q(K_PACK * w * 255.0))
			_k[b + 1] = mini(255, _k[b + 1] + _q(K_FREEZE * w * 255.0))
			_k[b + 2] = mini(255, _k[b + 2] + _q(K_DIRT * w * 255.0))
	n_print += 1
	_dirty = true


# ------------------------------------------------------------------ the gait
## Learn the machine's own gait off its own skeleton, once.
##
## NOTHING HERE IS A GUESSED NUMBER. `machine.gd` measures each foot as the
## lowest vertex weighted to its tibia, and the walk clip is baked in place at
## `Book.speed`, so stepping the clip through one period and reading where each
## foot actually is gives the stance phase and the stance offset exactly. That
## is the gait. Replaying it along a path is then arithmetic, which is what
## makes six hundred metres of history affordable.
##
## Returns {"period", "speed", "stride", "plants": [{"phase", "off": Vector2}]}
static func learn(m) -> Dictionary:
	if m == null or m.legs.is_empty():
		return {}
	var lib: AnimationLibrary = m.anim.get_animation_library("")
	if lib == null or not lib.has_animation("walk"):
		return {}
	var period: float = lib.get_animation("walk").length
	var speed: float = Book.speed(m.chassis, "walk")
	if period <= 0.001 or speed <= 0.001:
		return {}

	var save_clip: String = m.clip
	var save_ground: Callable = m.ground
	var save_xf: Transform3D = m.global_transform
	var save_t: float = m.t
	m.ground = Callable()
	m.global_transform = Transform3D.IDENTITY
	m.set_clip("walk")

	var NS := 72
	var nl: int = m.legs.size()
	# FLAT, and it has to be. A PackedFloat32Array is a VALUE in GDScript, so
	# `arr_of_arrays[i].append(v)` appends to a copy and throws the value away -
	# which is a silent empty array and an out-of-bounds read two loops later.
	var lifts := PackedFloat32Array()
	var offs := PackedVector2Array()
	lifts.resize(NS * nl)
	offs.resize(NS * nl)
	for s in NS:
		m.anim.seek(period * float(s) / float(NS), true)
		m._post_pose()
		for li in nl:
			var w: Vector3 = m._foot_world(m.legs[li])
			lifts[li * NS + s] = w.y
			offs[li * NS + s] = Vector2(w.x, w.z)

	var plants: Array = []
	for li in nl:
		var ly := PackedFloat32Array()
		var lo := PackedVector2Array()
		ly.resize(NS)
		lo.resize(NS)
		for s in NS:
			ly[s] = lifts[li * NS + s]
			lo[s] = offs[li * NS + s]
		var lo_y := 1e9
		for s in NS:
			lo_y = minf(lo_y, ly[s])
		# the stance is the contiguous run of samples within 12 mm of the
		# lowest the foot ever goes. It wraps, so start from a sample that is
		# definitely IN the air and walk forward.
		var hi := 0
		var best := -1e9
		for s in NS:
			if ly[s] > best:
				best = ly[s]
				hi = s
		var run: Array = []
		var cur: Array = []
		for k in NS:
			var s: int = (hi + k) % NS
			if ly[s] < lo_y + 0.012:
				cur.append(s)
			else:
				if cur.size() > run.size():
					run = cur
				cur = []
		if cur.size() > run.size():
			run = cur
		if run.is_empty():
			continue
		var mid: int = run[run.size() / 2]
		plants.append({"phase": float(mid) / float(NS),
			"off": Vector2(lo[mid].x, lo[mid].y)})

	m.set_clip(save_clip)
	m.ground = save_ground
	m.global_transform = save_xf
	m.t = save_t
	m.anim.seek(save_t, true)
	m._post_pose()
	return {"period": period, "speed": speed, "stride": speed * period,
		"plants": plants}


## Every footfall a machine with this gait makes walking `pts` once, starting at
## gait phase `ph0`, offset `lat` metres to the side of the line. Stamps them.
##
## `d0` and `d1` bound the arc length actually walked, which is what lets a shot
## stamp only the part of its own path that has happened SO FAR.
static func walk(gait: Dictionary, pts: PackedVector2Array, ph0: float,
		lat: float, depth: float, d0: float, d1: float) -> int:
	if gait.is_empty() or pts.size() < 2:
		return 0
	var stride: float = gait["stride"]
	var plants: Array = gait["plants"]
	# arc length table
	var cum := PackedFloat32Array()
	cum.resize(pts.size())
	cum[0] = 0.0
	for i in range(1, pts.size()):
		cum[i] = cum[i - 1] + pts[i].distance_to(pts[i - 1])
	var total: float = cum[cum.size() - 1]
	var lo := maxf(d0, 0.0)
	var hi := minf(d1, total)
	if hi <= lo:
		return 0
	var made := 0
	var seg := 0
	for pl in plants:
		var ph: float = float(pl["phase"])
		var off: Vector2 = pl["off"]
		var k0: int = int(floor((lo / stride) - ph + ph0)) - 1
		var k: int = k0
		while true:
			var d: float = (float(k) + ph - ph0) * stride
			k += 1
			if d < lo:
				continue
			if d > hi:
				break
			# where on the polyline, and which way it is going
			while seg < pts.size() - 2 and cum[seg + 1] < d:
				seg += 1
			var s := seg
			while s > 0 and cum[s] > d:
				s -= 1
			var span: float = maxf(cum[s + 1] - cum[s], 0.0001)
			var t: float = clampf((d - cum[s]) / span, 0.0, 1.0)
			var pos: Vector2 = pts[s].lerp(pts[s + 1], t)
			var dir: Vector2 = (pts[s + 1] - pts[s]).normalized()
			# the machine's own frame: forward is +X, lateral is +Z, and the
			# world yaw fleet.gd gives a walking machine is atan2(-dz, dx).
			var yaw: float = atan2(-dir.y, dir.x)
			var cs := cos(yaw)
			var sn := sin(yaw)
			var side := Vector2(sn, cs)          # machine +Z in world XZ
			# A MACHINE DOES NOT WALK A STRAIGHT LINE AND ITS FEET DO NOT LAND ON A
			# LATTICE. The first version replayed the gait exactly, and eighteen
			# passes down a walkway came back as four perfectly parallel rows of
			# evenly spaced dots - a conveyor, not a track. Two wobbles fix it: a
			# slow WANDER of the whole pass across the line, because nobody walks a
			# line twice the same way, and a per-footfall scatter of about a foot's
			# width, which is what a leg does when it is placing on broken ground.
			var wander: float = 0.42 * sin(d * 0.21 + ph0 * 31.0) \
				+ 0.20 * sin(d * 0.63 + ph0 * 71.0 + 1.7)
			var j := _jit()
			var w: Vector2 = pos + side * (lat + wander + j.x * 0.075) \
				+ dir * (j.y * 0.055) \
				+ Vector2(off.x * cs + off.y * sn, -off.x * sn + off.y * cs)
			foot(w.x, w.y, yaw + j.x * 0.22, depth * (0.80 + 0.44 * absf(j.y)))
			made += 1
	return made


# ------------------------------------------------------------------ the history
## THE YARD HAS A PAST, and this is where it comes from.
##
## DESIGN-PRINCIPLES 7: "clear ground is a feature - traffic lanes, turning
## circles, the apron in front of a bay and the ground a machine walks are kept
## clear, and their emptiness reads as use." In snow that emptiness has to be
## MADE by something, and the only honest maker is feet. So every route the plan
## knows about gets walked, at build, by the real gait, the right number of
## times - and then the course gets walked the way a course is walked, which is
## the part the static wear field could never express.
##
## The pass counts are guesses and they are the only guesses in this file.
static func history(L: SurfaceLayout, gait: Dictionary) -> Dictionary:
	if gait.is_empty():
		return {"prints": 0, "ms": 0.0}
	var t0 := Time.get_ticks_usec()
	var rng := RandomNumberGenerator.new()
	rng.seed = L.seed_v * 2654435761 + 90210
	var n0 := n_print

	# --- 1. the walkways. People and machines, both ways, for a season.
	var ww: Array = []
	for w in L.plan["walkways"]:
		ww.append(PackedVector2Array([
			Vector2(float(w[0][0]) * 0.001, float(w[0][1]) * 0.001),
			Vector2(float(w[1][0]) * 0.001, float(w[1][1]) * 0.001)]))
	for line in ww:
		for i in 18:
			walk(gait, line, rng.randf(), rng.randf_range(-0.40, 0.40),
				rng.randf_range(0.030, 0.052), 0.0, 1e9)

	# --- 2. the haul road. Wider, so the spread is wider; it is the way out.
	var rp: Array = L.plan["road"]
	var road := PackedVector2Array()
	for p in rp:
		road.append(Vector2(float(p[0]) * 0.001, float(p[1]) * 0.001))
	for i in 22:
		walk(gait, road, rng.randf(), rng.randf_range(-1.70, 1.70),
			rng.randf_range(0.028, 0.048), 0.0, 1e9)

	# --- 3. the stations and the collar. A machine that stops somewhere mills
	#        about; that is a patch of beaten ground, not a line.
	var spots: Array = [Vector2(0.0, 0.0)]
	for st in L.plan["stations"]:
		spots.append(Vector2(float(st["x"]) * 0.001, float(st["z"]) * 0.001))
	for sp in spots:
		for i in 14:
			var a := rng.randf() * TAU
			var b := a + rng.randf_range(1.4, 4.6)
			var r1 := rng.randf_range(1.0, 4.2)
			var r2 := rng.randf_range(1.0, 4.2)
			walk(gait, PackedVector2Array([
					sp + Vector2(cos(a), sin(a)) * r1,
					sp + Vector2(cos(a * 0.5 + b * 0.5), sin(a * 0.5 + b * 0.5)) * 0.6,
					sp + Vector2(cos(b), sin(b)) * r2]),
				rng.randf(), 0.0, rng.randf_range(0.034, 0.058), 0.0, 1e9)

	# --- 4. THE COURSE, AND THIS IS THE ONE THAT MATTERS.
	#
	# THE-ICE 7.1's whole claim is that a training course in snow SHOWS THE
	# POLICY: where it went twice, where it turned back, where it went wrong. A
	# distance field from the plan cannot say any of that, because the plan does
	# not contain a policy. What a course is walked like is: root to a leaf,
	# again, again; and into some branches only as far as the threshold, and
	# then back out, because that is what being taught not to go somewhere looks
	# like from above.
	var C: Dictionary = L.plan["course"]
	var pitch: float = float(C["pitch"]) * 0.001
	var ox: float = float(C["ox"]) * 0.001
	var oz: float = float(C["oz"]) * 0.001
	var nodes: Array = C["nodes"]
	var edges: Array = C["edges"]
	var np: Array = []
	for n in nodes:
		np.append(Vector2(ox + float(n[0]) * pitch, oz + float(n[1]) * pitch))
	# parent of each node, from the edge list, so a root-to-node path is a walk
	# up the parents.
	var par: Array = []
	for i in nodes.size():
		par.append(-1)
	for e in edges:
		par[int(e[1])] = int(e[0])

	var leaves: Array = C["leaves"]
	for li in leaves.size():
		var leaf: int = int(leaves[li])
		var path := _up(par, np, leaf)
		if path.size() < 2:
			continue
		# the taught route: walked whole, many times, both ways
		var runs: int = 9 if li == 0 else (6 if int(C["cargo_leaf"]) == leaf else 3)
		for i in runs:
			walk(gait, path, rng.randf(), rng.randf_range(-0.30, 0.30),
				rng.randf_range(0.032, 0.055), 0.0, 1e9)
			walk(gait, _rev(path), rng.randf(), rng.randf_range(-0.30, 0.30),
				rng.randf_range(0.032, 0.055), 0.0, 1e9)

	# THE TURN-BACKS. Two thirds of the way down a branch and then out again,
	# four or five times, which draws a stub with a beaten circle on the end of
	# it - a threshold a machine was taught to stop at. This is the single most
	# legible thing in the whole file and it is nine lines.
	for i in nodes.size():
		if i == 0 or par[i] < 0:
			continue
		if rng.randf() > 0.42:
			continue
		var path := _up(par, np, i)
		if path.size() < 2:
			continue
		var ln := _len(path)
		var stop: float = ln * rng.randf_range(0.55, 0.80)
		for k in rng.randi_range(3, 6):
			walk(gait, path, rng.randf(), rng.randf_range(-0.26, 0.26),
				rng.randf_range(0.034, 0.056), 0.0, stop)
			walk(gait, _rev(path), rng.randf(), rng.randf_range(-0.26, 0.26),
				rng.randf_range(0.034, 0.056), ln - stop, 1e9)

	return {"prints": n_print - n0,
		"ms": float(Time.get_ticks_usec() - t0) / 1000.0}


## two signed pseudo-randoms in -1..1 off the same xorshift the dither uses
static func _jit() -> Vector2:
	_dith ^= (_dith << 13) & 0x7FFFFFFF
	_dith ^= _dith >> 17
	_dith ^= (_dith << 5) & 0x7FFFFFFF
	var a := float(_dith & 0xFFFF) / 32768.0 - 1.0
	var b := float((_dith >> 8) & 0xFFFF) / 32768.0 - 1.0
	return Vector2(a, b)


static func _up(par: Array, np: Array, i: int) -> PackedVector2Array:
	var chain: Array = []
	var g := 0
	while i >= 0 and g < 64:
		chain.append(i)
		i = int(par[i])
		g += 1
	chain.reverse()
	var out := PackedVector2Array()
	for c in chain:
		out.append(np[int(c)])
	return out


static func _rev(p: PackedVector2Array) -> PackedVector2Array:
	var o := PackedVector2Array()
	for i in range(p.size() - 1, -1, -1):
		o.append(p[i])
	return o


static func _len(p: PackedVector2Array) -> float:
	var d := 0.0
	for i in range(1, p.size()):
		d += p[i].distance_to(p[i - 1])
	return d


# ------------------------------------------------------------------ the seam
static func upload() -> void:
	if not _dirty and _ptex != null:
		return
	var t0 := Time.get_ticks_usec()
	var pi := Image.create_from_data(PN, PN, false, Image.FORMAT_RGBA8, _p)
	var ki := Image.create_from_data(KN, KN, false, Image.FORMAT_RGBA8, _k)
	if _ptex == null:
		_ptex = ImageTexture.create_from_image(pi)
		_ktex = ImageTexture.create_from_image(ki)
	else:
		_ptex.update(pi)
		_ktex.update(ki)
	_dirty = false
	up_us += Time.get_ticks_usec() - t0
	up_n += 1


static func bind(mat: ShaderMaterial) -> void:
	upload()
	mat.set_shader_parameter("trk_print", _ptex)
	mat.set_shader_parameter("trk_pack", _ktex)
	# x0, z0, 1/span, print texels per edge
	mat.set_shader_parameter("trk_win", Vector4(OX, OZ, 1.0 / SPAN, float(PN)))


static func report() -> String:
	return "tracks         : %d prints, %d outside the window, %.1f MB, %d uploads" \
		% [n_print, n_out, float(PN * PN * 4 + KN * KN * 4) / 1048576.0, up_n]
