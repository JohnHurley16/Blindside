# ---------------------------------------------------------------------------
# BLINDSIDE -- the post stack.  TRAILER.md 9, in the order the table gives.
#
# Every effect here is a named bit so it can be turned on alone, measured alone,
# and shown before/after alone. `EFFECTS` is the table; `apply()` is the whole
# configuration of the frame.
#
# The rule that keeps this from becoming a filter is TRAILER.md 9's: every
# effect must be defensible as something a real lens or sensor does, in this
# light, at this scale. The one-line defence is next to each bit.
# ---------------------------------------------------------------------------
extends RefCounted
class_name CinemaGrade

const E_TONEMAP: int = 1 << 0    # the transfer curve. Not optional; it IS the picture.
const E_BLOOM: int = 1 << 1      # veiling glare in the lens, off the lamp only
const E_DOF: int = 1 << 2        # a lens has one focus plane; an eye does not
const E_MBLUR: int = 1 << 3      # the shutter is open for half a frame
const E_GRAIN: int = 1 << 4      # photon shot noise + the sensor read floor
const E_VIGNETTE: int = 1 << 5   # cos^4 falloff, from the focal length
const E_CA: int = 1 << 6         # lateral dispersion, at the frame edge
const E_DISTORT: int = 1 << 7    # sub-percent barrel on the wide lenses
const E_GRADE: int = 1 << 8      # one grade for the trailer
# E_DIRT is deliberately absent. TRAILER 9: "only on the surface, only in rain".
# There is no rain in a drowned mine 140 m down and nothing is spraying the
# lens. It is cut on the spec's own words, at zero cost. See CINEMA.md.

const NAMES := {
	"tonemap": E_TONEMAP, "bloom": E_BLOOM, "dof": E_DOF, "mblur": E_MBLUR,
	"grain": E_GRAIN, "vignette": E_VIGNETTE, "ca": E_CA, "distort": E_DISTORT,
	"grade": E_GRADE,
}
const ORDER := ["tonemap", "bloom", "dof", "mblur", "grain", "vignette", "ca",
	"distort", "grade"]
const ALL: int = E_TONEMAP | E_BLOOM | E_DOF | E_MBLUR | E_GRAIN | E_VIGNETTE \
	| E_CA | E_DISTORT | E_GRADE

var env: Environment
var attrs: CameraAttributesPractical
var lens: CinemaLens
var lut: ImageTexture3D
var mask: int = ALL

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
	# Exposure is the light's job, not the camera's. ART-DIRECTION 2.9: no shot
	# is brightened to make it read, so auto exposure is off and the multiplier
	# is exactly 1. The only exposure control in this project is the lamp.
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

# ---------------------------------------------------------------------------
# the grade, built rather than loaded -- there is not one imported asset in
# this project and a LUT is not going to be the first
# ---------------------------------------------------------------------------
# What it does, and it is deliberately almost nothing:
#   * the deepest shadows lose chroma, because both a sensor and a print do
#     (and because it is what stops the sensor's own chroma noise from turning
#     the black into confetti);
#   * the top two stops warm by about 2%, toward the iron and the lamp.
# There is no cool shadow lift. ART-DIRECTION 9 forbids cyan anywhere in the
# world, and cooling the shadows is how every other game arrives at cyan.
# 32, not 24, and the entry for index i holds f((i+0.5)/N rather than f(i/(N-1)).
# Godot samples a 3-D colour-correction LUT with texture(), so a colour v lands
# at texel position v*N - 0.5. Building the table on i/(N-1) therefore returns
# f(v - 0.5/N) for every pixel, which at v = 0.1 is an 17% drop -- and it read
# as "the grade is a bit moody" rather than as an exposure cut. Measured:
# it took 14.3% off the mean of the whole frame before this was fixed.
const LUT_N: int = 32

func _build_lut() -> ImageTexture3D:
	var imgs: Array[Image] = []
	for b in range(LUT_N):
		var im := Image.create(LUT_N, LUT_N, false, Image.FORMAT_RGB8)
		for g in range(LUT_N):
			for r in range(LUT_N):
				var c := (Vector3(float(r), float(g), float(b)) + Vector3(0.5, 0.5, 0.5)) / float(LUT_N)
				var y: float = c.x * 0.2126 + c.y * 0.7152 + c.z * 0.0722
				# chroma rolloff below about 12% of the range
				var keep: float = clampf(y / 0.12, 0.0, 1.0)
				keep = keep * keep * (3.0 - 2.0 * keep)
				c = Vector3(y, y, y).lerp(c, 0.30 + 0.70 * keep)
				# 2% warm in the top two stops
				var hi: float = clampf((y - 0.55) / 0.45, 0.0, 1.0)
				c.x *= 1.0 + 0.020 * hi
				c.z *= 1.0 - 0.018 * hi
				im.set_pixel(r, g, Color(clampf(c.x, 0, 1), clampf(c.y, 0, 1), clampf(c.z, 0, 1)))
		imgs.append(im)
	var t := ImageTexture3D.new()
	t.create(Image.FORMAT_RGB8, LUT_N, LUT_N, LUT_N, false, imgs)
	return t

# ---------------------------------------------------------------------------
# apply -- called once per shot, and again per frame for the shutter
# ---------------------------------------------------------------------------
func apply(m: int, cam: Camera3D, lens_mm: float, tstop: float, focus_m: float) -> void:
	mask = m

	# 1 -- TONEMAP. AgX, already right, and untouched: ART-DIRECTION 2.3 forbids
	# a curve that rescues the far end, and 2.9's histogram is measured on it.
	# The "off" case is the only linear-ish thing Godot offers, and it exists in
	# the pairs to show what the curve is doing, not as an option.
	env.tonemap_mode = Environment.TONE_MAPPER_AGX if (m & E_TONEMAP) else Environment.TONE_MAPPER_LINEAR
	env.tonemap_exposure = 1.0

	# 2 -- BLOOM. Veiling glare is real and it is tight: the lamp filament and
	# the beacon pilot, not a haze over the rock. Weight on the two tightest
	# mip levels only, and a threshold above the deliberately blown near wall.
	env.glow_enabled = (m & E_BLOOM) != 0
	env.set("glow_levels/1", 1.0)
	env.set("glow_levels/2", 0.55)
	env.set("glow_levels/3", 0.12)
	env.set("glow_levels/4", 0.0)
	env.set("glow_levels/5", 0.0)
	env.set("glow_levels/6", 0.0)
	env.set("glow_levels/7", 0.0)
	env.glow_normalized = true
	env.glow_intensity = 0.55
	env.glow_strength = 1.0
	env.glow_bloom = 0.0
	env.glow_blend_mode = Environment.GLOW_BLEND_MODE_ADDITIVE
	# MEASURED, at the shot-16 pose with a beacon pilot in frame (tune/bloom_*):
	#   threshold 0.8 -> 0.099% of pixels changed, max delta 154/255
	#             1.6 -> 0.059%, max 106     <- here
	#             2.6 -> 0.024%, max  21
	#             4.0 -> 0.009%, max  16
	# At 1.6 the pilot plate carries a tight halo and no rock glows, which is
	# the discipline in TRAILER 9. It is doing almost nothing because there is
	# almost nothing in this cave above threshold: the subjects section 9 names
	# for bloom -- the lamp seen directly, the winch head at 2400 K,
	# retroreflectors -- are none of them in the spike. See CINEMA.md.
	env.glow_hdr_threshold = 1.60
	env.glow_hdr_scale = 2.0
	env.glow_hdr_luminance_cap = 12.0

	# 3 -- DEPTH OF FIELD, from the lens and the stop, never dialled by eye.
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
	# Godot's amount is a blur radius, not an f-number, so it is derived rather
	# than physical: proportional to the entrance pupil (f/N), normalised so a
	# 50 mm at T2.8 sits at 0.06. TRAILER 9: never so shallow it is a miniature.
	attrs.dof_blur_amount = clampf((lens_mm / maxf(tstop, 0.7)) / 17.9 * 0.06, 0.01, 0.14)

	# 9 -- GRADE
	env.adjustment_enabled = (m & E_GRADE) != 0
	env.adjustment_brightness = 1.0      # never. 2.9 is a contract.
	env.adjustment_contrast = 1.0
	env.adjustment_saturation = 1.0
	env.adjustment_color_correction = lut if (m & E_GRADE) else null

	# 4,5,6,7,8 -- the compositor pass
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
	# barrel, scaled off the focal length: a 21 mm has some, a 50 mm has almost
	# none, an 85 mm has none. Sub-percent at the corner in every case.
	lens.k_distort = -0.0090 * clampf((32.0 - lens_mm) / 14.0, 0.0, 1.0)
	# lateral CA scales the same way and for the same reason
	lens.ca_px = 1.9 * clampf((45.0 - lens_mm) / 25.0, 0.15, 1.0)
	lens.vig_k = 0.55
	lens.taps = 9
	lens.max_blur_px = 40.0

# The natural (cos^4) illumination falloff at the corner of a 16:9 full-frame
# frame for this focal length. No taste in it: it is geometry.
static func cos4_corner_for(lens_mm: float) -> float:
	var half_diag: float = sqrt(CameraRig.SENSOR_W_MM * CameraRig.SENSOR_W_MM
		+ CameraRig.SENSOR_H_MM * CameraRig.SENSOR_H_MM) * 0.5
	var th: float = atan(half_diag / maxf(lens_mm, 4.0))
	var c: float = cos(th)
	return c * c * c * c
