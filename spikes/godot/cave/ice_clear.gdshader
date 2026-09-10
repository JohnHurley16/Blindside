// ---------------------------------------------------------------------------
// BLINDSIDE -- CLEAR ICE. Icicles, columns, curtains, pool lids, ribs, blocks.
//
// The designer, 2026-09-10: *"it should be somewhat transparent, reflect the
// light inside it when the flashlight shines on it."*
//
// THIS IS THE HALF OF THAT SENTENCE `ice.gdshader` CANNOT DO. A wall of
// glacier ice is a semi-infinite solid: you see the structure inside it, not
// the rock behind it, and the shell shader is opaque for that reason. An
// ICICLE IS 40 MM THICK. You see the passage through it, distorted, and its
// tip is nearly colourless because there is almost no ice in the way. That is
// a transparent dielectric and it needs the transparent path.
//
// FOUR THINGS, and they are the designer's four:
//
//   1. REFRACTION.  Screen-space, IOR 1.31, offset by the view-space normal
//      and shrinking with distance. What is behind the object is visible and
//      bent. `ALPHA` finishes at 1.0 and the object writes depth, using
//      Godot's own premultiplied-refraction idiom -- so it sorts against
//      opaque geometry by the depth buffer rather than by AABB centre, which
//      is what keeps a field of instanced icicles from swapping order as the
//      camera turns.
//   2. SPECULAR.  Roughness 0.03-0.09. One lamp on wet ice is a HARD BRIGHT
//      HIGHLIGHT, and on an icicle it is a vertical streak down the flute,
//      which is the single most recognisable thing about the object.
//   3. LIGHT INSIDE IT.  The same fracture-sheet march the shell uses, four
//      steps instead of seven, so a column glitters internally where the beam
//      crosses it.
//   4. COLOUR FROM THICKNESS, and this is the one that stops it reading as
//      paint. `thin_m` is the object's characteristic thickness in METRES and
//      the path is derived from it and the viewing angle:
//        round objects (icicle, column, rib, block, curtain lobe) -- a chord
//          through a cylinder, so `thin_m * |N.V|`: FAT MIDDLE BLUE, EDGES AND
//          TIP COLOURLESS.
//        flat objects (a pool lid) -- a slab, so `thin_m / |N.V|`: colourless
//          face-on and blue at grazing.
//      A 40 mm icicle now has about 4% of the absorption of a 3 m wall, which
//      is why it is white and the wall is blue. Version 2 gave them the same
//      constant and the designer called it blue paint, correctly.
//
// VERTEX CONTRACT: the four ice scalars come from uniforms, not from the
// vertex, because the kit builder writes kit colours. UV2.x is the distance
// along the object's own axis, so the flutes run DOWN an icicle.
// ---------------------------------------------------------------------------
shader_type spatial;
render_mode blend_mix, depth_draw_opaque, cull_disabled, diffuse_burley, specular_schlick_ggx;

uniform sampler3D t_fbm : filter_linear, repeat_enable;
uniform sampler2D screen_tex : hint_screen_texture, repeat_disable, filter_linear_mipmap;

uniform vec3 ice_absorb = vec3(0.355, 0.082, 0.021);
uniform vec3 debris_col = vec3(0.052, 0.041, 0.030);

// THE THICKNESS OF THIS KIND OF OBJECT, IN METRES. The whole point of the file.
uniform float thin_m = 0.06;
// 1.0 = a round thing (chord through a cylinder), 0.0 = a slab
uniform float thin_round = 1.0;
uniform float refract_str = 0.055;
uniform float clarity_u = 0.88;
uniform float polish_u = 0.90;
uniform float debris_u = 0.05;
uniform float wet_u = 0.30;
uniform float scat_body = 0.46;
uniform float scat_crack = 0.72;
uniform float crack_gain = 1.0;
uniform float albedo_gain = 1.0;
uniform float bump_gain = 1.0;
uniform float water_y = -1000.0;

uniform vec3  lamp_pos   = vec3(0.0, 0.0, 0.0);
uniform vec3  lamp_dir   = vec3(0.0, 0.0, -1.0);
uniform float lamp_energy = 5.4;
uniform float lamp_range  = 26.0;
uniform float lamp_cos    = 0.891;
uniform float lamp_cos_wide = 0.500;
uniform float sss_gain    = 1.0;
uniform vec3  sky_pos    = vec3(0.0, 1e6, 0.0);
uniform float sky_energy = 0.0;
uniform vec3  sky_col    = vec3(0.60, 0.74, 1.00);

varying vec3 wpos;
varying vec3 wnorm;

float fb(vec3 p) { return texture(t_fbm, p).r; }

float crack_at(vec3 q) {
	// A 50 mm icicle has ONE flaw in it, not forty. The first tuning ran this
	// at 1.15 and 4.10 and every spike came back speckled like granite.
	// AND THEY ARE LAYERED, not veined. An isosurface of an ISOTROPIC field is
	// a wandering ribbon and the wall came back looking like polished onyx.
	// Ice is DEPOSITED: its bubbles and its refreeze planes lie in beds, and
	// a glacier's beds are near-horizontal. Compressing the sample coordinate
	// 3.4:1 in Y turns every sheet into a bed, which is the single cheapest
	// thing that separates ice from stone.
	vec3 qa = vec3(q.x, q.y * 3.4, q.z);
	float a = fb(qa * 0.48);
	float b = fb(qa * 1.70 + 11.3);
	float sheet_a = smoothstep(0.950, 1.0, 1.0 - abs(a * 2.0 - 1.0));
	float sheet_b = smoothstep(0.965, 1.0, 1.0 - abs(b * 2.0 - 1.0));
	return clamp(sheet_a + sheet_b * 0.70, 0.0, 1.0);
}

float cone(vec3 L, float cs) {
	float c = dot(-L, normalize(lamp_dir));
	return smoothstep(cs, mix(cs, 1.0, 0.45), c);
}

vec3 bumped(vec3 n, vec3 g, float k) {
	g -= n * dot(g, n);
	g *= k;
	float l = length(g);
	if (l > 1.0) { g *= 1.0 / l; }
	return normalize(n - g);
}

void vertex() {
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	wnorm = normalize((MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz);
}

void fragment() {
	vec3 n0 = normalize(wnorm);
	vec3 dv = wpos - CAMERA_POSITION_WORLD;
	float dist = length(dv);
	vec3 V = dv / max(dist, 0.0001);
	float ndv = clamp(abs(dot(n0, V)), 0.04, 1.0);

	// --- the flutes, down the object's own axis ---------------------------
	// UV2.x is the distance along the axis, so its world gradient is the axis.
	// On a mesh with a constant UV2 the gradient vanishes and this falls back
	// to vertical, which is what an icicle is.
	vec3 dpx = dFdx(wpos);
	vec3 dpy = dFdy(wpos);
	vec3 fdir = dpx * dFdx(UV2.x) + dpy * dFdy(UV2.x);
	float flen = length(fdir);
	fdir = flen > 1e-6 ? fdir / flen : vec3(0.0, 1.0, 0.0);
	float fw = (length(dpx) + length(dpy)) * 0.5;
	float fine = clamp(0.012 / max(fw * 5.0, 1e-5) - 0.55, 0.0, 1.0);

	vec3 qm = wpos - fdir * dot(wpos, fdir) * 0.5;
	float e = 0.010;
	vec3 tx = normalize(abs(n0.y) < 0.9 ? cross(n0, vec3(0.0, 1.0, 0.0)) : vec3(1.0, 0.0, 0.0));
	vec3 ty = cross(n0, tx);
	float g0 = (fb(qm * 21.0) - 0.5);
	float gx = (fb((qm + tx * e) * 21.0) - 0.5);
	float gy = (fb((qm + ty * e) * 21.0) - 0.5);
	vec3 mg = (tx * (gx - g0) + ty * (gy - g0)) / e * 0.0035 * fine;
	vec3 N = bumped(n0, mg, 0.9 * bump_gain);

	// --- THICKNESS, and therefore colour ----------------------------------
	float thick = thin_m * mix(1.0 / ndv, ndv, thin_round);
	thick = clamp(thick, 0.002, 1.6) * 2.0;          // in and back out again
	vec3 transmit = exp(-ice_absorb * thick);

	// --- the internal fracture sheets, four steps -------------------------
	vec3 Rv = refract(V, N, 0.763);
	if (dot(Rv, Rv) < 0.001) { Rv = V; }
	float crk = 0.0;
	float glint = 0.0;
	float step_m = max(thin_m, 0.03) * 0.55;
	for (int i = 1; i <= 4; i++) {
		vec3 q = wpos + Rv * (step_m * float(i));
		float c = crack_at(q);
		float vis = 1.0 - clamp(crk, 0.0, 1.0);
		crk += c * vis * 0.32 * crack_gain;
		if (c > 0.02) {
			vec3 Lq = normalize(lamp_pos - q);
			float g = crack_at(q + Lq * 0.030) - c;
			glint += c * vis * clamp(0.5 - g * 6.0, 0.0, 1.0);
		}
	}
	crk = clamp(crk, 0.0, 1.0);

	float dmask = clamp(smoothstep(0.52, 0.92, fb(wpos * 1.9)) * debris_u * 2.2, 0.0, 1.0);

	// --- ROUGHNESS. Glassy. -----------------------------------------------
	float rough = mix(0.24, 0.055, polish_u);
	rough = mix(rough, 0.80, dmask * 0.85);
	rough = mix(rough, max(rough * 0.45, 0.034), wet_u * 0.8);
	rough = clamp(rough + (fb(wpos * 9.0) - 0.5) * 0.020, 0.032, 1.0);

	// --- REFRACTION, Godot's premultiplied idiom --------------------------
	// The offset is the VIEW-space normal, so a bulge bends what is behind it
	// sideways, and it shrinks with distance so a far icicle does not smear
	// the whole screen.
	vec3 vn = normalize((VIEW_MATRIX * vec4(N, 0.0)).xyz);
	vec2 ref_ofs = SCREEN_UV - vn.xy * (refract_str / max(dist, 0.35));
	vec3 behind = textureLod(screen_tex, clamp(ref_ofs, vec2(0.001), vec2(0.999)),
		rough * 6.0).rgb;

	// how much of the ray is STOPPED inside: cracks, dirt, and the ice itself
	float opac = clamp(crk * 0.85 + dmask + (1.0 - clarity_u) * 0.45, 0.0, 1.0);
	// and how much survives the trip, per channel. THIS is where the blue is:
	// a 40 mm tip transmits ~0.97 red and reads white; a 300 mm block
	// transmits ~0.80 red and reads faintly blue; the 3 m wall behind them is
	// a different shader and is properly blue.
	vec3 through = transmit * (1.0 - opac);

	// --- the lamp, and the glow -------------------------------------------
	vec3 Lv = lamp_pos - wpos;
	float ld = length(Lv);
	vec3 L = Lv / max(ld, 0.0001);
	float att = 1.0 / (1.0 + ld * ld * 1.35);
	float hard = cone(L, lamp_cos);
	float soft = cone(L, lamp_cos_wide);
	float halo = clamp(soft - hard, 0.0, 1.0);
	float wrap = clamp((dot(N, L) + 0.72) / 1.72, 0.0, 1.0);
	float inflow = lamp_energy * att * (hard * 0.45 + halo * 0.90) * wrap;
	vec3 Sv = sky_pos - wpos;
	float sd = length(Sv);
	float satt = sky_energy / (1.0 + sd * sd * 1.10);

	vec3 glow = transmit * scat_body * sss_gain * inflow * (1.0 - dmask * 0.85);
	glow += transmit * scat_body * sky_col * satt * (1.0 - dmask * 0.85);
	vec3 spark = transmit * clamp(glint, 0.0, 3.0) * scat_crack * lamp_energy * att
		* (hard * 0.85 + halo * 0.30) * (1.0 - dmask);

	// what the surface itself returns: the cracks and the dirt, lit
	// same split as the shell: a short path for what is multiplied by light
	vec3 t_short = exp(-ice_absorb * min(thick, 0.30));
	vec3 alb = mix(t_short * scat_body, t_short * scat_crack, crk);
	alb = mix(alb, vec3(dot(alb, vec3(0.3333))), 0.22);
	alb = mix(alb, debris_col, dmask);

	// PREMULTIPLIED. ALBEDO carries only the stopped fraction, EMISSION
	// carries what came through, and ALPHA finishes at 1 so the depth buffer
	// does the sorting.
	// 0.72 rather than 1.0: a fully honest premultiply hands a thin icicle a
	// black cave to be transparent ONTO, and it goes dark and reads as dirty
	// stone. Keeping a quarter of the surface's own return is the one place
	// in this shader where a number is chosen for the picture and not the
	// physics, and it is flagged as such.
	float o = clamp(dot(through, vec3(0.3333)), 0.0, 1.0) * 0.72;
	ALBEDO = alb * albedo_gain * (1.0 - o);
	EMISSION = behind * through * 0.72 + glow * 0.155 + spark * 0.090;
	ROUGHNESS = rough;
	METALLIC = 0.0;
	SPECULAR = 0.225;
	NORMAL = N;
	ALPHA = 1.0;
	AO_LIGHT_AFFECT = 0.0;
}
