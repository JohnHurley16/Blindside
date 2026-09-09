# Vision board — WHAT IS FOUND, and THE MACHINE'S OWN VIEW

Group: deposits, wrecks, beacons, discoveries (ART-DIRECTION §6); the point cloud as art,
the map the player sees, world against belief, enter-agent-perception (ART-DIRECTION §8,
SPECTATOR-DISPLAY §6.4/§6.7). Rendered 2026-09-08.

Every concept has at least one CLEAR view (a studio: grey world at strength 1.0, one big soft
key from 45° high, AgX — the thing can be *seen*; not the game) and at least one IN-SITU view
(world background 0; if a pixel is lit, a fixture in frame is lighting it). Show the thing
first, the mood second.

Every render re-applies the three `agent_model` fixes ART-DIRECTION asks for, at runtime and
without touching `agent_model/`: the head lamp re-aimed to +X and tilted 8–10° down, the lamp
white for every team, identity emissives at strength ≤ 3 in BONE (player) / EMBER (rival),
never cyan. Beacon pilots are WARM_DIM. No red anywhere except the painted E-stop, which is
never emissive. 0.6 m per cell throughout.

**Rendering these again.** All scripts are under `_probes/` and are re-runnable with a Blender
5.2 install (the `.venv` has no `bpy`):

| script | what |
|---|---|
| `_probes/found_common.py` | shared: the two rigs, materials (cast iron, bearing steel, porcelain, retro band, ore), the agent with the fixes, the wreck pose, the head-down pose, the beacon, a talus cone, a working face |
| `_probes/found_probe.py` + `found_batch.sh` | every deposit / wreck / beacon / discovery shot |
| `_probes/cloud_dump.py` | `.venv` Python; runs `phase1.match.sim.Sim(7)` headless to a list of times and writes the belief cloud, trail, pose, beacons and the truth grid/pose to `_probes/data/*.npz` |
| `_probes/cloud_scene.py` + `cloud_batch.sh` | the cloud / gap / perception shots from those dumps |
| `_probes/icons_and_ladder.py` | PIL only: the block-icon mock, the nine-pixel ladder, the belief-inset crop |
| `python -m phase1 --snap=-3,143,341,480 --snap-dir map` and `--teach --snap map/teach` | the spectator and teach-stop pictures |

All images are 960 px wide or more (Blender frames 960×600 at 40 spp, Cycles CPU, denoised;
spectator frames 2000×1125).

---

## deposit/ — a worked face and the muck pile under it (E1)

ART-DIRECTION §6.1 and THE-MACHINERY §7: a deposit is a face that was being worked and the
talus at its foot, spread over `DEPOSIT_RADIUS = 12` cells = 7.2 m; the ore is redder, denser,
glassier and more specular **only when lit**; loading leaves a scar and a spoil pile.
**This shape is decision 4 in ART-DIRECTION's list and is still unanswered; everything here is
a proposal for that shape.** The substance stays unnamed.

| image | intent | tool |
|---|---|---|
| `01_clear_face.png` | CLEAR. The whole object: a fresh-cut face with nine drill holes (three charged, wires hanging), the talus cone of broken stock at its foot, a Surveyor at the pile with its belly bay open. The heap is big and diffuse, not a point. | found_probe `dep_clear_face` |
| `02_clear_after.png` | CLEAR. The same face after a load: a bite of fresh, un-silted, brighter rock in the face, and a new pile of fines beside the cone in the same fresh rock — visibly newer than the heap it came from. A rival can see this has been worked, with no UI. | `dep_clear_after` |
| `03_clear_swatch_lit.png` | CLEAR swatch under one hard lamp: country rock (left) and ore (right). The ore is redder, glossier, and throws a specular highlight; the country rock returns nothing. | `dep_clear_swatch_lit` |
| `04_clear_swatch_unlit.png` | The same two slabs under the flat studio grey only: one warm family, the difference nearly gone. You find ore by shining a light at it — a thing only `optical` does. | `dep_clear_swatch_unlit` |
| `05_clear_plan.png` | CLEAR plan, orthographic from above, the 1.2 m module painted on the floor: the cone's spread against the grid, the machine for scale. (The painted grid sinks into the displaced floor in places — cosmetic.) | `dep_clear_plan` |
| `06_situ_find.png` | IN-SITU. The machine's own lamp finds the pile in a black chamber. The machine is between the viewer and its pool (the §2.4 camera rule) and the ore glints where nothing else does. | `dep_situ_find` |
| `07_situ_loading.png` | IN-SITU. Loading: the bay open, stock going in, the lamp on the face two metres ahead — the thirty seconds during which the whole cave can hear it. | `dep_situ_loading` |
| `08_situ_worked.png` | IN-SITU. The rival arrives later; its lamp finds the scar and the new spoil. The information channel produced entirely by art. | `dep_situ_worked` |

Guesses: the face is a displaced slab 8.5 × 4.6 m with holes at ~0.9 m spacing (no source);
the cone is 3.6 m radius × 1.15 m high (angle of repose ≈ 18°, shallower than real muck to
keep the machine visible); ore = the same `rock()` shader with a tighter voronoi, a redder
ramp, roughness 0.27–0.52 and a light coat — numbers chosen by eye, not measured; the scar is
a proud patch (a recess needs a boolean); the spoil is in the scar's rock, not the ore's.

## wreck/ — the best asset in the game (E2)

ART-DIRECTION §6.2. The pose is the whole read: belly on the rock, rolled 40° so the underside
shows, one leg gone below the knee, the compute hatch shed onto the floor, the cargo hatch
sprung and ore spilled, every emissive dead, the recovery handle the only clean thing.
Built exactly as `av_probe.py`'s third attempt (the one that read as fallen), plus the spill.

| image | intent | tool |
|---|---|---|
| `01_clear_front.png` | CLEAR three-quarter from the rolled-down side: the roll, the splayed feet, the shed panel, the spill, the rail gauge on the floor for scale. Studio: the design can be read. | found_probe `wreck_clear_front` |
| `02_clear_back.png` | CLEAR reverse three-quarter, from the rolled-up side: the underside — which you never see on a working machine — the missing tibia, the sprung hatch, the spilled stock. | `wreck_clear_back` |
| `03_clear_handle.png` | CLEAR macro. The recovery handle on its two posts, rubber-coated, unbent, unmuddied — the part designed to survive this, and what the next machine grabs. | `wreck_clear_handle` |
| `04_situ_found.png` | IN-SITU. A passing machine's lamp finds it at 1.7 m (av_10's frame, with the spill). Nothing else in frame emits: a hole where two lights should be. | `wreck_situ_found` |
| `05_situ_6m.png` | IN-SITU. A rival's lamp finds it at 6 m; the rival is the silhouette at the frame edge, the wreck a low shape in the far half of the pool. With retroreflective running lights (decision 1) it would *appear* here all at once; rendered as built, strips dead. | `wreck_situ_6m` |
| `06_situ_pair.png` | IN-SITU. A healthy machine and a wreck side by side, backlit by a third machine, for the ladder. | `wreck_situ_pair` |
| `07_situ_recovery.png` | IN-SITU. The recovery: a machine standing over the corpse, head down, doing nothing visible for a long time, its own lamp on the wreck under its chin. What is being taken is invisible; no glowing brain. | `wreck_situ_recovery` |
| `08_nine_pixel.png` | `06` resampled down the display's ladder (machine 90 → 9 px): a flat thing where a tall thing should be, which is what the display's `X` means. | icons_and_ladder (PIL) |

Guesses: the spill (14 lumps within 0.3 m of the belly) and where it lands; the head-down
recovery pose (the tilt bone is limited to ±0.6 rad, so the head cannot touch the rock as
built — the pose is as far down as the rig goes and the body is crouched 0.12 m). Needs, as
before: `WreckSpec` with roll *and* per-leg pose, a hull ground-contact solve, `shed`,
`emissive_scale`, `spill`.

## beacon/ — the only thing the player makes (E3)

ART-DIRECTION §6.3: a 230 × 60 mm cast tube, self-righting on a weighted base, one warm pilot
at the top (WARM_DIM #7A6650, never team-coloured), a retroreflective band; useful to 3.6 m,
visible to ~20 m; a spoofed one is pixel-identical. There was no beacon object anywhere in the
repo; `found_common.beacon()` is the first.

| image | intent | tool |
|---|---|---|
| `01_clear_product.png` | CLEAR product shot on a bench with a 24 mm coin and a 100 mm bar: the base, the tube, the band, the cap, the pilot. Hand-scale. | found_probe `bcn_clear_product` |
| `02_clear_rack.png` | CLEAR macro of the rack as `agent_model` builds it: four deck tubes with caps and the chute at the tail. The caps are the inventory readout (they go dark one at a time — spectator vocabulary only). | `bcn_clear_rack` |
| `03_clear_drop.png` | CLEAR. The moment of a drop: one beacon mid-fall behind the chute, one already down and righted 1.2 m back, the machine walking on. | `bcn_clear_drop` |
| `04_situ_chain.png` | IN-SITU. The direction's most beautiful image: four pilots receding into black behind a walking machine, the nearest catching the lamp on its band, the rest points. One of them may be lying. | `bcn_situ_chain` |
| `05_situ_range.png` | IN-SITU. Useful to 3.6 m, visible to 20 m: the near beacon's body reads in the lamp, the far one is a pilot and nothing else. | `bcn_situ_range` |
| `06_situ_twins.png` | IN-SITU. An honest beacon and a spoofed one in the same lamp: the same function, the same arguments, pixel-identical. No tell. Not a subtle one. | `bcn_situ_twins` |
| `07_situ_sump.png` | IN-SITU, cross-ref THE BUS (C7). A beacon left in a live sump: the conductor overhead on white porcelain, the water faintly self-lit (a corona), the pilot still lit. It comes back wrong rather than dead, and keeps lying. | `bcn_situ_sump` |

Guesses: the body is cast iron (the same material as the works, so a beacon reads as a small
piece of the industry the player carries); the pilot is a 14 mm sphere at emission 6 plus a
0.35 W point so it is *seen* and lights nothing; the retro band is a glossy metallic coat
(Cycles has no retroreflector — it returns a lamp near the camera axis, which is the case that
matters); the corona is 2100 K at 0.012 linear emission on a glass surface (proposal); the
self-righting base is a 40 mm taper (proposal).

## discovery/ — a transaction, not an object (E4)

ART-DIRECTION §6.4 / THE-MACHINERY §6: a discovery is the plant's own control software,
obtained by putting a transducer on the rock. Art makes three things, none of them a pickup:
the STATION, the POSE, the MARK that it is spent; the item's own representation is a block
icon in the editor. **This is decision 5 in ART-DIRECTION's list; everything here is the
proposed answer.**

| image | intent | tool |
|---|---|---|
| `01_clear_stations.png` | CLEAR sheet of four stations in the casting language, with a Surveyor for scale: a junction box on the Bus (porcelain insulators, a bright latch), a rail switch (lever, counterweight, the 0.6 m gauge), a pump (volute, motor, a bright coupling), the Assayer's footing hub. All one idea — the prior industry's control surfaces. | found_probe `disc_clear_stations` |
| `02_clear_pose.png` | CLEAR. The pose at a junction box: head folded down toward the rock, body crouched, still. The same gesture as salvaging a wreck: *I am listening to something that is not alive.* | `disc_clear_pose` |
| `03_block_icons.png` | PIL mock of the editor's item row: hollow predicates, filled actions, two just-found blocks carrying the silhouette of the plant that yielded them. The block's own look is an icon, never a world model. | icons_and_ladder |
| `04_situ_pose.png` | IN-SITU. The same pose in its own lamp, aimed at the rock under its chin; the box above it is barely in the beam; the TONE it broadcasts is a sound and draws nothing. | `disc_situ_pose` |
| `05_situ_spent.png` | IN-SITU, PROPOSAL. The mark that a *small* station is spent: two junction boxes in one lamp, the near one intact, the far one with its cover hanging open on the hinge — somebody knocked here and took the report. Readable from across the passage, permanently, the way a stopped Assayer is (C9). | `disc_situ_spent` |
| `06_situ_rival.png` | IN-SITU. What a rival sees of a download from 5 m: a machine head-down at the footing, still, in the rival's lamp. The most committed, least deniable thing a machine can do. | `disc_situ_rival` |

Guesses: the station family (junction box, switch, pump, footing) and their forms; the
"cover hangs open" spent-mark for stations that have no moving cycle to stop; that the
junction box's part numbers are raised plates with no glyphs (legible as an index, unreadable
as language); the head-down pose limits as above.

## cloud/ — the point cloud as art (F1)

ART-DIRECTION §8.2: hits, not dots — 40–50 mm world-space discs facing back along the return
ray; two classes only (sensed at its scattered z, walked at z = 0); alpha = confidence; old
returns dimmer and never re-registered; a dark-cyan floor decal where count > 0; emission only,
unlit, shadowless; never meshed. "A rug on the floor of the real cave." Data is the real
seed-7 belief from `phase1` (`cloud_dump.py`), not a mock.

| image | intent | tool |
|---|---|---|
| `01_clear_director.png` | Belief only, on black, the display's own attitude (elevation 72°, orthographic) at 2:18: SENSED banks where the walls were pinged, the WALKED rug, the decal under it, the hollow ghost and its 2σ ellipse, the believed trail, ghost diamonds where it recorded its beacons. | cloud_scene `cloud_director`, t=138 |
| `02_clear_low.png` | Belief only, a low orbit near the believed pose: banks of discs read as surfaces because every disc faces the sensor that measured it; the rug is a rug; the ghost stands on it. | `cloud_low`, t=138 |
| `03_clear_macro.png` | Belief only, close, at the direction's 44 mm: each disc a hit facing its sensor; a bank of returns is a surface from any angle with no mesh. | `cloud_macro`, t=138 |
| `04_clear_drift.png` | Belief only, wide, at 5:00: fixes moved everything placed since the epoch and nothing before it — the old corridor and the new one for the same passage, both drawn, no annotation. | `cloud_drift`, t=300 |
| `05_situ_both_rear.png` | IN-SITU, the replay's "both": the real passage lit only by the real lamp at ~35 %, the cloud additive over it at full strength, the ghost 1.5 m from the machine and the tether between them. They never overlap in brightness and never agree in shape. | `both`, t=100 |
| `06_situ_low_t100.png` | Belief only at 1:40, low orbit, early in the match: sparse, mostly walked, a few pinged walls — an honest picture of how little the machine knows. | `cloud_low`, t=100 |

Guesses and flags: **`PointCloud` stores no ray direction** (x, y, z, confidence, t, source);
the disc normal is reconstructed as (believed pose at the point's timestamp → point) from the
belief trail, which is the only origin belief knows — a guess. The sim's cloud is sparse
(1,100–3,900 points in a whole match; 0.35 per cell at 8:00), so the wide frames use 70 mm
discs (`--disc 0.035`) and the drift frame 100 mm so a 960 px board can show them; the macro
is at the true 44 mm. Age dims alpha to 35 % at the start of the match (a guess at the curve).
The floor decal is one quad per occupied 2-cell bin at 25 % WALKED. The ghost is drawn at the
machine's real size, not the display's 2.4-cell glyph (§8.4 says the licence does not transfer).

## map/ — the map the player sees (F2)

Belief only, always: the spectator display's belief inset and the teach window are the only
pictures a policy, a pendant or a bench screen may ever show. These are `phase1`'s own frames.

| image | intent | tool |
|---|---|---|
| `01_cold_open.png` | The cold open, three seconds into the card: the premise in seven lines before the clock starts. | `python -m phase1 --snap=-3` |
| `02_mid_match_223.png` | 2:23, just after the spoof: the truth scene main, ITS MAP in the corner, IT IS WRONG BY 33 CELLS / IT THINKS IT IS WRONG BY 1. The gap as the display draws it. | `--snap 143` |
| `03_freeze_541.png` | 5:41, the near miss: the machinery counting, the machine frozen. | `--snap 341` |
| `04_reveal_800.png` | 8:00, the reveal: truth drawn over belief in one picture, the only time the display does it automatically. | `--snap 480` |
| `05_belief_inset.png` | The 2:23 inset alone, 3×: this and only this is what the machine has. | icons_and_ladder (PIL) |
| `06_teach_stop1.png` | The teach window at stop 1 (0:00, the start): belief only, the rail showing every enabled predicate with its value and the actions as keys; the match clock stopped for the whole of the asking. The picture a pendant on the surface would carry. | `python -m phase1 --teach --snap` |
| `07_teach_stop2.png` | Stop 2 (1:28, *carrying_cargo* rose): the same window with a map in it. | same |

## gap/ — world and belief as one picture (F3)

ART-DIRECTION §8.1/§8.3: "Truth is rendered. Belief is drawn." Three modes; truth is the
layer that gets turned down, never belief.

| image | intent | tool |
|---|---|---|
| `01_clear_gap.png` | The teaching image: the truth passage at CLEAR exposure with its crown cut away, the cloud at full strength over it at the coordinates the agent believes, the machine and its ghost 1.5 m apart, the rope between them. Two registers, one frame. | cloud_scene `gap_clear`, t=100 |
| `02_situ_both.png` | "Both": truth at ~35 %, cloud additive. The ground and the drawing on it. | `both`, t=138 |
| `03_situ_belief_only.png` | "Belief only", the same camera: the live default, because it is what the player is legally allowed to see. The real machine is not drawn; only its ghost is. | `belief_only`, t=138 |
| `04_situ_truth_only.png` | "Truth only", the same camera: the photographic register, full exposure, the lamp and nothing else. | `truth_only`, t=138 |
| `05_situ_reveal.png` | The 8:00 reveal in three dimensions at 5:41: the true wall outline in WARM_DIM over the built map, from the director's attitude, wide. The machine is 66 cells from where it thinks it is. | `reveal`, t=341 |

Guesses: the truth cave is the grid extruded to 4.4 m and displaced (the display's 8-cell
extrusion does not transfer; Phase 3 will have a real heightfield — this is a stand-in); the
tether colour follows `READOUT_RAMP_CELLS`; the "both" exposure is done by scaling the lamp to
35 %, with no desaturation step.

## perception/ — enter-agent-perception (F4)

ROADMAP Phase 5 / ART-DIRECTION §8.3: first person at 0.5 m eye height, the cloud, a lamp
pool, and nothing else.

| image | intent | tool |
|---|---|---|
| `01_clear_truth.png` | What is actually in front of it at 1:40: the passage from the head, the lamp's pool, the near wall blown. Not the game. | cloud_scene `percep_truth`, t=100 |
| `02_situ_both.png` | The mode: the pool at ~40 %, the rug of discs, black. | `percep_both` |
| `03_situ_belief.png` | The discs and nothing else: what the sensor has given it, seen from where it stands. | `percep_belief` |

Open question flagged: the "lamp pool" in this mode is a rendered thing, and `Return::Optical`
carries occupancy, not radiance — so the pool in `02` is the spectator's courtesy, not a thing
the policy sees. Whether enter-agent-perception shows the pool at all needs a ruling.

---

## Every guess, in one place

1. The deposit's shape (face + cone), its dimensions, the ore shader and the scar/spoil forms.
2. The beacon's body (cast iron), base, band, pilot size and light; the corona colour and level.
3. The station family and forms; the open-cover spent mark for small stations; raised blank
   part numbers.
4. The wreck's spill; the head-down pose is as far as the rig's tilt limit allows.
5. The cloud: reconstructed ray directions, board disc sizes larger than the direction's 44 mm
   in wide frames, the age curve, the decal opacity, ghost at real size.
6. The truth cave stand-in (extruded grid, 4.4 m crown); the "both" exposure as a 35 % lamp.
7. The CLEAR rig itself (grey world 0.18, one 3 m key ~1000 W at 45°, AgX medium-high
   contrast) and DAYLIGHT is not used in this group.
8. Beacon pilots are visible to the camera as a point at 20 m only because of a 14 mm emissive
   sphere; a real pilot LED would be smaller and would need bloom to read at that distance.

## Design problems found (not art problems)

1. **The belief cloud is sparse.** Seed 7 produces 172 wall returns in the first 100 s and
   ~3,900 points by 5:41 (0.35 per cell). As oriented 44 mm discs that is a scatter, not a
   survey, in any camera wider than a macro. Either the 3D client draws a bigger disc than the
   direction specifies, or the sensor returns more points, or the decal (the silhouette) is the
   element that carries the map — SPECTATOR-DISPLAY §6.4 already says it is.
2. **`PointCloud` does not store the return direction**, so "a disc facing back along its
   ray" cannot be drawn honestly from the belief object as it stands; it needs one more array
   (or the believed pose at placement time) in Phase 3's `Belief`.
3. **The head cannot touch the rock.** THE-MACHINERY §6 says the transducer goes "hard against
   the floor"; the rig's tilt limit is ±0.6 rad and the head sits 0.3 m up on a crouched body.
   The download pose needs a `head_down` pose in `agent_model`, or a transducer on a foot.
4. **The enter-agent-perception pool** (above): a rendered lamp pool is not a thing the policy
   has.
5. **The teach picture on the surface** is the belief inset; nothing in it distinguishes a
   surface demonstration from a cave one, which is correct — but it means the pendant's screen
   (G2, another group's) must be exactly this frame and never the spectator's truth scene.
