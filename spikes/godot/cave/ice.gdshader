// ---------------------------------------------------------------------------
// BLINDSIDE -- ICE. The second material family (ART-DIRECTION 3.1, 2026-09-09).
//
// This is a SEPARATE SHADER on purpose, and the reason is written down in
// ART-DIRECTION 3.1's two warnings:
//
//   "Everything in the rock family shares one voronoi and it shows... Ice built
//    from the same function will join that family, which is exactly what it
//    must not do -- it is the one material that is supposed to look like it
//    came from somewhere else."
//
//   "Do not build a smooth conduit out of the rock family's primitive... the
//    fix is a second pattern primitive -- anisotropic, directional,
//    flow-shaped -- which nothing here has. That is the one real new shader
//    the ice costs."
//
// So: NO cellular function is sampled here at all. t_cel, t_agg and t_cid are
// not bound. The only texture is the fbm volume, and it is sampled with the
// coordinate COMPRESSED 6:1 along the flow axis, which is what makes the
// pattern directional rather than blobby. On top of that sit explicit
// scallops -- the flutes running water cuts into a conduit wall -- which are a
// sinusoid in the flow coordinate and the perimeter, and nothing else in this
// project produces anything like them.
//
// THE FOUR SCALARS are ART-DIRECTION 3.1's, taken as written:
//   clarity   bubble content. glacier ice is white because it is full of air;
//             meltwater-refrozen conduit ice is clear
//   polish    whether running water shaped it. roughness 0.55 -> 0.03, and the
//             normal-incidence flash. also the footing axis and the sensor axis
//   debris    entrained rock, gravel and silt. A VOLUME mask, not a surface
//             one -- the ice is a fill, so it carries what it pushed into, and
//             this is the term that keeps ice inside the warm rock family
//   depth_of_medium   the blue
//
// THE BLUE IS A PATH LENGTH, NOT A TINT. ART-DIRECTION 3.1 / THE-ICE 6.1:
// "Thin ice is neutral; thick ice is blue because the light travelled far."
// So there is no blue constant anywhere below. There is an ABSORPTION
// COEFFICIENT in metres^-1 and an exp(). A shader that reaches for a blue
// albedo has failed the rule; this one reaches for Beer-Lambert.
//
// VERTEX CONTRACT (dressing.gd writes these):
//   COLOR.r  wet      0..1
//   COLOR.g  polish   0..1
//   COLOR.b  dark     0..1   depth fade, same field the rock shader uses
//   COLOR.a  debris   0..1
//   UV.x     axial distance along the passage or down the pitch, metres
//   UV.y     perimeter position, 0..1
//   UV2.x    FLOW COORDINATE, metres. For a pitch this is the elevation, so
//            the flutes run DOWN it; for a passage it is the axial distance.
//   UV2.y    clarity 0..1
// ---------------------------------------------------------------------------
shader_type spatial;
render_mode blend_mix, depth_draw_opaque, cull_disabled, diffuse_burley, specular_schlick_ggx;

uniform sampler3D t_fbm : filter_linear, repeat_enable;

// Absorption of pure ice, per metre, R/G/B. Real ice absorbs red about six
// times as strongly as blue, which is the whole reason a serac is blue. These
// are my numbers, chosen so 0.15 m of ice is visually neutral and 2.5 m is the
// colour of a crevasse. GUESS.
uniform vec3 ice_absorb = vec3(0.42, 0.20, 0.128);
// What the ice is standing in. NOT a colour of ice: the colour of the cave
// frozen into it. ART-DIRECTION 3.1's measured dark-rock band.
uniform vec3 debris_col = vec3(0.052, 0.041, 0.030);
// The scattering albedo of the ice itself once light is inside it. Air bubbles
// are what make glacier ice white; this is the ceiling of that.
uniform float ice_scatter = 0.26;
uniform float sss_gain = 0.50;
uniform float lamp_energy = 5.4;
uniform float detail_far = 11.0;
uniform float bump_gain = 1.0;
uniform float water_y = -1000.0;

varying vec3 wpos;
varying vec3 wnorm;

float fb(vec3 p) { return texture(t_fbm, p).r; }

// --- THE FLOW-SHAPED PRIMITIVE --------------------------------------------
// `s` is metres along the flow, `t` is the perimeter angle in radians, `p` is
// the world point. Anisotropic fbm (6:1 along the flow) plus two scallop
// registers. Returns a height in metres.
float h_flow(vec3 p, float s, float t, float pol, vec3 fdir) {
	// the anisotropic field: stretched along the flow so every feature is a
	// streak rather than a blob
	vec3 q = p;
	q -= fdir * dot(q, fdir) * (5.0 / 6.0);
	float h = (fb(q * 0.34) - 0.5) * 0.055;
	h += (fb(q * 1.30) - 0.5) * 0.012;
	// scallops. Running water cuts crescent hollows whose size is set by the
	// velocity; in a conduit they wrap into a helix. 0.22 m and 0.075 m.
	float helix = t * 1.6;
	float sc1 = sin((s + helix * 0.22) * (6.2831853 / 0.22));
	float sc2 = sin((s * 1.61 - helix * 0.31) * (6.2831853 / 0.075) + 2.1);
	// a scallop is a HOLLOW: the negative half is deeper than the positive
	// half is tall, which is what makes it read as scoured rather than lumpy
	float sc1n = sc1 * 0.5 + 0.5;
	h -= pow(1.0 - sc1n, 1.6) * 0.017 * pol;
	h -= pow(clamp(-sc2, 0.0, 1.0), 1.4) * 0.004 * pol;
	return h;
}

// The fine register. Ice is macroscopically smooth and microscopically not:
// frost, sublimation etch, refreeze rind, and the fine scallops running water
// leaves at a few centimetres. Without it the shell's per-band normals show as
// flat facets, because ice has none of the parallax and joint detail that hide
// them on the rock family.
float h_micro(vec3 p, vec3 fdir) {
	vec3 q = p;
	q -= fdir * dot(q, fdir) * 0.5;
	return (fb(q * 9.5) - 0.5) * 0.0060 + (fb(q * 26.0) - 0.5) * 0.0022;
}

vec3 bumped(vec3 n, vec3 g, float k) {
	g -= n * dot(g, n);
	g *= k;
	float l = length(g);
	if (l > 1.2) { g *= 1.2 / l; }
	return normalize(n - g);
}

void vertex() {
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	wnorm = normalize((MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz);
}

void fragment() {
	float wet     = COLOR.r;
	float polish  = COLOR.g;
	float dark    = COLOR.b;
	float debris  = COLOR.a;
	float s       = UV2.x;
	float clarity = UV2.y;
	float t       = UV.y * 6.2831853;

	vec3 n0 = normalize(wnorm);
	vec3 dv = wpos - CAMERA_POSITION_WORLD;
	float dist = length(dv);
	vec3 V = dv / max(dist, 0.0001);
	float f_det = clamp(1.0 - (dist - detail_far * 0.42) / (detail_far * 0.58), 0.0, 1.0);

	// --- the flow axis, recovered from the geometry -----------------------
	// UV2.x IS the distance along the flow, so its world-space gradient IS the
	// flow direction. Taking it from the derivatives costs two instructions
	// and saves carrying a tangent array through the mesh builder.
	vec3 dpx = dFdx(wpos);
	vec3 dpy = dFdy(wpos);
	vec3 fdir = dpx * dFdx(s) + dpy * dFdy(s);
	float flen = length(fdir);
	fdir = flen > 1e-6 ? fdir / flen : vec3(0.0, 1.0, 0.0);

	// --- form, and its normal by finite difference ------------------------
	float h0 = h_flow(wpos, s, t, polish, fdir);
	float e = 0.095;
	vec3 tx = normalize(abs(n0.y) < 0.9 ? cross(n0, vec3(0.0, 1.0, 0.0)) : vec3(1.0, 0.0, 0.0));
	vec3 ty = cross(n0, tx);
	float hx = h_flow(wpos + tx * e, s + dot(tx, fdir) * e, t, polish, fdir);
	float hy = h_flow(wpos + ty * e, s + dot(ty, fdir) * e, t, polish, fdir);
	vec3 grad = (tx * (hx - h0) + ty * (hy - h0)) / e;
	// the fine gradient, at its own epsilon
	float me = 0.013;
	float m0 = h_micro(wpos, fdir);
	float mx = h_micro(wpos + tx * me, fdir);
	float my2 = h_micro(wpos + ty * me, fdir);
	vec3 mgrad = (tx * (mx - m0) + ty * (my2 - m0)) / me;
	vec3 N = bumped(n0, grad + mgrad * mix(0.35, 1.35, f_det),
		0.85 * bump_gain * mix(0.40, 1.0, f_det));

	// --- THE BLUE, as a path length ---------------------------------------
	// How far light travels inside before it comes back out. Clear ice lets it
	// go a long way; bubbly ice turns it round in centimetres. Modulated by
	// the form so a thick lens reads deeper than a rind.
	// SHORT. Light entering ice scatters back out within centimetres in bubbly
	// ice and within a few tens of centimetres in clear ice; the first pass
	// used metres and produced a green-blue wall that ate the whole frame.
	float path = mix(0.030, 0.55, clarity) * (0.80 + 0.55 * clamp(0.5 + h0 * 6.0, 0.0, 1.0));
	vec3 transmit = exp(-ice_absorb * path);

	// --- entrained debris, as a VOLUME mask -------------------------------
	// The ice is a fill, so it carries what it pushed into. Sampled in world
	// space at two scales, not on the surface, and it never uses a cellular
	// function -- that is the rock family's and this must not join it.
	float dmask = smoothstep(0.46, 0.86, fb(wpos * 0.55)) * 0.75
				+ smoothstep(0.60, 0.95, fb(wpos * 2.30)) * 0.25;
	dmask = clamp(dmask * debris * 1.6, 0.0, 1.0);

	vec3 body = transmit * ice_scatter;
	vec3 alb = mix(body, debris_col, dmask);
	// the waterline: below it the ice is soaked and dark, above it dry rime
	float above = wpos.y - water_y;
	float subm = 1.0 - smoothstep(-0.02, 0.10, above);
	alb *= mix(1.0, 0.55, subm);

	// --- roughness. polish is what running water did to it ----------------
	// 0.030 is a mirror and a mirror in a black room returns one hotspot and
	// nothing else -- the failure ART-DIRECTION 3.1 names twice. Ice keeps a
	// floor under it.
	float rough = mix(0.62, 0.115, polish);
	rough = mix(rough, 0.95, dmask * 0.8);          // dirty ice is not glassy
	rough = mix(rough, max(rough * 0.45, 0.02), wet * 0.7);
	rough = clamp(rough + (fb(wpos * 3.7) - 0.5) * 0.10 * (1.0 - polish)
		+ (fb(wpos * 14.0) - 0.5) * 0.13, 0.05, 1.0);

	// --- the internal glow ------------------------------------------------
	// SPIKE SHORTCUT, AND IT IS FLAGGED IN VERTICAL.md. A real transmission
	// term needs a light() function or Godot's SSS. This approximates the ONE
	// carried lamp -- which in this spike is 0.26 m from the camera -- as a
	// point source at the camera, so an ice wall returns the lamp's own light
	// from inside rather than reflecting a black room. It is the reason ice is
	// the one specular-family material that does not fail ART-DIRECTION 3.1's
	// "a pool reflects one hotspot and otherwise reflects black" test.
	// It will be WRONG the first time two agents are in one chamber.
	float irr = lamp_energy / (1.0 + dist * dist * 1.35);
	float facing = clamp(-dot(N, V), 0.0, 1.0);
	vec3 glow = transmit * irr * sss_gain * (0.35 + 0.65 * facing) * (1.0 - dmask * 0.85);

	ALBEDO = alb * (1.0 - 0.55 * dark * 0.35);
	ROUGHNESS = rough;
	METALLIC = 0.0;
	// ice IOR 1.31 -> F0 0.018 -> Godot SPECULAR 0.36
	SPECULAR = 0.36;
	NORMAL = N;
	EMISSION = glow * 0.020;
	AO = mix(1.0, clamp(0.55 + h0 * 3.0, 0.35, 1.0), 0.6);
	AO_LIGHT_AFFECT = 0.7;
}
