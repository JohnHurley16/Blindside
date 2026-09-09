// ---------------------------------------------------------------------------
// BLINDSIDE -- the one rock material, AS COPIED INTO THE ASSAYER SPIKE.
//
// This is spikes/godot/cave/rock.gdshader verbatim plus ONE addition: the
// SCOUR (ART-DIRECTION 5.3) and the last firing's LOBE (machinery NOTES
// proposal 10). Nothing else was touched, so a fix in the cave copy is a
// three-line re-merge.
//
//   THE SCOUR. "Within ~9 cells the floor has no fines. Everything that could
//   be shaken loose has been. Bare, angular, freshly-fractured bedrock --
//   albedo up, roughness up, fracture frequency x3 -- surrounded by a floor of
//   silt and rounded rubble. No boundary drawn anywhere."  So: one radial
//   factor about the machine, its edge displaced by a metre-scale noise so
//   that there IS no edge, driving mud, fines, albedo, roughness and the joint
//   frequency together. Display tints the scour; the world de-silts it.
//
//   THE LOBE. The last firing's lethal wedge as a fractionally paler patch
//   where the fines were shaken off, +-40 deg about the aim, 1.9 to 5.4 m.
//   NEVER a glow, never magenta: only the display draws the field.
//
// ---------------------------------------------------------------------------
// (original header follows)
// BLINDSIDE -- the one rock material.   PHOTOREAL PASS (2026-09-09)
//
// ART-DIRECTION 3.1: one material, four scalars (wet / fracture / bedding /
// worked) plus a waterline. Three rock values, one warm buff family, no hue
// axis, no biome colour.
// ART-DIRECTION 3.2: world-space mapping, NEVER a UV. Nothing here is
// unwrapped and nothing here is photographic. The four sampler3Ds are noise
// GENERATED at load by FastNoiseLite (PROCEDURAL-AND-GODOT Q5, default yes) --
// they replace ~700 integer-hash evaluations per fragment with ~30-60 texture
// fetches, and that is what paid for everything else in this file.
//
// What is new in this pass, in the order it matters:
//   1. PARALLAX OCCLUSION MAPPING on the floor. A four-vertex polygon becomes
//      55 mm of packed aggregate, fines, ruts and puddles. Linear march plus
//      binary refine; step count falls with distance AND with view angle,
//      because looking straight down needs no parallax at all.
//   2. THREE NORMAL SCALES from one field: form (metres), detail (centimetres),
//      micro (millimetres), each with its own distance fade so the surface
//      never goes flat close up and never shimmers far away.
//   3. A WETNESS FIELD, not a scalar: height above the datum, surface
//      orientation, concavity, and drip runs off overhangs. It drives albedo,
//      roughness and specular together, which is what a wet surface does.
//   4. PUDDLES that follow the parallax height field, with a FLAT normal, so
//      water sits in the real low spots and the aggregate breaks its surface.
//   5. Roughness that varies everywhere, from the same field as the albedo.
//
// The scalars arrive per-vertex from the dressing layer:
//   COLOR.r  wet        0..1
//   COLOR.g  worked     0..1
//   COLOR.b  dark       0..1   (the depth field)
//   COLOR.a  iron       0..1   (proximity to something ferrous -> rust runs)
//   UV.x     axial distance along the passage, metres (drill rounds)
//   UV.y     perimeter position around the profile, 0..1 (shot-hole scallops)
//   UV2.x    SIGNED LATERAL OFFSET from the passage centreline, metres
//            (was "height above the local waterline"; the waterline is now a
//            uniform, and the floor needed a lateral coordinate for tracks)
//   UV2.y    packed rock type: floor(fracture01*31)*32 + floor(bedding01*31)
// ---------------------------------------------------------------------------
shader_type spatial;
render_mode blend_mix, depth_draw_opaque, cull_disabled, diffuse_burley, specular_schlick_ggx;

// generated at load: fbm, joint cellular (F2-F1), aggregate cellular (F1),
// per-cell value (so one stone is not the value of the stone beside it)
uniform sampler3D t_fbm : filter_linear, repeat_enable;
uniform sampler3D t_cel : filter_linear, repeat_enable;
uniform sampler3D t_agg : filter_linear, repeat_enable;
uniform sampler3D t_cid : filter_linear, repeat_enable;

// the three rock values, ART-DIRECTION 3.1
uniform vec3 rock_dry   = vec3(0.325, 0.250, 0.170);
uniform vec3 rock_sub   = vec3(0.090, 0.075, 0.062);
uniform vec3 rock_crust = vec3(0.480, 0.436, 0.372);
// The floor is NOT the wall lying down. ART-DIRECTION 3.1 gives a "scoured
// floor" at (0.42,0.36,0.28); that is a lit schematic value and it is far
// outside anything you can measure off a wet mine floor, which is muck at
// 0.05-0.12. Bent deliberately -- see PHOTOREAL.md.
uniform vec3 rock_floor = vec3(0.190, 0.158, 0.122);
uniform vec3 silt_col   = vec3(0.128, 0.108, 0.086);
uniform vec3 rust_tint  = vec3(0.230, 0.104, 0.044);

uniform float water_y     = -1000.0;  // the water datum, world Y, metres
uniform float pom_depth   = 0.075;    // how deep the floor reads
uniform float pom_far     = 4.0;      // metres past which the march stops
uniform int   pom_steps   = 20;
uniform float detail_far  = 13.0;
uniform float micro_far   = 2.6;
uniform float floor_bump_far = 12.0;
uniform float bump_gain   = 1.0;
uniform float wet_gain    = 1.0;

// --- the scour and the lobe (the only addition to the cave's copy) ---------
uniform vec3  scour_c    = vec3(0.0, 0.0, 0.0);  // the machine, world
uniform float scour_r    = 5.40;                 // 9 cells, the lethal contour
uniform float scour_soft = 1.60;                 // metres of blend
uniform float lobe_aim   = 0.0;                  // radians, atan2(z, x)
uniform float lobe_half  = 0.70;                 // +-40 deg
uniform float lobe_amt   = 0.0;                  // 0 = never fired

// world metres per texture tile, at three scales. The ratios are deliberately
// irrational-ish so the three tilings do not beat against each other.
const float LF = 3.70;
const float LD = 0.470;
const float LM = 0.0615;

varying vec3 wpos;
varying vec3 wnorm;

float fb(vec3 p) { return texture(t_fbm, p).r; }
float cj(vec3 p) { return texture(t_cel, p).r; }   // 0 on a joint, 1 mid-block
float ag(vec3 p) { return texture(t_agg, p).r; }   // 0 at a stone centre
float ci(vec3 p) { return texture(t_cid, p).r; }   // one value per stone

// ---------------------------------------------------------------------------
// FORM -- metres. Bedding, the joint set, the shot-hole barrels, the swell of
// the face. This is what you read from across the passage.
// ---------------------------------------------------------------------------
// `wof` is the domain-warp offset, computed ONCE per fragment and passed in.
// It varies over metres, so holding it constant across the four finite-
// difference taps is exact to first order and saves three texture fetches per
// tap -- twelve per fragment, on the most-shaded surface in the game.
float h_form(vec3 p, float fr, float bd, float wk, float ax, float pe, vec3 wof) {
	float h = (fb(p * (1.0 / LF)) - 0.5) * 0.42;
	// bedding: beds banded in world Y at 0.25..0.60 m (ART-DIRECTION 3.1)
	float per = mix(0.25, 0.60, fract(floor(p.y * 0.7) * 0.37 + 0.31));
	float bed = sin(p.y * 6.2831853 / per);
	h += bed * 0.016 * bd;
	h -= smoothstep(0.86, 1.0, bed * 0.5 + 0.5) * 0.042 * bd;   // the parting
	// the joint set: `fr` blocks per metre, warped so the cells are not all the
	// same size and the joints not all the same curvature. Un-warped cellular
	// reads as crazed pottery.
	vec3 jp = p + wof;
	float c = cj(jp * vec3(fr, fr * 0.40, fr) * (1.0 / 6.0));
	// a joint is a step between two blocks, not a groove: quantise it
	h -= (1.0 - smoothstep(0.0, 0.20, c)) * 0.062;
	// worked ground: half-barrel shot-hole scallops at 340 mm around the
	// perimeter in 1.6 m rounds, each round phase-offset (ART-DIRECTION 3.3)
	if (wk > 0.25) {
		float rid = floor(ax / 1.6);
		float ph = fract(sin(rid * 12.9898) * 43758.5453);
		float pm = pe * 7.5 + ph * 0.34;
		float sc = abs(fract(pm / 0.34) - 0.5) * 2.0;
		float ew = smoothstep(0.02, 0.16, fract(ax / 1.6));
		h += (sc * sc - 0.33) * 0.055 * wk * ew;
		h -= (1.0 - smoothstep(0.0, 0.06, fract(ax / 1.6))) * 0.020 * wk;
	}
	return h;
}

// DETAIL -- centimetres. Spall scars, the roughness of a broken face.
float h_det(vec3 p) {
	return (fb(p * (1.0 / LD)) - 0.5) * 0.062
	     + (fb(p * (1.0 / (LD * 0.31)) + vec3(5.1, 0.7, 2.3)) - 0.5) * 0.030;
}

// MICRO -- millimetres. Grain. Never visible past two metres; always visible
// under a lamp you are standing next to.
float h_mic(vec3 p) {
	return (fb(p * (1.0 / LM) + vec3(1.7, 9.1, 3.3)) - 0.5) * 0.0090;
}

// ---------------------------------------------------------------------------
// THE FLOOR HEIGHT FIELD -- what parallax marches against. 1 = the top of the
// aggregate, 0 = the bottom of the voids, over `pom_depth` metres.
//
// Two fetches only. Everything that does not change measurably over a 60 mm
// parallax offset -- the broad relief of the floor, how much of it the fines
// have buried, and the wheel ruts -- is hoisted out and arrives in `base`.
// ---------------------------------------------------------------------------
float h_march(vec2 xz, float base, float mud) {
	vec3 q = vec3(xz.x, 0.0, xz.y) * (1.0 / 0.60) + vec3(0.0, 3.0, 0.0);
	// Coarse aggregate, roughly 100 mm across. The HEIGHT of a stone is its
	// cell value, which is constant over the whole cell and steps at the cell
	// wall -- so each block is a flat facet sitting at its own level with a
	// hard arris, which is what blasted rock walked on for a century looks
	// like. Using the distance field for the height instead gives a dome, and
	// a field of domes reads as cauliflower. The distance field is used only
	// to bevel the arris and open the gap between blocks.
	// A NARROW bevel. The whole point of taking the height from the cell value
	// is that the top of a stone is FLAT; if the bevel is wide the distance
	// field takes over and every block becomes a dome, and a field of domes is
	// the cauliflower that three passes of this shader could not shake off.
	float bev = smoothstep(0.80, 0.60, ag(q));
	return clamp(base + (0.05 + 0.86 * ci(q)) * bev * (1.0 - mud * 0.70), 0.0, 1.0);
}

// The mid grade, ~250 mm: clods, spoil heaps in miniature, the lumps a floor
// has that are bigger than a stone. Too broad for parallax to add anything, so
// it goes into the normal only -- but it MUST go into the normal, because a
// term that only moves the height and never the shading is invisible.
float h_mid_ground(vec2 xz) {
	vec3 p = vec3(xz.x, 0.0, xz.y);
	return (fb(p * (1.0 / 0.30) + vec3(0.9, 0.0, 4.4)) - 0.5) * 0.024;
}

// the next grade down, ~25 mm. Too shallow to be worth parallax; it goes into
// the normal and the albedo only.
float h_fine_ground(vec2 xz) {
	vec3 q = vec3(xz.x, 0.0, xz.y) * (1.0 / 0.155) + vec3(5.0, 0.0, 9.0);
	return smoothstep(0.84, 0.58, ag(q)) * (0.004 + 0.016 * ci(q));
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
	wnorm = normalize((MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz);
}

void fragment() {
	float wet0    = COLOR.r;
	float worked  = COLOR.g;
	float dark    = COLOR.b;
	float iron    = COLOR.a;
	float axial   = UV.x;
	float perim   = UV.y;
	float lat     = UV2.x;             // metres from the centreline, signed
	float packed  = UV2.y;
	float frac01  = floor(packed / 32.0) / 31.0;
	float bed01   = fract(packed / 32.0) * 32.0 / 31.0;
	float fracture = mix(3.0, 14.0, clamp(frac01, 0.0, 1.0));
	float bedding  = mix(0.4, 3.5, clamp(bed01, 0.0, 1.0));

	vec3 n0 = normalize(wnorm);

	// --- THE SCOUR ---------------------------------------------------------
	// One radial factor whose edge is displaced by a metre-scale noise, so the
	// transition happens over 1.6 m and wanders by another 1.4 m: there is no
	// circle anywhere in it. It reaches everything the fines touch.
	float sdist = length(wpos.xz - scour_c.xz)
	            + (fb(vec3(wpos.x, 0.0, wpos.z) * (1.0 / 2.9) + vec3(0.0, 17.0, 0.0)) - 0.5) * 1.40;
	float scour = 1.0 - smoothstep(scour_r - scour_soft * 0.5, scour_r + scour_soft * 0.5, sdist);
	scour *= step(0.30, wnorm.y);                 // the floor only; walls keep their silt
	// freshly-fractured ground breaks smaller: ART-DIRECTION 5.3's "fracture
	// frequency x3", applied to the joint set the albedo and the form read.
	fracture *= 1.0 + 2.0 * scour;
	vec3 dv = wpos - CAMERA_POSITION_WORLD;
	float dist = length(dv);
	vec3 V = dv / max(dist, 0.0001);

	// per-scale distance fades. Amplitude, not frequency: a faded-out octave
	// costs nothing and cannot shimmer.
	float f_det = clamp(1.0 - (dist - detail_far * 0.42) / (detail_far * 0.58), 0.0, 1.0);
	float f_mic = clamp(1.0 - (dist - micro_far * 0.35) / (micro_far * 0.65), 0.0, 1.0);

	// -----------------------------------------------------------------------
	// THE FLOOR. Parallax where it is close enough to be worth it, the same
	// field as a bump map where it is not, so there is no distance at which
	// the floor becomes a plane.
	// -----------------------------------------------------------------------
	bool floorish = n0.y > 0.55;
	vec3 sp = wpos;
	float gh = 1.0;
	float gao = 1.0;
	float mud = 0.0;
	float f_flr = 0.0;
	vec2 huv = wpos.xz;
	if (floorish) {
		f_flr = clamp(1.0 - (dist - floor_bump_far * 0.4) / (floor_bump_far * 0.6), 0.0, 1.0);
		vec3 pp = vec3(wpos.x, 0.0, wpos.z);
		// where the fines have buried the aggregate. A mine floor is mostly
		// compacted muck with stone showing through it, not a gravel bed.
		mud = smoothstep(0.30, 0.70, fb(pp * (1.0 / 1.85) + vec3(0.0, 9.0, 0.0)));
		// nothing settles here: the compacted muck that buries the aggregate
		// everywhere else has been shaken off this ground for a century
		mud *= 1.0 - scour * 0.94;
		// the broad relief of the floor itself, and the trammed way worn into
		// it: two bands at the 0.60 m gauge plus a shallow dish between them.
		// Long wavelength only -- this term is hoisted out of the march, so it
		// decides where the hollows are and nothing about the shading.
		float base = 0.34 + (fb(pp * (1.0 / 1.90)) - 0.5) * 0.62;
		float wob = (fb(pp * (1.0 / 0.9) + vec3(21.0, 0.0, 6.0)) - 0.5) * 0.11;
		float dd = abs(abs(lat + wob) - 0.30);
		float rut = exp(-dd * dd * 150.0);
		float way = exp(-lat * lat * 2.0);
		float wear = smoothstep(0.25, 0.70, worked);
		base -= (rut * 0.42 + way * 0.14) * wear;
		base = clamp(base, 0.02, 0.96);

		float ramp = clamp(1.0 - dist / pom_far, 0.0, 1.0);
		if (ramp > 0.0) {
			// step count falls with distance AND with how far the view is from
			// vertical: looking straight down, the parallax offset is zero.
			float slant = clamp(length(V.xz) / max(-V.y, 0.20), 0.0, 1.6);
			float nsf = clamp(float(pom_steps) * ramp * (0.30 + 0.70 * slant), 5.0, float(pom_steps));
			int ns = int(nsf);
			float dl = 1.0 / nsf;
			vec2 dxz = (V.xz / max(-V.y, 0.20)) * pom_depth * dl;
			vec2 uv = wpos.xz;
			float cur = 1.0;
			float hs = h_march(uv, base, mud);
			for (int i = 0; i < ns; i++) {
				if (cur <= hs) {
					break;
				}
				uv += dxz;
				cur -= dl;
				hs = h_march(uv, base, mud);
			}
			// binary refine: five halvings beat forty more linear steps
			vec2 hstep = dxz * 0.5;
			float hl = dl * 0.5;
			for (int i = 0; i < 5; i++) {
				if (cur <= h_march(uv, base, mud)) {
					uv -= hstep;
					cur += hl;
				} else {
					uv += hstep;
					cur -= hl;
				}
				hstep *= 0.5;
				hl *= 0.5;
			}
			gh = clamp(cur, 0.0, 1.0);
			huv = uv;
		} else {
			gh = h_march(huv, base, mud);
		}
		sp = vec3(huv.x, wpos.y - (1.0 - gh) * pom_depth, huv.y);
		// the normal is the gradient of the field we just marched, plus the
		// finer grade that was too shallow to be worth marching against
		float e = 0.010;
		float ff = 1.0 - mud * 0.70;
		float hc = h_march(huv, base, mud) * pom_depth + h_fine_ground(huv) * ff + h_mid_ground(huv);
		float hx = h_march(huv + vec2(e, 0.0), base, mud) * pom_depth + h_fine_ground(huv + vec2(e, 0.0)) * ff + h_mid_ground(huv + vec2(e, 0.0));
		float hz = h_march(huv + vec2(0.0, e), base, mud) * pom_depth + h_fine_ground(huv + vec2(0.0, e)) * ff + h_mid_ground(huv + vec2(0.0, e));
		vec3 gn = normalize(vec3(clamp(-(hx - hc) / e, -2.2, 2.2), 1.0,
		                         clamp(-(hz - hc) / e, -2.2, 2.2)));
		n0 = normalize(mix(n0, gn, f_flr));
		// a real cavity term: fragments down in the voids see less of the room
		gao = mix(0.22, 1.0, smoothstep(0.0, 0.80, gh));
	}

	// -----------------------------------------------------------------------
	// NORMALS, three scales, all from the same height field
	// -----------------------------------------------------------------------
	vec3 n = n0;
	// One fetch, three axes. A scalar times vec3(1,1,1) would shear the joint
	// set along a single diagonal and the blocks would all lean the same way.
	vec3 wof = (fb(sp * (1.0 / (LF * 0.5)) + vec3(11.0, 3.0, 7.0)) - 0.5)
	           * vec3(0.55, -0.38, 0.47);
	{
		float ef = 0.055;
		float h0 = h_form(sp, fracture, bedding, worked, axial, perim, wof);
		vec3 g = vec3(h_form(sp + vec3(ef, 0.0, 0.0), fracture, bedding, worked, axial, perim, wof) - h0,
		              h_form(sp + vec3(0.0, ef, 0.0), fracture, bedding, worked, axial, perim, wof) - h0,
		              h_form(sp + vec3(0.0, 0.0, ef), fracture, bedding, worked, axial, perim, wof) - h0) / ef;
		float amp = mix(0.30, 1.05, clamp(frac01, 0.0, 1.0)) * bump_gain;
		n = bumped(n, g, amp * (floorish ? 0.16 : 0.82));
	}
	if (f_det > 0.004) {
		float ed = 0.018;
		float h0 = h_det(sp);
		vec3 g = vec3(h_det(sp + vec3(ed, 0.0, 0.0)) - h0,
		              h_det(sp + vec3(0.0, ed, 0.0)) - h0,
		              h_det(sp + vec3(0.0, 0.0, ed)) - h0) / ed;
		n = bumped(n, g, 0.78 * f_det * bump_gain);
	}
	float micro_h = 0.0;
	if (f_mic > 0.004) {
		float em = 0.0017;
		float h0 = h_mic(sp);
		micro_h = h0;
		vec3 g = vec3(h_mic(sp + vec3(em, 0.0, 0.0)) - h0,
		              h_mic(sp + vec3(0.0, em, 0.0)) - h0,
		              h_mic(sp + vec3(0.0, 0.0, em)) - h0) / em;
		n = bumped(n, g, 0.34 * f_mic * bump_gain);
	}

	// -----------------------------------------------------------------------
	// THE WETNESS FIELD. Not a scalar -- this is a drowned mine, so water is
	// the strongest cue available and it has to come from somewhere real:
	// height above the datum, which way the surface faces, whether it is a
	// hollow, and what runs down it from above.
	// -----------------------------------------------------------------------
	float above = sp.y - water_y;
	float submerged = 1.0 - smoothstep(-0.02, 0.02, above);
	float w_datum = 1.0 - smoothstep(0.0, 1.5, max(above, 0.0));
	float w_patch = fb(sp * (1.0 / 2.4) + vec3(0.0, 4.0, 0.0));
	// drip runs: stretched hard in Y so they fall, only on faces steep enough
	// for a run to exist, and only where there is water to run
	float run = fb(vec3(sp.x * 4.6, sp.y * 0.30, sp.z * 4.6) + vec3(7.0, 0.0, 1.0));
	float w_run = smoothstep(0.56, 0.88, run) * smoothstep(0.45, 0.80, 1.0 - abs(n.y));
	// The floor is the wettest surface in a drowned mine: everything that runs
	// down a wall ends up on it, and nothing dries. Without this term the drive
	// floor read as pale dry dust at every depth, which is the one thing a
	// flooded working cannot be.
	float w_floor = floorish ? (0.15 + (1.0 - gh) * 0.34) * (0.45 + 0.55 * w_patch) : 0.0;
	float wet = wet0 * (0.30 + 0.70 * w_patch) * 0.80 + w_datum * 0.45
	            + w_run * 0.70 * (0.40 + 0.60 * wet0) + w_floor;
	wet = clamp(wet * wet_gain, 0.0, 1.0);
	wet = max(wet, submerged);

	// PUDDLES, following the parallax field, so the water sits in the real low
	// spots and the aggregate breaks its surface.
	float plevel = (0.20 + 0.50 * fb(sp * (1.0 / 1.75) + vec3(6.0, 1.0, 0.0)))
	               * smoothstep(0.46, 0.92, wet);
	float pool = floorish ? clamp((plevel - gh) / 0.055, 0.0, 1.0) : 0.0;
	// the wet/dry boundary: a puddle that has stood and shrunk leaves a pale
	// mineral rim, and the rim is what says the water level MOVED
	float rim = floorish ? clamp(1.0 - abs(gh - plevel) / 0.075, 0.0, 1.0) * (1.0 - pool) : 0.0;
	pool = max(pool, submerged);
	if (pool > 0.001) {
		// a water surface is FLAT. Leaving the rock normal under it is what
		// makes a "wet" shader sparkle like glitter instead of reading as water.
		float rip = (fb(sp * 26.0 + vec3(0.0, TIME * 0.05, 0.0)) - 0.5)
		          + (fb(sp * 61.0 + vec3(TIME * 0.03, 0.0, 0.0)) - 0.5) * 0.5;
		vec3 wn2 = normalize(vec3(rip * 0.055, 1.0, rip * 0.055));
		n = normalize(mix(n, wn2, pool));
	}

	// -----------------------------------------------------------------------
	// ALBEDO
	// -----------------------------------------------------------------------
	vec3 alb = rock_dry;
	if (floorish) {
		// the floor is muck, not a wall lying down
		alb = mix(alb, rock_floor, (0.62 + 0.30 * worked) * f_flr + 0.55 * (1.0 - f_flr));
		// each stone gets its own value. Without this, aggregate is one grey.
		vec3 qc = vec3(sp.x, 0.0, sp.z) * (1.0 / 0.60) + vec3(0.0, 3.0, 0.0);
		float cv = ci(qc);
		float onstone = smoothstep(0.80, 0.60, ag(qc)) * (1.0 - mud * 0.55);
		alb *= mix(1.0, 0.42 + 1.30 * cv, onstone * f_flr);
		// the finer grade carries its own value too
		vec3 qf = vec3(sp.x, 0.0, sp.z) * (1.0 / 0.155) + vec3(5.0, 0.0, 9.0);
		alb *= mix(1.0, 0.58 + 0.90 * ci(qf), smoothstep(0.84, 0.58, ag(qf)) * (1.0 - mud * 0.6) * f_flr);
		alb = mix(alb, silt_col, mud * 0.45 * f_flr);
		// Large-scale value structure. Without this the floor is uniformly
		// speckled and reads as a texture rather than as a place: real ground
		// has metre-scale patches -- dried pale muck, black wet muck, a drift
		// of fines against a sleeper.
		float patchv = fb(vec3(sp.x, 0.0, sp.z) * (1.0 / 2.6) + vec3(13.0, 0.0, 5.0));
		alb *= mix(1.0, 0.52 + 1.20 * patchv, f_flr);
	}
	// bedding as value, never as hue (ART-DIRECTION 3.5)
	float per2 = mix(0.25, 0.60, fract(floor(sp.y * 0.7) * 0.37 + 0.31));
	float bedv = sin(sp.y * 6.2831853 / per2) * 0.5 + 0.5;
	alb *= 1.0 + (bedv - 0.5) * 0.46 * (bedding / 3.5);
	alb *= 1.0 - smoothstep(0.86, 0.995, bedv) * 0.32 * (bedding / 3.5);
	// open joints read dark because they are holes, not because they are painted
	vec3 jc = (sp + wof) * vec3(fracture, fracture * 0.40, fracture) * (1.0 / 6.0);
	float joint = 1.0 - smoothstep(0.0, 0.085, cj(jc));
	alb *= 1.0 - joint * 0.58;
	// one block is not the value of the block beside it
	alb *= 0.80 + 0.42 * ci(jc);
	// a coarser second joint set: the beds part as well as the blocks
	float cjv2 = cj(sp * vec3(0.36, 1.9, 0.36) * (1.0 / 6.0) + vec3(3.0, 5.0, 9.0));
	alb *= 1.0 - (1.0 - smoothstep(0.0, 0.075, cjv2)) * 0.26;
	// broad mineral staining. Nothing in a mine is one colour, and this is the
	// only place chroma enters -- warm, low frequency, small in amplitude.
	float stain = fb(sp * vec3(0.30, 0.10, 0.30) * 0.9);
	alb *= 0.72 + 0.44 * stain;
	// ART-DIRECTION 3.1 forbids a hue axis. This is the ONE place chroma moves,
	// it is +-3.5% on two channels, and it is mineral staining rather than a
	// biome colour. See PHOTOREAL.md for the rule this bends and how far.
	alb.r *= 1.0 + (stain - 0.5) * 0.07;
	alb.b *= 1.0 - (stain - 0.5) * 0.07;
	// detail and micro break the value up so no patch is one number
	alb *= 0.88 + 0.24 * fb(sp * (1.0 / LD) + vec3(2.0, 8.0, 5.0));
	// dirt collects in the crevices of the SAME field the normal came from.
	// With the lamp at the eye this carries more of the relief than the normal
	// does, because N.L equals N.V and the cosine term barely moves.
	float dh = h_det(sp);
	alb *= clamp(0.78 + 6.0 * dh * f_det, 0.45, 1.25);
	alb *= 1.0 + micro_h * 6.0 * f_mic;
	// fines gather in the hollows even where the floor is stony
	float fines = floorish ? smoothstep(0.52, 0.12, gh) * f_flr : 0.0;
	fines = max(fines, mud * 0.8 * f_flr);
	fines *= 1.0 - scour * 0.92;
	fines *= 0.45 + 0.55 * fb(sp * (1.0 / 0.85) + vec3(0.0, 12.0, 0.0));
	alb = mix(alb, silt_col, fines * 0.60);
	// the 0.12 m mineral tide-mark crust above the line (ART-DIRECTION 3.5),
	// with a boundary that wanders instead of being a spirit level
	float bwob = (fb(sp * vec3(1.4, 0.4, 1.4)) - 0.5) * 0.10;
	float ab2 = above + bwob;
	float crust = smoothstep(-0.006, 0.006, ab2) * (1.0 - smoothstep(0.0, 0.13, ab2));
	crust *= 0.40 + 0.60 * fb(sp * 2.6);
	alb = mix(alb, rock_crust, crust * 0.80);
	// under the water the rock is darker
	alb = mix(alb, rock_sub, submerged);
	// water darkens what it wets. This is the single strongest free cue.
	alb *= mix(1.0, 0.54, wet);
	alb *= mix(1.0, 0.55, pool);
	// rust runs off anything ferrous, falling, gated on the iron channel
	float streak = fb(vec3(sp.x * 4.4, sp.y * 0.36, sp.z * 4.4) + vec3(0.0, 0.0, 17.0));
	streak = smoothstep(0.60, 0.92, streak) * iron;
	alb = mix(alb, rust_tint, clamp(streak * 0.42, 0.0, 1.0));
	alb = mix(alb, rock_crust, rim * 0.42 * (0.4 + 0.6 * fb(sp * 5.0)));
	// --- the scour, in albedo ----------------------------------------------
	// bare fresh-fractured rock is PALER than the silted floor around it, and
	// it is the one place the floor value gets to rise. ART-DIRECTION 5.3 says
	// "albedo up to 0.42"; the clamp below holds the whole shader at 0.55.
	alb *= 1.0 + 0.78 * scour;
	// --- the last firing's lobe -------------------------------------------
	// a fractionally paler wedge where the fines jumped. Not a glow, not a
	// boundary, and nowhere near HAZARD: only the display draws the field.
	if (lobe_amt > 0.001 && floorish) {
		float th = atan(wpos.z - scour_c.z, wpos.x - scour_c.x) - lobe_aim;
		th = abs(atan(sin(th), cos(th)));
		float lb = smoothstep(lobe_half, lobe_half * 0.72, th)
		         * smoothstep(1.6, 2.4, sdist) * (1.0 - smoothstep(4.9, 5.7, sdist));
		alb *= 1.0 + lb * lobe_amt * 0.13;
	}
	// depth is drawn as darkness (ART-DIRECTION 7)
	alb *= 1.0 - 0.50 * clamp(dark, 0.0, 1.0);
	// nothing in nature is pure black or above 0.9
	ALBEDO = clamp(alb, vec3(0.014), vec3(0.55));

	// -----------------------------------------------------------------------
	// ROUGHNESS -- driven by the same field as the albedo, so wet, dusty,
	// crusted, freshly-broken and polished ground all differ.
	// -----------------------------------------------------------------------
	float r_dry = 0.88 + (fb(sp * (1.0 / 0.62) + vec3(9.0, 2.0, 4.0)) - 0.5) * 0.16;
	r_dry = mix(r_dry, 0.97, fines);                      // silt is dead matte
	r_dry = mix(r_dry, 0.95, crust);                      // so is the crust
	r_dry = mix(r_dry, 0.97, rim * 0.7);                  // and the dried rim
	if (floorish) {
		// a trammed floor is polished by everything that ran over it
		vec3 pp2 = vec3(sp.x, 0.0, sp.z);
		float wob2 = (fb(pp2 * (1.0 / 0.9) + vec3(21.0, 0.0, 6.0)) - 0.5) * 0.11;
		float dd2 = abs(abs(lat + wob2) - 0.30);
		r_dry = mix(r_dry, 0.44, exp(-dd2 * dd2 * 150.0) * smoothstep(0.25, 0.70, worked) * (1.0 - fines) * f_flr);
	}
	// a freshly-broken face is rougher than one a century of fines has polished
	r_dry = mix(r_dry, 0.955, scour * 0.55);
	// millimetre roughness variation: without this every highlight is a disc
	r_dry += micro_h * 14.0 * f_mic;
	float rough = mix(r_dry, 0.24, wet * wet * 0.88);
	rough = mix(rough, 0.040, pool);
	// specular anti-aliasing: a high-frequency normal at low roughness sparkles
	// like glitter at range, so put the roughness floor up with distance
	ROUGHNESS = clamp(rough, 0.038 + clamp(dist * 0.022, 0.0, 0.30), 1.0);

	// rock is a dielectric: F0 about 4-6%. Never metallic, never in between.
	SPECULAR = mix(0.50, 0.58, max(wet, pool));
	METALLIC = 0.0;
	NORMAL = normalize((VIEW_MATRIX * vec4(n, 0.0)).xyz);

	// cavity: the parallax field where we have one, the form field where we do
	// not. This is what holds joints and scallops open under a lamp that sits
	// at the eye and therefore casts no modelling shadow of its own.
	float cav = clamp(0.56 + 9.0 * dh * f_det, 0.22, 1.0);
	AO = clamp(min(gao, cav) * (1.0 - joint * 0.45), 0.14, 1.0);
	AO_LIGHT_AFFECT = 1.0;
}
