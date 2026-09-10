// ---------------------------------------------------------------------------
// BLINDSIDE -- ICE. The second material family (ART-DIRECTION 3.1, 2026-09-09).
// Rewritten 2026-09-10 for ICE-CAVE.md: the first pass was physically shaped
// and visually inert. It rendered as grey concrete, and the reason is
// arithmetic rather than taste -- see THE THREE NUMBERS below.
//
// This is a SEPARATE SHADER on purpose, and the reason is written down in
// ART-DIRECTION 3.1's two warnings:
//
//   "Everything in the rock family shares one voronoi and it shows... Ice built
//    from the same function will join that family, which is exactly what it
//    must not do."
//
//   "Do not build a smooth conduit out of the rock family's primitive... the
//    fix is a second pattern primitive -- anisotropic, directional,
//    flow-shaped -- which nothing here has."
//
// So: NO cellular function is sampled here at all. t_cel, t_agg and t_cid are
// not bound. The only texture is the fbm volume, sampled with the coordinate
// COMPRESSED 6:1 along the flow axis.
//
// THE THREE NUMBERS THE FIRST PASS GOT WRONG, and they are why v6_ice_band is
// a photograph of a concrete culvert:
//
//   1. THE PATH WAS CENTIMETRES.   mix(0.030, 0.55) m against an absorption of
//      0.42/0.20/0.128 per metre gives transmit = (0.79, 0.90, 0.93) at the
//      CLEAREST end. That is a 4% blue bias. Ice is blue because light travels
//      METRES inside it before it comes back out -- the mean free path in
//      bubbly ice is centimetres but the RANDOM WALK is long, and what leaves
//      the surface has been through many scattering events. The quantity that
//      belongs in Beer-Lambert here is the total walked distance, which is
//      metres. Now mix(0.35, 7.5).
//   2. THE ABSORPTION RATIO WAS 3.3:1.  Real ice absorbs red about fifteen
//      times as strongly as blue. At 3.3:1 no path length produces a blue; it
//      produces a warm grey that gets darker. Now 17:1.
//   3. THE SCATTERING ALBEDO WAS 0.26 AND CONSTANT.  Glacier ice is bright
//      because it is full of air. Bubbly ice returns most of what enters it;
//      clear ice lets it go deep, so it is DARKER and BLUER. One number
//      cannot be both. Now it is driven by `clarity`, opposite in sign to the
//      path: mix(0.92 bubbly, 0.30 clear).
//
// Together those three make the material do what the fiction says it does:
// thin/bubbly ice is white and bright, thick/clear ice is deep blue, and the
// SAME two scalars produce both. There is still no blue constant in this file.
//
// THE LIGHT, which is the other half of the task. ART-DIRECTION 2.x's economy
// is one lamp and no ambient, and on rock that gives a hard pool and a black
// room. Ice does not behave that way and the difference is the whole point:
//
//   - SSS_STRENGTH puts Godot's screen-space subsurface pass on the direct
//     light, so EVERY light in the scene -- the lamp, a beacon pilot, the
//     daylight down the collar -- diffuses laterally through the surface
//     instead of stopping at it. That is the correct mechanism and it costs
//     one pass that the renderer already has.
//   - THE LAMP IS NOW A REAL LAMP. The first pass approximated it as a point
//     source AT THE CAMERA, which is why the glow had no shape: it was a
//     vignette. cave_root.gd now feeds the true spot position, axis and cone,
//     and the internal glow is computed against a DELIBERATELY WIDER cone than
//     the lamp actually has. The light bleeds past the edge of its own beam,
//     because inside ice it does. That single term is the difference between
//     "a lamp in a mine" and "a lamp in an ice passage".
//   - BUBBLE TRAINS are marched three taps INTO the surface along the
//     refracted view vector, so what you see is under the surface rather than
//     on it. It is the cheapest possible depth cue and it is the one thing
//     that stops polished ice reading as painted plastic.
//
// THE FOUR SCALARS are ART-DIRECTION 3.1's, taken as written:
//   clarity   bubble content. glacier ice is white because it is full of air;
//             meltwater-refrozen conduit ice is clear
//   polish    whether running water shaped it. roughness and the flash
//   debris    entrained rock, gravel and silt. A VOLUME mask, not a surface
//             one -- the ice is a fill, so it carries what it pushed into
//   depth_of_medium   the blue, as a path
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
//
// PROP OVERRIDE. Ice props (icicles, columns, curtains, pool lids) are built
// by the kit builder, which writes no UV2, so the four scalars can be forced
// from uniforms instead: any *_u >= 0.0 replaces the vertex channel. With
// UV2.x constant the flow gradient vanishes and fdir falls back to vertical,
// which is exactly right for an icicle.
// ---------------------------------------------------------------------------
shader_type spatial;
render_mode blend_mix, depth_draw_opaque, cull_disabled, diffuse_burley, specular_schlick_ggx;

uniform sampler3D t_fbm : filter_linear, repeat_enable;

// Absorption of pure ice, per metre, R/G/B. Real ice absorbs red roughly
// fifteen to twenty times as strongly as blue, which is the whole reason a
// serac is blue and the first pass's 3.3:1 could never be. GUESS, chosen so
// 0.4 m of ice is visually neutral and 7 m is the colour of a crevasse.
uniform vec3 ice_absorb = vec3(0.355, 0.082, 0.021);
// What the ice is standing in. NOT a colour of ice: the colour of the cave
// frozen into it. ART-DIRECTION 3.1's measured dark-rock band.
uniform vec3 debris_col = vec3(0.052, 0.041, 0.030);
// backscatter albedo at the two ends of `clarity`. Bubbly ice returns most of
// what enters; clear ice lets it walk far enough to be absorbed.
// 0.92 was a blown white at 1 m under a 5.4 W lamp -- an ice block read as
// polystyrene, which is the same failure the loose-stone pass already
// recorded once. Bubbly ice is bright, not luminous.
uniform float scat_bubbly = 0.60;
uniform float scat_clear  = 0.30;
// the random-walk distance inside the ice, metres, at the two ends of clarity
uniform float path_bubbly = 0.35;
uniform float path_clear  = 5.2;

// --- the real lamp. cave_root.gd writes these every frame ------------------
uniform vec3  lamp_pos   = vec3(0.0, 0.0, 0.0);
uniform vec3  lamp_dir   = vec3(0.0, 0.0, -1.0);
uniform float lamp_energy = 5.4;
uniform float lamp_range  = 26.0;
// cos of the lamp's own cone half-angle, and of the WIDER cone the internal
// scattering uses. The gap between them IS the effect.
uniform float lamp_cos    = 0.891;   // cos(27 deg)
uniform float lamp_cos_wide = 0.500; // cos(60 deg)
uniform float sss_gain    = 1.0;
uniform float sss_strength = 0.42;

// a second, static source: the daylight down the collar. Zero energy disables.
uniform vec3  sky_pos    = vec3(0.0, 1e6, 0.0);
uniform float sky_energy = 0.0;
uniform vec3  sky_col    = vec3(0.60, 0.74, 1.00);

uniform float detail_far = 11.0;
uniform float bump_gain = 1.0;
uniform float scallop_gain = 1.0;
uniform float bubble_gain = 1.0;
// a per-material value trim. Broken ice is frost-shattered and genuinely
// brighter than a wall, but a heap of it at a metre under a 5.4 W lamp is a
// heap of white polygons, so the block material carries 0.70 of the wall's.
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
// `s` is metres along the flow, `t` is the perimeter angle in radians, `p` is
// the world point. Anisotropic fbm (6:1 along the flow) plus two scallop
// registers. Returns a height in metres.
float h_flow(vec3 p, float s, float t, float pol, vec3 fdir, float f22, float f075) {
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
	// half is tall, which is what makes it read as scoured rather than lumpy.
	// The gain went 0.017 -> 0.030 because the geometry now carries the LOW
	// register of the same pattern and these two have to agree or the wall
	// reads as a bumpy tube with a decal on it.
	float sc1n = sc1 * 0.5 + 0.5;
	// BOTH registers carry a footprint fade. A scallop is a PERIODIC pattern
	// and a periodic pattern seen edge-on at a metre aliases into a
	// checkerboard -- which is exactly what the first collar frame rendered,
	// a moire so strong it looked like a tiled floor. The fades are computed
	// from the pixel's world-space footprint (see f22/f075 in fragment), so a
	// register switches itself off the moment it is smaller than a pixel
	// rather than at some hand-chosen distance.
	h -= pow(1.0 - sc1n, 1.6) * 0.046 * pol * scallop_gain * f22;
	h -= pow(clamp(-sc2, 0.0, 1.0), 1.4) * 0.012 * pol * scallop_gain * f075;
	return h;
}

// The fine register. Ice is macroscopically smooth and microscopically not:
// frost, sublimation etch, refreeze rind, and the fine scallops running water
// leaves at a few centimetres.
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

// the spot cone term for an arbitrary half-angle cosine, softened at the edge
float cone(vec3 L, float cs) {
	float c = dot(-L, normalize(lamp_dir));
	return smoothstep(cs, mix(cs, 1.0, 0.45), c);
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

	// --- the flow axis, recovered from the geometry -----------------------
	// UV2.x IS the distance along the flow, so its world-space gradient IS the
	// flow direction. Two derivatives, and no tangent array has to be carried
	// through the mesh builder. On a prop UV2.x is constant, the gradient
	// vanishes and this falls back to vertical -- which is what an icicle is.
	vec3 dpx = dFdx(wpos);
	vec3 dpy = dFdy(wpos);
	vec3 fdir = dpx * dFdx(s) + dpy * dFdy(s);
	float flen = length(fdir);
	fdir = flen > 1e-6 ? fdir / flen : vec3(0.0, 1.0, 0.0);

	// --- form, and its normal by finite difference ------------------------
	// the pixel's world-space footprint, in metres. Everything periodic below
	// is faded against it: a register whose wavelength is under about four
	// footprints cannot be resolved and must not be drawn.
	float fw = (length(dpx) + length(dpy)) * 0.5;
	float f22 = clamp(0.22 / max(fw * 5.0, 1e-5) - 0.55, 0.0, 1.0);
	float f075 = clamp(0.075 / max(fw * 5.0, 1e-5) - 0.55, 0.0, 1.0);
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
	vec3 N = bumped(n0, grad + mgrad * mix(0.35, 1.35, f_det),
		1.15 * bump_gain * mix(0.40, 1.0, f_det));

	// --- THE BLUE, as a path length ---------------------------------------
	// TWO paths, not one, and that separation is what makes ice read as ice
	// rather than as blue plastic. Light that entered a centimetre away and
	// came straight back has travelled almost nothing and is NEUTRAL; light
	// that walked the body of the ice and came back out has travelled metres
	// and is blue. A single path makes the whole surface one colour, which is
	// what the first tuning of this pass produced -- a uniform teal wall with
	// no white in it anywhere.
	//
	//   SHORT -> ALBEDO.   the first-scatter rind. Bright, nearly neutral.
	//                      This is what the lamp lands on.
	//   LONG  -> the glow. The body. This is the blue, and it appears where
	//                      the lamp is NOT pointing -- in the shadows, round
	//                      the edge of the beam, and in thick lenses.
	//
	// So a beam entering ice makes a white patch with a blue halo, which is
	// exactly what a torch in an ice cave does and is the opposite of what it
	// does on rock.
	float form = 0.72 + 0.62 * clamp(0.5 + h0 * 6.0, 0.0, 1.0);
	float path_s = mix(0.03, 0.34, clarity) * form;
	float path_d = mix(path_bubbly, path_clear, clarity) * form;
	vec3 t_surf = exp(-ice_absorb * path_s);
	vec3 transmit = exp(-ice_absorb * path_d);
	// and the backscatter runs the OTHER way: what comes back out is a lot in
	// bubbly ice and a little in clear ice. Same scalar, opposite sign, and it
	// is why clear ice is dark AND blue rather than merely blue.
	float scat = mix(scat_bubbly, scat_clear, clarity);
	// THE-ICE 6.1: "an ice passage under a work lamp is BRIGHTER, SOFTER and
	// FLATTER than a rock one at the same power." That is a number, and this
	// is the number: the first-scatter albedo of ice is about twice the rock
	// family's 0.19-0.32, so the same lamp returns twice as much from the same
	// distance. It is also why the ice band needs its own exposure row.
	// MEASURED, TWICE. 0.66 for clear conduit ice is about 3.5x the rock
	// family's 0.19 and it puts a six-metre ice dome above the legibility
	// ceiling end to end: ten of fourteen ice frames came back "not enough
	// black", and in the chamber it erased the Assayer -- a cast-iron machine
	// at albedo 0.058 standing in front of a wall at 0.66 is a silhouette, and
	// the whole point of that machine is that it is the brightest thing in the
	// cave. THE-ICE 6.1 asks for "brighter, softer and flatter than a rock one
	// at the same power", which is a RATIO of about 1.5, not of 3.5.
	float scat_s = mix(scat_bubbly, 0.34, clarity);

	// --- bubble trains, marched INTO the surface --------------------------
	// Three taps along the refracted view vector. What this buys is that the
	// structure you can see is BELOW the surface, which is the only cheap cue
	// that separates ice from a polished dielectric. Layers, because ice is
	// deposited in layers and the bubbles are trapped between them.
	vec3 Rv = refract(V, N, 0.763);          // 1/1.31
	if (dot(Rv, Rv) < 0.001) { Rv = V; }
	float bub = 0.0;
	float step_m = mix(0.045, 0.30, clarity);
	for (int i = 1; i <= 3; i++) {
		vec3 q = wpos + Rv * (step_m * float(i));
		// layered: a strong vertical banding times an isotropic cloud
		float lay = 0.55 + 0.45 * sin(q.y * 7.3 + fb(q * 0.21) * 9.0);
		bub += smoothstep(0.52, 0.92, fb(q * 3.4)) * lay / float(i);
	}
	bub = clamp(bub * 0.42 * bubble_gain * (0.35 + 0.65 * (1.0 - clarity)), 0.0, 1.0);

	// --- entrained debris, as a VOLUME mask -------------------------------
	// The ice is a fill, so it carries what it pushed into. Sampled in world
	// space at two scales, not on the surface, and it never uses a cellular
	// function -- that is the rock family's and this must not join it.
	float dmask = smoothstep(0.46, 0.86, fb(wpos * 0.55)) * 0.75
				+ smoothstep(0.60, 0.95, fb(wpos * 2.30)) * 0.25;
	dmask = clamp(dmask * debris * 1.6, 0.0, 1.0);

	vec3 body = t_surf * scat_s;
	// the bubbles are white: they are air, and air scatters without absorbing,
	// so a bubble train is the one part of an ice wall that is NOT blue.
	body = mix(body, mix(body, vec3(scat_bubbly), 0.75), bub);
	vec3 alb = mix(body, debris_col, dmask);
	// the waterline: below it the ice is soaked and dark, above it dry rime
	float above = wpos.y - water_y;
	float subm = 1.0 - smoothstep(-0.02, 0.10, above);
	alb *= mix(1.0, 0.55, subm);

	// --- roughness. polish is what running water did to it ----------------
	float rough = mix(0.62, 0.105, polish);
	rough = mix(rough, 0.95, dmask * 0.8);          // dirty ice is not glassy
	rough = mix(rough, max(rough * 0.45, 0.02), wet * 0.7);
	rough = clamp(rough + (fb(wpos * 3.7) - 0.5) * 0.10 * (1.0 - polish)
		+ (fb(wpos * 14.0) - 0.5) * 0.13, 0.05, 1.0);

	// --- THE INTERNAL GLOW, against the real lamp -------------------------
	// Not a vignette. The lamp has a position, an axis and a cone, and the
	// scattering is computed against a cone 60 degrees wide where the lamp's
	// own is 27 -- so the light BLEEDS PAST THE EDGE OF ITS OWN BEAM. That
	// does not happen on rock and it is the signature of the material.
	vec3 Lv = lamp_pos - wpos;
	float ld = length(Lv);
	vec3 L = Lv / max(ld, 0.0001);
	// A HALO, NOT A WASH. The first tuning of this term used a soft cone and a
	// gentle falloff, and the result was every ice surface within eight metres
	// carrying the same flat teal -- light with no shape, which is the exact
	// failure the camera-point approximation had. What a beam entering ice
	// actually makes is a BRIGHT PATCH WITH A RING ROUND IT, and the ring is
	// the part rock cannot do. So the term is built as the ring explicitly:
	// `soft - hard` is the annulus between the lamp's own 27-degree cone and
	// the 62-degree cone the scattering fills, and it gets most of the weight.
	// Inverse square, and no linear term, so it dies inside two metres.
	float att = 1.0 / (1.0 + ld * ld * 1.35);
	float hard = cone(L, lamp_cos);
	float soft = cone(L, lamp_cos_wide);
	float halo = clamp(soft - hard, 0.0, 1.0);
	// wrapped lambert: light that entered somewhere else and came out here
	float wrap = clamp((dot(N, L) + 0.72) / 1.72, 0.0, 1.0);
	float inflow = lamp_energy * att * (hard * 0.40 + halo * 0.95) * wrap;
	// the daylight down the collar, on the same rule
	vec3 Sv = sky_pos - wpos;
	float sd = length(Sv);
	float satt = sky_energy / (1.0 + sd * sd * 1.10);
	float swrap = clamp((dot(N, Sv / max(sd, 0.0001)) + 0.65) / 1.65, 0.0, 1.0);

	// what leaves the surface is what got in, walked, and survived
	vec3 glow = transmit * scat * sss_gain * inflow * (1.0 - dmask * 0.85);
	glow += transmit * scat * sky_col * satt * swrap * (1.0 - dmask * 0.85);
	// bubbles catch the beam and light up white inside the ice
	glow *= (1.0 + bub * 1.10);

	ALBEDO = alb * albedo_gain * (1.0 - 0.55 * dark * 0.35);
	ROUGHNESS = rough;
	METALLIC = 0.0;
	// ice IOR 1.31 -> F0 0.018 -> Godot SPECULAR 0.225
	SPECULAR = 0.225;
	NORMAL = N;
	EMISSION = glow * 0.155;
	// Godot's screen-space subsurface pass. This is what makes EVERY light --
	// the lamp, a beacon pilot, the collar daylight -- diffuse laterally
	// through the surface instead of stopping on it. Suppressed where the ice
	// is dirty, because dirty ice does not transmit.
	SSS_STRENGTH = sss_strength * (1.0 - dmask) * (0.45 + 0.55 * clarity);
	AO = mix(1.0, clamp(0.55 + h0 * 3.0, 0.35, 1.0), 0.6);
	AO_LIGHT_AFFECT = 0.7;
}
