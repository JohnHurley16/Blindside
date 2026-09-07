"""Is there a branch worth taking at the junction I believe I am standing at?"""
from __future__ import annotations

from typing import Mapping

from ...belief.belief import Belief


def evaluate(belief: Belief, params: Mapping[str, float]) -> tuple[bool, float | None]:
    """True when some onward passage at this junction is not exhausted: not yet
    walked, or walked with unexplored ground still beyond it.

    Only passages *at the current believed junction* are candidates -- no other
    junction's mouths are offered. But deciding whether one of them is exhausted
    reads the believed subtree beyond it (`Belief.exhausted` recurses), so this
    predicate is not a purely local test, and its label says so.

    That is a deliberate reading of the spec and it is load-bearing; see the note
    at the head of `phase2/belief/belief.py`. Under the strictly local reading --
    true only when a mouth here has never been walked -- the shaft's one passage
    is walked the moment the agent comes home for a fix, so no policy over these
    three predicates can ever resume exploring, and the theta-aware reference tree
    scores 1/20 instead of 20/20 (measured).
    """
    return bool(belief.unexplored_here()), None
