# ---------------------------------------------------------------------------
# BLINDSIDE -- the post stack, PIT-HEAD.  TRAILER.md 9, in the order given.
#
# Ported from spikes/godot/cave/postfx.gd. Every effect is a named bit so it can
# be turned on alone, measured alone, and shown before/after alone; `EFFECTS` is
# TRAILER 9's table and `apply()` is the whole configuration of the frame.
#
# THE RULE that keeps this from becoming a filter is unchanged: every effect
# must be defensible as something a real lens or sensor does, IN THIS LIGHT, at
# this scale. "In this light" is doing the work in this port -- the cave's
# tuning is tuning for one 54-degree lamp in a black room, and none of it
# transfers to a directional light over 170 x 148 m of yard under a sky.
#
# THREE STRUCTURAL DIFFERENCES FROM THE CAVE, all of them exposure hazards:
#
# 1. THE SCENE ALREADY OWNS `adjustment_*`. `weather.gd` runs AgX with
#    adjustment_contrast 1.06-1.15 and adjustment_saturation 1.10-1.14 per
#    lighting preset, because AgX desaturates hard and PHOTOREAL 1.5 technique
#    23 put it back there. The cave's postfx sets brightness/contrast/saturation
#    to 1.0 and owns the whole adjustment block.
#    HERE THE GRADE BIT OWNS ONLY THE LUT. If it owned the BCS as well, turning
#    the grade off would silently undo the photoreal pass and every "stack off"
#    reference frame in this directory would be a different picture from the one
#    in shots/. The grade's before/after pair is then exactly the LUT's
#    contribution, which is the pair the 14.3% bug was found in.
#
# 2. THE SCENE ALREADY OWNS `tonemap_exposure`, and it is different in every
#    preset: 0.70 overcast, 1.45 rain, 1.45 dusk. The cave's postfx pins it to
#    1.0. Doing that here would be a two-stop exposure change wearing a port's
#    costume -- exactly the failure ART-DIRECTION 2.9 exists to catch, and the
#    same shape as the LUT bug. This file never writes tonemap_exposure.
#
# 3. BLOOM HAS SUBJECTS HERE. The cave kept bloom at threshold 1.6 and measured
#    it changing 0.06% of the frame, because none of the things TRAILER 9 names
#    for bloom exist down there. Under a sky there is a cloud deck, a sun glow,
#    wet iron, standing water and, at dusk, fourteen floods and every amber
#    pilot on the site. The threshold is re-measured from scratch: see the sweep
#    in CINEMA.md 6.2.
# ---------------------------------------------------------------------------
extends RefCounted
class_name CinemaGrade

const E_TONEMAP: int = 1 << 0    # the transfer curve. Not optional; it IS the picture.
const E_BLOOM: int = 1 << 1      # veiling glare in the lens, off the strongest sources
const E_DOF: int = 1 << 2        # a lens has one focus plane; an eye does not
const E_MBLUR: int = 1 << 3      # the shutter is open for half a frame
const E_GRAIN: int = 1 << 4      # photon shot noise + the sensor read floor
const E_VIGNETTE: int = 1 << 5   # cos^4 falloff, from the focal length
const E_CA: int = 1 << 6         # lateral dispersion, at the frame edge
const E_DISTORT: int = 1 << 7    # sub-percent barrel on the wide lenses
const E_GRADE: int = 1 << 8      # one grade for the trailer -- the LUT only
const E_DIRT: int = 1 << 9       # the tenth row of TRAILER 9's table, and it is
                                 # the surface's to answer: "only on the surface,
                                 # only in rain, only on the strongest sources"

const NAMES := {
	"tonemap": E_TONEMAP, "bloom": E_BLOOM, "dof": E_DOF, "mblur": E_MBLUR,
	"grain": E_GRAIN, "vignette": E_VIGNETTE, "ca": E_CA, "distort": E_DISTORT,
	"grade": E_GRADE, "dirt": E_DIRT,
}
const ORDER := ["tonemap", "bloom", "dof", "mblur", "grain", "vignette", "ca",
	"distort", "grade", "dirt"]
const ALL: int = E_TONEMAP | E_BLOOM | E_DOF | E_MBLUR | E_GRAIN | E_VIGNETTE \
	| E_CA | E_DISTORT | E_GRADE | E_DIRT

var env: Environment
var attrs: CameraAttributesPractical
var lens: CinemaLens
var lut: ImageTexture3D
var mask: int = ALL
# what the scene's own lighting preset asked for, captured so the cinematic
# layer can never be the thing that changed it
var base_contrast: float = 1.0
var base_saturation: float = 1.0
# tuning overrides, for the sweeps
# BLOOM, retuned from the cave by measurement. The cave runs threshold 1.60 with
# Godot's default 2.00 soft knee; on this site that is above EVERY value in the
# buffer. The HDR probe (--cinema=hdr) says the pit-head's scene radiance runs
# 0.03-0.9 with the overcast sky at 0.33, and only the sun glow reaches 9. So the
# threshold comes down by 4x and the knee -- which is a WIDTH, not a ratio -- comes
# down by 13x, because a 2.0-wide smoothstep is wider than the whole range and
# nothing ever reaches full weight. 0.40 is above the sky and below the sun.
var bloom_threshold: float = 0.40
var bloom_scale: float = 0.15
var bloom_intensity: float = 0.70
var vig_k: float = 0.55
var dirt_gain: float = 0.0
var dirt_thresh: float = 1.6

static func parse(s: String) -> int:
	if s == "all":
		return ALL
	if s == "none":
		return 0
	var m: int = 0
	for part in s.split("+", false):
		var p: String = part.strip_edges()
		if p == "":
			continue
		if NAMES.has(p):
			m |= int(NAMES[p])
		else:
			push_error("CINEMA: unknown effect '%s'" % p)
	return m

static func mask_str(m: int) -> String:
	if m == ALL:
		return "all"
	if m == 0:
		return "none"
	var o: Array = []
	for n in ORDER:
		if (m & int(NAMES[n])) != 0:
			o.append(n)
	return "+".join(o)

func setup(p_env: Environment, cam: Camera3D) -> void:
	env = p_env
	attrs = CameraAttributesPractical.new()
	# Exposure is the sky's job, not the camera's. ART-DIRECTION 2.9: no shot is
	# brightened to make it read, so auto exposure is off and the multiplier is
	# exactly 1. The only exposure controls in this project are the light and
	# the preset's own tonemap_exposure, and neither of them lives here.
	attrs.auto_exposure_enabled = false
	attrs.exposure_multiplier = 1.0
	cam.attributes = attrs
	lens = CinemaLens.new()
	var comp := Compositor.new()
	comp.compositor_effects = [lens]
	cam.compositor = comp
	lut = _build_lut()
	# A round iris. Godot's default bokeh shape is a hexagon, which reads as a
	# six-blade stills lens; a cinema prime stops down round.
	ProjectSettings.set_setting("rendering/camera/depth_of_field/depth_of_field_bokeh_shape", 2)
	ProjectSettings.set_setting("rendering/camera/depth_of_field/depth_of_field_bokeh_quality", 1)
	ProjectSettings.set_setting("rendering/camera/depth_of_field/depth_of_field_use_jitter", true)

# Call after Weather.apply(), before CinemaGrade.apply(): it reads what the
# lighting preset asked for so the grade bit can be toggled without touching it.
func capture_base() -> void:
	base_contrast = env.adjustment_contrast
	base_saturation = env.adjustment_saturation

# ---------------------------------------------------------------------------
# the grade, built rather than loaded
# ---------------------------------------------------------------------------
# 32, not 24, and the entry for index i holds f((i+0.5)/N) rather than f(i/(N-1)).
# THIS IS THE BUG THE CAVE FOUND AND IT IS THE REASON THIS FILE IS A PORT AND
# NOT A REWRITE. Godot samples a 3-D colour-correction LUT with texture(), so a
# colour v lands at texel position v*N - 0.5. Building the table on i/(N-1)
# returns f(v - 0.5/N) for every pixel, which at v = 0.1 is a 17% drop -- and it
# reads as "the grade is a bit moody" rather than as an exposure cut. Measured
# in the cave: it took 14.3% off the mean of the whole frame.
#
# Verified on the surface by measurement rather than by eye: see CINEMA.md 6.9.
const LUT_N: int = 32

# WHAT THE SURFACE GRADE DOES, and it is deliberately almost nothing:
#
#  * the deepest shadows lose chroma, because both a sensor and a print do. Same
#    as the cave, same threshold. On the surface its subject is the shaft mouth
#    and the inside of the roofed bay rather than nine-tenths of the frame.
#
#  * the top two stops warm. THE CAVE WARMS THEM BY 2% AND THAT NUMBER DOES NOT
#    COME ACROSS. In the cave the top two stops are the lamp pool on iron. On
#    the surface the top two stops are THE SKY, and ART-DIRECTION 2.1 gives the
#    sky's colour to the shaft -- 12000 K, "the only cold light, and the only
#    daylight". Warming the highlights here warms the one thing in the game that
#    is not allowed to be warm, and it undoes PHOTOREAL 3's fight to get the
#    frame's B:R from 1.30 to 1.01. So the warm is masked off the top: it runs
#    over the upper MIDTONES, which on this site are wet iron, rust, timber and
#    concrete, and falls back to nothing as the value approaches the sky.
var grade_warm: float = 0.020
var grade_warm_lo: float = 0.42
var grade_warm_hi: float = 0.78

## When true the LUT is built the WRONG way -- on i/(N-1) instead of (i+0.5)/N.
## This exists so the port can PROVE it did not inherit the cave's bug, with a
## number, rather than asserting it. --cinema=lutbug renders both.
var lut_bug: bool = false

func _build_lut() -> ImageTexture3D:
	var imgs: Array[Image] = []
	for b in range(LUT_N):
		var im := Image.create(LUT_N, LUT_N, false, Image.FORMAT_RGB8)
		for g in range(LUT_N):
			for r in range(LUT_N):
				var c := (Vector3(float(r), float(g), float(b)) + Vector3(0.5, 0.5, 0.5)) / float(LUT_N)
				if lut_bug:
					c = Vector3(float(r), float(g), float(b)) / float(LUT_N - 1)
				var y: float = c.x * 0.2126 + c.y * 0.7152 + c.z * 0.0722
				# chroma rolloff below about 12% of the range
				var keep: float = clampf(y / 0.12, 0.0, 1.0)
				keep = keep * keep * (3.0 - 2.0 * keep)
				c = Vector3(y, y, y).lerp(c, 0.30 + 0.70 * keep)
				# warm the upper midtones and let go before the sky
				var hi: float = clampf((y - grade_warm_lo) / (grade_warm_hi - grade_warm_lo), 0.0, 1.0)
				hi = hi * hi * (3.0 - 2.0 * hi)
				var fade: float = 1.0 - clampf((y - grade_warm_hi) / (1.0 - grade_warm_hi), 0.0, 1.0)
				var w: float = hi * fade
				c.x *= 1.0 + grade_warm * w
				c.z *= 1.0 - (grade_warm * 0.9) * w
				im.set_pixel(r, g, Color(clampf(c.x, 0, 1), clampf(c.y, 0, 1), clampf(c.z, 0, 1)))
		imgs.append(im)
	var t := ImageTexture3D.new()
	t.create(Image.FORMAT_RGB8, LUT_N, LUT_N, LUT_N, false, imgs)
	return t

func rebuild_lut() -> void:
	lut = _build_lut()

# ---------------------------------------------------------------------------
# apply -- called once per shot, and again per frame for the shutter
# ---------------------------------------------------------------------------
func apply(m: int, cam: Camera3D, lens_mm: float, tstop: float, focus_m: float,
		wet: float = 0.0) -> void:
	mask = m

	# 1 -- TONEMAP. AgX, as the photoreal pass left it. tonemap_exposure is NOT
	# written here: it belongs to the lighting preset (0.70 / 1.45 / 1.45) and
	# the cinematic layer may not be the thing that changed the exposure.
	env.tonemap_mode = Environment.TONE_MAPPER_AGX if (m & E_TONEMAP) else Environment.TONE_MAPPER_LINEAR

	# 2 -- BLOOM. Veiling glare in the lens. On the surface it has real subjects
	# for the first time -- the cloud deck, the sun glow, specular off wet iron
	# and standing water, and after dark fourteen floods and every amber pilot.
	# Threshold measured, not chosen: CINEMA.md 6.2.
	env.glow_enabled = (m & E_BLOOM) != 0
	env.set("glow_levels/1", 1.0)
	env.set("glow_levels/2", 0.55)
	env.set("glow_levels/3", 0.12)
	env.set("glow_levels/4", 0.0)
	env.set("glow_levels/5", 0.0)
	env.set("glow_levels/6", 0.0)
	env.set("glow_levels/7", 0.0)
	env.glow_normalized = true
	env.glow_intensity = bloom_intensity
	env.glow_strength = 1.0
	env.glow_bloom = 0.0
	env.glow_blend_mode = Environment.GLOW_BLEND_MODE_ADDITIVE
	env.glow_hdr_threshold = bloom_threshold
	env.glow_hdr_scale = bloom_scale
	env.glow_hdr_luminance_cap = 12.0

	# 3 -- DEPTH OF FIELD, from the lens and the stop, never dialled by eye.
	#
	# The daylight hazard, and it is TRAILER 9's own discipline line: "never so
	# shallow it looks like a miniature". A far-field blur on a wide site shot IS
	# tilt-shift, and tilt-shift on an industrial yard is the single most
	# recognisable "this is a model" cue there is. The arithmetic already
	# prevents it and it is worth stating why: a 21 mm at T2.8 has a hyperfocal
	# of 5.3 m, so any wide shot focused past that gets far_m = infinity and the
	# far blur switches itself off. The clamp below is the backstop.
	var lim: Array = CameraRig.dof_limits(lens_mm, tstop, focus_m)
	var near_m: float = float(lim[0])
	var far_m: float = float(lim[1])
	var on: bool = (m & E_DOF) != 0
	attrs.dof_blur_far_enabled = on and far_m < cam.far
	attrs.dof_blur_far_distance = minf(far_m, cam.far)
	attrs.dof_blur_far_transition = maxf(0.5, far_m * 0.65)
	attrs.dof_blur_near_enabled = on and near_m > cam.near * 4.0
	attrs.dof_blur_near_distance = near_m
	attrs.dof_blur_near_transition = maxf(0.20, near_m * 0.55)
	attrs.dof_blur_amount = clampf((lens_mm / maxf(tstop, 0.7)) / 17.9 * 0.06, 0.01, 0.14)

	# 9 -- GRADE. The LUT ONLY. The contrast and saturation belong to the
	# lighting preset and are put back exactly as the preset asked for them.
	env.adjustment_enabled = true
	env.adjustment_brightness = 1.0      # never. 2.9 is a contract.
	env.adjustment_contrast = base_contrast
	env.adjustment_saturation = base_saturation
	env.adjustment_color_correction = lut if (m & E_GRADE) else null

	# 4,5,6,7,8,10 -- the compositor pass
	var f: int = 0
	if (m & E_MBLUR) != 0:
		f |= CinemaLens.F_MBLUR
	if (m & E_GRAIN) != 0:
		f |= CinemaLens.F_GRAIN
	if (m & E_VIGNETTE) != 0:
		f |= CinemaLens.F_VIGNETTE
	if (m & E_CA) != 0:
		f |= CinemaLens.F_CA
	if (m & E_DISTORT) != 0:
		f |= CinemaLens.F_DISTORT
	if (m & E_DIRT) != 0 and dirt_gain > 0.0 and wet > 0.5:
		f |= CinemaLens.F_DIRT
	lens.flags = f
	lens.cos4_corner = cos4_corner_for(lens_mm)
	lens.k_distort = -0.0090 * clampf((32.0 - lens_mm) / 14.0, 0.0, 1.0)
	# LATERAL CA, halved from the cave's 1.9 px at the corner of a 21 mm.
	# Not because the optics changed -- because the SUBJECT did. The cave points
	# a 21 mm at rock, which is low-frequency; the pit-head points it at a
	# headframe, which is a lattice of 1-2 pixel members against a bright sky and
	# is the highest-frequency thing in the game. Those members already carry
	# specular aliasing at MSAA 2x (visible in 04_grain_OFF, so it is not grain),
	# and a 1.9 px colour split applied to a 1 px aliased edge does not read as a
	# lens, it reads as chroma noise. At 1.0 px the fringe is still there at the
	# frame edge and stops being confetti in the middle. TRAILER 9's "a pixel or
	# two" is satisfied either way; this is the half that survives being pointed
	# at ironwork.
	lens.ca_px = 1.0 * clampf((45.0 - lens_mm) / 25.0, 0.15, 1.0)
	lens.vig_k = vig_k
	lens.taps = 9
	lens.max_blur_px = 40.0
	# TRAILER 9: "only in rain". `g_wet` is the site's one weather number and it
	# is 0.26 dry / 0.68 dusk / 1.0 in rain, so the dirt is literally gated on
	# whether it is raining rather than on a per-shot switch somebody can forget.
	lens.dirt_gain = dirt_gain * clampf((wet - 0.55) / 0.45, 0.0, 1.0)
	lens.dirt_thresh = dirt_thresh

static func cos4_corner_for(lens_mm: float) -> float:
	var half_diag: float = sqrt(CameraRig.SENSOR_W_MM * CameraRig.SENSOR_W_MM
		+ CameraRig.SENSOR_H_MM * CameraRig.SENSOR_H_MM) * 0.5
	var th: float = atan(half_diag / maxf(lens_mm, 4.0))
	var c: float = cos(th)
	return c * c * c * c
