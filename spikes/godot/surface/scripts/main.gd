extends Node3D
##
## Blindside - surface (pit-head) procedural spike.
##
##   godot --path spikes/godot/surface --resolution 1920x1080 -- --mode=free
##   ... --mode=shots            capture the shot list to shots/ and quit
##   ... --mode=bench --secs=45  fly the camera and log to perf/ and quit
##   ... --seed=N --light=overcast|rain|dusk
##
## The generator is in two halves and they are in separate files:
##   layout.gd   integers only, no floats, no dict iteration  -> blindside-gen
##   dressing.gd / props.gd / scatter.gd / ground.gd          -> client side
## Nothing in the second half may change a number produced by the first.

var L: SurfaceLayout
var B: Batcher
var W: Weather
var cam: Camera3D
var mode := "free"
var seedv := 20260908
var light_name := "overcast"
var bench_secs := 45.0
var only_shot := ""
var tag := "before"
var dbg := 0
## measurement switches, so the cost of each technique can be priced separately
var pom := 1.0
var skymode := "realtime"
var nrm := 1.0
var solid := 1.0
var ssao := true

var stats := {}
var frame_times: Array[float] = []
var t_run := 0.0
var samples: Array = []
var log_lines: Array[String] = []

# free-fly camera state
var yaw := 0.0
var pitch := 0.0
var speed := 12.0

# ------------------------------------------------------------- shot list
## Eight required frames plus five that argue the case. Each names its light.
var SHOTS := [
	{"n": "01_site_wide",      "p": Vector3(-52, 15.5, 41), "t": Vector3(2, 6, -2),    "fov": 58, "l": "overcast"},
	{"n": "02_headframe_sky",  "p": Vector3(-14.5, 1.38, -1.2), "t": Vector3(0.2, 10.6, -0.3), "fov": 58, "l": "overcast"},
	{"n": "03_yard_working",   "p": Vector3(-13.5, 1.75, 8.5), "t": Vector3(-22.5, 1.0, 4.0), "fov": 55, "l": "overcast"},
	{"n": "04_service_bay",    "p": Vector3(-17.4, 1.50, -1.6), "t": Vector3(-21.6, 1.05, -6.9), "fov": 60, "l": "overcast"},
	{"n": "05_course",         "p": Vector3(35.5, 1.58, 5.0), "t": Vector3(50.0, 0.85, -1.5), "fov": 62, "l": "overcast"},
	{"n": "06_shaft_mouth",    "p": Vector3(-1.5, 3.1, 2.6),  "t": Vector3(0.1, -1.6, 0.0), "fov": 62, "l": "overcast"},
	{"n": "07_underfoot",      "p": Vector3(-8.6, 0.38, 5.6), "t": Vector3(-6.9, -0.30, 3.9), "fov": 44, "l": "overcast"},
	{"n": "08_dusk_yard",      "p": Vector3(-13.5, 1.75, 8.5), "t": Vector3(-22.5, 1.0, 4.0), "fov": 55, "l": "dusk"},
	{"n": "09_sceptic_bench",  "p": Vector3(-18.2, 1.28, -4.2), "t": Vector3(-21.4, 0.98, -6.6), "fov": 46, "l": "overcast"},
	{"n": "10_sceptic_charge", "p": Vector3(-14.9, 1.02, 7.7), "t": Vector3(-24.2, 0.62, 5.9), "fov": 50, "l": "overcast"},
	{"n": "11_rain_collar",    "p": Vector3(-9.2, 1.52, 3.0),  "t": Vector3(0.8, 0.55, -0.4), "fov": 60, "l": "rain"},
	{"n": "12_yard_deep",      "p": Vector3(2.6, 1.85, 7.4), "t": Vector3(19.0, 3.2, 15.5), "fov": 62, "l": "overcast"},
	{"n": "13_dusk_wide",      "p": Vector3(-40, 11.0, 33),   "t": Vector3(0, 6, 0),  "fov": 58, "l": "dusk"},
	{"n": "15_course_high",    "p": Vector3(30.0, 17.0, 26.0), "t": Vector3(58.0, 0.0, -2.0), "fov": 55, "l": "overcast"},
	{"n": "16_collar_close",   "p": Vector3(-5.6, 1.55, 4.6),  "t": Vector3(0.6, 0.35, -0.4), "fov": 56, "l": "overcast"},
	{"n": "14_gate_road",      "p": Vector3(-40.0, 2.2, 6.5), "t": Vector3(-14.0, 3.0, 0.5), "fov": 58, "l": "overcast"},
]

## ---------------------------------------------------------------- PHOTOREAL
## The before/after pairs. Frozen poses: every one of these is captured from the
## SAME camera before and after the material work, so the pair is a fair test.
## Captured to shots/photoreal/<tag>/ by --mode=pshots --tag=before|after.
var PSHOTS := [
	{"n": "p01_underfoot_macro", "p": Vector3(-8.6, 0.38, 5.6), "t": Vector3(-6.9, -0.30, 3.9), "fov": 44, "l": "overcast"},
	{"n": "p02_underfoot_45",    "p": Vector3(-11.0, 1.40, 6.2), "t": Vector3(-9.6, 0.00, 4.8), "fov": 46, "l": "overcast"},
	{"n": "p03_yard_working",    "p": Vector3(-13.5, 1.75, 8.5), "t": Vector3(-22.5, 1.0, 4.0), "fov": 55, "l": "overcast"},
	{"n": "p04_hardstanding",    "p": Vector3(-25.0, 1.55, 14.0), "t": Vector3(-16.0, 0.10, 6.0), "fov": 52, "l": "overcast"},
	{"n": "p05_rain_underfoot",  "p": Vector3(-11.0, 1.40, 6.2), "t": Vector3(-9.6, 0.00, 4.8), "fov": 46, "l": "rain"},
	{"n": "p06_rain_collar",     "p": Vector3(-9.2, 1.52, 3.0),  "t": Vector3(0.8, 0.55, -0.4), "fov": 60, "l": "rain"},
	{"n": "p07_rusted_iron",     "p": Vector3(-5.10, 1.05, -4.60), "t": Vector3(-3.65, 1.55, -3.25), "fov": 42, "l": "overcast"},
	{"n": "p08_shaft_collar",    "p": Vector3(-5.6, 1.55, 4.6),  "t": Vector3(0.6, 0.35, -0.4), "fov": 56, "l": "overcast"},
	{"n": "p09_shaft_mouth",     "p": Vector3(-1.5, 3.1, 2.6),   "t": Vector3(0.1, -1.6, 0.0), "fov": 62, "l": "overcast"},
	{"n": "p10_site_wide",       "p": Vector3(-52, 15.5, 41),    "t": Vector3(2, 6, -2), "fov": 58, "l": "overcast"},
	{"n": "p11_road_kerb",       "p": Vector3(-34.0, 1.45, 4.2), "t": Vector3(-24.0, 0.05, 1.0), "fov": 50, "l": "overcast"},
	{"n": "p12_dusk_yard",       "p": Vector3(-13.5, 1.75, 8.5), "t": Vector3(-22.5, 1.0, 4.0), "fov": 55, "l": "dusk"},
]

## the camera path used by --mode=bench, chosen to hit every density regime
var PATH := [
	Vector3(-56, 14, 44), Vector3(-30, 4, 22), Vector3(-14, 1.7, 9),
	Vector3(-20, 1.6, 0), Vector3(-6, 1.6, 3), Vector3(2, 2.2, 8),
	Vector3(18, 2.4, 14), Vector3(34, 1.7, 6), Vector3(48, 1.7, -2),
	Vector3(30, 8, -14), Vector3(6, 6, -20), Vector3(-20, 9, -18),
	Vector3(-48, 12, -6), Vector3(-56, 14, 44),
]

func _ready() -> void:
	_parse_args()
	RenderingServer.global_shader_parameter_add("g_wet", RenderingServer.GLOBAL_VAR_TYPE_FLOAT, 0.3)
	DisplayServer.window_set_size(Vector2i(1920, 1080))
	_log("=== Blindside surface spike ===")
	_log("adapter        : %s" % RenderingServer.get_video_adapter_name())
	_log("api            : %s (%s)" % [RenderingServer.get_video_adapter_api_version(), RenderingServer.get_video_adapter_vendor()])
	_log("godot          : %s" % Engine.get_version_info()["string"])
	_log("seed           : %d" % seedv)

	# ---------------- LAYOUT (integers only)
	var t0 := Time.get_ticks_usec()
	L = SurfaceLayout.new(seedv)
	var t_layout := float(Time.get_ticks_usec() - t0) / 1000.0
	_log("layout hash    : %d" % L.plan["hash"])
	_log("layout ms      : %.2f" % t_layout)

	# ---------------- DRESSING (floats allowed, client side)
	var t1 := Time.get_ticks_usec()
	var gstats := Ground.build(L, self)
	if dbg == 9:
		for t in [[0,0],[-20,-2],[10,10],[-40,-40],[52,-46],[35,0]]:
			var xx: int = int(t[0]) * 1000
			var zz: int = int(t[1]) * 1000
			_log("probe %s on_pad=%s h=%d" % [str(t), str(L.on_pad(xx, zz)), L.ground_mm(xx, zz)])
		var gm: MeshInstance3D = null
		for c in get_children():
			if c is MeshInstance3D and c.name == "Ground":
				gm = c
		var arrs := gm.mesh.surface_get_arrays(0)
		var vv: PackedVector3Array = arrs[Mesh.ARRAY_VERTEX]
		var cc = arrs[Mesh.ARRAY_COLOR]
		_log("color array type: %s size %d" % [str(typeof(cc)), (cc.size() if cc != null else -1)])
		for i in [0, 5000, 12000, 18000, 20000, 25000]:
			if i < vv.size():
				_log("v[%d] = %s  col=%s" % [i, str(vv[i]), str(cc[i]) if cc != null else "nil"])
	if dbg > 0:
		for c in get_children():
			if c is MeshInstance3D and c.name == "Ground":
				(c.material_override as ShaderMaterial).set_shader_parameter("dbg", dbg)
	var t_ground := float(Time.get_ticks_usec() - t1) / 1000.0

	var t2 := Time.get_ticks_usec()
	B = Batcher.new()
	var D := Dressing.new(L, B)
	D.build()
	var t_inherited := float(Time.get_ticks_usec() - t2) / 1000.0

	var t3 := Time.get_ticks_usec()
	var P := Props.new(L, B)
	P.build()
	var t_brought := float(Time.get_ticks_usec() - t3) / 1000.0

	var t4 := Time.get_ticks_usec()
	var S := Scatter.new(L, B)
	S.build(self)
	var t_scatter := float(Time.get_ticks_usec() - t4) / 1000.0

	var t5 := Time.get_ticks_usec()
	var fstats := B.flush(self)
	var t_flush := float(Time.get_ticks_usec() - t5) / 1000.0

	if dbg == 10:
		var rows: Array = []
		for c in get_children():
			if c is MultiMeshInstance3D:
				var ab: AABB = c.multimesh.get_aabb()
				rows.append([ab.size.x * ab.size.z, c.name, str(ab), c.multimesh.instance_count])
		rows.sort_custom(func(a, b): return a[0] > b[0])
		for i in mini(14, rows.size()):
			_log("BIG %s n=%d %s" % [rows[i][1], rows[i][3], rows[i][2]])
	if dbg == 16:
		var counts := {}
		for c in get_children():
			var k := c.get_class()
			counts[k] = int(counts.get(k, 0)) + 1
		for k in counts:
			_log("child class %s x%d" % [k, counts[k]])
		for c2 in get_children():
			if not (c2 is MultiMeshInstance3D):
				_log("  node %s : %s" % [c2.name, c2.get_class()])
	if dbg == 15:
		for c in get_children():
			if c is MeshInstance3D and c.name == "Ground":
				var sm := StandardMaterial3D.new()
				sm.albedo_color = Color(1, 0, 0)
				sm.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
				sm.cull_mode = BaseMaterial3D.CULL_DISABLED
				c.material_override = sm
				_log("ground aabb %s" % str(c.mesh.get_aabb()))
				_log("surfaces %d  format %d" % [c.mesh.get_surface_count(), c.mesh.surface_get_format(0)])
	if dbg == 14:
		for c in get_children():
			if c is MultiMeshInstance3D:
				c.visible = false
			if c.name == "Decals":
				c.visible = false
	if dbg >= 4 and dbg <= 13 and dbg != 7 and dbg != 10:
		var hide_bucket := Batcher.DETAIL
		if dbg == 12:
			hide_bucket = Batcher.PROP
		elif dbg == 13:
			hide_bucket = Batcher.SITE
		for c in get_children():
			if c is MultiMeshInstance3D and c.get_meta("bucket", 0) == hide_bucket:
				c.visible = false
	# ---------------- occluders for the two things that hide the most
	_occluders()

	# ---------------- light and weather
	for gm in Mats.grounds():
		gm.set_shader_parameter("pom_lod", pom)
		gm.set_shader_parameter("nrm_lod", nrm)
	if solid < 0.5:
		for mid in ["iron", "iron_pale", "steel", "stone", "timber", "rock", "brick",
				"bone", "kitgrey", "galv", "alu", "ember", "rubber", "plastic",
				"amber", "screen", "glass", "weed", "gravel", "litter", "water"]:
			Mats.get_mat(mid).set_shader_parameter("detail_on", 0.0)
	W = Weather.new()
	W.setup(self, P.lights, skymode, ssao)
	for c in get_children():
		if c is MeshInstance3D and c.name == "Ground":
			W.ground_mat = c.material_override
	W.add_column_lights(self, L)
	W.apply(light_name)
	if dbg == 3:
		W.sun.shadow_enabled = false

	cam = Camera3D.new()
	cam.far = 900.0
	cam.near = 0.05
	add_child(cam)
	cam.position = Vector3(-52, 15.5, 41)
	cam.look_at(Vector3(2, 6, -2))
	cam.current = true

	var total := t_layout + t_ground + t_inherited + t_brought + t_scatter + t_flush
	_log("ground ms      : %.2f  (%d tris, %d verts)" % [t_ground, gstats["tris"], gstats["verts"]])
	_log("inherited ms   : %.2f" % t_inherited)
	_log("brought ms     : %.2f" % t_brought)
	_log("scatter ms     : %.2f" % t_scatter)
	_log("flush ms       : %.2f" % t_flush)
	_log("TOTAL GEN ms   : %.2f" % total)
	_log("prop instances : %d" % fstats["instances"])
	_log("multimeshes    : %d" % fstats["multimeshes"])
	_log("mm triangles   : %d" % fstats["tris"])
	_log("decals         : %d" % (S.decals[0] if S.decals.size() > 0 else 0))
	_log("mode           : %s   light: %s" % [mode, light_name])
	_log("pom            : %.1f   sky: %s   ssao: %s" % [pom, skymode, str(ssao)])
	stats = {"gen_ms": total, "instances": fstats["instances"], "mm": fstats["multimeshes"],
		"tris": fstats["tris"], "ground_tris": gstats["tris"]}

	if mode == "shots":
		_run_shots()
	elif mode == "pshots":
		_run_pshots()
	elif mode == "bench":
		set_process(true)

func _occluders() -> void:
	# The winding house and the container row hide most of the site from most of
	# the site. Two boxes, and occlusion culling does the rest.
	var boxes := [[Vector3(11.5, 2.6, -15.0), Vector3(11.0, 5.2, 10.0)],
		[Vector3(19.2, 2.5, 15.5), Vector3(6.0, 5.0, 17.0)],
		[Vector3(-19.0, 2.4, -3.0), Vector3(14.0, 4.8, 1.0)]]
	for b in boxes:
		var occ := OccluderInstance3D.new()
		var bo := BoxOccluder3D.new()
		bo.size = b[1]
		occ.occluder = bo
		occ.position = b[0]
		add_child(occ)

# ---------------------------------------------------------------- args
func _parse_args() -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--mode="):
			mode = a.substr(7)
		elif a.begins_with("--seed="):
			seedv = int(a.substr(7))
		elif a.begins_with("--light="):
			light_name = a.substr(8)
		elif a.begins_with("--secs="):
			bench_secs = float(a.substr(7))
		elif a.begins_with("--shot="):
			only_shot = a.substr(7)
		elif a.begins_with("--tag="):
			tag = a.substr(6)
		elif a.begins_with("--pom="):
			pom = float(a.substr(6))
		elif a.begins_with("--nrm="):
			nrm = float(a.substr(6))
		elif a.begins_with("--solid="):
			solid = float(a.substr(8))
		elif a.begins_with("--sky="):
			skymode = a.substr(6)
		elif a.begins_with("--ssao="):
			ssao = int(a.substr(7)) != 0
		elif a.begins_with("--dbg="):
			dbg = int(a.substr(6))

func _log(s: String) -> void:
	print(s)
	log_lines.append(s)

# ---------------------------------------------------------------- shots
func _run_shots() -> void:
	var dir := ProjectSettings.globalize_path("res://shots/")
	DirAccess.make_dir_recursive_absolute(dir)
	for s in SHOTS:
		if only_shot != "" and s["n"] != only_shot:
			continue
		W.apply(s["l"])
		cam.fov = s["fov"]
		cam.position = s["p"]
		cam.look_at(s["t"])
		# let culling, visibility ranges, particles AND THE SKY settle. The sky's
		# radiance map is PROCESS_MODE_INCREMENTAL - it converges to the quality
		# result over several dozen frames and costs nothing once it has, which
		# is worth 6 ms a frame - so a capture has to wait for it or the ambient
		# is still the unfiltered, far too bright, early pass.
		for i in 72:
			await RenderingServer.frame_post_draw
		var img := get_viewport().get_texture().get_image()
		var path: String = dir + str(s["n"]) + ".png"
		img.save_png(path)
		_log("shot %s  %s  fps=%.1f draws=%d prims=%d" % [s["n"], s["l"],
			Performance.get_monitor(Performance.TIME_FPS),
			int(Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME)),
			int(Performance.get_monitor(Performance.RENDER_TOTAL_PRIMITIVES_IN_FRAME))])
	_write_log("shots.txt")
	get_tree().quit()

func _run_pshots() -> void:
	var dir := ProjectSettings.globalize_path("res://shots/photoreal/%s/" % tag)
	DirAccess.make_dir_recursive_absolute(dir)
	for s in PSHOTS:
		if only_shot != "" and s["n"] != only_shot:
			continue
		W.apply(s["l"])
		cam.fov = s["fov"]
		cam.position = s["p"]
		cam.look_at(s["t"])
		W.rain.global_position = cam.position + Vector3(0, 6, 0)
		for i in 72:
			await RenderingServer.frame_post_draw
		var img := get_viewport().get_texture().get_image()
		img.save_png(dir + str(s["n"]) + ".png")
		_log("pshot %s  %s  fps=%.1f draws=%d prims=%d" % [s["n"], s["l"],
			Performance.get_monitor(Performance.TIME_FPS),
			int(Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME)),
			int(Performance.get_monitor(Performance.RENDER_TOTAL_PRIMITIVES_IN_FRAME))])
	_write_log("pshots_%s.txt" % tag)
	get_tree().quit()

# ---------------------------------------------------------------- bench
func _process(dt: float) -> void:
	if mode == "free":
		_free_fly(dt)
		return
	if mode != "bench":
		return
	t_run += dt
	# fly the path at constant speed
	var seg_time := bench_secs / float(PATH.size() - 1)
	var i := int(t_run / seg_time)
	if i >= PATH.size() - 1:
		_finish_bench()
		return
	var f := fmod(t_run, seg_time) / seg_time
	var p: Vector3 = PATH[i].lerp(PATH[i + 1], f)
	cam.position = p
	var look: Vector3 = PATH[(i + 2) % PATH.size()]
	cam.look_at(Vector3(look.x, look.y * 0.4 + 1.0, look.z))
	W.rain.global_position = p + Vector3(0, 6, 0)
	if t_run > 1.0:
		frame_times.append(dt * 1000.0)
		if frame_times.size() % 20 == 0:
			samples.append([t_run, dt * 1000.0,
				Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME),
				Performance.get_monitor(Performance.RENDER_TOTAL_PRIMITIVES_IN_FRAME),
				Performance.get_monitor(Performance.RENDER_TOTAL_OBJECTS_IN_FRAME),
				Performance.get_monitor(Performance.RENDER_VIDEO_MEM_USED),
				p.x, p.y, p.z])

func _finish_bench() -> void:
	frame_times.sort()
	var n := frame_times.size()
	if n == 0:
		get_tree().quit()
		return
	var sum := 0.0
	for f in frame_times:
		sum += f
	var mean := sum / float(n)
	var p50: float = frame_times[int(n * 0.50)]
	var p95: float = frame_times[int(n * 0.95)]
	var p99: float = frame_times[mini(int(n * 0.99), n - 1)]
	var worst: float = frame_times[n - 1]
	_log("")
	_log("--- sustained, %s light, 1920x1080, camera moving ---" % light_name)
	_log("frames         : %d over %.1f s" % [n, t_run])
	_log("mean frame     : %.2f ms   (%.1f fps)" % [mean, 1000.0 / mean])
	_log("median frame   : %.2f ms   (%.1f fps)" % [p50, 1000.0 / p50])
	_log("p95 frame      : %.2f ms   (%.1f fps)" % [p95, 1000.0 / p95])
	_log("p99 frame      : %.2f ms   (%.1f fps)" % [p99, 1000.0 / p99])
	_log("worst frame    : %.2f ms   (%.1f fps)" % [worst, 1000.0 / worst])
	var dmax := 0.0
	var pmax := 0.0
	var vmax := 0.0
	var omax := 0.0
	for s in samples:
		dmax = maxf(dmax, s[2])
		pmax = maxf(pmax, s[3])
		omax = maxf(omax, s[4])
		vmax = maxf(vmax, s[5])
	_log("draw calls max : %d" % int(dmax))
	_log("primitives max : %d" % int(pmax))
	_log("objects max    : %d" % int(omax))
	_log("video mem      : %.1f MB" % (vmax / 1048576.0))
	_log("gen ms         : %.2f" % stats["gen_ms"])
	_log("instances      : %d" % stats["instances"])
	_write_log("bench_%s.txt" % light_name)
	var csv := "t_s,frame_ms,draw_calls,primitives,objects,video_mem,x,y,z\n"
	for s in samples:
		csv += "%.3f,%.3f,%d,%d,%d,%d,%.1f,%.1f,%.1f\n" % [s[0], s[1], int(s[2]), int(s[3]), int(s[4]), int(s[5]), s[6], s[7], s[8]]
	var f2 := FileAccess.open(ProjectSettings.globalize_path("res://perf/frames_%s.csv" % light_name), FileAccess.WRITE)
	if f2:
		f2.store_string(csv)
		f2.close()
	get_tree().quit()

func _write_log(name: String) -> void:
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path("res://perf/"))
	var f := FileAccess.open(ProjectSettings.globalize_path("res://perf/" + name), FileAccess.WRITE)
	if f:
		f.store_string("\n".join(log_lines) + "\n")
		f.close()

# ---------------------------------------------------------------- free fly
func _free_fly(dt: float) -> void:
	var v := Vector3.ZERO
	if Input.is_key_pressed(KEY_W): v.z -= 1
	if Input.is_key_pressed(KEY_S): v.z += 1
	if Input.is_key_pressed(KEY_A): v.x -= 1
	if Input.is_key_pressed(KEY_D): v.x += 1
	if Input.is_key_pressed(KEY_E): v.y += 1
	if Input.is_key_pressed(KEY_Q): v.y -= 1
	var sp := speed * (4.0 if Input.is_key_pressed(KEY_SHIFT) else 1.0)
	cam.translate(v.normalized() * sp * dt)
	W.rain.global_position = cam.global_position + Vector3(0, 6, 0)

func _unhandled_input(e: InputEvent) -> void:
	if e is InputEventMouseMotion and Input.get_mouse_mode() == Input.MOUSE_MODE_CAPTURED:
		yaw -= e.relative.x * 0.003
		pitch = clampf(pitch - e.relative.y * 0.003, -1.5, 1.5)
		cam.rotation = Vector3(pitch, yaw, 0)
	elif e is InputEventMouseButton and e.pressed:
		Input.set_mouse_mode(Input.MOUSE_MODE_CAPTURED)
	elif e is InputEventKey and e.pressed:
		if e.keycode == KEY_ESCAPE:
			Input.set_mouse_mode(Input.MOUSE_MODE_VISIBLE)
		elif e.keycode == KEY_1:
			W.apply("overcast")
		elif e.keycode == KEY_2:
			W.apply("rain")
		elif e.keycode == KEY_3:
			W.apply("dusk")
		elif e.keycode == KEY_F2:
			_snap()

func _snap() -> void:
	await RenderingServer.frame_post_draw
	var dir := ProjectSettings.globalize_path("res://shots/")
	DirAccess.make_dir_recursive_absolute(dir)
	var img := get_viewport().get_texture().get_image()
	img.save_png(dir + "free_%d.png" % Time.get_ticks_msec())
	print("snap at ", cam.position, " -> ", cam.position + cam.global_transform.basis.z * -8.0)
