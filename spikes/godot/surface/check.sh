#!/usr/bin/env bash
# Parse / shader gate for the surface spike.
#
# WHY THIS EXISTS. A GDScript parse error does not stop Godot: it loads a broken
# scene, prints once, and then spins. A capture run against a broken build looks
# exactly like a slow one, and it cost ten minutes of wall clock before anybody
# noticed the shots directory had not been written to. So nothing captures,
# benchmarks or commits until this returns 0.
#
#   ./check.sh   ->  exit 0 clean, exit 1 with the errors printed
set -u
GODOT="${GODOT:-C:/Users/jackh/Downloads/Godot_v4.7.2-stable_win64.exe/Godot_v4.7.2-stable_win64.exe}"
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="$("$GODOT" --headless --path "$HERE" --quit-after 3 -- --mode=free 2>&1)"
BAD="$(printf '%s\n' "$OUT" | grep -iE 'SCRIPT ERROR|SHADER ERROR|Parse Error|Compile Error|Failed to load script|Shader compilation failed' | grep -v 'translate' || true)"
if [ -n "$BAD" ]; then
	printf '%s\n' "$OUT" | grep -iE -A2 -B2 'SCRIPT ERROR|SHADER ERROR|Parse Error|Compile Error|Failed to load|compilation failed' | head -60
	echo "CHECK: FAIL"
	exit 1
fi
printf '%s\n' "$OUT" | grep -E 'layout hash|valley ms|town ms|ground ms|scatter ms|TOTAL GEN|prop instances|multimeshes'
echo "CHECK: OK"
exit 0
