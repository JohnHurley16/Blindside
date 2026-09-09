#!/bin/sh
# parse/compile gate. Headless, so it never compiles a shader -- see shadercheck.sh.
cd "$(dirname "$0")" || exit 1
G="C:/Users/jackh/Downloads/Godot_v4.7.2-stable_win64.exe/Godot_v4.7.2-stable_win64.exe"
out=$("$G" --path . --headless --quit-after 3 2>&1)
echo "$out" | grep -E "Parse Error|Compile Error|Failed to load script|SCRIPT ERROR|Invalid" && { echo "FAILED"; exit 1; }
echo "$out" | grep -E "adapter|points|match|truth mesh"
echo "OK"
