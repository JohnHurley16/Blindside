# The cinematic layer, belief side — the matched camera and the post stack on data

2026-09-09. `spikes/godot/cloud/`, Godot 4.7.2, Forward+, Vulkan, RTX 3080 Laptop.
Spec: `docs/TRAILER.md` §3 (shots 18, 19, 20, 21, 26), §8 (the camera), §9 (the lens and
the grade). Rules: `docs/art/ART-DIRECTION.md` §8.2 as rewritten today.
Adopted rather than redesigned: `spikes/godot/cave/CINEMA.md` and its shot format.
Nothing outside `spikes/godot/cloud/` was modified. Nothing was committed.

```
<godot> --path spikes/godot/cloud --resolution 1920x1080 -- --cinema=validate
                                                            --cinema=seq
                                                            --cinema=match
                                                            --cinema=pairs
                                                            --cinema=bloom
                                                            --cinema=fail
                                                            --cinema=tune
                                                            --cinema=cost
                                        --ground=local   resolve height locally (§2)
                                        --fx=a+b+c       any subset / all / none / keep
```

---

## 0. The short version

| | |
|---|---|
| **Does the belief cut read as one place seen two ways?** | **Yes, and it is proved rather than claimed.** The belief camera reproduces the cave rig's own recorded track to **5 mm RMS**, and `shots/cinema/match/align_*.png` puts the two frames in one image: the cave's timber post is exactly the vertical *void* in the cloud, and the cave's rail lies along the cloud's floor rings. §7. |
| **How is a camera matched across two projects?** | Three things, in order of how much each is worth: **two integers** (seed 7, 240 cells) that make it the same cave; the shot definition **copied verbatim** out of the cave's `shots_cinema.json`; and **one exported number per anchor** for the floor, because that is the only channel that does not survive the crossing. §2. |
| **The thing that does not cross, and why** | `u` is "metres above the floor here", and the floor here is whatever the *dressing* put there. The cave's dressing is drawn from an ordered `RandomNumberGenerator`; this spike's from a stateless hash. They agree about the workings and disagree about the litter, so they disagree about what the camera is standing on — by **0.27 m** at the head of shot 18 and by **0 mm** at its tail. §2.3. That is a design problem in `dressing.gd`, not in the format. §9.1. |
| **What does the camera collide against?** | **The truth geometry — literally the mesh the sensor raycasts.** With one addition the cave already has and this spike did not: a second collision body for the camera that omits loose scatter. §3. |
| **And when there is nothing to collide with?** | A shot declares its **frame**. `world` has a body and every cave rule. `survey` has none — and pays for the exemption with two rules of its own: it may never enter the cloud, and **it may never draw truth**. §3.3. |
| **Which post effects survive on emissive data?** | **One of nine: the vignette.** It is the only one of the nine that is multiplicative and ≤ 1 — the only one that can only ever take light *away*. Everything else adds light, and on a belief frame nine tenths of the frame is a place the sensor returned nothing from. §5. |
| **Biggest thing found in the post** | Every geometric lens effect **resamples the frame**, and resampling a hard 2-pixel mark spreads it into the void beside it. Sub-percent barrel writes into **16.0% of the sensor shadow at +97.7/255**; half a pixel of chromatic aberration into 20.4%. On a lit image both are invisible; on data both are `ART-DIRECTION` §8.2 broken. §5.5. |
| **Do the shots execute?** | **18, 19, 20, 21 and 26**, plus the fix as a sixth shot that is not in the trailer's list. Three entries are rejected and all three are deliberate. §6. |
| **Point count / draw calls** | 224 k to 1.52 M returns depending on the shot; **one draw call** for the belief layer at any of them; six when shot 21 turns truth on. §8. |
| **Frame times** | Deltas only, on a GPU throttled to **780 MHz of 2100**. The whole stack is 6.4 ms of an 11.4 ms frame and depth of field is 3.5 ms of that; the vignette that ships is **0.17 ms**. Two earlier runs produced negative deltas and are recorded as failures. §8. |

---

## 1. What was adopted, and what had to change

`spikes/godot/cave/CINEMA.md` §3 defines a shot as a JSON dictionary and an anchor as
`{st, r, u, f}` — a station on the main drive, metres right of the centreline, metres
above the floor there, and **arc length** along the drive. `cinema.gd` here is a port of
that file and it is deliberately kept recognisable next to it: same anchors, same
smootherstep, same "linear is a failure", same 0.15–2.5 m travel, same 1.2 m/s ceiling,
same 36 × 20.25 mm sensor, same 0.030 mm circle of confusion, same seven rules in the
same order. **A shot list that means two different things in two projects is not a shared
shot list**, and the whole of §2 depends on this being a port rather than a rewrite.

Four things are new, and every one of them is forced by the register:

1. **A shot declares its `frame`** — `world` or `survey`. §3.
2. **A survey camera may never draw truth**, and that is the price of not having a body.
3. **A survey camera may not enter the cloud.** Rule 9.
4. **The scrub is part of the shot.** `t_from` / `t_to` move belief time across the take,
   which is the only way drift, a fix and a lie can be *shots*. §4.

---

## 2. How a camera is matched across two projects

This is the part that decides whether the trailer's signature works, so it is measured
rather than argued. The ground truth is the cave spike's own recorded camera track,
`spikes/godot/cave/shots/cinema/sequences.txt`, which prints at 10 mm. Nothing in the
cave spike was run or modified to produce any of this; its frames and its log were already
on disk.

### 2.1 Two integers, and nothing else matters if they are wrong

`topology.gd` is byte-identical in the two projects (`md5` verified) and is the
deterministic layer: no floats, no engine RNG, a stateless counter hash. So the same seed
gives the same cave — **as long as the stretch length matches too**, and that is not
obvious. Probed at both lengths:

| | seed 7, **170** cells (the sensor spike's own) | seed 7, **240** cells (the cave spike's) |
|---|---|---|
| station 68, x / z | 45.000 / 23.400 | 45.000 / 23.400 |
| station 68, `worked` | 205 | **175** |
| station 70, `works` | 0x3f | **0x37** |
| station 89, floor | −0.778 m | **−0.178 m** |
| topology hash | 0x97de7a55 | 0xad83e3ed |

**A station's x and z do not depend on the length** — the drive's lateral walk is a
function of the cell index alone — so a naive check "is station 68 in the same place?"
passes at any length and tells you nothing. Everything that decides what the passage *is*
divides by the stretch: `worked` is `(i·1000)/n` and drives the profile from natural to
horseshoe, the sump centre is `(n·58)/100`, the chambers are at `(n·17)/100 …`. At 170
cells station 68 is the same coordinate **in a different passage**: different section,
different props, floor 0.6 m lower at station 89.

So the cinema path forces seed 7 over 240 cells and turns on a `cave_match` flag in
`lidar_geo.gd` that stops the two things this spike does for the sensor test and which
the other project does not do: inflating the biggest chamber to ≥ 9.5 m, and cutting
chambers out of the sweep to replace them with a dome. In cave-match mode a chamber is a
wide length of the same swept drive, which is what `dressing.gd` builds.

### 2.2 The shot definition, copied rather than referenced

`shots_cinema.json` here holds shot 18's camera as a **verbatim copy** of the cave's
`t17_follow_machine` — lens, T-stop, ease, handheld degrees, seed, and all six anchors,
character for character — and shot 20's as a verbatim copy of the cave's
`t20_sensor_shadow`. The copy is deliberate and it is the weakest link in the design:
there is no mechanism that would notice if the cave's file changed. §9.3.

Both shots carry `_same_camera_as: "cave:<name>"`, and the validator prints it and says
that the cave rig's verdict governs. `xfail_through_the_wall` is copied over too, for one
reason: **a port that does not reject the shot the original rejects is not the same rig.**
It rejects it.

### 2.3 What actually crosses, measured

`--cinema=match` renders the belief frame at the pose this rig computes and prints the
residual against the cave's recorded track, frame by frame.

| | in plan (x, z) | in elevation (y) | overall |
|---|---|---|---|
| shot 20 — camera on bare rock | ≤ 5 mm | ≤ 11 mm | **RMS 4 mm, worst 7 mm** |
| shot 18 — camera on dressing, height exported | ≤ 5 mm | ≤ 7 mm | **RMS 5 mm, worst 9 mm** |
| shot 18 — height resolved locally (`--ground=local`) | ≤ 5 mm | **268 mm → 0 mm** | RMS 167 mm, worst 268 mm |

**The plan crosses for free and the elevation does not cross at all.** Every millimetre of
the 167 mm residual is in y, and it is not noise: it runs 268 mm at the head of the move
and falls smoothly to 0 mm at the tail. The cave's rig found the floor 0.276 m above the
station datum where the move starts, and this project's floor there is at the datum. The
cave's camera is standing on something.

It is not the timber set — that is two posts at ±1.23 m and the camera is 0.06 m off the
centreline. It is a breakdown block, placed by `dressing.gd` under
`if integ < 0.55 or worked < 0.3` at `rng.randf_range(0.42, 0.88) · hw` with
`rng.randf_range(0.7, 1.8)` of scale. **Four draws from an ordered stream**, whose values
depend on how many `randf()` calls happened earlier in the same station's dressing pass.
Nothing outside that project can reproduce it. §9.1.

### 2.4 What I chose, and the rule that comes with it

**The shot definition is shared; the floor is exported.** A matched shot carries two extra
numbers, `ground_from` and `ground_to`, which are the cave rig's own resolved floor at the
two move anchors — read straight out of its `sequences.txt` by subtracting the declared
`u` from the recorded world y. They are applied to the **move** anchors only. Pushing them
out to a look target three metres down the drive would swing the aim by five degrees on
the strength of a measurement taken somewhere else; look and focus resolve locally, and
the measured consequence is the ≤ 7 mm of residual y above.

That leaves one problem, and it is the interesting one. With the exported floor the camera
is 0.42 m above **the cave's** floor and 0.69 m above **this project's**, so rule 3 — the
height rule — rejected it. The resolution is a rule, not an exemption:

> **Rule 3 is measured where the shot was authored.** An exported ground *is* a raycast;
> it was taken in the project that has the floor. Re-measuring it here does not check the
> shot, it checks the model, and this model of the same cave is missing the block the
> camera is standing on. So for a matched shot the exported height governs, the local
> measurement is printed beside it as a warning, and **nothing else is relaxed**: the body
> sweep, the near-plane clearance and the line-of-sight test still run against the
> geometry that is actually here — because those ask whether the camera *hits* something,
> and a camera that hits something here would hit it there.

`validation.txt` prints, for shot 18:

```
   WARN: height is the exported one: 0.42 m above the floor the CAVE rig found.
         Against this project's own floor the same camera runs 0.42-0.69 m,
         a disagreement of 0.27 m
```

Both readings are rendered — `shots/cinema/match/` is the exported one and
`match_local/` is the local one — so the choice can be checked by looking rather than by
reading this paragraph.

### 2.5 What should replace all of it

The exported ground is a patch on a format that is portable in plan and not in elevation.
**The right mechanism is for the project that owns the truth register to export the pose**
— position, basis, lens, T-stop and focus distance per frame, at full precision — and for
the belief rig to play it back and validate it rather than re-derive it. That is about
twenty lines in the cave's `_cin_seq`, it removes the dressing from the problem entirely,
and it removes the 10 mm quantisation the cave's log currently imposes. I did not build it
because `spikes/godot/cave/` is not mine to modify.

---

## 3. What the camera collides against

### 3.1 The truth geometry, and it is not a convenience

The belief cloud is data; there is nothing in it to collide with. The camera therefore
collides against the **truth geometry underneath** — the same `StaticBody3D` trimeshes the
sensor raycasts, 148,128 triangles at seed 7 / 240 cells. Three reasons, in order:

1. **The next shot reveals it.** A camera that flies through a wall the viewer cannot see
   is still a camera that flies through a wall, and shot 18 is cut *from* a shot in which
   that wall is lit.
2. **A matched cut has to pass or fail on both sides.** Validating the belief camera
   against anything other than the world the cave validates against makes the two verdicts
   incomparable.
3. **It is not an extra asset.** The collision the camera sweeps against is literally the
   surface that produced the points. Nothing had to be authored for it.

### 3.2 Two collision bodies, and the cave already knew why

The first run of the matched shot was rejected with four failures, and all four were one
cause: this spike strews `_rock_lump` boulders down the drive every three cells and puts
them in the same physics body as the shell. The cave's `cinema.gd` §4.1 is explicit:

> "Loose scatter — stones, ballast, grit, spall, litter — is deliberately **not**
> collision. A 40 mm chip is not an obstacle."

So `lidar_geo.gd` now builds a second body:

| | layer | contents | triangles | bodies |
|---|---|---|---|---|
| `surf_rock` … `surf_retro` | 1 | **everything**, including loose scatter | 148,128 | 5 |
| `camera_collision` | 2 | everything **except** the corridor's loose rock | **118,140** | 1 |

The laser masks to layer 1 and must see every chip, because a chip casts a return and a
shadow. The camera masks to layer 2. **Twenty per cent of the truth mesh is litter** —
29,988 triangles of it in this stretch — and taking it out of the camera's world turned
four failures into none.

Two content gaps between the projects were closed at the same time, and both were found by
the rig rather than by looking:

* **The timber set was the wrong size.** This spike stood 1.98 m posts under a cap at
  0.64 of the section height, putting a beam across the drive at 2.05 m; the cave's set is
  scaled to `(ht − 0.25)`, which puts it at 2.95 m. That is not only a content difference:
  the rig finds the floor by casting **down from 2.6 m above the station datum**, so a cap
  at 2.05 m *is* a floor, and every eye-height shot in this drive came out two metres in
  the air. The set is now built to the cave's dimensions.
  **`spikes/godot/cave/cinema.gd` has the same latent bug** and is only saved by its sets
  being taller than 2.6 m. `_ground_y` should cast from the anchor's own nominal height,
  not from a fixed offset above the datum.
* **There was no spoil heap.** `WK_SPOIL` is in the topology and the cave draws it; this
  spike did not. Trailer shot 20 is "the clean wedge of no data behind a fallen block" and
  a 0.3 m stone does not cast one. Added, on the side the station's index parity chooses,
  so the two projects agree about which wall it is against.

Both edits are guarded by `cave_match` only where they change a *scene* (the chambers);
the set resize and the spoil heap apply to the sensor spike's own scenes too, and they
move its published return counts by two: `chamber1` is 23,399 where `LIDAR.md` §6 records
23,397, and `real_short` is 114,998 where it records 114,997. `toy_stand` is unchanged at
8,640. That is 0.01% and it is recorded rather than glossed, because the counts in
`LIDAR.md` are the argument for the sensor decision and somebody re-running them should
know why they moved.

### 3.3 The survey camera, which collides with nothing

Shot 26 is thirty metres of corridor tearing in half. That cannot be seen from inside a
2.4 m drive, and no camera standing in the mine can photograph it. So the format has a
second frame:

> **A camera that draws the world has a body. A camera that draws only the drawing does
> not need one — and it may then never draw the world.**

That is one rule stated twice, and it is the whole argument. A survey camera is the
replay's map view: it is not *in* the mine, it is over the drawing, so asking what it
collides with is asking the wrong question. The moment truth appears in frame the camera
is claiming to stand somewhere, and a claimed place can be caught inside a wall by the
next cut — so `truth: true` on a survey shot is a **failure**, not a warning
(`xfail_survey_draws_truth`).

The exemption is paid for twice more:

* **Rule 9 — it may not enter its own subject.** Flying into an accumulated cloud is this
  register's version of flying through a wall: the data closes over the lens and there is
  no picture left. Checked against the cloud's own bounding extent plus 0.75 m.
  `shots/cinema/fail/xfail_into_the_cloud_b_end.png` is what that looks like, and it is
  the most persuasive frame in the failure directory.
* **Rule 10 — it must declare `height: "survey"`**, so that nothing hovers by accident.
  The declared height is checked against the cloud rather than against a floor.

Shot 21 is the test that the rule is not a loophole: it draws truth, so it is a `world`
camera, and it passes every rule the cave rig applies at eye height.

---

## 4. The scrub, and why these are shots rather than stills

`LIDAR.md` §4 ends with a finding worth repeating: **the fix reads as a pair of frames and
not as one still**, and the first pass's conclusion — that motion is the strongest carrier
and a two-second clip beats any still — "has not been overturned; it has been made
unnecessary rather than wrong."

So the shot format moves belief time across the take. `t_from` / `t_to` are the scrub at
the two ends of the shot; a value ≤ 0 is relative to the end of the run, which is how a
shot that has to catch a correction is authored. The three belief behaviours are then
shots and not pairs:

| behaviour | shot | what happens during the take |
|---|---|---|
| **drift accumulating** | `t21_two_registers` | the cloud and the truth cave are in one frame and do not line up; the disagreement is 20 m of dead reckoning |
| **the map building** | `t19_cloud_building` | four sweeps a second land during the 5 s take; the far end thins into unmapped black |
| **the fix closing a doubled corridor** | `x19_fix_closes` | two records of one passage, 43 m long and diverging, collapse into one over 0.7 s |
| **the lie tearing the map** | `t26_the_fold` | the return leg hinges 26° and 11 m away from everything placed before it |

The fold is the one that is unarguable in motion: `seq/_strip_t26_the_fold.png` is one
corridor in the first three frames and two limbs at 26° in the last two.

**The fix needed two things pushed to read at all, and both are recorded rather than
hidden.** At the first framing — a 27 m walk and a 0.55 m crop box — the two records read
as *one wide corridor*, which is exactly the failure `LIDAR.md` §4 predicted for the
single still. What fixed it was more drift (43 m each way instead of 27, so the return
leg is 8 m out rather than 2) and a harder crop (0.30 m, so the ribbon is ground rings and
not lower wall). Neither is a presentation trick: the first buys real disagreement and the
second is `ART-DIRECTION` §8.2's own crop box.

---

## 5. The post stack, on data rather than on light

TRAILER §9's rule is "every effect must be defensible as something a real lens or sensor
does, in this light, at this scale." Two thirds of that sentence does not survive the
crossing. **There is no light** — zero `Light3D`, ambient disabled, every cloud shader
unshaded — so nothing in frame is radiance. **There is no sensor** — the numbers on screen
*are* the sensor's output, and adding photon shot noise to a measured reflectivity claims
the belief view was photographed. **There is still a lens**, because the camera in shot 18
stands in a passage at a stated focal length and cuts frame-on-frame with a cave shot at
the same one.

So each effect is asked two questions, and the second one does most of the killing:

1. is it a property of the **optical path** (which both registers share) or of the
   **subject** (which they do not)?
2. does it survive `ART-DIRECTION` §8.2 — ring structure intact, and **nothing drawn into
   a sensor shadow**?

### 5.1 The measurement

`beliefcheck.py pairs` measures each effect **alone against nothing**, at three poses:
`w` = shot 18, close, machine height, in the drive; `b` = shot 19, eye height, a
retroreflector in frame; `s` = shot 26, the survey register. Two numbers carry the
verdict:

* **ring ×** — mean `|dI/dx|` over the luma, after ÷ before. A point cloud at 1.6–3.6 px
  is almost all edge, so this number *is* the ring structure; anything that merges
  adjacent returns drops it.
* **into void** — the share of the pixels that were **exactly** background in the `off`
  frame and are **brighter** than background in the `on` frame. A sensor shadow is a void
  with no returns in it. §8.2 says nothing may ever be drawn into one, so **any non-zero
  number here is a rule broken, not a taste call.**

The first version of this measured the effects cumulatively, the way the cave's pairs are
built, and it was worthless: depth of field destroyed 82% of the void in row 2 and every
later row was then measured against what was left. The second version counted a vignette's
*darkening* of the void as an intrusion and reported 100%. Both are recorded because both
looked like results.

| effect | w · ring × | **w · into void** | b · into void | s · into void | verdict |
|---|---:|---:|---:|---:|---|
| tonemap (AgX) | 1.02 | 0.00% | 0.00% | 0.00% | **cut** — 98–100% of pixels changed, −16% to −20% of the frame mean |
| bloom | 1.00 | 0.00% | 0.00% | 0.00% | **cut** — no subject at any usable threshold. §5.2 |
| depth of field | **0.66** | **71.6%** @ +36/255 | 15.0% @ +23.6 | 0.00% | **cut**. §5.3 |
| motion blur | 1.04 | **18.8%** @ +27/255 | 0.00% | 0.00% | **cut**, and it is the one verdict that reversed. §5.4 |
| film grain | 1.19 | **37.1%** @ +4.4/255 | 37.1% | 37.2% | **cut**. §5.6 |
| **vignette** | 0.97 | **0.00%** | **0.00%** | **0.00%** | **KEPT — the only one.** §5.7 |
| chromatic aberration | 0.98 | **20.4%** @ +7.3/255 | 18.9% @ +10.9 | 2.1% | **cut**. §5.5 |
| lens distortion | 1.00 (0 at 35 mm) | 0.00% | **16.0%** @ +97.7/255 | 1.7% @ +111 | **cut**. §5.5 |
| colour grade | 1.00 | 0.00% | 0.00% | 0.00% | **not built**. §5.8 |

Read the `into void` column and the answer falls out: **the survivor is the only one of the
nine that is multiplicative and ≤ 1.** Everything else in the table adds light somewhere,
and on a belief frame 84–90% of the pixels are a place the sensor returned nothing from,
so "somewhere" is overwhelmingly there.

### 5.2 Bloom — cut, and not on a rule: it has no subject

Bloom changed **0.000% of pixels at every pose**. That is a strong enough claim that it has
to be separated from "the effect is not running", so `--cinema=bloom` sweeps the threshold
on a frame with a retroreflective plate in it:

| threshold | pixels changed | into the void |
|---:|---:|---:|
| 1.60 (the cave's) | 0.000% | 0.00% |
| 0.80 | 0.000% | 0.00% |
| 0.40 | 0.012% | 0.01% |
| 0.10 | 4.730% | 4.72% |
| 0.00 | 17.195% | **17.23%** |

It is running. It has nothing to do. The point shader writes `ALBEDO` in 0..1 and a
retroreflector *clips* the intensity channel at exactly 1.0, so **nothing in a belief
frame is ever above 1.0** and the cave's threshold of 1.60 can catch nothing at all; and a
2-pixel mark does not survive the glow mip chain, so even at 0.40 it is doing 0.012%. The
only settings at which bloom does anything are settings at which it writes into one in six
pixels of sensor shadow. Cut, at no cost.

This is **not** the cave's bloom situation. There, bloom is kept-but-idle because its
subjects — the lamp seen directly, the winch head, retroreflectors — do not exist in the
spike *yet*. Here the retroreflectors do exist, they are in frame, and they are the
brightest thing in it. Bloom still has nothing to do, because the register has no HDR at
all: belief is drawn at its authored value and 1.0 is the ceiling by construction.

### 5.3 Depth of field — cut, and it is the most destructive thing tested

At shot 18's camera — 35 mm at T2.8 focused at 2.4 m, the same arithmetic the cave uses —
depth of field changes **71.6% of pixels**, takes **a third off the ring energy** (×0.66),
writes into **71.6% of the sensor shadow** at a mean of +36/255, and raises the frame mean
by **69%**. It does not soften a frame; it dissolves the data into a fog. That is the
first-pass nebula this whole spike exists to have stopped being, arriving through the lens
instead of through the blend mode.

It scales with how shallow it is — 15.0% of the void at shot 19's 21 mm focused at 8 m,
and **0.000%** on the survey shot, where T4.0 at 36 m is past hyperfocal and nothing is
out of focus at all. So there is nowhere it is both harmless and doing anything.

Does cutting it break the matched cut? The cave's shot 17 has a near timber going soft and
this frame does not. That reads as a change of *subject*, not a change of *lens* — the
belief frame is sharp everywhere because a measurement does not have a focus plane — and
it is the one asymmetry across the cut I would defend rather than fix.

### 5.4 Camera motion blur — cut, and this is the verdict that reversed

It was kept. Then shot 18's density was halved to make the frame readable (§7), and the
same measurement on the same camera came back at **18.8% of the sensor shadow written
into, at a mean of +27/255**, against 0.00% before.

That is not a contradiction, it is the mechanism showing itself: **the reach of a smear is
the per-frame screen velocity, and whether that reach lands in a void depends on how
isolated the mark is.** In a dense frame every bright return already has returns beside
it and the smear lands on data. Thin the cloud until the rings are countable — which is
what §8.2 asks for — and the same 2 px smear now starts in a bright mark and ends in
black. So motion blur's damage is *worst exactly at the density the rule wants*, and it
scales with camera speed: 18.8% at shot 18's 0.78 m/s peak, 0.00% at shot 19's slower
push, 0.00% on the survey shots where the camera moves 1.8 m in four seconds and the data
does the moving.

**What is lost by cutting it.** A field of hard 1.6–2.2 px marks moving two pixels a frame
is a textbook temporal aliasing case and a 180° shutter is the textbook answer. That
argument is untouched by any of this, and it is a claim about motion that a still cannot
test — which is precisely why I let it override the rule for one pass, and why the second
measurement is the one to believe. If the finished sequence crawls, this is the first
thing to reconsider, and the reconsideration is a designer's ruling on how absolute §8.2's
"nothing may ever be drawn into a sensor shadow" is when the something is a two-pixel
smear off a real return.

The compositor pass and the reprojection are still in `lens.gd`, unchanged and working;
`--fx=mblur` turns them on.

### 5.5 Chromatic aberration and lens distortion — cut, and the reason is one sentence

Both are geometric properties of the optical path, so by the argument at the top of §5
both should have survived. They do not, and the reason generalises:

> **Every geometric lens effect resamples the frame, and resampling a hard two-pixel mark
> with a bilinear filter spreads it into the void beside it.** On a lit image a
> sub-pixel resample is invisible. On a point cloud it moves data and leaves a ghost where
> the sensor returned nothing.

Chromatic aberration at 35 mm is 0.76 px at the corner — sub-pixel — and it writes into
**20.4% of the sensor shadow**, because shifting the red channel half a pixel off a 2 px
white return leaves a red copy of that return one pixel away in the black. Lens distortion
is worse where it acts at all: `k = −0.009` is 0.9% at the corner, which at 1080p is about
**ten pixels of displacement**, and at 21 mm it writes into 16.0% of the void at a mean of
**+97.7/255**. (At 35 mm the coefficient is zero by the cave's own formula, which is why
pose `w` shows 0.000% — the effect is off, not harmless.)

The cost to the matched cut is small and worth stating: the cave's shot 17 has 0.76 px of
lateral dispersion at its corners and shot 18 will not. At 35 mm the barrel is zero on
both sides, so nothing changes there.

### 5.6 Film grain — cut

Ring energy goes **up** (×1.19 close, ×2.14 on the survey shot), which is the giveaway:
that is not structure, it is noise being counted as structure by a high-frequency measure.
And it writes into **37.1% of the void** at +4.4/255 at every pose, because a sensor's
read-noise floor lands on a zero signal by definition. A sensor's noise on a measurement
that already *is* the sensor's output is a claim that the belief view was photographed. It
was not; §8.1 says it was drawn.

The cave keeps grain partly to dither 8-bit banding in the near-black. That job does not
exist here: the belief background is one flat authored colour and does not band.

### 5.7 Vignette — kept, and it is the only one

cos⁴ evaluated from the shot's own focal length, `vig_k = 0.55`, exactly the cave's
implementation. It **only darkens**, so it puts nothing into a sensor shadow — 0.00% at
every pose, at every density, at every camera speed — and it costs 3.9–5.6% of the frame
mean and 3–4% of the ring energy.

It is kept because of the cut. At 35 mm the corner falloff is about 25%, and if the cave
frame has it and the belief frame does not, **the cut carries a lens change as well as a
register change** and reads as two cameras rather than as one camera pointed at two
things. That is the whole thesis of shot 18, so the one lens mark that survives is the one
that has to match.

### 5.8 The tone curve, and the grade

The cave runs AgX. This register runs **LINEAR**, and it is not taste: **the intensity
channel is the data.** AgX changes 97–100% of pixels and takes 10–20% off the frame mean,
and its shoulder compresses the top two stops — which is exactly where a retroreflector
lives — so a filmic curve quietly throws away the separation between "bright rock" and "a
survey plate". `LIDAR.md` §3 made this call for the still frames; it holds for the shots.

**The two registers therefore cannot share a tone curve**, and that is a real consequence
for the edit: the belief cut is a change of transfer function as well as of subject, and
the grade for the trailer has to be built as two grades that meet at a cut rather than one
that spans it.

The colour grade is **not built**. The cave's does two things — roll chroma out of the
deepest shadows, and warm the top two stops toward the iron and the lamp. Belief has no
iron and no lamp, and rolling chroma out of the dark end would eat the low half of the
intensity ramp, which is the channel. The switch exists so the bit can be measured; it is
wired to nothing so it cannot ship by accident.

---

## 6. Which trailer shots execute

`shots/cinema/validation.txt` is the machine-readable version; `shots/cinema/seq/<name>/`
holds each as 24 frames at 1920×1080, and `_strip_<name>.png` next to it is six of them
on one sheet.

| # | shot | lens | frame | returns | executes | note |
|---|---|---|---|---|---|---|
| **18** | the first belief cut | 35 mm T2.8 | world | 482,482 | **yes** | verbatim camera from cave `t17_follow_machine`, matched to 5 mm RMS. §7 |
| **19** | the cloud building | 21 mm T2.8 | world | 1,476,344 | **yes** | four sweeps a second land during the take |
| **20** | the sensor shadow | 35 mm T2.0 | world | 224,036 | **yes** | verbatim camera from cave `t20_sensor_shadow`, matched to 4 mm RMS |
| **21** | truth and belief in one frame | 21 mm T4.0 | world + truth | 1,116,236 | **yes** | but see below |
| **26** | the second belief cut, the fold | 21 mm T4.0 | survey | 1,442,474 | **yes** | the map tears during the take |
| — | `x19_fix_closes` | 35 mm T4.0 | survey | 1,517,578 | **yes** | not a numbered trailer shot; the third belief behaviour |
| — | `xfail_through_the_wall` | 21 mm | world | — | **REJECTED** | the cave's own deliberate failure, ported |
| — | `xfail_survey_draws_truth` | 35 mm | survey | — | **REJECTED** | rule 11 |
| — | `xfail_into_the_cloud` | 35 mm | survey | — | **REJECTED** | rule 9 |

**Shot 21 executes and should not ship as it stands.** The truth layer in *this* project is
a flat-shaded, untextured stand-in that exists so a viewer can check a sensor shadow
against the thing that cast it (`LIDAR.md` §9.2 says so). At the exposure §8.3 asks for —
truth turned down to a ground, belief the drawing on it — it is a dim brown silhouette and
the frame is legible, but it is not the photographed cave. **The shipping version of shot
21 is a composite of the cave spike's rendered truth with this cloud over it**, which is
the same matched-camera problem as shot 18 and is solved by the same mechanism. It is the
one shot in the trailer that needs both projects in one frame, and §2 is what makes it
possible.

One thing worth flagging about the shot list itself: **TRAILER §3 gives shot 20's source
as L, and the cave spike also built it** (`spikes/godot/cave/CINEMA.md` §7 lists it as
executing). Both exist, on the same anchors. That is not a conflict to resolve — it gave
this pass a second matched pair for free, and the alignment overlay for shot 20 is the
clearest evidence in this document — but somebody should decide which one is the shot.

### 6.1 The three deliberate failures

`shots/cinema/failure.txt`, and each one photographs what would have shipped.

```
xfail_through_the_wall: REJECTED
  FAIL: body intersects geometry at t=0.34 (the 0.35 m sphere overlaps)
  FAIL: frustum clearance falls to 0.14 m at t=0.53 (needs 0.40)
  FAIL: height 'eye' wants 1.38-1.82 m; the move runs 0.74-1.62 m above the floor

xfail_survey_draws_truth: REJECTED
  FAIL: a survey camera has no body and may not draw truth: truth in frame means
        the camera claims a place it has not proved

xfail_into_the_cloud: REJECTED
  FAIL: camera is 1.53 m inside the cloud's own extent at t=1.00:
        a survey camera may not enter its subject
```

The first is the cave's own file, unchanged, and it is the cross-check that this is the
same rig: it is rejected there and it is rejected here, on the body and the near plane.
(The cave also rejects it for leaving the drive's line of sight, where this project's
version leaves the height band first — the drive dips differently under the two dressings.
Same shot, same verdict, different first failure.)

### 6.2 What is in `shots/cinema/`

| where | what |
|---|---|
| `seq/<shot>/000..023.png` | the executing shots as 24-frame image sequences, 1920×1080, with the shipping stack |
| `seq/_strip_<shot>.png` | six frames of each on one sheet, for reading a shot at a glance |
| `match/<shot>/` | the belief frame at the matched pose, with the exported ground |
| `match/sbs_17_18_*.png`, `sbs_20_*.png` | **the matched-camera test**: the cave frame and the belief frame side by side, same position, same focal length |
| `match/align_17_18_*.png`, `align_20_*.png` | the same two frames as one image — cave in red, belief in cyan. Structure the two agree about lands grey; anything they disagree about is coloured |
| `match/_ground_local_vs_export_000.png` | the two ways of crossing the boundary, at the frame where they differ most |
| `match_local/`, `match_local.txt` | the same shots with the height resolved locally, for §2.4 |
| `match.txt` | the frame-by-frame residual against the cave's recorded track |
| `pairs/w**, b**, s**` | before and after for **every** effect, alone, at three poses |
| `stack/<shot>_{off,on}.png` | nothing versus what ships, at three shots |
| `bloom/thresh_*.png` | the threshold sweep behind §5.2 |
| `tune/` | the recency-window sweep behind §7, eight variants of one frame |
| `fail/` | the three rejected shots, each photographed at its start and at the end it would have shipped |
| `validation.txt`, `sequences.txt`, `pairs.txt`, `bloom.txt`, `failure.txt`, `cost.txt` | the machine-readable versions of §6, §4, §5 and §8 |

**The directory is 253 MB** — `seq` 105, `pairs` 48, `match` + `match_local` 64, `tune` 25,
the rest under 12. `LIDAR.md` §9.8 made a deliberate non-decision to keep `shots/lidar/`'s
10 MB in the tree because the frames are the evidence; this is twenty-five times that and
I am not going to make the same call by default. Whoever commits this should decide. If
the answer is no, the smallest honest cut is `seq/*/`, `pairs/` and `tune/` in
`.gitignore`: the `_strip_*.png` sheets, `match/` and `fail/` carry every claim in this
document between them, at about 35 MB.

---

## 7. Does the belief cut read as one place seen two ways?

My honest judgement, from reading the frames rather than from having made them.

**Shot 20: yes, and it is not arguable.** `shots/cinema/match/align_20_012.png` puts the
cave's frame in red and the belief frame in cyan on one image. The cave's rail, its
sleepers, its wall and its timber post all fall on cloud structure: the wall bands sit on
the wall, the floor ring band lies along the floor edge, and **the cave's timber post is
exactly the vertical wedge of no data between the two banks of returns.** The sensor shadow
is where the thing that cast it is. A viewer does not need to be told what they are
looking at.

**Shot 18: yes at the tail of the move, and less certainly at the head.** At frame 23 the
correspondence is direct, and `align_17_18_023.png` is where to look: the cave's timber
post is a vertical break in the cloud, the cave's sleepers and rail lie along the cloud's
floor ring band, and the dark passage recedes in the same place in both. At frame 0 it is
harder, and the reason is scale rather than registration: shot 17 is a camera 0.5 m off
the floor with a timber post at a metre, so **everything in frame is inside four metres,
and at four metres a scanning sensor's returns are a fabric.** The cave frame solves that
with a lamp cone and nine-tenths black; the belief frame has no lamp and draws every
return it has.

That is worth stating as a finding rather than as a caveat:

> **Shot 17's camera is a hard camera for a belief cut, and the reason is that it is
> close.** The rings are countable at 6–20 m and they merge into a fabric at 1–3 m. The
> cave spike's own scout found stations with 8–24 m sightlines; a matched pair authored at
> one of those would give both registers depth. This is a note for whoever authors the
> final shot list, not a fault in the mechanism — the mechanism puts the camera in the
> same place to five millimetres.

**What changed the frame-0 read, and it is honest rather than a trick.** The first pass
accumulated thirty revolutions over the twelve metres before the camera and the frame came
out a solid fabric of returns with no countable rings and no voids in it — the first
pass's nebula arriving by a different route. Halving the revolution rate (one sweep every
1.6 s of walking rather than every 0.8 s) and dropping the point cap from 3.6 px to 2.2 px
took shot 18 from 964,815 returns to **482,482**, and the rings became countable and the
sensor shadows became holes. Both numbers are inside `ART-DIRECTION` §8.2's own bounds and
neither is a legibility hack: **a sensor that sweeps at 10 Hz produces more data than a
camera can show, and choosing how much of it to draw is a real decision this register has
to make** — `LIDAR.md` §6 already flags it as a Phase 3 belief-map question rather than an
art one. It also reversed the motion-blur verdict (§5.4), which is worth stating plainly:
a presentation choice made for legibility changed which post effects are legal.

**What else helps.** `--cinema=tune` sweeps the recency
window, which is the one presentation control this register has that the cave's does not.
Age is already mandatory — §8.2's "an old return is dimmer and stays where it was believed
to be" — and turning the knee down to about nine seconds makes the live sweep the subject
and leaves the accumulated map as a dim ground. Because the machine is walking *away* from
the camera, the near wall was scanned seven seconds ago and the passage ahead is being
scanned now, so age produces a depth cue out of what the machine actually believes rather
than out of a falloff it does not have. The eight variants are in `shots/cinema/tune/`.

**What still says "not the same place":**

1. **The dressing.** The two projects agree about the *workings* — the passage, its
   section, the sets, the rail, the pipe, the spoil, the beacons, because the topology
   says where those are — and disagree about the *litter*, because one draws it from an
   ordered RNG and the other from a hash. In shot 18 the cave has a tipped tub and a
   breakdown block this spike does not.
2. **The prop orientation.** Corridor props here are placed with the lateral axis pinned
   to world Z; the cave rotates them to the drive's local frame. Over stations 68–90 the
   drive bends about 20°, so the sets are skewed relative to the cave's by roughly that.
3. **Shot 18 has no machine in it and neither does shot 17.** The cave's own entry says
   so. Both are plates.

---

## 8. The measurements, and what they are worth

**Safe at any time, and these are the numbers to quote:**

* **One draw call for the belief layer at every point count in the list**, 224,036 to
  1,517,578 returns. Six when shot 21 turns the truth layer on (five surface meshes plus
  the cloud).
* Point counts per shot: §6's table.
* The bake is not a frame cost: 3.1 s for shot 20's seven revolutions, 25 s for shot 19's
  forty-six. `LIDAR.md` §8 already records that this is GDScript raycasting and would be
  the sim's job in Phase 3.
* The residuals in §2.3, which are geometry and do not depend on the clock.
* The pair measurements in §5, which are pixel counts.

**Deltas only, and read the throttle before you read them.** `--cinema=cost` runs a
leave-one-out GPU timing, interleaved A/B, three blocks of 110 frames each, on shot 18's
camera at 482,482 returns. `nvidia-smi` reported the adapter at **84 °C and 780 MHz against
a 2100 MHz maximum — a 2.7× throttle — at 100% utilisation** at the start of the run, so
every number below is inflated by roughly that factor and **none of it is a frame rate.**

```
  effect     all      without    delta
  tonemap   35.36 ms  34.78 ms  +0.57      <- first block, warming up; ignore the absolutes
  bloom     11.71     10.73     +0.98
  dof       11.84      8.30     +3.54      the most expensive thing in the stack
  mblur     11.91     11.51     +0.40
  grain     11.81     10.58     +1.22
  vignette  11.68     11.51     +0.17      <- what ships
  ca        11.69     11.16     +0.53
  distort   11.45     11.38     +0.07
  grade     11.67     11.57     +0.10

  no post    5.07 ms   (1 draw call)
  what ships 7.06 ms
  everything 11.43 ms  -> the whole stack is 6.36 ms
```

The nine leave-one-out deltas sum to 7.58 ms against a whole-stack figure of 6.36 ms —
19% apart, which on a machine throttling by 2.7× is about as well as the parts are going
to add up to the whole, and it is the only reason to believe the table at all. Depth of
field is over half of it and is also the effect that breaks the most rules, so nothing
hangs on the number.

**Two earlier runs of exactly this code produced tables that were not usable, and both are
worth recording because both looked like results:**

* The first produced **nine rows of 0.00 ms**. Godot does not measure a viewport unless
  `RenderingServer.viewport_set_measure_render_time` has been called on it, and it returns
  zero for ever if you forget.
* The second produced **negative deltas** — `vignette` at −10.31 ms, `dof` at −3.80 ms —
  which is arithmetically impossible for a leave-one-out. Two Godot processes were on the
  device because two of my own background jobs overlapped. `tasklist` is not a formality.

---

## 9. Design problems found, which are not art problems

### 9.1 `dressing.gd` breaks the determinism guarantee that `topology.gd` exists to give

`topology.gd` is emphatic, and `DETERMINISM.md` is behind it: no floats, no engine RNG,
no dictionary iteration, and a **stateless counter-based hash** so that "the ORDER of calls
cannot change any result". `dressing.gd` then draws its props from an ordered
`RandomNumberGenerator`, so what is at station 68 depends on how many `randf()` calls
happened earlier in the same pass.

The consequence is exactly what §2.3 measured: **two clients of the same cave cannot agree
about what a camera is standing on.** That is not a spike problem. Two clients of the same
match will need to agree about the world in Phase 3, and a replay that re-derives the
dressing will not reproduce it. The fix is the one the topology layer already uses —
`draw(purpose, a, b)` keyed on the station index — and it costs nothing except doing it.

### 9.2 The generator's length is part of a shot list's identity

A shot that names a station is only portable if the *stretch length* is pinned as well as
the seed, because `worked`, the sump and the chamber positions all divide by it. Two
projects that both say "seed 7" and differ in length are looking at different caves at the
same coordinates. Either the shot format carries the generator parameters, or the
generator carries a hash the rig can assert against. Right now neither happens and the
number lives in two files.

### 9.3 A copied shot definition has no way to notice it has gone stale

Shot 18's camera is a verbatim copy of a dictionary in another project's JSON. If the cave
re-scouts station 68 — and `spikes/godot/cave/CINEMA.md` §7.3 says shot 17 went through
three stations before it was chosen — the belief cut silently stops being a matched cut and
nothing fails. The two files should be one file, in `docs/` or in a shared `shots/`
directory, with each project reading the entries it owns.

### 9.4 `_ground_y` casts down from a fixed height above the datum

Both rigs find the floor by raycasting down from `station datum + 2.6 m`. Anything
horizontal in the passage below that height *is* the floor as far as the rig is concerned.
This spike's timber cap at 2.05 m triggered it and put every eye-height shot two metres in
the air; the cave's cap at 2.95 m does not, by luck. The ray should start at the anchor's
own nominal height.

---

## 10. Everything I guessed

Everything below is mine rather than read out of a document.

1. **That the exported ground governs rule 3 on a matched shot** (§2.4), and that the body,
   near-plane and line-of-sight rules do not get the same treatment. This is the single
   most load-bearing interpretation in the file and it is the one I most want overruled.
2. **That `ground_from`/`ground_to` apply to the move anchors and not to look or focus.**
   The measured consequence is ≤ 7 mm of residual, but the reasoning is mine.
3. **`frame: "world" | "survey"`**, and the rule that a survey camera may never draw truth.
   TRAILER §8 does not contemplate a camera that is not in the world.
4. **Rule 9's margin**: the cloud's axis-aligned bounding extent plus 0.75 m. A bounding
   box is a crude proxy for a corridor-shaped cloud and would wrongly reject a camera in a
   side passage that the cloud's box happens to span.
5. **That loose corridor rock is not camera collision and everything else is.** The cave's
   own list is 19 named kit parts; mine is "not the `along % 3 == 1` lumps".
6. **The corridor spoil heap**: 0.66–0.89 m radius, squash 0.52, at 0.86 of the half-width,
   on the side the station index's parity chooses. The cave's is a kit mesh at 0.72 of the
   half-width with three RNG scale factors; the parity rule is copied and the size is not.
7. **The timber set rebuild** — 1.95 m posts and a 2.02 m cap scaled by
   `(hw−0.12)/1.18` and `(ht−0.25)/2.02`. Copied from the cave's numbers, but the cave
   applies them through a `basis_dir` rotation and this does not.
8. **Every `cine` bake parameter**: walk speed 0.40 m/s for the following shots and
   1.20 m/s for the survey ones, one revolution every 0.25–1.60 s, and the lead-in and
   run-out cell counts. The walk speed for shot 18 was chosen so the machine and the
   camera keep station; nothing says a machine walks at 0.4 m/s.
9. **The recency window that ships on shot 18**: `age_knee = 9 s`, `age_floor = 0.22`.
   §8.2 gives the principle and not the curve, and `LIDAR.md` §10.12 already flags the age
   curve as a guess. Mine is a different guess, chosen by looking at eight of them.
10. **`max_px = 2.2–2.6` on the close shots** rather than the spike's 3.6, and
    **one revolution every 1.6 s on shot 18** rather than every 0.8. Inside §8.2's "cap
    around 4 px", chosen because at 3.6 px and thirty revolutions everything within 11 m
    is at the cap and the frame is a solid fabric with no countable rings in it. Halving
    the density is the single change that made shot 18 read — and it is also what reversed
    the motion-blur verdict (§5.4), which is worth remembering: **a presentation choice
    made for legibility changed which post effects are legal.**
11. **`t_from` / `t_to`, and that a value ≤ 0 means "relative to the end of the run".**
12. **The scrub windows** for the fold and the fix — 3.0 s before the correction to 1.0 s
    after — and that a 0.7 s eased correction wants about that much air on either side.
13. **Shot 26's and `x19`'s camera altitudes** (36 m and 44 m) and their crop boxes
    (0.55 m and 0.30 m above the station datum). All four were chosen by looking.
14. **That shot 19 is at eye height and 21 mm** rather than at the sensor's own 0.42 m.
    TRAILER does not say, and the first version at machine height was all floor.
15. **`truth_exposure = 0.035`** on shot 21, i.e. a tenth of what this spike calls
    "as authored". §8.3 says 30–40% of exposure and this project's exposure control is not
    denominated the same way.
16. **Bloom's threshold of 0.80** as the value at which the effect is "measured doing
    something rather than measured switched off". The sweep is the real answer.
17. **The 1.5-code threshold** in `beliefcheck.py` for "brighter than background", and
    that mean `|dI/dx|` is a fair proxy for ring structure. It is a proxy; a real one would
    be an autocorrelation at the ring pitch.
18. **That the belief cut's asymmetries in depth of field and chromatic aberration are
    acceptable** while the vignette's would not be. Three lens effects, three different
    answers, and only the vignette one is measured — the other two are my judgement that a
    change of *subject sharpness* reads as a change of register and a change of *corner
    brightness* reads as a change of camera.
19. **That the cost table's 19% shortfall between the sum of the parts and the whole is
    throttling rather than a mistake.** On a quiet machine it should be a few per cent.

### One thing I did not guess, and it should be corrected in the cave spike

`spikes/godot/cave/cinema.gd`'s `_ground_y` casts down from `station datum + 2.6 m`, which
means anything horizontal below 2.6 m is a floor. It is correct there today only because
the cave's timber cap sits at 2.95 m. It is one line and it is a trap. I did not change it:
it is outside this directory.

---

## 11. What I would do next, in order

1. **Export the pose, not the place.** Twenty lines in the cave's `_cin_seq`: write
   position, basis, lens, T-stop and focus per frame at full precision, and have this rig
   play it back and validate it. It removes the dressing from the matched cut entirely,
   removes the exported-ground special case in rule 3, and removes §9.3's staleness
   problem in the same stroke.
2. **Make `dressing.gd` hash-based.** §9.1. It is the same change the topology layer
   already made, for the same reason, and it is the difference between "two clients agree
   about the cave" and "two clients agree about the cave except for what is on the floor".
3. **Author the matched pair somewhere with depth.** §7. The mechanism is proved at five
   millimetres; the frame it is proved on is a hard frame for both registers. The cave's
   scout already knows which stations have an 8–24 m sightline.
4. **Get a ruling on how absolute §8.2 is.** "Nothing may ever be drawn into a sensor
   shadow" is what cut six of nine effects, and it is doing that work correctly. But the
   motion-blur case (§5.4) is a two-pixel smear off a *real* return landing in the first
   two pixels of a void, and reading the rule absolutely costs a moving field of hard
   marks its only defence against temporal aliasing. That is a designer's call, not an
   engineer's, and it is the only place in this pass where the rule and the picture pull
   in different directions.
5. **Re-measure the post stack on a quiet machine.** §8's table is coherent and the parts
   add up to the whole to within 19%, but every millisecond in it is on a GPU at 780 MHz
   of 2100. Nothing in §5's verdicts depends on it — they are pixel counts — but a frame
   budget would.
