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
## The rate the trailer is CUT at. See the note in _cin_seq.
const CUT_FPS := 24.0

var cfg := {
	"seed": 7, "len": 240, "shadow": true, "fog": true, "props": true,
	"vis": true, "walkonly": false, "stay": false, "shotsonly": false,
	"speed": 1.7, "shotdir": "", "shotset": "legacy", "ssao": false,
	"pom": true, "scales": true, "water": true,
	"cinema": "", "fx": "all", "shot": "", "seqframes": 0, "capfps": 60.0,
	"stations": "",
	# LEVELS. 1 is the flat cave this spike shipped with and it is the DEFAULT,
	# because spikes/godot/cloud/ cuts its belief frames from these cameras and
	# the current trailer was rendered against seed 7 / 240 / 1 levels. 2..4 is
	# the layered cave of THE-ICE section 5. See VERTICAL.md.
	"levels": 1,
	# THE ASSAYER. It is only ever built on the layered cave, because it stands
	# in the ice band and the flat cave has no ice in it. `--p=` parks its clock
	# at a phase; the stills use it, the sequence sweeps it.
	"assayer": true, "phase": -1.0,
}

var sub: SubViewport
var cam: Camera3D
var lamp: SpotLight3D
var world_root: Node3D
var envr: Environment
var topo: CaveTopology
var dress: CaveDressing
## The machine (TRAILER 11.2). Until 2026-09-09 this spike had none, and said
## so in the note over trailer shot 17. See fleet.gd and res://machines/.
var fleet: CaveFleet

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
var rig: CameraRig
var grade: CinemaGrade
var geo_root: Node3D
var cin_shots: Array = []

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
		elif a.begins_with("--cinema="):
			cfg["cinema"] = a.substr(9)
		elif a.begins_with("--fx="):
			cfg["fx"] = a.substr(5)
		elif a.begins_with("--shot="):
			cfg["shot"] = a.substr(7)
		elif a.begins_with("--stations="):
			cfg["stations"] = a.substr(11)
		elif a.begins_with("--seqframes="):
			cfg["seqframes"] = int(a.substr(12))
		elif a.begins_with("--levels="):
			cfg["levels"] = clampi(int(a.substr(9)), 1, 4)
		elif a == "--vertical":
			cfg["levels"] = 4
		elif a.begins_with("--p="):
			cfg["phase"] = float(a.substr(4))
		elif a == "--noassayer":
			cfg["assayer"] = false

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
		# 0.011 is the top of ART-DIRECTION 2.6's 0.008-0.012 band and it was
		# chosen against a rock cave. Ice returns about twice as much light, so
		# the same density reads as milk in the ice band; 0.009 is inside the
		# same band and keeps the beam without hazing the walls.
		env.volumetric_fog_density = 0.009
		env.volumetric_fog_anisotropy = 0.55
		env.volumetric_fog_albedo = Color(0.85, 0.86, 0.90)
		env.volumetric_fog_emission_energy = 0.0
		env.volumetric_fog_length = 34.0
		env.volumetric_fog_gi_inject = 0.0
	envr = env
	var wenv := WorldEnvironment.new()
	wenv.environment = env
	world_root.add_child(wenv)

	# --- generate ---------------------------------------------------------
	var t0: int = Time.get_ticks_usec()
	topo = CaveTopology.new()
	topo.generate(cfg["seed"], cfg["len"], cfg["levels"])
	var t1: int = Time.get_ticks_usec()
	_stage("topology done")
	dress = CaveDressing.new()
	dress.stage = _stage
	var geo := Node3D.new()
	world_root.add_child(geo)
	geo_root = geo
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
		dress.set_rock_param("pom_far", 0.001)
	if not cfg["scales"]:
		dress.set_rock_param("bump_gain", 0.0)
		dress.set_rock_param("detail_far", 0.001)
		dress.set_rock_param("micro_far", 0.001)
		dress.set_rock_param("floor_bump_far", 0.001)
		dress.set_ice_param("bump_gain", 0.0)
		dress.set_ice_param("detail_far", 0.001)
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

	# --- DAYLIGHT DOWN THE COLLAR -----------------------------------------
	# ART-DIRECTION 2.1's fifth row, added by THE-ICE 2.7: "the sky ... the
	# same light as the shaft's, and the shaft's row becomes the last of it."
	# It is 12000 K, it reaches about three metres, and then it stops. This is
	# the only light in the cave that is not carried or dropped.
	if topo.levels > 1 and topo.pitches.size() > 0:
		var cpr: PackedInt32Array = topo.pitch(0)
		if (cpr[CaveTopology.P_FLAGS] & CaveTopology.PF_DAYLIGHT) != 0:
			var sky := OmniLight3D.new()
			sky.position = Vector3(float(cpr[CaveTopology.P_X]) * 0.6,
				float(cpr[CaveTopology.P_TOP_MM]) * 0.001 + 1.4,
				float(cpr[CaveTopology.P_Y]) * 0.6)
			sky.light_color = Color(0.60, 0.74, 1.00)
			sky.light_energy = 19.0
			sky.omni_range = 15.0
			sky.omni_attenuation = 2.6
			sky.shadow_enabled = false
			world_root.add_child(sky)
			sky_light = sky
			print("daylight         : collar at %s, 12000 K, range %.1f m" % [
				str(sky.position.round()), sky.omni_range])

	# --- THE ASSAYER ------------------------------------------------------
	# spikes/godot/assayer/ built the machine; this brings it in. Four files
	# were copied verbatim (assayer.gd, materials.gd, mb.gd, chamber.gdshader)
	# and NOTHING in them was edited -- the cycle, the mechanism, the two hot
	# points and the calibrated 72 are that spike's and stay that spike's.
	#
	# It stands in the largest chamber on level 0, in the ice. See
	# dressing.gd's _dress_assayer_site() for why that is a fiction decision
	# and how it is reconciled.
	if cfg["assayer"] and topo.levels > 1:
		var wy: float = -1000.0
		if topo.level_water_mm.size() > 0 and topo.level_water_mm[0] > -1000000:
			wy = float(topo.level_water_mm[0]) * 0.001
		asy_mats = AssayerMaterials.new()
		asy_mats.build(cfg["seed"], wy)
		machine = Assayer.new()
		var ap: Vector3 = dress.assayer_pos()
		# _base_y is captured inside build(), so the position has to be set
		# BEFORE it: the recoil is measured from wherever it was standing.
		machine.position = ap
		world_root.add_child(machine)
		machine.build(asy_mats, cfg["seed"])
		machine.set_phase(0.0)
		# THE ANVIL RING LEAKS THROUGH THE SHELL, and the fix is NOT shadows.
		#
		# The assayer spike's chamber was the entire world, so nothing was ever
		# outside it; here the chamber is a 6.4 m dome with eighty metres of
		# passage around it, and six shadowless omnis at the mast foot light
		# the dome from the inside and make it glow like a paper lantern from
		# any camera in the drive. The first `a9_the_room` was a photograph of
		# exactly that: a lit egg, seen from outside, in a black void.
		#
		# I turned shadows on for them and the machine went dark, which is
		# assayer/NOTES.md 4.1's first bug arriving on schedule: the ring sits
		# at r = 0.62, INSIDE the anvil's own chamfer, so a shadowed source
		# there is a source sealed in a casting. That is why the ring is
		# shadowless, and it stays shadowless. The range comes down instead --
		# 12 m reaches the dome, 6.0 dies before it -- and the cameras stay
		# inside the room, which they have to anyway.
		for ol in machine.anvil_lights:
			(ol as OmniLight3D).omni_range = 6.0
		# AND THE HOT ENERGY IS RE-DERIVED, which assayer/NOTES.md 4 requires
		# rather than permits: "It is a RATIO, not a wattage, and
		# ART-DIRECTION 2.2 is explicit that it does not survive a change of
		# renderer." It does not survive a change of ROOM either. 72 was
		# calibrated against a chamber of rock at albedo 0.19-0.32; this
		# machine stands in a tube of ice whose first-scatter albedo is 0.34
		# to 0.60, so the same output comes back about twice as strong and the
		# whole sequence measured 0.1-3.6% true black against a 70% floor.
		# Halving it puts the ice band back inside the contract and, more to
		# the point, makes the strike read as a FLASH instead of as a flood.
		machine.hot_energy = 34.0
		machine.set_phase(0.0)
		print("assayer          : chamber %d at %s   %d tris   mast %.1f m, chamber r %.1f m" % [
			dress.assayer_chamber(), str(ap.round()), machine.stat_tris,
			Assayer.MAST_TOP, dress.assayer_radius()])

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
	# BOTH HASHES, EVERY RUN. The flat cave is regenerated from scratch and its
	# hash printed beside the built one, so a machine can tell the two schemas
	# apart and can see that the flat path still produces what it always did.
	# spikes/godot/cloud/ matches its belief frames to THIS cave's cameras.
	var v1 := CaveTopology.new()
	v1.generate(cfg["seed"], cfg["len"], 1)
	var v1h: int = v1.content_hash()
	print("topology schema  : v%d  (%d level%s)" % [
		topo.schema_version(), topo.levels, "" if topo.levels == 1 else "s"])
	print("topology hash    : 0x%08X" % topo.content_hash())
	print("topology hash v1 : 0x%08X   (flat path, same seed and length)" % v1h)
	if cfg["seed"] == 7 and cfg["len"] == 240:
		print("v1 regression    : %s   (recorded 0x%08X)" % [
			"PASS" if v1h == CaveTopology.V1_SEED7_LEN240_HASH else "FAIL",
			CaveTopology.V1_SEED7_LEN240_HASH])
	print("open cells       : %d of %d" % [topo.open_cells(), topo.grid_state.size()])
	print("stations         : %d   edges %d   chambers %d   junctions %d" % [
		topo.stations.size(), topo.edges.size(), topo.chambers.size() / CaveTopology.CH_ROW,
		topo.junctions.size()])
	print("vertical range   : %.1f m   datum %.1f m   melt front %.1f m" % [
		float(topo.vertical_range_mm()) * 0.001, float(topo.datum_mm) * 0.001,
		float(topo.melt_mm) * 0.001])
	print("connectivity     : reachable %d of %d open cells   RETURNABLE %d (%.1f%%)" % [
		topo.reach_down, topo.open_cells(), topo.reach_up,
		100.0 * float(topo.reach_up) / float(maxi(1, topo.open_cells()))])
	print("ceiling invariant: %d violations" % topo.ceil_violations)
	if topo.pitches.size() > 0:
		print("pitches          : %d" % topo.pitches.size())
		for pi in range(topo.pitches.size()):
			var prw: PackedInt32Array = topo.pitch(pi)
			print("  %-9s L%d->L%d  drop %6.1f m  bore %4.2f m  %-8s %-8s down=%s up=%s flow=%d" % [
				CaveTopology.PK_NAME[prw[CaveTopology.P_KIND]],
				prw[CaveTopology.P_FROM_LEVEL], prw[CaveTopology.P_TO_LEVEL],
				float(prw[CaveTopology.P_DROP_MM]) * 0.001,
				float(prw[CaveTopology.P_BORE_MM]) * 0.001,
				CaveTopology.CL_NAME[prw[CaveTopology.P_CLIMB]],
				CaveTopology.MED_NAME[prw[CaveTopology.P_MEDIUM]],
				"Y" if (prw[CaveTopology.P_FLAGS] & CaveTopology.PF_DOWN) != 0 else "n",
				"Y" if (prw[CaveTopology.P_FLAGS] & CaveTopology.PF_UP) != 0 else "n",
				prw[CaveTopology.P_FLOW]])
		var medn := PackedInt32Array([0, 0, 0, 0])
		for i in range(topo.stations.size()):
			medn[(topo.stations[i] as PackedInt32Array)[CaveTopology.S_MEDIUM]] += 1
		print("media            : rock %d  worked %d  ice %d  ice-over-rock %d" % [
			medn[0], medn[1], medn[2], medn[3]])
		for L in range(topo.levels):
			var nst: int = 0
			for i in range(topo.stations.size()):
				if (topo.stations[i] as PackedInt32Array)[CaveTopology.S_LEVEL] == L:
					nst += 1
			print("  level %d        : datum %7.1f m  band %d  %3d stations  water %s" % [
				L, float(CaveTopology.LEVEL_DATUM_MM[L]) * 0.001,
				topo.band_of(int(CaveTopology.LEVEL_DATUM_MM[L])), nst,
				("%.1f m" % (float(topo.level_water_mm[L]) * 0.001)) if topo.level_water_mm[L] > -1000000 else "dry"])
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
	if String(cfg["cinema"]) != "":
		_cinema_setup()

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
	var i_cham: int = topo.chambers[1 * CaveTopology.CH_ROW + CaveTopology.CH_SID] if topo.chambers.size() >= 2 * CaveTopology.CH_ROW else int(ids.size() * 0.4)
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
	if String(cfg["shotset"]) == "vertical":
		shot_list = _build_vertical_shots()
		return
	if String(cfg["shotset"]) == "ice":
		shot_list = _build_ice_shots()
		return
	if String(cfg["shotset"]) == "assayer":
		shot_list = _build_assayer_shots()
		return
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
	# VW: an absolute world pose. The vertical frames are posed against the
	# topology's own geometry (a pitch axis, a chamber floor) rather than
	# against a station index on one drive, because there is no longer one
	# drive.
	# "VW" is an absolute world pose. A SEVENTH element on a VW shot is the
	# Assayer's phase for that frame -- the machine is a pure function of one
	# clock, so a still of it is a camera plus a number.
	if shot.size() >= 6 and typeof(shot[5]) == TYPE_STRING and String(shot[5]) == "VW":
		return [shot[1], float(shot[2]), float(shot[3]), float(shot[4])]
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

# ===========================================================================
# THE VERTICAL SHOT SET -- posed against the topology, not against one drive
# ===========================================================================
func _look_pose(nm: String, from: Vector3, to: Vector3, fov: float) -> Array:
	var d: Vector3 = to - from
	if d.length() < 0.0001:
		d = Vector3(0, 0, -1)
	d = d.normalized()
	return [nm, from, atan2(-d.x, -d.z), asin(clampf(d.y, -1.0, 1.0)), fov, "VW"]

func _main_pitch(from_level: int) -> int:
	for pi in range(topo.pitches.size()):
		var pr: PackedInt32Array = topo.pitch(pi)
		if (pr[CaveTopology.P_FLAGS] & CaveTopology.PF_MAIN) == 0:
			continue
		if pr[CaveTopology.P_KIND] == CaveTopology.PK_COLLAR:
			continue
		if pr[CaveTopology.P_FROM_LEVEL] == from_level:
			return pi
	return -1

func _pitch_t_at_y(pi: int, y: float) -> float:
	var pr: PackedInt32Array = topo.pitch(pi)
	var top: float = float(pr[CaveTopology.P_TOP_MM]) * 0.001
	var bot: float = float(_st_of(pr[CaveTopology.P_TO_ST])[CaveTopology.S_CEIL_MM]) * 0.001
	if absf(top - bot) < 0.01:
		return 0.5
	return clampf((top - y) / (top - bot), 0.0, 1.0)

func _st_of(sid: int) -> PackedInt32Array:
	return topo.stations[sid]

# A CAMERA MUST STAND ON THE DRIVE CENTRELINE. The chamber dome is a 5-7 m
# hemisphere and the swept passage is a 2.9 m tube running THROUGH it, so
# anywhere off the centreline by more than the tube's half width is inside the
# tube's wall and the frame is a grey slab. That is cave/NOTES.md 7's
# "chamber interpenetration" weakness, met head-on by a vertical camera.
func _on_drive(level: int, sid: int, back: int, eye: float) -> Vector3:
	var ids: PackedInt32Array = topo.edges[topo.level_main_edge[level]]
	var at: int = 0
	for i in range(ids.size()):
		if ids[i] == sid:
			at = i
			break
	var j: int = clampi(at + back, 0, ids.size() - 1)
	return dress._st_pos(ids[j]) + Vector3.UP * eye

# the drawn radius of the chamber at this station
func _chamber_r_of(sid: int) -> float:
	var n: int = topo.chambers.size() / CaveTopology.CH_ROW
	for ci in range(n):
		if topo.chambers[ci * CaveTopology.CH_ROW + CaveTopology.CH_SID] == sid:
			return float(topo.chambers[ci * CaveTopology.CH_ROW + CaveTopology.CH_R]) * 0.6 + 1.6
	return 4.0

# a station on `level` whose medium is `med` (or any if med < 0), taken at
# `frac` along that level's main drive and searched forward from there
func _level_station(level: int, med: int, frac: float, min_w: int) -> int:
	if level >= topo.level_main_edge.size():
		return -1
	var ids: PackedInt32Array = topo.edges[topo.level_main_edge[level]]
	var start: int = clampi(int(float(ids.size()) * frac), 1, ids.size() - 8)
	for k in range(ids.size() - 8):
		var i: int = (start + k) % (ids.size() - 8)
		var st: PackedInt32Array = topo.stations[ids[i]]
		if st[CaveTopology.S_WIDTH] < min_w:
			continue
		# never stand in a chamber, at a junction, or at the mouth of a pitch:
		# the section flares over one station there and the frame is a wall
		if st[CaveTopology.S_KIND] != CaveTopology.K_DRIVE:
			continue
		if st[CaveTopology.S_PITCH_HEAD] >= 0 or st[CaveTopology.S_PITCH_FOOT] >= 0:
			continue
		var clear: bool = true
		for k2 in range(-4, 5):
			var jj: int = clampi(i + k2, 0, ids.size() - 1)
			if topo.stations[ids[jj]][CaveTopology.S_KIND] == CaveTopology.K_CHAMBER:
				clear = false
		if not clear:
			continue
		if med >= 0 and st[CaveTopology.S_MEDIUM] != med:
			continue
		return i
	return clampi(start, 1, ids.size() - 8)

func _drive_pose(nm: String, level: int, med: int, frac: float, eye: float,
				 ahead: int, fov: float, dp: float) -> Array:
	var ids: PackedInt32Array = topo.edges[topo.level_main_edge[level]]
	var i: int = _level_station(level, med, frac, CaveTopology.WC_NARROW)
	var a: Vector3 = dress._st_pos(ids[i]) + Vector3.UP * eye
	var j: int = clampi(i + ahead, 0, ids.size() - 1)
	var b: Vector3 = dress._st_pos(ids[j]) + Vector3.UP * (eye * 0.9 + dp)
	return _look_pose(nm, a, b, fov)

func _build_vertical_shots() -> Array:
	var out: Array = []
	var p0: int = _main_pitch(0)
	var p1: int = _main_pitch(1)
	var p2: int = _main_pitch(2)
	var ice_base: float = float(CaveTopology.BAND_ICE_BASE_MM) * 0.001
	var melt: float = float(topo.melt_mm) * 0.001
	# 0 -- the collar, from underneath. The only daylight in the game, three
	# metres of it, seen from the bottom of the hole it comes down.
	if topo.pitches.size() > 0:
		var c0: PackedInt32Array = topo.pitch(0)
		var cf: Vector3 = dress._st_pos(c0[CaveTopology.P_TO_ST])
		out.append(_look_pose("v0_collar_daylight",
			cf + Vector3(1.4, 1.15, 0.9), dress.pitch_axis(0, 0.0) + Vector3.UP * 2.5, 64.0))
	# 1 -- looking DOWN the moulin from the lip. The frame the whole task is
	# about: a hole in the floor with nothing at the bottom of it.
	if p0 >= 0:
		var b0: float = float(topo.pitch(p0)[CaveTopology.P_BORE_MM]) * 0.001
		var lip: Vector3 = dress.pitch_axis(p0, 0.0)
		out.append(_look_pose("v1_down_the_shaft",
			_on_drive(0, topo.pitch(p0)[CaveTopology.P_FROM_ST], -5, 1.30),
			dress.pitch_axis(p0, 0.55), 60.0))
		# 2 -- looking UP it from the bottom, with the beacon chain receding
		# stand UNDER the hole, not beside it: the drive's own crown occludes a
		# ceiling opening from anywhere more than a couple of metres away, which
		# is itself the point -- a machine standing in a chamber cannot see the
		# shaft that dropped into it unless it is directly beneath it.
		out.append(_look_pose("v2_up_from_the_bottom",
			dress._st_pos(topo.pitch(p0)[CaveTopology.P_TO_ST]) + Vector3(0.35, 0.80, 0.20),
			dress.pitch_axis(p0, 0.03), 70.0))
		# 4 -- the meltwater, inside the bore
		var t4: float = 0.30
		var h0: float = float(topo.pitch(p0)[CaveTopology.P_DROP_MM]) * 0.001
		var ang: float = 0.9 + t4 * h0 * 0.26
		out.append(_look_pose("v4_moulin_meltwater",
			dress.pitch_axis(p0, t4 - 0.16) - Vector3(cos(ang), 0.0, sin(ang)) * (b0 * 0.20),
			dress.pitch_axis(p0, t4 + 0.16) + Vector3(cos(ang), 0.0, sin(ang)) * (b0 * 0.46), 62.0))
		# 5 -- the ice-to-rock transition, which happens inside this shaft
		var t5: float = _pitch_t_at_y(p0, ice_base)
		if t5 > 0.06 and t5 < 0.94:
			out.append(_look_pose("v5_ice_to_rock",
				dress.pitch_axis(p0, maxf(0.03, t5 - 0.20)),
				dress.pitch_axis(p0, minf(0.97, t5 + 0.26)), 56.0))
	# 3 -- a chamber with another chamber above it, through the hole in the back
	if p1 >= 0:
		out.append(_look_pose("v3_chamber_below_chamber",
			dress._st_pos(topo.pitch(p1)[CaveTopology.P_TO_ST]) + Vector3(1.9, 1.10, 1.1),
			dress.pitch_axis(p1, 0.06), 74.0))
	# 6 -- the ice band. A meltwater conduit in dead ice, at walking height.
	out.append(_drive_pose("v6_ice_band", 0, CaveTopology.MED_ICE, 0.34, 1.05, 7, 52.0, 0.0))
	# 7 -- the melt front, crossed inside the deepest winze. Nothing marks it.
	if p2 >= 0:
		var t7: float = _pitch_t_at_y(p2, melt)
		if t7 > 0.05 and t7 < 0.95:
			out.append(_look_pose("v7_melt_front",
				dress.pitch_axis(p2, maxf(0.03, t7 - 0.22)),
				dress.pitch_axis(p2, minf(0.97, t7 + 0.30)), 56.0))
	# 8 -- past the front. Dry, silent, and older than everything above it.
	if topo.levels >= 4:
		out.append(_drive_pose("v8_below_the_melt_front", 3, -1, 0.55, 1.20, 5, 56.0, 0.20))
	# 9 -- the workings, for the comparison. Same cave, three media.
	out.append(_drive_pose("v9_the_workings", mini(2, topo.levels - 1), -1, 0.45, 1.15, 6, 52.0, 0.10))
	return out

# ===========================================================================
# THE ICE SHOT SET
# ===========================================================================
# Fourteen frames of the glacial cave, posed against the topology. The set the
# vertical pass shot was a set about STRUCTURE -- here is a level, here is a
# level under it. This one is about MATERIAL and LIGHT, because that is what
# was wrong: the structure was right and the place still read as a mine.
#
# The rule for every frame here is the one CINEMA.md already states: photograph
# a thing, not a place. Each of these is aimed at one object.

# a station on `level`'s main drive matching a predicate, searched forward from
# `frac`, never in a chamber or at the mouth of a pitch
func _ice_find(level: int, pred: Callable, frac: float) -> int:
	if level >= topo.level_main_edge.size():
		return -1
	var ids: PackedInt32Array = topo.edges[topo.level_main_edge[level]]
	var n: int = ids.size()
	var start: int = clampi(int(float(n) * frac), 2, maxi(2, n - 6))
	for k in range(n - 6):
		var i: int = 2 + (start - 2 + k) % maxi(1, n - 8)
		var st: PackedInt32Array = topo.stations[ids[i]]
		if st[CaveTopology.S_KIND] != CaveTopology.K_DRIVE:
			continue
		if st[CaveTopology.S_PITCH_HEAD] >= 0 or st[CaveTopology.S_PITCH_FOOT] >= 0:
			continue
		# NEVER FRAME A CRAWL. A 0.75 m half-width conduit with a 1.3 m crown
		# puts the lens inside the wall at any eye height a machine has, which
		# is what produced the first i10 -- a full-screen slab of nothing. The
		# crawls are the best thing about the ice band and they are shot from
		# OUTSIDE, looking in.
		if st[CaveTopology.S_WIDTH] < CaveTopology.WC_NARROW:
			continue
		# and never stand where the section flares: a chamber four stations
		# away still owns the dome the camera is inside
		# +-8 STATIONS, not +-3. Three is 1.8 m, and there is now a 6.6 m machine
		# standing in one of these chambers: `i02_beam_in_ice` was rendered one
		# metre from the Assayer's ladder, which is a rusted iron rack in a
		# frame whose entire job is to have no iron in it.
		var bad: bool = false
		for k2 in range(-8, 9):
			var jj: int = clampi(i + k2, 0, n - 1)
			if topo.stations[ids[jj]][CaveTopology.S_KIND] == CaveTopology.K_CHAMBER:
				bad = true
		if bad:
			continue
		if pred.call(st, ids[i]):
			return i
	return -1

# the local frame of the drive at index i on `level`: [pos, tangent, right,
# halfwidth, height]. Every wall-aimed frame in this set needs it.
func _drive_frame(level: int, i: int) -> Array:
	var ids: PackedInt32Array = topo.edges[topo.level_main_edge[level]]
	i = clampi(i, 0, ids.size() - 2)
	var p: Vector3 = dress._st_pos(ids[i])
	var q: Vector3 = dress._st_pos(ids[mini(ids.size() - 1, i + 1)])
	var tg: Vector3 = (q - p).normalized()
	if tg.length() < 0.5:
		tg = Vector3(1, 0, 0)
	var rt: Vector3 = tg.cross(Vector3.UP).normalized()
	var st: PackedInt32Array = topo.stations[ids[i]]
	return [p, tg, rt, dress._hw(st), dress._ht(st)]

# stand back along the drive and look at a point on the wall. This is the pose
# that shows a MATERIAL rather than a corridor, and it is the only way to get
# the lamp onto a surface at an angle when the lamp is bolted to the eye.
func _wall_pose(nm: String, level: int, i: int, side: float, up: float,
				back: float, fov: float) -> Array:
	var f: Array = _drive_frame(level, i)
	var p: Vector3 = f[0]
	var tg: Vector3 = f[1]
	var rt: Vector3 = f[2]
	var hw: float = f[3]
	var tgt: Vector3 = p + rt * (side * hw * 0.92) + Vector3.UP * up
	var eye: Vector3 = p - tg * back + Vector3.UP * 1.15 - rt * (side * hw * 0.25)
	return _look_pose(nm, eye, tgt, fov)

func _build_ice_shots() -> Array:
	var out: Array = []
	var ICE: int = CaveTopology.MED_ICE
	var IOR: int = CaveTopology.MED_ICE_OVER_ROCK
	var p0: int = _main_pitch(0)
	var ice_base: float = float(CaveTopology.BAND_ICE_BASE_MM) * 0.001

	# --- 1. the wide ice passage. One lamp, and the ice carries it. --------
	var i_wide: int = _ice_find(0, func(st, _sid): return st[CaveTopology.S_MEDIUM] == ICE 		and st[CaveTopology.S_WIDTH] >= CaveTopology.WC_PASSAGE, 0.22)
	if i_wide < 0:
		i_wide = _level_station(0, ICE, 0.30, CaveTopology.WC_NARROW)
	out.append(_drive_pose("i01_ice_passage", 0, ICE, 0.22, 1.15, 14, 58.0, 0.16))

	# --- 2. THE BEAM ENTERING THE ICE -------------------------------------
	# The frame the whole task turns on. Stand a metre and a half off a wall
	# and point the lamp INTO it: on rock that is a hard pool with a black
	# edge, on ice it is a white patch with a blue halo that is bigger than
	# the beam. ice.gdshader computes that halo against a 62-degree cone where
	# the lamp's own is 27, which is the whole trick.
	var ice_pred := func(st: PackedInt32Array, _sid: int) -> bool:
		return st[CaveTopology.S_MEDIUM] == ICE
	var i_beam: int = _ice_find(0, ice_pred, 0.38)
	if i_beam < 0:
		i_beam = i_wide
	out.append(_wall_pose("i02_beam_in_ice", 0, i_beam, 1.0, 0.80, 2.45, 52.0))

	# --- 3. the scallops, oblique and close -------------------------------
	var i_sc: int = _ice_find(0, ice_pred, 0.60)
	if i_sc < 0:
		i_sc = i_wide
	out.append(_wall_pose("i03_scallops", 0, i_sc, -1.0, 0.85, 3.40, 50.0))

	# --- 4/5/6. the moulin ------------------------------------------------
	if p0 >= 0:
		var pr0: PackedInt32Array = topo.pitch(p0)
		var b0: float = float(pr0[CaveTopology.P_BORE_MM]) * 0.001
		# from ABOVE: stand at the lip and look down it, off-axis so the far
		# wall of the bore is in frame and the hole has a shape
		var lip: Vector3 = dress.pitch_axis(p0, 0.0)
		out.append(_look_pose("i04_moulin_above",
			_on_drive(0, pr0[CaveTopology.P_FROM_ST], -6, 1.20),
			dress.pitch_axis(p0, 0.22), 62.0))
		# --- FROM BELOW, and it is the COLLAR rather than the moulin --------
		# The moulin lands on level 1 at -26 m, eleven metres BELOW the ice
		# base, so standing at its foot and looking up is eleven metres of
		# unlit rock before any ice: 98% true black, which is what the first
		# attempt measured. The collar is the shaft that DOES read from
		# underneath, because it is ice all the way and it has the only
		# daylight in the game at the top of it.
		var cf0: PackedInt32Array = topo.pitch(0)
		var axf: Vector3 = dress.pitch_axis(0, 0.92)
		out.append(_look_pose("i05_moulin_below",
			Vector3(axf.x + 0.25, dress._st_pos(cf0[CaveTopology.P_TO_ST]).y + 0.65, axf.z + 0.15),
			dress.pitch_axis(0, 0.0), 76.0))
		# INSIDE the bore: look DOWN it rather than at it, from off the axis,
		# so the bore recedes and the frozen fall runs out of frame
		var t6: float = 0.14
		var h6: float = float(pr0[CaveTopology.P_DROP_MM]) * 0.001
		var a6: float = 0.9 + PI + t6 * h6 * 0.26
		out.append(_look_pose("i06_moulin_icefall",
			dress.pitch_axis(p0, t6) - Vector3(cos(a6), 0.0, sin(a6)) * (b0 * 0.30),
			dress.pitch_axis(p0, t6 + 0.34) + Vector3(cos(a6), 0.0, sin(a6)) * (b0 * 0.30), 66.0))
		# --- 11. THE ICE-TO-ROCK TRANSITION, inside the same shaft --------
		var t11: float = _pitch_t_at_y(p0, ice_base)
		if t11 > 0.05 and t11 < 0.95:
			out.append(_look_pose("i11_ice_to_rock",
				dress.pitch_axis(p0, maxf(0.02, t11 - 0.26)),
				dress.pitch_axis(p0, minf(0.98, t11 + 0.30)), 56.0))

	# --- 7. the frozen pool -----------------------------------------------
	var pool_pred := func(st: PackedInt32Array, _sid: int) -> bool:
		if st[CaveTopology.S_MEDIUM] != ICE:
			return false
		return st[CaveTopology.S_STATE] == CaveTopology.FLOODED 			or (st[CaveTopology.S_WORKS] & CaveTopology.WK_STANDWATER) != 0
	var i_pool: int = _ice_find(0, pool_pred, 0.30)
	if i_pool < 0:
		i_pool = _ice_find(0, func(st, _sid): return st[CaveTopology.S_MEDIUM] == ICE 			and st[CaveTopology.S_WET] > 180, 0.30)
	if i_pool >= 0:
		var fp: Array = _drive_frame(0, i_pool)
		out.append(_look_pose("i07_frozen_pool",
			(fp[0] as Vector3) - (fp[1] as Vector3) * 3.4 + Vector3.UP * 1.20,
			(fp[0] as Vector3) + Vector3.UP * 0.12, 50.0))

	# --- 8. icicles and columns -------------------------------------------
	var i_ice2: int = _ice_find(0, func(st, _sid): return st[CaveTopology.S_MEDIUM] == ICE 		and st[CaveTopology.S_WET] > 150, 0.55)
	if i_ice2 < 0:
		i_ice2 = i_wide + 10
	if i_ice2 < 0:
		i_ice2 = i_wide
	var f8: Array = _drive_frame(0, i_ice2)
	# 2.6 m back and aimed at the crown put the lens in the wall: at that
	# standoff the sight line to a 3 m crown leaves the section before it gets
	# there. Stand five metres off and let the fringe recede.
	out.append(_look_pose("i08_icicles_columns",
		(f8[0] as Vector3) - (f8[1] as Vector3) * 5.0 + Vector3.UP * 1.10,
		(f8[0] as Vector3) + Vector3.UP * ((f8[4] as float) * 0.52), 50.0))

	# --- 9. the frozen waterfall on a wall --------------------------------
	out.append(_wall_pose("i09_icefall", 0, i_ice2, 1.0, 0.90, 3.6, 52.0))

	# --- 10. the meltwater cutting the floor ------------------------------
	var i_ch: int = _ice_find(0, func(st, _sid): return st[CaveTopology.S_MEDIUM] == ICE 		and st[CaveTopology.S_WET] > 120 and st[CaveTopology.S_STATE] != CaveTopology.FLOODED, 0.10)
	if i_ch >= 0:
		var f10: Array = _drive_frame(0, i_ch)
		# The lamp pool on an ice floor is twice as bright as it is on a rock
		# one, so a near-level camera two metres off the ground puts a blown
		# ellipse across a quarter of the frame. Stand further back, higher,
		# and narrower, so the channel recedes instead of the pool filling it.
		out.append(_look_pose("i10_meltwater_channel",
			(f10[0] as Vector3) - (f10[1] as Vector3) * 4.2 + Vector3.UP * 1.45,
			(f10[0] as Vector3) + (f10[1] as Vector3) * 5.0 + Vector3.UP * 0.35, 44.0))

	# --- 12. THE FIRST IRON -----------------------------------------------
	# One cast survey plate on a natural wall, and nothing else the ancients
	# left anywhere in frame. This is the frame the works reduction was for.
	var i_iron: int = _ice_find(1, func(st, _sid): return (st[CaveTopology.S_WORKS] & CaveTopology.WK_PLATE) != 0, 0.05)
	if i_iron >= 0:
		# AIMED AT THE OBJECT. A cast index plate is 160 x 100 mm; at 2.6 m and
		# 44 degrees it is two per cent of the frame width and the frame is
		# about a wall. dressing.gd puts it at right * hw * 0.96, 1.40 m up, so
		# the camera is told exactly that and stands 1.7 m off it.
		var fI: Array = _drive_frame(1, i_iron)
		var pI: Vector3 = fI[0]
		var tI: Vector3 = fI[1]
		var rI: Vector3 = fI[2]
		var plate: Vector3 = pI + rI * (float(fI[3]) * 0.80) + Vector3.UP * 1.40
		out.append(_look_pose("i12_first_iron",
			pI - tI * 2.30 + Vector3.UP * 1.30 - rI * (float(fI[3]) * 0.55), plate, 30.0))

	# --- 13. UNCOVERING ---------------------------------------------------
	for lv in [0, 1]:
		var rev_pred := func(st: PackedInt32Array, sid: int) -> bool:
			var m: int = st[CaveTopology.S_MEDIUM]
			return (m == ICE or m == IOR) and dress._reveal_at(sid)
		var i_rev: int = _ice_find(lv, rev_pred, 0.0)
		if i_rev >= 0:
			var ids2: PackedInt32Array = topo.edges[topo.level_main_edge[lv]]
			var sd: int = ids2[i_rev]
			var f13: Array = _drive_frame(lv, i_rev)
			var side: float = 1.0 if (sd % 2 == 0) else -1.0
			var org: Vector3 = f13[0]
			var tgv: Vector3 = f13[1]
			var rtv: Vector3 = f13[2]
			var hwv: float = f13[3]
			var tgt: Vector3 = org + rtv * (side * hwv * 0.97) + Vector3.UP * (0.35 + float(sd % 5) * 0.16)
			var eye: Vector3 = org - tgv * 1.55 + Vector3.UP * 0.95 - rtv * (side * hwv * 0.35)
			out.append(_look_pose("i13_uncovered_L%d" % lv, eye, tgt, 34.0))
			break

	# --- 14. the collar, and the only daylight in the game -----------------
	if topo.pitches.size() > 0:
		var c0: PackedInt32Array = topo.pitch(0)
		var cf: Vector3 = dress._st_pos(c0[CaveTopology.P_TO_ST])
		var cax: Vector3 = dress.pitch_axis(0, 0.0)
		var away: Vector3 = (cf - cax)
		away.y = 0.0
		if away.length() < 0.5:
			away = Vector3(1, 0, 0)
		away = away.normalized()
		out.append(_look_pose("i14_collar_daylight",
			cf + away * 3.6 + Vector3.UP * 1.25, cax + Vector3.UP * 1.6, 62.0))
	return out

# ===========================================================================
# THE ASSAYER, FOUND
# ===========================================================================
# The designer, 2026-09-10: "it should end with the dog finding something
# massive and bright and scary in there."
#
# THIS IS A SEQUENCE, NOT A SHOT, and the order is the whole effect:
#
#   1  something at the edge of the lamp        it is not ice and not rock
#   2  closer                                    it is made
#   3  the footing, frozen in                    it has been here longer than
#                                                the ice
#   4  the scale                                 look up. It does not end
#   5  it moves                                  and it was never a ruin
#   6  the wind, click one                       it is counting
#   7  click nine                                and it is nearly done counting
#   8  THE STRIKE                                4000 K, the only white light
#                                                in the game
#   9  the room, at the strike                   what it has been standing in
#  10  the decay                                 and it goes back to waiting
#
# THREE FINDINGS FROM spikes/godot/assayer/ ARE OBEYED HERE RATHER THAN
# REDISCOVERED, and each of them decides a camera:
#
#   * A DORMANT ASSAYER EMITS NOTHING. It can only be found by the visitor's
#     own lamp, and at nine metres the mast is below the legibility floor. So
#     the approach starts at seven and the first two frames are lit entirely by
#     the machine that is looking at it.
#   * THE SLEW IS ONLY VISIBLE IF THE CAMERA LOOKS AT THE BEARING RACE. The
#     lamp is a child of the camera and the race at 5.4 m sits outside its
#     cone, so frame 5 is aimed at the race and not at the boom.
#   * THE WIND CANNOT FIT IN FOUR SECONDS. Nine clicks are nine seconds, so the
#     ratchet has to have STARTED before the shot -- frame 6 is click one at
#     p = 62.4 and the sequence below enters mid-wind rather than at p = 62.

func _asy_drive_index() -> int:
	var ci: int = dress.assayer_chamber()
	if ci < 0 or topo.level_main_edge.size() == 0:
		return -1
	var sid: int = topo.chambers[ci * CaveTopology.CH_ROW + CaveTopology.CH_SID]
	var ids: PackedInt32Array = topo.edges[topo.level_main_edge[0]]
	for i in range(ids.size()):
		if ids[i] == sid:
			return i
	return -1

# a camera standing `back` metres along the drive from the machine, at `eye`,
# looking at a point `up` metres above its footing. The camera stands ON THE
# CENTRELINE -- VERTICAL.md 5: a chamber dome is a hemisphere with a 2.9 m tube
# through it and anywhere off the centreline is inside the tube's wall.
func _asy_pose(nm: String, back: float, eye: float, up: float, fov: float,
			   phase: float, lat: float = 0.0) -> Array:
	# STAND ON THE DRIVE, STATION BY STATION, not on a straight line from the
	# chamber centre. The first version walked back along ONE tangent, which is
	# the tangent at the chamber and not the tangent anywhere else: the drive
	# wanders by a cell every four stations, so at seven metres out the camera
	# was a metre and a half off the centreline and inside the tube's wall.
	# Every one of the first ten assayer frames was a photograph of the inside
	# of a wall. Cells are 0.6 m, so `back` metres is back/0.6 stations.
	# LATERAL IS ZERO EVERYWHERE IN THIS SET, and that is the second thing the
	# first sequence taught. VERTICAL.md 5 already records it: "the chamber
	# dome is a 5-7 m hemisphere with a 2.9 m tube running through it, so
	# anywhere off the centreline by more than the tube's half width is INSIDE
	# the tube's wall." A camera 0.9 m off the line in a room that is really a
	# tube photographs the OUTSIDE of the tube, which is the pale featureless
	# mass that filled two thirds of every early frame. The room a viewer sees
	# here is therefore the DRIVE -- 5.9 m wide and 6.75 m tall at a chamber
	# station -- and a 6.6 m machine standing in a 6.75 m drive is a better
	# scale reveal than a dome would have been, because it nearly touches.
	var i: int = _asy_drive_index()
	var ap: Vector3 = dress.assayer_pos()
	var from: Vector3 = ap + Vector3.UP * eye
	if i >= 0:
		var ids: PackedInt32Array = topo.edges[topo.level_main_edge[0]]
		var j: int = clampi(i - int(round(back / 0.6)), 0, ids.size() - 1)
		from = dress._st_pos(ids[j]) + Vector3.UP * eye
		if absf(lat) > 0.001:
			var f2: Array = _drive_frame(0, j)
			from += (f2[2] as Vector3) * lat
	var pose: Array = _look_pose(nm, from, ap + Vector3.UP * up, fov)
	pose.append(phase)
	return pose

func _build_assayer_shots() -> Array:
	if machine == null:
		return _build_ice_shots()
	var out: Array = []
	# 1 -- AT THE EDGE OF THE LAMP. Seven metres, dormant. The lamp reaches
	# about six on a floor, so what comes back is the footing and one edge of
	# the anvil block: an object, in a place that has had no objects in it.
	out.append(_asy_pose("a1_edge_of_the_lamp", 6.1, 1.15, 1.3, 52.0, 22.0))
	# 2 -- closer. Five metres is where the mast crosses the legibility floor.
	out.append(_asy_pose("a2_closer", 4.9, 1.15, 1.9, 54.0, 30.0, 0.0))
	# 3 -- THE FOOTING, FROZEN IN. Low and close: the ice has come up the
	# anchor pads, and the meltwater running off it is the reason it is running.
	out.append(_asy_pose("a3_footing_frozen", 2.9, 0.62, 0.75, 46.0, 38.0, 0.0))
	# 4 -- THE SCALE. Stand at its foot and look up the mast. This is the
	# moment: the chamber crown is 8.4 m and the mast is 6.6, so the top of it
	# is nearly in the roof.
	out.append(_asy_pose("a4_the_scale", 3.0, 0.55, 5.30, 82.0, 46.0, 0.0))
	# 5 -- IT MOVES. Aimed at the bearing race at 5.4 m, mid-slew, because the
	# race is the only part of a 36-degree turn a camera can see.
	out.append(_asy_pose("a5_the_slew", 4.6, 1.35, 5.40, 44.0, 55.6, 0.0))
	# 6 -- the wind, click one. It has started counting.
	out.append(_asy_pose("a6_click_one", 3.2, 1.05, 2.55, 66.0, 62.4, 0.0))
	# 7 -- click nine. Same camera, so the count is the only thing that changed.
	out.append(_asy_pose("a7_click_nine", 3.2, 1.05, 2.55, 66.0, 70.6, 0.0))
	# 8 -- THE STRIKE. 4000 K, and it is the only white light in the game.
	out.append(_asy_pose("a8_the_strike", 3.2, 1.05, 2.55, 66.0, 71.05, 0.0))
	# 9 -- THE ROOM, at the strike. What it has been standing in all along, seen
	# for one frame because the machine lit it.
	out.append(_asy_pose("a9_the_room", 4.6, 1.30, 2.20, 74.0, 71.05, 0.0))
	# 10 -- the decay, and it goes back to waiting.
	out.append(_asy_pose("a10_the_decay", 4.6, 1.30, 2.20, 74.0, 74.2, 0.0))
	return out

# --- the moving sequence ---------------------------------------------------
# Thirty-two frames at 1280x720: a dolly from 8.6 m to 3.1 m while the clock
# runs from p 58 to p 72.5, so the approach, the slew, all nine clicks and the
# strike happen while the camera is closing. That is the shape of the beat --
# the machine does not wait for the visitor to arrive.
func _assayer_sequence() -> void:
	# the stills already go into shots/ice/assayer/, so the sequence goes in
	# beside them rather than into a second directory of the same name
	var dir: String = shot_dir
	if not dir.ends_with("assayer/"):
		dir = shot_dir + "assayer/"

	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(dir))
	var N: int = 32
	sub.size = Vector2i(1280, 720)
	await RenderingServer.frame_post_draw
	for i in range(N):
		var u: float = float(i) / float(N - 1)
		# ease the dolly so it slows as it arrives
		var e: float = 1.0 - pow(1.0 - u, 2.2)
		var back: float = lerp(6.1, 3.0, e)
		var eye: float = lerp(1.20, 0.95, e)
		var up: float = lerp(1.3, 2.6, e * e)
		var fov: float = lerp(52.0, 70.0, e)
		var ph: float = lerp(58.0, 72.5, u)
		var pose: Array = _asy_pose("seq", back, eye, up, fov, ph, 0.0)
		cam.fov = pose[4]
		cam.global_transform = Transform3D(Basis.from_euler(Vector3(pose[3], pose[2], 0)), pose[1])
		cam.force_update_transform()
		_ice_lamp()
		machine.set_phase(ph)
		for k in range(3):
			await RenderingServer.frame_post_draw
		var img: Image = sub.get_texture().get_image()
		img.save_png(ProjectSettings.globalize_path(dir + "seq_%03d.png" % i))
	sub.size = Vector2i(1920, 1080)
	print("assayer sequence : %d frames at 1280x720 in %s" % [N, dir])

# ===========================================================================
# THE SECTION. ART-DIRECTION 3.6: "the wide shot in Blindside is a schematic."
# A vertical cave has no wide shot that is a photograph -- there is no place to
# stand that sees two levels at once -- so the frame that makes the structure
# legible is drawn from the plan rather than lit. Everything below comes out of
# `topology.gd` and nothing out of `dressing.gd`.
# ===========================================================================
const SEC_MED_COL: Array = [
	Color(0.40, 0.31, 0.22),   # rock
	Color(0.80, 0.57, 0.30),   # worked
	Color(0.82, 0.85, 0.87),   # ice
	Color(0.58, 0.57, 0.53),   # ice over rock
]
const SEC_CLIMB_COL: Array = [
	Color(0.90, 0.90, 0.84),   # walk
	Color(0.96, 0.76, 0.34),   # scramble  -- you can get back up
	Color(0.95, 0.44, 0.16),   # pitch     -- down only
	Color(0.74, 0.17, 0.13),   # vertical  -- neither
]

func _sec_quad(v: PackedVector3Array, c: PackedColorArray, idx: PackedInt32Array,
			   a: Vector3, b: Vector3, w: float, col: Color) -> void:
	var d: Vector3 = b - a
	if d.length() < 0.0001:
		return
	d = d.normalized()
	var nrm := Vector3(-d.y, d.x, 0.0) * (w * 0.5)
	var base: int = v.size()
	v.push_back(a - nrm)
	v.push_back(a + nrm)
	v.push_back(b - nrm)
	v.push_back(b + nrm)
	for i in range(4):
		c.push_back(col)
	idx.push_back(base); idx.push_back(base + 1); idx.push_back(base + 2)
	idx.push_back(base + 2); idx.push_back(base + 1); idx.push_back(base + 3)

func _shot_section() -> void:
	var v := PackedVector3Array()
	var c := PackedColorArray()
	var idx := PackedInt32Array()
	var minx: float = 1e9
	var maxx: float = -1e9
	var miny: float = 1e9
	var maxy: float = -1e9
	# the drives, drawn at their real section height
	for e in range(topo.edges.size()):
		var ids: PackedInt32Array = topo.edges[e]
		var main: bool = false
		for L in range(topo.level_main_edge.size()):
			if topo.level_main_edge[L] == e:
				main = true
		for i in range(ids.size() - 1):
			var a: PackedInt32Array = topo.stations[ids[i]]
			var b: PackedInt32Array = topo.stations[ids[i + 1]]
			var ax: float = float(a[CaveTopology.S_X]) * 0.6
			var bx: float = float(b[CaveTopology.S_X]) * 0.6
			var ay: float = float(a[CaveTopology.S_FLOOR_MM]) * 0.001
			var by: float = float(b[CaveTopology.S_FLOOR_MM]) * 0.001
			var ah: float = float(a[CaveTopology.S_CEIL_MM] - a[CaveTopology.S_FLOOR_MM]) * 0.001
			var bh: float = float(b[CaveTopology.S_CEIL_MM] - b[CaveTopology.S_FLOOR_MM]) * 0.001
			var col: Color = SEC_MED_COL[a[CaveTopology.S_MEDIUM]]
			if not main:
				col = col.darkened(0.45)
			_sec_quad(v, c, idx, Vector3(ax, ay + ah * 0.5, 0), Vector3(bx, by + bh * 0.5, 0),
				maxf(0.55, (ah + bh) * 0.5), col)
			minx = minf(minx, ax); maxx = maxf(maxx, ax)
			miny = minf(miny, ay); maxy = maxf(maxy, ay + ah)
	# the pitches, coloured by whether a machine can come back up them
	for pi in range(topo.pitches.size()):
		var pr: PackedInt32Array = topo.pitch(pi)
		var px: float = float(pr[CaveTopology.P_X]) * 0.6
		var qx: float = float(pr[CaveTopology.P_TO_X]) * 0.6
		var ty: float = float(pr[CaveTopology.P_TOP_MM]) * 0.001
		var by2: float = float(pr[CaveTopology.P_BOT_MM]) * 0.001
		var bore: float = float(pr[CaveTopology.P_BORE_MM]) * 0.001
		_sec_quad(v, c, idx, Vector3(px, ty, 0), Vector3(qx, by2, 0),
			maxf(0.5, bore), SEC_CLIMB_COL[pr[CaveTopology.P_CLIMB]])
		miny = minf(miny, by2); maxy = maxf(maxy, ty)
		minx = minf(minx, minf(px, qx)); maxx = maxf(maxx, maxf(px, qx))
	# the datum, the three band boundaries, the water surfaces and the front
	var x0: float = minx - 6.0
	var x1: float = maxx + 6.0
	_sec_quad(v, c, idx, Vector3(x0, 0.0, -0.4), Vector3(x1, 0.0, -0.4), 0.45,
		Color(0.52, 0.52, 0.52))
	for bmm in [CaveTopology.BAND_ICE_BASE_MM, CaveTopology.BAND_KARST_BASE_MM,
				CaveTopology.BAND_WORK_BASE_MM]:
		var by3: float = float(bmm) * 0.001
		var xx: float = x0
		while xx < x1:
			_sec_quad(v, c, idx, Vector3(xx, by3, -0.4), Vector3(xx + 1.6, by3, -0.4), 0.22,
				Color(0.34, 0.31, 0.27))
			xx += 3.2
	for L in range(topo.levels):
		if topo.level_water_mm[L] > -1000000:
			var wy: float = float(topo.level_water_mm[L]) * 0.001
			_sec_quad(v, c, idx, Vector3(x0, wy, -0.2), Vector3(x1, wy, -0.2), 0.30,
				Color(0.30, 0.44, 0.52))
	var my: float = float(topo.melt_mm) * 0.001
	var mx: float = x0
	while mx < x1:
		_sec_quad(v, c, idx, Vector3(mx, my, -0.1), Vector3(mx + 2.6, my, -0.1), 0.40,
			Color(0.62, 0.58, 0.46))
		mx += 4.4
	var am := ArrayMesh.new()
	var arr := []
	arr.resize(Mesh.ARRAY_MAX)
	arr[Mesh.ARRAY_VERTEX] = v
	arr[Mesh.ARRAY_COLOR] = c
	arr[Mesh.ARRAY_INDEX] = idx
	am.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arr)
	var smat := StandardMaterial3D.new()
	smat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	smat.vertex_color_use_as_albedo = true
	smat.cull_mode = BaseMaterial3D.CULL_DISABLED
	am.surface_set_material(0, smat)
	var mi := MeshInstance3D.new()
	mi.mesh = am
	world_root.add_child(mi)
	# frame it
	var cx: float = (minx + maxx) * 0.5
	var cy: float = (miny + maxy) * 0.5
	var hgt: float = (maxy - miny) * 1.12
	var wid: float = (maxx - minx) * 1.04
	var sc := Camera3D.new()
	sc.projection = Camera3D.PROJECTION_ORTHOGONAL
	sc.size = maxf(hgt, wid / 1.7778) * 1.30
	sc.near = 0.05
	sc.far = 400.0
	sc.position = Vector3(cx - sc.size * 1.7778 * 0.145, cy, 120.0)
	sub.add_child(sc)
	sc.current = true
	var fog_was: bool = envr.volumetric_fog_enabled
	envr.volumetric_fog_enabled = false
	var glow_was: bool = envr.glow_enabled
	envr.glow_enabled = false
	geo_root.visible = false
	# the legend sits in the black below the workings, on a panel, because the
	# drives run the full width of the frame and text over them is unreadable
	var panel := ColorRect.new()
	panel.color = Color(0, 0, 0, 0.62)
	panel.position = Vector2(10, 10)
	panel.size = Vector2(452, 1058)
	sub.add_child(panel)
	var legend := Label.new()
	legend.position = Vector2(22, 22)
	legend.add_theme_font_size_override("font_size", 15)
	legend.add_theme_color_override("font_color", Color(0.86, 0.85, 0.82))
	legend.add_theme_color_override("font_outline_color", Color(0, 0, 0))
	legend.add_theme_constant_override("outline_size", 6)
	var txt: String = "SECTION\nseed %d   %d levels\n%.1f m of vertical range\n\n" % [
		cfg["seed"], topo.levels, float(topo.vertical_range_mm()) * 0.001]
	txt += "datum 0 m = the valley floor\n"
	txt += "bands\n  ice      0 .. %.0f\n  karst      .. %.0f\n  workings   .. %.0f\n  deep     below\n" % [
		float(CaveTopology.BAND_ICE_BASE_MM) * 0.001,
		float(CaveTopology.BAND_KARST_BASE_MM) * 0.001,
		float(CaveTopology.BAND_WORK_BASE_MM) * 0.001]
	txt += "\nmelt front %.0f m\n  above it the water has arrived,\n  below it nothing has run\n" % my
	txt += "\nmedium  rock / worked / ice / ice-over-rock\n"
	txt += "pitch   walk / scramble (up ok)\n        PITCH (down only) / VERTICAL (neither)\n"
	for pi in range(topo.pitches.size()):
		var pr2: PackedInt32Array = topo.pitch(pi)
		txt += "  %-8s %5.1f m  %.2f  %-8s  dn %s up %s\n" % [
			CaveTopology.PK_NAME[pr2[CaveTopology.P_KIND]],
			float(pr2[CaveTopology.P_DROP_MM]) * 0.001,
			float(pr2[CaveTopology.P_BORE_MM]) * 0.001,
			CaveTopology.CL_NAME[pr2[CaveTopology.P_CLIMB]],
			"Y" if (pr2[CaveTopology.P_FLAGS] & CaveTopology.PF_DOWN) != 0 else "n",
			"Y" if (pr2[CaveTopology.P_FLAGS] & CaveTopology.PF_UP) != 0 else "n"]
	txt += "\nreachable      %d of %d open cells\nable to return %d  (%.0f%%)" % [
		topo.reach_down, topo.open_cells(), topo.reach_up,
		100.0 * float(topo.reach_up) / float(maxi(1, topo.open_cells()))]
	legend.text = txt
	sub.add_child(legend)
	for k in range(SETTLE):
		await RenderingServer.frame_post_draw
	var img: Image = sub.get_texture().get_image()
	img.save_png(ProjectSettings.globalize_path(shot_dir + "v10_section.png"))
	print("shot %-22s  %dx%d  ortho size %.1f m" % ["v10_section", img.get_width(),
		img.get_height(), sc.size])
	legend.queue_free()
	panel.queue_free()
	sc.current = false
	sc.queue_free()
	cam.current = true
	geo_root.visible = true
	envr.volumetric_fog_enabled = fog_was
	envr.glow_enabled = glow_was
	mi.queue_free()

# ---------------------------------------------------------------------------
# ===========================================================================
# THE LAMP, HANDED TO THE ICE
# ===========================================================================
# ice.gdshader computes its internal scattering against the REAL lamp -- a
# position, an axis and a cone -- rather than against a point source at the
# camera, which is what the first pass did and why the glow had no shape. It
# is four uniforms and it has to be written wherever the camera moves,
# INCLUDING inside the screenshot loop, because that loop sets `busy` and
# _process returns early.
var sky_light: OmniLight3D = null
var machine: Assayer = null
var asy_mats: AssayerMaterials = null
var cycle_t: float = 0.0

func _ice_lamp() -> void:
	if dress == null or lamp == null:
		return
	var lt: Transform3D = lamp.global_transform
	dress.set_ice_param("lamp_pos", lt.origin)
	dress.set_ice_param("lamp_dir", -lt.basis.z)
	dress.set_ice_param("lamp_energy", lamp.light_energy if lamp.visible else 0.0)
	dress.set_ice_param("lamp_range", lamp.spot_range)
	dress.set_ice_param("lamp_cos", cos(deg_to_rad(lamp.spot_angle)))
	# the wide cone is the effect: the light bleeds past the edge of its own
	# beam because inside ice it does. 27 deg of lamp, 62 deg of glow.
	dress.set_ice_param("lamp_cos_wide", cos(deg_to_rad(minf(78.0, lamp.spot_angle * 2.3))))
	if sky_light != null:
		dress.set_ice_param("sky_pos", sky_light.global_position)
		dress.set_ice_param("sky_energy", sky_light.light_energy)
		dress.set_ice_param("sky_col", Vector3(sky_light.light_color.r,
			sky_light.light_color.g, sky_light.light_color.b))

func _process(delta: float) -> void:
	_ice_lamp()
	if busy:
		return
	t += delta
	# ONE CLOCK, the assayer spike's rule kept: everything the machine does is
	# a pure function of cycle_t and nothing else in the scene moves with it.
	if machine != null:
		if float(cfg["phase"]) >= 0.0:
			machine.set_phase(float(cfg["phase"]))
		else:
			cycle_t += delta
			if cycle_t >= Assayer.PERIOD:
				cycle_t -= Assayer.PERIOD
				machine.advance_cycle()
			machine.set_phase(cycle_t)
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
				if String(cfg["cinema"]) != "":
					phase = 3
					_cinema_run()
					return
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
		sf.store_line("topology_schema=v%d levels=%d" % [topo.schema_version(), topo.levels])
		sf.store_line("vertical_range_m=%.1f reach_down=%d reach_up=%d pitches=%d" % [
			float(topo.vertical_range_mm()) * 0.001, topo.reach_down, topo.reach_up,
			topo.pitches.size()])
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
		cam.force_update_transform()
		_ice_lamp()
		if machine != null and shot.size() >= 7 and typeof(shot[6]) == TYPE_FLOAT:
			machine.set_phase(float(shot[6]))
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
	if String(cfg["shotset"]) == "assayer" and machine != null:
		await _assayer_sequence()
	if String(cfg["shotset"]) == "vertical" and topo.levels > 1:
		await _shot_section()
	busy = false
	phase = 3
	if not cfg["stay"]:
		await get_tree().create_timer(0.3).timeout
		get_tree().quit()

# ===========================================================================
# THE CINEMATIC LAYER -- TRAILER.md 8 (the camera) and 9 (the lens and grade)
# ===========================================================================
const CIN_DIR := "res://shots/cinema/"
const SETTLE: int = 8              # frames to let the fog and shadow atlas land
var fx_mask: int = 0
var cin_report: PackedStringArray = PackedStringArray()

func _cin(msg: String) -> void:
	print(msg)
	cin_report.append(msg)

func _cin_flush(fname: String) -> void:
	var f := FileAccess.open(CIN_DIR + fname, FileAccess.WRITE)
	if f:
		for l in cin_report:
			f.store_line(l)
		f.close()
	cin_report.clear()

func _cinema_setup() -> void:
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(CIN_DIR))
	for d in ["pairs", "seq", "stack", "fail", "diag"]:
		DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(CIN_DIR + d))
	cam.keep_aspect = Camera3D.KEEP_HEIGHT
	rig = CameraRig.new()
	rig.build_collision(geo_root, topo, dress, world_root)
	rig.ready_space(world_root)
	fleet = CaveFleet.new()
	fleet.build(world_root, rig)
	rig.fleet = fleet
	grade = CinemaGrade.new()
	grade.setup(envr, cam)
	fx_mask = CinemaGrade.parse(String(cfg["fx"]))
	print("cinema           : mode=%s fx=%s" % [cfg["cinema"], CinemaGrade.mask_str(fx_mask)])
	print("collision        : %d shell triangles + %d prop boxes in %.0f ms" % [
		rig.collision_tris, rig.collision_props, rig.build_ms])

# --- the shot list, as data ------------------------------------------------
func _cin_stations() -> Dictionary:
	var ids: PackedInt32Array = topo.edges[0]
	return {
		"rail": _straight(0.30, 12, CaveTopology.WC_PASSAGE),
		# Three passes to get this one, and the sequence is the lesson.
		#   116  the first guess. Passes every rule in TRAILER 8 and is a bad
		#        shot: the drive bends inside 3 m at 0.42 m and the dolly ends
		#        with a blown near face filling the frame.
		#   196  chosen for the longest machine-height SIGHTLINE, 8.9 m. Worse:
		#        0.00% of the frame legible, 97% true black. A long sightline
		#        down an unlit drive is a long look at nothing.
		#   68   chosen by photographing the candidates (--cinema=locations,
		#        shots/cinema/loc/). Rails running away, an arched drive, a
		#        beacon pilot at the far end. 4.96% legible, 87.9% black -- in
		#        contract, and it is a picture.
		# Neither the rule set nor the sightline could have picked 68. Looking
		# could. That is worth saying out loud: the rig makes a shot LEGAL and
		# it cannot make one GOOD.
		"dense": 68,
		# Scouted for sightline, then CHOSEN BY LOOKING. Station 60 has the
		# longest sightline that accepts an eye-height drift -- 23.8 m -- and
		# makes a bad frame, because the sightline says the camera can see a
		# long way and says nothing about what is in the first two metres (60
		# has a launder and a spoil heap there). --cinema=locations photographs
		# the candidates; 70 is the one that reads as a passage going away with
		# a pilot at the end of it, which is what "wide, small in frame" needs.
		# shots/cinema/loc/ is the comparison.
		"long": 70,
		"spoil": _find(func(s): return (s[CaveTopology.S_WORKS] & CaveTopology.WK_SPOIL) != 0, 0.35),
		"junc": topo.junctions[mini(2, topo.junctions.size() - 1)] if topo.junctions.size() > 0 else int(ids.size() * 0.3),
	}

# The trailer's cave shots, written out as JSON so the list is data and the
# rig executes it rather than anyone hand-flying it.
func _cin_write_shots() -> void:
	var st: Dictionary = _cin_stations()
	var rail: int = int(st["rail"])
	var dense: int = int(st["dense"])
	var lng: int = int(st["long"])
	var spoil: int = int(st["spoil"])
	var list: Array = [
		# 16 -- 1:04, 5s. "The lamp comes on. A passage resolves out of nothing:
		# wet rock, sets, a rail underfoot." A patient push in on a wide lens,
		# eye height, focus pulled off the rail underfoot and out down the drive.
		{"name": "t16_lamp_comes_on", "trailer": "16", "len_s": 5.0,
		 "lens_mm": 21.0, "tstop": 2.8, "ease": "inout", "handheld_deg": 0.0,
		 "height": "eye", "seed": 16,
		 "move": {"from": {"st": rail, "r": 0.0, "u": 1.60, "f": 0.0},
				  "to":   {"st": rail, "r": 0.0, "u": 1.60, "f": 1.30}},
		 "look": {"from": {"st": rail, "r": 0.0, "u": 0.70, "f": 6.0},
				  "to":   {"st": rail, "r": 0.0, "u": 0.95, "f": 9.0}},
		 "focus": {"from": {"st": rail, "r": 0.0, "u": 0.05, "f": 2.2},
				   "to":   {"st": rail, "r": 0.0, "u": 0.60, "f": 7.0}}, 
		 # NOTE-16. The machine is NOT in this frame, and it is worth saying so
		 # rather than leaving it to be inferred. The lamp that comes on is its
		 # lamp; the shot is what the lamp finds. Put the machine in frame and
		 # this becomes shot 17, which is the next shot. Hero.BEATS agrees: 16
		 # is not on it.
		 "machine": {"role": "none"}},

		# 17 -- 1:09, 4s. "Following the machine from behind, its own pool of
		# light moving over the floor." Machine height, a normal lens, a follow
		# dolly. IT NOW HAS A MACHINE IN IT. Until 2026-09-09 this line read
		# "There is no machine in this spike: this executes as the plate", and
		# that sentence is half of TRAILER 11.1's fault: the trailer's subject
		# was absent from the whole second half of the trailer. The hero walks
		# 2.0 m down the drive in the 4.0 s the shot lasts, which is exactly
		# the 0.50 m/s the walk clip was baked at, and the camera follows it at
		# a constant 3.2 m -- so it neither skates nor is overtaken.
		{"name": "t17_follow_machine", "trailer": "17", "len_s": 4.0,
		 "lens_mm": 35.0, "tstop": 2.8, "ease": "inout", "handheld_deg": 0.22,
		 "height": "machine", "seed": 17,
		 "machine": {"role": "hero", "chassis": "surveyor", "loadout": "default",
			 "skin": "player", "wear": 0.35, "damage": 0.0, "lamp": true,
			 "clip": "walk", "yaw": "path",
			 "at": {"from": {"st": dense, "r": 0.0, "u": 0.0, "f": 3.20},
					"to":   {"st": dense, "r": 0.0, "u": 0.0, "f": 5.20}},
			 "head": [[-6.0, -3.0], [7.0, -5.0]]},
		 "move": {"from": {"st": dense, "r": 0.10, "u": 0.42, "f": 0.0},
				  "to":   {"st": dense, "r": 0.02, "u": 0.42, "f": 1.60}},
		 "look": {"from": {"st": dense, "r": 0.0, "u": 0.62, "f": 3.2},
				  "to":   {"st": dense, "r": 0.0, "u": 0.70, "f": 4.6}},
		 "focus": {"from": 2.4, "to": 3.2}},

		# 18 -- 1:13, 4s. THE FIRST BELIEF CUT: "Hard cut, same passage, SAME
		# CAMERA, as the machine believes it." So it is not a new move: it is
		# shot 17's move, run again, with the cloud on instead of the lamp.
		# Identical anchors, ease and seed, so the two cut frame on frame. Its
		# sequence is not re-rendered here because it would be byte-identical
		# to 17's; the cloud side belongs to the lidar spike.
		{"name": "t18_belief_cut_plate", "trailer": "18", "len_s": 4.0,
		 "lens_mm": 35.0, "tstop": 2.8, "ease": "inout", "handheld_deg": 0.22,
		 "height": "machine", "seed": 17, "_same_camera_as": "t17_follow_machine",
		 "machine": {"role": "hero", "chassis": "surveyor", "loadout": "default",
			 "skin": "player", "wear": 0.35, "damage": 0.0, "lamp": true,
			 "clip": "walk", "yaw": "path",
			 "at": {"from": {"st": dense, "r": 0.0, "u": 0.0, "f": 3.20},
					"to":   {"st": dense, "r": 0.0, "u": 0.0, "f": 5.20}},
			 "head": [[-6.0, -3.0], [7.0, -5.0]]},
		 "move": {"from": {"st": dense, "r": 0.10, "u": 0.42, "f": 0.0},
				  "to":   {"st": dense, "r": 0.02, "u": 0.42, "f": 1.60}},
		 "look": {"from": {"st": dense, "r": 0.0, "u": 0.62, "f": 3.2},
				  "to":   {"st": dense, "r": 0.0, "u": 0.70, "f": 4.6}},
		 "focus": {"from": 2.4, "to": 3.2}},

		# The other reading of shot 18 -- that the camera keeps going through the
		# cut rather than repeating the move. PINNED TO STATION 116, the station
		# the first draft of shot 17 used, where it is REJECTED: 0.96 m further
		# down that drive the body finds geometry and the frustum finds the near
		# wall. At station 196, where 17 now stands, the same continuation is
		# legal. Kept in the list at 116 as the record of an authoring attempt
		# that failed, rather than quietly moved until it passed.
		{"name": "x18_continuation_at_116", "trailer": "18", "len_s": 4.0,
		 "lens_mm": 35.0, "tstop": 2.8, "ease": "out", "handheld_deg": 0.22,
		 "height": "machine", "seed": 17,
		 "machine": {"role": "hero", "chassis": "surveyor", "loadout": "default",
			 "skin": "player", "wear": 0.35, "damage": 0.0, "lamp": true,
			 "clip": "walk", "yaw": "path",
			 "at": {"from": {"st": 116, "r": 0.0, "u": 0.0, "f": 4.80},
					"to":   {"st": 116, "r": 0.0, "u": 0.0, "f": 6.80}},
			 "head": [0.0, -4.0]},
		 "move": {"from": {"st": 116, "r": 0.02, "u": 0.42, "f": 1.60},
				  "to":   {"st": 116, "r": 0.00, "u": 0.42, "f": 2.55}},
		 "look": {"from": {"st": 116, "r": 0.0, "u": 0.30, "f": 6.2},
				  "to":   {"st": 116, "r": 0.0, "u": 0.30, "f": 7.4}},
		 "focus": {"from": 3.4, "to": 3.9}},

		# 20 -- 1:24, 4s. "A sensor shadow: the clean wedge of no data behind a
		# fallen block. Hold on the emptiness." Held, but not frozen: TRAILER 6
		# forbids a still pretending to be footage, so it drifts 0.3 m and the
		# operator is breathing. At sensor height, because the wedge is cast
		# from the sensor and only reads from there.
		{"name": "t20_sensor_shadow", "trailer": "20", "len_s": 4.0,
		 "lens_mm": 35.0, "tstop": 2.0, "ease": "inout", "handheld_deg": 0.30,
		 "height": "machine", "seed": 20,
		 "move": {"from": {"st": spoil, "r": -0.20, "u": 0.40, "f": -1.20},
				  "to":   {"st": spoil, "r": -0.05, "u": 0.40, "f": -0.95}},
		 "look": {"from": {"st": spoil, "r": 0.40, "u": 0.35, "f": 0.6},
				  "to":   {"st": spoil, "r": 0.45, "u": 0.35, "f": 0.9}},
		 "focus": {"from": 1.9, "to": 1.9},
		 # The belief register. This frame is the plate the cloud is cut over,
		 # and the subject of it is the WEDGE OF MISSING DATA, not the machine
		 # that failed to see into it.
		 "machine": {"role": "none"}},

		# 27 -- 1:51, 3s. "The machine walking, confident, in completely the
		# wrong direction. Wide, small in frame." The longest sightline in the
		# cave, a wide lens, and a lateral drift so the frame is not a still.
		# The machine is in it, 11 m away, its own lamp the brightest thing in
		# the frame. At 21 mm that is about 60 px of machine, which NOTES 10's
		# legibility ladder puts above the 34 px where the chassis class stops
		# reading -- small in frame, still the same machine. It walks AWAY down
		# the drive, which is the confident part; the wrong part is that the
		# drive it is confident about is the wrong one.
		{"name": "t27_wrong_direction", "trailer": "27", "len_s": 3.0,
		 "lens_mm": 21.0, "tstop": 4.0, "ease": "inout", "handheld_deg": 0.0,
		 "height": "eye", "seed": 27,
		 "machine": {"role": "hero", "chassis": "surveyor", "loadout": "default",
			 "skin": "player", "wear": 0.35, "damage": 0.0, "lamp": true,
			 "clip": "walk", "yaw": "path",
			 # Off the centreline to the left: on the centreline at 11 m the
			 # machine stands behind a fallen slab and is cut off at the hips,
			 # which reads as an accident rather than as a composition. 0.30 m
			 # to the left is open floor for the whole move.
			 "at": {"from": {"st": lng, "r": -0.30, "u": 0.0, "f": 10.10},
					"to":   {"st": lng, "r": -0.30, "u": 0.0, "f": 11.60}},
			 "head": [12.0, -3.0]},
		 "move": {"from": {"st": lng, "r": -0.45, "u": 1.55, "f": 0.0},
				  "to":   {"st": lng, "r": 0.35, "u": 1.55, "f": 0.35}},
		 "look": {"from": {"st": lng, "r": 0.0, "u": 1.10, "f": 11.0},
				  "to":   {"st": lng, "r": 0.0, "u": 1.10, "f": 11.5}},
		 "focus": {"from": 9.0, "to": 9.0}},

		# THE OTHER DELIBERATE FAILURE, and it is the one TRAILER 11.1 asks
		# for. Every rule the camera has is satisfied -- this is shot 17's move
		# exactly. What is wrong is the MACHINE: it claims trailer beat 17 and
		# names a Scout on the rival livery at a different wear. In a cut
		# assembled out of four Godot projects that is precisely the mistake
		# nobody catches by looking, because each shot is fine on its own.
		{"name": "xfail_wrong_machine", "trailer": "17", "len_s": 4.0,
		 "lens_mm": 35.0, "tstop": 2.8, "ease": "inout", "handheld_deg": 0.22,
		 "height": "machine", "seed": 95,
		 "move": {"from": {"st": dense, "r": 0.10, "u": 0.42, "f": 0.0},
				  "to":   {"st": dense, "r": 0.02, "u": 0.42, "f": 1.60}},
		 "look": {"from": {"st": dense, "r": 0.0, "u": 0.62, "f": 3.2},
				  "to":   {"st": dense, "r": 0.0, "u": 0.70, "f": 4.6}},
		 "focus": {"from": 2.4, "to": 3.2},
		 "machine": {"role": "hero", "chassis": "scout", "loadout": "default",
			 "skin": "rival", "wear": 0.10, "damage": 0.0, "lamp": true,
			 "clip": "walk", "yaw": "path",
			 "at": {"from": {"st": dense, "r": 0.0, "u": 0.0, "f": 3.20},
					"to":   {"st": dense, "r": 0.0, "u": 0.0, "f": 5.20}}}},

		# THE DELIBERATE FAILURE. A push that leaves the centreline for the
		# wall, which is exactly the move a hand-flown camera makes when nobody
		# is checking. It must be rejected, not repaired.
		{"name": "xfail_through_the_wall", "trailer": "", "len_s": 4.5,
		 "lens_mm": 21.0, "tstop": 2.8, "ease": "inout", "handheld_deg": 0.0,
		 "height": "eye", "seed": 99,
		 "move": {"from": {"st": rail, "r": 0.0, "u": 1.60, "f": 0.0},
				  "to":   {"st": rail, "r": 2.20, "u": 1.60, "f": 0.6}},
		 "_why": "authored to fail: it leaves the centreline for the wall",
		 "look": {"from": {"st": rail, "r": 0.0, "u": 1.20, "f": 6.0},
				  "to":   {"st": rail, "r": 0.0, "u": 1.20, "f": 6.0}}},
	]
	var f := FileAccess.open("res://shots_cinema.json", FileAccess.WRITE)
	f.store_string(JSON.stringify(list, "  "))
	f.close()

func _cin_load_shots() -> void:
	if not FileAccess.file_exists("res://shots_cinema.json"):
		_cin_write_shots()
	var txt: String = FileAccess.get_file_as_string("res://shots_cinema.json")
	var v = JSON.parse_string(txt)
	cin_shots = v if v is Array else []
	if String(cfg["shot"]) != "":
		var only: Array = []
		for s in cin_shots:
			if String(s["name"]).contains(String(cfg["shot"])):
				only.append(s)
		cin_shots = only

# --- posing ----------------------------------------------------------------
func _cin_pose(shot: Dictionary, tn: float, fi: int) -> Dictionary:
	# The machine moves with the camera and on the SHOT'S clock. Offline
	# capture renders each frame many times over to let the scene settle, so
	# anything driven by the frame clock walks thirty times too fast.
	if fleet != null:
		fleet.hero_pose(shot, tn, tn * float(shot.get("len_s", 4.0)))
	var ps: Dictionary = rig.pose(shot, tn)
	cam.global_transform = Transform3D(ps["basis"], ps["pos"])
	cam.fov = CameraRig.fov_for(float(ps["lens"]))
	grade.apply(fx_mask, cam, float(ps["lens"]), float(ps["tstop"]), float(ps["focus"]))
	# The previous SHOT frame at the true capture rate. The sequence is
	# decimated for disk, but the shutter is computed against 1/60 s, so the
	# blur is the blur the finished 60 fps shot will have.
	var dt: float = (1.0 / float(cfg["capfps"])) / maxf(float(shot["len_s"]), 0.01)
	var pp: Dictionary = rig.pose(shot, maxf(tn - dt, 0.0))
	grade.lens.use_external_prev = true
	grade.lens.external_prev = Transform3D(pp["basis"], pp["pos"])
	grade.lens.seedt = float(fi) * 7.31 + 0.5
	return ps

func _cin_grab(path: String) -> void:
	for k in range(SETTLE):
		await RenderingServer.frame_post_draw
	var img: Image = sub.get_texture().get_image()
	img.save_png(ProjectSettings.globalize_path(path))

func _cin_gpu_median(n: int) -> float:
	var v: Array = []
	for i in range(n):
		await RenderingServer.frame_post_draw
		if i >= 8:
			v.append(RenderingServer.viewport_get_measured_render_time_gpu(sub.get_viewport_rid()))
	v.sort()
	return v[v.size() / 2] if v.size() > 0 else 0.0

# ===========================================================================
func _cinema_run() -> void:
	busy = true
	_cin_load_shots()
	match String(cfg["cinema"]):
		"validate": await _cin_validate()
		"pairs": await _cin_pairs()
		"stack": await _cin_stack()
		"seq": await _cin_seq()
		"hero": await _cin_hero()
		"fail": await _cin_fail()
		"cost": await _cin_cost()
		"veldbg": await _cin_veldbg()
		"probe": await _cin_probe()
		"scout": await _cin_scout()
		"tune": await _cin_tune()
		"mvcost": await _cin_mvcost()
		"contract": await _cin_contract()
		"locations": await _cin_locations()
		_:
			print("cinema: unknown mode ", cfg["cinema"])
	busy = false
	phase = 3
	if not cfg["stay"]:
		await get_tree().create_timer(0.3).timeout
		get_tree().quit()

# --- 1. validation ---------------------------------------------------------
func _cin_validate() -> void:
	await get_tree().physics_frame
	await get_tree().physics_frame
	rig.ready_space(world_root)
	_cin("=== SHOT VALIDATION -- TRAILER.md 8 and 11.1 ===")
	_cin(Hero.banner())
	_cin("body sphere %.2f m, near clearance %.2f m, query margin %.2f m" % [
		CameraRig.BODY_R, CameraRig.NEAR_CLEAR, CameraRig.QUERY_MARGIN])
	_cin("collision: %d shell triangles + %d prop boxes, built in %.0f ms" % [
		rig.collision_tris, rig.collision_props, rig.build_ms])
	_cin("")
	var npass: int = 0
	for s in cin_shots:
		var r: Dictionary = rig.validate(s)
		var st: Dictionary = r["stats"]
		var dof: Array = st["dof"]
		_cin("%-26s trailer %-3s  %s" % [r["name"], str(s.get("trailer", "-")),
			"PASS" if r["ok"] else "REJECTED"])
		_cin("   %.0f mm (%.1f deg v)  T%.1f  %.1fs  ease %s  handheld %.2f deg" % [
			float(s["lens_mm"]), float(st["fov"]), float(s.get("tstop", 2.8)),
			float(s["len_s"]), s.get("ease", "inout"), float(s.get("handheld_deg", 0.0))])
		_cin("   travel %.2f m  peak %.2f m/s  clearance %.2f m  height %.2f-%.2f m (%s)" % [
			float(st["travel"]), float(st["vmax"]), float(st["clear"]),
			float(st["h_lo"]), float(st["h_hi"]), s.get("height", "eye")])
		_cin("   depth of field: sharp %.2f m to %s (hyperfocal %.1f m)" % [
			float(dof[0]), ("infinity" if float(dof[1]) > 900.0 else "%.2f m" % float(dof[1])),
			float(dof[2])])
		_cin("   machine: %s" % Hero.describe(Hero.block(s)))
		for w in r["warn"]:
			_cin("   warn: " + str(w))
		for x in r["fail"]:
			_cin("   FAIL: " + str(x))
		if r["ok"]:
			npass += 1
		_cin("")
	_cin("%d of %d shots execute; %d rejected." % [npass, cin_shots.size(),
		cin_shots.size() - npass])
	_cin("")
	_cin("--- continuity: every shot that names the hero machine ---")
	var au: Array[String] = Hero.audit(cin_shots, "cave")
	if au.is_empty():
		_cin("   one machine, in every shot that has one.")
	for a in au:
		_cin("   " + a)
	_cin_flush("validation.txt")

# --- 2. before/after pairs, cumulative, in TRAILER 9's order ---------------
func _cin_pairs() -> void:
	await get_tree().physics_frame
	rig.ready_space(world_root)
	var shot: Dictionary = _cin_named("t16_lamp_comes_on")
	var tn: float = 0.55
	_cin("=== BEFORE / AFTER, cumulative, TRAILER 9 order ===")
	_cin("pose: %s at t=%.2f, identical for every pair" % [shot["name"], tn])
	var acc: int = 0
	var i: int = 0
	for nm in CinemaGrade.ORDER:
		var before: int = acc
		acc |= int(CinemaGrade.NAMES[nm])
		fx_mask = before
		_cin_pose(shot, tn, 3)
		await _cin_grab(CIN_DIR + "pairs/%02d_%s_off.png" % [i, nm])
		fx_mask = acc
		_cin_pose(shot, tn, 3)
		await _cin_grab(CIN_DIR + "pairs/%02d_%s_on.png" % [i, nm])
		_cin("%02d %-9s off=%-28s on=%s" % [i, nm, CinemaGrade.mask_str(before),
			CinemaGrade.mask_str(acc)])
		i += 1
	_cin_flush("pairs.txt")

# --- 3. the whole stack, on and off, three frames --------------------------
func _cin_stack() -> void:
	await get_tree().physics_frame
	rig.ready_space(world_root)
	var picks: Array = [["t16_lamp_comes_on", 0.30], ["t20_sensor_shadow", 0.50],
		["t27_wrong_direction", 0.65]]
	_cin("=== FULL STACK ON / OFF ===")
	for p in picks:
		var shot: Dictionary = _cin_named(String(p[0]))
		var tn: float = float(p[1])
		# "off" is the spike as it stood: AgX and nothing else. Comparing
		# against LINEAR would be comparing against a picture nobody would ship.
		fx_mask = CinemaGrade.E_TONEMAP
		_cin_pose(shot, tn, 3)
		await _cin_grab(CIN_DIR + "stack/%s_off.png" % shot["name"])
		fx_mask = CinemaGrade.ALL
		_cin_pose(shot, tn, 3)
		await _cin_grab(CIN_DIR + "stack/%s_on.png" % shot["name"])
		_cin("%s at t=%.2f, %.0f mm" % [shot["name"], tn, float(shot["lens_mm"])])
	_cin_flush("stack.txt")

# --- 4. the sequences ------------------------------------------------------
func _cin_seq() -> void:
	await get_tree().physics_frame
	rig.ready_space(world_root)
	# TRAILER 11.3. Every shot used to render `seqframes` frames regardless of
	# `len_s`, and the default was 24 -- one second at 24 fps. The designer's
	# note on the rough cut: "The rough cuts of 1 second footage is very
	# jarring." It is not a cut artefact, it is the capture: a 4-second push
	# rendered as 24 frames is a 4x speed-up. A shot is now its own length at
	# CUT_FPS, which is 72 frames for a 3 s shot and 120 for a 5 s one.
	#
	# 24 fps rather than the 60 the capture rule names is a deliberate
	# separation: 60 is the rate the MOTION BLUR is computed against (capfps,
	# because that is the shutter the finished shot has); 24 is the rate the
	# frames are CUT at. --seqframes= still forces a count, for a quick look.
	for shot in cin_shots:
		if String(shot["name"]).begins_with("x"):
			continue
		if shot.has("_same_camera_as"):
			_cin("SKIP %s -- identical camera to %s by design" % [
				shot["name"], shot["_same_camera_as"]])
			continue
		var r: Dictionary = rig.validate(shot)
		if not r["ok"]:
			_cin("SKIP %s -- rejected: %s" % [shot["name"], "; ".join(r["fail"])])
			continue
		var dir: String = CIN_DIR + "seq/" + String(shot["name"]) + "/"
		DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(dir))
		var n: int = int(cfg["seqframes"])
		if n <= 0:
			n = maxi(24, int(round(float(shot.get("len_s", 1.0)) * CUT_FPS)))
		var t_shot: int = Time.get_ticks_msec()
		_cin("=== %s  %.0f mm  %.1f s  %d frames at %.0f fps ===" % [shot["name"],
			float(shot["lens_mm"]), float(shot["len_s"]), n, CUT_FPS])
		_cin("    machine: %s" % Hero.describe(Hero.block(shot)))
		_cin("  frame     t_s      x       y       z    step_mm   focus_m")
		var prev: Vector3 = Vector3.ZERO
		for i in range(n):
			var tn: float = float(i) / float(n - 1)
			var ps: Dictionary = _cin_pose(shot, tn, i)
			await _cin_grab(dir + "%03d.png" % i)
			var p: Vector3 = ps["pos"]
			var step: float = 0.0 if i == 0 else p.distance_to(prev) * 1000.0
			_cin("  %5d  %6.3f  %6.2f  %6.2f  %6.2f  %8.1f  %7.2f" % [
				i, tn * float(shot["len_s"]), p.x, p.y, p.z, step, float(ps["focus"])])
			prev = p
		var el: float = float(Time.get_ticks_msec() - t_shot) / 1000.0
		_cin("    %d frames in %.1f s = %.2f s/frame" % [n, el, el / float(n)])
		if fleet != null and fleet.misses > 0:
			_cin("    floor probes with no hit in the window: %d" % fleet.misses)
			fleet.misses = 0
		_cin("")
	_cin_flush("sequences.txt")

# --- 4b. where the machine IS on screen ------------------------------------
## Writes shots/cinema/hero_boxes.json: for every shot that names the hero, the
## frame to look at and the pixel rectangle the machine occupies in it. The
## continuity contact sheet is built from this rather than hand-cropped, so a
## wrong chassis or a wrong livery is visible at a glance across all of it.
## Renders nothing.
func _cin_hero() -> void:
	await get_tree().physics_frame
	rig.ready_space(world_root)
	var out: Dictionary = {"project": "cave", "hero": Hero.SPEC,
		"fps": CUT_FPS, "shots": []}
	_cin("=== HERO BOXES ===")
	_cin(Hero.banner())
	for shot in cin_shots:
		var nm: String = String(shot["name"])
		if not Hero.is_hero(shot) or nm.begins_with("x"):
			continue
		if shot.has("_same_camera_as"):
			continue
		if not rig.validate(shot)["ok"]:
			continue
		var nf: int = maxi(24, int(round(float(shot.get("len_s", 1.0)) * CUT_FPS)))
		var fi: int = int(round(0.72 * float(nf - 1)))
		var tn: float = float(fi) / float(nf - 1)
		_cin_pose(shot, tn, fi)
		var r: Rect2 = _hero_rect()
		out["shots"].append({"name": nm, "trailer": String(shot.get("trailer", "")),
			"dir": "shots/cinema/seq/%s" % nm, "frame": fi, "frames": nf,
			"lens_mm": float(shot["lens_mm"]), "len_s": float(shot["len_s"]),
			"machine": Hero.describe(Hero.block(shot)),
			"rect": [r.position.x, r.position.y, r.size.x, r.size.y]})
		_cin("%-24s frame %3d of %3d   rect %4.0f %4.0f  %4.0f x %4.0f px"
			% [nm, fi, nf, r.position.x, r.position.y, r.size.x, r.size.y])
	var f := FileAccess.open(ProjectSettings.globalize_path(
		CIN_DIR + "hero_boxes.json"), FileAccess.WRITE)
	if f:
		f.store_string(JSON.stringify(out, "  "))
		f.close()
	_cin_flush("hero.txt")

## The eight corners of the machine's mesh AABB, in the camera's projection.
func _hero_rect() -> Rect2:
	var m: Machine = fleet.hero
	var ab: AABB = m.mi.get_aabb()
	var xf: Transform3D = m.mi.global_transform
	var lo := Vector2(1e9, 1e9)
	var hi := Vector2(-1e9, -1e9)
	for i in range(8):
		var c: Vector3 = xf * (ab.position + Vector3(
			ab.size.x * float(i & 1), ab.size.y * float((i >> 1) & 1),
			ab.size.z * float((i >> 2) & 1)))
		if cam.is_position_behind(c):
			continue
		var q: Vector2 = cam.unproject_position(c)
		lo = Vector2(minf(lo.x, q.x), minf(lo.y, q.y))
		hi = Vector2(maxf(hi.x, q.x), maxf(hi.y, q.y))
	if hi.x < lo.x:
		return Rect2(0, 0, 0, 0)
	return Rect2(lo, hi - lo)

# --- 5. the deliberate failure --------------------------------------------
func _cin_fail() -> void:
	await get_tree().physics_frame
	rig.ready_space(world_root)
	var shot: Dictionary = _cin_named("xfail_through_the_wall")
	var r: Dictionary = rig.validate(shot)
	_cin("=== THE DELIBERATE FAILURE ===")
	_cin("%s: %s" % [shot["name"], "PASS" if r["ok"] else "REJECTED"])
	for x in r["fail"]:
		_cin("  FAIL: " + str(x))
	# find the last legal t and the first illegal one, and photograph both
	var last_ok: float = 0.0
	var first_bad: float = -1.0
	for i in range(65):
		var tn: float = float(i) / 64.0
		var ps: Dictionary = rig.pose(shot, tn)
		var p: Vector3 = ps["pos"]
		var clear: float = rig._frustum_clear(p, ps["basis"], float(shot["lens_mm"]))
		var bad: bool = rig._overlaps(p) or clear < CameraRig.NEAR_CLEAR - 0.001
		if bad and first_bad < 0.0:
			first_bad = tn
		if not bad and first_bad < 0.0:
			last_ok = tn
	_cin("last legal t = %.3f, first rejected t = %.3f" % [last_ok, first_bad])
	fx_mask = CinemaGrade.ALL
	for pair in [["a_start", 0.0], ["b_last_legal", last_ok],
				 ["c_rejected", maxf(first_bad, 0.0)], ["d_end_inside_rock", 1.0]]:
		var tn: float = float(pair[1])
		var ps: Dictionary = _cin_pose(shot, tn, 3)
		await _cin_grab(CIN_DIR + "fail/%s.png" % String(pair[0]))
		var p: Vector3 = ps["pos"]
		_cin("  %-18s t=%.3f  pos %.2f %.2f %.2f  overlaps=%s  clearance=%.2f m" % [
			String(pair[0]), tn, p.x, p.y, p.z, str(rig._overlaps(p)),
			rig._frustum_clear(p, ps["basis"], float(shot["lens_mm"]))])
	_cin("")
	_cin("The rig does not move the camera to a legal place and it does not stop")
	_cin("short. It rejects the shot and names the number that rejected it. The")
	_cin("frames above are what would have been shipped if it had not.")
	_cin_flush("failure.txt")

# --- 6. cost ---------------------------------------------------------------
func _cin_cost() -> void:
	await get_tree().physics_frame
	rig.ready_space(world_root)
	var shot: Dictionary = _cin_named("t16_lamp_comes_on")
	_cin("=== COST, leave-one-out from the full stack ===")
	_cin("1920x1080, pose %s t=0.55. Interleaved A/B/A/B/A/B, 56 frames a block," % shot["name"])
	_cin("median GPU ms of each block, reported as the median of the deltas.")
	_cin("")
	_cin("%-10s %8s %8s %8s   %s" % ["effect", "with", "without", "cost ms", "verdict"])
	for nm in CinemaGrade.ORDER:
		var bit: int = int(CinemaGrade.NAMES[nm])
		var ds: Array = []
		var wa: Array = []
		var wo: Array = []
		for rep in range(3):
			fx_mask = CinemaGrade.ALL
			_cin_pose(shot, 0.55, rep)
			var a: float = await _cin_gpu_median(56)
			fx_mask = CinemaGrade.ALL & ~bit
			_cin_pose(shot, 0.55, rep)
			var b: float = await _cin_gpu_median(56)
			wa.append(a); wo.append(b); ds.append(a - b)
		ds.sort(); wa.sort(); wo.sort()
		_cin("%-10s %8.2f %8.2f %8.2f" % [nm, wa[1], wo[1], ds[1]])
	# and the two ends
	# THE STATIC POSE UNDER-REPORTS MOTION BLUR. At t16's 0.49 m/s the frame
	# moves under a third of a pixel, so the tap loop collapses to n=1 and the
	# row above measures only the reprojection arithmetic. Re-measured at a
	# pose that actually moves: t27's lateral drift, run at 1.2 s.
	var fast: Dictionary = _cin_named("t27_wrong_direction").duplicate(true)
	fast["len_s"] = 1.2
	_cin("")
	_cin("re-measured on a moving frame (t27 at 1.2 s, 14.7%% of pixels blurred):")
	for nm in ["mblur", "ca"]:
		var bit2: int = int(CinemaGrade.NAMES[nm])
		var d2: Array = []
		var w2: Array = []
		var o2: Array = []
		for rep in range(3):
			fx_mask = CinemaGrade.ALL
			_cin_pose(fast, 0.50, rep)
			var a2: float = await _cin_gpu_median(56)
			fx_mask = CinemaGrade.ALL & ~bit2
			_cin_pose(fast, 0.50, rep)
			var b2: float = await _cin_gpu_median(56)
			w2.append(a2); o2.append(b2); d2.append(a2 - b2)
		d2.sort(); w2.sort(); o2.sort()
		_cin("%-10s %8.2f %8.2f %8.2f" % [nm, w2[1], o2[1], d2[1]])

	fx_mask = 0
	_cin_pose(shot, 0.55, 0)
	var none_ms: float = await _cin_gpu_median(80)
	fx_mask = CinemaGrade.ALL
	_cin_pose(shot, 0.55, 0)
	var all_ms: float = await _cin_gpu_median(80)
	fx_mask = 0
	_cin_pose(shot, 0.55, 0)
	var none2: float = await _cin_gpu_median(80)
	_cin("")
	_cin("stack off  %.2f ms  (repeat %.2f ms)" % [none_ms, none2])
	_cin("stack on   %.2f ms" % all_ms)
	_cin("whole stack %.2f ms over an untreated frame" % (all_ms - (none_ms + none2) * 0.5))
	_cin("")
	_cin("THERMAL: %s" % _gpu_state())
	_cin_flush("cost.txt")

# --- 7. the reprojection sanity frame --------------------------------------
# A dolly-in must produce velocity pointing OUTWARD from the frame centre. In
# texture space row 0 is the top, so the top half of the frame must read vel.y
# < 0 (drawn red) and the bottom half vel.y > 0 (drawn blue). If that is upside
# down, the render target's Y is flipped relative to NDC and every motion blur
# in the project is smearing along the wrong diagonal.
func _cin_veldbg() -> void:
	await get_tree().physics_frame
	rig.ready_space(world_root)
	var shot: Dictionary = _cin_named("t16_lamp_comes_on")
	fx_mask = CinemaGrade.ALL
	var ps: Dictionary = rig.pose(shot, 0.55)
	cam.global_transform = Transform3D(ps["basis"], ps["pos"])
	cam.fov = CameraRig.fov_for(float(ps["lens"]))
	grade.apply(fx_mask, cam, float(ps["lens"]), float(ps["tstop"]), float(ps["focus"]))
	grade.lens.use_external_prev = true
	# a large, unambiguous dolly straight back along the view axis
	grade.lens.external_prev = Transform3D(ps["basis"], ps["pos"] - (-ps["basis"].z) * 0.25)
	grade.lens.max_blur_px = 4000.0
	grade.lens.flags = CinemaLens.F_MBLUR | CinemaLens.F_VELDBG
	await _cin_grab(CIN_DIR + "diag/veldbg_dolly_in.png")
	grade.lens.max_blur_px = 40.0
	_cin("=== reprojection sanity ===")
	_cin("diag/veldbg_dolly_in.png -- dolly IN by 0.25 m.")
	_cin("Correct: TOP half red, BOTTOM half blue. Inverted: the other way round.")
	_cin_flush("veldbg.txt")

# A location scout. Sweeps the main drive with a template move and reports the
# stations where the rig would accept it. This is authoring, not repairing: it
# says where a shot COULD stand, the shot list is then written by hand against
# the answer, and the validator still governs what ships.
# Showcase frames for the three effects that a slow wide static pose cannot
# show: bloom needs a source above threshold, motion blur needs motion, depth
# of field needs something close.
# Is per-object motion blur affordable at all?
#
# The question is not the blur, it is the PREREQUISITE. Godot 4.7 only produces
# a velocity buffer when something asks for one (TAA, FSR2, or a CompositorEffect
# with needs_motion_vectors). Asking for it makes every opaque draw write motion
# vectors and keeps a second copy of every transform, so it is paid on the whole
# scene whether or not anything in it moves. This measures that, interleaved.
# ART-DIRECTION 2.9 on the frames the cinematic layer actually produces. If the
# lens quietly darkens the picture, this is what says so.
# Photograph one shot from several candidate stations so the station can be
# chosen by looking rather than by a sightline number. The sightline says the
# camera CAN see a long way; it does not say what is in the first two metres.
func _cin_locations() -> void:
	await get_tree().physics_frame
	rig.ready_space(world_root)
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(CIN_DIR + "loc"))
	var tpl: Dictionary = _cin_named(String(cfg["shot"])).duplicate(true)
	fx_mask = CinemaGrade.ALL
	for stx in String(cfg["stations"]).split(",", false):
		var i: int = int(stx)
		for grp in ["move", "look"]:
			for k in (tpl[grp] as Dictionary).keys():
				if tpl[grp][k] is Dictionary:
					tpl[grp][k]["st"] = i
		var r: Dictionary = rig.validate(tpl)
		_cin_pose(tpl, 0.5, 3)
		await _cin_grab(CIN_DIR + "loc/%s_st%03d.png" % [tpl["name"], i])
		_cin("st %3d  %s  sight-checked frame written" % [i, "PASS" if r["ok"] else "REJECTED"])
	_cin_flush("locations.txt")

func _cin_contract() -> void:
	await get_tree().physics_frame
	rig.ready_space(world_root)
	for d in ["contract_off", "contract_on"]:
		DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(CIN_DIR + d))
	for shot in cin_shots:
		if String(shot["name"]).begins_with("x") or shot.has("_same_camera_as"):
			continue
		for tn in [0.15, 0.50, 0.85]:
			fx_mask = CinemaGrade.E_TONEMAP
			_cin_pose(shot, tn, 3)
			await _cin_grab(CIN_DIR + "contract_off/%s_%02d.png" % [shot["name"], int(tn * 100)])
			fx_mask = CinemaGrade.ALL
			_cin_pose(shot, tn, 3)
			await _cin_grab(CIN_DIR + "contract_on/%s_%02d.png" % [shot["name"], int(tn * 100)])
	_cin("contract frames written: AgX-only in contract_off, full stack in contract_on")
	_cin_flush("contract.txt")

func _cin_mvcost() -> void:
	await get_tree().physics_frame
	rig.ready_space(world_root)
	var shot: Dictionary = _cin_named("t16_lamp_comes_on")
	fx_mask = CinemaGrade.ALL
	_cin("=== per-object motion blur: the cost of asking for motion vectors ===")
	var wa: Array = []
	var wo: Array = []
	for rep in range(3):
		grade.lens.needs_motion_vectors = false
		_cin_pose(shot, 0.55, rep)
		wo.append(await _cin_gpu_median(64))
		grade.lens.needs_motion_vectors = true
		_cin_pose(shot, 0.55, rep)
		wa.append(await _cin_gpu_median(64))
	grade.lens.needs_motion_vectors = false
	wa.sort(); wo.sort()
	_cin("needs_motion_vectors=false  %.2f ms   (%s)" % [wo[1], str(wo)])
	_cin("needs_motion_vectors=true   %.2f ms   (%s)" % [wa[1], str(wa)])
	_cin("velocity pass costs %.2f ms before a single blur tap is taken" % (wa[1] - wo[1]))
	_cin_flush("mvcost.txt")

func _cin_tune() -> void:
	await get_tree().physics_frame
	rig.ready_space(world_root)
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(CIN_DIR + "tune"))
	_cin("=== TUNING FRAMES ===")
	var s16: Dictionary = _cin_named("t16_lamp_comes_on")
	# --- bloom threshold sweep, at a pose with a beacon pilot in it ----------
	fx_mask = CinemaGrade.E_TONEMAP
	_cin_pose(s16, 0.55, 3)
	grade.env.glow_enabled = false
	await _cin_grab(CIN_DIR + "tune/bloom_off.png")
	for th in [0.8, 1.6, 2.6, 4.0]:
		fx_mask = CinemaGrade.E_TONEMAP | CinemaGrade.E_BLOOM
		_cin_pose(s16, 0.55, 3)
		grade.env.glow_hdr_threshold = th
		await _cin_grab(CIN_DIR + "tune/bloom_t%0.1f.png" % th)
		_cin("bloom threshold %.1f" % th)
	# --- motion blur, at the fastest instant of the fastest shot -------------
	var s27: Dictionary = _cin_named("t27_wrong_direction")
	for on in [false, true]:
		fx_mask = CinemaGrade.E_TONEMAP | (CinemaGrade.E_MBLUR if on else 0)
		_cin_pose(s27, 0.50, 3)
		await _cin_grab(CIN_DIR + "tune/mblur_t27_%s.png" % ("on" if on else "off"))
	# and the same shot as if it were a 2x faster move, to show the shutter
	var fast: Dictionary = s27.duplicate(true)
	fast["len_s"] = 1.2
	for on in [false, true]:
		fx_mask = CinemaGrade.E_TONEMAP | (CinemaGrade.E_MBLUR if on else 0)
		_cin_pose(fast, 0.50, 3)
		await _cin_grab(CIN_DIR + "tune/mblur_fast_%s.png" % ("on" if on else "off"))
	_cin("motion blur: t27 at its peak (%.2f m/s) and the same move at 1.2 s" % 0.55)
	# --- depth of field, on the shallowest shot in the list ------------------
	var s20: Dictionary = _cin_named("t20_sensor_shadow")
	for on in [false, true]:
		fx_mask = CinemaGrade.E_TONEMAP | (CinemaGrade.E_DOF if on else 0)
		_cin_pose(s20, 0.50, 3)
		await _cin_grab(CIN_DIR + "tune/dof_t20_%s.png" % ("on" if on else "off"))
	_cin("depth of field: t20, 35 mm at T2.0 focused 1.9 m -- the shallowest in the list")
	# --- what focal length does the LAMP allow? -----------------------------
	# The work lamp is a 54 degree cone (spot_angle 27). A lens whose horizontal
	# field matches it is 18/tan(27) = 35.3 mm. Anything wider is looking at
	# rock the lamp is not lighting.
	for mm in [21.0, 28.0, 35.0, 50.0]:
		var v: Dictionary = s16.duplicate(true)
		v["lens_mm"] = mm
		fx_mask = CinemaGrade.ALL
		_cin_pose(v, 0.55, 3)
		await _cin_grab(CIN_DIR + "tune/lens_%02dmm.png" % int(mm))
	_cin("focal length sweep at the t16 pose: 21 / 28 / 35 / 50 mm against a 54 deg lamp")
	_cin_flush("tune.txt")

func _cin_scout() -> void:
	await get_tree().physics_frame
	await get_tree().physics_frame
	rig.ready_space(world_root)
	var ids: PackedInt32Array = topo.edges[0]
	var tpl: Dictionary = _cin_named(String(cfg["shot"])).duplicate(true)
	if tpl.is_empty():
		print("SCOUT needs --shot=NAME as the template")
		return
	print("SCOUT template = %s  (%s at %.0f mm)" % [tpl["name"], tpl["height"], float(tpl["lens_mm"])])
	var good: Array = []
	for i in range(6, ids.size() - 30, 2):
		var sd: PackedInt32Array = topo.stations[ids[i]]
		if sd[CaveTopology.S_WIDTH] < CaveTopology.WC_PASSAGE:
			continue
		if sd[CaveTopology.S_STATE] == CaveTopology.FLOODED:
			continue
		for grp in ["move", "look"]:
			for k in (tpl[grp] as Dictionary).keys():
				var an = tpl[grp][k]
				if an is Dictionary:
					an["st"] = i
		var r: Dictionary = rig.validate(tpl)
		if r["ok"]:
			var st2: Dictionary = r["stats"]
			good.append(i)
			# how far can this camera actually see? "Wide, small in frame"
			# needs a sightline, and ART-DIRECTION 3.6 measured the median at
			# 3.6 m, so the ones that have one are worth finding.
			var ps0: Dictionary = rig.pose(tpl, 0.0)
			var rq := PhysicsRayQueryParameters3D.create(ps0["pos"],
				ps0["pos"] + (-(ps0["basis"] as Basis).z) * 60.0)
			rq.collision_mask = 1
			var h0: Dictionary = rig._ss().intersect_ray(rq)
			var sight: float = 60.0 if h0.is_empty() else (ps0["pos"] as Vector3).distance_to(h0["position"])
			print("SCOUT ok st=%3d  works=0x%05X worked=%3d clear=%.2f h=%.2f-%.2f sight=%.1f m" % [
				i, sd[CaveTopology.S_WORKS], sd[CaveTopology.S_WORKED],
				float(st2["clear"]), float(st2["h_lo"]), float(st2["h_hi"]), sight])
	print("SCOUT %s: %d stations of the drive accept it" % [tpl["name"], good.size()])
	print("SCOUT stations: ", good)

func _cin_probe() -> void:
	await get_tree().physics_frame
	await get_tree().physics_frame
	rig.ready_space(world_root)
	var st: Dictionary = _cin_stations()
	print("stations: ", st)
	var ids: PackedInt32Array = topo.edges[0]
	for key in ["rail", "dense", "long", "spoil"]:
		var i: int = int(st[key])
		var fr: Array = rig.frame_at(i)
		var floorp: Vector3 = fr[0]
		var sd: PackedInt32Array = topo.stations[ids[i]]
		print("--- %s st=%d floor=%s width=%d worked=%d works=0x%X hw=%.2f ht=%.2f" % [
			key, i, str(floorp.snapped(Vector3(0.01,0.01,0.01))), sd[CaveTopology.S_WIDTH],
			sd[CaveTopology.S_WORKED], sd[CaveTopology.S_WORKS],
			dress._hw(sd), dress._ht(sd)])
		for h in [0.4, 1.0, 1.6]:
			var p: Vector3 = floorp + Vector3.UP * h
			var q := PhysicsShapeQueryParameters3D.new()
			q.shape = rig.body
			q.transform = Transform3D(Basis.IDENTITY, p)
			q.margin = 0.05
			q.collision_mask = 1
			var hits: Array = rig._ss().intersect_shape(q, 8)
			var names: Array = []
			for hh in hits:
				var col = hh["collider"]
				names.append("%s#%d" % [str(col.name) if col else "?", int(hh["shape"])])
			print("   h=%.2f  hits=%d  %s  floor_under=%.3f  head=%.3f" % [
				h, hits.size(), str(names), rig.floor_under(p), rig.head_room(p)])
			var dn := PhysicsRayQueryParameters3D.create(p + Vector3.UP*0.05, p - Vector3.UP*12.0)
			dn.collision_mask = 1
			var hit: Dictionary = rig._ss().intersect_ray(dn)
			if not hit.is_empty():
				print("        down-ray hit at y=%.3f  normal=%s" % [
					float((hit["position"] as Vector3).y), str(hit["normal"].snapped(Vector3(0.01,0.01,0.01)))])
	print("static_root children: ", rig.static_root.get_child_count())
	var c0 = rig.static_root.get_child(0)
	print("first shape: ", c0.shape, " gt=", c0.global_transform)

func _gpu_state() -> String:
	var o: Array = []
	OS.execute("nvidia-smi", ["--query-gpu=temperature.gpu,clocks.sm,utilization.gpu",
		"--format=csv,noheader,nounits"], o)
	return String(o[0]).strip_edges() if o.size() > 0 else "unknown"

func _cin_named(n: String) -> Dictionary:
	for s in cin_shots:
		if String(s["name"]) == n:
			return s
	return cin_shots[0] if cin_shots.size() > 0 else {}
