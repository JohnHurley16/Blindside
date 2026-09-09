// Loose rock, breakdown blocks and spoil. The same warm buff family as the
// wall (ART-DIRECTION 3.1) but a much cheaper shader: these are instanced in
// their tens of thousands and are never more than a few metres from the lamp.
// World-space only, no UV, no texture.
shader_type spatial;
render_mode blend_mix, depth_draw_opaque, cull_back, diffuse_lambert, specular_schlick_ggx;

uniform vec3 stone_dry = vec3(0.320, 0.250, 0.170);
uniform float wetness = 0.35;

varying vec3 wpos;
varying vec3 wn;

// A proper integer bit-mixing hash. The fract(sin()) family used in the first
// pass produced visible square lattice artefacts at high frequency -- the
// "QR code" look on every prop. This one is uniform.
uint uhash(uvec3 x) {
	x = x * 1664525u + 1013904223u;
	x.x += x.y * x.z; x.y += x.z * x.x; x.z += x.x * x.y;
	x ^= x >> 16u;
	x.x += x.y * x.z; x.y += x.z * x.x; x.z += x.x * x.y;
	return x.x;
}

float h31(vec3 p) {
	return float(uhash(uvec3(ivec3(floor(p + 0.5)) + 8192)) & 0xFFFFFFu) / 16777215.0;
}

float vnoise(vec3 p) {
	vec3 i = floor(p);
	vec3 f = fract(p);
	f = f * f * (3.0 - 2.0 * f);
	return mix(mix(mix(h31(i), h31(i + vec3(1, 0, 0)), f.x),
	               mix(h31(i + vec3(0, 1, 0)), h31(i + vec3(1, 1, 0)), f.x), f.y),
	           mix(mix(h31(i + vec3(0, 0, 1)), h31(i + vec3(1, 0, 1)), f.x),
	               mix(h31(i + vec3(0, 1, 1)), h31(i + vec3(1, 1, 1)), f.x), f.y), f.z);
}

float sh(vec3 q) {
	return (vnoise(q * 13.0) - 0.5) * 0.5 + (vnoise(q * 34.0) - 0.5) * 0.22;
}

void vertex() {
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	wn = normalize((MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz);
}

void fragment() {
	float n1 = vnoise(wpos * 5.3) * 0.62 + vnoise(wpos * 12.7 + vec3(4.1, 9.3, 2.7)) * 0.38;
	float n2 = vnoise(wpos * 29.0 + vec3(7.7, 1.9, 13.1));
	vec3 alb = stone_dry * COLOR.rgb * (0.62 + 0.70 * n1) * (0.86 + 0.28 * n2);
	// mud gathers low: wear is gravity, not noise (ART-DIRECTION 1)
	float low = clamp(1.0 - (wpos.y + 0.4) * 0.6, 0.0, 1.0);
	alb *= mix(1.0, 0.62, low * wetness);
	ALBEDO = alb;
	ROUGHNESS = mix(0.95, 0.30, wetness * (0.35 + 0.65 * low));
	SPECULAR = 0.35;
	// tangent-free normal perturbation: these meshes carry no UVs, so a
	// tangent-space NORMAL_MAP would be evaluated in a garbage basis.
	float e = 0.008;
	float b0 = sh(wpos);
	vec3 g = vec3(sh(wpos + vec3(e, 0.0, 0.0)) - b0,
	              sh(wpos + vec3(0.0, e, 0.0)) - b0,
	              sh(wpos + vec3(0.0, 0.0, e)) - b0) / e;
	vec3 nn = normalize(wn);
	g = g - nn * dot(g, nn);
	NORMAL = normalize((VIEW_MATRIX * vec4(normalize(nn - g * 0.016), 0.0)).xyz);
}
