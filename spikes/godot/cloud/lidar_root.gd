# ---------------------------------------------------------------------------
# BLINDSIDE -- the belief cloud, rebuilt around a SCANNING sensor.
#
# The previous pass rendered 5,663 points exported from a phase1 match and got
# glowing mist, because a sensor that fires 90 rays in one horizontal plane
# every 1.5 seconds does not produce a point cloud, it produces a sparse
# outline. Nothing in the renderer could have fixed that. This build replaces
# the SENSOR: a spinning head with a fixed vertical array of emitters, fired
# against real generated geometry, so every structural feature of a real scan
# -- rings, constant azimuth pitch, hard occlusion shadows, intensity, 1/r^2
# density, a hole at the origin -- is produced rather than drawn.
#
# WHAT IS KEPT FROM THE PREVIOUS PASS, unchanged:
#   * one MultiMesh, 64 bytes a point, three draw calls at any point count
#   * a point carries two positions and one fix time, because a belief point
#     is moved by AT MOST ONE correction, so scrubbing is a single uniform
#   * belief and truth are separate node trees and the cloud never reads one
#
# THE INVARIANT. `LidarScan` is the only thing here that reads the true world.
# It hands back range/bearing/elevation in the SENSOR's own frame plus a time.
# Everything after that line -- placement, drift, the fix, the render -- sees
# only those measurements and a believed pose. There is no path from the
# geometry to the cloud that does not go through `sweep()`.
# ---------------------------------------------------------------------------
extends Node3D

const CELL := 0.6

# The depth gauge (CHASSIS-TIMING D8 assigns SensorId 7 to every chassis). Height is measured
# rather than dead-reckoned, which is why belief drift is planar -- but it is measured by an
# instrument, not read off the world. Before 2026-09-10 this file copied the true height into
# belief verbatim; on a flat cave that was invisible, and on a vertical one it is a truth leak
# into the one view that exists to show what the machine does NOT know.
const GAUGE_BIAS_M: float = 0.42     # fixed offset for a match, sign and size from the seed
const GAUGE_NOISE_M: float = 0.08    # per-reading, one sigma
const VOID := Color(0.0235, 0.0314, 0.0431)
const SENSED := Color(0.388, 0.839, 0.969)
const LIE := Color(1.000, 0.824, 0.247)
const GHOST := Color(0.624, 0.910, 1.000)

# phase1 dead-reckoning constants, from phase1/tuning.py. Not invented here.
const DR_HEADING_BIAS_DEG_PER_CELL := 0.11
const DR_HEADING_NOISE_DEG_PER_CELL := 0.03
const DR_POS_NOISE_PER_CELL := 0.03

# ---------------------------------------------------------------- world
var geo: LidarGeo
var seed_v := 7
var length_cells := 170

# ---------------------------------------------------------------- render
var mm: MultiMesh
var mmi: MultiMeshInstance3D
var mat: ShaderMaterial
var truth_root: Node3D
var lights: Node3D
var lines: MeshInstance3D
var line_mesh: ImmediateMesh
var line_mat: StandardMaterial3D
var hud: Label
var cam: Camera3D

# ---------------------------------------------------------------- cloud state
var n_pts := 0
var t_end := 1.0
var now := 1.0
var playing := false
var play_rate := 1.0

var scene_name := ""
var scan_desc := ""
var bake_ms := 0.0
var scan_ms := 0.0
var n_shots := 0
var n_drop := 0
var revs := 0
var cloud_min := Vector3.ZERO
var cloud_max := Vector3.ZERO

# fix records: {t, anchor, dth, dtv, sigma, lie}
var fix_log: Array = []
var trail_true := PackedVector3Array()
var trail_bel := PackedVector3Array()
var trail_t := PackedFloat32Array()
var sensor_stand := Vector3.ZERO

# ---------------------------------------------------------------- view state
var mode := 0
var gain := 1.0
var pt_world := 0.020
var min_px := 1.6
var max_px := 3.6
var square := 0.0
var footprint := 0.0
var age_knee := 90.0
var age_floor := 0.42
var epoch_split := -1.0
var col_before := SENSED
var col_after := SENSED
var show_truth := false
var truth_exposure := 0.35
var show_lines := true
var show_hud := true
var h_lo := -1.0
var h_hi := 4.0
var clip_lo := -1000.0
var clip_hi := 1000.0

var orbit_target := Vector3.ZERO
var orbit_az := 0.6
var orbit_el := 0.5
var orbit_dist := 30.0
var orbit_fov := 55.0

var shots_only := false
var shot_filter := ""
var shot_dir := "shots/lidar"
var stats_only := false

# ---------------------------------------------------------------- cinema
# The trailer's belief shots (TRAILER.md 3 shots 18, 19, 20, 21 and 26) and the
# camera rig that executes them. See cinema.gd, cinema_run.gd and CINEMA.md.
var cinema_mode := ""
var cinema: CloudCinema = null
# The walk planner's overrides, used only by the cinema bakes: a trailer shot
# is authored at a STATION, so the machine has to walk past that station rather
# than wherever the longest chamber-free run happens to be.
var cine_from := -1
var cine_to := -1
var walk_oneway := false
# the cinema rig drives the camera transform directly; the orbit rig must not
# overwrite it every frame
var cam_driven := false


# ===========================================================================
func _ready() -> void:
	for a in OS.get_cmdline_user_args():
		if a == "--shotsonly": shots_only = true
		elif a == "--stats": stats_only = true
		elif a.begins_with("--shot="): shots_only = true; shot_filter = a.substr(7)
		elif a.begins_with("--shotdir="): shot_dir = a.substr(10)
		elif a.begins_with("--seed="): seed_v = int(a.substr(7))
		elif a.begins_with("--len="): length_cells = int(a.substr(6))
		elif a.begins_with("--cinema="): cinema_mode = a.substr(9)

	print("adapter: ", RenderingServer.get_video_adapter_name(), " | api ",
		RenderingServer.get_video_adapter_api_version())

	var t0 := Time.get_ticks_msec()
	geo = LidarGeo.new()
	if cinema_mode != "":
		cinema = CloudCinema.new()
		cinema.parse_args(self)
		# THE CAMERA MATCH BEGINS HERE, and it is two integers.
		# spikes/godot/cave/ generates seed 7 over 240 cells. Station 68's
		# x and z are the same at any length -- the drive's Y walk depends only
		# on the cell index -- but `worked`, the works bitfield and the sump
		# all divide by the stretch length, so at 170 cells station 68 is the
		# same COORDINATE in a different passage: different profile, different
		# props, different floor. Nothing else in this file matters if these
		# two numbers are wrong. CINEMA.md 2.
		seed_v = cinema.cave_seed
		length_cells = cinema.cave_len
		geo.cave_match = true
	geo.build(seed_v, length_cells)
	geo.attach(self)
	print("cave: seed ", seed_v, "  ", geo.topo.stations.size(), " stations  ",
		geo.tri_total, " triangles  ", geo.chamber_m.size(), " chambers  hash 0x",
		String.num_int64(geo.topo.content_hash(), 16))
	print("geometry built in ", Time.get_ticks_msec() - t0, " ms")

	_build_render()
	_build_truth()
	_build_camera()
	_build_hud()
	# physics needs a tick before the trimesh shapes answer a ray
	await get_tree().physics_frame
	await get_tree().physics_frame

	if cinema_mode != "":
		call_deferred("_run_cinema")
	elif stats_only:
		call_deferred("_run_stats")
	elif shots_only:
		call_deferred("_run_shots")
	else:
		_bake("chamber1")
		_frame_cloud()


# ===========================================================================
# render nodes.  three draw calls: the cloud, the trail, the truth shell.
# ===========================================================================
func _quad() -> Mesh:
	var v := PackedVector3Array([Vector3(-1, -1, 0), Vector3(1, -1, 0), Vector3(1, 1, 0), Vector3(-1, 1, 0)])
	var uv := PackedVector2Array([Vector2(0, 0), Vector2(1, 0), Vector2(1, 1), Vector2(0, 1)])
	var ix := PackedInt32Array([0, 1, 2, 0, 2, 3])
	var arr: Array = []
	arr.resize(Mesh.ARRAY_MAX)
	arr[Mesh.ARRAY_VERTEX] = v
	arr[Mesh.ARRAY_TEX_UV] = uv
	arr[Mesh.ARRAY_INDEX] = ix
	var am := ArrayMesh.new()
	am.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arr)
	return am


func _build_render() -> void:
	mat = ShaderMaterial.new()
	mat.shader = load("res://lidar_point.gdshader")
	mm = MultiMesh.new()
	mm.transform_format = MultiMesh.TRANSFORM_3D
	mm.use_custom_data = true
	mm.mesh = _quad()
	mmi = MultiMeshInstance3D.new()
	mmi.multimesh = mm
	mmi.material_override = mat
	mmi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	mmi.extra_cull_margin = 1000.0
	add_child(mmi)

	line_mesh = ImmediateMesh.new()
	line_mat = StandardMaterial3D.new()
	line_mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	line_mat.vertex_color_use_as_albedo = true
	line_mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	line_mat.disable_receive_shadows = true
	lines = MeshInstance3D.new()
	lines.mesh = line_mesh
	lines.material_override = line_mat
	lines.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	lines.extra_cull_margin = 1000.0
	add_child(lines)

	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = VOID
	env.ambient_light_source = Environment.AMBIENT_SOURCE_DISABLED
	# LINEAR, not AgX. The previous pass needed a filmic roll-off because a
	# million additive discs summed past white; opaque points never accumulate,
	# so the intensity ramp should arrive on screen as it was authored.
	env.tonemap_mode = Environment.TONE_MAPPER_LINEAR
	var we := WorldEnvironment.new()
	we.environment = env
	add_child(we)


func _build_truth() -> void:
	# The truth layer exists only so a viewer can check a shadow against the
	# thing that cast it. It is lit by a non-diegetic survey fill, which is
	# PROCEDURAL-AND-GODOT 5.4(a)'s recommendation and not a diegetic source.
	truth_root = Node3D.new()
	truth_root.visible = false
	add_child(truth_root)
	var cols := [Color(0.42, 0.40, 0.38), Color(0.20, 0.26, 0.30),
				 Color(0.44, 0.33, 0.22), Color(0.52, 0.53, 0.55), Color(0.85, 0.85, 0.85)]
	for cls in range(LidarGeo.N_SURF):
		if geo.meshes[cls] == null:
			continue
		var mi := MeshInstance3D.new()
		mi.mesh = geo.meshes[cls]
		var sm := StandardMaterial3D.new()
		sm.albedo_color = cols[cls]
		sm.roughness = 0.95
		# A small self-emission under the survey fill. Without it a surface the
		# fill does not reach reads as a hole, and a hole in the TRUTH layer is
		# exactly the thing this overlay exists to rule out -- the voids the
		# viewer is being asked to check must all belong to the sensor.
		sm.emission_enabled = true
		sm.emission = cols[cls]
		sm.cull_mode = BaseMaterial3D.CULL_DISABLED
		mi.material_override = sm
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		truth_root.add_child(mi)
	var l1 := DirectionalLight3D.new()
	l1.light_energy = 1.6
	l1.shadow_enabled = false
	l1.rotation_degrees = Vector3(-52, 34, 0)
	truth_root.add_child(l1)
	var l2 := DirectionalLight3D.new()
	l2.light_energy = 0.5
	l2.shadow_enabled = false
	l2.rotation_degrees = Vector3(-16, -140, 0)
	truth_root.add_child(l2)


func _build_camera() -> void:
	cam = Camera3D.new()
	cam.far = 400.0
	cam.near = 0.05
	add_child(cam)
	_update_camera()


func _build_hud() -> void:
	var cl := CanvasLayer.new()
	add_child(cl)
	hud = Label.new()
	hud.position = Vector2(18, 14)
	hud.add_theme_color_override("font_color", GHOST)
	hud.add_theme_font_size_override("font_size", 15)
	cl.add_child(hud)


# ===========================================================================
# maths
# ===========================================================================
func _gauge_y(true_y: float, seed_i: int, step_i: int) -> float:
	"""What the depth gauge reports. The only place belief may learn a height."""
	var bias: float = (float((seed_i * 2654435761) % 2000) / 1000.0 - 1.0) * GAUGE_BIAS_M
	return true_y + bias + _gauss(43, step_i, 0) * GAUGE_NOISE_M

func _yawrot(v: Vector3, y: float) -> Vector3:
	var c := cos(y)
	var s := sin(y)
	return Vector3(v.x * c - v.z * s, v.y, v.x * s + v.z * c)


func _apply_fix(p: Vector3, a: Vector3, dth: float, dtv: Vector3) -> Vector3:
	return a + _yawrot(p - a, dth) + dtv


func _h01(purpose: int, a: int, b: int) -> float:
	var x: int = seed_v & 0xFFFFFFFF
	x = (x ^ ((purpose * 0x9E3779B1) & 0xFFFFFFFF)) & 0xFFFFFFFF
	x = (x ^ ((a * 0x85EBCA77) & 0xFFFFFFFF)) & 0xFFFFFFFF
	x = (x ^ ((b * 0xC2B2AE3D) & 0xFFFFFFFF)) & 0xFFFFFFFF
	x = (x ^ (x >> 15)) & 0xFFFFFFFF
	x = (x * 0x2545F491) & 0xFFFFFFFF
	x = (x ^ (x >> 13)) & 0xFFFFFFFF
	x = (x * 0x27D4EB2F) & 0xFFFFFFFF
	x = (x ^ (x >> 16)) & 0xFFFFFFFF
	return float(x) / 4294967296.0


func _gauss(purpose: int, a: int, b: int) -> float:
	return (_h01(purpose, a, b) + _h01(purpose, a, b + 7919) + _h01(purpose, a, b + 104729) - 1.5) * 1.1547


# ===========================================================================
# the run.  a path, a true pose, a believed pose, and a list of fixes.
# ===========================================================================
var path_pts := PackedVector3Array()      # arc-length samples of the walk
var path_len := 0.0
var walk_speed := 1.50
var stand_pos := Vector3.ZERO
var bel_t := PackedFloat32Array()
var bel_x := PackedFloat32Array()
var bel_z := PackedFloat32Array()
var bel_yaw := PackedFloat32Array()
var run_is_walk := false


func _biggest_chamber() -> Array:
	var best: Array = geo.chamber_m[0]
	for c in geo.chamber_m:
		if float((c as Array)[2]) > float(best[2]):
			best = c
	return best


func _build_path() -> void:
	# a straight-ish run of the main drive, clear of the chambers, walked out
	# and back. The out-and-back is the whole point: it is the only way one
	# wall gets recorded twice and the only way drift becomes visible as a
	# disagreement rather than as a shape you cannot check.
	var ids: PackedInt32Array = geo.topo.edges[0]
	# A cinema bake overrides the search: a trailer shot names a station and
	# the machine has to walk past THAT station, not past whichever run the
	# planner likes best.
	if cine_from >= 0:
		path_pts = PackedVector3Array()
		for i in range(maxi(0, cine_from), mini(ids.size(), cine_to + 1)):
			path_pts.push_back(geo._st_pos(ids[i]))
		path_len = 0.0
		for i in range(1, path_pts.size()):
			path_len += path_pts[i - 1].distance_to(path_pts[i])
		print("walk: stations %d..%d  %d cells  %.1f m" % [
			cine_from, cine_to, path_pts.size(), path_len])
		return
	var start := -1
	var run := 0
	var best_start := 0
	var best_run := 0
	for i in range(ids.size()):
		var p: Vector3 = geo._st_pos(ids[i])
		if geo._in_big_chamber(p, 1.06):
			run = 0
			start = -1
			continue
		if start < 0:
			start = i
		run += 1
		if run > best_run:
			best_run = run
			best_start = start
	var leg_cells: int = mini(best_run - 2, 64)
	path_pts = PackedVector3Array()
	for i in range(best_start + 1, best_start + 1 + leg_cells):
		path_pts.push_back(geo._st_pos(ids[i]))
	path_len = 0.0
	for i in range(1, path_pts.size()):
		path_len += path_pts[i - 1].distance_to(path_pts[i])
	print("walk: stations %d..%d  %d cells  %.1f m each way" % [
		best_start + 1, best_start + leg_cells, leg_cells, path_len])


func _path_at(s: float) -> Array:
	var acc := 0.0
	for i in range(1, path_pts.size()):
		var d: float = path_pts[i - 1].distance_to(path_pts[i])
		if acc + d >= s or i == path_pts.size() - 1:
			var u: float = clampf((s - acc) / maxf(d, 1e-5), 0.0, 1.0)
			var p: Vector3 = path_pts[i - 1].lerp(path_pts[i], u)
			var dir: Vector3 = (path_pts[i] - path_pts[i - 1]).normalized()
			return [p, atan2(dir.z, dir.x)]
		acc += d
	return [path_pts[path_pts.size() - 1], 0.0]


func _true_pose(t: float) -> Array:
	if not run_is_walk:
		return [stand_pos, 0.0]
	if walk_oneway:
		# The belief cut follows a machine walking AWAY from the camera into
		# ground it has not mapped, so there is no return leg. Nothing in the
		# frame is recorded twice, which is correct: shot 18 is the reveal, not
		# the discrepancy.
		var s1: float = clampf(t * walk_speed, 0.0, path_len)
		var r1: Array = _path_at(s1)
		var p1: Vector3 = r1[0]
		return [p1 + Vector3(0, geo._cfloor(p1.x, p1.z) + 0.90, 0), float(r1[1])]
	var half: float = path_len / walk_speed
	var s: float
	var back := false
	if t <= half:
		s = t * walk_speed
	else:
		s = maxf(0.0, path_len - (t - half) * walk_speed)
		back = true
	var r: Array = _path_at(clampf(s, 0.0, path_len))
	var p: Vector3 = r[0]
	var yaw: float = float(r[1])
	if back:
		yaw += PI
	return [p + Vector3(0, geo._cfloor(p.x, p.z) + 0.90, 0), yaw]


# Integrate the believed pose forward at 20 Hz -- phase1's tick rate -- with
# phase1's own dead-reckoning error model, and apply each correction at the
# moment it lands. `fix_spec` is a list of [time, kind] where kind is
# "honest" or "lie".
func _integrate_belief(fix_spec: Array) -> void:
	bel_t = PackedFloat32Array()
	bel_x = PackedFloat32Array()
	bel_z = PackedFloat32Array()
	bel_yaw = PackedFloat32Array()
	fix_log = []
	trail_true = PackedVector3Array()
	trail_bel = PackedVector3Array()
	trail_t = PackedFloat32Array()

	var dt := 0.05
	var n: int = int(ceil(t_end / dt)) + 1
	var tp0: Array = _true_pose(0.0)
	var bp: Vector3 = tp0[0]
	var byaw: float = float(tp0[1])
	var anchor: Vector3 = bp
	var fi := 0
	var step := 0
	for k in range(n):
		var t: float = float(k) * dt
		var tp: Array = _true_pose(t)
		var tpos: Vector3 = tp[0]
		var tyaw: float = float(tp[1])
		if k > 0:
			var prev: Array = _true_pose(t - dt)
			var pprev: Vector3 = prev[0]
			var ds: float = Vector2(tpos.x - pprev.x, tpos.z - pprev.z).length()
			var dyaw: float = wrapf(tyaw - float(prev[1]), -PI, PI)
			var cells: float = ds / CELL
			byaw += dyaw
			byaw += deg_to_rad(DR_HEADING_BIAS_DEG_PER_CELL) * cells
			byaw += deg_to_rad(DR_HEADING_NOISE_DEG_PER_CELL) * sqrt(maxf(cells, 0.0)) * _gauss(41, step, 0)
			var fwd: Vector3 = _yawrot(Vector3(ds, 0, 0), byaw)
			var jitter: float = DR_POS_NOISE_PER_CELL * CELL * sqrt(maxf(cells, 0.0))
			bp += fwd + Vector3(_gauss(42, step, 0) * jitter, 0, _gauss(42, step, 1) * jitter)
			bp.y = _gauge_y(tpos.y, seed_v, step)
			step += 1
		else:
			bp.y = _gauge_y(tpos.y, seed_v, step)

		# a correction lands between this tick and the last
		while fi < fix_spec.size() and float((fix_spec[fi] as Array)[0]) <= t:
			var spec: Array = fix_spec[fi]
			var kind: String = spec[1]
			var target_p: Vector3
			var target_yaw: float
			if kind == "lie":
				# The rival has cloned a beacon and put it where it is not.
				# The SAME code runs; only the answer is wrong.
				var away: Vector3 = _yawrot(Vector3(float(spec[2]), 0, 0), byaw + float(spec[3]))
				target_p = bp + away
				target_yaw = byaw + float(spec[4])
			else:
				target_p = Vector3(tpos.x, bp.y, tpos.z) \
					+ Vector3(_gauss(43, fi, 0) * 0.10, 0, _gauss(43, fi, 1) * 0.10)
				target_yaw = tyaw + deg_to_rad(0.4) * _gauss(43, fi, 2)
			var dth: float = wrapf(target_yaw - byaw, -PI, PI)
			var moved: Vector3 = _apply_fix(bp, anchor, dth, Vector3.ZERO)
			var dtv: Vector3 = target_p - moved
			var jump: float = bp.distance_to(target_p)
			fix_log.append({"t": float(spec[0]), "anchor": anchor, "dth": dth, "dtv": dtv,
							"jump": jump, "lie": kind == "lie"})
			bp = target_p
			byaw = target_yaw
			anchor = bp
			fi += 1

		bel_t.push_back(t)
		bel_x.push_back(bp.x)
		bel_z.push_back(bp.z)
		bel_yaw.push_back(byaw)
		if k % 4 == 0:
			trail_true.push_back(tpos)
			trail_bel.push_back(Vector3(bp.x, bp.y, bp.z))
			trail_t.push_back(t)


func _bel_pose(t: float) -> Array:
	var i: int = clampi(int(t / 0.05), 0, bel_t.size() - 1)
	return [Vector3(bel_x[i], 0.0, bel_z[i]), bel_yaw[i]]


# ===========================================================================
# the bake.  sweep, place, pack.
# ===========================================================================
func _make_scan(kind: String) -> LidarScan:
	var s := LidarScan.new()
	s.seed_v = seed_v
	if kind == "toy_lidar":
		# phase1/tuning.py, verbatim: LIDAR_RAYS 90, LIDAR_ARC_DEG 360,
		# LIDAR_RANGE 18 cells, LIDAR_PERIOD_S 1.5. One horizontal plane.
		s.rings = 1
		s.el_min_deg = 0.0
		s.el_max_deg = 0.0
		s.az_steps = 90
		s.spin_hz = 1.0 / 1.5
		s.range_max = 18.0 * CELL
		s.range_min = 0.12
		s.range_sigma = 0.08 * CELL
		s.det_floor = 0.0001
		s.beam_div_mrad = 34.9      # 2 deg of ray spacing, not a beam
	elif kind == "toy_near":
		# NEARFIELD_RAYS 8, NEARFIELD_RANGE 2.5 cells, every 4 ticks.
		s.rings = 1
		s.el_min_deg = 0.0
		s.el_max_deg = 0.0
		s.az_steps = 8
		s.spin_hz = 5.0
		s.range_max = 2.5 * CELL
		s.range_min = 0.10
		s.range_sigma = 0.15 * CELL
		s.det_floor = 0.0001
	return s


# Set by CloudCinema before a `cine_*` bake. Keys: st, lead, fwd, speed,
# rev_dt, oneway, fix ("none" | "honest" | "lie").
var cine_spec: Dictionary = {}

func _bake(name: String) -> void:
	var t0 := Time.get_ticks_msec()
	scene_name = name
	fix_log = []
	var is_cine: bool = name.begins_with("cine_")
	run_is_walk = name in ["walk", "lie", "toy_walk", "real_short"] \
		or (is_cine and name != "cine_stand")

	var ch: Array = _biggest_chamber()
	var cx: float = ch[0]
	var cz: float = ch[1]
	var fy: float = ch[3]
	stand_pos = Vector3(cx + float(ch[2]) * 0.18, fy + geo._cfloor(cx, cz) + 0.90, cz - float(ch[2]) * 0.10)
	sensor_stand = stand_pos

	var scans: Array = []
	var fix_spec: Array = []
	var rev_dt := 0.0

	if not is_cine:
		walk_speed = 1.50
		walk_oneway = false
		cine_from = -1
	if is_cine:
		var ids0: PackedInt32Array = geo.topo.edges[0]
		var st: int = int(cine_spec.get("st", 68))
		walk_speed = float(cine_spec.get("speed", 0.45))
		walk_oneway = bool(cine_spec.get("oneway", true))
		rev_dt = float(cine_spec.get("rev_dt", 0.5))
		scans = [_make_scan("real")]
		if name == "cine_stand":
			# the machine stands `stand_f` metres along the drive from the
			# station and `stand_r` metres off the centreline, which is where a
			# machine the camera is looking at would be
			var i0: int = clampi(st, 0, ids0.size() - 1)
			var i1: int = clampi(st + 1, 0, ids0.size() - 1)
			var sp: Vector3 = geo._st_pos(ids0[i0])
			var fw: Vector3 = geo._st_pos(ids0[i1]) - sp
			fw.y = 0.0
			fw = fw.normalized() if fw.length() > 0.01 else Vector3(1, 0, 0)
			var rt: Vector3 = fw.cross(Vector3.UP).normalized()
			sp += fw * float(cine_spec.get("stand_f", 0.0)) + rt * float(cine_spec.get("stand_r", 0.0))
			stand_pos = Vector3(sp.x, sp.y + geo._cfloor(sp.x, sp.z) + 0.90, sp.z)
			sensor_stand = stand_pos
			t_end = float(cine_spec.get("dur", 0.4))
			cine_from = -1
		else:
			cine_from = maxi(0, st - int(cine_spec.get("lead", 16)))
			cine_to = mini(ids0.size() - 1, st + int(cine_spec.get("fwd", 26)))
			_build_path()
			t_end = (1.0 if walk_oneway else 2.0) * path_len / walk_speed
			var cap: float = float(cine_spec.get("dur", 0.0))
			if cap > 0.0:
				t_end = minf(t_end, cap)
			var kind: String = String(cine_spec.get("fix", "none"))
			# The out-and-back is what makes a corridor get recorded twice, and
			# the fix at the turn is what makes the two records different
			# epochs -- which is the only reason a later correction can close
			# the doubling at all (NOTES.md 5).
			if kind == "honest":
				fix_spec = [[t_end * 0.49, "honest", 0.0, 0.0, 0.0],
							[t_end - 1.2, "honest", 0.0, 0.0, 0.0]]
			elif kind == "lie":
				fix_spec = [[t_end * 0.49, "honest", 0.0, 0.0, 0.0],
							[t_end - 1.2, "lie", 11.0, 1.15, deg_to_rad(26.0)]]
	elif name == "chamber1":
		t_end = 0.10
		scans = [_make_scan("real")]
		rev_dt = 0.10
	elif name == "chamber4":
		t_end = 0.40
		scans = [_make_scan("real")]
		rev_dt = 0.10
	elif name == "toy_stand":
		t_end = 480.0
		scans = [_make_scan("toy_lidar")]
		rev_dt = 1.5
	else:
		_build_path()
		t_end = 2.0 * path_len / walk_speed
		if name == "toy_walk":
			scans = [_make_scan("toy_lidar"), _make_scan("toy_near")]
			rev_dt = 0.0
		elif name == "real_short":
			t_end = 2.0 * path_len / walk_speed
			scans = [_make_scan("real")]
			rev_dt = 0.10
		else:
			scans = [_make_scan("real")]
			rev_dt = 1.00
		# The corridor is walked out and back. One correction lands at the
		# turn and closes the outbound leg; the second lands at the end.
		var half: float = path_len / walk_speed
		if name == "lie":
			fix_spec = [[half * 0.98, "honest", 0.0, 0.0, 0.0],
						[t_end - 1.5, "lie", 11.0, 1.15, deg_to_rad(26.0)]]
		else:
			fix_spec = [[half * 0.98, "honest", 0.0, 0.0, 0.0],
						[t_end - 1.5, "honest", 0.0, 0.0, 0.0]]

	_integrate_belief(fix_spec)

	var space := get_world_3d().direct_space_state
	var ts := Time.get_ticks_usec()
	revs = 0
	n_shots = 0
	n_drop = 0
	for sc in scans:
		var s: LidarScan = sc
		s.reset()
		var period: float = 1.0 / s.spin_hz
		var step: float = maxf(rev_dt, period) if rev_dt > 0.0 else period
		if name == "real_short":
			step = period
		var t := 0.0
		var rv := 0
		var limit: float = t_end
		if name == "real_short":
			limit = 0.40         # four revolutions, against the toy's whole walk
		while t < limit:
			var a: Array = _true_pose(t)
			var b: Array = _true_pose(minf(t + period, t_end))
			s.sweep(space, a[0], float(a[1]), b[0], float(b[1]), t, rv)
			rv += 1
			t += step
		revs += rv
		n_shots += s.n_shots
		n_drop += s.n_dropped
	scan_ms = float(Time.get_ticks_usec() - ts) / 1000.0

	_place(scans)
	scan_desc = (scans[0] as LidarScan).describe()
	bake_ms = float(Time.get_ticks_msec() - t0)
	print("[%s] %d returns from %d shots in %d revs  (%.0f%% hit, %.0f%% dropout)  scan %.0f ms  bake %.0f ms"
		% [name, n_pts, n_shots, revs, 100.0 * float(n_pts) / maxf(float(n_shots), 1.0),
		   100.0 * float(n_drop) / maxf(float(n_shots), 1.0), scan_ms, bake_ms])
	now = t_end
	h_lo = cloud_min.y
	h_hi = cloud_max.y
	if run_is_walk and fix_log.size() > 0:
		for f in fix_log:
			var fd: Dictionary = f
			print("    fix at %6.2f s   jump %5.2f m   heading %+5.2f deg   %s" % [
				float(fd["t"]), float(fd["jump"]), rad_to_deg(float(fd["dth"])),
				"LIE" if bool(fd["lie"]) else "honest"])


# Place every measurement at the pose the machine BELIEVED it had when the
# shot was fired, then record where the next correction will put it. This is
# the whole of drift, the fix and the lie: two positions and one time.
func _place(scans: Array) -> void:
	var total := 0
	for sc in scans:
		total += (sc as LidarScan).out_local.size()
	var buf := PackedFloat32Array()
	buf.resize(total * 16)
	cloud_min = Vector3(1e9, 1e9, 1e9)
	cloud_max = Vector3(-1e9, -1e9, -1e9)
	# hoist the fix table: this inner loop runs once per return
	var nf: int = fix_log.size()
	var f_t := PackedFloat32Array()
	var f_th := PackedFloat32Array()
	var f_a := PackedVector3Array()
	var f_d := PackedVector3Array()
	for f in fix_log:
		var fd: Dictionary = f
		f_t.push_back(float(fd["t"]))
		f_th.push_back(float(fd["dth"]))
		f_a.push_back(fd["anchor"])
		f_d.push_back(fd["dtv"])

	var w := 0
	for sc in scans:
		var s: LidarScan = sc
		var n: int = s.out_local.size()
		for i in range(n):
			var t: float = s.out_t[i]
			var bpr: Array = _bel_pose(t)
			var bpos: Vector3 = bpr[0]
			var byaw: float = float(bpr[1])
			var m: Vector3 = s.out_local[i]
			var n0: Vector3 = _yawrot(m, byaw)
			# the believed sensor origin at that instant; the y datum is
			# measured, not dead-reckoned, so drift is planar (as in phase1)
			var org := Vector3(bpos.x, _gauge_y(s.out_org[i].y, seed_v, i), bpos.z)
			var p0: Vector3 = org + n0
			var p1: Vector3 = p0
			var n1: Vector3 = n0
			var tf := -1.0
			for fk in range(nf):
				if f_t[fk] > t:
					p1 = _apply_fix(p0, f_a[fk], f_th[fk], f_d[fk])
					n1 = _yawrot(n0, f_th[fk])
					tf = f_t[fk]
					break
			var dp: Vector3 = p1 - p0
			var o := w * 16
			buf[o + 0] = dp.x;  buf[o + 1] = n0.x; buf[o + 2] = n1.x;  buf[o + 3] = p0.x
			buf[o + 4] = dp.y;  buf[o + 5] = n0.y; buf[o + 6] = n1.y;  buf[o + 7] = p0.y
			buf[o + 8] = dp.z;  buf[o + 9] = n0.z; buf[o + 10] = n1.z; buf[o + 11] = p0.z
			buf[o + 12] = s.out_int[i]
			buf[o + 13] = t
			buf[o + 14] = tf
			buf[o + 15] = s.out_pack[i]
			cloud_min = cloud_min.min(p0.min(p1))
			cloud_max = cloud_max.max(p0.max(p1))
			w += 1
	n_pts = total
	mm.instance_count = 0
	mm.instance_count = total
	if total > 0:
		mm.buffer = buf


# ===========================================================================
# camera, uniforms, lines
# ===========================================================================
func _update_camera() -> void:
	var d := Vector3(cos(orbit_el) * cos(orbit_az), sin(orbit_el), cos(orbit_el) * sin(orbit_az))
	cam.projection = Camera3D.PROJECTION_PERSPECTIVE
	cam.fov = orbit_fov
	cam.position = orbit_target + d * orbit_dist
	cam.look_at(orbit_target, Vector3.UP)


func _frame_cloud() -> void:
	var c: Vector3 = (cloud_min + cloud_max) * 0.5
	orbit_target = c
	orbit_dist = maxf(8.0, (cloud_max - cloud_min).length() * 0.62)


func _apply_uniforms() -> void:
	var vp: Vector2 = Vector2(get_viewport().get_visible_rect().size)
	mat.set_shader_parameter("u_now", now)
	mat.set_shader_parameter("u_mode", mode)
	mat.set_shader_parameter("u_pt_world", pt_world)
	mat.set_shader_parameter("u_min_px", min_px)
	mat.set_shader_parameter("u_max_px", max_px)
	mat.set_shader_parameter("u_vp", vp)
	mat.set_shader_parameter("u_gain", gain)
	mat.set_shader_parameter("u_age_knee_s", age_knee)
	mat.set_shader_parameter("u_age_floor", age_floor)
	mat.set_shader_parameter("u_h_lo", h_lo)
	mat.set_shader_parameter("u_h_hi", h_hi)
	mat.set_shader_parameter("u_epoch_split", epoch_split)
	mat.set_shader_parameter("u_before", col_before)
	mat.set_shader_parameter("u_after", col_after)
	mat.set_shader_parameter("u_clip_lo", clip_lo)
	mat.set_shader_parameter("u_clip_hi", clip_hi)
	mat.set_shader_parameter("u_square", square)
	mat.set_shader_parameter("u_footprint", footprint)
	mat.set_shader_parameter("u_beam_mrad", 3.0)
	truth_root.visible = show_truth
	for c in truth_root.get_children():
		if c is MeshInstance3D:
			var mi: MeshInstance3D = c
			var sm: StandardMaterial3D = mi.material_override
			sm.emission_energy_multiplier = 0.42 * truth_exposure
		elif c is DirectionalLight3D:
			var dl: DirectionalLight3D = c
			dl.light_energy = (1.6 if dl.rotation_degrees.y > 0.0 else 0.5) * truth_exposure * 2.86
	lines.visible = show_lines
	hud.visible = show_hud
	if show_hud:
		hud.text = _hud_text()


func _hud_text() -> String:
	return "%s   t %.2f / %.2f s\n%s\n%d returns   %d shots   %.0f%% dropout   %s\n%s" % [
		scene_name, now, t_end, scan_desc, n_pts, n_shots,
		100.0 * float(n_drop) / maxf(float(n_shots), 1.0),
		["intensity", "intensity (conventional ramp)", "height", "ring index", "epoch", "range"][mode],
		"fixes: " + str(fix_log.size())]


func _rebuild_lines() -> void:
	line_mesh.clear_surfaces()
	if not show_lines:
		return
	line_mesh.surface_begin(Mesh.PRIMITIVE_LINES)
	# the believed trail, corrected by whichever fix has landed
	for i in range(1, trail_bel.size()):
		if trail_t[i] > now:
			break
		var a: Vector3 = _trail_at(i - 1)
		var b: Vector3 = _trail_at(i)
		line_mesh.surface_set_color(Color(GHOST.r, GHOST.g, GHOST.b, 0.85))
		line_mesh.surface_add_vertex(a + Vector3(0, -0.85, 0))
		line_mesh.surface_add_vertex(b + Vector3(0, -0.85, 0))
	# the sensor head, as a small cross
	var s: Vector3 = _sensor_at(now)
	for d in [Vector3(0.3, 0, 0), Vector3(0, 0.3, 0), Vector3(0, 0, 0.3)]:
		line_mesh.surface_set_color(Color(1, 1, 1, 0.9))
		line_mesh.surface_add_vertex(s - d)
		line_mesh.surface_add_vertex(s + d)
	line_mesh.surface_end()


func _trail_at(i: int) -> Vector3:
	var p: Vector3 = trail_bel[i]
	var t: float = trail_t[i]
	for f in fix_log:
		var fd: Dictionary = f
		if float(fd["t"]) > t:
			if now >= float(fd["t"]):
				return _apply_fix(p, fd["anchor"], float(fd["dth"]), fd["dtv"])
			return p
	return p


func _sensor_at(t: float) -> Vector3:
	var r: Array = _bel_pose(minf(t, t_end))
	var p: Vector3 = r[0]
	var tp: Array = _true_pose(minf(t, t_end))
	var y: float = (tp[0] as Vector3).y
	var out := Vector3(p.x, y, p.z)
	for f in fix_log:
		var fd: Dictionary = f
		if float(fd["t"]) > t and now >= float(fd["t"]):
			return _apply_fix(out, fd["anchor"], float(fd["dth"]), fd["dtv"])
	return out


# ===========================================================================
func _process(dt: float) -> void:
	if playing:
		now += dt * play_rate
		if now > t_end:
			now = 0.0
	if not cam_driven:
		_update_camera()
	_apply_uniforms()
	_rebuild_lines()


func _unhandled_input(e: InputEvent) -> void:
	if e is InputEventMouseMotion and (e as InputEventMouseMotion).button_mask != 0:
		var m: InputEventMouseMotion = e
		orbit_az -= m.relative.x * 0.006
		orbit_el = clampf(orbit_el + m.relative.y * 0.006, -1.5, 1.5)
	elif e is InputEventMouseButton and (e as InputEventMouseButton).pressed:
		var b: InputEventMouseButton = e
		if b.button_index == MOUSE_BUTTON_WHEEL_UP: orbit_dist *= 0.9
		elif b.button_index == MOUSE_BUTTON_WHEEL_DOWN: orbit_dist *= 1.11
	elif e is InputEventKey and (e as InputEventKey).pressed:
		var k: InputEventKey = e
		match k.keycode:
			KEY_SPACE: playing = not playing
			KEY_LEFT: now = maxf(0.0, now - t_end * 0.02)
			KEY_RIGHT: now = minf(t_end, now + t_end * 0.02)
			KEY_1: mode = 0
			KEY_2: mode = 1
			KEY_3: mode = 2
			KEY_4: mode = 3
			KEY_5: mode = 4
			KEY_6: mode = 5
			KEY_T: show_truth = not show_truth
			KEY_L: show_lines = not show_lines
			KEY_H: show_hud = not show_hud
			KEY_S: square = 1.0 - square
			KEY_F: footprint = 1.0 - footprint
			KEY_EQUAL: min_px += 0.4
			KEY_MINUS: min_px = maxf(0.4, min_px - 0.4)
			KEY_Q: _bake("chamber1"); _frame_cloud()
			KEY_W: _bake("chamber4"); _frame_cloud()
			KEY_E: _bake("walk"); _frame_cloud()
			KEY_R: _bake("lie"); _frame_cloud()
			KEY_Y: _bake("toy_walk"); _frame_cloud()


# ===========================================================================
# capture
# ===========================================================================
func _settle(frames: int = 8) -> void:
	for i in frames:
		_update_camera()
		_apply_uniforms()
		_rebuild_lines()
		await get_tree().process_frame


func _snap(name: String) -> void:
	await RenderingServer.frame_post_draw
	var img := get_viewport().get_texture().get_image()
	var dir := "res://" + shot_dir
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(dir))
	img.save_png(dir + "/" + name + ".png")
	print("shot %-32s %5d px  %7d pts  %d draws  %s" % [name, img.get_width(), n_pts,
		RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_DRAW_CALLS_IN_FRAME),
		scene_name])


func _reset_view() -> void:
	mode = 0; gain = 1.0; pt_world = 0.020; min_px = 1.6; max_px = 3.6
	clip_lo = -1000.0; clip_hi = 1000.0
	square = 0.0; footprint = 0.0; age_knee = 90.0; age_floor = 0.42
	epoch_split = -1.0; col_before = SENSED; col_after = SENSED
	show_truth = false; truth_exposure = 0.35; show_lines = false; show_hud = false
	orbit_fov = 55.0
	h_lo = cloud_min.y; h_hi = cloud_max.y


func _anchor(nm: String) -> Vector3:
	if nm == "stand":
		return sensor_stand
	if nm == "machine":
		return geo.machine_pos
	if nm == "walk_mid":
		return _true_pose(path_len / walk_speed * 0.5)[0]
	if nm == "walk_far":
		return _true_pose(path_len / walk_speed * 0.96)[0]
	if nm == "walk_qtr":
		return _true_pose(path_len / walk_speed * 0.14)[0]
	if nm == "walk_corr":
		# the point on the walk farthest from any chamber, weighted toward the
		# start of the leg: that is where the return pass has drifted furthest
		# from the outbound record of the same wall.
		var best := 0.0
		var best_s := 0.0
		var half2: float = path_len / walk_speed
		for i in range(60):
			var u: float = float(i) / 59.0
			var p: Vector3 = _true_pose(half2 * u)[0]
			var dmin := 1e9
			for c in geo.chamber_m:
				var cc: Array = c
				dmin = minf(dmin, Vector2(p.x - float(cc[0]), p.z - float(cc[1])).length() - float(cc[2]))
			var score: float = dmin * (1.35 - 0.7 * u)
			if score > best:
				best = score
				best_s = half2 * u
		return _true_pose(best_s)[0]
	return Vector3.ZERO


func _run_shots() -> void:
	for s in SHOTS:
		var d: Dictionary = s
		if shot_filter != "" and not String(d["name"]).contains(shot_filter):
			continue
		if scene_name != String(d["scene"]):
			_bake(String(d["scene"]))
		_reset_view()
		for k in d.keys():
			if k in ["name", "scene", "target", "toff", "tfrac", "tx", "ty", "tz",
					 "clip_rel_hi", "clip_rel_lo", "epoch_fix", "h_rel_lo", "h_rel_hi"]:
				continue
			set(k, d[k])
		if d.has("tfrac"):
			now = t_end * float(d["tfrac"])
		if d.has("toff"):
			now = t_end + float(d["toff"])
		if d.has("epoch_fix") and fix_log.size() > int(d["epoch_fix"]):
			epoch_split = float((fix_log[int(d["epoch_fix"])] as Dictionary)["t"])
		orbit_target = _anchor(String(d["target"])) + Vector3(
			float(d.get("tx", 0.0)), float(d.get("ty", 0.0)), float(d.get("tz", 0.0)))
		if d.has("h_rel_lo"):
			h_lo = orbit_target.y + float(d["h_rel_lo"])
		if d.has("h_rel_hi"):
			h_hi = orbit_target.y + float(d["h_rel_hi"])
		if d.has("clip_rel_hi"):
			clip_hi = orbit_target.y + float(d["clip_rel_hi"])
		if d.has("clip_rel_lo"):
			clip_lo = orbit_target.y + float(d["clip_rel_lo"])
		await _settle(10)
		await _snap(String(d["name"]))
	_run_stats()


func _run_cinema() -> void:
	await cinema.run(self)
	get_tree().quit()


func _run_stats() -> void:
	# The comparison the previous pass asked for: the toy simulation's sensor
	# and a real scanning one, over the SAME ground, measured rather than
	# argued. See LIDAR.md section 6.
	print("\n--- what the sensor decision is worth ---------------------------------")
	print("%-12s %-44s %10s %9s %11s" % ["scene", "sensor", "returns", "seconds", "returns/s"])
	for r in ["toy_walk", "walk", "real_short", "toy_stand", "chamber1"]:
		_bake(r)
		var dur: float = t_end
		if r == "real_short":
			dur = 0.40
		print("%-12s %-44s %10d %8.1fs %11.0f" % [r, scan_desc.substr(0, 44), n_pts, dur,
			float(n_pts) / maxf(dur, 0.001)])
	print("-----------------------------------------------------------------------")
	get_tree().quit()


# ---------------------------------------------------------------- shot list
const SHOTS := [
	# --- one revolution from a standing machine ----------------------------
	{"name": "01_single_sweep", "scene": "chamber1", "target": "stand",
	 "orbit_az": 2.35, "orbit_el": 0.40, "orbit_dist": 17.0, "ty": 0.4, "mode": 0},
	{"name": "02_occlusion_shadows", "scene": "chamber1", "target": "stand",
	 "orbit_az": 2.35, "orbit_el": 0.95, "orbit_dist": 15.0, "ty": 0.0, "mode": 0},
	{"name": "03_occlusion_with_truth", "scene": "chamber1", "target": "stand",
	 "orbit_az": 2.35, "orbit_el": 0.80, "orbit_dist": 7.6, "ty": -0.7, "mode": 0,
	 "show_truth": true, "truth_exposure": 0.30, "pt_world": 0.014},
	{"name": "04_rings_countable", "scene": "chamber1", "target": "stand",
	 "orbit_az": 2.60, "orbit_el": 0.26, "orbit_dist": 6.2, "ty": -0.3, "mode": 3,
	 "min_px": 2.0, "pt_world": 0.024},
	{"name": "05_rings_plan", "scene": "chamber1", "target": "stand",
	 "orbit_az": 1.57, "orbit_el": 1.40, "orbit_dist": 19.0, "ty": 0.0, "mode": 0},
	# --- four revolutions: the colour channels -----------------------------
	{"name": "06_intensity", "scene": "chamber4", "target": "stand",
	 "orbit_az": 1.15, "orbit_el": 0.28, "orbit_dist": 13.0, "ty": 0.3, "mode": 0},
	{"name": "07_intensity_conventional", "scene": "chamber4", "target": "stand",
	 "orbit_az": 1.15, "orbit_el": 0.28, "orbit_dist": 13.0, "ty": 0.3, "mode": 1},
	{"name": "08_height", "scene": "chamber4", "target": "stand",
	 "orbit_az": 1.15, "orbit_el": 0.28, "orbit_dist": 13.0, "ty": 0.3, "mode": 2,
	 "h_rel_lo": -1.1, "h_rel_hi": 3.2},
	{"name": "09_first_person", "scene": "chamber4", "target": "machine",
	 "orbit_az": 2.05, "orbit_el": 0.10, "orbit_dist": 5.5, "mode": 0,
	 "orbit_fov": 62.0, "pt_world": 0.012, "max_px": 3.0},
	# --- the walk ----------------------------------------------------------
	{"name": "10_accumulated_walk", "scene": "walk", "target": "walk_mid",
	 "orbit_az": 0.46, "orbit_el": 0.56, "orbit_dist": 46.0, "ty": 0.4, "mode": 2,
	 "tfrac": 1.0, "clip_rel_hi": 1.6, "age_floor": 1.0,
	 "h_rel_lo": -2.3, "h_rel_hi": 1.75, "pt_world": 0.014, "min_px": 1.4},
	# --- drift: two passes down one corridor that do not agree -------------
	{"name": "11_drift_two_passes", "scene": "walk", "target": "walk_corr",
	 "orbit_az": 1.57, "orbit_el": 1.45, "orbit_dist": 13.0, "mode": 4,
	 "toff": -2.2, "epoch_fix": 0, "col_before": SENSED, "col_after": LIE,
	 "age_floor": 1.0, "clip_rel_hi": 0.55, "min_px": 1.8, "pt_world": 0.012},
	{"name": "12_drift_close", "scene": "walk", "target": "walk_corr",
	 "orbit_az": 0.10, "orbit_el": 0.22, "orbit_dist": 9.0, "mode": 4,
	 "toff": -2.2, "epoch_fix": 0, "col_before": SENSED, "col_after": LIE,
	 "age_floor": 1.0, "min_px": 1.7, "pt_world": 0.010, "max_px": 2.8},
	# --- the fix, with NO annotation: intensity only -----------------------
	{"name": "13_fix_before", "scene": "walk", "target": "walk_corr",
	 "orbit_az": 1.57, "orbit_el": 1.45, "orbit_dist": 13.0, "mode": 0,
	 "toff": -2.2, "age_floor": 1.0, "clip_rel_hi": 0.55, "min_px": 1.8,
	 "pt_world": 0.012},
	{"name": "14_fix_after", "scene": "walk", "target": "walk_corr",
	 "orbit_az": 1.57, "orbit_el": 1.45, "orbit_dist": 13.0, "mode": 0,
	 "toff": 0.0, "age_floor": 1.0, "clip_rel_hi": 0.55, "min_px": 1.8,
	 "pt_world": 0.012},
	{"name": "15_fix_before_perspective", "scene": "walk", "target": "walk_corr",
	 "orbit_az": 0.10, "orbit_el": 0.22, "orbit_dist": 9.0, "mode": 0,
	 "toff": -2.2, "age_floor": 1.0, "min_px": 1.7, "pt_world": 0.010, "max_px": 2.8},
	{"name": "16_fix_after_perspective", "scene": "walk", "target": "walk_corr",
	 "orbit_az": 0.10, "orbit_el": 0.22, "orbit_dist": 9.0, "mode": 0,
	 "toff": 0.0, "age_floor": 1.0, "min_px": 1.7, "pt_world": 0.010, "max_px": 2.8},
	# --- what the sensor decision is worth: the SAME walk, both sensors ----
	{"name": "20_real_sensor_whole_walk", "scene": "walk", "target": "walk_mid",
	 "orbit_az": 0.46, "orbit_el": 0.56, "orbit_dist": 46.0, "ty": 0.4, "mode": 0,
	 "tfrac": 1.0, "min_px": 2.0, "age_floor": 1.0, "clip_rel_hi": 1.6},
	{"name": "19_toy_sensor_whole_walk", "scene": "toy_walk", "target": "walk_mid",
	 "orbit_az": 0.46, "orbit_el": 0.56, "orbit_dist": 46.0, "ty": 0.4, "mode": 0,
	 "tfrac": 1.0, "min_px": 2.0, "age_floor": 1.0, "clip_rel_hi": 1.6},
	# --- the rival's lie ---------------------------------------------------
	{"name": "17_lie_before", "scene": "lie", "target": "walk_mid",
	 "orbit_az": 1.57, "orbit_el": 1.45, "orbit_dist": 40.0, "mode": 0,
	 "toff": -2.2, "age_floor": 1.0, "clip_rel_hi": 1.6, "min_px": 1.7,
	 "pt_world": 0.010},
	{"name": "18_lie_after", "scene": "lie", "target": "walk_mid",
	 "orbit_az": 1.57, "orbit_el": 1.45, "orbit_dist": 40.0, "mode": 0,
	 "toff": 0.0, "age_floor": 1.0, "clip_rel_hi": 1.6, "min_px": 1.7,
	 "pt_world": 0.010},
]
