"""A decision tree over the block list: the contract's tree.json, interpreted.

Copied from the corridor (`phase2/policy/decision_tree.py`); it is the contract. One
method is added, `walk`, which returns the path a decision took as well as the action,
because the cave's decision graph draws the path. No rendering here; the Rust side
renders.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from ..belief.belief import Belief
from .block_registry import BlockRegistry

Node = dict[str, Any]
Params = Mapping[str, Mapping[str, float]]


class DecisionTree:
    """A node is either {"action": id} or {"predicate": id, "yes": node, "no": node}."""

    def __init__(self, root: Node, params: dict[str, dict[str, float]], registry: BlockRegistry) -> None:
        self.root: Node = root
        self.params: dict[str, dict[str, float]] = params
        self.registry: BlockRegistry = registry
        self._check(root)

    @classmethod
    def load(cls, path: Path, registry: BlockRegistry) -> DecisionTree:
        data = json.loads(path.read_text(encoding="utf-8"))
        params = {k: {n: float(v) for n, v in vals.items()} for k, vals in data.get("params", {}).items()}
        return cls(data["root"], params, registry)

    def _check(self, node: Node) -> None:
        if "action" in node:
            if node["action"] not in self.registry.action_ids():
                raise ValueError(f"tree names an action not in the block list: {node['action']}")
            return
        if node["predicate"] not in self.registry.predicate_ids():
            raise ValueError(f"tree names a predicate not in the block list: {node['predicate']}")
        self._check(node["yes"])
        self._check(node["no"])

    def decide(self, belief: Belief, params: Params) -> str:
        """Walk from the root, evaluating each predicate on Belief, to an action id."""
        return self.walk(belief, params)[0]

    def walk(self, belief: Belief, params: Params) -> tuple[str, list[tuple[str, bool]]]:
        """The action, and every (predicate, answer) on the way to it, in order."""
        node = self.root
        path: list[tuple[str, bool]] = []
        while "action" not in node:
            pid = node["predicate"]
            value, _ = self.registry.evaluate(pid, belief, params.get(pid, {}))
            path.append((pid, value))
            node = node["yes"] if value else node["no"]
        return str(node["action"]), path

    def predicates_used(self) -> set[str]:
        return {n["predicate"] for n in self._walk(self.root) if "predicate" in n}

    def predicates_in_order(self) -> list[str]:
        """Distinct predicates in preorder: a stable order for a display to list them in."""
        seen: list[str] = []
        for n in self._walk(self.root):
            if "predicate" in n and n["predicate"] not in seen:
                seen.append(n["predicate"])
        return seen

    def actions_used(self) -> set[str]:
        return {n["action"] for n in self._walk(self.root) if "action" in n}

    def _walk(self, node: Node) -> list[Node]:
        if "action" in node:
            return [node]
        return [node] + self._walk(node["yes"]) + self._walk(node["no"])
