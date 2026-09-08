#!/usr/bin/env bash
#
# assert-empty-sim.sh -- the parallel-window assertion (BLD-40; BLD-66 re-runs it).
#
# Phase 0 is built in parallel with Phases 1 and 2, against a sim that must stay empty
# until the Phase 2 gate report exists (CLAUDE.md build order: "Do not start a phase whose
# predecessor's gate has not been met"). The harness is allowed to be finished; the sim is
# not allowed to have started. Nothing in a compiler or a test enforces that -- a plausible
# Cave, a first Sensor, a Belief with one field would all build and all pass -- so it is
# enforced here, by naming exactly what Phase 0 needs and failing on anything else.
#
# It is a shape check, not a semantic one: it reads declarations, so a Phase 3 type hidden
# under a Phase 0 name would pass -- `struct Grid` that is a cave, `fn step` that propagates
# sound. That is the same trade the determinism lint makes, for the same reason: it guards
# against drift, not against a determined author. Two holes an adversarial verifier found
# ARE closed, because both were accidents waiting rather than malice: a compound name
# (`SensorRig` against a `Sensor\b` pattern) and an orphan .rs file that lib.rs never
# declares.
#
# Usage:  tools/assert-empty-sim.sh [--root DIR] [-q]
# Exit:   0 the window held, 1 at least one check failed, 2 could not run.

set -uo pipefail

root=""
quiet=0
while [ $# -gt 0 ]; do
  case "$1" in
    --root)
      root="${2:-}"
      [ -n "$root" ] || { echo "assert-empty-sim: --root needs a DIR" >&2; exit 2; }
      shift 2
      ;;
    -q|--quiet) quiet=1; shift ;;
    -h|--help) sed -n '3,17p' "$0" | sed 's/^#\{0,1\} \{0,1\}//'; exit 0 ;;
    *) echo "assert-empty-sim: unexpected argument: $1" >&2; exit 2 ;;
  esac
done

if [ -z "$root" ]; then
  root="$(cd "$(dirname "$0")/.." && pwd)"
fi
if [ ! -d "$root/crates/blindside-sim/src" ]; then
  echo "assert-empty-sim: $root is not the workspace root (no crates/blindside-sim/src)" >&2
  exit 2
fi

sim="$root/crates/blindside-sim/src"
fails=0

say()  { [ "$quiet" -eq 1 ] || printf '%s\n' "$*"; }
ok()   { say "  ok    $1"; }
bad()  { printf '  FAIL  %s\n' "$1"; fails=$((fails + 1)); }

# Compare a found set against an expected set, both sorted. $1 label, $2 want, $3 found.
compare_set() {
  label="$1"
  want="$(printf '%s\n' "$2" | awk 'NF' | sort)"
  found="$(printf '%s\n' "$3" | awk 'NF' | sort)"
  if [ "$want" = "$found" ]; then
    ok "$label"
  else
    bad "$label"
    printf '        expected (<) vs found (>):\n'
    diff <(printf '%s\n' "$want") <(printf '%s\n' "$found") | sed 's/^/          /'
  fi
}

# Count item declarations in one file. Phase 0 leaves two files with none.
count_items() {
  grep -cE '^ *(pub(\([a-z]+\))? )?(unsafe )?(fn|struct|enum|trait|impl|union|const|static|type|mod|macro_rules!)\b' "$1"
}

say "assert-empty-sim: the Phase 0 parallel window, at $root"
say ""
say "blindside-sim"

# --- 1. the module list --------------------------------------------------------------
# A new module in the sim is a new answer to "what does Phase 0 need", and Phase 0 needs
# none. sensor, belief, cave, acoustics and policy are all Phase 3.
mods="$(grep -hE '^ *(pub )?mod [a-z_]+;' "$sim/lib.rs" | sed -E 's/.*mod ([a-z_]+);.*/\1/')"
compare_set "module list is the Phase 0 set" \
"diagnostics
fxmath
golden
golden_tables
hash
ids
record
rng
testing
world" "$mods"

# --- 1b. the files on disk match the module list -------------------------------------
# Check 1 reads lib.rs, so a .rs file nobody declares is invisible to it. Such a file does
# not compile in and cannot affect a hash, but it is where a Phase 3 module gets parked
# while its author "finishes it later", and it is free to catch.
files="$(cd "$sim" && ls *.rs 2>/dev/null | sed 's/\.rs$//' | grep -v '^lib$')"
compare_set "the .rs files under src/ are exactly those modules" "$mods" "$files"

# --- 2. World's fields ---------------------------------------------------------------
# ARCHITECTURE.md's Phase 3 World has cave, agents, beacons, wrecks, deposits, ancients
# and acoustics. Phase 0 has a tick, a placeholder roster the hash can watch move, the
# injection fixture's target, and one deliberately excluded cache field.
fields="$(awk '/^pub\(crate\) struct World \{/{f=1;next} f&&/^\}/{exit} f' "$sim/world.rs" \
          | grep -E '^ *pub [a-z_]+:' | sed -E 's/^ *pub ([a-z_]+):.*/\1/')"
compare_set "World's fields are the Phase 0 set" \
"agents
inject_fold
moved_last_step
tick" "$fields"

# --- 3. fxmath declares nothing ------------------------------------------------------
# BLD-24 built fxmath.rs as a header with no implementations: the address for sqrt/sin/cos
# exists so a Phase 3 author cannot honestly put them anywhere else. An item here means
# fixed-point transcendentals were written during the parallel window.
n="$(count_items "$sim/fxmath.rs")"
if [ "$n" -eq 0 ]; then
  ok "fxmath.rs declares no items (header only)"
else
  bad "fxmath.rs declares $n item(s); Phase 0 leaves it a header"
fi

# --- 4. Belief does not exist yet ----------------------------------------------------
# ARCHITECTURE.md makes Belief the public half of the boundary. Phase 0 has no sensors, so
# there is nothing for a Belief to hold; an empty one written now would be a guess at the
# Phase 3 shape that the Phase 1 report is meant to inform.
belief="$(grep -rlE '^ *(pub )?(struct|enum|trait|type) Belief\b' "$root/crates" 2>/dev/null || true)"
if [ -z "$belief" ]; then
  ok "no Belief type is declared anywhere under crates/"
else
  bad "Belief is declared in: $(printf '%s ' $belief)"
fi

# --- 5. no Phase 3 subject matter in the constrained crates --------------------------
# Declarations only. What must not appear is a type or function that DOES something -- a
# sensor that samples, a field that propagates, a generator that generates.
say ""
say "no Phase 3 subject matter in blindside-sim / -gen / -content"
# The subject words match as PREFIXES, because a Phase 3 name is a compound: SensorRig,
# CaveGrid, BeliefUpdater, AncientCycle. Matching `Sensor\b` caught none of them, which a
# verifier demonstrated by adding `pub struct SensorRig` to an allowed module and getting a
# pass. The stable-ID types are the deliberate exception: ARCHITECTURE.md fixes them now and
# DETERMINISM.md rule 7 requires them, and they carry no behaviour, so they are spared by
# name rather than by the pattern being loose.
pattern='^ *(pub(\([a-z]+\))? )?(unsafe )?(struct|enum|trait|impl|fn) +(Sensor|Belief|Occupancy|Contact|Acoustic|Cave|Biome|Deposit|Ancient|Beacon|Wreck|Hazard|Policy|Predicate|BtNode|Pose|SelfReport|Inventory|Chassis|Loadout|Module)[A-Za-z0-9_]*'
spared='\b(SensorId|ModuleId|ChassisId|PredicateId|ActionId|AncientKindId|BiomeId|ModeId|BeaconId|DepositId|WreckId|ContactId)\b'
# BLD-30 requires Loadout, PolicyRef and Command to exist as EMPTY stubs so MatchRecord
# has its shape. Only the unit-struct spelling is spared: give one a field and the line
# stops ending in `;`, and this check fails again -- which is exactly when it should.
stubs=':[0-9]+: *pub struct (Loadout|PolicyRef|Command);$'
hits="$(grep -rnE "$pattern" \
        "$root/crates/blindside-sim/src" \
        "$root/crates/blindside-gen/src" \
        "$root/crates/blindside-content/src" 2>/dev/null | grep -vE "$spared" | grep -vE "$stubs" || true)"
if [ -z "$hits" ]; then
  ok "no sensor, belief, acoustic, cave, ancient or policy declaration"
else
  bad "Phase 3 subject matter is declared:"
  printf '%s\n' "$hits" | sed 's/^/          /'
fi

# --- 6. the stub crates are still stubs ----------------------------------------------
say ""
say "the stub crates"
n="$(count_items "$root/crates/blindside-gen/src/lib.rs")"
if [ "$n" -eq 0 ]; then
  ok "blindside-gen declares no items (a lint target, not yet a generator)"
else
  bad "blindside-gen declares $n item(s); world generation is Phase 3 (BLD-71)"
fi

vm_items="$(grep -hE '^ *(pub(\([a-z]+\))? )?(unsafe )?(fn|struct|enum|trait|impl|union|const|static|type|macro_rules!)\b' "$root/crates/blindside-vm/src/lib.rs" \
            | sed -E 's/^ *(pub(\([a-z]+\))? )?(unsafe )?(fn|struct|enum|trait|impl|union|const|static|type|macro_rules!) *//' \
            | sed -E 's/[ <({;].*//')"
compare_set "blindside-vm declares only VmBudget (Phase 4 writes the interpreter)" "VmBudget" "$vm_items"

# --- 7. blindside-content is a pack hasher, not a registry ---------------------------
# ARCHITECTURE.md's content crate holds sensor, module, chassis and ancient definitions.
# Phase 0 needs exactly one thing from it: the content pack hash every replay carries
# (DETERMINISM.md, "Enforcement"). The registries are BLD-68.
content_items="$(awk '/^#\[cfg\(test\)\]/{exit} 1' "$root/crates/blindside-content/src/lib.rs" \
                 | grep -hE '^ *pub (fn|struct|enum|const) ' \
                 | sed -E 's/^ *pub (fn|struct|enum|const) *//' | sed -E 's/[ <({;:].*//')"
compare_set "blindside-content's public items are the pack hash and nothing else" \
"CONTENT_SCHEMA
EMPTY_PACK_HASH
PackEntry
ContentPack
PackError
content_hash
empty
from_entries
read_dir
entries
hash" "$content_items"

say ""
if [ "$fails" -eq 0 ]; then
  say "assert-empty-sim: OK -- the sim is still empty; Phase 0 built only tooling."
  exit 0
fi
printf 'assert-empty-sim: FAIL -- %d check(s) failed. The parallel window did not hold.\n' "$fails"
printf 'Either the sim grew during Phase 0 and the change should be reverted, or the\n'
printf 'Phase 2 gate has passed and this script needs its new expected set in the same\n'
printf 'commit as the sim change -- never afterwards, and never quietly.\n'
exit 1
