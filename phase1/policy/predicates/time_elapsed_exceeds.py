"""Is it late?"""
from __future__ import annotations

from typing import Mapping

from ...belief.belief import Belief


def evaluate(belief: Belief, params: Mapping[str, float]) -> tuple[bool, float | None]:
    """Match seconds elapsed on the agent's own clock, against the one parameter.

    Elapsed rather than remaining, because the induction tests `raw > value`. The
    raid has a deadline and a stateless tree has no other way to know it.
    """
    if len(params) != 1:
        raise ValueError(f"this predicate takes exactly one parameter, got {dict(params)}")
    threshold = float(next(iter(params.values())))
    return belief.t > threshold, belief.t
