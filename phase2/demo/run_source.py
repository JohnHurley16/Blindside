"""Where a run comes from, as far as anything downstream of the sensor layer knows.

A run needs a World, and World is ground truth, so nothing in `demo`, `replay` or
`view` may build one. They are handed this instead: something that opens a run and
gives back the narrow `RunDriver` face of it. `match.run_factory.RunFactory` is the
implementation; the invariant check is what keeps it the only one that is imported
where it matters.
"""
from __future__ import annotations

from typing import Iterable, Mapping, Protocol

from .run_driver import RunDriver


class RunSource(Protocol):
    """Seed in, a driver out. Nothing about the world crosses this either."""

    def open(self, seed: int, *, enabled_predicates: Iterable[str],
             enabled_actions: Iterable[str],
             params: Mapping[str, Mapping[str, float]],
             drift: bool) -> RunDriver: ...
