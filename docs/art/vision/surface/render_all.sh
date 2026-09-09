#!/usr/bin/env bash
# Renders the surface vision board. --out must be ABSOLUTE (Blender resolves relative paths
# against its own cwd). Screens: --screen is a belief-only crop of a phase1 snapshot, --term the
# whole spectator frame (the replay). Both are optional; without them the screens are dark glass.
set -u
BL="/c/Program Files/Blender Foundation/Blender 5.2/blender.exe"
ROOT="C:/Users/jackh/documents/programming/Blindside"
OUT="$ROOT/docs/art/vision/surface"
SCR="${SCREEN_IMG:-}"
TERM_IMG="${TERM_IMG:-}"
Q="--samples ${SAMPLES:-32} --res ${RES:-960x600}"
LOG="${LOGDIR:-$OUT}/render_all.log"

shot () { name="$1"; sh="$2"
  t0=$(date +%s)
  if [ -f "$OUT/$name.png" ] && [ "${FORCE:-0}" = "0" ]; then echo "skip $name (exists)"; return; fi
  "$BL" -b -P "$OUT/surface.py" -- --shot "$sh" --out "$OUT/$name.png" $Q \
    ${SCR:+--screen "$SCR"} ${TERM_IMG:+--term "$TERM_IMG"} > "${LOGDIR:-$OUT}/_$name.log" 2>&1
  rc=$?; t1=$(date +%s)
  echo "$name $sh exit $rc wall $((t1-t0)) s" | tee -a "$LOG"
}

# Shots that lift exposure do so inside surface.py (CLEAR frames only). Composites afterwards:
#   .venv/Scripts/python.exe docs/art/vision/surface/diagrams.py --composites
# priority pass: one CLEAR and one IN-SITU per concept
shot 01_pithead_wide            pithead_wide
shot 03_pithead_insitu_drizzle  pithead_insitu
shot 05_headframe_elevation     headframe_elevation
shot 07_headframe_sheave        headframe_sheave
shot 09_yard_bench              yard_bench
shot 11_yard_modules            yard_modules
shot 14_course_oblique          course_oblique
shot 15_course_ground           course_ground
shot 16_course_human            course_human
shot 19_shaft_lookdown          shaft_lookdown
shot 20_shaft_collar            shaft_collar
shot 22_shaft_insitu            shaft_insitu
shot 23_descent_1_collar        descent_1_collar
shot 24_descent_2_halfway       descent_2_halfway
shot 25_descent_3_lookup        descent_3_lookup
shot 26_descent_4_chamber       descent_4_chamber
shot 27_descent_insitu_lookup   descent_insitu_lookup
shot 29_sky_overcast            sky_overcast
shot 30_sky_drizzle             sky_drizzle
shot 31_sky_rain                sky_rain
shot 36_link_post               link_post
shot 38_machine_daylight        machine_daylight
shot 42_machine_collar          machine_collar
shot 43_teach_overshoulder      teach_overshoulder
shot 44_teach_wide              teach_wide
shot 46_pendant_product         pendant_product
shot 50_commit_in               commit_in
shot 51_commit_out              commit_out
shot 52_commit_wide             commit_wide
shot 48_interface_collar        interface_collar
# second pass: variants
shot 02_pithead_high            pithead_high
shot 04_pithead_from_course     pithead_from_course
shot 06_headframe_threequarter  headframe_threequarter
shot 08_headframe_insitu        headframe_insitu
shot 10_yard_overhead           yard_overhead
shot 12_yard_wreck              yard_wreck
shot 13_yard_insitu_dusk        yard_insitu
shot 54_shaft_recovery          shaft_recovery
shot 17_course_root             course_root
shot 18_course_roofed_alt       course_roofed
shot 21_shaft_hole              shaft_hole
shot 28_descent_insitu_leaving  descent_insitu_leaving
shot 32_sky_dusk                sky_dusk
shot 33_sky_night               sky_night
shot 34_sky_sun_alt             sky_sun
shot 35_rain_shell              rain_shell
shot 37_link_insitu             link_insitu
shot 39_machine_fresh_veteran   machine_fresh_veteran
shot 40_machine_lineup          machine_lineup
shot 41_machine_rival_daylight  machine_rival_daylight
shot 45_teach_insitu            teach_insitu
shot 47_terminal_bench          terminal_bench
shot 49_interface_terminal_dusk interface_terminal_dusk
shot 53_teach_cave_truth        teach_cave_truth
echo "BATCH DONE" | tee -a "$LOG"
