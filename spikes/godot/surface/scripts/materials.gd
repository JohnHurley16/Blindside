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
## SNOW. Pasted into the ground shader and the valley shader the same way NOISE
## is, because a Godot shader has no include and the two must not disagree.
##
## THE FAILURE CASE, stated first because it is the only thing that matters:
## snow rendered badly is white plastic, every time, and the cause is never the
## albedo. Four things cause it.
##
##  1. SNOW IS TRANSLUCENT. A photon enters, scatters through a few centimetres
##     of ice grains and trapped air, and leaves somewhere else. So a hollow in
##     snow is FILLED with light rather than dark, and the shadow terminator is
##     wide, soft and coloured. Ambient occlusion at rock strength is the
##     fastest possible way to turn snow into plaster; the fix is not less AO,
##     it is an occlusion term that goes BLUE and STAYS BRIGHT as it deepens.
##  2. ITS SPECULAR IS FACETED, NOT ROUGH. A wind crust is a field of ice facets
##     a millimetre across. It GLITTERS - sparse, hard, violently view-dependent
##     highlights that no roughness value on earth produces. This is the single
##     detail that most says "snow" in a still frame and it is the one a
##     roughness-and-albedo material system cannot express.
##  3. WIND SCULPTS IT. Sastrugi, ripples, a scoured windward face and a drift
##     tail behind everything. Undisturbed snow is strongly ANISOTROPIC, and
##     isotropic noise on it reads as porridge. Every band below is stretched
##     along `snow_wind`.
##  4. IT IS NOT WHITE, HERE. THE-ICE 2.6: 0.80 linear under a tenth of full sun
##     is no brighter than the yard's concrete was under overcast. And THE-ICE
##     6.1: the blue is PATH LENGTH, not a tint - "implemented as depth-of-medium
##     rather than as an albedo, it satisfies the no-hue-axis rule honestly".
##     So the albedo is achromatic and every blue in this block is a function of
##     how far into the snow the light went.
const SNOW := """
// THE PREVAILING WIND, and it does two jobs that pull in different directions.
// Down the valley (+x) is where a katabatic wind actually goes, and it is what
// the drifts on the floor want. But `sn_plaster` only whitens a face that looks
// INTO the wind, and every face of the town looks -z across the valley, so a
// purely axial wind leaves the whole settlement bare while the ground beside it
// is loaded. 0.80/0.60 is mostly down-valley with enough cross-valley component
// to pack the far wall, which is also what a wind funnelling round a 1,800 m
// ridge does. One vector, two effects, and it is the same one everywhere.
uniform vec2 snow_wind = vec2(0.80, 0.60);      // prevailing wind, world XZ
uniform float snow_alb = 0.795;                 // linear. fresh 0.85, settled 0.75
// THE-ICE 2.6 is the constraint and it is about SATURATION, not hue: "nothing in
// the world may use belief's saturation at belief's brightness". SENSED is
// #63D6F7 - saturated, bright cyan. This is 0.80/0.875/1.00 on an 0.795 base:
// high value, very low saturation, and it only appears where the light went a
// long way in. The first take had it at 0.62/0.755/1.00 applied at an average
// cavity of 0.5 - i.e. everywhere - and the whole valley came back the colour of
// a sensor return. That is exactly the failure THE-ICE names.
uniform vec3 snow_deep : source_color = vec3(0.800, 0.875, 1.00);
uniform float snow_sss = 0.55;
uniform float snow_glit = 1.0;
global uniform float g_snow;

// the wind frame: x along the wind, y across it
vec2 sn_ax(vec2 p) { return vec2(dot(p, snow_wind), dot(p, vec2(-snow_wind.y, snow_wind.x))); }

// The snow surface, metres above the ground it lies on. Everything is stretched
// 3:1 to 6:1 along the wind, which is what makes it snow and not stucco.
//   lod 0 : drift form only  (the parallax march, and anything past 30 m)
//   lod 1 : + sastrugi and ripples
//   lod 2 : + crust grain
float snowf(vec2 p, int lod) {
	vec2 q = sn_ax(p);
	float h = (fbm2(vec2(q.x * 0.052, q.y * 0.150)) - 0.5) * 0.74;
	h += (fbm2(vec2(q.x * 0.190, q.y * 0.560) + 7.0) - 0.5) * 0.230;
	if (lod >= 1) {
		// sastrugi: hard ridges ACROSS the wind with a scour cut behind each.
		// MEASURED BY EYE AND RAISED TWICE: on a floor lit only by the sky there
		// is no shadow to reveal form, so the relief IS the whole read and a
		// physically modest amplitude photographs as a flat sheet. Real sastrugi
		// run 5-30 cm; this is at the top of that and it is still not much.
		float s = fbm2(vec2(q.x * 0.95, q.y * 5.6) + 21.0);
		h += (s - 0.5) * 0.135;
		h -= 0.052 * smoothstep(0.54, 0.88, s);
		h += (gnoise(vec2(q.x * 2.9, q.y * 14.0)) - 0.5) * 0.030;
		h += (gnoise(vec2(q.x * 7.4, q.y * 31.0) + 3.0) - 0.5) * 0.012;
	}
	if (lod >= 2) {
		// 168/m is a 6 mm cell, and the forward difference that reads it uses an
		// epsilon of 10 mm - so it samples a cell and a half per tap and returns
		// noise rather than a gradient. It came back as a regular cross-weave
		// over the whole snowfield: not sparkle, not grain, FABRIC. This is the
		// same Nyquist argument the ground shader already makes about aggregate,
		// and the fix is the same: do not carry a band you cannot sample.
		h += (gnoise(q * 38.0) - 0.5) * 0.0042 + (gnoise(q * 96.0) - 0.5) * 0.0011;
	}
	return h;
}

// GLITTER. A sparse lattice of ice facets, each with its own tilted normal.
// A facet lights up when its reflection happens to point at something bright,
// which is why real snow sparkles at YOU and not at the camera beside you.
// Faded by the pixel footprint: a facet under a pixel is aliasing, not sparkle,
// which is the same Nyquist argument the ground shader makes about aggregate.
float sn_facet(vec2 p, vec3 n, vec3 v, vec3 towards, float fade) {
	if (fade < 0.02 || snow_glit < 0.01) { return 0.0; }
	vec2 c = floor(p * 560.0);
	float r1 = hash21(c);
	if (r1 < 0.942) { return 0.0; }
	vec2 j = hash22(c + 3.17);
	vec3 fn = normalize(n + vec3(j.x, 0.28 * (r1 - 0.96) * 40.0, j.y) * 0.62);
	vec3 hv = normalize(v + towards);
	return pow(max(dot(fn, hv), 0.0), 720.0) * fade * snow_glit;
}

// The snow's own colour, given how deep into it we are looking. `cav` is 0 on a
// crest and 1 in the bottom of a hollow. THE-ICE 6.1's rule made literal: one
// achromatic material, and the distance the light travelled does the work.
vec3 sn_col(float cav, float wet) {
	vec3 c = vec3(snow_alb) * mix(1.0, 0.90, wet);
	// deeper == longer path == bluer AND (this is the part that is always got
	// wrong) not much darker. Snow in a hollow is a different HUE from snow on
	// a crest, and only a little lower in value.
	//
	// `cav` MUST be zero on open ground. It is a hollow detector, not a shade,
	// and every caller derives it as sn_cav() below rather than by hand.
	return mix(c, c * snow_deep * 1.02, clamp(cav, 0.0, 1.0) * 0.62);
}

// The hollow detector. 0 on a crest and on flat ground; 1 only where the surface
// has actually gone down. Getting this wrong is the difference between snow and
// a blue sheet, so it exists once and everything calls it.
float sn_cav(float field) { return clamp(-field * 5.5, 0.0, 1.0); }
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
uniform float snow_take = 1.0;      // how much snow this material collects
// THIS MATERIAL *IS* SNOW, rather than being a thing with snow on it.
//
// ACT-ONE 8.2: "scatter.gd::_drift instances a rock mesh with the snow material,
// and the snow material is shaded from WORLD POSITION. So a drift's own crust,
// sastrugi and wind grain line up exactly with the ground's underneath it, and
// on open snow the result reads as a TRANSLUCENT FACETED SHEET lying on the
// ground rather than as a bank of snow." Correct diagnosis, and its own fix:
// "a per-instance offset into the noise field, not a new mesh."
//
// There is no per-instance custom data channel in this batcher, and adding one
// would touch every bin. It is not needed: MODEL_MATRIX's own origin is unique
// per instance and is already in the vertex shader, so hashing it gives every
// drift its own place in the same field for one hash and one varying.
//
// It does the second half too. A drift's SIDES face sideways, so the up-facing
// cap misses them and only the wind plaster catches them - which is the other
// reason they read as sheets. A bank of snow is snow all over.
uniform float snow_body = 0.0;
global uniform float g_wet;

__NOISE__
__SNOW__

varying vec3 wpos;
varying vec3 wnorm;
varying vec2 snowp;

void vertex() {
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	wnorm = normalize((MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz);
	snowp = wpos.xz + snow_body
		* (hash22(floor(MODEL_MATRIX[3].xz * 2.7) + 0.5) - 0.5) * 840.0;
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

	// --- SNOW ON EVERYTHING THAT FACES UP.
	// THE-ICE 7.4: "the slope term already exists ... snow on up-facing surfaces
	// is the dirt term with a different colour and a harder threshold, and that
	// is genuinely close to free." It is, and it is the highest-value cheap
	// change in the whole pass: fifty-one thousand props get a snow cap for two
	// dozen lines and one global uniform.
	//
	// Three things stop it reading as paint. It is HARD-EDGED, because snow
	// either lies or it does not and the boundary is a line rather than a
	// gradient. It is BROKEN UP at the margin by a noise field, because snow
	// blows off a narrow member and stays on a wide one. And it carries the same
	// blue-in-the-hollow rule as the ground, because it is the same snow.
	float snowc = 0.0;
	if (g_snow > 0.01 && snow_take > 0.01) {
		if (up > 0.16) {
			snowc = smoothstep(0.30, 0.62, up);
			float br = fbm2(q * 1.9 + 53.0);
			snowc *= smoothstep(0.14, 0.52, br + up * 0.42);
		}
		// WIND PLASTER, and it is the thing that stops a snowy yard being a
		// white floor with black objects standing on it. Snow does not only
		// LIE, it STICKS: driven snow packs onto the windward face of anything
		// vertical and stays there, so a fence, a container and a headframe leg
		// are all half white on one side and black on the other. It costs one
		// dot product against the same `snow_wind` the drifts use, and it is
		// worth more to this frame than the horizontal cap is.
		// MEASURED BY EYE AND RAISED: at wind-squared x 0.72 a fence panel came
		// back with 8% coverage, i.e. none, and the yard stayed a white floor
		// with black objects on it. Driven snow packs HARD onto a windward face
		// and this is the term that keeps the pit-head's iron in the same
		// picture as the ground it stands on.
		float wind = clamp(-dot(normalize(wnorm.xz + vec2(1e-5)), snow_wind), 0.0, 1.0);
		// MEASURED BY EYE AND HALVED, TWICE. At 1.15 the containers came back
		// ninety per cent white and the yard lost the thing it is FOR:
		// DESIGN-PRINCIPLES 4's two registers, the old iron and the brought kit,
		// which are a VALUE contrast before they are anything else. Burying both
		// under the same white is the snow equivalent of the scatter mistake -
		// uniform cover, and uniform cover is always the tell.
		//
		// And it has to RUN, not coat. Driven snow packs into the lee of every
		// rib and corner and streaks DOWNWARD from it, so the term is stretched
		// along world Y exactly the way the rust streak above it is, and for the
		// same reason: gravity, not noise. That is what makes it read as
		// something that happened to the object rather than as a coat of paint.
		float plaster = wind * (1.0 - abs(up)) * 0.62;
		float run_s = fbm2(vec2(wpos.x * 2.4 + wpos.z * 2.4, wpos.y * 0.42));
		plaster *= smoothstep(0.34, 0.86, run_s * 0.72 + wind * 0.42);
		snowc = clamp(max(snowc, plaster) * g_snow * snow_take, 0.0, 1.0);
		// and a drift is snow all the way round, not a rock wearing a hat
		snowc = max(snowc, snow_body * clamp(g_snow, 0.0, 1.0) * 0.96);
	}
	float metalq = metal;
	if (snowc > 0.004) {
		float sh = snowf(snowp, dist < 9.0 ? 2 : (dist < 36.0 ? 1 : 0));
		float scav = sn_cav(sh);
		alb = mix(alb, sn_col(scav, clamp(g_wet, 0.0, 1.0)), snowc);
		r = mix(r, mix(0.44, 0.80, scav), snowc);
		metalq = mix(metalq, 0.0, snowc);
		wetness *= 1.0 - snowc * 0.85;
		// a lying drift has its own micro form, and that is what stops the cap
		// reading as a decal painted on the top face of a box
		if (dist < 22.0) {
			float es = 0.010;
			float s0 = snowf(snowp, 1);
			vec2 gs = vec2(snowf(snowp + vec2(es, 0.0), 1) - s0,
			               snowf(snowp + vec2(0.0, es), 1) - s0) / es;
			n = normalize(mix(n, normalize(vec3(-gs.x, 1.0, -gs.y)), snowc * 0.80));
		}
	}

	// --- AMBIENT OCCLUSION from the height field's own cavities. 85 000 props
	// on a ground plane will hover without this; a crevice that does not darken
	// is the cheapest tell there is.
	float ao = 1.0 - 0.55 * cav - 0.22 * clamp(1.0 - nf * 1.6, 0.0, 1.0);
	// ...but not under snow. A hollow in snow is FILLED with scattered light,
	// so it changes hue rather than value. Occlusion at rock strength is what
	// makes rendered snow read as plaster and this one line is the fix.
	ao = mix(ao, mix(ao, 1.0, 0.45), snowc);

	ALBEDO = alb;
	ROUGHNESS = clamp(r, 0.04, 1.0);
	METALLIC = metalq;
	SPECULAR = mix(mix(0.5, 0.62, wetness), 0.42, snowc);
	AO = clamp(ao, 0.25, 1.0);
	AO_LIGHT_AFFECT = mix(0.35, 0.10, snowc);
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

// ---------------------------------------------------------------------------
// WHAT WALKED ON IT. `tracks.gd` owns both of these and its header explains the
// encoding; this is the read side.
//
//   trk_print  NEAREST, and it must be. It does not hold a picture of a print,
//              it holds the print's IDENTITY - centre to 0.8 mm in RG, foot
//              yaw in B, depth in A - and filtering an identity averages two
//              different prints into a third that never happened.
//   trk_pack   LINEAR. Three saturating counters: compaction, refreeze, dirt.
//   trk_win    (x0, z0, 1/span, print texels per edge)
uniform sampler2D trk_print : filter_nearest, repeat_disable, hint_default_black;
uniform sampler2D trk_pack : filter_linear, repeat_disable, hint_default_black;
uniform vec4 trk_win = vec4(-95.0, -104.0, 0.004807692, 1024.0);
uniform vec2 trk_foot = vec2(0.066, 0.052);   // print half-extents: along, across
uniform float trk_rim = 0.062;                // how far the displaced snow reaches
uniform float trk_far = 17.0;                 // past this, prints are the field

__NOISE__
__SNOW__

varying vec3 wpos;
varying vec3 wnorm;
varying vec4 vcol;
varying vec2 vfloor;                   // UV2: (braid plain, glacier ice)

void vertex() {
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	wnorm = normalize((MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz);
	vcol = COLOR;
	vfloor = UV2;
}

// ---------------------------------------------------------------------------
// THE PRINTS, REBUILT.
//
// Nine texelFetches, gated to the distance at which a 130 mm print is more than
// a couple of pixels. The buffer gives the centre, the yaw and the depth; the
// SHAPE is evaluated here, so the print has a 1 mm edge off a 203 mm texel and
// the buffer's own resolution never appears in the picture.
//
// A ball foot punches a rounded hole and pushes what was in it out into a rim
// around the lip. THE RIM IS NOT DECORATION. On a valley floor lit only by the
// sky there is no sun to cast a shadow into a hollow, so a depression alone is
// nearly invisible - what actually reads is the rim, because it is the one part
// of a footprint with a surface tilted enough to catch the bright part of the
// sky. The first version had no rim and the prints read as grey smudges.
//
// Returns (dh, dh/dx, dh/dz, packed), the height added to the snow surface and
// its ANALYTIC gradient. Differencing this would cost eighteen more fetches per
// pixel and is not necessary: the primitive is known, so its derivative is too.
vec4 trk_prints(vec2 p) {
	float tex = 1.0 / (trk_win.z * trk_win.w);            // metres a texel
	vec2 tc = (p - trk_win.xy) * trk_win.z * trk_win.w;   // position in texels
	vec2 fl = floor(tc);
	vec4 acc = vec4(0.0);
	for (int j = -1; j <= 1; j++) {
		for (int i = -1; i <= 1; i++) {
			vec2 c = fl + vec2(float(i), float(j));
			if (c.x < 0.0 || c.y < 0.0 || c.x >= trk_win.w || c.y >= trk_win.w) { continue; }
			vec4 s = texelFetch(trk_print, ivec2(c), 0);
			if (s.a < 0.03) { continue; }
			vec2 ctr = trk_win.xy + (c + s.rg) * tex;
			vec2 d = p - ctr;
			if (dot(d, d) > 0.030) { continue; }
			float yaw = s.b * 6.2831853;
			float cs = cos(yaw);
			float sn = sin(yaw);
			// into the foot's own frame. tracks.gd puts a machine-local
			// (forward, lateral) into the world with [[cs, sn], [-sn, cs]];
			// this is that inverted, which for a rotation is its transpose.
			vec2 q = vec2(d.x * cs - d.y * sn, d.x * sn + d.y * cs);
			vec2 hf = trk_foot;
			vec2 qn = q / hf;
			float e = length(qn) + 1e-5;
			// the edge of a print in snow is CRUMBLED, never elliptical. This
			// is what stops a track reading as a row of stamps.
			e *= 0.90 + 0.24 * gnoise(p * 26.0 + 11.0);
			float dep = s.a * 0.075;
			float dh = 0.0;
			float dde = 0.0;
			if (e < 1.0) {
				// A ROUNDED PUNCH WITH A STEEP WALL, and the exponent is where
				// the picture is. At 1.0 it is a parabola and the print reads as
				// a dent; the wall of a real print is nearly vertical for the
				// first centimetre because the snow SHEARS rather than deforms.
				// The floor is clamped so the wall's gradient stays bounded -
				// an unbounded one aliases into a bright ring at three metres.
				float u = 1.0 - e * e;
				dh = -dep * pow(max(u, 0.0), 0.75);
				dde = dep * 1.5 * e * pow(max(u, 0.04), -0.25);
				acc.w = max(acc.w, 1.0 - e * 0.35);
			} else {
				float g = trk_rim / max(hf.x, 1e-4);
				float u = (e - 1.0) / g;
				if (u < 1.0) {
					float ru = u * (1.0 - u) * 4.0;          // 0 -> 1 -> 0
					dh = dep * 0.55 * ru;
					dde = dep * 0.55 * (4.0 - 8.0 * u) / g;
					acc.w = max(acc.w, (1.0 - u) * 0.55);
				}
			}
			if (dh == 0.0) { continue; }
			acc.x += dh;
			// grad = dh/de * de/dq * dq/dp, and dq/dp is the rotation back
			vec2 gq = dde * vec2(qn.x / hf.x, qn.y / hf.y) / e;
			acc.yz += vec2(gq.x * cs + gq.y * sn, -gq.x * sn + gq.y * cs);
		}
	}
	return acc;
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
float ghf(vec2 p, float hard, float wear, int lod, float trod) {
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
		//
		// AND THE BRAID PLAIN IS NOT THIS GROUND. The pit-head's bed is a 130 mm
		// worley with 38 mm of relief, which is right for a made yard and is a
		// REGULAR LATTICE at a metre - the first re-render of shot 4 came back
		// as rows of dark ovals, because the stones poked through the thin snow
		// on a grid. An outwash plain is smaller stones, sorted and packed by
		// the water that laid them, and it belongs to the landform rather than
		// to the site. Invisible until now, because until now the only macro in
		// the act was on concrete.
		float vr = clamp(vfloor.x, 0.0, 1.0);
		// A BEATEN PATH IS A PRESSED BED. The yard's gravel bed is a 130 mm
		// worley with 38 mm of relief; where the snow over it is thin - which
		// is exactly where something has walked all winter - those stones poke
		// through it on a regular grid and the track reads as COBBLES. Shot 7
		// came back paved. Feet press a bed flat; that is what a path is.
		float bed = (1.0 - vr * 0.95) * (1.0 - 0.80 * smoothstep(0.20, 0.72, trod));
		ho = 0.030 * (fbm2(p * 1.15) - 0.5) * (1.0 - vr * 0.55) * (1.0 - 0.45 * trod);
		// ruts: stretched hard across the direction of travel, soft along it
		ho -= 0.055 * wear * smoothstep(0.35, 0.72, fbm2(vec2(p.x * 0.30, p.y * 2.60)));
		if (lod >= 1) {
			ho += 0.038 * (1.0 - smoothstep(0.10, 0.62, worley(p * 7.5).x)) * bed;
			ho += vr * 0.012 * (1.0 - smoothstep(0.06, 0.52, worley(p * 23.0 + 9.0).x));
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
	vec3 V0 = normalize(CAMERA_POSITION_WORLD - wpos);
	float hard = max(max(in_rect(p0, pad, 1.6), in_rect(p0, pad2, 1.6)), vcol.r * 0.85);
	float wear = clamp(vcol.b, 0.0, 1.0);
	float pondable = clamp(vcol.a, 0.0, 1.0);
	float flat_ = smoothstep(0.86, 0.985, wnorm.y);
	// --- WHAT HAS WALKED HERE. `tracks.gd` owns the two buffers; this is one
	//     bilinear tap and it is read by four different things below.
	vec2 tuv = (p0 - trk_win.xy) * trk_win.z;
	vec3 K = vec3(0.0);
	if (tuv.x > 0.0 && tuv.y > 0.0 && tuv.x < 1.0 && tuv.y < 1.0) {
		K = texture(trk_pack, tuv).rgb;
	}
	// the counters are a 406 mm field, and a 406 mm grid must not be visible in
	// a 130 mm print. Every threshold below is crossed through a broad noise,
	// which costs one fbm and hides the lattice completely.
	float tramp = clamp(K.r * (0.84 + 0.34 * fbm2(p0 * 1.35 + 5.0)), 0.0, 1.0);
	float refroze = K.g;
	float trdirt = K.b;


	// EACH FREQUENCY GETS ITS OWN DISTANCE, and this is a correctness fix rather
	// than an optimisation. A 23 mm worley cell is four pixels at 10 m and two at
	// 20 m, and a two-pixel cell does not average, it ALIASES - it came back as
	// pale blotches crawling over the spoil tips that read exactly like snow.
	// Nyquist, not taste: every band is faded out before it reaches two pixels.
	float near_ = 1.0 - smoothstep(22.0, 38.0, dist);   // the coarse masks
	float near_a = 1.0 - smoothstep(6.0, 14.0, dist);   // 23 mm aggregate
	float near_s = 1.0 - smoothstep(14.0, 26.0, dist);  // 130 mm stones
	// THE BRAID PLAIN IS NOT THE YARD'S SOIL and it must not carry the yard's
	// 130 mm stone worley. Shot 4 is a macro at a metre, and at a metre that
	// worley is a REGULAR LATTICE of dark ovals - which is exactly what the
	// first re-render of the shot came back as. It was invisible for as long as
	// the only macro in the act was on concrete.
	float vriver = clamp(vfloor.x, 0.0, 1.0);
	near_s *= 1.0 - vriver * 0.94;
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
			float f = -ghf(p0 + stride * d, hard, wear, 0, tramp);
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
	float h = ghf(p, hard, wear, lodn, tramp);
	vec3 n = wnorm;
	// Past 55 m the ground's own form is a metre of relief across a hundred
	// pixels: the mesh normal already carries it and the two gradient taps buy
	// nothing. This is aimed squarely at the worst frame in the benchmark, which
	// is the wide establishing view at each end of the loop.
	if (dist < 55.0) {
		float gx = (ghf(p + vec2(e, 0.0), hard, wear, lodn, tramp) - h) / e;
		float gz = (ghf(p + vec2(0.0, e), hard, wear, lodn, tramp) - h) / e;
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

	// ---------------- THE VALLEY FLOOR, INSIDE THE SITE'S OWN MESH
	//
	// ACT-ONE 8.1: the pit-head's ground mesh used to be a FLAT LID out to
	// 420 m drawn on top of the valley, so the braid plain, the moraine trough
	// and the roches moutonnees did not exist inside that radius and shot 4
	// could not be taken. `ground.gd` now follows `Valley.h` outside the
	// compound, which gives back the FORM - but the braid plain is a MATERIAL
	// as much as a shape, and the valley shader owns that material. This is
	// that block, ported, keyed off UV2.x, which `ground.gd` fills from exactly
	// the field `valley.gd` writes into its own vertex colour G. Two surfaces,
	// one river.
	// ---------------- WHAT IS UNDER A BEATEN PATH, AND IT IS NOT SOIL
	//
	// Ground crossed all winter is not bare ground with the snow taken off it.
	// It is the BOTTOM OF THE SNOW: thawed under a foot, refrozen, with the
	// grit of the yard trodden into it, polished by every crossing since. The
	// first version left the yard's own dark soil showing through wherever the
	// track cleared it and drew black mud lanes across a white yard, which is a
	// summer picture. This is what makes a route read as a LINE from sixty
	// metres, which is the scale the print reconstruction cannot serve.
	float beaten = smoothstep(0.34, 0.90, tramp);
	if (beaten > 0.004) {
		vec3 ice_c = mix(vec3(0.168, 0.174, 0.184), vec3(0.104, 0.100, 0.094),
			clamp(trdirt * 2.4, 0.0, 1.0));
		alb = mix(alb, ice_c * mix(0.86, 1.14, grit), beaten * 0.88);
		r = mix(r, mix(0.42, 0.24, clamp(refroze * 2.6, 0.0, 1.0)), beaten * 0.85);
	}

	float river = vriver;
	if (river > 0.01) {
		float braid = fbm2(vec2(p.x * 0.011, p.y * 0.46) + 63.0);
		vec3 flat_c = mix(vec3(0.088, 0.078, 0.064), vec3(0.190, 0.196, 0.206),
			smoothstep(0.40, 0.75, braid));
		// WASHED GRAVEL, and it only exists inside four metres. An outwash plain
		// is made of 20-60 mm stones sorted by the water that put them there,
		// and at the range shot 4 is taken from that is what it has to be made
		// of. 26 cells a metre is a 38 mm stone; it is faded out by 8 m,
		// before it is two pixels, on the same Nyquist rule as everything else
		// in this shader.
		if (near_a > 0.01) {
			vec4 wg = worley(p * 26.0);
			float st = (1.0 - smoothstep(0.05, 0.52, wg.x)) * near_a;
			flat_c *= mix(1.0, mix(0.60, 1.46, hash21(floor(p * 26.0) + 5.0)), st * 0.90);
		}
		alb = mix(alb, flat_c, river * 0.90);
		r = mix(r, 0.88, river * 0.8);
		// the threads are narrow, and they are a MIRROR before they are a dark
		// body: what you see in meltwater under a bright sky is the sky.
		// THE WATER IS IN THE LOWEST PART OF THE CHANNEL, which is a correction
		// and not a tuning. Keying the threads to the braid noise ALONE put them
		// in bands six metres apart wherever the noise happened to be high, so
		// whether shot 4 had any water in it at all was a coin toss on where the
		// camera stood. `river` is the distance into the channel; the melt runs
		// down the middle of it and the noise decides which threads are running
		// today and which are dry gravel.
		float thread = smoothstep(0.62, 0.92, river)
			* (0.30 + 0.70 * smoothstep(0.42, 0.78, braid));
		alb = mix(alb, vec3(0.062, 0.070, 0.082), thread * 0.80);
		r = mix(r, 0.09, thread * 0.90);
		n = normalize(mix(n, vec3(0.0, 1.0, 0.0), thread * 0.90));
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

	// ================= SNOW, AND IT IS WHY THE ICE IS WORTH BUILDING =========
	//
	// DESIGN-PRINCIPLES 7 said: "clear ground is a feature - traffic lanes,
	// turning circles, the apron in front of a bay and the ground a machine
	// walks are kept clear, and their emptiness reads as use. Uniform cover is
	// the tell."
	//
	// In snow that stops being a placement rule and becomes a PHOTOGRAPH.
	// Somebody cleared this yard this morning and you can see exactly how far
	// they got. And THE-ICE 7.1 says why it matters more than it looks:
	//
	//   "Snow records what walked on it ... A training course in snow shows the
	//    machine's own path, every run, as a physical mark on the ground - where
	//    it hesitated, where it turned, where it went twice, where it went
	//    wrong. That is the single most valuable object the ice decision
	//    produces, and it is not an art win, it is a teaching win."
	//
	// AND THE FIRST VERSION OF THIS READ THE PLAN, WHICH IS THE DEFECT.
	// `wear` is baked from the six walkway polylines, the haul road and the
	// four stations, so a route appeared in the snow if and only if the LAYOUT
	// ALREADY KNEW ABOUT IT. A machine that walked somewhere nobody planned
	// left nothing - which is precisely the case the teaching loop is about,
	// and it made shot 7 a machine walking a course through untouched snow.
	//
	// `tracks.gd` accumulates instead. `tramp` is how many times something has
	// actually crossed this ground, `refroze` is how long ago it started, and
	// `trdirt` is what it dragged up. The plan's own wear field keeps ONE job
	// and it is not this one: a lane is PLOUGHED and swept as well as walked,
	// and the plan is a fair account of where a plough goes. It is at half
	// strength and it clears; it no longer draws tracks.
	// THE TRAMPLE TERM CLEARS, and where it clears what is under it is the
	// `beaten` block above rather than the yard's soil - which is the whole
	// reason that block exists. The thresholds are worth stating: the snow
	// depth term saturates the cover smoothstep at load 0.065, so only ground
	// past `tramp` ~0.85 - the main routes, walked all winter - opens at all,
	// and it opens PATCHILY, in the snow field's own hollows. A course branch
	// at 0.5 and the hero's own single pass at 0.04 keep their snow and show
	// their prints, which is the point.
	float clr = max(max(smoothstep(0.26, 0.74, wear) * 0.52,
			smoothstep(0.50, 0.95, tramp) * 0.97),
		1.0 - smoothstep(9.2, 11.6, length(p - hot_a)));
	float lie = clamp((1.0 - clr) * (1.0 - hard * 0.22) * (1.0 - river * 0.985),
		0.0, 1.0);
	float load = clamp(g_snow, 0.0, 1.0) * lie;
	// THE PRINTS. Nine texelFetches, and they are bought only where a 130 mm
	// print is bigger than a couple of pixels AND something has actually walked
	// here. In a wide frame that is no pixels at all.
	vec4 TR = vec4(0.0);
	if (dist < trk_far && tramp > 0.003) {
		TR = trk_prints(p);
		// AND PRINTS ARE TRODDEN OUT. On ground crossed all winter every texel
		// in the buffer holds a print, so drawing each one at full depth builds
		// a continuous raised lattice of rims that reads as COBBLES - which is
		// what shot 7 came back as on the first pass. What survives on a beaten
		// path is not four thousand footprints, it is packed lumpy firn; the
		// individual print is the thing that reads on ground crossed ONCE.
		float pfade = 1.0 - 0.66 * smoothstep(0.26, 0.82, tramp);
		TR.xyz *= pfade;
	}
	float sbase = snowf(p, lodn);
	float sfield = sbase + TR.x;
	// SNOW FINDS A LEVEL exactly the way water does, which is the same trick the
	// puddle code two blocks up uses and for the same reason: the edge of a
	// snow patch is where a SURFACE crosses a SURFACE. So it fills the slab
	// joints first, wraps round the aggregate, banks against the kerbs, and its
	// margin is ragged without a single patch shape being authored anywhere.
	float sd = load * 0.40 + sfield * load * 1.5 - h * 1.6 - 0.006;
	float scov = clamp(smoothstep(-0.006, 0.026, sd), 0.0, 1.0);
	float glit_s = 0.0;
	if (scov > 0.002) {
		float scav = sn_cav(sfield);
		vec3 sc = sn_col(scav, clamp(g_wet, 0.0, 1.0));
		// COMPACTED snow is a different material from lying snow and the
		// difference is the whole yard. Packed under a foot pad it is denser,
		// glassier, greyer and BLUER, because the light gets further into it
		// before it comes back out - which is the same path-length rule, used
		// as evidence of traffic rather than of depth.
		//
		// AND IT NOW COMES FROM A COUNTER RATHER THAN A DISTANCE FIELD, which
		// is what lets ground crossed a hundred times look different from
		// ground crossed twice. `TR.w` carries the single print, so one foot on
		// fresh snow packs its own bottom even where the counter is near zero.
		float pack = max(smoothstep(0.03, 0.52, tramp), TR.w * 0.80);
		sc = mix(sc, sc * mix(vec3(1.0), snow_deep, 0.55) * 0.72, pack);
		// REFROZEN. Snow crossed all winter thaws under a foot and freezes
		// again, and what that makes is not snow, it is ice with snow in it:
		// lower albedo, much lower roughness, and no facets at all.
		sc = mix(sc, sc * 0.66, refroze * 0.85);
		// AND DIRTY. Grit dragged up out of the ground underneath. This is the
		// third scale DESIGN-PRINCIPLES 4 asks for and it is the one that says
		// "a working yard" rather than "a ski slope".
		sc = mix(sc, mix(sc, alb, 0.66), trdirt);
		alb = mix(alb, sc, scov);
		r = mix(r, mix(mix(0.46, 0.80, scav), 0.22, max(pack, refroze)), scov);
		if (dist < 46.0) {
			float es = clamp(dist * 0.0026, 0.010, 0.09);
			vec2 gsn = vec2(snowf(p + vec2(es, 0.0), lodn) - sbase,
			                snowf(p + vec2(0.0, es), lodn) - sbase) / es + TR.yz;
			// the ground under the snow is GONE, not showing through, so the
			// snow's own normal REPLACES the concrete's rather than blending
			// with it - which is also why the joints stop reading where it lies
			n = normalize(mix(n, normalize(vec3(-gsn.x * 1.35, 1.0, -gsn.y * 1.35)), scov));
		}
		// the facets, lit by the sky, faded out before they alias
		float gf = (1.0 - smoothstep(4.0, 13.0, dist)) * scov * (1.0 - pack * 0.7)
			* (1.0 - refroze * 0.6);
		if (gf > 0.02) {
			vec3 zen = normalize(vec3(0.10, 1.0, -0.10));
			glit_s = sn_facet(p, n, V0, zen, gf) * 0.55;
		}
	}

	// ---------------- OCCLUSION
	// Cavity from the field: joints, cracks, the shadow side of every stone.
	// This is what stops a chipping lying on a bright plane like a sticker.
	float ao = clamp(1.0 + h * 7.0, 0.44, 1.0);
	ao *= 1.0 - 0.22 * par_shadow * clamp(1.0 - dist / 12.0, 0.0, 1.0);
	ao = mix(1.0, ao, 0.9);
	// snow fills its own hollows with scattered light: see the SNOW block. This
	// is the line that decides whether the yard reads as snow or as plaster.
	// The first take mixed this 0.78 toward white, which is physically closer to
	// the truth and photographs as a blank sheet: under a sky with no sun,
	// self-occlusion is the ONLY cue a snow surface has, so removing it removes
	// the surface. 0.45 keeps the hollows and still stops it reading as plaster.
	ao = mix(ao, mix(ao, 1.0, 0.45), scov);
	// a print is a hole and a hole sees less sky. Small, because snow fills its
	// own hollows with scattered light - the same correction two lines up.
	ao *= 1.0 - TR.w * 0.17 * scov;

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
	AO_LIGHT_AFFECT = mix(0.28, 0.09, scov);
	NORMAL = normalize((VIEW_MATRIX * vec4(n, 0.0)).xyz);
	EMISSION = spec * mix(0.55, 1.0, water) * ao + glit_s * mix(sky_col, sky_top, 0.4);

	if (dbg == 1) { ALBEDO = vec3(hard, mud, traffic); ROUGHNESS = 1.0; EMISSION = vec3(0.0); }
	if (dbg == 2 || dbg == 3) { ALBEDO = vec3(0.4); ROUGHNESS = 1.0; EMISSION = vec3(0.0); }
	if (dbg == 5) { ALBEDO = vec3(0.5); ROUGHNESS = 1.0; EMISSION = vec3(0.0); }
	if (dbg == 6) { ALBEDO = vec3(water, pondable, clamp(depth * 60.0, 0.0, 1.0)); ROUGHNESS = 1.0; EMISSION = vec3(0.0); }
	if (dbg == 7) { ALBEDO = vec3(0.0); ROUGHNESS = 1.0; EMISSION = vec3(1.0, 0.0, 0.6); }
	if (dbg == 17) { ALBEDO = vec3(0.5); ROUGHNESS = 1.0; EMISSION = vec3(0.0); }
	// --dbg=22: what walked here. R how many times, G how long ago it started,
	// B the print field itself. The only honest way to ask whether the counters
	// are where you think they are rather than judging them through snow, a
	// tone curve and a grade - the same argument --dbg=1 makes about wear.
	if (dbg == 22) { ALBEDO = vec3(0.0); ROUGHNESS = 1.0;
		EMISSION = vec3(tramp, refroze, clamp(-TR.x * 22.0, 0.0, 1.0)); }
	if (dbg == 23) { ALBEDO = vec3(0.0); ROUGHNESS = 1.0;
		EMISSION = vec3(river, clamp(vfloor.y, 0.0, 1.0), 0.0); }
}
"""

## ---------------------------------------------------------------------------
## THE VALLEY SHADER. Sixteen kilometres of landscape on one mesh: floor, two
## walls, a glacier, a horizon of peaks, and the three lines THE-ICE 3 hangs the
## entire timeline on.
##
## THE THREE LINES, and they are the reason this shader exists rather than the
## snow being. THE-ICE 3, verbatim:
##
##   the trimline  +310 m   "where the ice stood at its greatest. Weathered,
##                           jointed, lichened rock above; scoured, polished,
##                           freshly exposed rock below. Permanent, geological,
##                           a millennium old. One smoothstep on world height"
##   the town      +90/+520 "it straddles the trimline ... the society has been
##                           walking downhill for a thousand years and you can
##                           see the whole descent at once"
##   the snowline  +1100 m  "where the ice is NOW. It is not geological, it is
##                           current, and it is moving - the tell is a band of
##                           rock below it that is bare, raw and colonised by
##                           nothing, because it came out from under the ice
##                           inside a human lifetime"
##
## That is the whole timeline of the game delivered with no date, no era, no
## calendar and no word of language, which is WHAT-HAPPENED-HERE 1.3's rule
## obeyed exactly. Two of the three are one smoothstep each and they are in here.
##
## AND THE ALPENGLOW, which is the only warm light in the world (THE-ICE 2.7)
## and is drawn as a HEIGHT THRESHOLD rather than as a light. See the block
## comment above it: this is the one physical cheat in the pass and it is
## flagged in VALLEY.md.
const VALLEY_SHADER := """
shader_type spatial;
// Same argument as the ground shader: a first-person camera looking across a
// valley floor sees it at 80-89 degrees of incidence and Schlick goes to 1 at
// grazing whatever F0 is, so a full-hemisphere sky turns the whole landscape
// into a mirror. Every reflection here is hand written against an analytic sky.
render_mode cull_back, diffuse_burley, specular_disabled;

uniform float trim_h = 310.0;      // THE-ICE 3: where the ice stood
uniform float snow_h = 1100.0;     // THE-ICE 3: where the ice is now
uniform float bare_h = 90.0;       // the band below it that came out this lifetime
uniform float sun_h = 1500.0;      // the opposite ridge's shadow line
uniform float sun_soft = 110.0;
uniform vec3 alpen_col : source_color = vec3(1.00, 0.42, 0.20);
uniform float alpen_amt = 0.0;
uniform vec3 alpen_dir = vec3(-0.62, 0.13, 0.77);   // toward the low sun
uniform vec3 sky_col : source_color = vec3(0.62, 0.66, 0.72);
uniform vec3 sky_top : source_color = vec3(0.42, 0.48, 0.60);
uniform vec3 sun_col : source_color = vec3(1.0, 1.0, 1.0);
uniform vec3 sun_dir = vec3(0.55, 0.72, -0.42);
// THE WALL ROCK, and the first take had it at 0.28-0.48 linear after the scour
// multiplier - which is new plaster, not rock, and it is exactly the error
// materials/NOTES.md 5.1 records against ART-DIRECTION 3.1's own 0.34: "0.34
// linear is a pale limestone or new plaster ... I think it is the direct cause
// of what the designer was looking at". Against snow at 0.795 the rock has to be
// genuinely dark or there is no contrast on the wall, and with no contrast there
// is no trimline, no snow pattern and no landform - just a white ramp.
// AND DOWN AGAIN, a third time. Against snow at 0.795 the rock has to be
// genuinely dark or the wall has no contrast, and with no contrast there is no
// trimline, no bedding, no gully and no landform - only shading. 0.036-0.104 is
// a dark grey-brown crystalline rock and it is still inside ART-DIRECTION 3.1's
// one warm family; the measured band in materials/NOTES.md 5.1 argues that even
// this is on the pale side of honest.
uniform vec3 rock_lo : source_color = vec3(0.036, 0.030, 0.023);
uniform vec3 rock_hi : source_color = vec3(0.104, 0.088, 0.068);
uniform int dbg = 0;
global uniform float g_wet;

__NOISE__
__SNOW__

varying vec3 wpos;
varying vec3 wnorm;
varying vec4 vcol;

void vertex() {
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	wnorm = normalize((MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz);
	vcol = COLOR;
}

vec3 sky_of(vec3 d) {
	float t = clamp(d.y, 0.0, 1.0);
	vec3 c = mix(sky_col, sky_top, pow(t, 0.55));
	float s = clamp(dot(normalize(d), normalize(sun_dir)), 0.0, 1.0);
	c += sun_col * pow(s, 220.0) * 3.5;
	c += sun_col * pow(s, 8.0) * 0.10;
	return c;
}

// the rock the valley is cut out of. ART-DIRECTION 3.1's ONE warm family, and
// the trimline moves it along the family's own value axis rather than adding a
// hue - which is the letter as well as the intent of the no-hue-axis rule.
vec3 rock_of(vec2 p, float above_trim, float fp, out float rr, out float rcav) {
	// THREE BANDS, and the middle one is the one that was missing. fbm4 at
	// 0.055/m is an 18 m feature and fbm2 at 0.34/m is a 3 m one; between them
	// sat nothing, so at four hundred metres - which is where the wall is
	// actually looked at - the rock had no structure at all and read as a
	// gradient with fur on it. 0.011/m is a 90 m crag system and it survives to
	// the far ridge.
	float n0 = fbm2(p * 0.011 + 31.0);
	float n1 = fbm4(p * 0.055);
	float n2 = (1.0 - smoothstep(0.6, 2.4, fp * 0.4)) > 0.01 ? fbm2(p * 0.34 + 9.0) : 0.5;
	vec3 c = mix(rock_lo, rock_hi, n1);
	c *= mix(0.62, 1.34, n0);
	c *= mix(0.80, 1.22, n2);
	// ABOVE THE TRIMLINE: never buried. A thousand years of frost, so it is
	// jointed, broken, dark in the joints, and organic matter has had time to
	// find it. Darker and higher contrast.
	// BELOW IT: the ice took the surface off. Scoured, smoothed, paler, and
	// striated ALONG the valley because that is the way the ice went - which is
	// a real glacial signature and costs one sine.
	// GLACIAL STRIAE: parallel scratches gouged ALONG the ice's direction of
	// travel, which on both walls of a valley is along the valley. Real ones are
	// millimetres to metres apart; these are at three metres, because at 0.34 m
	// they were a third of a pixel at the distance the wall is actually seen
	// from and smeared into vertical fur over the entire mountainside.
	float striae = 0.0;
	if (fp < 2.4) {
		striae = sin(p.y * 0.34 + fbm2(p * 0.02) * 6.0) * 0.5 + 0.5;
		striae *= (1.0 - smoothstep(0.7, 2.4, fp));
	}
	// BELOW THE TRIMLINE the ice took the surface off within the last millennium,
	// so the rock is fresher, paler and smoother than the weathered stuff above.
	// 1.28 rather than 1.42: it is a different WEATHERING STATE of one warm rock
	// family (ART-DIRECTION 3.1), not a different rock and not a second hue.
	vec3 scour = c * 1.20 * mix(0.94, 1.06, striae);
	c = mix(scour, c * 0.74, above_trim);
	rcav = mix(smoothstep(0.42, 0.68, n2) * 0.45, smoothstep(0.34, 0.72, n2), above_trim);
	rr = mix(0.66, 0.95, n1) - (1.0 - above_trim) * 0.14;
	return c;
}

void fragment() {
	vec2 p = wpos.xz;
	float y = wpos.y;
	vec3 V = normalize(CAMERA_POSITION_WORLD - wpos);
	float dist = length(wpos - CAMERA_POSITION_WORLD);
	// THE PIXEL FOOTPRINT, in metres. This shader covers 30 m to 16 km in one
	// draw, so no band may be faded on DISTANCE - it has to be faded on how big
	// a pixel is on the surface, or the same band that is correct at the wall
	// toe is a screen of aliasing on the far ridge.
	float fp = length(fwidth(wpos)) + 0.0005;
	float slope = clamp(wnorm.y, 0.0, 1.0);
	float glacier = clamp(vcol.r, 0.0, 1.0);
	float river = clamp(vcol.g, 0.0, 1.0);
	float talus = clamp(vcol.b, 0.0, 1.0);
	float cut = vcol.a * 2.0 - 1.0;          // >0 buttress, <0 gully

	// ---------------- WHERE THE SNOW LIES
	// Below the snowline it lies on anything shallower than about 55 degrees,
	// loaded on the lee and scoured off the crests. Above it, on everything the
	// rock does not shed - which is why a peak is white and its cliffs are not.
	// ---------------- BEDDING, computed FIRST because the snow needs it.
	// Sedimentary rock is LAYERED, the layers are metres to tens of metres
	// thick, and - this is the part that reads - THEY RUN CONSISTENTLY ACROSS A
	// WHOLE MASSIF at one dip, because they were laid down flat and tilted once.
	// One plane equation and an fbm, and it is the single strongest "this is
	// rock" cue available at a kilometre.
	float bed_co = y * 0.9848 + p.x * 0.1736;        // 10 degrees of dip
	float bands = fbm2(vec2(bed_co * 0.055, p.y * 0.004 + 3.0));
	float bed = smoothstep(0.42, 0.58, bands);

	float above_snow = smoothstep(snow_h - 70.0, snow_h + 110.0, y);
	// ========================================================================
	// SNOW COVER IS A FUNCTION OF SLOPE. NOT OF HEIGHT, AND NOT OF NOISE.
	//
	// This is the rule the whole mountain hangs on and it is not a stylistic
	// choice - it is the mechanics of a snowpack, and it is why real ranges
	// look the way they do:
	//
	//   under ~30 deg   it lies, deep and smooth
	//   30 to 50 deg    it forms SLABS, and this band accumulates most
	//   over ~50 deg    IT WILL NOT HOLD. The face sluffs continuously as
	//                   spindrift and stays BARE ROCK, all winter, every winter
	//
	// So on a real mountain every steep face is exposed rock and the snow lives
	// on ledges, benches, gully floors, low-angle shoulders and buttress tops.
	// Rock is not decoration on a white shape; ROCK IS THE STRUCTURE and snow is
	// what settles into it. Getting this backwards is exactly what produced a
	// range of smooth white mounds with no structure at any scale.
	//
	// slope here is n.y = cos(angle): 0.643 is 50 deg, 0.766 is 40, 0.866 is 30.
	float lay = smoothstep(0.700, 0.880, slope);
	// ASPECT. The second term, and it is what stops the cover being a pure
	// function of steepness. Wind scours the windward face and dumps its load in
	// the lee, so two faces at the same angle on opposite sides of a ridge carry
	// completely different amounts. This is also what builds a cornice.
	vec2 fall = normalize(wnorm.xz + vec2(1e-5));
	float lee = clamp(dot(fall, snow_wind), -1.0, 1.0);
	// the lee LOADS but it cannot make a cliff hold: the boost is multiplicative
	// on a mask that is already zero above 50 degrees, and the additive part is
	// small enough that it cannot lift bare rock on its own.
	lay = clamp(lay * (1.0 + lee * 0.38) + lee * 0.07, 0.0, 1.0);
	// GULLIES LOAD, BUTTRESSES BLOW CLEAR. `cut` comes out of the LANDFORM's own
	// ridged field through vertex colour, so the snow lies in the gullies that
	// are actually there rather than in gullies the material invented. Two
	// fields that disagree about where a gully is look worse than no gullies.
	lay = clamp(lay - cut * 0.55, 0.0, 1.0);
	float dith = fbm2(p * 0.055 + 17.0) * 0.55 + fbm2(p * 0.28 + 4.0) * 0.45;
	lay = clamp(lay + (dith - 0.5) * 0.22, 0.0, 1.0);
	// TALUS holds snow well - it is a 33 degree apron - but not perfectly: the
	// blocks on a scree slope are half a metre across and they stand out of it.
	lay = max(lay, talus * 0.74);
	// ========================================================================
	// OUTCROPS, AND THIS IS THE LAST PIECE OF "WHERE'S THE ROCK".
	//
	// The slope rule is correct and it was not enough, for a reason that is
	// about VIEWING GEOMETRY rather than about the rule: from the floor of a
	// valley you see a wall almost edge-on, so the near-vertical faces the rule
	// correctly strips are foreshortened to nothing and the shallow shelves it
	// correctly covers are the ones facing you. Obey the rule and nothing else,
	// and you get a mountain that is bare where you cannot see it and white
	// where you can.
	//
	// What a real wall has instead is BANDS OF ROCK STANDING OUT OF THE SNOW at
	// every angle, because the beds are not equally resistant: the hard ones
	// form ledges and steps and the snow slides off them, and they run
	// horizontally across the whole face because the strata do. So the outcrops
	// come off the same `bands` field the rock's own bedding does - not off a
	// second noise - which is why they line up with the rock they expose.
	// and they persist a long way onto the shallows, because a bed that is hard
	// enough to form a ledge is hard enough to form one at any angle. Only truly
	// flat ground - a shelf, a col, the valley floor - buries them.
	float outcrop = smoothstep(0.48, 0.74, bands) * (1.0 - smoothstep(0.930, 0.996, slope));
	lay *= 1.0 - outcrop * 0.92;
	// above the permanent snowline even the steep carries rime and plastered
	// snow, but a vertical cliff is still a vertical cliff
	float cover = clamp(mix(lay, max(lay, smoothstep(0.30, 0.62, slope)), above_snow), 0.0, 1.0);
	// ========================================================================
	// AND THE BOUNDARY IS HARD. This is the last step and it is not cosmetic.
	//
	// Snow is 0.80 linear and this rock is 0.05-0.13, so they are NINE TO ONE in
	// albedo. A pixel at 30 per cent cover is therefore 75 per cent white by
	// value, and a mask that spends most of its range between 0.2 and 0.6 - as a
	// smoothstep of a noisy slope does - photographs as a white mountain with
	// faint grey shading on it, no matter how correct the mask is. Which is
	// exactly what the debug channel showed: the rule was working and none of it
	// was visible.
	//
	// A real snowfield on rock has a SHARP EDGE, because snow either bridged and
	// stayed or slid off. So the mask is pushed to its ends: bare is bare, white
	// is white, and the boundary is a line you could trace. That line is most of
	// what "where's the rock" was asking for.
	cover = smoothstep(0.38, 0.62, cover);
	cover = max(cover, glacier);
	cover *= 1.0 - river * 0.92;
	cover *= clamp(g_snow, 0.0, 1.0);
	// meltwater strips it off the floor near the river and around the terminus
	cover *= 1.0 - clamp(g_wet - 0.55, 0.0, 1.0) * vcol.b * 0.35;

	// ---------------- THE SNOW SURFACE
	int lod = fp < 0.05 ? 2 : (fp < 0.45 ? 1 : 0);
	float sh = snowf(p, lod);
	vec3 n = wnorm;
	// bands fade by footprint. Drifts survive to two kilometres, sastrugi to
	// two hundred metres, grain to ten - which is what they are worth.
	float f_snow = 1.0 - smoothstep(1.6, 6.0, fp);
	if (cover > 0.02 && f_snow > 0.01) {
		float e = clamp(fp * 1.5, 0.012, 3.0);
		float s0 = snowf(p, lod);
		vec2 gs = vec2(snowf(p + vec2(e, 0.0), lod) - s0,
		               snowf(p + vec2(0.0, e), lod) - s0) / e;
		n = normalize(n + vec3(-gs.x, 0.0, -gs.y) * cover * f_snow * 1.15);
	}
	float cav = sn_cav(sh);

	// ---------------- ROCK
	float above_trim = smoothstep(trim_h - 26.0, trim_h + 18.0, y);
	// AND THE BAND THAT SAYS THE SNOWLINE IS MOVING. THE-ICE 3: rock below the
	// snowline that "is bare, raw and colonised by nothing, because it came out
	// from under the ice inside a human lifetime". So it is the palest, cleanest
	// rock on the wall, and it is a band rather than a line - which is the tell
	// that this line is CURRENT and the trimline is not.
	float fresh = smoothstep(snow_h - bare_h - 60.0, snow_h - bare_h + 40.0, y)
		* (1.0 - smoothstep(snow_h - 40.0, snow_h + 90.0, y));
	float rr; float rcav;
	vec3 rock = rock_of(p, above_trim * (1.0 - fresh), fp, rr, rcav);
	rock *= mix(1.0, 1.30, fresh);
	// the bedding, applied. It was computed at the top of fragment() because the
	// snow mask needs it too - see OUTCROPS.
	rock *= mix(0.70, 1.28, bed);
	rr += (bed - 0.5) * 0.12;
	// the fine bedding, which only survives close in but is what makes the
	// bottom of the wall read as a quarry face
	if (fp < 1.2) {
		float fine_b = sin(bed_co * 0.62 + fbm2(p * 0.02) * 5.0) * 0.5 + 0.5;
		rock *= mix(0.88, 1.12, fine_b * (1.0 - smoothstep(0.4, 1.2, fp)));
	}
	// ---------------- TALUS is a different material from the face above it.
	// Angular shattered rubble, one value, no bedding, and much rougher.
	if (talus > 0.01) {
		float rub = fbm2(p * 0.62 + 88.0);
		vec3 scree = mix(rock_lo, rock_hi, 0.42) * mix(0.72, 1.30, rub);
		rock = mix(rock, scree, talus * 0.90);
		rcav = mix(rcav, 0.55 + 0.35 * rub, talus * 0.8);
		rr = mix(rr, 0.97, talus * 0.8);
	}

	// ---------------- COMBINE
	// SNOW IS NOT ONE MATERIAL EITHER, and on the floor - which is most of the
	// frame in half these shots - a single uniform white is as much a tell as a
	// single uniform rock was. Three states, all of them real, all of them from
	// one extra noise:
	//   WIND CRUST   scoured hard and glazed, brighter and much smoother, on the
	//                exposed backs of the drifts
	//   SASTRUGI     the worked surface in between, which is what snowf() draws
	//   OLD DIRTY    where the valley's own dust and the works' grit have been
	//                blown onto it and re-frozen, near the ground and downwind
	float state = fbm2(p * 0.026 + 5.0) * 0.62 + fbm2(p * 0.13 + 44.0) * 0.38;
	float crust = smoothstep(0.56, 0.76, state) * clamp(1.0 - cut * 2.0, 0.0, 1.0);
	float dirty = smoothstep(0.62, 0.86, 1.0 - state) * clamp(1.0 - y / 90.0, 0.0, 1.0);
	vec3 snow_c = sn_col(cav, clamp(g_wet, 0.0, 1.0));
	snow_c *= mix(1.0, 1.06, crust);
	snow_c = mix(snow_c, snow_c * vec3(0.74, 0.72, 0.70), dirty * 0.55);
	vec3 alb = mix(rock, snow_c, cover);
	float rough = mix(rr, mix(mix(0.40, 0.80, cav), 0.20, crust), cover);
	// the glacier is ICE, not snow: harder, glossier, and the blue is deeper
	// because the path length through it is metres rather than centimetres
	if (glacier > 0.01) {
		vec3 ice = sn_col(1.0, 0.35) * 0.86;
		alb = mix(alb, ice, glacier * 0.72);
		rough = mix(rough, 0.24, glacier * 0.66);
	}
	// THE MELTWATER, and it is braided rather than channelled. A glacier's river
	// carries more load than it can move, so it splits, wanders and re-joins
	// across a wide flat of its own gravel. What that gives the frame is a PALE
	// band with DARK THREADS in it, which is worth much more than a dark canal:
	// the flat is the only bare ground on the whole valley floor, so it is the
	// only place the warm rock family appears at ground level, and the threads
	// are the only moving thing in the picture.
	if (river > 0.01) {
		float braid = fbm2(vec2(p.x * 0.011, p.y * 0.46) + 63.0);
		vec3 flat_c = mix(vec3(0.088, 0.078, 0.064), vec3(0.190, 0.196, 0.206),
			smoothstep(0.40, 0.75, braid));
		alb = mix(alb, flat_c, river * 0.90);
		rough = mix(rough, 0.88, river * 0.8);
		// THE THREADS ARE NARROW AND THEY ARE NOT BLACK. At 0.026 linear over
		// 92% they read as holes punched in the snowfield, which is the single
		// most render-looking thing a white landscape can do. Meltwater under a
		// bright sky is a MIRROR before it is a dark body: what you see is the
		// sky in it, so its albedo hardly matters and its roughness does all the
		// work. Half of it is under rotten shore ice anyway.
		// THE WATER IS IN THE LOWEST PART OF THE CHANNEL, which is a correction
		// and not a tuning. Keying the threads to the braid noise ALONE put them
		// in bands six metres apart wherever the noise happened to be high, so
		// whether shot 4 had any water in it at all was a coin toss on where the
		// camera stood. `river` is the distance into the channel; the melt runs
		// down the middle of it and the noise decides which threads are running
		// today and which are dry gravel.
		float thread = smoothstep(0.62, 0.92, river)
			* (0.30 + 0.70 * smoothstep(0.42, 0.78, braid));
		alb = mix(alb, vec3(0.062, 0.070, 0.082), thread * 0.80);
		rough = mix(rough, 0.09, thread * 0.90);
		n = normalize(mix(n, vec3(0.0, 1.0, 0.0), thread * 0.90));
	}

	// ---------------- OCCLUSION, and it is not the rock's
	float ao = clamp(1.0 - rcav * 0.55, 0.42, 1.0);
	// snow fills its own hollows with scattered light - but only partly, or the
	// surface disappears. See the same correction in the ground shader.
	ao = mix(ao, mix(ao, 1.0, 0.45), cover);
	// AND THE SHAPE OF THE MOUNTAIN ITSELF. At two kilometres the snow's own
	// relief is long gone and the mesh normal is all that is left, so the wall
	// needs a cheap large-scale occlusion or it reads as a paper cut-out. A
	// gully is darker than the spur beside it because it can see less sky, and
	// that is a slope-and-curvature term, not a light.
	ao *= mix(1.0, clamp(0.55 + slope * 0.55, 0.0, 1.0), clamp(fp * 0.35, 0.0, 0.85));

	// ---------------- THE GLITTER
	// Facets, lit by whatever is bright. On the floor that is the sky; on the
	// peaks it is the sun. Both are handed to the same function.
	float gf = (1.0 - smoothstep(0.006, 0.030, fp)) * cover;
	vec3 glit = vec3(0.0);
	if (gf > 0.02) {
		vec3 zen = normalize(vec3(0.10, 1.0, -0.10));
		glit += sky_of(zen) * sn_facet(p, n, V, zen, gf) * 0.55;
	}

	// ---------------- ALPENGLOW.
	// THE-ICE 2.7: "alpenglow on the peaks at 2600-3200 m is the only sunlit
	// surface in the exterior and the player can never stand on it. That gives
	// every wide frame a warm third - cold blue floor, warm lit peaks - with no
	// invented light source."
	//
	// THE CHEAT, FLAGGED. This is not a second sun and there is no shadow map
	// fifteen kilometres wide. It is the FIRST sun, still above the ridge the
	// valley floor is behind, drawn as what it geometrically is: a height
	// threshold with a real N.L against the sun's direction. A shadow map that
	// covered this range would cost more than the mountains do, and the line it
	// produced would be a straight horizontal one anyway, because the ridge that
	// casts it is a ridge.
	if (alpen_amt > 0.001) {
		float lit = smoothstep(sun_h - sun_soft, sun_h + sun_soft, y);
		// the ridge that casts the shadow is not level, so neither is its edge
		lit *= 1.0;
		float ndl = clamp(dot(n, normalize(alpen_dir)), 0.0, 1.0);
		vec3 warm = alpen_col * alpen_amt * lit * (ndl * 0.86 + 0.14);
		// on snow it is a wrap, not a lambert, and it stains the shadow side too
		vec3 give = mix(vec3(0.30), alb, 0.72);
		glit += warm * give;
		// and the facets catch it hard, which is what makes a lit peak SHIMMER
		if (gf > 0.02) {
			glit += alpen_col * alpen_amt * lit
				* sn_facet(p, n, V, normalize(alpen_dir), gf) * 2.2;
		}
	}

	// ---------------- the hand-written sky reflection
	float ndv = clamp(dot(n, V), 0.0, 1.0);
	float F = 0.02 + 0.98 * pow(1.0 - ndv, 5.0);
	float gloss = pow(1.0 - clamp(rough, 0.0, 1.0), 2.2);
	vec3 spec = sky_of(reflect(-V, n)) * F * gloss * mix(0.35, 1.0, river + glacier);
	// snow's forward scatter: at grazing you are looking THROUGH a centimetre of
	// it and it goes bright and slightly warm. That is real and it is what makes
	// a low camera over a snowfield work.
	spec += mix(sky_col, sky_top, 0.4) * pow(1.0 - ndv, 2.6) * cover * 0.10;

	ALBEDO = alb;
	ROUGHNESS = clamp(rough, 0.05, 1.0);
	METALLIC = 0.0;
	AO = ao;
	AO_LIGHT_AFFECT = mix(0.30, 0.08, cover);
	NORMAL = normalize((VIEW_MATRIX * vec4(n, 0.0)).xyz);
	EMISSION = glit + spec * ao;

	if (dbg == 1) { ALBEDO = vec3(cover, above_trim, above_snow); ROUGHNESS = 1.0; EMISSION = vec3(0.0); }
	if (dbg == 2 || dbg == 3) { ALBEDO = vec3(0.4); ROUGHNESS = 1.0; EMISSION = vec3(0.0); }
	if (dbg == 18) { ALBEDO = vec3(0.0); EMISSION = vec3(clamp(fp, 0.0, 1.0), clamp(fp * 0.1, 0.0, 1.0), 0.0); }
}

// THE SNOW BRDF, and it is the thing the materials spike named as its biggest
// remaining item ("that needs a custom light() function, which means writing
// the whole BRDF"). Snow is the material that most needs it, because every
// characteristic thing snow does to light is invisible to a Lambert-plus-GGX.
void light() {
	float ndl = dot(NORMAL, LIGHT);
	// WRAP. Multiple scattering inside the pack carries light metres around the
	// terminator, so snow a hand's breadth into shadow is DIMMER, not dark, and
	// the terminator is a soft coloured band rather than an edge. 0.62 is a lot
	// of wrap and it is right for a dense forward scatterer.
	float w = 0.62;
	float wr = pow(clamp((ndl + w) / (1.0 + w), 0.0, 1.0), 0.78);
	DIFFUSE_LIGHT += LIGHT_COLOR * ATTENUATION * ALBEDO * wr;
	// TRANSMISSION. In the front, out the back. A drift lip, a cornice and the
	// cut edge of a ploughed lane all do this and it is the whole reason snow
	// does not read as plaster at a silhouette.
	float bk = clamp(-ndl, 0.0, 1.0);
	DIFFUSE_LIGHT += LIGHT_COLOR * ATTENUATION * ALBEDO * snow_deep
		* pow(bk, 2.6) * snow_sss;
	// one broad specular lobe off the packed crust. The facets are in EMISSION,
	// because on this valley floor there is no direct light for them to catch.
	vec3 H = normalize(LIGHT + VIEW);
	float nh = max(dot(NORMAL, H), 0.0);
	float a = max(ROUGHNESS * ROUGHNESS, 0.003);
	float dn = nh * nh * (a * a - 1.0) + 1.0;
	SPECULAR_LIGHT += LIGHT_COLOR * ATTENUATION * (a * a / (3.1416 * dn * dn))
		* SPECULAR_AMOUNT * max(ndl, 0.0) * 0.5;
}
"""

static var _shader_solid: Shader
static var _shader_ground: Shader
static var _shader_valley: Shader
static var _cache: Dictionary = {}
static var _grounds: Array = []
static var _valleys: Array = []

static func solid_shader() -> Shader:
	if _shader_solid == null:
		_shader_solid = Shader.new()
		_shader_solid.code = SOLID_SHADER.replace("__NOISE__", NOISE).replace("__SNOW__", SNOW)
	return _shader_solid

static func ground_shader() -> Shader:
	if _shader_ground == null:
		_shader_ground = Shader.new()
		_shader_ground.code = GROUND_SHADER.replace("__NOISE__", NOISE).replace("__SNOW__", SNOW)
	return _shader_ground

static func valley_shader() -> Shader:
	if _shader_valley == null:
		_shader_valley = Shader.new()
		_shader_valley.code = VALLEY_SHADER.replace("__NOISE__", NOISE).replace("__SNOW__", SNOW)
	return _shader_valley

## The valley's material takes the three lines straight out of the integer plan,
## so the shader cannot disagree with the layout about where the ice stood.
static func valley_material(L: SurfaceLayout) -> ShaderMaterial:
	var m := ShaderMaterial.new()
	m.shader = valley_shader()
	var V: Dictionary = L.plan["valley"]
	m.set_shader_parameter("trim_h", float(V["trim_h"]) * 0.001)
	m.set_shader_parameter("snow_h", float(V["snow_h"]) * 0.001)
	m.set_shader_parameter("bare_h", float(V["bare_h"]) * 0.001)
	m.set_shader_parameter("sun_h", float(V["sun_h"]) * 0.001)
	_valleys.append(m)
	return m

static func valleys() -> Array:
	return _valleys

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
		# ORDER PASS (DESIGN-PRINCIPLES 7). Line paint on concrete: high albedo but
		# NOT white - a lane marking that has been driven over for a season is
		# 0.45-0.55 linear and it is dirtiest where the wheels run, which is what
		# the wide dirt term is for. It is the cheapest object on the site that
		# answers "who put it there and why".
		"paint":    [Vector3(0.690, 0.640, 0.455), 0.50, 0.84, 0.0, 0.40, 0.0, 7.0, 0.30, 0.22, 0.0],
		"glass":    [Vector3(0.050, 0.053, 0.058), 0.04, 0.14, 0.0, 0.08, 0.0, 8.0, 0.05, 0.10, 0.0],
		# ---------------- scatter and growth
		"weed":     [Vector3(0.072, 0.086, 0.038), 0.62, 0.96, 0.0, 0.60, 0.0, 3.0, 0.10, 0.70, 0.0],
		"gravel":   [Vector3(0.166, 0.146, 0.116), 0.72, 0.99, 0.0, 0.80, 0.0, 12.0, 0.22, 1.90, 0.25],
		"litter":   [Vector3(0.270, 0.268, 0.256), 0.38, 0.80, 0.0, 0.60, 0.0, 9.0, 0.35, 0.45, 0.0],
		"water":    [Vector3(0.026, 0.032, 0.036), 0.02, 0.07, 0.0, 0.12, 0.0, 3.0, 0.0, 0.10, 0.0],
		# ---------------- THE ICE (DESIGN-PRINCIPLES 10, THE-ICE 7)
		# Snow as a SOLID, for the drifts and banks that a height field cannot
		# do. The materials spike's own 7.4 is the reason these exist at all:
		# "a flat plane with a heightfield on it is still a flat plane ... at
		# grazing the ground shows a clean straight edge". A drift is exactly
		# the case parallax cannot fake, so drifts are geometry.
		#
		# 0.795 linear is settled snow. `calib.py` in the materials spike puts
		# its plausibility ceiling at 0.93 "fresh snow 0.85", so this sits where
		# a fortnight-old pack belongs. Grain is LOW - snow does not have value
		# variation, it has FORM variation - and the roughness band is wide
		# because a crust and the powder beside it are different materials.
		"snow":     [Vector3(0.795, 0.795, 0.795), 0.44, 0.82, 0.0, 0.16, 0.0, 2.2, 0.02, 1.10, 0.0],
		# packed by traffic: denser, glassier, and bluer because the light gets
		# further in. THE-ICE 6.1's path-length rule used as evidence of use.
		"snowpack": [Vector3(0.615, 0.640, 0.700), 0.26, 0.54, 0.0, 0.22, 0.0, 3.0, 0.10, 0.55, 0.0],
		# ice. THE-ICE 2.5 amends ART-DIRECTION 9's "no ice" to "ice is a
		# material and a place, never a biome and never a hue axis". This is the
		# material half: one colour, and the DISTANCE does the work.
		"ice":      [Vector3(0.480, 0.560, 0.660), 0.06, 0.26, 0.0, 0.14, 0.0, 4.0, 0.04, 0.30, 0.0],
		# ---------------- THE TOWN (THE-ICE 7.3)
		# Two materials and the whole age gradient is in the difference between
		# them: quarried stone that has stood above the trimline for a thousand
		# winters, and panel that was made in a factory this decade.
		"oldstone": [Vector3(0.150, 0.138, 0.118), 0.74, 0.98, 0.0, 1.10, 0.35, 2.0, 0.30, 1.70, 0.30],
		"newpanel": [Vector3(0.372, 0.372, 0.380), 0.30, 0.60, 0.0, 0.26, 0.0, 4.0, 0.16, 0.35, 0.0],
		"roofdark": [Vector3(0.062, 0.060, 0.062), 0.44, 0.82, 0.0, 0.45, 0.0, 5.0, 0.30, 0.60, 0.05],
		# a lit window seen from nine hundred metres. THE-ICE 2.6: nothing in the
		# world may emit belief's colour, so this is warm and it is the second
		# warm element in the exterior after the alpenglow.
		"warmlit":  [Vector3(1.000, 0.660, 0.352), 0.10, 0.30, 0.0, 0.10, 0.0, 6.0, 0.02, 0.10, 0.0],
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
	# How much snow this material collects on its up-facing surfaces. Glass and
	# a screen shed it; a lit fitting melts it off; snow on snow is fine and is
	# how a drift gets a crust. Everything else in a yard collects it.
	var st := 1.0
	if id == "screen" or id == "glass" or id == "water" or id == "warmlit":
		st = 0.0
	elif id == "amber" or id == "ember":
		st = 0.22
	elif id == "ice":
		st = 0.35
	m.set_shader_parameter("snow_take", st)
	# a drift IS snow: it takes its own place in the noise field so its crust
	# stops agreeing with the ground's, and it is covered all over. ACT-ONE 8.2.
	m.set_shader_parameter("snow_body", 1.0 if id == "snow" else 0.0)
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
	# a fitting that is on is warm, and snow does not lie on it
	m.set_shader_parameter("snow_take", 0.0)
	m.set_shader_parameter("emissive", strength)
	_cache[key] = m
	return m
