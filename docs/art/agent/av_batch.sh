#!/usr/bin/env bash
# Agent-direction probe batch, for docs/art/ART-DIRECTION.md.
#
# --out must be ABSOLUTE: Blender resolves relative paths against its own cwd, not the
# shell's, and will happily write to C:/docs/art/agent/ if you let it.
set -u
BL="/c/Program Files/Blender Foundation/Blender 5.2/blender.exe"
ROOT="C:/Users/jackh/documents/programming/Blindside"
OUT="$ROOT/docs/art/agent"
Q="--samples 40 --res 960x600"

shot () { name="$1"; sh="$2"
  echo "=== $name"
  "$BL" -b -P "$ROOT/docs/art/agent/av_probe.py" -- --shot "$sh" --out "$OUT/$name.png" $Q \
    >/dev/null 2>&1 && echo "ok $name" || echo "FAIL $name"
}

# the lamp: same power, same frame, sign flipped. §0
shot av_01_lamp_asbuilt        lamp_asbuilt
shot av_02_lamp_fixed          lamp_fixed
# wear: isotropic against three gravity masks extended to the leg materials. §4.1
shot av_03_wear_current        wear_current
shot av_04_wear_directed       wear_directed
# team identity: value inversion, today's hue-only scheme, and a dust control. §4.3
shot av_05_team_player         team_player
shot av_06_team_rival          team_rival
shot av_07_team_hue            team_hue
shot av_12_team_player_lowdust team_player_lowdust
shot av_13_team_rival_lowdust  team_rival_lowdust
# the loadout in silhouette, backlit, machine between camera and pool. §4.4
shot av_08_sil_bare            sil_bare
shot av_09_sil_loaded          sil_loaded
# the wreck: full collapse against ride-height-only. §6.2
shot av_10_wreck               wreck
shot av_11_wreck_ridehonly     wreck_ridehonly
echo "BATCH DONE"
echo "now: .venv/Scripts/python.exe docs/art/agent/av_measure.py"
