# Phase 0 harness: build, test, run

Rust workspace for the BLINDSIDE determinism harness (`docs/PHASE-0-HARNESS.md`). The sim
it exercises is deliberately almost empty — two agents whose fixed-point positions random
walk from a stateless RNG — because the tooling, not the sim, is the deliverable. That is
enough for the state hash to change every tick and for an injected non-determinism to have
somewhere to hide.

## Layout

```
Cargo.toml                    workspace root; pins fixed and blake3 `=x.y.z`; release
                              profile sets overflow-checks AND debug-assertions
rust-toolchain.toml           pins the exact stable (1.98.1)
.gitattributes                eol=lf for *.rs *.toml *.md *.yml *.json *.sh Cargo.lock
                              content/** fixtures/** ci/**
.gitignore                    target/, plus the harness output the CI steps write into the
                              repository root (hash logs, dumps, batch tables, replay.json)
                              so re-running them locally cannot be committed by accident;
                              anchored to the root, so fixtures/ stays tracked
docs/HARNESS.md               the reference: the BLD-20 question round, CLI, bisect
                              semantics, state-hash coverage, golden-hash procedure, lint
                              evasions, dependency audit, the parallel window
docs/PHASE-0-READINESS.md     the five acceptance criteria with the command and output for
                              each, every guess made, and days spent (BLD-40)
.github/PULL_REQUEST_TEMPLATE.md  the five determinism rules no lint can check (BLD-34)
ci/no-tooling-features.txt    crates whose resolved features must not include the sim's
                              `diagnostics` or `inject-desync` gates (BLD-29)
ci/fixtures/unsafe-*          pass and fail halves of the rule-8 SAFETY-comment check;
                              read by the lint, never compiled
crates/blindside-sim          deterministic core (constrained, see docs/DETERMINISM.md)
crates/blindside-vm           bytecode VM (constrained) - stub
crates/blindside-content      content definitions (held to the same rules); content pack hash
crates/blindside-gen          world generation (constrained) - stub
crates/blindside-harness      headless runner, canary, record/verify, bisect, batch,
                              diff-dumps, golden (unconstrained; builds `harness`)
tools/determinism-lint        CI lint for the constrained crates
tools/assert-empty-sim.sh     the parallel-window assertion: the sim is still empty
content/                      the content pack; absent in Phase 0 = the empty pack
fixtures/phase0-empty-10k.record   the checked-in replay: seed 0xDEADBEEF, 10,000 ticks
```

Ground truth (`World`) is `pub(crate)`. The one window onto it is
`blindside_sim::diagnostics::{diff, dump}` -- strings only, compiled only under the sim's
`diagnostics` feature, which `blindside-harness` enables for the canary's field-level diffs
and bisect's state dumps. `crates/blindside-harness/tests/world_unreachable.rs` proves at
compile time (trybuild) that `World` cannot be named or reached through that API. The
canary's `--injected` needs a second feature, `inject-desync`: with it the sim carries the
BLD-35 fixture (`Sim::set_inject_tick`; on the armed tick every instance folds a fresh
`HashMap`'s iteration order into a hashed field); without it `--injected` exits 2. The
harness's own tests enable it through a dev-dependency, so `cargo test` exercises the real
thing while `cargo build -p blindside-harness` does not carry it. Neither feature is a
default, and neither is a privacy boundary: Cargo unifies features per build, so
hash-producing binaries are built with `-p <crate>` and CI's `feature-gates` job asserts
the resolved feature sets are clean (BLD-29; `docs/HARNESS.md` section 7).

## Build

```
cargo build --workspace
cargo build --workspace --release      # for throughput numbers
```

## Test

```
cargo test --workspace
```

`blindside-sim` (31 tests) checks that two sims with the same seed hash identically for
1000 ticks, that the hash changes every tick, that different seeds differ, and that the
diagnostics dump and the hash move together (they cover the same fields). Per hashed field
of `World` a mutation test proves the hash sees it; the deliberately excluded cache field
(`moved_last_step`) proves the hash ignores it; the same agents inserted in two orders hash
once. Golden hashes for the empty sim on seed `0xDEADBEEF` at ticks 0, 1, 1000 and 10,000
are pinned; the tick-1000 one is the cross-platform anchor CI's `cross-platform` job checks
the other way round. `DeterministicRng::draw` is repeatable, in `[0, 1)`, and 1,000 draws in
an order shuffled by `blindside_sim::testing::permutation` (itself built on `draw`, so no
rand-family crate anywhere) equal the sorted-order draws; the mean of 10,000 draws is within
0.02 of 0.5, accumulated in `Fx`. `golden_tables.rs` (generated by `harness golden`, 40 RNG
rows and 48 `Fx` arithmetic rows as raw bits) is asserted row by row. `Fx::MAX * 2` panics
under both `cargo test` and `cargo test --release`. The record types validate: schema 0
migrates as identity, an unknown schema and an unsorted command log are typed errors. With
`inject-desync` on (as `cargo test --workspace` builds it) two armed instances agree until
the injection tick and disagree from it, 20 rounds; with it off `set_inject_tick` reports
the fixture absent.

`blindside-content` (6 tests): the empty pack's hash is the documented constant; adding a
one-byte file to a temp pack changes it; entry order does not; path, bytes, boundaries and
count all do; nested directories hash with `/` paths and dotfiles are skipped.

`blindside-harness` checks the round trips the CLI is made of (24 CLI tests, 31 unit, 3 in
the binary): record then verify is clean, a record from another content pack or a newer
schema is rejected with both hashes and exit 2, `--hash-every N` keeps ticks `0, N, 2N, ...`
plus the final tick, 10,000 `step()` calls take under 10 ms, an injected divergence is
caught in the tick it was armed for (and names `inject_fold`), 20 injection runs fire every
time, a log corrupted from tick 1234 onward is bisected to tick 1234 in at most 16 re-runs,
a foreign checkpoint log every 100 ticks is narrowed and then walked to the exact tick, the
batch table is byte-identical for J=1 and J=8, a `--content` directory that is named but
absent is exit 2 while the absent built-in default is not, and `golden` prints the
checked-in tables (compared with whitespace collapsed, since rustfmt splits the long rows:
116 generated lines against 476 checked in). `tests/fixture.rs` loads
`fixtures/phase0-empty-10k.record` through `migrate()`, checks its 281-byte size and LF
endings, re-serialises it byte-identically and re-runs it to its final hash.
`tests/workspace.rs` reads `cargo metadata`: blindside-sim depends on no workspace crate but
vm and content, every external dependency of sim/vm/content/gen is pinned `=x.y.z`, no
rand-family crate (or rayon, libm) is reachable from them even through dev-dependencies,
the sim's default feature set is empty, the harness has no GUI, renderer or audio
dependency and a closed direct-dependency list, and the constrained crate roots carry
`#![deny(unsafe_code)]`. It also runs `cargo tree -e features` for every crate in
`ci/no-tooling-features.txt` and fails if `diagnostics` or `inject-desync` is in the
resolved set (BLD-29), which is the same check CI's `feature-gates` job runs.
`tests/world_unreachable.rs` is the trybuild compile-fail suite.

`determinism-lint`'s tests are listed under "Determinism lint" below.

## Tools

> **`docs/HARNESS.md` is the reference.** It carries the annotated version of everything
> below plus what this section does not repeat: bisect's semantics (§5), what the state
> hash covers (§4), the golden-hash update procedure (§8), the lint's evasion table (§9),
> the dependency audit (§10), and the decisions the build took with no designer answer,
> written as a yes/no question round (§1). This section is the short version, and every
> transcript in it was produced by running the command.

Two things trip people up before anything else:

- **The package is `blindside-harness`; only the binary is `harness`.** `cargo run -p
  harness` fails, with ``error: package(s) `harness` not found in workspace``. Use
  `cargo run -p blindside-harness -- <subcommand>`, or run the built binary directly at
  `target/release/harness` (`harness.exe` on Windows, which is what the usage lines below
  say because they were pasted from a Windows run).
- **The hash log is named after the record.** `verify` and `canary` write one by default,
  at `<record stem>.hashlog` in the current directory; `run` and `record` write one only
  when `--hash-log <PATH>` asks. `--hash-every N` thins it to ticks `0, N, 2N, …` plus the
  final tick, so the last line is always the final hash. `batch` writes no log: its output
  is the `seed,final_hash` table.

Subcommands, from `harness --help`. The top-level help prints only the one-line summary of
each; the Usage column is each subcommand's own `--help` line, verbatim:

| Subcommand | Usage | What it does |
|---|---|---|
| `run` | `harness.exe run [OPTIONS] <RECORD>` | re-runs a `MatchRecord` to its tick count, compares the final hash against the recorded one, prints final tick, wall-clock, ticks/s, matches/hour at 9,600 ticks/match and the per-tick hash cost; `--dump-state-at <TICK>` writes `diagnostics::dump` there |
| `record` | `harness.exe record [OPTIONS] --seed <SEED> --ticks <TICKS> --out <OUT>` | runs a fresh empty match and writes the replay with `final_hash` filled in |
| `verify` | `harness.exe verify [OPTIONS] <RECORD>` | re-runs a record, compares the final hash to the recorded one (exit 1 with both hashes on a mismatch), refuses a record from another content pack (exit 2, both hashes) |
| `canary` | `harness.exe canary [OPTIONS] --record <RECORD>` | two sims built from that one record through `Sim::new`, stepped in lockstep, hashes compared every tick; `--injected` arms the `HashMap`-ordering desync in both instances (needs a build with `--features inject-desync`, else exit 2), `--inject-tick` picks the tick (default 5000), `--divergence` names the report file |
| `bisect` | `harness.exe bisect [OPTIONS] <--hash-log <PATH>\|--injected\|--from-divergence <PATH>>` | finds the first tick a local re-run disagrees with the foreign side on and dumps the local state there; the foreign side is a plain hash log recorded elsewhere, the BLD-35 fixture, or a `divergence.json` from `canary` |
| `diff-dumps` | `harness.exe diff-dumps <A> <B>` | field-level diff of two state dumps from two machines; exit 1 if they differ |
| `batch` | `harness.exe batch [OPTIONS] --seeds <A..B> --out <OUT>` | one empty match per seed, at most `--jobs J` at once, writes a `seed,final_hash` table sorted by seed (byte-identical for any J) and reports matches/hour and aggregate ticks/s |
| `golden` | `harness.exe golden` | prints `crates/blindside-sim/src/golden_tables.rs` (RNG draws and `Fx` arithmetic as raw bits) to stdout; redirect over the checked-in file, then `cargo fmt --all` |

Global flag: `--content <DIR>`, the content pack a record is validated against. The default
is `<workspace>/content`, and it is allowed to be missing — Phase 0 ships no `content/` and
the empty pack *is* the pack. A directory you name yourself must exist:

```
$ harness.exe run fixtures/phase0-empty-10k.record --content ./no-such-pack
harness: error: --content ./no-such-pack: no such directory. (The built-in default may be
absent -- that is the empty pack -- but a directory named on the command line must exist.)
[exit 2]
```

Exit codes are the same everywhere and are what CI and `git bisect run` key off:

| Code | Meaning |
|---|---|
| 0 | ran, and everything that was compared agreed |
| 1 | a determinism failure: canary divergence, hash mismatch, located or reproduced desync, two dumps that differ |
| 2 | could not run: bad arguments, unreadable file, or a file that does not belong (wrong schema, wrong content hash, `--injected` without the `inject-desync` feature) |

Exit 2 is not a determinism result: nothing was compared.

### The hash log

Plain text, one `tick,hash` line per logged tick, LF, no header — so `diff`, `cmp` and
`sha256sum` compare two machines' logs without this binary, which is how CI's
`cross-platform` job works:

```
$ head -3 hashes.hashlog
0,e299d9f373c4ff513633802b5ce9a28237fa0989f068467b704014d42031d12b
1,664104ee0d3ea2b949a36d65e7dde6fc5c3af2f2d4debeba6103a38283cabd3a
2,d8fa48b8307f511973e2f2fa7758c8bf9daa5d6d32d031b32c74500a9178ac8d
$ tail -1 hashes.hashlog
5000,d61455307886d124f1b6913f95bc70fde56633488e23a80163fb9303500a5b1a
```

Carrying no seed and no tick count is the price of a format `diff` understands: a log from
*another* record is reported as a divergence at tick 0, not as a usage error, because
nothing structural distinguishes the two.

### Worked examples

One run of the release build, in a scratch directory. `<repo>` replaces the absolute path
the binary prints; nothing else is edited.

**Record a replay, then verify it.** `record` runs a fresh empty match and writes the
record with `final_hash` filled in; `verify` re-runs it and compares.

```
$ harness.exe record --seed 7 --ticks 5000 --out replay.json --hash-log hashes.hashlog
recorded seed 7, 5000 ticks
record: replay.json
content hash: 3dbd5a09e7a3cb05765522ff5d618722f3ab7784973a3e7c3b8a43c095404ba1
final hash: d61455307886d124f1b6913f95bc70fde56633488e23a80163fb9303500a5b1a
hash log: hashes.hashlog  (5001 line(s), 5001 entries, every tick to 5000)
[exit 0]

$ harness.exe verify replay.json
verify: replay.json  (seed 7, 5000 ticks)
final hash: d61455307886d124f1b6913f95bc70fde56633488e23a80163fb9303500a5b1a
recorded  : d61455307886d124f1b6913f95bc70fde56633488e23a80163fb9303500a5b1a
wall-clock: 0.001s
hash log: replay.hashlog  (5001 line(s), 5001 entries, every tick to 5000)
OK: final hash matches record
[exit 0]
```

**Run the checked-in fixture and dump a state.** The dump is the only form in which ground
truth crosses a machine boundary: strings, produced inside the sim behind the `diagnostics`
feature. Fixed-point values print as decimal *and* raw bits, because the bits are what the
hash covers.

```
$ harness.exe run fixtures/phase0-empty-10k.record --dump-state-at 5000
record: <repo>/fixtures/phase0-empty-10k.record  (seed 3735928559, 10000 ticks)
final tick: 10000
final hash: 653b9057c4dd809407213920a217794adafd41c7ea92976e6bf344b76a5639bc
recorded  : 653b9057c4dd809407213920a217794adafd41c7ea92976e6bf344b76a5639bc
wall-clock: 0.003s  (step-only pass 0.000s, hashing pass 0.002s)
ticks/s: 66622252  => 24983344 matches/hour at 9600 ticks/match
hash cost per tick: 227 ns  (10001 hashes, every tick; 0.002s of the hashing pass)
state at tick 5000 written to phase0-empty-10k.tick5000.dump:
  seed = 3735928559
  tick = 5000
  inject_fold = 0x0000000000000000
  agents.len = 2
  agents[1].pos.x = 13.5116733697 (0x0000000d82fd06a5)
  agents[1].pos.y = -19.1461968874 (0xffffffecda92d73e)
  agents[2].pos.x = 48.2984460506 (0x000000304c66f5db)
  agents[2].pos.y = -23.487017158 (0xffffffe88352d7f2)
OK: final hash matches record
[exit 0]
```

Timings are not reproducible and should not be quoted as measurements; the hashes are, and
are the point. (`hash cost per tick` in particular is stable only when hashing every tick —
227–249 ns across runs. At a sparse `--hash-every` it has ranged from 1.1 µs to 6.3 µs on
the same machine, because it is then dividing a handful of hashes by a whole run's noise.)

**The desync canary, unarmed.** Acceptance criterion 1: two `Sim`s built from one record
through `Sim::new`, stepped in lockstep, compared after every step.

```
$ harness.exe canary --record fixtures/phase0-empty-10k.record
canary: <repo>/fixtures/phase0-empty-10k.record  (seed 3735928559, 10000 ticks), two
instances in lockstep
OK: 10000 ticks, hashes identical every tick
final hash: 653b9057c4dd809407213920a217794adafd41c7ea92976e6bf344b76a5639bc
wall-clock: 0.005s
hash log: phase0-empty-10k.hashlog  (10001 line(s), 10001 entries, every tick to 10000)
[exit 0]
```

**The desync canary, armed.** `--injected` needs a build carrying the sim's `inject-desync`
feature. Without it the run refuses rather than passing quietly:

```
$ harness.exe canary --record fixtures/phase0-empty-10k.record --injected
canary: <repo>/fixtures/phase0-empty-10k.record  (seed 3735928559, 10000 ticks), two
instances in lockstep
harness: error: --injected: this build of blindside-sim has no inject-desync fixture
(build with --features inject-desync)
[exit 2]
```

With it (`cargo run -p blindside-harness --release --features inject-desync -- …`), both
instances fold a fresh `HashMap`'s iteration order into a hashed field on tick 5000, and
the canary catches it in that tick — acceptance criterion 2:

```
injected at tick 5000: both instances folded a fresh HashMap's iteration order into
World.inject_fold
DESYNC at tick 5000
  hash A: af4820cb4e377063c6fbd6559da32048e65c4bfaba8252b1ae2c6a0e30f8223b
  hash B: 7324d1284ecbd7ebd005b0555ba7809c7992da477f74b0366d0ade342f675bda
  1 differing field(s):
  inject_fold
      A: 0x8c8741fd167d45e7
      B: 0x2c4a81760dbcd6f1
divergence written to divergence.json
reproduce with: harness bisect --from-divergence divergence.json
[exit 1]
```

> **Two runs of the armed canary print different numbers, and that is the fixture
> working.** A `HashMap`'s iteration order comes from a `RandomState` seeded per process,
> so both hashes and both `inject_fold` values change every run. Three consecutive runs
> here gave folds `0x8c8741fd167d45e7 / 0x2c4a81760dbcd6f1`,
> `0x306ab3437a155adb / 0x13e2b155046eb28f` and
> `0xc820ccaf873dd709 / 0xd1394de1639768b9`. Reproducible is what CI asserts: the exit
> code, the tick, and the field named in the diff. Never pin an armed canary's hashes and
> never compare two machines' armed runs.

**Bisect against a foreign hash log.** The case bisect exists for: a log recorded on
another machine, another OS or another commit. Here `hashes.hashlog` was copied and
corrupted from tick 3000 onward.

```
$ harness.exe bisect --record replay.json --hash-log foreign.hashlog
bisect: replay.json  (seed 7, 5000 ticks), local re-run vs foreign.hashlog  (5001 entries,
every tick to 5000)
DIVERGENCE at tick 3000  (found by binary search over 5001 checkpoint(s), 14 re-run(s))
  recorded: f4b0d389a224410848d1471998543975a60ebf9ae33505a2cb840761a836d144
  local   : c4b0d389a224410848d1471998543975a60ebf9ae33505a2cb840761a836d144
  tick 2999 matched on both sides
local state at tick 3000 (hash c4b0d389…a836d144):
  seed = 7
  tick = 3000
  … (agents[1].pos.x, agents[1].pos.y, agents[2].pos.x, agents[2].pos.y)
5 field(s) changed across tick 2999 -> 3000 (suspects):
  tick
      before: 2999
      after : 3000
  agents[1].pos.x
      before: 7.807158166 (0x00000007cea1eae6)
      after : 8.2472922162 (0x000000083f4e8aed)
  … (three more)
the recorded side supplied hashes only; the diff above is the local instance's change
across the divergent tick
dump of the local state at tick 3000 written to replay.tick3000.dump
[exit 1]
```

Fourteen re-runs for a 5,000-tick record. `--injected` (acceptance criterion 4) and
`--from-divergence` are the other two foreign sides; `docs/HARNESS.md` §5 has both, the
exit-code contract and the `git bisect run` example.

**Diff two dumps from two machines.** Needs neither machine's `Sim`: a dump is text.

```
$ harness.exe diff-dumps phase0-empty-10k.tick5000.dump copy.dump
diff-dumps: A = phase0-empty-10k.tick5000.dump  B = copy.dump
OK: identical (8 field(s))
[exit 0]
```

**Batch: one match per seed, and the same table for any `--jobs`.** Parallelism *between*
matches only, never inside a tick (DETERMINISM.md rule 5). Workers pull the next seed from
a shared counter, so the schedule depends on timing; rows are sorted by seed before the
table is written, so the table does not.

```
$ harness.exe batch --seeds 0..1000 --ticks 9600 --jobs 8 --out j8.csv
batch: 1000 seed(s) 0..=999 x 9600 ticks, 8 job(s)
elapsed: 0.036s
matches/hour: 101158831  aggregate ticks/s: 269756882
table: j8.csv  (1000 line(s), seed,final_hash sorted by seed)
[exit 0]

$ harness.exe batch --seeds 0..1000 --ticks 9600 --jobs 1 --out j1.csv
batch: 1000 seed(s) 0..=999 x 9600 ticks, 1 job(s)
elapsed: 0.136s
matches/hour: 26431543  aggregate ticks/s: 70484116
table: j1.csv  (1000 line(s), seed,final_hash sorted by seed)
[exit 0]

$ cmp j1.csv j8.csv && echo identical
identical

$ head -1 j8.csv
0,2d2a08bdd4d9fa98dfd0248800795e9ad85a63f65057f6fc98522e9c310b764f
```

BLD-38's budget for that command is 60 s; a 16-logical-core Windows laptop does it in
0.036 s at `--jobs 8` and 0.136 s at `--jobs 1`. Read that as a floor and a regression
tripwire, not a Phase 3 prediction — a Phase 0 tick moves two agents.

**Regenerate the golden tables.** 116 lines out; the checked-in file is 476, because
rustfmt splits the long rows. `golden_prints_the_checked_in_tables` compares the two with
whitespace collapsed, so it asserts the content is unchanged modulo formatting.

```
$ harness.exe golden | wc -l
116

cargo run -p blindside-harness -- golden > crates/blindside-sim/src/golden_tables.rs
cargo fmt --all
```

### The parallel window

```
$ bash tools/assert-empty-sim.sh
assert-empty-sim: the Phase 0 parallel window, at <repo>

blindside-sim
  ok    module list is the Phase 0 set
  ok    World's fields are the Phase 0 set
  ok    fxmath.rs declares no items (header only)
  ok    no Belief type is declared anywhere under crates/

no Phase 3 subject matter in blindside-sim / -gen / -content
  ok    no sensor, belief, acoustic, cave, ancient or policy declaration

the stub crates
  ok    blindside-gen declares no items (a lint target, not yet a generator)
  ok    blindside-vm declares only VmBudget (Phase 4 writes the interpreter)
  ok    blindside-content's public items are the pack hash and nothing else

assert-empty-sim: OK -- the sim is still empty; Phase 0 built only tooling.
[exit 0]
```

Phase 0 was built before the Phase 1 report existed and alongside Phase 2, so the sim had
to stay empty while the tooling around it was finished. This asserts that it did, on every
commit and again at readiness; `docs/HARNESS.md` §12 says what each check defends and why
`World` holds four fields rather than one. BLD-66 re-runs it before the first Phase 3
commit.

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
constructs are written with — the spelling half of rule 8 (a `// SAFETY:` line above
every `unsafe` and every `#[allow(unsafe_code)]`), and `ARCHITECTURE.md`'s "no I/O"
(`std::fs`, `std::io`, `std::net`), in `crates/blindside-sim`,
`crates/blindside-vm` and `crates/blindside-gen` (`tools/determinism-lint`); the crate
layout, on every run; and the dependency list, with `--check-all`. One exemption: inside an
item under `#[cfg(feature = "inject-desync")]` — that exact spelling, an outer attribute,
never a `mod` — `HashMap`, `HashSet` and the std hashers pass. That is the canary's
injection fixture (`World::inject_desync`), the one sanctioned HashMap in a constrained
crate; the exemption ends with the item and covers nothing else (a float in it is still a
finding). `blindside-content` is held to the same rules by this repo's standing orders but
is not in the lint's crate list (the BLD-20 question on scope is open). Every `src/**/*.rs` is lexed with `proc-macro2` (the
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
- *Rules 6-8.* Iteration by stable ID, IDs not derived from name hashes, and whether a
  `// SAFETY:` line is *true* (its presence is checked; its argument is not).
  `BTreeMap<NameHash, _>` reads perfectly and is still non-deterministic. The desync canary
  and review catch those; this lint cannot.

Rejected, with the label each finding prints:

| Label | Rejected |
|---|---|
| `rule 1` | idents `f32`, `f64`; any float literal (`0.0`, `1e3`, `2.5f32`), including as a range bound (`..0.5`, `0..0.5`). Tuple indexes (`t.0.1`, `t.0 .1`) are not literals and pass |
| `rule 2` | idents `HashMap`, `HashSet` |
| `rule 2/3` | std's hashers, which reach non-determinism without naming a `HashMap` (`RandomState` is OS-seeded per process, `DefaultHasher` is unstable across std versions): idents `DefaultHasher`, `RandomState`, `SipHasher`, `SipHasher13`; paths `collections::hash_map`, `collections::hash_set` |
| `rule 3` (wall clock) | idents `SystemTime`, `Instant`; paths `std::time`, `core::time` |
| `rule 3` (address) | `*const`, `*mut`; paths `std::ptr`, `core::ptr`, `fmt::Pointer`; idents `as_ptr`, `as_mut_ptr`, `addr_of`, `addr_of_mut`, `into_raw`, `transmute`, `NonNull`; a `{:p}` / `{:#p}` format spec (any fill, width or argument name; `{{:p}}` is an escaped brace and passes) in a string literal that is not a doc comment |
| `rule 3` (environment) | paths `std::process`, `std::env`; macros `env!`, `option_env!` (a variable named `env` is fine) |
| `no I/O` | paths `std::fs`, `std::io`, `std::net` — `ARCHITECTURE.md` gives `blindside-sim` "no I/O", and a file or socket is an input the replay does not carry. `std::fmt` is *not* banned: a `Display` impl writes into a formatter, not to a device |
| `rule 4` | ident `rand`; any ident beginning `rand_` |
| `rule 5` | ident `rayon`; paths `std::thread`, `core::thread` |
| `lint scope` | source the `src/` walk would not read: `include!`; `#[path = ".."]`, bare or inside `cfg_attr`, that leaves `src/` or does not name a `.rs` file (the walk reads only `*.rs`); in `Cargo.toml`, a `path` under `[lib]` or `[[bin]]` (the root is `src/lib.rs`; see *a hostile manifest* above for what the reader misses) and a build script (`build.rs`, or `[package] build = ".."` other than `false`, since it runs unlinted before the crate compiles); no `src/lib.rs` at all |
| `rule 8` | `unsafe`, `#[allow(unsafe_code)]` or `#[expect(unsafe_code)]` (in any spelling that names both words, `cfg_attr` included) whose comment block directly above — attribute lines between are skipped — has no line starting `// SAFETY:`; `#![allow(unsafe_code)]` anywhere. Doc comments and strings that say `unsafe` are not tokens and pass |
| `dependency tree` | `--check-all` only: a `[dependencies]`, `[build-dependencies]` or `[dev-dependencies]` entry whose *package* is outside the allow-list `blindside-vm`, `blindside-content`, `fixed`, `blake3` (dev-dependencies are inside the check so the rand ban stays one rule; tests draw from `blindside_sim::testing`). A `package = ".."` rename is checked by the package name in both the inline-table and `[dependencies.<key>]` spellings, and `workspace = true` is resolved through the nearest ancestor `Cargo.toml` with a `[workspace]` table; a `workspace = true` key that workspace does not declare is also a finding. `workspace = true` with no workspace above at all only warns (Cargo could not build that crate either) |

The `lint scope` rows run without `--check-all` too, so a `CRATE_DIR` with no `Cargo.toml`
or no `src/lib.rs` is a finding, not a silently short scan.

Positional `CRATE_DIR`s override the default three; CI uses this to lint a copy of
`blindside-sim` with `pub fn bad() -> f64 { 0.0 }` appended and assert the lint fails
(acceptance criterion 5). Run here, with the copy in a temp directory whose path is
abbreviated to `<tmp>`:

```
$ cargo run -p determinism-lint --quiet -- --check-all <tmp>/blindside-sim
<tmp>/blindside-sim\Cargo.toml:16:1: warning: `fixed` is `workspace = true` but no ancestor Cargo.toml has a [workspace] table, so the package it names cannot be checked here
<tmp>/blindside-sim\Cargo.toml:17:1: warning: `blake3` is `workspace = true` but no ancestor Cargo.toml has a [workspace] table, so the package it names cannot be checked here
<tmp>/blindside-sim\src\lib.rs:313:17: `f64` -- rule 1: no f32/f64, fixed-point (Fx) only
<tmp>/blindside-sim\src\lib.rs:313:23: `0.0` -- rule 1: no f32/f64, fixed-point (Fx) only
determinism-lint: FAIL -- 2 finding(s) in 1 file(s) across 1 of 1 crate(s) (sources + layout + Cargo.toml dependencies)
determinism-lint: token-level check; not seen: macro expansion, dependency contents, most pointer casts, indirect `{:p}`, `use std as sys` / glob roots, a hostile manifest, rules 6-8 (`--help` has the list).
```

Exit 1. Two findings — the type and the literal, both on the appended line — and two
warnings: the copy sits outside the workspace, so the `fixed = { workspace = true }` and
`blake3 = { workspace = true }` entries on lines 16 and 17 of `blindside-sim/Cargo.toml`
cannot be resolved there. Warnings do not affect the exit code; the CI job asserts exit 1
and the `f64` line only.

The appended line is 313 because `crates/blindside-sim/src/lib.rs` is 311 lines and the
`printf` prepends a blank one. That number moves every time the sim grows, which is why
the CI job greps ``lib.rs:[0-9]*:[0-9]*: `f64` -- rule 1`` and never a fixed line number:
the check cannot go stale, only this paste can. If it disagrees with
`wc -l crates/blindside-sim/src/lib.rs` plus two, the paste is what is out of date.

Tests: `cargo test -p determinism-lint` runs 16 unit tests and 28 integration tests.

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
  hashers, pointer ingredients, `{:p}` and `fmt::Pointer`, process/env reads, file, socket
  and stream I/O (with a `Display` impl in the same file proving `std::fmt` passes), `r#f64`, a
  float as a range bound, `#[path]` and `include!` leaving `src/`, `#[path]` inside
  `cfg_attr`, `#[path]` to a non-`.rs` file, `[lib]`/`[[bin]] path`, `build.rs` and
  `package.build`, `package = ".."` renames in four spellings, `workspace = true`
  resolution (declared, undeclared, and no workspace at all). The `inject-desync`
  exemption: a crate with a gated fn (exempt), an ungated fn, a gated `mod`, another
  feature's cfg, a float inside a gated fn, a gated `use` and the item after it (all
  caught, 7 findings), plus a file-level `#![cfg(feature = "inject-desync")]` that exempts
  nothing. Rule 8: a crate whose every `unsafe` has a SAFETY line passes; the same crate
  with the lines removed and a blanket `#![allow(unsafe_code)]` fails with 4 findings
  naming each. A crate of near-miss idioms
  — `BTreeMap`, `blake3::Hasher`, `Hash`/`Hasher` bounds, a struct named `Pointer`,
  `t.0 .1`, `0..10`, `..=5`, a parameter named `env`, an in-`src/` `#[path]`, banned words
  and `{{:p}}` in strings, `build = false`, every allowed-dependency spelling — passes with
  no warnings. `--help` and the summary line must name every gap listed above. A missing
  `CRATE_DIR` exits 2.

## CI

`.github/workflows/determinism.yml`. Six jobs on every push and pull request, two more on a
schedule.

| Job | Runs on | What |
|---|---|---|
| `build-test-lint` | ubuntu, macos, windows | `cargo build --workspace --locked`, `cargo test --workspace --locked`, `cargo run -p determinism-lint --locked -- --check-all`, `bash tools/assert-empty-sim.sh`, then six `cargo run -p blindside-harness --release --locked` steps: `canary --record fixtures/phase0-empty-10k.record`, `verify fixtures/phase0-empty-10k.record`, `record --seed 7 --ticks 5000 --out replay.json --hash-log hashes.hashlog`, `run fixtures/phase0-empty-10k.record --dump-state-at 5000`, `batch --seeds 0..100 --ticks 9600 --jobs 8 --out batch.csv` (whose throughput line goes to the job summary), and `golden` twice with `cmp` on the two outputs; uploads `hashes.hashlog` + `batch.csv` + the tick-5000 dump + `replay.json` as artifact `hashes-<os>` |
| `cross-platform` | ubuntu | downloads the three `hashes-*` artifacts and fails unless the three `hashes.hashlog`, the three `batch.csv` **and** the three `phase0-empty-10k.tick5000.dump` are each byte-identical (`cmp`), printing the first differing lines; if it is the dumps that differ it then builds the harness and prints `diff-dumps`' field-level report, so the failure names fields rather than a byte offset |
| `feature-gates` | ubuntu | for every crate in `ci/no-tooling-features.txt`, `cargo tree -e features --locked -p <crate>` must mention neither `diagnostics` nor `inject-desync`; then the same grep must still find both on `blindside-harness`, so a blind check cannot pass silently (BLD-29) |
| `canary-injection` | ubuntu | first: the fixture must still be in `world.rs` and the lint must still pass with it there (BLD-35's exemption is scoped to the item, so it costs the lint nothing). Then with `--features inject-desync`: `canary --record <fixture> --injected` must exit 1 reporting `DESYNC at tick 5000` with `inject_fold` in the diff, and `bisect --record <fixture> --injected` must locate the same tick; then, on the plain build, `canary --record <fixture>` must exit 0 and `--injected` must exit 2 saying the fixture is absent. The job is red if the armed canary passes |
| `unsafe-policy` | ubuntu | BLD-34: `#![deny(unsafe_code)]` must be at the root of sim, vm, gen and content; `ci/fixtures/unsafe-justified` must lint clean; `ci/fixtures/unsafe-unjustified` must fail with exactly four rule-8 findings, one of them the crate-wide `#![allow(unsafe_code)]` |
| `lint-rejects-f64` | ubuntu | `cargo build -p determinism-lint --locked`; copies `crates/blindside-sim` to a temp dir, appends `pub fn bad() -> f64 { 0.0 }`, runs `cargo run -p determinism-lint --locked -- --check-all <copy>` and fails unless it exits 1 naming the `f64` line (the copy's two `workspace = true` warnings, shown above, are expected); then `--check-all` on the unmodified crates as a sanity check |
| `nightly-long-run` | ubuntu, macos, windows | **schedule (07:17 UTC) and `workflow_dispatch` only.** Records 10,000,000 ticks, runs the canary over them (`--hash-every 10000`, which thins the log and not the comparison), `verify`s the same record and `cmp`s the two logs, then runs a 1,000-seed batch; uploads `nightly-<os>` |
| `nightly-cross-platform` | ubuntu | same trigger: the three `long.record`, `long.hashlog` and `batch1000.csv` must be byte-identical |

`cross-platform` is acceptance criterion 3, `canary-injection` is criteria 2 and 4,
`lint-rejects-f64` is criterion 5, and the canary step is criterion 1. Every `cargo` step
passes `--locked` (the committed `Cargo.lock` is authoritative); the harness steps also use
`--release`. `canary-injection` is the only job that enables `inject-desync`, so no
hash-producing step can compile the fixture in.

Every step that PRODUCES a hash — canary, verify, record, batch, golden — runs `cargo run
-p blindside-harness`, never `--workspace`, because Cargo unifies features per package
across one invocation (BLD-29; `docs/HARNESS.md` §7). `cargo build/test --workspace` stay
as they are: they produce no hash that leaves the job.

**The per-commit budget is 10 minutes (BLD-37) and the estimate is about 3.** Run
34066438383, on HEAD `25b3ac8`, took 2 min 10 s end to end: ubuntu 58 s, macOS 46 s,
Windows 2 min 01 s, `lint-rejects-f64` 16 s, `cross-platform` 4 s. That file declared three
jobs, which the OS matrix expanded to those five job runs; the file now declares eight, of
which two are nightly-only. The five steps added to `build-test-lint` since are each well
under a second on the empty sim (parallel window 0.78 s, `verify` 0.07 s, state dump
0.05 s, 100-seed batch 0.05 s, `golden` twice 0.09 s on the dev laptop), and the three
added per-commit jobs run in parallel with the matrix rather than after it, so the chain is
still Windows `build-test-lint` then `cross-platform`. The nightly jobs are outside the
budget by construction: they never run on push. **3 minutes is an estimate against that
measured baseline, not a measurement — the current file has never run.** Re-measure with
`gh run view <id> --json jobs` on the first run after the next push, and after adding a
step; the number to watch is the Windows job, which is half the total on its own.

Not yet in CI: **required status checks on `main`** — a repository setting, not a file, so
it cannot be landed from a branch; the list to require is `build, test, lint, canary` ×3,
`cross-platform`, `feature-gates`, `canary-injection`, `unsafe-policy` and
`lint-rejects-f64`. Also outstanding: the two consecutive green commits BLD-37 asks for
(this branch has not been pushed), and per-OS dumps of the *injected* case, which cannot be
compared across machines at all — the fold value is per-process by construction, so the
cross-OS dump comparison covers the clean case instead (`docs/HARNESS.md` §6).
