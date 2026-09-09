#!/bin/sh
# Shader compile gate: headless never compiles a shader, so a GLSL error silently
# falls the material back to white and the frame still renders.
cd "$(dirname "$0")" || exit 1
G="C:/Users/jackh/Downloads/Godot_v4.7.2-stable_win64.exe/Godot_v4.7.2-stable_win64.exe"
out=$(timeout -k 5 120 "$G" --path . --resolution 640x360 --position 40,40 -- --shot=01 --shotdir=shots/_probe 2>&1)
echo "$out" | grep -E "SHADER ERROR|Shader compilation failed|ERROR" && { echo "SHADER FAILED"; exit 1; }
echo "$out" | grep -E "adapter|shot |points"
echo "SHADERS OK"
