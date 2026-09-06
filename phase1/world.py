"""Ground truth. Nothing outside sensors.py and sim.py may import this.

The cave is hand-authored as a graph of chambers and passages and rasterised into a
grid: 0 = rock, 1 = dry passage, 2 = flooded (below the waterline). Agents cannot
enter flooded cells; sound travels through them more easily.
"""
import math
import numpy as np
from . import tuning as T

W, H = 200, 120

# Chambers: name -> (x, y, radius). Coordinates are cells; y grows upward.
CHAMBERS = {
    "S":    (14, 60, 6),    # player's shaft
    "C1":   (44, 42, 8),
    "DA":   (66, 16, 6),    # deposit A
    "C2":   (82, 68, 11),   # the big hall
    "ECHO": (48, 98, 5),    # reflective dead end
    "C3":   (122, 42, 8),
    "ANC":  (140, 86, 12),  # the ancient system's chamber
    "SUMP": (108, 104, 9),  # flooded
    "DB":   (176, 96, 7),   # deposit B
    "C4":   (166, 34, 7),
    "R":    (188, 60, 5),   # rival's shaft
}
# Passages: (a, b, width, flooded)
PASSAGES = [
    ("S", "C1", 5, False), ("C1", "DA", 4, False), ("C1", "C2", 6, False),
    ("C2", "ECHO", 4, False), ("C2", "C3", 5, False), ("C3", "ANC", 5, False),
    ("ANC", "DB", 4, False), ("C3", "C4", 5, False), ("C4", "DB", 4, False),
    ("C2", "SUMP", 5, True), ("SUMP", "ANC", 4, True), ("R", "C4", 5, False),
    ("R", "DB", 5, False),
]
DEPOSITS = {"A": CHAMBERS["DA"][:2], "B": CHAMBERS["DB"][:2]}
ANCIENT_POS = CHAMBERS["ANC"][:2]
ECHO_POS = (CHAMBERS["ECHO"][0], CHAMBERS["ECHO"][1] + 3)
SHAFTS = {"player": CHAMBERS["S"][:2], "rival": CHAMBERS["R"][:2]}

# Survey routes: prior intel handed to the policies, as waypoints in the shaft frame.
ROUTES = {
    "player_out_A": ["C1", "DA"],
    "player_A_to_B": ["C1", "C2", "C3", "C4", "DB"],
    "player_home_from_B": ["C4", "C3", "C2", "C1", "S"],
    "player_home_from_A": ["C1", "S"],
    "rival_out": ["C4", "C3", "C2", "C3", "ANC", "DB", "ANC", "C3", "C2", "C1", "DA"],
}


def _rasterise():
    yy, xx = np.mgrid[0:H, 0:W]
    grid = np.zeros((H, W), dtype=np.uint8)
    rng = np.random.default_rng(T.SEED)
    for name, (cx, cy, r) in CHAMBERS.items():
        # slightly lumpy chambers so sonar returns are not perfect circles
        ang = np.arctan2(yy - cy, xx - cx)
        wob = 1.0 + 0.12 * np.sin(3 * ang + rng.uniform(0, 6)) + 0.08 * np.cos(5 * ang + rng.uniform(0, 6))
        mask = (xx - cx) ** 2 + (yy - cy) ** 2 <= (r * wob) ** 2
        grid[mask] = 2 if name == "SUMP" else 1
    for a, b, w, flooded in PASSAGES:
        ax, ay, _ = CHAMBERS[a]; bx, by, _ = CHAMBERS[b]
        # gentle bend so passages are not straight lines
        mx, my = (ax + bx) / 2, (ay + by) / 2
        nx, ny = -(by - ay), (bx - ax)
        nl = math.hypot(nx, ny) or 1.0
        bend = rng.uniform(-0.18, 0.18) * nl
        mx += nx / nl * bend; my += ny / nl * bend
        for (x0, y0), (x1, y1) in (((ax, ay), (mx, my)), ((mx, my), (bx, by))):
            n = int(math.hypot(x1 - x0, y1 - y0) * 2) + 1
            for i in range(n + 1):
                t = i / n
                px, py = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
                mask = (xx - px) ** 2 + (yy - py) ** 2 <= (w / 2) ** 2
                if flooded:
                    grid[mask & (grid == 0)] = 2
                else:
                    grid[mask] = 1
    # waterline: anything in the sump region below y=110 is flooded already; keep
    # a thin dry rim so the hall does not flood.
    grid[0, :] = 0; grid[-1, :] = 0; grid[:, 0] = 0; grid[:, -1] = 0
    return grid


GRID = _rasterise()
FREE = GRID > 0          # sound passes
WALKABLE = GRID == 1     # agents pass


def is_walkable(x, y):
    xi, yi = int(x), int(y)
    return 0 <= xi < W and 0 <= yi < H and WALKABLE[yi, xi]


class AgentTruth:
    def __init__(self, name, x, y, heading_deg, seed):
        self.name = name
        self.x, self.y = float(x), float(y)
        self.heading = math.radians(heading_deg)
        self.alive = True
        self.extracted = False
        self.audible_until = -1.0
        self.rng = np.random.default_rng(seed)
        self.drift_sign_scale = 1.0 if self.rng.random() < 0.5 else -1.0
        self.drift_sign_heading = 1.0 if self.rng.random() < 0.5 else -1.0
        self.cargo = 0
        self.last_true_delta = (0.0, 0.0)   # (forward, turn) actually executed this tick

    def move(self, desired_heading, speed, dt):
        """Turn toward desired heading at a limited rate, then move with wall sliding."""
        if not self.alive or self.extracted:
            self.last_true_delta = (0.0, 0.0)
            return
        d = (desired_heading - self.heading + math.pi) % (2 * math.pi) - math.pi
        max_turn = math.radians(T.AGENT_TURN_RATE) * dt
        turn = max(-max_turn, min(max_turn, d))
        self.heading = (self.heading + turn + math.pi) % (2 * math.pi) - math.pi
        step = speed * dt
        dx, dy = math.cos(self.heading) * step, math.sin(self.heading) * step
        moved = 0.0
        for tx, ty in ((self.x + dx, self.y + dy), (self.x + dx, self.y), (self.x, self.y + dy)):
            if self._clear(tx, ty):
                moved = math.hypot(tx - self.x, ty - self.y)
                self.x, self.y = tx, ty
                break
        self.last_true_delta = (moved, turn)

    def _clear(self, x, y):
        r = T.AGENT_RADIUS
        return all(is_walkable(x + ox, y + oy) for ox, oy in ((0, 0), (r, 0), (-r, 0), (0, r), (0, -r)))


class Beacon:
    def __init__(self, bid, x, y, owner, truth_anchor=False):
        self.id = bid; self.x = x; self.y = y; self.owner = owner
        self.truth_anchor = truth_anchor
        self.range = T.SHAFT_BEACON_RANGE if truth_anchor else T.BEACON_RANGE


class Ancient:
    """Fixed cycle. Signature is audible ANCIENT_WARNING_S before lethal."""
    def __init__(self):
        self.x, self.y = ANCIENT_POS

    def phase(self, t):
        return (t + T.ANCIENT_PHASE_S) % T.ANCIENT_PERIOD_S

    def signature_strength(self, t):
        """0 when quiet; ramps 0->1 over the warning; 1 while lethal."""
        p = self.phase(t)
        start = T.ANCIENT_PERIOD_S - T.ANCIENT_WARNING_S - T.ANCIENT_LETHAL_S
        if p < start:
            return 0.0
        if p < start + T.ANCIENT_WARNING_S:
            return 0.3 + 0.7 * (p - start) / T.ANCIENT_WARNING_S
        return 1.0

    def lethal(self, t):
        return self.phase(t) >= T.ANCIENT_PERIOD_S - T.ANCIENT_LETHAL_S


class World:
    def __init__(self):
        self.t = 0.0
        self.tick = 0
        px, py = SHAFTS["player"]; rx, ry = SHAFTS["rival"]
        self.agents = {
            "player": AgentTruth("player", px, py, 0, T.SEED * 11 + 1),
            "rival": AgentTruth("rival", rx, ry, 180, T.SEED * 11 + 2),
        }
        self.beacons = {}
        self.next_beacon_id = 1
        for name, (sx, sy) in SHAFTS.items():
            self.beacons[f"shaft_{name}"] = Beacon(f"shaft_{name}", sx, sy, name, truth_anchor=True)
        self.ancient = Ancient()
        self.deposits = dict(DEPOSITS)
        self.spoof_done = False
        self.echo_fired = 0
        self.events = []       # (t, kind, payload) -- truth-side log, headless only
        self.pending_sounds = []    # (t, x, y, kind) one-shot loud events, heard at exactly t
        self.load_progress = {"player": 0.0, "rival": 0.0}

    def log(self, kind, **kw):
        self.events.append((self.t, kind, kw))

    def drop_beacon(self, owner):
        a = self.agents[owner]
        bid = f"{owner}_{self.next_beacon_id}"; self.next_beacon_id += 1
        self.beacons[bid] = Beacon(bid, a.x, a.y, owner)
        self.log("beacon_drop", owner=owner, id=bid, x=a.x, y=a.y)
        return bid

    def spoof(self, victim, cloned_id):
        """Scripted: the rival has cloned the victim's most recent beacon and placed
        the clone SPOOF_AHEAD_CELLS ahead of the victim. Same id, wrong place."""
        a = self.agents[victim]
        b = self.beacons[cloned_id]
        cx = a.x + math.cos(a.heading) * T.SPOOF_AHEAD_CELLS
        cy = a.y + math.sin(a.heading) * T.SPOOF_AHEAD_CELLS
        b.x, b.y = cx, cy                 # the original is gone; the clone answers to its id
        self.spoof_done = True
        self.log("spoof", victim=victim, id=cloned_id, x=cx, y=cy)

    def step_loading(self, name, loading):
        """Cargo only arrives if the agent is actually at a deposit. Belief finds out
        through a cargo return, not by assumption."""
        a = self.agents[name]
        if not loading:
            self.load_progress[name] = 0.0
            return
        near = any(math.hypot(a.x - dx, a.y - dy) < 6.0 for dx, dy in self.deposits.values())
        if near and a.cargo < T.CARGO_CAPACITY:
            self.load_progress[name] += T.DT
            if self.load_progress[name] >= T.LOAD_SECONDS - T.DT:
                a.cargo += 1
                self.load_progress[name] = 0.0
                self.log("loaded", agent=name, cargo=a.cargo)

    def step_hazards(self):
        for a in self.agents.values():
            inside = a.alive and math.hypot(a.x - self.ancient.x, a.y - self.ancient.y) < T.ANCIENT_RADIUS
            was = getattr(a, "_in_ancient", False)
            if inside != was:
                a._in_ancient = inside
                self.log("ancient_zone", agent=a.name, inside=inside)
        if self.ancient.lethal(self.t):
            for a in self.agents.values():
                if a.alive and math.hypot(a.x - self.ancient.x, a.y - self.ancient.y) < T.ANCIENT_RADIUS:
                    a.alive = False
                    self.pending_sounds.append((self.t + T.DT, a.x, a.y, "crash"))
                    self.log("death", agent=a.name, x=a.x, y=a.y, cause="ancient")
