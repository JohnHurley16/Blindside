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
const RING_VERTS: int = 40          # 20 per side
const HALF_RING: int = 20
const SUBSTEPS: int = 4             # rings per station -> ~0.15 m spacing

# how far each family of thing is drawn. The lamp reaches ~20 m on walls and
# ~6 m on the floor (ART-DIRECTION 2.1), and the direction says spend no art
# budget past 15 m (3.6). These numbers are that rule, made mechanical.
const VIS_SHELL: float = 44.0
const VIS_SILHOUETTE: float = 30.0  # sets, arches, pipes, duct, spoil
const VIS_LAMP: float = 19.0        # bolts, trays, plates, cable, kit
const VIS_UNDERFOOT: float = 12.0   # loose stone, ballast, fines, litter
# A VERTICAL sightline defeats a visibility range. Standing at the lip of a
# 34 m winze, the far end is more than twice VIS_SHELL away, and THE-ICE 2.4
# predicted exactly this: "LOD comes back... a vertical sightline is what
# defeats them." This spike answers it the cheap way -- a longer range on the
# chunks that hold pitch geometry only -- and reports what that costs.
const VIS_PITCH: float = 96.0

var topo: CaveTopology
var rng: RandomNumberGenerator
var noise: FastNoiseLite
var noise_lo: FastNoiseLite

# Generated noise, not a bitmap asset. PROCEDURAL-AND-GODOT Q5 (default yes).
# These four volumes replace ~700 integer-hash evaluations per rock fragment
# with ~30-60 texture fetches, which is what paid for the parallax and the
# three normal scales. Built by FastNoiseLite at load, from the cave seed;
# nothing is imported, nothing is unwrapped, nothing is photographic. 786 KB.
const NTEX: int = 64
var tex_fbm: ImageTexture3D
var tex_cel: ImageTexture3D
var tex_agg: ImageTexture3D
var tex_cid: ImageTexture3D

var mat_rock: ShaderMaterial
var mat_stone: ShaderMaterial
var mat_block: ShaderMaterial
var mat_iron: ShaderMaterial
var mat_steel: ShaderMaterial
var mat_timber: ShaderMaterial
var mat_composite: ShaderMaterial
var mat_alu: ShaderMaterial
var mat_porcelain: ShaderMaterial
var mat_cable: ShaderMaterial
var mat_water: ShaderMaterial
var mat_ice: ShaderMaterial
var mat_ice_clear: ShaderMaterial
var mat_ice_bubbly: ShaderMaterial
var mat_ice_block: ShaderMaterial
var mat_ice_lid: ShaderMaterial
var mat_ice_dirty: ShaderMaterial
var mat_pilot: StandardMaterial3D
# ONE ROCK AND ONE ICE MATERIAL PER LEVEL. The only thing that differs between
# them is `water_y`: the cave now has a water surface per level rather than one
# global datum, which cave/PHOTOREAL.md 7 already listed as guess 4 -- "this
# treats the whole cave as having drowned once, to one level" -- and which
# THE-ICE 2.3 says the melt turns from a flagged guess into a required change.
# A chunk only ever belongs to one level, so this costs no extra draw calls.
var mat_rock_lv: Array = []
var mat_ice_lv: Array = []
var max_depth: float = 1.0
# What `dark` (the depth fade in COLOR.b) is normalised by. On the flat path it
# is the main drive's length, which is what it always was; on the layered path
# graph depth runs far past that, so it is the deepest station.
var dark_div: float = 1.0

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

	_make_noise_textures(p_seed)
	stage.call("noise volumes")
	_make_materials()
	_make_kit()
	stage.call("kit built")
	for i in range(topo.stations.size()):
		max_depth = maxf(max_depth, float((topo.stations[i] as PackedInt32Array)[CaveTopology.S_DEPTH]))
	dark_div = float(maxi(1, topo.edges[0].size())) if topo.levels <= 1 else max_depth
	_sweep_edges()
	stage.call("swept")
	_sweep_pitches()
	stage.call("pitches")
	_build_chambers()
	stage.call("chambers")
	_place_props()
	stage.call("props")
	_place_reveals()
	_dress_assayer_site()
	stage.call("reveals")
	_emit(root)
	stage.call("emitted")
	_build_camera_path()

# --- the generated noise volumes ------------------------------------------
# kind 0 = fbm, 1 = cellular F2-F1 (joints), 2 = cellular F1 (the bevel between
# aggregate stones), 3 = cellular CELL_VALUE (one value per stone: its height
# and its albedo). Seamless, so they tile in world space at any scale.
func _noise3(kind: int, freq: float, oct: int, seedv: int) -> ImageTexture3D:
	var n := FastNoiseLite.new()
	n.seed = seedv
	n.frequency = freq
	if kind == 0:
		n.noise_type = FastNoiseLite.TYPE_SIMPLEX_SMOOTH
		n.fractal_type = FastNoiseLite.FRACTAL_FBM
		n.fractal_octaves = oct
		n.fractal_lacunarity = 2.0
		n.fractal_gain = 0.54
	else:
		n.noise_type = FastNoiseLite.TYPE_CELLULAR
		n.fractal_type = FastNoiseLite.FRACTAL_NONE
		n.cellular_distance_function = FastNoiseLite.DISTANCE_EUCLIDEAN
		n.cellular_jitter = 1.0
		if kind == 1:
			n.cellular_return_type = FastNoiseLite.RETURN_DISTANCE2_SUB
		elif kind == 2:
			n.cellular_return_type = FastNoiseLite.RETURN_DISTANCE
		else:
			n.cellular_return_type = FastNoiseLite.RETURN_CELL_VALUE
	var imgs: Array[Image] = n.get_seamless_image_3d(NTEX, NTEX, NTEX, false, 0.08)
	var t := ImageTexture3D.new()
	t.create(imgs[0].get_format(), NTEX, NTEX, NTEX, false, imgs)
	if OS.get_cmdline_args().has("--dumpnoise"):
		var im: Image = imgs[20].duplicate()
		im.convert(Image.FORMAT_RGB8)
		im.save_png(ProjectSettings.globalize_path("res://_noise_dump_k%d.png" % kind))
		var mn := 255
		var mx := 0
		for yy in range(NTEX):
			for xx in range(NTEX):
				var v: int = int(imgs[20].get_pixel(xx, yy).r * 255.0)
				mn = mini(mn, v)
				mx = maxi(mx, v)
		print("DBG noise kind %d fmt %d range %d..%d" % [kind, imgs[0].get_format(), mn, mx])
	return t

func _make_noise_textures(sd: int) -> void:
	# 2 base cycles across the tile, 5 octaves -> features from half a tile down
	# to a thirty-second of one. Sampled at three world scales in the shader.
	tex_fbm = _noise3(0, 2.0 / float(NTEX), 5, sd + 101)
	# 6 cells across the tile, so `p * fracture / 6` gives `fracture` per metre
	tex_cel = _noise3(1, 6.0 / float(NTEX), 1, sd + 211)
	tex_agg = _noise3(2, 6.0 / float(NTEX), 1, sd + 307)
	# one value per cell, so a stone is not the value of the stone beside it.
	# Same seed and frequency as tex_agg, so the cells line up exactly.
	tex_cid = _noise3(3, 6.0 / float(NTEX), 1, sd + 307)

# --- materials -------------------------------------------------------------
func _make_materials() -> void:
	var rsh: Shader = load("res://rock.gdshader")
	var ish: Shader = load("res://ice.gdshader")
	mat_rock_lv = []
	mat_ice_lv = []
	for L in range(topo.levels):
		var wy: float = -1000.0
		if L < topo.level_water_mm.size() and topo.level_water_mm[L] > -1000000:
			wy = float(topo.level_water_mm[L]) * 0.001
		var mr := ShaderMaterial.new()
		mr.shader = rsh
		mr.set_shader_parameter("t_fbm", tex_fbm)
		mr.set_shader_parameter("t_cel", tex_cel)
		mr.set_shader_parameter("t_agg", tex_agg)
		mr.set_shader_parameter("t_cid", tex_cid)
		mr.set_shader_parameter("water_y", wy)
		mat_rock_lv.append(mr)
		var mi := ShaderMaterial.new()
		mi.shader = ish
		mi.set_shader_parameter("t_fbm", tex_fbm)
		mi.set_shader_parameter("water_y", wy)
		mat_ice_lv.append(mi)
	mat_rock = mat_rock_lv[0]
	mat_ice = mat_ice_lv[0]
	# --- the ice PROP materials -------------------------------------------
	# The kit builder writes vertex colours but the four ice scalars are not
	# what a kit vertex colour means, so ice props force them from uniforms
	# instead (ice.gdshader's *_u overrides). Three sets, because an icicle,
	# a floor boss and a plug of dirty fill are three different materials made
	# of the same substance -- which is the whole argument of ART-DIRECTION
	# 3.1's four scalars.
	#
	# They are APPENDED TO mat_ice_lv on purpose: set_ice_param() walks that
	# array, and the lamp uniforms have to reach every ice surface in the
	# frame or half the ice glows and half does not.
	var wy0: float = -1000.0
	if topo.level_water_mm.size() > 0 and topo.level_water_mm[0] > -1000000:
		wy0 = float(topo.level_water_mm[0]) * 0.001
	mat_ice_clear = _ice_prop_mat(ish, wy0, 0.90, 0.92, 0.05, 0.28)
	mat_ice_bubbly = _ice_prop_mat(ish, wy0, 0.34, 0.34, 0.16, 0.40)
	# broken ice carries the floor it broke onto. Without the debris term a
	# block pile under a moulin renders as a heap of white polygons.
	mat_ice_block = _ice_prop_mat(ish, wy0, 0.64, 0.20, 0.26, 0.50)
	mat_ice_block.set_shader_parameter("albedo_gain", 0.66)
	# THE POOL LID IS NOT A MIRROR. At polish 0.92 the slab is roughness 0.13,
	# and a flat horizontal sheet at that roughness two metres under a 5.4 W
	# lamp returns almost all of it: 19.6% of `i10_meltwater_channel` came back
	# over 0.50 against a 3% ceiling, from one object. A lid froze slowly from
	# still water under a dripping roof; it is matt, not glassy.
	mat_ice_lid = _ice_prop_mat(ish, wy0, 0.80, 0.42, 0.10, 0.12)
	mat_ice_lid.set_shader_parameter("albedo_gain", 0.78)
	mat_ice_lv.append(mat_ice_lid)
	mat_ice_dirty = _ice_prop_mat(ish, wy0, 0.40, 0.30, 0.52, 0.55)
	mat_ice_lv.append(mat_ice_clear)
	mat_ice_lv.append(mat_ice_bubbly)
	mat_ice_lv.append(mat_ice_block)
	mat_ice_lv.append(mat_ice_dirty)
	mat_stone = ShaderMaterial.new()
	mat_stone.shader = load("res://stone.gdshader")
	mat_stone.set_shader_parameter("t_fbm", tex_fbm)
	mat_stone.set_shader_parameter("t_cel", tex_cel)
	mat_stone.set_shader_parameter("water_y", float(topo.water_datum_mm) * 0.001)
	# Loose rock in a drowned mine is wet rock. 0.35 was the first pass's guess
	# and it left every breakdown block reading as dry chalk under the lamp.
	mat_stone.set_shader_parameter("wetness", 0.55)
	mat_stone.set_shader_parameter("stone_tint", Vector3(0.80, 0.775, 0.74))
	# Breakdown blocks and spall plates are the only loose rock that is ever
	# within half a metre of the lamp, and at that range ANY albedo blows. A
	# 0.6 m boulder rendered at the same value as a 60 mm chip reads as
	# polystyrene. They get their own instance of the same shader: darker,
	# because a block that fell off the back is a fresh wet face, not a dusted
	# one, and wetter, because it has been sitting in the muck.
	mat_block = ShaderMaterial.new()
	mat_block.shader = mat_stone.shader
	mat_block.set_shader_parameter("t_fbm", tex_fbm)
	mat_block.set_shader_parameter("t_cel", tex_cel)
	mat_block.set_shader_parameter("water_y", float(topo.water_datum_mm) * 0.001)
	mat_block.set_shader_parameter("wetness", 0.78)
	mat_block.set_shader_parameter("stone_tint", Vector3(0.60, 0.583, 0.560))

	# One shader, six parameter sets. Vertex colours carry the part colours, so
	# a rail is rusted web plus bright head inside a single draw call.
	# METAL IS 0 OR 1. Cast iron was 0.55 in the first pass, which is not a
	# material. Where the rust has taken it, the mask carries it to dielectric.
	var ksh: Shader = load("res://kit.gdshader")
	var F0_IRON := Color(0.560, 0.570, 0.580)
	var F0_ALU := Color(0.912, 0.914, 0.920)
	mat_iron = _kit_mat(ksh, 1.0, 0.62, 1.00, 0.42, 0.0, F0_IRON)   # cast iron
	mat_steel = _kit_mat(ksh, 1.0, 0.19, 0.16, 0.45, 0.0, F0_IRON)  # rubbed steel
	mat_timber = _kit_mat(ksh, 0.0, 0.88, 0.16, 0.55, 1.0, F0_IRON) # waterlogged
	mat_composite = _kit_mat(ksh, 0.0, 0.38, 0.00, 0.14, 0.0, F0_ALU)  # BROUGHT
	mat_alu = _kit_mat(ksh, 1.0, 0.26, 0.00, 0.14, 0.0, F0_ALU)        # BROUGHT
	mat_porcelain = _kit_mat(ksh, 0.0, 0.09, 0.03, 0.24, 0.0, F0_IRON) # the Bus
	mat_cable = _kit_mat(ksh, 0.0, 0.56, 0.00, 0.30, 0.0, F0_IRON)

	mat_water = ShaderMaterial.new()
	mat_water.shader = load("res://water.gdshader")
	mat_water.set_shader_parameter("t_fbm", tex_fbm)

	# WARM_DIM amber. Never cyan (belief), never red (lethal). ART-DIRECTION 2.5
	mat_pilot = StandardMaterial3D.new()
	mat_pilot.albedo_color = Color(1.0, 0.72, 0.36)
	mat_pilot.emission_enabled = true
	mat_pilot.emission = Color(1.0, 0.70, 0.34)
	mat_pilot.emission_energy_multiplier = 2.6
	mat_pilot.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED

func _ice_prop_mat(sh: Shader, wy: float, clarity: float, polish: float,
				   debris: float, wet: float) -> ShaderMaterial:
	var m := ShaderMaterial.new()
	m.shader = sh
	m.set_shader_parameter("t_fbm", tex_fbm)
	m.set_shader_parameter("water_y", wy)
	m.set_shader_parameter("clarity_u", clarity)
	m.set_shader_parameter("polish_u", polish)
	m.set_shader_parameter("debris_u", debris)
	m.set_shader_parameter("wet_u", wet)
	m.set_shader_parameter("dark_u", 0.0)
	return m

func _kit_mat(sh: Shader, metal: float, rough: float, rust: float,
			  wet: float, grain: float, f0: Color = Color(0.56, 0.57, 0.58)) -> ShaderMaterial:
	var m := ShaderMaterial.new()
	m.shader = sh
	m.set_shader_parameter("metal", metal)
	m.set_shader_parameter("rough", rough)
	m.set_shader_parameter("rust", rust)
	m.set_shader_parameter("wet_amt", wet)
	m.set_shader_parameter("grain", grain)
	m.set_shader_parameter("metal_f0", Vector3(f0.r, f0.g, f0.b))
	m.set_shader_parameter("t_fbm", tex_fbm)
	m.set_shader_parameter("water_y", float(topo.water_datum_mm) * 0.001)
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
func _stone_mesh(sd: int, r: float, flat: float = 1.0, mat: Material = null) -> ArrayMesh:
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
	# BUG, and it was in every underfoot frame this spike ever rendered.
	# _recalc_normals' cross product has the opposite sign to Godot's
	# front-face winding, so every loose stone, ballast chip, spall flake and
	# breakdown block was lit by a normal pointing INTO itself. Under one lamp
	# and zero ambient that means no diffuse and no specular: they rendered as
	# flat black cut-outs lying on the floor, which is most of why the underfoot
	# scale read as origami. A stone is star-shaped about its own origin, so
	# `dot(n, v) > 0` is the correct outward test.
	var sn: PackedVector3Array = _recalc_normals(v, a[Mesh.ARRAY_INDEX])
	for i in range(sn.size()):
		if sn[i].dot(v[i]) < 0.0:
			sn[i] = -sn[i]
	a[Mesh.ARRAY_NORMAL] = sn
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
	arr[Mesh.ARRAY_NORMAL] = sn
	arr[Mesh.ARRAY_COLOR] = col
	arr[Mesh.ARRAY_INDEX] = a[Mesh.ARRAY_INDEX]
	am.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arr)
	am.surface_set_material(0, mat if mat != null else mat_stone)
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
		_reg("block%d" % i, _stone_mesh(311 + i, 0.30 + i * 0.24, 0.72, mat_block), VIS_SILHOUETTE)
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
		_reg("spall%d" % i, _stone_mesh(511 + i, 0.16 + i * 0.07, 0.28, mat_block), VIS_LAMP)
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

	# --- the ancients' shaft rings. NEW 2026-09-10. A UNIT ring, radius 1.0,
	# built from 16 tangential segments and four vertical straps; a pitch
	# scales it to its own bore. It is the one thing that gives a bore a scale
	# and a rhythm when there is nothing else in frame but wall going past.
	var cb := MB.new()
	for i in range(16):
		var ra: float = float(i) / 16.0 * TAU
		var rq := Vector3(cos(ra), 0.0, sin(ra))
		cb.add_prim(mat_iron, _box(0.075, 0.085, 0.42),
			Transform3D(Basis.from_euler(Vector3(0, -ra, 0)), rq), C_IRON)
	for i in range(4):
		var ra2: float = float(i) / 4.0 * TAU + 0.39
		var rq2 := Vector3(cos(ra2) * 0.97, 0.0, sin(ra2) * 0.97)
		cb.add_prim(mat_iron, _box(0.055, 0.34, 0.055), _xf(rq2), C_IRON_L)
	_reg("collarring", cb.commit(), VIS_PITCH)

	_make_ice_kit()

# ===========================================================================
# THE ICE KIT
# ===========================================================================
# Everything here is a solid of revolution about the local Y axis with a
# helical flute on it, because that is what water freezing while it runs
# actually makes. One generator, seven parameter sets -- the same discipline
# the rock family uses (ART-DIRECTION 3.1: one primitive, four scalars),
# applied to a substance that GROWS rather than one that breaks.
#
# THE VERTEX CONTRACT MATTERS HERE. ice.gdshader recovers the flow direction
# from the world-space gradient of UV2.x, so writing UV2.x = the distance
# along the icicle's own axis is what makes its flutes run DOWN it. A mesh
# built with add_prim() writes no UV2, the gradient vanishes, and the shader
# falls back to vertical -- right for an icicle, wrong for a pool lid, so the
# lid is built here with explicit arrays and not with add_prim.
#
# All of them are UNIT meshes: 1 m of length, scaled at placement. Same rule
# as the timber set, and it is why one mesh covers a 0.2 m dribble and a 2 m
# column.
func _revolve(mb: MB, mat: Material, prof: PackedVector2Array, seg: int, sd: int,
			  flute: float, wob: float, lean: Vector3) -> void:
	var lr := RandomNumberGenerator.new()
	lr.seed = sd
	var v := PackedVector3Array()
	var cc := PackedColorArray()
	var uu := PackedVector2Array()
	var u2 := PackedVector2Array()
	var idx := PackedInt32Array()
	var n_i: int = prof.size()
	# a per-RING radial jitter, held so the whole ring moves together: an
	# icicle is lumpy along its length, not around it
	var jit := PackedFloat32Array()
	jit.resize(n_i)
	for i in range(n_i):
		jit[i] = 1.0 + lr.randf_range(-wob, wob)
	var axial: float = 0.0
	for i in range(n_i):
		if i > 0:
			axial += absf(prof[i].y - prof[i - 1].y)
		for j in range(seg):
			var a: float = float(j) / float(seg) * TAU
			# the flute: six ribs that wind as they go, which is what a
			# refreezing dribble leaves and what stops a cone reading as a cone
			var f: float = 1.0 + flute * sin(a * 6.0 + prof[i].y * 9.0)
			var r: float = prof[i].x * jit[i] * f
			var y: float = prof[i].y
			v.push_back(Vector3(cos(a) * r + lean.x * absf(y), y, sin(a) * r + lean.z * absf(y)))
			cc.push_back(Color(1, 1, 1, 1))
			uu.push_back(Vector2(axial, float(j) / float(seg)))
			u2.push_back(Vector2(axial, 0.0))
	for i in range(n_i - 1):
		for j in range(seg):
			var j2: int = (j + 1) % seg
			var a0: int = i * seg + j
			var a1: int = i * seg + j2
			var b0: int = (i + 1) * seg + j
			var b1: int = (i + 1) * seg + j2
			idx.push_back(a0); idx.push_back(b0); idx.push_back(a1)
			idx.push_back(a1); idx.push_back(b0); idx.push_back(b1)
	var nn: PackedVector3Array = _recalc_normals(v, idx)
	# the profile is star-shaped about its own axis, so "points away from the
	# axis" is the outward test. Same bug the stone mesh had, same fix.
	for i in range(nn.size()):
		var rad := Vector3(v[i].x, 0.0, v[i].z)
		if rad.length() > 0.001 and nn[i].dot(rad) < 0.0:
			nn[i] = -nn[i]
	mb.add_arrays(mat, v, nn, cc, uu, u2, idx, Transform3D.IDENTITY)

# a hanging spike: fat at the root, a point at the tip, with growth rings.
# Unit length 1.0 downward from the origin.
func _icicle_prof(r0: float, rings: int) -> PackedVector2Array:
	var pr := PackedVector2Array()
	# A CAP RING. Without it the top of the spike is an open tube, and with
	# cull_disabled the camera sees its unlit inside -- which is why the first
	# icicle frame had a row of dark brown blobs where the roots should be.
	pr.push_back(Vector2(r0 * 0.18, 0.020))
	for i in range(rings + 1):
		var t: float = float(i) / float(rings)
		# (1-t)^0.62 is close to what a dribble that keeps flowing leaves;
		# the sine is the ring the freeze-thaw cycle puts on it
		var r: float = r0 * pow(1.0 - t, 0.62) * (1.0 + 0.16 * sin(t * 26.0))
		pr.push_back(Vector2(maxf(r, 0.0015), -t))
	return pr

func _make_ice_kit() -> void:
	var b: MB
	# --- icicles, three lengths -------------------------------------------
	for i in range(3):
		b = MB.new()
		_revolve(b, mat_ice_clear, _icicle_prof(0.026 + float(i) * 0.011, 13 + i * 3),
			9, 900 + i, 0.13, 0.10, Vector3(0.02 * float(i), 0.0, -0.01))
		_reg("icicle%d" % i, b.commit(), VIS_SILHOUETTE)
	# --- a fringe: seven spikes of different lengths off one patch of rime.
	# One draw call per chunk instead of seven, and it is how icicles actually
	# occur -- a line of them along a crack, never one on its own.
	for vv in range(2):
		b = MB.new()
		var lr := RandomNumberGenerator.new()
		lr.seed = 940 + vv
		for k in range(7):
			var off := Vector3(lr.randf_range(-0.42, 0.42), 0.0, lr.randf_range(-0.10, 0.10))
			# lengths on a power law, so a fringe is mostly short spikes with
			# two or three long ones in it. Uniform lengths read as a comb.
			var ln: float = 0.16 + 0.84 * pow(lr.randf(), 2.1)
			var pr: PackedVector2Array = _icicle_prof(0.017 + ln * 0.024, 9)
			for q in range(pr.size()):
				pr[q] = Vector2(pr[q].x, pr[q].y * ln)
			var sub := MB.new()
			_revolve(sub, mat_ice_clear, pr, 8, 951 + k + vv * 11, 0.14, 0.12,
				Vector3(lr.randf_range(-0.04, 0.04), 0.0, lr.randf_range(-0.04, 0.04)))
			var sf: Surf = sub.surf[mat_ice_clear]
			b.add_arrays(mat_ice_clear, sf.v, sf.n, sf.c, sf.u, sf.u2, sf.idx,
				Transform3D(Basis.IDENTITY, off))
		_reg("icefringe%d" % vv, b.commit(), VIS_SILHOUETTE)
	# --- floor bosses: where the drips landed and built back up ------------
	# Bubbly, because a drip freezes fast and traps its air. These are the ice
	# meshes that are WHITE rather than blue and the contrast is the point.
	for i in range(2):
		b = MB.new()
		var pr2 := PackedVector2Array()
		var rings: int = 9
		for k in range(rings + 1):
			var t: float = float(k) / float(rings)
			pr2.push_back(Vector2((0.16 + float(i) * 0.09) * pow(1.0 - t, 0.45)
				* (1.0 + 0.10 * sin(t * 15.0)), t))
		_revolve(b, mat_ice_bubbly, pr2, 10, 970 + i, 0.10, 0.14, Vector3.ZERO)
		_reg("iceboss%d" % i, b.commit(), VIS_LAMP)
	# --- the column: an icicle that reached the floor ---------------------
	# Waisted in the middle, because it is two things that met. Unit height 1,
	# so a 3 m column and a 1 m one are the same mesh.
	b = MB.new()
	var pc := PackedVector2Array()
	for k in range(19):
		var t: float = float(k) / 18.0
		var waist: float = 0.42 + 0.58 * pow(absf(t * 2.0 - 1.0), 1.5)
		pc.push_back(Vector2(0.085 * waist * (1.0 + 0.09 * sin(t * 34.0)), t))
	_revolve(b, mat_ice_clear, pc, 11, 981, 0.15, 0.06, Vector3(0.015, 0.0, 0.01))
	_reg("icecolumn", b.commit(), VIS_SILHOUETTE)
	# --- the frozen waterfall -------------------------------------------
	# Not a revolve of one thing: a SHEET clinging to a wall, made of seven
	# fused lobes of different diameters that all reach the floor. The single
	# most recognisable object in an ice cave and there was nothing like it
	# here. Modelled 1 m wide, 1 m tall, hanging from the origin, +Z outward.
	b = MB.new()
	var lr2 := RandomNumberGenerator.new()
	lr2.seed = 993
	for k in range(7):
		var xk: float = -0.5 + (float(k) + 0.5) / 7.0
		var rk: float = lr2.randf_range(0.055, 0.115)
		var hk: float = lr2.randf_range(0.72, 1.0)
		var pf := PackedVector2Array()
		for q in range(13):
			var t: float = float(q) / 12.0
			# a lobe is fat at the top and fatter again where it spreads onto
			# the floor: it is a flow, not a drip
			var rr: float = rk * (0.55 + 0.45 * cos(t * PI * 0.9))
			rr *= 1.0 + 0.30 * smoothstep(0.82, 1.0, t)
			pf.push_back(Vector2(rr * (1.0 + 0.13 * sin(t * 21.0)), -t * hk))
		var sub2 := MB.new()
		_revolve(sub2, mat_ice_clear, pf, 8, 1001 + k, 0.17, 0.08,
			Vector3(0.0, 0.0, lr2.randf_range(0.02, 0.09)))
		var sf2: Surf = sub2.surf[mat_ice_clear]
		b.add_arrays(mat_ice_clear, sf2.v, sf2.n, sf2.c, sf2.u, sf2.u2, sf2.idx,
			Transform3D(Basis.IDENTITY, Vector3(xk, 0.0, lr2.randf_range(-0.02, 0.03))))
	_reg("icefall", b.commit(), VIS_SILHOUETTE)
	# --- the pool lid ------------------------------------------------------
	# A 1 x 1 slab, slightly domed, for a still pool that froze over. What
	# sells it is not the slab: it is that the shader marches the bubble
	# trains INTO it, so the air trapped under the lid is under the lid.
	b = MB.new()
	var lv := PackedVector3Array()
	var lc := PackedColorArray()
	var lu := PackedVector2Array()
	var lu2 := PackedVector2Array()
	var li := PackedInt32Array()
	var NQ: int = 7
	for gz in range(NQ + 1):
		for gx in range(NQ + 1):
			var fx: float = float(gx) / float(NQ) - 0.5
			var fz: float = float(gz) / float(NQ) - 0.5
			var rr2: float = sqrt(fx * fx + fz * fz)
			var yy: float = 0.030 * (1.0 - clampf(rr2 * 2.0, 0.0, 1.0))
			lv.push_back(Vector3(fx, yy, fz))
			lc.push_back(Color(1, 1, 1, 1))
			lu.push_back(Vector2(fx, fz))
			lu2.push_back(Vector2(fx * 2.0, 0.0))
	for gz in range(NQ):
		for gx in range(NQ):
			var a0: int = gz * (NQ + 1) + gx
			var a1: int = a0 + 1
			var b0: int = a0 + NQ + 1
			var b1: int = b0 + 1
			li.push_back(a0); li.push_back(b0); li.push_back(a1)
			li.push_back(a1); li.push_back(b0); li.push_back(b1)
	var ln2: PackedVector3Array = _recalc_normals(lv, li)
	for i2 in range(ln2.size()):
		if ln2[i2].y < 0.0:
			ln2[i2] = -ln2[i2]
	b.add_arrays(mat_ice_lid, lv, ln2, lc, lu, lu2, li, Transform3D.IDENTITY)
	_reg("icelid", b.commit(), VIS_SHELL)
	# --- broken ice: the blocks a roof or a bridge dropped ----------------
	for i in range(3):
		_reg("iceblock%d" % i, _stone_mesh(1101 + i, 0.16 + float(i) * 0.13, 0.62,
			mat_ice_block), VIS_LAMP)
	# --- a rib for the inside of a bore ------------------------------------
	# Unit height 1, hugging the wall. What gives a shaft a rhythm when there
	# is nothing in frame but bore going past.
	b = MB.new()
	var prb := PackedVector2Array()
	for k in range(13):
		var t: float = float(k) / 12.0
		prb.push_back(Vector2(0.055 * (0.6 + 0.4 * sin(t * PI)) * (1.0 + 0.22 * sin(t * 18.0)), t))
	_revolve(b, mat_ice_clear, prb, 7, 1051, 0.20, 0.10, Vector3.ZERO)
	_reg("icerib", b.commit(), VIS_PITCH)

# ===========================================================================
# chunking
# ===========================================================================
func _chunk_key(p: Vector3) -> int:
	# 8 m CUBES, 2026-09-10. This was XZ only, and THE-ICE 2.3 named the
	# consequence before there was any vertical geometry to suffer it: "a
	# vertical shaft puts an entire cave's worth of geometry into one chunk
	# key." It now has a Y axis, so a chunk is a chunk of cave rather than a
	# column through all of it.
	var cx: int = int(floor(p.x / CHUNK_M))
	var cz: int = int(floor(p.z / CHUNK_M))
	if topo.levels <= 1:
		# the flat cave keeps its old partition, so the frames the trailer was
		# cut from are drawn by exactly the same MeshInstances as before
		return (cx + 4096) * 8192 + (cz + 4096)
	var cy: int = int(floor(p.y / CHUNK_M))
	return ((cx + 2048) * 4096 + (cy + 2048)) * 4096 + (cz + 2048)

func _chunk(p: Vector3) -> Dictionary:
	var k: int = _chunk_key(p)
	if not chunks.has(k):
		var c := {"shell": MB.new(), "props": {}, "key": k, "pitch": false}
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
# The shell floor is displaced by noise in _sweep_edge; the rock shader then
# parallax-maps another 58 mm of aggregate DOWN from that polygon. A prop
# placed on the polygon therefore stands on the tallest stone in the frame and
# reads as hovering. This returns the offset that puts it back in the ground.
func _floor_y(q: Vector3, worked: float) -> float:
	return noise.get_noise_3d(q.x * 3.1, 7.0, q.z * 3.1) * lerp(0.10, 0.022, worked) - 0.026

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

# --- the ice scalars -------------------------------------------------------
# ART-DIRECTION 3.1's four, derived from ONE topology field (`medium`) plus the
# depth band, because THE-ICE 5.4 note 4 puts exactly one enum above the line
# and everything else is the client's business.
#   polish   water-shaped or not. A conduit is polished; a fill is not.
#   clarity  bubble content. Refrozen meltwater is clear; dead glacier ice is
#            full of air and white.
#   debris   what the ice pushed into and carried.
# Returns (polish, clarity, debris).
func _ice_params(s: PackedInt32Array) -> Vector3:
	var med: int = s[CaveTopology.S_MEDIUM]
	var elev: int = s[CaveTopology.S_FLOOR_MM]
	var bnd: int = topo.band_of(elev)
	var jit: float = noise_lo.get_noise_3d(float(s[CaveTopology.S_X]) * 0.7, 3.0,
		float(s[CaveTopology.S_Y]) * 0.7) * 0.18
	if med == CaveTopology.MED_ICE and bnd == 0:
		# the meltwater conduit: scoured, clear, and it carries little
		return Vector3(clampf(0.86 + jit, 0.0, 1.0), clampf(0.78 + jit, 0.0, 1.0),
			clampf(0.16 + jit * 0.6, 0.0, 1.0))
	if med == CaveTopology.MED_ICE:
		# dead ice in the fill: bubbly, dirty, and nothing has polished it
		return Vector3(clampf(0.30 + jit, 0.0, 1.0), clampf(0.26 + jit, 0.0, 1.0),
			clampf(0.52 + jit, 0.0, 1.0))
	# a plug or a floor of ice over rock: it froze standing still, so it is
	# clear, flat and full of the muck it settled onto
	return Vector3(clampf(0.55 + jit, 0.0, 1.0), clampf(0.66 + jit, 0.0, 1.0),
		clampf(0.40 + jit, 0.0, 1.0))

# the ablation switches used to poke one material; there are now one per
# level plus the ice family, so they poke all of them.
func set_rock_param(n: String, v: Variant) -> void:
	for m in mat_rock_lv:
		(m as ShaderMaterial).set_shader_parameter(n, v)

func set_ice_param(n: String, v: Variant) -> void:
	for m in mat_ice_lv:
		(m as ShaderMaterial).set_shader_parameter(n, v)

# the world point on a pitch's axis at parameter t, corkscrew included. Shared
# with cave_root so a camera can be put down a hole without duplicating it.
func pitch_axis(pi: int, t: float) -> Vector3:
	var pr: PackedInt32Array = topo.pitch(pi)
	var tp := Vector3(float(pr[CaveTopology.P_X]) * CELL,
		float(pr[CaveTopology.P_TOP_MM]) * 0.001, float(pr[CaveTopology.P_Y]) * CELL)
	var foot: PackedInt32Array = _st(pr[CaveTopology.P_TO_ST])
	var bp := Vector3(float(pr[CaveTopology.P_TO_X]) * CELL,
		float(foot[CaveTopology.S_CEIL_MM]) * 0.001, float(pr[CaveTopology.P_TO_Y]) * CELL)
	var hgt: float = tp.y - bp.y
	var c: Vector3 = tp.lerp(bp, t)
	var kind: int = pr[CaveTopology.P_KIND]
	var bore: float = float(pr[CaveTopology.P_BORE_MM]) * 0.001
	if kind == CaveTopology.PK_MOULIN or kind == CaveTopology.PK_COLLAR:
		c += Vector3(cos(t * hgt * 0.22), 0.0, sin(t * hgt * 0.22)) * (bore * 0.32 * sin(t * PI))
	elif kind == CaveTopology.PK_COLLAPSE:
		c += Vector3(sin(t * 2.4) * bore * 0.38, 0.0, cos(t * 1.7) * bore * 0.30)
	return c

func _rock_mat(L: int) -> Material:
	return mat_rock_lv[clampi(L, 0, mat_rock_lv.size() - 1)]

func _ice_mat(L: int) -> Material:
	return mat_ice_lv[clampi(L, 0, mat_ice_lv.size() - 1)]

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
			# WK_STANDWATER used to place an instanced disc. It now raises the
			# wetness the shader sees, and the shader grows the puddle out of
			# the parallax height field where the ground is actually low.
			if (sa[CaveTopology.S_WORKS] & CaveTopology.WK_STANDWATER) != 0:
				wet = maxf(wet, 0.82)
			var dark: float = clampf(float(sa[CaveTopology.S_DEPTH]) / dark_div, 0.0, 1.0)
			var lvl: int = sa[CaveTopology.S_LEVEL]
			var is_ice: bool = sa[CaveTopology.S_MEDIUM] == CaveTopology.MED_ICE
			var is_ior: bool = sa[CaveTopology.S_MEDIUM] == CaveTopology.MED_ICE_OVER_ROCK
			var icep: Vector3 = _ice_params(sa)
			# a conduit that is still running has a channel cut down it; one
			# that froze does not. Above the melt front and wet is the test.
			var chan_hw: float = 0.0
			var chan_d: float = 0.0
			if is_ice and wet > 0.42 and sa[CaveTopology.S_STATE] != CaveTopology.FLOODED:
				chan_hw = minf(0.46, hw * 0.38)
				chan_d = 0.13 + 0.13 * clampf((wet - 0.42) / 0.5, 0.0, 1.0)
			var frac01: float = clampf((float(sa[CaveTopology.S_FRACTURE]) - 3.0) / 11.0, 0.0, 1.0)
			var bed01: float = clampf((float(sa[CaveTopology.S_BEDDING]) - 4.0) / 31.0, 0.0, 1.0)
			var packed: float = floor(frac01 * 31.0) * 32.0 + floor(bed01 * 31.0)
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
				# ICE IS SMOOTH, and this is not only an art choice. THE-ICE 6.2
				# rests on a meltwater conduit having no features to lock a scan
				# onto; a 0.5 m lumpy ice wall would hand the estimator exactly
				# what the design says it cannot have.
				var amp: float = lerp(0.52, 0.155, worked) * floor_mask * (0.30 if is_ice else 1.0)
				var d: float = big * amp + fine * amp * 0.45
				# --- SCALLOPS, IN THE SILHOUETTE ---------------------------
				# 2026-09-10, ICE-CAVE.md. The first pass put scallops in the
				# normal map only, and a lamp that sits ON the eye returns
				# almost no shading contrast from a normal map because N.L
				# equals N.V -- which is the same finding this file already
				# records for bedding, applied to the other material family.
				# The result was a smooth grey tube. So the LOW register of
				# the scallop pattern is now real geometry, in phase with the
				# shader's high register (same period family, same helix
				# constant 1.6, same perimeter coordinate).
				#
				# AND IT DOES NOT BREAK THE SENSOR ARGUMENT. THE-ICE 6.2 needs
				# a conduit to have nothing to LOCK ONTO along its own axis. A
				# strictly periodic form is the degenerate case, not the
				# exception: every scallop looks like every other scallop, so
				# it supplies no landmark and no axial constraint. Lumps would
				# have. This is 75 mm of crescent hollow that reads at three
				# metres and tells an estimator nothing.
				if is_ice:
					var pol: float = icep.x
					var perim: float = (s01 * 0.5 + (0.5 if side < 0.0 else 0.0)) * TAU
					# NYQUIST, AND IT COST A FRAME. The first version of this used
					# the shader's own 0.42 m period and its 1.6 helix constant,
					# which shifts the phase by 4.2 m around a ring that has 40
					# vertices in it -- four vertices per cycle in the perimeter
					# direction and 2.8 along the sweep. The mesh could not
					# carry the pattern and folded it into a set of curtains
					# hanging down the passage that were not objects and that
					# survived --noprops.
					#
					# The geometry carries the LOW register only: 0.70 m axial
					# against a 0.15 m ring pitch (4.7 samples) and a helix slow
					# enough to give ~17 vertices per cycle round the ring. The
					# 0.22 m and 0.075 m registers stay in the shader, where the
					# footprint fade can filter them properly.
					var g1: float = sin((axial + perim * 0.25) * (TAU / 0.70))
					var g1n: float = g1 * 0.5 + 0.5
					d -= pow(1.0 - g1n, 1.5) * 0.100 * pol * (0.35 + 0.65 * floor_mask)
					# a second, longer register: the conduit widens and pinches
					# on a two-metre beat, because the discharge did
					d += sin(axial * (TAU / 2.30) + perim * 0.5) * 0.090 * pol
				# BEDDING AS GEOMETRY, not only as a shader band. A lamp that
				# sits at the eye returns almost no shading contrast from a
				# normal map (N.L equals N.V), so the beds have to be real
				# ledges in the silhouette or they do not read at all.
				var bedp: float = lerp(0.25, 0.60, fposmod(floor(lp.y * 0.7) * 0.37 + 0.31, 1.0))
				# bedding is a property of the ROCK. Ice has no beds.
				var bedg: float = 0.0 if is_ice else (bed01 * floor_mask)
				d += sin(lp.y * TAU / bedp) * 0.030 * bedg
				d -= smoothstep(0.86, 1.0, sin(lp.y * TAU / bedp) * 0.5 + 0.5) * 0.045 * bedg
				lp += outward * d
				# the floor is not flat either: rubble relief under the sweep
				if uv.y < 0.02:
					lp.y += (noise.get_noise_3d(lp.x * 3.1, 7.0, lp.z * 3.1)) * lerp(0.10, 0.022, worked)
				# --- THE MELTWATER CHANNEL ---------------------------------
				# A glacier is water. Where it is still running it has cut a
				# groove down the middle of its own floor, and the groove is
				# the reason an ice passage has a direction to look along. It
				# is a notch in the profile, not a decal, so the water in it
				# (placed in _place_water) sits BELOW the floor either side.
				if chan_hw > 0.0 and uv.y < 0.05:
					var cu: float = absf(uv.x) / chan_hw
					if cu < 1.0:
						lp.y -= chan_d * pow(cos(cu * PI * 0.5), 0.65)
				ring.append(lp)
				# UV2.x is the SIGNED lateral offset from the centreline in
				# metres. The waterline moved into a shader uniform; the floor
				# needed a lateral coordinate so the trammed way and the wheel
				# ruts have somewhere to be.
				if is_ice:
					# same four channels, ice meanings. UV2.x is the FLOW
					# coordinate: along a passage the water ran along it, so
					# the flutes lie down the drive.
					data.append([
						Color(wet, icep.x, dark, icep.z),
						Vector2(axial, s01 * 0.5 + (0.5 if side < 0.0 else 0.0)),
						Vector2(axial, icep.y)
					])
				else:
					data.append([
						Color(wet, worked, dark, iron_base * clampf(1.2 - abs(uv.y - 1.5), 0.0, 1.0)),
						Vector2(axial, s01 * 0.5 + (0.5 if side < 0.0 else 0.0)),
						Vector2(uv.x, packed)
					])
			if prev_ring.size() == RING_VERTS:
				_emit_band(prev_ring, prev_data, ring, data, prev_centre,
					p + Vector3.UP * ht * 0.42,
					_ice_mat(lvl) if is_ice else _rock_mat(lvl))
				# --- THE ICE APRON ------------------------------------------
				# THE-ICE 5.2's second structural claim: "the ice is a FILL,
				# not a layer... a stope with a floor of clear ice over a muck
				# pile you can see and cannot reach". So an ice-over-rock
				# station is a ROCK passage with a body of ice lying in the
				# bottom of it, not an ice passage. Built as a second, inner
				# surface over the lower part of the same ring: the rock is
				# still there, still drawn, and now under something.
				if is_ior:
					var lift: float = 0.22 + 0.30 * icep.z
					var ap0: Array = _apron_ring(prev_ring, prev_data, prev_centre, lift, icep)
					var ap1: Array = _apron_ring(ring, data, p + Vector3.UP * ht * 0.42, lift, icep)
					_emit_strip(ap0[0], ap0[1], ap1[0], ap1[1], prev_centre,
						p + Vector3.UP * ht * 0.42, _ice_mat(lvl), APRON_KS)
			prev_ring = ring
			prev_data = data
			prev_centre = p + Vector3.UP * ht * 0.42
			axial += 0.15

# The k indices an apron covers: up one side from the floor centre, and down
# the other. RING_VERTS is 40 with k = 0 at the floor centre, so this is the
# bottom sixth of the section on both sides, taken as one open strip through
# the wrap rather than as two.
static var APRON_KS: PackedInt32Array = PackedInt32Array([33, 34, 35, 36, 37, 38, 39,
	0, 1, 2, 3, 4, 5, 6, 7])

# lift the lower part of a ring into a body of ice lying in it. The surface is
# nearly level -- water froze standing still -- so it is the shell point
# raised to a plane, pulled in a little where it meets the wall.
func _apron_ring(r: Array, d: Array, ctr: Vector3, lift: float, icep: Vector3) -> Array:
	var out: Array = []
	var od: Array = []
	var y0: float = 1e9
	for k in APRON_KS:
		y0 = minf(y0, (r[k] as Vector3).y)
	for k in APRON_KS:
		var pv: Vector3 = r[k]
		var top: float = y0 + lift
		var q := Vector3(pv.x, maxf(pv.y + 0.02, minf(top, pv.y + lift)), pv.z)
		# a meniscus where it meets the wall, and a slight dome in the middle
		var side_f: float = clampf((top - pv.y) / maxf(lift, 0.01), 0.0, 1.0)
		q.y += 0.035 * side_f
		q.x = lerp(pv.x, ctr.x, 0.02 * side_f)
		q.z = lerp(pv.z, ctr.z, 0.02 * side_f)
		out.append(q)
		# the apron's own ice scalars: it froze standing still, so it is clear
		# and flat and full of what it settled onto
		od.append([Color(0.85, icep.x * 0.5, (d[k][0] as Color).b, icep.z),
			d[k][1], Vector2((d[k][2] as Vector2).x, icep.y)])
	return [out, od]

# an OPEN strip between two partial rings, indexed by an explicit list of k.
# _emit_band closes the loop; an apron must not.
func _emit_strip(r0: Array, d0: Array, r1: Array, d1: Array, c0: Vector3, c1: Vector3,
				 mat: Material, ks: PackedInt32Array) -> void:
	var n: int = r0.size()
	if n < 2:
		return
	var mid: Vector3 = ((r0[0] as Vector3) + (r1[0] as Vector3)) * 0.5
	var c: Dictionary = _chunk(mid)
	var mb: MB = c["shell"]
	var v := PackedVector3Array()
	var cc := PackedColorArray()
	var uu := PackedVector2Array()
	var u2 := PackedVector2Array()
	var idx := PackedInt32Array()
	for k in range(n):
		v.push_back(r0[k]); cc.push_back(d0[k][0]); uu.push_back(d0[k][1]); u2.push_back(d0[k][2])
	for k in range(n):
		v.push_back(r1[k]); cc.push_back(d1[k][0]); uu.push_back(d1[k][1]); u2.push_back(d1[k][2])
	for k in range(n - 1):
		var k2: int = k + 1
		idx.push_back(k); idx.push_back(n + k); idx.push_back(k2)
		idx.push_back(k2); idx.push_back(n + k); idx.push_back(n + k2)
	var nn: PackedVector3Array = _recalc_normals(v, idx)
	# an apron is seen from ABOVE: point every normal up
	for i in range(nn.size()):
		if nn[i].y < 0.0:
			nn[i] = -nn[i]
	mb.add_arrays(mat, v, nn, cc, uu, u2, idx, Transform3D.IDENTITY)

func _catmull(p0: Vector3, p1: Vector3, p2: Vector3, p3: Vector3, t: float) -> Vector3:
	var t2: float = t * t
	var t3: float = t2 * t
	return 0.5 * ((2.0 * p1) + (-p0 + p2) * t + (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * t2
		+ (-p0 + 3.0 * p1 - 3.0 * p2 + p3) * t3)

func _emit_band(r0: Array, d0: Array, r1: Array, d1: Array, c0: Vector3, c1: Vector3,
				mat: Material = null) -> void:
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
	mb.add_arrays(mat if mat != null else mat_rock, v, nn, cc, uu, u2, idx, Transform3D.IDENTITY)

# --- chambers: a noise-displaced dome dropped over the station -------------
# 2026-09-10: a chamber can now have a HOLE IN ITS FLOOR (a pitch is sunk from
# it) and a HOLE IN ITS BACK (a pitch lands in it through the ceiling). That is
# what "things below other things" costs in geometry, and it is two skipped
# index ranges plus one skirt.
func _build_chambers() -> void:
	var nrow: int = topo.chambers.size() / CaveTopology.CH_ROW
	for ci in range(nrow):
		var sid: int = topo.chambers[ci * CaveTopology.CH_ROW + CaveTopology.CH_SID]
		var r: float = float(topo.chambers[ci * CaveTopology.CH_ROW + CaveTopology.CH_R]) * CELL + 1.6
		var p: Vector3 = _st_pos(sid)
		var s: PackedInt32Array = _st(sid)
		var lvl: int = s[CaveTopology.S_LEVEL]
		var ht: float = _ht(s) * 1.25
		var worked: float = float(s[CaveTopology.S_WORKED]) / 255.0
		var wet: float = float(s[CaveTopology.S_WET]) / 255.0
		var dark: float = clampf(float(s[CaveTopology.S_DEPTH]) / dark_div, 0.0, 1.0)
		var frac01: float = clampf((float(s[CaveTopology.S_FRACTURE]) - 3.0) / 11.0, 0.0, 1.0)
		var bed01: float = clampf((float(s[CaveTopology.S_BEDDING]) - 4.0) / 31.0, 0.0, 1.0)
		var packed: float = floor(frac01 * 31.0) * 32.0 + floor(bed01 * 31.0)
		var is_ice: bool = s[CaveTopology.S_MEDIUM] == CaveTopology.MED_ICE
		var mat: Material = _ice_mat(lvl) if is_ice else _rock_mat(lvl)
		var icep: Vector3 = _ice_params(s)
		# the two holes, as radii in metres
		var hole_floor: float = 0.0
		var hole_back: float = 0.0
		if s[CaveTopology.S_PITCH_HEAD] >= 0:
			hole_floor = float(topo.pitch(s[CaveTopology.S_PITCH_HEAD])[CaveTopology.P_BORE_MM]) * 0.0005
		if s[CaveTopology.S_PITCH_FOOT] >= 0:
			hole_back = float(topo.pitch(s[CaveTopology.S_PITCH_FOOT])[CaveTopology.P_BORE_MM]) * 0.0005 + 0.60
		var RINGS: int = 9
		var SEG: int = 26
		var rows: Array = []
		var nominal: PackedFloat32Array = PackedFloat32Array()
		for a in range(RINGS + 1):
			var ph: float = float(a) / float(RINGS) * (PI * 0.5)
			var row: Array = []
			nominal.push_back(r * cos(ph))
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
		# the highest dome row we keep. Above it is the hole the pitch came
		# down through; _pitch_skirt closes the join.
		var top_row: int = RINGS
		if hole_back > 0.0:
			for a2 in range(RINGS + 1):
				if nominal[a2] < hole_back:
					top_row = maxi(1, a2 - 1)
					break
		for a3 in range(top_row):
			for b2 in range(SEG):
				var b3: int = (b2 + 1) % SEG
				var q0: Vector3 = rows[a3][b2]
				var q1: Vector3 = rows[a3][b3]
				var q2: Vector3 = rows[a3 + 1][b2]
				var q3: Vector3 = rows[a3 + 1][b3]
				var v := PackedVector3Array([q0, q1, q2, q3])
				var idx := PackedInt32Array([0, 2, 1, 1, 2, 3])
				var cc := PackedColorArray()
				var uu := PackedVector2Array()
				var u2 := PackedVector2Array()
				for w in range(4):
					if is_ice:
						cc.push_back(Color(wet, icep.x, dark, icep.z))
						uu.push_back(Vector2(v[w].x, float(b2) / float(SEG)))
						u2.push_back(Vector2(v[w].y, icep.y))
					else:
						cc.push_back(Color(wet, worked, dark, 0.15))
						uu.push_back(Vector2(v[w].x, float(b2) / float(SEG)))
						u2.push_back(Vector2(6.0, packed))
				var nn: PackedVector3Array = _recalc_normals(v, idx)
				var ctr: Vector3 = p + Vector3.UP * (ht * 0.35)
				for w2 in range(4):
					if nn[w2].dot(ctr - v[w2]) < 0.0:
						nn[w2] = -nn[w2]
				var mid: Vector3 = (q0 + q3) * 0.5
				var mb: MB = _chunk(mid)["shell"]
				mb.add_arrays(mat, v, nn, cc, uu, u2, idx, Transform3D.IDENTITY)
		# --- the floor. A fan, unless a pitch is sunk from it, in which case it
		# is an ANNULUS and the hole in the middle of it is the whole point.
		var fv := PackedVector3Array()
		var fi := PackedInt32Array()
		var fc := PackedColorArray()
		var fu := PackedVector2Array()
		var fu2 := PackedVector2Array()
		var fcol: Color = Color(wet, icep.x, dark, icep.z) if is_ice else Color(wet, worked, dark, 0.1)
		var fuv2: Vector2 = Vector2(p.y, icep.y) if is_ice else Vector2(6.0, packed)
		if hole_floor > 0.01:
			for b4 in range(SEG):
				var th3: float = float(b4) / float(SEG) * TAU
				fv.push_back(Vector3(p.x + cos(th3) * hole_floor, p.y, p.z + sin(th3) * hole_floor))
				fc.push_back(fcol)
				fu.push_back(Vector2(p.x, float(b4) / float(SEG)))
				fu2.push_back(fuv2)
			for b5 in range(SEG):
				var lpo: Vector3 = rows[0][b5]
				fv.push_back(lpo)
				fc.push_back(fcol)
				fu.push_back(Vector2(lpo.x, float(b5) / float(SEG)))
				fu2.push_back(fuv2)
			for b6 in range(SEG):
				var b7: int = (b6 + 1) % SEG
				fi.push_back(b6); fi.push_back(SEG + b6); fi.push_back(b7)
				fi.push_back(b7); fi.push_back(SEG + b6); fi.push_back(SEG + b7)
		else:
			fv.push_back(p)
			fc.push_back(fcol)
			fu.push_back(Vector2(p.x, 0.0))
			fu2.push_back(fuv2)
			for b8 in range(SEG + 1):
				var lp2: Vector3 = rows[0][b8 % SEG]
				fv.push_back(lp2)
				fc.push_back(fcol)
				fu.push_back(Vector2(lp2.x, float(b8) / float(SEG)))
				fu2.push_back(fuv2)
			for b9 in range(SEG):
				fi.push_back(0); fi.push_back(b9 + 1); fi.push_back(((b9 + 1) % SEG) + 1)
		var fn: PackedVector3Array = PackedVector3Array()
		fn.resize(fv.size())
		for w3 in range(fv.size()):
			fn[w3] = Vector3.UP
		_chunk(p)["shell"].add_arrays(mat, fv, fn, fc, fu, fu2, fi, Transform3D.IDENTITY)

# ===========================================================================
# PITCHES -- THE SECOND PROFILE FAMILY
# ===========================================================================
# THE-ICE 5.3, on what the built cave costs above the seam: "_half_profile()
# builds a floor, two legs and a crown, which a vertical shaft is not. A moulin
# needs a SECOND PROFILE FAMILY beside the sweep, not a modification of it."
#
# This is that family, and the two really are different functions rather than
# one function with a flag:
#
#   passage   an OPEN half-section (floor centre -> crown) mirrored about a
#             vertical and swept along a horizontal spine, oriented by a
#             tangent and a right vector. It cannot close over itself.
#   pitch     a CLOSED ring in the HORIZONTAL plane swept down an axis that is
#             allowed to corkscrew. No floor, no legs, no crown, and its
#             perimeter coordinate is an angle rather than an arc up from the
#             floor.
#
# Six kinds share it and each is a different RADIUS FUNCTION, not a different
# parameter: a winze is square-set, a crevasse is a slot, an aven bells out
# upward, a collapse is broken, a moulin is fluted, and a collar is a moulin
# with the ancients' rings still in it.
func _sweep_pitches() -> void:
	for pi in range(topo.pitches.size()):
		_sweep_pitch(pi)

func _pitch_radius(kind: int, bore: float, th: float, t: float, hgt: float) -> float:
	if kind == CaveTopology.PK_WINZE or kind == CaveTopology.PK_ORE_PASS:
		# square-set: four timbered sides, so the section is a rounded square
		var c: float = absf(cos(th))
		var sn: float = absf(sin(th))
		return bore * 0.5 / maxf(0.62, pow(pow(c, 8.0) + pow(sn, 8.0), 0.125))
	if kind == CaveTopology.PK_CREVASSE:
		# a slot: wide one way, a hand's width the other
		var ex: float = cos(th)
		var ez: float = sin(th) / 4.2
		return bore * 0.5 / maxf(0.12, sqrt(ex * ex + ez * ez))
	if kind == CaveTopology.PK_AVEN:
		return bore * 0.5 * (0.72 + 0.55 * (1.0 - t))
	if kind == CaveTopology.PK_COLLAPSE:
		return bore * 0.5 * (0.80 + 0.34 * sin(th * 2.0 + t * 5.0))
	return bore * 0.5 * (1.0 + 0.13 * sin(th * 3.0 + t * hgt * 0.55))

func _sweep_pitch(pi: int) -> void:
	var pr: PackedInt32Array = topo.pitch(pi)
	var kind: int = pr[CaveTopology.P_KIND]
	var bore: float = float(pr[CaveTopology.P_BORE_MM]) * 0.001
	var top_y: float = float(pr[CaveTopology.P_TOP_MM]) * 0.001
	var foot: PackedInt32Array = _st(pr[CaveTopology.P_TO_ST])
	# the tube stops at the BACK of the chamber it lands in. A shaft breaking
	# into a level comes through the ceiling; it does not grow out of the floor.
	var bot_y: float = float(foot[CaveTopology.S_CEIL_MM]) * 0.001
	var top_p := Vector3(float(pr[CaveTopology.P_X]) * CELL, top_y, float(pr[CaveTopology.P_Y]) * CELL)
	var bot_p := Vector3(float(pr[CaveTopology.P_TO_X]) * CELL, bot_y, float(pr[CaveTopology.P_TO_Y]) * CELL)
	var hgt: float = top_y - bot_y
	if hgt < 0.8:
		return
	var nr: int = maxi(8, int(hgt / 0.55))
	var lvl: int = pr[CaveTopology.P_FROM_LEVEL]
	var flow: float = float(pr[CaveTopology.P_FLOW]) / 255.0
	var ice_base: float = float(CaveTopology.BAND_ICE_BASE_MM) * 0.001
	var meltm: float = float(topo.melt_mm) * 0.001
	var worked_pitch: bool = kind == CaveTopology.PK_WINZE or kind == CaveTopology.PK_ORE_PASS
	var pf01: float = clampf((float(foot[CaveTopology.S_FRACTURE]) - 3.0) / 11.0, 0.0, 1.0)
	var pb01: float = clampf((float(foot[CaveTopology.S_BEDDING]) - 4.0) / 31.0, 0.0, 1.0)
	var packed: float = floor(pf01 * 31.0) * 32.0 + floor(pb01 * 31.0)
	var worked: float = float(foot[CaveTopology.S_WORKED]) / 255.0
	var dark: float = clampf(float(foot[CaveTopology.S_DEPTH]) / dark_div, 0.0, 1.0)
	# the ice scalars of a pitch, per kind
	var pol: float = 0.45
	var cla: float = 0.55
	var deb: float = 0.35
	if kind == CaveTopology.PK_MOULIN or kind == CaveTopology.PK_COLLAR:
		pol = 0.93
		cla = 0.84
		deb = 0.10
	elif kind == CaveTopology.PK_CREVASSE:
		pol = 0.72
		cla = 0.90
		deb = 0.06
	elif kind == CaveTopology.PK_COLLAPSE:
		pol = 0.18
		cla = 0.22
		deb = 0.72
	var prev_ring: Array = []
	var prev_data: Array = []
	var prev_c: Vector3 = Vector3.ZERO
	var prev_ice: bool = false
	var bottom_ring: Array = []
	for i in range(nr + 1):
		var t: float = float(i) / float(nr)
		var c: Vector3 = top_p.lerp(bot_p, t)
		# the axis wanders. A moulin CORKSCREWS -- that is what falling water
		# does to a hole in ice -- and a collapse leans.
		if kind == CaveTopology.PK_MOULIN or kind == CaveTopology.PK_COLLAR:
			var aa: float = t * hgt * 0.22
			var amp: float = bore * 0.32 * sin(t * PI)
			c += Vector3(cos(aa) * amp, 0.0, sin(aa) * amp)
		elif kind == CaveTopology.PK_COLLAPSE:
			c += Vector3(sin(t * 2.4) * bore * 0.38, 0.0, cos(t * 1.7) * bore * 0.30)
		var y: float = c.y
		var is_ice: bool = (not worked_pitch) and y > ice_base
		if kind == CaveTopology.PK_CREVASSE:
			is_ice = true
		# the ends are CLEAN so they meet the floor annulus and the skirt
		var ends: float = smoothstep(0.0, 0.055, t) * smoothstep(0.0, 0.055, 1.0 - t)
		var wetv: float = clampf(0.35 + flow * 0.6, 0.0, 1.0) if y > meltm else 0.10
		var ring: Array = []
		var data: Array = []
		for k in range(RING_VERTS):
			var th: float = float(k) / float(RING_VERTS) * TAU
			var rr: float = _pitch_radius(kind, bore, th, t, hgt)
			var ax: float = cos(th)
			var az: float = sin(th)
			var lp := Vector3(c.x + ax * rr, y, c.z + az * rr)
			var nlo: float = noise_lo.get_noise_3d(lp.x * 0.9, lp.y * 0.35, lp.z * 0.9)
			var nhi: float = noise.get_noise_3d(lp.x * 2.4, lp.y * 1.1, lp.z * 2.4)
			var amp2: float = (0.10 if is_ice else 0.30) * bore * ends
			if kind == CaveTopology.PK_COLLAPSE:
				amp2 = 0.55 * bore * ends
			lp += Vector3(ax, 0.0, az) * (nlo * amp2 + nhi * amp2 * 0.4)
			ring.append(lp)
			if is_ice:
				# UV2.x is the FLOW COORDINATE, and in a pitch it is the
				# ELEVATION, so the flutes run DOWN the bore rather than round
				# it. That one line is why a moulin does not look like a
				# passage stood on end.
				data.append([Color(wetv, pol, dark, deb),
					Vector2(t * hgt, float(k) / float(RING_VERTS)),
					Vector2(y, cla)])
			else:
				data.append([Color(wetv, worked, dark, 0.35 if worked_pitch else 0.05),
					Vector2(t * hgt, float(k) / float(RING_VERTS)),
					Vector2(ax * rr, packed)])
		if prev_ring.size() == RING_VERTS:
			_emit_band(prev_ring, prev_data, ring, data, prev_c, c,
				_ice_mat(lvl) if prev_ice else _rock_mat(lvl))
		prev_ring = ring
		prev_data = data
		prev_c = c
		prev_ice = is_ice
		bottom_ring = ring
		var ch: Dictionary = _chunk(c)
		ch["pitch"] = true
		_chunk(ring[0])["pitch"] = true
		_chunk(ring[RING_VERTS / 2])["pitch"] = true
	# --- the skirt that closes the join into the chamber below --------------
	_pitch_skirt(bot_p, bore * 0.5 + 0.60, bottom_ring, lvl, worked, dark, packed)
	_pitch_props(pi, pr, top_p, bot_p, bore, hgt, nr, flow)

func _pitch_skirt(c: Vector3, outer: float, ring: Array, lvl: int, worked: float,
				  dark: float, packed: float) -> void:
	if ring.size() != RING_VERTS:
		return
	var v := PackedVector3Array()
	var cc := PackedColorArray()
	var uu := PackedVector2Array()
	var u2 := PackedVector2Array()
	var idx := PackedInt32Array()
	for k in range(RING_VERTS):
		var th: float = float(k) / float(RING_VERTS) * TAU
		v.push_back(ring[k])
		v.push_back(Vector3(c.x + cos(th) * outer, c.y - 0.34, c.z + sin(th) * outer))
	for k2 in range(RING_VERTS):
		var a: int = k2 * 2
		var b: int = ((k2 + 1) % RING_VERTS) * 2
		idx.push_back(a); idx.push_back(a + 1); idx.push_back(b)
		idx.push_back(b); idx.push_back(a + 1); idx.push_back(b + 1)
	for i in range(v.size()):
		cc.push_back(Color(0.5, worked, dark, 0.2))
		uu.push_back(Vector2(v[i].x, 0.0))
		u2.push_back(Vector2(3.0, packed))
	var nn: PackedVector3Array = _recalc_normals(v, idx)
	for i2 in range(nn.size()):
		if nn[i2].dot(c - v[i2]) < 0.0:
			nn[i2] = -nn[i2]
	_chunk(c)["shell"].add_arrays(_rock_mat(lvl), v, nn, cc, uu, u2, idx, Transform3D.IDENTITY)

# --- what is IN a pitch ----------------------------------------------------
# The ancients' rings where they left steel; the players' beacon chain going
# DOWN, which is ART-DIRECTION 6.3's "the most beautiful image in the game"
# rotated ninety degrees; the meltwater; and the cone of rubble at the bottom
# that is everything the hole has ever dropped.
func _pitch_props(pi: int, pr: PackedInt32Array, top_p: Vector3, bot_p: Vector3,
				  bore: float, hgt: float, nr: int, flow: float) -> void:
	var kind: int = pr[CaveTopology.P_KIND]
	var flags: int = pr[CaveTopology.P_FLAGS]
	var meltm: float = float(topo.melt_mm) * 0.001
	var curly: bool = kind == CaveTopology.PK_MOULIN or kind == CaveTopology.PK_COLLAR
	if (flags & CaveTopology.PF_FIXED) != 0:
		var nring: int = maxi(2, int(hgt / 1.2))
		for i in range(1, nring):
			var t: float = float(i) / float(nring)
			var q: Vector3 = top_p.lerp(bot_p, t)
			if curly:
				q += Vector3(cos(t * hgt * 0.22), 0.0, sin(t * hgt * 0.22)) * (bore * 0.32 * sin(t * PI))
			var sc: float = bore * 0.5 * 0.97
			_prop(q, "collarring", Transform3D(Basis.from_euler(Vector3(0, t * 0.4, 0))
				* Basis.from_scale(Vector3(sc, 1.0, sc)), q))
	# A BEACON AT THE HEAD AND THE FOOT OF EVERY PITCH A MACHINE CAN GO DOWN.
	# The players mark a route they intend to come back along, and a drop is
	# the one place on a route where being wrong is not recoverable. It is also
	# the only thing that makes a shaft photograph: the lamp reaches about six
	# metres on a floor and a shaft has no floor to reach.
	if (flags & CaveTopology.PF_DOWN) != 0:
		var hb: Vector3 = top_p + Vector3(bore * 0.62, 0.02, bore * 0.30)
		_prop(hb, "beacon", _xf(hb, Vector3(0, 2.1, 0)))
		lights.append(hb + Vector3.UP * 0.56)
		var fb2: Vector3 = _st_pos(pr[CaveTopology.P_TO_ST]) + Vector3(bore * 0.75, 0.02, -bore * 0.4)
		_prop(fb2, "beacon", _xf(fb2, Vector3(0, 0.7, 0)))
		lights.append(fb2 + Vector3.UP * 0.56)
	if (flags & CaveTopology.PF_MAIN) != 0:
		# ART-DIRECTION 6.3 calls a beacon chain receding down a drive the most
		# beautiful image in the game. Rotated ninety degrees it is also the
		# ONLY thing that makes a shaft read as deep rather than as black: the
		# lamp reaches about six metres on a floor and a shaft has no floor.
		var nbe: int = maxi(2, int(hgt / 3.2))
		for i2 in range(nbe):
			var t2: float = (float(i2) + 0.5) / float(nbe)
			var q2: Vector3 = top_p.lerp(bot_p, t2)
			if curly:
				q2 += Vector3(cos(t2 * hgt * 0.22), 0.0, sin(t2 * hgt * 0.22)) * (bore * 0.32 * sin(t2 * PI))
			var ang: float = t2 * 3.1
			var rr: float = _pitch_radius(kind, bore, ang, t2, hgt) - 0.20
			q2 += Vector3(cos(ang) * rr, 0.0, sin(ang) * rr)
			_prop(q2, "beacon", _xf(q2, Vector3(0, ang, 0)))
			lights.append(q2 + Vector3.UP * 0.30)
	# the meltwater: a ribbon down the flutes, not a column. What runs down a
	# moulin clings to the wall until it does not.
	if flow > 0.02 and top_p.y > meltm:
		var v := PackedVector3Array()
		var idx := PackedInt32Array()
		var n2: int = maxi(6, nr / 2)
		for i3 in range(n2 + 1):
			var t3: float = float(i3) / float(n2)
			var q3: Vector3 = top_p.lerp(bot_p, t3)
			if curly:
				q3 += Vector3(cos(t3 * hgt * 0.22), 0.0, sin(t3 * hgt * 0.22)) * (bore * 0.32 * sin(t3 * PI))
			var ang3: float = 0.9 + t3 * hgt * 0.26
			var rr3: float = _pitch_radius(kind, bore, ang3, t3, hgt) - 0.06
			var e0 := Vector3(cos(ang3), 0.0, sin(ang3))
			var e1 := Vector3(-sin(ang3), 0.0, cos(ang3))
			v.push_back(q3 + e0 * rr3 - e1 * (0.10 + 0.24 * flow))
			v.push_back(q3 + e0 * rr3 + e1 * (0.10 + 0.24 * flow))
		for i4 in range(n2):
			var a2: int = i4 * 2
			idx.push_back(a2); idx.push_back(a2 + 1); idx.push_back(a2 + 2)
			idx.push_back(a2 + 2); idx.push_back(a2 + 1); idx.push_back(a2 + 3)
		var cc := PackedColorArray()
		var uu := PackedVector2Array()
		for i5 in range(v.size()):
			cc.push_back(Color(1, 1, 1, 1))
			uu.push_back(Vector2(v[i5].y, float(i5 % 2)))
		var nn: PackedVector3Array = _recalc_normals(v, idx)
		for i6 in range(nn.size()):
			var axis := Vector3(top_p.x, v[i6].y, top_p.z)
			if nn[i6].dot(axis - v[i6]) < 0.0:
				nn[i6] = -nn[i6]
		_chunk(top_p.lerp(bot_p, 0.5))["shell"].add_arrays(mat_water, v, nn, cc, uu,
			PackedVector2Array(), idx, Transform3D.IDENTITY)
	# --- THE ICE IN THE BORE ----------------------------------------------
	# VERTICAL.md 6 reports that three of its ten photographed frames were
	# "a hole with nothing in it", and diagnoses it as the mechanic: a shaft
	# has no floor for the lamp to find. Half of that is true and half of it
	# was a missing object. A shaft in ICE is not empty: the lip is fringed,
	# the bore is ribbed where the water ran and stopped, and one side of a
	# moulin is a frozen waterfall thirty metres long. All three are things
	# the lamp CAN find, because they stand off the wall into the bore.
	var icy_bore: bool = top_p.y > float(CaveTopology.BAND_ICE_BASE_MM) * 0.001 	and kind != CaveTopology.PK_WINZE and kind != CaveTopology.PK_ORE_PASS
	if icy_bore:
		# the fringe round the lip. A hole in ice always has one, and it is
		# what makes the EDGE of the hole read from above.
		var nlip: int = maxi(6, int(bore * 9.0))
		for il in range(nlip):
			var al: float = float(il) / float(nlip) * TAU + rng.randf_range(-0.12, 0.12)
			var rl: float = _pitch_radius(kind, bore, al, 0.0, hgt) * rng.randf_range(0.80, 0.97)
			var ql := Vector3(top_p.x + cos(al) * rl, top_p.y - 0.03, top_p.z + sin(al) * rl)
			var lnl: float = rng.randf_range(0.20, 0.85)
			_prop(ql, "icefringe%d" % (il % 2), Transform3D(
				Basis.from_euler(Vector3(0, al + PI * 0.5, 0))
				* Basis.from_scale(Vector3(rng.randf_range(0.35, 0.75), lnl, 0.5)), ql))
		# ribs down the bore: the rhythm VERTICAL.md 3.4 says the rings give a
		# worked shaft, in the medium that has no rings
		var nrib: int = maxi(3, int(hgt / 1.6))
		for ir in range(nrib):
			var tr: float = (float(ir) + 0.35) / float(nrib)
			var qr: Vector3 = top_p.lerp(bot_p, tr)
			if curly:
				qr += Vector3(cos(tr * hgt * 0.22), 0.0, sin(tr * hgt * 0.22)) * (bore * 0.32 * sin(tr * PI))
			var ar: float = rng.randf() * TAU
			var rr4: float = _pitch_radius(kind, bore, ar, tr, hgt) - 0.05
			var qq := Vector3(qr.x + cos(ar) * rr4, qr.y, qr.z + sin(ar) * rr4)
			_prop(qq, "icerib", Transform3D(_face(Vector3(-cos(ar), 0.0, -sin(ar)))
				* Basis.from_scale(Vector3(1.0, rng.randf_range(0.7, 1.6), 1.0)), qq))
		# THE FROZEN WATERFALL down one side of the moulin. Where the flow is
		# and where the melt front is not: what ran, and then stopped.
		if curly and hgt > 5.0:
			var nfl: int = int(hgt / 1.1)
			var a5: float = 0.9 + PI
			for jf in range(nfl):
				var t5: float = (float(jf) + 0.5) / float(nfl)
				var q5: Vector3 = top_p.lerp(bot_p, t5)
				q5 += Vector3(cos(t5 * hgt * 0.22), 0.0, sin(t5 * hgt * 0.22)) * (bore * 0.32 * sin(t5 * PI))
				var a6: float = a5 + t5 * hgt * 0.26
				var r6: float = _pitch_radius(kind, bore, a6, t5, hgt) - 0.04
				var q6 := Vector3(q5.x + cos(a6) * r6, q5.y + 1.15, q5.z + sin(a6) * r6)
				_prop(q6, "icefall", Transform3D(_face(Vector3(-cos(a6), 0.0, -sin(a6)))
					* Basis.from_scale(Vector3(0.62, 1.25, 0.85)), q6))
	# the cone of rubble under it. Everything the hole has ever dropped.
	var foot: PackedInt32Array = _st(pr[CaveTopology.P_TO_ST])
	var fp: Vector3 = _st_pos(pr[CaveTopology.P_TO_ST])
	var nst: int = 26 + int(bore * 14.0)
	var cone_r: float = bore * 0.62 + 0.45
	var cone_icy: bool = _st(pr[CaveTopology.P_TO_ST])[CaveTopology.S_MEDIUM] == CaveTopology.MED_ICE 		or icy_bore
	for i7 in range(nst):
		var ang4: float = rng.randf() * TAU
		var rad: float = sqrt(rng.randf()) * cone_r
		var q4 := Vector3(fp.x + cos(ang4) * rad, fp.y, fp.z + sin(ang4) * rad)
		q4.y += _floor_y(q4, float(foot[CaveTopology.S_WORKED]) / 255.0)
		q4.y += maxf(0.0, 1.0 - rad / cone_r) * 0.22
		# a hole in ice drops ICE. Half the cone under a moulin is the roof of
		# the moulin, and it is the one place in the cave with broken ice in it.
		if cone_icy and i7 % 2 == 0:
			_prop(q4, "iceblock%d" % (rng.randi() % 3), _xf(q4, Vector3(rng.randf() * TAU,
				rng.randf() * TAU, rng.randf() * TAU), Vector3.ONE * rng.randf_range(0.7, 1.5)))
		elif i7 % 9 == 0:
			_prop(q4, "block%d" % (rng.randi() % 3), _xf(q4, Vector3(rng.randf() * TAU,
				rng.randf() * TAU, rng.randf() * TAU)))
		else:
			_prop(q4, "stone%d" % (rng.randi() % 4), _xf(q4, Vector3(rng.randf() * TAU,
				rng.randf() * TAU, rng.randf() * TAU)))

# ===========================================================================
# THE ASSAYER'S SITE
# ===========================================================================
# The designer, 2026-09-10: "it should end with the dog finding something
# massive and bright and scary in there."
#
# WHERE IT STANDS, and this is a fiction decision rather than a placement one.
# THE-ICE 5.2's band table puts the ancients at -80 m and below and says band 0
# has "none. This band is below the ancients' surface works and above their
# workings". Standing an Assayer in the ice band contradicts that table, and I
# am doing it on instruction -- but there is a reading in THE-ICE itself that
# makes it consistent rather than an exception, and it is the SECOND STRUCTURAL
# CLAIM of the same section:
#
#     "The ice is a FILL, not a layer. The glacier pushed into the openings it
#      found."
#
# So the machine was here first and the ice came into the chamber around it.
# Its footing is frozen in, there is a floor of clear ice over the muck it is
# standing on, and the meltwater that runs off it is the same meltwater that
# turns its wheel. That is why it is still running: THE-ICE 4 -- "it started
# again" -- with the mechanism visible in the same frame as the machine.
#
# It is flagged in ICE-CAVE.md as a change to a table the designer's ruling
# overrides, not as a thing I invented.
#
# WHICH CHAMBER. The largest chamber on level 0, chosen deterministically from
# the topology so cave_root.gd and dressing.gd agree without passing anything.
# It needs 6.6 m of mast air; a K_CHAMBER at WC_HALL gives a dome of
# _ht * 1.25 = 8.4 m, so the mast clears with 1.8 m over it -- tight, and tight
# is the point: the reveal of its height has to be a moment.
func assayer_chamber() -> int:
	# THREE CONDITIONS, and the first two were learned by putting a camera
	# somewhere there was no room to stand:
	#   1. ON LEVEL 0's MAIN DRIVE. _add_pitch() calls _force_chamber(), so
	#      several chambers are pitch heads and feet on crosscuts rather than
	#      rooms on the drive. A camera posed against the drive tangent at one
	#      of those is inside the wall, which is exactly what the first ten
	#      assayer frames photographed.
	#   2. NO PITCH IN IT. A chamber with a hole in its floor is not a place to
	#      stand a 6.6 m machine.
	#   3. THE BIGGEST, and furthest along on a tie -- the machine is at the END
	#      of the ice, which is where a viewer will have earned it.
	if topo.level_main_edge.size() == 0:
		return -1
	var ids: PackedInt32Array = topo.edges[topo.level_main_edge[0]]
	var nrow: int = topo.chambers.size() / CaveTopology.CH_ROW
	var best: int = -1
	var best_key: int = -1
	for ci in range(nrow):
		if topo.chambers[ci * CaveTopology.CH_ROW + CaveTopology.CH_LEVEL] != 0:
			continue
		var sid: int = topo.chambers[ci * CaveTopology.CH_ROW + CaveTopology.CH_SID]
		var at: int = -1
		for i in range(ids.size()):
			if ids[i] == sid:
				at = i
				break
		if at < 4 or at > ids.size() - 5:
			continue
		var st: PackedInt32Array = _st(sid)
		if st[CaveTopology.S_PITCH_HEAD] >= 0 or st[CaveTopology.S_PITCH_FOOT] >= 0:
			continue
		var r: int = topo.chambers[ci * CaveTopology.CH_ROW + CaveTopology.CH_R]
		var key: int = r * 1000 + at
		if key > best_key:
			best_key = key
			best = ci
	return best

func assayer_pos() -> Vector3:
	var ci: int = assayer_chamber()
	if ci < 0:
		return Vector3.ZERO
	var sid: int = topo.chambers[ci * CaveTopology.CH_ROW + CaveTopology.CH_SID]
	var q: Vector3 = _st_pos(sid)
	return q

func assayer_radius() -> float:
	var ci: int = assayer_chamber()
	if ci < 0:
		return 5.0
	return float(topo.chambers[ci * CaveTopology.CH_ROW + CaveTopology.CH_R]) * CELL + 1.6

# The footing frozen in, and a floor of ice over what it is standing on.
# Everything here is inside PAD_R (1.56 m) plus a metre, so it reads as the ice
# having come UP the machine rather than as scenery near it.
func _asy_site_frame(sid: int) -> Array:
	var ids: PackedInt32Array = topo.edges[topo.level_main_edge[0]]
	var at: int = 0
	for i in range(ids.size()):
		if ids[i] == sid:
			at = i
			break
	var a: Vector3 = _st_pos(ids[maxi(0, at - 1)])
	var b: Vector3 = _st_pos(ids[mini(ids.size() - 1, at + 1)])
	var tg: Vector3 = (b - a).normalized()
	if tg.length() < 0.5:
		tg = Vector3(1, 0, 0)
	return [tg, tg.cross(Vector3.UP).normalized()]

func _dress_assayer_site() -> void:
	if topo.levels <= 1:
		return
	var ci: int = assayer_chamber()
	if ci < 0:
		return
	var sid: int = topo.chambers[ci * CaveTopology.CH_ROW + CaveTopology.CH_SID]
	var p: Vector3 = _st_pos(sid)
	var R: float = assayer_radius()
	# the floor of clear ice it is standing in. Four overlapping lids so the
	# sheet is not a square, laid just under the anchor pads.
	for k in range(5):
		var a: float = TAU * float(k) / 5.0 + 0.3
		var rr: float = 1.1 + float(k % 2) * 0.7
		var q: Vector3 = p + Vector3(cos(a) * rr, 0.0, sin(a) * rr)
		q.y += _floor_y(q, 0.0) + 0.055
		_prop(q, "icelid", _xf(q, Vector3(0, a * 0.7, 0),
			Vector3(2.2 + float(k) * 0.25, 1.0, 1.9 + float(k) * 0.2)))
	# ice grown up the anchor pads: bosses ON the footing, not beside it
	for k in range(14):
		var a2: float = TAU * float(k) / 14.0 + 0.17
		var rr2: float = 1.35 + rng.randf_range(-0.30, 0.55)
		var q2: Vector3 = p + Vector3(cos(a2) * rr2, 0.0, sin(a2) * rr2)
		q2.y += _floor_y(q2, 0.0) - 0.02
		var h: float = rng.randf_range(0.16, 0.46)
		_prop(q2, "iceboss%d" % (k % 2), _xf(q2, Vector3(0, rng.randf() * TAU, 0),
			Vector3(h * 3.4, h, h * 3.4)))
	# broken ice at the foot: what the roof of the chamber has shed onto it
	for k in range(22):
		var a3: float = rng.randf() * TAU
		var rr3: float = 1.7 + sqrt(rng.randf()) * (R * 0.55)
		var q3: Vector3 = p + Vector3(cos(a3) * rr3, 0.0, sin(a3) * rr3)
		q3.y += _floor_y(q3, 0.0) - 0.03
		_prop(q3, "iceblock%d" % (rng.randi() % 3), _xf(q3,
			Vector3(rng.randf() * TAU, rng.randf() * TAU, rng.randf() * TAU),
			Vector3.ONE * rng.randf_range(0.8, 1.8)))
	# and the chamber wall behind it: three frozen falls at the back of the
	# dome, so the machine is silhouetted against ice rather than against black
	# ... but NOT across the drive. A 2 m wide curtain on the chamber wall is
	# 2 m of wall the camera has to come through, and the drive enters the dome
	# on two opposite sides. These sit on the four quarters between them.
	var f0: Array = _asy_site_frame(sid)
	var tgv: Vector3 = f0[0]
	for k in range(4):
		var a4: float = TAU * (float(k) + 0.5) / 4.0
		var dirv: Vector3 = (tgv * cos(a4) + (f0[1] as Vector3) * sin(a4)).normalized()
		var q4: Vector3 = p + dirv * (R * 0.90)
		q4.y += 3.4
		_prop(q4, "icefall", Transform3D(_face(-dirv)
			* Basis.from_scale(Vector3(1.5, 3.2, 1.1)), q4))
	# a fringe round the crown over it
	for k in range(16):
		var a5: float = TAU * float(k) / 16.0 + 0.4
		var rr5: float = R * rng.randf_range(0.35, 0.80)
		var q5: Vector3 = p + Vector3(cos(a5) * rr5, 0.0, sin(a5) * rr5)
		var ph: float = acos(clampf(rr5 / R, 0.0, 1.0))
		q5.y += sin(ph) * (_ht(_st(sid)) * 1.25) * 0.97
		var ln: float = rng.randf_range(0.35, 1.5)
		_prop(q5, "icefringe%d" % (k % 2), _xf(q5, Vector3(0, rng.randf() * TAU, 0),
			Vector3(rng.randf_range(0.6, 1.3), ln, rng.randf_range(0.6, 1.3))))

# ===========================================================================
# UNCOVERING
# ===========================================================================
# The designer, 2026-09-10: "it wonders through the cave and than starts to
# uncover stuff."
#
# A discovery has no world object -- ART-DIRECTION 6.4 is explicit about that
# and it is right, because a discovery is a block, and a block is a thing you
# get rather than a thing that stands somewhere. But UNCOVERING is not the
# discovery. It is the moment before it: a shape in a wall that is the wrong
# shape for a wall.
#
# Three places, and they are the three the designer named:
#
#   IN AN ICE WALL   an ancients' object frozen into the fill, sunk into the
#                    surface so a third of it is proud and the rest is a
#                    shadow inside the ice. The ice.gdshader bubble march does
#                    the rest: what is behind the surface reads as behind it.
#   UNDER A LID      the same object under a frozen pool, which is THE-ICE
#                    5.2's "you can see and cannot reach" exactly.
#   AT THE FOOT OF A PITCH   in the cone. Everything the hole has ever dropped
#                    includes the thing somebody dropped down it.
#
# The rule is deterministic from the station id, not from the RNG stream, so a
# reveal is a property of the cave rather than of the order the dressing ran.
# It is a CLIENT rule, not a topology one, because S_WORKS is inside
# SCHEMA_V1_FIELDS and nothing may move it.
const REVEAL_KIT: Array = ["plate", "drum", "coil", "instrument"]

func _reveal_at(sid: int) -> bool:
	# a cheap integer hash of the station id, and one in nineteen passes
	var h: int = (sid * 2654435761) & 0x7FFFFFFF
	h = (h ^ (h >> 13)) * 1274126177
	return ((h >> 7) & 0x7FFFFFFF) % 19 == 3

func _place_reveals() -> void:
	if topo.levels <= 1:
		return
	var n_rev: int = 0
	for e in range(topo.edges.size()):
		var ids: PackedInt32Array = topo.edges[e]
		for i in range(ids.size()):
			var sid: int = ids[i]
			var s: PackedInt32Array = _st(sid)
			var med: int = s[CaveTopology.S_MEDIUM]
			if med != CaveTopology.MED_ICE and med != CaveTopology.MED_ICE_OVER_ROCK:
				continue
			if not _reveal_at(sid):
				continue
			var p: Vector3 = _st_pos(sid)
			var nxt: Vector3 = _st_pos(ids[mini(ids.size() - 1, i + 1)])
			var tg: Vector3 = (nxt - p).normalized()
			if tg.length() < 0.5:
				continue
			var right: Vector3 = tg.cross(Vector3.UP).normalized()
			var hw: float = _hw(s)
			var sgn: float = 1.0 if (sid % 2 == 0) else -1.0
			var nm: String = REVEAL_KIT[(sid / 3) % REVEAL_KIT.size()]
			# SUNK INTO THE WALL. 0.62 of the way in, so what stands proud is
			# a third of an object and the eye has to finish it.
			# ON the wall, not through it. The first pass put the object 100 mm
			# BEYOND a wall whose own silhouette noise is 150 mm, at 0.38 of its
			# own depth: every reveal was completely inside the rock and the
			# frame photographed an empty wall. It sits on the surface now and
			# the wall's own displacement half-buries it, which is what
			# "embedded" has to mean when the wall is procedural.
			var q: Vector3 = p + right * (sgn * hw * 0.97) + Vector3.UP * (0.35 + float(sid % 5) * 0.16)
			_prop(q, nm, Transform3D(_face(-right * sgn)
				* Basis.from_scale(Vector3(0.92, 0.92, 0.55)), q))
			# and a lens of clear ice over it, standing off the wall, so the
			# thing is UNDER something rather than merely against something
			var ql: Vector3 = q - right * (sgn * 0.085)
			_prop(ql, "icelid", Transform3D(_face(-right * sgn)
				* Basis.from_euler(Vector3(PI * 0.5, 0, 0))
				* Basis.from_scale(Vector3(0.85, 1.0, 0.85)), ql))
			n_rev += 1
	# --- and one at the foot of every pitch a machine can descend ----------
	for pi in range(topo.pitches.size()):
		var pr: PackedInt32Array = topo.pitch(pi)
		if (pr[CaveTopology.P_FLAGS] & CaveTopology.PF_DOWN) == 0:
			continue
		var fp: Vector3 = _st_pos(pr[CaveTopology.P_TO_ST])
		var bore: float = float(pr[CaveTopology.P_BORE_MM]) * 0.001
		var a: float = float(pi) * 2.39996
		var q2 := Vector3(fp.x + cos(a) * bore * 0.55, fp.y + 0.10, fp.z + sin(a) * bore * 0.55)
		var nm2: String = REVEAL_KIT[pi % REVEAL_KIT.size()]
		_prop(q2, nm2, _xf(q2, Vector3(1.15, a, 0.42)))
		n_rev += 1
	print("reveals          : %d uncovered objects (ice walls, lids, pitch feet)" % n_rev)

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
	# THE ICE BAND IS EMPTY, and that is the design rather than a saving.
	# THE-ICE 5.2 band 0 is "round, polished, steep and smooth" with no
	# ancients in it; ART-DIRECTION 3.7 makes it the friendly band. Everything
	# gated on this is a thing that cannot be in dead ice: speleothems, a
	# breakdown field, and the prior industry's ground support.
	var icy_here: bool = s[CaveTopology.S_MEDIUM] == CaveTopology.MED_ICE
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
	# Loose stone. HALF-BURIED, not resting: every one of these is sunk between
	# a quarter and three-quarters of its own radius into the ground, which is
	# what stops a floor reading as a pile of cut-outs lying on a plane. The
	# counts are roughly half what they were, because the rock shader now
	# parallax-maps the aggregate itself and the props only have to break its
	# silhouette. That is also where most of the frame-rate cost went.
	var n_stone: int = int(8.0 + 17.0 * (1.0 - worked * 0.62) + (1.0 - integ) * 12.0)
	for k in range(n_stone):
		var u: float = rng.randf_range(-0.95, 0.95) * hw
		var v: float = rng.randf_range(-0.30, 0.30)
		var q: Vector3 = p + right * u + tangent * v
		var si: int = rng.randi() % 4
		var sc: float = rng.randf_range(0.55, 1.7)
		var rad: float = (0.075 + float(si) * 0.035) * sc
		q.y += _floor_y(q, worked) - rad * rng.randf_range(0.25, 0.72)
		# WHAT IS LOOSE ON AN ICE FLOOR IS ICE. Two thirds of it, anyway: a
		# conduit floor carries the blocks the roof shed and the englacial
		# rubble the fill was already holding, and the second kind is stone.
		# Before this the ice band's floor was a brown scree, which is most of
		# why v6_ice_band read as a culvert with a blue wall.
		if icy_here and rng.randf() < 0.66:
			_prop(q, "iceblock%d" % (si % 3),
				_xf(q, Vector3(rng.randf() * 0.5, rng.randf() * TAU, rng.randf() * 0.5),
					Vector3.ONE * sc * 1.15))
			continue
		_prop(q, "stone%d" % si,
			_xf(q, Vector3(rng.randf() * 0.4, rng.randf() * TAU, rng.randf() * 0.4),
				Vector3.ONE * sc),
			Color(1, 1, 1).lerp(Color(0.55, 0.5, 0.45), rng.randf() * 0.6))
	# grit: the smallest instanced scale. The parallax field supplies the rest.
	for k in range(9):
		var ug: float = rng.randf_range(-0.98, 0.98) * hw
		var qg: Vector3 = p + right * ug + tangent * rng.randf_range(-0.30, 0.30)
		var gc: float = rng.randf_range(0.6, 2.0)
		qg.y += _floor_y(qg, worked) - 0.030 * gc * rng.randf_range(0.2, 0.7)
		_prop(qg, "grit%d" % (rng.randi() % 2),
			_xf(qg, Vector3(rng.randf() * TAU, rng.randf() * TAU, rng.randf() * TAU),
				Vector3.ONE * gc))
	# fresh spall under bad ground: angular flakes off the back, lying in the
	# muck at the angle they came to rest, one edge under the fines
	if integ < 0.62:
		for k in range(int(3.0 + (1.0 - integ) * 7.0)):
			var qsl: Vector3 = p + right * rng.randf_range(-0.95, 0.95) * hw + tangent * rng.randf_range(-0.3, 0.3)
			qsl.y += _floor_y(qsl, worked) - rng.randf_range(0.005, 0.030)
			_prop(qsl, "spall%d" % (rng.randi() % 3),
				_xf(qsl, Vector3(rng.randf_range(-0.28, 0.28), rng.randf() * TAU, rng.randf_range(-0.28, 0.28)),
					Vector3.ONE * rng.randf_range(0.6, 1.6)))
	# silt fans, where the water has been. Value, not brightness: the first pass
	# gave these a near-white vertex colour and they read as paper on the floor.
	if wet > 0.45:
		for k in range(2):
			var q2: Vector3 = p + right * rng.randf_range(-0.9, 0.9) * hw + tangent * rng.randf_range(-0.3, 0.3)
			q2.y += _floor_y(q2, worked) + 0.004
			_prop(q2, "fines", _xf(q2, Vector3(0, rng.randf() * TAU, 0),
				Vector3(rng.randf_range(0.8, 2.4), 1.0, rng.randf_range(0.8, 2.4))),
				Color(0.55, 0.52, 0.48))
	# litter: small, sparse, everywhere the industry went
	for k in range(2):
		if worked < 0.25 or rng.randf() > 0.5:
			continue
		var q3: Vector3 = p + right * rng.randf_range(-0.9, 0.9) * hw + tangent * rng.randf_range(-0.3, 0.3)
		q3.y += 0.012
		_prop(q3, "litter", _xf(q3, Vector3(0, rng.randf() * TAU, 0)), Color(1, 1, 1))

	# ---------- THE ICE ----------------------------------------------------
	var med_here: int = s[CaveTopology.S_MEDIUM]
	if med_here == CaveTopology.MED_ICE or med_here == CaveTopology.MED_ICE_OVER_ROCK:
		_dress_ice(sid, s, p, tangent, right, basis_dir, hw, ht, wet, worked, flooded)

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
		for k in range(15):
			var qb: Vector3 = p + right * rng.randf_range(-0.72, 0.72) + tangent * rng.randf_range(-0.3, 0.3)
			var bi: int = rng.randi() % 3
			var bs: float = rng.randf_range(0.7, 1.5)
			qb.y += _floor_y(qb, worked) - (0.038 + float(bi) * 0.012) * bs * rng.randf_range(0.15, 0.6) + 0.02
			_prop(qb, "ballast%d" % bi,
				_xf(qb, Vector3(rng.randf(), rng.randf() * TAU, rng.randf()), Vector3.ONE * bs),
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
		var nb: int = 1 if icy_here else (1 + int((1.0 - integ) * 2.5))
		for k in range(nb):
			if rng.randf() > (0.16 if icy_here else 0.55):
				continue
			var side_bk: float = 1.0 if rng.randf() < 0.5 else -1.0
			var qbk: Vector3 = p + right * (side_bk * rng.randf_range(0.42, 0.88) * hw) + tangent * rng.randf_range(-0.3, 0.3)
			qbk.y += 0.10
			_prop(qbk, "block%d" % (rng.randi() % 3),
				_xf(qbk, Vector3(rng.randf() * 0.5, rng.randf() * TAU, rng.randf() * 0.5),
					Vector3.ONE * (rng.randf_range(0.30, 0.70) if icy_here else rng.randf_range(0.7, 1.8))),
				Color(1, 1, 1).lerp(Color(0.6, 0.55, 0.5), rng.randf() * 0.7))
	# roof pendants in natural ground. NOT IN ICE: a pendant and a flowstone
	# boss are both limestone speleothems and take ten thousand years of
	# dripping to make. The ice band is younger than the machinery.
	if worked < 0.35 and not icy_here and rng.randf() < 0.45:
		var qp: Vector3 = p + right * rng.randf_range(-0.6, 0.6) * hw
		qp.y += ht * rng.randf_range(0.78, 0.95)
		_prop(qp, "pendant", _xf(qp, Vector3(rng.randf() * 0.25, rng.randf() * TAU, rng.randf() * 0.25),
			Vector3(rng.randf_range(0.5, 1.2), rng.randf_range(0.6, 1.6), rng.randf_range(0.5, 1.2))),
			Color(1, 1, 1))
	if worked < 0.5 and not icy_here and rng.randf() < 0.5:
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
		# 0.96 of the half width puts a 10 mm plate INSIDE a wall whose own
		# silhouette noise is up to 0.5 m, so on the layered path -- where this
		# plate is THE FIRST IRON and has a frame of its own -- it stands off
		# on its bracket instead. The flat arm is the old constant, because the
		# committed flat frames are matched to it.
		var qpl: Vector3 = p + right * (hw * (0.96 if topo.levels <= 1 else 0.80))
		qpl.y += 1.40
		_prop(qpl, "plate", Transform3D(_face(-right), qpl), Color(1, 1, 1))
	# NOTE: the instanced `puddle` disc is GONE. It was a flat plane with
	# roughness 0.03 and metallic 0.15, which under a lamp sitting at the eye
	# returned nothing to the camera and read as a black hole cut in the floor
	# -- the single most damaging object in the underfoot frame. The rock
	# shader now grows puddles out of the parallax height field itself, so the
	# water sits in the real low spots and the aggregate breaks its surface.
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
# 2026-09-10: the water surface is PER LEVEL, not one global datum. The datum
# was cave/PHOTOREAL.md's guess 4 -- "this treats the whole cave as having
# drowned once, to one level" -- and THE-ICE 2.3 says meltwater cutting
# downward is precisely the case where one horizontal datum is wrong. Each
# station now carries its own surface, and below the melt front there is none.
# ===========================================================================
# THE ICE, DRESSED
# ===========================================================================
# THE-ICE 5.2 says band 0 has no ancients in it, and the first pass took that
# to mean band 0 has NOTHING in it -- the comment in _dress_station still says
# "the ice band is empty, and that is the design rather than a saving". That
# was wrong twice over. It is only empty of the INDUSTRY. An ice cave is one
# of the most crowded places on earth: everything that ever dripped in it is
# still there, standing up or hanging down.
#
# Five objects and one rule each. Every one of them is water that stopped.
#
#   icefringe   the crown drips and the drips froze. Placed on the crown by
#               the section's own ellipse, so they hang from where the roof is
#   iceboss     what landed under a fringe and built back up
#   icecolumn   a fringe that reached its boss. Only where the two would meet
#   icefall     a wall seep that ran and froze. The frozen waterfall, and it
#               is the single most recognisable object in an ice cave
#   icelid      a still pool that froze over, with its air trapped underneath
#
# The density is driven by ONE topology field -- `wet` -- because a drip is
# water and the field that says how much water is here is the field that says
# how many icicles there are. Nothing new crosses the seam.
func _dress_ice(sid: int, s: PackedInt32Array, p: Vector3, tangent: Vector3,
				right: Vector3, basis_dir: Basis, hw: float, ht: float,
				wet: float, worked: float, flooded: bool) -> void:
	var icep: Vector3 = _ice_params(s)
	var pure: bool = s[CaveTopology.S_MEDIUM] == CaveTopology.MED_ICE
	# how much has run here. Below 0.2 the ice is dry and sublimating and
	# nothing hangs off it, which is what makes the wet stretches read.
	var drip: float = clampf((wet - 0.18) / 0.62, 0.0, 1.0)
	# the crown height at a lateral offset u, from the same ellipse the profile
	# sweeps. Getting this from the section rather than from `ht` is what stops
	# an icicle hanging in mid-air two metres from the wall it belongs to.
	var crown := func(u: float) -> float:
		var k: float = clampf(absf(u) / maxf(hw * 0.95, 0.01), 0.0, 1.0)
		return ht * sqrt(maxf(0.0, 1.0 - k * k)) * 0.94

	# --- the crown fringe --------------------------------------------------
	var nfr: int = int(0.6 + drip * 4.2)
	for k in range(nfr):
		var u: float = rng.randf_range(-0.82, 0.82) * hw
		var q: Vector3 = p + right * u + tangent * rng.randf_range(-0.30, 0.30)
		var cy: float = crown.call(u)
		if cy < 0.5:
			continue
		q.y += cy - 0.015
		var ln: float = rng.randf_range(0.14, 0.30 + drip * 0.95)
		ln = minf(minf(ln, cy - 0.25), 1.3)
		if ln < 0.10:
			continue
		var wd: float = rng.randf_range(0.35, 0.95)
		_prop(q, "icefringe%d" % (rng.randi() % 2),
			Transform3D(Basis.from_euler(Vector3(0, rng.randf() * TAU, 0))
				* Basis.from_scale(Vector3(wd, ln, wd)), q))
		# what came off it is under it
		if rng.randf() < 0.55:
			var qb: Vector3 = p + right * (u + rng.randf_range(-0.10, 0.10)) + tangent * rng.randf_range(-0.2, 0.2)
			qb.y += _floor_y(qb, worked) - 0.01
			var bh: float = rng.randf_range(0.10, 0.16 + drip * 0.30)
			_prop(qb, "iceboss%d" % (rng.randi() % 2),
				_xf(qb, Vector3(0, rng.randf() * TAU, 0), Vector3(bh * 4.0, bh, bh * 4.0)))
		# --- THE COLUMN. Only where the two would actually have met --------
		# A column is not a decoration, it is an age: the drip has been running
		# long enough to close a gap. So it is generated only where the fringe
		# is long enough and the crown low enough that they touch, which makes
		# it rare, and rare is what makes it worth photographing.
		if ln > cy * 0.62 and drip > 0.55 and rng.randf() < 0.42:
			var qc: Vector3 = p + right * (u + rng.randf_range(-0.06, 0.06)) + tangent * rng.randf_range(-0.25, 0.25)
			var fy: float = qc.y + _floor_y(qc, worked)
			var top: float = p.y + crown.call(u)
			var hgt: float = top - fy
			if hgt > 0.6:
				qc.y = fy
				_prop(qc, "icecolumn", _xf(qc, Vector3(0, rng.randf() * TAU, 0),
					Vector3(rng.randf_range(0.7, 1.5), hgt, rng.randf_range(0.7, 1.5))))

	# --- the frozen waterfall ---------------------------------------------
	# A wall seep, so it wants a wall: the wider the section the better it
	# reads, and it only exists where water came THROUGH the wall rather than
	# down the middle. One in four wet stations, at most one per station.
	# NOT IN A CHAMBER. `hw` for a K_CHAMBER station is 2.93 m and `ht` is
	# 6.75, so the same rule that hangs a 1.5 m curtain in a passage hangs a
	# FIVE METRE one three metres from the middle of a room -- which is what
	# stood between the camera and the Assayer in every frame of the first
	# discovery sequence. A chamber gets its curtains from the site rule
	# instead, on the wall, where a seep would actually be.
	if s[CaveTopology.S_KIND] != CaveTopology.K_CHAMBER 			and drip > 0.30 and hw > 1.15 and rng.randf() < 0.15:
		var sgn: float = 1.0 if (sid % 2 == 0) else -1.0
		var qf: Vector3 = p + right * (sgn * (hw - 0.10)) + tangent * rng.randf_range(-0.25, 0.25)
		var htop: float = minf(ht * rng.randf_range(0.48, 0.72), 2.7)
		qf.y += htop
		var hf: float = htop + 0.18
		_prop(qf, "icefall", Transform3D(_face(-right * sgn)
			* Basis.from_scale(Vector3(rng.randf_range(0.55, 1.15), hf, 1.0)), qf))

	# --- rime and floor ice on the walls of a dry conduit ------------------
	if pure and drip < 0.35 and rng.randf() < 0.30:
		var sgn2: float = 1.0 if (rng.randf() < 0.5) else -1.0
		var qr: Vector3 = p + right * (sgn2 * (hw - 0.06)) + tangent * rng.randf_range(-0.3, 0.3)
		qr.y += rng.randf_range(0.15, ht * 0.5)
		_prop(qr, "icerib", Transform3D(_face(-right * sgn2)
			* Basis.from_scale(Vector3(1.0, rng.randf_range(0.4, 1.1), 1.0)), qr))

	# --- the still pool that froze over ------------------------------------
	# THE-ICE 6.1's "a stope with a floor of clear ice over a muck pile you can
	# see and cannot reach", at passage scale. The lid is a slab; what makes it
	# read is that ice.gdshader marches the bubble trains INTO it, so the air
	# under the lid is under the lid.
	var still: bool = (s[CaveTopology.S_WORKS] & CaveTopology.WK_STANDWATER) != 0
	if (still or (pure and wet > 0.74)) and not flooded and rng.randf() < 0.62:
		var ql: Vector3 = p + right * rng.randf_range(-0.20, 0.20) + tangent * rng.randf_range(-0.2, 0.2)
		ql.y += _floor_y(ql, worked) + 0.055
		_prop(ql, "icelid", Transform3D(basis_dir * Basis.from_scale(
			Vector3(hw * rng.randf_range(1.3, 1.9), 1.0, rng.randf_range(0.9, 1.5))), ql))

func _place_water() -> void:
	for e in range(topo.edges.size()):
		var ids: PackedInt32Array = topo.edges[e]
		var run_start: int = -1
		for i in range(ids.size() + 1):
			var flooded: bool = false
			if i < ids.size():
				flooded = _st(ids[i])[CaveTopology.S_STATE] == CaveTopology.FLOODED
			if flooded and run_start < 0:
				run_start = i
			elif not flooded and run_start >= 0:
				for j in range(run_start, i):
					var sj: PackedInt32Array = _st(ids[j])
					var y: float = float(sj[CaveTopology.S_WATER_MM]) * 0.001
					var p: Vector3 = _st_pos(ids[j])
					var hw: float = _hw(sj) * 1.05
					var nxt: Vector3 = _st_pos(ids[mini(ids.size() - 1, j + 1)])
					var tangent: Vector3 = (nxt - p).normalized()
					var yaw: float = atan2(tangent.x, tangent.z)
					var q := Vector3(p.x, y, p.z)
					_prop(q, "watertile", Transform3D(Basis.from_euler(Vector3(0, yaw, 0)) * Basis.from_scale(
						Vector3(hw * 2.0, 1.0, 0.75)), q), Color(1, 1, 1))
					# A POOL IN THE ICE BAND HAS A LID ON IT. Still water in a
					# place that is below freezing does not stay water; it
					# freezes from the top and traps its own air under the
					# skin. So the water surface stays -- you can see it -- and
					# a slab of ice sits 40 mm above it.
					if sj[CaveTopology.S_MEDIUM] == CaveTopology.MED_ICE:
						var qd := Vector3(p.x, y + 0.045, p.z)
						_prop(qd, "icelid", Transform3D(Basis.from_euler(Vector3(0, yaw, 0))
							* Basis.from_scale(Vector3(hw * 2.05, 1.0, 0.78)), qd))
				run_start = -1

	# --- THE MELTWATER CHANNEL --------------------------------------------
	# _sweep_edge cuts a groove down the floor of a running conduit; this is
	# the water in it. It is a ribbon 0.5-0.9 m wide sitting BELOW the floor
	# either side of it, which is the difference between a stream and a
	# puddle, and it is the thing that gives an ice passage a direction.
	for e2 in range(topo.edges.size()):
		var ids2: PackedInt32Array = topo.edges[e2]
		for i2 in range(ids2.size()):
			var s2: PackedInt32Array = _st(ids2[i2])
			if s2[CaveTopology.S_MEDIUM] != CaveTopology.MED_ICE:
				continue
			if s2[CaveTopology.S_STATE] == CaveTopology.FLOODED:
				continue
			var wet2: float = float(s2[CaveTopology.S_WET]) / 255.0
			if wet2 <= 0.42:
				continue
			var hw2: float = _hw(s2)
			var chw: float = minf(0.46, hw2 * 0.38)
			var chd: float = 0.13 + 0.13 * clampf((wet2 - 0.42) / 0.5, 0.0, 1.0)
			var p2: Vector3 = _st_pos(ids2[i2])
			var nx2: Vector3 = _st_pos(ids2[mini(ids2.size() - 1, i2 + 1)])
			var tg2: Vector3 = (nx2 - p2).normalized()
			if tg2.length() < 0.5:
				continue
			var yaw2: float = atan2(tg2.x, tg2.z)
			# the stream does not fill the notch: it runs in the bottom of it
			var q2 := Vector3(p2.x, p2.y - chd * 0.62, p2.z)
			_prop(q2, "watertile", Transform3D(Basis.from_euler(Vector3(0, yaw2, 0))
				* Basis.from_scale(Vector3(chw * 1.5, 1.0, 0.72)), q2), Color(1, 1, 1))

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
			mi.visibility_range_end = VIS_PITCH if bool(c.get("pitch", false)) else VIS_SHELL
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
	if topo.levels <= 1:
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
		return
	# the layered walk: cross a level to its far end, drop, cross the next one
	# back the other way. It is the descent, and it is the shape of the mine.
	for L in range(topo.levels):
		var lids: PackedInt32Array = topo.edges[topo.level_main_edge[L]]
		var head: int = lids.size() - 1
		if topo.level_head_st[L] >= 0:
			for i in range(lids.size()):
				if lids[i] == topo.level_head_st[L]:
					head = i
					break
		for i in range(head + 1):
			var p2: Vector3 = _st_pos(lids[i])
			var s2: PackedInt32Array = _st(lids[i])
			var eye2: float = 1.15
			if s2[CaveTopology.S_WIDTH] == CaveTopology.WC_CRAWL:
				eye2 = 0.70
			path_points.push_back(p2 + Vector3.UP * eye2)
		var hs: int = topo.level_head_st[L]
		if hs < 0:
			continue
		var ph: int = _st(hs)[CaveTopology.S_PITCH_HEAD]
		if ph < 0:
			continue
		var pr: PackedInt32Array = topo.pitch(ph)
		var tp := Vector3(float(pr[CaveTopology.P_X]) * CELL,
			float(pr[CaveTopology.P_TOP_MM]) * 0.001, float(pr[CaveTopology.P_Y]) * CELL)
		var bp := Vector3(float(pr[CaveTopology.P_TO_X]) * CELL,
			float(pr[CaveTopology.P_BOT_MM]) * 0.001 + 1.15, float(pr[CaveTopology.P_TO_Y]) * CELL)
		var dh: float = tp.y - bp.y
		var ns: int = maxi(3, int(dh / 1.1))
		var bore2: float = float(pr[CaveTopology.P_BORE_MM]) * 0.001
		var kind2: int = pr[CaveTopology.P_KIND]
		for i in range(1, ns + 1):
			var t: float = float(i) / float(ns)
			var q: Vector3 = tp.lerp(bp, t)
			if kind2 == CaveTopology.PK_MOULIN or kind2 == CaveTopology.PK_COLLAR:
				q += Vector3(cos(t * dh * 0.22), 0.0, sin(t * dh * 0.22)) * (bore2 * 0.32 * sin(t * PI))
			path_points.push_back(q)
	for i in range(path_points.size()):
		var j2: int = mini(path_points.size() - 1, i + 3)
		path_look.push_back(path_points[j2])
