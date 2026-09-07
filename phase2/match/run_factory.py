"""Open runs. The one place a World is built for the tutorial and its replays.

**This module reads ground truth.** It exists so that the window, the replays and
the demonstrations do not: they are handed a `demo.run_source.RunSource` and get
back the narrow `DriverView` face of a Session. It also keeps the last session it
opened, so that `__main__` can ask for that run's reveal after it is over.
"""
from __future__ import annotations

from typing import Iterable, Mapping

from ..policy.block_registry import BlockRegistry
from ..reveal.truth_snapshot import TruthSnapshot
from .driver_view import DriverView
from .reveal_builder import RevealBuilder
from .session import Session
from ..truth.world import World


class RunFactory:
    """`RunSource` over `Session`, plus the reveal for the run that just ended."""

    def __init__(self, registry: BlockRegistry) -> None:
        self.registry: BlockRegistry = registry
        self.last: Session | None = None

    def open(self, seed: int, *, enabled_predicates: Iterable[str],
             enabled_actions: Iterable[str],
             params: Mapping[str, Mapping[str, float]],
             drift: bool) -> DriverView:
        session = Session(World(seed), self.registry,
                          enabled_predicates=enabled_predicates,
                          enabled_actions=enabled_actions,
                          params=params, drift=drift)
        self.last = session
        return DriverView(session)

    def reveal(self) -> TruthSnapshot | None:
        """The truth of the last run opened. Called by `__main__` after a run ends."""
        return None if self.last is None else RevealBuilder.of(self.last)
