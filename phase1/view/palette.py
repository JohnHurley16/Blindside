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
