"""Can I hear the machinery, and how loud?"""
from __future__ import annotations

from typing import Mapping

from ... import tuning as T
from ...belief.belief import Belief


def evaluate(belief: Belief, params: Mapping[str, float]) -> tuple[bool, float | None]:
    """The signature's quality if heard within SIGNATURE_STALE_S, else 0, against the
    one parameter.

    One block for both temperaments: the cautious one freezes at 0.45 and the
    aggressive one goes to look at 0.30, and the fitted threshold says which the
    player meant. Quality already carries the aim -- the agent about to be hit hears
    it loudest -- so no second block is needed for direction.
    """
    if len(params) != 1:
        raise ValueError(f"this predicate takes exactly one parameter, got {dict(params)}")
    threshold = float(next(iter(params.values())))
    sig = belief.signature
    level = sig.quality if (sig is not None and belief.t - sig.t < T.SIGNATURE_STALE_S) else 0.0
    return level > threshold, level
