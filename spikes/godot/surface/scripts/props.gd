extends RefCounted
class_name Props
##
## DRESSING LAYER - THE BROUGHT. The players' technology, which lives up here.
##
## DESIGN-PRINCIPLES 4: "if the world contains autonomous walkers, something in
## the world has to have built and serviced them. That evidence is the surface's
## job and it must be visible." Everything in this file is that evidence: the
## bay, the bench, the handling gear, the power, the antennas, the cases, and
## the machines themselves standing in the yard.
##
## The register is deliberate: chamfered edges, pale and grey and galvanised,
## labelled panels, small warm pilots at strength <= 3, and every piece of it
## small enough to be dwarfed by the iron it is bolted to.

var L: SurfaceLayout
var B: Batcher
var r: RandomNumberGenerator
var lights: Array = []      # [pos, colour, energy, range] for the dusk preset
## Where a machine STANDS. Filled by _machines(); Fleet turns each entry into a
## real chassis out of the shared machine layer. Until 2026-09-09 this file also
## BUILT the machine, out of 34 batched boxes -- see the note over _walker().
var machine_slots: Array = []

func _init(p_L: SurfaceLayout, p_B: Batcher) -> void:
	L = p_L
	B = p_B
	r = RandomNumberGenerator.new()
	r.seed = L.seed_v * 104729 + 7

func gh(x: float, z: float) -> float:
	return float(L.ground_mm(int(x * 1000.0), int(z * 1000.0))) / 1000.0

func kcol(lo: float = 0.84, hi: float = 1.08) -> Color:
	var v := r.randf_range(lo, hi)
	return Color(v, v, v * r.randf_range(0.97, 1.03))

func ircol(lo: float = 0.55, hi: float = 2.0) -> Color:
	var v := r.randf_range(lo, hi)
	return Color(v * 1.02, v * 0.95, v * 0.88)

func build() -> void:
	_markings()
	_service_bay()
	_gantry()
	_charge_row()
	_containers()
	_tanks()
	_transformer()
	_comms_mast()
	_zone_clutter()
	_arrangements()
	_margin_tips()
	_machines()
	_signage()

# ============================================================= markings
## RULE, and it is the cheapest thing in this file. DESIGN-PRINCIPLES 7: "clear
## ground is a feature ... their emptiness reads as use". Emptiness only reads as
## use if something says the emptiness is deliberate, so every route the LAYOUT
## declares gets painted: an edge line each side of all six walkways, and a
## turning circle round the collar. Sixty-odd instances, and they are the single
## strongest signal in the frame that somebody runs this yard.
func _markings() -> void:
	var hw := float(L.plan["walkway_w"]) / 2000.0
	var cr0: Dictionary = L.plan["clear_r"][0]
	var turn := float(cr0["r"]) / 1000.0 - 0.4
	for w in L.plan["walkways"]:
		var a := Vector2(float(w[0][0]) / 1000.0, float(w[0][1]) / 1000.0)
		var b := Vector2(float(w[1][0]) / 1000.0, float(w[1][1]) / 1000.0)
		var d := (b - a).normalized()
		var n := Vector2(-d.y, d.x)
		var ln := (b - a).length()
		# DASHED, on a 1.2 m mark / 0.9 m gap, and stopping at the turning circle
		# rather than running into it - six lane lines converging on one point is
		# a starburst, and a real yard bounds the circle and leads off it.
		var step := 2.1
		var m := int(ln / step)
		for k in m:
			var t0 := step * float(k) + 0.45
			var t1 := t0 + 1.2
			if t1 > ln:
				break
			for sgn in [-1.0, 1.0]:
				var pa: Vector2 = a + d * t0 + n * hw * sgn
				var pb: Vector2 = a + d * t1 + n * hw * sgn
				if ((pa + pb) * 0.5).length() < turn:
					continue
				_paint_line(pa, pb, 0.17)
	# the turning circle at the collar: 40 chords, painted, on the radius the
	# layout keeps clear. Nothing stands inside it and nothing collects on it.
	var cr: Dictionary = L.plan["clear_r"][0]
	var rad := float(cr["r"]) / 1000.0 - 0.6
	var segs := 40
	for i in segs:
		var a0 := TAU * float(i) / float(segs)
		var a1 := TAU * float(i + 1) / float(segs)
		_paint_line(Vector2(cos(a0), sin(a0)) * rad, Vector2(cos(a1), sin(a1)) * rad, 0.19)

## one painted stripe on the ground, from a to b. SITE bucket: a lane that stops
## existing at 55 m is not a lane.
func _paint_line(a: Vector2, b: Vector2, w: float) -> void:
	var mid := (a + b) * 0.5
	var y := gh(mid.x, mid.y) + 0.012
	var d := b - a
	B.add("box", "paint", Batcher.xf(Vector3(mid.x, y, mid.y),
		Vector3(d.length(), 0.012, w), -atan2(d.y, d.x)), Color(0.92, 0.88, 0.78), Batcher.SITE)

## a painted rectangle outline, centred, in the stand frame
func _paint_rect(c: Vector3, u: Vector3, v: Vector3, ln: float, dp: float, yaw: float, col: Color) -> void:
	for s in [-1.0, 1.0]:
		B.add("box", "paint", Batcher.xf(c + v * (dp * 0.5 * s) + Vector3(0, 0.012, 0),
			Vector3(ln, 0.012, 0.10), yaw), col, Batcher.SITE)
		B.add("box", "paint", Batcher.xf(c + u * (ln * 0.5 * s) + Vector3(0, 0.012, 0),
			Vector3(0.10, 0.012, dp), yaw), col, Batcher.SITE)

# ============================================================ arrangements
## DESIGN-PRINCIPLES 7. Placement is ARRANGEMENTS, not scatter.
##
## LAYOUT has already decided where every stand is, how big it is and which way
## it faces (`plan["stands"]`, cut out of `plan["ranks"]` by an integer rule).
## This half decides WHAT is in one. Randomness reaches exactly two decisions:
## which arrangement fills a stand, and what that arrangement holds. It never
## touches the position or the angle of an individual object - inside an
## arrangement everything is on a fixed pitch and square to the stand, with at
## most two degrees of deliberate jitter where a real pallet would be off square.
##
## Each arrangement therefore answers "who put it there and why" by construction:
## a rack was racked, a row was ranked, a bay was marked out and parked in.
##
## | arrangement      | class | footprint          | pitch  | holds |
## |------------------|-------|--------------------|--------|-------|
## | rack_run         | 0     | 3.6-8.4 x 3.0-4.5  | 2.4 m  | one kind: totes, palletised loads OR long stock |
## | stillage_block   | 0     | as the stand       | 1.35 x 1.15 | mesh stillages, back row stacked two high |
## | pallet_row       | 0     | as the stand       | 1.35 m | identical banded loads, 2-4 high |
## | pipe_laydown     | 1     | as the stand       | bearers at 1/4 | pipe, ends flush, chocked |
## | section_laydown  | 1     | as the stand       | bearers at 1/4 | rolled sections, packed and banded |
## | plate_laydown    | 1     | as the stand       | 0.14 m | plate, edges flush, corner marked |
## | bunded_drums     | 2     | as the stand, kerbed | 0.78 m grid | drums, upright, all one way |
## | bottle_rack      | 2     | as the stand       | 1.9 m  | identical gas cages, chained |
## | reel_stand       | 2     | as the stand       | 2.6 m  | cable reels on a common shaft |
## | marked_bay       | 3     | as the stand, painted | -   | one squarely parked item, or nothing |
## | trolley_queue    | 3     | as the stand       | 1.7 m  | identical trolleys nose to tail |
## | skip_bay         | 3     | as the stand, kerbed | -    | one skip. THE ONLY place random angles are allowed |
const ARR_BY_CLASS := [
	["rack_run", "stillage_block", "pallet_row"],
	["pipe_laydown", "section_laydown", "plate_laydown"],
	["bunded_drums", "bottle_rack", "reel_stand"],
	["marked_bay", "trolley_queue", "skip_bay"]]

func _arrangements() -> void:
	var y := L.pad_h() / 1000.0
	var stands: Array = L.plan["stands"]
	for i in stands.size():
		var st: Dictionary = stands[i]
		var x0 := float(st["x0"]) / 1000.0
		var z0 := float(st["z0"]) / 1000.0
		var x1 := float(st["x1"]) / 1000.0
		var z1 := float(st["z1"]) / 1000.0
		var along_x: bool = int(st["yaw"]) == 0
		var yaw := 0.0 if along_x else -PI * 0.5
		var u := Vector3(cos(yaw), 0.0, -sin(yaw))
		var v := Vector3(sin(yaw), 0.0, cos(yaw))
		var c := Vector3((x0 + x1) * 0.5, y, (z0 + z1) * 0.5)
		var ln := (x1 - x0) if along_x else (z1 - z0)
		var dp := (z1 - z0) if along_x else (x1 - x0)
		var tbl: Array = ARR_BY_CLASS[int(st["cls"])]
		_arrange(tbl[r.randi() % tbl.size()], c, u, v, ln, dp, yaw)

func _arrange(kind: String, c: Vector3, u: Vector3, v: Vector3, ln: float, dp: float, yaw: float) -> void:
	match kind:
		"rack_run":     _arr_rack(c, u, v, ln, dp, yaw)
		"stillage_block": _arr_stillage(c, u, v, ln, dp, yaw)
		"pallet_row":   _arr_pallets(c, u, v, ln, dp, yaw)
		"pipe_laydown": _arr_laydown(c, u, v, ln, dp, yaw, 0)
		"section_laydown": _arr_laydown(c, u, v, ln, dp, yaw, 1)
		"plate_laydown": _arr_plates(c, u, v, ln, dp, yaw)
		"bunded_drums": _arr_bund(c, u, v, ln, dp, yaw)
		"bottle_rack":  _arr_bottles(c, u, v, ln, dp, yaw)
		"reel_stand":   _arr_reels(c, u, v, ln, dp, yaw)
		"marked_bay":   _arr_marked(c, u, v, ln, dp, yaw)
		"trolley_queue": _arr_trolleys(c, u, v, ln, dp, yaw)
		"skip_bay":     _arr_skip(c, u, v, ln, dp, yaw)

## a bay-number plate on a post, at the head of an arrangement. Every stand gets
## one: it is the object that says a person numbered this bay.
func _bay_plate(c: Vector3, u: Vector3, v: Vector3, ln: float, dp: float, yaw: float) -> void:
	var p := c - u * (ln * 0.5 + 0.35) + v * (dp * 0.5 - 0.2)
	B.prop("cyl", "galv", Batcher.xf(p + Vector3(0, 0.62, 0), Vector3(0.05, 1.24, 0.05), yaw), kcol())
	B.prop("box", "bone", Batcher.xf(p + Vector3(0, 1.16, 0), Vector3(0.34, 0.26, 0.014), yaw), kcol(0.85, 1.0))
	B.detail("box", "kitgrey", Batcher.xf(p + Vector3(0, 1.16, 0) + u * 0.009, Vector3(0.2, 0.09, 0.004), yaw), Color(0.55, 0.55, 0.55))

# --- 0 stores ---------------------------------------------------------------
## RULE. Uprights on the 2.4 m module both sides, three beam levels, and ONE kind
## of stock repeated in every bay. The repetition is the point: identical units
## in an aligned row say somebody built these (DESIGN-PRINCIPLES 7).
func _arr_rack(c: Vector3, u: Vector3, v: Vector3, ln: float, dp: float, yaw: float) -> void:
	var bays := maxi(1, int(ln / 2.4))
	var pitch := ln / float(bays)
	var vv := dp * 0.5 - 0.42
	for i in range(bays + 1):
		var a := c + u * (-ln * 0.5 + pitch * float(i))
		for sgn in [-1.0, 1.0]:
			B.prop("angle", "ember", Batcher.xf(a + v * (vv * sgn) + Vector3(0, 1.62, 0),
				Vector3(0.10, 3.24, 0.10), yaw), kcol(0.62, 0.88))
	for lvl in 3:
		var ly := 0.52 + 1.0 * float(lvl)
		for sgn2 in [-1.0, 1.0]:
			B.prop("box", "ember", Batcher.xf(c + v * (vv * sgn2) + Vector3(0, ly, 0),
				Vector3(ln, 0.10, 0.09), yaw), kcol(0.62, 0.88))
	var hold := r.randi() % 3
	var tone := kcol(0.82, 1.0)
	for i2 in bays:
		var bc := c + u * (-ln * 0.5 + pitch * (float(i2) + 0.5))
		for lvl2 in 3:
			var ly2 := 0.57 + 1.0 * float(lvl2)
			if hold == 0:
				for k in 3:
					B.prop("casebox", "bone" if k != 1 else "kitgrey",
						Batcher.xf(bc + u * (-0.62 + 0.62 * float(k)) + Vector3(0, ly2 + 0.23, 0),
							Vector3(0.54, 0.44, minf(dp - 1.15, 1.05)), yaw), tone)
			elif hold == 1:
				B.prop("pallet", "timber", Batcher.xf(bc + Vector3(0, ly2 + 0.07, 0),
					Vector3(pitch - 0.35, 0.14, minf(dp - 1.0, 1.15)), yaw), kcol(0.62, 1.0))
				B.prop("box", "kitgrey", Batcher.xf(bc + Vector3(0, ly2 + 0.44, 0),
					Vector3(pitch - 0.45, 0.58, minf(dp - 1.15, 1.05)), yaw), tone)
				B.detail("box", "plastic", Batcher.xf(bc + Vector3(0, ly2 + 0.44, 0),
					Vector3(0.03, 0.60, minf(dp - 1.10, 1.10)), yaw), Color(0.8, 0.8, 0.8))
			else:
				for k2 in 5:
					B.prop("cyl", "galv", Batcher.xf(bc + v * (-0.32 + 0.16 * float(k2)) + Vector3(0, ly2 + 0.11, 0),
						Vector3(0.15, pitch - 0.25, 0.15), yaw, 0.0, PI * 0.5), tone)
	_bay_plate(c, u, v, ln, dp, yaw)

## RULE. Mesh stillages on an exact 1.35 x 1.15 grid, all one way up, the back
## row stacked two high because that is how a yard uses the depth it has.
func _arr_stillage(c: Vector3, u: Vector3, v: Vector3, ln: float, dp: float, yaw: float) -> void:
	var nu := maxi(1, int(ln / 1.35))
	var nv := maxi(1, int(dp / 1.15))
	var pu := ln / float(nu)
	var pv := dp / float(nv)
	for i in nu:
		for j in nv:
			var b := c + u * (-ln * 0.5 + pu * (float(i) + 0.5)) + v * (-dp * 0.5 + pv * (float(j) + 0.5))
			var high := (j == nv - 1)
			for st in (2 if high else 1):
				var by := 0.42 + 0.88 * float(st)
				B.prop("pallet", "timber", Batcher.xf(b + Vector3(0, by - 0.36, 0), Vector3(1.2, 0.16, 1.0), yaw), kcol(0.6, 1.0))
				for e in [[-0.58, 0.0], [0.58, 0.0], [0.0, -0.48], [0.0, 0.48]]:
					var sz := Vector3(0.04, 0.70, 0.96) if absf(e[0]) > 0.1 else Vector3(1.16, 0.70, 0.04)
					B.prop("box", "galv", Batcher.xf(b + u * e[0] + v * e[1] + Vector3(0, by, 0), sz, yaw), kcol(0.62, 1.0))
				B.detail("casebox", "kitgrey", Batcher.xf(b + Vector3(0, by - 0.06, 0), Vector3(0.9, 0.5, 0.76), yaw), kcol(0.7, 0.95))
	_bay_plate(c, u, v, ln, dp, yaw)

## RULE. Palletised stock on the 1.35 m module, one row per 1.3 m of depth, every
## stack the same load and the same height. Two degrees of jitter per pallet: a
## pallet two degrees off square is realistic, forty-seven is not.
func _arr_pallets(c: Vector3, u: Vector3, v: Vector3, ln: float, dp: float, yaw: float) -> void:
	var nu := maxi(1, int(ln / 1.35))
	var nv := maxi(1, int(dp / 1.30))
	var pu := ln / float(nu)
	var pv := dp / float(nv)
	var high := r.randi_range(2, 4)
	var load := r.randi() % 2
	for i in nu:
		for j in nv:
			var b := c + u * (-ln * 0.5 + pu * (float(i) + 0.5)) + v * (-dp * 0.5 + pv * (float(j) + 0.5))
			var jit := r.randf_range(-0.035, 0.035)
			for st in high:
				var by := 0.075 + 0.44 * float(st)
				B.prop("pallet", "timber", Batcher.xf(b + Vector3(0, by, 0), Vector3(1.2, 0.15, 1.0), yaw + jit), kcol(0.6, 1.05))
				B.prop("box", "bone" if load == 0 else "kitgrey",
					Batcher.xf(b + Vector3(0, by + 0.24, 0), Vector3(1.10, 0.30, 0.92), yaw + jit), kcol(0.72, 0.98))
				B.detail("box", "plastic", Batcher.xf(b + Vector3(0, by + 0.24, 0), Vector3(1.14, 0.05, 0.03), yaw + jit), Color(0.85, 0.85, 0.85))
	_bay_plate(c, u, v, ln, dp, yaw)

# --- 1 lay-down --------------------------------------------------------------
## RULE. Long stock does not lie on concrete: it lies on transverse timber
## bearers, parallel, ends flush at the head of the bay, chocked at both ends.
func _arr_laydown(c: Vector3, u: Vector3, v: Vector3, ln: float, dp: float, yaw: float, form: int) -> void:
	for k in 3:
		var bx := c + u * (-ln * 0.5 + ln * (0.15 + 0.35 * float(k)))
		B.prop("box", "timber", Batcher.xf(bx + Vector3(0, 0.07, 0), Vector3(0.20, 0.14, dp - 0.5), yaw), kcol(0.55, 0.95))
	var rows := 3
	var tone := kcol(0.7, 1.0)
	var head := ln * 0.5 - 0.35
	for row in rows:
		var per := 5 - row
		var ry := 0.24 + 0.30 * float(row)
		var span := (dp - 0.8) * (1.0 - 0.18 * float(row))
		for k2 in per:
			var off := -span * 0.5 + span * (float(k2) + 0.5) / float(per)
			var q := c + v * off + Vector3(0, ry, 0) + u * (head - (ln - 0.9) * 0.5)
			if form == 0:
				B.prop("cyl", "galv", Batcher.xf(q, Vector3(0.26, ln - 0.9, 0.26), yaw, 0.0, PI * 0.5), tone)
			else:
				B.prop("ibeam", "iron", Batcher.xf(q, Vector3(0.24, ln - 0.9, 0.24), yaw, 0.0, PI * 0.5), ircol(0.7, 1.4))
	for sgn in [-1.0, 1.0]:
		B.prop("box", "timber", Batcher.xf(c + v * ((dp - 0.5) * 0.5 * sgn) + Vector3(0, 0.24, 0),
			Vector3(0.16, 0.34, 0.16), yaw), kcol(0.5, 0.9))
	_bay_plate(c, u, v, ln, dp, yaw)

## RULE. Plate lies flat on packers with every edge flush, because a plate stack
## that is not flush cannot be lifted by a magnet.
func _arr_plates(c: Vector3, u: Vector3, v: Vector3, ln: float, dp: float, yaw: float) -> void:
	var n := r.randi_range(3, 6)
	for k in n:
		var py := 0.10 + 0.16 * float(k)
		for sgn in [-1.0, 1.0]:
			B.detail("box", "timber", Batcher.xf(c + u * ((ln - 1.4) * 0.35 * sgn) + Vector3(0, py - 0.05, 0),
				Vector3(0.14, 0.10, dp - 0.7), yaw), kcol(0.55, 0.95))
		B.prop("box", "steel", Batcher.xf(c + Vector3(0, py, 0), Vector3(ln - 0.8, 0.05, dp - 0.6), yaw), kcol(0.32, 0.55))
	B.prop("cyl", "amber", Batcher.xf(c + u * (ln * 0.5 - 0.25) + v * (dp * 0.5 - 0.25) + Vector3(0, 0.45, 0),
		Vector3(0.09, 0.9, 0.09), yaw), kcol(0.8, 1.0))
	_bay_plate(c, u, v, ln, dp, yaw)

# --- 2 consumables -----------------------------------------------------------
## RULE. Anything that can leak stands in a BUND: a kerbed slab, and the drums on
## it in an exact grid, all upright, all facing the same way, with a spill kit and
## a placard at the head. That is what makes a drum store legible as a store
## rather than as drums somebody dropped.
func _arr_bund(c: Vector3, u: Vector3, v: Vector3, ln: float, dp: float, yaw: float) -> void:
	B.prop("box", "stone", Batcher.xf(c + Vector3(0, 0.06, 0), Vector3(ln, 0.12, dp), yaw), kcol(0.75, 0.95))
	for sgn in [-1.0, 1.0]:
		B.prop("box", "stone", Batcher.xf(c + v * (dp * 0.5 - 0.08) * sgn + Vector3(0, 0.20, 0),
			Vector3(ln, 0.28, 0.16), yaw), kcol(0.72, 0.95))
		B.prop("box", "stone", Batcher.xf(c + u * (ln * 0.5 - 0.08) * sgn + Vector3(0, 0.20, 0),
			Vector3(0.16, 0.28, dp), yaw), kcol(0.72, 0.95))
	var nu := maxi(1, int((ln - 0.7) / 0.78))
	var nv := maxi(1, int((dp - 0.7) / 0.78))
	var mat: String = ["iron", "kitgrey", "amber"][r.randi() % 3]
	var tone := ircol(0.7, 1.3) if mat == "iron" else kcol(0.7, 0.95)
	for i in nu:
		for j in nv:
			var b := c + u * (-(ln - 0.7) * 0.5 + (ln - 0.7) * (float(i) + 0.5) / float(nu)) \
				+ v * (-(dp - 0.7) * 0.5 + (dp - 0.7) * (float(j) + 0.5) / float(nv))
			B.prop("drum", mat, Batcher.xf(b + Vector3(0, 0.56, 0), Vector3(0.58, 0.88, 0.58), yaw), tone)
			if j == 0:
				B.detail("box", "bone", Batcher.xf(b + v * -0.30 + Vector3(0, 0.68, 0), Vector3(0.22, 0.15, 0.01), yaw), kcol(0.85, 1.0))
	B.prop("casebox", "amber", Batcher.xf(c + u * (ln * 0.5 + 0.55) + Vector3(0, 0.34, 0), Vector3(0.7, 0.68, 0.6), yaw), kcol(0.8, 1.0))
	_bay_plate(c, u, v, ln, dp, yaw)

## RULE. Gas goes in cages, the cages go on the 1.9 m module, and every cage is
## the same cage. Chained, because loose bottles are a fireable offence.
func _arr_bottles(c: Vector3, u: Vector3, v: Vector3, ln: float, dp: float, yaw: float) -> void:
	var n := maxi(1, int(ln / 1.9))
	var pu := ln / float(n)
	for i in n:
		var b := c + u * (-ln * 0.5 + pu * (float(i) + 0.5))
		B.prop("box", "galv", Batcher.xf(b + Vector3(0, 0.06, 0), Vector3(pu - 0.35, 0.12, 0.92), yaw), kcol())
		for sgn in [-1.0, 1.0]:
			B.prop("angle", "galv", Batcher.xf(b + u * ((pu - 0.4) * 0.5 * sgn) + Vector3(0, 0.80, 0),
				Vector3(0.06, 1.6, 0.06), yaw), kcol())
		B.prop("box", "galv", Batcher.xf(b + v * -0.36 + Vector3(0, 1.32, 0), Vector3(pu - 0.35, 0.05, 0.05), yaw), kcol())
		for k in 6:
			var q := b + u * (-(pu - 0.7) * 0.5 + (pu - 0.7) * float(k) / 5.0) + v * -0.05 + Vector3(0, 0.82, 0)
			B.prop("cyl", "ember" if k % 3 == 0 else "kitgrey", Batcher.xf(q, Vector3(0.22, 1.4, 0.22), yaw), kcol(0.55, 0.9))
			B.detail("cyl", "alu", Batcher.xf(q + Vector3(0, 0.78, 0), Vector3(0.09, 0.16, 0.09), yaw), kcol())
	_bay_plate(c, u, v, ln, dp, yaw)

## RULE. Reels live on a stand with the shaft through them, all axes parallel,
## so a cable can be pulled off without lifting anything.
func _arr_reels(c: Vector3, u: Vector3, v: Vector3, ln: float, dp: float, yaw: float) -> void:
	var n := maxi(1, int(ln / 2.6))
	var pu := ln / float(n)
	for i in n:
		var b := c + u * (-ln * 0.5 + pu * (float(i) + 0.5))
		for sgn in [-1.0, 1.0]:
			var foot: Vector3 = b + u * ((pu - 0.5) * 0.5 * sgn)
			B.prop("angle", "kitgrey", Batcher.beam_xf(foot + v * 0.5, foot + Vector3(0, 1.25, 0), 0.07, 0.07), kcol())
			B.prop("angle", "kitgrey", Batcher.beam_xf(foot - v * 0.5, foot + Vector3(0, 1.25, 0), 0.07, 0.07), kcol())
		B.prop("cyl", "steel", Batcher.xf(b + Vector3(0, 1.25, 0), Vector3(0.05, pu - 0.4, 0.05), yaw, 0.0, PI * 0.5), kcol(0.5, 0.8))
		for k in 2:
			var q := b + u * (-0.35 + 0.70 * float(k)) + Vector3(0, 0.78, 0)
			B.prop("wheel", "kitgrey", Batcher.xf(q, Vector3(1.5, 1.5, 0.5), yaw, 0.0, PI * 0.5), kcol(0.75, 0.95))
			B.prop("cyl", "rubber", Batcher.xf(q, Vector3(1.05, 0.36, 1.05), yaw, 0.0, PI * 0.5), Color(0.75, 0.75, 0.75))
			B.detail("box", "bone", Batcher.xf(q + v * 0.26, Vector3(0.30, 0.20, 0.01), yaw), kcol(0.85, 1.0))
	_bay_plate(c, u, v, ln, dp, yaw)

# --- 3 marshalling -----------------------------------------------------------
## RULE. A marked bay is paint on the ground and one thing parked squarely in it,
## or paint on the ground and NOTHING. An empty marked bay is not a missing prop:
## it is the strongest statement in the vocabulary that this yard is in use, and
## it costs four instances.
func _arr_marked(c: Vector3, u: Vector3, v: Vector3, ln: float, dp: float, yaw: float) -> void:
	_paint_rect(c, u, v, ln - 0.4, dp - 0.4, yaw, Color(0.92, 0.86, 0.66))
	_bay_plate(c, u, v, ln, dp, yaw)
	if r.randf() < 0.40:
		return                                  # kept empty, on purpose
	var what := r.randi() % 2
	if what == 0:
		var nu := maxi(1, int((ln - 1.0) / 1.35))
		for i in nu:
			var b := c + u * (-(ln - 1.0) * 0.5 + (ln - 1.0) * (float(i) + 0.5) / float(nu))
			var jit := r.randf_range(-0.03, 0.03)
			for st in 2:
				B.prop("pallet", "timber", Batcher.xf(b + Vector3(0, 0.075 + 0.44 * float(st), 0), Vector3(1.2, 0.15, 1.0), yaw + jit), kcol(0.6, 1.0))
				B.prop("box", "bone", Batcher.xf(b + Vector3(0, 0.315 + 0.44 * float(st), 0), Vector3(1.1, 0.30, 0.92), yaw + jit), kcol(0.75, 0.98))
	else:
		B.prop("casebox", "kitgrey", Batcher.xf(c + Vector3(0, 0.75, 0), Vector3(ln - 1.6, 1.5, dp - 1.2), yaw), kcol(0.7, 0.92))
		B.detail("box", "bone", Batcher.xf(c + v * ((dp - 1.2) * 0.5) + Vector3(0, 1.05, 0), Vector3(0.5, 0.3, 0.02), yaw), kcol(0.85, 1.0))
		for k in 4:
			B.detail("hex", "alu", Batcher.xf(c + u * (-(ln - 1.9) * 0.5 + (ln - 1.9) * float(k) / 3.0) + Vector3(0, 0.04, 0), Vector3(0.10, 0.06, 0.10), yaw), kcol())

## RULE. Trolleys queue. Identical, nose to tail on the 1.7 m module, all facing
## the head of the bay, because that is how somebody left them to be taken.
func _arr_trolleys(c: Vector3, u: Vector3, v: Vector3, ln: float, dp: float, yaw: float) -> void:
	_paint_rect(c, u, v, ln - 0.4, dp - 0.4, yaw, Color(0.92, 0.86, 0.66))
	var n := maxi(1, int(ln / 1.7))
	var pu := ln / float(n)
	for i in n:
		var b := c + u * (-ln * 0.5 + pu * (float(i) + 0.5))
		B.prop("box", "kitgrey", Batcher.xf(b + Vector3(0, 0.34, 0), Vector3(pu - 0.45, 0.07, 0.78), yaw), kcol(0.7, 0.95))
		for e in [[-1.0, -1.0], [1.0, -1.0], [-1.0, 1.0], [1.0, 1.0]]:
			B.detail("cyl", "rubber", Batcher.xf(b + u * ((pu - 0.7) * 0.5 * e[0]) + v * (0.32 * e[1]) + Vector3(0, 0.13, 0),
				Vector3(0.24, 0.08, 0.24), yaw, 0.0, PI * 0.5), Color(1, 1, 1))
		B.prop("cyl", "galv", Batcher.xf(b + u * ((pu - 0.5) * 0.5) + Vector3(0, 0.68, 0), Vector3(0.04, 0.72, 0.04), yaw), kcol())
		B.detail("cyl", "galv", Batcher.xf(b + u * ((pu - 0.5) * 0.5) + Vector3(0, 1.02, 0), Vector3(0.035, 0.7, 0.035), yaw, 0.0, PI * 0.5), kcol())
		if i < n - 1:
			B.prop("casebox", "bone", Batcher.xf(b + Vector3(0, 0.62, 0), Vector3(pu - 0.7, 0.48, 0.66), yaw), kcol(0.78, 0.98))
	_bay_plate(c, u, v, ln, dp, yaw)

## RULE. Waste is a place, not a habit. One skip in a kerbed, painted bay, and it
## is the ONLY object on this site whose contents are allowed a random angle -
## because the answer to "who put it there and why" is "somebody threw it away".
func _arr_skip(c: Vector3, u: Vector3, v: Vector3, ln: float, dp: float, yaw: float) -> void:
	_paint_rect(c, u, v, ln - 0.3, dp - 0.3, yaw, Color(0.88, 0.72, 0.35))
	var sl := minf(ln - 1.0, 4.2)
	var sd := minf(dp - 0.9, 1.9)
	B.prop("box", "ember", Batcher.xf(c + Vector3(0, 0.06, 0), Vector3(sl, 0.12, sd), yaw), kcol(0.55, 0.8))
	for sgn in [-1.0, 1.0]:
		B.prop("box", "ember", Batcher.xf(c + v * (sd * 0.5 * sgn) + Vector3(0, 0.62, 0), Vector3(sl, 1.10, 0.06), yaw), kcol(0.55, 0.8))
		B.prop("box", "ember", Batcher.xf(c + u * (sl * 0.5 * sgn) + Vector3(0, 0.62, 0), Vector3(0.06, 1.10, sd), yaw), kcol(0.55, 0.8))
	for k in 5:
		B.detail("box", "ember", Batcher.xf(c + u * (-sl * 0.5 + sl * float(k) / 4.0) + v * (sd * 0.5) + Vector3(0, 0.62, 0),
			Vector3(0.09, 1.06, 0.09), yaw), kcol(0.5, 0.75))
	for k2 in r.randi_range(6, 11):
		B.detail(["box", "angle", "chip"][r.randi() % 3], ["iron", "timber", "litter"][r.randi() % 3],
			Batcher.xf(c + u * r.randf_range(-sl * 0.4, sl * 0.4) + v * r.randf_range(-sd * 0.3, sd * 0.3) + Vector3(0, 1.02, 0),
				Vector3(r.randf_range(0.1, 0.5), r.randf_range(0.08, 0.5), r.randf_range(0.1, 0.4)),
				r.randf() * TAU, r.randf_range(-0.9, 0.9), r.randf_range(-0.9, 0.9)), ircol())
	_bay_plate(c, u, v, ln, dp, yaw)

# ============================================================== margin tips
## RULE. DESIGN-PRINCIPLES 7: "weeds, debris and standing water belong in the
## margins only". Three tips, all of them BEHIND something and none of them on
## the hardstanding: the strip behind the boiler house, the fence corner north of
## the container row, and the dead ground west of the pallet yard. This is the
## only unordered dressing left on the site, and you have to go and look at it.
func _margin_tips() -> void:
	var spots := [Vector3(23.0, 0, -27.5), Vector3(31.0, 0, 29.0), Vector3(-35.5, 0, -18.0)]
	for sp in spots:
		for k in r.randi_range(9, 15):
			var x: float = sp.x + r.randf_range(-3.2, 3.2)
			var z: float = sp.z + r.randf_range(-2.6, 2.6)
			var y := gh(x, z)
			var which := r.randi() % 4
			if which == 0:
				B.detail("box", "timber", Batcher.xf(Vector3(x, y + 0.06, z), Vector3(0.20, 0.06, r.randf_range(1.0, 2.4)),
					r.randf() * TAU, r.randf_range(-0.2, 0.2), r.randf_range(-0.2, 0.2)), kcol(0.5, 1.0))
			elif which == 1:
				B.detail("angle", "iron", Batcher.xf(Vector3(x, y + 0.10, z), Vector3(0.12, r.randf_range(0.8, 2.2), 0.12),
					r.randf() * TAU, r.randf_range(-1.4, 1.4), r.randf_range(-1.2, 1.2)), ircol())
			elif which == 2:
				B.detail("drum", "iron", Batcher.xf(Vector3(x, y + 0.29, z), Vector3(0.58, 0.88, 0.58),
					r.randf() * TAU, 0.0, PI * 0.5), ircol(0.4, 1.0))
			else:
				B.detail("ring", "rubber", Batcher.xf(Vector3(x, y + 0.09, z), Vector3(0.95, 0.19, 0.95),
					r.randf() * TAU, r.randf_range(-0.3, 0.3), r.randf_range(-0.3, 0.3)), Color(1, 1, 1))

# ============================================================== service bay
## RULE. A light steel portal frame on a cast pad: four portals at 3.5 m, a
## shallow roof, one open side facing the collar so the bay is legible from the
## yard, and a back wall of cladding. Inside, on a 1.2 m module: bench, tool
## board, parts rack, case stack, cable reels, a terminal, a service cradle.
func _service_bay() -> void:
	var bdg := _building("service_bay")
	if bdg.is_empty():
		return
	var x0 := float(bdg["x0"]) / 1000.0
	var z0 := float(bdg["z0"]) / 1000.0
	var x1 := float(bdg["x1"]) / 1000.0
	var z1 := float(bdg["z1"]) / 1000.0
	var h := float(bdg["h"]) / 1000.0
	var y := L.pad_h() / 1000.0
	var portals := int((x1 - x0) / 3.5) + 1
	for i in portals:
		var x := x0 + (x1 - x0) * float(i) / float(portals - 1)
		B.add("ibeam", "kitgrey", Batcher.xf(Vector3(x, y + h * 0.5, z0), Vector3(0.22, h, 0.22)), kcol())
		B.add("ibeam", "kitgrey", Batcher.xf(Vector3(x, y + h * 0.5, z1), Vector3(0.22, h, 0.22)), kcol())
		B.beam("ibeam", "kitgrey", Vector3(x, y + h, z0), Vector3(x, y + h + 0.55, (z0 + z1) * 0.5), 0.20, 0.20, kcol())
		B.beam("ibeam", "kitgrey", Vector3(x, y + h, z1), Vector3(x, y + h + 0.55, (z0 + z1) * 0.5), 0.20, 0.20, kcol())
		# base plates and holding-down bolts
		for zz in [z0, z1]:
			B.prop("box", "alu", Batcher.xf(Vector3(x, y + 0.02, zz), Vector3(0.5, 0.04, 0.5)), kcol())
			for k in 4:
				var a := TAU * float(k) / 4.0 + 0.78
				B.detail("hex", "alu", Batcher.xf(Vector3(x + cos(a) * 0.17, y + 0.06, zz + sin(a) * 0.17), Vector3(0.05, 0.05, 0.05)), kcol())
	# purlins and roof sheets
	for k in 9:
		var t := float(k) / 8.0
		var zz := z0 + (z1 - z0) * t
		var yy := y + h + 0.55 * (1.0 - absf(t - 0.5) * 2.0)
		B.beam("channel", "kitgrey", Vector3(x0, yy + 0.12, zz), Vector3(x1, yy + 0.12, zz), 0.10, 0.14, kcol())
	# RULE. Every fourth sheet, both slopes, is a translucent ROOFLIGHT rather
	# than steel - which is what a real workshop does, and it is the fix for
	# NOTES 7.8: the bay was the dimmest of the frames that argue the case.
	# RULE, and it is the fix for NOTES 7.8: the bay's contents are the best
	# evidence the world has that somebody builds and services these machines, and
	# a roof was hiding them. The last 4 m at the collar end is now an OPEN BAY -
	# no sheets, just the portal - and every third sheet elsewhere is a rooflight.
	var open_from := x1 - 4.0
	for i in int((x1 - x0) / 1.0):
		var x2 := x0 + 1.0 * (float(i) + 0.5)
		if x2 > open_from:
			continue
		var lit := (i % 3) == 1
		for side in [-1.0, 1.0]:
			var zc: float = (z0 + z1) * 0.5 + side * (z1 - z0) * 0.25
			var xf := Batcher.xf(Vector3(x2, y + h + 0.55 - absf(side) * 0.14, zc),
				Vector3(0.98, 0.035, (z1 - z0) * 0.53), 0.0, atan2(0.55, (z1 - z0) * 0.5) * side, 0.0)
			if lit:
				B.add("box", "bone", xf, Color(1, 1, 1), Batcher.SITE, true)
			else:
				B.add("box", "alu", xf, kcol(0.75, 1.0))
		if lit:
			# the daylight that comes through it. Shadowless and distance faded,
			# because positional shadows are what cost 142 ms in the first pass.
			lights.append([Vector3(x2, y + h - 0.15, (z0 + z1) * 0.5),
				Color(0.86, 0.90, 1.0), 5.5, 9.5, true])
	# back cladding (north), on the z0 side
	for i in int((x1 - x0) / 0.9):
		var x3 := x0 + 0.9 * (float(i) + 0.5)
		B.add("box", "alu", Batcher.xf(Vector3(x3, y + h * 0.5 + 0.2, z0 - 0.12), Vector3(0.88, h - 0.3, 0.04)), kcol(0.78, 1.02))
		for cg in 5:
			B.detail("cyl6", "alu", Batcher.xf(Vector3(x3 - 0.34 + 0.17 * float(cg), y + h * 0.5 + 0.2, z0 - 0.15),
				Vector3(0.045, h - 0.3, 0.045)), kcol(0.78, 1.02))
	# --- the bench: 4.8 m of it, on the back wall, with the modules laid out
	var bx := (x0 + x1) * 0.5 - 1.4
	var bz := z0 + 0.85
	B.prop("box", "alu", Batcher.xf(Vector3(bx, y + 0.90, bz), Vector3(4.8, 0.07, 0.85)), kcol())
	for k in 5:
		var lx := bx - 2.2 + 1.1 * float(k)
		B.prop("box", "kitgrey", Batcher.xf(Vector3(lx, y + 0.45, bz - 0.3), Vector3(0.07, 0.9, 0.07)), kcol())
		B.prop("box", "kitgrey", Batcher.xf(Vector3(lx, y + 0.45, bz + 0.3), Vector3(0.07, 0.9, 0.07)), kcol())
	# under-bench drawers and bins
	for k in 4:
		B.prop("casebox", "kitgrey", Batcher.xf(Vector3(bx - 2.0 + 1.15 * float(k), y + 0.40, bz), Vector3(0.85, 0.72, 0.62)), kcol())
	# the seven modules, as parts on the bench (vision board A3 / 11_yard_modules)
	var mods := [Vector3(0.34, 0.09, 0.11), Vector3(0.16, 0.16, 0.16), Vector3(0.44, 0.06, 0.06),
		Vector3(0.22, 0.20, 0.14), Vector3(0.62, 0.05, 0.05), Vector3(0.30, 0.14, 0.24), Vector3(0.19, 0.13, 0.13)]
	for k in mods.size():
		var p := Vector3(bx - 2.1 + 0.62 * float(k), y + 0.94 + mods[k].y * 0.5, bz)
		B.prop("casebox", "bone" if k % 3 != 1 else "kitgrey", Batcher.xf(p, mods[k]), kcol())
		B.detail("box", "amber", Batcher.xf(p + Vector3(0, mods[k].y * 0.52, 0), Vector3(mods[k].x * 0.5, 0.004, 0.02)), Color(1, 1, 1))
	# hand tools scattered on the bench
	for k in 14:
		var p2 := Vector3(bx + r.randf_range(-2.3, 2.3), y + 0.96, bz + r.randf_range(-0.35, 0.35))
		B.detail("box", "alu" if r.randf() < 0.5 else "kitgrey",
			Batcher.xf(p2, Vector3(r.randf_range(0.02, 0.05), 0.02, r.randf_range(0.10, 0.26)), r.randf() * TAU), kcol())
	# tool board on the wall
	B.prop("box", "kitgrey", Batcher.xf(Vector3(bx, y + 1.85, z0 + 0.32), Vector3(3.2, 1.1, 0.04)), kcol(0.6, 0.8))
	for k in 22:
		var p3 := Vector3(bx + r.randf_range(-1.5, 1.5), y + 1.45 + r.randf_range(0.0, 0.75), z0 + 0.36)
		B.detail("box", "alu", Batcher.xf(p3, Vector3(r.randf_range(0.015, 0.05), r.randf_range(0.10, 0.32), 0.02), r.randf_range(-0.2, 0.2)), kcol())
	# terminal: a rugged case with a screen, on the bench
	B.prop("casebox", "kitgrey", Batcher.xf(Vector3(bx + 1.9, y + 1.10, bz - 0.05), Vector3(0.52, 0.36, 0.30), -0.3), kcol())
	B.add("box", "screen", Batcher.xf(Vector3(bx + 1.9, y + 1.12, bz - 0.19), Vector3(0.46, 0.28, 0.01), -0.3, 0.18), Color(1, 1, 1), Batcher.PROP, true)
	lights.append([Vector3(bx + 1.9, y + 1.4, bz - 0.5), Color(0.75, 0.80, 0.95), 1.2, 3.0, true])
	# parts rack: four bays of shelves full of bins
	var rx := x0 + 1.2
	for bay in 3:
		for shelf in 4:
			var sy := y + 0.35 + 0.55 * float(shelf)
			B.prop("box", "kitgrey", Batcher.xf(Vector3(rx + 0.9 * float(bay), sy, z0 + 0.55), Vector3(0.86, 0.04, 0.55)), kcol())
			for bn in 3:
				if r.randf() < 0.2:
					continue
				B.detail("casebox", "bone" if r.randf() < 0.6 else "amber",
					Batcher.xf(Vector3(rx + 0.9 * float(bay) - 0.28 + 0.28 * float(bn), sy + 0.11, z0 + 0.55 + r.randf_range(-0.06, 0.06)),
						Vector3(0.24, 0.17, 0.42)), kcol())
		for post in [-0.43, 0.43]:
			B.prop("angle", "kitgrey", Batcher.xf(Vector3(rx + 0.9 * float(bay) + post, y + 1.2, z0 + 0.3), Vector3(0.06, 2.4, 0.06)), kcol())
			B.prop("angle", "kitgrey", Batcher.xf(Vector3(rx + 0.9 * float(bay) + post, y + 1.2, z0 + 0.8), Vector3(0.06, 2.4, 0.06)), kcol())
	# flight cases stacked, labelled
	# flight cases: three columns, stacked, labels all facing out. Cases squared
	# up in a column read as a loadout; cases at nine angles read as a heap.
	for col in 3:
		var cx := x1 - 5.4 + 0.95 * float(col)
		var cz := z0 + 1.05
		for st in 3:
			B.prop("casebox", "kitgrey", Batcher.xf(Vector3(cx, y + 0.22 + 0.45 * float(st), cz),
				Vector3(0.86, 0.44, 0.60)), kcol(0.55, 0.72))
			B.detail("box", "bone", Batcher.xf(Vector3(cx, y + 0.22 + 0.45 * float(st), cz + 0.31),
				Vector3(0.32, 0.14, 0.01)), kcol(0.85, 1.0))
	# cable reels and a loom into the roof
	for k in 3:
		var dx := x0 + 2.6 + 1.3 * float(k)
		B.prop("wheel", "kitgrey", Batcher.xf(Vector3(dx, y + 0.42, z1 - 0.9), Vector3(0.82, 0.82, 0.58), 0.0, 0.0, PI * 0.5), kcol())
		B.prop("cyl", "rubber", Batcher.xf(Vector3(dx, y + 0.42, z1 - 0.9), Vector3(0.60, 0.42, 0.60), 0.0, 0.0, PI * 0.5), kcol(0.7, 0.9))
	_cable_run(Vector3(x0 + 0.6, y + h - 0.3, z0 + 0.4), Vector3(x1 - 0.6, y + h - 0.3, z0 + 0.4), 7, 0.035)
	# work light under the roof (DESIGN-PRINCIPLES 3: the surface is safe and lit)
	for k in 3:
		var lx2 := x0 + 3.0 + 4.0 * float(k)
		B.prop("box", "alu", Batcher.xf(Vector3(lx2, y + h + 0.28, (z0 + z1) * 0.5), Vector3(1.3, 0.10, 0.22)), kcol())
		B.add("box", "glass", Batcher.xf(Vector3(lx2, y + h + 0.21, (z0 + z1) * 0.5), Vector3(1.2, 0.03, 0.16)), Color(1, 1, 1))
		# RULE. A roofed bay is dark at noon, so the bay's own work lights are on in
		# every lighting condition, not only after dark. The 5th field is that flag.
		lights.append([Vector3(lx2, y + h + 0.10, (z0 + z1) * 0.5), Color(1.0, 0.96, 0.90), 7.5, 12.0, true])

func _building(kind: String) -> Dictionary:
	for b in L.plan["buildings"]:
		if b["kind"] == kind:
			return b
	return {}

## a cable tray with N cables in it, sagging between supports
func _cable_run(a: Vector3, b: Vector3, n: int, w: float) -> void:
	B.prop("channel", "alu", Batcher.beam_xf(a, b, 0.30, 0.14), kcol())
	var dir := (b - a).normalized()
	var side := dir.cross(Vector3.UP).normalized()
	for i in n:
		var off := side * (-0.11 + 0.22 * float(i) / float(maxi(n - 1, 1)))
		var col := Color(0.8, 0.8, 0.8) if i % 3 != 0 else Color(1.4, 1.0, 0.5)
		B.detail("cyl6", "rubber", Batcher.beam_xf(a + off + Vector3(0, -0.05, 0), b + off + Vector3(0, -0.05, 0), w, w), col)

# ================================================================== gantry
## RULE. A rail gantry spanning the bay and reaching out over the yard: two rails
## on legs, a crab, a hoist block on a chain, and a lifting frame that fits a
## machine. This is the "handling gear" that makes servicing plausible.
func _gantry() -> void:
	var G: Dictionary = L.plan["gantry"]
	var x0 := float(G["x0"]) / 1000.0
	var x1 := float(G["x1"]) / 1000.0
	var z := float(G["z"]) / 1000.0
	var h := float(G["h"]) / 1000.0
	var g := float(G["rail_gauge"]) / 2000.0
	var y := L.pad_h() / 1000.0
	for side in [-1.0, 1.0]:
		B.beam("ibeam", "kitgrey", Vector3(x0, y + h, z + side * g), Vector3(x1 + 4.0, y + h, z + side * g), 0.26, 0.26, kcol())
		var n := int((x1 + 4.0 - x0) / 3.6)
		for i in range(n + 1):
			var x := x0 + (x1 + 4.0 - x0) * float(i) / float(n)
			B.add("ibeam", "kitgrey", Batcher.xf(Vector3(x, y + h * 0.5, z + side * g), Vector3(0.2, h, 0.2)), kcol())
			if i < n:
				B.prop("angle", "kitgrey", Batcher.beam_xf(Vector3(x, y + 0.4, z + side * g),
					Vector3(x + (x1 + 4.0 - x0) / float(n), y + h - 0.2, z + side * g), 0.09, 0.09), kcol())
	# the crab and hoist
	var cx := x1 + 1.2
	B.beam("ibeam", "kitgrey", Vector3(cx, y + h + 0.30, z - g), Vector3(cx, y + h + 0.30, z + g), 0.24, 0.24, kcol())
	B.prop("casebox", "kitgrey", Batcher.xf(Vector3(cx, y + h + 0.30, z + 0.9), Vector3(0.7, 0.5, 0.9)), kcol())
	B.prop("cyl6", "steel", Batcher.xf(Vector3(cx, y + h - 0.55, z + 0.9), Vector3(0.03, 1.4, 0.03)), kcol(0.5, 0.8))
	B.prop("casebox", "amber", Batcher.xf(Vector3(cx, y + h - 1.35, z + 0.9), Vector3(0.24, 0.30, 0.20)), kcol())
	# the lifting frame, hanging just above a machine
	var fy := y + h - 1.9
	for e in [[-0.45, -0.28, 0.45, -0.28], [-0.45, 0.28, 0.45, 0.28], [-0.45, -0.28, -0.45, 0.28], [0.45, -0.28, 0.45, 0.28]]:
		B.prop("angle", "alu", Batcher.beam_xf(Vector3(cx + e[0], fy, z + 0.9 + e[1]), Vector3(cx + e[2], fy, z + 0.9 + e[3]), 0.05, 0.05), kcol())
	for e2 in [[-0.45, -0.28], [0.45, -0.28], [-0.45, 0.28], [0.45, 0.28]]:
		B.detail("cyl6", "steel", Batcher.beam_xf(Vector3(cx + e2[0], fy, z + 0.9 + e2[1]), Vector3(cx, y + h - 1.42, z + 0.9), 0.012, 0.012), kcol(0.6, 0.9))

# ============================================================== charge row
## RULE, and this is the frame that has to convince a sceptic. Five IDENTICAL
## pedestals on one plinth, on an exact 2.4 m pitch, square to the site grid,
## each in front of a painted and numbered dock bay, with a machine standing in
## four of the five. DESIGN-PRINCIPLES 7: "five identical charge pedestals in a
## line with machines docked in them is worth more than fifty scattered objects."
##
## Bay 3 is empty and its cable is coiled on the hook. An empty bay in a line of
## full ones says a machine is out; five full bays say nothing is happening.
const DOCK_N := 5
const DOCK_PITCH := 2.4
const DOCK_EMPTY := 2

func _charge_row() -> void:
	var Z := _zone("charge_row")
	if Z.is_empty():
		return
	var x0 := float(Z["x0"]) / 1000.0
	var x1 := float(Z["x1"]) / 1000.0
	var zc := float(Z["z0"]) / 1000.0 + 0.6
	var y := L.pad_h() / 1000.0
	var cx := (x0 + x1) * 0.5
	var run := DOCK_PITCH * float(DOCK_N - 1)
	# the common plinth. One casting under all five: the thing that says these were
	# installed together rather than dropped one at a time.
	B.prop("box", "stone", Batcher.xf(Vector3(cx, y + 0.09, zc), Vector3(run + 1.6, 0.18, 1.30)), kcol(0.82, 1.0))
	B.detail("box", "paint", Batcher.xf(Vector3(cx, y + 0.19, zc - 0.62), Vector3(run + 1.6, 0.02, 0.09)), Color(0.9, 0.85, 0.6))
	for i in DOCK_N:
		var x := cx - run * 0.5 + DOCK_PITCH * float(i)
		# the pedestal: pale, chamfered, labelled. The players' register.
		B.prop("casebox", "bone", Batcher.xf(Vector3(x, y + 0.86, zc), Vector3(0.44, 1.20, 0.36)), kcol(0.88, 1.02))
		B.prop("casebox", "kitgrey", Batcher.xf(Vector3(x, y + 0.26, zc), Vector3(0.50, 0.24, 0.42)), kcol())
		B.prop("casebox", "kitgrey", Batcher.xf(Vector3(x, y + 1.50, zc), Vector3(0.48, 0.16, 0.40)), kcol())
		B.add("box", "amber", Batcher.xf(Vector3(x, y + 1.53, zc + 0.21), Vector3(0.24, 0.03, 0.01)), Color(1, 1, 1), Batcher.PROP, true)
		B.detail("box", "kitgrey", Batcher.xf(Vector3(x, y + 1.16, zc + 0.19), Vector3(0.22, 0.14, 0.01)), Color(0.5, 0.5, 0.5))
		B.detail("box", "paint", Batcher.xf(Vector3(x, y + 0.95, zc + 0.19), Vector3(0.16, 0.10, 0.006)), Color(0.9, 0.85, 0.6))
		# the painted dock bay in front of it, numbered
		var bc := Vector3(x, y, zc + 1.85)
		_paint_rect(bc, Vector3(1, 0, 0), Vector3(0, 0, 1), 2.10, 2.20, 0.0, Color(0.92, 0.86, 0.66))
		for k in 3:
			B.add("box", "paint", Batcher.xf(bc + Vector3(-0.6 + 0.6 * float(k), 0.012, 1.05), Vector3(0.09, 0.012, 0.30)), Color(0.92, 0.86, 0.66), Batcher.SITE)
		# the cable: coiled on the hook if the bay is empty, plugged in if it is not
		if i == DOCK_EMPTY:
			for k2 in 9:
				var a := TAU * float(k2) / 9.0
				B.detail("cyl6", "rubber", Batcher.xf(Vector3(x + 0.27, y + 0.92 + sin(a) * 0.19, zc + cos(a) * 0.19),
					Vector3(0.028, 0.19, 0.028), 0.0, 0.0, a), Color(0.9, 0.9, 0.9))
		lights.append([Vector3(x, y + 1.55, zc), Color(1.0, 0.72, 0.42), 0.8, 3.0])
	# the feeder: one straight trunking run behind the plinth, and one ramp where
	# it has to cross the walkway. Straight, because a cable somebody laid is.
	_cable_run(Vector3(cx - run * 0.5 - 1.4, y + 0.16, zc - 0.95), Vector3(cx + run * 0.5 + 1.4, y + 0.16, zc - 0.95), 5, 0.03)
	B.detail("box", "amber", Batcher.xf(Vector3(cx, y + 0.05, zc + 3.4), Vector3(1.2, 0.10, 0.55)), Color(0.7, 0.7, 0.7))
	# a battery skid at the head of the line, square to it
	var sx := cx - run * 0.5 - 3.0
	B.add("casebox", "kitgrey", Batcher.xf(Vector3(sx, y + 1.15, zc + 0.2), Vector3(2.4, 2.3, 2.2)), kcol())
	for k3 in 12:
		B.detail("box", "alu", Batcher.xf(Vector3(sx - 1.0 + 0.18 * float(k3), y + 1.6, zc + 1.32), Vector3(0.05, 1.1, 0.10)), kcol())
	for k4 in 2:
		B.prop("ring", "kitgrey", Batcher.xf(Vector3(sx - 0.6 + 1.2 * float(k4), y + 1.9, zc - 0.92), Vector3(0.62, 0.10, 0.62), 0.0, PI * 0.5), kcol())
	B.detail("box", "bone", Batcher.xf(Vector3(sx, y + 1.1, zc - 0.92), Vector3(0.5, 0.3, 0.02)), kcol())

## where a machine stands when it is on charge: bay i of the dock line.
func _dock_pos(i: int) -> Vector3:
	var Z := _zone("charge_row")
	var y := L.pad_h() / 1000.0
	var cx := (float(Z["x0"]) + float(Z["x1"])) / 2000.0
	var zc := float(Z["z0"]) / 1000.0 + 0.6
	var run := DOCK_PITCH * float(DOCK_N - 1)
	return Vector3(cx - run * 0.5 + DOCK_PITCH * float(i), y, zc + 1.35)

func _zone(kind: String) -> Dictionary:
	for zz in L.plan["zones"]:
		if zz["kind"] == kind:
			return zz
	return {}

# ============================================================== containers
## RULE. 6.06 x 2.44 x 2.59 boxes on the 2.44 module, stacked to two where the
## row is deep, corrugated on a 0.28 pitch, doors on one end, a stair and a rail
## on the ones in use. Half old and rusted, half the players' recent grey.
func _containers() -> void:
	var Z := _zone("container_row")
	if Z.is_empty():
		return
	var x0 := float(Z["x0"]) / 1000.0
	var z0 := float(Z["z0"]) / 1000.0
	var z1 := float(Z["z1"]) / 1000.0
	var y := L.pad_h() / 1000.0
	var rows := int((z1 - z0) / 3.0)
	for i in rows:
		var z := z0 + 3.0 * (float(i) + 0.5)
		var stack := 2 if (i % 3 == 1) else 1
		var mat := "kitgrey" if i % 2 == 0 else "iron"
		for s in stack:
			var cy := y + 1.30 + 2.62 * float(s)
			var yaw := r.randf_range(-0.02, 0.02)
			B.add("box", mat, Batcher.xf(Vector3(x0 + 3.2, cy, z), Vector3(6.06, 2.59, 2.44), yaw),
				kcol(0.55, 0.9) if mat == "kitgrey" else ircol(0.6, 1.5))
			# corrugations
			for k in 20:
				B.prop("cyl6", mat, Batcher.xf(Vector3(x0 + 3.2 - 2.8 + 0.29 * float(k), cy, z + 1.24),
					Vector3(0.10, 2.4, 0.10), yaw), kcol(0.55, 0.9) if mat == "kitgrey" else ircol(0.6, 1.5))
				B.prop("cyl6", mat, Batcher.xf(Vector3(x0 + 3.2 - 2.8 + 0.29 * float(k), cy, z - 1.24),
					Vector3(0.10, 2.4, 0.10), yaw), kcol(0.55, 0.9) if mat == "kitgrey" else ircol(0.6, 1.5))
			# corner castings
			for ex in [-3.03, 3.03]:
				for ez in [-1.22, 1.22]:
					for ey in [-1.28, 1.28]:
						B.prop("box", "iron", Batcher.xf(Vector3(x0 + 3.2 + ex, cy + ey, z + ez), Vector3(0.20, 0.18, 0.20)), ircol())
			# doors on the west end
			B.prop("box", mat, Batcher.xf(Vector3(x0 + 0.14, cy, z - 0.61), Vector3(0.05, 2.4, 1.16), yaw), kcol(0.5, 0.8))
			B.prop("box", mat, Batcher.xf(Vector3(x0 + 0.14, cy, z + 0.61), Vector3(0.05, 2.4, 1.16), yaw), kcol(0.5, 0.8))
			for k2 in 4:
				B.detail("cyl", "iron", Batcher.xf(Vector3(x0 + 0.08, cy, z - 0.9 + 0.6 * float(k2)), Vector3(0.05, 2.3, 0.05)), ircol())
			# label panel
			B.detail("box", "bone", Batcher.xf(Vector3(x0 + 3.2, cy + 0.75, z + 1.28), Vector3(1.1, 0.34, 0.01)), kcol())
		if i % 3 == 1:
			# a stair and landing up the double stack
			B.prop("box", "galv", Batcher.xf(Vector3(x0 - 0.7, y + 1.4, z), Vector3(1.2, 0.06, 2.2)), kcol())
			for k3 in 7:
				B.detail("box", "galv", Batcher.xf(Vector3(x0 - 1.2 - 0.3 * float(k3), y + 1.35 - 0.19 * float(k3), z), Vector3(0.3, 0.05, 1.0)), kcol())

# =================================================================== tanks
## RULE. Vertical tanks on a bunded slab, banded every 1.2 m, with a caged
## ladder, a walkway between them, and a valve manifold at the foot.
func _tanks() -> void:
	var Z := _zone("tank_farm")
	if Z.is_empty():
		return
	var x0 := float(Z["x0"]) / 1000.0
	var z0 := float(Z["z0"]) / 1000.0
	var z1 := float(Z["z1"]) / 1000.0
	var y := L.pad_h() / 1000.0
	# bund
	for side in [-1.0, 1.0]:
		B.add("box", "stone", Batcher.xf(Vector3(x0 + 3.0, y + 0.30, (z0 + z1) * 0.5 + side * 5.5), Vector3(8.0, 0.6, 0.35)), kcol(0.7, 1.0))
		B.add("box", "stone", Batcher.xf(Vector3(x0 + 3.0 + side * 4.0, y + 0.30, (z0 + z1) * 0.5), Vector3(0.35, 0.6, 11.0)), kcol(0.7, 1.0))
	for i in 3:
		var z := z0 + 2.0 + 3.6 * float(i)
		var rr := 1.55
		var hh := 6.2 + r.randf_range(-0.6, 0.9)
		B.add("cyl", "iron", Batcher.xf(Vector3(x0 + 3.0, y + hh * 0.5, z), Vector3(rr * 2.0, hh, rr * 2.0)), ircol(0.5, 1.4))
		for k in int(hh / 1.2):
			B.prop("ring", "iron", Batcher.xf(Vector3(x0 + 3.0, y + 0.6 + 1.2 * float(k), z), Vector3(rr * 2.1, 0.10, rr * 2.1)), ircol())
			var a0 := Vector3(x0 + 3.0 - rr, y + 0.6 + 1.2 * float(k), z)
			var a1 := Vector3(x0 + 3.0 + rr, y + 0.6 + 1.2 * float(k), z)
			B.detail("hex", "iron", Batcher.xf(a0, Vector3(0.09, 0.07, 0.09), 0.0, 0.0, PI * 0.5), ircol(0.8, 1.7))
			B.detail("hex", "iron", Batcher.xf(a1, Vector3(0.09, 0.07, 0.09), 0.0, 0.0, PI * 0.5), ircol(0.8, 1.7))
		# conical top and a vent
		B.prop("cone", "iron", Batcher.xf(Vector3(x0 + 3.0, y + hh + 0.35, z), Vector3(rr * 2.0, 0.8, rr * 2.0)), ircol())
		B.prop("cyl", "iron", Batcher.xf(Vector3(x0 + 3.0, y + hh + 1.0, z), Vector3(0.2, 0.9, 0.2)), ircol())
		# caged ladder
		B.add("ladder", "iron", Batcher.xf(Vector3(x0 + 3.0 - rr - 0.28, y + hh * 0.5, z), Vector3(0.5, hh, 0.1)), ircol())
		for k2 in int(hh - 2.0):
			B.detail("ring", "iron", Batcher.xf(Vector3(x0 + 3.0 - rr - 0.05, y + 2.0 + float(k2), z), Vector3(1.3, 0.04, 1.3), 0.0, 0.0, PI * 0.5), ircol())
		# manifold at the foot
		var mp := Vector3(x0 + 3.0 + rr, y + 0.35, z)
		B.prop("cyl", "iron", Batcher.xf(mp + Vector3(0.5, 0, 0), Vector3(0.22, 1.4, 0.22), 0.0, 0.0, PI * 0.5), ircol())
		B.prop("wheel", "iron", Batcher.xf(mp + Vector3(0.9, 0.3, 0), Vector3(0.42, 0.42, 0.08), 0.0, PI * 0.5), ircol())
		B.detail("box", "bone", Batcher.xf(mp + Vector3(0.2, 0.9, -0.1), Vector3(0.30, 0.20, 0.01)), kcol())
	# pipe bridge out of the farm to the winding house
	var py := y + 4.4
	B.beam("cyl", "iron", Vector3(x0 + 4.6, py, z0 + 2.0), Vector3(x0 + 4.6, py, z1 - 1.0), 0.26, 0.26, ircol())
	B.beam("cyl", "iron", Vector3(x0 + 4.9, py - 0.35, z0 + 2.0), Vector3(x0 + 4.9, py - 0.35, z1 - 1.0), 0.18, 0.18, ircol())
	for k in 5:
		var zz := z0 + 2.0 + (z1 - z0 - 3.0) * float(k) / 4.0
		B.prop("angle", "iron", Batcher.xf(Vector3(x0 + 4.75, y + py * 0.5 - 0.1, zz), Vector3(0.12, py - y, 0.12)), ircol())

# ============================================================= transformer
## RULE. A fenced pen holding two transformers with radiator banks, a switch
## cabinet row, bushings, and a cable trench under a chequer plate lid.
func _transformer() -> void:
	var Z := _zone("transformer")
	if Z.is_empty():
		return
	var x0 := float(Z["x0"]) / 1000.0
	var z0 := float(Z["z0"]) / 1000.0
	var x1 := float(Z["x1"]) / 1000.0
	var z1 := float(Z["z1"]) / 1000.0
	var y := L.pad_h() / 1000.0
	_pen(x0, z0, x1, z1, 2.2)
	for i in 2:
		var cx := x0 + 2.0 + 3.2 * float(i)
		var cz := (z0 + z1) * 0.5
		B.add("box", "kitgrey", Batcher.xf(Vector3(cx, y + 1.1, cz), Vector3(2.0, 2.2, 1.6)), kcol(0.5, 0.75))
		for k in 14:
			B.prop("box", "kitgrey", Batcher.xf(Vector3(cx - 0.9 + 0.14 * float(k), y + 1.1, cz + 1.05), Vector3(0.06, 1.9, 0.5)), kcol(0.5, 0.75))
		for k2 in 3:
			B.prop("cyl", "bone", Batcher.xf(Vector3(cx - 0.6 + 0.6 * float(k2), y + 2.5, cz), Vector3(0.24, 0.7, 0.24)), Color(1, 1, 1))
			B.detail("ring", "bone", Batcher.xf(Vector3(cx - 0.6 + 0.6 * float(k2), y + 2.65, cz), Vector3(0.36, 0.06, 0.36)), Color(1, 1, 1))
		B.detail("box", "amber", Batcher.xf(Vector3(cx, y + 1.6, cz - 0.82), Vector3(0.34, 0.26, 0.01)), Color(0.9, 0.9, 0.9))
	for i in 4:
		B.prop("casebox", "kitgrey", Batcher.xf(Vector3(x0 + 0.9, y + 0.95, z0 + 1.0 + 1.0 * float(i)), Vector3(0.8, 1.9, 0.9)), kcol(0.55, 0.8))
	B.prop("box", "galv", Batcher.xf(Vector3((x0 + x1) * 0.5, y + 0.06, z1 - 0.7), Vector3(x1 - x0 - 0.6, 0.06, 0.8)), kcol())

func _pen(x0: float, z0: float, x1: float, z1: float, h: float) -> void:
	var y := L.pad_h() / 1000.0
	var segs := [[x0, z0, x1, z0], [x1, z0, x1, z1], [x1, z1, x0, z1], [x0, z1, x0, z0]]
	for s in segs:
		var a := Vector2(s[0], s[1])
		var b := Vector2(s[2], s[3])
		var n := maxi(2, int(a.distance_to(b) / 2.4))
		for i in range(n + 1):
			var p: Vector2 = a.lerp(b, float(i) / float(n))
			B.prop("angle", "galv", Batcher.xf(Vector3(p.x, y + h * 0.5, p.y), Vector3(0.08, h, 0.08)), kcol())
		# palisade
		var m := maxi(2, int(a.distance_to(b) / 0.14))
		for i in m:
			var p2: Vector2 = a.lerp(b, (float(i) + 0.5) / float(m))
			B.detail("box", "galv", Batcher.xf(Vector3(p2.x, y + h * 0.5, p2.y), Vector3(0.035, h - 0.1, 0.035)), kcol(0.6, 1.0))
		B.detail("box", "galv", Batcher.beam_xf(Vector3(a.x, y + h - 0.15, a.y), Vector3(b.x, y + h - 0.15, b.y), 0.04, 0.04), kcol())
		B.detail("box", "galv", Batcher.beam_xf(Vector3(a.x, y + 0.25, a.y), Vector3(b.x, y + 0.25, b.y), 0.04, 0.04), kcol())

# ============================================================== comms mast
## RULE. A three-leg lattice mast on a cast pad, guyed at two levels, carrying
## two dishes, three panel antennas, a cable ladder down one leg and an obstruction
## pilot at the top. This is the uplink; the acoustic link's own end is at the collar.
func _comms_mast() -> void:
	for m in L.plan["masts"]:
		if m["kind"] != "comms":
			continue
		var x := float(m["x"]) / 1000.0
		var z := float(m["z"]) / 1000.0
		var h := float(m["h"]) / 1000.0
		var y := gh(x, z)
		var rr := 0.62
		var legs: Array = []
		for k in 3:
			var a := TAU * float(k) / 3.0
			legs.append(Vector2(cos(a) * rr, sin(a) * rr))
		B.add("box", "stone", Batcher.xf(Vector3(x, y + 0.2, z), Vector3(2.6, 0.4, 2.6)), kcol(0.7, 1.0))
		for k in 3:
			var lp: Vector2 = legs[k]
			B.add("cyl", "galv", Batcher.xf(Vector3(x + lp.x, y + h * 0.5, z + lp.y), Vector3(0.13, h, 0.13)), kcol(0.7, 1.05))
		var bays := int(h / 1.2)
		for i in bays:
			var yy := y + 1.2 * float(i)
			for k in 3:
				var a1: Vector2 = legs[k]
				var b1: Vector2 = legs[(k + 1) % 3]
				B.detail("cyl6", "galv", Batcher.beam_xf(Vector3(x + a1.x, yy, z + a1.y), Vector3(x + b1.x, yy, z + b1.y), 0.05, 0.05), kcol(0.7, 1.05))
				B.detail("cyl6", "galv", Batcher.beam_xf(Vector3(x + a1.x, yy, z + a1.y), Vector3(x + b1.x, yy + 1.2, z + b1.y), 0.042, 0.042), kcol(0.7, 1.05))
		# guys
		for k in 3:
			var a2 := TAU * float(k) / 3.0 + 0.5
			var anch := Vector3(x + cos(a2) * h * 0.55, y, z + sin(a2) * h * 0.55)
			B.prop("box", "stone", Batcher.xf(anch + Vector3(0, 0.15, 0), Vector3(0.8, 0.3, 0.8)), kcol(0.7, 1.0))
			for lvl in [0.55, 0.85]:
				B.add("cyl6", "galv", Batcher.beam_xf(Vector3(x, y + h * lvl, z), anch + Vector3(0, 0.3, 0), 0.02, 0.02), kcol(0.6, 0.9))
		# dishes and panels
		for k in 2:
			var a3 := 1.2 + float(k) * 2.4
			B.prop("dish", "bone", Batcher.xf(Vector3(x + cos(a3) * 0.95, y + h * 0.72 + float(k) * 2.2, z + sin(a3) * 0.95),
				Vector3(1.5, 0.6, 1.5), a3, -PI * 0.5 + 0.25), kcol())
			B.prop("cyl", "galv", Batcher.xf(Vector3(x + cos(a3) * 0.75, y + h * 0.72 + float(k) * 2.2, z + sin(a3) * 0.75), Vector3(0.07, 1.2, 0.07)), kcol())
		for k in 3:
			var a4 := TAU * float(k) / 3.0 + 0.3
			B.prop("casebox", "bone", Batcher.xf(Vector3(x + cos(a4) * 0.85, y + h - 1.6, z + sin(a4) * 0.85),
				Vector3(0.22, 1.5, 0.14), a4), kcol())
		# cable ladder down one leg
		B.prop("ladder", "galv", Batcher.xf(Vector3(x + legs[0].x + 0.22, y + h * 0.5, z + legs[0].y), Vector3(0.34, h, 0.06)), kcol())
		for k in 6:
			B.detail("cyl6", "rubber", Batcher.beam_xf(Vector3(x + legs[0].x + 0.30, y + 0.2, z + legs[0].y - 0.09 + 0.036 * float(k)),
				Vector3(x + legs[0].x + 0.30, y + h - 1.0, z + legs[0].y - 0.09 + 0.036 * float(k)), 0.022, 0.022), Color(0.7, 0.7, 0.7))
		B.add("cyl", "amber", Batcher.xf(Vector3(x, y + h + 0.25, z), Vector3(0.2, 0.22, 0.2)), Color(1, 1, 1), Batcher.SITE, true)
		lights.append([Vector3(x, y + h + 0.25, z), Color(1.0, 0.66, 0.35), 1.5, 6.0])

# ============================================================ zone clutter
## RULE. Each zone rectangle is filled by a table that says what goes in it and
## how densely. This is the whole of "walking distance": a yard is not props
## placed by hand, it is six zones with a stocking rule each.
func _zone_clutter() -> void:
	for zz in L.plan["zones"]:
		var kind: String = zz["kind"]
		var x0 := float(zz["x0"]) / 1000.0
		var z0 := float(zz["z0"]) / 1000.0
		var x1 := float(zz["x1"]) / 1000.0
		var z1 := float(zz["z1"]) / 1000.0
		match kind:
			"pallets":
				_fill_pallets(x0, z0, x1, z1)
			"drums":
				_fill_drums(x0, z0, x1, z1)
			"spares":
				_fill_spares(x0, z0, x1, z1)
			"scrap":
				_fill_scrap(x0, z0, x1, z1)

## RULE. A pallet yard is ROWS with an aisle down it, not a field of stacks.
## Every row is the same load at the same height; the aisle is 2.4 m so a machine
## can get down it, and it is kept clear.
func _fill_pallets(x0: float, z0: float, x1: float, z1: float) -> void:
	var y := L.pad_h() / 1000.0
	var rows := maxi(1, int((z1 - z0 - 2.4) / 1.30))
	var cols := maxi(1, int((x0 - x1) / -1.35))
	var aisle := rows / 2
	for j in rows:
		var z := z0 + 0.75 + 1.30 * float(j) + (2.4 if j >= aisle else 0.0)
		if z > z1 - 0.6:
			continue
		var high := r.randi_range(2, 4)
		var load := r.randi() % 2
		for i in cols:
			var x := x0 + 0.8 + (x1 - x0 - 1.6) * float(i) / float(maxi(cols - 1, 1))
			var jit := r.randf_range(-0.035, 0.035)
			for st in high:
				var by := 0.075 + 0.44 * float(st)
				B.prop("pallet", "timber", Batcher.xf(Vector3(x, y + by, z), Vector3(1.2, 0.15, 1.0), jit), kcol(0.6, 1.05))
				B.prop("box", "bone" if load == 0 else "timber",
					Batcher.xf(Vector3(x, y + by + 0.24, z), Vector3(1.08, 0.30, 0.90), jit), kcol(0.68, 1.0))
				B.detail("box", "plastic", Batcher.xf(Vector3(x, y + by + 0.24, z), Vector3(1.12, 0.05, 0.03), jit), Color(0.85, 0.85, 0.85))

## RULE. Drums live in bunds, in a grid, upright. Two bunds with a walking gap
## between them, which is the whole difference between a store and a spill.
func _fill_drums(x0: float, z0: float, x1: float, z1: float) -> void:
	var y := L.pad_h() / 1000.0
	var u := Vector3(1, 0, 0)
	var v := Vector3(0, 0, 1)
	for k in 2:
		var zc := z0 + 1.7 + (z1 - z0 - 3.4) * float(k)
		_arr_bund(Vector3((x0 + x1) * 0.5, y, zc), u, v, x1 - x0 - 0.6, 3.0, 0.0)

## RULE. A spares yard is a rack. Uprights on the 2.4 m module, three levels, and
## ONE kind of stock per bay so a bay reads as a bay.
func _fill_spares(x0: float, z0: float, x1: float, z1: float) -> void:
	var y := L.pad_h() / 1000.0
	var bays := maxi(1, int((z1 - z0) / 2.4))
	var pz := (z1 - z0) / float(bays)
	for post in [x0 + 0.35, x1 - 0.35]:
		for b in range(bays + 1):
			var z := z0 + pz * float(b)
			B.prop("angle", "ember", Batcher.xf(Vector3(post, y + 1.62, z), Vector3(0.10, 3.24, 0.10)), kcol(0.6, 0.9))
	for shelf in 3:
		var sy := y + 0.55 + 1.0 * float(shelf)
		for post2 in [x0 + 0.35, x1 - 0.35]:
			B.prop("box", "ember", Batcher.xf(Vector3(post2, sy, (z0 + z1) * 0.5), Vector3(0.09, 0.10, z1 - z0)), kcol(0.6, 0.9))
	for b2 in bays:
		var z2 := z0 + pz * (float(b2) + 0.5)
		var hold := r.randi() % 3
		for shelf2 in 3:
			var sy2 := y + 0.60 + 1.0 * float(shelf2)
			if hold == 0:
				for k in 2:
					B.prop("casebox", "bone", Batcher.xf(Vector3(x0 + (x1 - x0) * (0.3 + 0.4 * float(k)), sy2 + 0.30, z2),
						Vector3(1.7, 0.58, 0.86), PI * 0.5), kcol(0.8, 1.0))
			elif hold == 1:
				for t in 6:
					B.prop("cyl", "iron", Batcher.xf(Vector3((x0 + x1) * 0.5, sy2 + 0.14 + 0.20 * float(t / 3), z2 - 0.30 + 0.60 * float(t % 3)),
						Vector3(0.18, x1 - x0 - 1.0, 0.18), 0.0, 0.0, PI * 0.5), ircol(0.7, 1.4))
			else:
				B.prop("pallet", "timber", Batcher.xf(Vector3((x0 + x1) * 0.5, sy2 + 0.08, z2), Vector3(1.9, 0.15, 1.1), PI * 0.5), kcol(0.6, 1.0))
				B.prop("box", "bone", Batcher.xf(Vector3((x0 + x1) * 0.5, sy2 + 0.42, z2), Vector3(1.8, 0.55, 1.0), PI * 0.5), kcol(0.72, 0.95))

## RULE. Scrap is a BAY. Kerbed, painted, with three skips in a line in it, and
## the loose stock inside the kerb where it was thrown. The yard around it is not
## the scrap bay - that distinction is the whole of DESIGN-PRINCIPLES 7.
func _fill_scrap(x0: float, z0: float, x1: float, z1: float) -> void:
	var y := L.pad_h() / 1000.0
	var c := Vector3((x0 + x1) * 0.5, y, (z0 + z1) * 0.5)
	for sgn in [-1.0, 1.0]:
		B.prop("box", "stone", Batcher.xf(c + Vector3(0, 0.24, (z1 - z0) * 0.5 * sgn), Vector3(x1 - x0, 0.48, 0.22)), kcol(0.7, 0.95))
	B.prop("box", "stone", Batcher.xf(c + Vector3((x1 - x0) * 0.5, 0.24, 0), Vector3(0.22, 0.48, z1 - z0)), kcol(0.7, 0.95))
	_paint_rect(c, Vector3(1, 0, 0), Vector3(0, 0, 1), x1 - x0 - 0.9, z1 - z0 - 0.9, 0.0, Color(0.88, 0.72, 0.35))
	for k in 3:
		var sc := Vector3(x0 + 2.6, y, z0 + 1.9 + (z1 - z0 - 3.8) * float(k) / 2.0)
		_arr_skip(sc, Vector3(1, 0, 0), Vector3(0, 0, 1), 4.6, 2.4, 0.0)
	var n := int((x1 - x0) * (z1 - z0) * 0.45)
	for i in n:
		var x := r.randf_range(x0 + 5.2, x1 - 0.8)
		var z := r.randf_range(z0 + 0.8, z1 - 0.8)
		var yy := gh(x, z) + r.randf_range(0.0, 0.4)
		var col := ircol(0.5, 1.6)
		match r.randi() % 4:
			0: B.detail("angle", "iron", Batcher.xf(Vector3(x, yy, z), Vector3(0.14, r.randf_range(0.8, 2.6), 0.14), r.randf() * TAU, r.randf_range(-1.4, 1.4), r.randf_range(-1.4, 1.4)), col)
			1: B.detail("cyl", "iron", Batcher.xf(Vector3(x, yy, z), Vector3(0.24, r.randf_range(0.5, 1.8), 0.24), r.randf() * TAU, r.randf_range(-1.4, 1.4), r.randf_range(-1.4, 1.4)), col)
			2: B.detail("wheel", "iron", Batcher.xf(Vector3(x, yy, z), Vector3(r.randf_range(0.5, 1.2), r.randf_range(0.5, 1.2), 0.16), r.randf() * TAU, r.randf_range(-1.5, 1.5)), col)
			3: B.detail("ibeam", "iron", Batcher.xf(Vector3(x, yy, z), Vector3(0.22, r.randf_range(1.0, 3.2), 0.22), r.randf() * TAU, r.randf_range(-1.5, 1.5), r.randf_range(-0.4, 0.4)), col)

# ================================================================ machines
## RULE. A parametric quadruped, ~0.77 m long, built from 34 instances: hull,
## deck modules, head and sensor bar, four three-segment legs, recovery handle,
## charge port, flank strip. Pose is a parameter: STAND, DOCK (legs folded on a
## charge plate), CRADLE (up on the service frame), WRECK (rolled, one leg gone).
## Player value inversion (ART-DIRECTION 4.3): pale shell over graphite chassis.
## RULE. Every machine on this site is standing somewhere a machine would be
## STOOD: in a numbered dock bay, on a painted muster bay, on a service stand, at
## the collar waiting to be sent down, or on the lane it is walking. All of them
## square to the thing they are standing on, with two degrees of jitter.
func _machines() -> void:
	var y := L.pad_h() / 1000.0
	# four of the five dock bays, all facing their pedestal
	for i in DOCK_N:
		if i == DOCK_EMPTY:
			continue
		_walker(_dock_pos(i), PI * 0.5 + r.randf_range(-0.02, 0.02), "dock", r.randf_range(0.2, 0.5))
	# the service bay. Three machines: one on the hoist cradle outside the door,
	# one on a work stand inside with panels off, one parked square in the bay.
	var G: Dictionary = L.plan["gantry"]
	var gx := float(G["x1"]) / 1000.0 + 1.2
	var gz := float(G["z"]) / 1000.0 + 0.9
	_cradle(Vector3(gx, y, gz))
	_walker(Vector3(gx, y + 0.72, gz), -PI * 0.5, "cradle", 0.55)
	var bdg := _building("service_bay")
	if not bdg.is_empty():
		var bx0 := float(bdg["x0"]) / 1000.0
		var bx1 := float(bdg["x1"]) / 1000.0
		var bz0 := float(bdg["z0"]) / 1000.0
		var bz1 := float(bdg["z1"]) / 1000.0
		# two work stands on the 2.4 m module in front of the bench, and the
		# machines on them: the bench, the rack and the machines in one frame is the
		# whole argument that somebody builds and services these things.
		for k in 2:
			var wx := bx0 + 4.6 + 2.4 * float(k)
			_cradle(Vector3(wx, y, bz0 + 3.1))
			_walker(Vector3(wx, y + 0.72, bz0 + 3.1), -PI * 0.5, "cradle", 0.42 + 0.2 * float(k))
		# one parked square on a painted bay by the door
		_paint_rect(Vector3(bx1 - 2.4, y, bz1 - 2.4), Vector3(1, 0, 0), Vector3(0, 0, 1), 1.7, 1.4, 0.0, Color(0.92, 0.86, 0.66))
		_walker(Vector3(bx1 - 2.4, y, bz1 - 2.4), -PI * 0.5, "stand", 0.24)
		# the wreck, on a trestle at the back of the bay: the extraction loop's loss,
		# put where a lost machine would actually be put, not left where it fell.
		_trestle(Vector3(bx0 + 1.9, y, bz1 - 2.2))
		_wreck(Vector3(bx0 + 1.9, y + 0.62, bz1 - 2.2), 0.0)
	# the muster square: four machines on four painted bays, one pitch, one yaw
	var M := _zone("muster")
	if not M.is_empty():
		var mx0 := float(M["x0"]) / 1000.0
		var mx1 := float(M["x1"]) / 1000.0
		var mz := (float(M["z0"]) + float(M["z1"])) / 2000.0
		for i2 in 4:
			var mx := mx0 + 0.9 + (mx1 - mx0 - 1.8) * float(i2) / 3.0
			_paint_rect(Vector3(mx, y, mz), Vector3(1, 0, 0), Vector3(0, 0, 1), 1.5, 1.1, 0.0, Color(0.92, 0.86, 0.66))
			_walker(Vector3(mx, y, mz), -PI * 0.5 + r.randf_range(-0.02, 0.02), "stand", r.randf_range(0.15, 0.7))
	# one at the collar, square to the shaft, about to be sent down
	_walker(Vector3(-3.8, y, -1.2), 0.0, "stand", 0.62)
	# two on the lane, walking back in from the course
	_walker(Vector3(15.0, gh(15.0, 0.6), 0.6), PI, "stand", 0.30)
	_walker(Vector3(19.4, gh(19.4, -0.5), -0.5), PI, "stand", 0.38)
	# one out on the course
	var C: Dictionary = L.plan["course"]
	var nodes: Array = C["nodes"]
	if nodes.size() > 5:
		var pitch := float(C["pitch"]) / 1000.0
		var n1: Array = nodes[3]
		var p1 := Vector3(float(C["ox"]) / 1000.0 + float(n1[0]) * pitch, 0, float(C["oz"]) / 1000.0 + float(n1[1]) * pitch)
		p1.y = gh(p1.x, p1.z)
		_walker(p1, 0.0, "stand", 0.45)

## RECORD where a machine stands. It does not build one.
##
## This used to be a parametric quadruped: 34 batched instances, a hull, a head,
## four three-segment legs, and a flank strip. It was a stand-in built before the
## Blender rig had a glTF exporter, and TRAILER 11.2 is the bill for it -- every
## machine in the rough cut is this box animal and the designer spotted it in one
## frame ("the dog isnt even the right model"). The real chassis now arrive from
## agent_model through the shared machine layer, so all this does is say WHERE.
##
## The placement rules above are unchanged and they are the part worth keeping:
## every machine on this site stands somewhere a machine would be STOOD.
func _walker(base: Vector3, yaw: float, pose: String, wear: float) -> void:
	machine_slots.append({"pos": base, "yaw": yaw, "pose": pose, "wear": wear})

func _cradle(p: Vector3) -> void:
	# a yellow service cradle: a frame that holds a machine at working height
	for s in [-1.0, 1.0]:
		for s2 in [-1.0, 1.0]:
			B.prop("box", "amber", Batcher.xf(p + Vector3(s * 0.42, 0.34, s2 * 0.28), Vector3(0.06, 0.68, 0.06)), kcol(0.7, 1.0))
	B.prop("box", "amber", Batcher.xf(p + Vector3(0, 0.68, 0), Vector3(0.98, 0.06, 0.66)), kcol(0.7, 1.0))
	for k in 4:
		B.detail("box", "amber", Batcher.xf(p + Vector3(0, 0.34, -0.28 + 0.186 * float(k)), Vector3(0.92, 0.04, 0.04)), kcol(0.7, 1.0))
	B.detail("cyl", "rubber", Batcher.xf(p + Vector3(0, 0.02, 0), Vector3(0.9, 0.04, 0.66)), Color(0.9, 0.9, 0.9))

func _trestle(p: Vector3) -> void:
	for s in [-1.0, 1.0]:
		B.prop("angle", "galv", Batcher.xf(p + Vector3(s * 0.5, 0.31, -0.3), Vector3(0.06, 0.62, 0.06), 0.0, 0.0, s * 0.12), kcol())
		B.prop("angle", "galv", Batcher.xf(p + Vector3(s * 0.5, 0.31, 0.3), Vector3(0.06, 0.62, 0.06), 0.0, 0.0, s * 0.12), kcol())
	B.prop("box", "timber", Batcher.xf(p + Vector3(0, 0.62, 0), Vector3(1.2, 0.05, 0.8)), kcol(0.6, 1.0))

## a wreck: recorded, not built. ART-DIRECTION 6.2 and NOTES 11.9 -- ride at the
## crouch clip, rolled, every emissive dead, the retro still returning.
func _wreck(p: Vector3, yaw: float) -> void:
	machine_slots.append({"pos": p, "yaw": yaw, "pose": "wreck", "wear": 0.85})

func _signage() -> void:
	var spots := [Vector3(-33.0, 0, 5.0), Vector3(-33.0, 0, 2.0), Vector3(-6.0, 0, 4.6),
		Vector3(6.4, 0, 3.4), Vector3(-11.5, 0, 3.2), Vector3(31.0, 0, 2.2),
		Vector3(12.0, 0, 5.5), Vector3(-27.5, 0, 12.0)]
	# RULE. A sign faces the thing it is telling you about, so its yaw is square
	# to the site grid - not a random angle. Signs at a random angle are the tell
	# that nobody hung them.
	for s in spots:
		var y := gh(s.x, s.z)
		var yaw := 0.0 if absf(s.x) > 10.0 else PI * 0.5
		B.prop("cyl", "galv", Batcher.xf(Vector3(s.x, y + 0.85, s.z), Vector3(0.055, 1.7, 0.055)), kcol())
		B.prop("box", "bone", Batcher.xf(Vector3(s.x, y + 1.55, s.z), Vector3(0.62, 0.46, 0.015), yaw), kcol())
		B.detail("box", "amber", Batcher.xf(Vector3(s.x, y + 1.68, s.z + 0.01 * cos(yaw)), Vector3(0.4, 0.10, 0.005), yaw), Color(0.9, 0.9, 0.9))
		B.detail("box", "kitgrey", Batcher.xf(Vector3(s.x, y + 1.45, s.z + 0.01 * cos(yaw)), Vector3(0.44, 0.05, 0.005), yaw), Color(0.6, 0.6, 0.6))
		B.detail("box", "kitgrey", Batcher.xf(Vector3(s.x, y + 1.36, s.z + 0.01 * cos(yaw)), Vector3(0.36, 0.04, 0.005), yaw), Color(0.6, 0.6, 0.6))
