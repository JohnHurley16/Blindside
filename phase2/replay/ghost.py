"""Run the induced tree on a demonstration's seed, beside the demonstration.

Same seed, same blocks, same drift setting, so the same drift stream: the two runs
diverge only where the tree chooses differently from the player. The comparison
itself is `induct diff` over the two lists of choices -- the seam decides where
they first part, not this file.
"""
from __future__ import annotations

from pathlib import Path

from ..demo.recording import Recording
from ..demo.run_source import RunSource
from ..demo.trace_step import TraceStep
from ..induct_client import InductClient
from ..policy.block_registry import BlockRegistry
from ..policy.decision_tree import DecisionTree
from ..policy.policy import Policy
from .ghost_result import GhostResult


class Ghost:
    """One demonstration, one tree, one answer."""

    def __init__(self, source: RunSource, registry: BlockRegistry, client: InductClient) -> None:
        self.source: RunSource = source
        self.registry: BlockRegistry = registry
        self.client: InductClient = client

    def can_run(self, recording: Recording, tree: DecisionTree) -> bool:
        """A tree that names a block the run never had cannot be replayed on it --
        the tutorial's first run is the case that matters."""
        have = set(recording.trace.enabled_predicates) | set(recording.trace.enabled_actions)
        return not (tree.predicates_used() | tree.actions_used()) - have

    def run(self, recording: Recording, tree_path: Path) -> GhostResult:
        """Re-simulate, collect the choices, and ask the seam where they differ."""
        tree = DecisionTree.load(tree_path, self.registry)
        trace = recording.trace
        policy = Policy(tree, trace.enabled_predicates, trace.enabled_actions)
        driver = self.source.open(trace.seed,
                                  enabled_predicates=trace.enabled_predicates,
                                  enabled_actions=trace.enabled_actions,
                                  params=trace.params, drift=recording.stage.drift)
        steps: list[TraceStep] = []
        while (view := driver.advance_to_stop()) is not None:
            action = policy.choose(view.belief)
            step = TraceStep(tick=view.tick, junction=view.junction,
                             predicates=dict(view.predicates), raw=dict(view.raw),
                             action=action)
            # The same rule the demonstration recorded under, or the two lists of
            # choices `induct diff` is given would not be about the same thing.
            if driver.choose(action):
                steps.append(step)
        demonstrated = recording.choices()
        ghosted = [s.action for s in steps]
        diff = self.client.diff(demonstrated, ghosted, name=f"ghost-{trace.seed}")
        return GhostResult(seed=trace.seed, demonstrated=demonstrated, ghosted=ghosted,
                           diff=diff, outcome=driver.outcome, steps=steps)
