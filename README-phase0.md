# Phase 0 harness: build, test, run

Rust workspace for the BLINDSIDE determinism harness (`docs/PHASE-0-HARNESS.md`). The sim
it exercises is deliberately empty; the tooling is the deliverable.

## Layout

```
Cargo.toml                    workspace root
rust-toolchain.toml           pins stable
crates/blindside-sim          deterministic core (constrained, see docs/DETERMINISM.md)
crates/blindside-vm           bytecode VM (constrained) - stub
crates/blindside-content      content definitions - stub
crates/blindside-gen          world generation (constrained) - stub
crates/blindside-harness      headless runner, canary, replay, bisect (unconstrained)
tools/determinism-lint        CI lint for the constrained crates
```

## Build

```
cargo build --workspace
cargo build --workspace --release      # for throughput numbers
```

## Test

```
cargo test --workspace
```

`blindside-sim` unit tests check that two sims with the same seed hash identically for
1000 ticks, that different seeds differ, and that `DeterministicRng::draw` is
order-independent.

## Tools

<!-- Later Phase 0 tasks: replace each placeholder with the real invocation. -->

### Headless runner

```
cargo run -p blindside-harness -- run <TODO: args>
```

TODO: runs a `MatchRecord` to completion with no renderer; prints final tick, final state
hash, and matches-per-hour throughput.

### Desync canary

```
cargo run -p blindside-harness -- canary <TODO: args>
```

TODO: two `Sim` instances in lockstep, hash compared every tick, panics on first
divergence with tick, both hashes, and a structural diff from `Sim::state_debug`.

### Replay verify

```
cargo run -p blindside-harness -- replay <TODO: path>
```

TODO: loads a replay (seed + input log + content pack hash), re-runs it, checks the final
hash against the recorded one.

### Bisect

```
cargo run -p blindside-harness -- bisect <TODO: args>
```

TODO: one command to re-run a divergent replay, bisect by tick, and dump the state diff
at the divergence point.

### Determinism lint

```
cargo run -p determinism-lint -- --check-all            # what CI runs
cargo run -p determinism-lint -- [--root DIR] [--check-all] [-q] [CRATE_DIR ...]
cargo run -p determinism-lint -- --help
```

Enforces `docs/DETERMINISM.md` rules 1-5 in `crates/blindside-sim`, `crates/blindside-vm`
and `crates/blindside-gen` (`tools/determinism-lint`). Every `src/**/*.rs` is lexed with
`proc-macro2` (the front end `syn` is built on) and scanned at the token level, so
comments, doc comments and string literals never false-positive. Rejected:

| Rule | Tokens |
|---|---|
| 1 float | idents `f32`, `f64`; any float literal (`0.0`, `1e3`, `2.5f32`) |
| 2 unordered | idents `HashMap`, `HashSet` |
| 3 wall clock | idents `SystemTime`, `Instant`; paths `std::time`, `core::time` |
| 4 rand | ident `rand`, any `rand_*` crate |
| 5 threads | ident `rayon`; paths `std::thread`, `core::thread` |

Each hit prints `file:line:column: \`token\` -- rule ...`, followed by a summary line.
Exit code 0 clean, 1 findings, 2 usage/IO error.

`--check-all` additionally reads each crate's `Cargo.toml` and fails on any
`[dependencies]` / `[build-dependencies]` entry outside the allow-list
`blindside-vm`, `blindside-content`, `fixed`, `blake3` (`[dev-dependencies]` only warn).

Positional `CRATE_DIR`s override the default three; CI uses this to lint a copy of
`blindside-sim` with `pub fn bad() -> f64 { 0.0 }` appended and assert the lint fails
(acceptance criterion 5). Tests: `cargo test -p determinism-lint` (unit tests on the
scanner and manifest reader; integration tests that run the binary on the real workspace
and on temp crates containing an `f64` field, a `HashMap`, `std::time::Instant`, `rand`,
and a disallowed dependency).

## CI

`.github/workflows/determinism.yml`, on every push and pull request:

| Job | Runs on | What |
|---|---|---|
| `build-test-lint` | ubuntu, macos, windows | `cargo build --workspace`, `cargo test --workspace`, `determinism-lint --check-all`, `blindside-harness canary --ticks 10000`, `blindside-harness record --seed 7 --ticks 5000 --out replay.json --hashes hashes.json`; uploads `hashes.json` + `replay.json` as artifact `hashes-<os>` |
| `cross-platform` | ubuntu | downloads the three `hashes-*` artifacts and fails unless the three `hashes.json` are byte-identical (`cmp`), printing the first differing lines |
| `lint-rejects-f64` | ubuntu | copies `crates/blindside-sim` to a temp dir, appends `pub fn bad() -> f64 { 0.0 }`, runs the lint on the copy and fails unless the lint exits 1 naming the `f64` line |

`cross-platform` is acceptance criterion 3, `lint-rejects-f64` is criterion 5, and the
canary step is criterion 1. Both `cargo run` harness steps use `--release` and
`--locked` (the committed `Cargo.lock` is authoritative).
