# Overnight plan, 2026-09-09 → 2026-09-10

The designer asked for the world fixed and the trailer in a good spot in nine or ten hours. This
is the order of work, written down so it survives a session limit, and so that whatever is
unfinished when they log back on is visible rather than guessed at.

**The one sequencing rule:** principle 10 (the ice age) invalidates the surface as built. The
pit-head is a wet industrial yard under grey cloud and the world is now a snowy valley under
mountains with a town in them. **Nothing on the surface gets re-rendered until it has been
rebuilt**, or the work is thrown away twice.

---

## Wave 1 — running now

| | what | GPU | why first |
|---|---|---|---|
| A | `docs/THE-ICE.md` — reconcile every document to the ice age, including the mountains and the town | no | everything else depends on its rulings |
| B | The hero machine, placed in scenes, continuity enforced, **cave only** | yes | the cave survives the reframe; the surface does not |
| C | The trailer score — build it in `phase1/audio/`, Acts I–II, stopping after the descent | no | the longest unstarted item, and it needs no renders |
| D | The teaching act — capture shots 8–11 out of the Phase 1 window | light | the only act with no footage at all |

## Wave 2 — when A lands

| | what | GPU |
|---|---|---|
| E | **The valley**: rebuild the surface as snow, mountains, a town in them, and a way down | yes |
| F | **The vertical cave**: height as a first-class axis in the generator, ice and rock and workings interleaved by depth | yes |
| G | `ART-DIRECTION.md` rewritten to the ice world — the one sentence, the light economy, the cave section | no |

## Wave 3 — when E and F land

| | what |
|---|---|
| H | Re-render every trailer shot at its real duration, 72–120 frames, with the hero machine in it |
| I | Assemble, with the score, and cut it |

---

## What "a good spot" means, concretely

Not finished. Finished needs the teaching interface, real chassis variety and a composer. A good
spot is:

1. **The world is coherent.** Every document agrees about the ice, and nothing contradicts
   principle 10. `THE-ICE.md` names anything that had to be cut.
2. **The surface is the valley.** Snow, mountains, a town in them, at frame rate, with the shot
   list re-authored against it.
3. **The cave has depth.** Vertical is real in the generator, not dressing.
4. **One machine, in every shot, the same one**, and the introduction earns the pronoun.
5. **Shots run three to five seconds**, so the cut breathes.
6. **There is a score**, on the surface, stopping at the descent.
7. **There is a new cut**, longer than 34 seconds, with sound.

## What will not be done, and is being said now rather than discovered

- The teaching act comes out of the Phase 1 Python window, so it will not match the Godot look.
- The machines are one chassis with one loadout; the other three are still only in the machines
  spike.
- The score is procedural and is a brief for a composer, not a finished piece.
- Cave verticality will be in the generator and only partly in the art.
- The designer decisions still outstanding (cave tuning, the rock albedo, the ratchet count, the
  seventeen sound questions, the thirteen backstory questions) are not mine to make and are not
  blocking this list.

## Risks

- **Usage limits** killed two long jobs yesterday. Every wave is resumable and every agent writes
  its notes as it goes rather than at the end.
- **One GPU.** Only one capture job runs at a time; measurements taken under contention are
  reported as relative only.
- **Wave 2 is the big one.** If the valley is not buildable in one pass, the trailer opens in the
  cave and the surface act is cut rather than shipped half-done.
