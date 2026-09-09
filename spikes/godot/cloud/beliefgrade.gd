# ---------------------------------------------------------------------------
# BLINDSIDE -- the post stack on DATA rather than on light.  TRAILER.md 9.
#
# The cave's stack (spikes/godot/cave/postfx.gd) is nine effects and it is
# built on one argument: "every effect must be defensible as something a real
# lens or sensor does, in this light, at this scale." Two thirds of that
# sentence does not survive the crossing into the belief register, and the
# whole of this file is working out which third does.
#
#   THERE IS NO LIGHT.        ART-DIRECTION 8.1: truth is rendered, belief is
#                             drawn. Zero Light3D, ambient disabled, every
#                             cloud shader unshaded. Nothing in frame is
#                             radiance, so anything that models what light does
#                             on its way to a sensor has no subject.
#
#   THERE IS NO SENSOR.       The numbers on screen ARE the sensor's output.
#                             Adding photon shot noise to a reflectivity that
#                             was already measured claims the belief view was
#                             photographed. It was not; it was drawn.
#
#   THERE IS STILL A LENS.    The camera in shot 18 stands in a passage at a
#                             stated focal length and cuts frame-on-frame with
#                             a cave shot at the same focal length. Whatever
#                             the trailer's lens does to the corner of the cave
#                             frame it must do to the corner of the belief
#                             frame, or the cut carries a LENS change as well
#                             as a register change and reads as two cameras.
#
# So the test each effect has to pass here is not the cave's test. It is:
#
#   1. is it a property of the OPTICAL PATH (which both registers share) or of
#      the SUBJECT (which they do not)?
#   2. does it survive ART-DIRECTION 8.2 -- ring structure intact, points
#      opaque and depth-tested, and NOTHING drawn into a sensor shadow?
#
# Rule 2 is absolute and it is what does most of the killing. Measurements and
# verdicts are in CINEMA.md 5.
# ---------------------------------------------------------------------------
extends RefCounted
class_name BeliefGrade

const E_TONEMAP: int = 1 << 0    # AgX vs LINEAR -- and belief wants LINEAR
const E_BLOOM: int = 1 << 1
const E_DOF: int = 1 << 2
const E_MBLUR: int = 1 << 3
const E_GRAIN: int = 1 << 4
const E_VIGNETTE: int = 1 << 5
const E_CA: int = 1 << 6
const E_DISTORT: int = 1 << 7
const E_GRADE: int = 1 << 8

const NAMES := {
	"tonemap": E_TONEMAP, "bloom": E_BLOOM, "dof": E_DOF, "mblur": E_MBLUR,
	"grain": E_GRAIN, "vignette": E_VIGNETTE, "ca": E_CA, "distort": E_DISTORT,
	"grade": E_GRADE,
}
const ORDER := ["tonemap", "bloom", "dof", "mblur", "grain", "vignette", "ca",
	"distort", "grade"]
const ALL: int = E_TONEMAP | E_BLOOM | E_DOF | E_MBLUR | E_GRAIN | E_VIGNETTE \
	| E_CA | E_DISTORT | E_GRADE

# WHAT ACTUALLY SHIPS ON BELIEF: ONE OF NINE.
#
# Measured, each effect ALONE, at three poses; the table is CINEMA.md 5 and the
# frames are shots/cinema/pairs/. Two numbers decide it: what the effect does to
# the mean horizontal luma gradient (which on a field of 1.6-2.6 px marks IS the
# ring structure), and what share of the pixels that were EXACTLY background it
# makes brighter than background. ART-DIRECTION 8.2 makes the second absolute:
# nothing may ever be drawn into a sensor shadow.
#
# The survivor is the only one of the nine that is MULTIPLICATIVE AND <= 1 --
# the only one that can only ever take light away. That is not a coincidence and
# it is the shortest statement of the whole finding:
#
#     On a lit frame, an effect adds light where there was light.
#     On a belief frame, nine tenths of the frame is a place the sensor
#     returned nothing from, so an effect that adds light adds it THERE.
#
#   kept    vignette   cos^4 from the focal length, the cave's implementation
#                      unchanged. 0.00% into the void at every pose because it
#                      only darkens; costs 3.9-5.6% of the frame mean and 3-4%
#                      of the ring energy; and it is the one lens mark that MUST
#                      match across the belief cut, because at 35 mm the corner
#                      falls off about 25% and a cut with it on one side and off
#                      the other reads as two cameras.
#
#   cut     dof        71.6% of the sensor shadow written into, at +36/255, and
#                      a third of the ring energy gone. It does not soften a
#                      frame, it dissolves the data.
#           mblur      18.8% of the void at +27/255 at shot 18's camera. It was
#                      kept until the shot's density was halved and the voids
#                      got bigger: the reach of a smear is the screen velocity,
#                      and an isolated bright mark smears into black. The one
#                      verdict here that reversed on a measurement.
#           grain      37.1% of the void at +4.4/255, at every pose. A sensor's
#                      read floor on a measurement that already IS the sensor's
#                      output.
#           ca         20.4% of the void. Half a pixel of lateral dispersion on
#                      a 2 px white return leaves a red copy of it in the black.
#           distort    16.0% of the void at +97.7/255 on a 21 mm. Sub-percent
#                      barrel is ~10 px at a 1080p corner and the resample
#                      spreads every mark it moves.
#           bloom      0.000% of pixels at every threshold down to 0.40, and
#                      17.2% of the void at 0.00. No subject. CINEMA.md 5.2.
#           tonemap    AgX changes 98-100% of pixels and takes 16-20% off the
#                      frame mean. The intensity channel IS the data; LINEAR.
#           grade      not built. See below.
const KEEP: int = E_VIGNETTE

var env: Environment
var attrs: CameraAttributesPractical
var lens: CinemaLens
var mask: int = KEEP
# overridable so the threshold can be swept and the 'bloom does nothing'
# claim measured rather than asserted
var bloom_thresh: float = 0.80

static func parse(s: String) -> int:
	if s == "all":
		return ALL
	if s == "none":
		return 0
	if s == "keep":
		return KEEP
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
	# ART-DIRECTION 2.9 is a contract on the truth register and it is honoured
	# here for the same reason: the only thing that decides how bright a return
	# is, is how much of the pulse came back. Auto exposure off, multiplier 1.
	attrs.auto_exposure_enabled = false
	attrs.exposure_multiplier = 1.0
	cam.attributes = attrs
	lens = CinemaLens.new()
	var comp := Compositor.new()
	comp.compositor_effects = [lens]
	cam.compositor = comp
	ProjectSettings.set_setting("rendering/camera/depth_of_field/depth_of_field_bokeh_shape", 2)
	ProjectSettings.set_setting("rendering/camera/depth_of_field/depth_of_field_bokeh_quality", 1)
	ProjectSettings.set_setting("rendering/camera/depth_of_field/depth_of_field_use_jitter", true)

func apply(m: int, cam: Camera3D, lens_mm: float, tstop: float, focus_m: float) -> void:
	mask = m

	# 1 -- TONEMAP. The cave runs AgX. This register runs LINEAR and the
	# difference is not taste: the intensity channel IS the data. AgX's
	# shoulder compresses the top two stops, which is exactly where a
	# retroreflector lives, so a filmic curve quietly throws away the
	# separation between "bright rock" and "a survey plate". LIDAR.md 3 already
	# made this call for the still frames; it holds for the shots.
	env.tonemap_mode = Environment.TONE_MAPPER_AGX if (m & E_TONEMAP) else Environment.TONE_MAPPER_LINEAR
	env.tonemap_exposure = 1.0

	# 2 -- BLOOM. Veiling glare is a property of the lens, so on the argument
	# above it should survive. It does not, and rule 2 is why: glare spreads a
	# bright return into its neighbours, and neighbours here are the next ring.
	# Worse, it spreads INTO the voids -- and ART-DIRECTION 8.2 says nothing may
	# ever be drawn into a sensor shadow. Measured in pairs.txt.
	env.glow_enabled = (m & E_BLOOM) != 0
	env.set("glow_levels/1", 1.0)
	env.set("glow_levels/2", 0.55)
	env.set("glow_levels/3", 0.12)
	for i in range(4, 8):
		env.set("glow_levels/%d" % i, 0.0)
	env.glow_normalized = true
	env.glow_intensity = 0.55
	env.glow_strength = 1.0
	env.glow_bloom = 0.0
	env.glow_blend_mode = Environment.GLOW_BLEND_MODE_ADDITIVE
	# The cave's threshold of 1.60 is INERT here and that is a fact about the
	# data, not a setting: the point shader writes ALBEDO in 0..1 (a
	# retroreflector clips the intensity channel at exactly 1.0), so nothing in
	# a belief frame is ever above 1.0 and a threshold above 1.0 catches
	# nothing at all. Dropped to 0.80 so that the effect is measured DOING
	# something rather than measured switched off.
	env.glow_hdr_threshold = bloom_thresh
	env.glow_hdr_scale = 2.0
	env.glow_hdr_luminance_cap = 12.0

	# 3 -- DEPTH OF FIELD, from the lens and the stop, exactly as the cave
	# derives it. Same arithmetic, same circle of confusion, same clamp.
	var lim: Array = CloudRig.dof_limits(lens_mm, tstop, focus_m)
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

	# 9 -- GRADE. There is no grade here and the LUT is not built. The cave's
	# grade does two things: it rolls chroma out of the deepest shadows, and it
	# warms the top two stops toward the iron and the lamp. Belief has no iron
	# and no lamp, and rolling chroma out of the dark end would eat the low
	# half of the intensity ramp -- which is the channel. Kept as a switch so
	# the bit can be measured, wired to nothing so it cannot ship by accident.
	env.adjustment_enabled = false
	env.adjustment_brightness = 1.0
	env.adjustment_contrast = 1.0
	env.adjustment_saturation = 1.0
	env.adjustment_color_correction = null

	# 4,5,6,7,8 -- the compositor pass, the cave's file verbatim
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
	lens.flags = f
	lens.cos4_corner = cos4_corner_for(lens_mm)
	lens.k_distort = -0.0090 * clampf((32.0 - lens_mm) / 14.0, 0.0, 1.0)
	lens.ca_px = 1.9 * clampf((45.0 - lens_mm) / 25.0, 0.15, 1.0)
	lens.vig_k = 0.55
	lens.taps = 9
	lens.max_blur_px = 40.0

static func cos4_corner_for(lens_mm: float) -> float:
	var half_diag: float = sqrt(CloudRig.SENSOR_W_MM * CloudRig.SENSOR_W_MM
		+ CloudRig.SENSOR_H_MM * CloudRig.SENSOR_H_MM) * 0.5
	var th: float = atan(half_diag / maxf(lens_mm, 4.0))
	var c: float = cos(th)
	return c * c * c * c
