"""One predicate block, as listed in blocks.json."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class Predicate:
    """A boolean test over Belief. `param` names its one parameter, if it has one:
    then its boolean is a function of a raw number and that parameter.

    `stage` is the tutorial run at which this block first exists. It is an OPTIONAL
    field this side added to blocks.json, so that which blocks a staged run has is
    data on the list rather than a set of ids written somewhere else. The induction
    ignores it.
    """
    id: str
    label: str
    param: str | None = None
    stage: int = 1
