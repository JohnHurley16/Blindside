"""The active-learning question, when no separator exists."""
from __future__ import annotations

from dataclasses import dataclass

from .step_ref import StepRef


@dataclass(slots=True, frozen=True)
class Query:
    """Two contradicting stops and the text that shows them side by side.

    The text is written by the induction and is already in the block list's
    labels; this side prints it as it arrives.
    """
    pair: tuple[StepRef, StepRef]
    text: str

    @classmethod
    def parse(cls, data: dict[str, object]) -> Query:
        pair = [StepRef.parse(p) for p in data["pair"]]        # type: ignore[union-attr]
        return cls(pair=(pair[0], pair[1]), text=str(data["text"]))
