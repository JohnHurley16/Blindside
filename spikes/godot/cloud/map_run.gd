# ---------------------------------------------------------------------------
# BLINDSIDE -- THE MAP.  The trailer's ending, and the lidar cuts that lead to it.
#
# The designer, 2026-09-10:
#
#   "it wonders through the cave and than starts to uncover stuff and thats
#    where it fades to black.  work in the lidar views where it gets dark"
#   "show a 3d map of the cave system somehow after the dog explored it"
#
# There is no text in the new trailer, so the last image has to carry the idea
# unaided: a machine wandered somewhere alone in the dark, it fades to black,
# and what comes up is WHAT IT KNEW -- the cave rebuilt out of nothing but its
# own sensor returns, turning in space.
#
# Everything here draws the SAME accumulated cloud one exploration produced.
# Nothing is authored into it, nothing is filled in, nothing is smoothed, and
# nothing is ever drawn into a sensor shadow. The holes are the holes.
#
#   <godot> --path spikes/godot/cloud --resolution 1920x1080 -- --map=probe
#                                                              --map=stills
#                                                              --map=reveal
#                                                              --map=moments
#                                                              --map=depth
#                                                              --map=all
#                                         --depth=gauge|beams|blind
#                                         --voxel=0.07     metres, 0 = keep all
#                                         --fast           half the revolutions
#                                         --mapshot=NAME   just one
# ---------------------------------------------------------------------------
extends RefCounted

const DIR_SEQ := "res://shots/cinema/seq/"
const DIR_MAP := "res://shots/map/"
const SETTLE: int = 5
const CUT_FPS: float = 24.0

var r                       # the lidar root
var grade: BeliefGrade
var only: String = ""
var report: PackedStringArray = PackedStringArray()
var baked: String = ""


func say(t: String) -> void:
	print(t)
	report.push_back(t)


func flush(fname: String) -> void:
	var f := FileAccess.open(DIR_MAP + fname, FileAccess.WRITE)
	if f != null:
		f.store_string("\n".join(report) + "\n")
		f.close()
	report = PackedStringArray()


func _env() -> Environment:
	for c in r.get_children():
		if c is WorldEnvironment:
			return (c as WorldEnvironment).environment
	return null


func run(root) -> void:
	r = root
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(DIR_MAP))
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(DIR_SEQ))
	grade = BeliefGrade.new()
	grade.setup(_env(), r.cam)
	r.cam_driven = true
	r.show_hud = false
	r.show_lines = false
	r.cam.keep_aspect = Camera3D.KEEP_HEIGHT
	r.cam.far = 900.0
	r.trail_ribbon = true
	await r.get_tree().physics_frame
	await r.get_tree().physics_frame
	var m: String = r.map_mode
	if m == "all":
		await _probe(); await _stills(); await _reveal(); await _moments(); await _depth()
	elif m == "probe": await _probe()
	elif m == "stills": await _stills()
	elif m == "reveal": await _reveal()
	elif m == "moments": await _moments()
	elif m == "depth": await _depth()
	else: print("map: unknown mode ", m)


# ---------------------------------------------------------------------------
func _bake_map() -> void:
	var key: String = "%s|%.3f|%s|%.1f|%.1f|%.2f" % [r.depth_model, r.voxel_m, str(r.fast),
		r.map_s0, r.map_s1, r.map_rev_m]
	if baked == key:
		return
	r._bake("map")
	baked = key


# THE WHOLE ROUTE, sampled: what the accumulated map is.
func _bake_whole() -> void:
	r.map_s0 = 0.0
	r.map_s1 = 1.0e9
	r.map_rev_m = 0.0        # let the bake choose 1.7 m, or 3.4 with --fast
	r.voxel_m = r.voxel_want
	await _bake_map()


# ONE STRETCH, at the rate the device really turns: what the machine sees NOW.
#
# A 10 Hz head walking at 1.45 m/s lays a revolution every 145 mm. This is one
# every 0.65 m, which is a quarter of that and still forty times the whole-route
# bake -- and 0.65 m rather than 0.30 for the reason CINEMA.md 7 already found
# and had to fix once: at full local density everything within eleven metres is
# at the point-size cap and the frame is a solid fabric with no countable rings
# and no legible shadows in it. It is the same sensor, the same route and the
# same drift; only the sampling differs, which is exactly the split LIDAR.md 6
# says Phase 3 has to make anyway.
func _bake_local(s0: float, s1: float) -> void:
	r.map_s0 = maxf(0.0, s0)
	r.map_s1 = s1
	r.map_rev_m = 0.65
	r.voxel_m = 0.0
	await _bake_map()


func _grab(path: String) -> void:
	for k in range(SETTLE):
		r._apply_uniforms()
		await RenderingServer.frame_post_draw
	var img: Image = r.get_viewport().get_texture().get_image()
	img.save_png(ProjectSettings.globalize_path(path))


# The survey camera. There is no floor eighty metres over a cave, so this is
# CINEMA.md 3.3's `survey` frame: no body, and therefore it may never draw
# truth. `show_truth` is forced off on every frame this file renders.
func _look(pos: Vector3, tgt: Vector3, lens_mm: float, up: Vector3 = Vector3.UP) -> void:
	r.cam.fov = CloudRig.fov_for(lens_mm)
	r.cam.global_transform = Transform3D(Basis.IDENTITY, pos)
	r.cam.look_at(tgt, up)
	r.show_truth = false
	grade.apply(BeliefGrade.KEEP, r.cam, lens_mm, 5.6, pos.distance_to(tgt))


func _ease(t: float) -> float:
	return t * t * (3.0 - 2.0 * t)


func _smoother(t: float) -> float:
	var x: float = clampf(t, 0.0, 1.0)
	return x * x * x * (x * (x * 6.0 - 15.0) + 10.0)


# A move eased at both ends and CONSTANT in the middle. A smootherstep across
# thirteen seconds is nearly still at both ends and hurries through the middle,
# which is the opposite of what a slow turn wants: the eye needs the same rate
# for most of the shot and only the ends softened. Trapezoid velocity, ramps of
# `ramp`, integrated and normalised.
func _glide(t: float, ramp: float = 0.22) -> float:
	var x: float = clampf(t, 0.0, 1.0)
	var total: float = 1.0 - ramp
	if x < ramp:
		return (x * x / (2.0 * ramp)) / total
	if x > 1.0 - ramp:
		var y: float = 1.0 - x
		return (total - y * y / (2.0 * ramp)) / total
	return (x - ramp * 0.5) / total


# ---------------------------------------------------------------------------
# 1. probe -- what the exploration produced, in numbers
# ---------------------------------------------------------------------------
func _probe() -> void:
	await _bake_whole()
	var lo: Vector3 = r.cloud_min
	var hi: Vector3 = r.cloud_max
	say("=== the exploration =================================================")
	say("  route            %.1f m over %.1f s (%.1f min)" % [r.path_len, r.t_end, r.t_end / 60.0])
	say("  revolutions      %d, one every %.1f m of route" % [r.revs, r.map_rev_m])
	say("  shots fired      %d" % r.n_shots)
	say("  returns          %d raw" % r.n_raw)
	say("  points drawn     %d   (voxel %.0f mm)" % [r.n_pts, r.voxel_m * 1000.0])
	say("  dropout          %.1f%%" % (100.0 * float(r.n_drop) / maxf(float(r.n_shots), 1.0)))
	say("  depth model      %s" % r.depth_model)
	say("  cloud extent     x %.1f  y %.1f  z %.1f m" % [hi.x - lo.x, hi.y - lo.y, hi.z - lo.z])
	say("  cave extent      y %.1f m (truth)" % r._vertical_range())
	say("  believed / true depth  %.1f / %.1f m" % [r.drop_bel, r.drop_true])
	say("  drops")
	for d in r.descent_log:
		var dd: Dictionary = d
		say("    %-9s drop %5.1f m  bore %.2f m  believed %5.1f m" % [
			CaveTopology.PK_NAME[int(dd["kind"])], float(dd["drop"]), float(dd["bore"]),
			r._believed_drop(int(dd["pitch"]), float(dd["drop"]))])
	# what a machine can see down a hole, against what the hole is
	var sc := LidarScan.new()
	say("  the envelope     rings %d over %.1f .. %+.1f deg" % [sc.rings, sc.el_min_deg, sc.el_max_deg])
	for d2 in r.descent_log:
		var dd2: Dictionary = d2
		var br: float = float(dd2["bore"]) * 0.5
		say("    %-9s from the lip the steepest ring strikes the far wall %.2f m down; the drop is %.1f m"
			% [CaveTopology.PK_NAME[int(dd2["kind"])], br / tan(deg_to_rad(-sc.el_min_deg)), float(dd2["drop"])])
	say("  draw calls       1 for the cloud at %d points" % r.n_pts)
	flush("probe.txt")


# ---------------------------------------------------------------------------
# 2. stills -- the map, read from six directions
# ---------------------------------------------------------------------------
func _view_default() -> void:
	r.mode = 2                 # height. Depth IS the subject of this map.
	r.gain = 1.0
	r.pt_world = 0.020
	r.min_px = 1.4
	r.max_px = 2.6
	r.square = 0.0
	r.footprint = 0.0
	r.age_knee = 1.0e9         # a MAP is not a live sweep; nothing in it is new
	r.age_floor = 1.0
	r.epoch_split = -1.0
	r.clip_lo = -1000.0
	r.clip_hi = 1000.0
	r.clip_x_lo = -1.0e9
	r.clip_x_hi = 1.0e9
	r.clip_z_lo = -1.0e9
	r.clip_z_hi = 1.0e9
	r.cut_n = Vector3.ZERO
	r.cut_d0 = -1.0e9
	r.cut_d1 = 1.0e9
	r.now = r.t_end
	# The height ramp. Its dark end is a near-black navy, so putting the
	# DEEPEST level exactly on it hides the deepest level -- which is the one
	# there is no way back up from. The ramp is given 18% of headroom below the
	# cloud so the bottom of the map is on the ramp rather than at the end of it.
	var span: float = maxf(r.cloud_max.y - r.cloud_min.y, 1.0)
	r.h_lo = r.cloud_min.y - span * 0.18
	r.h_hi = r.cloud_max.y + span * 0.04
	r.show_truth = false
	r.show_lines = false


# The centre of what was EXPLORED, not the centre of the bounding box. The box
# is stretched by whatever the drift threw furthest; the route is where the
# machine actually went, and it is the thing the frame is about.
# EVERY AIM POINT IS IN BELIEF SPACE, and getting this wrong cost an hour of
# frames that looked like static.
#
# `geo.pitch_m` holds where a shaft IS. The cloud holds where the machine
# THOUGHT it was when it measured it, and after two hundred metres of route
# those two differ by metres. A camera standing in the machine's map and aimed
# at a true-world coordinate is aimed into the rock beside the thing it wants,
# and what it photographs is the inside of a wall. The rule for this file is
# therefore absolute and it is the same rule as CLAUDE.md's: nothing downstream
# of the sensor gets a world coordinate. A place is named by WHERE ON THE ROUTE
# it is, and resolved through the belief.
func _bel_at_s(s_route: float) -> Vector3:
	# resolved in the FINISHED map's frame whatever the shot is scrubbed to, so
	# that two stills either side of a moment share a camera rather than each
	# getting the one its own epoch would have given it
	var was: float = r.now
	r.now = r.t_end
	var a: Array = r.belief_view(r._map_time_at(clampf(s_route, 0.0, r.path_len)))
	r.now = was
	return a[0] as Vector3


func _centre() -> Vector3:
	if r.path_pts.size() == 0:
		return (r.cloud_min + r.cloud_max) * 0.5
	var acc := Vector3.ZERO
	for i in range(r.path_pts.size()):
		acc += r.path_pts[i]
	return acc / float(r.path_pts.size())


func _stills() -> void:
	await _bake_whole()
	_view_default()
	var c: Vector3 = _centre()
	var ext: Vector3 = r.cloud_max - r.cloud_min
	var d: float = maxf(ext.x, ext.z) * 1.15
	var shots: Array = [
		["01_the_map",       Vector3(0.62, 0.30, 0.72), d * 1.00, 35.0, "the whole system, three quarters, height coloured"],
		["02_section",       Vector3(0.00, 0.06, 1.00), d * 0.95, 40.0, "a 22 m slab through the descent chain: four levels and the way between them"],
		["03_plan",          Vector3(0.00, 0.99, 0.05), d * 0.92, 35.0, "plan. What a survey draws, and it is the one view that hides the subject"],
		["04_end_on",        Vector3(1.00, 0.10, 0.00), d * 0.90, 40.0, "end on, down the length of the workings"],
		["05_the_descent",   Vector3(0.22, 0.14, 0.97), d * 0.62, 42.0, "the descent chain: the moulin and the two winzes, close"],
		["06_intensity",     Vector3(0.62, 0.30, 0.72), d * 1.00, 35.0, "the same camera as 01, coloured by intensity instead of height"],
		["08_before_the_drop", Vector3(0.02, 0.10, 1.00), 62.0, 40.0, "THE MAP AT THE MOMENT OF COMMITMENT. Scrubbed to the instant the machine reached the lip of the first pitch. The drive ends. Below it there is a 1.9 m stub of bore and then nothing at all -- the steepest ring in the device is -30 deg and from a 2.2 m bore that is as far down as it reaches, at any depth, for ever. Everything the machine knows about the fourteen and a half metres under its feet is in that stub."],
		["09_after_the_drop",  Vector3(0.02, 0.10, 1.00), 62.0, 40.0, "the same camera at the end of the walk. The shaft is in the map now, and it is in the map for one reason: the machine went down it. A pitch is mapped by being fallen down."],
	]
	for sh in shots:
		var nm: String = sh[0]
		if only != "" and not nm.contains(only):
			continue
		_view_default()
		if nm == "02_section":
			_slab(22.0)
		if nm == "05_the_descent":
			_slab(30.0)
			r.show_lines = true
		if nm == "06_intensity":
			r.mode = 0
		if nm.begins_with("08_") or nm.begins_with("09_"):
			_slab(20.0, _first_lip().z)
			r.show_lines = true
			r.max_px = 3.0
		if nm == "08_before_the_drop":
			r.now = _t_at_first_lip()
		var dir: Vector3 = (sh[1] as Vector3).normalized()
		var tgt: Vector3 = c
		if nm == "05_the_descent":
			tgt = _descent_centre()
		if nm.begins_with("08_") or nm.begins_with("09_"):
			tgt = _first_lip() + Vector3(0.0, -7.5, 0.0)
		_look(tgt + dir * float(sh[2]), tgt, float(sh[3]))
		await _grab(DIR_MAP + nm + ".png")
		say("  %-16s %s" % [nm, sh[4]])
	flush("stills.txt")


# The head of the first pitch on the route, and the instant the machine got
# there. The pair of stills either side of it is the depth-blindness picture
# that needs no comparison and no caption: the same camera, the same map, and
# the only difference is whether the machine has committed yet.
# The lip of the first pitch sunk in WORKED ground -- the one the pitch shot is
# about. The moulin above it is in ice and the whole frame there is already thin.
func _first_winze_lip() -> Vector3:
	var wi: int = _winze_index()
	if wi > 0:
		return _bel_at_s(r.path_s[wi - 1])
	return _first_lip()


# The LAST WALKING point before a drop, not the first point inside the bore.
# The first point inside the bore is already 0.45 m down the hole, and an aim
# resolved from it points a camera five metres away at the floor two metres in
# front of it. The last standing place is where the machine is when it can still
# choose, which is also what the shot is about.
func _first_lip() -> Vector3:
	for i in range(1, r.path_pts.size()):
		if r.path_kind[i] == 1:
			return _bel_at_s(r.path_s[i - 1])
	return _descent_centre()


func _t_at_first_lip() -> float:
	for i in range(1, r.path_pts.size()):
		if r.path_kind[i] == 1:
			return r._map_time_at(maxf(0.0, r.path_s[i] - 0.35))
	return r.t_end


# A slab through the main descent chain, normal to Z, so that the four levels
# and the pitches between them are all in one section. ART-DIRECTION 8.2's
# crop box, in the axis a vertical cave needs it in.
func _slab(thick: float, at_z: float = NAN) -> void:
	var z: float = at_z if not is_nan(at_z) else _descent_centre().z
	r.clip_z_lo = z - thick * 0.5
	r.clip_z_hi = z + thick * 0.5


# The bottom of the deepest pitch on the route: where the exploration stopped.
func _deep_point() -> Vector3:
	var s_best := -1.0
	var lowest := 1.0e9
	for i in range(1, r.path_pts.size()):
		if r.path_kind[i] == 1 and r.path_pts[i].y < lowest:
			lowest = r.path_pts[i].y
			s_best = r.path_s[i]
	if s_best < 0.0:
		return _descent_centre()
	return _bel_at_s(s_best) + Vector3(0.0, 1.6, 0.0)


func _descent_centre() -> Vector3:
	var n := 0
	var acc := Vector3.ZERO
	var was := 0
	for i in range(1, r.path_pts.size()):
		if r.path_kind[i] == 1 and was == 0:
			acc += _bel_at_s(r.path_s[i])
			n += 1
		was = r.path_kind[i]
	if n == 0:
		return _centre()
	return acc / float(n)


# ---------------------------------------------------------------------------
# 3. THE REVEAL -- the last shot of the trailer
#
# IT IS A PULL-BACK, and that is the one structural decision in this file.
# The first version pushed IN: it started on the whole system and ended on a
# passage, which is a shot that explains itself in its first frame and then has
# nothing left to do for twelve seconds. A reveal has to reveal.
#
# So it opens where the audience has just been -- inside a passage, at the scale
# the lidar cuts were at, close enough that the marks are individual
# measurements and the machine's own trail is lying in the floor of it -- and
# then it goes away. The passage becomes a level. The level becomes four levels
# with three shafts hanging between them. The four levels become a cave. It is
# still turning when it fades.
#
#   0.0 - 3.0 s   one passage, sectioned, the trail in it. This is the register
#                 the cut arrives in, so nothing has to be established.
#   3.0 - 9.0 s   the pull-back. The section opens as the camera leaves, which
#                 is what lets the whole system arrive with nothing cropped out
#                 of it, and the turn runs through broadside the whole time.
#   9.0 - 13.0 s  the object, whole, still turning, still going away. Fade.
#
# Nothing cuts. The move is the whole shot.
# ---------------------------------------------------------------------------
func _reveal_pose(u: float) -> Dictionary:
	var c: Vector3 = _centre()
	var dc: Vector3 = _descent_centre()
	var ext: Vector3 = r.cloud_max - r.cloud_min
	var base: float = maxf(ext.x, ext.z)
	var g: float = _glide(u)
	# Azimuth is measured from +X, and the workings run along X, so 90 degrees
	# is broadside and 0 is end on -- where a hundred and twenty metres of cave
	# collapse into forty. The sweep is 66 degrees THROUGH broadside, from one
	# three-quarter to the other, so the length is across the frame for the whole
	# shot and the parallax still says solid object.
	var az: float = deg_to_rad(lerp(58.0, 124.0, g))
	var el: float = deg_to_rad(lerp(4.0, 17.0, g))
	var dist: float = lerp(44.0, maxf(base * 1.20, 152.0), g)
	# IT STARTS WHERE THE MACHINE ENDED. The first frame is the foot of the
	# deepest winze -- the last place the exploration reached, on the level
	# there is no route back up from -- and the move goes from there to
	# everything it knew. The target leaves it for the centre of the whole route
	# as the camera pulls out, so the thing that was the subject stays in frame
	# and stops being the subject.
	var tgt: Vector3 = _deep_point().lerp(c, _glide(clampf(u / 0.86, 0.0, 1.0)))
	var pos: Vector3 = tgt + Vector3(cos(el) * cos(az), sin(el), cos(el) * sin(az)) * dist
	return {"pos": pos, "tgt": tgt, "lens": lerp(40.0, 34.0, g)}


func _reveal_view(u: float) -> void:
	_view_default()
	r.show_lines = true
	r.min_px = 1.3
	r.max_px = 2.6
	# THE SECTION. ART-DIRECTION 8.2's crop box, in the axis a vertical cave
	# needs it in: a slab normal to Z, so the levels and the pitches between
	# them are all in one cut. It is closed at the head of the shot -- which is
	# what makes the opening frame a passage seen from inside its own wall, with
	# the trail lying in it -- and opens as the camera leaves, so that the whole
	# system arrives with nothing cropped out of it.
	var dc: Vector3 = _deep_point().lerp(_descent_centre(), _glide(clampf(u / 0.6, 0.0, 1.0)))
	var full: float = (r.cloud_max.z - r.cloud_min.z) * 1.2
	var th: float
	if u < 0.16:
		th = 16.0
	elif u < 0.72:
		th = lerp(16.0, full, _smoother((u - 0.16) / 0.56))
	else:
		th = full
	r.clip_z_lo = dc.z - th * 0.5
	r.clip_z_hi = dc.z + th * 0.5


func _reveal() -> void:
	await _bake_whole()
	var n: int = int(round(13.0 * CUT_FPS))
	if r.map_frames > 0:
		n = r.map_frames
	var dir: String = DIR_SEQ + "map_reveal/"
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(dir))
	var t0: int = Time.get_ticks_msec()
	say("=== map_reveal   13.0 s   %d frames at %.0f fps   %d points   1 draw call ===" % [
		n, CUT_FPS, r.n_pts])
	say("  frame     t_s     az_deg   dist_m   slab_m")
	for i in range(n):
		var u: float = float(i) / float(n - 1)
		_reveal_view(u)
		var ps: Dictionary = _reveal_pose(u)
		_look(ps["pos"], ps["tgt"], float(ps["lens"]))
		await _grab(dir + "%03d.png" % i)
		if i % 24 == 0 or i == n - 1:
			say("  %5d  %6.2f  %7.1f  %7.1f  %7.1f" % [
				i, u * 13.0, rad_to_deg(atan2((ps["pos"] as Vector3).z - (ps["tgt"] as Vector3).z,
					(ps["pos"] as Vector3).x - (ps["tgt"] as Vector3).x)),
				(ps["pos"] as Vector3).distance_to(ps["tgt"]), r.clip_z_hi - r.clip_z_lo])
	var el: float = float(Time.get_ticks_msec() - t0) / 1000.0
	say("  %d frames in %.1f s = %.2f s/frame" % [n, el, el / float(n)])
	# a contact sheet, six frames across the turn
	_sheet(dir, n, DIR_MAP + "_strip_map_reveal.png")
	flush("reveal.txt")


func _sheet(dir: String, n: int, out: String) -> void:
	var cols := 3
	var rows := 2
	var tw := 640
	var th := 360
	var sheet := Image.create(tw * cols, th * rows, false, Image.FORMAT_RGB8)
	for k in range(cols * rows):
		var idx: int = int(round(float(k) / float(cols * rows - 1) * float(n - 1)))
		var img := Image.load_from_file(ProjectSettings.globalize_path(dir + "%03d.png" % idx))
		if img == null:
			continue
		img.resize(tw, th, Image.INTERPOLATE_LANCZOS)
		img.convert(Image.FORMAT_RGB8)
		sheet.blit_rect(img, Rect2i(0, 0, tw, th), Vector2i((k % cols) * tw, (k / cols) * th))
	sheet.save_png(ProjectSettings.globalize_path(out))


# ---------------------------------------------------------------------------
# 4. THE LIDAR MOMENTS -- inside the cave, where it gets dark
#
# Not a labelled section and not one hard cut: a set of instants along ONE
# continuous journey at which the picture becomes what the machine sees. Each
# is a camera in the drive at the machine's own height, scrubbed to the moment
# it belongs to, and each is a different thing the sensor does.
# ---------------------------------------------------------------------------
func _moment_list() -> Array:
	# `find` names the CONTENT the moment is about; the time is looked up on the
	# route rather than typed in, because a fraction of a six-minute walk is not
	# a place and it stops being one the moment anything about the route changes.
	return [
		{"name": "m1_into_the_dark", "len": 3.5, "lens": 24.0, "back": 2.6, "up": 0.70,
		 "ahead": 15.0, "find": "ice", "lead": 5.0, "run": 6.5, "cam_move": 3.2,
		 "knee": 9.0, "floor": 0.24, "mode": 0,
		 "why": "the ice band, and the map going thin in it. THE-ICE 6.2: near-infrared is absorbed by ice, so a polished meltwater conduit returns almost nothing at the walls and flashes where the beam meets it square -- the returns collapse into a narrow forward cone. In the WORLD register this band is the one place the darkness relents (THE-ICE 6.1). In the machine's own view it is the emptiest place in the cave. That inversion is free and it is the strongest thing the ice does for this register."},
		{"name": "m2_passage_resolves", "len": 4.0, "lens": 21.0, "back": 2.4, "up": 1.42,
		 "ahead": 22.0, "find": "rock", "lead": 3.0, "run": 11.0, "cam_move": 1.1,
		 "knee": 10.0, "floor": 0.22, "mode": 0,
		 "why": "the map being written. Bedrock, so the returns come back: sweeps land during the take and the passage ahead builds out of nothing, ring by ring, while the far end stays black because nothing has been there yet."},
		{"name": "m3_the_pitch", "len": 4.5, "lens": 21.0, "back": 1.5, "up": 1.05, "gain": 1.5,
		 "ahead": 8.5, "aim_lip": true, "lip_down": 1.15, "still": 0.98, "find": "winze", "lead": 3.6, "run": 4.4, "cam_move": 2.2,
		 "knee": 16.0, "floor": 0.26, "mode": 0,
		 "why": "the lip of the winze, and the floor stops. The steepest ring in the device is -30 deg, so from a 1.6 m bore it strikes the FAR WALL 1.4 m down and nothing below that is in the beam pattern at any depth, for ever. The drop is 22.7 m and the map has 1.4 m of it. The beacon on the lip is retroreflective and blazes; below it there is nothing at all, and the nothing is the shot."},
		{"name": "m4_uncovered", "len": 4.0, "lens": 24.0, "back": 2.6, "up": 1.10, "gain": 2.3,
		 "ahead": 10.0, "find": "worked", "lead": 4.5, "run": 9.0, "cam_move": 2.8,
		 "knee": 18.0, "floor": 0.42, "mode": 0,
		 "why": "something is uncovered. The workings: rail down the floor as two bright dotted lines, timber sets as a regular row of shadow slots, a beacon. A retroreflector clips the intensity channel and blazes from anywhere in range at any incidence, so the PLACED things are automatically the brightest things in the machine's own view -- no overlay, no art direction, and physically true."},
	]


# Find the route distance at which the moment's content happens. Each test is a
# question about the station the machine is standing on, or about a pitch it is
# arriving at, and the answer is a distance along the route.
# The DEEPEST winze on the route, and the choice is not arbitrary.
#
# The first winze is at the foot of the karst, and topology.gd puts
# ICE-OVER-ROCK exactly there -- "in the karst, ice-over-rock NEAR A PITCH" --
# so the floor at the lip is ice, and an ice floor at grazing incidence returns
# almost nothing (THE-ICE 6.2). The frame is then a sparse dust of returns with
# no floor in it and no lip, which is a true picture of that place and a useless
# picture of a pitch. The deepest winze is below the melt front in the workings:
# rock, timber, rail, dense returns on every side of a hole. Same event, and it
# is legible.
func _winze_index() -> int:
	var best := -1
	var lowest := 1.0e9
	for i in range(1, r.path_pts.size()):
		if r.path_kind[i] != 1 or r.path_kind[i - 1] != 0:
			continue
		var pm: Dictionary = r.geo.pitch_m[r.path_pitch[i]]
		if int(pm["kind"]) != CaveTopology.PK_WINZE:
			continue
		if float(pm["top"]) < lowest:
			lowest = float(pm["top"])
			best = i
	return best


func _find_s(kind: String) -> float:
	if kind == "winze":
		var wi: int = _winze_index()
		return r.path_s[wi] if wi > 0 else -1.0
	var topo: CaveTopology = r.geo.topo
	var best := -1.0
	var last_bore := 0.0
	for i in range(1, r.path_pts.size()):
		if r.path_kind[i] != 0:
			last_bore = r.path_s[i]
		var sid: int = r.path_st[i]
		if sid < 0:
			continue
		# A route point inside a BORE carries the head station's row, so a test
		# that only asks about the station will happily answer "yes, here" for a
		# place that is 1.6 m of vertical tube. And a point sixteen metres past
		# the foot of one is no better: the camera stands BACK along the route
		# from what it is looking at, so a find too close behind a drop puts the
		# camera in the shaft and the shot is a descent rather than a walk. Both
		# failures were photographed before this line existed.
		if r.path_kind[i] != 0:
			continue
		if r.path_s[i] - last_bore < 18.0:
			continue
		var st: PackedInt32Array = topo.stations[sid]
		var med: int = st[CaveTopology.S_MEDIUM]
		match kind:
			"ice":
				# a run of clean ice, past the collar, wide enough to walk
				if med == CaveTopology.MED_ICE and r.path_s[i] > 22.0 \
					and st[CaveTopology.S_WIDTH] >= CaveTopology.WC_PASSAGE:
					return r.path_s[i]
			"rock":
				if med == CaveTopology.MED_ROCK and st[CaveTopology.S_LEVEL] >= 1 \
					and st[CaveTopology.S_WIDTH] >= CaveTopology.WC_PASSAGE:
					return r.path_s[i]
			"worked":
				if med == CaveTopology.MED_WORKED and st[CaveTopology.S_LEVEL] >= 2 \
					and (st[CaveTopology.S_WORKS] & CaveTopology.WK_RAIL) != 0 \
					and (st[CaveTopology.S_WORKS] & CaveTopology.WK_SETS) != 0:
					return r.path_s[i]
			"winze":
				pass    # handled by _winze_index below; it is not a scan
			"pitch":
				if r.path_kind[i] == 1:
					return r.path_s[i]
	return best


func _moment_window(m: Dictionary) -> Array:
	var s0: float = _find_s(String(m["find"]))
	if s0 < 0.0:
		s0 = _find_s("rock")
	if s0 < 0.0:
		s0 = r.path_len * 0.3
	var a: float = maxf(0.0, s0 - float(m.get("lead", 4.0)))
	var b: float = minf(r.path_len, a + float(m.get("run", 8.0)))
	return [a, b]


# THE CAMERA IS ON THE ROUTE, and that is not a convenience.
#
# The first version put the camera `back` metres behind the machine along its
# instantaneous heading and aimed it `ahead` metres along the same straight
# line. In a drive that bends -- which is every drive -- that lands the camera
# inside the wall behind and the aim inside the wall in front, and what it
# photographs is a flat rectangle of returns two metres away. Both ends are
# resolved ALONG THE ROUTE instead: a place the machine has already stood is
# guaranteed to be inside the passage, and a place it is about to stand is
# guaranteed to be where the passage goes. It also means that at a pitch the aim
# follows the route straight down the hole, with nothing to author.
#
# The camera and the scrub are parameterised separately, because they are
# different things. `cam_move` is how far the camera travels during the take;
# the window is how much of the walk lands in it. A shot where the camera barely
# moves while four seconds of sweeps arrive is the map being WRITTEN. A shot
# where the two move together is a machine walking.
func _moment_pose(m: Dictionary, u: float) -> Dictionary:
	var w: Array = m["_win"]
	var s_a: float = float(w[0])
	var s_b: float = float(w[1])
	var t: float = r._map_time_at(lerp(s_a, s_b, u))
	r.now = t
	var s_cam: float = s_a - float(m["back"]) + float(m.get("cam_move", 2.0)) * u
	var s_tgt: float = s_cam + float(m["ahead"])
	var pa: Array = r.belief_view(r._map_time_at(clampf(s_cam, 0.0, r.path_len)))
	var pb: Array = r.belief_view(r._map_time_at(clampf(s_tgt, 0.0, r.path_len)))
	var up: float = float(m["up"]) - 0.9
	var pos: Vector3 = (pa[0] as Vector3) + Vector3(0, up, 0)
	var tgt: Vector3 = (pb[0] as Vector3) + Vector3(0, up - float(m.get("aim_down", 0.0)), 0)
	if bool(m.get("aim_lip", false)):
		# aim AT the lip rather than along the route past it. Aiming along
		# the route is right everywhere else and wrong here: the route
		# turns straight down at a pitch, so the camera pitches into the
		# floor and photographs it. The subject is the drive ending.
		tgt = _first_winze_lip() - Vector3(0.0, float(m.get("lip_down", 0.45)), 0.0)
	return {"pos": pos, "tgt": tgt, "t": t}


func _moments() -> void:
	r.ensure_route()
	for m_ in _moment_list():
		var m: Dictionary = m_
		var nm: String = m["name"]
		if only != "" and not nm.contains(only):
			continue
		m["_win"] = _moment_window(m)
		var wv: Array = m["_win"]
		await _bake_local(float(wv[0]) - float(m["back"]) - 3.0,
			float(wv[1]) + float(m["ahead"]) + 6.0)
		var n: int = int(round(float(m["len"]) * CUT_FPS))
		if r.map_frames > 0:
			n = r.map_frames
		var dir: String = DIR_SEQ + nm + "/"
		DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(dir))
		var t0: int = Time.get_ticks_msec()
		var wi: Array = m["_win"]
		say("=== %s   %.1f s   %d frames   %.0f mm   route %.1f..%.1f m of %.0f ===" % [
			nm, float(m["len"]), n, float(m["lens"]), float(wi[0]), float(wi[1]), r.path_len])
		say("    %s" % m["why"])
		say("  frame     t_s   cam x/y/z              aim x/y/z")
		for i in range(n):
			var u: float = float(i) / float(n - 1)
			_view_default()
			r.mode = int(m["mode"])
			r.max_px = 2.4
			r.pt_world = 0.018
			r.age_knee = float(m["knee"])
			r.age_floor = float(m["floor"])
			# THE ONE EXPOSURE IN THIS FILE, and it is per shot rather than
			# global. A worked drive has a FLAT floor, and a flat floor seen
			# from a 0.90 m head at five metres is 80 degrees off its own
			# normal: cos^0.75 of that is 0.27, so a 0.30-albedo rock floor
			# returns eight per cent and lands on the dark end of the intensity
			# ramp. The karst above it is rounded and rough, so its floor faces
			# the beam in patches and reads two stops brighter. That difference
			# is real and it is worth keeping -- deeper looks different in the
			# belief register too -- but a frame in the workings needs exposing
			# for what is in it. LIDAR.md 3's claim that no frame has a hand-set
			# gain no longer holds for these two, and it is recorded rather than
			# hidden.
			r.gain = float(m.get("gain", 1.0))
			var ps: Dictionary = _moment_pose(m, u)
			r.now = float(ps["t"])
			_look(ps["pos"], ps["tgt"], float(m["lens"]))
			await _grab(dir + "%03d.png" % i)
			if i % 12 == 0 or i == n - 1:
				var pp: Vector3 = ps["pos"]
				var tt: Vector3 = ps["tgt"]
				say("  %5d  %6.2f  %7.2f %6.2f %7.2f   %7.2f %6.2f %7.2f" % [
					i, float(ps["t"]), pp.x, pp.y, pp.z, tt.x, tt.y, tt.z])
		var el: float = float(Time.get_ticks_msec() - t0) / 1000.0
		say("    %d frames in %.1f s = %.2f s/frame" % [n, el, el / float(n)])
		_sheet(dir, n, DIR_MAP + "_strip_" + nm + ".png")
		# a still from the middle of each, for shots/map/
		var pm: Dictionary = _moment_pose(m, float(m.get("still", 0.62)))
		_view_default()
		r.mode = int(m["mode"])
		r.max_px = 2.2
		r.pt_world = 0.017
		r.age_knee = float(m["knee"])
		r.age_floor = float(m["floor"])
		r.gain = float(m.get("gain", 1.0))
		r.now = float(pm["t"])
		_look(pm["pos"], pm["tgt"], float(m["lens"]))
		await _grab(DIR_MAP + nm + ".png")
	flush("moments.txt")


# ---------------------------------------------------------------------------
# 5. DEPTH -- the same exploration under three vertical belief models
#
# VERTICAL.md 9: a machine cannot see down a shaft, cannot see up one, cannot
# even RECORD that nothing came back, and a fall contributes no odometry. What
# it has instead, in this project, is a depth gauge that no design document has
# ever agreed to. This renders the same camera three times so the difference is
# a picture rather than a paragraph.
# ---------------------------------------------------------------------------
func _depth() -> void:
	var models := ["gauge", "beams", "blind"]
	var was: String = r.depth_model
	say("=== the vertical belief ==============================================")
	say("  %-8s %10s %10s %10s   %s" % ["model", "map depth", "cave", "error", "what it assumes"])
	var why := {
		"gauge": "a depth gauge on every chassis, bias 0.42 m. No document in this project agrees it exists.",
		"beams": "the machine estimates a drop from what its own beams reached: r/tan30 down from the lip, r/tan12 up from the foot.",
		"blind": "a fall contributes nothing. VERTICAL.md 9.5 item 1, taken literally.",
	}
	# ONE camera for all three, fixed from the first, or the comparison is
	# three different framings of three different things and proves nothing.
	var cam_pos := Vector3.ZERO
	var cam_tgt := Vector3.ZERO
	var slab_z := 0.0
	for mo in models:
		r.depth_model = mo
		baked = ""
		await _bake_whole()
		_view_default()
		var ext: Vector3 = r.cloud_max - r.cloud_min
		say("  %-8s %9.1f m %9.1f m %9.1f m   %s" % [
			mo, ext.y, r._vertical_range(), ext.y - r._vertical_range(), why[mo]])
		if cam_tgt == Vector3.ZERO:
			var c: Vector3 = _centre()
			slab_z = _descent_centre().z
			cam_tgt = Vector3(c.x, c.y, c.z)
			cam_pos = cam_tgt + Vector3(0.0, 0.10, 1.0).normalized() 				* maxf(ext.x, r.cloud_max.z - r.cloud_min.z) * 0.95
		_slab(30.0, slab_z)
		r.show_lines = true
		_look(cam_pos, cam_tgt, 40.0)
		await _grab(DIR_MAP + "07_depth_" + mo + ".png")
	r.depth_model = was
	baked = ""
	flush("depth.txt")
