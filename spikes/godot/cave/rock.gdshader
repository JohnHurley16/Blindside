// ---------------------------------------------------------------------------
// BLINDSIDE -- the one rock material.
//
// ART-DIRECTION 3.1: one material, four scalars (wet / fracture / bedding /
// worked) plus a waterline. Three rock values, one warm buff family, no hue
// axis, no biome colour.
// ART-DIRECTION 3.2: world-space mapping, NEVER a UV, and not one image
// texture anywhere in the repo. Everything below is computed from the world
// position of the fragment.
//
// The scalars arrive per-vertex from the dressing layer:
//   COLOR.r  wet        0..1
//   COLOR.g  worked     0..1
//   COLOR.b  dark       0..1   (the depth field, albedo * (1 - 0.55*dark))
//   COLOR.a  iron       0..1   (proximity to something ferrous -> rust runs)
//   UV.x     axial distance along the passage, metres (drill rounds)
//   UV.y     perimeter position around the profile, 0..1 (shot-hole scallops)
//   UV2.x    height above the local waterline, metres (tide-mark crust)
//   UV2.y    packed rock type: floor(fracture01*31)*32 + floor(bedding01*31)
// ---------------------------------------------------------------------------
shader_type spatial;
render_mode blend_mix, depth_draw_opaque, cull_disabled, diffuse_burley, specular_schlick_ggx;

// the three rock values, ART-DIRECTION 3.1
uniform vec3 rock_dry   = vec3(0.340, 0.260, 0.175);
uniform vec3 rock_wet   = vec3(0.190, 0.150, 0.105);
uniform vec3 rock_sub   = vec3(0.090, 0.075, 0.062);
uniform vec3 rock_crust = vec3(0.520, 0.470, 0.400);
uniform vec3 rock_floor = vec3(0.420, 0.360, 0.280);
uniform vec3 rust_tint  = vec3(0.300, 0.130, 0.055);
uniform float detail_far = 13.0;   // metres past which octaves are dropped
uniform float bump_gain  = 1.0;

varying vec3 wpos;
varying vec3 wnorm;

// --- hash + value noise, world space ---------------------------------------
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
	float n000 = h31(i + vec3(0.0, 0.0, 0.0));
	float n100 = h31(i + vec3(1.0, 0.0, 0.0));
	float n010 = h31(i + vec3(0.0, 1.0, 0.0));
	float n110 = h31(i + vec3(1.0, 1.0, 0.0));
	float n001 = h31(i + vec3(0.0, 0.0, 1.0));
	float n101 = h31(i + vec3(1.0, 0.0, 1.0));
	float n011 = h31(i + vec3(0.0, 1.0, 1.0));
	float n111 = h31(i + vec3(1.0, 1.0, 1.0));
	return mix(mix(mix(n000, n100, f.x), mix(n010, n110, f.x), f.y),
	           mix(mix(n001, n101, f.x), mix(n011, n111, f.x), f.y), f.z);
}

// Domain warp. Un-warped voronoi reads as crazed pottery: every cell the same
// size, every joint the same curvature. Rock joints are not.
vec3 warp(vec3 p) {
	return p + vec3(vnoise(p * 0.7) - 0.5, vnoise(p * 0.7 + 13.0) - 0.5,
	                vnoise(p * 0.7 + 27.0) - 0.5) * 2.1;
}

// cellular / voronoi distance, the fracture term. Returns (F1, F2-F1).
vec2 cell2(vec3 p) {
	vec3 i = floor(p);
	vec3 f = p - i;
	float f1 = 8.0;
	float f2 = 8.0;
	for (int z = -1; z <= 1; z++) {
		for (int y = -1; y <= 1; y++) {
			for (int x = -1; x <= 1; x++) {
				vec3 g = vec3(float(x), float(y), float(z));
				vec3 o = vec3(h31(i + g), h31(i + g + vec3(37.0, 0.0, 0.0)),
				              h31(i + g + vec3(0.0, 91.0, 0.0)));
				float d = length(g + o - f);
				if (d < f1) { f2 = f1; f1 = d; }
				else if (d < f2) { f2 = d; }
			}
		}
	}
	return vec2(f1, f2 - f1);
}

// the height field the normal is perturbed by. `lod` drops octaves at range.
float rock_h(vec3 p, float fracture, float bedding, float worked,
             float axial, float perim, float lod) {
	float h = 0.0;
	// bedding: banded in world Y. Beds at 0.25..0.6 m (ART-DIRECTION 3.1).
	float bed_period = mix(0.25, 0.60, fract(floor(p.y * 0.7) * 0.37 + 0.31));
	float bed = sin(p.y * 6.2831853 / bed_period);
	h += bed * 0.016 * bedding;
	h += smoothstep(0.90, 1.0, bed * 0.5 + 0.5) * -0.030 * bedding;
	// broad form
	h += (vnoise(p * 0.9) - 0.5) * 0.22;
	h += (vnoise(p * 1.9) - 0.5) * 0.10;
	if (lod > 0.15) {
		h += (vnoise(p * 2.7) - 0.5) * 0.13 * lod;
		// fracture: voronoi at 3..14 per metre, crack lines darkened elsewhere
		vec2 c = cell2(warp(p * vec3(fracture * 1.5, fracture * 0.55, fracture * 1.5)));
		h += (1.0 - smoothstep(0.0, 0.07, c.y)) * -0.030 * lod;
		h += (c.x - 0.5) * 0.022 * lod;
	}
	if (lod > 0.55) {
		h += (vnoise(p * 8.3) - 0.5) * 0.055;
		h += (vnoise(p * 19.0) - 0.5) * 0.026;
		h += (vnoise(p * 43.0) - 0.5) * 0.012;
		h += (vnoise(p * 97.0) - 0.5) * 0.005;
	}
	// worked ground: half-barrel shot-hole scallops at 340 mm around the
	// perimeter, in 1.6 m rounds, each round phase-offset from the last
	// (ART-DIRECTION 3.3). Only where the industry actually cut.
	if (worked > 0.25) {
		float round_id = floor(axial / 1.6);
		float phase = fract(sin(round_id * 12.9898) * 43758.5453);
		float pm = perim * 7.5 + phase * 0.34;
		float sc = abs(fract(pm / 0.34) - 0.5) * 2.0;
		float endw = smoothstep(0.02, 0.16, fract(axial / 1.6));
		h += (sc * sc - 0.33) * 0.055 * worked * endw;
		// the collar of each round reads as a faint step
		h -= (1.0 - smoothstep(0.0, 0.06, fract(axial / 1.6))) * 0.02 * worked;
	}
	return h;
}

void vertex() {
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	wnorm = normalize((MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz);
}

void fragment() {
	float wet     = COLOR.r;
	float worked  = COLOR.g;
	float dark    = COLOR.b;
	float iron    = COLOR.a;
	float axial   = UV.x;
	float perim   = UV.y;
	float above   = UV2.x;               // metres above the local waterline
	float packed  = UV2.y;
	float frac01  = floor(packed / 32.0) / 31.0;
	float bed01   = fract(packed / 32.0) * 32.0 / 31.0;
	float fracture = mix(3.0, 14.0, clamp(frac01, 0.0, 1.0));
	float bedding  = mix(0.4, 3.5, clamp(bed01, 0.0, 1.0));

	float dist = length(VERTEX);         // view-space position => camera range
	float lod = clamp(1.0 - (dist - detail_far * 0.45) / detail_far, 0.0, 1.0);

	// --- normal, by central difference on the height field ------------------
	float e = 0.014 + dist * 0.004;
	float h0 = rock_h(wpos, fracture, bedding, worked, axial, perim, lod);
	float hx = rock_h(wpos + vec3(e, 0.0, 0.0), fracture, bedding, worked, axial, perim, lod);
	float hy = rock_h(wpos + vec3(0.0, e, 0.0), fracture, bedding, worked, axial, perim, lod);
	float hz = rock_h(wpos + vec3(0.0, 0.0, e), fracture, bedding, worked, axial, perim, lod);
	vec3 grad = vec3(hx - h0, hy - h0, hz - h0) / e;
	vec3 n = normalize(wnorm);
	grad = grad - n * dot(grad, n);      // tangential part only
	float amp = mix(0.15, 0.9, clamp(frac01, 0.0, 1.0)) * bump_gain * (0.4 + 0.6 * lod);
	n = normalize(n - grad * amp * 0.62);
	NORMAL = normalize((VIEW_MATRIX * vec4(n, 0.0)).xyz);

	// --- albedo -------------------------------------------------------------
	float submerged = 1.0 - step(0.0, above);
	vec3 alb = mix(rock_dry, rock_wet, clamp(wet, 0.0, 1.0));
	alb = mix(alb, rock_sub, submerged);
	// the floor is scoured where the industry trammed over it
	float up = clamp(n.y, 0.0, 1.0);
	alb = mix(alb, rock_floor, up * up * worked * 0.55);
	// the 0.12 m mineral tide-mark crust above the line: albedo x1.7, matte
	float crust = (1.0 - submerged) * (1.0 - smoothstep(0.0, 0.12, above))
	              * smoothstep(-0.02, 0.01, above);
	crust *= 0.55 + 0.45 * vnoise(wpos * 9.0);
	alb = mix(alb, rock_crust, crust);
	// bedding as value, not hue
	float bed_period2 = mix(0.25, 0.60, fract(floor(wpos.y * 0.7) * 0.37 + 0.31));
	float bedv = sin(wpos.y * 6.2831853 / bed_period2) * 0.5 + 0.5;
	alb *= 1.0 + (bedv - 0.5) * 0.52 * (bedding / 3.5);
	// and a hard parting every few beds, which is what you actually count
	float part = smoothstep(0.86, 0.995, bedv);
	alb *= 1.0 - part * 0.34 * (bedding / 3.5);
	// crack darkening: the voronoi edges read as open joints
	if (lod > 0.15) {
		vec2 c = cell2(warp(wpos * vec3(fracture * 1.5, fracture * 0.55, fracture * 1.5)));
		alb *= 1.0 - (1.0 - smoothstep(0.0, 0.022, c.y)) * 0.18 * lod;
		// a second, coarser joint set: the beds part as well as the blocks
		vec2 c2v = cell2(warp(wpos * vec3(0.42, 2.1, 0.42)));
		alb *= 1.0 - (1.0 - smoothstep(0.0, 0.040, c2v.y)) * 0.24;
	}
	// mineral staining: broad, low-frequency, warm; nothing is evenly coloured
	float stain = vnoise(wpos * vec3(0.35, 0.12, 0.35));
	alb *= 0.78 + 0.42 * stain;
	// rust runs: streaks that fall from anything ferrous. Stretched in Y so
	// they run downward, gated on the iron channel and only below the source.
	float streak = vnoise(vec3(wpos.x * 6.0, wpos.y * 0.55, wpos.z * 6.0));
	streak = smoothstep(0.52, 0.85, streak) * iron;
	alb = mix(alb, rust_tint, clamp(streak * 0.85, 0.0, 1.0));
	// depth is drawn as darkness (ART-DIRECTION 7)
	alb *= 1.0 - 0.55 * clamp(dark, 0.0, 1.0);

	ALBEDO = alb;
	// wet rock returns a hard glint at any angle; dry rock returns nothing
	// (ART-DIRECTION 2.7 -- this is what makes a wet passage findable).
	// only genuinely wet rock shines. A gentle linear ramp made the whole
	// cave read as glazed pottery.
	float w2 = smoothstep(0.40, 0.95, clamp(wet, 0.0, 1.0));
	float rough = mix(0.95, 0.12, w2);
	rough = mix(rough, 0.92, crust);          // the crust is matte
	rough = mix(rough, 0.07, submerged);
	ROUGHNESS = rough;
	SPECULAR = mix(0.18, 0.55, w2);
	METALLIC = 0.0;
	// a cheap cavity term so joints and scallops hold shape at grazing light
	AO = clamp(0.55 + 0.75 * (h0 + 0.25), 0.35, 1.0);
	AO_LIGHT_AFFECT = 0.9;
}
