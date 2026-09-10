# ---------------------------------------------------------------------------
# BLINDSIDE machines spike -- one machine.
#
# Loads a chassis from agent_model's .glb, collapses it to two draw calls,
# rebuilds the surfacing against ART-DIRECTION section 4, hangs the work lamp
# off the head, and drives the walk.
#
# WHAT THE .GLB BRINGS: geometry, the armature, and the gait baked to FK by
# agent_model/export_gltf.py. Nothing here invents a proportion.
# WHAT IS REBUILT HERE: the surfacing, the lamp, team, wear, damage, and the
# terrain response. Blender materials do not survive glTF in a useful form and
# were never meant to.
# ---------------------------------------------------------------------------
class_name Machine
extends Node3D

const MODELS := "res://models/%s_%s.glb"
const CLIPS := ["walk", "trot", "idle", "crouch"]

var chassis: String = "surveyor"
var model_name: String = "surveyor"
var team: String = "player"
var wear: float = 0.35
var damage: float = 0.0
var lamp_on: bool = true
var pinging: bool = false
var beacons_left: int = 4

var skel: Skeleton3D
var mi: MeshInstance3D
var anim: AnimationPlayer
var lamp: SpotLight3D
var mat_body: ShaderMaterial
var mat_retro: ShaderMaterial

var clip: String = "walk"
var walking: bool = false
var t: float = 0.0

# per-leg: [coxa, femur, tibia] bone indices and the foot point in tibia space
var legs: Array = []
var b_pan: int = -1
var b_tilt: int = -1
var head_yaw: float = 0.0
var head_pitch: float = 0.0
# The pan and tilt bones point along the machine's FORWARD (Blender builds them
# head-to-tail down +X), and a Blender bone's local +Y is its own axis. So
# rotating the pan bone about local +Y ROLLS the head, it does not pan it --
# which is why the first version of this aimed a lamp 40 degrees off and the
# frame came back black. The axes are taken from the bone's own rest basis
# instead of assumed.
var pan_axis: Vector3 = Vector3.UP
var tilt_axis: Vector3 = Vector3.RIGHT

# measured at build
var tri_count: int = 0
var draw_surfaces: int = 0
var bone_count: int = 0
var build_ms: float = 0.0
var stand_height: float = 0.4
var body_len: float = 0.58

# terrain
var ground: Callable = Callable()
var body_y: float = 0.0
var body_pitch: float = 0.0
var body_roll: float = 0.0
var _settled: bool = false
# a wreck lies over. The terrain solver owns pitch and roll, so anything else
# that wants to tilt the body has to go through it rather than round it.
var extra_roll: float = 0.0
var extra_pitch: float = 0.0


# `model` is the .glb prefix and `ch` is the chassis class. They differ for
# loadout variants (surveyor_bare), and the class is what the numbers key off.
func build(model: String, ch: String, tm: String = "player", wr: float = 0.35,
		   dmg: float = 0.0) -> void:
	var t0: int = Time.get_ticks_usec()
	model_name = model
	chassis = ch
	team = tm
	wear = wr
	damage = dmg
	var ps: PackedScene = load(MODELS % [model, "walk"])
	var root: Node = ps.instantiate()
	add_child(root)
	skel = _find(root, "Skeleton3D") as Skeleton3D
	mi = _find(root, "MeshInstance3D") as MeshInstance3D
	anim = _find(root, "AnimationPlayer") as AnimationPlayer
	bone_count = skel.get_bone_count()

	_gather_clips()
	_index_bones()
	_make_materials()
	_collapse_surfaces()
	_make_lamp()

	var ab: AABB = mi.get_aabb()
	stand_height = ab.size.y
	body_len = Book.hull_len(ch)
	# a skinned mesh is culled on its REST aabb, and a leg in swing leaves it
	mi.extra_cull_margin = 1.0
	# ART 2.4: the outline is the loadout readout, so it must not be eaten by
	# the shadow of the thing casting it
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
	build_ms = float(Time.get_ticks_usec() - t0) / 1000.0
	set_clip("idle")
	refresh()


# --- every clip in one AnimationPlayer -------------------------------------
func _gather_clips() -> void:
	var lib: AnimationLibrary = anim.get_animation_library("")
	for c in CLIPS:
		if lib.has_animation(c):
			continue
		var p: String = MODELS % [model_name, c]
		if not ResourceLoader.exists(p):
			continue
		var other: Node = (load(p) as PackedScene).instantiate()
		var oap: AnimationPlayer = _find(other, "AnimationPlayer") as AnimationPlayer
		for l in oap.get_animation_library_list():
			for n in oap.get_animation_library(l).get_animation_list():
				lib.add_animation(n, oap.get_animation_library(l).get_animation(n).duplicate())
		other.queue_free()
	for c in lib.get_animation_list():
		var a: Animation = lib.get_animation(c)
		a.loop_mode = Animation.LOOP_LINEAR
	# The clip is advanced by hand so that the damage pose and the terrain
	# response can be applied AFTER it and not be overwritten by it. With the
	# mixer on its own callback the ordering is a race.
	anim.callback_mode_process = AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_MANUAL


func _index_bones() -> void:
	legs.clear()
	b_pan = skel.find_bone("pan")
	b_tilt = skel.find_bone("tilt")
	if b_pan >= 0:
		# pan is a rotation about the machine's UP, expressed in pan-bone space
		pan_axis = (skel.get_bone_global_rest(b_pan).basis.inverse() * Vector3(0, 1, 0)).normalized()
	if b_tilt >= 0:
		# tilt is a rotation about the machine's LATERAL axis
		tilt_axis = (skel.get_bone_global_rest(b_tilt).basis.inverse() * Vector3(0, 0, 1)).normalized()
	var i: int = 0
	while true:
		var c: int = skel.find_bone("coxa.%d" % i)
		if c < 0:
			break
		legs.append({"coxa": c, "femur": skel.find_bone("femur.%d" % i),
					 "tibia": skel.find_bone("tibia.%d" % i),
					 "foot": Vector3.ZERO, "world": Vector3.ZERO})
		i += 1


# --- ART section 4, rebuilt -------------------------------------------------
func _make_materials() -> void:
	mat_body = ShaderMaterial.new()
	mat_body.shader = load("res://machine.gdshader")
	mat_retro = ShaderMaterial.new()
	mat_retro.shader = load("res://retro.gdshader")
	for m in [mat_body, mat_retro]:
		m.set_shader_parameter("dark_col", _lin(Color(0.09, 0.09, 0.10)))
	mat_body.set_shader_parameter("pale_col", _lin(Book.PALE))
	mat_body.set_shader_parameter("graphite_col", _lin(Book.GRAPHITE))
	mat_body.set_shader_parameter("accent_col", _lin(Book.ACCENT))
	mat_body.set_shader_parameter("bare_col", _lin(Book.BARE))
	mat_body.set_shader_parameter("bare_leg_col", _lin(Book.BARE_LEG))
	mat_body.set_shader_parameter("rubber_col", _lin(Color(0.035, 0.035, 0.038)))
	mat_body.set_shader_parameter("estop_col", _lin(Color(0.6, 0.04, 0.03)))
	mat_body.set_shader_parameter("mud_col", _lin(Book.MUD))
	mat_body.set_shader_parameter("dust_col", _lin(Book.DUST))
	mat_body.set_shader_parameter("warm_dim", _lin(Book.WARM_DIM))
	mat_body.set_shader_parameter("hurt_col", _lin(Book.HURT))
	mat_body.set_shader_parameter("kill_col", _lin(Book.KILL))
	mat_body.set_shader_parameter("lamp_col", _lin(Book.LAMP))


static func _lin(c: Color) -> Vector3:
	var l: Color = c.srgb_to_linear()
	return Vector3(l.r, l.g, l.b)


# Twelve Blender material slots arrive as twelve surfaces. They are collapsed
# to TWO -- the body and the retroreflective strips -- because the part
# identity that used to be carried by the material slot now rides in the UV.
# The split is by part index, not by material: `light_strip` in Blender covers
# the sonar bar, the running lights, the status pilot and the beacon caps, and
# ART 4.5 makes the running lights a different KIND of thing from the rest.
func _collapse_surfaces() -> void:
	var src: ArrayMesh = mi.mesh
	var buckets := [_new_bucket(), _new_bucket()]     # 0 body, 1 retro
	for s in range(src.get_surface_count()):
		var a: Array = src.surface_get_arrays(s)
		var uv: PackedVector2Array = a[Mesh.ARRAY_TEX_UV]
		var idx: PackedInt32Array = a[Mesh.ARRAY_INDEX]
		# fast path: a whole surface is one bucket unless it is the mixed one
		var any_retro: bool = false
		var all_retro: bool = true
		for u in uv:
			var p: int = int(floor(u.x * 256.0 / 16.0 + 0.0001))
			if p == Book.P_RETRO:
				any_retro = true
			else:
				all_retro = false
		if not any_retro:
			_append(buckets[0], a, idx)
		elif all_retro:
			_append(buckets[1], a, idx)
		else:
			_split(buckets, a, idx, uv)
	var out := ArrayMesh.new()
	tri_count = 0
	for b in range(2):
		var bk: Dictionary = buckets[b]
		if (bk["idx"] as PackedInt32Array).size() == 0:
			continue
		var arr := []
		arr.resize(Mesh.ARRAY_MAX)
		arr[Mesh.ARRAY_VERTEX] = bk["v"]
		arr[Mesh.ARRAY_NORMAL] = bk["n"]
		arr[Mesh.ARRAY_TEX_UV] = bk["uv"]
		arr[Mesh.ARRAY_TEX_UV2] = bk["uv2"]
		arr[Mesh.ARRAY_BONES] = bk["bn"]
		arr[Mesh.ARRAY_WEIGHTS] = bk["wt"]
		arr[Mesh.ARRAY_INDEX] = bk["idx"]
		out.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arr)
		out.surface_set_material(out.get_surface_count() - 1,
								 mat_body if b == 0 else mat_retro)
		tri_count += (bk["idx"] as PackedInt32Array).size() / 3
	mi.mesh = out
	draw_surfaces = out.get_surface_count()
	_measure_feet(buckets[0])


func _new_bucket() -> Dictionary:
	return {"v": PackedVector3Array(), "n": PackedVector3Array(),
			"uv": PackedVector2Array(), "uv2": PackedVector2Array(),
			"bn": PackedInt32Array(), "wt": PackedFloat32Array(),
			"idx": PackedInt32Array()}


func _append(bk: Dictionary, a: Array, idx: PackedInt32Array) -> void:
	var base: int = (bk["v"] as PackedVector3Array).size()
	bk["v"].append_array(a[Mesh.ARRAY_VERTEX])
	bk["n"].append_array(a[Mesh.ARRAY_NORMAL])
	bk["uv"].append_array(a[Mesh.ARRAY_TEX_UV])
	bk["uv2"].append_array(a[Mesh.ARRAY_TEX_UV2])
	bk["bn"].append_array(a[Mesh.ARRAY_BONES])
	bk["wt"].append_array(a[Mesh.ARRAY_WEIGHTS])
	var d := PackedInt32Array()
	d.resize(idx.size())
	for i in range(idx.size()):
		d[i] = idx[i] + base
	bk["idx"].append_array(d)


func _split(buckets: Array, a: Array, idx: PackedInt32Array, uv: PackedVector2Array) -> void:
	var remap := [{}, {}]
	var i: int = 0
	while i < idx.size():
		var p: int = int(floor(uv[idx[i]].x * 256.0 / 16.0 + 0.0001))
		var b: int = 1 if p == Book.P_RETRO else 0
		var bk: Dictionary = buckets[b]
		for k in range(3):
			var vi: int = idx[i + k]
			if not remap[b].has(vi):
				remap[b][vi] = (bk["v"] as PackedVector3Array).size()
				bk["v"].push_back(a[Mesh.ARRAY_VERTEX][vi])
				bk["n"].push_back(a[Mesh.ARRAY_NORMAL][vi])
				bk["uv"].push_back(a[Mesh.ARRAY_TEX_UV][vi])
				bk["uv2"].push_back(a[Mesh.ARRAY_TEX_UV2][vi])
				for c in range(4):
					bk["bn"].push_back(a[Mesh.ARRAY_BONES][vi * 4 + c])
					bk["wt"].push_back(a[Mesh.ARRAY_WEIGHTS][vi * 4 + c])
			bk["idx"].push_back(remap[b][vi])
		i += 3


# The foot is the lowest vertex weighted to each tibia bone. glTF carries no
# bone length, so this is the only way to find where the machine touches the
# ground -- and it is exact, because the ball foot IS the lowest thing on the
# leg.
func _measure_feet(bk: Dictionary) -> void:
	var v: PackedVector3Array = bk["v"]
	var bn: PackedInt32Array = bk["bn"]
	var lowest := {}
	for li in range(legs.size()):
		lowest[legs[li]["tibia"]] = Vector3(0, 1e9, 0)
	for i in range(v.size()):
		var b: int = bn[i * 4]
		if lowest.has(b) and v[i].y < lowest[b].y:
			lowest[b] = v[i]
	for li in range(legs.size()):
		var tb: int = legs[li]["tibia"]
		var rest: Transform3D = skel.get_bone_global_rest(tb)
		# the ball's lowest point, expressed in the tibia bone's own frame
		legs[li]["foot"] = rest.affine_inverse() * lowest[tb]


# --- the lamp ---------------------------------------------------------------
# ART 2.1: white (1.00, 0.98, 0.95) for EVERY team, 50 degree cone, tilted 8-10
# degrees down. ART 2.5 kills the team-tinted lamp; build.py still tints it, so
# the tint is dropped here along with the rest of the Blender material state.
func _make_lamp() -> void:
	var att := BoneAttachment3D.new()
	att.bone_idx = b_tilt
	att.set_use_external_skeleton(false)
	skel.add_child(att)
	att.bone_name = skel.get_bone_name(b_tilt)

	lamp = SpotLight3D.new()
	lamp.light_color = Book.LAMP
	# Re-derived on this renderer rather than inherited. ART 2.2 is explicit
	# that watts do not survive the move between renderers and that the RATIOS
	# are the durable part: floor 3 m ahead about 0.08 relative luminance, near
	# wall blown, roughly 90:1 across three metres.
	lamp.light_energy = 5.2
	lamp.spot_range = 24.0
	lamp.spot_angle = 25.0                 # a 50 degree cone
	lamp.spot_angle_attenuation = 0.42
	# Godot's attenuation parameter is the DECAY EXPONENT of a windowed inverse
	# square, so the default 1.0 is 1/d and lights the whole throw evenly. The
	# cave spike measured this as the single difference between a lit level and
	# a carried lamp.
	lamp.spot_attenuation = 2.0
	lamp.shadow_enabled = true
	lamp.shadow_bias = 0.012
	lamp.shadow_normal_bias = 0.9
	lamp.light_specular = 1.0
	att.add_child(lamp)

	# Place it where build.py places it -- on the head, at the eye, offset down
	# and forward -- but expressed in the tilt bone's own frame, because glTF
	# has rotated everything into Y-up and the bone's local axes are Blender's.
	var rest: Transform3D = skel.get_bone_global_rest(b_tilt)
	var inv: Basis = rest.basis.inverse()
	var fwd_local: Vector3 = (inv * Vector3(1, 0, 0)).normalized()   # machine forward
	var up_local: Vector3 = (inv * Vector3(0, 1, 0)).normalized()
	var side_local: Vector3 = (inv * Vector3(0, 0, 1)).normalized()
	var hr: float = Book.hull_len(chassis) * 0.11
	# ART 0: the lamp fires FORWARD. In agent_model it fires into its own eye
	# lens at 14 mm because of one sign, and every dark render in that repo is
	# graded against the broken rig. Here the aim is asserted, not inherited,
	# and mach_root prints the beam direction with every shot so it cannot
	# quietly break again.
	var aim: Vector3 = (fwd_local - up_local * tan(deg_to_rad(9.0))).normalized()
	var b := Basis.looking_at(aim, up_local)
	# A lamp on the view axis produces no form, because the light and view
	# vectors coincide and nothing is shadowed. The model already separates the
	# reflector from the camera laterally; this keeps that separation and adds
	# a little more, so the machine's own optical sensor sees modelling.
	var off: Vector3 = fwd_local * (hr * 0.75 + 0.02) - up_local * (hr * 0.15) + side_local * (hr * 0.30)
	lamp.transform = Transform3D(b, off)


# --- state ------------------------------------------------------------------
func refresh() -> void:
	var rival: bool = team == "rival"
	var tc: Vector3 = _lin(Book.EMBER if rival else Book.BONE)
	mat_body.set_shader_parameter("invert", 1.0 if rival else 0.0)
	mat_body.set_shader_parameter("team_col", tc)
	mat_retro.set_shader_parameter("team_col", tc)
	# ART 4.3: value is necessary and not sufficient; the rest has to come from
	# layout and RHYTHM. With no always-on emissive left after 4.5, rhythm is
	# read spatially: the player's strip is continuous, the rival's is dashed.
	mat_retro.set_shader_parameter("rhythm", 1.0 if rival else 0.0)
	# ART 4.1's three masks, in the ratios the vision board used for its rungs
	mat_body.set_shader_parameter("mud", clampf(wear * 1.18, 0.0, 1.0))
	mat_body.set_shader_parameter("dust", clampf(wear * 0.95, 0.0, 1.0))
	mat_body.set_shader_parameter("scuff", clampf(wear * 1.06, 0.0, 1.0))
	mat_body.set_shader_parameter("damage", damage)
	var dead: float = 1.0 if damage >= 1.0 else 0.0
	mat_body.set_shader_parameter("dead", dead)
	mat_retro.set_shader_parameter("dead", 0.0)   # ART 6.2: a wreck still returns
	mat_body.set_shader_parameter("pinging", 1.0 if pinging else 0.0)
	mat_body.set_shader_parameter("beacons_left", float(beacons_left))
	var on: bool = lamp_on and damage < 1.0
	mat_body.set_shader_parameter("lamp_on", 1.0 if on else 0.0)
	if lamp:
		lamp.visible = on


func set_emissive_running_lights(on: bool) -> void:
	mat_retro.set_shader_parameter("emissive_mode", 1.0 if on else 0.0)


func set_clip(c: String) -> void:
	clip = c
	if anim.has_animation(c):
		anim.play(c)
		anim.seek(0.0, true)


func set_walking(on: bool, c: String = "walk") -> void:
	walking = on
	set_clip(c if on else "idle")


# Park the clip at one time and re-apply everything that comes after it.
# `look_at_local` is an offset ON TOP of the clip, and the idle clip is a head
# SCAN -- so a machine settled for 0.8 s of idle is already looking 46 degrees
# off before anything here is asked for. Two frames in this spike came out with
# their captions swapped for exactly that reason.
func hold(tsec: float) -> void:
	anim.seek(tsec, true)
	_post_pose()
	_terrain(1.0)


func look_at_local(yaw_deg: float, pitch_deg: float) -> void:
	head_yaw = deg_to_rad(yaw_deg)
	head_pitch = deg_to_rad(pitch_deg)


# --- the walk ---------------------------------------------------------------
# The clip is baked IN PLACE: agent_model plants feet in world space, so
# stripping the body's travel leaves the stance feet moving backwards under the
# body at exactly the gait's speed. Move the node forward at that same speed
# and the feet are stationary on the ground. Any other speed and it skates.
func advance(dt: float) -> void:
	t += dt
	anim.advance(dt)
	if walking:
		var v: float = Book.speed(chassis, clip)
		global_position += global_transform.basis.x * v * dt
	_post_pose()
	_terrain(dt)


func _post_pose() -> void:
	# ART 4.2 rung 0.30: "the gait acquires a hitch". motion.py already has
	# per-leg timing in Blender; here the clip is baked, so the hitch is a
	# lurch added to one leg after the pose -- one foot dragging half a beat.
	if damage >= 0.30 and damage < 1.0 and legs.size() > 0:
		var ph: float = fposmod(t / 0.6, 1.0)
		var hitch: float = maxf(0.0, sin(ph * TAU)) * 0.22 * clampf((damage - 0.2) * 2.0, 0.0, 1.0)
		var f: int = legs[1]["femur"]
		skel.set_bone_pose_rotation(f, skel.get_bone_pose_rotation(f)
			* Quaternion(tilt_axis, hitch))
	# ART 4.2 rung 0.75: "the head stops tracking and jitters". A machine that
	# can no longer look where it is going is the most legible damage there is,
	# because the lamp goes with the head.
	if b_pan >= 0:
		var yaw: float = head_yaw
		var pitch: float = head_pitch
		if damage >= 0.75:
			yaw = deg_to_rad(50.0) + sin(t * 23.0) * 0.035
			pitch = deg_to_rad(-22.0) + sin(t * 31.0) * 0.03
		# To add a rotation about a WORLD axis on top of an animated pose, the
		# rotation has to be PRE-multiplied in the PARENT's space. Applying it
		# after the pose, about the bone's own axes, rotates about whatever the
		# clip happens to have left the bone pointing at -- which is how a lamp
		# asked to swing 46 degrees swung an unrelated amount and two frames in
		# this spike came out with their captions swapped.
		if absf(yaw) > 0.0001:
			var pp: int = skel.get_bone_parent(b_pan)
			var pb: Basis = skel.get_bone_global_pose(pp).basis if pp >= 0 else Basis.IDENTITY
			skel.set_bone_pose_rotation(b_pan,
				Quaternion((pb.inverse() * Vector3(0, 1, 0)).normalized(), yaw)
				* skel.get_bone_pose_rotation(b_pan))
		if b_tilt >= 0 and absf(pitch) > 0.0001:
			var tb2: Basis = skel.get_bone_global_pose(b_pan).basis
			skel.set_bone_pose_rotation(b_tilt,
				Quaternion((tb2.inverse() * Vector3(0, 0, 1)).normalized(), pitch)
				* skel.get_bone_pose_rotation(b_tilt))


# --- the ground -------------------------------------------------------------
# The body rides on a plane fitted through where the feet actually are. On flat
# ground that is a no-op; over broken ground it is what makes the machine look
# like it weighs something, because the hull leans before the leg has finished
# taking the load.
func _terrain(dt: float) -> void:
	if not ground.is_valid():
		return
	# 1. where the clip has put each foot, in the world
	var pts: Array = []
	for l in legs:
		var w: Vector3 = _foot_world(l)
		l["world"] = w
		pts.append(w)
	# 2. fit a plane y = a*x + b*z + c through the GROUND under those feet
	var n: float = float(pts.size())
	var sx := 0.0
	var sz := 0.0
	var sy := 0.0
	var sxx := 0.0
	var szz := 0.0
	var sxz := 0.0
	var sxy := 0.0
	var szy := 0.0
	for p in pts:
		var h: float = ground.call(p.x, p.z)
		sx += p.x; sz += p.z; sy += h
		sxx += p.x * p.x; szz += p.z * p.z; sxz += p.x * p.z
		sxy += p.x * h; szy += p.z * h
	var mx: float = sx / n
	var mz: float = sz / n
	var my: float = sy / n
	var cxx: float = sxx - n * mx * mx
	var czz: float = szz - n * mz * mz
	var cxz: float = sxz - n * mx * mz
	var cxy: float = sxy - n * mx * my
	var czy: float = szy - n * mz * my
	var det: float = cxx * czz - cxz * cxz
	var a: float = 0.0
	var b: float = 0.0
	if absf(det) > 1e-9:
		a = (cxy * czz - czy * cxz) / det
		b = (czy * cxx - cxy * cxz) / det
	var here: Vector3 = global_position
	var h0: float = my + a * (here.x - mx) + b * (here.z - mz)
	# Body forward is +X, up is +Y, lateral is +Z (glTF Y-up put Blender's +X
	# forward on Godot's +X). rotate_object_local(+Z) takes X toward Y, so
	# ground rising ahead (a > 0) is nose UP; rotate_object_local(+X) takes Y
	# toward Z, so ground rising to +Z must tilt the body up toward -Z.
	var pitch: float = atan(a)
	var roll: float = -atan(b)
	# 3. the body follows the plane, LATE. The lag is the whole point: a hull
	# that snaps to the plane reads as a camera move, and a hull that arrives a
	# beat after the foot reads as mass.
	var k: float = 1.0 - exp(-dt * 7.0)
	if not _settled:
		k = 1.0
		_settled = true
	body_y = lerpf(body_y, h0, k)
	body_pitch = lerpf(body_pitch, pitch, k)
	body_roll = lerpf(body_roll, roll, k)
	var yaw: float = rotation.y
	global_position = Vector3(here.x, body_y, here.z)
	rotation = Vector3(0, yaw, 0)
	rotate_object_local(Vector3(0, 0, 1), body_pitch + extra_pitch)
	rotate_object_local(Vector3(1, 0, 0), body_roll + extra_roll)
	# 4. and then each foot is put back ON THE GROUND, keeping whatever lift
	# the clip gave it. Without this the body leans correctly and the feet
	# still sink into the rock, which is worse than not leaning at all.
	for l in legs:
		var w: Vector3 = _foot_world(l)
		var lift: float = maxf(0.0, (global_transform.affine_inverse() * w).y)
		_ik(l, Vector3(w.x, ground.call(w.x, w.z) + lift, w.z))


func _foot_world(l: Dictionary) -> Vector3:
	# skel is a descendant of this node, so its global transform already
	# carries the machine's -- multiplying by both double-counts it.
	return skel.global_transform * (skel.get_bone_global_pose(l["tibia"]) * l["foot"])


# Two-bone IK onto a world target, applied AFTER the clip.
#
# The clip is the gait and it is not touched; this only corrects where the foot
# ENDS UP, which on flat ground is a no-op and over broken ground is the
# difference between walking and wading. The knee is kept in the plane it is
# already in, so the correction cannot flip a leg inside out.
func _ik(l: Dictionary, target_world: Vector3) -> void:
	var fb: int = l["femur"]
	var tb: int = l["tibia"]
	var inv: Transform3D = skel.global_transform.affine_inverse()
	var T: Vector3 = inv * target_world
	var gf: Transform3D = skel.get_bone_global_pose(fb)
	var gt: Transform3D = skel.get_bone_global_pose(tb)
	var Hp: Vector3 = gf.origin                       # hip
	var K: Vector3 = gt.origin                        # knee
	var F: Vector3 = gt * l["foot"]                   # foot, now
	var l1: float = (K - Hp).length()
	var l2: float = (F - K).length()
	if l1 < 1e-5 or l2 < 1e-5:
		return
	var d: Vector3 = T - Hp
	var r: float = clampf(d.length(), absf(l1 - l2) + 1e-4, l1 + l2 - 1e-4)
	if r < 1e-5:
		return
	var dir: Vector3 = d.normalized()
	# the knee's own plane: keep it
	var nrm: Vector3 = dir.cross(K - Hp)
	if nrm.length() < 1e-6:
		nrm = dir.cross(Vector3(0, 0, 1))
	if nrm.length() < 1e-6:
		return
	nrm = nrm.normalized()
	var ca: float = clampf((r * r + l1 * l1 - l2 * l2) / (2.0 * r * l1), -1.0, 1.0)
	var ang: float = acos(ca)
	# two solutions; take the one the leg is already nearest, so the knee does
	# not snap through
	var k1: Vector3 = Hp + dir.rotated(nrm, ang) * l1
	var k2: Vector3 = Hp + dir.rotated(nrm, -ang) * l1
	var Kn: Vector3 = k1 if (k1 - K).length_squared() <= (k2 - K).length_squared() else k2
	# femur: rotate it so its tip lands on the new knee
	var q1: Quaternion = Quaternion((K - Hp).normalized(), (Kn - Hp).normalized())
	_set_global(fb, Transform3D(Basis(q1) * gf.basis, Hp))
	# tibia: re-read (it moved with the femur) and rotate it onto the target
	var gt2: Transform3D = skel.get_bone_global_pose(tb)
	var F2: Vector3 = gt2 * l["foot"]
	var K2: Vector3 = gt2.origin
	if (F2 - K2).length() < 1e-5 or (T - K2).length() < 1e-5:
		return
	var q2: Quaternion = Quaternion((F2 - K2).normalized(), (T - K2).normalized())
	_set_global(tb, Transform3D(Basis(q2) * gt2.basis, K2))


func _set_global(b: int, g: Transform3D) -> void:
	var par: int = skel.get_bone_parent(b)
	var pg: Transform3D = skel.get_bone_global_pose(par) if par >= 0 else Transform3D.IDENTITY
	var loc: Transform3D = pg.affine_inverse() * g
	skel.set_bone_pose_position(b, loc.origin)
	skel.set_bone_pose_rotation(b, loc.basis.get_rotation_quaternion())


func _find(n: Node, cls: String) -> Node:
	if n.get_class() == cls:
		return n
	for c in n.get_children():
		var r: Node = _find(c, cls)
		if r:
			return r
	return null
