// The TRUTH layer, and it exists in this spike only so the two registers can be put in
// one frame. Rendered, lit, shadowed-off, desaturated, and turned DOWN -- ART 8.3 says
// truth is the layer that gets dimmed, never belief. The light is the non-diegetic
// survey fill that PROCEDURAL-AND-GODOT 5.4(a) recommends, because you cannot expose
// black: with the diegetic lamp economy alone this layer is a black rectangle.
shader_type spatial;
render_mode cull_back, shadows_disabled, specular_disabled, fog_disabled;
uniform float u_level = 0.35;
uniform vec3 u_rock : source_color = vec3(0.235, 0.227, 0.216);
void fragment() {
	vec3 n = normalize(NORMAL);
	float f = 0.55 + 0.45 * abs(n.y);
	ALBEDO = u_rock * f * u_level;
	ROUGHNESS = 0.95;
	METALLIC = 0.0;
}
