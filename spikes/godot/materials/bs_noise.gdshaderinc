// ---------------------------------------------------------------------------
// BLINDSIDE -- procedural noise library, shared by every material in the family.
//
// Everything here is a pure function of a world-space position. Nothing is
// sampled from a bitmap, nothing needs a UV, and nothing needs a tangent
// basis. ART-DIRECTION 3.2.
// ---------------------------------------------------------------------------
#ifndef BS_NOISE_INC
#define BS_NOISE_INC

// Integer bit-mixing hash. The fract(sin(dot())) family leaves a visible
// square lattice at high frequency -- the "QR code" artefact the cave spike
// hit -- and it is the single most common cause of a procedural surface
// reading as fabric rather than as stone.
uvec3 bs_uhash3(uvec3 x) {
	x = x * 1664525u + 1013904223u;
	x.x += x.y * x.z; x.y += x.z * x.x; x.z += x.x * x.y;
	x ^= x >> 16u;
	x.x += x.y * x.z; x.y += x.z * x.x; x.z += x.x * x.y;
	return x;
}

// one float in [0,1) from a lattice point
float bs_h1(vec3 i) {
	return float(bs_uhash3(uvec3(ivec3(i) + 32768)).x & 0xFFFFFFu) / 16777216.0;
}

// three floats in [-1,1] from a lattice point -- gradient vectors
vec3 bs_h3(vec3 i) {
	uvec3 u = bs_uhash3(uvec3(ivec3(i) + 32768));
	return vec3(u & uvec3(0xFFFFFu)) * (2.0 / float(0xFFFFF)) - 1.0;
}

// Gradient (Perlin) noise, quintic interpolant, returns roughly [-0.7, 0.7].
// Gradient rather than value noise: value noise puts its extrema ON the
// integer lattice, which is exactly the axis-aligned blockiness that makes a
// procedural rock look woven.
float bs_gnoise(vec3 p) {
	vec3 i = floor(p);
	vec3 f = p - i;
	vec3 u = f * f * f * (f * (f * 6.0 - 15.0) + 10.0);
	float n000 = dot(bs_h3(i + vec3(0, 0, 0)), f - vec3(0, 0, 0));
	float n100 = dot(bs_h3(i + vec3(1, 0, 0)), f - vec3(1, 0, 0));
	float n010 = dot(bs_h3(i + vec3(0, 1, 0)), f - vec3(0, 1, 0));
	float n110 = dot(bs_h3(i + vec3(1, 1, 0)), f - vec3(1, 1, 0));
	float n001 = dot(bs_h3(i + vec3(0, 0, 1)), f - vec3(0, 0, 1));
	float n101 = dot(bs_h3(i + vec3(1, 0, 1)), f - vec3(1, 0, 1));
	float n011 = dot(bs_h3(i + vec3(0, 1, 1)), f - vec3(0, 1, 1));
	float n111 = dot(bs_h3(i + vec3(1, 1, 1)), f - vec3(1, 1, 1));
	return mix(mix(mix(n000, n100, u.x), mix(n010, n110, u.x), u.y),
	           mix(mix(n001, n101, u.x), mix(n011, n111, u.x), u.y), u.z);
}

// value noise -- cheaper, used where the lattice will not show (masks, stains)
float bs_vnoise(vec3 p) {
	vec3 i = floor(p);
	vec3 f = p - i;
	f = f * f * (3.0 - 2.0 * f);
	float n000 = bs_h1(i + vec3(0, 0, 0));
	float n100 = bs_h1(i + vec3(1, 0, 0));
	float n010 = bs_h1(i + vec3(0, 1, 0));
	float n110 = bs_h1(i + vec3(1, 1, 0));
	float n001 = bs_h1(i + vec3(0, 0, 1));
	float n101 = bs_h1(i + vec3(1, 0, 1));
	float n011 = bs_h1(i + vec3(0, 1, 1));
	float n111 = bs_h1(i + vec3(1, 1, 1));
	return mix(mix(mix(n000, n100, f.x), mix(n010, n110, f.x), f.y),
	           mix(mix(n001, n101, f.x), mix(n011, n111, f.x), f.y), f.z);
}

// fractal sums, explicit octave counts so the cost is legible at the call site
float bs_fbm2(vec3 p) { return bs_gnoise(p) * 0.60 + bs_gnoise(p * 2.03 + 17.3) * 0.30; }
float bs_fbm3(vec3 p) {
	return bs_gnoise(p) * 0.53 + bs_gnoise(p * 2.03 + 17.3) * 0.27
	     + bs_gnoise(p * 4.11 + 41.7) * 0.13;
}
float bs_fbm4(vec3 p) {
	return bs_gnoise(p) * 0.50 + bs_gnoise(p * 2.03 + 17.3) * 0.25
	     + bs_gnoise(p * 4.11 + 41.7) * 0.13 + bs_gnoise(p * 8.07 + 73.1) * 0.065;
}

// ridged noise -- the sharp-crested variant. Freshly broken rock is ridged;
// weathered rock is not. This is the single cheapest cue for that difference.
float bs_ridge(vec3 p) {
	float a = 1.0 - abs(bs_gnoise(p) * 2.0);
	float b = 1.0 - abs(bs_gnoise(p * 2.07 + 11.1) * 2.0);
	return a * 0.62 + b * a * 0.30;
}

// Domain warp. Un-warped voronoi reads as crazed pottery: every cell the same
// size, every joint the same curvature.
vec3 bs_warp(vec3 p, float k) {
	if (k <= 0.001) { return p; }
	return p + vec3(bs_gnoise(p * 0.63), bs_gnoise(p * 0.63 + 13.0),
	                bs_gnoise(p * 0.63 + 27.0)) * k;
}

// Cellular / voronoi. Returns (F1, F2-F1, cell hash 0..1).
// F1     -> domed grains (aggregate, ballast, gravel)
// F2-F1  -> joint and crack lines (rock, concrete, mud crack)
vec3 bs_cell(vec3 p) {
	vec3 i = floor(p);
	vec3 f = p - i;
	float f1 = 9.0;
	float f2 = 9.0;
	float id = 0.0;
	for (int z = -1; z <= 1; z++) {
		for (int y = -1; y <= 1; y++) {
			for (int x = -1; x <= 1; x++) {
				vec3 g = vec3(float(x), float(y), float(z));
				vec3 o = bs_h3(i + g) * 0.5 + 0.5;
				float d = length(g + o - f);
				if (d < f1) { f2 = f1; f1 = d; id = bs_h1(i + g + 7.0); }
				else if (d < f2) { f2 = d; }
			}
		}
	}
	return vec3(f1, f2 - f1, id);
}

// 2D cellular on a plane -- half the samples of the 3D case. Used where the
// pattern is genuinely planar (mud cracks on a floor, plate seams).
vec3 bs_cell2(vec2 p) {
	vec2 i = floor(p);
	vec2 f = p - i;
	float f1 = 9.0;
	float f2 = 9.0;
	float id = 0.0;
	for (int y = -1; y <= 1; y++) {
		for (int x = -1; x <= 1; x++) {
			vec2 g = vec2(float(x), float(y));
			vec2 o = bs_h3(vec3(i + g, 0.0)).xy * 0.5 + 0.5;
			float d = length(g + o - f);
			if (d < f1) { f2 = f1; f1 = d; id = bs_h1(vec3(i + g, 3.0)); }
			else if (d < f2) { f2 = d; }
		}
	}
	return vec3(f1, f2 - f1, id);
}

// triplanar blend weights from a world normal
vec3 bs_tri_w(vec3 n, float sharp) {
	vec3 w = pow(abs(n), vec3(sharp));
	return w / max(w.x + w.y + w.z, 1e-4);
}

#endif
