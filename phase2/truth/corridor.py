"""A seeded branching corridor: the whole of Phase 2's world.

A shaft at the root, eight junctions each with two or three onward passages,
leaves that dead-end, one deposit at a random leaf. Nothing else.
"""
from __future__ import annotations

import math

import numpy as np

from .. import geometry as G
from .. import tuning as T
from .junction import Junction
from .passage import Passage


class Corridor:
    """The graph and its geometry, both fixed by the seed."""

    def __init__(self, seed: int) -> None:
        self.seed: int = seed
        self.nodes: dict[int, Junction] = {}
        self.passages: dict[int, Passage] = {}
        self.shaft: int = 0
        rng = np.random.default_rng([seed, 0])
        self._add_node(depth=0, parent=None, x=0.0, y=0.0)
        first = self._add_passage(rng, self.shaft, float(rng.uniform(-math.pi, math.pi)))
        self._branch(rng, first.far)
        for _ in range(T.JUNCTIONS - 1):
            leaves = self.leaves()
            self._branch(rng, leaves[int(rng.integers(0, len(leaves)))])
        leaves = self.leaves()
        self.deposit: int = leaves[int(rng.integers(0, len(leaves)))]

    # ---- construction --------------------------------------------------------------
    def _add_node(self, depth: int, parent: int | None, x: float, y: float) -> Junction:
        node = Junction(id=len(self.nodes), depth=depth, parent=parent, x=x, y=y)
        self.nodes[node.id] = node
        return node

    def _add_passage(self, rng: np.random.Generator, near: int, bearing: float) -> Passage:
        length = int(rng.integers(T.PASSAGE_MIN_CELLS, T.PASSAGE_MAX_CELLS + 1))
        parent = self.nodes[near]
        pid = len(self.passages)
        far = self._add_node(depth=parent.depth + 1, parent=pid,
                             x=parent.x + math.cos(bearing) * length,
                             y=parent.y + math.sin(bearing) * length)
        passage = Passage(id=pid, near=near, far=far.id, bearing=bearing, length=length)
        self.passages[pid] = passage
        parent.onward.append(pid)
        return passage

    def _branch(self, rng: np.random.Generator, node_id: int) -> None:
        """Turn a leaf into a junction with two or three onward passages."""
        node = self.nodes[node_id]
        assert node.parent is not None
        incoming = self.passages[node.parent].bearing
        count = int(T.BRANCH_CHOICES[int(rng.integers(0, len(T.BRANCH_CHOICES)))])
        for offset in self._offsets(rng, count):
            self._add_passage(rng, node_id, G.wrap(incoming + offset))

    @staticmethod
    def _offsets(rng: np.random.Generator, count: int) -> list[float]:
        """Onward directions relative to the way in, all at least MIN_SEPARATION
        apart from each other and from the way back (which sits at +-180)."""
        limit = math.radians(T.ONWARD_MAX_OFFSET_DEG)
        sep = math.radians(T.PASSAGE_MIN_SEPARATION_DEG)
        while True:
            offsets = sorted((float(v) for v in rng.uniform(-limit, limit, size=count)),
                             reverse=True)
            if any(abs(o) > math.pi - sep for o in offsets):
                continue
            if all(offsets[i] - offsets[i + 1] >= sep for i in range(count - 1)):
                return offsets

    # ---- queries -----------------------------------------------------------------------
    def children(self, junction: int) -> list[int]:
        """Onward passage ids leaving a node, deeper."""
        return list(self.nodes[junction].onward)

    def bearing(self, passage: int) -> float:
        return self.passages[passage].bearing

    def length(self, passage: int) -> int:
        return self.passages[passage].length

    def passages_at(self, junction: int) -> list[tuple[int, float]]:
        """Every passage mouth at a node with its bearing away from the node --
        onward passages and the way back alike. The branch rule chooses among these."""
        node = self.nodes[junction]
        out = [(pid, self.passages[pid].bearing) for pid in node.onward]
        if node.parent is not None:
            out.append((node.parent, G.wrap(self.passages[node.parent].bearing + math.pi)))
        return out

    def leaves(self) -> list[int]:
        return [n.id for n in self.nodes.values() if n.is_leaf]

    def junction_ids(self) -> list[int]:
        return [n.id for n in self.nodes.values() if n.parent is not None and n.onward]

    def far_end(self, passage: int, from_node: int) -> int:
        p = self.passages[passage]
        return p.far if p.near == from_node else p.near

    def passage_ticks(self, passage: int) -> int:
        return math.ceil(self.passages[passage].length / (T.AGENT_SPEED * T.DT))

    def dfs_walk_ticks(self) -> int:
        """Ticks a full depth-first walk needs: every passage out and back."""
        return 2 * sum(self.passage_ticks(pid) for pid in self.passages)

    def layout(self) -> dict[int, tuple[float, float]]:
        """Node positions for drawing, shaft at the origin. Deterministic in the seed."""
        return {n.id: (n.x, n.y) for n in self.nodes.values()}

    def depth_of(self, junction: int) -> int:
        return self.nodes[junction].depth
