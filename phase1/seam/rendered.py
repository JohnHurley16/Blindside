"""What `induct render` answered: a tree in words."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True, frozen=True)
class Rendered:
    """One line per node, and the whole tree as one sentence."""
    lines: list[str]
    sentence: str

    @classmethod
    def parse(cls, data: dict[str, Any]) -> Rendered:
        return cls(lines=[str(line) for line in data["lines"]], sentence=str(data["sentence"]))
