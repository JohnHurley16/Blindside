extends RefCounted
class_name Valley
##
## DRESSING LAYER - the landform.
##
## The pit-head used to stand in a 174 x 148 m box with a flat geometric skirt
## for a horizon. THE-ICE 2.2 calls that "a yard, not a valley" and it is right.
## This file builds the valley the yard now stands on the floor of: a floor, two
## walls, a head wall, a glacier and a horizon of peaks, from the integer numbers
## in LAYOUT and nothing else.
##
## THE COST ARGUMENT, which is THE-ICE 7.5 and is why this file is short:
##
##   "The mountains themselves are the cheapest large thing you can add to this
##    game ... At that range they are silhouette, aerial perspective and a snow
##    line, and nothing else: no material detail, no props, no shadow casting,
##    no collision, and LOD that never has to be good. ... Budget the town, not
##    the mountains."
##
## So this is ONE indexed ArrayMesh in ONE draw call, with cast_shadow OFF (the
## nearest thing in it is a wall toe at 300 m and the sun's shadow range is 95),
## no props, and an axis grading that spends its vertices where the eye is:
## thick through the floor and the wall toes, thin everywhere past two
## kilometres. It is ~55 000 vertices for sixteen kilometres of landscape, which
## is fewer than the pit-head's 65 000 for one hundred and seventy metres.
##
## THE SEAM WITH THE PIT-HEAD. `ground.gd` still owns everything inside its own
## site box plus its skirt to ~420 m, and it draws ON TOP: the valley mesh runs
## underneath the whole site at SINK metres below the floor datum. At 420 m a
## 0.25 m step is a third of a pixel, and the alternative - making two graded
## grids share a boundary ring exactly - is a class of bug that eats a day.

## how far below the floor datum the valley mesh sits under the pit-head, metres
const SINK := 0.25

## the outer bound of the drawn world, metres. The camera's far plane is set
## from this in main.gd.
const REACH := 16000.0

static var _V: Dictionary = {}
static var _wall: Array = []
static var _peaks: Array = []

# --------------------------------------------------------------- the surface
## Height above the valley floor datum, in METRES, at a world (x, z).
##
## This is the dressing-side twin of `SurfaceLayout.ground_mm` and it obeys the
## same contract: it is the only place the landform is decided, and everything
## else - the town's foundations, the moraines, the river, the shot list - asks
## it rather than re-deriving it.
static func h(x: float, z: float) -> float:
	# --- 1. the two walls. `d` is the horizontal run beyond a toe.
	#     The fall line is perturbed BEFORE the profile is applied, not after,
	#     which is what turns an extruded ramp into spurs and re-entrants: a
	#     wall whose profile is constant along its length reads as a road cutting
	#     and no amount of noise laid on top of it fixes that.
	var far_toe: float = _V["far_toe"]
	var near_toe: float = _V["near_toe"]
	# `dt` is the SIGNED distance from the nearer toe: positive up the wall,
	# negative out on the valley floor. It is signed because the talus apron
	# lives on both sides of the toe and a hard line there was one of the things
	# that made this read as a backdrop rather than as a place.
	var dt := 0.0
	var side := 0.0
	if z > far_toe:
		dt = z - far_toe
		side = 1.0
	elif z < near_toe:
		dt = near_toe - z
		side = -1.0
	else:
		var df := far_toe - z
		var dn := z - near_toe
		if df < dn:
			dt = -df
			side = 1.0
		else:
			dt = -dn
			side = -1.0
	var d := maxf(dt, 0.0)
	var hw := 0.0
	# ------------------------------------------------------------------------
	# BUTTRESSES AND GULLIES, AND THEY ARE RIDGED, NOT SMOOTH.
	#
	# The first take used three bands of ordinary value noise on the fall line
	# and the result was a duvet: a wall with dents in it. A mountain is not a
	# noisy plane. It is a set of BUTTRESSES separated by GULLIES, and the thing
	# that distinguishes those from bumps and dips is that the boundary between
	# them is a CREASE - a line, not a curve. Ordinary noise has no creases in
	# it at any amplitude.
	#
	# Ridged noise does: 1 - |2n - 1| folds the field at its midpoint, so it has
	# a sharp maximum along a locus rather than a rounded one. Three bands of it
	# give a spur system at 240 m, a gully system at 80 m and ribs at 28 m, and
	# the creases at each scale are what the eye reads as the structure of a
	# mountainside. This one change is most of the difference between a mound
	# and a mountain.
	var g1 := _rid(x * 0.0042 + side * 19.0, side * 3.0)
	var g2 := _rid(x * 0.0125 + side * 71.0, side * 7.0)
	var g3 := _rid(x * 0.0365 + side * 31.0, side * 11.0)
	var cut := (g1 - 0.5) * 0.62 + (g2 - 0.5) * 0.36 + (g3 - 0.5) * 0.15
	if d > 0.0:
		var de: float = d * (1.0 + cut * 0.86)
		hw = _profile(maxf(de, 0.0))
		hw *= 1.0 + cut * 0.24
		# ARETES. Where the profile eases toward the ridge the wall wants to go
		# round, and a rounded ridge is the single strongest "this is a hill"
		# signal there is. So the crest is sharpened by the same ridged field,
		# weighted in only over the top third: a ridge is where two faces MEET.
		var crest := clampf((hw - 1150.0) / 520.0, 0.0, 1.0)
		hw += (g1 - 0.35) * 190.0 * crest * crest
		# and the rock itself is broken above the trimline and scoured below it.
		# This is the ONE place the trimline is geometry rather than material,
		# and it is worth it: the break in TEXTURE at 310 m is what makes the
		# line read from the valley floor at a kilometre.
		var rough := 30.0 * (Ground._vn(x * 0.010 + 4.0, z * 0.010 + 9.0) - 0.5) \
			+ 11.0 * (Ground._vn(x * 0.031 + 2.0, z * 0.031 + 5.0) - 0.5) \
			+ 4.0 * (Ground._vn(x * 0.090 + 6.0, z * 0.090 + 1.0) - 0.5)
		hw += rough * clampf((hw - 240.0) / 240.0, 0.06, 1.0)
		# HANGING VALLEYS. A tributary glacier cuts its own trough and the main
		# glacier cuts deeper and faster, so the side valley is left stranded
		# high on the wall with its floor cut clean off. It is the most
		# recognisable thing a glaciated wall has after the trimline, and it is
		# one subtraction: a bowl notched into the face at a chosen height.
		for k in 3:
			var hx0: float = -3400.0 + float(k) * 2500.0 + side * 900.0
			var hy0: float = 640.0 + float(k) * 120.0
			var dxh := (x - hx0) / 340.0
			var dyh := (hw - hy0) / 300.0
			var rr2 := dxh * dxh + dyh * dyh
			if rr2 < 1.0:
				var tt := 1.0 - rr2
				hw -= 190.0 * tt * tt
	# ------------------------------------------------------------------------
	# TALUS AND SCREE. Every rock face sheds, and what it sheds piles at the
	# angle of repose - 31 to 36 degrees - in a smooth apron at the foot of the
	# face, spilling out over the valley floor. Where a gully discharges, the
	# apron becomes a CONE, which is why a real wall has a scalloped skirt of
	# fans along its whole length rather than a hem.
	#
	# It is also the reason the wall above it can be as steep as it now is: the
	# bedrock profile starts at 63 degrees, which is what an over-steepened
	# glacial trough actually does, and no snow whatever holds on that. The
	# talus is where snow lies deep, so the sequence from the floor is
	#   flat - deep snow apron - bare rock wall - gullies - upper slopes - ridge
	# and that sequence IS the picture.
	var fan := 0.70 + 0.95 * g2 + 0.35 * g1
	var tal_run: float = (52.0 + 78.0 * Ground._vn(x * 0.0035 + side * 51.0, side * 5.0)) * fan
	var talus: float = (tal_run + dt) * 0.62
	if talus > 0.0:
		hw = maxf(hw, minf(talus, _profile(maxf(d, 0.0)) + 26.0))

	# --- 2. the head wall up-valley and the ridge that closes the view down it.
	var hx := 0.0
	var hxd: float = _V["head_x"]
	var mxd: float = _V["mouth_x"]
	if x > hxd:
		hx = _profile((x - hxd) * (1.0 + (Ground._vn(z * 0.0050 + 33.0, 1.0) - 0.5) * 0.40))
	elif x < mxd:
		hx = _profile((mxd - x) * (1.0 + (Ground._vn(z * 0.0050 + 51.0, 2.0) - 0.5) * 0.40))
	var y := maxf(hw, hx)

	# --- 3. the peaks. THE-ICE 7.2 puts them at 2600-3200 m and 4-15 km, and
	#     7.5 says they are nearly free. They are: a cone with a ridged
	#     perturbation on its radius, combined with max() rather than added, so
	#     a range of them produces a skyline with cols in it instead of a row of
	#     slag heaps. Nothing else is spent on them.
	for i in _peaks.size():
		var pk: Array = _peaks[i]
		var dx: float = x - pk[0]
		var dz: float = z - pk[1]
		var dr := sqrt(dx * dx + dz * dz)
		var r: float = pk[2]
		if dr < r:
			var ang := atan2(dz, dx)
			# ridges radiating from the summit: this is what a mountain is
			var rid := 1.0 + 0.30 * (Ground._vn(ang * 2.4 + float(i) * 13.0, dr * 0.00042) - 0.5) \
				+ 0.13 * (Ground._vn(ang * 7.1 + float(i) * 5.0, dr * 0.0011) - 0.5)
			var t := clampf(1.0 - dr / (r * rid), 0.0, 1.0)
			y = maxf(y, float(pk[3]) * pow(t, 1.45))

	# --- 4. the floor. Everything below is under a metre except the moraines.
	if y < 3.0:
		y = maxf(y, _floor(x, z))
	else:
		y = maxf(y, _floor(x, z))
	return y

## The valley floor: glacial outwash, two lateral moraines, a braided meltwater
## river and, up-valley, the glacier that made all of it.
static func _floor(x: float, z: float) -> float:
	var near_toe: float = _V["near_toe"]
	var far_toe: float = _V["far_toe"]
	var y := 1.9 * (Ground._vn(x * 0.0125 + 3.0, z * 0.0125 + 8.0) - 0.5) \
		+ 0.75 * (Ground._vn(x * 0.048 + 21.0, z * 0.048 + 4.0) - 0.5)

	# --- LATERAL MORAINES. The other unmistakable thing a glacier leaves, and
	#     the cheapest: two long ridges of dumped rubble lying parallel to the
	#     walls a little way out from the toe, with a trough behind each. A
	#     player who has never heard the word reads "something enormous was
	#     parked here".
	var mo: float = _V["moraine_off"]
	var mh: float = _V["moraine_h"]
	for s in [-1.0, 1.0]:
		var toe: float = near_toe if s < 0.0 else far_toe
		# the crest lies `moraine_off` INSIDE the toe, out on the floor, which is
		# where a lateral moraine actually sits: it is the rubble the ice carried
		# on its flank, let down when the flank melted away from the wall.
		var mz: float = toe - s * mo
		var dz := absf(z - mz)
		var wdt := 78.0 * (1.0 + 0.34 * (Ground._vn(x * 0.0032 + s * 11.0, 0.0) - 0.5))
		if dz < wdt:
			var t := 1.0 - dz / wdt
			var crest: float = mh * (0.62 + 0.76 * Ground._vn(x * 0.0060 + s * 27.0, 1.0))
			y += crest * t * t * (3.0 - 2.0 * t) * 0.5
			# and it is rubble, not a dune
			y += 2.4 * (Ground._vn(x * 0.075 + s * 3.0, z * 0.075) - 0.5) * t

	# --- THE RIVER. The only dark, moving, warm-adjacent thing in a white
	#     valley, and TRAILER shot 4's meltwater. It runs hard against the near
	#     wall because outwash pushes it there, and it braids.
	var rz: float = _V["river_z"] + 120.0 * (Ground._vn(x * 0.00085 + 7.0, 0.0) - 0.5)
	var rw: float = _V["river_w"] * (0.55 + 0.90 * Ground._vn(x * 0.0022 + 15.0, 0.0))
	var rd := absf(z - rz)
	if rd < rw * 1.9:
		var t2 := clampf(1.0 - rd / (rw * 1.9), 0.0, 1.0)
		y -= (2.6 + 1.4 * Ground._vn(x * 0.004 + 44.0, 0.0)) * t2 * t2
		# gravel bars in the channel
		y += 0.9 * (Ground._vn(x * 0.055 + 61.0, z * 0.16) - 0.5) * t2

	# --- ROCHES MOUTONNEES. Bedrock humps the ice rode over: smoothed and
	#     gently ramped on the up-glacier side, plucked and steep on the down
	#     side. The asymmetry is the whole point - it is a DIRECTION ARROW left
	#     in the rock, and every one of them on the floor points the same way,
	#     which is the way the ice went. Two lines and it costs nothing.
	for k in 6:
		var rx: float = -2600.0 + float(k) * 1150.0
		var rzc: float = 120.0 + 380.0 * Ground._vn(float(k) * 7.3, 2.0)
		var rr: float = 55.0 + 70.0 * Ground._vn(float(k) * 3.1, 5.0)
		var ddx := (x - rx) / rr
		var ddz := (z - rzc) / (rr * 0.62)
		var q2 := ddx * ddx + ddz * ddz
		if q2 < 1.0:
			var t3 := 1.0 - q2
			# steep on the DOWN-glacier side (-x), ramped on the up-glacier side
			var asym: float = 1.0 if ddx > 0.0 else clampf(1.0 + ddx * 0.55, 0.30, 1.0)
			y = maxf(y, (7.0 + 9.0 * Ground._vn(float(k) * 11.0, 1.0)) * pow(t3, 0.75) * asym)

	# --- THE GLACIER, up-valley. THE-ICE 3 puts its terminus 3 km beyond the
	#     pit-head: far enough to be scenery, near enough to be the reason the
	#     pit-head exists. The snout is a wall; behind it the surface climbs.
	var tx: float = _V["terminus_x"]
	if x > tx - 260.0:
		var g := clampf((x - (tx - 260.0)) / 300.0, 0.0, 1.0)
		g = g * g * (3.0 - 2.0 * g)
		var ice := 34.0 * g + maxf(x - tx, 0.0) * 0.085
		# crevasse field: transverse on the steep, longitudinal at the margins
		ice += 5.5 * (Ground._vn(x * 0.020 + 5.0, z * 0.0024) - 0.5) * g
		# the snout is not a straight line
		ice *= 0.80 + 0.40 * Ground._vn(z * 0.0035 + 2.0, 0.0)
		y = maxf(y, ice)
	return y

## RIDGED noise: 1 - |2n - 1|. Folds the field about its midpoint so it has a
## sharp maximum along a LOCUS rather than a rounded one. Every crease in this
## landscape - every gully wall, every buttress edge, every arete - comes from
## this function, and ordinary noise cannot produce one at any amplitude.
static func _rid(a: float, b: float) -> float:
	return 1.0 - absf(Ground._vn(a, b) * 2.0 - 1.0)

## The buttress / gully field at a point, as `h()` computes it. Written into
## vertex colour A so the material can put snow in the gullies the GEOMETRY has
## rather than in gullies of its own invention. Two fields that disagree about
## where a gully is look far worse than one field with no gullies at all.
static func _cut_at(x: float, z: float) -> float:
	var far_toe: float = _V["far_toe"]
	var near_toe: float = _V["near_toe"]
	var side := 1.0 if (z - near_toe) > (far_toe - z) else -1.0
	if z > far_toe:
		side = 1.0
	elif z < near_toe:
		side = -1.0
	var g1 := _rid(x * 0.0042 + side * 19.0, side * 3.0)
	var g2 := _rid(x * 0.0125 + side * 71.0, side * 7.0)
	var g3 := _rid(x * 0.0365 + side * 31.0, side * 11.0)
	return (g1 - 0.5) * 0.62 + (g2 - 0.5) * 0.36 + (g3 - 0.5) * 0.15

## the wall profile, in metres, straight off the integer plan
static func _profile(d: float) -> float:
	var n := _wall.size()
	var last: Array = _wall[n - 1]
	if d <= 0.0:
		return 0.0
	if d >= float(last[0]) * 0.001:
		return float(last[1]) * 0.001
	for i in range(n - 1):
		var a: Array = _wall[i]
		var b: Array = _wall[i + 1]
		var ad := float(a[0]) * 0.001
		var bd := float(b[0]) * 0.001
		if d >= ad and d < bd:
			var t := (d - ad) / (bd - ad)
			# ease the joins so the profile is a curve rather than a polyline.
			# A visible kink at 310 m would read as a terrace and there is
			# already a town of those on this wall.
			t = t * t * (3.0 - 2.0 * t)
			return lerpf(float(a[1]) * 0.001, float(b[1]) * 0.001, t)
	return float(last[1]) * 0.001

# ------------------------------------------------------------------- build
static func build(L: SurfaceLayout, parent: Node3D) -> Dictionary:
	var t0 := Time.get_ticks_usec()
	_V = {}
	var vp: Dictionary = L.plan["valley"]
	for k in ["near_toe", "far_toe", "head_x", "mouth_x", "terminus_x",
			"moraine_h", "moraine_off", "river_z", "river_w"]:
		_V[k] = float(vp[k]) * 0.001
	_wall = vp["wall"]
	_peaks = []
	for p in L.plan["peaks"]:
		_peaks.append([float(p[0]) * 0.001, float(p[1]) * 0.001,
			float(p[2]) * 0.001, float(p[3]) * 0.001])

	# --- the axes. Vertices go where the eye is: 26 m through the floor and the
	#     wall toes, 55 m up the walls where the town is, and a geometric ramp
	#     past two kilometres where a vertex is worth less than a pixel.
	# RESOLUTION IS A PREREQUISITE FOR THE SLOPE RULE, and this is the part that
	# is easy to miss. Snow cover is driven by the MESH NORMAL, and a 52 m
	# quantisation across a wall that has 28 m ribs in it averages those ribs
	# away: every normal comes back near vertical, every slope reads as gentle,
	# and the whole range is therefore snow. The structure has to exist in the
	# geometry before the material rule can find it. These are the numbers that
	# let a 28 m rib survive to be sampled.
	var xs := _grade([[-REACH, -2600.0, 0.0], [-2600.0, -900.0, 30.0],
		[-900.0, 900.0, 20.0], [900.0, 3400.0, 30.0],
		[3400.0, 7200.0, 110.0], [7200.0, REACH, 0.0]])
	# THE BAND AT -260..-40 IS THE RIVER, and it is there because a 58 m braid
	# plain sampled at 24 m is two vertices wide: the mask lands on the mesh as
	# a row of dark blobs rather than as a channel, which is exactly what the
	# first take looked like. Eighteen extra rows buy a river.
	var zs := _grade([[-REACH, -3400.0, 0.0], [-3400.0, -700.0, 30.0],
		[-700.0, -260.0, 18.0], [-260.0, -40.0, 12.0], [-40.0, 1700.0, 16.0],
		[1700.0, 4000.0, 30.0],
		[4000.0, 8000.0, 130.0], [8000.0, REACH, 0.0]])
	var nx := xs.size()
	var nz := zs.size()

	var verts := PackedVector3Array()
	var norms := PackedVector3Array()
	var cols := PackedColorArray()
	verts.resize(nx * nz)
	norms.resize(nx * nz)
	cols.resize(nx * nz)

	var hc := PackedFloat32Array()
	hc.resize(nx * nz)
	for iz in nz:
		var zf: float = zs[iz]
		for ix in nx:
			hc[iz * nx + ix] = h(xs[ix], zf) - SINK

	var site: Dictionary = L.plan["site"]
	var sx0 := float(site["x0"]) * 0.001 - 340.0
	var sx1 := float(site["x1"]) * 0.001 + 340.0
	var sz0 := float(site["z0"]) * 0.001 - 340.0
	var sz1 := float(site["z1"]) * 0.001 + 340.0

	for iz in nz:
		for ix in nx:
			var i := iz * nx + ix
			var x: float = xs[ix]
			var z: float = zs[iz]
			var y: float = hc[i]
			verts[i] = Vector3(x, y, z)
			var hl: float = hc[i - (1 if ix > 0 else 0)]
			var hr: float = hc[i + (1 if ix < nx - 1 else 0)]
			var hb: float = hc[i - (nx if iz > 0 else 0)]
			var hf: float = hc[i + (nx if iz < nz - 1 else 0)]
			var dx: float = xs[mini(ix + 1, nx - 1)] - xs[maxi(ix - 1, 0)]
			var dz: float = zs[mini(iz + 1, nz - 1)] - zs[maxi(iz - 1, 0)]
			# THE MIDDLE TERM IS 1.0 AND IT MUST BE 1.0, and getting this wrong
			# cost most of a pass. `ground.gd` writes 2.0 here, which is the
			# constant from the standard heightfield-normal formula for a grid of
			# UNIT spacing where the differences are taken across TWO cells. The
			# differences here are already divided by the real spacing, so the
			# vector is (-dh/dx, 1, -dh/dz) and a 2 in that slot HALVES EVERY
			# GRADIENT: a 63 degree cliff reports as 45 and a 50 degree face
			# reports as 30.
			#
			# On the pit-head, where the whole natural relief is 1.2 m, that is
			# invisible. On an 1,800 m wall it is fatal, and it is fatal
			# specifically because the snow rule reads this number: every face
			# came back shallow enough to hold snow, so the entire range was
			# white and had no rock in it at any scale. The designer's note -
			# "a bunch of big white mounds dont cut it, where's the rock" - is
			# this one constant.
			norms[i] = Vector3(-(hr - hl) / maxf(dx, 0.01), 1.0,
				-(hf - hb) / maxf(dz, 0.01)).normalized()
			# vertex colour, read by the shader:
			#   R  glacier      - it is ice, not snow, and it reads differently
			#   G  river bed    - wet, dark, gravel, and the only moving thing
			#   B  floor-ness   - 1 on the floor, 0 on the wall
			#   A  slope proxy  - carried so the shader does not re-derive it far
			#                     away, where the mesh normal is all there is
			var glac := clampf((x - (float(vp["terminus_x"]) * 0.001 - 180.0)) / 220.0, 0.0, 1.0)
			glac *= clampf(1.0 - (y - 60.0) / 400.0, 0.0, 1.0)
			var rz: float = float(vp["river_z"]) * 0.001 + 120.0 * (Ground._vn(x * 0.00085 + 7.0, 0.0) - 0.5)
			var rw: float = float(vp["river_w"]) * 0.001 * (0.55 + 0.90 * Ground._vn(x * 0.0022 + 15.0, 0.0))
			var riv := clampf(1.0 - absf(z - rz) / maxf(rw, 1.0), 0.0, 1.0)
			riv *= clampf(1.0 - glac * 2.0, 0.0, 1.0)
			riv *= clampf(1.0 - (x - float(vp["terminus_x"]) * 0.001) / 600.0, 0.0, 1.0)
			# VERTEX COLOUR, and two of the four channels changed for a reason
			# worth writing down. The shader needs to know where the GULLIES are,
			# because snow loads in them and blows off the buttresses between
			# them - and it cannot work that out for itself: it would have to
			# re-derive `_rid` with GDScript's integer hash, which no shader has.
			# So the landform hands it over.
			#   R  glacier   ice, not snow
			#   G  river     the braid plain
			#   B  talus     scree apron, 0..1: a different material entirely
			#   A  cut       the buttress / gully field. 0.5 flat, >0.5 buttress,
			#                <0.5 gully. This is the channel that lets snow lie
			#                where it actually lies.
			var toe_d: float = minf(absf(z - float(vp["far_toe"]) * 0.001),
				absf(z - float(vp["near_toe"]) * 0.001))
			var tal := clampf(1.0 - (y - 20.0) / 130.0, 0.0, 1.0) \
				* clampf(1.0 - (toe_d - 90.0) / 190.0, 0.0, 1.0) \
				* clampf(y / 12.0, 0.0, 1.0)
			var cutv := _cut_at(x, z)
			cols[i] = Color(glac, riv, tal, clampf(cutv * 0.5 + 0.5, 0.0, 1.0))

	var idx := PackedInt32Array()
	for iz in nz - 1:
		for ix in nx - 1:
			var mx := (xs[ix] + xs[ix + 1]) * 0.5
			var mz := (zs[iz] + zs[iz + 1]) * 0.5
			# leave a hole where the pit-head's own mesh draws. Not strictly
			# needed - the site ground is 0.25 m above - but it saves the
			# overdraw in the frames a camera actually stands in.
			if mx > sx0 and mx < sx1 and mz > sz0 and mz < sz1:
				continue
			var a := iz * nx + ix
			var b := a + 1
			var c := a + nx
			var d2 := c + 1
			# Godot's front faces are CLOCKWISE - see ground.gd. This cost a day
			# once already and it will not be paid twice.
			idx.append(a); idx.append(b); idx.append(c)
			idx.append(b); idx.append(d2); idx.append(c)

	var arr := []
	arr.resize(Mesh.ARRAY_MAX)
	arr[Mesh.ARRAY_VERTEX] = verts
	arr[Mesh.ARRAY_NORMAL] = norms
	arr[Mesh.ARRAY_COLOR] = cols
	arr[Mesh.ARRAY_INDEX] = idx
	var am := ArrayMesh.new()
	am.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arr)

	var mi := MeshInstance3D.new()
	mi.name = "Valley"
	mi.mesh = am
	mi.material_override = Mats.valley_material(L)
	# nothing in it is inside the sun's 95 m shadow range, and it is 3.6 M
	# triangles that would otherwise be walked twice.
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	mi.extra_cull_margin = 4000.0
	parent.add_child(mi)

	return {"verts": verts.size(), "tris": idx.size() / 3,
		"ms": float(Time.get_ticks_usec() - t0) / 1000.0}

# ------------------------------------------------------------------ erratics
## ERRATICS. Boulders the ice carried and then simply put down when it melted,
## sitting on a floor made of something else entirely, with nothing around them.
## They are the most quietly strange object in a glaciated valley - a house-sized
## rock standing alone on a flat plain - and they are four lines.
##
## They also do a job no mountain can: they are a KNOWN SIZE at a KNOWN
## DISTANCE, out on the floor between the camera and the wall, which is the
## missing middle of THE-ICE 7.2's chain of scales. A valley with nothing in it
## between a machine and a 1,800 m wall has no scale at all, however big the wall
## is - that is 7.2's own correction and this is the cheapest answer to it.
##
## And they cluster on the moraines and along the ice's flow line rather than
## scattering, because that is where a glacier drops its load. DESIGN-PRINCIPLES
## 7's rule holds here as everywhere: the answer to "who put it there" is the
## ice, and the ice put them in lines.
static func erratics(L: SurfaceLayout, B: Batcher) -> void:
	var rng := RandomNumberGenerator.new()
	rng.seed = L.seed_v * 2654435761 + 7717
	var near_toe: float = _V["near_toe"]
	var far_toe: float = _V["far_toe"]
	var mo: float = _V["moraine_off"]
	for i in 320:
		var x := rng.randf_range(-3200.0, 3400.0)
		# three quarters of them on or beside a moraine crest, the rest strung
		# down the flow line. Never uniform.
		var z := 0.0
		var r1 := rng.randf()
		if r1 < 0.40:
			z = near_toe + mo + rng.randf_range(-110.0, 90.0)
		elif r1 < 0.76:
			z = far_toe - mo + rng.randf_range(-90.0, 110.0)
		else:
			z = rng.randf_range(near_toe + 60.0, far_toe - 60.0)
		if absf(x) < 200.0 and z > -120.0 and z < 120.0:
			continue                       # not through the pit-head
		var y := h(x, z)
		if y > 60.0:
			continue                       # floor and moraine only
		# size: a few are enormous and most are not, which is what makes the
		# enormous ones read. A uniform size distribution reads as gravel.
		var s := rng.randf_range(1.4, 4.0)
		if rng.randf() < 0.12:
			s = rng.randf_range(5.5, 13.0)
		var m: String = ["rock", "rock2", "rock3"][rng.randi() % 3]
		B.add(m, "rock", Batcher.xf(Vector3(x, y - s * 0.22, z),
			Vector3(s * rng.randf_range(0.8, 1.5), s * rng.randf_range(0.55, 0.95),
				s * rng.randf_range(0.8, 1.5)),
			rng.randf() * TAU, rng.randf_range(-0.2, 0.2), rng.randf_range(-0.2, 0.2)),
			Color(1, 1, 1) * rng.randf_range(0.62, 1.25), Batcher.FAR)

## A graded axis. `bands` is an ordered array of [from, to, step]; a step of 0
## means "geometric", which is how the last two kilometres cost eight vertices
## instead of two hundred.
static func _grade(bands: Array) -> PackedFloat32Array:
	var v := PackedFloat32Array()
	for bi in bands.size():
		var b: Array = bands[bi]
		var a: float = b[0]
		var c: float = b[1]
		var s: float = b[2]
		if s > 0.0:
			var x := a
			while x < c - 0.001:
				v.append(x)
				x += s
		else:
			# geometric, growing away from whichever end touches the fine band
			if bi == 0:
				var pre := PackedFloat32Array()
				var e := c
				var g := 90.0
				while e > a:
					e -= g
					g *= 1.42
					pre.append(e)
				pre.reverse()
				v.append_array(pre)
			else:
				var e2 := a
				var g2 := 190.0
				while e2 < c:
					v.append(e2)
					e2 += g2
					g2 *= 1.42
	v.append(bands[bands.size() - 1][1])
	return v
