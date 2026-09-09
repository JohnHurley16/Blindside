#!/usr/bin/env bash
# Renders the cave vision board. One Blender process per group of shot prefixes (the
# 15 s start-up is paid once per group, not once per frame). Flat output to _render/,
# then `sort_into_concepts.py` copies each frame into cave/<concept>/NN_name.png.
#
#   bash cave_batch.sh                 # every group, skipping frames that already exist
#   bash cave_batch.sh b12_,b13_       # one group (comma-separated prefixes)
#   Q="--samples 64 --res 1400x875" bash cave_batch.sh b1_   # a hero pass
#
# --outdir must be ABSOLUTE: Blender resolves relative paths against its own cwd.
# Per-shot OK/FAIL lines stream to stdout as they happen; the full Blender log per group
# is in _logs/batch_<group>.txt.
set -u
BL="/c/Program Files/Blender Foundation/Blender 5.2/blender.exe"
HERE="C:/Users/jackh/documents/programming/Blindside/docs/art/vision/cave"
Q="${Q:---samples 40 --res 960x600}"
mkdir -p "$HERE/_render" "$HERE/_logs"

group () { pre="$1"
  tag=$(echo "$pre" | tr -d ',_')
  s=$(date +%s)
  "$BL" -b -P "$HERE/cave_probe.py" -- --shots "$pre" --outdir "$HERE/_render" --skip-existing $Q 2>&1 \
    | tee "$HERE/_logs/batch_$tag.txt" | grep --line-buffered -E "^(OK|FAIL|SKIP) |Traceback|Error:"
  echo "group $pre done in $(( $(date +%s) - s )) s"
}

if [ $# -gt 0 ]; then
  for g in "$@"; do group "$g"; done
else
  group b1_,b2_,b3_
  group b4_,b5_,b6_
  group b7_,b8_,b9_,b10_
  group b11_,b12_,b13_
  group b14_,b15_,b16_,b17_
fi
echo "BATCH DONE"
