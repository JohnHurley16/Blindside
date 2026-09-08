"""Every number in Phase 1, in one place. Edit here, nowhere else.

Units: cells (1 cell ~ 1 m), seconds, degrees. The sim runs at TICK_HZ and a match
is MATCH_SECONDS of sim time.

Where a value was changed after watching a headless run, the measurement that
prompted it is written next to it. Those notes are the point of this file.
"""
from __future__ import annotations

from typing import Final

# ---- time and scale ---------------------------------------------------------------
TICK_HZ: Final[int] = 20
DT: Final[float] = 1.0 / TICK_HZ
MATCH_SECONDS: Final[float] = 8 * 60
EXTRACT_WINDOW_OPENS: Final[float] = 6 * 60 + 30   # DESIGN: the last 90 s
EXTRACT_RADIUS: Final[float] = 6.0                 # cells from shaft centre, in truth
                                                   # (the shaft chamber's own radius)
SEED: Final[int] = 7

AGENT_SPEED: Final[float] = 1.1                    # cells/s; 480 s => ~530 cells of travel
RIVAL_SPEED: Final[float] = 1.4                    # the aggressive one runs a lighter chassis
AGENT_TURN_RATE: Final[float] = 150.0              # deg/s
AGENT_RADIUS: Final[float] = 0.6                   # for wall collision

# ---- dead reckoning ----------------------------------------------------------------
# Bias-dominated so the map ghosts instead of fuzzing. Signs are drawn per agent from
# SEED so the two agents lean differently.
#
# Measured: at 0.035 deg/cell the entire outbound leg produced 5.7 cells of position
# error and the largest fix jump in the whole match was 3.6 cells. On a 200x120 map
# that is about 2% of the view -- invisible. The first acceptance criterion is that
# the cloud visibly smears and snaps, so heading bias is now the dominant term.
DR_SCALE_BIAS: Final[float] = 0.055                # fraction of distance travelled
DR_HEADING_BIAS_DEG_PER_CELL: Final[float] = 0.11  # ~22 deg over a 200-cell leg; the
                                                   # lateral ghost is the integral of
                                                   # that, so tens of cells by the far end
DR_POS_NOISE_PER_CELL: Final[float] = 0.03         # random walk std, cells per sqrt(cell)
DR_HEADING_NOISE_DEG_PER_CELL: Final[float] = 0.03

# The estimator's own model of its error. Scaled with the above so the ellipse stays a
# meaningful trigger, but kept slightly under the truth: a fix that jumps further than
# the ellipse promised is the tell a player can actually catch.
EST_SIGMA_ALONG_PER_CELL: Final[float] = 0.038
EST_SIGMA_HEADING_RAD_PER_CELL: Final[float] = 0.0013
EST_SIGMA_AFTER_FIX: Final[float] = 0.5
EST_HEADING_SIGMA_AFTER_FIX: Final[float] = 0.02
HEADING_FIX_GAIN: Final[float] = 0.0               # fraction of inferred heading error a fix removes
# Zero, deliberately. ARCHITECTURE specifies Fix { position, source } -- a beacon gives
# position and says nothing about heading. The heading correction here was invented: it
# guessed rotation error by comparing the direction travelled since the last fix against
# the direction to the fixed position, which is a weak heuristic, and when it guessed
# wrong it rotated the whole back-propagated map about the anchor. Measured over a
# match, half of all honest loop closures left the agent MORE wrong than before they
# happened. At 0.0 none of them do.
#
# Heading drift is now uncorrected for the whole match, which is the honest consequence:
# the map fans open and nothing straightens it. DESIGN says the thing that recovers
# heading is terrain-relative matching against ground already surveyed, and that is a
# Phase 3 sensor, not something a lone beacon can do.

# ---- passive acoustic ---------------------------------------------------------------
# Ranges are path length through the cave: sound follows passages. Flooded cells cost
# FLOODED_COST per cell, so water carries further.
FLOODED_COST: Final[float] = 0.55
HEAR_MOTION_RANGE: Final[float] = 40.0             # a rival walking
HEAR_PING_RANGE: Final[float] = 170.0              # a rival's sonar: most of the cave
HEAR_ANCIENT_RANGE: Final[float] = 80.0
HEAR_CRASH_RANGE: Final[float] = 170.0             # an agent dying is loud
BEARING_NOISE_NEAR_DEG: Final[float] = 4.0
BEARING_NOISE_FAR_DEG: Final[float] = 22.0         # at max range: a 44-degree wedge at
                                                   # two sigma, which is nearly useless,
                                                   # and that is the point of bearing-only
MOTION_LISTEN_PERIOD: Final[float] = 0.5
CONTACT_MERGE_DEG: Final[float] = 18.0
CONTACT_MERGE_S: Final[float] = 8.0
CONTACT_FADE_S: Final[float] = 14.0
SELF_DEAF_AFTER_PING_S: Final[float] = 1.0

# ---- the active sensor is a loadout choice --------------------------------------------
# Designer's call, 2026-09-06: in the real game sonar and lidar are both modules and
# the player picks. Each has a cost. Sonar is loud -- every listener in the basin hears
# it -- and long, and it works in water. Lidar is silent, short, precise, and blind
# the moment there is water or silt in the way; the map it builds simply stops at the
# waterline. "Do I ping?" does not go away, it moves: it is the loud question for a
# sonar carrier, and for a lidar carrier the question becomes where it dares to go.
#
# THE GATE IS TWO VIEWINGS, SONAR FIRST. Designer's call, 2026-09-06, after a design
# panel: the tester watches an agent carrying sonar, then a second match with the
# agent carrying lidar. Sonar goes first because the Phase 1 spec names three sensors
# and its acceptance criteria are written for pings, and roughly ten "Measured:"
# numbers in this file were calibrated against heard pings -- so that viewing is the
# specced one. The panel's caveat, recorded and accepted: a tester who sees both worlds
# compares rather than reacts, which weakens attribution of a failure. Watch the first
# viewing for the gate, the second for the sensor question. This default is the first
# viewing; --player-sensor lidar is the second.
#
# A lidar sweep is a visible light in a dark cave, so in the real game it should be a
# tell to anyone with LINE OF SIGHT -- local exposure rather than basin-wide. Neither
# Phase 1 agent carries optics, so that tell is not modelled here. Noted, not built.
PLAYER_SENSOR: Final[str] = "sonar"                # "sonar" (the gate) or "lidar" (comparison)
RIVAL_SENSOR: Final[str] = "sonar"

LIDAR_RANGE: Final[float] = 18.0                   # short; sonar reaches 30 and across water
LIDAR_RAYS: Final[int] = 90                        # a full sweep
LIDAR_ARC_DEG: Final[float] = 360.0
LIDAR_PERIOD_S: Final[float] = 1.5                 # it spins; no discipline needed, it is free
LIDAR_RANGE_NOISE: Final[float] = 0.08             # cells; lidar is precise
LIDAR_BEARING_NOISE_DEG: Final[float] = 0.3
LIDAR_FALSE_RETURNS: Final[int] = 0

# ---- active sonar ---------------------------------------------------------------------
SONAR_ARC_DEG: Final[float] = 120.0
SONAR_RAYS: Final[int] = 60
SONAR_RANGE: Final[float] = 30.0
SONAR_RANGE_NOISE: Final[float] = 0.25             # cells, plus 2% of range
SONAR_BEARING_NOISE_DEG: Final[float] = 1.2
SONAR_FALSE_RETURNS: Final[int] = 2                # spurious points per ping
SONAR_FALSE_QUALITY: Final[tuple[float, float]] = (0.12, 0.35)
SONAR_AUDIBLE_S: Final[float] = 3.0
WAVEFRONT_SPEED: Final[float] = 28.0               # cells/s. Fake, for legibility.
WAVEFRONT_LIFE_S: Final[float] = 6.0

# ---- near-field sense ------------------------------------------------------------------
# The fourth, tiny sensor. Without it a corridor walked without pinging leaves no points
# at all, which contradicts "sparse where it has only passed through".
NEARFIELD_RANGE: Final[float] = 2.5
NEARFIELD_RAYS: Final[int] = 8
NEARFIELD_PERIOD_TICKS: Final[int] = 4
NEARFIELD_QUALITY: Final[float] = 0.28

# ---- beacons ----------------------------------------------------------------------------
BEACON_DROP_EVERY_CELLS: Final[float] = 45.0
BEACON_RANGE: Final[float] = 6.0
# Acquisition range is deliberately far below the drop interval. If it were not, the
# agent would never leave its own chain, drift would never accumulate, and there would
# be nothing to look at. The gap between 6 and 45 is where the smear happens.
BEACON_FIX_NOISE: Final[float] = 0.35
SHAFT_BEACON_RANGE: Final[float] = 10.0            # survey-placed: the only truth anchor
HOME_REACHED: Final[float] = 6.0
HOME_FINAL: Final[float] = 2.0                     # once the shaft has answered
# Measured: at 1.5 cells the agent never once registered arriving at the shaft in a
# whole sweep of recall timings, so the search that follows arrival never ran at all.
# A drifting agent wall-following its way home cannot hit a 1.5-cell target.

# ---- the spoof ---------------------------------------------------------------------------
# Lie distance divided by beacon range is the most important ratio in the test. Below
# 1 the victim re-acquires an honest beacon and the lie heals itself within a minute.
# At 34 against a 6-cell acquisition range the victim walks off its own chain entirely.
#
# Measured: with the window at 3:20 the spoof never fired in a full match. The
# uncertainty return triggered at 3:03.9 and the old arming condition required the
# policy to be in TRAVEL at a beacon-drop instant, so the window never opened. The
# mode gate is gone and the window now opens well before the return can fire.
SPOOF_AFTER_S: Final[float] = 140.0
# Measured: at 2:30 the victim spent the remaining five and a half minutes walking
# into walls, because every waypoint it held was forty cells from where it thought.
# That is the right failure but it is one note held far too long. At 4:00 the
# aftermath was the right length, but the uncertainty return had already fired at
# 3:31 and sent the agent home on its own -- which made Recall worthless, because the
# player's one command did what the agent was doing anyway.
#
# So the spoof must land before that return, and the return must be late enough to
# leave room. 3:20 with the trigger at 16 does both: three clean minutes of normal
# fixes, then the lie, which collapses the ellipse and disarms the agent's own
# self-preservation. After that Recall is the only thing that can bring it home.
SPOOF_LIE_CELLS: Final[float] = 34.0
SPOOF_AHEAD_CELLS: Final[float] = 4.0              # clone placed this far ahead of the victim
SPOOF_RANGE: Final[float] = 18.0                   # louder than an honest beacon
SPOOF_REASSERT_S: Final[float] = 8.0
# A spoof keeps broadcasting; an honest beacon answers once as you pass. So the lie is
# reasserted while the victim is inside SPOOF_RANGE, which beats the quiet markers it
# passes every 45 cells. The counter DESIGN names -- cross-check a fix against
# terrain, distrust a lone beacon -- is a policy skill these scripted agents do not
# have, and Phase 2 is where it would be learned.
#
# Measured: at a 30-cell range the liar pinned the victim for the rest of the match,
# holding sigma at 0.9 while the true error sat near 80 cells. Confidently wrong is
# the design, but for five unbroken minutes it flattens into one note and the ellipse
# stops being worth looking at. At 18 the victim walks out of range, drift resumes,
# and the error moves again.

# ---- deposits ------------------------------------------------------------------------------
DEPOSIT_RADIUS: Final[float] = 12.0
# Measured: at 6.0 the player believed it had arrived at deposit A, sat there for the
# full load time and got nothing, because drift had left it 7.8 cells short. It then
# extracted with an empty hold and never knew why. 12.0 lets a modest drift still
# succeed, so that failing to load means something rather than being the default.
LOAD_SECONDS: Final[float] = 30.0
CARGO_CAPACITY: Final[int] = 2
LOAD_RETRIES: Final[int] = 2
LOAD_SEARCH_STEP: Final[float] = 9.0               # how far to hunt after a failed load

# ---- ancient system --------------------------------------------------------------------------
ANCIENT_PERIOD_S: Final[float] = 75.0
# Measured: at a 42 s period with a 6 s lethal window the rival died at 3:46, which
# silenced the map for the last four minutes of an eight-minute match. A longer period
# and a shorter kill make passing through survivable, so dying there is a decision that
# went wrong rather than a toll booth.
ANCIENT_WARNING_S: Final[float] = 9.0              # signature before lethal
ANCIENT_LETHAL_S: Final[float] = 4.0
ANCIENT_RADIUS: Final[float] = 9.0
ANCIENT_PHASE_S: Final[float] = 30.0
# Measured after map-aware steering moved every path: at 20 nobody dies in either
# kit; at 30 the rival dies at 5:41 (sonar) / 5:45 (lidar), within a few seconds of
# where it did before. Several other phases kill the PLAYER instead -- the spoof walks
# it into the machinery's chamber -- which is DESIGN's "march into a trench" beat and
# worth a deliberate seed later, but not the default the gate runs on.
ANCIENT_HOLD_QUALITY: Final[float] = 0.45          # cautious policy stops above this
INVESTIGATE_QUALITY: Final[float] = 0.30           # aggressive policy walks toward it above this
INVESTIGATE_HOLD_S: Final[float] = 14.0            # and keeps heading that way this long after
                                                   # the last time it heard it
# Measured: 90 s here -- hunt until the next warning -- dropped the kill rate to 0/8,
# because a bearing in a cave points down the passage the sound arrived by, not at the
# source, and the rival walked itself somewhere else. The hunt is flavour; the kill
# comes from the dwell below.
INTERFACE_QUALITY: Final[float] = 0.60             # loud enough to mean "here": stop and interface
INTERFACE_S: Final[float] = 80.0                   # longer than one cycle, so the next one lands
INTERFACE_SPEED: Final[float] = 0.4                # creeping the last few cells along the bearing
# Measured: walking toward the machinery on hearing it did nothing to the kill rate
# (1-in-8, 2-in-8), because it hears the nine-second warning, starts walking, and
# arrives after the four-second lethal window has closed -- then wanders off. The
# fiction implies it goes there and STAYS to download, so it now interfaces for longer
# than one cycle, and the next cycle finds it there.
# Designer's call: the aggressive temperament investigates the machinery, because in
# the real game the machinery is where an agent can download new behaviours -- so
# going to look is rational, not reckless. Measured before this: the rival's death
# was a 2-in-8 event across seeds under every phase and lethal window tried, which is
# path luck, not a beat. This makes it a decision the rival takes, and one the
# spectator can watch it take.

# ---- the Assayer: the cycle, the lobe, the dose -------------------------------------------------
# THE-MACHINERY.md sections 3 and 4. The five constants above keep their values and one
# of them changes its meaning: ANCIENT_RADIUS is now the lethal contour ON THE AXIS,
# which is 9.0 in every direction only when the lobe floor is 1.0. Change what 9 means;
# do not change 9.
ANCIENT_AIM_0_DEG: Final[float] = 40.0
# The survey azimuth of the first firing (0:41). Chosen from the 26 of 72 five-degree
# origins that keep all three of the deaths seeds 1-8 produce today (THE-MACHINERY 11,
# scratchpad/lobe_sweep2.py, re-run 2026-09-07). Two of those deaths are so deep inside
# the contour that they die at any angle; only seed 7's rival, at 8.121 cells, is
# angle-sensitive, and it dies within 32.3 degrees of the axis -- which makes the
# surviving interval [9.2, 73.8] degrees. 40 is the grid origin furthest from either
# edge of it (30.8 degrees of margin), so this is the most robust of the 26 rather than
# the one that lands a beat.
ANCIENT_AIM_STEP_DEG: Final[float] = -36.0
# A survey covers ground: the aim indexes the same way every firing, so ten firings is a
# revolution and the safe side of a chamber is safe for a while and then is not. Two
# slews are enough for a player to predict the third.
ANCIENT_SLEW_S: Final[float] = 3.0    # the boom swings; movement is the loudest thing on a screen
ANCIENT_LOCK_S: Final[float] = 5.0    # stillness after movement: the beat that reads as a decision
ANCIENT_FIRE_S: Final[float] = 0.15   # the hammer falls: 3 frames at the recorder's 20 fps
# 54 listening / 3 slew / 5 locked / 9 wind / 4 lethal, inside the established 75. The
# warning and lethal windows are untouched, so every measured spectator beat survives.
ANCIENT_LOBE_FLOOR: Final[float] = 0.35
# gain(theta) = 0.35 + 0.65*cos^2(theta - aim). The array is directional, so the lethal
# contour is 9.00 cells on the axis and 5.32 at the flank: safe becomes a PLACE (behind
# it) rather than a distance a machine has to estimate. cos^2 is symmetric, so the back
# lobe is as strong as the front -- a ribbed array driving a shock into the rock has no
# reason to be one-sided.
ANCIENT_WATER_COST: Final[float] = 0.35
# A flooded working is a continuous column coupled to the rock on every side, so the
# shock runs along it with much less loss. Cost per flooded cell against 1.00 for
# everything else, on a Dijkstra from the machine, taken as a RATIO against the same
# Dijkstra over uniform cost. Measured: exactly 1.000 on all 529 walkable cells within
# 20 cells, so the reference beats survive to the third decimal; the felt contour runs
# 33.6 cells up the flooded ANC->SUMP bearing against 17.9 on dry ones. Rock is not
# cover -- both Dijkstras cross it -- which is the rule this object exists to teach.
ANCIENT_DOSE_K: Final[float] = 0.5
ANCIENT_DOSE_CURVE: Final[float] = 1.5
# damage += 0.5 * coupling^1.5, per FIRING and not per second, because the blow is an
# instant: the unit of risk is the cycle, so an 80-second interface dwell costs exactly
# one firing. At the rim (coupling 0.99) that is half a machine.
ANCIENT_DOSE_FLOOR: Final[float] = 0.04
# Below this coupling nothing is recorded: 0.04 is 45 cells on the axis, and the ratio
# to defend is audible at 80, felt at 45, killed at 9.
# ---- what damage COSTS -----------------------------------------------------------------------
# THE-MACHINERY 4.3 wanted the HEADING REFERENCE to go first: the truth-side drift
# coefficients scaled by 1 + 1.5*damage, so a shaken machine became confidently wrong at an
# accelerating rate with nothing on the belief side announcing it. Section 11 pre-committed
# to an A/B on it -- "if they are not obviously different by 7:00, the odometry effect
# should be cut and damage should cost speed and sensor range instead" -- and the A/B was
# run on seed 7 and FAILED it. Player position error at 7:00: 91.13 cells with the effect
# off against 88.38 with it on, and 91.13 against 84.93 at 8:00. The damaged machine ended
# up LESS wrong than the healthy one, and at eight times the gain it fell to 41.5, so the
# effect was not even monotone in its own gain: both runs jam against walls for the last
# 79 s and the paths diverge for reasons that have nothing to do with drift. So the
# coupling is cut, honouring the pre-commitment, and what is left is two constants that
# are legible, much less interesting, and honest.
DAMAGE_RANGE_FROM: Final[float] = 0.20
DAMAGE_RANGE_LOSS: Final[float] = 0.5
# The transducer goes first, because frames survive shock and precision does not: active
# range * (1 - 0.5*damage) above 0.20, so a half-wrecked machine's sonar reaches 22.6 cells
# instead of 30 and its lidar 13.6 instead of 18. Nothing tells it the range shrank -- the
# far returns simply stop arriving, and quality is still scored against the nominal range,
# so a near return looks exactly as good as it always did.
DAMAGE_SPEED_FROM: Final[float] = 0.30
DAMAGE_SPEED_LOSS: Final[float] = 0.5
# The drive second, and one rung later, because a chassis is the sturdiest thing on it:
# speed * (1 - 0.5*damage) above 0.30. At the 0.493 dose the 5:41 near miss delivers that
# is 75% speed -- a quarter less ground per minute, which is visible beside an unhurt rival
# and nowhere near unable to get home.
#
# Both are TRUTH-side. The policy asks for a speed and gets less and sweeps a range and
# gets shorter; it finds that out through its own returns, if it finds out at all. And both
# keep a THRESHOLD rather than being continuous from zero, which is measured rather than
# tidy: the dose floor is 45 cells, so almost every match delivers two or three 0.005
# scratches to agents that are nowhere near the machine, and applied continuously a 0.15%
# speed change compounds through waypoint thresholds and stuck timers into completely
# different paths -- it moved every death across seeds 1-8 and put the seed 7 player 4.7
# cells from the machinery instead of 9.038. With the thresholds the match is bit-identical
# to the one that was swept until something is actually hurt.
ANCIENT_MAST_CELLS: Final[float] = 11.0   # 3 cells above CAVE_WALL_HEIGHT_CELLS: the only
                                          # thing in the cave that breaks the skyline
ANCIENT_BOOM_CELLS: Final[float] = 7.0    # a 7-cell arm swinging 36 degrees moves its tip
                                          # 4.4 cells, which is above the 6-8 px/s threshold
                                          # this project already built comets to defeat

# ---- drawing the Assayer -----------------------------------------------------------------------
# THE-MACHINERY.md sections 2 and 3, view side. The numbers that move a beat live here;
# the proportions of one object -- leg spans, rib widths, hammer collar -- live beside the
# code that draws them in view/assayer.py, the way director.py keeps its own hold times.
ANCIENT_CLICKS: Final[int] = 9
# The wind is nine ratchet clicks at 1 Hz. At the recorder's 20 fps that is twenty frames a
# click, which is countable on a captured video rather than a strobe -- and it is the same
# count as ANCIENT_WARNING_S seconds, so the hammer IS the countdown.
ANCIENT_RATCHET_FRACTION: Final[float] = 0.20
# Each click snaps up over the first fifth of its second and then holds. A step reads as a
# mechanism taking load; a smooth rise reads as a slider and nobody counts a slider.
ANCIENT_HAMMER_RISE_CELLS: Final[float] = 8.4
# From the leg hub to just under the mast head. Deliberately the REDUNDANT mark: a world-z
# displacement projects up-screen at cos(elevation), which is 0.31x at the 72-degree default
# and exactly zero at the top of the 60-90 clamp, so height can never carry the warning.
ANCIENT_RECOIL_CELLS: Final[float] = 0.4
ANCIENT_RECOIL_S: Final[float] = 0.5
# The rig jolts down on the blow and recovers over half a second. It is the only mark that
# says the hammer HIT something rather than merely arrived, and it costs one transform.
ANCIENT_FELT_COUPLING: Final[float] = 0.25
# The faint contour: 18.0 cells on a dry axis and 32.5 up the flooded ANC->SUMP bearing.
# THE-MACHINERY 4.2 draws the felt boundary here, and section 4.4's dose table is indexed
# on it. It is the outer of the two curves and the one that says "you are in the work".
ANCIENT_LOBE_ALPHA: Final[float] = 0.34
ANCIENT_LOBE_HALO: Final[float] = 0.35
ANCIENT_LOBE_FALLOFF: Final[float] = 1.6
# The floor field is a CORE and a HALO, not one ramp. Measured: one ramp from the felt
# contour to the lethal one, at any peak alpha that made the lethal ground read, filled
# the whole chamber at a third of that -- which is a red disc, which is the thing the
# gate rejected. So the halo carries ANCIENT_LOBE_HALO of the peak and falls off as
# band^1.6, and the remaining 65% arrives as a step just inside coupling 1.0. The eye
# gets a hard edge where the boundary actually is and a wash where the shape is. 0.34 is
# the peak that still lets the machine's own boom read over its own lit ground at CLOSE.
ANCIENT_SCOUR_ALPHA: Final[float] = 0.10
# The permanent ruined ground: alpha = 0.10 * min(1, 9/d), on ground only, with no boundary
# drawn anywhere. It replaces the dormant floor ring, which was on screen for 72% of the
# match and was most of the reason the object read as a circle.
ANCIENT_HEAVE_SPEED: Final[float] = 24.0
ANCIENT_HEAVE_ARCS: Final[int] = 3
ANCIENT_HEAVE_GAP_S: Final[float] = 0.35
# Three arcs of heave crossing the floor during the four lethal seconds, clipped to the
# lobe. This REPLACES the three flashes at 6 Hz: one hammer falling and a wave leaving it is
# legible, and a strobe is part of why the object read as a generic damage zone.
SCOUR_DRAW_ORDER: Final[int] = 1
LOBE_DRAW_ORDER: Final[int] = 2            # image, then the two contours, then the heave
ASSAYER_DRAW_ORDER: Final[int] = 5         # the body, over its own floor marks
TRUTH_OVERLAY_ORDER: Final[int] = 12       # comets, glyphs, tether: never behind anything
# Draw order in the truth scene, stated once. The machine is depth-tested against the cave
# and its floor marks are not, so the order is what keeps a mast in front of its own lobe.

# ---- what damage looks like ----------------------------------------------------------------------
# THE-MACHINERY 4.7. Three marks and no new widget: the glyph degrades into the wreck it is
# becoming, one rail row carries the number, and the tether -- which already lengthens --
# lengthens faster. Prefer this to a world-space bar: a 1.6-cell bar is 50 px at CLOSE and
# 9 px at WIDE, and WIDE is where the director sits for most of the match.
DAMAGE_TINT_FROM: Final[float] = 0.30
# Above this the machine's own colour walks toward KILL. It is the only damage display of
# the four proposed that reads at CAMERA_WIDE_CELLS, where a glyph is nine pixels and no
# text anywhere on screen is legible: thinner, redder, and it has stopped looking.
DAMAGE_HATCH_1: Final[float] = 0.34
DAMAGE_HATCH_2: Final[float] = 0.67
# The three hull hatch strokes drop front-to-back at these two thresholds, so a damaged
# machine is visibly THINNER -- the hatching is what makes a line drawing read as a solid,
# and losing it is the glyph walking toward the wreck cross it becomes at 1.0.
DAMAGE_HEAD_SLOW_FROM: Final[float] = 0.45
DAMAGE_HEAD_STOP_FROM: Final[float] = 0.80
# The sensor head is the one mark that says alive and still LOOKING, so halving its turn
# and then stopping it reads instantly as a machine that has stopped watching.
DAMAGE_HURT_FROM: Final[float] = 0.20      # = DAMAGE_RANGE_FROM: the first rung of the ladder
DAMAGE_LIMPING_FROM: Final[float] = 0.30   # = DAMAGE_SPEED_FROM: the second one
# What the CONDITION row calls it. Tied to the two rungs above rather than chosen: "hurt" is
# the word from the moment the transducer has actually gone short, "limping" from the moment
# the drive has slowed. The row shows hull REMAINING, so the 0.493 dose the 5:41 near miss
# delivers reads "limping, 51%".

# ---- policies ---------------------------------------------------------------------------------
CAUTIOUS_PING_COOLDOWN_S: Final[float] = 24.0
AGGRESSIVE_PING_COOLDOWN_S: Final[float] = 8.0
PING_ONLY_IF_UNMAPPED_AHEAD: Final[bool] = True
MIN_POINTS_AHEAD: Final[int] = 40
CAUTIOUS_RETURN_SIGMA: Final[float] = 16.0
# Measured: at 26 the ellipse never reached the trigger in a whole match, so the
# cautious agent's defining rule never fired once and it was cautious in name only.
# At 12 it fired at 3:31, ahead of the spoof, and pre-empted the player's only
# command. 16 puts the natural return after the lie has already collapsed sigma.
# Raised with the drift. Note that a fix collapses this, so the spoof silently disarms
# the agent's own self-preservation rule -- which is the design, not a bug.
WAYPOINT_REACHED: Final[float] = 5.0
MAP_LOOKAHEAD: Final[float] = 9.0                  # cells the steering reads off the map
MAP_ESCAPE_LOOKAHEAD: Final[float] = 18.0          # and when stuck, looking for an exit
# Measured: with steering on the 2.5-cell feeler alone, the spoofed agent spent 2:24
# to 8:00 inside one chamber, skipping every waypoint in turn, because each target was
# thirty cells off in truth and pointed into rock. It had a 26,000-point map and used
# none of it. Reading clearance off the map does not undo the lie -- it still thinks
# it is somewhere else -- but it finds the door.
STUCK_SECONDS: Final[float] = 5.0
ESCAPE_SECONDS: Final[float] = 9.0
ESCAPES_BEFORE_SKIP: Final[int] = 4
# 4 x (5 + 9) = 56 s of trying before a waypoint is abandoned. A lost agent should
# look like it is failing to get somewhere, not like it is stuck in a loop, and the
# difference between those two readings is how fast it gives up.
#
# Measured across eight seeds, after map-aware steering: at 2 the rival gave up on the
# machinery's chamber at 44-68 cells out in six of eight matches and never arrived,
# so the dwell that kills it never ran (reached 2/8, died 2/8). At 4 it reaches 5/8
# and dies 4/8, and the player's own longest stall is unchanged (median 88 s vs 90).
# At 8 the rival does no better and the player's stalls get longer. A finer occupancy
# grid was worse in every cell of the matrix. What still keeps it out in the remaining
# matches is the C3-to-ANC passage itself, which is a navigation-stack problem for
# Phase 3, not a number here.

# ---- recall -- the one player input --------------------------------------------------------------
RECALL_DELAY_S: Final[float] = 3.0
RECALL_LATENCY_PER_CELL: Final[float] = 0.02       # DESIGN: latency grows with depth
RECALL_BEACON_REACHED: Final[float] = 3.0
RECALL_SEARCH_PITCH: Final[float] = 3.2            # cells of radius per radian, so each
# loop steps out by 2*pi*3.2 = 20 cells, twice the shaft's 10-cell answering range.
# Wider and the search can circle straight past the shaft; tighter and it cannot cover
# the distance a spoof puts between belief and the truth before the match ends. Sweeping
# a 35-cell radius takes about 190 cells of walking, which is roughly three minutes --
# so a recall sent late genuinely cannot get home, and that is the decision.
# On recall the agent runs for the shaft it believes in, and if nothing is there it
# searches outward until the real transponder answers. That search is the only thing
# in the match that can undo a spoof, which is what makes the single command worth
# holding rather than spending early.

# ---- scripted events ----------------------------------------------------------------------------
ECHO_TIMES: Final[tuple[float, ...]] = (155.0, 156.5)
# Measured: at 2:15 the echo arrived on bearing 23 while the rival's own pings were a
# standing contact on bearing 13, inside the 18-degree merge window, so it was absorbed
# and never appeared as its own event. Lowering the merge angle does not help -- both
# sounds enter the chamber down the same passage. Moved to 2:35, after the spoof, when
# the agent is elsewhere and the bearings separate. Designer's pick of three levers.
# The same ping arriving a second time off a reflective chamber, on a different bearing
# because it came by a different passage. Scripted so the beat is guaranteed, but the
# mechanism is real: it is a second sound field from a second point.

# ---- display -------------------------------------------------------------------------------------
MAX_POINTS: Final[int] = 250_000
ELLIPSE_SIGMAS: Final[float] = 2.0
WALL_POINT_HEIGHT: Final[float] = 2.2

# ---- display: the spectator screen ---------------------------------------------------------------
# SPECTATOR-DISPLAY.md section 8. Only the constants slice 1 consumes are here; the rest
# of that block arrives with the slice that first reads it.
GLYPH_LENGTH_CELLS: Final[float] = 2.4      # 2x the true 0.6-cell footprint; at CLOSE that is 75 px
COMET_SECONDS: Final[float] = 20.0          # a moving gradient reads as motion at 6 px/s; a dot does not
TETHER_MIN_CELLS: Final[float] = 3.0        # below this the tether is noise, so it is thin and unlabelled
TETHER_HOT_CELLS: Final[float] = 12.0       # past this the gap is the story, and turns lie-yellow
TETHER_ALARM_CELLS: Final[float] = 30.0     # past this it is kill-red with a pip at each end
HAZARD_COUNTDOWN_FROM_S: Final[float] = 15.0  # the clock appears this long before lethal, so it is a wait
DEPTH_TINT_FLOOR: Final[float] = 0.45       # how dark the far end of the cave gets, by graph distance
STALL_SECONDS: Final[float] = 4.0           # a pause longer than this is a jam, not a manoeuvre
STALL_MOVE_CELLS: Final[float] = 0.3        # under a third of what a 0.5 s trail sample travels at speed
ERROR_SAMPLE_HZ: Final[float] = 2.0         # the rate the truth channel records error, for the traces

# ---- display: the third dimension ------------------------------------------------------------------
CAVE_WALL_HEIGHT_CELLS: Final[float] = 8.0  # tall enough to read as rock; measured: 3 reads as a kerb
CAVE_FACE_SHADES: Final[tuple[float, float, float, float]] = (0.84, 0.46, 0.62, 1.00)
# +x/+y/-x/-y: a fixed world light, so orbiting moves the shadows rather than carrying
# them. The spike's four values, rotated: it lit +x, and at the default azimuth of 0 the
# camera is south of the cave, so every face a viewer ever saw was the 0.46 one and the
# rock read as a flat brown field. The light is now south-east, which puts the brightest
# face on the rim the default camera is looking at.
CAVE_BASE_SHADE: Final[float] = 0.42        # the wall foot, so a wall has a visible vertical
CAVE_CAP_SHADE: Final[float] = 0.30         # the top of a rock cell, which at a 60-90 degree
                                            # elevation is most of what is on screen. At 0.90 the
                                            # cave read as a brown desert with dark cracks in it.
                                            # 0.30 puts the cap under even the darkest floor -- the
                                            # far end of the cave is DEPTH_TINT_FLOOR of the near
                                            # end -- so every room is lighter than the rock around
                                            # it at every depth, and the lit faces are the only
                                            # bright part of the stone. Dark tops, lit rims.
TETHER_Z_CELLS: Final[float] = 9.0          # one cell above the rock: a rope over the cave, not a floor line
ELEVATION_MIN_DEG: Final[float] = 60.0      # measured: below this an 8-cell wall hides over 23% of the floor
ELEVATION_MAX_DEG: Final[float] = 90.0
ELEVATION_DEFAULT_DEG: Final[float] = 72.0  # 92% of the floor visible, walls still showing their faces
CAMERA_WIDE_CELLS: Final[float] = 225.0     # the whole 200x120 cave across the main view, with a margin
CAMERA_CLOSE_CELLS: Final[float] = 40.0     # holds the 18-cell lethal disc and both machines; 31.3 px/cell
CAMERA_EASE_S: Final[float] = 1.2           # an ease, never a cut
CAMERA_MIN_DWELL_S: Final[float] = 6.0      # a camera that is always drifting is not trusted
CAMERA_MAX_HOLD_S: Final[float] = 45.0      # after this, cut to whatever is actually moving
CAMERA_NEAR_CELLS: Final[float] = 20.0      # two machines this close are one shot
CAMERA_HAZARD_WATCH_CELLS: Final[float] = 15.0
# Measured over seed 7: the nearest machine during windows 1-4 is 44.4 cells, and during
# window 5 the player is at 11.5 when the warning arms. Anything in 12..44 gives the beat
# sheet exactly, so this sits in the middle of that gap.

# ---- display: the spoof's held breath -----------------------------------------------------------------
SPOOF_ARM_CELLS: Final[float] = 5.5         # 5 s of arming at 1.1 cells/s, so the ring closes before the lie
SPOOF_ARM_LEAD_S: Final[float] = 8.0        # arming may not show earlier than this before SPOOF_AFTER_S,
                                            # or a beacon reddens in minute two for a lie that cannot fire

# ---- display: the screen ------------------------------------------------------------------------------
CANVAS_W: Final[int] = 1600                 # smallest width holding a 1252 main view, a 300 rail and 9 pt type
CANVAS_H: Final[int] = 900
HEADER_H: Final[float] = 52.0
TITLE_H: Final[float] = 26.0                # the main slot's title; the inset carries its own
TIMELINE_H: Final[float] = 150.0
MARGIN: Final[float] = 16.0
RAIL_W: Final[float] = 300.0                # words, never pictures
PIP_INSET_FRACTION: Final[float] = 0.24     # of the main view in each axis, so the two rectangles are
                                            # similar and a swap would rescale rather than reframe
MINIMAP_PX_PER_CELL: Final[float] = 1.0     # 200x120 into a 200x120 viewport: the image is never resampled
