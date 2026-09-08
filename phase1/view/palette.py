"""Twenty-four colour values, one meaning each, and four type sizes.

SPECTATOR-DISPLAY.md 6.1-6.3. This file used to hold about fifty values with six
meanings on amber and seven on green; the audit is in the commit message. What is left
is the list below and nothing else, and the rule that keeps it that way is the one the
old docstring already claimed and did not enforce: **a colour means one thing each.**

Two orthogonal channels do the heavy lifting, both learned in one beat and never
explained:

  * **Warm and filled is real. Cool and sparse is believed.** A viewer who learns
    nothing else always knows which half she is looking at, and the 8:00 reveal becomes
    warm-over-cool rather than red-over-grey.
  * **Solid fill is the thing. Hollow outline is a belief about the thing.** This is
    what makes the ghost machine legible sitting next to the real one, and dashed is
    the relationship between them.

**Red means lethal and nothing else.** That was established by the Assayer work and it
is the constraint most likely to be broken by accident, because red is the obvious
colour for every alarming thing on the screen. The tether escalates by weight into LIE
and never into KILL; the true trails, the reveal's wall outline and the ancient's body
are all warm and none of them is red.

**The hierarchy, and the rule that enforces it.** Three levels of visual weight:

  * PRIMARY -- readable in under a second from across the room: the two display
    numbers, the tether, the machinery while it is counting.
  * SECONDARY -- read when something happens: both machines, the fix beat, sound
    wedges, major event pips.
  * AMBIENT -- never read, only felt: the cave mesh, the floor, the point cloud, the
    trails, chamber names, the minimap's furniture.

> An ambient value's relative luminance never exceeds `AMBIENT_MAX_LUMINANCE` of the
> brightest primary's.

That is asserted at the foot of this file, so an ambient value that is quietly brightened
to make it visible fails at import rather than six weeks later on a screen where the cave
competes with the machine standing on it. The other two clauses of 6.3 -- an ambient
element never animates for longer than a second, and never carries text above Body --
are not assertable here and live with the marks themselves.
"""
from __future__ import annotations

import numpy as np

from .. import tuning as T
from ..sound_character import SoundCharacter
from .event_kind import EventKind

Rgb = tuple[float, float, float]
Rgba = tuple[float, float, float, float]

# ---- chrome: three values, and none of them is ever a mark ---------------------------------
VOID: Rgb = (0.024, 0.031, 0.043)          # #06080B  outside everything, and anything never
                                           # sensed. `unmapped` folded into this: absence and
                                           # absence are the same colour, which is the point.
PANEL: Rgb = (0.043, 0.055, 0.075)         # #0B0E13  rail and timeline ground
RULE: Rgb = (0.102, 0.129, 0.169)          # #1A212B  1 px separators, bar tracks, dead track

# ---- truth: warm, filled, opaque -------------------------------------------------------------
ROCK: Rgb = (0.082, 0.067, 0.051)          # #15110D  solid rock at the base of a wall
ROCK_LIT: Rgb = (0.227, 0.180, 0.133)      # #3A2E22  the top of a wall and its lit faces
FLOOR: Rgb = (0.165, 0.133, 0.098)         # #2A2219  dry passage, tinted darker with depth
WATER: Rgb = (0.086, 0.125, 0.180)         # #16202E  flooded -- cool on purpose; water is not warm
BONE: Rgb = (0.949, 0.902, 0.824)          # #F2E6D2  the player's machine, and its true path
EMBER: Rgb = (1.000, 0.478, 0.184)         # #FF7A2F  the rival, and its true path
WARM_DIM: Rgb = (0.478, 0.400, 0.314)      # #7A6650  true comets, chamber names, true beacons,
                                           # and the wall outline the reveal draws over the map

# ---- belief: cool, sparse, translucent ---------------------------------------------------------
SENSED: Rgb = (0.388, 0.839, 0.969)        # #63D6F7  a point the sensor returned. One value, not a
                                           # two-colour lerp: confidence is alpha and size, and
                                           # four channels doing one job is most of why the map
                                           # read as noise.
WALKED: Rgb = (0.180, 0.282, 0.329)        # #2E4854  ground it only passed through
GHOST: Rgb = (0.624, 0.910, 1.000)         # #9FE8FF  believed pose, its ellipse, its intent, the
                                           # beacons it recorded, every wedge it heard -- every
                                           # hollow mark, which is to say every belief
COOL_DIM: Rgb = (0.227, 0.322, 0.376)      # #3A5260  believed trail, the chain, residue spokes

# ---- accents: one meaning each, used nowhere else, ever -------------------------------------------
HAZARD: Rgb = (1.000, 0.310, 0.847)        # #FF4FD8  the machinery's field, in every picture
LIE: Rgb = (1.000, 0.824, 0.247)           # #FFD23F  a fix that moved the world; the spoof; a hot
                                           # tether; the extraction window closing on it
CARGO: Rgb = (0.310, 0.878, 0.541)         # #4FE08A  the objective: deposits, the hold, the shaft
KILL: Rgb = (1.000, 0.231, 0.188)          # #FF3B30  a machine dying, and error past the alarm.
                                           # LETHAL and nothing else. Do not add a second red.
HURT: Rgb = (0.878, 0.435, 0.376)          # #E06F60  a machine that is hurt and still alive.
                                           # Not a second red: damage and trouble both wore
                                           # KILL, so red meant dying AND hurt AND stuck AND
                                           # lost, and the rail stacked a red error figure
                                           # over a red "limping, 50%" that meant something
                                           # else. Red keeps death; this is being hurt.

# ---- the Assayer's body: one hue, three weights, all multiples of ROCK_LIT -------------------------
# THE-MACHINERY.md 2.1. The machine is dead iron bolted into stone, so it is drawn in the rock's
# own colour and never in HAZARD -- only the FIELD is magenta. That is what stops the object being
# a magenta blob and lets the dormant state read as finished rather than menacing. 2.1's table is
# written as multiples of ROCK_LIT and it is written that way here too, so the three are visibly
# one material at three weights rather than three colours: worked iron is brighter than the stone
# it is bolted to, and the hammer -- the one part that has to be found while it is moving up a
# mast -- is the brightest thing on the machine and nothing else on it is.
def _weight(rgb: Rgb, k: float) -> Rgb:
    return (min(rgb[0] * k, 1.0), min(rgb[1] * k, 1.0), min(rgb[2] * k, 1.0))


ASSAYER_MAST: Rgb = _weight(ROCK_LIT, 2.3)    # #85694E  the mast, one step back from the arm
ASSAYER_IRON: Rgb = _weight(ROCK_LIT, 2.6)    # #96775B  footing, legs, boom, ribs
ASSAYER_HAMMER: Rgb = _weight(ROCK_LIT, 3.2)  # #B9936C  the hammer

# ---- type ---------------------------------------------------------------------------------------
PRIMARY: Rgb = (0.949, 0.961, 0.976)       # #F2F5F9  a number or a word that must be read
SECONDARY: Rgb = (0.576, 0.635, 0.694)     # #93A2B1  the label above one. Never below 9 pt, and
                                           # never TERTIARY at 9 pt: the tester watched an h264
                                           # encode and small dark grey does not survive one.
TERTIARY: Rgb = (0.337, 0.384, 0.435)      # #56626F  furniture that is present, not read

# ---- how a sound is drawn ---------------------------------------------------------------------
# A wedge in the belief scene is a belief about a bearing, so it is GHOST like every other hollow
# mark; character is carried by the wedge's length and by the timeline pip, not by a fourth and
# fifth hue. The two exceptions are the two accents that already mean exactly this: a crash is a
# machine dying and a signature is the machinery.
CONTACT: dict[SoundCharacter, Rgb] = {
    SoundCharacter.TONE: GHOST,
    SoundCharacter.PING: GHOST,
    SoundCharacter.CRASH: KILL,
}

# ---- what a timeline pip means ------------------------------------------------------------------
# Eight kinds over seven values, and every one of them is a value that already exists with the
# same meaning it has everywhere else on screen: a correction is a belief event, a disagreeing one
# is the world moving underneath it, the machinery is magenta wherever it appears.
EVENT: dict[EventKind, Rgb] = {
    EventKind.FIX: SENSED,
    EventKind.DISAGREE: LIE,
    EventKind.CONTACT: GHOST,
    EventKind.HAZARD: HAZARD,
    EventKind.CARGO: CARGO,
    EventKind.COMMAND: PRIMARY,
    EventKind.PHASE: SECONDARY,
    # Stuck, lost, or nothing where it expected -- none of those is a machine dying, which is
    # what red means. Trouble takes the amber of a lie: something is wrong with what it
    # believes, not with what it is.
    EventKind.TROUBLE: LIE,
}

# ---- the hierarchy, asserted -----------------------------------------------------------------
PRIMARY_MARKS: tuple[Rgb, ...] = (BONE, EMBER, GHOST, HAZARD, LIE, CARGO, KILL, HURT,
                                  PRIMARY)
AMBIENT_MARKS: tuple[Rgb, ...] = (VOID, PANEL, RULE, ROCK, ROCK_LIT, FLOOR, WATER, WARM_DIM,
                                  WALKED, COOL_DIM, TERTIARY)


def luminance(rgb: Rgb) -> float:
    """Relative luminance, sRGB linearised first.

    Doing this on the gamma-encoded values instead -- which is the easy mistake -- puts
    WARM_DIM at 0.41 and the assertion below fails on a palette that is in fact correctly
    ordered, because gamma encoding compresses the dark end and a mid-brown reads as half
    the brightness of white when it carries a sixth of the light.
    """
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def _check_hierarchy(ceiling: float) -> None:
    brightest = max(luminance(rgb) for rgb in PRIMARY_MARKS)
    limit = ceiling * brightest
    for rgb in AMBIENT_MARKS:
        assert luminance(rgb) <= limit, (
            f"ambient value {rgb} at luminance {luminance(rgb):.3f} is over "
            f"{ceiling:.0%} of the brightest primary ({limit:.3f}): "
            "SPECTATOR-DISPLAY 6.3. Make the mark bigger, not brighter.")


def lerp(a: Rgb, b: Rgb, amount: float) -> Rgb:
    """Straight-line blend, clamped. Used for exactly one thing: a machine's own colour
    walking toward KILL as it takes shock, which is the only damage display of the four
    proposed that survives CAMERA_WIDE_CELLS, where the glyph is nine pixels and no text
    on screen is legible."""
    k = min(max(amount, 0.0), 1.0)
    return (a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k, a[2] + (b[2] - a[2]) * k)


def ramp(cells: float) -> Rgb:
    """How wrong it is, as a colour. TETHER_MIN / HOT / ALARM, so the rope in the picture
    and the number in the rail never disagree about how bad it has got.

    It escalates into KILL because past thirty cells the machine is, in the only sense
    this game means it, lost -- and KILL is the one value on screen that outranks LIE.
    """
    near, hot, alarm = T.READOUT_RAMP_CELLS
    if cells < near:
        return TERTIARY
    if cells < hot:
        return PRIMARY
    if cells < alarm:
        return LIE
    return KILL


# ---- not on screen ---------------------------------------------------------------------------
# `decision_graph.py`, `node_box.py` and `map_key.py` are unbound: nothing imports them, so
# nothing below reaches a pixel and nothing below is counted in the twenty-four. The first two
# are kept because they hold the two hardest-won vispy workarounds in this repo and are the
# specification for BLD-152; the key is kept because 3.5 may yet want five rows of it in the foot
# of the rail. Deleting those three modules deletes this block with them.
LEGEND: Rgb = (0.44, 0.50, 0.58)
NODE_FILL: Rgba = (0.11, 0.13, 0.16, 0.95)
NODE_EDGE: Rgba = (0.24, 0.29, 0.36, 0.95)
NODE_TEST_HOT: Rgba = (0.17, 0.15, 0.10, 0.95)
NODE_EDGE_HOT: Rgba = (0.72, 0.58, 0.24, 0.95)
NODE_ACTION_FILL: Rgba = (0.09, 0.19, 0.15, 0.95)
NODE_ACTION_EDGE: Rgba = (0.30, 0.72, 0.50, 0.95)
NODE_SUB_FILL: Rgba = (0.09, 0.10, 0.13, 0.85)
NODE_SUB_EDGE: Rgba = (0.19, 0.23, 0.28, 0.80)
BAR_FILL: Rgba = (0.36, 0.68, 0.95, 0.95)
BAR_HOT: Rgba = (1.00, 0.78, 0.30, 0.98)
EDGE_LIVE: Rgba = (0.42, 1.00, 0.68, 0.85)
EDGE_IDLE: Rgba = (0.28, 0.33, 0.40, 0.80)
TREE_LIVE: Rgb = (0.42, 1.00, 0.68)
BAR_TRACK: Rgba = (*RULE, 0.95)
TITLE: Rgb = PRIMARY
HUD: Rgb = SECONDARY
DIM: Rgb = TERTIARY
BANNER: Rgb = LIE
AGENT: Rgba = (*GHOST, 1.00)
ELLIPSE: Rgba = (*GHOST, 0.55)
BEACON: Rgba = (*GHOST, 0.95)
BELIEVED_HAZARD: Rgba = (*HAZARD, 0.34)
BELIEVED_RIVAL: Rgba = (*EMBER, 0.34)

_check_hierarchy(T.AMBIENT_MAX_LUMINANCE)

# Kept out of the twenty-four deliberately: this is the one array in the file, and it is the
# point cloud's per-point colour, which is SENSED and WALKED and nothing else.
POINT_SENSED: np.ndarray = np.array(SENSED)
POINT_WALKED: np.ndarray = np.array(WALKED)
