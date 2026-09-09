# Vision board — THE DESCENT AND THE CAVE

Group B of the inventory: the shaft chamber, passages by width, chambers, the waterline,
below the waterline, silt, rock types, magnetic rock (the negative concept), unstable
ground, thermal layering, depth, and the works — the drive, the rails, the Bus, the survey
plates, deep machine ground — plus one concept the inventory missed, a junction in rock
(B17), which is the atom of every teaching stop underground. Rendered 2026-09-08.

Every concept has at least one **CLEAR** view and at least one **IN-SITU** view.

- **CLEAR** is a concept-art reference, not the game: a neutral grey world at strength 1.0,
  one 3 m area key from about 45° high, AgX base look, a 1.2 m black-and-white ruler or the
  0.60 m rail gauge or a 0.77 m Surveyor in frame for scale. Enclosed rock is cut away
  (bisected) so the light can get in. Show the thing first.
- **IN-SITU** is the game's own light: world background strength 0, resting silt 0.008–0.012,
  and only the fiction's sources — the head lamp (white `(1.00, 0.98, 0.95)`, re-aimed to +X
  and tilted 6–12° down, 600 W at 960 px), the shaft's 12000 K sky `(0.60, 0.74, 1.00)`, a
  beacon pilot in WARM_DIM, the Assayer's winch from a Blackbody node at 2400 K. AgX medium-high
  contrast, no exposure rescue except where the notes say so. The mood second.

Every frame re-applies the three `agent_model` rig faults ART-DIRECTION §0/§2.5 names, at
runtime and without touching `agent_model/`: lamp re-aimed `Euler((0, -π/2, 0))` and tilted
down, lamp white for every team, identity emissives at strength ≤ 3 in BONE `#F2E6D2` — never
cyan. Survey plates are dark (§6.5). No red anywhere. 0.6 m per cell.

**Rendering these again.** `cave_probe.py` is one script, many shots; `cave_batch.sh` runs
them in groups (one Blender 5.2 process per group, 40 spp, 960×600, Cycles CPU, denoised) into
`_render/`, and `sort_into_concepts.py` copies each frame to `<concept>/NN_name.png`;
`sheets.py` (PIL) makes the labelled composites. The `.venv` has no `bpy`; use the Blender
install:

```
"C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b -P cave_probe.py -- --list
"..." -b -P cave_probe.py -- --shot b12_03_insitu_drive_lamp --out <abs>.png
bash cave_batch.sh            # everything, skipping frames that exist
python sort_into_concepts.py  # any Python 3
.venv/Scripts/python.exe sheets.py
```

The probe reuses `docs/art/probes/p2_env.py` (passage, chamber, lights, settings) and copies
the worked drive from `docs/art/ruins/ruins_probe.py` (that file parses argv at import and
cannot be imported). The rock is `p2_env.rock()` extended with a `dark` scalar (the depth
field, albedo × (1 − 0.55·depth)), a `wet_above_z` mask (condensation above the thermal
layer) and a CLEAR-only module grid.

---

## cave-shaft/ — the shaft chamber underground (B1)

Established: the shaft is one of the four sources — 12000 K `(0.60, 0.74, 1.00)`, "the only
cold light, and the only daylight", lighting its own chamber (ART-DIRECTION §2.1); the
descent is ~20 s and the surface's light IS this light (the surface board, `../surface/`).
Proposed here: a cast landing plate where the kibble sets down; a 1.7 m aven radius (the
surface board's shaft is 2 × 2.4 m — the two should be reconciled; mine is the older
`p2_env` number). The chamber is `p2_env.chamber()` with the aven punched through the roof.

| image | intent | tool |
|---|---|---|
| `01_clear_cutaway.png` | CLEAR. The room cut in half: the dome, the aven going up out of frame, the landing plate under it, the Surveyor and a 1.2 m ruler for scale. This is the only room in the cave with a hole in the roof. | `b1_01_clear_cutaway` |
| `02_clear_aven_only.png` | The same cutaway lit by nothing but the sky at +3 stops (AgX base look): the shaft is a column of cold light and everything it does not reach is not there. Captioned as not-the-game (the exposure). | `b1_02_clear_aven_only` |
| `03_insitu_pool.png` | IN-SITU. The machine standing in the pool of daylight under the aven, lamp off, from three metres: the last lit moment before it has to make its own light. | `b1_03_insitu_pool` |
| `04_insitu_leaving.png` | IN-SITU. The machine walking out of the pool into black with its lamp on — "leaving somewhere". The daylight behind it, its own pool ahead of it, nothing between. | `b1_04_insitu_leaving` |
| `05_insitu_lookup.png` | IN-SITU. From the floor, looking up the aven: the machine centred under the 12000 K disc, the rock of the aven throat catching the sky, everything else black. | `b1_05_insitu_lookup` |

Guesses: sky area light 2600 W + an emissive disc at strength 9 (the disc is what the camera
sees; the area light is what lights the room); the landing plate; the aven radius.

## cave-width/ — passages by width class (B2)

Established: four width classes crawl / narrow / passage / hall (CHASSIS-TIMING D5, cells
2–3 / 3–4 / 4–5 / ≥5, marked **guess** there); the 1.2 m module and the 0.60 m gauge as
the scale rulers (ART-DIRECTION §3.3); "a crawl is where a Hauler's 0.32 m stops" (§3.5).
Rendered widths in metres are my reading of the cell classes: crawl 1.5 × 1.3 m, narrow
2.1 × 2.2, passage 2.7 × 3.2, hall 3.9 × 5.0 — the narrow end of each class, so the
difference reads.

| image | intent | tool |
|---|---|---|
| `01–04_clear_section_*.png` | CLEAR. Four cross-sections, same rock, same rig, same Surveyor at the same spot, the 0.60 m gauge painted on the floor and a 1.2 m ruler across the mouth. The machine is the constant; the hole changes. | `b2_01_clear_section_{crawl,narrow,passage,hall}` |
| `05_clear_scout_crawl.png` | CLEAR. A Scout in the crawl: the class that fits anywhere. | `b2_02_clear_scout_crawl` |
| `06_clear_hauler_crawl.png` | CLEAR. The Hauler in the same crawl, as `agent_model` builds it (0.90 × 0.32 m). It fits — which is the design problem, not the render: CHASSIS-TIMING makes the Hauler 4.0 cells (2.4 m) across, 7× the model. The designer must pick. | `b2_03_clear_hauler_crawl` |
| `07_insitu_crawl_lamp.png` | IN-SITU. The lamp in a crawl: the near wall blown at 1.5 m, the pool right under the head, nothing to see because everything is too close. | `b2_04_insitu_crawl_lamp` |
| `08_insitu_hall_lamp.png` | IN-SITU. The same lamp, same camera, in a hall: the beam finds nothing. Width is read from what the light does, never from fog or brightness. | `b2_05_insitu_hall_lamp` |
| `09_sheet_four_classes.png` | The four sections on one sheet, labelled with the cell classes. PIL. | `sheets.py` |

Guesses: the metre widths; the crawl's 1.3 m height (below a human, above the 0.57 m
machine); that a natural crawl is a lens, not a tube.

## cave-chamber/ — chambers (B3)

Established: the largest chamber is 14.4 m across, "about one lamp wide", and no landmark
may be required to be visible across one (ART-DIRECTION §3.6); a chamber that holds
something worth seeing must be taller than the passages that reach it (§5.5).

| image | intent | tool |
|---|---|---|
| `01_clear_cutaway.png` | CLEAR. A 14.4 m chamber cut in half, the 1.2 m module drawn on the floor as a grid so the size is countable, the Surveyor at the centre. | `b3_01_clear_cutaway` |
| `02_insitu_one_lamp.png` | IN-SITU. The same room by one lamp: the pool, the near rubble, and no far wall. A chamber is a place where the beam comes back with nothing. | `b3_02_insitu_one_lamp` |
| `03_insitu_beacon_far.png` | IN-SITU. The same frame with one beacon on the far side, 9.6 m off: the only thing that reads at distance is a thing that emits. Position without identification — a Contact. | `b3_03_insitu_beacon_far` |

Guesses: the 8 m ceiling; the floor grid is CLEAR-only and drawn in the shader.

## cave-waterline/ — the sump and standing water (B4)

Established (ART-DIRECTION §3.5): a waterline and everything one does — a 0.12 m mineral
tide-mark crust above it (albedo ×1.7, matte), below it albedo ×0.6 and roughness 0.10,
the surface IOR 1.33 roughness 0.02, a mirror at grazing angle that lidar returns as a
wall; not a blue tint. §2.7: wet rock keeps a glint after the beam leaves, dry rock does
not — "a wet passage stays findable".

| image | intent | tool |
|---|---|---|
| `01_clear_section.png` | CLEAR. The passage cut down its axis and seen from the side, low: dry rock, the pale crust band, the surface as a line, the submerged floor going down under the water. The machine stands on the bank at the crust line. | `b4_01_clear_section` |
| `02_clear_grazing.png` | CLEAR. Down the flooded passage at 0.7 m: the surface is a mirror and the far mouth is in it twice. This is what a range sensor sees too. | `b4_02_clear_grazing` |
| `03_insitu_pool_returns.png` | IN-SITU. The lamp pool reaching the water and coming back off it onto the far wall: the one place in the cave where the light goes somewhere the machine did not point it. | `b4_03_insitu_pool_returns` |
| `04_insitu_wet_streak.png` | IN-SITU. The rival's view: a wet floor (roughness 0.10) returns the lamp along a streak toward the camera — a wet passage stays findable after the beam has left. | `b4_04_insitu_wet_streak` |
| `05_insitu_dry_same.png` | IN-SITU. The identical frame with dry rock (roughness 0.96): no streak, nothing to find. Wetness is a navigation axis, not decoration. | `b4_05_insitu_dry_same` |
| `06_sheet_section_labelled.png` | The section with the bands named. PIL. | `sheets.py` |

Guesses: the water volume under the surface (scatter 0.03, absorption 0.05 off red) in the
CLEAR section; the floor's 4° fall so the water deepens down the passage.

## cave-underwater/ — below the waterline (B5)

Established: scatter 0.35, absorption weighted off red, anisotropy 0.8, light dies in
4–6 m (ART-DIRECTION §2.6); the Swimmer walks the bottom, no fins, no thrusters (§4.6);
amphibious with a heavy dry penalty (CHASSIS-TIMING D6). Nothing in the repo had been
rendered underwater before this.

| image | intent | tool |
|---|---|---|
| `01_clear_above.png` | CLEAR pair, first half: a flooded drive (waterline 1.1 m) seen from above the line under one fixed source. | `b5_01a_clear_above` |
| `02_clear_below.png` | CLEAR pair, second half: the same drive, same source, the camera under the surface with the volume on. The colour goes off red, the far end goes first. | `b5_01b_clear_below` |
| `03_clear_light_death.png` | CLEAR. Seven white balls at 1 m intervals in front of a fixed 600 W spot under water: where the light dies, measured in balls. | `b5_04_clear_light_death` |
| `04_insitu_swimmer_lamp.png` | IN-SITU. The Swimmer's own lamp under water, silt from its feet, four metres of visibility and then nothing. | `b5_02_insitu_swimmer_lamp` |
| `05_insitu_from_above.png` | IN-SITU. What a walker sees of a Swimmer: a lamp glow under the surface, the machine itself a shape in it. | `b5_03_insitu_from_above` |
| `06_sheet_above_below.png` | The pair on one sheet. PIL. | `sheets.py` |

Guesses: the absorption colour `(0.45, 0.70, 0.82)` and density 0.12; the Swimmer's loadout
(the default has no `optical` — I fit one so it has a lamp); exposure lifted 0.8–1.6 stops
in the underwater frames, otherwise the medium eats everything at 40 spp.

## cave-silt/ — silt (B6)

Established (ART-DIRECTION §2.6): resting scatter 0.008–0.012, silt is the only thing
that raises it, ~0.05 behind a moving agent decaying over 10–20 s, 0.15 self-blinding;
"the beam is only visible when the agent has stirred silt". `BLD-96` models it as
transient, movement-raised, mass-scaled.

| image | intent | tool |
|---|---|---|
| `01_insitu_stopped.png` | IN-SITU. Agent stopped, rest density only: no beam in the air, just the pool on the floor. | `b6_01a_insitu_stopped` |
| `02_insitu_walking.png` | IN-SITU. Same frame, agent walking: a plume of ~0.05 behind and around it, and the beam appears in it. | `b6_01b_insitu_walking` |
| `03_insitu_blinded.png` | IN-SITU. 0.15: the plume swallows the pool; the machine has blinded itself. | `b6_01c_insitu_blinded` |
| `04_insitu_plume_behind.png` | IN-SITU. From behind: the machine a silhouette in its own beam, the plume around it. Movement makes you visible twice. | `b6_02_insitu_plume_behind` |
| `05_sheet_three_densities.png` | The three densities on one sheet. PIL. | `sheets.py` |

Guesses: the plume is a stretched sphere of scatter with a spherical falloff and a noise
break-up, hand-placed behind the machine; there is no simulation in it.

## cave-rock/ — rock types (B7)

Established: one rock material, four scalars, no hue axis; rock type = `fracture` 3→14
and `bedding` contrast; absorbent = friable, tight, spalled; reflective = dense, planar,
blocky; the three rock values dry `#9E8B74` / wet `#796C5B` / submerged `#554D46`
(ART-DIRECTION §3.1). "Rock type changes surface, never colour."

| image | intent | tool |
|---|---|---|
| `01_clear_swatches.png` | CLEAR. Six slabs under one key: fracture 3 / 8 / 14 across, bedding contrast low / high down. One colour family; only the surface changes. | `b7_01_clear_swatches` |
| `02_clear_three_values.png` | CLEAR. The three rock values as slabs: dry, wet, submerged (the last under a block of water). | `b7_02_clear_three_values` |
| `03_insitu_absorbent.png` | IN-SITU. An absorbent passage under the lamp at the fixed exposure: the beam is eaten, the pool is small and soft. | `b7_03_insitu_absorbent` |
| `04_insitu_reflective.png` | IN-SITU. A reflective passage, same lamp, same exposure: the walls throw the light back, the pool is bigger and harder. Sonar quality, expressed as surface. | `b7_04_insitu_reflective` |
| `05–06_sheet_*_labelled.png` | The swatch frames with the values written on. PIL. | `sheets.py` |

Guesses: the two in-situ passages' scalar settings (albedo 0.05–0.16 wet 0.15 fracture 14
versus 0.03–0.34 wet 0.6 fracture 3) — chosen to bracket the axis, not measured.

## cave-magnetic/ — magnetic rock, the negative concept (B8)

Established: **nothing visible, ever** (ART-DIRECTION §3.5, §9). "If noisy rock glows,
the magnetometer is redundant and the false-find mechanic dies."

| image | intent | tool |
|---|---|---|
| `01_insitu_noisy.png` | IN-SITU. A Surveyor with its magnetometer boom raised, lamp on a wall of magnetically noisy rock. | `b8_01a_insitu_noisy` |
| `02_insitu_deposit.png` | IN-SITU. The same machine, same lamp, rock over a true deposit. The two frames differ only by the passage seed. That is the rule. | `b8_01b_insitu_deposit` |
| `03_sheet_the_rule.png` | Both frames side by side, captioned as the rule so nobody invents a glow. PIL. | `sheets.py` |

No CLEAR view: there is nothing to show clearly. The pair IS the concept.

## cave-unstable/ — unstable ground (B9)

Established (ART-DIRECTION §3.5): geometry, not colour — fresh spall on the floor, open
joints in the back, a fracture set that runs, one timber set failed while its neighbours
stand; static, so it is learnable before the sensor speaks; the structural monitor's
geophone is the sensor that hears it.

| image | intent | tool |
|---|---|---|
| `01_clear_sets.png` | CLEAR. A drive with five timber sets in the 1.2 m module, the middle one failed: post broken, cap down at one end, spall under it, an open joint in the crown above. Nothing is coloured. | `b9_01_clear_sets` |
| `02_clear_fracture_set.png` | CLEAR. A natural passage where a fracture set runs: parallel open joints across the wall at one dip, and fresh angular spall under them. | `b9_04_clear_fracture_set` |
| `03_insitu_failed_set.png` | IN-SITU. The failed set in the lamp, half in the pool: the thing a player learns to read before the geophone does. | `b9_02_insitu_failed_set` |
| `04_insitu_fracture_set.png` | IN-SITU. The lamp raised onto the running fracture set. | `b9_03_insitu_fracture_set` |

Guesses: the sets (0.20 × 0.18 m posts, 0.22 m cap, waterlogged timber material); joints
as dark slots set into the wall rather than carved; the spall as flat-shaded ico rubble.

## cave-thermal/ — thermal layering (B10)

Established (ART-DIRECTION §3.5): draw the cause, never the effect — a 0.3 m haze band at
the layer height that a beam flares crossing; condensation on the wall above it and not
below; a thermocline shimmer in flooded sections. The shadow zone is never drawn.

| image | intent | tool |
|---|---|---|
| `01_clear_band.png` | CLEAR (half-exposed studio + the volume): the haze slab at 1.5 m, the beam tilted up through it. The layer is visible as a band, and only as a band. | `b10_01_clear_band` |
| `02_insitu_lamp_up.png` | IN-SITU. The lamp tilted up: the beam flares where it crosses the layer and is invisible above and below it. | `b10_02_insitu_lamp_up` |
| `03_insitu_condensation.png` | IN-SITU. No haze; the wall is wet (roughness 0.10, dark) above 1.5 m and dry below — the layer drawn as a line of glint on the rock. | `b10_03_insitu_condensation` |

Guesses: the layer height (1.5 m); band density 0.10; the thermocline shimmer in water is
not rendered (it needs an animated normal, and a still cannot carry it).

## cave-depth/ — what deeper looks like (B11)

Established (ART-DIRECTION §7): one BFS field, six consumers — `worked` climbs (karst → cut
drive → machine ground), iron in frame increases, wetter, darker (rock × (1 − 0.55·depth)),
the plates get younger, the beacon chain thins. "Depth is drawn as darkness, not as
altitude."

| image | intent | tool |
|---|---|---|
| `01_clear_shallow.png` | CLEAR. Shallow: a natural passage, dry rock at full albedo, three of the player's beacons on the floor, no iron. | `b11_01a_clear_shallow` |
| `02_clear_middle.png` | CLEAR. Middle: the cut drive — sets, rails, the bolt line, a survey plate, rock at 0.5 depth. | `b11_01b_clear_middle` |
| `03_clear_deep.png` | CLEAR. Deep: machine ground — the pump chamber, the Bus, the launder, standing water, rock at full depth (×0.45). Its own camera (the same 40 mm three-quarter pulled back to hold a 12 m room); the first version reused the passage camera and put a bolt plate in front of the lens. | `b11_01c_clear_deep` |
| `04_insitu_shallow.png` | IN-SITU. The same shallow place: lamp and three beacon pilots in one frame. | `b11_02a_insitu_shallow` |
| `05_insitu_middle.png` | IN-SITU. Lamp and rails. | `b11_02b_insitu_middle` |
| `06_insitu_deep.png` | IN-SITU. Lamp, wet iron, and the Assayer's winch glow coming round the mouth from the next chamber (2400 K Blackbody, nothing else) — no beacons anywhere. Darker and more lit at once. | `b11_02c_insitu_deep` |
| `07–08_sheet_*_triptych.png` | The two triptychs as sheets. PIL. | `sheets.py` |
| `09_six_cues.png` | The six consumers as a diagram. PIL, no render. | `sheets.py` |

Guesses: the three `dark` values 0 / 0.5 / 1.0 and matching `wet` 0.25 / 0.6 / 0.9. As
rendered: the timber-set sockets are black blocks standing on the wall (a hole needs a
boolean; the block is a stand-in and reads as one in CLEAR, and as a dark patch in-situ,
which is all it needs to do).

## works-drive/ — the worked drive (B12)

Established (ART-DIRECTION §3.3–3.4): the horseshoe 2.4 × 2.4 m, legs to 1.2 m,
half-barrel shot-hole scars at 340 mm parallel to the advance, 1.6 m rounds phase-offset,
flat trammed floor, 300 × 90 mm gutter, rail on sleepers at 600 mm, sockets at 1.2 m, a
bolt line at the springing — all of it a guess chosen to be legible against a 0.77 m agent.
"The agent fits between the rails."

| image | intent | tool |
|---|---|---|
| `01_clear_down_drive.png` | CLEAR. Down the drive with the 1.2 m ruler on the floor, the gauge, the scallops countable per round, the Surveyor between the rails. | `b12_01_clear_down_drive` |
| `02_clear_section_endon.png` | CLEAR. The profile end-on: legs, arch, gutter, the sockets at the springing. | `b12_02_clear_section_endon` |
| `03_insitu_drive_lamp.png` | IN-SITU. The drive by one lamp from behind the machine: the rails running into black, the bolt line catching the pool. `ruins/03_drive_lamp` redone at 960 with the lamp fix and the plates dark. | `b12_03_insitu_drive_lamp` |
| `04_insitu_machine_height.png` | IN-SITU. The same from 0.42 m — what the machine's own camera would see: rails, gutter, and the near wall blown. | `b12_04_insitu_machine_height` |

## works-rails/ — rails polished by use (B13)

Established (ART-DIRECTION §5.6): rail heads mirror-bright from use — two lines in the
floor that return your own lamp straight back; the only specular landmark, the one long
shot the cave allows; bearing steel `(0.52, 0.50, 0.48)` roughness 0.30 metallic 1.

| image | intent | tool |
|---|---|---|
| `01_clear_railhead.png` | CLEAR macro of one rail: rusted web and foot, the bright round head, the sleeper. | `b13_01_clear_railhead` |
| `02_clear_gauge_topdown.png` | CLEAR orthographic from above: the 0.60 m gauge, the 1.2 m ruler beside it, the machine between the rails. | `b13_04_clear_gauge_topdown` |
| `03_insitu_rails_long.png` | IN-SITU. The lamp low along 34 m of drive: two bright lines running out past where the rock has gone black. | `b13_02_insitu_rails_long` |
| `04_insitu_machine_height.png` | IN-SITU. The same from the machine's height. | `b13_03_insitu_machine_height` |

Guesses: the head at roughness 0.16 (brighter than the bearing spec, because it is rubbed
daily); the sleeper timber.

## works-bus/ — the Bus as an object (B14)

Established (ART-DIRECTION §5.6, THE-MACHINERY §8): a bare conductor the length of the
workings on glazed white porcelain insulators — the only clean, white, undamaged material
in the game; it never glows; the water under it does (that is `../found/beacon/07` and the
machinery board's business, not this one).

| image | intent | tool |
|---|---|---|
| `01_clear_conductor.png` | CLEAR. The drive cut open: the conductor along the crown on its row of insulators, the machine under it. | `b14_01_clear_conductor` |
| `02_clear_insulator.png` | CLEAR macro of one insulator: shed, skirt, pin, the plate it hangs from. Glazed white in a wet black place. | `b14_02_clear_insulator` |
| `03_insitu_row.png` | IN-SITU. The lamp raised: the row of white insulators receding — the tell. The conductor itself is barely there. | `b14_03_insitu_row` |

Guesses: insulator form (a two-shed pin type), 2.4 m pitch, hung at 2.02 m; the conductor
alloy gone dark `(0.16, 0.10, 0.06)` metallic 0.7.

## works-plates/ — survey plates (B15)

Established (ART-DIRECTION §6.5): cast index plates at 1.40 m, raised numbers, **no
emission**, legible only with a lamp at close range, deliberately not a Fix source; shallow
ones corroded and half-buried in flowstone, deep ones sharp (§7). `ruins_probe` had them
emissive; every frame here has them dark.

| image | intent | tool |
|---|---|---|
| `01_clear_plate_macro.png` | CLEAR macro: raised numerals, the rim, two bolts, the foundry mark bottom right — legible as an index, unreadable as language, no date. | `b15_01_clear_plate_macro` |
| `02_clear_shallow_deep.png` | CLEAR. A shallow plate (corroded, calcite over its lower half) beside a deep one (clean). The mine got better as it went down. | `b15_02_clear_shallow_deep` |
| `03_insitu_plate_1m.png` | IN-SITU. The head turned to put the lamp on the plate at a metre: readable. | `b15_03_insitu_plate_1m` |
| `04_insitu_lamp_off_it.png` | IN-SITU. Same frame, lamp ahead instead: the plate is gone. It tells you the passage was worked and nothing about where you are. | `b15_04_insitu_lamp_off_it` |

Guesses: the numeral style (`K7-41`, letter–digit–digit–digit: an index, not a date); a
ring-and-triangle foundry mark; 160 × 100 mm.

## works-machine-ground/ — deep machine ground (B16)

Established (ART-DIRECTION §3.4): stopes, the scour, bolt rings, the Bus overhead,
launders, collapsed sets, a pump chamber with the pump still under water — "where the
industry looks most competent". Nothing had been built for it; every part here is a
proposal in the casting language.

| image | intent | tool |
|---|---|---|
| `01_clear_pump_chamber.png` | CLEAR. The chamber cut open: the pump on its plinth half under the water, flywheel, pipework up to the launder, the bolt ring at the springing, the Bus across the crown, rails in through the mouth with one set down. | `b16_01_clear_pump_chamber` |
| `02_insitu_one_lamp.png` | IN-SITU. The same by one lamp: wet iron and water, and most of the plant not there. | `b16_02_insitu_one_lamp` |
| `03_insitu_winch_glow.png` | IN-SITU. The same with the Assayer winding in the next chamber: 2400 K round the mouth, the lamp's white in front — the deep register's two sources in one frame. | `b16_03_insitu_winch_glow` |

Guesses: everything about the pump (a horizontal barrel with a flywheel), the launder on
posts, the 18-bolt ring; the water at 0.30 m. As rendered: under the CLEAR key the cast
iron `(0.075, 0.038, 0.021)` reads terracotta — the spec's hue is orange by ratio (R/B =
3.6) and a bright flat key shows it; under a lamp in-situ the same material is near-black.
If the CLEAR sheets are shown to anyone, say so; do not desaturate the spec to fix a
studio artefact.

## works-junction/ — a junction in rock (B17, not in the inventory)

Every teaching stop underground (CAVE-BLOCKS §9, `python -m phase1 --teach`) happens at
a decision point, and the inventory drew the junction only on the surface course. This is
the same atom in the cave: a crosscut leaving a drive at right angles.

| image | intent | tool |
|---|---|---|
| `01_clear_crosscut.png` | CLEAR. The drive cut open, the crosscut opening in its far wall, the machine at the choice. | `b17_01_clear_crosscut` |
| `02_insitu_crosscut.png` | IN-SITU. The machine stopped at the junction with its head turned into the crosscut, the lamp showing it one way and not the other. The stop is a question. | `b17_02_insitu_crosscut` |

Guesses: that a crosscut is a second drive of the same profile punched through the first;
the whole concept.

---

## What the renders taught, and what they cost

- **Per-frame cost.** Alone on the machine an in-situ frame is 68 s at 960x600, 40 spp
  (`_logs/smoke.txt`). With the other boards rendering at the same time (nine Blender
  processes on 16 threads at one point) the same frame took 190-320 s; the numbers in the
  batch logs are wall time under that contention, not the cost of the scene.
- **Volume stepping.** The probe originally turned on fine volume stepping (rate 2.0, 192
  steps) whenever any volume existed, which the resting fog always does; that triples a
  frame for no visible gain. Only the local volumes (silt plume, water body, haze band) buy
  it now.
- **The rock under flat light.** `rock()` puts its fracture (voronoi) term into the bump
  only, so under the CLEAR key the walls read as bedding noise - smoke, not stone. Under a
  raking lamp the bump carries it. Left as is: the CLEAR views are references, and the
  direction spends its detail budget at 10 m under the lamp (ART-DIRECTION 3.6). A
  colour-side crack term (voronoi edge darkening) is the fix if the references need to
  stand alone.
- **Cutaways need culling.** A bisected room keeps every loose prop that stood in the
  removed half - bolt plates, posts, rubble - hanging in the air in front of the camera.
  `cull()` removes them; the shaft and chamber cutaways did not need it, machine ground did.

## Design problems found (not art problems)

1. **The Hauler's size** (B2): CHASSIS-TIMING makes it 4.0 cells = 2.4 m across;
   `agent_model` builds it 0.90 x 0.32 m. `06_clear_hauler_crawl` shows the model fitting
   a crawl with room to spare, which is the opposite of the rule the class exists for.
   Render the model, flag it, let the designer pick.
2. **The shaft's size** (B1): this board's aven is 1.7 m radius (from `p2_env`); the
   surface board's shaft is 2 x 2.4 m. One number, two guesses; reconcile before either
   becomes geometry.
3. **A chamber with plant needs a taller ceiling than its passages** (B3, B16): the pump
   chamber here is 6.5 m, the Assayer needs >= 8 m (ART-DIRECTION 5.5). Nothing enforces it
   yet; it is a `blindside-gen` rule.
4. **Sockets, joints and spall are stand-ins** (B9, B12): carved recesses need booleans or
   a displacement mask on the drive mesh; boxes and slots are what a probe can do.

## Every guess in this board, in one list

0.6 m per cell (inherited, stated nowhere). The CLEAR rig (grey 0.45 at 1.0, one 3 m key at
45 deg, AgX base) and every exposure lift in a CLEAR frame. The four width classes in metres.
The 8 m chamber ceiling. The landing plate and the sky disc. The water volume's scatter and
absorption, the floor's 4 deg fall, the 1.1 m waterline in the flooded drive. The Swimmer's
lamp (its default loadout has none). The silt plume's shape. The six swatch settings and the
two in-situ rock-type settings. The timber set dimensions and material. Joint slots. The
layer height 1.5 m and band density. The three depth scalars. The rail head at roughness
0.16. The insulator form, pitch and height; the conductor alloy. The plate text, size and
foundry mark. Everything in machine ground. The crosscut (B17). The beacon's point light
(1.5 W) so its pilot lights something.
