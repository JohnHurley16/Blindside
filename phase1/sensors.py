"""The sensor layer. The ONLY module that reads both World and (an agent's) truth and
produces returns. Everything it emits is a return: noisy, sometimes wrong.

Return tuples:
  ("odom", forward, turn)                       dead reckoning, corrupted
  ("rb", range, bearing_body, quality, source)  sonar / near-field / false
  ("bearing", bearing_body, quality, kind)      passive acoustic. kind is a hint about
                                                the sound's character, not an identity
  ("fix", beacon_id, range, bearing_body)       a beacon heard. May be lying.
  ("cargo", count)                              self report after a load attempt
"""
import heapq
import math
import numpy as np
from . import tuning as T
from . import world as Wd


def _wrap(a):
    return (a + math.pi) % (2 * math.pi) - math.pi


# ---- acoustics: sound follows passages ---------------------------------------------
_NB = [(-1, 0, 1.0), (1, 0, 1.0), (0, -1, 1.0), (0, 1, 1.0),
       (-1, -1, 1.4142), (1, -1, 1.4142), (-1, 1, 1.4142), (1, 1, 1.4142)]


def sound_field(sx, sy, max_range):
    """Dijkstra from a source over free cells. Returns (dist, pred) arrays; dist is inf
    beyond max_range. Flooded cells are cheaper: water carries."""
    H, W = Wd.H, Wd.W
    dist = np.full((H, W), np.inf)
    pred = np.full((H, W), -1, dtype=np.int32)
    sx, sy = int(sx), int(sy)
    if not Wd.FREE[sy, sx]:
        return dist, pred
    dist[sy, sx] = 0.0
    heap = [(0.0, sx, sy)]
    free = Wd.FREE; grid = Wd.GRID
    while heap:
        d, x, y = heapq.heappop(heap)
        if d > dist[y, x]:
            continue
        for dx, dy, c in _NB:
            nx, ny = x + dx, y + dy
            if not free[ny, nx]:
                continue
            cost = c * (T.FLOODED_COST if grid[ny, nx] == 2 else 1.0)
            nd = d + cost
            if nd < dist[ny, nx] and nd <= max_range:
                dist[ny, nx] = nd
                pred[ny, nx] = y * W + x
                heapq.heappush(heap, (nd, nx, ny))
    return dist, pred


def arrival(field, lx, ly, max_range):
    """(path_distance, arrival_bearing_world) at a listener, or None if inaudible.
    Bearing points the way the sound came in: back along the shortest path."""
    dist, pred = field
    xi, yi = int(lx), int(ly)
    d = dist[yi, xi]
    if not np.isfinite(d) or d > max_range:
        return None
    cx, cy = xi, yi
    for _ in range(5):
        p = pred[cy, cx]
        if p < 0:
            break
        cx, cy = p % Wd.W, p // Wd.W
    if (cx, cy) == (xi, yi):
        return d, 0.0
    return d, math.atan2(cy + 0.5 - ly, cx + 0.5 - lx)


def _march(x, y, ang, max_r, blocked, step=0.3):
    r = 0.0
    while r < max_r:
        r += step
        px, py = x + math.cos(ang) * r, y + math.sin(ang) * r
        xi, yi = int(px), int(py)
        if not (0 <= xi < Wd.W and 0 <= yi < Wd.H) or blocked[yi, xi]:
            return r
    return None


class SensorRig:
    """Per-agent sensor state. Holds no belief and no policy."""

    def __init__(self, name, seed):
        self.name = name
        self.rng = np.random.default_rng(seed)
        self.beacons_in_range = set()
        self.next_shaft_fix = -1.0
        self.deaf_until = -1.0
        self.next_motion_listen = 0.0
        self.motion_field = None       # cached (field, t, src)
        self.ancient_field = None
        self.tick = 0

    def sample(self, world, me, cmd, t):
        """cmd: dict(ping=bool, load=bool). Returns a list of return tuples."""
        self.tick += 1
        out = []
        out.append(self._odometry(me))
        if cmd.get("ping"):
            out += self._sonar(me)
            me.audible_until = t + T.SONAR_AUDIBLE_S
            self.deaf_until = t + T.SELF_DEAF_AFTER_PING_S
        if self.tick % T.NEARFIELD_PERIOD_TICKS == 0:
            out += self._nearfield(me)
        if t >= self.deaf_until:
            out += self._passive(world, me, t)
        out += self._beacons(world, me, t)
        if cmd.get("load"):
            out.append(("cargo", me.cargo))
        return out

    # dead reckoning: the true displacement, corrupted by bias and noise
    def _odometry(self, me):
        df, dturn = me.last_true_delta
        scale = 1.0 + T.DR_SCALE_BIAS * me.drift_sign_scale
        df_m = df * scale + self.rng.normal(0, T.DR_POS_NOISE_PER_CELL * math.sqrt(max(df, 1e-9)))
        hb = math.radians(T.DR_HEADING_BIAS_DEG_PER_CELL) * me.drift_sign_heading * df
        hn = self.rng.normal(0, math.radians(T.DR_HEADING_NOISE_DEG_PER_CELL) * math.sqrt(max(df, 1e-9)))
        return ("odom", df_m, dturn + hb + hn)

    def _sonar(self, me):
        out = []
        half = math.radians(T.SONAR_ARC_DEG) / 2
        for i in range(T.SONAR_RAYS):
            b = -half + 2 * half * i / (T.SONAR_RAYS - 1)
            r = _march(me.x, me.y, me.heading + b, T.SONAR_RANGE, ~Wd.FREE)
            if r is None:
                continue
            q = 1.0 - 0.7 * r / T.SONAR_RANGE
            rn = r + self.rng.normal(0, T.SONAR_RANGE_NOISE + 0.02 * r)
            bn = b + self.rng.normal(0, math.radians(T.SONAR_BEARING_NOISE_DEG))
            out.append(("rb", max(0.2, rn), bn, q, "sonar"))
        for _ in range(T.SONAR_FALSE_RETURNS):
            out.append(("rb", self.rng.uniform(3, T.SONAR_RANGE), self.rng.uniform(-half, half),
                        self.rng.uniform(*T.SONAR_FALSE_QUALITY), "false"))
        return out

    def _nearfield(self, me):
        out = []
        for i in range(T.NEARFIELD_RAYS):
            b = 2 * math.pi * i / T.NEARFIELD_RAYS + self.rng.uniform(-0.2, 0.2)
            r = _march(me.x, me.y, me.heading + b, T.NEARFIELD_RANGE, ~Wd.WALKABLE, step=0.2)
            if r is not None:
                out.append(("rb", r + self.rng.normal(0, 0.15), b, T.NEARFIELD_QUALITY, "near"))
        return out

    def _bearing_return(self, me, d, bw, max_range, kind):
        q = max(0.0, 1.0 - d / max_range)
        noise = math.radians(T.BEARING_NOISE_NEAR_DEG + (T.BEARING_NOISE_FAR_DEG - T.BEARING_NOISE_NEAR_DEG) * (1 - q))
        bb = _wrap(bw - me.heading + self.rng.normal(0, noise))
        return ("bearing", bb, q, kind)

    def _passive(self, world, me, t):
        out = []
        # the rival, walking or pinging
        for other in world.agents.values():
            if other is me or not other.alive or other.extracted:
                continue
            pinging = t < other.audible_until
            if pinging:
                ev = getattr(other, "_ping_field", None)
                if ev is None or ev[1] != other.audible_until:
                    other._ping_field = (sound_field(other.x, other.y, T.HEAR_PING_RANGE), other.audible_until)
                a = arrival(other._ping_field[0], me.x, me.y, T.HEAR_PING_RANGE)
                if a and self.tick % 10 == 0:
                    out.append(self._bearing_return(me, a[0], a[1], T.HEAR_PING_RANGE, "ping"))
            if t >= self.next_motion_listen and other.last_true_delta[0] > 0:
                self.next_motion_listen = t + T.MOTION_LISTEN_PERIOD
                if math.hypot(other.x - me.x, other.y - me.y) < T.HEAR_MOTION_RANGE:
                    f = sound_field(other.x, other.y, T.HEAR_MOTION_RANGE)
                    a = arrival(f, me.x, me.y, T.HEAR_MOTION_RANGE)
                    if a:
                        out.append(self._bearing_return(me, a[0], a[1], T.HEAR_MOTION_RANGE, "tone"))
        # the ancient system's signature
        s = world.ancient.signature_strength(t)
        if s > 0 and self.tick % 5 == 0:
            if self.ancient_field is None:
                self.ancient_field = sound_field(world.ancient.x, world.ancient.y, T.HEAR_ANCIENT_RANGE)
            a = arrival(self.ancient_field, me.x, me.y, T.HEAR_ANCIENT_RANGE)
            if a:
                r = self._bearing_return(me, a[0], a[1], T.HEAR_ANCIENT_RANGE, "signature")
                out.append(("bearing", r[1], r[2] * s, "signature"))
        # one-shot loud events: a death, or the scripted phantom
        for (et, ex, ey, kind) in world.pending_sounds:
            if abs(et - t) < T.DT / 2:
                f = sound_field(ex, ey, T.HEAR_CRASH_RANGE)
                a = arrival(f, me.x, me.y, T.HEAR_CRASH_RANGE)
                if a:
                    out.append(self._bearing_return(me, a[0], a[1], T.HEAR_CRASH_RANGE, kind))
        return out

    def _beacons(self, world, me, t=0.0):
        out = []
        now = set()
        for bid, b in world.beacons.items():
            if b.owner != me.name:
                continue
            d = math.hypot(b.x - me.x, b.y - me.y)
            if d < b.range:
                now.add(bid)
                periodic = b.truth_anchor and t >= self.next_shaft_fix
                if bid not in self.beacons_in_range or periodic:
                    if b.truth_anchor:
                        self.next_shaft_fix = t + T.SHAFT_FIX_PERIOD_S
                    bw = math.atan2(b.y - me.y, b.x - me.x)
                    rn = d + self.rng.normal(0, T.BEACON_FIX_NOISE)
                    bb = _wrap(bw - me.heading + self.rng.normal(0, math.radians(2.0)))
                    out.append(("fix", bid, max(0.0, rn), bb))
        self.beacons_in_range = now
        return out
