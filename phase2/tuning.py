"""Every number in Phase 2, in one place. Edit here, nowhere else.

Units: cells (1 cell ~ 1 m), seconds, degrees. The sim runs at TICK_HZ.

The drift and estimator constants start from Phase 1's tuning.py; each one says
whether it was kept. Where a value was changed after a headless sweep, the
measurement that prompted it is written next to it. Those notes are the point of
this file.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Final

# ---- time and scale ---------------------------------------------------------------
TICK_HZ: Final[int] = 20                           # kept from Phase 1
DT: Final[float] = 1.0 / TICK_HZ
AGENT_SPEED: Final[float] = 1.1                    # cells/s, kept from Phase 1

# ---- the corridor -----------------------------------------------------------------
JUNCTIONS: Final[int] = 8                          # the spec's number
BRANCH_CHOICES: Final[tuple[int, ...]] = (2, 3)    # onward passages per junction, spec
PASSAGE_MIN_CELLS: Final[int] = 14                 # > SHAFT_BEACON_RANGE so the first
                                                   # junction is outside the beacon
PASSAGE_MAX_CELLS: Final[int] = 36                 # ~2.5x the minimum: long enough that
                                                   # a deep deposit sits 150-250 cells
                                                   # out and the trunk re-walks cost
                                                   # something, short enough that a
                                                   # full walk (~1000 cells) still fits
                                                   # inside one heading-bias sign
# A junction's onward passages leave within this many degrees of the direction the
# agent arrived by, and every pair of passages at a junction -- the way back
# included -- is at least PASSAGE_MIN_SEPARATION_DEG apart. Half that separation is
# the heading error at which the branch rule takes the wrong passage, so this pair
# of numbers is the size of drift's teeth: 25 degrees at the tightest junction.
ONWARD_MAX_OFFSET_DEG: Final[float] = 130.0
PASSAGE_MIN_SEPARATION_DEG: Final[float] = 50.0

# ---- dead reckoning ----------------------------------------------------------------
# Bias-dominated, as in Phase 1, so the error leans one way rather than fuzzing.
DR_SCALE_BIAS: Final[float] = 0.055                # kept from Phase 1
DR_POS_NOISE_PER_CELL: Final[float] = 0.03         # kept from Phase 1
DR_HEADING_NOISE_DEG_PER_CELL: Final[float] = 0.03 # kept from Phase 1
DR_HEADING_BIAS_DEG_PER_CELL: Final[float] = 0.055 # CHANGED from Phase 1's 0.11.
# What picks a passage is not heading error itself but the heading error accrued
# BETWEEN recording a junction's bearings and turning by them -- for the trip home
# through a junction, that is the whole walk below it. The bias is the same sign
# out and back, so a subtree walk of D cells turns the way home by bias * D. Against
# the 25-degree half-gap at the tightest junction, 0.11 misturns after ~230 cells of
# subtree, which is under most first junctions' subtrees: the depth-first policy was
# lost on nearly every seed. At 0.055 misturns begin after ~450 cells of subtree,
# which is what the deeper half of the seeds have below their first junction.
# Sweep, depth-first tree that ignores theta, successes per twenty seeds and over
# sixty (0..19 / 20..39 / 40..59 / total):
#   0.045  14 18 14  46/60 = 77%
#   0.05   13 16 14  43/60 = 72%
#   0.055  11 15 14  40/60 = 67%   <- chosen
#   0.06    9 15 13  37/60 = 62%
#   0.065   8 13 13  34/60 = 57%
#   0.07    8 13 10  31/60 = 52%
# The spec asks this tree to fail on roughly a third. One twenty-seed band settles
# that to +-10 points and the first run of this sweep was read off 0..19 alone,
# which put 0.05 at 65% there and 80% on 20..39 -- outside the band it was tuned
# for. Sixty seeds is the smallest sample that does not move that much: 0.055 fails
# on exactly a third of them, and no band is better than 75% or worse than 55%.

# The estimator's own model of its error -- all kept from Phase 1, so that sigma
# means the same thing it meant on the Phase 1 display. Position sigma is a function
# of distance walked since the last fix: about 9 cells at 100, 18 at 150, 30 at 200,
# 45 at 250, 63 at 300, 99 at 380. Cross-track dominates because heading sigma grows
# with distance and is multiplied by it.
EST_SIGMA_ALONG_PER_CELL: Final[float] = 0.038
EST_SIGMA_HEADING_RAD_PER_CELL: Final[float] = 0.0013
EST_SIGMA_AFTER_FIX: Final[float] = 0.5
EST_HEADING_SIGMA_AFTER_FIX: Final[float] = 0.02

# ---- sensing --------------------------------------------------------------------------
JUNCTION_BEARING_NOISE_DEG: Final[float] = 3.0     # near-field: a passage mouth a few
                                                   # cells away is seen well
SHAFT_BEACON_RANGE: Final[float] = 10.0            # kept from Phase 1
SHAFT_FIX_RANGE_NOISE: Final[float] = 0.35         # kept (Phase 1's BEACON_FIX_NOISE)
SHAFT_FIX_BEARING_NOISE_DEG: Final[float] = 2.0    # kept (inline in Phase 1's rig)
SHAFT_HEADING_REF_NOISE_DEG: Final[float] = 2.0    # NEW. The shaft is survey-placed, so
# the fix also carries the agent's heading read against the survey marks. Phase 1's
# fix gave position only (HEADING_FIX_GAIN = 0). Here heading error is the thing that
# picks the wrong passage, and it accrues over every cell walked; without a heading
# anchor a policy that goes home for a fix walks further in total than one that does
# not and so takes MORE wrong turns, and `uncertainty > theta` could never be worth
# obeying. Position sigma still collapses at the fix as before.

# ---- stops --------------------------------------------------------------------------------
LOST_ALLOWANCE_TICKS: Final[int] = 60              # 3 s of listening at the place belief
                                                   # calls the shaft before giving up
BUDGET_FACTOR: Final[int] = 2                      # spec: twice a full depth-first walk

# ---- the reference trees ---------------------------------------------------------------------
THETA_AWARE_THETA: Final[float] = 64.0             # cells of position sigma; see below
# The theta-aware tree goes home for a fix once sigma passes theta, then walks out
# again, so theta sets the length of one excursion: 64 is about 300 cells since the
# fix (EST_* above). Two edges bound it. Below, the excursion must clear the trunk to
# the deepest frontier -- a depth-7 deposit sits up to 250 cells out -- with a new
# passage to spare, or the agent re-walks the trunk once per passage and runs out of
# budget. Above, an excursion's return turns carry bias * (excursion length) of
# heading error, which passes the 25-degree half-gap and the tree fails the way the
# depth-first one does. Sweep at bias 0.055, successes over sixty seeds:
#   24 -> 51/60 (9 budget)    32 -> 57/60    40 -> 58/60    48 -> 60/60
#   56 -> 59/60               64 -> 60/60    80 -> 59/60   100 -> 60/60
#  140 -> 57/60 (3 lost)     180 -> 50/60   220 -> 44/60
# Every failure below 48 is budget; every failure above 100 is lost. The flat top
# runs from about 48 to about 100 and 64 is the middle of it, so neither edge is
# one tuning change away. A player's fitted theta will approach the lower edge,
# which is the forgiving one: budget failures, not lost ones.

# ---- the staged tutorial ----------------------------------------------------------------------
# Six runs: three that stage the block list in, then three demonstrations. Seeds sit
# above every band the headless sweeps were read off (0..59), so the twenty unseen
# evaluation seeds and the demonstration seeds do not overlap.
TUTORIAL_SEEDS: Final[tuple[int, int, int]] = (101, 102, 103)
DEMONSTRATION_SEEDS: Final[tuple[int, int, int]] = (104, 105, 106)
# The theta a demonstration reads `lost` with is `provisional` on that block in
# blocks.json, not here: a block is a data change plus its evaluator, and a value for it
# in this file was a third edit (crates/blindside-induct/FORMAT.md says why it lives on the
# list). It is set to THETA_AWARE_THETA's value, by hand, so that a player who mimics the
# reference tree is reading the same booleans it is; change one, change the other.

# ---- the window -------------------------------------------------------------------------------
ELLIPSE_SIGMAS: Final[float] = 2.0                 # the drawn ellipse is 2 sigma: the
                                                   # ordinary reading of "where it might be"
UNWALKED_STUB_CELLS: Final[float] = 7.0            # half the shortest passage, so a dashed
                                                   # mouth reads as a direction, not a passage
TRUTH_TRAIL_EVERY_TICKS: Final[int] = 10           # reveal only: half a second of true path

# ---- the seam ---------------------------------------------------------------------------------
# The induction is Rust and is not throwaway; the two sides talk through JSON files only.
# Overridable by the environment so a build somewhere else can point at its own binary.
INDUCT_BIN: Final[Path] = (Path(__file__).resolve().parent.parent / "crates"
                           / "blindside-induct" / "target" / "release"
                           / ("induct.exe" if os.name == "nt" else "induct"))
