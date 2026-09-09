# ---------------------------------------------------------------------------
# BLINDSIDE -- CAVE DRESSING
#
# THIS FILE IS THE CLIENT LAYER. Floats are allowed. It reads the topology blob
# and the seed and produces geometry, props, materials and scatter.
#
# THE SEAM, stated once: this file MAY NOT WRITE to the CaveTopology object,
# and nothing it decides is ever read back by anything that would be the sim.
# It reads: grid_state, stations (all 16 integer fields), edges, chambers,
# junctions, water_datum_mm, and the seed. That is the whole interface, and it
# is a plain data blob -- it would cross a JSON / FFI boundary unchanged.
#
# Everything is chunked on an 8 m world grid so that the ONE LAMP can pay for
# itself: a chunk more than `visibility_range_end` away is not drawn at all,
# and the lamp only reaches ~20 m.
# ---------------------------------------------------------------------------
class_name CaveDressing
extends RefCounted

const CELL: float = 0.6
const CHUNK_M: float = 8.0
const RING_VERTS: int = 30          # 15 per side
const HALF_RING: int = 15
const SUBSTEPS: int = 3             # rings per station -> ~0.2 m spacing

# how far each family of thing is drawn. The lamp reaches ~20 m on walls and
# ~6 m on the floor (ART-DIRECTION 2.1), and the direction says spend no art
# budget past 15 m (3.6). These numbers are that rule, made mechanical.
const VIS_SHELL: float = 44.0
const VIS_SILHOUETTE: float = 30.0  # sets, arches, pipes, duct, spoil
const VIS_LAMP: float = 19.0        # bolts, trays, plates, cable, kit
const VIS_UNDERFOOT: float = 12.0   # loose stone, ballast, fines, litter

var topo: CaveTopology
var rng: RandomNumberGenerator
var noise: FastNoiseLite
var noise_lo: FastNoiseLite

var mat_rock: ShaderMaterial
var mat_stone: ShaderMaterial
var mat_iron: ShaderMaterial
var mat_steel: ShaderMaterial
var mat_timber: ShaderMaterial
var mat_composite: ShaderMaterial
var mat_alu: ShaderMaterial
var mat_porcelain: ShaderMaterial
var mat_cable: ShaderMaterial
var mat_water: StandardMaterial3D
var mat_pilot: StandardMaterial3D

var kit: Dictionary = {}            # name -> Mesh
var kit_vis: Dictionary = {}        # name -> visibility range

# chunk_key(int) -> { "node": Node3D, "shell": MeshBuilder, "props": {name: [xf,col]} }
var chunks: Dictionary = {}
var chunk_order: PackedInt64Array = PackedInt64Array()

var stat_instances: int = 0
var stat_shell_tris: int = 0
var stat_multimeshes: int = 0
var stat_chunks: int = 0
var lights: Array = []
var path_points: PackedVector3Array = PackedVector3Array()
var path_look: PackedVector3Array = PackedVector3Array()

# ===========================================================================
# small mesh builder: accumulates primitives per material into one ArrayMesh
# ===========================================================================
class Surf:
	var v := PackedVector3Array()
	var n := PackedVector3Array()
	var c := PackedColorArray()
	var u := PackedVector2Array()
	var u2 := PackedVector2Array()
	var idx := PackedInt32Array()

	# NOTE: every Packed* here is a MEMBER, and is only ever mutated from
	# inside this class. That matters: GDScript Packed arrays are
	# copy-on-write, so holding one in a local variable while appending copies
	# the whole array on every call. Doing that per band made generation
	# quadratic and cost 1.3 s for 144 m; this version is the same code
	# without the second reference.
	func append_geo(av: PackedVector3Array, an: PackedVector3Array,
					ac: PackedColorArray, au: PackedVector2Array,
					au2: PackedVector2Array, aidx: PackedInt32Array,
					xf: Transform3D, ident: bool) -> void:
		var base: int = v.size()
		if ident:
			for i in range(av.size()):
				v.push_back(av[i])
				n.push_back(an[i])
		else:
			var nb: Basis = xf.basis.inverse().transposed()
			for i in range(av.size()):
				v.push_back(xf * av[i])
				n.push_back((nb * an[i]).normalized())
		var nc: int = ac.size()
		var nu: int = au.size()
		var nu2: int = au2.size()
		for i in range(av.size()):
			c.push_back(ac[i] if i < nc else Color(1, 1, 1, 1))
			u.push_back(au[i] if i < nu else Vector2.ZERO)
			u2.push_back(au2[i] if i < nu2 else Vector2.ZERO)
		for i in range(aidx.size()):
			idx.push_back(aidx[i] + base)


class MB:
	var surf: Dictionary = {}    # Material -> Surf
	var order: Array = []

	func _bucket(m: Material) -> Surf:
		if not surf.has(m):
			surf[m] = Surf.new()
			order.append(m)
		return surf[m]

	func add_arrays(m: Material, v: PackedVector3Array, n: PackedVector3Array,
					c: PackedColorArray, u: PackedVector2Array, u2: PackedVector2Array,
					idx: PackedInt32Array, xf: Transform3D) -> void:
		_bucket(m).append_geo(v, n, c, u, u2, idx, xf, xf == Transform3D.IDENTITY)

	func add_prim(m: Material, prim: PrimitiveMesh, xf: Transform3D, col: Color) -> void:
		var a: Array = prim.get_mesh_arrays()
		var v: PackedVector3Array = a[Mesh.ARRAY_VERTEX]
		var n: PackedVector3Array = a[Mesh.ARRAY_NORMAL]
		var idx: PackedInt32Array = a[Mesh.ARRAY_INDEX]
		var c := PackedColorArray()
		c.resize(v.size())
		c.fill(col)
		_bucket(m).append_geo(v, n, c, PackedVector2Array(), PackedVector2Array(), idx, xf, false)

	func tri_count() -> int:
		var t: int = 0
		for m in order:
			t += (surf[m] as Surf).idx.size() / 3
		return t

	func commit() -> ArrayMesh:
		var am := ArrayMesh.new()
		for m in order:
			var b: Surf = surf[m]
			if b.idx.size() == 0:
				continue
			var arr := []
			arr.resize(Mesh.ARRAY_MAX)
			arr[Mesh.ARRAY_VERTEX] = b.v
			arr[Mesh.ARRAY_NORMAL] = b.n
			arr[Mesh.ARRAY_COLOR] = b.c
			arr[Mesh.ARRAY_TEX_UV] = b.u
			arr[Mesh.ARRAY_TEX_UV2] = b.u2
			arr[Mesh.ARRAY_INDEX] = b.idx
			am.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arr)
			am.surface_set_material(am.get_surface_count() - 1, m)
		return am

# ===========================================================================
var stage: Callable = func(_m: String) -> void: pass

func build(p_topo: CaveTopology, p_seed: int, root: Node3D) -> void:
	topo = p_topo
	rng = RandomNumberGenerator.new()
	rng.seed = p_seed * 6364136223846793005 + 1442695040888963407
	noise = FastNoiseLite.new()
	noise.seed = p_seed
	noise.noise_type = FastNoiseLite.TYPE_SIMPLEX_SMOOTH
	noise.frequency = 0.55
	noise.fractal_octaves = 4
	noise_lo = FastNoiseLite.new()
	noise_lo.seed = p_seed + 977
	noise_lo.noise_type = FastNoiseLite.TYPE_SIMPLEX_SMOOTH
	noise_lo.frequency = 0.11
	noise_lo.fractal_octaves = 2

	_make_materials()
	_make_kit()
	stage.call("kit built")
	_sweep_edges()
	stage.call("swept")
	_build_chambers()
	stage.call("chambers")
	_place_props()
	stage.call("props")
	_emit(root)
	stage.call("emitted")
	_build_camera_path()

# --- materials -------------------------------------------------------------
func _make_materials() -> void:
	mat_rock = ShaderMaterial.new()
	mat_rock.shader = load("res://rock.gdshader")
	mat_stone = ShaderMaterial.new()
	mat_stone.shader = load("res://stone.gdshader")

	# One shader, six parameter sets. Vertex colours carry the part colours, so
	# a rail is rusted web plus bright head inside a single draw call.
	var ksh: Shader = load("res://kit.gdshader")
	mat_iron = _kit_mat(ksh, 0.55, 0.68, 1.00, 0.35, 0.0)      # cast iron
	mat_steel = _kit_mat(ksh, 1.00, 0.17, 0.15, 0.40, 0.0)     # rubbed steel
	mat_timber = _kit_mat(ksh, 0.00, 0.90, 0.35, 0.45, 1.0)    # waterlogged
	mat_composite = _kit_mat(ksh, 0.00, 0.36, 0.00, 0.10, 0.0) # BROUGHT
	mat_alu = _kit_mat(ksh, 0.92, 0.28, 0.00, 0.10, 0.0)       # BROUGHT
	mat_porcelain = _kit_mat(ksh, 0.00, 0.10, 0.03, 0.20, 0.0) # the Bus
	mat_cable = _kit_mat(ksh, 0.00, 0.58, 0.00, 0.25, 0.0)

	mat_water = StandardMaterial3D.new()
	mat_water.albedo_color = Color(0.020, 0.028, 0.032, 0.86)
	mat_water.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat_water.metallic = 0.15
	mat_water.roughness = 0.03
	mat_water.metallic_specular = 0.9
	mat_water.cull_mode = BaseMaterial3D.CULL_DISABLED

	# WARM_DIM amber. Never cyan (belief), never red (lethal). ART-DIRECTION 2.5
	mat_pilot = StandardMaterial3D.new()
	mat_pilot.albedo_color = Color(1.0, 0.72, 0.36)
	mat_pilot.emission_enabled = true
	mat_pilot.emission = Color(1.0, 0.70, 0.34)
	mat_pilot.emission_energy_multiplier = 2.6
	mat_pilot.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED

func _kit_mat(sh: Shader, metal: float, rough: float, rust: float,
			  wet: float, grain: float) -> ShaderMaterial:
	var m := ShaderMaterial.new()
	m.shader = sh
	m.set_shader_parameter("metal", metal)
	m.set_shader_parameter("rough", rough)
	m.set_shader_parameter("rust", rust)
	m.set_shader_parameter("wet_amt", wet)
	m.set_shader_parameter("grain", grain)
	return m

# --- the kit of parts ------------------------------------------------------
# Every prop below is boxes, cylinders, prisms and spheres put together in
# code. No modeller, no import. Each becomes one Mesh used by a MultiMesh.
const C_IRON := Color(0.058, 0.030, 0.017)
const C_IRON_L := Color(0.115, 0.062, 0.034)
const C_STEEL := Color(0.52, 0.50, 0.48)
const C_RAILHEAD := Color(0.62, 0.60, 0.58)
const C_TIMBER := Color(0.072, 0.053, 0.036)
const C_TIMBER_L := Color(0.108, 0.082, 0.056)
const C_COMPOSITE := Color(0.185, 0.196, 0.180)  # the brought: cool grey-green.
# Still three times the albedo of the cast iron next to it, which is the whole
# point of the register, but not white when the lamp is two metres off it.
const C_ALU := Color(0.42, 0.43, 0.44)
const C_PORCELAIN := Color(0.62, 0.61, 0.58)
const C_CABLE := Color(0.035, 0.033, 0.031)
const C_STONE := Color(0.30, 0.24, 0.17)

func _box(sx: float, sy: float, sz: float) -> BoxMesh:
	var b := BoxMesh.new()
	b.size = Vector3(sx, sy, sz)
	return b

func _cyl(r: float, h: float, seg: int = 10) -> CylinderMesh:
	var c := CylinderMesh.new()
	c.top_radius = r
	c.bottom_radius = r
	c.height = h
	c.radial_segments = seg
	c.rings = 0
	return c

func _cone(r: float, h: float, seg: int = 10) -> CylinderMesh:
	var c := CylinderMesh.new()
	c.top_radius = 0.001
	c.bottom_radius = r
	c.height = h
	c.radial_segments = seg
	c.rings = 0
	return c

func _sph(r: float, seg: int = 8) -> SphereMesh:
	var s := SphereMesh.new()
	s.radius = r
	s.height = r * 2.0
	s.radial_segments = seg
	s.rings = maxi(3, seg / 2)
	return s

func _xf(p: Vector3, rot: Vector3 = Vector3.ZERO, sc: Vector3 = Vector3.ONE) -> Transform3D:
	var b := Basis.from_euler(rot).scaled(sc)
	return Transform3D(b, p)

# a basis whose LOCAL +Z points along `dir`. Every wall-mounted kit part is
# modelled with its outward direction along +Z.
func _face(dir: Vector3) -> Basis:
	var d: Vector3 = dir.normalized()
	var up: Vector3 = Vector3.UP
	if absf(d.dot(up)) > 0.98:
		up = Vector3.FORWARD
	return Basis.looking_at(-d, up)

# an angular stone: a box distorted per-vertex. Reads as broken rock, not a ball.
func _stone_mesh(sd: int, r: float, flat: float = 1.0) -> ArrayMesh:
	var lr := RandomNumberGenerator.new()
	lr.seed = sd
	var s := _sph(r, 7)
	var a: Array = s.get_mesh_arrays()
	var v: PackedVector3Array = a[Mesh.ARRAY_VERTEX]
	for i in range(v.size()):
		var d: Vector3 = v[i].normalized()
		# quantise the direction so facets appear: broken rock has flats
		var q := Vector3(round(d.x * 2.0) / 2.0, round(d.y * 2.0) / 2.0, round(d.z * 2.0) / 2.0)
		d = d.lerp(q.normalized() if q.length() > 0.01 else d, 0.55)
		var k: float = r * (0.62 + lr.randf() * 0.55)
		v[i] = Vector3(d.x * k, d.y * k * flat, d.z * k)
	a[Mesh.ARRAY_VERTEX] = v
	a[Mesh.ARRAY_NORMAL] = _recalc_normals(v, a[Mesh.ARRAY_INDEX])
	var col := PackedColorArray()
	col.resize(v.size())
	for i in range(v.size()):
		col[i] = C_STONE
	a[Mesh.ARRAY_COLOR] = col
	a[Mesh.ARRAY_TEX_UV] = PackedVector2Array()
	a[Mesh.ARRAY_TEX_UV2] = PackedVector2Array()
	a.resize(Mesh.ARRAY_MAX)
	var am := ArrayMesh.new()
	var arr := []
	arr.resize(Mesh.ARRAY_MAX)
	arr[Mesh.ARRAY_VERTEX] = a[Mesh.ARRAY_VERTEX]
	arr[Mesh.ARRAY_NORMAL] = a[Mesh.ARRAY_NORMAL]
	arr[Mesh.ARRAY_COLOR] = col
	arr[Mesh.ARRAY_INDEX] = a[Mesh.ARRAY_INDEX]
	am.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arr)
	am.surface_set_material(0, mat_stone)
	return am

func _recalc_normals(v: PackedVector3Array, idx: PackedInt32Array) -> PackedVector3Array:
	var n := PackedVector3Array()
	n.resize(v.size())
	for i in range(v.size()):
		n[i] = Vector3.ZERO
	var i2: int = 0
	while i2 < idx.size():
		var a: int = idx[i2]
		var b: int = idx[i2 + 1]
		var c: int = idx[i2 + 2]
		var fn: Vector3 = (v[b] - v[a]).cross(v[c] - v[a])
		n[a] += fn
		n[b] += fn
		n[c] += fn
		i2 += 3
	for i in range(n.size()):
		n[i] = n[i].normalized() if n[i].length() > 0.0001 else Vector3.UP
	return n

func _reg(name: String, mesh: Mesh, vis: float) -> void:
	kit[name] = mesh
	kit_vis[name] = vis

func _make_kit() -> void:
	var b: MB

	# --- underfoot ---------------------------------------------------------
	for i in range(4):
		_reg("stone%d" % i, _stone_mesh(101 + i, 0.075 + i * 0.035, 0.75), VIS_UNDERFOOT)
	for i in range(3):
		_reg("ballast%d" % i, _stone_mesh(211 + i, 0.038 + i * 0.012, 0.8), VIS_UNDERFOOT)
	for i in range(3):
		_reg("block%d" % i, _stone_mesh(311 + i, 0.30 + i * 0.24, 0.72), VIS_SILHOUETTE)
	# fines / silt fan: a flat disc
	b = MB.new()
	b.add_prim(mat_stone, _cyl(0.30, 0.012, 9), _xf(Vector3.ZERO), Color(0.40, 0.35, 0.27))
	_reg("fines", b.commit(), VIS_UNDERFOOT)
	# litter: a tiny bent scrap
	b = MB.new()
	b.add_prim(mat_iron, _box(0.055, 0.008, 0.022), _xf(Vector3.ZERO), C_IRON_L)
	b.add_prim(mat_iron, _box(0.020, 0.008, 0.030), _xf(Vector3(0.03, 0.004, 0.01), Vector3(0, 0.6, 0.4)), C_IRON_L)
	_reg("litter", b.commit(), VIS_UNDERFOOT)
	# puddle
	b = MB.new()
	b.add_prim(mat_water, _cyl(0.42, 0.004, 12), _xf(Vector3.ZERO), Color(1, 1, 1))
	_reg("puddle", b.commit(), VIS_LAMP)

	# --- the permanent way -------------------------------------------------
	# rail: foot, web, head. The head is the only mirror-bright thing in the
	# cave (ART-DIRECTION 5.6). 0.6 m section.
	b = MB.new()
	b.add_prim(mat_iron, _box(0.062, 0.012, 0.62), _xf(Vector3(0, 0.006, 0)), C_IRON)
	b.add_prim(mat_iron, _box(0.014, 0.048, 0.62), _xf(Vector3(0, 0.036, 0)), C_IRON)
	b.add_prim(mat_steel, _box(0.040, 0.016, 0.62), _xf(Vector3(0, 0.068, 0)), C_RAILHEAD)
	_reg("rail", b.commit(), VIS_SILHOUETTE)
	# sleeper
	b = MB.new()
	b.add_prim(mat_timber, _box(0.90, 0.075, 0.13), _xf(Vector3.ZERO), C_TIMBER)
	_reg("sleeper", b.commit(), VIS_LAMP)

	# --- ground support ----------------------------------------------------
	# timber set: two posts and a cap, on the 1.2 m module
	b = MB.new()
	b.add_prim(mat_timber, _box(0.18, 1.95, 0.16), _xf(Vector3(-1.18, 0.97, 0), Vector3(0, 0, 0.045)), C_TIMBER)
	b.add_prim(mat_timber, _box(0.18, 1.95, 0.16), _xf(Vector3(1.18, 0.97, 0), Vector3(0, 0, -0.045)), C_TIMBER)
	b.add_prim(mat_timber, _box(2.62, 0.20, 0.17), _xf(Vector3(0, 2.02, 0)), C_TIMBER_L)
	b.add_prim(mat_timber, _box(0.30, 0.10, 0.18), _xf(Vector3(-1.02, 1.88, 0), Vector3(0, 0, 0.5)), C_TIMBER)
	b.add_prim(mat_timber, _box(0.30, 0.10, 0.18), _xf(Vector3(1.02, 1.88, 0), Vector3(0, 0, -0.5)), C_TIMBER)
	_reg("set", b.commit(), VIS_SILHOUETTE)
	# the one that failed while its neighbours stand (ART-DIRECTION 3.5)
	b = MB.new()
	b.add_prim(mat_timber, _box(0.18, 1.10, 0.16), _xf(Vector3(-1.18, 0.55, 0), Vector3(0, 0, 0.10)), C_TIMBER)
	b.add_prim(mat_timber, _box(0.18, 0.55, 0.16), _xf(Vector3(-0.92, 1.30, 0.05), Vector3(0.2, 0, 0.75)), C_TIMBER)
	b.add_prim(mat_timber, _box(0.18, 1.95, 0.16), _xf(Vector3(1.18, 0.97, 0), Vector3(0, 0, -0.045)), C_TIMBER)
	b.add_prim(mat_timber, _box(2.62, 0.20, 0.17), _xf(Vector3(-0.30, 1.55, 0.02), Vector3(0.05, 0, 0.34)), C_TIMBER_L)
	_reg("setfail", b.commit(), VIS_SILHOUETTE)
	# steel arch set: five segments of a semicircle
	b = MB.new()
	for i in range(7):
		var a: float = PI * float(i) / 6.0
		var px: float = cos(a) * 1.30
		var py: float = 1.05 + sin(a) * 1.30
		b.add_prim(mat_iron, _box(0.26, 0.09, 0.10), _xf(Vector3(px, py, 0), Vector3(0, 0, a + PI * 0.5)), C_IRON_L)
	b.add_prim(mat_iron, _box(0.10, 1.10, 0.10), _xf(Vector3(-1.30, 0.52, 0)), C_IRON_L)
	b.add_prim(mat_iron, _box(0.10, 1.10, 0.10), _xf(Vector3(1.30, 0.52, 0)), C_IRON_L)
	_reg("arch", b.commit(), VIS_SILHOUETTE)
	# rock bolt: plate, nut, stub
	b = MB.new()
	b.add_prim(mat_iron, _box(0.150, 0.150, 0.012), _xf(Vector3(0, 0, 0.006)), C_IRON_L)
	b.add_prim(mat_iron, _cyl(0.026, 0.030, 6), _xf(Vector3(0, 0, 0.026), Vector3(PI * 0.5, 0, 0)), C_STEEL * 0.5)
	b.add_prim(mat_iron, _cyl(0.011, 0.055, 5), _xf(Vector3(0, 0, 0.040), Vector3(PI * 0.5, 0, 0)), C_STEEL * 0.6)
	_reg("bolt", b.commit(), VIS_LAMP)
	# ground support mesh panel: a lattice of thin bars, bad ground only
	b = MB.new()
	for i in range(7):
		var t: float = -0.6 + i * 0.2
		b.add_prim(mat_iron, _box(0.010, 1.30, 0.010), _xf(Vector3(t, 0, 0)), C_IRON_L)
		b.add_prim(mat_iron, _box(1.30, 0.010, 0.010), _xf(Vector3(0, t, 0.006)), C_IRON_L)
	_reg("meshpanel", b.commit(), VIS_LAMP)

	# --- services, the inherited ------------------------------------------
	# cast pipe with a flange every section
	b = MB.new()
	b.add_prim(mat_iron, _cyl(0.085, 0.62, 9), _xf(Vector3.ZERO, Vector3(PI * 0.5, 0, 0)), C_IRON)
	b.add_prim(mat_iron, _cyl(0.115, 0.030, 9), _xf(Vector3(0, 0, 0.30), Vector3(PI * 0.5, 0, 0)), C_IRON_L)
	b.add_prim(mat_iron, _box(0.06, 0.20, 0.05), _xf(Vector3(0, 0.13, 0.0)), C_IRON_L)
	_reg("pipe", b.commit(), VIS_SILHOUETTE)
	# rusted wall bracket -- what the brought register gets clipped to
	b = MB.new()
	b.add_prim(mat_iron, _box(0.05, 0.09, 0.24), _xf(Vector3(0, 0, 0.12)), C_IRON_L)
	b.add_prim(mat_iron, _box(0.12, 0.12, 0.012), _xf(Vector3(0, 0, 0.006)), C_IRON_L)
	_reg("bracket", b.commit(), VIS_LAMP)
	# timber launder on posts
	b = MB.new()
	b.add_prim(mat_timber, _box(0.34, 0.030, 0.62), _xf(Vector3(0, 0, 0)), C_TIMBER)
	b.add_prim(mat_timber, _box(0.030, 0.22, 0.62), _xf(Vector3(-0.17, 0.11, 0)), C_TIMBER)
	b.add_prim(mat_timber, _box(0.030, 0.22, 0.62), _xf(Vector3(0.17, 0.11, 0)), C_TIMBER)
	b.add_prim(mat_timber, _box(0.09, 0.80, 0.09), _xf(Vector3(0, -0.40, 0.2)), C_TIMBER)
	_reg("launder", b.commit(), VIS_SILHOUETTE)
	# porcelain insulator on its pin -- the Bus
	b = MB.new()
	b.add_prim(mat_porcelain, _cyl(0.062, 0.045, 10), _xf(Vector3(0, -0.02, 0)), C_PORCELAIN)
	b.add_prim(mat_porcelain, _cyl(0.045, 0.050, 10), _xf(Vector3(0, 0.035, 0)), C_PORCELAIN)
	b.add_prim(mat_porcelain, _cyl(0.030, 0.040, 8), _xf(Vector3(0, 0.078, 0)), C_PORCELAIN)
	b.add_prim(mat_iron, _cyl(0.014, 0.13, 6), _xf(Vector3(0, -0.10, 0)), C_IRON_L)
	b.add_prim(mat_iron, _box(0.13, 0.012, 0.09), _xf(Vector3(0, -0.168, 0)), C_IRON_L)
	_reg("insulator", b.commit(), VIS_LAMP)
	b = MB.new()
	b.add_prim(mat_iron, _cyl(0.011, 0.62, 5), _xf(Vector3.ZERO, Vector3(PI * 0.5, 0, 0)), Color(0.16, 0.10, 0.06))
	_reg("bus", b.commit(), VIS_LAMP)
	# cast survey index plate at 1.40 m -- no emission, ART-DIRECTION 6.5
	b = MB.new()
	b.add_prim(mat_iron, _box(0.160, 0.100, 0.010), _xf(Vector3.ZERO), C_IRON_L)
	b.add_prim(mat_iron, _box(0.140, 0.080, 0.004), _xf(Vector3(0, 0, 0.007)), C_IRON)
	for i in range(4):
		b.add_prim(mat_iron, _box(0.016, 0.036, 0.006), _xf(Vector3(-0.048 + i * 0.032, 0, 0.011)), C_IRON_L * 1.6)
	_reg("plate", b.commit(), VIS_LAMP)
	# an old iron drum, left where it fell
	b = MB.new()
	b.add_prim(mat_iron, _cyl(0.28, 0.86, 10), _xf(Vector3(0, 0.43, 0)), C_IRON)
	b.add_prim(mat_iron, _cyl(0.295, 0.035, 10), _xf(Vector3(0, 0.62, 0)), C_IRON_L)
	b.add_prim(mat_iron, _cyl(0.295, 0.035, 10), _xf(Vector3(0, 0.24, 0)), C_IRON_L)
	_reg("drum", b.commit(), VIS_LAMP)
	# a coil of old rope / chain heap
	b = MB.new()
	for i in range(9):
		var a2: float = float(i) * 0.7
		b.add_prim(mat_iron, _cyl(0.022, 0.30, 5),
			_xf(Vector3(cos(a2) * 0.16, 0.03 + (i % 3) * 0.02, sin(a2) * 0.16), Vector3(PI * 0.5, a2, 0)), C_IRON)
	_reg("coil", b.commit(), VIS_LAMP)
	# spoil heap
	b = MB.new()
	b.add_prim(mat_stone, _cone(0.95, 0.62, 9), _xf(Vector3(0, 0.31, 0), Vector3.ZERO, Vector3(1.0, 1.0, 1.7)), Color(0.28, 0.22, 0.16))
	_reg("spoil", b.commit(), VIS_SILHOUETTE)
	# roof pendant: a hanging spike of rock
	b = MB.new()
	b.add_prim(mat_stone, _cone(0.24, 0.85, 7), _xf(Vector3(0, -0.42, 0), Vector3(PI, 0, 0)), Color(0.30, 0.24, 0.17))
	_reg("pendant", b.commit(), VIS_SILHOUETTE)
	# flowstone boss on the wall, shallow ground
	b = MB.new()
	b.add_prim(mat_stone, _sph(0.22, 7), _xf(Vector3.ZERO, Vector3.ZERO, Vector3(0.6, 1.9, 0.6)), Color(0.44, 0.40, 0.33))
	_reg("flowstone", b.commit(), VIS_LAMP)

	# --- services, the brought --------------------------------------------
	# composite cable tray, clipped over the old bracket line. Clean edges.
	b = MB.new()
	b.add_prim(mat_composite, _box(0.20, 0.012, 0.62), _xf(Vector3(0, 0, 0)), C_COMPOSITE)
	b.add_prim(mat_composite, _box(0.012, 0.075, 0.62), _xf(Vector3(-0.10, 0.037, 0)), C_COMPOSITE)
	b.add_prim(mat_composite, _box(0.012, 0.075, 0.62), _xf(Vector3(0.10, 0.037, 0)), C_COMPOSITE)
	b.add_prim(mat_alu, _box(0.24, 0.020, 0.030), _xf(Vector3(0, -0.014, 0.24)), C_ALU)
	b.add_prim(mat_cable, _cyl(0.016, 0.62, 6), _xf(Vector3(-0.05, 0.024, 0), Vector3(PI * 0.5, 0, 0)), C_CABLE)
	b.add_prim(mat_cable, _cyl(0.016, 0.62, 6), _xf(Vector3(0.0, 0.024, 0), Vector3(PI * 0.5, 0, 0)), C_CABLE)
	b.add_prim(mat_cable, _cyl(0.012, 0.62, 6), _xf(Vector3(0.05, 0.022, 0), Vector3(PI * 0.5, 0, 0)), Color(0.10, 0.10, 0.11))
	_reg("tray", b.commit(), VIS_LAMP)
	# extruded ventilation duct with a printed hanger
	b = MB.new()
	b.add_prim(mat_composite, _cyl(0.20, 0.62, 12), _xf(Vector3.ZERO, Vector3(PI * 0.5, 0, 0)), C_COMPOSITE * 1.15)
	b.add_prim(mat_composite, _cyl(0.215, 0.020, 12), _xf(Vector3(0, 0, 0.29), Vector3(PI * 0.5, 0, 0)), C_COMPOSITE * 0.85)
	b.add_prim(mat_alu, _box(0.014, 0.26, 0.020), _xf(Vector3(-0.19, 0.16, 0.20)), C_ALU)
	b.add_prim(mat_alu, _box(0.014, 0.26, 0.020), _xf(Vector3(0.19, 0.16, 0.20)), C_ALU)
	_reg("duct", b.commit(), VIS_SILHOUETTE)
	# the player's beacon: a machined tripod, a labelled body, one warm pilot
	b = MB.new()
	for i in range(3):
		var a3: float = float(i) * TAU / 3.0
		b.add_prim(mat_alu, _box(0.022, 0.30, 0.022),
			_xf(Vector3(cos(a3) * 0.10, 0.14, sin(a3) * 0.10), Vector3(cos(a3) * 0.35, 0, -sin(a3) * 0.35)), C_ALU)
	b.add_prim(mat_composite, _cyl(0.085, 0.26, 10), _xf(Vector3(0, 0.40, 0)), C_COMPOSITE * 1.3)
	b.add_prim(mat_alu, _cyl(0.092, 0.020, 10), _xf(Vector3(0, 0.53, 0)), C_ALU)
	b.add_prim(mat_composite, _box(0.10, 0.055, 0.006), _xf(Vector3(0, 0.44, 0.086)), Color(0.72, 0.71, 0.68))
	b.add_prim(mat_alu, _cyl(0.010, 0.22, 5), _xf(Vector3(0, 0.64, 0)), C_ALU)
	b.add_prim(mat_pilot, _sph(0.028, 8), _xf(Vector3(0, 0.56, 0)), Color(1, 1, 1))
	_reg("beacon", b.commit(), VIS_SILHOUETTE)
	# a modular case, stacked or dropped: the brought register on the floor
	b = MB.new()
	b.add_prim(mat_composite, _box(0.62, 0.34, 0.40), _xf(Vector3(0, 0.17, 0)), C_COMPOSITE)
	b.add_prim(mat_alu, _box(0.64, 0.020, 0.42), _xf(Vector3(0, 0.345, 0)), C_ALU)
	b.add_prim(mat_alu, _box(0.030, 0.34, 0.030), _xf(Vector3(-0.31, 0.17, 0.21)), C_ALU)
	b.add_prim(mat_alu, _box(0.030, 0.34, 0.030), _xf(Vector3(0.31, 0.17, 0.21)), C_ALU)
	b.add_prim(mat_composite, _box(0.16, 0.09, 0.006), _xf(Vector3(0.1, 0.22, 0.203)), Color(0.75, 0.74, 0.70))
	_reg("case", b.commit(), VIS_LAMP)
	# a printed bracket bolted into old stone, holding a small instrument
	b = MB.new()
	b.add_prim(mat_alu, _box(0.13, 0.13, 0.012), _xf(Vector3(0, 0, 0.006)), C_ALU)
	b.add_prim(mat_alu, _box(0.030, 0.030, 0.16), _xf(Vector3(0, 0, 0.09)), C_ALU)
	b.add_prim(mat_composite, _box(0.13, 0.085, 0.075), _xf(Vector3(0, 0, 0.20)), C_COMPOSITE * 1.2)
	b.add_prim(mat_alu, _cyl(0.012, 0.10, 5), _xf(Vector3(0, 0.07, 0.20), Vector3(0, 0, 0)), C_ALU)
	_reg("instrument", b.commit(), VIS_LAMP)

	# --- machine ground plant ---------------------------------------------
	b = MB.new()
	b.add_prim(mat_iron, _cyl(0.52, 2.30, 12), _xf(Vector3(0, 0.75, 0), Vector3(0, 0, PI * 0.5)), C_IRON)
	b.add_prim(mat_iron, _cyl(0.60, 0.10, 12), _xf(Vector3(-1.10, 0.75, 0), Vector3(0, 0, PI * 0.5)), C_IRON_L)
	b.add_prim(mat_iron, _cyl(0.60, 0.10, 12), _xf(Vector3(1.10, 0.75, 0), Vector3(0, 0, PI * 0.5)), C_IRON_L)
	b.add_prim(mat_iron, _cyl(1.05, 0.10, 16), _xf(Vector3(1.45, 0.85, 0), Vector3(0, 0, PI * 0.5)), C_IRON_L)
	for i in range(8):
		var a4: float = float(i) * TAU / 8.0
		b.add_prim(mat_iron, _box(0.07, 0.95, 0.07), _xf(Vector3(1.45, 0.85 + sin(a4) * 0.47, cos(a4) * 0.47), Vector3(a4, 0, PI * 0.5)), C_IRON)
	b.add_prim(mat_iron, _box(2.70, 0.34, 1.30), _xf(Vector3(0, 0.17, 0)), C_IRON)
	b.add_prim(mat_iron, _cyl(0.16, 1.90, 8), _xf(Vector3(-0.9, 1.70, 0.2)), C_IRON)
	b.add_prim(mat_iron, _cyl(0.16, 1.20, 8), _xf(Vector3(-0.9, 2.60, 0.8), Vector3(PI * 0.5, 0, 0)), C_IRON)
	_reg("pump", b.commit(), VIS_SILHOUETTE)

	# a derailed mine tub: the single best silhouette object the mine owns
	b = MB.new()
	b.add_prim(mat_iron, _box(0.66, 0.46, 0.92), _xf(Vector3(0, 0.40, 0)), C_IRON)
	b.add_prim(mat_iron, _box(0.70, 0.05, 0.96), _xf(Vector3(0, 0.64, 0)), C_IRON_L)
	b.add_prim(mat_iron, _box(0.74, 0.10, 0.14), _xf(Vector3(0, 0.16, 0.36)), C_IRON_L)
	for wsn in [-1.0, 1.0]:
		for wsd in [-1.0, 1.0]:
			b.add_prim(mat_steel, _cyl(0.115, 0.05, 9),
				_xf(Vector3(wsn * 0.30, 0.115, wsd * 0.33), Vector3(0, 0, PI * 0.5)), C_STEEL * 0.7)
	_reg("tub", b.commit(), VIS_SILHOUETTE)
	# lagging: the boards packed in behind a set, the thing that says the
	# ground here would not stand on its own
	b = MB.new()
	for lg in range(5):
		b.add_prim(mat_timber, _box(0.16, 0.045, 1.05),
			_xf(Vector3(0, 0.06 + lg * 0.20, 0), Vector3(0, 0, PI * 0.5 + (float(lg) - 2.0) * 0.05)), C_TIMBER)
	_reg("lagging", b.commit(), VIS_LAMP)
	# fresh spall: thin angular flakes off the back, on ledges and underfoot
	for i in range(3):
		_reg("spall%d" % i, _stone_mesh(511 + i, 0.16 + i * 0.07, 0.28), VIS_LAMP)
	# grit: the smallest thing a machine stands on
	for i in range(2):
		_reg("grit%d" % i, _stone_mesh(611 + i, 0.026 + i * 0.010, 0.85), VIS_UNDERFOOT)
	# BROUGHT: a charging mast, clean, powered, out of place
	b = MB.new()
	b.add_prim(mat_alu, _box(0.34, 0.030, 0.34), _xf(Vector3(0, 0.015, 0)), C_ALU)
	b.add_prim(mat_alu, _cyl(0.036, 1.35, 8), _xf(Vector3(0, 0.69, 0)), C_ALU)
	b.add_prim(mat_composite, _box(0.26, 0.32, 0.14), _xf(Vector3(0, 1.10, 0.09)), C_COMPOSITE * 1.25)
	b.add_prim(mat_composite, _box(0.18, 0.10, 0.008), _xf(Vector3(0, 1.18, 0.165)), Color(0.76, 0.75, 0.71))
	b.add_prim(mat_cable, _cyl(0.020, 0.55, 6), _xf(Vector3(0.10, 0.30, 0.16), Vector3(0.5, 0, 0.3)), C_CABLE)
	b.add_prim(mat_pilot, _box(0.10, 0.022, 0.006), _xf(Vector3(0, 1.28, 0.165)), Color(1, 1, 1))
	_reg("mast", b.commit(), VIS_SILHOUETTE)

	# a cable catenary link (one short segment, many instanced along a curve)
	b = MB.new()
	b.add_prim(mat_cable, _cyl(0.014, 1.0, 5), _xf(Vector3.ZERO, Vector3(PI * 0.5, 0, 0)), C_CABLE)
	_reg("cablelink", b.commit(), VIS_LAMP)

# ===========================================================================
# chunking
# ===========================================================================
func _chunk_key(p: Vector3) -> int:
	var cx: int = int(floor(p.x / CHUNK_M))
	var cz: int = int(floor(p.z / CHUNK_M))
	return (cx + 4096) * 8192 + (cz + 4096)

func _chunk(p: Vector3) -> Dictionary:
	var k: int = _chunk_key(p)
	if not chunks.has(k):
		var c := {"shell": MB.new(), "props": {}, "key": k}
		chunks[k] = c
		chunk_order.push_back(k)
	return chunks[k]

func _prop(p: Vector3, name: String, xf: Transform3D, _col: Color = Color(1, 1, 1)) -> void:
	var c: Dictionary = _chunk(p)
	var pr: Dictionary = c["props"]
	if not pr.has(name):
		pr[name] = []
	(pr[name] as Array).append(xf)
	stat_instances += 1

# ===========================================================================
# station geometry helpers
# ===========================================================================
func _st(i: int) -> PackedInt32Array:
	return topo.stations[i]

func _st_pos(i: int) -> Vector3:
	var s: PackedInt32Array = topo.stations[i]
	return Vector3(float(s[CaveTopology.S_X]) * CELL,
				   float(s[CaveTopology.S_FLOOR_MM]) * 0.001,
				   float(s[CaveTopology.S_Y]) * CELL)

func _hw(s: PackedInt32Array) -> float:
	var base: float = float(CaveTopology.WC_HALFWIDTH_MM[s[CaveTopology.S_WIDTH]]) * 0.001
	if s[CaveTopology.S_KIND] == CaveTopology.K_CHAMBER:
		base *= 1.5
	return base

func _ht(s: PackedInt32Array) -> float:
	var base: float = float(CaveTopology.WC_HEIGHT_MM[s[CaveTopology.S_WIDTH]]) * 0.001
	if s[CaveTopology.S_KIND] == CaveTopology.K_CHAMBER:
		base *= 1.35
	return base

# The profile. Two registers interpolated on `worked` (ART-DIRECTION 3.4).
#   worked 0 : natural. Rounded, no flat surface, no straight line.
#   worked 1 : the horseshoe drive. Vertical legs to 1.2 m, semicircular arch,
#              flat trammed floor, a 300 x 90 gutter down one side.
# s runs 0 (floor centre) -> 1 (crown) on ONE side; the ring mirrors it.
func _half_profile(s: float, worked: float, hw: float, ht: float, side: float,
				   gutter: bool) -> Vector2:
	# natural
	var nu: float
	var nv: float
	if s < 0.22:
		nu = (s / 0.22) * hw * 0.92
		nv = 0.0
	else:
		var a: float = ((s - 0.22) / 0.78) * (PI * 0.5)
		var bulge: float = 1.0 + 0.22 * sin(a * 2.0)
		nu = hw * 0.92 * cos(a) * bulge
		nv = ht * sin(a) * (0.92 + 0.10 * cos(a * 3.0))
	# horseshoe
	var R: float = minf(hw, ht * 0.62)
	var leg: float = maxf(0.18, ht - R)
	var wu: float
	var wv: float
	if s < 0.28:
		wu = (s / 0.28) * hw
		wv = 0.0
		if gutter and side > 0.0:
			# 300 x 90 mm drainage gutter down one side
			var g: float = (wu - (hw - 0.34)) / 0.30
			if g > 0.0 and g < 1.0:
				wv = -0.09 * sin(g * PI)
	elif s < 0.55:
		wu = hw
		wv = ((s - 0.28) / 0.27) * leg
	else:
		var a2: float = ((s - 0.55) / 0.45) * (PI * 0.5)
		wu = R * cos(a2) + (hw - R)
		wv = leg + R * sin(a2)
	return Vector2(lerp(nu, wu, worked) * side, lerp(nv, wv, worked))

# ===========================================================================
# the shell
# ===========================================================================
func _sweep_edges() -> void:
	for e in range(topo.edges.size()):
		_sweep_edge(topo.edges[e])

func _sweep_edge(ids: PackedInt32Array) -> void:
	var n: int = ids.size()
	if n < 2:
		return
	var prev_ring: Array = []
	var prev_data: Array = []
	var prev_centre: Vector3 = Vector3.ZERO
	var axial: float = 0.0
	for i in range(n):
		for sub in range(SUBSTEPS):
			var t: float = float(sub) / float(SUBSTEPS)
			var i0: int = maxi(0, i - 1)
			var i1: int = i
			var i2: int = mini(n - 1, i + 1)
			var i3: int = mini(n - 1, i + 2)
			var p: Vector3 = _catmull(_st_pos(ids[i0]), _st_pos(ids[i1]), _st_pos(ids[i2]), _st_pos(ids[i3]), t)
			var pn: Vector3 = _catmull(_st_pos(ids[i0]), _st_pos(ids[i1]), _st_pos(ids[i2]), _st_pos(ids[i3]), t + 0.02)
			var tangent: Vector3 = (pn - p).normalized()
			if tangent.length() < 0.5:
				tangent = Vector3(1, 0, 0)
			var right: Vector3 = tangent.cross(Vector3.UP).normalized()
			if right.length() < 0.5:
				right = Vector3(0, 0, 1)
			var sa: PackedInt32Array = _st(ids[i1])
			var sb: PackedInt32Array = _st(ids[i2])
			var hw: float = lerp(_hw(sa), _hw(sb), t)
			var ht: float = lerp(_ht(sa), _ht(sb), t)
			var worked: float = lerp(float(sa[CaveTopology.S_WORKED]), float(sb[CaveTopology.S_WORKED]), t) / 255.0
			var wet: float = lerp(float(sa[CaveTopology.S_WET]), float(sb[CaveTopology.S_WET]), t) / 255.0
			var dark: float = float(sa[CaveTopology.S_DEPTH]) / float(maxi(1, topo.edges[0].size()))
			dark = clampf(dark, 0.0, 1.0)
			var frac01: float = clampf((float(sa[CaveTopology.S_FRACTURE]) - 3.0) / 11.0, 0.0, 1.0)
			var bed01: float = clampf((float(sa[CaveTopology.S_BEDDING]) - 4.0) / 31.0, 0.0, 1.0)
			var packed: float = floor(frac01 * 31.0) * 32.0 + floor(bed01 * 31.0)
			var water_y: float = -9999.0
			if sa[CaveTopology.S_STATE] == CaveTopology.FLOODED:
				water_y = float(topo.water_datum_mm) * 0.001
			var gutter: bool = (sa[CaveTopology.S_WORKS] & CaveTopology.WK_GUTTER) != 0
			var iron_base: float = 0.0
			var wks: int = sa[CaveTopology.S_WORKS]
			if (wks & CaveTopology.WK_BOLTLINE) != 0:
				iron_base += 0.45
			if (wks & CaveTopology.WK_PIPE) != 0:
				iron_base += 0.30
			if (wks & CaveTopology.WK_RAIL) != 0:
				iron_base += 0.20
			iron_base = clampf(iron_base, 0.0, 1.0)

			var ring: Array = []
			var data: Array = []
			for k in range(RING_VERTS):
				var side: float = 1.0
				var s01: float
				if k <= HALF_RING:
					s01 = float(k) / float(HALF_RING)
				else:
					side = -1.0
					s01 = float(RING_VERTS - k) / float(HALF_RING)
				var uv: Vector2 = _half_profile(s01, worked, hw, ht, side, gutter)
				var lp: Vector3 = p + right * uv.x + Vector3.UP * uv.y
				# --- silhouette break. Low-frequency lumps that vary along the
				# passage AND around it: buttresses, spalled backs, roof
				# irregularity. Suppressed on the floor and where the industry
				# cut a clean face.
				var outward: Vector3 = (right * uv.x + Vector3.UP * (uv.y - ht * 0.42)).normalized()
				var floor_mask: float = clampf(uv.y / 0.35, 0.0, 1.0)
				var big: float = noise_lo.get_noise_3d(lp.x * 1.0, lp.y * 1.0, lp.z * 1.0)
				var fine: float = noise.get_noise_3d(lp.x * 2.2, lp.y * 2.2, lp.z * 2.2)
				var amp: float = lerp(0.42, 0.085, worked) * floor_mask
				var d: float = big * amp + fine * amp * 0.45
				lp += outward * d
				# the floor is not flat either: rubble relief under the sweep
				if uv.y < 0.02:
					lp.y += (noise.get_noise_3d(lp.x * 3.1, 7.0, lp.z * 3.1)) * lerp(0.10, 0.022, worked)
				ring.append(lp)
				var above: float = lp.y - water_y if water_y > -9000.0 else 4.0
				data.append([
					Color(wet, worked, dark, iron_base * clampf(1.2 - abs(uv.y - 1.5), 0.0, 1.0)),
					Vector2(axial, s01 * 0.5 + (0.5 if side < 0.0 else 0.0)),
					Vector2(above, packed)
				])
			if prev_ring.size() == RING_VERTS:
				_emit_band(prev_ring, prev_data, ring, data, prev_centre, p + Vector3.UP * ht * 0.42)
			prev_ring = ring
			prev_data = data
			prev_centre = p + Vector3.UP * ht * 0.42
			axial += 0.2

func _catmull(p0: Vector3, p1: Vector3, p2: Vector3, p3: Vector3, t: float) -> Vector3:
	var t2: float = t * t
	var t3: float = t2 * t
	return 0.5 * ((2.0 * p1) + (-p0 + p2) * t + (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * t2
		+ (-p0 + 3.0 * p1 - 3.0 * p2 + p3) * t3)

func _emit_band(r0: Array, d0: Array, r1: Array, d1: Array, c0: Vector3, c1: Vector3) -> void:
	var mid: Vector3 = ((r0[0] as Vector3) + (r1[0] as Vector3)) * 0.5
	var c: Dictionary = _chunk(mid)
	var mb: MB = c["shell"]
	var v := PackedVector3Array()
	var nn := PackedVector3Array()
	var cc := PackedColorArray()
	var uu := PackedVector2Array()
	var u2 := PackedVector2Array()
	var idx := PackedInt32Array()
	for k in range(RING_VERTS):
		v.push_back(r0[k]); cc.push_back(d0[k][0]); uu.push_back(d0[k][1]); u2.push_back(d0[k][2])
	for k in range(RING_VERTS):
		v.push_back(r1[k]); cc.push_back(d1[k][0]); uu.push_back(d1[k][1]); u2.push_back(d1[k][2])
	for k in range(RING_VERTS):
		var k2: int = (k + 1) % RING_VERTS
		# inward-facing winding: the camera is inside the tube
		idx.push_back(k); idx.push_back(RING_VERTS + k); idx.push_back(k2)
		idx.push_back(k2); idx.push_back(RING_VERTS + k); idx.push_back(RING_VERTS + k2)
	nn = _recalc_normals(v, idx)
	# point every normal INTO the tube: the camera is inside it
	for i in range(nn.size()):
		var ctr: Vector3 = c0 if i < RING_VERTS else c1
		if nn[i].dot(ctr - v[i]) < 0.0:
			nn[i] = -nn[i]
	mb.add_arrays(mat_rock, v, nn, cc, uu, u2, idx, Transform3D.IDENTITY)

# --- chambers: a noise-displaced dome dropped over the station -------------
func _build_chambers() -> void:
	var nrow: int = topo.chambers.size() / 5
	for ci in range(nrow):
		var sid: int = topo.chambers[ci * 5 + 4]
		var r: float = float(topo.chambers[ci * 5 + 2]) * CELL + 1.6
		var p: Vector3 = _st_pos(sid)
		var s: PackedInt32Array = _st(sid)
		var ht: float = _ht(s) * 1.25
		var worked: float = float(s[CaveTopology.S_WORKED]) / 255.0
		var wet: float = float(s[CaveTopology.S_WET]) / 255.0
		var dark: float = clampf(float(s[CaveTopology.S_DEPTH]) / float(maxi(1, topo.edges[0].size())), 0.0, 1.0)
		var frac01: float = clampf((float(s[CaveTopology.S_FRACTURE]) - 3.0) / 11.0, 0.0, 1.0)
		var bed01: float = clampf((float(s[CaveTopology.S_BEDDING]) - 4.0) / 31.0, 0.0, 1.0)
		var packed: float = floor(frac01 * 31.0) * 32.0 + floor(bed01 * 31.0)
		var RINGS: int = 9
		var SEG: int = 26
		var rows: Array = []
		for a in range(RINGS + 1):
			var ph: float = float(a) / float(RINGS) * (PI * 0.5)
			var row: Array = []
			for b2 in range(SEG):
				var th: float = float(b2) / float(SEG) * TAU
				var rr: float = r * cos(ph)
				var yy: float = ht * sin(ph)
				var lp := Vector3(p.x + cos(th) * rr, p.y + yy, p.z + sin(th) * rr)
				var nsl: float = noise_lo.get_noise_3d(lp.x, lp.y * 1.4, lp.z)
				var nsf: float = noise.get_noise_3d(lp.x * 2.0, lp.y * 2.0, lp.z * 2.0)
				var outv := Vector3(cos(th) * cos(ph), sin(ph), sin(th) * cos(ph))
				lp += outv * (nsl * 0.85 + nsf * 0.30) * (0.35 + 0.65 * float(a) / float(RINGS))
				if a == 0:
					lp.y = p.y
				row.append(lp)
			rows.append(row)
		for a in range(RINGS):
			for b2 in range(SEG):
				var b3: int = (b2 + 1) % SEG
				var q0: Vector3 = rows[a][b2]
				var q1: Vector3 = rows[a][b3]
				var q2: Vector3 = rows[a + 1][b2]
				var q3: Vector3 = rows[a + 1][b3]
				var v := PackedVector3Array([q0, q1, q2, q3])
				var idx := PackedInt32Array([0, 2, 1, 1, 2, 3])
				var cc := PackedColorArray()
				var uu := PackedVector2Array()
				var u2 := PackedVector2Array()
				for w in range(4):
					cc.push_back(Color(wet, worked, dark, 0.15))
					uu.push_back(Vector2(v[w].x, float(b2) / float(SEG)))
					u2.push_back(Vector2(v[w].y - p.y + 0.4, packed))
				var nn: PackedVector3Array = _recalc_normals(v, idx)
				var ctr: Vector3 = p + Vector3.UP * (ht * 0.35)
				for w in range(4):
					if nn[w].dot(ctr - v[w]) < 0.0:
						nn[w] = -nn[w]
				var mid: Vector3 = (q0 + q3) * 0.5
				var mb: MB = _chunk(mid)["shell"]
				mb.add_arrays(mat_rock, v, nn, cc, uu, u2, idx, Transform3D.IDENTITY)
		# a flat-ish chamber floor so props sit on something
		var fv := PackedVector3Array()
		var fi := PackedInt32Array()
		var fc := PackedColorArray()
		var fu := PackedVector2Array()
		var fu2 := PackedVector2Array()
		fv.push_back(p)
		fc.push_back(Color(wet, worked, dark, 0.1))
		fu.push_back(Vector2(p.x, 0.0))
		fu2.push_back(Vector2(0.4, packed))
		for b2 in range(SEG + 1):
			var th2: float = float(b2 % SEG) / float(SEG) * TAU
			var lp2: Vector3 = rows[0][b2 % SEG]
			fv.push_back(lp2)
			fc.push_back(Color(wet, worked, dark, 0.1))
			fu.push_back(Vector2(lp2.x, float(b2) / float(SEG)))
			fu2.push_back(Vector2(0.4, packed))
		for b2 in range(SEG):
			fi.push_back(0); fi.push_back(b2 + 1); fi.push_back(((b2 + 1) % SEG) + 1)
		var fn: PackedVector3Array = PackedVector3Array()
		fn.resize(fv.size())
		for w in range(fv.size()):
			fn[w] = Vector3.UP
		_chunk(p)["shell"].add_arrays(mat_rock, fv, fn, fc, fu, fu2, fi, Transform3D.IDENTITY)

# ===========================================================================
# props -- every rule here reads topology and writes only to chunks
# ===========================================================================
func _place_props() -> void:
	for e in range(topo.edges.size()):
		var ids: PackedInt32Array = topo.edges[e]
		for i in range(ids.size()):
			_dress_station(ids[i], i, ids)
	_place_water()

func _dress_station(sid: int, i: int, ids: PackedInt32Array) -> void:
	var s: PackedInt32Array = _st(sid)
	var p: Vector3 = _st_pos(sid)
	var nxt: Vector3 = _st_pos(ids[mini(ids.size() - 1, i + 1)])
	var tangent: Vector3 = (nxt - p).normalized()
	if tangent.length() < 0.5:
		tangent = Vector3(1, 0, 0)
	var right: Vector3 = tangent.cross(Vector3.UP).normalized()
	var yaw: float = atan2(tangent.x, tangent.z)
	var hw: float = _hw(s)
	var ht: float = _ht(s)
	var worked: float = float(s[CaveTopology.S_WORKED]) / 255.0
	var wet: float = float(s[CaveTopology.S_WET]) / 255.0
	var wks: int = s[CaveTopology.S_WORKS]
	var flooded: bool = s[CaveTopology.S_STATE] == CaveTopology.FLOODED
	var integ: float = float(s[CaveTopology.S_INTEG]) / 255.0
	var basis_dir := Basis.from_euler(Vector3(0, yaw, 0))

	# ---------- UNDERFOOT (0 - 1.5 m) --------------------------------------
	# loose stone. More where the ground is bad, less where it was trammed.
	var n_stone: int = int(14.0 + 34.0 * (1.0 - worked * 0.62) + (1.0 - integ) * 24.0)
	for k in range(n_stone):
		var u: float = rng.randf_range(-0.95, 0.95) * hw
		var v: float = rng.randf_range(-0.30, 0.30)
		var q: Vector3 = p + right * u + tangent * v
		q.y += 0.02
		_prop(q, "stone%d" % (rng.randi() % 4),
			_xf(q, Vector3(rng.randf() * 0.4, rng.randf() * TAU, rng.randf() * 0.4),
				Vector3.ONE * rng.randf_range(0.55, 1.7)),
			Color(1, 1, 1).lerp(Color(0.55, 0.5, 0.45), rng.randf() * 0.6))
	# grit: the smallest scale, and the one that decides whether a floor reads
	# as ground or as a polygon. 22 per 0.6 m cell inside 12 m of the lamp.
	for k in range(22):
		var ug: float = rng.randf_range(-0.98, 0.98) * hw
		var qg: Vector3 = p + right * ug + tangent * rng.randf_range(-0.30, 0.30)
		qg.y += 0.008
		_prop(qg, "grit%d" % (rng.randi() % 2),
			_xf(qg, Vector3(rng.randf() * TAU, rng.randf() * TAU, rng.randf() * TAU),
				Vector3.ONE * rng.randf_range(0.6, 2.0)))
	# fresh spall under bad ground: angular flakes off the back
	if integ < 0.62:
		for k in range(int(4.0 + (1.0 - integ) * 9.0)):
			var qsl: Vector3 = p + right * rng.randf_range(-0.95, 0.95) * hw + tangent * rng.randf_range(-0.3, 0.3)
			qsl.y += 0.02
			_prop(qsl, "spall%d" % (rng.randi() % 3),
				_xf(qsl, Vector3(rng.randf() * 0.5, rng.randf() * TAU, rng.randf() * 0.5),
					Vector3.ONE * rng.randf_range(0.6, 1.6)))
	# fines and silt fans, where the water has been
	if wet > 0.45:
		for k in range(3):
			var q2: Vector3 = p + right * rng.randf_range(-0.9, 0.9) * hw + tangent * rng.randf_range(-0.3, 0.3)
			q2.y += 0.006
			_prop(q2, "fines", _xf(q2, Vector3(0, rng.randf() * TAU, 0),
				Vector3(rng.randf_range(0.6, 2.0), 1.0, rng.randf_range(0.6, 2.0))),
				Color(0.9, 0.85, 0.78))
	# litter: small, sparse, everywhere the industry went
	for k in range(2):
		if worked < 0.25 or rng.randf() > 0.5:
			continue
		var q3: Vector3 = p + right * rng.randf_range(-0.9, 0.9) * hw + tangent * rng.randf_range(-0.3, 0.3)
		q3.y += 0.012
		_prop(q3, "litter", _xf(q3, Vector3(0, rng.randf() * TAU, 0)), Color(1, 1, 1))

	# ---------- THE PERMANENT WAY -----------------------------------------
	if (wks & CaveTopology.WK_RAIL) != 0 and not flooded:
		var off: float = 0.30                                  # 0.60 m gauge
		for sgn in [-1.0, 1.0]:
			var q4: Vector3 = p + right * (sgn * off)
			q4.y += 0.10
			_prop(q4, "rail", Transform3D(basis_dir, q4), Color(1, 1, 1))
		var qs: Vector3 = p
		qs.y += 0.045
		_prop(qs, "sleeper", Transform3D(basis_dir, qs),
			Color(1, 1, 1).lerp(Color(0.6, 0.55, 0.5), rng.randf() * 0.7))
		for k in range(26):
			var qb: Vector3 = p + right * rng.randf_range(-0.72, 0.72) + tangent * rng.randf_range(-0.3, 0.3)
			qb.y += 0.03
			_prop(qb, "ballast%d" % (rng.randi() % 3),
				_xf(qb, Vector3(rng.randf(), rng.randf() * TAU, rng.randf()), Vector3.ONE * rng.randf_range(0.7, 1.5)),
				Color(0.9, 0.86, 0.8))

	# ---------- SILHOUETTE -------------------------------------------------
	if (wks & CaveTopology.WK_SETS) != 0:
		var qset: Vector3 = p
		var use_arch: bool = worked > 0.80 and (sid % 3 == 0)
		var nm: String = "setfail" if (wks & CaveTopology.WK_SETFAIL) != 0 else ("arch" if use_arch else "set")
		# the set is built for a 2.36 m span and a 2.02 m cap: scale it so the
		# posts stand against the legs of THIS section, not in the middle of it
		var sc: float = clampf((hw - 0.12) / 1.18, 0.55, 2.4)
		var sy: float = clampf((ht - 0.25) / 2.02, 0.5, 2.2)
		_prop(qset, nm, Transform3D(basis_dir * Basis.from_scale(Vector3(sc, sy, 1.0)), qset),
			Color(1, 1, 1).lerp(Color(0.55, 0.5, 0.46), rng.randf() * 0.8))
	if (wks & CaveTopology.WK_SETS) != 0 and hw > 1.15 and integ < 0.72 and rng.randf() < 0.6:
		var lgs: float = 1.0 if (sid % 4 < 2) else -1.0
		var qlg: Vector3 = p + right * (lgs * (hw + 0.06))
		qlg.y += 0.30
		_prop(qlg, "lagging", Transform3D(_face(-right * lgs) * Basis.from_scale(
			Vector3(1.0, clampf(ht / 2.2, 0.7, 1.8), 1.0)), qlg))
	if (wks & CaveTopology.WK_RAIL) != 0 and rng.randf() < 0.045:
		var qtb: Vector3 = p + right * (rng.randf_range(0.45, 0.8) * hw * (1.0 if rng.randf() < 0.5 else -1.0))
		qtb.y += 0.06
		_prop(qtb, "tub", Transform3D(basis_dir * Basis.from_euler(
			Vector3(rng.randf_range(-0.2, 0.9), rng.randf_range(-0.5, 0.5), rng.randf_range(-0.3, 1.2))), qtb))
	if (wks & CaveTopology.WK_SPOIL) != 0:
		var sgn2: float = 1.0 if (sid % 2 == 0) else -1.0
		var qsp: Vector3 = p + right * (sgn2 * hw * 0.72)
		_prop(qsp, "spoil", Transform3D(basis_dir * Basis.from_scale(Vector3(
			rng.randf_range(0.7, 1.3), rng.randf_range(0.6, 1.2), rng.randf_range(0.8, 1.6))), qsp),
			Color(1, 1, 1).lerp(Color(0.6, 0.55, 0.5), rng.randf()))
	# breakdown blocks: bad ground and natural passage
	if integ < 0.55 or worked < 0.3:
		var nb: int = 1 + int((1.0 - integ) * 2.5)
		for k in range(nb):
			if rng.randf() > 0.55:
				continue
			var side_bk: float = 1.0 if rng.randf() < 0.5 else -1.0
			var qbk: Vector3 = p + right * (side_bk * rng.randf_range(0.42, 0.88) * hw) + tangent * rng.randf_range(-0.3, 0.3)
			qbk.y += 0.10
			_prop(qbk, "block%d" % (rng.randi() % 3),
				_xf(qbk, Vector3(rng.randf() * 0.5, rng.randf() * TAU, rng.randf() * 0.5),
					Vector3.ONE * rng.randf_range(0.7, 1.8)),
				Color(1, 1, 1).lerp(Color(0.6, 0.55, 0.5), rng.randf() * 0.7))
	# roof pendants in natural ground
	if worked < 0.35 and rng.randf() < 0.45:
		var qp: Vector3 = p + right * rng.randf_range(-0.6, 0.6) * hw
		qp.y += ht * rng.randf_range(0.78, 0.95)
		_prop(qp, "pendant", _xf(qp, Vector3(rng.randf() * 0.25, rng.randf() * TAU, rng.randf() * 0.25),
			Vector3(rng.randf_range(0.5, 1.2), rng.randf_range(0.6, 1.6), rng.randf_range(0.5, 1.2))),
			Color(1, 1, 1))
	if worked < 0.5 and rng.randf() < 0.5:
		var sgn3: float = 1.0 if rng.randf() < 0.5 else -1.0
		var qf: Vector3 = p + right * (sgn3 * hw * 0.92)
		qf.y += rng.randf_range(0.3, ht * 0.6)
		_prop(qf, "flowstone", _xf(qf, Vector3(0, rng.randf() * TAU, 0),
			Vector3(rng.randf_range(0.6, 1.5), rng.randf_range(0.7, 2.2), rng.randf_range(0.6, 1.5))),
			Color(1, 1, 1))

	# ---------- LAMP DISTANCE (2 - 6 m) ------------------------------------
	# the bolt line at the springing, on the 1.2 m module
	if (wks & CaveTopology.WK_BOLTLINE) != 0 and sid % 2 == 0:
		for sgn4 in [-1.0, 1.0]:
			var qb2: Vector3 = p + right * (sgn4 * hw * 0.96)
			qb2.y += 1.55 + rng.randf_range(-0.08, 0.08)
			var look: Basis = _face(-right * sgn4)
			_prop(qb2, "bolt", Transform3D(look, qb2),
				Color(1, 1, 1).lerp(Color(0.7, 0.55, 0.42), rng.randf()))
		# a second, higher ring in the bigger sections
		if hw > 1.5 and rng.randf() < 0.6:
			var qb3: Vector3 = p + Vector3.UP * (ht * 0.82)
			_prop(qb3, "bolt", Transform3D(_face(Vector3.DOWN), qb3), Color(1, 1, 1))
	if (wks & CaveTopology.WK_MESH) != 0 and sid % 3 == 0:
		var sgn5: float = 1.0 if (sid % 6 < 3) else -1.0
		var qm: Vector3 = p + right * (sgn5 * hw * 0.97)
		qm.y += 1.5
		_prop(qm, "meshpanel", Transform3D(_face(-right * sgn5), qm),
			Color(1, 1, 1).lerp(Color(0.8, 0.6, 0.45), rng.randf() * 0.8))
	if (wks & CaveTopology.WK_PIPE) != 0:
		var qpi: Vector3 = p + right * (hw * 0.90)
		qpi.y += 1.62
		_prop(qpi, "pipe", Transform3D(basis_dir, qpi),
			Color(1, 1, 1).lerp(Color(0.75, 0.55, 0.40), rng.randf() * 0.9))
	if (wks & CaveTopology.WK_LAUNDER) != 0:
		var ql: Vector3 = p - right * (hw * 0.78)
		ql.y += 0.86
		_prop(ql, "launder", Transform3D(basis_dir, ql), Color(1, 1, 1))
	if (wks & CaveTopology.WK_BUS) != 0:
		var qbus: Vector3 = p + Vector3.UP * (ht * 0.86)
		_prop(qbus, "bus", Transform3D(basis_dir, qbus), Color(1, 1, 1))
		if sid % 4 == 0:
			var qin: Vector3 = qbus + Vector3.UP * 0.10
			_prop(qin, "insulator", Transform3D(basis_dir, qin), Color(1, 1, 1))
	if (wks & CaveTopology.WK_PLATE) != 0:
		var qpl: Vector3 = p + right * (hw * 0.96)
		qpl.y += 1.40
		_prop(qpl, "plate", Transform3D(_face(-right), qpl), Color(1, 1, 1))
	if (wks & CaveTopology.WK_STANDWATER) != 0:
		var qw: Vector3 = p + right * rng.randf_range(-0.6, 0.6) * hw
		qw.y += 0.012
		_prop(qw, "puddle", _xf(qw, Vector3(0, rng.randf() * TAU, 0),
			Vector3(rng.randf_range(0.7, 2.2), 1.0, rng.randf_range(0.7, 1.8))), Color(1, 1, 1))
	# discarded kit of the old register
	if worked > 0.4 and rng.randf() < 0.09:
		var qd: Vector3 = p + right * (hw * rng.randf_range(0.55, 0.9) * (1.0 if rng.randf() < 0.5 else -1.0))
		_prop(qd, "drum" if rng.randf() < 0.5 else "coil",
			_xf(qd, Vector3(0.0 if rng.randf() < 0.6 else 1.4, rng.randf() * TAU, 0.0)), Color(1, 1, 1))

	# ---------- THE BROUGHT ------------------------------------------------
	# a composite tray clipped over the old bracket line, and a bracket under it
	if (wks & CaveTopology.WK_TRAY) != 0:
		var qt: Vector3 = p - right * (hw * 0.83)
		qt.y += 1.86
		_prop(qt, "tray", Transform3D(basis_dir, qt), Color(1, 1, 1))
		if sid % 3 == 0:
			var qbr: Vector3 = qt - Vector3.UP * 0.06 - right * 0.10
			_prop(qbr, "bracket", Transform3D(_face(right), qbr), Color(1, 1, 1))
	if (wks & CaveTopology.WK_DUCT) != 0 and ht > 2.6:
		var qdu: Vector3 = p + Vector3.UP * (ht * 0.80) + right * (hw * 0.34)
		_prop(qdu, "duct", Transform3D(basis_dir, qdu), Color(1, 1, 1))
	if (wks & CaveTopology.WK_BEACON) != 0 and not flooded:
		var qbe: Vector3 = p + right * (hw * 0.70 * (1.0 if (sid % 2 == 0) else -1.0))
		qbe.y += 0.02
		_prop(qbe, "beacon", _xf(qbe, Vector3(0, rng.randf() * TAU, 0)), Color(1, 1, 1))
		lights.append(qbe + Vector3.UP * 0.56)
	if (wks & CaveTopology.WK_KIT) != 0 and not flooded:
		var qk: Vector3 = p + right * (hw * rng.randf_range(0.6, 0.88) * (1.0 if rng.randf() < 0.5 else -1.0))
		qk.y += 0.01
		var roll_kit: float = rng.randf()
		if roll_kit < 0.45:
			_prop(qk, "case", _xf(qk, Vector3(0, rng.randf() * TAU, 0)))
		elif roll_kit < 0.75:
			var qi: Vector3 = qk + Vector3.UP * 1.25
			_prop(qi, "instrument", Transform3D(_face(-right), qi))
		else:
			_prop(qk, "mast", _xf(qk, Vector3(0, rng.randf() * TAU, 0)))
			lights.append(qk + Vector3.UP * 1.28)

	# ---------- MACHINE GROUND --------------------------------------------
	if (wks & CaveTopology.WK_PLANT) != 0:
		var qpu: Vector3 = p + right * 1.4
		_prop(qpu, "pump", Transform3D(basis_dir, qpu), Color(1, 1, 1))

	# ---------- SAGGING CABLE ---------------------------------------------
	# a catenary between this bracket and the next, 8 links. This is the thing
	# that makes a passage feel used rather than dug.
	if (wks & CaveTopology.WK_BOLTLINE) != 0 and i + 2 < ids.size():
		var s2: PackedInt32Array = _st(ids[i + 2])
		if (s2[CaveTopology.S_WORKS] & CaveTopology.WK_BOLTLINE) != 0:
			var a0: Vector3 = p + right * (hw * 0.93) + Vector3.UP * 1.66
			var a1: Vector3 = _st_pos(ids[i + 2]) + right * (hw * 0.93) + Vector3.UP * 1.66
			var sag: float = 0.16 + rng.randf() * 0.13
			var prev: Vector3 = a0
			for k in range(1, 7):
				var tt: float = float(k) / 6.0
				var cur: Vector3 = a0.lerp(a1, tt)
				cur.y -= sin(tt * PI) * sag
				var mid2: Vector3 = (prev + cur) * 0.5
				var dl: float = prev.distance_to(cur)
				var bb: Basis = _face((cur - prev).normalized()) * Basis.from_scale(Vector3(1, 1, dl))
				_prop(mid2, "cablelink", Transform3D(bb, mid2), Color(1, 1, 1))
				prev = cur

# --- standing water in the sump -------------------------------------------
func _place_water() -> void:
	var ids: PackedInt32Array = topo.edges[0]
	var y: float = float(topo.water_datum_mm) * 0.001
	var run_start: int = -1
	for i in range(ids.size() + 1):
		var flooded: bool = false
		if i < ids.size():
			flooded = _st(ids[i])[CaveTopology.S_STATE] == CaveTopology.FLOODED
		if flooded and run_start < 0:
			run_start = i
		elif not flooded and run_start >= 0:
			for j in range(run_start, i):
				var p: Vector3 = _st_pos(ids[j])
				var hw: float = _hw(_st(ids[j])) * 1.05
				var nxt: Vector3 = _st_pos(ids[mini(ids.size() - 1, j + 1)])
				var tangent: Vector3 = (nxt - p).normalized()
				var yaw: float = atan2(tangent.x, tangent.z)
				var q := Vector3(p.x, y, p.z)
				_prop(q, "watertile", Transform3D(Basis.from_euler(Vector3(0, yaw, 0)) * Basis.from_scale(
					Vector3(hw * 2.0, 1.0, 0.75)), q), Color(1, 1, 1))
			run_start = -1

# ===========================================================================
# emit: one MeshInstance3D per chunk for the shell, one MultiMeshInstance3D
# per (chunk, prop type). This is where the single lamp pays: every one of
# these carries a visibility range, so a chunk out of lamp reach costs nothing.
# ===========================================================================
func _emit(root: Node3D) -> void:
	# the water tile mesh, built late so it can use mat_water
	var wb := MB.new()
	wb.add_prim(mat_water, _box(1.0, 0.01, 1.0), _xf(Vector3.ZERO), Color(1, 1, 1))
	kit["watertile"] = wb.commit()
	kit_vis["watertile"] = VIS_SHELL

	for ki in range(chunk_order.size()):
		var key: int = chunk_order[ki]
		var c: Dictionary = chunks[key]
		var holder := Node3D.new()
		holder.name = "chunk_%d" % key
		root.add_child(holder)
		stat_chunks += 1
		var shell: MB = c["shell"]
		if shell.tri_count() > 0:
			var mi := MeshInstance3D.new()
			mi.mesh = shell.commit()
			mi.visibility_range_end = VIS_SHELL
			mi.visibility_range_end_margin = 3.0
			mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
			stat_shell_tris += shell.tri_count()
			holder.add_child(mi)
		var props: Dictionary = c["props"]
		for name in props.keys():
			var xs: Array = props[name]
			if xs.size() == 0:
				continue
			# NOTE: no instance colours. A MultiMesh instance colour REPLACES the
			# mesh's own vertex colours in Godot 4, which flattened every kit
			# part to white in the first pass. Colour lives in the mesh; the
			# per-instance variation comes from the world-space wear shader.
			var mm := MultiMesh.new()
			mm.transform_format = MultiMesh.TRANSFORM_3D
			mm.use_colors = false
			mm.mesh = kit[name]
			mm.instance_count = xs.size()
			var buf := PackedFloat32Array()
			buf.resize(xs.size() * 12)
			for n in range(xs.size()):
				var t: Transform3D = xs[n]
				var b: Basis = t.basis
				var o: int = n * 12
				buf[o + 0] = b.x.x; buf[o + 1] = b.y.x; buf[o + 2] = b.z.x; buf[o + 3] = t.origin.x
				buf[o + 4] = b.x.y; buf[o + 5] = b.y.y; buf[o + 6] = b.z.y; buf[o + 7] = t.origin.y
				buf[o + 8] = b.x.z; buf[o + 9] = b.y.z; buf[o + 10] = b.z.z; buf[o + 11] = t.origin.z
			mm.buffer = buf
			var mmi := MultiMeshInstance3D.new()
			mmi.multimesh = mm
			mmi.name = name
			mmi.visibility_range_end = kit_vis.get(name, VIS_LAMP)
			mmi.visibility_range_end_margin = 2.0
			# scatter does not cast shadows: it doubles the cost of the lamp
			# and nothing in the frame reads a pebble's shadow.
			if name.begins_with("stone") or name.begins_with("ballast") or name == "litter" or name == "fines":
				mmi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
			holder.add_child(mmi)
			stat_multimeshes += 1

# --- the camera path, straight down the main drive -------------------------
func _build_camera_path() -> void:
	var ids: PackedInt32Array = topo.edges[0]
	for i in range(ids.size()):
		var p: Vector3 = _st_pos(ids[i])
		var s: PackedInt32Array = _st(ids[i])
		var eye: float = 1.15
		if s[CaveTopology.S_WIDTH] == CaveTopology.WC_CRAWL:
			eye = 0.70
		path_points.push_back(p + Vector3.UP * eye)
	for i in range(path_points.size()):
		var j: int = mini(path_points.size() - 1, i + 3)
		path_look.push_back(path_points[j])
