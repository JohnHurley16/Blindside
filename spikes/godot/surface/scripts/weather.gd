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

## PHOTOREAL PASS. A flat two-stop gradient is the strongest "this is a render"
## tell a daylight frame has, and the surface is the only place in the game with
## sky, so it is in most frames. This is a generated sky: a gradient, a cloud
## deck raymarched flat onto a plane at 900 m, a horizon haze band and a sun
## glow. No bitmap - it is the same gradient noise the ground shader uses.
##
## Baked once per preset (PROCESS_MODE_QUALITY) so it costs nothing per frame,
## and the radiance map it produces is what lights everything as ambient.
const SKY_SHADER := """
shader_type sky;

uniform vec3 top_col : source_color = vec3(0.42, 0.48, 0.60);
uniform vec3 hor_col : source_color = vec3(0.80, 0.82, 0.855);
uniform vec3 gnd_col : source_color = vec3(0.50, 0.50, 0.50);
uniform vec3 cloud_lit : source_color = vec3(1.0, 1.0, 1.0);
uniform vec3 cloud_dark : source_color = vec3(0.42, 0.46, 0.55);
uniform float cloud_amt = 0.55;
uniform float cloud_cover = 0.5;
uniform float haze = 0.5;
uniform float sun_glow = 0.6;

vec2 hash22(vec2 p) {
	vec3 p3 = fract(vec3(p.xyx) * vec3(0.1031, 0.1030, 0.0973));
	p3 += dot(p3, p3.yzx + 33.33);
	return fract((p3.xx + p3.yz) * p3.zy) * 2.0 - 1.0;
}
float gnoise(vec2 p) {
	vec2 i = floor(p); vec2 f = p - i;
	vec2 u = f * f * (3.0 - 2.0 * f);
	float a = dot(hash22(i), f);
	float b = dot(hash22(i + vec2(1.0, 0.0)), f - vec2(1.0, 0.0));
	float c = dot(hash22(i + vec2(0.0, 1.0)), f - vec2(0.0, 1.0));
	float d = dot(hash22(i + vec2(1.0, 1.0)), f - vec2(1.0, 1.0));
	return mix(mix(a, b, u.x), mix(c, d, u.x), u.y) * 0.7 + 0.5;
}
const mat2 R = mat2(vec2(0.8, 0.6), vec2(-0.6, 0.8));
float fbm(vec2 p) {
	float s = 0.0; float a = 0.5; float t = 0.0;
	for (int i = 0; i < 5; i++) { s += a * gnoise(p); t += a; p = R * p * 2.11; a *= 0.5; }
	return s / t;
}

void sky() {
	vec3 d = EYEDIR;
	float up = d.y;
	vec3 col;
	if (up >= 0.0) {
		col = mix(hor_col, top_col, pow(clamp(up, 0.0, 1.0), 0.48));
		// the deck, flattened onto a plane. Cloud stretches toward the horizon
		// the way real cloud does, which is most of why this reads as sky.
		vec2 uv = d.xz / max(up, 0.035) * 0.55;
		float c = fbm(uv * 0.85);
		float c2 = fbm(uv * 2.6 + 19.0);
		float dens = clamp((c * 0.72 + c2 * 0.28 - (1.0 - cloud_cover)) * 2.6, 0.0, 1.0);
		float lit = clamp(c2 * 1.25 - 0.20, 0.0, 1.0);
		vec3 cl = mix(cloud_dark, cloud_lit, lit);
		col = mix(col, cl, dens * cloud_amt * smoothstep(0.0, 0.16, up));
		// haze band: the last few degrees above the horizon are always paler
		col = mix(col, hor_col * 1.04, haze * (1.0 - smoothstep(0.0, 0.20, up)));
	} else {
		col = mix(hor_col * 0.94, gnd_col, pow(clamp(-up, 0.0, 1.0), 0.55));
	}
	float s = clamp(dot(normalize(d), normalize(LIGHT0_DIRECTION * -1.0)), 0.0, 1.0);
	col += LIGHT0_COLOR * sun_glow * pow(s, 5.0) * 0.30;
	col += LIGHT0_COLOR * sun_glow * pow(s, 900.0) * 6.0;
	COLOR = col;
}
"""

var sun: DirectionalLight3D
var env: Environment
var world_env: WorldEnvironment
var rain: GPUParticles3D
var yard_lights: Array = []
var always_lights: Array = []
var preset := "overcast"

func setup(root: Node3D, light_data: Array, skymode: String = "realtime", ssao_on: bool = true) -> void:
	world_env = WorldEnvironment.new()
	env = Environment.new()
	env.background_mode = Environment.BG_SKY
	var sky := Sky.new()
	var shd := Shader.new()
	shd.code = SKY_SHADER
	var psm := ShaderMaterial.new()
	psm.shader = shd
	sky.sky_material = psm
	# MEASURED, and it cost an afternoon: PROCESS_MODE_QUALITY re-bakes the whole
	# importance-sampled radiance map whenever the sky is marked dirty, and with a
	# ShaderMaterial sky that is every frame. It took the overcast pass from
	# 93 fps to 9 fps on its own - a 100 ms frame, all of it in one cubemap bake.
	# REALTIME is the mode for a sky whose material is not a ProceduralSkyMaterial.
	match skymode:
		"quality": sky.process_mode = Sky.PROCESS_MODE_QUALITY
		"incremental": sky.process_mode = Sky.PROCESS_MODE_INCREMENTAL
		"realtime": sky.process_mode = Sky.PROCESS_MODE_REALTIME
		_: sky.process_mode = Sky.PROCESS_MODE_INCREMENTAL
	sky.radiance_size = Sky.RADIANCE_SIZE_128
	env.sky = sky
	env.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	env.ambient_light_sky_contribution = 1.0
	# AgX: correct filmic shoulder for a daylight scene, and it is what the
	# project already used. It desaturates hard, so the adjustment block below
	# puts the contrast and a little of the colour back - which is cheaper and
	# more controllable than swapping to ACES and losing the highlight rolloff.
	env.tonemap_mode = Environment.TONE_MAPPER_AGX
	env.tonemap_white = 6.0
	env.adjustment_enabled = true
	env.adjustment_brightness = 1.0
	env.adjustment_contrast = 1.12
	env.adjustment_saturation = 1.20
	env.fog_enabled = true
	env.fog_mode = Environment.FOG_MODE_EXPONENTIAL
	# NOTE: fog_aerial_perspective samples the SKY in the pixel's view direction.
	# Every ray that looks down at the ground samples the sky's GROUND half, so a
	# dark ground_bottom_color paints the whole distance black. That is why the
	# ground colours below are near as bright as the horizon: this is mist lit by
	# an overcast sky, and mist lit from above is not dark.
	env.fog_aerial_perspective = 0.22
	env.fog_sky_affect = 0.35
	# CONTACT. 55 000 DETAIL instances cast no shadow, so occlusion is the only
	# thing that puts them ON the ground rather than above it. The first pass ran
	# radius 0.7 m, which is ten times the size of a chipping: it darkened whole
	# regions and did nothing at the contact. 0.34 m is the scale of the objects
	# that actually need it.
	env.ssao_enabled = ssao_on
	env.ssao_radius = 0.34
	env.ssao_intensity = 1.5
	env.ssao_power = 1.25
	env.ssao_detail = 0.5
	env.ssao_horizon = 0.06
	env.ssao_sharpness = 0.98
	env.ssao_light_affect = 0.0
	env.ssao_ao_channel_affect = 0.0
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

## The three lighting conditions the spike ships.
##
## PHOTOREAL PASS. Two things changed here and both are exposure, not colour:
##
## 1. OVERCAST IS THE BEST-LOOKING STATE, per the spike's own recommendation in
##    NOTES 5. It was the flattest. It now has the widest sun:ambient ratio of
##    the three, so surfaces have form, and its exposure is set for concrete at
##    0.26 linear albedo rather than 0.086 - the old exposure was compensating
##    for an albedo three times too dark, which is why everything read blue.
## 2. RAIN CHANGES MATERIALS. `g_wet` goes to 1.0, which darkens every albedo,
##    drops every roughness, fills the joints, raises the puddle plane over the
##    whole yard and turns run-off on every vertical face. The particles are the
##    least of it: a rain state where only particles fall is the strongest
##    possible tell that this is not a photograph.
func apply(name: String) -> void:
	preset = name
	var psm: ShaderMaterial = env.sky.sky_material
	match name:
		"overcast":
			# High overcast at the shaft's own colour, DESATURATED. The first
			# pass ran a saturated blue sky into a 100%-sky ambient and every
			# surface in the yard came back blue; real overcast is nearly
			# neutral with a cool bias, and the bias is enough.
			psm.set_shader_parameter("top_col", Color(0.300, 0.352, 0.442))
			psm.set_shader_parameter("hor_col", Color(0.660, 0.688, 0.726))
			psm.set_shader_parameter("gnd_col", Color(0.404, 0.386, 0.352))
			psm.set_shader_parameter("cloud_lit", Color(0.900, 0.912, 0.940))
			psm.set_shader_parameter("cloud_dark", Color(0.320, 0.352, 0.412))
			psm.set_shader_parameter("cloud_amt", 0.78)
			psm.set_shader_parameter("cloud_cover", 0.58)
			psm.set_shader_parameter("haze", 0.45)
			psm.set_shader_parameter("sun_glow", 0.35)
			sun.light_color = Color(1.0, 0.985, 0.962)
			sun.light_energy = 1.50
			sun.light_angular_distance = 3.6
			sun.rotation_degrees = Vector3(-46, 132, 0)
			env.ambient_light_energy = 1.30
			env.fog_light_color = Color(0.60, 0.635, 0.685)
			env.fog_density = 0.0016
			env.tonemap_exposure = 0.70
			env.adjustment_contrast = 1.15
			env.adjustment_saturation = 1.10
			_wet(0.26)
			_yard(false)
			rain.visible = false
		"rain":
			psm.set_shader_parameter("top_col", Color(0.132, 0.148, 0.180))
			psm.set_shader_parameter("hor_col", Color(0.352, 0.366, 0.392))
			psm.set_shader_parameter("gnd_col", Color(0.224, 0.216, 0.202))
			psm.set_shader_parameter("cloud_lit", Color(0.430, 0.446, 0.482))
			psm.set_shader_parameter("cloud_dark", Color(0.108, 0.118, 0.142))
			psm.set_shader_parameter("cloud_amt", 0.95)
			psm.set_shader_parameter("cloud_cover", 0.80)
			psm.set_shader_parameter("haze", 0.62)
			psm.set_shader_parameter("sun_glow", 0.10)
			sun.light_color = SHAFT_LIGHT.lerp(Color(1, 1, 1), 0.72)
			sun.light_energy = 1.30
			sun.light_angular_distance = 14.0
			sun.rotation_degrees = Vector3(-58, 132, 0)
			env.ambient_light_energy = 1.70
			env.fog_light_color = Color(0.36, 0.375, 0.405)
			env.fog_density = 0.0060
			env.tonemap_exposure = 1.45
			env.adjustment_contrast = 1.10
			env.adjustment_saturation = 1.10
			_wet(1.0)
			_yard(true, 0.55)
			rain.visible = true
		"dusk":
			psm.set_shader_parameter("top_col", Color(0.018, 0.024, 0.042))
			psm.set_shader_parameter("hor_col", Color(0.088, 0.080, 0.078))
			psm.set_shader_parameter("gnd_col", Color(0.014, 0.014, 0.016))
			psm.set_shader_parameter("cloud_lit", Color(0.115, 0.092, 0.076))
			psm.set_shader_parameter("cloud_dark", Color(0.020, 0.022, 0.030))
			psm.set_shader_parameter("cloud_amt", 0.85)
			psm.set_shader_parameter("cloud_cover", 0.60)
			psm.set_shader_parameter("haze", 0.55)
			psm.set_shader_parameter("sun_glow", 1.30)
			sun.light_color = Color(0.45, 0.55, 0.78)
			sun.light_energy = 0.09
			sun.light_angular_distance = 20.0
			sun.rotation_degrees = Vector3(-8, 250, 0)
			env.ambient_light_energy = 1.0
			env.fog_light_color = Color(0.070, 0.072, 0.088)
			env.fog_density = 0.007
			env.tonemap_exposure = 1.45
			env.adjustment_contrast = 1.06
			env.adjustment_saturation = 1.14
			_wet(0.68)
			_yard(true, 1.0)
			rain.visible = false
	_push_ground(psm)

var ground_mat: ShaderMaterial

func _wet(v: float) -> void:
	RenderingServer.global_shader_parameter_set("g_wet", v)

## Hand the ground shader the sky it has to mirror. The ground writes its own
## reflection (see the note in materials.gd about grazing Fresnel), so it needs
## to be told the sky's colours and the sun's direction rather than being able
## to sample them.
func _push_ground(psm: ShaderMaterial) -> void:
	var toward_sun := Basis.from_euler(sun.rotation).z.normalized()
	for m in Mats.grounds():
		m.set_shader_parameter("sky_col", psm.get_shader_parameter("hor_col"))
		m.set_shader_parameter("sky_top", psm.get_shader_parameter("top_col"))
		m.set_shader_parameter("sun_col", sun.light_color * sun.light_energy * 0.45)
		m.set_shader_parameter("sun_dir", toward_sun)
	if ground_mat != null:
		ground_mat.set_shader_parameter("sky_col", psm.get_shader_parameter("hor_col"))
		ground_mat.set_shader_parameter("sky_top", psm.get_shader_parameter("top_col"))
		ground_mat.set_shader_parameter("sun_col", sun.light_color * sun.light_energy * 0.45)
		ground_mat.set_shader_parameter("sun_dir", toward_sun)

func set_sky_col(_c: Color) -> void:
	pass

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
