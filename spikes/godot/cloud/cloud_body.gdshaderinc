// One belief point = one world-space oriented disc, facing back along the ray the
// return came from. ART-DIRECTION 8.2. Unlit, shadowless, emission only, never meshed.
//
// The whole of drift / fix / spoof lives in this vertex shader and costs nothing per
// frame, because a phase1 point is moved by AT MOST ONE fix (proved in export_belief.py).
// Each instance therefore carries two positions and two normals; the scrub time picks.
//
// Instance packing (MultiMesh TRANSFORM_3D + custom data; the node is at identity, so
// MODEL_MATRIX is the raw instance transform and its columns are free storage):
//   column 0 = p1 - p0   what the fix did to this point, in metres
//   column 1 = n0        sensor -> hit before the fix, UNNORMALISED: its length is range
//   column 2 = n1        the same after it
//   origin   = p0        where it was believed to be when it was measured
//   custom   = (confidence, t_placed, t_fix or -1, source)
//
// The quad's corner comes from UV, not from VERTEX, because the basis above is not a
// rotation and world_vertex_coords hands VERTEX in already multiplied by it.

uniform float u_now = 480.0;
uniform float u_disc_m = 0.045;        // 45 mm, the middle of the direction's 40-50
// THE DISC IS THE SENSOR FOOTPRINT, and a footprint is range x beamwidth. phase1's sonar
// fires 60 rays over 120 deg (2.0 deg apart, 1.2 deg of bearing noise) out to 30 cells;
// its lidar fires 90 over 360 (4.0 deg) out to 18. So the patch a return could have come
// off is 0.2-0.7 m across, five to fifteen times ART 8.2's constant 45 mm. Sizing by the
// beam is both more honest and the thing that makes a bank of returns read as a surface.
// Set u_beam_rad = 0 for the direction's literal constant-size disc.
uniform float u_beam_rad = 0.035;      // 2.0 deg, phase1 sonar ray spacing
uniform float u_disc_max_m = 0.9;
uniform float u_size_conf = 0.45;      // size as the weak second confidence channel
uniform float u_ease_s = 0.7;          // a fix lands in one sim tick; the eye needs 0.7 s
uniform float u_age_knee_s = 150.0;   // age reaches the floor here, not at t_end
uniform float u_age_floor = 0.35;      // an old return is dim, and it never re-registers
uniform float u_gain = 1.0;
uniform float u_emit_sensed = 1.0;
uniform float u_emit_walked = 1.0;     // WALKED is dark BY ITS COLOUR; do not double-dim it
uniform vec3 u_sensed : source_color = vec3(0.388, 0.839, 0.969);   // #63D6F7 SENSED
uniform vec3 u_walked : source_color = vec3(0.180, 0.282, 0.329);   // #2E4854 WALKED
uniform float u_min_px = 1.35;         // edge-on floor, in pixels. 0 disables it.
uniform vec2 u_vp = vec2(1920.0, 1080.0);
uniform float u_walked_flat = 0.0;     // 1 = walked discs lie flat on the floor
uniform float u_epoch_split = -1.0;    // >= 0: colour by which side of this fix time
uniform vec3 u_before : source_color = vec3(0.388, 0.839, 0.969);
uniform vec3 u_after : source_color = vec3(0.388, 0.839, 0.969);
uniform float u_epoch_only = 0.0;      // 1 = hide everything the split does not name
uniform float u_solid = 0.0;

varying vec3 v_col;
varying float v_a;
varying vec2 v_c;

void vertex() {
	vec3 p0 = MODEL_MATRIX[3].xyz;
	vec3 dp = MODEL_MATRIX[0].xyz;
	vec3 n0 = MODEL_MATRIX[1].xyz;
	vec3 n1 = MODEL_MATRIX[2].xyz;
	float conf = INSTANCE_CUSTOM.x;
	float tp = INSTANCE_CUSTOM.y;
	float tf = INSTANCE_CUSTOM.z;
	float src = INSTANCE_CUSTOM.w;
	vec2 corner = UV * 2.0 - 1.0;
	v_c = corner;

	bool walked = src > 0.5 && src < 1.5;
	bool hidden = tp > u_now;
	vec3 col = u_sensed;
	float emit = u_emit_sensed;
	if (u_epoch_split >= 0.0) {
		col = tp <= u_epoch_split ? u_before : u_after;
		if (u_epoch_only > 0.5 && walked) {
			hidden = true;
		}
	}

	float w = 0.0;
	if (tf >= 0.0 && u_now >= tf) {
		w = clamp((u_now - tf) / max(u_ease_s, 1e-4), 0.0, 1.0);
		w = 1.0 - pow(1.0 - w, 3.0);
	}
	vec3 p = p0 + dp * w;
	vec3 ray = mix(n0, n1, w);
	float range = max(length(ray), 1e-4);
	vec3 nrm = ray / range;
	if (walked && u_walked_flat > 0.5) {
		nrm = vec3(0.0, 1.0, 0.0);
	}

	vec3 up = abs(nrm.y) > 0.9 ? vec3(1.0, 0.0, 0.0) : vec3(0.0, 1.0, 0.0);
	vec3 tx = normalize(cross(up, nrm));
	vec3 ty = cross(nrm, tx);
	float r = max(u_disc_m, min(range * u_beam_rad * 0.5, u_disc_max_m));
	r *= (1.0 - u_size_conf + u_size_conf * 2.0 * conf);
	vec3 world = p + (tx * corner.x + ty * corner.y) * r;

	// The edge-on floor. A disc facing back along a horizontal ray IS a vertical plane,
	// so from any high camera it is a sliver and the survey vanishes -- which is exactly
	// what went wrong in the Blender board's director frames. Widen it in SCREEN space
	// only, and only up to about a pixel, so the orientation stays honest and a bank of
	// discs still reads as a surface. It says "a hit is here"; it does not fake a normal.
	if (u_min_px > 0.0) {
		vec4 c0 = VIEW_MATRIX * vec4(p, 1.0);
		vec4 h0 = PROJECTION_MATRIX * c0;
		if (h0.w > 0.001) {
			vec4 hx = PROJECTION_MATRIX * (c0 + vec4(mat3(VIEW_MATRIX) * (tx * r), 0.0));
			vec4 hy = PROJECTION_MATRIX * (c0 + vec4(mat3(VIEW_MATRIX) * (ty * r), 0.0));
			vec2 s0 = h0.xy / h0.w * u_vp * 0.5;
			vec2 ex = hx.xy / hx.w * u_vp * 0.5 - s0;
			vec2 ey = hy.xy / hy.w * u_vp * 0.5 - s0;
			float lx = max(length(ex), 1e-6);
			float ly = max(length(ey), 1e-6);
			float kx = clamp(u_min_px / lx, 1.0, 60.0);
			float ky = clamp(u_min_px / ly, 1.0, 60.0);
			world = p + (tx * corner.x * kx + ty * corner.y * ky) * r;
		}
	}
	VERTEX = world;

	// One confidence channel: alpha. Size is the weak second. No third colour.
	float age = max(u_now - tp, 0.0);
	float dim = mix(1.0, u_age_floor, clamp(age / max(u_age_knee_s, 1e-3), 0.0, 1.0));
	float a = (0.35 + 0.50 * conf) * dim;
	if (walked) {
		if (u_epoch_split < 0.0) {
			col = u_walked;
		}
		emit = u_emit_walked;
		a = 0.55 * dim;
	}
	v_col = col * emit * u_gain;
	v_a = a;

	// Not measured yet at this scrub time: collapse the quad to a point, which produces
	// no fragments. It must NOT be done by writing POSITION: Godot defines
	// OVERRIDE_POSITION for the whole shader as soon as POSITION is assigned ANYWHERE,
	// so a conditional write silently sends every other vertex to an uninitialised clip
	// position and the entire cloud disappears. That cost this spike an hour.
	if (hidden) {
		v_a = 0.0;
		v_col = vec3(0.0);
		VERTEX = p0;
	}
}

void fragment() {
	// a disc, not a square. Soft-edged because a 45 mm disc is two pixels across at
	// twelve metres and a hard 2 px quad crawls as the camera orbits.
	// NOTE: under `unshaded` Godot outputs ALBEDO and drops EMISSION entirely, so the
	// emissive colour goes in ALBEDO and the intensity in ALPHA (blend_add is
	// SRC_ALPHA, ONE, so ALBEDO * ALPHA is exactly the light this disc adds).
	float d = smoothstep(1.0, 0.55, dot(v_c, v_c));
	if (d <= 0.002) {
		discard;
	}
	if (u_solid > 0.5) {
		ALBEDO = v_col * 1.4;
		ALPHA = clamp(v_a * d * 2.4, 0.0, 1.0);
	} else {
		ALBEDO = v_col;
		ALPHA = v_a * d;
	}
}
