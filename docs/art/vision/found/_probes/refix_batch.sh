#!/usr/bin/env bash
# Re-renders after review. Run after found_batch.sh and cloud_batch.sh.
set -u
BL="/c/Program Files/Blender Foundation/Blender 5.2/blender.exe"
ROOT="C:/Users/jackh/documents/programming/Blindside"
OUT="$ROOT/docs/art/vision/found"
DATA="$OUT/_probes/data"
Q="${Q:---samples 40 --res 960x600}"
f () { concept="$1"; name="$2"; sh="$3"
  s=$(date +%s)
  "$BL" -b -P "$OUT/_probes/found_probe.py" -- --shot "$sh" --out "$OUT/$concept/$name.png" $Q > "$OUT/_probes/log_$sh.txt" 2>&1 \
    && echo "ok $concept/$name $(( $(date +%s) - s )) s" || echo "FAIL $concept/$name"
}
c () { concept="$1"; name="$2"; data="$3"; sh="$4"; shift 4
  s=$(date +%s)
  "$BL" -b -P "$OUT/_probes/cloud_scene.py" -- --data "$DATA/$data" --shot "$sh" --out "$OUT/$concept/$name.png" $Q "$@" > "$OUT/_probes/log_$sh.txt" 2>&1 \
    && echo "ok $concept/$name $(( $(date +%s) - s )) s" || echo "FAIL $concept/$name"
}
f deposit 02_clear_after   dep_clear_after
f deposit 07_situ_loading  dep_situ_loading
f deposit 08_situ_worked   dep_situ_worked
c cloud 01_clear_director seed7_t138.npz cloud_director --disc 0.05
c cloud 02_clear_low      seed7_t138.npz cloud_low      --disc 0.035
c cloud 03_clear_macro    seed7_t138.npz cloud_macro    --disc 0.022
c cloud 04_clear_drift    seed7_t300.npz cloud_drift    --disc 0.12
c cloud 05_situ_both_rear seed7_t100.npz both --disc 0.05
echo "REFIX DONE"
