extends RefCounted
class_name Town
##
## DRESSING LAYER - the town on the far wall.
##
## THE-ICE 7.2 is blunt about why this file matters more than the mountains do:
##
##   "A mountain does not make a machine read small. A CHAIN OF KNOWN SIZES
##    does ... What delivers absolute scale here is the sequence machine -> bay
##    -> building -> town on the wall -> ridge -> peak, and the load-bearing
##    link in that chain is THE TOWN, because it is the only element whose size
##    a viewer already knows. So the mountains are the thing you see and the
##    town is the thing that does the work, and if only one of them can be built
##    properly it is the town."
##
## And THE-ICE 7.3 says what it has to say without saying it:
##
##   "The society survived the ice on the walls, above the trimline, and it has
##    been walking downhill ever since ... So the town's own stratigraphy runs
##    downward and gets newer - which is the mine's index running downward and
##    getting newer, a thousand years apart, in one frame."
##
## LAYOUT decided the terraces and the gradient (see `SurfaceLayout._town`).
## This file decides what stands on them, and it has exactly one job: make five
## things vary monotonically down the wall, so that a viewer at 900 m who never
## thinks about any of it still reads *the old part is at the top*.
##
##   1. GRAIN.       Many small units above, few large ones below. At a
##                   kilometre this is a spatial FREQUENCY and it is the
##                   strongest of the five, because frequency survives blur and
##                   detail does not.
##   2. VALUE.       Quarried stone above, factory panel below.
##   3. ROOF LINE.   Broken and steeply pitched above; one long flat line below.
##   4. REGULARITY.  Accreted above, set out below.
##   5. LIGHT.       The lower town has glazing and the upper town has windows.
##
## ONE RULE THIS FILE OBEYS AND IT IS EASY TO GET WRONG.
## DESIGN-PRINCIPLES 7 is "density is order, not scatter", and a thousand-year
## hill quarter is undeniably irregular. Those are not in conflict, and the
## distinction is the whole of it: the upper town is IRREGULAR BY ACCRETION, not
## by scatter. Buildings share walls, sit flush against the neighbour that was
## already there, and step along the shelf. Nothing is rotated at random and
## nothing stands on its own in the middle of anything. What varies is height,
## width, depth and setback - the things a builder chooses - and never angle or
## position, which are the things nobody chooses. Rotate them randomly and the
## upper town reads as a rockfall, which is the same failure as the scrapyard.

var L: SurfaceLayout
var B: Batcher
var n_terraces := 0
var n_buildings := 0
var n_windows := 0

## a small float RNG. Dressing side, so floats are allowed; seeded off the site
## seed so two clients draw the same town.
var _s: int = 1

func _init(p_L: SurfaceLayout, p_B: Batcher) -> void:
	L = p_L
	B = p_B
	_s = (p_L.seed_v * 2654435761 + 991) & 0x7FFFFFFF

func _r() -> float:
	_s = (_s * 1103515245 + 12345) & 0x7FFFFFFF
	return float(_s % 100000) / 100000.0

func _rr(a: float, b: float) -> float:
	return a + (b - a) * _r()

func build() -> void:
	var T: Dictionary = L.plan["town"]
	var terr: Array = T["terraces"]
	n_terraces = terr.size()
	for i in terr.size():
		_terrace(terr[i])
	_incline(T)
	_switchbacks(T)
	_tower(T)

# ------------------------------------------------------------------ terrace
## THE Z A TERRACE ACTUALLY SITS AT, and this function is the difference between
## a town and a mobile hanging in front of a mountain.
##
## LAYOUT works from the smooth wall profile, because layout has no floats and
## must not know what the dressing layer did to the landform. But `Valley.h()`
## perturbs the fall line by up to fifty per cent before it applies that profile
## - that is what turns an extruded ramp into spurs and gullies - so the real
## surface at a given height can be a hundred and fifty metres in front of or
## behind where the profile says it is. Built against the profile, every terrace
## floated over the gullies and buried itself in the spurs, and the whole town
## read as a stack of shelves hanging in the air. It was the single most obvious
## wrong thing in the frame.
##
## So the terrace asks the LANDFORM where its own height is, per segment, and
## follows it. Which is what a terrace is: a contour line somebody built on. The
## town now wraps the spurs and steps back into the re-entrants, and it does that
## because the mountain is that shape, not because anybody drew it.
static func _contour_z(x: float, y: float, lo: float, hi: float) -> float:
	for i in 16:
		var m := (lo + hi) * 0.5
		if Valley.h(x, m) < y:
			lo = m
		else:
			hi = m
	return (lo + hi) * 0.5

func _terrace(t: Dictionary) -> void:
	var y := float(t["y"]) * 0.001
	var x0 := float(t["x0"]) * 0.001
	var x1 := float(t["x1"]) * 0.001
	var depth := float(t["z1"] - t["z0"]) * 0.001
	var f := float(t["f"]) * 0.001         # 0 oldest / highest, 1 newest / lowest
	var toe: float = float(Valley._V["far_toe"])
	var stone := "oldstone" if f < 0.42 else "newpanel"

	var bw := float(t["bw"]) * 0.001
	var bd := float(t["bd"]) * 0.001
	var bh := float(t["bh"]) * 0.001
	var gap := float(t["gap"]) * 0.001
	var pit := float(t["pitch"]) * 0.001
	# INTEGER TRAP, and it cost a frame: every scalar layout.gd hands over is an
	# integer in thousandths, including the ones that are not millimetres. `glass`
	# is 0..1000, not 0..1, and taken raw it made one window nineteen hundred
	# metres wide - an emissive slab across the whole valley. Scale everything
	# that crosses the seam, and scale it here rather than there, because the
	# integer side is not allowed to know what a float is.
	var glass := float(t["glass"]) * 0.001
	var jit := float(t["jitter"]) * 0.001
	bd = minf(bd, depth - 3.0)

	var seg := 15.0 + f * 13.0
	var x := x0
	var prev_h := bh
	var lamp_due := 0.0
	while x < x1 - 2.0:
		var w := minf(seg, x1 - x)
		var cx := x + w * 0.5
		var z := _contour_z(cx, y, toe - 40.0, toe + 2400.0)
		var zf := z - depth * 0.5
		var zb := z + depth * 0.5
		# the retaining wall reaches from the shelf down to wherever the hill
		# actually is at its front edge, which on a fifty degree face is 10-30 m
		var gnd := Valley.h(cx, zf - 1.0)
		var face := clampf(y - gnd, 3.0, 46.0)

		# --- the shelf. THE ONE THING THAT HAS TO READ AT A KILOMETRE is the
		# horizontal: a bright edge with a dark face under it, twenty times up a
		# mountain. Everything else on this terrace is detail inside that line.
		B.add("box", stone, Batcher.xf(Vector3(cx, y - face * 0.5, zf + 0.9),
			Vector3(w * 1.02, face, 1.8)), Color(1, 1, 1) * _rr(0.86, 1.10), Batcher.FAR)
		B.add("box", "rock", Batcher.xf(Vector3(cx, y - 0.40, z),
			Vector3(w * 1.02, 0.8, depth)), Color(1, 1, 1) * _rr(0.90, 1.06), Batcher.FAR)
		# the parapet along the drop: 1.1 m of wall, and the single brightest
		# line on the hillside, because it is the one horizontal surface up there
		# that faces the sky and nothing stands on it
		B.add("box", stone, Batcher.xf(Vector3(cx, y + 0.55, zf + 0.25),
			Vector3(w * 1.02, 1.1, 0.5)), Color(1, 1, 1) * _rr(1.02, 1.20), Batcher.FAR)
		# buttresses: the vertical rhythm that stops the face reading as a poured
		# slab, and denser going up because an older wall needed more of them
		var bstep := 5.0 + f * 11.0
		var bx := x + bstep * 0.5
		while bx < x + w:
			B.add("box", stone, Batcher.xf(Vector3(bx, y - face * 0.5, zf - 0.15),
				Vector3(1.1 + f * 0.7, face * _rr(0.72, 0.96), 1.3)),
				Color(1, 1, 1) * _rr(0.78, 1.00), Batcher.FAR)
			bx += bstep

		# --- WHICH SIDE OF THE SHELF THE HOUSES STAND ON, and it is not a
		# detail. A hill town fronts the drop: every house is built out to the
		# edge of its own terrace, because that is where the light and the view
		# are and because the back of the shelf is a cut face. Built at the BACK,
		# as the first take was, the whole town hides behind its own parapets and
		# from the valley floor you see a stack of retaining walls and no
		# buildings at all. The front row IS the town.
		var rows: Array = [zf + 1.1 + bd * 0.5]
		if depth > bd * 2.3 + 5.0:
			rows.append(zb - bd * 0.5 - 0.8)
		# --- AVALANCHE SPURS. The best detail available on this hillside, and it
		# costs four boxes a terrace. A settlement under a 1,500 m face lives or
		# dies by what it does about slides, and what mountain villages actually
		# do is build a WEDGE of stone into the uphill wall of the building - a
		# prow, pointed up the slope - so a moving slab is split and goes round
		# rather than through. Above the settlement they build wall-dams across
		# the fall line for the same reason. Nothing else in this file says as
		# plainly that people have lived here a long time and that the mountain
		# tries to kill them.
		var spx := x + 4.0
		while spx < x + w:
			# the splitting prow, behind the back row, pointed uphill
			B.add("cyl6", stone, Batcher.xf(Vector3(spx, y + 1.6, zb + 1.4),
				Vector3(3.4, 3.2, 5.6), 0.0), Color(1, 1, 1) * _rr(0.74, 0.98),
				Batcher.FAR)
			spx += 22.0 + f * 26.0
		# and one wall-dam above the terrace, staggered off the one below it
		if int(f * 100.0) % 3 == 0:
			B.add("box", stone, Batcher.xf(Vector3(cx, y + 3.4, zb + 7.0),
				Vector3(w * 0.7, 5.0, 2.2)), Color(1, 1, 1) * 0.86, Batcher.FAR)

		for ri in rows.size():
			var rz: float = rows[ri]
			var bxx := x + 0.6
			# CLUSTERING. Buildings pack tightly where the terrace is good and
			# are absent where it is not, so the settlement has crowds and gaps
			# rather than an even comb of blocks. One low-frequency field along
			# the run decides it, which is the same instrument the yard uses to
			# decide where an arrangement stands: density is a consequence of the
			# ground, never of a coin toss per object.
			while bxx < x + w - 1.4:
				var good := 0.5 + 0.5 * sin(bxx * 0.045 + f * 9.0 + float(ri) * 2.3)
				if good < 0.30:
					bxx += 4.0
					continue
				var bwd: float = bw * _rr(0.74, 1.34)
				if bxx + bwd > x + w - 0.5:
					bwd = x + w - 0.5 - bxx
				if bwd < 2.2:
					break
				# ACCRETION, not scatter. `jit` is 1 at the top and 0 at the
				# foot, and every term it multiplies is a builder's decision -
				# how tall, how deep, how far back from the line - never an angle
				# and never a position. The next house starts where this one ends.
				var hh: float = bh * _rr(1.0 - 0.34 * jit, 1.0 + 0.44 * jit)
				hh = lerpf(hh, prev_h * _rr(0.88, 1.16), jit * 0.55)
				var dd: float = bd * _rr(1.0 - 0.20 * jit, 1.0 + 0.12 * jit)
				var back: float = _rr(0.0, 1.1) * jit
				var zc: float = rz + (back if ri == 0 else -back)
				var mat := "oldstone" if f < _rr(0.30, 0.56) else "newpanel"
				var tint := _rr(0.62, 1.34)
				# STONE BELOW, LIGHTER ABOVE, which is the near-universal form of
				# a mountain house and is a structural fact before it is a look:
				# the plinth is heavy coursed stone standing on the most
				# consistent ground it can find, half a metre thick or more, and
				# what goes on top of it is light because somebody had to carry
				# it up there. The two-part elevation is the thing that reads at
				# a kilometre - a dark base and a paler body, on every building
				# on the hill, all at slightly different heights.
				var pl := hh * _rr(0.32, 0.52)
				B.add("box", "oldstone", Batcher.xf(
					Vector3(bxx + bwd * 0.5, y + pl * 0.5, zc),
					Vector3(bwd * 1.03, pl, dd * 1.03)),
					Color(1, 1, 1) * tint * 0.78, Batcher.FAR)
				# VALUE SPREAD, and it is worth more than any amount of detail at
				# this range. Nine hundred buildings inside an 18% value band read
				# as one extruded mass; inside a 2:1 band they read as nine
				# hundred buildings, because a viewer counts EDGES and an edge is
				# a value step. Same material, same rule, one wider multiply.
				B.add("box", mat, Batcher.xf(
					Vector3(bxx + bwd * 0.5, y + pl + (hh - pl) * 0.5, zc),
					Vector3(bwd, hh - pl, dd)), Color(1, 1, 1) * tint, Batcher.FAR)
				n_buildings += 1
				_roof(bxx + bwd * 0.5, y + hh, zc, bwd, dd, pit, f)
				_windows(bxx + bwd * 0.5, y, zc - dd * 0.5, bwd, hh, glass, f)
				bxx += bwd + gap * _rr(0.0, 1.0) * (1.0 if ri == 1 else jit)
				prev_h = hh

		# --- the street lamps. Denser downhill, because the lower town has power
		# and the upper town has been making do for a thousand years.
		lamp_due -= w
		if lamp_due <= 0.0:
			B.add("cyl6", "galv", Batcher.xf(Vector3(cx, y + 2.4, zf + 2.2),
				Vector3(0.16, 4.8, 0.16)), Color(1, 1, 1), Batcher.FAR)
			B.add("casebox", "warmlit", Batcher.xf(Vector3(cx, y + 4.7, zf + 2.2),
				Vector3(0.7, 0.26, 0.5)), Color(1, 1, 1), Batcher.FAR, true)
			lamp_due = 30.0 - f * 14.0
		x += w

# ---------------------------------------------------------------------- roof
## Roof line is gradient item 3. Above: steep, broken, one ridge per house, so
## the skyline is a saw. Below: shallow to flat, and neighbouring roofs line up,
## so the skyline is a rule. Nothing in between needs saying.
func _roof(cx: float, top: float, cz: float, w: float, d: float, pitch: float, f: float) -> void:
	if pitch > 1.2:
		var rise := d * 0.5 * (pitch / 2.6)
		var sl := sqrt((d * 0.5) * (d * 0.5) + rise * rise)
		var ang := atan2(rise, d * 0.5)
		for s in [-1.0, 1.0]:
			B.add("box", "roofdark",
				Batcher.xf(Vector3(cx, top + rise * 0.5, cz + s * d * 0.25),
					Vector3(w * 1.06, 0.16, sl * 1.02), 0.0, -s * ang, 0.0),
				Color(1, 1, 1) * _rr(0.80, 1.15), Batcher.FAR)
		# a chimney. Two pixels at nine hundred metres and worth every one of
		# them, because a chimney says somebody is keeping warm in there.
		if w > 3.0:
			B.add("box", "oldstone", Batcher.xf(
				Vector3(cx + w * _rr(-0.26, 0.26), top + rise + 0.7, cz),
				Vector3(0.55, 1.5, 0.55)), Color(1, 1, 1) * 0.9, Batcher.FAR)
	else:
		B.add("box", "roofdark", Batcher.xf(Vector3(cx, top + 0.10, cz),
			Vector3(w * 1.02, 0.20, d * 1.02)), Color(1, 1, 1) * _rr(0.88, 1.06),
			Batcher.FAR)
		# a flat roof has plant on it, and a row of identical units on a row of
		# identical roofs is DESIGN-PRINCIPLES 7's "repetition reads as
		# manufactured" applied at a kilometre
		if f > 0.55 and w > 7.0:
			for k in 2:
				B.add("casebox", "kitgrey", Batcher.xf(
					Vector3(cx + (float(k) - 0.5) * w * 0.32, top + 0.85, cz),
					Vector3(1.5, 1.3, 1.5)), Color(1, 1, 1), Batcher.FAR)

# ------------------------------------------------------------------ windows
## Gradient item 5. The upper town has windows punched in a thick wall - small,
## few, deep. The lower town has glazing - a band, nearly continuous. At nine
## hundred metres neither is a shape; both are a LINE OF LIGHT, and the
## difference between a dotted line and a solid one is completely legible.
##
## ART-DIRECTION 8.4 must-not 1 and THE-ICE 2.6: nothing in this world may EMIT
## belief's colour. These are warm and they are the only warm thing the player
## can ever get near.
func _windows(cx: float, base: float, zf: float, w: float, hh: float,
		glass: float, f: float) -> void:
	var floors := maxi(1, int(hh / 3.3))
	var ww := 0.8 + glass * 1.7
	# THE COUNT IS THE WHOLE PROBLEM. The first take drew up to eight windows
	# across five storeys on every building and lit a third to two thirds of
	# them, and the town came back as a spreadsheet: forty orange cells per
	# block, in a grid, on nine hundred buildings. What a hill town at a
	# kilometre actually looks like is a SPARSE SCATTER OF WARM POINTS with big
	# dark gaps between them, and the gaps are what make the lit ones read as
	# lights rather than as a texture. Two to four openings a face, and most of
	# them are dark, because most rooms are empty most of the time.
	var per := clampi(int(w / (ww + 3.4 - glass * 1.2)), 1, 4)
	for fl in floors:
		var fy := base + 1.65 + float(fl) * 3.3
		if fy > base + hh - 0.9:
			break
		for k in per:
			# lit, and NOT MANY. The upper town has fewer, because it has fewer
			# people and less power; the lower town has more, because it is where
			# everybody moved to. That gradient is the fifth of the five and it
			# is the only one that works at night.
			var on := _r() < (0.11 + f * 0.19)
			var wx := cx - w * 0.5 + (float(k) + 0.5) * (w / float(per))
			# an unlit window at a kilometre is not a light grey rectangle, it is
			# a dark one: a hole in a wall with nothing behind it. Drawing it
			# pale is what turned the dark two thirds into part of the grid.
			var m := "warmlit" if on else "roofdark"
			B.add("box", m, Batcher.xf(Vector3(wx, fy, zf - 0.10),
				Vector3(ww, 1.15 + glass * 0.75, 0.16)),
				Color(1, 1, 1) * (_rr(0.5, 1.35) if on else _rr(0.7, 1.0)),
				Batcher.FAR, on)
			n_windows += 1

# -------------------------------------------------------------- switchbacks
## Anything above about an eight per cent grade needs zigzags, and a hillside at
## fifty degrees is six hundred per cent. So every road in a mountain village
## SWITCHBACKS, and the zigzag is one of the most recognisable things about
## these places: from across a valley it is the only continuous line on the
## whole slope and it ties eighteen disconnected terraces into one settlement.
##
## It is drawn from the terrace list rather than invented, so it lands on the
## shelves that exist: a straight run along each terrace, then a hairpin up to
## the next, alternating direction. Twenty terraces, forty segments, and it is
## the cheapest legibility in this file.
func _switchbacks(T: Dictionary) -> void:
	var terr: Array = T["terraces"]
	var toe: float = float(Valley._V["far_toe"])
	var dir := 1.0
	for i in range(terr.size() - 1):
		var a: Dictionary = terr[i + 1]        # lower (newer)
		var b: Dictionary = terr[i]            # upper (older)
		var ya := float(a["y"]) * 0.001
		var yb := float(b["y"]) * 0.001
		var ax0 := float(a["x0"]) * 0.001
		var ax1 := float(a["x1"]) * 0.001
		var run := ax1 - ax0
		if run < 30.0:
			continue
		# the traverse along the lower shelf, then the hairpin climbing to the
		# upper one. `dir` flips every terrace, which is what makes it a zigzag.
		var n := 9
		for k in n:
			var t0 := float(k) / float(n)
			var t1 := float(k + 1) / float(n)
			var u0: float = ax0 + (t0 if dir > 0.0 else 1.0 - t0) * run
			var u1: float = ax0 + (t1 if dir > 0.0 else 1.0 - t1) * run
			var yy0 := lerpf(ya, yb, t0)
			var yy1 := lerpf(ya, yb, t1)
			var z0 := _contour_z(u0, yy0, toe - 40.0, toe + 2400.0)
			var z1 := _contour_z(u1, yy1, toe - 40.0, toe + 2400.0)
			var p0 := Vector3(u0, yy0 + 0.35, z0 - 1.2)
			var p1 := Vector3(u1, yy1 + 0.35, z1 - 1.2)
			B.beam("box", "newpanel", p0, p1, 4.2, 0.35,
				Color(1, 1, 1) * 1.14, Batcher.FAR)
			# the outer edge of a mountain road is a wall, always
			B.beam("box", "oldstone", p0 + Vector3(0, -0.9, -2.1),
				p1 + Vector3(0, -0.9, -2.1), 0.7, 2.2,
				Color(1, 1, 1) * 0.82, Batcher.FAR)
		dir = -dir

# ----------------------------------------------------------------- incline
## THE-ICE 7.8, leg 1 of three: "an inclined railway down the terraces. A
## society on a wall needs one, and it is the players' technological register
## made obvious." It is also the only straight line on the whole hillside, which
## is why it reads from the valley floor: everything else up there is horizontal.
func _incline(T: Dictionary) -> void:
	var pts: Array = T["incline"]
	var a := Vector3(float(pts[0][0]) * 0.001, float(pts[0][2]) * 0.001, float(pts[0][1]) * 0.001)
	var b := Vector3(float(pts[2][0]) * 0.001, float(pts[2][2]) * 0.001, float(pts[2][1]) * 0.001)
	var n := 26
	for i in n:
		var t0 := float(i) / float(n)
		var t1 := float(i + 1) / float(n)
		var p0 := a.lerp(b, t0)
		var p1 := a.lerp(b, t1)
		p0.y = maxf(p0.y, Valley.h(p0.x, p0.z))
		p1.y = maxf(p1.y, Valley.h(p1.x, p1.z))
		# the deck, held off the slope on trestles
		var d0 := p0 + Vector3(0, 2.6, 0)
		var d1 := p1 + Vector3(0, 2.6, 0)
		for s in [-1.0, 1.0]:
			B.beam("box", "galv", d0 + Vector3(s * 2.0, 0, 0), d1 + Vector3(s * 2.0, 0, 0),
				0.22, 0.22, Color(1, 1, 1), Batcher.FAR)
		B.beam("box", "kitgrey", d0, d1, 4.6, 0.28, Color(1, 1, 1), Batcher.FAR)
		B.beam("ibeam", "galv", p0, d0, 0.5, 0.5, Color(1, 1, 1), Batcher.FAR)
	# the car, parked at the foot, and a second one halfway up. Two objects, and
	# they are the whole of "there are people here" at this distance.
	for t in [0.06, 0.62]:
		var p := a.lerp(b, t)
		p.y = maxf(p.y, Valley.h(p.x, p.z)) + 3.5
		B.add("casebox", "bone", Batcher.xf(p, Vector3(3.6, 3.0, 7.4)),
			Color(1, 1, 1), Batcher.FAR)
		B.add("box", "warmlit", Batcher.xf(p + Vector3(0, 0.3, -3.75),
			Vector3(2.8, 1.4, 0.12)), Color(1, 1, 1), Batcher.FAR, true)

# ------------------------------------------------------------------- tower
## A skyline needs one vertical or it is a stack of lines. THE-ICE says nothing
## about this object; it is a guess and it is listed as one in VALLEY.md. What
## it is for is legibility: it marks the oldest quarter from the valley floor,
## and being the highest built thing in the frame it is the first thing the
## alpenglow reaches and the last thing it leaves.
func _tower(T: Dictionary) -> void:
	var tw: Dictionary = T["tower"]
	var x := float(tw["x"]) * 0.001
	var y := float(tw["y"]) * 0.001
	var hh := float(tw["h"]) * 0.001
	var z: float = float(Valley._V["far_toe"]) + float(L.wall_d(int(tw["y"]))) * 0.001
	var lifts := 9
	for i in lifts:
		var t := float(i) / float(lifts)
		var s := 5.4 * (1.0 - t * 0.30)
		B.add("box", "oldstone", Batcher.xf(Vector3(x, y + hh * (t + 0.5 / float(lifts)), z),
			Vector3(s, hh / float(lifts) * 1.02, s)),
			Color(1, 1, 1) * _rr(0.84, 1.10), Batcher.FAR)
	B.add("box", "roofdark", Batcher.xf(Vector3(x, y + hh + 1.2, z),
		Vector3(6.4, 2.4, 6.4)), Color(1, 1, 1), Batcher.FAR)
