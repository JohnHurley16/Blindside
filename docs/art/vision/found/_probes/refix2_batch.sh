#!/usr/bin/env bash
# Second review pass (2026-09-08, evening): re-renders of every first-pass frame that came
# out black or off-frame, the three frames the first pass never wrote, one new concept
# (the spoof as an act), and the cloud/gap frames re-framed. Run after found_batch.sh and
# cloud_batch.sh; safe to re-run. Usage: bash refix2_batch.sh [E|F|all]
set -u
BL="/c/Program Files/Blender Foundation/Blender 5.2/blender.exe"
ROOT="C:/Users/jackh/documents/programming/Blindside"
OUT="$ROOT/docs/art/vision/found"
DATA="$OUT/_probes/data"
Q="${Q:---samples 40 --res 960x600}"
WHICH="${1:-all}"
f () { concept="$1"; name="$2"; sh="$3"
  s=$(date +%s)
  "$BL" -b -P "$OUT/_probes/found_probe.py" -- --shot "$sh" --out "$OUT/$concept/$name.png" $Q > "$OUT/_probes/log_$sh.txt" 2>&1 \
    && echo "ok $concept/$name $(( $(date +%s) - s )) s" || echo "FAIL $concept/$name (see _probes/log_$sh.txt)"
}
c () { concept="$1"; name="$2"; data="$3"; sh="$4"; shift 4
  s=$(date +%s)
  "$BL" -b -P "$OUT/_probes/cloud_scene.py" -- --data "$DATA/$data" --shot "$sh" --out "$OUT/$concept/$name.png" $Q "$@" > "$OUT/_probes/log_${name}.txt" 2>&1 \
    && echo "ok $concept/$name $(( $(date +%s) - s )) s" || echo "FAIL $concept/$name (see _probes/log_${name}.txt)"
}
if [ "$WHICH" = "E" ] || [ "$WHICH" = "all" ]; then
  f deposit   07_situ_loading   dep_situ_loading
  f wreck     02_clear_back     wreck_clear_back
  f beacon    01_clear_product  bcn_clear_product
  f beacon    03_clear_drop     bcn_clear_drop
  f beacon    04_situ_chain     bcn_situ_chain
  f beacon    05_situ_range     bcn_situ_range
  f beacon    07_situ_sump      bcn_situ_sump
  f beacon    08_situ_spoof     bcn_situ_spoof
  f discovery 04_situ_pose      disc_situ_pose
fi
if [ "$WHICH" = "F" ] || [ "$WHICH" = "all" ]; then
  # F1 the cloud: the director's attitude at 5:00 (wide enough to be a map), the macro on
  # dark grey, the drift PAIR from one fixed camera (before the spoof / after it), the early
  # low orbit. Disc radii above the direction's 22 mm are board licences, flagged in NOTES.
  c cloud 01_clear_director     seed7_t300.npz cloud_director --disc 0.08 --ortho 44 --bg 0.02
  c cloud 03_clear_macro        seed7_t341.npz cloud_macro    --disc 0.022 --bg 0.05
  c cloud 04_clear_drift_before seed7_t138.npz cloud_top      --disc 0.07 --ortho 26 --centre 60,36 --bg 0.02
  c cloud 05_clear_drift_after  seed7_t200.npz cloud_top      --disc 0.07 --ortho 26 --centre 60,36 --bg 0.02
  c cloud 07_situ_low_t100      seed7_t100.npz cloud_low      --disc 0.035
  # F3 world and belief: the cut-away teaching image, and the three modes from an OPEN camera
  c gap 01_clear_gap            seed7_t138.npz gap_clear      --disc 0.035 --wall-h 2.2
  c gap 02_situ_both            seed7_t138.npz both           --disc 0.035
  c gap 03_situ_belief_only     seed7_t138.npz belief_only    --disc 0.035
  c gap 04_situ_truth_only      seed7_t138.npz truth_only
fi
echo "REFIX2 DONE ($WHICH)"
