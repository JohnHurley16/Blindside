"""Belief-only display. Receives Belief objects; never sees World during the run.
After the match ends, sim.reveal_after_end() hands over truth for the replay overlay.

Camera: orbit with left drag, zoom with wheel. Starts top-down.
Key: R = Recall (single use).
"""
import math
import time
import numpy as np
import vispy
from vispy import scene, app
from vispy.scene import visuals
from . import tuning as T


def pick_backend():
    for b in ("pyqt6", "glfw", "pyqt5", "pyside6"):
        try:
            vispy.use(app=b)
            return b
        except Exception:
            continue
    raise RuntimeError("no vispy backend: pip install PyQt6 (or glfw)")


def _wrap(a):
    return (a + math.pi) % (2 * math.pi) - math.pi


KIND_COLOR = {"tone": (1.0, 0.72, 0.25), "ping": (0.85, 0.95, 1.0), "crash": (1.0, 0.3, 0.25)}
LOW, HIGH = np.array([0.22, 0.32, 0.45]), np.array([0.8, 0.97, 1.0])


def _ring(cx, cy, r, n=72, a0=0.0, a1=2 * math.pi, z=0.0):
    a = np.linspace(a0, a1, n)
    return np.column_stack([cx + r * np.cos(a), cy + r * np.sin(a), np.full(n, z)])


def _segs_from_polyline(p):
    return np.repeat(p, 2, axis=0)[1:-1]


class View:
    def __init__(self, sim, audio=None, show=True, size=(1400, 900)):
        self.sim = sim
        self.audio = audio
        self.b = sim.beliefs["player"]
        self.canvas = scene.SceneCanvas(title="BLINDSIDE - belief view (R = Recall)", size=size,
                                        bgcolor=(0.015, 0.015, 0.025), keys="interactive", show=show)
        self.view = self.canvas.central_widget.add_view()
        cam = scene.TurntableCamera(elevation=90, azimuth=0, fov=0, up="z")
        cam.center = (100, 60, 0)
        cam.scale_factor = 140
        self.view.camera = cam
        S = self.view.scene
        self.cloud = visuals.Markers(parent=S)
        self.cloud.set_gl_state("translucent", depth_test=False)
        self.trail = visuals.Line(parent=S, color=(0.5, 0.6, 0.7, 0.35), width=1)
        self.beacons = visuals.Markers(parent=S)
        self.ellipse = visuals.Line(parent=S, color=(0.3, 1.0, 0.5, 0.9), width=1.5)
        self.agent = visuals.Markers(parent=S)
        self.heading = visuals.Line(parent=S, color=(0.4, 1.0, 0.6, 1.0), width=2)
        self.contacts = visuals.Line(parent=S, connect="segments", width=1.5)
        self.signature = visuals.Line(parent=S, connect="segments", width=2)
        self.fronts = visuals.Line(parent=S, connect="segments", width=1.2)
        self.fixflash = visuals.Line(parent=S, connect="segments", width=2)
        for v in (self.trail, self.ellipse, self.heading, self.contacts, self.signature, self.fronts, self.fixflash):
            v.set_gl_state("translucent", depth_test=False)
        self.reveal_vis = []
        self.hud_lines = [visuals.Text("", parent=self.canvas.scene, pos=(14, 14 + 18 * i), anchor_x="left",
                                       anchor_y="top", color=(0.85, 0.9, 0.95), font_size=9) for i in range(10)]
        self.banner = visuals.Text("", parent=self.canvas.scene, pos=(size[0] / 2, size[1] - 40), anchor_x="center",
                                   anchor_y="center", color=(1.0, 0.85, 0.4), font_size=16, bold=True)
        self.legend = visuals.Text(
            "cloud: brighter = more confident    amber wedge: something moving    white wedge: a ping heard    "
            "magenta: machinery signature    red: something broke    green: you, and how sure you are",
            parent=self.canvas.scene, pos=(14, size[1] - 12), anchor_x="left", anchor_y="bottom",
            color=(0.5, 0.55, 0.6), font_size=7)
        self.canvas.events.key_press.connect(self.on_key)
        self.canvas.events.resize.connect(self._on_resize)
        self.revealed = False
        self.wall0 = None
        self.timer = app.Timer(interval=1 / 60, connect=self.on_tick, start=show)

    # ---- input ------------------------------------------------------------------------
    def on_key(self, ev):
        if ev.key is not None and ev.key.name.lower() == "r":
            if self.sim.recall():
                self.banner.text = "RECALL SENT"
                if self.audio:
                    self.audio.recall_sent()

    def _on_resize(self, ev):
        w, h = self.canvas.size
        self.banner.pos = (w / 2, h - 40)
        self.legend.pos = (14, h - 12)

    # ---- frame ------------------------------------------------------------------------
    def on_tick(self, ev):
        if self.wall0 is None:
            self.wall0 = time.perf_counter()
        target = time.perf_counter() - self.wall0
        n = 0
        while self.sim.t < target and not self.sim.over and n < 6:
            self.sim.step(); n += 1
        self.draw()

    def draw(self):
        b = self.b; t = self.sim.t
        self._draw_cloud(b)
        self._draw_agent(b)
        self._draw_contacts(b, t)
        self._draw_fronts(b, t)
        self._draw_fix(b, t)
        self._draw_hud(b, t)
        if self.audio:
            self.audio.update(b, t, self.view.camera.azimuth)
        if self.sim.over and not self.revealed:
            self._reveal()
        self.canvas.update()

    def _draw_cloud(self, b):
        n = b.n
        if n == 0:
            self.cloud.visible = False
            return
        q = b.pconf[:n]
        col = LOW[None, :] + (HIGH - LOW)[None, :] * q[:, None]
        rgba = np.column_stack([col, 0.25 + 0.75 * q])
        pos = np.column_stack([b.px[:n], b.py[:n], b.pz[:n]])
        self.cloud.set_data(pos, face_color=rgba, edge_width=0, size=2.0 + 5.0 * q, symbol="disc")
        self.cloud.visible = True
        if len(b.trail) > 1:
            self.trail.set_data(np.array([(x, y, 0.05) for x, y, _ in b.trail]))
            self.trail.visible = True

    def _draw_agent(self, b):
        self.agent.set_data(np.array([[b.x, b.y, 0.2]]), face_color=(0.4, 1.0, 0.6, 1.0), size=11, symbol="triangle_up")
        self.heading.set_data(np.array([[b.x, b.y, 0.2], [b.x + 3 * math.cos(b.theta), b.y + 3 * math.sin(b.theta), 0.2]]))
        sa, sc, ang = b.ellipse()
        a = np.linspace(0, 2 * math.pi, 64)
        ex, ey = T.ELLIPSE_SIGMAS * sa * np.cos(a), T.ELLIPSE_SIGMAS * sc * np.sin(a)
        c, s = math.cos(ang), math.sin(ang)
        self.ellipse.set_data(np.column_stack([b.x + c * ex - s * ey, b.y + s * ex + c * ey, np.full(64, 0.1)]))
        if b.beacons:
            pts = np.array([[x, y, 0.1] for (x, y, _) in b.beacons.values()])
            self.beacons.set_data(pts, face_color=(0.6, 0.8, 1.0, 0.9), size=7, symbol="diamond")
            self.beacons.visible = True

    def _wedge(self, b, bearing, half, length, z=0.15):
        o = np.array([b.x, b.y, z])
        pts = []
        for a in (bearing - half, bearing, bearing + half):
            pts += [o, o + np.array([math.cos(a) * length, math.sin(a) * length, 0])]
        return pts

    def _draw_contacts(self, b, t):
        segs, cols = [], []
        for c in b.contacts:
            age = t - c["t_last"]
            alpha = max(0.0, 1.0 - age / T.CONTACT_FADE_S)
            if alpha <= 0:
                continue
            q = c["quality"]
            half = math.radians(T.BEARING_NOISE_NEAR_DEG + (T.BEARING_NOISE_FAR_DEG - T.BEARING_NOISE_NEAR_DEG) * (1 - q))
            L = 25 + 35 * q
            pts = self._wedge(b, c["bearing"], half, L)
            segs += pts
            rgb = KIND_COLOR.get(c["kind"], (1, 1, 1))
            cols += [(*rgb, alpha * (0.35 + 0.65 * q))] * len(pts)
        if segs:
            self.contacts.set_data(np.array(segs), color=np.array(cols))
            self.contacts.visible = True
        else:
            self.contacts.visible = False
        sig = b.signature
        if sig and t - sig["t"] < 1.0:
            s = sig["strength"]
            pulse = 0.5 + 0.5 * math.sin(t * (3 + 14 * s))
            pts = self._wedge(b, sig["bearing"], math.radians(8), 30 + 40 * s, z=0.16)
            r = (t * (6 + 20 * s)) % 12
            ring = _ring(b.x + math.cos(sig["bearing"]) * (8 + r), b.y + math.sin(sig["bearing"]) * (8 + r), 2 + s * 3,
                         n=24, a0=sig["bearing"] - 1.2, a1=sig["bearing"] + 1.2, z=0.16)
            pts += list(_segs_from_polyline(ring))
            self.signature.set_data(np.array(pts), color=(0.95, 0.3, 0.95, 0.35 + 0.6 * pulse * s))
            self.signature.visible = True
        else:
            self.signature.visible = False

    def _draw_fronts(self, b, t):
        segs, cols = [], []
        for (t0, x, y, _) in b.own_pings[-6:]:
            age = t - t0
            if 0 <= age < T.WAVEFRONT_LIFE_S:
                ring = _ring(x, y, age * T.WAVEFRONT_SPEED, n=96, z=0.12)
                segs += list(_segs_from_polyline(ring))
                cols += [(0.6, 0.9, 1.0, 0.7 * (1 - age / T.WAVEFRONT_LIFE_S))] * (2 * 96 - 2)
        for stream, rgb, R in ((b.heard_pings, (0.85, 0.95, 1.0), 35), (b.crashes, (1.0, 0.3, 0.25), 50)):
            for (t0, bw, q) in stream[-8:]:
                age = t - t0
                if not (0 <= age < 4.0):
                    continue
                d = 55 - age * T.WAVEFRONT_SPEED
                cx, cy = b.x + math.cos(bw) * (d + R), b.y + math.sin(bw) * (d + R)
                back = bw + math.pi
                arc = _ring(cx, cy, R, n=40, a0=back - 0.6, a1=back + 0.6, z=0.12)
                segs += list(_segs_from_polyline(arc))
                cols += [(*rgb, (0.3 + 0.7 * q) * (1 - age / 4.0))] * (2 * 40 - 2)
        if segs:
            self.fronts.set_data(np.array(segs), color=np.array(cols))
            self.fronts.visible = True
        else:
            self.fronts.visible = False

    def _draw_fix(self, b, t):
        segs, cols = [], []
        for (t0, x0, y0, x1, y1) in b.fix_events[-3:]:
            age = t - t0
            if age < 3.0:
                a = 1 - age / 3.0
                segs += [np.array([x0, y0, 0.2]), np.array([x1, y1, 0.2])]
                cols += [(1.0, 0.95, 0.3, a)] * 2
                ring = _ring(x1, y1, 1.5 + age * 4, n=32, z=0.2)
                segs += list(_segs_from_polyline(ring))
                cols += [(1.0, 0.95, 0.3, a * 0.6)] * (2 * 32 - 2)
        if segs:
            self.fixflash.set_data(np.array(segs), color=np.array(cols))
            self.fixflash.visible = True
        else:
            self.fixflash.visible = False

    def _draw_hud(self, b, t):
        s = self.sim
        left = max(0.0, T.MATCH_SECONDS - t)
        win = T.EXTRACT_WINDOW_OPENS - t
        win_txt = f"extraction window opens in {int(win)//60}:{int(win)%60:02d}" if win > 0 else "EXTRACTION WINDOW OPEN"
        since_fix = b.ticks_since_fix * T.DT
        lf = b.last_fix
        lines = [
            f"T-{int(left)//60}:{int(left)%60:02d}    {win_txt}",
            f"cargo {b.cargo}/{T.CARGO_CAPACITY}    position uncertainty +/-{b.sigma_pos():.1f} cells    last fix {since_fix:.0f}s ago",
            f"last fix: {lf['id']}  moved estimate {lf['jump']:.1f} cells, heading {math.degrees(lf['dtheta']):+.1f} deg" if lf else "last fix: none",
            f"pings sent {len(b.own_pings)}    contacts held {len(b.contacts)}    map points {b.n}",
            "recall: " + ("USED" if s.recall_used else "available (press R) - single use"),
            "agent: " + ("HOLDING (machinery signature)" if s.policies['player'].hold else s.policies['player'].mode),
        ]
        if b.log:
            lines.append("log: " + " | ".join(txt for _, txt in b.log[-3:]))
        for i, tv in enumerate(self.hud_lines):
            tv.text = lines[i] if i < len(lines) else ""
        if s.over and s.result:
            r = s.result
            self.banner.text = f"MATCH OVER - agent {r['player']}, cargo {r['cargo']}   (truth now shown in red)"
        elif s.recall_used and s.recall_at is None:
            self.banner.text = "RECALL RECEIVED - agent retracing its beacon chain"

    # ---- after the end ------------------------------------------------------------------
    def _reveal(self):
        self.revealed = True
        R = self.sim.reveal_after_end()
        S = self.view.scene
        walls = np.column_stack([R["walls"], np.full(len(R["walls"]), -0.1)])
        m = visuals.Markers(parent=S); m.set_data(walls, face_color=(0.9, 0.25, 0.2, 0.35), size=2.5, edge_width=0)
        m.set_gl_state("translucent", depth_test=False)
        self.reveal_vis.append(m)
        if len(R["flooded"]):
            fl = np.column_stack([R["flooded"], np.full(len(R["flooded"]), -0.1)])
            f = visuals.Markers(parent=S); f.set_data(fl, face_color=(0.2, 0.4, 0.9, 0.25), size=2, edge_width=0)
            self.reveal_vis.append(f)
        tt = R["truth_trail"]
        if tt and tt.get("player"):
            tr = visuals.Line(parent=S, pos=np.array([(x, y, 0.3) for x, y, _ in tt["player"]]), color=(1.0, 0.3, 0.2, 0.9), width=2)
            self.reveal_vis.append(tr)
        if tt and tt.get("rival"):
            tr = visuals.Line(parent=S, pos=np.array([(x, y, 0.3) for x, y, _ in tt["rival"]]), color=(1.0, 0.6, 0.2, 0.6), width=1.5)
            self.reveal_vis.append(tr)
        ax, ay, ar = R["ancient"]
        self.reveal_vis.append(visuals.Line(parent=S, pos=_ring(ax, ay, ar, z=0.3), color=(0.95, 0.3, 0.95, 0.9), width=2))
        pts = np.array([[x, y, 0.35] for (x, y, _, _) in R["agents"].values()])
        am = visuals.Markers(parent=S); am.set_data(pts, face_color=(1.0, 0.3, 0.2, 1.0), size=12, symbol="x")
        self.reveal_vis.append(am)
        bp = np.array([[x, y, 0.35] for (x, y, o) in R["beacons"].values() if o == "player"])
        if len(bp):
            bm = visuals.Markers(parent=S); bm.set_data(bp, face_color=(1.0, 0.5, 0.3, 0.9), size=7, symbol="diamond")
            self.reveal_vis.append(bm)
        for (dx, dy) in R["deposits"].values():
            self.reveal_vis.append(visuals.Line(parent=S, pos=_ring(dx, dy, 3, n=24, z=0.3), color=(1.0, 0.9, 0.3, 0.9), width=2))

    # ---- offscreen snapshot, for tuning without a screen ---------------------------------
    def snapshot(self, path):
        self.draw()
        img = self.canvas.render()
        from vispy import io
        io.write_png(path, img)
