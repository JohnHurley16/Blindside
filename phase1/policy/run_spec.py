"""Which blocks exist in a run, and with what parameter values.

A run -- a demonstration, a ghost, a match on a tree -- is played over a subset of
the block list: the predicates that can stop the bot and the actions it can be told
to do. This is that subset as plain data, and it is what a trace records under
`enabled_predicates`, `enabled_actions` and `params` (crates/blindside-induct/
FORMAT.md). Nothing here names a block; the ids come from the registry, a tree or a
`--enabled` list.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Mapping

from .block_registry import BlockRegistry
from .decision_tree import DecisionTree


@dataclass(slots=True, frozen=True)
class RunSpec:
    """`params` carries a value for every enabled parametric predicate: the tree's
    own where a tree sets it, the block list's provisional one otherwise."""
    enabled_predicates: tuple[str, ...]
    enabled_actions: tuple[str, ...]
    params: dict[str, dict[str, float]] = field(default_factory=dict)

    @classmethod
    def for_demonstration(cls, registry: BlockRegistry,
                          enabled: Iterable[str] | None = None) -> RunSpec:
        """A player's run: every block, or the `--enabled` subset, at the provisional
        thresholds off the block list."""
        predicates, actions = _restrict(registry, enabled)
        return cls(tuple(predicates), tuple(actions), registry.provisional_params(predicates))

    @classmethod
    def for_tree(cls, tree: DecisionTree, registry: BlockRegistry,
                 enabled: Iterable[str] | None = None) -> RunSpec:
        """A tree's run: the tree's own thresholds for the predicates it reads, the
        provisional ones for any other enabled predicate. With no `enabled` list only
        the tree's own predicates exist -- the corridor evaluator's rule, so a match
        on a tree stops only where the tree can see -- and every action does."""
        if enabled is None:
            predicates = [pid for pid in registry.predicate_ids() if pid in tree.predicates_used()]
            actions = registry.action_ids()
        else:
            predicates, actions = _restrict(registry, enabled)
        outside = sorted(tree.predicates_used() - set(predicates)) + sorted(
            tree.actions_used() - set(actions))
        if outside:
            raise ValueError(f"tree uses blocks that do not exist in this run: {outside}")
        params = registry.provisional_params(predicates)
        for pid in predicates:
            if pid in tree.params:
                params[pid] = dict(tree.params[pid])
        return cls(tuple(predicates), tuple(actions), params)

    @classmethod
    def from_trace(cls, enabled_predicates: Iterable[str], enabled_actions: Iterable[str],
                   params: Mapping[str, Mapping[str, float]]) -> RunSpec:
        """The run a recorded trace was played over, so a replay stops where it did."""
        return cls(tuple(enabled_predicates), tuple(enabled_actions),
                   {pid: {k: float(v) for k, v in vals.items()} for pid, vals in params.items()})

    def check(self, registry: BlockRegistry) -> None:
        for pid in self.enabled_predicates:
            param = registry.predicate(pid).param
            if param is not None and param not in self.params.get(pid, {}):
                raise ValueError(f"{pid} is enabled and needs a value of {param}")


def _restrict(registry: BlockRegistry, enabled: Iterable[str] | None) -> tuple[list[str], list[str]]:
    """Block-list order, so a trace's columns agree with every other trace's."""
    if enabled is None:
        return registry.predicate_ids(), registry.action_ids()
    wanted = set(enabled)
    unknown = wanted - set(registry.predicate_ids()) - set(registry.action_ids())
    if unknown:
        raise ValueError(f"--enabled names blocks not in the block list: {sorted(unknown)}")
    return ([p for p in registry.predicate_ids() if p in wanted],
            [a for a in registry.action_ids() if a in wanted])
