"""One node of the policy, with what it currently evaluates to."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class DecisionNode:
    """A test or an action, and how close it is to firing.

    `fill` is the whole point. A label saying "am I lost?" tells you nothing you did
    not already know; a bar creeping toward its threshold tells you what the machine
    is about to decide, several seconds before it decides it. That is the difference
    between reading the policy and watching it think.
    """
    node_id: str
    label: str
    kind: str = "test"          # test | action | sub
    answer: str = ""            # yes / no / blank
    detail: str = ""            # "8 of 16 cells"
    fill: float = -1.0          # 0..1 for a bar, negative for no bar
    active: bool = False        # this node was reached
    fired: bool = False         # this is the branch that was taken
    target: str = ""            # raw place name, for the display to put into words
