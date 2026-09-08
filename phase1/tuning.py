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
