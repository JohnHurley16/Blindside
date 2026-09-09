// ---------------------------------------------------------------------------
// BLINDSIDE assayer spike -- the CLEAR rig's ground, and NOTHING ELSE.
//
// This is the concept board's studio floor: "a grey ground ruled at the 1.2 m
// industrial module with the 0.6 m rail gauge as two finer lines". It exists
// so a 6.6 m machine can be SEEN before it is lit, and it is not the game.
// Every frame made over it is named `clear_` for exactly that reason.
// ---------------------------------------------------------------------------
shader_type spatial;
render_mode blend_mix, depth_draw_opaque, cull_back, diffuse_burley, specular_schlick_ggx;

uniform vec3 ground = vec3(0.150, 0.150, 0.152);
uniform float module_m = 1.2;
uniform float cell_m = 0.6;

varying vec3 wpos;

void vertex() { wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz; }

float rule(vec2 p, float period, float w) {
	vec2 g = abs(fract(p / period - 0.5) - 0.5) * period;
	vec2 fw = fwidth(p) * 1.2 + 0.0005;
	vec2 l = 1.0 - smoothstep(vec2(w), vec2(w) + fw, g);
	return max(l.x, l.y);
}

void fragment() {
	vec3 c = ground;
	c = mix(c, ground * 0.62, rule(wpos.xz, cell_m, 0.004));
	c = mix(c, ground * 1.75, rule(wpos.xz, module_m, 0.008));
	// the datum lines through the origin, so the machine's own axes are legible
	vec2 ax = abs(wpos.xz);
	float axl = 1.0 - smoothstep(0.010, 0.010 + fwidth(wpos.x) * 1.2, min(ax.x, ax.y));
	c = mix(c, vec3(0.36, 0.36, 0.37), axl);
	// the 9-cell lethal contour, drawn ONLY here, as a studio annotation
	float d = length(wpos.xz);
	float ring = 1.0 - smoothstep(0.014, 0.014 + fwidth(d) * 1.4, abs(d - 5.40));
	c = mix(c, vec3(0.30, 0.30, 0.31), ring * 0.85);
	ALBEDO = c;
	ROUGHNESS = 0.92;
	METALLIC = 0.0;
	SPECULAR = 0.5;
}
