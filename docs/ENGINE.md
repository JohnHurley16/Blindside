# The engine decision

2026-09-10. Live, and being settled by measurement rather than argument. This file is the record.

---

## 1. The decision, as it stands

**Unreal Engine 5.8, and nothing older.** The designer, this morning:

> "everything from now on should be done in 5.8. anything that isnt using the features in 5.8 is
> wrong."

Read strictly, and it is meant strictly: a result that could have been produced in 5.6 has not
answered the question. If a newer capability exists and applies, use it; if it does not apply, say
why.

## 2. How it got here

- The designer spent two days rejecting Godot renders of snowy mountains and an ice cave, and
  asked whether Unreal would make photoreal environments easier. It almost certainly would: the
  scanned asset library and virtualised geometry are built for exactly this, and this project has
  been hand-writing what they give away.
- `DESIGN-PRINCIPLES.md` §11 then decided that **a cave persists for weeks and evolves with a
  season** rather than being generated per match. That is what makes the move sensible. A place
  that stands for weeks can carry authored and scanned art; a per-match roll cannot.
- The architecture already anticipated a swap. The simulation is Rust and the client is a thin
  renderer that may only ever see Belief, so the renderer is the cheapest thing in this design to
  replace.

## 3. What is settled

**The Rust boundary works and is worth having whatever engine wins.** `spikes/unreal/ffi/`
(2026-09-10):

- Unreal displaying a tick count and a state hash out of `blindside-sim`, at a fixed 20 Hz step,
  copying a belief snapshot every tick. It survived hot reload and a deliberate panic in the Rust.
- **148 lines of C++**, about 40 of which exist only to buy hot reload.
- **The invariant is enforced by the shape of the interface.** The library exports fifteen symbols
  and `World` is crate-private, so the interface crate cannot name it and no function can return
  it. That is stronger than the AST lints the Python phases use.
- No special Rust target, CRT flag or linker setting: a cdylib carries its own runtime.
- **The cost finding that outlives the engine question:** a belief snapshot is 9.5 µs at one tick
  of returns and free, 339 µs at 500 k points, and 1.45 ms at 1.5 M — nearly 9% of a frame. So a
  full-cloud copy per frame does not scale. Phase 3 needs a cursor, and the belief buffer must be
  maintained incrementally rather than rebuilt. Unbuilt, and it applies to Godot equally.

## 4. What is not settled

**Whether the pictures are better.** That is the whole reason the question was asked and it is
being tested now: the valley and the ice cave rebuilt in 5.8, framed against the Godot frames so
the comparison is direct. Until those exist this is an opinion.

## 5. The toolchain blocker, and it needs the designer

**Unreal 5.8 will not compile C++ on this machine.** Its own config
(`Engine/Config/Windows/Windows_SDK.json`) bans these MSVC toolsets, with reasons:

| Banned | Why, per Epic |
|---|---|
| 14.39.x | Internal compiler errors; codegen bug crashing at runtime with AVX |
| 14.40.0 – 14.43.99999 | Codegen bug crashing at runtime with AVX; PGO bug crashing at runtime |
| 14.44.0 – 14.44.35210 | Superseded |
| 14.50.0 – 14.50.35722 | Superseded |

Minimum 14.38.33130; preferred 14.44.35207+ (VS 2022 17.14) or 14.50.35717+ (VS 2026).

**This machine has exactly one C++ toolset: 14.43.34808**, in Build Tools 2022 at 17.13, which is
inside the banned range. Build Tools 2019 carries 14.29.30133, below the minimum.

**It could not be installed from here.** `vs_installer update --quiet` returns 5007, which is its
elevation-required result, and the session is not elevated. It needs an administrator:

```
"C:\Program Files (x86)\Microsoft Visual Studio\Installer\vs_installer.exe" update \
  --installPath "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools" --quiet --norestart
```

or the Visual Studio Installer's Update button on Build Tools 2022. A few gigabytes.

**What is blocked and what is not.** Content work in 5.8 — Landscape, Nanite, Lumen, materials,
volumetrics, scanned assets — needs no C++ compile and runs today. **Anything with the Rust
boundary in it does not**, so the boundary spike ran on 5.6 and has to be redone on 5.8 once the
toolset lands. That is the single thing gating the decision from becoming the plan.

## 6. What a migration would actually cost

**Ports cleanly:** the topology generator (integer logic, engine-independent), the machines
(already glTF out of Blender), the score (Python, renders a WAV), every design finding, and the
whole simulation, which never knew what engine was drawing.

**Rebuilt:** shaders, the camera rig and post stack, the point cloud renderer, the snow track
buffers, the valley and cave dressing. Roughly two days of the work done here.

**Genuinely worse in Unreal**, from the boundary spike rather than from opinion: the type system
is lost at the seam, so every variable-length part of `Belief` becomes manual marshalling and
that tax grows with the game; no free reflection into the editor's scripting; two build systems
that must be told about each other; and CI is about 100 GB and an Epic account against a 100 MB
headless runner. That last one is the largest concrete cost and has nothing to do with Rust.

**Unknown until the look test lands:** whether the point cloud, which is one draw call for 1.5 M
points in Godot, is as cheap. The belief view is not optional and it is the game's signature.

## 7. Open

1. The toolset install (designer, elevated).
2. Whether the 5.8 renders beat the Godot ones (testing now).
3. Whether the belief point cloud is affordable in Unreal.
4. Whether behaviour authoring is better in Blueprint than GDScript — a separate spike, and the
   boundary spike named it as the thing that would change its own recommendation.
