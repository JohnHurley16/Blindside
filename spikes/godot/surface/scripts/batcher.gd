extends RefCounted
class_name Batcher
##
## DRESSING LAYER - instancing.
##
## Every solid on the site goes through here. Instances are binned by
## (mesh, material, bucket) and flushed to one MultiMeshInstance3D per bin, so
## the whole pit-head costs tens of draw calls instead of tens of thousands.
##
## Three buckets, which is where the frame budget is actually won:
##   SITE   - silhouette structures. Cast shadows. Always resident.
##   PROP   - walking-distance objects. Cast shadows. Chunked at 32 m.
##   DETAIL - underfoot. NO shadow casting, chunked at 16 m, culled past 55 m.
##
## Shadow casting is the expensive half of a daylight scene, so the rule is:
## if it is smaller than a boot it does not cast.

const CHUNK_PROP := 32.0
const CHUNK_DETAIL := 16.0

const SITE := 0
const PROP := 1
const DETAIL := 2
## FAR - the town on the far wall, 900 m to 2.5 km away. It casts no shadow (the
## sun's shadow range is 95 m), it is never culled by distance (it is the
## horizon), and it is NOT chunked, because chunking a thing that is either
## entirely in frame or entirely out of it buys nothing and costs draw calls.
const FAR := 3

var _bins: Dictionary = {}
var _keys: Array = []
var total_instances := 0

class Bin extends RefCounted:
	var mesh_id: String
	var mat_id: String
	var bucket: int
	var xf := PackedFloat32Array()
	var n := 0
	var emissive := false

func _key(mesh_id: String, mat_id: String, bucket: int, pos: Vector3) -> String:
	match bucket:
		SITE:
			return mesh_id + "|" + mat_id + "|s"
		FAR:
			return mesh_id + "|" + mat_id + "|f"
		PROP:
			return "%s|%s|p%d_%d" % [mesh_id, mat_id,
				int(floor(pos.x / CHUNK_PROP)), int(floor(pos.z / CHUNK_PROP))]
		_:
			return "%s|%s|d%d_%d" % [mesh_id, mat_id,
				int(floor(pos.x / CHUNK_DETAIL)), int(floor(pos.z / CHUNK_DETAIL))]

func add(mesh_id: String, mat_id: String, xform: Transform3D, col: Color = Color.WHITE,
		bucket: int = SITE, emissive: bool = false) -> void:
	var k := _key(mesh_id, mat_id, bucket, xform.origin)
	var bin: Bin
	if _bins.has(k):
		bin = _bins[k]
	else:
		bin = Bin.new()
		bin.mesh_id = mesh_id
		bin.mat_id = mat_id
		bin.bucket = bucket
		bin.emissive = emissive
		_bins[k] = bin
		_keys.append(k)
	var b := xform.basis
	var o := xform.origin
	bin.xf.append_array(PackedFloat32Array([
		b.x.x, b.y.x, b.z.x, o.x,
		b.x.y, b.y.y, b.z.y, o.y,
		b.x.z, b.y.z, b.z.z, o.z,
		col.r, col.g, col.b, col.a]))
	bin.n += 1
	total_instances += 1

func prop(mesh_id: String, mat_id: String, xform: Transform3D, col: Color = Color.WHITE) -> void:
	add(mesh_id, mat_id, xform, col, PROP)

func detail(mesh_id: String, mat_id: String, xform: Transform3D, col: Color = Color.WHITE) -> void:
	add(mesh_id, mat_id, xform, col, DETAIL)

# ------------------------------------------------------------- placement help
## NOTE, and this cost an afternoon: Basis.scaled() scales the basis ROWS, which
## applies the scale in the PARENT frame. For a rotated instance that stretches
## it along world axes instead of its own, and a 4.8 x 0.07 bench turns into a
## 4.8 m tall post. Multiply by from_scale on the RIGHT to scale local axes.
static func xf(pos: Vector3, size: Vector3, yaw: float = 0.0,
		pitch: float = 0.0, roll: float = 0.0) -> Transform3D:
	var basis := Basis.from_euler(Vector3(pitch, yaw, roll)) * Basis.from_scale(size)
	return Transform3D(basis, pos)

## a member running from a to b, cross-section w x d
static func beam_xf(a: Vector3, b: Vector3, w: float, d: float, twist: float = 0.0) -> Transform3D:
	var dv := b - a
	var l := dv.length()
	if l < 0.0001:
		return Transform3D(Basis().scaled(Vector3(w, 0.001, d)), a)
	var y := dv / l
	var ref := Vector3(0, 0, -1)
	if absf(y.z) > 0.94:
		ref = Vector3(1, 0, 0)
	var x := ref.cross(y).normalized()
	var z := x.cross(y)
	var basis := Basis(x, y, z)
	if twist != 0.0:
		basis = basis * Basis.from_euler(Vector3(0, twist, 0))
	basis = basis * Basis.from_scale(Vector3(w, l, d))
	return Transform3D(basis, (a + b) * 0.5)

func beam(mesh_id: String, mat_id: String, a: Vector3, b: Vector3, w: float, d: float,
		col: Color = Color.WHITE, bucket: int = SITE) -> void:
	add(mesh_id, mat_id, beam_xf(a, b, w, d), col, bucket)

# ------------------------------------------------------------------- flush
func flush(parent: Node3D) -> Dictionary:
	var made := 0
	var tris := 0
	for k in _keys:
		var bin: Bin = _bins[k]
		var mm := MultiMesh.new()
		mm.transform_format = MultiMesh.TRANSFORM_3D
		mm.use_colors = true
		mm.mesh = Kit.get_mesh(bin.mesh_id)
		mm.instance_count = bin.n
		mm.buffer = bin.xf
		var mi := MultiMeshInstance3D.new()
		mi.multimesh = mm
		mi.material_override = Mats.get_mat(bin.mat_id) if not bin.emissive else Mats.emissive_of(bin.mat_id, 2.4)
		mi.name = k.replace("|", "_")
		mi.set_meta("bucket", bin.bucket)
		match bin.bucket:
			SITE:
				mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
			FAR:
				mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
				# the town is 2 km long and the frustum test is per-MultiMesh, so
				# the AABB has to be allowed to be enormous or it pops
				mi.extra_cull_margin = 1500.0
			PROP:
				mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
				mi.visibility_range_end = 140.0
				mi.visibility_range_end_margin = 18.0
				mi.visibility_range_fade_mode = GeometryInstance3D.VISIBILITY_RANGE_FADE_DISABLED
			DETAIL:
				mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
				mi.visibility_range_end = 55.0
				mi.visibility_range_end_margin = 10.0
				mi.visibility_range_fade_mode = GeometryInstance3D.VISIBILITY_RANGE_FADE_DISABLED
		parent.add_child(mi)
		made += 1
		tris += bin.n * (Kit.get_mesh(bin.mesh_id).surface_get_array_len(0) / 3)
	return {"multimeshes": made, "instances": total_instances, "tris": tris}
