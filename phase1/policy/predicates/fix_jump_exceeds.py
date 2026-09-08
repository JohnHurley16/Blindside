"""Did the map just snap further than it should have?"""
from __future__ import annotations

from typing import Mapping

from ... import tuning as T
from ...belief.belief import Belief


def evaluate(belief: Belief, params: Mapping[str, float]) -> tuple[bool, float | None]:
    """The largest fix jump, in cells, in the last FIX_JUMP_MEMORY_S; 0 when none.

    The spoof, made visible to the tree. `FixRecord.jump` is belief-derived and the
    rail already prints it as the tell. A memory rather than the most recent fix,
    because the spoof reasserts every 8 s and a small honest fix would otherwise
    erase the big one before the next stop. Honest about being weak: an old beacon's
    honest fix can jump as far as the lie (tuning.py, BEACON_RANGE).
    """
    if len(params) != 1:
        raise ValueError(f"this predicate takes exactly one parameter, got {dict(params)}")
    threshold = float(next(iter(params.values())))
    since = belief.t - T.FIX_JUMP_MEMORY_S
    biggest = max((f.jump for f in belief.fixes if f.t >= since), default=0.0)
    return biggest > threshold, biggest
