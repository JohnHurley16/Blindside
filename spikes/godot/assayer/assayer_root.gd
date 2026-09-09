# ---------------------------------------------------------------------------
# BLINDSIDE assayer spike -- scene, ONE CLOCK, the shots and the numbers.
#
# Renders into a SubViewport fixed at exactly 1920x1080, for the reason the
# cave spike records: this desktop is a 1080p panel at 125% scaling, so a
# 1920x1080 WINDOW cannot exist in logical coordinates and every PNG would
# quietly be 1536x864. The window is only a way to look at the viewport.
#
# THE ONE CLOCK. `cycle_t` is the only piece of state in the scene that moves.
# The machine's aim, the hammer's height, the chain's length, the tank's level,
# the colour and output of both hot points, the recoil and the drip are all
# pure functions of it, computed in Assayer.set_phase(). There is no second
# timeline anywhere and no animation player.
#
# Command line (after a bare --):
#   --shots         the twelve stills, then quit          (the default)
#   --seq           the three trailer shots as sequences
#   --clear         the CLEAR rig: a neutral studio key, for the design read.
#                   NOT THE GAME, and every frame it makes says so in its name.
#   --run           run the cycle live in the window
#   --p=N           start the clock at phase N seconds
#   --stay          do not quit
# ---------------------------------------------------------------------------
extends Node3D

const SHOT_DIR := "res://shots/"
const SEQ_DIR := "res://shots/seq/"

var cfg := {
	"seed": 7, "clear": false, "shots": true, "seq": false, "run": false,
	"p": 0.0, "stay": false, "shotdir": "", "calib": false, "dbg": false,
	"hot": 0.0, "shellshadow": "", "noshadow": false, "bias": 0.0, "nbias": 1.4,
}

var sub: SubViewport
var cam: Camera3D
var camlamp: SpotLight3D
var world: Node3D
var env: Environment
var machine: Assayer
var room: Chamber
var dog: Surveyor
var dog2: Surveyor
var key: DirectionalLight3D
var fill: OmniLight3D
var clear_ground: MeshInstance3D
var svc: SubViewportContainer

var cycle_t: float = 0.0
var busy: bool = false
var hud: Label
var gen_ms_mat: float = 0.0
var gen_ms_room: float = 0.0
var gen_ms_mach: float = 0.0
var shot_dir: String = SHOT_DIR


func _stage(msg: String) -> void:
	var f := FileAccess.open("res://progress.log", FileAccess.READ_WRITE)
	if f == null:
		f = FileAccess.open("res://progress.log", FileAccess.WRITE)
	if f:
		f.seek_end()
		f.store_line("%8.2f  %s" % [Time.get_ticks_msec() / 1000.0, msg])
		f.close()


func _parse() -> void:
	var args: PackedStringArray = OS.get_cmdline_user_args()
	for a in OS.get_cmdline_args():
		args.append(a)
	for a in args:
		if a == "--clear":
			cfg["clear"] = true
		elif a == "--seq":
			cfg["seq"] = true
			cfg["shots"] = false
		elif a == "--run":
			cfg["run"] = true
			cfg["shots"] = false
		elif a == "--stay":
			cfg["stay"] = true
		elif a.begins_with("--p="):
			cfg["p"] = float(a.substr(4))
		elif a.begins_with("--seed="):
			cfg["seed"] = int(a.substr(7))
		elif a == "--calib":
			cfg["calib"] = true
			cfg["shots"] = false
		elif a.begins_with("--bias="):
			var pr: PackedStringArray = a.substr(7).split(",")
			cfg["bias"] = float(pr[0])
			cfg["nbias"] = float(pr[1]) if pr.size() > 1 else 1.4
		elif a == "--noshadow":
			cfg["noshadow"] = true
		elif a == "--shellshadow=off":
			cfg["shellshadow"] = "off"
		elif a == "--dbg":
			cfg["dbg"] = true
			cfg["shots"] = false
		elif a.begins_with("--hot="):
			cfg["hot"] = float(a.substr(6))
		elif a.begins_with("--shotdir="):
			cfg["shotdir"] = a.substr(10)


func _ready() -> void:
	var pf := FileAccess.open("res://progress.log", FileAccess.WRITE)
	if pf:
		pf.close()
	_parse()
	shot_dir = SHOT_DIR
	if String(cfg["shotdir"]) != "":
		shot_dir = SHOT_DIR + String(cfg["shotdir"]) + "/"
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(shot_dir))
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(SEQ_DIR))

	svc = SubViewportContainer.new()
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

	world = Node3D.new()
	sub.add_child(world)
	_environment()

	var t0: int = Time.get_ticks_usec()
	var mats := AssayerMaterials.new()
	mats.build(cfg["seed"], Chamber.WATER_Y)
	var t1: int = Time.get_ticks_usec()
	room = Chamber.new()
	room.build(mats, cfg["seed"])
	world.add_child(room)
	var t2: int = Time.get_ticks_usec()
	machine = Assayer.new()
	machine.build(mats, cfg["seed"])
	world.add_child(machine)
	var t3: int = Time.get_ticks_usec()
	gen_ms_mat = float(t1 - t0) / 1000.0
	gen_ms_room = float(t2 - t1) / 1000.0
	gen_ms_mach = float(t3 - t2) / 1000.0

	# THE SCOUR is the machine's own footprint in the chamber floor, so the
	# chamber material is told where the machine is and how far it reaches.
	# The lethal contour is 9 cells; the scour is drawn at exactly that radius
	# and nowhere is a boundary drawn.
	mats.rock.set_shader_parameter("scour_c", machine.global_position)
	mats.rock.set_shader_parameter("scour_r", Assayer.LETHAL_R)
	mats.rock.set_shader_parameter("lobe_aim", deg_to_rad(machine.aim_deg - Assayer.AIM_STEP_DEG))
	mats.rock.set_shader_parameter("lobe_amt", 1.0)

	dog = Surveyor.new()
	dog.build(mats)
	# ART-DIRECTION 5.1's own scale check: "the dog stands to the top of the
	# footing hub". Put it where that comparison is visible: at the foot, off
	# the axis, outside the platform ring.
	# Bearing 84 deg at 3.3 m: outside the 2.04 m platform ring, at the foot,
	# and in frame from BOTH the elevation camera (bearing 131.5) and the
	# in-situ camera (bearing 36). It is 0.57 m standing against a 6.60 m mast
	# and it stands to the top of the footing hub, which is ART-DIRECTION 5.1's
	# own scale check and the only one this build can pass or fail on sight.
	dog.position = Vector3(1.17, 0, 3.61)
	dog.rotation.y = deg_to_rad(-110.0)
	world.add_child(dog)

	dog2 = Surveyor.new()
	dog2.build(mats)
	dog2.position = Vector3(2.70, 0, -4.68)
	# side-on to the camera and BACKLIT by the machine, which is ART-DIRECTION
	# 2.4's rule: the outline only carries information where it falls on
	# something lit, and the pose IS the information here.
	dog2.rotation.y = deg_to_rad(-30.0)
	dog2.download()
	world.add_child(dog2)

	cam = Camera3D.new()
	cam.fov = 42.0
	cam.near = 0.04
	cam.far = 90.0
	sub.add_child(cam)
	# TRAILER 8: the camera has a body and no shot passes through matter, so
	# every pose in _shot_list is a place a body could stand or a rig could
	# hang, and each one is asserted against the chamber below.
	camlamp = SpotLight3D.new()
	camlamp.light_color = Color(1.00, 0.98, 0.95)
	camlamp.light_energy = 5.4
	camlamp.spot_range = 26.0
	camlamp.spot_angle = 27.0
	camlamp.spot_angle_attenuation = 0.40
	camlamp.spot_attenuation = 2.0
	camlamp.shadow_enabled = true
	camlamp.shadow_bias = 0.020
	camlamp.shadow_normal_bias = 1.10
	camlamp.position = Vector3(0.26, -0.22, 0.10)
	camlamp.rotation_degrees = Vector3(-11.0, 0, 0)
	camlamp.visible = false
	cam.add_child(camlamp)

	hud = Label.new()
	hud.position = Vector2(14, 10)
	hud.add_theme_font_size_override("font_size", 15)
	hud.add_theme_color_override("font_color", Color(0.75, 0.78, 0.8))
	hud.add_theme_color_override("font_outline_color", Color(0, 0, 0))
	hud.add_theme_constant_override("outline_size", 5)
	hud.visible = cfg["run"]
	layer.add_child(hud)

	RenderingServer.viewport_set_measure_render_time(sub.get_viewport_rid(), true)
	cycle_t = float(cfg["p"])
	machine.set_phase(cycle_t)

	print("=== BLINDSIDE assayer spike ===")
	print("adapter          : %s" % RenderingServer.get_video_adapter_name())
	print("seed             : %d" % cfg["seed"])
	print("gen ms  materials: %.2f   chamber: %.2f   assayer: %.2f   total: %.2f" % [
		gen_ms_mat, gen_ms_room, gen_ms_mach, gen_ms_mat + gen_ms_room + gen_ms_mach])
	print("assayer triangles: %d" % machine.stat_tris)
	print("chamber triangles: %d  (incl. %d loose-rock instances)" % [room.stat_tris, 0])
	print("surveyor tris     : %d each" % dog.stat_tris)
	print("mast top         : %.2f m   boom at %.2f m   lethal contour %.2f m" % [
		Assayer.MAST_TOP, Assayer.SLEW_Y, Assayer.LETHAL_R])
	print("hammer travel    : %.2f m  (%.0f kJ at 1.6 t)" % [
		Assayer.HAMMER_TOP - Assayer.ANVIL_TOP,
		1600.0 * 9.81 * (Assayer.HAMMER_TOP - Assayer.ANVIL_TOP) / 1000.0])
	_stage("scene ready")

	if float(cfg["bias"]) > 0.0:
		for lt in [machine.winch_light]:
			lt.shadow_bias = float(cfg["bias"])
			lt.shadow_normal_bias = float(cfg["nbias"])
	if cfg["noshadow"]:
		machine.winch_light.shadow_enabled = false
	if String(cfg["shellshadow"]) == "off":
		room.shell_mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	if float(cfg["hot"]) > 0.0:
		machine.hot_energy = float(cfg["hot"])
		machine.set_phase(cycle_t)
	if cfg["shots"]:
		_do_shots()
	elif cfg["calib"]:
		_do_calib()
	elif cfg["dbg"]:
		_do_dbg()
	elif cfg["seq"]:
		_do_sequences()


# The energy sweep. ART-DIRECTION 2.2 is explicit that a wattage does not
# survive a change of renderer and that what is durable is the RATIO, so the
# number is found by rendering the same frame at several energies and reading
# ART-DIRECTION 2.9's bands off it, not by inheriting one from Blender.
func _do_calib() -> void:
	busy = true
	var dir: String = SHOT_DIR + "_calib/"
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(dir))
	for e in [30.0, 45.0, 65.0, 90.0, 125.0, 170.0]:
		machine.hot_energy = e
		_clear_rig(false)
		camlamp.visible = false
		dog2.visible = false
		machine.set_phase(70.4)
		cam.fov = 52.0
		cam.look_at_from_position(Vector3(6.90, 0.40, 5.05), Vector3(0.0, 2.70, 0.0), Vector3.UP)
		for k in range(10):
			await RenderingServer.frame_post_draw
		var img: Image = sub.get_texture().get_image()
		img.save_png(ProjectSettings.globalize_path(dir + "click9_e%04d.png" % int(e)))
		print("calib energy %6.0f" % e)
	busy = false
	if not cfg["stay"]:
		await get_tree().create_timer(0.3).timeout
		get_tree().quit()


func _do_dbg() -> void:
	busy = true
	var dir: String = SHOT_DIR + "_dbg/"
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(dir))
	var shots := []
	var n: int = room.drive_pts.size()
	for k in [10, 13, 16, 19, 22]:
		shots.append(["drive_i%02d" % k, room.drive_pts[k] + Vector3(0, 0.40, 0),
			room.drive_pts[maxi(0, k - 8)] + Vector3(0, 1.00, 0), 32.0, false])
	var fnrm := Vector3(cos(deg_to_rad(330.0)), 0, sin(deg_to_rad(330.0)))
	shots.append(["anvil_mark", Vector3(cos(deg_to_rad(8.0)) * 3.6, 0.95, sin(deg_to_rad(8.0)) * 3.6),
		fnrm * 0.80 + Vector3(0, 0.82, 0), 14.0, true])
	machine.set_phase(70.4)
	for sh in shots:
		_clear_rig(bool(sh[4]))
		camlamp.visible = false
		dog2.visible = false
		cam.fov = float(sh[3])
		cam.look_at_from_position(sh[1], sh[2], Vector3.UP)
		for k in range(10):
			await RenderingServer.frame_post_draw
		var img: Image = sub.get_texture().get_image()
		img.save_png(ProjectSettings.globalize_path(dir + String(sh[0]) + ".png"))
		print("dbg %-22s eye %s" % [sh[0], str((sh[1] as Vector3).snapped(Vector3(0.1, 0.1, 0.1)))])
	busy = false
	if not cfg["stay"]:
		await get_tree().create_timer(0.3).timeout
		get_tree().quit()


# ---------------------------------------------------------------------------
# THE LIGHT ECONOMY. ART-DIRECTION 2.1 lists four sources and this scene has
# two of them: the machinery, and the work lamp of whatever walks up to it.
# Ambient is DISABLED, the world background is black, and there is no fill, no
# rim, no bounce card and no sky term. If a pixel is lit, something in the
# frame is lighting it.
#
# --clear adds a studio key and a low grey world. That is the concept board's
# CLEAR rig and it is NOT THE GAME: it exists so a design can be read before
# its mood, and every frame it makes is named `clear_`.
# ---------------------------------------------------------------------------
func _environment() -> void:
	env = Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color(0, 0, 0)
	env.ambient_light_source = Environment.AMBIENT_SOURCE_DISABLED
	env.ambient_light_energy = 0.0
	env.tonemap_mode = Environment.TONE_MAPPER_AGX
	env.tonemap_exposure = 1.0
	env.tonemap_white = 6.0
	env.ssao_enabled = false
	# TRAILER 9: "real glare is tight and bright, not a soft haze over
	# everything. Threshold high. If bloom is visible on rock, it is too
	# strong." The winch head at 2400 K and the strike at 4000 K are the only
	# things in the scene that ever cross it.
	env.glow_enabled = true
	env.glow_intensity = 0.42
	env.glow_bloom = 0.03
	env.glow_hdr_threshold = 1.35
	env.glow_hdr_scale = 2.0
	env.glow_blend_mode = Environment.GLOW_BLEND_MODE_ADDITIVE
	# ART-DIRECTION 2.6: resting cave volume scatter 0.008-0.012, anisotropy
	# 0.55 (forward-scattering, like silt in water), colour (0.85,0.86,0.90) so
	# it does not blue-shift. The strike's glow in the air is THIS, not a bloom.
	env.volumetric_fog_enabled = true
	env.volumetric_fog_density = 0.0105
	env.volumetric_fog_anisotropy = 0.55
	env.volumetric_fog_albedo = Color(0.85, 0.86, 0.90)
	env.volumetric_fog_emission_energy = 0.0
	env.volumetric_fog_length = 44.0
	env.volumetric_fog_gi_inject = 0.0
	var we := WorldEnvironment.new()
	we.environment = env
	world.add_child(we)


func _clear_rig(on: bool) -> void:
	if on and clear_ground == null:
		# the studio floor. The chamber is HIDDEN under the CLEAR rig, not lit:
		# a concept-board elevation stands off at 15 m and a 10.5 m chamber has
		# no such place to stand. Refusing to fake it is the point of having two
		# rigs at all.
		var pl := PlaneMesh.new()
		pl.size = Vector2(70, 70)
		pl.subdivide_width = 2
		pl.subdivide_depth = 2
		var gm := ShaderMaterial.new()
		gm.shader = load("res://clear.gdshader")
		pl.material = gm
		clear_ground = MeshInstance3D.new()
		clear_ground.mesh = pl
		clear_ground.position = Vector3(0, -0.02, 0)
		clear_ground.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		world.add_child(clear_ground)
	if clear_ground:
		clear_ground.visible = on
	room.visible = not on
	# The hot points stay ON under the CLEAR rig -- the concept board's
	# `01_clear_click6` shows the mechanism lit, and a dark brake band hides
	# which part is the emitter -- but at a quarter output, because a 62-unit
	# source washes a studio floor red and then the rig is not describing form
	# any more, it is competing with it.
	if machine:
		machine.hot_scale = 0.26 if on else 1.0
		machine.set_phase(machine.last_p)
	if on and key == null:
		key = DirectionalLight3D.new()
		key.light_color = Color(1.0, 0.99, 0.97)
		key.light_energy = 2.35
		key.rotation_degrees = Vector3(-42.0, 128.0, 0)
		key.shadow_enabled = true
		key.directional_shadow_max_distance = 60.0
		world.add_child(key)
		fill = OmniLight3D.new()
		fill.light_color = Color(0.90, 0.92, 0.96)
		fill.light_energy = 3.2
		fill.omni_range = 40.0
		fill.omni_attenuation = 0.55
		fill.position = Vector3(-9.0, 7.0, -8.0)
		fill.shadow_enabled = false
		world.add_child(fill)
	if key:
		key.visible = on
		fill.visible = on
	if on:
		env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
		env.ambient_light_color = Color(0.42, 0.42, 0.44)
		env.ambient_light_energy = 0.26
		env.volumetric_fog_density = 0.0018
	else:
		env.ambient_light_source = Environment.AMBIENT_SOURCE_DISABLED
		env.ambient_light_energy = 0.0
		env.volumetric_fog_density = 0.0105


# ---------------------------------------------------------------------------
# THE STILLS
#
# Every pose is [name, phase, eye, target, fov, flags]. `flags` is a string:
#   C = the CLEAR rig      L = the visiting machine's work lamp on the camera
#   D = the download pose in frame
# The camera never passes through matter and never hovers: every eye below is
# either floor level (0.35), machine height (0.40), a person's eye (1.60), or
# a rig hung off the chamber wall, and each says which.
# ---------------------------------------------------------------------------
func _shot_list() -> Array:
	return [
		# --- the design read: the CLEAR rig, which is not the game ----------
		# The boom is on bearing 41.5 deg, so the elevation stands PERPENDICULAR
		# to it at 131.5 deg: a 4.2 m arm seen end-on is not an elevation.
		["01_clear_elevation", 66.0, Vector3(-9.93, 3.10, 11.22), Vector3(0.0, 3.30, 0), 36.0, "C"],
		["02_clear_three_quarter", 66.0, Vector3(-3.55, 2.40, 13.60), Vector3(0.0, 3.15, 0), 38.0, "C"],
		["03_clear_boom_axis", 66.0, Vector3(11.60, 3.30, 10.30), Vector3(0.0, 4.10, 0), 34.0, "C"],
		# outside the platform ring, on the bearing the K 14 face looks down,
		# with a long lens -- from inside the ring the deck is in the way
		["04_clear_footing_anvil", 66.0, Vector3(4.65, 0.98, 0.95), Vector3(0.55, 0.95, 0.05), 20.0, "C"],
		["05_clear_head_winch", 66.0, Vector3(4.75, 6.55, 3.45), Vector3(0.0, 5.90, 0.20), 44.0, "C"],
		["06_clear_tank_sightglass", 66.0, Vector3(4.30, 3.10, -2.55), Vector3(0.55, 3.00, -1.15), 38.0, "C"],
		["07_clear_hammer_at_rest", 40.0, Vector3(6.10, 3.55, 4.35), Vector3(0.0, 3.55, 0.0), 56.0, "C"],
		["08_clear_hammer_at_click9", 70.4, Vector3(6.10, 3.55, 4.35), Vector3(0.0, 3.55, 0.0), 56.0, "C"],
		["09_clear_plan", 66.0, Vector3(0.02, 17.5, 0.02), Vector3(0, 0, 0), 40.0, "C"],
		# --- the same machine in the game's own light, which is almost none --
		["10_insitu_dormant_lamp", 40.0, Vector3(6.90, 0.40, 5.05), Vector3(0.0, 1.15, 0.0), 52.0, "L"],
		["11_insitu_click1", 62.4, Vector3(6.90, 0.40, 5.05), Vector3(0.0, 2.70, 0.0), 52.0, ""],
		["12_insitu_click5", 66.4, Vector3(6.90, 0.40, 5.05), Vector3(0.0, 2.70, 0.0), 52.0, ""],
		["13_insitu_click9", 70.4, Vector3(6.90, 0.40, 5.05), Vector3(0.0, 2.70, 0.0), 52.0, ""],
		["14_insitu_strike", 71.06, Vector3(6.90, 0.40, 5.05), Vector3(0.0, 2.70, 0.0), 52.0, ""],
		["15_insitu_two_seconds_after", 73.15, Vector3(6.90, 0.40, 5.05), Vector3(0.0, 2.70, 0.0), 52.0, ""],
		["16_insitu_across_the_chamber", 69.6, Vector3(-7.70, 1.60, -4.55), Vector3(0.0, 2.90, 0.0), 34.0, ""],
		["17_insitu_from_the_passage", 69.6, Vector3.ZERO, Vector3.ZERO, 32.0, "P"],
		["18_insitu_download_pose", 67.4, Vector3(4.00, 0.32, -6.93), Vector3(2.70, 0.22, -4.68), 24.0, "D"],
		["19_clear_download_pose", 67.4, Vector3(3.85, 0.50, -6.70), Vector3(2.70, 0.22, -4.68), 26.0, "CD"],
		# the index mark, at the distance TRAILER 10 needs it legible from
		["20_insitu_index_mark_K14", 70.4, Vector3(5.544, 1.02, 0.779), Vector3(0.693, 0.82, -0.40), 9.0, ""],
		["21_insitu_wide_dormant", 20.0, Vector3(7.40, 1.60, 5.45), Vector3(0.0, 1.55, 0.0), 56.0, "L"],
	]


func _pose(shot: Array) -> Array:
	var eye: Vector3 = shot[2]
	var tgt: Vector3 = shot[3]
	if String(shot[5]).find("P") >= 0:
		# THE PASSAGE SHOT. Stand in the far leg of the drive, past the bend,
		# so the mast is behind solid rock and only its light comes round.
		# ART-DIRECTION 5.5: "vertical landmark presence is bought with light,
		# not with geometry, because light goes round corners and a mast does
		# not." The pose is derived from the drive's own centreline so it can
		# never drift into the wall.
		# THE PASSAGE FRAME, arrived at by sweeping six stations along the drive
		# and reading each against ART-DIRECTION 2.9 (10, 13, 16, 19, 22, 25 ->
		# 8.2%, 4.8%, 3.1%, 2.5%, 0.0%, 0.0% legible). Station 16 is 5.1 m in
		# and it is the one that is right for a reason rather than by taste:
		#
		#   ART-DIRECTION 5.5 says vertical landmark presence is bought with
		#   LIGHT, not geometry, "because light goes round corners and a mast
		#   does not". A renderer with no GI will not turn a corner for you, so
		#   the frame that proves the claim is not a corner at all -- it is the
		#   ARCH. From an eye at 0.40 m, 5.1 m inside a 2.40 m drive, the sight
		#   line through the top of the arch reaches 6.52 m at the machine, and
		#   the mast is 6.60 m: the top of the machine, the boom and the winch
		#   head are all behind solid rock, and what fills the mouth is the
		#   ground its own light is standing on.
		var n: int = room.drive_pts.size()
		eye = room.drive_pts[16] + Vector3(0, 0.40, 0)
		tgt = room.drive_pts[8] + Vector3(0, 1.00, 0)
	return [eye, tgt]


func _apply(shot: Array) -> void:
	var flags: String = shot[5]
	_clear_rig(flags.find("C") >= 0)
	camlamp.visible = flags.find("L") >= 0
	dog.visible = true
	dog2.visible = flags.find("D") >= 0
	machine.set_phase(float(shot[1]))
	var pose: Array = _pose(shot)
	cam.fov = float(shot[4])
	cam.look_at_from_position(pose[0], pose[1], Vector3.UP)


func _do_shots() -> void:
	busy = true
	for shot in _shot_list():
		_apply(shot)
		for k in range(10):
			await RenderingServer.frame_post_draw
		var img: Image = sub.get_texture().get_image()
		img.save_png(ProjectSettings.globalize_path(shot_dir + String(shot[0]) + ".png"))
		var dc: int = int(Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME))
		var pr: int = int(Performance.get_monitor(Performance.RENDER_TOTAL_PRIMITIVES_IN_FRAME))
		var gpu: float = RenderingServer.viewport_get_measured_render_time_gpu(sub.get_viewport_rid())
		print("shot %-30s p=%6.2f  draws %-5d tris %-8d gpu %.2f ms" % [
			shot[0], float(shot[1]), dc, pr, gpu])
		_stage("shot " + String(shot[0]))
	# the three clicks side by side, so the countdown is countable in one frame
	await _strip()
	busy = false
	if not cfg["stay"]:
		await get_tree().create_timer(0.3).timeout
		get_tree().quit()


# clicks 1 / 5 / 9 composited into one 1920x1080 frame. The concept board's
# `02_clear_clicks_strip`, made the same way: three renders, one PIL-equivalent
# paste. If the nine clicks are not countable HERE they are not countable.
func _strip() -> void:
	var out := Image.create(1920, 1080, false, Image.FORMAT_RGBA8)
	out.fill(Color(0, 0, 0, 1))
	var ps := [62.4, 66.4, 70.4]
	svc.stretch = false
	sub.size = Vector2i(640, 1080)
	for i in range(3):
		_clear_rig(false)
		camlamp.visible = false
		dog2.visible = false
		machine.set_phase(ps[i])
		cam.fov = 50.0
		# Bearing -22 degrees at 6.5 m. The tank stands on -Z, so a camera on
		# that bearing photographs the tank and hides the mast behind it --
		# which is exactly what the first strip did, and a countdown you cannot
		# see the hammer on is not a countdown. From here the mast is clear,
		# the hammer's bearing-steel top flange is the mark that moves, and the
		# tank's sight glass is still in frame as the second, slower clock.
		# and the eye is at 3.4 m -- a rig hung on the chamber wall, which
		# TRAILER 8 allows -- because the hammer's mark is a bearing-steel TOP
		# flange lit by a source 1.7 m above its top of travel, and from an eye
		# at 0.4 m that flange is edge-on for the whole nine seconds.
		cam.look_at_from_position(Vector3(6.03, 3.40, -2.44), Vector3(0.0, 3.15, -0.45), Vector3.UP)
		for k in range(10):
			await RenderingServer.frame_post_draw
		var img: Image = sub.get_texture().get_image()
		img.convert(Image.FORMAT_RGBA8)
		out.blit_rect(img, Rect2i(0, 0, 640, 1080), Vector2i(i * 640, 0))
	sub.size = Vector2i(1920, 1080)
	svc.stretch = true
	out.save_png(ProjectSettings.globalize_path(shot_dir + "17_clicks_1_5_9_strip.png"))
	print("shot %-30s  three renders composited" % "17_clicks_1_5_9_strip")


# ---------------------------------------------------------------------------
# THE THREE TRAILER SHOTS, as image sequences
#
# TRAILER 3, Act V:
#   23  1:36  3s  Something in the dark ahead, barely lit. A mast. Not moving.
#   24  1:39  4s  The boom slews. The hammer ratchets: nine clicks, the winch
#                 head getting hotter and brighter with each.
#   25  1:43  2s  The strike. One frame of the whole chamber, white.
#
# Shot 24 covers 54 s -> 71 s of a 75 s cycle in four seconds of screen time,
# so it is TWO shots in the cut and it is rendered as two here: the slew, and
# the wind. Saying that plainly is more use to an editor than pretending one
# continuous take exists.
#
# TRAILER 8 governs the moves: short and slow, eased in and out, never linear,
# a body-sized camera that never passes through matter. Every move below is a
# dolly of a metre or less on a cubic ease.
# ---------------------------------------------------------------------------
func _seq_list() -> Array:
	return [
		# name, p0, p1, frames, eye0, eye1, tgt0, tgt1, fov, flags
		# A dormant Assayer emits NOTHING, so the only thing that can find it is
		# the visitor's own beam, and a beam falls off with the square of the
		# distance: at 9 m the mast was under the legibility floor and the shot
		# was a lit patch of floor with a black object behind it. Closer (6.4 ->
		# 5.5 m) and aimed higher, because the lamp is a child of the camera and
		# pitches with it -- which is also what a machine walking up to a 6.6 m
		# object actually does with its head.
		["s23_mast_in_the_dark", 47.0, 50.4, 24,
			Vector3(5.20, 0.62, 3.80), Vector3(4.45, 0.62, 3.25),
			Vector3(0.0, 2.20, 0.0), Vector3(0.0, 2.60, 0.0), 46.0, "L"],
		# THE SLEW IS THE ONE BEAT WITH NO LIGHT OF ITS OWN. ART-DIRECTION 5.4:
		# "nothing. The arm moves; the bearing race is bright metal and catches
		# whatever is present." So the shot has to put the visitor's beam ON the
		# race, which means the camera looks UP at 5.40 m and the lamp -- being
		# a child of it -- follows. Aimed at 4.60 m instead, as this first was,
		# the race is outside the cone and the tell is invisible.
		["s24a_the_slew", 53.7, 57.3, 26,
			Vector3(4.95, 1.55, 3.65), Vector3(4.55, 1.55, 3.35),
			Vector3(0.0, 5.42, 0.0), Vector3(0.0, 5.42, 0.0), 44.0, "L"],
		["s24b_the_wind", 61.7, 71.02, 38,
			Vector3(6.60, 0.40, 4.85), Vector3(6.20, 0.40, 4.55),
			Vector3(0.0, 3.10, 0.0), Vector3(0.0, 3.30, 0.0), 50.0, ""],
		["s25_the_strike", 70.90, 73.10, 27,
			Vector3(6.20, 0.40, 4.55), Vector3(6.05, 0.40, 4.44),
			Vector3(0.0, 3.30, 0.0), Vector3(0.0, 3.20, 0.0), 50.0, ""],
	]


func _do_sequences() -> void:
	busy = true
	# the sequences are rendered at 1280x720: enough to judge motion, and a
	# hundred and fifteen 1080p PNGs is a quarter of a gigabyte of spike.
	svc.stretch = false
	sub.size = Vector2i(1280, 720)
	for s in _seq_list():
		var dir: String = SEQ_DIR + String(s[0]) + "/"
		DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(dir))
		var frames: int = int(s[3])
		_clear_rig(false)
		camlamp.visible = String(s[9]).find("L") >= 0
		dog2.visible = false
		for i in range(frames):
			var u: float = float(i) / float(maxi(1, frames - 1))
			var e: float = u * u * (3.0 - 2.0 * u)      # ease: the camera has mass
			machine.set_phase(lerp(float(s[1]), float(s[2]), u))
			cam.fov = float(s[8])
			cam.look_at_from_position((s[4] as Vector3).lerp(s[5], e),
				(s[6] as Vector3).lerp(s[7], e), Vector3.UP)
			for k in range(4):
				await RenderingServer.frame_post_draw
			var img: Image = sub.get_texture().get_image()
			img.save_png(ProjectSettings.globalize_path(dir + "%03d.png" % i))
		print("seq %-24s %d frames  p %.2f -> %.2f  at 1280x720" % [
			s[0], frames, float(s[1]), float(s[2])])
		_stage("seq " + String(s[0]))
	sub.size = Vector2i(1920, 1080)
	svc.stretch = true
	busy = false
	if not cfg["stay"]:
		await get_tree().create_timer(0.3).timeout
		get_tree().quit()


# ---------------------------------------------------------------------------
func _process(delta: float) -> void:
	if busy or not cfg["run"]:
		return
	var prev: float = cycle_t
	cycle_t += delta
	if cycle_t >= Assayer.PERIOD:
		cycle_t -= Assayer.PERIOD
		machine.advance_cycle()
		# the last firing's lobe follows the aim it fired on
		room.mats.rock.set_shader_parameter("lobe_aim", deg_to_rad(machine.last_fired_aim))
	machine.set_phase(cycle_t)
	# a slow orbit at machine height so the whole cycle can be watched
	var a: float = Time.get_ticks_msec() * 0.000045
	cam.look_at_from_position(Vector3(cos(a) * 8.4, 1.35, sin(a) * 8.4),
		Vector3(0, 3.0, 0), Vector3.UP)
	hud.text = "p %5.2f / 75  |  aim %5.1f deg  clicks %d/9  tank %3.0f%%  |  %.0f fps  gpu %.2f ms  draws %d tris %d" % [
		cycle_t, machine.aim_deg, machine.clicks_done, machine.tank_fill * 100.0,
		Performance.get_monitor(Performance.TIME_FPS),
		RenderingServer.viewport_get_measured_render_time_gpu(sub.get_viewport_rid()),
		int(Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME)),
		int(Performance.get_monitor(Performance.RENDER_TOTAL_PRIMITIVES_IN_FRAME))]
