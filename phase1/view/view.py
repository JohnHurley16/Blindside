"""Belief-only display.

Receives Belief objects and never sees World during the run. Once the match is over,
`Sim.reveal()` hands over truth for the replay overlay -- that is the one place truth
is drawn, and it is guarded on the match being finished.

Camera: left drag orbits, wheel zooms, starts top-down. R sends Recall.
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
from .caption_feed import CaptionFeed
from .shapes import ring, to_segments

FIX_ANIM_SECONDS: float = 0.7
CAPTION_HOLD: float = 3.2
CAPTION_FADE: float = 1.3
FRIENDLY: dict[str, str] = {"DA": "DEPOSIT A", "DB": "DEPOSIT B",
                           "S": "THE SHAFT", "HOME": "THE SHAFT"}


class View:
    def __init__(self, sim: Sim, audio: object | None = None, show: bool = True,
                 size: tuple[int, int] = (1400, 900)) -> None:
        self.sim: Sim = sim
        self.audio = audio
        self.b: Belief = sim.beliefs["player"]
        self.canvas = scene.SceneCanvas(title="BLINDSIDE - belief view (R = Recall)",
                                        size=size, bgcolor=palette.BACKGROUND,
                                        keys="interactive", show=show)
        self.view = self.canvas.central_widget.add_view()
        # Not straight down. A flat sheet of dots hides the fact that this is a volume,
        # and the wall height only does something once the camera is off the vertical.
        camera = scene.TurntableCamera(elevation=62, azimuth=0, fov=0, up="z")
        camera.center = (100, 60, 0)
        camera.scale_factor = 140
        self.view.camera = camera

        s = self.view.scene
        self.cloud = visuals.Markers(parent=s)
        self.cloud.set_gl_state("translucent", depth_test=False)
        self.trail = visuals.Line(parent=s, color=palette.TRAIL, width=1)
        self.beacons = visuals.Markers(parent=s)
        self.ellipse = visuals.Line(parent=s, color=palette.ELLIPSE, width=1.5)
        self.agent = visuals.Markers(parent=s)
        self.heading = visuals.Line(parent=s, color=palette.AGENT, width=2)
        self.contacts = visuals.Line(parent=s, connect="segments", width=1.5)
        self.signature = visuals.Line(parent=s, connect="segments", width=2)
        self.fronts = visuals.Line(parent=s, connect="segments", width=1.2)
        self.fix_flash = visuals.Line(parent=s, connect="segments", width=2)
        self.intent = visuals.Line(parent=s, color=(0.40, 0.95, 0.72, 0.45), width=1.5)
        self.intent_marker = visuals.Markers(parent=s)
        for v in (self.trail, self.ellipse, self.heading, self.contacts,
                  self.signature, self.fronts, self.fix_flash, self.intent):
            v.set_gl_state("translucent", depth_test=False)

        self.reveal_visuals: list[object] = []
        self.hud_lines = [visuals.Text("", parent=self.canvas.scene, pos=(18, 22 + 19 * i),
                                       anchor_x="left", anchor_y="top",
                                       color=palette.HUD, font_size=9) for i in range(10)]
        self.banner = visuals.Text("", parent=self.canvas.scene, pos=(size[0] / 2, size[1] - 40),
                                   anchor_x="center", anchor_y="center",
                                   color=palette.BANNER, font_size=16, bold=True)
        self.legend = visuals.Text(
            "bright dots: pinged wall     dim dots: ground it only walked through     "
            "wedges: a bearing, no range     green: where it thinks it is",
            parent=self.canvas.scene, pos=(18, size[1] - 20), anchor_x="left",
            anchor_y="bottom", color=palette.LEGEND, font_size=8)
        self.canvas.events.key_press.connect(self.on_key)
        self.canvas.events.resize.connect(self.on_resize)
        self._hud_cache: list[str] = [""] * len(self.hud_lines)
        self.feed: CaptionFeed = CaptionFeed(self.b)
        self._caption_visuals: list[tuple[object, object]] = []
        for i in range(3):
            y = size[1] * 0.70 + i * 56
            head = visuals.Text("", parent=self.canvas.scene, pos=(size[0] / 2, y),
                                anchor_x="center", anchor_y="center",
                                color=palette.BANNER, font_size=15, bold=True)
            detail = visuals.Text("", parent=self.canvas.scene, pos=(size[0] / 2, y + 23),
                                  anchor_x="center", anchor_y="center",
                                  color=palette.HUD, font_size=9)
            self._caption_visuals.append((head, detail))
        self._caption_cache: list[tuple[str, str]] = [("", "")] * 3
        # For animating a fix. The correction lands in a single sim tick, which at
        # 20 fps is one frame -- the most important visual in the test was finishing
        # before the eye could start. So the display eases the map across instead.
        self._prev_xy: np.ndarray | None = None
        self._anim_from: np.ndarray | None = None
        self._anim_start: float = -1e9
        self._n_fixes_seen: int = 0
        self.revealed: bool = False
        self._wall_clock_zero: float | None = None
        self.timer = app.Timer(interval=1 / 60, connect=self.on_tick, start=show)

    # ---- input --------------------------------------------------------------------------
    def on_key(self, ev: object) -> None:
        key = getattr(ev, "key", None)
        if key is not None and key.name.lower() == "r":
            if self.sim.recall():
                self.banner.text = "RECALL SENT"
                if self.audio is not None:
                    self.audio.recall_sent()      # type: ignore[attr-defined]

    def on_resize(self, ev: object) -> None:
        w, h = self.canvas.size
        self.banner.pos = (w / 2, h - 40)
        self.legend.pos = (18, h - 20)

    # ---- frame --------------------------------------------------------------------------
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
        self._draw_agent(b)
        self._draw_intent(b)
        self._draw_contacts(b, t)
        self._draw_fronts(b, t)
        self._draw_fix(b, t)
        self._draw_hud(b, t)
        self._draw_captions(t)
        if self.audio is not None:
            self.audio.update(b, t, self.view.camera.azimuth)   # type: ignore[attr-defined]
        if self.sim.over and not self.revealed:
            self._reveal()
        self.canvas.update()

    # ---- the map ------------------------------------------------------------------------
    def _draw_cloud(self, b: Belief, t: float) -> None:
        """The point cloud, in the agent's estimated frame.

        Nothing corrects for drift here, because the smear IS the map: points were
        placed with whatever pose the agent held at the time. What this does add is
        time -- a fix is eased across FIX_ANIM_SECONDS so the ghost corridor can be
        seen sliding onto the original rather than teleporting between two frames.
        """
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
        source = b.cloud.source[:n]
        walked = source == 1
        rgb = palette.POINT_LOW[None, :] + (palette.POINT_HIGH - palette.POINT_LOW)[None, :] * q[:, None]
        alpha = 0.30 + 0.70 * q
        size = 2.5 + 5.0 * q
        # Ground the agent only walked through is dimmer and smaller than ground it
        # actually pinged. There are four of these for every sonar return, so drawing
        # them alike is most of why an accumulated map reads as undifferentiated noise.
        rgb[walked] = palette.POINT_WALKED
        alpha[walked] = 0.20
        size[walked] = 1.6
        self.cloud.set_data(np.column_stack([xs, ys, b.cloud.z[:n]]),
                            face_color=np.column_stack([rgb, alpha]),
                            edge_width=0, size=size, symbol="disc")
        self.cloud.visible = True
        if len(b.trail) > 1:
            self.trail.set_data(np.array([(x, y, 0.05) for x, y, _ in b.trail]))
            self.trail.visible = True

    def _draw_agent(self, b: Belief) -> None:
        self.agent.set_data(np.array([[b.x, b.y, 0.2]]), face_color=palette.AGENT,
                            size=11, symbol="triangle_up")
        self.heading.set_data(np.array([[b.x, b.y, 0.2],
                                        [b.x + 3 * math.cos(b.theta),
                                         b.y + 3 * math.sin(b.theta), 0.2]]))
        along, cross, angle = b.ellipse()
        a = np.linspace(0, 2 * math.pi, 64)
        ex = T.ELLIPSE_SIGMAS * along * np.cos(a)
        ey = T.ELLIPSE_SIGMAS * cross * np.sin(a)
        c, s = math.cos(angle), math.sin(angle)
        self.ellipse.set_data(np.column_stack([b.x + c * ex - s * ey,
                                               b.y + s * ex + c * ey, np.full(64, 0.1)]))
        if b.beacons:
            pts = np.array([[k.x, k.y, 0.1] for k in b.beacons.values()])
            self.beacons.set_data(pts, face_color=palette.BEACON, size=7, symbol="diamond")
            self.beacons.visible = True

    def _draw_intent(self, b: Belief) -> None:
        """Where the agent is trying to get to, in its own believed coordinates.

        Without this the viewer cannot tell purposeful movement from thrashing, which
        is most of the difference between a machine working and a machine lost.
        """
        policy = self.sim.policies["player"]
        if policy.done or not policy.route or policy.i >= len(policy.route):
            self.intent.visible = False
            self.intent_marker.visible = False
            return
        wp = policy.route[policy.i]
        self.intent.set_data(np.array([[b.x, b.y, 0.18], [wp.x, wp.y, 0.18]]))
        self.intent_marker.set_data(np.array([[wp.x, wp.y, 0.18]]),
                                    face_color=(0.40, 0.95, 0.72, 0.55),
                                    size=13, symbol="ring", edge_width=0)
        self.intent.visible = True
        self.intent_marker.visible = True

    def _target_name(self) -> str:
        policy = self.sim.policies["player"]
        if policy.done or not policy.route or policy.i >= len(policy.route):
            return "nothing"
        label = policy.route[policy.i].label
        if label in FRIENDLY:
            return FRIENDLY[label]
        if label.startswith("player_"):
            return "one of its own beacons"
        return f"survey point {label}"

    def _draw_captions(self, t: float) -> None:
        active = self.feed.active(t, CAPTION_HOLD, CAPTION_FADE, limit=3)
        for i, (head, detail) in enumerate(self._caption_visuals):
            if i < len(active):
                caption, a = active[i]
                text, sub_text = caption.text, caption.detail
                head.color = (*palette.BANNER, a) if caption.weight >= 2.0 else (*palette.HUD, a * 0.8)
                head.font_size = 16 if caption.weight >= 2.0 else 11
                detail.color = (*palette.HUD, a * 0.75)
            else:
                text, sub_text = "", ""
            if self._caption_cache[i] != (text, sub_text):
                self._caption_cache[i] = (text, sub_text)
                head.text = text
                detail.text = sub_text

    def _wedge_at(self, b: Belief, bearing: float, half: float, length: float,
                  z: float = 0.15) -> list[np.ndarray]:
        from .shapes import wedge
        return wedge(b.x, b.y, bearing, half, length, z)

    def _draw_contacts(self, b: Belief, t: float) -> None:
        segs: list[np.ndarray] = []
        cols: list[tuple[float, float, float, float]] = []
        for c in b.contacts:
            alpha = max(0.0, 1.0 - (t - c.t_last) / T.CONTACT_FADE_S)
            if alpha <= 0.0:
                continue
            half = math.radians(T.BEARING_NOISE_NEAR_DEG
                                + (T.BEARING_NOISE_FAR_DEG - T.BEARING_NOISE_NEAR_DEG) * (1 - c.quality))
            pts = self._wedge_at(b, c.bearing, half, 11 + 17 * c.quality)
            segs += pts
            rgb = palette.CONTACT.get(c.character, (1.0, 1.0, 1.0))
            cols += [(*rgb, alpha * (0.25 + 0.5 * c.quality))] * len(pts)
        if segs:
            self.contacts.set_data(np.array(segs), color=np.array(cols))
            self.contacts.visible = True
        else:
            self.contacts.visible = False

        sig = b.signature
        if sig is not None and t - sig.t < 1.0:
            strength = sig.quality
            pulse = 0.5 + 0.5 * math.sin(t * (3 + 14 * strength))
            pts = self._wedge_at(b, sig.bearing, math.radians(8), 30 + 40 * strength, z=0.16)
            r = (t * (6 + 20 * strength)) % 12
            arc = ring(b.x + math.cos(sig.bearing) * (8 + r),
                       b.y + math.sin(sig.bearing) * (8 + r),
                       2 + strength * 3, n=24,
                       a0=sig.bearing - 1.2, a1=sig.bearing + 1.2, z=0.16)
            pts += list(to_segments(arc))
            self.signature.set_data(np.array(pts),
                                    color=(*palette.SIGNATURE, 0.35 + 0.6 * pulse * strength))
            self.signature.visible = True
        else:
            self.signature.visible = False

    def _draw_fronts(self, b: Belief, t: float) -> None:
        """Own pings expand from where the agent believed it was; heard sounds arrive
        as arcs from a bearing."""
        segs: list[np.ndarray] = []
        cols: list[tuple[float, float, float, float]] = []
        for ping in b.own_pings[-6:]:
            age = t - ping.t
            if 0.0 <= age < T.WAVEFRONT_LIFE_S:
                circle = ring(ping.x, ping.y, age * T.WAVEFRONT_SPEED, n=96, z=0.12)
                segs += list(to_segments(circle))
                cols += [(0.6, 0.9, 1.0, 0.7 * (1 - age / T.WAVEFRONT_LIFE_S))] * (2 * 96 - 2)

        arrivals = [s for s in b.heard[-40:]
                    if s.character in (SoundCharacter.PING, SoundCharacter.CRASH)]
        for sound in arrivals[-8:]:
            age = t - sound.t
            if not (0.0 <= age < 4.0):
                continue
            radius = 50.0 if sound.character is SoundCharacter.CRASH else 35.0
            d = 55 - age * T.WAVEFRONT_SPEED
            cx = b.x + math.cos(sound.bearing) * (d + radius)
            cy = b.y + math.sin(sound.bearing) * (d + radius)
            back = sound.bearing + math.pi
            arc = ring(cx, cy, radius, n=40, a0=back - 0.6, a1=back + 0.6, z=0.12)
            segs += list(to_segments(arc))
            rgb = palette.CONTACT[sound.character]
            cols += [(*rgb, (0.3 + 0.7 * sound.quality) * (1 - age / 4.0))] * (2 * 40 - 2)

        if segs:
            self.fronts.set_data(np.array(segs), color=np.array(cols))
            self.fronts.visible = True
        else:
            self.fronts.visible = False

    def _draw_fix(self, b: Belief, t: float) -> None:
        """Draw the correction itself. A fix that moves the estimate far further than
        the ellipse allowed is the one clue a player gets that something lied."""
        segs: list[np.ndarray] = []
        cols: list[tuple[float, float, float, float]] = []
        for record in b.fixes[-3:]:
            age = t - record.t
            if age >= 3.0:
                continue
            alpha = 1 - age / 3.0
            segs += [np.array([record.pre_x, record.pre_y, 0.2]),
                     np.array([record.post_x, record.post_y, 0.2])]
            cols += [(*palette.FIX_FLASH, alpha)] * 2
            circle = ring(record.post_x, record.post_y, 1.5 + age * 4, n=32, z=0.2)
            segs += list(to_segments(circle))
            cols += [(*palette.FIX_FLASH, alpha * 0.6)] * (2 * 32 - 2)
        if segs:
            self.fix_flash.set_data(np.array(segs), color=np.array(cols))
            self.fix_flash.visible = True
        else:
            self.fix_flash.visible = False

    def _draw_hud(self, b: Belief, t: float) -> None:
        sim = self.sim
        left = max(0.0, T.MATCH_SECONDS - t)
        window = T.EXTRACT_WINDOW_OPENS - t
        window_text = (f"extraction window opens in {int(window) // 60}:{int(window) % 60:02d}"
                       if window > 0 else "EXTRACTION WINDOW OPEN")
        since_fix = b.ticks_since_fix * T.DT
        fix = b.last_fix
        policy = sim.policies["player"]
        lines = [
            f"T-{int(left) // 60}:{int(left) % 60:02d}    {window_text}",
            "",
            f"IT IS DOING: {self._doing(policy)}",
            f"IT BELIEVES: it is carrying {b.cargo} of {T.CARGO_CAPACITY}, "
            f"and that it knows where it is to within {b.sigma_pos():.0f} cells",
            f"LAST POSITION FIX: {self._fix_phrase(fix, since_fix)}",
            f"MAP: {b.cloud.n} points, {len(b.own_pings)} pings sent, "
            f"{len(b.contacts)} contact{'' if len(b.contacts) == 1 else 's'} being tracked",
            "RECALL: " + ("spent" if sim.recall_used else "available - press R, once only"),
        ]
        if policy.hold:
            lines.append("HOLDING STILL - it can hear machinery")
        # Only touch a Text visual when the string actually changed: assigning to
        # .text rebuilds the glyph atlas, and doing that for seven lines every frame
        # cost more than drawing the entire point cloud.
        for i, text_visual in enumerate(self.hud_lines):
            wanted = lines[i] if i < len(lines) else ""
            if self._hud_cache[i] != wanted:
                self._hud_cache[i] = wanted
                text_visual.text = wanted

        banner = self.banner.text
        if sim.over and sim.result is not None:
            banner = (f"MATCH OVER - agent {sim.result.player_outcome}, "
                      f"cargo {sim.result.cargo}   (truth now shown in red)")
        elif sim.recall_used and not sim.recall_pending:
            banner = "RECALL RECEIVED - agent running for the shaft it believes in"
        if banner != self.banner.text:
            self.banner.text = banner

    # ---- after the end -------------------------------------------------------------------
    def _doing(self, policy: object) -> str:
        mode = str(getattr(policy, "mode", ""))
        target = self._target_name()
        if getattr(policy, "done", False):
            return "waiting - it thinks it is home"
        if mode == "load":
            return "loading cargo where it believes a deposit is"
        if mode == "search":
            return "searching for a shaft that is not where it expected"
        if mode == "home":
            return f"heading home, currently making for {target}"
        return f"surveying, currently making for {target}"

    @staticmethod
    def _fix_phrase(fix: object, since: float) -> str:
        if fix is None:
            return "none yet"
        jump = getattr(fix, "jump", 0.0)
        surprise = getattr(fix, "surprise", 0.0)
        ago = f"{int(since) // 60}:{int(since) % 60:02d} ago"
        if surprise >= 2.5 and jump >= 8.0:
            return f"{ago} - and it moved the estimate {jump:.0f} cells, far more than expected"
        return f"{ago} - moved the estimate {jump:.1f} cells"

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

    # ---- offscreen ---------------------------------------------------------------------------
    def snapshot(self, path: str) -> None:
        self.draw()
        io.write_png(path, self.canvas.render())
