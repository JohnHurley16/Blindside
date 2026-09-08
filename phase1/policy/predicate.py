"""One predicate block, as listed in blocks.json."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class Predicate:
    """A boolean test over Belief. `param` names its one parameter, if it has one:
    then its boolean is a function of a raw number and that parameter.

    `stage` is the tutorial run at which this block first exists -- the optional,
    Python-side field the corridor added to blocks.json. The induction ignores it.
    The value of `param` a demonstration runs with is `tuning.DEMONSTRATION_PARAMS`,
    keyed by the parameter's name: the induct crate refuses a block list with a field
    it does not know, so it cannot travel on the list.
    """
    id: str
    label: str
    param: str | None = None
    stage: int = 1
