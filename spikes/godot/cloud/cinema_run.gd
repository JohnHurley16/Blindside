# ---------------------------------------------------------------------------
# BLINDSIDE -- running the belief side of the trailer.
#
#   --cinema=validate   every shot against the rules; nothing is repaired
#   --cinema=seq        the executing shots as image sequences
#   --cinema=match      the matched-camera test: the belief frame at the exact
#                       pose the cave rig recorded, plus the residual in mm
#   --cinema=pairs      before/after for every post effect, one pose
#   --cinema=stack      the surviving stack on and off
#   --cinema=fail       the three deliberate failures and what they would ship
#   --cinema=cost       leave-one-out GPU timing, interleaved
#   --fx=a+b+c          any subset, or all / none / keep
# ---------------------------------------------------------------------------
extends RefCounted
class_name CloudCinema

const DIR := "res://shots/cinema/"
const SETTLE: int = 6

# TRAILER.md 11.3. A shot is its own length, and the length is in the shot.
# Every sequence in this directory used to be 24 frames whatever `len_s` said,
# which is one second at 24 fps -- so a 4 s push was rendered as a 4x speed-up
# and the belief cut, which is the trailer's signature, flashed past. The rate
# is the rate the frames are CUT at; `capfps` below is a different number and
# stays 60, because that is the shutter the finished shot has and it is what
# the motion-blur reprojection is computed against. Ported from the cave rig,
# which fixed the same fault in the same words (cave_root.gd `_cin_seq`).
const CUT_FPS: float = 24.0

# The cave spike's generator parameters. These two integers ARE the camera
# match: see cinema.gd and CINEMA.md 2.
var cave_seed: int = 7
var cave_len: int = 240

var mode: String = ""
var fx: String = "keep"
var only: String = ""
var seqframes: int = 0        # 0 = derive from len_s at CUT_FPS; --seqframes= forces a count
var capfps: float = 60.0

var rig: CloudRig
var grade: BeliefGrade
var shots: Array = []
var fx_mask: int = 0
var report: PackedStringArray = PackedStringArray()
var r                                     # the lidar root node
var baked: String = ""


func parse_args(root) -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--cinema="): mode = a.substr(9)
		elif a.begins_with("--fx="): fx = a.substr(5)
		elif a.begins_with("--shot="): only = a.substr(7)
		elif a.begins_with("--seqframes="): seqframes = int(a.substr(12))
		elif a.begins_with("--caveseed="): cave_seed = int(a.substr(11))
		elif a.begins_with("--cavelen="): cave_len = int(a.substr(10))
		elif a == "--ground=local": ground_local = true


# HOW A MATCHED SHOT'S HEIGHT IS RESOLVED, and it is the one thing in the shot
# format that does not cross the project boundary.
#
#   default          the cave rig's own resolved floor, carried in the shot as
#                    ground_from / ground_to and read out of
#                    cave/shots/cinema/sequences.txt. MEASURED: reproduces the
#                    cave's recorded world position to 5 mm RMS, which is
#                    inside the 10 mm the cave's log prints at.
#   --ground=local   resolve `u` against THIS project's own floor, the way the
#                    cave rig resolves it against the cave's. The shot's own
#                    words are honoured and the coordinate is not: MEASURED at
#                    167 mm RMS and 268 mm worst, every millimetre of it in Y.
#
# Both are rendered -- shots/cinema/match/ and match_local/ -- and CINEMA.md 2
# is the argument for shipping the first.
var ground_local: bool = false


func say(s: String) -> void:
	print(s)
	report.append(s)


func flush(fname: String) -> void:
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(DIR))
	var f := FileAccess.open(DIR + fname, FileAccess.WRITE)
	if f:
		for l in report:
			f.store_line(l)
		f.close()
	report.clear()


func run(root) -> void:
	r = root
	for d in ["", "seq", "pairs", "match", "fail", "stack"]:
		DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(DIR + d))
	rig = CloudRig.new()
	rig.setup(r.geo, r)
	grade = BeliefGrade.new()
	grade.setup(_env(), r.cam)
	fx_mask = BeliefGrade.parse(fx)
	r.cam.keep_aspect = Camera3D.KEEP_HEIGHT
	r.cam_driven = true
	r.show_lines = false
	r.show_hud = false
	_load()
	print("cinema        : mode=%s fx=%s  cave seed %d len %d  %d shots" % [
		mode, BeliefGrade.mask_str(fx_mask), cave_seed, cave_len, shots.size()])
	match mode:
		"validate": await _validate()
		"seq": await _seq()
		"match": await _match()
		"pairs": await _pairs()
		"stack": await _stack()
		"fail": await _fail()
		"cost": await _cost()
		"tune": await _tune()
		"bloom": await _bloom()
		"hero": await _hero()
		_: print("cinema: unknown mode ", mode)


func _env() -> Environment:
	for c in r.get_children():
		if c is WorldEnvironment:
			return (c as WorldEnvironment).environment
	return null


func _load() -> void:
	var txt: String = FileAccess.get_file_as_string("res://shots_cinema.json")
	var v = JSON.parse_string(txt)
	shots = v if v is Array else []
	if ground_local:
		for s in shots:
			(s as Dictionary).erase("ground_from")
			(s as Dictionary).erase("ground_to")
	if only != "":
		var keep: Array = []
		for s in shots:
			if String(s["name"]).contains(only):
				keep.append(s)
		shots = keep


func named(n: String) -> Dictionary:
	for s in shots:
		if String(s["name"]) == n:
			return s
	return {}


# ---------------------------------------------------------------------------
# the bake a shot asks for, and the view state it asks for
# ---------------------------------------------------------------------------
func _ensure_scene(shot: Dictionary) -> void:
	var key: String = String(shot.get("scene", "cine_stand")) + "|" + JSON.stringify(shot.get("cine", {}))
	if key == baked:
		return
	r.cine_spec = shot.get("cine", {})
	r._bake(String(shot.get("scene", "cine_stand")))
	baked = key
	rig.set_cloud_bounds(r.cloud_min, r.cloud_max)


func _view(shot: Dictionary) -> void:
	# the spike's own defaults, then whatever the shot overrides
	r.mode = 0
	r.gain = 1.0
	r.pt_world = 0.020
	r.min_px = 1.6
	r.max_px = 3.6
	r.square = 0.0
	r.footprint = 0.0
	r.age_knee = 90.0
	r.age_floor = 0.42
	r.epoch_split = -1.0
	r.clip_lo = -1000.0
	r.clip_hi = 1000.0
	r.h_lo = r.cloud_min.y
	r.h_hi = r.cloud_max.y
	r.show_truth = bool(shot.get("truth", false))
	r.truth_exposure = float(shot.get("truth_exposure", 0.32))
	var v: Dictionary = shot.get("view", {})
	for k in v.keys():
		if k == "clip_rel_hi":
			r.clip_hi = r.geo._st_pos(r.geo.topo.edges[0][int((shot.get("cine", {}) as Dictionary).get("st", 70))]).y \
				+ float(v[k])
		elif k == "clip_rel_lo":
			r.clip_lo = r.geo._st_pos(r.geo.topo.edges[0][int((shot.get("cine", {}) as Dictionary).get("st", 70))]).y \
				+ float(v[k])
		else:
			r.set(k, v[k])


func _pose(shot: Dictionary, tn: float, fi: int) -> Dictionary:
	var ps: Dictionary = rig.pose(shot, tn)
	r.cam.global_transform = Transform3D(ps["basis"], ps["pos"])
	r.cam.fov = CloudRig.fov_for(float(ps["lens"]))
	r.now = rig.scrub(shot, tn, r.t_end)
	grade.apply(fx_mask, r.cam, float(ps["lens"]), float(ps["tstop"]), float(ps["focus"]))
	# The previous SHOT frame at the true capture rate, not the previously
	# rendered one -- offline capture renders each frame several times to let
	# the buffers settle, so "last frame" is the same pose and the blur would
	# be exactly zero. The cave rig does the same thing for the same reason.
	var dt: float = (1.0 / capfps) / maxf(float(shot["len_s"]), 0.01)
	var pp: Dictionary = rig.pose(shot, maxf(tn - dt, 0.0))
	grade.lens.use_external_prev = true
	grade.lens.external_prev = Transform3D(pp["basis"], pp["pos"])
	grade.lens.seedt = float(fi) * 7.31 + 0.5
	return ps


func _grab(path: String) -> void:
	for k in range(SETTLE):
		r._apply_uniforms()
		await RenderingServer.frame_post_draw
	var img: Image = r.get_viewport().get_texture().get_image()
	img.save_png(ProjectSettings.globalize_path(path))


func _gpu_median(n: int) -> float:
	# Godot does not measure a viewport unless it is asked to, and it returns
	# 0.00 ms for ever if you forget. The first cost table this produced was
	# nine rows of zeroes and it looked like a result.
	RenderingServer.viewport_set_measure_render_time(r.get_viewport().get_viewport_rid(), true)
	var v: Array = []
	for i in range(n):
		await RenderingServer.frame_post_draw
		if i >= 8:
			v.append(RenderingServer.viewport_get_measured_render_time_gpu(
				r.get_viewport().get_viewport_rid()))
	v.sort()
	return v[v.size() / 2] if v.size() > 0 else 0.0


# ---------------------------------------------------------------------------
# 1. validation
# ---------------------------------------------------------------------------
func _validate() -> void:
	await r.get_tree().physics_frame
	await r.get_tree().physics_frame
	rig.ready_space(r)
	say("=== BELIEF SHOT VALIDATION -- TRAILER.md 8, cinema.gd ===")
	say(Hero.banner())
	say("cave datum: seed %d, %d cells, %d stations, topology hash 0x%s" % [
		cave_seed, cave_len, r.geo.topo.stations.size(),
		String.num_int64(r.geo.topo.content_hash(), 16)])
	say("body sphere %.2f m, near clearance %.2f m, query margin %.2f m" % [
		CloudRig.BODY_R, CloudRig.NEAR_CLEAR, CloudRig.QUERY_MARGIN])
	say("collision: the TRUTH geometry, and it is the same mesh the sensor raycasts.")
	say("   laser  layer 1  %d triangles in %d bodies -- everything, litter included" % [
		r.geo.tri_total, LidarGeo.N_SURF])
	say("   camera layer 2  %d triangles in 1 body   -- everything except loose scatter" % [
		r.geo.cam_tris])
	say("            A 40 mm chip casts a return and a shadow and is not an obstacle;")
	say("            spikes/godot/cave/cinema.gd 4.1 says so and this is the port of it.")
	say("")
	var npass: int = 0
	for s in shots:
		# A world shot is validated against the truth geometry, which exists
		# the moment the project loads; only a survey shot needs the cloud
		# baked, because rule 9 is about the cloud's own extent.
		if String(s.get("frame", "world")) == "survey":
			_ensure_scene(s)
			rig.set_cloud_bounds(r.cloud_min, r.cloud_max)
		var res: Dictionary = rig.validate(s)
		var st: Dictionary = res["stats"]
		var dof: Array = st["dof"]
		say("%-26s trailer %-3s  %s   [%s]" % [res["name"], str(s.get("trailer", "-")),
			"PASS" if res["ok"] else "REJECTED", st["frame"]])
		say("   %.0f mm (%.1f deg v)  T%.1f  %.1fs  ease %s  handheld %.2f deg" % [
			float(s["lens_mm"]), float(st["fov"]), float(s.get("tstop", 2.8)),
			float(s["len_s"]), str(s.get("ease", "inout")), float(s.get("handheld_deg", 0.0))])
		if String(st["frame"]) == "world":
			say("   travel %.2f m  peak %.2f m/s  clearance %.2f m  height %.2f-%.2f m (%s)" % [
				st["travel"], st["vmax"], st["clear"], st["h_lo"], st["h_hi"],
				str(s.get("height", "eye"))])
		else:
			say("   travel %.2f m  peak %.2f m/s  no body; %.2f m clear of the cloud's extent" % [
				st["travel"], st["vmax"], -float(st["in_cloud"])])
		var far_s: String = "infinity" if float(dof[1]) > 1e6 else ("%.2f m" % float(dof[1]))
		say("   depth of field: sharp %.2f m to %s (hyperfocal %.1f m)" % [dof[0], far_s, dof[2]])
		say("   machine: %s" % Hero.describe(Hero.block(s)))
		if s.has("_same_camera_as"):
			say("   MATCHED to %s -- camera fields are a verbatim copy." % str(s["_same_camera_as"]))
			say("   The cave rig's verdict governs a matched shot; this one agrees with it.")
		for w in res["warn"]:
			say("   WARN: " + str(w))
		for f2 in res["fail"]:
			say("   FAIL: " + str(f2))
		if not res["ok"] and String(st["frame"]) == "world":
			for t in [0.0, 0.5, 1.0]:
				var ps: Dictionary = rig.pose(s, t)
				var p: Vector3 = ps["pos"]
				var ov: PackedVector3Array = rig.overlap_points(p)
				var s2: String = "   at t=%.1f  cam y %.2f  floor %.2f m below  head %.2f m" % [
					t, p.y, rig.floor_under(p), rig.head_room(p)]
				if ov.size() > 0:
					s2 += "  touching %d point(s) on [%s], first at y %.2f" % [
						ov.size(), rig.overlap_who(p), ov[0].y]
				say(s2)
		say("")
		if res["ok"]:
			npass += 1
	say("%d of %d shots execute; %d rejected." % [npass, shots.size(), shots.size() - npass])
	say("")
	# The check a single shot cannot make: every hero block in the file against
	# the one declaration and against each other. In the assembly this is run
	# over all three projects' shot files at once, which is the check TRAILER
	# 11.1 actually asks for, since the drift it names is BETWEEN projects.
	var au: Array[String] = Hero.audit(shots, "cloud")
	if au.is_empty():
		say("HERO AUDIT: every machine block in this file is the one machine.")
	else:
		for l in au:
			say("HERO AUDIT: " + l)
	flush("validation.txt")


# ---------------------------------------------------------------------------
# 2. the executing shots, as sequences
# ---------------------------------------------------------------------------
func _seq() -> void:
	await r.get_tree().physics_frame
	rig.ready_space(r)
	for shot in shots:
		if String(shot["name"]).begins_with("xfail"):
			continue
		_ensure_scene(shot)
		rig.set_cloud_bounds(r.cloud_min, r.cloud_max)
		var res: Dictionary = rig.validate(shot)
		if not res["ok"]:
			say("SKIP %s -- rejected: %s" % [shot["name"], "; ".join(res["fail"])])
			continue
		_view(shot)
		var dir: String = DIR + "seq/" + String(shot["name"]) + "/"
		DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(dir))
		var n: int = seqframes
		if n <= 0:
			n = maxi(24, int(round(float(shot.get("len_s", 1.0)) * CUT_FPS)))
		var t_shot: int = Time.get_ticks_msec()
		say("=== %s  %.0f mm  %.1f s  %d frames at %.0f fps  %d returns ===" % [shot["name"],
			float(shot["lens_mm"]), float(shot["len_s"]), n, CUT_FPS, r.n_pts])
		say("    machine: %s" % Hero.describe(Hero.block(shot)))
		say("  frame     t_s      x       y       z    step_mm   focus_m   belief_t")
		var prev: Vector3 = Vector3.ZERO
		for i in range(n):
			var tn: float = float(i) / float(n - 1)
			var ps: Dictionary = _pose(shot, tn, i)
			await _grab(dir + "%03d.png" % i)
			var p: Vector3 = ps["pos"]
			var step: float = 0.0 if i == 0 else p.distance_to(prev) * 1000.0
			say("  %5d  %6.3f  %6.2f  %6.2f  %6.2f  %8.1f  %7.2f  %8.2f" % [
				i, tn * float(shot["len_s"]), p.x, p.y, p.z, step,
				float(ps["focus"]), r.now])
			prev = p
		var el: float = float(Time.get_ticks_msec() - t_shot) / 1000.0
		say("    %d frames in %.1f s = %.2f s/frame" % [n, el, el / float(n)])
		say("")
	flush("sequences.txt")


# ---------------------------------------------------------------------------
# 3. THE MATCHED-CAMERA TEST
#
# The cave spike recorded the world position of every frame of t17 and t20 in
# shots/cinema/sequences.txt. This renders the belief frame at the pose THIS
# rig computes for the same shot definition, and prints the residual against
# the cave's own numbers. Position is the whole of the claim: if the two rigs
# disagree about where the camera is, nothing else matters.
# ---------------------------------------------------------------------------
const CAVE_SEQ := "../cave/shots/cinema/sequences.txt"

func _cave_track(shot_name: String) -> Array:
	var path: String = ProjectSettings.globalize_path("res://") + CAVE_SEQ
	if not FileAccess.file_exists(path):
		return []
	var txt: String = FileAccess.get_file_as_string(path)
	var out: Array = []
	var inside: bool = false
	for line in txt.split("\n"):
		var l: String = line.strip_edges()
		if l.begins_with("==="):
			inside = l.contains(shot_name)
			continue
		if not inside or l == "" or l.begins_with("frame"):
			continue
		var parts: PackedStringArray = l.split(" ", false)
		if parts.size() < 7 or not parts[0].is_valid_int():
			continue
		# Every column of a frame line is a number. The cave's log now ends each
		# shot with "    96 frames in 56.2 s = 0.59 s/frame", which also starts
		# with an integer and also has more than seven fields -- it parsed as a
		# 97th frame at (0, 56.2, 0) and took the residual from 5 mm to 7.8 m.
		# That is TRAILER-side 9.3's staleness problem arriving through the LOG
		# rather than through the shot file: the cave changed its own format for
		# a good reason and nothing here failed, it just answered wrongly.
		var ok: bool = true
		for c in range(1, 7):
			if not parts[c].is_valid_float():
				ok = false
				break
		if not ok:
			continue
		out.append(Vector3(float(parts[2]), float(parts[3]), float(parts[4])))
	return out


func _match() -> void:
	await r.get_tree().physics_frame
	rig.ready_space(r)
	say("=== THE MATCHED-CAMERA TEST ===")
	say("Ground truth is the cave spike's own recorded track,")
	say("spikes/godot/cave/shots/cinema/sequences.txt, printed at 10 mm.")
	say("")
	for pair in [["t18_belief_cut", "t17_follow_machine"], ["t20_sensor_shadow", "t20_sensor_shadow"]]:
		var shot: Dictionary = named(String(pair[0]))
		if shot.is_empty():
			continue
		var track: Array = _cave_track(String(pair[1]))
		_ensure_scene(shot)
		_view(shot)
		var dir: String = DIR + "match/" + String(shot["name"]) + "/"
		DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(dir))
		say("--- %s   vs cave %s   (%d recorded frames) ---" % [shot["name"], pair[1], track.size()])
		say("  frame      belief x/y/z            cave x/y/z          dx    dy    dz   |d| mm")
		var worst: float = 0.0
		var sum2: float = 0.0
		var n: int = maxi(track.size(), 1)
		for i in range(n):
			var tn: float = float(i) / float(maxi(n - 1, 1))
			var ps: Dictionary = _pose(shot, tn, i)
			var p: Vector3 = ps["pos"]
			if i < track.size():
				var q: Vector3 = track[i]
				var d: Vector3 = (p - q) * 1000.0
				worst = maxf(worst, d.length())
				sum2 += d.length_squared()
				say("  %5d  %7.2f %6.2f %7.2f   %7.2f %6.2f %7.2f  %5.0f %5.0f %5.0f  %6.0f" % [
					i, p.x, p.y, p.z, q.x, q.y, q.z, d.x, d.y, d.z, d.length()])
			if i == 0 or i == n / 2 or i == n - 1:
				await _grab(dir + "%03d.png" % i)
		say("  RMS %.0f mm, worst %.0f mm" % [sqrt(sum2 / float(n)), worst])
		say("")
	flush("match.txt")


# ---------------------------------------------------------------------------
# 4. the post stack, one effect at a time
# ---------------------------------------------------------------------------
func _pairs() -> void:
	await r.get_tree().physics_frame
	rig.ready_space(r)
	say("=== POST, ONE EFFECT AT A TIME ===")
	say("EACH EFFECT ALONE against nothing, not cumulative. The cave's pairs are")
	say("cumulative because they are building a look; the question here is a RULE")
	say("test -- does this effect merge rings, and does it put light into a sensor")
	say("shadow -- and a cumulative stack answers it about the stack rather than")
	say("about the effect. Measured cumulatively first, and the depth-of-field row")
	say("destroyed the void that every later row was then measured against.")
	say("")
	for spec in [["t18_belief_cut", 0.55, "w", "close, machine height, in the drive"],
				 ["t19_cloud_building", 0.90, "b", "eye height, a retroreflector in frame"],
				 ["t26_the_fold", 0.90, "s", "the survey register, plan, accumulated"]]:
		var shot: Dictionary = named(String(spec[0]))
		if shot.is_empty():
			continue
		_ensure_scene(shot)
		_view(shot)
		var tag: String = String(spec[2])
		say("--- %s%s at t=%.2f: %s" % [tag, "", float(spec[1]), str(spec[3])])
		var i: int = 0
		for nm in BeliefGrade.ORDER:
			fx_mask = 0
			_pose(shot, float(spec[1]), 3)
			await _grab(DIR + "pairs/%s%02d_%s_off.png" % [tag, i, nm])
			fx_mask = int(BeliefGrade.NAMES[nm])
			_pose(shot, float(spec[1]), 3)
			await _grab(DIR + "pairs/%s%02d_%s_on.png" % [tag, i, nm])
			i += 1
		say("    %s" % ", ".join(BeliefGrade.ORDER))
	fx_mask = BeliefGrade.parse(fx)
	say("")
	say("w** = t18 close in the drive, b** = t19 with a retro plate,")
	say("s** = t26 the survey register. beliefcheck.py pairs <dir> measures them.")
	flush("pairs.txt")


func _stack() -> void:
	await r.get_tree().physics_frame
	rig.ready_space(r)
	for nm in ["t18_belief_cut", "t20_sensor_shadow", "t26_the_fold"]:
		var shot: Dictionary = named(nm)
		if shot.is_empty():
			continue
		_ensure_scene(shot)
		_view(shot)
		fx_mask = 0
		_pose(shot, 0.5, 3)
		await _grab(DIR + "stack/%s_off.png" % nm)
		fx_mask = BeliefGrade.KEEP
		_pose(shot, 0.5, 3)
		await _grab(DIR + "stack/%s_on.png" % nm)
		say("%s: off = nothing, on = %s" % [nm, BeliefGrade.mask_str(BeliefGrade.KEEP)])
	fx_mask = BeliefGrade.parse(fx)
	flush("stack.txt")


# ---------------------------------------------------------------------------
# 5. the deliberate failures
# ---------------------------------------------------------------------------
func _fail() -> void:
	await r.get_tree().physics_frame
	rig.ready_space(r)
	say("=== THE DELIBERATE FAILURES ===")
	fx_mask = BeliefGrade.KEEP
	for nm in ["xfail_through_the_wall", "xfail_survey_draws_truth", "xfail_into_the_cloud"]:
		var shot: Dictionary = named(nm)
		if shot.is_empty():
			continue
		_ensure_scene(shot)
		rig.set_cloud_bounds(r.cloud_min, r.cloud_max)
		var res: Dictionary = rig.validate(shot)
		say("")
		say("%s: %s" % [nm, "PASS -- THE RULE DID NOT FIRE" if res["ok"] else "REJECTED"])
		say("  why authored: %s" % str(shot.get("_why", "")))
		for f2 in res["fail"]:
			say("  FAIL: " + str(f2))
		# photograph the end of the move: what would have shipped
		_view(shot)
		if bool(shot.get("truth", false)):
			r.show_truth = true
		for t in [0.0, 1.0]:
			_pose(shot, t, 3)
			await _grab(DIR + "fail/%s_%s.png" % [nm, "a_start" if t == 0.0 else "b_end"])
		say("  frames: fail/%s_a_start.png and _b_end.png -- the second is what" % nm)
		say("          would have shipped if the rule had not fired.")
	fx_mask = BeliefGrade.parse(fx)
	say("")
	say("The rig does not move a camera to a legal place and it does not stop")
	say("short. It rejects the shot and names the number that rejected it.")
	flush("failure.txt")


# ---------------------------------------------------------------------------
# 7. tuning the RECENCY WINDOW, which is the one presentation choice this
# register has that the cave's does not.
#
# The cave frame is legible because a lamp lights a cone and everything outside
# it is black. Belief has no lamp: every return ever taken is drawn at its own
# reflectance, so a camera standing inside an accumulated map sees a solid
# fabric of rings in every direction and the passage stops being a passage.
#
# The honest exposure control here is AGE, which ART-DIRECTION 8.2 already
# mandates ("an old return is dimmer and stays where it was believed to be").
# Turning the knee down to a couple of seconds makes the live sweep the subject
# and leaves the accumulated map as a dim ground. It is not a fade: the old
# returns are still there, still where they were believed to be.
# ---------------------------------------------------------------------------
func _tune() -> void:
	await r.get_tree().physics_frame
	rig.ready_space(r)
	var shot: Dictionary = named("t18_belief_cut")
	_ensure_scene(shot)
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(DIR + "tune"))
	say("=== RECENCY WINDOW, %s at t=0.50, %d returns ===" % [shot["name"], r.n_pts])
	say("knee = seconds to the age floor; floor = what an old return keeps.")
	for v in [[90.0, 1.00, 3.6], [26.0, 0.55, 3.6], [9.0, 0.22, 2.6],
			  [3.2, 0.16, 2.6], [1.8, 0.12, 2.4], [1.8, 0.12, 1.8],
			  [0.9, 0.08, 2.4], [1.8, 0.30, 2.4]]:
		_view(shot)
		r.age_knee = float(v[0])
		r.age_floor = float(v[1])
		r.max_px = float(v[2])
		_pose(shot, 0.50, 3)
		var nm: String = "knee%03d_floor%03d_px%02d" % [
			int(v[0] * 10), int(v[1] * 100), int(v[2] * 10)]
		await _grab(DIR + "tune/%s.png" % nm)
		say("  %s" % nm)
	flush("tune.txt")


# ---------------------------------------------------------------------------
# 8. IS BLOOM IDLE, OR IS IT OFF?
#
# Every pair measured bloom at 0.000% of pixels changed, at every pose. That is
# a strong claim -- strong enough that it has to be separated from "the effect
# is not running". Threshold 0.0 makes every pixel in the frame a bloom source;
# if THAT changes nothing, the effect is broken and the verdict is worthless.
# ---------------------------------------------------------------------------
func _bloom() -> void:
	await r.get_tree().physics_frame
	rig.ready_space(r)
	var shot: Dictionary = named("t19_cloud_building")
	_ensure_scene(shot)
	_view(shot)
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(DIR + "bloom"))
	say("=== BLOOM THRESHOLD SWEEP -- %s at t=0.90, a retro plate in frame ===" % shot["name"])
	say("The point shader writes ALBEDO in 0..1 and a retroreflector clips the")
	say("intensity channel at exactly 1.0, so nothing in a belief frame is ever")
	say("above 1.0 and the cave's threshold of 1.60 can catch nothing at all.")
	fx_mask = 0
	_pose(shot, 0.90, 3)
	await _grab(DIR + "bloom/thresh_off.png")
	for t in [1.60, 0.80, 0.40, 0.10, 0.00]:
		grade.bloom_thresh = t
		fx_mask = BeliefGrade.E_BLOOM
		_pose(shot, 0.90, 3)
		await _grab(DIR + "bloom/thresh_%03d.png" % int(t * 100))
		say("  threshold %.2f" % t)
	grade.bloom_thresh = 0.80
	fx_mask = BeliefGrade.parse(fx)
	say("")
	say("beliefcheck.py measures thresh_off against each: if thresh_000 is also")
	say("unchanged the effect is not running and the verdict above is worthless.")
	flush("bloom.txt")


# ---------------------------------------------------------------------------
# 6. cost, leave-one-out, interleaved
# ---------------------------------------------------------------------------
func _cost() -> void:
	await r.get_tree().physics_frame
	rig.ready_space(r)
	var shot: Dictionary = named("t18_belief_cut")
	_ensure_scene(shot)
	_view(shot)
	say("=== POST COST, leave-one-out from `all`, interleaved A/B ===")
	say("scene %s, %d returns, %.0f mm lens, 1920x1080" % [
		r.scene_name, r.n_pts, float(shot["lens_mm"])])
	say("READ THE MEASUREMENT WARNING IN CINEMA.md BEFORE USING THESE.")
	say("")
	for nm in BeliefGrade.ORDER:
		var bit: int = int(BeliefGrade.NAMES[nm])
		var a_ms: float = 0.0
		var b_ms: float = 0.0
		for rep in range(3):
			fx_mask = BeliefGrade.ALL
			_pose(shot, 0.55, rep)
			var x: float = await _gpu_median(110)
			fx_mask = BeliefGrade.ALL & ~bit
			_pose(shot, 0.55, rep)
			var y: float = await _gpu_median(110)
			a_ms += x / 3.0
			b_ms += y / 3.0
		say("  %-9s all %6.2f ms   without %6.2f ms   delta %+6.2f ms" % [nm, a_ms, b_ms, a_ms - b_ms])
	fx_mask = 0
	_pose(shot, 0.55, 0)
	var none_ms: float = await _gpu_median(160)
	fx_mask = BeliefGrade.KEEP
	_pose(shot, 0.55, 0)
	var keep_ms: float = await _gpu_median(160)
	fx_mask = BeliefGrade.ALL
	_pose(shot, 0.55, 0)
	var all_ms: float = await _gpu_median(160)
	say("")
	say("  no post      %6.2f ms   (%d draw calls)" % [none_ms,
		RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_DRAW_CALLS_IN_FRAME)])
	say("  what ships   %6.2f ms   (%s)" % [keep_ms, BeliefGrade.mask_str(BeliefGrade.KEEP)])
	say("  everything   %6.2f ms" % all_ms)
	fx_mask = BeliefGrade.parse(fx)
	flush("cost.txt")


# ---------------------------------------------------------------------------
# 8. WHERE THE MACHINE IS, in a register that cannot draw it
#
# The belief cut is the same camera as the cave's shot 17, and shot 17 follows
# THE machine from behind. Hero.BEATS says beat 18 must contain it. But the
# belief register draws only what the sensor returned, and the sensor is bolted
# to that machine: a scanner cannot see its own carrier, so there is no mark in
# the frame that IS the machine. What the frame has instead is the machine's
# consequence -- every ray in it starts there, the minimum-range hole is around
# it, and the whole map is drawn from poses it believed it had.
#
# So the block is declared and nothing is drawn, and the declaration is then
# PROVED the way the camera is: the cave says the machine walks from f 3.2 to
# f 5.2 at station 68 over the take, and this rig can say where its sensor
# actually was at the two ends of the scrub. If those two disagree, the cut has
# the machine in two places and no picture will say so.
# ---------------------------------------------------------------------------
func _hero() -> void:
	await r.get_tree().physics_frame
	rig.ready_space(r)
	say("=== THE MACHINE, ACROSS THE CUT ===")
	say(Hero.banner())
	say("")
	say("The belief register draws no machine: a scanner cannot see the thing it")
	say("is bolted to. What is checked here is that the sensor -- which IS the")
	say("machine -- is where the cave's shot says the machine is at that moment.")
	say("")
	for shot in shots:
		var m: Dictionary = Hero.block(shot)
		if m.is_empty() or String(m.get("role", "")) != "hero":
			continue
		_ensure_scene(shot)
		var at = m.get("at", null)
		if not (at is Dictionary) or not (at as Dictionary).has("from"):
			say("%s: hero `at` is a hold; nothing to travel" % String(shot["name"]))
			continue
		var a0: Vector3 = rig.resolve((at as Dictionary)["from"])
		var a1: Vector3 = rig.resolve((at as Dictionary)["to"])
		var ta: float = rig.scrub(shot, 0.0, r.t_end)
		var tb: float = rig.scrub(shot, 1.0, r.t_end)
		var pa: Array = r._true_pose(ta)
		var pb: Array = r._true_pose(tb)
		var ba: Array = r._bel_pose(ta)
		var bb: Array = r._bel_pose(tb)
		var sa: Vector3 = pa[0]
		var sb: Vector3 = pb[0]
		var dur2: float = float(shot.get("len_s", 4.0))
		var clip: String = String(m.get("clip", "idle"))
		var v_book: float = Book.speed(String(m.get("chassis", "surveyor")), clip)
		say("--- %s   trailer %s   %s" % [String(shot["name"]),
			str(shot.get("trailer", "-")), Hero.describe(m)])
		say("  the cave's anchors     from %7.2f %6.2f %7.2f   to %7.2f %6.2f %7.2f" % [
			a0.x, a0.y, a0.z, a1.x, a1.y, a1.z])
		say("  this sensor, TRUE      from %7.2f %6.2f %7.2f   to %7.2f %6.2f %7.2f" % [
			sa.x, sa.y, sa.z, sb.x, sb.y, sb.z])
		say("  this sensor, BELIEVED  from %7.2f  ---  %7.2f   to %7.2f  ---  %7.2f" % [
			float(ba[0].x), float(ba[0].z), float(bb[0].x), float(bb[0].z)])
		var d0: Vector3 = Vector3(sa.x - a0.x, 0.0, sa.z - a0.z)
		var d1: Vector3 = Vector3(sb.x - a1.x, 0.0, sb.z - a1.z)
		say("  residual in plan       head %.0f mm    tail %.0f mm" % [
			d0.length() * 1000.0, d1.length() * 1000.0])
		say("  head height            sensor %.2f m above the floor (LIDAR 2's guess)" % 0.90)
		var d_cave: float = a0.distance_to(a1)
		var d_here: float = Vector3(sa.x, 0.0, sa.z).distance_to(Vector3(sb.x, 0.0, sb.z))
		say("  travel over the take   cave %.2f m = %.2f m/s   here %.2f m = %.2f m/s" % [
			d_cave, d_cave / maxf(dur2, 0.01), d_here, d_here / maxf(dur2, 0.01)])
		say("  the '%s' clip is baked at %.2f m/s (Book.CHASSIS), and the bake walks at %.2f m/s" % [
			clip, v_book, float((shot.get("cine", {}) as Dictionary).get("speed", 0.0))])
		say("  drift at the cut       %.2f m" % Vector3(
			float(bb[0].x) - sb.x, 0.0, float(bb[0].z) - sb.z).length())
		say("  scrub window           %.2f s to %.2f s of a %.2f s run" % [ta, tb, r.t_end])
		say("")
	flush("hero.txt")
