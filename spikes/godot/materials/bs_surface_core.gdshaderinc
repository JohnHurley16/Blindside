// ---------------------------------------------------------------------------
// BLINDSIDE -- the one surface material, parameterised.
//
// Every opaque surface in the game is this file with different uniforms. It is
// not a switch over material types: it is a stack of layers, each with an
// amplitude, and a material is a set of amplitudes. A material that does not
// want a layer sets its amplitude to zero and the branch is skipped -- uniform
// branches are coherent across a draw call, so a rock pays nothing for the
// rust code and vice versa.
//
// Feature #defines, set by the thin .gdshader that includes this file. Leaving
// one out removes the code, not just the branch, which is how a shipping
// variant gets its cost down (see NOTES.md, "Adoption").
//   BS_F_VORO     voronoi joints / grains       (rock, aggregate, concrete)
//   BS_F_BED      bedding bands                 (rock)
//   BS_F_GRAIN    directional grain and lay     (timber, brushed metal)
//   BS_F_METAL    rust / paint / chipping       (iron, steel)
//   BS_F_PRINT    printed labels                (the players' register)
//   BS_F_POM      parallax occlusion mapping
//
// Coordinates: world space, always. No UV is read for anything except the
// printed-label rectangle, which is a decal on a manufactured part and is the
// one place a UV is honest. ART-DIRECTION 3.2.
// ---------------------------------------------------------------------------
#ifndef BS_SURFACE_CORE_INC
#define BS_SURFACE_CORE_INC

#include "res://bs_noise.gdshaderinc"

// --- project-wide controls, driven by the testbed and by the game client ---
global uniform float bs_wet;           // the wetness slider: 0 dry, 1 drowned
global uniform float bs_debug;         // 0 shaded 1 albedo 2 rough 3 normal 4 AO 5 field 6 metallic
global uniform float bs_pom_on;        // master parallax enable / scale
global uniform float bs_normal_gain;   // master normal amplitude (the sweep)
global uniform float bs_detail_gain;   // master detail+micro enable (ablation)

// --- albedo ----------------------------------------------------------------
// LINEAR values, stated as measured reflectance. Not sRGB, not source_color.
uniform vec3  alb_lo = vec3(0.040, 0.033, 0.026);
uniform vec3  alb_hi = vec3(0.105, 0.088, 0.070);
uniform float alb_curve = 1.0;         // shaping of the field before the mix
uniform float alb_cell = 0.0;          // per-voronoi-cell value scatter
uniform float macro_var = 0.0;         // low-frequency value variation
uniform float macro_freq = 0.55;       // cycles per metre
uniform vec3  stain_col = vec3(0.09, 0.045, 0.020);
uniform float stain_amt = 0.0;
uniform float stain_freq = 0.30;
uniform float stain_sharp = 1.0;

// --- specular ---------------------------------------------------------------
uniform float rough_lo = 0.62;         // roughness where the field is 0
uniform float rough_hi = 0.94;         // roughness where the field is 1
uniform float rough_micro = 0.10;      // roughness the micro band turns into at range
uniform float metallic = 0.0;
uniform float spec = 0.5;              // Godot SPECULAR; 0.5 == F0 0.04

// --- the height field, in metres, at three scales ---------------------------
uniform float form_freq = 1.4;         // cycles per metre
uniform float form_amp = 0.010;        // metres
uniform float form_ridge = 0.0;        // 0 billowy (weathered), 1 ridged (fresh)
uniform float detail_freq = 11.0;
uniform float detail_amp = 0.0022;
uniform float micro_freq = 90.0;
uniform float micro_amp = 0.00022;

uniform float voro_freq = 0.0;         // primary cells: joints or stones
uniform float voro_amp = 0.0;          // metres
uniform float voro_pebble = 0.0;       // 0 crack relief, 1 domed grains
uniform float voro_warp = 0.9;
uniform float voro2_freq = 0.0;        // secondary cells: fines between stones
uniform float voro2_amp = 0.0;
uniform float voro2_pebble = 1.0;

uniform float bed_freq = 0.0;          // bedding, cycles per metre in world Y
uniform float bed_amp = 0.0;
uniform float bed_value = 0.0;         // bedding as albedo value, not just relief

uniform float grain_freq = 0.0;
uniform float grain_amp = 0.0;
uniform float grain_stretch = 0.05;    // 0.05 == 20:1 anisotropy along the axis
uniform vec3  grain_axis = vec3(1.0, 0.0, 0.0);
uniform float grain_value = 0.0;       // grain as albedo value
uniform float weave_amt = 0.0;         // 2x2 twill, for woven composite
uniform float weave_freq = 90.0;       // tows per metre

// --- occlusion --------------------------------------------------------------
uniform float ao_strength = 0.0;       // 0 = the cheap cavity term only
uniform float ao_radius = 0.05;        // metres; ~1.5 cells of the form band

// --- apparent depth ---------------------------------------------------------
uniform float pom_depth = 0.0;         // metres of apparent relief
uniform float pom_far = 5.0;           // metres past which parallax is off
uniform int   pom_steps_near = 13;
uniform int   pom_steps_far = 4;

// --- water ------------------------------------------------------------------
uniform float wet_gain = 1.0;          // how much of bs_wet this material feels
uniform float wet_darken = 0.55;       // albedo multiplier when soaked
uniform float wet_rough = 0.09;        // roughness when soaked
uniform float pool_gain = 1.0;         // how strongly water gathers in hollows
uniform float wet_bias = 0.0;          // this material's own standing wetness
uniform float wet_fill = 0.9;          // how much water fills the micro relief

// --- metal ------------------------------------------------------------------
uniform float rust_amt = 0.0;          // 0 bare .. 1 rotten and laminating
uniform float rust_freq = 4.0;
uniform vec3  rust_col = vec3(0.150, 0.052, 0.020);
uniform vec3  rust_col_old = vec3(0.062, 0.030, 0.018);
uniform float paint_amt = 0.0;         // 0 bare .. 1 sound paint
uniform vec3  paint_col = vec3(0.028, 0.040, 0.036);
uniform float paint_rough = 0.42;
uniform float chip_amt = 0.0;          // paint loss, 0..1

// --- manufactured -----------------------------------------------------------
uniform float lay_amt = 0.0;           // machined / brushed lay, roughness only
uniform float lay_freq = 900.0;
uniform vec3  lay_axis = vec3(0.0, 0.0, 1.0);
uniform float edge_wear = 0.0;         // convex edges polish and lighten
uniform float print_amt = 0.0;         // printed label
uniform vec3  print_bg = vec3(0.72, 0.71, 0.68);
uniform vec3  print_fg = vec3(0.020, 0.020, 0.021);

varying vec3 v_wpos;
varying vec3 v_wnorm;

// ---------------------------------------------------------------------------
// the height field, banded
// ---------------------------------------------------------------------------

// FORM: what you read in silhouette and at three metres. This is the band the
// parallax march uses, because it is the one that carries apparent depth.
float bs_form(vec3 p) {
	float h = 0.0;
	if (form_amp > 0.0) {
		vec3 q = p * form_freq;
		h += mix(bs_fbm3(q), bs_ridge(q) - 0.42, form_ridge) * form_amp;
	}
#ifdef BS_F_BED
	if (bed_amp > 0.0) {
		float y = p.y * bed_freq + bs_gnoise(p * 0.35) * 0.9;
		float b = sin(y * 6.2831853);
		// a hard parting every few beds -- that is what you actually count
		h += (b * 0.35 - smoothstep(0.80, 1.0, b) * 1.15) * bed_amp;
	}
#endif
#ifdef BS_F_VORO
	if (voro_amp > 0.0) {
		vec3 c = bs_cell(bs_warp(p * voro_freq, voro_warp));
		float crack = -(1.0 - smoothstep(0.0, 0.10, c.y));
		// A stone is a plateau with a defined shoulder, and every stone sits at
		// its own height. A smooth 1-F1 dome reads as bubble wrap: it has no
		// flat face for a highlight to sit on and no edge for a shadow to
		// break against, which is most of what says "crushed rock".
		float d = clamp(1.0 - c.x * 1.70, 0.0, 1.0);
		d = d * d * (3.0 - 2.0 * d);
		d *= 0.50 + 0.95 * c.z;                    // half-buried, not a layer
		h += mix(crack, d - 0.45, voro_pebble) * voro_amp;
	}
#endif
	return h;
}

// A deliberately cheap form band, for the occlusion taps only. It drops the
// domain warp (three gradient-noise calls) and two of the three fbm octaves.
// The occlusion term is a horizon estimate over a few centimetres; it does not
// need the warp, and paying for the warp four more times per pixel is what
// took the aggregate case from 38 ms to 56.
float bs_form_ao(vec3 p) {
	float h = 0.0;
	if (form_amp > 0.0) { h += bs_gnoise(p * form_freq) * 0.53 * form_amp; }
#ifdef BS_F_VORO
	if (voro_amp > 0.0) {
		vec3 c = bs_cell(p * voro_freq);
		float d = clamp(1.0 - c.x * 1.70, 0.0, 1.0);
		d = d * d * (3.0 - 2.0 * d);
		d *= 0.50 + 0.95 * c.z;
		h += mix(-(1.0 - smoothstep(0.0, 0.10, c.y)), d - 0.45, voro_pebble) * voro_amp;
	}
#endif
	return h;
}

// DETAIL: what you read at a metre. Never touched by the parallax march.
float bs_detail(vec3 p) {
	float h = 0.0;
	if (detail_amp > 0.0) { h += bs_fbm3(p * detail_freq) * detail_amp; }
#ifdef BS_F_VORO
	if (voro2_amp > 0.0) {
		vec3 c = bs_cell(bs_warp(p * voro2_freq, voro_warp * 0.4));
		float crack = -(1.0 - smoothstep(0.0, 0.14, c.y));
		float d = clamp(1.0 - c.x * 1.60, 0.0, 1.0);
		d = d * d * (3.0 - 2.0 * d);
		d *= 0.45 + 1.00 * c.z;
		h += mix(crack, d - 0.45, voro2_pebble) * voro2_amp;
	}
#endif
#ifdef BS_F_GRAIN
	if (grain_amp > 0.0) {
		vec3 q = p * grain_freq;
		q -= grain_axis * dot(q, grain_axis) * (1.0 - grain_stretch);
		float rings = bs_fbm2(q) * 5.0 + bs_gnoise(q * 3.1) * 0.6;
		h += (abs(fract(rings) - 0.5) * 2.0 - 0.5) * grain_amp;
	}
	if (weave_amt > 0.0) {
		// 2x2 twill. The dominant world axis picks the plane, which is exactly
		// what triplanar does, and a moulded composite panel is flat enough
		// that the seam never shows.
		vec3 an = abs(normalize(v_wnorm));
		vec2 uv = an.y > max(an.x, an.z) ? p.xz : (an.x > an.z ? p.zy : p.xy);
		vec2 gq = uv * weave_freq;
		vec2 cq = floor(gq * 0.5);
		float over = mod(cq.x + cq.y, 2.0);
		float band = mix(fract(gq.x * 0.5), fract(gq.y * 0.5), over);
		h += (sin(band * 3.14159265) - 0.5) * weave_amt;
	}
#endif
	return h;
}

// MICRO: what stops a surface going flat when a machine is standing on it.
float bs_micro(vec3 p) {
	if (micro_amp <= 0.0) { return 0.0; }
	return (bs_gnoise(p * micro_freq) + bs_gnoise(p * micro_freq * 2.61 + 5.0) * 0.5)
	       * micro_amp;
}

// ---------------------------------------------------------------------------
// parallax occlusion mapping, world space, no tangent basis needed
//
// The height volume hangs below the geometric surface: the mesh is the TOP of
// the material and the field descends `pom_depth` into it. The march runs on
// the tangent plane through the fragment, so it is correct for a mesh with no
// UV and no tangents -- which is every mesh a generator makes.
// ---------------------------------------------------------------------------
#ifdef BS_F_POM
float bs_form01(vec3 p, float inv_span) {
	return clamp(bs_form(p) * inv_span + 0.5, 0.0, 1.0);
}

vec3 bs_pom_march(vec3 P, vec3 N, vec3 V, float depth, int steps, float inv_span) {
	float ndv = max(-dot(V, N), 0.10);
	vec3 tdir = V + N * ndv;                       // tangential part of the ray
	float dt = depth / float(steps);
	float prev_rd = 0.0;
	float prev_sd = depth * (1.0 - bs_form01(P, inv_span));
	if (prev_sd <= 0.0) { return P; }
	vec3 q = P;
	for (int i = 1; i <= 32; i++) {
		if (i > steps) { break; }
		float rd = dt * float(i);
		q = P + tdir * (rd / ndv);
		float sd = depth * (1.0 - bs_form01(q, inv_span));
		if (rd >= sd) {
			// Bracketed. Four bisection steps beat sixteen more linear ones:
			// the linear march only has to find the interval, and the height
			// field here contains a 3D voronoi, which is by far the most
			// expensive thing in the shader. Halving the linear step count
			// took the underfoot case from 42 ms to under 20.
			float lo = dt * float(i - 1);
			float hi = rd;
			for (int k = 0; k < 4; k++) {
				float mt = (lo + hi) * 0.5;
				vec3 q2 = P + tdir * (mt / ndv);
				if (mt >= depth * (1.0 - bs_form01(q2, inv_span))) { hi = mt; }
				else { lo = mt; }
			}
			return P + tdir * (hi / ndv);
		}
		prev_rd = rd;
		prev_sd = sd;
	}
	return q;
}
#endif

void vertex() {
	v_wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	v_wnorm = normalize((MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz);
}

void fragment() {
	vec3 N = normalize(v_wnorm);
	vec3 P = v_wpos;
	vec3 cam = (INV_VIEW_MATRIX * vec4(0.0, 0.0, 0.0, 1.0)).xyz;
	vec3 Vd = normalize(P - cam);
	float dist = length(P - cam);

	// The pixel footprint in world metres. Every band is faded out when its
	// wavelength approaches it: that, and not a hand-tuned distance, is what
	// stops high-frequency detail shimmering at range, and it is automatically
	// correct at any resolution and any field of view.
	float fp = max(length(fwidth(P)), 1e-5);
	float span = max(form_amp * 1.6 + voro_amp * 1.2 + bed_amp * 1.1, 1e-4);
	float inv_span = 0.5 / span;

	// --- apparent depth ------------------------------------------------------
	vec3 S = P;                                     // the shading position
#ifdef BS_F_POM
	float pom_fade = clamp(1.0 - dist / max(pom_far, 0.1), 0.0, 1.0);
	pom_fade *= pom_fade;
	float pd = pom_depth * pom_fade * bs_pom_on;
	if (pd > 0.0002) {
		int steps = int(mix(float(pom_steps_far), float(pom_steps_near), pom_fade));
		S = bs_pom_march(P, N, Vd, pd, steps, inv_span);
	}
#endif

	// --- the three normal bands ---------------------------------------------
	// Forward differences along two tangent directions: two extra evaluations
	// per band rather than three, and no tangent attribute needed on the mesh.
	vec3 Tn = normalize(cross(N, abs(N.y) < 0.9 ? vec3(0.0, 1.0, 0.0) : vec3(1.0, 0.0, 0.0)));
	vec3 Bn = cross(N, Tn);

	float f_form = clamp(1.0 - fp * form_freq * 2.2, 0.0, 1.0);
	float f_det = clamp(1.0 - fp * detail_freq * 2.2, 0.0, 1.0) * bs_detail_gain;
	float f_mic = clamp(1.0 - fp * micro_freq * 2.2, 0.0, 1.0) * bs_detail_gain;

	float e1 = max(0.30 / max(form_freq, 0.01), fp * 1.2);
	float h_form = bs_form(S);
	vec3 g = vec3(0.0);
	if (f_form > 0.002) {
		float a = bs_form(S + Tn * e1);
		float b = bs_form(S + Bn * e1);
		g += ((a - h_form) * Tn + (b - h_form) * Bn) / e1 * f_form;
	}
	float h_det = 0.0;
	if (f_det > 0.002 && (detail_amp > 0.0 || voro2_amp > 0.0 || grain_amp > 0.0)) {
		float e2 = max(0.30 / max(detail_freq, 0.01), fp * 1.2);
		h_det = bs_detail(S);
		float a = bs_detail(S + Tn * e2);
		float b = bs_detail(S + Bn * e2);
		g += ((a - h_det) * Tn + (b - h_det) * Bn) / e2 * f_det;
	}
	float h_mic = 0.0;
	if (f_mic > 0.002 && micro_amp > 0.0) {
		float e3 = max(0.30 / max(micro_freq, 0.01), fp * 1.2);
		h_mic = bs_micro(S);
		float a = bs_micro(S + Tn * e3);
		float b = bs_micro(S + Bn * e3);
		g += ((a - h_mic) * Tn + (b - h_mic) * Bn) / e3 * f_mic;
	}

	// --- the field that drives everything ------------------------------------
	// One number, from the same height field the normals came from. Albedo,
	// roughness, AO and wetness all read it, which is why they correlate the
	// way a real surface does instead of looking like three unrelated masks.
	float field = clamp(h_form * inv_span + 0.5
	                  + h_det / max(detail_amp * 2.2, 1e-4) * 0.16 * f_det
	                  + h_mic / max(micro_amp * 2.2, 1e-4) * 0.07 * f_mic, 0.0, 1.0);
	float fieldc = pow(field, alb_curve);

	// --- albedo ---------------------------------------------------------------
	vec3 alb = mix(alb_lo, alb_hi, fieldc);

#ifdef BS_F_VORO
	if (alb_cell > 0.0 && voro_amp > 0.0) {
		// Every stone in an aggregate is a different stone. Without this the
		// whole surface reads as one lumpy object rather than as many pieces.
		vec3 c = bs_cell(bs_warp(S * voro_freq, voro_warp));
		alb *= 1.0 + (c.z - 0.5) * 2.0 * alb_cell;
		// the space between stones holds fines: a soft dark band, not a drawn
		// line. A narrow one reads as crazed pottery, which is the classic
		// procedural-voronoi tell.
		alb *= 1.0 - (1.0 - smoothstep(0.0, 0.115, c.y)) * 0.34;
	}
#endif
#ifdef BS_F_BED
	if (bed_value > 0.0) {
		float b = sin((S.y * bed_freq + bs_gnoise(S * 0.35) * 0.9) * 6.2831853) * 0.5 + 0.5;
		alb *= 1.0 + (b - 0.5) * bed_value;
	}
#endif
#ifdef BS_F_GRAIN
	if (grain_value > 0.0) {
		vec3 q = S * grain_freq;
		q -= grain_axis * dot(q, grain_axis) * (1.0 - grain_stretch);
		float rings = bs_fbm2(q) * 5.0 + bs_gnoise(q * 3.1) * 0.6;
		float r = abs(fract(rings) - 0.5) * 2.0;
		alb *= 1.0 - r * grain_value;
	}
#endif
	// Nothing real is one value over a square metre. Two octaves of
	// low-frequency value variation, independent of the height field, is what
	// stops a flat face reading as a painted plane. It is the cheapest single
	// item on the photoreal list and at three metres it does more than any of
	// the normal bands.
	float mv = 0.0;
	if (macro_var > 0.0) {
		mv = bs_gnoise(S * macro_freq) * 0.66
		   + bs_gnoise(S * macro_freq * 2.7 + 31.0) * 0.34;
		alb *= 1.0 + mv * macro_var;
	}
	if (stain_amt > 0.0) {
		// Mineral staining. Broad, low-frequency, and the one place this family
		// carries hue -- see NOTES.md, "Rules bent".
		float s = bs_fbm3(S * vec3(stain_freq, stain_freq * 0.42, stain_freq));
		s = smoothstep(-0.10, 0.34, s * stain_sharp);
		alb = mix(alb, stain_col, s * stain_amt);
	}

	float rough = mix(rough_lo, rough_hi, field);
	rough = clamp(rough - mv * macro_var * 0.35, 0.02, 1.0);
	float metal = metallic;
	float specular = spec;

	// --- metal: paint, rust, and the only legitimate metallic gradient --------
#ifdef BS_F_METAL
	if (rust_amt > 0.0) {
		float r = bs_fbm4(S * rust_freq) + bs_fbm2(S * rust_freq * 5.3) * 0.35;
		// rust starts in the low points and at the edges, and creeps outward
		r += (0.5 - field) * 0.55;
		// A wide transition. A narrow one gives the terrazzo look: hard-edged
		// islands of oxide with clean metal between them, which is what rust
		// does on a car in a game and never on iron in a wet mine.
		float rust_mask = smoothstep(0.10 - rust_amt * 0.55, 0.62 - rust_amt * 0.30,
		                             r + rust_amt * 0.30);
		// runs below the source: stretched vertically. Wear is gravity, not noise.
		float run = bs_fbm2(vec3(S.x * 9.0, S.y * 0.7, S.z * 9.0));
		rust_mask = clamp(rust_mask + smoothstep(0.18, 0.46, run) * rust_amt * 0.30, 0.0, 1.0);
		vec3 rc = mix(rust_col, rust_col_old, smoothstep(0.35, 0.95, rust_mask));
		alb = mix(alb, rc, rust_mask);
		// METALLIC is 0 or 1 everywhere except across this transition, which is
		// the one place in the game where a surface really is part oxide and
		// part metal inside one pixel.
		metal = metallic * (1.0 - rust_mask);
		rough = mix(rough, mix(0.55, 0.93, rust_mask), rust_mask);
	}
	if (paint_amt > 0.0) {
		float chip = 0.0;
		if (chip_amt > 0.0) {
			float c = bs_fbm4(S * 6.5) + (0.5 - field) * 0.7;
			chip = clamp(smoothstep(0.30 - chip_amt * 0.55, 0.40 - chip_amt * 0.30, c), 0.0, 1.0);
		}
		float cover = paint_amt * (1.0 - chip);
		alb = mix(alb, paint_col, cover);
		rough = mix(rough, paint_rough + bs_gnoise(S * 30.0) * 0.05, cover);
		metal = metal * (1.0 - cover);
		specular = mix(specular, 0.55, cover);
	}
#endif

	// --- manufactured: machining lay, edge wear, printed labels ---------------
#ifdef BS_F_GRAIN
	if (lay_amt > 0.0) {
		// A turned or brushed lay is roughness anisotropy. Modelled here as a
		// high-frequency roughness modulation along one axis, which reads
		// correctly from every angle a player sees and needs no tangent.
		vec3 q = S * lay_freq;
		q -= lay_axis * dot(q, lay_axis) * 0.995;
		rough += (bs_vnoise(q) - 0.5) * lay_amt;
	}
#endif
	if (edge_wear > 0.0) {
		// Convex edges polish. Curvature from the derivative of the shading
		// normal, which costs two derivatives and nothing else.
		float curv = length(fwidth(N)) / max(fp, 1e-5);
		float e = clamp(curv * 0.010, 0.0, 1.0);
		alb *= 1.0 + e * edge_wear * 0.55;
		rough = mix(rough, rough * 0.45, e * edge_wear);
	}
#ifdef BS_F_PRINT
	if (print_amt > 0.0) {
		// A printed label. This is the one UV in the family, because a label is
		// applied to a manufactured part in a factory and a manufactured part
		// has an authored surface. Everything else is world space.
		vec2 c = abs(UV - 0.5);
		if (c.x < 0.34 && c.y < 0.16) {
			vec2 lp = (UV - vec2(0.16, 0.34)) / vec2(0.68, 0.32);
			float bars = step(0.55, bs_h1(vec3(floor(lp.x * 34.0), 3.0, 0.0)))
			           * step(0.10, lp.y) * step(lp.y, 0.42);
			float t1 = step(0.62, bs_h1(vec3(floor(lp.x * 26.0), 9.0, 0.0)))
			         * step(0.52, lp.y) * step(lp.y, 0.68);
			float t2 = step(0.68, bs_h1(vec3(floor(lp.x * 20.0), 15.0, 0.0)))
			         * step(0.74, lp.y) * step(lp.y, 0.88);
			float ink = clamp(bars + t1 + t2, 0.0, 1.0);
			vec3 lab = mix(print_bg, print_fg, ink);
			lab *= 0.80 + 0.30 * bs_fbm2(S * 60.0);       // labels get grubby
			alb = mix(alb, lab, print_amt);
			rough = mix(rough, 0.34 + ink * 0.10, print_amt);
			metal = metal * (1.0 - print_amt);
		}
	}
#endif

	// --- what the fading bands turn into --------------------------------------
	// A normal band that has faded out has not stopped existing: its geometry is
	// now smaller than a pixel, which is the definition of roughness. Folding it
	// back in is what stops a surface going glossy and plastic at range -- the
	// single most common cause of "it looked fine in the close-up".
	float lost = (1.0 - f_mic) * rough_micro + (1.0 - f_det) * rough_micro * 0.55;
	rough = sqrt(clamp(rough * rough + lost * lost, 0.0, 1.0));

	// --- water ----------------------------------------------------------------
	float w = clamp(bs_wet * wet_gain + wet_bias, 0.0, 1.0);
	// A film that forms everywhere, and standing water that fills the hollows
	// from the bottom upward. `lvl` is where the water surface sits inside the
	// height field's own 0..1 range: at w = 0.5 it covers the lowest ~15% of
	// the area, at w = 1.0 it has drowned most of it. Getting this curve wrong
	// is the fastest way to turn an entire library into black mirrors -- a
	// pool at roughness 0.04 under a lamp beside the camera returns nothing
	// except one hotspot, which is correct physics and an unreadable image.
	float lvl = w * w * 0.55 * pool_gain;
	float pool = clamp(smoothstep(0.0, 0.11, lvl - field), 0.0, 1.0) * step(0.03, w);
	float film = w * 0.85;
	float wl = max(film * 0.75, pool);

	alb *= mix(1.0, wet_darken, film);
	alb *= mix(1.0, 0.74, pool);
	// A DAMP surface is darker and slightly glossier. It is not shiny: the
	// water is inside the pores, not standing on top of them. Only where water
	// is actually standing does roughness collapse toward a mirror. Letting
	// the film drive roughness all the way to `wet_rough` is what turned the
	// first pass of this library into wet ceramic.
	rough = mix(rough, max(wet_rough, 0.26), film * 0.72);
	// Standing water, but not a perfect mirror: at 0.02 the lamp reflects as a
	// single point and a flooded floor reads as black. 0.07 spreads it into a
	// sheen you can see, which is also what a real pool with any silt in it
	// does. See NOTES.md -- under zero ambient there is nothing else to
	// reflect, and that is a finding, not a setting.
	rough = mix(rough, max(wet_rough * 0.55, 0.075), pool);
	specular = mix(specular, 0.58, wl);
	// Water fills the micro relief before it fills the detail relief, which is
	// why a wet surface loses its sparkle before it loses its shape.
	g *= mix(1.0, 1.0 - wet_fill * 0.85, pool);

	vec3 nrm = normalize(N - (g - N * dot(g, N)) * bs_normal_gain);

	// --- occlusion -------------------------------------------------------------
	// A cavity term from the same field. Without it the joints and the spaces
	// between stones do not close, and the surface hovers.
	float ao = clamp(0.30 + 0.85 * field + 0.25 * (h_det / max(detail_amp * 2.2, 1e-4)),
	                 0.22, 1.0);
	if (ao_strength > 0.0 && f_form > 0.02) {
		// A real horizon estimate: four taps of the form band at a radius of
		// about one cell. Godot has no contact shadows in 4.x and SSAO does
		// nothing under zero ambient, so without this the space between two
		// stones is exactly as bright as the top of one and the whole floor
		// reads as a printed pattern. This is the term that makes aggregate
		// look like stones lying on the ground rather than a picture of them.
		float rr = max(ao_radius, fp * 2.0);
		float hc = bs_form_ao(S);
		float occ = 0.0;
		occ += max(0.0, bs_form_ao(S + Tn * rr) - hc);
		occ += max(0.0, bs_form_ao(S - Tn * rr) - hc);
		occ += max(0.0, bs_form_ao(S + Bn * rr) - hc);
		occ += max(0.0, bs_form_ao(S - Bn * rr) - hc);
		ao *= clamp(1.0 - (occ / rr) * ao_strength, 0.10, 1.0);
	}

	// --- output ----------------------------------------------------------------
	rough = clamp(rough, 0.020, 1.0);
	if (bs_debug < 0.5) {
		ALBEDO = clamp(alb, vec3(0.0), vec3(0.95));
		ROUGHNESS = rough;
		METALLIC = clamp(metal, 0.0, 1.0);
		SPECULAR = specular;
		NORMAL = normalize((VIEW_MATRIX * vec4(nrm, 0.0)).xyz);
		AO = ao;
		AO_LIGHT_AFFECT = 1.0;
		// The water film is a coat over the substrate, not a change to it.
		// the film is a coat over the substrate, not a change to it -- and it
		// is thin. A strong clearcoat over everything reads as cling film.
		CLEARCOAT = pool * 0.65 + film * 0.18;
		CLEARCOAT_ROUGHNESS = mix(0.16, 0.03, pool);
	} else {
		vec3 dbg = vec3(0.0);
		if (bs_debug < 1.5) { dbg = clamp(alb, vec3(0.0), vec3(1.0)); }
		else if (bs_debug < 2.5) { dbg = vec3(rough); }
		else if (bs_debug < 3.5) { dbg = nrm * 0.5 + 0.5; }
		else if (bs_debug < 4.5) { dbg = vec3(ao); }
		else if (bs_debug < 5.5) { dbg = vec3(field); }
		else { dbg = vec3(clamp(metal, 0.0, 1.0)); }
		ALBEDO = vec3(0.0);
		METALLIC = 0.0;
		ROUGHNESS = 1.0;
		SPECULAR = 0.0;
		EMISSION = dbg;
	}
}

#endif
