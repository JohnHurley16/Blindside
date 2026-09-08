"""Behaviour over Belief.

**This package must never import `phase1.truth`.** A policy reads `Belief` and
nothing else -- that is the one invariant the whole project rests on.

The policy is a decision tree over the block list (`blocks.json`, loaded by
`BlockRegistry`, the one place ids appear) evaluated at decision points; between
them the motor programs under `motor/` drive.
"""
from __future__ import annotations

from .action import Action
from .block_registry import BlockRegistry
from .decision_tree import DecisionTree
from .loadout import Loadout
from .policy import Policy
from .predicate import Predicate
from .waypoint import Waypoint

__all__ = ["Action", "BlockRegistry", "DecisionTree", "Loadout", "Policy", "Predicate", "Waypoint"]
