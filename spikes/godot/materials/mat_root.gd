extends Node3D

const BSLibrary := preload("res://library.gd")
const BSForms := preload("res://forms.gd")

# ---------------------------------------------------------------------------
# BLINDSIDE -- procedural PBR material testbed.
#
# Four views:
#   library    every material in the library, each on four forms
#   calib      the physics, made checkable: albedo ramp, roughness sweep,
#              metallic pair, normal-scale sweep, and every material's albedo
#              measured against its claimed range
#   scalars    ART-DIRECTION 3.1's four rock scalars, five steps each
#   falloff    one lamp down a 25 m plane, for the 2.2 exposure ratios
#
# Three lighting conditions, and they are the only three this game has:
#   lamp       one work lamp in the dark, zero ambient of any kind
#   day        overcast daylight on the surface, sky-sourced (see NOTES.md)
#   machine    the ancients' plant, 1900-2400 K, zero ambient
# ---------------------------------------------------------------------------

const SHOT_DIR := "res://shots/"
const VIEWS := ["library", "calib", "sweeps", "scalars", "falloff"]
const LIGHTS := ["lamp", "day", "machine"]

# The three energies, and the exposure, are one knob each (ART-DIRECTION 2.2:
# "lamp power and camera exposure are the same knob"). They are set so that a
# 0.07-albedo floor three metres ahead lands near 0.08 linear luminance, which
# is the ratio the art direction fixes. `lum.py` measures it off the PNG.
const LAMP_ENERGY := 140.0
const MACH_ENERGY := 72.0
const DAY_SUN := 1.9
const DAY_AMBIENT := 0.55
const DAY_EXPOSURE := 0.95
# The framing distance the carried lamp is normalised to. Raising it lowers the
# irradiance on every framed shot by the square: 4.5 puts a 0.08-albedo floor
# near 0.09 linear, which is where ART 2.2 puts the floor three metres ahead.
const LAMP_REF_M := 4.8

var sub: SubViewport
var world: Node3D
var cam: Camera3D
var env: Environment
var wenv: WorldEnvironment
var hud: Label
var ui: Control

var view_root := {}          # view name -> Node3D
var light_root := {}         # light name -> Node3D
var mats := {}               # material id -> ShaderMaterial
var shaders := {}            # variant name -> Shader
var lib: Array = []
var calib_rects: Array = []
var tile_center := {}        # material id -> Vector3
var row_center := {}         # row index -> Vector3
var row_node := {}           # row index -> Node3D, so one row can be shot alone

var cfg := {
	"view": "library", "light": "lamp", "wet": 0.30,
	"shots": false, "cost": false, "ssr": false, "stay": false,
	"ambient_test": false, "pom": 1.0, "diag": false, "expo": false,
}
var adapter := ""
var frame_i := 0
# Mirror of the five global shader parameters. RenderingServer's getter returns
# null with no rendering device (headless), so the script never reads it back.
var gv := {"bs_wet": 0.35, "bs_debug": 0.0, "bs_pom_on": 1.0,
	"bs_normal_gain": 1.0, "bs_detail_gain": 1.0}
var report_lines: Array[String] = []


# --- Kelvin -> linear RGB ---------------------------------------------------
# ART-DIRECTION 2.1 states its light colours as sRGB triples. Godot uses
# `light_color` as a raw linear multiplier, so they must be linearised or a
# 2100 K lamp comes out at roughly 3200 K. This is the single most common way
# a warm light ends up looking wrong.
func kelvin(k: float) -> Color:
	var pts := [
		[1900.0, Color(1.00, 0.67, 0.34)],
		[2100.0, Color(1.00, 0.72, 0.42)],
		[2400.0, Color(1.00, 0.78, 0.52)],
		[4000.0, Color(1.00, 0.90, 0.78)],
		[6500.0, Color(1.00, 1.00, 1.00)],
		[12000.0, Color(0.60, 0.74, 1.00)],
	]
	var c: Color = pts[0][1]
	for i in range(pts.size() - 1):
		var a: float = pts[i][0]
		var b: float = pts[i + 1][0]
		if k >= a and k <= b:
			c = (pts[i][1] as Color).lerp(pts[i + 1][1] as Color, (k - a) / (b - a))
			break
		if k > b:
			c = pts[i + 1][1]
	return c.srgb_to_linear()


func _gset(n: String, v: float) -> void:
	gv[n] = v
	RenderingServer.global_shader_parameter_set(n, v)


func _parse_args() -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--view="): cfg["view"] = a.substr(7)
		elif a.begins_with("--light="): cfg["light"] = a.substr(8)
		elif a.begins_with("--wet="): cfg["wet"] = float(a.substr(6))
		elif a.begins_with("--pom="): cfg["pom"] = float(a.substr(6))
		elif a == "--shots": cfg["shots"] = true
		elif a == "--cost": cfg["cost"] = true
		elif a == "--diag": cfg["diag"] = true
		elif a == "--expo": cfg["expo"] = true
		elif a == "--ssr": cfg["ssr"] = true
		elif a == "--ambient-test": cfg["ambient_test"] = true
		elif a == "--stay": cfg["stay"] = true


# ---------------------------------------------------------------------------
func _ready() -> void:
	_parse_args()
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(SHOT_DIR))

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
	# NOTE: use_hdr_2d must stay OFF. With it on, get_texture().get_image()
	# returns the linear HDR buffer and save_png writes linear values into an
	# sRGB-tagged file, which reads three stops too dark in every viewer and in
	# every measurement script. Half an hour of "the lights are broken".
	sub.use_hdr_2d = false
	svc.add_child(sub)

	world = Node3D.new()
	sub.add_child(world)

	env = Environment.new()
	wenv = WorldEnvironment.new()
	wenv.environment = env
	world.add_child(wenv)

	cam = Camera3D.new()
	cam.fov = 42.0
	cam.near = 0.02
	cam.far = 120.0
	sub.add_child(cam)

	shaders["full"] = load("res://bs_surface.gdshader")
	shaders["lean"] = load("res://bs_surface_lean.gdshader")
	shaders["far"] = load("res://bs_surface_far.gdshader")
	shaders["water_shallow"] = load("res://bs_water_shallow.gdshader")
	shaders["water_deep"] = load("res://bs_water_deep.gdshader")
	shaders["calib"] = load("res://bs_calib.gdshader")

	lib = BSLibrary.materials()
	for m in lib:
		mats[m["id"]] = _make_material(m)

	_build_lights()
	_build_library()
	_build_calib()
	_build_sweeps()
	_build_scalars()
	_build_falloff()
	_build_ui(layer)

	_gset("bs_wet", cfg["wet"])
	_gset("bs_debug", 0.0)
	_gset("bs_pom_on", cfg["pom"])
	_gset("bs_normal_gain", 1.0)
	_gset("bs_detail_gain", 1.0)

	RenderingServer.viewport_set_measure_render_time(sub.get_viewport_rid(), true)
	adapter = RenderingServer.get_video_adapter_name()
	print("=== BLINDSIDE material testbed ===")
	print("adapter   : %s (%s)" % [adapter, RenderingServer.get_video_adapter_vendor()])
	print("engine    : %s" % str(Engine.get_version_info()["string"]))
	print("materials : %d" % lib.size())
	print("render    : %dx%d, %s" % [sub.size.x, sub.size.y,
		"Forward+" if ProjectSettings.get_setting("rendering/renderer/rendering_method") == "forward_plus" else "?"])

	_set_view(cfg["view"])
	_set_light(cfg["light"])

	if cfg["expo"]:
		call_deferred("_run_expo")
	elif cfg["diag"]:
		call_deferred("_run_diag")
	elif cfg["cost"]:
		call_deferred("_run_cost")
	elif cfg["shots"]:
		call_deferred("_run_shots")


# ---------------------------------------------------------------------------
func _make_material(m: Dictionary) -> ShaderMaterial:
	var sm := ShaderMaterial.new()
	sm.shader = shaders[m["shader"]]
	for k in (m["p"] as Dictionary):
		sm.set_shader_parameter(k, (m["p"] as Dictionary)[k])
	return sm


func _calib_mat(v: Color, ramp := false, srgb_steps := false, ticks := false) -> ShaderMaterial:
	var sm := ShaderMaterial.new()
	sm.shader = shaders["calib"]
	sm.set_shader_parameter("value_linear", Vector3(v.r, v.g, v.b))
	sm.set_shader_parameter("ramp", 1.0 if ramp else 0.0)
	sm.set_shader_parameter("ramp_srgb", 1.0 if srgb_steps else 0.0)
	sm.set_shader_parameter("ticks", 1.0 if ticks else 0.0)
	return sm


func _mi(mesh: Mesh, mat: Material, parent: Node3D, xform: Transform3D) -> MeshInstance3D:
	var n := MeshInstance3D.new()
	n.mesh = mesh
	n.material_override = mat
	n.transform = xform
	parent.add_child(n)
	return n


# mode 0: lying on the floor, read from above (the library)
# mode 1: upright, facing +Z (the charts)
# mode 2: upright and turned on its side, for a column caption
func _label(text: String, parent: Node3D, pos: Vector3, size := 0.030,
		col := Color(0.55, 0.56, 0.58), mode := 0) -> Label3D:
	var l := Label3D.new()
	l.text = text
	l.pixel_size = size / 40.0
	l.font_size = 40
	l.position = pos
	l.billboard = BaseMaterial3D.BILLBOARD_DISABLED
	if mode == 0:
		l.rotation_degrees = Vector3(-90, 0, 0)
	elif mode == 2:
		l.rotation_degrees = Vector3(0, 0, -90)   # reads downward
	else:
		l.rotation_degrees = Vector3.ZERO
	l.horizontal_alignment = HORIZONTAL_ALIGNMENT_LEFT
	l.modulate = col
	l.outline_size = 0
	l.no_depth_test = false
	l.double_sided = true
	parent.add_child(l)
	return l


# ---------------------------------------------------------------------------
# lighting
# ---------------------------------------------------------------------------
func _build_lights() -> void:
	# --- one lamp in the dark ------------------------------------------------
	# The lamp is carried. It is a child of the camera, tilted 10 degrees down
	# so the pool lands inside the frustum (ART-DIRECTION 2.1). Every frame in
	# this game is lit from where the viewer is standing, so a testbed whose
	# lamp is a fixture in the room is testing the wrong thing.
	var r := Node3D.new()
	cam.add_child(r)
	light_root["lamp"] = r
	var sl := SpotLight3D.new()
	sl.light_color = Color(1.00, 0.98, 0.95)     # white for every team, ART 2.5
	sl.light_energy = LAMP_ENERGY
	sl.spot_range = 26.0
	sl.spot_angle = 30.0                          # a 60 degree cone
	sl.spot_angle_attenuation = 0.45
	sl.spot_attenuation = 2.0        # true inverse square; a lamp is a lamp
	sl.shadow_enabled = true
	sl.shadow_bias = 0.010
	sl.shadow_normal_bias = 0.8
	sl.shadow_blur = 1.0
	sl.light_specular = 1.0
	sl.position = Vector3(0.12, -0.15, 0.0)
	sl.rotation_degrees = Vector3(-10.0, 0.0, 0.0)
	r.add_child(sl)

	# --- overcast daylight ---------------------------------------------------
	r = Node3D.new()
	world.add_child(r)
	light_root["day"] = r
	var dl := DirectionalLight3D.new()
	dl.light_color = Color(1.0, 0.99, 0.97)
	dl.light_energy = DAY_SUN
	dl.shadow_enabled = true
	dl.shadow_bias = 0.03
	dl.shadow_normal_bias = 1.2
	dl.directional_shadow_max_distance = 40.0
	dl.rotation_degrees = Vector3(-52, 38, 0)
	r.add_child(dl)

	# --- the machinery, 1900-2400 K -----------------------------------------
	# Three fittings of the ancients' plant. Parented to the camera as well --
	# in the game they stand in the world, but a testbed has to put them where
	# the subject is, and what is being tested is the colour and the direction,
	# not where the plant happens to be.
	r = Node3D.new()
	cam.add_child(r)
	light_root["machine"] = r
	var spec := [
		[Vector3(-1.9, 0.15, -0.6), 1900.0, MACH_ENERGY * 1.00, 7.0],
		[Vector3(2.1, 0.45, -1.2), 2400.0, MACH_ENERGY * 0.72, 8.0],
		[Vector3(0.2, -0.35, -2.6), 2100.0, MACH_ENERGY * 0.45, 6.0],
	]
	for s2 in spec:
		var ol := OmniLight3D.new()
		ol.position = s2[0]
		ol.light_color = kelvin(s2[1])
		ol.light_energy = s2[2]
		ol.set_meta("base_energy", s2[2])
		ol.omni_range = s2[3]
		ol.omni_attenuation = 2.0
		ol.shadow_enabled = true
		ol.shadow_bias = 0.020
		ol.shadow_normal_bias = 0.8
		ol.light_specular = 1.0
		r.add_child(ol)


func _sky(overcast: bool) -> Sky:
	var psm := ProceduralSkyMaterial.new()
	psm.sky_top_color = Color(0.52, 0.55, 0.60) if overcast else Color(0.24, 0.40, 0.72)
	psm.sky_horizon_color = Color(0.62, 0.63, 0.65)
	psm.ground_bottom_color = Color(0.10, 0.10, 0.10)
	psm.ground_horizon_color = Color(0.28, 0.27, 0.25)
	psm.sun_angle_max = 60.0
	psm.sun_curve = 0.2
	psm.energy_multiplier = 0.85
	var s := Sky.new()
	s.sky_material = psm
	s.radiance_size = Sky.RADIANCE_SIZE_128
	return s


func _set_light(name: String) -> void:
	cfg["light"] = name
	for k in light_root:
		(light_root[k] as Node3D).visible = (k == name)
		for c in (light_root[k] as Node3D).get_children():
			if c is Light3D:
				(c as Light3D).visible = (k == name)

	env.ssr_enabled = cfg["ssr"]
	env.ssr_max_steps = 48
	env.ssr_fade_in = 0.1
	env.ssr_fade_out = 6.0
	env.ssao_enabled = false        # with no ambient it has nothing to occlude
	env.ssil_enabled = false
	# Glow is a lens artefact, not a lighting term. At 0.28 with a 1.5 threshold
	# every sample in the library grew a halo and the whole frame went milky.
	env.glow_enabled = true
	env.glow_intensity = 0.15
	env.glow_bloom = 0.0
	env.glow_hdr_threshold = 2.4
	env.tonemap_mode = Environment.TONE_MAPPER_AGX
	env.tonemap_white = 6.0

	if name == "day":
		# The surface. A sky is a real, visible source that is in the frame, so
		# sky-sourced ambient is not the "light arriving from infinity through
		# solid rock" that ART 9 forbids. See NOTES.md, "Rules bent".
		env.background_mode = Environment.BG_SKY
		env.sky = _sky(true)
		env.ambient_light_source = (Environment.AMBIENT_SOURCE_DISABLED
			if cfg["ambient_test"] else Environment.AMBIENT_SOURCE_SKY)
		env.ambient_light_energy = DAY_AMBIENT
		env.ambient_light_sky_contribution = 1.0
		env.background_energy_multiplier = 1.0
		env.tonemap_exposure = DAY_EXPOSURE
	else:
		env.background_mode = Environment.BG_COLOR
		env.background_color = Color(0, 0, 0)
		env.ambient_light_source = Environment.AMBIENT_SOURCE_DISABLED
		env.ambient_light_energy = 0.0
		env.tonemap_exposure = 1.0


# ---------------------------------------------------------------------------
# the library view
# ---------------------------------------------------------------------------
func _build_library() -> void:
	var root := Node3D.new()
	world.add_child(root)
	view_root["library"] = root

	var rows: Array = []
	for i in range(BSLibrary.ROWS.size()):
		rows.append([])
	for m in lib:
		(rows[m["row"]] as Array).append(m)

	# The tile is 1.5 x 1.3 m and the base slabs abut, so the library reads as
	# one continuous floor of samples rather than as objects hovering over a
	# black void -- which is itself a photoreal failure, and the thing a grid
	# of swatches is most likely to look like.
	var tile_w := 1.50
	var row_d := 1.30
	var mesh_box := BSForms.bevel_box(Vector3(0.30, 0.30, 0.30), 0.028, 24)
	var mesh_lump: Array = []
	for si in range(6):
		mesh_lump.append(BSForms.lump(0.155, 1000 + si * 7, 26))
	var mesh_graze := BSForms.plane(0.80, 0.46, 48)
	var mesh_base := BSForms.plane(tile_w, row_d, 64)

	for r in range(rows.size()):
		var row: Array = rows[r]
		var z := (float(r) - (rows.size() - 1) * 0.5) * row_d
		var rn := Node3D.new()
		root.add_child(rn)
		row_node[r] = rn
		row_center[r] = Vector3(0, 0, z)
		for c in range(row.size()):
			var m: Dictionary = row[c]
			var x := (float(c) - (row.size() - 1) * 0.5) * tile_w
			var t := Node3D.new()
			t.position = Vector3(x, 0, z)
			rn.add_child(t)
			tile_center[m["id"]] = Vector3(x, 0, z)
			var mat: ShaderMaterial = mats[m["id"]]

			if (m["shader"] as String).begins_with("water"):
				# Water over a bed of damp silt, with a block of tide-mark crust
				# standing proud of it. Water over saturated mud in the dark is
				# not a material test -- it is a black mirror with nothing to
				# reflect, and it is the finding in NOTES.md section 7.1 rather
				# than a useful sample. The crust gives it something lit.
				var bed: ShaderMaterial = mats["silt_damp"]
				_mi(mesh_base, bed, t, Transform3D(Basis(), Vector3(0, -0.055, 0)))
				_mi(BSForms.lump(0.17, 4000 + c, 24), mats["rock_tidemark"], t,
					Transform3D(Basis(), Vector3(0.36, 0.02, -0.20)))
				_mi(mesh_box, mats["rock_tidemark"], t,
					Transform3D(Basis(), Vector3(-0.44, 0.10, -0.22)))
				_mi(BSForms.plane(tile_w - 0.02, row_d - 0.02, 8), mat, t, Transform3D())
			else:
				_mi(mesh_base, mat, t, Transform3D())
				_mi(mesh_box, mat, t, Transform3D(Basis(), Vector3(-0.44, 0.150, 0.06)))
				_mi(mesh_lump[c % 6], mat, t, Transform3D(Basis(), Vector3(0.03, 0.120, -0.20)))
				# the grazing panel: a vertical plane yawed 74 degrees off the
				# camera, so the camera reads it at ~74 degrees of incidence,
				# which is where a roughness lie is loudest
				var b := Basis(Vector3.UP, deg_to_rad(74.0)) * Basis(Vector3.RIGHT, deg_to_rad(90.0))
				_mi(mesh_graze, mat, t, Transform3D(b, Vector3(0.50, 0.235, 0.12)))

			_label(str(m["label"]), t, Vector3(0.0, 0.004, 0.50), 0.030)


func _show_rows(only: int) -> void:
	for k in row_node:
		(row_node[k] as Node3D).visible = (only < 0 or int(k) == only)


# ---------------------------------------------------------------------------
# the calibration view: the physics, made checkable rather than admired
#
# Two frames, because they need opposite render settings and mixing them is how
# a calibration chart ends up lying:
#
#   calib    the albedo chart. Orthographic, tone mapper LINEAR at exposure
#            1.0, every material emitting its own ALBEDO unlit, so the value in
#            the PNG IS the number. A linear ramp above it with the claimed
#            range of every material ticked onto it, so the chart can be read
#            by eye, and `shots/calib_rects.json` so it can be read by a script.
#   sweeps   roughness 0..1, metallic 0/1, and normal+parallax scale 0..1, lit
#            by the one lamp, because those three can only be judged lit.
# ---------------------------------------------------------------------------
func _build_calib() -> void:
	var root := Node3D.new()
	world.add_child(root)
	view_root["calib"] = root

	var quad := BSForms.plane(1.0, 1.0, 2)
	var flat := Basis(Vector3.RIGHT, deg_to_rad(90.0))       # a plane facing +Z
	var n := lib.size()
	var x0 := -4.60
	var x1 := 4.60
	var w := (x1 - x0) / float(n)

	# the linear ramp, 0..1, ticked every 0.1
	_mi(quad, _calib_mat(Color.WHITE, true, false, true), root,
		Transform3D(flat.scaled(Vector3(x1 - x0, 0.40, 1.0)), Vector3(0.0, 2.55, 0.0)))
	_label("linear reflectance 0.0 -> 1.0, tick every 0.1.  orange = each"
		+ " material's claimed minimum, green = its maximum", root,
		Vector3(x0, 2.86, 0.0), 0.115, Color(0.62, 0.63, 0.65), 1)

	# the claimed range of every material, ticked onto the ramp
	for i in range(n):
		var m: Dictionary = lib[i]
		var lo: float = m["range"][0]
		var hi: float = m["range"][1]
		_mi(quad, _calib_mat(Color(0.95, 0.32, 0.05)), root,
			Transform3D(flat.scaled(Vector3(0.012, 0.30, 1.0)),
				Vector3(x0 + (x1 - x0) * lo, 2.55, 0.004)))
		_mi(quad, _calib_mat(Color(0.10, 0.85, 0.40)), root,
			Transform3D(flat.scaled(Vector3(0.012, 0.30, 1.0)),
				Vector3(x0 + (x1 - x0) * hi, 2.55, 0.004)))

	# every material's albedo, unlit, in the same units as the ramp
	calib_rects.clear()
	for i in range(n):
		var m: Dictionary = lib[i]
		var cx := x0 + w * (float(i) + 0.5)
		var mi := _mi(quad, mats[m["id"]], root,
			Transform3D(flat.scaled(Vector3(w * 0.94, 1.55, 1.0)), Vector3(cx, 1.36, 0.0)))
		mi.name = "swatch_" + str(m["id"])
		_label(str(m["id"]), root, Vector3(cx + w * 0.18, 0.66, 0.01), 0.085,
			Color(0.52, 0.53, 0.55), 2)
		calib_rects.append({
			"id": m["id"],
			"lo": m["range"][0], "hi": m["range"][1],
			"a": Vector3(cx - w * 0.36, 1.36 - 0.62, 0.0),
			"b": Vector3(cx + w * 0.36, 1.36 + 0.62, 0.0),
		})
	_label("every material, ALBEDO only, unlit, linear -- the same scale as the"
		+ " ramp above.  measured back by calib.py", root,
		Vector3(x0, 2.06, 0.0), 0.115, Color(0.62, 0.63, 0.65), 1)


func _build_sweeps() -> void:
	var root := Node3D.new()
	world.add_child(root)
	view_root["sweeps"] = root

	var sph := BSForms.sphere(0.21, 30)
	var flat_src := {}
	for e in lib:
		if e["id"] == "rock_weathered":
			flat_src = e["p"]

	# roughness 0 -> 1 at a fixed albedo
	for i in range(11):
		var sm := ShaderMaterial.new()
		sm.shader = shaders["far"]
		sm.set_shader_parameter("alb_lo", Vector3(0.18, 0.18, 0.18))
		sm.set_shader_parameter("alb_hi", Vector3(0.18, 0.18, 0.18))
		sm.set_shader_parameter("rough_lo", float(i) / 10.0)
		sm.set_shader_parameter("rough_hi", float(i) / 10.0)
		sm.set_shader_parameter("rough_micro", 0.0)
		sm.set_shader_parameter("form_amp", 0.0)
		sm.set_shader_parameter("detail_amp", 0.0)
		sm.set_shader_parameter("micro_amp", 0.0)
		sm.set_shader_parameter("macro_var", 0.0)
		sm.set_shader_parameter("stain_amt", 0.0)
		sm.set_shader_parameter("wet_gain", 0.0)
		_mi(sph, sm, root, Transform3D(Basis(), Vector3(-2.50 + 0.50 * i, 1.62, 0.0)))
	_label("roughness 0.00 -> 1.00   albedo 0.18   metallic 0", root,
		Vector3(-2.95, 1.24, 0.0), 0.10, Color(0.55, 0.56, 0.58), 1)

	# metallic 0 and 1, three roughnesses each
	for i in range(6):
		var sm := ShaderMaterial.new()
		sm.shader = shaders["far"]
		var met := 1.0 if i >= 3 else 0.0
		var a := Vector3(0.56, 0.565, 0.57) if met > 0.5 else Vector3(0.18, 0.18, 0.18)
		sm.set_shader_parameter("alb_lo", a)
		sm.set_shader_parameter("alb_hi", a)
		sm.set_shader_parameter("metallic", met)
		sm.set_shader_parameter("rough_lo", 0.12 + 0.24 * float(i % 3))
		sm.set_shader_parameter("rough_hi", 0.12 + 0.24 * float(i % 3))
		sm.set_shader_parameter("rough_micro", 0.0)
		sm.set_shader_parameter("form_amp", 0.0)
		sm.set_shader_parameter("detail_amp", 0.0)
		sm.set_shader_parameter("micro_amp", 0.0)
		sm.set_shader_parameter("macro_var", 0.0)
		sm.set_shader_parameter("stain_amt", 0.0)
		sm.set_shader_parameter("wet_gain", 0.0)
		var xo := 0.50 if i >= 3 else 0.0
		_mi(sph, sm, root, Transform3D(Basis(), Vector3(-2.50 + 0.50 * i + xo, 0.86, 0.0)))
	_label("metallic 0, albedo 0.18        |        metallic 1, F0 0.56 (iron)",
		root, Vector3(-2.95, 0.48, 0.0), 0.10, Color(0.55, 0.56, 0.58), 1)

	# normal + parallax scale 0 -> 1 on one material
	var box := BSForms.bevel_box(Vector3(0.44, 0.30, 0.44), 0.030, 28)
	for i in range(6):
		var sm := ShaderMaterial.new()
		sm.shader = shaders["lean"]
		for k in flat_src:
			sm.set_shader_parameter(k, flat_src[k])
		var f := float(i) / 5.0
		sm.set_shader_parameter("form_amp", 0.018 * f)
		sm.set_shader_parameter("detail_amp", 0.0072 * f)
		sm.set_shader_parameter("micro_amp", 0.0005 * f)
		sm.set_shader_parameter("voro_amp", 0.012 * f)
		sm.set_shader_parameter("pom_depth", 0.022 * f)
		sm.set_shader_parameter("wet_gain", 0.0)
		sm.set_shader_parameter("wet_bias", 0.18)
		_mi(box, sm, root, Transform3D(Basis(), Vector3(-2.45 + 0.98 * i, 0.10, 0.0)))
	_label("normal + parallax scale 0.0 -> 1.0 on one material", root,
		Vector3(-2.95, -0.16, 0.0), 0.10, Color(0.55, 0.56, 0.58), 1)


# ---------------------------------------------------------------------------
# ART-DIRECTION 3.1's four scalars, five steps each
# ---------------------------------------------------------------------------
func _build_scalars() -> void:
	var root := Node3D.new()
	world.add_child(root)
	view_root["scalars"] = root
	var names := ["wet 0 -> 1", "fracture 3 -> 14", "bedding 0.4 -> 3.5", "worked 0 -> 1"]
	var box := BSForms.bevel_box(Vector3(0.44, 0.44, 0.44), 0.04, 26)
	var slab := BSForms.plane(0.56, 0.56, 34)
	for r in range(4):
		for c in range(5):
			var f := float(c) / 4.0
			var p: Dictionary
			if r == 0: p = BSLibrary.rock_from_scalars(f, 8.0, 1.6, 0.3)
			elif r == 1: p = BSLibrary.rock_from_scalars(0.35, lerpf(3.0, 14.0, f), 1.6, 0.3)
			elif r == 2: p = BSLibrary.rock_from_scalars(0.35, 8.0, lerpf(0.4, 3.5, f), 0.3)
			else: p = BSLibrary.rock_from_scalars(0.35, 8.0, 1.6, f)
			var sm := ShaderMaterial.new()
			sm.shader = shaders["lean"]
			for k in p:
				sm.set_shader_parameter(k, p[k])
			sm.set_shader_parameter("wet_gain", 0.0)
			var pos := Vector3(-1.5 + 0.75 * c, 0.0, -0.9 + 0.66 * r)
			_mi(slab, sm, root, Transform3D(Basis(), pos))
			_mi(box, sm, root, Transform3D(Basis(), pos + Vector3(0, 0.22, 0)))
		_label(names[r], root, Vector3(-2.35, 0.004, -0.9 + 0.66 * r), 0.055)


# ---------------------------------------------------------------------------
# the falloff strip: ART-DIRECTION 2.2's ratios, measurable
# ---------------------------------------------------------------------------
func _build_falloff() -> void:
	var root := Node3D.new()
	world.add_child(root)
	view_root["falloff"] = root
	var strip := BSForms.plane(3.2, 30.0, 220)
	_mi(strip, mats["aggregate"], root, Transform3D(Basis(), Vector3(0, 0, -14.0)))
	# a wall down one side, facing the passage: +Y of the plane rotated to -X
	var wall := BSForms.plane(3.0, 30.0, 200)
	var b := Basis(Vector3(0, 0, 1), deg_to_rad(90.0))
	_mi(wall, mats["rock_wet"], root, Transform3D(b, Vector3(1.55, 1.5, -14.0)))
	for d in [1.6, 3.0, 8.0, 25.0]:
		_label("%.1f m" % d, root, Vector3(-1.35, 0.006, -d), 0.10, Color(0.30, 0.30, 0.31))


# ---------------------------------------------------------------------------
func _pose_for(view: String, light: String) -> Array:
	match view:
		"library":
			return [Vector3(0.0, 2.55, 4.35), Vector3(0.0, 0.05, -0.30)]
		"calib":
			return [Vector3(0.0, 1.60, 6.0), Vector3(0.0, 1.60, 0.0)]
		"sweeps":
			return [Vector3(0.0, 1.05, 5.3), Vector3(0.0, 0.85, 0.0)]
		"scalars":
			return [Vector3(0.0, 1.55, 2.05), Vector3(0.0, 0.05, -0.10)]
		"falloff":
			return [Vector3(0.0, 0.62, 0.6), Vector3(0.0, 0.30, -12.0)]
		_:
			pass
	return [Vector3(0, 2, 4), Vector3.ZERO]


func _set_view(v: String) -> void:
	cfg["view"] = v
	for k in view_root:
		(view_root[k] as Node3D).visible = (k == v)
	var p := _pose_for(v, cfg["light"])
	cam.fov = 42.0
	# The chart is orthographic. A chart in perspective is a chart whose
	# swatches are different sizes, and the one on the end is the one you were
	# supposed to be able to trust.
	cam.projection = (Camera3D.PROJECTION_ORTHOGONAL if v == "calib"
		else Camera3D.PROJECTION_PERSPECTIVE)
	# the chart is 9.2 m wide; 5.6 m of vertical ortho on 16:9 is 9.95 m across
	cam.size = 5.6 if v == "calib" else 3.6
	cam.position = p[0]
	cam.look_at(p[1], Vector3.UP)
	if cfg["light"] != "day":
		env.tonemap_exposure = 1.0
		# every view is lit as though the lamp were LAMP_REF_M away, except the
		# falloff strip, which is the one that measures the real ratios
		var dd: float = (p[0] as Vector3).distance_to(p[1] as Vector3)
		if v == "sweeps":
			_scale_lights(0.16)
		elif v == "falloff" or v == "calib":
			_scale_lights(1.0)
		else:
			_scale_lights(clampf(pow(dd / LAMP_REF_M, 2.0), 0.05, 40.0))
	if v == "library":
		env.tonemap_exposure = clampf(pow(p[0].distance_to(p[1]) / 3.0, 2.0), 0.05, 30.0)
		if cfg["light"] == "day":
			env.tonemap_exposure = DAY_EXPOSURE
	if v == "scalars":
		env.tonemap_exposure = clampf(pow(p[0].distance_to(p[1]) / 3.0, 2.0), 0.05, 30.0)
		if cfg["light"] == "day":
			env.tonemap_exposure = DAY_EXPOSURE
	if v == "calib":
		# The chart must not be tone mapped, or the numbers on it are not the
		# numbers in the material. LINEAR at exposure 1.0, glow off, and the
		# family switched to emitting its own ALBEDO with no lighting at all.
		env.tonemap_mode = Environment.TONE_MAPPER_LINEAR
		env.tonemap_exposure = 1.0
		env.glow_enabled = false
		_gset("bs_debug", 1.0)
	else:
		if gv["bs_debug"] == 1.0 and cfg["view"] != "calib":
			pass
		env.tonemap_mode = Environment.TONE_MAPPER_AGX
		env.glow_enabled = true
		env.tonemap_exposure = DAY_EXPOSURE if cfg["light"] == "day" else 1.0


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------
func _build_ui(layer: CanvasLayer) -> void:
	ui = Control.new()
	ui.set_anchors_preset(Control.PRESET_FULL_RECT)
	ui.mouse_filter = Control.MOUSE_FILTER_IGNORE
	layer.add_child(ui)

	var panel := VBoxContainer.new()
	panel.position = Vector2(14, 10)
	panel.custom_minimum_size = Vector2(320, 0)
	ui.add_child(panel)

	hud = Label.new()
	hud.add_theme_font_size_override("font_size", 14)
	hud.add_theme_color_override("font_color", Color(0.80, 0.82, 0.84))
	hud.add_theme_color_override("font_outline_color", Color(0, 0, 0))
	hud.add_theme_constant_override("outline_size", 5)
	panel.add_child(hud)

	var slider := HSlider.new()
	slider.min_value = 0.0
	slider.max_value = 1.0
	slider.step = 0.01
	slider.value = cfg["wet"]
	slider.custom_minimum_size = Vector2(300, 20)
	slider.value_changed.connect(func(v):
		cfg["wet"] = v
		_gset("bs_wet", v))
	panel.add_child(slider)

	var help := Label.new()
	help.add_theme_font_size_override("font_size", 12)
	help.add_theme_color_override("font_color", Color(0.55, 0.57, 0.60))
	help.add_theme_color_override("font_outline_color", Color(0, 0, 0))
	help.add_theme_constant_override("outline_size", 4)
	help.text = ("1/2/3 light   Q/W/E/R view   [ ] wetness   D debug   P parallax\n"
		+ "N normals   M detail bands   S screen-space reflection   F1 shots")
	panel.add_child(help)


func _unhandled_input(e: InputEvent) -> void:
	if not (e is InputEventKey) or not (e as InputEventKey).pressed:
		return
	var k := (e as InputEventKey).keycode
	if k == KEY_1: _set_light("lamp")
	elif k == KEY_2: _set_light("day")
	elif k == KEY_3: _set_light("machine")
	elif k == KEY_Q: _set_view("library")
	elif k == KEY_W: _set_view("calib")
	elif k == KEY_E: _set_view("scalars")
	elif k == KEY_R: _set_view("falloff")
	elif k == KEY_T: _set_view("sweeps")
	elif k == KEY_BRACKETLEFT:
		cfg["wet"] = maxf(0.0, cfg["wet"] - 0.1)
		_gset("bs_wet", cfg["wet"])
	elif k == KEY_BRACKETRIGHT:
		cfg["wet"] = minf(1.0, cfg["wet"] + 0.1)
		_gset("bs_wet", cfg["wet"])
	elif k == KEY_D:
		_gset("bs_debug", fmod(gv["bs_debug"] + 1.0, 7.0))
	elif k == KEY_P:
		_gset("bs_pom_on", 0.0 if gv["bs_pom_on"] > 0.5 else 1.0)
	elif k == KEY_N:
		_gset("bs_normal_gain", 0.0 if gv["bs_normal_gain"] > 0.5 else 1.0)
	elif k == KEY_M:
		_gset("bs_detail_gain", 0.0 if gv["bs_detail_gain"] > 0.5 else 1.0)
	elif k == KEY_S:
		cfg["ssr"] = not cfg["ssr"]
		_set_light(cfg["light"])
	elif k == KEY_F1:
		call_deferred("_run_shots")
	elif k == KEY_ESCAPE:
		get_tree().quit()


func _process(_dt: float) -> void:
	frame_i += 1
	if hud:
		var gpu: float = RenderingServer.viewport_get_measured_render_time_gpu(sub.get_viewport_rid())
		hud.text = "%s / %s   wet %.2f   gpu %.2f ms   %d fps   debug %d   ssr %s" % [
			cfg["view"], cfg["light"], cfg["wet"], gpu,
			Engine.get_frames_per_second(), int(gv["bs_debug"]), str(cfg["ssr"])]


# ---------------------------------------------------------------------------
# screenshots
# ---------------------------------------------------------------------------
# An auto-exposure meter. It exists, and it is deliberately NOT used for any
# shot in `shots/`, because it destroys the one thing the library is for: if
# every frame is metered to the same mid-grey then rubber at albedo 0.012 and
# concrete at 0.26 come out the same value and the chart is a lie. Every shot
# is taken at exposure 1.0 with the lamp scaled to the framing instead, so a
# dark material looks dark. Kept for interactive use.
func _meter(target := 0.20) -> void:
	for it in range(3):
		for i in range(3):
			await RenderingServer.frame_post_draw
		var img: Image = sub.get_texture().get_image()
		var vals: Array[float] = []
		for y in range(0, img.get_height(), 11):
			for x in range(0, img.get_width(), 11):
				var c := img.get_pixel(x, y).srgb_to_linear()
				vals.append(0.2126 * c.r + 0.7152 * c.g + 0.0722 * c.b)
		vals.sort()
		var p90: float = vals[int(float(vals.size()) * 0.90)]
		if p90 < 1e-5:
			env.tonemap_exposure = clampf(env.tonemap_exposure * 4.0, 0.02, 400.0)
			continue
		env.tonemap_exposure = clampf(
			env.tonemap_exposure * clampf(pow(target / p90, 1.4), 0.2, 5.0), 0.02, 400.0)


func _shot(name: String) -> void:
	for i in range(6):
		await RenderingServer.frame_post_draw
	var img: Image = sub.get_texture().get_image()
	var path := SHOT_DIR + name + ".png"
	img.save_png(ProjectSettings.globalize_path(path))
	var gpu: float = RenderingServer.viewport_get_measured_render_time_gpu(sub.get_viewport_rid())
	print("shot %-36s gpu %6.2f ms  exposure %5.2f  fov %4.1f" % [
		name, gpu, env.tonemap_exposure, cam.fov])


# Framing and exposure are one decision, and this is where the testbed departs
# from a game frame on purpose. A carried lamp is inverse-square, so a subject
# at 5 m is 2.8 stops darker than the same subject at 3 m. A game frame is
# supposed to show that (ART 2.3: do not compress the ramp). A material testbed
# is not: it has to put the subject at the same place on the curve every time
# or the shots are a picture of the framing rather than of the material.
#
# So every framed shot is exposed as though the lamp were always three metres
# away -- exposure = (distance / 3)^2 -- and the compensation is printed with
# the shot. The two views that keep exposure at 1.0 and carry the physics are
# `falloff` (the ART 2.2 ratios) and `calib` (linear, untone-mapped).
func _look(pos: Vector3, at: Vector3, fov := 42.0, auto_expose := true) -> void:
	cam.fov = fov
	cam.position = pos
	cam.look_at(at, Vector3.UP)
	if auto_expose and cfg["light"] != "day":
		# The lamp scales with the framing rather than the exposure doing all
		# the work: a wide row is shot with a bigger lamp, the way a studio
		# lights a bigger subject. ART 2.2 says lamp power and exposure are the
		# same knob, and this is the half of that knob that keeps AgX inside
		# the range it was designed for -- metering a 400x exposure instead
		# pushes everything onto the toe and the image goes to milk.
		var d := pos.distance_to(at)
		var k := clampf(pow(d / LAMP_REF_M, 2.0), 0.25, 40.0)
		_scale_lights(k)
		env.tonemap_exposure = 1.0
	elif cfg["light"] != "day":
		_scale_lights(1.0)
		env.tonemap_exposure = 1.0


func _scale_lights(k: float) -> void:
	for kk in light_root:
		for c in (light_root[kk] as Node3D).get_children():
			if c is SpotLight3D:
				(c as SpotLight3D).light_energy = LAMP_ENERGY * k
			elif c is OmniLight3D:
				(c as OmniLight3D).light_energy = float(c.get_meta("base_energy", 1.0)) * k


# Frame a group of samples from a real working distance. Four at a time keeps
# the camera near 3 m, which is the range ART 2.2 denominates its ratios at and
# the range a machine actually stands at.
func _group_shot(ids: Array) -> Array:
	var cx := 0.0
	var cz := 0.0
	for id in ids:
		cx += (tile_center[id] as Vector3).x
		cz += (tile_center[id] as Vector3).z
	cx /= float(ids.size())
	cz /= float(ids.size())
	var half := float(ids.size()) * 1.50 * 0.5 + 0.06
	var d: float = maxf(half / 0.754, 2.2)
	return [Vector3(cx, 0.34 + d * 0.32, cz + d * 0.88), Vector3(cx, 0.05, cz - 0.10)]


func _row_shot(r: int) -> Array:
	var z: float = (row_center[r] as Vector3).z
	var n := 0
	for m in lib:
		if int(m["row"]) == r:
			n += 1
	# fit the row across the frame: the horizontal half-angle of a 44 deg
	# vertical lens on 16:9 is 37 deg, so the distance is half the row width
	# over tan 37
	var half := (float(n) * 1.50) * 0.5 + 0.06
	var d: float = maxf(half / 0.754, 2.0)
	return [Vector3(0.0, 0.34 + d * 0.32, z + d * 0.88), Vector3(0.0, 0.05, z - 0.10)]


# A macro is shot from a real working distance with a long lens, not by putting
# the camera 0.6 m from the subject. At 0.6 m the carried lamp is four stops
# hotter than it is at the distance a machine actually stands, and everything
# clips: the image says "overexposed", not "close".
func _macro(id: String, h := 0.95, d := 2.55) -> Array:
	var c: Vector3 = tile_center[id]
	return [c + Vector3(0.0, h, d), c + Vector3(0.0, 0.05, 0.02)]


func _dump_calib_rects() -> void:
	var out: Array = []
	for r in calib_rects:
		var a := cam.unproject_position(r["a"])
		var b := cam.unproject_position(r["b"])
		out.append({
			"id": r["id"], "lo": r["lo"], "hi": r["hi"],
			"x0": int(minf(a.x, b.x)), "x1": int(maxf(a.x, b.x)),
			"y0": int(minf(a.y, b.y)), "y1": int(maxf(a.y, b.y)),
		})
	var f := FileAccess.open(SHOT_DIR + "calib_rects.json", FileAccess.WRITE)
	f.store_string(JSON.stringify({"width": sub.size.x, "height": sub.size.y,
		"swatches": out}, "  "))
	f.close()
	print("wrote %scalib_rects.json (%d swatches)" % [SHOT_DIR, out.size()])


func _run_shots() -> void:
	ui.visible = false
	_gset("bs_wet", 0.30)

	# the full library under each of the three lighting conditions
	for L in LIGHTS:
		_set_view("library")
		_set_light(L)
		await _shot("01_library_%s" % L)

	# every material, four at a time, at a working distance and at a fixed
	# exposure. This is where a material is judged.
	_set_light("lamp")
	var part := 0
	for r in range(BSLibrary.ROWS.size()):
		_show_rows(r)
		var ids: Array = []
		for m in lib:
			if int(m["row"]) == r:
				ids.append(m["id"])
		var i := 0
		while i < ids.size():
			var grp: Array = ids.slice(i, mini(i + 4, ids.size()))
			var p := _group_shot(grp)
			_look(p[0], p[1], 44.0)
			await _shot("02_%02d_%s" % [part, "_".join(PackedStringArray(grp))])
			part += 1
			i += 4

	# the wetness slider, dry and soaked, on the underfoot materials
	_show_rows(1)
	var p1 := _group_shot(["silt_dry", "silt_damp", "mud_saturated", "aggregate"])
	for wv in [0.0, 1.0]:
		_gset("bs_wet", wv)
		_look(p1[0], p1[1], 44.0)
		await _shot("03_wet_%s_underfoot" % ("dry" if wv < 0.5 else "soaked"))
	# and on the whole library
	_show_rows(-1)
	for wv in [0.0, 1.0]:
		_gset("bs_wet", wv)
		_set_view("library")
		await _shot("03_wet_%s_library" % ("dry" if wv < 0.5 else "soaked"))
	_gset("bs_wet", 0.30)

	# close macros of the underfoot materials -- the designer's named case
	_show_rows(1)
	for id in ["aggregate", "ballast", "silt_dry", "mud_saturated"]:
		var p := _macro(id)
		_look(p[0], p[1], 11.0)
		await _shot("04_macro_%s" % id)

	# the same macro with parallax off, which is the before/after for the
	# single biggest win in the underfoot case
	var pa := _macro("aggregate")
	_look(pa[0], pa[1], 11.0)
	_gset("bs_pom_on", 0.0)
	await _shot("05_macro_aggregate_no_parallax")
	_gset("bs_pom_on", 1.0)
	# and with the normal bands off, which is the before/after for the shader
	_gset("bs_detail_gain", 0.0)
	await _shot("05_macro_aggregate_no_detail_bands")
	_gset("bs_detail_gain", 1.0)

	# Water, at a grazing angle, which is the only angle at which water is
	# interesting: Fresnel at 75 degrees is 0.15 instead of 0.02, and that is
	# where a pool stops being a dark plane and starts being a mirror.
	_show_rows(2)
	var cw: Vector3 = tile_center["water_shallow"]
	var cd: Vector3 = tile_center["water_deep"]
	var pw := [cw + Vector3(-0.20, 0.30, 2.35), cw + Vector3(0.30, 0.02, -0.30)]
	var pd := [cd + Vector3(-0.20, 0.30, 2.35), cd + Vector3(0.30, 0.02, -0.30)]
	cfg["ssr"] = false
	_set_light("lamp")
	_look(pw[0], pw[1], 26.0)
	await _shot("06_water_shallow_lamp")
	_look(pd[0], pd[1], 26.0)
	await _shot("06_water_deep_ssr_off")
	cfg["ssr"] = true
	_set_light("lamp")
	_look(pd[0], pd[1], 26.0)
	await _shot("06_water_deep_ssr_on")
	cfg["ssr"] = false
	_set_light("machine")
	_look(pw[0], pw[1], 26.0)
	await _shot("06_water_shallow_machine")
	_set_light("lamp")

	# the calibration chart, and the rectangles a script needs to read it
	_show_rows(-1)
	_set_view("calib")
	await _shot("07_calibration_albedo")
	_dump_calib_rects()
	_gset("bs_debug", 0.0)
	_set_view("sweeps")
	_set_light("lamp")
	await _shot("07_calibration_sweeps")

	# the four rock scalars
	_set_view("scalars")
	_set_light("lamp")
	await _shot("08_scalars_lamp")

	# the exposure contract. The lamp goes back to its calibrated power and the
	# exposure back to 1.0: this is the one framed shot that is not metered.
	_set_view("falloff")
	_set_light("lamp")
	_scale_lights(1.0)
	env.tonemap_exposure = 1.0
	await _shot("09_falloff_lamp")

	# the surface, in daylight, with and without the sky ambient term
	_set_view("library")
	_show_rows(2)
	var p2 := _group_shot(["concrete_weathered", "hardstanding"])
	cfg["ambient_test"] = false
	_set_light("day")
	_look(p2[0], p2[1], 44.0)
	await _shot("10_day_sky_ambient_on")
	cfg["ambient_test"] = true
	_set_light("day")
	await _shot("10_day_sky_ambient_off")
	cfg["ambient_test"] = false

	# debug channels, for the record
	_set_light("lamp")
	_show_rows(1)
	var p0 := _group_shot(["silt_dry", "silt_damp", "mud_saturated", "aggregate"])
	_look(p0[0], p0[1], 44.0)
	for d in [[1.0, "albedo"], [2.0, "roughness"], [3.0, "normal"], [6.0, "metallic"]]:
		_gset("bs_debug", d[0])
		await _shot("11_debug_%s" % d[1])
	_gset("bs_debug", 0.0)

	print("SHOTS_DONE")
	if not cfg["stay"]:
		get_tree().quit()


# ---------------------------------------------------------------------------
# the light-budget diagnostic: what a known albedo actually renders as
# ---------------------------------------------------------------------------
func _mean_lin() -> float:
	var img: Image = sub.get_texture().get_image()
	var s := 0.0
	var n := 0
	for y in range(0, img.get_height(), 6):
		for x in range(0, img.get_width(), 6):
			var c := img.get_pixel(x, y).srgb_to_linear()
			s += 0.2126 * c.r + 0.7152 * c.g + 0.0722 * c.b
			n += 1
	return s / float(n)


func _probe(tag: String) -> void:
	for i in range(6):
		await RenderingServer.frame_post_draw
	print("%-44s mean linear %.5f" % [tag, _mean_lin()])


# ---------------------------------------------------------------------------
# ART-DIRECTION 2.2's ratios, measured on the floor at four ranges.
#   floor 3 m ahead, grazing   ~ 0.08 linear
#   near wall at 1.6 m         blown, deliberately
#   wall at 8 m                ~ 0.06 -- the last thing that reads
#   brightest : dimmest legible over three metres  ~ 90 : 1
# ---------------------------------------------------------------------------
func _sample(img: Image, world_pt: Vector3, r: int = 9) -> float:
	var sp := cam.unproject_position(world_pt)
	var x := int(sp.x)
	var y := int(sp.y)
	if x < r or y < r or x >= img.get_width() - r or y >= img.get_height() - r:
		return -1.0
	var s := 0.0
	var n := 0
	for dy in range(-r, r + 1):
		for dx in range(-r, r + 1):
			var c := img.get_pixel(x + dx, y + dy).srgb_to_linear()
			s += 0.2126 * c.r + 0.7152 * c.g + 0.0722 * c.b
			n += 1
	return s / float(n)


func _run_expo() -> void:
	ui.visible = false
	_scale_lights(1.0)
	_set_view("falloff")
	_set_light("lamp")
	var sl: SpotLight3D = null
	for c in (light_root["lamp"] as Node3D).get_children():
		if c is SpotLight3D:
			sl = c
	print("")
	print("=== ART 2.2 exposure calibration, aggregate floor + rock wall, linear ===")
	print("%8s %9s %9s %9s %9s %9s %9s %8s" % ["energy", "floor1.6", "floor3.0",
		"floor8.0", "wall1.6", "wall4.6", "wall8.0", "wall3m"])
	for combo in [[120.0, 2.0], [140.0, 2.0], [170.0, 2.0]]:
		sl.light_energy = combo[0]
		sl.spot_attenuation = combo[1]
		for i in range(6):
			await RenderingServer.frame_post_draw
		var img: Image = sub.get_texture().get_image()
		var f16 := _sample(img, Vector3(0.0, 0.0, -1.6))
		var f30 := _sample(img, Vector3(0.0, 0.0, -3.0))
		var f80 := _sample(img, Vector3(0.0, 0.0, -8.0))
		var w16 := _sample(img, Vector3(1.53, 0.9, -1.6))
		var w46 := _sample(img, Vector3(1.53, 0.9, -4.6))
		var w80 := _sample(img, Vector3(1.53, 0.9, -8.0))
		print("%8.1f %9.4f %9.4f %9.4f %9.4f %9.4f %9.4f %8.1f" % [
			combo[0], f16, f30, f80, w16, w46, w80, w16 / maxf(w46, 1e-6)])
	print("EXPO_DONE")
	get_tree().quit()


func _run_diag() -> void:
	ui.visible = false
	for k in view_root:
		(view_root[k] as Node3D).visible = false
	var root := Node3D.new()
	world.add_child(root)
	var mi := _mi(BSForms.plane(8.0, 8.0, 4), null, root, Transform3D())
	var sm := StandardMaterial3D.new()
	sm.albedo_color = Color(0.18, 0.18, 0.18)
	sm.roughness = 0.85
	sm.metallic = 0.0
	mi.material_override = sm
	_look(Vector3(0.0, 0.55, 1.4), Vector3(0.0, 0.0, -1.6), 46.0)

	# a bare positional light in the world, owned by nothing
	for k in light_root:
		(light_root[k] as Node3D).visible = false
		for c in (light_root[k] as Node3D).get_children():
			if c is Light3D:
				(c as Light3D).visible = false
	var probe_omni := OmniLight3D.new()
	probe_omni.position = Vector3(0.0, 1.2, -1.0)
	probe_omni.light_energy = 8.0
	probe_omni.omni_range = 12.0
	probe_omni.shadow_enabled = false
	world.add_child(probe_omni)
	await _probe("bare OmniLight in world, energy 8")
	for nf in [[0.05, 60.0], [0.1, 100.0], [0.3, 40.0]]:
		cam.near = nf[0]
		cam.far = nf[1]
		await _probe("bare Omni, cam near %.2f far %.0f" % [nf[0], nf[1]])
	cam.near = 0.02
	cam.far = 120.0
	var pv := get_viewport()
	print("   sub.own_world=%s  msaa=%d  ssaa=%d  scale=%s  debug_draw=%d" % [
		str(sub.own_world_3d), sub.msaa_3d, sub.screen_space_aa,
		str(sub.scaling_3d_mode), sub.debug_draw])
	print("   cluster max=%s" % str(ProjectSettings.get_setting("rendering/limits/cluster_builder/max_clustered_elements")))
	probe_omni.omni_attenuation = 1.0
	await _probe("bare OmniLight, attenuation 1.0")
	var probe_spot := SpotLight3D.new()
	probe_spot.position = Vector3(0.0, 1.6, 0.4)
	probe_spot.rotation_degrees = Vector3(-70.0, 0.0, 0.0)
	probe_spot.light_energy = 8.0
	probe_spot.spot_range = 12.0
	probe_spot.spot_angle = 45.0
	probe_spot.shadow_enabled = false
	world.add_child(probe_spot)
	probe_omni.visible = false
	await _probe("bare SpotLight in world, energy 8")
	probe_spot.visible = false

	for L in LIGHTS:
		_set_light(L)
		await _probe("StandardMaterial 0.18, light=" + L)

	_set_light("lamp")
	var sl: SpotLight3D = null
	for c in (light_root["lamp"] as Node3D).get_children():
		if c is SpotLight3D:
			sl = c
	for e in [1.0, 4.0, 14.0, 50.0, 200.0]:
		sl.light_energy = e
		await _probe("StandardMaterial 0.18, lamp energy %.0f" % e)
	for at in [0.5, 1.0, 1.8, 2.0]:
		sl.light_energy = 14.0
		sl.spot_attenuation = at
		await _probe("StandardMaterial 0.18, spot_attenuation %.1f" % at)
	sl.spot_attenuation = 1.8
	sl.shadow_enabled = false
	await _probe("StandardMaterial 0.18, shadows OFF")
	sl.shadow_enabled = true

	var src: Dictionary = {}
	for e2 in lib:
		if e2["id"] == "aggregate":
			src = e2["p"]
	var bm := ShaderMaterial.new()
	bm.shader = shaders["lean"]
	for k in src:
		bm.set_shader_parameter(k, src[k])
	mi.material_override = bm
	for wv in [0.0, 0.3, 0.7, 1.0]:
		_gset("bs_wet", wv)
		await _probe("bs aggregate, wet %.1f" % wv)
	_gset("bs_wet", 0.0)
	bm.set_shader_parameter("alb_lo", Vector3(0.18, 0.18, 0.18))
	bm.set_shader_parameter("alb_hi", Vector3(0.18, 0.18, 0.18))
	await _probe("bs aggregate, albedo forced 0.18, wet 0")
	_gset("bs_normal_gain", 0.0)
	await _probe("bs aggregate, albedo 0.18, no normal perturbation")
	_gset("bs_normal_gain", 1.0)
	print("DIAG_DONE")
	get_tree().quit()


# ---------------------------------------------------------------------------
# per-material cost, at 1920x1080 full screen coverage
# ---------------------------------------------------------------------------
func _run_cost() -> void:
	ui.visible = false
	for k in view_root:
		(view_root[k] as Node3D).visible = false
	_set_light("lamp")
	_scale_lights(1.0)
	env.glow_enabled = false

	# Two conditions, because one number is not enough to budget with.
	#   UNDERFOOT  a 60 m plane filling the frame with the near edge at 0.4 m.
	#              Every pixel runs the parallax march at full step count and
	#              every normal band is on. This is the worst case in the game
	#              and it is what a machine standing still is looking at.
	#   AT RANGE   the same plane from 6 m at a shallower angle, so the pixel
	#              footprint has faded the micro band out and the parallax
	#              range has expired over most of the frame. This is what a
	#              wall or a floor eight metres away costs.
	var root := Node3D.new()
	world.add_child(root)
	var plane := BSForms.plane(80.0, 80.0, 2)
	var mi := _mi(plane, null, root, Transform3D())

	var flat := StandardMaterial3D.new()
	flat.albedo_color = Color(0.18, 0.18, 0.18)
	flat.roughness = 0.8

	var poses := {
		"underfoot": [Vector3(0.0, 0.45, 0.0), Vector3(0.0, 0.20, -1.2)],
		"at range": [Vector3(0.0, 1.70, 0.0), Vector3(0.0, 1.20, -6.0)],
	}
	var base := {}
	for cond in poses:
		_look(poses[cond][0], poses[cond][1], 62.0, false)
		env.tonemap_exposure = 1.0
		base[cond] = await _measure(mi, flat, 15)

	print("")
	print("=== per-material GPU cost, 1920x1080, the material covering the frame ===")
	print("adapter: %s" % adapter)
	print("baseline, StandardMaterial3D, one spot with shadows:")
	for cond in poses:
		print("    %-10s %6.3f ms" % [cond, base[cond]])
	print("")
	print("%-22s %10s %10s %10s   %s" % ["material", "underfoot", "at range",
		"delta near", "verdict at full screen"])
	for m in lib:
		var ms := {}
		for cond in poses:
			_look(poses[cond][0], poses[cond][1], 62.0, false)
			env.tonemap_exposure = 1.0
			ms[cond] = await _measure(mi, mats[m["id"]], 9)
		var near: float = ms["underfoot"]
		var far: float = ms["at range"]
		var verdict := "large surfaces, any range"
		if near > 12.0 and far > 6.0:
			verdict = "CLOSE RANGE ONLY, and not the whole floor"
		elif near > 12.0:
			verdict = "fine at range, restrict near coverage"
		elif near > 5.0:
			verdict = "large surfaces, watch near coverage"
		print("%-22s %10.2f %10.2f %10.2f   %s" % [m["id"], near, far,
			near - base["underfoot"], verdict])

	# the three shader variants on identical parameters
	print("")
	print("=== variant cost, identical uniforms (rock_weathered), underfoot ===")
	var src: Dictionary = {}
	for e in lib:
		if e["id"] == "rock_weathered":
			src = e["p"]
	_look(poses["underfoot"][0], poses["underfoot"][1], 62.0, false)
	env.tonemap_exposure = 1.0
	for vn in ["full", "lean", "far"]:
		var sm := ShaderMaterial.new()
		sm.shader = shaders[vn]
		for k in src:
			sm.set_shader_parameter(k, src[k])
		var msx := await _measure(mi, sm, 12)
		print("%-22s %10.2f ms" % [vn, msx])

	# what each feature costs, on the underfoot case the designer named
	print("")
	print("=== ablation on `aggregate`, underfoot ===")
	for ab in [["everything on", 1.0, 1.0], ["no parallax", 0.0, 1.0],
			["no detail+micro bands", 1.0, 0.0], ["neither", 0.0, 0.0]]:
		_gset("bs_pom_on", ab[1])
		_gset("bs_detail_gain", ab[2])
		var msy := await _measure(mi, mats["aggregate"], 12)
		print("%-22s %10.2f ms" % [ab[0], msy])
	_gset("bs_pom_on", 1.0)
	_gset("bs_detail_gain", 1.0)

	print("COST_DONE")
	get_tree().quit()


func _measure(mi: MeshInstance3D, mat: Material, frames: int) -> float:
	mi.material_override = mat
	for i in range(3):
		await RenderingServer.frame_post_draw
	var samples: Array[float] = []
	for i in range(frames):
		await RenderingServer.frame_post_draw
		var g: float = RenderingServer.viewport_get_measured_render_time_gpu(sub.get_viewport_rid())
		if g > 0.0:
			samples.append(g)
	if samples.is_empty():
		return 0.0
	samples.sort()
	return samples[samples.size() / 2]
