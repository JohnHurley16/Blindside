# ---------------------------------------------------------------------------
# BLINDSIDE assayer spike -- the machine that stands at its foot, for scale.
#
# A PLACEHOLDER, and the trailer already says so: TRAILER 7 lists "machines are
# placeholder shapes" as a known gap and handles it by keeping them small in
# frame and backlit. It is here for two jobs and only two:
#
#   1. SCALE. Nothing communicates that the Assayer is 6.6 m tall like
#      something 0.57 m tall standing at its foot. ART-DIRECTION 5.1 states the
#      comparison as "the dog stands to the top of the footing hub", and that
#      is a check this build can either pass or fail on sight.
#   2. THE DOWNLOAD POSE. THE-MACHINERY 6: "it walks up, stops, and puts its
#      transducer on the rock -- sensor head down, hard against the floor, and
#      holds still." Concept proposal 15 makes that a play-bow, with the lamp
#      OFF, because a listening machine with its lamp on is lighting nothing it
#      needs. A box cannot do that pose, which is the only reason this is more
#      than a box.
#
# The dimensions are the ones the concept board used: 0.77 m long, 0.57 m
# standing. Everything else about its form is a guess and none of it should be
# read as a proposal for the real chassis.
#
# ART-DIRECTION 2.1 and 2.5: the work lamp is WHITE for every team, a 50 degree
# cone tilted 8-10 degrees down. The running lights are BONE at strength 3 and
# they light nothing past 1.5 m. Nothing on it is cyan and nothing is red.
# ---------------------------------------------------------------------------
class_name Surveyor
extends Node3D

const LEN: float = 0.770
const STAND: float = 0.570

var mats: AssayerMaterials
var lamp: SpotLight3D
var body: Node3D
var head: Node3D
var legs: Array = []          # [Node3D upper, Node3D lower] x 4
var stat_tris: int = 0


func build(m: AssayerMaterials) -> void:
	mats = m
	var C := AssayerMaterials.C_SHELL
	var CD := Color(0.075, 0.078, 0.080)     # graphite, the under-chassis

	body = Node3D.new()
	add_child(body)
	var mb := MeshKit.MB.new()
	# the hull: a pale shell over a graphite frame. ART-DIRECTION 4.3 -- the
	# BROUGHT register is clean-edged and three times the albedo of the iron
	# beside it, which is the whole point of putting the two in one frame.
	mb.add_prim(mats.iron, MeshKit.box(0.480, 0.150, 0.215),
		Transform3D(Basis.IDENTITY, Vector3(0, 0, 0)), C)
	mb.add_prim(mats.iron, MeshKit.box(0.500, 0.075, 0.185),
		Transform3D(Basis.IDENTITY, Vector3(0, -0.085, 0)), CD)
	mb.add_prim(mats.iron, MeshKit.box(0.190, 0.110, 0.170),
		Transform3D(Basis.IDENTITY, Vector3(0.290, 0.012, 0)), C)
	# the cargo bay, empty
	mb.add_prim(mats.iron, MeshKit.box(0.230, 0.090, 0.150),
		Transform3D(Basis.IDENTITY, Vector3(-0.150, 0.100, 0)), CD)
	var bmi := MeshInstance3D.new()
	bmi.mesh = mb.commit()
	body.add_child(bmi)
	stat_tris += mb.tri_count()

	# the sensor head: the one mark that says "alive and still looking"
	head = Node3D.new()
	head.position = Vector3(0.390, 0.020, 0)
	body.add_child(head)
	var hb := MeshKit.MB.new()
	hb.add_prim(mats.iron, MeshKit.cyl(0.062, 0.115, 12),
		Transform3D(Basis.from_euler(Vector3(0, 0, PI * 0.5)), Vector3(0.02, 0, 0)), CD)
	hb.add_prim(mats.iron, MeshKit.box(0.030, 0.090, 0.130),
		Transform3D(Basis.IDENTITY, Vector3(0.082, 0, 0)), C)
	# the transducer face -- the thing it puts on the rock
	hb.add_prim(mats.steel, MeshKit.cyl(0.044, 0.016, 12),
		Transform3D(Basis.from_euler(Vector3(0, 0, PI * 0.5)), Vector3(0.100, 0, 0)),
		AssayerMaterials.C_STEEL)
	var hmi := MeshInstance3D.new()
	hmi.mesh = hb.commit()
	head.add_child(hmi)
	stat_tris += hb.tri_count()

	# the running lights: BONE, strength 3, lighting nothing past 1.5 m
	for zs in [-0.105, 0.105]:
		var pm := MeshKit.MB.new()
		pm.add_prim(mats.pilot, MeshKit.box(0.150, 0.014, 0.008),
			Transform3D(Basis.IDENTITY, Vector3(0.02, 0.058, zs)), Color(1, 1, 1))
		var pmi := MeshInstance3D.new()
		pmi.mesh = pm.commit()
		body.add_child(pmi)
		stat_tris += pm.tri_count()

	# the legs
	for i in range(4):
		var fx: float = 0.185 if i < 2 else -0.185
		var fz: float = 0.128 if (i % 2) == 0 else -0.128
		var up := Node3D.new()
		up.position = Vector3(fx, -0.055, fz)
		body.add_child(up)
		var ub := MeshKit.MB.new()
		ub.add_prim(mats.iron, MeshKit.box(0.048, 0.190, 0.040),
			Transform3D(Basis.IDENTITY, Vector3(0, -0.095, 0)), CD)
		var umi := MeshInstance3D.new()
		umi.mesh = ub.commit()
		up.add_child(umi)
		var lo := Node3D.new()
		lo.position = Vector3(0, -0.190, 0)
		up.add_child(lo)
		var lb := MeshKit.MB.new()
		lb.add_prim(mats.iron, MeshKit.box(0.036, 0.215, 0.032),
			Transform3D(Basis.IDENTITY, Vector3(0, -0.108, 0)), CD)
		lb.add_prim(mats.iron, MeshKit.sph(0.030, 8),
			Transform3D(Basis.IDENTITY, Vector3(0, -0.215, 0)), CD)
		var lmi := MeshInstance3D.new()
		lmi.mesh = lb.commit()
		lo.add_child(lmi)
		stat_tris += ub.tri_count() + lb.tri_count()
		legs.append([up, lo])

	lamp = SpotLight3D.new()
	lamp.light_color = Color(1.00, 0.98, 0.95)      # white for every team
	lamp.light_energy = 5.4                          # the cave spike's, re-derived there
	lamp.spot_range = 26.0
	lamp.spot_angle = 25.0
	lamp.spot_angle_attenuation = 0.40
	lamp.spot_attenuation = 2.0
	lamp.shadow_enabled = true
	lamp.shadow_bias = 0.020
	lamp.shadow_normal_bias = 1.10
	lamp.position = Vector3(0.44, 0.055, 0)
	# ART-DIRECTION 2.1: tilted 9 degrees down so the pool lands in frame
	lamp.rotation_degrees = Vector3(-9.0, -90.0, 0)
	body.add_child(lamp)

	stand()


# the standing pose, and the height that has to be 0.57 m
func stand() -> void:
	position.y = STAND - 0.135
	body.rotation = Vector3.ZERO
	body.position = Vector3.ZERO
	head.rotation = Vector3.ZERO
	for i in range(4):
		var up: Node3D = legs[i][0]
		var lo: Node3D = legs[i][1]
		up.rotation = Vector3(0, 0, deg_to_rad(-14.0 if i < 2 else 14.0))
		lo.rotation = Vector3(0, 0, deg_to_rad(24.0 if i < 2 else -24.0))
	lamp.visible = true
	lamp.light_energy = 5.4


# THE DOWNLOAD POSE. "sensor head down, hard against the floor, and holds
# still" (THE-MACHINERY 6), as a play-bow (concept proposal 15): body dropped
# and pitched nose-down, front legs folded, the head folded to the rock, the
# lamp OFF. In the game the head also STOPS TURNING, which is what reads as
# "doing something deliberate, and not watching".
func download() -> void:
	# The sign matters and the first build had it backwards: the body's long
	# axis is +X and a POSITIVE rotation about Z lifts the nose. A play-bow
	# drops it. With the body at -26 deg and the head folded another -22, the
	# transducer face lands 0.27 m below the node, which is where the node then
	# stands so that the face is ON the rock rather than above it.
	position.y = 0.272
	body.rotation = Vector3(0, 0, deg_to_rad(-26.0))
	body.position = Vector3(0, -0.030, 0)
	head.rotation = Vector3(0, 0, deg_to_rad(-22.0))
	for i in range(4):
		var up: Node3D = legs[i][0]
		var lo: Node3D = legs[i][1]
		if i < 2:
			# the front pair folded right under: elbows out, feet back
			up.rotation = Vector3(0, 0, deg_to_rad(-88.0))
			lo.rotation = Vector3(0, 0, deg_to_rad(126.0))
		else:
			# the back pair still standing, which is what makes it a BOW
			up.rotation = Vector3(0, 0, deg_to_rad(24.0))
			lo.rotation = Vector3(0, 0, deg_to_rad(-6.0))
	lamp.visible = false
