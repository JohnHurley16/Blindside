"""The rule the player taught, as the spectator rail shows it: rendered by the seam."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True, frozen=True)
class TaughtRule:
    """`lines` and `sentence` are `induct render`'s -- the block list's labels arranged
    by the induction; this side never builds them. `root` and `params` are the
    tree.json itself, so `tree_path` can light the lines a decision walked."""
    path: Path
    lines: list[str]
    sentence: str
    root: dict[str, Any]
    params: dict[str, dict[str, float]] = field(default_factory=dict)
