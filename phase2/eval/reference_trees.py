"""The two hand-built reference trees, written as tree.json under phase2/reference/.

    python -m phase2.eval.reference_trees

These are data, built by hand, and so may name blocks by id -- the one exception
to the rule that nothing outside blocks.json and the registry does.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .. import tuning as T

REFERENCE_DIR: Path = Path(__file__).resolve().parent.parent / "reference"


def dfs_ignores_theta() -> dict[str, Any]:
    """Depth-first, home once carrying, never mind how lost."""
    return {
        "params": {},
        "root": {
            "predicate": "carrying_cargo",
            "yes": {"action": "return_to_beacon"},
            "no": {
                "predicate": "unexplored_branch_exists",
                "yes": {"action": "take_branch"},
                "no": {"action": "return_to_beacon"},
            },
        },
    }


def theta_aware() -> dict[str, Any]:
    """The same, but turn back for a fix once too lost."""
    return {
        "params": {"uncertainty_exceeds": {"theta": T.THETA_AWARE_THETA}},
        "root": {
            "predicate": "carrying_cargo",
            "yes": {"action": "return_to_beacon"},
            "no": {
                "predicate": "uncertainty_exceeds",
                "yes": {"action": "return_to_beacon"},
                "no": {
                    "predicate": "unexplored_branch_exists",
                    "yes": {"action": "take_branch"},
                    "no": {"action": "return_to_beacon"},
                },
            },
        },
    }


def write_reference_trees(directory: Path = REFERENCE_DIR) -> list[Path]:
    directory.mkdir(parents=True, exist_ok=True)
    out: list[Path] = []
    for name, tree in (("dfs_ignores_theta", dfs_ignores_theta()), ("theta_aware", theta_aware())):
        path = directory / f"{name}.json"
        path.write_text(json.dumps(tree, indent=1) + "\n", encoding="utf-8")
        out.append(path)
    return out


if __name__ == "__main__":
    for written in write_reference_trees():
        print(f"wrote {written.as_posix()}")
