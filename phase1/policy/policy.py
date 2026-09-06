"""A hand-written scripted policy. Reads Belief only; never imports truth.

Two instances exist in Phase 1 and they differ mostly in two numbers: how often
they ping, and how much uncertainty they will tolerate before turning for home.
"""
from __future__ import annotations

import math

from .. import geometry as G
from .. import tuning as T
from ..belief.belief import Belief
from ..motor_command import MotorCommand
from ..sound_character import SoundCharacter
from .decision_node import DecisionNode
from .policy_mode import PolicyMode
from .waypoint import Waypoint


class Policy:
    def __init__(self, belief: Belief, routes: dict[str, list[str]], cautious: bool,
                 shaft_beacon_id: str) -> None:
        self.b: Belief = belief
        self.routes: dict[str, list[str]] = routes
        self.cautious: bool = cautious
        self.shaft_beacon_id: str = shaft_beacon_id
        self.mode: PolicyMode = PolicyMode.TRAVEL
        self.route: list[Waypoint] = []
        self.i: int = 0
        self.stage: int = 0
        self.done: bool = False
        self.recalled: bool = False
        self.hold: bool = False
        # load bookkeeping
        self.load_until: float = 0.0
        self.cargo_at_load: int = 0
        self.load_attempts: int = 0
        # stuck detection
        self.best_dist: float = 1e9
        self.best_t: float = 0.0
        self.escapes: int = 0
        self.escape_until: float = 0.0
        self.escape_heading: float | None = None
        # search
        self.search_t0: float = 0.0
        self.search_x: float = 0.0
        self.search_y: float = 0.0

    # ---- routes ---------------------------------------------------------------------
    def set_route(self, names: list[str], t: float) -> None:
        self.route = [Waypoint(*self.b.known_places[n], n) for n in names]
        self.i = 0
        self.best_dist = 1e9
        self.best_t = t
        self.mode = PolicyMode.TRAVEL

    def set_beacon_chain_home(self, t: float) -> None:
        """Retrace the believed beacon chain in reverse, then the believed shaft."""
        self.route = [Waypoint(self.b.beacons[bid].x, self.b.beacons[bid].y, bid)
                      for bid in reversed(self.b.beacon_order)]
        sx, sy = self.b.known_places["HOME"]
        self.route.append(Waypoint(sx, sy, "HOME"))
        self.i = 0
        self.best_dist = 1e9
        self.best_t = t
        self.mode = PolicyMode.HOME

    def recall(self, t: float) -> None:
        """Abort to the nearest shaft. Blunt on purpose.

        Not the beacon chain: the agent's own uncertainty return retraces the chain,
        which is the careful thing to do and which, once the pose estimate is
        corrupted, walks it into wall after wall without ever arriving. Recall drives
        straight at the shaft it believes in, and when the shaft is not there it
        starts searching -- and the search is the only thing in the match that can
        undo a lie. That difference is what the player is actually buying.
        """
        if self.recalled or self.done:
            return
        self.recalled = True
        self.b.log.append((t, "RECALL received"))
        sx, sy = self.b.known_places["HOME"]
        self.route = [Waypoint(sx, sy, "HOME")]
        self.i = 0
        self.best_dist = 1e9
        self.best_t = t
        self.escapes = 0
        self.mode = PolicyMode.HOME

    def decision_report(self, t: float) -> list[DecisionNode]:
        """The policy as a graph of tests and actions, with live values.

        Read from Belief only. This is the Phase 1 stand-in for the execution trace
        Phase 4 captures from the behaviour-tree VM -- which nodes fired, on what
        predicate values -- and it is what lets the display show the machine deciding
        rather than only the result of a decision.
        """
        b = self.b
        nodes: list[DecisionNode] = [
            DecisionNode("root", self._root_text(), kind="action", active=True, fired=True)
        ]

        # test: is it getting lost? the bar is how close the ellipse is to the limit
        sigma = b.sigma_pos()
        limit = T.CAUTIOUS_RETURN_SIGMA
        lost = self.mode is PolicyMode.HOME and not self.recalled
        nodes.append(DecisionNode(
            "guard.lost", "am I getting lost?", "test",
            answer="yes" if lost else "no",
            detail=f"{sigma:.0f} of {limit:.0f} cells adrift",
            fill=min(sigma / limit, 1.0), active=True, fired=lost))

        # test: can it hear the machinery?
        sig = b.signature
        strength = sig.quality if (sig is not None and t - sig.t < 1.5) else 0.0
        nodes.append(DecisionNode(
            "guard.machinery", "can I hear machinery?", "test",
            answer="yes" if self.hold else "no",
            detail="holding still" if self.hold else (
                "faint" if strength > 0 else "nothing"),
            fill=min(strength / max(T.ANCIENT_HOLD_QUALITY, 1e-6), 1.0),
            active=not lost, fired=self.hold))

        # test: has it arrived at whatever it is making for?
        if self.route and self.i < len(self.route):
            wp = self.route[self.i]
            gap = G.dist(b.x, b.y, wp.x, wp.y)
            reach = self._reach_radius(wp)
            close = max(0.0, 1.0 - min(gap / 60.0, 1.0))
            detail = f"{gap:.0f} cells to go"
        else:
            gap, reach, close, detail = 0.0, 1.0, 1.0, "nowhere to go"
        arrived = self.mode in (PolicyMode.LOAD, PolicyMode.SEARCH) or self.done
        nodes.append(DecisionNode(
            "guard.arrived", "have I got there yet?", "test",
            answer="yes" if arrived else "no", detail=detail, fill=close,
            active=not lost and not self.hold, fired=arrived))

        nodes.extend(self._action_nodes(t))
        return nodes

    def _root_text(self) -> str:
        if self.done:
            return "IT THINKS IT IS HOME"
        if self.recalled:
            return "RECALLED"
        if self.mode is PolicyMode.HOME:
            return "TURNING BACK"
        return "RUNNING THE SURVEY"

    def _action_nodes(self, t: float) -> list[DecisionNode]:
        b = self.b
        if self.done:
            return [DecisionNode("act.done", "WAIT TO BE COLLECTED", "action",
                                 active=True, fired=True)]
        if self.mode is PolicyMode.LOAD:
            left = max(0.0, self.load_until - t)
            return [DecisionNode("act.load", "LOAD CARGO", "action", active=True, fired=True),
                    DecisionNode("act.load.wait", "filling up", "sub",
                                 detail=f"{left:.0f}s left",
                                 fill=1.0 - left / max(T.LOAD_SECONDS, 1e-6), active=True)]
        if self.mode is PolicyMode.SEARCH:
            spread = (t - self.search_t0) * T.RECALL_SEARCH_RADIUS_RATE
            return [DecisionNode("act.search", "SEARCH FOR THE SHAFT", "action",
                                 active=True, fired=True),
                    DecisionNode("act.search.spiral", "widening the circle", "sub",
                                 detail=f"{spread:.0f} cells out",
                                 fill=min(spread / 60.0, 1.0), active=True)]
        if self.hold:
            return [DecisionNode("act.hold", "FREEZE UNTIL IT PASSES", "action",
                                 active=True, fired=True)]

        target = "nothing"
        if self.route and self.i < len(self.route):
            target = self.route[self.i].label
        drive = DecisionNode("act.drive", "DRIVE TO", "action",
                             active=True, fired=True, target=target)
        escaping = self.escape_heading is not None and t < self.escape_until
        subs = [
            DecisionNode("act.drive.steer",
                         "following the wall out" if escaping else "steering round what it feels",
                         "sub", detail="stuck" if escaping else "", active=True),
            DecisionNode("act.drive.beacon", "drop a beacon", "sub",
                         detail=f"{b.dist_since_drop:.0f} of {T.BEACON_DROP_EVERY_CELLS:.0f} cells",
                         fill=min(b.dist_since_drop / T.BEACON_DROP_EVERY_CELLS, 1.0),
                         active=True),
        ]
        cooldown = T.CAUTIOUS_PING_COOLDOWN_S if self.cautious else T.AGGRESSIVE_PING_COOLDOWN_S
        since = b.ticks_since_ping * T.DT
        subs.append(DecisionNode("act.drive.ping", "ping", "sub",
                                 detail=f"{min(since, cooldown):.0f} of {cooldown:.0f}s",
                                 fill=min(since / cooldown, 1.0), active=True))
        return [drive, *subs]

    def heard_shaft(self) -> bool:
        """Has the survey-placed transponder actually answered? Belief knows this."""
        return any(f.beacon_id == self.shaft_beacon_id for f in self.b.fixes[-4:])

    # ---- per tick -------------------------------------------------------------------
    def step(self, t: float) -> MotorCommand:
        b = self.b
        cmd = MotorCommand(heading=b.theta)
        if self.done:
            return cmd
        if self.mode is PolicyMode.LOAD:
            cmd.load = True
            if t >= self.load_until:
                self._after_load(t)
            return cmd
        if self.mode is PolicyMode.SEARCH:
            return self._search(t)
        if not self.route:
            self._plan(t)
            if not self.route:
                self.done = True
                return cmd

        sig = b.signature
        self.hold = bool(self.cautious and sig is not None
                         and sig.character is SoundCharacter.SIGNATURE
                         and t - sig.t < 1.0
                         and sig.quality >= T.ANCIENT_HOLD_QUALITY)

        if (self.cautious and self.mode is PolicyMode.TRAVEL and not self.recalled
                and b.sigma_pos() > T.CAUTIOUS_RETURN_SIGMA):
            b.log.append((t, f"uncertainty {b.sigma_pos():.1f} > {T.CAUTIOUS_RETURN_SIGMA}: heading home"))
            self.set_beacon_chain_home(t)

        goal_wp = self.route[self.i]
        dist = G.dist(b.x, b.y, goal_wp.x, goal_wp.y)
        reached = self._reach_radius(goal_wp)
        if dist < reached:
            self._arrived(goal_wp, t)
            return cmd
        self._track_progress(dist, goal_wp, t)

        goal = math.atan2(goal_wp.y - b.y, goal_wp.x - b.x)
        if t < self.escape_until:
            goal = self._escape_heading(goal)
        heading, free_ahead = self._steer(goal)
        cmd.heading = heading
        slow = free_ahead < 1.3 or G.angle_between(heading, b.theta) > math.radians(60.0)
        base = T.AGENT_SPEED if self.cautious else T.RIVAL_SPEED
        cmd.speed = 0.0 if self.hold else base * (0.5 if slow else 1.0)

        if self.mode is PolicyMode.TRAVEL and b.dist_since_drop >= T.BEACON_DROP_EVERY_CELLS:
            cmd.drop = True
        cmd.ping = self._wants_ping()
        return cmd

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
        b = self.b
        hits = self._near_hits()
        best, best_score, best_free = b.theta, -1e9, T.NEARFIELD_RANGE
        for k in range(-10, 11):
            cand = G.wrap(goal + k * math.radians(15.0))
            free = self._clearance(cand, hits, 28.0)
            score = math.cos(G.wrap(cand - goal)) + 0.9 * free / T.NEARFIELD_RANGE
            if free < 0.9:
                score -= 3.0
            score += 0.15 * math.cos(G.wrap(cand - b.theta))    # hysteresis
            if score > best_score:
                best, best_score, best_free = cand, score, free
        return best, best_free

    def _escape_heading(self, goal: float) -> float:
        if self.escape_heading is not None:
            return self.escape_heading
        b = self.b
        hits = self._near_hits()
        best, best_free = b.theta, -1.0
        for k in range(24):
            cand = G.wrap(k * math.pi / 12.0)
            free = self._clearance(cand, hits, 30.0)
            free += 0.3 * math.cos(G.wrap(cand - goal))
            free -= 0.6 * max(0.0, -math.cos(G.wrap(cand - b.theta)))
            if free > best_free:
                best, best_free = cand, free
        self.escape_heading = best
        return best

    def _track_progress(self, dist: float, wp: Waypoint, t: float) -> None:
        if dist < self.best_dist - 1.0:
            self.best_dist = dist
            self.best_t = t
            self.escapes = 0
        elif t - self.best_t > T.STUCK_SECONDS and t >= self.escape_until:
            self.escapes += 1
            if self.escapes > T.ESCAPES_BEFORE_SKIP:
                self.b.log.append((t, f"cannot reach {wp.label}; skipping"))
                self.escapes = 0
                self._advance(t)
                return
            self.escape_until = t + T.ESCAPE_SECONDS
            self.escape_heading = None
            self.best_t = t
            self.b.log.append((t, f"no progress toward {wp.label}; wall escape {self.escapes}"))

    def _reach_radius(self, wp: Waypoint) -> float:
        if wp.label in ("HOME", "S"):
            return T.HOME_REACHED
        if self.mode is PolicyMode.HOME:
            return T.RECALL_BEACON_REACHED
        return T.WAYPOINT_REACHED

    def _wants_ping(self) -> bool:
        b = self.b
        cooldown = T.CAUTIOUS_PING_COOLDOWN_S if self.cautious else T.AGGRESSIVE_PING_COOLDOWN_S
        if b.ticks_since_ping * T.DT < cooldown or self.hold:
            return False
        if self.cautious and T.PING_ONLY_IF_UNMAPPED_AHEAD:
            return b.points_ahead() < T.MIN_POINTS_AHEAD
        return True

    # ---- the search that can undo a lie -------------------------------------------------
    def _search(self, t: float) -> MotorCommand:
        """At the believed shaft with nothing answering, spiral outward.

        This is the only behaviour in the match that can recover from a corrupted
        pose estimate, because widening the circle far enough eventually brings the
        agent inside the real shaft transponder's range -- and that one is survey
        placed, so its fix is the truth. It is also the reason Recall is worth
        holding: without the command the agent simply waits to be collected at a
        place where there is no shaft.
        """
        b = self.b
        cmd = MotorCommand(heading=b.theta)
        if self.heard_shaft():
            b.log.append((t, "shaft acquired"))
            self.done = True
            return cmd
        elapsed = t - self.search_t0
        radius = T.RECALL_SEARCH_RADIUS_RATE * elapsed
        angle = elapsed * T.RECALL_SEARCH_SWEEP
        target_x = self.search_x + math.cos(angle) * radius
        target_y = self.search_y + math.sin(angle) * radius
        goal = math.atan2(target_y - b.y, target_x - b.x)
        heading, free_ahead = self._steer(goal)
        cmd.heading = heading
        cmd.speed = T.AGENT_SPEED * (0.5 if free_ahead < 1.3 else 1.0)
        cmd.ping = self._wants_ping()
        return cmd

    # ---- arrival ---------------------------------------------------------------------
    def _arrived(self, wp: Waypoint, t: float) -> None:
        b = self.b
        if wp.label in ("DA", "DB"):
            b.log.append((t, f"at {wp.label}, loading"))
            self.cargo_at_load = b.cargo
            self.mode = PolicyMode.LOAD
            self.load_until = t + T.LOAD_SECONDS
            return
        if wp.label in ("HOME", "S"):
            if self.heard_shaft():
                b.log.append((t, "at the shaft"))
                self.done = True
                self.route = []
            else:
                b.log.append((t, "at the shaft, but nothing is answering"))
                self.mode = PolicyMode.SEARCH
                self.search_t0 = t
                self.search_x, self.search_y = b.x, b.y
            return
        self._advance(t)

    def _after_load(self, t: float) -> None:
        """Discover through the cargo return whether the load actually happened."""
        b = self.b
        wp = self.route[self.i]
        if b.cargo > self.cargo_at_load:
            self.load_attempts = 0
            self._resume_after_load(t)
            return
        self.load_attempts += 1
        if self.load_attempts <= T.LOAD_RETRIES:
            b.log.append((t, f"nothing loaded at {wp.label}; it is not where I think it is"))
            angle = float(b.rng.uniform(0.0, 2.0 * math.pi))
            wp.nudge(math.cos(angle) * T.LOAD_SEARCH_STEP, math.sin(angle) * T.LOAD_SEARCH_STEP)
            self.mode = PolicyMode.TRAVEL
            self.best_dist = 1e9
            self.best_t = t
            return
        b.log.append((t, f"giving up on {wp.label}"))
        self.load_attempts = 0
        self._resume_after_load(t)

    def _resume_after_load(self, t: float) -> None:
        if self.i + 1 < len(self.route):
            self._advance(t)
        else:
            self.route = []
            self._plan(t)

    def _advance(self, t: float) -> None:
        self.i += 1
        self.best_dist = 1e9
        self.best_t = t
        self.escapes = 0
        if self.i >= len(self.route):
            self.route = []
            self._plan(t)

    def _plan(self, t: float) -> None:
        b = self.b
        self.stage += 1
        if self.cautious:
            if self.stage == 1:
                self.set_route(self.routes["out_A"], t)
            elif self.stage == 2:
                if b.sigma_pos() < T.CAUTIOUS_RETURN_SIGMA and b.cargo < T.CARGO_CAPACITY:
                    b.log.append((t, f"sigma {b.sigma_pos():.1f}: pushing on to B"))
                    self.set_route(self.routes["A_to_B"], t)
                else:
                    b.log.append((t, "going home from A"))
                    self.set_route(self.routes["home_from_A"], t)
            else:
                b.log.append((t, "going home from B"))
                self.set_route(self.routes["home_from_B"], t)
        else:
            if self.stage == 1:
                self.set_route(self.routes["out"], t)
            else:
                self.set_beacon_chain_home(t)
