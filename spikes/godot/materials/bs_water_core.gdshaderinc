// ---------------------------------------------------------------------------
// BLINDSIDE -- standing water.
//
// Two cases, one core:
//   shallow  a film to half a metre over silt. Transparent, refracting, and
//            the thing you see is the bottom through it.
//   deep     a pool you cannot see the bottom of. Opaque, so that Godot's
//            screen-space reflection can run on it -- see NOTES.md, "The
//            ambient rule I am testing".
//
// Physics, and each number has a source:
//   IOR 1.333, so F0 = ((1.333-1)/(1.333+1))^2 = 0.0203. SPECULAR 0.25 in
//   Godot's parameterisation (SPECULAR 0.5 == F0 0.04).
//   Absorption of clear water, per metre, roughly (0.35, 0.045, 0.015) in
//   R/G/B -- water eats red first, which is why depth reads blue-green even
//   with no blue tint anywhere in the palette (ART-DIRECTION 3.5).
//   Mine water is not clear: suspended iron fines add scattering and shift the
//   residual toward ochre, which is `murk_col`.
// ---------------------------------------------------------------------------
#ifndef BS_WATER_CORE_INC
#define BS_WATER_CORE_INC

#include "res://bs_noise.gdshaderinc"

global uniform float bs_wet;
global uniform float bs_debug;

uniform vec3  absorb = vec3(0.85, 0.30, 0.18);   // per metre, mine water
uniform vec3  murk_col = vec3(0.030, 0.026, 0.020);
uniform float murk = 0.55;                        // in-scatter per metre
uniform float ripple_amp = 0.0016;                // metres. Standing water is still.
uniform float ripple_freq = 5.5;
uniform float ripple_speed = 0.09;
uniform float drip_rings = 0.0;                   // rings from roof drips
uniform float max_depth = 3.0;                    // metres, for the deep case
uniform float refract_k = 0.035;

#ifndef BS_WATER_OPAQUE
uniform sampler2D screen_tex : hint_screen_texture, filter_linear_mipmap;
uniform sampler2D depth_tex : hint_depth_texture, filter_nearest;
#endif

varying vec3 v_wpos;
varying vec3 v_wnorm;

float bs_wave(vec3 p, float t) {
	// Two scales of capillary ripple plus, optionally, expanding rings where a
	// drip lands. Nothing here is a swell: this is water in a closed chamber.
	float h = bs_gnoise(vec3(p.x * ripple_freq, t * ripple_speed, p.z * ripple_freq)) * 0.6;
	h += bs_gnoise(vec3(p.x * ripple_freq * 3.7 + 11.0, t * ripple_speed * 1.9,
	                    p.z * ripple_freq * 3.7)) * 0.28;
	if (drip_rings > 0.0) {
		vec2 c = floor(p.xz * 0.7);
		vec2 o = bs_h3(vec3(c, 0.0)).xy * 0.5;
		float d = length(p.xz - (c + 0.5 + o) / 0.7);
		float ph = bs_h1(vec3(c, 4.0));
		float age = fract(t * 0.22 + ph);
		float r = age * 1.4;
		h += sin((d - r) * 46.0) * exp(-abs(d - r) * 12.0) * (1.0 - age) * drip_rings;
	}
	return h;
}

void vertex() {
	v_wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	v_wnorm = normalize((MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz);
}

void fragment() {
	vec3 N = normalize(v_wnorm);
	vec3 P = v_wpos;
	float t = TIME;

	// surface normal from the ripple field, tangent-free like everything else
	float fp = max(length(fwidth(P)), 1e-5);
	float e = max(0.35 / ripple_freq, fp * 1.5);
	vec3 Tn = normalize(cross(N, abs(N.y) < 0.9 ? vec3(0.0, 1.0, 0.0) : vec3(1.0, 0.0, 0.0)));
	vec3 Bn = cross(N, Tn);
	float h0 = bs_wave(P, t);
	float ha = bs_wave(P + Tn * e, t);
	float hb = bs_wave(P + Bn * e, t);
	// fade the ripple as its wavelength approaches a pixel, same rule as the
	// surface family, so a distant pool does not fizz
	float fade = clamp(1.0 - fp * ripple_freq * 4.0, 0.0, 1.0);
	vec3 g = ((ha - h0) * Tn + (hb - h0) * Bn) / e * ripple_amp * fade;
	vec3 nrm = normalize(N - (g - N * dot(g, N)));

	vec3 cam = (INV_VIEW_MATRIX * vec4(0.0, 0.0, 0.0, 1.0)).xyz;
	vec3 Vd = normalize(cam - P);

#ifdef BS_WATER_OPAQUE
	// Deep. You do not see the bottom, so there is nothing to refract; what is
	// left is the residual scatter of the column, which is very dark, plus
	// whatever the specular lobe reflects.
	ALBEDO = murk_col * 0.45;
	ROUGHNESS = mix(0.020, 0.055, clamp(length(g) * 40.0, 0.0, 1.0));
	METALLIC = 0.0;
	SPECULAR = 0.25;                     // F0 0.0203, water
	NORMAL = normalize((VIEW_MATRIX * vec4(nrm, 0.0)).xyz);
	AO = 1.0;
#else
	// Shallow. The image is the bottom, refracted, absorbed over the path, with
	// the column's in-scatter added on top.
	float depth_raw = texture(depth_tex, SCREEN_UV).r;
	vec3 ndc = vec3(SCREEN_UV * 2.0 - 1.0, depth_raw);
	vec4 vpos = INV_PROJECTION_MATRIX * vec4(ndc, 1.0);
	vpos.xyz /= vpos.w;
	float bottom_dist = -vpos.z;
	float here = length(P - cam);
	float path = clamp(bottom_dist - here, 0.0, max_depth);

	// refraction offset: the tangential part of the perturbed normal, scaled by
	// how far the bottom is below the surface
	vec3 nv = normalize((VIEW_MATRIX * vec4(nrm, 0.0)).xyz);
	vec2 off = nv.xy * refract_k * clamp(path, 0.0, 0.6);
	vec3 back = texture(screen_tex, clamp(SCREEN_UV + off, vec2(0.001), vec2(0.999))).rgb;

	vec3 trans = exp(-absorb * path);
	vec3 inscat = murk_col * (1.0 - exp(-murk * path));
	float F = 0.0203 + (1.0 - 0.0203) * pow(1.0 - clamp(dot(nrm, Vd), 0.0, 1.0), 5.0);

	ALBEDO = vec3(0.0);
	EMISSION = (back * trans + inscat) * (1.0 - F);
	ALPHA = 1.0;
	ROUGHNESS = mix(0.020, 0.060, clamp(length(g) * 40.0, 0.0, 1.0));
	METALLIC = 0.0;
	SPECULAR = 0.25;
	NORMAL = nv;
	AO = 1.0;
#endif

	if (bs_debug > 0.5) {
		ALBEDO = vec3(0.0);
		METALLIC = 0.0;
		ROUGHNESS = 1.0;
		SPECULAR = 0.0;
		if (bs_debug < 1.5) { EMISSION = vec3(0.02, 0.021, 0.022); }
		else if (bs_debug < 2.5) { EMISSION = vec3(0.03); }
		else if (bs_debug < 3.5) { EMISSION = nrm * 0.5 + 0.5; }
		else { EMISSION = vec3(1.0); }
	}
}

#endif
