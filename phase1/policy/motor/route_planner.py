"""Shortest routes over the survey map, from wherever belief says the agent is."""
from __future__ import annotations

import heapq
import math

from ... import tuning as T
from ...belief.survey_map import SurveyMap
from ..waypoint import Waypoint
from ..waypoint_kind import WaypointKind


class RoutePlanner:
    """Dijkstra over the survey's chambers and dry passages.

    Replaces the hand-authored survey routes, which were the policy leaking into the
    engine: a player cannot teach "go to B after A" if B-after-A is a constant. The
    machinery's chamber is kept out of every route unless it is the destination
    (CAVE-BLOCKS.md guess 7): without that rule the shortest intel path from C3 to
    deposit B runs through the Assayer's chamber, and the cautious tree would walk
    the player into the machine on day one.

    The route joins the graph at the believed nearest chamber, or at the far end of
    the passage the agent is believed to be in -- a survey neighbour of the nearest
    chamber whose passage runs within PASSAGE_JOIN_CELLS of the believed position --
    when straight line to it plus path from it is shorter, so an agent mid-passage
    carries on rather than walking back. Only those candidates, and never the avoided
    ground unless it is the goal or the agent is standing in it: measured with every
    chamber allowed, the straight line to the goal itself always won, and the first
    route after deposit A was one waypoint, deposit B, through eighty cells of rock;
    with every neighbour allowed, a route from C3 joined at the Assayer's chamber. The
    survey has no notion of a passage's interior, so the join rule is this file's own
    guess.
    """

    def __init__(self, survey: SurveyMap) -> None:
        self.survey: SurveyMap = survey

    def distances_to(self, goal: str) -> dict[str, float]:
        """Path length from every place to `goal`, avoiding the avoided ground except
        as the goal itself (or as the start: the agent may already be standing in it)."""
        survey = self.survey
        dist: dict[str, float] = {goal: 0.0}
        queue: list[tuple[float, str]] = [(0.0, goal)]
        while queue:
            d, place = heapq.heappop(queue)
            if d > dist.get(place, math.inf):
                continue
            for other, length in survey.neighbours(place):
                if place in survey.avoided and place != goal:
                    continue          # never pass through it, only start or end there
                nd = d + length
                if nd < dist.get(other, math.inf):
                    dist[other] = nd
                    heapq.heappush(queue, (nd, other))
        return dist

    def cost(self, x: float, y: float, goal: str) -> float | None:
        """Straight line to the best joining place plus the path from it, or None
        when the goal cannot be reached over the survey."""
        best = self._join(x, y, goal)
        return None if best is None else best[1]

    def route(self, x: float, y: float, goal: str) -> list[Waypoint] | None:
        """The waypoints to walk, the joining place first unless already there."""
        best = self._join(x, y, goal)
        if best is None:
            return None
        start, _ = best
        dist = self.distances_to(goal)
        survey = self.survey
        names = [start]
        while names[-1] != goal:
            here = names[-1]
            nxt = min((other for other, _ in survey.neighbours(here)
                       if other in dist and not (other in survey.avoided and other != goal)),
                      key=lambda o: dist[o] + self._length(here, o))
            names.append(nxt)
        sx, sy = survey.positions[start]
        if len(names) > 1 and math.hypot(sx - x, sy - y) < T.WAYPOINT_REACHED:
            names = names[1:]
        return [Waypoint(*survey.positions[n], n, WaypointKind.PLACE) for n in names]

    def _length(self, a: str, b: str) -> float:
        for other, length in self.survey.neighbours(a):
            if other == b:
                return length
        return math.inf

    def _join(self, x: float, y: float, goal: str) -> tuple[str, float] | None:
        survey = self.survey
        dist = self.distances_to(goal)
        nearest = survey.nearest(x, y)
        candidates = [nearest] + [
            other for other, _ in survey.neighbours(nearest)
            if not (other in survey.avoided and other != goal)
            and self._on_passage(x, y, nearest, other)]
        best: tuple[str, float] | None = None
        for place in candidates:
            if place not in dist:
                continue
            px, py = self.survey.positions[place]
            total = math.hypot(px - x, py - y) + dist[place]
            if best is None or total < best[1]:
                best = (place, total)
        return best

    def _on_passage(self, x: float, y: float, a: str, b: str) -> bool:
        """Is the believed position within PASSAGE_JOIN_CELLS of the survey's straight
        line from a to b? That is as much as the survey knows about a passage."""
        (ax, ay), (bx, by) = self.survey.positions[a], self.survey.positions[b]
        dx, dy = bx - ax, by - ay
        length_sq = dx * dx + dy * dy
        f = 0.0 if length_sq == 0.0 else max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / length_sq))
        return math.hypot(x - (ax + f * dx), y - (ay + f * dy)) < T.PASSAGE_JOIN_CELLS
