// ---------------------------------------------------------------------------
// BLINDSIDE -- standing water.   PHOTOREAL PASS (2026-09-09)
//
// The first pass drew the sump as a flat translucent plane with roughness 0.03
// and metallic 0.15 (a value that no material has), and the small puddles as
// instanced discs of the same. Under a lamp that sits at the eye, a flat
// mirror returns nothing toward the camera, so every one of them read as a
// black hole cut in the floor. That was the single most damaging object in the
// underfoot frame.
//
// This is a water SURFACE:
//   * two scrolling scales of ripple, from the shared generated noise volume
//   * screen-space refraction of what is under it, displaced by those ripples
//   * depth-weighted absorption, so shallow water is the floor slightly
//     darkened and deep water is nearly black -- the Beer-Lambert term is what
//     makes a body of water read as having a volume
//   * a Fresnel-weighted screen-space reflection, which is the only way to get
//     ART-DIRECTION 3.5's "a mirror at grazing angle" without a probe. The
//     march is 14 steps and runs on water fragments only.
//   * no tint. ART-DIRECTION 3.5: "not a blue tint". The colour comes from
//     what is under the water and what is reflected in it.
// ---------------------------------------------------------------------------
shader_type spatial;
render_mode blend_mix, depth_draw_never, cull_disabled, diffuse_lambert, specular_schlick_ggx;

uniform sampler2D screen_tex : hint_screen_texture, filter_linear_mipmap;
uniform sampler2D depth_tex : hint_depth_texture, filter_nearest;
uniform sampler3D t_fbm : filter_linear, repeat_enable;

// absorption per metre of path, weighted off red (ART-DIRECTION 2.6: below the
// line the medium changes and light dies in 4-6 m instead of 20)
uniform vec3 absorb = vec3(2.30, 1.45, 1.20);
uniform float refract_amt = 0.055;
uniform float ripple_amp = 0.035;
uniform float ripple_speed = 0.035;
uniform bool do_ssr = true;

varying vec3 wpos;
// Godot 4.7 exposes neither PROJECTION_MATRIX nor INV_PROJECTION_MATRIX to the
// FRAGMENT stage, so the four terms of it that this shader needs are carried
// across as a flat varying instead. For a perspective projection that is all
// there is: (P00, P11) project a view-space point to NDC xy, and (P22, P32)
// invert the depth buffer back to a view-space Z.
varying flat vec4 pj;

float fb(vec3 p) { return texture(t_fbm, p).r; }

//     ndc_z = (P22 * vz + P32) / -vz   ->   vz = -P32 / (ndc_z + P22)
// correct for the reverse-Z projection Forward+ uses, because it is derived
// from the actual matrix rather than assuming a convention.
float view_z(vec2 uv, vec4 P) {
	float d = texture(depth_tex, uv).r;
	return -P.w / (d + P.z);
}

void vertex() {
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	pj = vec4(PROJECTION_MATRIX[0][0], PROJECTION_MATRIX[1][1],
	          PROJECTION_MATRIX[2][2], PROJECTION_MATRIX[3][2]);
}

void fragment() {
	// --- ripples, two scales, drifting slowly ------------------------------
	float t = TIME * ripple_speed;
	vec3 q1 = vec3(wpos.x * 5.5, t, wpos.z * 5.5);
	vec3 q2 = vec3(wpos.x * 17.0 + t * 0.6, t * 1.7, wpos.z * 17.0);
	float e = 0.012;
	float h0 = fb(q1) * 0.7 + fb(q2) * 0.3;
	float hx = fb(q1 + vec3(e * 5.5, 0.0, 0.0)) * 0.7 + fb(q2 + vec3(e * 17.0, 0.0, 0.0)) * 0.3;
	float hz = fb(q1 + vec3(0.0, 0.0, e * 5.5)) * 0.7 + fb(q2 + vec3(0.0, 0.0, e * 17.0)) * 0.3;
	vec3 nw = normalize(vec3(-(hx - h0) * ripple_amp / e, 1.0, -(hz - h0) * ripple_amp / e));
	vec3 nv = normalize((VIEW_MATRIX * vec4(nw, 0.0)).xyz);

	// --- how deep is the water here ----------------------------------------
	float zs = view_z(SCREEN_UV, pj);          // the floor under the surface
	float zw = VERTEX.z;                   // the surface itself
	float depth = max(zw - zs, 0.0);       // both negative; floor is further

	// --- refraction: displace the lookup by the ripple ---------------------
	vec2 off = nv.xy * refract_amt * clamp(depth, 0.0, 1.0);
	vec2 ruv = clamp(SCREEN_UV + off, vec2(0.001), vec2(0.999));
	// reject the displacement if it pulled in something in FRONT of the water
	if (view_z(ruv, pj) > zw) {
		ruv = SCREEN_UV;
	}
	vec3 below = texture(screen_tex, ruv).rgb;
	// Beer-Lambert down and back up again
	vec3 through = below * exp(-absorb * depth * 2.0);

	// --- reflection ---------------------------------------------------------
	vec3 vdir = normalize(VERTEX);
	float fres = clamp(0.02 + 0.98 * pow(1.0 - max(dot(-vdir, nv), 0.0), 5.0), 0.0, 1.0);
	vec3 refl = vec3(0.0);              // a cave has no sky: unhit rays are black
	if (do_ssr && fres > 0.02) {
		vec3 r = reflect(vdir, nv);
		vec3 p = VERTEX + r * 0.06;
		float st = 0.16;
		for (int i = 0; i < 14; i++) {
			p += r * st;
			st *= 1.42;
			if (p.z > -0.02) {
				break;
			}
			vec2 suv = vec2(pj.x * p.x, pj.y * p.y) / (-p.z) * 0.5 + 0.5;
			if (suv.x < 0.0 || suv.x > 1.0 || suv.y < 0.0 || suv.y > 1.0) {
				break;
			}
			float zz = view_z(suv, pj);
			if (p.z < zz && zz - p.z < st * 2.6) {
				refl = texture(screen_tex, suv).rgb;
				break;
			}
		}
	}

	ALBEDO = vec3(0.0);
	EMISSION = mix(through, refl, fres);
	// the surface itself is still a specular surface for the lamp: this is the
	// glint that says "water" the instant the beam crosses it
	ROUGHNESS = 0.035 + 0.06 * h0;
	SPECULAR = 0.5;
	METALLIC = 0.0;
	NORMAL = nv;
	ALPHA = 1.0;
}
