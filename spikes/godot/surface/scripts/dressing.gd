extends RefCounted
class_name Dressing
##
## DRESSING LAYER - THE INHERITED. The mine that drowned and never stopped
## working: riveted plate, cast iron, stone, timber, corrosion, weather.
##
## Everything here reads LAYOUT and writes instances. Nothing here may change a
## number LAYOUT produced. Floats are allowed; this is client side.
##
## Every function below is a placement RULE, not a model. The comment above each
## one is the rule as it would be written in Rust.

var L: SurfaceLayout
var B: Batcher
var r: RandomNumberGenerator

func _init(p_L: SurfaceLayout, p_B: Batcher) -> void:
	L = p_L
	B = p_B
	r = RandomNumberGenerator.new()
	r.seed = L.seed_v * 7919 + 11

# ---------------------------------------------------------------- helpers
func gh(x: float, z: float) -> float:
	return float(L.ground_mm(int(x * 1000.0), int(z * 1000.0))) / 1000.0

## corroded iron varies enormously in value; that variation IS the material
func ircol(lo: float = 0.55, hi: float = 2.1) -> Color:
	var v := r.randf_range(lo, hi)
	return Color(v * r.randf_range(0.92, 1.08), v * r.randf_range(0.88, 1.02), v * r.randf_range(0.82, 1.0))

func kcol(lo: float = 0.82, hi: float = 1.10) -> Color:
	var v := r.randf_range(lo, hi)
	return Color(v, v, v * r.randf_range(0.97, 1.03))

## a line of rivet heads from a to b - the single cheapest "this is riveted
## plate and not a box" tell there is
func rivets(a: Vector3, b: Vector3, spacing: float, size: float, mat: String = "iron") -> void:
	var d := b - a
	var n := int(d.length() / spacing)
	if n <= 0:
		return
	var up := d.normalized()
	var side := up.cross(Vector3.UP)
	if side.length_squared() < 0.01:
		side = Vector3(1, 0, 0)
	side = side.normalized()
	for i in range(n + 1):
		var p := a + d * (float(i) / float(n))
		B.detail("hex", mat, Batcher.xf(p, Vector3(size, size * 0.6, size),
			r.randf() * TAU, PI * 0.5 if absf(up.y) < 0.5 else 0.0), ircol(0.7, 1.6))

func build() -> void:
	_headframe()
	_collar_and_shaft()
	_winch(L.pad_h() / 1000.0)
	_old_buildings()
	_stack()
	_fence()
	_poles()
	_spoil_dressing()
	_course()
	_lighting_columns()
	_road_furniture()

# ================================================================= headframe
## RULE. Four battered legs from the base spread to the deck rectangle, plus a
## raked back-leg pair taking the winch pull. Horizontal ties every 1.8 m and one
## diagonal per bay per face. Deck is open grating with a handrail. Two sheaves:
## the one the rope runs on is BEARING STEEL, its neighbour is the same rust as
## the legs (ART-DIRECTION 5.2, "still in use is polished bright").
## A rivet ring at every node. One ladder, one cable, one hoist beam.
func _headframe() -> void:
	var H: Dictionary = L.plan["headframe"]
	var h := float(H["height"]) / 1000.0
	var deck := float(H["deck_h"]) / 1000.0
	var sx := float(H["spread_x"]) / 2000.0
	var sz := float(H["spread_z"]) / 2000.0
	var tx := float(H["top_x"]) / 2000.0
	var tz := float(H["top_z"]) / 2000.0
	var y0 := L.pad_h() / 1000.0

	var feet: Array = [Vector3(-sx, y0, -sz), Vector3(sx, y0, -sz), Vector3(sx, y0, sz), Vector3(-sx, y0, sz)]
	var tops: Array = [Vector3(-tx, deck, -tz), Vector3(tx, deck, -tz), Vector3(tx, deck, tz), Vector3(-tx, deck, tz)]

	# legs
	for i in 4:
		B.beam("ibeam", "iron", feet[i] - Vector3(0, 0.4, 0), tops[i], 0.42, 0.42, ircol())
		# base casting and holding-down bolts
		B.add("box", "stone", Batcher.xf(feet[i] + Vector3(0, -0.1, 0), Vector3(1.5, 0.45, 1.5)), kcol(0.75, 1.0))
		B.prop("box", "iron", Batcher.xf(feet[i] + Vector3(0, 0.16, 0), Vector3(1.05, 0.22, 1.05)), ircol())
		for k in 6:
			var a := TAU * float(k) / 6.0
			B.detail("hex", "iron", Batcher.xf(feet[i] + Vector3(cos(a) * 0.42, 0.30, sin(a) * 0.42),
				Vector3(0.09, 0.09, 0.09)), ircol(0.8, 1.7))

	# bays: ties and bracing
	var bays := int(round((deck - y0) / 1.9))
	for bi in range(1, bays + 1):
		var t := float(bi) / float(bays)
		var t0 := float(bi - 1) / float(bays)
		for i in 4:
			var j := (i + 1) % 4
			var a0: Vector3 = feet[i].lerp(tops[i], t0)
			var a1: Vector3 = feet[i].lerp(tops[i], t)
			var b0: Vector3 = feet[j].lerp(tops[j], t0)
			var b1: Vector3 = feet[j].lerp(tops[j], t)
			B.beam("angle", "iron", a1, b1, 0.20, 0.20, ircol())
			if bi % 2 == 1:
				B.beam("angle", "iron", a0, b1, 0.15, 0.15, ircol())
			else:
				B.beam("angle", "iron", a1, b0, 0.15, 0.15, ircol())
			rivets(a1 + Vector3(0, 0, 0), b1, 0.55, 0.075)

	# deck
	var dx := tx + 0.5
	var dz := tz + 0.5
	for gx in range(-3, 4):
		for gz in range(-3, 4):
			var p := Vector3(float(gx) * (dx * 2.0 / 7.0), deck + 0.06, float(gz) * (dz * 2.0 / 7.0))
			if absf(p.x) < dx and absf(p.z) < dz:
				B.add("grate", "iron", Batcher.xf(p, Vector3(dx * 2.0 / 7.0, 1.0, dz * 2.0 / 7.0)), ircol(0.7, 1.3))
	# deck beams
	B.beam("ibeam", "iron", Vector3(-dx, deck, -dz), Vector3(dx, deck, -dz), 0.36, 0.36, ircol())
	B.beam("ibeam", "iron", Vector3(-dx, deck, dz), Vector3(dx, deck, dz), 0.36, 0.36, ircol())
	B.beam("ibeam", "iron", Vector3(-dx, deck, -dz), Vector3(-dx, deck, dz), 0.36, 0.36, ircol())
	B.beam("ibeam", "iron", Vector3(dx, deck, -dz), Vector3(dx, deck, dz), 0.36, 0.36, ircol())
	# handrail on three sides
	for side in [Vector3(0, 0, -1), Vector3(0, 0, 1), Vector3(-1, 0, 0)]:
		var along := Vector3(side.z, 0, side.x)
		var ext := dx if absf(along.x) > 0.5 else dz
		var off := dz if absf(side.z) > 0.5 else dx
		for k in range(-4, 5):
			var p: Vector3 = side * off + along * (float(k) * ext / 4.0) + Vector3(0, deck, 0)
			B.prop("cyl", "iron", Batcher.xf(p + Vector3(0, 0.55, 0), Vector3(0.05, 1.1, 0.05)), ircol())
		var a: Vector3 = side * off - along * ext + Vector3(0, deck + 1.05, 0)
		var b: Vector3 = side * off + along * ext + Vector3(0, deck + 1.05, 0)
		B.beam("cyl", "iron", a, b, 0.055, 0.055, ircol())
		B.beam("cyl", "iron", a - Vector3(0, 0.5, 0), b - Vector3(0, 0.5, 0), 0.04, 0.04, ircol())

	# sheaves: axis along Z, one in use (steel rim) and one dead
	var sr := float(H["sheave_r"]) / 1000.0
	var gap := float(H["sheave_gap"]) / 1000.0
	var sy := h
	for i in 2:
		var zpos := -gap * 0.5 + gap * float(i)
		var mat := "steel" if i == 0 else "iron"
		B.add("wheel", mat, Batcher.xf(Vector3(0, sy, zpos), Vector3(sr * 2.0, sr * 2.0, 0.34)),
			kcol(0.85, 1.05) if i == 0 else ircol())
		# bearing pedestals
		for s in [-1.0, 1.0]:
			B.add("box", "iron", Batcher.xf(Vector3(0, sy - 0.05, zpos + s * 0.30), Vector3(0.5, 0.5, 0.22)), ircol())
			B.beam("ibeam", "iron", Vector3(0, deck, zpos + s * 0.30), Vector3(0, sy - 0.25, zpos + s * 0.30), 0.3, 0.3, ircol())
	# sheave-support A frame
	for s in [-1.0, 1.0]:
		B.beam("ibeam", "iron", Vector3(s * dx, deck, -gap), Vector3(0, sy + 0.2, -gap * 0.5), 0.3, 0.3, ircol())
		B.beam("ibeam", "iron", Vector3(s * dx, deck, gap), Vector3(0, sy + 0.2, gap * 0.5), 0.3, 0.3, ircol())
	# the rope: sheave -> winch pad, and sheave -> down the shaft
	var wpad := Vector3(-8.5, y0 + 0.9, -1.2)
	_rope(Vector3(0, sy - sr, -gap * 0.5), wpad, 0.05)
	_rope(Vector3(0, sy - sr, -gap * 0.5 + 0.15), Vector3(0.0, y0 - 3.5, 0.2), 0.05)

	# ladder up the north-west leg, in cages
	var lx := -sx * 0.55
	B.add("ladder", "iron", Batcher.xf(Vector3(lx, y0 + (deck - y0) * 0.5, -sz * 0.55 - 0.35),
		Vector3(0.55, deck - y0, 0.12)), ircol())
	for k in range(3, int(deck - y0), 1):
		B.prop("ring", "iron", Batcher.xf(Vector3(lx, y0 + float(k), -sz * 0.55 - 0.05),
			Vector3(1.5, 0.05, 1.5), 0.0, PI * 0.5), ircol())

	# hoist beam over the collar - THE BROUGHT bolted to the old frame
	B.beam("ibeam", "kitgrey", Vector3(-2.6, deck - 1.2, 0.0), Vector3(2.6, deck - 1.2, 0.0), 0.28, 0.28, kcol())
	B.prop("casebox", "bone", Batcher.xf(Vector3(0.9, deck - 1.55, 0.0), Vector3(0.55, 0.42, 0.42)), kcol())
	B.prop("cyl", "alu", Batcher.xf(Vector3(0.9, deck - 2.6, 0.0), Vector3(0.05, 1.8, 0.05)), kcol())
	B.prop("casebox", "kitgrey", Batcher.xf(Vector3(0.9, deck - 3.65, 0.0), Vector3(0.30, 0.35, 0.24)), kcol())

func _rope(a: Vector3, b: Vector3, w: float) -> void:
	var n := 10
	var sag := a.distance_to(b) * 0.035
	var prev := a
	for i in range(1, n + 1):
		var t := float(i) / float(n)
		var p: Vector3 = a.lerp(b, t)
		p.y -= sin(t * PI) * sag
		B.beam("cyl6", "steel", prev, p, w, w, kcol(0.5, 0.8))
		prev = p

# ============================================================ collar / shaft
## RULE. A cast collar ring on a stone plinth, a rectangular lined shaft for the
## top 3 m and bare rock below, guide rails down both long sides, a fence on
## three sides with the yard side open, and the surface end of the acoustic link
## on the plinth: a cable drum with the hydrophone cable over the edge.
func _collar_and_shaft() -> void:
	var S: Dictionary = L.plan["shaft"]
	var w := float(S["w"]) / 2000.0
	var d := float(S["d"]) / 2000.0
	var y0 := L.pad_h() / 1000.0
	var pw := float(S["plinth_w"]) / 2000.0
	var pd := float(S["plinth_d"]) / 2000.0

	# stone plinth: a frame of dressed blocks around the opening
	var blocks := 0
	for i in range(-6, 7):
		for side in [-1.0, 1.0]:
			var bx := float(i) * (pw * 2.0 / 13.0)
			if absf(bx) < pw:
				B.add("box", "stone", Batcher.xf(Vector3(bx, y0 + 0.20, side * (pd - 0.42)),
					Vector3(pw * 2.0 / 13.0 - 0.03, 0.42, 0.86)), kcol(0.7, 1.05))
				blocks += 1
			var bz := float(i) * (pd * 2.0 / 13.0)
			if absf(bz) < pd - 0.8:
				B.add("box", "stone", Batcher.xf(Vector3(side * (pw - 0.42), y0 + 0.20, bz),
					Vector3(0.86, 0.42, pd * 2.0 / 13.0 - 0.03)), kcol(0.7, 1.05))
				blocks += 1

	# cast collar: four ribbed castings around the mouth, bolts on the 0.6 module
	for side in [-1.0, 1.0]:
		B.add("box", "iron", Batcher.xf(Vector3(0, y0 + 0.46, side * (d + 0.22)), Vector3(w * 2.0 + 0.9, 0.30, 0.44)), ircol())
		B.add("box", "iron", Batcher.xf(Vector3(side * (w + 0.22), y0 + 0.46, 0), Vector3(0.44, 0.30, d * 2.0 - 0.02)), ircol())
		rivets(Vector3(-w - 0.3, y0 + 0.60, side * (d + 0.22)), Vector3(w + 0.3, y0 + 0.60, side * (d + 0.22)), 0.30, 0.08)
	# lining: iron plate rings for the top 3 m, then rock
	var lined := float(S["lined_depth"]) / 1000.0
	var depth := float(S["depth"]) / 1000.0
	## RULE. Value falls off with depth: everything below the collar is
	## multiplied by 1/(1 + (depth/2.2)^2), which is the inverse-square a
	## rectangular sky hole actually delivers. Three metres down it is 35%; at
	## eight metres it is 7%; and the shaft reads as a hole rather than a box.
	var ring := 0
	var yy := y0 + 0.3
	while yy > y0 - depth:
		var seg := 0.75 if yy > y0 - lined else 2.5
		var mat := "iron" if yy > y0 - lined else "rock"
		var dep := (y0 - yy) / 2.2
		var fall := 1.0 / (1.0 + dep * dep)
		var cc := (ircol(0.4, 1.2) if mat == "iron" else kcol(0.5, 0.9)) * fall
		cc.a = 1.0
		for side2 in [-1.0, 1.0]:
			B.add("box", mat, Batcher.xf(Vector3(0, yy - seg * 0.5, side2 * (d + 0.16)),
				Vector3(w * 2.0 + 0.64, seg * 0.98, 0.32)), cc)
			B.add("box", mat, Batcher.xf(Vector3(side2 * (w + 0.16), yy - seg * 0.5, 0),
				Vector3(0.32, seg * 0.98, d * 2.0), 0.0), cc)
		if mat == "iron":
			rivets(Vector3(-w, yy, -d - 0.16), Vector3(w, yy, -d - 0.16), 0.28, 0.07)
			# timber bunton sets across the shaft, on the 1.2 m module
			if ring % 2 == 0:
				B.add("box", "timber", Batcher.xf(Vector3(0, yy - 0.05, 0), Vector3(w * 2.0, 0.16, 0.20)), cc)
		yy -= seg
		ring += 1
	_cage(y0)
	# a black floor a long way down, so the hole is a hole
	B.add("box", "rock", Batcher.xf(Vector3(0, y0 - depth - 0.5, 0), Vector3(w * 2.6, 1.0, d * 2.6)), Color(0.15, 0.15, 0.15))
	# guide rails
	for side3 in [-1.0, 1.0]:
		B.beam("channel", "steel", Vector3(side3 * (w - 0.12), y0 + 0.4, 0), Vector3(side3 * (w - 0.12), y0 - depth * 0.8, 0), 0.12, 0.16, kcol(0.6, 0.9))

	# fence on three sides (the yard side, west, is open so a machine can walk in)
	for side4 in [-1.0, 1.0]:
		_rail_run(Vector3(-pw, y0, side4 * pd), Vector3(pw, y0, side4 * pd), 1.1)
	_rail_run(Vector3(pw, y0, -pd), Vector3(pw, y0, pd), 1.1)

	# the surface end of the acoustic link: drum, cable over the lip, and the post
	var lp: Dictionary = L.plan["stations"][0]
	var px := float(lp["x"]) / 1000.0
	var pz := float(lp["z"]) / 1000.0
	B.prop("wheel", "kitgrey", Batcher.xf(Vector3(px, y0 + 0.55, pz), Vector3(0.9, 0.9, 0.62), 0.0, 0.0, PI * 0.5), kcol())
	for k in 3:
		B.prop("cyl", "galv", Batcher.xf(Vector3(px + 0.5 * cos(2.1 * float(k)), y0 + 0.28, pz + 0.5 * sin(2.1 * float(k))),
			Vector3(0.05, 0.56, 0.05), 0.0, r.randf_range(-0.12, 0.12)), kcol())
	# the cable, running to the collar lip and over it
	var prev := Vector3(px, y0 + 0.30, pz)
	var pts := [Vector3(px + 0.8, y0 + 0.16, pz - 0.6), Vector3(-1.2, y0 + 0.16, 0.9),
		Vector3(-w - 0.2, y0 + 0.62, 0.5), Vector3(-w + 0.1, y0 - 0.6, 0.45), Vector3(-w + 0.15, y0 - 6.0, 0.4)]
	for p in pts:
		B.beam("cyl6", "rubber", prev, p, 0.035, 0.035, kcol(0.8, 1.0))
		prev = p

## RULE. The cage sits one metre into the collar with its gate open: a
## galvanised open frame on a four-rope bridle to a single rope, floor of
## grating so a machine standing in it reads from below. Vision board guess 6.
func _cage(y0: float) -> void:
	var S: Dictionary = L.plan["shaft"]
	var w := float(S["w"]) / 2000.0 - 0.22
	var d := float(S["d"]) / 2000.0 - 0.22
	var fy := y0 - 1.1
	var ch := 1.5
	B.add("grate", "galv", Batcher.xf(Vector3(0, fy, 0), Vector3(w * 2.0, 1.0, d * 2.0)), kcol(0.7, 1.0))
	for sx in [-1.0, 1.0]:
		for sz in [-1.0, 1.0]:
			B.add("angle", "galv", Batcher.xf(Vector3(sx * w, fy + ch * 0.5, sz * d), Vector3(0.07, ch, 0.07)), kcol(0.7, 1.0))
	for lvl in [0.35, 0.95, 1.45]:
		for sz2 in [-1.0, 1.0]:
			B.add("box", "galv", Batcher.xf(Vector3(0, fy + lvl, sz2 * d), Vector3(w * 2.0, 0.05, 0.05)), kcol(0.7, 1.0))
		B.add("box", "galv", Batcher.xf(Vector3(-w, fy + lvl, 0), Vector3(0.05, 0.05, d * 2.0)), kcol(0.7, 1.0))
	# the bridle, four ropes converging on one
	for sx2 in [-1.0, 1.0]:
		for sz3 in [-1.0, 1.0]:
			B.add("cyl6", "steel", Batcher.beam_xf(Vector3(sx2 * w, fy + ch, sz3 * d),
				Vector3(0, fy + ch + 1.3, 0), 0.014, 0.014), kcol(0.5, 0.8))
	B.add("cyl6", "steel", Batcher.xf(Vector3(0, fy + ch + 1.9, 0), Vector3(0.05, 1.2, 0.05)), kcol(0.5, 0.8))

## RULE. The modern winch: a skid-mounted drum on a cast pad the old engine used
## to sit on, with a control box and a bollard fairlead. THE BROUGHT, at the one
## point where it has to move the old machine's load.
func _winch(y0: float) -> void:
	var p := Vector3(-8.5, y0, -1.2)
	B.add("box", "stone", Batcher.xf(p + Vector3(0, 0.18, 0), Vector3(3.6, 0.36, 2.6)), kcol(0.7, 1.0))
	B.add("casebox", "kitgrey", Batcher.xf(p + Vector3(0, 0.72, 0), Vector3(2.9, 0.68, 1.9)), kcol())
	B.add("wheel", "steel", Batcher.xf(p + Vector3(0, 1.15, 0), Vector3(1.5, 1.5, 1.5), 0.0, 0.0, PI * 0.5), kcol(0.6, 0.9))
	for k in 22:
		B.detail("cyl6", "steel", Batcher.xf(p + Vector3(-0.68 + 0.062 * float(k), 1.15, 0),
			Vector3(0.055, 1.42, 0.055), 0.0, 0.0, PI * 0.5), kcol(0.45, 0.75))
	B.prop("casebox", "kitgrey", Batcher.xf(p + Vector3(1.9, 0.85, 0.6), Vector3(0.6, 1.6, 0.5)), kcol())
	B.detail("box", "amber", Batcher.xf(p + Vector3(1.62, 1.2, 0.6), Vector3(0.02, 0.26, 0.36)), Color(0.9, 0.9, 0.9))
	B.prop("bollard", "iron", Batcher.xf(p + Vector3(2.3, 0.5, -0.9), Vector3(0.3, 1.0, 0.3)), ircol())
	_cable_tray(p + Vector3(1.9, 0.12, 1.0), Vector3(-19.0, 0.12, 0.5))

func _cable_tray(a: Vector3, b: Vector3) -> void:
	B.prop("channel", "alu", Batcher.beam_xf(a, b, 0.26, 0.12), kcol())
	var dir := (b - a).normalized()
	var side := dir.cross(Vector3.UP).normalized()
	for i in 4:
		B.detail("cyl6", "rubber", Batcher.beam_xf(a + side * (-0.09 + 0.06 * float(i)),
			b + side * (-0.09 + 0.06 * float(i)), 0.026, 0.026), Color(0.9, 0.9, 0.9))

# generic handrail / fence run
func _rail_run(a: Vector3, b: Vector3, h: float) -> void:
	var n := maxi(2, int(a.distance_to(b) / 1.5))
	for i in range(n + 1):
		var p: Vector3 = a.lerp(b, float(i) / float(n))
		B.prop("cyl", "galv", Batcher.xf(p + Vector3(0, h * 0.5, 0), Vector3(0.05, h, 0.05)), kcol())
	B.beam("cyl", "galv", a + Vector3(0, h, 0), b + Vector3(0, h, 0), 0.045, 0.045, kcol())
	B.beam("cyl", "galv", a + Vector3(0, h * 0.55, 0), b + Vector3(0, h * 0.55, 0), 0.04, 0.04, kcol())
	B.beam("box", "galv", a + Vector3(0, 0.09, 0), b + Vector3(0, 0.09, 0), 0.02, 0.16, kcol())

# ========================================================== old buildings
## RULE. A ruined masonry shell: walls built as 0.6 m piers whose top height is
## noise * the nominal, so the parapet is broken; openings punched on a 2.4 m
## rhythm; a corbel course; rubble at the foot of every wall. If roof = 1, rusted
## trusses and corrugated sheets with a seeded fraction missing.
func _old_buildings() -> void:
	for bdg in L.plan["buildings"]:
		if bdg["reg"] != "old":
			continue
		_ruined_shell(bdg)
	_winding_gear()

func _ruined_shell(bdg: Dictionary) -> void:
	var x0 := float(bdg["x0"]) / 1000.0
	var z0 := float(bdg["z0"]) / 1000.0
	var x1 := float(bdg["x1"]) / 1000.0
	var z1 := float(bdg["z1"]) / 1000.0
	var hh := float(bdg["h"]) / 1000.0
	var walls := [[Vector2(x0, z0), Vector2(x1, z0)], [Vector2(x1, z0), Vector2(x1, z1)],
		[Vector2(x1, z1), Vector2(x0, z1)], [Vector2(x0, z1), Vector2(x0, z0)]]
	var pier := 0.6
	for wi in walls.size():
		var w: Array = walls[wi]
		var a: Vector2 = w[0]
		var b: Vector2 = w[1]
		var len := a.distance_to(b)
		var n := int(len / pier)
		var dir := (b - a) / float(n)
		var nrm := Vector2(dir.y, -dir.x).normalized()
		for i in n:
			var c: Vector2 = a + dir * (float(i) + 0.5)
			var y0 := gh(c.x, c.y)
			var frac := float(i) / float(n)
			var top := hh * (0.62 + 0.38 * (0.5 + 0.5 * sin(frac * 9.0 + float(wi) * 2.3 + float(L.seed_v % 17))))
			top *= r.randf_range(0.94, 1.06)
			# openings: a 2.4 m rhythm, and the gable wall gets a big one
			var opening := (i % 4 == 1) and top > hh * 0.7
			var doorway := (wi == 0 and i == n / 2)
			if doorway:
				top = hh * 0.35
			B.add("box", "stone", Batcher.xf(Vector3(c.x, y0 + top * 0.5, c.y),
				Vector3(pier * 1.02, top, 0.62), atan2(dir.y, dir.x)), kcol(0.62, 1.12))
			if opening:
				B.add("box", "stone", Batcher.xf(Vector3(c.x, y0 + top * 0.42, c.y),
					Vector3(pier * 0.55, top * 0.42, 0.70), atan2(dir.y, dir.x)), Color(0.10, 0.10, 0.10))
				# a timber lintel, sagging
				B.prop("box", "timber", Batcher.xf(Vector3(c.x, y0 + top * 0.64, c.y),
					Vector3(pier * 0.9, 0.14, 0.72), atan2(dir.y, dir.x), 0.0, r.randf_range(-0.05, 0.05)), kcol(0.7, 1.1))
			# coping and corbels
			if r.randf() < 0.7:
				B.prop("box", "stone", Batcher.xf(Vector3(c.x, y0 + top + 0.09, c.y),
					Vector3(pier * 0.95, 0.18, 0.74), atan2(dir.y, dir.x) + r.randf_range(-0.05, 0.05)), kcol(0.7, 1.15))
			# rubble at the foot
			for k in 3:
				var o := nrm * r.randf_range(0.4, 1.6) + dir * r.randf_range(-0.3, 0.3)
				var rr := r.randf_range(0.12, 0.42)
				B.detail("rock" if k % 2 == 0 else "rock2", "stone",
					Batcher.xf(Vector3(c.x + o.x, gh(c.x + o.x, c.y + o.y) + rr * 0.3, c.y + o.y),
						Vector3(rr, rr * 0.7, rr * r.randf_range(0.8, 1.4)), r.randf() * TAU), kcol(0.6, 1.1))
	if int(bdg["roof"]) == 1:
		_roof(x0, z0, x1, z1, hh)

func _roof(x0: float, z0: float, x1: float, z1: float, hh: float) -> void:
	var span := z1 - z0
	var n := int((x1 - x0) / 2.4)
	for i in range(n + 1):
		var x := x0 + (x1 - x0) * float(i) / float(n)
		var apex := Vector3(x, hh + 0.9, (z0 + z1) * 0.5)
		B.beam("ibeam", "iron", Vector3(x, hh, z0), apex, 0.16, 0.16, ircol())
		B.beam("ibeam", "iron", Vector3(x, hh, z1), apex, 0.16, 0.16, ircol())
		B.beam("angle", "iron", Vector3(x, hh, z0), Vector3(x, hh, z1), 0.12, 0.12, ircol())
	# corrugated sheets, some missing
	var sheets := int((x1 - x0) / 0.9)
	for i in sheets:
		var x := x0 + 0.9 * (float(i) + 0.5)
		for side in [-1.0, 1.0]:
			if r.randf() < 0.22:
				continue
			var mid := Vector3(x, hh + 0.45, (z0 + z1) * 0.5 + side * span * 0.25)
			var pitch: float = atan2(0.9, span * 0.5) * side
			B.add("box", "iron", Batcher.xf(mid, Vector3(0.88, 0.03, sqrt(span * span * 0.25 + 0.81) * 0.5),
				0.0, pitch, 0.0), ircol(0.5, 1.4))
			# corrugations
			for k in 5:
				B.detail("cyl6", "iron", Batcher.xf(mid + Vector3(-0.35 + 0.175 * float(k), 0.03, 0.0),
					Vector3(0.05, sqrt(span * span * 0.25 + 0.81) * 0.5, 0.05), 0.0, PI * 0.5 + pitch, 0.0), ircol(0.5, 1.4))

## RULE. The winding house keeps its engine: a flywheel on a stone bed, a drum,
## a governor, and the pipework that fed it. All dead, none of it moving.
func _winding_gear() -> void:
	var cx := 11.5
	var cz := -15.0
	var y := gh(cx, cz)
	B.add("box", "stone", Batcher.xf(Vector3(cx, y + 0.5, cz), Vector3(6.0, 1.0, 3.0)), kcol(0.7, 1.0))
	B.add("wheel", "iron", Batcher.xf(Vector3(cx - 1.6, y + 3.0, cz), Vector3(4.6, 4.6, 0.42), 0.0, 0.0, 0.0), ircol())
	B.add("cyl", "iron", Batcher.xf(Vector3(cx + 1.6, y + 2.2, cz), Vector3(2.2, 2.6, 2.2), 0.0, 0.0, PI * 0.5), ircol())
	for k in 8:
		var a := TAU * float(k) / 8.0
		B.prop("hex", "iron", Batcher.xf(Vector3(cx + 1.6 + cos(a) * 1.15, y + 2.2 + sin(a) * 1.15, cz - 1.3),
			Vector3(0.16, 0.12, 0.16), 0.0, PI * 0.5), ircol(0.8, 1.7))
	B.beam("cyl", "iron", Vector3(cx - 1.6, y + 3.0, cz + 0.6), Vector3(cx + 1.6, y + 2.2, cz + 0.6), 0.16, 0.16, ircol())
	# pipework off the bed and out through the wall
	var pp := Vector3(cx + 2.6, y + 0.6, cz + 1.4)
	for k in 6:
		var nx := pp + Vector3(r.randf_range(-0.4, 1.2), r.randf_range(-0.1, 0.9), r.randf_range(0.4, 1.4))
		B.prop("cyl", "iron", Batcher.beam_xf(pp, nx, 0.16, 0.16), ircol())
		B.prop("ring", "iron", Batcher.xf(nx, Vector3(0.34, 0.10, 0.34), 0.0, PI * 0.5), ircol())
		pp = nx

# ================================================================== stack
## RULE. A tapered brick stack in 1.2 m lifts, iron banding every third lift,
## a cracked cap and a lightning conductor down one face.
func _stack() -> void:
	for m in L.plan["masts"]:
		if m["kind"] != "stack":
			continue
		var x := float(m["x"]) / 1000.0
		var z := float(m["z"]) / 1000.0
		var h := float(m["h"]) / 1000.0
		var y := gh(x, z)
		var lifts := int(h / 1.2)
		B.add("box", "stone", Batcher.xf(Vector3(x, y + 0.6, z), Vector3(4.2, 1.2, 4.2)), kcol(0.7, 1.0))
		for i in lifts:
			var t := float(i) / float(lifts)
			var rr := 2.0 - 1.15 * t
			B.add("cyl", "brick", Batcher.xf(Vector3(x, y + 1.2 + 1.2 * float(i) + 0.6, z),
				Vector3(rr * 2.0, 1.22, rr * 2.0), float(i) * 0.11), kcol(0.65, 1.2))
			if i % 3 == 2:
				B.prop("ring", "iron", Batcher.xf(Vector3(x, y + 1.2 + 1.2 * float(i) + 1.15, z),
					Vector3(rr * 2.14, 0.12, rr * 2.14)), ircol())
		B.prop("ring", "stone", Batcher.xf(Vector3(x, y + h + 0.2, z), Vector3(2.0, 0.35, 2.0)), kcol(0.75, 1.05))
		B.beam("cyl6", "iron", Vector3(x + 1.4, y + h, z), Vector3(x + 2.0, y, z), 0.035, 0.035, ircol())

# ================================================================== fence
## RULE. The perimeter is corrugated hoarding on angle posts at 3 m, with three
## rails, barbed-wire arms raked outward, and a seeded 6% of panels missing,
## leaning or replaced with mesh. The gate span is left open.
func _fence() -> void:
	var pts: Array = L.plan["fence"]
	var h := float(L.plan["fence_h"]) / 1000.0
	var gate: Dictionary = L.plan["gate"]
	var gx := float(gate["x"]) / 1000.0
	var gz0 := float(gate["z0"]) / 1000.0
	var gz1 := float(gate["z1"]) / 1000.0
	for i in range(pts.size() - 1):
		var a := Vector2(float(pts[i][0]) / 1000.0, float(pts[i][1]) / 1000.0)
		var b := Vector2(float(pts[i + 1][0]) / 1000.0, float(pts[i + 1][1]) / 1000.0)
		var len := a.distance_to(b)
		var n := int(len / 3.0)
		var dir := (b - a).normalized()
		for k in range(n + 1):
			var c: Vector2 = a + dir * (float(k) * 3.0)
			if absf(c.x - gx) < 0.5 and c.y > gz0 - 0.5 and c.y < gz1 + 0.5:
				continue
			var y := gh(c.x, c.y)
			B.prop("angle", "galv", Batcher.xf(Vector3(c.x, y + h * 0.5, c.y),
				Vector3(0.11, h + 0.2, 0.11), atan2(dir.y, dir.x)), kcol(0.6, 1.0))
			# barbed arm
			B.detail("cyl", "galv", Batcher.xf(Vector3(c.x, y + h + 0.18, c.y),
				Vector3(0.03, 0.45, 0.03), atan2(dir.y, dir.x), 0.0, 0.6), kcol(0.6, 1.0))
			if k < n:
				var c2: Vector2 = a + dir * (float(k) * 3.0 + 3.0)
				if absf(c2.x - gx) < 0.5 and c2.y > gz0 - 0.5 and c2.y < gz1 + 0.5:
					continue
				var mid: Vector2 = (c + c2) * 0.5
				var ym := gh(mid.x, mid.y)
				var roll := 0.0
				var missing := r.randf() < 0.06
				if r.randf() < 0.10:
					roll = r.randf_range(-0.22, 0.22)
				if not missing:
					# hoarding sheets, 0.75 m wide, with corrugations
					for s in 4:
						var pc: Vector2 = c + dir * (0.375 + 0.75 * float(s))
						var yc := gh(pc.x, pc.y)
						B.prop("box", "iron", Batcher.xf(Vector3(pc.x, yc + h * 0.5 + 0.1, pc.y),
							Vector3(0.74, h, 0.03), atan2(dir.y, dir.x), 0.0, roll), ircol(0.45, 1.5))
						for cg in 4:
							B.detail("cyl6", "iron", Batcher.xf(
								Vector3(pc.x, yc + h * 0.5 + 0.1, pc.y) + Vector3(dir.x, 0, dir.y) * (-0.28 + 0.185 * float(cg)),
								Vector3(0.04, h, 0.04), atan2(dir.y, dir.x), 0.0, roll), ircol(0.45, 1.5))
				# rails
				for rh in [0.25, h * 0.55, h - 0.1]:
					B.detail("box", "galv", Batcher.beam_xf(Vector3(c.x, ym + rh, c.y), Vector3(c2.x, ym + rh, c2.y), 0.05, 0.05), kcol(0.55, 0.95))
				# wire above
				for wy in [h + 0.20, h + 0.35]:
					B.detail("cyl6", "galv", Batcher.beam_xf(Vector3(c.x, ym + wy, c.y), Vector3(c2.x, ym + wy, c2.y), 0.014, 0.014), kcol(0.5, 0.9))
	# the gate itself, hung open
	var y := gh(gx, gz0)
	B.prop("box", "galv", Batcher.xf(Vector3(gx - 1.4, y + 1.2, gz0 - 1.2), Vector3(3.2, 2.3, 0.08), 0.9), kcol())
	for k in 8:
		B.detail("cyl", "galv", Batcher.xf(Vector3(gx - 1.4, y + 1.2, gz0 - 1.2) + Vector3(cos(0.9), 0, sin(0.9)) * (-1.4 + 0.4 * float(k)),
			Vector3(0.05, 2.3, 0.05), 0.9), kcol())

# ================================================================== poles
## RULE. Timber poles at 22 m carrying a crossarm of porcelain insulators and
## four conductors. The catenary is ten segments with a sag of 3.5% of the span:
## the only thing in the frame that is a curve, which is why it reads.
func _poles() -> void:
	var poles: Array = L.plan["poles"]
	for i in poles.size():
		var p: Dictionary = poles[i]
		var x := float(p["x"]) / 1000.0
		var z := float(p["z"]) / 1000.0
		var h := float(p["h"]) / 1000.0
		var y := gh(x, z)
		B.add("cyl", "timber", Batcher.xf(Vector3(x, y + h * 0.5 - 0.5, z), Vector3(0.34, h, 0.34)), kcol(0.6, 1.1))
		B.prop("box", "timber", Batcher.xf(Vector3(x, y + h - 0.75, z), Vector3(0.16, 0.16, 2.6)), kcol(0.6, 1.1))
		B.prop("box", "timber", Batcher.xf(Vector3(x, y + h - 1.55, z), Vector3(0.14, 0.14, 1.9)), kcol(0.6, 1.1))
		B.prop("angle", "iron", Batcher.xf(Vector3(x, y + h - 1.15, z + 0.55), Vector3(0.08, 1.1, 0.08), 0.0, 0.0, 0.42), ircol())
		B.prop("angle", "iron", Batcher.xf(Vector3(x, y + h - 1.15, z - 0.55), Vector3(0.08, 1.1, 0.08), 0.0, 0.0, -0.42), ircol())
		for k in 4:
			var zz := z - 1.15 + 0.77 * float(k)
			B.detail("cyl", "bone", Batcher.xf(Vector3(x, y + h - 0.55, zz), Vector3(0.17, 0.20, 0.17)), Color(1, 1, 1))
			B.detail("cyl", "bone", Batcher.xf(Vector3(x, y + h - 0.40, zz), Vector3(0.12, 0.14, 0.12)), Color(1, 1, 1))
		if i > 0:
			var q: Dictionary = poles[i - 1]
			var qx := float(q["x"]) / 1000.0
			var qz := float(q["z"]) / 1000.0
			var qy := gh(qx, qz) + float(q["h"]) - 0.4
			for k in 4:
				var a := Vector3(x, y + h - 0.4, z - 1.15 + 0.77 * float(k))
				var b := Vector3(qx, gh(qx, qz) + float(q["h"]) / 1000.0 - 0.4, qz - 1.15 + 0.77 * float(k))
				_catenary(a, b, 0.028)

func _catenary(a: Vector3, b: Vector3, w: float) -> void:
	var n := 8
	var sag := a.distance_to(b) * 0.045
	var prev := a
	for i in range(1, n + 1):
		var t := float(i) / float(n)
		var p: Vector3 = a.lerp(b, t)
		p.y -= sin(t * PI) * sag
		B.add("cyl6", "iron", Batcher.beam_xf(prev, p, w, w), Color(0.5, 0.5, 0.5))
		prev = p

# ============================================================ spoil dressing
## RULE. The height field already makes the tips. Dressing puts loose stock on
## them: 1 lump per 6 m^2, biased to the toe, plus timber and iron thrown out
## with the waste. Nothing casts a shadow below 0.35 m.
func _spoil_dressing() -> void:
	for t in L.plan["spoil"]:
		var cx := float(t["cx"]) / 1000.0
		var cz := float(t["cz"]) / 1000.0
		var rr := float(t["r"]) / 1000.0
		if absf(cx) > 110.0 or absf(cz) > 100.0:
			continue
		var n := int(rr * rr * 0.16)
		for i in n:
			var a := r.randf() * TAU
			var d := sqrt(r.randf()) * rr
			var x := cx + cos(a) * d
			var z := cz + sin(a) * d
			var s := r.randf_range(0.10, 0.75) * (0.5 + 0.5 * d / rr)
			var mesh: String = ["rock", "rock2", "rock3", "chip"][r.randi() % 4]
			B.detail(mesh, "rock", Batcher.xf(Vector3(x, gh(x, z) + s * 0.22, z),
				Vector3(s, s * r.randf_range(0.5, 0.9), s * r.randf_range(0.8, 1.3)),
				r.randf() * TAU, r.randf_range(-0.3, 0.3), r.randf_range(-0.3, 0.3)), kcol(0.55, 1.25))
		# thrown-out timber and iron
		for i in int(rr * 0.7):
			var a2 := r.randf() * TAU
			var d2 := sqrt(r.randf()) * rr
			var x2 := cx + cos(a2) * d2
			var z2 := cz + sin(a2) * d2
			if r.randf() < 0.5:
				B.detail("box", "timber", Batcher.xf(Vector3(x2, gh(x2, z2) + 0.08, z2),
					Vector3(r.randf_range(0.12, 0.24), 0.1, r.randf_range(1.2, 2.6)), r.randf() * TAU, 0.0, r.randf_range(-0.2, 0.2)), kcol(0.6, 1.1))
			else:
				B.detail("angle", "iron", Batcher.xf(Vector3(x2, gh(x2, z2) + 0.1, z2),
					Vector3(0.14, r.randf_range(0.8, 2.2), 0.14), r.randf() * TAU, PI * 0.5, r.randf_range(-0.3, 0.3)), ircol())

# ================================================================== course
## RULE (DESIGN-PRINCIPLES 3 - teaching is a physical act). The corridor graph
## from LAYOUT is extruded as two hoarding walls per edge, 1.2 m high on timber
## posts at 1.2 m: above a machine's head, below a person's eye, which is the
## whole point of the course. Nodes are cut back so a junction reads as a
## junction. The root carries a galvanised post with a WARM_DIM pilot; every
## junction carries a stencilled number plate; the cargo leaf holds a crate.
func _course() -> void:
	var C: Dictionary = L.plan["course"]
	var pitch := float(C["pitch"]) / 1000.0
	var ox := float(C["ox"]) / 1000.0
	var oz := float(C["oz"]) / 1000.0
	var hw := float(C["half_w"]) / 1000.0
	var wh := float(C["wall_h"]) / 1000.0
	var nodes: Array = C["nodes"]
	var function_of := func(n: Array) -> Vector2:
		return Vector2(ox + float(n[0]) * pitch, oz + float(n[1]) * pitch)
	for e in C["edges"]:
		var a: Vector2 = function_of.call(nodes[e[0]])
		var b: Vector2 = function_of.call(nodes[e[1]])
		var dir := (b - a).normalized()
		var nrm := Vector2(-dir.y, dir.x)
		var len := a.distance_to(b)
		# cut back 1.3 m at each node so junctions open out
		var a2 := a + dir * 1.3
		var b2 := b - dir * 1.3
		var l2 := a2.distance_to(b2)
		if l2 <= 0.5:
			continue
		var panels := maxi(1, int(l2 / 1.2))
		for side in [-1.0, 1.0]:
			for i in panels:
				var t := (float(i) + 0.5) / float(panels)
				var p: Vector2 = a2 + (b2 - a2) * t + nrm * side * hw
				var y := gh(p.x, p.y)
				var yaw := atan2(dir.y, dir.x)
				B.prop("box", "iron", Batcher.xf(Vector3(p.x, y + wh * 0.5, p.y),
					Vector3(l2 / float(panels) * 0.99, wh, 0.03), yaw), ircol(0.5, 1.5))
				for cg in 5:
					B.detail("cyl6", "iron", Batcher.xf(
						Vector3(p.x, y + wh * 0.5, p.y) + Vector3(dir.x, 0, dir.y) * ((float(cg) / 4.0 - 0.5) * l2 / float(panels) * 0.9),
						Vector3(0.045, wh, 0.045), yaw), ircol(0.5, 1.5))
				# posts and a top rail
				var pp: Vector2 = a2 + (b2 - a2) * (float(i) / float(panels)) + nrm * side * hw
				B.prop("box", "timber", Batcher.xf(Vector3(pp.x, gh(pp.x, pp.y) + wh * 0.55, pp.y),
					Vector3(0.10, wh + 0.22, 0.10), yaw), kcol(0.6, 1.05))
			var pa: Vector2 = a2 + nrm * side * hw
			var pb: Vector2 = b2 + nrm * side * hw
			B.detail("box", "timber", Batcher.beam_xf(Vector3(pa.x, gh(pa.x, pa.y) + wh + 0.08, pa.y),
				Vector3(pb.x, gh(pb.x, pb.y) + wh + 0.08, pb.y), 0.09, 0.07), kcol(0.6, 1.05))
	# node furniture: a number plate on a post at every junction
	for i in nodes.size():
		var p: Vector2 = function_of.call(nodes[i])
		var y := gh(p.x, p.y)
		if i == 0:
			# the root post: the course's "shaft" beacon
			B.prop("cyl", "galv", Batcher.xf(Vector3(p.x, y + 0.9, p.y), Vector3(0.16, 1.8, 0.16)), kcol())
			B.prop("casebox", "kitgrey", Batcher.xf(Vector3(p.x, y + 1.9, p.y), Vector3(0.26, 0.26, 0.26)), kcol())
			B.add("cyl", "amber", Batcher.xf(Vector3(p.x, y + 2.06, p.y), Vector3(0.14, 0.08, 0.14)), Color(1, 1, 1), Batcher.SITE, true)
			continue
		B.prop("cyl", "galv", Batcher.xf(Vector3(p.x + 0.55, y + 0.7, p.y + 0.55), Vector3(0.06, 1.4, 0.06)), kcol())
		B.prop("box", "bone", Batcher.xf(Vector3(p.x + 0.55, y + 1.28, p.y + 0.55),
			Vector3(0.30, 0.22, 0.02), r.randf_range(-0.3, 0.3)), kcol(0.9, 1.05))
	# the cargo leaf holds a pale crate and a few stones
	var cl: int = C["cargo_leaf"]
	if cl < nodes.size():
		var p2: Vector2 = function_of.call(nodes[cl])
		var y2 := gh(p2.x, p2.y)
		B.prop("casebox", "bone", Batcher.xf(Vector3(p2.x, y2 + 0.28, p2.y), Vector3(0.66, 0.56, 0.48), 0.4), kcol())
		for k in 7:
			B.detail("rock", "rock", Batcher.xf(Vector3(p2.x + r.randf_range(-0.9, 0.9), y2 + 0.06, p2.y + r.randf_range(-0.9, 0.9)),
				Vector3(0.16, 0.11, 0.14), r.randf() * TAU), kcol(0.7, 1.2))

# ========================================================= lighting columns
## RULE. A tapered column with a base door and a duct stub, one or two flood
## heads on a raked bracket. THE BROUGHT: galvanised, recent, bolted to a pad
## that was cast for something else.
func _lighting_columns() -> void:
	for c in L.plan["columns"]:
		var x := float(c["x"]) / 1000.0
		var z := float(c["z"]) / 1000.0
		var h := float(c["h"]) / 1000.0
		var y := gh(x, z)
		B.add("box", "stone", Batcher.xf(Vector3(x, y + 0.12, z), Vector3(0.9, 0.3, 0.9)), kcol(0.7, 1.0))
		B.add("cyl", "galv", Batcher.xf(Vector3(x, y + h * 0.5, z), Vector3(0.24, h, 0.24)), kcol(0.7, 1.05))
		B.add("cyl", "galv", Batcher.xf(Vector3(x, y + h * 0.86, z), Vector3(0.15, h * 0.3, 0.15)), kcol(0.7, 1.05))
		B.prop("casebox", "kitgrey", Batcher.xf(Vector3(x, y + 0.75, z), Vector3(0.20, 0.55, 0.12)), kcol())
		for k in range(int(c["heads"]) + 1):
			var a := float(k) * 1.4
			var arm := Vector3(cos(a) * 0.9, 0, sin(a) * 0.9)
			B.prop("cyl", "galv", Batcher.beam_xf(Vector3(x, y + h, z), Vector3(x, y + h + 0.25, z) + arm, 0.07, 0.07), kcol())
			B.prop("casebox", "kitgrey", Batcher.xf(Vector3(x, y + h + 0.20, z) + arm,
				Vector3(0.62, 0.16, 0.42), a, 0.35), kcol())
			B.add("box", "glass", Batcher.xf(Vector3(x, y + h + 0.12, z) + arm * 1.02,
				Vector3(0.55, 0.03, 0.36), a, 0.35), Color(1, 1, 1))
		for k in 4:
			var aa := TAU * float(k) / 4.0
			B.detail("hex", "galv", Batcher.xf(Vector3(x + cos(aa) * 0.30, y + 0.28, z + sin(aa) * 0.30), Vector3(0.07, 0.06, 0.07)), kcol())

# ============================================================ road furniture
## RULE. Kerbs at 0.9 m along both sides of the haul road, a drainage channel on
## the low side with grating covers every 2 m, and a bollard line where the road
## meets the collar apron.
func _road_furniture() -> void:
	var pts: Array = L.plan["road"]
	var w := float(L.plan["road_w"]) / 2000.0
	for i in range(pts.size() - 1):
		var a := Vector2(float(pts[i][0]) / 1000.0, float(pts[i][1]) / 1000.0)
		var b := Vector2(float(pts[i + 1][0]) / 1000.0, float(pts[i + 1][1]) / 1000.0)
		var dir := (b - a).normalized()
		var nrm := Vector2(-dir.y, dir.x)
		var n := int(a.distance_to(b) / 0.9)
		for k in n:
			var t := (float(k) + 0.5) / float(n)
			for side in [-1.0, 1.0]:
				var p: Vector2 = a.lerp(b, t) + nrm * side * w
				var y := gh(p.x, p.y)
				B.prop("box", "stone", Batcher.xf(Vector3(p.x, y + 0.10, p.y),
					Vector3(0.88, 0.26, 0.18), atan2(dir.y, dir.x) + r.randf_range(-0.03, 0.03)), kcol(0.65, 1.05))
			if k % 3 == 0:
				var pc: Vector2 = a.lerp(b, t) + nrm * (w + 0.45)
				B.detail("grate", "iron", Batcher.xf(Vector3(pc.x, gh(pc.x, pc.y) + 0.06, pc.y),
					Vector3(0.5, 1.0, 0.9), atan2(dir.y, dir.x)), ircol())
	# bollards at the apron
	for k in 9:
		var x := -32.0 + 1.6 * float(k)
		var z := 6.5
		B.prop("bollard", "galv", Batcher.xf(Vector3(x, gh(x, z) + 0.45, z), Vector3(0.20, 0.9, 0.20)), kcol(0.7, 1.05))
