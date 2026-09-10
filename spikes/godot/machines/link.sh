#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# BLINDSIDE -- link the shared machine layer into the environment spikes.
#
# WHY A LINK AND NOT A COPY, AND NOT AN ADDON.
#
# `shared/` is the machine layer: the four chassis as .glb, the ART section 4
# shaders, the palette book, the gait/IK driver, and the hero-machine identity.
# Three Godot projects need it -- this spike, the cave and the pit-head -- and
# the trailer's whole problem is that the SAME machine has to appear in all of
# them. A copy in each project is the exact failure mode TRAILER 11.1 names:
# three copies drift, and the drift is invisible until it is on screen.
#
# Godot has no multi-root res://. An `addons/` plugin does not help: an addon
# is still a directory inside each project, so it is still three copies. The
# only mechanism that gives one physical copy with three res:// names is a
# filesystem link, and on Windows a DIRECTORY JUNCTION needs no privilege and
# is transparent to every Win32 file API, so Godot's importer walks it as a
# normal folder.
#
# THE ONE THING THIS COSTS. Every project mounts it at the SAME path,
# res://machines/, including this spike -- which is why the layer lives in
# machines/machines/ rather than at this project's root. An identical mount
# path is what keeps models/*.glb.import stable; if the paths differed, each
# project would rewrite the others' import files every time it opened. And
# nothing inside the layer may write a res:// literal even so: machine.gd
# resolves every path against its own script path, which is one function and
# makes the layer relocatable.
#
# TWO CONSUMERS TODAY, MORE LATER, AND THAT IS THE POINT.
#
# The cave is wired. The pit-head is being rebuilt as the valley
# (DESIGN-PRINCIPLES 10) and will need the same machine in the same shots the
# moment it stands up; the lidar spike needs it to draw what the machine
# believes about itself. Neither is a port: it is this script with the project
# named, plus `rig.fleet = ...` in that project's cinema setup and one
# `machine` block per shot. Which projects get the link is an ARGUMENT and not
# a hard-coded list, so adopting it costs one word:
#
#   ./link.sh                 cave and surface (the default)
#   ./link.sh cave            just the cave
#   ./link.sh cave valley cloud
#
# Run this after a fresh clone. It is idempotent.
# ---------------------------------------------------------------------------
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
SRC="$(cygpath -w "$HERE/machines" 2>/dev/null || echo "$HERE/machines")"
PROJECTS="${*:-cave surface}"
for proj in $PROJECTS; do
  if [ ! -d "$HERE/../$proj" ]; then
    echo "[$proj] no such project directory -- skipped"
    continue
  fi
  DST_U="$HERE/../$proj/machines"
  if [ -e "$DST_U" ]; then
    echo "[$proj] already linked"
    continue
  fi
  DST="$(cygpath -w "$(cd "$HERE/../$proj" && pwd)/machines" 2>/dev/null || echo "$DST_U")"
  # No quotes around the two paths: Git Bash hands cmd.exe the string as-is and
  # escaped quotes inside it come out as literal characters, which mklink reads
  # as part of the filename. The repo has no spaces in its path; if that ever
  # changes this needs a different quoting strategy, not more backslashes.
  cmd //c "mklink /J $DST $SRC" || echo "[$proj] FAILED"
done
# A project that has just gained (or just moved) the layer needs ONE editor
# pass to import the .glb -- a game run never imports, it loads the cache. If
# the machines come back missing, this is why:
echo
echo "then, once per project:  <godot> --headless --path <project> --import"
