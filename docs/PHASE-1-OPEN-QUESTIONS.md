# Phase 1 — open questions before code

Written before any Phase 1 code. Two parts: things I think the spec gets wrong or
leaves load-bearing gaps in, and numbers I need. Nothing here has been assumed and
built; answer inline and I will treat the answered file as the tuning sheet.

`ROADMAP.md` and `DESIGN.html` arrived after the first draft. Where they settle a
question it is marked **[settled]** with the source; the spec still wins where they
disagree with it.

---

## Part 1 — pushback

### 1. "A fix snaps the map back into alignment" needs back-propagation, or it is a lie

Each sonar return is (range, bearing) in the body frame. To store it as a point it
must be placed using the *pose estimate at that instant*. Drift makes later points land
offset from earlier ones: the corridor doubles. That part is straightforward.

The trap is the fix. A fix corrects the pose estimate *now*. Points already stored do
not move. So with the naive implementation a fix only stops further smearing; the
ghost corridor stays forever, and the only thing that "snaps" is the agent marker and
the ellipse. The spec's visual — the doubled corridor collapsing onto itself — does not
happen.

What I intend to build instead: every point is stamped with the time it was placed.
A fix yields a correction (translation and heading). That correction is applied to
every point placed since the previous fix, weighted by how far into the drift interval
each point was placed (like a pose-graph relaxation with one loop closure). The ghost
slides onto the original: that is the snap. A spoofed fix runs the identical code and
drags the recent map to a wrong place, visibly tearing it from the older map. That is
the spoof moment made legible, and nothing in the code distinguishes the two cases.

**Needs a yes.** It changes what a "fix" does to belief, not just to the display.

### 2. Heading drift is the drift that reads. Translation-only drift will look wrong

"Drift proportional to distance travelled" is usually implemented as position error.
Pure position error produces a parallel doubled corridor that is hard to see. Heading
error produces a map that fans open and visibly rotates on a fix. I need both numbers
(below), and I need drift to be bias-dominated (a slow lean), not a random walk. A
random walk gives fuzz, not a ghost.

### 3. Your own beacons anchor you to your past belief, not to the world

When the agent drops a beacon, the only position it can record for it is its own
*estimated* position at drop time, which is already drifted. Re-acquiring that beacon
later collapses drift accumulated *since the drop*, and snaps the map to the frame the
agent was in at drop time. The map becomes self-consistent while remaining globally
offset from truth.

I think this is right and elegant, but confirm it, because it means: the only fix to
*truth* is the shaft (survey-placed, known position). Everything else is relative.

### 4. The spoof only works if the offset is larger than beacon range

If the spoofed fix moves the estimate by less than the range at which the agent can
hear its next real beacon, the agent re-acquires a real beacon, re-fixes, and the map
tears back. That is a superb spectator moment ("it was lying") but it means the spoof
is self-healing. If the offset is *larger* than beacon range, the agent walks off its
own breadcrumb chain and is lost unless recalled before it leaves range. **Spoof offset
divided by beacon range is the single most important tuning ratio in the test.** I want
you to set both deliberately, not me.

Related: the spec says the cautious policy "returns on high uncertainty". A spoofed fix
*collapses* uncertainty. So the spoof also silently disarms the agent's own
self-preservation, and Recall becomes the only thing that can bring it home. I think
that is the actual design of the beat and I will build toward it, but say so if not.

### 5. Nothing in the three sensors produces "sparse where it has only passed through"

Passive acoustic gives bearings to emitters, not walls. Dead reckoning gives nothing
about walls. Sonar is only fired on ping. So a corridor the agent walks without pinging
produces zero points, which contradicts "sparse where passed through" and makes the
cautious agent's map almost empty.

Options: (a) a tiny fourth sense — near-field passive returns from the agent's own
motion noise off walls within one or two cells, low quality, every tick; (b) accept the
empty corridor and show only the believed trail; (c) drop "sparse where passed
through" from the spec. I recommend (a). It is ten lines and it is what a real
machine would have. Your call, because it is a fourth sensor.

### 6. The 3D orbitable point cloud of a 2D grid is a flat sheet

The world is a 200×120 grid. Sonar returns from a 2D sim are 2D. An orbitable 3D view
of that is a sheet of points, and orbiting it adds nothing to "information under
ambiguity", which is what the phase says it tests.

Cheapest honest version: 2D sim; each wall hit spawns a short vertical scatter of
points so walls read as curtains and orbiting is not pointless. If you actually want a
3D cave sim (voxels, sonar cones in 3D), that is a different and much larger Phase 1.
I recommend 2D sim with fake height. Confirm.

**[partly settled]** ROADMAP Phase 1 says "2D top-down cave, hardcoded" and DESIGN says
milestones one to three are "coloured dots on a black background". So the sim is 2D.
What remains open is only whether the *view* is a 3D scatter with fake wall height
(orbitable, as the spec says) or a plain 2D scatter (as ROADMAP implies). I will build
the 3D scatter unless you say otherwise; the accumulation-in-belief-frame mechanism is
identical either way and the camera is free in vispy.

The waterline has the same problem: in a top-down grid it is a region (flooded cells),
in a side view it is a height. Which, and what does it do in Phase 1 — impassable,
acoustic conduit, visual only?

### 7. The spec sends the rival's ping to the player "from a bearing" but says nothing about how sound moves in a cave

If sound propagates by straight line, bearings point at the source through rock and
the cave geometry is meaningless to the acoustics. If it propagates along passages, the
bearing points down the passage the sound arrived through, range attenuates with path
length, and "is that a rival or an echo?" is an emergent question rather than a
scripted one. The second is far more interesting and is roughly a BFS on the grid. It
also gives the echo a mechanism: a loud ping arriving by two paths gives two bearings.
DESIGN already commits to this ("reflective rock produces echoes that look like
contacts"; "decoys don't move naturally"), so the echo's tell should be that it does
not move and does not repeat.

I would still script the required echo event so the timeline is guaranteed, but the
propagation model decides whether bearings mean anything. Choose.

### 8. Belief-only display means the player can never *know* the agent is wrong

The gate wants the player to "form a wrong theory and correct it". With truth never
rendered during the run, the only correction signals are: the map tearing on a big
fix, contacts that stop making sense, and Recall failing. Two cheap things help and
both are legal (both are derived from belief):

- Render the fix correction as an event: a visible jump vector and the innovation size.
  A fix that moves you fifteen cells when your ellipse was three cells is itself the
  clue, and a player who notices it has done exactly what the design wants.
- After the run ends, reveal truth over belief. "Never rendered *during* the run" allows
  it, and the correction of the wrong theory often happens at the reveal. Without it the
  player leaves not knowing whether they were fooled, and you lose the playtest signal.

I would like to build both. Say no if you disagree.

**[settled for the reveal]** DESIGN: "Ground truth appears in exactly two places: the
post-match replay, where both layers are drawn together, and the spectator view." The
post-run reveal is in scope. The fix-jump overlay is still my proposal.

### 9. The rival needs its own Belief

The invariant says policies never see ground truth. Running the rival on truth in
Phase 1 would be cheaper but would mean "pings often" has no cost and no benefit for
the rival. Simulating two beliefs is a loop over two agents. I intend to do it.

### 10. The match needs a beat sheet, and it should be yours

Eight minutes with a cautious agent that pings rarely is eight minutes of an almost
empty screen unless events are scheduled. The spec requires a contact, an echo, the
spoof and a deadline but gives no order or timing. A proposed timeline, for you to edit:

| Time | Event |
|---|---|
| 0:00 | Commit. Agent leaves shaft. Shaft beacon gives one true fix. |
| 0:45 | First own ping. Map appears. |
| 1:30 | Rival ping heard from a bearing. First contact. |
| 2:15 | Passive contact that does not repeat and does not move: the echo. |
| 3:00 | Ancient system signature first audible, distant. |
| 3:45 | Second rival ping, closer, different bearing. |
| 4:30 | Spoofed beacon. Fix. Map tears. Ellipse collapses. |
| 5:15 | Ancient cycle fires. Rival dies to it, audibly. Its pings stop. |
| 6:00 | Player's agent, on the wrong fix, heading somewhere it should not. |
| 7:00 | Last moment Recall can plausibly succeed. |
| 8:00 | Extraction deadline. Reveal. |

Who dies to the ancient system? I have assumed the rival, so the player hears a
sequence they must interpret. If the player's agent can die to it, say what ends the
match.

---

## Part 2 — numbers I need

I will not run anything until these have values. A dash in the "why it matters"
column means it is a straightforward tuning knob.

### Time and scale

| # | Quantity | Why it matters |
|---|---|---|
| T1 | Tick rate (Hz) | Sim resolution; everything below in ticks or seconds, your choice |
| T2 | Agent speed (cells/s) | At 1 cell/s the agent covers 480 cells in a match: two or three cave crossings. Sets how much of the cave gets seen |
| T3 | Extraction window: DESIGN says the last 90 s, and anything not back through a shaft is lost. Confirm 90 s of an 8:00 match, so the window opens at 6:30 | The Recall tension is entirely this number |
| T4 | Does the match include the 20 s descent before commit, or start at commit? | — |
| T5 | Match seed fixed for reproducible tuning? (I assume yes, with a flag) | — |

### Dead reckoning

| # | Quantity | Why it matters |
|---|---|---|
| D1 | Position bias per cell travelled (fraction, e.g. 0.03 = 3 cm per m) | Size of the smear |
| D2 | Heading bias (degrees per cell travelled, or per turn) | Whether the smear reads at all; see pushback 2 |
| D3 | Random component on top of bias (std per cell) | Fuzz vs ghost |
| D4 | Covariance growth for the ellipse (should it track D1–D3 honestly, or be tuned separately for legibility?) | The ellipse is the estimator's *belief about its own error*; it is allowed to be wrong |
| D5 | Uncertainty threshold at which the cautious policy turns for home (ellipse radius in cells) | Interacts with pushback 4 |

### Passive acoustic

| # | Quantity | Why it matters |
|---|---|---|
| P1 | Range at which rival *motion* noise is detectable (cells) | Whether the agents ever hear each other moving |
| P2 | Range at which a rival *ping* is detectable | Should be much larger than P1 |
| P3 | Range at which the ancient signature is detectable | Warning distance |
| P4 | Bearing noise std (degrees) at close range, and how it degrades with distance | Width of the uncertainty wedge |
| P5 | Quality falloff model: with distance only, or with path length through the cave (pushback 7) | — |
| P6 | Contact persistence: how long a bearing line stays drawn after the last return (s) | Screen clutter vs memory |
| P7 | Returns needed before a contact is drawn as a track rather than a single line | — |
| P8 | Is the agent deaf to passive while its own ping is outgoing? For how long? | — |

### Active sonar

| # | Quantity | Why it matters |
|---|---|---|
| S1 | Arc width (degrees) and number of rays | Points per ping; map density |
| S2 | Max range (cells) | — |
| S3 | Range noise std and bearing noise std | Point confidence spread |
| S4 | False-return rate (spurious points per ping) and their confidence | "Returns are sometimes false" |
| S5 | `audible` duration after a ping (ticks or s) | — |
| S6 | Cautious policy ping cooldown; aggressive policy ping cooldown | The two policies are mostly these two numbers |
| S7 | Wavefront visual speed (cells/s). Real sound would cross the cave in a frame; this is a fake speed for legibility | — |
| S8 | Near-field passive sense (pushback 5): range and quality, if approved | — |

### Beacons

| # | Quantity | Why it matters |
|---|---|---|
| B1 | Drop interval: by time (s) or by distance travelled (cells)? Value? | Chain spacing |
| B2 | Beacon acquisition range (cells) | See pushback 4. If B2 ≥ B1-in-cells the agent is never off its chain and drift becomes small jumps rather than a smear |
| B3 | Fix accuracy (range/bearing noise to a beacon) | How tight the ellipse collapses |
| B4 | Fix mode: one-shot on entering range, or continuous while in range? | Continuous means drift only grows away from beacons |
| B5 | Shaft beacon: survey-placed with a true position (the only truth anchor)? | Pushback 3 |
| B6 | Spoof time (s into match), location, and offset (cells and direction) | The beat. Direction should be chosen for the drama you want: toward the ancient, or "closer to the shaft than it is" so Recall fails |
| B7 | Spoof mechanism: impersonates a known beacon ID, or is an unknown beacon the agent trusts anyway? | Decides what Belief.beacons has to hold |

### Ancient system

| # | Quantity | Why it matters |
|---|---|---|
| A1 | Cycle period (s) | — |
| A2 | Warning lead: signature onset before lethal (s) | "Legible before lethal" |
| A3 | Lethal duration (s) | — |
| A4 | Hazard footprint (which cells, or a radius around a point) | — |
| A5 | Signature audible range (also P3) | — |
| A6 | What the scripted policies do about it: hold position while signature is up if within N cells? Ignore entirely (aggressive)? | Who dies |
| A7 | Kill or damage? If damage, how much per second inside | — |

### Policies and deposits

| # | Quantity | Why it matters |
|---|---|---|
| L1 | Do agents know deposit locations a priori (rough intel), or must they explore to find them? | Exploration policy is real work; a priori is a waypoint list |
| L2 | Dwell time at a deposit to load; cargo capacity; does cargo show in self-report | Something must be at stake for Recall to be a decision |
| L3 | Does the cautious agent return on its own when full? When uncertain (D5)? Both? | If it always returns in time, Recall is never needed |
| L4 | Aggressive rival route: how deep, past the ancient system or not | Whether it dies (pushback 10) |
| L5 | Rival passes within P1 of the player's agent at least once? Where? | Guarantees a real contact |

### Recall

| # | Quantity | Why it matters |
|---|---|---|
| R1 | Behaviour: retrace the believed beacon chain in reverse, or path through the believed occupancy map to the believed shaft? | Retracing is simpler and self-heals via beacons; pathing on a torn map fails in interesting ways |
| R2 | Delivery: instant, delayed by N s, or a chance to fail? DESIGN says latency proportional to depth and blocked in acoustic shadow; Phase 1 spec is silent. A fixed delay of a few seconds is the cheapest version of that tension | — |
| R3 | If the agent cannot find a believed path home, what does it do? | Edge case that will happen after the spoof |
| R4 | Number and position of shafts | "Nearest shaft" |

---

## Part 3 — tooling

Keep numpy, vispy, sounddevice. Reasons and caveats:

- **vispy** does exactly one thing we need well: a large scatter with per-point colour
  and size, orbitable for free with a turntable camera. Per-point confidence maps to
  alpha and size. It needs a backend on Windows; I will use **PyQt6** (glfw is the
  fallback). Overlays (wedges, ellipse, wavefronts) are line visuals in the same scene.
- **sounddevice** ships PortAudio in its Windows wheel and gives a callback into which
  a numpy mixer writes stereo frames. The mixer is about a hundred lines: a handful of
  voices with pan, pitch, envelope. That is enough for a contact tone that pans with
  bearing and sharpens with quality, a ping sweep that spreads as the wavefront does,
  and a signature drone for the ancient. The alternative is `pygame.mixer` with
  pre-rendered tones and per-channel left/right volume: less code, but no continuous
  pitch or filter movement, and the ancient's signature wants to *change* as it
  approaches lethal. sounddevice is the right choice for that.
- Not proposing anything else. No config system; numbers go in one `TUNING` block at
  the top of the file so you can edit them in place.

One environment note: I am building on Linux without a display or audio device, so
I can run the sim headless and verify state, but the point-cloud rendering and the
audio panning will get their first real look on your machine. Expect a round of
"this looks wrong" fixes after the first run.


---

## Part 4 - decided after the first playtests

### Sonar and lidar are both loadout options

Designer's question: *"can we change from pings to lidar? Idk why we wouldn't do lidar
in a cave, maybe pings only when it's flooded."* Then: *"in the real game, sonar and
lidar should both be options the user has to decide upon."*

Decision: both are modules. The player picks, and the choice is locked at launch like
every other loadout choice.

- **Sonar** - loud. Every listener in the basin hears it, from the direction of the
  passage it arrived through. Long range. Works in water.
- **Lidar** - silent. Short range, precise. Blind the moment there is water or silt in
  the way. The water surface reflects, so from the dry side a sump maps as a wall over a
  mirror: the agent steers round it and never learns what is beyond (designer's call,
  over the alternative where water returned nothing, read as open space, and would have
  sent the agent in). A sweep is a visible light in a dark cave, so it is a tell to
  anyone with *line of sight* - local exposure, not basin-wide. (Not modelled in Phase
  1: neither agent carries optics.)

"Do I ping?" does not go away. It moves. For a sonar carrier it is the loud question it
always was. For a lidar carrier it becomes *where do I dare to go* - the quiet sensor is
also the one that goes blind in the flooded sections, which is where the machinery
lives. A Swimmer chassis can only sensibly carry sonar.

**The gate is two viewings: an agent carrying sonar, then an agent carrying lidar.**
Designer's call after a four-lens design panel with three adversarial judges. Sonar
goes first because the Phase 1 spec names three sensors and its acceptance criteria are
written for pings, and about ten measured tunings were calibrated against heard pings
-- so that viewing is the specced one and the one the gate is judged on. The panel also
found that in Phase 1 "do I ping" is a cooldown rather than a decision: no policy reads
contacts, so the gate is testing the *signal* side of pings (something is out there,
roughly that way, and it just died), which is the rival's emission and is untouched by
the player's sensor.

The panel's caveat, recorded and accepted: a tester who sees both worlds compares
rather than reacts, which weakens attribution of a failure ("nothing happened" and
"the machine looked implausible" are fixed differently). Watch the first viewing for the
gate and the second for the sensor question. `PLAYER_SENSOR` in `tuning.py` is the
first viewing; `--player-sensor lidar` is the second; both render from the same seed.

Also decided from the same panel: the scripted echo moves from 2:15 to 2:35, after the
spoof, because at 2:15 it merged into the standing rival contact and never showed as
its own event; and a lidar ray reaching water returns the surface as a wall.

GLOSSARY's *Passive / active* entry should be updated to say this; left for the
designer, since it is the one document that defines the vocabulary.
