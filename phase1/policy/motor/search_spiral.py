"""The search that can undo a lie."""
from __future__ import annotations

import math

from ... import geometry as G
from ... import tuning as T
from ...belief.belief import Belief
from ...motor_command import MotorCommand
from ..decision_node import DecisionNode
from .driver import Driver


class SearchSpiral:
    """At the believed shaft with nothing answering, spiral outward.

    This is the only behaviour in the match that can recover from a corrupted pose
    estimate, because widening the circle far enough eventually brings the agent
    inside the real shaft transponder's range -- and that one is survey placed, so
    its fix is the truth. It is the tail of `return_to_beacon` and of Recall, and not
    a block: at a silent shaft there is nothing else sane to do (CAVE-BLOCKS.md 4).
    """

    def __init__(self, belief: Belief, driver: Driver, t: float) -> None:
        """Start the widening circle, and say honestly which of the two reasons it is.

        Arriving where the shaft should be and hearing nothing is one story. Giving up
        on ever getting there and searching from wherever the rock stopped it is a
        different one, and the feed should not report the second as the first.
        """
        self.b: Belief = belief
        self.driver: Driver = driver
        hx, hy = belief.known_places["HOME"]
        arrived = G.dist(belief.x, belief.y, hx, hy) < T.HOME_REACHED
        belief.log.append((t, "at the shaft, but nothing is answering" if arrived
                           else "cannot get to the shaft; searching from here"))
        self.t0: float = t
        self.angle: float = 0.0
        self.dist0: float = belief.dist_total
        # The circle to widen is the one around the place it believes home to be, even
        # -- especially -- when it never got there. Centred on wherever the rock
        # stopped it, the spiral swept empty cave fifty-six cells off target and the
        # shaft stayed 55-80 true cells away for the rest of the match, in all eight
        # seeds. The true shaft is exactly one pose error from the believed one, so
        # that is the only centre from which widening can ever reach it.
        self.cx, self.cy = (belief.x, belief.y) if arrived else (hx, hy)

    @property
    def radius(self) -> float:
        return 4.0 + T.RECALL_SEARCH_PITCH * self.angle

    def step(self, t: float) -> MotorCommand:
        b, d = self.b, self.driver
        cmd = MotorCommand(heading=b.theta)
        # An Archimedean spiral sized so each loop steps outward by less than the width
        # it can detect the shaft across -- otherwise it can circle straight past the
        # thing it is looking for. The angle advances with ground actually covered, so
        # the whole search really is something the agent can walk. On a clock, which is
        # what it used to be, the target walked the spiral at nominal speed whether or
        # not the agent could follow, and in a cave it cannot: measured, the target ran
        # 20-47 cells ahead and the "search" was a point orbiting forty cells away being
        # chased.
        radius = self.radius
        self.angle += (b.dist_total - self.dist0) / radius
        self.dist0 = b.dist_total
        target_x = self.cx + math.cos(self.angle) * radius
        target_y = self.cy + math.sin(self.angle) * radius
        goal = math.atan2(target_y - b.y, target_x - b.x)
        # The search gets the same way out of a jam that travelling does. Without it the
        # spiral had no escape at all: measured on seed 7, a recalled agent stood at one
        # spot from 6:00 to 7:30 with the target rotating in front of it, because
        # `_steer` only looks 150 degrees either side of the goal and the way out was
        # behind it.
        if d.jammed(t):
            d.break_jam(t)
        elif t >= d.escape_until and d.failed_escapes:
            d.failed_escapes.clear()         # moving again; nothing is ruled out
        if t < d.escape_until:
            goal = d.escape_heading_for(goal)
        heading, free_ahead = d.steer(goal)
        cmd.heading = heading
        cmd.speed = T.AGENT_SPEED * (0.5 if free_ahead < 1.3 else 1.0)
        cmd.ping = d.wants_ping()
        return cmd

    def nodes(self) -> list[DecisionNode]:
        spread = self.radius
        return [DecisionNode("act.search", "SEARCH FOR THE SHAFT", "action",
                             active=True, fired=True),
                DecisionNode("act.search.spiral", "widening the circle", "sub",
                             detail=f"{spread:.0f} cells out",
                             fill=min(spread / 60.0, 1.0), active=True)]
