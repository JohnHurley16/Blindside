# Vision board — the teaching space, and mood

Group G (teach-surface, teach-interface, teach-commit, teach-cave, teach-forensics) and group H
(palette strips, light sources) from the board inventory, plus five frames the inventory did not
list (G0: the place as a whole and the loop as a storyboard). Rendered 2026-09-08 in two passes:
the first pass built the scene and rendered most of the frames; the second re-rendered the nine
frames that came out black or occluded (marked **re-rendered** below, with what changed), added
six frames, and made the sheets that are assembled from the renders.

**Everything on the surface is a proposal.** `DESIGN-PRINCIPLES.md` §3 binds four things — there
is a pit-head, it is the only place with sky, machines are kept / prepared / taught / sent down
there, it is safe and lit — and leaves the rest open. Every image below dresses those four facts
with guesses, and each guess is listed at the foot of this file so it can be refused precisely.

Three rigs, so a clear view and an in-situ view of the same thing agree:

- **DAYLIGHT** (surface, clear and in-situ): uniform overcast sky in the shaft's own colour
  `(0.60, 0.74, 1.00)` — so the light on the surface *is* the light that comes down the shaft —
  plus one 14 m soft "cloud break" area, no sun, no shadow edge. Drizzle / dusk / night are the
  same sky at lower strength with wetter materials and a thin haze. `--sky sun` renders one
  comparison frame with a sun (g0_05) for the decision.
- **CLEAR** (product shots): neutral grey world at 1.0, one 3 m key at 45°, a grey floor, a scale
  reference in frame. A catalogue rig; not the game.
- **Cave** frames use the direction's own rig: world 0, the machine's lamp, nothing else. Where a
  cave or night frame is shown lifted (+1.5 to +3 stops) the caption says so: that is board
  exposure so the thing can be seen, never the game's.

Every machine in every frame carries the three fixes `ART-DIRECTION.md` asks for (lamp re-aimed
`Euler((0,-pi/2,0))` and tilted down, lamp white, emissives ≤ 3 in BONE, no cyan) and the three
gravity wear masks from `av_probe.py`. `agent_model/` itself is untouched.

## How to re-render

    bash docs/art/vision/teaching/teaching_batch.sh                    # every Blender frame, shot -> file
    ONLY="g5_ g4_" bash docs/art/vision/teaching/teaching_batch.sh     # a subset by file-name prefix
    blender -b -P docs/art/vision/teaching/teaching_probe.py -- --shot <shot> --out <ABS>.png --samples 40 --res 960x600
    .venv/Scripts/python.exe docs/art/vision/teaching/teaching_sheets.py --stage pre --snaps <dir with the phase1/phase2 snaps>
    .venv/Scripts/python.exe docs/art/vision/teaching/teaching_sheets.py --stage post

`teaching_probe.py` builds the whole pit-head procedurally (terrain, collar, headframe, winding
house, winch and kibble, lean-to, course, person, pendant, terminal, listening post, an optional
yard work light) and holds one block per shot; `teaching_batch.sh` is the shot → file table.
`teaching_sheets.py` makes the screen mocks the probe puts on its screens, the palette and light
sheets, the course plan (`pre`), and the two-panels, storyboard, contact sheet and tone rows that
are cut from the renders (`post`). The screen pictures come from the real software:
`python -m phase2 --snap` (the corridor's teach window), `python -m phase1 --teach --snap`
(the cave's belief-only stop pictures) and `python -m phase1 --snap 143,341,480` (the spectator
display, the 8:00 reveal). `_screens/` holds the versions cut for the screens; `_logs/` the
render log and a JSON of each shot's camera and staged junction.

Measured on this machine (16 threads, Cycles CPU, 960 × 600 / 40 spp, from the `_logs`): product
shots 0.3–2 min, cave frames 2–3 min, **surface frames 3.5–10.5 min** (the seed-104 course is
64 × 62 m of hoarding and posts; two machines; DoF), and longer when other Blender jobs share the
CPU (g1_02 took 29 min with four other Blender jobs running). The first pass's note of "60–80 s"
was wrong by an order of magnitude. The second-pass surface frames were rendered at 24 spp for
that reason (`SAMPLES=24`); daylight scenes converge early and the denoiser covers the rest.

---

## G1 — teach-surface: the act of teaching at the course

The corridor test made physical: `phase2.truth.corridor.Corridor(seed)` (read-only; seed 104,
the first demonstration seed) extruded as 1.2 m corrugated-hoarding walls on timber posts at the
1.2 m module, passages 1.8 m wide, junction squares open, dead ends capped, the root a pale post
with a WARM_DIM pilot (the corridor's "shaft" beacon), the deposit leaf a pale crate with a heap of
broken stock. At 0.6 m/cell the seed-104 course is 64 × 62 m with passages 8–22 m long.

| image | intent | tool |
|---|---|---|
| `g1_01_course-oblique.png` | DAYLIGHT high oblique of the whole course on the spoil flat with the pit-head behind it: the maze a person reads at a glance and a machine at 0.57 m never can. | probe `g1_course_oblique` |
| `g1_02_junction-over-the-shoulder.png` | **The act.** Over the player's shoulder at the first junction: the machine stopped below, head turned to the mouth it believes is there, the wall between them, the pendant in the hands with the belief picture on it, the cable over the wall. Full information above the wall, none below it. | probe `g1_junction_ots` (**re-rendered**: the first pass's Blender was killed mid-render by another job) |
| `g1_03_junction-machine-height.png` | The same junction from the machine's own height (0.45 m): blind walls, two mouths, no person, no course — what the sensors have to work with, as a spectator would see it. | probe `g1_junction_machine_eye` (**re-rendered**, same reason) |
| `g1_04_scale-lineup-clear.png` | CLEAR: person 1.75 m / wall 1.2 m / machine 0.57 m / the 0.60 m rail gauge / a 1.2 m ruler, in one frame — the surface's scale rule. The wall is above the machine's head and below the person's eye; that is the whole design of the course. | probe `g1_scale_lineup` |
| `g1_05_junction-drizzle.png` | In-situ: the same stop in drizzle at the end of the day, from further back and lower, the machine in the junction square, the cable coming over the wall behind it; the person is outside the frame. | probe `g1_junction_drizzle` |
| `g1_06_deadend-turning-back.png` | The machine at the nearest dead end, already turning back, seen from above the wall line down the passage; the player over the wall to the side. `go back` is a thing you watch it do. | probe `g1_deadend` (**re-rendered**: the first camera was outside the wall and the machine was 30 px behind hoarding) |
| `g1_07_course-plan.png` | PIL plan of the seed-104 corridor as built, truth only, with the staged junction, the root and the crate marked — and the passages that cross each other circled in red (design problem 2). | sheets |
| `g1_08_roofed-section.png` | **Proposal** for design problem 3: the first passage roofed and walled to 1.6 m, the machine's lamp on inside. Rendered so the designer can see that a roofed length in daylight is dim, not dark: teaching lamp / silt / ping decisions on the surface needs doors, or it happens only in the cave. | probe `g1_roofed` |
| `g1_09_junction-from-above.png` | The staged junction from straight above, 9.5 m up: the plan the pendant draws, as a photograph — the machine, the way in, the three mouths, the person at the wall, the cable. What g2_02's "ITS MAP" is a belief about. | probe `g1_junction_plan` (new) |
| `g1_10_junction-pendant-in-frame.png` | The act over the other shoulder, steeper: the pendant screen in the hands and the machine below the wall in one frame — the belief picture and the thing it is a belief about. (In g1_02 the pendant is hidden by the shoulder.) | probe `g1_junction_ots_pendant` (new) |

## G2 — teach-interface: the interface's presence in the world

**Proposal (Q2):** a wired **pendant** on a cable for demonstrations at the course and at the
collar — a 220 × 140 mm dark slab, a 2:1 screen showing the belief picture and the stop's
predicates, a row of five pale **block keys** under the screen (the spectator rail's action list
made physical; the screen's bottom edge labels them), a scrub wheel on the right edge, the cable
out of the left edge into the machine's charge port — and a **bench terminal** in the lean-to for
composing trees, reading the sentence and watching replays: a screen on a stand and a rail of nine
block keys with a wheel. **No voice.** The machine's channel is acoustic and a few bytes; a voice
interface would promise a bandwidth the game denies.

| image | intent | tool |
|---|---|---|
| `g2_01_pendant-product-clear.png` | CLEAR product shot of the pendant on a wedge, screen lit, with a beacon (230 × 60 mm, the thing the machine drops) beside it for hand-scale. | probe `g2_pendant_clear` |
| `g2_02_pendant-screen-mock.png` | PIL mock of the pendant's screen: the corridor's belief inset (from `python -m phase2 --snap`), the stop's predicates, the two offered actions in CARGO, the rule so far, and the key legend along the bottom edge. What the player is looking at in g1_02. | sheets |
| `g2_03_terminal-bench-clear.png` | CLEAR: the terminal on the bench with the block-key rail and the pendant lying beside it on its cable — the two objects of the interface in one frame. | probe `g2_terminal_clear` |
| `g2_04_pendant-at-collar.png` | In-situ: the pendant plugged into the machine at the collar, the player crouched beside it, the kibble hanging at the top of the shaft behind — the last check before it goes. | probe `g2_pendant_collar` (**re-rendered** without the course: the first pass had the course's first arm between the camera and the collar and the frame was all hoarding) |
| `g2_05_terminal-dusk.png` | In-situ: the terminal lit in the lean-to at dusk with the replay on it, the player at the bench; the sky nearly gone, the screen the only source that reaches a face. | probe `g2_terminal_dusk` (**re-rendered**: the first pass was a black frame with a screen in it; screen strength 4 → 24, dusk sky 0.035 → 0.07, +1.8 stops) |
| `g2_06_terminal-screen-mock.png` | The terminal's screen: phase2's window after induction (the map of every demonstration, the rule as a tree and as one sentence) with a replay scrubber added along the foot. Real software, resized; the scrubber is the proposal. | sheets |

## G3 — teach-commit: the commit

**Proposal (Q3):** the commit is the pendant cable pulled from the port at the collar. The cable is
the physical difference between the surface (a wire: full authority, full information) and the
cave (a hydrophone and a few bytes: full information, no authority — `GLOSSARY` "Commit").

| image | intent | tool |
|---|---|---|
| `g3_01_cable-in-macro.png` | CLEAR macro: the plug seated in the charge port on the machine's rear face (the port `build.py:236` already models), the cable running away. | probe `g3_cable_in` |
| `g3_02_cable-out-macro.png` | CLEAR macro: the same frame with the plug pulled, the port face open. Control has left. (The hand holding the plug is outside the macro frame.) | probe `g3_cable_out` |
| `g3_03_commit-wide.png` | In-situ, drizzle: the cable coiled on the hardstanding by the collar with the plug lying loose, the kibble gone, the rope running down into black, the player at the listening post with the belief map on its screen. | probe `g3_commit_wide` (**re-rendered** +0.7 stops and a step closer so the coil and the plug on the kerb read) |
| `g3_04_descent-from-collar.png` | Looking down into the collar from nearly overhead: the kibble 1.6 m down on the guides, the machine's pale shell the last pale thing before the timber sets go black. The board's "leaving somewhere" frame. | probe `g3_descent` (**re-rendered**: the first camera was too oblique and the collar frame hid the kibble) |
| `g3_05_listening-post.png` | After the commit: the player at the listening post in drizzle, the belief-only map on its small screen, the cable drum, the hydrophone cable over the collar, the shaft black behind. The surface end of the link (inventory A8), and where the run phase is watched from. | probe `g3_commit_post` (new) |

## G4 — teach-cave: teaching underground

**Proposal (Q4):** the same act through the link. The machine waits at a decision point and the
match clock stops (`CAVE-BLOCKS.md` §9); the pendant — or the post — shows the same belief-only
picture it shows on the course. A training mode, not a match.

| image | intent | tool |
|---|---|---|
| `g4_01_cave-stop-truth.png` | Truth, rendered, at the game's exposure: the machine halted at a narrowing of a natural passage, head down, in its own lamp, mud on its legs; the clock stopped. What the spectator could see and the player is not shown. | probe `g4_cave_stop` |
| `g4_02_stop-two-panel.png` | The same stop twice: the truth render beside the belief-only picture the player actually gets (`python -m phase1 --teach --snap`, stop 2). They never agree in shape. | sheets |
| `g4_03_cave-stop-director.png` | The stop from the director's height: the pool, the machine between the camera and its pool, and black. Shown at +1.5 stops so the passage reads on a board. | probe `g4_cave_stop_above` (**re-rendered** at +1.5: the first pass was a pool and nothing else) |
| `g4_04_cave-stop-exposure-pair.png` | g4_01 beside g4_05: the game's exposure and +3 stops of the same frame, so the board shows what is there and what the game shows of it. | sheets |
| `g4_05_cave-stop-plus3.png` | The SAME frame as g4_01 at +3 stops: the passage, the rubble, the head on the rock, the mud line. The clear view of the in-situ frame; captioned as not the game. | probe `g4_cave_stop_plus3` (new) |

## G5 — teach-forensics: the replay on the bench

| image | intent | tool |
|---|---|---|
| `g5_01_terminal-replay-mock.png` | The replay screen: the spectator display's 8:00 reveal (truth over belief, the tether, the rule it was taught) with the scrubber along the foot. The most polished screen in the game, on the least polished bench. | sheets |
| `g5_02_leanto-night.png` | In-situ: the lean-to at night, the player at the bench, the terminal the only light on the surface — the surface's one emissive, and what it does to a face, a bench and the underside of a roof. | probe `g5_leanto_night` (**re-rendered**: screen strength 6 → 40, +1 stop; the first pass was black) |
| `g5_03_pithead-night-wide.png` | The whole pit-head at night from the spoil: the headframe against a sky just short of black, one lit rectangle under the lean-to roof. | probe `g5_leanto_night_wide` (**re-rendered**: night sky 0.0015 → 0.004 and +2.5 stops; the first pass was a black frame with a 12 px screen) |
| `g5_04_leanto-night-worklight.png` | **Proposal:** the same night frame with a caged work light hung under the lean-to roof (180 W, ~3500 K). The clear view of the place at night — bench, rack, roof, the person — and the alternative to "the terminal is the surface's one emissive": a yard with an electric winch has a work light. | probe `g5_leanto_night_light` (new; `--yard-lamp W` on any surface shot) |

## G0 — what the inventory missed

| image | intent | tool |
|---|---|---|
| `g0_01_teaching-loop-storyboard.png` | Six frames in order: course → bench → collar → commit → cave stop → replay. The loop `CAVE-BLOCKS.md` §9 built, drawn as places. | sheets |
| `g0_02_surface-vs-cave.png` | One act, two places: the stop on the course beside the stop in the cave. | sheets |
| `g0_03_pithead-from-the-yard.png` | The establishing wide from the yard: lean-to and rack in the foreground, the headframe and collar in the middle, the course beyond, sky. The one frame that shows the surface is a single small compound. | probe `a_yard_wide` |
| `g0_04_yard-bench.png` | The yard bench: a Scout and a Swimmer on the rack, a Surveyor on charge, loose modules and crates on the bench. Where loadouts are physical parts. | probe `a_yard_bench` |
| `g0_05_pithead-sun-variant.png` | The same wide with a sun, for the decision: the direction says the cave has no sun and never borrows one; the overcast default keeps the surface light identical to the shaft light. A sun makes the surface a different world. | probe `a_yard_wide --sky sun` |

## H1 — palette strips

Six zones, the belief register, and what is never a colour. World values are the linear
reflectances / light colours from `ART-DIRECTION.md` §3.1 / §5.2 / §2.1, shown gamma-encoded and
labelled with both; display values are `phase1/view/palette.py`'s. Kelvin swatches come from a
Planckian-locus fit and are approximate — the Blender rule is a Blackbody node.

| image | intent |
|---|---|
| `h1_01_palette-surface.png` | Sky, wet iron, wet spoil, hardstanding, pale shell, graphite, dark kit, the jacket, BONE, EMBER. |
| `h1_02_palette-shaft.png` | The 12000 K disc, VOID, wet rock, pale shell, timber, bearing steel. |
| `h1_03_palette-shallow.png` | Dry lit rock, scoured floor, wet rock, the lamp, WARM_DIM, BONE, ROCK_LIT. |
| `h1_04_palette-deep.png` | Wet rock, rock at depth, cast iron, bearing steel, 1900 → 2400 → 4000 K, KILL for the distance that must be kept. |
| `h1_05_palette-water.png` | Tide crust, wet, submerged, WATER, the underwater medium, graphitised iron, the corona. |
| `h1_06_palette-works.png` | Cast iron, graphitised, porcelain, polished rail, grease, timber, the boxed residual circuit. |
| `h1_07_palette-belief-and-accents.png` | SENSED, WALKED, GHOST, COOL_DIM, HAZARD, LIE, CARGO, KILL, HURT — overlay vocabulary, shown once. |
| `h1_08_palette-never.png` | Cyan, a second red, biome hue, glowing ore, orange rust, a sun, blue-for-flooding: each struck through. |
| `h1_09_tone-rows.png` | One tone row per zone sampled from this board's finished in-situ frames: sixteen luminance bins painted their mean colour, and the share of the frame under linear 0.02. |

## H2 — light sources

| image | intent |
|---|---|
| `h2_01_light-sources.png` | Rows = zones; each source a swatch at its colour and a bar for its reach on a 20 m scale, with the exposure contract underneath. |
| `h2_02_assayer-cycle.png` | The 75 s as light: 54 s of nothing, the slew, nine clicks 1900 → 2400 K at 1/9 per click, the 4000 K frame at ~4×, the decay; the anvil at a third; the nine clicks as swatches. |
| `h2_03_sources-contact.png` | One in-situ frame per source available on this board: the sky from above, the sky as the shaft's disc, the terminal at night, the lamp under a roof, the lamp in the cave, the pendant in drizzle. |

---

## The questions the fiction has not answered, and the answer each image proposes

| | question | proposed answer (what the board shows) |
|---|---|---|
| Q1 | Where is the player, physically? | At the pit-head, in the weather: beside the course for demonstrations, at the collar for the commit, at the listening post for the run, under the lean-to for composing and replays. Never underground. |
| Q2 | What is the interface, in the world? | A wired pendant (screen, five block keys, a wheel, a cable) and a bench terminal (screen, nine block keys, a wheel); the listening post's small screen for the run. No voice. |
| Q3 | What is the commit, physically? | The pendant cable pulled from the port at the collar, and the kibble lowered. |
| Q4 | How does teaching underground differ? | It does not: the machine stops at a decision point, the clock stops, the pendant/post shows belief only. The wire is replaced by the link. |
| Q5 | Is anything at stake on the surface? | Not settled by the designer. The board shows the surface as safe: nothing on it is lethal, wet or dark, and the only losses visible there are wrecks that come back to the bench. It asks rather than answers. |

## Guesses (everything not in `DESIGN-PRINCIPLES.md` §3)

**The place**
1. The pit-head is the prior industry's own dead surface works: a 9 m cast-iron headframe with a
   sheave, a roofless stone winding house with the dead engine's drum and flywheel inside, a stone
   kerb and cast collar round a 2.4 × 2.0 m timbered shaft. Same castings language as the Assayer:
   no paint, wet black iron, one bright bearing (the sheave groove) and one bright cable (the new
   rope).
2. The modern teams' kit is small, temporary and pale or dark polymer: a galvanised fence with a
   gap, a small electric winch on a skid with a galvanised kibble, a lean-to of timber and rusted
   sheet against the winding house, a bench, a rack, crates, the pendant, the terminal, the
   listening post — and, in one frame only (g5_04), a caged work light under the roof.
3. One pit-head per team; rivals are never seen on the surface (phase1 has two shafts in two
   chambers, so this is consistent, but the surface then has no social read — design problem 4).
4. Overcast always; no sun; time of day fixed per match; weather is the season axis. The surface
   light is the shaft's 12000 K so that the descent is continuous in colour and the cave's
   "no sun" rule survives in a surface-legal form. `--sky sun` exists only for the comparison.
5. The spoil flat is flat inside the works and rises into rough ground and heaps beyond; the
   hardstanding in front of the winding house is puddled setts.
6. Descent is in a kibble on the modern winch, on the old guides.

**The course**
7. 0.6 m/cell, inherited from `ART-DIRECTION.md`'s own inherited guess. `phase2/tuning.py` says
   "1 cell ~ 1 m"; at that scale the seed-104 course is 107 × 103 m and passages 14–36 m.
8. Walls 1.2 m (above the 0.57 m machine, below a person's eye), passages 1.8 m wide, open-topped,
   built from the mine's own furniture (hoarding on timber posts at the 1.2 m module); junction
   squares open; a capped dead end; the root a pale post with a WARM_DIM pilot; the deposit a pale
   crate and broken stock. The sim's corridor has no width at all.
9. The staged junction is the first one out from the root; the machine stops 0.4 m short of the
   node facing in, head turned to the first onward mouth; the player stands 2.1 m back on the side
   away from that mouth, leaning over the wall.

**The interface**
10. Everything in Q2, Q3 and Q4 above; the pendant's and terminal's dimensions, key counts and the
    wheel; that the pendant plugs into the existing charge port rather than a separate teach port.
11. The screens' content: the pendant shows the corridor teach window's belief inset plus the stop
    rail; the terminal shows phase2's post-induction window with a replay scrubber; the replay is the
    phase1 spectator reveal; the listening post shows phase1's belief-only "ITS MAP". Screen
    emission strengths (1.2 in daylight → 24 at dusk → 40 at night) are exposure choices, not
    photometry.
12. The person: 1.75 m, hooded, waxed-cotton dark, no face. Scale and the act only.
13. The yard work light (g5_04): a caged bulkhead under a rafter, 180 W in Blender units, ~3500 K
    `(1.0, 0.86, 0.68)`. It exists so the night frames can show the place; whether the surface has
    any standing light at night is the designer's, and the two night frames are the two answers.

**The rigs**
14. DAYLIGHT: sky strength 0.32 + a 12 kW / 14 m area from 34 m; drizzle 0.30 + 9 kW + haze
    0.006; dusk 0.07 (was 0.035: no roof-line); night 0.004 (was 0.0015: a black frame). CLEAR:
    grey world 1.0 + 1000 W / 3 m key + 220 W fill. All of these are what made the frames read,
    not measurements.
15. Board exposure: g2_05 +1.8, g3_03 +0.7, g3_04 +0.5, g3_05 +0.5, g4_03 +1.5, g4_05 +3.0,
    g5_02 +1.0, g5_03 +2.5, g5_04 +0.6 stops. Every other frame is at 0. The direction's rule
    against exposure compensation is a rule for the client; a board that cannot show the thing
    is the complaint this pass exists to answer, so the lifted frames say they are lifted.
16. The surface has no exposure contract yet; DAYLIGHT frames are 40–70 % legible by the cave's
    definition, which is the point of the place.

**The screens as bitmaps**
17. The probe puts real PNGs on the screens (an Image Texture node on a UV plane). `ART-DIRECTION`
    §3.2 forbids image textures in the *world*; a picture of a screen is the one thing that is
    honestly a bitmap, and it is a probe, not the client. The client would draw the screen live.

**The mood sheets**
18. h2_02: that the winch emits at all (inherited from `ART-DIRECTION` §5.4; `THE-MACHINERY.md`
    never says it glows); the anvil as a second source at a third; the decay drawn as an e-fold of
    3.5 s inside the doc's "over 8 s"; the Kelvin-to-RGB fit.

## Design problems found while building this (not art problems)

1. **The course cannot teach anything about darkness if it is open-topped in daylight** (also
   inventory problem 3). g1_08 shows that a roofed length in daylight is dim, not dark: lamp,
   silt and ping decisions are either met only in the cave, or the course gets a closed shed with
   doors — a second building on the surface the fiction has not asked for.
2. **`phase2.truth.corridor.Corridor` is a graph with positions, not a planar embedding: passages
   cross.** Seed 104 has three crossings (g1_07, red). The sim does not care; a physical course
   does. Either the corridor generator gains a no-crossing constraint (it is one rejection test in
   `_branch`), or the fiction says the course is not the corridor but a course *like* it, and the
   plan the pendant shows is not the plan on the ground.
3. **Cells are 1 m in phase2 and 0.6 m in the art.** `phase2/tuning.py` says so in its header;
   `ART-DIRECTION.md` says its 0.6 is stated nowhere. The course's size and the machine's stride
   against it both depend on which wins. At either scale a course of eight junctions with passages
   of 14–36 cells is a 60–110 m installation — a field, not a yard.
4. **Rivals are never seen on the surface** under one-pit-head-per-team. If the designer wants the
   surface to carry a social read (four crews at four winches), the pit-head is shared and every
   frame in G1–G3 changes shape.
5. **The surface breaks "the only light is what a machine brings"** unless its light is defined
   as the thing that comes down the shaft, which is what the DAYLIGHT rig does. It needs a yes.
   And at night it breaks it again: a screen cannot light a bench (g5_02 needed a strength-40
   screen and a stop of exposure to show a hand), so either the surface has a standing world light
   after dark (g5_04) or the surface at night is a black frame with a rectangle in it. The
   contrast §3 asks for — safe and lit against not — is made of exactly this.
6. **The pendant is a wire to a machine whose channel is defined as acoustic and low-bandwidth.**
   On the surface the wire is honest (the machine is in your hands). Underground (G4) the same
   picture arrives over the link, and the fiction should say how much of it does: a belief map is
   far more than "a few bytes" per second. Either the stop is rare enough that a full map can be
   sent while the clock is stopped, or the pendant underground shows less than it shows on the
   course.
7. **The charge port doubles as the teach port.** `build.py:236` has one port; a second would be a
   model change. Cheap, but it is `agent_model/`'s.

## Things this pass could not do

- No rain. Drizzle is wet materials, a darker sky and haze; rain streaks are a particle system
  the probe does not carry.
- No hands on the pendant: the mannequin holds it in two spheres.
- The course walls at a junction are simply trimmed back; corners are not filled. A real
  course would have panels turning the corner.
- The machine's believed graph drawn over the course (the inventory's "GHOST over render") is not
  made: it needs the belief out of a phase2 controller mid-run, which the CLI does not expose, and a
  drawn guess at drift would be exactly the kind of invented data the board should not carry.
  g1_09 (the junction from above) and g2_02 (the pendant's ITS MAP of the same kind of stop) are
  the two halves, shown separately.
- `build_agent` names its objects by fixed names, so a second machine in a scene loses the
  chassis bevel to the first one (`build.py` looks up `bpy.data.objects["chassis"]`). Cosmetic.
- Renders on this machine share the CPU with other Blender jobs, and one of those jobs killed
  every `blender.exe` at 18:48 (the `machines/batch.sh` comment names the same hazard). The batch
  script runs one Blender per shot so a kill costs one frame; the `_logs` show which.
