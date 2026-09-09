// ---------------------------------------------------------------------------
// BLINDSIDE -- the kit material. One shader, six parameter sets, and it covers
// every manufactured thing in the cave: cast iron, rubbed steel, waterlogged
// timber, glazed porcelain, and the two BROUGHT materials (composite and
// machined aluminium).
//
// ART-DIRECTION 1: "wear is gravity, not noise". Corrosion pools low and on
// upward faces, scuff clears the leading edges, and the only bright surfaces
// are the ones something is still rubbing (rail heads: rust = 0.15).
//
// Colour comes from the mesh's own vertex colours, so one prop can be iron
// plate and bright steel head in one draw. World-space noise gives the
// large-scale staining; MODEL-space noise gives the grain and the machining,
// which is what makes the same instanced mesh not look like the same mesh.
// No textures, no UVs.
// ---------------------------------------------------------------------------
shader_type spatial;
render_mode blend_mix, depth_draw_opaque, cull_back, diffuse_burley, specular_schlick_ggx;

uniform float metal : hint_range(0.0, 1.0) = 0.55;
uniform float rough : hint_range(0.0, 1.0) = 0.68;
uniform float rust  : hint_range(0.0, 2.0) = 1.0;   // how far gone it is
uniform float wet_amt : hint_range(0.0, 1.0) = 0.35;
uniform float grain : hint_range(0.0, 1.0) = 0.0;   // timber
uniform vec3 rust_col = vec3(0.230, 0.098, 0.042);

varying vec3 wpos;
varying vec3 lpos;
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

// the surface relief of a manufactured thing: casting texture, saw marks,
// pitting. Model-space, so it travels with the instance.
float wear_h(vec3 q) {
	return (vnoise(q * 9.0) - 0.5) * 0.55
	     + (vnoise(q * 23.0) - 0.5) * 0.22
	     + (vnoise(q * 57.0) - 0.5) * 0.09;
}

void vertex() {
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	lpos = VERTEX;
	wn = normalize((MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz);
}

void fragment() {
	vec3 base = COLOR.rgb;
	// where this instance stands changes how far gone it is: one drift is not
	// uniformly rusted, and two identical sets 1.2 m apart are not twins.
	float patch = vnoise(wpos * 0.9);
	float mid = vnoise(wpos * 4.1) * 0.6 + vnoise(wpos * 9.7 + vec3(5.5, 1.3, 8.9)) * 0.4;
	// three octaves at incommensurate frequencies and offsets: one octave of
	// value noise reads as an axis-aligned mosaic on a flat board.
	float fine = vnoise(lpos * 7.3 + wpos * 1.1) * 0.55
	           + vnoise(lpos * 17.7 + vec3(11.3, 4.1, 27.7)) * 0.30
	           + vnoise(lpos * 41.0 + vec3(3.7, 19.1, 7.3)) * 0.15;
	// gravity: rust runs down and pools on horizontals
	float upface = clamp(wn.y, 0.0, 1.0);
	float lowness = clamp(1.0 - (wpos.y - 0.1) * 0.55, 0.0, 1.2);
	float corr = smoothstep(0.30, 0.86, patch * 0.62 + mid * 0.38);
	corr = clamp(corr * rust * (0.55 + 0.55 * upface + 0.45 * lowness), 0.0, 1.0);

	vec3 alb = mix(base, rust_col, corr * 0.88);
	// scale flakes off in patches, showing darker metal beneath
	alb *= 0.84 + 0.30 * fine;
	// timber: grain runs along the member's own long axis (model Z)
	if (grain > 0.0) {
		float g = vnoise(vec3(lpos.x * 13.0, lpos.y * 13.0, lpos.z * 1.6));
		alb *= mix(1.0, 0.68 + 0.70 * g, grain);
	}
	ALBEDO = alb;
	METALLIC = metal * (1.0 - corr * 0.85);
	float r = mix(rough, 0.96, corr);
	// wet iron is the deep register's whole look: it keeps a glint
	r = mix(r, 0.14, wet_amt * (0.35 + 0.65 * lowness));
	ROUGHNESS = clamp(r, 0.04, 1.0);
	SPECULAR = 0.5;
	// NOT NORMAL_MAP. These meshes are generated with no UVs and no tangents,
	// so a tangent-space normal map is evaluated in a garbage basis -- that is
	// what painted the blocky light/dark mosaic over every prop in the first
	// dense pass. Perturb the world normal directly instead.
	float e = 0.010;
	float b0 = wear_h(lpos);
	vec3 g = vec3(wear_h(lpos + vec3(e, 0.0, 0.0)) - b0,
	              wear_h(lpos + vec3(0.0, e, 0.0)) - b0,
	              wear_h(lpos + vec3(0.0, 0.0, e)) - b0) / e;
	vec3 nn = normalize(wn);
	g = g - nn * dot(g, nn);
	nn = normalize(nn - g * (0.010 + corr * 0.026));
	NORMAL = normalize((VIEW_MATRIX * vec4(nn, 0.0)).xyz);
	// AO_LIGHT_AFFECT makes AO modulate DIRECT light. With world-space noise in
	// it, that painted a 10 cm mosaic of light and shade on every flat board --
	// the single ugliest thing in the first dense pass. Keep it small.
	AO = clamp(0.80 + 0.24 * mid, 0.66, 1.0);
	AO_LIGHT_AFFECT = 0.22;
}
