# Phase 1 — the spectator display, third design

Written 2026-09-07, after the gate playtest failed on 2026-09-06. Revised the same day, three
times: after the designer granted the amendment in §0; after he decided the display goes **3D**
and a feasibility spike measured what that costs; and after he fixed the arrangement as
**picture in picture** — one 3D view filling the screen, the other a small clickable inset over
it, and a persistent minimap in a corner.

**Status.** §0's prerequisite is **granted** (commit `0175f69`). The arrangement in §3 is the
designer's decision, not this document's proposal, and it overrides both the panel's flat
two-panel layout and this document's own side-by-side 3D revision. What has survived every
revision, unchanged: the truth channel in §4, the beat sheet in §5, the two big numbers under
near-identical labels, the drawn rival, the machinery countdown, the palette, type and hierarchy
discipline in §6.1–6.6, the cold open, and the shape of the build order in §9.

---

## 0. The prerequisite, granted

`docs/PHASE-1-SPECTATOR-TEST.md`, *Display*, used to say:

> The player sees **belief only**. Ground truth is never rendered during the run.

Every word of this document breaks that sentence, so the second design asked for an amendment
rather than building against a spec that said not to. **The designer granted it on 2026-09-07,
commit `0175f69`.** The spec now reads:

> The **operator** view — what a player sees while playing — is belief only, and ground truth
> is never rendered in it. The **spectator** view draws truth beside belief, because the gate
> asks a stranger to follow a match she is not playing, and a viewer who is as lost as the
> machine has no way to feel the machine being wrong.

The reasoning is kept here as the record, because it is the thing to re-read if this design
fails and someone proposes going back. `CLAUDE.md` says the phase spec wins where it disagrees
with `DESIGN.html`, so the sentence stood until the designer moved it. `DESIGN.html` was
evidence but not authority, and it treated the question as open:

> Ground truth appears in exactly two places: the post-match replay … and the spectator view.
> (line 234)
>
> Whether live spectators see ground truth or only belief. Truth makes matches far more
> watchable — the audience knows the trap is there and the operator doesn't. Belief-only is
> more honest and more tense. **I lean truth for spectators, belief for players.** (line 238)

The reading that makes both documents true: the build shipped the **operator** view and ran the
**spectator** gate on it. The spec's Display section describes what a player sees. The gate asks
a stranger to watch a match she is not playing.

**The invariant is untouched, and §4 is the proof.** An agent's *policy* still never observes
ground truth. The truth channel is one-way to the screen, it is off unless switched on, and
`phase1/match/invariant.py` must still prove that belief and policy cannot reach truth — with
eight rules instead of one. Neither the 3D decision nor the picture-in-picture decision changes
a line of §4. The arrangement decides which rectangle a picture is drawn in; it does not touch
what is allowed to reach a picture.

One consequence of the amendment is worth stating here rather than only in §10.8, because the
picture-in-picture arrangement improved it. `T` hides the truth channel for the second gate
viewing. Under a side-by-side layout that left half the screen black. Under this arrangement it
**forces the belief view into the main slot and puts the `TRUTH HIDDEN` card in the inset**, and
what is left on screen is the belief map at full size with a dark corner — which is the operator
view. The amendment therefore no longer costs a wasted half-screen in viewing two, and Phase 3's
shipping operator layout falls out of this one for free.

**The second thing the spec asked for all along, and never got.** The same Display section says:

> Primary view is a **sparse 3D point cloud** of accumulated sensor returns, orbitable.

The build shipped a `TurntableCamera` at a fixed `elevation=58, fov=0` — an orthographic
projection tilted 32° off vertical that nobody could rotate. That is not orbitable and it is not
3D; it is a flat map drawn askew. The second design's answer was to finish flattening it to
`elevation=90` and argue the case, which is kept and marked overruled in §10.7. **The designer
overruled it on 2026-09-07:** the belief side becomes a point cloud the viewer can orbit, the
truth side becomes the cave in three dimensions with the machine in it, and a minimap carries
the whole cave. The tester's own words were *"it would be easier to understand in 3D vs the 2D
demo,"* and the spec had asked for it before she ever saw it.

---

## 1. What went wrong

A non-engineer watched the eight-minute recording and said nothing until the end; in the
middle she was bored "because there was no interaction going on and if there was it was hard
to tell," and at the end that it was hard to understand and needed more action — "all that
changes is things kinda beep and nothing really is obvious." Scored against the gate, none of
the three available pass criteria was met, and the fourth was structurally unavailable because
she watched a video and the fourth criterion is about a decision. The display showed her only
what the machine knew, which meant she knew less than the machine and could anticipate
nothing, so every event arrived as a report rather than as something she had been watching
come.

She also said it would be easier to understand in 3D. The playtest record filed that as *a
hypothesis about the fix, not an observation*, and it was right to. The designer has decided to
spend it anyway, and the feasibility spike removed the reason to hesitate: **the 3D screen is
cheaper than the flat one it replaces** — 27.4 ms median live against 32.1, with the worst frame
down from 84.1 ms to 33.2, and 6.0 minutes to render the match against 6.3. There is no longer a
performance argument on either side of the question, so it is decided on legibility alone.

Two of her four sentences are about different things and it is worth separating them, because
the picture-in-picture arrangement serves one and only glances at the other. *"Hard to
understand"* is a legibility complaint and every section below answers it. *"There was no
interaction going on"* is partly the video format (§10.2) and partly a real absence: until now
the only input in this project was one key that fires once, and it fired never. **The inset is
the first thing on this screen a viewer can touch and get a whole new picture from**, and that
is a small, honest, second answer to her second sentence — not the reason for the arrangement,
but a consequence of it worth watching for at the slice-1 look.

---

## 2. The design in one paragraph

The screen becomes a cave you can look into, filling almost the whole of it, with the machine's
own map floating over it in a corner as a small live second camera — and clicking that corner
trades them, so the map fills the screen and the cave becomes the corner. The big picture is the
cave as it really is: rock extruded into walls, chambers that read as rooms, warm light on
filled stone, eleven named places, and a camera that behaves like a director — it holds the
whole cave when nothing is happening and moves in on the beat when something is, because at
whole-cave framing a machine is nine pixels and the tester's complaint was that nothing was
obvious. Inside that picture the machine is drawn twice — solid where it really is, hollow where
it believes it is — joined by a rope slung above the rock with a number on it, and because the
camera is usually close, the rope usually leaves the frame as an arrow still carrying its
number: *it thinks it is sixty-five cells away.* The small picture is the map the machine has
built, cool and sparse on black, orbiting on the same shared bearing, holding the whole world at
once so its shape can be seen to smear and to snap; it is flat where the cave has walls, because
the machine cannot measure height, and that is the thesis drawn rather than argued. In the
opposite corner, a minimap: north-up, fixed, never rotating, one pixel per cell, showing where
the camera is looking and where everything else is — the one thing on screen that never changes
meaning. Down the right-hand edge, two numbers of the same size under near-identical labels —
`IT IS WRONG BY 34` and `IT THINKS IT IS WRONG BY 1` — which is the whole game in four words and
two integers with no vocabulary to learn, sitting directly beside the small picture whose claim
the second one is. The cave has named rooms, so it is a place instead of a shape; the rival is
drawn for the first time in this project, so twenty-two beeps acquire an author; and the
machinery's kill cycle is drawn as a clock that counts down in front of a machine that cannot
hear it, six times a match, which is the suspense the middle of the match currently lacks. It is
legible because it takes things away as well as adding them — one meaning per colour, four type
sizes with a nine-point floor, three levels of visual weight, one picture at a time, and a
camera the viewer never has to touch — and because a stranger is told the rules in twenty-two
words before the clock starts. And it is comparable, which the two-panel layout never really
was: because the two pictures take turns in **the same rectangle at the same bearing**, the
comparison is made by alternation rather than by juxtaposition, and the eye is far better at
seeing one thing change in place than at carrying a shape three hundred pixels sideways.

---

## 3. The layout

Default canvas **1600 × 900**, 16:9. Three scenes as before — a 3D truth cave, a 3D belief
cloud, a 2D minimap — but no longer three panels in a row. **One 3D scene fills the main region.
The other is a small inset over it, and clicking the inset trades them. The minimap sits in the
opposite corner and never moves.**

```
x=0  16                                                    1268 1284           1584 1600
+--------------------------------------------------------------------------------+ y=0
| BLINDSIDE  nobody is driving it   CARGO |#|_|   5:34/8:00   BACK BY 8:00        |  52  HEADER
+--------------------------------------------------------------------------------+ y=52
| THE CAVE   what is actually there                             [N]              |  26  TITLE
+-----------------------------------------------------------+--------------------+ y=78
|                                        +----------------+ | IT IS WRONG BY     |
|                                        |[N] ITS MAP     | |         34         |
|                                        |     . : .      | |       cells        |
|          THE MACHINERY                 |   . : : .   . :| | IT THINKS IT IS    |
|              ( O )  LETHAL IN 0:07     |      (o)       | |    WRONG BY        |
|                                        +----------------+ |          1         |
|                                                           |        cell        |
|          O===o- - - - - - - - ->  65 cells                +--------------------+
|                                                           | the beacon it is   |
|                                                           | about to trust is  |
|                                                           | 33 cells from ...  |
|   +-------------+                                         | "I am at the       |
|   |   MINIMAP   |                                         |  junction."        |
|   | . you  ^ riv|                                         +--------------------+
|   | (O)  [cam]  |                                         | IT IS DOING        |
|   +-------------+                                         | DRIVING TO DEP B   |
|                                                           | LAST FIX 1:26 AGO  |
|                                                           | YOUR ONE COMMAND   |
|                                                           | RECALL READY   R   |
+--------------------------------------------------------------------------------+ y=750
| machinery  #        #        #        #        #        #                      |  26
| 100|                       ______________________  how wrong it is             |  60
|   0|_______________________\____________________  what it thinks               |  28
| events   . .  |  .. .  | . .  |  . . . . .  | . .     |   .                    |  36
+--------------------------------------------------------------------------------+ y=900
```

```python
HEADER_H            =   52.0
TITLE_H             =   26.0            # the MAIN slot's title. The inset carries its own.
MAIN_H              =  672.0
TIMELINE_H          =  150.0
MARGIN              =   16.0
RAIL_W              =  300.0            # words, never pictures
MAIN_W              = 1252.0            # w - 3*MARGIN - RAIL_W;  1.863:1

PIP_INSET_FRACTION  =    0.24           # inset = 300 x 161, similar to the main rectangle
PIP_INSET_AT        = "top-right of MAIN, inset by MARGIN"     # (952, 94)
MINIMAP_W           =  200.0            # exactly 1.00 px per cell over the 200 x 120 grid
MINIMAP_H           =  120.0
MINIMAP_AT          = "bottom-left of MAIN, inset by MARGIN"   # (32, 614)
```

**The main region is 1252 × 672, an aspect of 1.863:1.** That is not chosen for its own sake:
the flat design's truth panel was 900 × 486, an aspect of **1.852:1**. The two are within half a
per cent of each other, so **every framing constant in §7.1 survives the rearrangement
unchanged** — `CAMERA_WIDE_CELLS = 225` still fits the 200 × 120 cave with a margin, and
`CAMERA_CLOSE_CELLS = 40` still holds the machinery's 18-cell lethal diameter inside the panel
height. What changes is the scale it is all drawn at, and it changes in the right direction:
**CLOSE goes from 22.5 to 31.3 pixels per cell, and the machine glyph from 54 px to 75 px.**

**The pixel budget, and this is the one place the arrangement costs something the spike did not
measure.** The spike measured two 776 × 500 ViewBoxes and a 300 × 190 minimap: 833,000 scene
pixels, none of them larger than 388,000. This layout is 841,344 + 48,300 + 24,000 =
**913,644 scene pixels, ten per cent more — and the main view alone is 2.17× the largest panel
the spike ever drew.** §6.10 derives what that is likely to cost, says plainly what is
unmeasured, and gives the fallback. Short version: the truth scene's 5.3 ms becomes somewhere
between 5.3 and 11.5 ms, best estimate 8.4; the belief scene's 1.5 ms collapses to about 0.4
because it is drawn into 48,300 pixels instead of 388,000; the net is about **+3 ms**, against
the −15 ms that grouping the chrome text buys in the same build. Nothing has to give, but it is
measured in slice 10 rather than assumed.

**What each region is for.**

| region | job |
|---|---|
| **Header** | The premise and the two clocks. `nobody is driving it` sits there for eight minutes because it is the one fact a stranger keeps forgetting. `CARGO` is the objective as a picture, not a number. |
| **Title** | One line, belonging to **the main slot**, not to a scene: `THE CAVE — what is actually there` or, after a swap, `ITS MAP — what it thinks is there`. Plus that scene's compass tick. It is the only text on screen that changes when the slots trade, and it is what says which picture you are looking at. |
| **Main view** | Whichever scene is big. The place, up close, and only what belief is currently wrong about. It is a stage, not a debug dump: no rival belief, no sound-field interior, no sigma, no policy, no log. |
| **Inset** | Whichever scene is small, live, and clickable. It is a second camera, not a widget, which is why it is drawn **over** the main view rather than beside it in the rail — a picture floating on a picture reads as a monitor; the same picture in a column of labels reads as a chart. §3.7. |
| **Minimap** | Where the camera is looking, and where everything else is. It is the fixed frame of reference for two scenes that can be spun *and* can trade places, and it always shows truth. §3.3. |
| **Rail** | Words only, never pictures. Top to bottom: the two display numbers, the two captions, the action block, the one command, the point-of-no-return line, the map key. Nothing in it moves when the slots trade. |
| **Timeline** | Four rails, full width: the six machinery windows drawn from frame one so the next kill is visibly sliding toward the playhead; the two error traces; the event pips; the clock and the one now-line. |

### 3.1 Which view is big, and why the two were never twins

**Truth is big by default. Belief is the inset.** This is the load-bearing choice in the
arrangement and it was close, so here is the argument in full, including the case against.

**The case for belief-big, which is real.** The game is about a machine's experience of a place
it cannot see. The accumulated map smearing and snapping is what the phase spec calls *"the
single most important visual in the test."* Making the subject of the game the small picture
looks like a category error, and there is a version of this display where the viewer lives
inside the machine's head and glances out at the world.

**The case for truth-big, which wins, and the second reason is the decisive one.**

1. **The gate failed on legibility, and everything legible is on the truth side.** §10.7 already
   concluded that what actually answers the tester is *naming*, not dimension: the filled cave,
   the eleven chamber names, the drawn rival, the countdown clock, the tether with a number on
   it. Every one of those marks lives in the truth scene. The belief scene has no names in it
   **by construction** — the machine does not know what room it is in — so giving the belief
   scene the pixels gives them to the half of the design with nothing written on it.

2. **Pixels buy the truth scene something and buy the belief scene almost nothing, and both are
   measured.** The spike measured the truth side at 9 logical pixels per machine at whole-cave
   framing and unmistakable at chamber framing: area converts directly into legibility there. It
   measured the belief side at **0.35 points per cell** — 6,007 points over 174 × 100 cells —
   reading as "a diagonal of disconnected blobs" at every angle *and* at every size it was drawn
   at. Scaling a sparse cloud up does not make it denser; it puts more black between the dots.
   What makes the belief scene legible is the mapped silhouette (§6.4, belief mark 1), and a
   silhouette is a **texture** — a texture's shape survives downscaling far better than a scatter
   of marks whose individual size matters. So the belief scene is the one that loses least by
   being small and the truth scene is the one that gains most by being big. That is a
   measurement, not a taste.

3. **A deviation needs a referent.** `IT IS WRONG BY 34` means nothing to someone who does not
   know what right looks like. Truth is the referent and belief is the departure from it;
   showing the departure large against an unknown referent is the display we already tested, and
   it failed.

4. **The convention is free.** A world filling the screen with a small second view over it is
   what every game a stranger has ever seen does. She spends none of her eight minutes working
   out which picture is the world.

**And the other one is genuinely one click away.** Not a menu, not a key, not a mode: the inset
is a button that is also a picture, and clicking it puts the belief map at 1252 × 672 with the
cave in the corner. That is a stronger form of "available" than side-by-side offered, because
side by side the belief scene was permanently available *and permanently 652 px wide* — it could
never be looked at properly. Now it can be, on demand, at nearly twice the linear scale it had
before and four times the scale it has as an inset. §3.7 covers the swap.

**Why the two scenes were never twins, and why the cameras are not linked.** The second design
put the two panels at identical size and argued the case in one sentence: *a cell must be at the
same pixel offset within each panel, so a displacement between the panels is a real
displacement.* **That claim is dead.** It died when the two panels went 3D; picture-in-picture
buries it. The spike measured two things no single shared camera can satisfy at once:

- At whole-cave framing the machines are about **nine logical pixels** and vanish against the
  rock; the target beat at 5:45 renders as a red disc with nothing legible on it
  (`p12-beat-h8.0-wide.png`). The truth camera has to come close.
- The belief cloud's whole job is the **accumulated** map, and that needs the whole map in
  frame. At chamber framing the belief scene would hold about 180 points and show nothing.

So the two cameras want different centres and different scales, permanently and by construction.
`camera.link()` couples azimuth, elevation, `scale_factor` **and** centre together — the spike
confirmed it works, one line, bidirectional, and *cheaper* than driving two cameras, because
only one `view_changed` fires — but it can only be used when both scenes want the same framing,
and they provably do not. **The cameras are independent in framing and shared in attitude**
(§6.8). The measured price is 0.3 ms per frame per independently driven camera, 2.1 ms against
the linked case. It is the cheapest thing in this document.

What related the two pictures was never pixel identity anyway. It was **the tether**, which
lives entirely inside the truth scene and joins two poses in one picture, and **the two
numbers**, which are text. Both survive intact and both now carry more weight — §6.9. What is
lost is comparison by *superposition*, which was already spent everywhere except the 8:00
reveal; what replaces it is comparison by **alternation** in the same rectangle (§6.7), which is
the thing this arrangement adds and the flat layout could not have had.

### 3.2 The two 3D scenes, and their framing rules

**A scene's framing rule belongs to the scene, not to the slot. Only its size changes when the
slots trade.** That one sentence settles whether the inset tracks the main view's subject, and
it is worth stating as a rule because the alternative — an inset that mirrors the main view
smaller — is redundancy rather than a second camera.

**Truth.** `TurntableCamera(elevation=72, azimuth=0, fov=0, up="z")`, centre and scale driven by
the director in §7.2, **in either slot**. The cave is extruded to a **wall height of 8 cells** —
one quad per exposed rock face plus a cap over every rock cell, 43,202 triangles, built in 5.1 ms
of CPU and uploaded once at construction for 92.7 ms. It costs **2.2 ms per frame** thereafter at
the spike's panel size, and orbiting it is free, because an orbit needs no re-upload.

Three decisions came out of measurement, and each gave something up.

- **Mesh, not points.** The spike drew the cave both ways at three wall heights and three camera
  angles. The capped mesh reads as a cave: a solid massif with chambers and passages carved into
  it, the SUMP visibly flooded, the chambers visibly rooms. The point version reads as glowing
  dust along the edge of a flat map — *the same picture the belief scene already draws, in a
  different colour* — which is precisely the confusion the two scenes exist to remove, and which
  would be fatal now that the two of them take turns in one rectangle. Cost was not the
  discriminator: 2.2 ms against 0.8–1.2. **What gave: 1.4 ms and the ability to see through
  walls.**
- **`fov=0`, orthographic, not perspective.** The spike used `fov=45` and hit catastrophic
  z-fighting between the rock cap and the floor image — at a 2.6-cell wall the whole cave is
  barred with black stripes, and at 8 cells it degrades to a horizon line but does not go away.
  Orthographic removes it. It also keeps the scale honest, and that is the decisive reason:
  **the near-miss at 5:41 is a distance claim** — 9.038 cells against a 9.000-cell lethal radius
  — and under perspective the near rim of that ring is drawn larger than the far rim, so "the
  glyph is touching the ring" becomes true or false depending on where in the frame the ring
  happens to sit. Orthographic is the only projection in which the target beat is readable as
  the fact it is. It has a third benefit this arrangement now depends on: **an orthographic
  picture rescales without reprojecting**, so a scene that changes slot is the same picture at a
  different size and nothing in it foreshortens differently. Under perspective a swap would
  subtly redraw both pictures and the eye would lose the feature it was tracking. **What gave:
  occlusion is slightly worse at low elevation, because there is no foreshortening to look past.
  §3.4's clamp already covers it.** Belt and braces on the z-fighting: the floor `Image` is drawn
  only over walkable cells and left transparent under rock, so the cap carries the rock colour
  and the two surfaces are never coplanar.
- **Wall height 8, not 3.** The spike guessed 8 and measured 5, 4, 3, 2.6 and 2; the choice is
  made here. Three cells still needs the z-fighting fix, reads as a kerb rather than as rock, and
  buys floor visibility that §3.4's clamp buys more cheaply. **What gave: the occlusion table,
  which is why §3.4 exists.**

**Belief.** `TurntableCamera(elevation=72, azimuth=0, fov=0, up="z")` — the same attitude, its
own framing, **in either slot**. It holds a **fixed frame the size of the true cave, from frame
one**, and does not fit itself to the cloud. That is the spec's requirement rather than a
preference: *"empty space must read as absence, not as fog."* A camera that zooms to fit the
points makes the map always full, so the unmapped rest of the world is never on screen, and at
0:30 a 251-point smear would fill the frame and read as a complete map of a small cave. The
frame's **centre** eases, at most once every ten seconds, to keep the believed pose inside the
middle 60 % — which is what stops the map walking off the edge as the error reaches 91 cells by
8:00.

**So in the default arrangement the two framings are complementary, and that is the point.** The
main view is at chamber framing on the beat; the inset holds the whole world. Neither is a
smaller copy of the other, and between them the screen always has both a close shot and an
overview. After a swap the same pair is inverted: the whole map fills the screen and the beat
continues in the corner at 7.5 px/cell — where a lethal disc is 135 px and a machine standing on
its rim reads as *something is happening over there*, which is exactly what an inset is for.

**What the inset gives up, stated rather than implied.** At 300 × 161 the belief scene draws the
whole cave at 1.33 px/cell. Individual points are not resolvable; the silhouette, the believed
pose, the ellipse and whole-map movement are. That is an acceptable trade because it is
whole-map movement that carries the belief scene's two biggest beats. At 2:21.4 the map slides
34 cells, which is **45 px of a 300 px picture moving at once** — and a small picture moving as a
whole is *more* visible than a large picture whose parts move, so the spoof reads better in the
inset than it did in a 652 px panel. At 8:00 the 91-cell error puts the ghost 121 px from where
the cave says it is, a third of the inset's width.

**Both scenes carry a compass tick.** In the main slot it is a 12 px `Line` at the right of the
title band with a one-character `N`; in the inset it is a 10 px tick in the picture's own
top-left corner. When the two ticks agree, the pictures agree. This is what makes an orbit
readable instead of disorienting; see §6.8.

### 3.3 The minimap

**200 × 120 at (32, 614)** — inset by one margin from the main view's bottom-left corner, drawn
over it. **Exactly 1.00 pixel per cell** over the 200 × 120 grid, so the cave image is uploaded
at its native resolution into a viewport of exactly its own size and is never resampled;
`interpolation="nearest"` is then pixel-exact rather than approximately so. A `PanZoomCamera`
ViewBox with **`interactive = False`**: the spike found the minimap pans on its own drag, and
that is a thing to switch off rather than a feature.

**It always shows truth. It never follows the big view.** Three reasons, and the third would not
be obvious:

- **A minimap is read by glancing, and a glance has no time to check what the map currently
  means.** A reference that changes meaning is worse than no reference, because the viewer will
  not notice that it changed.
- **It is the fixed frame of reference, and it is now the only one.** Two of the three pictures
  can be spun, and those same two can trade places. Exactly one thing on screen has to be the
  same way up, at the same scale, showing the same thing, every time she looks at it.
- **It already draws both sides, so "following the big view" would remove information rather
  than mirror it.** Among its marks are the true pose, the believed pose, and the tether between
  them. It is not a truth map missing belief; it is the one picture on screen that holds both, at
  whole-cave scale, at every instant. A belief-only version of it would be strictly worse and
  would delete the design's own thesis from the corner it is most reliably visible in.

It goes dark with the truth channel under `T` (§10.8), because every mark in it is truth-derived.

**It never rotates and never zooms.** North-up, top-down, always. That is also why it is 2D: a
third dimension on a 200 px map buys nothing and costs the one property that makes it useful.

**Why it is diagonally opposite the inset.** Bottom-left against top-right, as far apart as the
main view allows. Two small rectangles side by side would read as one cluster of widgets and the
viewer would have to work out which is the map and which is the second camera. Diagonal
opposition separates them maximally, puts the minimap in the least-scanned corner — correct for
something that is *never the focus* — and lands it directly above the timeline's left end, so the
two whole-match references, *where* and *when*, are neighbours.

What it draws, and why each earns its place:

| mark | drawn as | why |
|---|---|---|
| cave outline | a 200 × 120 `Image`, uploaded once, walkable pale on rock dark | The shape of the place at a size where the whole shape fits. The only whole-cave truth picture on screen at every instant, including while the main view is at chamber framing. |
| **the camera footprint** | a bone rectangle with a nose showing the truth camera's azimuth, easing with the camera | **The minimap's primary job.** It answers *where is the thing I am watching* and *which way am I looking at it* — the exact question a director camera creates. Drawn whichever slot the truth scene is in. |
| the player, true | a 4 px bone dot | The subject. |
| the rival, true | a 4 px ember dot | The brief asks for the rival to be drawn, and this is where *"the ember is coming"* reads at a glance while the truth camera is elsewhere. During the 236-second fix drought it is the only mark on screen moving with purpose. |
| the believed pose | a 4 px hollow ghost dot, with the tether between the two | **The tether at whole-cave scale.** At 8:00 the error is 91 cells, which at 1 px/cell is a 91 px line across half the minimap. When the truth camera is close and the ghost is off-frame (§6.9), this is where the full length of the lie stays visible. |
| the machinery | a hazard ring at the true 9-cell radius, 18 px across, breathing on the real 75 s cycle and flooding for the four lethal seconds | The countdown is the suspense engine and it runs whether or not the camera is pointed at it. Six times a match the minimap says a clock is running somewhere else. |
| deposits | two cargo rings at the true 12-cell radius, 24 px across | The objective. Static, uploaded once, free. Without them the minimap is a map of a cave with no reason to be in it. |
| the extraction shaft | a cargo mark at the player's shaft, pulsing at 1 Hz after 6:30 | The destination, and what the point-of-no-return line in §5 is about. The only mark that changes state at the end of the match. |
| **beacons — no** | — | Fourteen dots at 1 px/cell is fourteen pixels of noise on a 200 px map, and a beacon is an internal mechanic rather than a place. |
| **the moved beacon — yes** | after 2:21.4, a lie-yellow dot with a dashed line to where the machine still records it | The single exception, because that one mark is the match's story, and because at this scale the 32.7-cell relocation is a 33 px line — a third of the minimap's height, and the most legible drawing of the spoof anywhere on screen. |

Rival belief, contact wedges, sound rings, the point cloud and the trails are **not** on the
minimap. It is an index, not a fourth display.

### 3.4 The elevation clamp, and what "orbitable" now means

This is the one place the spike said something does not fit, and the correction is real.

A capped 8-cell mesh occludes. The spike put a depth-tested marker on every one of the 3,371
walkable cells and counted how many survive, averaged over four azimuths and normalised to
top-down:

| elevation | 20° | 30° | 40° | 45° | 50° | **60°** | 70° | 80° | 90° |
|---|---|---|---|---|---|---|---|---|---|
| fraction of the cave floor visible | 8 % | 24 % | 42 % | 51 % | 60 % | **77 %** | 92 % | ~100 % | ~100 % |

At the "3D-ish" angle a viewer naturally drags to, **three quarters of the floor is hidden**, and
a machine standing on a hidden cell is a machine the spectator cannot watch. That is the failure
this whole document exists to prevent, arriving by a new route.

**Elevation is clamped to 60°–90°. Azimuth is free. Default 72°.** So "orbit" means a full spin
around the compass and a thirty-degree tilt, not a free camera. That still satisfies the spec —
the view is orbitable, the cloud has depth, the walls have visible faces — and it never hides the
thing being watched. 60° rather than the spike's suggested 55° because orthographic projection
costs a few points of visibility that perspective was quietly providing.

The clamp applies to **both** 3D cameras, because §6.8 shares the attitude between them, and it
applies in **both slots**. The belief cloud has no occluder and could be viewed from 15°, but the
spike measured that orbiting the real cloud shows nothing a fixed view did not: 6,007 points over
174 × 100 cells is 0.35 points per cell, and it reads as disconnected blobs from every angle.
Losing a low belief angle costs nothing that was measured; losing the shared attitude would cost
the relation between the two pictures, which under this arrangement is the relation the whole
design rests on.

### 3.5 What leaves the screen, and why

- **The decision graph** (10 boxes, 5 bars, ~30 strings, 292 × 600 px) is **gone**, not moved
  behind a key. The second design put it behind `D`; there is no rectangle left on the canvas it
  can occupy, and a key that produces a broken layout is worse than no key. `decision_graph.py`
  and `node_box.py` are **not deleted** — they hold the two hardest-won vispy workarounds in this
  repo and they are the specification for BLD-152 — but nothing binds them. In the measured match
  its text was unchanged for 36 seconds at a stretch and only four of its strings ever change; a
  non-engineer reads *"am I getting lost? no · 3 of 16 cells adrift"* as noise. The designer's
  brief asks to "know why its doing what its doing", and that is answered by the belief caption
  in the machine's own voice at 15 pt, in the rail, beside a picture of what the reasoning is
  about to hit.
- **The second title band and the second caption band are gone as bands.** With one picture at a
  time there is one title and it belongs to the main slot. Both captions move into the rail,
  stacked, still opposite points of view: the upper one third person about the world and allowed
  to be ironic, the lower one first person as the machine. One above the other is better than one
  under each panel — the irony is a *contrast*, and a contrast reads in one glance rather than
  two.
- **The map key** is cut from seven rows to five, moved out of any scene ViewBox (it currently
  floats *inside* one, at `PANEL_W + 24`) into the foot of the rail, set at 9 pt, and faded to
  40 % after 1:00. A key is a confession that the encoding failed, but a stranger with no
  background needs one for the first minute and does not need it after.
- **The status panel** goes from five rows to three and becomes the rail's `IT IS DOING` block,
  at the same sizes minus the overprint bug: `ROW_HEIGHT = 30` with a 10.5 pt bold value at
  `row_y + 14` and the next 7.5 pt label at `row_y + 30` means the value strikes through the
  label below it, which is visible in the current renders. `ROW_HEIGHT` becomes 38 and the value
  moves to `row_y + 16`.

### 3.6 Why 1600 × 900, and two measured traps about it

1600 is the smallest width at which a 1252 px main view, a 300 px rail and a 9 pt type floor all
fit. The second design chose it against a recorder cost it had measured wrongly: readback was
believed to dominate at 43.1 ms, and the spike found readback is **13.4 ms** at 2000 × 1125 with
the rest being the draw. Rendering the whole 8:12 match at 20 fps costs about **6.7 minutes** for
this screen against 6.3 for the flat one — and about 4.3 once the chrome text is grouped (§6.10)
— so resolution is not the constraint it was priced as.
It stays at 1600 × 900 because 16:9 is what the recording gets watched on.

**Trap one: `show()` clamps the canvas to the screen; `render()` does not.** On the spike's
machine a window requested at 1600 × 900 became 1923 × 1055 while the hidden recorder canvas
became 2000 × 1125. **The live frame and the recorded frame are different sizes**, so a layout
tuned by eye in the window is not the layout in the mp4. Three binding consequences, one more
than the flat design had: every number in the block above is re-derived from the *actual* canvas
size inside `_layout()`; camera framing is stated in cells rather than in `scale_factor` (§7.1);
and **the inset and the minimap are derived, not placed** — the inset from `PIP_INSET_FRACTION`
and the minimap from one pixel per cell, both against the live main rectangle — because two
hand-placed overlays would sit over different parts of the picture in the window and in the mp4.
The layout is checked at both sizes before the gate.

**Trap two, and it is new: the overlays must not cover the beat.** The inset and the minimap
together occupy **8.6 %** of the main view, in its two opposite corners. At CLOSE framing
(31.3 px/cell) the subject is centred, so the machinery's 9-cell ring reaches 282 px from centre;
its nearest approach to the inset's lower edge is **77 px of clearance** and to the minimap's
**211 px**, and the machine glyph itself is 310 px from the inset. **That clearance, not
aesthetics, is what bounds the inset's size**, and `_layout()` asserts the clearance rather than
the fraction — so a future `PIP_INSET_FRACTION` that covers the machinery fails loudly at start-up
instead of quietly eating the target beat. 0.24 leaves the ring clear with room to spare and is
otherwise a judgement (§10). At WIDE
framing the overlays do cover cave, and that is accepted: WIDE is the framing used when nothing
in particular is happening, and covering a tenth of an establishing shot is the ordinary price of
a HUD.

And a shown canvas and a hidden canvas cannot share a process — the spike reproduced the
`glBindFramebuffer` death that `__main__.py` already documents — so `--record` stays a separate
invocation.

### 3.7 The swap

**Clicking anywhere in the inset trades the two scenes between the two rectangles.** Nothing else
on the screen swaps: the rail, the minimap, the timeline, the header and the two numbers are
fixed, and the *rectangles* are fixed too. Only which scene is drawn in which rectangle changes.

**Interactivity belongs to the slot, not to the scene.** The main slot orbits and does not swap;
the inset slot swaps and does not orbit. A drag inside the inset is not an orbit — the inset's
ViewBox is `interactive = False` and the whole rectangle is one hit target — because a gesture
that might be a click and might be a drag is a gesture the viewer has to be taught, and this
display teaches nothing it does not have to. After a swap the two slots exchange those
properties along with their contents.

**The swap is animated and takes `PIP_SWAP_S = 0.28` seconds.** Both rectangles interpolate `pos`
and `size` simultaneously on a critically-damped curve; the shrinking picture is drawn on top so
the eye can follow it into the corner. Three reasons it is not instant:

- **An instant swap is a cut**, and §6.5 has already ruled cuts out for the camera on the grounds
  that a cut costs the viewer her bearings. A swap moves more than a camera move does.
- **Because the two rectangles are similar** — the inset is 24 % of the main view in each
  dimension, not 24 % of its area or some pleasing size — **neither picture reframes.** Each is
  purely rescaled, so a viewer can track one feature, the machine glyph or the map's smear, all
  the way from one slot to the other, and object identity survives the change. That is the whole
  value of the 0.28 s, and it is why the similarity rule is not cosmetic.
- **0.28 s is under the ~0.3 s at which a transition stops being a movement and becomes something
  you wait for.** Seventeen frames at 60 Hz.

During the swap each camera's `scale_factor` is re-derived every frame from its rectangle's new
pixel size, because framing is stated in cells (§7.1). Two consequences fall out, both handled in
§6.10: text inside a scene is sized in **points, not scene units**, so chamber names would swamp
a 300 px picture — text inside a 3D scene is therefore drawn only while that scene is in the main
slot; and the per-frame `pos`/`size` assignment on a ViewBox is the one thing in this document
that the spike did not measure at all.

**What tells a viewer it is clickable, with no label.** Four things, in descending order of how
much work each does, and the fourth is a concession rather than a device:

1. **It is a live picture over a picture.** This is the reason the inset is overlaid on the main
   view rather than placed in the rail. A moving image floating on another moving image reads as
   a second camera, and a second camera is a thing you expect to be able to switch to. The same
   image in a column of labels reads as a chart, and nobody clicks a chart.
2. **Hover.** The cursor becomes a pointer; the inset's 1 px border brightens from `rule` to that
   scene's key colour over `PIP_HOVER_FADE_S = 0.12`; and a 14 px swap glyph — two overlapping
   rectangles, one `Line`, invisible until hover — fades in at the inset's top-right. **No text.**
   This is the strongest affordance and it only helps someone already moving the mouse.
3. **One demonstration, in the six seconds already reserved for teaching.** Halfway through the
   cold open, after the twenty-two words are up, the inset grows to 40 % and returns, once, over
   `PIP_TEACH_S = 0.5`, with the swap glyph at full opacity. It is shown, not labelled, and it
   costs none of the match. *This is the first thing to cut if the cold open reads as busy.*
4. **She may still never click it, and the design does not need her to.** §7's governing rule
   covers the swap as well as the camera: nothing that matters is ever only visible after an
   input. Every beat in §5 lands with the viewer's hands in her lap, truth big and belief small.
   The swap is for the second viewing, for the designer, and for the viewer who leans in.

**Exactly one swap is automatic, and it is the 8:00 reveal.** At the end of the match the belief
scene moves to the main slot and the true wall outline is drawn over the map the machine built,
in the same rectangle, at the same scale, from the same bearing. The flat design spent the reveal
on side-by-side comparison; **this is better, because it is literal superposition rather than
juxtaposition** — the two pictures are in the same place instead of 300 px apart — and it doubles
as a demonstration of the swap at the only moment in the match where nothing is lost by it. No
other automatic swap exists and none may be added: a display that moves the thing the viewer is
looking at, of its own accord, in the middle of a beat, has taken the picture away from her.

No key is bound to the swap. The affordance under test is the click, and a keyboard shortcut for
it would only make the test harder to read.

---

## 4. The truth channel

This is the section that cannot bend. `CLAUDE.md`'s invariant is:

> An agent's **policy** may never observe ground truth.

A viewer is not a policy. This proposal changes what reaches the screen and changes nothing
about what `Policy.step` can reach. Here is the exact construction, the exact proof, and an
exact statement of what the proof does not cover.

### 4.1 The pipe

```
phase1/truth/                    unchanged, zero lines
        | read by
        v
phase1/match/stage_builder.py    the ONLY new module that imports truth.
                                 Lives in match/ for the reason
                                 phase2/match/reveal_builder.py states in its own
                                 docstring: "This module reads ground truth, which
                                 is why it lives in match and not in reveal."
                                 Imports numpy and truth. Imports nothing from
                                 belief, policy, view or audio.
        | returns
        v
phase1/match/stage_frame.py      @dataclass(slots=True, frozen=True) StageFrame.
                                 Floats, ints, bools, strs, tuples of those, and
                                 read-only ndarrays. No World, no AgentTruth, no
                                 Ancient, no Beacon, no methods, no callables.
        | handed to
        v
phase1/view/truth_panel.py       Consumes StageFrame. Cannot import truth.
                                 Cannot name `.world`.
```

Both new files live in `phase1/match/`. That placement is load-bearing: it is what lets rule 2
below say *a policy cannot name the truth type at all.*

`Sim` grows one method, beside `reveal()`:

```python
def stage(self) -> StageFrame:
    """The live truth export for the spectator panel.

    A deliberate relaxation of reveal()'s `assert self.over`, and a category change:
    reveal fires once, this fires every frame. It is safe because what it returns is
    a frozen record of numbers with no route back to World; because stage_builder
    cannot see Belief or Policy; and because neither belief nor policy may import
    match, so neither can name StageFrame. match/invariant.py proves all three.
    """
    assert not self._in_tick, "a stage frame may not be built from inside a tick"
    assert self._stage_enabled, "the truth channel was not switched on"
    return StageBuilder.of(self._world, self.truth_trail, self.t, self._spoof_arm)
```

`StageBuilder.of` takes the spoof arming fraction as a **parameter** rather than computing it,
because computing it needs Belief and the builder is forbidden to import Belief. `Sim` may see
both; it always could. See §8 — this needs no `tuning.py` change and moves no event.

`StageFrame` carries: `t`; `grid` (120 × 200 uint8, copied once at construction, cached,
`writeable = False`); `player` and `rival` as `(x, y, heading, alive, cargo, load_progress,
stalled_for, in_ancient)`; `trail_player`, `trail_rival` as read-only ndarrays; `beacons` as
`(x, y, owner, moved_from | None)`; `ancient` as `(x, y, radius, signature_strength,
seconds_until_lethal, is_lethal)`; `deposits` as `(x, y, radius)`; `born` — sounds emitted this
frame, as `(x, y, character)`; `error_cells`; `heading_error_deg`; `spoof_arming` (0..1);
`seconds_home`, the true walking time home from a Dijkstra field built once; and
`error_history`, a read-only 2 Hz `(n, 3)` array feeding the timeline's two traces.

`seconds_until_lethal()` in `truth/ancient.py` currently has **zero callers anywhere in the
codebase** — its own docstring says *"only ever used by truth-side logging."* This gives it
one. It is the best suspense asset in the project and it has never been drawn.

### 4.2 The changes to `phase1/match/invariant.py`

Today the file scans `CLEAN_PACKAGES = ("belief", "policy")` for imports of `truth`, and
nothing else. That check is real but narrower than it reads: **`phase1/view` is not scanned at
all, `View.__init__` stores `self.sim`, and `Sim.world` is a live `World`.** The renderer could
read ground truth this afternoon and `--invariant` would still print "invariant holds". The
truth scene does not open that hole; it closes it, in the same commit.

Eight rules. Rules 1 and 2 are what actually protect the policy.

**1. `belief` and `policy` may not import `truth`.** Today's rule, unchanged in text and in
meaning. This is the one that matters most and it is not touched.

**2. `belief` and `policy` may not import `match`.** *New.* `StageFrame` lives in `match/`, so
a policy cannot name the truth channel's type — not to receive it, not to annotate it, not to
construct it. This is the Python spelling of BLD-76's criterion, *"a compile-fail test proves
Policy, Predicate, Action and BeliefUpdater cannot name it."* It is free today:
`grep -rn "from \.\.match\|import match" phase1/belief phase1/policy` returns nothing.

**3. `view` and `audio` may not import `truth`.** *New.* Neither does today, so it passes
unchanged and stands as a tripwire. `audio` is on the list deliberately: a room tone or hazard
drone driven from truth would tell a player how close the machinery really is, through a
channel that scanning `view` alone would never inspect. **This proposal adds nothing to
`audio` and changes nothing in the mixer.** `Mixer.update(belief, t, azimuth)` keeps its
signature.

**4. `view` and `audio` may not contain the attribute access `.world` or `._world`.** *New.*
`self.sim.world` is not an import, so the import scan never saw it. An `ast.Attribute` walk.
Passes today (`grep -rn "\.world" phase1/view` returns nothing) and stays a tripwire.

**5. Allowlist: the only files in `phase1` that may import `truth` are `truth/*`, `sensing/*`,
`match/sim.py`, `match/headless.py`, `match/reveal.py` and `match/stage_builder.py`.** *New.* A
package-by-package scan only catches leaks in the packages someone thought of. An allowlist
makes every *new* truth reader a deliberate, reviewable edit to one line in one file. This is
the check that survives the module that has not been written yet.

**6. `match/stage_builder.py` may not import `belief` or `policy`.** *New, and the only rule
here that closes the **return** path.* A module that can see `World` and `Belief` in the same
scope is one convenience line away from being a fusion point, and that is exactly the leak
`CLAUDE.md` warns will not be visible for months. The exporter cannot see belief, so it cannot
be tricked into feeding it.

**7. An AST shape check on `match/stage_frame.py`.** *New.* Every dataclass in that module must
be declared `frozen=True, slots=True`, and every field annotation must be drawn from
`{float, int, bool, str, tuple[...], np.ndarray, None}` or another dataclass in the same
module. A future *"just pass the World through here"* becomes a test failure at the
**declaration**, which is where someone will actually write it — not a runtime check that only
inspects the values that happen to exist in the frame it built.

**8. Structure, not spelling.** Rules 4 and 5 are name-based AST walks, and a name-based walk
will miss `getattr(self.sim, "world")`, a re-export, or a module-level alias. Two changes
remove the reachability rather than detecting the reach:

- `Sim.world` → `Sim._world` (16 call sites, all inside `match/`).
- `View` is handed a `MatchView` facade, not `Sim`: `t`, `over`, `result`, `recall_used`,
  `recall_pending`, `beliefs`, `policies`, `recall()`, `stage()`, `reveal()`. There is no
  attribute chain from anything the renderer holds to a `World`.

Three more things that are not rules but are part of the same guarantee:

- **A runtime tripwire.** `Sim.step()` sets `self._in_tick = True` for the duration of a tick;
  `Sim.stage()` asserts it is `False`. No frame can be built from inside a tick, so no sensor,
  belief or policy path can route through one even by accident.
- **Arrays are copied *and* frozen.** `arr = src.copy(); arr.flags.writeable = False`. A frozen
  slotted dataclass prevents rebinding a field; it does not prevent mutation *through* one, and
  a numpy view onto `cave.GRID` handed to the renderer would be a live write path back into
  `World`. A runtime test builds a frame from a real `Sim` and asserts every field is a plain
  type and every array is non-writeable.
- **The channel is off unless switched on.** `Sim.__init__` takes `stage=False`. `--headless`,
  `--invariant` and any future batch or training path never construct a frame at all, so the
  leak has to be deliberately enabled rather than merely not used.

`python -m phase1 --invariant` still prints one line, and it now means eight things instead of
one.

### 4.3 What this does not prove, stated rather than implied

It does not prove that a `StageFrame` cannot be *passed into* `Policy.step`. What forbids that
is that `policy` cannot import `match` (rule 2), that `Policy.step(t)` takes no such parameter,
and that the object is constructed in `match/` and handed only to the view. In Python that is
the ceiling. The compile-time guarantee is BLD-123's job in Rust, and `StageFrame` is
deliberately shaped as `ReplayFrame` (BLD-76, BLD-145) at one-tenth scale so Phase 5 does not
have to improvise it.

It does not prove anything about reflection. `phase2/match/invariant.py` already says this
plainly and the same words apply: Python hands every object the whole process, and
`().__class__.__base__.__subclasses__()` walks to any loaded class without importing anything.
That is deliberate malice, not the accident this guards against.

It does not audit the sensor layer. `sensing/` is still the one module permitted to read both,
and its guarantee is still that it can be checked by reading it. **This proposal adds no public
accessor to `SensorRig`.** An earlier draft wanted one, to expose the already-built sound
fields so the truth scene could draw wavefronts that pour down passages and turn corners. That
would have widened the audited module and created a second unscanned door out of truth — and
`belief/belief.py` already imports `sensing.returns`, so nothing in rules 1–8 would have caught
it. Sound origins are drawn instead as plain expanding circles from the true origin, which the
exporter already has from `World.events`. If passage-following wavefronts are wanted later, the
exporter builds its own `SoundField` inside `stage_builder.py`, and it is slice 10.

---

## 5. Beat by beat

Seed 7, sonar, Recall not sent — the exact match the tester watched. Distances and times below
are measured from the headless run and from a Dijkstra over `WALKABLE`, not estimated.

The machinery's cycle is fixed: `phase(t) = (t + 30) mod 75`, lethal for the last 4 s, with a
signature over the 9 s before that. So the **six lethal windows are 0:41, 1:56, 3:11, 4:26,
5:41 and 6:56**, and the warnings begin at 0:32, 1:47, 3:02, 4:17, 5:32 and 6:47. That
seventy-five-second heartbeat is already in the sim, it is perfectly regular, and it has never
been drawn.

| t | true | believed | truth scene | belief scene | feeling |
|---|---|---|---|---|---|
| **−0:06** | — | — | The cave fades up from black under 22 words: *no radio. you cannot drive it. it must bring two loads home in eight minutes. you can call it back once.* | black | *I know what I am looking at before anything happens.* The only place in eight minutes where anyone is told anything. |
| **0:00** | Two machines 174 cells apart, one at each shaft | Both know their own shaft and nothing else | A lit cave with eleven named rooms, two machines, two deposit rings at their true 12-cell radius, a magenta ring in the south-east labelled `MACHINERY`, breathing | Black; three hollow green rings and one hollow chevron | *A place, two machines, a race.* Today: black, one triangle, three stars. |
| **0:16–0:27** | Rival pings from 170 cells | A bearing arrives, roughly east | A ring is born **at the rival** and crosses half the cave | A faint wedge from the machine pointing where the sound came *in* from — and it stays, at 12 %, forever | *That faint line is that machine over there.* The core mechanic taught in one shot, unprompted. |
| **0:30** | error 2.0 cells | σ 2.4 | The two trails separate visibly for the first time | The map has a shape now: a stubby smear from the shaft toward C1 | *This is working.* You need the baseline in order to feel it break. |
| **0:39** | First beacon dropped | Recorded about 2 cells off | A warm diamond | A ghost diamond nearly on top of it | First instance of "same thing, two places". |
| **0:41** | **Window 1 — lethal, nobody near** | nothing heard | The countdown reaches zero and the disc floods for four seconds. The machines are 46 and 106 cells away | nothing | *That kills things. Nothing was in it. It will happen again.* Currently invisible. |
| **0:58.9–1:29.0** | **30 s motionless: loading at deposit A.** The rival closes from 62 to 56 cells | "loading" | The machine sits still inside `DEPOSIT A`'s green ring, which fills clockwise, while **the rival's ember comet crosses a third of the cave** | A bar creeps | **The first stretch of dead air, fixed by showing what is approaching.** Motionless is not static once something is coming. |
| **1:28.9** | cargo 1 | cargo 1 | The deposit ring flashes | — | The header's cargo block fills. The objective visibly advanced. |
| **1:44** | An honest fix, 2.2 cells | jump 2.2, surprise 0.3× | The ghost jumps *toward* the solid machine; the tether shortens | Yellow flash; the cloud eases 2.2 cells over 0.7 s; the **pre-fix silhouette is held as a ghost for 1.2 s** so you can see what moved | *So that is what a correction looks like.* **The most important small beat in the match: it establishes the rule 37 seconds before a liar breaks it.** |
| **1:56** | Window 2, empty | — | Countdown, flood, nothing in it | — | *Every seventy-five seconds.* The rhythm is learned for free, twice, before it costs anything. |
| **2:16.4** | The spoof arms: the victim passes 30 cells from its most recent beacon | nothing | **The beacon behind the machine begins to redden and a ring closes on it.** The machine walks toward it | nothing whatsoever | *It doesn't know. I can't tell it.* The first real suspense in the match — and it costs no sim change, see §7. |
| **2:21.4** | **THE SPOOF. Beacon `player_5` relocated 32.7 cells; fix jump 34.0, surprise 11.2×** | "corrected. I am at the junction, sure to 1 cell." | The diamond **travels** old→new over 0.45 s, turns `lie` yellow, and leaves a permanent dashed line back to where the machine still records it, labelled `THE RIVAL MOVED THIS`. The ghost is flung 34 cells; the tether snaps taut in `kill` red. **The rival is 24 cells away, visible, plainly the author.** | 0.25 s later the whole map slides 34 cells while a ghost of its old shape hangs for 1.6 s | Readout: **34** and **1**. Timeline: a lie pip, `A BEACON MOVED`, and the two error traces split — warm to the ceiling, cool to the floor. *Somebody just did that to it, and it does not know.* Today the entire beat is a dot cloud shifting eight pixels and two lines of text changing colour, and sixteen seconds later the status panel still reads "within 1 cell". |
| **2:25** | Grinding on rock | Driving down a clear corridor | The machine pressed against a wall, comet piling up | The intent line points confidently into open blue space 30 cells away | *I can see the wall and it cannot.* This is what Recall is the answer to. Today: one word changes in a grey box. |
| **2:30–2:35** | The rival closes to 16.2, then 13.9 cells — same chamber | one more amber wedge | Two machines, one chamber, neither aware | — | Dread, drawn. |
| **2:35 / 2:36.5** | **The scripted echo, born at (48, 101) — an empty labelled dead end 50 cells from anything** | A bearing indistinguishable from the 22 rival pings | A ring is born **in `THE ECHO CHAMBER`**, with nothing in it | A wedge pointing at bare rock | *That's not the other machine, that's a bounce.* **The spec's one guaranteed ambiguous beat, drawn for the first time.** Today it draws one arc identical to the other twenty-two, and the timeline's 12 s cooldown eats it entirely. |
| **3:02–3:11** | Window 3 | A magenta wedge blinks for under a second, then a magenta ring settles **40 cells from where the machinery actually is** | Countdown 9…8…7, then flood. Player 55 cells away | The believed-machinery ring, in the wrong place | **Two magenta rings, one right and one wrong, in the same instant in two pictures — one filling the screen and one in the corner.** The display's whole argument in one frame, and it no longer needs the eye to travel to get it. |
| **3:43–4:03.9** | Four small fixes, all from the spoofed beacon | "corrected" ×4 | The *red* beacon answering each time; the tether refusing to shorten | Small yellow flashes | *It is being held wrong.* |
| **4:04–5:30** | **THE DROUGHT. No fix will ever occur again — 236 seconds. Error 34 → 64 cells.** The rival walks to the machinery. Windows 4 (4:26) and window 5's warning (5:32) | σ stays under 4 for most of it | The tether lengthens continuously across a third of the frame; a `LAST CORRECTION 1:26 AGO` row counts up and turns amber past 60 s; the rival's comet runs to the machinery and **stops inside the ring at 5:13 to download**, surviving one window | The warm error trace climbs a long ramp while the cool trace stays flat | **The second stretch of dead air, fixed by making the absence itself the subject.** "Nothing has corrected it for two minutes" is more frightening to watch than another yellow flash. |
| **5:32–5:45** | **THE NEAR MISS. Window 5's warning begins; the machine walks at the ring — 11.5, 10.7, 9.8 cells — and jams at exactly 9.038 against a 9.000 lethal radius. The disc is lethal for four seconds with the machine touching it. Margin +0.038 cells; the rival is at 10.008.** | "I am near deposit A." It is 65 cells from deposit A. | The countdown hand sweeps; the ring thickens through the nine-second warning; it goes solid and pulses for four seconds with the machine standing on its edge | Nothing at all. The caption does not change. | **The best fourteen seconds in the match, currently invisible to the tester, to the designer and to us until a script went looking for it.** |
| **5:45.8** | It steps inside. **0.8 seconds too late to die.** | "near deposit A" | Green machine inside a red ring, the countdown restarting at 75 | — | *Now it's in there and the clock is running again.* |
| **5:56.1** | **The two machines pass at 0.41 cells, both inside the machinery's chamber. Neither notices.** | one amber tone wedge, quality 0.97 | The glyphs overlap | one wedge | *They just walked through each other.* Nothing whatever is drawn today. |
| **6:30** | Extraction opens. The machine is **6.4 cells from deposit B, standing inside it** | "I am lost." | The shaft begins a 1 Hz green pulse; deposit B's ring at its true 12-cell radius has the machine inside it | The header goes orange | *It is standing on the thing it came for.* The reveal currently draws deposits at radius 3 against a true 12 — a lie by a factor of four, and the reason the ending reads as nothing. |
| **6:31.5** | It decides on its own that it is lost, and turns — away from the real shaft | σ 16.0 > 16.0 | It walks the wrong way, confidently | Action line: `TURNING BACK` | *Ninety seconds too late, and the wrong way.* |
| **6:40.5–8:00** | **79.5 s motionless in truth AND belief. Jammed on rock 6.4 cells from deposit B.** | frozen | A slow pulse ring on the machine and `NOT MOVING 0:01, 0:02 …` counting in the rail, beside a green deposit ring it is standing inside | frozen | **The third and worst stretch of dead air.** No drawing shortens it. Drawn honestly it becomes the cruellest shot in the match: *it is right there.* Today it reads as a crashed program. |
| **6:56.0** | **Window 6. The rival is 8.121 cells inside a 9.000 radius. It dies.** | 4 s later, a red arc from bearing 183 | The ring floods with the ember machine inside it; the glyph collapses to a red `X` and **stays as a wreck for the rest of the match**; a crash ring crosses the cave | A wide red wedge lands, for a thing the viewer has just watched die | *That's what nearly happened to ours.* Today: a red arc arrives from a bearing and nothing on screen has ever shown the thing that died. |
| **8:00** | error 91.1 cells, heading error 39.5°, cargo 0, Recall unused | "within 18 cells" | Unchanged — it has been telling the truth for eight minutes | The true wall outline draws over the map the machine built: a fan, rotated and smeared, because `HEADING_FIX_GAIN = 0.0` means nothing ever straightened it | The rail holds **91** and **18** one above the other. One line: `LOST IN THE CAVE — CARGO 0 — RECALL UNUSED`. |

**One additional truth-side line, and it is the only thing on screen that makes the game's one
decision expire.** A Dijkstra over `WALKABLE` from the player's shaft, built once (measured
0.008 s, hidden inside the existing warm-up), gives the true walking time home. Against the
clock:

> **5:34** — path home 155 cells, needs 147 s including recall delay and depth latency, 146 s
> remain. After this instant Recall provably cannot get the machine home before 8:00.

That appears as a line under the truth caption, `RECALL CAN NO LONGER GET IT HOME`, and the
timeline shades everything after it. It is truth-derived, so it lives on the **truth** side
only and goes dark with the truth scene. It must never appear in a build a player touches: a
player waiting for a red bar is operating a robot with a cheat sheet, not judging under
uncertainty. `DESIGN.html`'s own line is *"truth for spectators, belief for players."*

**A fourth kind of dead air is on the timeline, not the map.** 34 of 50 timeline events are one
of two strings, firing every 16.0 s ± 0.1 for the whole match, because the rival pings on an
8 s cooldown against a 12 s `ROUTINE_COOLDOWN`. Anything on a fixed clock stops being an event.
Routine contacts leave the timeline's *sentences* entirely — they are already drawn twice on
the maps, as a wedge and as a ring at the true origin — and become pips. A contact earns a
sentence only when its bearing has moved more than 25° or its character changes.

### 5.1 What the director is looking at

The beat sheet above is unchanged — the sim is unchanged, so the beats are unchanged, which is
what keeps the re-run a clean A/B on the display. What is new is that the truth camera has a
subject at every instant, chosen by the priority list in §7.2. Against this match it produces:

| t | subject | framing |
|---|---|---|
| −0:06 → 0:00 | the whole cave | WIDE, the cold open's descent from 90° to 72° |
| 0:00 → 0:41 | both machines | WIDE — 174 cells apart, nothing else will fit |
| 0:32 → 0:45 | window 1 | rule 10. CLOSE on the machinery, empty, so the rule is learned for free |
| 0:58.9 → 1:29 | the player loading at deposit A | rule 7. CLOSE — and the rival's comet crosses a third of the cave *behind it*, which is why this stretch of dead air stops being dead |
| 1:47 → 2:00 | window 2 | rule 10. CLOSE, empty again |
| 2:16.4 → 2:30 | the arming beacon, then the spoof | rule 3. CLOSE on the player with the reddening diamond in frame |
| 2:30 → 2:35 | the two machines, 13.9 cells apart | CLOSE holds both. Dread, drawn. |
| 2:35 → 2:39 | **the echo chamber** | CLOSE on an empty labelled dead end while two rings expand out of it and a wedge on the belief side points at bare rock. Rule 4, and the only time the camera is pointed at nothing. |
| 3:02 → 3:15 | window 3 | rule 10. CLOSE, player 55 cells away |
| 4:04 → 5:30 | **the rival** | rule 8, the drought. The player has been the subject for 45 s and is doing nothing; the rival is walking to the machinery and downloads inside the ring at 5:13. A sports director cuts to the thing that is happening. |
| **5:32 → 5:58.6** | **the machinery, with both machines in it** | rule 1. **CLOSE. The target beat.** The warning arms at 11.5 cells, the machine jams at 9.038 against 9.000, stands there for the whole four-second window, and steps inside 0.8 s late; the two machines pass at 0.41 cells at 5:56.1. All of it inside one 40-cell frame, no cut. |
| 6:30 | the machine and the shaft | rule 7. Framed to hold both, which is very nearly WIDE — the one place the whole cave is needed, because the question is *how far is home* |
| 6:40.5 → 6:52 | the rival | rule 8: the player has stopped and the rival is still walking. It is walking into the machinery. |
| 6:52 → 7:04 | **the rival dying** | rules 1 then 2. The ring floods with the ember machine 8.121 cells inside a 9.000 radius, and the wreck stays. |
| 7:04 → 8:00 | the stalled machine | rule 9. CLOSE, with deposit B's 12-cell ring 6.4 cells away and therefore 200 px away, on screen, unreachable. The 79.4 s of dead air becomes the cruellest shot in the match rather than a frozen video — and the middle twelve seconds of it are a death. |
| 8:00 → 8:12 | the whole cave | WIDE, rising to 90°, for the reveal |

Three things this makes visible that the flat layout could not, and one it costs:

- The drought and the stall — the two longest stretches of nothing — now have a **subject**. The
  camera has somewhere to be during both, and in the stall it is the deposit the machine is
  standing next to.
- The near miss is drawn at **31.3 px per cell** instead of 4 — half again what the flat layout's
  truth panel could have managed, because the main view is 1252 px wide instead of 900. The
  0.038-cell margin is a third of a pixel, which is correct: the glyph edge is *on* the ring.
- **The inset is doing the opposite job in the same instants, and this is what picture in picture
  buys the beat sheet.** While the main view is 40 cells across the machinery at 5:32, the belief
  inset holds the whole 200 × 120 world and shows the machine's marker sitting quietly beside
  deposit A, sixty-five cells away. The gap is on screen twice at once, at two scales, in two
  pictures: as a rope leaving the main frame with `→ 65 cells` on it, and as a small cool map
  that is calmly wrong. Side by side the second picture was 652 px of sparse cloud and the eye
  never went there. As a 300 px inset it is one glance.
- **The cost:** at CLOSE framing the believed pose is essentially never inside the main frame. At
  5:45 the machine is at the machinery and believes it is near deposit A, 65 cells away — the
  ghost is nowhere near the shot. §6.9 says what the tether does about that, the inset holds the
  believed pose at whole-map scale, and the minimap draws the whole of the error regardless.

---

## 6. The visual language

### 6.1 Palette — roles, not hues

`palette.py`'s own docstring states the rule that keeps it readable: *"a colour means one thing
each."* The rule is already broken four ways — amber carries six meanings (deposit, believed
rival, TONE contact, `BAR_HOT`, extraction window, banner) and green seven (agent, ellipse,
intent, intent ring, playhead, live graph edges, cargo). Twenty values replace about fifty, and
green goes back to meaning the objective while yellow goes back to meaning "the world just
moved under it".

```
CHROME
  void        #06080B   outside everything
  panel       #0B0E13   rail and timeline ground
  rule        #1A212B   1 px separators only

TRUTH — warm, filled, opaque
  rock        #15110D   solid rock, at the base of a wall
  rock-lit    #3A2E22   the top of a wall and its lit faces
  floor       #2A2219   dry passage, tinted toward #1A150F with depth
  water       #16202E   flooded — cool on purpose; water is not warm
  bone        #F2E6D2   the player's machine, true
  ember       #FF7A2F   the rival, true
  warm-dim    #7A6650   true comets, chamber labels, truth ambient

BELIEF — cool, sparse, translucent
  unmapped    #070A0E   never sensed. Must read as absence, not fog.
  mapped      #16303E   silhouette fill, alpha ramped by point density
  sensed      #63D6F7   a point the sensor returned
  walked      #2E4854   ground it only passed through
  ghost       #9FE8FF   believed pose, ellipse, all hollow marks
  cool-dim    #3A5260   believed trail, residue spokes

ACCENTS — one meaning each, used nowhere else, ever
  hazard      #FF4FD8   the machinery. Both scenes, and the minimap.
  lie         #FFD23F   a fix that moved the world; the spoof; a hot tether
  cargo       #4FE08A   the objective: deposits, the hold, the shaft, extraction
  kill        #FF3B30   a machine dying; error past the alarm threshold

TYPE
  primary     #F2F5F9
  secondary   #93A2B1
  tertiary    #56626F
```

One value is added to the second design's twenty: **rock-lit**, because an extruded wall has a
top and four faces and they cannot all be one colour or the cave reads as a flat stencil. The
face shading is described in §6.7.

Two orthogonal channels do the heavy lifting, both learned in one beat and never explained:

- **Warm and filled is real. Cool and sparse is believed.** A viewer who learns nothing else
  always knows which half she is looking at, and the 8:00 reveal becomes warm-over-cool.
- **Solid fill is the thing. Hollow outline is a belief about the thing.** This is what makes
  the ghost machine legible sitting next to the real one. Dashed is the relationship between
  them.

### 6.2 Type

Four sizes. **Nothing below 9 pt.** The current display sets the status labels, the map key and
the timeline's window label at 7.5 pt, and she watched a compressed H.264 video, where 7.5 pt
is not small — it is absent.

| role | size | weight | used for |
|---|---|---|---|
| Display | 34 | bold | the two error numbers, the match clock |
| Head | 15 | bold | the title band, captions, the action line, the now-line |
| Body | 11 | regular | chamber names, labels, timeline clock |
| Micro | 9 | regular | units only — "cells", "to go" |

`IT IS WRONG BY` ramps: tertiary ≤ 3 cells → primary 3–12 → **lie** 12–30 → **kill** > 30.
`IT THINKS IT IS WRONG BY` is **ghost** cyan always. The machine's calm is the joke; do not
colour it.

Units are **cells** everywhere, because that is what the sim and `GLOSSARY.md` say. Not metres.

**Four sizes is now a performance rule as well as a design one.** §6.10 groups every chrome
string into one `Text` visual per size, which the spike measured as the single largest saving
available anywhere on this screen — about 15 ms a frame. A fifth size would be a fifth visual.

### 6.3 Hierarchy, and the rule that enforces it

Three levels:

- **PRIMARY** — readable in under a second from across the room: the two display numbers; the
  tether; the machinery ring while it is counting.
- **SECONDARY** — read when something happens: both machines and their comets; the fix beat;
  sound rings and wedges; major event pips; the action line.
- **AMBIENT** — never read, only felt: the cave mesh, the belief silhouette, the point cloud,
  residue spokes, routine pips, beacons, trails, chamber names, the minimap's static furniture.

> **An ambient element never exceeds 35 % of a primary element's luminance, never animates for
> longer than one second, and never carries text above Body size.**

Everything else in this document is a drawing. That rule is what stops the drawing decaying
back into the forty-five-encoding screen it replaced, and it is the single most useful sentence
here. **The cave mesh is ambient**, which is the constraint that sets its brightness: a lit
massif that competes with a bone machine standing on it has undone the whole exercise.

### 6.4 The encoding of every object

**Truth scene — thirteen marks.**

| # | object | encoding | level |
|---|---|---|---|
| 1 | **the cave** | an extruded `Mesh`: one quad per rock face exposed to floor, plus a cap over every rock cell, at `CAVE_WALL_HEIGHT_CELLS = 8`. 43,202 triangles, built once, 2.2 ms/frame. Four face brightnesses fixed to **world** compass directions plus a vertical gradient dark at the base — see §6.7 | ambient |
| 2 | **the floor** | one 200 × 120 RGBA `visuals.Image` at z = 0, `interpolation="nearest"`, uploaded once. Floor and water only; **fully transparent under rock**, so the mesh cap carries the rock colour and the two surfaces are never coplanar. A BFS from the shaft over `WALKABLE` darkens it by graph distance, so the far end of the cave is visibly *deeper*: `DESIGN-PRINCIPLES` §2, *"further in is where the blocks you do not have are"*, as a gradient, for free | ambient |
| 3 | chamber names | eleven strings in **one** `Text` visual, Body, warm-dim, at z = wall height + 0.5 so they float above the rock and are never occluded, placed once at `CHAMBERS` centres and **never reassigned**: `YOUR SHAFT · JUNCTION · DEPOSIT A · THE BIG HALL · THE ECHO CHAMBER · THE SUMP · JUNCTION · THE MACHINERY · JUNCTION · DEPOSIT B · THEIR SHAFT` | ambient |
| 4 | the player, true | **solid** bone machine glyph on true heading, on the floor plane | secondary |
| 5 | its comet | the last 20 s of `truth_trail` as a `Line` strip on the floor plane, alpha 0→1 head-ward, width 3→1 | secondary |
| 6 | its belief | **hollow** ghost glyph at the believed pose, identical geometry, plus the 2σ ellipse | primary |
| 7 | **the tether** | §6.9. A rope above the rock, not a line on the floor | **primary** |
| 8 | the rival, true | **solid** ember glyph and its own comet. *Drawn for the first time in this project.* | secondary |
| 9 | the machinery | a ring at the true 9-cell radius on the floor, **and a faint cylinder wall of the same radius rising to the cave's wall height**, so the hazard is visible over a rock rim from any azimuth and reads as a volume rather than a decal. **Quiet:** 1 px, 12 % alpha, 0.1 Hz breathe. **Warning (9 s):** the floor ring fills clockwise as `1 − seconds_until_lethal / 9`, brightening, with `LETHAL IN 0:07` beside it in Body. **Lethal (4 s):** the disc floods hazard→kill, three flashes at 6 Hz | **primary while counting** |
| 10 | sound origins | a ring expanding on the floor plane from the **true** origin at 28 cells/s, character-coloured, 2.5 s. Crash: 6 s, radius 60 | secondary |
| 11 | beacons, true | 6 px diamonds on a 1-cell stalk, so they are not lost in the floor texture at a shallow angle, warm-dim. Before 2:21.4 the spoofed one is indistinguishable — the surprise is preserved. Arming: it reddens as `spoof_arming` closes. After it moves: **lie** yellow, a permanent dashed line to where belief still records it, labelled `THE RIVAL MOVED THIS` | ambient → primary |
| 12 | deposits | cargo rings at the **true 12-cell radius**, on the floor plane. The reveal currently draws 3 | ambient |
| 13 | wreck | after a death the glyph collapses to a kill `X` over 0.4 s and **stays for the rest of the match** | secondary |

**The machine glyph.** A plan-view vehicle in world coordinates: a hull, two tracks, a sensor
head that rotates slowly and throws a 120° arc when it pings, and a cargo pip per load aboard —
about 17 line segments, lying flat on the floor plane. Both machines plus the ghost are one
`Line(connect="segments")`, 51 segments, one `set_data` per frame.

It stays **2.4 cells long** against a true radius of 0.6. That is a 2× exaggeration of the
footprint and it is the largest scale licence in this document. **The 3D decision created
pressure to make it bigger, the picture-in-picture decision removed that pressure, and it is
still refused.** At whole-cave framing 2.4 cells is about nine pixels and the spike is right that
it is invisible — but the answer to an invisible subject is to move the camera to it, not to
inflate it, and the main view now draws CLOSE framing at 31.3 px/cell, where the same glyph is
**75 px**. A larger glyph — an earlier draft wanted six cells, ten times true size — destroys
exactly the two beats it exists to serve: the near miss at 9.038 cells against a 9.000 radius,
and the pass at 0.41 cells, which at 75 px per glyph is two machines overlapping by 62 px.
**The camera is the free variable; the glyph is not.** In the inset the same glyph is 18 px,
which is legible as *a machine is there* and not as *a machine is doing this* — correct for an
overview, and the reason the inset is never the slot a beat is read in.

**Belief scene — eleven marks. Content unchanged; encoding repaired.**

| # | object | encoding | level |
|---|---|---|---|
| 1 | **the mapped silhouette** | a 170 × 130 RGBA `Image` **on the z = 0 plane**, under the cloud, alpha `clip(count · 26, 0, 150)` in `mapped`, rebuilt at 4 Hz and on every fix. **This is the element the spec has been missing, and the spike raised its importance rather than lowering it.** The spec calls the smear *"the single most important visual in the test"*, and today it is 6,000 grey dots: you cannot see a shape drift until there is a shape. The real cloud at 8:00 is 0.35 points per cell and reads as disconnected blobs from *every* camera angle, so the third dimension does not rescue it — the silhouette does. Nothing is discarded; the silhouette is derived from the same points | ambient |
| 2 | point cloud | **two classes only.** Sensed: 2.4 px, `sensed`, alpha 0.35 + 0.5q, at its scattered z. Walked: 1.6 px, `walked`, alpha 0.2, at z = 0. The colour lerp × alpha ramp × size ramp × three source overrides collapse to one rule; four channels doing one job is most of why the map reads as noise, and `FALSE` returns are currently drawn identically to real sonar anyway. Per-point colour and per-point size are both measured to survive at every count this phase can reach — +0.6 ms at 25k against flat scalars | ambient |
| 3 | believed pose | **hollow** ghost glyph on the z = 0 plane, identical geometry to truth mark 6 | secondary |
| 4 | 2σ ellipse | ghost, 1.5 px, on the z = 0 plane | secondary |
| 5 | believed trail | cool-dim, 0.25 alpha, z = 0 | ambient |
| 6 | beacons it recorded | ghost diamonds on 1-cell stalks, matching truth mark 11 | ambient |
| 7 | surveyed places | shaft and two deposits as **hollow** cargo rings on the floor plane — prior intel, not something it sensed | ambient |
| 8 | **bearing spokes** | strike → decay → **permanent 12 % residue**, drawn **on the z = 0 plane**, not as rays through space: a bearing is a compass direction on the ground and drawing it in the air would claim an elevation the sensor never measured. By 8:00 there is a fan of about 30 faded spokes: a visible record of everything the machine has ever heard | secondary → ambient |
| 9 | own wavefront | ring on the floor plane from the believed pose, 28 cells/s, 6 s | secondary |
| 10 | believed machinery / believed rival | soft discs on the floor plane at 8 % fill with a 1 px edge, radius `clamp(σ, 4, 20)`. Demoted from the brightest rings on screen to ambient, but kept — with the truth scene in the other slot the gap between where it thinks the machinery is and where it is becomes a readable joke | ambient |
| 11 | fix beat | the cloud eases over 0.7 s as today, and the **pre-fix silhouette is held as a ghost** — 1.2 s for an honest fix, 1.6 s for a disagreeing one — so the map it abandoned is visible beside the one it adopted | primary on event |

**Minimap — the ten marks in §3.3, and nothing else.**

### 6.5 What moves and what is still

**Four things move continuously and two move on demand.** Continuously: the playhead, the leading
edge of the error chart, and the two machines. On demand: the truth camera, which is bounded, and
the swap, which is the viewer's.

The camera is governed: `CAMERA_MIN_DWELL_S = 6.0` means it changes subject at most once every
six seconds, and `CAMERA_EASE_S = 1.2` means each change is a 1.2 s critically-damped ease rather
than a cut. Over the whole match that is roughly twenty moves totalling twenty-four seconds —
five per cent of the running time. **A camera that is always drifting is a camera the viewer
stops trusting**, and the hierarchy rule in §6.3 applies to it: the camera is ambient, so it never
animates for longer than one second and a bit, and it never moves for its own sake.

**The swap is the only thing on the screen that ever changes what a rectangle contains, and it
only ever happens because the viewer asked.** Once, at 8:00, the design asks on her behalf
(§3.7). Everything else about the arrangement is static: two rectangles, fixed, for eight minutes.
That is deliberate, and it is the reason the inset is safe to overlay on the picture the whole
display depends on — an overlay that moved, resized itself, or appeared and disappeared would be
a fifth moving thing competing with the two machines, and §6.3 would not survive it.

The two problems with motion in the current display, and their fixes, are unchanged:

- **Slow motion does not read as motion.** The machines move at 1.1 and 1.4 cells/s; at WIDE
  framing that is 6–8 px/s, at or below the threshold where the eye registers movement at all.
  Fix: the 20-second comet. A moving gradient reads as motion even when the head barely moves.
  At CLOSE framing the same machine moves at 34–44 px/s, which is the second thing the director
  buys and it was not the reason for building it.
- **Stillness is not marked as stillness.** 6:40.5 → 8:00 is 79.5 seconds where truth and belief
  are both frozen, and on screen that currently reads as "the video has stopped". Fix: a 1 Hz
  stall ring on the machine and `NOT MOVING 0:34` counting in the rail — and the camera pushing in
  on it, so the frame is a machine standing 6.4 cells from the deposit it came for. An invisible
  failure is a bug; a counting, visible failure is drama.

### 6.6 What a sound looks like

Her words were *"all that changes is things kinda beep and nothing really is obvious."* The
current answer to a sound is a four-second incoming arc, drawn identically for all 22 rival
pings, for the scripted echo, and — bigger and red — for a machine dying. Then it is gone. A
sound that leaves no trace cannot be reasoned about, and she was asked to reason about
twenty-two of them.

**Every audible event now makes three marks in three places in the same instant:**

1. **Truth scene, at the true origin** — a ring expanding on the floor plane at 28 cells/s in the
   character colour. *Where the sound was born.* If the origin is outside the current frame, the
   ring is still drawn and simply arrives from off-screen, which is correct: a sound from
   off-camera is a sound from somewhere else.
2. **Belief scene, from the machine** — a wedge on the measured bearing, on the floor plane: full
   alpha instantly (a 120 ms strike, no fade-in, because a strike that ramps reads as a fade),
   decaying over 900 ms, then **persisting forever at 12 %**.
3. **Timeline** — a pip on the event rail.

One shared curve module, `view/beat.py`:

```
strike(age)       = 1.0                     for age < 0.12 s
decay(age, life)  = (1 - age/life) ** 2     for 0.12 <= age < life
residue           = a constant floor alpha, forever
```

| event | truth scene | belief scene | timeline | life |
|---|---|---|---|---|
| own ping | ring from true pose | ring from believed pose | routine pip | 4.0 s |
| heard ping | ring from **true origin** | wedge strike → decay → **permanent spoke** | routine pip | 2.5 s / forever |
| motion (TONE) | ring from true origin | shorter wedge | routine pip | 2.0 s |
| crash | kill ring, radius 60 | wide kill wedge | MAJOR pip | 6.0 s |
| machinery signature | the ring begins its countdown sweep | magenta wedge; believed-machinery disc brightens | MAJOR pip, first of a cycle only | 9 s |
| machinery lethal | the 9-cell disc floods, 3 flashes at 6 Hz | — | band on the machinery rail | 4.0 s |
| honest fix | the ghost slides toward the machine | cloud eases 0.7 s; pre-fix ghost 1.2 s | routine pip | 1.2 s |
| **disagreeing fix** | the ghost slides; **the tether flashes lie and stays hot 8 s** | cloud eases; pre-fix ghost 1.6 s; **that picture's own border** pulses lie for 1.0 s, in whichever slot it is in — which reads *better* in the inset, because a 300 px frame flashing at the edge of vision is a thing the eye is built to catch | MAJOR pip + words | 8.0 s |
| **beacon moved** | the diamond **travels** old→new over 0.45 s, leaving a permanent dashed line | nothing — correctly, it cannot see this | MAJOR pip, `A BEACON MOVED` | 0.45 s + permanent |
| beacon drop | diamond appears, one pulse | diamond appears | routine pip | 0.5 s |
| cargo | the deposit ring fills once | — | MAJOR pip | 1.0 s |
| stall begins | 1 Hz pulse ring | — | stall band on the rail | until it moves |
| recall sent | one-frame cool wash | same | MAJOR pip | latency countdown |
| death | the disc floods; the glyph collapses to `X`; **the wreck persists** | wide kill wedge | MAJOR pip | permanent |
| extraction opens | the shaft begins a 1 Hz cargo pulse | the shaft star pulses | MAJOR pip + band | 90 s |

**One deliberate craft decision.** The spoof and the fix land in the same sim tick, 2:21.4.
Drawn together they read as "two things happened". So they are **staggered**: the beacon
travels over 0.45 s, the cloud ease starts at +0.25 s. Cause, then effect. That quarter-second
of display-only delay is the difference between an event and a story.

### 6.7 What height means, and it is not the same thing on each side

This is the section the third dimension makes necessary, and getting it wrong is how a 3D
display becomes less legible than a flat one rather than more.

**On the truth side, height means one bit: rock or not rock.** The sim's cave is a 200 × 120
grid with no vertical dimension at all, so the 8 cells of wall are **invented**, and this
document says so rather than implying a model that does not exist. The extrusion is a legibility
device and it earns its place by doing one job the flat image could not: it makes a chamber read
as a *room* and a passage read as a *passage*, which is what turns the cave from a shape into a
place. It carries no scalar. **A varying wall height would be a lie** — it would read as terrain
the machine has to climb, and there is no terrain.

The one real scalar on the truth side is graph distance from the shaft, and it stays in the
**floor**, as brightness, exactly as the second design had it. Depth is drawn as darkness, not
as altitude.

The lighting is a fixed **world** light, not a camera light: four face brightnesses attached to
the four compass directions (1.00 / 0.84 / 0.62 / 0.46 for +x / +y / −x / −y) with the wall base
darkened to 0.42. So as the viewer orbits, the lit faces move to the back and the shadowed ones
come round to the front. That is the correct behaviour for a sun, it is a strong depth cue, and
it is *why the cave reads as solid stone rather than as a texture*. These six numbers are the
whole lighting model, they came from the spike, and they are unvalidated against anything but
the spike's own screenshots — flagged in §11.

**On the belief side, height means what the sensor touched.** The cloud already carries a z:
`WALL_POINT_HEIGHT = 2.2` cells of scatter on returns off rock, and zero for ground the machine
only drove over. Flat, that was nine pixels of fuzz and the second design proposed throwing it
away. In three dimensions it becomes an encoding for free: **z above zero is a wall return, z at
zero is ground it walked.** A corridor is then a strip of floor between two low banks, and the
spec's *"corridor ghosting into a doubled version of itself"* is visible as **two banks where
there should be one** — which is a shape the eye catches and a scatter of dots is not.

**The two sides deliberately disagree about how tall a wall is, and that disagreement is the
game.** The truth cave has 8-cell walls. The belief cloud has a 2.2-cell scatter. Nothing is
done to reconcile them, and `WALL_POINT_HEIGHT` is **not changed** — it is consumed inside
`Belief`, not inside the view, so changing it would be a sim change and §8 does not permit one.
The picture that produces is correct and it is worth more than a matched pair would be: the
truth side is a canyon and the belief side is nearly flat, because **the machine cannot measure
height at all.** Its map is a tracing, not a model. A viewer learns that in one glance and is
never told it.

**The shared datum is z = 0.** Both scenes put the floor there, every mark that represents a
position on the ground is drawn there, and nothing on either side is drawn at a z that claims a
measurement. That is the rule that keeps the two pictures comparable when their wall heights are
not.

**And picture in picture turns the comparison from juxtaposition into alternation, which is what
makes the disagreement about height readable at all.** Side by side, the eight-cell canyon and
the nearly-flat tracing were two pictures three hundred pixels apart at two different framings,
and the viewer had to carry one across the gutter to compare it with the other. Under this
arrangement they take turns in **the same rectangle, at the same bearing, at the same size**, one
after the other, 0.28 seconds apart. The eye is very much better at detecting that something in
front of it has changed than at holding a shape while it looks somewhere else, so the comparison
this design has been trying to stage since the first draft is finally staged properly — and it is
staged by a click rather than by a layout.

Two honest conditions on that. First, alternation only compares like with like if the two
pictures are at the same scale when they trade, and their framing rules differ by construction
(§3.2) — so the true comparison is `Space` (which sends the truth camera to WIDE and both cameras
to the default attitude, §7.4) and then one click. Three inputs, not one. Second, the design
spends it automatically exactly once, at the 8:00 reveal, where the true wall outline is drawn
over the built map in one picture. Everything else in the match is legible without it.

### 6.8 How the eye keeps the two sides related when both can be rotated and only one is visible

Five devices, in order of how much work each does. The first is new and it is the one the
arrangement adds.

**0. They occupy the same rectangle, one after the other.** This is the strongest relation
available and the flat layout could not have it. See §6.7 — comparison by alternation in one
frame beats comparison by juxtaposition across two, and the orthographic projection (§3.2) is
what makes it exact: the picture that comes back is the same picture, rescaled, not reprojected.

**1. The attitude is shared; the framing is not.** A drag in the main 3D scene sets `azimuth` and
`elevation` on **both** cameras; `center` and `scale_factor` stay per-scene. So the two pictures
are always seen from the same compass bearing and the same tilt, and they are always framed
differently — which is exactly the split the design needs, because the relation the viewer must
keep is *direction*, not *scale*. It matters more under this arrangement than it did under the
last one: if the inset were north-up while the main view was orbited, a swap would **rotate the
world**, which is the single most disorienting thing a display can do to someone.

This is not `camera.link()`. `link()` couples centre and `scale_factor` too, which §3.1 shows
cannot be allowed. It is the six-line mirror the second design already named as `link()`'s
fallback: on the drag handler, set the other camera's two attitude fields. Measured cost, 0.3 ms
per set, and only while a drag is in progress. Both cameras take §3.4's 60°–90° elevation clamp
in both slots, so the shared value is always legal on the side that occludes.

**2. The minimap never rotates.** North-up, top-down, fixed, with the truth camera's footprint
drawn on it, always showing truth in either arrangement. When two of three pictures can spin *and*
can trade places, one must do neither. §3.3.

**3. A compass tick on each scene.** In the main slot, a 12 px `Line` in the title band with a
one-character `N`; in the inset, a 10 px tick in its own top-left corner. Two ticks that always
agree are a cheap, constant, peripheral confirmation that the two pictures are aligned — and they
are the one mark that survives the swap unchanged, so they are also what says *the same two
pictures are still here, they have only changed size*.

**4. `Space` re-aligns everything.** Both cameras to azimuth 0, elevation 72°; the truth camera
to WIDE and back onto the director when the override expires; the belief frame re-centred. §7.4.
**Every orbitable view needs an undo, and a viewer who has knocked the camera askew and cannot
get back has lost the display.** With a swap in the mix it needs one more thing, and it has it:
`Space` does **not** swap the slots back. Undoing a camera and undoing a choice of picture are
different actions and a viewer who deliberately swapped to the belief map should not have it
taken away by pressing the key that fixes a crooked camera.

One device deliberately **not** used: drawing a connecting line between the inset and the main
view, or mirroring a highlight from one into the other. Both were considered and both are noise —
they add a mark whose only content is "these two things correspond", which devices 0, 1 and 3
already say continuously and for free.

### 6.9 The tether, and the two numbers, when one picture is small

The tether is the segment from mark 4 to mark 6 of the truth scene — solid machine to hollow
belief — and it is `PRIMARY`. Under this arrangement it is the single most important mark on the
screen, because **it is the only place the gap is drawn as one object rather than as a
comparison the viewer has to make**, and picture in picture removed the comparison.

**It never spanned the two panels and it does not now.** Both endpoints are world coordinates in
the truth scene, so the arrangement costs it nothing and in fact pays it: in the flat layout it
was one mark inside a 900 px panel, and here it is one mark inside a 1252 px picture at 31.3 px
per cell. **The gap got 39 % bigger when the panels went away.** Anyone reading this design as
"the tether crosses the gutter" has it wrong; it is drawn inside one picture, which is what makes
it a single mark rather than something the viewer has to assemble.

**It is drawn above the rock, not on the floor.** At z = `CAVE_WALL_HEIGHT_CELLS + 1` = 9 cells,
with a short vertical drop-line at each end down to the pose it names. The believed pose is
routinely on the far side of solid rock from the true one — that is the whole point of it — so a
tether on the floor plane would be buried by the mesh for most of its length at every elevation
below 90°, and a primary mark that the ambient layer occludes is not primary. As a rope over the
cave it reads from any azimuth, it is never cut, and the drop-lines say which two cells it joins.
It is also the only mark in the scene that is never occluded, which is correct for the one mark
the hierarchy calls primary.

Its encoding is unchanged: ≤ 3 cells, 1 px cool-dim, unlabelled. 3–12, 2 px primary. 12–30, 3 px
**lie**. > 30, 4 px **kill** with a pip at each end. Label at the midpoint, Head size, `34 cells`.

**When the ghost is off-frame — which at CLOSE framing is almost the whole match — the tether
leaves the frame and says so.** It is clipped to the main view's edge and terminates in an
arrow-headed stub carrying the number: `→ 65 cells`. This is not a degraded case; it is the
better drawing. At 5:45 the machine is standing on the rim of a lethal disc and believes it is
65 cells away beside deposit A, and an arrow going off the edge of the world says *it thinks it is
somewhere else entirely* far more directly than a thin line to a distant dot ever did.

**In the inset the rope is drawn and its number is not.** Text inside a 3D scene is drawn only
while that scene is in the main slot (§6.10), so a truth scene sitting in the corner shows a
coloured rope of a given width and no label — which still reads as severity, because width and
colour are the encoding and the number is the confirmation.

### 6.9.1 Exactly how the gap reads, in each arrangement

This is the question picture in picture forces, so it is answered as a table rather than as a
claim. Every row is a mark that already exists; nothing was added to compensate for the layout.

| what says the machine is wrong | truth big (default) | belief big (after a click) |
|---|---|---|
| **the tether** | a rope at 31.3 px/cell across the biggest picture on screen, or — usually — an arrow leaving it with `→ 65 cells` on it | present, in the 300 px inset, as a coloured rope with no number |
| **the two numbers** | 34 pt, in the rail, directly beside the inset | unchanged, in the same place, at the same size |
| **the minimap** | both dots and the whole length of the line, at 1 px/cell, north-up | unchanged |
| **the ghost beside the real machine** | in the main picture at 75 px | in the inset at 18 px |
| **the map's shape against the cave's** | not available before 8:00 | not available before 8:00 |

**So when the belief view is the small one — the default, and the state the gate is run in — the
gap reads three times over, at three scales, continuously:** as a rope or an arrow with an
integer on it inside the big picture; as two integers under near-identical labels in the rail;
and as a line between two dots on a north-up map in the corner. It is stated in the machine's
frame (`IT THINKS IT IS WRONG BY 1`) and in the world's (`IT IS WRONG BY 34`) at the same size,
six inches apart, which is the four-word version of the whole design. Nothing about that depends
on the belief picture being large, and that is exactly why the belief picture is the one that
gets made small.

**The two numbers gained something from the arrangement.** In the flat layout they sat in a
readout band under the middle of the screen and belonged to neither panel. Here they are the top
block of the rail, immediately right of the inset, so **the small picture of the machine's belief
and the small claim that belief makes are neighbours** — the picture and its caption, one
saccade, not six hundred pixels. They do not move when the slots trade, because a readout that
moves is a readout the viewer has to find again, and because their meaning does not depend on
which picture is big.

**And the minimap always has the whole of it.** Ghost dot, true dot, line between, at 1 px per
cell — so at every instant the full length of the error exists somewhere on screen at a scale
where it fits. That is the second reason the minimap is not optional.

### 6.10 vispy, and the frame budget

Every documented trap in `phase1/view/`, every new one the spike found, every one the
picture-in-picture arrangement adds, and what this does about each.

| trap | handling |
|---|---|
| **34 separate `Text` visuals cost ~15 ms a frame just to exist**, even when never reassigned. The spike isolated it: three 3D viewboxes alone paint in 12.2 ms, adding the panel grounds and images and lines and markers changes nothing measurable, and adding the 34 strings takes it to 27.3 | **Every chrome string is grouped into one `Text` visual per type size — four visuals, not thirty-four.** `Text` takes a list of strings and an array of positions. Measured: 34 separate = 24.2 ms, the same 34 in one visual = 10.0 ms, in four = 15.6 ms, and reassigning one grouped string per frame costs nothing detectable. **This is the largest single saving available on this screen**, it is what pays for the larger main view, and it applies to the flat display too. |
| Assigning `Text.text` rebuilds the glyph atlas | The chamber names, panel titles, key rows and bar labels are **set once at construction and never reassigned**. The two display numbers are gated on their **integer** value (~1 Hz). The captions have a priority table and a `CAPTION_MIN_DWELL_S = 2.5` rule, so at most one assignment per 2.5 s each. `LETHAL IN n` is gated on the integer second: ≤ 15 per window × 6 = 90 per match. The now-line changes only on a major event, ~10 per match instead of 50. **No `Text` is assigned unconditionally in `draw()`.** The spike priced that rule: reassigning unconditionally costs 25.4 ms with one visual, 33.1 with twelve and **50.1 ms median (p90 164)** with thirty-four. First parenting 34 `Text` produced a **7,308 ms** frame and re-parenting them 2,993 ms. |
| **`visuals.Text` inside a camera viewbox takes `font_size` in points, not scene units — so it does not shrink when its ViewBox does** | **New consequence, and it is the one real cost the arrangement imposes on the visual language: text inside a 3D scene is drawn only while that scene is in the main slot.** Eleven 11 pt chamber names in a 300 × 161 inset would cover the picture. The main slot's title band and the rail carry all the words for the small picture. Toggling is `visual.visible = False`, a boolean, **not** a `.text` assignment, so it costs no atlas rebuild — this is why the rule is affordable at all. It applies to the chamber names, the tether's midpoint label, `LETHAL IN 0:07`, and the beacon's `THE RIVAL MOVED THIS`. |
| **The swap assigns `pos` and `size` on two ViewBoxes every frame for 0.28 s** | **Unmeasured. The spike never resized a ViewBox and never overlapped two.** A resize triggers a transform rebuild, which the spike priced at 0.30 ms for the analogous `camera.azimuth` set, so the expected cost is under 1 ms for seventeen frames — but expected is not measured, and this is on slice 10's list. **The fallback is one constant:** `PIP_SWAP_S = 0.0` makes the swap a cut, which is worse and is not a redesign. |
| **Two ViewBoxes overlapping a third** | Also unmeasured. `clip_method="viewport"` sets `glViewport` and a scissor per ViewBox, so overlap is a draw-order question rather than a correctness one, and the overlays are drawn last. If it misbehaves the arrangement does not change: the inset moves out of the picture and into the head of the rail, which costs the affordance in §3.7 and nothing else. |
| Setting any property on a `Rectangle` regenerates geometry and forces a synchronous repaint | **No new `Rectangle` in any per-frame path.** The spike clarified the shape of this trap: a *static* `Rectangle` costs nothing — three full-width panel grounds measured as noise. It is **assignment** that is expensive. Every filled region is an `Image`; every ring, sweep, tether, glyph, rail, border and inset frame is a `Line`. The only `Rectangle`s are the rail ground and its dividers, touched only in `_layout()`. |
| **Orbiting is free; `set_data` is not** | The spike measured orbiting a 250,000-point cloud at the same cost as leaving it still — an orbit needs no re-upload. The per-frame cost is `set_data`, at 0.5 ms for the sonar cloud and 13.2 ms at `MAX_POINTS`. **The cloud is re-uploaded only when it grew or when a fix is easing**, not every frame, and not at all because a swap changed its size — a rescale is a camera change, not a data change. |
| **The cave mesh** | Built in 5.1 ms of CPU, 92.7 ms to upload and first-paint, **once**, inside the existing warm-up. Never touched again, in either slot. |
| **Z-fighting between the rock cap and the floor `Image`** | Two fixes, both taken: `fov=0` (§3.2), and the floor image is transparent under rock so the two surfaces are never coplanar. The spike's failure case is worth remembering — at a 2.6-cell wall the entire cave came back barred with black stripes. |
| Timers must be created after construction, bound to `canvas.app`, and held in a local that outlives `app.run()` | **Untouched.** The frame clock stays in `__main__.py`. Neither the cold open, the swap animation nor the swap's 0.5 s teach is a new timer: all three are branches in `advance()` against the existing wall clock, and `__main__.py`'s `_wall_clock_zero = None` reset after warm-up already puts the cold open in the right place. `Recorder.run()` prepends `COLD_OPEN_S * fps` frames. |
| `canvas.render()` on a never-shown canvas empties the framebuffer stack and every later paint dies inside `glBindFramebuffer` | Still live in vispy 0.16.2; the spike reproduced it. Untouched: show, then two offscreen paints. **A shown canvas and a hidden canvas cannot coexist in one process**, so `--record` stays its own invocation. The warm-up gets slower — a mesh upload and more strings — so budget about 2.6 s instead of 1.86 and keep the "preparing the display" message. |
| **`show()` clamps the canvas to the screen; `render()` does not** | §3.6. Live and recorded frames are different sizes. Everything positional is computed from the live canvas size in `_layout()` — **including the inset's rectangle, which is a fraction of the main view rather than a pixel position, and the minimap's, which is one pixel per cell** — camera framing is expressed in cells rather than in `scale_factor`, and the layout is eyeballed at both sizes before the gate. |
| `set_gl_state("translucent", depth_test=False)` on every overlay | Every overlay in the truth scene gets it, and the cave mesh and floor image get `order = 0` with depth testing **on**, because the mesh must occlude. The overlays that must never be occluded — the tether, the chamber names — are lifted in z instead of being excused from the depth test, which is the same result and is stable under orbit. |
| Two cameras | Separate `TurntableCamera` instances — they cannot be shared — driven independently, with azimuth and elevation mirrored by hand (§6.8). `link()` is confirmed working and is **not used**, for the reason in §3.1. Measured: 0.30 ms per `azimuth` set, because it triggers `view_changed` and a transform rebuild. |
| `visuals.Image` | Both images are `set_data()` with a **same-shaped preallocated array**, or the texture reallocates. The cave floor image and the minimap image are uploaded once and never touched again; the minimap's is 200 × 120 into a 200 × 120 viewport, so it is never resampled either. |

**Budget. The measured baseline is the side-by-side 3D screen; this arrangement is derived from
it, and the derivation is shown rather than hidden.**

| piece | live paint | source |
|---|---|---|
| measurement floor (empty shown canvas) | 3.1 | measured |
| truth scene at 776 × 500 | 5.3 | measured |
| **truth scene in the main slot, 1252 × 672 (2.17× the pixels)** | **8.4** | **derived; range 5.3–11.5** |
| belief scene at 776 × 500, sonar | 1.5 | measured |
| **belief scene in the inset, 300 × 161 (0.125× the pixels)** | **~0.4** | **derived** |
| minimap, 200 × 120 | ~0.0 | measured at 300 × 190 |
| 34 separate chrome `Text` | 15.0 | measured |
| **the same strings in 4 grouped `Text`** | **1.4** | measured |
| second camera driven independently | 0.3 | measured |
| `set_data` on the cloud, per frame | 0.5 (sonar), 13.2 (250k) | measured |
| the swap, per frame while it runs | unknown, expected < 1.0 | **unmeasured** |
| readback, 2000 × 1125 | 13.4 | measured |

**Whole screen: the side-by-side 3D layout measured 27.4 ms median and 33.2 ms worst live, 36.7
recorded. Substituting the main view for the truth panel and the inset for the belief panel is
+3.1 ms best estimate and +6.2 ms worst, giving about 30.5 ms median live and about 41 ms
recorded.** With the chrome text grouped — which is in the same build, slice 6 — that becomes
**about 16 ms live and about 26 ms recorded.** Against the ~60 ms live budget that is 51 % before
the grouping and 27 % after; an 8:12 render at 20 fps is about 6.7 minutes before and 4.3 after,
against 6.3 for the flat display it replaces. **The arrangement spends about three milliseconds
to make the main picture two and a sixth times bigger, and the text grouping returns five times
that in the same afternoon.**

**The one honest caveat, and it is the reason slice 10 grew.** Three things in the paragraph
above are derived from the spike rather than measured by it: a ViewBox at 841,344 pixels, two
ViewBoxes overlapping a third, and a ViewBox being resized every frame. The first is the one that
could actually bite, because fill cost scales with pixels and the spike never drew a panel more
than 388,000 pixels across. If the main view comes in above the 11.5 ms worst case, **the fix is
one constant and no redesign**: `RAIL_W` widens, `MAIN_W` shrinks, the inset and minimap follow
because they are fractions of it, and the framing constants follow because they are stated in
cells. Nothing else in this document depends on the main view being exactly 1252 px wide.

**Real point counts, so nobody designs against the ceiling.** Measured from
`python -m phase1 --headless`, seed 7: the player's sonar cloud is 251 points at 0:30, 2,634 at
4:00 and **6,007 at 8:00**; lidar reaches 28,597. `MAX_POINTS = 250_000` is 8.7× above the worst
real count and is never approached. Growth is linear at ~12.5 points/s and there is no
late-match spike.

**If a budget ever has to be cut**, in order of what costs least to lose: group the chrome text
(−15 ms, no visual loss whatever); gate the cloud `set_data` on a fix being in flight (−0.5 ms,
−13 ms at the ceiling); shrink the main view by widening the rail (−0.5 ms per 100 px, and it
costs px/cell on the beat); drop the truth floor `Image` (−0 ms, and it removes the z-fighting
risk outright); then the wall cap (−2 ms, and it costs the cave read, so this is where it stops).
**Dropping the inset saves 0.4 ms and costs the design its second picture** — the scenes are the
cheapest things on the screen and the chrome is the expensive one. That inversion is the spike's
most useful finding and it should be re-read before anyone proposes simplifying a picture to save
time.

**One measurement bug fixed on the way.** `EventFeed` appends in **processing order, not
chronological order**, and stamps cargo, extraction and machinery events with the current `t`
rather than their own. Invisible live and in recordings; wrong in every `--snap` frame —
`snap_142.png` shows `CARGO ABOARD` at 2:22 when the correct latest event is `the fix
disagrees` at 2:21.4. Snapshots are how this gets iterated, so it is fixed: stamp with the
event's own time and insert in time order. One sort and three timestamps.

---

## 7. The camera, the swap, and what the viewer does with the mouse

The view is orbitable now and one corner of it is clickable, which means for the first time in
this project the display has inputs the viewer can get wrong. This section exists because the
gate viewer is a stranger who sat silently through eight minutes of video: **she will not touch
the mouse**, and the design has to be excellent for that person first and merely good for the one
who does.

> **The rule that governs everything below: nothing that matters is ever only visible after an
> input.** Every beat in §5 lands at the default attitude, in the default framing, with truth big
> and belief small, and with the viewer's hands in her lap. The mouse is an amplifier, never a
> prerequisite. That rule covers the swap as well as the camera.

### 7.1 The defaults

| | truth scene | belief scene | minimap |
|---|---|---|---|
| slot at 0:00 | **main**, 1252 × 672 | **inset**, 300 × 161 | fixed overlay, 200 × 120 |
| camera | `TurntableCamera` | `TurntableCamera` | `PanZoomCamera` |
| projection | `fov=0`, `up="z"` | `fov=0`, `up="z"` | 2D |
| azimuth | 0 (north up the screen) | 0 | fixed |
| elevation | **72°**, clamped 60–90 | **72°**, clamped 60–90 | — |
| centre | the director, §7.2, in either slot | eases to hold the believed pose in the middle 60 %, at most once per 10 s, in either slot | fixed, the cave's centre |
| framing | WIDE 225 cells across, CLOSE 40 cells across | fixed at 225 cells across, from frame one | fixed, 1.00 px/cell |
| interactive | **only while in the main slot** | **only while in the main slot** | **never** |

Framing is stated in **cells across the rectangle**, not in `scale_factor`, and converted at
`_layout()` time and again on every frame of a swap. That is deliberate three times over:
`scale_factor` means different things at different `fov` values and different aspect ratios;
§3.6's measured live-versus-recorded size difference would otherwise make the mp4 framed
differently from the window; and **a scene that changes rectangle has to keep its framing**, which
is only expressible if framing is a property of the world rather than of the viewport.

`CAMERA_WIDE_CELLS = 225` puts the 200 × 120 cave in the 1252 × 672 main view at 5.56 px/cell:
1,113 px of cave across a 1,252 px frame and 668 px of cave in 672 px of height, so the cave's
height is what binds and what margin there is sits at the sides. `CAMERA_CLOSE_CELLS = 40` gives **31.3 px/cell**, which fits the machinery's 18-cell
lethal diameter inside the 21.5-cell frame height with room, draws the machine glyph at 75 px, and
renders the 0.41-cell pass at 5:56.1 as two 75 px glyphs overlapping by 62 px. Both constants are
unchanged from the side-by-side design, because the main view's aspect is 1.863:1 against that
design's truth panel at 1.852:1 (§3).

In the inset the same two framings give 1.33 px/cell (belief, WIDE) and 7.5 px/cell (truth,
CLOSE): a whole map whose *shape* is legible, and a close shot in which *something is happening*
is legible. Neither is a slot a beat is read in, and neither has to be.

### 7.2 The director

The truth camera has a **subject** at every instant, chosen each frame from a fixed priority list,
**and it runs in whichever slot the truth scene occupies.** This is the answer to the spike's
single unresolved design question — *at whole-cave framing the machines are invisible* — and the
spike is right that it is free: a `center` lerp costs 0.3 ms.

1. a machine is inside the machinery's warning or lethal ring → **that machine and the machinery,
   CLOSE**
2. a machine has died in the last 8 s → **the wreck, CLOSE**
3. the spoof is arming, or a beacon moved in the last 6 s → **the player and that beacon, CLOSE**
4. a MAJOR sound was born more than `CAMERA_NEAR_CELLS` from every machine → **its origin, CLOSE,
   for 4 s.** In this match that is the scripted echo at 2:35 and nothing else.
5. the two machines are within `CAMERA_NEAR_CELLS = 20` of each other → **both, CLOSE**
6. a fix is easing → **the player, CLOSE**
7. the player is loading at a deposit → **the player, CLOSE**. Extraction has just opened →
   **the player and the shaft, framed to hold both**, which at 6:30 is very nearly WIDE, because
   the question the beat asks is *how far is home*
8. the player has been the subject for more than `CAMERA_MAX_HOLD_S = 45` and has not moved a
   cell, and the rival has → **the rival, CLOSE**
9. the player has not moved for more than four times `STALL_SECONDS` — sixteen seconds, not four,
   because a four-second pause is a manoeuvre and sixteen is a jam → **the player, CLOSE**
10. the machinery is counting down and nothing above fires → **the machinery, CLOSE**
11. otherwise → **both machines, WIDE**

Four of these are load-bearing and the rest are housekeeping.

**Rule 1 produces the target beat**, at 5:32, with nothing scripted: the warning arms while the
player is at 11.5 cells, and the camera is on the machinery for the whole of 5:32–5:58.6.

**Rule 4 is the echo, and it is the one rule that points the camera at nothing.** The scripted
echo is born at (48, 101), in a labelled dead end fifty cells from anything, and its entire
meaning is *that there is nothing there*. A viewer can only see that if she is shown the empty
room, so the camera eases to it, sits on visibly bare rock while two rings expand out of it at
2:35 and 2:36.5, and eases back. The ambiguity the spec asks for belongs to the **machine**,
which hears a bearing indistinguishable from twenty-two rival pings; the spectator is meant to
know better. This is the only rule in the list that promotes a sound with no source, and no
second one may be added: a camera that chases every ping is a camera that shows nothing.

**Rule 8 fixes the 236-second fix drought.** The player is doing nothing worth a close shot and
the rival is walking to the machinery and downloading inside the ring at 5:13; a sports director
cuts to the thing that is happening, and this display now can.

**Rule 10 draws the heartbeat.** The machinery's seventy-five-second cycle has never been drawn
in this project. Placed this low it takes the camera only when the match has nothing else — which
in this seed is windows 1, 2 and 3, at 0:41, 1:56 and 3:11, all of them empty. That is exactly
right: the rule is learned three times for free, before it costs anything, and by window 5 the
camera is there because a machine is.

**When it moves, and whether it ever cuts.** `CAMERA_MIN_DWELL_S = 6.0` and `CAMERA_EASE_S = 1.2`
govern all of it, per §6.5, **except that a MAJOR event overrides the dwell** — a death, a moved
beacon or the echo may take the camera at any time, because the dwell exists to suppress noise and
a MAJOR event is by definition not noise. **The dwell is overridden; the ease never is. The
director does not cut, ever.** Two subjects at once (rule 5, and rule 1 when both machines are in
the ring) are framed by their midpoint with the scale opened just enough to hold both, capped at
WIDE.

**Where the subject is placed in the frame, which the overlays make a real question.** The subject
is centred in the main view, and the inset and minimap sit in the two corners a centred subject is
furthest from — §3.6 does the arithmetic and finds 77 px of clearance between a CLOSE hazard ring
and the inset. Two rules keep it true: **the centre is never shifted to dodge an overlay**, because
shifting the centre moves the whole world under the viewer, and if a two-subject frame would put
either subject under an overlay **the scale opens instead**, which only zooms out. `_layout()`
asserts the CLOSE clearance, so a future change to `PIP_INSET_FRACTION` fails loudly rather than
quietly covering the machinery.

### 7.3 If she never touches it

The match plays as a directed film. Truth is big and belief is small for the whole eight minutes;
the truth camera moves about twenty times, easing, never cutting; the belief frame re-centres a
handful of times; the minimap, the rail and every piece of chrome are fixed. The one swap is the
8:00 reveal and the design performs it for her. Nothing waits for input and nothing is hidden
behind a gesture.

This is the case the gate is run on, and it is the case every screenshot and every `--snap`
frame must be judged in.

### 7.4 If she does

| input | effect |
|---|---|
| **left drag inside the main view** | orbits. `azimuth` free, `elevation` clamped 60–90. **Both** cameras take the new attitude (§6.8). The spike verified that vispy dispatches a drag to the ViewBox under the cursor and to no other, so no extra hit-testing is needed for the orbit. |
| **click the inset** | **swaps.** §3.7. The two scenes trade rectangles over 0.28 s. Clicks during a swap are ignored until it finishes. |
| **hover the inset** | pointer cursor; the border brightens over 0.12 s; the swap glyph fades in. The only affordance, and it carries no text. |
| **drag inside the inset** | **nothing.** The inset is `interactive = False` and is one hit target. A gesture that is a click at one length and an orbit at another is a gesture that has to be taught. |
| **wheel** | zooms **the main view only** — the spike verified per-ViewBox dispatch: truth `scale_factor` moved 165 → 124 while the other camera did not. On the truth scene this **takes the camera off the director.** Over the inset and over the minimap, the wheel does nothing. |
| **right or middle drag** | pans the main view. Same override. |
| **`Space`** | **re-align.** Both cameras to azimuth 0, elevation 72; the truth camera to WIDE and back onto the director when the override expires; the belief frame re-centred on the believed pose. The undo. **It does not swap the slots back** — undoing a crooked camera and undoing a deliberate choice of picture are different actions (§6.8 device 4). `Space` then one click is how a viewer gets the same cave and the same map at the same scale in the same rectangle, which is the comparison §6.7 is about. |
| **`R`** | Recall. Unchanged, and still the only input that touches the sim. |
| **`T`** | the truth channel toggle. It now also **forces the belief scene into the main slot** and puts the `TRUTH HIDDEN` card in the inset, because a hidden truth scene has no business being the big picture. §10.8. |
| **`D`** | **retired.** §3.5. |
| minimap | nothing. `interactive = False`, and no click target. It is an index; there is nothing to switch to. |

No key is bound to the swap, deliberately: the affordance under test is the click, and a keyboard
shortcut for the same thing would make the slice-4 look harder to read.

**The manual override, and why it expires.** Once the viewer zooms or pans the truth scene, a
`CAMERA · MANUAL` chip appears in the title band and the director stops moving the camera. After
`CAMERA_RESUME_S = 12.0` seconds with no further input the chip fades and the director eases back
to its current subject over `CAMERA_EASE_S`. Twelve seconds is long enough to look at something
and short enough that a viewer who has wandered off is returned to the match rather than left
staring at a rock. Orbiting alone does **not** trigger the override, because the director does not
control attitude — it controls centre and scale — so a viewer can spin the cave all match without
ever losing the direction. **Swapping does not trigger it either**, and this is deliberate: the
director keeps running the truth scene in the inset, so a viewer who has gone to look at the map
still gets a moving, correctly-framed close shot in the corner when the machinery starts counting.

### 7.5 Does the recorder script a path?

**Almost none, and deliberately.** `Recorder` runs the director exactly as the live window does,
with truth in the main slot for the whole match. The recording must be the artefact that was
tested; a camera or a layout that behaves differently in the mp4 makes the mp4 a different
display, and this phase has already been burned once by testing something other than what was
built.

Three exceptions, all at the ends of the match, all already in the design:

- **The cold open, −0:06 → 0:00.** The truth camera starts at elevation 90, azimuth 0, WIDE — a
  flat map — and eases to 72° over six seconds while the cave fades up under the twenty-two
  words. The camera *arriving* is what makes the flat plan resolve into a place, and it teaches
  the viewer in one move that the big picture has depth. It is a branch in `advance()`, not a new
  timer.
- **The swap's one demonstration, at −0:03.** The inset grows to 40 % and returns over 0.5 s
  (§3.7). It is in the recording as well as in the window, because the recording is what a second
  viewer is shown and the affordance has to be in both.
- **The reveal, 8:00 → 8:12.** `_orbit_for_reveal` is retargeted, and the arrangement changes what
  it reveals. The truth camera eases to WIDE and rises to elevation 90, the belief camera follows
  by the shared attitude, **the two scenes swap**, and the true wall outline draws over the map the
  machine built — in one rectangle, at one scale, from directly above. The flat design ended on the
  two pictures side by side; this ends on them **on top of each other**, which is what
  superposition actually means and is the one moment in eight minutes it is spent. The spike
  verified that the programmatic camera path carries over unchanged: 120 frames of
  `azimuth += 0.5, elevation −= 0.25` landed exactly where they should, at 0.30 ms per set.

Nothing else in the recorder changes. The frame is still `canvas.render()` on a hidden canvas in
its own process, still at 20 fps, and the whole match renders in about 6.7 minutes before the
chrome text is grouped and about 4.3 after.

---

## 8. What changes in the sim

**No `tuning.py` number changes. None.** Not `SPOOF_*`, not `ANCIENT_*`, not `BEACON_RANGE`,
not `ESCAPE_SECONDS`, not `ANCIENT_WARNING_S`, and — see §6.7 — not `WALL_POINT_HEIGHT`, which
is consumed inside `Belief` and is therefore a sim number wearing a display name. Every
"Measured:" note in that file was earned against a specific behaviour and this proposal is not
entitled to spend them.

The reason is not conservatism, it is the experiment. The diagnosis under test is
**legibility**. If the display and the pacing change in the same commit, a different result on
the re-run cannot be attributed to either. **The beat sheet after this work is identical to the
one the tester watched**, which makes the re-run a clean A/B on the display alone. The
designer's pacing fixes — `BEACON_RANGE`, waypoint abandonment — are explicitly out of this
scope and belong in a separate commit whose effect can be read.

That is also the answer to the one thing that looks like it needs a sim change. An earlier
draft wanted `SPOOF_ARM_S = 5.0` so the beacon could redden five seconds before the lie — which
shifts every beat after 2:21.4, forces a re-baseline of the beat sheet, and invalidates both
reference renders. It is not needed. `Sim._script()` **already** computes the arming condition
every tick: the lie fires once the victim is `SPOOF_LIE_CELLS - SPOOF_AHEAD_CELLS` = 30 cells
from its most recent beacon, measured in the belief frame. Storing that as a 0..1 fraction in
`Sim._spoof_arm_dist` — a field that already exists in `__init__` and is currently unused —
gives the display the same five seconds of held breath for free. Nothing inside the sim reads
it, no branch changes, no event time moves. In this match it starts rising around 2:16 and
reaches 1.0 at 2:21.4.

**Additive display constants only**, in the existing `# ---- display` block:

```python
# ---- display: the spectator screen ------------------------------------------------
COLD_OPEN_S:             Final[float] = 6.0
END_HOLD_S:              Final[float] = 8.0
GLYPH_LENGTH_CELLS:      Final[float] = 2.4    # 2x the true footprint; see 6.4
TETHER_MIN_CELLS:        Final[float] = 3.0    # below this the tether is noise
TETHER_HOT_CELLS:        Final[float] = 12.0
TETHER_ALARM_CELLS:      Final[float] = 30.0
HAZARD_COUNTDOWN_FROM_S: Final[float] = 15.0
COMET_SECONDS:           Final[float] = 20.0
EVENT_STRIKE_S:          Final[float] = 0.12
EVENT_DECAY_S:           Final[float] = 0.90
SPOKE_RESIDUE:           Final[float] = 0.12
FIX_GHOST_S:             Final[float] = 1.2    # 1.6 for a disagreeing fix
SPOOF_STAGGER_S:         Final[float] = 0.25
SILHOUETTE_HZ:           Final[float] = 4.0
ERROR_SAMPLE_HZ:         Final[float] = 2.0
STALL_SECONDS:           Final[float] = 4.0
CAPTION_MIN_DWELL_S:     Final[float] = 2.5
DEPTH_TINT_FLOOR:        Final[float] = 0.45   # how dark the far end of the cave gets
FEED_ROUTINE_COOLDOWN_S: Final[float] = 30.0   # was hard-coded 12.0 in event_feed.py
FEED_BEARING_CHANGE_DEG: Final[float] = 25.0   # a repeat line needs a moved bearing

# ---- display: the third dimension -------------------------------------------------
CAVE_WALL_HEIGHT_CELLS:  Final[float] = 8.0    # tall enough to read as rock; 3 reads as a kerb
CAVE_FACE_SHADES: Final[tuple[float, float, float, float]] = (1.00, 0.84, 0.62, 0.46)
                                               # +x/+y/-x/-y, a fixed world light, not a camera one
CAVE_BASE_SHADE:         Final[float] = 0.42   # wall foot, so a wall has a visible vertical
TETHER_Z_CELLS:          Final[float] = 9.0    # one cell above the rock; a rope, not a floor line
ELEVATION_MIN_DEG:       Final[float] = 60.0   # below this an 8-cell wall hides >23% of the floor
ELEVATION_MAX_DEG:       Final[float] = 90.0
ELEVATION_DEFAULT_DEG:   Final[float] = 72.0   # 92% of the floor visible, walls still have faces
CAMERA_WIDE_CELLS:       Final[float] = 225.0  # the whole 200x120 cave with a margin
CAMERA_CLOSE_CELLS:      Final[float] = 40.0   # holds the 18-cell lethal disc and both machines
CAMERA_EASE_S:           Final[float] = 1.2    # an ease, never a cut
CAMERA_MIN_DWELL_S:      Final[float] = 6.0    # a camera that is always drifting is not trusted
CAMERA_MAX_HOLD_S:       Final[float] = 45.0   # after this, cut to whatever is actually moving
CAMERA_RESUME_S:         Final[float] = 12.0   # manual override expires; the match resumes
CAMERA_NEAR_CELLS:       Final[float] = 20.0   # two machines this close are one shot
BELIEF_RECENTRE_S:       Final[float] = 10.0   # the map may not walk off the edge; it may not swim

# ---- display: picture in picture ---------------------------------------------------
PIP_INSET_FRACTION:      Final[float] = 0.24   # of the main view, in each axis, so the two
                                               # rectangles are similar and a swap rescales a
                                               # picture without reframing it. Largest value for
                                               # which a CLOSE hazard ring still clears the inset.
PIP_SWAP_S:              Final[float] = 0.28   # under the ~0.3 s where a change becomes a wait
PIP_HOVER_FADE_S:        Final[float] = 0.12   # border brightens; the only affordance, no label
PIP_TEACH_S:             Final[float] = 0.5    # the cold open's one half-swap demonstration
PIP_TEACH_TO:            Final[float] = 0.40   # what the inset grows to during that half-swap
MINIMAP_PX_PER_CELL:     Final[float] = 1.0    # 200x120 over a 200x120 grid: never resampled
```

`FEED_*` are the only two that change existing behaviour, and both were previously hard-coded
inside `event_feed.py`. They change what the timeline *says*, not what the sim *does*.
`ELLIPSE_SIGMAS`, `MAX_POINTS` and `WALL_POINT_HEIGHT` are unchanged. `CAVE_RASTER_SCALE` is
**dropped** — the second design's 800 × 480 raster was for a flat cave image that no longer
exists; the mesh is built from the grid directly and the floor image is 200 × 120.
`MINIMAP_PX_PER_CELL` moves from the second design's 1.25 to **1.0**, because at exactly one
pixel per cell the minimap's `Image` is never resampled (§3.3). `__main__.py`'s default canvas
goes 1400 × 900 → 1600 × 900.

**Two pacing questions are raised in §10 and not answered here**, because they are the
designer's to answer and because answering them in this commit would confound the test.

---

## 9. Build order

**Precondition, and it is not negotiable.** The gate is re-run **live**, with her hand on the R
key, and every slice below is watched live. The playtest record already recommends this and it
costs twenty minutes. Rendering this to an mp4 and showing her the mp4 learns as little as the
first run did, because the tension criterion is about a decision and a video does not contain
one.

Two stop points, at 2.75 days and at 5.5. If slice 1 does not read, stop and report — that is the
diagnosis being wrong, which is worth knowing after under three days rather than after ten.

| # | slice | what you can look at | days |
|---|---|---|---|
| **1** | **The truth channel, the cave in 3D at main size, the director, and the machinery clock.** All of §4 — `stage_frame.py`, `stage_builder.py`, `Sim.stage()`, the `_in_tick` tripwire, the `_world` rename, the `MatchView` facade, all eight invariant rules. Then `cave_mesh.py` (the extruded capped mesh at 8 cells, `fov=0`, the four-face world light, the floor image transparent under rock), `truth_panel.py`, `director.py` (§7.2, the priority list, the ease, the dwell, the overlay-clearance assert), both machines to scale, both comets, the ghost, the tether as a rope with its off-frame stub, and the machinery ring and its countdown. Plus a **stub minimap** — outline image, two dots, the camera footprint box, about forty lines. The belief view is **exactly as it is today**, on its old camera, untouched, at the inset's `pos` and `size` — a layout change and nothing else. **No swap yet.** No palette pass, no rail, no timeline, no captions, no cold open, no manual camera control. | The whole hypothesis. Point it at 5:25–6:00 of seed 7, live, and watch a stranger for thirty-five seconds. | **2.75** |
| **2** | **The two numbers and the two captions, and the rail they live in.** Rail geometry; the two display numbers at 34 pt in its top block, beside the inset; about thirty caption strings stacked under them with the priority and dwell rule; the action block. | 2:21.4 landing as a beat rather than as a dot cloud moving eight pixels. | **0.75** |
| **3** | **The belief scene in three dimensions.** Its own `TurntableCamera` with the shared attitude and its own fixed whole-cave framing; z as evidence type (§6.7); **the mapped silhouette on the z = 0 plane**; the two-class cloud; the residue spokes on the floor plane; the pre-fix ghost; the `set_data` gate. | Whether the small picture reads at 300 px — which under this arrangement is the question, and it is a harder one than the flat design asked. | **1.25** |
| **4** | **The mouse and the swap.** Manual orbit with the attitude mirror, the 60–90 elevation clamp, per-scene wheel and pan, the manual override and its expiry, `Space` re-align, the two compass ticks — and `pip.py`: two slots, hit-testing, the 0.28 s transposition, per-frame `scale_factor` re-derivation, the hover border and glyph, the text-in-inset rule, interactivity following the slot. | Whether a viewer who touches the display can still find her way back, whether she finds the swap at all, and what the belief map looks like at 1252 px. | **0.75** |
| **5** | **The full minimap.** The eight remaining marks in §3.3 at exactly 1 px/cell: machinery on its real cycle, deposits, the shaft and its extraction pulse, the ghost dot and the whole-cave tether, the moved beacon after 2:21.4. | Where everything is, while the camera is somewhere. | **0.5** |
| **6** | **Palette, type and hierarchy — and the chrome text grouped.** The twenty-one-value palette, the four type sizes with the 9 pt floor, the ambient/secondary/primary pass over all three scenes, the status panel cut to three rows with the overprint fixed, the map key moved into the rail and faded. **Every chrome string grouped into four `Text` visuals**, which §6.10 measures at −15 ms a frame and which is what pays for the larger main view. | The screen as a designed object rather than an accumulation — and the frame budget halved in the same afternoon. | **0.75** |
| **7** | **Timeline.** The machinery rail with all six windows drawn from frame one, the two error traces, five event kinds instead of eight, the de-metronomed feed, the `--snap` ordering fix. | The shape of the whole match, and the next kill sliding toward the playhead. | **0.75** |
| **8** | **Event choreography.** The three-marks rule, the 0.25 s stagger, the spoof arming glow and beacon travel, the wreck, the stall ring and counter. | Cause-then-effect at 2:21, and a death at 6:56 you watch happen. | **0.75** |
| **9** | **Ends and the toggle.** The cold open with the camera's descent **and the swap's one half-swap demonstration**; the 8:00 reveal retargeted as a **scripted swap with the true outline drawn over the built map in one rectangle**; deposits at their true radius; the point-of-no-return line; the `T` toggle, which now forces belief to the main slot and puts the `TRUTH HIDDEN` card in the inset. | The first six seconds and the last eighty. | **0.75** |
| **10** | **Recorder, perf, render.** The record path in its own process, the layout verified at both the shown and the hidden canvas size, the warm-up budget, one render, `--invariant` re-run — **and the three measurements the spike could not give us: a ViewBox at 841,344 pixels, two ViewBoxes overlapping a third, and a ViewBox resized every frame for 0.28 s.** If the main view exceeds §6.10's 11.5 ms worst case, `RAIL_W` widens and everything else follows, because the inset and minimap are fractions and the framing is in cells. *If passage-following wavefronts are wanted, they are built here, inside `stage_builder.py`, never through `SensorRig`.* | The comparison video, the invariant printing eight things, and the first honest number for the main view. | **0.75** |

**Total: 9.75 days**, with looks at **2.75** and at **5.5**.

**What the arrangement did to the estimate**, against the side-by-side 3D design's 9.25:

- **Slice 1 got cheaper, −0.25.** One main rectangle with two derived overlays is less layout work
  than two balanced panels plus a minimap band, and the belief side needs *no code at all* in
  slice 1 — the existing view is given the inset's `pos` and `size` and left alone. The slice-1
  look therefore arrives sooner, which is the point of having one.
- **Slice 4 grew, +0.25**, and it is where the whole arrangement lives: `pip.py`, the slot
  abstraction, the transposition, the affordance, the text rule.
- **Slice 9 grew, +0.25.** Both ends gained work: the cold open's demonstration and a reveal that
  is now a swap plus a superposition rather than two pictures side by side.
- **Slice 10 grew, +0.25**, because three things in §6.10 are derived and not measured, and a
  design that quotes a derived number owes a measurement.
- Everything else is unchanged, because the arrangement changes which rectangle a picture is in
  and almost nothing about what is drawn in it.

**The second stop point moved from 5.0 to 5.5**, and the reason is worth stating rather than
absorbing: under the flat layout the belief scene was at full size from slice 3, so "is the right
half readable on its own" could be asked as soon as slice 3 landed. Under this arrangement the
belief scene is a 300 px inset until the swap exists, so the same question cannot be asked until
slice 4. **That is a real cost of the arrangement** — half a day later to the second-most
important question in the phase — and it is paid because the first question, which is whether a
stranger can follow the match at all, gets asked a quarter of a day earlier.

Nine and three quarter days is a lot for a phase whose spec says in bold *"do not engineer
this."* The defence is unchanged and it is the same one the flat design made: the display **is**
what is under test — R1 is the largest risk in the project, the gate failed on legibility, and no
other artefact of this phase is the thing being measured. Roughly forty per cent of it is also
the specification for BLD-148, BLD-149, BLD-150, BLD-152 and BLD-154 (6 + 8 + 8 + 5 + 10 days
budgeted in Phase 4), and this arrangement *raises* that fraction again: a measured orbit with an
occlusion table, a director with a priority list, a text-grouping finding, and a working
picture-in-picture with a swap are all things BLD-148 and BLD-149 were budgeted fourteen days to
discover. The design survives even though the Python does not.

**Files.** New: `match/stage_frame.py`, `match/stage_builder.py`, `match/match_view.py`,
`view/truth_panel.py`, `view/cave_mesh.py`, `view/director.py`, `view/pip.py`, `view/minimap.py`,
`view/caption.py`, `view/rail.py`, `view/beat.py`, `view/cold_open.py`, `view/text_group.py`.
Modified: `view/view.py` (becomes a compositor — layout, two slots, three scenes, header, wiring,
resize; it sheds more than it gains), `view/palette.py`, `view/timeline.py`,
`view/event_feed.py`, `view/status_panel.py`, `view/map_key.py`, `view/recorder.py`,
`match/sim.py`, `match/invariant.py`, `match/headless.py`, `tuning.py`, `__main__.py`.
**Untouched: `belief/`, `policy/`, `truth/`, `sensing/`, `audio/`, `view/decision_graph.py`,
`view/node_box.py`, `view/shapes.py`, `view/backend.py`.**

---

## 10. What this does not fix

1. **She had no connection to the bot, because she put no work into it.** This is the
   designer's first diagnosis and I believe it is the true one. **No display fixes it, and
   pretending otherwise would be the expensive mistake here — a third dimension least of all.**
   Attachment comes from authorship, and authorship is Phase 2. The most this display can do is
   make the machine a *character* — named, embodied, visibly deciding, visibly about to be wrong
   — so that Phase 2's authorship has something to attach to. Watching a stranger's machine be
   cleverly wrong is a documentary. Watching one you taught is a game.

2. **It does not create a decision.** Recall is still one key. The point-of-no-return line makes
   the existing decision *expire* visibly; it does not make the decision *cost* anything. A
   dilemma needs two options with different prices, and spending Recall currently has no visible
   price for waiting. That is a design gap and it is above my pay grade, but it should be on the
   agenda before the next gate: criterion 4 may keep failing on design grounds with a perfect
   display.

3. **The 236-second fix drought.** After 4:03.9 the machine never re-enters any honest beacon's
   6-cell acquisition range, so the spec's "single most important visual" fires four times in
   eight minutes and never in the second half. **I am displaying the absence rather than
   removing it** — a lengthening tether, a `LAST CORRECTION 3:12 AGO` row, and now a camera that
   cuts to the rival because the player has nothing to show. That is more frightening than
   another flash and it is still not a fix. The alternative is raising `BEACON_RANGE` from 6,
   which `tuning.py` explicitly trades against `BEACON_DROP_EVERY_CELLS = 45`: *"the gap between
   6 and 45 is where the smear happens."* **The designer has taken this one; it is out of this
   scope and its commit must be separate from this one so the A/B stays clean.**

4. **The 79.4-second frozen ending.** 6:40.6 → 8:00, motionless in truth and belief, 16 % of the
   match. The display makes it agonising rather than blank — the camera pushes in and deposit B's
   ring sits 200 px away on screen — and that is all it can do. `tuning.py` already names the
   cause: *"the C3-to-ANC passage itself, which is a navigation-stack problem for Phase 3."*
   The policy question behind it — after the second consecutive skipped waypoint, abandon the
   route and start the shaft search — is the designer's and is likewise out of this scope.

5. **The near-miss at 5:41 is luck, not agency.** The machine survives by 0.038 cells because it
   happens to be jammed against rock. It is the best four seconds available, this display now
   spends 27 seconds of camera on it, and it is still a coincidence of `ANCIENT_PHASE_S = 30`.
   `tuning.py`'s own note says several other phases kill the *player* instead — *"the spoof walks
   it into the machinery's chamber, which is DESIGN's 'march into a trench' beat and worth a
   deliberate seed later."* That is a designer's call and it is probably worth more than half of
   this proposal.

6. **Audio is untouched, and the 3D decision took one small thing away from it.** The mixer keeps
   its signature and reads Belief only, deliberately — §4.2 rule 3. Sound now has visible
   consequence, which was the stated complaint, but 636 sound events with no dynamic range is a
   separate afternoon and it is out of scope for a change meant to isolate one variable. **What
   the flat design claimed as a free win is now gone:** it argued that fixing the camera azimuth
   at 0 made the mixer's bearing-relative stereo pan consistent for the whole match. With an
   orbitable view it moves again whenever the viewer spins. The resolution: the mixer is fed the
   **belief** camera's azimuth and the truth camera's is ignored, because bearings are
   belief-frame quantities and the belief scene is where they are drawn. Under §6.8's shared
   attitude the two are always equal anyway, so this only decides which one is read.
   `Mixer.update(belief, t, azimuth)` is unchanged.

7. **It is 3D, it is picture in picture, and here is what both cost.** The flat design argued the
   opposite case on the third dimension and it is kept here as the record, because the argument
   was not silly and part of it is still live: the shipped view was *the bad half of 3D* — an
   unlit orthographic projection tilted 32° with no occlusion, no ground plane and no perspective,
   which had every ambiguity of a 3D image and none of the depth cues; and **a third dimension
   names nothing.** Nothing on the shipped screen said *machine*, *cave*, *hazard*, *lie* or
   *rival*, and a rotatable version of an unnamed picture is an unnamed picture you can rotate.
   That second point survives both decisions completely: **almost everything in this document
   that answers the tester is the naming, not the dimension and not the arrangement** — the filled
   cave, the eleven chamber names, the drawn rival, the countdown clock, the tether with a number
   on it, the two words `IT IS WRONG BY`. The third dimension is what makes the cave read as a
   place and lets the camera come close enough for a machine to be a machine; picture in picture
   is what lets that close shot have the whole screen. Both are strong amplifiers and neither is
   the message.

   What the third dimension cost, concretely, each of them measured or forced rather than feared:
   **a clamped camera** (60–90°, because an 8-cell wall hides three quarters of the floor at 30°,
   §3.4); **the loss of pixel identity between the two pictures** and with it comparison by
   superposition, spent everywhere except the 8:00 reveal (§3.1); and **an input the viewer can
   get wrong**, which is why §7 exists and why `Space` does.

   What the arrangement cost on top of that is four things. **The belief scene spends the match at
   300 × 161**, which is defensible only because its legibility is a texture rather than a scatter
   (§3.1 argument 2) and is the single thing most likely to be wrong. **The second gate viewing is
   no longer a pixel-clean A/B** (item 8 below). **The second stop point moved half a day later**
   (§9). And **three numbers in §6.10 are derived rather than measured**, which is a debt slice 10
   pays. What neither decision cost is frame time, which is the thing everyone expected: the 3D
   screen is 15 % faster than the flat one, and this arrangement spends about three milliseconds
   of that back to make the main picture two and a sixth times bigger.

8. **It makes the spectator smarter than the player, and that is a real cost.** If Phase 1 passes
   its gate with the truth scene on, we will have proven that the **replay** is compelling —
   which is real, and is BLD-154 — and proven nothing about the run phase, which is R1, the risk
   this phase exists to retire. That is why the truth scene is bound to `T` and why the gate is
   two viewings: **truth on first so she learns the world, truth off second so we find out
   whether the belief scene alone now carries it.** The second viewing is the one that answers
   R1; the first is what makes the second interpretable.

   **The arrangement changed what viewing two is, and the change is a trade rather than a win.**
   In viewing two, `T` hides truth, forces the belief scene into the main slot, and puts
   `TRUTH HIDDEN — THIS IS WHAT THE OPERATOR SEES` in the inset; the minimap goes dark with it,
   because every mark in it is truth-derived, and so do the first display number and the
   point-of-no-return line. **What is gained:** viewing two is no longer half a screen of black —
   it is the belief map at 1252 × 672, which is the operator view, so Phase 3 inherits a working
   layout instead of a hole. **What is lost, and it is the flat design's stated reason for the
   `TRUTH HIDDEN` card:** the belief scene is *not* pixel-identical across the two viewings any
   more. In viewing one it is a 300 px inset and in viewing two it is the whole screen, so the
   comparison is no longer clean. The question viewing two answers therefore shifts slightly —
   from *"does the belief scene alone carry it at the same size"* to *"does the belief scene alone
   carry it when it is the whole screen"* — and that is arguably the more useful question, since
   the shipping operator view is belief at full size and never belief in a corner. It is still a
   confound and it is recorded as one.

9. **The third dimension does not fix the belief scene, and the arrangement leans on that fact
   rather than hiding it.** The real cloud at 8:00 is 6,007 points spread over 174 × 100 cells —
   **0.35 points per cell** — and it reads as a diagonal of disconnected blobs whether it is flat,
   tilted or orbited. Lidar's 28,597 are denser but confined to a 68 × 73 corner. **Orbiting a
   fragment shows you nothing a fixed view did not**, and neither does enlarging one. What makes
   the belief picture legible is the mapped silhouette (§6.4 belief mark 1) — a 170 × 130 texture
   that costs nothing and turns six thousand dots into a shape that can be seen to drift. The
   belief scene is 3D because the attitude is shared with the truth scene and two pictures seen
   from different directions cannot be related; it is not 3D because the third dimension solved
   anything there.

   **Picture in picture raises the silhouette from important to load-bearing.** At 1.33 px/cell in
   the inset, individual points are not resolvable at all — the silhouette is the entire picture.
   §10.9's old line was *"if a day ever has to come out of the plan, it comes out of slice 3's
   camera and not its silhouette."* Under this arrangement that is no longer a preference: **the
   inset without the silhouette is 6,000 unresolvable dots in a 300 px box, and the arrangement
   fails.** If slice 3 has to be cut in half, the half that survives is the silhouette and the
   two-class cloud, and the belief camera can stay at `elevation=90` for the gate.

10. **It does not make Phase 1 less throwaway.** All of it is deleted at Phase 3. `StageFrame` is
    the one idea that survives, as `ReplayFrame` — and now the occlusion table, the director's
    priority list, the text-grouping finding and the slot/scene separation survive as notes for
    BLD-148 and BLD-149.

**Everything guessed at, listed as `CLAUDE.md` requires.**

- **Truth is the big picture and belief is the inset.** The reasoning in §3.1 is mine; arguments 1
  and 3 are judgements and argument 2 is a reading of the spike's measurements rather than a
  measurement of the question. **A designer could reverse this in one line** — the slots are
  symmetric and `pip.py` takes which scene starts in which — and if the slice-1 look shows a
  viewer who never once looks at the inset, reversing it is the cheapest experiment available.
- **The layout's pixels**: `MAIN_W = 1252`, `RAIL_W = 300`, `MAIN_H = 672`, the inset at 24 % in
  the top-right, the minimap at 200 × 120 in the bottom-left. The 1.863:1 aspect is chosen to
  match the flat design's truth panel so the framing constants survive; everything else is
  invented. The 77 px of overlay clearance is arithmetic, but the *requirement* that a CLOSE
  hazard ring must clear the inset, with `_layout()` asserting it, is my rule.
- **`PIP_SWAP_S = 0.28`, `PIP_HOVER_FADE_S = 0.12`, `PIP_TEACH_S = 0.5` and the half-swap
  demonstration in the cold open.** All invented. The demonstration in particular is the thing
  most likely to read as fussy and it is flagged in §3.7 as the first thing to cut.
- **That an animated swap beats an instant one**, and that similar rectangles preserve object
  identity across it. This is a claim about perception, argued from first principles and not
  tested. It is cheap to falsify: set `PIP_SWAP_S = 0` and look.
- **That the hover border and a wordless glyph are enough to make the inset read as clickable.**
  This is the weakest guess in the document and §3.7 admits it by ranking "she may never click it"
  as the fourth affordance. It is what slice 4's look is for.
- The twenty-one colour values and the four type sizes are my invention, calibrated by eye and
  not against a display.
- **The cave's wall height of 8 cells.** No spec exists; the spike measured 8, 5, 4, 3, 2.6 and 2
  and recommended 8. It sets the entire occlusion table and therefore §3.4's clamp. **This is the
  single most consequential guess in the document and it wants the designer.**
- **The six lighting numbers** — four face brightnesses and the base darkening — are the spike's,
  invented for a probe. They are the whole lighting model and they are why the cave reads as
  stone, so they are load-bearing and unvalidated.
- **The elevation clamp at 60° and the default at 72°.** Derived from the occlusion table, but
  the choice of "77 % of the floor visible is enough" is mine.
- **The director's priority list, its eleven rules, and every camera constant** — dwell, ease, max
  hold, resume, near-cells, and the two framings in cells. Invented here. The list is the thing
  most likely to need a second pass after the first live look.
- **The minimap's marks, and that it always shows truth.** The panel design had no minimap; the
  designer's brief added one and gave no size. The exclusions (beacons out, the moved beacon in)
  are judgements, and 1.00 px/cell is chosen for the resampling property rather than because 200
  px is the right size.
- `GLYPH_LENGTH_CELLS = 2.4` is a judgement call about the smallest legible glyph that does not
  distort the 9-cell radius. The arrangement relieved the pressure on it and it is unchanged.
- The eleven chamber names are mine — `cave.CHAMBERS` has only `S`, `C1`, `DA`, `C2`, `ECHO`,
  `C3`, `ANC`, `SUMP`, `DB`, `C4`, `R`. The twenty-two words of the cold open are mine.
- `FEED_ROUTINE_COOLDOWN_S = 30` and `FEED_BEARING_CHANGE_DEG = 25` are guesses at what stops
  the metronome without also eating the echo.
- **The nine-and-three-quarter-day estimate**, every per-slice number in it, and in particular the
  claim that slice 1 got a quarter-day cheaper because the belief side needs no code.
- **Three performance numbers are derived, not measured**: the main view at 841,344 pixels, two
  ViewBoxes overlapping a third, and a ViewBox resized every frame. §6.10 states the derivation,
  the range, and the one-constant fallback; slice 10 measures them.
- The spike's own numbers were taken on one machine at one DPI scale, over 60–90 frames per
  condition. A worst-case figure over 90 frames will not catch a once-a-minute stall.

---

## 11. The riskiest assumption

**That a spectator who knows the answer still cares about a machine that does not.**

The whole Phase 1 display was built on the opposite premise — that the viewer should be as lost
as the agent — and it produced a bored tester. This inverts it completely: it replaces *mystery*
with *dread*, and those are different emotions with different failure modes. **Mystery fails by
being illegible, which is what happened. Dread fails by being inert.** If the viewer, handed the
answer, simply shrugs — *"I can see where it is, so what"* — then the display will be perfectly
legible and still boring, and we will have spent ten days to learn that the problem was never
the display. That is R1 coming back, harder, with one fewer excuse.

Neither the 3D decision nor the picture-in-picture decision changes that risk, and neither should
be read as insurance against it. They change the *cost of being wrong*: nine and three quarter
days instead of seven and a half, and two more hypotheses spent. The tester named 3D herself, so
if this fails there is no obvious next rendering change to try, which is a reason to build it
properly and a reason to stop at the slice-1 look if it does not read.

The specific way it could fail is worth naming, because it is not the obvious one. It is not
that she cannot read the big picture; it is that she reads **only** the big picture, where a small
machine drives slowly around a cave for eight minutes and occasionally stops — which is also
boring, and boring in a worse way, because the truth reveal will have been spent for nothing and
there is no third card to play. **The director makes this failure mode more likely, not less**,
because a camera that is always pointed at the interesting thing on the truth side gives the eye
even less reason to travel. **And picture in picture makes it more likely again, which is the one
place this arrangement is worse than the layout it replaces.** Side by side, the belief map was
half the screen and it was hard *not* to see it; as a 300 px inset it is easy to ignore for eight
minutes, and a viewer who ignores it has watched a documentary about a robot in a cave rather
than a game about a machine being wrong. That is the specific thing to watch for at the slice-1
look, and it is why the second question below is not a formality.

The mitigation is not more inset. It is that the gap does not live in the inset: it is the rope
with a number on it in the big picture, the two integers in the rail, and the line between two
dots on the minimap (§6.9.1). **If the viewer never looks at the inset and still says "it thinks
it's over there and it isn't", the design has worked and the inset is a bonus. If she never looks
at the inset and cannot say that, the inset was never the problem.** Those two outcomes are
distinguishable at the slice-1 look and they point at different fixes, which is the reason for
running slice 1 before anything else exists.

Cinema says dramatic irony works: Hitchcock's bomb under the table beats Hitchcock's surprise
explosion. But the bomb works because the audience is willing the character to **notice**, and a
character who structurally *cannot* notice — which is precisely what an autonomous machine under
this invariant is — may not sustain it.

**The cheapest way to find out, and it costs under three days rather than ten.** Build slice 1
only — the truth channel, the cave in three dimensions filling the screen, the director, both
machines, the ghost and tether, the machinery clock, the stub minimap, and today's belief view
dropped unchanged into the inset rectangle. Point it at **5:25–6:00 of seed 7**, live, not
recorded. Those thirty-five seconds contain the countdown arming at 5:32, the machine walking to
9.038 cells against a 9.000 lethal radius and standing there for the entire four-second kill
window, the window closing, the machine stepping inside 0.8 seconds late at 5:45.8, and the two
machines passing at 0.41 cells at 5:56.1 — all of it in one frame at **31.3 pixels per cell**,
because the director is there and does not cut. Say one sentence — *"the big picture is what is
real, the little one is what the machine thinks"* — and then watch three things:

- **Does she lean in at the countdown?** If a stranger watches a machine stand on the rim of a
  lethal circle while a clock runs out and does not react, nothing in the other seven days saves
  it, and R1 is real.
- **Do her eyes ever go to the inset, and can she say what the machine believes?** These are two
  questions and they must be scored separately, because the answers point at different fixes. If
  she never looks at the inset but can still say the machine thinks it is somewhere else, the
  tether and the numbers are doing their job and the arrangement is right. If she can say
  nothing about what the machine believes, the gap is not reading anywhere and this design is
  wrong about its own thesis.
- **Does she touch anything?** She has no swap in slice 1 and no manual camera, so this is only
  an observation — but if she reaches for the inset unprompted, slice 4 is validated before it is
  built, and if she tries to drag the big picture, §7.4's clamp is what stands between her and a
  cave seen edge-on.

If the first two answers are yes, build the rest. If either is no, stop and report, and do not
spend the other seven days finding out more slowly.
