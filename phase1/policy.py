"""Scripted policies. Read Belief only. Never import world.

Output per tick: dict(heading=float, speed=float, ping=bool, drop=bool, load=bool).
"""
import math
from . import tuning as T


def _wrap(a):
    return (a + math.pi) % (2 * math.pi) - math.pi


class Policy:
    def __init__(self, belief, routes, cautious):
        self.b = belief
        self.routes = routes
        self.cautious = cautious
        self.mode = "travel"
        self.route = []            # list of (x, y, label)
        self.i = 0
        self.load_until = None
        self.best_dist = 1e9
        self.best_t = 0.0
        self.recalled = False
        self.hold = False
        self.done = False
        self.stage = 0
        self.escape_until = 0.0
        self.escape_heading = None
        self.escapes = 0

    # ---- route handling ------------------------------------------------------------
    def set_route(self, names, t):
        self.route = [(self.b.known_places[n][0], self.b.known_places[n][1], n) for n in names]
        self.i = 0
        self.best_dist = 1e9; self.best_t = t
        self.mode = "travel"

    def set_beacon_chain_home(self, t):
        """Retrace the believed beacon chain in reverse, then the shaft."""
        pts = [(self.b.beacons[bid][0], self.b.beacons[bid][1], bid) for bid in reversed(self.b.beacon_order)]
        sx, sy = self.b.known_places["HOME"]
        pts.append((sx, sy, "HOME"))
        self.route = pts; self.i = 0
        self.best_dist = 1e9; self.best_t = t
        self.mode = "home"

    def recall(self, t):
        if self.recalled or self.done:
            return
        self.recalled = True
        self.b.log.append((t, "RECALL received"))
        self.set_beacon_chain_home(t)

    # ---- per tick ------------------------------------------------------------------
    def step(self, t):
        b = self.b
        cmd = {"heading": b.theta, "speed": 0.0, "ping": False, "drop": False, "load": False}
        if self.done:
            return cmd
        if self.mode == "load":
            cmd["load"] = True
            if t >= self.load_until:
                self._after_load(t)
            return cmd
        if not self.route:
            self._plan(t)
            if not self.route:
                self.done = True
                return cmd
        # cautious: hold while the ancient signature is loud
        sig = b.signature
        self.hold = bool(self.cautious and sig and t - sig["t"] < 1.0 and sig["strength"] >= T.ANCIENT_HOLD_QUALITY)
        # cautious: go home on high uncertainty
        if self.cautious and self.mode == "travel" and not self.recalled and b.sigma_pos() > T.CAUTIOUS_RETURN_SIGMA:
            b.log.append((t, f"uncertainty {b.sigma_pos():.1f} > {T.CAUTIOUS_RETURN_SIGMA}: heading home"))
            self.set_beacon_chain_home(t)
        gx, gy, label = self.route[self.i]
        dist = math.hypot(gx - b.x, gy - b.y)
        if label in ("HOME", "S"):
            reached = T.HOME_REACHED
        elif self.mode == "home":
            reached = T.RECALL_BEACON_REACHED
        else:
            reached = T.WAYPOINT_REACHED
        if dist < reached:
            self._arrived(label, t)
            return cmd
        if dist < self.best_dist - 1.0:
            self.best_dist = dist; self.best_t = t
            if dist < self.best_dist + 3.0:
                self.escapes = 0
        elif t - self.best_t > T.STUCK_SECONDS and t >= self.escape_until:
            self.escapes += 1
            if self.escapes > T.ESCAPES_BEFORE_SKIP:
                b.log.append((t, f"cannot reach {label}; skipping"))
                self.escapes = 0
                self._advance(t)
                return cmd
            self.escape_until = t + T.ESCAPE_SECONDS
            self.escape_heading = None
            self.best_t = t
            b.log.append((t, f"no progress toward {label}; wall escape {self.escapes}"))
        # steering: pick the candidate heading that best trades goal alignment for
        # clearance, judged on recent near-field hits (belief frame)
        goal = math.atan2(gy - b.y, gx - b.x)
        hits = [(math.atan2(hy - b.y, hx - b.x), math.hypot(hx - b.x, hy - b.y)) for (_, hx, hy) in b.recent_near]
        if t < self.escape_until:
            # wall escape: commit to the clearest direction that is not straight back
            if self.escape_heading is None:
                bestc, bestf = b.theta, -1.0
                for k in range(24):
                    cand = _wrap(k * math.pi / 12)
                    free = T.NEARFIELD_RANGE
                    for (ha, hd) in hits:
                        if abs(_wrap(ha - cand)) < math.radians(30):
                            free = min(free, hd)
                    free += 0.3 * math.cos(_wrap(cand - goal)) - 0.6 * max(0.0, -math.cos(_wrap(cand - b.theta)))
                    if free > bestf:
                        bestc, bestf = cand, free
                self.escape_heading = bestc
            goal = self.escape_heading
        best, best_score, free_ahead = b.theta, -1e9, T.NEARFIELD_RANGE
        for k in range(-10, 11):
            cand = _wrap(goal + k * math.radians(15))
            free = T.NEARFIELD_RANGE
            for (ha, hd) in hits:
                if abs(_wrap(ha - cand)) < math.radians(28):
                    free = min(free, hd)
            score = math.cos(_wrap(cand - goal)) + 0.9 * free / T.NEARFIELD_RANGE
            if free < 0.9:
                score -= 3.0
            score += 0.15 * math.cos(_wrap(cand - b.theta))     # hysteresis
            if score > best_score:
                best, best_score, free_ahead = cand, score, free
        cmd["heading"] = best
        slow = free_ahead < 1.3 or abs(_wrap(best - b.theta)) > math.radians(60)
        base = T.AGENT_SPEED if self.cautious else T.RIVAL_SPEED
        cmd["speed"] = 0.0 if self.hold else (base * (0.5 if slow else 1.0))
        # beacons: automatic by distance, not on the way home
        if self.mode == "travel" and b.dist_since_drop >= T.BEACON_DROP_EVERY_CELLS:
            cmd["drop"] = True
        # ping discipline
        cd = T.CAUTIOUS_PING_COOLDOWN_S if self.cautious else T.AGGRESSIVE_PING_COOLDOWN_S
        if b.ticks_since_ping * T.DT >= cd and not self.hold:
            if self.cautious and T.PING_ONLY_IF_UNMAPPED_AHEAD and b.points_ahead() >= T.MIN_POINTS_AHEAD:
                pass
            else:
                cmd["ping"] = True
        return cmd

    def _advance(self, t):
        self.i += 1
        self.best_dist = 1e9; self.best_t = t
        if self.i >= len(self.route):
            self.route = []
            self._plan(t)

    def _arrived(self, label, t):
        b = self.b
        if label in ("DA", "DB"):
            b.log.append((t, f"at {label}, loading"))
            self.mode = "load"; self.load_until = t + T.LOAD_SECONDS
            return
        if label in ("HOME", "S"):
            b.log.append((t, "at shaft (believed)"))
            self.done = True
            self.route = []
            return
        self._advance(t)

    def _after_load(self, t):
        if self.i + 1 < len(self.route):
            self._advance(t)            # loading was a stop on the way, not the end
        else:
            self.route = []
            self._plan(t)

    def _plan(self, t):
        """Stage machine. Cautious: A, then B if still certain, then home.
        Aggressive: B, then across the cave to A, then home."""
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
        if self.mode == "home" or (self.route and self.route[-1][2] in ("S", "HOME")):
            pass
