# The Phase 0 harness

What the determinism tooling does, what it decided on its own, and how to use it.
`README-phase0.md` is the build-and-test guide; this is the reference.

Companion documents: `PHASE-0-HARNESS.md` (the spec and its five acceptance criteria),
`DETERMINISM.md` (rules 1–8), `ARCHITECTURE.md` (crate layout, `MatchRecord`), and
`PHASE-0-READINESS.md` (each criterion with the command and output that demonstrates it,
the consolidated guess list, and what is still outstanding).

---

## 1. Decisions — the BLD-20 question round, all still open

**This section is the question list, not a record of answers. No designer answer has been
received; nothing below is settled.**

Each question carries the default the build took so Phase 0 could keep moving, why that
default and not another, where it is marked in the source, and what breaks if the answer
comes back "no". Every marker in the code begins `DEFAULT (awaiting designer)` and then
says what and why, so `grep -rn "DEFAULT (awaiting designer)"` is the live index of this
section. That is a claim about a document and a source tree staying in step, so it is
tested rather than asserted: `harness_default_markers_match_the_question_round` in
`crates/blindside-harness/tests/workspace.rs` fails the build if the grep and this
section's `*Marked in:*` lines name different files, in either direction.

**To answer:** put an `x` in one box per question. A `yes` means "the default is the
decision" and the only follow-up work is deleting the marker in the source. A `no` needs
one line underneath saying what instead — that is enough to act on. Questions 1–7 change
recorded hashes, so a `no` there means re-pinning the goldens and bumping the layout or
schema version in the same commit (§8); the rest cost nothing to change.

| # | Question | Default taken | Changing it moves a hash |
|---|---|---|---|
| 1 | State hasher and width | BLAKE3, 256-bit, hand-written LE layout | yes |
| 2 | RNG mix function | SplitMix64 finaliser | yes |
| 3 | `Tick` width | `u64` | yes |
| 4 | Overflow-checks in the hash-producing profile | on, plus `debug-assertions` | yes (on overflow) |
| 5 | `MatchRecord` serialisation format | JSON | yes (the record's bytes) |
| 6 | `MatchRecord` gains `ticks` and `final_hash` | yes | yes (the record's bytes) |
| 7 | Content-hash coverage semantics | whole-pack file bytes | yes |
| 8 | `TeamId` width | `u16` | no (nothing uses it yet) |
| 9 | Bisect semantics | replay + a foreign hash log; a desync never heals | no |
| 10 | Bisect against a sparse foreign log | report the window, not a tick | no |
| 11 | Blessing of the `diagnostics` diff as the sanctioned ground-truth window | built as recommended | no |
| 12 | Is `blindside-content` inside the lint's crate list | **no default taken** | no |
| 13 | `--content DIR` naming a directory that is not there | usage error, exit 2 | no |
| 14 | Tick rate | 20 Hz assumed for reporting only | no |
| 15 | "Phase 0 starts now, in parallel with Phase 2" | **no default taken** | no |

---

**1. State hasher and width.** BLAKE3 over a hand-written little-endian byte layout,
256 bits, with `hash::LAYOUT_VERSION = 2` in the preimage.

*Why:* `content_hash` is already `[u8; 32]`, so a 256-bit state hash keeps one width in the
codebase, one artifact format and one comparison. A 64-bit per-tick hash would be cheaper
to log and would collide about once in 4 billion ticks — a batch run reaches that in an
afternoon, and the failure mode is a desync the canary calls clean. BLAKE3 rather than
std's `DefaultHasher` because `DefaultHasher` is explicitly unstable across std versions,
which is a desync between two machines on different toolchains.
*Marked in:* `crates/blindside-sim/src/hash.rs`.
*If no:* every pinned hash in the repository changes; §8 is the procedure.
**Designer: [ ] yes  [ ] no** —

**2. RNG mix function.** `draw(seed, tick, entity, purpose)` mixes its four inputs with the
SplitMix64 finaliser and takes the high bits as an `Fx` in `[0, 1)`.

*Why:* DETERMINISM.md rule 4 fixes the *shape* (counter-based, stateless, order-independent)
and is silent on the mix. SplitMix64's finaliser is a few integer operations, has no
platform-dependent path, and its avalanche behaviour is published and tested. The
alternative — BLAKE3 per draw — is correct but roughly a hundred times the cost of a draw
that Phase 3 makes several times per agent per tick.
*Marked in:* `crates/blindside-sim/src/rng.rs`; pinned row by row in `golden_tables.rs`.
*If no:* the 40 RNG golden rows and every state hash change together.
**Designer: [ ] yes  [ ] no** —

**3. `Tick` width.** `u64`.

*Why:* nothing in the documents states one. At 20 Hz a `u32` wraps after about seven years
of continuous simulation, which is not a real limit, but a tick counter is also a hash
input and a replay key, and a wrap is a silent hash collision rather than an error. Eight
bytes in the layout costs nothing measurable.
*Marked in:* `crates/blindside-sim/src/ids.rs`.
*If no:* the hash layout changes, so every pinned hash changes.
**Designer: [ ] yes  [ ] no** —

**4. Overflow-checks in the hash-producing profile.** `[profile.release]` sets
`overflow-checks = true` **and** `debug-assertions = true`.

*Why:* this is the one on the list that is a live bug, not a preference. Integer overflow
panics in debug and wraps in release, so a sim that overflows produces one answer under
`cargo test` and a different one under `--release` — a profile-dependent desync that none
of the hard rules name. Turning the checks on in release makes overflow an error
everywhere. `debug-assertions` is needed as well because the `fixed` crate guards its
`+ - * /` with `debug_assert!(!overflow)` and does not consult `overflow-checks` at all;
without it an overflowing `Fx` multiply panics under test and silently wraps in the
build that produces the hashes. Arithmetic that is *meant* to wrap says so
(`wrapping_add`) and is unaffected.
*Marked in:* `Cargo.toml`; `fx_multiply_overflow_panics_in_every_profile` holds under both
profiles.
*If no:* nothing changes today, and Phase 3 gets a class of desync that only appears in
release builds.
**Designer: [ ] yes  [ ] no** —

**5. `MatchRecord` serialisation format.** JSON, pretty-printed, LF, no trailing newline; a
loaded record re-serialises byte-identically.

*Why:* a replay is "a few kilobytes" (DETERMINISM.md) and is read by humans during a
desync hunt more often than by machines. JSON diffs, greps and pastes into a bug report. A
binary format would be smaller and would need its own tooling before it could be debugged.
The byte-identical round trip is what lets a fixture be compared with `cmp`.
*Marked in:* `crates/blindside-sim/src/record.rs`.
*If no:* `fixtures/phase0-empty-10k.record` is rewritten and `MATCH_RECORD_SCHEMA` bumps.
**Designer: [ ] yes  [ ] no** —

**6. `MatchRecord` gains `ticks` and `final_hash`.** Both added.

*Why:* ARCHITECTURE.md's struct has neither, and the acceptance criteria cannot be
expressed without them: "runs a match to completion" needs a length, and "verify the final
state hash matches the recorded one" needs a recorded hash. Putting them in the record
rather than beside it keeps a replay one self-describing file.
*Marked in:* `crates/blindside-sim/src/record.rs`; ARCHITECTURE.md carries the note.
*If no:* say where the length and the expected hash live instead; `verify` and `run` are
built on them.
**Designer: [ ] yes  [ ] no** —

**7. Content-hash coverage semantics.** BLAKE3 over `CONTENT_SCHEMA` and then every file in
the pack, sorted by path, each contributing its path bytes and its file bytes.

*Why:* whole-pack bytes is the semantics that cannot be wrong by omission — anything that
can change a match is in it. The alternative the roadmap implies is hashing only the
*season-enabled* entries, serialised canonically and sorted by stable ID, so that adding
next season's content to the pack does not invalidate this season's replays. That is a
real requirement later (ARCHITECTURE extension rule 5) and it is BLD-63's decision; Phase 0
must not foreclose it, which is why this question is here rather than settled.
*Marked in:* `crates/blindside-content/src/lib.rs`.
*If no:* `EMPTY_PACK_HASH` and every fixture's `content_hash` change.
**Designer: [ ] yes  [ ] no** —

**8. `TeamId` width.** `u16`.

*Why:* no document states one. A match has a handful of teams, and the record sorts
commands by `(tick, team, sequence)`, so all that is needed is a small totally ordered
integer.
*Marked in:* `crates/blindside-sim/src/ids.rs`.
*If no:* a type alias change; nothing is serialised with it yet.
**Designer: [ ] yes  [ ] no** —

**9. Bisect semantics.** A local replay re-run against a *foreign hash log* — one recorded
on another machine, another OS or another commit — binary-searched on the assumption that a
divergence never heals.

*Why:* the in-process canary already finds the tick by walking forward, so bisect earns its
keep only against a log from elsewhere, which is the case that actually happens (the CI
matrix). "Never heals" is what makes binary search valid; it is true for a real state
divergence and false for a transient one, so the implementation falls back to a linear scan
when the binary search lands on a tick that agrees again. The alternative reading — bisect
by *commit* — is `git bisect run`, which this exit-code contract supports (§5).
*Marked in:* `crates/blindside-harness/src/bisect.rs`.
*If no:* the fallback and the exit-code contract are what change.
**Designer: [ ] yes  [ ] no** —

**10. Bisect against a sparse foreign log.** With a log recorded every N ticks, bisect
narrows to the checkpoint window and then walks it in lockstep only when it has a second
local instance to walk against (`--injected`); with a plain foreign log it reports the
**window**, not a tick.

*Why:* the exact tick is not recoverable from what the other machine sent. Reporting a tick
anyway would be a guess presented as a measurement, and at 1am in month nine that is the
number someone will chase.
*Marked in:* `crates/blindside-harness/src/bisect.rs`.
*If no:* the alternative is to demand a per-tick log from every producer, which is 350 KB
per 10,000 ticks per OS.
**Designer: [ ] yes  [ ] no** —

**11. The `diagnostics` diff as the one sanctioned ground-truth window.** Built as
PHASE-0-HARNESS.md recommends: `blindside_sim::diagnostics::{diff, dump}`, `String` only,
behind a cargo feature.

*Why:* the canary's required output is "the tick number, both hashes, and a structural diff
of the two states", and a structural diff of `World` cannot be produced without reading
`World`. Strings mean no type crosses the boundary and nothing downstream can act on the
values; a compile-fail test proves `World` cannot be named or reached through the API.
CLAUDE.md says to stop and ask before passing `&World` anywhere downstream, so this asks.
*Marked in:* `crates/blindside-sim/src/diagnostics.rs`; ARCHITECTURE.md names it.
*If no:* the canary reports a tick and two hashes and no diff, and bisect loses `--injected`
and the state dump.
**Designer: [ ] yes  [ ] no** —

**12. Is `blindside-content` inside the determinism lint's crate list?** **No default
taken** — the lint scans `blindside-sim`, `blindside-vm` and `blindside-gen`, as
DETERMINISM.md names them.

*Why it is open:* `blindside-content` is in `blindside-sim`'s dependency tree, this repo's
standing orders hold it to rules 1–8, and `tests/workspace.rs` treats it as constrained —
but the lint does not scan it, so an `f64` in a content table would be caught by review and
nothing else. Widening the lint's scope is a decision about which crates the rules bind,
not a bug fix, so it was not taken unilaterally.
*If yes:* one line in the lint's default crate list, and `blindside-content` must then
carry the same allow-list discipline.
**Designer: [ ] yes, add it  [ ] no, review covers it** —

**13. `--content DIR` naming a directory that is not there.** Usage error, exit 2 — while
the *built-in default* path is allowed to be absent.

*Why:* the asymmetry is deliberate. Phase 0 ships no `content/` directory and the empty
pack *is* the pack, so the default has to stay lenient. But a path a human typed is a claim
that the pack is there; from Phase 3 a typo would otherwise be indistinguishable from "no
content", and the record would validate against the wrong pack and produce a wrong hash
with no error anywhere.
*Marked in:* `crates/blindside-harness/src/main.rs`.
*If no:* one branch in `content_dir()`.
**Designer: [ ] yes  [ ] no** —

**14. Tick rate.** Nothing in Phase 0 depends on it. Phase 1 ran at 20 Hz and its worst
tick was 33 ms, which rules out 60 Hz. The harness assumes 20 Hz × 480 s = 9,600 ticks per
match in `TICKS_PER_MATCH`, used only as the divisor in the "matches/hour" line.

*Why it is here:* it is on BLD-20's list and Phase 3 needs it, not because Phase 0 is
blocked on it.
*Marked in:* `crates/blindside-harness/src/runner.rs`.
**Designer: [ ] 20 Hz  [ ] other** —

**15. "Phase 0 starts now, before the Phase 1 report and in parallel with Phase 2."**
**No default taken** — it already happened, which is exactly why it needs an answer on the
record rather than an assumption.

*What was done to make it safe:* the sim stayed empty. `tools/assert-empty-sim.sh` (§12)
asserts on every commit that `World` holds only what Phase 0 needs, that `fxmath` has no
implementations, that no `Belief` exists and that no sensor, cave, acoustic or policy code
was written. Phase 3 is still blocked on the Phase 1 and Phase 2 gate reports.
**Designer: [ ] yes, this was fine  [ ] no** —

---

When answers arrive: record them here verbatim and dated, keep every question in place with
its answer, and delete the matching marker in the source in the same commit.

---

## 2. Exit codes

The same for every subcommand. They are what CI and `git bisect run` key off.

| Code | Meaning |
|---|---|
| 0 | Ran, and everything that was compared agreed |
| 1 | A determinism failure: canary divergence, hash mismatch, a located or reproduced desync, two dumps that differ |
| 2 | Could not run: bad arguments, unreadable file, or a file that does not belong (wrong schema, wrong content hash, `--injected` without the `inject-desync` feature) |

Exit 2 is never a determinism result: nothing was compared.

---

## 3. CLI reference

The package is `blindside-harness`; only the binary is `harness`. Run it as
`cargo run -p blindside-harness --release -- <subcommand>`, or directly from
`target/release/harness`. Transcripts below were produced by the release build on Windows;
the hashes are reproducible and are the point, the timings are not.

Global flag: `--content <DIR>` — the content pack a record is validated against. The
default is `<workspace>/content`, resolved at compile time, and it is allowed to be
missing: Phase 0 ships no `content/` directory and the empty pack *is* the pack. A
directory you name yourself must exist (question 13 of §1):

```
$ harness run fixtures/phase0-empty-10k.record --content ./no-such-pack
harness: error: --content ./no-such-pack: no such directory. (The built-in default may be
absent -- that is the empty pack -- but a directory named on the command line must exist.)
                                                                              [exit 2]
```

### The hash log

`verify` and `canary` write one by default at `<record stem>.hashlog` in the current
directory; `run` and `record` write one only when `--hash-log <PATH>` asks; `batch` never
does — its output is the table. The format is plain text, one `tick,hash` line per logged
tick, LF, no header, so `diff`, `cmp` and `sha256sum` work on it and two machines' logs can
be compared without this binary:

```
0,e299d9f373c4ff513633802b5ce9a28237fa0989f068467b704014d42031d12b
1,664104ee0d3ea2b949a36d65e7dde6fc5c3af2f2d4debeba6103a38283cabd3a
2,d8fa48b8307f511973e2f2fa7758c8bf9daa5d6d32d031b32c74500a9178ac8d
```

`--hash-every N` keeps ticks `0, N, 2N, …` and always the final tick, so the last line is
the final hash whatever the cadence. Carrying no seed and no tick count is the price of a
format `diff` understands: a log from *another* record is reported as a divergence at tick
0, not as a usage error, because nothing structural distinguishes the two.

### `run <RECORD>`

Re-runs a record to its tick count, compares the final hash to the recorded one, and
reports throughput. Two passes: steps only, then steps plus hashing, so the per-hash cost
is a difference between passes and no timer sits inside a 15 ns step loop.

```
$ harness run fixtures/phase0-empty-10k.record
record: fixtures/phase0-empty-10k.record  (seed 3735928559, 10000 ticks)
final tick: 10000
final hash: 653b9057c4dd809407213920a217794adafd41c7ea92976e6bf344b76a5639bc
recorded  : 653b9057c4dd809407213920a217794adafd41c7ea92976e6bf344b76a5639bc
wall-clock: 0.003s  (step-only pass 0.000s, hashing pass 0.003s)
ticks/s: 66622252  => 24983344 matches/hour at 9600 ticks/match
hash cost per tick: 247 ns  (10001 hashes, every tick; 0.002s of the hashing pass)
OK: final hash matches record                                                 [exit 0]
```

`hash cost per tick` is only meaningful at `--hash-every 1`, where it is stable: 232, 234
and 249 ns over three runs here. At a sparse cadence the difference between the two passes
is dominated by loop overhead and divided by a handful of hashes, so the figure is noise —
five consecutive runs at `--hash-every 1000` gave 1136, 1572, 6318, 2136 and 4090 ns. The
line names the cadence and the hash count so the reader can tell which kind of number it
is. Do not quote a sparse-cadence figure; it is not reproducible.

`--dump-state-at <TICK>` also writes `diagnostics::dump` of that tick to
`<record stem>.tick<N>.dump` and prints it.

### `record --seed S --ticks N --out PATH`

Runs a fresh empty match and writes the replay with `final_hash` filled in. The record is
validated through the sim's rules before anything reaches disk.

```
$ harness record --seed 7 --ticks 5000 --out replay.json
recorded seed 7, 5000 ticks
record: replay.json
content hash: 3dbd5a09e7a3cb05765522ff5d618722f3ab7784973a3e7c3b8a43c095404ba1
final hash: d61455307886d124f1b6913f95bc70fde56633488e23a80163fb9303500a5b1a
                                                                              [exit 0]
```

### `verify <RECORD>`

Re-runs and compares the **final** hash, and writes the per-tick log. A divergence that
heals before the last tick is therefore caught by `bisect`, not by `verify`.

```
$ harness verify replay.json
verify: replay.json  (seed 7, 5000 ticks)
final hash: d61455307886d124f1b6913f95bc70fde56633488e23a80163fb9303500a5b1a
recorded  : d61455307886d124f1b6913f95bc70fde56633488e23a80163fb9303500a5b1a
wall-clock: 0.001s
hash log: replay.hashlog  (5001 line(s), 5001 entries, every tick to 5000)
OK: final hash matches record                                                 [exit 0]

$ harness verify tampered.json          # final_hash edited by hand
...
recorded  : 061455307886d124f1b6913f95bc70fde56633488e23a80163fb9303500a5b1a
MISMATCH: final hash differs from record                                      [exit 1]

$ harness verify foreign-pack.json      # content_hash edited by hand
harness: error: content hash mismatch: record 0dbd5a09…4ba1 but current content
pack 3dbd5a09…4ba1                                                            [exit 2]
```

### `canary --record <RECORD>`

Acceptance criterion 1. Two `Sim` instances built from that one record through
`Sim::new(&MatchRecord)` — the only constructor there is — stepped in lockstep, hashes
compared after every step.

```
$ harness canary --record fixtures/phase0-empty-10k.record
canary: fixtures/phase0-empty-10k.record  (seed 3735928559, 10000 ticks), two instances in
lockstep
OK: 10000 ticks, hashes identical every tick
final hash: 653b9057c4dd809407213920a217794adafd41c7ea92976e6bf344b76a5639bc
wall-clock: 0.005s
hash log: phase0-empty-10k.hashlog  (10001 line(s), 10001 entries, every tick)  [exit 0]
```

`--injected` arms the BLD-35 fixture in **both** instances (§6). It needs a build carrying
the sim's `inject-desync` feature; without it the run refuses rather than passing quietly:

```
$ harness canary --record <r> --injected            # plain build
harness: error: --injected: this build of blindside-sim has no inject-desync fixture
(build with --features inject-desync)                                         [exit 2]

$ harness canary --record <r> --injected            # --features inject-desync
injected at tick 5000: both instances folded a fresh HashMap's iteration order into
World.inject_fold
DESYNC at tick 5000
  hash A: 2860d9bb1aeefc8ca972f240d57dbeb0dc43db960db7749abf2519702b0215df
  hash B: c6de9872611798244a0f3b658d5cba89ca04b9caac2a5e5854a040148d072a95
  1 differing field(s):
  inject_fold
      A: 0x610d6d30d12f9c0d
      B: 0x04f822a7fbfdbc2f
divergence written to divergence.json
reproduce with: harness bisect --from-divergence divergence.json
wall-clock: 0.002s                                                            [exit 1]
```

`--inject-tick N` moves the injection (default 5000); `--divergence PATH` names the report.

**Two runs of the armed canary print different numbers, and that is the fixture working.**
`hash A`, `hash B` and both `inject_fold` values change on every run, because a `HashMap`'s
iteration order comes from a `RandomState` seeded per process. Three consecutive runs here
produced folds `0x8c8741fd167d45e7 / 0x2c4a81760dbcd6f1`,
`0x306ab3437a155adb / 0x13e2b155046eb28f` and `0xc820ccaf873dd709 / 0xd1394de1639768b9`.
What is reproducible is everything CI asserts: the exit code, the tick, and the field named
in the diff. Never pin an armed canary's hashes, never compare two machines' armed runs, and
do not report "the hashes changed since yesterday" as a finding — the only armed run whose
numbers mean anything is the one that does **not** diverge, which is the failure.

### `bisect` — see §5.

### `diff-dumps <A> <B>`

Field-level diff of two state dumps, typically written on two different machines. A dump
is the only form in which state crosses a machine boundary — strings, produced inside the
sim behind the `diagnostics` feature — so this needs neither machine's `Sim`.

```
$ harness diff-dumps replay.tick42.dump other.tick42.dump
5 differing field(s):
  seed
      A: 7
      B: 8
  agents[1].pos.x
      A: -2.077488187 (0xfffffffdec29bbf3)
      B: 2.4528647 (0x0000000273eef0e4)
  … (agents[1].pos.y, agents[2].pos.x, agents[2].pos.y)                       [exit 1]

$ harness diff-dumps replay.tick42.dump replay.tick42.dump
OK: identical (8 field(s))                                                    [exit 0]
```

Fixed-point values print as decimal *and* raw bits, because the bits are what the hash
covers.

### `batch --seeds A..B [--ticks N] [--jobs J] --out TABLE`

One empty match per seed, at most J at once — parallelism *between* matches only, never
inside a tick (rule 5). `A..B` excludes B and `A..=B` includes it, as in Rust; an empty
range is exit 2. `--ticks` defaults to 9,600 and `--jobs` to the machine's parallelism.

Workers pull the next seed from a shared atomic counter, so the schedule depends on
timing; rows are sorted by seed before the table is written, so the table does not. The
output is plain `seed,final_hash`, LF, no header.

```
$ harness batch --seeds 0..1000 --ticks 9600 --jobs 8 --out j8.csv
batch: 1000 seed(s) 0..=999 x 9600 ticks, 8 job(s)
elapsed: 0.035s
matches/hour: 102767002  aggregate ticks/s: 274045337
table: j8.csv  (1000 line(s), seed,final_hash sorted by seed)                 [exit 0]

$ head -1 j8.csv
0,2d2a08bdd4d9fa98dfd0248800795e9ad85a63f65057f6fc98522e9c310b764f
```

BLD-38's budget is 60 s for that command; a 16-logical-core Windows laptop does it in
0.033–0.037 s over three runs, and 0.136–0.138 s at `--jobs 1`. Treat those as a floor and
a regression tripwire, not a Phase 3 prediction: a Phase 0 tick moves two agents. What the
number *is* good for is J-independence — the J=1, J=8 and J=default tables are
byte-identical (`cmp`), which is what makes the table a cross-machine artifact.

### `golden`

Prints `crates/blindside-sim/src/golden_tables.rs` (40 RNG rows and 48 `Fx` arithmetic
rows, as raw bits) to stdout. Regenerate with:

```
cargo run -p blindside-harness -- golden > crates/blindside-sim/src/golden_tables.rs
cargo fmt --all
```

The raw output is 116 lines; the checked-in file is 476, because rustfmt splits the long
rows. `golden_prints_the_checked_in_tables` compares the two with whitespace collapsed and
`,)` normalised to `)`, so it asserts the *content* is unchanged modulo formatting.

---

## 4. State-hash coverage (BLD-27)

`Sim::state_hash` must cover everything that can affect a future tick and nothing that
cannot. This table mirrors the doc comment on `World`
(`crates/blindside-sim/src/world.rs`), which is the authority; `hash.rs` writes the fields
in this order, `diagnostics::dump` renders them in the same order, and `hash.rs` carries a
mutation test per row.

| Field | Hashed | Why |
|---|---|---|
| `Sim::seed` | yes | every RNG draw is a function of it |
| `tick` | yes | the RNG's first input, and what a replay's commands are keyed on |
| `inject_fold` | yes | must be hashed or the BLD-35 injection would be invisible; always 0 unless the fixture fires |
| `agents` — count, then per agent in `AgentId` order: id, `pos.x`, `pos.y` | yes | positions are the only evolving state; the id is hashed with them so a re-keyed or missing agent changes the hash |
| `moved_last_step` | **no** | derived: rewritten from scratch by every `step`, read by nothing that affects a tick. It exists to prove the hash ignores a cache — `hash.rs` mutates it and expects the same hash |
| `DeterministicRng` | no, beyond the seed | stateless; there is no counter to hash. If one is ever added it moves into the "yes" rows |

The hash is BLAKE3 over a hand-written little-endian layout prefixed by
`hash::LAYOUT_VERSION` (currently 2; history: 1 was seed/tick/agents, 2 inserted
`inject_fold` after `tick`).

**Adding a field:** pick its row above, add it to `StateHash for World` *and*
`hash::debug_fields` in the same position, bump `LAYOUT_VERSION`, and re-pin the goldens
(§8).

---

## 5. Bisect semantics

`bisect` re-runs a record locally and finds the first tick at which the local hashes
disagree with hashes produced *elsewhere* — another run, another OS, another commit. The
in-process canary already finds the tick linearly; bisect earns its keep when the other
side is not in this process.

**The assumption:** a desync never heals. That makes the mismatch monotone in tick, so the
foreign log's entries can be binary-searched with one fresh re-run per probe — about
log₂(entries) re-runs, 15 for a 5,001-entry log. If the *final* entry agrees, the
assumption is violated: that is an edited or corrupt log, not a desync, and bisect falls
back to a single linear pass and says so (`found by linear scan (transient mismatch: final
hash matches)`).

**The foreign side** is exactly one of `--hash-log`, `--injected` or `--from-divergence`.

### `--hash-log <FOREIGN.log>` — a log recorded elsewhere

```
$ harness bisect --record replay.json --hash-log dense7.hashlog          # agrees
bisect: replay.json  (seed 7, 5000 ticks), local re-run vs dense7.hashlog  (5001 entries,
every tick to 5000)
OK: 5000 ticks, none of 5001 checkpoint(s) differs from the recorded hashes    [exit 0]

$ harness bisect --record replay.json --hash-log spliced.hashlog         # diverges @1234
DIVERGENCE at tick 1234  (found by binary search over 5001 checkpoint(s), 15 re-run(s))
  recorded: cdc6325027db0336fb316a709c9f60d8f8aa23a3db72764a41ad4098817b872b
  local   : 0c24647fbecf7e8c8ac8da80f870e4d93cb5bd4b316e18927dab58aee15cc02a
  tick 1233 matched on both sides
local state at tick 1234 (hash 0c24647f…):
  seed = 7 / tick = 1234 / inject_fold = 0x0 / agents.len = 2 / agents[1..2].pos.{x,y}
5 field(s) changed across tick 1233 -> 1234 (suspects): tick, agents[1].pos.x, …
the recorded side supplied hashes only; the diff above is the local instance's change
across the divergent tick
dump of the local state at tick 1234 written to replay.tick1234.dump          [exit 1]
```

The recorded side contributes hashes only — no state crosses the machine boundary — so the
printed diff is the *local* instance's own change across the divergent tick: the fields
that moved during the tick that first disagreed. For a genuine field-level comparison
between the two machines, each writes a dump and `diff-dumps` compares them.

**A sparse foreign log cannot reach the exact tick, and says so** (question 10 of §1). BLD-36
asks that bisect "narrows to the checkpoint then steps linearly to the exact tick". That is
literally achievable only in `--injected` mode, where the foreign side is a process this
binary can re-run. A log recorded every 100 ticks contains no hashes inside the window, so
stepping linearly has nothing to compare against:

```
$ harness bisect --record replay.json --hash-log sparse.hashlog          # foreign N=100
DIVERGENCE at checkpoint tick 1300  (found by binary search over 51 checkpoint(s),
7 re-run(s))
  tick 1200 matched on both sides; the log has no entry in 1201..=1299, so the desync
  began somewhere in that window -- record the other side with --hash-every 1 to pin
  the tick                                                                    [exit 1]
```

Reporting a false exact tick would be worse than reporting the window.

### `--injected` — acceptance criterion 4, in one command

Both the local instance and a third armed instance playing the foreign side carry the
fixture, exactly as every instance of a sim with a real `HashMap` bug would. The foreign
side records its checkpoint log every `--hash-every` ticks; the search narrows to the
checkpoint window and then, because this foreign side *can* be re-run, two fresh armed
instances walk that window in lockstep to the exact tick. Needs a build with
`--features inject-desync`.

```
$ harness bisect --record fixtures/phase0-empty-10k.record --injected
DIVERGENCE at tick 5000  (found by binary search over 10001 checkpoint(s), 16 re-run(s))
  checkpoints bracketed the desync in 4999..=5000; a lockstep walk of that window pinned
  tick 5000
  1 differing field(s) between the two instances:
  inject_fold
      A: 0x0ed15f063c8ef913
      B: 0x4d367fdeecac4531
  …local state at tick 5000, then the 6 fields that changed across 4999 -> 5000
dump of the local state at tick 5000 written to phase0-empty-10k.tick5000.dump [exit 1]

$ harness bisect --record <r> --injected --inject-tick 1234 --hash-every 100
DIVERGENCE at tick 1234  (found by binary search over 101 checkpoint(s), 8 re-run(s))
  checkpoints bracketed the desync in 1200..=1300; a lockstep walk of that window pinned
  tick 1234                                                                   [exit 1]
```

BLD-36's budget is 5 s on a 10,000-tick empty record. Measured on this laptop, three runs
each, wall-clock including process start: `bisect --injected` 50–51 ms, and
`bisect --hash-log` against a dense 10,001-entry log tampered from tick 3000 onward,
47–51 ms and 15 re-runs.

### `--from-divergence <divergence.json>` — reproduce a canary's report

```
$ harness bisect --from-divergence div.json
bisect: reproducing div.json (seed 3735928559, 10000 ticks, divergence at tick 777)
  recorded injection at tick 777
recorded divergence: DESYNC at tick 777 … inject_fold A: 0x6e25… B: 0xfe8a…
fresh local instance at tick 777: hash 1762d2f4…  (matches A: false, matches B: false)
re-run with the recorded injection: DESYNC at tick 777 … inject_fold …
  (fresh HashMap orders on both sides, so the hashes are new; the tick is what must repeat)
REPRODUCED: divergence at tick 777                                            [exit 1]
```

The hashes are new on every run — that is the nature of a `HashMap` ordering bug. **The
tick is what must repeat**, and it does.

### `git bisect run`

The exit codes are `git bisect run`-compatible, so with a hash log from a known-good build
the culprit *commit* is found by:

```
git bisect start <bad> <good>
git bisect run cargo run -p blindside-harness --release -- bisect \
    --record fixtures/phase0-empty-10k.record --hash-log good.hashlog
```

`git bisect run` treats exit 0 as good, 1–124 as bad, and 125 as "skip this commit". Exit 2
therefore counts as *bad*, which is wrong for a commit that merely fails to build or to
read the log. If that becomes a real nuisance, wrap the command in a script that turns 2
into 125; it is not wrapped here because a Phase 0 record cannot fail to load on a commit
that compiles. The same example is in `harness bisect --help`.

---

## 6. The one sanctioned `HashMap` (BLD-35)

`World::inject_desync` (`crates/blindside-sim/src/world.rs`) is the only `HashMap` allowed
in a crate `DETERMINISM.md` constrains, and it exists to violate rule 2 on purpose so that
the canary is proven against the actual failure mode rather than against a state change
that merely looks like one. On the injection tick it builds a fresh
`HashMap<u64, u64>` with 32 entries — fresh means a fresh `RandomState`, so two instances
in one process get different keys and different iteration orders — and folds that order
into the hashed `inject_fold` field with a non-commutative polynomial fold. Both canary
instances call it independently.

Why 32: the story asks for at least 16; 32 makes two maps agree on iteration order with
negligible probability. Run 20× locally, the injection fired 20/20, so the entry count has
not been widened. If a run ever passes, widen `INJECT_ENTRIES` and record the reason here.

The same property that makes the fixture realistic makes its *output* irreproducible: the
fold values and therefore both state hashes differ on every run and every machine (§3). The
armed canary's contract is the exit code, the tick and the field name — not its numbers.

Three things keep it out of everything else:

1. **The feature.** It is compiled only under `inject-desync`, which is not a default
   feature and which only the `canary-injection` CI job and the harness's own dev-dependency
   turn on. A build without it has a stub `Sim::set_inject_tick` that reports the fixture
   absent, and `--injected` exits 2 rather than passing quietly.
2. **The lint exemption is scoped to the item, never to a module path.** `determinism-lint`
   ignores `HashMap`, `HashSet` and the std hashers *inside an item carrying the outer
   attribute* `#[cfg(feature = "inject-desync")]`, that exact spelling. The exemption ends
   with the item's `{…}` body or `;`; it never covers a `mod`, never a file-level
   `#![cfg(…)]`, and exempts nothing else — a float inside the fixture is still a finding.
   `inject_desync_cfg_exempts_hashmap_only_inside_the_gated_item` is the test.
3. **§7's feature-unification check** proves the feature is absent from every non-canary
   build.

---

## 7. Cargo features are not a privacy boundary (BLD-29)

`blindside-sim` declares two gates, both `default = []`: `diagnostics` (the string-only
window onto ground truth) and `inject-desync` (§6). **Declaring them is not enough.**
Cargo unifies features per package across one build invocation, so `cargo build
--workspace` — with `blindside-harness` in it asking for `blindside-sim/diagnostics` —
turns that feature on for `blindside-sim` in *every* crate compiled by that invocation,
including `blindside-client` and `blindside-net` when they exist. The `String` dump of
`World` would then be callable from the client at compile time, and the injected `HashMap`
path could be compiled into a shipped binary.

Two things make the gates real:

- **The crate list and the check.** `ci/no-tooling-features.txt` names every crate whose
  resolved feature set must contain neither gate (`blindside-sim` today; BLD-115 adds the
  client, BLD-164 the net crate). For each, `cargo tree -e features -p <crate>` must
  mention neither. Enforced twice: CI job `feature-gates`, and
  `feature_gates_are_absent_from_the_resolved_sets` in
  `crates/blindside-harness/tests/workspace.rs` so the dev machine fails before the push
  does. The CI job also asserts that the same grep still *finds* the gates on
  `blindside-harness`, because a check that cannot go red is not a check.
- **The build rule.** Every CI step that produces a hash — canary, record, batch, and later
  verify and golden — runs `cargo run -p blindside-harness`, never `--workspace`.
  `cargo build/test --workspace` stay as they are: they produce no hash that leaves the job.

`blindside-harness` is deliberately absent from the list. It is the tool the gates exist
for, and its dev-dependencies arm `inject-desync` on purpose so that `cargo test`
exercises the real fixture. Under resolver 2, dev-dependency features are unified only when
dev-dependencies are being built, so `cargo build -p blindside-harness` does *not* carry
the fixture.

---

## 8. Golden-hash update procedure (BLD-37)

Values pinned in the repository, and what each is for:

| Pin | Where | Covers |
|---|---|---|
| `GOLDEN_SEED_DEADBEEF_TICK_{0,1,1000,10000}` | `crates/blindside-sim/src/hash.rs` | the state hash of the empty sim at four ticks |
| `PIN_SEED_DEADBEEF_TICK_1000` | `crates/blindside-harness/src/lib.rs` | the same tick-1000 value, checked from the harness side |
| `golden_tables.rs` (40 RNG + 48 `Fx` rows) | `crates/blindside-sim/src/golden_tables.rs` | the RNG mix and fixed-point arithmetic, as raw bits |
| `EMPTY_PACK_HASH` | `crates/blindside-content/src/lib.rs` | the content pack hash of the empty pack |
| `fixtures/phase0-empty-10k.record` | 281 bytes, checked in | seed `0xDEADBEEF` × 10,000 ticks and its `final_hash` |

**A checked-in hash may only change deliberately.** To change one:

1. Say which of the four causes it is: a hash-layout change, an RNG or `Fx` change, a
   content-pack change, or a record-format change. If it is none of those, the change is a
   *desync* and the answer is not to re-pin.
2. Bump the matching version in the same commit — `hash::LAYOUT_VERSION` for the state
   hash, `CONTENT_SCHEMA` for the pack, `MATCH_RECORD_SCHEMA` for the record — and add a
   `migrate` arm for the old schema where one applies.
3. Regenerate: `cargo run -p blindside-harness -- golden > …/golden_tables.rs && cargo fmt
   --all` for the tables; `harness record` for the fixture; copy the new state hashes from
   the failing assertions.
4. Re-run the three-OS matrix. All three must produce the *new* value. A re-pin that only
   one platform agrees with is the bug the pin exists to catch.
5. Tick the PR-template checkbox (BLD-34) stating the reason, and update the history line
   on `LAYOUT_VERSION`.

---

## 9. Determinism lint (BLD-21, BLD-22)

`tools/determinism-lint` is a token-level lint over the sources and manifests of
`blindside-sim`, `blindside-vm` and `blindside-gen`. It covers the spellings of
DETERMINISM.md rules 1–5, the spelling half of rule 8, and ARCHITECTURE.md's "no I/O"
(`std::fs`, `std::io`, `std::net` — `std::fmt` is not I/O and is not banned). `--check-all` also checks each crate's
`Cargo.toml` against an allow-list (`blindside-vm`, `blindside-content`, `fixed`,
`blake3`), across `[dependencies]`, `[build-dependencies]` and `[dev-dependencies]` alike.
Comments and doc comments are ignored; string literals are opaque except for a pointer
format spec.

`determinism-lint --help` is the authoritative list of what it rejects and — the section
that matters more — **what it cannot see**: macro-expanded tokens, dependency types,
what a cast operates on, `{:p}` spelled indirectly, `use std as sys`, a hostile
`Cargo.toml`, and rules 6–8, which are not lintable at all. It guards against an honest
author's accidents. A hostile author is what review is for.

### Evasion table (BLD-21)

Two adversarial rounds were run against it: the first found six evasions, all closed; the
second found thirteen more, of which the six it targeted are confirmed closed and the rest
are stated under WHAT THIS CANNOT SEE rather than claimed. Each row below names a test in
`tools/determinism-lint/tests/lint.rs`; the crate has 44 tests in all, 28 there and 16
unit tests in `src/lib.rs`.

| Evasion | Caught | Test |
|---|---|---|
| `f64` field / `f32` literal | yes | `f64_field_fails_and_names_the_line` |
| `f64` appended to a copy of the real crate | yes | `f64_appended_to_a_copy_of_blindside_sim_fails` |
| `HashMap` iteration | yes | `hashmap_iteration_fails_and_names_the_line` |
| `Instant` / `SystemTime` / `std::time` | yes | `std_time_fails_and_names_the_line` |
| a `rand` dependency or `use` | yes | `rand_use_fails`, `check_all_rejects_unexpected_dependency` |
| braced use tree `use std::{thread, time};` | yes | `braced_use_tree_does_not_hide_std_thread_and_time` |
| `DefaultHasher` / `RandomState` / `SipHasher` without naming `HashMap` | yes | `std_hashers_are_rejected_without_naming_hashmap` |
| raw-pointer routes to an address | the common ones | `pointer_to_integer_cast_ingredients_are_rejected` |
| `{:p}` in a string literal | yes | `pointer_format_spec_in_a_string_literal_is_rejected` |
| `std::process` / `std::env` / `env!` | yes | `process_and_environment_reads_are_rejected` |
| `std::fs` / `std::io` / `std::net` (BLD-22's "no I/O") | yes | `file_socket_and_stream_io_are_rejected` |
| a `Display` impl using `std::fmt` | must NOT fire | the same test: three findings, not five |
| raw identifiers (`r#f64`) | yes | `raw_identifiers_do_not_hide_banned_tokens` |
| `include!` or `#[path]` leaving `src/`, bare or under `cfg_attr` | yes | `source_pulled_in_from_outside_src_is_rejected`, `cfg_attr_wrapped_path_attribute_is_rejected`, `path_attribute_to_a_non_rs_file_is_rejected` |
| `[lib]`/`[[bin]]` `path` moving the crate root | yes | `lib_or_bin_path_relocating_the_crate_root_is_rejected` |
| a build script | yes | `build_script_is_rejected` |
| `package = ".."` rename hiding a banned crate | yes | `renamed_package_dependency_is_checked_by_its_real_name` |
| `workspace = true` inheritance hiding one | yes | `workspace_inherited_dependency_is_resolved_to_its_package` |
| `unsafe` or `#[allow(unsafe_code)]` with no `// SAFETY:` | yes | `unsafe_without_a_safety_line_fails_and_with_one_passes` |
| **a comment or doc comment mentioning `f64`** | **must NOT fire** | `comments_strings_and_docs_do_not_false_positive` |
| `1.0..2` range end mistaken for a tuple index | must NOT fire | `range_end_float_is_not_mistaken_for_a_tuple_index` |
| ordinary code under the tightened checks | must NOT fire | `tightened_checks_do_not_fire_on_ordinary_code` |
| `HashMap` inside `#[cfg(feature = "inject-desync")]`, and only there | exempt inside, caught outside | `inject_desync_cfg_exempts_hashmap_only_inside_the_gated_item` |

**Deviation from BLD-21 as written:** the story asks for "a fixture crate outside the
workspace default members … one file per evasion". Most of the table is instead one
temporary crate per test, written to a scratch directory and removed afterwards, plus a
real copy of `blindside-sim` for the `f64` case: same coverage, no checked-in crate that
must be kept compiling. The exception is rule 8, where BLD-34 asks for a fixture that CI
itself runs, so the pass and fail halves are checked in at
`ci/fixtures/unsafe-justified/` and `ci/fixtures/unsafe-unjustified/`. Neither is a
workspace member (each declares an empty `[workspace]` table so cargo ignores it) and
neither is ever compiled — they exist to be read by the lint.

**CI proves the lint can go red as well as green**, which is the property that keeps it
worth having:

| Job | Must pass | Must fail |
|---|---|---|
| `lint-rejects-f64` | the unmodified crates | a copy of `blindside-sim` with `pub fn bad() -> f64 { 0.0 }` appended, naming the line (acceptance criterion 5) |
| `unsafe-policy` | `ci/fixtures/unsafe-justified` | `ci/fixtures/unsafe-unjustified`, with exactly four rule-8 findings |
| `canary-injection` | the workspace **with** the injection fixture in the tree | — (the fixture is the one sanctioned `HashMap`; §6) |
| `feature-gates` | every crate in `ci/no-tooling-features.txt` | — plus a probe asserting the same grep still finds the gates on `blindside-harness`, so a blind check cannot pass |

**Two of BLD-22's bullets cannot be closed from a branch and are open, not omitted:**
making `lint-rejects-f64` a *required* status check on `main` is a repository setting, and
the throwaway-branch demonstration it asks to link needs a pushed branch and a pull
request. The local reproduction of that job, output and all, is in
`PHASE-0-READINESS.md` §5; the link replaces it once there is one.

---

## 10. Dependency audit

Every external dependency of the constrained crates, its determinism properties, and which
golden test catches an upgrade that changes them. All are pinned `=x.y.z` in
`[workspace.dependencies]`; `constrained_crates_pin_every_external_dependency_exactly`
fails if one is not.

| Crate | Version | Determinism properties | What catches a change |
|---|---|---|---|
| `fixed` | `=1.31.0` | `Fx = I32F32`. All arithmetic is integer; no float paths are compiled — no features are enabled, and `f16`, `nightly-float`, `num-traits` and `serde` would each route values through floating point. Rounding is truncation toward zero on multiply and divide. Overflow is guarded by `debug_assert!`, not by `overflow-checks`, which is why `[profile.release]` sets `debug-assertions = true` | the 48 `Fx` rows of `golden_tables.rs`, asserted as raw bits, and `fx_multiply_overflow_panics_in_every_profile` |
| `blake3` | `=1.8.7` | Fixed output for fixed input on every platform; no SIMD path may change the digest, only its speed. Used for both the state hash and the content pack hash | `GOLDEN_SEED_DEADBEEF_TICK_*`, `PIN_SEED_DEADBEEF_TICK_1000`, `EMPTY_PACK_HASH`, and the cross-OS artifact comparison |

That is the whole list. Per crate: `blindside-sim` depends on `fixed`, `blake3` and the
two workspace crates ARCHITECTURE.md allows it (`blindside-vm`, `blindside-content`);
`blindside-content` depends on `blake3` alone; `blindside-vm` and `blindside-gen` have no
dependencies at all. `blindside_sim_depends_on_no_workspace_crate_but_vm_and_content`
fails if that changes.

`no_rand_family_crate_is_reachable_from_a_constrained_crate` walks the resolved graph from
each constrained crate — dev-dependencies included — and fails if `rand`, any `rand_*`,
`rayon` or `libm` is reachable. When `smallvec` or `slotmap` arrive, each needs a row here
(spill behaviour; iteration order) before it is merged.

**An upgrade is never silent.** `Cargo.lock` is committed and every CI step passes
`--locked`, so a bumped version is a diff in a pull request, and the golden tests in the
last column are what turn a *behavioural* change in that version into a red build rather
than into a new hash nobody questioned.

---

## 11. Reconciliation with the other documents

- **Crate names.** `ARCHITECTURE.md` wins: `blindside-*`. `ROADMAP.md` still says
  `deadwater-*` in places; that is the old working title and renaming it is a `git mv` no
  one should spend time on.
- **`MatchRecord`.** `ARCHITECTURE.md`'s struct has neither `ticks` nor `final_hash`; the
  built type has both, per question 6 of §1. `ARCHITECTURE.md` carries a note pointing here.
- **Lint scope.** `DETERMINISM.md` names `blindside-sim`, `blindside-vm` and
  `blindside-gen`; `ROADMAP.md` says only "the sim crate". The lint follows
  `DETERMINISM.md`. `blindside-content` is held to the same rules by this repo's standing
  orders and by `tests/workspace.rs`, but is **not** scanned by the lint — see the open
  question in §1.

---

## 12. The parallel window: what Phase 0 was not allowed to build

Phase 0 was built before the Phase 1 report existed and alongside Phase 2. CLAUDE.md's
build order forbids starting a phase whose predecessor's gate has not been met, and Phase 3
— the sim itself — is blocked on the Phase 1, 2 and 0 gates. So the harness was allowed to
be finished and the sim was not allowed to have started. That is the *parallel window*: the
period in which one crate had to stay empty while the tooling around it was completed.

Nothing in a compiler or a test suite enforces that. A plausible `Cave`, a first `Sensor`,
a `Belief` with one field would all build, all pass, and all be answers to questions the
Phase 1 report is supposed to answer instead. So it is asserted, on every commit and again
at readiness:

```
bash tools/assert-empty-sim.sh
```

```
assert-empty-sim: the Phase 0 parallel window, at <workspace>

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

assert-empty-sim: OK -- the sim is still empty; Phase 0 built only tooling.  [exit 0]
```

What each check is defending, and against what:

| Check | Expected | What it would catch |
|---|---|---|
| `blindside-sim`'s module list | `hash ids record rng world fxmath diagnostics testing golden golden_tables` | a `sensor`, `belief`, `cave`, `acoustics` or `policy` module — a new module in the sim is a new answer to "what does Phase 0 need", and Phase 0 needs none |
| `World`'s fields | `tick agents inject_fold moved_last_step` | ARCHITECTURE.md's Phase 3 `World` growing in early: `cave`, `beacons`, `wrecks`, `deposits`, `ancients`, `acoustics` |
| `fxmath.rs` | declares nothing | fixed-point `sqrt`/`sin`/`cos` written before the golden-table procedure that must pin them (BLD-67) |
| `Belief` | does not exist anywhere under `crates/` | the public half of the truth/belief boundary being shaped before Phase 1 says what belongs in it |
| declaration vocabulary in sim / gen / content | no `struct`, `enum`, `trait`, `impl` or `fn` named `Sensor`, `Belief`, `AcousticField`, `Cave`, `Deposit`, `Ancient`, `Policy`, `Predicate`, … | Phase 3 subject matter arriving under its own name anywhere in the three constrained crates |
| `blindside-gen` | declares nothing | cave generation (BLD-71 and after) |
| `blindside-vm` | declares only `VmBudget` | the bytecode interpreter, which is Phase 4 |
| `blindside-content` | `ContentPack`, `PackEntry`, `PackError`, `content_hash`, `CONTENT_SCHEMA`, `EMPTY_PACK_HASH` and `ContentPack`'s methods | the sensor / module / chassis / ancient registries, which are BLD-68 |

**`World` holds more than a tick, and the story that asked for this script says "World
contains only `tick`".** That is a deliberate, marked deviation, not drift. An empty sim
with a single monotonic counter cannot demonstrate any of the five acceptance criteria: a
hash over a tick counter changes in a way nothing can perturb, so the mutation tests would
have nothing to mutate, a state diff would have nothing to diff, and the injected desync
would have nowhere to hide. `agents` is two agents whose fixed-point positions random-walk
from the stateless RNG; `inject_fold` is the BLD-35 fixture's target; `moved_last_step`
exists precisely to be *excluded* from the hash, proving the hash ignores a cache
(BLD-27). The check therefore pins the exact field set rather than a count, so any further
growth fails.

**What the script is not.** It reads declarations, so a Phase 3 type hidden under a Phase 0
name passes — the same trade the determinism lint makes (§9), for the same reason. It
guards against drift, not against a determined author.

**When the window closes.** BLD-66 re-runs this script before the first Phase 3 commit, as
the last confirmation that nothing was written early. After that the sim is supposed to
grow, and the script's expected sets are updated in the same commit as the code — never
afterwards, and never quietly. Until then a failure has exactly two honest resolutions:
revert the sim change, or name the gate report that authorises it.
