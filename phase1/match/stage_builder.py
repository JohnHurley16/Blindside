"""Reads World, returns a StageFrame. The only new module that imports truth.

This module reads ground truth, which is why it lives in `match` and not in `view`.
`phase2/match/reveal_builder.py` states the same thing in its own docstring and for the
same reason: a truth reader that lives beside the renderer is one import away from
being read by the renderer.

It cannot import `belief` or `policy` -- `match/invariant.py` rule 6 proves it -- so it
can never become a fusion point. Everything it needs from the belief side arrives as
plain floats that `Sim` passes in, because `Sim` may see both and always could.
"""
from __future__ import annotations

import heapq
import math

import numpy as np

from .. import tuning as T
from ..truth import cave
from ..truth.agent_truth import AgentTruth
from ..truth.world import World
from .stage_frame import (
    StageAncient,
    StageBeacon,
    StageDeposit,
    StageFrame,
    StageMachine,
    StageSound,
)

Trail = dict[str, list[tuple[float, float, float]]]

_EMPTY_TRAIL: np.ndarray = np.zeros((0, 3), dtype=np.float64)
_EMPTY_TRAIL.flags.writeable = False


def _frozen(array: np.ndarray) -> np.ndarray:
    """A copy that cannot be written through.

    A frozen dataclass stops a field being rebound; it does nothing about mutation
    *through* one, and a numpy view onto `cave.GRID` handed to the renderer would be a
    live write path back into World.
    """
    out = np.array(array, copy=True)
    out.flags.writeable = False
    return out


class StageBuilder:
    """Builds the frame. Two fields are built once and cached: the grid copy, which is
    constant, and the walking-time-home field, which is a Dijkstra over WALKABLE."""

    _grid: np.ndarray | None = None
    _home_cells: np.ndarray | None = None

    # ---- cached, constant ------------------------------------------------------------
    @classmethod
    def _grid_copy(cls) -> np.ndarray:
        if cls._grid is None:
            cls._grid = _frozen(cave.GRID)
        return cls._grid

    @classmethod
    def _home_field(cls) -> np.ndarray:
        """Walking distance in cells from the player's shaft to every walkable cell.

        Eight-connected Dijkstra over 3,371 cells; measured at 0.008 s and built once,
        inside the warm-up. It is what makes the game's one command expire: against the
        clock it says when Recall provably cannot get the machine home before 8:00.
        """
        if cls._home_cells is not None:
            return cls._home_cells
        walkable = cave.WALKABLE
        dist = np.full(walkable.shape, np.inf, dtype=np.float64)
        sx, sy = cave.SHAFTS["player"]
        start = (int(sy), int(sx))
        dist[start] = 0.0
        queue: list[tuple[float, int, int]] = [(0.0, start[0], start[1])]
        diag = math.sqrt(2.0)
        steps = ((-1, 0, 1.0), (1, 0, 1.0), (0, -1, 1.0), (0, 1, 1.0),
                 (-1, -1, diag), (-1, 1, diag), (1, -1, diag), (1, 1, diag))
        height, width = walkable.shape
        while queue:
            d, y, x = heapq.heappop(queue)
            if d > dist[y, x]:
                continue
            for dy, dx, cost in steps:
                ny, nx = y + dy, x + dx
                if not (0 <= ny < height and 0 <= nx < width) or not walkable[ny, nx]:
                    continue
                nd = d + cost
                if nd < dist[ny, nx]:
                    dist[ny, nx] = nd
                    heapq.heappush(queue, (nd, ny, nx))
        cls._home_cells = _frozen(dist)
        return cls._home_cells

    # ---- per frame -------------------------------------------------------------------
    @classmethod
    def of(cls, world: World, trail: Trail, t: float, spoof_arming: float,
           believed: tuple[float, float, float],
           error_history: list[tuple[float, float, float]]) -> StageFrame:
        """`believed` is the player's estimated (x, y, heading) as three floats, and
        `error_history` a list of (t, error, sigma) triples. Both come from `Sim`,
        which may see Belief; this module may not."""
        grid = cls._grid_copy()
        player = world.agents["player"]
        rival = world.agents["rival"]
        bx, by, btheta = believed

        ancient = world.ancient
        moved = cls._relocations(world)
        beacons = tuple(
            StageBeacon(float(b.x), float(b.y), b.owner, moved.get(bid))
            for bid, b in world.beacons.items())

        home = cls._home_field()
        cell = home[min(max(int(player.y), 0), home.shape[0] - 1),
                    min(max(int(player.x), 0), home.shape[1] - 1)]
        seconds_home = float(cell / T.AGENT_SPEED) if np.isfinite(cell) else float("inf")

        history = (_frozen(np.asarray(error_history, dtype=np.float64))
                   if error_history else _frozen(np.zeros((0, 3), dtype=np.float64)))

        return StageFrame(
            t=float(t),
            grid=grid,
            player=cls._machine(world, player, trail),
            rival=cls._machine(world, rival, trail),
            trail_player=cls._trail(trail, "player"),
            trail_rival=cls._trail(trail, "rival"),
            beacons=beacons,
            ancient=StageAncient(float(ancient.x), float(ancient.y), float(T.ANCIENT_RADIUS),
                                 float(ancient.signature_strength(t)),
                                 float(ancient.seconds_until_lethal(t)),
                                 bool(ancient.is_lethal(t))),
            deposits=tuple(StageDeposit(float(dx), float(dy), float(T.DEPOSIT_RADIUS))
                           for dx, dy in world.deposits.values()),
            born=cls._born(world, t),
            error_cells=float(math.hypot(player.x - bx, player.y - by)),
            heading_error_deg=float(math.degrees(
                (btheta - player.heading + math.pi) % (2 * math.pi) - math.pi)),
            spoof_arming=float(spoof_arming),
            seconds_home=seconds_home,
            error_history=history,
        )

    # ---- pieces ----------------------------------------------------------------------
    @staticmethod
    def _relocations(world: World) -> dict[str, tuple[float, float]]:
        """Where each relocated beacon used to be, read off the truth log rather than
        stored on the Beacon: a spoof leaves no mark on the transponder, which is the
        whole point of it, so the only record is the event. One pass over the log per
        frame -- per beacon it was a 700-entry scan twelve times a frame."""
        return {event.data["id"]: (float(event.data["was_x"]), float(event.data["was_y"]))
                for event in world.events if event.kind == "spoof"}

    @classmethod
    def _machine(cls, world: World, agent: AgentTruth, trail: Trail) -> StageMachine:
        return StageMachine(
            x=float(agent.x),
            y=float(agent.y),
            heading=float(agent.heading),
            alive=bool(agent.alive),
            cargo=int(agent.cargo),
            load_progress=float(world.load_progress.get(agent.name, 0.0)),
            stalled_for=cls._stalled_for(trail.get(agent.name, [])),
            in_ancient=bool(agent.in_ancient),
        )

    @staticmethod
    def _stalled_for(path: list[tuple[float, float, float]]) -> float:
        """Seconds since the machine last moved. 6:40.5 to 8:00 is 79.5 seconds where
        truth and belief are both frozen, and on screen that reads as a stopped video
        unless something counts it."""
        if len(path) < 2:
            return 0.0
        lx, ly, lt = path[-1]
        oldest = lt
        for x, y, tt in reversed(path[:-1]):
            if math.hypot(x - lx, y - ly) > T.STALL_MOVE_CELLS:
                break
            oldest = tt
        return float(lt - oldest)

    @staticmethod
    def _trail(trail: Trail, name: str) -> np.ndarray:
        path = trail.get(name)
        if not path:
            return _EMPTY_TRAIL
        return _frozen(np.asarray(path, dtype=np.float64))

    @staticmethod
    def _born(world: World, t: float) -> tuple[StageSound, ...]:
        """Sounds that came into existence this tick, at their true origin. Pings are
        logged rather than queued, so both sources are read."""
        half = T.DT * 0.5
        out: list[StageSound] = [
            StageSound(float(s.x), float(s.y), str(s.character.value))
            for s in world.pending_sounds if abs(s.t - t) <= half]
        for event in reversed(world.events):
            if event.t < t - T.DT:
                break
            if event.kind == "ping":
                out.append(StageSound(float(event.data["x"]), float(event.data["y"]), "ping"))
        return tuple(out)
