# Two spikes now live in this directory and both must stay runnable.
#   default   the scanning-sensor build   (lidar_root.gd, LIDAR.md)
#   --old     the first pass, additive oriented discs on a real phase1 match
#             (cloud_root.gd, NOTES.md); needs data/, which is gitignored.
extends Node3D

func _ready() -> void:
	var old := false
	for a in OS.get_cmdline_user_args():
		if a == "--old":
			old = true
	var n := Node3D.new()
	n.set_script(load("res://cloud_root.gd") if old else load("res://lidar_root.gd"))
	n.name = "OldCloud" if old else "Lidar"
	add_child(n)
