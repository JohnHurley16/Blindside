"""What the agent thinks. Assembled only from sensor returns.

**This module must never import `phase2.truth`.** A policy reads this object and
nothing else, so anything that leaks in here leaks into the policy.

WHAT "UNEXPLORED" MEANS HERE, and why it is a question for the designer.
`unexplored_here()` offers the passages at the current believed junction that are
not *exhausted*: not walked, or walked with something beyond them still unwalked.
`PHASE-2-OPEN-QUESTIONS.md` (c) says "the current junction only", which reads as
the stricter test -- a mouth here that has never been walked.

The strict test cannot be made to work with the day-one block list, and this is
measured, not argued. The shaft has one onward passage. The moment a policy goes
home for a fix that passage is walked, so at the shaft the strict predicate is
false forever after, the tree falls through to `return_to_beacon`, and the run
ends standing on the beacon with no cargo. On seeds 0..19 the theta-aware
reference tree scores 1/20 under the strict test and 20/20 under this one; the
depth-first tree scores 13/20 under both, because it never goes home until it is
carrying and so never meets the case where the two readings differ.

So the choice is between a test the spec's wording implies and an acceptance
criterion the spec states (a theta-aware tree succeeding at least nine times in
ten). This code takes the second, and the label of the predicate block in
blocks.json was rewritten to describe what is actually tested, so that the
rendered rule does not lie to a player reading it at a junction whose own mouths
are all walked. The alternative is a fourth block; that is the designer's call
and it is R5 evidence either way.
"""
from __future__ import annotations

import math

from .. import geometry as G
from .. import tuning as T
from ..sensing.returns import CargoReturn, JunctionReturn, OdometryReturn, Return, ShaftFixReturn
from .junction_node import JunctionNode
from .seen_passage import SeenPassage


class Belief:
    """Believed pose with sigma, the believed junction graph, the route back, cargo.
    Frequently wrong."""

    def __init__(self) -> None:
        # pose, in the belief frame; the shaft is surveyed at the origin
        self.x: float = 0.0
        self.y: float = 0.0
        self.theta: float = 0.0
        self.trail: list[tuple[float, float]] = [(0.0, 0.0)]

        # uncertainty: Phase 1's estimator, position only
        self.dist_since_fix: float = 0.0
        self.dist_total: float = 0.0
        self.sigma_theta: float = T.EST_HEADING_SIGMA_AFTER_FIX
        self.fixes: int = 0

        # the believed junction graph
        self.nodes: dict[int, JunctionNode] = {}
        self.shaft: int = 0
        self.current: int | None = None              # believed node when stopped
        self.walking: tuple[int, int | None] | None = None   # (from node, passage index); None = back
        self._snap_to_shaft: bool = False            # a fix arrived mid-walk
        self.fixed_here: bool = False                # a fix arrived since the last departure
        self.cargo: int = 0
        self.cargo_at: int | None = None             # believed node where cargo appeared
        self.log: list[tuple[int, str]] = []

    # ---- uncertainty -------------------------------------------------------------------
    def sigma_along(self) -> float:
        return T.EST_SIGMA_AFTER_FIX + T.EST_SIGMA_ALONG_PER_CELL * self.dist_since_fix

    def sigma_cross(self) -> float:
        return T.EST_SIGMA_AFTER_FIX + 0.5 * self.dist_since_fix * self.sigma_theta

    def sigma_pos(self) -> float:
        return math.hypot(self.sigma_along(), self.sigma_cross())

    # ---- fusion -------------------------------------------------------------------------
    def update(self, returns: list[Return], tick: int) -> None:
        for r in returns:
            match r:
                case OdometryReturn():
                    self._integrate(r)
                case JunctionReturn():
                    self._arrive(r, tick)
                case ShaftFixReturn():
                    self._fix(r, tick)
                case CargoReturn():
                    if r.count != self.cargo:
                        if r.count > self.cargo:
                            self.cargo_at = self.current
                        self.cargo = r.count
                        self.log.append((tick, f"cargo now {self.cargo}"))

    def _integrate(self, r: OdometryReturn) -> None:
        self.theta = G.wrap(self.theta + r.turn)
        self.x += math.cos(self.theta) * r.forward
        self.y += math.sin(self.theta) * r.forward
        self.dist_since_fix += r.forward
        self.dist_total += r.forward
        self.sigma_theta += T.EST_SIGMA_HEADING_RAD_PER_CELL * r.forward
        if r.forward > 0.0 and math.dist((self.x, self.y), self.trail[-1]) > 0.5:
            self.trail.append((self.x, self.y))

    def _arrive(self, r: JunctionReturn, tick: int) -> None:
        """The agent has stopped: work out which believed node this is."""
        observed = sorted(r.bearings_body, reverse=True)      # left-most first
        if self.current is None and self.walking is None:
            # the start: standing at the shaft, every mouth is onward
            node = JunctionNode(id=0, parent=None, depth=0, back_bearing=None, x=self.x, y=self.y)
            node.passages = [SeenPassage(i, G.wrap(self.theta + b)) for i, b in enumerate(observed)]
            self.nodes[node.id] = node
            self.shaft = node.id
            self.current = node.id
            return
        assert self.walking is not None
        frm, index = self.walking
        if index is None:
            self.current = self.nodes[frm].parent
        else:
            passage = self.nodes[frm].passages[index]
            passage.walked = True
            if self._snap_to_shaft:
                # It led home, which is nowhere to explore: walked, far end unknown,
                # and so exhausted. Pointing it at the shaft would put a cycle in
                # the graph the exhaustion walk recurses over.
                passage.far = None
            elif passage.far is None:
                passage.far = self._new_node(frm, observed).id
            self.current = passage.far
        if self._snap_to_shaft:
            # The beacon said we were home, whatever the route said.
            self.current = self.shaft
        self._snap_to_shaft = False
        self.walking = None
        self.log.append((tick, f"at believed node {self.current}"))

    def _new_node(self, frm: int, observed: list[float]) -> JunctionNode:
        """A node never stood at before. The mouth behind us is the way in; the rest
        are onward, left-most first."""
        incoming = min(range(len(observed)), key=lambda i: G.angle_between(observed[i], math.pi))
        onward = [b for i, b in enumerate(observed) if i != incoming]
        parent = self.nodes[frm]
        node = JunctionNode(id=len(self.nodes), parent=frm, depth=parent.depth + 1,
                            back_bearing=G.wrap(self.theta + math.pi), x=self.x, y=self.y)
        node.passages = [SeenPassage(i, G.wrap(self.theta + b)) for i, b in enumerate(onward)]
        self.nodes[node.id] = node
        return node

    def _fix(self, r: ShaftFixReturn, tick: int) -> None:
        """The shaft answered: position and heading collapse onto the survey."""
        self.theta = r.heading_ref
        self.x = 0.0 - math.cos(self.theta + r.bearing_body) * r.range
        self.y = 0.0 - math.sin(self.theta + r.bearing_body) * r.range
        self.dist_since_fix = 0.0
        self.sigma_theta = T.EST_HEADING_SIGMA_AFTER_FIX
        self.fixes += 1
        self.fixed_here = True
        if self.walking is not None:
            self._snap_to_shaft = True
        self.log.append((tick, "shaft fix"))

    # ---- what the motor tells us -----------------------------------------------------------
    def note_walk_branch(self, passage: SeenPassage) -> None:
        assert self.current is not None
        self.walking = (self.current, passage.index)
        self.current = None
        self.fixed_here = False

    def note_walk_back(self) -> None:
        assert self.current is not None
        self.walking = (self.current, None)
        self.current = None
        self.fixed_here = False

    # ---- what a predicate or motor asks ---------------------------------------------------------
    def current_node(self) -> JunctionNode:
        assert self.current is not None, "not stopped"
        return self.nodes[self.current]

    def at_shaft(self) -> bool:
        return self.current == self.shaft

    def route_back(self) -> list[int]:
        """Believed node ids from the current node up to the shaft, current excluded."""
        out: list[int] = []
        node = self.current_node()
        while node.parent is not None:
            out.append(node.parent)
            node = self.nodes[node.parent]
        return out

    def exhausted(self, passage: SeenPassage, _seen: frozenset[int] = frozenset()) -> bool:
        """Walked, and nothing beyond it is left to walk."""
        if not passage.walked:
            return False
        if passage.far is None or passage.far in _seen:
            return True
        below = _seen | {passage.far}
        return all(self.exhausted(p, below) for p in self.nodes[passage.far].passages)

    def unexplored_here(self) -> list[SeenPassage]:
        """Onward passages at the current believed junction not yet exhausted,
        left-most first. Candidates are this junction's mouths only; whether one
        is exhausted is read from the believed subtree beyond it. See the note at
        the head of this module for why, and what it costs."""
        return [p for p in self.current_node().passages if not self.exhausted(p)]
