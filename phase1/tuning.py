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
ESCAPES_BEFORE_SKIP: Final[int] = 2
# 2 x (5 + 9) = 28 s of trying before a waypoint is abandoned, down from 48 s. A lost
# agent should look like it is failing to get somewhere, not like it is stuck in a
# loop, and the difference between those two readings is how fast it gives up.

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
RECALL_SEARCH_SWEEP: Final[float] = 0.9            # unused: the spiral now sweeps at
                                                   # walking pace, speed / radius
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
