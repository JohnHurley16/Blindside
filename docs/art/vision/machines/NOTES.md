# Vision board — THE MACHINES

Group D of the inventory: four chassis, loadouts in silhouette, teams, wear, damage, the
lamp, daylight, the nine-pixel test. One line of intent per image; what each proposes
against what is established; every guess at the end.

Everything here was rendered by `machines_probe.py` (Blender 5.2, Cycles CPU, 40 samples,
960 × 600 unless stated) and `ladders.py` (PIL, no Blender), both in this directory. Re-run:

```
"C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b -P docs/art/vision/machines/machines_probe.py -- --shots all --out-dir <ABSOLUTE path to this directory>
.venv/Scripts/python.exe docs/art/vision/machines/ladders.py
```

`00_board.png` is every image below as a captioned thumbnail — the board in one picture.

**The rule for every concept:** one CLEAR view first (a rig a concept artist would use, so
the thing can be seen), then IN-SITU views in the direction's own light (world background
0, only sources the fiction supplies). Nine-tenths black is the direction for the match,
not for a board.

**Three fixes re-applied to every machine in every frame** (established in
`ART-DIRECTION.md` §0, §2.5, §4.3; `agent_model/` is still unfixed): the head lamp is
re-aimed +X, it is white for every team, and no emissive is cyan — strips are `BONE`
(player) / `EMBER` (rival) at strength ≤ 3. Directional wear (`worn_metal`) is copied from
`av_probe.py` so the two agree. The active sonar bar is **dark by default** in every frame
(passive) and lit only where a frame is about pinging — `ART-DIRECTION` design problem 2.

**Two reference rigs, both guesses, shared with the other renderers so clear views agree:**

- **CLEAR** — neutral grey world at strength 1.0, one 3 m area key from 45° high at
  1000 W, a grey ground plane, the 0.60 m rail gauge painted on the floor and a 1 m rod in
  0.1 m black/white bands. AgX Base Contrast.
- **DAYLIGHT** (surface only) — uniform overcast sky at the shaft's own 12000 K
  `(0.60, 0.74, 1.00)`, no sun disc, one 8 m soft "cloud break" area light. The claim it
  makes: the surface's light *is* the light that comes down the shaft.

Paths below are relative to this directory.

---

## chassis-lineup — the four chassis side by side (D1)

Established: `agent_model/params.py` — Scout 0.40 m hull, Surveyor 0.58, Hauler 0.90 on six
legs, Swimmer 0.66; ride heights 0.25 / 0.32 / 0.34 / 0.27. `ART-DIRECTION` §4.6: only the
Hauler is unmistakable.

| image | intent | tool |
|---|---|---|
| `chassis-lineup/01_clear_lineup_3q.png` | The four abreast on one floor, one light, front three-quarter; the 0.60 m gauge painted under the Surveyor ("the agent fits between the rails"); the banded rod for height. The first picture anyone should see of the machines. | probe, CLEAR |
| `chassis-lineup/02_clear_side_ortho.png` (2000 × 700) | Orthographic side elevation in a row, same scale, so hull length, ride height and leg count read as numbers against the 1 m rod. | probe, CLEAR, ortho |
| `chassis-lineup/03_clear_top_ortho.png` (2000 × 700) | Orthographic plan of the same row against the gauge: the Hauler's 0.32 m width against the 0.60 m rails; the Surveyor's 0.21 m. | probe, CLEAR, ortho |
| `chassis-lineup/04_insitu_passage_staggered.png` | The four in one passage, each under its own lamp, each a silhouette against the next machine's pool — which class reads from outline alone in the game's light. | probe, in-situ |
| `machine-daylight/04_insitu_four_in_the_yard.png` | The same four on the pit-head hardstanding under the overcast (cross-listed from D10). | probe, DAYLIGHT |
| `nine-pixel/01–04_src_*.png` | One machine per frame, identical camera and light (the `av_08` backlit framing): the single-machine in-situ reference for each class, and the source of the nine-pixel ladder. | probe, in-situ |

**Design problem carried (inventory #1):** `CHASSIS-TIMING` gives the Hauler a body of
4.0 cells (2.4 m); the model is 0.90 × 0.32 m. These renders show the model as built. At
0.6 m/cell the model's Hauler is 1.5 cells long — it fits a *narrow* passage, not only a
*hall*, which changes what the class is for. The designer must pick.

---

## chassis-gestures — proposed hull gestures (D2)

Established: nothing — `ART-DIRECTION` §4.6 is a proposal. Measured while building: of the
`ChassisSpec` fields, `build.py` reads only `hull`, `ride_height`, `legs`, `slots` and
`head_radius`; **`head_neck`, `head_pos`, `hull_bevel` and `spine_rail` are never read**, so
§4.6's "`head_neck` 0.07 → 0.13" and "`hull_bevel` 0.07 → 0.16" do nothing today.

| image | intent | tool |
|---|---|---|
| `chassis-gestures/01_clear_scout_asbuilt_vs_proposed.png` | Scout as built (far) against the proposal (near): head radius 0.045 → 0.055, hull height 0.085 → 0.070, and a 60 mm neck. *All sensor, no body.* | probe, CLEAR; the neck is the pan/tilt bones moved up in edit mode plus a column, because `head_neck` is dead |
| `chassis-gestures/02_clear_swimmer_asbuilt_vs_proposed.png` | Swimmer as built (standing, far) against the proposal (near): a bare-metal ballast band 0.3 L at mid-body, a chine along the seam, flat plate feet, legs stowed flat in the rest pose. *A sealed lozenge that walks on the bottom.* No fins, no thrusters. | probe, CLEAR; ride 0.12 + feet tucked for the stow |
| `chassis-gestures/03_clear_hauler_asbuilt_vs_truck.png` | Hauler with its default loadout (far) against the truck proposal (near): top modules off, a flat bed, two load rails, four tie-down cleats where the `top_*` slots are. *A frame around a hole.* | probe, CLEAR |
| `chassis-gestures/04_insitu_swimmer_proposed_backlit.png` | The proposed Swimmer walking, backlit by its own lamp: does the band + chine survive as an outline. | probe, in-situ |

Proposals, all of them: every number is §4.6's. The Swimmer's larger hull bevel was not
rendered (no live parameter); the chine and band carry the read instead. The Hauler's
"frame around a hole" was not attempted — it needs a hull rebuild, not a bolt-on.

---

## modules — the catalogue and the loadout in silhouette (D3)

Established: `params.MODULES` (seven modules), `build._module` (their geometry), `ART-
DIRECTION` §4.4 (the outline is honest; passive dark, active emits), `av_08/09` (the
backlit silhouette is the loadout readout, 0.71 % of frame).

| image | intent | tool |
|---|---|---|
| `modules/01_clear_catalogue_side.png` (2400 × 520) | Bare Surveyor, then each module alone on a Surveyor, orthographic side, same scale: sonar face bar, lamp, hydrophone bumps, beacon rack, belly bay, magnetometer boom, structural-monitor collars + box. | probe, CLEAR, ortho |
| `modules/02_clear_catalogue_top.png` (2400 × 520) | The same row from above against the gauge. | probe, CLEAR, ortho |
| `modules/08_clear_catalogue_sheet.png` | 01 and 02 stacked with a label per column — the catalogue sheet. | ladders.py |
| `modules/03_clear_loaded_3q.png` | The full default loadout, three-quarter, under CLEAR: every module visible at once as physical parts. | probe, CLEAR |
| `modules/04_insitu_sil_bare.png` | `av_08` re-rendered: bare chassis (lamp only) between the camera and its own pool. | probe, in-situ |
| `modules/05_insitu_sil_loaded.png` | `av_09` re-rendered: same frame, full loadout. The difference is the readout. Sonar bar dark here (passive). | probe, in-situ |
| `modules/06_insitu_rival_view_pinging.png` | What a rival sees, lit by the rival's own lamp: the sonar bar's seven elements lit while pinging. | probe, in-situ |
| `modules/07_insitu_rival_view_passive.png` | The same machine, same light, not pinging: the bar dark. *Passive sensors are dark, active sensors emit.* | probe, in-situ |

The model builds `face` + `eye` as two head slots (4/7/9) where `DESIGN.html` says 3/6/8;
the catalogue renders the model (`ART-DIRECTION` decision 6).

---

## modules-fixes — the two modules that fail, and the two state readouts (D4)

Established: `ART-DIRECTION` §4.4's verdicts (passive_acoustic and structural_monitor fail
the silhouette rule; beacon caps and cargo fill are proposed readouts) and §9 (no
world-readable inventory in the live view — these two are spectator/replay vocabulary).

| image | intent | tool |
|---|---|---|
| `modules-fixes/01_clear_bumps_vs_vane.png` | As built (five 6 mm rubber bumps on a rail, far) against the proposal (near): a line array standing 0.06 m proud of each flank on two stalks, 0.7 L long. *A listening machine looks wider.* No emissive, ever. | probe, CLEAR |
| `modules-fixes/02_clear_collars_vs_spike.png` | As built (ankle collars + deck box, far), the proposed 180 mm geophone spike stowed in a deck cradle (middle), and **planted** (near): the machine crouched to ride 0.15 with the spike from its belly into the floor. | probe, CLEAR |
| `modules-fixes/03_clear_rack_full_vs_dropped.png` | Beacon rack from behind: four tubes with lit caps (far) / two dropped, two lit caps remaining (near). A live inventory readout in the silhouette. | probe, CLEAR |
| `modules-fixes/04_clear_bay_0_1_2.png` | Cargo bay from low on the flank: a two-segment window on the bay, 0 / 1 / 2 lit. | probe, CLEAR |
| `modules-fixes/05_insitu_vane_backlit.png` | The vane machine backlit in a passage — wider than the bare outline in `modules/04`. | probe, in-situ |
| `modules-fixes/06_insitu_spike_planted_lamp.png` | The planted pose in a passing lamp: a low machine with a rod under it is *listening to rock*. | probe, in-situ |

Guesses: the vane's dimensions; that planting requires a crouch (180 mm cannot reach the
floor from a 0.32 m ride height, so monitoring becomes a posture as well as a part); the
window on the bay's flank rather than the hatch (the hatch faces the floor and cannot be
seen); cap pilots in `WARM_DIM`, the beacon's own colour.

---

## team — team identity (D5)

Established: `ART-DIRECTION` §4.3 — player `BONE #F2E6D2` pale shell over graphite; rival
`EMBER #FF7A2F` graphite shell over pale chassis; emissives ≤ 3; hue alone is a quarter of a
JND; the value inversion is 3.5–4× better and still at threshold; the rest needs a human
A/B. `av_05/06/07/12/13` (fiction-lit, 960 × 600) stand as they are.

| image | intent | tool |
|---|---|---|
| `team/01_clear_player_vs_rival.png` | Player (far) and rival (near) side by side under CLEAR: the inversion seen plainly, before the dark takes most of it away. | probe, CLEAR |
| `team/02_ladder_9_24_90.png` | The two at 9 / 24 / 90 px from the frame above — what survives at gameplay size under a *kind* light. | ladders.py |
| `team/03_insitu_rival_in_players_lamp.png` | One passage, both machines: the player (silhouette, near) lights the rival (lit, far) with its work lamp. The rival's EMBER strips against a lit shell. | probe, in-situ |
| `team/04_insitu_player_in_rivals_lamp.png` | The reverse: the rival's white lamp finds the player. The lamp is white for both — only the strips and the value say whose. | probe, in-situ |

---

## running-lights — retroreflective running lights (D6, decision #1)

Established: nothing — `ART-DIRECTION` §4.5 says answer this first. `build.py:142` makes
the strips emissive at strength 8 and adds a status sphere; the sim registers no emission.

| image | intent | tool |
|---|---|---|
| `running-lights/01_clear_emissive_vs_retro.png` | Under CLEAR: the §4.5 fallback (emissive strip at 1.5, 16 mm, no status sphere; far) against the proposal (retroreflective sheeting, 16 mm; near). Under a light that is not at the viewer, the retro strip is just a strip. | probe, CLEAR |
| `running-lights/02_insitu_quiet_unfound.png` | A quiet machine (lamp off, retro strips) with a rival's lamp pointed *past* it: the machine is not there. | probe, in-situ |
| `running-lights/03_insitu_quiet_found.png` | The same frame, the rival's lamp swung onto it from 4.5 m: it lights up like a road sign. Two frames, one decision. | probe, in-situ |
| `running-lights/04_insitu_wreck_found.png` | A wreck (every emissive dead) with retro strips, found by a lamp near the camera: it *appears*, all at once, silently — §6.2's argument for the proposal. | probe, in-situ |
| `running-lights/05_insitu_fallback_strip_1p5.png` | The fallback if retro is rejected: strip strength 1.5, no status sphere, nothing else lit. A dim pair of lines in the dark, honestly costed. | probe, in-situ |

**The approximation, stated:** Cycles has no retroreflector BSDF. The strip's shading normal
is bent to face the viewer (`Geometry → Incoming`), so its glossy lobe returns light that
arrives from near the camera and almost nothing else. Correct for the case that matters —
a rival's lamp is beside a rival's eye — and wrong for a lamp far off the viewer's axis,
which real prism sheeting would still return toward *that* lamp. Godot would do this with a
view-dependent emission, not a BSDF.

---

## wear — wear and age (D7)

Established: `ART-DIRECTION` §4.1 — three gravity masks (mud at the feet, dust on
horizontals in the rock's own colour, scuff on leading faces), extended to the lower leg;
wear is history, damage is state; the salvage skin loses its red. `av_03/04` measured it.

| image | intent | tool |
|---|---|---|
| `wear/01_clear_fresh_035_085.png` | Fresh (far) / 0.35 (middle) / 0.85 (near) under CLEAR, directed masks, legs included. 0.85 must read *veteran*, not casualty — nothing here is damage. | probe, CLEAR |
| `wear/02_insitu_veteran_lamp.png` | The 0.85 machine in a passing lamp raking from the side: the mud line at the feet, the dust on the deck, scuff on the prow. | probe, in-situ |
| `machine-daylight/06_insitu_veteran_in_the_yard.png` | The same veteran on the surface, where wear reads plainly (cross-listed from D10). | probe, DAYLIGHT |

---

## damage — damage rungs (D8)

Established: `ART-DIRECTION` §4.2's table — 0.20 sonar bar loses elements (7 / 4 / 2);
0.30 a hip cover shed, a gait hitch; 0.50 a hull panel not built (graphite under); 0.75 the
head stops tracking and jitters, the boom hangs, ride height −25 %; 1.00 the wreck. Must
read at nine pixels; no second red. No `damage` parameter exists in the model.

| image | intent | tool |
|---|---|---|
| `damage/01_clear_ladder_side.png` (2400 × 600) | Six side views in a row, 0 → 1.0: bar 7 lit / 4 lit / 4 lit + hip cover gone + one foot lifted / 2 lit + battery hatch missing / 2 lit + head frozen off-axis + boom hanging + ride −25 % / the wreck. | probe, CLEAR, ortho; per-element sonar materials, object removal, ride-height mutation, boom parts rotated about the hinge |
| `damage/03_ladder_9_24_90.png` | The six rungs at 9 / 24 / 90 px. The question is which rung is the first that reads at nine. | ladders.py |
| `damage/02_insitu_075_own_lamp.png` | The 0.75 machine under its own lamp, low, head pointing the lamp off to the side: a machine that can no longer look where it is going. | probe, in-situ |

The bar is lit in the ladder (a pinging machine) so the lost elements can be counted; in a
passive frame all rungs below 1.0 would show the same dark bar.

---

## own-lamp — a machine under its own lamp (D9)

Established: `ART-DIRECTION` §0, §2.2–2.4 — white 50° cone, 8–10° down, pool 3–6 m ahead,
near wall blown, ≈ 90 : 1 across three metres, the machine a backlit silhouette.
`av_02_lamp_fixed.png` is the target frame.

| image | intent | tool |
|---|---|---|
| `own-lamp/01_clear_same_frame_plus3stops.png` | `av_02`'s frame at +3 stops: what is actually in the passage. **Not the game** — captioned so nobody mistakes it for the exposure. | probe, in-situ, exposure +3 |
| `own-lamp/02_insitu_own_lamp.png` | `av_02` re-rendered: the target frame of the whole direction. | probe, in-situ |
| `own-lamp/03_insitu_rival_view_beam_in_face.png` | What a rival sees coming: the beam in your face, the machine behind it a shape. | probe, in-situ |
| `own-lamp/04_insitu_director_72deg.png` | From the spectator camera's elevation: the pool is the only lit thing on the floor; the machine is where the pool is not. | probe, in-situ |

---

## machine-daylight — a machine on the surface in daylight (D10 = A9)

Established: `DESIGN-PRINCIPLES` §3 only — a surface exists, it is the pit-head, it has sky,
it is safe and lit, teaching happens there. Everything drawn is a guess (below).

| image | intent | tool |
|---|---|---|
| `machine-daylight/01_clear_surveyor_daylight_3q.png` | Catalogue three-quarter of the Surveyor on the yard hardstanding under the overcast: emissives vanish, the reflector is a dark disc, the pale shell is just pale. It looks small and harmless. | probe, DAYLIGHT |
| `machine-daylight/02_clear_fresh_vs_veteran.png` | Fresh (far) and 0.85 veteran (near) side by side in daylight — wear reads plainly where the lamp never let it. | probe, DAYLIGHT |
| `machine-daylight/03_insitu_at_the_collar.png` | The machine at the shaft collar with the hole black behind it, the headframe and cable above, the winding house beyond: the last image before commit. | probe, DAYLIGHT |
| `machine-daylight/04_insitu_four_in_the_yard.png` | The four chassis loose on the hardstanding under the headframe. | probe, DAYLIGHT |
| `machine-daylight/05_variant_low_sun.png` | The collar frame with a low warm sun, for the designer to reject: the direction's "no sun" rule (§8.4) kept in surface-legal form by making the sky overcast always. | probe, DAYLIGHT + sun |
| `machine-daylight/06_insitu_veteran_in_the_yard.png` | The veteran close, on the wet hardstanding. | probe, DAYLIGHT |

The pit-head set inside `machines_probe.py` (`stage_yard`) is deliberately minimal — a
hardstanding, the collar (stone plinth, cast ring, the hole), a cast-iron headframe with
its sheave and cable, a roofless stone winding house, spoil on the skyline. Renderer B's
`surface.py` (inventory A1) is the real surface; these frames should be re-shot on it when it
exists, and the set here retired.

---

## nine-pixel — the nine-pixel test (D11)

Established: `SPECTATOR-DISPLAY` §6.4 — at `CAMERA_WIDE` a machine is nine pixels.
`docs/art/probes/pixel_ladder.py` is the reference method; its ladders were built from the
studio renders with cyan lights and are superseded.

| image | intent | tool |
|---|---|---|
| `nine-pixel/01_src_scout.png` … `04_src_swimmer.png` | Same camera, same passage, own lamp, backlit: the four classes. | probe, in-situ |
| `nine-pixel/05_src_rival.png` | The rival Surveyor in the same frame. | probe, in-situ |
| `nine-pixel/06_src_damaged075.png` | The 0.75 machine in the same frame. | probe, in-situ |
| `nine-pixel/07_src_wreck.png` | The wreck in the same frame, lit by a finder's lamp beside the camera (a wreck emits nothing, so this one cannot share the others' light). | probe, in-situ |
| `nine-pixel/08_ladder_chassis.png` | The four classes at 9 / 14 / 22 / 34 / 56 / 90 px, fiction-lit. | ladders.py |
| `nine-pixel/09_ladder_state.png` | Player / rival / damaged / dead, same ladder. | ladders.py |

The crop is the projected bounding box of the agent's parts (written by the probe as a
`.bbox.json` beside each render), not a brightness threshold: in a backlit frame the
brightest thing is the pool, not the machine.

---

## Guesses made in this group

1. **The CLEAR and DAYLIGHT rigs** — their values, and that the surface's light is the
   shaft's 12000 K with no sun ever. `05_variant_low_sun` exists so the alternative can be
   rejected on a picture.
2. **The pit-head set** — hardstanding, collar, headframe, winding house, spoil: shape,
   scale (headframe ≈ 9 m, collar ring ⌀ 2.6 m), the cast-iron material on all of it, and
   that the kit is where it is. Nothing in the fiction draws a surface.
3. **Emissive colours** are `av_probe`'s sRGB hexes used as linear values (BONE `(0.949,
   0.902, 0.824)` etc.), so this board matches `av_02/08/09`; a linearised BONE would be
   `(0.88, 0.78, 0.64)`.
4. **The sonar bar dark by default**, lit only while pinging.
5. **Module fixes**: vane size, the crouch-to-plant posture, the bay window's placement, cap
   pilots in `WARM_DIM`.
6. **Chassis gestures**: all of §4.6's numbers, plus the 60 mm Scout neck and the Swimmer's
   stow pose (ride 0.12, feet tucked beside the hull).
7. **Damage rungs** as rendered: 4 / 4 / 2 / 2 elements at 0.20 / 0.30 / 0.50 / 0.75; the
   boom hangs 48°; the hitch is a foot lifted 50 mm; the frozen head looks 50° right and
   down.
8. **The retroreflective approximation** (see running-lights).
9. **The wreck pose** is `av_10`'s, unchanged, at wear 0.95.
10. **Wear values** per rung: fresh 0 / 0 / 0 / 0; 0.35 with mud 0.5 dust 0.4 scuff 0.4;
    0.85 with mud 1.0 dust 0.8 scuff 0.9.
11. **Cameras**, every one.

## Design problems found, not art problems

1. **The Hauler's size** (inventory #1) — 4.0 cells in `CHASSIS-TIMING`, 1.5 cells in the
   model. The lineup renders the model; the class boundaries decide whether it fits a
   *passage* at all.
2. **Four `ChassisSpec` fields are dead** (`head_neck`, `head_pos`, `hull_bevel`,
   `spine_rail`): `ART-DIRECTION` §4.6's proposals name two of them as the knobs to turn.
   They need wiring into `build.py` before §4.6 can be expressed as parameters.
3. **`build.py` looks parts up by global name** (`bpy.data.objects["chassis"]`,
   `["shell"]`): in any scene with two machines the second machine's hull gets no bevel and
   the first gets two. Harmless on a board; a bug for a lineup or a match.
4. **A planted geophone cannot reach the floor** from the deck at ride height 0.32 with a
   180 mm spike; either the spike is longer, or monitoring is a crouch. Rendered as a crouch.
5. **The surface breaks "the only light is what a machine brings"** unless its light is
   defined as the thing that comes down the shaft (inventory #2). The DAYLIGHT rig is that
   definition and needs a yes.
