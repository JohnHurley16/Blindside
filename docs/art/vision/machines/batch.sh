#!/usr/bin/env bash
# Renders the MACHINES vision board: docs/art/vision/machines/NOTES.md lists every image.
#
#   bash docs/art/vision/machines/batch.sh            # all four lanes in parallel
#   bash docs/art/vision/machines/batch.sh 2          # one lane
#
# One Blender process per shot, so a crash (or another job's blanket `taskkill blender`)
# loses one frame, not a lane; --skip-existing makes a re-run pick up where it stopped.
# Four lanes because scene building is single-threaded Python and rendering is not.
# --out-dir must be ABSOLUTE (Blender resolves relative paths against its own cwd).
# Afterwards:
#   .venv/Scripts/python.exe docs/art/vision/machines/ladders.py
set -u
BL="/c/Program Files/Blender Foundation/Blender 5.2/blender.exe"
ROOT="C:/Users/jackh/documents/programming/Blindside"
OUT="$ROOT/docs/art/vision/machines"
Q="--samples 40 --res 960x600 --skip-existing"
export PYTHONUNBUFFERED=1

LANE1="lineup_clear lineup_side lineup_top lineup_passage scout_gesture swimmer_gesture_shot hauler_gesture swimmer_backlit catalogue_side catalogue_top loaded_3q sil_bare sil_loaded rival_view_loud rival_view_quiet"
LANE2="fix_vane_shot fix_spike_shot fix_rack_shot fix_bay_shot fix_vane_backlit fix_spike_lamp team_clear team_lamp_a team_lamp_b retro_clear retro_dark retro_found retro_wreck fallback_dark wear_row wear_lamp"
LANE3="damage_ladder damage_limp damage_bar ownlamp_plus3 ownlamp ownlamp_rival ownlamp_above day_3q day_fresh_vet day_collar day_four day_sun day_veteran"
LANE4="single_scout single_surveyor single_hauler single_swimmer single_rival single_damaged single_wreck head_macro head_reflector head_insitu hardpoints_macro hardpoints_tail underside gait_clear gait_side gait_insitu human_scale"

mkdir -p "$OUT/_logs"
lane () { n="$1"; shots="$2"
  for sh in $shots; do
    log="$OUT/_logs/$sh.log"
    t0=$(date +%s)
    "$BL" -b -P "$ROOT/docs/art/vision/machines/machines_probe.py" -- --shots "$sh" --out-dir "$OUT" $Q 2>&1 \
      | grep -v "^Fra:" | grep --line-buffered -iE "error|traceback|===|WROTE|DONE|File \"|line [0-9]+|Exception" > "$log"
    echo "lane $n: $sh exit ${PIPESTATUS[0]} wall $(( $(date +%s) - t0 )) s"
  done
  echo "lane $n done"
}

case "${1:-all}" in
  1) lane 1 "$LANE1" ;;
  2) lane 2 "$LANE2" ;;
  3) lane 3 "$LANE3" ;;
  4) lane 4 "$LANE4" ;;
  all)
    lane 1 "$LANE1" &
    lane 2 "$LANE2" &
    lane 3 "$LANE3" &
    lane 4 "$LANE4" &
    wait
    echo "BATCH DONE" ;;
esac
