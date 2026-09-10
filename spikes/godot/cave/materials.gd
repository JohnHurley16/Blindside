# ---------------------------------------------------------------------------
# BLINDSIDE assayer spike -- the materials, and the colour of heat.
#
# The three ages of iron (ART-DIRECTION 5.2) are three parameter sets on the
# cave spike's kit.gdshader, copied here verbatim. Nothing is added to it:
#
#   cast iron, wet a century   metallic 1, rough 0.62, rust 1.00
#   bearing steel, still working   metallic 1, rough 0.19, rust 0.16
#   graphitised, below the waterline   metallic 0, rough 0.98, rust 0.30
#
# The fourth material is the sight glass, which is the only transparent thing
# on the machine and the only reason the tank level is legible from the floor.
#
# THE COLOUR OF HEAT. ART-DIRECTION 2.1 gives the machinery's light as
# "1900 K -> 2400 K, 4000 K at the strike". Those are colour temperatures, so
# they are computed from the Planckian locus rather than picked: `blackbody()`
# is the standard piecewise fit, and its output is LINEARISED before it reaches
# a light or an emission, because Godot uses Color values raw and an sRGB-
# encoded amber arrives about 30% too pale in the green channel.
# ---------------------------------------------------------------------------
class_name AssayerMaterials
extends RefCounted

const NTEX: int = 64

var tex_fbm: ImageTexture3D
var tex_cel: ImageTexture3D
var tex_agg: ImageTexture3D
var tex_cid: ImageTexture3D

var rock: ShaderMaterial          # the chamber, with the scour
var stone: ShaderMaterial         # loose rock
var iron: ShaderMaterial          # cast iron, wet a century
var iron_dk: ShaderMaterial       # the same, graphitised below the waterline
var steel: ShaderMaterial         # bearing steel, still working
var glass: StandardMaterial3D     # the sight glass
var water: StandardMaterial3D     # the column inside it, and the drip
var hot_winch: StandardMaterial3D # the brake band -- HOT POINT 1
var hot_anvil: StandardMaterial3D # the anvil ring -- HOT POINT 2
var pilot: StandardMaterial3D     # the visiting machine's running lights

# ART-DIRECTION 5.2 / cave dressing.gd: the vertex colour says how RUBBED a
# surface is, not what colour it is. Cast iron is near-black; the steel values
# are the only bright numbers anywhere on the object.
const C_IRON := Color(0.058, 0.030, 0.017)
const C_IRON_L := Color(0.115, 0.062, 0.034)   # a face that gets rained on
const C_STEEL := Color(0.52, 0.50, 0.48)
const C_RACE := Color(0.64, 0.62, 0.60)        # the slew race and the hammer face
const C_STONE := Color(0.30, 0.24, 0.17)
const C_SHELL := Color(0.60, 0.61, 0.60)       # the visiting machine: BROUGHT
const C_GRAPH := Color(0.030, 0.028, 0.026)


func _noise3(kind: int, freq: float, oct: int, seedv: int) -> ImageTexture3D:
	var n := FastNoiseLite.new()
	n.seed = seedv
	n.frequency = freq
	if kind == 0:
		n.noise_type = FastNoiseLite.TYPE_SIMPLEX_SMOOTH
		n.fractal_type = FastNoiseLite.FRACTAL_FBM
		n.fractal_octaves = oct
		n.fractal_lacunarity = 2.0
		n.fractal_gain = 0.54
	else:
		n.noise_type = FastNoiseLite.TYPE_CELLULAR
		n.fractal_type = FastNoiseLite.FRACTAL_NONE
		n.cellular_distance_function = FastNoiseLite.DISTANCE_EUCLIDEAN
		n.cellular_jitter = 1.0
		if kind == 1:
			n.cellular_return_type = FastNoiseLite.RETURN_DISTANCE2_SUB
		elif kind == 2:
			n.cellular_return_type = FastNoiseLite.RETURN_DISTANCE
		else:
			n.cellular_return_type = FastNoiseLite.RETURN_CELL_VALUE
	var imgs: Array[Image] = n.get_seamless_image_3d(NTEX, NTEX, NTEX, false, 0.08)
	var t := ImageTexture3D.new()
	t.create(imgs[0].get_format(), NTEX, NTEX, NTEX, false, imgs)
	return t


func build(sd: int, water_y: float) -> void:
	tex_fbm = _noise3(0, 2.0 / float(NTEX), 5, sd + 101)
	tex_cel = _noise3(1, 6.0 / float(NTEX), 1, sd + 211)
	tex_agg = _noise3(2, 6.0 / float(NTEX), 1, sd + 307)
	tex_cid = _noise3(3, 6.0 / float(NTEX), 1, sd + 307)

	rock = ShaderMaterial.new()
	rock.shader = load("res://chamber.gdshader")
	rock.set_shader_parameter("t_fbm", tex_fbm)
	rock.set_shader_parameter("t_cel", tex_cel)
	rock.set_shader_parameter("t_agg", tex_agg)
	rock.set_shader_parameter("t_cid", tex_cid)
	rock.set_shader_parameter("water_y", water_y)

	stone = ShaderMaterial.new()
	stone.shader = load("res://stone.gdshader")
	stone.set_shader_parameter("t_fbm", tex_fbm)
	stone.set_shader_parameter("t_cel", tex_cel)
	stone.set_shader_parameter("water_y", water_y)
	stone.set_shader_parameter("wetness", 0.62)
	stone.set_shader_parameter("stone_tint", Vector3(0.44, 0.435, 0.43))

	var ksh: Shader = load("res://kit.gdshader")
	var F0_IRON := Vector3(0.560, 0.570, 0.580)
	# RUST 1.55, not the cave's 1.00. kit.gdshader scales corrosion by `lowness`
	# -- how close a surface is to the floor -- because in the cave nothing
	# manufactured is more than about 2.5 m up. This machine is 6.6 m tall, and
	# at 1.00 everything above about 3 m came back as clean grey metal, which is
	# the one thing ART-DIRECTION 5.2 forbids: "everything is ruined except the
	# surfaces still in use". A machine that stands under a dripping header tank
	# in a drowned chamber is wet at the top too.
	iron = _kit(ksh, 1.0, 0.62, 1.55, 0.50, F0_IRON, water_y)
	iron_dk = _kit(ksh, 0.0, 0.98, 0.30, 0.92, F0_IRON, water_y)
	steel = _kit(ksh, 1.0, 0.19, 0.16, 0.42, F0_IRON, water_y)

	# The sight glass. Proposal 4 in the concept notes, and the whole reason a
	# falling water level is a countdown a viewer on the floor can read.
	glass = StandardMaterial3D.new()
	glass.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	glass.albedo_color = Color(0.66, 0.70, 0.68, 0.12)
	glass.roughness = 0.05
	glass.metallic = 0.0
	glass.cull_mode = BaseMaterial3D.CULL_DISABLED
	glass.refraction_enabled = false

	water = StandardMaterial3D.new()
	water.albedo_color = Color(0.10, 0.115, 0.115)
	water.roughness = 0.06
	water.metallic = 0.0

	hot_winch = _emitter()
	hot_anvil = _emitter()

	pilot = StandardMaterial3D.new()
	pilot.albedo_color = Color(0.86, 0.83, 0.76)
	pilot.emission_enabled = true
	pilot.emission = Color(0.86, 0.83, 0.76)
	pilot.emission_energy_multiplier = 3.0
	pilot.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED


func _emitter() -> StandardMaterial3D:
	# an emitter is UNSHADED: it is a source, not a lit surface, and shading it
	# means the only light in the room is being asked to light its own filament.
	var m := StandardMaterial3D.new()
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.albedo_color = Color(0, 0, 0)
	m.emission_enabled = true
	m.emission = Color(0, 0, 0)
	m.emission_energy_multiplier = 0.0
	return m


func _kit(sh: Shader, metal: float, rough: float, rust: float, wet: float,
		  f0: Vector3, water_y: float) -> ShaderMaterial:
	var m := ShaderMaterial.new()
	m.shader = sh
	m.set_shader_parameter("metal", metal)
	m.set_shader_parameter("rough", rough)
	m.set_shader_parameter("rust", rust)
	m.set_shader_parameter("wet_amt", wet)
	m.set_shader_parameter("grain", 0.0)
	m.set_shader_parameter("metal_f0", f0)
	m.set_shader_parameter("t_fbm", tex_fbm)
	m.set_shader_parameter("water_y", water_y)
	return m


# ---------------------------------------------------------------------------
# THE COLOUR OF HEAT
#
# The standard piecewise fit to the Planckian locus, returning sRGB-ENCODED
# values, then linearised. Below 1900 K the blue channel is zero, which is why
# the dormant machine's residual glow goes to a pure ember rather than fading
# through grey: a cooling brake band does that.
# ---------------------------------------------------------------------------
static func blackbody(kelvin: float) -> Color:
	var t: float = clampf(kelvin, 1000.0, 40000.0) / 100.0
	var r: float
	var g: float
	var b: float
	if t <= 66.0:
		r = 255.0
	else:
		r = 329.698727446 * pow(t - 60.0, -0.1332047592)
	if t <= 66.0:
		g = 99.4708025861 * log(t) - 161.1195681661
	else:
		g = 288.1221695283 * pow(t - 60.0, -0.0755148492)
	if t >= 66.0:
		b = 255.0
	elif t <= 19.0:
		b = 0.0
	else:
		b = 138.5177312231 * log(t - 10.0) - 305.0447927307
	var c := Color(clampf(r / 255.0, 0.0, 1.0), clampf(g / 255.0, 0.0, 1.0),
				   clampf(b / 255.0, 0.0, 1.0))
	# linearise: Godot uses Color values raw, and an sRGB-encoded 1900 K amber
	# arrives with 55% green instead of 26% -- pale orange instead of ember.
	return Color(_lin(c.r), _lin(c.g), _lin(c.b))


static func _lin(v: float) -> float:
	return v / 12.92 if v <= 0.04045 else pow((v + 0.055) / 1.055, 2.4)
