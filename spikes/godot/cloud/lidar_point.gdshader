// ---------------------------------------------------------------------------
// BLINDSIDE -- a return is a POINT.
//
// Replaces the additive oriented disc. The three things that make the output
// read as sensor data rather than as mist, in the order they matter:
//
//   1. OPAQUE, DEPTH-TESTED, DEPTH-WRITING. A near return hides a far one.
//      Every point-cloud viewer anyone works in does this and the additive
//      x-ray does not; additive blending is the single biggest reason the
//      previous pass looked like a nebula. It also means no sorting is needed
//      (the depth buffer does it) and the count no longer has to be paid for
//      with a 1/sqrt(N) brightness fudge -- there is no accumulation to blow
//      out, so the view is self-exposing at any density.
//   2. SMALL AND SHARP. A hard-edged round dot of a near-constant screen size
//      with a floor and a cap, not a soft footprint disc. Structure comes from
//      WHERE the points are, not from how much they overlap.
//   3. COLOURED BY A CHANNEL, not by class. Intensity or height, the way a
//      scan is conventionally read. Ring and epoch are the diagnostic modes.
//
// Instance packing is UNCHANGED from cloud_body.gdshaderinc, so the data path,
// the 64 bytes a point and the free scrub all survive:
//   column 0 = p1 - p0    what the next fix does to this point, metres
//   column 1 = n0         sensor -> hit before that fix, UNNORMALISED
//   column 2 = n1         the same after it
//   origin   = p0         where it was believed to be when it was measured
//   custom   = (intensity, t_placed, t_fix or -1, ring + 64 * surface class)
// ---------------------------------------------------------------------------
shader_type spatial;
render_mode unshaded, shadows_disabled, cull_disabled, fog_disabled;

uniform float u_now = 60.0;
uniform float u_ease_s = 0.7;          // a fix lands in one tick; the eye needs 0.7 s
uniform int u_mode = 0;                // 0 int-cool 1 int-jet 2 height 3 ring 4 epoch 5 range
uniform float u_pt_world = 0.020;      // metres; the point grows a little when near
uniform float u_min_px = 1.6;
uniform float u_max_px = 5.0;
uniform vec2 u_vp = vec2(1920.0, 1080.0);
uniform float u_gain = 1.0;
uniform float u_age_knee_s = 90.0;
uniform float u_age_floor = 0.42;
uniform float u_h_lo = -1.0;
uniform float u_h_hi = 4.0;
uniform float u_r_hi = 30.0;
uniform float u_epoch_split = -1.0;
uniform float u_epoch_only = 0.0;
uniform vec3 u_before : source_color = vec3(0.388, 0.839, 0.969);
uniform vec3 u_after : source_color = vec3(1.000, 0.824, 0.247);
uniform float u_clip_lo = -1000.0;     // crop box, world Y. Every point-cloud
uniform float u_clip_hi = 1000.0;      // tool has one, and a tube of returns
                                       // cannot be read from outside without it.
// THE SECTION, added 2026-09-10 for the map. A crop box in Y takes the ceiling
// off a flat cave; a cave with four levels in it cannot be cropped in Y at all
// without deleting the subject. So the box gains its other two axes, and an
// ORIENTED slab: keep only points within [u_cut_d0, u_cut_d1] of the origin
// along u_cut_n. One plane normal, animatable, and it is the same operator --
// it only ever REMOVES points and it never draws anything into a shadow.
uniform vec3 u_cut_n = vec3(0.0, 0.0, 0.0);
uniform float u_cut_d0 = -1.0e9;
uniform float u_cut_d1 = 1.0e9;
uniform float u_clip_x_lo = -1.0e9;
uniform float u_clip_x_hi = 1.0e9;
uniform float u_clip_z_lo = -1.0e9;
uniform float u_clip_z_hi = 1.0e9;
uniform float u_square = 0.0;          // 1 = square dots (what most viewers draw)
uniform float u_footprint = 0.0;       // 1 = size by beam footprint instead of screen px
uniform float u_beam_mrad = 3.0;

varying vec3 v_col;
varying vec2 v_c;

vec3 ramp4(float t, vec3 a, vec3 b, vec3 c, vec3 d) {
	t = clamp(t, 0.0, 1.0);
	if (t < 0.3333) return mix(a, b, t * 3.0);
	if (t < 0.6667) return mix(b, c, (t - 0.3333) * 3.0);
	return mix(c, d, (t - 0.6667) * 3.0);
}

vec3 ramp5(float t, vec3 a, vec3 b, vec3 c, vec3 d, vec3 e) {
	t = clamp(t, 0.0, 1.0);
	if (t < 0.25) return mix(a, b, t * 4.0);
	if (t < 0.50) return mix(b, c, (t - 0.25) * 4.0);
	if (t < 0.75) return mix(c, d, (t - 0.50) * 4.0);
	return mix(d, e, (t - 0.75) * 4.0);
}

void vertex() {
	vec3 p0 = MODEL_MATRIX[3].xyz;
	vec3 dp = MODEL_MATRIX[0].xyz;
	vec3 n0 = MODEL_MATRIX[1].xyz;
	vec3 n1 = MODEL_MATRIX[2].xyz;
	float inten = INSTANCE_CUSTOM.x;
	float tp = INSTANCE_CUSTOM.y;
	float tf = INSTANCE_CUSTOM.z;
	float packed = INSTANCE_CUSTOM.w;
	float ring = mod(packed, 64.0);
	float cls = floor(packed / 64.0);

	vec2 corner = UV * 2.0 - 1.0;
	v_c = corner;

	// the fix: a point is moved by AT MOST ONE correction, ever, so the whole
	// of drift / the fix / the lie is this one lerp and the scrub is free.
	float w = 0.0;
	if (tf >= 0.0 && u_now >= tf) {
		w = clamp((u_now - tf) / max(u_ease_s, 1e-4), 0.0, 1.0);
		w = 1.0 - pow(1.0 - w, 3.0);
	}
	vec3 p = p0 + dp * w;
	float rng = length(mix(n0, n1, w));

	bool hidden = tp > u_now || p.y < u_clip_lo || p.y > u_clip_hi
		|| p.x < u_clip_x_lo || p.x > u_clip_x_hi
		|| p.z < u_clip_z_lo || p.z > u_clip_z_hi;
	if (dot(u_cut_n, u_cut_n) > 1e-6) {
		float d = dot(p, normalize(u_cut_n));
		hidden = hidden || d < u_cut_d0 || d > u_cut_d1;
	}

	// ---- colour --------------------------------------------------------
	vec3 col;
	if (u_mode == 0) {
		// intensity, in the belief palette: dark teal -> SENSED -> white.
		col = ramp4(inten,
			vec3(0.086, 0.235, 0.302), vec3(0.176, 0.463, 0.596),
			vec3(0.388, 0.839, 0.969), vec3(1.000, 1.000, 1.000));
	} else if (u_mode == 1) {
		// intensity, the conventional scan ramp, for comparison only.
		col = ramp5(inten,
			vec3(0.055, 0.031, 0.290), vec3(0.031, 0.400, 0.831),
			vec3(0.086, 0.804, 0.545), vec3(0.941, 0.855, 0.161),
			vec3(1.000, 1.000, 1.000));
	} else if (u_mode == 2) {
		float h = clamp((p.y - u_h_lo) / max(u_h_hi - u_h_lo, 0.01), 0.0, 1.0);
		col = ramp4(h,
			vec3(0.086, 0.161, 0.451), vec3(0.098, 0.600, 0.808),
			vec3(0.373, 0.902, 0.827), vec3(0.965, 0.984, 0.800));
	} else if (u_mode == 3) {
		// ring index. The diagnostic view: if these bands are not obvious the
		// sensor model is wrong.
		float f = ring / 6.0;
		col = 0.45 + 0.55 * cos(6.2831853 * (f + vec3(0.0, 0.33, 0.67)));
		col *= mix(0.55, 1.0, mod(ring, 2.0));
	} else if (u_mode == 4) {
		col = tp <= u_epoch_split ? u_before : u_after;
		col *= 0.45 + 0.85 * inten;
	} else {
		col = ramp4(clamp(rng / u_r_hi, 0.0, 1.0),
			vec3(1.000, 0.980, 0.900), vec3(0.388, 0.839, 0.969),
			vec3(0.157, 0.427, 0.561), vec3(0.055, 0.176, 0.239));
	}

	// age. An old return is dimmer and stays where it was believed to be.
	float age = max(u_now - tp, 0.0);
	float dim = mix(1.0, u_age_floor, clamp(age / max(u_age_knee_s, 0.01), 0.0, 1.0));
	// a retroreflector is the one thing that never dims into the background
	if (cls > 3.5) { dim = max(dim, 0.85); }
	v_col = col * dim * u_gain;

	// ---- size ----------------------------------------------------------
	vec4 view = VIEW_MATRIX * vec4(p, 1.0);
	vec4 clip = PROJECTION_MATRIX * view;
	float dist = max(-view.z, 0.01);
	float ppm = 0.5 * u_vp.y * PROJECTION_MATRIX[1][1] / dist;
	float world_r = mix(u_pt_world, rng * u_beam_mrad * 0.0005, u_footprint);
	float px = clamp(world_r * ppm, u_min_px, u_max_px);
	clip.xy += corner * px * clip.w * 2.0 / u_vp;
	POSITION = hidden ? vec4(2.0, 2.0, 2.0, 1.0) : clip;
}

void fragment() {
	// a hard round dot. `u_square` gives the square splat most viewers draw;
	// at two pixels the difference is academic, at eight it is not.
	if (u_square < 0.5 && dot(v_c, v_c) > 1.0) { discard; }
	ALBEDO = v_col;
}
