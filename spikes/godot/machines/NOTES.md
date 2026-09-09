# Spike — the machines, out of `agent_model` and into Godot, walking

The machines were the one thing every Godot spike so far had left as a placeholder. This
one takes the model that has been rendering them all along, gets it out of Blender as
glTF, and stands it up in Godot under the game's own lamp.

**The headline: the export works, all four chassis walk, and a machine costs 20–29 k
triangles in two draw calls.** What was lost in the trip is materials — all of them, by
design — and what had to be rebuilt in Godot is ART-DIRECTION §4 in its entirety.

---

## 0. What this is not

An earlier version of this spike started rebuilding the machines procedurally in GDScript,
on the reading that ART-DIRECTION §9's "no hand-modelled asset" applies to them. **It does
not.** §9's rule exists because *a generated cave cannot be unwrapped* — it is a rule about
generated world geometry. A machine is authored content, four of them, changing rarely.
The procedural mesh kit that pass produced (`mk.gd`, ~600 lines: a chamfered box with a
convex-winding fixup, tapered members, actuator drums, bolt rings, louvres, a parabolic
reflector) was **deleted**, and this file records that so nobody rebuilds it.

**Kept from that pass and still in use:** the ART §4 shader design (the four-channel vertex
scheme, the three gravity masks, the team/wear/damage separation), the retroreflective
`light()` function, the lamp rig, the three lighting rigs, the shot harness, and the
Godot-side gait driver. **Binned:** all mesh generation.

---

## 1. How to run it

```sh
# 1. export from Blender (needs Blender 5.2; ~4 min for 18 .glb)
spikes/godot/machines/export.sh

# 2. everything: 23 stills, 5 walk-cycle sequences, 5 contact sheets  (~4 min)
<godot> --path spikes/godot/machines --resolution 1920x1080
#    --  --shots        just the stills
#    --  --seq          just the sequences
#    --  --shot=NAME    one frame
```

`bpy` is **not** pip-installed on this machine, so the export runs through the Blender
application, which `agent_model/run.py` already supports:
`"C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b -P agent_model/run.py -- …`

---

## 2. The export, and the four things that went wrong in it

`agent_model/export_gltf.py` is new; `run.py` gains `--export`, `--export-clip`,
`--export-frames`, `--export-in-place` and `--fps`. **Nothing about what the model IS was
changed** — no geometry, no proportions, no rig, no materials.

The export does five things, in this order, and each one exists because glTF cannot carry
what Blender was using.

1. **Bake the constraints.** `build.py` drives the legs with IK to world-space `FOOT`
   empties and the head with track constraints to a `LOOK` empty. glTF has no constraint
   and no solver, so `nla.bake(visual_keying=True, clear_constraints=True)` resolves the
   whole pose to plain FK rotations on every bone of every frame. Without this the clip
   arrives in Godot with the body animated and the legs rigid.
2. **Add a `root` bone.** The body's own motion lives on the armature *object*, and the
   hull meshes are parented to the object rather than to a bone. A skinned glTF mesh needs
   every vertex to name a joint. One unanimated bone at the armature origin, no parent, no
   children, no keys.
3. **Convert bone parenting to rigid vertex weights.** `build.py` parents ~150 separate
   mesh objects to bones. Exported as-is those arrive as ~150 `BoneAttachment3D` nodes and
   ~150 draw calls. Every vertex at weight 1.0 on its part's bone says the same thing in
   one skinned mesh.
4. **Stamp the ART §4 data into two UV layers** (§3 below).
5. **Join, and flatten the world travel** so the clip loops in place.

### The four failures, all measured, all now commented in the code

| what happened | why | what it cost |
|---|---|---|
| **`Bone.select` does not exist in Blender 5.x** | the API moved | one run |
| **Vertex colours arrived flat white on 11 of 12 primitives** | `object.join()` keeps the ACTIVE object's colour attribute and defaults the other 149, whatever `active_color_name` says. And even after baking the attribute correctly on the *joined* mesh — verified by reading all 11,850 values back — Blender's glTF exporter still wrote real `COLOR_0` for the first primitive and `1,1,1,1` for the rest. | two runs; the fix was to move every channel into UV layers, which survive both |
| **The masks were computed against the posed rig** | `nla.bake` leaves the scene on the last baked frame, and a bone-parented object's `matrix_world` is its POSED matrix. The armature is now forced to `pose_position = REST` with an identity object matrix before the conversion. | would have baked the last frame of the walk into the mesh and then deformed it a second time |
| **The chamfers were missing** | `build.py` puts BEVEL modifiers on the hull and the shell, and the exporter has to run `export_apply=False` (it would otherwise apply the armature modifier and destroy the skin). Modifiers are now applied per object before the join. | 15,476 → 23,048 tris on the Surveyor, and it is the difference between a pressed enclosure and a box |

Also measured: **the glTF exporter flips V** (glTF's UV origin is top-left, Blender's is
bottom-left) and does not touch U. The two mask values that ride in V are written inverted
in the exporter so they arrive the right way up and nothing downstream has to know.

### What comes out

18 files, `models/<chassis>_<clip>.glb`, 0.6–2.5 MB each.

| chassis | tris (after bevel) | bones | legs | clips |
|---|---|---|---|---|
| scout | 20,564 | 19 | 4 | walk, trot, idle, crouch |
| surveyor | 23,048 | 19 | 4 | walk, trot, idle, crouch |
| hauler | 28,636 | 27 | 6 | walk, trot, idle, crouch |
| swimmer | 21,140 | 19 | 4 | walk, trot, idle, crouch |
| surveyor_bare | 23,048 | 19 | 4 | walk, idle (lamp only, for the loadout comparison) |

`crouch` exists because ART 4.2's rung 0.75 is *"ride height drops 25 %"*, and
`motion.py`'s own `crouch` verb does it with the IK intact — the legs fold, they do not
stretch. Nothing Godot could do to a baked clip would be as good.

---

## 3. What survives the trip, and how

Blender's materials do not survive glTF in any useful form and were never meant to. What
has to survive is *which part is this* and *where is the gravity*, and both now ride in
the UVs, which are the one channel measured to come through intact:

```
UV .x   (part * 16 + element) / 256    part identity, and the shed id for damage
UV .y   mud     1 at the feet, 0 above the hull seam
UV2.x   dust    max(0, N_up)^3
UV2.y   scuff   max(0, N_forward)^1.5
```

Sixteen part identities (`export_gltf.PART_INDEX` ↔ `book.gd` `P_*`), which is what lets
twelve Blender material slots collapse to **two Godot surfaces** — the body and the
retroreflective strips. The split is by part, not by material: Blender's `light_strip`
covers the sonar bar, the running lights, the status pilot *and* the beacon caps, and
ART 4.5 makes the running lights a different kind of thing from the rest.

The three masks are baked on the **rest** geometry and on the **polygon** normal.
Rest, because ART 4.2 says wear is *history*, and the history of a femur blade's outboard
face is its average orientation, not its orientation this frame. Polygon rather than
averaged-vertex normal, because these are flat-shaded machined parts and the averaged
normal at a box corner points along the diagonal, which puts dust on a vertical face.

---

## 4. The three channels, and where each one lives

This is ART 4.2's and 4.3's hard separation, and it is enforced structurally so it can be
checked by reading one file (`machine.gdshader`):

| channel | uniforms | may touch | may never touch |
|---|---|---|---|
| **TEAM** | `invert`, `team_col` | which of the two liveried parts is pale; the identity mark's colour | roughness, any mask, any emissive position, any geometry |
| **WEAR** | `mud`, `dust`, `scuff`, `wet` | `ALBEDO`, `ROUGHNESS` | `HURT`, `KILL`, `EMISSION`, any part's existence |
| **DAMAGE** | `damage` | the sonar bar's lit count, the two shed parts, the one state pilot, ride height, head tracking, the gait | paint, any wear mask |

**Team is value and rhythm, never hue.** Both teams get the *same* pale and the *same*
graphite, assigned the other way round — ART 4.3 rule 3, and it is one `mix()`. Hue is
absent from the mechanism entirely, which is the only honest response to 4.3's measurement
that hue alone is a quarter of a JND at every size. The rhythm half is read **spatially**:
the player's flank strip is continuous, the rival's is dashed. See §6.

**Damage is the one parameter allowed to touch geometry**, and ART 4.2 says that exception
has to be written down. It is written down at the top of `machine.gdshader` and the two
`discard`s are the first thing in `fragment()`.

**There are exactly two reds in the shader**, both uniforms, both reachable only by
`damage`. The E-stop is painted and never emissive.

---

## 5. The gait

The gait is **`motion.py`'s**, baked. Nothing here re-choreographs it.

- `walk` — 18-frame cycle at 30 fps, 0.50 m/s, stride 0.30 m, duty 0.78, one foot at a
  time (phase 0, 0.5, 0.75, 0.25).
- `trot` — 16-frame cycle, 0.60 m/s, stride 0.32 m, duty 0.55, diagonal pairs.
- Six-legged chassis take `motion.py`'s `phase6` automatically.

The clip is baked **in place**: `motion.py` plants feet in world space, so flattening the
body's forward travel leaves the stance feet moving backwards under the body at exactly the
gait's speed. Move the node forward at that same speed and the feet are stationary on the
ground. **Any other speed and it skates** — `book.gd` carries the speed each clip was baked
at, and `Machine.advance()` uses it.

`--export-frames 1,N+1` trims each clip to exactly one period: frame 1 is the stance at
t = 0 and frame N+1 is the same phase one cycle later, which is what a looping clip needs.
`motion.py`'s trailing settle frame is cut off.

### What Godot adds on top, after the clip

The mixer is on `ANIMATION_CALLBACK_MODE_PROCESS_MANUAL` and advanced by hand, so
everything below runs *after* the pose and is not a race with it.

1. **A plane fit through the ground under every foot.** The body's height, pitch and roll
   follow that plane with a 7 Hz first-order lag. The lag is the point: a hull that snaps
   to the plane reads as a camera move; a hull that arrives a beat after the foot reads as
   mass.
2. **Two-bone IK per leg, onto the terrain.** The clip is the gait and is not touched; this
   only corrects where the foot *ends up*, keeping whatever lift the clip gave it. The knee
   is kept in the plane it is already in, so a correction cannot flip a leg inside out. On
   flat ground it is a no-op. Over broken ground it is the difference between walking and
   wading — without it the body leans correctly and the feet still sink into the rock,
   which is worse than not leaning at all.
   The foot point is found at load as **the lowest vertex weighted to each tibia bone**,
   because glTF carries no bone length and the ball foot *is* the lowest thing on the leg.
3. **The damage pose** — the gait hitch (0.30) and the frozen, jittering head (0.75).

### Gait parameters

| | value | from |
|---|---|---|
| cycle | 18 fr walk / 16 fr trot at 30 fps | chosen so `T = 0.12/v + 0.36` lands on a whole frame |
| duty | 0.78 walk / 0.55 trot | `motion.py` GAITS |
| stride | 0.30 / 0.32 m | `motion.py`: `min(0.32, 0.12 + 0.36·v)` |
| body lag | 7 Hz first-order | mine, guess |
| IK | 2-bone analytic, knee plane preserved | mine |

---

## 6. Decisions ART section 4 left open, and what this spike did

### 4.5 the running lights — **DECIDED: retroreflective. Needs a designer's yes.**

ART 4.5 says resolve this before anything else in §4 and recommends retroreflective
markings. This spike implements that, and **Godot can implement it properly where Cycles
could not.** The vision board had to bend the shading normal toward the viewer with
`Geometry → Incoming` and noted the approximation is "wrong for a lamp far off the viewer's
axis". A Godot `light()` function is handed both `LIGHT` (fragment → source) and `VIEW`
(fragment → eye), so the real lobe is one line:

```glsl
float lobe = pow(max(dot(normalize(LIGHT), normalize(VIEW)), 0.0), retro_tightness);
DIFFUSE_LIGHT += LIGHT_COLOR * ATTENUATION * facing * lobe * retro_gain * team_col;
```

A lamp 90° off the camera now returns its light to the lamp and nothing to the camera,
which is what prism sheeting does. `19_running_lights_unfound` / `20_running_lights_found`
are the two frames the decision should be made on. `21_running_lights_fallback` is ART
4.5's own fallback (strip at 1.5, always on) so the alternative can be rejected on a
picture. **Zero emission on a healthy machine; a wreck still returns**, which is §6.2's
argument.

Two things the designer should know before ruling:
- **The strip on the model is 0.32 L × 4 mm. ART 4.3 rule 2 asks for 0.32 L × 16 mm** —
  "area over intensity". That change belongs in `params.py`, not here. At the 4.5 m
  stand-off the vision board used, a 4 mm strip is one pixel and the decision cannot be
  made on a picture at all; frames 19–21 are shot at 1.6 m for that reason.
- Retroreflection removes the last always-on emissive, which is where 4.3's *rhythm* was
  supposed to live.

### 4.3 rhythm, with nothing left to blink — **DECIDED: spatial, not temporal.**

ART 4.3 concludes value is necessary and not sufficient, and that the rest must come from
"layout and rhythm — which parts are pale, and the blink pattern of the emissives". With
4.5 answered as above there is no blink to pattern. So rhythm is read **spatially**: the
player's strip is continuous, the rival's is dashed on its own pitch. Same value, same
area, no hue. **This is a guess and it is exactly the thing 4.3 says needs a human A/B.**

### 4.7 the head slot count — **KEPT AT TWO, per ART's own recommendation.**

The model builds `face` + `eye` as two head slots (4/7/9) where `DESIGN.html` says 3/6/8.
ART 4.7 says keep two and fix the doc. This spike renders the model as built. Nothing here
changes it, and the doc still needs fixing before `BLD-71` freezes content IDs.

### 4.6 the chassis gestures — **NOT EXPRESSED, and this is now confirmed in Godot.**

The vision board found four `ChassisSpec` fields dead in `build.py` (`head_neck`,
`head_pos`, `hull_bevel`, `spine_rail`), so §4.6's proposals "do nothing today". That is
still true, and since the geometry now comes from `agent_model` rather than from a
generator, **§4.6 cannot be expressed from the Godot side at all.** `08_silhouette_four`
is the consequence, measured on a real outline test: see §8.

### The Hauler's size — put on a picture, not decided.

`CHASSIS-TIMING` gives the Hauler a body of 4.0 cells (2.4 m); the model is 0.90 m.
`22_hauler_size_question` puts both in one orthographic frame at the same scale. Scaling
the model is *not* what a 2.4 m Hauler would be, but it makes the disagreement decidable by
looking, which is what the vision board asked for.

---

## 7. The lamp

One `SpotLight3D` on a `BoneAttachment3D` on the `tilt` bone, placed where `build.py`
places it — at the eye, forward and down — but expressed in the tilt bone's own frame,
because glTF has rotated everything into Y-up while the bone's local axes are still
Blender's.

| | value | authority |
|---|---|---|
| colour | `(1.00, 0.98, 0.95)`, **white for every team** | ART 2.1, 2.5 |
| cone | 50° (`spot_angle = 25`) | ART 2.1 |
| tilt | 9° down | ART 2.1 ("8–10°") |
| attenuation | `spot_attenuation = 2.0` | Godot's parameter is the **decay exponent of a windowed inverse square**; the default 1.0 is `1/d` and lights the whole throw evenly. The cave spike measured this as the single difference between a lit level and a carried lamp. |
| energy | 5.2, range 24 m | re-derived here, not inherited. ART 2.2 is explicit that watts do not survive a change of renderer and that the ratios are the durable part. |

**The aim is asserted, not inherited.** ART §0's finding is that `agent_model`'s lamp fires
into its own eye lens at 14 mm because of one character's sign, and that it survived four
passes. Here the beam direction is constructed from the bone's rest basis and **printed
with every frame** (`lampfwd=` and `dot(cam,lamp)=` in `shots/stats.txt`), so it cannot
break quietly again.

**On the lamp and the view axis.** The finding is real and it bit twice here. The model
already separates the reflector from the machine's own camera laterally; this adds a little
more. For the *shot* camera the answer is framing, and `stats.txt` carries the
camera-to-lamp dot product for every frame so an accidental co-axial frame is visible in
the log rather than only in the picture. `13_own_lamp` is deliberately shot at
`dot ≈ 0.9` — the machine between the camera and its own pool, which ART 2.4 measured at
nine times the read of the same machine with its pool beside it.

**The work lamp is off under the catalogue rig.** It is a fixture in the world, not a studio
light, and under a grey backdrop it throws a two-metre pool that reads as a lighting
mistake.

---

## 8. Do the tests pass?

### Does it read as a machine somebody engineered rather than a shape? — **Yes.**

`04_surveyor_3q` and `05_hauler_3q` are the frames to judge on. The pan-tilt head on a real
bearing, the seven-element sonar bar, the belly bay, the hip drums, the chamfered shell
with its hatches and latches, the boom on a hinge. This was already true in Blender; what
this spike proves is that it survives into a real-time renderer at 23 k triangles.

### Can you tell the four apart in silhouette alone? — **Three of four. Confirmed.**

`08_silhouette_four` is a real outline test: no light, no ambient, no glow, no ground, every
emissive off, bright backdrop. The Hauler is unmistakable (six legs, long deck, four beacon
tubes). The Scout is unmistakable (small, low, no boom). **The Surveyor and the Swimmer
separate only by their loadout** — the Swimmer's outline is the Surveyor's minus the
magnetometer boom, and that is a *loadout* difference, not a *chassis* difference.

That is exactly ART 4.6's finding — "Scout, Surveyor and Swimmer are three pale slabs on
four legs and the read is carried entirely by the loadout" — now reproduced in Godot on a
harder test than the vision board's. **The Swimmer needs §4.6's chine, ballast band and
larger hull bevel in `params.py`/`build.py`, or it will never be a different machine.**

### Does the walk read as weight? — **Mostly. It reads as a real gait; it does not yet read as heavy.**

What works: the feet plant and stay planted (contact shadows confirm it), the cycle is a
real walk with three feet down, the body follows the support plane late, and over broken
ground the IK puts every foot on the rock while the hull leans. `18_broken_ground` and
`sheet_walk_broken` are the frames.

What does not: `motion.py` derives the stride from **speed alone** —
`stride = min(0.32, 0.12 + 0.36·speed)` — with no reference to leg length or body size, so
a 0.90 m Hauler and a 0.40 m Scout take exactly the same 0.32 m step at the same speed.
That is a real property of the model and it has been left alone rather than worked around.
It is why the Hauler ambles rather than plods and the Scout prances rather than scurries.
**This is the single biggest thing that would improve the walk**, and it is a four-line
change in `motion.py`, not a Godot change.

---

## 9. The counts, and what one machine costs

Measured at 1920×1080, Godot 4.7.2 Forward+, one other Godot process on the GPU during part
of the session — so **no frame rates are reported**. Triangle counts, draw calls, bone
counts and generation times are load-independent and are reported.

| chassis | triangles | draw calls | bones | legs | load |
|---|---|---|---|---|---|
| scout | 20,564 | **2** | 19 | 4 | 63–208 ms |
| surveyor | 23,048 | **2** | 19 | 4 | 63–208 ms |
| hauler | 28,636 | **2** | 27 | 6 | 63–208 ms |
| swimmer | 21,140 | **2** | 19 | 4 | 63–208 ms |

**Two draw calls per machine** is the number that matters, because a match has several on
screen. Twelve Blender material slots become two Godot surfaces (body, retro) — see §3.
Exporting as-is instead would give ~150 `BoneAttachment3D` nodes and ~150 draw calls.

Load time is dominated by the surface collapse, which walks every triangle once in
GDScript. It is a load-time cost, not a frame cost, and it would be nothing in Rust.

Six machines on screen — a plausible worst case for a match — is therefore ~140 k triangles
and 12 draw calls before the cave. For scale, the cave spike's whole 144 m shell is 64 k
triangles in ~320 draw calls.

Skinning is on the GPU; the per-frame CPU cost is the plane fit and the IK, which is
`legs × (one plane fit + two quaternion solves)` — 4 or 6 legs, trivially cheap.

---

## 10. The frames

23 stills at 1920×1080 (four cropped to elevation strips), 5 walk cycles as image sequences
at 1280×720, and a contact sheet per sequence. `shots/stats.txt` carries draw calls,
primitives, the lamp's beam direction and the camera-to-lamp dot product for every frame.

| frame | what it is for |
|---|---|
| `01_four_abreast_clear` | the four at one scale in a clear light, 1 m rod |
| `02_four_abreast_own_light` | the same four; the only light in frame is four work lamps |
| `03`–`06_*_3q` | each chassis alone, three-quarter, sonar bar lit so the seven elements can be counted |
| `07_side_ortho_row` | orthographic side elevation, same scale, 1 m rod in 0.1 m bands |
| `08_silhouette_four` | **the test**: four outlines and nothing else |
| `09_loadout_silhouette` / `09b_loadout_outline` | bare vs default loadout, lit and as pure outline |
| `10_team_player_vs_rival` | the value inversion |
| `11_wear_fresh_vs_worn` | wear 0.00 against 0.85 |
| `12_damage_rungs` | 0 / .20 / .30 / .50 / .75 / 1.0 |
| `13_own_lamp` | a machine under its own lamp, between the camera and its own pool |
| `14_daylight` | the surface: overcast at 12000 K, no sun disc |
| `15_nine_pixels` (+ `15b` source) | the legibility ladder, 9 / 14 / 22 / 34 / 56 / 90 px, seven states |
| `16_walk_side`, `17_walk_front` | mid-stride stills |
| `18_broken_ground` | the body responding to the rock under each foot |
| `19`–`21_running_lights_*` | unfound / found / the emissive fallback |
| `22_hauler_size_question` | 0.90 m model against `CHASSIS-TIMING`'s 2.4 m |
| `seq/walk_side`, `walk_front`, `walk_broken`, `trot_side`, `hauler_side` | 16–18 frames each, one full cycle, + `sheet_*.png` |

**What `15_nine_pixels` actually shows, and it is the finding ART 4.2 predicted:** a
backlit machine at nine pixels is a smudge. The only things that survive the ladder are the
**emissives** — the damaged machine's HURT/KILL pip is countable at 9 px, the lit sonar bar
is countable at 22 px, and the chassis class is not distinguishable at any rung below 34 px.
"Losing emissive elements does [read at nine pixels]. A dent does not." Confirmed.

---

## 11. Things I guessed, in one list

1. **The clip set** — walk / trot / idle / crouch, and that four clips is the right set to
   export. Nothing specifies which gaits ship.
2. **The clip speeds** — 0.50 m/s walk, 0.60 m/s trot, chosen so `motion.py`'s own stride
   rule lands the cycle on a whole number of frames at 30 fps. Nothing in the design says
   how fast a machine walks.
3. **30 fps** for the baked clips.
4. **The idle is a head scan**, not a still. A machine that stands perfectly still is a
   prop, and the pan-tilt is the cheapest thing it owns.
5. **The body lag** (7 Hz first-order) and that the body follows a plane fit through its
   feet rather than a per-leg suspension.
6. **The IK correction preserves the clip's foot lift** and puts the foot on the terrain at
   the clip's own (x, z). A real controller would re-plan the foothold.
7. **The gait hitch at damage 0.30** — one femur, 0.22 rad, once per 0.6 s. ART 4.2 says
   "the gait acquires a hitch" and nothing more.
8. **The frozen head at 0.75** — 50° right, 22° down, jittering at 23 and 31 Hz.
9. **The wreck** — ride at the `crouch` clip, rolled 13°, pitched −5°, every emissive dead,
   retro still returning.
10. **The two shed parts** — the battery hatch at 0.50 and one belt cover at 0.30. ART 4.2
    names "a hull panel" and "one hip actuator's cover" without saying which.
11. **The scuff edge term.** ART 4.1's scuff is `max(0, dot(N,+X)) × edge_AO`. An imported
    mesh gives no curvature term, so the edge is a clustered noise. The first attempt
    produced a visible halftone over every flat panel.
12. **The spatial rhythm for team identity** (continuous vs dashed) — see §6.
13. **`retro_gain = 26`, `retro_tightness = 26`.** Real sheeting has a divergence of about
    0.2–0.5°; this lobe is far broader, because at 1.6 m the camera and the finder's lamp
    subtend about 11° at the strip and a physically tight lobe would return nothing.
14. **The CLEAR rig** — a neutral grey world plus one key. It is a labelled exception to
    ART §9's "no ambient light, ever", on ART 2.1's own allowance for catalogue renders.
15. **The DAYLIGHT rig** — the vision board's claim that the surface's light *is* the light
    that comes down the shaft, overcast at 12000 K with no sun disc. Still needs a yes.
16. **The floor.** A plain procedural ground; the cave spike owns the rock. Its albedo was
    re-derived (0.165) after a first version at 0.03 made the lamp's pool unreadable at any
    wattage — ART 2.2's instruction to re-derive against the ratios whenever the materials
    move.
17. **The broken ground profile** — a camber, 48 mm drill-round steps every 1.2 m, spall,
    and four loose stones. About 15 cm of relief across a stride. The first version had
    2 cm and the body responded by 0.6°, which is not a picture of anything.
18. **Every camera.**
19. **The palette is linearised** where the vision board used the same sRGB hexes as linear
    values (its guess 3), so BONE reads a little deeper here than there.
20. **Exposure per part** (`EXPOSE` in `export_gltf.py`) — how reachable each part is by
    mud, dust and a rock wall.

---

## 12. Design problems found, which are not art problems

1. **`motion.py`'s stride is a function of speed alone.** `min(0.32, 0.12 + 0.36·speed)`,
   with no reference to leg length or body size. A 0.90 m Hauler and a 0.40 m Scout take
   exactly the same step. This is the biggest single improvement available to the walk and
   it is four lines in `motion.py`.
2. **The Hauler's size is still undecided** — 4.0 cells in `CHASSIS-TIMING`, 1.5 cells in
   the model. `22_hauler_size_question` exists to get it decided.
3. **ART 4.6's chassis gestures cannot be expressed anywhere but `params.py`/`build.py`,**
   and until they are, the Swimmer is a Surveyor without a boom. `08_silhouette_four` is
   the evidence.
4. **ART 4.3's 16 mm flank strip is not in the model** (it is 4 mm), so the running-lights
   decision cannot be photographed at gameplay range.
5. **`build.py` looks parts up by global name** (`bpy.data.objects["chassis"]`), so in any
   scene with two machines the second gets no bevel. The exporter builds one machine per
   run, so this spike never hits it — but it is a real bug for a lineup render.
6. **Four `ChassisSpec` fields are dead** (`head_neck`, `head_pos`, `hull_bevel`,
   `spine_rail`). The vision board found this; it is unchanged.

---

## 13. What I would do next, in order

1. **Wire ART 4.6's four gestures into `params.py`/`build.py`** — the Scout's head and
   neck, the Swimmer's chine, ballast band and hull bevel, the Hauler's flat bed. Until
   then the four are three. It is numbers, not modelling, and it is the difference between
   a chassis class and a loadout.
2. **Make `motion.py`'s stride a function of leg length.** The walk reads as a real gait;
   it does not yet read as a *heavy* gait, and this is why.
3. **Take the ART 4.5 ruling** on retroreflective vs the emissive fallback, off frames
   19–21, and widen the flank strip to 16 mm either way.
4. **The two modules that fail ART 4.4** — `passive_acoustic`'s vane and
   `structural_monitor`'s deployable spike — are still the invisible 6 mm bumps and ankle
   collars. They are `build.py` changes, and the spike posture the vision board proposed
   would need a `crouch` clip, which now exists.
5. **A hardware-facing seam for the gait.** The clips are baked, which is right for a
   trailer and wrong for a machine that has to walk where the terrain says. The IK layer
   here is the beginning of the real thing; the next step is a foothold planner that
   re-plans the *target*, not just corrects the result.
