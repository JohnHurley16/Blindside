"""Is there somewhere worth going?"""
from __future__ import annotations

from typing import Mapping

from ...belief.belief import Belief


def evaluate(belief: Belief, params: Mapping[str, float]) -> tuple[bool, float | None]:
    """A survey deposit the load program has not yet marked tried.

    Asked of intel rather than of exploration: the cave has no junction graph in
    belief, but it has the survey's deposits. Loaded from, given up on, or never
    reached all count as tried, so this goes false the moment the last one is done
    with -- whether or not anything was loaded.
    """
    tried = belief.tried_deposits
    return any(place not in tried for place in belief.survey.deposits), None
