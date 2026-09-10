# ---------------------------------------------------------------------------
# BLINDSIDE -- the machine, underground.
#
# The cave spike has never had a machine in it. Its own shot list says so, in
# the note over trailer shot 17: "There is no machine in this spike: this
# executes as the plate." That is why every cave frame in the rough cut is a
# lamp-lit passage with nothing in it, and it is half of why TRAILER 11.1's
# pronoun has no referent -- the trailer's subject is absent from the entire
# second half of it.
#
# This is smaller than the pit-head's `fleet.gd` because a cave has no yard: it
# carries ONE machine, the hero, and nothing else. Everything else about it is
# the same file in the same shared layer, which is the point.
#
# TWO THINGS THE CAVE NEEDS THAT THE SURFACE DOES NOT.
#
# 1. THE GROUND IS A RAYCAST, NOT A HEIGHTFIELD. The pit-head's floor is a
#    function of x and z that `Ground.height` can answer directly. A cave's is
#    a swept, noise-displaced shell with a roof over it, so the only honest
#    answer is a downward ray -- and it has to START just above the machine's
#    feet, because a ray dropped from the sky in a tunnel hits the back.
#
#    AND IT MUST NOT ASSUME THE CAVE IS A PLANE. DESIGN-PRINCIPLES 10 makes
#    vertical a first-class axis: glacial systems are shafts, moulins and
#    meltwater cutting downward, so `blindside-gen` will carry height as a
#    dimension rather than as dressing. Nothing here holds a global floor
#    level, a datum, or a single y for the machine. The probe is RELATIVE to
#    wherever the machine currently is and is cast over a window deep enough to
#    contain a stride on a steep floor; the body's attitude comes from the
#    plane fitted through the four feet, which is a local tangent plane and is
#    correct on a ramp; and `at` interpolates in three dimensions, so a shot
#    can walk a machine down a decline by naming two anchors at different
#    depths. The one thing that is still flat is the shot ANCHOR grammar --
#    {st, r, u, f} measures `u` up from the floor and `f` along a plan
#    polyline, and when the generator gains levels that grammar gains a level
#    selector. That is a change to the rig, not to this file.
#
# 2. THE MACHINE BRINGS ITS OWN LIGHT, AND THE CAMERA KEEPS ITS OWN. The cave
#    spike's key is a lamp on the CAMERA, 0.26 m to the side of the sensor: a
#    fiction that stands in for the machine that was not there, and the whole
#    photometric contract in CINEMA.md is measured against it. Turning it off
#    now would re-grade every frame in the spike. So both are on, and the
#    machine's own pool is what trailer 17 actually asks for -- "its own pool
#    of light moving over the floor". The cost is measured, not assumed: see
#    the lumcheck numbers in the report.
# ---------------------------------------------------------------------------
class_name CaveFleet
extends RefCounted

const MACHINE_LAYER: int = 2

var root: Node3D
var rig: CameraRig
var hero: Machine = null
var _t: float = 0.0
var _ref_y: float = 0.0
var build_ms: float = 0.0
var _space: PhysicsDirectSpaceState3D = null
## floor probes that found nothing in the window -- reported, never hidden
var misses: int = 0


func build(p_root: Node3D, p_rig: CameraRig) -> void:
	var t0: int = Time.get_ticks_usec()
	root = p_root
	rig = p_rig
	hero = Hero.spawn(root, {
		"chassis": Hero.SPEC["chassis"], "loadout": Hero.SPEC["loadout"],
		"skin": Hero.SPEC["skin"], "wear": Hero.SPEC["wear"],
		"damage": Hero.SPEC["damage"], "clip": "walk", "lamp": true,
	}, Callable(self, "ground_y"))
	hero.name = "HeroMachine"
	hero.visible = false
	_proxy(hero)
	build_ms = float(Time.get_ticks_usec() - t0) / 1000.0
	print("machine         : %s, %d tris, %d surfaces, %.0f ms  |  %s"
		% [Hero.model_of(Hero.SPEC), hero.tri_count, hero.draw_surfaces,
			build_ms, Hero.banner()])


## Downward ray from just above the machine, against the world only (mask 1),
## so it can never land on the machine's own hull proxy on layer 2.
func ground_y(x: float, z: float) -> float:
	if rig == null or rig.world3d == null:
		return 0.0
	# Fetched fresh every call, never cached: the space state handle is only
	# valid inside the physics step and Godot hands back null outside it. The
	# cave rig's own _ss() carries the same note for the same reason.
	_space = rig.world3d.direct_space_state
	if _space == null:
		return _ref_y
	# The window: 1.5 m above the machine's own level down to 6 m below it.
	# Above, because on a rising floor the foot in front is higher than the
	# hull; below, because on a decline or at the lip of a drop it is a long way
	# lower, and a short probe would silently return the fallback and flatten
	# the shot. 1.5 m of headroom is under the cave's 2.2 m narrow-class height,
	# so the probe cannot start inside the back.
	var top: float = _ref_y + 1.5
	var q := PhysicsRayQueryParameters3D.create(Vector3(x, top, z),
		Vector3(x, top - 7.5, z))
	q.collision_mask = 1
	var hit: Dictionary = _space.intersect_ray(q)
	if hit.is_empty():
		# No floor within the window. Do NOT invent one: hold the machine's own
		# level, which leaves that foot unsupported rather than teleporting the
		# body. When the cave gains real drops this is the case that means "the
		# machine is standing at the edge of one", and it should be visible in
		# the frame rather than smoothed away.
		misses += 1
		return _ref_y
	return float((hit["position"] as Vector3).y)


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
## Put the machine where the shot says, at `tsec` seconds into the shot.
## Anchors are the cave's own {st, r, u, f}, resolved by the rig that will
## photograph it -- never by a second copy of the same arithmetic.
func hero_pose(shot: Dictionary, tn: float, tsec: float) -> void:
	if hero == null:
		return
	var m: Dictionary = Hero.block(shot)
	if m.is_empty() or String(m.get("role", "")) != "hero":
		hero.visible = false
		return
	hero.visible = true
	hero.wear = float(m.get("wear", Hero.SPEC["wear"]))
	hero.damage = float(m.get("damage", Hero.SPEC["damage"]))
	hero.lamp_on = bool(m.get("lamp", true))
	hero.refresh()
	var clip: String = String(m.get("clip", "walk"))
	if hero.clip != clip:
		hero.set_clip(clip)
	hero.walking = false

	var at = m.get("at", null)
	var p: Vector3 = hero.global_position
	var travel: Vector3 = Vector3.ZERO
	if at is Dictionary and (at as Dictionary).has("from"):
		var a: Vector3 = rig.resolve(at["from"])
		var b: Vector3 = rig.resolve(at["to"])
		# linear, never eased: the feet are baked at one speed (NOTES 5)
		p = a.lerp(b, tn)
		travel = b - a
	elif at != null:
		p = rig.resolve(at)
	var yaw: float = hero.rotation.y
	var y = m.get("yaw", null)
	if y is String and String(y) == "path" and travel.length() > 0.01:
		# HEADING only, and deliberately ignoring travel.y. A machine walking
		# down a decline is not pitched by its path, it is pitched by the rock
		# under its feet, and that comes from the plane fit in Machine._terrain
		# after this. Baking the path's slope into the node here would fight it.
		yaw = atan2(-travel.z, travel.x)
	elif y != null:
		yaw = deg_to_rad(float(y))
	var hd = m.get("head", null)
	if hd is Array and (hd as Array).size() == 2:
		var h0: Array = hd
		if hd[0] is Array:
			var e: float = tn * tn * tn * (tn * (tn * 6.0 - 15.0) + 10.0)
			h0 = [lerpf(float(hd[0][0]), float(hd[1][0]), e),
				  lerpf(float(hd[0][1]), float(hd[1][1]), e)]
		hero.look_at_local(float(h0[0]), float(h0[1]))

	_ref_y = p.y
	hero.global_position = p
	hero.rotation = Vector3(0, yaw, 0)
	_t = tsec
	hero.t = _t
	hero.anim.seek(_t, true)
	hero._post_pose()
	hero.body_y = p.y
	hero._settled = false
	hero._terrain(1.0)
