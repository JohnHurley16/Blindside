"""What the agent thinks.

**This package must never import `phase2.truth`.** It is built only from sensor
returns, and it is the only world representation a policy, a motor or a view may
read.
"""
from __future__ import annotations

from .belief import Belief
from .junction_node import JunctionNode
from .seen_passage import SeenPassage

__all__ = ["Belief", "JunctionNode", "SeenPassage"]
