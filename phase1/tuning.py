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
# Only while it is running the survey; a machine that has turned for home stops marking.
# Dropping every 20 cells once it had given up on the survey was tried and reverted --
# measured, it deleted the spoof from 8 recall-at-2:00 matches out of 8. The clone is
# placed on the victim's most recent beacon and the lie only fires once the victim is
# thirty cells clear of it, which a beacon every twenty cells never allows. It bit at
# exactly one recall timing, 2:00, because that is the only one where the agent is
# already home-bound when SPOOF_AFTER_S arrives -- and 2:00 is the timing that extracts.
# A denser chain while lost is not a bad idea; it is a bad idea to lay it across the
# thing the whole test is built to show.
# Measured: a beacon answers within 6 cells of where it truly is, and the agent walks to
# where it RECORDED it. The gap between those is the drift since the drop -- median 4-10
# cells for a beacon under a minute old and 8-69 for one over three minutes -- so after
# the spoof the chain is mostly out of range by the time the agent goes back for it, and
# the second half has no map fixes at all in the worst seeds. Marking more densely while
# lost is the part of that this file can fix; the rest is recorded in BEACON_RANGE.
BEACON_RANGE: Final[float] = 6.0
# Acquisition range is deliberately far below the drop interval. If it were not, the
# agent would never leave its own chain, drift would never accumulate, and there would
# be nothing to look at. The gap between 6 and 45 is where the smear happens.
# Measured, sweeping 6/9/10/11/12/16 over eight seeds: raising this does NOT reliably
# close the second-half fix drought, it only moves which seeds have it -- worst gap by
# seed was 107-254 s at 6, 101-181 at 9, 97-191 at 12. What it does do reliably is
# collapse the estimator's own sigma (max 6.2-17.3 at 12 against 7.1-34.0 at 6), which
# retires the cautious agent's "too lost to continue" rule, and it re-rolls every path:
# at 10 the PLAYER walked into the machinery in four seeds of eight, and at 9 the spoof
# on seed 6 slipped from 2:26 to 4:49. So it stays at 6 and the drought is reported
# rather than tuned away. The honest fix is not a number here: with HEADING_FIX_GAIN at
# 0.0 the drift is ~0.26 cells per cell walked, so keeping a beacon acquirable for the
# three minutes it takes to be re-crossed would need a range near 35. The only marker in
# the cave whose recorded position does not drift is the survey-placed shaft, and
# reaching that one is exactly what Recall buys.
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

JAM_SECONDS: Final[float] = 2.5                    # pressed against rock this long is a jam
JAM_MOVE_CELLS: Final[float] = 0.5                 # ground covered that proves it is not
# A jam is a different failure from "no progress toward the waypoint", and until now
# the policy could only see the second. Measured over eight seeds: the agent was
# commanding a step and achieving nothing for 1-27% of ticks, longest unbroken run
# 59.3 s, and belief froze exactly as hard as truth because odometry of a swallowed
# step reports zero. So the jam is visible in Belief -- dist_total stops -- and the
# answer to it is different: not "try harder toward the target", but "the heading you
# are holding is into rock, pick another one now" rather than in nine seconds.
# 2.5 s at 1.1 cells/s is two cells of nothing, which no manoeuvre needs.
ESCAPE_REPEAT_ARC_DEG: Final[float] = 50.0         # an escape this close to one that just
ESCAPES_REMEMBERED: Final[int] = 4                 # failed is not a new idea
# Measured: seven consecutive escapes on seed 7 all chose 170-180 degrees, into 0.2-3.2
# cells of true clearance, while 290 degrees stayed open at forty cells for the whole
# 81-second freeze -- because the inputs to the choice had not changed, so neither had
# the answer. Four remembered at 50 degrees rules out a 200-degree arc at worst, which
# still leaves most of the circle; remembering more boxed it in against a real dead end.

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

# ---- the event feed -------------------------------------------------------------------------------
# The feed selects by news, not by clock. Measured before this: 636 sounds heard on
# seed 7, 481 past the quality gate, 50 lines printed, and 34 of the 50 were one of two
# sentences arriving every 16.0 s +/- 0.1 for the whole match -- the rival pings on an
# 8 s cooldown and the feed admitted the first window past its 12 s wall-clock, which is
# always the third one. The longest silence in four of eight matches was 16.0 s, so
# nothing in the feed could land as an event; a metronome teaches a viewer to stop
# looking. These numbers replace that clock with three questions: is this the first I
# have heard of it, has it swung round, is it closer than when I last spoke.
#
# Measured after, over eight seeds: 18-30 lines a match against 27-57; no single line
# more than 20-42% of a feed against 34-52%; 11-14 distinct lines against 9-11; and the
# longest quiet stretch now 48-70 s, where four seeds in eight previously could not go
# quiet for longer than 16.0 s. Fewer lines, and each one is something that changed.
FEED_CONTACT_FORGET_S: Final[float] = 40.0   # unheard this long and its return is news again
FEED_CONTACT_TURN_DEG: Final[float] = 70.0   # a swing this wide is a contact that went somewhere
# A return at the 0.45 quality gate carries about 14 degrees of bearing noise, halved
# again by the smoothing, so this is well clear of a standing contact announcing that it
# moved. It is also the number that decides how much of the feed is bearing chatter:
# measured over eight seeds, at 40 degrees "the pinging has swung round" was 26-42% of
# every feed, at 55 it was 17-32%, and at 70 it is 15-25%.
FEED_CLOSER_QUALITY: Final[float] = 0.15     # louder by this much is "closer", ~15% of hearing range
FEED_CONTACT_SMOOTH: Final[float] = 0.5      # the halving Contact.absorb already uses
FEED_CONTACT_HOLD_S: Final[float] = 30.0     # having just spoken about a contact, wait
# Not a metronome: the change tests still have to pass, so this only sets a floor on how
# fast a genuinely moving contact can be narrated. Measured without it: a rival passing
# close swung the bearing 165 to 030 over 1.5 s and the feed printed four lines about it.
FEED_FIX_CELLS: Final[float] = 2.0           # announce an ordinary fix only this big
# Reverted from 4.0 on instruction. First, what this number is NOT: it decides only
# whether the feed prints a line. It cannot change how many fixes happen, how far any of
# them moves the estimate, or what the point cloud does on screen -- verified by running
# the same eight seeds at 2.0 and at 4.0, no recall and Recall at 2:00, and comparing:
# identical paths, identical fix lists, to the cell. So the jump-size distribution can
# never be an argument about this number.
#
# What it does decide is a straight trade, measured over eight seeds each way:
#            largest single line        longest silence in the feed
#   2.0      14-42% no-recall           30.8-69.8 s no-recall
#            20-33% Recall 2:00         69.5-112.0 s Recall 2:00
#   4.0      15-26% no-recall           37.5-69.8 s no-recall
#            23-25% Recall 2:00         101.5-195.3 s Recall 2:00
# At 2.0 one seed prints "position fix, corrected 2 cells" fifteen times, 42% of its
# whole feed, about a snap that is 1% of the picture -- which is the metronome the feed
# work exists to kill. At 4.0 the Recall run prints no fix line at all and goes silent
# for up to 195 s while the agent searches -- which is the dead air the same work exists
# to kill. Both readings cannot be had from one number. Which one the gate cares about
# is a viewing question, so it stays where it was told to stay and this note is the lever.
HAZARD_REPEAT_S: Final[float] = 25.0         # one warning per firing: shorter than the
                                             # 75 s cycle, longer than the 9 s signature
# Deliberately a clock, and the only one left in the feed. The signature is audible for
# ANCIENT_WARNING_S = 9 s before each firing, so anything from 10 to 74 here prints
# exactly one line per cycle; 25 is the middle of that and says so. Four warnings a
# match at clock-exact 75.0 s spacing is not the metronome the contact work removed --
# it is THE-MACHINERY.md section 3's fixed cycle being legible, which is what a player
# has to hear six times to learn. Raise it above 75 to print fewer.
FEED_REPEAT_COOLDOWN: Final[float] = 6.0     # the same sentence AND the same bearing, twice, is not news
# Keyed on the sentence and its detail together, which is the fault the old cooldown
# had: the bearing was not part of the key, so a contact ninety degrees away was
# indistinguishable from the one already standing there.

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

# ---- sound: the cave ---------------------------------------------------------------------------------
# The gate failed on "all that changes is things kinda beep". A tick-by-tick replay of
# seed 7 found the cause: 587 audible events, 80% of them one of two recipes, every one
# built from the same 6 ms attack and linear fade, none filtered -- so AMPLITUDE was the
# only channel in use, and amplitude alone cannot say far, near, closing, mine, theirs,
# winding up, or dead. Everything below exists to open a second, third and fourth channel.
#
# Quality is the distance proxy the sensor already produces (q = 1 - path/range), so every
# one of these is a function of q.
#
# THE REGISTER RULE, and it is the one that cost a gate. Every sound here has to carry its
# weight ABOVE 300 Hz, because the gate is a human watching a rendered video and a laptop
# speaker is a 300 Hz / 12 dB-per-octave high-pass. The first rework put the two most
# dramatic sounds in the match -- the crash and the hammer -- almost entirely below that:
# 96.4% and 99.9% of their energy under 150 Hz, centroid 95 Hz. Measured through the
# model, the crash went from 2.7 dB ABOVE the loudest routine ping to 4.9 dB BELOW it, and
# the hammer lost 14.6 dB where a ping lost none. So the two things that were supposed to
# be unmissable were the two that disappeared on the only machine anyone watched on.
#
# The rule that follows: low end is for weight on good playback, never for legibility. If
# a sound has to be *identified*, something in it lives between 400 Hz and 3 kHz -- a
# strike, a ring, a snap, a shriek. Rock and steel really do make those; the low end alone
# was never honest either.
HAZARD_GAIN_FLOOR: Final[float] = 0.78         # a lethal strike and a death do not fade with
                                               # distance the way a ping does: their placement
                                               # gain is floored here, so the far ones still
                                               # arrive above every routine sound. Distance is
                                               # still in them -- brightness, attack, the room,
                                               # and the 1.7 dB of level this leaves -- but
                                               # level alone no longer decides whether the
                                               # loudest event in the match is audible. The
                                               # cost is real and it is stated in Mixer.hammer.
HAZARD_BRIGHT_FLOOR: Final[float] = 0.45       # and their strike keeps most of its partials at
                                               # range for the same reason: a hammer two
                                               # chambers away should be a duller hammer, not a
                                               # sine. Distance still thins it, from 1.00 to
                                               # 0.45 rather than to nothing.

# Level. The old spread was 10.7 dB across the whole match, which is a volume knob nobody
# notices moving over two minutes. 0.10..1.00 with a 1.7 power is 20 dB, and the power
# puts most of the travel in the near half where the drama is.
AUDIO_FAR_GAIN: Final[float] = 0.10
AUDIO_NEAR_GAIN: Final[float] = 1.00
AUDIO_GAIN_CURVE: Final[float] = 1.7

# Brightness. Rock and water are low-pass filters: a sound that came 150 cells through
# passages has no top left. Implemented as the height of the partial stack on a tonal
# voice and as the low-pass width on a noise one, so a far sound is a fundamental and a
# near one has edge. This is the cue the old mixer lacked entirely and it is the one the
# ear actually uses for distance.
AUDIO_BRIGHT_CURVE: Final[float] = 1.25
AUDIO_PARTIAL_2: Final[float] = 0.35        # second harmonic at full brightness
AUDIO_PARTIAL_3: Final[float] = 0.18        # third
AUDIO_NOISE_LP_DULL: Final[int] = 74        # moving-average width; ~265 Hz at 44.1 kHz
AUDIO_NOISE_LP_BRIGHT: Final[int] = 3       # ~6.5 kHz: a crack rather than a rumble

# Attack. A transient that has crossed a cave arrives smeared; one from ten cells away is
# a crack. 3 ms to 45 ms is the difference between "hit" and "swelled".
AUDIO_ATTACK_NEAR_S: Final[float] = 0.003
AUDIO_ATTACK_FAR_S: Final[float] = 0.045

# The room. Discrete arrivals rather than a reverb: the cave really does deliver a sound
# twice down two passages, and three delayed voices cost less than any convolution. The
# ratio is the distance cue -- close to a source you hear the source, far from it you hear
# mostly the room, because the reverberant field barely falls off with distance.
AUDIO_REFLECT_NEAR_FRAC: Final[float] = 0.10   # reflection level as a fraction of direct
AUDIO_REFLECT_FAR_FRAC: Final[float] = 0.55
AUDIO_REFLECT_FLOOR: Final[float] = 0.07       # below this a reflection is not worth a voice,
                                               # so near sounds get one and far sounds three
AUDIO_REFLECT_DELAY_NEAR_S: Final[float] = 0.035
AUDIO_REFLECT_DELAY_FAR_S: Final[float] = 0.085
AUDIO_REFLECT_SPACING: Final[tuple[float, float, float]] = (1.0, 2.15, 3.6)
AUDIO_REFLECT_LEVELS: Final[tuple[float, float, float]] = (1.0, 0.62, 0.38)
AUDIO_REFLECT_DULLING: Final[tuple[float, float, float]] = (0.55, 0.38, 0.26)
AUDIO_REFLECT_SPREAD: Final[float] = 0.75      # how far off the direct pan the room answers;
                                               # a far sound becomes wide and a near one a point
AUDIO_REFLECT_STRETCH: Final[float] = 0.9      # extra duration on a reflection, as a fraction
AUDIO_REFLECT_MAX_TAIL_S: Final[float] = 0.45  # but capped, or a crash's reflections are
                                               # five seconds of saw built inside one frame

# Direction. Pan is the screen-x component of the bearing. Stereo has one axis and cos()
# folds north onto south exactly, so two contacts on opposite sides pan identically, and
# THERE IS NO FRONT/BACK CUE. There was one: a small brightness and level tilt off the
# screen-y component. It was measured and deleted, because it was worse than nothing --
# the tilt came to 1.74 dB on the same channel where distance moves 20 dB, so a north
# contact at q=0.70 was matched within 0.1 dB by a south contact at q=0.60. It could not
# be heard as direction and it could be heard as distance, which means the only thing it
# ever did was corrupt the distance cue. Two channels and no HRTF cannot carry front/back;
# saying so is cheaper than a parameter only a spectrogram can see.

# Distance, in pitch. Base pitch comes from proximity -- a near contact speaks higher --
# which is the fifth channel distance is expressed on, alongside level, brightness, attack
# and the room. It is NOT an approach cue: measured over 62 gestures the median step
# between consecutive transmissions was 0.20 semitones, which is a drift nobody hears.
# Approach is an event now; see AUDIO_APPROACH_* below.
AUDIO_DISTANCE_SEMITONES: Final[float] = 9.0   # across the whole quality range
AUDIO_DISTANCE_REFERENCE_Q: Final[float] = 0.5 # the pitch a mid-range contact sits at

# Approach, as an EVENT. A contact that has closed materially since the last time that
# bearing spoke is answered by a SECOND note, a fifth above the first and slightly
# louder, a fifth of a second behind it. One transmission, two notes, stepping up: that is
# a different gesture from the same contact holding station, not the same gesture 0.2 of a
# semitone higher. The rising pair is in the ping's own register, so it survives a laptop
# speaker, and it replaces the closing chirp, which measured 13.1 dB under the ping's own
# tail and could not be heard at all.
AUDIO_APPROACH_STEP_Q: Final[float] = 0.055    # a jump this big since the last time this
                                               # bearing sounded is an approach.
                                               # Measured over seed 7: at 0.10 it fired twice in
                                               # a match, because the rival closes over 143 s in
                                               # steps of about 0.04 of quality per transmission.
                                               # At 0.055 it fires through the approach and stops
                                               # once the rival is simply near.
AUDIO_APPROACH_INTERVAL: Final[float] = 7.0    # semitones between the two notes: a fifth
AUDIO_APPROACH_GAP_S: Final[float] = 0.22      # and how far behind the first the second is
AUDIO_APPROACH_SECOND_AMP: Final[float] = 1.15 # the second note is the louder one
AUDIO_TRACK_MERGE_DEG: Final[float] = 40.0     # bearing noise reaches 22 deg sigma at range,
                                               # so the gate has to be wide or one burst splits
AUDIO_TRACK_MEMORY_S: Final[float] = 45.0
AUDIO_PING_MERGE_S: Final[float] = 3.5         # SONAR_AUDIBLE_S plus a margin. One transmission
                                               # produced SIX identical beeps 0.5 s apart, which
                                               # is why the match sounded like a metronome and why
                                               # a listener had no reason to think it was one
                                               # event. One transmission is now one gesture.
AUDIO_PING_SEPARATE_DEG: Final[float] = 45.0   # unless it arrives from a clearly different
                                               # direction, which is a second arrival -- the
                                               # scripted echo, and it must survive the merge

# Whose sensor it was. The most important distinction on screen, and it was carried by a
# fifth and a pan. It is now categorical on three axes at once: the own ping is the only
# RISING sweep in the game, the only hard-centred world sound, and the only one followed by
# the room answering it -- which is what a sonar transmission physically is.
AUDIO_OWN_PING_F0: Final[float] = 620.0
AUDIO_OWN_PING_F1: Final[float] = 2100.0       # above the heard band even at full approach
AUDIO_OWN_PING_S: Final[float] = 0.30
AUDIO_OWN_PING_AMP: Final[float] = 0.089
AUDIO_OWN_WASH_DELAYS: Final[tuple[float, ...]] = (0.31, 0.40, 0.55, 0.75)
# The wash starts after the chirp has finished, not under it. Measured: with the first
# return at 0.10 s the wash's falling voices sat on top of the rising sweep and the
# gesture's spectral centroid came out FALLING -- the one cue that says "this one is
# mine" was cancelled by the cue that says "and the room answered". A room cannot
# answer before the ping has got there anyway.
AUDIO_OWN_WASH_LEVELS: Final[tuple[float, ...]] = (0.30, 0.22, 0.15, 0.10)
AUDIO_OWN_WASH_PANS: Final[tuple[float, ...]] = (-0.7, 0.8, 0.5, -0.9)
AUDIO_OWN_WASH_F0: Final[float] = 980.0        # the room answers lower and duller than it was asked
AUDIO_OWN_WASH_S: Final[float] = 0.55

# Somebody else's sonar: falling, panned, reverberant. Base pitch shifts with proximity.
AUDIO_HEARD_PING_F0: Final[float] = 760.0
AUDIO_HEARD_PING_FALL: Final[float] = 0.62     # sweeps down to this fraction of f0
AUDIO_HEARD_PING_S: Final[float] = 0.34
AUDIO_HEARD_PING_AMP: Final[float] = 0.122

# Something moving. The only unpitched, non-catastrophic sound in the game: a scrape, in
# grains, so it reads as rubbing rather than as a quieter beep.
AUDIO_SCRAPE_S: Final[float] = 0.13
AUDIO_SCRAPE_AMP: Final[float] = 0.089
AUDIO_SCRAPE_GRAINS: Final[int] = 3
AUDIO_SCRAPE_GAP_S: Final[float] = 0.085
AUDIO_SCRAPE_LP: Final[int] = 42               # ~470 Hz: below the ping band, above the machinery

# The machinery. THE-MACHINERY.md: a hammer ratcheted up a mast and dropped. So the warning
# is a countable ratchet that accelerates and climbs, then a held breath, then the drop.
# The old version pulsed 70-110 Hz sine at 1.7 dB of rise over thirteen seconds and stopped
# accelerating at the instant it became lethal, which is the opposite of an alarm.
#
# Progress through the wind-up is read from Belief alone as the ratio of the signature's
# current quality to its quality at the start of this cycle. Quality is (1 - d/range) x
# strength, and strength ramps from a floor to 1.0, so that ratio recovers strength without
# knowing the distance -- which is why a DISTANT machinery now winds up audibly too, where
# before it moved 1.7 dB and nobody could hear it.
# NOTE: SIGNATURE_RATIO_AT_LETHAL is one over the floor of Ancient.signature_strength. If
# that ramp is ever rewritten this number moves with it; a wrong value degrades to a
# shallower ratchet rather than to a broken one.
SIGNATURE_RATIO_AT_LETHAL: Final[float] = 3.33
RATCHET_SLOW_S: Final[float] = 1.05            # notch spacing at the start of the warning
RATCHET_FAST_S: Final[float] = 0.115           # and at the top: ~24 countable notches over 9 s
RATCHET_F0: Final[float] = 84.0                # the body of the pawl
RATCHET_METAL_F0: Final[float] = 940.0         # and its ring, which is what carries on a laptop
RATCHET_CLIMB_SEMITONES: Final[float] = 14.0   # the mast, being climbed
RATCHET_PARTIALS: Final[tuple[float, ...]] = (1.0, 2.76, 5.4)   # struck-bar ratios: metal, not tone
RATCHET_AMP: Final[float] = 0.25               # the wind-up sits about 10 dB under the loudest
                                               # routine ping and 19 under the hammer it leads
                                               # to. It was 18.5 under the PING before, which is
                                               # a long way down for the one sound in the game
                                               # that is a countdown to being killed.
# The ring was 11 dB under the body, so what a listener actually heard climbing was the
# BODY going 84 -> 188 Hz, which a laptop does not reproduce: the wind-up was audible on
# the gate machine by accident, not for the reason the design claims. The two levels are
# now the other way round. The body is the weight; the ring is the pawl, and the ring is
# what climbs the mast in a register a small speaker has.
RATCHET_BODY_LEVEL: Final[float] = 0.50        # fraction of RATCHET_AMP
RATCHET_RING_LEVEL: Final[float] = 1.00
RATCHET_RING_BRIGHT_FLOOR: Final[float] = 0.55 # the ring survives distance: a far pawl is
                                               # duller but it is still a pawl
RATCHET_CLICK_HP: Final[int] = 96              # ~200 Hz: the pawl's click is a click, and is
                                               # kept out of the body's register
RATCHET_BREATH_DUCK: Final[float] = 0.10       # what everything already sounding is pulled to
RATCHET_BREATH_DUCK_S: Final[float] = 0.10     # when the ratchet tops out and the breath starts
RATCHET_CYCLE_GAP_S: Final[float] = 4.0        # no signature for this long ends the cycle
RATCHET_TOP_SLOPE_FRACTION: Final[float] = 0.35  # when the quality ramp falls to this fraction of
                                               # its own peak the ratchet has topped out -- which
                                               # is the moment strength stops rising, which is the
                                               # moment the hazard becomes lethal
RATCHET_MIN_CYCLE_S: Final[float] = 7.5        # never call the top before this much of a wind-up.
# Measured over seed 7's four cycles: three of them top out at 9.5-10.0 s and the hammer
# lands 1.2-1.8 s into the lethal window, which is right. The fourth is the cycle the
# agent spends walking AWAY from the machinery at nearly full speed, and there the
# distance loss very nearly cancels the strength gain -- quality rises by a factor of
# 1.55 over thirteen seconds instead of 3.33 -- so the ramp genuinely flattens and the
# detector called the top at 3.0 s and dropped the hammer 5.2 s early. At 7.5 it cannot,
# and that cycle now reads as a short quiet wind-up receding, which is what it is. This
# is the honest limit of the signal: an agent that hears one bearing cannot separate
# 'it is winding up' from 'I am walking toward it', and neither can the mixer.
RATCHET_BREATH_S: Final[float] = 0.75          # the held breath. The brief is explicit that the
                                               # moments before it fires should get QUIETER, and
                                               # silence is the only thing that makes a hit land.
                                               # Nothing enforced that: _quiet_until was set by a
                                               # crash and by nothing else, so in two of seed 7's
                                               # four cycles the thing sitting in the silence was
                                               # as loud as the hit. The mixer now ducks what is
                                               # sounding and starts nothing routine while the
                                               # ratchet is topped out.

# The hammer. Steel, dropped down a mast, onto rock. Four things happen at once and only
# two of them used to be above 300 Hz -- the old hammer was 99.9% under 150 Hz, centroid
# 95 Hz, and lost 14.6 dB through the laptop model while a ping lost nothing. The strike
# and the anvil ring are the fix: they are what a struck mast actually does, and they are
# what a small speaker can reproduce. The body and the rock ring stay, because on real
# playback they are the weight, and they are now the smaller half of the sound.
HAMMER_AMP: Final[float] = 0.65
HAMMER_CRACK_S: Final[float] = 0.14
HAMMER_CRACK_DECAY_S: Final[float] = 0.055     # an 18 ms crack was all peak and no level
HAMMER_CRACK_HP: Final[int] = 78               # ~250 Hz: a snap, not a thump
HAMMER_STRIKE_F0: Final[float] = 780.0         # steel meeting steel, struck-bar partials
HAMMER_STRIKE_F1: Final[float] = 690.0
HAMMER_STRIKE_S: Final[float] = 0.28
HAMMER_STRIKE_DECAY_S: Final[float] = 0.13
HAMMER_STRIKE_LEVEL: Final[float] = 0.90       # fraction of HAMMER_AMP
HAMMER_STRIKE_PARTIALS: Final[tuple[float, ...]] = (1.0, 2.76, 5.4)
# The four voices do not all start at once, because a hammer does not: steel arrives, the
# mast rings, the mass goes into the rock. A few milliseconds apart is honest and it is
# also what stops five voices summing into one enormous sample -- with everything landing
# on the same instant the hammer peaked at 2.4 of full scale, which the offline render
# normalises away and the live callback clips.
HAMMER_ANVIL_DELAY_S: Final[float] = 0.018
HAMMER_BODY_DELAY_S: Final[float] = 0.012
HAMMER_RING_DELAY_S: Final[float] = 0.038
HAMMER_ANVIL_F0: Final[float] = 470.0          # and the mast ringing afterwards, which is the
HAMMER_ANVIL_F1: Final[float] = 442.0          # part that is still there a second later
HAMMER_ANVIL_S: Final[float] = 1.15            # every duration here is about two decay
                                               # constants: past that the tail is inaudible and
                                               # all it costs is transcendentals built on the
                                               # game thread, inside a frame
HAMMER_ANVIL_DECAY_S: Final[float] = 0.60
HAMMER_ANVIL_LEVEL: Final[float] = 0.85
HAMMER_ANVIL_PARTIALS: Final[tuple[float, ...]] = (1.0, 2.09, 3.42)
HAMMER_BODY_F0: Final[float] = 135.0
HAMMER_BODY_F1: Final[float] = 34.0
HAMMER_BODY_S: Final[float] = 0.75
HAMMER_BODY_LEVEL: Final[float] = 0.45         # was 1.0, and it was most of the peak and none
                                               # of the audibility
HAMMER_RING_F0: Final[float] = 52.0            # the shock going into the rock
HAMMER_RING_S: Final[float] = 1.60
HAMMER_RING_LEVEL: Final[float] = 0.22         # was 0.60: 25 dB of it is lost on a laptop, so
                                               # it was buying headroom and nothing else
HAMMER_RING_PARTIALS: Final[tuple[float, ...]] = (1.0, 1.48, 2.11)
HAMMER_DUCK: Final[float] = 0.40               # what everything else drops to when it lands
HAMMER_DUCK_S: Final[float] = 0.9

# Death. It was 3.3 dB above a routine beep, in the same speaker as the drone running over
# it, with the same envelope as everything else -- the most significant event in the match,
# buried. It now takes the room: everything sounding is ducked to a tenth and no routine
# gesture is allowed to start until it has spoken. That is honest -- a near hull failure
# masks everything -- and it is the single largest legibility win available.
#
# And it was 96.4% below 150 Hz, which meant the version that took the room took it only
# on speakers nobody watched the gate on. The tear is the answer: a hull coming apart
# shrieks before it thuds, and the shriek is the half of it a laptop can reproduce.
CRASH_AMP: Final[float] = 0.70
CRASH_SNAP_S: Final[float] = 0.16
CRASH_SNAP_DECAY_S: Final[float] = 0.055
CRASH_SNAP_HP: Final[int] = 62                 # ~310 Hz: the first instant is a crack
CRASH_TEAR_F0: Final[float] = 1250.0           # plating shearing: inharmonic, falling fast
CRASH_TEAR_F1: Final[float] = 430.0
CRASH_TEAR_S: Final[float] = 0.62
CRASH_TEAR_DECAY_S: Final[float] = 0.38
CRASH_TEAR_LEVEL: Final[float] = 0.85          # fraction of CRASH_AMP
CRASH_TEAR_PARTIALS: Final[tuple[float, ...]] = (1.0, 1.73, 2.61)
CRASH_TEAR_DELAY_S: Final[float] = 0.012       # the snap, the shriek, then the box going
CRASH_HULL_DELAY_S: Final[float] = 0.030       # -- not all on the same sample
CRASH_COLLAPSE_F0: Final[float] = 340.0        # the only downward SAW sweep in the game
CRASH_COLLAPSE_F1: Final[float] = 38.0
CRASH_COLLAPSE_S: Final[float] = 0.90
CRASH_HULL_F0: Final[float] = 62.0
CRASH_HULL_S: Final[float] = 2.00
CRASH_HULL_LEVEL: Final[float] = 0.36          # was 0.75, and 19 dB of it never left the sub
CRASH_HULL_PARTIALS: Final[tuple[float, ...]] = (1.0, 1.41, 2.07, 3.11)   # inharmonic: a box, torn
CRASH_DEBRIS: Final[int] = 5
CRASH_DEBRIS_S: Final[float] = 0.10
CRASH_DEBRIS_DECAY_S: Final[float] = 0.032
CRASH_DEBRIS_HP: Final[int] = 110              # ~176 Hz: rock hitting rock clatters
CRASH_DEBRIS_DELAYS: Final[tuple[float, ...]] = (0.13, 0.24, 0.37, 0.49, 0.62)
CRASH_DEBRIS_PANS: Final[tuple[float, ...]] = (-0.8, 0.6, -0.4, 0.9, -0.6)
CRASH_DUCK: Final[float] = 0.10
CRASH_DUCK_S: Final[float] = 0.05
CRASH_SUPPRESS_S: Final[float] = 1.30          # nothing routine may start inside this

# Instrument sounds -- fix, cargo, recall. These are the agent's own panel, not the world,
# so they are dry, centred and small, and they stay out of the way of everything above.
AUDIO_PANEL_AMP: Final[float] = 0.042
AUDIO_MAX_VOICES: Final[int] = 48              # was 24. A crash is fourteen voices and a wind-up
                                               # runs under it; measured concurrency peaked at 5
                                               # before and there is no cost to the headroom.

# ---- display: type, and the three levels of weight ------------------------------------------
# SPECTATOR-DISPLAY.md 6.2. Four sizes, nothing below nine points. The gate tester watched a
# compressed H.264 video, where 7.5 pt grey is not small -- it is absent. Four is a performance
# rule as well as a design one: 6.10 groups every chrome string into one Text visual per size,
# so a fifth size would be a fifth visual.
TYPE_DISPLAY_PT: Final[float] = 34.0        # the two error numbers, the match clock, the cold open
TYPE_HEAD_PT: Final[float] = 15.0           # titles, the action line, the now-line
TYPE_BODY_PT: Final[float] = 11.0           # chamber names, labels, the timeline clock
TYPE_MICRO_PT: Final[float] = 9.0           # units only -- "cells", "to go". The floor.
AMBIENT_MAX_LUMINANCE: Final[float] = 0.35  # 6.3's hierarchy rule as a number palette.py asserts
                                            # at import: an ambient value's relative luminance
                                            # never exceeds this fraction of the brightest
                                            # primary's, which is what stops a lit cave competing
                                            # with the bone machine standing on it

# ---- display: the readout row ------------------------------------------------------------------
# SPECTATOR-DISPLAY.md 3 and 6.9.1: two numbers of the same size under near-identical labels,
# the whole game in four words and two integers with no vocabulary to learn.
READOUT_RAMP_CELLS: Final[tuple[float, float, float]] = (3.0, 12.0, 30.0)
                                            # where IT IS WRONG BY steps tertiary -> primary ->
                                            # lie -> kill. Deliberately TETHER_MIN/HOT/ALARM: the
                                            # rope and the number are one fact drawn twice and
                                            # they may not disagree about how bad it is.
READOUT_FIX_HOLD_S: Final[float] = 2.5      # a fix underlines BOTH numbers for this long. At 1:44
                                            # both fall and the rule is taught; at 2:21.4 the same
                                            # mark fires and the left one leaps to 34.
READOUT_LABEL_GAP: Final[float] = 34.0      # px from a label down to its own number
READOUT_UNIT_GAP: Final[float] = 30.0       # px from a number down to its unit
READOUT_BLOCK_GAP: Final[float] = 38.0      # px between the two blocks. Close enough to read as a
                                            # pair; the eye must land on the numbers, not the gap.

# ---- display: the cold open ----------------------------------------------------------------------
# SPECTATOR-DISPLAY.md 3 and 7.5. Twenty-one words before the clock starts, and the only place in
# eight minutes anyone is told anything. Three of the four design proposals skipped it.
COLD_OPEN_S: Final[float] = 6.5             # long enough to read seven lines twice, short enough
                                            # that a viewer never wonders whether it is broken.
                                            # Six, until the card gained the two lines that say
                                            # which machine is which.
COLD_OPEN_LINE_S: Final[float] = 0.44       # each line lands this long after the one above it, so
                                            # the card is read in order rather than scanned. Seven
                                            # lines at 0.44 are all up 1.4 s before the fade starts;
                                            # at the old 0.60 the last one arrived as it began.
COLD_OPEN_FADE_S: Final[float] = 1.8        # the words go and the cave comes up over this, at the
                                            # end of the six. A cut here would read as a glitch.
COLD_OPEN_FROM_DEG: Final[float] = 90.0     # the camera starts flat and arrives at 72: the camera
                                            # arriving is what makes a plan resolve into a place

# ---- display: the rail's rows ----------------------------------------------------------------
# SPECTATOR-DISPLAY.md 3.5. The old panel put a 10.5 pt value at row_y + 14 with the next
# 7.5 pt label at row_y + 30, so every value struck through the label under it -- visible in
# every render of the display the gate failed on. Taller rows and bigger type, both.
STATUS_ROW_H: Final[float] = 44.0           # an 11 pt label and a 15 pt value, clear of each other
STATUS_VALUE_DROP: Final[float] = 21.0      # px from a row's label to its own value
STATUS_BAR_ROW_EXTRA: Final[float] = 22.0   # a row with a bar is taller, so the bar never lands
                                            # on the next row's label
STATUS_BAR_H: Final[float] = 5.0

# ---- display: the readout's one mark, and the card's ---------------------------------------------
READOUT_UNDERLINE_LEN: Final[float] = 96.0  # px. The same under both numbers, because it is one
                                            # mark saying "a correction landed", not a measurement
READOUT_UNDERLINE_DROP: Final[float] = 22.0 # px below a number's centre; clear of a 34 pt descender
COLD_OPEN_LINE_H: Final[float] = 68.0       # px between the card's lines at 34 pt. Loose: it is a
                                            # card, not a paragraph, and it is read in five beats.
COLD_OPEN_LINE_IN_S: Final[float] = 0.28    # each line arrives over this -- long enough not to
                                            # read as a flash, short enough not to be a transition
COLD_OPEN_SCRIM_HOLD: Final[float] = 0.55   # what the scrim settles to under the words, so the
                                            # cave comes up *beneath* them rather than after them
COLD_OPEN_SCRIM_S: Final[float] = 2.0       # how long it takes to get there from solid black
