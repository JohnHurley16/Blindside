"""One predicate block, as listed in blocks.json."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class Predicate:
    """A boolean test over Belief. `param` names its one parameter, if it has one:
    then its boolean is a function of a raw number and that parameter.

    `stage` is the tutorial run at which this block first exists -- the optional,
    Python-side field the corridor added to blocks.json. The induction ignores it.
    The value of `param` a demonstration runs with is the `provisional` field beside
    the block in blocks.json -- so a parametric block is one list entry and one evaluator
    file, like any other. The induct crate declares the field and ignores it.
    """
    id: str
    label: str
    param: str | None = None
    stage: int = 1
