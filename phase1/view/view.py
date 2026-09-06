"""Belief-only display.

Laid out as three regions rather than telemetry floating over a picture: the policy
deciding on the left, the map it has built in the middle, and the shape of the match
along the bottom. Words live in fixed places, so position carries meaning and only
the one event happening now has to be read.

Truth appears exactly once, after the match is over, via `Sim.reveal()`.

Camera: left drag orbits, wheel zooms. R sends Recall.
"""
from __future__ import annotations

import math
import time

import numpy as np
from vispy import app, io, scene
from vispy.scene import visuals

from .. import tuning as T
from ..belief.belief import Belief
from ..match.sim import Sim
from ..sound_character import SoundCharacter
from . import palette
from .decision_tree import DecisionTreeView
from .event_feed import EventFeed
from .map_key import MapKey
from .shapes import ring, to_segments, wedge
from .status_panel import StatusPanel
from .timeline import TimelineView

HEADER_H: float = 44.0
PANEL_W: float = 292.0
TIMELINE_H: float = 62.0
FIX_ANIM_SECONDS: float = 0.7

FRIENDLY: dict[str, str] = {"DA": "deposit A", "DB": "deposit B",
                            "S": "the shaft", "HOME": "the shaft"}
STATUS_LABELS: tuple[str, ...] = ("CARGO", "IT THINKS IT KNOWS WHERE IT IS TO",
                                  "LAST POSITION FIX", "MAP IT HAS BUILT",
                                  "YOUR ONE COMMAND")


class View:
    def __init__(self, sim: Sim, audio: object | None = None, show: bool = True,
                 size: tuple[int, int] = (1400, 900)) -> None:
        self.sim: Sim = sim
        self.audio = audio
        self.b: Belief = sim.beliefs["player"]
        self.size: tuple[int, int] = size
        w, h = size

        self.canvas = scene.SceneCanvas(title="BLINDSIDE", size=size,
                                        bgcolor=palette.BACKGROUND,
                                        keys="interactive", show=show)
        overlay = self.canvas.scene

        # The map gets its own box so the panels are never drawn over it.
        self.view = scene.ViewBox(parent=overlay, bgcolor=palette.BACKGROUND)
        self.view.pos = (PANEL_W, HEADER_H)
        self.view.size = (w - PANEL_W, h - HEADER_H - TIMELINE_H)
        camera = scene.TurntableCamera(elevation=58, azimuth=0, fov=0, up="z")
        camera.center = (100, 60, 0)
        camera.scale_factor = 150
        self.view.camera = camera

        s = self.view.scene
        self.cloud = visuals.Markers(parent=s)
        self.cloud.set_gl_state("translucent", depth_test=False)
        self.trail = visuals.Line(parent=s, color=palette.TRAIL, width=1)
        self.beacon_chain = visuals.Line(parent=s, color=palette.BEACON_CHAIN, width=1)
        self.beacons = visuals.Markers(parent=s)
        self.places = visuals.Markers(parent=s)
        self.ellipse = visuals.Line(parent=s, color=palette.ELLIPSE, width=1.5)
        self.agent = visuals.Markers(parent=s)
        self.heading = visuals.Line(parent=s, color=palette.AGENT, width=2)
        self.contacts = visuals.Line(parent=s, connect="segments", width=1.5)
        self.signature = visuals.Line(parent=s, connect="segments", width=2)
        self.fronts = visuals.Line(parent=s, connect="segments", width=1.2)
        self.fix_flash = visuals.Line(parent=s, connect="segments", width=2)
        self.intent = visuals.Line(parent=s, color=palette.INTENT, width=1.5)
        self.intent_marker = visuals.Markers(parent=s)
        self.believed = visuals.Line(parent=s, connect="segments", width=1.5)
        for v in (self.trail, self.ellipse, self.heading, self.contacts, self.signature,
                  self.fronts, self.fix_flash, self.intent, self.believed,
                  self.beacon_chain):
            v.set_gl_state("translucent", depth_test=False)

        # ---- chrome ----
        self.panel_left = self._panel(overlay, PANEL_W / 2, h / 2, PANEL_W, h)
        self.panel_header = self._panel(overlay, w / 2, HEADER_H / 2, w, HEADER_H)
        self.panel_timeline = self._panel(overlay, w / 2, h - TIMELINE_H / 2, w, TIMELINE_H)

        self.title = visuals.Text("BLINDSIDE", parent=overlay, pos=(18, HEADER_H / 2),
                                  anchor_x="left", anchor_y="center", color=palette.TITLE,
                                  font_size=13, bold=True)
        self.subtitle = visuals.Text(
            "you cannot drive it - you can only watch, and recall it once",
            parent=overlay, pos=(168, HEADER_H / 2), anchor_x="left",
            anchor_y="center", color=palette.DIM, font_size=8.5)
        self.header_right = visuals.Text("", parent=overlay, pos=(w - 18, HEADER_H / 2),
                                         anchor_x="right", anchor_y="center",
                                         color=palette.BANNER, font_size=10, bold=True)

        self.tree = DecisionTreeView(overlay, 8.0, HEADER_H + 30.0, PANEL_W - 16)
        rule_y = HEADER_H + 30.0 + self.tree.height + 8
        self._rule(overlay, 14, rule_y, PANEL_W - 28)
        self.status = StatusPanel(overlay, 8.0, rule_y + 26, PANEL_W - 16, STATUS_LABELS)
        self.key = MapKey(overlay, PANEL_W + 24, h - TIMELINE_H - 140)
        self.timeline = TimelineView(overlay, PANEL_W + 18, h - TIMELINE_H + 6,
                                     w - PANEL_W - 36, TIMELINE_H - 12)

        self.feed: EventFeed = EventFeed(self.b)
        self._header_cache: str = ""
        self._prev_xy: tuple[np.ndarray, np.ndarray] | None = None
        self._anim_from: tuple[np.ndarray, np.ndarray] | None = None
        self._anim_start: float = -1e9
        self._n_fixes_seen: int = 0
        self.revealed: bool = False
        self.reveal_visuals: list[object] = []
        self._wall_clock_zero: float | None = None

        self.canvas.events.key_press.connect(self.on_key)
        self.canvas.events.resize.connect(self.on_resize)
        self._layout(w, h)
        self.timer = app.Timer(interval=1 / 60, connect=self.on_tick, start=show)

    # ---- layout ------------------------------------------------------------------------
    def _layout(self, w: float, h: float) -> None:
        """Place everything from the current canvas size.

        The layout is absolute pixels, so without this every label sits where a
        1400x900 window would have put it and the whole thing overprints itself the
        moment the window is any other size.
        """
        self.view.pos = (PANEL_W, HEADER_H)
        self.view.size = (max(w - PANEL_W, 50), max(h - HEADER_H - TIMELINE_H, 50))
        self.panel_left.center = (PANEL_W / 2, h / 2)
        self.panel_left.height = h
        self.panel_header.center = (w / 2, HEADER_H / 2)
        self.panel_header.width = w
        self.panel_timeline.center = (w / 2, h - TIMELINE_H / 2)
        self.panel_timeline.width = w
        self.header_right.pos = (w - 18, HEADER_H / 2)
        self.subtitle.visible = w > 760
        self.key.move(PANEL_W + 24, h - TIMELINE_H - 24 - self.key.height)
        self.timeline.move(PANEL_W + 18, h - TIMELINE_H + 6, max(w - PANEL_W - 36, 80))

    def on_resize(self, ev: object) -> None:
        w, h = self.canvas.size
        self._layout(float(w), float(h))

    # ---- chrome helpers ---------------------------------------------------------------
    @staticmethod
    def _panel(parent: object, cx: float, cy: float, w: float, h: float) -> object:
        return visuals.Rectangle(center=(cx, cy), width=w, height=h,
                                 color=palette.PANEL, border_color=palette.PANEL_EDGE,
                                 border_width=1, parent=parent)

    @staticmethod
    def _rule(parent: object, x: float, y: float, w: float) -> object:
        line = visuals.Line(parent=parent, color=palette.PANEL_EDGE, width=1)
        line.set_data(np.array([[x, y, 0.0], [x + w, y, 0.0]]))
        return line

    # ---- input ------------------------------------------------------------------------
    def on_key(self, ev: object) -> None:
        key = getattr(ev, "key", None)
        if key is not None and key.name.lower() == "r":
            if self.sim.recall() and self.audio is not None:
                self.audio.recall_sent()      # type: ignore[attr-defined]

    # ---- frame ------------------------------------------------------------------------
    def on_tick(self, ev: object) -> None:
        if self._wall_clock_zero is None:
            self._wall_clock_zero = time.perf_counter()
        target = time.perf_counter() - self._wall_clock_zero
        steps = 0
        while self.sim.t < target and not self.sim.over and steps < 6:
            self.sim.step()
            if self.sim.tick % 10 == 0:
                self.sim.record_truth_trail()
            steps += 1
        self.draw()

    def draw(self) -> None:
        b, t = self.b, self.sim.t
        self.feed.update(t)
        self._draw_cloud(b, t)
        self._draw_places(b)
        self._draw_agent(b)
        self._draw_intent(b)
        self._draw_believed(b)
        self._draw_contacts(b, t)
        self._draw_fronts(b, t)
        self._draw_fix(b, t)
        self._draw_panels(b, t)
        self.timeline.update(self.feed, t)
        if self.audio is not None:
            self.audio.update(b, t, self.view.camera.azimuth)   # type: ignore[attr-defined]
        if self.sim.over and not self.revealed:
            self._reveal()
        self.canvas.update()

    # ---- the map ------------------------------------------------------------------------
    def _draw_cloud(self, b: Belief, t: float) -> None:
        """Points sit where the agent believed it was when it sensed them, so the map
        smears as the estimate drifts. A fix is eased across FIX_ANIM_SECONDS: it lands
        in a single sim tick, which at 20 fps is one frame, and the ghost corridor
        sliding onto the original was over before the eye could start."""
        n = b.cloud.n
        if n == 0:
            self.cloud.visible = False
            return
        if len(b.fixes) > self._n_fixes_seen:
            self._n_fixes_seen = len(b.fixes)
            if self._prev_xy is not None and b.fixes[-1].jump > 1.0:
                self._anim_from = self._prev_xy
                self._anim_start = t

        xs = b.cloud.x[:n].copy()
        ys = b.cloud.y[:n].copy()
        progress = (t - self._anim_start) / FIX_ANIM_SECONDS
        if self._anim_from is not None and 0.0 <= progress < 1.0:
            eased = 1.0 - (1.0 - progress) ** 3
            m = min(len(self._anim_from[0]), n)
            xs[:m] = self._anim_from[0][:m] + (xs[:m] - self._anim_from[0][:m]) * eased
            ys[:m] = self._anim_from[1][:m] + (ys[:m] - self._anim_from[1][:m]) * eased
        elif progress >= 1.0:
            self._anim_from = None
        self._prev_xy = (b.cloud.x[:n].copy(), b.cloud.y[:n].copy())

        q = b.cloud.confidence[:n]
        walked = b.cloud.source[:n] == 1
        rgb = palette.POINT_LOW[None, :] + (palette.POINT_HIGH - palette.POINT_LOW)[None, :] * q[:, None]
        alpha = 0.32 + 0.68 * q
        size = 2.6 + 5.2 * q
        rgb[walked] = palette.POINT_WALKED
        alpha[walked] = 0.22
        size[walked] = 1.7
        self.cloud.set_data(np.column_stack([xs, ys, b.cloud.z[:n]]),
                            face_color=np.column_stack([rgb, alpha]),
                            edge_width=0, size=size, symbol="disc")
        self.cloud.visible = True
        if len(b.trail) > 1:
            self.trail.set_data(np.array([(x, y, 0.05) for x, y, _ in b.trail]))
            self.trail.visible = True

    def _draw_places(self, b: Belief) -> None:
        """Beacons, the chain joining them, and the places it was told about."""
        if b.beacon_order:
            pts = [b.beacons[bid] for bid in b.beacon_order]
            self.beacons.set_data(np.array([[k.x, k.y, 0.12] for k in pts]),
                                  face_color=palette.BEACON, size=8,
                                  symbol="diamond", edge_width=0)
            self.beacons.visible = True
            if len(pts) > 1:
                self.beacon_chain.set_data(np.array([[k.x, k.y, 0.1] for k in pts]))
                self.beacon_chain.visible = True
        else:
            self.beacons.visible = False
            self.beacon_chain.visible = False

        marks: list[list[float]] = []
        colours: list[tuple[float, float, float, float]] = []
        for name in ("HOME", "DA", "DB"):
            place = b.known_places.get(name)
            if place is None:
                continue
            marks.append([place[0], place[1], 0.12])
            colours.append(palette.SHAFT if name == "HOME" else palette.DEPOSIT)
        if marks:
            self.places.set_data(np.array(marks), face_color=np.array(colours),
                                 size=15, symbol="star", edge_width=0)
            self.places.visible = True

    def _draw_agent(self, b: Belief) -> None:
        self.agent.set_data(np.array([[b.x, b.y, 0.2]]), face_color=palette.AGENT,
                            size=13, symbol="triangle_up", edge_width=0)
        self.heading.set_data(np.array([[b.x, b.y, 0.2],
                                        [b.x + 4 * math.cos(b.theta),
                                         b.y + 4 * math.sin(b.theta), 0.2]]))
        along, cross, angle = b.ellipse()
        a = np.linspace(0, 2 * math.pi, 64)
        ex = T.ELLIPSE_SIGMAS * along * np.cos(a)
        ey = T.ELLIPSE_SIGMAS * cross * np.sin(a)
        c, s = math.cos(angle), math.sin(angle)
        self.ellipse.set_data(np.column_stack([b.x + c * ex - s * ey,
                                               b.y + s * ex + c * ey, np.full(64, 0.1)]))

    def _draw_intent(self, b: Belief) -> None:
        policy = self.sim.policies["player"]
        if policy.done or not policy.route or policy.i >= len(policy.route):
            self.intent.visible = False
            self.intent_marker.visible = False
            return
        wp = policy.route[policy.i]
        self.intent.set_data(np.array([[b.x, b.y, 0.18], [wp.x, wp.y, 0.18]]))
        self.intent_marker.set_data(np.array([[wp.x, wp.y, 0.18]]),
                                    face_color=palette.INTENT, size=14,
                                    symbol="ring", edge_width=0)
        self.intent.visible = True
        self.intent_marker.visible = True

    def _draw_believed(self, b: Belief) -> None:
        """Where the agent has worked out that things probably are.

        Not truth, and not given to it: bearings heard from different places, crossed.
        The ring is how badly those bearings disagree, so something heard only once,
        or only from one spot, does not appear at all.
        """
        segments: list[np.ndarray] = []
        colours: list[tuple[float, float, float, float]] = []
        for tracker, colour in ((b.hazard_track, palette.BELIEVED_HAZARD),
                                (b.rival_track, palette.BELIEVED_RIVAL)):
            guess = tracker.estimate()
            if guess is None:
                continue
            gx, gy, sigma = guess
            circle = ring(gx, gy, min(max(sigma, 4.0), 34.0), n=44, z=0.14)
            segments += list(to_segments(circle))
            colours += [colour] * (2 * 44 - 2)
            for dx, dy in ((4.0, 0.0), (0.0, 4.0)):
                segments += [np.array([gx - dx, gy - dy, 0.14]),
                             np.array([gx + dx, gy + dy, 0.14])]
                colours += [colour] * 2
        if segments:
            self.believed.set_data(np.array(segments), color=np.array(colours))
            self.believed.visible = True
        else:
            self.believed.visible = False

    def _draw_contacts(self, b: Belief, t: float) -> None:
        segments: list[np.ndarray] = []
        colours: list[tuple[float, float, float, float]] = []
        for c in b.contacts:
            alpha = max(0.0, 1.0 - (t - c.t_last) / T.CONTACT_FADE_S)
            if alpha <= 0.0:
                continue
            half = math.radians(T.BEARING_NOISE_NEAR_DEG
                                + (T.BEARING_NOISE_FAR_DEG - T.BEARING_NOISE_NEAR_DEG) * (1 - c.quality))
            pts = wedge(b.x, b.y, c.bearing, half, 11 + 17 * c.quality)
            segments += pts
            rgb = palette.CONTACT.get(c.character, (1.0, 1.0, 1.0))
            colours += [(*rgb, alpha * (0.25 + 0.5 * c.quality))] * len(pts)
        if segments:
            self.contacts.set_data(np.array(segments), color=np.array(colours))
            self.contacts.visible = True
        else:
            self.contacts.visible = False

        sig = b.signature
        if sig is not None and t - sig.t < 1.0:
            strength = sig.quality
            pulse = 0.5 + 0.5 * math.sin(t * (3 + 14 * strength))
            pts = wedge(b.x, b.y, sig.bearing, math.radians(8), 26 + 34 * strength, 0.16)
            self.signature.set_data(np.array(pts),
                                    color=(*palette.SIGNATURE, 0.30 + 0.6 * pulse * strength))
            self.signature.visible = True
        else:
            self.signature.visible = False

    def _draw_fronts(self, b: Belief, t: float) -> None:
        segments: list[np.ndarray] = []
        colours: list[tuple[float, float, float, float]] = []
        for ping in b.own_pings[-6:]:
            age = t - ping.t
            if 0.0 <= age < T.WAVEFRONT_LIFE_S:
                circle = ring(ping.x, ping.y, age * T.WAVEFRONT_SPEED, n=96, z=0.12)
                segments += list(to_segments(circle))
                colours += [(0.55, 0.88, 1.0, 0.55 * (1 - age / T.WAVEFRONT_LIFE_S))] * (2 * 96 - 2)
        arrivals = [x for x in b.heard[-40:]
                    if x.character in (SoundCharacter.PING, SoundCharacter.CRASH)]
        for sound in arrivals[-6:]:
            age = t - sound.t
            if not (0.0 <= age < 4.0):
                continue
            radius = 50.0 if sound.character is SoundCharacter.CRASH else 35.0
            d = 55 - age * T.WAVEFRONT_SPEED
            cx = b.x + math.cos(sound.bearing) * (d + radius)
            cy = b.y + math.sin(sound.bearing) * (d + radius)
            back = sound.bearing + math.pi
            arc = ring(cx, cy, radius, n=40, a0=back - 0.6, a1=back + 0.6, z=0.12)
            segments += list(to_segments(arc))
            rgb = palette.CONTACT[sound.character]
            colours += [(*rgb, (0.3 + 0.7 * sound.quality) * (1 - age / 4.0))] * (2 * 40 - 2)
        if segments:
            self.fronts.set_data(np.array(segments), color=np.array(colours))
            self.fronts.visible = True
        else:
            self.fronts.visible = False

    def _draw_fix(self, b: Belief, t: float) -> None:
        segments: list[np.ndarray] = []
        colours: list[tuple[float, float, float, float]] = []
        for record in b.fixes[-3:]:
            age = t - record.t
            if age >= 3.0:
                continue
            alpha = 1 - age / 3.0
            segments += [np.array([record.pre_x, record.pre_y, 0.2]),
                         np.array([record.post_x, record.post_y, 0.2])]
            colours += [(*palette.FIX_FLASH, alpha)] * 2
            circle = ring(record.post_x, record.post_y, 1.5 + age * 4, n=32, z=0.2)
            segments += list(to_segments(circle))
            colours += [(*palette.FIX_FLASH, alpha * 0.6)] * (2 * 32 - 2)
        if segments:
            self.fix_flash.set_data(np.array(segments), color=np.array(colours))
            self.fix_flash.visible = True
        else:
            self.fix_flash.visible = False

    # ---- panels ---------------------------------------------------------------------------
    def _draw_panels(self, b: Belief, t: float) -> None:
        sim = self.sim
        policy = sim.policies["player"]
        self.tree.update(policy.active_nodes(), self._root_label(policy))

        since = b.ticks_since_fix * T.DT
        fix = b.last_fix
        surprised = fix is not None and fix.surprise >= 2.5 and fix.jump >= 8.0
        if fix is None:
            fix_text = "none yet"
        else:
            ago = f"{int(since) // 60}:{int(since) % 60:02d} ago"
            fix_text = f"{ago}, moved it {fix.jump:.0f} cells"
        self.status.set((
            f"{b.cargo} of {T.CARGO_CAPACITY}",
            f"within {b.sigma_pos():.0f} cells",
            fix_text,
            f"{b.cloud.n} points, {len(b.own_pings)} pings",
            "spent" if sim.recall_used else "ready - press R",
        ), (
            None,
            palette.BANNER if b.sigma_pos() > 12 else palette.TITLE,
            palette.BANNER if surprised else palette.TITLE,
            None,
            palette.DIM if sim.recall_used else palette.TREE_LIVE,
        ))

        if sim.over and sim.result is not None:
            header = f"MATCH OVER - {sim.result.player_outcome}, cargo {sim.result.cargo}"
        elif t >= T.EXTRACT_WINDOW_OPENS:
            header = "EXTRACTION WINDOW OPEN"
        else:
            left = T.EXTRACT_WINDOW_OPENS - t
            header = f"extraction opens in {int(left) // 60}:{int(left) % 60:02d}"
        if header != self._header_cache:
            self._header_cache = header
            self.header_right.text = header

    def _root_label(self, policy: object) -> str:
        mode = str(getattr(policy, "mode", ""))
        if getattr(policy, "done", False):
            return "IT THINKS IT IS HOME"
        if getattr(policy, "recalled", False):
            return "RECALLED - RUNNING FOR THE SHAFT"
        if mode == "home":
            return "TURNING BACK"
        if mode == "search":
            return "LOOKING FOR THE SHAFT"
        if mode == "load":
            return "LOADING CARGO"
        return f"MAKING FOR {self._target_name().upper()}"

    def _target_name(self) -> str:
        policy = self.sim.policies["player"]
        if policy.done or not policy.route or policy.i >= len(policy.route):
            return "nothing"
        label = policy.route[policy.i].label
        if label in FRIENDLY:
            return FRIENDLY[label]
        return "its own beacon" if label.startswith("player_") else f"survey point {label}"

    # ---- after the end ------------------------------------------------------------------------
    def _reveal(self) -> None:
        self.revealed = True
        r = self.sim.reveal()
        s = self.view.scene

        walls = np.column_stack([r.walls, np.full(len(r.walls), -0.1)])
        wall_vis = visuals.Markers(parent=s)
        wall_vis.set_data(walls, face_color=palette.TRUTH_WALL, size=2.5, edge_width=0)
        wall_vis.set_gl_state("translucent", depth_test=False)
        self.reveal_visuals.append(wall_vis)

        if len(r.flooded):
            flooded = np.column_stack([r.flooded, np.full(len(r.flooded), -0.1)])
            flood_vis = visuals.Markers(parent=s)
            flood_vis.set_data(flooded, face_color=palette.TRUTH_FLOOD, size=2, edge_width=0)
            self.reveal_visuals.append(flood_vis)

        for name, colour, width in (("player", palette.TRUTH_TRAIL_PLAYER, 2),
                                    ("rival", palette.TRUTH_TRAIL_RIVAL, 1.5)):
            path = r.truth_trail.get(name)
            if path:
                self.reveal_visuals.append(visuals.Line(
                    parent=s, pos=np.array([(x, y, 0.3) for x, y, _ in path]),
                    color=colour, width=width))

        ax, ay, ar = r.ancient
        self.reveal_visuals.append(visuals.Line(parent=s, pos=ring(ax, ay, ar, z=0.3),
                                                color=(*palette.SIGNATURE, 0.9), width=2))
        ends = np.array([[x, y, 0.35] for (x, y, _, _) in r.agents.values()])
        end_vis = visuals.Markers(parent=s)
        end_vis.set_data(ends, face_color=palette.TRUTH_TRAIL_PLAYER, size=12, symbol="x")
        self.reveal_visuals.append(end_vis)

        own = np.array([[x, y, 0.35] for (x, y, owner) in r.beacons.values() if owner == "player"])
        if len(own):
            beacon_vis = visuals.Markers(parent=s)
            beacon_vis.set_data(own, face_color=palette.TRUTH_BEACON, size=7, symbol="diamond")
            self.reveal_visuals.append(beacon_vis)

        for dx, dy in r.deposits.values():
            self.reveal_visuals.append(visuals.Line(parent=s, pos=ring(dx, dy, 3, n=24, z=0.3),
                                                    color=palette.TRUTH_DEPOSIT, width=2))

    # ---- offscreen -----------------------------------------------------------------------------
    def snapshot(self, path: str) -> None:
        self.draw()
        io.write_png(path, self.canvas.render())
