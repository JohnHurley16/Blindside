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

---

# The track and the lid — 2026-09-10

Two defects, both named by `ACT-ONE.md` §8 and both in §8's own priority order.

> **§8.6 / ACT-ONE §8.4** — *"The snow does not record what walked on it … Shot 7 is a
> machine walking a course in snow and **the snow behind it is untouched.** It is the only
> place in this act where the frame actively contradicts the design."*
>
> **ACT-ONE §8.1** — *"The pit-head's own ground mesh is a single ArrayMesh spanning the
> site box plus a skirt to **420 m in every direction** … from the collar out to 420 m the
> valley's floor detail — the braid plain, the near lateral moraine's trough, the roches
> moutonnées — is under a flat lid."*

Both are fixed. Fourteen frames in `shots/tracks/`; shots 4, 7 and 12 re-rendered at full
duration into `shots/cinema/seq/`. Nothing outside `spikes/godot/surface/` was modified and
nothing was committed.

## 11. The short version

| | |
|---|---|
| **Does the snow record what walked on it?** | **Yes.** `scripts/tracks.gd`. Feet mark the surface, the marks persist and accumulate, and they read at all three of `DESIGN-PRINCIPLES.md` §4's scales. `shots/tracks/k05_route_behind.png` is a machine on open snow with its own track running out behind it. §12 |
| **How is it accumulated?** | Two buffers, and the split is forced rather than chosen. A **print buffer** stores each footfall's *identity* — centre to 0.8 mm, foot yaw, depth — and the ground shader rebuilds the shape analytically; a **pack buffer** holds three saturating counters that say *how many times*. §12.1 |
| **What does it cost?** | **5.0 MB, fixed** — 4 MB + 1 MB, independent of print count and of agent count. Measured video memory 333.6 → 340.5 MB, which is the buffers plus the bigger ground mesh. In frame time it is **inside the run-to-run noise**: three interleaved pairs of control against `--trk=0` measured the ablation as *slower*, which is thermal drift, not a result. §15 |
| **Does it survive twenty agents?** | **The read side and the storage do, exactly. The write side as built does not, and the fix is fifty lines rather than a different design.** §12.4 |
| **Is the valley floor's detail visible?** | **Yes.** `ground.gd` follows `Valley.h` outside the site box now, over 70 m, and its skirt is graded instead of geometric. The braid plain, the near moraine and the roches moutonnées exist inside 420 m. §13 |
| **Shot 4** | Re-authored onto the braid plain, which is the object `THE-ICE.md` §8.2 asks for and which could not be photographed before. It has a **site anchor** — `braid` — that finds the channel rather than being told where it is. §13.3 |
| **Layout hash** | **UNCHANGED: `701635322695612`.** So are seeds 4242 and 7. Not one integer moved; every change in this pass is on the dressing side of the seam. §16 |
| **Honest verdict** | The close read and the many-times read are good and the teaching claim is delivered. The line-across-the-yard-at-fifty-metres read is the weakest of the three and §17 says why. |

## 12. The track

### 12.1 Four mechanisms were on the table and the answer is two of them

A render target the feet write into; a growing instanced set of print meshes; a decal
buffer; a field the ground shader samples. **The answer is the fourth, in two layers, and
the split is forced by the density principle rather than chosen for convenience.**
`DESIGN-PRINCIPLES.md` §4 asks every environment to carry detail at three scales at once,
and a track has to read at all three:

| scale | what it needs |
|---|---|
| a line across the yard, from sixty metres | a **field**. 40 cm resolution is ample |
| individual prints, from two metres | 1–2 cm of **shape** |
| ground crossed a hundred times | a **counter**, not an image |

One buffer cannot serve the first and second at once without being enormous. A foot is
130 mm across, so drawing print *shape* into a texture wants ~15 mm texels, and 15 mm over
the site box is an 8192-square texture — 67 MB for a single channel. So:

**`_p`, the print buffer. 1024² RGBA8 over a 208 m square centred on (9, 0) — 203 mm a
texel, 4 MB.** It does not hold a picture of a print. It holds the print's **identity**:
R,G the sub-texel offset of its centre (0.8 mm), B the foot's yaw, A its depth. **One texel
is written per footfall — not a splat, one texel** — and the newest print in a texel wins,
which is also what happens in snow. `trk_prints()` in the ground shader reads the 3×3
neighbourhood, reconstructs each print about its stored centre and evaluates a rounded
punch with a rim of displaced snow, **with an analytic gradient**. So a 203 mm texel yields
a print with a 1 mm edge and a correct normal, and the buffer's own resolution never
appears in the picture.

**`_k`, the pack buffer. 512² RGBA8 over the same square — 406 mm a texel, 1 MB.** Three
saturating counters splatted over ~0.6 m per footfall: **R compaction** (~24 machine passes
to saturate), **G refreeze**, **B dirt**. This is the layer that reads from sixty metres,
the layer that says *many times* rather than *once*, and it costs one bilinear tap.

Nine `texelFetch`es sounds expensive and is not, because it is gated twice: only inside
17 m, where a 130 mm print is more than a couple of pixels, and only where something has
actually walked. In a wide frame that is no pixels at all.

**The rim is not decoration.** On a valley floor lit only by the sky there is no sun to
cast a shadow into a hollow, so a depression on its own is nearly invisible — what reads is
the lip of displaced snow around it, because it is the one part of a footprint tilted
enough to catch the bright part of the sky. The first version had no rim and the prints
came back as grey smudges.

### 12.2 The gait is measured, not guessed

`Tracks.learn()` steps the hero's own `walk` clip through one period, reads each foot off
the skeleton, finds the stance window and records the phase and the body-frame offset.
Nothing in it is a number somebody chose. `machine.gd` already measures each foot as the
lowest vertex weighted to its tibia, and the clip is baked in place at `Book.speed`, so the
answer is exact: **0.63 s a cycle, 0.50 m/s, four feet, a 0.315 m stride — 12.7 footfalls a
metre.** Replaying that along a path is then arithmetic, which is what makes six hundred
metres of history affordable.

**This is why `Tracks` is built after `Fleet`.** The prints the yard's history is made of
are the prints *this machine* makes.

### 12.3 The yard has a past, and the course is the part that matters

At build, every route the plan knows about gets walked by that gait the right number of
times: the six walkways ×18, the haul road ×22, the four stations and the collar ×14 each
as short mill-abouts. **141,781 footfalls, laid in 1.8 s, none of them outside the window.**

And then the course gets walked *the way a course is walked*, which is the part the static
wear field could never express. `THE-ICE.md` §7.1's whole claim is that a training course
in snow **shows the policy** — *"where it hesitated, where it turned, where it went twice,
where it went wrong."* A distance field cannot say any of that, because the plan does not
contain a policy. So: root to a leaf, again, again, both ways; and into some branches only
as far as a **threshold**, and then back out, four or five times, which draws a stub with a
beaten circle on the end of it. **That is what being taught not to go somewhere looks like
from above, and it is nine lines.**

Live, `Fleet._mark()` replays the same measured gait along the part of the shot's own path
that has already happened. It is deterministic and frame-rate independent, so a shot has
the same track at three frames as at a hundred and twenty — which matters, because
`--cinema=look` renders exactly three.

### 12.4 Twenty agents

**Storage and reading are unaffected by agent count and that is not a claim, it is the
shape of the design:** the buffers are fixed-size and shared, so twenty agents cost exactly
what one costs to store and exactly what one costs to sample. There is no per-agent state
anywhere in the read path.

**The write path as built does not scale, and it should be said plainly.** A footfall costs
one texel write and a 3×3 splat — about thirty byte operations, which is nothing at any
agent count — but any frame on which a foot lands re-uploads both images, 5 MB. At 0.8 s a
frame of offline capture that is free; at sixty frames a second with twenty agents walking
it is 300 MB/s of pointless traffic.

**The production form of the same design writes the stamps on the GPU** — one instanced
quad per new footfall into a render target with clear-mode never, driven `UPDATE_ONCE` so
the accumulation is exactly-once regardless of how many render passes a frame takes. That
is O(new footfalls) and uploads nothing. **It is a different fifty lines, not a different
design:** the two buffers, the encoding, the gait, the history and the whole of the shader
are unchanged. Flagged as the one thing here that is spike-shaped.

### 12.5 Four things that were wrong first, and what each one taught

1. **The counters were four times too hot, twice.** At K = 0.15 a texel saturated in about
   seven crossings, so every route in the plan came back at 1.0 — which cleared the snow off
   *all* of them, which left nothing for a print to be in, and the yard photographed
   exactly as it had before the file existed. **Saturating a counter throws away the only
   information it has.** The arithmetic that fixes it is in `tracks.gd`: a texel on the line
   is inside the splat of every footfall within 620 mm, which is about sixteen a pass, not
   the four I first estimated.
2. **The dither is load-bearing.** A counter that rises 0.011 a pass is 2.8 of 255 and the
   outer half of every splat is under 1, so truncating rounds the whole *margin* of every
   track to zero and the field comes back as a hard-edged core with no feathering — which
   is the one thing a footpath in snow does not have. Carrying the fraction as a
   probability costs one xorshift.
3. **A beaten path is smoother than the snow beside it.** Feet destroy sastrugi. Without
   knocking the wind relief down inside the track, a 40 mm print sits against 135 mm of
   sastrugi and is *there, correct and invisible* — which is precisely how the first pass
   photographed.
4. **And the yard's gravel bed is a lattice.** `ghf`'s open-ground bed is a 130 mm worley
   with 38 mm of relief. Where the snow over it goes thin — which is exactly where something
   has walked all winter — those stones poke through **on a grid**, and shot 7 came back
   *paved*. Feet press a bed flat; that is what a path is. The same failure appeared in
   shot 4's first re-render as rows of dark ovals on the braid plain, and it had been
   invisible for as long as the only macro in the act was on concrete.

A fifth, and it is the one that decides whether the whole thing looks real: **a machine
does not walk a straight line and its feet do not land on a lattice.** Replaying the
measured gait exactly produced four perfectly parallel rows of evenly spaced dots — a
conveyor, not a track. A slow wander of each pass across the line, plus a per-footfall
scatter of about a foot's width, is what turns it into a track.

## 13. The lid

### 13.1 The agreement

The pit-head owns its own site box, exactly and unchanged: LAYOUT still says where a foot
stands, `ground_mm` is untouched, and the plan hash did not move. **Outside the box the
ground becomes the valley, over 70 m**, and the seam is a 2 % grade rather than a step —
the whole mismatch to blend out is the metre or so of outwash relief at the site.

That direction is the only one that works. Making LAYOUT know about the landform would put
a float and a square root inside the integer half; making the valley know about the
pit-head would put a graded pad inside a 16 km heightfield. This is a **dressing** decision,
the same kind as `relief()`, and it belongs on the dressing side of the seam.

The two meshes still overlap rather than sharing a boundary ring, for the reason `valley.gd`
gives about two graded grids meeting exactly. What changed is that **they now agree about
the shape in the overlap**, so the 0.25 m the ground sits proud of the valley is a constant
offset instead of a lid.

`ground.gd` also carries the valley's two floor masks in **UV2** — all four colour channels
were spoken for — so the braid plain drawn on the pit-head's mesh is the same field the
valley shader draws beyond it, off one function (`Valley.floor_masks`). Two fields that
disagree about where a river is look far worse than one field with no river in it.

### 13.2 The skirt is graded now

The old skirt doubled its ring every step — 2, 3.1, 4.8, 7.4, 11.5 m — which is correct
while the skirt is flat and useless the moment it carries a landform: the braid plain is
58 m wide and the geometric ring out there was 28 m, so it would land on the mesh as two
vertices. That is the identical failure `valley.gd`'s own z-grading was written to fix. The
new bands spend rows where the shape is; the −260…−74 band is the moraine trough and the
braid plain.

**Cost: 65,095 → 77,290 vertices, 129,072 → 153,372 triangles (+19 %), and the ground's
generation goes 1.4 → 3.3 s** because the vertices outside the box each call `Valley.h`.
Total generation 8.2 → 10.1 s, which `NOTES.md` §4.2 already argues is not a number worth
defending in GDScript.

**And one real bug fell out of it.** The valley's hole was the site box ±340 m and the
ground's skirt reached 420 m *from the origin* — so on the +x side the hole ran to 436 m
and the lid stopped at 420, and there was a 16 m ring of nothing. Never noticed, because it
is a sliver seen edge-on at four hundred metres. The hole is ±290 m now.

### 13.3 Shot 4, and a site anchor that finds its own subject

`THE-ICE.md` §8.2 turns shot 4 into *"meltwater running off ice, macro"* and ACT-ONE could
not take it. It can be taken now, and it has an anchor of its own: **`braid`, the only
anchor in `cinema.gd` that is not on the pit-head.**

It **finds** the channel rather than being told where it is, and that is the interesting
part. `river_z` is −150 m, but the braid wanders 60 m either side of that, so the plan's
number names a **band and not a place** — at x = 8 the thread is actually at z ≈ −200, with
the near lateral moraine standing 15 m high between it and the yard. Marching the mask and
taking its maximum is the only way to name the thread, and it costs eighty evaluations once.

Two material corrections came with it, and both are physics rather than taste:

* **The valley floor is not the yard's ground.** Its 130 mm stone worley and its gravel bed
  are suppressed under the braid plain and replaced with a finer, sorted outwash bed.
* **The water is in the lowest part of the channel.** Keying the threads to the braid noise
  alone put them in bands six metres apart wherever the noise happened to be high, so
  whether shot 4 had *any water in it at all* was a coin toss on where the camera stood.
  `river` is the distance into the channel; the melt runs down the middle of it and the
  noise decides which threads are running today and which are dry gravel.

## 14. The drifts, which were third on the list and were ruining the floor frames

`ACT-ONE.md` §8.2 diagnosed this correctly and prescribed its own fix: *"scatter.gd::_drift
instances a rock mesh with the snow material, and the snow material is shaded from world
position … the fix is a per-instance offset into the noise field, not a new mesh."*

There is no per-instance custom-data channel in this batcher and adding one would touch
every bin. **It is not needed: `MODEL_MATRIX`'s own origin is unique per instance and is
already in the vertex shader**, so hashing it gives every drift its own place in the same
field for one hash and one varying. A `snow_body` uniform says *this material IS snow*
rather than *this is a thing with snow on it*, and it is set on exactly one material.

It does the second half too, which ACT-ONE did not name. A drift's **sides** face sideways,
so the up-facing cap misses them and only the wind plaster catches them — which is the other
reason they read as sheets. A bank of snow is snow all over.

## 15. Frame rate, and the machine was NOT quiet

**Checked, and it matters.** `tasklist` at the time of measurement: Brave (two processes),
Discord, Spotify (two), Epic Games Launcher, VS Code, Razer Cortex, Razer Synapse, Windows
Defender, Phone Link. `ACT-ONE.md` §7's numbers were taken on a genuinely quiet machine and
these are not comparable to them. **Only the relative numbers below mean anything**, and the
run-to-run spread today is ±3–5 ms, which is worse than the ±3 ms this laptop is documented
as having.

Same 14-waypoint free-flight path, 1920×1080, MSAA 2×, `day`, no cinematic post stack:

| run | mean | worst |
|---|---|---|
| control | 18.04 ms | 26.60 ms |
| `--trk=0` (print reconstruction off) | 23.00 ms | 35.00 ms |
| `--ssao=0` | 14.85 ms | 29.87 ms |

`--trk=0` measuring **slower** than control is not a result, it is drift, so two more pairs
were taken interleaved:

| pair | control | `--trk=0` |
|---|---|---|
| 1 | 20.73 ms | 21.91 ms |
| 2 | 21.70 ms | 22.22 ms |

**The print reconstruction is inside the noise on this machine today.** It is bought only
inside 17 m and only where something has walked, so in a wide frame it is bought by no
pixels at all; the honest statement is that it costs less than this measurement can see.
The one number that is not noisy is memory: **video memory 333.6 → 340.5 MB**, which is the
5.0 MB of buffers plus the larger ground mesh, and it does not move with print count.

**Ambient occlusion is still the whole of the frame budget**, exactly as `PHOTOREAL.md` and
§7.1 both found. Nothing in this pass touched it.

Render time for the three re-rendered sequences: `t04` 64.0 s, `t07` 79.1 s, `t12` 86.6 s
for 96 frames each — 0.67 / 0.82 / 0.90 s a frame, in line with `ACT-ONE.md` §7.2.

## 16. What did not move

* **The layout hash: `701635322695612`.** Seed 4242 is still `462980458301742` and seed 7 is
  still `526964610805162`. Not one integer in the plan changed.
* `layout.gd` has no new float, no new square root and no dictionary iteration.
* The layout/dressing seam, the arrangement vocabulary, the batcher, the kit, the sky
  shader, the camera rig, the post stack, `props.gd`, `dressing.gd`.
* The four `xfail` shots still fail, correctly and for their own reasons.

**New:** `scripts/tracks.gd`; `--mode=tshots`; `--dbg=22` (the track field: how many times,
how long ago, the print field) and `--dbg=23` (the floor masks); `--trk=N` as an ablation
switch; a `braid` site anchor; a `u`/`tu` ground-relative height in the `tshots` list,
because out on the valley floor nobody has measured the ground and defect two just put
twenty metres of relief inside 420 m.

## 17. What is weak, and what was not reached

1. **The line-across-the-yard-at-fifty-metres read is the weakest of the three.** Close in
   the prints are unambiguous and the beaten ground is unambiguous; at fifty metres, on a
   graded pad, under a sky with no sun, a packed route is a 30 % value difference on a
   0.795 albedo and the frame is already full of white. `k01_yard_line.png` shows it and
   `k09_field_dbg.png` shows the field that is under it, and the gap between the two is
   this item. It wants either a ploughed *edge* — a lane has banks, and banks have
   silhouettes — or accepting that in this light a route reads by its **emptiness** rather
   than by its colour, which is what `DESIGN-PRINCIPLES.md` §7 said in the first place.
2. **Individual prints stop reading at about twelve metres** and are gone at seventeen,
   where the reconstruction is switched off. Between there and sixty metres there is only
   the field. That is the correct trade and it is also a visible seam if you look for it.
3. **`trk_far` and the buffer window are both fixed.** The window is 208 m centred on the
   pit-head, so a machine that walks past x = 113 leaves nothing. For a spike whose subject
   is a 126 × 68 m compound that is fine; for a match it wants the scrolling window this
   deliberately avoided, and a scrolling window has a seam.
4. **Cornices and avalanche paths were not reached.** They were §8.3's item and they are
   still §8.3's item.
5. **The prints are round.** The machine's foot is a ball, so a round punch is right, but
   there is no toe, no heel, no drag on take-off and no spoil thrown forward, and a real
   track is asymmetric in the direction of travel. The yaw is in the buffer and used only
   to orient the ellipse.
6. **Nothing melts and nothing refills.** The counters only ever go up. Snowfall should
   erase a track over hours and a thaw should turn one to ice; both are one decay term on
   the pack buffer and neither is built.
7. **Shot 4 is a frame rather than a macro**, and that is a decision taken against
   `THE-ICE.md` §8.2's own word. At 50 mm from a metre this material is a texture swatch;
   at 50 mm from eye height looking thirteen metres down the channel it is a place. Struck
   individually in §18.
8. **One seed was examined for the pictures**, as ever, though the hash and the print counts
   were checked on three.

## 18. Every guess in this pass

1. **The buffer geometry**: a 208 m window centred on (9, 0), 1024² for prints and 512² for
   the counters, and that the window is fixed rather than following the camera.
2. **Every counter rate** — 0.0077, 0.0028, 0.0021 — and the 0.62 m splat radius. §12.5
   derives them from a footfall count; the target values they were derived *to* are mine.
3. **Every pass count in the history**: walkways ×18, haul road ×22, stations ×14, a taught
   course leaf ×3–9 each way, a turn-back ×3–6 at 55–80 % of the branch. These are the only
   guesses in `tracks.gd` and they are the whole of what the yard's past looks like.
4. **That 42 % of course nodes have a turn-back at all**, and that a turn-back is what
   teaching looks like from above.
5. **The print's shape**: 132 × 104 mm, a rounded punch at exponent 0.75, a rim reaching
   62 mm at 0.55 of the depth, depth 28–58 mm for history and 44 mm for a live walk.
6. **`APPROACH = 8.0`** — that a walking machine's track already runs eight metres back
   along its own line when a shot opens. It is an authoring decision, not a physical one:
   the machine did not come into existence at t = 0, and a track that begins at the first
   frame's feet is a worse lie than one that does not.
7. **Every threshold in the ground shader's track block**: `clr` at `smoothstep(0.50, 0.95)
   × 0.97`, `beaten` at `smoothstep(0.34, 0.90)`, the sastrugi flatten at
   `smoothstep(0.012, 0.42) × 0.74`, the print fade at `smoothstep(0.26, 0.82) × 0.66`, and
   `trk_far = 17 m`.
8. **The beaten-ground colour** — that what is under a foot track is dirty refrozen ice at
   0.17/0.10 rather than the yard's soil.
9. **That the plan's static wear field keeps a job**: at 52 % strength, clearing only,
   because a lane is *ploughed* as well as walked and the plan is a fair account of where a
   plough goes. It no longer draws tracks.
10. **`BLEND_OUT = 70 m`** — how far outside the site box the ground takes to become the
    valley — and every band in the re-graded skirt.
11. **That the valley's hole should be ±290 m** rather than ±340.
12. **That the braid plain's threads follow the channel** rather than the braid noise, and
    the outwash bed at 23 cells a metre.
13. **Shot 4's whole re-framing**: the `braid` anchor at x = 8, eye height, 50 mm, looking
    13 m down-valley at f/4 in `snowfall`. Flagged in §17.7 as the one place this pass took
    a side against the document.
14. **That `snow_body` should exist as a material property** rather than the drift getting a
    mesh or a custom-data channel of its own.
15. **That `--mode=tshots` and its eleven frames should exist**, and every camera in them.

## 19. The frames

Fourteen at 1920×1080 in `shots/tracks/`, captured by `--mode=tshots`. Each one is a
falsifiable claim rather than a flattering angle.

| file | the claim it would disprove |
|---|---|
| `k01_yard_line` | the field reads as a route across the yard from fifty metres. **§17.1: it half does** |
| `k02_prints_close` | individual prints read at a machine's own height, on snow nothing else has touched |
| `k03_many_times` | ground crossed all winter is a different material from ground crossed once |
| `k04_course_policy` | the course draws the policy: taught routes beaten, turn-back stubs, clean snow between |
| `k05_route_behind` | **the machine's own route runs out behind it while it walks.** The frame ACT-ONE §8.4 says does not exist |
| `k06_route_wide` | the same, from far enough away to see where it came from |
| `k07_braid_plain` | the braid plain exists, at 200 m, on the pit-head's own mesh |
| `k08_floor_detail` | the valley floor's relief and erratics exist inside 420 m |
| `k09_field_dbg` | `--dbg=22`: what the counters actually hold, judged without snow, fog or a tone curve on top |
| `k10_floor_over` | the whole site in its landform, from 58 m up — the lid gone, in one frame |
| `k11_moraine` | the near lateral moraine reads as a moraine from the yard |
| `k12_shot4_melt` | TRAILER shot 4, re-rendered on the object `THE-ICE.md` §8.2 names |
| `k13_shot7_course` | TRAILER shot 7 — the frame that used to argue against the design |
| `k14_shot12_alone` | TRAILER shot 12, with the track that makes *alone* a fact rather than a composition |
