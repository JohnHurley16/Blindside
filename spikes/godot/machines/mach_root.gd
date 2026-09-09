# ---------------------------------------------------------------------------
# BLINDSIDE machines spike -- the scene, the three lighting rigs, the shots.
#
# Run:
#   <godot> --path spikes/godot/machines --resolution 1920x1080
#   ... --  --shots            just the stills
#   ... --  --seq              just the walk-cycle sequences
#   ... --  --shot=NAME        one shot
#
# THREE RIGS, and the difference between them matters:
#   CLEAR     a neutral grey world and one key. NOT THE GAME. ART 2.1 keeps the
#             studio lights for "catalogue and marketing renders -- those are
#             not the game", and this is that. Ambient here is a deliberate,
#             labelled exception to ART 9's "no ambient light, ever".
#   DARK      the game. World background strength ZERO, ambient DISABLED, and
#             the only light in the frame is a lamp a machine is carrying.
#   DAYLIGHT  the surface. Overcast at the shaft's own 12000 K, no sun disc.
# ---------------------------------------------------------------------------
extends Node3D

const SHOT_DIR := "res://shots/"
const W := 1920
const H := 1080

var sub: SubViewport
var world: Node3D
var env: Environment
var cam: Camera3D
var key: DirectionalLight3D
var machines: Array = []
var ground_node: MeshInstance3D
var ground_mat: ShaderMaterial
var rod: Node3D

var cfg := {"shots": true, "seq": true, "shot": "", "dir": ""}
var busy := false
var stats_lines: Array = []
var broken := false
var cur_rig := "clear"


# ===========================================================================
# ground
# ===========================================================================
# One height function, used both to build the mesh and to plant the feet, so
# the two cannot disagree. A machine standing on a mesh whose collision is a
# different surface is the classic floating tell.
static func h_flat(_x: float, _z: float) -> float:
	return 0.0


static func h_broken(x: float, z: float) -> float:
	# a worked floor: a long shallow camber, drill-round steps every 1.2 m, and
	# spall. Amplitudes are small on purpose -- a mine floor is walkable.
	var h: float = sin(x * 0.9) * 0.042 + cos(z * 1.3 + 1.1) * 0.030
	h += sin(x * 2.7 + z * 1.9) * 0.024
	h += floor(fposmod(x, 2.4) / 1.2) * 0.048
	h += sin(x * 9.1 + z * 7.3) * 0.009 + sin(x * 17.0 - z * 13.0) * 0.005
	# loose stones the machine has to step over. A mine floor is muck and
	# spall, not a camber: 15 cm of relief across a stride is what makes the
	# hull work, and 2 cm is what makes it look like a hovercraft.
	for s in [[0.35, 0.09, 0.22, 0.085], [1.5, -0.11, 0.20, 0.075],
			  [2.4, 0.13, 0.19, 0.065], [3.1, -0.14, 0.17, 0.055]]:
		var d: float = Vector2(x - s[0], z - s[1]).length()
		if d < s[2]:
			h += s[3] * cos(d / s[2] * PI * 0.5)
	return h


func _ground_h(x: float, z: float) -> float:
	return h_broken(x, z) if broken else h_flat(x, z)


func _build_ground(kind: String) -> void:
	if ground_node:
		ground_node.queue_free()
	broken = kind == "broken"
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var n := 150
	var span := 14.0
	var step: float = span / float(n)
	for i in range(n):
		for j in range(n):
			var x0: float = -span * 0.5 + float(i) * step
			var z0: float = -span * 0.5 + float(j) * step
			var pts := [Vector2(x0, z0), Vector2(x0 + step, z0),
						Vector2(x0 + step, z0 + step), Vector2(x0, z0 + step)]
			var v := []
			for p in pts:
				v.append(Vector3(p.x, _ground_h(p.x, p.y), p.y))
			# Godot's front face winds so the naive cross product points INTO
			# the solid (measured in the assayer spike). For an up-facing floor
			# that means the cross must be -Y, which is [0,1,2] and [0,2,3].
			# The other order renders no floor at all, from any angle.
			for tri in [[0, 1, 2], [0, 2, 3]]:
				var a: Vector3 = v[tri[0]]
				var b: Vector3 = v[tri[1]]
				var c: Vector3 = v[tri[2]]
				var nn: Vector3 = (b - a).cross(c - a).normalized()
				if nn.y < 0.0:
					nn = -nn
				for q in [a, b, c]:
					st.set_normal(nn)
					st.add_vertex(q)
	var mesh: ArrayMesh = st.commit()
	ground_node = MeshInstance3D.new()
	ground_node.mesh = mesh
	ground_mat = ShaderMaterial.new()
	ground_mat.shader = load("res://ground.gdshader")
	ground_node.material_override = ground_mat
	world.add_child(ground_node)


# ===========================================================================
func _ready() -> void:
	_parse_args()
	var layer := CanvasLayer.new()
	add_child(layer)
	var svc := SubViewportContainer.new()
	svc.stretch = true
	svc.set_anchors_preset(Control.PRESET_FULL_RECT)
	layer.add_child(svc)
	sub = SubViewport.new()
	sub.size = Vector2i(W, H)
	sub.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	sub.msaa_3d = Viewport.MSAA_4X
	sub.screen_space_aa = Viewport.SCREEN_SPACE_AA_FXAA
	sub.positional_shadow_atlas_size = 4096
	svc.add_child(sub)

	world = Node3D.new()
	sub.add_child(world)
	env = Environment.new()
	env.tonemap_mode = Environment.TONE_MAPPER_AGX
	env.tonemap_exposure = 1.0
	env.tonemap_white = 6.0
	env.glow_enabled = true
	env.glow_intensity = 0.30
	env.glow_bloom = 0.02
	env.glow_hdr_threshold = 1.5
	var we := WorldEnvironment.new()
	we.environment = env
	world.add_child(we)

	cam = Camera3D.new()
	cam.fov = 40.0
	cam.near = 0.02
	cam.far = 90.0
	sub.add_child(cam)

	key = DirectionalLight3D.new()
	key.light_energy = 1.0
	key.shadow_enabled = true
	key.light_angular_distance = 2.0
	world.add_child(key)

	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(SHOT_DIR))
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(SHOT_DIR + "seq/"))
	_build_ground("flat")
	_run()


func _parse_args() -> void:
	for a in OS.get_cmdline_user_args():
		if a == "--shots":
			cfg["seq"] = false
		elif a == "--seq":
			cfg["shots"] = false
		elif a.begins_with("--shot="):
			cfg["shot"] = a.substr(7)
			cfg["seq"] = false


# --- the three rigs ---------------------------------------------------------
func rig_clear() -> void:
	cur_rig = "clear"
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color(0.26, 0.26, 0.27)
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.40, 0.41, 0.45)
	env.ambient_light_energy = 0.34
	env.volumetric_fog_enabled = false
	key.visible = true
	key.light_energy = 2.3
	key.light_color = Color(1.0, 0.98, 0.96)
	key.rotation_degrees = Vector3(-38, 36, 0)
	ground_mat.set_shader_parameter("studio", 1.0)
	ground_mat.set_shader_parameter("gauge", 1.0)


func rig_dark() -> void:
	cur_rig = "dark"
	# ART 2.1: world background strength ZERO. If a pixel is lit, name the
	# fixture -- and in this rig every fixture is a lamp a machine is carrying.
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color(0, 0, 0)
	env.ambient_light_source = Environment.AMBIENT_SOURCE_DISABLED
	env.ambient_light_energy = 0.0
	# ART 2.6: resting cave volume scatter 0.008-0.012, anisotropy 0.55,
	# colour (0.85,0.86,0.90) so it does not blue-shift.
	env.volumetric_fog_enabled = true
	env.volumetric_fog_density = 0.010
	env.volumetric_fog_anisotropy = 0.55
	env.volumetric_fog_albedo = Color(0.85, 0.86, 0.90)
	env.volumetric_fog_emission_energy = 0.0
	env.volumetric_fog_length = 30.0
	env.volumetric_fog_gi_inject = 0.0
	key.visible = false
	ground_mat.set_shader_parameter("studio", 0.0)
	ground_mat.set_shader_parameter("gauge", 0.0)


func rig_daylight() -> void:
	cur_rig = "daylight"
	# ART 2.1: the shaft is 12000 K (0.60, 0.74, 1.00) and is the only daylight.
	# The surface's light IS the light that comes down the shaft -- overcast,
	# no sun disc. That claim is the vision board's and it still needs a yes.
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color(0.42, 0.50, 0.62)
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.60, 0.74, 1.00)
	env.ambient_light_energy = 1.5
	env.volumetric_fog_enabled = false
	key.visible = true
	key.light_energy = 1.1
	key.light_color = Color(0.86, 0.90, 1.00)
	key.rotation_degrees = Vector3(-62, 24, 0)
	ground_mat.set_shader_parameter("studio", 0.0)
	ground_mat.set_shader_parameter("gauge", 0.0)


# Strip the frame back to nothing but the outline: no light, no ambient, no
# glow, no ground, and every emissive off. What survives is the silhouette.
func _outline_rig() -> void:
	key.visible = false
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color(0.62, 0.62, 0.63)
	env.ambient_light_source = Environment.AMBIENT_SOURCE_DISABLED
	env.ambient_light_energy = 0.0
	env.volumetric_fog_enabled = false
	env.glow_enabled = false
	for m in machines:
		m.lamp_on = false
		m.refresh()
		m.mat_body.set_shader_parameter("dead", 1.0)
	ground_node.visible = false
	if rod:
		rod.visible = false


# --- machines ---------------------------------------------------------------
func clear_machines() -> void:
	for m in machines:
		m.queue_free()
	machines.clear()
	if rod:
		rod.queue_free()
		rod = null


func add_machine(ch: String, at: Vector3, yaw_deg: float, team := "player",
				 wear := 0.35, damage := 0.0, variant := "") -> Machine:
	var m := Machine.new()
	world.add_child(m)
	m.build(variant if variant != "" else ch, ch, team, wear, damage)
	m.position = at
	m.rotation_degrees = Vector3(0, yaw_deg, 0)
	# The work lamp is a fixture in the WORLD, not a studio light. Under the
	# catalogue rig it throws a two-metre pool across the backdrop and reads as
	# a lighting mistake, so it is off wherever the frame is not about it.
	if cur_rig != "dark":
		m.lamp_on = false
		m.refresh()
	m.ground = Callable(self, "_ground_h")
	machines.append(m)
	return m


# A one-metre rod in 0.1 m black and white bands, and the 0.60 m rail gauge --
# the vision board's CLEAR rig, so the two boards can be compared directly.
func add_rod(at: Vector3) -> void:
	rod = Node3D.new()
	world.add_child(rod)
	rod.position = at
	for i in range(10):
		var b := MeshInstance3D.new()
		var bm := BoxMesh.new()
		bm.size = Vector3(0.022, 0.1, 0.022)
		b.mesh = bm
		b.position = Vector3(0, 0.05 + 0.1 * float(i), 0)
		var sm := StandardMaterial3D.new()
		sm.albedo_color = Color(0.02, 0.02, 0.02) if i % 2 == 0 else Color(0.86, 0.86, 0.86)
		sm.roughness = 0.8
		b.material_override = sm
		rod.add_child(b)


static func yaw_toward(from: Vector3, to: Vector3) -> float:
	var d: Vector3 = to - from
	return rad_to_deg(atan2(-d.z, d.x))


func settle(n: int = 24) -> void:
	for m in machines:
		m._settled = false
	for i in range(n):
		for m in machines:
			m.advance(1.0 / 30.0)


# --- capture ----------------------------------------------------------------
func shoot(name: String, note: String = "", crop := Rect2i()) -> void:
	for k in range(6):
		await RenderingServer.frame_post_draw
	var img: Image = sub.get_texture().get_image()
	if crop.size.x > 0:
		img = img.get_region(crop)
	var p: String = SHOT_DIR + name + ".png"
	img.save_png(ProjectSettings.globalize_path(p))
	var dc: int = int(Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME))
	var pr: int = int(Performance.get_monitor(Performance.RENDER_TOTAL_PRIMITIVES_IN_FRAME))
	var line := "%-28s %dx%d draws=%-5d tris=%-8d %s" % [name, img.get_width(), img.get_height(), dc, pr, note]
	# ART 0: a lamp that fires backwards produced twelve times too little light
	# in agent_model for one character's sake, and it survived four passes. The
	# beam direction and its angle to the camera go in the log of every frame
	# so it cannot happen quietly again.
	if machines.size() > 0 and machines[0].lamp:
		var lf: Vector3 = -machines[0].lamp.global_transform.basis.z
		var cf: Vector3 = -cam.global_transform.basis.z
		line += "  lampfwd=%s dot(cam,lamp)=%.3f" % [str(lf.snapped(Vector3(0.01, 0.01, 0.01))), cf.dot(lf)]
	stats_lines.append(line)
	print(line)


func look_at_from(eye: Vector3, target: Vector3, fov := 40.0, ortho := 0.0) -> void:
	cam.projection = Camera3D.PROJECTION_ORTHOGONAL if ortho > 0.0 else Camera3D.PROJECTION_PERSPECTIVE
	if ortho > 0.0:
		# A row of four machines is 3.5 m wide and 0.5 m tall. Godot's ortho
		# keeps the HEIGHT by default, which crops a row to its middle two.
		# These shots keep the WIDTH and the frame is cropped to a strip.
		cam.keep_aspect = Camera3D.KEEP_WIDTH
		cam.size = ortho
	else:
		cam.keep_aspect = Camera3D.KEEP_HEIGHT
		cam.fov = fov
	cam.global_transform = Transform3D(Basis.looking_at((target - eye).normalized(), Vector3.UP), eye)


func _run() -> void:
	busy = true
	if cfg["shots"]:
		await _stills()
	if cfg["seq"]:
		await _sequences()
	await _cost_table()
	var f := FileAccess.open("res://shots/stats.txt", FileAccess.WRITE)
	for l in stats_lines:
		f.store_line(l)
	f.close()
	print("DONE")
	await get_tree().create_timer(0.2).timeout
	get_tree().quit()


# Per-machine cost. A match has several on screen at once, so the number that
# matters is the cost of ONE, not the cost of the frame.
func _cost_table() -> void:
	clear_machines()
	_build_ground("flat")
	rig_clear()
	stats_lines.append("")
	stats_lines.append("--- per machine, measured at load ---")
	for c in Book.ORDER:
		var m := add_machine(c, Vector3.ZERO, 0.0)
		stats_lines.append("%-9s tris=%-6d draw_surfaces=%d bones=%-3d legs=%d build=%.0f ms  hull=%.2f m" % [
			c, m.tri_count, m.draw_surfaces, m.bone_count, Book.CHASSIS[c]["legs"],
			m.build_ms, Book.hull_len(c)])
		clear_machines()
	for l in stats_lines:
		print(l)


func _want(n: String) -> bool:
	return cfg["shot"] == "" or cfg["shot"] == n


# ===========================================================================
# THE STILLS
# ===========================================================================
func _stills() -> void:
	var order: Array = Book.ORDER

	# --- 01 the four abreast, one scale, a clear light ---------------------
	if _want("01_four_abreast_clear"):
		clear_machines(); _build_ground("flat"); rig_clear()
		var x := -0.95
		for c in order:
			var m := add_machine(c, Vector3(x, 0, 0), -90.0)
			x += 0.62
		add_rod(Vector3(-1.55, 0, 0))
		settle()
		look_at_from(Vector3(1.1, 0.62, 2.55), Vector3(-0.05, 0.20, 0), 34.0)
		await shoot("01_four_abreast_clear", "scout surveyor hauler swimmer, 1 m rod")

	# --- 02 the same four in the game's own light --------------------------
	if _want("02_four_abreast_own_light"):
		rig_dark()
		for m in machines:
			m.lamp_on = true
			m.refresh()
		look_at_from(Vector3(1.1, 0.62, 2.55), Vector3(-0.05, 0.20, 0), 34.0)
		await shoot("02_four_abreast_own_light", "only light in frame is four work lamps")

	# --- 03..06 each chassis alone, three-quarter --------------------------
	var i := 3
	for c in order:
		var nm := "%02d_%s_3q" % [i, c]
		i += 1
		if not _want(nm):
			continue
		clear_machines(); _build_ground("flat"); rig_clear()
		var m := add_machine(c, Vector3.ZERO, -35.0)
		m.look_at_local(18.0, -6.0)
		# ART 4.4: passive sensors are dark, active sensors emit. The catalogue
		# frame shows the bar LIT because that is the only state in which the
		# seven elements can be counted; every in-situ frame here is passive.
		m.pinging = true
		m.refresh()
		settle()
		var L: float = Book.hull_len(c)
		var d: float = L * 2.6 + 0.35
		look_at_from(Vector3(d * 0.72, L * 0.85 + 0.10, d * 0.72), Vector3(0, L * 0.42, 0), 36.0)
		await shoot(nm, "hull %.2f m, ride %.2f m, %d legs" % [L, Book.ride(c), Book.CHASSIS[c]["legs"]])

	# --- 07 orthographic side elevation, one row, one rod ------------------
	if _want("07_side_ortho_row"):
		clear_machines(); _build_ground("flat"); rig_clear()
		var x := -1.35
		for c in order:
			add_machine(c, Vector3(x, 0, 0), 180.0)
			x += Book.hull_len(c) * 0.5 + 0.62
		add_rod(Vector3(-2.15, 0, 0))
		settle()
		look_at_from(Vector3(0.15, 0.45, 6.0), Vector3(0.15, 0.45, 0), 40.0, 5.0)
		await shoot("07_side_ortho_row", "ORTHOGRAPHIC, same scale, 1 m rod in 0.1 m bands",
					Rect2i(0, 300, 1920, 470))

	# --- 08 silhouette only: can you tell the four apart from the outline? --
	if _want("08_silhouette_four"):
		# THE TEST, and it has to be a real one: no light at all and a bright
		# background, so what is left is the outline and nothing else. ART 2.4
		# makes the outline the loadout readout and DESIGN.html makes it always
		# honest; if the four do not separate here they do not separate in a
		# match either.
		_outline_rig()
		look_at_from(Vector3(0.15, 0.45, 6.0), Vector3(0.15, 0.45, 0), 40.0, 5.0)
		await shoot("08_silhouette_four", "THE TEST: four outlines, no surface at all",
					Rect2i(0, 300, 1920, 470))
		ground_node.visible = true
		env.glow_enabled = true

	# --- 09 what a loadout does to the outline -----------------------------
	if _want("09_loadout_silhouette"):
		clear_machines(); _build_ground("flat"); rig_clear()
		add_machine("surveyor", Vector3(-0.42, 0, 0), 180.0, "player", 0.35, 0.0, "surveyor_bare")
		add_machine("surveyor", Vector3(0.42, 0, 0), 180.0)
		settle()
		look_at_from(Vector3(0.0, 0.40, 4.6), Vector3(0.0, 0.40, 0), 40.0, 2.4)
		await shoot("09_loadout_silhouette", "bare (left) vs default loadout (right), ortho side",
					Rect2i(0, 300, 1920, 470))
		# and again as pure outline, which is what ART 4.4 actually claims
		_outline_rig()
		await shoot("09b_loadout_outline", "the same pair, outline only: the difference IS the readout",
					Rect2i(0, 300, 1920, 470))
		ground_node.visible = true
		env.glow_enabled = true

	# --- 10 team identity: value and rhythm, never hue ---------------------
	if _want("10_team_player_vs_rival"):
		clear_machines(); _build_ground("flat"); rig_clear()
		add_machine("surveyor", Vector3(-0.45, 0, 0.0), 200.0, "player")
		add_machine("surveyor", Vector3(0.45, 0, 0.0), 200.0, "rival")
		settle()
		look_at_from(Vector3(0.0, 0.46, 2.55), Vector3(0.0, 0.24, 0), 42.0)
		await shoot("10_team_player_vs_rival", "player pale-over-graphite, rival inverted; same hue budget")

	# --- 11 wear is history --------------------------------------------------
	if _want("11_wear_fresh_vs_worn"):
		clear_machines(); _build_ground("flat"); rig_clear()
		add_machine("surveyor", Vector3(-0.45, 0, 0.0), 200.0, "player", 0.0)
		add_machine("surveyor", Vector3(0.45, 0, 0.0), 200.0, "player", 0.85)
		settle()
		look_at_from(Vector3(0.0, 0.46, 2.55), Vector3(0.0, 0.24, 0), 42.0)
		await shoot("11_wear_fresh_vs_worn", "wear 0.00 vs 0.85 -- veteran, not casualty")

	# --- 12 the damage rungs -------------------------------------------------
	if _want("12_damage_rungs"):
		clear_machines(); _build_ground("flat"); rig_clear()
		var rungs := [0.0, 0.20, 0.30, 0.50, 0.75, 1.0]
		var x2 := -1.55
		for d in rungs:
			var m := add_machine("surveyor", Vector3(x2, 0, 0), 180.0, "player", 0.35, d)
			m.pinging = true          # lit so the lost elements can be counted
			m.refresh()
			if d >= 0.75:
				m.set_clip("crouch")   # rung 0.75: ride height drops 25%
			if d >= 1.0:
				m.extra_roll = deg_to_rad(13.0)
				m.extra_pitch = deg_to_rad(-5.0)
			x2 += 0.62
		settle()
		look_at_from(Vector3(0.35, 0.30, 6.0), Vector3(0.35, 0.30, 0), 40.0, 4.6)
		await shoot("12_damage_rungs", "0 / .20 / .30 / .50 / .75 / 1.0 -- bar 7,4,4,2,2,0",
					Rect2i(0, 270, 1920, 540))

	# --- 13 a machine under its own lamp ------------------------------------
	if _want("13_own_lamp"):
		clear_machines(); _build_ground("broken"); rig_dark()
		var m := add_machine("surveyor", Vector3(0, 0, 0), -20.0)
		m.look_at_local(0.0, 0.0)
		settle()
		# ART 2.4: put the machine BETWEEN the camera and its own pool. The
		# vision board measured 0.71% of frame that way against 0.08% with the
		# pool beside it -- nine times the read for a camera move.
		look_at_from(Vector3(-1.05, 0.40, 0.42), Vector3(2.2, 0.01, -0.72), 54.0)
		await shoot("13_own_lamp", "the only light in the world is on its head")

	# --- 14 daylight, on the surface ----------------------------------------
	if _want("14_daylight"):
		clear_machines(); _build_ground("flat"); rig_daylight()
		var m2 := add_machine("surveyor", Vector3(0, 0, 0), -35.0)
		m2.lamp_on = false
		m2.refresh()
		m2.look_at_local(12.0, -8.0)
		settle()
		look_at_from(Vector3(1.35, 0.60, 1.35), Vector3(0, 0.24, 0), 38.0)
		await shoot("14_daylight", "overcast at 12000 K, no sun disc; emissives vanish")

	# --- 15 the nine-pixel test ---------------------------------------------
	if _want("15_nine_pixels"):
		await _nine_pixels()

	# --- 16 / 17 the walk, side and front ------------------------------------
	if _want("16_walk_side"):
		clear_machines(); _build_ground("flat"); rig_clear()
		var m3 := add_machine("surveyor", Vector3(-1.2, 0, 0), 0.0)
		m3.set_walking(true, "walk")
		settle(30)
		for k in range(9):
			m3.advance(1.0 / 30.0)
		look_at_from(m3.global_position + Vector3(0, 0.30, 2.3), m3.global_position + Vector3(0, 0.24, 0), 40.0)
		await shoot("16_walk_side", "mid-stride, side")

	if _want("17_walk_front"):
		clear_machines(); _build_ground("flat"); rig_clear()
		var m4 := add_machine("surveyor", Vector3(-1.6, 0, 0), 0.0)
		m4.set_walking(true, "walk")
		settle(30)
		for k in range(5):
			m4.advance(1.0 / 30.0)
		look_at_from(m4.global_position + Vector3(2.1, 0.34, 0.05), m4.global_position + Vector3(0, 0.26, 0), 38.0)
		await shoot("17_walk_front", "mid-stride, head on")

	# --- 18 broken ground, the body responding -------------------------------
	if _want("18_broken_ground"):
		clear_machines(); _build_ground("broken"); rig_clear()
		var m5 := add_machine("surveyor", Vector3(-0.6, 0, 0), 0.0)
		m5.set_walking(true, "walk")
		settle(40)
		for k in range(52):
			m5.advance(1.0 / 30.0)
		look_at_from(m5.global_position + Vector3(-0.45, 0.22, 1.55),
					 m5.global_position + Vector3(0.25, 0.16, 0), 44.0)
		await shoot("18_broken_ground", "pitch %.1f deg roll %.1f deg" % [
			rad_to_deg(m5.body_pitch), rad_to_deg(m5.body_roll)])

	# --- 19 / 20 the running lights, the decision in two frames --------------
	if _want("19_running_lights_unfound"):
		clear_machines(); _build_ground("flat"); rig_dark()
		# The strip on the model is 0.32L x 4 mm. ART 4.3 rule 2 asks for
		# 0.32L x 16 mm -- "area over intensity" -- and that change is in
		# agent_model, not here, so these two frames are shot at 1.6 m rather
		# than at the 4.5 m the vision board used. At 4.5 m a 4 mm strip is
		# one pixel and the decision cannot be made on the picture.
		# The geometry of this frame is the whole point of ART 4.5, so it is
		# constructed rather than guessed. Retroreflective sheeting returns
		# light along the ray it arrived on, so the finder's LAMP has to be
		# beside the finder's EYE -- which is the case that matters, because a
		# rival's lamp is bolted to a rival's head. Here the camera stands in
		# for that eye, the finder is set 0.40 m to one side of it and 0.50 m
		# behind, and the angle subtended at the strip between lamp and eye
		# comes out at about 11 degrees. Behind the camera the finder is out of
		# frame; on the camera it fills it, which is what the first two
		# attempts at this shot did.
		var eye := Vector3(-1.90, 0.42, 1.50)
		var vdir: Vector3 = (Vector3(0, 0.20, 0) - eye).normalized()
		var right: Vector3 = vdir.cross(Vector3.UP).normalized()
		var fp: Vector3 = eye + right * 0.40 - vdir * 0.50
		fp.y = 0.0
		# the quiet machine stands side-on to the camera so the flank strip is
		# the thing being tested
		var quiet := add_machine("surveyor", Vector3.ZERO,
								 yaw_toward(Vector3.ZERO, eye) + 104.0, "rival")
		quiet.lamp_on = false
		quiet.refresh()
		var finder := add_machine("surveyor", fp, yaw_toward(fp, Vector3.ZERO), "player")
		# the lamp swung 46 degrees off, so it misses
		finder.look_at_local(-46.0, 0.0)
		settle()
		quiet.hold(0.0)
		finder.hold(0.0)
		look_at_from(eye, Vector3(0.0, 0.20, 0.0), 40.0)
		await shoot("19_running_lights_unfound", "quiet machine, lamp pointed PAST it")
		finder.look_at_local(0.0, -4.0)
		settle(8)
		quiet.hold(0.0)
		finder.hold(0.0)
		await shoot("20_running_lights_found", "same frame, lamp swung on: it returns like a road sign")

	# --- 21 the emissive fallback, honestly costed ---------------------------
	if _want("21_running_lights_fallback"):
		for m in machines:
			m.set_emissive_running_lights(true)
		machines[1].look_at_local(0.0, -4.0)
		settle(8)
		for m in machines:
			m.hold(0.0)
		await shoot("21_running_lights_fallback", "ART 4.5 fallback: strip at 1.5, always on, a permanent tell")
		for m in machines:
			m.set_emissive_running_lights(false)

	# --- 22 the Hauler's size, which the documents disagree about ------------
	if _want("22_hauler_size_question"):
		clear_machines(); _build_ground("flat"); rig_clear()
		var a := add_machine("hauler", Vector3(-1.35, 0, 0), 180.0)
		var b := add_machine("hauler", Vector3(1.55, 0, 0), 180.0)
		# CHASSIS-TIMING gives the Hauler a body of 4.0 cells = 2.4 m; the model
		# is 0.90 m. Scaling the model is not what a 2.4 m Hauler would be, but
		# it puts the disagreement on a picture, which is what the vision board
		# asked the designer to decide from.
		b.scale = Vector3.ONE * (2.4 / 0.90)
		settle()
		look_at_from(Vector3(0.2, 0.75, 7.5), Vector3(0.2, 0.75, 0), 40.0, 5.4)
		await shoot("22_hauler_size_question", "model 0.90 m (left) vs CHASSIS-TIMING 2.4 m (right)",
					Rect2i(0, 250, 1920, 570))


func _nine_pixels() -> void:
	# ART 4.2's third rule and SPECTATOR-DISPLAY 6.4: a machine is NINE PIXELS
	# at CAMERA_WIDE, and anything that cannot be read there cannot be read in
	# a match. The framing is `av_08`'s: the machine BETWEEN the camera and its
	# own pool, because ART 2.4 measured that as nine times the read of the
	# same machine with its pool beside it.
	clear_machines(); _build_ground("flat"); rig_dark()
	var labels := ["scout", "surveyor", "hauler", "swimmer", "rival", "dmg .75", "wreck"]
	var setups := [["scout", "player", 0.35, 0.0], ["surveyor", "player", 0.35, 0.0],
				   ["hauler", "player", 0.35, 0.0], ["swimmer", "player", 0.35, 0.0],
				   ["surveyor", "rival", 0.35, 0.0], ["surveyor", "player", 0.5, 0.75],
				   ["surveyor", "player", 0.95, 1.0]]
	var srcs := []
	for st in setups:
		clear_machines()
		var m := add_machine(st[0], Vector3.ZERO, 180.0, st[1], st[2], st[3])
		m.lamp_on = st[3] < 1.0
		m.refresh()
		m.look_at_local(0.0, 0.0)
		if st[3] >= 0.75:
			m.set_clip("crouch")
		if st[3] >= 1.0:
			m.extra_roll = deg_to_rad(14.0)
			# a wreck emits nothing, so it cannot share the others' light: it is
			# found by a lamp beside the camera, which is ART 6.2's argument for
			# the retroreflective proposal in the first place
			var fp := Vector3(2.55, 0, 0.85)
			var finder := add_machine("surveyor", fp, yaw_toward(fp, Vector3.ZERO))
			finder.lamp_on = true
			finder.refresh()
			finder.look_at_local(0.0, -7.0)
		settle()
		# ART 2.4: the machine BETWEEN the camera and its own pool. The lamp
		# throws down the -X axis, so the camera stands on +X and looks along
		# it; the pool lands past the machine and its outline falls on lit
		# floor instead of on unlit rock.
		# aim at the machine itself, not at the floor beyond it: the pool is
		# huge and the machine is 0.58 m, so anything that frames the pool
		# nicely puts the subject off the edge
		look_at_from(Vector3(2.10, 0.30, 0.50), Vector3(0.0, 0.26, 0.0), 38.0)
		for k in range(6):
			await RenderingServer.frame_post_draw
		srcs.append(sub.get_texture().get_image())
	# the crop is the machine's own box, CENTRED -- not the top-left corner,
	# and not a brightness threshold: in a backlit frame the brightest thing in
	# the picture is the pool, not the machine.
	var cw := 760
	var chh := 428
	# The crop is the MACHINE's box, found by eye against the source frame that
	# is saved beside the ladder -- not the frame centre, and not a brightness
	# threshold: in a backlit frame the brightest thing is the pool.
	var reg := Rect2i(430, (H - chh) / 2 - 168, cw, chh)
	var rungs := [9, 14, 22, 34, 56, 90]
	var cell := 210
	var sheet := Image.create(cell * srcs.size(), 760, false, Image.FORMAT_RGB8)
	sheet.fill(Color(0.055, 0.055, 0.062))
	for ci in range(srcs.size()):
		var full: Image = srcs[ci]
		var src: Image = full.get_region(reg)
		var y := 14
		for r in rungs:
			var c: Image = src.duplicate()
			var w: int = int(round(float(r) * float(cw) / float(chh)))
			c.resize(w, r, Image.INTERPOLATE_LANCZOS)
			# nearest-upscaled, so nine pixels is actually visible on a sheet
			var k: int = maxi(1, int(floor(float(cell - 16) / float(w))))
			c.resize(w * k, r * k, Image.INTERPOLATE_NEAREST)
			sheet.blit_rect(c, Rect2i(0, 0, mini(c.get_width(), cell - 12), c.get_height()),
							Vector2i(ci * cell + 6, y))
			y += r * k + 12
	sheet.save_png(ProjectSettings.globalize_path(SHOT_DIR + "15_nine_pixels.png"))
	# and the source frames, so the ladder can be checked against them
	srcs[1].get_region(reg).save_png(ProjectSettings.globalize_path(SHOT_DIR + "15b_nine_pixels_source.png"))
	var line := "15_nine_pixels               ladder 9/14/22/34/56/90 px, columns: " + ", ".join(labels)
	stats_lines.append(line)
	print(line)


# ===========================================================================
# THE WALK CYCLES
# ===========================================================================
func _sequences() -> void:
	await _seq("walk_side", "surveyor", "walk", "side", false)
	await _seq("walk_front", "surveyor", "walk", "front", false)
	await _seq("walk_broken", "surveyor", "walk", "side", true)
	await _seq("trot_side", "scout", "trot", "side", false)
	await _seq("hauler_side", "hauler", "walk", "side", false)


func _seq(name: String, ch: String, clip: String, view: String, rough: bool) -> void:
	var dir: String = SHOT_DIR + "seq/" + name + "/"
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(dir))
	clear_machines()
	_build_ground("broken" if rough else "flat")
	rig_clear()
	var m := add_machine(ch, Vector3(-1.4, 0, 0), 0.0)
	m.set_walking(true, clip)
	settle(40)
	# one full cycle: the clip was exported as exactly one period
	var frames := 18 if clip == "walk" else 16
	var seq_imgs := []
	for k in range(frames):
		m.advance(1.0 / 30.0)
		var p: Vector3 = m.global_position
		var L: float = Book.hull_len(ch)
		if view == "side":
			look_at_from(p + Vector3(0.02, 0.26, L * 2.35), p + Vector3(0.02, 0.22, 0), 40.0)
		else:
			look_at_from(p + Vector3(L * 3.1, 0.30, 0.02), p + Vector3(0, 0.22, 0), 34.0)
		for j in range(3):
			await RenderingServer.frame_post_draw
		var img: Image = sub.get_texture().get_image()
		img.resize(1280, 720, Image.INTERPOLATE_LANCZOS)
		img.save_png(ProjectSettings.globalize_path(dir + "f%02d.png" % k))
		seq_imgs.append(img)
	# a contact sheet, because eight frames side by side is how a cycle is read
	var cols := 4
	var rows := 2
	var cw := 1920 / cols
	var chh := int(round(float(cw) * 9.0 / 16.0))
	var sheet := Image.create(1920, chh * rows, false, Image.FORMAT_RGB8)
	sheet.fill(Color(0.08, 0.08, 0.09))
	for i in range(cols * rows):
		var src: Image = seq_imgs[int(round(float(i) * float(frames - 1) / float(cols * rows - 1)))].duplicate()
		src.resize(cw, chh, Image.INTERPOLATE_LANCZOS)
		sheet.blit_rect(src, Rect2i(0, 0, cw, chh), Vector2i((i % cols) * cw, (i / cols) * chh))
	sheet.save_png(ProjectSettings.globalize_path(SHOT_DIR + "sheet_" + name + ".png"))
	var line := "seq/%-14s %d frames 1280x720 + sheet_%s.png (one full %s cycle, %s)" % [
		name, frames, name, clip, ch]
	stats_lines.append(line)
	print(line)
	# per-machine cost, measured on the last frame of the sequence
	stats_lines.append("   %-9s tris=%-7d surfaces=%d bones=%-3d build=%.0f ms" % [
		ch, m.tri_count, m.draw_surfaces, m.bone_count, m.build_ms])
