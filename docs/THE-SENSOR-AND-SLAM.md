# The sensor, and the thing the machines cannot do yet

2026-09-09. Three designer questions asked together, answered against what the code actually
does. `DESIGN-PRINCIPLES.md` §8 fixed that the sensor is simulated for real; this is what that
opens up. Nothing here is decided except where it says a decision already exists.

---

## 1. Water returns a surface — already decided, and it stands

> "We decided water returns should just return as a plane."

Correct, and it is recorded. `PHASE-1-OPEN-QUESTIONS.md` and the board both carry **lidar water
returns as a wall**, over the rejected alternative where water returned nothing, read as open
space, and let the machine plan a route straight into a sump. `phase1/sensing/sensor_rig.py`
implements it: a ray reaching water returns the surface, and the *hole* branch was deleted.

**What changes under a scanning sensor.** The decision survives, but it gets richer for free
rather than needing new rules:

- A flat sheet of returns at the water datum, and because the rings are concentric, still water
  reads as a **perfect set of arcs** — the most regular thing in the machine's whole view. Real
  water is either a mirror that returns nothing or a strong specular flash; a clean plane is a
  game abstraction, and a defensible one, because it makes water *legible to the machine* rather
  than invisible to it.
- The plane is at a known height, so a flooded passage reads as a floor that is at the wrong
  level, which is exactly what it is.
- Disturbed water should break the arcs. A machine standing in a sump makes its own returns
  unreliable. That is a consequence, not a new rule.

**Open, and small:** whether the surface returns at full intensity (a specular flash) or low
(most of the energy leaves), and whether anything is returned from the bottom in shallow water.
Recommendation: low intensity, nothing from the bottom, and the bottom only becomes knowable by
walking into it.

---

## 2. Dust and moisture as a sensor failure — endorsed, and it belongs to SLAM

> "Then dusty areas in the cave / moist areas that would trip up the sensor would also be cool."

Agreed, and the lidar spike already flagged its absence as the one real omission
(`spikes/godot/cloud/LIDAR.md` §9). Underground this is not a detail: airborne dust and water
mist are the standard reason mine and tunnel scanning fails.

**What it is physically, and therefore what to build.** A beam through suspended particles gets
partial returns from the air itself before it reaches anything solid. Real sensors report this as
**multiple returns per beam**: a weak early return from the dust, then a strong late one from the
wall, and past a certain density no late return at all. So the failure has three stages, and they
are all visible:

1. **Haze.** Sparse false points floating in the passage at short range, in front of the true
   walls. The map gains geometry that is not there.
2. **Occlusion.** The far returns thin out and then stop. The passage appears to end. The machine
   believes it is in a shorter room than it is.
3. **Blindness.** Nothing but the near cloud. Odometry is all that is left.

**Where it comes from in the fiction.** A machine's own movement raises silt; the Assayer's strike
shakes fines off every surface (`THE-MACHINERY.md`); water dripping and falling makes mist; a
collapse makes a wall of it. That means dust is partly **self-inflicted and partly an event**,
which is more interesting than a static map property. A machine that hurries blinds itself.

**Why it matters more than it looks:** dust removes exactly the returns that scan matching needs.
It is the natural counter to §3.

---

## 3. Is this SLAM? No. Not remotely, and that is on purpose

> "Is this using SLAM right now? Maybe it's just object avoidance at first and then there is a
> SLAM module they can find in the cave?"

**What the machines do today.** Dead reckoning plus fixes on beacons they dropped themselves.
`phase1/belief/belief.py` integrates odometry into a pose estimate whose uncertainty grows with
distance walked, adds range/bearing returns to a point cloud at that estimated pose, and when it
hears a beacon whose ID it knows and whose position it recorded, applies a rigid correction to
everything placed since the previous fix. `phase1/belief/pose_correction.py` says so in its own
words: *"That is one loop closure of a pose graph, done by hand."*

**The distinction that matters.** The machine localises against **markers it placed and
identifies by name**. It never compares what it is seeing now against what it has seen before.
There is no feature extraction, no data association, no scan matching, no map optimisation. Two
consequences follow directly, and both are load-bearing:

- **The spoof works because nothing checks geometry.** A cloned beacon says a name, the machine
  believes the name, and the map folds. A system that matched what it saw against what it had
  mapped would have a chance of noticing that the room is the wrong shape.
- **Old returns are never re-registered**, which is the entire visual signature in
  `ART-DIRECTION.md` §8.2: the same corridor drawn twice, in two places, with no annotation.

**So "object avoidance first, SLAM as a found module" is exactly right as a reading of where the
game is today**, and it is a strong progression idea. But it needs one guard rail, stated plainly.

### 3.1 The risk: SLAM would delete the game

`DESIGN-PRINCIPLES.md` §2: *"Drift is what makes depth expensive. The tension of the game is
I have something, I am getting lost, do I go one junction further? Any tuning that removes the
possibility of not getting out removes the game."*

A working SLAM removes drift. A machine that can recognise a place it has been, close the loop and
correct itself does not get lost, and the doubled corridors snap together and stop being a
picture. Handed out as a straight upgrade, SLAM is not a new toy; it is an off switch for the
central tension.

### 3.2 The fix, and it is free, because real SLAM fails in exactly the right ways

None of the following is invented for balance. They are the standard failure modes of scan
matching underground, which is why mine and tunnel autonomy is a research problem and not a solved
one.

- **Corridor degeneracy.** A long, straight, uniform passage gives scan matching nothing to lock
  onto *along its own axis*. Every position down the tunnel looks the same, so the estimate is
  well constrained sideways and free to slide lengthwise. SLAM in a featureless drive does almost
  nothing, and the machine still arrives at the far end not knowing how far it has gone. **This
  hands the cave generator a direct lever: a long uniform passage is a place where SLAM stops
  helping, and that is a level design decision rather than a number.**
- **Perceptual aliasing.** Two places that look alike get matched to each other, and the map folds
  in the wrong place with total confidence. A wrong loop closure is *worse than no loop closure*,
  because the machine is now confidently wrong about everything since. This is the same failure
  the spoof already exploits, arrived at honestly. A cave with repeated geometry — the ancients
  built to a pattern — is a cave that induces it.
- **It needs returns, and dust takes them away.** §2 is the natural counter. A machine that
  hurries, or that stands where the Assayer just fired, blinds the thing keeping it found.
- **It costs.** Compute, power, and time. A machine doing this is a machine doing less of
  something else.

### 3.3 What it implies if it is taken up

- **SLAM is a module with real parameters**, like the sensor: how often it attempts a match, how
  far back it will search, how confident it must be to accept one. A cheap one accepts bad matches.
- **A found SLAM module is the strongest possible expression of §2's "the cool things are new
  blocks, and they are found by depth"** — it is not a bigger number, it is a new sense. And the
  moment it first closes a loop and the doubled corridor snaps together is a genuinely dramatic
  image that the game currently has no way of producing.
- **It changes what the player can teach.** A machine with SLAM has predicates the base list does
  not have: *I have been here before*, *my map disagrees with itself*, *my last correction was
  large*. Those are new base blocks in the `DESIGN-PRINCIPLES.md` §1 sense, arriving because a
  module arrived, which is exactly how that principle says content should grow.
- **It gives the rival a new attack.** Inducing a false loop closure in someone else's machine is
  a more sophisticated version of the spoof, and it is available to a player who understands the
  system rather than to one who bought a better part.

---

## 4. What is not decided here

1. The sensor parameters (`DESIGN-PRINCIPLES.md` §8 carries a measured recommendation).
2. Whether water returns at full or low intensity, and whether shallow water shows its bottom.
3. Whether dust is a map property, an event, self-inflicted, or all three.
4. Whether SLAM enters the game at all, and if so whether it is found, bought or built.
5. Whether SLAM predicates are base blocks the player can teach with, or an invisible improvement
   to the estimate.
6. Whether a machine can be *deprived* of SLAM mid-match, which is the difference between a
   capability and a resource.
