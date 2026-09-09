# ---------------------------------------------------------------------------
# BLINDSIDE cave spike -- scene assembly, the walk, the measurements.
#
# Renders into a SubViewport of exactly 1920x1080 so the numbers and the PNGs
# are both at 1080p regardless of what the desktop's DPI scaling does to the
# window. The window shows that viewport.
#
# Command line (after a bare --):
#   --seed=N        cave seed (default 7)
#   --len=N         stretch length in cells, 0.6 m each (default 240 = 144 m)
#   --noshadow      lamp casts no shadows
#   --nofog         no volumetric silt
#   --noprops       shell only, no scatter -- the "empty corridor" control
#   --novis         disable every visibility range: what the one lamp bought
#   --walkonly      skip the scripted screenshots
#   --stay          do not quit at the end
# ---------------------------------------------------------------------------
extends Node3D

const SHOT_DIR := "res://shots/"
const CSV_PATH := "res://metrics.csv"

var cfg := {
	"seed": 7, "len": 240, "shadow": true, "fog": true, "props": true,
	"vis": true, "walkonly": false, "stay": false, "shotsonly": false,
	"speed": 1.7, "shotdir": "", "shotset": "legacy", "ssao": false,
	"pom": true, "scales": true, "water": true,
}

var sub: SubViewport
var cam: Camera3D
var lamp: SpotLight3D
var world_root: Node3D
var topo: CaveTopology
var dress: CaveDressing

var phase: int = 0            # 0 warmup, 1 walk, 2 shots, 3 done
var t: float = 0.0
var walk_s: float = 0.0       # arc length along the path
var path_len: PackedFloat32Array = PackedFloat32Array()
var total_len: float = 0.0
var samples: Array = []
var csv_lines: PackedStringArray = PackedStringArray()
var gen_ms_topo: float = 0.0
var gen_ms_dress: float = 0.0
var gen_ms_total: float = 0.0
var warmup_frames: int = 0
var hud: Label
var adapter: String = ""
var shot_list: Array = []
var shot_i: int = 0
var busy: bool = false
var shot_dir: String = SHOT_DIR

func _parse_args() -> void:
	var args: PackedStringArray = OS.get_cmdline_user_args()
	var all: PackedStringArray = OS.get_cmdline_args()
	for a in all:
		args.append(a)
	for a in args:
		if a.begins_with("--seed="):
			cfg["seed"] = int(a.substr(7))
		elif a.begins_with("--len="):
			cfg["len"] = int(a.substr(6))
		elif a == "--noshadow":
			cfg["shadow"] = false
		elif a == "--nofog":
			cfg["fog"] = false
		elif a == "--noprops":
			cfg["props"] = false
		elif a == "--novis":
			cfg["vis"] = false
		elif a == "--ssao":
			cfg["ssao"] = true
		elif a == "--nopom":
			cfg["pom"] = false
		elif a == "--noscales":
			cfg["scales"] = false
		elif a == "--nowater":
			cfg["water"] = false
		elif a == "--walkonly":
			cfg["walkonly"] = true
		elif a == "--stay":
			cfg["stay"] = true
		elif a == "--shotsonly":
			cfg["shotsonly"] = true
		elif a.begins_with("--speed="):
			cfg["speed"] = float(a.substr(8))
		elif a.begins_with("--shotdir="):
			cfg["shotdir"] = a.substr(10)
		elif a.begins_with("--shotset="):
			cfg["shotset"] = a.substr(10)

func _stage(msg: String) -> void:
	# stdout is fully buffered when Godot's output is redirected, so progress
	# goes to a file that is closed after every write.
	var f := FileAccess.open("res://progress.log", FileAccess.READ_WRITE)
	if f == null:
		f = FileAccess.open("res://progress.log", FileAccess.WRITE)
	if f:
		f.seek_end()
		f.store_line("%8.2f  %s" % [Time.get_ticks_msec() / 1000.0, msg])
		f.close()

func _ready() -> void:
	var pf := FileAccess.open("res://progress.log", FileAccess.WRITE)
	if pf:
		pf.close()
	_stage("ready")
	_parse_args()
	shot_dir = SHOT_DIR
	if String(cfg["shotdir"]) != "":
		shot_dir = SHOT_DIR + String(cfg["shotdir"]) + "/"
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(shot_dir))

	# --- the 1920x1080 render target -------------------------------------
	var svc := SubViewportContainer.new()
	svc.stretch = true
	svc.set_anchors_preset(Control.PRESET_FULL_RECT)
	var layer := CanvasLayer.new()
	add_child(layer)
	layer.add_child(svc)
	sub = SubViewport.new()
	sub.size = Vector2i(1920, 1080)
	sub.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	sub.msaa_3d = Viewport.MSAA_DISABLED
	sub.screen_space_aa = Viewport.SCREEN_SPACE_AA_FXAA
	sub.positional_shadow_atlas_size = 4096
	svc.add_child(sub)

	world_root = Node3D.new()
	sub.add_child(world_root)

	# --- environment: nothing arrives from infinity ------------------------
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color(0, 0, 0)
	env.ambient_light_source = Environment.AMBIENT_SOURCE_DISABLED
	env.ambient_light_energy = 0.0
	env.tonemap_mode = Environment.TONE_MAPPER_AGX
	env.tonemap_exposure = 1.0
	env.tonemap_white = 6.0
	# SSAO -- MEASURED, AND CUT. Off by default; --ssao turns it on.
	#
	# Godot's SSAO modulates AMBIENT, and ambient here is disabled, so it does
	# nothing at all without ssao_light_affect. Turned onto direct light at
	# 0.55 it cost 4.35 ms of an 8.68 ms GPU frame -- half the frame -- and it
	# was also what produced every one of the 60 ms+ spikes in the walk: the
	# runs with it off were the only stall-free ones. The underfoot frame with
	# and without differs by 0.25% mean absolute pixel value
	# (shots/photoreal/cmp_ssao.png), because the material AO computed from the
	# parallax height field is already doing this job, from the real geometry
	# rather than from the depth buffer, and doing it better.
	#
	# Keeping the code and the switch because the ruling in the note below is
	# still worth having; the technique is simply not worth its price here.
	env.ssao_enabled = cfg["ssao"]
	env.ssao_radius = 0.55
	env.ssao_intensity = 2.4
	env.ssao_power = 1.6
	env.ssao_detail = 0.9
	env.ssao_horizon = 0.10
	env.ssao_sharpness = 0.96
	env.ssao_light_affect = 0.55
	env.ssao_ao_channel_affect = 0.55
	env.glow_enabled = true
	env.glow_intensity = 0.35
	env.glow_bloom = 0.02
	env.glow_hdr_threshold = 1.6
	if cfg["fog"]:
		# ART-DIRECTION 2.6: resting cave volume scatter 0.008-0.012,
		# anisotropy 0.55 (forward-scattering, like silt in water), colour
		# (0.85,0.86,0.90) so it does not blue-shift.
		env.volumetric_fog_enabled = true
		env.volumetric_fog_density = 0.011
		env.volumetric_fog_anisotropy = 0.55
		env.volumetric_fog_albedo = Color(0.85, 0.86, 0.90)
		env.volumetric_fog_emission_energy = 0.0
		env.volumetric_fog_length = 34.0
		env.volumetric_fog_gi_inject = 0.0
	var wenv := WorldEnvironment.new()
	wenv.environment = env
	world_root.add_child(wenv)

	# --- generate ---------------------------------------------------------
	var t0: int = Time.get_ticks_usec()
	topo = CaveTopology.new()
	topo.generate(cfg["seed"], cfg["len"])
	var t1: int = Time.get_ticks_usec()
	_stage("topology done")
	dress = CaveDressing.new()
	dress.stage = _stage
	var geo := Node3D.new()
	world_root.add_child(geo)
	dress.build(topo, cfg["seed"], geo)
	var t2: int = Time.get_ticks_usec()
	_stage("dressing done")
	gen_ms_topo = float(t1 - t0) / 1000.0
	gen_ms_dress = float(t2 - t1) / 1000.0
	gen_ms_total = float(t2 - t0) / 1000.0

	# --- the per-technique ablation switches -------------------------------
	# 0.001, not 0.0: these uniforms are all divisors in a distance ramp, and
	# setting one to zero divides by zero, which makes the ablation row measure
	# a NaN rather than the technique. The first ablation table taken with this
	# switch reported parallax as FREE and three normal scales as a saving,
	# which is what sent me looking.
	if not cfg["pom"]:
		dress.mat_rock.set_shader_parameter("pom_far", 0.001)
	if not cfg["scales"]:
		dress.mat_rock.set_shader_parameter("bump_gain", 0.0)
		dress.mat_rock.set_shader_parameter("detail_far", 0.001)
		dress.mat_rock.set_shader_parameter("micro_far", 0.001)
		dress.mat_rock.set_shader_parameter("floor_bump_far", 0.001)
		dress.mat_stone.set_shader_parameter("detail_far", 0.001)
		dress.mat_stone.set_shader_parameter("micro_far", 0.001)
	if not cfg["water"]:
		for c in geo.get_children():
			for g in c.get_children():
				if g is MultiMeshInstance3D and g.name == "watertile":
					g.visible = false
	if not cfg["props"]:
		for c in geo.get_children():
			for g in c.get_children():
				if g is MultiMeshInstance3D:
					g.visible = false
	if not cfg["vis"]:
		for c in geo.get_children():
			for g in c.get_children():
				if g is GeometryInstance3D:
					g.visibility_range_end = 0.0

	if OS.get_cmdline_user_args().has("--dumpnoise") or OS.get_cmdline_args().has("--dumpnoise"):
		for nm in [["fbm", dress.tex_fbm], ["cel", dress.tex_cel], ["agg", dress.tex_agg], ["cid", dress.tex_cid]]:
			var t3: ImageTexture3D = nm[1]
			var imgs: Array[Image] = t3.get_data()
			print("DBG noise %s slices=%d dim=%dx%dx%d" % [nm[0], imgs.size(), t3.get_width(), t3.get_height(), t3.get_depth()])
			if imgs.size() == 0:
				continue
			var im: Image = imgs[mini(20, imgs.size() - 1)]
			im.convert(Image.FORMAT_RGB8)
			im.save_png(ProjectSettings.globalize_path("res://_noise_dump_%s.png" % nm[0]))
			print("DBG noise %s slice %dx%d fmt %d" % [nm[0], im.get_width(), im.get_height(), im.get_format()])

	# --- beacon pilots: the only standing light, and it is the players' ---
	var nlit: int = 0
	for p in dress.lights:
		var ol := OmniLight3D.new()
		ol.position = p
		ol.light_color = Color(1.0, 0.72, 0.36)
		ol.light_energy = 0.9
		ol.omni_attenuation = 2.0
		ol.omni_range = 2.6
		ol.shadow_enabled = false
		ol.distance_fade_enabled = true
		ol.distance_fade_begin = 16.0
		ol.distance_fade_length = 4.0
		world_root.add_child(ol)
		nlit += 1

	# --- the camera and the one lamp --------------------------------------
	cam = Camera3D.new()
	cam.fov = 46.0
	cam.near = 0.03
	cam.far = 80.0
	sub.add_child(cam)
	lamp = SpotLight3D.new()
	lamp.light_color = Color(1.00, 0.98, 0.95)     # white for every team
	# Re-derived, not inherited. ART-DIRECTION 2.2 is explicit that the wattage
	# is renderer-specific and must be re-derived against the RATIOS whenever
	# the materials move. The floor albedo dropped from the schematic's 0.42 to
	# a measured-plausible 0.19, so the lamp goes up to hold "floor 3 m ahead,
	# grazing, about 0.08 relative luminance".
	lamp.light_energy = 5.4
	lamp.spot_range = 26.0
	lamp.spot_angle = 27.0                          # a 54 degree cone
	lamp.spot_angle_attenuation = 0.40
	lamp.spot_attenuation = 2.0
	lamp.shadow_enabled = cfg["shadow"]
	# Tighter than the first pass. A large bias detaches a small prop's shadow
	# from its own base, which is the classic hovering tell, and the whole point
	# of moving the lamp off the eye was to get those contact shadows back.
	lamp.shadow_bias = 0.020
	lamp.shadow_normal_bias = 1.10
	lamp.light_specular = 1.0
	# The lamp is 0.26 m to the side of and 0.22 m below the sensor. It was
	# 0.10/0.16, which is close enough to co-located that NOTHING in the frame
	# had a modelling shadow: every surface was lit from exactly the direction
	# it was seen from, and that alone made the underfoot read flat. This is the
	# cheapest single photoreal change in the whole pass.
	lamp.position = Vector3(0.26, -0.22, 0.10)
	lamp.rotation_degrees = Vector3(-11.0, 0.0, 0.0) # tilted 11 deg down
	cam.add_child(lamp)

	# --- drips and motes ---------------------------------------------------
	_add_particles()

	# --- path arc length ---------------------------------------------------
	total_len = 0.0
	path_len.push_back(0.0)
	for i in range(1, dress.path_points.size()):
		total_len += dress.path_points[i].distance_to(dress.path_points[i - 1])
		path_len.push_back(total_len)

	hud = Label.new()
	hud.position = Vector2(14, 10)
	hud.add_theme_font_size_override("font_size", 15)
	hud.add_theme_color_override("font_color", Color(0.75, 0.78, 0.8))
	hud.add_theme_color_override("font_outline_color", Color(0, 0, 0))
	hud.add_theme_constant_override("outline_size", 5)
	layer.add_child(hud)

	RenderingServer.viewport_set_measure_render_time(sub.get_viewport_rid(), true)
	adapter = RenderingServer.get_video_adapter_name()
	_build_shot_list()
	_stage("scene ready")

	csv_lines.append("t_s,phase,fps,cpu_process_ms,gpu_ms,draw_calls,primitives,video_mem_mb,x,y,z")
	print("=== BLINDSIDE cave spike ===")
	print("adapter          : %s (%s)" % [adapter, RenderingServer.get_video_adapter_vendor()])
	print("seed             : %d   stretch %d cells = %.1f m" % [cfg["seed"], cfg["len"], float(cfg["len"]) * 0.6])
	print("topology hash    : 0x%08X" % topo.content_hash())
	print("open cells       : %d of %d" % [topo.open_cells(), topo.grid_state.size()])
	print("stations         : %d   edges %d   chambers %d   junctions %d" % [
		topo.stations.size(), topo.edges.size(), topo.chambers.size() / 5, topo.junctions.size()])
	print("gen topology ms  : %.2f" % gen_ms_topo)
	print("gen dressing ms  : %.2f" % gen_ms_dress)
	print("gen total ms     : %.2f" % gen_ms_total)
	print("chunks           : %d" % dress.stat_chunks)
	print("shell triangles  : %d" % dress.stat_shell_tris)
	print("prop instances   : %d  in %d multimeshes  (%d kit parts)" % [
		dress.stat_instances, dress.stat_multimeshes, dress.kit.size()])
	print("beacon pilots    : %d" % nlit)
	var km: ArrayMesh = dress.kit["set"]
	var fmt: int = km.surface_get_format(0)
	var ar: Array = km.surface_get_arrays(0)
	print("DBG kit 'set' surfaces=%d has_color=%s firstcol=%s" % [
		km.get_surface_count(), str((fmt & Mesh.ARRAY_FORMAT_COLOR) != 0),
		str((ar[Mesh.ARRAY_COLOR] as PackedColorArray)[0]) if ar[Mesh.ARRAY_COLOR] != null else "none"])
	print("path length      : %.1f m" % total_len)
	print("flags            : shadow=%s fog=%s props=%s vis=%s ssao=%s" % [cfg["shadow"], cfg["fog"], cfg["props"], cfg["vis"], cfg["ssao"]])

func _add_particles() -> void:
	# drips: where the works are wet. GPU particles, a handful of emitters,
	# each with a visibility range so only the one you are standing under runs.
	var ids: PackedInt32Array = topo.edges[0]
	var made: int = 0
	for i in range(0, ids.size(), 11):
		var s: PackedInt32Array = topo.stations[ids[i]]
		if s[CaveTopology.S_WET] < 130:
			continue
		var p: Vector3 = dress._st_pos(ids[i])
		var pm := GPUParticles3D.new()
		var mat := ParticleProcessMaterial.new()
		mat.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_BOX
		mat.emission_box_extents = Vector3(0.7, 0.02, 0.4)
		mat.direction = Vector3(0, -1, 0)
		mat.spread = 1.0
		mat.initial_velocity_min = 0.2
		mat.initial_velocity_max = 0.5
		mat.gravity = Vector3(0, -9.8, 0)
		mat.scale_min = 0.5
		mat.scale_max = 1.2
		var dm := StandardMaterial3D.new()
		dm.albedo_color = Color(0.55, 0.60, 0.62, 0.7)
		dm.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
		dm.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
		dm.roughness = 0.05
		var dq := QuadMesh.new()
		dq.size = Vector2(0.006, 0.05)
		dq.material = dm
		pm.process_material = mat
		pm.draw_pass_1 = dq
		pm.amount = 26
		pm.lifetime = 1.4
		pm.position = p + Vector3.UP * (dress._ht(s) * 0.85)
		pm.visibility_range_end = 14.0
		pm.explosiveness = 0.0
		world_root.add_child(pm)
		made += 1
		if made > 22:
			break

# --- the scripted shots ----------------------------------------------------
func _find(pred: Callable, from_frac: float = 0.0) -> int:
	var ids: PackedInt32Array = topo.edges[0]
	var start: int = int(float(ids.size()) * from_frac)
	for i in range(start, ids.size()):
		if pred.call(topo.stations[ids[i]]):
			return i
	for i in range(0, start):
		if pred.call(topo.stations[ids[i]]):
			return i
	return int(ids.size() / 2)

# A shot is only useful if the camera can actually see down the passage. Find a
# station where the next `look` stations run straight and the section is at
# least a PASSAGE, so the framing is not a timber post 300 mm from the lens.
func _straight(from_frac: float, look: int, min_w: int) -> int:
	var ids: PackedInt32Array = topo.edges[0]
	var start: int = int(float(ids.size()) * from_frac)
	for i in range(start, ids.size() - look - 2):
		var s0: PackedInt32Array = topo.stations[ids[i]]
		if s0[CaveTopology.S_WIDTH] < min_w:
			continue
		var ok: bool = true
		for j in range(1, look):
			var sj: PackedInt32Array = topo.stations[ids[i + j]]
			if absi(sj[CaveTopology.S_Y] - s0[CaveTopology.S_Y]) > 1 or sj[CaveTopology.S_WIDTH] < min_w:
				ok = false
				break
		if ok:
			return i
	return clampi(start, 1, ids.size() - look - 2)

# where dressing.gd put the beacon at this station. Same rule, read back.
func _beacon_world(i: int) -> Vector3:
	var ids: PackedInt32Array = topo.edges[0]
	var sid: int = ids[clampi(i, 0, ids.size() - 1)]
	var p: Vector3 = dress._st_pos(sid)
	var nxt: Vector3 = dress._st_pos(ids[clampi(i + 1, 0, ids.size() - 1)])
	var tangent: Vector3 = (nxt - p).normalized()
	var right: Vector3 = tangent.cross(Vector3.UP).normalized()
	var hw: float = dress._hw(topo.stations[sid])
	return p + right * (hw * 0.70 * (1.0 if (sid % 2 == 0) else -1.0)) + Vector3.UP * 0.40

func _build_shot_list() -> void:
	var ids: PackedInt32Array = topo.edges[0]
	var has := func(bit: int) -> Callable:
		return func(s: PackedInt32Array) -> bool: return (s[CaveTopology.S_WORKS] & bit) != 0
	var i_rail: int = _straight(0.30, 12, CaveTopology.WC_PASSAGE)
	var i_dense: int = _straight(0.50, 14, CaveTopology.WC_PASSAGE)
	var i_cham: int = topo.chambers[1 * 5 + 4] if topo.chambers.size() >= 10 else int(ids.size() * 0.4)
	var i_plant: int = _find(func(s): return (s[CaveTopology.S_WORKS] & CaveTopology.WK_PLANT) != 0, 0.6)
	var i_flood: int = _find(func(s): return s[CaveTopology.S_STATE] == CaveTopology.FLOODED, 0.4)
	var i_junc: int = topo.junctions[mini(2, topo.junctions.size() - 1)] if topo.junctions.size() > 0 else int(ids.size() * 0.3)
	var i_shallow: int = _find(func(s): return s[CaveTopology.S_WORKED] < 20, 0.02)
	# the frame that has to prove the two registers: a composite tray clipped
	# over a rusted bracket line, with the old iron and a beacon in the same shot
	var i_beacon: int = _find(func(s): return (s[CaveTopology.S_WORKS] & CaveTopology.WK_TRAY) != 0 		and (s[CaveTopology.S_WORKS] & CaveTopology.WK_SETS) != 0 		and (s[CaveTopology.S_WORKS] & CaveTopology.WK_BEACON) != 0, 0.40)
	var i_long: int = _straight(0.62, 22, CaveTopology.WC_PASSAGE)

	# each shot: name, station index on the main drive, eye height, look-ahead
	# stations, yaw offset (rad), pitch offset (rad), fov
	shot_list = [
		["01_wide_passage", i_rail, 1.15, 10, 0.0, -0.03, 48.0],
		["02_dense_mid", i_dense + 3, 1.15, 12, 0.02, -0.02, 46.0],
		["03_underfoot", i_rail + 3, 0.88, 4, 0.02, -0.58, 62.0],
		["04_chamber", i_cham - 5, 1.30, 7, 0.05, 0.02, 58.0],
		["05_two_registers", i_beacon, 1.35, 3, 0.0, 0.05, 46.0, _beacon_world(i_beacon)],
		["06_falloff_to_black", i_long, 0.95, 26, 0.0, 0.03, 40.0],
		["07_junction", i_junc - 4, 1.15, 5, 0.14, -0.05, 56.0],
		["08_waterline", i_flood - 5, 1.05, 9, 0.0, -0.12, 52.0],
		["09_machine_ground", i_plant - 3, 1.30, 4, 0.16, -0.02, 62.0],
		["10_natural_shallow", i_shallow + 4, 1.00, 5, 0.0, -0.08, 50.0],
		["11_set_line", i_dense + 2, 1.20, 13, -0.04, 0.0, 40.0],
		["12_crown", i_dense + 4, 1.05, 6, 0.0, 0.26, 52.0],
	]
	# a station carrying BOTH a timber set and a bolt line, so the iron-against-
	# rock frame is guaranteed rather than hoped for
	var i_iron: int = _find(func(s): return (s[CaveTopology.S_WORKS] & CaveTopology.WK_SETS) != 0 		and (s[CaveTopology.S_WORKS] & CaveTopology.WK_BOLTLINE) != 0 		and (s[CaveTopology.S_WORKS] & CaveTopology.WK_PIPE) != 0, 0.45)
	if String(cfg["shotset"]) == "photoreal":
		# The photoreal pair set. Format is deliberately different from the
		# legacy one so a pose is an ABSOLUTE eye height, yaw offset and pitch
		# -- these frames have to be byte-for-byte the same camera before and
		# after, and a pose derived from a look-ahead point is not, because the
		# look-ahead point moves if anything about the path changes.
		#   [name, station, eye_m, yaw_offset_rad, pitch_rad, fov, "PR"]
		shot_list = [
			["p1_underfoot_macro", i_rail + 3, 1.20, 0.05, -0.785, 50.0, "PR"],
			["p2_wet_floor_water", i_flood - 13, 1.10, 0.0, -0.34, 52.0, "PR"],
			["p3_wall_lamp_dist", i_dense, 1.30, 0.85, -0.06, 46.0, "PR"],
			["p4_bedded_face", i_shallow + 4, 1.10, 1.05, 0.04, 40.0, "PR"],
			# legacy pose format (look-ahead, not absolute pitch): this is the
			# same camera as the old 11_set_line, which is the frame that
			# actually contains sets, a pipe run, mesh and wet floor at once.
			["p5_iron_prop", i_dense + 2, 1.20, 13, -0.04, 0.0, 40.0],
			["p6_wide_passage", i_rail, 1.15, 0.0, -0.10, 48.0, "PR"],
			["p7_ballast_gauge", i_rail + 1, 0.98, 0.03, -0.55, 52.0, "PR"],
			["p8_junction_wet", i_junc - 4, 1.15, 0.14, -0.22, 56.0, "PR"],
		]

func _pose_for(shot: Array) -> Array:
	var ids: PackedInt32Array = topo.edges[0]
	var idx: int = clampi(shot[1], 1, dress.path_points.size() - 2)
	if shot.size() == 7 and typeof(shot[6]) == TYPE_STRING:
		var pp: Vector3 = dress.path_points[idx]
		pp.y = dress._st_pos(ids[idx]).y + float(shot[2])
		var ah: int = clampi(idx + 4, 0, dress.path_points.size() - 1)
		var dd: Vector3 = (dress.path_points[ah] - dress.path_points[idx]).normalized()
		if dd.length() < 0.5:
			dd = Vector3(0, 0, -1)
		return [pp, atan2(-dd.x, -dd.z) + float(shot[3]), float(shot[4]), float(shot[5])]
	if shot.size() > 7:
		# an explicit world target: stand back along the passage and look at it.
		# This is how the two-registers frame is guaranteed rather than hoped for.
		var tgt2: Vector3 = shot[7]
		var bk: int = clampi(idx - maxi(2, int(shot[3])), 0, dress.path_points.size() - 1)
		var back: Vector3 = dress.path_points[bk]
		var eye2: Vector3 = Vector3(back.x, dress._st_pos(ids[bk]).y + float(shot[2]), back.z)
		var d2: Vector3 = (tgt2 - eye2).normalized()
		return [eye2, atan2(-d2.x, -d2.z) + float(shot[4]),
				asin(clampf(d2.y, -1.0, 1.0)) + float(shot[5]), float(shot[6])]
	var eye: float = shot[2]
	var ahead: int = clampi(idx + int(shot[3]), 0, dress.path_points.size() - 1)
	var p: Vector3 = dress.path_points[idx]
	p.y = dress._st_pos(ids[idx]).y + eye
	var tgt: Vector3 = dress.path_points[ahead]
	tgt.y = dress._st_pos(ids[ahead]).y + eye * 0.85
	var dir: Vector3 = (tgt - p).normalized()
	var yaw: float = atan2(-dir.x, -dir.z) + float(shot[4])
	var pitch: float = asin(clampf(dir.y, -1.0, 1.0)) + float(shot[5])
	return [p, yaw, pitch, float(shot[6])]

# ---------------------------------------------------------------------------
func _process(delta: float) -> void:
	if busy:
		return
	t += delta
	match phase:
		0:
			warmup_frames += 1
			# park the camera at the start and let every pipeline compile
			var p: Vector3 = dress.path_points[2]
			cam.global_transform = Transform3D(Basis.looking_at(
				(dress.path_points[8] - p).normalized(), Vector3.UP), p)
			if t > 2.0:
				t = 0.0
				walk_s = 0.0
				if cfg["shotsonly"]:
					phase = 2
					_do_shots()
					return
				phase = 1
		1:
			walk_s += delta * float(cfg["speed"])
			if walk_s >= total_len - 2.0:
				phase = 2 if not cfg["walkonly"] else 3
				t = 0.0
				_finish_walk()
				if phase == 2:
					_do_shots()
				elif not cfg["stay"]:
					get_tree().quit()
				return
			_place_on_path(walk_s)
			_record(1)
		3:
			pass
	_hud()

func _place_on_path(s: float) -> void:
	var i: int = 0
	while i < path_len.size() - 2 and path_len[i + 1] < s:
		i += 1
	var seg: float = maxf(0.001, path_len[i + 1] - path_len[i])
	var f: float = clampf((s - path_len[i]) / seg, 0.0, 1.0)
	var p: Vector3 = dress.path_points[i].lerp(dress.path_points[i + 1], f)
	var j: int = mini(dress.path_points.size() - 1, i + 5)
	var tgt: Vector3 = dress.path_points[j]
	# a little sway so the lamp sweeps rather than stares
	var sway: float = sin(s * 0.35) * 0.22 + sin(s * 0.11) * 0.14
	var dir: Vector3 = (tgt - p).normalized()
	# Godot's camera looks along LOCAL -Z, so the yaw that points it at `dir`
	# is atan2(-dir.x, -dir.z), not atan2(dir.x, dir.z).
	var yaw: float = atan2(-dir.x, -dir.z) + sway
	var pitch: float = sin(s * 0.23) * 0.05 - 0.02
	p.y += sin(s * 2.9) * 0.012
	cam.global_transform = Transform3D(Basis.from_euler(Vector3(pitch, yaw, 0)), p)

func _record(ph: int) -> void:
	var fps: float = Performance.get_monitor(Performance.TIME_FPS)
	var cpu: float = Performance.get_monitor(Performance.TIME_PROCESS) * 1000.0
	var gpu: float = RenderingServer.viewport_get_measured_render_time_gpu(sub.get_viewport_rid())
	var dc: float = Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME)
	var pr: float = Performance.get_monitor(Performance.RENDER_TOTAL_PRIMITIVES_IN_FRAME)
	var vm: float = Performance.get_monitor(Performance.RENDER_VIDEO_MEM_USED) / 1048576.0
	var p: Vector3 = cam.global_position
	samples.append([fps, cpu, gpu, dc, pr, vm])
	csv_lines.append("%.3f,%d,%.2f,%.3f,%.3f,%d,%d,%.1f,%.2f,%.2f,%.2f" % [
		t, ph, fps, cpu, gpu, int(dc), int(pr), vm, p.x, p.y, p.z])

func _hud() -> void:
	var gpu: float = RenderingServer.viewport_get_measured_render_time_gpu(sub.get_viewport_rid())
	hud.text = "seed %d  |  %.0f fps  gpu %.2f ms  |  draws %d  tris %d  |  %.1f / %.1f m  |  %d instances" % [
		cfg["seed"], Performance.get_monitor(Performance.TIME_FPS), gpu,
		int(Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME)),
		int(Performance.get_monitor(Performance.RENDER_TOTAL_PRIMITIVES_IN_FRAME)),
		walk_s, total_len, dress.stat_instances]

func _pct(a: Array, q: float) -> float:
	var v := a.duplicate()
	v.sort()
	return v[clampi(int(float(v.size()) * q), 0, v.size() - 1)]

func _finish_walk() -> void:
	var fps := []
	var gpu := []
	var cpu := []
	var dc := []
	var pr := []
	var vm := []
	# drop the first second: pipeline compilation is a one-off, not the frame
	var skip: int = mini(60, samples.size() / 8)
	for i in range(skip, samples.size()):
		fps.append(samples[i][0]); cpu.append(samples[i][1]); gpu.append(samples[i][2])
		dc.append(samples[i][3]); pr.append(samples[i][4]); vm.append(samples[i][5])
	if fps.is_empty():
		return
	var sum: float = 0.0
	for f in fps:
		sum += f
	print("--- WALK, %d frames at 1920x1080, %.1f m of cave ---" % [fps.size(), total_len])
	print("fps        mean %.1f   p50 %.1f   p05 %.1f (worst 5%%)   min %.1f" % [
		sum / fps.size(), _pct(fps, 0.5), _pct(fps, 0.05), _pct(fps, 0.0)])
	print("gpu ms     p50 %.2f   p95 %.2f   max %.2f" % [_pct(gpu, 0.5), _pct(gpu, 0.95), _pct(gpu, 1.0)])
	print("cpu ms     p50 %.2f   p95 %.2f   max %.2f" % [_pct(cpu, 0.5), _pct(cpu, 0.95), _pct(cpu, 1.0)])
	print("draw calls p50 %d   p95 %d   max %d" % [int(_pct(dc, 0.5)), int(_pct(dc, 0.95)), int(_pct(dc, 1.0))])
	print("primitives p50 %d   p95 %d   max %d" % [int(_pct(pr, 0.5)), int(_pct(pr, 0.95)), int(_pct(pr, 1.0))])
	print("video mem  p50 %.1f MB  max %.1f MB" % [_pct(vm, 0.5), _pct(vm, 1.0)])
	var f := FileAccess.open(CSV_PATH, FileAccess.WRITE)
	if f:
		for l in csv_lines:
			f.store_line(l)
		f.close()
	# a machine-readable one-liner for the notes
	var sf := FileAccess.open("res://summary.txt", FileAccess.WRITE)
	if sf:
		sf.store_line("adapter=%s" % adapter)
		sf.store_line("seed=%d len_cells=%d length_m=%.1f" % [cfg["seed"], cfg["len"], float(cfg["len"]) * 0.6])
		sf.store_line("flags shadow=%s fog=%s props=%s vis=%s" % [cfg["shadow"], cfg["fog"], cfg["props"], cfg["vis"]])
		sf.store_line("topology_hash=0x%08X" % topo.content_hash())
		sf.store_line("gen_ms topo=%.2f dress=%.2f total=%.2f" % [gen_ms_topo, gen_ms_dress, gen_ms_total])
		sf.store_line("chunks=%d shell_tris=%d instances=%d multimeshes=%d" % [
			dress.stat_chunks, dress.stat_shell_tris, dress.stat_instances, dress.stat_multimeshes])
		sf.store_line("fps mean=%.1f p50=%.1f p05=%.1f min=%.1f" % [
			sum / fps.size(), _pct(fps, 0.5), _pct(fps, 0.05), _pct(fps, 0.0)])
		sf.store_line("gpu_ms p50=%.2f p95=%.2f max=%.2f" % [_pct(gpu, 0.5), _pct(gpu, 0.95), _pct(gpu, 1.0)])
		sf.store_line("cpu_ms p50=%.2f p95=%.2f max=%.2f" % [_pct(cpu, 0.5), _pct(cpu, 0.95), _pct(cpu, 1.0)])
		sf.store_line("draws p50=%d p95=%d max=%d" % [int(_pct(dc, 0.5)), int(_pct(dc, 0.95)), int(_pct(dc, 1.0))])
		sf.store_line("prims p50=%d p95=%d max=%d" % [int(_pct(pr, 0.5)), int(_pct(pr, 0.95)), int(_pct(pr, 1.0))])
		sf.store_line("vram_mb p50=%.1f max=%.1f" % [_pct(vm, 0.5), _pct(vm, 1.0)])
		sf.close()

func _do_shots() -> void:
	busy = true
	for si in range(shot_list.size()):
		var shot: Array = shot_list[si]
		var pose: Array = _pose_for(shot)
		cam.fov = pose[3]
		cam.global_transform = Transform3D(Basis.from_euler(Vector3(pose[2], pose[1], 0)), pose[0])
		# let the volumetric fog and the shadow atlas settle
		for k in range(8):
			await RenderingServer.frame_post_draw
		var img: Image = sub.get_texture().get_image()
		_stage("shot " + str(shot[0]))
		var path: String = shot_dir + str(shot[0]) + ".png"
		img.save_png(ProjectSettings.globalize_path(path))
		var dc: int = int(Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME))
		var pr: int = int(Performance.get_monitor(Performance.RENDER_TOTAL_PRIMITIVES_IN_FRAME))
		var gpu: float = RenderingServer.viewport_get_measured_render_time_gpu(sub.get_viewport_rid())
		var cf: Vector3 = -cam.global_transform.basis.z
		var lf: Vector3 = -lamp.global_transform.basis.z
		print("shot %-22s  %dx%d  draws %-5d tris %-8d gpu %.2f ms" % [
			shot[0], img.get_width(), img.get_height(), dc, pr, gpu])
		print("     cam %s  fwd %s   lampfwd %s  dot %.3f" % [
			str(cam.global_position.round()), str(cf.snapped(Vector3(0.01,0.01,0.01))),
			str(lf.snapped(Vector3(0.01,0.01,0.01))), cf.dot(lf)])
	busy = false
	phase = 3
	if not cfg["stay"]:
		await get_tree().create_timer(0.3).timeout
		get_tree().quit()
