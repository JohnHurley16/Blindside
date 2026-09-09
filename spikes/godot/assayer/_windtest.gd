extends SceneTree
func _init():
	var b := BoxMesh.new()
	b.size = Vector3(2,2,2)
	var a: Array = b.get_mesh_arrays()
	var v: PackedVector3Array = a[Mesh.ARRAY_VERTEX]
	var n: PackedVector3Array = a[Mesh.ARRAY_NORMAL]
	var idx: PackedInt32Array = a[Mesh.ARRAY_INDEX]
	for f in range(2):
		var i0: int = idx[f*3]; var i1: int = idx[f*3+1]; var i2: int = idx[f*3+2]
		var fn: Vector3 = (v[i1]-v[i0]).cross(v[i2]-v[i0]).normalized()
		print("face %d  v0=%s v1=%s v2=%s  shading_normal=%s  cross=%s  dot=%.2f" % [
			f, str(v[i0]), str(v[i1]), str(v[i2]), str(n[i0]), str(fn), fn.dot(n[i0])])
	quit()
