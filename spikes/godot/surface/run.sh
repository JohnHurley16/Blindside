#!/usr/bin/env bash
# Run the surface spike, reimporting first.
#
# THIS EXISTS BECAUSE OF A REAL BUG. A game run does NOT reimport .glsl: it
# loads the cached SPIR-V in .godot/imported/. So an edit to lens.glsl is
# silently ignored until the editor has been run over the project once, and a
# measurement taken after such an edit is a measurement of the OLD shader.
# It cost one bogus HDR probe. Every run goes through here.
set -u
GODOT="${GODOT:-C:/Users/jackh/Downloads/Godot_v4.7.2-stable_win64.exe/Godot_v4.7.2-stable_win64.exe}"
HERE="$(cd "$(dirname "$0")" && pwd)"
if [ "$HERE/lens.glsl" -nt "$(ls "$HERE"/.godot/imported/lens.glsl-*.res 2>/dev/null | head -1)" ]; then
  echo "[reimport: lens.glsl is newer than its SPIR-V]"
  "$GODOT" --headless --path "$HERE" --import >/dev/null 2>&1
  find "$HERE/shots" -name "*.import" -delete 2>/dev/null
fi
n=$(tasklist //FI "IMAGENAME eq Godot_v4.7.2-stable_win64.exe" 2>/dev/null | grep -c Godot_ )
echo "[stray godot processes: $n]"
"$GODOT" --path "$HERE" --resolution 1920x1080 -- "$@"
