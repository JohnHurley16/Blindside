extends Node3D
# BLINDSIDE -- the agent's own view, as a 3D point cloud.
#
# Everything drawn here comes from one phase1 match's Belief (seed 7, exported by
# export_belief.py). No World, no truth pose, no truth grid, except in the one mode
# that exists to compare the two registers and which turns TRUTH down, never belief.
#
# ART-DIRECTION 8.2 is the spec: hits not dots, 40-50 mm world-space discs facing back
# along the return ray, two classes only, alpha carries confidence, old returns dimmer
# and never re-registered, a floor decal where the count is above zero, emission only,
# unlit, shadowless, never meshed.

const CELL := 0.6
const WALL_H := 4.4                     # the truth stand-in crown, from the Blender board
const SENSED := Color(0.388, 0.839, 0.969)
const WALKED := Color(0.180, 0.282, 0.329)
const GHOST := Color(0.624, 0.910, 1.000)
const COOL_DIM := Color(0.227, 0.322, 0.376)
const LIE := Color(1.000, 0.824, 0.247)
const VOID := Color(0.0235, 0.0314, 0.0431)

var meta: Dictionary = {}
var mm: MultiMesh
var mmi: MultiMeshInstance3D
var mat_add: ShaderMaterial
var mat_solid: ShaderMaterial
var decal_mmi: MultiMeshInstance3D
var decal_mm: MultiMesh
var pts_mesh: MeshInstance3D          # the PRIMITIVE_POINTS baseline
var truth_root: Node3D
var lines: MeshInstance3D
var hud: Label
var cam: Camera3D

var n_loaded := 0
var buf_name := "seed7_real.mmbuf"
var now := 480.0
var playing := false
var play_rate := 8.0
var mode := "belief"                  # belief | both | truth
var solid := false
var technique := "multimesh"          # multimesh | points
var show_hud := true
var show_decal := true
var show_lines := true
var disc_m := 0.045
var beam_rad := 0.035
var disc_max := 0.9
var min_px := 1.6
var walked_flat := 0.0
var gain := 1.0
var epoch_split := -1.0
var epoch_only := 0.0
var age_knee := 150.0
var auto_gain := true
var auto_beam := true
var decal_bin := 0.6
var decal_level := 0.10
var frame_box := Vector4(0, 0, 0, 0)   # belief cells x0,x1,y0,y1; zero = no spatial filter
var frame_times := Vector2.ZERO        # only frame on points placed in this window
var frame_fill := 0.86
var frame_at := 0.0                    # fit at this time instead of `now`, so a
                                       # before/after pair shares one camera
var col_before := SENSED
var col_after := SENSED
var last_decal_t := -1.0e9

var orbit_target := Vector3.ZERO
var orbit_az := 0.6
var orbit_el := 0.55
var orbit_dist := 60.0
var orbit_fov := 55.0
var ortho := false
var ortho_size := 60.0

var belief_trail: PackedVector3Array = PackedVector3Array()
var belief_trail_t: PackedFloat32Array = PackedFloat32Array()
var beacons: Array = []
var fixes: Array = []
var load_ms := 0.0

var shots_only := false
var shot_filter := ""
var bench := false
var shot_dir := "shots"


func _ready() -> void:
	var args := OS.get_cmdline_user_args()
	for a in args:
		if a == "--shotsonly": shots_only = true
		elif a == "--bench": bench = true
		elif a.begins_with("--shot="): shots_only = true; shot_filter = a.substr(7)
		elif a.begins_with("--shotdir="): shot_dir = a.substr(10)
	_load_meta()
	_build_camera()
	_build_cloud()
	_build_decal()
	_build_lines()
	_build_hud()
	_frame_all()
	print("adapter: ", RenderingServer.get_video_adapter_name(),
		" | ", RenderingServer.get_video_adapter_vendor(),
		" | api ", RenderingServer.get_video_adapter_api_version())
	print("points: ", n_loaded, "  load ", "%.1f" % load_ms, " ms")
	_report_lights()
	if bench:
		call_deferred("_run_bench")
	elif shots_only:
		call_deferred("_run_shots")


# ---------------------------------------------------------------- data
func _load_meta() -> void:
	var f := FileAccess.open("res://data/seed7.json", FileAccess.READ)
	meta = JSON.parse_string(f.get_as_text())
	for p in meta.belief_trail:
		belief_trail.append(Vector3(p[0] * CELL, 0.06, -p[1] * CELL))
		belief_trail_t.append(p[2])
	beacons = meta.beacons
	fixes = meta.fixes
	print("match: seed ", meta.seed, "  ", meta.n_points, " points  t_end ", meta.t_end,
		"  fixes ", fixes.size(), "  spoof at ", meta.spoof_t)


func _quad_mesh() -> Mesh:
	var q := QuadMesh.new()
	q.size = Vector2(1.0, 1.0)
	return q


func _tri_mesh() -> Mesh:
	# three vertices circumscribing the unit disc: 25% fewer vertices, half the
	# triangles, same coverage. Measured against the quad in NOTES.
	var v := PackedVector3Array()
	var uv := PackedVector2Array()
	for i in 3:
		var a := TAU * float(i) / 3.0 + PI * 0.5
		var c := Vector2(cos(a), sin(a)) * 2.0
		v.append(Vector3(c.x, c.y, 0.0))
		uv.append((c + Vector2.ONE) * 0.5)
	var arr := []
	arr.resize(Mesh.ARRAY_MAX)
	arr[Mesh.ARRAY_VERTEX] = v
	arr[Mesh.ARRAY_TEX_UV] = uv
	var m := ArrayMesh.new()
	m.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arr)
	return m


func _build_cloud() -> void:
	mat_add = ShaderMaterial.new()
	mat_add.shader = load("res://cloud_add.gdshader")
	mat_solid = ShaderMaterial.new()
	mat_solid.shader = load("res://cloud_solid.gdshader")
	mat_solid.set_shader_parameter("u_solid", 1.0)
	mmi = MultiMeshInstance3D.new()
	mm = MultiMesh.new()
	mm.transform_format = MultiMesh.TRANSFORM_3D
	mm.use_custom_data = true
	mm.mesh = _quad_mesh()
	mmi.multimesh = mm
	mmi.material_override = mat_add
	mmi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	mmi.custom_aabb = AABB(Vector3(-200, -40, -200), Vector3(600, 120, 600))
	mmi.extra_cull_margin = 400.0
	add_child(mmi)

	pts_mesh = MeshInstance3D.new()
	pts_mesh.visible = false
	pts_mesh.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	pts_mesh.custom_aabb = AABB(Vector3(-200, -40, -200), Vector3(600, 120, 600))
	pts_mesh.extra_cull_margin = 400.0
	add_child(pts_mesh)
	_load_buffer(buf_name)


func _load_buffer(name: String) -> void:
	var t0 := Time.get_ticks_usec()
	var f := FileAccess.open("res://data/" + name, FileAccess.READ)
	if f == null:
		push_error("missing res://data/" + name)
		return
	var bytes := f.get_buffer(f.get_length())
	var floats := bytes.to_float32_array()
	var n := floats.size() / 16
	mm.instance_count = 0
	mm.instance_count = n
	mm.buffer = floats
	n_loaded = n
	buf_name = name
	load_ms = float(Time.get_ticks_usec() - t0) / 1000.0
	_apply_uniforms()
	_rebuild_points_mesh(floats, n)


func _rebuild_points_mesh(floats: PackedFloat32Array, n: int) -> void:
	# the PRIMITIVE_POINTS baseline shares the same data. Confidence, placement time and
	# source ride in COLOR because a points primitive has no instance custom data.
	if n > 2_100_000:
		return
	var v := PackedVector3Array(); v.resize(n)
	var c := PackedColorArray(); c.resize(n)
	for i in n:
		var b := i * 16
		v[i] = Vector3(floats[b + 3], floats[b + 7], floats[b + 11])
		c[i] = Color(floats[b + 12], floats[b + 13] / 1000.0, floats[b + 15] / 8.0, 1.0)
	var arr := []
	arr.resize(Mesh.ARRAY_MAX)
	arr[Mesh.ARRAY_VERTEX] = v
	arr[Mesh.ARRAY_COLOR] = c
	var m := ArrayMesh.new()
	m.add_surface_from_arrays(Mesh.PRIMITIVE_POINTS, arr)
	var pm := ShaderMaterial.new()
	pm.shader = load("res://points.gdshader")
	pts_mesh.mesh = m
	pts_mesh.material_override = pm


# ---------------------------------------------------------------- decal
func _build_decal() -> void:
	decal_mmi = MultiMeshInstance3D.new()
	decal_mm = MultiMesh.new()
	decal_mm.transform_format = MultiMesh.TRANSFORM_3D
	var q := QuadMesh.new()
	q.size = Vector2(1.0, 1.0)
	q.orientation = PlaneMesh.FACE_Y
	decal_mm.mesh = q
	decal_mmi.multimesh = decal_mm
	var dm := ShaderMaterial.new()
	dm.shader = load("res://decal.gdshader")
	dm.set_shader_parameter("u_col", WALKED)
	dm.set_shader_parameter("u_level", 0.10)
	decal_mmi.material_override = dm
	decal_mmi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	decal_mmi.custom_aabb = AABB(Vector3(-200, -40, -200), Vector3(600, 120, 600))
	add_child(decal_mmi)


func _rebuild_decal() -> void:
	# ART 8.2: a dark-cyan wash at z = 0 wherever count > 0, under everything. Rebuilt on
	# the CPU because the bins a point falls in change when a fix moves it. Two-cell bins,
	# the same 1.2 m the belief occupancy grid uses.
	if not show_decal or n_loaded == 0:
		decal_mmi.visible = false
		return
	decal_mmi.visible = true
	var bin := decal_bin
	var seen := {}
	var floats := mm.buffer
	var step := 1
	if n_loaded > 240_000:
		step = int(n_loaded / 240_000.0) + 1
	var i := 0
	while i < n_loaded:
		var b := i * 16
		var tp := floats[b + 13]
		if tp <= now:
			var tf := floats[b + 14]
			var w := 1.0 if (tf >= 0.0 and now >= tf) else 0.0
			var x: float = floats[b + 3] + floats[b + 0] * w
			var z: float = floats[b + 11] + floats[b + 8] * w
			seen[Vector2i(int(floor(x / bin)), int(floor(z / bin)))] = true
		i += step
	var keys := seen.keys()
	decal_mm.instance_count = 0
	decal_mm.instance_count = keys.size()
	var buf := PackedFloat32Array()
	buf.resize(keys.size() * 12)
	var j := 0
	for k in keys:
		var ox := (float(k.x) + 0.5) * bin
		var oz := (float(k.y) + 0.5) * bin
		buf[j + 0] = bin * 2.6; buf[j + 1] = 0.0; buf[j + 2] = 0.0; buf[j + 3] = ox
		buf[j + 4] = 0.0; buf[j + 5] = 1.0; buf[j + 6] = 0.0; buf[j + 7] = 0.02
		buf[j + 8] = 0.0; buf[j + 9] = 0.0; buf[j + 10] = bin * 2.6; buf[j + 11] = oz
		j += 12
	decal_mm.buffer = buf
	last_decal_t = now


# ---------------------------------------------------------------- lines
func _build_lines() -> void:
	lines = MeshInstance3D.new()
	lines.mesh = ImmediateMesh.new()
	var lm := ShaderMaterial.new()
	lm.shader = load("res://line.gdshader")
	lm.set_shader_parameter("u_col", GHOST)
	lm.set_shader_parameter("u_level", 1.0)
	lines.material_override = lm
	lines.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	lines.custom_aabb = AABB(Vector3(-200, -40, -200), Vector3(600, 120, 600))
	add_child(lines)


func _belief_pose_at(t: float) -> Vector3:
	var lo := 0
	var hi := belief_trail_t.size() - 1
	if hi < 0: return Vector3.ZERO
	while lo < hi:
		var mid := (lo + hi + 1) >> 1
		if belief_trail_t[mid] <= t: lo = mid
		else: hi = mid - 1
	return belief_trail[lo]


func _rebuild_lines() -> void:
	var im: ImmediateMesh = lines.mesh
	im.clear_surfaces()
	if not show_lines:
		return
	im.surface_begin(Mesh.PRIMITIVE_LINES)
	# the believed trail: where it thinks it has been
	var trail_col := Color(0.36, 0.51, 0.60, 0.30)
	for i in range(1, belief_trail.size()):
		if belief_trail_t[i] > now: break
		im.surface_set_color(trail_col)
		im.surface_add_vertex(belief_trail[i - 1])
		im.surface_add_vertex(belief_trail[i])
	# the beacons it recorded. NO chain between them: a line joining beacons in drop order
	# runs straight across the whole map, is the brightest thing in frame, and is not in
	# ART 8.2 -- it was reading as structure that the belief does not have.
	for b in beacons:
		if float(b.t) > now: continue
		var p := Vector3(float(b.x) * CELL, 0.30, -float(b.y) * CELL)
		im.surface_set_color(Color(1, 1, 1, 0.34))
		for k in 4:
			var a0 := TAU * float(k) / 4.0 + PI * 0.25
			var a1 := TAU * float(k + 1) / 4.0 + PI * 0.25
			im.surface_add_vertex(p + Vector3(cos(a0), 0, sin(a0)) * 0.5)
			im.surface_add_vertex(p + Vector3(cos(a1), 0, sin(a1)) * 0.5)
	# the ghost: where it believes it is standing, at its real size
	var g := _belief_pose_at(now)
	im.surface_set_color(Color(1, 1, 1, 0.55))
	for k in 24:
		var a0 := TAU * float(k) / 24.0
		var a1 := TAU * float(k + 1) / 24.0
		im.surface_add_vertex(g + Vector3(cos(a0), 0, sin(a0)) * 0.9 + Vector3(0, 0.5, 0))
		im.surface_add_vertex(g + Vector3(cos(a1), 0, sin(a1)) * 0.9 + Vector3(0, 0.5, 0))
	im.surface_end()


# ---------------------------------------------------------------- truth
func _build_truth() -> void:
	if truth_root != null:
		return
	var t0 := Time.get_ticks_usec()
	truth_root = Node3D.new()
	add_child(truth_root)
	var f := FileAccess.open("res://data/seed7_grid.bin", FileAccess.READ)
	var g := f.get_buffer(f.get_length())
	var W: int = meta.grid_w
	var H: int = meta.grid_h
	var v := PackedVector3Array()
	var nrm := PackedVector3Array()
	var free_cells := 0
	for y in H:
		for x in W:
			if g[y * W + x] == 0:
				continue
			free_cells += 1
			var x0 := float(x) * CELL
			var x1 := x0 + CELL
			var z1 := -float(y) * CELL
			var z0 := z1 - CELL
			_quad(v, nrm, Vector3(x0, 0, z0), Vector3(x1, 0, z0),
				Vector3(x1, 0, z1), Vector3(x0, 0, z1), Vector3.UP)
			for d in [Vector2i(1, 0), Vector2i(-1, 0), Vector2i(0, 1), Vector2i(0, -1)]:
				var nx: int = x + d.x
				var ny: int = y + d.y
				var rock := true
				if nx >= 0 and nx < W and ny >= 0 and ny < H:
					rock = g[ny * W + nx] == 0
				if not rock:
					continue
				var a: Vector3
				var b: Vector3
				var n2: Vector3
				if d.x == 1:
					a = Vector3(x1, 0, z0); b = Vector3(x1, 0, z1); n2 = Vector3(-1, 0, 0)
				elif d.x == -1:
					a = Vector3(x0, 0, z1); b = Vector3(x0, 0, z0); n2 = Vector3(1, 0, 0)
				elif d.y == 1:
					a = Vector3(x1, 0, z0); b = Vector3(x0, 0, z0); n2 = Vector3(0, 0, 1)
				else:
					a = Vector3(x0, 0, z1); b = Vector3(x1, 0, z1); n2 = Vector3(0, 0, -1)
				_quad(v, nrm, a, b, b + Vector3(0, WALL_H, 0), a + Vector3(0, WALL_H, 0), n2)
	var arr := []
	arr.resize(Mesh.ARRAY_MAX)
	arr[Mesh.ARRAY_VERTEX] = v
	arr[Mesh.ARRAY_NORMAL] = nrm
	var m := ArrayMesh.new()
	m.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arr)
	var mi := MeshInstance3D.new()
	mi.mesh = m
	var rm := ShaderMaterial.new()
	rm.shader = load("res://rock.gdshader")
	mi.material_override = rm
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	truth_root.add_child(mi)
	# The non-diegetic survey light. See rock.gdshader: with the diegetic economy alone
	# this layer is a black rectangle and no exposure recovers it.
	var l := DirectionalLight3D.new()
	l.rotation_degrees = Vector3(-52, 34, 0)
	l.light_energy = 1.6
	l.shadow_enabled = false
	truth_root.add_child(l)
	var l2 := DirectionalLight3D.new()
	l2.rotation_degrees = Vector3(-18, -150, 0)
	l2.light_energy = 0.5
	l2.shadow_enabled = false
	truth_root.add_child(l2)
	print("truth mesh: ", free_cells, " free cells, ", v.size() / 3, " tris, ",
		"%.0f" % (float(Time.get_ticks_usec() - t0) / 1000.0), " ms")


func _quad(v: PackedVector3Array, n: PackedVector3Array,
		a: Vector3, b: Vector3, c: Vector3, d: Vector3, nn: Vector3) -> void:
	v.append(a); v.append(b); v.append(c)
	v.append(a); v.append(c); v.append(d)
	for i in 6: n.append(nn)


# ---------------------------------------------------------------- camera / hud
func _build_camera() -> void:
	cam = Camera3D.new()
	cam.near = 0.02
	cam.far = 900.0
	add_child(cam)
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = VOID
	env.ambient_light_source = Environment.AMBIENT_SOURCE_DISABLED
	env.tonemap_mode = Environment.TONE_MAPPER_AGX
	env.tonemap_white = 4.0
	env.glow_enabled = false
	var we := WorldEnvironment.new()
	we.environment = env
	add_child(we)


func _build_hud() -> void:
	var l := Label.new()
	l.position = Vector2(18, 12)
	l.add_theme_font_size_override("font_size", 15)
	l.add_theme_color_override("font_color", Color(0.55, 0.72, 0.8))
	add_child(l)
	hud = l


func _frame_all() -> void:
	orbit_target = Vector3(60.0, 1.0, -22.0)
	orbit_dist = 95.0
	orbit_az = 0.9
	orbit_el = 0.62


func _screen_extent(inv: Transform3D, pts: PackedVector3Array) -> Vector4:
	# (umin, umax, vmin, vmax) at the 1.5 / 98.5 percentiles, not the extremes: a single
	# stray return -- and a sonar cloud has plenty, 34 of them are literally FALSE -- would
	# otherwise set the camera distance and leave half the frame empty.
	var us := PackedFloat32Array()
	var vs := PackedFloat32Array()
	for p in pts:
		var v := inv * p
		if v.z > -0.05:
			continue
		us.append(v.x / -v.z)
		vs.append(v.y / -v.z)
	if us.size() < 4:
		return Vector4(-1, 1, -1, 1)
	us.sort()
	vs.sort()
	var k: int = int(us.size() * 0.015)
	return Vector4(us[k], us[us.size() - 1 - k], vs[k], vs[vs.size() - 1 - k])


func _frame_from_box() -> void:
	# Fit the camera to the points themselves, not to a hand-typed box: gather every point
	# visible at the scrub time (optionally only those placed inside frame_times), then
	# solve in SCREEN space for the distance that fills the frame. A box fitted in world
	# space wastes most of the frame, because the near corner of a 50 m box at 40 m is
	# what limits it and the cloud is nowhere near that corner.
	if frame_box == Vector4(0, 0, 0, 0) and frame_times == Vector2.ZERO:
		return
	var at: float = frame_at if frame_at > 0.0 else now
	var pts: PackedVector3Array = PackedVector3Array()
	var floats := mm.buffer
	var step: int = max(1, int(n_loaded / 20000.0) + 1)
	var i := 0
	var lo: float = frame_times.x
	var hi: float = frame_times.y if frame_times.y > 0.0 else 1e9
	var bx0: float = frame_box.x
	var bx1: float = frame_box.y
	var by0: float = frame_box.z
	var by1: float = frame_box.w
	var use_box := frame_box != Vector4(0, 0, 0, 0)
	while i < n_loaded:
		var b := i * 16
		var tp: float = floats[b + 13]
		if tp <= at and tp >= lo and tp <= hi:
			var tf: float = floats[b + 14]
			var w: float = 1.0 if (tf >= 0.0 and at >= tf) else 0.0
			var px: float = floats[b + 3] + floats[b + 0] * w
			var py: float = floats[b + 7] + floats[b + 4] * w
			var pz: float = floats[b + 11] + floats[b + 8] * w
			if not use_box or (px >= bx0 * CELL and px <= bx1 * CELL
					and -pz >= by0 * CELL and -pz <= by1 * CELL):
				pts.append(Vector3(px, py, pz))
		i += step
	if pts.size() < 4:
		return
	var lo3 := pts[0]
	var hi3 := pts[0]
	for p in pts:
		lo3 = lo3.min(p)
		hi3 = hi3.max(p)
	orbit_target = (lo3 + hi3) * 0.5
	orbit_target.y = 0.7
	var ar := float(get_viewport().size.x) / float(get_viewport().size.y)
	var lim_v := tan(deg_to_rad(orbit_fov) * 0.5) * frame_fill
	var lim_u := lim_v * ar
	orbit_dist = max(3.0, (hi3 - lo3).length())
	# Distance AND centring, alternately. Fitting distance alone leaves the content off
	# centre -- perspective plus elevation put the bbox centre nowhere near the screen
	# centre -- and one extreme point then sets the distance while the opposite half of
	# the frame stays empty. That wasted 40% of every wide frame in the first pass.
	for outer in 8:
		for it in 30:
			_update_camera()
			var inv := cam.global_transform.affine_inverse()
			var e := _screen_extent(inv, pts)
			var need: float = max(max(abs(e.x), abs(e.y)) / lim_u,
				max(abs(e.z), abs(e.w)) / lim_v)
			if abs(need - 1.0) < 0.004:
				break
			orbit_dist *= 1.0 + 0.6 * (need - 1.0)
		_update_camera()
		var e2 := _screen_extent(cam.global_transform.affine_inverse(), pts)
		var uc := (e2.x + e2.y) * 0.5
		var vc := (e2.z + e2.w) * 0.5
		if abs(uc) < 0.004 and abs(vc) < 0.004:
			break
		var b := cam.global_transform.basis
		orbit_target += (b.x * uc + b.y * vc) * orbit_dist


func _update_camera() -> void:
	var d := Vector3(
		cos(orbit_el) * cos(orbit_az),
		sin(orbit_el),
		cos(orbit_el) * sin(orbit_az)) * orbit_dist
	cam.position = orbit_target + d
	cam.look_at(orbit_target, Vector3.UP)
	cam.fov = orbit_fov
	if ortho:
		cam.projection = Camera3D.PROJECTION_ORTHOGONAL
		cam.size = ortho_size
	else:
		cam.projection = Camera3D.PROJECTION_PERSPECTIVE


func _apply_uniforms() -> void:
	for m in [mat_add, mat_solid]:
		m.set_shader_parameter("u_now", now)
		m.set_shader_parameter("u_disc_m", disc_m)
		# A denser sensor has a NARROWER beam: N returns off the same surfaces means the ray
		# spacing fell by sqrt(N0/N), so the footprint falls with it. Scaling the beam this
		# way is what stops a million points becoming a million 0.9 m blobs, and at about
		# 300k the footprint drops below ART 8.2's 45 mm floor and the constant takes over.
		m.set_shader_parameter("u_beam_rad", beam_rad * (sqrt(5663.0 / float(max(n_loaded, 1)))
			if auto_beam else 1.0))
		m.set_shader_parameter("u_disc_max_m", disc_max)
		m.set_shader_parameter("u_min_px", min_px)
		m.set_shader_parameter("u_walked_flat", walked_flat)
		m.set_shader_parameter("u_gain", gain)
		m.set_shader_parameter("u_epoch_split", epoch_split)
		m.set_shader_parameter("u_epoch_only", epoch_only)
		m.set_shader_parameter("u_before", col_before)
		m.set_shader_parameter("u_after", col_after)
		m.set_shader_parameter("u_vp", Vector2(get_viewport().size))
		m.set_shader_parameter("u_age_knee_s", age_knee)
		# Additive discs at a million points overdraw the same surface hundreds of times.
		# Per-disc emission must therefore fall as the count rises: 1/sqrt(N) keeps a bank
		# of returns at roughly constant brightness while a lone outlier stays visible.
		# Straight 1/N is energy-correct and loses every isolated hit; see NOTES.
		m.set_shader_parameter("u_gain", gain * (sqrt(5663.0 / float(max(n_loaded, 1)))
			if auto_gain else 1.0))
	if pts_mesh != null and pts_mesh.material_override != null:
		pts_mesh.material_override.set_shader_parameter("u_now", now)
		pts_mesh.material_override.set_shader_parameter("u_gain", gain)
	mmi.material_override = mat_solid if solid else mat_add
	mmi.visible = technique == "multimesh" and mode != "truth"
	if pts_mesh != null:
		pts_mesh.visible = technique == "points" and mode != "truth"
	if decal_mmi != null:
		decal_mmi.visible = show_decal and mode != "truth"
	if lines != null:
		lines.visible = show_lines and mode != "truth"
	if mode == "both" or mode == "truth":
		_build_truth()
		truth_root.visible = true
		var lvl := 0.35 if mode == "both" else 1.0
		truth_root.get_child(0).material_override.set_shader_parameter("u_level", lvl)
	elif truth_root != null:
		truth_root.visible = false


func _process(dt: float) -> void:
	if playing:
		now = fmod(now + dt * play_rate, float(meta.t_end))
	_update_camera()
	_apply_uniforms()
	if abs(now - last_decal_t) > 0.4:
		_rebuild_decal()
	decal_mmi.material_override.set_shader_parameter("u_level", decal_level)
	_rebuild_lines()
	if hud != null:
		hud.visible = show_hud
		if show_hud:
			var vp := get_viewport().get_texture()
			hud.text = "t %5.1f / %.0f   %s   %s   %s   n=%d   disc %.0f mm\n%.1f ms cpu  %.1f ms gpu  %d draws  fps %d" % [
				now, meta.t_end, mode, technique, ("solid" if solid else "additive"),
				n_loaded, disc_m * 1000.0,
				RenderingServer.viewport_get_measured_render_time_cpu(get_viewport().get_viewport_rid()),
				RenderingServer.viewport_get_measured_render_time_gpu(get_viewport().get_viewport_rid()),
				RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_DRAW_CALLS_IN_FRAME),
				Engine.get_frames_per_second()]


func _unhandled_input(e: InputEvent) -> void:
	if e is InputEventMouseMotion and (e.button_mask & MOUSE_BUTTON_MASK_LEFT):
		orbit_az -= e.relative.x * 0.006
		orbit_el = clamp(orbit_el + e.relative.y * 0.006, -1.5, 1.5)
	elif e is InputEventMouseButton and e.pressed:
		if e.button_index == MOUSE_BUTTON_WHEEL_UP: orbit_dist *= 0.9; ortho_size *= 0.9
		elif e.button_index == MOUSE_BUTTON_WHEEL_DOWN: orbit_dist /= 0.9; ortho_size /= 0.9
	elif e is InputEventKey and e.pressed:
		match e.keycode:
			KEY_SPACE: playing = not playing
			KEY_LEFT: now = max(0.0, now - 5.0)
			KEY_RIGHT: now = min(float(meta.t_end), now + 5.0)
			KEY_1: mode = "belief"
			KEY_2: mode = "both"
			KEY_3: mode = "truth"
			KEY_B: solid = not solid
			KEY_P: technique = "points" if technique == "multimesh" else "multimesh"
			KEY_H: show_hud = not show_hud
			KEY_D: show_decal = not show_decal
			KEY_L: show_lines = not show_lines
			KEY_F: walked_flat = 1.0 - walked_flat
			KEY_O: ortho = not ortho
			KEY_EQUAL: disc_m *= 1.25
			KEY_MINUS: disc_m /= 1.25
			KEY_ESCAPE: get_tree().quit()


func _report_lights() -> void:
	# PROCEDURAL-AND-GODOT 5.4(a): the truth layer cannot be exposed out of black because
	# there is no light in it. The belief layer has the same problem and does not care.
	# This prints the evidence rather than asserting it in prose.
	var n := 0
	for c in get_children():
		if c is Light3D:
			n += 1
		for g in c.get_children():
			if g is Light3D:
				n += 1
	var env: Environment = null
	for c in get_children():
		if c is WorldEnvironment:
			env = c.environment
	print("belief layer: ", n, " Light3D in the scene; ambient source ",
		env.ambient_light_source, " (1 = AMBIENT_SOURCE_DISABLED); background BG_COLOR ",
		env.background_color, "; no fog, no GI, no shadows; every cloud shader unshaded")


# ---------------------------------------------------------------- capture
func _snap(name: String) -> void:
	await RenderingServer.frame_post_draw
	var img := get_viewport().get_texture().get_image()
	var dir := "res://" + shot_dir
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(dir))
	img.save_png(dir + "/" + name + ".png")
	print("shot ", name, "  tgt ", orbit_target, " d ", "%.1f" % orbit_dist, " box ", frame_box, "  ",
		"%.2f" % RenderingServer.viewport_get_measured_render_time_gpu(
		get_viewport().get_viewport_rid()), " ms gpu  ",
		RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_DRAW_CALLS_IN_FRAME),
		" draws  ", n_loaded, " pts")


func _reset() -> void:
	mode = "belief"; solid = false; technique = "multimesh"; show_hud = false
	show_decal = true; show_lines = true; disc_m = 0.045; min_px = 1.6
	walked_flat = 0.0; gain = 1.0; epoch_split = -1.0; epoch_only = 0.0
	col_before = SENSED; col_after = SENSED; ortho = false; orbit_fov = 55.0
	age_knee = 150.0; auto_gain = true; decal_bin = 0.6; decal_level = 0.10
	beam_rad = 0.035; disc_max = 0.9; auto_beam = true
	frame_box = Vector4(0, 0, 0, 0); frame_times = Vector2.ZERO; frame_fill = 0.86
	frame_at = 0.0
	if buf_name != "seed7_real.mmbuf":
		_load_buffer("seed7_real.mmbuf")


func _settle(frames: int = 6) -> void:
	for i in frames:
		_update_camera()
		_apply_uniforms()
		_rebuild_decal()
		_rebuild_lines()
		await get_tree().process_frame


func _run_shots() -> void:
	RenderingServer.viewport_set_measure_render_time(get_viewport().get_viewport_rid(), true)
	var shots := SHOTS
	for s in shots:
		if shot_filter != "" and not String(s.name).contains(shot_filter):
			continue
		_reset()
		for k in s.keys():
			if k == "name" or k == "buffer":
				continue
			set(k, s[k])
		if s.has("buffer"):
			_load_buffer(s.buffer)
		_frame_from_box()
		await _settle(10)
		await _snap(s.name)
	get_tree().quit()


func _run_bench() -> void:
	RenderingServer.viewport_set_measure_render_time(get_viewport().get_viewport_rid(), true)
	show_hud = false
	print("\n%-22s %-11s %9s %8s %8s %8s %8s" % ["buffer", "technique", "instances",
		"gpu ms", "cpu ms", "draws", "load ms"])
	for row in BENCH:
		_reset()
		for k in row.keys():
			if k == "name" or k == "buffer": continue
			set(k, row[k])
		if row.has("buffer"):
			_load_buffer(row.buffer)
		await _settle(60)
		var g := 0.0
		var c := 0.0
		for i in 40:
			await get_tree().process_frame
			g += RenderingServer.viewport_get_measured_render_time_gpu(get_viewport().get_viewport_rid())
			c += RenderingServer.viewport_get_measured_render_time_cpu(get_viewport().get_viewport_rid())
		print("%-22s %-11s %9d %8.2f %8.2f %8d %8.1f" % [row.name, technique, n_loaded,
			g / 40.0, c / 40.0,
			RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_DRAW_CALLS_IN_FRAME),
			load_ms])
	get_tree().quit()


# ---------------------------------------------------------------- the shot list
# t = 141.7 is the SPOOF: a fix on a lie, jump 33.3 cells, surprise 11.1 sigma.
# t = 428.3 is THE FIX: an honest beacon, jump 13.3 cells, surprise 4.3 sigma, after
#           246 s of dead reckoning.
const SHOTS := [
	# 01-04  the renderer itself, on the real seed-7 belief
	{name = "01_early_sparse", now = 100.0, orbit_az = 1.15, orbit_el = 0.50,
		frame_times = Vector2(0, 101)},
	{name = "02_late_full_match", now = 480.0, frame_times = Vector2(0, 481),
		orbit_az = 1.28, orbit_el = 0.78},
	{name = "03_low_orbit_surfaces", now = 300.0, orbit_target = Vector3(70, 0.8, -14),
		orbit_dist = 22.0, orbit_az = 2.05, orbit_el = 0.09, orbit_fov = 45.0},
	{name = "04_macro_true_disc", now = 300.0, orbit_target = Vector3(70.5, 0.7, -14.5),
		orbit_dist = 1.8, orbit_az = 2.05, orbit_el = 0.13, orbit_fov = 32.0,
		show_decal = false, show_lines = false},
	# 05  DRIFT. 246 s of dead reckoning between the fix at 3:03 and the one at 7:08.
	# The whole map, so that the early part -- surveyed while the estimate was good --
	# and the late part -- laid down while it was 73 cells out -- are in one frame.
	{name = "05_drift_smear", now = 427.0, frame_times = Vector2(0, 428),
		orbit_az = 1.28, orbit_el = 0.72},
	# 06-08  THE FIX. player_6 at 428.3: jump 13.3 cells, 4.3 sigma. Everything placed
	# since the 182.6 epoch swings about it; everything older does not move at all.
	# 06 is the doubling ITSELF -- the machine walked out along a passage at 3:03-6:21
	# and back along it at 6:21-7:08, and by 7:07 the two records of one passage sit
	# 8 cells apart, both drawn, both with the believed trail running through them.
	# 07 is the same camera four seconds later: the fix has slid the recent copy onto
	# the older one and the passage is single again. That is the pair.
	{name = "06_fix_before", now = 427.0, frame_times = Vector2(150, 428),
		frame_at = 433.0, orbit_az = 1.32, orbit_el = 0.55},
	{name = "07_fix_after", now = 433.0, frame_times = Vector2(150, 428),
		frame_at = 433.0, orbit_az = 1.32, orbit_el = 0.55},
	# 08 is the doubling a fix does NOT close, because the second pass fell in a later
	# epoch: 6:21-7:08 against 7:46-8:00, 17.4 cells (10.4 m) apart, and it stays that
	# way for the rest of the match. Measured by rigid alignment: median residual
	# 0.21 cells at a shift of (3.5, 17.0) -- the same shape, twice, in two places.
	# The camera is high because the doubling is a PLAN fact: two traces of one passage,
	# side by side, with the machine's own believed trail running through each of them.
	# age_knee 90 s so the older copy sits at the 0.35 age floor and the newer one does
	# not -- ART 8.2's own "an old return is dimmer" doing the separating, no third colour.
	{name = "08_fix_two_corridors", now = 480.0, age_knee = 90.0,
		frame_box = Vector4(88, 130, 0, 42), frame_times = Vector2(300, 481),
		orbit_az = 1.30, orbit_el = 1.05, orbit_fov = 45.0},
	# 09-10  THE SPOOF at 141.7: a fix on a cloned beacon. Jump 33.3 cells, 11.1 sigma.
	{name = "09_spoof_before", now = 141.0, frame_times = Vector2(0, 142),
		frame_at = 141.0, orbit_az = 1.25, orbit_el = 0.62},
	{name = "10_spoof_after", now = 144.0, frame_times = Vector2(0, 142),
		frame_at = 141.0, orbit_az = 1.25, orbit_el = 0.62},
	# 11-13  the dense ladder, same camera as 02
	{name = "11_dense_100k", buffer = "dense_100k.mmbuf", now = 480.0,
		frame_times = Vector2(0, 481), orbit_az = 1.28, orbit_el = 0.78},
	{name = "12_dense_1m", buffer = "dense_1m.mmbuf", now = 480.0,
		frame_times = Vector2(0, 481), orbit_az = 1.28, orbit_el = 0.78},
	{name = "13_dense_2m", buffer = "dense_2m.mmbuf", now = 480.0,
		frame_times = Vector2(0, 481), orbit_az = 1.28, orbit_el = 0.78},
	# 14-15  the two registers, and the reason the truth one is a problem
	{name = "14_both_registers", now = 480.0, mode = "both",
		frame_times = Vector2(0, 481), orbit_az = 1.28, orbit_el = 0.78},
	{name = "15_truth_only", now = 480.0, mode = "truth",
		frame_times = Vector2(0, 481), orbit_az = 1.28, orbit_el = 0.78},
	# 16-17  the two rejected alternatives, for the table
	{name = "16_solid_blend", now = 300.0, solid = true, orbit_target = Vector3(70, 0.8, -14),
		orbit_dist = 22.0, orbit_az = 2.05, orbit_el = 0.09, orbit_fov = 45.0},
	{name = "17_points_baseline", now = 480.0, technique = "points",
		frame_times = Vector2(0, 481), orbit_az = 1.28, orbit_el = 0.78},
	# probes
	# 18-20  the same three moments at lidar density. The toy sim returns 5,663 points in
	# a whole match; a modern scanner returns that in a tenth of a second. The doubling is
	# marginal at 5.7k and unmistakable at 1M, which says the sparsity is the problem and
	# the renderer is not.
	{name = "18_fix_two_corridors_dense", buffer = "dense_1m.mmbuf", now = 480.0,
		age_knee = 90.0, gain = 0.40, frame_box = Vector4(88, 130, 0, 42),
		frame_times = Vector2(300, 481), orbit_az = 1.30, orbit_el = 1.05,
		orbit_fov = 45.0},
	{name = "19_spoof_after_dense", buffer = "dense_1m.mmbuf", now = 144.0, gain = 0.5,
		frame_times = Vector2(0, 142), frame_at = 141.0,
		orbit_az = 1.25, orbit_el = 0.62},
	{name = "20_low_orbit_dense", buffer = "dense_1m.mmbuf", now = 300.0,
		orbit_target = Vector3(70, 0.8, -14), orbit_dist = 22.0,
		orbit_az = 2.05, orbit_el = 0.09, orbit_fov = 45.0, gain = 0.7},
	{name = "21_spoof_before_dense", buffer = "dense_1m.mmbuf", now = 141.0, gain = 0.5,
		frame_times = Vector2(0, 142), frame_at = 141.0,
		orbit_az = 1.25, orbit_el = 0.62},
	# probes kept for the record: the direction's constant 600 mm disc, and walked returns
	# laid flat on the floor instead of along their ray.
	{name = "90_probe_600mm_flat_disc", now = 480.0, disc_m = 0.6, min_px = 0.0,
		beam_rad = 0.0, show_decal = false, show_lines = false,
		orbit_target = Vector3(70, 0.8, -14), orbit_dist = 22.0,
		orbit_az = 2.05, orbit_el = 0.09, orbit_fov = 45.0},
	{name = "91_probe_walked_flat", now = 480.0, walked_flat = 1.0,
		orbit_target = Vector3(70, 0.8, -14), orbit_dist = 22.0,
		orbit_az = 2.05, orbit_el = 0.09, orbit_fov = 45.0},
]

const BENCH := [
	{name = "real 5.7k quad", buffer = "seed7_real.mmbuf"},
	{name = "real 5.7k points", buffer = "seed7_real.mmbuf", technique = "points"},
	{name = "100k quad", buffer = "dense_100k.mmbuf"},
	{name = "100k points", buffer = "dense_100k.mmbuf", technique = "points"},
	{name = "500k quad", buffer = "dense_500k.mmbuf"},
	{name = "1M quad", buffer = "dense_1m.mmbuf"},
	{name = "1M solid mix+depth", buffer = "dense_1m.mmbuf", solid = true},
	{name = "1M no decal", buffer = "dense_1m.mmbuf", show_decal = false},
	{name = "2M quad", buffer = "dense_2m.mmbuf"},
	{name = "2M points", buffer = "dense_2m.mmbuf", technique = "points"},
	# fill-rate isolation: same instance count, sub-pixel discs, so what is left is the
	# vertex/instance cost and nothing else.
	{name = "2M quad zero-fill", buffer = "dense_2m.mmbuf", disc_m = 0.0005,
		min_px = 0.0, beam_rad = 0.0, auto_beam = false},
	{name = "4M quad", buffer = "dense_4m.mmbuf"},
	{name = "4M quad zero-fill", buffer = "dense_4m.mmbuf", disc_m = 0.0005,
		min_px = 0.0, beam_rad = 0.0, auto_beam = false},
	# NOTE: there is no "4M points" row. The PRIMITIVE_POINTS path needs a GDScript loop
	# over every point to build its mesh and is capped at 2.1M; above that it silently
	# keeps the previous mesh and the row measures nothing. Removed rather than reported.
]
