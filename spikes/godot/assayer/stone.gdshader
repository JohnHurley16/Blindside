// Loose rock, breakdown blocks, ballast and spoil.   PHOTOREAL PASS
//
// The same warm buff family as the wall (ART-DIRECTION 3.1) and now the same
// generated noise volumes, so a stone and the wall it fell off are made of the
// same field. These are instanced in their tens of thousands and are always
// within a few metres of the lamp, so they get the two close-range normal
// scales and the wetness field, and skip the metre-scale one -- a 60 mm stone
// has no metre scale.
//
// World-space only, no UV, no image texture.
shader_type spatial;
render_mode blend_mix, depth_draw_opaque, cull_back, diffuse_burley, specular_schlick_ggx;

uniform sampler3D t_fbm : filter_linear, repeat_enable;
uniform sampler3D t_cel : filter_linear, repeat_enable;

uniform vec3 stone_tint = vec3(1.00, 0.97, 0.93);
uniform vec3 stone_sub = vec3(0.086, 0.072, 0.060);
uniform float wetness = 0.35;
uniform float water_y = -1000.0;
uniform float micro_far = 2.2;
uniform float detail_far = 8.0;

const float LD = 0.086;    // detail: centimetres, sized to a stone
const float LM = 0.0128;   // micro:  millimetres

varying vec3 wpos;
varying vec3 wn;

float fb(vec3 p) { return texture(t_fbm, p).r; }
float cj(vec3 p) { return texture(t_cel, p).r; }

// the two close scales of a broken rock surface: conchoidal detail, then grain
float h_det(vec3 p) {
	return (fb(p * (1.0 / LD)) - 0.5) * 0.0130
	     + (fb(p * (1.0 / (LD * 0.36)) + vec3(3.3, 7.1, 1.9)) - 0.5) * 0.0052;
}
float h_mic(vec3 p) {
	return (fb(p * (1.0 / LM) + vec3(8.2, 1.1, 5.7)) - 0.5) * 0.00135;
}


// ---------------------------------------------------------------------------
// Perturb a world normal by the gradient of a height field, WITH A CLAMP.
//
// This clamp is not a nicety. `g` is dh/dx in metres per metre, and a noise
// volume sampled below its own Nyquist returns slopes of 3 or 4; `n - g*k`
// then tips the normal past 90 degrees and the surface faces AWAY from the
// only light in the world. That is what turned every loose stone underfoot
// into a black cut-out, and it survived three passes because a forced-albedo
// debug render still comes out black when the normal is inverted.
// atan(1.2) is about 50 degrees, which is as steep as a bump map should ever
// claim on geometry that is actually flat.
// ---------------------------------------------------------------------------
vec3 bumped(vec3 n, vec3 g, float k) {
	g -= n * dot(g, n);
	g *= k;
	float l = length(g);
	if (l > 1.2) {
		g *= 1.2 / l;
	}
	return normalize(n - g);
}

void vertex() {
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	wn = normalize((MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz);
}

void fragment() {
	vec3 n = normalize(wn);
	float dist = length(wpos - CAMERA_POSITION_WORLD);
	float f_det = clamp(1.0 - (dist - detail_far * 0.4) / (detail_far * 0.6), 0.0, 1.0);
	float f_mic = clamp(1.0 - (dist - micro_far * 0.35) / (micro_far * 0.65), 0.0, 1.0);

	// --- normal, two scales, tangent-free (these meshes carry no UVs) -------
	float d0 = h_det(wpos);
	if (f_det > 0.004) {
		float e = 0.0032;
		vec3 g = vec3(h_det(wpos + vec3(e, 0.0, 0.0)) - d0,
		              h_det(wpos + vec3(0.0, e, 0.0)) - d0,
		              h_det(wpos + vec3(0.0, 0.0, e)) - d0) / e;
		n = bumped(n, g, 0.30 * f_det);
	}
	float m0 = 0.0;
	if (f_mic > 0.004) {
		float e = 0.00055;
		m0 = h_mic(wpos);
		vec3 g = vec3(h_mic(wpos + vec3(e, 0.0, 0.0)) - m0,
		              h_mic(wpos + vec3(0.0, e, 0.0)) - m0,
		              h_mic(wpos + vec3(0.0, 0.0, e)) - m0) / e;
		n = bumped(n, g, 0.20 * f_mic);
	}

	// --- wetness: the same field the wall uses ------------------------------
	float above = wpos.y - water_y;
	float submerged = 1.0 - smoothstep(-0.02, 0.03, above);
	float w_datum = 1.0 - smoothstep(0.0, 1.5, max(above, 0.0));
	float w_patch = fb(wpos * (1.0 / 2.9) + vec3(0.0, 4.0, 0.0));
	// Water runs off the top of a stone and stays under its shoulder -- but
	// only a little. The first pass made up-faces much drier, which turned
	// every spall flake lying face-up on the floor into a sheet of white paper.
	// Nothing in a drowned mine that is catching drips is drier than the muck
	// it is lying in.
	float w_side = 1.0 - clamp(n.y, 0.0, 1.0) * 0.18;
	float wet = clamp(wetness * (0.50 + 0.50 * w_patch) * w_side + w_datum * 0.42
	                  + clamp(n.y, 0.0, 1.0) * 0.16 * wetness, 0.0, 1.0);
	wet = max(wet, submerged);

	// --- albedo -------------------------------------------------------------
	// COLOR.rgb is the mesh's own per-part value; the world-space fields do the
	// rest, so two identical stones 200 mm apart are not twins.
	float n1 = fb(wpos * (1.0 / 0.55)) * 0.62 + fb(wpos * (1.0 / 0.17) + vec3(4.1, 9.3, 2.7)) * 0.38;
	// COLOR.rgb ALREADY carries the stone value (C_STONE, the ART-DIRECTION 3.1
	// dry-lit rock). The first pass multiplied it by stone_dry as well, which
	// squared a 0.30 albedo into 0.09 and is why every loose stone underfoot
	// read as a black cut-out once the wetness field started darkening things.
	vec3 alb = COLOR.rgb * stone_tint * (0.66 + 0.50 * n1);
	// bedding survives into the broken block it came out of
	float bedv = sin(wpos.y * 20.0) * 0.5 + 0.5;
	alb *= 0.93 + 0.14 * bedv;
	// joints and chipped arrises
	float c = cj(wpos * (1.0 / 0.085));
	alb *= 1.0 - (1.0 - smoothstep(0.0, 0.10, c)) * 0.30;
	// the grain shows as value at reading distance and nowhere else
	alb *= 1.0 + m0 * 34.0 * f_mic;
	alb *= 1.0 + d0 * 5.0 * f_det;
	// silt clings to the underside and to anything sitting in the fines
	float low = clamp(1.0 - (wpos.y + 0.35) * 0.6, 0.0, 1.0);
	alb = mix(alb, vec3(0.118, 0.100, 0.080), low * 0.38 * (1.0 - clamp(n.y, 0.0, 1.0) * 0.55));
	alb = mix(alb, stone_sub, submerged);
	alb *= mix(1.0, 0.47, wet);           // water darkens what it wets
	ALBEDO = clamp(alb, vec3(0.012), vec3(0.55));

	// --- roughness: varies with the same field ------------------------------
	float r = 0.92 + (fb(wpos * (1.0 / 0.22) + vec3(2.0, 6.0, 8.0)) - 0.5) * 0.12;
	r += m0 * 26.0 * f_mic;               // millimetre roughness breakup
	r = mix(r, 0.14, wet * wet);
	r = mix(r, 0.05, submerged);
	ROUGHNESS = clamp(r, 0.04, 1.0);
	SPECULAR = mix(0.50, 0.58, wet);
	METALLIC = 0.0;
	NORMAL = normalize((VIEW_MATRIX * vec4(n, 0.0)).xyz);
	// a cavity term from the detail field: this is what stops a faceted stone
	// reading as an origami cut-out under a lamp that sits at the eye
	AO = clamp(0.68 + 26.0 * d0 * f_det, 0.34, 1.0);
	AO_LIGHT_AFFECT = 0.75;
}
