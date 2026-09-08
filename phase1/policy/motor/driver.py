"""Waypoint following: steering, wall escape, jam breaking, arrival, ping and drop.

This is the hand-written policy's engine, moved whole. Every number and every
measured note came with it; nothing here decides *where* to go, only how to get to
the next waypoint of a route it was handed, and when to give up on one. Reads Belief
only.
"""
from __future__ import annotations

import math

from ... import geometry as G
from ... import tuning as T
from ...belief.belief import Belief
from ...motor_command import MotorCommand
from ..decision_node import DecisionNode
from ..loadout import Loadout
from ..waypoint import Waypoint
from ..waypoint_kind import WaypointKind
from .body import Body
from .jam_clock import JamClock


class Driver:
    """The body between decisions. One per program, so a suspended program keeps
    its route and its progress and a new one starts clean, as `set_route` always
    started clean."""

    def __init__(self, body: Body) -> None:
        self.b: Belief = body.belief
        self.loadout: Loadout = body.loadout
        self.shaft_beacon_id: str = body.shaft_beacon_id
        self.jam: JamClock = body.jam
        self.route: list[Waypoint] = []
        self.i: int = 0
        # stuck detection
        self.best_dist: float = 1e9
        self.best_t: float = 0.0
        self.escapes: int = 0
        self.escape_until: float = 0.0
        self.escape_heading: float | None = None
        # headings already tried and already failed, for this waypoint only
        self.failed_escapes: list[float] = []

    # ---- routes ---------------------------------------------------------------------
    def set_route(self, route: list[Waypoint], t: float) -> None:
        self.route = list(route)
        self.i = 0
        self.reset_progress(t)

    def reset_progress(self, t: float) -> None:
        self.best_dist = 1e9
        self.best_t = t
        self.failed_escapes.clear()

    def resume(self, t: float) -> None:
        """Back from a suspension: the pause was on purpose, so it is not a stall
        toward the waypoint. (The old policy's stall tracker ran through a freeze, so
        a hold longer than STUCK_SECONDS ended in a wall escape in a direction chosen
        while frozen -- seed 1, rival inert, 3:15.9. Deliberately not reproduced.)"""
        self.best_t = t
        self.jam.reset(t)

    @property
    def finished(self) -> bool:
        return self.i >= len(self.route)

    def target(self) -> Waypoint | None:
        return self.route[self.i] if not self.finished else None

    def advance(self, t: float) -> None:
        self.i += 1
        self.best_dist = 1e9
        self.best_t = t
        self.failed_escapes.clear()
        self.escapes = 0

    def heard_shaft(self) -> bool:
        """Has the survey-placed transponder actually answered? Belief knows this."""
        return any(f.beacon_id == self.shaft_beacon_id for f in self.b.fixes[-4:])

    # ---- arrival ---------------------------------------------------------------------
    def reach_radius(self, wp: Waypoint) -> float:
        if wp.kind is WaypointKind.SHAFT:
            return T.HOME_FINAL if self.heard_shaft() else T.HOME_REACHED
        if wp.kind is WaypointKind.BEACON:
            return T.RECALL_BEACON_REACHED
        return T.WAYPOINT_REACHED

    def arrived(self) -> bool:
        wp = self.target()
        if wp is None:
            return False
        return G.dist(self.b.x, self.b.y, wp.x, wp.y) < self.reach_radius(wp)

    # ---- jam: not moving, which is not the same as not arriving -----------------------
    def still_on_purpose(self, t: float) -> None:
        """Standing still to load, to freeze or to dwell is not a jam."""
        self.jam.still(t)

    def jammed(self, t: float) -> bool:
        return self.jam.jammed(t)

    def break_jam(self, t: float) -> None:
        """Pressed against rock: throw away the heading doing it and re-pick, now.

        It must not push `escape_until` out. `_track_progress` escalates only outside
        an escape window, so a jam every 2.5 s that renewed the window pinned the
        agent to one unreachable waypoint for the rest of the match -- measured that
        way, terminal freezes of 195 and 221 s, worse than doing nothing at all.
        """
        self._blame_escape()
        self.escape_heading = None
        if t >= self.escape_until:
            self.escape_until = t + T.ESCAPE_SECONDS
        self.jam.reset(t)

    def _blame_escape(self) -> None:
        """Record the heading that has just failed, so the next pick is a new idea."""
        if self.escape_heading is None:
            return
        self.failed_escapes.append(self.escape_heading)
        del self.failed_escapes[:-T.ESCAPES_REMEMBERED]

    # ---- one tick of driving ------------------------------------------------------------
    def drive(self, t: float, *, goal_override: float | None = None,
              break_jams: bool = True, speed: float | None = None,
              drop: bool = False) -> MotorCommand:
        """Steer toward the current waypoint -- or along `goal_override` -- for one tick.

        `break_jams` is off while an agent is driving at a bearing it chose: it has a
        decision in hand, and "throw the heading away and take the longest open line
        on the map" is precisely the wrong answer to being briefly stopped on the
        way. `speed` overrides the loadout's for the interface creep. `drop` is the
        beacon cadence, outbound only.

        The caller has already checked `arrived`; a skipped waypoint still steers at
        the old target for this one tick, as it always did.
        """
        b = self.b
        cmd = MotorCommand(heading=b.theta)
        goal_wp = self.route[self.i]
        dist = G.dist(b.x, b.y, goal_wp.x, goal_wp.y)
        self._track_progress(dist, goal_wp, t)
        if self.jammed(t) and break_jams:
            self.break_jam(t)

        goal = math.atan2(goal_wp.y - b.y, goal_wp.x - b.x)
        if goal_override is not None:
            goal = goal_override                 # toward the sound, not the waypoint
        if t < self.escape_until:
            goal = self._escape_heading(goal)
        heading, free_ahead = self._steer(goal)
        cmd.heading = heading
        slow = free_ahead < 1.3 or G.angle_between(heading, b.theta) > math.radians(60.0)
        if speed is not None:
            cmd.speed = speed
        else:
            cmd.speed = self.loadout.speed * (0.5 if slow else 1.0)
        if drop and b.dist_since_drop >= T.BEACON_DROP_EVERY_CELLS:
            cmd.drop = True
        cmd.ping = self.wants_ping()
        return cmd

    def _track_progress(self, dist: float, wp: Waypoint, t: float) -> None:
        if dist < self.best_dist - 1.0:
            self.best_dist = dist
            self.best_t = t
            self.escapes = 0
            self.failed_escapes.clear()      # it is moving again; nothing is ruled out
        elif t - self.best_t > T.STUCK_SECONDS and t >= self.escape_until:
            self._blame_escape()             # that one did not work either
            self.escapes += 1
            if self.escapes > T.ESCAPES_BEFORE_SKIP:
                # Abandoned whatever the mode. The recalled case used to reset the
                # counter and keep pushing, and since Recall's route is a single HOME
                # waypoint that was an unbounded fourteen-second loop for the rest of
                # the match -- measured, six to thirty-six repeats per recalled run,
                # every one of fifty-six. Running off the end of a route is the
                # program's to notice, next tick.
                self.b.log.append((t, f"cannot reach {wp.label}; skipping"))
                self.escapes = 0
                self.advance(t)
                return
            self.escape_until = t + T.ESCAPE_SECONDS
            self.escape_heading = None
            self.best_t = t
            self.b.log.append((t, f"no progress toward {wp.label}; wall escape {self.escapes}"))

    # ---- steering --------------------------------------------------------------------
    def _near_hits(self) -> list[tuple[float, float]]:
        b = self.b
        return [(math.atan2(hy - b.y, hx - b.x), G.dist(b.x, b.y, hx, hy))
                for (_, hx, hy) in b.recent_near]

    def _clearance(self, candidate: float, hits: list[tuple[float, float]],
                   cone_deg: float) -> float:
        free = T.NEARFIELD_RANGE
        for angle, d in hits:
            if G.angle_between(angle, candidate) < math.radians(cone_deg):
                free = min(free, d)
        return free

    def _steer(self, goal: float) -> tuple[float, float]:
        """Pick a heading by what it can feel close in and what its map says further out.

        The feeler alone (2.5 cells) was the whole of its steering, which is why a
        machine holding a 26,000-point map still walked into walls like it was blind.
        The map is wrong globally by the drift, but so is the agent, so locally it is
        right -- and locally is all steering needs.
        """
        b = self.b
        hits = self._near_hits()
        best, best_score, best_free = b.theta, -1e9, T.NEARFIELD_RANGE
        for k in range(-10, 11):
            cand = G.wrap(goal + k * math.radians(15.0))
            free = self._clearance(cand, hits, 28.0)
            ahead = b.cloud.clearance(b.x, b.y, cand, T.MAP_LOOKAHEAD)
            score = (math.cos(G.wrap(cand - goal))
                     + 0.9 * free / T.NEARFIELD_RANGE
                     + 0.6 * ahead / T.MAP_LOOKAHEAD)
            if free < 0.9:
                score -= 3.0
            score += 0.15 * math.cos(G.wrap(cand - b.theta))    # hysteresis
            if score > best_score:
                best, best_score, best_free = cand, score, free
        return best, best_free

    def _escape_heading(self, goal: float) -> float:
        """Stuck: find the longest open line on the map, leaning toward the goal.

        In a chamber whose exits are not where the target says they are, the only
        long open line is an exit. Weighting alignment weakly here is deliberate --
        a strong pull toward the goal is what kept it grinding the same wall.

        A heading that has already been tried and already failed is not a new idea.
        Measured before this: seven consecutive escapes on one seed all chose 170-180
        degrees into two cells of rock while 290 stayed open at forty, because the
        inputs had not changed and neither had the answer.
        """
        if self.escape_heading is not None:
            return self.escape_heading
        b = self.b
        hits = self._near_hits()
        best, best_score = b.theta, -1e9
        for k in range(36):
            cand = G.wrap(k * math.pi / 18.0)
            near = self._clearance(cand, hits, 30.0)
            far = b.cloud.clearance(b.x, b.y, cand, T.MAP_ESCAPE_LOOKAHEAD)
            score = far / T.MAP_ESCAPE_LOOKAHEAD + 0.4 * near / T.NEARFIELD_RANGE
            score += 0.15 * math.cos(G.wrap(cand - goal))
            score -= 0.5 * max(0.0, -math.cos(G.wrap(cand - b.theta)))
            if near < 0.9:
                score -= 2.0
            if any(G.angle_between(cand, bad) < math.radians(T.ESCAPE_REPEAT_ARC_DEG)
                   for bad in self.failed_escapes):
                score -= 1.5
            if score > best_score:
                best, best_score = cand, score
        self.escape_heading = best
        return best

    def steer(self, goal: float) -> tuple[float, float]:
        """Steering without a waypoint, for the search spiral: the map-aware pick and
        nothing about progress. The escape window is the caller's to apply."""
        return self._steer(goal)

    def escape_heading_for(self, goal: float) -> float:
        return self._escape_heading(goal)

    # ---- ping ---------------------------------------------------------------------------
    def wants_ping(self, silent: bool = False) -> bool:
        b = self.b
        if b.sensor == "lidar":
            # Silent, so there is nothing to be disciplined about: it sweeps on a
            # period, holding still or not. The decision it faces is not "do I emit"
            # but "do I go where this cannot see".
            return b.ticks_since_ping * T.DT >= T.LIDAR_PERIOD_S
        if b.ticks_since_ping * T.DT < self.loadout.ping_cooldown_s or silent:
            return False
        if self.loadout.ping_only_if_unmapped_ahead:
            return b.points_ahead() < T.MIN_POINTS_AHEAD
        return True

    # ---- the graph ------------------------------------------------------------------------
    def nodes(self, t: float, *, drop: bool, target: str | None = None) -> list[DecisionNode]:
        """DRIVE TO and its subs, for the decision graph."""
        b = self.b
        wp = self.target()
        label = target if target is not None else (wp.label if wp is not None else "nothing")
        drive = DecisionNode("act.drive", "DRIVE TO", "action", active=True, fired=True,
                             target=label)
        escaping = self.escape_heading is not None and t < self.escape_until
        subs = [DecisionNode(
            "act.drive.steer",
            "following the wall out" if escaping else "steering round what it feels",
            "sub", detail="stuck" if escaping else "", active=True)]
        if drop:
            subs.append(DecisionNode(
                "act.drive.beacon", "drop a beacon", "sub",
                detail=f"{b.dist_since_drop:.0f} of {T.BEACON_DROP_EVERY_CELLS:.0f} cells",
                fill=min(b.dist_since_drop / T.BEACON_DROP_EVERY_CELLS, 1.0), active=True))
        subs.append(self.ping_node())
        return [drive, *subs]

    def ping_node(self) -> DecisionNode:
        since = self.b.ticks_since_ping * T.DT
        if self.b.sensor == "lidar":
            return DecisionNode("act.drive.ping", "lidar sweep", "sub", detail="silent",
                                fill=min(since / T.LIDAR_PERIOD_S, 1.0), active=True)
        cooldown = self.loadout.ping_cooldown_s
        return DecisionNode("act.drive.ping", "ping", "sub",
                            detail=f"{min(since, cooldown):.0f} of {cooldown:.0f}s",
                            fill=min(since / cooldown, 1.0), active=True)
