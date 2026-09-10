# Handoff — 2026-09-10, 11:40

Written because the machine is about to restart and the session that did this work will not
survive it. **Read this first, then `docs/DESIGN-PRINCIPLES.md`, then `docs/ENGINE.md`.**

Branch `claude/game-phase-1-setup-p9g1bb`, HEAD `8267b96`, everything pushed. 56 commits in the
last day. Each one's message explains what changed and why — the messages are the real record and
are worth reading in preference to any summary, including this one.

---

## 1. The one thing to do first

**Check whether the compiler toolset landed.** After the restart:

```
dir "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Tools\MSVC"
```

You want a folder **14.44 or higher**. Before the restart there was only `14.43.34808`, which
Unreal 5.8 bans (its config bans 14.40–14.43 for a codegen bug that crashes at runtime with AVX).
The installer ran, exited 0, staged 14.44.35211 packages, and left three pending-reboot flags, so
the files should appear once Windows finishes.

- **If 14.44+ is there:** Unreal 5.8 can build C++, and the Rust boundary work can be redone on
  5.8 (see §4).
- **If it is not:** the install did not complete. Re-run, elevated:
  `vs_installer.exe modify --installPath "...\2022\BuildTools" --add Microsoft.VisualStudio.Component.VC.14.44.17.14.x86.x64 --quiet --norestart`

## 2. Where the project actually is

**This is a game about teaching autonomous machines to work where you cannot control them.** The
one invariant, in `CLAUDE.md`: a policy may never observe ground truth. That has held all session
and it is the thing to protect.

**Phase status is unchanged and is not what the last two days were about.** Phase 1's gate failed
on 2026-09-06 and is diagnosed. Phase 2 is built and has never been run with a human. Phase 0's
harness is green on three operating systems on branch `claude/harness-plus-induct` and is one
merge from landing. **The single highest-value unblocked thing in the whole project is still a
twenty-minute corridor teaching session with a non-engineer** (`docs/phase2-playtests/PROTOCOL.md`).
It needs no build and no decision. Everything else assumes its answer.

**The last two days were world, art and trailer work**, driven by the designer in real time.

## 3. The decisions made in this session, in order of importance

All are in `docs/DESIGN-PRINCIPLES.md`, dated, in the designer's own words. The recent ones:

| | |
|---|---|
| §10 | **The world is coming out of an ice age.** A recovering society in a snowy valley under mountains, discovering the pre-ice-age civilisation whose machinery is in the caves. Reframed everything; reconciled in `docs/THE-ICE.md` (1,550 lines). |
| §11 | **A cave persists for weeks, then evolves with a season.** Not generated per match. This is what makes authored/scanned art viable and is the deciding argument on the engine. It also kills the seed-leak exploit and sharpens the game: the player knows the cave and the machine still does not. |
| §4 | Density is a requirement; the world is two technological registers colliding. |
| §5 | Procedural, in-engine — but **scoped**: that rule is about *generated* content. Machines and machinery are authored assets. I got this wrong once and the designer caught it. |
| §6 | It has to look photoreal. |
| §7 | **Density is order, not scatter.** Random scatter reads as abandonment. |
| §8 | The sensor is simulated for real — a scanning instrument, not decoration. |
| §9 | Belief should be rich, so technique can differ (`docs/BELIEF-CATALOGUE.md`, 100 signals). |

**Also written this session:** `docs/WHAT-HAPPENED-HERE.md` (why the machinery was left running —
it holds a claim), `docs/WHY-THEY-ARE-ALL-DOWN-THERE.md` (why clans share a cave, and why there is
never a weapon), `docs/SOUND-DESIGN.md`, `docs/THE-SENSOR-AND-SLAM.md`, `docs/TRAILER.md`
(rewritten), `docs/ENGINE.md`.

## 4. The live question: Unreal

`docs/ENGINE.md` is the record. **Designer instruction: everything from now on is Unreal 5.8, and
anything not using 5.8's features is wrong.**

- **Settled:** the Rust→C→Unreal boundary works. `spikes/unreal/ffi/` — 148 lines of C++, the
  invariant enforced by the crate boundary (the world type is crate-private so no exported
  function can return it), hot reload works, a Rust panic is survivable. **It ran on 5.6 and must
  be redone on 5.8** to meet the instruction.
- **Not settled:** whether the pictures are better. `spikes/unreal/look/` was mid-flight when the
  restart was called — six frames, a 5.8 migration in progress, and it was asked to write
  `spikes/unreal/look/NOTES.md` before stopping. **Read that file first; if it is missing, the
  agent did not get to checkpoint and its two hours are lost.**
- **Open and important:** whether the belief point cloud (1.5 M points, one draw call in Godot) is
  affordable in Unreal. It is the game's signature view.
- **The designer's idea, worth pursuing:** use Unreal's ray tracing to generate point-cloud data.
  Correct for anything visual. **Cannot drive gameplay** — GPU tracing is not deterministic across
  machines and the sim must be. The strong version is to **bake offline against the persistent
  cave and have the Rust sim query the result with integer arithmetic**.

## 5. What exists on disk that is worth not rebuilding

**Godot spikes** (`spikes/godot/`) — likely superseded by the engine move, but their *findings*
are engine-independent and several are load-bearing:
- `cave/` — vertical cave, four levels, nine pitches, an ice shader rebuilt as a dielectric.
  `ICE-CAVE.md` and `VERTICAL.md` are the good documents.
- `surface/` — the valley, a town on contour terraces, snow that records the machine's own tracks.
  `VALLEY.md`, `ORDER.md`, `ACT-ONE.md`.
- `cloud/` — the belief view as a real scanning lidar, and the map reveal. `LIDAR.md`, `MAP.md`.
- `machines/` — the four chassis exported from Blender via the new `agent_model/export_gltf.py`,
  with continuity enforced by the shot validator.
- `assayer/` — the ancient machine, fully animated through its 75-second cycle.

**The trailer** — `docs/TRAILER.md` was rewritten to the designer's structure: one continuous
journey, no text cards, ending on the Assayer and then the cave drawn from the machine's own
returns. `spikes/godot/_assemble_cut.py` cuts it in one command. The last delivered cut was 1:11.
**The designer's standing criticism is that the mountains still do not look like mountains** (said
three times) and that the above-ground looks bad. That is why the engine question was raised.

**Audio** — `spikes/score/valley-score.wav` (regenerate with `python -m phase1.audio.score_render`)
and a snow set. `spikes/score/NOTES2.md`.

## 6. Uncommitted right now

37 paths, all in `spikes/godot/surface/` — a Godot mountains pass that was **deliberately killed**
mid-flight when the engine decision was made, plus its perf files. Nothing depends on it. It is
either worth committing as a record or discarding; it was stopped because it was the most
engine-specific work in flight.

## 7. Waiting on the designer, and none of it is blocked on code

1. **The corridor teaching session** — twenty minutes, no build. The most valuable thing available.
2. **The cave tuning decision (P2X-11)** — four options measured in `docs/CAVE-WINNABLE.md`; option
   A reaches 16 of 20 at a teachable threshold and costs the 2:20 betrayal beat.
3. **The rock albedo**, which two independent measurements found is 3–4× too bright in
   `ART-DIRECTION.md` §3.1 and which one spike named as the direct cause of the "peach plastic"
   look. Two passes now disagree by 4.4× about what a mine floor is.
4. **The ratchet count** — the code plays 31 notches where five documents promise nine.
5. Question rounds nobody has answered: `PROCEDURAL-AND-GODOT.md` §8 (14 open),
   `SOUND-DESIGN.md` (17), `WHAT-HAPPENED-HERE.md` (13), `THE-ICE.md` (24), `HARNESS.md`,
   `PHASE-3-OPEN-QUESTIONS.md` (52).

## 8. How to work with this designer, learned the hard way

- **They are right when they push back.** Every rejection this session was correct, and twice the
  root cause was a single wrong constant rather than missing effort.
- **Verify before reporting a number.** I told them a four-hour stall was fifteen minutes because
  I estimated instead of reading the log. Check `git log --date=format:%H:%M:%S`.
- **Do not stop and wait.** When a wave of work lands, launch the next before writing anything.
- **Show, do not describe.** Renders, videos and measurements land; summaries do not.
- **Say what is missing.** Every document here ends with its guesses listed. Keep that.
