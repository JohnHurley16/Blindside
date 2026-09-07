"""A policy: a decision tree plus the parameters it was written with."""
from __future__ import annotations

from typing import Iterable

from ..belief.belief import Belief
from .decision_tree import DecisionTree


class Policy:
    """What an agent runs. `choose(belief)` is the whole interface.

    Built for a run in which only some blocks exist: a tree that names a block
    outside that set is refused, so a scripted demonstration cannot quietly use
    a block the player has not met.
    """

    def __init__(self, tree: DecisionTree, enabled_predicates: Iterable[str],
                 enabled_actions: Iterable[str]) -> None:
        self.tree: DecisionTree = tree
        enabled_p = set(enabled_predicates)
        enabled_a = set(enabled_actions)
        outside = sorted(tree.predicates_used() - enabled_p) + sorted(tree.actions_used() - enabled_a)
        if outside:
            raise ValueError(f"tree uses blocks that do not exist in this run: {outside}")
        for pid in tree.predicates_used():
            param = tree.registry.predicate(pid).param
            if param is not None and param not in tree.params.get(pid, {}):
                raise ValueError(f"tree needs a value of {param} for {pid}")

    @property
    def params(self) -> dict[str, dict[str, float]]:
        return self.tree.params

    def choose(self, belief: Belief) -> str:
        return self.tree.decide(belief, self.tree.params)
