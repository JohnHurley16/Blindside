extends RefCounted
class_name Mats
##
## DRESSING LAYER - materials.
##
## One shader for every solid on the site, driven by seven uniforms, plus one
## shader for the ground. No image texture, no UV unwrap: everything is world
## space procedural, which is the only thing that survives a generated site
## (ART-DIRECTION 3.2).
##
## Per-instance MultiMesh colour multiplies albedo, so one material covers a
## whole family (rust light to rust black, bone to grubby bone) in one draw call.

const SOLID_SHADER := """
shader_type spatial;
render_mode cull_back, diffuse_burley, specular_schlick_ggx;

uniform vec3 base_col : source_color = vec3(0.3);
uniform float rough_lo = 0.5;
uniform float rough_hi = 0.95;
uniform float metal = 0.0;
uniform float grain = 1.0;        // how much procedural noise varies albedo
uniform float streak = 0.0;       // vertical rust / mineral runs
uniform vec3 streak_col : source_color = vec3(0.16, 0.07, 0.03);
uniform float noise_scale = 2.0;
uniform float wet_take = 1.0;     // how much this material responds to rain
uniform float dirt = 0.35;        // dust settling on up-facing surfaces
uniform vec3 dirt_col : source_color = vec3(0.19, 0.16, 0.12);
uniform float emissive = 0.0;
global uniform float g_wet;

float h31(vec3 p) {
	return fract(sin(dot(p, vec3(12.9898, 78.233, 37.719))) * 43758.5453);
}
float vnoise(vec3 p) {
	vec3 i = floor(p);
	vec3 f = fract(p);
	f = f * f * (3.0 - 2.0 * f);
	float n000 = h31(i);
	float n100 = h31(i + vec3(1, 0, 0));
	float n010 = h31(i + vec3(0, 1, 0));
	float n110 = h31(i + vec3(1, 1, 0));
	float n001 = h31(i + vec3(0, 0, 1));
	float n101 = h31(i + vec3(1, 0, 1));
	float n011 = h31(i + vec3(0, 1, 1));
	float n111 = h31(i + vec3(1, 1, 1));
	return mix(mix(mix(n000, n100, f.x), mix(n010, n110, f.x), f.y),
	           mix(mix(n001, n101, f.x), mix(n011, n111, f.x), f.y), f.z);
}
float fbm(vec3 p) {
	return vnoise(p) * 0.6 + vnoise(p * 2.7) * 0.27 + vnoise(p * 6.1) * 0.13;
}

varying vec3 wpos;
varying vec3 wnorm;

void vertex() {
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	wnorm = normalize((MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz);
}

void fragment() {
	vec3 p = wpos * noise_scale;
	float n = fbm(p);
	float fine = fbm(p * 9.0);
	vec3 alb = base_col * COLOR.rgb;
	alb *= mix(1.0 - grain * 0.55, 1.0 + grain * 0.45, n);
	alb *= mix(0.88, 1.12, fine);

	// vertical runs: smear the noise down the world Y axis
	if (streak > 0.0) {
		float s = fbm(vec3(wpos.x * 3.1, wpos.y * 0.28, wpos.z * 3.1));
		float run = smoothstep(0.52, 0.80, s) * clamp(1.0 - abs(wnorm.y), 0.0, 1.0);
		alb = mix(alb, streak_col, run * streak);
	}

	// dust and mud settle on horizontals; that is gravity, not noise
	float up = clamp(wnorm.y, 0.0, 1.0);
	float set = up * up * up * dirt * mix(0.5, 1.3, fbm(p * 0.7));
	alb = mix(alb, dirt_col, clamp(set, 0.0, 0.85));

	float r = mix(rough_lo, rough_hi, n);
	// rain: darkens and polishes, more on horizontals where it pools
	float w = clamp(g_wet * wet_take * (0.45 + 0.55 * up), 0.0, 1.0);
	alb *= mix(1.0, 0.62, w);
	r = mix(r, 0.09, w * 0.85);

	ALBEDO = alb;
	ROUGHNESS = clamp(r, 0.03, 1.0);
	METALLIC = metal;
	SPECULAR = mix(0.16, 0.5, clamp(w, 0.0, 1.0) + metal * 0.5);
	if (emissive > 0.0) {
		EMISSION = base_col * COLOR.rgb * emissive;
	}
}
"""

const GROUND_SHADER := """
shader_type spatial;
// specular_disabled is load-bearing, and it took a day to find out why. A first
// person camera near the ground always sees the ground at 75-88 degrees of
// incidence, and Schlick Fresnel goes to 1 at grazing whatever F0 is. Under a
// full-hemisphere overcast sky that turns the entire site into a mirror of the
// sky: uniform pale grey, no albedo, no joints, no cracks, at every distance.
// So the ground takes no engine specular at all, and the one thing that should
// be shiny - standing water - gets a hand-written sheen at the bottom instead.
render_mode cull_back, diffuse_burley, specular_disabled;

// Everything this shader needs is derived from WORLD POSITION and the surface
// normal - not from vertex data. The pad rectangle comes across as a uniform
// straight out of LAYOUT, so the concrete stops exactly where the simulation
// says it stops, and nothing else needs an attribute at all.
uniform float slab = 3.6;              // hardstanding slab module, metres
uniform vec4 pad = vec4(-32.0, -26.0, 30.0, 26.0);
uniform vec4 pad2 = vec4(30.0, -10.0, 38.0, 10.0);
uniform vec2 hot_a = vec2(0.0, 0.0);   // the collar: the most worked ground
uniform vec2 hot_b = vec2(-19.0, -3.0);// the service bay
uniform int dbg = 0;
uniform vec3 sky_col : source_color = vec3(0.62, 0.66, 0.72);
global uniform float g_wet;

float h21(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float vnoise2(vec2 p) {
	vec2 i = floor(p); vec2 f = fract(p); f = f * f * (3.0 - 2.0 * f);
	return mix(mix(h21(i), h21(i + vec2(1, 0)), f.x),
	           mix(h21(i + vec2(0, 1)), h21(i + vec2(1, 1)), f.x), f.y);
}
float fbm2(vec2 p) {
	return vnoise2(p) * 0.55 + vnoise2(p * 2.3) * 0.27 + vnoise2(p * 5.7) * 0.12 + vnoise2(p * 13.0) * 0.06;
}
float cracks(vec2 p) {
	vec2 i = floor(p); vec2 f = fract(p);
	float d1 = 8.0; float d2 = 8.0;
	for (int y = -1; y <= 1; y++) {
		for (int x = -1; x <= 1; x++) {
			vec2 g = vec2(float(x), float(y));
			vec2 o = vec2(h21(i + g), h21(i + g + 41.3));
			float d = length(g + o - f);
			if (d < d1) { d2 = d1; d1 = d; } else if (d < d2) { d2 = d; }
		}
	}
	return d2 - d1;
}
float in_rect(vec2 p, vec4 r, float feather) {
	vec2 d = max(r.xy - p, p - r.zw);
	return 1.0 - smoothstep(0.0, feather, max(d.x, d.y));
}

varying vec3 wpos;
varying vec3 wnorm;

void vertex() {
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	wnorm = normalize((MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz);
}

void fragment() {
	vec2 p = wpos.xz;
	float hard = max(in_rect(p, pad, 1.8), in_rect(p, pad2, 1.8));
	// spoil rises: the tips are dark waste rock, and height is what says so
	float mud = smoothstep(0.55, 3.2, wpos.y) * 0.9;
	// traffic: where the work happens, oil and rubber and tracked mud
	float traffic = max(1.0 - length(p - hot_a) / 17.0, 1.0 - length(p - hot_b) / 13.0);
	traffic = clamp(max(traffic, 1.0 - abs(p.y - 1.5) / 4.0 - max(0.0, p.x + 30.0) / 40.0), 0.30, 1.0);
	float flat_ = smoothstep(0.90, 0.995, wnorm.y);

	float grit = fbm2(p * 6.0);
	float fine = fbm2(p * 40.0);

	// --- concrete hardstanding
	vec3 conc = vec3(0.086, 0.082, 0.075) * mix(0.58, 1.42, grit) * mix(0.86, 1.14, fine);
	vec2 g = abs(fract(p / slab + 0.5) - 0.5) * slab;
	float joint = smoothstep(0.075, 0.012, min(g.x, g.y));
	conc = mix(conc, vec3(0.048, 0.043, 0.038), joint * 0.88);
	float cr = cracks(p * 0.85);
	float crack = smoothstep(0.045, 0.006, cr) * smoothstep(0.40, 0.75, fbm2(p * 0.6));
	conc = mix(conc, vec3(0.036, 0.031, 0.027), crack * 0.7);
	float oil = smoothstep(0.52, 0.88, fbm2(p * 0.9 + 17.0));
	conc = mix(conc, vec3(0.020, 0.018, 0.018), oil * 0.85 * clamp(traffic + 0.25, 0.0, 1.0));
	float trk = smoothstep(0.38, 0.82, fbm2(p * 1.4 + 91.0)) * clamp(traffic + 0.2, 0.0, 1.0);
	conc = mix(conc, vec3(0.075, 0.058, 0.040), trk * 0.72);

	// --- open ground: spoil, mud, gravel
	vec3 soil = vec3(0.086, 0.064, 0.042) * mix(0.55, 1.40, grit) * mix(0.82, 1.18, fine);
	float gravel = smoothstep(0.45, 0.72, fbm2(p * 20.0));
	soil = mix(soil, vec3(0.148, 0.124, 0.094), gravel * 0.5);
	soil = mix(soil, vec3(0.043, 0.035, 0.029), clamp(mud, 0.0, 0.95));
	soil = mix(soil, vec3(0.088, 0.066, 0.042), traffic * 0.5 * (1.0 - hard));

	vec3 alb = mix(soil, conc, hard);
	float r = mix(0.96, mix(0.86, 0.62, joint), hard);

	// --- standing water. Only on ground that is actually flat, which is what a
	// puddle needs, and always in the slab joints once it is wet.
	float pond = smoothstep(0.56, 0.80, fbm2(p * 0.85 + 5.0)) * flat_;
	float puddle = clamp(pond * (0.30 + 0.70 * g_wet) + joint * hard * g_wet * 0.5, 0.0, 1.0);
	alb = mix(alb, alb * 0.5, puddle);
	r = mix(r, 0.05, puddle * 0.94);
	alb *= mix(1.0, 0.70, g_wet * 0.75);
	r = mix(r, r * 0.6, g_wet * 0.7);

	ALBEDO = alb;
	ROUGHNESS = clamp(r, 0.04, 1.0);
	METALLIC = 0.0;
	// Grazing-angle Fresnel off a full-hemisphere overcast sky turns a rough
	// ground plane into a mirror: at 85 degrees incidence F -> 1 and the whole
	// distance washes out to sky colour whatever the albedo is. Dry ground gets
	// almost no specular; a puddle gets all of it, which is the contrast we want.
	// the hand-written water sheen: only where there is water, and only at the
	// angle water actually mirrors from
	float fres = pow(1.0 - clamp(dot(normalize(NORMAL), normalize(VIEW)), 0.0, 1.0), 4.0);
	EMISSION = sky_col * puddle * (0.10 + 0.95 * fres);
	if (dbg == 1) { ALBEDO = vec3(hard, mud, traffic); ROUGHNESS = 1.0; }
	if (dbg == 2 || dbg == 3) { ALBEDO = vec3(0.4); ROUGHNESS = 1.0; }
	if (dbg == 7) { ALBEDO = vec3(0.0); ROUGHNESS = 1.0; EMISSION = vec3(1.0, 0.0, 0.6); }
}
"""

static var _shader_solid: Shader
static var _shader_ground: Shader
static var _cache: Dictionary = {}

static func solid_shader() -> Shader:
	if _shader_solid == null:
		_shader_solid = Shader.new()
		_shader_solid.code = SOLID_SHADER
	return _shader_solid

static func ground_shader() -> Shader:
	if _shader_ground == null:
		_shader_ground = Shader.new()
		_shader_ground.code = GROUND_SHADER
	return _shader_ground

static func ground_material(L: SurfaceLayout) -> ShaderMaterial:
	var m := ShaderMaterial.new()
	m.shader = ground_shader()
	var p0: Dictionary = L.plan["pads"][0]
	var p1: Dictionary = L.plan["pads"][1]
	m.set_shader_parameter("pad", Vector4(float(p0["x0"]) / 1000.0, float(p0["z0"]) / 1000.0,
		float(p0["x1"]) / 1000.0, float(p0["z1"]) / 1000.0))
	m.set_shader_parameter("pad2", Vector4(float(p1["x0"]) / 1000.0, float(p1["z0"]) / 1000.0,
		float(p1["x1"]) / 1000.0, float(p1["z1"]) / 1000.0))
	m.set_shader_parameter("slab", float(L.plan["slab_module"]) / 1000.0)
	m.set_shader_parameter("hot_a", Vector2(0.0, 0.0))
	var bay: Dictionary = {}
	for b in L.plan["buildings"]:
		if b["kind"] == "service_bay":
			bay = b
	if not bay.is_empty():
		m.set_shader_parameter("hot_b", Vector2((float(bay["x0"]) + float(bay["x1"])) / 2000.0,
			(float(bay["z0"]) + float(bay["z1"])) / 2000.0))
	return m

## The palette. Every entry names which register it belongs to:
##   old  = THE INHERITED, the hellscape: corroded, riveted, timbered, stained
##   new  = THE BROUGHT, the future: manufactured, modular, clean-edged, labelled
static func get_mat(id: String) -> ShaderMaterial:
	if _cache.has(id):
		return _cache[id]
	var m := ShaderMaterial.new()
	m.shader = solid_shader()
	var P := {
		# ---------------- THE INHERITED
		# ART-DIRECTION 5.2: submerged-and-emerged iron. Near black, matte, scaled.
		"iron":     [Vector3(0.105, 0.055, 0.028), 0.72, 0.94, 0.0, 1.0, 0.95, 2.6, 0.26],
		"iron_pale":[Vector3(0.155, 0.085, 0.045), 0.70, 0.92, 0.0, 1.0, 0.85, 2.2, 0.30],
		# "still in use is polished bright by the work itself"
		"steel":    [Vector3(0.52, 0.50, 0.48), 0.22, 0.38, 1.0, 0.35, 0.0, 4.0, 0.10],
		"stone":    [Vector3(0.168, 0.150, 0.122), 0.80, 0.97, 0.0, 0.95, 0.45, 2.4, 0.34],
		"timber":   [Vector3(0.105, 0.072, 0.044), 0.78, 0.96, 0.0, 0.85, 0.30, 5.0, 0.32],
		"rock":     [Vector3(0.175, 0.134, 0.090), 0.84, 0.98, 0.0, 1.0, 0.10, 3.0, 0.25],
		"brick":    [Vector3(0.118, 0.070, 0.046), 0.75, 0.95, 0.0, 0.85, 0.65, 7.0, 0.34],
		# ---------------- THE BROUGHT
		# BONE #F2E6D2 in linear. The players' shells and cases.
		"bone":     [Vector3(0.887, 0.792, 0.646), 0.32, 0.50, 0.0, 0.28, 0.0, 4.0, 0.30],
		"kitgrey":  [Vector3(0.235, 0.245, 0.255), 0.34, 0.52, 0.0, 0.25, 0.0, 4.0, 0.24],
		"galv":     [Vector3(0.310, 0.320, 0.335), 0.36, 0.55, 0.72, 0.30, 0.0, 5.0, 0.20],
		"alu":      [Vector3(0.55, 0.56, 0.575), 0.20, 0.34, 0.9, 0.18, 0.0, 5.0, 0.14],
		"ember":    [Vector3(0.62, 0.19, 0.035), 0.35, 0.55, 0.0, 0.25, 0.0, 4.0, 0.22],
		"rubber":   [Vector3(0.030, 0.030, 0.032), 0.62, 0.82, 0.0, 0.35, 0.0, 6.0, 0.30],
		"plastic":  [Vector3(0.145, 0.150, 0.140), 0.40, 0.60, 0.0, 0.30, 0.0, 6.0, 0.28],
		"amber":    [Vector3(0.72, 0.46, 0.16), 0.38, 0.58, 0.0, 0.22, 0.0, 6.0, 0.18],
		"screen":   [Vector3(0.035, 0.040, 0.045), 0.08, 0.16, 0.0, 0.10, 0.0, 8.0, 0.05],
		"glass":    [Vector3(0.055, 0.058, 0.062), 0.05, 0.12, 0.0, 0.08, 0.0, 8.0, 0.05],
		# ---------------- scatter and growth
		"weed":     [Vector3(0.062, 0.075, 0.032), 0.70, 0.95, 0.0, 0.55, 0.0, 3.0, 0.10],
		"gravel":   [Vector3(0.175, 0.152, 0.118), 0.78, 0.97, 0.0, 1.0, 0.0, 12.0, 0.22],
		"litter":   [Vector3(0.30, 0.30, 0.29), 0.45, 0.75, 0.0, 0.55, 0.0, 9.0, 0.35],
		"water":    [Vector3(0.030, 0.036, 0.040), 0.03, 0.09, 0.0, 0.12, 0.0, 3.0, 0.0],
	}
	if not P.has(id):
		push_error("Mats: unknown material " + id)
		id = "iron"
	var e: Array = P[id]
	var c: Vector3 = e[0]
	m.set_shader_parameter("base_col", Color(c.x, c.y, c.z))
	m.set_shader_parameter("rough_lo", e[1])
	m.set_shader_parameter("rough_hi", e[2])
	m.set_shader_parameter("metal", e[3])
	m.set_shader_parameter("grain", e[4])
	m.set_shader_parameter("streak", e[5])
	m.set_shader_parameter("noise_scale", e[6])
	m.set_shader_parameter("dirt", e[7])
	m.set_shader_parameter("streak_col", Color(0.225, 0.092, 0.030))
	m.set_shader_parameter("dirt_col", Color(0.150, 0.122, 0.088))
	m.set_shader_parameter("wet_take", 1.0 if id != "water" else 0.0)
	m.set_shader_parameter("emissive", 0.0)
	_cache[id] = m
	return m

## Emissive fittings, in the palette entry's own colour. ART-DIRECTION: nothing
## in the world is ever cyan; red is lethal only; identity emissives at strength
## <= 3 and area over intensity.
static func emissive_of(id: String, strength: float) -> ShaderMaterial:
	var key := "E:" + id
	if _cache.has(key):
		return _cache[key]
	var base := get_mat(id)
	var m := ShaderMaterial.new()
	m.shader = solid_shader()
	for p in ["base_col", "rough_lo", "rough_hi", "metal", "grain", "streak",
			"noise_scale", "dirt", "streak_col", "dirt_col", "wet_take"]:
		m.set_shader_parameter(p, base.get_shader_parameter(p))
	m.set_shader_parameter("grain", 0.06)
	m.set_shader_parameter("dirt", 0.05)
	m.set_shader_parameter("emissive", strength)
	_cache[key] = m
	return m
