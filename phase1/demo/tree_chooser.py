"""A tree as the chooser at a demonstration's stops, for scripted runs and tests."""
from __future__ import annotations

from ..policy.decision_tree import DecisionTree
from ..policy.run_spec import RunSpec
from ..policy.stop_view import StopView


class TreeChooser:
    """Walks the tree on the stop's Belief with the tree's own parameters -- exactly
    what the policy does when it carries the tree itself, so a demonstration this
    drives is the same match, tick for tick, as `--tree` with the same run spec.

    Refuses a tree that names a block outside the run, so a scripted demonstration
    cannot quietly use a block the player has not met.
    """

    def __init__(self, tree: DecisionTree, spec: RunSpec) -> None:
        self.tree: DecisionTree = tree
        outside = sorted(tree.predicates_used() - set(spec.enabled_predicates)) + sorted(
            tree.actions_used() - set(spec.enabled_actions))
        if outside:
            raise ValueError(f"tree uses blocks that do not exist in this run: {outside}")

    def __call__(self, stop: StopView) -> str:
        return self.tree.decide(stop.belief, self.tree.params)
