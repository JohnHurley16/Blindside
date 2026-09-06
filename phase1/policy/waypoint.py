"""One point on a route, in the belief frame."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Waypoint:
    """A place the agent is trying to get to.

    These are believed coordinates. As the pose estimate drifts, arriving at a
    waypoint stops meaning arriving at the place it names -- which is how an agent
    ends up loading cargo from bare rock, or waiting for pickup in open cave.
    """
    x: float
    y: float
    label: str

    def nudge(self, dx: float, dy: float) -> None:
        self.x += dx
        self.y += dy
