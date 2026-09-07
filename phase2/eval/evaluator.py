"""Run a tree.json on N seeds headless and print a table and the rate.

Success is the spec's sentence, implemented in `Session`: a run succeeds when the
agent is within the shaft beacon's range carrying cargo before the tick budget
ends; the budget is twice the ticks a full depth-first walk of that seed's
corridor needs.

**This module imports `phase2.truth`** -- only to construct each seed's World and
to read it afterwards for the reveal columns (deposit depth, misturns). Nothing
it reads from World reaches the tree.
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

from ..match.session import Session
from ..policy.block_registry import BlockRegistry
from ..policy.decision_tree import DecisionTree
from ..policy.policy import Policy
from ..truth.world import World
from .run_outcome import RunOutcome


class Evaluator:
    """Twenty unseen seeds, or however many are asked for."""

    def __init__(self, tree_path: Path, registry: BlockRegistry) -> None:
        self.tree_path: Path = tree_path
        self.registry: BlockRegistry = registry
        self.tree: DecisionTree = DecisionTree.load(tree_path, registry)
        self.policy: Policy = Policy(self.tree, registry.predicate_ids(), registry.action_ids())

    def run_one(self, seed: int) -> tuple[RunOutcome, Session]:
        world = World(seed)
        # Only the predicates the tree reads exist in an evaluation run: a parametric
        # predicate the tree never asks about has no parameter to evaluate it with.
        used = [pid for pid in self.registry.predicate_ids() if pid in self.tree.predicates_used()]
        session = Session(world, self.registry, enabled_predicates=used, params=self.policy.params)
        while (view := session.advance_to_stop()) is not None:
            session.choose(self.policy.choose(view.belief))
        assert session.outcome is not None
        return session.outcome, session

    def run(self, seeds: Iterable[int], quiet: bool = False) -> float:
        seeds = list(seeds)
        params = ", ".join(f"{pid} {vals}" for pid, vals in self.policy.params.items()) or "no params"
        if not quiet:
            print(f"tree {self.tree_path.as_posix()}  ({params})  seeds {seeds[0]}..{seeds[-1]}")
            print(f"{'seed':>4}  {'result':<10} {'ticks':>6} {'budget':>6} {'stops':>5} "
                  f"{'fixes':>5} {'walked':>6} {'depth':>5} {'misturns':>8} {'first@':>6}")
        successes = 0
        for seed in seeds:
            outcome, session = self.run_one(seed)
            successes += int(outcome.success)
            if not quiet:
                corridor = session.world.corridor          # the reveal: truth, after the run
                first = "-" if session.first_misturn_stop is None else str(session.first_misturn_stop)
                print(f"{seed:>4}  {outcome.reason:<10} {outcome.ticks:>6} {session.budget:>6} "
                      f"{session.stops:>5} {session.belief.fixes:>5} {session.belief.dist_total:>6.0f} "
                      f"{corridor.depth_of(corridor.deposit):>5} "
                      f"{session.misturns:>8} {first:>6}")
        rate = successes / len(seeds)
        if not quiet:
            print(f"success {successes}/{len(seeds)} = {100.0 * rate:.0f}%")
        return rate
