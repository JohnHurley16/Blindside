// The baseline technique, for the table only: PRIMITIVE_POINTS with a screen-space
// point size. Cheapest possible, and it is what ART 8.2 explicitly rules out -- a
// fixed angular size is a fog, not a survey. Kept so the cost of being right is known.
shader_type spatial;
render_mode unshaded, shadows_disabled, fog_disabled, depth_draw_never,
	depth_test_disabled, blend_add;
uniform float u_now = 480.0;
uniform float u_px = 2.4;
uniform float u_gain = 1.0;
uniform float u_age_full_s = 480.0;
uniform float u_age_floor = 0.35;
uniform vec3 u_sensed : source_color = vec3(0.388, 0.839, 0.969);
uniform vec3 u_walked : source_color = vec3(0.180, 0.282, 0.329);
varying vec3 v_col;
varying float v_a;
void vertex() {
	float conf = COLOR.r;
	float tp = COLOR.g * 1000.0;
	float src = COLOR.b * 8.0;
	POINT_SIZE = u_px * (0.6 + 0.8 * conf);
	bool walked = src > 0.5 && src < 1.5;
	float age = max(u_now - tp, 0.0);
	float dim = mix(1.0, u_age_floor, clamp(age / u_age_full_s, 0.0, 1.0));
	float a = (0.35 + 0.50 * conf) * dim;
	v_col = (walked ? u_walked * 0.34 : u_sensed) * u_gain;
	v_a = a;
	if (tp > u_now) {
		v_a = 0.0;          // see cloud_body: a conditional POSITION write kills the shader
		POINT_SIZE = 1.0;
	}
}
void fragment() {
	ALBEDO = v_col;
	ALPHA = v_a;
}
