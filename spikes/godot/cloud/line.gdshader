// Believed trail, beacon chain, uncertainty ellipse, ghost: unlit emission, nothing else.
shader_type spatial;
render_mode unshaded, shadows_disabled, cull_disabled, fog_disabled,
	depth_draw_never, depth_test_disabled, blend_add;
uniform vec3 u_col : source_color = vec3(0.624, 0.910, 1.000);
uniform float u_level = 0.5;
varying vec4 v_c;
void vertex() {
	v_c = COLOR;
}
void fragment() {
	ALBEDO = u_col * v_c.rgb;
	ALPHA = u_level * v_c.a;
}
