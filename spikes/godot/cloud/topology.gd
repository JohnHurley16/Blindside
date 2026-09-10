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
#
# ---------------------------------------------------------------------------
# VERTICAL, 2026-09-10.  docs/THE-ICE.md section 5.3 option B (levels),
# implemented as recommended: a cell position gains a LEVEL, the raster stays a
# stack of integer arrays one per level, and the thing that joins two levels is
# a PITCH -- its own record, with a climb class on the LINK while the width
# class stays on the CELL (section 5.4 note 3).
#
# Connectivity is now a DIRECTED three-dimensional property. Down is cheap and
# up is not, so "reachable from the collar" and "able to return to it" are two
# separate post-conditions and the second is ALLOWED TO FAIL BY DESIGN
# (THE-ICE section 5.1, 5.3). Both are computed at the bottom of generate().
#
# Everything is still integers, the draw() hash is unchanged, content_hash() is
# unchanged in form, and none of it needs a float to port to Rust.
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

# media ---------------------------------------------------------------------
# THE-ICE section 5.4 note 4: ONE u8-sized enum, on the passage and on the
# pitch rather than per cell, keying the material, the sensor response, the
# acoustic cost and the footing at once. It is the only new axis the ice needs.
const MED_ROCK: int = 0
const MED_WORKED: int = 1
const MED_ICE: int = 2
const MED_ICE_OVER_ROCK: int = 3

# climb classes -------------------------------------------------------------
# On the LINK, never on the cell. THE-ICE section 5.4 note 3.
const CL_WALK: int = 0        # a ramp. down free, up free
const CL_SCRAMBLE: int = 1    # broken ground. down free, up costs and is gated
const CL_PITCH: int = 2       # a controlled vertical descent. down yes, up NO
const CL_VERTICAL: int = 3    # no purchase at all. entering it is a fall

# pitch kinds ---------------------------------------------------------------
const PK_COLLAR: int = 0      # the shaft head. daylight, iron rings in ice
const PK_MOULIN: int = 1      # meltwater conduit. polished, fluted, wet
const PK_WINZE: int = 2       # sunk from one level to the next. worked
const PK_AVEN: int = 3        # a natural hole in the back of a drive
const PK_ORE_PASS: int = 4    # steep, narrow, choked. a fall
const PK_COLLAPSE: int = 5    # a run of broken ground. the only way back up
const PK_CREVASSE: int = 6    # a split in the ice. narrow, and it is neither
const PK_NAME: Array = ["collar", "moulin", "winze", "aven", "orepass", "collapse", "crevasse"]
const CL_NAME: Array = ["walk", "scramble", "pitch", "vertical"]
const MED_NAME: Array = ["rock", "worked", "ice", "ice/rock"]

# pitch flags ---------------------------------------------------------------
const PF_DAYLIGHT: int = 1 << 0    # it reaches the sky
const PF_MAIN: int = 1 << 1        # on the main descent chain
const PF_FIXED: int = 1 << 2       # the ancients left steel in it (a ladderway)
const PF_DOWN: int = 1 << 3        # DERIVED: a machine can descend it
const PF_UP: int = 1 << 4          # DERIVED: a machine can climb it

# works bit flags. "the works" is where the prior industry ran things.
# These ARE topology: the sim needs them (rails are trammable, sets pinch the
# section, the Bus is a hazard, a beacon is a Fix source).
# THE 17-FLAG BITFIELD IS UNCHANGED. THE-ICE section 2.3 lists it among the
# rules that survive verbatim, and it does.
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
const S_FLOOR_MM: int = 2   # floor ELEVATION, mm, signed, measured from
                            #   datum_mm (the valley floor). negative is down.
                            #   THE-ICE section 5.4 note 6: this is the one zero
                            #   the town height and the cave depth share.
const S_WIDTH: int = 3      # width class
const S_WORKED: int = 4     # 0..255, how much the industry touched it
const S_STATE: int = 5      # DRY / FLOODED
const S_WATER_MM: int = 6   # water surface elevation, mm; -1000000 if dry
const S_WORKS: int = 7      # works bitfield
const S_DEPTH: int = 8      # BFS graph distance from the collar, in cells
const S_INTEG: int = 9      # structural integrity 0..255 (low = bad ground)
const S_WET: int = 10       # 0..255 surface wetness (the `wet` scalar)
const S_FRACTURE: int = 11  # 3..14, the `fracture` scalar (voronoi frequency)
const S_BEDDING: int = 12   # 4..35, the `bedding` scalar x10
const S_KIND: int = 13      # K_*
const S_EDGE: int = 14      # which edge this station belongs to
const S_DISCOVERY: int = 15 # 0 none, else a discovery id (blocks by depth)
# --- NEW, 2026-09-10 -------------------------------------------------------
const S_LEVEL: int = 16     # 0..levels-1. 0 is the shallowest
const S_MEDIUM: int = 17    # MED_*
const S_CEIL_MM: int = 18   # ceiling ELEVATION, mm. NEW: it fixes the invariant
                            #   PROCEDURAL-AND-GODOT section 1.6 asserts against
                            #   a field Passage did not have (THE-ICE 2.10)
const S_PITCH_HEAD: int = 19  # index into pitches whose TOP is here, else -1
const S_PITCH_FOOT: int = 20  # index into pitches whose BOTTOM is here, else -1
const S_ROW: int = 21

# pitch row layout ----------------------------------------------------------
const P_FROM_ST: int = 0    # station at the top, or -1 if that is the sky
const P_TO_ST: int = 1      # station at the bottom
const P_X: int = 2          # top cell x
const P_Y: int = 3          # top cell y
const P_TO_X: int = 4       # bottom cell x
const P_TO_Y: int = 5       # bottom cell y
const P_TOP_MM: int = 6     # elevation of the lip
const P_BOT_MM: int = 7     # elevation of the floor it lands on
const P_DROP_MM: int = 8    # positive is downward. TOP - BOT
const P_BORE_MM: int = 9    # clear diameter. the width class of a vertical hole
const P_CLIMB: int = 10     # CL_*
const P_KIND: int = 11      # PK_*
const P_MEDIUM: int = 12    # MED_* at the TOP; a long pitch changes with depth
const P_WATER_MM: int = 13  # water surface inside the pitch, or -1000000
const P_FLOW: int = 14      # 0..255 meltwater running down it. an acoustic object
const P_FLAGS: int = 15     # PF_*
const P_FROM_LEVEL: int = 16
const P_TO_LEVEL: int = 17
const P_ROW: int = 18

# link row layout -----------------------------------------------------------
# The graph. Passages are bidirectional; a pitch is directed and carries its
# own permission bits, which is what makes connectivity a directed property.
const L_A: int = 0
const L_B: int = 1
const L_COST: int = 2       # cells
const L_PITCH: int = 3      # -1 for a passage, else the pitch index
const L_ROW: int = 4

# --- the depth stack, in millimetres of elevation --------------------------
# GUESS, and it is the biggest one in this file. THE-ICE section 5.2 gives the
# bands as 0..-30 m ice, -30..-80 karst, -80..-250 the workings, -250+ past the
# sump, and says "the ratios matter more than the numbers". This spike
# COMPRESSES that section by about 2.2x so the whole of it renders and so a
# chamber one level down is inside the lamp's reach. The ratios are kept.
const BAND_ICE_BASE_MM: int = -15000      # 0 .. -15 m   band 0, the fill
const BAND_KARST_BASE_MM: int = -38000    # -15 .. -38   band 1, the karst
const BAND_WORK_BASE_MM: int = -72000     # -38 .. -72   band 2, the workings
                                          # below -72    band 3, the deep

# The four level datums, elevation in mm. Four is the top of THE-ICE section
# 5.3 option B's "two to four levels".
const LEVEL_DATUM_MM: Array = [-11000, -26000, -49000, -83000]
# Deeper levels are shorter: the frontier narrows. Per mille of the stretch.
# Level 0 is SHORT and levels 2 and 3 are long, so that most of the cave is
# the mine (THE-ICE 5.2: "the ice band is thin, the karst is the transition,
# and most of the cave is the mine"). Truncated automatically where a level
# would run off the grid.
const LEVEL_LEN_PM: Array = [760, 900, 1000, 700]
# The main descent leaves each level near its FAR end, so you have to cross a
# level to find the way down. Per mille along that level's drive.
const LEVEL_HEAD_PM: Array = [880, 880, 850, 0]

# THE MELT FRONT. THE-ICE section 5.4 note 5: one i32 that makes section 4's
# ruling generative. At or above it the water has arrived -- wet, dripping, and
# the ancient machinery running. Below it the mine is dry, cold and silent and
# has not been touched since before the ice.
const MELT_DATUM_MM: int = -60000

var cave_seed: int = 0
var w_cells: int = 0
var h_cells: int = 0
var levels: int = 1
var datum_mm: int = 0                    # the valley floor. the ONE zero.
var melt_mm: int = 0                     # the melt front elevation
var grid_state: PackedByteArray          # levels*w*h, ROCK/DRY/FLOODED
var grid_station: PackedInt32Array       # levels*w*h, owning station or -1
var stations: Array = []                 # Array[PackedInt32Array] of S_ROW
var edges: Array = []                    # Array[PackedInt32Array] station ids
var pitches: Array = []                  # Array[PackedInt32Array] of P_ROW
var links: PackedInt32Array              # rows of L_ROW
var chambers: PackedInt32Array           # rows of CH_ROW
const CH_X: int = 0
const CH_Y: int = 1
const CH_R: int = 2
const CH_PLANT: int = 3
const CH_SID: int = 4
const CH_LEVEL: int = 5
const CH_RUNNING: int = 6      # THE-ICE 5.4: AncientSite.running, from melt_mm
const CH_ROW: int = 7
var junctions: PackedInt32Array           # station ids
var level_main_edge: PackedInt32Array     # edge index of each level's drive
var level_head_st: PackedInt32Array       # station the main descent leaves from
var level_foot_st: PackedInt32Array       # station the main descent lands on
var level_water_mm: PackedInt32Array      # water surface per level, or -1000000
var water_datum_mm: int = 0               # the deepest WET level's surface
var collar_st: int = 0                    # the station the collar lands on
# post-conditions, computed, not decided ------------------------------------
var reach_down: int = 0        # open cells reachable from the collar
var reach_up: int = 0          # open cells that can get BACK to the collar
var ceil_violations: int = 0
var st_down: PackedByteArray
var st_up: PackedByteArray

# ---------------------------------------------------------------------------
# Stateless counter-based RNG. draw(purpose, a, b) -> [0, 2^32).
# The order of calls cannot affect any result. Ports to Rust verbatim.
# UNCHANGED.
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
# pure integer classification helpers
# ---------------------------------------------------------------------------
func band_of(elev_mm: int) -> int:
	if elev_mm > BAND_ICE_BASE_MM:
		return 0
	if elev_mm > BAND_KARST_BASE_MM:
		return 1
	if elev_mm > BAND_WORK_BASE_MM:
		return 2
	return 3

# THE-ICE section 5.4 note 1: depth in millimetres is ADDITIONAL to the BFS
# band, never a replacement for it. This is the derivation.
func depth_mm_of(st: PackedInt32Array) -> int:
	return datum_mm - st[S_FLOOR_MM]

func idx3(level: int, cx: int, cy: int) -> int:
	return (level * h_cells + cy) * w_cells + cx

func pitch(i: int) -> PackedInt32Array:
	return pitches[i]

# ---------------------------------------------------------------------------
func generate(p_seed: int, length_cells: int, p_levels: int = 1) -> void:
	cave_seed = p_seed & M32
	levels = clampi(p_levels, 1, 4)
	w_cells = length_cells + 14
	h_cells = 76
	datum_mm = 0
	melt_mm = MELT_DATUM_MM
	grid_state = PackedByteArray()
	grid_state.resize(levels * w_cells * h_cells)
	grid_station = PackedInt32Array()
	grid_station.resize(levels * w_cells * h_cells)
	for i in range(grid_state.size()):
		grid_state[i] = ROCK
		grid_station[i] = -1
	stations = []
	edges = []
	pitches = []
	links = PackedInt32Array()
	chambers = PackedInt32Array()
	junctions = PackedInt32Array()
	level_main_edge = PackedInt32Array()
	level_head_st = PackedInt32Array()
	level_foot_st = PackedInt32Array()
	level_water_mm = PackedInt32Array()
	collar_st = 0

	if levels == 1:
		# --- THE FROZEN FLAT PATH ------------------------------------------
		# Rules R1-R4 exactly as they were before 2026-09-10, so the cave the
		# trailer sequences in shots/cinema/seq were shot against reproduces
		# cell for cell. It is a REGRESSION CONTROL, not a feature, and it
		# should be deleted the day the trailer is re-shot.
		melt_mm = -1000000000        # everything is above the front: all wet
		_legacy_drive(length_cells)
		_legacy_crosscuts(length_cells)
		level_main_edge.append(0)
		level_head_st.append(0)
		level_foot_st.append(0)
		level_water_mm.append(water_datum_mm)
	else:
		_build_levels(length_cells)
		_build_pitches()
		_assign_media()
		_water()

	_ceilings()
	_depth_bfs()
	_assign_works()
	_rasterise()
	_connectivity()

# ===========================================================================
# THE FLAT PATH -- frozen. Do not edit; edit the vertical path instead.
# ===========================================================================
func _legacy_drive(n: int) -> void:
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
		floor_mm = -(i * 2)
		var sump_c: int = (n * 58) / 100
		var sump_half: int = maxi(6, n / 11)
		var off: int = absi(i - sump_c)
		if off < sump_half:
			floor_mm -= ((sump_half - off) * 1500) / sump_half
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
		var blk: int = i / 9
		st[S_FRACTURE] = draw_range(15, blk, 0, 3, 14)
		st[S_BEDDING] = draw_range(16, blk, 1, 4, 35)
		st[S_WET] = 0
		st[S_LEVEL] = 0
		st[S_MEDIUM] = MED_WORKED if st[S_WORKED] > 128 else MED_ROCK
		st[S_CEIL_MM] = 0
		st[S_PITCH_HEAD] = -1
		st[S_PITCH_FOOT] = -1
		stations.append(st)
		ids.append(stations.size() - 1)
		if i > 0:
			_link(stations.size() - 2, stations.size() - 1, 1, -1)
	edges.append(ids)

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
		_chamber_row(st[S_X], st[S_Y], r, 1 if ci == 3 else 0, si, 0, 1)

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

func _legacy_crosscuts(n: int) -> void:
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
			st[S_LEVEL] = 0
			st[S_MEDIUM] = MED_WORKED if st[S_WORKED] > 128 else MED_ROCK
			st[S_CEIL_MM] = 0
			st[S_PITCH_HEAD] = -1
			st[S_PITCH_FOOT] = -1
			stations.append(st)
			ids.append(stations.size() - 1)
			_link(i if j == 1 else stations.size() - 2, stations.size() - 1, 1, -1)
		edges.append(ids)
		edge_id += 1
		side = -side
		i += draw_range(26, i, 0, 26, 40)

# ===========================================================================
# THE VERTICAL PATH
# ===========================================================================
func _link(a: int, b: int, cost: int, pi: int) -> void:
	links.append(a)
	links.append(b)
	links.append(cost)
	links.append(pi)

func _chamber_row(cx: int, cy: int, r: int, plant: int, sid: int, lvl: int, running: int) -> void:
	chambers.append(cx)
	chambers.append(cy)
	chambers.append(r)
	chambers.append(plant)
	chambers.append(sid)
	chambers.append(lvl)
	chambers.append(running)

# --- rule V1: the levels ---------------------------------------------------
# Level 0 runs +X from the collar. Every level below it runs BACK the other
# way from the foot of the descent, which is a switchback mine, keeps every
# level on the same grid, and is what puts one level directly under another.
func _build_levels(n: int) -> void:
	var sx: int = 7
	var sy: int = h_cells / 2
	var dir: int = 1
	for L in range(levels):
		var ln: int = maxi(24, (n * int(LEVEL_LEN_PM[L])) / 1000)
		if dir > 0:
			ln = mini(ln, w_cells - 5 - sx)
		else:
			ln = mini(ln, sx - 4)
		var e: int = _build_level_drive(L, ln, sx, sy, dir)
		level_main_edge.append(e)
		var ids: PackedInt32Array = edges[e]
		level_foot_st.append(ids[0])
		_build_level_crosscuts(L, e)
		if L + 1 < levels:
			var hi: int = clampi((ids.size() * int(LEVEL_HEAD_PM[L])) / 1000, 4, ids.size() - 2)
			var hs: PackedInt32Array = stations[ids[hi]]
			level_head_st.append(ids[hi])
			sx = hs[S_X]
			sy = hs[S_Y]
			dir = -dir
		else:
			level_head_st.append(-1)

# --- rule V2: one level's drive --------------------------------------------
# The spine rule of the flat cave, re-datumed. Y still wanders by a bounded
# integer walk. The floor still falls, and still has ONE bowl -- but only if
# the level is above the melt front, because below the front nothing has run
# for fourteen hundred years and there is nothing to pond.
func _build_level_drive(L: int, n: int, sx: int, sy: int, dir: int) -> int:
	var base: int = int(LEVEL_DATUM_MM[L])
	var bnd: int = band_of(base)
	var wet_level: bool = base > melt_mm
	var ids := PackedInt32Array()
	var y: int = sy
	var wc: int = WC_PASSAGE
	var wc_hold: int = 0
	var sump_c: int = (n * draw_range(40, L, 0, 42, 72)) / 100
	var sump_half: int = maxi(6, n / 11)
	for i in range(n):
		if i % 4 == 0 and i > 0:
			var d: int = draw_range(41, i, L, -1, 1)
			if y > h_cells / 2 + 9:
				d = -1
			elif y < h_cells / 2 - 9:
				d = 1
			y += d
		# floor: a gentle fall along the drive plus one bowl
		var floor_mm: int = base - (i * 2)
		if wet_level:
			var off: int = absi(i - sump_c)
			if off < sump_half:
				floor_mm -= ((sump_half - off) * 1500) / sump_half
		if wc_hold <= 0:
			wc_hold = draw_range(42, i, L, 6, 22)
			var roll: int = draw_pct(43, i, L)
			var along: int = (i * 100) / maxi(1, n)
			if bnd == 0:
				# a meltwater conduit: round, and it pinches
				wc = WC_CRAWL if roll < 26 else (WC_NARROW if roll < 68 else WC_PASSAGE)
			elif bnd == 1:
				wc = WC_NARROW if roll < 30 else (WC_PASSAGE if roll < 90 else WC_HALL)
			else:
				wc = WC_PASSAGE if roll < (70 - along / 4) else WC_HALL
		wc_hold -= 1
		var st := PackedInt32Array()
		st.resize(S_ROW)
		st[S_X] = sx + dir * i
		st[S_Y] = y
		st[S_FLOOR_MM] = floor_mm
		st[S_WIDTH] = wc
		# --- rule V3: worked is now driven by ELEVATION first ---------------
		# "going deeper becomes literal" (DESIGN-PRINCIPLES section 10). The
		# depth band sets the register; the along-drive ramp only shades it.
		var lo: int = 0
		var hi2: int = 0
		if bnd == 0:
			lo = 0
			hi2 = 28
		elif bnd == 1:
			lo = 48
			hi2 = 140
		elif bnd == 2:
			lo = 165
			hi2 = 250
		else:
			lo = 200
			hi2 = 255
		var p: int = (i * 1000) / maxi(1, n)
		var wk: int = lo + ((hi2 - lo) * p) / 1000
		wk += draw_range(44, i / 7, L, -14, 14)
		st[S_WORKED] = clampi(wk, 0, 255)
		if st[S_WORKED] > 128:
			st[S_WIDTH] = maxi(st[S_WIDTH], WC_PASSAGE)
		st[S_STATE] = DRY
		st[S_WATER_MM] = -1000000
		st[S_WORKS] = 0
		st[S_DEPTH] = 0
		st[S_INTEG] = draw_range(45, i / 5, L, 40, 255)
		st[S_KIND] = K_DRIVE
		st[S_EDGE] = edges.size()
		st[S_DISCOVERY] = 0
		var blk: int = i / 9
		st[S_FRACTURE] = draw_range(46, blk, L, 3, 14)
		st[S_BEDDING] = draw_range(47, blk, L + 1, 4, 35)
		st[S_WET] = 0
		st[S_LEVEL] = L
		st[S_MEDIUM] = MED_ROCK
		st[S_CEIL_MM] = 0
		st[S_PITCH_HEAD] = -1
		st[S_PITCH_FOOT] = -1
		stations.append(st)
		ids.append(stations.size() - 1)
		if i > 0:
			_link(stations.size() - 2, stations.size() - 1, 1, -1)
	edges.append(ids)
	var e: int = edges.size() - 1

	# --- rule V4: chambers, three per level plus the plant on the deepest ---
	var cfrac := PackedInt32Array([20, 48, 74])
	for ci in range(cfrac.size()):
		var si: int = clampi((n * cfrac[ci]) / 100 + draw_range(48, ci, L, -3, 3), 2, n - 3)
		_make_chamber(ids, si, L, draw_range(49, ci, L, 5, 9),
			1 if (ci == 2 and L >= 2) else 0)
	return e

func _make_chamber(ids: PackedInt32Array, si: int, L: int, r: int, plant: int) -> void:
	var n: int = ids.size()
	si = clampi(si, 1, n - 2)
	var st: PackedInt32Array = stations[ids[si]]
	if st[S_KIND] == K_CHAMBER:
		return
	st[S_WIDTH] = WC_HALL
	st[S_KIND] = K_CHAMBER
	stations[ids[si]] = st
	for k in range(1, 4):
		for s2 in [si - k, si + k]:
			if s2 >= 0 and s2 < n:
				var q: PackedInt32Array = stations[ids[s2]]
				q[S_WIDTH] = maxi(q[S_WIDTH], WC_HALL if k <= 2 else WC_PASSAGE)
				stations[ids[s2]] = q
	# THE-ICE section 5.4: AncientSite.running. Above the melt front the tank
	# fills and the hammer goes back to work; below it, it has not fired.
	var running: int = 1 if st[S_FLOOR_MM] > melt_mm else 0
	_chamber_row(st[S_X], st[S_Y], r, plant, ids[si], L, running)

# --- rule V5: crosscuts, per level -----------------------------------------
func _build_level_crosscuts(L: int, e: int) -> void:
	var ids: PackedInt32Array = edges[e]
	var n: int = ids.size()
	var i: int = 18
	var side: int = 1
	while i < n - 10:
		var psid: int = ids[i]
		var parent: PackedInt32Array = stations[psid]
		parent[S_KIND] = K_JUNCTION
		stations[psid] = parent
		junctions.append(psid)
		var length: int = draw_range(51, i, L, 10, 20)
		var cids := PackedInt32Array()
		var wc: int = maxi(WC_CRAWL, parent[S_WIDTH] - 1)
		var yy: int = parent[S_Y]
		var fl: int = parent[S_FLOOR_MM]
		for j in range(1, length + 1):
			yy += side
			fl += draw_range(52, i, j + L * 97, -8, 8)
			var st := PackedInt32Array()
			st.resize(S_ROW)
			st[S_X] = parent[S_X] + draw_range(53, i, j + L * 31, -1, 1)
			st[S_Y] = clampi(yy, 3, h_cells - 4)
			st[S_FLOOR_MM] = fl
			st[S_WIDTH] = wc if j < length - 2 else maxi(WC_CRAWL, wc - 1)
			st[S_WORKED] = clampi(parent[S_WORKED] - draw_range(54, i, j + L * 17, 20, 90), 0, 255)
			st[S_STATE] = DRY
			st[S_WATER_MM] = -1000000
			st[S_WORKS] = 0
			st[S_DEPTH] = 0
			st[S_INTEG] = draw_range(55, i, j / 4 + L * 13, 30, 255)
			st[S_KIND] = K_DRIVE
			st[S_EDGE] = edges.size()
			st[S_DISCOVERY] = 0
			st[S_FRACTURE] = parent[S_FRACTURE]
			st[S_BEDDING] = parent[S_BEDDING]
			st[S_WET] = 0
			st[S_LEVEL] = L
			st[S_MEDIUM] = MED_ROCK
			st[S_CEIL_MM] = 0
			st[S_PITCH_HEAD] = -1
			st[S_PITCH_FOOT] = -1
			stations.append(st)
			cids.append(stations.size() - 1)
			_link(psid if j == 1 else stations.size() - 2, stations.size() - 1, 1, -1)
		edges.append(cids)
		side = -side
		i += draw_range(56, i, L, 26, 40)

# ===========================================================================
# rule V6: PITCHES -- the things that connect levels
# ===========================================================================
# The climb class is DERIVED from the drop, the bore, the medium and whether
# the ancients left steel in it. It is on the LINK, and it is what makes down
# cheap and up expensive.
#
#   WALK      a ramp                          down free   up free
#   SCRAMBLE  broken ground, a rubble cone    down free   up costs, gated
#   PITCH     a controlled vertical descent   down yes    up NO
#   VERTICAL  no purchase anywhere            entering it is a FALL
func _climb_for(kind: int, drop_mm: int, bore_mm: int, medium: int, fixed: bool) -> int:
	var c: int = CL_VERTICAL
	if drop_mm <= 400:
		c = CL_WALK
	elif drop_mm <= 2200 and medium != MED_ICE:
		c = CL_SCRAMBLE
	elif fixed and drop_mm <= 14000:
		c = CL_SCRAMBLE
	elif kind == PK_COLLAPSE and drop_mm <= 30000:
		c = CL_SCRAMBLE
	elif drop_mm <= 45000 and bore_mm >= 1100:
		c = CL_PITCH
	# polished ice gives a leg nothing to push against. THE-ICE section 6.4.
	if medium == MED_ICE and c == CL_SCRAMBLE:
		c = CL_PITCH
	# a bore narrower than a chassis is not a route in either direction
	if bore_mm < 900:
		c = CL_VERTICAL
	return c

func _add_pitch(up_sid: int, dn_sid: int, kind: int, bore: int, flags: int, flow: int) -> int:
	var us: PackedInt32Array = stations[up_sid]
	var ds: PackedInt32Array = stations[dn_sid]
	if us[S_PITCH_HEAD] >= 0 or ds[S_PITCH_FOOT] >= 0:
		return -1
	var top: int = us[S_FLOOR_MM]
	var bot: int = ds[S_FLOOR_MM]
	if top - bot < 300:
		return -1
	var med: int = MED_ICE
	var bnd: int = band_of(top)
	if kind == PK_COLLAR:
		med = MED_ICE_OVER_ROCK          # ice, with the ancients' rings in it
	elif kind == PK_WINZE or kind == PK_ORE_PASS:
		med = MED_WORKED
	elif kind == PK_CREVASSE:
		med = MED_ICE
	elif kind == PK_COLLAPSE:
		# a run of broken ground. What fell is ROCK, even where it fell
		# through ice, so this is the one pitch the polish demotion below
		# must not touch -- and that is why it is the way back up.
		med = MED_ICE_OVER_ROCK if bnd <= 1 else MED_ROCK
	elif kind == PK_MOULIN:
		med = MED_ICE if bnd == 0 else MED_ICE_OVER_ROCK
	elif bnd == 0:
		med = MED_ICE
	elif bnd == 1:
		med = MED_ICE_OVER_ROCK
	else:
		med = MED_ROCK
	var fixed: bool = (flags & PF_FIXED) != 0
	var climb: int = _climb_for(kind, top - bot, bore, med, fixed)
	if climb <= CL_PITCH and bore >= 900:
		flags |= PF_DOWN
	if climb <= CL_SCRAMBLE and bore >= 900:
		flags |= PF_UP
	var row := PackedInt32Array()
	row.resize(P_ROW)
	row[P_FROM_ST] = up_sid
	row[P_TO_ST] = dn_sid
	row[P_X] = us[S_X]
	row[P_Y] = us[S_Y]
	row[P_TO_X] = ds[S_X]
	row[P_TO_Y] = ds[S_Y]
	row[P_TOP_MM] = top
	row[P_BOT_MM] = bot
	row[P_DROP_MM] = top - bot
	row[P_BORE_MM] = bore
	row[P_CLIMB] = climb
	row[P_KIND] = kind
	row[P_MEDIUM] = med
	# a pitch can be a waterfall, and that is an acoustic object. Below the
	# melt front nothing runs.
	row[P_FLOW] = flow if top > melt_mm else 0
	row[P_WATER_MM] = -1000000
	row[P_FLAGS] = flags
	row[P_FROM_LEVEL] = us[S_LEVEL]
	row[P_TO_LEVEL] = ds[S_LEVEL]
	pitches.append(row)
	var pi: int = pitches.size() - 1
	us[S_PITCH_HEAD] = pi
	stations[up_sid] = us
	ds = stations[dn_sid]
	ds[S_PITCH_FOOT] = pi
	stations[dn_sid] = ds
	# the two ends must be chambers: a shaft is sunk at a station, the floor
	# above it gets a hole in it and the back below it gets one too.
	_force_chamber(up_sid)
	_force_chamber(dn_sid)
	_link(up_sid, dn_sid, maxi(1, (top - bot) / CELL_MM), pi)
	return pi

func _force_chamber(sid: int) -> void:
	var st: PackedInt32Array = stations[sid]
	if st[S_KIND] == K_CHAMBER:
		return
	st[S_KIND] = K_CHAMBER
	st[S_WIDTH] = WC_HALL
	stations[sid] = st
	_chamber_row(st[S_X], st[S_Y], draw_range(60, sid, 0, 5, 8), 0, sid,
		st[S_LEVEL], 1 if st[S_FLOOR_MM] > melt_mm else 0)

# Find a station on the UPPER level lying as nearly as possible above a chosen
# station on the LOWER level. Deterministic scan in index order; no maps.
func _pair_for(Lup: int, Ldn: int, frac_pm: int, purpose: int) -> PackedInt32Array:
	var dids: PackedInt32Array = edges[level_main_edge[Ldn]]
	var uids: PackedInt32Array = edges[level_main_edge[Lup]]
	var best := PackedInt32Array([-1, -1, 99999])
	for k in range(5):
		var f: int = clampi(frac_pm + (k - 2) * 55, 60, 940)
		var di: int = clampi((dids.size() * f) / 1000, 2, dids.size() - 3)
		var ds: PackedInt32Array = stations[dids[di]]
		for j in range(uids.size()):
			var us: PackedInt32Array = stations[uids[j]]
			var d: int = absi(us[S_X] - ds[S_X]) + absi(us[S_Y] - ds[S_Y])
			if d < best[2]:
				best[0] = uids[j]
				best[1] = dids[di]
				best[2] = d
		if best[2] <= 2:
			break
	if best[2] > 5:
		return PackedInt32Array([-1, -1, best[2]])
	return best

func _build_pitches() -> void:
	# --- the collar. The player goes down the way the water went down, and
	# the water went down the way the ancients went down (THE-ICE 5.2).
	var l0: PackedInt32Array = edges[level_main_edge[0]]
	collar_st = l0[0]
	var cs: PackedInt32Array = stations[collar_st]
	var crow := PackedInt32Array()
	crow.resize(P_ROW)
	crow[P_FROM_ST] = -1
	crow[P_TO_ST] = collar_st
	crow[P_X] = cs[S_X]
	crow[P_Y] = cs[S_Y]
	crow[P_TO_X] = cs[S_X]
	crow[P_TO_Y] = cs[S_Y]
	crow[P_TOP_MM] = datum_mm
	crow[P_BOT_MM] = cs[S_FLOOR_MM]
	crow[P_DROP_MM] = datum_mm - cs[S_FLOOR_MM]
	crow[P_BORE_MM] = 2600
	crow[P_KIND] = PK_COLLAR
	crow[P_MEDIUM] = MED_ICE_OVER_ROCK
	crow[P_FLOW] = 55
	crow[P_WATER_MM] = -1000000
	crow[P_CLIMB] = _climb_for(PK_COLLAR, crow[P_DROP_MM], 2600, MED_ICE_OVER_ROCK, true)
	crow[P_FLAGS] = PF_DAYLIGHT | PF_MAIN | PF_FIXED | PF_DOWN | PF_UP
	crow[P_FROM_LEVEL] = 0
	crow[P_TO_LEVEL] = 0
	pitches.append(crow)
	cs[S_PITCH_FOOT] = 0
	stations[collar_st] = cs
	_force_chamber(collar_st)

	# --- the main descent chain. One pitch per level boundary, from the far
	# end of a level to the head of the next.
	for L in range(levels - 1):
		var up: int = level_head_st[L]
		var dn: int = level_foot_st[L + 1]
		if up < 0 or dn < 0:
			continue
		var us: PackedInt32Array = stations[up]
		var bnd: int = band_of(us[S_FLOOR_MM])
		var kind: int = PK_MOULIN if bnd == 0 else PK_WINZE
		var bore: int = 2200 if kind == PK_MOULIN else draw_range(61, L, 0, 1600, 2000)
		var fl: int = PF_MAIN
		if kind == PK_WINZE:
			fl |= PF_FIXED
		_add_pitch(up, dn, kind, bore, fl, 140 if kind == PK_MOULIN else 60)

	# --- the way back up. One run of broken ground per level pair, EXCEPT
	# out of the deepest level. That is the commitment: the bottom of the
	# cave is the one place a machine cannot walk out of.
	for L in range(levels - 2):
		var pr: PackedInt32Array = _pair_for(L, L + 1, 330 + L * 120, 62)
		if pr[0] >= 0:
			_add_pitch(pr[0], pr[1], PK_COLLAPSE, draw_range(63, L, 0, 2800, 4200),
				0, 0)

	# --- an ore pass: worked, steep, choked. A fall, not a route.
	if levels >= 3:
		var pr2: PackedInt32Array = _pair_for(1, 2, 620, 64)
		if pr2[0] >= 0:
			_add_pitch(pr2[0], pr2[1], PK_ORE_PASS, draw_range(65, 0, 0, 950, 1080),
				PF_FIXED, 0)

	# --- an aven: natural, opened by water working upward along a joint.
	if levels >= 4:
		var pr3: PackedInt32Array = _pair_for(2, 3, 470, 66)
		if pr3[0] >= 0:
			_add_pitch(pr3[0], pr3[1], PK_AVEN, draw_range(67, 0, 0, 1300, 1800), 0, 0)

	# --- a crevasse in the ice. Narrow, polished, and it is NEITHER: a
	# machine that walks into it does not come out and did not choose to.
	if levels >= 2:
		var pr4: PackedInt32Array = _pair_for(0, 1, 175, 68)
		if pr4[0] >= 0:
			_add_pitch(pr4[0], pr4[1], PK_CREVASSE, draw_range(69, 0, 0, 620, 860),
				0, 35)

# ===========================================================================
# rule V7: the three media, interleaved by depth
# ===========================================================================
# ART-DIRECTION section 3.7 / THE-ICE section 5.2. The interleave IS the design:
# ice above, rock below, and the ancients' workings cutting through both. And
# THE-ICE's second structural claim -- "the ice is a FILL, not a LAYER" -- is
# the reason band 1 is not "no ice": it is ice where the drafts and the
# drainage put it.
func _assign_media() -> void:
	for i in range(stations.size()):
		var st: PackedInt32Array = stations[i]
		var elev: int = st[S_FLOOR_MM]
		var bnd: int = band_of(elev)
		var worked: int = st[S_WORKED]
		var med: int = MED_ROCK
		if bnd == 0:
			# the fill, and the dead ice in it. The only worked thing this
			# high is the collar itself.
			med = MED_ICE
			if worked > 90:
				med = MED_ICE_OVER_ROCK
		elif bnd == 1:
			# the karst. Rock, with ice where the water stood or the draft
			# blows: near a pitch, in the low ground, on a wet floor.
			med = MED_WORKED if worked > 128 else MED_ROCK
			var icy: int = draw_pct(70, i, 0)
			var near_pitch: bool = st[S_PITCH_HEAD] >= 0 or st[S_PITCH_FOOT] >= 0
			# more ice the nearer the ice base: the fill pushed DOWN into the
			# karst from above and ran out of reach on the way
			var lowish: int = clampi((BAND_ICE_BASE_MM - elev) / 900, 0, 44)
			if near_pitch or icy < (48 - lowish):
				med = MED_ICE_OVER_ROCK
		else:
			# the workings, and below them the deep. No ice: below the
			# freezing front, and always was.
			med = MED_WORKED if worked > 128 else MED_ROCK
		st[S_MEDIUM] = med
		stations[i] = st

# ===========================================================================
# rule V8: water, per level, and the melt front
# ===========================================================================
# G10 ("flooding rises monotonically with depth") stops being a tested
# post-condition and becomes a consequence: water finds the lowest place on
# whatever floor it is standing on. THE-ICE section 5.5.
#
# The melt front is an ELEVATION. At or above it the water has arrived. Below
# it the mine is dry, silent, and older -- which is the world object THE-ICE
# section 4.2 item 4 calls the strongest thing the ruling buys.
func _water() -> void:
	level_water_mm.resize(levels)
	for L in range(levels):
		level_water_mm[L] = -1000000
	for L in range(levels):
		if int(LEVEL_DATUM_MM[L]) <= melt_mm:
			continue
		var lowest: int = 1000000
		for i in range(stations.size()):
			var st: PackedInt32Array = stations[i]
			if st[S_LEVEL] == L:
				lowest = mini(lowest, st[S_FLOOR_MM])
		if lowest < 1000000:
			level_water_mm[L] = lowest + 950
	water_datum_mm = -1000000
	for L in range(levels):
		if level_water_mm[L] > -1000000:
			water_datum_mm = level_water_mm[L] if water_datum_mm == -1000000 else mini(water_datum_mm, level_water_mm[L])

	for i in range(stations.size()):
		var st: PackedInt32Array = stations[i]
		var L2: int = st[S_LEVEL]
		var wsurf: int = level_water_mm[L2]
		var dry_level: bool = st[S_FLOOR_MM] <= melt_mm
		if dry_level:
			# past the melt front. No drip, no pond, no wet rock -- and the
			# only marker on it is that everything stops. ART-DIRECTION 3.7.
			st[S_STATE] = DRY
			st[S_WATER_MM] = -1000000
			st[S_WET] = draw_range(71, i, 0, 4, 26)
		elif wsurf > -1000000 and st[S_FLOOR_MM] < wsurf:
			st[S_STATE] = FLOODED
			st[S_WATER_MM] = wsurf
			st[S_WET] = 255
		else:
			st[S_STATE] = DRY
			st[S_WATER_MM] = -1000000
			var above: int = st[S_FLOOR_MM] - (wsurf if wsurf > -1000000 else st[S_FLOOR_MM])
			var near: int = clampi(255 - above / 4, 0, 255)
			# the shallow band is wet because it is melting, not because it
			# is deep. Two different reasons, one field.
			var bnd: int = band_of(st[S_FLOOR_MM])
			var base_wet: int = 0
			if bnd == 0:
				base_wet = 150
			elif bnd == 1:
				base_wet = 110
			elif bnd == 2:
				base_wet = 70
			else:
				base_wet = 30
			st[S_WET] = clampi(maxi(near, base_wet + draw_range(72, i, 0, -25, 25)), 0, 255)
			if st[S_WET] > 140 and draw_pct(73, i, 0) < 50:
				st[S_WORKS] = st[S_WORKS] | WK_STANDWATER
		stations[i] = st

	# a pitch above the front carries the water down it
	for pi in range(pitches.size()):
		var pr: PackedInt32Array = pitches[pi]
		var dn: int = pr[P_TO_ST]
		if dn >= 0:
			var ds: PackedInt32Array = stations[dn]
			if ds[S_STATE] == FLOODED:
				pr[P_WATER_MM] = ds[S_WATER_MM]
		pitches[pi] = pr

# ===========================================================================
# rule V9: what the works do, and where. UNCHANGED except that "no ancients
# above the karst" is now a real rule, and the descent shaft is its exception.
# ===========================================================================
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
		var dry_side: bool = st[S_FLOOR_MM] <= melt_mm

		# --- the inherited ------------------------------------------------
		# The old rule was `st[S_EDGE] == 0` -- rails on the main drive only.
		# With levels there are several main drives, so it becomes "any level's
		# main drive". When levels == 1 the second clause is dead and the rule
		# is the old rule, byte for byte.
		var on_main: bool = st[S_EDGE] == 0
		if levels > 1 and not on_main:
			for L2 in range(level_main_edge.size()):
				if level_main_edge[L2] == st[S_EDGE]:
					on_main = true
					break
		if worked > 90 and st[S_STATE] == DRY and on_main:
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
		# ground support is the ancients'. There is none in dead ice, and the
		# `levels == 1` clause keeps the flat path's rule exactly as it was.
		if st[S_INTEG] < 115 and (levels == 1 or worked > 40):
			wk |= WK_MESH
		if worked > 70 and draw_pct(34, i, 0) < 24:
			wk |= WK_SPOIL
		if worked > 110 and along % 12 == 3:
			wk |= WK_PLATE
		if st[S_KIND] == K_CHAMBER and worked > 195:
			wk |= WK_PLANT

		# --- the brought --------------------------------------------------
		if (wk & WK_BOLTLINE) != 0 and draw_pct(35, i, 0) < (58 - d100 / 3):
			wk |= WK_TRAY
		if worked > 150 and draw_pct(36, i, 0) < (32 - d100 / 5):
			wk |= WK_DUCT
		var every: int = 13 + (d100 * 27) / 100
		if along % every == 5 or (st[S_KIND] == K_JUNCTION and d100 < 75):
			wk |= WK_BEACON
		if draw_pct(37, i, 0) < (17 - d100 / 8):
			wk |= WK_KIT

		# --- discoveries, by DEPTH, which is now literal -------------------
		if levels == 1:
			if d100 > 60 and st[S_KIND] == K_CHAMBER:
				st[S_DISCOVERY] = 1 + (i % 3)
		else:
			var bnd: int = band_of(st[S_FLOOR_MM])
			if bnd >= 2 and st[S_KIND] == K_CHAMBER:
				st[S_DISCOVERY] = 1 + (i % 3)
			if bnd == 3 and st[S_KIND] == K_CHAMBER:
				st[S_DISCOVERY] = 4

		# --- past the melt front nothing runs and nothing drips -----------
		if dry_side:
			wk &= ~WK_STANDWATER

		st[S_WORKS] = wk
		stations[i] = st

# ===========================================================================
# rule V10: ceilings, and the invariant that could not be checked before
# ===========================================================================
# PROCEDURAL-AND-GODOT section 1.6 asserts "chambers must be taller than the
# passages that reach them" against a field `Passage` did not have. It has one
# now (THE-ICE section 2.10), so the assertion is a countable post-condition.
func _ceilings() -> void:
	for i in range(stations.size()):
		var st: PackedInt32Array = stations[i]
		var h: int = int(WC_HEIGHT_MM[st[S_WIDTH]])
		if st[S_KIND] == K_CHAMBER:
			h = (h * 135) / 100
		st[S_CEIL_MM] = st[S_FLOOR_MM] + h
		stations[i] = st
	ceil_violations = 0
	var nl: int = links.size() / L_ROW
	for k in range(nl):
		if links[k * L_ROW + L_PITCH] >= 0:
			continue
		var a: PackedInt32Array = stations[links[k * L_ROW + L_A]]
		var b: PackedInt32Array = stations[links[k * L_ROW + L_B]]
		if a[S_KIND] == K_CHAMBER and b[S_CEIL_MM] > a[S_CEIL_MM]:
			ceil_violations += 1
		if b[S_KIND] == K_CHAMBER and a[S_CEIL_MM] > b[S_CEIL_MM]:
			ceil_violations += 1

# ===========================================================================
# rule V11: depth_band, over the DIRECTED graph
# ===========================================================================
# THE-ICE section 5.4 note 1: depth_band and depth_mm must CORRELATE but not be
# identical, which is true of real mines and is why a long horizontal drive at
# depth still reads as deep. A pitch costs its own drop in cells, so a level
# reached by a 34 m winze starts 57 cells deep before anybody walks anywhere.
func _depth_bfs() -> void:
	var n: int = stations.size()
	# NOTE: these are untyped Arrays and NOT PackedInt32Arrays, deliberately.
	# A Packed* array is a VALUE type in GDScript, so `(adj[a] as
	# PackedInt32Array).append(b)` appends to a COPY and silently does nothing.
	# That cost an hour and it is the same copy-on-write trap dressing.gd's MB
	# class already carries a note about.
	var adj: Array = []
	adj.resize(n)
	for i in range(n):
		adj[i] = []
	var nl: int = links.size() / L_ROW
	for k in range(nl):
		var a: int = links[k * L_ROW + L_A]
		var b: int = links[k * L_ROW + L_B]
		var c: int = links[k * L_ROW + L_COST]
		var pi: int = links[k * L_ROW + L_PITCH]
		var down_ok: bool = true
		var up_ok: bool = true
		if pi >= 0:
			var pr: PackedInt32Array = pitches[pi]
			down_ok = (pr[P_FLAGS] & PF_DOWN) != 0
			up_ok = (pr[P_FLAGS] & PF_UP) != 0
		if down_ok:
			(adj[a] as Array).append(b)
			(adj[a] as Array).append(c)
		if up_ok:
			(adj[b] as Array).append(a)
			(adj[b] as Array).append(c)
	var dist := PackedInt32Array()
	dist.resize(n)
	for i in range(n):
		dist[i] = 1 << 28
	dist[collar_st] = 0
	# Dijkstra with integer costs, over a graph of a few thousand nodes and a
	# tiny cost range. A plain relaxation sweep is O(V*E) worst case and is
	# under a millisecond here; a heap is the Rust version's problem.
	var changed: bool = true
	var guard: int = 0
	while changed and guard < 64:
		changed = false
		guard += 1
		for i in range(n):
			if dist[i] >= (1 << 28):
				continue
			var a2: Array = adj[i]
			var m: int = a2.size() / 2
			for j in range(m):
				var b2: int = a2[j * 2]
				var c2: int = a2[j * 2 + 1]
				if dist[i] + c2 < dist[b2]:
					dist[b2] = dist[i] + c2
					changed = true
	for i in range(n):
		var st: PackedInt32Array = stations[i]
		st[S_DEPTH] = dist[i] if dist[i] < (1 << 28) else 0
		stations[i] = st

# ===========================================================================
# rule V12: rasterise, one integer array PER LEVEL
# ===========================================================================
func _rasterise() -> void:
	for si in range(stations.size()):
		var st: PackedInt32Array = stations[si]
		var L: int = st[S_LEVEL]
		var r: int = int(WC_RADIUS_CELLS[st[S_WIDTH]])
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
				var k: int = idx3(L, cx, cy)
				grid_state[k] = st[S_STATE]
				if grid_station[k] < 0:
					grid_station[k] = si

# ===========================================================================
# rule V13: connectivity is DIRECTED, and the two assertions are separate
# ===========================================================================
# THE-ICE section 5.3: "the post-condition test has to be written as two
# separate assertions: reachable from the shaft, and -- separately, and
# ALLOWED TO FAIL BY DESIGN -- able to return to it."
func _connectivity() -> void:
	var n: int = stations.size()
	var fwd: Array = []
	var rev: Array = []
	fwd.resize(n)
	rev.resize(n)
	for i in range(n):
		fwd[i] = []
		rev[i] = []
	var nl: int = links.size() / L_ROW
	for k in range(nl):
		var a: int = links[k * L_ROW + L_A]
		var b: int = links[k * L_ROW + L_B]
		var pi: int = links[k * L_ROW + L_PITCH]
		var down_ok: bool = true
		var up_ok: bool = true
		if pi >= 0:
			var pr: PackedInt32Array = pitches[pi]
			down_ok = (pr[P_FLAGS] & PF_DOWN) != 0
			up_ok = (pr[P_FLAGS] & PF_UP) != 0
		if down_ok:
			(fwd[a] as Array).append(b)
			(rev[b] as Array).append(a)
		if up_ok:
			(fwd[b] as Array).append(a)
			(rev[a] as Array).append(b)
	st_down = _bfs_mark(fwd, collar_st, n)
	st_up = _bfs_mark(rev, collar_st, n)
	reach_down = 0
	reach_up = 0
	for k in range(grid_state.size()):
		if grid_state[k] == ROCK:
			continue
		var si: int = grid_station[k]
		if si < 0:
			continue
		if st_down[si] == 1:
			reach_down += 1
		if st_up[si] == 1:
			reach_up += 1

func _bfs_mark(adj: Array, src: int, n: int) -> PackedByteArray:
	var seen := PackedByteArray()
	seen.resize(n)
	for i in range(n):
		seen[i] = 0
	var q := PackedInt32Array()
	q.append(src)
	seen[src] = 1
	var head: int = 0
	while head < q.size():
		var u: int = q[head]
		head += 1
		var a: Array = adj[u]
		for j in range(a.size()):
			var v: int = a[j]
			if seen[v] == 0:
				seen[v] = 1
				q.append(v)
	return seen

# ===========================================================================
# the replay hash. FNV-1a over every integer this layer produced, in index
# order. Two clients that agree on this agree on the cave. Dressing never
# contributes to it. UNCHANGED IN FORM; the pitch rows are new input.
# ===========================================================================
func _h32(h: int, v: int) -> int:
	v = v & M32
	h = ((h ^ (v & 0xFF)) * 0x01000193) & M32
	h = ((h ^ ((v >> 8) & 0xFF)) * 0x01000193) & M32
	h = ((h ^ ((v >> 16) & 0xFF)) * 0x01000193) & M32
	h = ((h ^ ((v >> 24) & 0xFF)) * 0x01000193) & M32
	return h

# SCHEMA VERSIONS, and this is load-bearing for something outside this
# directory. `spikes/godot/cloud/` holds a byte copy of the pre-2026-09-10 file
# and cuts its belief frames from THIS cave's cameras, matched at 5 mm RMS.
# So the flat path must hash to what it always hashed to:
#
#     seed 7, 240 cells, levels 1  ->  0xAD83E3ED
#
# v1 hashes the sixteen station fields the old row had and nothing else. v2
# adds the five new station fields, the pitch rows, the chamber rows, the water
# surfaces, the datum, the melt front and the level count.
const SCHEMA_V1_FIELDS: int = 16
const V1_SEED7_LEN240_HASH: int = 0xAD83E3ED

func schema_version() -> int:
	return 1 if levels == 1 else 2

func content_hash() -> int:
	var h: int = 0x811C9DC5
	for i in range(grid_state.size()):
		h = ((h ^ grid_state[i]) * 0x01000193) & M32
	var nf: int = SCHEMA_V1_FIELDS if levels == 1 else S_ROW
	for si in range(stations.size()):
		var st: PackedInt32Array = stations[si]
		for f in range(nf):
			h = _h32(h, st[f])
	if levels == 1:
		return h
	for pi in range(pitches.size()):
		var pr: PackedInt32Array = pitches[pi]
		for f2 in range(P_ROW):
			h = _h32(h, pr[f2])
	for c in range(chambers.size()):
		h = _h32(h, chambers[c])
	for L in range(level_water_mm.size()):
		h = _h32(h, level_water_mm[L])
	h = _h32(h, datum_mm)
	h = _h32(h, melt_mm)
	h = _h32(h, levels)
	return h

func open_cells() -> int:
	var n: int = 0
	for i in range(grid_state.size()):
		if grid_state[i] != ROCK:
			n += 1
	return n

func vertical_range_mm() -> int:
	var lo: int = 1 << 30
	var hi: int = -(1 << 30)
	for i in range(stations.size()):
		var st: PackedInt32Array = stations[i]
		lo = mini(lo, st[S_FLOOR_MM])
		hi = maxi(hi, st[S_CEIL_MM])
	for pi in range(pitches.size()):
		var pr: PackedInt32Array = pitches[pi]
		hi = maxi(hi, pr[P_TOP_MM])
		lo = mini(lo, pr[P_BOT_MM])
	return hi - lo
