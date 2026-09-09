# ---------------------------------------------------------------------------
# BLINDSIDE -- the cinematic capture driver, PIT-HEAD.
#
# Everything the cinematic layer can be asked to do, and every one of them
# writes into shots/cinema/ so a claim in CINEMA.md has a picture or a number
# behind it. Ported from the cave's --cinema=* modes.
#
#   --cinema=validate    validate every shot           shots/cinema/validation.txt
#   --cinema=seq         render the executing shots as image sequences
#   --cinema=pairs       before/after for every effect, cumulative, one pose
#   --cinema=stack       whole stack on/off, three frames
#   --cinema=tune        the bloom sweep, the vignette sweep, the dirt sweep
#   --cinema=cost        leave-one-out timing, interleaved A/B/A/B
#   --cinema=fail        the rejected shots and the frames they would have shipped
#   --cinema=contract    the frames lumcheck.py measures, AgX-only and full stack
#   --fx=a+b+c           any subset of the stack, or `all` / `none`
#   --shot=NAME          restrict to one shot
# ---------------------------------------------------------------------------
extends RefCounted
class_name Shoot

var root: Node3D
var cam: Camera3D
var W: Weather
var rig: CameraRig
var grade: CinemaGrade
var shots: Array = []
var lines: Array[String] = []

# frames rendered per captured frame, so the shadow atlas, SSAO, the sky
# radiance and the rain particles have settled before the shutter opens
const SETTLE_FIRST: int = 72
const SETTLE_STEP: int = 8
const SEQ_FRAMES: int = 24

func _init(p_root: Node3D, p_cam: Camera3D, p_W: Weather, p_rig: CameraRig,
		p_grade: CinemaGrade) -> void:
	root = p_root
	cam = p_cam
	W = p_W
	rig = p_rig
	grade = p_grade

func load_shots(path: String) -> void:
	var f := FileAccess.open(path, FileAccess.READ)
	if f == null:
		push_error("CINEMA: cannot open " + path)
		return
	var j = JSON.parse_string(f.get_as_text())
	f.close()
	if j is Array:
		shots = j

func find(nm: String) -> Dictionary:
	for s in shots:
		if String(s["name"]) == nm:
			return s
	return {}

func log_line(s: String) -> void:
	print(s)
	lines.append(s)

func write(name: String) -> void:
	var d := ProjectSettings.globalize_path("res://shots/cinema/")
	DirAccess.make_dir_recursive_absolute(d)
	var f := FileAccess.open(d + name, FileAccess.WRITE)
	if f:
		f.store_string("\n".join(lines) + "\n")
		f.close()
	lines.clear()

func dir_for(sub: String) -> String:
	var d := ProjectSettings.globalize_path("res://shots/cinema/" + sub)
	DirAccess.make_dir_recursive_absolute(d)
	return d

# ---------------------------------------------------------------------------
# posing
# ---------------------------------------------------------------------------
## Put the camera where the shot says, configure the lens, and hand the
## compositor the PREVIOUS SHOT FRAME's transform rather than the previous
## rendered frame's -- offline capture renders each frame many times over to let
## the scene settle, so "last frame" is the same pose and the blur would be
## exactly zero.
func pose_cam(shot: Dictionary, tn: float, mask_v: int, prev_tn: float = -1.0) -> Dictionary:
	var ps: Dictionary = rig.pose(shot, tn)
	cam.global_transform = Transform3D(ps["basis"], ps["pos"])
	cam.keep_aspect = Camera3D.KEEP_HEIGHT
	cam.fov = CameraRig.fov_for(float(ps["lens"]))
	if prev_tn >= 0.0:
		var pp: Dictionary = rig.pose(shot, prev_tn)
		grade.lens.use_external_prev = true
		grade.lens.external_prev = Transform3D(pp["basis"], pp["pos"])
	else:
		grade.lens.use_external_prev = true
		grade.lens.external_prev = cam.global_transform
	grade.lens.seedt = tn * 977.0 + float(int(shot.get("seed", 0)))
	grade.apply(mask_v, cam, float(ps["lens"]), float(ps["tstop"]), float(ps["focus"]),
		W.wet)
	if W.rain != null:
		W.rain.global_position = (ps["pos"] as Vector3) + Vector3(0, 6, 0)
	return ps

## The 1/60 s spacing a finished 60 fps shot has, expressed as a normalised
## time step, so the blur in a 24-frame sequence is the blur the real shot has.
func prev_tn_for(shot: Dictionary, tn: float) -> float:
	var dt: float = (1.0 / 60.0) / maxf(float(shot["len_s"]), 0.01)
	return maxf(tn - dt, 0.0)

func light_for(shot: Dictionary) -> String:
	return String(shot.get("light", "overcast"))

func set_light(shot: Dictionary) -> void:
	W.apply(light_for(shot))
	grade.capture_base()

func settle(n: int) -> void:
	for i in n:
		await RenderingServer.frame_post_draw

func grab(path: String) -> void:
	var img := root.get_viewport().get_texture().get_image()
	img.save_png(path)

# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------
func run_validate() -> void:
	log_line("=== CINEMA validation, pit-head ===")
	log_line("collision: %d ground tris + %d instances / %d tris, built in %.0f ms"
		% [rig.collision_ground_tris, rig.collision_props, rig.collision_tris, rig.build_ms])
	log_line("")
	var okn := 0
	for s in shots:
		var v: Dictionary = rig.validate(s)
		var st: Dictionary = v["stats"]
		var d: Array = st["dof"]
		log_line("%-26s  %s  %2.0fmm T%.1f  %s" % [v["name"],
			"EXECUTES " if v["ok"] else "REJECTED ", float(s["lens_mm"]),
			float(s.get("tstop", 2.8)), String(s.get("light", "overcast"))])
		log_line("    trailer %-4s  %.1fs  ease %-5s  height %-7s  handheld %.2f deg"
			% [String(s.get("trailer", "-")), float(s["len_s"]),
				String(s.get("ease", "inout")), String(s.get("height", "eye")),
				float(s.get("handheld_deg", 0.0))])
		log_line("    travel %.2f m   peak %.2f m/s   near clear %.2f m   above ground %.2f-%.2f m"
			% [st["travel"], st["vmax"], st["clear"], st["h_lo"], st["h_hi"]])
		var far_s: String = "inf" if float(d[1]) > 1e6 else ("%.2f" % float(d[1]))
		log_line("    fov %.1f deg   sharp %.2f m to %s m   hyperfocal %.2f m"
			% [st["fov"], float(d[0]), far_s, float(d[2])])
		if String(s.get("height", "")) == "crane":
			var mo: Array = st["mount"]
			if float(mo[0]) >= 0.0:
				log_line("    crane hangs off %s at %.1f m" % [mo[1], mo[0]])
		for w in v["warn"]:
			log_line("    WARN: %s" % w)
		for fl in v["fail"]:
			log_line("    FAIL: %s" % fl)
		log_line("")
		if v["ok"]:
			okn += 1
	log_line("%d of %d shots execute" % [okn, shots.size()])
	write("validation.txt")

# ---------------------------------------------------------------------------
# sequences
# ---------------------------------------------------------------------------
func run_seq(only: String, mask_v: int) -> void:
	log_line("=== CINEMA sequences, fx = %s ===" % CinemaGrade.mask_str(mask_v))
	for s in shots:
		var nm: String = String(s["name"])
		if only != "" and nm != only:
			continue
		if nm.begins_with("x"):
			continue
		var v: Dictionary = rig.validate(s)
		if not v["ok"]:
			log_line("%s  REJECTED, not rendered:" % nm)
			for fl in v["fail"]:
				log_line("    FAIL: %s" % fl)
			continue
		var d := dir_for("seq/" + nm + "/")
		set_light(s)
		var steps: Array = []
		for i in range(SEQ_FRAMES):
			var tn: float = float(i) / float(SEQ_FRAMES - 1)
			var ps: Dictionary = pose_cam(s, tn, mask_v, prev_tn_for(s, tn))
			await settle(SETTLE_FIRST if i == 0 else SETTLE_STEP)
			grab(d + "%03d.png" % i)
			steps.append(ps["pos"])
		var mm: Array = []
		for i in range(steps.size() - 1):
			mm.append("%.1f" % ((steps[i] as Vector3).distance_to(steps[i + 1]) * 1000.0))
		log_line("%s  %d frames, per-frame step in mm:" % [nm, SEQ_FRAMES])
		log_line("    " + " ".join(mm))
	write("sequences.txt")

# ---------------------------------------------------------------------------
# pairs -- cumulative, in TRAILER 9's order, from one identical camera
# ---------------------------------------------------------------------------
func run_pairs(only: String) -> void:
	var s: Dictionary = find(only) if only != "" else shots[0]
	if s.is_empty():
		push_error("CINEMA: no shot for pairs")
		return
	var tn: float = 0.55
	var d := dir_for("pairs/" + String(s["name"]) + "/")
	set_light(s)
	log_line("=== CINEMA pairs, cumulative, %s at t=%.2f, %s light ===" % [
		s["name"], tn, light_for(s)])
	var acc: int = CinemaGrade.E_TONEMAP
	pose_cam(s, tn, acc, prev_tn_for(s, tn))
	await settle(SETTLE_FIRST)
	grab(d + "00_base_tonemap.png")
	var i: int = 1
	for n in CinemaGrade.ORDER:
		if n == "tonemap":
			continue
		var bit: int = int(CinemaGrade.NAMES[n])
		pose_cam(s, tn, acc, prev_tn_for(s, tn))
		await settle(SETTLE_STEP)
		grab(d + "%02d_%s_off.png" % [i, n])
		acc |= bit
		pose_cam(s, tn, acc, prev_tn_for(s, tn))
		await settle(SETTLE_STEP)
		grab(d + "%02d_%s_on.png" % [i, n])
		log_line("%02d %-9s off -> on   (%s)" % [i, n, CinemaGrade.mask_str(acc)])
		i += 1
	write("pairs_%s.txt" % String(s["name"]))

# ---------------------------------------------------------------------------
# stack on / off, three frames
# ---------------------------------------------------------------------------
func run_stack(names: Array) -> void:
	var d := dir_for("stack/")
	log_line("=== CINEMA stack on/off ===")
	for nm in names:
		var s: Dictionary = find(String(nm))
		if s.is_empty():
			continue
		set_light(s)
		for pair in [["off", CinemaGrade.E_TONEMAP], ["on", CinemaGrade.ALL]]:
			pose_cam(s, 0.55, int(pair[1]), prev_tn_for(s, 0.55))
			await settle(SETTLE_FIRST)
			grab(d + "%s_%s.png" % [nm, pair[0]])
		log_line("%s  off/on written" % nm)
	write("stack.txt")

# ---------------------------------------------------------------------------
# tune -- the sweeps that decide a number
# ---------------------------------------------------------------------------
func run_tune(only: String) -> void:
	var d := dir_for("tune/")
	log_line("=== CINEMA tuning sweeps ===")
	# BLOOM: threshold, at a pose that has the sky, wet iron and a pilot in it
	var s: Dictionary = find(only) if only != "" else shots[0]
	set_light(s)
	var base: int = CinemaGrade.E_TONEMAP
	pose_cam(s, 0.55, base, -1.0)
	await settle(SETTLE_FIRST)
	grab(d + "bloom_off.png")
	# The threshold is swept in GODOT'S units, not in the scene's. The HDR probe
	# (--cinema=hdr) says this site's radiance runs to about 5 in the overcast
	# sky and 23 in the sun glow, and at glow_hdr_threshold 0.8 nothing blooms at
	# all -- so Godot's glow high-pass is not reading the same numbers the buffer
	# holds. The sweep therefore covers the range where it demonstrably responds
	# and the intensity is swept with it, because the two are one decision.
	# THE SWEEP THAT ACTUALLY ANSWERS IT is over the threshold AND the soft knee.
	# `glow_hdr_scale` is the width of the smoothstep above the threshold, and
	# the cave leaves it at 2.0. The HDR probe says this site's scene radiance
	# runs 0.03-0.9 with the overcast sky at 0.33 and only the sun glow above 1,
	# so a 2.0-wide knee is wider than the entire range: NOTHING ever reaches
	# full weight, which is why bloom looked broken at every threshold.
	for th in [0.30, 0.40, 0.55]:
		for sc in [0.15, 0.35, 2.00]:
			grade.bloom_threshold = th
			grade.bloom_scale = sc
			grade.bloom_intensity = 0.90
			pose_cam(s, 0.55, base | CinemaGrade.E_BLOOM, -1.0)
			await settle(SETTLE_STEP)
			grab(d + "bloom_t%.2f_s%.2f.png" % [th, sc])
			log_line("bloom threshold %.2f knee %.2f written" % [th, sc])
	grade.bloom_threshold = 2.60
	grade.bloom_intensity = 0.45
	# VIGNETTE: how much of the cos^4 law survives
	pose_cam(s, 0.55, base, -1.0)
	await settle(SETTLE_STEP)
	grab(d + "vig_off.png")
	for k in [0.35, 0.55, 0.80]:
		grade.vig_k = k
		pose_cam(s, 0.55, base | CinemaGrade.E_VIGNETTE, -1.0)
		await settle(SETTLE_STEP)
		grab(d + "vig_k%.2f.png" % k)
		log_line("vignette k %.2f written" % k)
	grade.vig_k = 0.55
	# MOTION BLUR: a still pose cannot show it, so it is shown at the fastest
	# instant of a real move
	for nm in [String(s["name"])]:
		var sh: Dictionary = find(nm)
		if sh.is_empty():
			continue
		pose_cam(sh, 0.50, base, -1.0)
		await settle(SETTLE_STEP)
		grab(d + "mblur_%s_off.png" % nm)
		pose_cam(sh, 0.50, base | CinemaGrade.E_MBLUR, prev_tn_for(sh, 0.50))
		await settle(SETTLE_STEP)
		grab(d + "mblur_%s_on.png" % nm)
		log_line("motion blur showcase %s written" % nm)
	# DIRT, only useful where it is allowed to run at all
	var rs: Dictionary = {}
	for sh2 in shots:
		if String(sh2.get("light", "")) == "rain":
			rs = sh2
			break
	if not rs.is_empty():
		set_light(rs)
		pose_cam(rs, 0.55, base, -1.0)
		await settle(SETTLE_FIRST)
		grab(d + "dirt_off.png")
		grade.dirt_gain = 0.10
		for th in [0.10, 0.25, 0.50, 1.00]:
			grade.dirt_thresh = th
			pose_cam(rs, 0.55, base | CinemaGrade.E_DIRT, -1.0)
			await settle(SETTLE_STEP)
			grab(d + "dirt_t%.2f.png" % th)
			log_line("dirt threshold %.2f gain %.2f -> lens.flags %d lens.dirt_gain %.3f wet %.2f"
				% [th, grade.dirt_gain, grade.lens.flags, grade.lens.dirt_gain, W.wet])
		grade.dirt_thresh = 0.25
		for g in [0.04, 0.12, 0.30]:
			grade.dirt_gain = g
			pose_cam(rs, 0.55, base | CinemaGrade.E_DIRT, -1.0)
			await settle(SETTLE_STEP)
			grab(d + "dirt_g%.2f.png" % g)
			log_line("dirt gain %.2f at threshold 0.25 written (%s)" % [g, rs["name"]])
	write("tune.txt")

# ---------------------------------------------------------------------------
# the deliberate and the real failures, and the frames they would have shipped
# ---------------------------------------------------------------------------
func run_fail() -> void:
	var d := dir_for("fail/")
	log_line("=== CINEMA rejected shots ===")
	for s in shots:
		var v: Dictionary = rig.validate(s)
		if v["ok"]:
			continue
		var nm: String = String(s["name"])
		log_line("%s  REJECTED" % nm)
		for fl in v["fail"]:
			log_line("    FAIL: %s" % fl)
		# Walk the move and find the last legal instant BEFORE the first rejection.
		#
		# It has to be "before", not "the last t that happens to pass", because the
		# shell is a triangle SOUP: a camera that has walked entirely inside a
		# solid touches no triangle and the overlap test reports it clear again.
		# The cave found the same hole with its own xfail. Reporting the maximum
		# passing t would say "last legal t = 1.000" about a camera standing
		# inside a building, which is worse than saying nothing.
		var last_ok: float = -1.0
		var first_bad: float = -1.0
		var clear_after: bool = false
		for i in range(CameraRig.SAMPLES + 1):
			var tn: float = float(i) / float(CameraRig.SAMPLES)
			var p: Vector3 = rig.pose(s, tn)["pos"]
			var okp: bool = not rig._overlaps(p) and rig.buried(p) < 5
			if okp and first_bad < 0.0:
				last_ok = tn
			elif not okp and first_bad < 0.0:
				first_bad = tn
			elif okp:
				clear_after = true
		log_line("    last legal t = %.3f, first rejected t = %.3f%s" % [last_ok, first_bad,
			"   (and it reports CLEAR again after that: the shell is a triangle soup,"
			+ " so a camera fully inside a solid touches nothing)" if clear_after else ""])
		set_light(s)
		var want: Array = [0.0, maxf(last_ok, 0.0), maxf(first_bad, 0.0), 1.0]
		var tags: Array = ["start", "lastlegal", "firstbad", "end"]
		for k in range(4):
			pose_cam(s, float(want[k]), CinemaGrade.ALL, -1.0)
			await settle(SETTLE_FIRST if k == 0 else SETTLE_STEP)
			grab(d + "%s_%s.png" % [nm, tags[k]])
	write("fail.txt")

# ---------------------------------------------------------------------------
# the exposure contract set
# ---------------------------------------------------------------------------
func run_contract() -> void:
	log_line("=== CINEMA contract frames ===")
	for pair in [["off", CinemaGrade.E_TONEMAP], ["on", CinemaGrade.ALL]]:
		var d := dir_for("contract_%s/" % pair[0])
		for s in shots:
			var nm: String = String(s["name"])
			if nm.begins_with("x"):
				continue
			if not rig.validate(s)["ok"]:
				continue
			set_light(s)
			for tn in [0.15, 0.50, 0.85]:
				pose_cam(s, float(tn), int(pair[1]), prev_tn_for(s, float(tn)))
				await settle(SETTLE_FIRST)
				grab(d + "%s@%.2f.png" % [nm, tn])
			log_line("%s %s written" % [nm, pair[0]])
	write("contract.txt")

# ---------------------------------------------------------------------------
# cost -- leave-one-out, interleaved A/B/A/B, median of medians
# ---------------------------------------------------------------------------
const COST_BLOCK: int = 56
const COST_REPS: int = 3

func _time_mask(s: Dictionary, m: int) -> float:
	pose_cam(s, 0.55, m, prev_tn_for(s, 0.55))
	await settle(10)
	var ts: Array = []
	for i in COST_BLOCK:
		var t0: int = Time.get_ticks_usec()
		await RenderingServer.frame_post_draw
		ts.append(float(Time.get_ticks_usec() - t0) / 1000.0)
	ts.sort()
	return float(ts[ts.size() / 2])

func _median(a: Array) -> float:
	a.sort()
	return float(a[a.size() / 2])

func run_cost(only: String) -> void:
	var s: Dictionary = find(only) if only != "" else shots[0]
	set_light(s)
	log_line("=== CINEMA cost, leave-one-out from the full stack ===")
	log_line("pose: %s at t=0.55, %s, 1920x1080, %d frames a block, %d blocks"
		% [s["name"], light_for(s), COST_BLOCK, COST_REPS])
	log_line("READ THE MACHINE STATE NOTE IN CINEMA.md BEFORE READING ANY OF THIS.")
	log_line("")
	var full: Array = []
	var none_: Array = []
	for r in COST_REPS:
		full.append(await _time_mask(s, CinemaGrade.ALL))
		none_.append(await _time_mask(s, CinemaGrade.E_TONEMAP))
	var f_ms: float = _median(full)
	var n_ms: float = _median(none_)
	log_line("%-10s %8.2f ms" % ["full stack", f_ms])
	log_line("%-10s %8.2f ms   -> the whole stack costs %.2f ms" % ["tonemap only", n_ms, f_ms - n_ms])
	log_line("")
	var total: float = 0.0
	for n in CinemaGrade.ORDER:
		if n == "tonemap":
			continue
		var bit: int = int(CinemaGrade.NAMES[n])
		var without: Array = []
		var with_: Array = []
		for r in COST_REPS:
			without.append(await _time_mask(s, CinemaGrade.ALL & ~bit))
			with_.append(await _time_mask(s, CinemaGrade.ALL))
		var dms: float = _median(with_) - _median(without)
		total += dms
		log_line("%-10s %8.2f ms  (full %.2f, without %.2f)" % [n, dms, _median(with_), _median(without)])
	log_line("")
	log_line("sum of leave-one-out deltas: %.2f ms   whole stack: %.2f ms" % [total, f_ms - n_ms])
	write("cost.txt")

# ---------------------------------------------------------------------------
# places -- the site anchor's vocabulary, resolved, so a shot can be authored
# against numbers rather than against a guess
# ---------------------------------------------------------------------------
func run_places() -> void:
	log_line("=== CINEMA places, seed %d ===" % int(rig.L.plan["seed"]))
	log_line("%-22s %28s %20s %8s" % ["place", "origin (x,y,z)", "axis", "ground"])
	var ids: Array = ["collar", "headframe", "gantry", "gate"]
	for b in rig.L.plan["buildings"]:
		ids.append("b:" + String(b["kind"]))
	for z in rig.L.plan["zones"]:
		ids.append("z:" + String(z["kind"]))
	for s in rig.L.plan["stations"]:
		ids.append("s:" + String(s["kind"]))
	for t in [0.0, 0.5, 1.0]:
		ids.append("road@%.1f" % t)
	for i in (rig.L.plan["walkways"] as Array).size():
		ids.append("walk%d@0.5" % i)
	for i in (rig.L.plan["course"]["nodes"] as Array).size():
		ids.append("course:%d" % i)
	for i in (rig.L.plan["columns"] as Array).size():
		ids.append("col%d" % i)
	for m in rig.L.plan["masts"]:
		ids.append("mast:" + String(m["kind"]))
	for id in ids:
		var fr: Array = rig.place(String(id))
		var o: Vector3 = fr[0]
		var f: Vector3 = fr[3]
		log_line("%-22s %9.2f %9.2f %9.2f   %6.2f %6.2f %6.2f  %7.2f" % [
			id, o.x, o.y, o.z, f.x, f.y, f.z, rig.ground_y(o)])
	log_line("")
	log_line("--- resolved shot anchors ---")
	for s in shots:
		log_line("%s" % s["name"])
		for k in ["move", "look"]:
			var dd: Dictionary = s[k]
			for e in ["from", "via", "to"]:
				if not dd.has(e):
					continue
				var p: Vector3 = rig.resolve(dd[e])
				log_line("    %-4s %-4s  %8.2f %8.2f %8.2f   ground %6.2f  above %6.2f" % [
					k, e, p.x, p.y, p.z, rig.ground_y(p), rig.floor_under(p)])
	write("places.txt")

# ---------------------------------------------------------------------------
# scout -- where could this camera stand?
# ---------------------------------------------------------------------------
# The cave sweeps the main drive with a shot as a template and reports the
# stations that would accept it. A site has no stations to sweep, so the sweep
# is over the shot's own anchor frame instead: shift the whole MOVE by (da, do)
# in the place's own axes, leave the LOOK where it is, and report which offsets
# validate. Same principle, and the cave's warning applies unchanged -- it is a
# LOCATION SCOUT, NOT A REPAIR. It says where a camera may stand; the shot list
# is still written by hand against the answer and the validator still governs
# what ships.
#
# The letter is the FIRST rule that rejected the offset, so the map reads as a
# picture of what is in the way:
#   .  accepts    b body    c near-plane clearance    h height band
#   u  buried     m no crane mount    t travel    s speed
func _shift(shot: Dictionary, da: float, do_: float) -> Dictionary:
	var s2: Dictionary = shot.duplicate(true)
	var mv: Dictionary = s2["move"]
	for k in ["from", "via", "to"]:
		if not mv.has(k) or not (mv[k] is Dictionary):
			continue
		var an: Dictionary = mv[k]
		an["a"] = float(an.get("a", 0.0)) + da
		an["o"] = float(an.get("o", 0.0)) + do_
	return s2

static func _code(v: Dictionary) -> String:
	if v["ok"]:
		return "."
	var f: String = String(v["fail"][0])
	if f.begins_with("body") or f.begins_with("swept"):
		return "b"
	if f.begins_with("frustum"):
		return "c"
	if f.begins_with("height") or f.begins_with("no ground"):
		return "h"
	if f.begins_with("camera is inside"):
		return "u"
	if f.begins_with("crane"):
		return "m"
	if f.begins_with("travels"):
		return "t"
	return "s"

func run_scout(only: String, span: float = 5.0, step: float = 1.0) -> void:
	var s: Dictionary = find(only)
	if s.is_empty():
		push_error("CINEMA: --cinema=scout needs --shot=NAME")
		return
	log_line("=== CINEMA scout: %s, move shifted in its own frame ===" % only)
	log_line("rows are `o` (right of the axis), columns are `a` (along it), in metres")
	var n: int = int(span / step)
	var hdr := "      "
	for i in range(-n, n + 1):
		hdr += "%5.1f" % (float(i) * step)
	log_line(hdr)
	var okn := 0
	var tot := 0
	for j in range(-n, n + 1):
		var row := "%5.1f " % (float(j) * step)
		for i in range(-n, n + 1):
			var v: Dictionary = rig.validate(_shift(s, float(i) * step, float(j) * step))
			var c: String = _code(v)
			if c == ".":
				okn += 1
			tot += 1
			row += "  %s  " % c
		log_line(row)
	log_line("")
	log_line("%d of %d offsets accept this shot" % [okn, tot])
	write("scout_%s.txt" % only)

# ---------------------------------------------------------------------------
# probe -- what, exactly, is in the way
# ---------------------------------------------------------------------------
func run_probe(only: String) -> void:
	var s: Dictionary = find(only)
	if s.is_empty():
		push_error("CINEMA: --cinema=probe needs --shot=NAME")
		return
	log_line("=== CINEMA probe: %s ===" % only)
	for tn in [0.0, 0.25, 0.5, 0.75, 1.0]:
		var ps: Dictionary = rig.pose(s, float(tn))
		var p: Vector3 = ps["pos"]
		log_line("t=%.2f  pos %7.2f %7.2f %7.2f   ground %6.2f  floor_under %6.2f  buried %d"
			% [tn, p.x, p.y, p.z, rig.ground_y(p), rig.floor_under(p), rig.buried(p)])
		var q := PhysicsShapeQueryParameters3D.new()
		q.shape = rig.body
		q.transform = Transform3D(Basis.IDENTITY, p)
		q.margin = CameraRig.QUERY_MARGIN
		q.collision_mask = 1
		var pts: PackedVector3Array = rig._ss().collide_shape(q, 24)
		for i in range(1, pts.size(), 2):
			var mark: String = "BREACH" if pts[i].y > p.y - CameraRig.GROUND_BAND else "ground"
			log_line("      contact %7.2f %7.2f %7.2f   dy %+6.2f   %s"
				% [pts[i].x, pts[i].y, pts[i].z, pts[i].y - p.y, mark])
		var res := PhysicsShapeQueryParameters3D.new()
		res.shape = rig.body
		res.transform = Transform3D(Basis.IDENTITY, p)
		res.margin = CameraRig.QUERY_MARGIN
		res.collision_mask = 1
		for hit in rig._ss().intersect_shape(res, 8):
			var col = hit["collider"]
			var si: int = int(hit["shape"])
			var who: String = rig.shape_names[si] if si < rig.shape_names.size() else "?"
			log_line("      overlaps shape %d -> %s" % [si, who])
	write("probe_%s.txt" % only)

# ---------------------------------------------------------------------------
# hdr -- what range of scene radiance is actually in front of the lens
# ---------------------------------------------------------------------------
## Bloom's threshold and the dirt's gate are both quoted in scene radiance, and
## the cave's numbers were measured against one 54-degree lamp in a black room.
## This writes lum/16 through the LINEAR tonemapper so the real range can be
## read back off the PNG. `tonemap_exposure` is per-preset, so it is printed
## alongside and divided out in hdrcheck.py.
func run_hdr() -> void:
	var d := dir_for("hdr/")
	log_line("=== CINEMA HDR probe (frame holds scene luminance / 16, LINEAR tonemap) ===")
	for s in shots:
		var nm: String = String(s["name"])
		if nm.begins_with("x"):
			continue
		if not rig.validate(s)["ok"]:
			continue
		set_light(s)
		pose_cam(s, 0.55, 0, -1.0)
		grade.lens.flags = CinemaLens.F_HDR
		env_linear()
		await settle(SETTLE_FIRST)
		grab(d + "%s.png" % nm)
		log_line("%-24s light %-9s tonemap_exposure %.3f" % [nm, light_for(s), grade.env.tonemap_exposure])
	write("hdr.txt")

func env_linear() -> void:
	grade.env.tonemap_mode = Environment.TONE_MAPPER_LINEAR
	grade.env.adjustment_enabled = false
	grade.env.glow_enabled = false

# ---------------------------------------------------------------------------
# lutbug -- the cave's 14.3% exposure cut, reproduced and then not inherited
# ---------------------------------------------------------------------------
## The cave found the colour grade taking 14.3% off the mean of the whole frame
## through a half-texel LUT lookup error, and recorded that it "did not look
## like a bug, it looked like a moody grade". A port of that code cannot claim
## to be clean by eye. This renders three frames from one camera -- grade off,
## grade on built correctly on (i+0.5)/N, and grade on built the WRONG way on
## i/(N-1) -- and lutcheck.py measures all three.
func run_lutbug(only: String) -> void:
	var s: Dictionary = find(only) if only != "" else shots[0]
	var d := dir_for("lutbug/")
	set_light(s)
	log_line("=== CINEMA LUT lookup check: %s at t=0.55 ===" % s["name"])
	var base: int = CinemaGrade.E_TONEMAP
	pose_cam(s, 0.55, base, -1.0)
	await settle(SETTLE_FIRST)
	grab(d + "grade_off.png")
	grade.lut_bug = false
	grade.rebuild_lut()
	pose_cam(s, 0.55, base | CinemaGrade.E_GRADE, -1.0)
	await settle(SETTLE_STEP)
	grab(d + "grade_on_correct.png")
	grade.lut_bug = true
	grade.rebuild_lut()
	pose_cam(s, 0.55, base | CinemaGrade.E_GRADE, -1.0)
	await settle(SETTLE_STEP)
	grab(d + "grade_on_halftexel_bug.png")
	grade.lut_bug = false
	grade.rebuild_lut()
	log_line("three frames written; run paircheck-style measurement in CINEMA.md 6.9")
	write("lutbug.txt")
