extends RefCounted
class_name Props
##
## DRESSING LAYER - THE BROUGHT. The players' technology, which lives up here.
##
## DESIGN-PRINCIPLES 4: "if the world contains autonomous walkers, something in
## the world has to have built and serviced them. That evidence is the surface's
## job and it must be visible." Everything in this file is that evidence: the
## bay, the bench, the handling gear, the power, the antennas, the cases, and
## the machines themselves standing in the yard.
##
## The register is deliberate: chamfered edges, pale and grey and galvanised,
## labelled panels, small warm pilots at strength <= 3, and every piece of it
## small enough to be dwarfed by the iron it is bolted to.

var L: SurfaceLayout
var B: Batcher
var r: RandomNumberGenerator
var lights: Array = []      # [pos, colour, energy, range] for the dusk preset

func _init(p_L: SurfaceLayout, p_B: Batcher) -> void:
	L = p_L
	B = p_B
	r = RandomNumberGenerator.new()
	r.seed = L.seed_v * 104729 + 7

func gh(x: float, z: float) -> float:
	return float(L.ground_mm(int(x * 1000.0), int(z * 1000.0))) / 1000.0

func kcol(lo: float = 0.84, hi: float = 1.08) -> Color:
	var v := r.randf_range(lo, hi)
	return Color(v, v, v * r.randf_range(0.97, 1.03))

func ircol(lo: float = 0.55, hi: float = 2.0) -> Color:
	var v := r.randf_range(lo, hi)
	return Color(v * 1.02, v * 0.95, v * 0.88)

func build() -> void:
	_service_bay()
	_gantry()
	_charge_row()
	_containers()
	_tanks()
	_transformer()
	_comms_mast()
	_zone_clutter()
	_yard_fill()
	_machines()
	_signage()

# =============================================================== yard fill
## RULE, and this is the one that carries "walking distance". The pad is swept on
## a 3.1 m lattice. Each cell that is not inside a building, a stocked zone, the
## collar apron or the road centreline rolls once against a table of twenty-two
## cluster generators, weighted so that the yard is 55% occupied. A cluster is
## 4-30 instances. Nothing here is placed by hand and nothing here is layout: you
## could delete this function and every machine would still walk the same route.
const YARD_KINDS := ["bottles", "stillage", "toolchest", "barrow", "cones", "barrier",
	"bin", "hosereel", "planks", "tyres", "cans", "ladder", "tarp", "genset",
	"crates", "sandbags", "jersey", "plate", "duckboard", "tripod", "welding", "spool"]

func _yard_fill() -> void:
	var p: Dictionary = L.plan["pads"][0]
	var x0 := float(p["x0"]) / 1000.0 + 1.6
	var z0 := float(p["z0"]) / 1000.0 + 1.6
	var x1 := float(p["x1"]) / 1000.0 - 1.6
	var z1 := float(p["z1"]) / 1000.0 - 1.6
	var y := L.pad_h() / 1000.0
	var step := 2.35
	var x := x0
	while x < x1:
		var z := z0
		while z < z1:
			var cx := x + r.randf_range(-0.9, 0.9)
			var cz := z + r.randf_range(-0.9, 0.9)
			z += step
			if _blocked(cx, cz):
				continue
			if r.randf() > 0.78:
				continue
			var kind: String = YARD_KINDS[r.randi() % YARD_KINDS.size()]
			_cluster(kind, Vector3(cx, y, cz), r.randf() * TAU)
		x += step
	_yard_fill_open()

## RULE. The unpaved strip between the pad edge and the fence is where things go
## that nobody wants on the concrete: spoil, scrap, drums, tips of stock, the
## overflow. Sparser (0.40) and biased to the heavy end of the table.
func _yard_fill_open() -> void:
	var f: Array = L.plan["fence"]
	var fx0 := float(f[0][0]) / 1000.0 + 2.0
	var fz0 := float(f[0][1]) / 1000.0 + 2.0
	var fx1 := float(f[1][0]) / 1000.0 - 2.0
	var fz1 := float(f[2][1]) / 1000.0 - 2.0
	var heavy := ["planks", "tyres", "bin", "jersey", "crates", "spool", "cones",
		"stillage", "tarp", "sandbags", "barrier", "cans"]
	var x := fx0
	while x < fx1:
		var z := fz0
		while z < fz1:
			var cx := x + r.randf_range(-1.0, 1.0)
			var cz := z + r.randf_range(-1.0, 1.0)
			z += 3.4
			if L.on_pad(int(cx * 1000.0), int(cz * 1000.0)):
				continue
			if cx > 29.0:
				continue      # the course flat stays clear: it is a test, not a store
			if _blocked(cx, cz):
				continue
			if r.randf() > 0.40:
				continue
			_cluster(heavy[r.randi() % heavy.size()], Vector3(cx, gh(cx, cz), cz), r.randf() * TAU)
		x += 3.4

## every rectangle a cluster may not land in. LAYOUT owns all of these; dressing
## only asks.
func _blocked(x: float, z: float) -> bool:
	if Vector2(x, z).length() < 8.5:
		return true                               # the collar apron
	if absf(z - 1.0) < 4.2 and x < -30.0:
		return true                               # the gate approach
	for b in L.plan["buildings"]:
		if x > float(b["x0"]) / 1000.0 - 1.4 and x < float(b["x1"]) / 1000.0 + 1.4 \
				and z > float(b["z0"]) / 1000.0 - 1.4 and z < float(b["z1"]) / 1000.0 + 1.4:
			return true
	for zz in L.plan["zones"]:
		if x > float(zz["x0"]) / 1000.0 - 1.0 and x < float(zz["x1"]) / 1000.0 + 1.0 \
				and z > float(zz["z0"]) / 1000.0 - 1.0 and z < float(zz["z1"]) / 1000.0 + 1.0:
			return true
	for c in L.plan["columns"]:
		if Vector2(x - float(c["x"]) / 1000.0, z - float(c["z"]) / 1000.0).length() < 1.6:
			return true
	# circulation stays clear. A yard with no route through it is a scrapyard.
	var hw := float(L.plan["walkway_w"]) / 2000.0
	var p2 := Vector2(x, z)
	for w in L.plan["walkways"]:
		var a := Vector2(float(w[0][0]) / 1000.0, float(w[0][1]) / 1000.0)
		var b := Vector2(float(w[1][0]) / 1000.0, float(w[1][1]) / 1000.0)
		var ab := b - a
		var t := clampf((p2 - a).dot(ab) / maxf(ab.length_squared(), 0.001), 0.0, 1.0)
		if (a + ab * t).distance_to(p2) < hw:
			return true
	return false

func _cluster(kind: String, o: Vector3, yaw: float) -> void:
	var fw := Vector3(cos(yaw), 0, sin(yaw))
	var sd := Vector3(-sin(yaw), 0, cos(yaw))
	match kind:
		"bottles":
			# a gas bottle rack: eight cylinders in a galvanised cage
			B.prop("box", "galv", Batcher.xf(o + Vector3(0, 0.05, 0), Vector3(1.6, 0.10, 0.8), yaw), kcol())
			for k in 8:
				var pp := o + fw * (-0.65 + 0.19 * float(k)) + sd * r.randf_range(-0.15, 0.15) + Vector3(0, 0.72, 0)
				B.prop("cyl", "ember" if k % 3 == 0 else "kitgrey", Batcher.xf(pp, Vector3(0.23, 1.35, 0.23), yaw), kcol(0.5, 0.9))
				B.detail("cyl", "alu", Batcher.xf(pp + Vector3(0, 0.75, 0), Vector3(0.09, 0.16, 0.09), yaw), kcol())
			for s in [-1.0, 1.0]:
				B.prop("angle", "galv", Batcher.xf(o + fw * 0.85 * s + Vector3(0, 0.7, 0), Vector3(0.06, 1.4, 0.06), yaw), kcol())
			B.prop("box", "galv", Batcher.xf(o + Vector3(0, 1.35, 0) + sd * 0.36, Vector3(1.7, 0.05, 0.05), yaw), kcol())
		"stillage":
			# mesh cage pallets, stacked
			for st in r.randi_range(1, 3):
				var by := o.y + 0.42 + 0.86 * float(st - 1)
				B.prop("pallet", "timber", Batcher.xf(o + Vector3(0, by - 0.36, 0), Vector3(1.2, 0.16, 1.0), yaw), kcol(0.6, 1.0))
				for e in [[-0.58, 0.0], [0.58, 0.0], [0.0, -0.48], [0.0, 0.48]]:
					B.prop("box", "galv", Batcher.xf(o + fw * e[0] + sd * e[1] + Vector3(0, by, 0),
						Vector3(0.04 if absf(e[0]) > 0.1 else 1.16, 0.72, 0.96 if absf(e[0]) > 0.1 else 0.04), yaw), kcol(0.6, 1.0))
					for w in 6:
						B.detail("cyl6", "galv", Batcher.xf(o + fw * e[0] + sd * e[1] + Vector3(0, by, 0)
							+ (sd if absf(e[0]) > 0.1 else fw) * (-0.45 + 0.18 * float(w)),
							Vector3(0.022, 0.7, 0.022), yaw), kcol(0.6, 1.0))
				for it in r.randi_range(1, 4):
					B.detail("casebox", "iron", Batcher.xf(o + Vector3(r.randf_range(-0.4, 0.4), by - 0.12, r.randf_range(-0.3, 0.3)),
						Vector3(0.3, 0.28, 0.3), r.randf() * TAU), ircol())
		"toolchest":
			B.prop("casebox", "ember", Batcher.xf(o + Vector3(0, 0.52, 0), Vector3(1.05, 1.0, 0.62), yaw), kcol(0.55, 0.85))
			for k in 5:
				B.detail("box", "kitgrey", Batcher.xf(o + Vector3(0, 0.20 + 0.16 * float(k), 0) + sd * 0.32,
					Vector3(0.95, 0.03, 0.02), yaw), kcol())
				B.detail("cyl", "alu", Batcher.xf(o + Vector3(0, 0.20 + 0.16 * float(k), 0) + sd * 0.34,
					Vector3(0.24, 0.03, 0.03), yaw, 0.0, PI * 0.5), kcol())
			for w2 in [-0.42, 0.42]:
				B.detail("cyl", "rubber", Batcher.xf(o + fw * w2 + sd * 0.24 + Vector3(0, 0.07, 0), Vector3(0.14, 0.06, 0.14), yaw, 0.0, PI * 0.5), Color(1, 1, 1))
		"barrow":
			B.prop("box", "ember", Batcher.xf(o + Vector3(0, 0.42, 0), Vector3(0.9, 0.3, 0.62), yaw, 0.18), kcol(0.55, 0.85))
			B.detail("cyl", "rubber", Batcher.xf(o + fw * 0.62 + Vector3(0, 0.18, 0), Vector3(0.36, 0.10, 0.36), yaw, 0.0, PI * 0.5), Color(1, 1, 1))
			for s2 in [-1.0, 1.0]:
				B.detail("cyl", "galv", Batcher.beam_xf(o + fw * 0.5 + sd * s2 * 0.25 + Vector3(0, 0.3, 0),
					o - fw * 0.7 + sd * s2 * 0.3 + Vector3(0, 0.62, 0), 0.035, 0.035), kcol())
				B.detail("cyl", "galv", Batcher.xf(o - fw * 0.1 + sd * s2 * 0.27 + Vector3(0, 0.16, 0), Vector3(0.04, 0.32, 0.04), yaw), kcol())
		"cones":
			for k in r.randi_range(3, 7):
				var pc := o + Vector3(r.randf_range(-1.2, 1.2), 0.28, r.randf_range(-1.2, 1.2))
				var lean := r.randf() < 0.2
				B.prop("cone", "ember", Batcher.xf(pc, Vector3(0.36, 0.56, 0.36), r.randf() * TAU,
					r.randf_range(-1.4, 1.4) if lean else 0.0), kcol(0.6, 1.0))
				B.detail("box", "ember", Batcher.xf(pc - Vector3(0, 0.26, 0), Vector3(0.42, 0.03, 0.42), r.randf() * TAU), kcol(0.6, 1.0))
				B.detail("ring", "bone", Batcher.xf(pc + Vector3(0, 0.06, 0), Vector3(0.24, 0.07, 0.24)), kcol())
		"barrier":
			for k in r.randi_range(2, 4):
				var pb := o + fw * (1.15 * float(k)) + sd * r.randf_range(-0.1, 0.1)
				B.prop("casebox", "ember", Batcher.xf(pb + Vector3(0, 0.5, 0), Vector3(1.1, 1.0, 0.42), yaw + r.randf_range(-0.1, 0.1)), kcol(0.6, 1.0))
				B.detail("box", "bone", Batcher.xf(pb + Vector3(0, 0.62, 0) + sd * 0.22, Vector3(0.9, 0.16, 0.02), yaw), kcol())
		"bin":
			B.prop("casebox", "iron", Batcher.xf(o + Vector3(0, 0.62, 0), Vector3(1.7, 1.2, 1.2), yaw), ircol(0.5, 1.3))
			for k in r.randi_range(3, 8):
				B.detail(["box", "chip", "angle"][r.randi() % 3], ["timber", "iron", "litter"][r.randi() % 3],
					Batcher.xf(o + Vector3(r.randf_range(-0.6, 0.6), 1.24, r.randf_range(-0.4, 0.4)),
						Vector3(r.randf_range(0.1, 0.4), r.randf_range(0.08, 0.5), r.randf_range(0.1, 0.4)),
						r.randf() * TAU, r.randf_range(-1.0, 1.0), r.randf_range(-1.0, 1.0)), ircol())
		"hosereel":
			B.prop("wheel", "ember", Batcher.xf(o + Vector3(0, 0.62, 0), Vector3(1.05, 1.05, 0.5), yaw, 0.0, PI * 0.5), kcol(0.6, 0.9))
			B.prop("cyl", "rubber", Batcher.xf(o + Vector3(0, 0.62, 0), Vector3(0.78, 0.42, 0.78), yaw, 0.0, PI * 0.5), Color(0.7, 0.7, 0.7))
			B.prop("angle", "ember", Batcher.xf(o + Vector3(0, 0.3, 0), Vector3(0.1, 0.6, 0.1), yaw), kcol(0.6, 0.9))
			var prev := o + fw * 0.55 + Vector3(0, 0.5, 0)
			for k in 5:
				var q := prev + fw * r.randf_range(0.4, 0.9) + sd * r.randf_range(-0.7, 0.7)
				q.y = o.y + 0.04
				B.detail("cyl6", "rubber", Batcher.beam_xf(prev, q, 0.028, 0.028), Color(0.8, 0.8, 0.8))
				prev = q
		"planks":
			for k in r.randi_range(4, 11):
				B.prop("box", "timber", Batcher.xf(o + Vector3(0, 0.06 + 0.055 * float(k), 0)
					+ sd * r.randf_range(-0.12, 0.12), Vector3(0.24, 0.05, r.randf_range(2.0, 3.4)),
					yaw + r.randf_range(-0.04, 0.04)), kcol(0.55, 1.1))
			B.detail("box", "timber", Batcher.xf(o + Vector3(0, 0.03, 0), Vector3(1.2, 0.06, 0.12), yaw), kcol(0.5, 1.0))
		"tyres":
			for k in r.randi_range(3, 7):
				B.prop("ring", "rubber", Batcher.xf(o + Vector3(r.randf_range(-0.1, 0.1), 0.10 + 0.19 * float(k), r.randf_range(-0.1, 0.1)),
					Vector3(0.98, 0.2, 0.98), r.randf() * TAU), Color(1, 1, 1))
		"cans":
			for k in r.randi_range(3, 9):
				B.detail("casebox", ["amber", "kitgrey", "ember"][r.randi() % 3],
					Batcher.xf(o + Vector3(r.randf_range(-0.7, 0.7), 0.18, r.randf_range(-0.7, 0.7)),
						Vector3(0.16, 0.36, 0.30), r.randf() * TAU), kcol(0.6, 1.0))
		"ladder":
			B.prop("ladder", "alu", Batcher.xf(o + Vector3(0, 0.32, 0), Vector3(0.5, 4.2, 0.09), yaw, 0.0, PI * 0.5 - 0.06), kcol())
		"tarp":
			var w3 := r.randf_range(1.6, 2.8)
			for k in r.randi_range(2, 5):
				B.prop("box", ["timber", "iron", "kitgrey"][r.randi() % 3],
					Batcher.xf(o + Vector3(r.randf_range(-0.3, 0.3), 0.2 + 0.28 * float(k), r.randf_range(-0.3, 0.3)),
						Vector3(w3 * 0.7, 0.26, w3 * 0.5), yaw + r.randf_range(-0.2, 0.2)), kcol(0.5, 1.0))
			B.prop("box", "plastic", Batcher.xf(o + Vector3(0, 0.28 * 3.0, 0), Vector3(w3, 0.04, w3 * 0.72), yaw, r.randf_range(-0.08, 0.08), r.randf_range(-0.08, 0.08)), Color(0.55, 0.55, 0.5))
			for k2 in 4:
				B.detail("cyl6", "rubber", Batcher.beam_xf(o + fw * (w3 * 0.5) * (1.0 if k2 % 2 == 0 else -1.0) + sd * (w3 * 0.36) * (1.0 if k2 < 2 else -1.0) + Vector3(0, 0.28 * 3.0, 0),
					o + fw * (w3 * 0.6) * (1.0 if k2 % 2 == 0 else -1.0) + sd * (w3 * 0.46) * (1.0 if k2 < 2 else -1.0) + Vector3(0, 0.02, 0), 0.012, 0.012), Color(1, 1, 1))
		"genset":
			B.prop("casebox", "amber", Batcher.xf(o + Vector3(0, 0.66, 0), Vector3(2.3, 1.3, 1.1), yaw), kcol(0.6, 0.95))
			B.prop("cyl", "iron", Batcher.xf(o + fw * 0.9 + Vector3(0, 1.6, 0), Vector3(0.14, 0.9, 0.14), yaw), ircol())
			for k in 10:
				B.detail("box", "kitgrey", Batcher.xf(o - fw * 1.16 + Vector3(0, 0.4 + 0.08 * float(k), 0), Vector3(0.03, 0.05, 0.9), yaw), kcol())
			B.detail("box", "bone", Batcher.xf(o + sd * 0.56 + Vector3(0, 0.9, 0), Vector3(0.5, 0.3, 0.02), yaw), kcol())
			var pe := o + fw * -1.2 + Vector3(0, 0.3, 0)
			for k3 in 4:
				var q2 := pe + Vector3(r.randf_range(-0.8, -0.2), -0.07 * float(k3), r.randf_range(-0.8, 0.8))
				B.detail("cyl6", "rubber", Batcher.beam_xf(pe, q2, 0.03, 0.03), Color(0.9, 0.9, 0.9))
				pe = q2
		"crates":
			for k in r.randi_range(2, 6):
				var s3 := r.randf_range(0.5, 1.0)
				B.prop("casebox", "bone" if r.randf() < 0.45 else "timber",
					Batcher.xf(o + Vector3(r.randf_range(-0.7, 0.7), s3 * 0.5 + r.randf_range(0.0, 0.6), r.randf_range(-0.7, 0.7)),
						Vector3(s3 * 1.5, s3, s3 * 1.1), r.randf() * TAU), kcol(0.6, 1.05))
		"sandbags":
			for k in r.randi_range(8, 18):
				var row := k / 6
				B.detail("rock", "litter", Batcher.xf(o + fw * (-0.7 + 0.24 * float(k % 6)) + sd * r.randf_range(-0.1, 0.1)
					+ Vector3(0, 0.11 + 0.17 * float(row), 0), Vector3(0.42, 0.22, 0.32), yaw + r.randf_range(-0.2, 0.2)), Color(0.55, 0.5, 0.42))
		"jersey":
			for k in r.randi_range(1, 3):
				B.prop("box", "stone", Batcher.xf(o + fw * (1.65 * float(k)) + Vector3(0, 0.42, 0), Vector3(1.6, 0.84, 0.5), yaw + r.randf_range(-0.05, 0.05)), kcol(0.7, 1.05))
				B.detail("box", "amber", Batcher.xf(o + fw * (1.65 * float(k)) + sd * 0.26 + Vector3(0, 0.62, 0), Vector3(1.2, 0.14, 0.02), yaw), Color(0.85, 0.85, 0.85))
		"plate":
			B.prop("box", "steel", Batcher.xf(o + Vector3(0, 0.03, 0), Vector3(2.4, 0.05, 1.4), yaw), kcol(0.35, 0.6))
			for k in 4:
				B.detail("hex", "steel", Batcher.xf(o + fw * (-1.0 + 0.66 * float(k)) + Vector3(0, 0.06, 0), Vector3(0.09, 0.03, 0.09), yaw), kcol(0.4, 0.7))
		"duckboard":
			for k in 7:
				B.detail("box", "timber", Batcher.xf(o + fw * (-0.6 + 0.2 * float(k)) + Vector3(0, 0.05, 0), Vector3(0.16, 0.05, 1.1), yaw), kcol(0.55, 1.0))
			B.detail("box", "timber", Batcher.xf(o + Vector3(0, 0.02, 0), Vector3(1.5, 0.04, 0.1), yaw), kcol(0.5, 0.9))
		"tripod":
			for k in 3:
				var a := yaw + TAU * float(k) / 3.0
				B.prop("cyl", "alu", Batcher.beam_xf(o + Vector3(cos(a) * 0.55, 0.0, sin(a) * 0.55), o + Vector3(0, 1.35, 0), 0.035, 0.035), kcol())
			B.prop("casebox", "bone", Batcher.xf(o + Vector3(0, 1.48, 0), Vector3(0.30, 0.22, 0.22), yaw), kcol())
			B.detail("box", "screen", Batcher.xf(o + fw * 0.12 + Vector3(0, 1.48, 0), Vector3(0.02, 0.16, 0.20), yaw), Color(1, 1, 1))
		"welding":
			B.prop("casebox", "kitgrey", Batcher.xf(o + Vector3(0, 0.42, 0), Vector3(0.8, 0.84, 0.6), yaw), kcol(0.55, 0.85))
			for k in 2:
				B.prop("cyl", ["ember", "kitgrey"][k], Batcher.xf(o + sd * (0.5 + 0.28 * float(k)) + Vector3(0, 0.72, 0), Vector3(0.24, 1.4, 0.24), yaw), kcol(0.55, 0.9))
			var pw := o + fw * 0.4 + Vector3(0, 0.5, 0)
			for k4 in 5:
				var q3 := pw + Vector3(r.randf_range(-0.6, 0.9), -0.1 * float(k4), r.randf_range(-0.9, 0.9))
				q3.y = maxf(q3.y, o.y + 0.03)
				B.detail("cyl6", "rubber", Batcher.beam_xf(pw, q3, 0.022, 0.022), Color(0.6, 0.6, 0.6))
				pw = q3
		"spool":
			var rr := r.randf_range(0.7, 1.35)
			B.prop("wheel", "timber", Batcher.xf(o + Vector3(0, rr, 0), Vector3(rr * 2.0, rr * 2.0, rr * 1.1), yaw, 0.0, PI * 0.5), kcol(0.55, 1.0))
			B.prop("cyl", "rubber", Batcher.xf(o + Vector3(0, rr, 0), Vector3(rr * 1.45, rr * 0.95, rr * 1.45), yaw, 0.0, PI * 0.5), Color(0.75, 0.75, 0.75))
			B.detail("box", "bone", Batcher.xf(o + sd * (rr * 0.58) + Vector3(0, rr, 0), Vector3(0.34, 0.24, 0.02), yaw), kcol())

# ============================================================== service bay
## RULE. A light steel portal frame on a cast pad: four portals at 3.5 m, a
## shallow roof, one open side facing the collar so the bay is legible from the
## yard, and a back wall of cladding. Inside, on a 1.2 m module: bench, tool
## board, parts rack, case stack, cable reels, a terminal, a service cradle.
func _service_bay() -> void:
	var bdg := _building("service_bay")
	if bdg.is_empty():
		return
	var x0 := float(bdg["x0"]) / 1000.0
	var z0 := float(bdg["z0"]) / 1000.0
	var x1 := float(bdg["x1"]) / 1000.0
	var z1 := float(bdg["z1"]) / 1000.0
	var h := float(bdg["h"]) / 1000.0
	var y := L.pad_h() / 1000.0
	var portals := int((x1 - x0) / 3.5) + 1
	for i in portals:
		var x := x0 + (x1 - x0) * float(i) / float(portals - 1)
		B.add("ibeam", "kitgrey", Batcher.xf(Vector3(x, y + h * 0.5, z0), Vector3(0.22, h, 0.22)), kcol())
		B.add("ibeam", "kitgrey", Batcher.xf(Vector3(x, y + h * 0.5, z1), Vector3(0.22, h, 0.22)), kcol())
		B.beam("ibeam", "kitgrey", Vector3(x, y + h, z0), Vector3(x, y + h + 0.55, (z0 + z1) * 0.5), 0.20, 0.20, kcol())
		B.beam("ibeam", "kitgrey", Vector3(x, y + h, z1), Vector3(x, y + h + 0.55, (z0 + z1) * 0.5), 0.20, 0.20, kcol())
		# base plates and holding-down bolts
		for zz in [z0, z1]:
			B.prop("box", "alu", Batcher.xf(Vector3(x, y + 0.02, zz), Vector3(0.5, 0.04, 0.5)), kcol())
			for k in 4:
				var a := TAU * float(k) / 4.0 + 0.78
				B.detail("hex", "alu", Batcher.xf(Vector3(x + cos(a) * 0.17, y + 0.06, zz + sin(a) * 0.17), Vector3(0.05, 0.05, 0.05)), kcol())
	# purlins and roof sheets
	for k in 9:
		var t := float(k) / 8.0
		var zz := z0 + (z1 - z0) * t
		var yy := y + h + 0.55 * (1.0 - absf(t - 0.5) * 2.0)
		B.beam("channel", "kitgrey", Vector3(x0, yy + 0.12, zz), Vector3(x1, yy + 0.12, zz), 0.10, 0.14, kcol())
	for i in int((x1 - x0) / 1.0):
		var x2 := x0 + 1.0 * (float(i) + 0.5)
		for side in [-1.0, 1.0]:
			var zc: float = (z0 + z1) * 0.5 + side * (z1 - z0) * 0.25
			B.add("box", "alu", Batcher.xf(Vector3(x2, y + h + 0.55 - absf(side) * 0.14, zc),
				Vector3(0.98, 0.035, (z1 - z0) * 0.53), 0.0, atan2(0.55, (z1 - z0) * 0.5) * side, 0.0), kcol(0.75, 1.0))
	# back cladding (north), on the z0 side
	for i in int((x1 - x0) / 0.9):
		var x3 := x0 + 0.9 * (float(i) + 0.5)
		B.add("box", "alu", Batcher.xf(Vector3(x3, y + h * 0.5 + 0.2, z0 - 0.12), Vector3(0.88, h - 0.3, 0.04)), kcol(0.78, 1.02))
		for cg in 5:
			B.detail("cyl6", "alu", Batcher.xf(Vector3(x3 - 0.34 + 0.17 * float(cg), y + h * 0.5 + 0.2, z0 - 0.15),
				Vector3(0.045, h - 0.3, 0.045)), kcol(0.78, 1.02))
	# --- the bench: 4.8 m of it, on the back wall, with the modules laid out
	var bx := (x0 + x1) * 0.5 - 1.4
	var bz := z0 + 0.85
	B.prop("box", "alu", Batcher.xf(Vector3(bx, y + 0.90, bz), Vector3(4.8, 0.07, 0.85)), kcol())
	for k in 5:
		var lx := bx - 2.2 + 1.1 * float(k)
		B.prop("box", "kitgrey", Batcher.xf(Vector3(lx, y + 0.45, bz - 0.3), Vector3(0.07, 0.9, 0.07)), kcol())
		B.prop("box", "kitgrey", Batcher.xf(Vector3(lx, y + 0.45, bz + 0.3), Vector3(0.07, 0.9, 0.07)), kcol())
	# under-bench drawers and bins
	for k in 4:
		B.prop("casebox", "kitgrey", Batcher.xf(Vector3(bx - 2.0 + 1.15 * float(k), y + 0.40, bz), Vector3(0.85, 0.72, 0.62)), kcol())
	# the seven modules, as parts on the bench (vision board A3 / 11_yard_modules)
	var mods := [Vector3(0.34, 0.09, 0.11), Vector3(0.16, 0.16, 0.16), Vector3(0.44, 0.06, 0.06),
		Vector3(0.22, 0.20, 0.14), Vector3(0.62, 0.05, 0.05), Vector3(0.30, 0.14, 0.24), Vector3(0.19, 0.13, 0.13)]
	for k in mods.size():
		var p := Vector3(bx - 2.1 + 0.62 * float(k), y + 0.94 + mods[k].y * 0.5, bz + r.randf_range(-0.2, 0.2))
		B.prop("casebox", "bone" if k % 3 != 1 else "kitgrey", Batcher.xf(p, mods[k], r.randf_range(-0.4, 0.4)), kcol())
		B.detail("box", "amber", Batcher.xf(p + Vector3(0, mods[k].y * 0.52, 0), Vector3(mods[k].x * 0.5, 0.004, 0.02)), Color(1, 1, 1))
	# hand tools scattered on the bench
	for k in 14:
		var p2 := Vector3(bx + r.randf_range(-2.3, 2.3), y + 0.96, bz + r.randf_range(-0.35, 0.35))
		B.detail("box", "alu" if r.randf() < 0.5 else "kitgrey",
			Batcher.xf(p2, Vector3(r.randf_range(0.02, 0.05), 0.02, r.randf_range(0.10, 0.26)), r.randf() * TAU), kcol())
	# tool board on the wall
	B.prop("box", "kitgrey", Batcher.xf(Vector3(bx, y + 1.85, z0 + 0.32), Vector3(3.2, 1.1, 0.04)), kcol(0.6, 0.8))
	for k in 22:
		var p3 := Vector3(bx + r.randf_range(-1.5, 1.5), y + 1.45 + r.randf_range(0.0, 0.75), z0 + 0.36)
		B.detail("box", "alu", Batcher.xf(p3, Vector3(r.randf_range(0.015, 0.05), r.randf_range(0.10, 0.32), 0.02), r.randf_range(-0.2, 0.2)), kcol())
	# terminal: a rugged case with a screen, on the bench
	B.prop("casebox", "kitgrey", Batcher.xf(Vector3(bx + 1.9, y + 1.10, bz - 0.05), Vector3(0.52, 0.36, 0.30), -0.3), kcol())
	B.add("box", "screen", Batcher.xf(Vector3(bx + 1.9, y + 1.12, bz - 0.19), Vector3(0.46, 0.28, 0.01), -0.3, 0.18), Color(1, 1, 1), Batcher.PROP, true)
	lights.append([Vector3(bx + 1.9, y + 1.4, bz - 0.5), Color(0.75, 0.80, 0.95), 1.2, 3.0, true])
	# parts rack: four bays of shelves full of bins
	var rx := x0 + 1.2
	for bay in 3:
		for shelf in 4:
			var sy := y + 0.35 + 0.55 * float(shelf)
			B.prop("box", "kitgrey", Batcher.xf(Vector3(rx + 0.9 * float(bay), sy, z0 + 0.55), Vector3(0.86, 0.04, 0.55)), kcol())
			for bn in 3:
				if r.randf() < 0.2:
					continue
				B.detail("casebox", "bone" if r.randf() < 0.6 else "amber",
					Batcher.xf(Vector3(rx + 0.9 * float(bay) - 0.28 + 0.28 * float(bn), sy + 0.11, z0 + 0.55 + r.randf_range(-0.06, 0.06)),
						Vector3(0.24, 0.17, 0.42)), kcol())
		for post in [-0.43, 0.43]:
			B.prop("angle", "kitgrey", Batcher.xf(Vector3(rx + 0.9 * float(bay) + post, y + 1.2, z0 + 0.3), Vector3(0.06, 2.4, 0.06)), kcol())
			B.prop("angle", "kitgrey", Batcher.xf(Vector3(rx + 0.9 * float(bay) + post, y + 1.2, z0 + 0.8), Vector3(0.06, 2.4, 0.06)), kcol())
	# flight cases stacked, labelled
	for k in 7:
		var cx := x1 - 1.6 - r.randf_range(0.0, 1.4)
		var cz := z0 + 0.9 + r.randf_range(0.0, 1.2)
		var st := float(k % 3)
		B.prop("casebox", "kitgrey", Batcher.xf(Vector3(cx, y + 0.22 + 0.45 * st, cz),
			Vector3(0.86, 0.44, 0.60), r.randf_range(-0.2, 0.2)), kcol(0.5, 0.7))
		B.detail("box", "bone", Batcher.xf(Vector3(cx, y + 0.22 + 0.45 * st, cz - 0.31),
			Vector3(0.32, 0.14, 0.01), r.randf_range(-0.2, 0.2)), kcol())
	# cable reels and a loom into the roof
	for k in 3:
		var dx := x0 + 2.6 + 1.3 * float(k)
		B.prop("wheel", "kitgrey", Batcher.xf(Vector3(dx, y + 0.42, z1 - 0.9), Vector3(0.82, 0.82, 0.58), 0.0, 0.0, PI * 0.5), kcol())
		B.prop("cyl", "rubber", Batcher.xf(Vector3(dx, y + 0.42, z1 - 0.9), Vector3(0.60, 0.42, 0.60), 0.0, 0.0, PI * 0.5), kcol(0.7, 0.9))
	_cable_run(Vector3(x0 + 0.6, y + h - 0.3, z0 + 0.4), Vector3(x1 - 0.6, y + h - 0.3, z0 + 0.4), 7, 0.035)
	# work light under the roof (DESIGN-PRINCIPLES 3: the surface is safe and lit)
	for k in 3:
		var lx2 := x0 + 3.0 + 4.0 * float(k)
		B.prop("box", "alu", Batcher.xf(Vector3(lx2, y + h + 0.28, (z0 + z1) * 0.5), Vector3(1.3, 0.10, 0.22)), kcol())
		B.add("box", "glass", Batcher.xf(Vector3(lx2, y + h + 0.21, (z0 + z1) * 0.5), Vector3(1.2, 0.03, 0.16)), Color(1, 1, 1))
		# RULE. A roofed bay is dark at noon, so the bay's own work lights are on in
		# every lighting condition, not only after dark. The 5th field is that flag.
		lights.append([Vector3(lx2, y + h + 0.10, (z0 + z1) * 0.5), Color(1.0, 0.96, 0.90), 7.5, 12.0, true])

func _building(kind: String) -> Dictionary:
	for b in L.plan["buildings"]:
		if b["kind"] == kind:
			return b
	return {}

## a cable tray with N cables in it, sagging between supports
func _cable_run(a: Vector3, b: Vector3, n: int, w: float) -> void:
	B.prop("channel", "alu", Batcher.beam_xf(a, b, 0.30, 0.14), kcol())
	var dir := (b - a).normalized()
	var side := dir.cross(Vector3.UP).normalized()
	for i in n:
		var off := side * (-0.11 + 0.22 * float(i) / float(maxi(n - 1, 1)))
		var col := Color(0.8, 0.8, 0.8) if i % 3 != 0 else Color(1.4, 1.0, 0.5)
		B.detail("cyl6", "rubber", Batcher.beam_xf(a + off + Vector3(0, -0.05, 0), b + off + Vector3(0, -0.05, 0), w, w), col)

# ================================================================== gantry
## RULE. A rail gantry spanning the bay and reaching out over the yard: two rails
## on legs, a crab, a hoist block on a chain, and a lifting frame that fits a
## machine. This is the "handling gear" that makes servicing plausible.
func _gantry() -> void:
	var G: Dictionary = L.plan["gantry"]
	var x0 := float(G["x0"]) / 1000.0
	var x1 := float(G["x1"]) / 1000.0
	var z := float(G["z"]) / 1000.0
	var h := float(G["h"]) / 1000.0
	var g := float(G["rail_gauge"]) / 2000.0
	var y := L.pad_h() / 1000.0
	for side in [-1.0, 1.0]:
		B.beam("ibeam", "kitgrey", Vector3(x0, y + h, z + side * g), Vector3(x1 + 4.0, y + h, z + side * g), 0.26, 0.26, kcol())
		var n := int((x1 + 4.0 - x0) / 3.6)
		for i in range(n + 1):
			var x := x0 + (x1 + 4.0 - x0) * float(i) / float(n)
			B.add("ibeam", "kitgrey", Batcher.xf(Vector3(x, y + h * 0.5, z + side * g), Vector3(0.2, h, 0.2)), kcol())
			if i < n:
				B.prop("angle", "kitgrey", Batcher.beam_xf(Vector3(x, y + 0.4, z + side * g),
					Vector3(x + (x1 + 4.0 - x0) / float(n), y + h - 0.2, z + side * g), 0.09, 0.09), kcol())
	# the crab and hoist
	var cx := x1 + 1.2
	B.beam("ibeam", "kitgrey", Vector3(cx, y + h + 0.30, z - g), Vector3(cx, y + h + 0.30, z + g), 0.24, 0.24, kcol())
	B.prop("casebox", "kitgrey", Batcher.xf(Vector3(cx, y + h + 0.30, z + 0.9), Vector3(0.7, 0.5, 0.9)), kcol())
	B.prop("cyl6", "steel", Batcher.xf(Vector3(cx, y + h - 0.55, z + 0.9), Vector3(0.03, 1.4, 0.03)), kcol(0.5, 0.8))
	B.prop("casebox", "amber", Batcher.xf(Vector3(cx, y + h - 1.35, z + 0.9), Vector3(0.24, 0.30, 0.20)), kcol())
	# the lifting frame, hanging just above a machine
	var fy := y + h - 1.9
	for e in [[-0.45, -0.28, 0.45, -0.28], [-0.45, 0.28, 0.45, 0.28], [-0.45, -0.28, -0.45, 0.28], [0.45, -0.28, 0.45, 0.28]]:
		B.prop("angle", "alu", Batcher.beam_xf(Vector3(cx + e[0], fy, z + 0.9 + e[1]), Vector3(cx + e[2], fy, z + 0.9 + e[3]), 0.05, 0.05), kcol())
	for e2 in [[-0.45, -0.28], [0.45, -0.28], [-0.45, 0.28], [0.45, 0.28]]:
		B.detail("cyl6", "steel", Batcher.beam_xf(Vector3(cx + e2[0], fy, z + 0.9 + e2[1]), Vector3(cx, y + h - 1.42, z + 0.9), 0.012, 0.012), kcol(0.6, 0.9))

# ============================================================== charge row
## RULE. Five pedestals on the 2.4 m module along the pad edge, each with a
## chamfered head, a warm pilot, a coiled cable on a hook, and a painted stand
## box on the ground. Three of the five have a machine on them.
func _charge_row() -> void:
	var Z := _zone("charge_row")
	if Z.is_empty():
		return
	var x0 := float(Z["x0"]) / 1000.0
	var x1 := float(Z["x1"]) / 1000.0
	var z := float(Z["z0"]) / 1000.0
	var y := L.pad_h() / 1000.0
	var n := 5
	for i in n:
		var x := x0 + (x1 - x0) * (float(i) + 0.5) / float(n)
		B.prop("casebox", "kitgrey", Batcher.xf(Vector3(x, y + 0.62, z), Vector3(0.42, 1.24, 0.34)), kcol())
		B.prop("casebox", "bone", Batcher.xf(Vector3(x, y + 1.30, z), Vector3(0.46, 0.16, 0.38)), kcol())
		B.add("box", "amber", Batcher.xf(Vector3(x, y + 1.34, z - 0.20), Vector3(0.22, 0.03, 0.01)), Color(1, 1, 1), Batcher.PROP, true)
		B.detail("box", "bone", Batcher.xf(Vector3(x, y + 0.95, z - 0.18), Vector3(0.20, 0.12, 0.01)), kcol())
		B.prop("box", "alu", Batcher.xf(Vector3(x, y + 0.03, z), Vector3(0.7, 0.06, 0.6)), kcol())
		# coiled cable on the hook
		for k in 7:
			var a := TAU * float(k) / 7.0
			B.detail("cyl6", "rubber", Batcher.xf(Vector3(x + 0.26, y + 0.85 + sin(a) * 0.16, z + cos(a) * 0.16),
				Vector3(0.028, 0.16, 0.028), 0.0, 0.0, a), Color(0.9, 0.9, 0.9))
		# the painted stand box
		B.detail("box", "amber", Batcher.xf(Vector3(x - 0.9, y + 0.005, z + 1.0), Vector3(1.5, 0.01, 1.4)), Color(0.8, 0.8, 0.8))
		lights.append([Vector3(x, y + 1.36, z), Color(1.0, 0.72, 0.42), 0.8, 3.0])
	# the feeder: a trunking run along the back with a ramp cover across the walkway
	_cable_run(Vector3(x0 - 0.5, y + 0.14, z - 0.55), Vector3(x1 + 0.5, y + 0.14, z - 0.55), 5, 0.03)
	for k in 3:
		B.detail("box", "amber", Batcher.xf(Vector3(x0 + 2.0 + 3.0 * float(k), y + 0.05, z + 1.6), Vector3(0.6, 0.10, 1.6)), Color(0.7, 0.7, 0.7))
	# a battery skid: a container-sized box with cooling fins and a fan bank
	B.add("casebox", "kitgrey", Batcher.xf(Vector3(x0 - 2.6, y + 1.15, z + 1.1), Vector3(2.4, 2.3, 2.2)), kcol())
	for k in 12:
		B.detail("box", "alu", Batcher.xf(Vector3(x0 - 2.6 + (-1.0 + 0.18 * float(k)), y + 1.6, z + 2.22), Vector3(0.05, 1.1, 0.10)), kcol())
	for k in 2:
		B.prop("ring", "kitgrey", Batcher.xf(Vector3(x0 - 3.2 + 1.2 * float(k), y + 1.9, z - 0.02), Vector3(0.62, 0.10, 0.62), 0.0, PI * 0.5), kcol())
	B.detail("box", "bone", Batcher.xf(Vector3(x0 - 2.6, y + 1.1, z - 0.02), Vector3(0.5, 0.3, 0.02)), kcol())

func _zone(kind: String) -> Dictionary:
	for zz in L.plan["zones"]:
		if zz["kind"] == kind:
			return zz
	return {}

# ============================================================== containers
## RULE. 6.06 x 2.44 x 2.59 boxes on the 2.44 module, stacked to two where the
## row is deep, corrugated on a 0.28 pitch, doors on one end, a stair and a rail
## on the ones in use. Half old and rusted, half the players' recent grey.
func _containers() -> void:
	var Z := _zone("container_row")
	if Z.is_empty():
		return
	var x0 := float(Z["x0"]) / 1000.0
	var z0 := float(Z["z0"]) / 1000.0
	var z1 := float(Z["z1"]) / 1000.0
	var y := L.pad_h() / 1000.0
	var rows := int((z1 - z0) / 3.0)
	for i in rows:
		var z := z0 + 3.0 * (float(i) + 0.5)
		var stack := 2 if (i % 3 == 1) else 1
		var mat := "kitgrey" if i % 2 == 0 else "iron"
		for s in stack:
			var cy := y + 1.30 + 2.62 * float(s)
			var yaw := r.randf_range(-0.02, 0.02)
			B.add("box", mat, Batcher.xf(Vector3(x0 + 3.2, cy, z), Vector3(6.06, 2.59, 2.44), yaw),
				kcol(0.55, 0.9) if mat == "kitgrey" else ircol(0.6, 1.5))
			# corrugations
			for k in 20:
				B.prop("cyl6", mat, Batcher.xf(Vector3(x0 + 3.2 - 2.8 + 0.29 * float(k), cy, z + 1.24),
					Vector3(0.10, 2.4, 0.10), yaw), kcol(0.55, 0.9) if mat == "kitgrey" else ircol(0.6, 1.5))
				B.prop("cyl6", mat, Batcher.xf(Vector3(x0 + 3.2 - 2.8 + 0.29 * float(k), cy, z - 1.24),
					Vector3(0.10, 2.4, 0.10), yaw), kcol(0.55, 0.9) if mat == "kitgrey" else ircol(0.6, 1.5))
			# corner castings
			for ex in [-3.03, 3.03]:
				for ez in [-1.22, 1.22]:
					for ey in [-1.28, 1.28]:
						B.prop("box", "iron", Batcher.xf(Vector3(x0 + 3.2 + ex, cy + ey, z + ez), Vector3(0.20, 0.18, 0.20)), ircol())
			# doors on the west end
			B.prop("box", mat, Batcher.xf(Vector3(x0 + 0.14, cy, z - 0.61), Vector3(0.05, 2.4, 1.16), yaw), kcol(0.5, 0.8))
			B.prop("box", mat, Batcher.xf(Vector3(x0 + 0.14, cy, z + 0.61), Vector3(0.05, 2.4, 1.16), yaw), kcol(0.5, 0.8))
			for k2 in 4:
				B.detail("cyl", "iron", Batcher.xf(Vector3(x0 + 0.08, cy, z - 0.9 + 0.6 * float(k2)), Vector3(0.05, 2.3, 0.05)), ircol())
			# label panel
			B.detail("box", "bone", Batcher.xf(Vector3(x0 + 3.2, cy + 0.75, z + 1.28), Vector3(1.1, 0.34, 0.01)), kcol())
		if i % 3 == 1:
			# a stair and landing up the double stack
			B.prop("box", "galv", Batcher.xf(Vector3(x0 - 0.7, y + 1.4, z), Vector3(1.2, 0.06, 2.2)), kcol())
			for k3 in 7:
				B.detail("box", "galv", Batcher.xf(Vector3(x0 - 1.2 - 0.3 * float(k3), y + 1.35 - 0.19 * float(k3), z), Vector3(0.3, 0.05, 1.0)), kcol())

# =================================================================== tanks
## RULE. Vertical tanks on a bunded slab, banded every 1.2 m, with a caged
## ladder, a walkway between them, and a valve manifold at the foot.
func _tanks() -> void:
	var Z := _zone("tank_farm")
	if Z.is_empty():
		return
	var x0 := float(Z["x0"]) / 1000.0
	var z0 := float(Z["z0"]) / 1000.0
	var z1 := float(Z["z1"]) / 1000.0
	var y := L.pad_h() / 1000.0
	# bund
	for side in [-1.0, 1.0]:
		B.add("box", "stone", Batcher.xf(Vector3(x0 + 3.0, y + 0.30, (z0 + z1) * 0.5 + side * 5.5), Vector3(8.0, 0.6, 0.35)), kcol(0.7, 1.0))
		B.add("box", "stone", Batcher.xf(Vector3(x0 + 3.0 + side * 4.0, y + 0.30, (z0 + z1) * 0.5), Vector3(0.35, 0.6, 11.0)), kcol(0.7, 1.0))
	for i in 3:
		var z := z0 + 2.0 + 3.6 * float(i)
		var rr := 1.55
		var hh := 6.2 + r.randf_range(-0.6, 0.9)
		B.add("cyl", "iron", Batcher.xf(Vector3(x0 + 3.0, y + hh * 0.5, z), Vector3(rr * 2.0, hh, rr * 2.0)), ircol(0.5, 1.4))
		for k in int(hh / 1.2):
			B.prop("ring", "iron", Batcher.xf(Vector3(x0 + 3.0, y + 0.6 + 1.2 * float(k), z), Vector3(rr * 2.1, 0.10, rr * 2.1)), ircol())
			var a0 := Vector3(x0 + 3.0 - rr, y + 0.6 + 1.2 * float(k), z)
			var a1 := Vector3(x0 + 3.0 + rr, y + 0.6 + 1.2 * float(k), z)
			B.detail("hex", "iron", Batcher.xf(a0, Vector3(0.09, 0.07, 0.09), 0.0, 0.0, PI * 0.5), ircol(0.8, 1.7))
			B.detail("hex", "iron", Batcher.xf(a1, Vector3(0.09, 0.07, 0.09), 0.0, 0.0, PI * 0.5), ircol(0.8, 1.7))
		# conical top and a vent
		B.prop("cone", "iron", Batcher.xf(Vector3(x0 + 3.0, y + hh + 0.35, z), Vector3(rr * 2.0, 0.8, rr * 2.0)), ircol())
		B.prop("cyl", "iron", Batcher.xf(Vector3(x0 + 3.0, y + hh + 1.0, z), Vector3(0.2, 0.9, 0.2)), ircol())
		# caged ladder
		B.add("ladder", "iron", Batcher.xf(Vector3(x0 + 3.0 - rr - 0.28, y + hh * 0.5, z), Vector3(0.5, hh, 0.1)), ircol())
		for k2 in int(hh - 2.0):
			B.detail("ring", "iron", Batcher.xf(Vector3(x0 + 3.0 - rr - 0.05, y + 2.0 + float(k2), z), Vector3(1.3, 0.04, 1.3), 0.0, 0.0, PI * 0.5), ircol())
		# manifold at the foot
		var mp := Vector3(x0 + 3.0 + rr, y + 0.35, z)
		B.prop("cyl", "iron", Batcher.xf(mp + Vector3(0.5, 0, 0), Vector3(0.22, 1.4, 0.22), 0.0, 0.0, PI * 0.5), ircol())
		B.prop("wheel", "iron", Batcher.xf(mp + Vector3(0.9, 0.3, 0), Vector3(0.42, 0.42, 0.08), 0.0, PI * 0.5), ircol())
		B.detail("box", "bone", Batcher.xf(mp + Vector3(0.2, 0.9, -0.1), Vector3(0.30, 0.20, 0.01)), kcol())
	# pipe bridge out of the farm to the winding house
	var py := y + 4.4
	B.beam("cyl", "iron", Vector3(x0 + 4.6, py, z0 + 2.0), Vector3(x0 + 4.6, py, z1 - 1.0), 0.26, 0.26, ircol())
	B.beam("cyl", "iron", Vector3(x0 + 4.9, py - 0.35, z0 + 2.0), Vector3(x0 + 4.9, py - 0.35, z1 - 1.0), 0.18, 0.18, ircol())
	for k in 5:
		var zz := z0 + 2.0 + (z1 - z0 - 3.0) * float(k) / 4.0
		B.prop("angle", "iron", Batcher.xf(Vector3(x0 + 4.75, y + py * 0.5 - 0.1, zz), Vector3(0.12, py - y, 0.12)), ircol())

# ============================================================= transformer
## RULE. A fenced pen holding two transformers with radiator banks, a switch
## cabinet row, bushings, and a cable trench under a chequer plate lid.
func _transformer() -> void:
	var Z := _zone("transformer")
	if Z.is_empty():
		return
	var x0 := float(Z["x0"]) / 1000.0
	var z0 := float(Z["z0"]) / 1000.0
	var x1 := float(Z["x1"]) / 1000.0
	var z1 := float(Z["z1"]) / 1000.0
	var y := L.pad_h() / 1000.0
	_pen(x0, z0, x1, z1, 2.2)
	for i in 2:
		var cx := x0 + 2.0 + 3.2 * float(i)
		var cz := (z0 + z1) * 0.5
		B.add("box", "kitgrey", Batcher.xf(Vector3(cx, y + 1.1, cz), Vector3(2.0, 2.2, 1.6)), kcol(0.5, 0.75))
		for k in 14:
			B.prop("box", "kitgrey", Batcher.xf(Vector3(cx - 0.9 + 0.14 * float(k), y + 1.1, cz + 1.05), Vector3(0.06, 1.9, 0.5)), kcol(0.5, 0.75))
		for k2 in 3:
			B.prop("cyl", "bone", Batcher.xf(Vector3(cx - 0.6 + 0.6 * float(k2), y + 2.5, cz), Vector3(0.24, 0.7, 0.24)), Color(1, 1, 1))
			B.detail("ring", "bone", Batcher.xf(Vector3(cx - 0.6 + 0.6 * float(k2), y + 2.65, cz), Vector3(0.36, 0.06, 0.36)), Color(1, 1, 1))
		B.detail("box", "amber", Batcher.xf(Vector3(cx, y + 1.6, cz - 0.82), Vector3(0.34, 0.26, 0.01)), Color(0.9, 0.9, 0.9))
	for i in 4:
		B.prop("casebox", "kitgrey", Batcher.xf(Vector3(x0 + 0.9, y + 0.95, z0 + 1.0 + 1.0 * float(i)), Vector3(0.8, 1.9, 0.9)), kcol(0.55, 0.8))
	B.prop("box", "galv", Batcher.xf(Vector3((x0 + x1) * 0.5, y + 0.06, z1 - 0.7), Vector3(x1 - x0 - 0.6, 0.06, 0.8)), kcol())

func _pen(x0: float, z0: float, x1: float, z1: float, h: float) -> void:
	var y := L.pad_h() / 1000.0
	var segs := [[x0, z0, x1, z0], [x1, z0, x1, z1], [x1, z1, x0, z1], [x0, z1, x0, z0]]
	for s in segs:
		var a := Vector2(s[0], s[1])
		var b := Vector2(s[2], s[3])
		var n := maxi(2, int(a.distance_to(b) / 2.4))
		for i in range(n + 1):
			var p: Vector2 = a.lerp(b, float(i) / float(n))
			B.prop("angle", "galv", Batcher.xf(Vector3(p.x, y + h * 0.5, p.y), Vector3(0.08, h, 0.08)), kcol())
		# palisade
		var m := maxi(2, int(a.distance_to(b) / 0.14))
		for i in m:
			var p2: Vector2 = a.lerp(b, (float(i) + 0.5) / float(m))
			B.detail("box", "galv", Batcher.xf(Vector3(p2.x, y + h * 0.5, p2.y), Vector3(0.035, h - 0.1, 0.035)), kcol(0.6, 1.0))
		B.detail("box", "galv", Batcher.beam_xf(Vector3(a.x, y + h - 0.15, a.y), Vector3(b.x, y + h - 0.15, b.y), 0.04, 0.04), kcol())
		B.detail("box", "galv", Batcher.beam_xf(Vector3(a.x, y + 0.25, a.y), Vector3(b.x, y + 0.25, b.y), 0.04, 0.04), kcol())

# ============================================================== comms mast
## RULE. A three-leg lattice mast on a cast pad, guyed at two levels, carrying
## two dishes, three panel antennas, a cable ladder down one leg and an obstruction
## pilot at the top. This is the uplink; the acoustic link's own end is at the collar.
func _comms_mast() -> void:
	for m in L.plan["masts"]:
		if m["kind"] != "comms":
			continue
		var x := float(m["x"]) / 1000.0
		var z := float(m["z"]) / 1000.0
		var h := float(m["h"]) / 1000.0
		var y := gh(x, z)
		var rr := 0.62
		var legs: Array = []
		for k in 3:
			var a := TAU * float(k) / 3.0
			legs.append(Vector2(cos(a) * rr, sin(a) * rr))
		B.add("box", "stone", Batcher.xf(Vector3(x, y + 0.2, z), Vector3(2.6, 0.4, 2.6)), kcol(0.7, 1.0))
		for k in 3:
			var lp: Vector2 = legs[k]
			B.add("cyl", "galv", Batcher.xf(Vector3(x + lp.x, y + h * 0.5, z + lp.y), Vector3(0.13, h, 0.13)), kcol(0.7, 1.05))
		var bays := int(h / 1.2)
		for i in bays:
			var yy := y + 1.2 * float(i)
			for k in 3:
				var a1: Vector2 = legs[k]
				var b1: Vector2 = legs[(k + 1) % 3]
				B.detail("cyl6", "galv", Batcher.beam_xf(Vector3(x + a1.x, yy, z + a1.y), Vector3(x + b1.x, yy, z + b1.y), 0.05, 0.05), kcol(0.7, 1.05))
				B.detail("cyl6", "galv", Batcher.beam_xf(Vector3(x + a1.x, yy, z + a1.y), Vector3(x + b1.x, yy + 1.2, z + b1.y), 0.042, 0.042), kcol(0.7, 1.05))
		# guys
		for k in 3:
			var a2 := TAU * float(k) / 3.0 + 0.5
			var anch := Vector3(x + cos(a2) * h * 0.55, y, z + sin(a2) * h * 0.55)
			B.prop("box", "stone", Batcher.xf(anch + Vector3(0, 0.15, 0), Vector3(0.8, 0.3, 0.8)), kcol(0.7, 1.0))
			for lvl in [0.55, 0.85]:
				B.add("cyl6", "galv", Batcher.beam_xf(Vector3(x, y + h * lvl, z), anch + Vector3(0, 0.3, 0), 0.02, 0.02), kcol(0.6, 0.9))
		# dishes and panels
		for k in 2:
			var a3 := 1.2 + float(k) * 2.4
			B.prop("dish", "bone", Batcher.xf(Vector3(x + cos(a3) * 0.95, y + h * 0.72 + float(k) * 2.2, z + sin(a3) * 0.95),
				Vector3(1.5, 0.6, 1.5), a3, -PI * 0.5 + 0.25), kcol())
			B.prop("cyl", "galv", Batcher.xf(Vector3(x + cos(a3) * 0.75, y + h * 0.72 + float(k) * 2.2, z + sin(a3) * 0.75), Vector3(0.07, 1.2, 0.07)), kcol())
		for k in 3:
			var a4 := TAU * float(k) / 3.0 + 0.3
			B.prop("casebox", "bone", Batcher.xf(Vector3(x + cos(a4) * 0.85, y + h - 1.6, z + sin(a4) * 0.85),
				Vector3(0.22, 1.5, 0.14), a4), kcol())
		# cable ladder down one leg
		B.prop("ladder", "galv", Batcher.xf(Vector3(x + legs[0].x + 0.22, y + h * 0.5, z + legs[0].y), Vector3(0.34, h, 0.06)), kcol())
		for k in 6:
			B.detail("cyl6", "rubber", Batcher.beam_xf(Vector3(x + legs[0].x + 0.30, y + 0.2, z + legs[0].y - 0.09 + 0.036 * float(k)),
				Vector3(x + legs[0].x + 0.30, y + h - 1.0, z + legs[0].y - 0.09 + 0.036 * float(k)), 0.022, 0.022), Color(0.7, 0.7, 0.7))
		B.add("cyl", "amber", Batcher.xf(Vector3(x, y + h + 0.25, z), Vector3(0.2, 0.22, 0.2)), Color(1, 1, 1), Batcher.SITE, true)
		lights.append([Vector3(x, y + h + 0.25, z), Color(1.0, 0.66, 0.35), 1.5, 6.0])

# ============================================================ zone clutter
## RULE. Each zone rectangle is filled by a table that says what goes in it and
## how densely. This is the whole of "walking distance": a yard is not props
## placed by hand, it is six zones with a stocking rule each.
func _zone_clutter() -> void:
	for zz in L.plan["zones"]:
		var kind: String = zz["kind"]
		var x0 := float(zz["x0"]) / 1000.0
		var z0 := float(zz["z0"]) / 1000.0
		var x1 := float(zz["x1"]) / 1000.0
		var z1 := float(zz["z1"]) / 1000.0
		match kind:
			"pallets":
				_fill_pallets(x0, z0, x1, z1)
			"drums":
				_fill_drums(x0, z0, x1, z1)
			"spares":
				_fill_spares(x0, z0, x1, z1)
			"scrap":
				_fill_scrap(x0, z0, x1, z1)

func _fill_pallets(x0: float, z0: float, x1: float, z1: float) -> void:
	var y := L.pad_h() / 1000.0
	var nx := int((x1 - x0) / 1.4)
	var nz := int((z1 - z0) / 1.4)
	for i in nx:
		for j in nz:
			if r.randf() < 0.3:
				continue
			var x := x0 + 1.4 * (float(i) + 0.5)
			var z := z0 + 1.4 * (float(j) + 0.5)
			var stack := r.randi_range(1, 4)
			var yaw := r.randf_range(-0.25, 0.25)
			for s in stack:
				B.prop("pallet", "timber", Batcher.xf(Vector3(x, y + 0.075 + 0.42 * float(s), z), Vector3(1.2, 0.15, 1.0), yaw), kcol(0.6, 1.1))
				if r.randf() < 0.75:
					B.prop("box", "bone" if r.randf() < 0.4 else "timber",
						Batcher.xf(Vector3(x + r.randf_range(-0.06, 0.06), y + 0.30 + 0.42 * float(s), z), Vector3(1.05, 0.30, 0.88), yaw + r.randf_range(-0.06, 0.06)),
						kcol(0.6, 1.0))
				if r.randf() < 0.4:
					for k in 4:
						B.detail("box", "plastic", Batcher.xf(Vector3(x, y + 0.30 + 0.42 * float(s), z) + Vector3(0, 0.16, -0.44 + 0.29 * float(k)),
							Vector3(1.06, 0.01, 0.03), yaw), Color(0.8, 0.8, 0.8))

func _fill_drums(x0: float, z0: float, x1: float, z1: float) -> void:
	var y := L.pad_h() / 1000.0
	var n := int((x1 - x0) * (z1 - z0) * 0.7)
	for i in n:
		var x := r.randf_range(x0, x1)
		var z := r.randf_range(z0, z1)
		var lying := r.randf() < 0.22
		var mat: String = ["iron", "iron", "amber", "kitgrey"][r.randi() % 4]
		if lying:
			B.prop("drum", mat, Batcher.xf(Vector3(x, y + 0.29, z), Vector3(0.58, 0.88, 0.58), r.randf() * TAU, 0.0, PI * 0.5),
				ircol(0.5, 1.4) if mat == "iron" else kcol(0.5, 0.9))
		else:
			B.prop("drum", mat, Batcher.xf(Vector3(x, y + 0.44, z), Vector3(0.58, 0.88, 0.58), r.randf() * TAU),
				ircol(0.5, 1.4) if mat == "iron" else kcol(0.5, 0.9))
			if r.randf() < 0.3:
				B.detail("box", "bone", Batcher.xf(Vector3(x, y + 0.55, z + 0.30), Vector3(0.22, 0.16, 0.01), r.randf() * 0.4), kcol())

func _fill_spares(x0: float, z0: float, x1: float, z1: float) -> void:
	var y := L.pad_h() / 1000.0
	# a racked spares yard: uprights, beams, and stock on the shelves
	var bays := int((z1 - z0) / 2.4)
	for b in bays:
		var z := z0 + 2.4 * (float(b) + 0.5)
		for post in [x0 + 0.3, x1 - 0.3]:
			B.prop("angle", "ember", Batcher.xf(Vector3(post, y + 1.6, z - 1.1), Vector3(0.10, 3.2, 0.10)), kcol(0.6, 0.9))
			B.prop("angle", "ember", Batcher.xf(Vector3(post, y + 1.6, z + 1.1), Vector3(0.10, 3.2, 0.10)), kcol(0.6, 0.9))
		for shelf in 3:
			var sy := y + 0.55 + 1.0 * float(shelf)
			for zz in [z - 1.1, z + 1.1]:
				B.prop("box", "ember", Batcher.xf(Vector3((x0 + x1) * 0.5, sy, zz), Vector3(x1 - x0 - 0.6, 0.09, 0.10)), kcol(0.6, 0.9))
			# stock
			var m := r.randi_range(2, 5)
			for k in m:
				var sx := r.randf_range(x0 + 0.8, x1 - 0.8)
				var kind := r.randi() % 4
				if kind == 0:
					B.prop("casebox", "kitgrey", Batcher.xf(Vector3(sx, sy + 0.35, z), Vector3(0.9, 0.6, 1.6), r.randf_range(-0.1, 0.1)), kcol(0.5, 0.8))
				elif kind == 1:
					for t in r.randi_range(3, 7):
						B.detail("cyl", "iron", Batcher.xf(Vector3(sx, sy + 0.12 + 0.22 * float(t / 3), z - 0.4 + 0.22 * float(t % 3)),
							Vector3(0.20, 2.0, 0.20), 0.0, 0.0, PI * 0.5), ircol())
				elif kind == 2:
					B.prop("box", "timber", Batcher.xf(Vector3(sx, sy + 0.2, z), Vector3(1.1, 0.4, 1.8), r.randf_range(-0.08, 0.08)), kcol(0.6, 1.0))
				else:
					for t2 in 4:
						B.detail("angle", "iron", Batcher.xf(Vector3(sx + 0.1 * float(t2), sy + 0.1, z), Vector3(0.12, 2.0, 0.12), 0.0, 0.0, PI * 0.5), ircol())

func _fill_scrap(x0: float, z0: float, x1: float, z1: float) -> void:
	var n := int((x1 - x0) * (z1 - z0) * 1.6)
	for i in n:
		var x := r.randf_range(x0, x1)
		var z := r.randf_range(z0, z1)
		var y := gh(x, z) + r.randf_range(0.0, 0.55)
		var kind := r.randi() % 5
		var col := ircol(0.5, 1.6)
		match kind:
			0: B.detail("angle", "iron", Batcher.xf(Vector3(x, y, z), Vector3(0.14, r.randf_range(0.8, 2.6), 0.14), r.randf() * TAU, r.randf_range(-1.4, 1.4), r.randf_range(-1.4, 1.4)), col)
			1: B.detail("cyl", "iron", Batcher.xf(Vector3(x, y, z), Vector3(0.24, r.randf_range(0.5, 1.8), 0.24), r.randf() * TAU, r.randf_range(-1.4, 1.4), r.randf_range(-1.4, 1.4)), col)
			2: B.detail("box", "iron", Batcher.xf(Vector3(x, y, z), Vector3(r.randf_range(0.3, 1.1), 0.04, r.randf_range(0.3, 0.9)), r.randf() * TAU, r.randf_range(-0.8, 0.8), r.randf_range(-0.8, 0.8)), col)
			3: B.detail("wheel", "iron", Batcher.xf(Vector3(x, y, z), Vector3(r.randf_range(0.5, 1.2), r.randf_range(0.5, 1.2), 0.16), r.randf() * TAU, r.randf_range(-1.5, 1.5)), col)
			4: B.detail("ibeam", "iron", Batcher.xf(Vector3(x, y, z), Vector3(0.22, r.randf_range(1.0, 3.2), 0.22), r.randf() * TAU, r.randf_range(-1.5, 1.5), r.randf_range(-0.4, 0.4)), col)

# ================================================================ machines
## RULE. A parametric quadruped, ~0.77 m long, built from 34 instances: hull,
## deck modules, head and sensor bar, four three-segment legs, recovery handle,
## charge port, flank strip. Pose is a parameter: STAND, DOCK (legs folded on a
## charge plate), CRADLE (up on the service frame), WRECK (rolled, one leg gone).
## Player value inversion (ART-DIRECTION 4.3): pale shell over graphite chassis.
func _machines() -> void:
	var y := L.pad_h() / 1000.0
	var Z := _zone("charge_row")
	var x0 := float(Z["x0"]) / 1000.0
	var x1 := float(Z["x1"]) / 1000.0
	var cz := float(Z["z0"]) / 1000.0
	# three docked on charge
	for i in 3:
		var x := x0 + (x1 - x0) * (float(i) + 0.5) / 5.0
		_walker(Vector3(x, y, cz + 1.1), PI * 0.5, "dock", 0.35)
	# one on the service cradle in the bay, panels off
	var G: Dictionary = L.plan["gantry"]
	_cradle(Vector3(float(G["x1"]) / 1000.0 + 1.2, y, float(G["z"]) / 1000.0 + 0.9))
	_walker(Vector3(float(G["x1"]) / 1000.0 + 1.2, y + 0.72, float(G["z"]) / 1000.0 + 0.9), 0.15, "cradle", 0.55)
	# one at the collar, about to be sent down
	_walker(Vector3(-3.6, y, -1.4), 0.4, "stand", 0.62)
	# one walking in from the course
	_walker(Vector3(19.0, gh(19.0, 3.0), 3.0), PI, "stand", 0.30)
	# two on the course
	var C: Dictionary = L.plan["course"]
	var nodes: Array = C["nodes"]
	if nodes.size() > 5:
		var pitch := float(C["pitch"]) / 1000.0
		var n1: Array = nodes[3]
		var p1 := Vector3(float(C["ox"]) / 1000.0 + float(n1[0]) * pitch, 0, float(C["oz"]) / 1000.0 + float(n1[1]) * pitch)
		p1.y = gh(p1.x, p1.z)
		_walker(p1, 0.9, "stand", 0.45)
	# a rank of machines waiting on the muster square, and one being walked in
	var M := _zone("muster")
	if not M.is_empty():
		var mx0 := float(M["x0"]) / 1000.0
		var mz0 := float(M["z0"]) / 1000.0
		for i in 4:
			_walker(Vector3(mx0 + 1.1 + 1.7 * float(i), y, mz0 + 1.4 + (0.5 if i % 2 == 0 else 0.0)),
				-PI * 0.5 + r.randf_range(-0.2, 0.2), "stand", r.randf_range(0.15, 0.7))
	_walker(Vector3(-8.5, y, 5.5), 0.2, "stand", 0.5)
	_walker(Vector3(6.5, y, 4.0), PI * 0.8, "stand", 0.25)
	_walker(Vector3(-13.0, y, -8.5), PI * 0.25, "stand", 0.4)
	# a wreck on a trestle by the bench: the extraction loop's loss, made visible
	_wreck(Vector3(-16.0, y + 0.62, -4.4), 0.7)
	_trestle(Vector3(-16.0, y, -4.4))

func _walker(base: Vector3, yaw: float, pose: String, wear: float) -> void:
	var ride := 0.32
	if pose == "dock":
		ride = 0.20
	elif pose == "cradle":
		ride = 0.30
	var bas := Basis.from_euler(Vector3(0, yaw, 0))
	var fw := bas * Vector3(1, 0, 0)
	var sd := bas * Vector3(0, 0, 1)
	var hull := base + Vector3(0, ride + 0.085, 0)
	var shell := Color(1, 1, 1).lerp(Color(0.55, 0.5, 0.45), wear * 0.5)
	# hull: pale shell over a graphite chassis (the value inversion)
	B.prop("casebox", "bone", Batcher.xf(hull, Vector3(0.60, 0.115, 0.235), yaw), shell)
	B.prop("casebox", "plastic", Batcher.xf(hull - Vector3(0, 0.085, 0), Vector3(0.58, 0.075, 0.225), yaw), Color(0.8, 0.8, 0.8))
	# flank strips - identity by area, not intensity (ART-DIRECTION 4.3)
	for s in [-1.0, 1.0]:
		B.add("box", "bone", Batcher.xf(hull + sd * s * 0.121, Vector3(0.32, 0.016, 0.004), yaw), Color(1, 1, 1), Batcher.PROP, true)
	# deck modules
	var mods := [Vector3(0.16, 0.055, 0.11), Vector3(0.10, 0.075, 0.09), Vector3(0.20, 0.04, 0.05)]
	for k in mods.size():
		B.prop("casebox", "kitgrey", Batcher.xf(hull + fw * (-0.16 + 0.16 * float(k)) + Vector3(0, 0.085, 0), mods[k], yaw), Color(0.9, 0.9, 0.9))
	# beacon rack: four tubes on the deck
	for k in 4:
		B.detail("cyl", "alu", Batcher.xf(hull + fw * -0.22 + sd * (-0.06 + 0.04 * float(k)) + Vector3(0, 0.10, 0),
			Vector3(0.028, 0.10, 0.028), yaw), Color(1, 1, 1))
	# recovery handle: the one clean thing (ART-DIRECTION 6.2)
	for s2 in [-1.0, 1.0]:
		B.detail("cyl", "alu", Batcher.xf(hull + fw * -0.05 + sd * s2 * 0.07 + Vector3(0, 0.09, 0), Vector3(0.016, 0.07, 0.016), yaw), Color(1, 1, 1))
	B.detail("cyl", "rubber", Batcher.xf(hull + fw * -0.05 + Vector3(0, 0.125, 0), Vector3(0.022, 0.16, 0.022), yaw, 0.0, PI * 0.5), Color(1, 1, 1))
	# neck and head
	var neck := hull + fw * 0.30 + Vector3(0, 0.02, 0)
	B.prop("cyl", "plastic", Batcher.xf(neck, Vector3(0.05, 0.13, 0.05), yaw, 0.0, 0.4), Color(0.9, 0.9, 0.9))
	var head := neck + fw * 0.055 + Vector3(0, 0.085, 0)
	B.prop("casebox", "bone", Batcher.xf(head, Vector3(0.13, 0.10, 0.145), yaw), shell)
	B.add("box", "amber", Batcher.xf(head + fw * 0.066, Vector3(0.004, 0.022, 0.10), yaw), Color(1, 1, 1), Batcher.PROP, true)
	B.detail("cyl", "glass", Batcher.xf(head + fw * 0.066 + Vector3(0, -0.03, 0), Vector3(0.05, 0.012, 0.05), yaw, 0.0, PI * 0.5), Color(1, 1, 1))
	# legs
	var legs := [[0.22, 0.10], [0.22, -0.10], [-0.22, 0.10], [-0.22, -0.10]]
	for li in legs.size():
		var lg: Array = legs[li]
		var hip: Vector3 = hull + fw * lg[0] + sd * lg[1] - Vector3(0, 0.03, 0)
		var spread := 0.0
		if pose == "dock":
			spread = 0.06
		var knee: Vector3 = hip + Vector3(sign(lg[1]) * (0.05 + spread), -ride * 0.55, 0) * 0.0 + fw * (0.02 * signf(lg[0])) + Vector3(0, -ride * 0.5, 0) + sd * signf(lg[1]) * (0.04 + spread)
		var foot := Vector3(hip.x, base.y + 0.02, hip.z) + sd * signf(lg[1]) * (0.02 + spread * 1.5) + fw * (0.03 * signf(lg[0]))
		B.detail("cyl", "plastic", Batcher.xf(hip, Vector3(0.075, 0.06, 0.075), yaw, 0.0, PI * 0.5), Color(0.85, 0.85, 0.85))
		B.detail("box", "kitgrey", Batcher.beam_xf(hip, knee, 0.045, 0.055), Color(0.9, 0.9, 0.9))
		B.detail("box", "plastic", Batcher.beam_xf(knee, foot, 0.032, 0.038), Color(0.6, 0.55, 0.5).lerp(Color(0.32, 0.26, 0.18), wear))
		B.detail("cyl", "rubber", Batcher.xf(foot, Vector3(0.05, 0.035, 0.05)), Color(1, 1, 1))
	# charge cable, if docked
	if pose == "dock":
		var port := hull + fw * -0.25 + sd * 0.10
		var prev := port
		for k in 5:
			var t := float(k + 1) / 5.0
			var p := port.lerp(Vector3(base.x, base.y + 0.9, base.z - 1.1), t)
			p.y += sin(t * PI) * 0.12
			B.detail("cyl6", "rubber", Batcher.beam_xf(prev, p, 0.014, 0.014), Color(0.9, 0.9, 0.9))
			prev = p

func _cradle(p: Vector3) -> void:
	# a yellow service cradle: a frame that holds a machine at working height
	for s in [-1.0, 1.0]:
		for s2 in [-1.0, 1.0]:
			B.prop("box", "amber", Batcher.xf(p + Vector3(s * 0.42, 0.34, s2 * 0.28), Vector3(0.06, 0.68, 0.06)), kcol(0.7, 1.0))
	B.prop("box", "amber", Batcher.xf(p + Vector3(0, 0.68, 0), Vector3(0.98, 0.06, 0.66)), kcol(0.7, 1.0))
	for k in 4:
		B.detail("box", "amber", Batcher.xf(p + Vector3(0, 0.34, -0.28 + 0.186 * float(k)), Vector3(0.92, 0.04, 0.04)), kcol(0.7, 1.0))
	B.detail("cyl", "rubber", Batcher.xf(p + Vector3(0, 0.02, 0), Vector3(0.9, 0.04, 0.66)), Color(0.9, 0.9, 0.9))

func _trestle(p: Vector3) -> void:
	for s in [-1.0, 1.0]:
		B.prop("angle", "galv", Batcher.xf(p + Vector3(s * 0.5, 0.31, -0.3), Vector3(0.06, 0.62, 0.06), 0.0, 0.0, s * 0.12), kcol())
		B.prop("angle", "galv", Batcher.xf(p + Vector3(s * 0.5, 0.31, 0.3), Vector3(0.06, 0.62, 0.06), 0.0, 0.0, s * 0.12), kcol())
	B.prop("box", "timber", Batcher.xf(p + Vector3(0, 0.62, 0), Vector3(1.2, 0.05, 0.8)), kcol(0.6, 1.0))

## a wreck: belly down, rolled, one leg gone below the knee, a shed panel beside
## it, and every emissive dark. ART-DIRECTION 6.2.
func _wreck(p: Vector3, yaw: float) -> void:
	var roll := 0.42
	var bas := Basis.from_euler(Vector3(0, yaw, roll))
	var fw := bas * Vector3(1, 0, 0)
	var sd := bas * Vector3(0, 0, 1)
	var mud := Color(0.30, 0.24, 0.17)
	B.prop("casebox", "bone", Batcher.xf(p, Vector3(0.60, 0.115, 0.235), yaw, 0.0, roll), mud)
	B.prop("casebox", "plastic", Batcher.xf(p - bas * Vector3(0, 0.085, 0), Vector3(0.58, 0.075, 0.225), yaw, 0.0, roll), Color(0.5, 0.5, 0.5))
	# the shed panel, on the deck beside it
	B.prop("casebox", "bone", Batcher.xf(p + Vector3(0.5, -0.55, 0.3), Vector3(0.34, 0.02, 0.20), yaw + 0.9, 0.0, 0.08), mud * 1.2)
	# legs: three folded, one missing below the knee
	var legs := [[0.22, 0.10], [0.22, -0.10], [-0.22, 0.10], [-0.22, -0.10]]
	for li in legs.size():
		var lg: Array = legs[li]
		var hip: Vector3 = p + fw * lg[0] + sd * lg[1]
		var knee: Vector3 = hip + fw * (0.10 * signf(lg[0])) - Vector3(0, 0.10, 0) + sd * signf(lg[1]) * 0.14
		B.detail("box", "kitgrey", Batcher.beam_xf(hip, knee, 0.045, 0.055), mud)
		if li == 1:
			continue
		var foot: Vector3 = knee + fw * (0.14 * signf(lg[0])) + sd * signf(lg[1]) * 0.10 - Vector3(0, 0.06, 0)
		B.detail("box", "plastic", Batcher.beam_xf(knee, foot, 0.032, 0.038), mud * 0.7)
	# the recovery handle: the only clean thing on it
	B.detail("cyl", "rubber", Batcher.xf(p + fw * -0.05 + bas * Vector3(0, 0.125, 0), Vector3(0.022, 0.16, 0.022), yaw, 0.0, PI * 0.5 + roll), Color(1.3, 1.3, 1.3))

# ================================================================= signage
## RULE. Signs on the 1.2 m module wherever a register meets another: at the
## gate, on the pen, at the collar, on the bay. Pale plate on a galvanised post.
func _signage() -> void:
	var spots := [Vector3(-33.0, 0, 5.0), Vector3(-33.0, 0, 2.0), Vector3(-6.0, 0, 4.6),
		Vector3(6.4, 0, 3.4), Vector3(-11.5, 0, 3.2), Vector3(31.0, 0, 2.2),
		Vector3(12.0, 0, 5.5), Vector3(-27.5, 0, 12.0)]
	for s in spots:
		var y := gh(s.x, s.z)
		var yaw := r.randf_range(-0.5, 0.5)
		B.prop("cyl", "galv", Batcher.xf(Vector3(s.x, y + 0.85, s.z), Vector3(0.055, 1.7, 0.055)), kcol())
		B.prop("box", "bone", Batcher.xf(Vector3(s.x, y + 1.55, s.z), Vector3(0.62, 0.46, 0.015), yaw), kcol())
		B.detail("box", "amber", Batcher.xf(Vector3(s.x, y + 1.68, s.z + 0.01 * cos(yaw)), Vector3(0.4, 0.10, 0.005), yaw), Color(0.9, 0.9, 0.9))
		B.detail("box", "kitgrey", Batcher.xf(Vector3(s.x, y + 1.45, s.z + 0.01 * cos(yaw)), Vector3(0.44, 0.05, 0.005), yaw), Color(0.6, 0.6, 0.6))
		B.detail("box", "kitgrey", Batcher.xf(Vector3(s.x, y + 1.36, s.z + 0.01 * cos(yaw)), Vector3(0.36, 0.04, 0.005), yaw), Color(0.6, 0.6, 0.6))
