# The valley — the surface rebuilt for the ice, 2026-09-09

`DESIGN-PRINCIPLES.md` §10 gave the game a period and a place:

> *"it's a society that lives in a world that is coming out of an ice age and discovering the
> society that existed pre ice age. so it's all monotonous and snowy and pretty, they live in a
> valley in a somewhat futuristic town."*

and the same day extended it:

> *"the background in the outside can be massive mountains with some civilization built up in them"*

`docs/THE-ICE.md` is the reconciliation and it carries the numbers. This pass builds what it
specifies: a valley floor, two walls, a horizon of peaks, a terraced town on the far wall that
straddles the trimline and gets newer as it comes downhill, and snow as a material. The pit-head
did not move in world space and almost nothing in it was thrown away — **THE-ICE 7.4's ruling that
"the pit-head is still a pit-head" is the reason this was affordable at all.**

Read `NOTES.md`, `ORDER.md` and `PHOTOREAL.md` first. Where this file disagrees with them about the
landform, the light, the ground material or the frame rate, **this one is current**; everything they
say about the layout/dressing seam, the arrangement vocabulary, the batching and the capture stack
is unchanged and still governs.

---

## 0. The short version

| | |
|---|---|
| **What it is now** | A 1.2 km-wide glacial trough with 1,800 m walls, a town of ~500 buildings on twenty contour terraces at 900–1,300 m, a glacier 3 km up-valley, and the same pit-head on the floor of it |
| **What was kept** | The whole layout/dressing seam and its integer plan hash, the arrangement vocabulary, every prop, the batcher, the kit, both existing shaders, the sky shader, the camera rig and the post stack |
| **What was replaced** | The horizon (a flat skirt → 16 km of landform), the ground material's top layer (concrete → snow over concrete), the weather presets, the weeds, the decal colours, and the wall rock |
| **New files** | `scripts/valley.gd` (the landform), `scripts/town.gd` (the settlement), `check.sh` (a parse gate) |
| **Frame rate** | **95.6 → 57.1 fps mean, 60.0 → 38.1 fps worst**, measured before and after on this machine today. §7 |
| **Layout hash** | still printed every run, still reproducible per seed, moved twice because the plan gained fields. §2 |
| **Honest verdict** | The valley reads at scale and the snow is convincing underfoot. The mountains are structured but not yet photographic; the town reads as a hill settlement at a kilometre and as boxes at two hundred metres. §8 |

---

## 1. What was kept from the pit-head, and what was replaced

THE-ICE 7.4 lists what should survive. Everything on its list did.

| | verdict |
|---|---|
| `layout.gd` / dressing seam, integer millimetres, no float, no dict iteration, printed plan hash | **kept, extended.** Four new integer fields, hash covers them |
| `ORDER.md`'s twelve arrangements, ranks, stands, walkways, clear rects, swept ground | **kept verbatim.** Not one line changed |
| `batcher.gd`'s three-bucket MultiMesh chunking | **kept, plus a fourth bucket** (`FAR`) for the town |
| `kit.gd`'s 24 unit meshes | **kept verbatim.** A town is boxes, cylinders and chamfered boxes |
| `materials.gd`'s `SOLID_SHADER` and its material table | **kept, extended.** Four rows added, one term added |
| `GROUND_SHADER` — ~800 lines of weathered concrete | **kept whole and now mostly covered.** §4.3 |
| `weather.gd`'s sky shader | **kept verbatim.** Winter is three new presets, not a shader edit |
| `cinema.gd` / `lens.gd` / `postfx.gd` / `shoot.gd` | **untouched** |
| `props.gd`, `dressing.gd`, `fleet.gd` | **untouched** |
| the `g_wet` global-uniform pattern | **kept, and copied** — `g_snow` is its twin |
| **replaced:** the geometric horizon skirt | it is landform now |
| **replaced:** the three weather presets | `day` / `firstlight` / `dusk`, with `snowfall` where rain was. Old names alias, so every existing shot list and benchmark still runs |
| **replaced:** the weeds in the margins | wind-aligned snow drifts, on the same placement rule |
| **replaced:** the decals' colours | a stain under snow is a grey bruise, a track is compacted snow |
| **lost:** the puddles | buried. `g_wet` still drives melt, and the braid plain is where water is now |

**The single most reused thing is not a file, it is a rule.** `DESIGN-PRINCIPLES.md` §7's *"clear
ground is a feature — traffic lanes, turning circles, the apron in front of a bay and the ground a
machine walks are kept clear, and their emptiness reads as use"* stops being a placement rule in
snow and becomes a photograph. `ground.gd` already baked a wear field from the six walkway
polylines, the haul road and the four stations; the snow layer reads that same field and lies
everywhere the plan does not say machines walk. **Nothing was added to the plan to make that work.**

---

## 2. The valley's numbers, and where each came from

All of these are integers in `layout.gd`, all in millimetres, and all are hashed.

| quantity | value | source |
|---|---|---|
| valley floor, toe to toe | **1,200 m** | THE-ICE 7.2 |
| near wall toe / far wall toe | **z = −300 m / +900 m** | **mine.** 7.2 asks for a 1.2 km floor *and* a far wall at ~900 m; those are only both true if the pit-head is off centre. It is, and it is the better composition: one wall to loom at 300 m, one to live on at 900 |
| wall height to the ridge | **1,800 m** | THE-ICE 7.2 |
| wall profile | 63° at the toe → 21° at the ridge, six control points | **mine.** §3.1 |
| the trimline | **+310 m** | THE-ICE 3 |
| the snowline, today | **+1,100 m**, with a 90 m bare band under it | THE-ICE 3 |
| the ridge's shadow line (alpenglow) | **+1,250 m** | **mine.** THE-ICE gives no number. §5.2 |
| peaks | 2,610–3,260 m, 4.3–9 km out, twelve of them | THE-ICE 7.2's band; the positions are mine and were moved once, §3.3 |
| the town | foot **+90 m**, body **+120…+380 m**, oldest **+520 m** | THE-ICE 7.3 |
| the town's run along the valley | **x −1,560 … +180 m** | **mine.** §6 |
| glacier terminus | **3 km up-valley** | THE-ICE 3 |
| head wall / valley mouth | +6.6 km / −7.8 km | **mine**, to close the view at THE-ICE 7.2's 6–8 km |
| lateral moraines | 26 m high, 150 m inside each toe | **mine** |
| meltwater braid plain | 58 m wide, hard against the near wall | **mine** |
| drawn extent | **16 km**, camera far plane 17 km | **mine** |

**One number in THE-ICE cannot be built as written and I took the other side of it.** §7.2 puts the
far wall at *"~900 m — deliberately close. The town has to read as **buildings**, not as texture"*,
and §7.8 puts the pit-head *"3–5 km of haul road up the valley"* from the town's foot. At 3–5 km a
building is four pixels. I built the 900 m, because 7.2 uses it three times and 7.5 repeats it, and
because the whole argument for the town is that it is the one object whose size a viewer knows. The
haul road is therefore **~2 km**, and the town is a long settlement strung along 1.7 km of wall
rather than a compact one further off. Flagged as guess 1.

**The plan hash.** It moved from `190631341776686` to `701635322695612` and is printed on every run.
It moved because the plan gained `valley`, `peaks`, `town` and `haul`, which is the correct
behaviour and the same event as the walkway rule in `NOTES.md` §2.1.16. Four headless runs:

```
seed 20260908  layout hash 701635322695612  56425 instances
seed 20260908  layout hash 701635322695612  56425 instances
seed 4242      layout hash 462980458301742  55521 instances
seed 7         layout hash 526964610805162  55683 instances
```

`layout.gd` still has no float literal, no float operation, no square root and no dictionary
iteration. The town generator (`_town`) is integer throughout, and so is the wall-profile query and
its inverse.

---

## 3. The landform

`scripts/valley.gd`. One indexed `ArrayMesh`, one draw call, 107,424 vertices and 208,712 triangles
for sixteen kilometres of landscape — fewer vertices than the pit-head spends on 170 metres.
`cast_shadow` is OFF (the nearest thing in it is a wall toe at 300 m; the sun's shadow range is 95).
It draws under the pit-head's own mesh, 0.25 m below the floor datum, so the two never have to share
a boundary ring: at 420 m a 0.25 m step is a third of a pixel.

### 3.1 The wall

**U-shaped, over-steepened at the base, which is what ice does.** 63° at the toe, 55°, 50°, 48°,
then easing to 33° and 21° at the ridge. This is the change that makes rock possible: nothing holds
snow on 63°.

**Buttresses and gullies are RIDGED, not smooth, and that is the single biggest improvement in the
pass.** The first take used three bands of ordinary value noise on the fall line and produced what
the designer accurately called a mound: *a wall with dents in it*. A mountain is a set of buttresses
separated by gullies, and what distinguishes those from bumps and dips is that the boundary is a
**crease** — a line, not a curve. Ordinary noise has no creases at any amplitude. Ridged noise
(`1 − |2n − 1|`) folds the field about its midpoint and has a sharp maximum along a locus. Three
bands of it — a 240 m spur system, an 80 m gully system, 28 m ribs — perturb the fall line *before*
the profile is applied.

Also in: **arêtes** (the same ridged field sharpens the crest over the top third, so ridges are
where two faces meet rather than a rounded shoulder), **hanging valleys** (three per wall, one
subtraction each), and **rock that is broken above the trimline and scoured below it** — the one
place the trimline is geometry rather than material.

### 3.2 Talus, and why it was missing

Every rock face sheds and what it sheds piles at the angle of repose in an apron at its foot,
spilling out over the valley floor, and becoming a **cone** where a gully discharges. The first take
had a hard line where the wall met the floor. There is now a scalloped skirt of fans along the whole
length of both walls, keyed to the same gully field, and it is where the deepest snow above the
floor lies. The sequence a player sees from the floor is now

> flat floor → deep snow apron → bare rock wall → snow-filled gullies → upper slopes → white ridge

and **that sequence is the picture**.

### 3.3 The peaks, and a geometry check the first list failed

THE-ICE 7.5 is right that mountains are nearly free — they cost 1.2 ms of a 17.5 ms frame (§7). But
a peak only exists if it clears the ridge in front of it, and the first list did not. From the floor
the far ridge is 1,800 m at 3.2 km — 29° of elevation — and a 3,050 m peak at 5.2 km is 30°. It
cleared by one degree and was invisible in every frame that was supposed to be about it. The twelve
now in the plan are nearer, higher, or both.

### 3.4 The floor

Lateral moraines (two long rubble ridges parallel to the walls — the other unmistakable glacial
signature), **roches moutonnées** (bedrock humps smoothed on the up-glacier side and plucked steep
on the down side, all pointing the same way, which is a direction arrow left in the rock), a
**braided meltwater plain** rather than a channelled river, the **glacier's snout** with a crevasse
field, and **320 erratics** — boulders the ice carried and put down, clustered on the moraine crests
and strung down the flow line rather than scattered. The erratics do a job no mountain can: they are
a known size at a known distance in the middle ground, which is exactly the link THE-ICE 7.2's chain
of scales was missing.

---

## 4. Snow

The hardest thing in the pass and the one most likely to fail. Snow rendered badly is white plastic
every time, and the cause is never the albedo. Four things cause it, and all four are addressed in
one shared GLSL block (`Mats.SNOW`) pasted into the ground shader, the solid shader and the valley
shader the same way the noise block already was.

### 4.1 The four failure modes

1. **Snow is translucent.** Light enters, scatters through a few centimetres of ice grains and
   trapped air, and leaves somewhere else. Its hollows are *filled* with light rather than dark and
   its shadow terminator is wide, soft and coloured. **Ambient occlusion at rock strength is the
   fastest way to turn snow into plaster.** The fix is not less AO — it is an occlusion term that
   goes blue and stays bright as it deepens, plus a wrap-diffuse BRDF.
2. **Its specular is faceted, not rough.** A wind crust is a field of ice facets a millimetre
   across, and it glitters: sparse, hard, violently view-dependent highlights that no roughness
   value produces. `sn_facet()` draws them off a sparse hash lattice, lit by whatever is bright —
   the sky on the floor, the sun on a peak — and faded out by pixel footprint before they alias.
3. **Wind sculpts it.** Every band is stretched 3:1 to 6:1 along one `snow_wind` vector: drifts at
   19 m and 5 m, sastrugi ridges *across* the wind with a scour cut behind each, ripples, crust
   grain. Isotropic noise on snow reads as porridge.
4. **It is not white, here.** THE-ICE 2.6's arithmetic: 0.80 linear under a tenth of full sun is no
   brighter than the yard's 0.24 concrete was under overcast. And THE-ICE 6.1's rule — *"the blue is
   a path-length effect, not a tint"* — is implemented literally: the material is achromatic and
   every blue in it is a function of how far into the snow the light went. `sn_cav()` is the hollow
   detector and it is **zero on open ground**; the first take had it at 0.5 everywhere and the whole
   valley came back the colour of a sensor return, which is precisely the failure THE-ICE 2.6 names.

### 4.2 The BRDF

The materials spike's `NOTES.md` §7.5 names a custom `light()` as its biggest remaining item —
*"which means writing the whole BRDF. That is the biggest single remaining item and it is a day of
work"*. Snow is the material that most needs it, because everything characteristic snow does to
light is invisible to Lambert-plus-GGX. The valley shader has one: **wrap diffuse** at 0.62 (a hand's
breadth into shadow is dimmer, not dark), **transmission** through thin edges (`pow(back, 2.6)`,
which is why a drift lip does not read as plaster at a silhouette), and one broad crust lobe.

### 4.3 Snow on the pit-head, and on 56,000 props

The ground shader gained a snow layer that **finds a level exactly the way the puddle code above it
does** — the edge of a snow patch is where a surface crosses a surface — so it fills the slab joints
first, wraps round the aggregate, banks against the kerbs, and its margin is ragged with no patch
shape authored anywhere. It is cleared where `wear` says machines walk. Compacted snow in the ruts
is denser, glassier and bluer than the snow beside it, which is the same path-length rule used as
**evidence of traffic**.

The solid shader gained two terms and both are cheap:

- **A cap on up-facing surfaces** — THE-ICE 7.4 predicted this was nearly free and it is.
- **Wind plaster on vertical faces**, which THE-ICE does not mention and which turned out to matter
  more. Driven snow packs onto the windward face of anything vertical and streaks *downward* from
  every rib and corner (stretched along world Y, the same instrument as the rust streak, and for the
  same reason: gravity). Without it a snowy yard is a white floor with black objects standing on it.
  **It was set four times too strong on the first attempt** and bleached the containers to 90%
  white, which destroyed `DESIGN-PRINCIPLES.md` §4's two registers — the old iron and the brought
  kit are a *value* contrast before they are anything else, and burying both under one white is the
  snow version of the scatter mistake.

**Drifts are geometry, not shader.** `materials/NOTES.md` §7.4 is explicit that parallax cannot
change a silhouette, and drifts banking against objects are exactly that case. `scatter.gd`'s weed
rule became a drift rule on the *same placement geometry* — the fence line, behind the buildings,
the margins — because `DESIGN-PRINCIPLES.md` §7 had already taught it where the margins are. Every
drift shares one axis and the answer to "who put it there" is **the wind**, which is how a field of
snow lumps avoids being the scrapyard failure in white.

### 4.4 Is it convincing?

**Underfoot, yes.** `v06_snow_macro` is the frame I would put in front of a sceptic: wind-carved
sastrugi running with one wind, tonal variation from crust to hollow, drifts banked at the fence,
dark stems standing out of it for scale. **At working distance, yes** — `v05_floor_yard` has snow
banked against the containers and packed snow streaking their windward faces.

**On the mountains it is only partly convincing**, and §8 says why.

---

## 5. Light

### 5.1 What THE-ICE resolved

THE-ICE 2.7 inverts what `weather.gd` used to believe: a valley floor in the shadow of an 1,800 m
wall **is** a clear-sky north window at the scale of a landscape, so `ART-DIRECTION.md` §2.1's
12000 K is not broken by the surface, it is *described* by it, and `PHOTOREAL.md` §3.4's provisional
call is answered rather than overruled. Four consequences, and every preset is built from them:

1. **The floor has no sun.** The directional light is a weak, very soft, cold key at the shaft's own
   colour, 8.5° across. That is not a cheat: skylight in a walled valley is genuinely anisotropic —
   far more arrives from the strip overhead and the gap down-valley than from a wall 200 m away — so
   a soft cold key *is* the physics, and it is also the only thing giving the yard contact shadows.
   It was set at 0.62 energy first and photographed as no key at all; a snowfield with no key has no
   form, because its only other cue is self-shadowing and that is weak by construction.
2. **The sky is bright and the ground is not.** Ambient up, exposure down, saturation *down* rather
   than up — skylit snow is high-value and low-saturation and pushing it is how the frame ends up
   the colour of belief.
3. **The only warm light is out of reach.** §5.2.
4. **Do not compress the ramp.** Grade for the floor and let the peaks go.

Three presets: `day` (the workhorse), `firstlight` (the trailer's opening), `dusk` (shot 28's
frame). `overcast` and `rain` alias to `day` and `snowfall`, so every existing shot list, benchmark
and capture mode in this spike still runs unmodified.

### 5.2 The alpenglow, and the one physical cheat in the pass

THE-ICE 2.7: *"alpenglow on the peaks is the only sunlit surface in the exterior and the player can
never stand on it. That gives every wide frame a warm third — cold blue floor, warm lit peaks — with
no invented light source."*

**It is drawn as a height threshold with a real N·L against the sun's direction, not as a light.**
This is a cheat and it is flagged. The defence: it is not a *second* sun, it is the first one, still
above the ridge that the valley floor is behind, and drawn as what it geometrically is. A shadow map
covering fifteen kilometres would cost more than the mountains do, and the line it produced would be
a horizontal one anyway, because the thing casting it is a ridge.

The sun sits on the −z side, low. That is a composition decision as much as a physical one: the far
wall — the inhabited one — faces −z, so a sun over there lights the town's wall and leaves the near
wall black. **One wall warm and one wall dark** is what a real valley does at sunrise and it is the
shape of the trailer's opening frame.

### 5.3 Aerial perspective, and a measurement that inverted a conclusion

The first take ran `fog_density` at 0.00060 — 50% opaque at 1.1 km, 70% at 2 km. A debug capture of
the snow mask showed the slope rule **correctly exposing rock across the whole upper wall and none
of it visible**: every mountain was three quarters sky colour before its own albedo got a vote. A
cold clear winter valley has tens of kilometres of visibility. It runs at **0.00013** now — 12% at a
kilometre, 65% at eight — which is aerial perspective separating distances rather than erasing them.
Plus height fog, which is the cold air sitting in the trough and is the cheapest thing in the file.

---

## 6. The town

`scripts/town.gd`, ~500 buildings on twenty terraces. THE-ICE 7.2 is blunt about why it matters more
than the mountains: *"a mountain does not make a machine read small. A chain of known sizes does …
and the load-bearing link in that chain is the town, because it is the only element whose size a
viewer already knows."*

### 6.1 The age gradient, which is the whole idea

THE-ICE 7.3: the society survived the ice **above** the trimline and has been walking downhill ever
since, so **the town's stratigraphy runs downward and gets newer**. `layout.gd::_town()` therefore
*walks downhill*, from the oldest quarter at +520 m to the foot at +90 m, and every property that
says "newer" is a monotone function of how far it has come:

| | oldest, +520 m | newest, +90 m |
|---|---|---|
| terrace depth | 10 m | 30 m |
| terrace run | 150 m | 640 m |
| vertical step | 18 m | 27 m |
| building width | 4.6 m | 15 m |
| building height | 8.6 m | 17 m |
| roof | steep, one ridge each, a saw skyline | flat, aligned, a rule |
| glazing | few small openings | a near-continuous band |
| lit windows | 11% | 30% |
| plan | accreted, wandering | set out, aligned |

**Nothing in the file says "old" or "new".** The gradient *is* the geometry, which is what makes it
legible at 900 m without a word, and it is the same instrument as the mine's index running downward
and getting newer — two societies, both working downhill, both getting better as they went.

### 6.2 The rule that is easy to get wrong

`DESIGN-PRINCIPLES.md` §7 is "density is order, not scatter", and a thousand-year hill quarter is
undeniably irregular. Those are not in conflict. **The upper town is irregular by *accretion*, not by
scatter.** Buildings share walls, sit flush against the neighbour that was already there, and step
along the shelf. Nothing is rotated at random and nothing stands alone in the middle of anything.
What varies is height, width, depth and setback — the things a builder chooses — and never angle or
position, which are the things nobody chooses. Rotate them randomly and the upper town reads as a
rockfall, which is the same failure as the scrapyard.

### 6.3 What makes it read as a mountain village rather than a graveyard

- **Contour terraces.** The terraces ask the *landform* where their own height is, per 15 m segment,
  and follow it. Built against the smooth profile — as the first take was — every shelf floated over
  the gullies and buried itself in the spurs, and the town read as a mobile hanging in front of a
  mountain. A terrace *is* a contour line somebody built on.
- **Cut and fill.** Each shelf is pushed half its depth out over the slope on a retaining wall and
  cut half its depth back into the hill, so what reads at a kilometre is a bright shelf edge with a
  10–30 m dark face under it, twenty times up a mountain. Buttresses under the face give it a
  vertical rhythm, and they are denser going up because an older wall needed more of them.
- **The houses front the drop.** Every house is built out to the edge of its own terrace, where the
  light and the view are. Built at the *back*, as the first take was, the whole town hides behind its
  own parapets and from the valley floor you see a stack of retaining walls and no buildings at all.
- **Stone below, lighter above.** A heavy coursed plinth on the most consistent ground it can find,
  and something lighter on top of it because somebody had to carry it up there. The two-part
  elevation — dark base, paler body, every building at a slightly different height — is the thing
  that reads at a kilometre.
- **Switchbacks.** Anything over about an 8% grade needs zigzags and this hillside is 600%. The road
  traverses each shelf and hairpins to the next, alternating direction, drawn from the terrace list
  so it lands on shelves that exist. From across the valley it is the only continuous line on the
  slope and it ties twenty disconnected terraces into one settlement.
- **Avalanche protection, and it is the best detail here.** A wedge-shaped stone prow behind each
  group of buildings, pointed uphill, to split a moving slab; and staggered wall-dams above the
  terraces. Four boxes a terrace. It says without a word that people have lived here a long time and
  that the mountain tries to kill them.
- **Clustering.** Buildings pack tightly where the terrace is good and are absent where it is not,
  decided by one low-frequency field along the run — the same instrument the yard uses to decide
  where an arrangement stands. Density is a consequence of the ground, never of a coin toss per
  object.
- **Lit windows, sparse.** Two to four openings a face and most of them dark. The first take drew up
  to forty per building and lit half, and the town came back as a spreadsheet. What a hill town at a
  kilometre looks like is a sparse scatter of warm points with big dark gaps, and the **gaps** are
  what make the lit ones read as lights. Nothing in the world emits belief's colour.
- **An inclined railway** down the wall — THE-ICE 7.8's first descent, and the players' register made
  obvious. It is the only straight line on the hillside, which is why it reads: everything else up
  there is horizontal.

---

## 7. Frame rate

**The machine was quiet for every number below** (`tasklist` checked; no other Godot process). Same
laptop, same day, same 40-second 14-waypoint camera path, 1920×1080, MSAA 2×.

| | before (pit-head, overcast) | after (valley, day) |
|---|---|---|
| **mean frame** | **10.46 ms — 95.6 fps** | **17.52 ms — 57.1 fps** |
| median | 10.00 ms — 100.0 fps | 17.26 ms — 57.9 fps |
| p95 | 15.28 ms — 65.5 fps | 24.07 ms — 41.5 fps |
| p99 | 15.97 ms — 62.6 fps | 25.00 ms — 40.0 fps |
| **worst frame** | **16.67 ms — 60.0 fps** | **26.23 ms — 38.1 fps** |
| draw calls max | 744 | 735 |
| primitives max | 2,312,083 | 2,675,115 |
| video memory | 326.2 MB | 333.6 MB |
| generation | 2,707 ms | 8,117 ms |
| instances | 51,042 | 56,425 |

**The delta is −7.1 ms of mean and −9.6 ms of worst frame.** The recorded clean baseline in
`PHOTOREAL.md` is 13.72 ms mean / 18.06 ms worst; this machine ran the same build at 10.46 / 16.67
today, so it is a little faster than the record, and the *relative* number is the one to trust:
**the valley costs about 67% more frame time than the pit-head alone.**

### 7.1 Where it goes, and it is not where THE-ICE expected

Ablations, 25-second runs:

| | mean | worst |
|---|---|---|
| control | 20.52 ms — 48.7 fps | 29.45 ms — 34.0 fps |
| `--ssao=0` | **14.37 ms — 69.6 fps** | 23.68 ms — 42.2 fps |
| `--dbg=20` (valley mesh hidden) | 16.29 ms — 61.4 fps | 25.29 ms — 39.5 fps |
| `--dbg=21` (town hidden) | 21.79 ms — 45.9 fps | 29.04 ms — 34.4 fps |

**THE-ICE 7.5 is right that the mountains are nearly free.** Hiding 208,712 triangles of landscape
buys 1.2 ms against the 40-second control and 4.2 ms against the 25-second one — the run-to-run
spread on this laptop is ±3 ms and swamps it either way. **The town is inside the noise entirely**
(hiding it measured *slower*, which is thermal drift, not a result).

**Screen-space ambient occlusion is still the whole of it**, exactly as `PHOTOREAL.md`'s clean
re-measurement found: 6.2 ms of a 20.5 ms frame, up from the recorded 4.2 ms because it now covers a
great deal more geometry. Turning it off restores a 42 fps worst case. Nobody chooses here; it is
measured. The trade is unchanged from `PHOTOREAL.md`: occlusion is what stops 56,000 props hovering
and it is half of what makes the underfoot work read.

**Generation tripled, to 8.1 s.** 4.8 s of that is the valley mesh: 107,424 vertices, each one a
`Valley.h()` call that walks twelve peaks with a `sqrt` and an `atan2` in GDScript. `NOTES.md` §4.2
already says why this is not a number worth arguing about — in Rust behind GDExtension it disappears
— but it does mean you would generate the surface at match start and not during one, and that was
already true.

---

## 8. What is weak, and what the designer's note is still right about

The designer rejected the first landform: *"those mountains, and pretty much everything, needs to be
way more detailed and picturesque. a bunch of big white mounds dont cut it, where's the rock."* Most
of that is now addressed and the diagnosis was correct in every particular. What remains:

1. **The mountains are structured but not photographic.** They have buttresses, gullies, arêtes,
   bedding, talus fans, hanging valleys and a slope-driven snow line, and they no longer read as
   mounds. They still read as *procedural*: the ridged bands are too regular in period, so a wall
   has a corrugated rhythm a real one does not, and the rock is grey-blue rather than warm. A real
   range has scale-invariant structure and this has three bands.
2. **The far wall is still too white and the reason is viewing geometry, not the rule.** From the
   floor you see a wall almost edge-on: the near-vertical faces the slope rule correctly strips are
   foreshortened to nothing and the shallow shelves it correctly covers are the ones facing you.
   Bedding-driven **outcrops** were added specifically for this and they help, but the honest fix is
   more relief at 50–150 m, which is more mesh.
3. **There are no cornices and no avalanche paths on the walls.** Both were on the designer's list.
   A cornice needs an overhang, which a heightfield cannot hold; an avalanche path with a debris fan
   is doable as a shader term keyed to the gully field and was not reached.
4. **The town reads at a kilometre and not at two hundred metres.** Close in it is boxes with a
   plinth. It has no arcades, no external stairs, no balconies, no visible roof structure and no
   snow cleared from anything.
5. **Nothing moves.** `NOTES.md` §7.4 said this before the ice and it is worse now: a valley with no
   drifting spindrift, no smoke from the town and no water in the braid plain reads as a still.
6. **The snow does not record what walked on it.** THE-ICE 7.1 calls this *"the single most valuable
   object the ice decision produces, and it is not an art win, it is a teaching win"* — a course
   whose floor draws the policy. The ground reads the plan's *static* wear field, so a machine's
   route is drawn only if the plan already knew about it. **Accumulating a machine's actual path is
   not built, and by THE-ICE's own priority ordering it should have been built first.** It is the
   single most important thing left undone in this pass.
7. **The `2.0` normal constant is still wrong in `ground.gd`.** It is fixed in `valley.gd`, where it
   was fatal — see §9 guess 12 — and left alone in the pit-head's mesh, whose whole relief is 1.2 m
   and whose established look is tuned around it. It should be fixed and re-tuned.
8. **One seed was examined.** Same caveat as `NOTES.md` §7.6, now with a town and two walls in it.

---

## 9. Every guess in this pass, in one list

Things this pass decided that neither the designer nor `THE-ICE.md` decided. Strike them
individually.

1. **The pit-head is 900 m across the valley from the town and ~2 km down-valley of it**, not
   THE-ICE 7.8's 3–5 km. §2 argues it; it is the one place I took a side against the document.
2. **The pit-head sits off-centre on the floor**, 300 m from the near toe and 900 m from the far
   one. THE-ICE gives a 1.2 km floor and a 900 m far wall and those are only both true off-centre.
3. **The whole wall profile**: 63° / 55° / 50° / 48° / 33° / 21° over six control points.
4. **The alpenglow shadow line at +1,250 m**, and that alpenglow is drawn as a height threshold with
   an analytic N·L rather than as a light with a shadow map. §5.2. This is the one physical cheat.
5. **The prevailing wind, `(0.80, 0.60)`**, mostly down-valley with a cross-valley component. It
   serves two masters — drift orientation on the floor and plaster on the town's faces — and it is a
   compromise between them, not a meteorological claim.
6. **Every snow number**: albedo 0.795 linear, the path-length blue at (0.80, 0.875, 1.00), the wrap
   at 0.62, the transmission exponent 2.6, the facet lattice at 560/m and 5.8% occupancy, and every
   band amplitude in `snowf()`.
7. **That snow cover is `smoothstep(0.700, 0.880)` on the mesh normal**, plus aspect, plus the
   gully field, plus bedding outcrops, hardened by a final `smoothstep(0.38, 0.62)`. The 30/38/50°
   avalanche physics behind it came from the designer's note; the thresholds are mine and they are
   deliberately *more* aggressive than the physics, for the viewing-geometry reason in §8.2.
8. **Bedding at a 10° dip and a 25 m spacing**, consistent across the whole massif.
9. **Talus at 0.62 gradient (~32°) over the bottom ~130 m**, fanning on the gully field.
10. **Every town number** in §6.1's table, the twenty terraces, the 15 m contour segment, the
    switchback geometry, the avalanche prows and wall-dams, the plinth fraction (32–52% of height),
    and the tower on the top terrace — which THE-ICE does not mention at all and which exists
    because a skyline needs one vertical.
11. **That people are present only as lit windows, two cable cars and a switchback road.** THE-ICE
    7.3 permits *"figures two pixels tall"*; none are built.
12. **That `ground.gd`'s `2.0` normal constant is a bug and `1.0` is correct.** It is: the
    differences are already divided by the real spacing, so the middle term must be 1. On a 1.2 m
    heightfield it is invisible; on an 1,800 m wall it halves every gradient, and it was the direct
    cause of "where's the rock" — every face reported shallow enough to hold snow. Fixed in
    `valley.gd`, deliberately not in `ground.gd`.
13. **The three hanging valleys per wall, six roches moutonnées, and 320 erratics**, and their
    positions.
14. **The braid plain's width and its three-state material** (washed gravel, shore ice, dark
    threads), and that the meltwater is braided rather than channelled.
15. **The three floor snow states** — wind crust, sastrugi, old dirty snow — and their thresholds.
16. **Every exposure, fog and colour number in the three presets.**
17. **That `check.sh` should exist.** A GDScript parse error does not stop Godot: it loads a broken
    scene, prints once, and spins. A capture against a broken build looks exactly like a slow one
    and cost ten minutes of wall clock before anybody noticed the shots directory was not being
    written to. Nothing captures or benchmarks now until it returns 0.

---

## 10. The frames

Sixteen at 1920×1080 in `shots/valley/`, captured by
`--mode=vshots`. `--dbg=1` on the valley shader shows `(cover, above_trim, above_snow)`, which is the
only honest way to ask whether the snow mask is doing what you think rather than judging it through
fog, aerial perspective and a tone curve — it is how §5.3's fog error was found.

| file | what it is for |
|---|---|
| `v01_valley_wide` | the valley from the floor: both walls, the town, the head wall |
| `v02_town_distant` | the town on the wall at ~1.1 km, from the yard |
| `v03_town_close` | the terracing, the age gradient, the switchbacks, the plinths |
| `v04_peaks` | the peaks with alpenglow, at first light |
| `v05_floor_yard` | the valley floor where the machines are, with snow banked on it |
| `v06_snow_macro` | **snow underfoot.** The frame to judge the material on |
| `v07_machine_snow` | a machine in the snow |
| `v08_way_down` | the collar at dusk with the town lit behind it — TRAILER shot 28 |
| `v09_trimline` | the trimline as a line on the near wall |
| `v10_trailer_open` | **the trailer's opening frame** — TRAILER shot 2 |
| `v11_haul_road` | the way out, down-valley toward the town |
| `v12_glacier` | up-valley to the terminus |
| `v13_town_dusk` | the town lit, long lens |
| `v14_course_snow` | the training course in snow |
| `v15_collar_town` | the collar from the yard |
| `v16_snowfall` | the fourth weather state |
