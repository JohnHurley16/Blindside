# Phase 1 — the spectator display, second design

Written 2026-09-07, after the gate playtest failed on 2026-09-06.

**This is a proposal, not a build that has started.** It has one prerequisite that is not mine
to satisfy: it contradicts the phase spec, and the phase spec wins. See §0 before anything
else.

---

## 0. The prerequisite: an amendment to `PHASE-1-SPECTATOR-TEST.md`

`docs/PHASE-1-SPECTATOR-TEST.md`, *Display*, says:

> The player sees **belief only**. Ground truth is never rendered during the run.

Every word of this document breaks that sentence. `CLAUDE.md` says the phase spec wins where
it disagrees with `DESIGN.html`, so the sentence stands until the designer changes it.
`DESIGN.html` is evidence but not authority — it treats this as an open question:

> Ground truth appears in exactly two places: the post-match replay … and the spectator view.
> (line 234)
>
> Whether live spectators see ground truth or only belief. Truth makes matches far more
> watchable — the audience knows the trap is there and the operator doesn't. Belief-only is
> more honest and more tense. **I lean truth for spectators, belief for players.** (line 238)

The reading that makes both documents true: the build shipped the **operator** view and ran
the **spectator** gate on it. The spec's Display section describes what a player sees. The
gate asks a stranger to watch a match she is not playing.

The amendment I am asking for, to replace that sentence:

> The **operator** view — what a player sees while playing — is belief only, and ground truth
> is never rendered in it. The **spectator** view draws truth beside belief, because the gate
> asks a stranger to follow a match she is not playing. Both are built from the same belief
> panel; the spectator view adds a second panel and a truth-derived readout, both bound to
> `T` and both dark in the operator build. The gate is run twice: truth on, then truth off.

If the answer is no, stop here. Nothing below is worth building against a spec that says not
to.

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

---

## 2. The design in one paragraph

The screen becomes two pictures of the same cave at the same scale in the same frame: on the
left the cave as it is, with both machines in it, drawn in warm light on filled stone; on the
right the map the player's machine has built, drawn cool and sparse on black, exactly as today
but repaired. Inside the left picture the machine is drawn twice — solid where it really is,
hollow where it believes it is — joined by a line with a number on it, so the gap between
world and belief is one mark rather than a comparison the viewer has to hold in her head.
Under the two pictures, two numbers of the same size under near-identical labels: `IT IS WRONG
BY 34` and `IT THINKS IT IS WRONG BY 1`, which is the whole thesis of the game delivered in
four words and two integers with no vocabulary to learn. The cave has named rooms, so it is a
place instead of a shape; the rival is drawn for the first time in this project, so
twenty-two beeps acquire an author; and the machinery's kill cycle is drawn as a clock that
counts down in front of a machine that cannot hear it, six times a match, which is the
suspense the middle of the match currently lacks. It is legible because it takes things away
as well as adding them — one meaning per colour, four type sizes with a nine-point floor,
three levels of visual weight and a rule that keeps them apart — and because a stranger is
told the rules in twenty-two words before the clock starts.

---

## 3. The layout

Default canvas **1600 × 900** (up from 1400 × 900). Reasons at the end of this section. All
bands are full width; heights are fixed pixels re-laid on resize, exactly as `_layout()`
already does.

```
x=0        16                    792 808                          1584   1600
+--------------------------------------------------------------------------+ y=0
| BLINDSIDE  nobody is driving it   CARGO |#|_|   5:34/8:00   BACK BY 8:00  |  52  HEADER
+---------------------------------+---+----------------------------------+ y=52
| THE CAVE                        |   | ITS MAP                          |  26  TITLES
| what is actually there          |   | what it thinks is there          |
+---------------------------------+   +----------------------------------+ y=78
|                                 |   |                                  |
|   rock, floor, water, filled    | r |      . : .        .              |
|   THE BIG HALL     DEPOSIT A    | u |    . : : .    . : .              |
|        O=========o  34 cells    | l |         (o)  <>                  | 500  MAPS
|     solid=real   hollow=belief  | e |    silhouette + point cloud      |
|   (O) MACHINERY  lethal in 0:07 |   |    (o) where it thinks the       |
|    ^  RIVAL                     |   |         machinery is             |
|                                 |   |                                  |
+---------------------------------+   +----------------------------------+ y=578
| the beacon it is about to trust |   | "I am at the junction.           |  36  CAPTIONS
| is thirty-three cells from where|   |  I am sure to within one cell."  |
| it left it                      |   |                                  |
+--------------+------------------+---+--------------+-------------------+ y=614
| IT IS DOING  | IT IS WRONG BY   | IT THINKS IT IS  | YOUR ONE COMMAND  |
| DRIVING TO   |                  | WRONG BY         |                   | 106  READOUT
| DEPOSIT B    |       34         |        1         | RECALL - READY    |
| ####___  42  |      cells       |      cell        |    press R        |
+--------------------------------------------------------------------------+ y=720
| machinery  #        #        #        #        #        #                |  30
| 100|                       ______________________  how wrong it is       |  66
|    |       _________________                                             |
|   0|_______________________\____________________  what it thinks         |  34
| events   . .  |  .. .  | . .  |  . . . . .  | . .     |   .               |
| 5:34 / 8:00        2:26 left        | A BEACON MOVED                      |  50
+--------------------------------------------------------------------------+ y=900
```

```python
HEADER_H   =  52.0
TITLE_H    =  26.0
MAP_H      = 500.0
CAPTION_H  =  36.0
READOUT_H  = 106.0
TIMELINE_H = 180.0
MARGIN     =  16.0
GUTTER     =  16.0                              # a 1 px rule, not a third column
PANEL_W    = (w - 2 * MARGIN - GUTTER) / 2      # 776 at 1600
```

**What each region is for.**

| region | job |
|---|---|
| **Header** | The premise and the two clocks. `nobody is driving it` sits there for eight minutes because it is the one fact a stranger keeps forgetting. `CARGO` is the objective as a picture, not a number. |
| **Truth panel** | The place, and only what belief is currently wrong about. It is a stage, not a debug dump: no rival belief, no sound-field interior, no sigma, no policy, no log. |
| **Belief panel** | Unchanged in content, repaired in encoding. Every existing visual survives: cloud, trail, beacons, known places, ellipse, agent, heading, intent, believed hazard and rival, contact wedges, signature wedge, wavefronts, incoming arcs, fix flash. |
| **Captions** | One line each, opposite points of view. Left is third person about the world and is allowed to be ironic. Right is first person, as the machine. This is where "why is it doing that" is answered — in the machine's own voice, at 15 pt. |
| **Readout** | Four blocks. The two middle ones are the design's thesis. Block 2 is truth-derived and goes dark with the truth panel. |
| **Timeline** | Four rails: the six machinery windows drawn from frame one so the next kill is visibly sliding toward the playhead; the two error traces; the event pips; the clock and the one now-line. |

**Camera.** Both panels get `TurntableCamera(elevation=90, azimuth=0, fov=0, up="z")`,
`center=(100, 60, 0)`, matched `scale_factor`, and `belief_cam.link(truth_cam)` so a drag
moves both. Orbit and zoom still work, so the spec's "orbitable" is satisfied — the *default*
is simply no longer tilted.

The current camera is `elevation=58, fov=0`: an **orthographic** projection tilted 32° off
vertical. It pays every cost of 3D — foreshortening, an unrecognisable cave outline, a camera
a viewer can knock askew — and buys one benefit, a 2.2-cell z-scatter on wall points, which at
4 px/cell is nine pixels of fuzz. Going flat is a move toward what the tester asked for, not
away from it: she asked to be able to tell what she was looking at.

**Scale.** The camera fits x ∈ 4..196, y ∈ 4..116, so `PANEL_W / 192 = 4.04 px per cell`. At
that scale the numbers that have to read do read: the 34-cell tether is **136 px**, a third of
the way across a panel; the machinery's 9-cell lethal radius is a **72 px** disc; the 12-cell
deposit radius is **96 px**; the two machines passing at 0.41 cells overlap by about two
pixels, which is what "they touched" should look like.

**Why side by side and not stacked.** The designer asked for side by side, and the arithmetic
agrees within a rounding error. Stacked in a 16:9 window gives about 4.0 px/cell in the truth
pane but forces the two panes to different heights and therefore different framing, which
destroys the one thing the design depends on: that a cell is at the same pixel offset within
each panel, so a displacement between the panels is a real displacement.

**Why 1600 × 900 and not 1920 × 1080.** Recorder framebuffer readback is per-pixel and
dominates the record path: measured 39.5 ms at 1400 × 900 and 43.1 ms at 1600 × 900. An
eight-minute render goes from about 38 minutes to about 42; at 1920 × 1080 it is about 53.
1600 is the smallest width at which two panels and a 9 pt type floor both fit.

**What leaves the screen, and why.**

- **The decision graph** (10 boxes, 5 bars, ~30 strings, 292 × 600 px = 19 % of the current
  screen) moves behind the `D` key, off by default. In the measured match its text was
  unchanged for 36 seconds at a stretch and only four of its strings ever change; a
  non-engineer reads *"am I getting lost? no · 3 of 16 cells adrift"* as noise. The designer's
  brief asks to "know why its doing what its doing", and that is now answered by the belief
  caption in the machine's own voice at 15 pt, beside a truth panel showing what the reasoning
  is about to hit — which is a better answer than ten boxes, not a smaller one.
  `decision_graph.py` and `node_box.py` are **not deleted**: they hold the two hardest-won
  vispy workarounds in this repo, they are one keystroke away for the designer's own use, and
  they are the specification for BLD-152. Reverting this is one line.
- **The map key** is cut from seven rows to five, moved out of the map viewbox (it currently
  floats *inside* it, at `PANEL_W + 24`), set at 9 pt, and faded to 40 % after 1:00. A key is a
  confession that the encoding failed, but a stranger with no background needs one for the
  first minute and does not need it after.
- **The status panel** goes from five rows to three, at the same sizes minus the overprint bug:
  `ROW_HEIGHT = 30` with a 10.5 pt bold value at `row_y + 14` and the next 7.5 pt label at
  `row_y + 30` means the value strikes through the label below it, which is visible in the
  current renders. `ROW_HEIGHT` becomes 38 and the value moves to `row_y + 16`.

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
both; it always could. See §7 — this needs no `tuning.py` change and moves no event.

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
truth panel does not open that hole; it closes it, in the same commit.

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
fields so the truth panel could draw wavefronts that pour down passages and turn corners. That
would have widened the audited module and created a second unscanned door out of truth — and
`belief/belief.py` already imports `sensing.returns`, so nothing in rules 1–8 would have caught
it. Sound origins are drawn instead as plain expanding circles from the true origin, which the
exporter already has from `World.events`. If passage-following wavefronts are wanted later, the
exporter builds its own `SoundField` inside `stage_builder.py`, and it is slice 8.

---

## 5. Beat by beat

Seed 7, sonar, Recall not sent — the exact match the tester watched. Distances and times below
are measured from the headless run and from a Dijkstra over `WALKABLE`, not estimated.

The machinery's cycle is fixed: `phase(t) = (t + 30) mod 75`, lethal for the last 4 s, with a
signature over the 9 s before that. So the **six lethal windows are 0:41, 1:56, 3:11, 4:26,
5:41 and 6:56**, and the warnings begin at 0:32, 1:47, 3:02, 4:17, 5:32 and 6:47. That
seventy-five-second heartbeat is already in the sim, it is perfectly regular, and it has never
been drawn.

| t | true | believed | truth panel | belief panel | feeling |
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
| **3:02–3:11** | Window 3 | A magenta wedge blinks for under a second, then a magenta ring settles **40 cells from where the machinery actually is** | Countdown 9…8…7, then flood. Player 55 cells away | The believed-machinery ring, in the wrong place | **Two magenta rings, one right and one wrong, at the same moment on two panels.** The display's whole argument in one frame. |
| **3:43–4:03.9** | Four small fixes, all from the spoofed beacon | "corrected" ×4 | The *red* beacon answering each time; the tether refusing to shorten | Small yellow flashes | *It is being held wrong.* |
| **4:04–5:30** | **THE DROUGHT. No fix will ever occur again — 236 seconds. Error 34 → 64 cells.** The rival walks to the machinery. Windows 4 (4:26) and window 5's warning (5:32) | σ stays under 4 for most of it | The tether lengthens continuously across a third of the panel; a `LAST CORRECTION 1:26 AGO` row counts up and turns amber past 60 s; the rival's comet runs to the machinery and **stops inside the ring at 5:13 to download**, surviving one window | The warm error trace climbs a long ramp while the cool trace stays flat | **The second stretch of dead air, fixed by making the absence itself the subject.** "Nothing has corrected it for two minutes" is more frightening to watch than another yellow flash. |
| **5:32–5:45** | **THE NEAR MISS. Window 5's warning begins; the machine walks at the ring — 11.5, 10.7, 9.8 cells — and jams at exactly 9.038 against a 9.000 lethal radius. The disc is lethal for four seconds with the machine touching it. Margin +0.038 cells; the rival is at 10.008.** | "I am near deposit A." It is 65 cells from deposit A. | The countdown hand sweeps; the ring thickens through the nine-second warning; it goes solid and pulses for four seconds with the machine standing on its edge | Nothing at all. The caption does not change. | **The best fourteen seconds in the match, currently invisible to the tester, to the designer and to us until a script went looking for it.** |
| **5:45.8** | It steps inside. **0.8 seconds too late to die.** | "near deposit A" | Green machine inside a red ring, the countdown restarting at 75 | — | *Now it's in there and the clock is running again.* |
| **5:56.1** | **The two machines pass at 0.41 cells, both inside the machinery's chamber. Neither notices.** | one amber tone wedge, quality 0.97 | The glyphs overlap | one wedge | *They just walked through each other.* Nothing whatever is drawn today. |
| **6:30** | Extraction opens. The machine is **6.4 cells from deposit B, standing inside it** | "I am lost." | The shaft begins a 1 Hz green pulse; deposit B's ring at its true 12-cell radius has the machine inside it | The header goes orange | *It is standing on the thing it came for.* The reveal currently draws deposits at radius 3 against a true 12 — a lie by a factor of four, and the reason the ending reads as nothing. |
| **6:31.5** | It decides on its own that it is lost, and turns — away from the real shaft | σ 16.0 > 16.0 | It walks the wrong way, confidently | Action line: `TURNING BACK` | *Ninety seconds too late, and the wrong way.* |
| **6:40.5–8:00** | **79.5 s motionless in truth AND belief. Jammed on rock 6.4 cells from deposit B.** | frozen | A slow pulse ring on the machine and `NOT MOVING 0:01, 0:02 …` counting in the readout, beside a green deposit ring it is standing inside | frozen | **The third and worst stretch of dead air.** No drawing shortens it. Drawn honestly it becomes the cruellest shot in the match: *it is right there.* Today it reads as a crashed program. |
| **6:56.0** | **Window 6. The rival is 8.121 cells inside a 9.000 radius. It dies.** | 4 s later, a red arc from bearing 183 | The ring floods with the ember machine inside it; the glyph collapses to a red `X` and **stays as a wreck for the rest of the match**; a crash ring crosses the cave | A wide red wedge lands, for a thing the viewer has just watched die | *That's what nearly happened to ours.* Today: a red arc arrives from a bearing and nothing on screen has ever shown the thing that died. |
| **8:00** | error 91.1 cells, heading error 39.5°, cargo 0, Recall unused | "within 18 cells" | Unchanged — it has been telling the truth for eight minutes | The true wall outline draws over the map the machine built: a fan, rotated and smeared, because `HEADING_FIX_GAIN = 0.0` means nothing ever straightened it | The readout holds **91** and **18** side by side. One line: `LOST IN THE CAVE — CARGO 0 — RECALL UNUSED`. |

**One additional truth-side line, and it is the only thing on screen that makes the game's one
decision expire.** A Dijkstra over `WALKABLE` from the player's shaft, built once (measured
0.008 s, hidden inside the existing warm-up), gives the true walking time home. Against the
clock:

> **5:34** — path home 155 cells, needs 147 s including recall delay and depth latency, 146 s
> remain. After this instant Recall provably cannot get the machine home before 8:00.

That appears as a line under the truth caption, `RECALL CAN NO LONGER GET IT HOME`, and the
timeline shades everything after it. It is truth-derived, so it lives on the **truth** side
only and goes dark with the truth panel. It must never appear in a build a player touches: a
player waiting for a red bar is operating a robot with a cheat sheet, not judging under
uncertainty. `DESIGN.html`'s own line is *"truth for spectators, belief for players."*

**A fourth kind of dead air is on the timeline, not the map.** 34 of 50 timeline events are one
of two strings, firing every 16.0 s ± 0.1 for the whole match, because the rival pings on an
8 s cooldown against a 12 s `ROUTINE_COOLDOWN`. Anything on a fixed clock stops being an event.
Routine contacts leave the timeline's *sentences* entirely — they are already drawn twice on
the maps, as a wedge and as a ring at the true origin — and become pips. A contact earns a
sentence only when its bearing has moved more than 25° or its character changes.

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
  panel       #0B0E13   readout and timeline ground
  rule        #1A212B   1 px separators only

TRUTH — warm, filled, opaque
  rock        #15110D   solid rock
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
  hazard      #FF4FD8   the machinery. Both panels.
  lie         #FFD23F   a fix that moved the world; the spoof; a hot tether
  cargo       #4FE08A   the objective: deposits, the hold, the shaft, extraction
  kill        #FF3B30   a machine dying; error past the alarm threshold

TYPE
  primary     #F2F5F9
  secondary   #93A2B1
  tertiary    #56626F
```

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
| Head | 15 | bold | panel titles, captions, the action line, the now-line |
| Body | 11 | regular | chamber names, labels, timeline clock |
| Micro | 9 | regular | units only — "cells", "to go" |

`IT IS WRONG BY` ramps: tertiary ≤ 3 cells → primary 3–12 → **lie** 12–30 → **kill** > 30.
`IT THINKS IT IS WRONG BY` is **ghost** cyan always. The machine's calm is the joke; do not
colour it.

Units are **cells** everywhere, because that is what the sim and `GLOSSARY.md` say. Not metres.

### 6.3 Hierarchy, and the rule that enforces it

Three levels:

- **PRIMARY** — readable in under a second from across the room: the two display numbers; the
  tether; the machinery ring while it is counting.
- **SECONDARY** — read when something happens: both machines and their comets; the fix beat;
  sound rings and wedges; major event pips; the action line.
- **AMBIENT** — never read, only felt: cave fill, belief silhouette, point cloud, residue
  spokes, routine pips, beacons, trails, chamber names.

> **An ambient element never exceeds 35 % of a primary element's luminance, never animates for
> longer than one second, and never carries text above Body size.**

Everything else in this document is a drawing. That rule is what stops the drawing decaying
back into the forty-five-encoding screen it replaced, and it is the single most useful sentence
here.

### 6.4 The encoding of every object

**Truth panel — twelve marks.**

| # | object | encoding | level |
|---|---|---|---|
| 1 | the cave | one 200 × 120 RGBA `visuals.Image`, `interpolation="nearest"`, uploaded **once**. Rock, floor, water, with a bright rim on every rock face adjacent to floor — the cheapest cue that reads as stone. A BFS from the shaft over `WALKABLE` darkens the floor by graph distance, so the far end of the cave is visibly *deeper*: `DESIGN-PRINCIPLES` §2, *"further in is where the blocks you do not have are"*, as a gradient, for free | ambient |
| 2 | chamber names | eleven `Text`, Body, warm-dim, placed once at `CHAMBERS` centres and **never reassigned**: `YOUR SHAFT · JUNCTION · DEPOSIT A · THE BIG HALL · THE ECHO CHAMBER · THE SUMP · JUNCTION · THE MACHINERY · JUNCTION · DEPOSIT B · THEIR SHAFT` | ambient |
| 3 | the player, true | **solid** bone machine glyph on true heading | secondary |
| 4 | its comet | the last 20 s of `truth_trail` as a `Line` strip, alpha 0→1 head-ward, width 3→1 | secondary |
| 5 | its belief | **hollow** ghost glyph at the believed pose, identical geometry, plus the 2σ ellipse | primary |
| 6 | **the tether** | segment 3→5. ≤ 3 cells: 1 px cool-dim, unlabelled. 3–12: 2 px primary. 12–30: 3 px **lie**. > 30: 4 px **kill** with a pip at each end. Label at the midpoint, Head size, `34 cells` | **primary** |
| 7 | the rival, true | **solid** ember glyph and its own comet. *Drawn for the first time in this project.* | secondary |
| 8 | the machinery | a ring at the true 9-cell radius, hazard. **Quiet:** 1 px, 12 % alpha, 0.1 Hz breathe. **Warning (9 s):** a sweep fills the ring clockwise as `1 − seconds_until_lethal / 9`, brightening, with `LETHAL IN 0:07` beside it in Body. **Lethal (4 s):** the disc floods hazard→kill, three flashes at 6 Hz | **primary while counting** |
| 9 | sound origins | a ring expanding from the **true** origin at 28 cells/s, character-coloured, 2.5 s. Crash: 6 s, radius 60 | secondary |
| 10 | beacons, true | 6 px diamonds, warm-dim. Before 2:21.4 the spoofed one is indistinguishable — the surprise is preserved. Arming: it reddens as `spoof_arming` closes. After it moves: **lie** yellow, a permanent dashed line to where belief still records it, labelled `THE RIVAL MOVED THIS` | ambient → primary |
| 11 | deposits | cargo rings at the **true 12-cell radius**. The reveal currently draws 3 | ambient |
| 12 | wreck | after a death the glyph collapses to a kill `X` over 0.4 s and **stays for the rest of the match** | secondary |

**The machine glyph.** A plan-view vehicle in world coordinates: a hull, two tracks, a sensor
head that rotates slowly and throws a 120° arc when it pings, and a cargo pip per load aboard —
about 17 line segments. Both machines plus the ghost are one `Line(connect="segments")`, 51
segments, one `set_data` per frame.

It is drawn **2.4 cells long** against a true radius of 0.6. That is a 2× exaggeration of the
footprint, and it is the largest scale licence in this document — taken deliberately and
bounded. At 4.04 px/cell it is 10 px, which is legible, and it is 13 % of the machinery's 72 px
lethal disc, so the near-miss at 9.038 cells and the pass at 0.41 cells both still read
correctly. A larger glyph — an earlier draft wanted six cells, ten times true size — destroys
exactly the two beats it exists to serve. This is the answer to *"it is just a triangle moving
on a screen"*, and it must not be bought by making the truth panel lie about distance.

**Belief panel — eleven marks. Content unchanged; encoding repaired.**

| # | object | encoding | level |
|---|---|---|---|
| 1 | **the mapped silhouette** | a 170 × 130 RGBA `Image` under the cloud, alpha `clip(count · 26, 0, 150)` in `mapped`, rebuilt at 4 Hz and on every fix. **This is the element the spec has been missing.** The spec calls the smear *"the single most important visual in the test"*, and today it is 6,000 grey dots: you cannot see a shape drift until there is a shape. Nothing is discarded — the silhouette is derived from the same points | ambient |
| 2 | point cloud | **two classes only.** Sensed: 2.4 px, `sensed`, alpha 0.35 + 0.5q. Walked: 1.6 px, `walked`, alpha 0.2. The colour lerp × alpha ramp × size ramp × three source overrides collapse to one rule; four channels doing one job is most of why the map reads as noise, and `FALSE` returns are currently drawn identically to real sonar anyway, so one of the four already fails silently | ambient |
| 3 | believed pose | **hollow** ghost glyph, identical geometry to truth mark 5 | secondary |
| 4 | 2σ ellipse | ghost, 1.5 px | secondary |
| 5 | believed trail | cool-dim, 0.25 alpha | ambient |
| 6 | beacons it recorded | ghost diamonds | ambient |
| 7 | surveyed places | shaft and two deposits as **hollow** cargo rings — prior intel, not something it sensed | ambient |
| 8 | **bearing spokes** | strike → decay → **permanent 12 % residue**. By 8:00 there is a fan of about 30 faded spokes: a visible record of everything the machine has ever heard | secondary → ambient |
| 9 | own wavefront | ring from the believed pose, 28 cells/s, 6 s | secondary |
| 10 | believed machinery / believed rival | soft discs at 8 % fill with a 1 px edge, radius `clamp(σ, 4, 20)`. Demoted from the brightest rings on screen to ambient, but kept — with the truth panel beside them the gap between where it thinks the machinery is and where it is becomes a readable joke | ambient |
| 11 | fix beat | the cloud eases over 0.7 s as today, and the **pre-fix silhouette is held as a ghost** — 1.2 s for an honest fix, 1.6 s for a disagreeing one — so the map it abandoned is visible beside the one it adopted | primary on event |

### 6.5 What moves and what is still

**Three things move continuously. Nothing else.** The playhead, the leading edge of the error
chart, and the two machines.

Two problems with motion in the current display, and their fixes:

- **Slow motion does not read as motion.** The machines move at 1.1 and 1.4 cells/s; at
  4 px/cell that is 4–6 px/s, at or below the threshold where the eye registers movement at
  all. Fix: the 20-second comet. A moving gradient reads as motion even when the head barely
  moves.
- **Stillness is not marked as stillness.** 6:40.5 → 8:00 is 79.5 seconds where truth and
  belief are both frozen, and on screen that currently reads as "the video has stopped". Fix: a
  1 Hz stall ring on the machine and `NOT MOVING 0:34` counting in the readout. An invisible
  failure is a bug; a counting, visible failure is drama.

### 6.6 What a sound looks like

Her words were *"all that changes is things kinda beep and nothing really is obvious."* The
current answer to a sound is a four-second incoming arc, drawn identically for all 22 rival
pings, for the scripted echo, and — bigger and red — for a machine dying. Then it is gone. A
sound that leaves no trace cannot be reasoned about, and she was asked to reason about
twenty-two of them.

**Every audible event now makes three marks in three places in the same instant:**

1. **Truth panel, at the true origin** — a ring expanding at 28 cells/s in the character
   colour. *Where the sound was born.*
2. **Belief panel, from the machine** — a wedge on the measured bearing: full alpha instantly
   (a 120 ms strike, no fade-in, because a strike that ramps reads as a fade), decaying over
   900 ms, then **persisting forever at 12 %**.
3. **Timeline** — a pip on the event rail.

One shared curve module, `view/beat.py`:

```
strike(age)       = 1.0                     for age < 0.12 s
decay(age, life)  = (1 - age/life) ** 2     for 0.12 <= age < life
residue           = a constant floor alpha, forever
```

| event | truth panel | belief panel | timeline | life |
|---|---|---|---|---|
| own ping | ring from true pose | ring from believed pose | routine pip | 4.0 s |
| heard ping | ring from **true origin** | wedge strike → decay → **permanent spoke** | routine pip | 2.5 s / forever |
| motion (TONE) | ring from true origin | shorter wedge | routine pip | 2.0 s |
| crash | kill ring, radius 60 | wide kill wedge | MAJOR pip | 6.0 s |
| machinery signature | the ring begins its countdown sweep | magenta wedge; believed-machinery disc brightens | MAJOR pip, first of a cycle only | 9 s |
| machinery lethal | the 9-cell disc floods, 3 flashes at 6 Hz | — | band on the machinery rail | 4.0 s |
| honest fix | the ghost slides toward the machine | cloud eases 0.7 s; pre-fix ghost 1.2 s | routine pip | 1.2 s |
| **disagreeing fix** | the ghost slides; **the tether flashes lie and stays hot 8 s** | cloud eases; pre-fix ghost 1.6 s; the panel border pulses lie for 1.0 s | MAJOR pip + words | 8.0 s |
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

### 6.7 vispy, and the frame budget

Every documented trap in `phase1/view/`, and what this does about it.

| trap | handling |
|---|---|
| Assigning `Text.text` rebuilds the glyph atlas | The eleven chamber names, the panel titles, the key rows and the bar labels are **set once at construction and never reassigned**. The two display numbers are gated on their **integer** value (~1 Hz). The captions have a priority table and a `CAPTION_MIN_DWELL_S = 2.5` rule, so at most one assignment per 2.5 s each. `LETHAL IN n` is gated on the integer second: ≤ 15 per window × 6 = 90 per match. The now-line changes only on a major event, ~10 per match instead of 50. **No `Text` is assigned unconditionally in `draw()`.** |
| Setting any property on a `Rectangle` regenerates geometry and forces a synchronous repaint — ten of them cost 400 ms | **No new `Rectangle` in any per-frame path.** The machinery ring, the countdown sweep, the tether, the machine glyphs, the deposit rings, the spoof callout, the wavefronts, the readout bars, the timeline rails and the panel borders are all `Line`. Every filled region is an `Image`. The only new `Rectangle`s are the panel grounds and the readout dividers, touched only in `_layout()`. |
| Timers must be created after construction, bound to `canvas.app`, and held in a local that outlives `app.run()` | **Untouched.** The frame clock stays in `__main__.py`. The cold open is **not a new timer**: it is a branch in `advance()` on `time.perf_counter() - self._wall_clock_zero < T.COLD_OPEN_S`, and `__main__.py`'s existing `_wall_clock_zero = None` reset after warm-up already puts it in the right place. `Recorder.run()` prepends `COLD_OPEN_S * fps` frames. |
| `canvas.render()` on a never-shown canvas empties the framebuffer stack and every later paint dies inside `glBindFramebuffer` | Untouched: show, then two offscreen paints. Note the warm-up gets slower — more visuals, more strings — so budget about 2.4 s instead of 1.86 and keep the "preparing the display" message. |
| `set_gl_state("translucent", depth_test=False)` on every overlay | Every truth-panel visual gets it, and the cave `Image` gets `order = 0`. Without it the Image and the markers are coplanar and the Image wins — the first prototype came back as a cave with no machines on it. |
| `visuals.Image` | Both images are `set_data()` with a **same-shaped preallocated array**, or the texture reallocates. The cave image is uploaded once and never touched again. |
| Two cameras | Separate `TurntableCamera` instances — they cannot be shared — with identical parameters, joined with `belief_cam.link(truth_cam)` after both viewboxes exist. `link()` is bidirectional; link once and set through either. **This is the one API detail not yet run against the real display**; the fallback is mirroring `elevation`, `azimuth` and `scale_factor` on a change event, about six lines. |
| `visuals.Text` inside a camera viewbox takes `font_size` in **points, not scene units** | Chamber labels are `font_size=11`. |

**Budget.** Measured baselines on this machine: `draw()` = 1.55 ms at 8:00; `canvas.render()` =
39.5 ms at 1400 × 900 and 43.1 ms at 1600 × 900; a second heavy ViewBox costs +0.55 ms; the
cave `Image` costs 2.6 ms once at construction and 0.00 ms per frame; a silhouette rebuild is
0.33 ms, which at 4 Hz against a 60 Hz draw is 0.02 ms per frame. Expected total `draw()` is
**≈ 2.4 ms against a ~60 ms live paint budget — four per cent.** The binding constraint stays
the recorder's per-pixel readback, which a second panel does not change; an eight-minute render
goes from about 38 minutes to about 42. Startup gains 2.6 ms for the image upload and 8 ms for
the Dijkstra, both inside the existing warm-up.

**One measurement bug fixed on the way.** `EventFeed` appends in **processing order, not
chronological order**, and stamps cargo, extraction and machinery events with the current `t`
rather than their own. Invisible live and in recordings; wrong in every `--snap` frame —
`snap_142.png` shows `CARGO ABOARD` at 2:22 when the correct latest event is `the fix
disagrees` at 2:21.4. Snapshots are how this gets iterated, so it is fixed: stamp with the
event's own time and insert in time order. One sort and three timestamps.

---

## 7. What changes in the sim

**No `tuning.py` number changes. None.** Not `SPOOF_*`, not `ANCIENT_*`, not `BEACON_RANGE`,
not `ESCAPE_SECONDS`, not `ANCIENT_WARNING_S`. Every "Measured:" note in that file was earned
against a specific behaviour and this proposal is not entitled to spend them.

The reason is not conservatism, it is the experiment. The diagnosis under test is
**legibility**. If the display and the pacing change in the same commit, a different result on
the re-run cannot be attributed to either. **The beat sheet after this work is identical to the
one the tester watched**, which makes the re-run a clean A/B on the display alone.

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
# ---- display: the spectator panel -------------------------------------------------
COLD_OPEN_S:             Final[float] = 6.0
END_HOLD_S:              Final[float] = 8.0
CAVE_RASTER_SCALE:       Final[int]   = 4      # 800x480 texture from the 200x120 grid
DEPTH_TINT_FLOOR:        Final[float] = 0.45   # how dark the far end of the cave gets
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
FEED_ROUTINE_COOLDOWN_S: Final[float] = 30.0   # was hard-coded 12.0 in event_feed.py
FEED_BEARING_CHANGE_DEG: Final[float] = 25.0   # a repeat line needs a moved bearing
```

`FEED_*` are the only two that change existing behaviour, and both were previously hard-coded
inside `event_feed.py`. They change what the timeline *says*, not what the sim *does*.
`ELLIPSE_SIGMAS`, `MAX_POINTS` and `WALL_POINT_HEIGHT` are unchanged. `__main__.py`'s default
canvas goes 1400 × 900 → 1600 × 900.

**Two pacing questions are raised in §9 and not answered here**, because they are the
designer's to answer and because answering them in this commit would confound the test.

---

## 8. Build order

**Precondition, and it is not negotiable either.** The gate is re-run **live**, with her hand
on the R key, and every slice below is watched live. The playtest record already recommends
this and it costs twenty minutes. Rendering this to an mp4 and showing her the mp4 learns as
little as the first run did, because the tension criterion is about a decision and a video does
not contain one.

Two stop points. If slice 1 does not read, stop and report — that is the diagnosis being wrong,
which is worth knowing after two and a half days rather than after seven and a half.

| # | slice | what you can look at | days |
|---|---|---|---|
| **1** | **The truth channel and the truth panel core.** `stage_frame.py`, `stage_builder.py`, `Sim.stage()`, the `_in_tick` tripwire, the `_world` rename, the `MatchView` facade, and all eight invariant rules. Then, beside the belief panel exactly as it is today: the filled cave with chamber names, both machines to scale, both comets, the ghost and the tether, and the machinery ring with its countdown. **Nothing else** — no palette pass, no readout, no timeline, no captions, no cold open. | The whole hypothesis. Point it at 5:25–6:00 of seed 7, live, and watch a stranger for thirty-five seconds. | **2.5** |
| **2** | **The two numbers and the two captions.** Readout blocks 2 and 3 at 34 pt; about thirty caption strings with the priority and dwell rule. | 2:21.4 landing as a beat rather than as a dot cloud moving eight pixels. | **0.75** |
| **3** | **The belief panel repair.** The silhouette image, the two-class cloud, the residue spokes, the pre-fix ghost, the status panel cut to three rows with the overprint fixed, the map key moved out of the map and faded. | Whether the right-hand half is readable *on its own* — which is what the second gate viewing asks. | **1.25** |
| **4** | **Palette, type and hierarchy.** The twenty-value palette, the four type sizes with the 9 pt floor, the ambient/secondary/primary pass over both panels. | The screen as a designed object rather than an accumulation. | **0.5** |
| **5** | **Timeline.** The machinery rail with all six windows drawn from frame one, the two error traces, five event kinds instead of eight, the de-metronomed feed, the `--snap` ordering fix. | The shape of the whole match, and the next kill sliding toward the playhead. | **0.75** |
| **6** | **Event choreography.** The three-marks rule, the 0.25 s stagger, the spoof arming glow and beacon travel, the wreck, the stall ring and counter. | Cause-then-effect at 2:21, and a death at 6:56 you watch happen. | **0.75** |
| **7** | **Ends and the toggle.** Cold open, the 8:00 reveal retargeted to the belief panel, deposits at their true radius, the point-of-no-return line, the `T` toggle and the `D` key for the decision graph. | The first six seconds and the last eighty. | **0.5** |
| **8** | **Recorder, perf, render.** The record path, the warm-up budget, a perf pass against the frame budget, one render, `--invariant` re-run. *If passage-following wavefronts are wanted, they are built here, inside `stage_builder.py`, never through `SensorRig`.* | The comparison video, and the invariant printing eight things. | **0.5** |

**Total: 7.5 days**, with looks at 2.5 and at 4.5.

Seven and a half days is a lot for a phase whose spec says in bold *"do not engineer this."*
The defence is that the display **is** what is under test — R1 is the largest risk in the
project, the gate failed on legibility, and no other artefact of this phase is the thing being
measured. Roughly forty per cent of it is also the specification for BLD-150, BLD-152 and
BLD-154 (8 + 5 + 10 days budgeted in Phase 4), so the design survives even though the Python
does not.

**Files.** New: `match/stage_frame.py`, `match/stage_builder.py`, `match/match_view.py`,
`view/truth_panel.py`, `view/cave_image.py`, `view/caption.py`, `view/readout.py`,
`view/beat.py`, `view/cold_open.py`. Modified: `view/view.py` (becomes a compositor — layout,
header, wiring, resize; it sheds more than it gains), `view/palette.py`, `view/timeline.py`,
`view/event_feed.py`, `view/status_panel.py`, `view/map_key.py`, `view/recorder.py`,
`match/sim.py`, `match/invariant.py`, `match/headless.py`, `tuning.py`, `__main__.py`.
**Untouched: `belief/`, `policy/`, `truth/`, `sensing/`, `audio/`, `view/decision_graph.py`,
`view/node_box.py`, `view/shapes.py`, `view/backend.py`.**

---

## 9. What this does not fix

1. **She had no connection to the bot, because she put no work into it.** This is the
   designer's first diagnosis and I believe it is the true one. **No display fixes it, and
   pretending otherwise would be the expensive mistake here.** Attachment comes from
   authorship, and authorship is Phase 2. The most this display can do is make the machine a
   *character* — named, embodied, visibly deciding, visibly about to be wrong — so that Phase
   2's authorship has something to attach to. Watching a stranger's machine be cleverly wrong
   is a documentary. Watching one you taught is a game.

2. **It does not create a decision.** Recall is still one key. The point-of-no-return line makes
   the existing decision *expire* visibly; it does not make the decision *cost* anything. A
   dilemma needs two options with different prices, and spending Recall currently has no visible
   price for waiting. That is a design gap and it is above my pay grade, but it should be on the
   agenda before the next gate: criterion 4 may keep failing on design grounds with a perfect
   display.

3. **The 236-second fix drought.** After 4:03.9 the machine never re-enters any honest beacon's
   6-cell acquisition range, so the spec's "single most important visual" fires four times in
   eight minutes and never in the second half. **I am displaying the absence rather than
   removing it** — a lengthening tether and a `LAST CORRECTION 3:12 AGO` row is more frightening
   than another flash. The alternative is raising `BEACON_RANGE` from 6, which `tuning.py`
   explicitly trades against `BEACON_DROP_EVERY_CELLS = 45`: *"the gap between 6 and 45 is where
   the smear happens."* **Flagged, not changed. This needs the designer's call.**

4. **The 79.5-second frozen ending.** 6:40.5 → 8:00, motionless in truth and belief, 16 % of the
   match. The display makes it agonising rather than blank and that is all it can do.
   `tuning.py` already names the cause: *"the C3-to-ANC passage itself, which is a
   navigation-stack problem for Phase 3."* **A second flag, and this one is a policy question
   rather than a number:** after the second consecutive skipped waypoint the policy should
   probably abandon the route and start the shaft search rather than trying the next waypoint
   ninety cells away. `CLAUDE.md` says ask rather than invent. I am asking.

5. **The near-miss at 5:41 is luck, not agency.** The machine survives by 0.038 cells because it
   happens to be jammed against rock. It is the best four seconds available and it is a
   coincidence of `ANCIENT_PHASE_S = 30`. `tuning.py`'s own note says several other phases kill
   the *player* instead — *"the spoof walks it into the machinery's chamber, which is DESIGN's
   'march into a trench' beat and worth a deliberate seed later."* That is a designer's call and
   it is probably worth more than half of this proposal.

6. **Audio is untouched.** The mixer keeps its signature and reads Belief only, deliberately —
   see §4.2 rule 3. Sound now has visible consequence, which was the stated complaint, but 636
   sound events with no dynamic range is a separate afternoon and it is out of scope for a change
   that is supposed to isolate one variable. One thing improves for free: the default camera
   azimuth is now fixed at 0, so the mixer's bearing-relative stereo pan is consistent for the
   whole match instead of moving whenever the viewer orbits.

7. **It is still 2D, deliberately.** The tester's *"it would be easier to understand in 3D"* is a
   hypothesis about the fix, not an observation. Three reasons to answer the legibility
   hypothesis first: the current view is already the bad half of 3D — an unlit orthographic
   projection tilted 32° with no occlusion, no ground plane and no perspective, which has every
   ambiguity of a 3D image and none of the depth cues; a third dimension **names nothing**, and
   nothing on screen currently says *machine*, *cave*, *hazard*, *lie* or *rival*; and the honest
   price is BLD-148 + BLD-149 + BLD-154, 6 + 8 + 10 days, on top of a Rust sim that does not
   exist, where it is a *replay-screen* feature and already on the plan. If the flattened,
   filled, named, two-panel 2D display still reads as illegible **watched live**, that hypothesis
   is dead and 3D is the next experiment, entering with a known-good information design to port.

8. **It makes the spectator smarter than the player, and that is a real cost.** If Phase 1 passes
   its gate with the truth panel on, we will have proven that the **replay** is compelling —
   which is real, and is BLD-154 — and proven nothing about the run phase, which is R1, the risk
   this phase exists to retire. That is why the truth panel is bound to `T` and why §0's
   amendment says the gate is two viewings: **truth on first so she learns the world, truth off
   second so we find out whether the belief panel alone now carries it.** The second viewing is
   the one that answers R1; the first is what makes the second interpretable. In viewing two the
   truth panel does not disappear — it goes black with the words `TRUTH HIDDEN — THIS IS WHAT
   THE OPERATOR SEES`, so the belief panel is pixel-identical across both viewings and the
   comparison is clean. The cost of that choice is that viewing two wastes half the screen; the
   shipping operator layout is Phase 3's problem and this is not it.

9. **It does not make Phase 1 less throwaway.** All of it is deleted at Phase 3. `StageFrame` is
   the one idea that survives, as `ReplayFrame`.

**Everything guessed at, listed as `CLAUDE.md` requires.** The twenty colour values and the four
type sizes are my invention, calibrated by eye and not against a display. `GLYPH_LENGTH_CELLS =
2.4` is a judgement call about the smallest legible glyph that does not distort the 9-cell
radius. The eleven chamber names are mine — `cave.CHAMBERS` has only `S`, `C1`, `DA`, `C2`,
`ECHO`, `C3`, `ANC`, `SUMP`, `DB`, `C4`, `R`. The twenty-two words of the cold open are mine.
`FEED_ROUTINE_COOLDOWN_S = 30` and `FEED_BEARING_CHANGE_DEG = 25` are guesses at what stops the
metronome without also eating the echo. `camera.link()`'s behaviour is documented but has not
been run against this display.

---

## 10. The riskiest assumption

**That a spectator who knows the answer still cares about a machine that does not.**

The whole Phase 1 display was built on the opposite premise — that the viewer should be as lost
as the agent — and it produced a bored tester. This inverts it completely: it replaces *mystery*
with *dread*, and those are different emotions with different failure modes. **Mystery fails by
being illegible, which is what happened. Dread fails by being inert.** If the viewer, handed the
answer, simply shrugs — *"I can see where it is, so what"* — then the display will be perfectly
legible and still boring, and we will have spent seven and a half days to learn that the problem
was never the display. That is R1 coming back, harder, with one fewer excuse.

The specific way it could fail is worth naming, because it is not the obvious one. It is not
that she cannot read the left panel; it is that she reads **only** the left panel, where a small
machine drives slowly around a cave for eight minutes and occasionally stops — which is also
boring, and boring in a worse way, because the truth reveal will have been spent for nothing and
there is no third card to play.

Cinema says dramatic irony works: Hitchcock's bomb under the table beats Hitchcock's surprise
explosion. But the bomb works because the audience is willing the character to **notice**, and a
character who structurally *cannot* notice — which is precisely what an autonomous machine under
this invariant is — may not sustain it.

**The cheapest way to find out, and it costs two and a half days rather than seven and a half:**
build slice 1 only — the truth channel, the filled cave, both machines, the ghost and tether,
and the machinery clock. Point it at **5:25–6:00 of seed 7**, live, not recorded. Those
thirty-five seconds contain the countdown arming at 5:32, the machine walking to 9.038 cells
against a 9.000 lethal radius and standing there for the entire four-second kill window, the
window closing, and the machine stepping inside 0.8 seconds late at 5:45.8. Say one sentence —
*"the left is what is real, the right is what the machine thinks"* — and then watch two things:

- **Does she lean in at the countdown?** If a stranger watches a machine stand on the rim of a
  lethal circle while a clock runs out and does not react, nothing in the other five days saves
  it, and R1 is real.
- **Do her eyes ever go back to the right panel after the first minute?** If they never do, the
  gap is not the story and this design is wrong about its own thesis.

If both answers are yes, build the rest. If either is no, stop and report, and do not spend the
other five days finding out more slowly.
