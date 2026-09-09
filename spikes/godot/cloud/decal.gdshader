// The floor decal: a dark-cyan wash at z = 0 wherever the believed map has a return.
// ART 8.2 -- the only belief element with area, and what makes drift read as a SHAPE
// drifting rather than as scatter moving. One quad per occupied bin, additive, flat.
shader_type spatial;
render_mode unshaded, shadows_disabled, cull_disabled, fog_disabled,
	depth_draw_never, depth_test_disabled, blend_add;
uniform vec3 u_col : source_color = vec3(0.180, 0.282, 0.329);
uniform float u_level = 0.25;
varying vec2 v_uv;
void vertex() {
	v_uv = UV * 2.0 - 1.0;
}
void fragment() {
	// Quads are drawn at twice the bin pitch with a radial falloff, so neighbouring bins
	// overlap and sum into a continuous wash. A hard quad per bin reads as a mosaic and
	// competes with the points, which is what the Blender board's director frames did.
	float d = 1.0 - clamp(dot(v_uv, v_uv), 0.0, 1.0);
	ALBEDO = u_col;
	ALPHA = u_level * d * d;
}
