"""Take the left-most passage here that still leads to unexplored ground."""
from __future__ import annotations

from .. import geometry as G
from ..belief.belief import Belief
from .motor_command import MotorCommand


def plan(belief: Belief) -> MotorCommand:
    """Turn to the recorded bearing of the left-most passage here that is not
    exhausted, and go -- which after a trip home for a fix is a passage already
    walked, taken to get back down to the frontier. If there is none, hold: the
    action has nothing to take. `Belief.unexplored_here` says what "exhausted"
    means and why it is not the stricter test."""
    candidates = belief.unexplored_here()
    if not candidates:
        return MotorCommand.hold()
    passage = candidates[0]
    belief.note_walk_branch(passage)
    return MotorCommand(turn=G.wrap(passage.bearing - belief.theta), go=True)
