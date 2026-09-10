# The trailer — one journey, no text

**Rewritten 2026-09-10.** The previous treatment was six acts, twenty-nine shots and five text
cards. It was cut twice and rejected twice. The designer replaced its whole structure in one
paragraph, and the replacement is better than what it replaces. Everything below follows from
their words; the old version is in git history and is not worth reviving.

> "what if its just a clip of one of the dogs wondering around an ice village, than it goes down
> stairs and stumbles upon a cave entrance (not the elevator thing), it wonders through the cave
> and than starts to uncover stuff and thats where it fades to black. work in the lidar views
> where it gets dark in the cave. have a flythrough of the mountains that ends at a dog exploring
> and than start the dog stuff. really show off the nice landscape, really show off the cave
> system, show a 3d map of the cave somehow after the dog explored it. the weird text that pops
> up is so weird... it feels like a horror game."

---

## 1. Why this is right and the old one was wrong

**One continuous journey beats six acts.** The old cut asked a viewer to follow a place, then a
lesson, then a descent, then a dark, then a threat, then a title, and stitched them together with
black cards. This is one animal walking somewhere, and a viewer will follow an animal walking
without being told anything at all.

**No text.** The cards are what made it feel like a horror game, and they were doing work the
pictures should do. A machine going down stairs and finding a hole needs no caption. The one thing
the cards genuinely carried — *it only knows what it has seen* — is now the ending, said as an
image instead of a sentence.

**The ending is the whole game in one shot.** The machine wanders alone in the dark, it fades to
black, and up comes the cave rebuilt out of nothing but its own sensor returns, turning in space.
That is the thesis delivered without a word, and it is why the point cloud was built.

**And it stops selling a plot the game does not have yet.** The old cut was about betrayal, a
rival's lie, and a machine walking confidently to its death. This is about a place worth going into
and a machine that goes. That is much closer to the game, and much easier to make beautiful.

---

## 2. The shape

Seven movements. No cards. No cuts to black except the one before the map.

| | | length | what |
|---|---|---|---|
| 1 | **The range** | ~20 s | A flythrough over and through the mountains. High, slow, wide, weather in the air. The shot that has to stop someone scrolling. It ends by arriving on the machine. |
| 2 | **The machine** | ~10 s | Walking, alone, small in the landscape, leaving a track behind it. |
| 3 | **The village** | ~15 s | It wanders the ice village on the valley wall. Terraces, stairs, lit windows, people's things. Somewhere lived in. |
| 4 | **The stairs, and the hole** | ~10 s | Down a flight of stairs, and off the edge of the built world it finds a natural cave entrance. Not the shaft, not machinery — a hole the ice opened. It goes in because that is what it does. |
| 5 | **The cave** | ~30 s | Ice, water, blue, scalloped walls, a pitch dropping away. Beautiful before it is dangerous. Its lamp is the only light and the ice carries it. As it goes deeper the picture starts becoming what the machine sees: returns, rings, shadows. The two registers alternate rather than being announced. |
| 6 | **Uncovering** | ~10 s | It finds something. Iron, in a cave that has been nothing but ice, which is the first sign somebody was here before. Fade to black. |
| 7 | **The map** | ~12 s | Black, then the cave it just walked, drawn entirely out of its own returns, turning. Passages as passages, the pitch as a drop, its own trail through it, and the sensor shadows as holes. Then the title. |

About 1:45. **Two structural rules only:** nothing is explained, and the map is last.

---

## 3. What each movement has to deliver

**1. The range.** Scale, weather, beauty. Rock, because a mountain is mostly rock with snow on the
ledges and in the gullies — snow holds below about fifty degrees and sheds above it, and that one
rule is most of what makes a range read. Drainage converging downhill. Fog banded in the valley,
snow in the air, spindrift off the ridges. **No repeating period at any scale**: the corrugated
rhythm two earlier passes had is the clearest possible tell that a range was generated.

**2. The machine.** Small in frame. It reads as an animal rather than as equipment when the camera
sits at its height rather than at eye height, which earlier work established by re-siting the shot
four times. Its track behind it in the snow, because a track is behaviour made visible and it is a
thing this game has that others do not.

**3. The village.** Lived in, not archaeological. Lit windows, cleared paths, things left outside.
The society is recovering rather than dying and the village is the evidence. It also gives the
machine something to walk through, which is more interesting than open ground.

**4. The stairs and the hole.** The transition the whole piece turns on. Built world above, natural
world below, and the machine crossing between them on its own. The hole should look like something
the ice opened this season rather than an entrance anybody made.

**5. The cave.** The longest movement and the one that has to be worth the trip. Ice throughout and
iron never, in this movement. A lamp inside translucent ice does something a lamp in rock cannot,
and that is the opportunity the old cave never took. The lidar cuts belong here, arriving as the
light fails rather than as a labelled section: returns resolving a passage ahead, a pitch with
nothing coming back from the bottom, the world becoming data as it gets dark.

**6. Uncovering.** One object, one moment. The first iron in a cave of ice. It does not need to be
explained and must not be.

**7. The map.** The payoff. It has to read as a *place* rather than a scatter, seen from outside, in
black. Everything the trailer just showed, rebuilt from what one machine measured while walking
through it in the dark.

---

## 4. Sound

No text means sound carries everything, so it matters more than it did.

- **A backing track across the whole piece**, beautiful rather than ominous. The tone note in the
  designer's message is broader than the cards: nothing here should feel like a horror game. Cold,
  wide, patient, with real harmonic movement. The previous score was struck iron at a fixed tempo,
  which suited a mine and does not suit a valley.
- **Snow has to sound like snow.** Footfall in deep snow is a compression rather than an impact, and
  the squeak of crushed crystals is the recognisable part. Air with falling snow in it is deadened,
  which is the opposite of reverb and is a real effect.
- **The cave is the sound design set piece**: drips, water moving under ice, the particular silence
  of a place with a low ceiling of ice, and the machine's own body.
- **The score thins rather than stops as it goes underground**, and the map is nearly silent.

---

## 5. Rules for capture, unchanged, and each learned the hard way

- In engine, in motion, 1920×1080 at 24 fps. No stills pretending to be footage.
- The camera has a body and cannot pass through anything, and a stated height is the height of the
  lens rather than the centre of the body. Short slow moves eased at both ends, no zooms, and a shot
  that must travel far is two shots.
- One machine throughout — same chassis, loadout, livery and wear — enforced by the shot validator
  rather than by convention.
- The exposure contract holds. No shot is brightened to make it read.
- Capture one project at a time. Two on one GPU cost a measurement once already.

## 6. What is honestly missing

| Gap | How this cut handles it | Would fix it |
|---|---|---|
| The village has no interiors and nobody in it | Shot from outside, in falling snow, at machine height | People, or evidence of them, moving |
| Only one chassis exists in the trailer | It is a single-animal story, so this costs nothing | The other three chassis |
| The Assayer is built and has no place in this structure | Cut. It belongs to a later trailer about danger | Nothing — this is a scope decision |
| The teaching loop is not in this trailer at all | Deliberately | A second trailer, which is the right place for it |

**The teaching cut is the one real loss and it should be said plainly.** The old treatment's whole
thesis was that the player teaches rather than drives, and this trailer does not say that. It is an
announcement of a place rather than an explanation of a game, and the designer's structure is right
that those are two different jobs. The teaching footage exists, it is good, and it belongs in the
next one.
