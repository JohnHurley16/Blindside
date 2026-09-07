"""Ground truth stepping. Holds the corridor and the agent; nothing downstream
of the sensor layer may see it.

THE BRANCH-CHOICE RULE lives here, in `depart`.
"""
from __future__ import annotations

import math

from .. import geometry as G
from .. import tuning as T
from .agent_truth import AgentTruth
from .corridor import Corridor


class World:
    """The corridor, the agent, and the tick."""

    def __init__(self, seed: int) -> None:
        self.seed: int = seed
        self.corridor: Corridor = Corridor(seed)
        first = self.corridor.passages[self.corridor.children(self.corridor.shaft)[0]]
        self.agent: AgentTruth = AgentTruth(seed, node=self.corridor.shaft, heading=first.bearing)
        self.tick: int = 0
        self._pending_turn: float = 0.0
        self.turns: int = 0

    # ---- the branch-choice rule ------------------------------------------------------------
    def depart(self, turn: float) -> int:
        """Leave the node the agent is stopped at.

        The motor asked for a turn relative to the heading the agent BELIEVES it has.
        The body turns by exactly that, so whatever heading error the belief carries
        is carried into the choice: the passage taken is the one whose true bearing
        best matches the body's new heading. When the heading error exceeds half
        the angle between two passages, the wrong one is taken. That is the whole of
        drift's teeth, and it is the only place they bite.

        Once inside, the agent follows the passage, so its body aligns with the
        passage's bearing; the odometry reports that as the turn actually made.
        """
        me = self.agent
        assert me.node is not None, "depart called while walking"
        before = me.heading
        wanted = G.wrap(me.heading + turn)
        candidates = self.corridor.passages_at(me.node)
        pid, bearing = min(candidates, key=lambda c: G.angle_between(c[1], wanted))
        passage = self.corridor.passages[pid]
        me.heading = bearing
        self._pending_turn = G.wrap(me.heading - before)
        me.passage = pid
        if passage.near == me.node:
            me.direction, me.along = 1, 0.0
        else:
            me.direction, me.along = -1, float(passage.length)
        me.node = None
        self.turns += 1
        return pid

    def hold(self) -> None:
        """Stay put this tick."""
        self._pending_turn = 0.0

    # ---- stepping ----------------------------------------------------------------------------
    def step(self) -> None:
        me = self.agent
        moved = 0.0
        if me.passage is not None:
            passage = self.corridor.passages[me.passage]
            step = T.AGENT_SPEED * T.DT
            if me.direction > 0:
                moved = min(step, passage.length - me.along)
                me.along += moved
                if me.along >= passage.length:
                    self._arrive(passage.far)
            else:
                moved = min(step, me.along)
                me.along -= moved
                if me.along <= 0.0:
                    self._arrive(passage.near)
        me.last_true_delta = (moved, self._pending_turn)
        self._pending_turn = 0.0
        self.tick += 1

    def _arrive(self, node: int) -> None:
        me = self.agent
        me.node = node
        me.passage = None
        if node == self.corridor.deposit:
            me.cargo = 1

    # ---- what the sensor layer and the evaluator ask ---------------------------------------------
    def shaft_distance(self) -> float:
        """Distance along passages from the shaft: the beacon is heard down the
        shaft passage, not through rock."""
        me = self.agent
        if me.node == self.corridor.shaft:
            return 0.0
        first = self.corridor.children(self.corridor.shaft)[0]
        if me.passage == first:
            return me.along
        return math.inf

    def in_shaft_range(self) -> bool:
        return self.shaft_distance() < T.SHAFT_BEACON_RANGE

    def position(self) -> tuple[float, float]:
        """The true 2D position, for the post-run reveal only."""
        me = self.agent
        if me.node is not None:
            n = self.corridor.nodes[me.node]
            return n.x, n.y
        assert me.passage is not None
        p = self.corridor.passages[me.passage]
        near = self.corridor.nodes[p.near]
        return (near.x + math.cos(p.bearing) * me.along, near.y + math.sin(p.bearing) * me.along)
