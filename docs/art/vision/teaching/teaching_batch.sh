#!/usr/bin/env bash
# Re-render every Blender frame on the teaching / mood board. One line per image: shot -> file.
# A surface frame takes 5-10 min on CPU at 960x600 / 40 spp (most of it Cycles on a scene with
# a 64 x 62 m course, two machines and DoF); a cave or product frame 2-5 min.
#
#   bash docs/art/vision/teaching/teaching_batch.sh                 # everything, in order
#   ONLY="g5_ g4_" bash docs/art/vision/teaching/teaching_batch.sh  # only names with these prefixes
#
# Then the PIL sheets that are assembled FROM the renders:
#   .venv/Scripts/python.exe docs/art/vision/teaching/teaching_sheets.py --stage post
# (`--stage pre --snaps <dir>` remakes the screen mocks / palette strips / plan; it needs the
#  phase1 / phase2 snapshot PNGs, see teaching_sheets.py's docstring)
set -u
B="C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"
D="C:/Users/jackh/documents/programming/Blindside/docs/art/vision/teaching"
SAMPLES="${SAMPLES:-40}"
RES="${RES:-960x600}"
mkdir -p "$D/_logs"

# shot  file-stem  [extra args]
SHOTS=(
  "g1_course_oblique        g1_01_course-oblique"
  "g1_junction_ots          g1_02_junction-over-the-shoulder"
  "g1_junction_machine_eye  g1_03_junction-machine-height"
  "g1_scale_lineup          g1_04_scale-lineup-clear"
  "g1_junction_drizzle      g1_05_junction-drizzle"
  "g1_deadend               g1_06_deadend-turning-back"
  "g1_roofed                g1_08_roofed-section"
  "g1_junction_plan         g1_09_junction-from-above"
  "g1_junction_ots_pendant  g1_10_junction-pendant-in-frame"
  "g2_pendant_clear         g2_01_pendant-product-clear"
  "g2_terminal_clear        g2_03_terminal-bench-clear"
  "g2_pendant_collar        g2_04_pendant-at-collar"
  "g2_terminal_dusk         g2_05_terminal-dusk"
  "g3_cable_in              g3_01_cable-in-macro"
  "g3_cable_out             g3_02_cable-out-macro"
  "g3_commit_wide           g3_03_commit-wide"
  "g3_descent               g3_04_descent-from-collar"
  "g3_commit_post           g3_05_listening-post"
  "g4_cave_stop             g4_01_cave-stop-truth"
  "g4_cave_stop_above       g4_03_cave-stop-director"
  "g4_cave_stop_plus3       g4_05_cave-stop-plus3"
  "g5_leanto_night          g5_02_leanto-night"
  "g5_leanto_night_wide     g5_03_pithead-night-wide"
  "g5_leanto_night_light    g5_04_leanto-night-worklight"
  "a_yard_wide              g0_03_pithead-from-the-yard"
  "a_yard_bench             g0_04_yard-bench"
  "a_yard_wide              g0_05_pithead-sun-variant  --sky sun"
)

for entry in "${SHOTS[@]}"; do
  set -- $entry
  shot="$1"; name="$2"; shift 2; extra="$*"
  if [ -n "${ONLY:-}" ]; then
    keep=0
    for pre in $ONLY; do case "$name" in "$pre"*) keep=1 ;; esac; done
    [ "$keep" = 1 ] || continue
  fi
  echo "== $shot -> $name.png  $extra"
  ( time "$B" -b -P "$D/teaching_probe.py" -- --shot "$shot" --out "$D/$name.png" \
      --samples "$SAMPLES" --res "$RES" --meta "$D/_logs/$name.json" $extra ) \
      > "$D/_logs/$name.log" 2>&1
  grep -h "WROTE\|Error\|Traceback\|^real" "$D/_logs/$name.log" | tail -3
done
