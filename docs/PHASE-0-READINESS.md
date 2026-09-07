# Phase 0 readiness report

**The build is ready for the Phase 0 gate.** Not "the gate is met" — CLAUDE.md reserves
that judgement for a human, and two of the things the gate depends on cannot be produced
from a branch at all (§7).

What follows is the evidence: each of the five `PHASE-0-HARNESS.md` acceptance criteria
with the exact command that demonstrates it and the output that command produced, the
parallel-window assertion, every value the build guessed because no designer answer
exists, and the days it actually took against the spec's estimate.

**Provenance.** Everything below was run on 2026-09-07 against the working tree of
`claude/phase-0-harness`, whose last commit is `25b3ac8` and which carries 50 uncommitted
paths — 31 modified, 19 new. That is the honest state and it matters for reading §6: the CI half of criterion 3
is **pending push**, and the criteria are demonstrated here on one *working tree*, not yet
on one pushed commit.

Transcripts are verbatim except that the absolute workspace path is written `<repo>` and a
temporary directory `<tmp>`.

---

## 1. Criterion 1 — an empty sim runs 10,000 ticks in two instances with identical hashes every tick

```
$ cargo run -p blindside-harness --release --locked -- \
    canary --record fixtures/phase0-empty-10k.record
canary: <repo>/fixtures/phase0-empty-10k.record  (seed 3735928559, 10000 ticks), two
instances in lockstep
OK: 10000 ticks, hashes identical every tick
final hash: 653b9057c4dd809407213920a217794adafd41c7ea92976e6bf344b76a5639bc
wall-clock: 0.005s
hash log: phase0-empty-10k.hashlog  (10001 line(s), 10001 entries, every tick to 10000)
[exit 0]
```

Both instances are built by `Sim::new(&MatchRecord)` — the only constructor there is — so
what the canary proves is what the runner, and later the server and the client, will run.
The comparison is every tick, not the final hash: 10,001 hashes, 10,001 comparisons.

**CI:** the `desync canary on the checked-in fixture` step of `build-test-lint`, on all
three OSes. Ran green on run 34066438383 (HEAD `25b3ac8`, 2026-09-06); **pending push** for
this working tree.

---

## 2. Criterion 2 — a deliberately introduced non-determinism is caught within the tick it occurs

The spec's kill line: *"A canary that does not catch a known bug is worse than no canary,
because it is trusted."* This is the criterion the whole phase is for.

```
$ cargo run -p blindside-harness --release --locked --features inject-desync -- \
    canary --record fixtures/phase0-empty-10k.record --injected
canary: <repo>/fixtures/phase0-empty-10k.record  (seed 3735928559, 10000 ticks), two
instances in lockstep
injected at tick 5000: both instances folded a fresh HashMap's iteration order into
World.inject_fold
DESYNC at tick 5000
  hash A: 1b39e56a93f17c6f5f316646052814b7bf94fe3fbe5cf43f48abffa0a812a32f
  hash B: 44308f20a9492a47c585ded9b8935adc2bb1090e7b14842959de58024a1ce136
  1 differing field(s):
  inject_fold
      A: 0x5a165fd4f1e94be5
      B: 0x405e04b0942a3825
divergence written to divergence.json
reproduce with: harness bisect --from-divergence divergence.json
wall-clock: 0.002s
hash log: phase0-empty-10k.hashlog  (5001 line(s), 5001 entries, every tick to 5000)
[exit 1]
```

Armed at tick 5000, reported at tick 5000 — the tick it occurred, not the next one.

What is injected is the real failure mode, not a stand-in: on the armed tick *each*
instance independently builds a fresh `HashMap<u64, u64>` with 32 entries and folds its
iteration order into a hashed field with a non-commutative polynomial fold. Fresh means a
fresh `RandomState`, so the two instances in one process genuinely see different orders,
exactly as two instances of a sim with a real rule-2 bug would.

**Run 20× on this working tree: fired 20 / 20.** Every run exited 1, reported tick 5000 and
named `inject_fold`. The entry count has not been widened; if a run ever passes, widen
`INJECT_ENTRIES` and record the reason in `HARNESS.md` §6.

**The numbers in that transcript are not reproducible and must never be pinned.** Both
hashes and both folds change on every run, because `RandomState` is seeded per process
(`HARNESS.md` §3, §6). The contract is the exit code, the tick and the field name.

**CI:** job `canary-injection`, which is red if the armed canary passes, and which also
asserts the unarmed canary is clean for 10,000 ticks and that `--injected` on a build
without the feature exits 2. That job is **new in this working tree** — run 34066438383
predates it, so the "CI run within the last 7 days" that BLD-40 asks for is **pending
push**, and this local 20/20 is what stands in the meantime.

---

## 3. Criterion 3 — the same replay produces identical final hashes on Linux, macOS and Windows in CI

Local half, on Windows — the record carries its own `final_hash`, so `verify` is the same
comparison each OS job does before the artifacts are compared to each other:

```
$ cargo run -p blindside-harness --release --locked -- \
    verify fixtures/phase0-empty-10k.record
verify: <repo>/fixtures/phase0-empty-10k.record  (seed 3735928559, 10000 ticks)
final hash: 653b9057c4dd809407213920a217794adafd41c7ea92976e6bf344b76a5639bc
recorded  : 653b9057c4dd809407213920a217794adafd41c7ea92976e6bf344b76a5639bc
wall-clock: 0.002s
hash log: phase0-empty-10k.hashlog  (10001 line(s), 10001 entries, every tick to 10000)
OK: final hash matches record
[exit 0]
```

**This is the one criterion that cannot be demonstrated locally.** It is about three
machines, and the dev machine is one. The CI shape that demonstrates it: each OS job
uploads its per-tick hash log, its 100-seed `seed,final_hash` table and a field-level state
dump at tick 5000; job `cross-platform` downloads all three sets and requires each of the
three files to be byte-identical across the three platforms, printing the first differing
lines and — for the dumps — a field-level `diff-dumps` report if they are not.

Run 34066438383 (2026-09-06, HEAD `25b3ac8`) proved the hash-log third of that on all
three OSes and was green. The batch table and the state dump are **new in this working
tree**: **pending push**.

---

## 4. Criterion 4 — bisect tooling locates an injected divergence in one command

```
$ cargo run -p blindside-harness --release --locked --features inject-desync -- \
    bisect --record fixtures/phase0-empty-10k.record --injected
bisect: <repo>/fixtures/phase0-empty-10k.record  (seed 3735928559, 10000 ticks), both
instances armed for tick 5000; foreign checkpoints every 1 tick(s)
DIVERGENCE at tick 5000  (found by binary search over 10001 checkpoint(s), 16 re-run(s))
  checkpoints bracketed the desync in 4999..=5000; a lockstep walk of that window pinned
  tick 5000
  recorded: 88f23ec01739f56cb2bd770927c35f4ccdcdde4820bce9c703106bf654a83cae
  local   : e336a491bcd0a2c1f2ab24a1e1cb2d30987057624624563efd6f03bac3fc244d
  tick 4999 matched on both sides
  1 differing field(s) between the two instances:
  inject_fold
      A: 0xaf41cdac23ce4495
      B: 0xf241e500cf903501
local state at tick 5000 (hash e336a491…c3fc244d):
  seed = 3735928559
  tick = 5000
  inject_fold = 0xaf41cdac23ce4495
  agents.len = 2
  … (agents[1].pos.x, agents[1].pos.y, agents[2].pos.x, agents[2].pos.y)
6 field(s) changed across tick 4999 -> 5000 (suspects):
  tick
      before: 4999
      after : 5000
  inject_fold
      before: 0x0000000000000000
      after : 0xaf41cdac23ce4495
  … (four more)
dump of the local state at tick 5000 written to phase0-empty-10k.tick5000.dump
[exit 1]
```

One command, exact tick, both hashes, a structural diff, and the local state dumped where
the divergence is. Sixteen re-runs over 10,001 checkpoints; wall clock including process
start was 169 / 47 / 46 ms over three consecutive runs, against BLD-36's 5-second budget.

The other two foreign sides — a hash log recorded on another machine, and a `divergence.json`
written by the canary — are in `HARNESS.md` §5, with the exit-code contract and the
`git bisect run` example that makes bisect-by-commit work with the canary as the test.

**CI:** the `bisect locates the injection in one command` step of `canary-injection`.
**Pending push**, with the rest of that job.

---

## 5. Criterion 5 — CI lint rejects a PR adding `f64` to `blindside-sim`

The CI job reproduced locally, verbatim: copy `blindside-sim`, append a float function,
lint the copy, require failure.

```
$ tmp="$(mktemp -d)"; cp -r crates/blindside-sim "$tmp/blindside-sim"
$ printf '\npub fn bad() -> f64 { 0.0 }\n' >> "$tmp/blindside-sim/src/lib.rs"
$ cargo run -p determinism-lint --locked -- --check-all "$tmp/blindside-sim"
<tmp>/blindside-sim\Cargo.toml:16:1: warning: `fixed` is `workspace = true` but no ancestor
Cargo.toml has a [workspace] table, so the package it names cannot be checked here
<tmp>/blindside-sim\Cargo.toml:17:1: warning: `blake3` is `workspace = true` but no ancestor
Cargo.toml has a [workspace] table, so the package it names cannot be checked here
<tmp>/blindside-sim\src\lib.rs:313:17: `f64` -- rule 1: no f32/f64, fixed-point (Fx) only
<tmp>/blindside-sim\src\lib.rs:313:23: `0.0` -- rule 1: no f32/f64, fixed-point (Fx) only
determinism-lint: FAIL -- 2 finding(s) in 1 file(s) across 1 of 1 crate(s) (sources +
layout + Cargo.toml dependencies)
determinism-lint: token-level check; not seen: macro expansion, dependency contents, most
pointer casts, indirect `{:p}`, `use std as sys` / glob roots, a hostile manifest, rules
6-8 (`--help` has the list).
lint exit code: 1
OK: lint rejects f64 in blindside-sim (acceptance criterion 5)
```

Two findings — the type and the literal. The two warnings are expected: the copy sits
outside the workspace, so its `workspace = true` entries cannot be resolved there.

`--check-all` on the unmodified crates is clean:

```
$ cargo run -p determinism-lint --locked -- --check-all
determinism-lint: OK -- 3 crate(s) clean (sources + layout + Cargo.toml dependencies):
  <repo>/crates/blindside-sim, <repo>/crates/blindside-vm, <repo>/crates/blindside-gen
determinism-lint: token-level check; not seen: macro expansion, dependency contents, most
pointer casts, indirect `{:p}`, `use std as sys` / glob roots, a hostile manifest, rules
6-8 (`--help` has the list).
[exit 0]
```

**CI:** job `lint-rejects-f64` does exactly this on every commit and passes only if the
lint fails, so the lint cannot silently rot. Green on run 34066438383;
**pending push** for this tree.

The scope is what DETERMINISM.md names — `blindside-sim`, `blindside-vm`,
`blindside-gen` — not "the sim crate" alone, and it covers more than `f64`:
`HashMap`/`HashSet` and std's hashers, `std::time`, `rand` and any `rand_*`,
`std::thread` and `rayon`, the raw-pointer routes to an address, `std::process`/`std::env`,
ARCHITECTURE.md's "no I/O" (`std::fs`, `std::io`, `std::net`), `unsafe` without a
`// SAFETY:` line, code linked in from outside `src/`, and any dependency outside the
allow-list.

**What the criterion does not cover, stated so nobody over-reads it.** The lint is
token-level: it rejects the *spellings* of DETERMINISM.md rules 1–5, the spelling half
of rule 8, and the I/O paths. It cannot see macro-expanded tokens, dependency internals, what a cast operates
on, `{:p}` spelled indirectly, a renamed `std`, or a hostile `Cargo.toml`, and rules 6–8
are not lintable at all. `HARNESS.md` §9 has the evasion table with the test that closes
each row, and the lint prints its own gap list on every run, pass or fail. It guards
against an honest author's accidents; a hostile author is what review is for.

---

## 6. The parallel window held

Phase 0 was built before the Phase 1 gate report existed and alongside Phase 2, against a
sim that must stay empty until the Phase 2 gate report exists. The harness was allowed to
be finished; the sim was not allowed to have started.

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

`HARNESS.md` §12 says what each check defends and against what. Two things to read
carefully:

- **`World` holds four fields, not one.** BLD-40's wording is "World contains only
  `tick`". A sim whose entire state is a monotonic counter cannot demonstrate any of the
  five criteria — nothing to mutate in the hash mutation tests, nothing to diff, nowhere
  for an injected desync to hide. So `World` also holds two agents whose fixed-point
  positions random-walk from the stateless RNG, the injection fixture's target, and one
  field that exists precisely to be *excluded* from the hash. The script pins that exact
  field set, so anything further fails.
- **It is a shape check.** It reads declarations, so Phase 3 subject matter hidden under a
  Phase 0 name would pass. Same trade as the lint, same reason.

The script runs in `build-test-lint` on every commit, and BLD-66 re-runs it before the
first Phase 3 commit.

---

## 7. What is not demonstrated, and why

These are the parts of the gate that a branch cannot produce. They are listed here rather
than quietly omitted.

| Gap | Why | What closes it |
|---|---|---|
| **All five criteria on one pushed commit** | nothing here is pushed; the branch's last commit is `25b3ac8` and the tree carries 60 uncommitted paths (31 modified, 29 new) | the next push, whose run URL replaces every "pending push" above |
| **The kill criterion in a CI run within the last 7 days** | job `canary-injection` is new in this tree; the newest run (34066438383, 2026-09-06) predates it | the same push. Until then, the local 20/20 in §2 |
| **Required status checks on `main`** | a repository *setting*, not a file, so it cannot be landed from a branch | someone with admin on the repo requiring: `build, test, lint, canary` ×3, `cross-platform`, `feature-gates`, `canary-injection`, `unsafe-policy`, `lint-rejects-f64` |
| **Two consecutive green commits on three OSes** | BLD-37 asks for it; this branch has been pushed once | two pushes |
| **The throwaway-branch red-check link** | BLD-22 asks for a branch adding `f64` to `blindside-sim` to be shown going red, with the PR link recorded in `HARNESS.md`; that needs a push and a pull request | one throwaway branch, once CI is running on this tree. The job is proven locally in §5 |
| **The BLD-20 answers** | the designer has not answered; every question is still open | one pass through `HARNESS.md` §1, which is written as a tick-box round for exactly this |
| **`diff-dumps` across two machines' *injected* dumps** | impossible by construction: the injected fold is per-process, so two machines' armed dumps must differ and comparing them proves nothing | the clean-case cross-OS dump comparison in `cross-platform` covers the useful direction; the injected case stays a single-machine, two-instance test |

---

## 8. GUESSES — every value chosen without a designer answer

Consolidated from all three build stages.

Rows 1-12 and 17 are the BLD-20 questions. Each is marked at the site of the decision with
a comment beginning `DEFAULT (awaiting designer)`, and each is a question in `HARNESS.md`
§1 that the designer can answer with a tick. `grep -rn "DEFAULT (awaiting designer)"`
returns twelve lines in source across ten files (`ids.rs` and `bisect.rs` carry two each)
plus one in `ARCHITECTURE.md`.

Rows 13-16 are choices no BLD-20 question covers. They are argued in a doc comment where
they are made and carry no marker, because the marker means "a designer answer is
outstanding" and for these none was asked for.

`harness_default_markers_match_the_question_round` in
`crates/blindside-harness/tests/workspace.rs` asserts both directions of the first
correspondence -- a marked file §1 does not name, and a file §1 names that carries no
marker -- so a default cannot quietly drop out of the question round. It exists because
one had: the tick rate, row 17, was defaulted under a plain doc comment and was listed
below as a question with no default at all.

**Hash-affecting — changing any of these re-pins every golden value (`HARNESS.md` §8):**

| # | Guess | Marked in |
|---|---|---|
| 1 | State hasher is BLAKE3, 256-bit, over a hand-written little-endian layout, with `LAYOUT_VERSION = 2` in the preimage | `crates/blindside-sim/src/hash.rs` |
| 2 | RNG mix is the SplitMix64 finaliser, one round per input, high bits taken as `Fx` in `[0, 1)` | `crates/blindside-sim/src/rng.rs` |
| 3 | `Tick` is `u64` | `crates/blindside-sim/src/ids.rs` |
| 4 | `[profile.release]` sets `overflow-checks = true` **and** `debug-assertions = true`, so integer and `Fx` overflow panic in every profile | `Cargo.toml` |
| 5 | `MatchRecord` is JSON — pretty, LF, no trailing newline, byte-identical round trip | `crates/blindside-sim/src/record.rs` |
| 6 | `MatchRecord` gains `ticks` and `final_hash`, which `ARCHITECTURE.md`'s struct does not have | `crates/blindside-sim/src/record.rs`, `docs/ARCHITECTURE.md` |
| 7 | The content hash covers the whole pack's file bytes, not the season-enabled entry set | `crates/blindside-content/src/lib.rs` |

**Not hash-affecting:**

| # | Guess | Marked in |
|---|---|---|
| 8 | `TeamId` is `u16` | `crates/blindside-sim/src/ids.rs` |
| 9 | Bisect means a local replay against a *foreign hash log*, binary-searched on the assumption that a desync never heals, with a linear fallback for a transient one | `crates/blindside-harness/src/bisect.rs` |
| 10 | With a sparse foreign log, bisect reports the **window**, not a tick — the exact tick is not recoverable from what the other machine sent | `crates/blindside-harness/src/bisect.rs` |
| 11 | `blindside_sim::diagnostics` is the sanctioned string-only ground-truth window, as `PHASE-0-HARNESS.md` recommends | `crates/blindside-sim/src/diagnostics.rs` |
| 12 | `--content DIR` naming a missing directory is exit 2, while the *built-in default* may be absent | `crates/blindside-harness/src/main.rs` |
| 13 | Dev-dependencies are inside the lint's dependency check, so the `rand` ban stays one rule | `tools/determinism-lint/src/lib.rs` |
| 14 | `inject_fold` is an unconditional `World` field (only the writer is feature-gated), so feature-on and feature-off builds share one hash layout and agree until the injection tick | `crates/blindside-sim/src/world.rs` |
| 15 | `INJECT_ENTRIES = 32` (BLD-35 asks for ≥16); the injection tick defaults to 5,000 in the *harness*, and the sim has no default; tick 0 is refused | `crates/blindside-sim/src/world.rs`, `crates/blindside-harness/src/main.rs` |
| 16 | `Purpose::TestShuffle = 0xFF00` is reserved for test helpers so they never collide with a sim purpose | `crates/blindside-sim/src/rng.rs` |
| 17 | Tick rate is 20 Hz, so `TICKS_PER_MATCH = 9_600` (20 Hz × 480 s) — the divisor in every "matches/hour" line in these documents and nothing else | `crates/blindside-harness/src/runner.rs` |

**Spec-silent choices with no marker, listed so they are not invisible:**

| # | Choice |
|---|---|
| 18 | `ci/no-tooling-features.txt` as the BLD-29 crate-list file's name and location, and `feature "<gate>"` as the grep; `blindside-harness` deliberately excluded, with a probe step asserting the grep still finds the gates there |
| 19 | The per-commit CI batch is 100 seeds × 9,600 ticks × `--jobs 8`; BLD-38 says "a 100-seed batch" and states neither ticks nor jobs |
| 20 | The nightly long run is 10,000,000 ticks and 1,000 seeds, on a 07:17 UTC cron plus `workflow_dispatch`; BLD-37 asks only that a nightly variant exist |
| 21 | `docs/HARNESS.md`'s section list and ordering, and the decision to keep transcripts in two places (README short form, HARNESS.md annotated) rather than one |
| 22 | The rule-8 CI fixtures are checked in at `ci/fixtures/unsafe-{justified,unjustified}/`, each with an empty `[workspace]` table so cargo ignores them; every other lint fixture stays a temp crate written by its test |
| 23 | `tools/assert-empty-sim.sh`'s expected sets — the sim module list, `World`'s four fields, `blindside-vm`'s single item, `blindside-content`'s public surface, and the banned declaration vocabulary |
| 24 | The `ARCHITECTURE.md` and `ROADMAP.md` edits are additive notes, not rewrites (BLD-39) |

**Open questions with no default at all,** because no code needed one: whether
`blindside-content` joins the lint's crate list (it is held to rules 1–8 by standing orders
and by `tests/workspace.rs`, but the lint does not scan it), and whether starting Phase 0
in parallel with Phase 2 was the right call. Both are in `HARNESS.md` §1 and say so there
in the same words. The tick rate is **not** one of them: it was defaulted (row 17 above),
the number is quoted in every throughput line in these documents, and calling it
undefaulted would hide a choice that has already been made.

---

## 9. Effort against the estimate

`PHASE-0-HARNESS.md` says **"Estimated: 1 weekend."** `DEV-PLAN.md`'s BLD-18 epic
independently estimates **17.5 working days** across 22 stories, plus at least 14 calendar
days of latency for the three human-gated ones.

Counted from `git log` on `claude/phase-0-harness`, plus the uncommitted work in this tree:

| | |
|---|---|
| First Phase 0 commit | `659f055`, 2026-09-06 17:48 −0400 |
| Last commit | `25b3ac8`, 2026-09-06 19:16 −0400 |
| Commits | 7, all on 2026-09-06, spanning 1 h 28 min |
| Uncommitted work | 2026-09-07: four verification-and-hardening passes over the same tree, 60 paths changed or added |
| **Working days elapsed** | **2** (2026-09-06 and 2026-09-07) |
| **Calendar days** | **2** |
| Human-gated latency so far | **0** — none of the three human gates has started |

**Read that carefully before recalibrating anything.** Two days against "one weekend" is
on estimate, and against the board's 17.5 working days it is not a velocity finding: the
work was done by agents running in sequence with no meetings, no context switches and no
waiting, and the epic's three human-gated stories — the BLD-20 designer round (BLD-20), the
CI required-status-check setup (BLD-37) and the reading of this report (BLD-40) — have not
started and carry the 14 calendar days the plan allows for them. The useful number for
recalibrating ROADMAP's floor estimates is therefore "2 working days of build, with every
human gate still outstanding", not "17.5 → 2".

One number is worth carrying to Phase 3: three of the four passes over this tree were
adversarial review of what the previous pass had built, and each one found real defects — a
canary proven against a state change rather than an order bug, a lint with six then thirteen
evasions, CI steps that printed OK on a failing iteration, three throughput figures that did
not reproduce, a pasted lint transcript whose line number was seventeen lines stale, and a
default taken under a plain doc comment that two documents then described as no default at
all. Budget for that, not for the first draft.

---

## 10. What Phase 3 inherits

- **`blindside-sim` is still empty**, and must stay so until the Phase 2 gate report exists
  (CLAUDE.md build order). `tools/assert-empty-sim.sh` enforces it on every commit; BLD-66
  re-runs it before the first Phase 3 commit.
- **The one invariant is laid down.** `World` is `pub(crate)`; the only window onto it is
  `blindside_sim::diagnostics`, strings only, behind a feature no shipping crate may
  enable, with a compile-fail test proving `World` cannot be named or reached through that
  API and a CI job proving the feature is absent from every non-tooling build.
- **Every checked-in hash has a procedure attached** (`HARNESS.md` §8): a hash may only
  change together with a schema bump or a content-pack change, in the same PR, with the
  reason stated on the PR-template checkbox. A hash that moved for any other reason is a
  desync, and the answer is not to re-pin it.
- **The tooling exists before it is needed.** Bisect, `diff-dumps`, the state dump, the
  batch table and the nightly long run were all built against an empty sim, which is the
  only time they are cheap to build. `PHASE-0-HARNESS.md`: building bisect the first time
  you need it, at 1am in month nine, is how projects die.
- **Thirteen defaults are waiting on one designer pass**, marked at the site of each
  decision by twelve comments in source and one note in `ARCHITECTURE.md`, and written up
  as fifteen tick-box questions in `HARNESS.md` §1 (two of which took no default at all).
  Seven of the thirteen move recorded hashes, so answering them before Phase 3 writes real
  state costs one commit; answering them after costs a re-pin of everything.

---

*Report written 2026-09-07 against the working tree of `claude/phase-0-harness` at
`25b3ac8` + 60 uncommitted paths. Every "pending push" above becomes a run URL on the next
push. Ready for the Phase 0 gate.*
