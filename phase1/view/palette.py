"""Colour and type. Restrained on purpose: one accent per meaning, nothing decorative.

The rule that keeps this readable is that a colour means one thing each. Green is
always the agent and its own certainty. Cyan is ground it has actually sensed. Amber
is something heard. Magenta is machinery. Yellow appears only when a fix moves the
world under it, so yellow always means "what you were looking at just changed".
"""
from __future__ import annotations

import numpy as np

from ..sound_character import SoundCharacter
from .event_kind import EventKind

Rgb = tuple[float, float, float]
Rgba = tuple[float, float, float, float]

# ---- surfaces -----------------------------------------------------------------------
BACKGROUND: Rgb = (0.035, 0.042, 0.055)
PANEL: Rgba = (0.075, 0.089, 0.110, 0.94)
PANEL_EDGE: Rgba = (0.20, 0.24, 0.30, 0.85)

# ---- the map ------------------------------------------------------------------------
# Confidence drives colour, size and alpha together: a marginal return must not look
# identical to a confident one.
POINT_LOW: np.ndarray = np.array([0.20, 0.34, 0.46])
POINT_HIGH: np.ndarray = np.array([0.62, 0.93, 1.00])
# Ground merely walked through, not pinged. There are roughly four of these for every
# sonar return, so drawing them alike is most of why a map reads as noise.
POINT_WALKED: np.ndarray = np.array([0.26, 0.30, 0.38])

AGENT: Rgba = (0.35, 1.00, 0.62, 1.00)
ELLIPSE: Rgba = (0.35, 1.00, 0.62, 0.55)
TRAIL: Rgba = (0.42, 0.52, 0.62, 0.30)
BEACON: Rgba = (0.45, 0.72, 1.00, 0.95)
BEACON_CHAIN: Rgba = (0.35, 0.55, 0.85, 0.30)
SHAFT: Rgba = (0.40, 1.00, 0.85, 0.95)
DEPOSIT: Rgba = (1.00, 0.86, 0.35, 0.85)
INTENT: Rgba = (0.35, 1.00, 0.62, 0.40)
FIX_FLASH: Rgb = (1.00, 0.92, 0.32)

# Where the agent *believes* something is, worked out by crossing bearings over time.
# Frequently wrong, and wrong in a way the reveal makes obvious.
BELIEVED_HAZARD: Rgba = (0.95, 0.32, 0.85, 0.34)
BELIEVED_RIVAL: Rgba = (1.00, 0.72, 0.28, 0.34)

CONTACT: dict[SoundCharacter, Rgb] = {
    SoundCharacter.TONE: (1.00, 0.72, 0.28),
    SoundCharacter.PING: (0.80, 0.92, 1.00),
    SoundCharacter.CRASH: (1.00, 0.34, 0.30),
}
SIGNATURE: Rgb = (0.95, 0.32, 0.85)

# ---- truth, only after the end ---------------------------------------------------------
TRUTH_WALL: Rgba = (0.92, 0.28, 0.24, 0.30)
TRUTH_FLOOD: Rgba = (0.22, 0.42, 0.92, 0.22)
TRUTH_TRAIL_PLAYER: Rgba = (1.00, 0.32, 0.24, 0.90)
TRUTH_TRAIL_RIVAL: Rgba = (1.00, 0.62, 0.22, 0.55)
TRUTH_BEACON: Rgba = (1.00, 0.52, 0.32, 0.90)
TRUTH_DEPOSIT: Rgba = (1.00, 0.90, 0.32, 0.90)

# ---- type --------------------------------------------------------------------------------
TITLE: Rgb = (0.88, 0.93, 0.98)
HUD: Rgb = (0.72, 0.79, 0.87)
DIM: Rgb = (0.46, 0.53, 0.62)
BANNER: Rgb = (1.00, 0.86, 0.42)
LEGEND: Rgb = (0.44, 0.50, 0.58)

NODE_FILL: Rgba = (0.11, 0.13, 0.16, 0.95)
NODE_EDGE: Rgba = (0.24, 0.29, 0.36, 0.95)
NODE_TEST_HOT: Rgba = (0.17, 0.15, 0.10, 0.95)
NODE_EDGE_HOT: Rgba = (0.72, 0.58, 0.24, 0.95)
NODE_ACTION_FILL: Rgba = (0.09, 0.19, 0.15, 0.95)
NODE_ACTION_EDGE: Rgba = (0.30, 0.72, 0.50, 0.95)
NODE_SUB_FILL: Rgba = (0.09, 0.10, 0.13, 0.85)
NODE_SUB_EDGE: Rgba = (0.19, 0.23, 0.28, 0.80)
BAR_TRACK: Rgba = (0.19, 0.23, 0.29, 0.95)
BAR_FILL: Rgba = (0.36, 0.68, 0.95, 0.95)
BAR_HOT: Rgba = (1.00, 0.78, 0.30, 0.98)
EDGE_LIVE: Rgba = (0.42, 1.00, 0.68, 0.85)
EDGE_IDLE: Rgba = (0.28, 0.33, 0.40, 0.80)

TREE_ROOT: Rgb = (0.88, 0.93, 0.98)
TREE_LIVE: Rgb = (0.42, 1.00, 0.68)
TREE_IDLE: Rgba = (0.40, 0.46, 0.55, 0.85)
TREE_DOT: Rgba = (0.42, 1.00, 0.68, 0.95)

EVENT: dict[EventKind, Rgb] = {
    EventKind.FIX: (0.55, 0.72, 0.90),
    EventKind.DISAGREE: (1.00, 0.92, 0.32),
    EventKind.CONTACT: (0.80, 0.92, 1.00),
    EventKind.HAZARD: (0.95, 0.32, 0.85),
    EventKind.CARGO: (0.45, 1.00, 0.70),
    EventKind.COMMAND: (0.40, 1.00, 0.85),
    EventKind.PHASE: (0.95, 0.62, 0.25),
    EventKind.TROUBLE: (1.00, 0.42, 0.32),
}

# ---- the truth scene ----------------------------------------------------------------------
# SPECTATOR-DISPLAY.md section 6.1, added rather than substituted: the palette pass that
# collapses the fifty values above into twenty is slice 6, and doing it in the same commit
# as the truth scene would make a re-run unattributable.
#
# Two orthogonal channels do the heavy lifting, both learned in one beat and never
# explained: warm and filled is real, cool and sparse is believed; solid fill is the
# thing, hollow outline is a belief about the thing.
ROCK: Rgb = (0.082, 0.067, 0.051)          # #15110D  solid rock at the base of a wall
ROCK_LIT: Rgb = (0.227, 0.180, 0.133)      # #3A2E22  the top of a wall and its lit faces
FLOOR: Rgb = (0.165, 0.133, 0.098)         # #2A2219  dry passage, tinted darker with depth
WATER: Rgb = (0.086, 0.125, 0.180)         # #16202E  flooded -- cool on purpose
BONE: Rgb = (0.949, 0.902, 0.824)          # #F2E6D2  the player's machine, true
EMBER: Rgb = (1.000, 0.478, 0.184)         # #FF7A2F  the rival, true
WARM_DIM: Rgb = (0.478, 0.400, 0.314)      # #7A6650  true comets, chamber labels
GHOST: Rgb = (0.624, 0.910, 1.000)         # #9FE8FF  believed pose, all hollow marks
COOL_DIM: Rgb = (0.227, 0.322, 0.376)      # #3A5260  believed trail, residue spokes

# one meaning each, used nowhere else, ever
HAZARD: Rgb = (1.000, 0.310, 0.847)        # #FF4FD8  the machinery
LIE: Rgb = (1.000, 0.824, 0.247)           # #FFD23F  a fix that moved the world; a hot tether
CARGO: Rgb = (0.310, 0.878, 0.541)         # #4FE08A  the objective: deposits, hold, shaft
KILL: Rgb = (1.000, 0.231, 0.188)          # #FF3B30  a machine dying; error past the alarm
VOID: Rgb = (0.024, 0.031, 0.043)          # #06080B  outside everything

# ---- the Assayer ---------------------------------------------------------------------------
# THE-MACHINERY.md section 2.1. The machine is dead iron bolted into stone and it is part
# of the world, so it is drawn in the rock's own colours and never in HAZARD -- only the
# FIELD is magenta. That is what stops the object being a magenta blob, and it is why the
# dormant state can read as finished rather than as menacing: a quiet state that already
# looks like a warning leaves the warning nowhere to go.
# Section 2.1's table is written as multiples of ROCK_LIT, and the multiples there are
# relative to each other rather than to the wall. Measured against a lit lobe: at 1.0x
# the whole machine disappeared into its own floor field, because the cave's world light
# darkens three faces in four and the lobe under it is brighter than any of them. Lifted
# until the boom reads over the lobe at CLOSE, which is 2.6x -- so the darkest face of the
# machine, at the cave light's 0.46, still sits above the brightest wall in the cave. It is still the rock's
# colour and it is still not HAZARD, which is the part of 2.1 that is load-bearing:
# worked iron is brighter than the stone it is bolted to, and only the FIELD is magenta.
ASSAYER_IRON: Rgb = (0.590, 0.468, 0.346)  # #96775B  footing, legs, boom, ribs
ASSAYER_MAST: Rgb = (0.522, 0.414, 0.306)  # #85694E  the mast, one step back from the arm
ASSAYER_HAMMER: Rgb = (0.726, 0.576, 0.426)  # #B9936C  the hammer
# The hammer is the one part that has to be found while it is moving up a mast, so it is
# the brightest thing on the machine and nothing else on it is.


def lerp(a: Rgb, b: Rgb, amount: float) -> Rgb:
    """Straight-line blend, clamped. Used for exactly one thing: a machine's own colour
    walking toward KILL as it takes shock, which is the only damage display of the four
    proposed that survives CAMERA_WIDE_CELLS, where the glyph is nine pixels and no text
    on screen is legible."""
    k = min(max(amount, 0.0), 1.0)
    return (a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k, a[2] + (b[2] - a[2]) * k)
