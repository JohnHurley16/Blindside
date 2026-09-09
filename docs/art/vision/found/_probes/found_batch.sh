#!/usr/bin/env bash
# Renders every 'found' shot at 960x600, 40 spp, into docs/art/vision/found/<concept>/.
# --out must be ABSOLUTE (Blender resolves relative paths against its own cwd).
set -u
BL="/c/Program Files/Blender Foundation/Blender 5.2/blender.exe"
ROOT="C:/Users/jackh/documents/programming/Blindside"
OUT="$ROOT/docs/art/vision/found"
Q="${Q:---samples 40 --res 960x600}"
shot () { concept="$1"; name="$2"; sh="$3"
  mkdir -p "$OUT/$concept"
  s=$(date +%s)
  "$BL" -b -P "$ROOT/docs/art/vision/found/_probes/found_probe.py" -- --shot "$sh" --out "$OUT/$concept/$name.png" $Q \
    > "$OUT/_probes/log_$sh.txt" 2>&1 && echo "ok $concept/$name $(( $(date +%s) - s )) s" || echo "FAIL $concept/$name (see _probes/log_$sh.txt)"
}
shot deposit   01_clear_face          dep_clear_face
shot deposit   02_clear_after         dep_clear_after
shot deposit   03_clear_swatch_lit    dep_clear_swatch_lit
shot deposit   04_clear_swatch_unlit  dep_clear_swatch_unlit
shot deposit   05_clear_plan          dep_clear_plan
shot deposit   06_situ_find           dep_situ_find
shot deposit   07_situ_loading        dep_situ_loading
shot deposit   08_situ_worked         dep_situ_worked
shot wreck     01_clear_front         wreck_clear_front
shot wreck     02_clear_back          wreck_clear_back
shot wreck     03_clear_handle        wreck_clear_handle
shot wreck     04_situ_found          wreck_situ_found
shot wreck     05_situ_6m             wreck_situ_6m
shot wreck     06_situ_pair           wreck_situ_pair
shot wreck     07_situ_recovery       wreck_situ_recovery
shot beacon    01_clear_product       bcn_clear_product
shot beacon    02_clear_rack          bcn_clear_rack
shot beacon    03_clear_drop          bcn_clear_drop
shot beacon    04_situ_chain          bcn_situ_chain
shot beacon    05_situ_range          bcn_situ_range
shot beacon    06_situ_twins          bcn_situ_twins
shot beacon    07_situ_sump           bcn_situ_sump
shot discovery 01_clear_stations      disc_clear_stations
shot discovery 02_clear_pose          disc_clear_pose
shot discovery 04_situ_pose           disc_situ_pose
shot discovery 05_situ_spent          disc_situ_spent
shot discovery 06_situ_rival          disc_situ_rival
echo "FOUND BATCH DONE"
