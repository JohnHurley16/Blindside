"""What an action hands off to: a motor program that runs until the next decision."""
from __future__ import annotations

from ...belief.belief import Belief
from ...motor_command import MotorCommand
from ..decision_node import DecisionNode
from ..loadout import Loadout
from ..waypoint import Waypoint
from .body import Body


class Program:
    """One action, carried out.

    `step(t)` returns the command for this tick, or `None` when the program found it
    had nothing left to do *before* acting -- the tick then belongs to whatever the
    tree picks next, so a freeze that lifts hands the same tick to the drive it
    interrupted, as the old policy did. A program may also return a command with
    `ended` already set: that was its last tick (the load dwell's final tick still
    asks to load, as it always did), and the tree decides at the top of the next.

    `noop` is true from construction when the action has nothing to do at all --
    fetch with no deposit left, freeze in silence. CAVE-BLOCKS.md 2.2 rule 2: a no-op
    is not a demonstration, and a tree that picks one stalls visibly rather than
    doing something else.

    A program the tree interrupts is suspended, not discarded, and `resume` is called
    if the tree picks it again straight after (rule 1): fetch interrupted by a freeze
    keeps its route and its retry count. The pause is not a stall and not a jam.
    """

    def __init__(self, body: Body, t: float) -> None:
        self.body: Body = body
        self.b: Belief = body.belief
        self.loadout: Loadout = body.loadout
        self.shaft_beacon_id: str = body.shaft_beacon_id
        self.started_at: float = t
        self.ended: bool = False
        self.outcome: str = ""
        self.noop: bool = False

    def step(self, t: float) -> MotorCommand | None:
        raise NotImplementedError

    def ending(self, t: float) -> str | None:
        """The outcome this program would end with *before acting* this tick, or None.

        A pure look-ahead: `step(t)` must begin by asking the same question and, on a
        yes, do its side effects and return None. The policy asks it at the top of the
        tick so that a stop caused by an ending is found before the world moves, and a
        chooser who is a person can be asked with the match clock stopped; a program
        that answers None here and still returns None from `step` costs a demonstration
        one idle tick, and the policy says so in the log.
        """
        return None

    def resume(self, t: float) -> None:
        pass

    def nodes(self, t: float) -> list[DecisionNode]:
        """The action as the decision graph draws it, with live detail."""
        raise NotImplementedError

    def target(self) -> Waypoint | None:
        """The waypoint being made for, if any, for the display's intent line."""
        return None

    def _end(self, t: float, outcome: str) -> None:
        self.ended = True
        self.outcome = outcome

    def idle(self) -> MotorCommand:
        """Stand still and say nothing, this tick."""
        return MotorCommand(heading=self.b.theta)
