"""Am I too lost?"""
from __future__ import annotations

from typing import Mapping

from ...belief.belief import Belief


def evaluate(belief: Belief, params: Mapping[str, float]) -> tuple[bool, float | None]:
    """Position sigma against the one parameter, under whatever name the block
    list gives it. The parameter is fitted by the induction, never set here. The
    raw sigma is returned alongside so the threshold can be re-fitted."""
    if len(params) != 1:
        raise ValueError(f"this predicate takes exactly one parameter, got {dict(params)}")
    threshold = float(next(iter(params.values())))
    sigma = belief.sigma_pos()
    return sigma > threshold, sigma
