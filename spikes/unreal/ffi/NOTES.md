# Rust → Unreal over a C ABI

**Spike question.** The designer asked: *"why do I need c++ for everything? can I not ship
rust with unreal and have a thin c++ layer that calls the backend?"*

**Answer: yes, and it is running.** Unreal Engine 5.6 is displaying a tick count and a
BLAKE3 state hash produced by `blindside-sim`, at a 20 Hz fixed timestep, copying an
184 KB belief snapshot across the boundary every tick for 9.5 µs. The C++ that makes that
happen is **148 lines** including comments (31 of them a `.Build.cs`). It hot-reloads
without restarting the editor. Nothing in the generated header can return `World`.

This is not a recommendation to migrate. It is the evidence you asked for so the decision
can be made on something other than my say-so; the honest comparison against gdext is
§10, and it is not one-sided.

---

## 0. What is here

```
spikes/unreal/ffi/
  NOTES.md                   this file
  build.ps1                  the one command
  shot.ps1                   screenshot helper (see 9.2 for why it exists)
  rust/
    Cargo.toml               spike workspace
    vendor/                  blindside-{sim,vm,content}, COPIED, unmodified
    crates/blindside-ffi/
      src/lib.rs             the C ABI: 618 lines (314 excl. blanks/comments) + 131 of tests
      build.rs               runs cbindgen
      cbindgen.toml
      include/blindside_sim.h   GENERATED. 323 lines. The whole boundary.
      tests/header_surface.rs   audits the generated header
      tests/no_diagnostics.rs   the sim's ground-truth window stays off
      src/bin/bench_snapshot.rs the cost table in 4
  cpptest/
    smoke.cpp                the ABI without Unreal, linked both ways
    build.cmd
  unreal/BlindsideFfi/       UE 5.6 project, code only, no .umap
  shots/                     the proof
  logs/                      build log, engine log, C++ smoke output
```

`rust/vendor/` is `crates/blindside-{sim,vm,content}` copied verbatim from
`claude/harness-plus-induct` (commit in `vendor/VENDORED-FROM.txt`), because that branch is
not checked out in this working tree and a spike must not check one out over the top of
another agent's. **Nothing in `vendor/` was edited.** The point of the exercise is that the
FFI wraps the sim's *real* public surface — `Sim::new`, `step`, `tick`, `seed`,
`state_hash` — with no changes asked of it.

---

## 1. The interface

The whole boundary, from `include/blindside_sim.h`. Fifteen functions, one opaque handle,
two POD structs, one status enum:

```c
uint32_t     bs_abi_version(void);
uint32_t     bs_belief_schema(void);
uint32_t     bs_belief_header_size(void);
uint32_t     bs_belief_point_size(void);
const char*  bs_status_message(BsStatus status);

struct BsSim* bs_sim_create(uint64_t seed, uint32_t belief_points);
void          bs_sim_destroy(struct BsSim *sim);
BsStatus      bs_sim_step(struct BsSim *sim, uint32_t ticks);
BsStatus      bs_sim_tick(const struct BsSim *sim, uint64_t *out_tick);
BsStatus      bs_sim_seed(const struct BsSim *sim, uint64_t *out_seed);
BsStatus      bs_sim_state_hash(const struct BsSim *sim, uint8_t *out32);
BsStatus      bs_sim_agent_count(const struct BsSim *sim, uint32_t *out_count);
BsStatus      bs_sim_belief_bytes(const struct BsSim *sim, uint32_t agent_index,
                                  uint32_t *out_bytes);
BsStatus      bs_sim_belief_snapshot(const struct BsSim *sim, uint32_t agent_index,
                                     uint8_t *buffer, uint32_t buffer_bytes,
                                     uint32_t *out_written);
BsStatus      bs_sim_spike_force_panic(const struct BsSim *sim);   /* SPIKE ONLY */
```

Rules it obeys, each of which is a thing that goes wrong at a boundary if you do not
decide it on day one:

- **Every call returns a status; 0 is success and every failure is negative,** so
  `if (status < 0)` is a correct check in C for the whole API forever. Values come back
  through out-parameters.
- **No panic crosses.** Every `extern "C"` body is wrapped in `catch_unwind`. Since Rust
  1.81 an unwind out of `extern "C"` aborts the process, and aborting inside the editor
  costs the user their unsaved work. Proven running, §5.3.
- **The caller frees nothing it cannot free.** The only owned thing handed out is the
  opaque `BsSim*`, freed by `bs_sim_destroy` (null is a documented no-op). Snapshots go
  into a caller-provided buffer. `bs_status_message` returns a `'static` pointer.
- **No allocation on the per-tick path.** The staging buffer is allocated once at create.
  `bs_sim_belief_snapshot` is a bounds check and two `memcpy`s.
- **Nothing that crosses is a float.** Fixed-point values cross as raw `int64_t` bits of
  `Fx = I32F32`. DETERMINISM.md rule 1 bans `f32`/`f64` in the sim, and "just to hand to
  the renderer" is the same violation wearing a different hat. The renderer divides by
  2^32 on its own side of the line, where floats are nobody's determinism problem.
  `tests/header_surface.rs::nothing_that_crosses_is_a_float` enforces this against the
  generated header.
- **Two independent version numbers.** `BS_ABI_VERSION` for the function shapes,
  `BS_BELIEF_SCHEMA` for the snapshot layout, because the snapshot will change far more
  often than the calls that carry it. Both are checked at load, along with
  `sizeof(BsBeliefHeader)` and `sizeof(BsBeliefPoint)` against what the DLL reports — a
  header and a binary that disagree read every snapshot at the wrong offsets, and that is
  a silent bug.

### 1.1 The belief snapshot

72-byte header, then `point_count` × 16-byte points, in the caller's buffer:

```c
typedef struct BsBeliefHeader {
    uint32_t schema;  uint32_t agent_index;  uint64_t tick;
    int64_t  pose_x, pose_y, pose_z, pose_yaw;   /* Fx raw bits */
    int64_t  pose_var;                            /* covariance trace: "how lost am I" */
    uint32_t ticks_since_fix, point_count, flags, reserved;
} BsBeliefHeader;                                 /* 72 bytes, align 8 */

typedef struct BsBeliefPoint {
    int32_t  x, y, z;        /* Fx16.16 raw bits, agent's ESTIMATED frame */
    uint16_t quality, age;   /* brightness, fade */
} BsBeliefPoint;                                  /* 16 bytes, align 4 */
```

Points are Fx16.16, not the sim's full I32F32: a display point does not need 32 fractional
bits and halving the width halves the copy, which is the one cost that recurs forever. The
truncation happens on the render side and never feeds back.

**The contents are a stand-in and must be read as one.** Phase 0's sim has no `Belief` and
no public accessor to an agent, so there is nothing real to snapshot yet. The FFI derives a
point cloud deterministically from `Sim::state_hash()` and `Sim::tick()` — both public,
both genuinely functions of simulation state — so that the bytes provably came from the
sim, change when it does, and have realistic *volume*, which is the thing being measured.
Nobody should tune anything against these positions. What Phase 3 keeps is the *shape*:
stage into a reused buffer on step, memcpy out on demand.

---

## 2. The build recipe

```powershell
cd spikes\unreal\ffi
.\build.ps1                     # rust, then unreal
.\build.ps1 -Clean -Test -Bench # from nothing, with the test suite and the cost table
.\build.ps1 -Run                # ...and launch it
```

Order is not negotiable and the script enforces it: cargo produces `blindside_ffi.dll` and,
via `build.rs` + cbindgen, `include/blindside_sim.h`; then UnrealBuildTool compiles the C++
that includes that header. `BlindsideSim.Build.cs` throws a `BuildException` naming the
cargo command if either artefact is missing, because a missing header is a clearer error
than a stale one.

**From clean, on this machine** (`logs/build-clean.log`): cargo 21.7 s, UBT 44.5 s, ≈ 66 s
total. Incremental after a one-line Rust change: cargo 1.8–8.2 s. Incremental after a C++
change: UBT 3–10 s.

### 2.1 Toolchain: what had to be found now rather than in six months

**No special Rust target. No CRT flag. No linker setting.** Default
`x86_64-pc-windows-msvc`, cargo 1.98.1, Unreal's default `/MD`. A cdylib is a
self-contained DLL that links its own UCRT; nothing about Unreal's allocator, exception
model or CRT reaches across a C ABI. This is the single biggest practical advantage of the
C ABI over a C++ or engine-plugin boundary, and it is worth stating plainly because the
usual fear about "Rust in Unreal" is exactly this and the fear is misplaced.

**The engine version is a real problem, and it is 5.8's.**

| | UE 5.6.1 | UE 5.8.1 |
|---|---|---|
| Installed MSVC | 14.43.34808 | 14.43.34808 |
| `MinimumVisualCppVersion` | 14.38.33130 | 14.38.33130 |
| `BannedVisualCppVersions` | 14.39.x, 14.40.x | 14.39.x, **14.40.0–14.43.99999**, 14.44 < .35211, 14.50 < .35723 |
| Result here | **builds** (with a "not a preferred version" warning; 5.6 prefers 14.38.33130) | **refuses** |

(from `Engine/Config/Windows/Windows_SDK.json` in each install.) **Everything in this spike
was built and run on 5.6.1.** To use 5.8 this machine needs MSVC 14.44.35211+ (VS 2022
17.14) or 14.50.35723+ (VS 2026) installed alongside. That is a download, not a problem —
but it is the kind of thing that eats a morning when you find it under deadline. Nothing in
the boundary itself is version-specific; the only 5.6-isms in the project are
`IncludeOrderVersion = EngineIncludeOrderVersion.Unreal5_6` in the two `.Target.cs` files
and `"EngineAssociation": "5.6"` in the `.uproject`.

**Only VS 2022 *Build Tools* are installed — no IDE, no WinDbg.** UBT is happy with that.
It matters for §7.

### 2.2 cdylib or staticlib

Both work. `cpptest/build.cmd` builds and runs the same C++ smoke test against each, under
`/MD /W4 /WX`, and they produce **byte-identical state hashes** (`logs/cpptest.log`).

| | cdylib (`blindside_ffi.dll`) | staticlib (`blindside_ffi.lib`) |
|---|---|---|
| Artefact | 212 KB DLL + 1.4 MB PDB | 13.6 MB `.lib` |
| Extra link inputs | none (or `blindside_ffi.dll.lib` if importing) | `ws2_32 userenv advapi32 bcrypt ntdll synchronization` |
| CRT | its own, isolated | shares Unreal's |
| Ships as | a file next to the exe | nothing extra |
| Hot reload | **yes** (§6) | no — needs a full relink and editor restart |

**Use the cdylib.** The extra 212 KB buys CRT isolation and same-session iteration. The
staticlib is the right answer only for a shipping build where one fewer file matters, and
even then the win is small. The system-library list above was found empirically; it will
grow if the sim gains dependencies, and that maintenance cost is a second reason to prefer
the DLL.

---

## 3. How thin is the C++, really

Counting everything in `unreal/BlindsideFfi/Source`, raw lines including comments and
blanks, and again excluding both:

| Group | Files | Raw | Code |
|---|---|---:|---:|
| **A. Linking the Rust in** | `BlindsideSim.Build.cs`, `BlindsideRust.h/.cpp` | **236** | **148** |
| B. The demonstration actor | `BlindsideSimActor.h/.cpp` | 400 | 276 |
| C. Unreal project boilerplate | 2 × `.Target.cs`, `.Build.cs`, module `.h/.cpp` | 98 | 76 |
| | **total** | **734** | **500** |

**Group A is the answer to the question, and it is 148 lines of code.** That is: a 31-line
`.Build.cs` that adds an include path, a preprocessor define and a runtime dependency; a
15-entry X-macro listing the exports; and a `Load`/`Unload` pair that copies the DLL,
`GetProcAddress`es the fifteen names and does the version handshake. Adding a function to
the boundary is **one line** in the X-macro — the declaration, the pointer, the bind and the
"missing export" error are all generated from that list.

Of those 148, roughly **40 exist only to get hot reload** (the copy-to-a-fresh-name dance
and the explicit `GetProcAddress` table). Import the `.dll.lib` instead and the C++ shrinks
to *an include path and a `PublicAdditionalLibraries` line* — call sites are then identical
to calling any C function. So the honest range is:

- **~40 lines** if you accept restarting the editor to pick up a Rust change;
- **~148 lines** for the version that does not.

Group B is not part of the answer. It is a demo: a fixed-timestep accumulator, a screen
readout, per-call timing, a DLL-timestamp watcher, a command-line switch to fire the panic.
A real renderer replaces it entirely with something much larger, and none of that size is
attributable to the boundary.

Group C is what any Unreal C++ project has.

---

## 4. What the belief snapshot costs

`cargo run -p blindside-ffi --release --bin bench-snapshot`. The point counts are the
project's own numbers, not round ones: `BELIEF-CATALOGUE.md` §1.2 and
`spikes/godot/cloud/LIDAR.md` §6.

Budgets: a 20 Hz sim tick is **50 ms**; a 60 Hz render frame is **16.6 ms**.

```
per-call, independent of snapshot size:
  bs_sim_step(1)          223.5 ns    Phase 0 sim tick, 1-point stage
  bs_sim_state_hash       195.6 ns    BLAKE3 over the Phase 0 state
  bs_sim_tick               0.9 ns    a trivial call

   points        bytes  step+fill ns       copy ns  copy GB/s     % 50ms   % 16.6ms
       76         1288         415.4          13.8      93.25     0.000%     0.000%
     8192       131144       20988.7        2694.1      48.68     0.005%     0.016%
    11500       184072       32319.9        3367.7      54.66     0.007%     0.020%
    23000       368072       61110.4        6697.7      54.95     0.013%     0.040%
    65536      1048648      174177.4       38140.8      27.49     0.076%     0.229%
   500000      8000072     1318080.6      339278.3      23.58     0.679%     2.036%
  1530334     24485416     4152410.7     1447286.0      16.92     2.895%     8.684%
  4194303     67108920    11394366.2     4229289.2      15.87     8.459%    25.376%
```

What the rows are:

- **11,500** — one 20 Hz tick of returns from a real scanning sensor at
  `DESIGN-PRINCIPLES.md` §8's parameters. **3.4 µs. Free.**
- **23,000** — one full 10 Hz revolution, "what the machine sees now". 6.7 µs. Free.
- **500,000** — the accumulated map after a 40 m drive, voxel-downsampled at 30 mm.
  339 µs: 0.68 % of a sim tick, **2.0 % of a 60 Hz frame**. Affordable, not free.
- **1,530,334** — the same walk *not* downsampled, which is what the Godot cloud spike
  actually drew. 1.45 ms, **8.7 % of a 60 Hz frame**. That is a real cost.

**Measured in-engine, not in a loop** (`logs/run-proof-blindside.log`, 11,500 points,
184,072 bytes, steady state over 2,000+ ticks):

```
step 46.8–58.4 µs   belief copy 9.4–12.3 µs   hash+hex 7.3–13.3 µs
```

(Later lines in that log read 104 µs / 22 µs / 30 µs. That is not drift: I was running
cargo builds on the same eight cores at the time. The quieter numbers above are the ones
to quote, and the noisy ones are a useful reminder that the sim shares a machine with the
renderer.)

The in-engine copy is **~9.5 µs against the bench's 3.4 µs**, about 2.7× — because the
bench hammers one buffer in a tight loop and it stays in L2, while Unreal touches it once
every 50 ms and it is cold. **The in-engine number is the honest one.** Even so: 9.5 µs is
0.02 % of a 20 Hz tick. The boundary copy is not a cost worth designing around at these
sizes.

### 4.1 Three findings from these numbers that outlive the spike

**(a) The full-cloud snapshot does not scale, and the API shape should change before it
matters.** At 500 k points it is 2 % of a frame; at 1.5 M it is 8.7 %, every frame, to
re-send data that is 99.99 % identical to last frame's. `bs_sim_belief_snapshot` as
specified copies everything. Phase 3 will want a cursor —
`bs_sim_belief_since(sim, agent, since_tick, buf, cap, &written)` returning only returns
accumulated since a tick — with the full snapshot kept for the first frame and for
resyncs. I have **not** built that: the brief asked for a snapshot into a caller buffer,
and CLAUDE.md says ask rather than invent. Flagging it, with the numbers that say why.

**(b) The *staging* cost is the one to watch, not the copy.** `step+fill` at 11,500 points
is 32 µs. `BELIEF-CATALOGUE.md` §1.2 puts the *entire* per-tick budget at 62.5 µs
single-threaded for the whole match, ~13 µs per agent. The stand-in's per-point splitmix is
not what Phase 3 will do — but it demonstrates that **any per-point work done to build the
snapshot each tick blows the budget**, while the memcpy of the result does not. The belief
buffer must be maintained incrementally by whatever writes returns into it, never rebuilt
per tick. Same conclusion as (a), from the other side.

**(c) Do not format the hash every frame.** `hash+hex` measures 7–13 µs in-engine, but
`bs_sim_state_hash` itself is 196 ns. Essentially all of it is 32 × `FString::Printf` on
the Unreal side. A debug readout should cache the string and refresh it on a cadence. Not a
boundary cost at all — but it is the sort of thing that gets blamed on the boundary.

---

## 5. Does the invariant survive the boundary

Yes, and more strongly than in a pure-Rust client, because the boundary is *enumerable*.

### 5.1 The proof is an absence, and it is enforced upstream

`blindside_sim::World` is `pub(crate)`. `blindside-ffi` is a different crate, so it cannot
*name* the type — not for debugging, not for a "just this once" accessor — and therefore no
function in it can return one. That is not a lint someone can `#[allow]`; widening it means
editing `blindside-sim`'s module privacy, in a different crate, in a separate commit, in
front of whoever reviews that crate.

What the C ABI adds is that the result is **readable in one file**. Here is the DLL's
complete export table (`dumpbin /exports`):

```
bs_abi_version           bs_sim_belief_bytes      bs_sim_spike_force_panic
bs_belief_header_size    bs_sim_belief_snapshot   bs_sim_state_hash
bs_belief_point_size     bs_sim_create            bs_sim_step
bs_belief_schema         bs_sim_destroy           bs_sim_tick
bs_sim_agent_count       bs_sim_seed              bs_status_message
```

Fifteen symbols. That is the entire attack surface a renderer has against the simulation,
for the life of the project. A reviewer can audit it in a minute. A Rust-linked client has
the same guarantee, but you cannot *see* it without reading a crate.

(Two entries alias to `_get_startup_argv_mode` in the raw dump; that is the linker folding
two identical `return <const>` functions. Both are separately callable and
`bs_abi_version()`/`bs_belief_schema()` return 1 each, as the C++ smoke test checks.)

### 5.2 It is also checked mechanically

`crates/blindside-ffi/tests/` (all passing):

- `the_header_exports_exactly_the_reviewed_list` — the header exports exactly fifteen named
  functions. Adding one fails the test, which is the moment to ask whether it can carry
  ground truth.
- `the_header_never_names_ground_truth` — no declaration in the generated header contains
  `world`, `truth`, `cave`, `acoustic`, `ancient`, `deposit`, `wreck`, `diagnostics`,
  `dump`. Deliberately crude: it is guarding against `bs_sim_world_agent_positions` being
  added at 2am, and a crude check catches that where a clever one gets argued with.
- `nothing_that_crosses_is_a_float` — no `float`/`double` in any declaration.
- `the_checked_in_header_is_current` — the committed header is what cbindgen produces now.
  A checked-in generated file that has drifted from its generator is worse than none.
- `no_diagnostics.rs` — `blindside-ffi` does not enable the sim's `diagnostics` feature,
  which is the sanctioned tooling window onto ground truth and which the sim's own docs say
  no client crate may turn on. The test asserts on the *manifest*, because that is where the
  mistake would be made. (Cargo features are not a privacy boundary — the real gate is
  BLD-29's `-p <crate>` rule, which is unchanged by any of this.)

### 5.3 The simulation is unchanged by crossing

Same seed `0xB11D51DE`, same hashes, out of four different binaries:

| tick | hash | seen in |
|---|---|---|
| 1 | `b42af811…17995a31` | C++ exe (DLL), C++ exe (staticlib), **Unreal** |
| 101 | `31bf7017…df267f85` | C++ exe ×2, **Unreal** |
| 2071 | `27c5edac…101ab571` | C++ exe ×2, **Unreal**, *after two hot reloads and a caught panic* |
| 2171 | `5c0e594f…d82cb8fa` | C++ exe ×2, **Unreal**, likewise |

The tick-2071 row is the interesting one. That Unreal instance had reloaded the Rust DLL
twice mid-run and survived a deliberate panic, and it still lands on the byte the reference
implementation says. The boundary does not perturb the sim, hot reload reproduces state
exactly, and a caught panic leaves the sim intact.

`tests/the_c_api_is_deterministic_for_a_seed` runs the same check through the C API on the
*snapshot bytes*, not just the hash, for 200 ticks — if the FFI ever grew state of its own,
that is what would catch it.

---

## 6. Hot reload and iteration

**Yes, without restarting the editor.** Two mechanisms, both in `BlindsideRust.cpp`:

1. **Load a copy.** Windows locks a loaded DLL, so an imported one cannot be rebuilt while
   the editor runs. `Load()` copies `blindside_ffi.dll` to
   `Intermediate/BlindsideRust/blindside_ffi_<pid>_<n>.dll` and loads *that*, leaving the
   original permanently writable. `cargo build` mid-session simply works.
2. **Watch the timestamp.** The actor stats the DLL twice a second
   (`bAutoReloadOnRebuild`, default on) and reloads on change. There is also a
   `CallInEditor` button.

The sim's state lives inside the DLL being replaced, so it cannot survive the swap — and it
does not need to. **Because the sim is deterministic, reload is: destroy, re-create from
the seed, re-step to the tick you were on.** That is the payoff of DETERMINISM.md showing up
somewhere nobody wrote it down as a benefit.

Measured (`logs/run-proof-blindside.log`):

```
hot reload #1: new blindside_ffi.dll, replayed  870 ticks in 32 ms
hot reload #2: new blindside_ffi.dll, replayed 2620 ticks in 47 ms
```

`shots/02-hot-reload.png` is the editor showing `3 agents` at tick 1098, from a
`BS_STANDIN_AGENT_COUNT` that was `2` when the process started. The Rust was edited and
rebuilt while that window was on screen.

**Caveats, stated rather than discovered later.** Most of the 32–47 ms above is the DLL
copy and `LoadLibrary`, not the replay: `bs_sim_step(sim, N)` steps N times and restages
the belief once, so 2,620 ticks of the empty sim is about 0.6 ms. But replay is O(ticks)
and the sim is empty. At 20 Hz a full 8-minute match is 9,600 ticks; when a real sim makes
that slow, the answer is a snapshot/restore pair across the boundary, not a faster replay. Also, the timestamp poll can catch cargo mid-write; the load
then fails, does *not* record the timestamp, and retries on the next poll (a one-line
decision in `OpenSim`, and the reason `DllPath` is kept outside `FBlindsideRust`). A
production integration would debounce properly.

**Iteration loop, measured:** edit Rust → `cargo build -p blindside-ffi --release`
(1.8–8.2 s) → the running editor picks it up within 0.5 s. Editing the C++ still costs a
UBT build (3–10 s) and an editor restart, exactly as it always does — but that is the
smaller half of the work, which is the point.

---

## 7. Debugging across the boundary

**Partly demonstrated. Read the caveat.**

What is verified:

- The release DLL carries a standard MSVC PDB. `dumpbin /headers` shows
  `Format: RSDS, {707EE8C3-…}, 1, blindside_ffi.pdb`, and the 1.4 MB PDB is next to the
  DLL. `rustc` on `-msvc` emits real PDBs, not DWARF, which is why this works at all —
  the whole question would be different on a `-gnu` target.
- The workspace release profile carries `debug = 1` (inherited from the main workspace
  root, where it is there for the canary), so line tables survive optimisation.
- Symbolication across the boundary works in practice: a panic raised inside the DLL and
  called from a plain C++ executable reports
  `panicked at crates\blindside-ffi\src\lib.rs:616:14`. Rust file-and-line resolves from a
  foreign host process.

**What I could not demonstrate: an actual Visual Studio break-in-Rust session. There is no
Visual Studio IDE on this machine** — only VS 2022 *Build Tools* — and no WinDbg. So the
claim "you can attach VS to UnrealEditor.exe and set a breakpoint in `bs_sim_step`" is an
inference from the PDB being present and well-formed, not something I watched happen. It is
the standard behaviour of MSVC-target Rust and I would expect it to work first try, but it
is a fifteen-minute check somebody should do on a machine with the IDE before this decision
is final, and I am not going to report it as proven.

The related thing that *is* proven and matters more day to day: a bug in the Rust does not
take the editor down. `bs_sim_spike_force_panic` returns `BS_STATUS_PANIC` (−6), the message
"panic caught at the FFI boundary; destroy this sim" appears on screen, and the sim keeps
ticking correctly afterwards (§5.3, tick 2071). `shots/03-panic-caught.png`.

---

## 8. What breaks on other platforms

The project has three-OS CI today. Here is the bill, honestly split.

**The Rust costs nothing.** `blindside-ffi` is portable Rust with a `crate-type` of
`["cdylib", "staticlib", "rlib"]`; cargo produces `.so` on Linux and `.dylib` on macOS with
no source change. cbindgen is platform-independent. Adding `blindside-ffi` to the existing
three-OS matrix is one more workspace member and would keep the header-audit and
determinism tests running everywhere. **Do that regardless of the engine decision** — it is
free and it is where the invariant tests live.

**The `.Build.cs` needs per-platform branches**, which is ordinary Unreal work but is not
zero:

| | Windows | Linux | macOS |
|---|---|---|---|
| Artefact | `blindside_ffi.dll` + `.dll.lib` | `libblindside_ffi.so` | `libblindside_ffi.dylib` |
| Runtime lookup | beside the exe | `$ORIGIN` RPATH | `@rpath` + `install_name_tool` |
| Debug info | PDB, works with MSVC debuggers | DWARF, gdb/lldb | dSYM, needs `dsymutil` |
| Signing | none | none | **the dylib must be signed and hardened-runtime-notarised with the app** |
| Hot reload trick | copy-then-load (files are locked) | not needed (`dlopen` on a replaced inode) | not needed |

The spike's `BlindsideSim.Build.cs` throws a `BuildException` on anything but Win64 rather
than pretend. Making it tri-platform is perhaps half a day; **macOS notarisation of a
second binary is the only item that can turn into a week**, and it lands on whoever does
the first Mac release either way.

**The expensive thing is not the boundary, it is Unreal in CI.** The three-OS matrix today
builds Rust. Building an Unreal *project* in CI needs an engine install (~100 GB), an Epic
account on the runner, and 20–40 minutes a build — for a launcher install it is not
something you casually add to GitHub-hosted runners. Godot is a 100 MB download and runs
headless on a stock runner. **This is the single largest concrete cost of choosing Unreal,
and it is not about Rust at all.** The mitigation is real, though: because the boundary is a
C ABI and the sim never sees the engine, *everything determinism-critical is testable
without the engine.* `cpptest/` is that argument in 100 lines — the full ABI exercised,
both link modes, reference hashes compared, on any runner with a C++ compiler. The engine
build can stay a manual or self-hosted step.

---

## 9. Running it

```powershell
.\build.ps1
& "C:\Program Files\Epic Games\UE_5.6\Engine\Binaries\Win64\UnrealEditor.exe" `
  unreal\BlindsideFfi\BlindsideFfi.uproject -game -windowed -ResX=1400 -ResY=800 -ForceRes
```

There is **no `.umap` in the repository.** The project uses the stock
`/Engine/Maps/Templates/Template_Default` and the game module spawns an
`ABlindsideSimActor` into any game world on `FWorldDelegates::OnWorldInitializedActors`. A
designer who drags one into a level gets that one instead. This keeps the spike free of
binary assets a reviewer would have to take on trust.

Switches the actor understands: `-ForcePanicAtTick=N` fires the caught-panic demonstration.
Properties on the actor: `Seed`, `BeliefPoints`, `SimTicksPerSecond` (20),
`MaxCatchUpTicks`, `bAutoReloadOnRebuild`.

### 9.1 The shots

| | |
|---|---|
| `shots/01-running.png` | tick 336 @ 20 Hz, full 64-char state hash, belief 184,072 B / 11,500 pts / 2 agents, `step 53.1us copy 11.0us` |
| `shots/02-hot-reload.png` | `hot reload #1: new blindside_ffi.dll, replayed 870 ticks in 32 ms`, and `3 agents` from a constant edited while it ran |
| `shots/03-panic-caught.png` | `forced panic returned -6 (panic caught at the FFI boundary; destroy this sim) -- still here`, tick 2196, still ticking |

Logs: `logs/build-clean.log` (clean build + tests + bench), `logs/cpptest.log` (both link
modes + reference hashes), `logs/run-proof-blindside.log` (the engine run, filtered to
`LogBlindside`).

### 9.2 Two irritations, so nobody rediscovers them

- **A Windows Firewall dialog appears on every run** and sits over the middle of the
  screen. It is Unreal's trace-control listener (`LogTrace: Control listening on port …`);
  `-notraceserver` and disabling `UdpMessaging` in `DefaultEngine.ini` do not stop it.
  `shot.ps1` sends the dialog `WM_CLOSE` before capturing — which grants nothing and
  changes no firewall rule — and the readout is laid out to sit clear of where the dialog
  lands. Do not "fix" it by clicking Allow.
- **`HighResShot` does not capture `AddOnScreenDebugMessage`.** Hence `shot.ps1` grabbing
  the window off the desktop. A real client would draw into UMG and be screenshot-able
  normally.
- `build.ps1` sets `$ErrorActionPreference = "Continue"`, not `"Stop"`: Windows PowerShell
  turns any native command's stderr into a terminating `NativeCommandError`, and cargo
  writes progress to stderr *on success*. Every step is gated on `$LASTEXITCODE` instead.

---

## 10. Against gdext, honestly

gdext is mature and pleasant, ARCHITECTURE.md already names it, and another agent is
working in `spikes/godot/` right now with real results behind them. Here is what is
genuinely **worse** about the Unreal C-ABI route, without diplomacy:

1. **You lose the type system at the seam.** gdext gives you `#[derive(GodotClass)]`, real
   Rust types, `Gd<T>` smart pointers and a macro that generates the binding. Here you get
   `uint8_t*` and a length. Every struct that crosses is hand-laid-out twice — once in
   Rust, once implicitly in the header — and the only thing standing between you and
   reading a snapshot at the wrong offset is a `sizeof` handshake I had to write by hand.
   cbindgen removes the *drift* risk; it does not give you types.
2. **Everything crossing must be POD.** No `Vec`, no `String`, no `Option`, no enum with
   data. `Belief` will grow variable-length parts — contact tracks, known beacons, an
   inventory — and each becomes a manual offset-table serialisation into the byte buffer.
   gdext hands you a `PackedVector3Array` and is done. **This is the real ongoing tax, and
   it grows with the game rather than being paid once.**
3. **No Blueprint/GDScript reflection for free.** gdext exposes Rust methods to GDScript
   automatically. Here, every Rust function a designer should be able to call from
   Blueprint needs a `UFUNCTION` wrapper written by hand. For a *behaviour-authoring* game
   — where the editor UI is much of the product — that is a lot of wrappers.
4. **CI, as in §8.** Godot: 100 MB, headless, stock runner. Unreal: ~100 GB, an Epic
   account, tens of minutes. This is the biggest concrete cost on the list.
5. **Iteration on the C++ half is slower.** Rust hot reloads (§6). But every `UFUNCTION`
   or `UPROPERTY` you add is UHT plus a UBT build plus an editor restart. GDScript is
   instant. Given the client is "GDScript for UI and glue — do not write the whole client
   in Rust, it costs the iteration speed that is the reason to use Godot"
   (ARCHITECTURE.md), Unreal's answer to that sentence is Blueprint, and Blueprint is
   worse than GDScript for the specific job of building a node-graph behaviour editor —
   it *is* a node-graph editor, which is either a gift or a trap and I do not know which.
6. **Two build systems that must be told about each other.** `build.ps1` exists because
   cargo and UBT do not know each other. gdext is one `cargo build` and a `.gdextension`
   text file. Small, but it is a permanent seam and it is where the "works on my machine"
   failures will live.
7. **Engine-version fragility, demonstrated in §2.1.** A banned MSVC range stopped 5.8
   dead. Godot has no equivalent — it ships its own toolchain expectations and gdext pins
   against a GDExtension API version that changes rarely.

And what is genuinely **better**:

1. **The C ABI is engine-agnostic in a way gdext is not.** gdext binds you to Godot's
   extension API. This header binds you to nothing: the same DLL is already driving a plain
   C++ console executable in `cpptest/`, and would drive Godot (via GDExtension calling the
   same C functions), a Python tool, a headless server, or — the stated long-term goal —
   **a hardware backend.** CLAUDE.md says the behaviour layer is meant to run on real
   hardware and that sensor/actuator interfaces should not foreclose it. A C ABI is the
   most literal possible non-foreclosure. gdext would have to be paralleled by exactly this
   header anyway.
2. **The invariant is auditable as a list**, §5.1. Fifteen symbols. This is a stronger
   review artefact than "trust the crate boundary".
3. **CRT and allocator isolation is total.** No `/MD` argument, no shared allocator, no
   exception-model negotiation. It just works, first try, which surprised me.
4. **Hot reload of the simulation**, which gdext also has, but here it composes with
   determinism into something quite nice: replay-to-tick reload, exact.
5. Unreal's renderer, if the sparse point cloud at 1.5 M points ever needs it. The Godot
   spike already draws that in one call, so this is not currently a differentiator.

**My recommendation.** Adopt the **C ABI**; do not adopt **Unreal** on this evidence.

Those are two decisions and the spike only settles one. The C ABI is worth building
*whatever engine you use*: it costs ~150 lines of glue per engine, it makes the invariant
auditable, it decouples the sim from the client's build entirely, and it is the shape a
hardware backend needs. If you keep Godot, put this header behind gdext or call it directly
from a GDExtension — you lose nothing and you gain the audit and the isolation. If you move
to Unreal, the boundary is not what will hurt; the CI weight, the hand-written `UFUNCTION`
wrappers and the POD-only marshalling of a growing `Belief` are, and none of those is
visible in a two-day spike. The thing that would change my mind toward Unreal is a
demonstration that the behaviour-authoring UI is dramatically better in Blueprint than in
GDScript, and that is a different spike.

---

## 11. Everything I guessed

Tagged `GUESS` or `STAND-IN` in the source too. In rough order of how much a wrong answer
would cost.

1. **The belief snapshot layout.** `BsBeliefHeader`'s fields — pose, `pose_var`,
   `ticks_since_fix` — are read off ARCHITECTURE.md's `Belief` struct and Phase 1's
   findings, not specified anywhere. `Belief.map: OccupancyMap` is explicitly unsettled
   (`DEV-PLAN.md` says it "cannot do this as written"), so the snapshot carries a point
   cloud instead of a map. **This will change. `BS_BELIEF_SCHEMA` exists because of that.**
2. **The snapshot's *contents* are derived, not real** (§1.1). Volume is realistic;
   positions are meaningless.
3. **Point coordinates are Fx16.16, not I32F32.** My choice, to halve the copy. Nobody
   specified display precision. Reversible; doubles the numbers in §4.
4. **`BS_DEFAULT_BELIEF_POINTS = 8192`** — invented before I found the real numbers. The
   actor now defaults to 11,500 (one 20 Hz tick of returns, from the docs). Neither is a
   decision; §4.1(a) says the ceiling is a designer question.
5. **`BS_STANDIN_AGENT_COUNT = 2`** — the Phase 0 sim has two agents in `world.rs`, but
   that is `pub(crate)` so the FFI genuinely cannot ask. Phase 3 needs a real public
   accessor. This is the invariant working correctly and being inconvenient, which is what
   correct looks like.
6. **`MatchRecord` construction.** `MatchRecord::seed_only` is `#[cfg(test)] pub(crate)`,
   so `bs_sim_create` builds a record literal with `content_hash: [0; 32]` and empty
   loadouts/policies/commands. A real client loads a record and validates it first. If the
   sim ever gains a public "record from seed" constructor, this should use it.
7. **20 Hz** for `SimTicksPerSecond`, from `PHASE-3-OPEN-QUESTIONS.md` §19 via
   `DEV-PLAN.md`. Read from the docs, not invented, but `DEV-PLAN.md` lists tick rate among
   the things Phase 3 must not guess at, so flagging it.
8. **`MaxCatchUpTicks = 8`** and the "give up if more than 4 periods behind" rule. Pure
   invention; a real client needs a policy for a client that cannot keep up, and that
   policy is a networking decision.
9. **`bs_sim_step` takes a tick count** rather than being called N times. Cheaper for
   catch-up and for the reload replay; no document asks for either shape.
10. **Status codes and their numbering.** Invented. The `< 0 is failure` convention is the
    part worth keeping.
11. **The staticlib's system-library list** (`ws2_32 userenv advapi32 bcrypt ntdll
    synchronization`) was found by fixing link errors until it linked. It is not derived
    from anything and will drift.
12. **`bs_sim_spike_force_panic` is spike-only** and must be deleted from `lib.rs` and from
    `tests/header_surface.rs`'s expected list together.
13. **UE 5.6 over 5.8**, forced by §2.1's MSVC ban, not chosen.
14. The generated header is **checked in**. Arguable — it is a build artefact — but a
    reviewer can then read the entire boundary without building anything, and
    `the_checked_in_header_is_current` stops it going stale.
