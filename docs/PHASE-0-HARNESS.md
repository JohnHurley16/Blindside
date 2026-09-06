# Phase 0 — Harness

**Language:** Rust. **Estimated: 1 weekend.** **Build immediately before Phase 3, not first.**

This is not a game. It is the tooling that makes eighteen months of determinism work
survivable. Building it against an empty sim is cheap; retrofitting it is not possible.

---

## Components

**`blindside-harness` — headless runner.** Loads a `MatchRecord` (seed, content hash,
loadouts, policies, command log) and runs a match to completion with no renderer. Must
run thousands of matches per hour on a laptop.

**Desync canary.** Two `Sim` instances in one process, constructed from identical inputs,
stepped in lockstep. State hash computed every tick and compared. On divergence: panic
with the tick number, both hashes, and a structural diff of the two states.

Hash must cover everything that can affect future ticks and nothing that cannot —
including RNG call counters if any state is kept, excluding caches and derived values.
Getting the hash wrong in either direction wastes weeks.

**Bisect tooling.** One command to re-run a divergent replay, bisect by tick, and dump
the state diff at the divergence point. Build this now. Building it the first time you
need it, at 1am in month nine, is how projects die.

**Replay format.** Seed plus input log plus content pack hash. Load, re-run, verify the
final state hash matches the recorded one.

**CI determinism lint.** Rejects `f32`, `f64`, `HashMap`/`HashSet` iteration,
`std::time`, and `rand` appearing in `blindside-sim`, `blindside-vm`, `blindside-gen`.
See `DETERMINISM.md`.

---

## Acceptance criteria

- [ ] An empty sim runs 10,000 ticks in two instances with identical hashes every tick
- [ ] A deliberately introduced non-determinism (e.g. a `HashMap` iteration) is caught by
      the canary within the tick it occurs
- [ ] The same replay produces identical final hashes on Linux, macOS, and Windows in CI
- [ ] Bisect tooling locates an injected divergence in one command
- [ ] CI lint rejects a PR adding `f64` to `blindside-sim`

The second criterion matters most. A canary that does not catch a known bug is worse than
no canary, because it is trusted.
