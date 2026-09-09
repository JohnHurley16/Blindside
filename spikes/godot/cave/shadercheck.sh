#!/bin/sh
# Shader compile gate. check.sh is headless and NEVER compiles a shader, so a
# GLSL error in rock/stone/kit/water silently falls the material back to white
# and the frame still renders -- which cost this pass an hour of debugging a
# "flat white floor" that was a one-line type error.
cd "$(dirname "$0")" || exit 1
G="C:/Users/jackh/Downloads/Godot_v4.7.2-stable_win64.exe/Godot_v4.7.2-stable_win64.exe"
out=$(timeout -k 5 90 "$G" --path . --resolution 640x360 --position 50,50 -- --shotsonly --shotdir=_probe 2>&1)
echo "$out" | grep -E "SHADER ERROR|Shader compilation failed" && { echo "SHADER FAILED"; exit 1; }
echo "SHADERS OK"
