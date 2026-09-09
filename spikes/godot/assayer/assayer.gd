# ---------------------------------------------------------------------------
# BLINDSIDE -- THE ASSAYER, built procedurally at true scale, and its cycle.
#
# "A survey machine the last industry bolted into the bedrock to find out what
#  was in the rock: every seventy-five seconds it swings a ribbed array onto a
#  new bearing, ratchets a hammer up its mast, and drops it, driving a shock
#  through the stone so it can listen to what comes back."   THE-MACHINERY 1
#
# EVERY DIMENSION BELOW IS FROM THE-MACHINERY 2.1 AT 0.6 m/CELL, or from
# ART-DIRECTION 5.1's table of the same numbers in metres. Where a dimension is
# not in either document it is a proposal from docs/art/vision/machinery/NOTES.md
# and it is marked `# CONCEPT n`; where it is neither, it is marked `# GUESS`
# and it appears in the list at the end of NOTES.md. Nothing is unlabelled.
#
# THE ONE STRUCTURAL DECISION, and it is a design problem the concept art found
# rather than an art choice (NOTES.md "design problems" 1):
#
#   THE-MACHINERY 2.1 puts the boom at z = 9 cells and lets the hammer climb
#   8.4 cells up a mast whose top is 11. A ring that rides the mast CANNOT pass
#   the boom root, so a physical build must choose. This build takes the
#   concept art's answer -- the slew ring at 5.40 m, the hammer's travel 3.50 m
#   below it, the mast continuing to 6.60 m to carry the winch head -- because
#   it keeps every number in the doc except the drop, and it puts the beacon
#   above the boom where ART-DIRECTION 5.4 measured it. 81 kJ becomes ~56 kJ.
#   The beat does not change. It is still a seismic weight drop.
#
# THE ANIMATION RULE, inherited from THE-MACHINERY 2.2 and true in Godot for a
# different reason: nothing rebuilds. The machine is three static meshes under
# three transforms -- the fixed body, the TURRET (rotates), the HAMMER
# (translates) -- plus two scaled bars (the chain, the water column) and two
# emitters whose colour and energy are set from one clock. There is no
# per-frame geometry anywhere.
# ---------------------------------------------------------------------------
class_name Assayer
extends Node3D

const CELL: float = 0.6

# --- the cycle, THE-MACHINERY 3 --------------------------------------------
const PERIOD: float = 75.0
const SLEW_AT: float = 54.0        # p 54-57, the boom swings 36 deg
const SLEW_S: float = 3.0
const LOCK_AT: float = 57.0        # p 57-62, five seconds of stillness
const WIND_AT: float = 62.0        # p 62-71, nine clicks at 1 Hz
const CLICKS: int = 9
const FIRE_AT: float = 71.0        # p 71.0-71.15, the fall
const FALL_S: float = 0.15
const LETHAL_S: float = 4.0        # p 71-75
const AIM_0_DEG: float = 41.5      # ANCIENT_AIM_0_DEG
const AIM_STEP_DEG: float = -36.0  # ANCIENT_AIM_STEP_DEG, always the same way

# --- the light, ART-DIRECTION 2.1 and 5.4 ----------------------------------
const K_WIND_LO: float = 1900.0
const K_WIND_HI: float = 2400.0
const K_STRIKE: float = 4000.0
const STRIKE_GAIN: float = 4.0     # "one frame at ~4x the wind's output".
                                   # The doc's own number, and it survives once
                                   # the sources are out of their castings and
                                   # the wind is calibrated: measured against
                                   # ART-DIRECTION 2.9 the strike lands inside
                                   # the 3% blown ceiling and inside the 50%
                                   # legible allowance that section grants a
                                   # strike specifically. It was pulled to 2.6
                                   # while the lights were still trapped, which
                                   # was fixing the wrong number.
const DECAY_S: float = 8.0         # "decay over 8 s as the brake cools"
const ANVIL_FRACTION: float = 0.34 # "a second source at the anvil block ...
                                   #  at about a third the output"

# --- the form, in metres ---------------------------------------------------
const PAD_R: float = 2.6 * CELL          # 1.560  footing anchor pads
const HUB_R: float = 1.0 * CELL          # 0.600  the hub, top of the legs
const LEG_TOP: float = 1.2 * CELL        # 0.720
const PAD_SZ: float = 0.8 * CELL         # 0.480  square pads
const ANVIL_AF: float = 1.600            # CONCEPT 1: the hub IS the anvil
const ANVIL_TOP: float = 1.050
const MAST_AF: float = 1.6 * CELL        # 0.960 across the flats
const MAST_TOP: float = 11.0 * CELL      # 6.600
const SLEW_Y: float = 9.0 * CELL         # 5.400  the boom's height in the doc
const TURRET_TOP: float = 6.050          # GUESS: 0.65 m of turret sleeve
const BOOM_Y: float = 5.550              # boom centreline, just above the ring
const BOOM_LEN: float = 7.0 * CELL       # 4.200
const BOOM_W: float = 0.9 * CELL         # 0.540
const RIB_ROOT: float = 2.4 * CELL       # 1.440  rib width at the root
const RIB_TIP: float = 1.2 * CELL        # 0.720  ... tapering at the tip
const RIB_SPACE: float = 1.4 * CELL      # 0.840  five cross-ribs
const RIBS: int = 5
const CW_LEN: float = 2.2 * CELL         # 1.320  the counterweight stub
const CW_RIB: float = 1.6 * CELL         # 0.960  with one rib
const HAMMER_AF: float = 2.0 * CELL      # 1.200  hex ring, riding the mast
const HAMMER_H: float = 0.600            # ART-DIRECTION 5.1: "600 mm deep"
const HAMMER_TOP: float = 4.550          # top of travel: bottom face
const PLATFORM_R: float = 3.4 * CELL     # 2.040  the old service platform
const PLATFORM_Y: float = 0.950          # GUESS: a deck height a man works at
const TANK_R: float = 0.600              # CONCEPT 5
const TANK_Y0: float = 2.100
const TANK_Y1: float = 3.900
const TANK_OFF: float = -1.180           # on a -Z bracket (the doc's -Y in plan)
const GLASS_Y0: float = 2.200
const GLASS_Y1: float = 3.800
const LETHAL_R: float = 9.0 * CELL       # 5.400  drawn nowhere; it is the scour

var mats: AssayerMaterials
var seedv: int = 7

# the three moving nodes and nothing else
var turret: Node3D
var hammer: Node3D
var body: Node3D                   # everything fixed, incl. the recoil
var chain: MeshInstance3D
var column: MeshInstance3D         # the water in the sight glass
var winch_glow: MeshInstance3D
var anvil_glow: MeshInstance3D
var winch_light: OmniLight3D
var anvil_lights: Array = []
var drip: GPUParticles3D
var pawl: Node3D

# state, all derived from one clock
var aim_deg: float = AIM_0_DEG
var cycle: int = 0
var clicks_done: int = 0
var tank_fill: float = 1.0
var last_fired_aim: float = AIM_0_DEG - AIM_STEP_DEG
var fired_once: bool = false
var stat_tris: int = 0
var spent: bool = false            # a machine that has stopped
var hot_scale: float = 1.0         # 1 in the game; 0.26 under the CLEAR rig
# CALIBRATED, not inherited, and calibrated TWICE: the first table was taken
# with both sources still sealed inside their own castings, so it was measuring
# a shadow bug and its numbers were 2.4x too high. Re-run with the sources
# where ART-DIRECTION 5.4 puts them, on the same frame (click 9, 8.5 m, 52 deg
# vertical), read against ART-DIRECTION 2.9's LINEARISED bands:
#
#     30 ->  1.5% legible, 94.5% black     unplayable
#     45 ->  2.7% legible, 90.1% black     under the 3% floor
#     65 ->  4.9% legible, 79.8% black     inside the contract
#     90 ->  8.5% legible, 65.5% black     loses the >=70% black
#    125 -> 16.0% legible, 55.7% black     a lit level
#    170 -> 29.1% legible, 49.5% black
#
# 72 sits at about 6% legible and 75% black. It is a RATIO, not a wattage, and
# ART-DIRECTION 2.2 is explicit that it does not survive a change of renderer.
var hot_energy: float = 72.0
var last_p: float = 0.0

var _sheave_p := Vector3(0.62, 5.980, 0.0)
var _base_y: float = 0.0


# ===========================================================================
# BUILD
# ===========================================================================
func build(m: AssayerMaterials, sd: int) -> void:
	mats = m
	seedv = sd
	_base_y = position.y

	body = Node3D.new()
	body.name = "Body"
	add_child(body)

	var fixed := MeshKit.MB.new()
	_footing(fixed)
	_anvil(fixed)
	_mast(fixed)
	_ratchet_track(fixed)
	_ladder(fixed)
	_slew_seat(fixed)
	_mast_head(fixed)
	_tank(fixed)
	_pipes(fixed)
	_platform(fixed)
	_stays_fixed(fixed)
	var fm := MeshInstance3D.new()
	fm.mesh = fixed.commit()
	fm.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
	body.add_child(fm)
	stat_tris += fixed.tri_count()

	# --- the turret: everything that turns with the bearing -----------------
	turret = Node3D.new()
	turret.name = "Turret"
	body.add_child(turret)
	var tb := MeshKit.MB.new()
	_turret_sleeve(tb)
	_slew_race(tb)
	_boom(tb)
	_counterweight(tb)
	_king_post_and_stays(tb)
	var tm := MeshInstance3D.new()
	tm.mesh = tb.commit()
	tm.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
	turret.add_child(tm)
	stat_tris += tb.tri_count()

	# --- the hammer: one translation in Y -----------------------------------
	hammer = Node3D.new()
	hammer.name = "Hammer"
	body.add_child(hammer)
	var hb := MeshKit.MB.new()
	_hammer(hb)
	var hm := MeshInstance3D.new()
	hm.mesh = hb.commit()
	hm.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
	hammer.add_child(hm)
	stat_tris += hb.tri_count()

	_chain_and_column()
	_emitters()
	_drip()
	set_phase(0.0)


# --- THE FOOTING -----------------------------------------------------------
# THE-MACHINERY 2.1: "3 legs 120 deg apart, hub r=1.0 at z=1.2 out to r=2.6 at
# z=0; 3 anchor pads, 0.8-cell squares". A cast leg is a tapering box with a
# web rib down its underside and a knee bracket where it meets the hub; a pad
# is a plate with four bolts through it into the rock; and the three pads are
# tied to each other, because a machine that hammers would walk otherwise.
func _footing(mb: MeshKit.MB) -> void:
	var C := AssayerMaterials.C_IRON
	var CL := AssayerMaterials.C_IRON_L
	var pads: Array = []
	for i in range(3):
		var a: float = TAU * float(i) / 3.0 + PI * 0.5
		var dirv := Vector3(cos(a), 0.0, sin(a))
		var hub: Vector3 = Vector3(0, LEG_TOP, 0) + dirv * (HUB_R * 0.72)
		var pad: Vector3 = dirv * PAD_R
		pads.append(pad)
		var d: Vector3 = pad - hub
		var l: float = d.length()
		# Basis.looking_at puts LOCAL -Z along its argument, and tbox builds
		# along local +Z, so the leg is aimed by negating.
		var t := Transform3D(Basis.looking_at(-d.normalized(), Vector3.UP), hub)
		# the leg: 340 mm x 300 mm at the hub, 500 mm x 160 mm at the pad
		MeshKit.tbox(mb, mats.iron, C, 0.340, 0.300, 0.500, 0.160, l, t)
		# the web rib on the underside -- ART-DIRECTION 5.2's "webs and ribs on
		# every flat plane". Without this a cast leg reads as a stick.
		var mid: Vector3 = (hub + pad) * 0.5
		MeshKit.web(mb, mats.iron, C,
			hub + Vector3(0, -0.14, 0),
			pad + Vector3(0, -0.05, 0),
			mid + Vector3(0, -0.44, 0), 0.055)
		# the knee bracket at the hub: a casting has a fillet, and a fillet
		# large enough to see is a bracket
		MeshKit.web(mb, mats.iron, C,
			Vector3(0, LEG_TOP + 0.18, 0) + dirv * (HUB_R * 0.30),
			hub + dirv * 0.62,
			Vector3(0, LEG_TOP - 0.10, 0) + dirv * (HUB_R * 0.30), 0.085)
		# The pad: a plate, four bolts, and the grout course under it -- and it
		# is the one part of the machine that stood in water for decades, so it
		# is built in the GRAPHITISED iron: black, non-metallic, velvety,
		# INTACT IN SILHOUETTE AND DEAD IN SURFACE (ART-DIRECTION 5.2). One
		# material swap on a Z threshold, decided HERE and not in a shader,
		# because where the waterline was is a fact about the world.
		mb.add_prim(mats.iron_dk, MeshKit.box(PAD_SZ * 1.30, 0.090, PAD_SZ * 1.30),
			Transform3D(Basis.from_euler(Vector3(0, -a, 0)), pad + Vector3(0, 0.045, 0)),
			AssayerMaterials.C_GRAPH)
		mb.add_prim(mats.iron_dk, MeshKit.box(PAD_SZ * 1.46, 0.070, PAD_SZ * 1.46),
			Transform3D(Basis.from_euler(Vector3(0, -a, 0)), pad + Vector3(0, -0.010, 0)),
			AssayerMaterials.C_GRAPH)
		# the 120 mm mineral crust standing above the line the water left
		mb.add_prim(mats.iron, MeshKit.box(PAD_SZ * 1.34, 0.120, PAD_SZ * 1.34),
			Transform3D(Basis.from_euler(Vector3(0, -a, 0)), pad + Vector3(0, 0.150, 0)), CL)
		for bx in [-1.0, 1.0]:
			for bz in [-1.0, 1.0]:
				var o: Vector3 = Basis.from_euler(Vector3(0, -a, 0)) * Vector3(bx * 0.155, 0.0, bz * 0.155)
				MeshKit.bolt(mb, mats.steel, AssayerMaterials.C_STEEL,
					pad + o + Vector3(0, 0.090, 0), Vector3.UP, 0.035)
	# the tie rods, pad to pad
	for i in range(3):
		var a0: Vector3 = pads[i] + Vector3(0, 0.14, 0)
		var a1: Vector3 = pads[(i + 1) % 3] + Vector3(0, 0.14, 0)
		var d2: Vector3 = a1 - a0
		mb.add_prim(mats.iron, MeshKit.cyl(0.028, d2.length(), 6),
			Transform3D(MeshKit.along(d2), (a0 + a1) * 0.5), C)
		# a turnbuckle in the middle of each, because a tie rod is adjustable
		mb.add_prim(mats.iron, MeshKit.cyl(0.052, 0.22, 6),
			Transform3D(MeshKit.along(d2), (a0 + a1) * 0.5), CL)


# --- THE ANVIL -------------------------------------------------------------
# CONCEPT 1: THE-MACHINERY never says what the hammer lands on, so the footing
# hub IS the anvil -- a hex block 1.6 m across with a bearing-steel strike
# face, and the drip lands on that face and keeps one wet patch on it.
#
# TRAILER 10 requires the raised index mark K 14 to be legible in shot 24
# without being pointed at, so it is 220 mm tall, 14 mm proud, on the flat that
# faces the chamber, and there is a second one on the hammer that lands on it.
func _anvil(mb: MeshKit.MB) -> void:
	var C := AssayerMaterials.C_IRON
	var CL := AssayerMaterials.C_IRON_L
	# The block, with draft: 1.640 at the bottom, 1.600 at the shoulder -- and
	# then a CHAMFER, 100 mm of run over 150 mm of rise, up to a 1.400 top face
	# the 1.200 hammer lands inside.
	#
	# The chamfer is not decoration and it is not a taste call. It is the only
	# surface on this block that a mark can be cast on and still be READ, and
	# TRAILER 10 requires K 14 to be legible in shot 24 without being pointed
	# at. Measured: the machine's own light comes from an emitter ring on the
	# anvil's top face and from the winch head 5.7 m straight up, so every
	# VERTICAL face of the anvil has N.L of -0.14 to -0.92 -- it is turned away
	# from every source the fiction supplies, and a mark on it renders as a
	# black panel. The chamfer's normal stands 56 degrees above horizontal, so
	# both sources rake it, and 12 mm of relief throws a shadow as long as the
	# letter is tall. Foundries cast marks on chamfers for the same reason.
	MeshKit.prism(mb, mats.iron, C, 6, 1.640, ANVIL_AF, LEG_TOP - 0.10, 0.900)
	MeshKit.prism(mb, mats.iron, CL, 6, ANVIL_AF, 1.400, 0.900, ANVIL_TOP, Vector3.ZERO, 0.0, false, false)
	# the parting line: every casting has one, and it is 4 mm of raised flash
	# round the middle of the block. It is the cheapest possible "this was
	# poured" and it is visible under a lamp at two metres.
	MeshKit.prism_ring(mb, mats.iron, CL, 6, 1.632, 1.600, 0.755, 0.763)
	# the strike face: bearing steel, still working, inset 12 mm
	MeshKit.prism_ring(mb, mats.steel, AssayerMaterials.C_RACE, 24, 1.360, 0.560,
		ANVIL_TOP - 0.012, ANVIL_TOP - 0.002)
	# a raised collar the hammer registers on
	MeshKit.prism_ring(mb, mats.iron, C, 6, 1.400, 1.340, ANVIL_TOP - 0.045, ANVIL_TOP)
	# THE INDEX MARK. Raised, cast, no date, unreadable as language. It is cast
	# TWICE on the same block, which is what a foundry does so a casting can be
	# identified whichever way it lies: once large on the vertical flat, where
	# a visiting machine's work lamp reads it, and once on the chamfer above,
	# where the machine's OWN light reads it. Two of the six faces carry it.
	# MeshKit.prism puts a VERTEX at `phase`, so a hexagon built at phase 0 has
	# its corners on 0, 60, 120 ... and its FLATS centred on 30, 90, 150 ...
	# The first build cast both marks on 0 and 120 and therefore straddled two
	# corners with a flat panel, which is why the anvil photographed as a blank
	# block from every bearing. Marks go on flat centres.
	# ... and they go on the two flats that can actually be SEEN, which is a
	# fact about the service platform and not about the casting: the deck sits
	# at 0.95 m and the mark at 0.74-0.89, so a surviving grating bay is a lid
	# over it. Four of the eight bays are gone (`keep` in _platform), and the
	# flats at 210 and 330 degrees are the two that look out through a gap.
	for ang in [deg_to_rad(210.0), deg_to_rad(330.0)]:
		var nrm := Vector3(cos(ang), 0, sin(ang))
		# --- on the flat: a raised panel, as a foundry would cast it ---------
		var t := Transform3D(MeshKit.face(nrm), nrm * (ANVIL_AF * 0.5)
			+ Vector3(0, LEG_TOP - 0.04, 0))
		mb.add_prim(mats.iron, MeshKit.box(0.560, 0.215, 0.010),
			t * Transform3D(Basis.IDENTITY, Vector3(0.150, 0.135, 0.005)), CL)
		MeshKit.lettering(mb, mats.iron, CL, "K 14",
			t * Transform3D(Basis.IDENTITY, Vector3(-0.075, 0.060, 0.010)),
			0.150, 0.026, 0.028)
		# --- on the chamfer: tilted 34 degrees off vertical, so it catches ---
		var cn: Vector3 = (nrm * 0.15 + Vector3(0, 0.10, 0)).normalized()
		var cp: Vector3 = nrm * 0.745 + Vector3(0, 0.972, 0)
		var ct := Transform3D(MeshKit.face(cn), cp)
		mb.add_prim(mats.iron, MeshKit.box(0.400, 0.130, 0.007),
			ct * Transform3D(Basis.IDENTITY, Vector3(0.0, 0.0, 0.0035)), CL)
		MeshKit.lettering(mb, mats.iron, CL, "K 14",
			ct * Transform3D(Basis.IDENTITY, Vector3(-0.166, -0.045, 0.007)),
			0.090, 0.012, 0.017)
	# the foundry mark: a round boss with one bar. A system, not a sentence.
	var fn := Vector3(cos(deg_to_rad(270.0)), 0, sin(deg_to_rad(270.0)))
	var ft := Transform3D(MeshKit.face(fn), fn * (ANVIL_AF * 0.5) + Vector3(0, LEG_TOP + 0.05, 0))
	mb.add_prim(mats.iron, MeshKit.cyl(0.115, 0.012, 14),
		ft * Transform3D(Basis.from_euler(Vector3(PI * 0.5, 0, 0)), Vector3(0, 0, 0.006)), CL)
	mb.add_prim(mats.iron, MeshKit.box(0.170, 0.026, 0.010),
		ft * Transform3D(Basis.IDENTITY, Vector3(0, 0, 0.014)), CL)


# --- THE MAST --------------------------------------------------------------
# THE-MACHINERY 2.1: "hexagonal prism, 1.6 across the flats, z = 1.2 -> 11.0".
# Built in three sections with a bolted flange between each, because a 5.5 m
# casting does not exist and a mast this tall was shipped in pieces
# (CONCEPT 3). 2 degrees of draft per section; a longitudinal web rib on every
# flat; the parting line running the whole height.
func _mast(mb: MeshKit.MB) -> void:
	var C := AssayerMaterials.C_IRON
	var CL := AssayerMaterials.C_IRON_L
	var breaks := [ANVIL_TOP, 2.780, 4.420, SLEW_Y]
	for i in range(breaks.size() - 1):
		var y0: float = breaks[i]
		var y1: float = breaks[i + 1]
		# draft: 2 degrees over the section, and each section starts a little
		# narrower than the one below finished -- a stack, not a taper
		var af0: float = MAST_AF - float(i) * 0.020
		var af1: float = af0 - (y1 - y0) * tan(deg_to_rad(2.0)) * 0.55
		MeshKit.prism(mb, mats.iron, C, 6, af0, af1, y0, y1, Vector3.ZERO, 0.0, false, false)
		# the flange at the bottom of every section: a hex ring, 12 bolts
		MeshKit.prism_ring(mb, mats.iron, CL, 6, af0 + 0.260, af0 - 0.06, y0, y0 + 0.075)
		var fr: float = (af0 + 0.150) * 0.5 / cos(PI / 6.0)
		for b in range(12):
			var a: float = TAU * float(b) / 12.0 + 0.26
			MeshKit.bolt(mb, mats.steel, AssayerMaterials.C_STEEL,
				Vector3(cos(a) * fr, y0 + 0.075, sin(a) * fr), Vector3.UP, 0.030)
		# a web rib up the centre of each flat: 50 mm proud, 90 mm wide
		for f in range(6):
			var fa: float = TAU * (float(f) + 0.5) / 6.0
			var nrm := Vector3(cos(fa), 0, sin(fa))
			var rr: float = af0 * 0.5 - 0.004
			var t := Transform3D(MeshKit.face(nrm),
				nrm * rr + Vector3(0, (y0 + y1) * 0.5 + 0.05, 0))
			mb.add_prim(mats.iron, MeshKit.box(0.090, y1 - y0 - 0.16, 0.050),
				t * Transform3D(Basis.IDENTITY, Vector3(0, 0, 0.025)), C)
	# the parting line, whole height, on two opposite corners
	for f in [0, 3]:
		var fa2: float = TAU * float(f) / 6.0
		var nrm2 := Vector3(cos(fa2), 0, sin(fa2))
		var rr2: float = MAST_AF * 0.5 / cos(PI / 6.0)
		mb.add_prim(mats.iron, MeshKit.box(0.020, SLEW_Y - ANVIL_TOP, 0.008),
			Transform3D(MeshKit.face(nrm2),
				nrm2 * (rr2 - 0.002) + Vector3(0, (ANVIL_TOP + SLEW_Y) * 0.5, 0)), CL)
	# above the slew ring the mast continues to the head, thinner
	MeshKit.prism(mb, mats.iron, C, 6, 0.720, 0.690, TURRET_TOP - 0.02, MAST_TOP - 0.12,
		Vector3.ZERO, 0.0, false, false)


# --- THE RATCHET TRACK -----------------------------------------------------
# CONCEPT 3: "a ratchet track of bearing-steel teeth on the +X flat of the
# mast". Nine clicks a cycle for a century, so the teeth are the one part of
# the machine that is polished bright by the pawl and never rusts. The pitch is
# the hammer's travel divided by nine times a whole number of teeth per click:
# 3.5 m / 9 = 389 mm a click, at 4 teeth a click, is a 97 mm pitch.   # GUESS
func _ratchet_track(mb: MeshKit.MB) -> void:
	var nrm := Vector3(1, 0, 0)
	var x: float = MAST_AF * 0.5 - 0.002
	# the track plate it is cut into
	mb.add_prim(mats.iron, MeshKit.box(0.180, HAMMER_TOP - ANVIL_TOP + 0.30, 0.040),
		Transform3D(MeshKit.face(nrm),
			Vector3(x, (ANVIL_TOP + HAMMER_TOP + 0.30) * 0.5 - 0.05, 0)),
		AssayerMaterials.C_IRON)
	var pitch: float = 0.0972
	var y: float = ANVIL_TOP + 0.10
	while y < HAMMER_TOP + 0.18:
		# a tooth is a wedge: vertical on the top face, sloped underneath, so
		# the pawl climbs it one way and locks the other
		mb.add_prim(mats.steel, MeshKit.box(0.135, 0.030, 0.056),
			Transform3D(MeshKit.face(nrm), Vector3(x + 0.048, y, 0)),
			AssayerMaterials.C_RACE)
		MeshKit.web(mb, mats.steel, AssayerMaterials.C_STEEL,
			Vector3(x + 0.020, y - 0.015, -0.066),
			Vector3(x + 0.076, y - 0.015, -0.066),
			Vector3(x + 0.020, y - 0.062, -0.066), 0.130)
		y += pitch


# --- THE LADDER ------------------------------------------------------------
# CONCEPT 3: "a ladder on the -X flat". Somebody serviced this. The ladder is
# the strongest single piece of evidence on the machine that a person was meant
# to be here, which is why it survives the density cut.
func _ladder(mb: MeshKit.MB) -> void:
	var C := AssayerMaterials.C_IRON
	var x: float = -(MAST_AF * 0.5) - 0.115
	var y0: float = 1.180
	var y1: float = 5.240
	for zs in [-0.170, 0.170]:
		mb.add_prim(mats.iron, MeshKit.cyl(0.021, y1 - y0, 6),
			Transform3D(Basis.IDENTITY, Vector3(x, (y0 + y1) * 0.5, zs)), C)
	var y: float = y0 + 0.14
	var rung: int = 0
	while y < y1:
		rung += 1
		# Three of the bottom six rungs are gone. A ladder with every rung is
		# maintenance; a ladder that has lost its wet end is a century, and it
		# is the cheapest sentence about time anywhere on the object.
		if rung == 2 or rung == 3 or rung == 6:
			y += 0.285
			continue
		mb.add_prim(mats.iron, MeshKit.cyl(0.014, 0.340, 5),
			Transform3D(Basis.from_euler(Vector3(PI * 0.5, 0, 0)), Vector3(x, y, 0.0)), C)
		y += 0.285
	# the stand-off brackets that hold it off the mast
	for yb in [1.40, 2.60, 3.80, 5.00]:
		mb.add_prim(mats.iron, MeshKit.box(0.120, 0.060, 0.400),
			Transform3D(Basis.IDENTITY, Vector3(x + 0.058, yb, 0.0)), C)
	# a hoop cage over the top third: the fall protection of the period
	var yh: float = 3.30
	while yh < y1:
		for k in range(9):
			var a0: float = PI * (0.10 + 0.80 * float(k) / 9.0)
			var a1: float = PI * (0.10 + 0.80 * float(k + 1) / 9.0)
			var p0 := Vector3(x - cos(a0) * 0.36, yh, sin(a0) * 0.36)
			var p1 := Vector3(x - cos(a1) * 0.36, yh, sin(a1) * 0.36)
			var d: Vector3 = p1 - p0
			mb.add_prim(mats.iron, MeshKit.cyl(0.014, d.length(), 5),
				Transform3D(MeshKit.along(d), (p0 + p1) * 0.5), C)
		yh += 0.62


# --- THE SLEW SEAT (fixed) -------------------------------------------------
# The flared bearing seat the ring runs on. It is the widest thing on the mast
# and it is what makes the machine read as a crane rather than as a pole.
func _slew_seat(mb: MeshKit.MB) -> void:
	var C := AssayerMaterials.C_IRON
	MeshKit.prism(mb, mats.iron, C, 12, 0.880, 1.440, SLEW_Y - 0.360, SLEW_Y - 0.060,
		Vector3.ZERO, 0.0, false, false)
	MeshKit.prism_ring(mb, mats.iron, C, 12, 1.470, 0.880, SLEW_Y - 0.075, SLEW_Y - 0.020)
	# gussets under the flare -- a 1.4 m overhang carrying a 4 m arm
	for i in range(12):
		var a: float = TAU * float(i) / 12.0
		var nrm := Vector3(cos(a), 0, sin(a))
		MeshKit.web(mb, mats.iron, C,
			nrm * 0.44 + Vector3(0, SLEW_Y - 0.36, 0),
			nrm * 0.70 + Vector3(0, SLEW_Y - 0.07, 0),
			nrm * 0.44 + Vector3(0, SLEW_Y - 0.90, 0), 0.045)


# --- THE MAST HEAD: the winch, the brake band, the water motor -------------
# CONCEPT 3 and 7. The winch head is the beacon (ART-DIRECTION 5.4 measured a
# mast-head source as lifting 20.6% of the frame and 6.8% of the floor half),
# so it is the thing that has to be visible from the next chamber and the thing
# that must NOT be what lights the ground. Both hot points are point sources
# BESIDE their emitters, not inside the mast.
func _mast_head(mb: MeshKit.MB) -> void:
	var C := AssayerMaterials.C_IRON
	var CL := AssayerMaterials.C_IRON_L
	# the head casting
	MeshKit.prism(mb, mats.iron, C, 6, 1.060, 0.980, MAST_TOP - 0.520, MAST_TOP - 0.060)
	MeshKit.prism(mb, mats.iron, CL, 6, 1.160, 1.060, MAST_TOP - 0.100, MAST_TOP)
	# the crown: a domed cap with a lifting eye, because it was craned in
	mb.add_prim(mats.iron, MeshKit.taper(0.14, 0.42, 0.170, 10),
		Transform3D(Basis.IDENTITY, Vector3(0, MAST_TOP + 0.085, 0)), C)
	mb.add_prim(mats.iron, MeshKit.cyl(0.055, 0.150, 6),
		Transform3D(Basis.from_euler(Vector3(0, 0, PI * 0.5)),
			Vector3(0, MAST_TOP + 0.220, 0)), C)
	# THE WINCH DRUM: axis along X, on a bracket on the +Z side of the head
	var dc := Vector3(0.0, MAST_TOP - 0.300, 0.560)
	mb.add_prim(mats.steel, MeshKit.cyl(0.290, 0.460, 16),
		Transform3D(Basis.from_euler(Vector3(0, 0, PI * 0.5)), dc), AssayerMaterials.C_STEEL)
	for xs in [-0.250, 0.250]:
		mb.add_prim(mats.iron, MeshKit.cyl(0.360, 0.060, 16),
			Transform3D(Basis.from_euler(Vector3(0, 0, PI * 0.5)), dc + Vector3(xs, 0, 0)), C)
		# the drum bearing pedestals
		mb.add_prim(mats.iron, MeshKit.box(0.150, 0.520, 0.220),
			Transform3D(Basis.IDENTITY, dc + Vector3(xs * 1.55, -0.150, 0)), C)
		MeshKit.web(mb, mats.iron, C,
			dc + Vector3(xs * 1.55, -0.400, 0.11),
			dc + Vector3(xs * 1.55, -0.400, -0.30),
			dc + Vector3(xs * 1.55, -0.080, -0.30), 0.040)
	# THE BRAKE BAND -- hot point 1. A band round the drum, held by a lever and
	# an anchor. CONCEPT 7: "the brake band is the emitter at the head".
	# The geometry is here; the emissive band itself is a separate mesh so its
	# material can be driven from the clock without touching this one.
	mb.add_prim(mats.iron, MeshKit.box(0.062, 0.640, 0.070),
		Transform3D(Basis.IDENTITY, dc + Vector3(0.315, 0.170, -0.290)), C)
	mb.add_prim(mats.iron, MeshKit.box(0.055, 0.060, 0.420),
		Transform3D(Basis.IDENTITY, dc + Vector3(0.315, 0.470, -0.100)), C)
	# THE WATER MOTOR: the reason the machine has never stopped. A volute
	# casing with a tangential inlet -- the mine's failure is its power supply.
	var mc := Vector3(0.0, MAST_TOP - 0.330, -0.520)
	mb.add_prim(mats.iron, MeshKit.cyl(0.255, 0.300, 14),
		Transform3D(Basis.from_euler(Vector3(0, 0, PI * 0.5)), mc), C)
	mb.add_prim(mats.iron, MeshKit.cyl(0.300, 0.070, 14),
		Transform3D(Basis.from_euler(Vector3(0, 0, PI * 0.5)), mc + Vector3(0.170, 0, 0)), CL)
	mb.add_prim(mats.iron, MeshKit.box(0.230, 0.190, 0.190),
		Transform3D(Basis.IDENTITY, mc + Vector3(0, -0.230, -0.060)), C)
	# the drain from the motor: the water it has used runs back to the sump
	MeshKit.pipe(mb, mats.iron, C, PackedVector3Array([
		mc + Vector3(0, -0.320, -0.060), mc + Vector3(0, -0.560, -0.240),
		Vector3(-0.180, 3.10, -0.620), Vector3(-0.180, 1.30, -0.620)]), 0.048)
	# THE SHEAVE the chain turns over on its way down the mast
	mb.add_prim(mats.steel, MeshKit.cyl(0.165, 0.090, 14),
		Transform3D(Basis.from_euler(Vector3(0, 0, PI * 0.5)), _sheave_p),
		AssayerMaterials.C_RACE)
	mb.add_prim(mats.iron, MeshKit.box(0.230, 0.400, 0.070),
		Transform3D(Basis.IDENTITY, _sheave_p + Vector3(0.02, 0.14, 0)), C)


# --- THE TURRET SLEEVE and THE SLEW RACE (rotate) --------------------------
# ART-DIRECTION 5.2: "the one clean thing on the object: slew ring, hammer
# face, winch drum contact face, the mast track where the pawl bites, chain.
# A viewer reads *it is still running* off the shine on the bearing before
# anything moves."  So the race is the only mirror in the frame.
func _turret_sleeve(mb: MeshKit.MB) -> void:
	var C := AssayerMaterials.C_IRON
	MeshKit.prism(mb, mats.iron, C, 12, 1.340, 1.180, SLEW_Y + 0.055, TURRET_TOP,
		Vector3.ZERO, 0.0, false, false)
	MeshKit.prism_ring(mb, mats.iron, C, 12, 1.400, 0.740, SLEW_Y + 0.020, SLEW_Y + 0.090)
	MeshKit.prism_ring(mb, mats.iron, AssayerMaterials.C_IRON_L, 12, 1.230, 0.740,
		TURRET_TOP - 0.070, TURRET_TOP)
	for i in range(12):
		var a: float = TAU * float(i) / 12.0 + 0.13
		MeshKit.bolt(mb, mats.steel, AssayerMaterials.C_STEEL,
			Vector3(cos(a) * 0.640, SLEW_Y + 0.090, sin(a) * 0.640), Vector3.UP, 0.028)


func _slew_race(mb: MeshKit.MB) -> void:
	# the bright race: 24 sides so it catches a highlight that travels as it
	# turns. This is the tell for the slew (THE-MACHINERY 5.4).
	MeshKit.prism_ring(mb, mats.steel, AssayerMaterials.C_RACE, 24, 1.500, 1.360,
		SLEW_Y - 0.052, SLEW_Y + 0.052)
	MeshKit.prism_ring(mb, mats.steel, AssayerMaterials.C_STEEL, 24, 1.520, 1.500,
		SLEW_Y - 0.020, SLEW_Y + 0.020)


# --- THE BOOM: the array ---------------------------------------------------
# THE-MACHINERY 2.1: "7.0 long x 0.9 wide at z = 9.0, five cross-ribs at
# 1.4-cell spacing, 2.4 wide at the root tapering to 1.2 at the tip".
# The doc's "outer 20% of each rib HAZARD" is a schematic's way of saying the
# ends do the work; ART-DIRECTION 5.2 forbids HAZARD as a material, so the ends
# are the transducer cans -- the things pressed to the rock's own resonance --
# and they are the one part of the boom in bearing steel.
func _boom(mb: MeshKit.MB) -> void:
	var C := AssayerMaterials.C_IRON
	var CL := AssayerMaterials.C_IRON_L
	# the box girder: a web tapering 440 -> 240 mm in depth, with a flange top
	# and bottom that follows it down. A bar is not a girder.
	var root: float = 0.520
	var tip: float = BOOM_LEN
	var bx := Transform3D(Basis.from_euler(Vector3(0, PI * 0.5, 0)), Vector3(root, BOOM_Y, 0))
	MeshKit.tbox(mb, mats.iron, C, BOOM_W, 0.440, BOOM_W * 0.62, 0.240, tip - root, bx)
	for sy in [1.0, -1.0]:
		MeshKit.tbox(mb, mats.iron, CL if sy > 0.0 else C,
			BOOM_W + 0.080, 0.055, BOOM_W * 0.62 + 0.050, 0.045, tip - root, bx,
			Vector2(0.0, sy * 0.248), Vector2(0.0, sy * 0.145))
	# lightening holes in the web: the only reason a girder this deep is not a
	# wall, and the thing that lets the winch head light through it
	var hx: float = root + 0.44
	while hx < tip - 0.34:
		mb.add_prim(mats.iron, MeshKit.cyl(0.088, BOOM_W + 0.02, 10),
			Transform3D(Basis.from_euler(Vector3(PI * 0.5, 0, 0)),
				Vector3(hx, BOOM_Y - 0.02, 0)), C)
		hx += 0.62
	# the root: a deep casting bolted through the turret top
	MeshKit.tbox(mb, mats.iron, C, 0.700, 0.600, BOOM_W, 0.450, root + 0.14,
		Transform3D(Basis.from_euler(Vector3(0, PI * 0.5, 0)), Vector3(-0.14, BOOM_Y, 0)))
	MeshKit.web(mb, mats.iron, C,
		Vector3(0.10, BOOM_Y + 0.30, 0.0), Vector3(1.10, BOOM_Y + 0.22, 0.0),
		Vector3(0.10, BOOM_Y - 0.34, 0.0), 0.060)
	# the five cross-ribs and their ten transducer cans
	for i in range(RIBS):
		var x: float = RIB_SPACE * float(i + 1)
		var f: float = float(i) / float(RIBS - 1)
		var w: float = lerp(RIB_ROOT, RIB_TIP, f)
		var dep: float = lerp(0.190, 0.130, f)
		MeshKit.tbox(mb, mats.iron, C, 0.150, dep, 0.130, dep * 0.85, w * 0.5,
			Transform3D(Basis.IDENTITY, Vector3(x, BOOM_Y - 0.06, 0.0)))
		MeshKit.tbox(mb, mats.iron, C, 0.150, dep, 0.130, dep * 0.85, w * 0.5,
			Transform3D(Basis.from_euler(Vector3(0, PI, 0)), Vector3(x, BOOM_Y - 0.06, 0.0)))
		# a gusset where each rib meets the girder
		for s in [1.0, -1.0]:
			MeshKit.web(mb, mats.iron, C,
				Vector3(x, BOOM_Y + 0.10, s * 0.12),
				Vector3(x, BOOM_Y - 0.10, s * (w * 0.5 - 0.10)),
				Vector3(x, BOOM_Y - 0.16, s * 0.12), 0.036)
			# THE TRANSDUCER CAN, hanging under the rib end
			var cp := Vector3(x, BOOM_Y - 0.26, s * (w * 0.5))
			mb.add_prim(mats.iron, MeshKit.cyl(0.108, 0.230, 12),
				Transform3D(Basis.IDENTITY, cp), C)
			mb.add_prim(mats.steel, MeshKit.cyl(0.096, 0.045, 12),
				Transform3D(Basis.IDENTITY, cp + Vector3(0, -0.132, 0)),
				AssayerMaterials.C_STEEL)
			mb.add_prim(mats.iron, MeshKit.cyl(0.125, 0.035, 12),
				Transform3D(Basis.IDENTITY, cp + Vector3(0, 0.105, 0)), CL)
			# the lead from the can back along the rib to the girder
			var lp0: Vector3 = cp + Vector3(0, 0.130, 0)
			var lp1 := Vector3(x, BOOM_Y - 0.14, s * 0.10)
			var dd: Vector3 = lp1 - lp0
			mb.add_prim(mats.iron, MeshKit.cyl(0.016, dd.length(), 5),
				Transform3D(MeshKit.along(dd), (lp0 + lp1) * 0.5), C)
	# the tip: a cast end cap with the last pair of cans and a plumb eye
	mb.add_prim(mats.iron, MeshKit.box(0.070, 0.320, BOOM_W * 0.75),
		Transform3D(Basis.IDENTITY, Vector3(tip + 0.03, BOOM_Y, 0)), CL)


# --- THE COUNTERWEIGHT (rotates) -------------------------------------------
# THE-MACHINERY 2.1: "a 2.2-cell stub opposite the boom with one 1.6-cell rib".
func _counterweight(mb: MeshKit.MB) -> void:
	var C := AssayerMaterials.C_IRON
	MeshKit.tbox(mb, mats.iron, C, BOOM_W, 0.420, 0.480, 0.360, CW_LEN,
		Transform3D(Basis.from_euler(Vector3(0, -PI * 0.5, 0)), Vector3(-0.30, BOOM_Y, 0)))
	for sr in [0.0, PI]:
		MeshKit.tbox(mb, mats.iron, C, 0.140, 0.170, 0.120, 0.140, CW_RIB * 0.5,
			Transform3D(Basis.from_euler(Vector3(0, sr, 0)),
				Vector3(-CW_LEN * 0.62, BOOM_Y - 0.05, 0)))
	# the mass box: cast, ribbed, and bolted on so it could be adjusted
	mb.add_prim(mats.iron, MeshKit.box(0.640, 0.540, 0.480),
		Transform3D(Basis.IDENTITY, Vector3(-(CW_LEN + 0.20), BOOM_Y - 0.02, 0)), C)
	for zz in [-0.150, 0.150]:
		mb.add_prim(mats.iron, MeshKit.box(0.680, 0.560, 0.050),
			Transform3D(Basis.IDENTITY, Vector3(-(CW_LEN + 0.20), BOOM_Y - 0.02, zz)),
			AssayerMaterials.C_IRON_L)
	for zz2 in [-0.180, 0.180]:
		for yy in [-0.190, 0.190]:
			MeshKit.bolt(mb, mats.steel, AssayerMaterials.C_STEEL,
				Vector3(-(CW_LEN - 0.12), BOOM_Y - 0.02 + yy, zz2), Vector3(1, 0, 0), 0.028)


# --- THE KING POST AND THE STAYS (rotate) ----------------------------------
# CONCEPT 3: "stays from the mast head to the boom". A 4.2 m arm with a tonne
# of transducers on it does not cantilever; it is stayed, and the stays are
# what make the silhouette read as a machine and not as a T.
func _king_post_and_stays(mb: MeshKit.MB) -> void:
	var C := AssayerMaterials.C_IRON
	var top := Vector3(0, TURRET_TOP + 0.560, 0)
	MeshKit.tbox(mb, mats.iron, C, 0.300, 0.300, 0.190, 0.190, 0.560,
		Transform3D(Basis.from_euler(Vector3(-PI * 0.5, 0, 0)), Vector3(0, TURRET_TOP, 0)))
	mb.add_prim(mats.iron, MeshKit.cyl(0.135, 0.090, 10),
		Transform3D(Basis.IDENTITY, top), AssayerMaterials.C_IRON_L)
	for anchor in [2.10, 4.05, -CW_LEN * 0.95]:
		var p := Vector3(anchor, BOOM_Y + (0.19 if anchor > 0.0 else 0.17), 0)
		for zs in [-0.115, 0.115]:
			var a: Vector3 = top + Vector3(0, 0, zs)
			var d: Vector3 = p - a
			mb.add_prim(mats.steel, MeshKit.cyl(0.026, d.length(), 6),
				Transform3D(MeshKit.along(d), (a + p) * 0.5),
				AssayerMaterials.C_STEEL)
			# a turnbuckle two thirds along: these were tensioned by hand
			mb.add_prim(mats.iron, MeshKit.cyl(0.046, 0.190, 6),
				Transform3D(MeshKit.along(d), a + d * 0.68), C)


# --- THE HAMMER ------------------------------------------------------------
# THE-MACHINERY 2.1: "hexagonal ring 2.0 across, riding the mast; its z is the
# animated variable". ART-DIRECTION 5.1: 1.2 m hex ring, 100 mm wall, 600 mm
# deep, grey cast iron, about 1.6 t. CONCEPT 6: "K 14 . 2" raised on it -- the
# second part of assembly K 14, which is the whole index system in two marks.
func _hammer(mb: MeshKit.MB) -> void:
	var C := AssayerMaterials.C_IRON
	var CL := AssayerMaterials.C_IRON_L
	MeshKit.prism_ring(mb, mats.iron, C, 6, HAMMER_AF, 1.020, 0.0, HAMMER_H)
	# the strike face: bearing steel, and the only face on the machine that is
	# hit sixty times an hour
	MeshKit.prism_ring(mb, mats.steel, AssayerMaterials.C_RACE, 6, HAMMER_AF - 0.030, 1.050,
		-0.012, 0.010)
	# A flange top and bottom -- the casting's own stiffening, and the top one
	# in BEARING STEEL. That is not decoration. The only light on this machine
	# during the wind is 1.7 m ABOVE the hammer's top of travel, so the top
	# flange is the one surface on the moving part squarely facing the source,
	# and making it the shiny age of iron is what turns the hammer from a bulge
	# on the mast into a countable mark. It is also true: the top flange is
	# what the guide shoes and the pawl gear bear on, so it is rubbed.
	MeshKit.prism_ring(mb, mats.steel, AssayerMaterials.C_RACE, 6,
		HAMMER_AF + 0.180, 1.020, HAMMER_H - 0.055, HAMMER_H)
	MeshKit.prism_ring(mb, mats.iron, CL, 6, HAMMER_AF + 0.140, 1.020,
		HAMMER_H - 0.150, HAMMER_H - 0.055)
	MeshKit.prism_ring(mb, mats.iron, C, 6, HAMMER_AF + 0.050, 1.020, 0.0, 0.060)
	# four lifting ears cast into the top flange
	for e in range(4):
		var ea: float = TAU * float(e) / 4.0 + 0.39
		var en := Vector3(cos(ea), 0, sin(ea))
		mb.add_prim(mats.iron, MeshKit.box(0.075, 0.130, 0.190),
			Transform3D(MeshKit.face(en), en * 0.760 + Vector3(0, HAMMER_H + 0.045, 0)), CL)
	# six vertical webs, one on each flat
	for f in range(6):
		var fa: float = TAU * (float(f) + 0.5) / 6.0
		var nrm := Vector3(cos(fa), 0, sin(fa))
		mb.add_prim(mats.iron, MeshKit.box(0.110, HAMMER_H - 0.170, 0.045),
			Transform3D(MeshKit.face(nrm), nrm * (HAMMER_AF * 0.5 + 0.020)
				+ Vector3(0, HAMMER_H * 0.5, 0)), C)
	# THE GUIDE SHOES: what it rides the mast on. Bearing steel, six of them.
	for f2 in range(6):
		var fa2: float = TAU * (float(f2) + 0.5) / 6.0
		var nrm2 := Vector3(cos(fa2), 0, sin(fa2))
		for yy in [0.090, HAMMER_H - 0.090]:
			mb.add_prim(mats.steel, MeshKit.box(0.170, 0.070, 0.035),
				Transform3D(MeshKit.face(-nrm2), nrm2 * (0.510) + Vector3(0, yy, 0)),
				AssayerMaterials.C_STEEL)
	# THE PAWL HOUSING on the +X face -- where the chain and the ratchet meet
	pawl = Node3D.new()
	mb.add_prim(mats.iron, MeshKit.box(0.260, 0.330, 0.240),
		Transform3D(Basis.IDENTITY, Vector3(HAMMER_AF * 0.5 + 0.10, HAMMER_H * 0.62, 0)), C)
	mb.add_prim(mats.steel, MeshKit.box(0.070, 0.190, 0.060),
		Transform3D(Basis.from_euler(Vector3(0, 0, -0.42)),
			Vector3(HAMMER_AF * 0.5 - 0.03, HAMMER_H * 0.62 + 0.02, 0)),
		AssayerMaterials.C_STEEL)
	# the chain shackle on top of the housing
	mb.add_prim(mats.steel, MeshKit.cyl(0.052, 0.120, 8),
		Transform3D(Basis.from_euler(Vector3(0, 0, PI * 0.5)),
			Vector3(HAMMER_AF * 0.5 + 0.10, HAMMER_H * 0.62 + 0.200, 0)),
		AssayerMaterials.C_STEEL)
	# THE INDEX MARK, second half. "K 14 . 2" -- part two of assembly K 14.
	var mn := Vector3(cos(TAU / 3.0), 0, sin(TAU / 3.0))
	var mt := Transform3D(MeshKit.face(mn), mn * (HAMMER_AF * 0.5 - 0.002)
		+ Vector3(0, HAMMER_H * 0.30, 0))
	mb.add_prim(mats.iron, MeshKit.box(0.560, 0.190, 0.008),
		mt * Transform3D(Basis.IDENTITY, Vector3(0.13, 0.070, 0.004)), CL)
	MeshKit.lettering(mb, mats.iron, CL, "K 14 . 2",
		mt * Transform3D(Basis.IDENTITY, Vector3(-0.11, 0.0, 0.008)), 0.140, 0.010, 0.022)


# --- THE HEADER TANK and THE SIGHT GLASS -----------------------------------
# CONCEPT 4 and 5. THE-MACHINERY 7: "the water that drowned the mine is the
# water that fills the Assayer's header tank -- the mine's failure is the
# machine's power supply". The tank is the countdown's second clock, and it is
# only a clock if the level shows, which is what the glass is for.
func _tank(mb: MeshKit.MB) -> void:
	var C := AssayerMaterials.C_IRON
	var CL := AssayerMaterials.C_IRON_L
	var c := Vector3(0, 0, TANK_OFF)
	MeshKit.prism(mb, mats.iron, C, 16, TANK_R * 2.0, TANK_R * 2.0 - 0.030,
		TANK_Y0, TANK_Y1, c, 0.0, true, false)
	# a domed top, riveted on
	mb.add_prim(mats.iron, MeshKit.taper(0.180, TANK_R - 0.010, 0.230, 16),
		Transform3D(Basis.IDENTITY, c + Vector3(0, TANK_Y1 + 0.115, 0)), C)
	# three hoop bands with rivets: it is a riveted vessel, not a moulding
	for yb in [TANK_Y0 + 0.18, (TANK_Y0 + TANK_Y1) * 0.5, TANK_Y1 - 0.18]:
		MeshKit.prism_ring(mb, mats.iron, CL, 16, TANK_R * 2.0 + 0.060, TANK_R * 2.0 - 0.010,
			yb - 0.040, yb + 0.040, c)
		for i in range(16):
			var a: float = TAU * (float(i) + 0.5) / 16.0
			mb.add_prim(mats.iron, MeshKit.sph(0.026, 6),
				Transform3D(Basis.IDENTITY,
					c + Vector3(cos(a) * (TANK_R + 0.030), yb, sin(a) * (TANK_R + 0.030))), CL)
	# the bracket: a cast knee off the mast, two members and a web
	for zs in [-0.34, 0.34]:
		var a0 := Vector3(zs, TANK_Y0 + 0.10, -MAST_AF * 0.5)
		var a1 := Vector3(zs, TANK_Y0 + 0.10, TANK_OFF + TANK_R * 0.6)
		var d: Vector3 = a1 - a0
		mb.add_prim(mats.iron, MeshKit.box(0.110, 0.150, d.length()),
			Transform3D(Basis.IDENTITY, (a0 + a1) * 0.5), C)
		MeshKit.web(mb, mats.iron, C, a0 + Vector3(0, -0.06, 0), a1 + Vector3(0, -0.06, 0),
			a0 + Vector3(0, -0.62, 0.10), 0.045)
		# a diagonal brace up to the mast: the tank is 1.2 t of water
		var b0: Vector3 = a1 + Vector3(0, -0.02, 0)
		var b1 := Vector3(zs * 0.5, TANK_Y1 - 0.10, -MAST_AF * 0.45)
		var d2: Vector3 = b1 - b0
		mb.add_prim(mats.iron, MeshKit.cyl(0.038, d2.length(), 6),
			Transform3D(MeshKit.along(d2), (b0 + b1) * 0.5), C)
	# THE SIGHT GLASS: two cast bosses, a guard, and the tube between them
	var gx: float = TANK_R + 0.100
	var gz: float = TANK_OFF
	for yy in [GLASS_Y0, GLASS_Y1]:
		mb.add_prim(mats.iron, MeshKit.box(0.230, 0.130, 0.180),
			Transform3D(Basis.IDENTITY, Vector3(gx - 0.06, yy, gz)), CL)
		mb.add_prim(mats.iron, MeshKit.cyl(0.042, 0.090, 8),
			Transform3D(Basis.IDENTITY, Vector3(gx, yy, gz)), C)
	# the guard rods either side, so a passing shovel does not break it
	for zs2 in [-0.085, 0.085]:
		mb.add_prim(mats.iron, MeshKit.cyl(0.014, GLASS_Y1 - GLASS_Y0, 5),
			Transform3D(Basis.IDENTITY,
				Vector3(gx + 0.020, (GLASS_Y0 + GLASS_Y1) * 0.5, gz + zs2)), C)


# --- THE PIPES -------------------------------------------------------------
# CONCEPT 5: the feed climbs out of frame toward the workings above, the
# downpipe runs to the anvil's drip joint, a second pipe to the motor at the
# winch. That is the whole power train and it is three pipe runs.
func _pipes(mb: MeshKit.MB) -> void:
	var C := AssayerMaterials.C_IRON
	var c := Vector3(0, 0, TANK_OFF)
	# THE RISING MAIN -- the mine's failure arriving as the machine's supply.
	# It goes up into the dark and is never explained, which is the point.
	MeshKit.pipe(mb, mats.iron, C, PackedVector3Array([
		c + Vector3(0.20, TANK_Y1 + 0.20, 0.10),
		c + Vector3(0.20, 4.90, 0.10),
		c + Vector3(0.20, 5.60, -0.85),
		c + Vector3(0.20, 8.60, -1.90),
		c + Vector3(0.20, 11.30, -2.30)]), 0.078)
	# the bracket that holds it off the wall of nothing
	mb.add_prim(mats.iron, MeshKit.box(0.320, 0.070, 0.070),
		Transform3D(Basis.IDENTITY, c + Vector3(0.20, 4.60, 0.10)), C)
	# THE MOTOR LINE: tank top to the water motor at the head
	MeshKit.pipe(mb, mats.iron, C, PackedVector3Array([
		c + Vector3(-0.26, TANK_Y1 + 0.16, 0.04),
		Vector3(-0.26, 4.60, TANK_OFF + 0.30),
		Vector3(-0.26, 5.70, -0.62),
		Vector3(-0.20, MAST_TOP - 0.62, -0.60),
		Vector3(-0.05, MAST_TOP - 0.42, -0.52)]), 0.056)
	# THE DOWNPIPE to the drip joint over the anvil. One drip every two seconds
	# onto the strike face is the entire dormant performance (ART-DIRECTION 5.4)
	MeshKit.pipe(mb, mats.iron, C, PackedVector3Array([
		c + Vector3(0.32, TANK_Y0 + 0.06, 0.20),
		Vector3(0.32, 1.86, TANK_OFF + 0.55),
		Vector3(0.32, 1.62, -0.10),
		Vector3(0.34, 1.46, 0.02)]), 0.046)
	# the joint itself: a flanged union, and it is the one that leaks
	mb.add_prim(mats.iron, MeshKit.cyl(0.082, 0.055, 10),
		Transform3D(Basis.IDENTITY, Vector3(0.34, 1.430, 0.02)),
		AssayerMaterials.C_IRON_L)
	mb.add_prim(mats.iron, MeshKit.cyl(0.030, 0.090, 8),
		Transform3D(Basis.IDENTITY, Vector3(0.34, 1.375, 0.02)), C)


# --- THE OLD SERVICE PLATFORM ----------------------------------------------
# THE-MACHINERY 2.1: "8 markers at r = 3.4 -- the old service platform".
# CONCEPT 8: eight stanchions with four of eight grating bays left. The four
# that are gone are the reason it reads as OLD rather than as furniture: a
# complete platform is maintenance, half a platform is a century.
func _platform(mb: MeshKit.MB) -> void:
	var C := AssayerMaterials.C_IRON
	var CL := AssayerMaterials.C_IRON_L
	var lr := RandomNumberGenerator.new()
	lr.seed = seedv * 31 + 7
	var keep := [true, true, false, true, false, false, true, false]
	# and one of the four missing bays did not vanish: it is lying on the floor
	# under the gap it came out of, which is the difference between a platform
	# somebody dismantled and a platform that fell down.
	var fa: float = TAU * 4.0 / 8.0 + 0.19
	var fp := Vector3(cos(fa + 0.40) * (PLATFORM_R + 0.95), 0.050,
					  sin(fa + 0.40) * (PLATFORM_R + 0.95))
	var fb: Basis = Basis.from_euler(Vector3(0.06, -fa + 0.55, 0.10))
	for k in range(7):
		mb.add_prim(mats.iron, MeshKit.box(0.014, 0.045, 1.44),
			Transform3D(fb, fp + fb * Vector3(-0.30 + 0.10 * float(k), 0, 0)),
			AssayerMaterials.C_IRON_L)
	for bo2 in [-0.34, 0.34]:
		mb.add_prim(mats.iron, MeshKit.box(0.055, 0.075, 1.50),
			Transform3D(fb, fp + fb * Vector3(bo2, -0.045, 0)), C)
	for i in range(8):
		var a: float = TAU * float(i) / 8.0 + 0.19
		var p := Vector3(cos(a) * PLATFORM_R, 0.0, sin(a) * PLATFORM_R)
		mb.add_prim(mats.iron, MeshKit.box(0.280, 0.055, 0.280),
			Transform3D(Basis.from_euler(Vector3(0, -a, 0)), p + Vector3(0, 0.028, 0)), C)
		for bx in [-0.090, 0.090]:
			for bz in [-0.090, 0.090]:
				MeshKit.bolt(mb, mats.steel, AssayerMaterials.C_STEEL,
					p + Basis.from_euler(Vector3(0, -a, 0)) * Vector3(bx, 0, bz)
						+ Vector3(0, 0.055, 0), Vector3.UP, 0.024)
		# the stanchion, leaning a little: a century of shock has moved them
		var lean: float = (lr.randf() - 0.5) * 0.075
		var topp: Vector3 = p + Vector3(sin(lean) * PLATFORM_Y * cos(a),
			PLATFORM_Y, sin(lean) * PLATFORM_Y * sin(a))
		var d: Vector3 = topp - (p + Vector3(0, 0.055, 0))
		mb.add_prim(mats.iron, MeshKit.cyl(0.052, d.length(), 8),
			Transform3D(MeshKit.along(d), (p + Vector3(0, 0.055, 0) + topp) * 0.5), C)
		# the bearer that the grating sat on, whether or not the grating is left
		var a2: float = TAU * float((i + 1) % 8) / 8.0 + 0.19
		var q := Vector3(cos(a2) * PLATFORM_R, PLATFORM_Y, sin(a2) * PLATFORM_R)
		if keep[i]:
			var dd: Vector3 = q - topp
			for bo in [-0.30, 0.30]:
				var offv: Vector3 = (topp + q).normalized() * bo
				mb.add_prim(mats.iron, MeshKit.box(0.055, 0.075, dd.length()),
					Transform3D(Basis.looking_at(dd.normalized(), Vector3.UP),
						(topp + q) * 0.5 + offv + Vector3(0, -0.040, 0)), C)
			# the grating: seven bars on edge, which is what grating IS
			for k in range(7):
				var f: float = -0.30 + 0.10 * float(k)
				var offv2: Vector3 = (topp + q).normalized() * f
				mb.add_prim(mats.iron, MeshKit.box(0.014, 0.045, dd.length() * 0.94),
					Transform3D(Basis.looking_at(dd.normalized(), Vector3.UP),
						(topp + q) * 0.5 + offv2), CL)
			# a handrail on the bays that survive
			var hr: Vector3 = topp + Vector3(0, 0.52, 0)
			var hq: Vector3 = q + Vector3(0, 0.52, 0)
			var dh: Vector3 = hq - hr
			mb.add_prim(mats.iron, MeshKit.cyl(0.020, dh.length(), 5),
				Transform3D(MeshKit.along(dh), (hr + hq) * 0.5), C)
			mb.add_prim(mats.iron, MeshKit.cyl(0.024, 0.52, 5),
				Transform3D(Basis.IDENTITY, topp + Vector3(0, 0.26, 0)), C)


# --- THE STAYS THAT DO NOT TURN --------------------------------------------
# Guys from the mast to the rock. THE-MACHINERY says the machine is "bolted
# into the bedrock"; four guys at 45 degrees is how a mast is actually held,
# and they are the only part of the object that touches the chamber.
func _stays_fixed(mb: MeshKit.MB) -> void:
	var C := AssayerMaterials.C_IRON
	for i in range(4):
		var a: float = TAU * float(i) / 4.0 + 0.42
		var top := Vector3(cos(a) * 0.56, 4.980, sin(a) * 0.56)
		var anch := Vector3(cos(a) * 4.60, 0.16, sin(a) * 4.60)
		var d: Vector3 = anch - top
		mb.add_prim(mats.iron, MeshKit.cyl(0.020, d.length(), 5),
			Transform3D(MeshKit.along(d), (top + anch) * 0.5), C)
		mb.add_prim(mats.iron, MeshKit.cyl(0.042, 0.200, 6),
			Transform3D(MeshKit.along(d), top + d * 0.30), C)
		# the ground anchor: a plate grouted into the rock
		mb.add_prim(mats.iron, MeshKit.box(0.300, 0.070, 0.220),
			Transform3D(Basis.from_euler(Vector3(0, -a, 0)), anch + Vector3(0, -0.10, 0)), C)


# --- the two scaled bars ---------------------------------------------------
# The chain and the water column are the only two parts whose SHAPE changes,
# and both change by a scale on one axis of a unit mesh. Still no rebuild.
func _chain_and_column() -> void:
	var cm := MeshKit.MB.new()
	# a unit chain: 1 m long, origin at the top, hanging down -Y
	var n: int = 26
	for i in range(n):
		var y: float = -(float(i) + 0.5) / float(n)
		var rot: float = PI * 0.5 * float(i % 2)
		cm.add_prim(mats.steel, MeshKit.cyl(0.0165, 1.0 / float(n) * 1.35, 6),
			Transform3D(Basis.from_euler(Vector3(0, rot, 0)).scaled(Vector3(1, 1, 0.42)),
				Vector3(0, y, 0)), AssayerMaterials.C_STEEL)
	chain = MeshInstance3D.new()
	chain.mesh = cm.commit()
	chain.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	body.add_child(chain)
	stat_tris += cm.tri_count()

	var wm := MeshKit.MB.new()
	# a unit water column: 1 m tall, origin at the BOTTOM, so scaling Y is the
	# level and nothing has to move.
	wm.add_prim(mats.water, MeshKit.cyl(0.031, 1.0, 10),
		Transform3D(Basis.IDENTITY, Vector3(0, 0.5, 0)), Color(1, 1, 1))
	column = MeshInstance3D.new()
	column.mesh = wm.commit()
	column.position = Vector3(TANK_R + 0.100, GLASS_Y0, TANK_OFF)
	column.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	body.add_child(column)
	stat_tris += wm.tri_count()

	# the glass itself is static and always there
	var gm := MeshKit.MB.new()
	gm.add_prim(mats.glass, MeshKit.cyl(0.040, GLASS_Y1 - GLASS_Y0, 12),
		Transform3D(Basis.IDENTITY, Vector3(0, (GLASS_Y1 - GLASS_Y0) * 0.5, 0)), Color(1, 1, 1))
	var gi := MeshInstance3D.new()
	gi.mesh = gm.commit()
	gi.position = Vector3(TANK_R + 0.100, GLASS_Y0, TANK_OFF)
	gi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	body.add_child(gi)
	stat_tris += gm.tri_count()


# --- THE TWO HOT POINTS ----------------------------------------------------
# ART-DIRECTION 5.4, and it is the measured half of that section: a source at
# the mast head is a BEACON -- it lifts 20.6% of the frame and 6.8% of the
# floor half -- so it cannot be the only one, and the second goes at the anvil
# block at the mast foot, which is where the friction is and at the height that
# lights a floor. The mast between them is lit by its own hot points and by
# nothing else.
func _emitters() -> void:
	var dc := Vector3(0.0, MAST_TOP - 0.300, 0.560)
	# the brake band, as an emissive ring round the drum
	var bm := MeshKit.MB.new()
	MeshKit.prism_ring(bm, mats.hot_winch, Color(1, 1, 1), 20, 0.700, 0.610, -0.170, 0.170)
	winch_glow = MeshInstance3D.new()
	winch_glow.mesh = bm.commit()
	winch_glow.transform = Transform3D(Basis.from_euler(Vector3(0, 0, PI * 0.5)), dc)
	winch_glow.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	body.add_child(winch_glow)
	stat_tris += bm.tri_count()

	# MEASURED, and this is the bug that made the passage frame black and the
	# whole chamber read two stops under. ART-DIRECTION 5.4 says "the lights
	# are point sources BESIDE the emitters, not inside the mast", and the
	# first build put this one at the drum's own centre -- 0.10 m from the axis
	# of a 0.29 m drum with capped ends and two 0.36 m flanges, so the source
	# was sealed inside a casting and every shadow-casting surface in the room
	# was shadowed by it. No amount of shadow bias fixes a light inside a box:
	# 0.06, 0.14 and 0.30 were all swept and all identical, which is what said
	# it was occlusion and not acne. It now sits 0.40 m above the drum axis,
	# clear of the band, the flanges, the head casting and the crown.
	winch_light = OmniLight3D.new()
	winch_light.position = dc + Vector3(0, 0.40, 0.0)
	# ART-DIRECTION 2.3: "the falloff is the style. Do not compress the ramp."
	# At attenuation 1.5 one source lit the whole 21 m chamber and the far wall
	# came back at 18.8% legible -- a lit level, not a mine. 2.4 is the number
	# that keeps the machine's own ground lit and puts the far wall under 0.02.
	winch_light.omni_range = 20.0
	# 2.0 is INVERSE SQUARE, which is what a point source does and therefore
	# what ART-DIRECTION 2.3's "do not compress the ramp" means for one. Godot
	# defaults an omni to 1.0, which is 1/d and flat enough to light a whole
	# chamber; 2.4 was tried and is steeper than physics, and put every in-situ
	# frame under the legibility floor at once. The energy is re-derived against
	# it by measurement (see NOTES.md, the calibration table).
	winch_light.omni_attenuation = 2.0
	winch_light.shadow_enabled = true
	winch_light.shadow_bias = 0.055
	winch_light.shadow_normal_bias = 2.0
	winch_light.light_specular = 1.0
	body.add_child(winch_light)

	# the anvil ring: a thin emitter on the strike face at a third the output
	var am := MeshKit.MB.new()
	MeshKit.prism_ring(am, mats.hot_anvil, Color(1, 1, 1), 24, 1.330, 0.600,
		ANVIL_TOP - 0.004, ANVIL_TOP + 0.008)
	anvil_glow = MeshInstance3D.new()
	anvil_glow.mesh = am.commit()
	anvil_glow.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	body.add_child(anvil_glow)
	stat_tris += am.tri_count()

	# THE ANVIL SOURCE IS A RING, and it has to be built as one.
	#
	# ART-DIRECTION 5.4 asks for "a second source at the anvil block at the mast
	# foot ... at the height that lights a floor", and 5.2 puts a raised index
	# mark on that block which TRAILER 10 requires to be legible in shot 24
	# "without being pointed at". A single point at the ring's centre satisfies
	# neither: it sits inside the mast, and every vertical face of the anvil --
	# including both K 14 faces -- has a normal pointing AWAY from it, so the
	# mark rendered as a flat black panel. Measured: N.L on the K 14 face from
	# an axial source at y 1.14 is -0.92.
	#
	# Six shadowless points on a 1.05 m ring at 60-degree spacing, each at a
	# sixth of the output. The K 14 faces look down 0 and 120 degrees and the
	# lights stand at 30, 90, 150, ..., so they light the floor evenly and none
	# of them stands in the mast. They do not cast shadows, because a ring has
	# no single shadow and a point at its centre would black out the floor it
	# exists to light.
	#
	# NOTE WHAT THIS RING DOES NOT LIGHT, because it decides where the marks
	# go. At r = 0.62 the ring sits INSIDE the anvil's own chamfer, so N.L on
	# the chamfer is -0.22 and on the vertical flat below it -0.46: the block
	# lights the floor and not itself. The chamfer mark is read by the WINCH
	# HEAD 5.7 m up, which rakes it at N.L = 0.44 -- the best raking angle
	# anywhere on the machine, and why the mark is there. The flat mark below
	# is read by nothing the machine owns, and is for a visitor's work lamp.
	for i in range(6):
		var a: float = TAU * (float(i) + 0.5) / 6.0
		var ol := OmniLight3D.new()
		ol.position = Vector3(cos(a) * 0.62, ANVIL_TOP + 0.05, sin(a) * 0.62)
		ol.omni_range = 12.0
		ol.omni_attenuation = 2.0
		ol.shadow_enabled = false
		body.add_child(ol)
		anvil_lights.append(ol)


# --- THE DRIP --------------------------------------------------------------
# "One drip every two seconds onto the anvil is the entire dormant performance,
#  and a machine that emits nothing while water runs off it reads as FINISHED
#  rather than menacing."   ART-DIRECTION 5.4
func _drip() -> void:
	drip = GPUParticles3D.new()
	var pm := ParticleProcessMaterial.new()
	pm.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_SPHERE
	pm.emission_sphere_radius = 0.010
	pm.direction = Vector3(0, -1, 0)
	pm.spread = 1.0
	pm.initial_velocity_min = 0.05
	pm.initial_velocity_max = 0.12
	pm.gravity = Vector3(0, -9.8, 0)
	pm.scale_min = 0.8
	pm.scale_max = 1.1
	var dm := StandardMaterial3D.new()
	dm.albedo_color = Color(0.62, 0.66, 0.66, 0.80)
	dm.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	dm.shading_mode = BaseMaterial3D.SHADING_MODE_PER_PIXEL
	dm.roughness = 0.05
	dm.metallic = 0.0
	var dq := SphereMesh.new()
	dq.radius = 0.011
	dq.height = 0.030
	dq.radial_segments = 6
	dq.rings = 3
	dq.material = dm
	drip.process_material = pm
	drip.draw_pass_1 = dq
	drip.amount = 3
	drip.lifetime = 2.0            # one drip every two seconds, exactly
	drip.explosiveness = 0.94
	drip.position = Vector3(0.34, 1.360, 0.02)
	body.add_child(drip)


# ===========================================================================
# THE CYCLE -- one clock, everything derived
#
# THE-MACHINERY 3:
#   p  0 - 54   listening   a still machine, one drip, nothing emitted
#   p 54 - 57   the slew    the boom swings 36 deg and stops, pointing
#   p 57 - 62   locked      five seconds of stillness after a movement
#   p 62 - 71   the wind    nine clicks, one per second; 1900 K -> 2400 K;
#                           the tank draws down one ninth per click
#   p 71.00-71.15  the fire hammer falls the whole travel in three frames;
#                           4000 K at 4x; the rig jolts 0.4 cells and recoils
#   p 71 - 75   lethal      decay over 8 s as the brake cools
# ===========================================================================
func set_phase(p: float) -> void:
	p = fposmod(p, PERIOD)
	last_p = p

	# --- the aim -----------------------------------------------------------
	# The boom eases from this cycle's bearing to the next over the three
	# seconds of the slew, and holds. -36 deg per cycle, always the same way,
	# which is what makes it learnable from two slews.
	var a_from: float = aim_deg
	var a_to: float = aim_deg + AIM_STEP_DEG
	var slew_f: float = 0.0
	if p >= SLEW_AT:
		slew_f = clampf((p - SLEW_AT) / SLEW_S, 0.0, 1.0)
		slew_f = slew_f * slew_f * (3.0 - 2.0 * slew_f)     # ease, it has mass
	var shown: float = lerp(a_from, a_to, slew_f)
	turret.rotation.y = -deg_to_rad(shown)

	# --- the hammer --------------------------------------------------------
	var hy: float = ANVIL_TOP
	var clicks: int = 0
	if p >= WIND_AT and p < FIRE_AT:
		clicks = clampi(int(floor(p - WIND_AT)) + 1, 0, CLICKS)
		# a ratchet click is a step, not a ramp: the pawl drops into the next
		# tooth and the load comes on. 120 ms of travel, then it is held.
		var frac: float = fposmod(p - WIND_AT, 1.0)
		var step: float = clampf(frac / 0.12, 0.0, 1.0)
		step = step * step * (3.0 - 2.0 * step)
		var lo: float = float(clicks - 1) / float(CLICKS)
		var hi: float = float(clicks) / float(CLICKS)
		hy = ANVIL_TOP + (HAMMER_TOP - ANVIL_TOP) * lerp(lo, hi, step)
	elif p >= FIRE_AT and p < FIRE_AT + FALL_S:
		clicks = CLICKS
		# the fall: free, so it is quadratic in time, not linear
		var ff: float = (p - FIRE_AT) / FALL_S
		hy = HAMMER_TOP - (HAMMER_TOP - ANVIL_TOP) * clampf(ff * ff, 0.0, 1.0)
	elif p >= FIRE_AT + FALL_S:
		clicks = 0
		hy = ANVIL_TOP
	clicks_done = clicks
	hammer.position.y = hy

	# --- the chain ---------------------------------------------------------
	# from the sheave to the shackle on the pawl housing. One scale on Y.
	var shackle := Vector3(HAMMER_AF * 0.5 + 0.10, hy + HAMMER_H * 0.62 + 0.200, 0)
	var top: Vector3 = _sheave_p + Vector3(0, -0.02, 0)
	var span: float = maxf(0.05, top.y - shackle.y)
	chain.position = Vector3(shackle.x, top.y, shackle.z)
	chain.scale = Vector3(1, span, 1)

	# --- the tank ----------------------------------------------------------
	# CONCEPT design problem 3, built as the doc implies rather than papered
	# over: the tank draws down one ninth per click across the nine seconds of
	# the wind, and refills over the other sixty-six. So the sight glass is
	# RISING for 88% of the cycle -- a second, slow countdown a viewer can read
	# from the floor, and the reason the period is seventy-five seconds.
	if p >= WIND_AT and p < FIRE_AT:
		tank_fill = 1.0 - float(clicks) / float(CLICKS)
	elif p >= FIRE_AT:
		tank_fill = (p - FIRE_AT) / (PERIOD - FIRE_AT + WIND_AT)
	else:
		tank_fill = (p + PERIOD - FIRE_AT) / (PERIOD - FIRE_AT + WIND_AT)
	tank_fill = clampf(tank_fill, 0.0, 1.0)
	if spent:
		tank_fill = 0.0
	column.scale = Vector3(1, maxf(0.001, tank_fill * (GLASS_Y1 - GLASS_Y0)), 1)

	# --- the light ---------------------------------------------------------
	var kelvin: float = K_WIND_LO
	var out: float = 0.0
	if p >= WIND_AT and p < FIRE_AT:
		# THE COLOUR is concept proposal 7's, which is what the concept renders
		# were made with: click n of 9 is 1900 + 500*n/9 K.
		kelvin = K_WIND_LO + (K_WIND_HI - K_WIND_LO) * float(clicks) / float(CLICKS)
		# THE OUTPUT is NOT n/9. ART-DIRECTION 5.4 says "ramping 0 -> full in
		# nine discrete one-second steps", and built literally that put click 1
		# at 0.18% of the frame above the legibility threshold -- an invisible
		# first click cannot be counted, and the countdown is the whole point.
		# THE-MACHINERY 3 already fixes the right law for the same nine seconds
		# on the acoustic side: "strength 0.3 -> 1.0 -- exactly what
		# ancient.signature_strength() already returns, and now it is the winch
		# taking load". The light is the same winch taking the same load, so it
		# uses the same ramp. Measured: click 1 goes 0.18% -> 2.6% legible.
		out = 0.30 + 0.70 * float(clicks) / float(CLICKS)
	elif p >= FIRE_AT:
		var since: float = p - FIRE_AT
		if since < FALL_S:
			kelvin = K_STRIKE
			out = STRIKE_GAIN
		else:
			# the decay: the brake cools, and the colour falls with the output
			# because a cooling body does both at once
			var d: float = clampf((since - FALL_S) / DECAY_S, 0.0, 1.0)
			out = STRIKE_GAIN * pow(1.0 - d, 2.4)
			kelvin = lerp(K_STRIKE, K_WIND_LO - 200.0, sqrt(d))
	else:
		# the tail of the last cycle's decay, running into the quiet
		var since2: float = p + PERIOD - FIRE_AT
		var d2: float = clampf((since2 - FALL_S) / DECAY_S, 0.0, 1.0)
		if d2 < 1.0:
			out = STRIKE_GAIN * pow(1.0 - d2, 2.4)
			kelvin = lerp(K_STRIKE, K_WIND_LO - 200.0, sqrt(d2))
	if spent:
		out = 0.0
	_set_hot(kelvin, out)

	# --- the recoil --------------------------------------------------------
	# THE-MACHINERY 3: "the rig jolts down 0.4 cells and recoils over 0.5 s".
	var jolt: float = 0.0
	if p >= FIRE_AT:
		var s: float = p - FIRE_AT
		if s < FALL_S:
			jolt = 0.0
		elif s < FALL_S + 0.5:
			var u: float = (s - FALL_S) / 0.5
			jolt = -0.4 * CELL * (1.0 - u) * cos(u * PI * 3.0) * exp(-u * 2.2)
	body.position.y = jolt

	# the drip stops while it is working: the tank is feeding the motor
	drip.emitting = (p < WIND_AT or p > FIRE_AT + 2.0) and not spent


func _set_hot(kelvin: float, out: float) -> void:
	out *= hot_scale
	var col: Color = AssayerMaterials.blackbody(kelvin)
	# The emissive surface and the point source beside it are driven together
	# and from the same numbers, so the band never glows without lighting
	# anything and never lights without glowing.
	mats.hot_winch.emission = col
	mats.hot_winch.emission_energy_multiplier = out * 9.5
	mats.hot_anvil.emission = col
	mats.hot_anvil.emission_energy_multiplier = out * 9.5 * ANVIL_FRACTION
	winch_light.light_color = col
	winch_light.light_energy = out * hot_energy
	winch_light.visible = out > 0.002
	for ol in anvil_lights:
		ol.light_color = col
		ol.light_energy = out * hot_energy * ANVIL_FRACTION / 6.0
		ol.visible = out > 0.002


# advance the survey: called once per cycle boundary by the clock
func advance_cycle() -> void:
	last_fired_aim = aim_deg
	aim_deg = fposmod(aim_deg + AIM_STEP_DEG, 360.0)
	cycle += 1
	fired_once = true
