// ---------------------------------------------------------------------------
// BLINDSIDE -- ICE, THE SHELL. Walls, crown and floor of an ice passage.
//
// THIRD VERSION, 2026-09-10 (ICE-CAVE.md section 2 and 13). The designer, on
// the second version:
//
//   "what the hell is that blue colored ice? it should be somewhat
//    transparent, reflect the light inside it when the flashlight shines on
//    it. that looks like a room with blue walls"
//
// They are right and the diagnosis is exact. Version 2 got the PHYSICS OF
// COLOUR right -- Beer-Lambert, a real absorption ratio, a path length -- and
// then applied it to the wrong kind of material. It was still a DIFFUSE
// SURFACE WITH A SUBSURFACE TINT: a matte wall that happened to be blue. Ice
// is a dielectric SOLID YOU SEE INTO, and that is a different rendering
// problem from a coloured wall, not a harder version of the same one.
//
// THE THREE THINGS IT WAS MISSING, in the designer's order:
//
//   1. YOU SEE INTO IT.  For a wall of glacier ice, "seeing into it" is not
//      refraction -- you cannot see through two metres of ice to the rock
//      behind. It is that the STRUCTURE INSIDE is visible at depth: bubble
//      trains, refreeze planes, and fracture sheets, all lying BELOW a glassy
//      surface. So the shell marches a real ray into the medium along the
//      refracted view vector and shades what it finds there. Thin ice --
//      icicles, columns, pool lids, curtains -- is a genuinely different
//      case and gets a genuinely different shader: see `ice_clear.gdshader`,
//      which refracts the screen.
//   2. SPECULAR.  Ice is wet, smooth and glassy, so one lamp on it makes a
//      HARD BRIGHT HIGHLIGHT. Version 2's roughness was mix(0.62, 0.105) plus
//      up to 0.23 of added noise -- a matte plaster wall. It is now
//      mix(0.34, 0.030) and the noise is a tenth of what it was. That
//      highlight is most of what makes a viewer read "ice" instantly and
//      there was not one anywhere in the frame.
//   3. LIGHT REFLECTING INSIDE IT.  Their words, and it is the best note in
//      the message. Real ice GLITTERS because light entering it bounces off
//      internal cracks and planes. Every fracture sheet the march crosses now
//      returns a glint weighted by how squarely the lamp hits it, so the ice
//      sparkles from the inside as the beam moves.
//
// AND THE BLUE IS NOW DRIVEN BY THICKNESS RATHER THAN BY A CONSTANT.
// Version 2 computed one path length per material, so a 40 mm icicle and a
// 3 m wall were the same teal -- which is what made it read as paint. The
// path is now THE DISTANCE THE MARCH TRAVELS BEFORE IT HITS SOMETHING:
// ice with a crack 60 mm down is almost colourless, ice with nothing in it
// for two metres is deep blue, and the two sit next to each other in the same
// wall. There is still no blue constant in this file. There is an absorption
// coefficient in m^-1 and an exp().
//
// WHAT DID NOT CHANGE: no cellular function is sampled (t_cel, t_agg, t_cid
// are not bound); the only texture is the fbm volume, compressed 6:1 along
// the flow axis; the scallops are explicit; and the lamp is a real spot whose
// internal scattering is computed against a 62-degree cone where the lamp's
// own is 27, so the light bleeds past the edge of its own beam.
//
// VERTEX CONTRACT (dressing.gd writes these):
//   COLOR.r wet | COLOR.g polish | COLOR.b dark | COLOR.a debris
//   UV.x axial metres | UV.y perimeter 0..1
//   UV2.x FLOW COORDINATE metres | UV2.y clarity 0..1
// ---------------------------------------------------------------------------
shader_type spatial;
// OPAQUE, deliberately. A cave whose every surface is transparent has nothing
// behind anything: the screen texture a refractive shell would sample is the
// far wall of the same passage, which is also ice, which is also not there
// yet. The shell is a semi-infinite dielectric and is drawn as one.
render_mode depth_draw_opaque, cull_disabled, diffuse_burley, specular_schlick_ggx;

uniform sampler3D t_fbm : filter_linear, repeat_enable;

// Absorption of pure ice, per metre, R/G/B. Real ice absorbs red roughly
// fifteen to twenty times as strongly as blue, which is the whole reason a
// serac is blue. GUESS on the absolute scale, chosen so 0.15 m of ice is
// visually neutral and 3 m is the colour of a crevasse.
uniform vec3 ice_absorb = vec3(0.355, 0.082, 0.021);
uniform vec3 debris_col = vec3(0.052, 0.041, 0.030);

// How far the march goes, in metres, and how deep "no feature found" reads.
uniform float march_m = 2.10;
uniform float deep_m = 4.20;
// what the internal structure returns when the light reaches it
uniform float scat_bubble = 0.86;   // air. Scatters without absorbing: WHITE
uniform float scat_crack = 0.72;    // a fracture face, near-specular
uniform float scat_body = 0.20;     // the ice itself, between features
uniform float crack_gain = 1.0;
uniform float bubble_gain = 1.0;

// --- the real lamp. cave_root.gd writes these every frame ------------------
uniform vec3  lamp_pos   = vec3(0.0, 0.0, 0.0);
uniform vec3  lamp_dir   = vec3(0.0, 0.0, -1.0);
uniform float lamp_energy = 5.4;
uniform float lamp_range  = 26.0;
uniform float lamp_cos    = 0.891;
uniform float lamp_cos_wide = 0.500;
uniform float sss_gain    = 1.0;
uniform float sss_strength = 0.30;

uniform vec3  sky_pos    = vec3(0.0, 1e6, 0.0);
uniform float sky_energy = 0.0;
uniform vec3  sky_col    = vec3(0.60, 0.74, 1.00);

uniform float detail_far = 11.0;
uniform float bump_gain = 1.0;
uniform float scallop_gain = 1.0;
uniform float albedo_gain = 1.0;
uniform float water_y = -1000.0;

// prop overrides; < 0 means "take it from the vertex"
uniform float wet_u = -1.0;
uniform float polish_u = -1.0;
uniform float dark_u = -1.0;
uniform float debris_u = -1.0;
uniform float clarity_u = -1.0;

varying vec3 wpos;
varying vec3 wnorm;

float fb(vec3 p) { return texture(t_fbm, p).r; }

// --- THE FLOW-SHAPED PRIMITIVE --------------------------------------------
float h_flow(vec3 p, float s, float t, float pol, vec3 fdir, float f22, float f075) {
	vec3 q = p;
	q -= fdir * dot(q, fdir) * (5.0 / 6.0);
	float h = (fb(q * 0.34) - 0.5) * 0.055;
	h += (fb(q * 1.30) - 0.5) * 0.012;
	float helix = t * 1.6;
	float sc1 = sin((s + helix * 0.22) * (6.2831853 / 0.22));
	float sc2 = sin((s * 1.61 - helix * 0.31) * (6.2831853 / 0.075) + 2.1);
	float sc1n = sc1 * 0.5 + 0.5;
	// BOTH registers carry a footprint fade: a periodic pattern seen edge-on
	// at a metre aliases into a checkerboard, and this one did.
	h -= pow(1.0 - sc1n, 1.6) * 0.046 * pol * scallop_gain * f22;
	h -= pow(clamp(-sc2, 0.0, 1.0), 1.4) * 0.012 * pol * scallop_gain * f075;
	return h;
}

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

float cone(vec3 L, float cs) {
	float c = dot(-L, normalize(lamp_dir));
	return smoothstep(cs, mix(cs, 1.0, 0.45), c);
}

// --- THE FRACTURE FIELD ----------------------------------------------------
// Ice is a brittle solid under load, so it is full of planes. An isosurface of
// a smooth field is a SHEET, and thresholding one hard is the cheapest sheet
// generator there is: `1 - |2f - 1|` peaks where the field crosses its own
// midpoint, which is a surface, not a blob. Two scales: metre-wide bedding
// planes and 100 mm shatter.
float crack_at(vec3 q) {
	// METRE-SCALE, and RARE. The first tuning ran these at 0.62 and 2.35 with
	// wide thresholds, which is a mottle rather than a plane: the wall came
	// back looking like camouflage. Ice fractures in big sheets a long way
	// apart, and the empty ice BETWEEN them is where the blue lives -- if the
	// march hits something every 100 mm, nothing in the wall is ever thick.
	// AND THEY ARE LAYERED, not veined. An isosurface of an ISOTROPIC field is
	// a wandering ribbon and the wall came back looking like polished onyx.
	// Ice is DEPOSITED: its bubbles and its refreeze planes lie in beds, and
	// a glacier's beds are near-horizontal. Compressing the sample coordinate
	// 3.4:1 in Y turns every sheet into a bed, which is the single cheapest
	// thing that separates ice from stone.
	vec3 qa = vec3(q.x, q.y * 3.4, q.z);
	float a = fb(qa * 0.26);
	float b = fb(qa * 0.92 + 11.3);
	float sheet_a = smoothstep(0.945, 1.0, 1.0 - abs(a * 2.0 - 1.0));
	float sheet_b = smoothstep(0.960, 1.0, 1.0 - abs(b * 2.0 - 1.0));
	return clamp(sheet_a + sheet_b * 0.70, 0.0, 1.0);
}

void vertex() {
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	wnorm = normalize((MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz);
}

void fragment() {
	float wet     = wet_u     >= 0.0 ? wet_u     : COLOR.r;
	float polish  = polish_u  >= 0.0 ? polish_u  : COLOR.g;
	float dark    = dark_u    >= 0.0 ? dark_u    : COLOR.b;
	float debris  = debris_u  >= 0.0 ? debris_u  : COLOR.a;
	float clarity = clarity_u >= 0.0 ? clarity_u : UV2.y;
	float s       = UV2.x;
	float t       = UV.y * 6.2831853;

	vec3 n0 = normalize(wnorm);
	vec3 dv = wpos - CAMERA_POSITION_WORLD;
	float dist = length(dv);
	vec3 V = dv / max(dist, 0.0001);
	float f_det = clamp(1.0 - (dist - detail_far * 0.42) / (detail_far * 0.58), 0.0, 1.0);

	vec3 dpx = dFdx(wpos);
	vec3 dpy = dFdy(wpos);
	vec3 fdir = dpx * dFdx(s) + dpy * dFdy(s);
	float flen = length(fdir);
	fdir = flen > 1e-6 ? fdir / flen : vec3(0.0, 1.0, 0.0);

	float fw = (length(dpx) + length(dpy)) * 0.5;
	float f22 = clamp(0.22 / max(fw * 5.0, 1e-5) - 0.55, 0.0, 1.0);
	float f075 = clamp(0.075 / max(fw * 5.0, 1e-5) - 0.55, 0.0, 1.0);

	// --- form, and its normal by finite difference ------------------------
	float h0 = h_flow(wpos, s, t, polish, fdir, f22, f075);
	float e = 0.095;
	vec3 tx = normalize(abs(n0.y) < 0.9 ? cross(n0, vec3(0.0, 1.0, 0.0)) : vec3(1.0, 0.0, 0.0));
	vec3 ty = cross(n0, tx);
	float hx = h_flow(wpos + tx * e, s + dot(tx, fdir) * e, t, polish, fdir, f22, f075);
	float hy = h_flow(wpos + ty * e, s + dot(ty, fdir) * e, t, polish, fdir, f22, f075);
	vec3 grad = (tx * (hx - h0) + ty * (hy - h0)) / e;
	float me = 0.013;
	float m0 = h_micro(wpos, fdir);
	float mx = h_micro(wpos + tx * me, fdir);
	float my2 = h_micro(wpos + ty * me, fdir);
	vec3 mgrad = (tx * (mx - m0) + ty * (my2 - m0)) / me;
	mgrad *= clamp(0.020 / max(fw * 5.0, 1e-5) - 0.55, 0.0, 1.0);
	// A GLASSY SURFACE HAS A QUIET NORMAL. Version 2 ran the bump at 1.15,
	// which on a material with roughness 0.03 turns one hard highlight into a
	// field of sequins. Polished ice takes a third of it; weathered ice keeps
	// it, which is what separates a meltwater conduit from a rime wall.
	float bump_k = mix(1.05, 0.34, polish) * bump_gain;
	vec3 N = bumped(n0, grad + mgrad * mix(0.35, 1.35, f_det), bump_k * mix(0.40, 1.0, f_det));

	// --- THE MARCH INTO THE MEDIUM ----------------------------------------
	// This is "you see into it". Refract the view vector at the surface and
	// walk it into the solid, looking for the things that are actually in
	// glacier ice: bubble trains, and fracture sheets. Record how far it got
	// before it hit something, because THAT distance is the thickness the
	// colour comes from.
	vec3 Rv = refract(V, N, 0.763);          // 1/1.31
	if (dot(Rv, Rv) < 0.001) { Rv = V; }
	int STEPS = f_det > 0.35 ? 7 : 3;
	float step_m = march_m / float(STEPS);
	float bub = 0.0;
	float crk = 0.0;
	float glint = 0.0;
	float hit_d = deep_m;
	bool found = false;
	// clear ice carries its features further apart; bubbly ice is opaque in
	// centimetres, which is why it is white and not blue
	float bub_thresh = mix(0.54, 0.78, clarity);
	for (int i = 1; i <= 7; i++) {
		if (i > STEPS) { break; }
		float d = step_m * float(i);
		vec3 q = wpos + Rv * d;
		// layered, because ice is deposited in layers and the air is trapped
		// between them
		float lay = 0.55 + 0.45 * sin(q.y * 7.3 + fb(q * 0.21) * 9.0);
		float b = smoothstep(bub_thresh, bub_thresh + 0.30, fb(q * 3.4)) * lay;
		float c = crack_at(q);
		// what survives the trip in and back out again
		vec3 tr = exp(-ice_absorb * (d * 2.0));
		float vis = (1.0 - clamp(bub + crk, 0.0, 1.0));
		bub += b * vis * 0.55 * bubble_gain;
		crk += c * vis * 0.55 * crack_gain;
		// THE GLINT. A fracture face is a mirror inside the ice, so it
		// FLASHES when the beam catches it square. Approximated by the
		// gradient of the crack field against the lamp direction -- one extra
		// sample, and it is what makes the ice sparkle rather than glow.
		if (c > 0.02) {
			vec3 Lq = normalize(lamp_pos - q);
			float g = crack_at(q + Lq * 0.045) - c;
			glint += c * vis * clamp(0.5 - g * 6.0, 0.0, 1.0) * dot(tr, vec3(0.33));
		}
		if (!found && (b + c) > 0.30) { hit_d = d; found = true; }
	}
	bub = clamp(bub, 0.0, 1.0);
	crk = clamp(crk, 0.0, 1.0);
	float inner = clamp(bub + crk, 0.0, 1.0);

	// --- THE BLUE, from the thickness the march measured ------------------
	// Light that came back off a crack 60 mm down travelled 120 mm and is
	// colourless. Light that found nothing for two metres travelled four and
	// is a crevasse. Same wall, both at once, and that is the difference
	// between ice and paint.
	float thick = mix(deep_m, hit_d, float(found)) * 2.0;
	thick *= mix(0.55, 1.35, clarity);              // bubbly ice turns it round sooner
	vec3 transmit = exp(-ice_absorb * thick);
	vec3 t_near = exp(-ice_absorb * (hit_d * 2.0 * mix(0.55, 1.35, clarity)));

	// --- entrained debris, as a VOLUME mask -------------------------------
	float dmask = smoothstep(0.46, 0.86, fb(wpos * 0.55)) * 0.75
				+ smoothstep(0.60, 0.95, fb(wpos * 2.30)) * 0.25;
	dmask = clamp(dmask * debris * 1.6, 0.0, 1.0);

	// THE DIFFUSE ALBEDO USES A SHORT PATH, AND THE DEEP BLUE LIVES IN THE
	// EMISSION. A saturated cyan ALBEDO is multiplied by every light that
	// touches it, and the only other light in this cave is the beacons' amber
	// -- amber times cyan is GREEN, and the icefall frame came back the colour
	// of pond water. It is also wrong physically: what a surface returns as
	// DIFFUSE is the first-scatter rind, which has travelled centimetres and
	// is near-neutral. The metres-long path belongs to the light that came
	// back out of the body, which is an ADDITIVE term and is not multiplied by
	// anybody's light colour. Split that way the blue survives and the green
	// cannot happen.
	vec3 t_short = exp(-ice_absorb * min(thick, 0.85));
	vec3 body = t_short * scat_body;
	vec3 feat = t_near * (scat_bubble * bub + scat_crack * crk) / max(inner, 0.001);
	vec3 alb = mix(body, feat, inner);
	alb = mix(alb, vec3(dot(alb, vec3(0.3333))), 0.28);
	alb = mix(alb, debris_col, dmask);

	float above = wpos.y - water_y;
	float subm = 1.0 - smoothstep(-0.02, 0.10, above);
	alb *= mix(1.0, 0.55, subm);

	// --- ROUGHNESS. It is a wet, smooth, glassy solid. --------------------
	float rough = mix(0.34, 0.065, polish);
	rough = mix(rough, 0.88, dmask * 0.8);          // dirty ice is not glassy
	rough = mix(rough, max(rough * 0.45, 0.038), wet * 0.8);
	// a tenth of the noise version 2 added. That noise was what turned the
	// one hard highlight into a matte sheen.
	rough = clamp(rough + (fb(wpos * 3.7) - 0.5) * 0.020 * (1.0 - polish)
		+ (fb(wpos * 14.0) - 0.5) * 0.014, 0.035, 1.0);

	// --- THE INTERNAL GLOW, against the real lamp -------------------------
	vec3 Lv = lamp_pos - wpos;
	float ld = length(Lv);
	vec3 L = Lv / max(ld, 0.0001);
	float att = 1.0 / (1.0 + ld * ld * 1.35);
	float hard = cone(L, lamp_cos);
	float soft = cone(L, lamp_cos_wide);
	float halo = clamp(soft - hard, 0.0, 1.0);
	float wrap = clamp((dot(N, L) + 0.72) / 1.72, 0.0, 1.0);
	float inflow = lamp_energy * att * (hard * 0.40 + halo * 0.95) * wrap;

	vec3 Sv = sky_pos - wpos;
	float sd = length(Sv);
	float satt = sky_energy / (1.0 + sd * sd * 1.10);
	float swrap = clamp((dot(N, Sv / max(sd, 0.0001)) + 0.65) / 1.65, 0.0, 1.0);

	vec3 glow = transmit * scat_body * sss_gain * inflow * (1.0 - dmask * 0.85);
	glow += transmit * scat_body * sky_col * satt * swrap * (1.0 - dmask * 0.85);
	// and the cracks catch the beam and light up inside the ice
	vec3 spark = t_near * clamp(glint, 0.0, 3.0) * lamp_energy * att
		* (hard * 0.75 + halo * 0.35) * (1.0 - dmask);

	ALBEDO = alb * albedo_gain * (1.0 - 0.55 * dark * 0.35);
	ROUGHNESS = rough;
	METALLIC = 0.0;
	// ice IOR 1.31 -> F0 0.018 -> Godot SPECULAR 0.225
	SPECULAR = 0.225;
	NORMAL = N;
	EMISSION = glow * 0.155 + spark * 0.075;
	SSS_STRENGTH = sss_strength * (1.0 - dmask) * (0.45 + 0.55 * clarity);
	AO = mix(1.0, clamp(0.55 + h0 * 3.0, 0.35, 1.0), 0.6);
	AO_LIGHT_AFFECT = 0.7;
}
