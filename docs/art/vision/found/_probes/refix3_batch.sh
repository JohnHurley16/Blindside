#!/usr/bin/env bash
# Third pass: the two beacon frames that still did not read after refix2 (the product shot
# was framed too tight; the chain's pilots were four dim pixels each) -- re-rendered with the
# camera moved back and the pilot halo (a bloom stand-in, see found_common.beacon).
set -u
BL="/c/Program Files/Blender Foundation/Blender 5.2/blender.exe"
ROOT="C:/Users/jackh/documents/programming/Blindside"
OUT="$ROOT/docs/art/vision/found"
Q="${Q:---samples 40 --res 960x600}"
f () { concept="$1"; name="$2"; sh="$3"
  s=$(date +%s)
  "$BL" -b -P "$OUT/_probes/found_probe.py" -- --shot "$sh" --out "$OUT/$concept/$name.png" $Q > "$OUT/_probes/log_$sh.txt" 2>&1 \
    && echo "ok $concept/$name $(( $(date +%s) - s )) s" || echo "FAIL $concept/$name (see _probes/log_$sh.txt)"
}
f beacon 01_clear_product  bcn_clear_product
f beacon 04_situ_chain     bcn_situ_chain
f beacon 07_situ_sump      bcn_situ_sump
echo "REFIX3 DONE"
