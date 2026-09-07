"""What `induct diff` answered: where two runs first chose differently."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True, frozen=True)
class ChoiceDiff:
    """`index` is the first stop at which the two choice lists differ, or at which
    one ends and the other does not. All three are None when they are identical."""
    index: int | None
    a: str | None
    b: str | None

    @classmethod
    def parse(cls, data: dict[str, Any]) -> ChoiceDiff:
        first = data.get("first_difference")
        return cls(index=None if first is None else int(first),
                   a=data.get("a"), b=data.get("b"))

    @property
    def agree(self) -> bool:
        return self.index is None
