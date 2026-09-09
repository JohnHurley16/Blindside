// ---------------------------------------------------------------------------
// BLINDSIDE -- the kit material.   PHOTOREAL PASS (2026-09-09)
//
// One shader, six parameter sets, covering every manufactured thing in the
// cave: cast iron, rubbed steel, waterlogged timber, glazed porcelain, and the
// two BROUGHT materials (composite and machined aluminium).
//
// ART-DIRECTION 1: "wear is gravity, not noise". Corrosion pools low and on
// upward faces, scuff clears the leading edges, and the only bright surfaces
// are the ones something is still rubbing (rail heads: rust = 0.15).
//
// What changed in this pass:
//   * METALLIC IS 0 OR 1, never in between. It was 0.55 for cast iron, which
//     is not a material that exists. Metal now means metal, and where the rust
//     has taken it the surface becomes a dielectric -- the one legitimate
//     in-between is the transition itself, and it is a mask, not a constant.
//   * A metal's ALBEDO is its F0 (about 0.56 for iron, 0.91 for aluminium),
//     not its diffuse colour. The mesh's vertex colour now modulates how
//     rubbed or how filthy the metal is, which is what it was really encoding.
//   * ROUGHNESS varies over every surface from the same field as the albedo:
//     casting skin, rubbed edges, rust bloom, and the water film on top.
//   * Two normal scales -- casting/saw texture at centimetres, machining and
//     grain at millimetres -- with their own distance fades.
//   * WETNESS comes from the water datum and from which way the face points,
//     not from a per-material constant. In a drowned mine the ironwork near
//     the sump is soaked and the ironwork at the crown is not.
//
// Colour comes from the mesh's own vertex colours, so one prop can be iron
// plate and bright steel head in one draw. World-space noise gives the
// large-scale staining; MODEL-space noise gives the grain and the machining,
// which is what makes the same instanced mesh not look like the same mesh.
// No image textures, no UVs -- the sampler3Ds are generated noise volumes
// shared with the rock (PROCEDURAL-AND-GODOT Q5).
// ---------------------------------------------------------------------------
shader_type spatial;
render_mode blend_mix, depth_draw_opaque, cull_back, diffuse_burley, specular_schlick_ggx;

uniform sampler3D t_fbm : filter_linear, repeat_enable;

uniform float metal : hint_range(0.0, 1.0) = 0.0;   // 0 or 1. Nothing between.
uniform float rough : hint_range(0.0, 1.0) = 0.68;
uniform float rust  : hint_range(0.0, 2.0) = 1.0;   // how far gone it is
uniform float wet_amt : hint_range(0.0, 1.0) = 0.35;
uniform float grain : hint_range(0.0, 1.0) = 0.0;   // timber
uniform vec3 rust_col = vec3(0.205, 0.088, 0.038);
uniform vec3 rust_col2 = vec3(0.115, 0.062, 0.036);  // the older, blacker scale
uniform vec3 metal_f0 = vec3(0.560, 0.570, 0.580);   // iron / steel
uniform float water_y = -1000.0;
uniform float micro_far = 2.4;
uniform float detail_far = 9.0;

varying vec3 wpos;
varying vec3 lpos;
varying vec3 wn;

float fb(vec3 p) { return texture(t_fbm, p).r; }

// the surface relief of a manufactured thing: casting skin, saw marks, pitting
float h_cast(vec3 q) {
	return (fb(q * (1.0 / 0.115)) - 0.5) * 0.0060
	     + (fb(q * (1.0 / 0.044) + vec3(3.1, 8.7, 1.3)) - 0.5) * 0.0024;
}
// machining, grain, the mill finish
float h_fine(vec3 q) {
	return (fb(q * (1.0 / 0.0090) + vec3(6.3, 2.9, 9.1)) - 0.5) * 0.00055;
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
	lpos = VERTEX;
	wn = normalize((MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz);
}

void fragment() {
	vec3 base = COLOR.rgb;
	float lum = dot(base, vec3(0.2126, 0.7152, 0.0722));
	vec3 n = normalize(wn);
	float dist = length(wpos - CAMERA_POSITION_WORLD);
	float f_det = clamp(1.0 - (dist - detail_far * 0.40) / (detail_far * 0.60), 0.0, 1.0);
	float f_mic = clamp(1.0 - (dist - micro_far * 0.35) / (micro_far * 0.65), 0.0, 1.0);

	// where this instance stands changes how far gone it is: one drift is not
	// uniformly rusted, and two identical sets 1.2 m apart are not twins.
	float patch = fb(wpos * (1.0 / 1.15));
	float mid = fb(wpos * (1.0 / 0.26)) * 0.6 + fb(wpos * (1.0 / 0.105) + vec3(5.5, 1.3, 8.9)) * 0.4;
	// model-space, so it travels with the instance and does not swim
	float fine = fb(lpos * (1.0 / 0.140)) * 0.55
	           + fb(lpos * (1.0 / 0.058) + vec3(11.3, 4.1, 27.7)) * 0.30
	           + fb(lpos * (1.0 / 0.024) + vec3(3.7, 19.1, 7.3)) * 0.15;

	// --- wetness: from the datum and from which way the face points ---------
	float above = wpos.y - water_y;
	float submerged = 1.0 - smoothstep(-0.02, 0.03, above);
	float w_datum = 1.0 - smoothstep(0.0, 1.6, max(above, 0.0));
	float upface = clamp(n.y, 0.0, 1.0);
	float wet = clamp(wet_amt * (0.35 + 0.65 * fb(wpos * (1.0 / 2.4) + vec3(0.0, 4.0, 0.0)))
	                  + w_datum * 0.55 + upface * 0.18 * wet_amt, 0.0, 1.0);
	wet = max(wet, submerged);

	// --- corrosion: gravity, not noise --------------------------------------
	float lowness = clamp(1.0 - (wpos.y - 0.1) * 0.55, 0.0, 1.2);
	float corr = smoothstep(0.12, 0.72, patch * 0.60 + mid * 0.40);
	corr = clamp(corr * rust * (0.50 + 0.55 * upface + 0.45 * lowness + 0.35 * w_datum), 0.0, 1.0);
	// the rubbed surfaces stay clean: the vertex colour is where that lives
	corr *= clamp(1.25 - lum * 1.6, 0.12, 1.0);
	// A FLOOR under the corrosion of anything ferrous. Making METALLIC binary
	// was right, but it exposed a real consequence: a rough BARE metal under a
	// lamp that sits at the eye has no diffuse term and returns almost nothing,
	// so every unrusted patch of cast iron went black. Nothing ferrous in a
	// drowned mine is bare, and this says so.
	corr = max(corr, rust * (0.42 + 0.30 * w_datum) * (0.55 + 0.45 * lowness)
	                 * clamp(1.25 - lum * 1.6, 0.12, 1.0));
	// two ages of rust: fresh orange bloom over old black scale
	float bloom = smoothstep(0.45, 0.85, mid);
	vec3 rustc = mix(rust_col2, rust_col, bloom);

	// --- albedo / metal ------------------------------------------------------
	// A metal's albedo IS its F0. The vertex colour says how rubbed it is.
	vec3 f0 = metal_f0 * clamp(0.34 + lum * 1.35, 0.34, 1.05);
	f0 *= 0.86 + 0.24 * fine;                     // the finish is not uniform
	vec3 diel = mix(base, rustc, clamp(corr * 1.05, 0.0, 1.0));
	diel *= 0.84 + 0.32 * fine;
	// timber: grain runs along the member's own long axis (model Z)
	if (grain > 0.0) {
		float g = fb(vec3(lpos.x * (1.0 / 0.077), lpos.y * (1.0 / 0.077), lpos.z * (1.0 / 0.62)));
		diel *= mix(1.0, 0.62 + 0.76 * g, grain);
		// waterlogged timber goes black at the ends and where it sits in muck
		diel *= mix(1.0, 0.55, clamp(lowness * 0.5 + w_datum * 0.5, 0.0, 1.0) * grain * 0.7);
	}
	float mmask = step(0.5, metal) * (1.0 - smoothstep(0.05, 0.62, corr));
	vec3 alb = mix(diel, f0, mmask);
	alb *= mix(1.0, 0.52, wet);                   // water darkens what it wets
	ALBEDO = clamp(alb, vec3(0.010), vec3(0.90));
	METALLIC = mmask;                             // 0 or 1 except in the transition

	// --- roughness -----------------------------------------------------------
	float r = rough;
	r = mix(r, 0.92, corr);                       // rust is matte and open
	r += (fine - 0.5) * 0.20;                     // casting skin varies
	r = mix(r, clamp(rough * 0.55, 0.04, 1.0), clamp(lum * 1.4, 0.0, 1.0) * (1.0 - corr));
	r = mix(r, 0.13, wet * (0.40 + 0.60 * lowness));
	r = mix(r, 0.06, submerged);
	// specular anti-aliasing at range
	ROUGHNESS = clamp(r, 0.05 + clamp(dist * 0.020, 0.0, 0.26), 1.0);
	SPECULAR = 0.5;

	// --- normals, two scales, tangent-free ----------------------------------
	// NOT NORMAL_MAP. These meshes are generated with no UVs and no tangents,
	// so a tangent-space normal map is evaluated in a garbage basis.
	float c0 = h_cast(lpos);
	if (f_det > 0.004) {
		float e = 0.0038;
		vec3 g = vec3(h_cast(lpos + vec3(e, 0.0, 0.0)) - c0,
		              h_cast(lpos + vec3(0.0, e, 0.0)) - c0,
		              h_cast(lpos + vec3(0.0, 0.0, e)) - c0) / e;
		n = bumped(n, g, (0.055 + corr * 0.30) * f_det);
	}
	float m0 = 0.0;
	if (f_mic > 0.004) {
		float e = 0.0006;
		m0 = h_fine(lpos);
		vec3 g = vec3(h_fine(lpos + vec3(e, 0.0, 0.0)) - m0,
		              h_fine(lpos + vec3(0.0, e, 0.0)) - m0,
		              h_fine(lpos + vec3(0.0, 0.0, e)) - m0) / e;
		n = bumped(n, g, (0.020 + corr * 0.10) * f_mic);
	}
	NORMAL = normalize((VIEW_MATRIX * vec4(n, 0.0)).xyz);

	// AO_LIGHT_AFFECT makes AO modulate DIRECT light. With world-space noise in
	// it, that painted a 10 cm mosaic of light and shade on every flat board --
	// the single ugliest thing in the first dense pass. Model-space and small.
	AO = clamp(0.80 + 22.0 * c0 * f_det, 0.62, 1.0);
	AO_LIGHT_AFFECT = 0.35;
}
