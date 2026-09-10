# The teaching act — capture notes

2026-09-09. `TRAILER.md` Act II, shots 8 to 12: the act with no footage. Five shots now
exist at 1920×1080, 24 fps, in `spikes/trailer_teach/seq/<shot>/`, with the ungraded
renders beside them in `raw/<shot>/`.

Nothing under `phase1/`, `phase2/`, `crates/`, `agent_model/` or `spikes/godot/` was
touched. Everything here reads `phase1` as a library.

---

## 1. The capture path — what it actually is

**There is no recorder for the teaching window.** `phase1/view/recorder.py` is the obvious
lead and it is the wrong one: `Recorder.__init__` takes a `MatchView` and builds a
spectator `View` — truth beside belief, the cold open, the reveal orbit, the offline
`Mixer` for sound. It cannot be pointed at a `TeachView`, and a teaching session has no
eight-minute shape for it to record.

What the teach window *can* produce, and this is the whole path:

```
TeachView(match, registry, workdir, show=False, size=(w, h))   # an offscreen SceneCanvas
view.draw()                                                    # one frame, from Belief
view.canvas.render()                                           # -> HxWx4 uint8, RGB in [:, :, :3]
view.snapshot(path)                                            # draw + write_png, the same thing
view.press("2")                                                # the key a player presses
match.advance_to(t)                                            # the clock, from outside
```

It is already used this way in one place: `python -m phase1 --teach --snap DIR`
(`_snap_stops`, `phase1/__main__.py`) opens the window with `show=False`, runs to a stop,
takes a PNG, presses a key, runs to the next stop, takes another. **Two frames.** It is a
stills path, not a capture path.

So the capture path for a *shot* is that same offscreen canvas driven on a fixed clock
instead of the wall clock, which is what `capture.py` here does. The live window's own
`view.advance()` reads `time.perf_counter()` and is therefore not repeatable; it is never
called. `MatchView.advance_to(t)` is, with `t` stepping by 1/24 s, and it stops early and
returns when the match pauses to ask — so the frame loop holds the clock still while a
question is open, exactly as the live window does by shifting its origin.

Two things worth knowing about the raster:

- **Size.** `canvas.render()` returns *physical* pixels: the requested logical size ×
  the display's DPI scale (1.25 here) × vispy's `px_scale`. Requesting **1536×864**
  therefore yields exactly 1920×1080. Capture is at `px_scale=2` (3840×2160) so the
  framing pass has headroom to crop and warp without upscaling.
- **`px_scale` scales the layout and the type together**, so a render at 3× or 4× is the
  same design at higher resolution rather than the same pixels enlarged. That is what
  makes shot 11 possible: the rail is 300 logical px wide whatever the window size, so
  the only way to fill a frame with the rule and keep it sharp is to raise `px_scale`
  until 300 logical px is about 1500 physical ones.

Costs measured on this machine (below), all offscreen:

| render | ms/frame |
|---|---|
| teach window, 3840×2160 | 345 |
| spectator, 6000×4200 (`px_scale` 3) | 734 |
| spectator, 8000×5600 (`px_scale` 4) | 780 |
| the framing and grade pass, 1920×1080 out | 1500–1940 |

---

## 2. How the session was driven

Not a person hesitating: a **scripted performance that can be shot again**.

`--teach-scripted TREE` does exist and is not it. `run_scripted_demo` builds
`Demonstration(match, TreeChooser(tree, spec)).run()` and writes a trace — headless, no
window, no frames. It is perfectly deterministic and it is what produced the
demonstrations the rule was induced from, but it cannot be photographed.

So `capture.py` uses the same `TreeChooser` at the *window's own keys*: it winds a match
to the stop it wants by answering every earlier stop the way the tree would, builds the
window on that match, then runs a frame loop that calls `view.press(str(n))` — the same
handler a keyboard hits — at a scripted frame. The pace is chosen for an audience: a
stop is held for about half a second to a second and a half before the key lands, which
is far slower than a person who already knows the answer and far faster than one who
does not.

The session:

- **seed 7** — the project's default and the seed whose beacon lie jumps 33.8 cells.
- **every block on the list**: all six predicates, all four actions, so the panel shows
  the full vocabulary the way it does once a player has met all of it.
- thresholds are the block list's provisional ones except where the cautious reference
  tree has its own (`machinery_audible` 0.45, `uncertainty_exceeds` 16).
- `phase1/reference/cautious.json` as the chooser — the temperament standing in for the
  player.

That session has **13 stops**. `scout.py` prints all of them; the shots were picked off
its output.

The rule in shot 11 is genuinely induced from this teaching, not hand-written: three
demonstrations (seeds 7, 11, 23) → `induct` → `session/tree.json`, 30 recorded stops,
30 agree, 0 disagree.

```
the machinery is loud (level = 0.4)?
  yes: freeze until it passes
  no: lost (theta = 11)?
    yes: go back
    no: fetch from a deposit

If the machinery is loud, freeze until it passes. Otherwise if lost, go back.
Otherwise fetch from a deposit.
```

That is, near enough word for word, the line the treatment invents for shot 11.

---

## 3. The shots

All 1920×1080, 24 fps, PNG per frame, numbered from 000.

| dir | frames | length | what is on screen |
|---|---|---|---|
| `seq/08_panel_stopped` | 120 | 5.0 s | Stop 6, clock 4:30. 36 frames walking in with the numbers ticking, then **IT HAS STOPPED / because: late**, six beliefs with their raw values, and four things it could do. No key is pressed. Slow push in, handheld. |
| `seq/09_choice_taken` | 72 | 3.0 s | Stop 8, clock 5:27, **because: lost**, `lost yes 16.0` against `theta = 16`. Held one second, then `[2]` lands on frame 24 and the footer says **you chose: go back**; the machine turns and goes for the remaining two seconds. |
| `seq/10_three_stops` | 96 | 4.0 s | Stops 9, 10 and 13 at 5:37, 5:45 and 7:08, 32 frames each, hard cut between them. Three different reasons and three different answers: the machinery is loud → `[3]` freeze; the freeze ends → `[2]` go back; the last fix was a jump → `[1]` fetch. The three beats punch in — 3630, 3400 then 3170 source pixels wide — so by the third the clock and the header are gone and only the question is left. |
| `seq/11_the_rule` | 96 | 4.0 s | The rule in the machine's words, on the spectator rail, on a match the rule is driving. The **lit branch changes at frame 35** — the decision at t = 297.95 walks the `no → lost → go back` path and those two lines light while the others fall back. Clean push in, no handheld. |
| `seq/12_runs_alone` | 96 | 4.0 s | t = 440, four seconds with no stop at all: the machine driving, the cloud extending, the numbers moving, and the footer's own words, **it is driving itself; it will stop when it has something to ask**. This is the frame the card *You cannot drive it. You can only teach it.* should land on. |

Shot order in the cut is forward in match time throughout — 4:30, 5:27, 5:37/5:45/7:08,
7:20 — so the clock in the rail never jumps backwards.

### Commands

```
# the three demonstrations the rule comes from (headless, deterministic)
ALL=deposit_remaining,carrying_cargo,time_elapsed_exceeds,uncertainty_exceeds,\
fix_jump_exceeds,machinery_audible,go_to_deposit,return_to_beacon,hold,interface_machinery
for s in 7 11 23; do
  python -m phase1 --teach-scripted phase1/reference/cautious.json --seed $s \
      --enabled "$ALL" --workdir spikes/trailer_teach/session
done
python -m phase1 --induce spikes/trailer_teach/session

# what the session does, stop by stop
python spikes/trailer_teach/scout.py 7

# the renders
python spikes/trailer_teach/capture.py 08 --scale 2
python spikes/trailer_teach/capture.py 09 --scale 2
python spikes/trailer_teach/capture.py 10 --scale 2
python spikes/trailer_teach/capture.py 11 --scale 4 --start 296.5 --frames 96
python spikes/trailer_teach/capture.py 12 --scale 2 --start 440.0 --frames 96

# framing, the over-the-shoulder treatment and the grade
python spikes/trailer_teach/grade.py all              # or one shot: grade.py 10_three_stops
```

`teaching_act.mp4` beside this file is the five cut together in order at 24 fps, 20
seconds, for watching the motion. It is a review copy, not a deliverable: the frames in
`seq/` are what the edit uses.

Every one of them is repeatable. Nothing reads a wall clock: the sim is seeded, the
choices come from a tree, the frame clock is `frame / 24`, and the grain is seeded on the
frame number. Re-running any line above re-renders the same shot.

`raw/` and `seq/` are gitignored, as every other frame sequence in `spikes/` is —
`capture.py` rebuilds `raw/` and `grade.py all` rebuilds `seq/` from it.

---

## 4. The look, and how honest it is

The problem is stated in `TRAILER.md` §7: *"The teaching panel is a 2D Python view — shot
over the shoulder at an angle, treated as a screen in the world rather than as the game's
UI."* That is the right answer and it cannot be done properly tonight, because doing it
properly means rendering the panel onto a screen inside a Godot scene. What `grade.py`
does instead is composite a room around the captured panel:

1. **crop and move** — the framing, eased in and out; handheld on shots 8, 9 and 10,
   clean pushes on 11 and 12. Section 8's rule about eases and sub-degree noise is kept.
2. **screen structure** — pixel pitch and the display's own glare, applied at the
   screen's own scale so the grid belongs to the monitor and not to the frame.
3. **perspective** — the panel as a quad seen from the operator's left: 4–5 % keystone
   so the far edge is shorter, about a degree of tilt off level. Deliberately mild;
   past about 6 % the rail stops being readable, which defeats the shot.
4. **the room** — near-black and warm, lit by the screen and nothing else, with a dark
   metal bezel that catches a little of it. On shots 8, 9, 11 and 12 the screen's real
   edge is inside the frame, so a monitor is visibly sitting in a dark room. Shot 10
   deliberately keeps its edges outside the frame; see §6.
5. **the glass** — the room's own dim warm reflection in the screen's face, brightest
   where a lamp would be. This is the one step added after measuring rather than before,
   and the measurement is below.
6. **the shoulder** — a defocused body in the bottom left, rim-lit by the screen. On
   shots 8 and 11 only.
7. **the lens** — veiling glare off a bright source in a dark room, sub-percent barrel,
   a pixel of chromatic aberration at the frame edge and none in the middle.
8. **the sensor** — vignette, grain that lives in the shadows, and the black floor lifted
   to 3/255 to match the cave.

**How well it matches, measured rather than asserted.** Read off
`spikes/godot/cave/shots/cinema/seq/t17_follow_machine/030.png` and one frame of
`t16_lamp_comes_on`, against `seq/08_panel_stopped/060.png`:

| | cave t17 | cave t16 | graded shot 8 |
|---|---|---|---|
| black floor (1st percentile) | 3.0 | 3.0 | **3.0** |
| median luminance | 13.0 | 6.0 | **15.0** |
| 95th percentile | 72.3 | 51.3 | **35.0** |
| mean RGB of everything under 25 | 11.5 / 8.4 / 6.0 | 9.5 / 7.0 / 5.4 | **13.6 / 14.0 / 15.5** |

So: **the black matches exactly, the exposure is close** (a little flatter than the cave —
the panel has no highlight anywhere near a tungsten lamp), **and the colour does not
match, by construction.** The cave's darks are warm at roughly 1.9 : 1.4 : 1; the teach
shot's are neutral. That is as far as it can honestly go, because ninety per cent of these
frames is screen and the screen is a cold image. Without the glass reflection in step 5
the darks were 8.7 / 10.5 / 13.4 — visibly blue — and the reflection is what pulls them to
neutral. Pulling them any further would mean laying an orange wash over a blue display,
which is not what a photograph of one looks like.

**What still does not match, and it is not the grade.** Three things:

- **The screen is cold and everything else in the cut is warm.** That is correct and
  deliberate — `ART-DIRECTION` keeps the world warm and belief cold, and a display in a
  dark room is the one place both are allowed in frame. The glass reflection takes these
  shots from blue to neutral, which is as far as physics allows; they will still read
  cooler than the surface shots either side of them, and will need those shots to sell
  the room.
- **There is no geometry.** The room has no objects in it, no depth cues but a blur
  gradient, no reflections in the screen, no light falling on anything with a shape.
  A viewer will read "monitor" but not "workshop". Roughly a 6 out of 10 match: it is no
  longer the game's UI, and it is not yet a photographed screen.
- **The machine on that screen is a triangle.** Shots 8–12 show the machine as a glyph on
  its own map. §11.1's requirement — one machine, established, carried through every shot
  — is not met by any of this footage, and cannot be: the teach window draws belief, and
  belief does not contain a chassis.

**What a proper version needs**, in the order that buys most:

1. The panel as a **texture on a screen model in the surface spike**, with the operator's
   bay around it, a real camera, real light, and the same post the rest of the cut gets.
   Every drawn pixel here then goes away, and the rail can be laid out for the shot
   instead of cropped for it.
2. **A hand.** Nothing in these five shots shows a person. The choice is made by the panel
   changing, not by anybody doing anything. One hand entering frame at the moment of
   choice would do more than every step of the grade combined.
3. **Shot 12 as it is written** — the Godot training course, the machine walking it — with
   the teach panel visible in the background rather than being the whole frame.

---

## 5. Does a viewer see teaching rather than operating?

Watched cold, no audio, no context, the five in order:

**Mostly yes, and for one reason: the words.** The panel says, in English, *IT HAS
STOPPED*, *because: late*, *WHAT IT BELIEVES HERE*, *WHAT YOU CAN DO*, *you chose: go
back*, *THE RULE IT WAS TAUGHT*, *it is driving itself*. A viewer who reads any two of
those has the premise. The machine stops, states a belief, is answered, moves. The rule
then appears in the same vocabulary as the answers, and the last shot has nobody
answering. That arc is legible.

**Where it is weak:**

- **Nobody is on screen.** The shoulder is a dark shape at the edge of two shots and it
  is not enough. Teaching is inferred from the panel's wording, not seen. If a viewer
  does not read the text, these are five shots of a screensaver. *This is the single
  biggest gap and a hand fixes it.*
- **The choice has no visible act.** Between "four things it could do" and "you chose: go
  back" nothing happens on screen but the words changing. A key press, a highlight, a
  cursor — anything that shows the answer being *given* — would carry it.
- **Shot 8's held panel is a still.** Once the machine stops, nothing in the frame moves
  for three and a half seconds; the only motion is the camera and the grain. That is
  defensible — the machine has stopped and is waiting for you, and the stillness is the
  content — but it is the one shot where §6's "no stills" rule is being read generously,
  and it is flagged rather than hidden.
- **Shot 10 nearly reads as one shot rather than three.** The rail has to reach the
  frame edge in every beat — the words are on the right — so the punch-in can only be
  taken off the left and the top, and 3630 → 3400 → 3170 is as much scale change as the
  geometry allows. It now escalates, but not as much as a montage wants. A version shot
  in 3D could cut between the panel and the operator, which is what the beat really
  needs.

---

## 6. Two defects in the shipped view, found while framing

Neither is a capture artefact; both are in the layout at its shipped size.

- **`teach_view.py`: the `because:` line does not wrap.** `stopped_why` is a single fixed
  slot and the rail is 300 px, so anything past about 28 characters runs off the right of
  the canvas. `because: the machinery is loud` renders as `because: the machinery is lo`.
  Six of this session's 13 stops clip. Shot 8 uses stop 6 (`because: late`) rather than
  the otherwise better stop 5 for exactly this reason.
- **`tree_panel.py`: the IN WORDS sentence is hidden at the default window size.**
  `TreePanel.move` drops it whenever what is left under the tree is shorter than the
  sentence needs, and at the default 1600×900 (`CANVAS_W`/`CANVAS_H`) it always is —
  `shots/teach/spectator_rule_332.png`, rendered before any of this, has no IN WORDS
  either. A player who never enlarges the window never sees the plain-English form of
  the rule, which is the form the Phase 2 protocol puts in front of the tester. Shot 11
  gets it only by rendering at 1600×1120 and cropping the rail out of a taller frame.

---

## 7. Measurement conditions

`tasklist` before, during and after: no Godot, no Blender, no Unreal, no ffmpeg. The
machine was running Claude Code, VS Code, a browser, Discord and Spotify. Nothing else
was touching the GPU, so none of the numbers in §1 are contended. The teach window is a
2D vispy canvas and the dominant cost is framebuffer readback, which scales with pixel
count — 345 ms at 3840×2160 against 780 ms at 8000×5600 is readback, not draw.

---

## 8. Everything guessed, in one list

1. **Seed 7.** The project default, and the seed the beacon lie is documented on. Not
   specified anywhere for the trailer.
2. **`phase1/reference/cautious.json` as the player.** A temperament standing in for a
   person. The aggressive tree would have produced a different, more reckless act.
3. **Seeds 11 and 23** for the other two demonstrations. Arbitrary; they only had to
   induce cleanly, and they did.
4. **Which stops to shoot** (6, 8, 9/10/13) and the beat lengths inside them — how long a
   stop is held before the key lands. Chosen to be readable, not measured against
   anything.
5. **24 fps**, from the brief's "72 to 120 frames". The rest of the trailer's rules say
   capture at 60 and conform; the Godot sequences on disk are 60 frames a shot, so the
   frame rate the cut will actually run at is not settled anywhere I could find.
6. **Shot 12 from the teach window, not the spectator display.** The literal reading of
   "runs that rule alone" is the spectator display, which is where a taught tree actually
   drives a match — but that display draws the true cave beside the map, and truth in
   Act II pre-empts the belief cut at 1:13. The teach window keeps the act in one
   register at the cost of the rule not being on screen in shot 12.
7. **Shot 11's window is 1600×1120**, not 16:9, so the rail has room for the sentence.
   The shot is a crop, so nothing else changes — but it is not the shipped window size.
8. **The over-the-shoulder geometry**: 4–5 % keystone, about a degree of tilt, where the
   screen's edges land. No reference; picked so the rail stays readable.
9. **The room, the bezel, the shoulder and its rim light are drawn, not captured.** They
   are the only invented pixels in these five shots. The screen content is all real and
   all moving.
10. **The grade target** was read off two frames of `cave/shots/cinema/seq/`, not from a
    written spec. If a trailer LUT exists, this is not it.
10b. **The glass reflection's level.** Set so the darks land neutral and the median
    luminance lands near the cave's, and no higher — §2.9's rule is that no shot is
    brightened to make it read, and a veiling reflection is the only thing here that
    could be mistaken for doing that.
11. **`px_scale`** as the way to get a high-resolution render out of the window. It is a
    vispy argument, not something the project uses anywhere.
12. **`--start 296.5` for shot 11** so the decision at t = 297.95 lands a third of the way
    in, and **`--start 440` for shot 12** because it is the longest stretch after the last
    stop shot. Both picked off the scout.
13. **Handheld amplitude** (about 3 px and a tenth of a degree at 24 fps).
14. **No audio.** The recorder's offline `Mixer` path only exists for the spectator
    `View`; the teach window has none. §5 wants the score under Act II and there is no
    score yet.
