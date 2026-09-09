#!/bin/sh
# parse/compile gate. A GDScript parse error otherwise becomes a window that
# spams one error per frame for ever.
cd "$(dirname "$0")" || exit 1
G="C:/Users/jackh/Downloads/Godot_v4.7.2-stable_win64.exe/Godot_v4.7.2-stable_win64.exe"
out=$("$G" --path . --headless --quit-after 3 2>&1)
echo "$out" | grep -E "Parse Error|Compile Error|Failed to load script|SCRIPT ERROR|Invalid|error\(" && { echo "FAILED"; exit 1; }
echo "$out" | grep -E "adapter|materials|render" 
echo "OK"
