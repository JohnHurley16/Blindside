# ---------------------------------------------------------------------------
# BLINDSIDE -- CAVE TOPOLOGY
#
# THIS FILE IS THE DETERMINISTIC LAYER. It is what `blindside-gen` would own.
#
# RULES OBEYED HERE (docs/DETERMINISM.md, DESIGN-PRINCIPLES section 5):
#   * no float anywhere. every length is an integer in millimetres.
#   * no dictionary iteration. every loop is over an integer range or over a
#     PackedInt32Array in index order.
#   * no engine RNG, no time, no node lookups. the only source of variety is
#     the counter-based hash `draw(purpose, a, b)` below, which is stateless:
#     the ORDER of calls cannot change any result.
#   * output is a plain data blob (PackedByteArray / PackedInt32Array / rows of
#     ints). It is JSON-able and it is what would be hashed into the replay.
#     `content_hash()` at the bottom is that hash.
#
# NOTHING IN dressing.gd MAY WRITE BACK INTO THIS.
# ---------------------------------------------------------------------------
class_name CaveTopology
extends RefCounted

const CELL_MM: int = 600          # 0.6 m per cell, inherited from phase1

# width classes -------------------------------------------------------------
const WC_CRAWL: int = 0
const WC_NARROW: int = 1
const WC_PASSAGE: int = 2
const WC_HALL: int = 3
# half-width and height per class, millimetres. GUESS: read off
# docs/art/vision/cave/NOTES.md B2, which itself calls the metres a guess.
const WC_HALFWIDTH_MM: Array = [750, 1050, 1350, 1950]
const WC_HEIGHT_MM: Array    = [1300, 2200, 3200, 5000]
const WC_RADIUS_CELLS: Array = [1, 2, 2, 3]     # stamp radius when rasterising

# cell states ---------------------------------------------------------------
const ROCK: int = 0
const DRY: int = 1
const FLOODED: int = 2

# works bit flags. "the works" is where the prior industry ran things.
# These ARE topology: the sim needs them (rails are trammable, sets pinch the
# section, the Bus is a hazard, a beacon is a Fix source).
const WK_RAIL: int      = 1 << 0
const WK_SETS: int      = 1 << 1     # timber sets, 1.2 m module
const WK_BOLTLINE: int  = 1 << 2     # rock bolts at the springing
const WK_BUS: int       = 1 << 3     # THE BUS, live conductor along the crown
const WK_GUTTER: int    = 1 << 4     # 300 x 90 drainage gutter, one side
const WK_PIPE: int      = 1 << 5     # cast pipe run on the haunch
const WK_TRAY: int      = 1 << 6     # BROUGHT: composite cable tray
const WK_SPOIL: int     = 1 << 7     # spoil heap against one wall
const WK_MESH: int      = 1 << 8     # ground support mesh, bad ground only
const WK_LAUNDER: int   = 1 << 9     # timber launder on posts
const WK_DUCT: int      = 1 << 10    # BROUGHT: ventilation ducting on the crown
const WK_BEACON: int    = 1 << 11    # BROUGHT: the player beacon chain
const WK_PLATE: int     = 1 << 12    # cast survey index plate
const WK_SETFAIL: int   = 1 << 13    # this set has failed, neighbours stand
const WK_STANDWATER: int = 1 << 14   # standing water on the floor, not a sump
const WK_PLANT: int     = 1 << 15    # machine ground: pump, flywheel, pipework
const WK_KIT: int       = 1 << 16    # BROUGHT: a modern crate / charger / mast

# station kinds -------------------------------------------------------------
const K_DRIVE: int = 0
const K_CHAMBER: int = 1
const K_JUNCTION: int = 2
const K_SHAFT: int = 3

# station row layout --------------------------------------------------------
const S_X: int = 0          # cell coordinate along the grid X
const S_Y: int = 1          # cell coordinate along the grid Y
const S_FLOOR_MM: int = 2   # floor height above datum, mm (signed)
const S_WIDTH: int = 3      # width class
const S_WORKED: int = 4     # 0..255, how much the industry touched it
const S_STATE: int = 5      # DRY / FLOODED
const S_WATER_MM: int = 6   # water surface above datum, mm; -1000000 if dry
const S_WORKS: int = 7      # works bitfield
const S_DEPTH: int = 8      # cells from the shaft along the graph
const S_INTEG: int = 9      # structural integrity 0..255 (low = bad ground)
const S_WET: int = 10       # 0..255 surface wetness (the `wet` scalar)
const S_FRACTURE: int = 11  # 3..14, the `fracture` scalar (voronoi frequency)
const S_BEDDING: int = 12   # 4..35, the `bedding` scalar x10
const S_KIND: int = 13      # K_*
const S_EDGE: int = 14      # which edge (0 = main drive, 1.. = crosscuts)
const S_DISCOVERY: int = 15 # 0 none, else a discovery id (blocks by depth)
const S_ROW: int = 16

var cave_seed: int = 0
var w_cells: int = 0
var h_cells: int = 0
var grid_state: PackedByteArray          # w*h, ROCK/DRY/FLOODED
var grid_station: PackedInt32Array       # w*h, owning station index or -1
var stations: Array = []                 # Array[PackedInt32Array] of S_ROW
var edges: Array = []                    # Array[PackedInt32Array] station ids
var chambers: PackedInt32Array           # rows of 5: x, y, r_cells, plant, sid
var junctions: PackedInt32Array          # station ids
var water_datum_mm: int = 0

# ---------------------------------------------------------------------------
# Stateless counter-based RNG. draw(purpose, a, b) -> [0, 2^32).
# The order of calls cannot affect any result. Ports to Rust verbatim.
# ---------------------------------------------------------------------------
const M32: int = 0xFFFFFFFF

func draw(purpose: int, a: int, b: int) -> int:
	var x: int = cave_seed & M32
	x = (x ^ ((purpose * 0x9E3779B1) & M32)) & M32
	x = (x ^ ((a * 0x85EBCA77) & M32)) & M32
	x = (x ^ ((b * 0xC2B2AE3D) & M32)) & M32
	x = (x ^ (x >> 15)) & M32
	x = (x * 0x2545F491) & M32
	x = (x ^ (x >> 13)) & M32
	x = (x * 0x27D4EB2F) & M32
	x = (x ^ (x >> 16)) & M32
	return x

func draw_range(purpose: int, a: int, b: int, lo: int, hi: int) -> int:
	return lo + int(draw(purpose, a, b) % (hi - lo + 1))

func draw_pct(purpose: int, a: int, b: int) -> int:
	return int(draw(purpose, a, b) % 100)

# ---------------------------------------------------------------------------
func generate(p_seed: int, length_cells: int) -> void:
	cave_seed = p_seed & M32
	w_cells = length_cells + 14
	h_cells = 76
	grid_state = PackedByteArray()
	grid_state.resize(w_cells * h_cells)
	grid_station = PackedInt32Array()
	grid_station.resize(w_cells * h_cells)
	for i in range(w_cells * h_cells):
		grid_state[i] = ROCK
		grid_station[i] = -1
	stations = []
	edges = []
	chambers = PackedInt32Array()
	junctions = PackedInt32Array()

	_build_main_drive(length_cells)
	_build_crosscuts(length_cells)
	_assign_works()
	_rasterise()

# --- rule 1: the spine -----------------------------------------------------
# The main drive runs +X. Its Y wanders by a bounded integer random walk: every
# 4 cells it may step one cell left or right, biased back toward the centre so
# it cannot run off the grid. Floor falls 7 mm per cell for the first 62% of
# the stretch and rises 11 mm per cell after: that is what makes the sump a
# sump. Nothing else decides where water goes.
func _build_main_drive(n: int) -> void:
	var ids := PackedInt32Array()
	var y: int = h_cells / 2
	var floor_mm: int = 0
	var wc: int = WC_PASSAGE
	var wc_hold: int = 0
	for i in range(n):
		if i % 4 == 0 and i > 0:
			var d: int = draw_range(11, i, 0, -1, 1)
			if y > h_cells / 2 + 7:
				d = -1
			elif y < h_cells / 2 - 7:
				d = 1
			y += d
		# Floor profile: a gentle general fall of 2 mm per cell, plus ONE
		# localised bowl two thirds of the way in. The bowl is the only reason
		# there is a sump; nothing else decides where water goes.
		floor_mm = -(i * 2)
		var sump_c: int = (n * 58) / 100
		var sump_half: int = maxi(6, n / 11)
		var off: int = absi(i - sump_c)
		if off < sump_half:
			floor_mm -= ((sump_half - off) * 1500) / sump_half
		# width class runs: a class holds for 6..22 cells. Deeper ground is more
		# likely to be a driven passage and less likely to be a crawl.
		if wc_hold <= 0:
			wc_hold = draw_range(12, i, 0, 6, 22)
			var roll: int = draw_pct(13, i, 0)
			var deep: int = (i * 100) / maxi(1, n)
			if deep < 22:
				wc = WC_CRAWL if roll < 16 else (WC_NARROW if roll < 55 else WC_PASSAGE)
			elif deep < 78:
				wc = WC_NARROW if roll < 20 else (WC_PASSAGE if roll < 88 else WC_HALL)
			else:
				wc = WC_PASSAGE if roll < 72 else WC_HALL
		wc_hold -= 1

		var st := PackedInt32Array()
		st.resize(S_ROW)
		st[S_X] = i + 7
		st[S_Y] = y
		st[S_FLOOR_MM] = floor_mm
		st[S_WIDTH] = wc
		# worked: 0 at the shaft, climbing to machine ground at the far end.
		# ART-DIRECTION section 7: worked climbs with depth (karst -> cut drive
		# -> machine ground). Integer ramp with three knees, per mille of the
		# stretch.
		var wk: int = 0
		var p: int = (i * 1000) / maxi(1, n)
		if p < 130:
			wk = 0
		elif p < 300:
			wk = ((p - 130) * 195) / 170
		elif p < 640:
			wk = 195 + ((p - 300) * 35) / 340
		else:
			wk = 230 + ((p - 640) * 25) / 360
		st[S_WORKED] = clampi(wk, 0, 255)
		# The industry drove to a standard section. Where it cut (worked > 128)
		# the passage is never narrower than a PASSAGE -- ART-DIRECTION 3.4 puts
		# the horseshoe drive at 2.4 x 2.4 m and the module is built to it. This
		# is why a driven length reads as built and a natural one does not.
		if st[S_WORKED] > 128:
			st[S_WIDTH] = maxi(st[S_WIDTH], WC_PASSAGE)
		st[S_STATE] = DRY
		st[S_WATER_MM] = -1000000
		st[S_WORKS] = 0
		st[S_DEPTH] = i
		st[S_INTEG] = draw_range(14, i / 5, 0, 40, 255)
		st[S_KIND] = K_SHAFT if i == 0 else K_DRIVE
		st[S_EDGE] = 0
		st[S_DISCOVERY] = 0
		# fracture and bedding are properties of the ROCK, so they change on a
		# coarse block (every 9 cells), never per cell, or the wall boils.
		var blk: int = i / 9
		st[S_FRACTURE] = draw_range(15, blk, 0, 3, 14)
		st[S_BEDDING] = draw_range(16, blk, 1, 4, 35)
		st[S_WET] = 0
		stations.append(st)
		ids.append(stations.size() - 1)
	edges.append(ids)

	# --- rule 2: chambers. Three along the drive plus a plant chamber deep.
	# A chamber that holds plant must be taller than the passages that reach it
	# (ART-DIRECTION 5.5 / cave NOTES design problem 3), so it is forced HALL.
	var chamber_at := PackedInt32Array([(n * 17) / 100, (n * 44) / 100, (n * 71) / 100, (n * 92) / 100])
	for ci in range(chamber_at.size()):
		var si: int = clampi(chamber_at[ci] + draw_range(17, ci, 0, -3, 3), 2, n - 3)
		var r: int = draw_range(18, ci, 0, 5, 9)
		var st: PackedInt32Array = stations[si]
		st[S_WIDTH] = WC_HALL
		st[S_KIND] = K_CHAMBER
		stations[si] = st
		for k in range(1, 4):
			for s2 in [si - k, si + k]:
				if s2 >= 0 and s2 < n:
					var q: PackedInt32Array = stations[s2]
					q[S_WIDTH] = maxi(q[S_WIDTH], WC_HALL if k <= 2 else WC_PASSAGE)
					stations[s2] = q
		chambers.append(st[S_X])
		chambers.append(st[S_Y])
		chambers.append(r)
		chambers.append(1 if ci == 3 else 0)
		chambers.append(si)

	# --- rule 3: the sump. A cell whose floor is below the water datum is
	# flooded. The datum is one integer for the stretch: lowest floor + 900 mm.
	var lowest: int = 0
	for i in range(n):
		lowest = mini(lowest, (stations[i] as PackedInt32Array)[S_FLOOR_MM])
	water_datum_mm = lowest + 950
	for i in range(n):
		var st: PackedInt32Array = stations[i]
		if st[S_FLOOR_MM] < water_datum_mm:
			st[S_STATE] = FLOODED
			st[S_WATER_MM] = water_datum_mm
			st[S_WET] = 255
		else:
			var above: int = st[S_FLOOR_MM] - water_datum_mm
			var near: int = clampi(255 - above / 4, 0, 255)
			var deepwet: int = (st[S_DEPTH] * 95) / maxi(1, n)
			st[S_WET] = clampi(maxi(near, 25 + deepwet), 0, 255)
			if st[S_WET] > 140 and draw_pct(19, i, 0) < 50:
				st[S_WORKS] = st[S_WORKS] | WK_STANDWATER
		stations[i] = st

# --- rule 4: crosscuts -----------------------------------------------------
# A crosscut is a second drive of the same profile punched through the first at
# right angles (cave NOTES B17). One every 26..40 cells, alternating side,
# 10..20 cells long, one class narrower than its parent, and less worked.
func _build_crosscuts(n: int) -> void:
	var i: int = 18
	var side: int = 1
	var edge_id: int = 1
	while i < n - 10:
		var parent: PackedInt32Array = stations[i]
		parent[S_KIND] = K_JUNCTION
		stations[i] = parent
		junctions.append(i)
		var length: int = draw_range(21, i, 0, 10, 20)
		var ids := PackedInt32Array()
		var wc: int = maxi(WC_CRAWL, parent[S_WIDTH] - 1)
		var yy: int = parent[S_Y]
		var fl: int = parent[S_FLOOR_MM]
		for j in range(1, length + 1):
			yy += side
			fl += draw_range(22, i, j, -8, 8)
			var st := PackedInt32Array()
			st.resize(S_ROW)
			st[S_X] = parent[S_X] + draw_range(23, i, j, -1, 1)
			st[S_Y] = clampi(yy, 3, h_cells - 4)
			st[S_FLOOR_MM] = fl
			st[S_WIDTH] = wc if j < length - 2 else maxi(WC_CRAWL, wc - 1)
			st[S_WORKED] = clampi(parent[S_WORKED] - draw_range(24, i, j, 20, 90), 0, 255)
			st[S_STATE] = DRY
			st[S_WATER_MM] = -1000000
			st[S_WORKS] = 0
			st[S_DEPTH] = parent[S_DEPTH] + j
			st[S_INTEG] = draw_range(25, i, j / 4, 30, 255)
			st[S_KIND] = K_DRIVE
			st[S_EDGE] = edge_id
			st[S_DISCOVERY] = 0
			st[S_FRACTURE] = parent[S_FRACTURE]
			st[S_BEDDING] = parent[S_BEDDING]
			st[S_WET] = clampi(parent[S_WET] - 30, 0, 255)
			stations.append(st)
			ids.append(stations.size() - 1)
		edges.append(ids)
		edge_id += 1
		side = -side
		i += draw_range(26, i, 0, 26, 40)

# --- rule 5: what the works do, and where ----------------------------------
# Every line is a threshold on `worked`, `integ`, `depth` and the 1.2 m module.
# The BROUGHT register (tray, duct, beacon, kit) is deliberately sparse and its
# probability FALLS with depth: the beacon chain thins (ART-DIRECTION 7) and
# the players have not been this far in.
func _assign_works() -> void:
	var deepest: int = 1
	for i in range(stations.size()):
		deepest = maxi(deepest, (stations[i] as PackedInt32Array)[S_DEPTH])
	for i in range(stations.size()):
		var st: PackedInt32Array = stations[i]
		var wk: int = st[S_WORKS]
		var worked: int = st[S_WORKED]
		var d100: int = (st[S_DEPTH] * 100) / deepest
		var along: int = st[S_DEPTH]

		# --- the inherited ------------------------------------------------
		if worked > 90 and st[S_STATE] == DRY and st[S_EDGE] == 0:
			wk |= WK_RAIL
		if worked > 55 and along % 2 == 0:          # sets on the 1.2 m module
			wk |= WK_SETS
			if st[S_INTEG] < 95 and draw_pct(31, i, 0) < 32:
				wk |= WK_SETFAIL
		if worked > 120:
			wk |= WK_BOLTLINE
		if worked > 100:
			wk |= WK_GUTTER
		if worked > 140 and draw_pct(32, i, 0) < 72:
			wk |= WK_PIPE
		if worked > 205:
			wk |= WK_BUS
		if worked > 215 and draw_pct(33, i, 0) < 45:
			wk |= WK_LAUNDER
		if st[S_INTEG] < 115:
			wk |= WK_MESH
		if worked > 70 and draw_pct(34, i, 0) < 24:
			wk |= WK_SPOIL
		if worked > 110 and along % 12 == 3:
			wk |= WK_PLATE
		if st[S_KIND] == K_CHAMBER and worked > 195:
			wk |= WK_PLANT

		# --- the brought --------------------------------------------------
		# A composite tray is clipped over a rusted bracket, so it can only
		# exist where there is already a bolt line to clip it to.
		if (wk & WK_BOLTLINE) != 0 and draw_pct(35, i, 0) < (58 - d100 / 3):
			wk |= WK_TRAY
		if worked > 150 and draw_pct(36, i, 0) < (32 - d100 / 5):
			wk |= WK_DUCT
		var every: int = 13 + (d100 * 27) / 100
		if along % every == 5 or (st[S_KIND] == K_JUNCTION and d100 < 75):
			wk |= WK_BEACON
		if draw_pct(37, i, 0) < (17 - d100 / 8):
			wk |= WK_KIT

		# --- discoveries by depth (DESIGN-PRINCIPLES section 2) ------------
		if d100 > 60 and st[S_KIND] == K_CHAMBER:
			st[S_DISCOVERY] = 1 + (i % 3)

		st[S_WORKS] = wk
		stations[i] = st

# --- rule 6: rasterise -----------------------------------------------------
# Integer disc stamp, phase1's rule: a cell is open if its centre is within
# `radius` cells of a station centre. No floats -- squared integers only.
func _rasterise() -> void:
	for si in range(stations.size()):
		var st: PackedInt32Array = stations[si]
		var r: int = WC_RADIUS_CELLS[st[S_WIDTH]]
		if st[S_KIND] == K_CHAMBER:
			r += 3
		var r2: int = r * r
		for dy in range(-r, r + 1):
			for dx in range(-r, r + 1):
				if dx * dx + dy * dy > r2:
					continue
				var cx: int = st[S_X] + dx
				var cy: int = st[S_Y] + dy
				if cx < 0 or cy < 0 or cx >= w_cells or cy >= h_cells:
					continue
				var k: int = cy * w_cells + cx
				grid_state[k] = st[S_STATE]
				if grid_station[k] < 0:
					grid_station[k] = si

# --- the replay hash -------------------------------------------------------
# FNV-1a over every integer this layer produced, in index order. Two clients
# that agree on this agree on the cave. Dressing never contributes to it.
func content_hash() -> int:
	var h: int = 0x811C9DC5
	for i in range(grid_state.size()):
		h = ((h ^ grid_state[i]) * 0x01000193) & M32
	for si in range(stations.size()):
		var st: PackedInt32Array = stations[si]
		for f in range(S_ROW):
			var v: int = st[f] & M32
			h = ((h ^ (v & 0xFF)) * 0x01000193) & M32
			h = ((h ^ ((v >> 8) & 0xFF)) * 0x01000193) & M32
			h = ((h ^ ((v >> 16) & 0xFF)) * 0x01000193) & M32
			h = ((h ^ ((v >> 24) & 0xFF)) * 0x01000193) & M32
	return h

func open_cells() -> int:
	var n: int = 0
	for i in range(grid_state.size()):
		if grid_state[i] != ROCK:
			n += 1
	return n
