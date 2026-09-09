# The surface — vision board notes

The pit-head: where the shaft comes up, where the machines are kept, prepared, taught and sent
down, and the only place in the game with sky. Every image in this directory, one line each: what
it is for, what made it, and whether it draws something the design has settled or something this
board proposes. Nothing in the repo drew a surface before this; **almost everything here is a
proposal**, and the guesses are numbered at the end so the designer can strike them one by one.

**What is established** (and the only things this board treats as fixed):

- `docs/DESIGN-PRINCIPLES.md` §3 (2026-09-08): there is a surface, it is the pit-head, machines are
  kept / prepared / taught / sent down there, it is the only place with sky, it is safe and lit, the
  corridor test (phase 2) is a training course up here and the cave demonstrations are the same act.
- `docs/art/ART-DIRECTION.md`: the shaft's light is 12000 K `(0.60, 0.74, 1.00)`, "the only cold
  light, and the only daylight"; work lamps are white for every team; no cyan in the world; player
  `BONE`, rival `EMBER`; emissives at strength <= 3; the three wear masks; the wreck pose; beacon
  pilots `WARM_DIM`; cast iron `(0.075, 0.038, 0.021)` rough 0.86, bearing steel `(0.52, 0.50, 0.48)`
  rough 0.30 metallic 1; "still in use is polished bright".
- `docs/THE-MACHINERY.md` §1: the Assayer runs "for as long as it rains" — rain is canon.
- `docs/GLOSSARY.md`: **Commit** is the moment control leaves, ~20 s after descent; `DESIGN.html`:
  "Descent ~20 s", "you see the entry shaft and nothing else".
- `agent_model/build.py`: the machine has a charge port, an E-stop, a recovery handle and a comms
  mast ("acoustic modem to the surface"). The surface is where those are used.

Everything else — the layout, the headframe, the winch, the yard, the course's walls, the cage, the
pendant, the listening post, the weather, the floodlight, the yard light — is proposed here.

---

## How the images were made

| tool | what |
|---|---|
| `surface_lib.py` | the whole pit-head as one procedural Blender scene: terrain and spoil heaps, hardstanding with puddles, the shaft (collar, plinth, iron lining, rock below, guide rails, fence), cage, headframe with two sheaves, the modern winch, the dead winding house, the yard lean-to (bench, rack, cases, charge box, terminal), the listening post and cable drum, the course (phase2's `Corridor(54)` extruded at 0.6 m/cell), machines (agent_model with av_probe's three fixes re-applied), the wreck pose, a scale mannequin, the pendant, the rain card, the underground shaft chamber. Imports `agent_model`, `p2_env` and `phase2.truth.corridor` read-only. |
| `surface.py` | one function per shot; `--list` names them. `blender -b -P surface.py -- --shot <name> --out <ABSOLUTE>.png --samples 32 --res 960x600 [--screen belief.png] [--term replay.png]` |
| `render_all.sh` | the batch, skipping images that exist (`FORCE=1` to redo). |
| `diagrams.py` | PIL only: the four `00_*` diagrams and the pendant screen mock; `--composites` writes the descent strip, the sky strip, the ghost overlay and the graph overlay from the finished renders. |

All Blender frames: Cycles CPU, 32 samples, denoised, AgX Medium High Contrast, 960 x 600. The two
rigs, so the surface and the cave can be compared:

- **DAYLIGHT** (proposal): uniform overcast world at the shaft's own colour `(0.60, 0.74, 1.00)`,
  strength 1.0, plus one discless "cloud break" — a SUN lamp with a 25 deg angular size at 1.3 —
  so there are soft shadows but no sun disc and no shadow edges. Weather scales the world down
  (drizzle 0.55, rain 0.32, dusk 0.22, night 0.02) and adds a bounded scattering box for aerial
  perspective. **The surface's light is the shaft's light.** That is the proposal that keeps
  ART-DIRECTION's "the rendered world has no sun" rule alive up here.
- **IN-SITU** underground: world strength 0, resting scatter 0.012, only diegetic sources — the
  machine's own lamp (white, re-aimed +X, tilted 9 deg down) and, in the shaft chamber, the
  floodlight the teams hung under the sheave deck (guess 14).

Exposure: every in-situ frame is at exposure 0. A few CLEAR frames are lifted so the thing can be
seen, and say so in their line below; the lift is never applied to an in-situ frame.

Screens: the pendant and the listening post show a belief-only crop of a phase1 snapshot
(`--screen`); the bench terminal shows the spectator replay frame (`--term`). Both are pictures on
screens — the one place an image texture is allowed, because a screen is a thing that shows
pictures.

---

## A1 — the pit-head as a place

| image | view | intent | proposes |
|---|---|---|---|
| `00_pithead_plan.png` | diagram | The layout, settled once: collar and headframe at the origin, winch north of it, the roofless winding house behind, the lean-to on its west wall, the listening post by the collar, the course on the spoil flat to the east, spoil heaps around. PIL. | the whole layout |
| `01_pithead_wide.png` | CLEAR | DAYLIGHT establishing from the south-west at ~40 m: headframe over the collar, winch, winding house, lean-to, one machine walking to the collar, another on charge in the yard. The kit is pale and small against wet black iron. | the era read: the prior industry's own dead works, the teams camping in them |
| `02_pithead_high.png` | CLEAR | High oblique of the whole compound with the course spread on the flat to the east, so the scale of the course against the works is seen once. | course adjacent to the works |
| `03_pithead_insitu_drizzle.png` | IN-SITU | Match start in drizzle: one machine walking to the collar, lamp on, the flood down the shaft. No rival is ever in frame: each team has its own pit-head (guess 3). | one pit-head per team |
| `04_pithead_from_course.png` | IN-SITU | The compound seen from the course: what the player walks back toward with a taught machine. Overcast. | — |

## A2 — the headframe and winding gear

| image | view | intent | proposes |
|---|---|---|---|
| `05_headframe_elevation.png` | CLEAR | Side elevation with a Surveyor at its foot. Cast-iron A-frame in the Assayer's casting language, ~9.4 m to the sheave deck; the live sheave rim is bearing steel, the dead one is the same rust as the legs. | height, casting language |
| `06_headframe_threequarter.png` | CLEAR | Three-quarter from the south-west: frame, winch pad and the cable's run. | — |
| `07_headframe_sheave.png` | CLEAR | The two sheaves close: the one still in use polished bright where the cable runs, its neighbour rusted solid. "Still in use is polished bright." | the one bright bearing on the surface |
| `08_headframe_insitu.png` | IN-SITU | From the yard in drizzle, cable running, the cage half into the collar. | — |

## A3 — the yard: where machines are kept and prepared

| image | view | intent | proposes |
|---|---|---|---|
| `09_yard_bench.png` | CLEAR | The lean-to at working distance: four chassis on the floor under the rack, the seven modules on the bench, a recovered wreck being read, one machine on charge by cable from the wall box. | charge by cable; wrecks come back here |
| `10_yard_overhead.png` | CLEAR | Overhead of the lean-to so its layout is settled: bench, rack, crates, charge box, terminal. | — |
| `11_yard_modules.png` | CLEAR | The loadout as physical parts in a row on the bench — sonar bar, lamp, hydrophone rail, beacon rack, magnetometer boom, cargo bay, monitor box — built with `build._module()` unattached. The four chassis behind. | modules as things on a table |
| `12_yard_wreck.png` | CLEAR | A recovered wreck on the bench: the extraction loop's loss made visible on the surface; the recovery handle the only clean thing on it. | recovery ends at this bench |
| `13_yard_insitu_dusk.png` | IN-SITU | Dusk drizzle under the lean-to, the yard work light on (guess 16), a machine being loaded, the flood down the shaft beyond. Exposure +0.5 (this frame is half CLEAR: the light is the teams' own). | the surface is lit after dark by the teams' own lights |
| `54_shaft_recovery.png` | CLEAR | A wreck coming up in the cage at the collar, the next machine and the player waiting at the fence: the loss, arriving. | wrecks are winched up in the same cage |

## A4 — the training course (phase 2's corridor, made physical)

| image | view | intent | proposes |
|---|---|---|---|
| `00_course_plan.png` | diagram | Plan of `Corridor(54)` at 0.6 m/cell: root, eight junctions, leaves, the cargo leaf; the walls as this board builds them. PIL from `phase2.truth.corridor` read-only. | — |
| `14_course_oblique.png` | CLEAR | High oblique of the whole course on the spoil flat so a human reads the maze: 1.8 m passages between 1.2 m walls of corrugated hoarding on timber posts. | walls, width, material |
| `14_course_oblique_graph.png` | diagram | The same frame with phase2's graph drawn over it, node ids as phase2 numbers them. PIL over the render via the camera projection the render wrote. | — |
| `15_course_ground.png` | CLEAR | What the machine sees at a junction, from its own head height: blind walls, two ways on, nothing else. | the machine's information is nil |
| `16_course_human.png` | CLEAR | The same junction from a standing person's eye: every passage visible over the 1.2 m walls. The surface inverts the cave — full information, no authority is the cave; full information *and* authority is up here. | 1.2 m walls: above the machine, below a person |
| `17_course_root.png` | CLEAR | The root bay: the galvanised "shaft" post with its warm pilot, the machine set down for a demonstration, the player at the bay. | the root post as the course's beacon |
| `18_course_roofed_alt.png` | ALTERNATIVE | A roofed, dark stretch of the course with the machine's lamp on inside it — where lamp / silt / ping blocks could be taught up here at all (design problem 3). | a roofed section |

## A5 — the shaft mouth

| image | view | intent | proposes |
|---|---|---|---|
| `00_shaft_section.png` | diagram | Section: sheave deck, collar, iron lining, rock, the chamber below, the hydrophone cable beside the cage. PIL. | shaft ~2.4 x 2.0 m, iron-lined for 3 m |
| `19_shaft_lookdown.png` | CLEAR | Into the collar from above with the cage at the top and a machine standing on its grating floor. | the cage's open floor |
| `20_shaft_collar.png` | CLEAR | The collar from the yard side: cast ring on a stone plinth, guide rails, fence, the listening post's screen, the hydrophone cable going over the edge. | collar iron in the 1.2 m module (bolts at 0.6 m) |
| `21_shaft_hole.png` | CLEAR | Straight down from the collar with the flood off: iron lining, then rock, then black. This is what daylight alone does in a shaft — see design problem 2. | — |
| `22_shaft_insitu.png` | IN-SITU | From the yard side in drizzle, the cage three metres down, the machine's pale shell the last pale thing. | — |

## A6 — the descent (20 s from full authority to none)

| image | view | intent | proposes |
|---|---|---|---|
| `23_descent_1_collar.png` | CLEAR 1/4 | The cage at the collar, lit by sky, the machine in it. Full authority. | — |
| `24_descent_2_halfway.png` | CLEAR 2/4 | Camera inside the shaft nine metres down, the cage passing, the rock walls, the light from the flood above. Exposure +1.5. | — |
| `25_descent_3_lookup.png` | CLEAR 3/4 | From inside the cage looking straight up: the sky as a shrinking rectangle with the sheave deck in it, the bridle converging on the cable. Exposure +1.0. | — |
| `26_descent_4_chamber.png` | CLEAR 4/4 | Standing in the pool under the shaft: the one moment a machine is lit from above. Exposure +1.0. | the chamber's daylight is the flood (guess 14) |
| `23_descent_strip.png` | composite | The four as a vertical strip. PIL. | — |
| `27_descent_insitu_lookup.png` | IN-SITU | From the chamber floor looking up the shaft: the machine silhouetted through the cage grating, centred in the 12000 K rectangle, everything else black. | — |
| `28_descent_insitu_leaving.png` | IN-SITU | The "leaving somewhere" image: the machine walking out of the pool of daylight into black, lamp on. | — |

## A7 — sky, weather, time of day

| image | view | intent | proposes |
|---|---|---|---|
| `00_sky_values.png` | diagram | The six sky values with colour, strength and what each says. PIL. | all six |
| `29_sky_overcast.png` | CLEAR | The default: flat overcast at the shaft's 12000 K. The headframe from the south-west, a machine at the collar, the same frame for every sky. | overcast always |
| `30_sky_drizzle.png` | IN-SITU | Drizzle: everything wet, the sky lower, iron gone black and glossy. | wet iron in rain |
| `31_sky_rain.png` | IN-SITU | Heavy rain — the flooding season's tell. The streaks are a procedural card 0.9 m in front of the lens, an experiment, not a particle system. | rain as the season lever |
| `32_sky_dusk.png` | IN-SITU | Dusk: sky at 0.22, the flood cone down the shaft, the yard light on at the left. Exposure +0.5. | — |
| `33_sky_night.png` | IN-SITU | Night: the yard light, the flood and the terminal are the only light on the surface, and the surface is allowed them. Exposure +1.5 (the sky is at 0.02: without the lift it is honestly black). | the surface's lights are free; the cave's are not |
| `34_sky_sun_alt.png` | ALTERNATIVE | Low sun, for comparison: what breaking "no sun" costs — hard shadows and a second colour of light. | — |
| `29_sky_renders_strip.png` | composite | The six as a sheet. PIL. | — |
| `35_rain_shell.png` | IN-SITU | Rain on a machine's shell at the collar: the pale shell wet, the mud line, the hole behind. | — |

## A8 — the surface end of the acoustic link

| image | view | intent | proposes |
|---|---|---|---|
| `36_link_post.png` | CLEAR | The listening post: a tripod with a small screen showing the belief map, the cable drum, the hydrophone cable going over the collar and down beside the cage. The other end of "a thin acoustic link". | the post, the drum, the cable |
| `37_link_insitu.png` | IN-SITU | The player at the post in rain, the map the only picture on the surface, the shaft black. This is also where the commit happens (G3). | — |

## D10 / A9 — a machine on the surface in daylight

| image | view | intent | proposes |
|---|---|---|---|
| `38_machine_daylight.png` | CLEAR | Catalogue three-quarter of the Surveyor on the hardstanding: emissives vanish, the reflector is a dark disc, the pale shell is just pale, wear reads plainly, it looks small and harmless. | — |
| `39_machine_fresh_veteran.png` | CLEAR | A fresh machine and a veteran side by side: history, not damage (mud at the feet, dust on the top, scuff on the leading faces). | — |
| `40_machine_lineup.png` | CLEAR | The four chassis abreast in daylight: Scout, Surveyor, Hauler, Swimmer (cross-ref the machines board). | — |
| `41_machine_rival_daylight.png` | CLEAR | Player and rival in daylight: the value inversion is all that is left when the emissives vanish. | — |
| `42_machine_collar.png` | IN-SITU | The machine at the collar in drizzle, the shaft behind it: the last image before commit. | — |

## The teaching frames rendered on this scene (G1–G4; the teaching board covers these concepts fully)

| image | view | intent | proposes |
|---|---|---|---|
| `00_pendant_screen.png` | diagram | The pendant's screen: belief inset, "it knows" predicates with values, numbered action keys, the sentence. PIL. | the interface's content (Q2) |
| `43_teach_overshoulder.png` | CLEAR | Over the player's shoulder at the wall: the machine stopped at a junction below, the pendant on its cable showing belief only. The stop is a question. | wired pendant (Q2), the player at the wall (Q1) |
| `44_teach_wide.png` | CLEAR | The demonstration wide: the player over the wall, the machine below, the course around them. | — |
| `44_teach_wide_ghost.png` | composite | The same frame with what the machine believes the course is drawn over it in GHOST — unlit, drawn, drifting a few pixels per hop. PIL. | belief drawn, truth rendered, up here too |
| `45_teach_insitu.png` | IN-SITU | Drizzle, late: the machine at a dead end turning back, the player following along the wall. | — |
| `46_pendant_product.png` | CLEAR | The pendant on the bench at hand scale: screen, six block keys, scrub wheel, coiled cable. | Q2 |
| `47_terminal_bench.png` | CLEAR | The bench terminal: a rugged case, the replay with tree and sentence on its screen. | Q2 |
| `48_interface_collar.png` | IN-SITU | The pendant plugged into the machine at the collar, the player beside it: the last conversation before commit. | — |
| `49_interface_terminal_dusk.png` | IN-SITU | The terminal lit in the lean-to at dusk with a replay on it. | — |
| `50_commit_in.png` | CLEAR | Macro: the cable in the charge port. Control is still a wire. | Q3: the commit is a cable unplugged |
| `51_commit_out.png` | CLEAR | Macro: the port empty, the cable coiled on the collar. The moment control leaves. | Q3 |
| `52_commit_wide.png` | IN-SITU | Cable coiled on the collar, cage gone, the player at the listening post, the shaft black. | — |
| `53_teach_cave_truth.png` | CLEAR | The rendered truth of an underground stop, for the two-panel with the belief snap the player actually gets. | — |

---

## State of the board (what changed in this pass)

An earlier pass built the scene and rendered 53 frames but left seven of them black or unreadable
and never wrote these notes. Found and fixed here:

1. **The shaft was not a hole.** The hardstanding, the terrain and the plinth were solid, so the
   shaft was capped at ground level — every frame from inside or below the collar (24–27) rendered
   black, and 19–22 showed a grey slab inside the collar. The terrain is now punched under the
   hardstanding, the hardstanding and plinth are frames around the opening, and the underground
   chamber's roof is punched where the shaft tube enters.
2. **The cage floor** was a solid plate, so from below the machine could never read against the
   sky. It is an open grating now (guess 12).
3. **Dusk and night** skies were at 0.09 and 0.004 — black frames. They are at 0.22 and 0.02, the
   yard work light exists (guess 16), and those frames carry a stated exposure lift.
4. One new frame, `54_shaft_recovery.png`.

Re-rendered this pass: 08, 13, 19, 20, 21, 22, 24, 25, 26, 27, 28, 32, 33, 36, 54, and the four
composites.

---

## Every guess

1. **The era.** The pit-head is the prior industry's own surface works, dead: the same wet black
   castings as the Assayer, no paint, foundry marks, no dates; the modern teams' kit is small,
   galvanised or pale, and temporary.
2. **Northern, high-latitude, wet.** Overcast always; no sun, ever (the `sun` frame is the
   alternative, not the proposal). Time of day is fixed for a match; weather is the season axis.
3. **One pit-head per team.** Phase 1 has two shafts in two chambers; four teams "see the entry
   shaft and nothing else"; so rivals are never seen above ground.
4. **The surface's light is the shaft's light** — `(0.60, 0.74, 1.00)`, the shaft's 12000 K — so
   "the only daylight" underground and the sky up here are one thing.
5. **Scale**: 0.6 m/cell (inherited; stated nowhere in the repo); shaft 2.4 x 2.0 m, iron-lined for
   the top 3 m, bare rock below; the surface scene digs it 40 m and ends it in black, the section
   drawing gives 16 m of shaft to a 9.6 m chamber, and the chamber scene's tube is 24 m -- three
   numbers for one depth, none of them decided; collar iron 150 mm proud on a 400 mm stone plinth; headframe 9.4 m to the deck, sheaves
   1.8 m across; winding house 9 x 7 m, roofless, with a 4.4 m flywheel and the dead engine inside;
   lean-to 7 x 5 m; hardstanding 32 x 28 m.
6. **The cage**: a galvanised open cage on a four-rope bridle to a single cable, on a small modern
   electric winch rigged to the old frame, ~20 s down. Not a kibble (a bucket would hide the
   machine).
7. **The course**: `Corridor(54)`, passages 1.8 m (3 cells) between 1.2 m walls of corrugated
   galvanised hoarding on timber posts, open-topped, cut back 1.3 m at every node; the root is a
   galvanised post with a `WARM_DIM` pilot (the "shaft" beacon); the deposit leaf holds a pale crate
   and a few stones. Built from the mine's own furniture (sleepers, hoarding, spoil) would be the
   fiction; the render uses hoarding only.
8. **The yard**: charge is by cable from a wall box into the model's charge port; the four chassis
   live on the floor under a rack of cases; modules are kept as parts on the bench; recovered wrecks
   come to the bench to be read.
9. **The listening post**: a tripod with a small screen and a cable drum; a hydrophone cable runs
   over the collar and down the shaft beside the cage. Entirely proposed (cross-ref A8 / G2 / G3).
10. **The interface** (Q2): a wired pendant — screen, six block keys, a scrub wheel — for
    demonstrations at the course and at the collar; a bench terminal for composing and replay;
    **no voice** (the machine's channel is acoustic and low-bandwidth; a voice would promise a
    bandwidth the game denies).
11. **The commit** (Q3) is the cable pulled from the charge port at the collar; the cable is the
    difference between the surface (a wire) and the cave (a hydrophone and a few bytes).
12. **The cage floor is a grating** so the machine reads from below. A real cage has a plate floor.
13. **Puddles** on the hardstanding (IOR 1.33, roughness 0.02) and a `WET` material switch that
    turns the iron black and glossy in drizzle and rain.
14. **The floodlight.** Sky through a 24–40 m shaft does not light the chamber floor (irradiance
    ~ L x A / h^2: 4.8 m^2 at 24 m is 0.8 % of the sky's radiance, black after AgX). So the "only
    daylight" ART-DIRECTION §2.1 gives the shaft chamber needs a source: this board hangs the teams'
    floodlight under the sheave deck, aimed down the shaft, in the sky's own colour
    (2500–4000 W in Blender's units). The alternative is a shallow, wide aven. Needs a ruling —
    design problem 2.
15. **Exposure lifts on CLEAR frames only**: 24 (+1.5), 25 (+1.0), 26 (+1.0), 13 (+0.5), 32 (+0.5),
    33 (+1.5). No in-situ cave frame is lifted.
16. **The yard work light**: a white LED area light under the lean-to roof, the lamp's
    `(1.00, 0.98, 0.95)`, 320 W. The surface is "safe and lit" (DESIGN-PRINCIPLES §3); after dark
    that has to mean the teams' own lights, and they are the one light the cave never has: free.
17. **The rain card**: streaks as a procedural transparent card 0.9 m in front of the lens. A cheap
    trick for two board frames, not a rain system.
18. **The mannequin**: 1.75 m, faceless, matte dark jacket, scale and gesture only. Nobody has
    designed a person for this game and this is not that design.
19. **The DAYLIGHT rig itself** (world 1.0 + a 25 deg discless sun at 1.3) and every weather value
    in `00_sky_values.png`.
20. **The wreck in the cage** (54): wrecks come up in the same cage the machines go down in.
21. **The Hauler renders as `agent_model` builds it** (0.90 x 0.32 m). CHASSIS-TIMING's 4.0-cell
    body would be 2.4 m; the model is used as-is and the disagreement is left to the designer.

## Design problems found (not art problems)

1. **The surface breaks "the only light is what a machine brings"** unless the surface's light is
   defined as the same thing that comes down the shaft. Guess 4 is that definition and needs a yes.
2. **Sky does not reach the bottom of a shaft.** ART-DIRECTION §2.1 gives the shaft chamber a
   12000 K "daylight" source; physically a 2.4 x 2.0 m opening 24 m up delivers under 1 % of sky
   radiance to the floor. Either the teams light the shaft (guess 14), or the shaft chamber is a
   wide shallow aven, or the chamber is simply black and the direction's table changes. `21_shaft_hole`
   is the honest picture: daylight alone goes black three metres down.
3. **An open-topped daylight course cannot teach darkness.** Drift and junction choice, yes; lamp,
   silt and ping decisions, no. Either the course has a roofed dark section (`18_course_roofed_alt`)
   or those blocks are only ever met in the cave.
4. **With one pit-head per team, rivals are never seen at all above ground** and the surface has no
   social read. If the designer wants rivals visible on the surface, the pit-head is shared and A1
   changes shape.
5. **Nothing is at stake on the surface** (Q5). Not settled by the designer; the board shows it safe
   and asks.
6. **Teaching underground is the same act through a wire that no longer exists.** The pendant's
   cable is the surface's authority; underground the same stop arrives over the acoustic link and
   the match clock stops (CAVE-BLOCKS §9). The board draws the pendant showing the same belief-only
   picture in both places; whether the underground stop is a *match* feature or a *training* mode is
   a design question this board does not answer.

## Not done

- No Blender cutaway of the shaft section (the PIL section stands in).
- No frame of the machine's own view on the surface (the belief cloud in daylight); the `found`
  board owns the cloud.
- `18_course_roofed_alt` roofs three passages by hand; a real roofed section would need the course
  builder to know which passages are dark.
- The teaching concepts (G1–G5) are only sketched here on the surface scene; `../teaching/NOTES.md`
  is their board.
