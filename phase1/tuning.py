"""Every number in Phase 1, in one place. Edit here, nowhere else.

Units: cells (1 cell ~ 1 m), seconds, degrees. Sim runs at TICK_HZ; the match is
MATCH_SECONDS of sim time at real-time speed.

Reasoning for each value is in docs/PHASE-1-OPEN-QUESTIONS.md Part 4.
"""

# ---- time and scale ---------------------------------------------------------
TICK_HZ = 20
DT = 1.0 / TICK_HZ
MATCH_SECONDS = 8 * 60
EXTRACT_WINDOW_OPENS = 6 * 60 + 30     # DESIGN: last 90 s
EXTRACT_RADIUS = 4.0                   # cells from shaft centre, in truth
SEED = 7

AGENT_SPEED = 1.1                      # cells/s. 480 s => ~530 cells of travel
RIVAL_SPEED = 1.4                      # the aggressive one runs a lighter chassis
AGENT_TURN_RATE = 150.0                # deg/s
AGENT_RADIUS = 0.6                     # for wall collision

# ---- dead reckoning ------------------------------------------------------------
# Bias-dominated so the map ghosts instead of fuzzing. Signs are drawn per agent
# from SEED so the two agents lean differently.
DR_SCALE_BIAS = 0.03                   # fraction of distance travelled (along-track)
DR_HEADING_BIAS_DEG_PER_CELL = 0.035   # 100 cells -> 3.5 deg lean; lateral ghost ~3 cells
DR_POS_NOISE_PER_CELL = 0.03           # random walk std, cells per sqrt(cell)
DR_HEADING_NOISE_DEG_PER_CELL = 0.03
# The estimator's own model of its error (honest, roughly matches the above).
EST_SIGMA_ALONG_PER_CELL = 0.02
EST_SIGMA_HEADING_RAD_PER_CELL = 0.0004
EST_SIGMA_AFTER_FIX = 0.5
EST_HEADING_SIGMA_AFTER_FIX = 0.02
HEADING_FIX_GAIN = 0.7                 # how much of the inferred heading error a fix removes

# ---- passive acoustic ---------------------------------------------------------
# Ranges are path length through the cave (sound follows passages), in cells.
# Flooded cells count FLOODED_COST per cell: water carries sound further.
FLOODED_COST = 0.55
HEAR_MOTION_RANGE = 40.0               # rival walking
HEAR_PING_RANGE = 170.0                # rival sonar; essentially the whole cave
HEAR_ANCIENT_RANGE = 80.0
HEAR_CRASH_RANGE = 170.0               # an agent dying is loud
BEARING_NOISE_NEAR_DEG = 4.0           # at zero range
BEARING_NOISE_FAR_DEG = 22.0           # at max range for that source
MOTION_LISTEN_PERIOD = 0.5             # s between passive samples of a moving rival
CONTACT_MERGE_DEG = 18.0               # returns within this bearing merge into one contact
CONTACT_MERGE_S = 8.0
CONTACT_FADE_S = 14.0                  # bearing line fades out over this after last return
SELF_DEAF_AFTER_PING_S = 1.0

# ---- active sonar --------------------------------------------------------------
SONAR_ARC_DEG = 120.0
SONAR_RAYS = 60
SONAR_RANGE = 30.0
SONAR_RANGE_NOISE = 0.25               # cells, plus 2 % of range
SONAR_BEARING_NOISE_DEG = 1.2
SONAR_FALSE_RETURNS = 2                # spurious points per ping
SONAR_FALSE_QUALITY = (0.12, 0.35)
SONAR_AUDIBLE_S = 3.0                  # 'audible' flag after a ping
WAVEFRONT_SPEED = 28.0                 # cells/s. Fake, for legibility.
WAVEFRONT_LIFE_S = 6.0

# ---- near-field sense (approved as the fourth, tiny sensor) -----------------------
NEARFIELD_RANGE = 2.5
NEARFIELD_RAYS = 8
NEARFIELD_PERIOD_TICKS = 4
NEARFIELD_QUALITY = 0.28

# ---- beacons --------------------------------------------------------------------
BEACON_DROP_EVERY_CELLS = 30.0
BEACON_RANGE = 8.0                     # acquisition, euclidean, one-shot on entering range
BEACON_FIX_NOISE = 0.35                # cells
SHAFT_BEACON_RANGE = 10.0              # survey-placed, the only truth anchor
SHAFT_FIX_PERIOD_S = 2.0               # the shaft beacon keeps fixing you while in range
HOME_REACHED = 1.5
SPOOF_AFTER_S = 2 * 60 + 45            # earliest time the scripted spoof may arm (fires on the next drop + lie distance)
SPOOF_LIE_CELLS = 12.0                 # how far the cloned beacon is from the original
SPOOF_AHEAD_CELLS = 4.0                # clone placed this far ahead of the victim

# ---- ancient system ---------------------------------------------------------------
ANCIENT_PERIOD_S = 42.0
ANCIENT_WARNING_S = 9.0                # signature before lethal
ANCIENT_LETHAL_S = 6.0
ANCIENT_RADIUS = 9.0                   # lethal footprint, cells
ANCIENT_PHASE_S = 20.0                 # cycle offset at match start
ANCIENT_HOLD_QUALITY = 0.45            # cautious policy stops when signature contact is this strong

# ---- policies -------------------------------------------------------------------
CAUTIOUS_PING_COOLDOWN_S = 24.0
AGGRESSIVE_PING_COOLDOWN_S = 8.0
PING_ONLY_IF_UNMAPPED_AHEAD = True     # cautious: ping only when < MIN_POINTS_AHEAD known
MIN_POINTS_AHEAD = 40
CAUTIOUS_RETURN_SIGMA = 8.0            # cells; go home when ellipse exceeds this (~230 cells after a fix)
LOAD_SECONDS = 30.0
CARGO_CAPACITY = 2
WAYPOINT_REACHED = 5.0
STUCK_SECONDS = 7.0                    # no progress for this long -> wall escape
ESCAPE_SECONDS = 9.0                   # follow the clearest direction for this long
ESCAPES_BEFORE_SKIP = 3

# ---- recall ---------------------------------------------------------------------
RECALL_DELAY_S = 3.0                   # command latency
RECALL_BEACON_REACHED = 3.0

# ---- display ---------------------------------------------------------------------
MAX_POINTS = 250_000
ELLIPSE_SIGMAS = 2.0
