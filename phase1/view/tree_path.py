"""Which lines of a rendered tree a stop lit up. Functions only. The corridor's.

`induct render` prints one line per node in preorder -- the node, then its yes
subtree, then its no subtree -- so a node's position in that walk is its line
number. This file walks the same order to work out which lines a stop's path went
through, so the panel can light them.

It also has to decide the tree on a recorded stop rather than on a Belief, and
that means restating the seam's reading of a stop: a parametric predicate with a
raw number and a value for its parameter is `raw > value`; otherwise the boolean
the stop recorded; absent from both, false (FORMAT.md, "How a stop is read").
That is the one rule this side duplicates; `--induce` cross-checks the seam's own
`decide` against every recorded stop, and the rail lights the path of a decision
the policy has already made, so a disagreement would show as a lit path ending at
a leaf other than the action running under it.
"""
from __future__ import annotations

from typing import Any, Mapping

from ..policy.block_registry import BlockRegistry

Node = dict[str, Any]


def preorder(root: Node) -> list[Node]:
    """The nodes in the order the render prints them."""
    if "action" in root:
        return [root]
    return [root] + preorder(root["yes"]) + preorder(root["no"])


def holds(predicate_id: str, registry: BlockRegistry,
          params: Mapping[str, Mapping[str, float]],
          predicates: Mapping[str, bool], raw: Mapping[str, float]) -> bool:
    """One predicate's value at one recorded stop."""
    param = registry.predicate(predicate_id).param
    if param is not None and predicate_id in raw:
        value = params.get(predicate_id, {}).get(param)
        if value is not None:
            return float(raw[predicate_id]) > float(value)
    return bool(predicates.get(predicate_id, False))


def lit_lines(root: Node, registry: BlockRegistry,
              params: Mapping[str, Mapping[str, float]],
              predicates: Mapping[str, bool],
              raw: Mapping[str, float]) -> tuple[list[int], str]:
    """The line numbers on this stop's path, and the action it reached."""
    order = preorder(root)
    index = {id(node): i for i, node in enumerate(order)}
    lines: list[int] = []
    node = root
    while True:
        lines.append(index[id(node)])
        if "action" in node:
            return lines, str(node["action"])
        node = node["yes"] if holds(node["predicate"], registry, params, predicates, raw) \
            else node["no"]
