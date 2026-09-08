"""What `induct induce` answered."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .query import Query
from .step_ref import StepRef


@dataclass(slots=True, frozen=True)
class Induction:
    """A tree, or the conflicts that stopped one existing.

    `tree` is the contract's tree.json as a plain dict -- this side interprets it
    with `policy.decision_tree` and never rewrites it. `path` is where the tree
    was written; None when the traces were inconsistent, because the induction
    does not write a file then.
    """
    consistent: bool
    tree: dict[str, Any] | None
    conflicts: list[tuple[StepRef, StepRef]]
    query: Query | None
    path: Path | None

    @classmethod
    def parse(cls, data: dict[str, Any], out: Path) -> Induction:
        consistent = bool(data["consistent"])
        query = data.get("query")
        return cls(
            consistent=consistent,
            tree=data.get("tree"),
            conflicts=[(StepRef.parse(a), StepRef.parse(b)) for a, b in data.get("conflicts", [])],
            query=None if query is None else Query.parse(query),
            path=out if consistent else None,
        )
