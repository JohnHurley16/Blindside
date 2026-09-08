"""Run the induced tree on a demonstration's seed, beside the demonstration.

Same seed, same blocks, same provisional thresholds, so the same stops and the same
sensor streams: the two matches diverge only where the tree chooses differently from
the player. The comparison itself is `induct diff` over the two lists of choices --
the seam decides where they first part, not this file.
"""
from __future__ import annotations

from pathlib import Path

from .. import tuning as T
from ..demo.recording import Recording
from ..demo.run_source import RunSource
from ..demo.trace_writer import TraceWriter
from ..induct_client import InductClient
from ..policy.block_registry import BlockRegistry
from ..policy.decision_tree import DecisionTree
from ..policy.run_spec import RunSpec
from .ghost_result import GhostResult


class Ghost:
    """One demonstration, one tree, one answer."""

    def __init__(self, source: RunSource, registry: BlockRegistry, client: InductClient) -> None:
        self.source: RunSource = source
        self.registry: BlockRegistry = registry
        self.client: InductClient = client

    def can_run(self, recording: Recording, tree: DecisionTree) -> bool:
        """A tree that names a block the run never had cannot be replayed on it."""
        have = set(recording.trace.enabled_predicates) | set(recording.trace.enabled_actions)
        return not (tree.predicates_used() | tree.actions_used()) - have

    def run(self, recording: Recording, tree_path: Path) -> GhostResult:
        """Re-simulate with the tree as the player's policy, over the demonstration's
        blocks, collect its choices, and ask the seam where they differ."""
        trace = recording.trace
        spec = RunSpec.from_trace(trace.enabled_predicates, trace.enabled_actions, trace.params)
        match = self.source.open(trace.seed, spec, tree_path)
        while not match.over:
            match.advance_to(T.MATCH_SECONDS + 1.0)
            if match.paused:
                raise RuntimeError("a ghost on a tree should never be asked")
        ghost_trace = TraceWriter.from_match(match)
        demonstrated = recording.choices()
        ghosted = ghost_trace.choices()
        diff = self.client.diff(demonstrated, ghosted, name=f"ghost-{trace.seed}")
        return GhostResult(seed=trace.seed, demonstrated=demonstrated, ghosted=ghosted,
                           diff=diff, outcome=ghost_trace.outcome, steps=list(ghost_trace.steps))
