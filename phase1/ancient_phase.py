"""Where the Assayer is in its seventy-five seconds.

THE-MACHINERY.md section 3's six rows, named. Shared vocabulary between truth and
the spectator screen, so it lives beside `sound_character.py` rather than inside
`truth/`: the renderer has to be able to name a phase without being able to name a
World. It reaches a StageFrame as the member's plain string value.
"""
from __future__ import annotations

from enum import StrEnum


class AncientPhase(StrEnum):
    LISTENING = "listening"  # 54 s of nothing: a still machine in a ruined patch of floor
    SLEW = "slew"            # 3 s: the boom swings 36 degrees and stops, pointing somewhere
    LOCKED = "locked"        # 5 s of stillness after a movement: it has decided something
    WIND = "wind"            # 9 s: the hammer ratchets up the mast in nine clicks
    FIRING = "firing"        # 3 frames: the hammer falls the whole mast
    LETHAL = "lethal"        # 4 s: the shock crossing the floor
