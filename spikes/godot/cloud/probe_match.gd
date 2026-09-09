# Throwaway probe: does the cloud spike's topology agree with the cave spike's
# about WHERE station N is?  The cave's own recorded track is in
# spikes/godot/cave/shots/cinema/sequences.txt and is the ground truth here.
extends SceneTree

const CELL := 0.6

func _st_pos(topo: CaveTopology, i: int) -> Vector3:
	var s: PackedInt32Array = topo.stations[i]
	return Vector3(float(s[CaveTopology.S_X]) * CELL,
				   float(s[CaveTopology.S_FLOOR_MM]) * 0.001,
				   float(s[CaveTopology.S_Y]) * CELL)

func _init() -> void:
	for ln in [170, 240]:
		var t := CaveTopology.new()
		t.generate(7, ln)
		print("--- seed 7  len %d  stations %d  hash 0x%s" % [
			ln, t.stations.size(), String.num_int64(t.content_hash(), 16)])
		for st in [68, 70, 72, 89]:
			var p: Vector3 = _st_pos(t, st)
			var s: PackedInt32Array = t.stations[st]
			print("   st %3d   x %7.3f  y %7.3f  z %7.3f   worked %3d  width %d  works 0x%s" % [
				st, p.x, p.y, p.z, s[CaveTopology.S_WORKED], s[CaveTopology.S_WIDTH],
				String.num_int64(s[CaveTopology.S_WORKS], 16)])
		var ch: String = ""
		for ci in range(t.chambers.size() / 5):
			ch += " (st %d r %d)" % [t.chambers[ci * 5 + 4], t.chambers[ci * 5 + 2]]
		print("   chambers:" + ch)
	print("")
	print("cave recorded t17 frame 0 : x 44.96  y 0.56  z 23.49   (st 68, r 0.10, u 0.42, f 0.0)")
	print("cave recorded t16 frame 0 : x 47.40  y 1.44  z 24.00   (st 72, r 0.00, u 1.60, f 0.0)")
	print("cave recorded t20 frame 0 : x 56.40  y 0.22  z 23.80   (st 89, r -0.20, u 0.40, f -1.20)")
	quit()
