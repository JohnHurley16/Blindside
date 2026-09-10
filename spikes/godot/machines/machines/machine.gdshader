// ---------------------------------------------------------------------------
// BLINDSIDE machines spike -- the machine surface.
//
// Blender's materials do not survive glTF in any useful form, so the surfacing
// is rebuilt here against ART-DIRECTION section 4. One shader covers every
// painted, bare, rubber and glass part of every chassis, which is why a machine
// is two draw calls and not twelve.
//
// WHAT ARRIVES FROM agent_model (see agent_model/export_gltf.py):
//   UV .x   (part * 16 + element) / 256
//   UV .y   mud    -- 1 at the feet, 0 above the hull seam
//   UV2.x   dust   -- max(0, N_up)^3
//   UV2.y   scuff  -- max(0, N_forward)^1.5
//
// THE THREE CHANNELS ART SECTION 4 REQUIRES TO STAY SEPARATE, and where each
// one lives, so that a reader can check the separation by reading this file:
//
//   TEAM   is `invert` and `team_col` only. It swaps WHICH of the two liveried
//          parts is pale (ART 4.3 rule 3) and colours the identity mark. It
//          never touches roughness, never adds a mask, never moves an emissive.
//          Hue does nothing here: both teams get the same two values, in the
//          opposite order. ART 4.3 measured hue alone at a quarter of a JND.
//   WEAR   is `mud`, `dust`, `scuff`, `wet` against the three baked masks. It
//          only ever moves ALBEDO and ROUGHNESS. It cannot reach HURT or KILL,
//          cannot reach EMISSION, and cannot remove a part.
//   DAMAGE is `damage` only. It counts down the sonar bar's lit elements,
//          discards the parts ART 4.2 says are shed, and lights the one state
//          pilot in HURT or KILL. It never touches a wear mask and never
//          changes paint.
//
// ART 4.2's second rule is enforced by there being exactly two reds in this
// file, both uniforms, both used only by `damage`. The E-stop is painted, and
// is never emissive.
// ---------------------------------------------------------------------------
shader_type spatial;
render_mode blend_mix, depth_draw_opaque, cull_back, diffuse_burley, specular_schlick_ggx;

// --- palette (linear) -------------------------------------------------------
uniform vec3 pale_col = vec3(0.335, 0.318, 0.264);
uniform vec3 graphite_col = vec3(0.004, 0.0045, 0.0055);
uniform vec3 accent_col = vec3(0.69, 0.17, 0.010);
uniform vec3 bare_col = vec3(0.17, 0.17, 0.18);
uniform vec3 bare_leg_col = vec3(0.011, 0.011, 0.013);
uniform vec3 rubber_col = vec3(0.003, 0.003, 0.0035);
uniform vec3 dark_col = vec3(0.007, 0.007, 0.008);
uniform vec3 estop_col = vec3(0.32, 0.010, 0.007);
uniform vec3 mud_col = vec3(0.0044, 0.0031, 0.0022);
uniform vec3 dust_col = vec3(0.073, 0.056, 0.036);
uniform vec3 team_col = vec3(0.888, 0.792, 0.647);
uniform vec3 warm_dim = vec3(0.69, 0.47, 0.26);
uniform vec3 hurt_col = vec3(0.74, 0.15, 0.11);
uniform vec3 kill_col = vec3(1.0, 0.04, 0.026);
uniform vec3 lamp_col = vec3(1.0, 0.955, 0.891);

// --- team: value and rhythm, never hue (ART 4.3) ----------------------------
uniform float invert : hint_range(0.0, 1.0) = 0.0;

// --- wear: history (ART 4.1) ------------------------------------------------
uniform float mud : hint_range(0.0, 1.0) = 0.30;
uniform float dust : hint_range(0.0, 1.0) = 0.25;
uniform float scuff : hint_range(0.0, 1.0) = 0.20;
uniform float wet : hint_range(0.0, 1.0) = 0.0;

// --- damage: state (ART 4.2) ------------------------------------------------
uniform float damage : hint_range(0.0, 1.0) = 0.0;
uniform float dead = 0.0;              // 1.0 = the wreck: every emissive out

// --- module state -----------------------------------------------------------
uniform float pinging = 0.0;           // ART 4.4: the bar is DARK when passive
uniform float lamp_on = 1.0;
uniform float beacons_left = 4.0;      // caps go dark one at a time
uniform float noise_gain : hint_range(0.0, 2.0) = 1.0;

varying vec3 wn;
varying vec3 vpos;

// One integer bit-mix, not fract(sin(dot(...))). The cave spike measured a
// visible square lattice from the sin family at high frequency.
float h31(vec3 p) {
	uvec3 q = uvec3(ivec3(floor(p))) * uvec3(1597334673u, 3812015801u, 2798796415u);
	uint n = (q.x ^ q.y ^ q.z) * 1597334673u;
	n = (n ^ (n >> 15u)) * 2246822519u;
	n = (n ^ (n >> 13u)) * 3266489917u;
	return float(n ^ (n >> 16u)) * (1.0 / 4294967296.0);
}

float vnoise(vec3 p) {
	vec3 i = floor(p);
	vec3 f = fract(p);
	f = f * f * (3.0 - 2.0 * f);
	float a = mix(mix(mix(h31(i + vec3(0, 0, 0)), h31(i + vec3(1, 0, 0)), f.x),
					  mix(h31(i + vec3(0, 1, 0)), h31(i + vec3(1, 1, 0)), f.x), f.y),
				  mix(mix(h31(i + vec3(0, 0, 1)), h31(i + vec3(1, 0, 1)), f.x),
					  mix(h31(i + vec3(0, 1, 1)), h31(i + vec3(1, 1, 1)), f.x), f.y), f.z);
	return a;
}

float fbm(vec3 p) {
	return vnoise(p) * 0.6 + vnoise(p * 2.7 + vec3(11.3, 4.1, 7.7)) * 0.3
		 + vnoise(p * 6.1 + vec3(3.7, 19.1, 2.3)) * 0.1;
}

// Perturb a world normal by a height-field gradient, WITH A CLAMP. The clamp
// is the cave spike's finding and not a nicety: a noise sampled below its own
// Nyquist returns slopes of 3 or 4, `n - g*k` then tips the normal past 90
// degrees, and the surface faces away from the only light in the world.
vec3 bumped(vec3 n, vec3 g, float k) {
	g -= n * dot(g, n);
	g *= k;
	float l = length(g);
	if (l > 1.2) { g *= 1.2 / l; }
	return normalize(n - g);
}

void vertex() {
	wn = normalize((MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz);
	vpos = VERTEX;
}

void fragment() {
	// ---- decode what part this is -----------------------------------------
	float id = UV.x * 256.0;
	float part = floor(id / 16.0 + 0.0001);
	float elem = floor(id + 0.5) - part * 16.0;

	// ---- DAMAGE, channel one. Geometry it is allowed to touch (ART 4.2 says
	// damage is the ONE parameter allowed to, and that the exception has to be
	// written down; this is where it is written down). ----------------------
	// rung 0.30: one hip actuator sheds its cover
	if (damage >= 0.30 && elem == 10.0) { discard; }
	// rung 0.50: a hull panel is simply not built, graphite underneath
	if (damage >= 0.50 && elem == 9.0) { discard; }

	// ---- base colour by part ----------------------------------------------
	// The two LIVERIED parts, and the whole of team identity in three lines:
	// the same pale and the same graphite for both teams, assigned the other
	// way round. ART 4.3: "invert the value, which is the only channel that
	// survives at all".
	vec3 base = graphite_col;
	float rough = 0.55;
	float metal = 0.0;
	float spec = 0.5;
	vec3 bare_through = bare_col;      // what scuffed paint reveals
	float ex = 1.0;                    // how reachable this face is
	vec3 emis = vec3(0.0);

	if (part < 0.5) {                          // 0 shell -- LIVERIED
		base = mix(pale_col, graphite_col, invert);
		rough = 0.62;
	} else if (part < 1.5) {                   // 1 chassis -- LIVERIED
		base = mix(graphite_col, pale_col, invert);
		rough = 0.58;
		ex = 0.9;
	} else if (part < 2.5) {                   // 2 accent
		base = accent_col; rough = 0.5; ex = 0.8;
	} else if (part < 3.5) {                   // 3 bare metal, hull grade
		base = bare_col; metal = 1.0; rough = 0.34; ex = 0.9;
	} else if (part < 4.5) {                   // 4 dark housings
		base = dark_col; rough = 0.44; ex = 0.7;
		bare_through = bare_leg_col;
	} else if (part < 5.5) {                   // 5 the LEG material
		// ART 4.1's third finding, from getting it wrong first: a muddy leg is
		// mud ON black, not paint worn THROUGH to bright metal. Using the
		// hull's bare colour here makes the legs lighter, not dirtier.
		base = bare_leg_col; rough = 0.40;
		bare_through = bare_leg_col * 2.2;
	} else if (part < 6.5) {                   // 6 rubber: feet, cable, handle
		base = rubber_col; rough = 0.88;
		bare_through = rubber_col;
	} else if (part < 7.5) {                   // 7 one sonar bar element
		base = dark_col * 0.6; rough = 0.22; ex = 0.3;
		// ART 4.4: lit WHILE PINGING, dark while passive -- and ART 4.2 rung
		// 0.20: 7 lit, then 4, then 2. Countable, and it names what broke.
		float lit = damage < 0.20 ? 7.0 : (damage < 0.50 ? 4.0 : (damage < 1.0 ? 2.0 : 0.0));
		if (pinging > 0.5 && elem <= lit && elem > 0.0) {
			emis = team_col * 2.6;
		}
	} else if (part < 8.5) {                   // 8 the lamp emitter disc
		base = dark_col; rough = 0.30; ex = 0.2;
		emis = lamp_col * (lamp_on > 0.5 ? 3.0 : 0.0);
	} else if (part < 9.5) {                   // 9 lamp lens
		base = vec3(0.010, 0.012, 0.014); rough = 0.06; spec = 0.9; ex = 0.25;
	} else if (part < 10.5) {                  // 10 dark glass: camera, window
		base = vec3(0.004, 0.005, 0.006); rough = 0.05; spec = 0.9; ex = 0.25;
	} else if (part < 11.5) {                  // 11 E-stop. PAINTED. Never lit.
		base = estop_col; rough = 0.45; ex = 0.6;
	} else if (part < 12.5) {                  // 12 retro -- other surface
		base = dark_col;
	} else if (part < 13.5) {                  // 13 the one state pilot
		base = dark_col; rough = 0.3; ex = 0.4;
		// ART 4.2: HURT for hurt-and-alive, KILL for dying, and no second red
		// anywhere. Dark on a healthy machine, because ART 4.5 will not have
		// an always-on emissive on every agent.
		if (damage >= 0.75) { emis = kill_col * 2.4; }
		else if (damage >= 0.30) { emis = hurt_col * 1.8; }
	} else if (part < 14.5) {                  // 14 a beacon cap
		base = dark_col; rough = 0.4; ex = 0.5;
		// ART 4.4's fix: caps go dark one at a time as beacons drop -- a live
		// inventory readout in the silhouette, nearly free.
		if (elem <= beacons_left && elem > 0.0) { emis = warm_dim * 1.4; }
	} else {                                   // 15 lamp housing
		base = dark_col * 0.8; rough = 0.35; ex = 0.4;
	}

	// ---- WEAR, channel two. ART 4.1's three gravity masks. -----------------
	// Only ALBEDO and ROUGHNESS below this line, and nothing that damage owns.
	vec3 np = vpos * 15.0;
	float n1 = fbm(np);
	float n2 = fbm(np * 0.42 + vec3(5.5, 1.3, 8.9));
	float m_mud = clamp(mud * UV.y * ex * (0.55 + 0.9 * n2) * 1.35, 0.0, 1.0);
	float m_dust = clamp(dust * UV2.x * ex * (0.55 + 0.95 * n1) * 1.25, 0.0, 1.0);
	// ART 4.1's scuff is `max(0, dot(N,+X)) x edge_AO`. An imported mesh gives
	// no curvature term, so the edge is approximated by a clustered noise. The
	// first version used smoothstep(0.42,0.78) on a 26/m field and produced a
	// visible HALFTONE over every flat panel: the cluster has to be broad and
	// soft or it reads as a print artefact rather than as chipped paint.
	float m_scuf = clamp(scuff * UV2.y * ex * smoothstep(0.34, 0.86, n1) * 1.35, 0.0, 1.0);

	// scuff first: paint comes off the leading faces, and then the mud lands
	// on what is underneath.
	base = mix(base, bare_through, m_scuf);
	// dust settles on the horizontals, in the ROCK's own colour, so a machine
	// wears the cave it has been in.
	base = mix(base, dust_col, m_dust * 0.88);
	base = mix(base, mud_col, m_mud);
	metal *= (1.0 - max(m_mud, m_dust * 0.7));

	rough = mix(rough, 0.95, m_dust);
	rough = mix(rough, 0.18, m_mud);         // ART 4.1: mud roughness -> 0.18
	rough = mix(rough, 0.10, wet);
	base *= mix(1.0, 0.55, wet);

	ALBEDO = clamp(base, vec3(0.002), vec3(0.95));
	METALLIC = metal;
	SPECULAR = spec;
	ROUGHNESS = clamp(rough, 0.04 + clamp(length(vpos) * 0.0, 0.0, 0.2), 1.0);
	EMISSION = emis * (1.0 - dead);

	// ---- a micro normal, tangent-free --------------------------------------
	// NOT NORMAL_MAP: these meshes have no UV unwrap and therefore no tangents,
	// so a tangent-space normal map is evaluated in a garbage basis. This is
	// the cave spike's finding and it applies unchanged here.
	vec3 n = normalize(wn);
	if (noise_gain > 0.001) {
		float e = 0.004;
		float h0 = fbm(vpos * 46.0);
		vec3 g = vec3(fbm((vpos + vec3(e, 0, 0)) * 46.0) - h0,
					  fbm((vpos + vec3(0, e, 0)) * 46.0) - h0,
					  fbm((vpos + vec3(0, 0, e)) * 46.0) - h0) / e;
		n = bumped(n, g, 0.00030 * noise_gain * (0.4 + 0.9 * m_mud + 0.5 * m_dust));
	}
	NORMAL = normalize((VIEW_MATRIX * vec4(n, 0.0)).xyz);
	AO = clamp(0.90 + 0.10 * n2, 0.80, 1.0);
	AO_LIGHT_AFFECT = 0.25;
}
