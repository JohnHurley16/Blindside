"""Have I got the thing?"""
from __future__ import annotations

from typing import Mapping

from ...belief.belief import Belief


def evaluate(belief: Belief, params: Mapping[str, float]) -> tuple[bool, float | None]:
    """The self-reported hold is not empty."""
    return belief.cargo > 0, None
