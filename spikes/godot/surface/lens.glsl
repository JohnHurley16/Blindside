#[compute]
#version 450

// ---------------------------------------------------------------------------
// BLINDSIDE -- the lens and the sensor, PIT-HEAD.  TRAILER.md 9.
//
// Ported from spikes/godot/cave/lens.glsl. The optics are unchanged, because
// optics do not care what is in front of them: distortion, lateral chromatic
// aberration, cos^4 vignetting, shutter integration and the sensor's own shot
// and read noise are the same arithmetic under a sky as under a lamp. Only the
// TUNING changes, and the tuning lives on the CPU side in postfx.gd.
//
// One effect was ADDED here that the cave cut on the spec's own words:
//
//   TRAILER 9, lens dirt / streak: "Only on the surface, only in rain, only on
//   the strongest sources. Easy to overdo; cut first if in doubt."
//
// and the cave's CINEMA.md 6.10: "There is no rain 140 m down a drowned mine
// and nothing is spraying the lens ... If it appears anywhere it belongs in
// spikes/godot/surface." Two of the ten pit-head trailer shots are rain shots,
// so this is the pass that has to answer it. See F_DIRT below and CINEMA.md 6.10.
//
// One compute pass at POST_TRANSPARENT, on the HDR *linear* colour buffer
// BEFORE tonemapping, which is where these things physically happen:
//
//   distortion, chromatic aberration, vignetting   the lens, on radiance
//   dirt on the front element                      forward scatter, on radiance
//   motion blur                                    integration over the shutter
//   shot / read noise                              the sensor, on electrons
//
// and only then does AgX turn the result into a picture.
// ---------------------------------------------------------------------------

layout(local_size_x = 8, local_size_y = 8, local_size_z = 1) in;

layout(set = 0, binding = 0) uniform sampler2D src_colour;
layout(set = 0, binding = 1) uniform sampler2D src_depth;
layout(rgba16f, set = 0, binding = 2) uniform restrict writeonly image2D dst_colour;

layout(set = 0, binding = 3, std140) uniform Params {
	mat4 inv_vp;        // clip -> world, this frame
	mat4 prev_vp;       // world -> clip, the previous SHOT frame
	vec2 size;          // pixels
	vec2 half_px;
	float k_distort;    // barrel: negative pulls the corners in
	float ca_px;        // lateral chromatic aberration at the corner, pixels
	float vig_k;        // 0..1 how much of the cos^4 law survives the lens design
	float cos4_corner;  // cos^4(theta) at the frame corner for this focal length
	float shutter;      // fraction of a frame interval the shutter is open
	float max_blur_px;
	float full_well;    // electrons at signal 1.0 -- sets the shot noise
	float read_noise;   // sensor floor, in signal units
	float grain_px;     // grain cell size in pixels
	float seedt;        // per-frame noise seed
	float dirt_gain;    // how much the front element scatters
	float dirt_thresh;  // the radiance above which a source is "strongest"
	int taps;
	int flags;
} p;

#define F_DISTORT   1
#define F_CA        2
#define F_VIGNETTE  4
#define F_GRAIN     8
#define F_MBLUR    16
#define F_VELDBG   32
#define F_BLIT     64
#define F_DIRT    128
#define F_HDR     256

float hash13(vec3 v) {
	v = fract(v * 0.1031);
	v += dot(v, v.yzx + 33.33);
	return fract((v.x + v.y) * v.z);
}

float h21(vec2 v) { return hash13(vec3(v, 7.7)); }

float vn2(vec2 x) {
	vec2 i = floor(x);
	vec2 f = x - i;
	f = f * f * (3.0 - 2.0 * f);
	float a = h21(i), b = h21(i + vec2(1.0, 0.0));
	float c = h21(i + vec2(0.0, 1.0)), d = h21(i + vec2(1.0, 1.0));
	return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);
}

// The state of the front element, in SCREEN space, because that is where a
// mark on the glass is: it does not move when the camera moves, which is the
// single thing that distinguishes dirt from anything in the world. Two
// populations, which is what a wet lens actually carries -- a fine haze of
// dried spatter, and a handful of fat drops that have run and stopped.
float dirt_field(vec2 uv, float aspect) {
	vec2 q = vec2(uv.x * aspect, uv.y);
	// vertical run: a drop on a vertical front element runs DOWN, so the
	// pattern is stretched 4:1 in y and not isotropic
	float haze = vn2(q * vec2(36.0, 9.0) + 3.1) * vn2(q * vec2(17.0, 5.0) + 11.7);
	haze = smoothstep(0.34, 0.86, haze);
	float drop = vn2(q * vec2(7.0, 5.5) + 41.0);
	drop = smoothstep(0.72, 0.97, drop);
	return haze * 0.55 + drop * 1.0;
}

void main() {
	ivec2 gid = ivec2(gl_GlobalInvocationID.xy);
	if (gid.x >= int(p.size.x) || gid.y >= int(p.size.y)) return;

	vec2 uv = (vec2(gid) + 0.5) / p.size;

	// Godot's scene colour buffer is not created with CAN_COPY_TO, so the
	// result cannot be blitted back into it with texture_copy. The effect
	// therefore runs as two dispatches: the work into a scratch target, then
	// this 1:1 store back.
	if ((p.flags & F_BLIT) != 0) {
		imageStore(dst_colour, gid, vec4(texture(src_colour, uv).rgb, 1.0));
		return;
	}

	// HDR PROBE. Bloom's threshold and the dirt's "strongest sources" gate are
	// both stated in units of scene radiance, and nobody has ever measured what
	// range this site's radiance actually occupies -- the cave's numbers are for
	// one lamp in a black room. Written as lum/16 and read back through the
	// LINEAR tonemapper, this recovers it exactly. See CINEMA.md 6.2.
	if ((p.flags & F_HDR) != 0) {
		float l = dot(texture(src_colour, uv).rgb, vec3(0.2126, 0.7152, 0.0722));
		imageStore(dst_colour, gid, vec4(vec3(l * 0.0625), 1.0));
		return;
	}

	float aspect = p.size.x / p.size.y;
	vec2 c = (uv - 0.5) * vec2(aspect, 1.0);
	float rn = length(c) / length(vec2(aspect, 1.0) * 0.5);

	// ---- lens distortion ------------------------------------------------
	vec2 uvl = uv;
	if ((p.flags & F_DISTORT) != 0) {
		float r2 = rn * rn;
		float s = (1.0 + p.k_distort * r2) / (1.0 + p.k_distort);
		uvl = 0.5 + (c * s) / vec2(aspect, 1.0);
	}

	// ---- reprojection velocity ------------------------------------------
	vec2 vel = vec2(0.0);
	if ((p.flags & F_MBLUR) != 0) {
		float d = texture(src_depth, uvl).r;
		vec4 clip = vec4(uvl * 2.0 - 1.0, d, 1.0);
		vec4 wp = p.inv_vp * clip;
		if (abs(wp.w) > 1e-6) {
			wp /= wp.w;
			vec4 pc = p.prev_vp * wp;
			if (pc.w > 1e-6) {
				vec2 puv = (pc.xy / pc.w) * 0.5 + 0.5;
				vel = (uvl - puv) * p.shutter;
			}
		}
		vec2 vpx = vel * p.size;
		float vl = length(vpx);
		if (vl > p.max_blur_px) vel *= p.max_blur_px / vl;
		if (vl < 0.35) vel = vec2(0.0);
	}

	// ---- chromatic aberration, carried into the shutter integral --------
	vec2 cadir = vec2(0.0);
	if ((p.flags & F_CA) != 0) {
		vec2 rd = uvl - 0.5;
		cadir = rd * (p.ca_px / max(length(rd * p.size), 1.0)) * rn;
	}

	if ((p.flags & F_VELDBG) != 0) {
		vec3 dbg = vec3(0.0);
		if (vel.y < 0.0) dbg.r = 1.0; else dbg.b = 1.0;
		dbg.g = min(length(vel * p.size) / 8.0, 1.0);
		imageStore(dst_colour, gid, vec4(dbg, 1.0));
		return;
	}

	int n = ((p.flags & F_MBLUR) != 0 && vel != vec2(0.0)) ? p.taps : 1;
	vec3 acc = vec3(0.0);
	for (int i = 0; i < n; i++) {
		float f = (n == 1) ? 0.0 : (float(i) / float(n - 1) - 0.5);
		vec2 s = uvl + vel * f;
		if ((p.flags & F_CA) != 0) {
			acc.r += texture(src_colour, s + cadir).r;
			acc.g += texture(src_colour, s).g;
			acc.b += texture(src_colour, s - cadir).b;
		} else {
			acc += texture(src_colour, s).rgb;
		}
	}
	vec3 col = acc / float(n);

	// ---- dirt on the front element --------------------------------------
	// Forward scatter: a mark on the glass takes light from a STRONG source
	// somewhere near it in the frame and spreads it over itself. So it is
	// gated on the radiance in a wide neighbourhood, not on this pixel, and
	// only on radiance above dirt_thresh -- TRAILER 9's "only on the strongest
	// sources", as a threshold rather than as a instruction to be careful.
	// Five taps: cheap, and a source has to be genuinely near to smear.
	if ((p.flags & F_DIRT) != 0) {
		float veil = 0.0;
		const vec2 O[5] = vec2[5](vec2(0.0, 0.0), vec2(0.055, 0.021),
			vec2(-0.048, 0.030), vec2(0.014, -0.058), vec2(-0.026, -0.045));
		for (int i = 0; i < 5; i++) {
			vec3 t = texture(src_colour, uvl + O[i]).rgb;
			veil = max(veil, dot(t, vec3(0.2126, 0.7152, 0.0722)));
		}
		veil = max(veil - p.dirt_thresh, 0.0);
		col += vec3(1.0, 0.985, 0.955) * (dirt_field(uv, aspect) * p.dirt_gain * veil);
	}

	// ---- vignetting ------------------------------------------------------
	if ((p.flags & F_VIGNETTE) != 0) {
		float t = rn * rn;
		float v = mix(1.0, p.cos4_corner, t * t * 0.5 + t * 0.5);
		col *= mix(1.0, v, p.vig_k);
	}

	// ---- the sensor ------------------------------------------------------
	// sigma = sqrt(S / full_well) + read_noise. Poisson, so the signal-to-noise
	// ratio is worst in the near-black and best in the sky. Applied to the
	// linear signal before AgX, which is where a sensor's noise happens.
	if ((p.flags & F_GRAIN) != 0) {
		vec2 g = floor(vec2(gid) / max(p.grain_px, 1.0));
		float u1 = max(hash13(vec3(g, p.seedt)), 1e-6);
		float u2 = hash13(vec3(g.yx + 17.0, p.seedt + 3.7));
		float gauss = sqrt(-2.0 * log(u1)) * cos(6.2831853 * u2);
		float u3 = hash13(vec3(g + 91.0, p.seedt + 11.3));
		float u4 = hash13(vec3(g.yx + 53.0, p.seedt + 29.1));
		vec3 chroma = vec3(u3, u4, 1.0 - u3) - 0.5;
		float lum = max(dot(col, vec3(0.2126, 0.7152, 0.0722)), 0.0);
		float sigma = sqrt(lum / max(p.full_well, 1.0)) + p.read_noise;
		col += sigma * (gauss + chroma * 0.7);
		col = max(col, vec3(0.0));
	}

	imageStore(dst_colour, gid, vec4(col, 1.0));
}
