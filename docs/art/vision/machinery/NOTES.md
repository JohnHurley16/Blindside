# Vision board — the ancient machinery

The Assayer in every state of its 75-second cycle, its two siblings (the Haulage, the
Bus), the download pose, and a spent machine. One line of intent per image, what made it,
what it proposes against what the fiction already says, and every guess.

Everything here was rendered by `machinery_probe.py` (Blender 5.2, Cycles CPU, 40 spp,
AgX) and composited by `machinery_sheets.py` (PIL). `machinery_batch.sh` re-renders
the lot; both scripts are beside the images. Nothing modifies `agent_model/`, `phase1/`
or `phase2/`; the probe re-applies the three `agent_model` fixes at runtime (lamp
re-aimed `Euler((0,-pi/2,0))` and tilted 8-10 deg down, lamp white `(1.00,0.98,0.95)`,
emissives BONE at strength 3, no cyan anywhere, sonar bar dark because it is not pinging).

**Two rigs, so a concept is shown before its mood.**

- **CLEAR** — neutral grey world (0.30) at strength 1.0, one soft area key 45 deg high
  whose power scales with the square of its distance (110 W at 2.5 m), AgX Base
  Contrast, a grey ground ruled at the 1.2 m industrial module with the 0.6 m rail gauge
  as two finer lines. For enclosed drives, neutral area lights hung at the crown instead
  of a sky. **Not the game.** A concept artist's studio so the thing can be seen.
- **IN SITU** — world background 0, resting silt 0.010-0.016, and only the sources the
  fiction supplies: the visiting machine's white work lamp, its running lights at
  strength 3 in BONE, the Assayer's two hot points at 1900 K -> 2400 K -> 4000 K from a
  Blackbody node (materials) or its numeric equivalent (lights), the Haulage's own lamp,
  the Bus corona on the water. Nine-tenths black is the direction for the match; the board
  frames were composed so that the lit tenth contains the concept.

The scale is 0.6 m/cell (inherited; stated nowhere in the repo). The visiting machine is a
Surveyor (0.77 m long, 0.57 m standing), pale shell over graphite, wear 0.45.

---

## What is established vs what is proposed

**Established (THE-MACHINERY.md 1-3, 6, 8; ART-DIRECTION.md 5):** the cell dimensions of
footing, mast, boom, ribs, counterweight, hammer ring, bolt ring; the 75 s cycle with its
54/3/5/9/4 split; the 36 deg index step; the header tank and the water drive; the drip;
the nine clicks and the tank drawing down one ninth per click; two hot points (winch head
beacon, anvil floor light) at 1900 -> 2400 K and 4000 K at the fire; the three ages of
iron and their numbers; the de-silted scour within ~9 cells; the Haulage as an ore train
on a fixed circuit with mirror-bright rail heads; the Bus as a bare conductor on white
porcelain that never glows while the water under it does; the download as head-down
contact with the rock for 80 s; a spent machine as a machine that has stopped.

**Proposed here (every one a guess until a designer says yes):**

1. **The hub IS the anvil.** THE-MACHINERY never says what the hammer lands on. Here the
   footing hub is a hex block 1.6 m across with a bearing-steel strike face; the drip lands
   on that face and keeps one wet patch on it.
2. **The hammer's travel is 3.5 m, not 5.04 m.** With the boom's slew ring at 5.4 m (9
   cells) and the anvil face at 1.05 m, a ring that rides the mast cannot pass the boom
   root. The schematic lets the hammer climb 8.4 cells *through* the boom's height. A
   physical build has to choose: the slew ring at the mast head (the boom above the
   hammer's whole travel) or a 3.5 m drop (~56 kJ at 1.6 t rather than 81). **Design
   problem, not an art one; see the list at the end.**
3. **The mechanism, dressed:** a ratchet track of bearing-steel teeth on the +X flat of the
   mast; a winch drum and brake band at the mast head with a small water-motor casing
   beside it; a chain over a sheave to a pawl housing on the hammer; three bolted flanges
   (a mast this tall was shipped in sections); a ladder on the -X flat; stays from the mast
   head to the boom; the counterweight's mass box. None of it is in the doc; all of it is
   the casting language (fillets, ribs, draft, parting lines) that 5.2 asks for.
4. **The sight glass.** The tank is an opaque cylinder; the countdown *as a falling water
   level* is invisible unless the level shows. A glass tube on the +X face of the tank,
   1.8 m tall, with the water column drawn at `tank_fill`. Cheap, legible from the floor,
   and it is what a real header tank has.
5. **The tank at 3 m on a -Y bracket, fed by a rising main that goes up into the dark.**
   THE-MACHINERY 7 says the water that drowned the mine fills the tank. The feed pipe here
   climbs out of frame toward the workings above; the downpipe runs to the anvil's drip
   joint and a second pipe to the motor at the winch. Where the tank physically sits is a
   guess.
6. **The index system:** raised "K 14" on the anvil, "K 14 · 2" on the hammer, a round
   foundry mark with one bar. Legible as an index, unreadable as language, no dates. The
   glyph style is a guess.
7. **The winch emits light at all** (inherited from ART-DIRECTION 5.4, which inherited it
   from the earlier passes; THE-MACHINERY never says the winch glows). The brake band is the
   emitter at the head; a thin ring on the anvil face is the emitter at the foot at a third
   the strength. Click n of 9 is `1900 + 500·n/9` K at `n/9` of full output; the strike is
   4000 K at ~4x. The lights are point sources beside the emitters, not inside the mast.
8. **The old service platform** (the bolt ring): eight stanchions at r 2.04 m with four
   of eight grating bays left.
9. **The scour as material:** a radial blend from fresh-fractured voronoi facets (albedo
   to 0.42, rough) at r < 5.4 m to bedded silt outside, over 1.6 m with a noise wobble so
   there is no line; angular spall inside, rounded rubble outside.
10. **The lobe as a decal:** the last firing's lethal wedge (+-40 deg about the aim, 1.9
    to 5.4 m) drawn as a fractionally paler patch of floor where the fines were shaken off.
    Never a glow. It is subtle by design and may be too subtle; that is a knob.
11. **The chamber:** radius 10.5 m, crown ~11.5 m, so a 6.6 m mast has air above it
    (ART-DIRECTION 5.5's rule, which nobody has agreed to).
12. **The Haulage's form:** a squat water-motor locomotive (a Pelton casing on its flank, no
    chimney, a rising-main inlet) on a 1.4 m cast frame, one lamp in a cast housing on the
    nose at 2400 K, three tipping tubs 1.20 x 0.64 m (one module long, one gauge wide),
    greased axleboxes, bright tyre treads, on a drive that curves at 11 m radius. Every
    number is a guess; the doc gives it a circuit, a line hazard, a ride, and a sound.
13. **The Bus's form:** a 30 mm conductor at the crown (z 2.32 m) on glazed white porcelain
    insulators every 2.4 m on cast brackets, one junction box on the wall; the live sump's
    corona at 2100 K as a faint emission in the water surface strongest under the
    conductor's line, plus one weak point light so the corona can light the walls (a
    rendering cheat, declared).
14. **The beacon:** 230 x 60 mm cast tube, weighted base, WARM_DIM pilot at strength 6, a
    bright band standing in for retroreflective sheeting (Cycles has no retroreflector).
15. **The download pose:** a play-bow — body dropped and pitched 24 deg nose-down, front
    legs folded, tilt limit relaxed so the head folds to the floor, lamp OFF while it
    listens (THE-MACHINERY says only "head down, hard against the floor"; the lamp is my
    addition — a listening machine with its lamp on is lighting nothing it needs).
16. **The spent bearing:** boom parked at 323 deg (eight index steps from 35), hammer on
    the anvil, tank at zero, no drip, no wet patch.
17. **The slew frame** exaggerates 36 deg into one frame of full-shutter motion blur so a
    still can show movement; in the game it is 36 deg over 3 s and the bright race is the
    tell.
18. The CLEAR and interior rigs, all camera positions, and the fog values.

---

## Images

Paths are relative to `docs/art/vision/machinery/`. Underscore-prefixed files are
intermediates that `machinery_sheets.py` composites; the numbered files are the board.
Tool: **P** = machinery_probe.py (Blender), **S** = machinery_sheets.py (PIL over P frames).

### assayer-dormant — the Assayer, dormant (54 s of 75)

| image | intent | tool |
|---|---|---|
| `01_clear_elevation.png` | The whole machine at once, CLEAR, three-quarter from floor level: 6.6 m hex mast on the 3.1 m tripod footing, boom at 35 deg, hammer on the anvil, tank and sight glass, ladder, winch head; a Surveyor at the footing for scale ("the dog stands to the top of the footing hub"). | P |
| `02_clear_plan.png` | Orthographic plan on the ruled ground: footing legs at 120 deg, boom 4.2 m long, counterweight, the bolt ring at r 2.04 m, the tank on -Y. The layout settled once. | P |
| `03_clear_footing.png` | The footing, anvil and hammer at rest at machine height: splayed legs with web ribs, pads with four bolts, tie rods, the hex anvil with its raised "K 14", the wet patch and ripple of the drip. | P |
| `04_clear_bearing_boom.png` | The slew ring and its bright race, the boom root, ribs and the ten transducer cans, the stays, the counterweight. The one part that still turns. | P |
| `05_clear_tank_sightglass.png` | The header tank on its bracket, the SIGHT GLASS (proposal 4) full, the feed pipe going up, the downpipe to the drip joint. The power supply, and the countdown's second clock. | P |
| `06_insitu_lamp.png` | In situ: 6.6 m of black shape resolving out of one machine's beam from 6 m, taller than the beam is wide, emitting nothing. The dormant read. | P |
| `07_insitu_drip.png` | In situ, macro: one drip every two seconds onto the anvil, in the visitor's lamp — the entire dormant performance. A machine that emits nothing while water runs off it reads as finished, not menacing. | P |

### assayer-winding — the wind, nine clicks

| image | intent | tool |
|---|---|---|
| `01_clear_click6.png` | CLEAR with the two hot points on at click 6 so the mechanism reads: hammer 6/9 up the track, the chain taut over the sheave, the brake band hot, the anvil ring hot at a third, the sight glass at 4/9. | P |
| `02_clear_clicks_strip.png` | Clicks 1 / 5 / 9 side by side under CLEAR: colour 1956 -> 2178 -> 2400 K, output 1/9 -> 5/9 -> 9/9, hammer rising, tank falling. Countable. | S |
| `03_insitu_click1.png` `04_insitu_click5.png` `05_insitu_click9.png` | The same three clicks in the game's light from the floor 8 m off: the winch head is a beacon, the anvil lights the ground the agents stand on, the mast is lit only by its own hot points. | P |
| `06_insitu_clicks_strip.png` | The three in-situ clicks as one strip: the warning IS the light, the light IS the countdown. | S |
| `07_insitu_wide_click8.png` | Wide in situ at click 8, the visitor standing off-axis: how much of a 20 m chamber the two hot points actually light (the head lifts the frame; the anvil lights the floor). | P |
| `08_insitu_next_chamber.png` | From behind a rock buttress with the mast hidden: the light comes round the corner, the mast does not. Vertical landmark presence is bought with light, not geometry (ART-DIRECTION 5.5). | P |

### assayer-firing — the fire and the lethal four seconds

| image | intent | tool |
|---|---|---|
| `01_clear_strike.png` | CLEAR at the instant of the strike: hammer on the anvil, both hot points at 4000 K, a low ring of fines off the anvil face. The only white light in the game, shown lit. | P |
| `02_insitu_strike_machine_height.png` | The strike from a machine's height at 9 cells (5.4 m) on the axis: the flash, the visitor's own shadow thrown outward, the chamber seen whole for one frame. | P |
| `03_insitu_decay_2s_lobe.png` | Two seconds later: the hot points cooling toward 2400 K, the visitor's lamp back on, the last firing's lobe drawn as a paler wedge in the silt only (proposal 10). The shock was in the ground; nothing is in the air. | P |
| `04_insitu_strike_wide.png` | The strike from across the chamber, low: what a rival two rooms away would see for one frame. | P |

### assayer-scour — the scour

| image | intent | tool |
|---|---|---|
| `01_clear_topdown.png` | Orthographic top-down of the footing and 7 m of floor, lit from inside the chamber: bare angular fresh-fractured floor inside ~9 cells, silt and rounded rubble outside, no boundary drawn anywhere. | P |
| `02_clear_oblique.png` | The same from the floor under a raking studio light: the rock inside the scour visibly newer than the machine standing on it. Display tints the scour; the world de-silts it. | P |
| `03_insitu_lamp_edge.png` | In situ: the visitor's lamp across the scour edge — the fines stop where the shaking starts, and a player reads "nothing settles here" forty seconds before finding out why. | P |

### assayer-iron — three ages of iron

| image | intent | tool |
|---|---|---|
| `01_clear_three_ages.png` | Material study: one cast knee bracket (base, upright, fillet web, boss, parting line) and a sphere in each of the three materials, labelled with the 5.2 numbers: cast iron wet a century / bearing steel still working / graphitised below the waterline. No paint anywhere. | S |
| `02_clear_casting_macro.png` | Macro of the anvil's flat: the raised index "K 14", the foundry mark, the parting line, the draft. Legible as an index system, unreadable as language, no dates. | P |
| `03_clear_waterline.png` | A footing leg and pad standing in water: graphitised black below the line, a 0.12 m mineral crust above it, ordinary cast iron above that — one material swap on a Z threshold, intact in silhouette and dead in surface. | P |
| `04_insitu_bearing_shine.png` | In situ: the visitor's lamp tilted up the mast and the slew race catching it while everything around it is matte. You read "still running" off the shine before anything moves. | P |

### sibling-haulage — the Haulage

| image | intent | tool |
|---|---|---|
| `01_clear_side_elevation.png` | Orthographic side elevation on the studio rails: the water-motor locomotive and three tubs on the 0.6 m gauge with a Surveyor beside them — the agent fits between the rails and can ride a tub. Every dimension a proposal (12). | P |
| `02_clear_threequarter.png` | Three-quarter CLEAR of the same train: the Pelton casing, the drum, the lamp housing on the nose, the couplings, ore in the middle tub. | P |
| `03_clear_bearing_detail.png` | Macro of a tub's axlebox: greased, wet, the bright tyre tread and the polished rail head under it. The same castings as the Assayer, but greased. | P |
| `04_insitu_round_the_curve.png` | In situ: the train's own lamp coming round a curve of drive toward the camera, the rail heads lit ahead of it, the machine itself not yet visible. The sound arrives before the glow; the glow arrives before the train. | P |
| `05_insitu_riding.png` | In situ: a Surveyor riding the second tub in the dark behind the locomotive's lamp — real distance with no odometry error and no noise of its own. | P |
| `06_insitu_rails_return.png` | In situ: a machine's lamp low along the rails — two bright lines running into black, the only specular landmark in the cave, the one long shot the cave allows. | P |

### sibling-bus-live — the Bus, dead and live

| image | intent | tool |
|---|---|---|
| `03_clear_dead_live_pair.png` | Interior CLEAR pair, same drive, same sump: dead, the water is a mirror; live, the water glows faintly at 2100 K under the conductor's line and the conductor never does. The corona's colour and strength are proposals (13). | S |
| `04_clear_insulator_detail.png` | Macro of one glazed white porcelain insulator on its cast bracket with the bare conductor through it: the only clean, white, undamaged material in the game — the tell. | P |
| `05_insitu_corona_from_bank.png` | In situ from the dry bank, the visitor's lamp off: the corona on the sump is the only light — a live flooded section forty cells from the conductor is not safe, and this is how it looks. | P |
| `06_insitu_beacon_in_sump.png` | In situ: one beacon standing in the live water and one on the bank, both pilots lit, pixel-identical. The wet one lies; nothing in the picture can tell you which. | P |

### download — the download moment

| image | intent | tool |
|---|---|---|
| `01_clear_pose_footing.png` | CLEAR: the pose at the footing — the machine stopped, head folded to the rock, still, the boom axis marked on the floor as a studio annotation (the axis decides which crescent of the room downloads fast and doses hard). | P |
| `02_clear_pose_macro.png` | Macro of the contact: the face plate on the rock, the body low and nose-down, the lamp reflector dark. "I am listening to something that is not alive." | P |
| `03_clear_pose_junction_box.png` | The same pose at a Bus junction box in a drive: the station family — the prior industry's control surfaces — is what makes a discovery a transaction and not a pickup. | P |
| `04_insitu_pose_during_wind.png` | In situ: the pose held through click 5 of the wind at 5.6 m on the axis — the two hot points, the machine a dark shape, its running lights the only thing on it. Coupling is the rate and the dose. | P |
| `05_insitu_pose_anvil_glow.png` | In situ, low and close at click 8: the anvil ring lighting the floor under a listening machine's chin. | P |
| `06_insitu_step_out.png` | In situ: the step-out — the machine walking off the axis at click 8 with its lamp on, the dwell paused. Stand and eat a firing, or walk twenty seconds a cycle; neither dominates. | P |

### spent — a spent machine as a found thing

| image | intent | tool |
|---|---|---|
| `03_clear_pair.png` | CLEAR pair, same camera: WORKING (hammer wound, tank full, the drip, a dull glow at the drum) / SPENT (boom parked on the last bearing, hammer on the anvil, tank drained, anvil dry, no glow ever again). | S |
| `04_insitu_spent_lamp.png` | In situ: the spent machine in a visitor's lamp — the same frame as `assayer-dormant/06` and a different answer. Someone beat you to it, readable from across the chamber, permanently. | P |

### assayer-slew — the slew (54-57 s), which the inventory missed

| image | intent | tool |
|---|---|---|
| `01_clear_index_plan.png` | Two plan views blended: the boom at 41.5 deg (this cycle) and 5.5 deg (next). -36 deg per cycle, always the same direction, learnable from two slews. | S |
| `02_insitu_blur.png` | In situ: the arm mid-swing under a visitor's lamp tilted up — motion-blurred (exaggerated, proposal 17), the bright race the only thing that catches. Nothing emits; horizontal rotation is the tell. | P |

### assayer-chamber — the chamber rule, which the inventory missed

| image | intent | tool |
|---|---|---|
| `01_clear_cutaway.png` | Cutaway (camera near-clip) of the 10.5 m chamber with the 6.6 m mast under an ~11 m crown and a 2.4 x 2.4 m drive mouth on the far wall for the height comparison. The generator rule ART-DIRECTION 5.5 needs. | P |

### assayer-cycle — the 75 seconds on one sheet

| image | intent | tool |
|---|---|---|
| `01_cycle_sheet.png` | Eight in-situ frames from this board on the cycle's timeline: listening, the slew, locked, clicks 1/5/9, the fire, the decay. One sheet a designer can read in a minute. | S |

---

## Guesses beyond the proposals above

- 0.6 m/cell, inherited and stated nowhere.
- The visiting Surveyor's wear (0.45), its pale-over-graphite scheme and BONE emissives at 3
  (ART-DIRECTION 4.3's recommendation, not a ruling).
- Lamp power 600 W in Blender watts, chosen to hit the 2.2 ratios at 40 spp; it does not
  survive the move to Godot and should not be quoted.
- The fog values (0.010-0.016) as resting silt; the strike frames use the same fog, so
  the flash's glow in the air is silt, not a bloom.
- Hot-point powers: winch 900-1100 W x n/9 (CLEAR / in situ), anvil a ninth each of three
  points, strike 3600-4400 W. Ratios, not absolutes.
- The corona's 40 W helper light.
- The dust ring at the strike: forty translucent puffs 0.9-1.7 m out — the one thing the
  strike throws into the air. THE-MACHINERY says the shock is in the ground; the fines on
  the anvil face are the only thing that can jump.
- The haulage lamp's 2400 K and 900 W spot at 62 deg.
- The drive curve (11 m radius, 38 deg) and its rounds phase-offset per 1.6 m.

## Design problems found (not art problems)

1. **The hammer cannot travel 8.4 cells on a mast whose boom sits at 9 cells.** THE-MACHINERY
   2.1 and ART-DIRECTION 5.1 both let the ring climb through the boom's height. A physical
   build must either put the slew ring above the hammer's top of travel (boom at the mast
   head, z = 11 cells) or accept a 3.5 m drop. Every render here shows the 3.5 m version.
   The 81 kJ in 5.1 becomes ~56 kJ, still a seismic weight drop; the beat does not change.
2. **The winch light has no source in the fiction.** The whole in-situ half of this board
   rests on 5.4's inherited assumption that the brake band glows. If the designer wants a
   machine that emits nothing at all, the wind is heard and not seen, and every "next
   chamber" image on this board is wrong.
3. **The tank cannot both fill in 75 s and drive the wind unless it drains in 9 s.** THE-
   MACHINERY 7 has the period as the fill time; 5.4 has the tank drawing down a ninth per
   click. That is one tank filling for 66 s and emptying for 9 s — consistent, but it means
   the sight glass is *rising* for 88% of the cycle, which is a second slow countdown a
   viewer can read. Worth deciding whether that is wanted.
4. **A spoofed beacon in a live sump is only pixel-identical if the corona does not light
   it differently.** Here the wet beacon stands in faintly self-lit water and the dry one
   does not; at close range the water's glow on the tube is a tell the design forbids. The
   corona must be weak enough never to light a beacon, or the rule that a lie has no tell
   needs a carve-out for the Bus.
5. **The Haulage needs its own chamber rule.** A 1.4 m locomotive on a 2.4 m drive leaves
   0.5 m either side; the agent "steps off the rail" into the gutter or a socket. The
   drive geometry the direction already specifies (gutter 0.3 m, sockets at 1.2 m) makes
   stepping off the line a real, cramped act, which is good; but a Hauler at 0.32 m wide
   cannot pass a moving train in a 2.4 m drive at all.
