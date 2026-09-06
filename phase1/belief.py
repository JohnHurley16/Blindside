"""What an agent thinks. Built only from sensor returns. Never imports world.

Points accumulate in the estimated frame. A fix back-propagates its correction over
everything placed since the previous fix (see docs/PHASE-1-OPEN-QUESTIONS.md, item 1).
"""
import math
import numpy as np
from . import tuning as T


def _wrap(a):
    return (a + math.pi) % (2 * math.pi) - math.pi


class Belief:
    def __init__(self, name, x, y, heading, known_places, rng):
        self.name = name
        self.x, self.y, self.theta = float(x), float(y), float(heading)
        self.rng = rng
        self.known_places = dict(known_places)   # prior intel: name -> (x, y) in shaft frame
        # uncertainty
        self.dist_since_fix = 0.0
        self.ticks_since_fix = 0
        self.sig_theta = T.EST_HEADING_SIGMA_AFTER_FIX
        self.t_epoch = 0.0
        self.epoch_x, self.epoch_y = self.x, self.y
        # map
        self.px = np.zeros(T.MAX_POINTS); self.py = np.zeros(T.MAX_POINTS)
        self.pz = np.zeros(T.MAX_POINTS); self.pconf = np.zeros(T.MAX_POINTS)
        self.pt = np.zeros(T.MAX_POINTS); self.n = 0
        self.trail = [(self.x, self.y, 0.0)]
        # contacts, beacons, inventory, self report
        self.contacts = []
        self.beacons = {}            # id -> [x, y, t_placed]
        self.beacon_order = []       # ids in drop order (the chain)
        self.cargo = 0
        self.dist_since_drop = 0.0
        self.ticks_since_ping = 10 ** 6
        self.last_fix = None         # dict(t, jump, id, dtheta)
        self.recent_near = []        # (t, x, y) recent near-field hits in the belief frame, for steering
        # display-only event streams (still belief-derived)
        self.own_pings = []          # (t, x, y, theta)
        self.heard_pings = []        # (t, bearing_world, quality)
        self.signature = None        # dict(t, bearing, strength) latest ancient signature
        self.crashes = []            # (t, bearing, quality)
        self.fix_events = []         # (t, x_pre, y_pre, x_post, y_post)
        self.log = []                # (t, text) belief-side event log

    # ---- uncertainty -----------------------------------------------------------------
    def sigma_along(self):
        return T.EST_SIGMA_AFTER_FIX + T.EST_SIGMA_ALONG_PER_CELL * self.dist_since_fix

    def sigma_cross(self):
        return T.EST_SIGMA_AFTER_FIX + 0.5 * self.dist_since_fix * self.sig_theta

    def sigma_pos(self):
        return math.hypot(self.sigma_along(), self.sigma_cross())

    def ellipse(self):
        """(sa, sc, angle): along/cross sigmas and the along-track direction."""
        vx, vy = self.x - self.epoch_x, self.y - self.epoch_y
        ang = math.atan2(vy, vx) if math.hypot(vx, vy) > 1.0 else self.theta
        return self.sigma_along(), self.sigma_cross(), ang

    # ---- fusion ----------------------------------------------------------------------
    def fuse(self, returns, t):
        self.ticks_since_fix += 1
        self.ticks_since_ping += 1
        for r in returns:
            kind = r[0]
            if kind == "odom":
                self._integrate(r[1], r[2], t)
            elif kind == "rb":
                self._add_point(r[1], r[2], r[3], t, r[4])
            elif kind == "bearing":
                self._add_contact(r[1], r[2], r[3], t)
            elif kind == "fix":
                self._fix(r[1], r[2], r[3], t)
            elif kind == "cargo":
                if r[1] != self.cargo:
                    self.cargo = r[1]
                    self.log.append((t, f"cargo now {self.cargo}"))
        self.recent_near = [h for h in self.recent_near if t - h[0] < 1.5]
        cut = t - T.CONTACT_FADE_S
        self.contacts = [c for c in self.contacts if c["t_last"] > cut]

    def _integrate(self, df, dturn, t):
        self.theta = _wrap(self.theta + dturn)
        self.x += math.cos(self.theta) * df
        self.y += math.sin(self.theta) * df
        self.dist_since_fix += df
        self.dist_since_drop += df
        self.sig_theta += T.EST_SIGMA_HEADING_RAD_PER_CELL * df
        if df > 0 and (not self.trail or math.hypot(self.x - self.trail[-1][0], self.y - self.trail[-1][1]) > 0.5):
            self.trail.append((self.x, self.y, t))

    def body_to_world(self, r, b):
        a = self.theta + b
        return self.x + math.cos(a) * r, self.y + math.sin(a) * r

    def _add_point(self, r, b, q, t, source):
        wx, wy = self.body_to_world(r, b)
        if source == "near":
            self.recent_near.append((t, wx, wy))       # belief frame, not body frame
        if self.n >= T.MAX_POINTS:
            return
        i = self.n
        self.px[i], self.py[i] = wx, wy
        self.pz[i] = self.rng.uniform(0.0, 2.2)      # fake wall height so orbiting means something
        self.pconf[i] = q
        self.pt[i] = t
        self.n += 1

    def _add_contact(self, b, q, kind, t):
        bw = _wrap(self.theta + b)
        if kind == "signature":
            self.signature = {"t": t, "bearing": bw, "strength": q}
            return
        if kind == "crash":
            self.crashes.append((t, bw, q))
        if kind == "ping":
            self.heard_pings.append((t, bw, q))
        for c in self.contacts:
            if abs(_wrap(c["bearing"] - bw)) < math.radians(T.CONTACT_MERGE_DEG) and t - c["t_last"] < T.CONTACT_MERGE_S:
                k = 0.5
                c["bearing"] = _wrap(c["bearing"] + k * _wrap(bw - c["bearing"]))
                c["quality"] = max(c["quality"] * 0.8, q)
                c["t_last"] = t; c["n"] += 1
                c["kind"] = kind if kind != "tone" else c["kind"]
                return
        self.contacts.append({"bearing": bw, "quality": q, "t_first": t, "t_last": t, "n": 1, "kind": kind})
        self.log.append((t, f"new contact {kind} brg {math.degrees(bw):.0f} q {q:.2f}"))

    def _fix(self, bid, r, b, t):
        if bid not in self.beacons:
            return                                    # unknown beacon: not trusted
        bx, by, _ = self.beacons[bid]
        pre_x, pre_y = self.x, self.y
        # first estimate with current heading, then infer heading error from the jump
        est_x = bx - math.cos(self.theta + b) * r
        est_y = by - math.sin(self.theta + b) * r
        vpx, vpy = pre_x - self.epoch_x, pre_y - self.epoch_y
        vfx, vfy = est_x - self.epoch_x, est_y - self.epoch_y
        dtheta = 0.0
        if math.hypot(vpx, vpy) > 3.0 and math.hypot(vfx, vfy) > 3.0:
            dtheta = _wrap(math.atan2(vfy, vfx) - math.atan2(vpy, vpx))
            dtheta = max(-math.radians(25), min(math.radians(25), dtheta)) * T.HEADING_FIX_GAIN
        self.theta = _wrap(self.theta + dtheta)
        post_x = bx - math.cos(self.theta + b) * r
        post_y = by - math.sin(self.theta + b) * r
        self._backpropagate(dtheta, pre_x, pre_y, post_x, post_y, t, exclude=bid)
        self.x, self.y = post_x, post_y
        jump = math.hypot(post_x - pre_x, post_y - pre_y)
        self.last_fix = {"t": t, "jump": jump, "id": bid, "dtheta": dtheta}
        self.fix_events.append((t, pre_x, pre_y, post_x, post_y))
        self.log.append((t, f"fix {bid} jump {jump:.1f} dtheta {math.degrees(dtheta):.1f}"))
        self.t_epoch = t
        self.epoch_x, self.epoch_y = post_x, post_y
        self.dist_since_fix = 0.0
        self.ticks_since_fix = 0
        self.sig_theta = T.EST_HEADING_SIGMA_AFTER_FIX

    def _backpropagate(self, dtheta, pre_x, pre_y, post_x, post_y, t, exclude):
        """Slide everything placed this epoch onto the corrected pose. Weight grows
        linearly from 0 at the epoch start to 1 now: drift is assumed to have
        accumulated steadily."""
        span = max(t - self.t_epoch, 1e-6)
        ox, oy = self.epoch_x, self.epoch_y
        c, s = math.cos(dtheta), math.sin(dtheta)
        rpx = ox + c * (pre_x - ox) - s * (pre_y - oy)
        rpy = oy + s * (pre_x - ox) + c * (pre_y - oy)
        dx, dy = post_x - rpx, post_y - rpy

        def corr(xs, ys, ts):
            w = np.clip((ts - self.t_epoch) / span, 0.0, 1.0)
            a = w * dtheta
            ca, sa = np.cos(a), np.sin(a)
            rx = ox + ca * (xs - ox) - sa * (ys - oy)
            ry = oy + sa * (xs - ox) + ca * (ys - oy)
            return rx + w * dx, ry + w * dy

        n = self.n
        if n:
            m = self.pt[:n] > self.t_epoch
            if m.any():
                nx, ny = corr(self.px[:n][m], self.py[:n][m], self.pt[:n][m])
                self.px[:n][m] = nx; self.py[:n][m] = ny
        if self.trail:
            tx = np.array([p[0] for p in self.trail]); ty = np.array([p[1] for p in self.trail])
            tt = np.array([p[2] for p in self.trail])
            nx, ny = corr(tx, ty, tt)
            self.trail = list(zip(nx.tolist(), ny.tolist(), tt.tolist()))
        for bid, (bx, by, bt) in self.beacons.items():
            if bt > self.t_epoch and bid != exclude:
                nx, ny = corr(np.array([bx]), np.array([by]), np.array([bt]))
                self.beacons[bid] = [float(nx[0]), float(ny[0]), bt]
        for c in self.contacts:
            c["bearing"] = _wrap(c["bearing"] + dtheta * min(1.0, (c["t_last"] - self.t_epoch) / span))

    # ---- actions the policy tells us about -------------------------------------------
    def note_beacon_drop(self, bid, t):
        self.beacons[bid] = [self.x, self.y, t]
        self.beacon_order.append(bid)
        self.dist_since_drop = 0.0
        self.log.append((t, f"drop {bid}"))

    def note_ping(self, t):
        self.ticks_since_ping = 0
        self.own_pings.append((t, self.x, self.y, self.theta))
        self.log.append((t, "ping"))

    def points_ahead(self, radius=12.0):
        n = self.n
        if not n:
            return 0
        dx = self.px[:n] - self.x; dy = self.py[:n] - self.y
        fwd = dx * math.cos(self.theta) + dy * math.sin(self.theta)
        return int(np.count_nonzero((fwd > 0) & (dx * dx + dy * dy < radius * radius)))
