#!/bin/sh
# Export every chassis and every clip from agent_model as .glb.
#
# Twelve files: four chassis x { idle, walk, trot }. Godot takes the mesh and
# the skeleton from `<chassis>_walk.glb` and lifts the other two clips'
# animations into the same AnimationPlayer, so only one mesh is ever loaded.
#
# CYCLE LENGTHS. motion.py derives the stride from the SPEED ALONE --
# `stride = min(0.32, 0.12 + 0.36 * speed)` -- with no reference to leg length
# or body size, so a 0.90 m Hauler and a 0.40 m Scout take exactly the same
# 0.32 m step at the same speed. That is a real property of the model and it is
# left alone here rather than worked around; see NOTES.md.
#
# Given that rule, T = 0.12/v + 0.36 below 0.556 m/s and 0.32/v above it, so
# the speeds are picked to land the cycle on a whole number of frames at 30 fps:
#
#   walk  v = 0.50 m/s   stride 0.30   T = 0.600 s   18 frames
#   trot  v = 0.60 m/s   stride 0.32   T = 0.533 s   16 frames
#
# `--export-frames 1,N+1` trims the clip to exactly one period: frame 1 is the
# stance at t = 0 and frame N+1 is the same phase one cycle later, which is
# what a looping clip needs. motion.py's trailing settle frame is cut off.
set -e
cd "$(dirname "$0")"
B="C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"
R=../../..
OUT=models
mkdir -p "$OUT"

run() {  # chassis clip move frames
  echo "--- $1 $2"
  "$B" -b -P "$R/agent_model/run.py" -- \
    --chassis "$1" --no-cave --fps 30 \
    --export "$(pwd)/$OUT/$1_$2.glb" --export-clip "$2" \
    --export-frames "$4" --move "$3" 2>&1 | grep -E "^EXPORT|Error|Traceback|error:" || true
}

# a bare Surveyor -- lamp only, no other module -- so the loadout can be
# compared against the default one in silhouette (ART 4.4)
runmod() {  # name chassis modules clip move frames
  echo "--- $1 $4"
  "$B" -b -P "$R/agent_model/run.py" --     --chassis "$2" --modules "$3" --no-cave --fps 30     --export "$(pwd)/$OUT/$1_$4.glb" --export-clip "$4"     --export-frames "$6" --move "$5" 2>&1 | grep -E "^EXPORT|Error|Traceback|error:" || true
}

for c in scout surveyor hauler swimmer; do
  # walk: 18-frame cycle, one period, in place
  run "$c" walk "walk 0.6 0.5 0 walk" "1,19"
  # trot: 16-frame cycle
  run "$c" trot "walk 0.5333 0.6 0 trot" "1,17"
  # idle: a standing machine looking around. Not a still: a machine that stands
  # perfectly still is a prop, and the pan/tilt is the cheapest thing it owns.
  run "$c" idle "stand 0.3; look 2.0,1.2,0.25 0.8 ride; stand 0.4; look 2.4,-1.1,0.10 0.8 ride; stand 0.4" "1,80"
  # ART 4.2 rung 0.75: "ride height drops 25%". motion.py's own `crouch` verb
  # does it with the IK intact, which is better than anything Godot could fake
  # on a baked clip -- the legs fold, they do not stretch.
  run "$c" crouch "crouch 0.08 0.5; stand 0.7" "1,36"
done
runmod surveyor_bare surveyor "eye=optical" walk "walk 0.6 0.5 0 walk" "1,19"
runmod surveyor_bare surveyor "eye=optical" idle "stand 0.3; look 2.0,1.2,0.25 0.8 ride; stand 0.6" "1,50"
ls -la "$OUT"
