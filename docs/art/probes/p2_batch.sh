#!/usr/bin/env bash
# Second-pass probe batch. Every image is lit ONLY by sources the fiction supplies.
set -u
BL="/c/Program Files/Blender Foundation/Blender 5.2/blender.exe"
OUT="${1:?output dir}"
mkdir -p "$OUT"
Q="--samples 20 --res 760x480"
shot () { name="$1"; shift
  if [ -f "$OUT/$name.png" ]; then echo "skip $name"; return; fi
  echo "=== $name"
  "$BL" -b -P docs/art/probes/p2_shot.py -- "$@" --out "$OUT/$name.png" >/dev/null 2>&1     && echo "ok $name" || echo "FAIL $name"
}
shot a_wide_0070_a30 --mode wide --lamp 70  --albedo 0.30 $Q
shot a_wide_0600_a30 --mode wide --lamp 600 --albedo 0.30 $Q
shot a_wide_0600_a10 --mode wide --lamp 600 --albedo 0.10 $Q
shot a_wide_0600_a50 --mode wide --lamp 600 --albedo 0.50 $Q
shot b_beam_fog050 --mode beam --lamp 600 --albedo 0.30 --fog 0.05 $Q
shot c_ahead_600   --mode ahead --lamp 600 --albedo 0.30 --fog 0.02 $Q
shot d_rim_000 --mode rim --rim 0.0 --albedo 0.30 --modules "side_l=passive_acoustic,side_r=passive_acoustic,top_r=beacon_rack,belly=cargo_bay" $Q
shot d_rim_060 --mode rim --rim 6.0 --albedo 0.30 --modules "side_l=passive_acoustic,side_r=passive_acoustic,top_r=beacon_rack,belly=cargo_bay" $Q
shot e_waterline --mode wide --lamp 600 --albedo 0.30 --waterline 0.22 --wet 0.9 $Q
shot f_assayer_dormant --mode assayer --lamp 900 --assayer-w 0   --aim 28 --hammer 0.0 $Q
shot f_assayer_wind    --mode assayer --lamp 0   --assayer-w 700 --aim 28 --hammer 0.85 --fog 0.012 $Q
shot g_shaft --mode shaft --fog 0.018 $Q
shot h_wreck --mode wreck --wear 0.9 $Q
echo "BATCH DONE"
