// BLINDSIDE machines spike -- the floor the machines stand on.
//
// Deliberately plain: this spike is about the machines, and the cave spike
// already owns the rock. It is here to catch the lamp's pool, take the
// machines' contact shadows and carry the 0.60 m rail gauge that the vision
// board's CLEAR rig paints under the Surveyor ("the agent fits between the
// rails"). ART 3.1 and 3.2 still apply: world-space, procedural, no UV.
shader_type spatial;
render_mode blend_mix, depth_draw_opaque, cull_back, diffuse_burley, specular_schlick_ggx;

uniform float studio = 1.0;     // 1 = the catalogue floor, 0 = mine floor
uniform float gauge = 1.0;      // paint the 0.60 m rail gauge
uniform vec3 studio_col = vec3(0.155, 0.155, 0.160);
uniform vec3 rock_col = vec3(0.165, 0.140, 0.112);

varying vec3 wpos;
varying vec3 wn;

float h31(vec3 p) {
	uvec3 q = uvec3(ivec3(floor(p))) * uvec3(1597334673u, 3812015801u, 2798796415u);
	uint n = (q.x ^ q.y ^ q.z) * 1597334673u;
	n = (n ^ (n >> 15u)) * 2246822519u;
	n = (n ^ (n >> 13u)) * 3266489917u;
	return float(n ^ (n >> 16u)) * (1.0 / 4294967296.0);
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

void vertex() {
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	wn = normalize((MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz);
}

void fragment() {
	float n1 = vnoise(wpos * 7.0) * 0.6 + vnoise(wpos * 23.0) * 0.3 + vnoise(wpos * 61.0) * 0.1;
	vec3 base = mix(rock_col, studio_col, studio);
	base *= 0.72 + 0.56 * n1;
	// the 0.60 m rail gauge: two 40 mm lines, painted, only in the catalogue rig
	float g = min(abs(abs(wpos.z) - 0.30), 1.0);
	float paint = gauge * (1.0 - smoothstep(0.012, 0.020, g));
	base = mix(base, vec3(0.24, 0.235, 0.22), paint);
	ALBEDO = base;
	ROUGHNESS = mix(0.96, 0.93, studio) - n1 * 0.05;
	METALLIC = 0.0;
	SPECULAR = 0.28;
	// tangent-free micro relief: no UVs here either
	float e = 0.006;
	float h0 = vnoise(wpos * 61.0);
	vec3 gr = vec3(vnoise((wpos + vec3(e, 0, 0)) * 61.0) - h0, 0.0,
				   vnoise((wpos + vec3(0, 0, e)) * 61.0) - h0) / e;
	vec3 n = normalize(wn - gr * 0.0013);
	NORMAL = normalize((VIEW_MATRIX * vec4(n, 0.0)).xyz);
}
