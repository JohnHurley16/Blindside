# BLD-64 — Acoustic propagation: model and per-tick budget

Spike report, 2026-09-06. Prototype in `spikes/acoustic/` (scratch Rust, floats allowed, not a
workspace member; nothing in it is sim code). Every number below was produced on this machine
tonight with `cargo build --release`; the commands to regenerate them are in §11.

Machine: Intel i7-11800H (8 cores / 16 threads, 2.3 GHz base), 32 GB, Windows 11, rustc
1.98.1. Timing noise between two runs of the same table is about ±15% on the microsecond
columns; the "worst tick" column of anything under 100 µs is dominated by OS scheduling
noise, and p99 is the robust column there.

---

## 1. The short version

**Recommendation: build the exact model — a range-bounded cell Dijkstra from the emitter,
resumed lazily to the farthest listener that asks, cached for the emission's life — and give
acoustics 10 µs per tick amortised (100 ms per 9,600-tick match) and 2 ms for the worst
single tick.** Not the precomputed passage graph, even though the graph is 100× cheaper.

Measured on the cave I am guessing is the Phase 3 target (400×240 cells, chambers joined by
passages, ~17% free, four agents, Phase 1's ranges and cooldowns): the exact model costs
**9.5 µs per tick mean, 91 ms per match, 1.2 ms worst tick**. With the task's eight agents it
costs 26.6 µs per tick (256 ms per match), which fits only if the batch gate runs matches in
parallel across cores (DETERMINISM rule 5 allows that; 8 cores make the per-tick budget
~500 µs). The graph model costs 0.1–0.3 µs per tick in every configuration measured.

Why the exact model anyway, in one paragraph: the graph model changes what the game says —
it never hears anything the exact model does not, but it fails to hear 13–20% of the
sound/listener pairs the exact model hears (its path is 4–12 cells longer on average, and the
range cut-off is hard), and its bearings differ from the exact model's by 25° on average and
about 60° at the 90th percentile — larger than the whole 4–22° bearing-noise model Phase 1 was
tuned on. It also needs a 6 ms graph rebuild per collapse at 400×240 (28 ms at 800×480), or a
local-rebuild algorithm nobody has written. The exact model has no precomputed state, so a
collapse costs nothing, an echo (BLD-80) is just another emitter, and the determinism story is
one heap ordered by `(cost, cell id)`. Its cost is inside the budget at the agent count the
design actually implies for Phase 3, and there are three cheap levers if it is not (§7).

The two findings that matter beyond the model choice:

1. **Motion noise, not pings, is the cost driver** for the exact model: ~93% of the field
   builds per match are motion-noise fields (one per moving agent per 0.5 s for every listener
   within 40 cells) and they are about two thirds of the time, and their number scales with
   agent density, not cave size. Eight agents on 200×120 cost more than eight agents on
   800×480.
2. **DESIGN's cellular-automata step alone does not produce a passage cave.** At the demo's
   fill (0.45–0.47) it produces an open field 52–61% free with rock islands; at fill 0.52 the
   largest component collapses to a few thousand cells. There is no fill that gives Phase 1's
   shape (16% free, passages 4–6 wide). The generator (BLD-72) has to carve passages between
   CA-shaped chambers; DESIGN's "then carved into a connectivity graph" is load-bearing, not
   decoration. The acoustic cost on the open field is 3–4× the passage cave's.

Questions for the designer, each answerable yes/no, are in §10.

---

## 2. What was asked and what was built

BLD-64 asks for two approaches measured at the target cave size with eight concurrent
emitters, a per-tick budget agreed with the designer, the chosen approach under that budget in
the prototype, and a cache/hash policy for BLD-81. ROADMAP lists "propagation, absorption by
rock type, thermal shadow zones" for Phase 3; this spike covers propagation and range. Rock
absorption is a per-cell cost multiplier in the same loop (flooded cells already are one) and
costs nothing extra; shadow zones (BLD-80) are not modelled here.

### 2.1 The models

All models share: sound travels through free cells (dry or flooded), never rock, with
8-neighbour moves costing 1 (orthogonal) or 1.4142 (diagonal) cells; entering a flooded cell
costs ×0.55 (Phase 1's `FLOODED_COST`, "water carries"); a hard range cut-off in path cells
(Phase 1's 170 for a ping and a crash, 80 for an ancient signature, 40 for motion); and a
Euclidean prefilter — a listener farther than the range as the crow flies cannot be within it
by path, so it is answered without touching the field. Costs are integers in 1/1024-cell
units throughout (the fixed-point port keeps exactly this), so the only float in any model is
the `atan2` that turns the final look-back vector into a bearing.

| model | what it does per emission | what it does per listener | precomputed |
|---|---|---|---|
| **A** — cell Dijkstra, per tick | Dijkstra from the emitter over cells, stopping at the range; rebuilt every tick the emission is sampled | array lookup, walk 5 steps back along the predecessor chain, `atan2` | nothing |
| **A+C** — cached | same build, once, kept for the emission's life (Phase 1 cached ping fields this way) | same | nothing |
| **A-lazy** — resumable, cached | the Dijkstra runs only until the listener asked about is settled; the heap is kept and resumed for the next listener. Dijkstra settles cells in non-decreasing cost, so every answer is exact and independent of the order listeners ask | same | nothing |
| **A (bucket)** — the same three with a Dial bucket queue | integer costs allow a circular array of `max step + 1` buckets in place of the binary heap; O(1) push/pop | same | nothing |
| **B** — passage graph, per tick | Dijkstra over the junction graph only (tens to hundreds of nodes), seeded from the two ends of the emitter's passage | map the listener's cell to its nearest skeleton pixel (precomputed), take the better of the passage's two ends plus both off-skeleton offsets, bearing along the passage | the graph (§2.2) |
| **B+C** — cached | same, once per emission | same | the graph |

"C" in the task's list — per-emitter result caching keyed by emission — is what A+C and B+C
are; the lazy variant is the cheap extra that made the biggest difference to A.

### 2.2 The passage graph (model B) in detail

The free mask is thinned to a one-cell skeleton (Zhang–Suen), made 8-minimal (sequential
deletion of simple points — without this step, Zhang–Suen's staircases merged into
28-pixel "junctions" and the graph's paths came out 60 cells shorter than the true path;
the `probe` command exists because of that bug), spurs shorter than the local half-width are
pruned, skeleton pixels with one or three-plus skeleton neighbours become nodes, and the runs
between nodes become edges carrying a per-pixel cumulative cost. Every free cell is mapped
once to its nearest skeleton pixel with the cost of getting there (8 bytes per cell).

Per emission, a Dijkstra over the node graph bounded by the range. Per listener, the distance
is `off_emitter + graph path + off_listener`, taking the better of the listener's passage's
two ends (or the direct along-passage distance when emitter and listener share a passage).
The graph's path is a real path through free cells, so it can only be longer than the exact
one — after the minimisation fix, B never hears anything A does not (§4.3).

### 2.3 The arrival bearing, per model

Phase 1 defined the bearing as the direction the sound came *in* from: walk five cells back
along the shortest path from the listener and point at that cell, so the bearing points down
the passage rather than at the source through rock. That definition is what the spectator
gate was watched on.

- **A (all variants):** exactly Phase 1's — five steps back along the predecessor chain, then
  `atan2` from the listener to that cell. One `atan2` per heard return, none per cell.
- **B:** from the listener toward the skeleton pixel five pixels along its passage toward the
  end the sound came in by (for a listener sitting on a junction, five pixels into the
  junction's predecessor passage; for a listener on the emitter's own junction, straight at
  the emitter). A look-along proportional to the listener's distance from the skeleton was
  tried and changed the mean error by 0.2°, so it is not in the code.

The two definitions agree exactly on a straight passage with the emitter on its axis and
disagree by 17–39° when the emitter or listener is near a wall or the sound has come round a
bend (§4.4). Neither is physically privileged; §9 says why that matters for BLD-79.

### 2.4 Caves

Two generators, because the task allows either and they answer different questions:

- **`ca`** — DESIGN.html's stated method and its demo's parameters: seeded noise, 45–47%
  initial rock, the 4/5 rule, five iterations, then the largest 8-connected component kept.
  Produces an open field, 52–61% free (Phase 1's cave was 16%). **`cat`** is the same at fill
  0.50, the last fill before the percolation cliff: 8–30% free depending on seed, fragmented.
- **`tree`** — Phase 1's shape scaled by area: 11 lumpy chambers per 24,000 cells (radius
  5–12) joined by bent passages 4–6 wide on a spanning tree plus 30% extra loops. 17–18%
  free at every size.

Both flood ~12% of free cells in random blobs (Phase 1: 460 of 3,831 cells = 12%). Cells are
0 rock / 1 dry / 2 flooded as in Phase 1. Sound moves 8-connected without a corner-cutting
check, as Phase 1's `SoundField` did.

| cave | cells | free | free % | flooded % | median half-width | p90 half-width | skeleton px | nodes | edges | graph build ms (thin/prune/graph/map) |
|---|---|---|---|---|---|---|---|---|---|---|
| tree-200x120-s1 | 24000 | 4437 | 18.5 | 12.5 | 2 | 5 | 460 | 10 | 12 | 1.9 (0.9/0.6/0.0/0.4) |
| tree-400x240-s1 | 96000 | 16767 | 17.5 | 12.2 | 2 | 4 | 1944 | 39 | 51 | 6.0 (2.3/1.9/0.2/1.5) |
| tree-800x480-s1 | 384000 | 66372 | 17.3 | 12.1 | 2 | 5 | 7805 | 138 | 192 | 25.6 (9.8/8.1/1.0/6.5) |
| cat-200x120-s1 | 24000 | 3689 | 15.4 | 12.8 | 2 | 3 | 627 | 47 | 55 | 1.4 (0.5/0.5/0.1/0.3) |
| cat-400x240-s1 | 96000 | 28512 | 29.7 | 12.3 | 2 | 3 | 5118 | 393 | 484 | 8.1 (2.5/2.3/0.5/2.7) |
| cat-800x480-s1 | 384000 | 48844 | 12.7 | 12.1 | 2 | 3 | 8488 | 654 | 808 | 21.9 (7.7/7.6/1.3/5.1) |
| ca-200x120-s1 | 24000 | 13399 | 55.8 | 12.2 | 2 | 3 | 2250 | 163 | 219 | 3.5 (1.3/0.7/0.3/1.2) |
| ca-400x240-s1 | 96000 | 57312 | 59.7 | 12.0 | 2 | 3 | 9962 | 785 | 1089 | 14.6 (4.9/2.9/1.2/5.5) |
| ca-800x480-s1 | 384000 | 231136 | 60.2 | 12.0 | 2 | 3 | 39782 | 3061 | 4301 | 69.9 (26.7/12.7/4.5/25.6) |
| tree-200x120-s2 | 24000 | 3843 | 16.0 | 21.2 | 2 | 4 | 496 | 10 | 13 | 2.0 (1.0/0.7/0.0/0.3) |
| tree-400x240-s2 | 96000 | 16584 | 17.3 | 12.5 | 2 | 5 | 1903 | 39 | 52 | 6.9 (2.8/2.2/0.3/1.5) |
| tree-800x480-s2 | 384000 | 66964 | 17.4 | 12.3 | 2 | 5 | 7552 | 154 | 209 | 24.5 (9.1/8.0/0.9/6.3) |
| cat-200x120-s2 | 24000 | 1804 | 7.5 | 14.4 | 2 | 3 | 272 | 20 | 21 | 1.0 (0.3/0.4/0.1/0.2) |
| cat-400x240-s2 | 96000 | 11693 | 12.2 | 13.1 | 2 | 3 | 2177 | 175 | 214 | 5.4 (1.7/2.0/0.3/1.3) |
| cat-800x480-s2 | 384000 | 107859 | 28.1 | 12.1 | 2 | 3 | 19157 | 1502 | 1840 | 33.8 (10.9/9.5/2.1/11.1) |
| ca-200x120-s2 | 24000 | 12356 | 51.5 | 14.1 | 2 | 3 | 1965 | 137 | 181 | 3.0 (1.0/0.6/0.2/1.1) |
| ca-400x240-s2 | 96000 | 55329 | 57.6 | 12.4 | 2 | 3 | 9576 | 753 | 1033 | 15.2 (5.6/2.9/1.0/5.5) |
| ca-800x480-s2 | 384000 | 233674 | 60.9 | 12.0 | 2 | 3 | 39985 | 3107 | 4349 | 62.6 (21.8/11.7/4.3/24.6) |

The CA fill sweep at 400×240 (seeds 1 and 2): fill 0.50 → 29.7% / 12.2% free; 0.52 → 5.0% /
3.9%; 0.53 → 2.8% / 1.4%; 0.54 → 0.9% / 1.1%. That is the percolation cliff.

`tree-200x120-s1`, one character per 2×4 cells, `~` flooded:

```
####################################################################################################
####################################################################################################
####################################################################################################
####################################################################################################
########################################################################~~~~~      #################
#######################################################################~~~~~~~     #################
####################        ###########################################~~~~~~~     #################
##################           ####################        ############  ~~~~~~      #################
##################          #####################        ####            #        ##################
####################        ####################                     ######     ####################
###################        ####################             ########################################
##################     #########################           #########################################
#################     ###########################       ############################################
##############      ###########################     ##   ###########################################
#####              ##########################      ###   ###########################################
####            ##########################       ######   #################################    #####
#####         ############################       ######   ###############################       ####
#####           ###########################       #####   ##############################           #
#####              ########################        ####   #############################            #
########    ##       #####################    ##          ##########################               #
#########    ####     ####################    ###            ###################                   #
#########    #####     ###################  ~~#######           ##############      #####   ### ####
########    #######     ################## ~~~#####                ~~#~~         ###################
######      ########        ###############~~~~##      #######    ~~~~~~~      #####################
####       ########~~~                    #~~~~~~~   ##############~~~~~~       ####################
###        ~~~####~~~~~  ~~~~~~           ~~~~~~~  ##################~~        #####################
####       ~~~~~~~~~~~~ ~~~~~~########            ####################      ########################
######    #####~~###~~  ~~~~~##############      ###################################################
############################################  ######################################################
####################################################################################################
```

### 2.5 The target cave size — a guess

No document states one. DESIGN.html's generator demo is 100×40; ROADMAP and the Phase 3
stories say "target cave size" without a number; Phase 1 was hand-authored at 200×120 for two
agents, and an agent at 1.1 cells/s covers ~530 cells in an 8-minute match. **Guess: 400×240**
— four teams with shafts on the perimeter and "rough parity of total worth per region"
(DESIGN) reads as roughly one Phase-1-sized region per team, which is 4× the area. All three
sizes (200×120, 400×240, 800×480) were measured so the guess can be corrected without
re-running anything.

### 2.6 The emitter load

Replayed identically through every model so the numbers compare. Per match of 9,600 ticks
(8 minutes at 20 Hz — Phase 1's `MATCH_SECONDS` and `TICK_HZ`; the Phase 3 gate arithmetic
in BLD-109 uses the same count):

| source | how many | range | audible | listeners sample it |
|---|---|---|---|---|
| sonar ping | 8 agents, half on the 8 s aggressive cooldown, half on 24 s cautious, ±10% jitter: **318–321 pings per match** | 170 | 60 ticks | every 10 ticks (Phase 1's `tick % 10`), all other agents |
| motion noise | every agent, every 10 ticks (`MOTION_LISTEN_PERIOD` 0.5 s): **7,680 per match** | 40 | 1 tick | once, only listeners within 40 cells as the crow flies (Phase 1's prefilter) |
| ancient signature | 2 static machines on Phase 1's 75 s cycle, audible 13 s of it (9 s warning + 4 s lethal): **12 windows per match** | 80 | 260 ticks | every 5 ticks, all agents |
| crash | 4 per match at random ticks and agent positions | 170 | 1 tick | once, all agents |
| echo (BLD-80) | 0 by default; the sensitivity run adds one per ping from a random free cell 20 ticks later | 170 | 60 ticks | as a ping |

Agents random-walk the cave: each picks a random walkable cell, follows a BFS path at Phase 1's
speeds (1.4 cells/s aggressive, 1.1 cautious), picks another on arrival, and never stops. That
is the worst case for motion noise (real agents dwell at deposits and shafts) and spreads them
uniformly (real agents cluster, which raises hearing rates but not per-emission cost). Both are
guesses; both are pessimistic for the totals and neutral for the per-emission costs.

Per tick, the timed block covers: registering new emissions, iterating live ones, every
listener query (prefilter, build or resume, lookup, bearing), and releasing expired fields.
After the match a random 4-cell-radius collapse is applied and what the model does about it
is timed separately.

---

## 3. Phase 1's Python baseline on this machine

For scale. `phase1/sensing/sound_field.py` at 200×120 (3,831 free cells), 40 random emitters:

| field | build ms mean | max | cells reached |
|---|---|---|---|
| ping, range 170 | 12.5 | 17.8 | 3,753 (the whole cave) |
| ancient, range 80 | 9.3 | 20.8 | 2,259 |
| motion, range 40 | 3.5 | 8.0 | 904 |

That is 3.3 µs per cell in Python against 48 ns per cell in the Rust prototype (§4.1):
about 70×. The 33 ms worst tick in the story is two of these in one tick. Note that at 170
cells Phase 1's ping is basin-wide on its cave; on 400×240 the same range reaches ~40% of the
free cells, so "every listener in the basin hears it" (DESIGN) stops being literally true
(§10, Q5).

---

## 4. Results

### 4.1 Cost per emission, by range (200 random emitters, idle machine)

`tree-400x240-s1` (16,767 free cells; graph 39 nodes, 51 edges):

| range | A heap build µs mean | max | A bucket build µs mean | max | cells reached mean | max | B build µs mean | max | nodes popped mean | A lookup µs | B lookup µs |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 170 | 321.4 | 790.2 | 295.0 | 677.0 | 6611 | 9933 | 1.28 | 15.00 | 15 | 0.029 | 0.066 |
| 80 | 117.4 | 209.7 | 109.5 | 182.6 | 2410 | 4124 | 0.93 | 13.60 | 6 | 0.012 | 0.053 |
| 40 | 45.0 | 102.1 | 43.6 | 102.2 | 935 | 2086 | 0.54 | 15.50 | 3 | 0.023 | 0.051 |
| 20 | 18.4 | 48.9 | 18.2 | 43.2 | 390 | 708 | 0.22 | 7.40 | 2 | 0.006 | 0.038 |

`cat-400x240-s1` (28,512 free cells; 393 nodes, 484 edges):

| range | A heap build µs mean | max | A bucket build µs mean | max | cells reached mean | max | B build µs mean | max | nodes popped mean | A lookup µs | B lookup µs |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 170 | 583.7 | 1010.5 | 514.5 | 979.1 | 10994 | 17508 | 6.16 | 21.30 | 129 | 0.025 | 0.075 |
| 80 | 173.3 | 389.1 | 159.6 | 395.0 | 3412 | 7001 | 2.35 | 13.20 | 39 | 0.009 | 0.067 |
| 40 | 58.5 | 136.2 | 56.0 | 117.4 | 1164 | 2314 | 0.97 | 8.80 | 13 | 0.008 | 0.061 |
| 20 | 19.7 | 57.0 | 19.6 | 54.7 | 402 | 917 | 0.33 | 3.60 | 5 | 0.005 | 0.050 |

`ca-400x240-s1` (57,312 free cells, the open field; 785 nodes, 1,089 edges):

| range | A heap build µs mean | max | A bucket build µs mean | max | cells reached mean | max | B build µs mean | max | nodes popped mean | A lookup µs | B lookup µs |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 170 | 1581.6 | 2575.6 | 1256.4 | 2263.7 | 27135 | 42662 | 17.57 | 44.20 | 344 | 0.037 | 0.158 |
| 80 | 446.7 | 886.7 | 369.2 | 811.1 | 7537 | 12586 | 6.09 | 29.30 | 87 | 0.013 | 0.124 |
| 40 | 113.0 | 324.9 | 100.1 | 350.5 | 2013 | 3399 | 2.09 | 17.80 | 22 | 0.011 | 0.105 |
| 20 | 29.8 | 79.8 | 28.2 | 72.8 | 575 | 1171 | 0.79 | 12.70 | 6 | 0.007 | 0.092 |

`tree-800x480-s1` (66,372 free cells; 138 nodes, 192 edges):

| range | A heap build µs mean | max | A bucket build µs mean | max | cells reached mean | max | B build µs mean | max | nodes popped mean | A lookup µs | B lookup µs |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 170 | 358.4 | 687.0 | 325.3 | 703.9 | 6882 | 11396 | 1.59 | 14.40 | 14 | 0.041 | 0.107 |
| 80 | 135.5 | 422.8 | 124.8 | 326.0 | 2565 | 4996 | 1.02 | 16.70 | 6 | 0.014 | 0.084 |
| 40 | 50.2 | 124.8 | 47.7 | 107.8 | 984 | 2211 | 0.60 | 15.20 | 3 | 0.009 | 0.071 |
| 20 | 19.4 | 55.0 | 19.1 | 52.2 | 402 | 886 | 0.29 | 6.00 | 2 | 0.008 | 0.060 |

`tree-200x120-s1` (4,437 free cells; 10 nodes, 12 edges):

| range | A heap build µs mean | max | A bucket build µs mean | max | cells reached mean | max | B build µs mean | max | nodes popped mean | A lookup µs | B lookup µs |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 170 | 199.6 | 267.7 | 191.8 | 280.2 | 4022 | 4437 | 0.71 | 14.30 | 9 | 0.059 | 0.086 |
| 80 | 106.1 | 245.2 | 101.1 | 203.8 | 2034 | 3039 | 0.59 | 16.40 | 4 | 0.033 | 0.051 |
| 40 | 46.8 | 174.7 | 44.9 | 139.7 | 923 | 1468 | 0.31 | 16.50 | 3 | 0.015 | 0.037 |
| 20 | 19.9 | 76.1 | 18.9 | 73.1 | 406 | 553 | 0.15 | 6.60 | 2 | 0.009 | 0.026 |

What these say:

- Model A costs **~48 ns per cell reached**, and cells reached is set by the range and the
  local openness, not by the cave size: a 170-cell ping costs the same 320–360 µs on
  tree-400×240 and tree-800×480. On the open field it reaches 4× the cells and costs 5×.
  Phase 1's Python worst case was about Python, not about the algorithm.
- The bucket queue is **8–20% faster** than the binary heap. The heap is not the bottleneck;
  memory traffic over `dist`/`state`/`pred` is.
- Model B's per-emission cost is **1–18 µs**, dominated by fixed overhead at these graph
  sizes (15 nodes popped on the tree cave). Its lookup is 2× A's (0.07 vs 0.03 µs); both are
  irrelevant.

### 4.2 Cost per tick under the Phase 3 load (three seeds, 8 agents)

Mean of the per-tick means across seeds; worst is the worst tick of any seed. Memory is the
model's resident bytes at the end of the match (A: one slot per concurrently live emission;
B: graph plus per-emission node arrays). Collapse is what the model does when a 4-cell-radius
collapse lands (A: drop live fields; B: rebuild the graph).

| cave (seeds) | free cells | model | mean µs/tick | p99 µs | worst µs | total ms/match | builds/match | heard/listens | memory KB | collapse ms |
|---|---|---|---|---|---|---|---|---|---|---|
| tree-200x120 (3) | 4151 | A cell Dijkstra (heap), per tick | 89.03 | 1269.5 | 2928 | 854.7 | 8769 | 28005/72154 | 2584 | 0.00 |
| tree-200x120 (3) | 4151 | A+C cell Dijkstra (heap), cached | 40.91 | 608.0 | 1505 | 392.7 | 6566 | 28005/72154 | 2579 | 0.01 |
| tree-200x120 (3) | 4151 | A-lazy resumable (heap), cached | 28.97 | 471.7 | 1160 | 278.1 | 6566 | 28005/72154 | 2568 | 0.01 |
| tree-200x120 (3) | 4151 | A+C cell Dijkstra (bucket), cached | 38.71 | 573.1 | 1397 | 371.7 | 6566 | 27937/72154 | 2459 | 0.01 |
| tree-200x120 (3) | 4151 | A-lazy resumable (bucket), cached | 29.15 | 474.6 | 1301 | 279.8 | 6566 | 27937/72154 | 2448 | 0.01 |
| tree-200x120 (3) | 4151 | B graph Dijkstra, per tick | 0.37 | 4.4 | 22 | 3.5 | 8769 | 24614/72154 | 227 | 1.57 |
| tree-200x120 (3) | 4151 | B+C graph Dijkstra, cached | 0.31 | 3.6 | 22 | 2.9 | 6566 | 24614/72154 | 227 | 1.71 |
| tree-400x240 (3) | 16491 | A cell Dijkstra (heap), per tick | 131.51 | 2073.8 | 4205 | 1262.5 | 6767 | 13583/72110 | 7389 | 0.00 |
| tree-400x240 (3) | 16491 | A+C cell Dijkstra (heap), cached | 45.87 | 917.5 | 9656 | 440.4 | 4648 | 13583/72110 | 7389 | 0.02 |
| tree-400x240 (3) | 16491 | A-lazy resumable (heap), cached | 26.63 | 613.0 | 1873 | 255.6 | 4648 | 13583/72110 | 7352 | 0.02 |
| tree-400x240 (3) | 16491 | A+C cell Dijkstra (bucket), cached | 35.34 | 688.9 | 1991 | 339.3 | 4648 | 13561/72110 | 7284 | 0.02 |
| tree-400x240 (3) | 16491 | A-lazy resumable (bucket), cached | 24.29 | 552.7 | 1521 | 233.2 | 4648 | 13561/72110 | 7247 | 0.02 |
| tree-400x240 (3) | 16491 | B graph Dijkstra, per tick | 0.26 | 3.4 | 24 | 2.5 | 6767 | 11730/72110 | 825 | 6.40 |
| tree-400x240 (3) | 16491 | B+C graph Dijkstra, cached | 0.22 | 2.9 | 20 | 2.1 | 4648 | 11730/72110 | 825 | 6.33 |
| tree-800x480 (3) | 66975 | A cell Dijkstra (heap), per tick | 88.66 | 1633.9 | 3606 | 851.2 | 3689 | 4109/72143 | 20151 | 0.00 |
| tree-800x480 (3) | 66975 | A+C cell Dijkstra (heap), cached | 25.06 | 651.3 | 2197 | 240.6 | 2321 | 4109/72143 | 20145 | 0.02 |
| tree-800x480 (3) | 66975 | A-lazy resumable (heap), cached | 15.92 | 515.5 | 2082 | 152.9 | 2321 | 4109/72143 | 20145 | 0.01 |
| tree-800x480 (3) | 66975 | A+C cell Dijkstra (bucket), cached | 22.14 | 580.2 | 1658 | 212.5 | 2321 | 4102/72143 | 20067 | 0.02 |
| tree-800x480 (3) | 66975 | A-lazy resumable (bucket), cached | 14.69 | 464.2 | 1922 | 141.0 | 2321 | 4102/72143 | 20067 | 0.02 |
| tree-800x480 (3) | 66975 | B graph Dijkstra, per tick | 0.20 | 2.6 | 23 | 1.9 | 3689 | 3619/72143 | 3219 | 27.04 |
| tree-800x480 (3) | 66975 | B+C graph Dijkstra, cached | 0.16 | 2.1 | 22 | 1.6 | 2321 | 3619/72143 | 3219 | 28.13 |
| cat-200x120 (3) | 3665 | A cell Dijkstra (heap), per tick | 109.61 | 1418.0 | 2564 | 1052.2 | 10123 | 41161/72147 | 2756 | 0.00 |
| cat-200x120 (3) | 3665 | A+C cell Dijkstra (heap), cached | 67.12 | 898.7 | 2350 | 644.4 | 7922 | 41161/72147 | 2756 | 0.01 |
| cat-200x120 (3) | 3665 | A-lazy resumable (heap), cached | 56.03 | 757.5 | 1610 | 537.9 | 7922 | 41161/72147 | 2751 | 0.01 |
| cat-200x120 (3) | 3665 | A+C cell Dijkstra (bucket), cached | 61.42 | 809.6 | 1604 | 589.6 | 7922 | 41101/72147 | 2627 | 0.01 |
| cat-200x120 (3) | 3665 | A-lazy resumable (bucket), cached | 52.63 | 706.2 | 1413 | 505.2 | 7922 | 41101/72147 | 2622 | 0.01 |
| cat-200x120 (3) | 3665 | B graph Dijkstra, per tick | 0.81 | 10.4 | 40 | 7.8 | 10123 | 36183/72147 | 239 | 1.46 |
| cat-200x120 (3) | 3665 | B+C graph Dijkstra, cached | 0.70 | 8.9 | 34 | 6.7 | 7922 | 36183/72147 | 239 | 1.67 |
| cat-400x240 (3) | 18187 | A cell Dijkstra (heap), per tick | 180.02 | 2806.2 | 5484 | 1728.2 | 7896 | 17227/72119 | 8170 | 0.00 |
| cat-400x240 (3) | 18187 | A+C cell Dijkstra (heap), cached | 65.06 | 1248.5 | 4014 | 624.6 | 5697 | 17227/72119 | 8133 | 0.02 |
| cat-400x240 (3) | 18187 | A-lazy resumable (heap), cached | 49.42 | 1054.2 | 3034 | 474.4 | 5697 | 17227/72119 | 8133 | 0.02 |
| cat-400x240 (3) | 18187 | A+C cell Dijkstra (bucket), cached | 59.75 | 1122.4 | 2912 | 573.6 | 5697 | 17183/72119 | 8019 | 0.02 |
| cat-400x240 (3) | 18187 | A-lazy resumable (bucket), cached | 58.12 | 1226.8 | 5432 | 558.0 | 5697 | 17183/72119 | 8019 | 0.04 |
| cat-400x240 (3) | 18187 | B graph Dijkstra, per tick | 1.92 | 28.4 | 586 | 18.4 | 7896 | 14228/72119 | 900 | 15.80 |
| cat-400x240 (3) | 18187 | B+C graph Dijkstra, cached | 1.27 | 18.6 | 2544 | 12.1 | 5697 | 14228/72119 | 900 | 11.43 |
| cat-800x480 (3) | 81235 | A cell Dijkstra (heap), per tick | 188.05 | 3283.6 | 7368 | 1805.3 | 4082 | 4053/72194 | 21928 | 0.00 |
| cat-800x480 (3) | 81235 | A+C cell Dijkstra (heap), cached | 47.91 | 1158.2 | 3534 | 459.9 | 2393 | 4053/72194 | 21928 | 0.02 |
| cat-800x480 (3) | 81235 | A-lazy resumable (heap), cached | 35.43 | 985.4 | 3418 | 340.2 | 2393 | 4053/72194 | 21901 | 0.03 |
| cat-800x480 (3) | 81235 | A+C cell Dijkstra (bucket), cached | 40.74 | 982.9 | 3136 | 391.1 | 2393 | 4042/72194 | 21844 | 0.03 |
| cat-800x480 (3) | 81235 | A-lazy resumable (bucket), cached | 29.71 | 809.6 | 3004 | 285.2 | 2393 | 4042/72194 | 21817 | 0.02 |
| cat-800x480 (3) | 81235 | B graph Dijkstra, per tick | 0.96 | 16.8 | 126 | 9.2 | 4082 | 3230/72194 | 3536 | 29.47 |
| cat-800x480 (3) | 81235 | B+C graph Dijkstra, cached | 0.43 | 9.4 | 31 | 4.2 | 2393 | 3230/72194 | 3536 | 29.56 |
| ca-200x120 (3) | 13125 | A cell Dijkstra (heap), per tick | 243.73 | 3612.5 | 6311 | 2339.8 | 9013 | 27124/72129 | 3103 | 0.00 |
| ca-200x120 (3) | 13125 | A+C cell Dijkstra (heap), cached | 100.86 | 1658.8 | 4508 | 968.3 | 6813 | 27124/72129 | 3060 | 0.02 |
| ca-200x120 (3) | 13125 | A-lazy resumable (heap), cached | 74.90 | 1285.2 | 3435 | 719.1 | 6813 | 27124/72129 | 3055 | 0.01 |
| ca-200x120 (3) | 13125 | A+C cell Dijkstra (bucket), cached | 87.98 | 1451.6 | 3342 | 844.5 | 6813 | 27085/72129 | 2931 | 0.02 |
| ca-200x120 (3) | 13125 | A-lazy resumable (bucket), cached | 67.17 | 1165.1 | 2687 | 644.9 | 6813 | 27085/72129 | 2926 | 0.02 |
| ca-200x120 (3) | 13125 | B graph Dijkstra, per tick | 1.40 | 22.3 | 64 | 13.5 | 9013 | 23660/72129 | 300 | 3.56 |
| ca-200x120 (3) | 13125 | B+C graph Dijkstra, cached | 0.77 | 13.0 | 50 | 7.4 | 6813 | 23660/72129 | 300 | 3.42 |
| ca-400x240 (3) | 56878 | A cell Dijkstra (heap), per tick | 521.11 | 8800.6 | 46543 | 5002.6 | 5517 | 12464/72150 | 8648 | 0.00 |
| ca-400x240 (3) | 56878 | A+C cell Dijkstra (heap), cached | 130.14 | 3240.4 | 10621 | 1249.3 | 3581 | 12464/72150 | 8648 | 0.05 |
| ca-400x240 (3) | 56878 | A-lazy resumable (heap), cached | 88.53 | 2507.6 | 6935 | 849.9 | 3581 | 12464/72150 | 8648 | 0.05 |
| ca-400x240 (3) | 56878 | A+C cell Dijkstra (bucket), cached | 89.31 | 2136.4 | 6057 | 857.4 | 3581 | 12416/72150 | 8543 | 0.05 |
| ca-400x240 (3) | 56878 | A-lazy resumable (bucket), cached | 64.27 | 1777.5 | 5372 | 617.0 | 3581 | 12416/72150 | 8543 | 0.04 |
| ca-400x240 (3) | 56878 | B graph Dijkstra, per tick | 3.07 | 54.2 | 128 | 29.4 | 5517 | 10055/72150 | 1150 | 15.45 |
| ca-400x240 (3) | 56878 | B+C graph Dijkstra, cached | 1.02 | 24.7 | 90 | 9.8 | 3581 | 10055/72150 | 1150 | 15.49 |
| ca-800x480 (3) | 232455 | A cell Dijkstra (heap), per tick | 546.83 | 9748.5 | 26277 | 5249.6 | 3236 | 4481/72152 | 21223 | 0.00 |
| ca-800x480 (3) | 232455 | A+C cell Dijkstra (heap), cached | 113.31 | 3650.3 | 11738 | 1087.8 | 1764 | 4481/72152 | 21223 | 0.06 |
| ca-800x480 (3) | 232455 | A-lazy resumable (heap), cached | 71.95 | 2611.8 | 7895 | 690.7 | 1764 | 4481/72152 | 21175 | 0.06 |
| ca-800x480 (3) | 232455 | A+C cell Dijkstra (bucket), cached | 88.52 | 2770.3 | 9316 | 849.8 | 1764 | 4469/72152 | 21145 | 0.07 |
| ca-800x480 (3) | 232455 | A-lazy resumable (bucket), cached | 59.71 | 2101.1 | 6486 | 573.1 | 1764 | 4469/72152 | 21097 | 0.06 |
| ca-800x480 (3) | 232455 | B graph Dijkstra, per tick | 3.53 | 66.1 | 163 | 33.9 | 3236 | 3676/72152 | 4446 | 72.84 |
| ca-800x480 (3) | 232455 | B+C graph Dijkstra, cached | 1.02 | 29.8 | 141 | 9.8 | 1764 | 3676/72152 | 4446 | 70.40 |

Reading the table:

- **Builds per match are almost all motion noise.** 4,648 builds on tree-400×240 against
  ~320 pings, 12 ancient windows and 4 crashes; the rest are motion emissions that had a
  listener within 40 cells. Their count falls with cave size because agents spread out
  (6,566 → 4,648 → 2,321 across the three tree sizes), which is why the exact model gets
  *cheaper* per tick on the bigger cave.
- **Lazy resume is the cheap extra that matters:** A-lazy costs 58–71% of A+C on the tree
  caves because a motion field stops at its listener instead of filling the 40-cell disc,
  and a ping's field stops at the farthest listener asked. A+C in turn is a third to a half
  of A per-tick, which is what Phase 1 did for motion (a new `SoundField` per listener pair
  every half second).
- **Open caves cost 3–4× passage caves** under the same load (ca vs tree at 400×240:
  88.5 vs 26.6 µs per tick), because a 170-cell disc on an open field holds 27k cells.
- **The graph model is 70–120× cheaper everywhere** (0.2–1.3 µs per tick), and its per-tick
  worst case is the graph rebuild after a collapse, not any emission.
- **Heard counts differ between A and B** (13,583 vs 11,730 on tree-400×240, 14% fewer for
  B) — the fidelity gap of §4.3, seen under the real load. A and A-lazy hear identically
  (the first cut of the lazy variant did not — it returned before expanding the settled
  target, and heard 0.3% fewer; the fix is in the code with the reason).
- The 9,656 µs worst tick for A+C heap on tree-400×240 and the 2,544 µs one for B+C on
  cat-400×240 are single ticks in one seed each, out of line with their p99 by 10–100×;
  those are the OS, not the model.

### 4.3 What the passage graph gets wrong (B against A, 1,000 random pairs per row)

Pairs are random walkable emitter/listener cells within the range as the crow flies. "dd" is
B's path length minus A's (always ≥ 0 after the minimisation fix). Bearing error is the
absolute difference between the two models' bearings; the last three columns split it by how
far the listener sits from the skeleton.

| cave | range | pairs in Euclid range | A hears | B hears | both | B misses | B false | mean dd cells | p90 dd | max dd | mean bearing err deg | p90 | max | bearing err by listener offset: <=1 cell (n) | 2-3 (n) | >=4 (n) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| tree-200x120-s1 | 170 | 1000 | 908 | 811 | 811 | 97 | 0 | 12.62 | 23.34 | 33.37 | 24.2 | 54.5 | 177.5 | 26.3 (333) | 25.5 (237) | 20.1 (241) |
| tree-200x120-s1 | 80 | 1000 | 703 | 599 | 599 | 104 | 0 | 7.48 | 13.68 | 19.99 | 25.7 | 56.9 | 173.7 | 25.8 (237) | 27.7 (179) | 23.6 (183) |
| tree-200x120-s1 | 40 | 1000 | 914 | 718 | 718 | 196 | 0 | 4.92 | 10.07 | 19.31 | 25.3 | 56.3 | 168.7 | 24.5 (310) | 27.6 (232) | 23.7 (176) |
| tree-400x240-s1 | 170 | 1000 | 683 | 594 | 594 | 89 | 0 | 11.90 | 20.41 | 32.34 | 25.5 | 59.0 | 180.0 | 24.9 (254) | 27.8 (206) | 22.9 (134) |
| tree-400x240-s1 | 80 | 1000 | 692 | 605 | 605 | 87 | 0 | 6.79 | 13.74 | 23.68 | 25.9 | 59.0 | 170.8 | 27.3 (287) | 25.3 (186) | 23.6 (132) |
| tree-400x240-s1 | 40 | 1000 | 870 | 699 | 699 | 171 | 0 | 4.46 | 8.83 | 24.97 | 27.0 | 61.9 | 139.4 | 25.2 (314) | 30.4 (224) | 25.8 (161) |
| tree-800x480-s1 | 170 | 1000 | 513 | 445 | 445 | 68 | 0 | 12.05 | 21.13 | 38.44 | 28.6 | 66.8 | 178.2 | 28.6 (214) | 28.7 (146) | 28.6 (85) |
| tree-800x480-s1 | 80 | 1000 | 706 | 590 | 590 | 116 | 0 | 7.36 | 13.21 | 27.09 | 26.3 | 59.0 | 166.0 | 26.1 (282) | 28.2 (195) | 23.4 (113) |
| tree-800x480-s1 | 40 | 855 | 718 | 543 | 543 | 175 | 0 | 4.89 | 9.55 | 23.90 | 28.6 | 62.7 | 177.5 | 27.4 (263) | 32.3 (172) | 25.4 (108) |
| cat-200x120-s1 | 170 | 1000 | 1000 | 1000 | 1000 | 0 | 0 | 14.53 | 23.97 | 38.32 | 28.7 | 64.4 | 170.5 | 32.1 (589) | 26.7 (320) | 14.0 (91) |
| cat-200x120-s1 | 80 | 1000 | 891 | 651 | 651 | 240 | 0 | 9.98 | 17.65 | 25.91 | 29.6 | 67.4 | 180.0 | 31.1 (389) | 30.3 (205) | 17.0 (57) |
| cat-200x120-s1 | 40 | 1000 | 658 | 482 | 482 | 176 | 0 | 4.69 | 9.07 | 15.36 | 26.2 | 63.4 | 157.6 | 28.5 (316) | 23.1 (133) | 16.4 (33) |
| cat-400x240-s1 | 170 | 1000 | 579 | 466 | 466 | 113 | 0 | 15.27 | 25.28 | 39.42 | 30.9 | 71.6 | 173.7 | 31.5 (294) | 31.7 (150) | 18.2 (22) |
| cat-400x240-s1 | 80 | 1000 | 531 | 400 | 400 | 131 | 0 | 7.89 | 13.66 | 22.59 | 28.4 | 68.2 | 180.0 | 30.1 (247) | 27.3 (123) | 19.3 (30) |
| cat-400x240-s1 | 40 | 1000 | 547 | 391 | 391 | 156 | 0 | 4.61 | 8.83 | 15.48 | 30.0 | 65.2 | 163.1 | 31.1 (254) | 29.7 (120) | 17.4 (17) |
| cat-800x480-s1 | 170 | 1000 | 537 | 431 | 431 | 106 | 0 | 15.41 | 25.07 | 35.08 | 31.3 | 76.0 | 166.0 | 32.3 (259) | 31.3 (137) | 24.8 (35) |
| cat-800x480-s1 | 80 | 1000 | 529 | 424 | 424 | 105 | 0 | 8.13 | 14.14 | 22.71 | 29.4 | 68.2 | 176.6 | 32.1 (266) | 25.6 (132) | 20.9 (26) |
| cat-800x480-s1 | 40 | 1000 | 581 | 420 | 419 | 162 | 1 | 5.01 | 9.07 | 16.90 | 31.6 | 74.7 | 149.0 | 30.7 (256) | 35.2 (134) | 22.3 (29) |
| ca-200x120-s1 | 170 | 1000 | 888 | 775 | 775 | 113 | 0 | 16.92 | 28.66 | 41.59 | 34.7 | 85.2 | 168.7 | 36.6 (450) | 35.5 (254) | 19.7 (71) |
| ca-200x120-s1 | 80 | 1000 | 655 | 529 | 529 | 126 | 0 | 8.42 | 14.90 | 25.21 | 32.1 | 71.6 | 175.6 | 32.0 (316) | 34.0 (175) | 23.6 (38) |
| ca-200x120-s1 | 40 | 1000 | 669 | 498 | 498 | 171 | 0 | 5.13 | 9.07 | 21.31 | 36.3 | 78.7 | 173.7 | 39.2 (294) | 34.0 (158) | 25.4 (46) |
| ca-400x240-s1 | 170 | 1000 | 849 | 684 | 684 | 165 | 0 | 14.82 | 23.30 | 33.56 | 38.7 | 92.7 | 180.0 | 37.6 (431) | 43.6 (218) | 20.9 (35) |
| ca-400x240-s1 | 80 | 1000 | 732 | 537 | 537 | 195 | 0 | 8.57 | 14.83 | 28.55 | 38.5 | 90.0 | 180.0 | 38.9 (341) | 39.9 (165) | 26.2 (31) |
| ca-400x240-s1 | 40 | 1000 | 696 | 497 | 495 | 201 | 2 | 5.32 | 9.90 | 20.73 | 38.5 | 90.0 | 173.7 | 38.4 (332) | 41.3 (130) | 28.0 (33) |
| ca-800x480-s1 | 170 | 1000 | 802 | 616 | 616 | 186 | 0 | 16.51 | 26.38 | 42.09 | 36.4 | 78.7 | 172.9 | 35.2 (377) | 40.0 (200) | 29.8 (39) |
| ca-800x480-s1 | 80 | 1000 | 667 | 490 | 490 | 177 | 0 | 9.06 | 15.24 | 23.55 | 35.9 | 78.7 | 171.9 | 36.4 (301) | 37.6 (155) | 24.1 (34) |
| ca-800x480-s1 | 40 | 1000 | 432 | 296 | 296 | 136 | 0 | 5.22 | 9.35 | 20.14 | 35.6 | 78.1 | 156.8 | 38.0 (188) | 33.7 (89) | 21.6 (19) |

On the passage caves B's path is 12 cells longer on average at range 170 (7 at 80, 4.5 at
40), so 10–20% of the pairs the exact model hears fall past the hard cut-off for B; the three
"B false" cases in 27,000 pairs are residual 2–3-pixel junction clusters. The bearing
difference is 24–29° mean, 55–67° p90 on the tree caves and is **the same for listeners on
the skeleton as off it**, so it is not an off-skeleton artefact; §4.4 shows what it is.

### 4.4 Where the two bearings come apart (hand-built fixture)

An 80×60 fixture with a straight corridor and an L-bend, both 5 cells wide. Bearings in world
degrees, from the listener toward where the sound came from.

| case | emitter | listener | A dist | A bearing deg | B dist | B bearing deg | bearing diff |
|---|---|---|---|---|---|---|---|
| straight, emitter mid-passage | (8,7) | (30,7) | 22.0 | 180 | 22.0 | 180 | 0 |
| straight, emitter mid-passage | (8,7) | (60,7) | 52.0 | 180 | 52.0 | 180 | 0 |
| straight, emitter mid-passage | (8,7) | (60,5) | 52.8 | 158 | 54.0 | 158 | 0 |
| straight, emitter mid-passage | (8,7) | (60,9) | 52.8 | -158 | 54.0 | -158 | 0 |
| straight, emitter on wall | (8,5) | (30,7) | 22.8 | -158 | 24.0 | 180 | 22 |
| straight, emitter on wall | (8,5) | (60,9) | 53.7 | -141 | 56.0 | -158 | 17 |
| L-bend, emitter at the far end of the x leg | (8,32) | (30,32) | 22.0 | 180 | 22.0 | 180 | 0 |
| L-bend, emitter at the far end of the x leg | (8,32) | (38,32) | 30.0 | 180 | 31.4 | 180 | 0 |
| L-bend, emitter at the far end of the x leg | (8,32) | (38,25) | 34.1 | 121 | 36.4 | 90 | 31 |
| L-bend, emitter at the far end of the x leg | (8,32) | (38,15) | 44.1 | 112 | 46.4 | 90 | 22 |
| L-bend, emitter at the far end of the x leg | (8,32) | (40,15) | 44.9 | 129 | 48.4 | 112 | 17 |
| L-bend, emitter at the far end of the x leg | (8,32) | (36,15) | 43.2 | 90 | 48.4 | 68 | 22 |
| L-bend, emitter up the y leg | (38,14) | (38,28) | 14.0 | -90 | 14.0 | -90 | 0 |
| L-bend, emitter up the y leg | (38,14) | (30,32) | 23.1 | -22 | 25.4 | 0 | 22 |
| L-bend, emitter up the y leg | (38,14) | (10,32) | 43.1 | -22 | 45.4 | 0 | 22 |
| L-bend, emitter up the y leg | (38,14) | (10,30) | 42.2 | 0 | 47.4 | 22 | 22 |
| L-bend, emitter up the y leg | (38,14) | (10,34) | 43.9 | -39 | 47.4 | -22 | 17 |

The two models are identical on a straight passage with the source on the axis. They differ
when the shortest path is not the passage axis: with the emitter on a wall the taut-string
path crosses the passage diagonally and A's five-cell look-back reports that diagonal
(22°); round a bend A's path hugs the inner corner while B follows the middle (22–31°). The
last three rows are the finding for BLD-79: **the same source, heard from the same passage
40 cells down the leg, gets bearing 0°, −22° or −39° from the exact model depending on
which side of a 5-wide passage the listener stands**, because the shortest 8-connected path
from the corner to the listener is a long diagonal. In a real passage the sound arrives along
the passage. Phase 1's noise model adds 4–22° on top of whichever definition is chosen.

### 4.5 Sensitivity of the recommended model (tree-400×240, three seeds, mean of means)

| configuration | A-lazy µs/tick | A-lazy ms/match | A-lazy worst tick µs (max of seeds) | B+C µs/tick | builds/match |
|---|---|---|---|---|---|
| the task's load: 8 agents, motion every 10 ticks, ping 170, no echo | 26.6 | 256 | 1726 | 0.23 | 4648 |
| motion field reused for 20 ticks (1 s) | 21.4 | 206 | 1774 | 0.20 | 2492 |
| 4 agents (one per team), motion every 10 | 9.5 | 91 | 1213 | 0.09 | 1578 |
| 4 agents, motion every 20 | 8.2 | 79 | 1347 | 0.09 | 863 |
| 8 agents, ping range 120 | 22.2 | 213 | 1147 | 0.22 | 4628 |
| 8 agents, one echo emission per ping (BLD-80) | 40.8 | 392 | 2350 | 0.42 | 4796 |
| open CA field 400×240, 4 agents, motion every 20 | 24.3 | 234 | 4261 | 0.39 | 658 |

Agent count is the big lever (8 → 4 is −64%, more than linear because both emitters and
listeners halve); motion-field reuse is −20%; ping range 170 → 120 is −17%; one echo per ping
is +53%. On the open field the four-agent configuration costs what eight agents cost on the
passage cave.

### 4.6 Memory

| model | what is resident | tree-200×120 | tree-400×240 | tree-800×480 |
|---|---|---|---|---|
| A (any variant) | 6 bytes per cell (`dist` u32, `pred` u8 direction, `state` u8) per concurrently live field, plus its heap; the prototype takes one slot per live emission and peaks at 8–14 slots because eight motion emissions land in the same sample tick | 2.6 MB | 7.4 MB | 20 MB |
| B | 8 bytes per cell (nearest skeleton pixel, offset) + 16 bytes per skeleton pixel + edge pixel lists + 12 bytes per node per live emission | 227 KB | 825 KB | 3.2 MB |

A's number is the prototype's, not a floor: motion emissions live one tick and can share one
slot in turn (build, answer every listener, release), which takes the peak from ~13 slots to
~4 (two live pings, two ancients) — 2.3 MB at 400×240 — and `dist` can be u16 in coarser
units. Eight matches in parallel at 400×240 is then ~20 MB, not 60. Not measured.

### 4.7 Cost of a cave change

A collapse (BLD-94) turns a 4-cell-radius blob of free cells to rock.

| model | what happens | tree-200×120 | 400×240 | 800×480 | open CA 400×240 / 800×480 |
|---|---|---|---|---|---|
| A | nothing is precomputed; live fields are dropped (they may have crossed the blob) and rebuilt on the next query at the per-emission cost of §4.1 | 0.01 ms | 0.02 ms | 0.02 ms | 0.05 / 0.06 ms |
| B | full graph rebuild (thin, minimise, prune, trace, map every cell) | 1.6 ms | 6.3 ms | 28 ms | 15 / 71 ms |

B's rebuild could be local to the changed component (re-thin a window, re-trace the edges
that cross it, re-map its cells) and would then be well under a millisecond; it is not built
and is the kind of code that hides determinism bugs (which window, in what order).

---

## 5. The budget

The gate: 1,000 matches headless in under 10 minutes, bit-identical on three platforms.
1,000 × 9,600 ticks in 600 s is **62.5 µs per tick for everything, single-threaded**, or
about **500 µs per tick with eight matches in parallel** on this laptop (DETERMINISM rule 5
permits parallelism across matches; BLD-109 assumes it; ARCHITECTURE-RECONCILIATION §17 uses
the same two numbers). A CI runner with 2–4 cores sits in between. A live 20 Hz server has
50 ms per tick and is not the binding constraint for anything here.

The rest of the tick, from the sibling spike's Python measurements scaled by the 50–100×
Rust factor seen here: odometry, beacons, cargo are trivial; a sonar ping is ~120 µs of trig
in the tick it fires (60 rays × 30 cells) and lidar ~1.5× that every 1.5 s; belief fusion,
terrain-relative matching (BLD-90) and the policy driver are unmeasured and terrain matching
is the likely second-largest consumer. Acoustics cannot take half the tick.

**Proposed budget:**

| | limit | measured, recommended model, tree-400×240 |
|---|---|---|
| acoustic cost per tick, mean over a match | **10 µs** (16% of the single-core tick, 2% of the 8-wide one; 100 ms per match) | 9.5 µs with 4 agents; 8.2 with 4 agents and 20-tick motion reuse; 26.6 with 8 agents |
| worst single tick | **2 ms** (one 170-cell ping field through a chamber-rich region plus its listeners; irrelevant to the batch total, relevant to BLD-81's worst-tick assertion and a live server) | 1.2–1.9 ms |
| memory per match | **8 MB** at 400×240 | 7.4 MB as prototyped; ~2.3 MB with slot sharing |
| a collapse | **0.1 ms** in the tick it happens, plus one rebuild per live emission on next query | 0.02 ms |

The budget is met by the recommended model at four agents. At eight agents it is met only
under the parallel-batch reading (26.6 µs of 500), or with two of the levers in §7 applied
together (motion reuse and ping range 120 would bring it to ~18 µs, estimated as the product
of the two measured factors, not measured together; still over 10 on one core).
The graph model meets it by a factor of 30–100 in every configuration and would be the
fallback.

---

## 6. Recommendation, with reasons and the cost of being wrong

**R1. Model A-lazy: exact range-bounded cell Dijkstra, integer costs, heap ordered by
`(cost, cell id)`, resumed per listener, cached per emission, Euclidean prefilter.**

Reason. It computes what Phase 1 computed and what the spectator gate was watched on, with
no approximation to explain; it has no precomputed structure, so BLD-94's collapses,
BLD-80's echoes and BLD-79's absorption are each one line in the same loop; cold and warm
caches give identical answers by construction (§8); and it fits the budget at the agent
count the design implies for Phase 3 (one agent per team — multiple agents per player is
deferred to after Phase 6 in ROADMAP Part 6).

Cost if wrong. If the Phase 3 cave turns out open-field (DESIGN's CA without carving) or the
match runs eight agents on one core, the acoustic share is 25–90 µs per tick and the batch
gate misses by up to 2×. The fallback is model B, already prototyped (~700 lines in
`skel.rs`, half of it skeleton extraction), at the price of the fidelity gap in §4.3 and a
rebuild per collapse; porting it is roughly the size of BLD-79 itself (4 days). Nothing about the exact model forecloses that
switch: the emitter list, the sensor seam (`arrivals_at`) and the hash policy are the same.

**R2. Budget: 10 µs per tick mean, 2 ms worst tick, 8 MB, 0.1 ms per collapse** (§5).

Reason. It is what the recommended model measures at four agents with a third of margin,
and it leaves 50 µs of the single-core tick for the seven other subsystems.

Cost if wrong. Too tight and BLD-81 fails its worst-tick assertion on a legitimate model;
too loose and BLD-109 discovers in month five that acoustics ate the terrain-matching budget.
Both are visible the day BLD-81 lands, which is why BLD-81 exists.

**R3. Motion-noise fields are reused for 20 ticks, not 10.**

Reason. −20% of the model's cost for a source displacement of at most 1.4 cells (the
aggressive chassis at 1.4 cells/s), which at the 40-cell motion range is a 2° bearing shift
against a 4° near-field noise floor.

Cost if wrong. If the designer wants motion contacts to track a running agent at half-second
resolution, this loses a quarter-second of freshness; revert by changing one constant.

**R4. Keep the binary heap, not the bucket queue.**

Reason. The bucket queue is 8–20% faster but pops equal-cost cells in push order rather than
by cell id, which contradicts BLD-79's acceptance criterion as written ("heap entries are
ordered by (cost, cell id)"); sorting each bucket would give the ordering back and eat the
gain. Both are deterministic across platforms; the criterion is about auditability.

Cost if wrong. 8–20% of the acoustic budget, recoverable in an afternoon.

**R5. The Phase 3 benchmark cave (BLD-72, BLD-108) is a passage cave: 400×240, ~17% free,
chambers of radius 5–12 joined by passages that carry all four width classes — crawl 2–3,
narrow 3–4, passage 4–5, hall ≥5 cells — in the biome's proportions, with every seed emitting
all four; four agents.**

Reason. It is the shape Phase 1 validated, the shape the cost model is benign on, and the
size that gives four teams a Phase-1-sized region each. The CA-only generator cannot produce
it (§2.4).

Cost if wrong. If the target is larger, the exact model gets cheaper (agents spread out) and
memory grows linearly (20 MB at 800×480 as prototyped); if the target is more open, see R1.

Reconciled 2026-09-06: the spec said "passages 4–6 wide" throughout, which cannot tell one
chassis from another — CHASSIS D5 needs all four width classes emitted in every seed, and the
Phase 1 raster shows nothing under 3.6 cells across is distinguishable at 4–6. The mix is
strictly cheaper acoustically than 4–6 everywhere (narrower passages reach fewer cells per
emission), so §4's costs stand as an upper bound. See PHASE-3-OPEN-QUESTIONS.md §38 and §25.

---

## 7. Levers if the budget is missed

In order of how little they change the game:

1. **Agent count.** 8 → 4 is −64%. Not a lever the sim controls, but the number that
   matters most.
2. **Motion-noise field reuse** (R3): −20%.
3. **Ping range** 170 → 120: −17% and a design change (§10, Q5).
4. **Parallel batch** (the gate's wall-clock, not the model): ×8 headroom on this machine.
5. **Model B** for motion noise only, exact model for pings: motion is ~93% of the builds
   but pings are the big ones (~320 pings × ~320 µs is ~100 ms of the 256 ms per match), so
   this would cut the exact model's cost by roughly 3× while keeping ping bearings exact —
   but motion contacts at 40 cells are where bearing accuracy matters most for tracking, so
   it moves the fidelity gap to the worst place. Not measured; listed so it is not
   rediscovered.
6. **Model B everywhere**: −99%, with §4.3's gap and a rebuild per collapse.

---

## 8. What the fixed-point port changes, and the cache/hash policy for BLD-81

**Arithmetic.** Nothing in the propagation is floating-point now: step costs are 1024, 1448,
563 and 796 (1/1024-cell units; 0.55 × 1024 = 563.2 rounds to 563, so the flooded
multiplier the port ships is 563/1024 = 0.5498, not 0.55 — content should state the integer),
the range is one integer per emission, distances are `u32` (a 170-cell range is 174,080
units; 4 M cells of range would still fit). The listener's cell is `floor` of an `Fx`
position. The only transcendental is one `atan2` per heard return for the bearing — from
BLD-67's single math module, which needs 0.5° accuracy against a 4° noise floor (a 256-entry
table is plenty). The Euclidean prefilter compares squared distances; in I32F32 a squared
800-cell coordinate is 640,000, well inside the integer part, but do it in `i64` on the
integer cell coordinates and avoid the question.

**Ordering.** `BinaryHeap<Reverse<(u32 cost, u32 cell)>>` is a total order — no two live
entries compare equal unless they are the same cell at the same cost, in which case either
is fine — so `std`'s heap is deterministic across platforms and `std` versions. A hand-rolled
heap is not needed. If the bucket queue is ever adopted, its tie order is push order, which is
also deterministic but is not `(cost, cell id)`.

**Query-order independence (the BLD-81 lockstep test).** Dijkstra's settled set at any cost
threshold, and each settled cell's predecessor, are a function of the cave and the source
only — the pop sequence is the same whether it is consumed in one go or in pieces. So a lazy
field answers every listener exactly as a full field would, whatever the order and grouping
of the questions, and a cold-start Sim and a warm-cache Sim stepped in lockstep hash
identically. The one way to break this was found tonight: returning from the resumed loop
before expanding the settled target's neighbours (§4.2); the fix is in the code and the
lockstep test is the regression test.

**Hash policy.** Emitters are state: `(emitter id or agent id, cell, start tick, end tick,
kind, range)` in a `BTreeMap` keyed by a record-assigned emission id, hashed every tick.
Fields (`dist`/`pred`/`state` slots, heaps, the touched lists) are derived and excluded from
the hash; clearing or warming them must not change it (BLD-81's mutation test). If model B
were used, the graph is also derived — but it is derived from the cave, so it is a function
of hashed state and can be rebuilt at any time without consequence; the same holds for a
local rebuild if its algorithm is deterministic.

**Threading.** None inside a tick. Each Sim owns its slots; eight Sims in parallel share
nothing.

**Memory.** Slot arrays are plain `Vec<u32>` / `Vec<u8>`, no hashing; the touched list makes
release O(reached), not O(cave). See §4.6 for the slot-sharing and `u16` reductions.

**Seams.** The prototype's `Model::listen(emission, listener)` is
ARCHITECTURE-RECONCILIATION's `SensorEnv::arrivals_at(pos, out)` with the loop over live
emissions moved inside; nothing in the sensor sees the field, only arrivals. A hardware
backend answers `arrivals_at` from a hydrophone array; the interface does not change.

---

## 9. Design problems found on the way

1. **The arrival bearing swings with the listener's lateral position** (§4.4): the exact
   model's "five cells back along the shortest path" is the taut string, not the passage
   axis, and in a passage wider than ~3 cells or round a bend it differs from the axis by
   20–40°. Phase 1 played with this definition and its 4–22° noise on top. It is not an
   error to keep — it is a definition — but BLD-79 should choose it knowingly (Q6). The
   passage-axis alternative needs the skeleton's cell-to-passage map as a direction-only side
   structure under the exact model (8 bytes per cell, 6 ms to build, tolerant of staleness
   after a collapse because the exact model still decides audibility and distance).
2. **The cellular-automata generator has a percolation cliff** (§2.4): DESIGN's demo
   parameters give an open field; two points of fill later there is no cave. BLD-72's
   "connectivity guarantees" cannot come from tuning the fill; they come from carving.
3. **Motion noise as specified is the dominant acoustic cost**, and it scales with agent
   density, not cave size. If Phase 6 ever runs more than one agent per team, the acoustic
   budget should be re-derived then, not inherited.
4. **A 170-cell ping is basin-wide on Phase 1's cave and 40% of the cave at 400×240**
   (§3). DESIGN's "every passive listener in the basin" and the tuned range disagree on the
   bigger cave. Either is fine; they are not the same game.

---

## 10. Questions for the designer

Each is a yes/no. A "no" comes with what changes.

- **Q1.** Phase 3's acoustic field is the exact range-bounded cell Dijkstra (A-lazy, R1),
  not the passage graph. — yes / no. *No:* B is ported instead; the §4.3 gap (10–20% of
  audible pairs silent, 25° mean bearing difference) becomes the game's behaviour and BLD-94
  gains a graph-rebuild step.
- **Q2.** The acoustic budget is 10 µs per tick mean, 2 ms worst tick, 8 MB, 0.1 ms per
  collapse (R2), judged against the 62.5 µs single-core tick. — yes / no. *No:* state the
  number; below 5 µs only model B fits.
- **Q3.** The Phase 3 benchmark cave is 400×240 cells, passage-shaped (~17% free, chambers
  joined by passages carrying all four of CHASSIS D5's width classes, every class in every
  seed), with four agents (R5). — yes / no. *No:* say the size, shape and agent count; the
  tables in §4 cover 200×120 to 800×480 and open to passage, so the answer is readable
  without re-running.
- **Q4.** A moving agent's motion-noise field is reused for 20 ticks (1 s) instead of 10
  (R3). — yes / no. *No:* +25% on the acoustic cost; the budget still holds at four agents.
- **Q5.** The ping range stays 170 cells on the bigger cave, so a ping reaches ~40% of a
  400×240 cave rather than the whole basin. — yes / no. *No:* say the range; cost scales
  with the area reached (120 → −17%; basin-wide on 400×240 would be ~300 cells, roughly
  +150%, and would make the open-field numbers the relevant ones).
- **Q6.** The arrival bearing keeps Phase 1's definition — the direction of the shortest
  path five cells back — accepting the ±20–40° lateral swing in wide passages and at bends
  (§4.4, §9.1). — yes / no. *No:* BLD-79 adds the skeleton-derived passage-axis bearing as a
  direction-only side structure (6 ms per cave, 8 bytes per cell) and the fixture in §4.4
  becomes its acceptance test.
- **Q7.** BLD-80 echoes are budgeted as at most one extra emission per ping. — yes / no.
  *No:* each further echo per ping is another +50% on the acoustic cost with the exact
  model, +0.2 µs per tick with the graph.
- **Q8.** BLD-72 is written as "cellular-automata chambers joined by carved passages", not
  "cellular automata with connectivity repair" (§2.4, §9.2). — yes / no. *No:* someone will
  spend the 4 days of BLD-72 on the fill parameter.

---

## 11. Guesses

Marked here so they are not mistaken for measurements.

- The target cave is 400×240 with four agents (§2.5); the task said eight agents and both
  were measured.
- Agents never stop moving and random-walk uniformly; real agents dwell and cluster.
- The ancient signature is audible 13 s of every 75 s (Phase 1's warning + lethal); four
  crashes per match; two ancients.
- Flooding is 12% of free cells in random blobs of radius 6–14; Phase 1 flooded one chamber
  and two passages.
- The CA fills 0.47 and 0.50, five iterations, and the tree generator's chamber density (11
  per 24,000 cells), radii (5–12), passage widths (4–6) and 30% extra loops are Phase 1's
  numbers or the DESIGN demo's, scaled; none is a Phase 3 spec.
- Sampling cadences (pings every 10 ticks, ancients every 5, motion every 10, crash once)
  are Phase 1's sensor rig, assumed to carry into Phase 3 unchanged.
- The Euclidean prefilter for motion noise (Phase 1 applied it to motion only) is applied to
  every emission kind; it is exact (path ≥ straight line) so it changes cost, not results.
- The 4-cell collapse radius, and that a collapse invalidates every live field rather than
  only those whose reached set touches the blob (the cheaper check was not built).
- Rock absorption is assumed to be a per-cell cost multiplier like the flooded one; not
  measured because it changes nothing in the loop.

---

## 12. Rebuilding the numbers

```
cd spikes/acoustic
cargo build --release

# §2.4 caves (two seeds) and the fill sweep
./target/release/acoustic-spike caves gens=tree,cat,ca seed=1
./target/release/acoustic-spike caves gens=tree,cat,ca seed=2
for f in 0.50 0.52 0.53 0.54; do ./target/release/acoustic-spike caves sizes=400x240 gens=ca seed=1 fill=$f; done
./target/release/acoustic-spike caves sizes=200x120 gens=tree seed=1 ascii=1      # the thumbnail

# §4.1 per-emission cost by range (run on an idle machine; ±15% between runs)
./target/release/acoustic-spike single size=400x240 gen=tree seed=1
./target/release/acoustic-spike single size=400x240 gen=cat  seed=1
./target/release/acoustic-spike single size=400x240 gen=ca   seed=1
./target/release/acoustic-spike single size=800x480 gen=tree seed=1
./target/release/acoustic-spike single size=200x120 gen=tree seed=1

# §4.2 per-tick cost, all models, three sizes, three generators, three seeds (~4 minutes);
# the aggregated table is the mean of the per-tick means and the max of the worst ticks per row
./target/release/acoustic-spike bench sizes=200x120,400x240,800x480 gens=tree,cat,ca seeds=3

# §4.3 accuracy of B against A
./target/release/acoustic-spike accuracy pairs=1000 seed=1 gens=tree,cat,ca

# §4.4 fixture
./target/release/acoustic-spike fixture

# §4.5 sensitivity (each prints three seed rows for A-lazy and B+C)
./target/release/acoustic-spike bench gens=tree sizes=400x240 seeds=3 models=AL,BC
./target/release/acoustic-spike bench gens=tree sizes=400x240 seeds=3 models=AL,BC motion_every=20
./target/release/acoustic-spike bench gens=tree sizes=400x240 seeds=3 models=AL,BC agents=4
./target/release/acoustic-spike bench gens=tree sizes=400x240 seeds=3 models=AL,BC ping=120
./target/release/acoustic-spike bench gens=tree sizes=400x240 seeds=3 models=AL,BC echo=1
./target/release/acoustic-spike bench gens=tree sizes=400x240 seeds=3 models=AL,BC agents=4 motion_every=20
./target/release/acoustic-spike bench gens=ca   sizes=400x240 seeds=3 models=AL,BC agents=4 motion_every=20

# §3 Phase 1's Python baseline (from the repo root)
PYTHONPATH=. .venv/Scripts/python.exe -c "
import time, statistics, numpy as np
from phase1.sensing.sound_field import SoundField
from phase1.truth import cave
from phase1 import tuning as T
ys, xs = np.nonzero(cave.WALKABLE); rng = np.random.default_rng(1); idx = rng.choice(len(xs), 40, replace=False)
for label, rr in (('ping 170', T.HEAR_PING_RANGE), ('ancient 80', T.HEAR_ANCIENT_RANGE), ('motion 40', T.HEAR_MOTION_RANGE)):
    ts = []
    for i in idx:
        t0 = time.perf_counter(); SoundField(xs[i] + 0.5, ys[i] + 0.5, rr); ts.append((time.perf_counter() - t0) * 1e3)
    print(label, 'ms mean %.1f max %.1f' % (statistics.mean(ts), max(ts)))
"
```

Prototype layout and per-file notes: `spikes/acoustic/README.md`. Not merged into any
workspace (BLD-64's last acceptance criterion); `spikes/acoustic/Cargo.toml` declares an
empty `[workspace]` so it cannot be picked up by one.
