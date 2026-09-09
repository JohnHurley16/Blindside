#!/bin/sh
cd "$(dirname "$0")" || exit 1
G="C:/Users/jackh/Downloads/Godot_v4.7.2-stable_win64.exe/Godot_v4.7.2-stable_win64.exe"
out=scaling.txt
: > $out
for L in 60 120 240 480 960; do
  timeout -k 5 180 "$G" --path . --resolution 1280x720 --position 50,50 -- --walkonly --speed=60 --len=$L > sc.log 2>&1
  echo "--- len=$L cells ($(echo "$L" | awk '{printf "%.1f", $1*0.6}') m) ---" >> $out
  grep -E "^gen topology|^gen dressing|^gen total|^chunks|^shell tri|^prop inst|^stations|^open cells|^fps " sc.log >> $out
done
echo "SCALE_DONE" >> $out
