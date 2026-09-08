"""Open matches. The one place a Sim is built for demonstrations and their replays.

**This module builds ground truth.** It exists so that the demonstration, the ghost,
the correction and the teach window do not: they are handed a `demo.run_source.
RunSource` and get back the `MatchView` face of a Sim, which has no route to World.
The truth channel is never switched on here: a demonstration is a belief-only affair
and a replay has no screen.
"""
from __future__ import annotations

from pathlib import Path

from ..policy.run_spec import RunSpec
from .match_view import MatchView
from .sim import Sim


class RunFactory:
    """`RunSource` over `Sim`."""

    def open(self, seed: int, spec: RunSpec, tree: Path | None) -> MatchView:
        return MatchView(Sim(seed, stage=False, tree=tree, spec=spec, taught=tree is None))
