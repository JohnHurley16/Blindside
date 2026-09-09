#!/bin/sh
cd "$(dirname "$0")" || exit 1
G="C:/Users/jackh/Downloads/Godot_v4.7.2-stable_win64.exe/Godot_v4.7.2-stable_win64.exe"
out=ablation.txt
: > $out
run() {
  echo "=== $1 ($2) ===" >> $out
  timeout -k 5 95 "$G" --path . --resolution 1280x720 --position 50,50 -- --walkonly --speed=5.0 $2 > ab_$1.log 2>&1
  grep -E "^fps|^gpu ms|^cpu ms|^draw calls|^primitives|^video mem|^gen dressing|^prop instances" ab_$1.log >> $out
}
run baseline ""
run novis "--novis"
run noprops "--noprops"
run noshadow "--noshadow"
run nofog "--nofog"
run lean "--noshadow --nofog"
echo "ABLATE_DONE" >> $out
