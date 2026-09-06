# Phase 0 harness: build, test, run

Rust workspace for the BLINDSIDE determinism harness (`docs/PHASE-0-HARNESS.md`). The sim
it exercises is deliberately almost empty — two agents whose fixed-point positions random
walk from a stateless RNG — because the tooling, not the sim, is the deliverable. That is
enough for the state hash to change every tick and for an injected non-determinism to have
somewhere to hide.

## Layout

```
Cargo.toml                    workspace root
rust-toolchain.toml           pins stable
crates/blindside-sim          deterministic core (constrained, see docs/DETERMINISM.md)
crates/blindside-vm           bytecode VM (constrained) - stub
crates/blindside-content      content definitions - stub
crates/blindside-gen          world generation (constrained) - stub
crates/blindside-harness      headless runner, canary, record/verify, bisect, batch
                              (unconstrained; builds the `harness` binary)
tools/determinism-lint        CI lint for the constrained crates
```

`Sim::state_debug()` and `Sim::perturb_for_test()` expose ground truth, so they live
behind `blindside-sim`'s `test-hooks` feature. `blindside-harness` is the only crate that
enables it; the canary's field-level diffs and `--inject` depend on it.

## Build

```
cargo build --workspace
cargo build --workspace --release      # for throughput numbers
```

## Test

```
cargo test --workspace
```

`blindside-sim` checks that two sims with the same seed hash identically for 1000 ticks,
that the hash changes every tick, that different seeds differ, that the `state_debug()`
dump and the hash move together (change one and the other changes too — they are meant to
cover the same fields), and that `DeterministicRng::draw` is repeatable and
order-independent. One test pins the literal hash at tick 1000 for seed `0xDEADBEEF`; that
constant is the cross-platform anchor CI's `cross-platform` job checks the other way round.

`blindside-harness` checks the round trips the CLI is made of: record then verify is clean,
a log with one tampered hash reports that tick, a log belonging to another record is
rejected, an injected divergence is caught in the tick it was injected, and a log corrupted
from tick 1234 onward is bisected to tick 1234 in at most 16 re-runs.

`determinism-lint`'s tests are listed under "Determinism lint" below.

## Tools

Two things trip people up before anything else:

- **The package is `blindside-harness`; only the binary is `harness`.** `cargo run -p
  harness` fails, with ``error: package(s) `harness` not found in workspace``. Use
  `cargo run -p blindside-harness -- <subcommand>`, or run the built binary directly at
  `target/release/harness` (`harness.exe` on Windows, which is the name in the usage lines
  below because they were pasted from a Windows run).
- **The hash sidecar is named after the replay.** `record --out replay.json` writes
  `replay.hashes.json`, not `hashes.json`. Pass `--hashes` to choose another name (CI
  does).

Subcommands, from `harness --help`. The top-level help prints only the one-line summary
of each; the Usage column is each subcommand's own `--help` line, verbatim:

| Subcommand | Usage | What it does |
|---|---|---|
| `run` | `harness.exe run <REPLAY>` | re-runs a `MatchRecord` to its tick count, compares the final hash against the recorded one, reports throughput |
| `canary` | `harness.exe canary [OPTIONS] --ticks <TICKS>` | two sims in lockstep, hashes compared every tick; `--inject` plants a `HashMap`-ordering desync, `--inject-tick` picks the tick, `--divergence` names the report file |
| `record` | `harness.exe record [OPTIONS] --seed <SEED> --ticks <TICKS> --out <OUT>` | runs a fresh match and writes the replay plus a per-tick hash log (`--hashes` names it) |
| `verify` | `harness.exe verify <REPLAY> <HASHES>` | re-runs a replay and checks *every* per-tick hash, not just the last |
| `bisect` | `harness.exe bisect [OPTIONS] [REPLAY] [HASHES]` | finds the first disagreeing tick and dumps the state there; `--from-divergence <FILE>` reproduces a `divergence.json` from `canary` instead |
| `batch` | `harness.exe batch [OPTIONS] --matches <MATCHES> --ticks <TICKS>` | N sequential matches, one thread, reports matches per hour; `--seed` is the first match's seed |

Exit codes are the same everywhere and are what CI keys off:

| Code | Meaning |
|---|---|
| 0 | ran, and everything that was compared agreed |
| 1 | a determinism failure: canary divergence, hash mismatch, reproduced desync |
| 2 | could not run: bad arguments, unreadable file, or a file that does not belong (wrong schema, wrong content hash, log from another seed) |

Exit 2 is not a determinism result. `verify replay.json other.hashes.json`, where the log
was recorded from a different seed, prints `harness: error: hash log seed 8 does not match
record seed 7` and exits 2 — it never ran the comparison, so nothing was proven either way.

### Worked example: record, verify, run, bisect

Every command and every line of output below was run in this workspace after
`cargo build --workspace --release`. The hashes are reproducible: they are the point. The
timings are not.

Record a 5000-tick match on seed 7:

```
$ cargo run -p blindside-harness --release --quiet -- record --seed 7 --ticks 5000 --out replay.json
recorded seed 7, 5000 ticks
replay: replay.json
hashes: replay.hashes.json  (5001 entries, ticks 0..=5000)
content hash: fac419fd5b17256e1b5936b050341963b88061362cb143271c5bbb4f1f5557a3
final hash: f9fe7a4608b97e6b3167a872d3f22fa03d23901f6ae877a6d46774b7e3215fa8
```

Two files. `replay.json` is the `MatchRecord` from `docs/ARCHITECTURE.md`, 271 bytes:

```
{
  "schema": 0,
  "seed": 7,
  "content_hash": "fac419fd5b17256e1b5936b050341963b88061362cb143271c5bbb4f1f5557a3",
  "loadouts": [],
  "policies": [],
  "commands": [],
  "ticks": 5000,
  "final_hash": "f9fe7a4608b97e6b3167a872d3f22fa03d23901f6ae877a6d46774b7e3215fa8"
}
```

`loadouts`, `policies` and `commands` are the match's inputs and are in the format now so
Phase 3 changes their type, not the file's shape. The Phase 0 sim takes none of them, so
they are always empty, and a record with anything in them is refused: `run` prints
`harness: error: Phase 0 sim accepts no loadouts, policies or commands; record has some`
and exits 2. `replay.hashes.json` is one hash per tick, `0..=5000`, so 5001 entries. Exit
0; the only failure mode is not being able to write.

Now the sidecar trap, then the real thing:

```
$ cargo run -p blindside-harness --release --quiet -- verify replay.json hashes.json
harness: error: cannot read hashes.json: The system cannot find the file specified. (os error 2)
```

Exit 2. (The text after the colon is the operating system's; Linux and macOS say `No such
file or directory`.) The file `record` actually wrote is `replay.hashes.json`:

```
$ cargo run -p blindside-harness --release --quiet -- verify replay.json replay.hashes.json
OK: 5000 ticks, every per-tick hash matches
final hash: f9fe7a4608b97e6b3167a872d3f22fa03d23901f6ae877a6d46774b7e3215fa8
```

Exit 0. `verify` checks all 5001 hashes and then the record's own final hash, so it catches
a divergence that heals before the last tick — which a final-hash-only check would miss.

`run` is the cheaper check: replay, compare the final hash only, report throughput.

```
$ cargo run -p blindside-harness --release --quiet -- run replay.json
replay: replay.json
seed: 7  ticks: 5000
final hash: f9fe7a4608b97e6b3167a872d3f22fa03d23901f6ae877a6d46774b7e3215fa8
recorded  : f9fe7a4608b97e6b3167a872d3f22fa03d23901f6ae877a6d46774b7e3215fa8
ticks/s: 69060773  (elapsed 0.000s)
OK: final hash matches record
```

Exit 0. Elapsed rounds to zero because a Phase 0 tick moves two agents; treat `ticks/s`
here as a measurement of the harness loop, not of a match. When the hashes disagree the
last line becomes `MISMATCH: final hash differs from record` and the exit code is 1:

```
$ cargo run -p blindside-harness --release --quiet -- run tampered.json
replay: tampered.json
seed: 7  ticks: 5000
final hash: f9fe7a4608b97e6b3167a872d3f22fa03d23901f6ae877a6d46774b7e3215fa8
recorded  : 09fe7a4608b97e6b3167a872d3f22fa03d23901f6ae877a6d46774b7e3215fa8
ticks/s: 68870523  (elapsed 0.000s)
MISMATCH: final hash differs from record
```

(`tampered.json` is `replay.json` with the first hex digit of `final_hash` changed by hand.)

`bisect` takes a replay and a hash log recorded on the *other* side — another machine,
another OS, another build — and finds the first tick they disagree on. Against its own log
there is nothing to find:

```
$ cargo run -p blindside-harness --release --quiet -- bisect replay.json replay.hashes.json
bisect: seed 7, 5000 ticks, local re-run vs replay.hashes.json
OK: 5000 ticks, no tick differs from the recorded hashes
```

Exit 0. To see it work you need a log that disagrees from some tick onward and never
re-converges, which is the shape of a real desync. Record a second match and splice its
tail onto the first log. In the pretty-printed log the hash for tick `t` is on line
`5 + t`, so tick 1233 is line 1238 and tick 1234 is line 1239:

```
$ cargo run -p blindside-harness --release --quiet -- record --seed 8 --ticks 5000 --out other.json
recorded seed 8, 5000 ticks
replay: other.json
hashes: other.hashes.json  (5001 entries, ticks 0..=5000)
content hash: fac419fd5b17256e1b5936b050341963b88061362cb143271c5bbb4f1f5557a3
final hash: 4036c6177eb91e23ff1caddf5559541abedf825e67ced610da7262663b39d303

$ head -n 1238 replay.hashes.json > spliced.hashes.json
$ tail -n +1239 other.hashes.json >> spliced.hashes.json
```

`spliced.hashes.json` still says `"seed": 7` and still covers 5000 ticks, so it passes the
structural check and looks exactly like a log from a machine that agreed with this one
until tick 1234:

```
$ cargo run -p blindside-harness --release --quiet -- bisect replay.json spliced.hashes.json
bisect: seed 7, 5000 ticks, local re-run vs spliced.hashes.json
DIVERGENCE at tick 1234  (found by binary search, 15 re-run(s))
  recorded: 9514f6910c9734e1decf2b71199121824d2ae75dc649806415be231150fafcb4
  local   : 2f0b6bc5e9e0c68ddb359e2ec9510d2bda14565dc030a82418a1a7e5ab6b70e1
  tick 1233 matched on both sides
local state at tick 1234 (hash 2f0b6bc5e9e0c68ddb359e2ec9510d2bda14565dc030a82418a1a7e5ab6b70e1):
  seed = 7
  tick = 1234
  agents.len = 2
  agents[1].pos.x = 6.765475479 (0x00000006c3f63374)
  agents[1].pos.y = -2.8720977975 (0xfffffffd20be32e1)
  agents[2].pos.x = 20.3524284617 (0x000000145a38c06d)
  agents[2].pos.y = 8.7124642332 (0x00000008b6640e55)
5 field(s) changed across tick 1233 -> 1234 (suspects):
  tick
      before: 1233
      after : 1234
  agents[1].pos.x
      before: 6.4553729629 (0x000000067493528f)
      after : 6.765475479 (0x00000006c3f63374)
  agents[1].pos.y
      before: -2.696634121 (0xfffffffd4da962e1)
      after : -2.8720977975 (0xfffffffd20be32e1)
  agents[2].pos.x
      before: 19.9427038648 (0x00000013f1550a5d)
      after : 20.3524284617 (0x000000145a38c06d)
  agents[2].pos.y
      before: 9.209923477 (0x0000000935bd8b84)
      after : 8.7124642332 (0x00000008b6640e55)
the recorded side supplied hashes only; the diff above is the local instance's change across the divergent tick
```

Exit 1. Fifteen re-runs, not 5000: a desync never heals, so the mismatch is monotone in
tick and the log can be binary-searched. Fixed-point values print as decimal *and* raw bits
because the bits are what the hash covers. The recorded side contributed hashes only — no
state crosses the machine boundary — so the diff is the local instance's own change across
the divergent tick, i.e. the list of fields that moved during the tick that first
disagreed. If instead the final hashes agree and only some middle tick differs, the desync
assumption is wrong (that is an edited or corrupt log), and `bisect` says so: it falls back
to a linear scan and reports `found by linear scan (transient mismatch: final hash
matches)`.

Clean up: `rm replay.json replay.hashes.json other.json other.hashes.json
spliced.hashes.json` — none of these are gitignored.

### Desync canary

Two `Sim` instances from identical inputs, stepped in lockstep, hashes compared every tick.
This is acceptance criterion 1 and what CI runs on all three platforms:

```
$ cargo run -p blindside-harness --release --quiet -- canary --ticks 10000
canary: seed 3735928559, 10000 ticks, two instances in lockstep
OK: 10000 ticks, hashes identical every tick
final hash: b40a42e73ef385bab5d204300e96d2c9c02a5398ac35ffeb83edf1a467c21326
```

Exit 0. The default seed is `0xDEADBEEF` (3735928559); `--seed` changes it.

A canary nobody has seen fail is not evidence of anything, so `--inject` deliberately
perturbs instance B on one tick using an ordering read out of a `std::collections::HashMap`
— the rule-2 violation from `docs/DETERMINISM.md`, the classic desync. The acceptance
criterion is that the reported tick equals the injection tick. Default injection tick is
`ticks / 2`; `--inject-tick` sets it.

```
$ cargo run -p blindside-harness --release --quiet -- canary --ticks 10000 --inject
canary: seed 3735928559, 10000 ticks, two instances in lockstep
injected at tick 5000: perturbed instance B with HashMap iteration order [1, 2] (2 agent(s) touched)
DESYNC at tick 5000
  hash A: 85f768a766d2129644d709ac5794a9d4d309b5443907f2464d59241d7acadb44
  hash B: b955c209c8f274f14ba3d7b9afaa014b96a9bf61091ee1e301da1d71cd8a6b1f
  2 differing field(s):
  agents[1].pos.x
      A: 13.5116733697 (0x0000000d82fd06a5)
      B: 14.5116733697 (0x0000000e82fd06a5)
  agents[2].pos.x
      A: 48.2984460506 (0x000000304c66f5db)
      B: 50.2984460506 (0x000000324c66f5db)
divergence written to divergence.json
reproduce with: harness bisect --from-divergence divergence.json
```

The order on the `injected` line is whatever this process's `HashMap` happened to
produce, so about half of all runs print `[2, 1]` instead (twelve runs here: five `[1, 2]`,
seven `[2, 1]`), and with `[2, 1]` hash B is
`f0ac0288249fbb3eebd676bf75637d21173ad65edb504101c2af4c65fea6067b` and B's values are
`15.5116733697 (0x0000000f82fd06a5)` and `49.2984460506 (0x000000314c66f5db)` — hash A,
`DESYNC at tick 5000` and the exit code do not change, because the order *is* the
non-determinism and instance A never sees it.

Exit 1, and the divergence tick equals the injection tick. The report is also written to
`divergence.json` (`--divergence` changes the path), carrying the seed, tick, both hashes,
the field diff, and the exact ordering that was injected — the ordering is what makes the
failure re-runnable, since a `HashMap`'s iteration order is not the same twice.

That file is the second input `bisect` accepts, and this is criterion 4, one command:

```
$ cargo run -p blindside-harness --release --quiet -- bisect --from-divergence divergence.json
bisect: reproducing divergence.json (seed 3735928559, 10000 ticks, divergence at tick 5000)
  recorded injection at tick 5000 with order [1, 2]
recorded divergence:
DESYNC at tick 5000
  hash A: 85f768a766d2129644d709ac5794a9d4d309b5443907f2464d59241d7acadb44
  hash B: b955c209c8f274f14ba3d7b9afaa014b96a9bf61091ee1e301da1d71cd8a6b1f
  2 differing field(s):
  agents[1].pos.x
      A: 13.5116733697 (0x0000000d82fd06a5)
      B: 14.5116733697 (0x0000000e82fd06a5)
  agents[2].pos.x
      A: 48.2984460506 (0x000000304c66f5db)
      B: 50.2984460506 (0x000000324c66f5db)
fresh local instance at tick 5000: hash 85f768a766d2129644d709ac5794a9d4d309b5443907f2464d59241d7acadb44  (matches A: true, matches B: false)
re-run with the recorded injection:
DESYNC at tick 5000
  hash A: 85f768a766d2129644d709ac5794a9d4d309b5443907f2464d59241d7acadb44
  hash B: b955c209c8f274f14ba3d7b9afaa014b96a9bf61091ee1e301da1d71cd8a6b1f
  2 differing field(s):
  agents[1].pos.x
      A: 13.5116733697 (0x0000000d82fd06a5)
      B: 14.5116733697 (0x0000000e82fd06a5)
  agents[2].pos.x
      A: 48.2984460506 (0x000000304c66f5db)
      B: 50.2984460506 (0x000000324c66f5db)
  diff identical to the recorded one
REPRODUCED: divergence at tick 5000
```

If your canary run printed `[2, 1]`, this block reads `with order [2, 1]`, every `hash B`
is `f0ac0288…`, the B values are the `[2, 1]` ones, and the last line is still
`REPRODUCED` — the file carries the order, so the re-run does not consult a `HashMap`
again.

Exit 1 means reproduced — the failure is still there, which is what you want to see before
you start fixing it. Exit 0 here means `NOT REPRODUCED`: the recorded injection no longer
diverges, so either it is fixed or it was never deterministic in the first place. A
divergence file with no recorded injection (a real desync between two instances, not an
injected one) cannot be re-run, so the recorded diff stands as reported and the local
instance is only checked against both sides' hashes.

### Batch throughput

`docs/PHASE-0-HARNESS.md` asks for thousands of matches per hour on a laptop. `batch` runs
N matches of T ticks sequentially on one thread — deliberately single-threaded, so the
number is per core:

```
$ cargo run -p blindside-harness --release --quiet -- batch --matches 200 --ticks 5000
batch: 200 matches x 5000 ticks, seeds 3735928559..=3735928758
elapsed: 0.017s
matches/hour: 41271625
ticks/s: 57321701
digest: 4f8e25ee2dfb94d0d6f597d2ac7c188bb491ac3d623d07b2e2b737c0f4f04bc7
```

Exit 0 always: `batch` measures, it does not compare. Match *i* uses seed + *i*, and the
digest is the XOR of every final hash — order-independent, enough to tell two batch runs
apart, and enough to stop the optimiser deleting the work. The rate is meaningless as a
prediction of Phase 3 throughput (two agents, no sensors, no policies); it is a floor and a
regression tripwire.

### Determinism lint

```
cargo run -p determinism-lint -- --check-all            # what CI runs
cargo run -p determinism-lint -- [--root DIR] [--check-all] [-q] [CRATE_DIR ...]
cargo run -p determinism-lint -- --help
```

```
$ cargo run -p determinism-lint --quiet -- --check-all
determinism-lint: OK -- 3 crate(s) clean (sources + layout + Cargo.toml dependencies): <workspace>\crates/blindside-sim, <workspace>\crates/blindside-vm, <workspace>\crates/blindside-gen
determinism-lint: token-level check; not seen: macro expansion, dependency contents, most pointer casts, indirect `{:p}`, `use std as sys` / glob roots, a hostile manifest, rules 6-8 (`--help` has the list).
```

Exit 0. (The real output prints the workspace root absolute; only that is replaced with
`<workspace>` here. The mixed separators are what a Windows run prints — the root comes
from the OS with backslashes, the crate path is joined with `/`. Without `--check-all` the
first line says `(sources + layout)`.) The
second line is printed on every run, pass or fail, because a clean exit means "none of the
tokens below was written in these files", which is narrower than "this code is
deterministic".

**What it checks.** The *spellings* of `docs/DETERMINISM.md` rules 1-5 — the tokens those
constructs are written with — in `crates/blindside-sim`, `crates/blindside-vm` and
`crates/blindside-gen` (`tools/determinism-lint`); the crate layout, on every run; and the
dependency list, with `--check-all`. Every `src/**/*.rs` is lexed with `proc-macro2` (the
front end `syn` is built on) and scanned at the token level. Comments and doc comments are
ignored; string literals are opaque except for a pointer format spec, so
`"f64 HashMap std::time rand"` in a string is not a finding and `"{:p}"` is. Braced use
trees (`use std::{thread, time}`) and raw identifiers (`r#f64` is `f64`) are matched. Each
finding prints ``file:line:column: `token` -- <label>: <why>``, then the summary line and
the second line above. Exit code 0 clean, 1 findings, 2 usage/IO error.

**What it cannot check**, from `--help` (`WHAT THIS CANNOT SEE`). It lexes; it does not
expand, resolve or type-check.

- *Macro-expanded tokens.* A proc macro can synthesise `f64` after the lint has run.
  `include!`, `env!` and build scripts are rejected, so the cheap ways in are shut; the
  rest needs a dependency, and those are allow-listed.
- *Dependency types, and only dependency names.* `blindside_content::Table` may alias
  `HashMap`; blindside-content is an allowed dependency of all three crates and is not
  itself linted. What `fixed` resolves to is settled by `Cargo.lock` and any `[patch]`
  table, neither of which is read.
- *What a cast operates on.* `x as usize` is a pointer cast only if `x` is a pointer, and
  the type is not in the token stream. Rejecting every integer cast would cry wolf, so
  the *common* ways of getting a raw address are rejected instead: `*const`/`*mut`,
  `as_ptr`, `addr_of`, `transmute`, `NonNull`. Others compile and pass — a fn item
  `as usize`, `&raw const`, `as_ptr_range()`, `alloc(..) as usize`, `transmute_copy`. An
  address-derived value is a review item, not a lint item.
- *`{:p}` spelled indirectly.* The pointer format spec is caught only when it is spelled
  `{:p}` inside one literal. Pieces joined by `concat!`, or a string escape such as
  `{:\x70}`, are not seen.
- *A hostile manifest.* `Cargo.toml` is read by a small hand-written reader. A `\"` escape
  inside an earlier string, or a UTF-8 BOM before the first header, blinds it to
  everything after — a `[lib]` path, a build script, a `package = ".."` rename. This lint
  guards against an honest author's accidents; a hostile author is what code review is
  for.
- *An allowed name at another source.* `blindside-content = { path = "../elsewhere" }`
  names an allowed dependency; what lives at that path is not read.
- *A renamed or glob root.* `use std as sys; sys::thread::spawn(..)`, `use std::*;
  thread::spawn(..)`, `use std::fmt::*; Pointer::fmt(..)`. Every path check matches the
  spelled `<root>::<name>`; catching these means banning root renames and glob imports,
  a rule `DETERMINISM.md` does not state.
- *Rules 6-8.* Iteration by stable ID, IDs not derived from name hashes, justified
  `unsafe`. `BTreeMap<NameHash, _>` reads perfectly and is still non-deterministic. The
  desync canary catches those; this lint cannot.

Rejected, with the label each finding prints:

| Label | Rejected |
|---|---|
| `rule 1` | idents `f32`, `f64`; any float literal (`0.0`, `1e3`, `2.5f32`), including as a range bound (`..0.5`, `0..0.5`). Tuple indexes (`t.0.1`, `t.0 .1`) are not literals and pass |
| `rule 2` | idents `HashMap`, `HashSet` |
| `rule 2/3` | std's hashers, which reach non-determinism without naming a `HashMap` (`RandomState` is OS-seeded per process, `DefaultHasher` is unstable across std versions): idents `DefaultHasher`, `RandomState`, `SipHasher`, `SipHasher13`; paths `collections::hash_map`, `collections::hash_set` |
| `rule 3` (wall clock) | idents `SystemTime`, `Instant`; paths `std::time`, `core::time` |
| `rule 3` (address) | `*const`, `*mut`; paths `std::ptr`, `core::ptr`, `fmt::Pointer`; idents `as_ptr`, `as_mut_ptr`, `addr_of`, `addr_of_mut`, `into_raw`, `transmute`, `NonNull`; a `{:p}` / `{:#p}` format spec (any fill, width or argument name; `{{:p}}` is an escaped brace and passes) in a string literal that is not a doc comment |
| `rule 3` (environment) | paths `std::process`, `std::env`; macros `env!`, `option_env!` (a variable named `env` is fine) |
| `rule 4` | ident `rand`; any ident beginning `rand_` |
| `rule 5` | ident `rayon`; paths `std::thread`, `core::thread` |
| `lint scope` | source the `src/` walk would not read: `include!`; `#[path = ".."]`, bare or inside `cfg_attr`, that leaves `src/` or does not name a `.rs` file (the walk reads only `*.rs`); in `Cargo.toml`, a `path` under `[lib]` or `[[bin]]` (the root is `src/lib.rs`; see *a hostile manifest* above for what the reader misses) and a build script (`build.rs`, or `[package] build = ".."` other than `false`, since it runs unlinted before the crate compiles); no `src/lib.rs` at all |
| `dependency tree` | `--check-all` only: a `[dependencies]` / `[build-dependencies]` entry whose *package* is outside the allow-list `blindside-vm`, `blindside-content`, `fixed`, `blake3`. A `package = ".."` rename is checked by the package name in both the inline-table and `[dependencies.<key>]` spellings, and `workspace = true` is resolved through the nearest ancestor `Cargo.toml` with a `[workspace]` table; a `workspace = true` key that workspace does not declare is also a finding. `[dev-dependencies]` only warn, and so does `workspace = true` with no workspace above at all (Cargo could not build that crate either) |

The `lint scope` rows run without `--check-all` too, so a `CRATE_DIR` with no `Cargo.toml`
or no `src/lib.rs` is a finding, not a silently short scan.

Positional `CRATE_DIR`s override the default three; CI uses this to lint a copy of
`blindside-sim` with `pub fn bad() -> f64 { 0.0 }` appended and assert the lint fails
(acceptance criterion 5). Run here, with the copy in a temp directory whose path is
abbreviated to `<tmp>`:

```
$ cargo run -p determinism-lint --quiet -- --check-all <tmp>/blindside-sim
<tmp>/blindside-sim\Cargo.toml:14:1: warning: `fixed` is `workspace = true` but no ancestor Cargo.toml has a [workspace] table, so the package it names cannot be checked here
<tmp>/blindside-sim\Cargo.toml:15:1: warning: `blake3` is `workspace = true` but no ancestor Cargo.toml has a [workspace] table, so the package it names cannot be checked here
<tmp>/blindside-sim\src\lib.rs:216:17: `f64` -- rule 1: no f32/f64, fixed-point (Fx) only
<tmp>/blindside-sim\src\lib.rs:216:23: `0.0` -- rule 1: no f32/f64, fixed-point (Fx) only
determinism-lint: FAIL -- 2 finding(s) in 1 file(s) across 1 of 1 crate(s) (sources + layout + Cargo.toml dependencies)
determinism-lint: token-level check; not seen: macro expansion, dependency contents, most pointer casts, indirect `{:p}`, `use std as sys` / glob roots, a hostile manifest, rules 6-8 (`--help` has the list).
```

Exit 1. Two findings — the type and the literal, on the appended line 216 — and two
warnings: the copy sits outside the workspace, so the `fixed = { workspace = true }` and
`blake3 = { workspace = true }` entries on lines 14 and 15 of `blindside-sim/Cargo.toml`
cannot be resolved there. Warnings do not affect the exit code; the CI job asserts exit 1
and the `f64` line only.

Tests: `cargo test -p determinism-lint` runs 16 unit tests and 25 integration tests.

- The unit tests drive the scanner and the manifest reader in-process: comments and
  strings ignored, float positions, tuple indexes against range ends, std paths only when
  rooted, `rand_*` and `rayon`, braced use trees, raw identifiers, `{:p}` read out of
  string literals, `#[path]` through `cfg_attr` and by extension, string-literal forms
  decoded or refused, path escapes with both separators; every TOML spelling the reader
  knows, `package = ".."` renames in each of them, `workspace = true` inheritance, and
  the inline-table helpers.
- The integration tests run the built binary. The real workspace with `--check-all` is
  clean with no warnings. A copy of `blindside-sim` with the `f64` line appended fails
  with exactly the two findings and the two warnings above (criterion 5 in miniature).
  Temp crates carrying one violation each — an `f64` field, a `HashMap`,
  `std::time::Instant`, `rand`, a disallowed dependency — fail naming the line. One test
  per closed evasion asserts exit 1 and the exact finding line: braced use tree, std
  hashers, pointer ingredients, `{:p}` and `fmt::Pointer`, process/env reads, `r#f64`, a
  float as a range bound, `#[path]` and `include!` leaving `src/`, `#[path]` inside
  `cfg_attr`, `#[path]` to a non-`.rs` file, `[lib]`/`[[bin]] path`, `build.rs` and
  `package.build`, `package = ".."` renames in four spellings, `workspace = true`
  resolution (declared, undeclared, and no workspace at all). A crate of near-miss idioms
  — `BTreeMap`, `blake3::Hasher`, `Hash`/`Hasher` bounds, a struct named `Pointer`,
  `t.0 .1`, `0..10`, `..=5`, a parameter named `env`, an in-`src/` `#[path]`, banned words
  and `{{:p}}` in strings, `build = false`, every allowed-dependency spelling — passes with
  no warnings. `--help` and the summary line must name every gap listed above. A missing
  `CRATE_DIR` exits 2.

## CI

`.github/workflows/determinism.yml`, on every push and pull request:

| Job | Runs on | What |
|---|---|---|
| `build-test-lint` | ubuntu, macos, windows | `cargo build --workspace --locked`, `cargo test --workspace --locked`, `cargo run -p determinism-lint --locked -- --check-all`, `cargo run -p blindside-harness --release --locked -- canary --ticks 10000`, `cargo run -p blindside-harness --release --locked -- record --seed 7 --ticks 5000 --out replay.json --hashes hashes.json`; uploads `hashes.json` + `replay.json` as artifact `hashes-<os>` |
| `cross-platform` | ubuntu | downloads the three `hashes-*` artifacts and fails unless the three `hashes.json` are byte-identical (`cmp`), printing the first differing lines |
| `lint-rejects-f64` | ubuntu | `cargo build -p determinism-lint --locked`; copies `crates/blindside-sim` to a temp dir, appends `pub fn bad() -> f64 { 0.0 }`, runs `cargo run -p determinism-lint --locked -- --check-all <copy>` and fails unless it exits 1 naming the `f64` line (the copy's two `workspace = true` warnings, shown above, are expected); then `cargo run -p determinism-lint --locked -- --check-all` on the unmodified crates as a sanity check |

`cross-platform` is acceptance criterion 3, `lint-rejects-f64` is criterion 5, and the
canary step is criterion 1. Every `cargo` step passes `--locked` (the committed
`Cargo.lock` is authoritative); the two harness steps also use `--release`. The CI record
step is the same command as the worked example above with `--hashes hashes.json` added,
which is why the artifact is named `hashes.json` and not `replay.hashes.json`; run here it
prints `hashes: hashes.json  (5001 entries, ticks 0..=5000)` and the same content and
final hashes as the worked example.
