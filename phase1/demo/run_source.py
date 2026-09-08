"""Where a match comes from, as far as anything downstream of the sensor layer knows.

A match needs a `Sim`, and a `Sim` holds ground truth, so nothing in `demo`, `replay`
or `view` may build one. They are handed this instead: something that opens a match
and gives back its `MatchView` face. `match.run_factory.RunFactory` is the
implementation; `match/invariant.py` keeps it the only one that is imported where it
matters.
"""
from __future__ import annotations

from pathlib import Path
from typing import Protocol

from ..match.match_view import MatchView
from ..policy.run_spec import RunSpec


class RunSource(Protocol):
    """Seed and blocks in, a match out. With a `tree` the player's policy is that
    tree; without one every stop is a question (`MatchView.paused`)."""

    def open(self, seed: int, spec: RunSpec, tree: Path | None) -> MatchView: ...
