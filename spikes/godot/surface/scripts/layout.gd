extends RefCounted
class_name SurfaceLayout
##
## LAYOUT LAYER - the deterministic half of the generator.
##
## This is what `blindside-gen` would own. It answers "what is where", and every
## client must agree on it bit for bit. Therefore, in this file:
##
##   * every number is an INTEGER, in MILLIMETRES (or cells / millidegrees)
##   * no float literal appears anywhere (one sqrt is called out in NOTES.md)
##   * no Dictionary is ever iterated; ordered Arrays only
##   * the RNG is an integer LCG seeded from the site seed and split by stream id,
##     so call order inside one stream is the only ordering that matters
##
## Everything a machine can collide with, walk on, navigate by, or that a match
## rule refers to is decided here. Nothing else is.
##
## Port note: the output is a Dictionary purely because GDScript has no structs.
## In Rust it is a `SitePlan` of Vec<..> and the field order is the order here.

const MM := 1000  # millimetres per metre

# ---------------------------------------------------------------- integer rng
class IntRng extends RefCounted:
	var s: int
	func _init(seed_v: int, stream: int) -> void:
		s = ((seed_v * 2654435761) ^ (stream * 40503)) & 0x7FFFFFFF
		if s == 0:
			s = 1 + stream
		for i in 4:
			next()
	func next() -> int:
		s = (s * 1103515245 + 12345) & 0x7FFFFFFF
		return s
	## uniform in [lo, hi] inclusive, integers only
	func rng(lo: int, hi: int) -> int:
		if hi <= lo:
			return lo
		return lo + (next() % (hi - lo + 1))
	func chance(num: int, den: int) -> bool:
		return (next() % den) < num

# ---------------------------------------------------------------- the plan
var seed_v: int
var plan: Dictionary

# flat caches for the height query, which is called ~100k times per site build.
# Dictionary lookups inside that loop cost more than the arithmetic does.
var _tcx := PackedInt64Array()
var _tcz := PackedInt64Array()
var _tr2 := PackedInt64Array()
var _th := PackedInt64Array()
var _px0 := PackedInt64Array()
var _pz0 := PackedInt64Array()
var _px1 := PackedInt64Array()
var _pz1 := PackedInt64Array()
var _pad_h := 0

func _init(p_seed: int) -> void:
	seed_v = p_seed
	plan = _build()
	for t in plan["spoil"]:
		_tcx.append(t["cx"])
		_tcz.append(t["cz"])
		_tr2.append(int(t["r"]) * int(t["r"]))
		_th.append(t["h"])
	for p in plan["pads"]:
		_px0.append(p["x0"])
		_pz0.append(p["z0"])
		_px1.append(p["x1"])
		_pz1.append(p["z1"])
	_pad_h = plan["pads"][0]["h"]

func _build() -> Dictionary:
	var P := {}
	P["seed"] = seed_v

	# ---- site bounds. Fixed; the seed does not move the world box.
	P["site"] = {"x0": -78 * MM, "z0": -74 * MM, "x1": 96 * MM, "z1": 74 * MM}

	# ---- the shaft. Origin. 2400 x 2000 collar (vision board guess 5).
	P["shaft"] = {"cx": 0, "cz": 0, "w": 2400, "d": 2000,
		"plinth_w": 5200, "plinth_d": 4600, "plinth_h": 400,
		"collar_h": 150, "lined_depth": 3000, "depth": 40 * MM}

	# ---- headframe over the collar. Four legs, a raked back leg, sheave deck.
	#      Height and spread are seeded within a band; the sim must agree on them
	#      because they are collision and because the hoist reaches down.
	var rf := IntRng.new(seed_v, 1)
	var hf_h := rf.rng(11600, 13400)
	P["headframe"] = {"cx": 0, "cz": 0,
		"spread_x": rf.rng(6800, 7800), "spread_z": rf.rng(6000, 7000),
		"top_x": 2600, "top_z": 2400,
		"height": hf_h, "deck_h": hf_h - 1400,
		"sheave_r": 1100, "sheave_gap": 1500,
		"back_leg_x": (hf_h * 9) / 10}

	# ---- hardstanding. Slab module 3600 mm (3 x the industry's 1.2 m).
	var pads: Array = []
	pads.append({"kind": "main", "x0": -32 * MM, "z0": -26 * MM, "x1": 30 * MM, "z1": 26 * MM, "h": 150})
	pads.append({"kind": "course_apron", "x0": 30 * MM, "z0": -10 * MM, "x1": 38 * MM, "z1": 10 * MM, "h": 120})
	P["pads"] = pads
	P["slab_module"] = 3600

	# ---- buildings. THE INHERITED (dead, roofless, iron and stone) and
	#      THE BROUGHT (light steel, recent, bolted onto the pad).
	var bl: Array = []
	bl.append({"kind": "winding_house", "reg": "old", "x0": 6 * MM, "z0": -20 * MM,
		"x1": 17 * MM, "z1": -10 * MM, "h": 5600, "roof": 0, "gable": 1})
	bl.append({"kind": "boiler_house", "reg": "old", "x0": 18 * MM, "z0": -22 * MM,
		"x1": 26 * MM, "z1": -13 * MM, "h": 4200, "roof": 0, "gable": 0})
	bl.append({"kind": "fan_house", "reg": "old", "x0": -15 * MM, "z0": -24 * MM,
		"x1": -8 * MM, "z1": -18 * MM, "h": 3600, "roof": 1, "gable": 0})
	bl.append({"kind": "service_bay", "reg": "new", "x0": -26 * MM, "z0": -8 * MM,
		"x1": -12 * MM, "z1": 2 * MM, "h": 5400, "roof": 1, "gable": 0})
	bl.append({"kind": "store", "reg": "new", "x0": -31 * MM, "z0": 8 * MM,
		"x1": -23 * MM, "z1": 14 * MM, "h": 3000, "roof": 1, "gable": 0})
	P["buildings"] = bl

	# ---- functional zones. LAYOUT declares the rectangle and what it is for;
	#      DRESSING decides what individual objects land inside it. A zone is
	#      layout because a machine cannot walk through a full one.
	var zones: Array = []
	zones.append({"kind": "charge_row",   "x0": -27 * MM, "z0": 5 * MM,  "x1": -15 * MM, "z1": 9 * MM})
	zones.append({"kind": "container_row","x0": 12 * MM,  "z0": 7 * MM,  "x1": 28 * MM,  "z1": 24 * MM})
	zones.append({"kind": "tank_farm",    "x0": 2 * MM,   "z0": 13 * MM, "x1": 10 * MM,  "z1": 24 * MM})
	zones.append({"kind": "spares",       "x0": -10 * MM, "z0": 9 * MM,  "x1": -2 * MM,  "z1": 20 * MM})
	zones.append({"kind": "drums",        "x0": -21 * MM, "z0": 16 * MM, "x1": -13 * MM, "z1": 24 * MM})
	zones.append({"kind": "scrap",        "x0": 18 * MM,  "z0": -8 * MM, "x1": 29 * MM,  "z1": 2 * MM})
	zones.append({"kind": "pallets",      "x0": -31 * MM, "z0": -23 * MM,"x1": -22 * MM, "z1": -13 * MM})
	zones.append({"kind": "transformer",  "x0": -7 * MM,  "z0": -24 * MM,"x1": 0,        "z1": -17 * MM})
	zones.append({"kind": "muster",       "x0": -10 * MM, "z0": 2 * MM,  "x1": -3 * MM,  "z1": 6 * MM})
	P["zones"] = zones

	# ---- the training course (DESIGN-PRINCIPLES 3: teaching is a physical act).
	#      A branching corridor on a 1800 mm passage module, walls 1200 high.
	#      Unambiguously layout: the sim walks and scores this graph.
	P["course"] = _course()

	# ---- spoil tips. Layout: they are terrain, they block sight and feet.
	var rs := IntRng.new(seed_v, 3)
	var spoil: Array = []
	var ring: Array = [
		[-52, -46], [-14, -54], [22, -50], [50, -34], [70, 8],
		[52, 46], [12, 54], [-30, 50], [-58, 22], [-66, -14],
		[78, -22], [40, 62], [-44, -8], [86, 30]]
	for i in ring.size():
		var c: Array = ring[i]
		spoil.append({
			"cx": c[0] * MM + rs.rng(-3500, 3500),
			"cz": c[1] * MM + rs.rng(-3500, 3500),
			"r":  rs.rng(9000, 22000),
			"h":  rs.rng(3200, 10500)})
	P["spoil"] = spoil

	# ---- haul road: gate in the west fence to the collar apron.
	P["road"] = [[-78 * MM, 4 * MM], [-56 * MM, 3 * MM], [-40 * MM, 0], [-33 * MM, -2 * MM]]
	P["road_w"] = 7000

	# ---- perimeter fence with a gate span. Layout: it is a wall.
	# the fence encloses the yard AND the training course: the course is part of
	# the compound, and a machine walking the course has not left the site.
	var fx0 := -34 * MM
	var fz0 := -34 * MM
	var fx1 := 92 * MM
	var fz1 := 34 * MM
	P["fence"] = [[fx0, fz0], [fx1, fz0], [fx1, fz1], [fx0, fz1], [fx0, fz0]]
	P["fence_h"] = 2400
	P["gate"] = {"x": fx0, "z0": 1 * MM, "z1": 8 * MM}

	# ---- circulation. Where machines and people walk between the collar, the
	#      bay, the charge row, the gate and the course. LAYOUT owns it because it
	#      is the route, and because dressing must not block it.
	P["walkways"] = [
		[[-33 * MM, -2 * MM], [0, 0]],
		[[0, 0], [-19 * MM, -3 * MM]],
		[[0, 0], [33 * MM, 0]],
		[[-19 * MM, -3 * MM], [-20 * MM, 11 * MM]],
		[[-27 * MM, 11 * MM], [-11 * MM, 11 * MM]],
		[[0, 0], [14 * MM, 9 * MM]]]
	P["walkway_w"] = 3400

	# ---- KEEP-CLEAR. DESIGN-PRINCIPLES 7: "clear ground is a feature ... their
	#      emptiness reads as use". These are the pieces of ground that are driven,
	#      turned on or worked daily and are therefore SWEPT: nothing stands on
	#      them and nothing collects on them, not even litter. LAYOUT owns them for
	#      the same reason it owns the walkways - they are where a machine goes -
	#      and dressing is forbidden to place anything inside one.
	P["clear_r"] = [{"cx": 0, "cz": 0, "r": 11000}]           # collar turning circle
	P["clear_rects"] = [
		{"x0": -26 * MM, "z0": 2 * MM,   "x1": -11 * MM, "z1": 5 * MM},    # service bay apron
		{"x0": -28 * MM, "z0": 9 * MM,   "x1": -13 * MM, "z1": 12 * MM},   # charge row frontage
		{"x0": -11 * MM, "z0": 1 * MM,   "x1": -2 * MM,  "z1": 7 * MM},    # muster square
		{"x0": 28 * MM,  "z0": -5 * MM,  "x1": 38 * MM,  "z1": 5 * MM}]    # course start apron

	# ---- RANKS and STANDS. DESIGN-PRINCIPLES 7: placement is arrangements, not
	#      scatter. A RANK is a hand-listed strip of ground - against a wall, along
	#      a pad edge, in a corner - along which stores are laid out in line. A
	#      STAND is one bay cut out of a rank by an integer rule: a rectangle, a
	#      yaw square to the site grid, and a class.
	#
	#      The line: LAYOUT decides WHERE a stand is, HOW BIG it is and WHICH WAY
	#      it faces, because a stand is occupied ground - a machine cannot walk
	#      through a rack, so a stand is exactly as much layout as a zone is.
	#      DRESSING decides WHAT stands in it. Randomness in this file never
	#      touches the position or angle of an individual object; it sets bay
	#      lengths and the gaps between them, and nothing finer.
	#
	#      rank = [x, z, run, depth, axis, class]   axis 0 = bays march along +x
	#      class 0 stores   1 lay-down   2 consumables   3 marshalling
	P["ranks"] = [
		[-32 * MM, -12200,   10000, 3400, 0, 0],  # west stores, in the 5 m between the pallet yard and the bay
		[-32 * MM,  16 * MM,  9500, 3000, 1, 1],  # NW lay-down, outer run
		[-28400,    16 * MM,  9500, 3000, 1, 0],  # NW stores, inner run - the two make an aisle
		[-21 * MM, -25500,   12000, 4000, 1, 0],  # SW stores, off the pallet yard
		[    900,  -25500,   14000, 3600, 1, 2],  # south consumables, between the pen and the winding house
		[ 17 * MM, -26 * MM, 12000, 3200, 0, 1],  # SE lay-down, along the south edge
		[ 18 * MM,   2800,   11000, 3400, 0, 0],  # east stores, between the scrap bay and the containers
		[-12 * MM, -16 * MM,  8000, 4000, 0, 2],  # bunded store, south of the collar
		[-32 * MM, -11 * MM,  6200, 4500, 1, 3],  # west marshalling bays, south of the haul road
		[-32 * MM,     800,   6400, 4500, 1, 3]]  # west marshalling bays, north of it - the road divides them
	P["stands"] = _stands(P)

	# ---- lighting columns. Position is layout (they are posts, and after dark
	#      they decide where a player can see). Fitting and lumens are dressing.
	var rl := IntRng.new(seed_v, 4)
	var cols: Array = []
	var col_seed: Array = [[-29, -22], [-29, 18], [10, -25], [25, 15], [27, -21],
		[-4, 23], [-19, -14], [17, 1], [35, 0], [-31, 1], [6, -6], [-13, 22]]
	for i in col_seed.size():
		var c2: Array = col_seed[i]
		cols.append({"x": c2[0] * MM + rl.rng(-800, 800), "z": c2[1] * MM + rl.rng(-800, 800),
			"h": rl.rng(8000, 11000), "heads": rl.rng(1, 2)})
	P["columns"] = cols

	# ---- power line marching in from the west to the transformer pen.
	var poles: Array = []
	var px := -76 * MM
	while px < -9 * MM:
		poles.append({"x": px, "z": -21 * MM + (px / 30), "h": 11000 + (absi(px / 100) % 900)})
		px += 22 * MM
	P["poles"] = poles

	# ---- masts. Comms mast (the uplink) and the old vent stack.
	P["masts"] = [
		{"kind": "comms", "x": -30 * MM, "z": -21 * MM, "h": 21000, "reg": "new"},
		{"kind": "stack", "x": 23 * MM, "z": -19 * MM, "h": 17000, "reg": "old"}]

	# ---- kit a machine stands on or plugs into, so the sim knows about it.
	P["stations"] = [
		{"kind": "listening_post", "x": -4200, "z": 3400, "yaw": 30000},
		{"kind": "bench",          "x": -19 * MM, "z": -3 * MM, "yaw": 0},
		{"kind": "cradle",         "x": -22500,   "z": -1500,   "yaw": 90000},
		{"kind": "course_root",    "x": 33 * MM,  "z": 0,       "yaw": 0}]

	# ---- gantry over the service bay; hoist beam over the collar.
	P["gantry"] = {"x0": -26 * MM, "x1": -12 * MM, "z": -3 * MM, "h": 4600, "rail_gauge": 6000}

	P["hash"] = _hash(P)
	return P

# ------------------------------------------------------------------ stands
## Cut a rank into bays. Walk the run placing a bay of a seeded length on the
## 1200 mm module, then a seeded gap, and reject any bay that would sit on a
## building, a stocked zone, a walkway or a swept apron. Integer throughout: the
## walkway test walks the centreline in ~300 mm steps and asks whether the point
## is inside the bay grown by the walkway half-width, which needs no sqrt.
func _stands(P: Dictionary) -> Array:
	var r := IntRng.new(seed_v, 5)
	var out: Array = []
	var ranks: Array = P["ranks"]
	for ri in ranks.size():
		var rk: Array = ranks[ri]
		var ax: int = rk[4]
		var run: int = rk[2]
		var dep: int = rk[3]
		var t := 1200 * r.rng(0, 2)
		while t < run - 3600:
			var blen := 1200 * r.rng(3, 7)
			if t + blen > run:
				blen = ((run - t) / 1200) * 1200
			if blen < 3600:
				break
			var x0: int = rk[0] + (t if ax == 0 else 0)
			var z0: int = rk[1] + (0 if ax == 0 else t)
			var x1: int = x0 + (blen if ax == 0 else dep)
			var z1: int = z0 + (dep if ax == 0 else blen)
			if _stand_ok(P, x0, z0, x1, z1):
				out.append({"x0": x0, "z0": z0, "x1": x1, "z1": z1,
					"yaw": (0 if ax == 0 else 90000), "cls": rk[5], "rank": ri})
			t += blen + 1200 * r.rng(1, 3)
	return out

const STAND_PAD := 700          # a stand keeps this much off anything it is not

func _stand_ok(P: Dictionary, x0: int, z0: int, x1: int, z1: int) -> bool:
	# stores stand on concrete, never on spoil
	if not (on_pad_raw(P, x0, z0) and on_pad_raw(P, x1, z1)):
		return false
	for b in P["buildings"]:
		if _overlap(x0, z0, x1, z1, b["x0"], b["z0"], b["x1"], b["z1"], STAND_PAD):
			return false
	for zz in P["zones"]:
		if _overlap(x0, z0, x1, z1, zz["x0"], zz["z0"], zz["x1"], zz["z1"], STAND_PAD):
			return false
	for cr in P["clear_rects"]:
		if _overlap(x0, z0, x1, z1, cr["x0"], cr["z0"], cr["x1"], cr["z1"], STAND_PAD):
			return false
	for cc in P["clear_r"]:
		var dx: int = maxi(maxi(x0 - cc["cx"], 0), cc["cx"] - x1)
		var dz: int = maxi(maxi(z0 - cc["cz"], 0), cc["cz"] - z1)
		var rr: int = cc["r"]
		if dx * dx + dz * dz < rr * rr:
			return false
	var hw: int = P["walkway_w"] / 2 + STAND_PAD
	for w in P["walkways"]:
		var ax0: int = w[0][0]
		var az0: int = w[0][1]
		var bx0: int = w[1][0]
		var bz0: int = w[1][1]
		var dx2: int = bx0 - ax0
		var dz2: int = bz0 - az0
		var steps: int = (absi(dx2) + absi(dz2)) / 300 + 1
		for k in range(steps + 1):
			var px: int = ax0 + (dx2 * k) / steps
			var pz: int = az0 + (dz2 * k) / steps
			if px > x0 - hw and px < x1 + hw and pz > z0 - hw and pz < z1 + hw:
				return false
	return true

static func _overlap(ax0: int, az0: int, ax1: int, az1: int,
		bx0: int, bz0: int, bx1: int, bz1: int, pad: int) -> bool:
	return ax0 < bx1 + pad and ax1 > bx0 - pad and az0 < bz1 + pad and az1 > bz0 - pad

static func on_pad_raw(P: Dictionary, x: int, z: int) -> bool:
	for p in P["pads"]:
		if x >= p["x0"] and x <= p["x1"] and z >= p["z0"] and z <= p["z1"]:
			return true
	return false

# ------------------------------------------------------------------ course
## A branching corridor grown eastward from the root on an 1800 mm module.
func _course() -> Dictionary:
	var r := IntRng.new(seed_v, 2)
	var nodes: Array = [[0, 0]]     # in cells
	var edges: Array = []
	var frontier: Array = [0]
	var depth: Array = [0]
	var target_nodes := 26
	var guard := 0
	while nodes.size() < target_nodes and guard < 500:
		guard += 1
		if frontier.is_empty():
			break
		var fi := r.next() % frontier.size()
		var pi: int = frontier[fi]
		var pd: int = depth[pi]
		if pd > 6:
			frontier.remove_at(fi)
			continue
		var branches := 2 if r.chance(3, 5) else 1
		var made := 0
		for b in branches:
			var dirs: Array = [[1, 0], [1, 1], [1, -1], [0, 1], [0, -1], [1, 0]]
			var d: Array = dirs[r.next() % dirs.size()]
			var length := r.rng(3, 7)
			var nx: int = nodes[pi][0] + d[0] * length
			var nz: int = nodes[pi][1] + d[1] * length
			if nx < 0 or nx > 24 or nz < -13 or nz > 13:
				continue
			var clash := false
			for n in nodes:
				if absi(n[0] - nx) + absi(n[1] - nz) < 2:
					clash = true
					break
			if clash:
				continue
			nodes.append([nx, nz])
			edges.append([pi, nodes.size() - 1])
			depth.append(pd + 1)
			frontier.append(nodes.size() - 1)
			made += 1
		if made == 0:
			frontier.remove_at(fi)
	var deg: Array = []
	for i in nodes.size():
		deg.append(0)
	for e in edges:
		deg[e[0]] += 1
		deg[e[1]] += 1
	var leaves: Array = []
	for i in nodes.size():
		if deg[i] == 1 and i != 0:
			leaves.append(i)
	var cargo_leaf: int = 0
	if leaves.size() > 0:
		cargo_leaf = leaves[r.next() % leaves.size()]
	return {"pitch": 2400, "ox": 33 * MM, "oz": 0,
		"nodes": nodes, "edges": edges, "leaves": leaves,
		"cargo_leaf": cargo_leaf, "wall_h": 1200, "half_w": 900}

# ------------------------------------------------------------------ hashing
## The layout hash goes into the replay. Any dressing change must leave it alone.
func _hash(P: Dictionary) -> int:
	var h := 146959810393466560
	var keys: Array = ["seed", "site", "shaft", "headframe", "pads", "buildings",
		"zones", "course", "spoil", "road", "fence", "columns", "poles",
		"masts", "stations", "gantry", "walkways", "clear_r", "clear_rects",
		"ranks", "stands"]
	for k in keys:
		h = _mix(h, str(P[k]).hash())
	return h

func _mix(h: int, v: int) -> int:
	h = (h ^ v) & 0x7FFFFFFFFFFFF
	h = (h * 1099511628211) & 0x7FFFFFFFFFFFF
	return h

# ------------------------------------------------------------------ queries
## Ground surface height in mm at an integer mm position. LAYOUT owns this
## because it is what a foot stands on. Integer in, integer out.
## No square root anywhere: the tip profile and the pad feather are both written
## against SQUARED distance, which is a generator choice, not an approximation -
## the profile is exactly what the rule says it is, and it ports to Rust as
## integer arithmetic with no isqrt and no float.
const PAD_FEATHER2 := 16000000     # (4000 mm)^2

func ground_mm(x: int, z: int) -> int:
	var h := _vnoise(x, z, 17000, 900) + _vnoise(x + 5000, z - 3000, 6100, 260)
	var n := _tcx.size()
	for i in n:
		var dx: int = x - _tcx[i]
		var dz: int = z - _tcz[i]
		var d2: int = dx * dx + dz * dz
		var r2: int = _tr2[i]
		if d2 < r2:
			var t01: int = ((r2 - d2) * 1000) / r2   # 0..1000
			h += (_th[i] * t01 * t01) / 1000000
	# The pads are graded flat and the grade feathers out over 4 m. A machine
	# stands on this, so it is layout, not dressing.
	var pd2 := _pad_dist2_mm(x, z)
	if pd2 < PAD_FEATHER2:
		var k: int = ((PAD_FEATHER2 - pd2) * 1000) / PAD_FEATHER2
		k = (k * k) / 1000
		h = h + ((_pad_h - h) * k) / 1000
	return h

## 0 inside any pad, else the SQUARED mm distance to the nearest pad edge.
func _pad_dist2_mm(x: int, z: int) -> int:
	var best := 0x3FFFFFFFFFFF
	var n := _px0.size()
	for i in n:
		var dx: int = maxi(maxi(_px0[i] - x, 0), x - _px1[i])
		var dz: int = maxi(maxi(_pz0[i] - z, 0), z - _pz1[i])
		var d2: int = dx * dx + dz * dz
		if d2 < best:
			best = d2
	return best

func on_pad(x: int, z: int) -> bool:
	var n := _px0.size()
	for i in n:
		if x >= _px0[i] and x <= _px1[i] and z >= _pz0[i] and z <= _pz1[i]:
			return true
	return false

func pad_h() -> int:
	return _pad_h

## Is this ground SWEPT - a lane, a turning circle or a working apron? Layout
## query, integer in. Dressing asks it before it drops anything on the floor.
func swept(x: int, z: int) -> bool:
	for cc in plan["clear_r"]:
		var dx: int = x - cc["cx"]
		var dz: int = z - cc["cz"]
		var rr: int = cc["r"]
		if dx * dx + dz * dz < rr * rr:
			return true
	for cr in plan["clear_rects"]:
		if x > cr["x0"] and x < cr["x1"] and z > cr["z0"] and z < cr["z1"]:
			return true
	var hw: int = plan["walkway_w"] / 2
	for w in plan["walkways"]:
		var ax: int = w[0][0]
		var az: int = w[0][1]
		var bx: int = w[1][0]
		var bz: int = w[1][1]
		var abx: int = bx - ax
		var abz: int = bz - az
		var den: int = abx * abx + abz * abz
		if den == 0:
			continue
		var num: int = (x - ax) * abx + (z - az) * abz
		if num < 0:
			num = 0
		elif num > den:
			num = den
		var cx: int = ax + (abx * num) / den
		var cz: int = az + (abz * num) / den
		var dx2: int = x - cx
		var dz2: int = z - cz
		if dx2 * dx2 + dz2 * dz2 < hw * hw:
			return true
	return false

## Is this ground inside a stand - i.e. does an arrangement occupy it?
func in_stand(x: int, z: int) -> bool:
	for st in plan["stands"]:
		if x > st["x0"] and x < st["x1"] and z > st["z0"] and z < st["z1"]:
			return true
	return false

## Deterministic integer value noise, roughly [-amp, amp].
func _vnoise(x: int, z: int, period: int, amp: int) -> int:
	var cx := _fdiv(x, period)
	var cz := _fdiv(z, period)
	var fx := x - cx * period
	var fz := z - cz * period
	var a := _cell(cx, cz)
	var b := _cell(cx + 1, cz)
	var c := _cell(cx, cz + 1)
	var d := _cell(cx + 1, cz + 1)
	var tx := (fx * 1000) / period
	var tz := (fz * 1000) / period
	tx = (tx * tx * (3000 - 2 * tx)) / 1000000
	tz = (tz * tz * (3000 - 2 * tz)) / 1000000
	var ab := a + ((b - a) * tx) / 1000
	var cd := c + ((d - c) * tx) / 1000
	var v := ab + ((cd - ab) * tz) / 1000
	return (v * amp) / 1000

func _fdiv(a: int, b: int) -> int:
	var q := a / b
	if a % b != 0 and (a < 0) != (b < 0):
		q -= 1
	return q

func _cell(cx: int, cz: int) -> int:
	var h := ((cx * 374761393) + (cz * 668265263) + seed_v * 2246822519) & 0x7FFFFFFF
	h = ((h ^ (h >> 13)) * 1274126177) & 0x7FFFFFFF
	return (h % 2001) - 1000
