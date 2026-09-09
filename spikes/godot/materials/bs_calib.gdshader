// The calibration swatch. Emits an exact LINEAR value with no lighting, no
// albedo and no specular, so that with the tone mapper set to LINEAR at
// exposure 1.0 the framebuffer value IS the number, and a screenshot can be
// measured rather than admired.
shader_type spatial;
render_mode unshaded, depth_draw_opaque, cull_back;

uniform vec3 value_linear = vec3(0.18);
uniform float ramp = 0.0;          // 0 flat, 1 horizontal linear ramp 0..1
uniform float ramp_srgb = 0.0;     // 1 => ramp is in perceptual (sRGB) steps
uniform float ticks = 0.0;         // draw tick marks every 0.1

void fragment() {
	vec3 c = value_linear;
	if (ramp > 0.5) {
		float x = clamp(UV.x, 0.0, 1.0);
		float v = x;
		if (ramp_srgb > 0.5) {
			// perceptual steps: what the eye reads as evenly spaced
			v = pow(x, 2.2);
		}
		c = vec3(v);
		if (ticks > 0.5 && UV.y > 0.80) {
			float m = abs(fract(x * 10.0 + 0.5) - 0.5);
			if (m < 0.004) { c = vec3(0.9, 0.25, 0.05); }
		}
	}
	// `unshaded` ignores EMISSION entirely and outputs ALBEDO, which is why
	// the reference ramp came out as a black bar the first time. ALBEDO set
	// from a shader is already linear, so this value reaches the framebuffer
	// unchanged and a LINEAR tone mapper writes it into the PNG unchanged.
	ALBEDO = c;
}
