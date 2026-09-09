#!/usr/bin/env bash
# The machine's own view: cloud / gap / perception, from cloud_dump.py's seed-7 data.
set -u
BL="/c/Program Files/Blender Foundation/Blender 5.2/blender.exe"
ROOT="C:/Users/jackh/documents/programming/Blindside"
OUT="$ROOT/docs/art/vision/found"
DATA="$ROOT/docs/art/vision/found/_probes/data"
Q="${Q:---samples 40 --res 960x600}"
shot () { concept="$1"; name="$2"; data="$3"; sh="$4"; shift 4
  mkdir -p "$OUT/$concept"
  s=$(date +%s)
  "$BL" -b -P "$ROOT/docs/art/vision/found/_probes/cloud_scene.py" -- --data "$DATA/$data" --shot "$sh" --out "$OUT/$concept/$name.png" $Q "$@" \
    > "$OUT/_probes/log_$sh.txt" 2>&1 && echo "ok $concept/$name $(( $(date +%s) - s )) s" || echo "FAIL $concept/$name (see _probes/log_$sh.txt)"
}
# F1 the cloud as art. Disc radius: 0.022 m is the direction's 44 mm; the wide frames use
# 0.035 so a 1000-point map reads on a 960 px board (flagged in NOTES).
shot cloud      01_clear_director     seed7_t138.npz cloud_director --disc 0.035
shot cloud      02_clear_low          seed7_t138.npz cloud_low      --disc 0.035
shot cloud      03_clear_macro        seed7_t138.npz cloud_macro    --disc 0.022
shot cloud      04_clear_drift        seed7_t300.npz cloud_drift    --disc 0.05
shot cloud      05_situ_both_rear     seed7_t100.npz both           --disc 0.035
shot cloud      06_situ_low_t100      seed7_t100.npz cloud_low      --disc 0.035
# F3 world and belief as one picture
shot gap        01_clear_gap          seed7_t100.npz gap_clear      --disc 0.035
shot gap        02_situ_both          seed7_t138.npz both           --disc 0.035
shot gap        03_situ_belief_only   seed7_t138.npz belief_only    --disc 0.035
shot gap        04_situ_truth_only    seed7_t138.npz truth_only
shot gap        05_situ_reveal        seed7_t341.npz reveal         --disc 0.06
# F4 enter-agent-perception
shot perception 01_clear_truth        seed7_t100.npz percep_truth
shot perception 02_situ_both          seed7_t100.npz percep_both    --disc 0.03
shot perception 03_situ_belief        seed7_t100.npz percep_belief  --disc 0.03
echo "CLOUD BATCH DONE"
