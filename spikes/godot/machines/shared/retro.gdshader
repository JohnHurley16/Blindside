// ---------------------------------------------------------------------------
// BLINDSIDE machines spike -- the running lights.
//
// ART-DIRECTION 4.5 says resolve this before anything else in section 4, and
// recommends an answer: THE RUNNING LIGHTS ARE NOT LAMPS, THEY ARE
// RETROREFLECTIVE MARKINGS. A quiet agent is then genuinely dark until a
// rival's lamp finds it, at which point it lights up like a road sign, and the
// going-quiet tradeoff survives intact. That is what this shader implements,
// and it is the decision this spike made -- flagged in NOTES.md as needing a
// designer's yes.
//
// The vision board could only approximate this. Cycles has no retroreflector
// BSDF, so `machines_probe.py` bent the shading normal toward the viewer with
// `Geometry -> Incoming` and noted that it is "correct for the case that
// matters and wrong for a lamp far off the viewer's axis".
//
// GODOT DOES NOT NEED THE APPROXIMATION. A `light()` function is handed both
// LIGHT (fragment toward the source) and VIEW (fragment toward the eye), so a
// retroreflective lobe is one line and it is the real thing: sheeting returns
// light back along the direction it arrived, so a viewer sees it exactly to
// the extent their eye is near that source. A lamp 90 degrees off the camera
// returns its light to the lamp and nothing to the camera, which is what real
// prism sheeting does and what the Cycles version could not express.
//
// RHYTHM, NOT HUE. ART 4.3 concludes that value is necessary and not
// sufficient, and that "the rest of the separation has to come from layout and
// rhythm -- which parts are pale, and the blink pattern of the emissives".
// With no always-on emissive left to blink, this spike reads rhythm SPATIALLY:
// the player's strip is continuous, the rival's is dashed on the same pitch as
// its own length. Both are the same value and the same size. That is a guess
// and it is in the list.
// ---------------------------------------------------------------------------
shader_type spatial;
render_mode blend_mix, depth_draw_opaque, cull_back, diffuse_lambert, specular_disabled;

uniform vec3 team_col = vec3(0.888, 0.792, 0.647);
uniform vec3 dark_col = vec3(0.010, 0.010, 0.012);
uniform float retro_gain : hint_range(0.0, 60.0) = 26.0;
uniform float retro_tightness : hint_range(1.0, 200.0) = 26.0;
uniform float rhythm : hint_range(0.0, 1.0) = 0.0;   // 0 continuous, 1 dashed
uniform float dash_pitch = 34.0;
uniform float dead = 0.0;
// ART 4.5's stated fallback, kept switchable so the two can be photographed
// side by side: strip strength 8 -> 1.5, status sphere deleted, and an
// emission of 0.1 registered in the sim so the tell is real and costed.
uniform float emissive_mode = 0.0;
uniform float emissive_strength = 1.5;

varying vec3 vpos;

void vertex() {
	vpos = VERTEX;
}

void fragment() {
	// the dash is cut along the strip's own long axis, which on every chassis
	// is the machine's X
	float d = rhythm > 0.5 ? step(0.35, fract(vpos.x * dash_pitch)) : 1.0;
	if (d < 0.5) {
		ALBEDO = dark_col;
		ROUGHNESS = 0.8;
		METALLIC = 0.0;
		EMISSION = vec3(0.0);
	} else {
		ALBEDO = dark_col * 1.6;
		ROUGHNESS = 0.35;
		METALLIC = 0.0;
		EMISSION = team_col * emissive_strength * emissive_mode * (1.0 - dead);
	}
	SPECULAR = 0.2;
}

void light() {
	// `return` is not allowed in a light() processor (Godot rejects the shader
	// outright and silently falls the material back), so the gap in the dash
	// and the emissive fallback are masks, not early exits.
	float d = rhythm > 0.5 ? step(0.35, fract(vpos.x * dash_pitch)) : 1.0;
	float active = d * (1.0 - step(0.5, emissive_mode));
	float facing = max(dot(NORMAL, LIGHT), 0.0);
	// LIGHT points from the fragment toward the source; VIEW points from the
	// fragment toward the eye. Sheeting returns along the incoming ray, so the
	// return the eye receives peaks where those two coincide.
	float lobe = pow(max(dot(normalize(LIGHT), normalize(VIEW)), 0.0), retro_tightness);
	DIFFUSE_LIGHT += LIGHT_COLOR * ATTENUATION * facing * lobe * retro_gain * team_col * active;
	// a little plain diffuse so the strip is a physical object in a raking
	// light rather than a hole
	DIFFUSE_LIGHT += LIGHT_COLOR * ATTENUATION * facing * mix(0.04, 0.06, active) * team_col;
}
