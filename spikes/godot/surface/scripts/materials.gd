extends RefCounted
class_name Mats
##
## DRESSING LAYER - materials.
##
## One shader for every solid on the site, plus one for the ground. No image
## texture, no UV unwrap: everything is world space procedural, which is the only
## thing that survives a generated site (ART-DIRECTION 3.2).
##
## PHOTOREAL PASS (2026-09-09, DESIGN-PRINCIPLES 6). Both shaders were rewritten
## against a checklist rather than a vibe:
##
##  * one procedural HEIGHT FIELD per material, and albedo, roughness, normal
##    and ambient occlusion are all read off that same field, so they agree.
##    A surface whose roughness does not follow its albedo reads as a decal.
##  * THREE NORMAL SCALES - form, detail, micro - each faded in at its own
##    distance, so a wall has shape at 20 m, tooling at 6 m and grain at 1 m.
##  * PARALLAX OCCLUSION MAPPING on the ground, step count ramped by distance
##    and off entirely past 18 m. This is what stops the hardstanding being a
##    plane with a picture of concrete on it.
##  * METALLIC IS STRICTLY 0 OR 1. There is no such thing as 0.72 metal.
##  * ALBEDO IN MEASURED RANGES: weathered concrete 0.22-0.30 linear before
##    wear, oil-soaked concrete and wet asphalt under 0.06, rusted steel
##    0.10-0.26, and every one of those VARIES across the surface.
##
## Per-instance MultiMesh colour still multiplies albedo, so one material covers
## a whole family (rust light to rust black, bone to grubby bone) in one draw.

## ---------------------------------------------------------------------------
## Shared procedural noise. Written once, pasted into both shaders, because a
## Godot shader has no include.
##
## Two changes from the first pass and both are visible in a still:
##   * GRADIENT noise, not value noise. Value noise on an axis-aligned lattice
##     puts a visible square check into every mask built on it, and at ~1 m cell
##     size on the hardstanding that check was the single most artificial thing
##     in the underfoot frame.
##   * every octave is ROTATED as well as scaled (the 0.8/0.6 matrix), which is
##     what stops four octaves stacking their lattices on the same axes.
const NOISE := """
vec3 hash33(vec3 p3) {
	p3 = fract(p3 * vec3(0.1031, 0.1030, 0.0973));
	p3 += dot(p3, p3.yxz + 33.33);
	return fract((p3.xxy + p3.yxx) * p3.zyx);
}
float hash21(vec2 p) {
	vec3 p3 = fract(vec3(p.xyx) * 0.1031);
	p3 += dot(p3, p3.yzx + 33.33);
	return fract((p3.x + p3.y) * p3.z);
}
vec2 hash22(vec2 p) {
	vec3 p3 = fract(vec3(p.xyx) * vec3(0.1031, 0.1030, 0.0973));
	p3 += dot(p3, p3.yzx + 33.33);
	return fract((p3.xx + p3.yz) * p3.zy) * 2.0 - 1.0;
}
// gradient noise, 0..1
float gnoise(vec2 p) {
	vec2 i = floor(p);
	vec2 f = p - i;
	vec2 u = f * f * (3.0 - 2.0 * f);
	float a = dot(hash22(i), f);
	float b = dot(hash22(i + vec2(1.0, 0.0)), f - vec2(1.0, 0.0));
	float c = dot(hash22(i + vec2(0.0, 1.0)), f - vec2(0.0, 1.0));
	float d = dot(hash22(i + vec2(1.0, 1.0)), f - vec2(1.0, 1.0));
	return mix(mix(a, b, u.x), mix(c, d, u.x), u.y) * 0.7 + 0.5;
}
const mat2 ROT = mat2(vec2(0.8, 0.6), vec2(-0.6, 0.8));
float fbm4(vec2 p) {
	float s = 0.0; float a = 0.5; float t = 0.0;
	for (int i = 0; i < 4; i++) { s += a * gnoise(p); t += a; p = ROT * p * 2.07; a *= 0.5; }
	return clamp((s / t - 0.320) * 2.78, 0.0, 1.0);
}
float fbm2(vec2 p) {
	float s = gnoise(p) * 0.66;
	p = ROT * p * 2.13;
	return clamp((s + gnoise(p) * 0.34 - 0.235) * 1.89, 0.0, 1.0);
}
// worley: x = f1, y = f2, zw = vector to the nearest feature point.
// The zw is what makes a cheap analytic bump normal possible - a stone leans
// away from its own centre, and that is the whole shape of embedded aggregate.
vec4 worley(vec2 p) {
	vec2 i = floor(p);
	vec2 f = p - i;
	float d1 = 8.0; float d2 = 8.0; vec2 v1 = vec2(0.0);
	for (int y = -1; y <= 1; y++) {
		for (int x = -1; x <= 1; x++) {
			vec2 g = vec2(float(x), float(y));
			vec2 o = hash22(i + g) * 0.5 + 0.5;
			vec2 dv = g + o - f;
			float d = dot(dv, dv);
			if (d < d1) { d2 = d1; d1 = d; v1 = dv; }
			else if (d < d2) { d2 = d; }
		}
	}
	return vec4(sqrt(d1), sqrt(d2), v1);
}
"""

## ---------------------------------------------------------------------------
## THE SOLID SHADER - everything on the site that is not the ground.
const SOLID_SHADER := """
shader_type spatial;
render_mode cull_back, diffuse_burley, specular_schlick_ggx;

uniform vec3 base_col : source_color = vec3(0.3);
uniform float rough_lo = 0.5;
uniform float rough_hi = 0.95;
uniform float metal = 0.0;          // 0 or 1. Nothing else exists.
uniform float grain = 1.0;          // how much the height field varies albedo
uniform float streak = 0.0;         // vertical rust / mineral runs
uniform vec3 streak_col : source_color = vec3(0.16, 0.07, 0.03);
uniform float noise_scale = 2.0;
uniform float wet_take = 1.0;       // how much this material responds to rain
uniform float dirt = 0.35;          // dust settling on up-facing surfaces
uniform vec3 dirt_col : source_color = vec3(0.19, 0.16, 0.12);
uniform float emissive = 0.0;
uniform float relief = 1.0;         // how deep this material's surface is
uniform float pit = 0.0;            // corrosion pitting: iron and stone only
uniform float bump_form = 0.0068;   // metres, the 0.4 m scale
uniform float bump_det = 0.0024;    // metres, the 5 cm scale
uniform float bump_mic = 0.00052;   // metres, the 6 mm scale
uniform float detail_on = 1.0;      // 0 = strip the normal scales, for pricing
global uniform float g_wet;

__NOISE__

varying vec3 wpos;
varying vec3 wnorm;

void vertex() {
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	wnorm = normalize((MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz);
}

// The kit is flat-shaded axis-aligned prisms under a rotation, so a HARD
// triplanar axis pick costs nothing and never blends. The two tangent axes it
// returns are world axes, which is why the gradient maps straight back out.
void tri_axes(vec3 n, out vec3 ta, out vec3 tb) {
	vec3 a = abs(n);
	if (a.y >= a.x && a.y >= a.z) { ta = vec3(1.0, 0.0, 0.0); tb = vec3(0.0, 0.0, 1.0); }
	else if (a.x >= a.z)          { ta = vec3(0.0, 0.0, 1.0); tb = vec3(0.0, 1.0, 0.0); }
	else                          { ta = vec3(1.0, 0.0, 0.0); tb = vec3(0.0, 1.0, 0.0); }
}

// d/dx of smoothstep(a, b, x). Wanted because an analytic gradient off a worley
// cell is free, and a finite difference through a worley is nine hashes a tap.
float sstep_d(float a, float b, float x) {
	float t = clamp((x - a) / (b - a), 0.0, 1.0);
	return 6.0 * t * (1.0 - t) / (b - a);
}

// the material's height field: form at 0.38 m and detail at 5 cm in one
// function, so one epsilon and two forward differences serve both
float sh_c(vec2 q, float fd) {
	return gnoise(q * 2.6) * bump_form + gnoise(q * 21.0) * bump_det * fd;
}

void fragment() {
	vec3 ta; vec3 tb;
	tri_axes(wnorm, ta, tb);
	vec2 q = vec2(dot(wpos, ta), dot(wpos, tb));
	float dist = length(wpos - CAMERA_POSITION_WORLD);

	// --- THREE NORMAL SCALES, each fading in at its own distance.
	// Form is always on; detail arrives at ~24 m, micro at ~4.5 m. Fading them
	// rather than running them everywhere is what keeps this affordable, and it
	// is also correct: 6 mm grain at 30 m is aliasing, not detail.
	float f_det = (1.0 - smoothstep(8.0, 17.0, dist)) * detail_on;
	float f_mic = (1.0 - smoothstep(1.4, 3.6, dist)) * detail_on;

	// corrosion, computed ONCE. The pit field feeds albedo, roughness, occlusion
	// and the normal, and it is patchy - a uniform pit density over a whole
	// member reads as a printed dot screen, which is what it looked like first.
	float pd = 0.0;
	float pits = 0.0;
	vec4 wp = vec4(0.0);
	if (pit > 0.0 && detail_on > 0.5) {
		pd = pit * (0.25 + 0.95 * fbm2(q * 1.35 + 5.0));
		wp = worley(q * 34.0);
		pits = 1.0 - smoothstep(0.0, 0.42, wp.x);
	}

	vec3 n = wnorm;
	if (detail_on > 0.5) {
		float ec = 0.006;
		float h0 = sh_c(q, f_det);
		float gx = (sh_c(q + vec2(ec, 0.0), f_det) - h0) / ec;
		float gy = (sh_c(q + vec2(0.0, ec), f_det) - h0) / ec;
		n -= (ta * gx + tb * gy) * relief;
	}
	if (pd > 0.0 && f_det > 0.004) {
		// a pit is a crater, and the vector to its centre came back free with the
		// worley the albedo already needed
		float mag = -sstep_d(0.0, 0.42, wp.x) * pd * bump_det * 2.4 * 34.0 * f_det;
		vec2 dir = wp.x > 1e-4 ? -wp.zw / wp.x : vec2(0.0);
		n -= (ta * dir.x + tb * dir.y) * mag * relief;
	}
	if (f_mic > 0.002) {
		float em = 0.0016;
		float g0 = gnoise(q * 140.0);
		float gx = (gnoise((q + vec2(em, 0.0)) * 140.0) - g0) * bump_mic / em;
		float gy = (gnoise((q + vec2(0.0, em)) * 140.0) - g0) * bump_mic / em;
		n -= (ta * gx + tb * gy) * relief * f_mic;
	}
	n = normalize(n);

	// --- ALBEDO, off the same field. One surface, many values.
	float nf = fbm4(q * noise_scale * 0.5);
	float fine = fbm2(q * noise_scale * 4.5);
	vec3 alb = base_col * COLOR.rgb;
	alb *= mix(1.0 - grain * 0.55, 1.0 + grain * 0.50, nf);
	alb *= mix(0.86, 1.14, fine);

	// corrosion: scale flakes off in patches and what is under it is darker
	float cav = pits * pd;
	if (pd > 0.0) {
		alb *= mix(1.0, 0.42, cav);
		float flake = smoothstep(0.52, 0.74, fbm2(q * 6.0 + 11.0));
		alb *= mix(1.0, 1.35, flake * pit);
	}

	// vertical runs: smear the noise down the world Y axis. Gravity, not noise.
	float side = clamp(1.0 - abs(wnorm.y), 0.0, 1.0);
	if (streak > 0.0 && side > 0.03) {
		float s = fbm2(vec2(wpos.x * 3.1 + wpos.z * 3.1, wpos.y * 0.30));
		alb = mix(alb, streak_col, smoothstep(0.50, 0.80, s) * side * streak);
	}

	// dust and mud settle on horizontals; that is gravity too
	float up = clamp(wnorm.y, 0.0, 1.0);
	if (up > 0.03 && dirt > 0.01) {
		float set = up * up * up * dirt * mix(0.45, 1.35, fbm2(q * 0.7));
		alb = mix(alb, dirt_col, clamp(set, 0.0, 0.85));
	}

	// --- ROUGHNESS, driven by the SAME field as albedo. This is the whole
	// point: a surface that is lighter because it is chalkier is also rougher.
	float r = mix(rough_lo, rough_hi, nf);
	r = mix(r, rough_hi, cav * 0.7);
	r += (fine - 0.5) * 0.12;

	// --- WET. Rain is a material state, not a particle system.
	//   horizontals hold water; verticals shed it in runs that reach the bottom
	//   edge; both darken and both polish.
	float w = clamp(g_wet * wet_take, 0.0, 1.0);
	float pool = w * (0.35 + 0.65 * up * up);
	float runoff = 0.0;
	if (w > 0.02 && side > 0.03) {
		float rr = fbm2(vec2(wpos.x * 5.5 + wpos.z * 5.5, wpos.y * 0.55));
		runoff = smoothstep(0.42, 0.72, rr) * side * w;
	}
	float wetness = clamp(pool + runoff * 0.8, 0.0, 1.0);
	alb *= mix(1.0, 0.55, wetness);
	r = mix(r, 0.10, wetness * 0.88);

	// --- AMBIENT OCCLUSION from the height field's own cavities. 85 000 props
	// on a ground plane will hover without this; a crevice that does not darken
	// is the cheapest tell there is.
	float ao = 1.0 - 0.55 * cav - 0.22 * clamp(1.0 - nf * 1.6, 0.0, 1.0);

	ALBEDO = alb;
	ROUGHNESS = clamp(r, 0.04, 1.0);
	METALLIC = metal;
	SPECULAR = mix(0.5, 0.62, wetness);
	AO = clamp(ao, 0.25, 1.0);
	AO_LIGHT_AFFECT = 0.35;
	NORMAL = normalize((VIEW_MATRIX * vec4(n, 0.0)).xyz);
	if (emissive > 0.0) {
		EMISSION = base_col * COLOR.rgb * emissive;
	}
}
"""

## ---------------------------------------------------------------------------
## THE GROUND SHADER. The single biggest thing in the frame and the scale the
## designer's note is about, so it gets the expensive treatment.
const GROUND_SHADER := """
shader_type spatial;
// specular_disabled is load-bearing, and it took a day to find out why. A first
// person camera near the ground always sees the ground at 75-88 degrees of
// incidence, and Schlick Fresnel goes to 1 at grazing whatever F0 is. Under a
// full-hemisphere overcast sky that turns the entire site into a mirror of the
// sky. So the ground takes no engine specular at all and every reflection in it
// is hand written below against an analytic sky - which is also why a puddle can
// mirror the sky sharply while the concrete two centimetres away does not.
render_mode cull_back, diffuse_burley, specular_disabled;

uniform float slab = 3.6;              // hardstanding slab module, metres
uniform vec4 pad = vec4(-32.0, -26.0, 30.0, 26.0);
uniform vec4 pad2 = vec4(30.0, -10.0, 38.0, 10.0);
uniform vec2 hot_a = vec2(0.0, 0.0);   // the collar: the most worked ground
uniform vec2 hot_b = vec2(-19.0, -3.0);// the service bay
uniform int dbg = 0;
uniform vec3 sky_col : source_color = vec3(0.62, 0.66, 0.72);   // horizon
uniform vec3 sky_top : source_color = vec3(0.42, 0.48, 0.60);   // zenith
uniform vec3 sun_col : source_color = vec3(1.0, 1.0, 1.0);
uniform vec3 sun_dir = vec3(0.55, 0.72, -0.42);                 // toward the sun
uniform float pom_lod = 1.0;           // 0 kills POM (for the bench comparison)
uniform float pond_amp = 0.024;        // must match Ground.POND_AMP
uniform float nrm_lod = 1.0;           // 0 kills the detail and micro normals
global uniform float g_wet;

__NOISE__

varying vec3 wpos;
varying vec3 wnorm;
varying vec4 vcol;

void vertex() {
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	wnorm = normalize((MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz);
	vcol = COLOR;
}

// ---------------------------------------------------------------------------
// THE HEIGHT FIELD. Metres, zero at the finished surface, negative into it.
// Everything else in this shader is read off this one function, which is the
// only way albedo, roughness, normal, occlusion and standing water can agree.
//
//   hardstanding : slab joints -> arris -> cracks -> spalled patches ->
//                  exposed aggregate -> repaired patch edges
//   open ground  : gravel bed -> ruts along the routes -> mud
//
// `lod` 0 form only (POM march), 1 + aggregate and cracks, 2 + micro grain.
float ghf(vec2 p, float hard, float wear, int lod) {
	// --- slab joints, analytic, no noise. The joint has to be exactly on the
	// module the simulation uses or the chippings drawn into it miss it.
	vec2 gj = abs(fract(p / slab + 0.5) - 0.5) * slab;
	float jd = min(gj.x, gj.y);
	float joint = 1.0 - smoothstep(0.006, 0.026, jd);
	float arris = 1.0 - smoothstep(0.026, 0.058, jd);

	float hc = 0.0;
	float ho = 0.0;
	// BRANCHED ON `hard`, and it is worth about a third of this shader. The
	// hardstanding is a rectangle out of the plan, so the concrete branch and the
	// open-ground branch are coherent across whole screen tiles rather than
	// interleaved - and the parallax march runs this function up to sixteen times
	// a pixel, so computing the gravel bed underneath a concrete slab sixteen
	// times is the most expensive nothing in the file.
	if (hard > 0.02) {
		hc = -0.020 * joint - 0.0022 * arris;
		// slab-to-slab lippage: no two bays were poured level
		hc += (hash21(floor(p / slab)) - 0.5) * 0.010;
		// spalled and repaired patches. A repair sits proud, a spall is a hole.
		float m = fbm2(p * 0.42 + 31.0);
		hc -= 0.013 * smoothstep(0.60, 0.80, m);
		hc += 0.005 * smoothstep(0.62, 0.80, 1.0 - m);
		if (lod >= 1) {
			// cracks: voronoi ridges, hairline, only where the concrete has gone
			vec4 w1 = worley(p * 1.70);
			float crm = smoothstep(0.70, 0.94, fbm2(p * 0.22 + 7.0));
			hc -= 0.008 * crm * (1.0 - smoothstep(0.0010, 0.0085, (w1.y - w1.x) / 1.70));
		}
		if (lod >= 2) {
			// embedded aggregate. HALF BURIED: the stone is a sphere the concrete
			// has been worn back from, so it rises out of the surface and is cut
			// off by it, rather than sitting on top of it.
			vec4 w2 = worley(p * 44.0);
			float worn = smoothstep(0.56, 0.86, fbm2(p * 0.30 + 61.0));
			hc += 0.0080 * (1.0 - smoothstep(0.08, 0.55, w2.x))
				* mix(0.06, 1.0, max(worn, wear * 0.8));
			hc += (gnoise(p * 62.0) - 0.5) * 0.0028 + (gnoise(p * 190.0) - 0.5) * 0.0009;
		}
	}
	if (hard < 0.98) {
		// open ground: a gravel bed with ruts down the routes things take
		ho = 0.030 * (fbm2(p * 1.15) - 0.5);
		// ruts: stretched hard across the direction of travel, soft along it
		ho -= 0.055 * wear * smoothstep(0.35, 0.72, fbm2(vec2(p.x * 0.30, p.y * 2.60)));
		if (lod >= 1) {
			ho += 0.038 * (1.0 - smoothstep(0.10, 0.62, worley(p * 7.5).x));
		}
		if (lod >= 2) {
			ho += ((gnoise(p * 62.0) - 0.5) * 0.0028 + (gnoise(p * 190.0) - 0.5) * 0.0009) * 2.0;
		}
	}
	return mix(ho, hc, hard);
}

float in_rect(vec2 p, vec4 r, float feather) {
	vec2 d = max(r.xy - p, p - r.zw);
	return 1.0 - smoothstep(0.0, feather, max(d.x, d.y));
}

// An analytic overcast sky, for the one thing on this ground that is allowed a
// mirror. Cheap, and it means a puddle carries the sky's own gradient and its
// sun rather than a flat blue disc.
vec3 sky_of(vec3 d) {
	float t = clamp(d.y, 0.0, 1.0);
	vec3 c = mix(sky_col, sky_top, pow(t, 0.55));
	float s = clamp(dot(normalize(d), normalize(sun_dir)), 0.0, 1.0);
	c += sun_col * pow(s, 220.0) * 3.5;
	c += sun_col * pow(s, 8.0) * 0.10;
	return c;
}

void fragment() {
	vec2 p0 = wpos.xz;
	float dist = length(wpos - CAMERA_POSITION_WORLD);
	float hard = max(max(in_rect(p0, pad, 1.6), in_rect(p0, pad2, 1.6)), vcol.r * 0.85);
	float wear = clamp(vcol.b, 0.0, 1.0);
	float pondable = clamp(vcol.a, 0.0, 1.0);
	float flat_ = smoothstep(0.86, 0.985, wnorm.y);
	// EACH FREQUENCY GETS ITS OWN DISTANCE, and this is a correctness fix rather
	// than an optimisation. A 23 mm worley cell is four pixels at 10 m and two at
	// 20 m, and a two-pixel cell does not average, it ALIASES - it came back as
	// pale blotches crawling over the spoil tips that read exactly like snow.
	// Nyquist, not taste: every band is faded out before it reaches two pixels.
	float near_ = 1.0 - smoothstep(22.0, 38.0, dist);   // the coarse masks
	float near_a = 1.0 - smoothstep(6.0, 14.0, dist);   // 23 mm aggregate
	float near_s = 1.0 - smoothstep(14.0, 26.0, dist);  // 130 mm stones
	float near_f = 1.0 - smoothstep(8.0, 18.0, dist);   // 37 mm grain

	// --- PARALLAX OCCLUSION MAPPING.
	// A ground plane reads as a plane however good the shader on it is. This is
	// what buys apparent depth in the last four metres.
	//
	// Steps ramp down with distance and stop entirely at 18 m, where a 20 mm
	// joint is under a pixel and the march is buying nothing. The stride is
	// clamped so a grazing view cannot walk half a metre sideways per step, and
	// the march uses the CHEAP lod of the field - form only - because a 20 step
	// loop is the one place in this shader that cannot afford a worley.
	vec2 p = p0;
	float par_shadow = 0.0;
	int steps = 0;
	if (pom_lod > 0.5 && flat_ > 0.35) {
		// MEASURED: at 16/10/6/3 steps out to 18 m the march cost 5.4 ms of a
		// 19.8 ms frame, and almost all of that was the 9-18 m band, because that
		// band is most of the ground pixels in a standing shot and each of those
		// pixels was buying a joint two pixels wide. It runs to 9 m now.
		if (dist < 2.5) { steps = 14; }
		else if (dist < 5.0) { steps = 9; }
		else if (dist < 9.0) { steps = 5; }
	}
	if (steps > 0) {
		vec3 vd = normalize(wpos - CAMERA_POSITION_WORLD);
		float dn = max(-vd.y, 0.16);
		vec2 stride = vd.xz / dn;
		if (length(stride) > 5.0) { stride = normalize(stride) * 5.0; }
		float H = 0.055;                      // the deepest the field ever goes
		float dh = H / float(steps);
		float d = 0.0;
		float prev_d = 0.0;
		float prev_f = 0.0;
		for (int i = 0; i < steps; i++) {
			d += dh;
			float f = -ghf(p0 + stride * d, hard, wear, 0);
			if (f <= d) {
				float a = prev_f - prev_d;
				float b = f - d;
				float t = clamp(a / max(a - b, 0.0001), 0.0, 1.0);
				d = mix(prev_d, d, t);
				break;
			}
			prev_d = d; prev_f = f;
			if (i == steps - 1) { d = H; }
		}
		p = p0 + stride * d;
		par_shadow = clamp(d / H, 0.0, 1.0);
	}

	// --- THE HEIGHT FIELD, ONCE, AND THE NORMAL FROM IT.
	//
	// MEASURED, and it is the number that decided the shape of this shader:
	// evaluating the field four times per scale for central differences at three
	// separate scales - twelve evaluations - cost 9.5 ms of a 27 ms frame on the
	// ground alone. It is the same three scales now, but the SAMPLING SCALE
	// rides the distance instead of three separate passes riding it: `lodn` says
	// which scales are present in the field and `e` says how finely it is
	// sampled, and both ramp together. That is one evaluation and two forward
	// differences, and it is also more correct, because the epsilon now tracks
	// the pixel footprint instead of being fixed.
	//
	//   under 5 m   : form + cracks + aggregate + grain, sampled at 11 mm
	//   5 to 15 m   : form + cracks, sampled at 11 to 60 mm
	//   beyond 15 m : form only, sampled at 75 mm
	int lodn = dist < 5.0 ? 2 : (dist < 15.0 ? 1 : 0);
	float e = mix(0.011, 0.075, clamp(dist / 20.0, 0.0, 1.0));
	float h = ghf(p, hard, wear, lodn);
	vec3 n = wnorm;
	// Past 55 m the ground's own form is a metre of relief across a hundred
	// pixels: the mesh normal already carries it and the two gradient taps buy
	// nothing. This is aimed squarely at the worst frame in the benchmark, which
	// is the wide establishing view at each end of the loop.
	if (dist < 55.0) {
		float gx = (ghf(p + vec2(e, 0.0), hard, wear, lodn) - h) / e;
		float gz = (ghf(p + vec2(0.0, e), hard, wear, lodn) - h) / e;
		n = normalize(wnorm + vec3(-gx, 0.0, -gz) * 1.25);
	}

	// the third scale: 5 mm grain, its own epsilon, gone by 6.5 m because below
	// a pixel it is aliasing rather than detail
	float f_mic = 1.0 - smoothstep(2.0, 4.5, dist);
	if (f_mic > 0.004 && nrm_lod > 0.5) {
		float em = 0.0016;
		float g0 = gnoise(p * 190.0);
		vec2 gm = vec2(gnoise((p + vec2(em, 0.0)) * 190.0) - g0,
		               gnoise((p + vec2(0.0, em)) * 190.0) - g0);
		n = normalize(n + vec3(-gm.x, 0.0, -gm.y) * (1.55 * f_mic));
	}

	// --- the surface facts, all off the world position and the plan
	float mud = max(smoothstep(0.55, 3.2, wpos.y) * 0.9, vcol.g);
	float traffic = clamp(max(wear, max(1.0 - length(p - hot_a) / 17.0,
		1.0 - length(p - hot_b) / 13.0)), 0.0, 1.0);

	float grit = fbm2(p * 3.2);
	float broad = fbm2(p * 0.20 + 3.0);
	float fine = near_f > 0.01 ? mix(0.5, fbm2(p * 27.0), near_f) : 0.5;
	float m = near_ > 0.01 ? fbm2(p * 0.42 + 31.0) : 0.5;
	float spall = smoothstep(0.60, 0.80, m) * near_;
	float patch = smoothstep(0.62, 0.80, 1.0 - m) * near_;
	vec2 gj = abs(fract(p / slab + 0.5) - 0.5) * slab;
	float jd = min(gj.x, gj.y);
	float joint = 1.0 - smoothstep(0.006, 0.026, jd);

	vec3 alb = vec3(0.0);
	float r = 0.9;
	if (hard > 0.02) {
		// ---------------- CONCRETE HARDSTANDING
		// Weathered concrete is 0.22-0.30 linear. It only gets dark here because
		// something happened to it - oil, rubber, tracked mud, standing water -
		// and every one of those is a different colour AND a different gloss.
		vec3 conc = vec3(0.240, 0.231, 0.215) * mix(0.70, 1.16, broad)
			* mix(0.66, 1.18, grit) * mix(0.84, 1.16, fine);
		float rc = mix(0.74, 0.96, grit) * mix(0.92, 1.05, broad);

		// a repaired bay is a different pour: greyer, smoother, and it shows
		conc = mix(conc, vec3(0.196, 0.196, 0.192), patch * 0.7);
		rc = mix(rc, 0.66, patch * 0.6);

		if (near_a > 0.01) {
			// exposed aggregate, where the float finish has actually gone
			vec4 wa = worley(p * 44.0);
			float worn = smoothstep(0.56, 0.86, fbm2(p * 0.30 + 61.0));
			float agg = (1.0 - smoothstep(0.08, 0.55, wa.x))
				* mix(0.06, 1.0, max(max(spall, worn), traffic * 0.8)) * near_a;
			conc = mix(conc, vec3(0.214, 0.192, 0.160) * mix(0.68, 1.34, hash21(floor(p * 44.0))), agg * 0.45);
			rc = mix(rc, 0.96, agg * 0.7);
			// cracks: hairlines, and only where the mask says the slab has gone
			vec4 w1 = worley(p * 1.70);
			float crm = smoothstep(0.70, 0.94, fbm2(p * 0.22 + 7.0));
			float crack = crm * (1.0 - smoothstep(0.0010, 0.0085, (w1.y - w1.x) / 1.70)) * near_;
			crack = crack;
			conc = mix(conc, vec3(0.030, 0.027, 0.024), crack * 0.82);
			rc = mix(rc, 0.55, crack * 0.35);
		}
		// joints: what is in them is dirt, not concrete
		conc = mix(conc, vec3(0.038, 0.034, 0.030), joint * 0.90);
		rc = mix(rc, 0.55, joint * 0.35);

		// oil. Soaked in, so it is dark AND smooth - a matte dark patch reads as
		// paint, and paint is not what happens under a machine.
		float oil = near_ > 0.01
			? smoothstep(0.56, 0.82, fbm2(p * 1.10 + 17.0)) * clamp(traffic + 0.34, 0.0, 1.0) * near_
			: 0.0;
		conc = mix(conc, vec3(0.022, 0.020, 0.019), oil * 0.92);
		rc = mix(rc, 0.30, oil * 0.75);

		// rubber and tracked mud. Mud is DRAGGED: heavy where the yard meets the
		// concrete, thinning inward along the routes things take.
		float edge_mud = clamp(1.0 - in_rect(p, pad, 7.0), 0.0, 1.0);
		float trk = near_ > 0.01
			? smoothstep(0.36, 0.80, fbm2(p * 1.05 + 91.0)) * clamp(traffic * 0.8 + edge_mud, 0.0, 1.0)
			: 0.0;
		conc = mix(conc, vec3(0.086, 0.062, 0.040), trk * 0.80);
		rc = mix(rc, 0.98, trk * 0.6);
		alb = conc;
		r = rc;
	}
	if (hard < 0.98) {
		// ---------------- OPEN GROUND
		vec3 soil = vec3(0.098, 0.074, 0.050) * mix(0.62, 1.42, grit) * mix(0.86, 1.16, fine);
		float rs = mix(0.92, 1.0, grit);
		if (near_s > 0.01) {
			vec4 w3 = worley(p * 7.5);
			float stone = (1.0 - smoothstep(0.10, 0.62, w3.x)) * near_s;
			soil = mix(soil, vec3(0.148, 0.126, 0.096) * mix(0.78, 1.16, hash21(floor(p * 7.5))), stone * 0.55);
			rs -= stone * 0.06;
		}
		soil = mix(soil, vec3(0.048, 0.039, 0.032), clamp(mud, 0.0, 0.95));
		soil = mix(soil, vec3(0.072, 0.052, 0.034), traffic * 0.55);
		alb = mix(soil, alb, hard);
		r = mix(rs, r, hard);
	}

	// ---------------- STANDING WATER
	// Water finds a LEVEL. `pondable * pond_amp` is the mesh's own shallow dish,
	// straight out of vertex colour; `h` is this shader's micro relief; `drain`
	// is how much of it has run off, which is the one thing rain changes. The
	// puddle's edge is wherever the two cross - which is why it wraps round the
	// aggregate, fills the joints first, and grows when it rains without a
	// single puddle shape being authored anywhere.
	float drain = mix(0.0208, 0.0122, g_wet);
	float depth = pondable * pond_amp - h - drain;
	float water = smoothstep(0.0, 0.0040, depth) * flat_;
	float damp = smoothstep(-0.0075, 0.0006, depth) * flat_;
	alb *= mix(1.0, 0.66, clamp(damp - water, 0.0, 1.0));
	r = mix(r, r * 0.72, clamp(damp - water, 0.0, 1.0));
	if (water > 0.001) {
		vec3 bed = alb * mix(0.42, 0.15, clamp(depth * 60.0, 0.0, 1.0));
		bed = mix(bed, vec3(dot(bed, vec3(0.34, 0.42, 0.24))), 0.40);
		bed = mix(bed, bed * vec3(1.10, 0.94, 0.76), 0.6);
		alb = mix(alb, bed, water);
		r = mix(r, 0.045, water);
		// the water surface is LEVEL. Flattening the normal here is the single
		// detail that makes a puddle read as water rather than as a dark stain.
		n = normalize(mix(n, vec3(0.0, 1.0, 0.0), water * 0.94));
		if (g_wet > 0.55) {
			vec2 rip = vec2(fbm2(p * 55.0 + TIME * 1.7), fbm2(p * 55.0 + 4.0 + TIME * 1.7)) - 0.5;
			n = normalize(n + vec3(rip.x, 0.0, rip.y) * 0.35 * water);
		}
	}

	// general wetting, short of a puddle: darker albedo, lower roughness
	float sheen = clamp(g_wet * (0.35 + 0.65 * flat_), 0.0, 1.0);
	alb *= mix(1.0, 0.62, sheen * 0.85);
	r = mix(r, max(r * 0.45, 0.14), sheen * 0.8);

	// ---------------- OCCLUSION
	// Cavity from the field: joints, cracks, the shadow side of every stone.
	// This is what stops a chipping lying on a bright plane like a sticker.
	float ao = clamp(1.0 + h * 7.0, 0.44, 1.0);
	ao *= 1.0 - 0.22 * par_shadow * clamp(1.0 - dist / 12.0, 0.0, 1.0);
	ao = mix(1.0, ao, 0.9);

	// ---------------- the hand-written reflection
	// Dry ground gets a roughness-attenuated Fresnel that cannot wash out at
	// grazing; water gets a real mirror of the analytic sky. F0 for water is
	// 0.02, which is why a puddle is dark from above and a mirror from the side.
	vec3 V = normalize(CAMERA_POSITION_WORLD - wpos);
	float ndv = clamp(dot(n, V), 0.0, 1.0);
	float F = 0.02 + 0.98 * pow(1.0 - ndv, 5.0);
	float gloss = pow(1.0 - clamp(r, 0.0, 1.0), 2.2);
	vec3 spec = sky_of(reflect(-V, n)) * F * gloss;
	// a wet surface also carries a broad sheen from the whole sky, not only the
	// mirror direction: the film is rough. That is what reads as "wet" at the
	// angle a standing camera actually looks at the ground from.
	vec3 skyavg = mix(sky_col, sky_top, 0.5);
	spec += skyavg * (0.105 * water + 0.038 * sheen * flat_);

	ALBEDO = alb;
	ROUGHNESS = clamp(r, 0.04, 1.0);
	METALLIC = 0.0;
	AO = ao;
	AO_LIGHT_AFFECT = 0.28;
	NORMAL = normalize((VIEW_MATRIX * vec4(n, 0.0)).xyz);
	EMISSION = spec * mix(0.55, 1.0, water) * ao;

	if (dbg == 1) { ALBEDO = vec3(hard, mud, traffic); ROUGHNESS = 1.0; EMISSION = vec3(0.0); }
	if (dbg == 2 || dbg == 3) { ALBEDO = vec3(0.4); ROUGHNESS = 1.0; EMISSION = vec3(0.0); }
	if (dbg == 5) { ALBEDO = vec3(0.5); ROUGHNESS = 1.0; EMISSION = vec3(0.0); }
	if (dbg == 6) { ALBEDO = vec3(water, pondable, clamp(depth * 60.0, 0.0, 1.0)); ROUGHNESS = 1.0; EMISSION = vec3(0.0); }
	if (dbg == 7) { ALBEDO = vec3(0.0); ROUGHNESS = 1.0; EMISSION = vec3(1.0, 0.0, 0.6); }
	if (dbg == 17) { ALBEDO = vec3(0.5); ROUGHNESS = 1.0; EMISSION = vec3(0.0); }
}
"""

static var _shader_solid: Shader
static var _shader_ground: Shader
static var _cache: Dictionary = {}
static var _grounds: Array = []

static func solid_shader() -> Shader:
	if _shader_solid == null:
		_shader_solid = Shader.new()
		_shader_solid.code = SOLID_SHADER.replace("__NOISE__", NOISE)
	return _shader_solid

static func ground_shader() -> Shader:
	if _shader_ground == null:
		_shader_ground = Shader.new()
		_shader_ground.code = GROUND_SHADER.replace("__NOISE__", NOISE)
	return _shader_ground

static func ground_material(L: SurfaceLayout) -> ShaderMaterial:
	var m := ShaderMaterial.new()
	m.shader = ground_shader()
	var p0: Dictionary = L.plan["pads"][0]
	var p1: Dictionary = L.plan["pads"][1]
	m.set_shader_parameter("pad", Vector4(float(p0["x0"]) / 1000.0, float(p0["z0"]) / 1000.0,
		float(p0["x1"]) / 1000.0, float(p0["z1"]) / 1000.0))
	m.set_shader_parameter("pad2", Vector4(float(p1["x0"]) / 1000.0, float(p1["z0"]) / 1000.0,
		float(p1["x1"]) / 1000.0, float(p1["z1"]) / 1000.0))
	m.set_shader_parameter("slab", float(L.plan["slab_module"]) / 1000.0)
	m.set_shader_parameter("hot_a", Vector2(0.0, 0.0))
	var bay: Dictionary = {}
	for b in L.plan["buildings"]:
		if b["kind"] == "service_bay":
			bay = b
	if not bay.is_empty():
		m.set_shader_parameter("hot_b", Vector2((float(bay["x0"]) + float(bay["x1"])) / 2000.0,
			(float(bay["z0"]) + float(bay["z1"])) / 2000.0))
	_grounds.append(m)
	return m

static func grounds() -> Array:
	return _grounds

## The palette. Every entry names which register it belongs to:
##   old  = THE INHERITED, the hellscape: corroded, riveted, timbered, stained
##   new  = THE BROUGHT, the future: manufactured, modular, clean-edged, labelled
##
## PHOTOREAL PASS. Three rules applied to every row:
##   1. albedo is a measured linear reflectance, not a value that looked right
##   2. the roughness BAND is wide - a single roughness is the strongest tell
##      that a surface was authored rather than weathered
##   3. metallic is 0 or 1. `galv` and `alu` were 0.72 and 0.90, which is not a
##      material, and their albedo is now the metal's F0 rather than a diffuse.
##
## Columns: base_col, rough_lo, rough_hi, metal, grain, streak, noise_scale,
##          dirt, relief, pit
static func get_mat(id: String) -> ShaderMaterial:
	if _cache.has(id):
		return _cache[id]
	var m := ShaderMaterial.new()
	m.shader = solid_shader()
	var P := {
		# ---------------- THE INHERITED
		# Rusted steel measures 0.10-0.26 linear. Iron was 0.065 luminance, which
		# is wet coal, not rust. The pitting term is what makes it read as scale.
		"iron":     [Vector3(0.150, 0.079, 0.041), 0.62, 0.97, 0.0, 1.05, 0.95, 2.6, 0.26, 1.30, 0.85],
		"iron_pale":[Vector3(0.205, 0.116, 0.062), 0.58, 0.94, 0.0, 1.00, 0.85, 2.2, 0.30, 1.20, 0.70],
		# "still in use is polished bright by the work itself" - real steel, F0
		"steel":    [Vector3(0.560, 0.560, 0.570), 0.17, 0.42, 1.0, 0.30, 0.0, 4.0, 0.10, 0.55, 0.15],
		"stone":    [Vector3(0.208, 0.190, 0.158), 0.72, 0.98, 0.0, 0.95, 0.45, 2.4, 0.34, 1.60, 0.45],
		"timber":   [Vector3(0.128, 0.092, 0.058), 0.70, 0.97, 0.0, 0.90, 0.30, 5.0, 0.32, 1.45, 0.20],
		"rock":     [Vector3(0.190, 0.150, 0.104), 0.78, 0.99, 0.0, 1.00, 0.10, 3.0, 0.25, 1.70, 0.30],
		"brick":    [Vector3(0.152, 0.092, 0.062), 0.68, 0.96, 0.0, 0.90, 0.65, 7.0, 0.34, 1.35, 0.35],
		# ---------------- THE BROUGHT
		# BONE was 0.887 linear, which is fresh laboratory white. A shell that has
		# been in this yard a season is 0.55-0.65 and it is not uniform.
		"bone":     [Vector3(0.620, 0.566, 0.482), 0.26, 0.56, 0.0, 0.34, 0.0, 4.0, 0.30, 0.45, 0.0],
		"kitgrey":  [Vector3(0.198, 0.206, 0.216), 0.28, 0.58, 0.0, 0.30, 0.0, 4.0, 0.24, 0.45, 0.0],
		# galvanised steel and aluminium are METAL. Their albedo is F0.
		"galv":     [Vector3(0.560, 0.575, 0.585), 0.38, 0.70, 1.0, 0.32, 0.0, 5.0, 0.20, 0.60, 0.10],
		"alu":      [Vector3(0.910, 0.915, 0.920), 0.22, 0.48, 1.0, 0.20, 0.0, 5.0, 0.14, 0.40, 0.0],
		"ember":    [Vector3(0.300, 0.148, 0.062), 0.32, 0.62, 0.0, 0.30, 0.0, 4.0, 0.22, 0.50, 0.0],
		"rubber":   [Vector3(0.042, 0.042, 0.044), 0.55, 0.86, 0.0, 0.35, 0.0, 6.0, 0.30, 0.60, 0.0],
		"plastic":  [Vector3(0.132, 0.138, 0.130), 0.32, 0.64, 0.0, 0.32, 0.0, 6.0, 0.28, 0.35, 0.0],
		"amber":    [Vector3(0.480, 0.302, 0.108), 0.34, 0.64, 0.0, 0.26, 0.0, 6.0, 0.18, 0.40, 0.0],
		"screen":   [Vector3(0.032, 0.036, 0.041), 0.06, 0.18, 0.0, 0.10, 0.0, 8.0, 0.05, 0.10, 0.0],
		"glass":    [Vector3(0.050, 0.053, 0.058), 0.04, 0.14, 0.0, 0.08, 0.0, 8.0, 0.05, 0.10, 0.0],
		# ---------------- scatter and growth
		"weed":     [Vector3(0.072, 0.086, 0.038), 0.62, 0.96, 0.0, 0.60, 0.0, 3.0, 0.10, 0.70, 0.0],
		"gravel":   [Vector3(0.166, 0.146, 0.116), 0.72, 0.99, 0.0, 0.80, 0.0, 12.0, 0.22, 1.90, 0.25],
		"litter":   [Vector3(0.270, 0.268, 0.256), 0.38, 0.80, 0.0, 0.60, 0.0, 9.0, 0.35, 0.45, 0.0],
		"water":    [Vector3(0.026, 0.032, 0.036), 0.02, 0.07, 0.0, 0.12, 0.0, 3.0, 0.0, 0.10, 0.0],
	}
	if not P.has(id):
		push_error("Mats: unknown material " + id)
		id = "iron"
	var e: Array = P[id]
	var c: Vector3 = e[0]
	m.set_shader_parameter("base_col", Color(c.x, c.y, c.z))
	m.set_shader_parameter("rough_lo", e[1])
	m.set_shader_parameter("rough_hi", e[2])
	m.set_shader_parameter("metal", e[3])
	m.set_shader_parameter("grain", e[4])
	m.set_shader_parameter("streak", e[5])
	m.set_shader_parameter("noise_scale", e[6])
	m.set_shader_parameter("dirt", e[7])
	m.set_shader_parameter("relief", e[8])
	m.set_shader_parameter("pit", e[9])
	m.set_shader_parameter("streak_col", Color(0.148, 0.062, 0.024))
	m.set_shader_parameter("dirt_col", Color(0.120, 0.100, 0.074))
	m.set_shader_parameter("wet_take", 1.0 if id != "water" else 0.0)
	m.set_shader_parameter("emissive", 0.0)
	_cache[id] = m
	return m

## Emissive fittings, in the palette entry's own colour. ART-DIRECTION: nothing
## in the world is ever cyan; red is lethal only; identity emissives at strength
## <= 3 and area over intensity.
static func emissive_of(id: String, strength: float) -> ShaderMaterial:
	var key := "E:" + id
	if _cache.has(key):
		return _cache[key]
	var base := get_mat(id)
	var m := ShaderMaterial.new()
	m.shader = solid_shader()
	for p in ["base_col", "rough_lo", "rough_hi", "metal", "grain", "streak",
			"noise_scale", "dirt", "streak_col", "dirt_col", "wet_take", "relief", "pit"]:
		m.set_shader_parameter(p, base.get_shader_parameter(p))
	m.set_shader_parameter("grain", 0.06)
	m.set_shader_parameter("dirt", 0.05)
	m.set_shader_parameter("relief", 0.15)
	m.set_shader_parameter("pit", 0.0)
	m.set_shader_parameter("emissive", strength)
	_cache[key] = m
	return m
