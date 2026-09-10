# ---------------------------------------------------------------------------
# BLINDSIDE -- the real machines, standing on the pit-head.
#
# WHAT THIS REPLACES. `props.gd` used to build every machine on the site out of
# 34 batched boxes. It was a stand-in written before `agent_model` had a glTF
# exporter, and TRAILER 11.2 is the bill: every machine in the rough cut is that
# box animal, and the designer read it off one frame. The chassis now come out
# of the shared machine layer -- `res://machines/`, a junction to the one
# physical copy in `spikes/godot/machines/shared/` -- so the pit-head, the cave
# and the machines spike are all driving the SAME geometry, the same ART 4
# shading, and the same gait.
#
# WHAT IT ADDS BEYOND "PUT A MACHINE THERE".
#
# 1. THE HERO IS ONE MACHINE AND IT IS NOT ONE OF THE EXTRAS. `hero.gd` names
#    it: a Surveyor in its default loadout, player skin, wear 0.35. This file
#    holds the site's other rule, which is the half a validator cannot check:
#    NO EXTRA ON THIS SITE IS A DEFAULT-LOADOUT SURVEYOR. The extras are Scouts,
#    Haulers, Swimmers and bare Surveyors, so the boom-and-sonar silhouette
#    belongs to exactly one machine in every frame of the pit-head. NOTES 8's
#    silhouette test is why: the Surveyor and the Swimmer separate ONLY by
#    loadout, so loadout is the thing that has to be reserved.
#
# 2. THE MACHINES ARE IN THE CAMERA'S COLLISION. TRAILER 8: "No shot passes
#    through solid matter. Not rock, not a prop, not a MACHINE." The batched
#    stand-ins were in the collision layer by accident, because they were props.
#    A real machine is a skinned mesh with no body, so each one gets a hull
#    proxy on LAYER 2, and the rig's clearance queries widened from mask 1 to
#    mask 3. Ground rays stay on mask 1 and so never hit a machine.
#
# 3. A MACHINE STANDS ON THE GROUND IT IS ON. Every one is handed
#    `Ground.height`, which is the height the dressing actually renders, so the
#    plane fit under its feet and the per-leg IK put it on the hardstanding
#    rather than on the layout's idea of it. On a graded pad that is a no-op;
#    on the course, where the relief runs to 4 m, it is the whole difference.
# ---------------------------------------------------------------------------
class_name Fleet
extends RefCounted

## Collision layer for machine hulls. 1 is the world; the camera sweeps 1|2.
const MACHINE_LAYER: int = 2

## What an extra may be. The default-loadout Surveyor is missing on purpose --
## see note 1 above. `surveyor_bare` is the same chassis with the magnetometer
## boom and the sonar face taken off, which is a different outline at any size.
const EXTRA_KINDS := [
	{"model": "scout", "chassis": "scout"},
	{"model": "hauler", "chassis": "hauler"},
	{"model": "swimmer", "chassis": "swimmer"},
	{"model": "surveyor_bare", "chassis": "surveyor"},
]

var root: Node3D
var L: SurfaceLayout
var rg: CameraRig
var hero: Machine = null
var extras: Array = []
var all: Array = []
var lines: Array[String] = []
var build_ms: float = 0.0
var tri_total: int = 0
var hero_home: Transform3D = Transform3D.IDENTITY
var _t: float = 0.0
## the hero's own gait, measured off its skeleton by Tracks.learn
var gait: Dictionary = {}
var _trk_shot: String = ""
var _trk_done: float = 0.0

## How far back along its own line a walking machine's track already runs when a
## shot opens, metres. GUESS, and it is an authoring decision rather than a
## physical one: the machine did not come into existence at t = 0, so a track
## that starts at the first frame's feet is a worse lie than one that does not.
## Eight metres is about six seconds of walking.
const APPROACH := 8.0


func gh(x: float, z: float) -> float:
	return Ground.height(L, x, z)


# ---------------------------------------------------------------------------
func build(p_root: Node3D, p_L: SurfaceLayout, slots: Array) -> void:
	var t0: int = Time.get_ticks_usec()
	root = p_root
	L = p_L
	# A rig with no collision: `place()` only reads the plan, and the machines
	# have to be able to name a place in exactly the grammar the shots do.
	rg = CameraRig.new()
	rg.L = L
	var g: Callable = Callable(self, "gh")

	# --- the hero. It is spawned first so it gets the first pick of everything
	# and so its index in `all` is stable at 0 for the contact sheet.
	hero = Hero.spawn(root, {
		"chassis": Hero.SPEC["chassis"], "loadout": Hero.SPEC["loadout"],
		"skin": Hero.SPEC["skin"], "wear": Hero.SPEC["wear"],
		"damage": Hero.SPEC["damage"], "clip": "idle",
	}, g)
	hero.name = "HeroMachine"
	# Its home when no shot has said otherwise: the muster square, one row south
	# of the four bays, facing the yard. Three requirements had to hold at once
	# and this is the only place on the site where they all do.
	#   IN DAYLIGHT. TRAILER 11.1 asks for it and the service bay interior is
	#     not: the first two passes of shot 6 were shot there and both came back
	#     with the machine against a dark corrugated wall 4 m behind it.
	#   ON THE GROUND. The first pass stood it on the hoist cradle, 0.72 m up,
	#     which is where a machine being serviced belongs and is exactly why it
	#     read as EQUIPMENT. A thing on a table is a thing being worked on. A
	#     thing standing on the floor at its own height, that you have to crouch
	#     to meet, is an animal. That is the whole of shot 6.
	#   WITH NOTHING TALL AND CLOSE BEHIND IT. At T4 and 1.9 m the far limit of
	#     focus is 2.45 m, so everything upstage is soft -- but soft black is
	#     still black. Looking north off the muster square there is ten metres
	#     of open hardstanding before anything, which is what puts the pale
	#     shell against a mid-grey ground instead of a hole.
	var home: Vector3 = _hero_home()
	_stand(hero, home, PI * 0.5)
	hero_home = hero.global_transform
	all.append(hero)
	_say("hero      %-14s at %6.2f %5.2f %6.2f  %s" % [Hero.model_of(Hero.SPEC),
		home.x, home.y, home.z, Hero.banner()])

	# --- the extras, one per slot props.gd recorded ------------------------
	var i: int = 0
	for s in slots:
		var pose: String = String(s["pose"])
		var pos: Vector3 = s["pos"]
		var kind: Dictionary = EXTRA_KINDS[i % EXTRA_KINDS.size()]
		var wear: float = clampf(float(s["wear"]), 0.05, 0.95)
		var dmg: float = 0.0
		var clip: String = "idle"
		if pose == "wreck":
			# NOTES 11.9's wreck: the crouch clip, rolled, every emissive dead,
			# the retro still returning. ART 6.2.
			dmg = 1.0
			clip = "crouch"
			kind = EXTRA_KINDS[1]
		elif pose == "dock":
			# ART 4.2 rung 0.75 drops the ride height 25 %; a docked machine is
			# doing the same thing for a different reason, and `crouch` is the
			# clip that folds the legs with the IK intact.
			clip = "crouch"
		var m: Machine = Hero.spawn(root, {
			"chassis": kind["chassis"], "model": kind["model"], "skin": "player",
			"wear": wear, "damage": dmg, "clip": clip,
			# ART 2.5: a work lamp burning in daylight on a parked machine is a
			# lighting mistake, not a detail. Only the hero carries one lit, and
			# only where the shot wants it.
			"lamp": false,
		}, g)
		m.name = "Extra%02d_%s" % [i, kind["model"]]
		if pose == "wreck":
			m.extra_roll = deg_to_rad(13.0)
			m.extra_pitch = deg_to_rad(-5.0)
		_stand(m, pos, s["yaw"])
		extras.append(m)
		all.append(m)
		i += 1

	for m2 in all:
		tri_total += m2.tri_count
		_proxy(m2)
	build_ms = float(Time.get_ticks_usec() - t0) / 1000.0
	_say("fleet     %d machines, %d triangles, %d draw surfaces, built in %.0f ms"
		% [all.size(), tri_total, all.size() * 2, build_ms])


## The muster square, on its centre line, 1.4 m south of the row of four bays.
## Read out of the zone rectangle rather than written as a coordinate, so a
## change of seed moves the machine with the square it is standing on.
func _hero_home() -> Vector3:
	for z in L.plan["zones"]:
		if String(z["kind"]) == "muster":
			var x: float = (float(z["x0"]) + float(z["x1"])) / 2000.0
			var zz: float = (float(z["z0"]) + float(z["z1"])) / 2000.0 - 2.4
			return Vector3(x, gh(x, zz), zz)
	return Vector3(0, 0, 0)


func _stand(m: Machine, pos: Vector3, yaw: float) -> void:
	m.global_position = pos
	m.rotation = Vector3(0, yaw, 0)
	# A machine on a stand is not on the ground; the terrain solver must not
	# drag it down to it.
	if pos.y > gh(pos.x, pos.z) + 0.25:
		m.ground = Callable()
	m.body_y = pos.y
	m._settled = false
	m.hold(0.0)


# --- the camera's view of a machine ----------------------------------------
## A box the size of the hull, on layer 2. Not the mesh: a skinned mesh's rest
## AABB is wrong the moment a leg swings, and the camera does not need to know
## about legs -- it needs to know it may not push through the body of the thing
## it is photographing.
func _proxy(m: Machine) -> void:
	var sb := StaticBody3D.new()
	sb.collision_layer = MACHINE_LAYER
	sb.collision_mask = 0
	var cs := CollisionShape3D.new()
	var bx := BoxShape3D.new()
	var hull: Vector3 = Book.CHASSIS[m.chassis]["hull"]
	bx.size = Vector3(hull.x, maxf(hull.z * 2.6, 0.26), hull.y)
	cs.shape = bx
	sb.add_child(cs)
	m.add_child(sb)
	sb.position = Vector3(0, Book.ride(m.chassis) * 0.55, 0)


# ---------------------------------------------------------------------------
# per-shot: put the hero where the shot says
# ---------------------------------------------------------------------------
## `at` is either one anchor (a hold) or {"from": anchor, "to": anchor} (a walk).
## The anchors are the pit-head's own site anchors, so a shot places its machine
## in the same grammar it places its camera, and `course:3` means the same thing
## to both.
func hero_pose(shot: Dictionary, tn: float, tsec: float) -> void:
	var m: Dictionary = Hero.block(shot)
	if m.is_empty():
		# No machine block: the hero is where it lives. It is on this site and
		# a frame that reaches the service bay should find it there.
		hero.visible = true
		hero.global_transform = hero_home
		hero.ground = Callable()
		hero.t = tsec
		hero.anim.seek(tsec, true)
		hero._post_pose()
		return
	if String(m.get("role", "")) != "hero":
		hero.visible = false
		return
	hero.visible = true
	hero.wear = float(m.get("wear", Hero.SPEC["wear"]))
	hero.damage = float(m.get("damage", Hero.SPEC["damage"]))
	hero.lamp_on = bool(m.get("lamp", false))
	hero.refresh()
	var clip: String = String(m.get("clip", "idle"))
	if hero.clip != clip:
		hero.set_clip(clip)
	hero.walking = false          # the node is placed by the shot, not driven

	var at = m.get("at", null)
	var p: Vector3 = hero_home.origin
	var yaw: float = hero_home.basis.get_euler().y
	var travel: Vector3 = Vector3.ZERO
	# A MOUNTED SHOT PLACES ITS MACHINE IN THE MOUNT'S FRAME TOO. Shot 14 is the
	# camera and the machine standing on the same descending cage deck, and a
	# machine placed by the site anchor while the camera is placed by the mount
	# is a machine standing in the yard while the camera is nine metres down a
	# shaft. There is also no ground in a shaft, so the terrain solver is off.
	if CameraRig.has_mount(shot):
		var org: Vector3 = rg.mount_at(shot, tn)
		p = org + (CameraRig._local(at) if at != null else Vector3.ZERO)
		var ym = m.get("yaw", null)
		hero.global_position = p
		hero.rotation = Vector3(0, deg_to_rad(float(ym)) if ym != null else 0.0, 0)
		hero.ground = Callable()
		var hdm = m.get("head", null)
		if hdm is Array and (hdm as Array).size() == 2 and not (hdm[0] is Array):
			hero.look_at_local(float(hdm[0]), float(hdm[1]))
		_t = tsec
		hero.t = _t
		hero.anim.seek(_t, true)
		hero._post_pose()
		hero.body_y = p.y
		hero._settled = true
		return
	if at is Dictionary and (at as Dictionary).has("from"):
		var a: Vector3 = _anchor(at["from"])
		var b: Vector3 = _anchor(at["to"])
		_mark(shot, a, b, tn, clip)
		# LINEAR, and never eased. The camera has mass and eases; the machine's
		# feet are BAKED, planted in world space at exactly the clip's speed
		# (NOTES 5: "any other speed and it skates"). Easing the machine's
		# travel would make it skate at both ends of every shot, which is the
		# single most obvious tell that a walk cycle is being faked.
		p = a.lerp(b, tn)
		travel = b - a
	elif at != null:
		p = _anchor(at)
	var y = m.get("yaw", null)
	if y is String and String(y) == "path" and travel.length() > 0.01:
		yaw = atan2(-travel.z, travel.x)
	elif y != null:
		yaw = deg_to_rad(float(y))

	var hd = m.get("head", null)
	if hd is Array and (hd as Array).size() == 2:
		# head aim: either a fixed [yaw, pitch] or [[yaw0,pitch0],[yaw1,pitch1]]
		# The head aim may itself be animated across the shot, which is what
		# makes the machine read as looking at something rather than as posed.
		var h0: Array = hd
		if (hd[0] is Array):
			h0 = [lerpf(float(hd[0][0]), float(hd[1][0]), _ease(tn)),
				  lerpf(float(hd[0][1]), float(hd[1][1]), _ease(tn))]
		hero.look_at_local(float(h0[0]), float(h0[1]))

	hero.global_position = p
	hero.rotation = Vector3(0, yaw, 0)
	hero.ground = Callable(self, "gh") if p.y <= gh(p.x, p.z) + 0.25 else Callable()
	# The clip is advanced by the SHOT'S clock and not the wall clock. Offline
	# capture renders every frame dozens of times over to let the shadow atlas
	# and the sky radiance settle, so anything driven by the frame clock runs
	# the gait thirty times too fast; anything driven by `tn` alone runs it at
	# whatever speed the shot happens to be. `tsec` is seconds into the shot,
	# which is the only clock that makes the walk land at 0.50 m/s.
	_t = tsec
	hero.t = _t
	hero.anim.seek(_t, true)
	hero._post_pose()
	hero.body_y = p.y
	hero._settled = false
	hero._terrain(1.0)


## THE MACHINE'S OWN ROUTE, BEHIND IT, AS IT WALKS.
##
## ACT-ONE 8.4: "Shot 7 is a machine walking a course in snow and THE SNOW
## BEHIND IT IS UNTOUCHED. It is the only place in this act where the frame
## actively contradicts the design." This is the line that fixes it.
##
## It replays the MEASURED gait along the part of the shot's own path that has
## already happened, which is deterministic, frame-rate independent and exactly
## reproducible - the same track whether a shot is rendered at three frames or
## at a hundred and twenty. Reading the skeleton's feet every frame would be more
## direct and would put a hole in the track wherever the capture skipped a
## plant, and `--cinema=look` renders t = 0.06, 0.50 and 0.94 and nothing else.
func _mark(shot: Dictionary, a: Vector3, b: Vector3, tn: float, clip: String) -> void:
	if gait.is_empty() or clip != "walk":
		return
	var nm: String = String(shot.get("name", ""))
	var p0 := Vector2(a.x, a.z)
	var p1 := Vector2(b.x, b.z)
	var total: float = p0.distance_to(p1)
	if total < 0.05:
		return
	var dir: Vector2 = (p1 - p0) / total
	# the whole line, INCLUDING the approach it walked in on
	var line := PackedVector2Array([p0 - dir * APPROACH, p1])
	if nm != _trk_shot or tn * total + APPROACH < _trk_done - 0.01:
		_trk_shot = nm
		_trk_done = 0.0
	var d: float = APPROACH + tn * total
	if d <= _trk_done + 0.001:
		return
	Tracks.walk(gait, line, 0.0, 0.0, 0.044, _trk_done, d)
	_trk_done = d


func reset_clock() -> void:
	_t = 0.0
	hero._settled = false
	_trk_shot = ""
	_trk_done = 0.0


static func _ease(t: float) -> float:
	return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)


## The rig's OWN resolver, not a copy of it. A machine placed by a different
## function than the camera that photographs it is a continuity bug waiting for
## a seed change.
func _anchor(a) -> Vector3:
	return rg.resolve(a)


func _say(s: String) -> void:
	lines.append(s)
	print(s)
