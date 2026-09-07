"""Colour and type. Copied from Phase 1 and cut down to what Phase 2 draws.

The rule that keeps this readable is that a colour means one thing each. Green is
the agent and its own certainty. Cyan is ground it believes it has walked. Dimmer
blue-grey is ground it has only seen the mouth of. Yellow appears only where the
window is telling you that two things disagree. Red appears only after a run is
over, and always means truth.
"""
from __future__ import annotations

Rgb = tuple[float, float, float]
Rgba = tuple[float, float, float, float]

# ---- surfaces -----------------------------------------------------------------------
BACKGROUND: Rgb = (0.035, 0.042, 0.055)
PANEL: Rgba = (0.075, 0.089, 0.110, 0.94)
PANEL_EDGE: Rgba = (0.20, 0.24, 0.30, 0.85)

# ---- the believed map ---------------------------------------------------------------
WALKED: Rgba = (0.42, 0.78, 0.92, 0.90)          # a passage it believes it has walked
UNWALKED: Rgba = (0.34, 0.42, 0.52, 0.80)        # a mouth it has only seen
NODE: Rgba = (0.62, 0.93, 1.00, 0.95)
NODE_HERE: Rgba = (0.42, 1.00, 0.68, 1.00)
SHAFT: Rgba = (0.40, 1.00, 0.85, 0.95)
DEPOSIT: Rgba = (1.00, 0.86, 0.35, 0.90)
AGENT: Rgba = (0.35, 1.00, 0.62, 1.00)
ELLIPSE: Rgba = (0.35, 1.00, 0.62, 0.45)
TRAIL: Rgba = (0.42, 0.52, 0.62, 0.30)
ROUTE: Rgba = (0.40, 1.00, 0.85, 0.22)           # the believed way home, faint

# ---- truth, only after a run is over ---------------------------------------------------
TRUTH_PASSAGE: Rgba = (0.92, 0.28, 0.24, 0.35)
TRUTH_TRAIL: Rgba = (1.00, 0.42, 0.32, 0.85)
TRUTH_DEPOSIT: Rgba = (1.00, 0.90, 0.32, 0.90)
TRUTH_AGENT: Rgba = (1.00, 0.32, 0.24, 0.95)

# ---- type -------------------------------------------------------------------------------
TITLE: Rgb = (0.88, 0.93, 0.98)
HUD: Rgb = (0.72, 0.79, 0.87)
DIM: Rgb = (0.46, 0.53, 0.62)
BANNER: Rgb = (1.00, 0.86, 0.42)
YES: Rgb = (0.42, 1.00, 0.68)
NO: Rgb = (0.58, 0.64, 0.72)
KEY: Rgb = (0.40, 1.00, 0.85)

# ---- the tree panel -----------------------------------------------------------------------
TREE_LIVE: Rgb = (0.42, 1.00, 0.68)              # a node on the path this stop took
TREE_IDLE: Rgb = (0.48, 0.55, 0.64)
TREE_FLAG: Rgb = (1.00, 0.92, 0.32)              # the stop where the ghost differed
