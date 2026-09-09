#!/bin/sh
# The performance ablation. Same walk at 5.0 m/s so each run is short, which is
# why the absolute fps is lower than the 1.7 m/s walk across the board.
#
# INTERLEAVED. This laptop's GPU falls from 2100 MHz to 780 MHz as it heats, and
# it does not come back down inside a useful time, so a table taken as ten
# consecutive runs measures the heatsink and not the renderer -- the first
# version of this script produced exactly that, with the baseline at 7.9 ms in
# one pass and 34.5 ms in the next. A baseline row is therefore run immediately
# before AND after every variant, and a technique's cost is the variant minus
# the mean of its two neighbouring baselines. The thermal state of each run is
# printed alongside it so the reader can see the drift rather than trust it away.
cd "$(dirname "$0")" || exit 1
G="C:/Users/jackh/Downloads/Godot_v4.7.2-stable_win64.exe/Godot_v4.7.2-stable_win64.exe"
out=ablation.txt
: > $out
n=0
run() {
  n=$((n + 1))
  powershell -NoProfile -Command "Get-Process -Name 'Godot_v4.7.2-stable_win64' -EA SilentlyContinue | Stop-Process -Force" >/dev/null 2>&1
  echo "=== $n $1 ($2) ===" >> $out
  ./cool.sh >> $out
  timeout -k 5 120 "$G" --path . --resolution 1280x720 --position 50,50 -- --walkonly --speed=5.0 $2 > ab_last.log 2>&1
  grep -E "^fps|^gpu ms|^cpu ms|^draw calls|^primitives|^video mem|^gen dressing|^prop instances|^shell tri" ab_last.log >> $out
}
run baseline ""
for v in "nopom --nopom" "noscales --noscales" "nowater --nowater" "ssao --ssao" \
         "novis --novis" "noprops --noprops" "noshadow --noshadow" "nofog --nofog" \
         "lean --noshadow_--nofog"; do
  name=$(echo "$v" | cut -d' ' -f1)
  flag=$(echo "$v" | cut -d' ' -f2 | tr '_' ' ')
  run "$name" "$flag"
  run baseline ""
done
powershell -NoProfile -Command "Get-Process -Name 'Godot_v4.7.2-stable_win64' -EA SilentlyContinue | Stop-Process -Force" >/dev/null 2>&1
echo "ABLATE_DONE" >> $out
