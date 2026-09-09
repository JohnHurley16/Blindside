#[compute]
#version 450

// ---------------------------------------------------------------------------
// BLINDSIDE -- the lens and the sensor.  TRAILER.md 9.
//
// One compute pass, run as a CompositorEffect at POST_TRANSPARENT, which means
// it operates on the HDR *linear* colour buffer BEFORE tonemapping. That is not
// a convenience: it is where these things physically happen.
//
//   distortion, chromatic aberration, vignetting   the lens, on radiance
//   motion blur                                    integration over the shutter
//   shot / read noise                              the sensor, on electrons
//
// and only then does AgX turn the result into a picture. Two things fall out
// for free that a post-tonemap filter has to fake:
//   * grain lands in the shadows and nowhere else, because AgX's slope is steep
//     in the toe and flat in the shoulder. No shadow mask is needed.
//   * vignetting rolls a blown near wall down into the shoulder instead of
//     multiplying an already-clipped value.
//
// Order along the light path: the lens disperses and distorts, the sensor
// integrates, then the sensor adds its own noise. The taps below therefore
// carry the chromatic offset into the motion-blur integral rather than after it.
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
	int taps;
	int flags;          // 1 distort  2 ca  4 vignette  8 grain  16 motion blur
} p;

#define F_DISTORT   1
#define F_CA        2
#define F_VIGNETTE  4
#define F_GRAIN     8
#define F_MBLUR    16
#define F_VELDBG   32
#define F_BLIT     64

float hash13(vec3 v) {
	v = fract(v * 0.1031);
	v += dot(v, v.yzx + 33.33);
	return fract((v.x + v.y) * v.z);
}

void main() {
	ivec2 gid = ivec2(gl_GlobalInvocationID.xy);
	if (gid.x >= int(p.size.x) || gid.y >= int(p.size.y)) return;

	vec2 uv = (vec2(gid) + 0.5) / p.size;

	// Godot's scene colour buffer is not created with CAN_COPY_TO, so the
	// result cannot be blitted back into it with texture_copy. The effect
	// therefore runs as two dispatches: the work into a scratch target, then
	// this 1:1 store back. Measured at 0.05-0.10 ms of the pass.
	if ((p.flags & F_BLIT) != 0) {
		imageStore(dst_colour, gid, vec4(texture(src_colour, uv).rgb, 1.0));
		return;
	}

	// aspect-corrected radial coordinate, 1.0 at the corner
	float aspect = p.size.x / p.size.y;
	vec2 c = (uv - 0.5) * vec2(aspect, 1.0);
	float rn = length(c) / length(vec2(aspect, 1.0) * 0.5);

	// ---- lens distortion ------------------------------------------------
	// r_src = r * (1 + k r^2), then overscanned by 1/(1+k) so the corner maps
	// to the corner and no black wedge appears. Sub-percent, per TRAILER 9.
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
		// bound it: a bad depth sample must not smear the frame
		vec2 vpx = vel * p.size;
		float vl = length(vpx);
		if (vl > p.max_blur_px) vel *= p.max_blur_px / vl;
		if (vl < 0.35) vel = vec2(0.0);   // under a third of a pixel is nothing
	}

	// ---- chromatic aberration, carried into the shutter integral --------
	// Lateral CA is a magnification difference: red images larger than blue.
	// Zero at the axis, growing with radius. Edges only, a pixel or two.
	vec2 cadir = vec2(0.0);
	if ((p.flags & F_CA) != 0) {
		vec2 rd = uvl - 0.5;
		cadir = rd * (p.ca_px / max(length(rd * p.size), 1.0)) * rn;
	}

	// one-frame diagnostic: is the reprojection's Y in the same sense as the
	// texture's? A dolly-in must give vel.y < 0 (red) in the top half.
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

	// ---- vignetting ------------------------------------------------------
	// Natural (cos^4) falloff, derived from the focal length on the CPU and
	// handed in as cos4_corner, then partly corrected the way a real lens
	// design corrects it. No free "amount" knob: a 21 mm darkens its corners
	// and a 100 mm does not, which is what a lens does.
	if ((p.flags & F_VIGNETTE) != 0) {
		float t = rn * rn;
		float v = mix(1.0, p.cos4_corner, t * t * 0.5 + t * 0.5);
		col *= mix(1.0, v, p.vig_k);
	}

	// ---- the sensor ------------------------------------------------------
	// Shot noise is Poisson: sigma = sqrt(S / full_well). Read noise is a
	// constant floor. So the signal-to-noise ratio is worst in the near-black,
	// which is nine-tenths of this game, and best in the lamp pool. That is
	// TRAILER 9's "grain in the shadows, not in the highlights" arrived at
	// from the sensor rather than from a mask.
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
