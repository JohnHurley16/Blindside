extends RefCounted
class_name Weather
##
## DRESSING LAYER - sky, light and rain.
##
## The surface is the only place in the game with sky, and ART-DIRECTION 2.1
## gives the shaft 12000 K (0.60, 0.74, 1.00) as "the only cold light, and the
## only daylight". So the surface's daylight IS the shaft's light: one source,
## seen from the top up here and from the bottom down there.
##
## Daylight is the cost centre. Everything here that costs frame time is called
## out in NOTES.md with the measurement that justified it.

const SHAFT_LIGHT := Color(0.60, 0.74, 1.00)

var sun: DirectionalLight3D
var env: Environment
var world_env: WorldEnvironment
var rain: GPUParticles3D
var yard_lights: Array = []
var always_lights: Array = []
var preset := "overcast"

func setup(root: Node3D, light_data: Array) -> void:
	world_env = WorldEnvironment.new()
	env = Environment.new()
	env.background_mode = Environment.BG_SKY
	var sky := Sky.new()
	var psm := ProceduralSkyMaterial.new()
	psm.sun_angle_max = 90.0
	psm.sun_curve = 1.0
	sky.sky_material = psm
	env.sky = sky
	env.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	env.ambient_light_sky_contribution = 1.0
	env.tonemap_mode = Environment.TONE_MAPPER_AGX
	env.tonemap_white = 6.0
	env.fog_enabled = true
	env.fog_mode = Environment.FOG_MODE_EXPONENTIAL
	# NOTE: fog_aerial_perspective samples the SKY in the pixel's view direction.
	# Every ray that looks down at the ground samples the sky's GROUND half, so a
	# dark ground_bottom_color paints the whole distance black. That is why the
	# ground colours below are near as bright as the horizon: this is mist lit by
	# an overcast sky, and mist lit from above is not dark.
	env.fog_aerial_perspective = 0.22
	env.fog_sky_affect = 0.35
	env.ssao_enabled = true
	env.ssao_radius = 0.7
	env.ssao_intensity = 1.05
	env.ssao_power = 1.2
	env.sdfgi_enabled = false
	env.glow_enabled = false
	world_env.environment = env
	root.add_child(world_env)

	sun = DirectionalLight3D.new()
	sun.name = "Sun"
	sun.rotation_degrees = Vector3(-52, 128, 0)
	# The cost centre. 4 splits over 110 m, blended off, and every scatter
	# MultiMesh has cast_shadow OFF - see Batcher.
	sun.directional_shadow_mode = DirectionalLight3D.SHADOW_PARALLEL_4_SPLITS
	sun.directional_shadow_max_distance = 95.0
	sun.directional_shadow_split_1 = 0.06
	sun.directional_shadow_split_2 = 0.17
	sun.directional_shadow_split_3 = 0.45
	sun.directional_shadow_blend_splits = false
	sun.directional_shadow_fade_start = 0.85
	sun.shadow_enabled = true
	# Measured: at bias 0.04 / normal_bias 1.4 the far splits acne so badly that
	# the ground beyond ~40 m goes uniformly dark. These numbers are the fix.
	sun.shadow_bias = 0.11
	sun.shadow_normal_bias = 3.2
	sun.shadow_blur = 1.2
	sun.light_angular_distance = 3.0
	root.add_child(sun)

	# the yard's own lights, off until dusk
	for e in light_data:
		var o := OmniLight3D.new()
		o.position = e[0]
		o.light_color = e[1]
		o.light_energy = e[2]
		o.omni_range = e[3]
		o.shadow_enabled = false
		o.visible = false
		o.distance_fade_enabled = true
		o.distance_fade_begin = 42.0
		o.distance_fade_length = 12.0
		o.set_meta("always", e.size() > 4 and bool(e[4]))
		root.add_child(o)
		if o.get_meta("always"):
			o.visible = true
			always_lights.append(o)
		yard_lights.append(o)

	# and one per lighting column, aimed down as a flood
	rain = GPUParticles3D.new()
	rain.name = "Rain"
	rain.visible = false
	rain.amount = 14000
	rain.lifetime = 1.4
	rain.explosiveness = 0.0
	rain.fixed_fps = 0
	rain.local_coords = false
	var pm := ParticleProcessMaterial.new()
	pm.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_BOX
	pm.emission_box_extents = Vector3(26, 9, 26)
	pm.direction = Vector3(0.12, -1, 0.06)
	pm.spread = 1.5
	pm.initial_velocity_min = 11.0
	pm.initial_velocity_max = 15.0
	pm.gravity = Vector3(0, -12.0, 0)
	pm.scale_min = 0.7
	pm.scale_max = 1.5
	rain.process_material = pm
	var qm := QuadMesh.new()
	qm.size = Vector2(0.013, 0.42)
	var qmat := StandardMaterial3D.new()
	qmat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	qmat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	qmat.albedo_color = Color(0.72, 0.78, 0.88, 0.30)
	qmat.billboard_mode = BaseMaterial3D.BILLBOARD_FIXED_Y
	qmat.billboard_keep_scale = true
	qmat.disable_receive_shadows = true
	qm.material = qmat
	rain.draw_pass_1 = qm
	rain.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	root.add_child(rain)

## the three lighting conditions the spike ships
func apply(name: String) -> void:
	preset = name
	var psm: ProceduralSkyMaterial = env.sky.sky_material
	match name:
		"overcast":
			# flat high overcast at the shaft's own colour. No sun disc, no
			# shadow edge you could name - soft, and everything is legible.
			psm.sky_top_color = Color(0.46, 0.53, 0.66)
			psm.sky_horizon_color = Color(0.80, 0.82, 0.855)
			psm.ground_bottom_color = Color(0.50, 0.50, 0.50)
			psm.ground_horizon_color = Color(0.76, 0.775, 0.80)
			psm.sky_energy_multiplier = 1.15
			sun.light_color = SHAFT_LIGHT.lerp(Color(1, 1, 1), 0.35)
			sun.light_energy = 1.55
			sun.light_angular_distance = 4.5
			sun.rotation_degrees = Vector3(-56, 132, 0)
			env.ambient_light_energy = 0.58
			env.fog_light_color = Color(0.62, 0.655, 0.71)
			env.fog_density = 0.0016
			env.tonemap_exposure = 0.50
			_wet(0.30)
			set_sky_col(Color(0.60, 0.64, 0.70))
			_yard(false)
			rain.visible = false
		"rain":
			# "the Assayer runs for as long as it rains" - rain is canon
			psm.sky_top_color = Color(0.235, 0.265, 0.325)
			psm.sky_horizon_color = Color(0.50, 0.515, 0.545)
			psm.ground_bottom_color = Color(0.30, 0.30, 0.30)
			psm.ground_horizon_color = Color(0.47, 0.485, 0.51)
			psm.sky_energy_multiplier = 1.05
			sun.light_color = SHAFT_LIGHT.lerp(Color(1, 1, 1), 0.2)
			sun.light_energy = 1.35
			sun.light_angular_distance = 9.0
			env.ambient_light_energy = 0.42
			env.fog_light_color = Color(0.44, 0.455, 0.485)
			env.fog_density = 0.0055
			env.tonemap_exposure = 1.35
			_wet(1.0)
			set_sky_col(Color(0.36, 0.38, 0.42))
			_yard(true, 0.45)
			rain.visible = true
		"dusk":
			# the yard after dark is lit by the teams' own lights. The cave never
			# gets those; the surface is allowed them (DESIGN-PRINCIPLES 3).
			psm.sky_top_color = Color(0.030, 0.038, 0.058)
			psm.sky_horizon_color = Color(0.105, 0.098, 0.098)
			psm.ground_bottom_color = Color(0.020, 0.020, 0.022)
			psm.ground_horizon_color = Color(0.075, 0.072, 0.070)
			psm.sky_energy_multiplier = 1.0
			sun.light_color = Color(0.45, 0.55, 0.78)
			sun.light_energy = 0.09
			sun.light_angular_distance = 20.0
			sun.rotation_degrees = Vector3(-8, 250, 0)
			env.ambient_light_energy = 1.0
			env.fog_light_color = Color(0.075, 0.078, 0.095)
			env.fog_density = 0.007
			env.tonemap_exposure = 1.5
			_wet(0.65)
			set_sky_col(Color(0.055, 0.058, 0.075))
			_yard(true, 1.0)
			rain.visible = false

var ground_mat: ShaderMaterial

func _wet(v: float) -> void:
	RenderingServer.global_shader_parameter_set("g_wet", v)

func set_sky_col(c: Color) -> void:
	if ground_mat != null:
		ground_mat.set_shader_parameter("sky_col", c)

func _yard(on: bool, scale: float = 1.0) -> void:
	for o in yard_lights:
		o.visible = on or o.get_meta("always", false)
		if on:
			o.light_energy = o.get_meta("base", o.light_energy)
			if not o.has_meta("base"):
				o.set_meta("base", o.light_energy)
			o.light_energy = o.get_meta("base") * scale

## RULE. Every lighting column in LAYOUT gets one downward flood at dusk. Only
## the two nearest the collar cast shadows; the rest are shadowless, which is
## what makes 14 lights affordable.
func add_column_lights(root: Node3D, L: SurfaceLayout) -> void:
	var i := 0
	for c in L.plan["columns"]:
		var x := float(c["x"]) / 1000.0
		var z := float(c["z"]) / 1000.0
		var h := float(c["h"]) / 1000.0
		var s := SpotLight3D.new()
		s.position = Vector3(x, h + 0.1, z)
		s.rotation_degrees = Vector3(-90, 0, 0)
		s.light_color = Color(1.0, 0.965, 0.92)
		s.light_energy = 9.0
		s.spot_range = h + 16.0
		s.spot_angle = 62.0
		s.spot_angle_attenuation = 0.6
		# measured: two shadow-casting column floods put a 142 ms spike in the
		# dusk run when both entered the frame with the bay omnis. Only the shaft
		# flood casts now, and every positional light distance-fades.
		s.shadow_enabled = false
		s.distance_fade_enabled = true
		s.distance_fade_begin = 60.0
		s.distance_fade_length = 15.0
		s.visible = false
		root.add_child(s)
		yard_lights.append(s)
		i += 1
	# the floodlight hung under the sheave deck, aimed down the shaft
	var H: Dictionary = L.plan["headframe"]
	var f := SpotLight3D.new()
	f.position = Vector3(0.0, float(H["deck_h"]) / 1000.0 - 1.8, 0.0)
	f.rotation_degrees = Vector3(-90, 0, 0)
	f.light_color = SHAFT_LIGHT
	f.light_energy = 22.0
	f.spot_range = 46.0
	f.spot_angle = 16.0
	f.shadow_enabled = true
	f.visible = false
	root.add_child(f)
	yard_lights.append(f)
