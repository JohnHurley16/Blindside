# ---------------------------------------------------------------------------
# BLINDSIDE machines spike -- the numbers, and where each one comes from.
#
# The GEOMETRY now arrives from agent_model as .glb, so nothing here describes
# a shape. What is left is the handful of numbers Godot still has to know: how
# big each chassis is (to frame it), how fast its clip walks (to move the node
# at exactly the speed the baked feet expect), and the palette.
#
# Chassis dimensions are transcribed verbatim from `agent_model/params.py`.
# ---------------------------------------------------------------------------
class_name Book
extends RefCounted

# --- ART-DIRECTION 4.2 / 4.3 palette. sRGB hexes, linearised at use. --------
# The vision board used these as LINEAR values and said so (its guess 3); this
# spike linearises, which is why BONE reads a little deeper here than there.
const BONE := Color(0.949, 0.902, 0.824)      # #F2E6D2  player
const EMBER := Color(1.000, 0.478, 0.184)     # #FF7A2F  rival
const HURT := Color(0.878, 0.435, 0.376)      # #E06F60  hurt and alive
const KILL := Color(1.000, 0.231, 0.188)      # #FF3B30  dying. No second red.
const WARM_DIM := Color(0.85, 0.72, 0.55)     # old bulbs, not a casualty
const LAMP := Color(1.00, 0.98, 0.95)         # ART 2.1/2.5: white, EVERY team

# params.py's Skin, minus the two colours ART 2.5 retires (the cyan work lamp
# and the red salvage light).
const PALE := Color(0.62, 0.60, 0.55)         # top shell: pale, reads in the dark
const GRAPHITE := Color(0.05, 0.055, 0.065)   # lower body and blades
const ACCENT := Color(0.85, 0.45, 0.10)
const BARE := Color(0.45, 0.45, 0.47)         # worn-through metal, hull grade
# ART 4.1's third finding, from getting it wrong first: THE LEG'S BARE COLOUR
# MUST STAY DARK. A muddy leg is mud ON black, not paint worn THROUGH to bright
# metal. The hull's bare colour on a leg makes it lighter, not dirtier.
const BARE_LEG := Color(0.115, 0.115, 0.125)
const MUD := Color(0.055, 0.042, 0.030)       # ART 4.1
const DUST := Color(0.30, 0.265, 0.215)       # ART 4.1: the ROCK's dust colour

# --- the four chassis -------------------------------------------------------
# hull  : (length, width, height), params.py, metres
# ride  : hull underside above ground at rest, params.py
# legs  : 4 or 6
# noise : params.py noise_label
# walk/trot speed: the speed the CLIP was baked at (export.sh), so the node has
#   to travel at exactly this or the planted feet will skate.
const CHASSIS := {
	"scout":    {"hull": Vector3(0.40, 0.15, 0.085), "ride": 0.25, "legs": 4, "noise": "quiet",
				 "walk": 0.50, "trot": 0.60, "job": "look, and do not be heard"},
	"surveyor": {"hull": Vector3(0.58, 0.21, 0.12),  "ride": 0.32, "legs": 4, "noise": "moderate",
				 "walk": 0.50, "trot": 0.60, "job": "the default; map and carry"},
	"hauler":   {"hull": Vector3(0.90, 0.32, 0.18),  "ride": 0.34, "legs": 6, "noise": "loud",
				 "walk": 0.50, "trot": 0.60, "job": "carry, on six legs, loudly"},
	"swimmer":  {"hull": Vector3(0.66, 0.18, 0.10),  "ride": 0.27, "legs": 4, "noise": "quiet",
				 "walk": 0.50, "trot": 0.60, "job": "below the waterline"},
}

const ORDER := ["scout", "surveyor", "hauler", "swimmer"]

# params.py's default_config(), verbatim -- what each class carries by default.
const LOADOUT := {
	"scout": {"eye": "optical", "side_l": "passive_acoustic", "side_r": "passive_acoustic",
			  "top_r": "structural_monitor"},
	"surveyor": {"face": "active_sonar", "eye": "optical", "top_m": "magnetometer",
				 "top_r": "beacon_rack", "side_l": "passive_acoustic",
				 "side_r": "passive_acoustic", "belly": "cargo_bay"},
	"hauler": {"face": "active_sonar", "eye": "optical", "top_0": "structural_monitor",
			   "top_1": "magnetometer", "top_2": "beacon_rack", "top_3": "beacon_rack",
			   "side_l": "passive_acoustic", "side_r": "passive_acoustic", "belly": "cargo_bay"},
	"swimmer": {"face": "active_sonar", "side_l": "passive_acoustic",
				"side_r": "passive_acoustic", "top_r": "beacon_rack", "belly": "cargo_bay"},
}

# --- the part index that came through the .glb in COLOR.a -------------------
# Must agree with agent_model/export_gltf.py PART_INDEX.
const P_SHELL := 0
const P_CHASSIS := 1
const P_ACCENT := 2
const P_METAL := 3
const P_DARK := 4
const P_CARBON := 5
const P_RUBBER := 6
const P_SONAR := 7
const P_EYE := 8
const P_LENS := 9
const P_GLASS := 10
const P_ESTOP := 11
const P_RETRO := 12
const P_PILOT := 13
const P_CAP := 14
const P_REFLECTOR := 15

# element ids carried in UV.x * 16, for the parts damage may shed
const E_HATCH_BATTERY := 9
const E_BELT_COVER := 10
const E_HATCH_COMPUTE := 11


static func hull_len(c: String) -> float:
	return float((CHASSIS[c]["hull"] as Vector3).x)


static func ride(c: String) -> float:
	return float(CHASSIS[c]["ride"])


# The height of the whole machine standing, head included. Used only for
# framing; measured off the imported mesh at load and cached there.
static func speed(c: String, clip: String) -> float:
	return float(CHASSIS[c].get(clip, 0.5))
