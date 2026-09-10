# The ice

The reconciliation `DESIGN-PRINCIPLES.md` §10 asks for. What the ice-age decision keeps, what it
breaks, what it costs, and the rulings a builder needs before touching anything.

Written 2026-09-09, minutes after §10 was recorded, and revised the same day when the designer
extended it: *"the background in the outside can be massive mountains with some civilization built
up in them."* That extension is folded in throughout and is not an appendix — it changed three
rulings rather than decorating them, and §2.7 is the one it reversed. §10 is the specification;
this document is subordinate to it and never overrules it.

**Three labels, used on every claim below, and nothing is unlabelled.**

| label | means |
|---|---|
| **DECIDED** | the designer said it. §10, or an earlier numbered principle. Not negotiable here |
| **PROPOSED** | mine, argued from something already in the repo, and I recommend it |
| **GUESS** | mine, with no evidence behind it. A number I picked, or a fact I invented. Every one is also collected in §10 |

**Nothing here deletes existing fiction silently.** Where a passage has to go, it is quoted, its
file and section are named, and its replacement is written out. Where two existing documents
already disagreed before the ice arrived, §2.10 says so rather than papering over it.

**One thing this document does not do.** It does not touch `spikes/godot/`. Everything said about
what is built there is a cost estimate, not an instruction.

---

## 0. The ruling in one page

| # | question | ruling | §  |
|---|---|---|---|
| 1 | Did the machinery stop? | **Yes. It froze, stood silent for the ice, and restarted when the meltwater reached it.** PROPOSED, and it is the highest-value ruling in the document | §4 |
| 2 | Is the existing backstory still true? | Almost all of it. The claim answer, the survey's finding, the index, the six downloads, the no-remains rule and the loot-by-depth chronology all survive, and four of them get *better* | §1 |
| 3 | What is the worst breakage? | The cave's dimensionality. `CellPos` is `(u16, u16)` and `rasterise` emits a heightfield. A heightfield cannot hold a passage under a chamber | §2.1, §5 |
| 4 | Second worst? | The surface. A valley, a town on a mountain wall and a view are not a re-skin of a 126 × 68 m yard with ±1.2 m of relief in it. The mountains themselves are nearly free; the inhabited wall is not | §2.2, §7.5 |
| 5 | Third worst? | `ART-DIRECTION.md` §9 contains the sentence **"No crystal, no ice, no bioluminescence, no glowing ore."** The decision is textually forbidden by the art direction's own rules-out list | §2.5 |
| 6 | How long ago were the ancients? | **~1,400 years.** ~1,150 of it ice. The melt front passed the pit-head ~70 years ago. PROPOSED, and the number is set by the iron, not by the glaciology | §3 |
| 7 | What is the cave made of now? | Three regimes by depth: **dead ice, then bedrock karst, then the workings** — and the shaft the player goes down is the ancients' own shaft, because the meltwater found it first | §5.2 |
| 8 | Is ice art or mechanics? | Both, and the split is stated per property. The load-bearing mechanic is that **ice is where the sensor stops working**, which is this game's subject arriving as terrain | §6 |
| 9 | What does the trailer become? | Act I opens on the valley instead of the headframe, shot 4's rain becomes meltwater, the reversal gains a third register (warm → white → black), and the last shot gains home on the wall above the empty shaft | §8 |
| 10 | What did the mountains change? | **They rescued the light economy.** A valley floor in the shadow of an 1,800 m wall is lit by 12000 K skylight, which is exactly what `ART-DIRECTION.md` §2.1 already specifies. And they put the ice age on the wall as a **trimline** the town straddles — the timeline told as geography, with no date | §2.7, §7.3 |

**The single best thing the decision buys, and it is not on the list above.** The deepest download
in the game (`WHAT-HAPPENED-HERE.md` §4.2, station 6) is the Assayer's summary sheet: *"the
accumulated horizon — depth, dip, and continues on every bearing, for a hundred years."* Under §4's
ruling **that sheet has a hole in it, and the hole is the ice age.** A player who has collected
enough index to read the sheet reads a number series that stops, stays stopped for a very long
count, and starts again. There is no prose, no date, no calendar, and no language — which is
`WHAT-HAPPENED-HERE.md` §0 rule 2 obeyed to the letter — and it is the only artefact in the world
that measures the ice. It costs nothing to build because the sheet already exists.

---

## 1. What survives unchanged

Be suspicious of a reconciliation that finds everything fine. This one genuinely does keep most of
the fiction, for a structural reason: `WHAT-HAPPENED-HERE.md` is a document about **a business
failing on a margin**, and a business failing on a margin is orthogonal to the climate. The ice
arrives *after* the story is over. It does not participate in it.

### 1.1 Passages that now read better than they did

**`THE-MACHINERY.md` §7, "Why the workings are flooded":**

> *"The pumps stopped when the industry left. The water that drowned the mine is the water that
> fills the Assayer's header tank — the mine's failure is the machine's power supply."*

Survives verbatim, and doubles. The mine's failure is the machine's power supply; the *world's*
failure is the machine's off switch; the world's recovery is the machine's on switch. One sentence
now carries three events instead of one, and none of the words change. **DECIDED** — §10's "Ice
explains the water" bullet says exactly this.

**`WHAT-HAPPENED-HERE.md` §2.1, on the client:**

> *"So the client, in the sense that matters, is whoever eventually buys the claim. ... Nobody
> came."*

This was the weakest load-bearing sentence in the backstory, because "nobody came" over a century
is a coincidence and coincidences age badly. Under the ice it stops being a coincidence and becomes
a fact about the world: **nobody came because there was nobody to come, and then there was nowhere
to come to.** The survey has been holding a claim against a legal system that stopped existing.
That is a better sentence than the one it replaces and it required no change.

**`WHAT-HAPPENED-HERE.md` §1.2, the claim answer:**

> *"a running survey is how you hold ground, and holding the ground was the last asset the company
> had."*

Survives entirely, and gains its ending. The company converted its mine into a machine that would
hold its claim without it. It worked. **The claim was held for fourteen centuries and the holder
was a ring of iron machines, and the thing they held it against was an ice age.** Nothing in §1.2
needs a word changed; it just got a second act.

**`WHAT-HAPPENED-HERE.md` §1.1, "Nobody died here":**

> *"There are no remains, no bodies, no personal effects, ever, anywhere in this game."*

Strengthened, and it needs defending, because the ice will make somebody want to put a frozen
person in a crevasse. Do not. The wind-down was orderly and finished *before* the ice — that is
§3's timeline doing real work — so the rule is not a convention any more, it is a consequence.
Keep §6.8's absence list exactly as written and add nothing to it.

**`WHAT-HAPPENED-HERE.md` §1.3, "No date, no era, no calendar":**

This is the passage I expected to break and it is the one that gains most. An ice age is a
**stratigraphic** date, not a calendar date. It gives the world a period without giving it a year,
a name, or a sentence — which is precisely the constraint §1.3 imposes. The world still tells time
by counting (the index), and it now has a second clock that is also not a calendar: the ice. Two
clocks, no language, no dates. **Keep §1.3 verbatim.**

**`WHAT-HAPPENED-HERE.md` §1.3, "No lost civilisation" / `THE-MACHINERY.md` §7, "A works, not a
temple":**

At risk, and rescued by §3's ordering. The temptation the ice creates is enormous: a pre-ice-age
civilisation *sounds* like a lost civilisation, and a lost civilisation is a temple. **The defence
is that the ice did not kill them. The margin did.** They failed, wound down, took their machines
up the shaft and left, and then — decades or a century later, to people who had nothing to do with
this mine — the world got cold. The mine is still a business failure. The civilisation is a
separate, larger, and deliberately unexamined thing that the game never enters. **PROPOSED**, and
it is the ruling that keeps §7's rule alive.

**`ART-DIRECTION.md` §5.2, "Graphitised, below the waterline":**

> *"Real metallurgy: cast iron underwater loses its iron and leaves a soft graphite shell that
> keeps the shape. Black, non-metallic, velvety, roughness 0.98. Intact in silhouette and dead in
> surface."*

Survives, and §4's ruling is what makes it survive at fourteen centuries rather than one. Cold,
anoxic, still fresh water is the best iron-preserving environment that exists on land. A machine
that spent 1,150 years submerged in meltwater at 1–4 °C with no oxygen and no motion comes out
graphitised and *shaped*, which is exactly the material this section already specifies. Under "it
never stopped" the same 1,150 years are 480 million hammer blows and there is no brake band left.
**The material rule is evidence for §4, not a casualty of it.**

**`ART-DIRECTION.md` §7, the six depth cues**, items 1, 2, 3, 5 and 6 (worked increases, iron
increases, water increases, the marks get younger, the beacon chain thins). All survive. Item 3
and item 6 get stronger: deeper is wetter is now hydrologically forced rather than asserted, and a
beacon chain going *down* a shaft is a vertical string of lights receding, which is the image
`ART-DIRECTION.md` §6.3 already calls the most beautiful in the game, rotated ninety degrees.

**`THE-MACHINERY.md` §7, "Why the rock is magnetically noisy":** untouched.
**`THE-MACHINERY.md` §4, the whole damage and coupling model:** untouched, except that §6.3 adds a
third medium cost.
**`THE-MACHINERY.md` §8, the two siblings:** untouched. The Bus and the Haulage are deep, and deep
is where the ice never reached.
**`WHAT-HAPPENED-HERE.md` §3, the index:** untouched. Grammar, blocks, series bars, the tally
board, the no-third-Fix-source argument in §3.2 — none of it interacts with the climate.
**`WHAT-HAPPENED-HERE.md` §4.2, the six downloads:** the ladder survives with one qualification in
§5.5 (the depth bands become literal, which the ladder wanted anyway).
**`GLOSSARY.md`:** eighteen of nineteen terms survive. The exception is in §2.8.
**`CLAUDE.md`'s invariant, `ARCHITECTURE.md`, `DETERMINISM.md`:** untouched. Nothing here proposes
that anything downstream of the sensor layer sees `World`.

### 1.2 The two existing inconsistencies the ice does not touch

Recorded so nobody thinks the ice caused them.

1. **`THE-MACHINERY.md` §1's "an exhausted claim" against `WHAT-HAPPENED-HERE.md` §2.3's "it does
   not end."** Already flagged as `WHAT-HAPPENED-HERE.md` §8 inconsistency 2, still open as
   question 2 in that document's §10. The ice changes nothing about it, and question 2's default
   (yes, *exhausted* means the ore the mine could reach) remains right.
2. **The index has two forms drawn** — `K 14 · 2` on the machinery board against `K7-41` on the
   cave board. Already flagged as `WHAT-HAPPENED-HERE.md` §8 inconsistency 1, question 4. Untouched.

---

## 2. What breaks, and how badly

**The cheapest true statement about cost in this document, and it should be the frame for every
estimate below.** Both Godot spikes are built on the same layout/dressing seam that
`DESIGN-PRINCIPLES.md` §5 mandates, and both have *already survived a total rebuild of the layer
below the line*: the cave's photoreal pass rewrote every shader and reports the same content hash
`0xAD83E3ED` before and after, and the surface's photoreal pass rewrote both shaders, the ground
mesh and the lighting without moving `layout.gd`'s hash. So:

> **Snow, ice, light and palette are a dressing change and cost nothing above the line. A valley
> and a vertical cave are layout and topology changes, and they cost the plan, the hash, the
> determinism tests and everything downstream of them.**

That is the whole shape of the estimate. The setting's *look* is affordable and the setting's
*shape* is not.

Twelve contradictions, ranked. Cost is an order of magnitude, not an estimate — the estimate
belongs to whoever owns the file, and everything said here about `spikes/godot/` is read from its
own notes rather than from the code.

| # | breakage | file · section | cost | kind |
|---|---|---|---|---|
| **B1** | The plan and raster are 2.5D. A vertical cave has things below other things | `spikes/PROCEDURAL-AND-GODOT.md` §1.2, §1.1 | **weeks**, unbuilt work rather than rework | structural, above the line |
| **B2** | The built surface has ±1.2 m of natural relief in a fixed 174 × 148 m box. A valley has hundreds of metres of wall, a town on it, and a view | `spikes/godot/surface/NOTES.md` §2.1.1, §2.1.9 · `ground.gd` | **weeks.** The mountains are nearly free (§7.5); **the inhabited wall is where the money goes** | above the line |
| **B3** | The cave's entire vertical range is under 2 m, its shell profile has a floor and a crown, and there is no shaft geometry at all | `spikes/godot/cave/NOTES.md` §2.2, §3.1 R2 · `topology.gd`, `dressing.gd` | **weeks** | above the line |
| **B4** | The lidar envelope −30°/+12° cannot see down a shaft or up a moulin | `DESIGN-PRINCIPLES.md` §8 | **days**, or **zero** if §6.2's ruling is taken | sim |
| **B5** | "Depth is drawn as darkness, not as altitude" | `ART-DIRECTION.md` §3.5, §8.4 · `SPECTATOR-DISPLAY.md` §6.7 | **days** | art + display |
| **B6** | ~~The shaft's 12000 K is "the only cold light, and the only daylight"~~ **This entry inverted when the mountains arrived.** A shadowed valley floor is lit by 12000 K skylight, so §2.1 is reconciled rather than broken; what gets harder is in-frame dynamic range | `ART-DIRECTION.md` §2.1 · `surface/PHOTOREAL.md` §3.4 | **days**, and it is a saving against what this row said before | art, resolved |
| **B7** | Every "a hundred years" in the backstory | `WHAT-HAPPENED-HERE.md` §1.1, §2.1, §2.3, §3.3, §5 | **hours** (edits), but it gates §3 and §4 | fiction |
| **B8** | "the machinery never stopped" | `THE-MACHINERY.md` §1 · `WHAT-HAPPENED-HERE.md` §1.2 · `GLOSSARY.md` · `ART-DIRECTION.md` §1 · `TRAILER.md` §10 | **hours** (edits), and it is §4's whole subject | fiction |
| **B9** | "No crystal, no **ice**, no bioluminescence, no glowing ore" | `ART-DIRECTION.md` §9 | **one line**, and getting it wrong costs the palette | art rule |
| **B10** | "One warm rock family, no hue axis anywhere" against a blue-white snowfield — and snow lit at `(0.60, 0.74, 1.00)` sits next to `SENSED #63D6F7` | `ART-DIRECTION.md` §3.1, §8.4 must-not 1, §9 | **days** of palette work, and it is the sneakiest item on this list | art rule |
| **B11** | "One pit-head per team; rivals are never seen above ground" against a shared town | `docs/art/vision/surface/NOTES.md` guess 3, design problem 4 | **days**, and it is a design question | design |
| **B12** | The exposure contract, the sightline statistics and the visibility-range strategy were all measured on a flat cave and a hellscape yard | `ART-DIRECTION.md` §2.9, §3.6, §5.5 · `cave/PHOTOREAL.md` §4.2 · `PROCEDURAL-AND-GODOT.md` §4.4 | **days** of re-measurement; **three conclusions reverse** | measurement |

**And a cost that is not a contradiction and is easy to forget: every captured frame in the project
is re-shot.** Sixteen surface shots, twelve canonical cave shots, eight photoreal pairs, seven
ORDER before/after pairs, thirty-six material sheets, plus the whole trailer capture stage. None of
it is hard and all of it is time.

### 2.1 B1 — the cave is not three-dimensional anywhere in the pipeline

This is the largest consequence of the decision and it is a build consequence, not an art one. §5
is the whole answer; what follows is only the statement of the break.

`PROCEDURAL-AND-GODOT.md` §1.2 is explicit: every position in `CavePlan` is a `CellPos`, and
`CellPos` is `(u16, u16)`. `Chamber.centre`, every point of `Passage.spine`, `Shaft.at`,
`DepositSite.at`, `AncientSite.at`, `DiscoverySite.at` and `Feature.at` are all planar. Height
exists as exactly two per-chamber scalars, `floor_mm` and `ceiling_mm`, and §1.3 says so in as many
words:

> *"**No geometry.** No vertices, no normals, no heights except `floor_mm` / `ceiling_mm` datums.
> The heightfield is `rasterise`'s output, derived, not carried."*

Three separate things follow, and each is fatal on its own:

- **`Passage` carries no height at all.** No `floor_mm`, no `ceiling_mm`, no gradient. A passage
  cannot slope, cannot drop, and cannot be a pitch. Meltwater cutting downward is unrepresentable.
- **`rasterise` emits a heightfield**, which is single-valued in z. No overhang, no ledge, no shaft
  passing a chamber, no moulin over a drive. §10's own words — *"levels, drops, and things below
  other things"* — name precisely the three things a heightfield forbids.
- **`depth_band` is BFS graph distance from the nearest shaft**, not elevation. §10 says *"going
  deeper becomes literal"*, which is an instruction to redefine the field that six documented
  consumers read (`ART-DIRECTION.md` §7's six cues, plus `WHAT-HAPPENED-HERE.md` §3.1's item
  number as a seventh).

And one pre-existing hole in the seam that the vertical rewrite should fix on the way past:
`PROCEDURAL-AND-GODOT.md` §1.6 asserts *"chambers must be taller than the passages that reach
them"* and comments `Chamber.ceiling_mm` as *">= every passage that reaches it"* — but `Passage`
has no ceiling field, so the invariant is asserted against a quantity that does not exist. Found
while reading for the ice; not caused by it.

**There is also a structural dependency nobody has cleared.** `PROCEDURAL-AND-GODOT.md` §6 records
that the entire plan schema is written against `PHASE-3-OPEN-QUESTIONS.md` §38's *recommendation*
(chambers plus carved passages) rather than a decision, and that if §38 comes back "CA with
connectivity repair" then *"the plan has no chambers and no passages to record and the seam
collapses to shipping the raster. That is the single largest structural dependency in this
document."* **A glacial vertical generator is a third answer to §38 and has to be argued as one.**
It is not a variation on either of the two on the table.

### 2.2 B2 — the surface as built has no relief and no horizon

`PROCEDURAL-AND-GODOT.md` §5.5 justified building the surface first on the grounds that *"the
pit-head is the **same place every match** ... It is authored once, not generated"*, and the
designer answered that question **yes, on 2026-09-08** (Q15). That answer is still right and the
work is still worth having. What changes is the *extent* of the place, and the built numbers say
how much:

- **The site box is fixed at 174 × 148 m and the seed does not move it** (`surface/NOTES.md`
  §2.1.1). Inside the fence is 126 × 68 m.
- **The ground is one ArrayMesh in one draw call** — 65,095 vertices, 129,072 triangles, 0.5 m
  inside the compound, 1 m over the rest, then a geometric skirt out to 420 m. **That skirt is the
  entire horizon, and it is a flat fringe, not landform.**
- **The whole natural relief of the built surface is about ±1.2 m of integer noise, plus fourteen
  spoil tips of 3.2–10.5 m.** `NOTES.md` §7.1 says it plainly: *"The ground is a 1 m heightfield.
  No displacement, no ruts, no wheel tracks in geometry."*

A valley is hundreds of metres of relief and a vista measured in kilometres. That is not a bigger
version of this mesh; it is a chunked, LOD'd terrain system with streaming, and the current mesh
build already takes 900–1,700 ms in GDScript. **This is the largest single new-work item in the
whole decision** and it is the one to get a schedule opinion on before anything else.

**Three specific things break rather than merely scale, and each is a named line of code.**

1. **`materials.gd:504` derives "is this spoil" from world height:**
   `float mud = max(smoothstep(0.55, 3.2, wpos.y) * 0.9, vcol.g);`
   On a valley, **every surface above 3.2 m becomes mud.** `surface/NOTES.md` §1 already flags this
   as the one place the shader reads world Y where it should read a layout field, and says what the
   fix is: *"if the sim ever needs to know 'is this cell spoil' it must come from the plan, not
   from the shader's threshold."* The ice forces it.
2. **The ground shader's hardstanding is two `vec4` rectangles** — `pad`, `pad2` — plus two wear
   hotspots `hot_a`, `hot_b`. A town has streets, not two rectangles. That is a shader-structure
   change, not a parameter change.
3. **Every layout rectangle is hand-listed against a flat pad**: five building footprints, nine
   zones, ten `ranks` strips, six walkways, the fence, the haul road. `ORDER.md` §8.1 already
   concedes it — *"a real generator would derive stores runs from the buildings, the pad edges and
   the circulation graph rather than list them."* A town means re-authoring all of that against a
   street graph. **That cost is design and retuning, not architecture**, which is the good news in
   this item.

**And the exposure problem, which is separate and worse than it looks.** The yard's hardstanding
sits at **0.24 linear albedo**, and `surface/PHOTOREAL.md` §7 says why: *"this sits at the bottom
of the range because the yard is meant to be a hellscape."* Overcast runs `tonemap_exposure 0.70`
with `ambient_light_energy 1.30`. Fresh snow is 0.7–0.9 linear. **Every exposure number in
`weather.gd` has to be re-derived**, and the image-statistics targets the photoreal pass set for
itself (p50 ≈ 0.33, under 2% dead black) have to be re-argued for a world whose ground is three
times brighter than the one they were fitted to.

**What is genuinely lost, and it should be said out loud.** The ground shader is ~800 lines whose
entire subject is weathered concrete: slab joints on the 3.6 m module, arris, per-bay lippage,
spalling, repaired patches, hairline cracks, half-exposed aggregate, oil, tracked mud, ruts,
puddles. It is the most expensive asset the photoreal pass produced and it is the one the setting
change makes least visible. That is a sunk cost rather than a new cost, and the honest consolation
is in §7.1: what snow puts on the ground instead is worth more to this particular game than
concrete was.

### 2.3 B3 — the cave has under two metres of vertical range and no shaft

The cave spike is a plan-view maze extruded to one floor height per station. The measured facts:

- **`grid_state` is a flat `PackedByteArray` of `w_cells × h_cells` bytes, indexed
  `cy * w_cells + cx`.** One byte per cell: `ROCK` / `DRY` / `FLOODED`. `h_cells = 76` is
  hard-coded, giving a fixed 45.6 m lateral corridor at `CELL_MM = 600`. There is no third grid
  axis.
- **`S_FLOOR_MM` is the only vertical quantity in the entire system** — one signed integer per
  station. The main drive falls **−2 mm per cell** (−3.33 mm/m, −480 mm over the whole 144 m
  stretch) and there is exactly one sump bowl, 1500 mm deep, at 58% of the stretch. Crosscuts
  wander ±8 mm/cell. **Total vertical range of the built cave: under two metres.**
- **`dressing.gd::_st_pos()` sets world Y exclusively from `floor_mm`**, and the shell is a
  40-vertex ring swept along a Catmull-Rom through those points. `_half_profile()` builds *a floor,
  two legs and a crown.* **A vertical shaft cannot be expressed by that profile function at all.**
  A moulin needs a second profile family, not a modification of this one.
- **`K_SHAFT = 3` exists as a station kind and is decorative.** It is assigned only to station 0,
  and `dressing.gd` never branches on it. **There is no shaft geometry anywhere in the cave spike.**
  The only shaft that exists is the surface side's collar.
- **Crosscuts alternate side and nothing anywhere produces a downward branch.**
- **`_chunk_key()` is XZ-only**, 8 m chunks, 49 for the whole cave. A vertical shaft puts an entire
  cave's worth of geometry into one chunk key.
- **`water_y` is a single global float uniform** and the water datum is `lowest_floor + 950 mm`.
  `cave/PHOTOREAL.md` §7 already lists this as guess 4: *"That the water datum is global.
  ART-DIRECTION gives a waterline per axis; this treats the whole cave as having drowned once, to
  one level."* **Meltwater cutting downward is precisely the case where one horizontal datum is
  wrong**, and the ice turns a flagged guess into a required change.

**What survives, and it is more than it looks.** `topology.gd` is 428 lines of pure integer code
with a stateless hash RNG. The rules that change are R1 (spine), R2 (floor), R3 (width runs), R9
(crosscuts) and R11 (rasterise). The rules that survive verbatim are the `draw(purpose, a, b)`
hash, the FNV-1a `content_hash()`, R10's 17-flag works bitfield, R4's `worked` ramp, R6's rock type
per 9-cell block, R8's water and wetness (re-datumed), R12's discoveries, and the whole 16-int
station row **minus the meaning of `S_X` and `S_Y`**. On the dressing side the 47-mesh kit, the
four shaders, the generated noise volumes, the chunking and every placement rule are reusable. **It
is the topology layer that is rewritten, and it is the small file.**

### 2.4 B12 — three measured conclusions reverse

Not a contradiction so much as a warning to whoever re-runs the probes.

1. **`ART-DIRECTION.md` §3.6's sightline statistics** — median 3.6 m, longest anywhere 49.8 m,
   *"90.8% of all directions under 12 m"* — and the two rules that follow (*"spend no art budget
   past 15 m"*, *"no landmark may be required to be visible across a chamber"*). A 40 m winze
   looked down is a single straight line longer than anything the cave currently contains.
2. **`PROCEDURAL-AND-GODOT.md` §4.4's LOD strategy**: *"Nothing is ever far enough away to need a
   decimated version. **Visibility ranges replace LOD entirely.**"* That is downstream of the same
   49.8 m. **LOD comes back**, and the cave spike's own post-photoreal ablation says how much is at
   stake: turning visibility ranges off costs **≈45 ms** (6.16 ms → 51.43 ms). The ranges are not
   insurance any more, they are the frame, and a vertical sightline is what defeats them.
3. **`ART-DIRECTION.md` §5.5**: *"The mast buys exactly zero extra cells of visibility at ground
   level"*, measured from ground level on a plane. From a level *above* the Assayer's chamber,
   looking down into it, a 6.6 m mast with a winch head that emits during the wind is exactly the
   landmark §5.5 said it could not be. **This partially reverses `ART-DIRECTION.md`'s own design
   problem 6**, which currently blocks one of the four gate questions.

And a fourth that is not a reversal but a hole: **the exposure contract does not survive daylight
underground.** `lumcheck.py` currently passes 9 of 12 cave frames against §2.9's bands, and the two
that fail already fail for *not enough black* (`05_two_registers` at 56.78%, `08_waterline` at
68.49%). Daylight down a moulin invalidates the contract for every frame it reaches. §2.7 is the
proposed fix.

### 2.5 B9 — the art direction textually forbids ice

`ART-DIRECTION.md` §9, "What this rules out", third bullet:

> *"**No crystal, no ice, no bioluminescence, no glowing ore.** That is fantasy-cave vocabulary and
> it pulls the world toward hue-swap biomes, which is the exact failure this direction exists to
> prevent."*

This is one line and it costs one line, but the *reason* behind it is right and must survive the
amendment. The rule was written to stop the season system becoming a palette swap. Ice arriving as
a **setting** rather than as a **biome** does not threaten that, and the amendment should say so:

> **PROPOSED replacement.** *"No crystal, no bioluminescence, no glowing ore. **Ice is a material
> and a place, never a biome and never a hue axis**: it changes surface, translucency and sensor
> response, and the rock family underneath it is unchanged. Nothing in this world glows because it
> is cold."*

### 2.6 B10 — the snow is close to the colour of belief, and the mountains change how close

This is the item most likely to be missed and it is the one that damages the game rather than the
schedule. **The mountains make it simultaneously more true and much less dangerous**, and both
halves of that need saying.

`ART-DIRECTION.md` §8.4, must-not 1: *"**Cyan is belief. No cyan in the world** — not a team, not a
lamp, not an LED."* The world's warm/cold split is load-bearing across both registers: warm and
filled is real, cool and sparse is believed.

**More true.** §7.2 puts the valley floor in the shadow of an 1,800 m wall for most of the day, and
a shadowed snowfield under a clear sky is lit by pure skylight, which really is on the order of
12000 K. So the surface vision board's guess 4 — *"the surface's light is the shaft's light"* —
stops being a convenient fiction and becomes physically correct, and the ground the player stands
on genuinely is blue-white. Trying to paint that neutral would be fighting the physics of the
setting the designer just chose.

**Much less dangerous, for three reasons, and they are what resolve it.**

1. **Belief and the snowy exterior almost never share a frame.** Belief is drawn in the live run
   view and in the replay, and both of those are underground — `ART-DIRECTION.md` §8.3 makes
   belief-only *"the default live view"* for the run phase, which happens after the descent. On the
   surface, belief appears on a **screen in the world**: the pendant and the bench terminal, which
   are objects a few hundred pixels across. The collision I was worried about is confined to those
   screens, and a screen is allowed to be cyan because it is a screen.
2. **The mountains supply the warm register and it is unreachable.** Alpenglow on the peaks at
   2,600–3,200 m is the only sunlit surface in the exterior and the player can never stand on it.
   That gives every wide frame a warm third — cold blue floor, warm lit peaks — with no invented
   light source, and it is `DESIGN-PRINCIPLES.md` §4's two-register collision handed over by the
   landscape. The town's lit windows are the second warm element and they are at human scale.
3. **The floor is dim as well as blue.** Skylight in a shadowed valley is roughly a tenth to a
   seventh of full sun. My arithmetic, and it is mine: snow at 0.8 albedo under a tenth of the
   illumination is comparable in luminance to the built yard's 0.24 concrete under full overcast —
   possibly darker. **The snow does not automatically dominate the frame by value**, which was half
   of what made the cyan risk frightening.

**So the rule to write down is about saturation, not hue.** `SENSED #63D6F7` and `GHOST #9FE8FF`
are *saturated and bright*. Skylit snow is high-value and low-saturation, and skylit shadow is
low-value. **Nothing in the world may use belief's saturation at belief's brightness** — that is
the enforceable version of must-not 1 and it survives a blue-white exterior intact, where a literal
"no blue outdoors" would not.

And one hard line regardless: **no emissive in the world is ever cyan.** Not a status LED, not a
window, not a vehicle light, not a screen seen from outside. The ground may be the colour the sky
makes it; nothing may *emit* belief's colour.

### 2.7 B6 — "the only daylight" is not broken by the mountains. It is rescued by them

This entry inverted when the mountains arrived, and it is the largest single saving in the
document.

`ART-DIRECTION.md` §2.1's light table calls the shaft *"the only cold light, and the only
daylight"*, at 12000 K, `(0.60, 0.74, 1.00)`. That was written before `DESIGN-PRINCIPLES.md` §3
gave the game a surface. The surface vision board recorded the conflict as its own design problem
1 and papered it with guess 4; then the built spike went further and half-overruled §2.1 outright.
`surface/PHOTOREAL.md` §3.4, verbatim:

> *"The sun is now near-neutral, (1.00, 0.985, 0.962), and the sky keeps the cool bias... Real
> overcast diffuse is 6500–7500 K, not 12000 K; **12000 K is a clear-sky north window.** This is a
> design call and I have made it provisionally."*

and its consequence:

> *"The claim §2.1 is defending — that the shaft is the only cold light in the game — survives in
> the ambient... **The direct beam does not.**"*

**A valley floor in the shadow of an 1,800 m wall is a clear-sky north window, at the scale of a
landscape.** There is no direct beam on the floor at all — the sun is on the peaks and the ridge,
and the floor is lit by the sky alone. So:

- The exterior's illuminant is **skylight, cold, high colour temperature, low intensity**, which is
  what §2.1 already describes.
- The shaft's 12000 K stops being an exception and becomes **the same light, arriving through a
  smaller hole.** The sky lights the valley; the sky lights the collar; the collar lights three
  metres of shaft and then stops. That is one continuous physical story from the peaks to the
  sump, and §7.2's `datum_mm` is the axis it runs down.
- `PHOTOREAL.md` §3.4's provisional call is **answered rather than overruled**: the sun stays
  near-neutral and correct, and it simply is not on the ground the player is standing on.

**PROPOSED, and it replaces what this section said before the mountains: `ART-DIRECTION.md` §2.1
does not need amending. It needs a fifth row.**

| source | who owns it | reach | colour | notes |
|---|---|---|---|---|
| **the sky** | the world | the valley floor, and three metres down the shaft | 12000 K `(0.60, 0.74, 1.00)` | the same light as the shaft's, and the shaft's row becomes *the last of it* |

And a sixth, which is the only warm light in the exterior and is deliberately out of reach:
**alpenglow on the peaks**, ~2,000 K on snow at 8–15 km, present for minutes, never illuminating
anything the player can touch.

**What genuinely gets harder, said honestly.** The *in-frame dynamic range* goes up, not down.
Sunlit snow on a peak against shadowed snow on the floor is somewhere in the region of thirty to
sixty to one within a single frame — my arithmetic. That is a real exposure problem and it is the
same problem `ART-DIRECTION.md` §2.3 already loves underground (*"a 90:1 falloff across three
metres is the one thing that says carried light"*), moved outdoors and made twenty times wider.
The discipline transfers exactly: **do not compress the ramp, let the peaks blow, and grade for the
floor.** A frame in which the peaks are correctly exposed is a frame in which the valley is black,
and that is the wrong picture.

**PROPOSED.** `ART-DIRECTION.md` §2.9's exposure table still gains a second column, and the reason
is now the peaks rather than the snow. The lamp-frame targets are unchanged and remain the contract
for everything below the collar. A **daylight frame** gets its own band — **GUESS**: `> 0.50` blown
≤ 8% (the peaks are allowed to be most of that), `> 0.18` mid-or-better 25–60%, `< 0.02` true black
≤ 12% — and the CI assertion runs against whichever set the shot's scene declares. The important
part is not the numbers; it is that one contract cannot cover both, and an artist who lifts a cave
frame to surface levels must still fail the build.

### 2.8 B8 — "never stopped", in five places

Every sentence that has to change under §4's ruling is listed in §4.3. `GLOSSARY.md`'s **Ancient
system** — *"machinery in the ruins that is still operating"* — is the one §10 does not name, and
it survives verbatim under either answer, because it *is* still operating. Recorded so the
glossary is not edited by reflex.

### 2.9 B5 — depth is now altitude, and the display says it is not

`SPECTATOR-DISPLAY.md` §6.7 rules *"Depth is drawn as darkness, not as altitude"*, and
`ART-DIRECTION.md` §3.5's axis table and §8.4's must-not 3 repeat it. Under a vertical cave, depth
and altitude are correlated, and the rule reads as a denial of the setting.

**PROPOSED.** The rule survives with its scope made explicit, because its actual content is about
the *display*, which has no vertical dimension and never will:

> *"On the display, depth is drawn as darkness. The display has no vertical axis and must not
> acquire one; a schematic that tries to show levels shows neither. In the rendered world, depth is
> altitude, because it is."*

That also resolves `ART-DIRECTION.md` §8.4's must-not 3, which currently reads *"The invented
8-cell wall extrusion does not transfer ... Phase 3 has a real heightfield."* **Phase 3 does not
have a heightfield any more** (§5.3), so that sentence needs its last clause replaced regardless of
what the display does.

### 2.10 Where documents already disagreed, and what the ice does to each

| the disagreement | already flagged? | what the ice does |
|---|---|---|
| `ART-DIRECTION.md` §2.1 "the only daylight" vs `DESIGN-PRINCIPLES.md` §3 (a surface with sky) | yes — surface board design problem 1, and `surface/PHOTOREAL.md` §3.4 half-overruled it | **the mountains close it.** §2.7 |
| `ART-DIRECTION.md` §5.5 "the boom is visible from the next chamber" is true of the schematic, false at ground level | yes — `ART-DIRECTION.md` design problem 6 | partially resolves it (§2.4) |
| `ART-DIRECTION.md` §3.1 "no hue axis" vs `DESIGN-PRINCIPLES.md` §6 "it has to look photoreal" | yes — §6 records both, unresolved | adds a third party to the argument (§2.6). Snow is the first thing in the game that is not the warm rock family |
| `ART-DIRECTION.md` §9 "no image texture" vs the noise textures photorealism needs | yes — `PROCEDURAL-AND-GODOT.md` Q5, default yes | untouched |
| `THE-MACHINERY.md` §1 "exhausted claim" vs `WHAT-HAPPENED-HERE.md` §2.3 "it does not end" | yes — `WHAT-HAPPENED-HERE.md` §8.2 | untouched |
| `DESIGN.html` says the cave is natural geology with no ruins | yes — `WHAT-HAPPENED-HERE.md` §8.5 | untouched; a glacial cave is *more* natural geology, so the older document gets slightly less wrong |
| `PROCEDURAL-AND-GODOT.md` §1.6 asserts a chamber-vs-passage ceiling invariant against a field `Passage` does not have | **no — new, found here** | must be fixed by the vertical rewrite anyway (§5.4) |
| `docs/art/vision/surface/NOTES.md` guess 3 (one pit-head per team, rivals never above ground) vs `DESIGN-PRINCIPLES.md` §2's extraction framing, which wants a stash you return to | **no — new, found here** | a town forces it. §7.6 |
| `GLOSSARY.md` **Return** is *"one raw sensor observation"* vs `THE-SENSOR-AND-SLAM.md` §2's multiple returns per beam | **no — new, found here** | unrelated to the ice; flagged because §6.2 adds a third material to the same model |
| `ART-DIRECTION.md` §3.1's dry rock albedo `(0.340, 0.260, 0.175)` vs the measured band — `spikes/godot/materials/NOTES.md` §5.1: *"**0.34 linear is a pale limestone or new plaster** ... This is not a small disagreement, and I think it is the direct cause of what the designer was looking at"* | yes — in the materials spike, open | **forces the ruling.** Ice and snow are genuinely bright, so the game now has two materials at the top of the range and the rock has to be settled against them rather than beside them |
| `PROCEDURAL-AND-GODOT.md` Q5 (generated noise textures allowed) vs `ART-DIRECTION.md` §9's letter | yes — Q5, default yes, unanswered | **gates the estimate.** `cave/PHOTOREAL.md` §5.1: *"If the answer comes back no, most of §2 goes with it."* Any ice or snow material is built the same way |

---

## 3. The timeline, decided

Everything in this section is **PROPOSED** except where marked GUESS, and it is offered as a set
because the numbers only make sense together.

**The number is set by the iron, not by the glaciology.** That is the whole argument. A real
Pleistocene glacial is 10⁴–10⁵ years and nothing recognisable as a machine survives it above the
permafrost. A Little-Ice-Age-scale event is 300–500 years, does not fill a valley with enough ice
to carve moulins, and does not erase a civilisation's records. The answer has to be long enough
that the player's society genuinely does not know who the ancients were, and short enough that a
bearing race is still bright. So:

| quantity | proposal | range I would accept | what pins it |
|---|---|---|---|
| the company wound down | **1,400 years ago** | 800–3,000 | long enough for total record loss; short enough for cast iron |
| the ice closed the valley | **1,300 years ago** | 100–200 years after the wind-down | see below — the gap must be short |
| the ice lasted | **~1,150 years** | 600–2,000 | long enough to be *an ice age* rather than a cold snap |
| the melt front passed the pit-head | **70 years ago** | 40–120 | just outside living memory, inside grandparents' |
| meltwater reached the deep workings and the machinery restarted | **40 years ago** | 20–60 | after the pit-head was exposed, so the society found a dead mine and it woke up |
| the town | **~50 years old** | 30–90 | founded because the melt exposed something |
| the deepest workings are still frozen / not yet drowned | **now, and moving** | — | this is a *place*, not a date. §5.2 |

**Why the gap between the wind-down and the ice must be short — 100 to 200 years, not a thousand.**
`WHAT-HAPPENED-HERE.md` §1.2's entire answer is that the company held its claim with a running
survey, waiting for a buyer. If a thousand years pass before the ice, then a thousand years of
ordinary history had every opportunity to sell, work or scrap the claim, and "nobody came" needs a
second explanation. At a century or two, the answer is clean and needs nothing: **they were still
waiting when the weather changed.** That is the load-bearing number in the table.

**What the player's society knows.** PROPOSED:

- That there was an industrial civilisation before the ice. This is not secret; the headframe has
  been above the snowline for decades and it is made of cast iron.
- That it used iron, water power and a numbering system. Visible from outside.
- **Not** who they were, what they were called, what language they had, or what year it was. There
  is no writing to find (`WHAT-HAPPENED-HERE.md` §0 rule 2), so there is nothing to decode.
- **Not** that the survey exists, what it was for, or that it has an answer. That is the game.
- **Not** that any of it is still running. The first machine to knock on an Assayer found out.
  GUESS, and a good one: the town exists because somebody sent a machine down and it came back.

**Consistency with a machine that is still working.** Under §4's ruling the Assayer has run for
about 40 years of the 1,400, at 75 seconds a cycle: **~17 million cycles**, ~1.7 million full
revolutions of its ten bearings. That is an enormous number for a brake band and it is one
thirty-fifth of the number "it never stopped" requires. The rest of the time it was submerged,
cold, still and anoxic. This is the argument in §4.2 and it is the physical reason to prefer the
restart.

**And the whole timeline is told as geography, which is how a player actually gets it.** This is
the cleanest thing the mountains bought and it should be read as the primary delivery mechanism,
with the table above as the bookkeeping behind it. Three horizontal lines on the valley wall, all
visible from the floor, none of them explained, and no number, name or date anywhere:

| the line | at | what it says |
|---|---|---|
| **the trimline** | **+310 m** | where the ice stood at its greatest. Weathered, jointed, lichened rock above; scoured, polished, freshly exposed rock below. Permanent, geological, a millennium old. One `smoothstep` on world height |
| **the town** | **+90 to +520 m** | it straddles the trimline. Old and dense above it, modern and manufactured below it. **The society has been walking downhill for a thousand years and you can see the whole descent at once** |
| **the snowline** | **+1,100 m** | where the ice is *now*. It is not geological, it is current, and it is moving — the tell is a band of rock below it that is bare, raw and colonised by nothing, because it came out from under the ice inside a human lifetime |

Plus the glacier itself, up-valley, with its terminus 3 km beyond the pit-head, and the pit-head
standing on ground that band uncovered.

**That is the entire timeline of §3, delivered without a word**, and it obeys
`WHAT-HAPPENED-HERE.md` §1.3's rule — *"no date, no era, no calendar"* — as strictly as the index
does. A player who never wonders about any of it still reads *the ice was up to there, it is up
there now, and the town came down in between.* **PROPOSED**, and if only one thing in §7 gets
built, this is the second candidate after §7.1.

**One consequence to note and one temptation to refuse.** The consequence: because the snowline is
current rather than historical, **where it sits is a stated fact that the world can later change.**
`ROADMAP.md` Phase 9 already plans to *"shift generation weights, change an ancient system's state,
publish the transition as an event"* — and a snowline that drops fifty metres, or rises, is that
event as a change to the sky rather than to a patch note. The temptation to refuse: **the snowline
must not move during a match, or between matches, without a deliberate published event.** A world
that visibly changes on its own is a weather system, and `WHAT-HAPPENED-HERE.md`'s thesis is that
this world is one arithmetic, frozen.

**Two things this timeline deliberately does not fix.** GUESS on both, and both should stay
unfixed: how big the ice was beyond this valley, and whether the player's society is the only one.
`DESIGN.html`'s *"specificity ages badly"* applies, and neither question has a world object that
could answer it.

---

## 4. Did the machinery stop?

**My position: yes. It stopped, and it started again.** Take §10's proposed beat.

This is the ruling with the most downstream consequence in the document, and it is genuinely close,
so both cases are argued.

### 4.1 What the two answers actually differ on

Not much, at the surface. **A player in their first hour sees a running machine either way.** The
difference is invisible until layer 3 of `WHAT-HAPPENED-HERE.md` §5, and it is fully legible only
at layer 5. So this is not a decision about what the game feels like on Tuesday; it is a decision
about what the deepest artefact in the game says.

### 4.2 The case for "it stopped"

1. **The physics forces it, and the mechanism is specific.** The Assayer is gravity-fed: a drip
   joint, a header tank, a rising main, a brake band. Under a valley glacier the *surface*
   catchment freezes and the supply stops. What it does **not** do is burst the machine, and this
   is the part that matters: the workings were already flooded to the tide mark
   (`WHAT-HAPPENED-HERE.md` §1.1), and a flooded working freezes from the top down. The deep
   machines stood in **liquid** water — under pressure, under 300 m of rock, at 1–4 °C, anoxic —
   for the whole ice. They did not freeze solid; they went quiet and were preserved. **PROPOSED**,
   and it is the single most useful sentence in this document because it is simultaneously the
   reason the machine stopped and the reason it is intact.
2. **It saves the material timeline.** §3's arithmetic: 17 million cycles instead of 590 million.
   `ART-DIRECTION.md` §5.2's *"bearing steel, still working ... roughness 0.30, metallic 1.0"* and
   *"a viewer reads it is still running off the shine on the bearing before anything moves"* are
   claims about a wear surface. Fourteen centuries of continuous hammering does not leave a wear
   surface; it leaves a hole.
3. **It gives the world its only measurement of the ice, and it costs nothing.** The summary sheet
   (`WHAT-HAPPENED-HERE.md` §4.2, station 6) is *"the accumulated horizon — depth, dip, and
   continues on every bearing"*. Under the restart it has **a gap in the middle**, of a length no
   player can put a year on but every player can see is enormous. No prose, no date, no language.
   This is the layer-5 payoff arriving as a number series, which is exactly the form
   `WHAT-HAPPENED-HERE.md` §0 rule 2 demands, and it did not exist before this ruling.
4. **It creates a world object that is worth more than the ruling costs: the machine that has not
   restarted yet.** If the melt is a moving front, then somewhere at the edge of it there is an
   Assayer standing dry, tank empty or frozen, hammer parked, that has not fired since before the
   ice. A player can find it. A player can, eventually, be the reason it starts. That is a
   generator flag and a hazard state, and it converts §10's *"the melt has come this far"* from
   backstory into a place. §5.2 makes it a depth band.
5. **It is more frightening, which is the designer's own argument** (§10) and I agree with it. A
   machine that never stopped is inertia. A machine that resumed is a machine that was *waiting*.
6. **It gives the player's society a reason to be here now** — also §10's. The melt is the event.
   Without it, "why now" has no answer and the extraction loop is arbitrary.

### 4.3 The case against, honestly

1. **It touches five documents**, and one of them is `ART-DIRECTION.md`'s one sentence, which is
   the build contract everything else was written from.
2. **"Never stopped" is simpler and might be scarier to the only audience that matters — the one
   that never reaches layer 3.** A machine with no history at all is a cleaner horror object than a
   machine with a biography.
3. **The physics does not actually force it.** This is the honest counter and it deserves to be
   stated properly: **a warm-based glacier has liquid water at its bed all year.** A valley glacier
   sliding on a wet bed delivers meltwater to the bedrock continuously, in winter as well as
   summer, and if the mine's catchment is *sub*-glacial rather than surface, the supply never
   stops — it becomes more reliable, not less. Under that reading the ice is a roof, not a
   freezer, "it never stopped" is physically correct, and the machine ran for fourteen hundred
   years. I do not recommend it, because it costs the summary-sheet gap and the material timeline
   and gains only the preservation of five sentences. But it is not a bad answer and the designer
   should know it exists.
4. **A machine that can stop invites a player to stop it**, and `WHAT-HAPPENED-HERE.md` §1.2 exists
   partly to foreclose that: *"It also settles a question the design will be asked eventually — can
   I disable the hazard? No, and the reason is visible on the casting."* Under the restart, a
   player will reason: it stopped once, so it can stop again, so where is the valve? **The answer
   must be written into the ruling, not discovered later:** there is no valve, there never was
   (§1.2 survives untouched), and the thing that stopped it was the water supply of an entire
   mountain. You cannot dam a mountain with a beacon rack. This is a real cost of the ruling and
   the defence has to ship with it.

### 4.4 Exactly which sentences change, under each answer

**Under YES — it stopped and restarted (recommended).**

| file · § | today | becomes |
|---|---|---|
| `THE-MACHINERY.md` §1 | *"It is still running because it never needed anybody — the water that drowned the workings is the same water that fills its header tank and winds the hammer, so it will keep surveying an exhausted claim **for as long as it rains**."* | *"...so it will keep surveying an exhausted claim **for as long as it melts**. It has not been running the whole time. When the ice came the supply froze and it stood in still water and stopped; when the melt reached it, the tank filled and it went back to work on the bearing it had been holding."* The clause *"it never needed anybody"* is untouched, and it is the clause that matters |
| `THE-MACHINERY.md` §7, last-but-two bullet | *"how a thing with no fuel and no store is still hammering after everybody went home. The seventy-five-second period is how long the tank takes to fill."* | unchanged. **And the period stays fixed at 75 s** — see the warning below |
| `WHAT-HAPPENED-HERE.md` §1.1 | *"And then, over a century, the water made the world the art direction already specifies"* | *"over centuries"*, and every other *"a century"* / *"a hundred years"* in §1.1, §2.1, §2.3, §3.3 and §5 gets the same treatment. §3's table is the source of the replacement numbers |
| `WHAT-HAPPENED-HERE.md` §1.2, table row 5 | *"'it never needed anybody' (§1) — the specification, not an accident of construction"* | unchanged, and stronger: the specification was tested by an ice age and passed |
| `WHAT-HAPPENED-HERE.md` §2.3 | *"Every bearing for a century has returned the same thing"* | *"Every bearing it has ever fired on has returned the same thing, in two runs with a very long silence between them"* |
| `WHAT-HAPPENED-HERE.md` §2.5 | *"The answer is powered by the reason the answer is useless, and it will go on being powered **for as long as it rains**."* | *"for as long as it melts"* — and the inversion sharpens, because the thing that made the answer unreachable is now also the thing that switched the machine off and back on |
| `ART-DIRECTION.md` §1, the one sentence | *"A drowned iron mine **that never stopped working**, photographed by one lamp somebody carried in..."* | *"A drowned iron mine **still working**, photographed by one lamp somebody carried in..."* — deliberately the weakest possible edit. The sentence describes what a frame contains, a frame of a running machine is identical either way, and *"never stopped"* is a layer-3 belief the player is supposed to hold and then lose |
| `TRAILER.md` §10 | *"The machinery the previous occupants left did not stop."* | *"did not stop for good."* |
| `GLOSSARY.md`, **Ancient system** | *"machinery in the ruins that is still operating"* | **unchanged.** It is still operating |

**Under NO — it never stopped.**

| file · § | change |
|---|---|
| `DESIGN-PRINCIPLES.md` §10 | the paragraph beginning *"The reframe this opens, and it is the strongest beat available"* is struck, and §10 records that it was considered and rejected |
| §3's timeline | must shorten hard, or the mine's water supply must be declared sub-glacial (§4.3 item 3) and that declaration written into `THE-MACHINERY.md` §7 |
| `ART-DIRECTION.md` §5.2 | the bearing-steel material needs a new justification at 1,400 years of continuous duty, and I do not have one |
| `WHAT-HAPPENED-HERE.md` §4.2 station 6 | the summary sheet stays as written and gains nothing. The ice becomes invisible below ground, everywhere, forever |
| everything else | unchanged. This is the cheap answer and its cheapness is its only argument |

### 4.5 One thing that must not change either way

**The 75-second period is fixed and must never become seasonal.** The temptation the melt creates
is obvious — more meltwater in summer, a faster cycle, a weather system with teeth — and it would
destroy a great deal. `THE-MACHINERY.md` §3 and Appendix B keep `ANCIENT_PERIOD_S 75`,
`ANCIENT_WARNING_S 9`, `ANCIENT_LETHAL_S 4` and every `CAMERA_*` constant deliberately unchanged,
and every measured spectator beat in `SPECTATOR-DISPLAY.md` is derived from them. More importantly,
`THE-MACHINERY.md` §5 makes the cycle *the only honest thing in the cave*: *"Nine clicks at 1 Hz
every seventy-five seconds from a fixed point is the only thing down there that is regular, loud
and not lying."* A variable period deletes that, and with it the clock, the landmark and the
learnable behaviour. **The tank fills in 75 seconds. It always has. Write it down.**

---

## 5. The cave is vertical

**DECIDED** (§10): *"The cave stops being a flat plan of passages and becomes a place with levels,
drops, and things below other things. `blindside-gen` has to carry height as a first-class
dimension rather than as dressing, and going deeper becomes literal."*

Everything in this section that is not that sentence is PROPOSED or GUESS.

### 5.1 The gameplay consequence that comes before any of the geometry

A vertical cave changes the extraction loop before it changes a single triangle, and this is the
part to get a ruling on first.

`DESIGN-PRINCIPLES.md` §2: *"The match is a raid: commit a loadout, go in, get out before the
window closes."* and *"Drift is what makes depth expensive. The tension of the game is I have
something, I am getting lost, do I go one junction further?"*

On a plane, every metre in is a metre out, and the risk of depth is entirely informational — drift.
**In a vertical cave, going down is cheap and coming up is not.** A drop is free, fast, and
one-way. That adds a second, non-informational risk axis to depth, and it is the one Tarkov
actually runs on: **commitment.** *I can get down there. I am not sure I can get back.* And it
composes with the first rather than replacing it: a machine that is lost *and* below a pitch it
cannot climb is in a different kind of trouble than a machine that is merely lost.

**PROPOSED, and it is the single best thing the vertical axis buys:** a machine can go somewhere it
cannot return from, and it can do so *without knowing*, because §6.2 says it cannot see down.
`DESIGN-PRINCIPLES.md` §2's *"Any tuning that removes the possibility of not getting out removes
the game"* now has a second mechanism, and the auto-memory note about never tuning that away
applies to this one too.

It also gives the wreck a new behaviour. `GLOSSARY.md`: *"**Wreck** — a destroyed agent. Persists
for the match, holding its cargo and its policy. Any agent may salvage one."* In a vertical cave a
wreck **falls**, and it can come to rest somewhere nothing can reach. That is a question for the
designer (§9, Q10) and my default is that it should be allowed, because a cargo you can see and
cannot have is exactly this game.

### 5.2 What the cave is made of, by depth

**PROPOSED.** Three regimes. The interleave is the design, not the list.

| band | what it is | ancients | water | ice |
|---|---|---|---|---|
| **0 — the collar and the fill, 0 to ~30 m** | the valley's own glacial fill and the **dead ice** buried in it: stagnant remnant ice the retreat left behind, not the glacier. Meltwater conduits cut through it — round, polished, steep, and *smooth* | none. This band is below the ancients' surface works and above their workings | running, seasonally | **most of it.** Ice walls, ice floor, ice ceiling |
| **1 — the karst, ~30 to ~80 m** | bedrock. Natural cave, opened out and re-cut by meltwater that found the old joints. The shallow band `WHAT-HAPPENED-HERE.md` §6.2 already describes — *"natural karst with a bit of rail in it"* | first marks. Low item numbers, corroded, half-buried in flowstone **and now also in ice** | running, then ponded | plugs, floor ice, rime near the drafts |
| **2 — the workings, ~80 to ~250 m** | the mine. Drives, stopes, the Bus, the Haulage, the pump house. `WHAT-HAPPENED-HERE.md` §6.3 and §6.4 unchanged | all of it | flooded to the tide mark, and rising | none. Below the freezing front, and always was |
| **3 — past the sump, ~250 m+** | `WHAT-HAPPENED-HERE.md` §6.5 unchanged. The deepest Assayer, the underwater scour, clear water | the highest numbers | fully submerged | none |

Depths are **GUESS** and are chosen to be legible rather than surveyed. The ratios matter more than
the numbers: the ice band is thin, the karst is the transition, and most of the cave is the mine.

**Two structural claims, both PROPOSED, and they are what make this a place rather than a layer cake.**

1. **The moulin is the ancients' own shaft.** Meltwater finds the lowest-resistance path down, and
   the lowest-resistance path through a mountain with a mine in it is *the mine*. So the vertical
   conduit the player descends is a shaft the ancients sank, re-bored by water, ice-lined at the
   top and iron-lined further down where the water could not scour the collar rings away. **The
   player goes down the way the water went down, and the water went down the way the ancients went
   down.** That is one object doing three jobs and it is free.

   And the light rule a moulin needs is already written and already the best image the surface
   spike has. `surface/NOTES.md` §2.2 multiplies every collar lining ring's instance colour by
   `1/(1 + (depth/2.2)²)` — *"the inverse-square a rectangular sky hole actually delivers. Three
   metres down it is 35%, at eight metres 7%: the shaft reads as a hole rather than a lit box."*
   That is exactly the falloff a shaft of daylight down a moulin wants, and it is one existing
   line.
2. **The ice is a *fill*, not a *layer*.** The glacier pushed into the openings it found. So band 1
   is not "no ice"; it is ice where the drafts and the drainage put it — an adit half-choked with a
   plug, a stope with a floor of clear ice over a muck pile you can see and cannot reach, a winze
   with an ice bridge over it. That is a placement rule, not a new geometry system, and it is
   exactly the kind of thing `Feature` exists to record.

**And the melt front is a place.** §4's ruling makes it one: somewhere in band 1 or the top of band
2 there is a boundary the water has not crossed yet, and past it the mine is dry, cold and silent,
with a machine standing in it that has not fired in fourteen hundred years. **PROPOSED**, and it is
the strongest single new world object the ice offers.

### 5.3 What it means for `blindside-gen` — the three options, costed

The seam today (`PROCEDURAL-AND-GODOT.md` §1.1, §1.2) is:

```rust
pub fn plan(seed: u64, biome: BiomeId, content: &ContentPack) -> CavePlan;  // ~12 kB, hashed
pub fn rasterise(plan: &CavePlan) -> Cave;                                  // ~1.2 MB, the grid
pub fn dress(plan, cave, chunk, kit) -> ChunkGeometry;                      // client, floats
```

and `rasterise` emits *"per-cell classification + heightfield"*, single-valued in z.

| | what it is | cost | verdict |
|---|---|---|---|
| **A — relief only** | keep one floor per cell; let `floor_mm` vary hard; steep passages and drops become cell attributes. No overhangs, nothing under anything | near zero to the seam | **the fallback.** It delivers "not flat" and fails "things below other things" |
| **B — levels** | `CellPos` gains a `level: u8`. The raster becomes a small sparse stack of heightfields, two to four deep. Within a level, still single-valued; between levels, anything | moderate: one byte in `CellPos`, a third index on every raster consumer, 3D connectivity checks, chunking gains an axis | **recommended** |
| **C — true voxels** | a 3D occupancy grid | at `cell_mm = 600` and 250 m of relief that is ~100 z-slices: 96,000 × 100 cells ≈ 9.6 M × 12 B ≈ **115 MB** raster, and `SensorEnv`'s raycast becomes a 3D DDA. Needs sparse chunking, which is a different architecture | **no** |

**And what the *built* cave costs on top of the seam**, from `spikes/godot/cave/NOTES.md`: the file
that has to be rewritten is `topology.gd`, and it is 428 lines of pure integer code with a
stateless hash RNG. Rules R1 (spine), R2 (floor), R3 (width runs), R9 (crosscuts) and R11
(rasterise) change; the `draw()` hash, the FNV-1a `content_hash()`, R4's `worked` ramp, R6's rock
type, R8's water, R10's 17-flag works bitfield and R12's discoveries survive verbatim. The
expensive half is on the dressing side and it is one specific function: `_half_profile()` builds *a
floor, two legs and a crown*, which a vertical shaft is not. **A moulin needs a second profile
family beside the sweep, not a modification of it.** Everything else there — the 47-mesh kit, the
four shaders, the generated noise volumes, the placement rules — is reusable.

**Option B, in detail.** The reason it is right is that it preserves the two properties the seam
was built for: the raster stays a set of 2D integer arrays (so `DETERMINISM.md`'s rules and the
blake3 golden survive untouched), and `dress` keeps working per-chunk on a plane. What it costs is
that *connectivity* — `ROADMAP.md` Phase 3's *"cellular automata caves, connectivity guarantees"* —
becomes a three-dimensional property, and a one-way link makes it a **directed** graph. A cave that
is connected downward and not upward is a legal cave under §5.1, so the post-condition test has to
be written as two separate assertions: reachable from the shaft, and — separately, and allowed to
fail by design — able to return to it.

### 5.4 The seam, field by field

**PROPOSED.** Additions and changes only; everything not listed is unchanged. Types obey
`PROCEDURAL-AND-GODOT.md` §1.2's discipline: integers and `Fx` only, millimetres in `i32`, angles
as `u8` at a 5.625° quantum, ordered `Vec`s, no maps.

```rust
pub struct CellPos { pub x: u16, pub y: u16, pub level: u8 }   // was (u16, u16)

pub struct CavePlan {
    // ...
    pub extent:    (u16, u16, u8),  // was (u16, u16); the u8 is the level count, 1..=4
    pub datum_mm:  i32,             // the valley floor (§7.2). the ONE zero the town height and the
                                    //   cave depth are both measured from. see §5.4 note 6
    pub pitches:   Vec<Pitch>,      // NEW. the vertical analogue of Passage
    pub melt_mm:   i32,             // NEW. the elevation the melt front has reached. see §4, §5.2
}

pub struct Chamber {
    // ...
    pub level:     u8,
    pub depth_mm:  i32,   // NEW. metres below datum_mm. ADDITIONAL TO depth_band, never replacing it
}

pub struct Passage {
    // ...
    pub level:        u8,        // a passage lies within one level; between levels is a Pitch
    pub floor_mm:     i32,       // NEW at the `from` end
    pub floor_to_mm:  i32,       // NEW at the `to` end. the gradient is the difference
    pub ceiling_mm:   i32,       // NEW. and it fixes the invariant §1.6 asserts and cannot check
    pub medium:       Medium,    // NEW. Rock | Worked | Ice | IceOverRock. see §6
}

pub struct Pitch {               // NEW. a drop, a climb, a shaft, a moulin, a winze
    pub from:       CellPos,
    pub to:         CellPos,
    pub drop_mm:    i32,         // positive is downward
    pub bore_mm:    u32,         // the clear diameter; the width class of a vertical hole
    pub climb:      ClimbClass,  // Walk | Scramble | Pitch | Vertical
    pub kind:       PitchKind,   // Moulin | Winze | Aven | Collar | Stope | Crevasse
    pub medium:     Medium,
    pub water_mm:   i32,         // a pitch can be a waterfall, and that is an acoustic object
}

pub struct Shaft {
    // was { at, team_slot, chamber, daylight } — a point with a boolean
    pub at:        CellPos,
    pub team_slot: u8,
    pub chamber:   u16,
    pub daylight:  bool,
    pub pitch:     u16,          // NEW. index into pitches. a shaft IS a pitch with a collar on it
}

pub struct AncientSite {
    // ...
    pub running:   bool,         // NEW. false = the melt has not reached it. §4.2 item 4
}
```

**Six notes on the shape of that, each of which is a decision rather than a field:**

1. **`depth_mm` is added, never substituted.** `depth_band` has at least seven documented consumers
   (`ART-DIRECTION.md` §7's six cues plus `WHAT-HAPPENED-HERE.md` §3.1's item numbering) and a
   measured gradient behind it. Replacing it breaks all seven for one `i32` of convenience. Keep
   both, and make the generator's post-condition that they **correlate but are not identical** —
   which is true of real mines and is the reason a long horizontal drive at depth still reads as
   deep.
2. **`Pitch` is a first-class record because it is a decision, not a rule.** This is the same test
   `PROCEDURAL-AND-GODOT.md` §1.2 applies to `Feature`: *"Anything that repeats on a rule is not in
   the plan."* A drop is not a rule. It is a place the generator chose, a place the sim must reason
   about, and a place the player will die at. It belongs beside `Passage`.
3. **`climb` goes on the link, `width_class` stays on the cell.** Width is a property of where you
   are standing; pitch is a property of a transition. Keeping them on different objects means
   `width_class_here` (`BELIEF-CATALOGUE.md`, and P3-OQ §25's four classes) is untouched, and the
   new belief signal is a different one: **`pitch_ahead`**, derived from returns, legal, and
   frequently wrong — which is the good kind of new signal.
4. **`medium` is one `u8`-sized enum and it does a lot of work.** It keys the sensor response
   (§6.2), the acoustic cost (§6.3), the footing (§6.4) and the material. It is the *only* new axis
   the ice needs, and putting it on `Passage` and `Pitch` rather than per-cell keeps the raster
   cheap.
5. **`melt_mm` is a single number that makes §4's ruling generative.** Everything above it is
   running; everything below it is dry, silent and older. One `i32` produces the melt-front place,
   the dry Assayer, and a depth at which the world changes character. If the designer rules "it
   never stopped", `melt_mm` and `AncientSite.running` are both deleted and nothing else changes.

6. **`datum_mm` is the valley floor, and that is a decision rather than a convenience.** §7.2
   puts the town at +90 to +520 m and the cave at 0 to −250 m against the same zero, so the game
   has **one vertical axis about eight hundred metres long with the shaft in the middle of it**.
   A player standing on the valley floor can see both ends. It costs one `i32` and it is the
   cheapest structural idea in this document.
**Size.** `CellPos` grows from 4 to 6 bytes (5 padded to 6, or 8 aligned); `Pitch` is 26 bytes and
there will be tens of them. `CavePlan` goes from ~12 kB to a **GUESS** of ~18 kB. The raster goes
from ~1.15 MB to *L* × 1.15 MB for *L* levels: at three levels, ~3.5 MB. Both are fine.
`PROCEDURAL-AND-GODOT.md` §4.2's chunking is the number that actually hurts: chunks become
32 × 32 × 1 per level, and §5.2's *"a 20 m radius touches at most 3 × 3 = 9 chunks of 104"*
becomes 3 × 3 × 3 = 27 in the worst case, which attacks the residency argument in §5 directly.
That is a measurement somebody has to redo, and it is on §2's B12 list.

### 5.5 What it means for depth, the loot table and the extraction loop

- **`DESIGN-PRINCIPLES.md` §2's "the cool things are found by depth" is unchanged and becomes
  literal.** The six-station download ladder (`WHAT-HAPPENED-HERE.md` §4.2) is expressed in
  percentages of a BFS field; it can be expressed in metres instead, or in both, and the bands do
  not move.
- **`WHAT-HAPPENED-HERE.md` §6.7's generator contract G1–G10 all survive**, and two get easier.
  **G10** (*"flooding rises monotonically with depth"*) stops being a tested post-condition and
  becomes a *consequence*: water finds the lowest place. `PROCEDURAL-AND-GODOT.md` §1.6 currently
  proposes generating `water_mm` from `depth_band` with a 1,000-seed post-condition test; under
  elevation it is free, and `ART-DIRECTION.md`'s design problem 3 closes. **G4** (the Assayer
  chamber ≥ 8 m crown) is trivially satisfiable when the generator thinks in elevations.
- **The one new gate.** A chassis that cannot climb cannot extract. That is a real loadout decision
  and it wants a `ClimbClass` on `ChassisSpec` beside the existing `enter_width_class` /
  `turn_width_class` (P3-OQ §25). **PROPOSED, and flagged as scope**: this is a new mechanic, and
  `CLAUDE.md` says do not add features. It is not optional if the cave is vertical — a machine has
  to have *some* answer to a 4 m drop — but the minimum viable answer is two classes, not four.

### 5.6 What it means for the chassis

**PROPOSED**, and deliberately minimal, because `CLAUDE.md` forbids inventing.

| chassis | today | under vertical |
|---|---|---|
| **Scout** | crawl / crawl | the climber. Light, small, high power-to-mass. It is already *"all sensor, no body"* (`ART-DIRECTION.md` §4.6) |
| **Surveyor** | narrow / passage | scrambles, does not climb a pitch. The reference chassis, and the one Phase 5 ships |
| **Hauler** | hall / hall | **walks only.** A loaded Hauler is the machine that cannot come back up, and that is the best thing this axis does for the loadout decision |
| **Swimmer** | narrow / passage | unchanged in class and transformed in meaning. Meltwater is cold, moving and vertical; a bottom-crawler in a flooded winze is a different animal from one in a flooded drive. `ART-DIRECTION.md` §4.6 calls the Swimmer's identity the weakest in the project; the ice hands it a job |

**One thing I am not proposing: rope, winches, or a descent module.** They are all obvious, they
are all features, and none of them is needed to answer the question the vertical axis asks.

---

## 6. Ice as a material and as a hazard

Each property below says **art** or **mechanic**, because the split is the useful part.

### 6.1 The lamp — art

Ice is translucent. A beam entering it scatters within a few centimetres and the surface *glows*
rather than returning a hard pool, so an ice passage under a work lamp is **brighter, softer and
flatter** than a rock one at the same power. Three consequences:

- `ART-DIRECTION.md` §2.2's ratio table (*"near wall at 1.6 m: blown, deliberately"*, *"90 : 1
  across three metres"*) is a rock contract. Ice will not hit 90:1 and should not be forced to,
  and the cave spike's `lumcheck.py` already fails two frames for *not enough black* before any
  ice exists (`05_two_registers` 56.78%, `08_waterline` 68.49% against a ≥ 70% floor).
  **PROPOSED**: the ice band gets its own row, softer falloff, and it is the one place in the cave
  where the darkness relents. That is a legitimate depth cue — the shallow band is the friendly one
  — and it costs nothing.
- Ice is the only material in the game with a defensible subsurface-scattering term, which
  `ART-DIRECTION.md` §9's ice ban was implicitly forbidding. §2.5's amendment permits it.
- **The blue is a path-length effect, not a tint.** Thin ice is neutral; thick ice is blue because
  the light travelled far. Implemented as depth-of-medium rather than as an albedo, it satisfies
  the no-hue-axis rule honestly: the material has one colour and the *distance* is what is doing
  the work. This matters — see §2.6.

### 6.2 The lidar — mechanic, and it is the important one

`THE-SENSOR-AND-SLAM.md` §1 records the only material-specific sensor decision the project has
made, and it is the designer's own:

> *"We decided water returns should just return as a plane."* ... *"Real water is either a mirror
> that returns nothing or a strong specular flash; a clean plane is a game abstraction, and a
> defensible one, because it makes water legible to the machine rather than invisible to it."*

**Ice is the case that sentence abstracts away, and unlike water it is not flat and not at a known
datum.** So it needs its own ruling. **PROPOSED, three properties:**

1. **Ice returns weakly and unreliably.** Near-infrared is strongly absorbed by ice, so most beam
   energy that enters does not come back. A clean ice wall gives **sparse, low-intensity, dropout-
   ridden returns**, not a mirror and not a hole.
2. **Wet ice at grazing incidence returns nothing; at normal incidence it flashes.** So a machine
   walking a polished meltwater conduit sees a bright patch straight ahead and almost nothing at
   the walls — **the returns collapse into a narrow forward cone.**
3. **This needs no new belief signals.** `BELIEF-CATALOGUE.md` already publishes returns per sweep
   and how much of the last sweep came back at all. Ice is legible in belief on day one, through
   signals that were built for other reasons, and a player learns *the map goes thin here* by
   watching it happen.

**And the SLAM consequence is the best mechanic the ice produces.** `THE-SENSOR-AND-SLAM.md` §3.2
already names corridor degeneracy — *"a long, straight, uniform passage gives scan matching nothing
to lock onto along its own axis"* — and calls it *"a direct lever for the cave generator"*. A
**smooth vertical ice shaft is that case squared**: degenerate along its axis *and* rotationally
symmetric, so there is no azimuthal lock either, and ice-polished walls have no `fracture` features
to extract in the first place. The machine going down a moulin **does not know how deep it is, and
cannot know.** Depth uncertainty is the vertical analogue of drift, it falls out of the physics
rather than being imposed, and it is the exact subject of the game arriving as terrain.

**The vertical field of view, and I recommend leaving it broken.** `DESIGN-PRINCIPLES.md` §8's
measured recommendation is *"32 rings over -30 to +12 degrees ... 0.55 to 40 m"*, explicitly marked
as not settled. My arithmetic, and it is mine, not in any document:

- Nadir is never sampled. The steepest downward beam is −30°, so from the lip of a shaft of radius
  *r* the lowest thing it can strike is the opposite wall at *r*/tan30° ≈ 1.73*r*. **A 3 m moulin
  reads as a 5 m pit with a black bottom, whether it is 5 m deep or 50.**
- Upward, +12° reaches the crown of a chamber of height *h* only at standoff *h*/tan12° ≈ 4.7*h*.
  A 10 m crown needs 47 m of standoff against a 40 m range: **tall chambers have no ceiling
  returns.** That directly threatens `PROCEDURAL-AND-GODOT.md` §1.6's chamber-height invariant,
  whose entire purpose was to make the Assayer's mast visible.

Three answers: widen the envelope (costs ring density where the floor and the crown actually are),
add a downward-looking module (a feature), or **make the blind cone the mechanic**. I recommend the
third, without hesitation. A machine that walks into a winze because it physically cannot see down
is not a bug; it is `DESIGN-PRINCIPLES.md` §8's own sentence — *"occlusion is the machine's
ignorance made visible"* — pointed at the floor. And it makes a future sensor that fixes it a real
upgrade with a real reason to exist, which is §8's third bullet exactly.

### 6.3 Sound — mechanic, and it is one row in a table

`THE-MACHINERY.md` §4.2 models the Assayer's coupling with a two-medium Dijkstra: *"0.35 cost per
flooded cell against 1.00 for everything else"*, taken as a ratio against a uniform run to give a
dimensionless **medium factor** per cell.

**PROPOSED: ice is a third cost, and it is between the two.** Sound travels at roughly 3,200 m/s in
ice against ~1,500 in water and ~5,000 in rock, and ice is lossy at high frequency and continuous
at low. A cost of **0.6 GUESS** puts it where it belongs — a better conduit than rock, worse than
water — and it costs one entry. Everything downstream (`coupling_at`, the drawn lethal and felt
contours, the lopsided footprint) works unchanged.

**Two free consequences.** The lopsided field (`THE-MACHINERY.md` §4.2: *"visibly lopsided toward
the water, every cycle, and the shape is the explanation"*) gains a second lobe shape in the
shallow band. And ice under stress **creaks** — a real, loud, irregular, non-machine sound that is
not an ancient system and does not lie. That is an ambient the sound design does not have, it is
the only thing in the world that is loud and *meaningless*, and it is therefore the perfect
counter-training for a player learning `THE-MACHINERY.md` §5's *"the most dangerous object in the
cave is also the only honest one"*.

### 6.4 Footing — mechanic, and it has already failed once

Ice is low-friction. The obvious mechanic is **slip**: commanded displacement exceeds achieved
displacement, and the machine's odometry does not know.

**This idea has already been built and cut once, and the record must travel with it.**
`THE-MACHINERY.md` §11 records the measured A/B in which damage-scaled drift was tested and killed:
*"Player position error at 7:00: 91.13 cells with the effect OFF against 88.38 with it ON ... the
damaged machine ends up less wrong than the healthy one."* The cause was diagnosed precisely:
*"position error is a whole-path quantity and a divergent path launders it completely."*

So the ice version is proposed **with the measurement protocol attached**, and it is a different
protocol: slip is a **direct** quantity — commanded minus achieved, per tick, in the cell the
machine is standing in — and `THE-MACHINERY.md` §11's own replacement metric is exactly that
(*"these are direct quantities, not downstream ones, so a divergent path cannot hide them"*).
Measure slip, not position error. If slip is measurable and the tester cannot see it, it is
correctly invisible; that is the point.

**PROPOSED**: ice cells apply a truth-side slip factor. **GUESS**: 0.7–0.9 of commanded
displacement on wet ice. The machine is never told.

### 6.5 The body — named, not built

Cold drains batteries and stiffens actuators. It is real, it is legible, and modules already cost
power. **I am not proposing it.** `CLAUDE.md` says do not add features, and this one buys a number
on a meter that competes with a meter the game already has (`SelfReport.power`). Recorded so it is
not re-invented; if it is ever wanted, the place it belongs is the descent, not the cave.

### 6.6 Ice as an event — refused, with one exception

A melting plug, a collapsing bridge, a roof that drops: all tempting and all wrong.
`WHAT-HAPPENED-HERE.md`'s whole thesis is that *"the world is one arithmetic, frozen, still
running"* and that **nothing dramatic happened here**, which is the most unsettling thing about it.
An ice hazard that *acts* converts the place into a haunted house.

The exception, and it is the one already argued: **the melt front is a place, not an event.** It
does not move during a match. It has moved, over decades, and it will move, and the player is
standing at the edge of the movement. That is the same tense the rest of the fiction is in.

---

## 7. The surface: a valley under mountains, with a town on the wall

**DECIDED** (§10): *"The player's society is recovering, not declining. They live in a valley in a
somewhat futuristic town, and they are the ones with the advanced machines."* and *"The surface is
snow, and it is beautiful. Monotonous, white, quiet, a valley under a large sky."*

**DECIDED**, extending it the same day: *"the background in the outside can be massive mountains
with some civilization built up in them."*

That extension does four things and only one of them is scenery. It gives the exterior absolute
scale (§7.2); it **rescues the light economy** rather than straining it further (§2.7); it puts the
ice age on the valley wall as a visible line (§7.3); and it makes the whole game read on **one
vertical axis** from the top of the settlement to the bottom of the workings (§7.2).

### 7.1 The thing to build first, because it is the reason to do any of this

Before the town, before the valley, before the terrain: **snow records what walked on it.**

`DESIGN-PRINCIPLES.md` §3 puts teaching on the surface. `DESIGN-PRINCIPLES.md` §7's whole
correction was that *"clear ground is a feature — traffic lanes, turning circles, the apron in
front of a bay and the ground a machine walks are kept clear, and their emptiness reads as use."*
Snow does that automatically and does something the yard could not: **it keeps a record.** A
training course in snow shows the machine's own path, every run, as a physical mark on the ground —
where it hesitated, where it turned, where it went twice, where it went wrong.

That is the single most valuable object the ice decision produces, and it is not an art win, it is
a teaching win. The project's own recorded lesson is to check every stream against *does this make
the player teach the agent sooner?* A course whose floor draws the policy answers **yes**, and
nothing else in this document does. It should be the first thing built on the new surface, ahead of
the valley and ahead of the town.

Cost: a deformation or decal accumulation on the course ground, which the existing arrangement and
material systems can carry. **PROPOSED.**

### 7.2 The valley, in numbers

**DECIDED**, 2026-09-09, extending §10: *"the background in the outside can be massive mountains
with some civilization built up in them."*

Scale is the entire point of mountains and vague scale delivers none of it, so here are numbers.
Every one is a **GUESS**, chosen so the frame reads rather than measured from anything, and they
are offered as a set because they only work together.

| quantity | proposal | why this number |
|---|---|---|
| valley floor, wall toe to wall toe | **1.2 km** | wide enough for a town's infrastructure and a pit-head with real separation between them; narrow enough that **both walls are in almost every frame**, which is what makes it a valley rather than a plain |
| valley length in view before it turns | **6–8 km** | one aerial-perspective ramp, and enough to put the glacier's terminus out of walking reach |
| wall height above the floor, to the ridge | **1,800 m** | the smallest number that reads as *massive* rather than as *hill* |
| the peaks behind, above the floor | **2,600–3,200 m** | they carry the only sunlight (§7.5, §2.7) |
| pit-head to the far wall | **~900 m** | deliberately close. The town has to read as **buildings**, not as texture |
| to the nearest big peak | **4–6 km**; the alpenglow peaks **8–15 km** | aerial perspective needs range to work in |
| **the trimline** | **+310 m** above the floor | the ice's high-water mark. §7.3 |
| **the permanent snowline, today** | **+1,100 m** | above the whole town, well below the peaks, and it has moved up within living memory |
| the glacier's terminus | **~3 km up-valley** of the pit-head | far enough to be scenery, near enough to be the reason the pit-head exists |
| the town | foot **+90 m**, main body **+120 to +380 m**, oldest quarter **+520 m** | §7.3 |
| the cave | **0 to −250 m** below the floor | §5.2 |

**Which gives the game one vertical axis, end to end: +520 m to −250 m, about eight hundred metres
of section, and the shaft is in the middle of it.** The player can see both ends from the valley
floor — the town above and the collar below — and `datum_mm` in §5.4's schema is the number that
ties them together: **the datum is the valley floor.** Depth in the cave is measured from the same
zero the town's height is measured from. That is one field and it makes the whole game legible on
one axis, which is the strongest structural argument for the mountains.

**One correction to the obvious reason for wanting them, because it changes what has to be built.**
A mountain does not make a machine read small. **A chain of known sizes does**, and one enormous
thing at 5 km with nothing between it and the machine reads as a backdrop rather than as scale.
What delivers absolute scale here is the sequence *machine → bay → building → town on the wall →
ridge → peak*, and the load-bearing link in that chain is **the town**, because it is the only
element whose size a viewer already knows. So the mountains are the thing you see and the town is
the thing that does the work, and if only one of them can be built properly it is the town.

### 7.3 The town: terraces above a trimline, and it has been coming downhill for a thousand years

**PROPOSED**, and it is the answer to *where can a town be, in a world coming out of an ice age.*

The constraint does the design. A glacier fills a valley floor from the bottom up, so the floor is
the **last** ground to come free, not the first. Above the ice surface — above the **trimline**,
the line the ice's own upper limit scours across both walls — the rock was cold, windy and exposed,
but it was never buried. **So the society survived the ice on the walls, above the trimline, and it
has been walking downhill ever since.**

Everything follows from that and none of it needs explaining to a player:

- **The town is terraces and galleries cut back into the wall, open to the sky.** Shelves quarried
  into the rock, buildings standing on them, roads switching back between them, everything facing
  out across the valley. **Not tunnelled and not underground** — see the ruling below.
- **It is oldest and highest.** The upper quarter at +520 m is the survival town: small, dense,
  weathered, built for a climate nobody now has to live in. The main body at +120 to +380 m is
  modern and manufactured. The foot at +90 m is new construction, on ground that was under ice.
- **So the town's own stratigraphy runs downward and gets newer** — which is the mine's index
  running downward and getting newer (`ART-DIRECTION.md` §7 cue 5, `WHAT-HAPPENED-HERE.md` §3.1), a
  thousand years apart, in one frame. **Two societies, both working downward, both getting better
  as they went, and the player stands in the second one looking at the first one's shaft.** That
  rhyme is the best thing the mountains buy and it costs nothing but the decision.
- **And the ice age becomes visible without a word.** The trimline is a horizontal line across both
  walls: weathered, lichened, jointed rock above it; scoured, polished, freshly exposed rock below.
  Every real glaciated valley has one and it is unmistakable. **It is one `smoothstep` on world
  height in the wall material** — the same instrument as the mine's own tide mark
  (`ART-DIRECTION.md` §3.5: *"a 0.12 m mineral tide-mark crust above it — one detail that says the
  water moved"*). **The valley has a tide mark and it is three hundred metres high.** It obeys
  `WHAT-HAPPENED-HERE.md` §0 rule 2 absolutely — no prose, no date, no language — and a player who
  never thinks about it still sees that the town straddles a line.

**The ruling on "tunnelled", and it matters more than it looks.** The temptation is a cave city and
it must be refused. `DESIGN-PRINCIPLES.md` §3's structure is *"the surface is safe and lit; the
cave is not. That contrast is the game's structure."* A society that lives *inside* rock puts the
safe place underground and collapses the opposition. **Terraced and open** keeps it exact: home is
*on* the mountain, in the light, under sky; the cave is *in* it, dark, and somebody else's.

**Does living in mountains dilute the strangeness of the descent? No — it sharpens it, and this is
worth arguing rather than asserting.** It removes the cheap version of the fear. These people are
not frightened of rock: they quarry it, they live on it, their machines are built for it — which is
`DESIGN-PRINCIPLES.md` §4's *"advanced robots must be plausible in the frame"* answered by the
culture instead of by the yard. **They still cannot go down there**, and the reason is not that
rock is frightening. It is that this rock is dark, drowned, unmapped, and belongs to somebody who
has been gone since before the ice. The strangeness moves from *underground* to *somebody else's
underground*, which is the strangeness the game actually wanted.

**And it answers "are there people" without a character pipeline.** The vision board's guess 18
records that *"nobody has designed a person for this game and this is not that design."* A town at
900 m does not need one: lit windows, moving vehicles, cable cars, smoke, figures two pixels tall.
**PROPOSED: people are present, at distance, never as characters, never named, never speaking,
never nearer than the far side of a street.**

### 7.4 The surface is three places, and that is what saves the built work

**PROPOSED.** What this section originally proposed as two places becomes three, and the third is
the one that already exists.

| | the town | the valley floor | the pit-head |
|---|---|---|---|
| where | on the wall, +90 to +520 m | 0 m, and 3–5 km of haul road | up-valley, at the retreat margin |
| what it is | the players' society: terraces, workshops, power, warmth, people at a distance | the journey. Snow, the road, the river, walls on both sides | the ancients' own surface works, exposed by the melt, teams camped in them |
| what it is for | the stash (`DESIGN-PRINCIPLES.md` §2), the bench, the player's tally board | the transition, and the only place both ends of the axis are in one frame | the commit: the cage, the course, the collar |
| register (`DESIGN-PRINCIPLES.md` §4) | the future: warm, manufactured, lit | neither. White, empty, enormous | the collision: pale modern kit bolted onto black ancient iron |
| built today? | **no. All new** | **no. All new** | **yes, nearly all of it** |

Everything in `spikes/godot/surface` is a pit-head, and under this proposal **the pit-head is still
a pit-head.** It moves up the valley, its ground material changes, its lighting changes, and its
props stay. `DESIGN-PRINCIPLES.md` §7's arrangement vocabulary — rows, racks, bays, stacks,
lay-down areas, queues, aligned to the site's own grid — is unchanged and is, if anything, *more*
correct in snow, because a swept bay in snow reads as use ten times more strongly than a swept bay
on tarmac.

**What is reusable verbatim**, named so nobody re-does it: `batcher.gd`'s three-bucket MultiMesh
chunking (geometry-agnostic; XZ-plan chunking is still right for a valley floor), `kit.gd`'s 24
unit meshes (a town is still boxes, I-beams, cylinders and chamfered boxes; roofs are additive),
`materials.gd`'s `SOLID_SHADER` and its 23-row material table, `weather.gd`'s sky shader (a winter
sky is a new preset, not a shader edit), the `layout.gd` / dressing seam with its LCG stream
discipline and `plan["hash"]`, `ORDER.md`'s twelve arrangements, and the whole `cinema.gd` /
`lens.gd` / `postfx.gd` / `shoot.gd` capture stack.

**And snow is cheap as a material and expensive as a look, and the split is worth stating exactly.**

*Cheap.* A `"snow"` row in `get_mat()` is one line of ten numbers — no shader edit. The `g_wet`
global-uniform mechanism (declared `global uniform float g_wet`, set through
`RenderingServer.global_shader_parameter_set`, one term per shader) is precisely the pattern a
`g_snow` copies, so snow accumulation as a season lever costs one uniform. And **the slope term
already exists**: `materials.gd:404` has `float flat_ = smoothstep(0.86, 0.985, wnorm.y)` in the
ground shader, and `SOLID_SHADER` line 230 already drives its `dirt` term from
`clamp(wnorm.y, 0.0, 1.0)` — *dust settling on up-facing surfaces*. **Snow on up-facing surfaces is
the dirt term with a different colour and a harder threshold**, and that is genuinely close to
free. The trimline and the snowline are the same instrument once more: two `smoothstep`s on world
height in the wall material.

*Expensive.* Three things, none of them optional. **Snow needs subsurface scattering to read, and
nothing in any of the three material systems has a translucency term.** **Snow's silhouette is the
known open weakness** — `materials/NOTES.md` §7.4: *"A flat plane with a heightfield on it is still
a flat plane. POM gives apparent depth and it works well ... but the silhouette is unchanged, so at
grazing the ground shows a clean straight edge."* Drifts and snow banking against objects are
exactly the case parallax cannot do. And **`g_wet` and a `g_snow` are not independent sliders**:
wet darkens albedo and drops roughness, snow does the opposite, and the two need one combined model
rather than two knobs that fight.

*Also gone:* the puddles (ice, or buried), the weeds in the margins, and the overcast lighting rig.

### 7.5 What the mountains cost, and what they save

**The mountains themselves are the cheapest large thing you can add to this game, and that is not
intuitive.** They are 4–15 km away. At that range they are silhouette, aerial perspective and a
snow line, and nothing else: no material detail, no props, no shadow casting, no collision, and LOD
that never has to be good. The surface build already generates a geometric skirt out to 420 m from
one integer height rule; extending that rule into real landform is the same code with different
numbers. `ART-DIRECTION.md` §3.6's *"spend no art budget past 15 m"* is exactly the right rule to
apply to them, inverted: **spend nothing past 500 m except silhouette and air.**

**The inhabited wall at 900 m is not cheap**, and it is where the money goes. It is mid-distance:
close enough that buildings need edges, roofs, glazing and a believable street logic, far enough
that none of it can be instanced from the yard kit at yard density. That is a new generator —
`dressing.gd`'s ruined masonry is pier-based and its opening and lintel machinery ports, but
pitched roofs, glazing and terracing do not exist. **Budget the town, not the mountains.**

**And they save something real: the horizon problem gets smaller rather than bigger.** A valley
floor is walled. The *view* is enormous and the *drawn extent* is bounded by two ridges at 900 m
and a head wall at 6 km, which is a far more tractable scene than an open snowfield with a true
horizon in every direction. **The valley is a room.** A large, cold, quiet room, and rooms are what
this project already knows how to build. That is a straight reduction of the cost I put on B2
before the mountains existed.

**The one measured risk.** `surface/PHOTOREAL.md`'s clean-machine re-measurement puts the built
pit-head at **13.72 ms mean and 18.06 ms worst in overcast — a 40 fps worst case, not a 60 fps
one** — with SSAO alone costing 4.2 ms of it. There is no headroom to spend on a town and a
mountain range, so the mountains have to be free by construction (they are) and the town has to buy
its own budget back (it does not yet). That is the number to hold any estimate against.

### 7.6 Two design questions left, and one I am answering

1. **Is the town shared with rivals?** The surface vision board's guess 3 is *"one pit-head per
   team ... rivals are never seen above ground"*, and its own design problem 4 says that leaves the
   surface with no social read. A town resolves it the way extraction games do: **the town is
   shared, the yards are not.** You see rivals in the town and never in the raid. **PROPOSED
   default: yes, shared town, private pit-heads.**
2. **Is anything at stake up there?** Still not settled by the designer (`DESIGN-PRINCIPLES.md` §3:
   *"whether anything is at stake up there"*). **The ice does not change this and I am not
   proposing an answer.** It does change the framing: §3's *"the surface is safe and lit"* now
   means safe and *cold*, and a valley at the foot of a retreating glacier is beautiful and
   provisional at once. That is a better tone for a stash than a wet yard, and it costs nothing.

**And the one I am answering rather than asking: does the player ever go up there?** Three options —
the town is pure background; the town is fully explorable; or the player occupies a small authored
part of it. **PROPOSED: the third.** One yard, one workshop, one wall with the tally board on it,
one street outside it, and everything else is view. It gives the stash a place to be, it satisfies
`DESIGN-PRINCIPLES.md` §4 in close-up rather than at 900 m, and it does not commission a
settlement. `CLAUDE.md` forbids adding features, and an explorable town is a feature.

### 7.7 Where teaching happens

Unchanged in substance (`DESIGN-PRINCIPLES.md` §3), relocated in place.

- **The course stays at the pit-head**, on the flat by the collar, now in snow (§7.1). It is
  outdoor, cold, and it is the last thing before the descent.
- **The bench and the tally board move to the town.** `WHAT-HAPPENED-HERE.md` §3.4 hangs the tally
  board in the roofless winding house at the pit-head, and §6.1 puts the bench beside it: *"things
  come up the shaft and get read on the surface."* Under a three-place surface that gesture is
  stronger, not weaker — things come up the shaft, and then they come **down the valley and up the
  wall** to be read where it is warm. **PROPOSED**: the winding house keeps the *ancients'* tally
  board, empty and cast; the *player's* board is the one in town, and the two are the same object a
  thousand years apart. That is one of the cheapest and best beats available.
- The vision board's design problem 3 — *"an open-topped daylight course cannot teach darkness"* —
  is unchanged and still open.

### 7.8 The three descents

The trip is now **town → down the wall → along the valley → down the shaft**, and each leg is
colder, emptier and darker than the one before it.

| leg | how | register |
|---|---|---|
| the town to the floor | an inclined railway down the terraces. A society on a wall needs one, and it is the players' technological register made obvious | warm → cold. You leave the last building |
| the floor to the pit-head | 3–5 km of haul road up the valley, walls on both sides, the glacier ahead | cold → empty. The only leg where the whole vertical axis is in one frame |
| the collar to the dark | the cage, about twenty seconds | empty → black |

`TRAILER.md` §1's reversal — *"you spend the first act being shown a machine you are preparing and
teaching, in daylight, with your hands on it. Then it goes down the shaft and you never touch it
again"* — now has two middles, and the picture runs warm → white → black across them.

`GLOSSARY.md`'s **Commit** — *"the moment control leaves the player, roughly 20 seconds after
descent"* — is unchanged and should stay unchanged. **The commit is the cable coming out of the
charge port at the collar** (surface board guess 11), not the town gate and not the road.

## 8. What the trailer becomes

`TRAILER.md`'s treatment is not rewritten. Five changes, and four of them are improvements the
existing structure was already reaching for.

1. **Shot 2 changes and it changes the whole opening.** Today: *"the headframe against an overcast
   sky, slow push in from low."* Under snow and mountains: **the valley at first light — the peaks
   lit and the floor still in shadow, walls on both sides, the town a line of small warm windows on
   the far wall at 900 m, and everything else white and silent.** That is §10's *"monotonous and
   snowy and pretty"* in a single frame; it establishes the society before it establishes the
   machine; and it is the one shot in the trailer that can carry absolute scale, because the town
   is in it and a town is a size a viewer already knows (§7.2). The headframe survives and becomes
   the *transition* out of the valley, where it now reads as old **against** something new — which
   is `DESIGN-PRINCIPLES.md` §4's two-register collision in one cut.

   And it puts the setting on screen without a card: the town straddles the trimline, so shot 2
   contains the ice age (§7.3) and nobody will consciously notice.
2. **Shot 4 keeps its job and changes its material.** Today: *"rain on hardstanding, macro,
   standing water rippling."* Becomes **meltwater running off ice, macro.** This preserves
   `WHAT-HAPPENED-HERE.md` §7 beat 5 exactly — *"the trailer opens on water dripping in black and
   on rain on hardstanding, and ends on rain and an empty shaft ... the first and last images of
   the trailer are both water"* — and sharpens it, because the first water is water **coming out of
   ice** and the last is water going down a hole. The machine that never stopped runs on the melt,
   and no viewer gets that on a first watch. That is the beat working better than it did.
3. **The reversal at 0:50 gains a third register, free.** `TRAILER.md` §5 already cuts the score at
   the shaft and calls the score *"the sound of having control"*. Now the picture goes **warm →
   white → black** across Acts I–IV, which maps onto the existing three-stage sound plan with
   nothing added. Act I is the town (warm, interior, score), Act II–III is the works and the
   descent (white, cold, score narrowing), Act IV is the cave (black, no score).
4. **Shot 14, the descent, is better.** *"Daylight climbing away up the shaft, the 12000 K disc
   shrinking"* becomes a disc of snow-light — brighter, harder-edged and colder against black than
   overcast is. The image was always the best in Act III; snow raises its contrast.
5. **Shot 28, the last shot, gets one addition and it is cruel.** *"The extraction window. The
   shaft, empty, from the surface, in the rain. Nothing comes up."* Rain becomes melt, running into
   the collar — so the last image of the trailer is the thing that woke the machine up, going back
   down to it. **And home is in the frame:** the town lit on the wall behind, 900 m away and 300 m
   up, warm, occupied, and not where the machine is. An empty shaft is a fact; an empty shaft with
   somewhere to have come back to is a loss. It costs nothing — it is a camera angle.

**And one thing the trailer must still not do.** `WHAT-HAPPENED-HERE.md` §7 forbids showing a
second Assayer, two comparable index marks, the boundary post, the tally board or the empty
footing. Add to that list: **never show a stopped, dry Assayer**, because that is §4's ruling given
away in one frame and it is worth a hundred hours.

`TRAILER.md` §11.1's fix — follow **one** machine from its first frame — is unaffected and remains
the most important change to the treatment.

---

## 9. Questions for the designer

Yes/no, with a recommended default each, ordered by how much they block. You decide; I propose.

| # | question | default |
|---|---|---|
| **1** | **Did the machinery stop and restart?** It froze when the ice came, stood in still water for the duration, and resumed when meltwater reached it. This is §10's own proposed beat. Saying yes changes eight sentences across five files (§4.4) and buys the gap in the summary sheet, the dry Assayer, and a material timeline that survives. | **yes** |
| **2** | **Is the cave a small stack of levels (2–4) rather than a heightfield or a voxel grid?** Option B in §5.3. It is the only one of the three that delivers "things below other things" without rebuilding the seam's determinism story. | **yes** |
| **3** | **Is the surface three places — a shared town terraced into the valley wall, the valley floor and its haul road, and a private pit-head at the retreat margin?** §7.4. This is what saves the built surface work: the pit-head stays a pit-head and moves up the valley. | **yes** |
| **4** | **Is the town terraced and open to the sky rather than tunnelled into the rock?** §7.3. Tunnelling puts the safe place underground and collapses `DESIGN-PRINCIPLES.md` §3's whole contrast. Terracing also explains where a society survives an ice age: above the trimline, walking downhill ever since. | **yes, terraced** |
| **5** | **Are §7.2's valley numbers right in order of magnitude?** 1.2 km floor, 1,800 m walls, peaks at 2,600–3,200 m, the far wall at 900 m, trimline at +310 m, town +90 to +520 m, snowline at +1,100 m. Every one is a guess; **the ratios are the decision, not the values**, and vague scale delivers no scale at all. | **yes** |
| **6** | **Is `ART-DIRECTION.md` §2.1 given a fifth row (the sky, 12000 K, lighting a shadowed valley floor) and a sixth (alpenglow on the peaks) rather than being amended?** §2.7. This is the ruling `surface/PHOTOREAL.md` §3.4 asked for and made provisionally; the mountains answer it in §2.1's favour. | **yes** |
| **7** | **Is `ART-DIRECTION.md` §9's "no ice" amended to "ice is a material and a place, never a biome and never a hue axis"?** The rule's intent — stop the season system becoming a palette swap — is preserved verbatim. §2.5 has the replacement text. | **yes** |
| **8** | **Is there ice inside the cave, or only snow outside it?** §5.2 puts ice in the shallow band and as plugs and fills in the karst, and none in the workings. Saying no makes the cave a purely rock cave under a snowy surface, deletes §6 entirely, and costs about a week of the estimate. | **yes, ice in the shallow band only** |
| **9** | **Is `datum_mm` the valley floor, so the town's height and the cave's depth are measured from one zero?** §5.4 note 6, §7.2. It makes the game one continuous vertical axis about 800 m long with the shaft in the middle of it, and it costs one `i32`. | **yes** |
| **10** | **Does depth become literal metres *alongside* the existing BFS band, rather than replacing it?** §5.4 note 1. Replacing it breaks seven documented consumers for one field's convenience. | **yes** |
| **11** | **May a machine go somewhere it cannot come back from — a one-way drop — and may a wreck fall somewhere nothing can reach?** §5.1. This is the commitment axis the vertical cave adds to the extraction loop, and it is the biggest gameplay consequence of the whole decision. | **yes** |
| **12** | **Is the timeline ~1,400 years since the ancients, ~1,150 of it ice, the melt past the pit-head ~70 years ago?** §3. The load-bearing part is that the ice arrived **within a century or two** of the wind-down. | **yes** |
| **13** | **Do the three lines on the valley wall — trimline, town, snowline — carry the timeline, with no date and no text anywhere?** §3. And does the snowline stay fixed until a deliberate published world event, rather than drifting on its own? | **yes to both** |
| **14** | **Does the lidar keep its −30°/+12° envelope, so that the downward blind cone is a mechanic rather than a bug?** §6.2. A machine that cannot see the hole it is about to walk into is this game's subject pointed at the floor. Saying no means widening the envelope or adding a module. | **yes, keep it** |
| **15** | **Is ice a sensor material — sparse, low-intensity, dropout-prone, specular at normal incidence — rather than a plane like water?** §6.2. This is the ruling `THE-SENSOR-AND-SLAM.md` §1 explicitly did not make. | **yes** |
| **16** | **Does ice inject truth-side slip that the machine cannot observe?** §6.4. Flagged because a structurally similar mechanic was measured and cut in Phase 1; this one is proposed with a different, direct measurement protocol attached. | **yes, and measure it before shipping it** |
| **17** | **Is the gap in the deepest Assayer's summary sheet the ice age?** §0, §4.2 item 3. Costs nothing, requires question 1 to be yes, and is the only artefact in the world that measures the ice without a word of language. | **yes** |
| **18** | **Is the melt front a place in the cave — a depth past which the mine is dry, silent, and holds a machine that has not fired since before the ice?** §5.2. One `i32` in the plan (`melt_mm`) and one `bool` on `AncientSite`. | **yes** |
| **19** | **Is the town shared between rivals, while the pit-heads are not?** §7.6. Overturns the surface vision board's guess 3 and fixes its design problem 4. | **yes** |
| **20** | **Does the player occupy a small authored part of the town — one yard, one workshop, one wall, one street — with the rest of it and all the mountains as view?** §7.6. An explorable settlement is a feature and `CLAUDE.md` forbids features. | **yes** |
| **21** | **Are people visible in the town — at distance, never as characters, never named, never speaking?** §7.3. Answering yes commits to lit windows, vehicles and two-pixel figures, and to nothing else. | **yes** |
| **22** | **Is the pit-head 3–5 km up the valley from the town's foot, reached by a haul road, with an inclined railway from the town down to the valley floor?** §7.8. Three descents rather than one, and each is colder than the last. | **yes** |
| **23** | **Does the surface get its own exposure band in the CI contract, leaving the lamp-frame targets untouched?** §2.7. Without it, either the peaks fail the build or the cave stops being enforced. | **yes** |
| **24** | **Does the trailer open on the valley rather than the headframe, and does the last shot put the lit town on the wall behind the empty shaft?** §8. | **yes to both** |

---

## 10. Everything I guessed

Per `CLAUDE.md`. Every item is mine, and none of it is in any existing document.

1. **That the ice did not kill the ancients — the margin did, and the ice arrived a century or two
   later, to people with nothing to do with this mine.** (§1.1.) This is the guess that keeps *a
   works, not a temple* alive, and it is the load-bearing guess of the whole reconciliation.
2. Every number in §3's timeline table: 1,400 / 1,300 / 1,150 / 70 / 40 / 50 years. Nothing
   measured them. They are chosen so that cast iron survives and a civilisation does not.
3. That the deep workings stayed **liquid** through the ice — flooded, pressurised, anoxic, 1–4 °C
   — and that this is both why the machine stopped and why it is intact. (§4.2 item 1.)
4. That the player's society knows there was a pre-ice industry and knows nothing else, and that
   the town exists because somebody sent a machine down and it came back. (§3.)
5. The three-regime cave: dead ice, karst, workings, and the depth ranges 30 / 80 / 250 m. (§5.2.)
6. **That the moulin is the ancients' own shaft, re-bored by water.** (§5.2.)
7. That the ice is a *fill* rather than a *layer* — plugs, floor ice, bridges over winzes. (§5.2.)
8. That the melt front is a place, that `melt_mm` and `AncientSite.running` express it, and that
   there is a dry Assayer standing past it. (§4.2 item 4, §5.2, §5.4.)
9. The entire schema in §5.4: `CellPos.level`, `datum_mm`, `Pitch` as a first-class record,
   `ClimbClass`, `PitchKind`, `Medium`, `depth_mm`, and every field on `Passage` I added.
10. That two to four levels is the right number, and the ~18 kB plan / 3.5 MB raster sizes.
11. That `climb` belongs on the link and `width_class` stays on the cell, and that `pitch_ahead`
    is the new belief signal rather than a new width class. (§5.4 note 3.)
12. The chassis climb assignment in §5.6, and specifically that a loaded Hauler cannot come back up.
13. **That ice returns weakly rather than as a plane or as a hole**, and the three sensor
    properties in §6.2. `THE-SENSOR-AND-SLAM.md` §1 decided water and explicitly decided nothing
    else.
14. The azimuthal-degeneracy claim — that a smooth cylindrical shaft defeats scan matching in *two*
    axes rather than one. `THE-SENSOR-AND-SLAM.md` §3.2 names only the axial case.
15. All of §6.2's field-of-view arithmetic: 1.73*r*, 4.7*h*, the 3 m moulin reading as a 5 m pit.
    Derived by me from `DESIGN-PRINCIPLES.md` §8's recommended envelope, which is itself unsettled.
16. The **0.6** ice cost in the Assayer's medium-factor Dijkstra. (§6.3.)
17. That ice creaks, that the creak is loud and meaningless, and that this is useful. (§6.3.)
18. The **0.7–0.9** slip factor on wet ice. (§6.4.)
19. That snow records the machine's path on the training course, and that this is the highest-value
    item in the whole decision. (§7.1.)
20. The three-place surface, the town / valley floor / pit-head division of labour, and
    everything in §7.4's table.
21. That people are visible in the town at distance and never as characters. (§7.3.)
22. **That the player's tally board in town and the ancients' cast tally board in the winding house
    are the same object a thousand years apart.** (§7.7.)
23. Every exposure number in §2.7's proposed daylight band.
24. The three-rule resolution of the snow-versus-cyan problem in §2.6, including that the snow's
    diffuse term is achromatic and the blue lives only in shadow and in path length.
25. Every cost figure in §2's ranking table. They are orders of magnitude, not estimates, and the
    "weeks" entries are the ones most likely to be wrong.

**Added with the mountains, 2026-09-09:**

26. **Every number in §7.2's valley table**: 1.2 km floor, 6–8 km of view, 1,800 m walls,
    2,600–3,200 m peaks, 900 m to the far wall, 4–15 km to the peaks, trimline +310 m, snowline
    +1,100 m, town +90/+380/+520 m, terminus 3 km up-valley. None of it is measured; all of it is
    chosen so the frame reads.
27. **That the society survived the ice above the trimline on the valley walls, and has been
    building downhill ever since.** (§7.3.) This is the guess that makes the town's position a
    consequence rather than a choice, and it is the second-most load-bearing guess in the document
    after item 1.
28. **That the town's own stratigraphy runs downward and gets newer, rhyming with the mine's
    index.** (§7.3.) Mine, and the thing I am most pleased with in this revision.
29. **That the trimline and the snowline are visible lines on the wall, that they carry the whole
    timeline, and that both are one `smoothstep` on world height.** (§3, §7.3.)
30. **That the valley floor is in shadow for most of the day and is therefore lit by ~12000 K
    skylight at roughly a tenth of full sun**, and all the arithmetic in §2.6 and §2.7 that follows
    from it — including the thirty-to-sixty-to-one in-frame dynamic range and the claim that
    shadowed snow is no brighter than the built yard's concrete. My arithmetic, not measured, and
    it is the load-bearing calculation behind B6 inverting.
31. **That scale comes from the chain and not from the mountain**, and therefore that the town is
    the element to build properly. (§7.2.)
32. **That the mountains are nearly free to render and the inhabited wall is not.** (§7.5.) Stated
    from the surface spike's own numbers, but not measured on anything that exists.
33. **The inclined railway from the town to the valley floor**, and the 3–5 km haul road. (§7.8.)
34. That alpenglow is the only warm light in the exterior and that the player can never reach it.
    (§2.7.)

---

## 11. What I did not do, and what should happen next

- **I changed no other file.** Every amendment in §2 and §4.4 is written out here and applied
  nowhere. Nothing is committed.
- **I did not read `spikes/godot/` as an author.** Another agent is working there. The cost
  estimates for B2 and B3 are read from `docs/`, from the surface and cave vision boards, and from
  `PROCEDURAL-AND-GODOT.md`, and they should be checked by whoever owns those projects before
  anybody plans against them.
- **The order I would do it in**, if questions 1, 2 and 5 come back yes:
  1. Answer question 1 and apply §4.4's eight sentence edits. Hours, and it unblocks §3.
  2. Amend `ART-DIRECTION.md` §9 (§2.5) and §2.1/§2.9 (§2.7), and settle the two rulings §2.10
     names as already open and now forced: the rock albedo, and `PROCEDURAL-AND-GODOT.md` Q5. A
     day between them, and they unblock every surface frame and every ice material.
  3. Build §7.1 — the course, in snow, recording tracks. It is the only item here that makes the
     player teach the agent sooner, and it does not need the valley, the town, or the vertical cave.
  3b. Then the three lines on the wall (§3, §7.3) — trimline, town, snowline. Two `smoothstep`s and
      a silhouette, and between them they put the entire setting on screen with no text.
  4. Everything else, in `ROADMAP.md`'s own order, behind Phase 2's gate.

**And the standing warning.** `CLAUDE.md` orders phases by how much damage a wrong answer does.
Phase 2's gate has not been met, and none of §5, §6 or §7 is Phase 2 work. This document exists so
that the setting decision is written down before it is built against — not so that it gets built
now.
