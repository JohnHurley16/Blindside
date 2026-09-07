"""Walk the believed route back to the shaft, one passage per stop."""
from __future__ import annotations

from .. import geometry as G
from ..belief.belief import Belief
from .motor_command import MotorCommand


def plan(belief: Belief) -> MotorCommand:
    """Turn to the recorded bearing of the way this junction was entered by,
    reversed, and go. At the place belief calls the shaft there is no way back:
    hold, and the session decides whether that is home or lost -- if no fix
    arrives within tuning.LOST_ALLOWANCE_TICKS, the run ends lost."""
    node = belief.current_node()
    if node.parent is None or node.back_bearing is None:
        return MotorCommand.hold()
    belief.note_walk_back()
    return MotorCommand(turn=G.wrap(node.back_bearing - belief.theta), go=True)
